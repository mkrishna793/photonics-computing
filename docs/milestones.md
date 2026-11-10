# Implementation checkpoints — 2026-11-10

These milestones are the review's three incremental checkpoints, not the full
seven-phase research roadmap. “Implemented” does not imply “kernel-validated.”

## Milestone 1 — Trustworthy project/build foundation

Implemented:
- Normalized Lean and Rust source/configuration/manifest locations.
- Restored the missing physics-laws module and removed duplicated draft fragments.
- Made all 11 maintained Lean modules reachable from the default library.
- Repaired the draft triangle-bound proof and revised the MZI matrix proof.
- Added the repository audit, ignore rules, README, and executable/formal CI jobs.
- Confirmed Rust targets build and execute offline with no third-party crates.

**Open acceptance gate:** run and pass the pinned Lean/Mathlib build. The sandbox
cannot install that toolchain through its permitted network endpoints. Static
import validation passes, but is not a proof-compilation result.

## Milestone 2 — Bounded software core

Implemented and executable-tested:
- Versioned SSA text IR and exact rational reference interpreter.
- Tight sign-preserving interval arithmetic and nonzero denominator checks.
- Per-node local error, actual-input-domain and expanded-output checks.
- Uncertainty for both external inputs and constants.
- Independent source-derived certificate checking and tampering rejection.
- Exported Lean rational obligations and documented certificate/trust format.
- Bounded per-device composition theorem scripts for all four operations.

Deliberate scope limits:
- The Rust implementation rejects rational-capacity overflow; it does not claim
  arbitrary-precision compilation. Python checking uses arbitrary precision.
- Generic device-local errors remain explicit assumptions until a supported
  physical branch discharges them.
- Parser/SSA-to-Lean semantic refinement is not yet a proved translation.

## Milestone 3 — End-to-end MZI model demonstration

Implemented and executable-tested:
- One live input × one exact configured weight, including negative weights.
- Explicit illustrative device calibration and safe parameter limits.
- Positive-branch phase/heater inversion, nearest-code candidate search, finite DAC.
- Independent exact cosine enclosure, calibration error, and composed output bound.
- SW-1 analytical simulator with boundary vectors, seeded perturbations, and
  energy conservation diagnostics.
- One-command compilation/check/simulation, plus optional formal validation.
- Useful rejection of unsupported graphs, infeasible precision, and model limits.

Reproduced default example:
- code 1891; voltage ≈ 2.308913309 V;
- checked physical error ≤ 0.0004005385444;
- 1018 simulation vectors; observed maximum ≈ 0.0003988068894;
- energy residual ≤ 2.23×10^-16.

**Open formal acceptance gates:** observe the Lean CI result and prove/link the
Taylor-enclosure checker to the MZI theorem. The existing exported numeric
obligations are not that proof. The executable milestone is demonstrated; a fully
Lean-certified compiler milestone must not be marked complete yet.

## Validation performed here

- 12 Rust unit tests: passed.
- 23 Python integration/property/adversarial tests: passed.
- 100 randomized arithmetic programs × 10 perturbed vectors: included in tests.
- 200 randomized phase intervals × 3 cosine samples: included in tests.
- End-to-end demo/checker/SW-1 run: passed.
- Layout/import/pin audit: passed.
- Lean kernel validation: **not run**; CI configured, result pending.

## Next work, in order

1. Run the formal CI gate and resolve any Lean/Mathlib elaboration issues.
2. Prove the certificate/Taylor checker bridge and source-IR semantic translation.
3. Add explicit encoding tags and unit-typed device schemas across Rust/Lean.
4. Add insertion loss/detection and measured calibration datasets.
5. Generalize the device registry/selection beyond the single concrete branch.
6. Proceed to timing, dynamics, and additional photonic/memristive mechanisms.
