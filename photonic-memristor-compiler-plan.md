# Plan v2: A Physics + Math Unified Compiler for Photonic and Memristive Hardware

> **Implementation checkpoint (2026-11-10).** This document is the long-term research
> vision, not a claim that all layers exist. The executable MVP now implements
> bounded straight-line rational arithmetic, explicit physical-domain/error checks,
> an exact independent certificate checker, and one static-weight MZI/DAC/SW-1
> demonstration. See [README](README.md), [milestone status](docs/milestones.md), and
> [verification boundaries](docs/verification.md). The Lean build is pending external
> validation; numeric obligation export is not yet a full source-to-physics proof.
>
> **Near-term scope:** one bounded arithmetic graph and one illustrative calibrated
> MZI. Arbitrary functions, generalized device selection, solver integration,
> memristor lowering, physical scheduling, and closed-loop control remain future work.

**Goal.** Compile *any* mathematics into physical control parameters (voltages, currents, pulses, wavelengths, timings) for light-based and memristor-based chips. All arithmetic reduces to a **Core Analog Algebra** of four operations (+, −, ×, ÷). Each operation can be realized physically in many ways, organized as an extensible **Physics Tree**. Each step is checked by math (Lean4), constraints (Z3/dReal) and a physics simulator (the "Small World") before anything touches hardware. A timing layer with closed-loop correction keeps the hardware correct while it runs.

---

## 0. Architecture at a glance

```
L0  Frontend            any math: expressions, functions, tensors, programs
 |
L1  Math IR             real/complex arithmetic, functions, control flow
 |   approximation passes: exp, sin, log, sqrt ... -> rational form with
 |   proven error bounds (Chebyshev / Pade / Newton iterations)
L2  Core Analog         ABSTRACT: add, sub, mul, div  (+ const, fanout,
 |  Algebra IR          route, store, convert, compare)
 |                      every value carries: range, encoding, error budget
L3  Physics Tree        each abstract op -> physical mechanisms -> devices
 |                      (built-in branches + user-invented branches)
 |
 ==  Small World        physics simulator + law checker + Lean/Z3 checks
 |   (verification      must PASS before lowering further
 |    gate)
L4  Control / Knob IR   engineering-level knobs: DAC codes, V, I, pulse
 |                      shapes, laser lambda/power, safe operating area
 |
L5  Timing + Adaptive   physics-derived timing (ps ... s), disturbance
    Control             models, closed-loop self-correction at runtime
```

Three checking tools run at every level:
- **Lean4 + Mathlib**: general theorems ("for all inputs in range, this lowering is within ε").
- **Z3 / dReal**: checks for one specific program on one specific chip (ranges, power, timing, wavelength spacing). Use validated transcendental enclosures or dReal for exp/sin/log constraints outside Z3's supported theories. dReal is δ-complete: δ-sat is not exact satisfiability; unknown/timeouts must fail closed. Solver certificates and their trusted checker must be specified.
- **Small World simulator**: executes the physics with noise, drift and crosstalk, and checks that physical laws are obeyed.

---

## 1. Math foundation: the Core Analog Algebra (L2)

### 1.1 Why four operations are enough (and what else is needed)

- {+, −, ×, ÷} are the **field operations** of ℝ. Any **rational function** (polynomials and ratios of polynomials) can be built from them exactly.
- Non-rational functions (exp, sin, log, sqrt, sigmoid, ...) are lowered in **L1** into rational approximations with **proven error bounds**: Chebyshev or minimax polynomials, Padé approximants, Newton iterations for sqrt and 1/x. Lean proves the bound on the domain; the error enters the budget.
- Optionally, a Physics Tree branch can provide a function **natively**, because physics gives it for free (photodetector: |E|²; diode: exp; saturable absorber: a sigmoid-like curve). Those are registered as **native extensions** with their own error model. They are a shortcut, not a requirement.
- Four arithmetic operations alone do **not** make a complete computer. A few **structural primitives** are also required, and they are physical too:
  - `const c`: a reference value (laser power level, reference voltage, stored conductance)
  - `fanout x → (x, x)`: copying is **not free** physically. An optical 1:2 splitter gives each output amplitude x/√2 (power x/2), so the compiler must track it.
  - `route`: waveguide or wire connections, which add loss and delay
  - `store / load`: memory (memristor or PCM states need no refresh power; read/write and peripheral energy still count)
  - `convert`: optical↔electrical (O/E, E/O) and analog↔digital (ADC/DAC)
  - `compare / select`: for control flow (`if`, `while`). This is either an analog comparator, or the program is split so a digital host handles control flow and analog hardware runs the arithmetic.

