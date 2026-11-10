#!/usr/bin/env python3
"""Independent exact-rational checker. Does not invoke or trust the Rust compiler.

Arithmetic/device assumptions are read from source, not inferred from certificates.
Cosine is enclosed by a degree-32 Taylor polynomial plus |x|^34/34!.
The algorithm is exact Python arithmetic; its implementation is NOT Lean-proved.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re


class Rejected(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Rejected(reason)


def read(path):
    require(Path(path).stat().st_size <= 65536, "file exceeds 64 KiB")
    return Path(path).read_text(encoding="utf-8")


def rational(s):
    require(
        len(s) <= 80 and re.fullmatch(r"[+-]?[0-9]+(?:/[+-]?[0-9]+)?", s, flags=re.ASCII),
        "invalid rational",
    )
    try:
        parts = [int(token) for token in s.split("/")]
        require(
            all(-(2**63) <= v <= 2**63 - 1 for v in parts), "rational token exceeds source capacity"
        )
        x = Q(parts[0], parts[1] if len(parts) == 2 else 1)
    except (ValueError, ZeroDivisionError) as e:
        raise Rejected("invalid rational") from e
    require(
        abs(x.numerator) <= 2**63 - 1 and x.denominator <= 2**63 - 1,
        "rational exceeds source capacity",
    )
    return x


def lines(text, header):
    rows = [s.split("#", 1)[0].split() for s in text.splitlines()]
    rows = [s for s in rows if s]
    require(rows and rows[0] == header.split(), f"expected {header}")
    return rows[1:]


@dataclass(frozen=True)
class Interval:
    lo: Q
    hi: Q

    def __post_init__(self):
        require(self.lo <= self.hi, "reversed interval")

    @property
    def mag(self):
        return max(abs(self.lo), abs(self.hi))

    @property
    def minmag(self):
        return self.lo if self.lo > 0 else -self.hi if self.hi < 0 else Q(0)

    def contains(self, other):
        return self.lo <= other.lo and other.hi <= self.hi

    def inflate(self, error):
        return Interval(self.lo - error, self.hi + error)

    def add(self, b):
        return Interval(self.lo + b.lo, self.hi + b.hi)

    def neg(self):
        return Interval(-self.hi, -self.lo)

    def mul(self, b):
        products = [a * c for a in (self.lo, self.hi) for c in (b.lo, b.hi)]
        return Interval(min(products), max(products))

    def div(self, b):
        require(b.minmag > 0, "divisor interval touches zero")
        return self.mul(Interval(1 / b.hi, 1 / b.lo))


@dataclass
class Node:
    name: str
    op: str
    interval: Interval
    error: Q
    args: tuple = ()
    local: Q = Q(0)


@dataclass
class Analysis:
    nodes: dict
    output: str
    tolerance: Q
    facts: list


def analyze(source):
    nodes, facts, output = {}, [], None
    for t in lines(source, "lumiris 1"):
        require(output is None, "output must be final")
        if t[0] == "output":
            require(len(t) == 3 and t[1] in nodes, "invalid output")
            output, tolerance = t[1], rational(t[2])
            facts.append((nodes[output].error, tolerance))
            require(0 <= nodes[output].error <= tolerance, "output budget exceeded")
            continue
        require(len(nodes) < 256 and len(t) >= 2, "node limit or malformed node")
        name = t[1]
        require(
            len(name) <= 64
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name, flags=re.ASCII)
            and name not in nodes,
            "invalid/duplicate name",
        )
        if t[0] == "input" and len(t) == 5:
            n = Node(name, "input", Interval(rational(t[2]), rational(t[3])), rational(t[4]))
        elif t[0] == "const" and len(t) == 4:
            c = rational(t[2])
            n = Node(name, "const", Interval(c, c), rational(t[3]))
        else:
            require(len(t) == 9 and t[0] in ("add", "sub", "mul", "div"), "invalid operation")
            require(t[2] in nodes and t[3] in nodes, "undefined/forward reference")
            a, b = nodes[t[2]], nodes[t[3]]
            local = rational(t[4])
            require(local >= 0, "negative local error")
            domain = Interval(rational(t[5]), rational(t[6]))
            out_domain = Interval(rational(t[7]), rational(t[8]))
            for operand in (a, b):
                actual = operand.interval.inflate(operand.error)
                require(domain.contains(actual), "actual operand outside device domain")
                facts.extend([(domain.lo, actual.lo), (actual.hi, domain.hi)])
            ea, eb = a.error, b.error
            ma, mb = a.interval.mag, b.interval.mag
            if t[0] in ("add", "sub"):
                interval = a.interval.add(b.interval if t[0] == "add" else b.interval.neg())
                error = ea + eb + local
            elif t[0] == "mul":
                interval = a.interval.mul(b.interval)
                error = ea * mb + ma * eb + ea * eb + local
            else:
                m = b.interval.minmag
                require(eb < m, "perturbed divisor can reach zero")
                interval = a.interval.div(b.interval)
                error = (ea * mb + ma * eb) / (m * (m - eb)) + local
                # Record a rational witness of strict separation.
                facts.append((Q(0), m - eb))
            actual = interval.inflate(error)
            require(out_domain.contains(actual), "actual result outside output domain")
            facts.extend([(out_domain.lo, actual.lo), (actual.hi, out_domain.hi)])
            n = Node(name, t[0], interval, error, (t[2], t[3]), local)
        require(n.error >= 0, "negative uncertainty")
        # Match the executable IR capacity and stop adversarial repeated squaring
        # before arbitrary-precision integers can grow without bound.
        require(
            all(
                abs(v.numerator) <= 2**63 - 1 and v.denominator <= 2**63 - 1
                for v in (n.interval.lo, n.interval.hi, n.error)
            ),
            "analyzed rational exceeds compiler capacity",
        )
        facts.extend([(n.interval.lo, n.interval.hi), (Q(0), n.error)])
        nodes[name] = n
    require(output is not None, "missing output")
    return Analysis(nodes, output, tolerance, facts)


def check_arithmetic(a, text):
    rows = lines(text, "lumiris-certificate 1")
    expected = [
        ["node", n.name, str(n.interval.lo), str(n.interval.hi), str(n.error)]
        for n in a.nodes.values()
    ]
    expected.append(["output", a.output, str(a.tolerance)])
    require(len(rows) == len(expected), "certificate node count mismatch")
    for row, wanted in zip(rows, expected):
        require(len(row) == len(wanted) and row[:2] == wanted[:2], "certificate graph mismatch")
        require(
            [rational(s) for s in row[2:]] == [Q(s) for s in wanted[2:]],
            "arithmetic certificate mismatch",
        )


def device_model(text):
    fields = {}
    for row in lines(text, "lumiris-mzi 1"):
        require(len(row) == 2 and row[0] not in fields, "duplicate/malformed device field")
        fields[row[0]] = row[1]
    require(
        set(fields)
        == {
            "id",
            "voltage_max",
            "dac_bits",
            "phase_per_v2",
            "phase_offset",
            "phase_error",
            "input_limit",
        },
        "device schema mismatch",
    )
    require(re.fullmatch(r"[+]?[0-9]+", fields["dac_bits"]), "invalid DAC bits")
    d = {k: rational(v) if k not in ("id", "dac_bits") else v for k, v in fields.items()}
    d["dac_bits"] = int(d["dac_bits"])
    require(
        2 <= d["dac_bits"] <= 16
        and 0 < d["voltage_max"] <= 10
        and 0 < d["phase_per_v2"] <= 1
        and abs(d["phase_offset"]) <= 1
        and 0 <= d["phase_error"] <= 1
        and 0 < d["input_limit"] <= 1,
        "unsupported device domain",
    )
    return d


def cosine_enclosure(phase):
    """Exact interval recurrence, no floating-point constants or compiler output."""
    x = phase.mul(Interval(Q(1, 2), Q(1, 2)))
    require(x.mag <= 8, "phase exceeds Taylor domain")
    square, term, total = x.mul(x), Interval(Q(1), Q(1)), Interval(Q(1), Q(1))
    for j in range(1, 17):
        term = term.mul(square).div(Interval(Q((2 * j - 1) * 2 * j), Q((2 * j - 1) * 2 * j)))
        total = total.add(term if j % 2 == 0 else term.neg())
    # Degree 33 has zero odd coefficient; order-34 Lagrange remainder <= |x|^34/34!.
    from math import factorial

    remainder = x.mag**34 / factorial(34)
    return Interval(max(Q(-1), total.lo - remainder), min(Q(1), total.hi + remainder))


def physical_binding(a):
    require(len(a.nodes) == 3, "MZI requires three-node graph")
    n = a.nodes[a.output]
    require(n.op == "mul", "MZI output is not multiply")
    left, right = (a.nodes[k] for k in n.args)
    if left.op == "const":
        left, right = right, left
    require(
        left.op == "input"
        and right.op == "const"
        and right.error == 0
        and abs(right.interval.lo) <= 1,
        "unsupported MZI binding",
    )
    return left, right.interval.lo, n.local


def check_physical(a, device_text, text):
    d = device_model(device_text)
    rows = lines(text, "lumiris-mzi-certificate 1")
    fields = {}
    for row in rows:
        require(len(row) >= 2 and row[0] not in fields, "duplicate/malformed physical claim")
        fields[row[0]] = row[1:]
    required = {
        "model": 1,
        "code": 1,
        "voltage": 1,
        "phase": 2,
        "transmission": 2,
        "weight_error": 1,
        "local_error": 1,
        "total_error": 1,
    }
    require(
        set(fields) == set(required) and all(len(fields[k]) == v for k, v in required.items()),
        "physical schema mismatch",
    )
    require(fields["model"] == [d["id"]], "model identity mismatch")
    require(re.fullmatch(r"[0-9]+", fields["code"][0]), "invalid DAC code")
    code = int(fields["code"][0])
    require(0 <= code < 2 ** d["dac_bits"], "unsafe DAC code")
    v = d["voltage_max"] * code / (2 ** d["dac_bits"] - 1)
    require(rational(fields["voltage"][0]) == v, "voltage binding mismatch")
    phase = Interval(
        d["phase_per_v2"] * v * v + d["phase_offset"] - d["phase_error"],
        d["phase_per_v2"] * v * v + d["phase_offset"] + d["phase_error"],
    )
    claimed_phase = Interval(*(rational(s) for s in fields["phase"]))
    require(phase == claimed_phase, "phase-model binding mismatch")
    transmission = Interval(*(rational(s) for s in fields["transmission"]))
    require(
        transmission.contains(cosine_enclosure(phase))
        and -1 <= transmission.lo <= transmission.hi <= 1,
        "invalid cosine enclosure",
    )
    inp, weight, budget = physical_binding(a)
    actual = inp.interval.inflate(inp.error)
    require(actual.mag <= d["input_limit"], "input exceeds calibrated model")
    delta = max(abs(transmission.lo - weight), abs(transmission.hi - weight))
    local = delta * actual.mag
    total = abs(weight) * inp.error + local
    for key, value in (("weight_error", delta), ("local_error", local), ("total_error", total)):
        require(rational(fields[key][0]) == value, f"{key} mismatch")
    require(
        local <= budget and total <= a.tolerance and total <= a.nodes[a.output].error,
        "physical error exceeds arithmetic contract",
    )
    a.facts.extend(
        [
            (Q(0), v),
            (v, d["voltage_max"]),
            (actual.mag, d["input_limit"]),
            (local, budget),
            (total, a.tolerance),
            (total, a.nodes[a.output].error),
        ]
    )
    return {
        "device": d,
        "code": code,
        "voltage": v,
        "phase": phase,
        "input": inp,
        "weight": weight,
        "total_error": total,
        "transmission": transmission,
    }


def export_lean(a, path):
    """Kernel-checkable numeric obligations, NOT a source-to-hardware proof."""

    def q(x):
        return f"({x.numerator} / {x.denominator} : ℚ)"

    out = [
        "import Lumiris",
        "",
        "-- Generated numeric obligations. See docs/verification.md for trust boundaries.",
        "namespace Lumiris.Generated",
    ]
    for i, (lo, hi) in enumerate(a.facts):
        out.append(f"theorem obligation_{i} : {q(lo)} ≤ {q(hi)} := by norm_num")
    out.append("end Lumiris.Generated\n")
    Path(path).write_text("\n".join(out))


def verify(bundle, expected_source=None, expected_device=None):
    bundle = Path(bundle)
    source = read(bundle / "program.lumi")
    if expected_source:
        require(source == read(expected_source), "bundle source differs from requested program")
    a = analyze(source)
    check_arithmetic(a, read(bundle / "arithmetic.cert"))
    physical = None
    require(
        (bundle / "physical.cert").exists() == (bundle / "device.mzi").exists(),
        "incomplete physical bundle",
    )
    if expected_device:
        require((bundle / "device.mzi").exists(), "expected physical bundle")
    if (bundle / "physical.cert").exists():
        device = read(bundle / "device.mzi")
        if expected_device:
            require(
                device == read(expected_device), "bundle device differs from requested calibration"
            )
        physical = check_physical(a, device, read(bundle / "physical.cert"))
    return a, physical, hashlib.sha256(source.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--device", type=Path)
    parser.add_argument("--lean", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        a, p, digest = verify(args.bundle, args.source, args.device)
        if args.lean:
            export_lean(a, args.lean)
        report = json.dumps(
            {
                "status": "PASS",
                "program_sha256": digest,
                "nodes": len(a.nodes),
                "output": a.output,
                "arithmetic_error_bound": str(a.nodes[a.output].error),
                "physical_error_bound": str(p["total_error"]) if p else None,
                "lean": (
                    "numeric obligations exported, not executed" if args.lean else "not executed"
                ),
                "assumption": "declared bounded operation errors and calibrated device model hold",
            },
            indent=2,
        )
        if args.report:
            args.report.write_text(report + "\n")
        print(report)
    except (Rejected, OSError, ValueError, KeyError, IndexError, ZeroDivisionError) as e:
        parser.exit(1, f"REJECT: {e}\n")


if __name__ == "__main__":
    main()
