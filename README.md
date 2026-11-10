# 💡 Lumiris: Photonic & Analog Computing Compiler

**A formally verified, physics-aware compiler and execution platform for light-speed optical meshes and memristor crossbars.**

[![Verify Lumiris](https://github.com/mkrishna793/photonics-computing/actions/workflows/ci.yml/badge.svg)](https://github.com/mkrishna793/photonics-computing/actions/workflows/ci.yml)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Tests: 50 Passing](https://img.shields.io/badge/Tests-50%2F50%20passing-brightgreen.svg)](tests/)
[![Formal: Lean 4](https://img.shields.io/badge/Formal%20Verification-Lean%204-purple.svg)](Lean-Semantics/lean/)

---

## 🌟 The Big Picture: Why Compute with Light?

Modern digital computers push billions of electrons through tiny silicon wires. But as artificial intelligence and scientific computing scale, electronic computing is running straight into a physical wall: **heat and resistance**. Every time a transistor switches and electrons move through metal traces, energy is lost as heat, capping clock speeds and consuming megawatts in data centers.

**Photonics takes a fundamentally different path.**

Instead of moving electrons, we compute using photons—particles of light travelling through microscopic silicon waveguides. 
- **Passive Matrix Multiplication at the Speed of Light**: When light waves pass through a grid of optical beam splitters and phase shifters (a Mach-Zehnder Interferometer mesh), they interfere with one another. This interference naturally computes matrix multiplications ($Y = W \cdot X$) essentially instantaneously (in picoseconds), with virtually zero dynamic power consumed by the calculation itself.
- **Wavelength Multiplexing (WDM)**: Dozens of independent calculations can travel down the exact same physical waveguide simultaneously on different colors (wavelengths) of light without interfering.

---

## 🛑 The Hard Truth: The Dirty Secret of Analog Hardware

If computing with light is so fast and energy-efficient, why isn't every data center running on optical chips today?

Because **analog physics is messy and unforgiving**:

1. **Thermal Crosstalk**: To configure an optical gate, tiny microheaters change the temperature of silicon to alter its refractive index and delay the light. But heat doesn't stay in one place. It diffuses through the silicon substrate into neighboring waveguides. Tuning one phase shifter unintentionally throws off all the shifters around it.
2. **Finite Precision & Saturation**: Unlike digital computers that have 64-bit IEEE floating-point numbers, analog hardware is limited by Digital-to-Analog Converters (DACs) with 8 to 14 bits of precision. If a calculated voltage exceeds the DAC range, the signal clips (saturates). If a calculation accidentally divides by a number close to zero, physical voltages spike and can destroy sensitive components.
3. **No Native Non-Linearities**: Light passes through passive optical meshes linearly. But neural networks and real-world algorithms require non-linear functions (like $\tanh$, $\text{sigmoid}$, $\exp$, or $\sin$). Creating clean, controllable optical non-linearities on a chip is notoriously difficult.
4. **The Trust Deficit**: In digital software, bitwise reproducibility is taken for granted. In analog hardware, noise, temperature drift, and fabrication imperfections cause errors. Without rigorous error tracking, you never know if your analog chip is returning a correct result or pure noise.

---

## ⚡ What is Lumiris?

**Lumiris is a compiler built specifically to tame this messy physics.**

It acts as the bridge between clean mathematical code and raw physical actuators (heaters, DACs, phase shifters, and memristor cells). Rather than treating analog chips like unpredictable black boxes, Lumiris compiles mathematical expressions with **strict mathematical and physical error bounds**, pre-compensates for physical crosstalk, and generates independently verifiable certificates.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                    Mathematical Model                   │
                  │         Tensors, Matrix Multiplications, Activations    │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                 L1 Transcendental Synthesis             │
                  │      Chebyshev Minimax Polynomials & Padé Approximants  │
                  │           Certified Error Bounds (< 10⁻³) in Horner Form │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                 L2 Bounded Interval SSA IR              │
                  │   Tracks tight [min, max] ranges for every node         │
                  │   Guarantees zero saturation & rejects zero-divisors    │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                     ┌─────────────────────────┴─────────────────────────┐
                     ▼                                                   ▼
       ┌───────────────────────────┐                       ┌───────────────────────────┐
       │   Optical Mesh Backend    │                       │ Memristor Crossbar Backend│
       │  • SVD (A = U Σ V†)       │                       │  • Differential Pairs     │
       │  • Reck/Clements MZI Grid │                       │    (W = α(G⁺ - G⁻))       │
       │  • Thermal Crosstalk      │                       │  • Wire IR-Drop Analysis  │
       │    Matrix Inversion       │                       │  • Conductance Drift Model│
       └─────────────┬─────────────┘                       └─────────────┬─────────────┘
                     │                                                   │
                     └─────────────────────────┬─────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │          Dual-Verification Certificate Auditor          │
                  │   Cryptographically signed exact-rational proof bundle  │
                  │   Audited independently by Python / Lean 4 Mathlib      │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                   Physical Actuators                    │
                  │        DAC Integer Codes, Heater Voltages (V), G        │
                  └─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Key Capabilities

### 1. Active Thermal Crosstalk Inversion
Lumiris models the thermal coupling matrix ($K_{i,j} \propto \frac{1}{\text{dist}(i,j)}$) of on-chip phase heaters. When compiling an optical unitary matrix, Lumiris inverts this coupling matrix:
$$\vec{P}_{\text{applied}} = K^{-1} \vec{P}_{\text{target}}$$
This ensures that the true target phase shifts are achieved in silicon, even when microheaters are tightly packed on a photonic integrated circuit (PIC).

### 2. Certified Non-Linear Function Lowering (L1)
Because optics cannot natively compute arbitrary functions like $\exp(x)$ or $\tanh(x)$, Lumiris synthesizes **Chebyshev minimax polynomials** and Padé rational approximants. It compiles them into an optimized Horner evaluation form with certified truncation error bounds, allowing complex mathematical models to run on linear analog cores.

### 3. Fail-Closed Interval Safety (SSA IR)
Every intermediate value in Lumiris carries an interval range $[a, b]$ and an absolute error budget $\delta$. 
- If an operation could ever divide by zero or an interval that encloses zero, **the compiler fails closed at compile time**.
- If a calculation could exceed the physical voltage or conductance dynamic range, the compiler halts before any damage can occur.

### 4. Dual-Verification & Lean 4 Formal Proofs
You don't have to trust the compiler. When Lumiris compiles a program, it emits an exact-rational certificate (`verification.json` and `Certificate.lean`). An independent verification tool audits the arithmetic and physical constraints using pure exact fractions and SHA-256 digests. Crucial properties (like unitary energy conservation $M^\dagger M = I$ and DAC monotonicity) are verified using the **Lean 4** theorem prover.

### 5. Multi-Hardware Backend: Photonics & Memristors
Lumiris is not tied to a single physical device:
- **Silicon Photonics**: Singular Value Decomposition ($A = U \Sigma V^\dagger$) mapped onto Reck or Clements MZI meshes, microring resonators (MRRs), and PIN photodetectors.
- **Analog In-Memory Memristors (ReRAM)**: Differential conductance crossbars ($W = \alpha(G^+ - G^-)$) with realistic wire resistance ($IR$ drops), DAC quantization, and conductance retention drift.

---

## 🚀 For Researchers & Hardware Startups

If you are a university lab or a deep-tech startup building next-generation analog or photonic AI accelerators:

- **Don't build your compiler from scratch**: You can adapt Lumiris to your specific hardware. Simply provide your calibrated device characteristics (phase vs. voltage curves, heater resistance, crosstalk matrix, DAC resolution, and waveguide insertion losses).
- **Plug-and-Play Benchmarking**: Use the included optical simulation engine to model realistic signal-to-noise ratio (SNR), Effective Number of Bits (ENOB), optical time-of-flight latency (in picoseconds), and energy efficiency (fJ/MAC) before taping out silicon.

---

## 🏁 Quickstart

### 1. Installation
Clone the repository and install dependencies in a virtual environment:
```bash
git clone https://github.com/mkrishna793/photonics-computing.git
cd photonics-computing

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Verification Test Suite
Lumiris comes with a comprehensive suite of 50 unit and integration tests:
```bash
scripts/test.sh
```

### 3. Run the End-to-End MZI Compilation Demo
Compile a high-level bounded arithmetic specification down to physical DAC codes, verify its mathematical certificate, and simulate optical propagation:
```bash
scripts/demo.sh artifacts/demo-run
```

---

## 💻 Python Example: Compiling to a Photonic Mesh

```python
import numpy as np
from photonics import (
    OpticalMeshBackend,
    OpticalTensorCore,
    approximate_transcendental,
    Interval
)

# 1. Define an arbitrary weight matrix (e.g., a neural layer or linear transform)
W = np.array([
    [ 0.45, -0.22,  0.78,  0.11],
    [-0.15,  0.64, -0.33,  0.52],
    [ 0.81, -0.40,  0.19, -0.67],
    [-0.30,  0.55, -0.85,  0.24]
])

# 2. Lower the matrix to an optical MZI mesh (SVD + Clements/Reck decomposition)
compiler = OpticalMeshBackend()
bundle = compiler.lower_gemm(W, node_name="layer1_gemm")

print(f"Total MZIs required: {bundle.control_registers['total_mzis']}")
print(f"Physical error bound: {bundle.physical_error_bound:.6e}")

# 3. Simulate coherent optical propagation with thermal crosstalk compensation
core = OpticalTensorCore(n_channels=4, enable_thermal_crosstalk=True, precompensate_crosstalk=True)
core.set_general_matrix(W)

# Forward pass with an input optical field vector
x = np.array([0.5, 0.2, -0.3, 0.4])
result = core.forward(x)

print(f"Time-of-Flight Latency: {result.time_of_flight_ps:.2f} ps")
print(f"Effective Number of Bits (ENOB): {result.enob_bits:.1f} bits")
print(f"Energy consumed: {result.energy_consumed_fJ:.2f} fJ")

# 4. Synthesize a non-linear activation function (Sigmoid) with proven error < 1e-3
sig_poly = approximate_transcendental("sigmoid", Interval(-2.0, 2.0), target_tolerance=1e-3)
print(f"Chebyshev degree {sig_poly.degree} polynomial max error: {sig_poly.max_truncation_error:.6e}")
```

---

## 📂 Repository Structure

```text
photonics-computing/
├── src/photonics/
│   ├── compiler/             # Lumiris SSA IR, Chebyshev approximations, Lowering, Certificates
│   │   ├── ir.py             # SSA interval arithmetic, physical encodings, domain checks
│   │   ├── transcendental.py # Chebyshev minimax & Padé polynomial expansions in Horner form
│   │   ├── lowering.py       # SVD optical mesh & differential memristor backends
│   │   └── certificate.py    # Independent Fraction auditor & cryptographic SHA-256 signatures
│   ├── core/
│   │   └── unitary.py        # Reck & Clements unitary decompositions into Givens rotations
│   ├── devices/
│   │   ├── mzi.py            # Mach-Zehnder Interferometers & Thermal Crosstalk Inversion
│   │   ├── ring_resonator.py # Micro-Ring Resonators (FSR, Q-factor, spectral weighting)
│   │   └── memristor.py      # Differential ReRAM crossbars, IR drops, retention drift
│   ├── simulation/
│   │   └── optical_engine.py # OpticalTensorCore, complex field propagation, PIN detectors
│   └── benchmarks/
│       └── benchmark_suite.py# Photonic vs Electronic comparative energy/latency profiling
├── tests/                    # 50 unit and integration tests (passing in < 1s)
├── scripts/                  # CI verification, demo runners, and Lean formal proof checkers
├── Lean-Semantics/
│   ├── rust/                 # Pure, dependency-free Rust reference compiler
│   └── lean/                 # Lean 4 / Mathlib formal verification proofs
├── devices/                  # Calibrated hardware target configurations (JSON)
├── examples/                 # Example high-level Lumiris programs (.lumi)
└── requirements.txt          # Python dependencies
```

---

## 📜 License

This project is licensed under the AGPLv3. If you wish to use this project in a closed-source commercial application without complying with the AGPLv3 terms, please contact the author to purchase a commercial license.

For the full legal text of the license, see [LICENSE](LICENSE).
