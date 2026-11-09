"""Tests for Optical Tensor Core simulation and GEMM execution."""

import numpy as np
import pytest
from scipy.stats import unitary_group
from photonics.simulation.optical_engine import OpticalTensorCore
from photonics.benchmarks.benchmark_suite import PhotonicBenchmarkSuite


def test_optical_tensor_core_forward():
    n = 4
    core = OpticalTensorCore(n_channels=n, mzi_loss_db=0.0, phase_noise_std=0.0)
    u = unitary_group.rvs(n)
    core.set_unitary(u)

    x = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)
    result = core.forward(x, noisy=False)

    # Output should exactly match target unitary times x
    expected = u @ x
    np.testing.assert_allclose(result.output_field, expected, atol=1e-10)
    assert result.error_frobenius < 1e-10
    assert pytest.approx(result.fidelity, abs=1e-10) == 1.0


def test_optical_tensor_core_physical_metrics():
    n = 8
    core = OpticalTensorCore(n_channels=n)
    x = np.ones(n, dtype=complex) / np.sqrt(n)
    res = core.forward(x, noisy=True)

    # Time of flight must be in the picosecond regime (< 100 ps for integrated SOI chip)
    assert 1.0 < res.time_of_flight_ps < 100.0
    # Energy per MAC must be in the femtojoule regime (< 100 fJ/MAC)
    assert 5.0 < res.energy_mac_fj < 100.0


def test_benchmark_suite():
    suite = PhotonicBenchmarkSuite(electronic_baseline_energy_fj=2500.0)
    profile = suite.benchmark_core(n_channels=4, n_trials=3)

    assert profile.energy_advantage_ratio > 10.0  # Optical should be >10x lower energy
    assert profile.latency_advantage_ratio > 10.0  # Optical should be >10x faster time-of-flight
    assert profile.matrix_fidelity > 0.95
