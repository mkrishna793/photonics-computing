"""Integration, adversarial-certificate, and numerical property tests (stdlib only)."""

from fractions import Fraction as Q
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_certificate as ck
from simulate import simulate

BIN = ROOT / "Lean-Semantics/rust/target/debug/lumiris"


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "bundle"

    def compile(self, source="mzi-scale.lumi", device=True, text=None, device_text=None):
        path = ROOT / "examples" / source
        if text is not None:
            path = Path(self.temp.name) / "source.lumi"
            path.write_text(text)
        args = [str(BIN), "compile", str(path), str(self.bundle)]
        if device:
            dp = ROOT / "devices/demo-mzi.mzi"
            if device_text is not None:
                dp = Path(self.temp.name) / "custom.mzi"
                dp.write_text(device_text)
            args.extend(["--device", str(dp)])
        return subprocess.run(args, text=True, capture_output=True)

    def test_end_to_end(self):
        r = self.compile()
        self.assertEqual(r.returncode, 0, r.stderr)
        a, p, _ = ck.verify(
            self.bundle, ROOT / "examples/mzi-scale.lumi", ROOT / "devices/demo-mzi.mzi"
        )
        self.assertEqual(a.nodes[a.output].interval, ck.Interval(Q(-9, 20), Q(9, 20)))
        self.assertLessEqual(p["total_error"], a.tolerance)
        report = simulate(self.bundle, 2000)
        self.assertEqual(report["status"], "PASS")
        self.assertLessEqual(report["maximum_absolute_error"], report["checked_error_bound"])
        out = self.bundle / "Certificate.lean"
        ck.export_lean(a, out)
        self.assertIn("theorem obligation_", out.read_text())

    def test_safe_division(self):
        r = self.compile("safe-division.lumi", False)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, _, _ = ck.verify(self.bundle)
        self.assertEqual(a.nodes[a.output].interval, ck.Interval(Q(1, 4), Q(1)))

    def test_negative_divisor(self):
        text = "lumiris 1\ninput a 1 2 0\ninput b -4 -2 0\ndiv y a b 0 -5 5 -2 0\noutput y 0"
        r = self.compile(text=text, device=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, _, _ = ck.verify(self.bundle)
        self.assertEqual(a.nodes["y"].interval, ck.Interval(Q(-1), Q(-1, 4)))

    def test_uncertain_divisor_rejected_by_both(self):
        text = "lumiris 1\ninput a 1 2 0\ninput b 1 2 1\ndiv y a b 0 -5 5 -10 10\noutput y 10"
        r = self.compile(text=text, device=False)
        self.assertNotEqual(r.returncode, 0)
        with self.assertRaises(ck.Rejected):
            ck.analyze(text)

    def test_capacity_and_node_limits(self):
        texts = [
            "lumiris 1\nconst a 9223372036854775807 0\nconst b 2 0\nmul y a b 0 -9223372036854775807 9223372036854775807 -9223372036854775807 9223372036854775807\noutput y 0",
            "lumiris 1\n" + "\n".join(f"const n{i} 0 0" for i in range(257)) + "\noutput n256 0",
        ]
        for text in texts:
            r = self.compile(text=text, device=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(self.bundle.exists())

    def test_zero_divisor(self):
        r = self.compile("reject-zero-divisor.lumi", False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.bundle.exists())

    def test_tamper_arithmetic(self):
        self.assertEqual(self.compile().returncode, 0)
        path = self.bundle / "arithmetic.cert"
        path.write_text(path.read_text().replace("21/20000", "0/1"))
        with self.assertRaises(ck.Rejected):
            ck.verify(self.bundle)

    def test_tamper_physics(self):
        self.assertEqual(self.compile().returncode, 0)
        path = self.bundle / "physical.cert"
        original = path.read_text()
        mutations = [
            original.replace("code 1891", "code 999999"),
            original.replace("voltage 1891/819", "voltage 0"),
            original + "code 1\n",
            original.replace("weight_error 97361/250000000", "weight_error 0"),
            original.replace(
                "transmission 250188469/500000000 125097361/250000000", "transmission 1/2 1/2"
            ),
        ]
        for text in mutations:
            path.write_text(text)
            with self.assertRaises(ck.Rejected):
                ck.verify(self.bundle)

    def test_calibration_binding(self):
        self.assertEqual(self.compile().returncode, 0)
        path = self.bundle / "device.mzi"
        path.write_text(path.read_text().replace("392699/1000000", "1/4"))
        with self.assertRaises(ck.Rejected):
            ck.verify(self.bundle)

    def test_expected_source(self):
        self.assertEqual(self.compile().returncode, 0)
        with self.assertRaises(ck.Rejected):
            ck.verify(self.bundle, ROOT / "examples/safe-division.lumi")

    def test_incomplete_physical_bundle(self):
        self.assertEqual(self.compile().returncode, 0)
        (self.bundle / "physical.cert").unlink()
        with self.assertRaises(ck.Rejected):
            ck.verify(self.bundle)

    def test_no_overwrite(self):
        self.assertEqual(self.compile().returncode, 0)
        before = (self.bundle / "physical.cert").read_bytes()
        self.assertNotEqual(self.compile().returncode, 0)
        self.assertEqual(before, (self.bundle / "physical.cert").read_bytes())

    def test_bad_device(self):
        device = (ROOT / "devices/demo-mzi.mzi").read_text()
        for text in [
            device.replace("dac_bits 12", "dac_bits 1"),
            device.replace("phase_error 1/100000", "phase_error -1"),
            device + "unknown 1\n",
            device + "dac_bits 12\n",
        ]:
            r = self.compile(device_text=text)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(self.bundle.exists())

    def test_resolution_failure(self):
        text = (
            (ROOT / "examples/mzi-scale.lumi")
            .read_text()
            .replace("mul y weight x 1/1000", "mul y weight x 0")
        )
        r = self.compile(text=text)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.bundle.exists())

    def test_saturation(self):
        text = "lumiris 1\ninput x 0 1 1/10\nconst w 1 0\nadd y x w 0 -2 2 0 2\noutput y 1"
        r = self.compile(text=text, device=False)
        self.assertNotEqual(r.returncode, 0)

    def test_eval(self):
        r = subprocess.run(
            [str(BIN), "eval", str(ROOT / "examples/mzi-scale.lumi"), "x=1/2"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "1/4")
        r = subprocess.run(
            [str(BIN), "eval", str(ROOT / "examples/mzi-scale.lumi"), "x=2"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(r.returncode, 0)

    def test_negative_and_endpoint_weights(self):
        original = (ROOT / "examples/mzi-scale.lumi").read_text()
        for w in ["-1", "-1/2", "0", "1"]:
            if self.bundle.exists():
                shutil.rmtree(self.bundle)
            r = self.compile(
                text=original.replace("const weight 1/2 0", f"const weight {w} 0").replace(
                    "output y 11/10000", "output y 1/100"
                )
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            ck.verify(self.bundle)
            simulate(self.bundle, 100)

    def test_unknown_and_oversize(self):
        for text in [
            "lumiris 1\nconst x NaN 0\noutput x 1",
            "lumiris 1\nconst x 1 0\noutput x 0\nconst y 2 0",
            "#" * 65537,
        ]:
            r = self.compile(text=text, device=False)
            self.assertNotEqual(r.returncode, 0)

    def test_randomized_arithmetic_compiler_checker_agree(self):
        rng = random.Random(9)
        for i in range(100):
            if self.bundle.exists():
                shutil.rmtree(self.bundle)
            lo1, lo2 = rng.randint(-5, 5), rng.randint(1, 5)
            hi1, hi2 = lo1 + rng.randint(0, 3), lo2 + rng.randint(0, 3)
            op = rng.choice(["add", "sub", "mul", "div"])
            text = f"lumiris 1\ninput a {lo1} {hi1} 1/100\ninput b {lo2} {hi2} 1/100\n{op} y a b 1/1000 -20 20 -100 100\noutput y 10"
            r = self.compile(text=text, device=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            a, _, _ = ck.verify(self.bundle)
            n = a.nodes["y"]
            for _ in range(10):
                x = Q(rng.randint(lo1 * 100, hi1 * 100), 100)
                y = Q(rng.randint(lo2 * 100, hi2 * 100), 100)
                dx, dy = Q(rng.randint(-10, 10), 1000), Q(rng.randint(-10, 10), 1000)
                fn = {
                    "add": lambda a, b: a + b,
                    "sub": lambda a, b: a - b,
                    "mul": lambda a, b: a * b,
                    "div": lambda a, b: a / b,
                }[op]
                ideal, actual = fn(x, y), fn(x + dx, y + dy) + Q(1, 1000)
                self.assertTrue(n.interval.contains(ck.Interval(ideal, ideal)))
                self.assertLessEqual(abs(actual - ideal), n.error)


class CheckerProperties(unittest.TestCase):
    def test_taylor_encloses_cosine(self):
        rng = random.Random(32)
        for _ in range(200):
            center = Q(rng.randint(-1500, 1500), 100)
            width = Q(rng.randint(0, 10), 10000)
            phase = ck.Interval(center - width, center + width)
            enclosure = ck.cosine_enclosure(phase)
            for f in (phase.lo, phase.hi, (phase.lo + phase.hi) / 2):
                v = math.cos(float(f) / 2)
                self.assertLessEqual(float(enclosure.lo), v + 1e-15)
                self.assertLessEqual(v, float(enclosure.hi) + 1e-15)

    def test_checker_stops_exponential_integer_growth(self):
        text = "lumiris 1\nconst a 9223372036854775807 0\nmul y a a 0 -9223372036854775807 9223372036854775807 -9223372036854775807 9223372036854775807\noutput y 0"
        with self.assertRaises(ck.Rejected):
            ck.analyze(text)

    def test_signed_rational_denominators(self):
        self.assertEqual(ck.rational("1/-2"), Q(-1, 2))
        self.assertEqual(ck.rational("-1/-2"), Q(1, 2))
        self.assertEqual(ck.rational("1/+2"), Q(1, 2))

    def test_reject_parser_edges(self):
        for s in ["1/0", "nan", "inf", "1e100", "0.1", "1/2/3", "9" * 100, "-9223372036854775808"]:
            with self.assertRaises(ck.Rejected):
                ck.rational(s)


if __name__ == "__main__":
    unittest.main()
