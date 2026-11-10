"""Tests for Thermal Crosstalk modeling and phase pre-compensation."""

import numpy as np
import pytest
from photonics.devices.mzi import ThermalCrosstalkModel
from photonics.simulation.optical_engine import OpticalTensorCore


def test_thermal_crosstalk_matrix_symmetry():
    model = ThermalCrosstalkModel(coupling_strength=0.2, decay_length=1.5)
    k = model.get_coupling_matrix(5)

    # Diagonal must be 0 (self-heating handled separately)
    assert np.all(np.diag(k) == 0.0)
    # Off-diagonal symmetry K_ij == K_ji
    np.testing.assert_allclose(k, k.T)
    # Monotonic decay with distance
    assert k[0, 1] > k[0, 2] > k[0, 3]


def test_thermal_crosstalk_precompensation():
    model = ThermalCrosstalkModel(coupling_strength=0.15, decay_length=1.2)
    n = 6
    target_thetas = np.array([0.2, 0.8, 1.5, 0.4, 2.1, 1.0])

    # Uncompensated
    eff_uncomp = model.apply_crosstalk(target_thetas)
    uncomp_err = np.linalg.norm(eff_uncomp - target_thetas)
    assert uncomp_err > 0.1

    # Pre-compensated: (I + K)^-1 @ target
    driven = model.precompensate(target_thetas)
    eff_comp = model.apply_crosstalk(driven)
    comp_err = np.linalg.norm(eff_comp - target_thetas)

    # Pre-compensation completely cancels crosstalk
    assert comp_err < 1e-12


def test_optical_tensor_core_crosstalk_compensation():
    # Test core with and without pre-compensation
    core_comp = OpticalTensorCore(
        n_channels=4,
        enable_thermal_crosstalk=True,
        precompensate_crosstalk=True,
        phase_noise_std=0.0,
        mzi_loss_db=0.0
    )
    core_uncomp = OpticalTensorCore(
        n_channels=4,
        enable_thermal_crosstalk=True,
        precompensate_crosstalk=False,
        phase_noise_std=0.0,
        mzi_loss_db=0.0
    )

    from scipy.stats import unitary_group
    np.random.seed(42)
    u_test = unitary_group.rvs(4)
    core_comp.set_unitary(u_test)
    core_uncomp.set_unitary(u_test)

    x = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)
    res_comp = core_comp.forward(x, noisy=True)
    res_uncomp = core_uncomp.forward(x, noisy=True)

    # Pre-compensated core maintains higher fidelity than uncompensated
    assert res_comp.fidelity > res_uncomp.fidelity
