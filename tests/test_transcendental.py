"""Tests for L1 Transcendental Function Approximations and SSA Lowering."""

import numpy as np
import pytest
from photonics.compiler.ir import Interval, SSAGraph, verify_graph_contracts
from photonics.compiler.transcendental import (
    ChebyshevApproximation,
    approximate_transcendental,
    lower_approximation_to_ssa,
)


def test_chebyshev_exp_approximation():
    domain = Interval(-1.0, 1.0)
    res = approximate_transcendental("exp", domain, target_tolerance=1e-4)

    assert res.degree >= 4
    assert res.max_truncation_error <= 1e-4

    # Test fine grid validation
    x = np.linspace(-1.0, 1.0, 500)
    poly_y = np.polynomial.polynomial.polyval(x, res.coefficients)
    true_y = np.exp(x)
    observed_err = np.max(np.abs(true_y - poly_y))
    assert observed_err <= res.max_truncation_error + 1e-10


def test_chebyshev_tanh_and_sigmoid():
    domain = Interval(-2.0, 2.0)
    res_tanh = approximate_transcendental("tanh", domain, target_tolerance=5e-3)
    assert res_tanh.max_truncation_error <= 5e-3

    res_sig = approximate_transcendental("sigmoid", domain, target_tolerance=5e-3)
    assert res_sig.max_truncation_error <= 5e-3


def test_lower_transcendental_to_ssa_horner():
    domain = Interval(-0.5, 0.5)
    res = ChebyshevApproximation.fit(np.exp, domain, degree=4, func_name="exp")

    graph = SSAGraph("test_exp_horner")
    graph.add_input("x", -0.5, 0.5, error=0.0001)

    result_node = lower_approximation_to_ssa(
        graph=graph,
        input_node_name="x",
        output_name_prefix="exp",
        approx=res,
        domain_out=Interval(0.2, 2.5),
    )
    graph.set_output(result_node, tolerance=0.01)

    # Verify contracts
    audit = verify_graph_contracts(graph)
    assert audit["status"] == "PASS"
    assert audit["composed_error"] <= 0.01