### 1.2 Values are encoded in physical quantities

The same number can live in different physical quantities, and which operations are cheap depends on that choice. So every L2 value carries an **encoding type**:

| Encoding | Physical quantity | Natural range | Sign? |
|---|---|---|---|
| `OptAmp` | coherent optical field amplitude E | complex, \|E\| ≤ E_max | yes (via phase 0/π) |
| `OptPow` | optical power P = \|E\|² | [0, P_max] | no (needs differential pair) |
| `OptPhase` | phase φ | [0, 2π) | angle |
| `Volt` / `Curr` | voltage / current | [V_min, V_max] | yes |
| `Cond` | conductance G | [G_min, G_max] > 0 | no (needs G⁺ − G⁻) |
| `Level` | PCM crystalline level | {0..63} | no |
| `Digital` | bits | fixed/float | yes |

Formally, an encoding is a pair `enc : ℝ_domain → PhysQuantity`, `dec : PhysQuantity → ℝ` with `dec ∘ enc = id` on the domain, plus a **scale** (e.g. 1.0 ↔ 1 mW). Changing encoding is an explicit `convert` op with its own cost and error.

### 1.3 Semantics: every abstract op is "approximately exact"

An L2 operation `⊙ ∈ {+, −, ×, ÷}` is given meaning as an **approximate operation with a contract**:

```
for all a ∈ A, b ∈ B (input ranges):
    | dec(realize_⊙(enc(a), enc(b))) − (a ⊙ b) | ≤ ε_⊙(a, b)
    and the output stays in its declared range
```

- This is **interval / affine arithmetic semantics** over the reals, formalized in Lean on top of Mathlib's `Real`.
- **Range analysis** is mandatory: physical values are bounded (T ≤ 1, G ∈ [G_min, G_max], V ≤ 5 V). The compiler inserts **scaling** (multiply by a constant, undone later) so every intermediate fits. Division needs `|b| ≥ b_min > 0`, proven or checked, never assumed.
- **Error composition** theorems (proved once in Lean) let the compiler output a **certified end-to-end error bound** for the whole program: `ε_total = f(ε_ops, ranges)`.
- Under noise, the guarantee becomes probabilistic: `P(|error| > ε) ≤ δ`. The noise models come from the physics layer.

**"100% correct" therefore means:** the math is proven exactly; the physical result is proven to be within a computed ε of the exact answer, **assuming the physics model holds**. The physics model is an explicit, named, calibrated assumption, and the Small World and the runtime monitors check it continuously.

### 1.4 What gets proven in Lean (Phase 0 core library)

- Encodings, scaling, and `dec ∘ enc = id`.
- Error-composition lemmas for +, −, ×, ÷, fanout, and for composition of programs.
- Approximation theorems: polynomial/Padé error bounds on intervals; Newton-iteration convergence for 1/x and sqrt.
- Linear algebra shortcuts, as macro-ops built on the core four: matrix-vector multiply, MZI ∈ U(2), Clements decomposition, SVD with scaling, differential encoding `w = w⁺ − w⁻`, crossbar `I = Gᵀ V`.
- Physical units / dimensional analysis as types (V, A, W, s, m, rad), so `V + nm` does not type-check.

---

## 2. L3: The Physics Tree

### 2.1 Structure

