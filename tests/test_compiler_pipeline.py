"""Tests for Lumiris SSA Compiler, Multi-Backend Lowering, and Independent Certificate Auditing."""

import numpy as np
import pytest
from photonics.compiler.ir import SSAGraph, Interval, verify_graph_contracts
from photonics.compiler.lowering import OpticalMeshBackend, MemristorCrossbarBackend
from photonics.compiler.certificate import (
    CertificateGenerator,
    IndependentCertificateAuditor,
    VerificationStatus,
)


def test_ssa_graph_arithmetic_verification():
    graph = SSAGraph("test_arithmetic")
    graph.add_input("x", -0.5, 0.5, error=0.001)
    graph.add_const("weight", 0.5, error=0.0)
    graph.add_binary_op(
        op="mul",
        name="y",
        left="weight",
        right="x",
        local_error=0.0005,
        domain_in=Interval(-1.0, 1.0),
        domain_out=Interval(-1.0, 1.0),
    )
    graph.set_output("y", tolerance=0.002)

    res = verify_graph_contracts(graph)
    assert res["status"] == "PASS"
    assert res["composed_error"] <= 0.002


def test_fail_closed_zero_and_uncertain_divisors():
    # 1. Zero divisor in interval [-0.1, 0.1]
    g_zero = SSAGraph("reject_zero_div")
    g_zero.add_input("num", 1.0, 2.0, error=0.0)
    g_zero.add_input("den", -0.1, 0.1, error=0.0)
    g_zero.add_binary_op(
        op="div",
        name="q",
        left="num",
        right="den",
        local_error=0.0,
        domain_in=Interval(-10.0, 10.0),
        domain_out=Interval(-10.0, 10.0),
    )
    g_zero.set_output("q", tolerance=1.0)

    with pytest.raises(ValueError, match="contains zero"):
        verify_graph_contracts(g_zero)

    # 2. Denominator does not touch 0 ideally, but error eb >= min(|lo|, |hi|)
    g_unc = SSAGraph("reject_uncertain_div")
    g_unc.add_input("num", 1.0, 2.0, error=0.0)
    # Denominator interval [0.2, 0.5], but uncertainty is 0.25 >= 0.2!
    g_unc.add_input("den", 0.2, 0.5, error=0.25)
    g_unc.add_binary_op(
        op="div",
        name="q",
        left="num",
        right="den",
        local_error=0.0,
        domain_in=Interval(-10.0, 10.0),
        domain_out=Interval(-10.0, 10.0),
    )
    g_unc.set_output("q", tolerance=1.0)

    with pytest.raises(ValueError, match="Uncertain divisor"):
        verify_graph_contracts(g_unc)


def test_optical_mesh_backend_lowering():
    backend = OpticalMeshBackend()
    w_target = np.array([
        [0.4, -0.6],
        [0.7, 0.2]
    ], dtype=complex)

    bundle = backend.lower_gemm(w_target, node_name="gemm_test")
    assert bundle.backend_type == "optical_mesh"
    assert bundle.status == "COMPILED"
    assert bundle.control_registers["total_mzis"] > 0
    assert bundle.physical_error_bound > 0.0

    # Verify that all DAC codes are within [0, 4095]
    for stage in bundle.control_registers["mzi_stages"]:
        assert 0 <= stage["dac_code"] < 4096
        assert 0.0 <= stage["heater_voltage_v"] <= 5.0


def test_memristor_crossbar_backend_lowering():
    backend = MemristorCrossbarBackend()
    w_target = np.array([
        [1.2, -0.5, 0.8],
        [-0.3, 0.9, -1.1]
    ])

    bundle = backend.lower_gemm(w_target, node_name="mem_gemm")
    assert bundle.backend_type == "memristor_crossbar"
    assert bundle.status == "COMPILED"
    assert bundle.target_shape == (2, 3)
    assert len(bundle.control_registers["g_pos_siemens"]) == 2
    assert len(bundle.control_registers["g_pos_siemens"][0]) == 3


def test_dual_verification_certificate_auditor():
    graph = SSAGraph("cert_test")
    graph.add_input("x", -0.5, 0.5, error=0.001)
    graph.add_const("weight", 0.5, error=0.0)
    graph.add_binary_op(
        op="mul",
        name="y",
        left="weight",
        right="x",
        local_error=0.0005,
        domain_in=Interval(-1.0, 1.0),
        domain_out=Interval(-1.0, 1.0),
    )
    graph.set_output("y", tolerance=0.01)

    backend = OpticalMeshBackend()
    w_target = np.array([[0.5]], dtype=complex)
    bundle = backend.lower_gemm(w_target, node_name="cert_bundle")

    # 1. Generate certificate
    cert = CertificateGenerator.generate(graph, bundle)
    assert cert.status == VerificationStatus.PASS

    # 2. Independent audit
    audit = IndependentCertificateAuditor.audit_certificate(cert, graph, bundle)
    assert audit["status"] == VerificationStatus.PASS

    # 3. Tampering test: tamper with control register digest
    cert.control_digest = "tampered_digest_deadbeef"
    audit_tampered = IndependentCertificateAuditor.audit_certificate(cert, graph, bundle)
    assert audit_tampered["status"] == VerificationStatus.REJECTED
    assert "tampering detected" in audit_tampered["reason"]
