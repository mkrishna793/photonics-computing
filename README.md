# Lumiris — bounded arithmetic to photonic controls

Lumiris is an early compiler foundation for photonic and memristive computing.
The executable MVP compiles **bounded, straight-line real arithmetic** and lowers
one static-weight multiplication to an illustrative thermo-optic MZI model.
It does **not** compile arbitrary mathematics, program a real chip, or implement
an adaptive runtime yet.

## What works

- A Rust compiler/reference interpreter with no third-party dependencies.
- Versioned textual SSA IR with exact rational constants and explicit uncertainty.
- Tight interval arithmetic, per-node physical input/output contracts, and composed
  absolute-error budgets for addition, subtraction, multiplication, and division.
- Fail-closed rejection of zero/uncertain divisors, saturation, invalid domains,
  arithmetic overflow, malformed programs, and unsupported device mappings.
- MZI static-weight selection, heater inversion, finite DAC quantization, bounded
  calibration error, and directed-rounding cosine enclosures.
- A separate Python checker using arbitrary-precision `Fraction` arithmetic. It
  recomputes certificates from the source and device description, rather than
  trusting Rust's decisions or its floating-point inverse calculation.
- SW-1 analytical simulation with boundary vectors, seeded disturbances, and
  energy-conservation checks.
- A repaired Lean project layout, bounded device-contract theorem scripts, and
  generated kernel-checkable **numeric obligations**. See the verification caveat below.

## Requirements

- Rust/Cargo **1.82+**; current stable recommended.
- Python **3.11+**, standard library only.
- Optional formal validation: elan, the pinned Lean **4.35.0**, and Mathlib.
  Initial Lean dependency/toolchain/cache downloads require network access.

The Rust compiler, checker, and simulator work offline after Rust is installed.
There is no Z3/JAX installation requirement for this deliberately small MVP:
exact rational inequalities suffice here. Those integrations remain future work.

## Run the complete executable demonstration

From the repository root:

```bash
scripts/demo.sh
```

The output directory must not already exist. Choose a new one for another run:

```bash
scripts/demo.sh artifacts/another-run
```

Pipeline:

```text
examples/mzi-scale.lumi + devices/demo-mzi.mzi
  → Rust bounded analysis and MZI lowering
  → source-bound arithmetic and physical certificate bundle
  → independent exact-rational checker
  → generated Lean numeric obligations
  → analytical simulation and JSON report
```

To also build the formal library and check the generated numeric obligations:

```bash
# First-time Mathlib preparation:
(cd Lean-Semantics/lean && lake exe cache get)

scripts/demo.sh artifacts/with-lean --lean
# Or check an existing demo:
scripts/check_lean.sh artifacts/mzi-demo
```

**Formal-validation status:** Lean could not be executed in the development
sandbox: Lean/Lake were absent and toolchain release-asset downloads were blocked.
The formal library changes and generated obligations are therefore **not locally
kernel-validated**. CI includes a required-to-pass formal build job, but its result
must be observed before calling the formal milestone complete.

Even after that job passes, the generated numeric obligations do **not** constitute
a complete Lean proof of the parser, certificate checker, Taylor-enclosure algorithm,
or source-to-hardware compilation. Those trust boundaries are documented in
[docs/verification.md](docs/verification.md). No hardware guarantee is claimed.

## Example program

```text
lumiris 1
input x -9/10 9/10 1/10000
const weight 1/2 0
mul y weight x 1/1000 -1 1 -1 1
output y 11/10000
```

This asks for `y = 0.5 × x` with bounded input conversion uncertainty, a per-op
local-error allowance, and explicit device operating domains.
See [docs/ir.md](docs/ir.md) for the complete grammar and mathematical contracts.

The illustrative calibration gives these reproducible results:

| Quantity | Result |
|---|---:|
| DAC code | 1891 of 4095 |
| Heater voltage | approximately 2.308913309 V |
| Ideal output interval | [−0.45, 0.45] |
| Arithmetic contract bound | 0.00105 |
| Independently checked physical-model bound | 0.0004005385444 |
| Maximum sampled error, default seed | approximately 0.0003988068894 |
| Sample vectors | 1018 |

The calibrated phase coefficient is a rational model parameter, **not an assertion
that a particular fabricated heater has that coefficient**. The device file is
illustrative and is not hardware authorization.

## Other commands

```bash
# Exact reference interpretation (rational result):
cargo run --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml -- \
  eval examples/mzi-scale.lumi x=1/2
# 1/4

# Arithmetic-only graph, including a safe nonlinear denominator:
cargo run --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml -- \
  compile examples/safe-division.lumi artifacts/division
python3 scripts/check_certificate.py artifacts/division \
  --source examples/safe-division.lumi

# Expected rejection, nonzero exit status, no compilation bundle:
cargo run --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml -- \
  compile examples/reject-zero-divisor.lumi artifacts/rejected
```

## Tests

```bash
scripts/test.sh
```

This runs the repository-layout/import audit, Rust unit tests, and Python
integration/property/adversarial tests. Coverage includes certificate tampering,
calibration mismatch, unsupported models, positive and negative static weights,
precision failure, output saturation, unsafe division, input domains, and exact
reference evaluation. Randomized tests compare both implementations and check
composed bounds against perturbed arithmetic.

The layout audit is not a substitute for `lake build`. CI separates executable
validation from formal validation; a passing executable job alone is insufficient
for claiming all formal proofs check.

## Repository map

```text
Lean-Semantics/
  lean/                   Lean/Mathlib project, all modules reachable from Lumiris
    Lumiris/Core/         units, ranges, encodings, semantics, bounded contracts
    Lumiris/Physics/      laws, photonic transfer models, DAC and error theorems
  rust/                   dependency-free compiler and exact interpreter
    src/rational.rs       checked rational and tight interval arithmetic
    src/lib.rs            parser, SSA analysis, error contracts, reference semantics
    src/mzi.rs            calibrated MZI branch and certificate generation
    src/main.rs           CLI and artifact emission
scripts/                  independent checker, SW-1 simulator, demo/test/formal scripts
examples/                 accepted and deliberately rejected input programs
devices/                  illustrative versioned device model
tests/                    cross-implementation and adversarial tests
docs/                     formats, verification boundaries, milestone status
```

For the long-term vision, see [the plan](photonic-memristor-compiler-plan.md).
For what has actually been implemented and what remains, see
[docs/milestones.md](docs/milestones.md).