```
mul (abstract)
├── Optical-coherent
│   ├── MZI interference          amplitude × cos(θ/2)·e^{iφ}   [thermo-optic | EO]
│   └── Phase + combiner          sign flip via φ = π
├── Optical-incoherent
│   ├── PIN attenuator            P_out = T(I) · P_in            (free-carrier absorption)
│   ├── Microring weight          P_out = T(λ, V_ring) · P_in    (Lorentzian, WDM)
│   └── PCM on waveguide          P_out = T(level) · P_in        (non-volatile)
├── Electrical-memristive
│   └── ReRAM / HfO2 cell         I = G · V                      (Ohm, non-volatile)
└── <user-invented branch>        e.g. "multiply by four-wave mixing"

add (abstract)
├── Coherent interference         E_out = (E1 + E2)/√2    (phase-matched combiner)
├── Incoherent power summing      P_out = Σ P_i on one photodetector (different λ via WDM)
└── Kirchhoff current summing     I_out = Σ I_i at a node (crossbar column)

sub (abstract)
├── Balanced photodetection       I = R·(P⁺ − P⁻)
├── π-phase interference          E1 + e^{iπ} E2 = E1 − E2
└── Differential columns          I = (G⁺ − G⁻) · V

div (abstract)
├── Constant divisor              x / c  →  x · (1/c)   (precomputed, uses a mul branch)
├── Feedback (TIA/op-amp)         V_out = −V_in · G_in / G_fb   (memristor in feedback path)
├── Optical gain normalization    detector/TIA gain set to 1/c
├── Iterative (Newton)            1/b via x_{k+1} = x_k(2 − b·x_k), uses mul + sub
└── Digital fallback              when b varies fast or specified digital precision is preferable; arbitrary real division is not generally exact
```

### 2.2 What a Physics Tree node is (formal contract)

Each node `n` refines its parent and must provide:

| Field | Meaning |
|---|---|
| `implements` | which abstract op (or parent node) it realizes |
| `encoding_in / encoding_out` | e.g. `OptPow → OptPow` |
| `transfer` | math formula of the physical process, e.g. `P_out = T·P_in` |
| `parameters` | physical params with units and ranges (φ, T, G, λ_res, level) |
| `laws_used` | which physics laws it relies on (energy conservation, Kirchhoff, Ohm, ...) |
| `error_model` | systematic error + noise (as distributions) |
| `cost` | energy, area, latency, endurance (write cycles) |
| `proof_obligations` | refinement: `dec(transfer(enc a, enc b)) ≈_ε a ⊙ b` on declared ranges |
| `knob_binding` | how its parameters map to L4 knobs (forward + inverse model) |

**Innovation = adding a node.** A researcher who invents a new way to multiply with light, or a new memristor stack, writes a node (data file + small Lean proof file + simulator model). The compiler accepts it **only if**:
1. its Lean refinement proof checks (or a solver discharges the obligations on the declared ranges),
2. it passes model-level law checks and statistical validation; Monte Carlo is diagnostic evidence, not a universal error proof,
3. its knob binding passes L4 safety checks.

**Choosing a branch** is an optimization pass: for each abstract op, pick the node that minimizes cost (energy/latency/area) under the error budget and the available hardware. Users can also pin choices manually.

---

## 3. The Small World: physics simulator and verification gate

A self-contained, multi-fidelity simulator of light physics and memristor physics. **Nothing lowers to L4 unless the Small World says the program is physically possible and correct.**

### 3.1 Fidelity levels

| Level | Model | Used for |
|---|---|---|
| **SW-1 Analytical** | transfer matrices (optics), nodal analysis (circuits) | fast check of every compile |
| **SW-2 Compact dynamic** | ODEs: thermal RC (τ ≈ µs), memristor state `dw/dt = f(w, V)` (VTEAM-style), PCM crystallization kinetics, laser RIN, detector bandwidth; noise: shot, thermal (Johnson), RIN, device variability, drift | Monte Carlo error statistics, timing |
| **SW-3 Field-level (offline)** | FDTD/eigenmode (e.g. Meep), device-physics fits | calibrating SW-1/SW-2 model parameters, not run per compile |

Implementation: **JAX** (differentiable, so it can also *optimize* knobs when no closed-form inverse exists). Cross-validated against open tools: SAX / gdsfactory (photonic circuits), Meep (FDTD), CrossSim / NeuroSim (crossbars).

### 3.2 Physics laws checked automatically (invariants)

