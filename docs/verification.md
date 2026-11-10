# Verification and trust boundaries

## Status of this implementation

The executable compiler, independent checker, and SW-1 simulation have been run
locally. The formal Lean changes have **not** been compiled locally. The sandbox
has no Lean/Lake toolchain and its network allowlist blocks the release-asset host.
A CI formal job is provided but has not been observed running in this session.
No assertion of a successful Lean build is made.

There are three intentionally different kinds of evidence:

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Independent exact-rational checker | Source-derived arithmetic bounds, physical-domain checks, DAC binding, conservative MZI cosine/error enclosure under the named model | Correctness of Python itself, calibration validity, real-device safety |
| Lean theorem scripts and generated numeric obligations | Once `lake build` and generated-file checking pass: stated mathematical theorems and concrete rational inequalities | A proved parser/compiler/checker or complete source-to-hardware refinement |
| SW-1 sampled simulation | Reproducible model diagnostics, observed bounded error, sampled energy residual | Universal input coverage, tail probabilities, fabrication accuracy |

A checker `PASS` means the independently recomputed certificate is consistent with
the program and model assumptions. It does not mean “Lean executed” or “hardware
is safe.” The CLI reports Lean's unexecuted status explicitly.

## Arithmetic foundation

`Core/Bounded.lean` introduces per-device input/output domains and a local error
specification that only applies inside those domains. Composition requires actual
operand membership, so an input uncertainty cannot be ignored at the domain edge.
The operation-specific theorems cover +, −, ×, ÷ with bounded input uncertainty.

`Core/Semantics.lean` retains the original expression-tree semantics and global
`Realization` theorem for compatibility/research. Its globally quantified operation
contracts are mathematical idealizations, not the contract used by the executable
physical branch. Constants in this legacy tree remain exact. The executable SSA
IR supports uncertain constants; its independent checker and bounded composition
model account for them. There is not yet a formal translation theorem between
these two syntax representations.

`Core/Range.lean` now uses sign-preserving endpoint product, scaling, and reciprocal
bounds. The zero-crossing reciprocal fallback cannot be certified by its safety
premise. No unsafe denominator is accepted merely because Lean's totalized division
assigns a value to division by zero.

## MZI branch

The trusted physical assumption is:

```text
theta ∈ k V² + offset ± bounded_phase_residual
bar_output = cos(theta/2) × actual_input
```

Within that model, exact interval arithmetic encloses cosine using a Taylor
polynomial. Degree 33 has the same polynomial as degree 32 because its odd
coefficient is zero. Lagrange's remainder is bounded by `|theta/2|^34 / 34!` since
all derivatives of cosine have absolute value at most one.

The Rust implementation uses integer-directed rounding on a fixed 10^-9 grid.
Its supported domain keeps intermediate fixed-point products inside i128.
The independent Python implementation instead uses exact, arbitrarily large
fractions and checks that the submitted enclosure contains its recomputed bound.
It does not call Rust or reuse Rust's fixed-point implementation.

`Physics/Control.lean` states the final MZI error composition theorem conditional
on a bound on the cosine/weight mismatch. **The Taylor-enclosure implementation is
not yet proved in Lean or connected to that premise by a kernel-checked bridge.**
The exported `Certificate.lean` checks numeric inequalities only; it is not a proof
of this missing bridge. This is the main remaining formal-certificate task.

## Explicit omissions

- No real-chip calibration measurements or uncertainty identification.
- No complex input-state graph/phase-reference tracking; the executable example
  uses real signed coherent amplitude and ideal phase matching.
- No optical insertion loss, detector/ADC response, shot/RIN/thermal noise,
  nonlinear response, or stochastic tail guarantee.
- No voltage slew, thermal settling, heater resistance/power limit, or controller.
- No general placement/routing, fanout accounting, storage, or physical DAG scheduling.
- No compiler approximation pass for exp/sin/sqrt and no memristor lowering yet.
- No Z3/dReal integration. Exact rational checks handle the implemented instances;
  future solver timeout/unknown/δ-sat policies still need design and validation.
- No hardware I/O. Every control file is a model-level artifact only.

The `phase_error` field must bound **all** residual phase effects assumed for a
single invocation; it is not automatically derived from noise or temperature data.
Sampling that interval uniformly is a stress-test distribution, not a claim that
real noise is uniform or bounded.

## Fail-closed behavior

Compilation returns a nonzero exit status on malformed input, unsupported graph,
unrepresentable rational arithmetic, unsafe divisor, insufficient precision,
out-of-domain values, or saturation. No physical control artifact is emitted
before model checks finish. Bundle verification rejects incomplete files, altered
claims, mismatched expected source/calibration, duplicate claims, and inconsistent
DAC/phase/error bindings. A corrupt bundle must never be used as hardware input.

For hostile external certificates, execution should additionally be sandboxed
with time/memory limits. The current limits bound source size and graph size but
are not a general-purpose resource-isolation mechanism.
