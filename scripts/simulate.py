#!/usr/bin/env python3
"""SW-1 analytical validation of an already checked MZI bundle.

Finite sampling is diagnostic evidence, not a universal or probabilistic proof.
The model is lossless and real coherent amplitude with bounded phase/input error.
"""

import argparse
import json
import math
from pathlib import Path
import random
from check_certificate import verify, Rejected, require


def simulate(bundle, samples=1000, seed=793):
    require(0 <= samples <= 1_000_000, "sample count outside [0, 1000000]")
    _, p, digest = verify(bundle)
    require(p is not None, "simulation requires a physical certificate")
    rng = random.Random(seed)
    inp, weight, phase = p["input"], float(p["weight"]), p["phase"]
    lo, hi, error = float(inp.interval.lo), float(inp.interval.hi), float(inp.error)
    pl, ph = float(phase.lo), float(phase.hi)
    vectors = [
        (x, e, theta)
        for x in (lo, hi, 0.0 if lo <= 0 <= hi else (lo + hi) / 2)
        for e in (-error, error)
        for theta in (pl, ph, (pl + ph) / 2)
    ]
    vectors += [
        (rng.uniform(lo, hi), rng.uniform(-error, error), rng.uniform(pl, ph))
        for _ in range(samples)
    ]
    worst = energy = 0.0
    for x, perturbation, theta in vectors:
        field = x + perturbation
        bar = math.cos(theta / 2) * field
        cross = math.sin(theta / 2) * field
        residual = abs(bar * bar + cross * cross - field * field)
        energy = max(energy, residual)
        worst = max(worst, abs(bar - weight * x))
    bound = float(p["total_error"])
    require(worst <= bound + 1e-12, "sampled error violates certificate")
    require(energy <= 1e-12, "energy conservation violated")
    return {
        "status": "PASS",
        "fidelity": "SW-1 analytical",
        "program_sha256": digest,
        "seed": seed,
        "vectors": len(vectors),
        "dac_code": p["code"],
        "voltage_V": float(p["voltage"]),
        "maximum_absolute_error": worst,
        "checked_error_bound": bound,
        "maximum_energy_residual": energy,
        "scope": "illustrative calibrated model; finite samples are not a proof; no hardware writes",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=793)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        text = json.dumps(simulate(args.bundle, args.samples, args.seed), indent=2) + "\n"
        if args.report:
            args.report.write_text(text)
        print(text, end="")
    except (Rejected, OSError, ValueError) as e:
        parser.exit(1, f"REJECT: {e}\n")


if __name__ == "__main__":
    main()
