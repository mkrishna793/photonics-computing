# Lumiris v1 formats and contracts

## Program grammar

UTF-8 plain text, one statement per line. Blank lines and `#` comments are ignored.
Numbers are signed integers or integer fractions `n/d`; decimals, exponents, NaN,
and infinity are rejected. Canonical certificate numbers are reduced fractions.

```text
lumiris 1
input NAME LO HI ERROR
const NAME VALUE ERROR
add NAME LEFT RIGHT LOCAL_ERROR INPUT_LO INPUT_HI OUTPUT_LO OUTPUT_HI
sub NAME LEFT RIGHT LOCAL_ERROR INPUT_LO INPUT_HI OUTPUT_LO OUTPUT_HI
mul NAME LEFT RIGHT LOCAL_ERROR INPUT_LO INPUT_HI OUTPUT_LO OUTPUT_HI
div NAME LEFT RIGHT LOCAL_ERROR INPUT_LO INPUT_HI OUTPUT_LO OUTPUT_HI
output NAME TOLERANCE
```

- `NAME` is an ASCII letter followed by ASCII letters/digits/underscores, at most
  64 characters. Each name is assigned exactly once.
- Operands must refer to previous nodes. Cycles and forward references are rejected.
- There is exactly one `output`, and it is the final statement.
- Error quantities and tolerance are nonnegative absolute bounds in decoded units.
- Both operands share the supplied physical input interval in v1. A later schema
  may support distinct left/right domains and encoding tags.
- The graph has at most 256 nodes and the file has at most 64 KiB.
- Rust rationals use reduced signed 64-bit numerators, positive 64-bit denominators,
  and exact 128-bit intermediates. An unrepresentable result is an explicit error;
  it is never silently rounded, wrapped, or accepted as a certificate.

## Semantics

For every node, maintain an ideal interval `R` and an absolute error `e`:

```text
ideal ∈ R
|actual − ideal| ≤ e
actual ∈ [R.lo − e, R.hi + e]
```

Inputs describe the allowed ideal external values and conversion uncertainty.
Constants can also have nonzero programming/reference uncertainty.

For a binary node, first check that **both expanded operand intervals** lie in its
physical input domain. Its local device contract is:

```text
|transfer(actual_a, actual_b) − (actual_a op actual_b)| ≤ local_error
```

The ideal interval is computed from endpoint interval arithmetic. Product bounds
use all four endpoint products, preserving positive/negative signs. Division uses
the reciprocal interval and requires that it not touch zero.

Let `Ma = max(|Ra.lo|, |Ra.hi|)` and similarly `Mb`. Composed errors are:

```text
add/sub: ea + eb + local
mul:     ea Mb + Ma eb + ea eb + local
div:     (ea Mb + Ma eb)/(m (m − eb)) + local
```

Here `m` is the minimum absolute denominator over its ideal interval. Division
requires **`eb < m`**, not merely a nominal nonzero denominator.

Finally, the expanded result interval must lie in the declared output domain, and
the selected output's error must not exceed the requested tolerance.

No independence assumption is used. Reused inputs can be correlated; interval
bounds remain conservative. Sharing a node does not currently model physical
fanout, routing, scheduling, or storage costs. An arithmetic-only certificate is
conditional on the declared local device contracts: it does not prove that an
unregistered physical mechanism implements them.

## Device schema

```text
lumiris-mzi 1
id MODEL_ID
voltage_max RATIONAL
# The remaining fields are required; unknown/duplicate fields are rejected.
dac_bits INTEGER
phase_per_v2 RATIONAL
phase_offset RATIONAL
phase_error RATIONAL
input_limit RATIONAL
```

Supported model domain:

- `2 ≤ dac_bits ≤ 16`
- `0 < voltage_max ≤ 10` V
- `0 < phase_per_v2 ≤ 1` rad/V²
- `|phase_offset| ≤ 1` rad
- `0 ≤ phase_error ≤ 1` rad
- `0 < input_limit ≤ 1`, normalized coherent field amplitude

These are software-supported bounds, **not universal safe chip limits**. A real
device needs calibrated voltage, thermal, power, endurance, and timing constraints.

The concrete branch requires exactly one input, one error-free static weight in
`[-1,1]`, and their multiply, selected as output. Either operand order is accepted.
Unsupported graphs are rejected rather than silently assigned the wrong mechanism.

```text
V = voltage_max × code/(2^bits − 1)
phase_nominal = phase_per_v2 × V² + phase_offset
phase_actual ∈ [phase_nominal − phase_error, phase_nominal + phase_error]
t = cos(phase_actual/2)
output_actual = t × input_actual
```

The positive-voltage, non-wrapped inverse branch proposes a nearby DAC code using
`acos` and `sqrt`. At most three adjacent codes are checked. This is not a globally
optimal branch search, and may conservatively reject other feasible settings.
Acceptance does not depend on the floating-point inverse's accuracy.

A directed-rounded degree-32 Taylor enclosure with order-34 absolute remainder
bounds `t`, for `|phase/2| ≤ 8`. The backend checks every proposed code against its
finite voltage range and input amplitude limit. The independent checker recomputes
the enclosure using arbitrary-precision rational operations without the backend's
fixed-point rounding.

With weight mismatch bounded by `delta`, ideal input magnitude `M`, and input
uncertainty `ein`:

```text
physical local error ≤ delta × (M + ein)
physical total error ≤ |weight| × ein + delta × (M + ein)
```

The physical local bound must fit the multiplication node's local allowance. The
total must fit both the arithmetic certificate and final output tolerance.

## Certificate bundle

```text
program.lumi       exact source copy
arithmetic.cert    per-node ideal ranges/errors
device.mzi         optional exact device-model copy
physical.cert      optional MZI control and error claims
Certificate.lean   generated numeric inequalities, when requested
simulation.json    diagnostic report, when requested
verification.json  independent-check report, when requested
```

`arithmetic.cert` starts with `lumiris-certificate 1`, then contains one ordered
`node NAME LO HI ERROR` per source node and a final `output NAME TOLERANCE`.

`physical.cert` starts with `lumiris-mzi-certificate 1`, followed by required fields:
`model`, `code`, `voltage`, `phase LO HI`, `transmission LO HI`, `weight_error`,
`local_error`, and `total_error`. Unknown, missing, or duplicated claims fail.

Verification recomputes the graph and numerical results. Supply `--source` and
`--device` to bind a bundle to the originally requested files. A consistent bundle
by itself cannot establish that it is the program/calibration the caller intended.

Compilation refuses existing output directories. Failed analysis or physical
lowering emits no bundle. Filesystem failure during emission can leave a partial
bundle; missing/inconsistent artifacts must never be treated as verification success.