- **Energy conservation / passivity**: a passive optical network's matrix is a contraction (`‖S‖ ≤ 1`); a lossless network's matrix is unitary.
- **Reciprocity**: `S = Sᵀ` for reciprocal (non-magnetic) components.
- **Kirchhoff current and voltage laws** at every electrical node.
- **Non-negativity**: power ≥ 0, conductance ≥ 0, T ∈ [0, 1].
- **Causality / bandwidth**: no output changes faster than the device bandwidth allows.
- **Thermodynamics**: heater temperature limits; heat dissipates with the modelled time constant.
- **Noise floor**: signal-to-noise ratio ≥ what the required precision needs (shot-noise limit, ADC bits).

### 3.3 What a Small World run produces

- **PASS / FAIL** with the reason (e.g. "node 17: required T = 1.2 > 1, needs rescaling", or "SNR 18 dB < 24 dB required for 4-bit precision").
- Measured error distribution vs. the Lean-predicted bound (any mismatch = bug in a model or proof → flagged).
- Energy, latency, and per-op error breakdown.

---

## 4. L4: Control / Knob IR (engineering level)

Every knob is specified like a datasheet entry, with units enforced by type:

| Knob | Range | Resolution | Settling | Safety limits |
|---|---|---|---|---|
| `Heater_Voltage` | 0–5 V | DAC 12–16 bit | thermal τ ≈ 1–10 µs | max heater temperature, max power per heater, total chip power |
| `EO_Voltage` | ±V_range | DAC bits | ≈ ps–ns | breakdown voltage |
| `Attenuator_Current` | 0–20 mA | DAC bits | ≈ ns (carrier lifetime) | max current density, extra loss and phase coupling |
| `Ring_Tuning_Voltage` | 0–V_max | DAC bits | thermal τ | λ_res must stay inside its channel slot within the FSR |
| `Laser_Wavelength` / `Laser_Power` | channel grid / 0–P_max | — | ms (laser lock) | eye-safety / waveguide power handling, nonlinear threshold |
| `ReRAM_Pulse` {V, Δt, I_cc, N} | SET +1.5 V / RESET −1.8 V, ~50 ns | — | per pulse + verify read | breakdown voltage, endurance (write-cycle budget) |
| `PCM_Pulse` {P, Δt, N} | RESET: short/hot (~20 ns); SET: N × ~100 ns warm | — | per pulse | endurance, thermal budget |

