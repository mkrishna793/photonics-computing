"""Tests for Memristor Crossbar Array, Differential Conductance, and IR Drops."""

import numpy as np
import pytest
from photonics.devices.memristor import MemristorCrossbar, MemristorConfig


def test_memristor_differential_programming():
    cfg = MemristorConfig(programming_noise_std=0.0, dac_levels=256)
    crossbar = MemristorCrossbar(n_rows=4, n_cols=4, config=cfg)

    # Random target weights in [-1, 1]
    np.random.seed(42)
    w_target = np.random.uniform(-1.0, 1.0, (4, 4))
    max_err = crossbar.program_weights(w_target, noisy=False)

    # Quantization error with 256 levels should be < 0.01
    assert max_err < 0.01


def test_memristor_forward_gemm():
    cfg = MemristorConfig(r_wire_ohm=0.0, programming_noise_std=0.0, dac_levels=1024)
    crossbar = MemristorCrossbar(n_rows=3, n_cols=3, config=cfg)

    w = np.array([
        [0.5, -0.3, 0.8],
        [-0.2, 0.6, -0.4],
        [0.1, 0.9, -0.7]
    ])
    crossbar.program_weights(w, noisy=False)

    x = np.array([0.1, -0.05, 0.15])
    y_expected = w.T @ x

    y_sim, metrics = crossbar.forward(x, include_ir_drop=False)
    np.testing.assert_allclose(y_sim, y_expected, atol=1e-2)
    assert metrics["power_watts"] > 0.0


def test_memristor_conductance_drift():
    cfg = MemristorConfig(drift_exponent=0.1, t0_seconds=1.0)
    crossbar = MemristorCrossbar(n_rows=2, n_cols=2, config=cfg)
    w = np.array([[1.0, -1.0], [0.5, -0.5]])
    crossbar.program_weights(w, noisy=False)

    initial_g_sum = np.sum(crossbar.g_pos)
    # Advance time to 100 seconds
    crossbar.apply_drift(100.0)
    drifted_g_sum = np.sum(crossbar.g_pos)

    # Retention drift causes conductances to decay over time
    assert drifted_g_sum < initial_g_sum


def test_memristor_wire_ir_drop_attenuation():
    cfg_ideal = MemristorConfig(r_wire_ohm=0.0)
    cfg_lossy = MemristorConfig(r_wire_ohm=10.0)  # High parasitic resistance

    cb_ideal = MemristorCrossbar(n_rows=8, n_cols=8, config=cfg_ideal)
    cb_lossy = MemristorCrossbar(n_rows=8, n_cols=8, config=cfg_lossy)

    w = np.ones((8, 8)) * 0.5
    cb_ideal.program_weights(w, noisy=False)
    cb_lossy.program_weights(w, noisy=False)

    v_in = np.ones(8) * 0.1
    y_ideal, _ = cb_ideal.forward(v_in, include_ir_drop=False)
    y_lossy, _ = cb_lossy.forward(v_in, include_ir_drop=True)

    # IR drop attenuates output current
    assert np.mean(y_lossy) < np.mean(y_ideal)