Inverse models (parameter → knob), with their traps (all registered in each node's `knob_binding`):
- **Thermo-optic**: `Δφ = φ0 + k·V²` ⇒ `V = √(((Δφ − φ0) mod 2π)/k)`; minimum-power branch; your numbers check out (k = π/8 rad/V²).
- **Thermal crosstalk** is linear in power: `φ = C·P`, `P_i = V_i²/R_i` ⇒ solve `C·P = φ` subject to `P ≥ 0` and limits (LP / Z3); use `C⁻¹φ` only when the model is invertible and well-conditioned, then `V_i = √(P_i R_i)`.
- **Electro-optic**: `V = V_π·Δφ/π`.
- **Attenuator**: `I = α⁻¹(−ln T / L)` with calibrated monotone α(I); clamp at T_min; compensate the side-effect phase shift.
- **Microring**: δ² = (TΓ² − γ²)/(1 − T); choose one side of resonance (±δ) consistently; T_min = γ²/Γ² unless critically coupled.
- **ReRAM**: no reliable closed form. The compiler emits a **write-verify loop** with a tolerance, not a fixed pulse count.
- **PCM**: level lookup table; T and φ change **together**, so a PCM cell traces a 1-D curve in (T, φ), and the compiler accounts for both.

**Customization:** users can add knob models or override inverse models, but each override must pass the same checks (Lean or solver obligations + Small World + safe-operating-area).

---

## 5. L5: Timing and adaptive control

### 5.1 Physics-derived timing

Timescales span about 15 orders of magnitude, from optical propagation (ps) to drift (seconds to hours). Timing is **computed from physics, not guessed**:
- Exponential settling: a first-order modeled state with time constant τ needs `t ≥ max(0, τ · ln(initial_state_error / state_tolerance))` to be within tolerance, so **settling time follows from the required precision**.
- Propagation delay: `t = n_g · L / c` per waveguide segment (path-length matching for coherent interference).
- Pulse schedules: memristor/PCM pulse + verify-read + thermal cool-down between pulses.
- Conversion: DAC update rate, ADC conversion time, photodetector bandwidth.
- The schedule is solved as a constraint problem (Z3 / ILP): dependencies, settling, power limits over time, shared DACs/ADCs.

### 5.2 Disturbances modelled explicitly

| Disturbance | Model | Timescale |
|---|---|---|
| Ambient temperature drift | φ shift ∝ ΔT (thermo-optic coefficient) | s – min |
| Thermal crosstalk | coupling matrix C (+ dynamics) | µs |
| Laser wavelength / power drift, RIN | random walk + noise spectrum | ms – s |
| PCM resistance drift | `G(t) = G0 · (t/t0)^(−ν)` | s – days |
| ReRAM relaxation, read disturb | stochastic, state dependent | s – days |
| Aging / endurance wear | parameter shift per write cycle | long term |

### 5.3 Auto-adaptation (self-correcting runtime)

A closed loop running on the controller:
1. **Sense**: monitor photodiodes / tap couplers, pilot tones, periodic reference inputs ("calibration vectors"), memristor verify-reads.
2. **Estimate**: a Kalman filter (or similar state estimator) tracks drifting parameters (φ0, k, λ_res, G, temperature).
3. **Correct**: a controller (PID for simple loops, model-predictive control where coupled) updates knobs using the same verified inverse models from L4.
4. **Re-program** non-volatile cells (write-verify) when their drift exceeds the tolerance.
5. **Guard**: runtime monitors check the Small World invariants on live data. If the error budget is exceeded and cannot be corrected, raise an alarm or fall back to recalibration or digital execution.

Verification of the loop: stability and bounded error proven on the model (Lyapunov / bounded-input-bounded-output arguments in Lean for the linear parts), and stress-tested in the Small World with injected disturbances.

---

## 6. Backend stack

| Part | Recommendation |
|---|---|
| Math foundations, IR semantics, refinement proofs | **Lean4 + Mathlib** |
| Instance constraints (ranges, power, schedule, λ allocation) | **Z3** (polynomial), **dReal** (exp/sin/ln) |
| Compiler core (IR data structures, passes, Physics Tree registry) | **Rust**. Each pass emits a **certificate** that a small Lean/Z3 checker validates, so the whole Rust code doesn't need proofs |
| Small World simulator, calibration fitting | **Python + JAX** |
| Physics Tree nodes / device descriptions | declarative files (TOML/YAML or small DSL) + Lean proof file + simulator model per node |
| Runtime adaptive controller | Rust (or C on the chip controller), generated from L5 |

---

## 7. Roadmap

**Phase 0: Math foundation (Lean4)**
Number encodings, units, ranges, approximate-operation semantics for +, −, ×, ÷, error composition, approximation theorems for exp/sin/1/x/sqrt, structural primitives (fanout with power split, convert).

**Phase 1: L1/L2 IR + reference interpreters**
Text format, range analysis, scaling insertion, approximation lowering, certified error budget output.

**Phase 2: Physics Tree + first branches**
Node format and registry; Lean refinement proofs for: MZI multiply, coherent add, balanced-detector subtract, attenuator multiply, Kirchhoff add, memristor multiply, constant-divide, feedback divide. Branch-selection pass.

**Phase 3: Small World**
SW-1 analytical + law checker; SW-2 compact dynamic models with noise; Monte Carlo verification; cross-checks against SAX/Meep/CrossSim.

**Phase 4: L4 knobs**
Datasheet-level knob specs, inverse models, crosstalk compensation, safe-operating-area checks, write-verify programs, user overrides with re-verification.

**Phase 5: L5 timing + adaptive runtime**
Physics-derived scheduling, disturbance models, Kalman + controller loop, runtime monitors, stress tests in the Small World.

**Phase 6: Frontends + hardware-in-the-loop**
ONNX/StableHLO/own DSL import, calibration from real measurements.

---

## 8. Open decisions

1. **Compiler core language**: Rust chosen for the executable MVP; independent exact certificate checking is implemented. Full Lean certificate-refinement linkage remains open.
2. **First branch**: static-weight thermo-optic MZI chosen and demonstrated at model level. Additional photonic branches and memristors follow after the verification bridge.
3. **Repo**: this repository, `photonics-computing`; executable/formal CI definitions are included.
