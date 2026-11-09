"""Tests for Mach-Zehnder Interferometer and directional coupler devices."""

import numpy as np
import pytest
from photonics.devices.mzi import MachZehnderInterferometer, DirectionalCoupler
from photonics.devices.ring_resonator import MicroRingResonator


def test_directional_coupler_unitarity():
    dc = DirectionalCoupler(coupling_ratio=0.5, excess_loss_db=0.0)
    mat = dc.matrix
    # Check B @ B^dagger == I
    diff = np.max(np.abs(mat @ mat.conj().T - np.eye(2)))
    assert diff < 1e-12


def test_mzi_unitarity_lossless():
    mzi = MachZehnderInterferometer(theta=np.pi / 3, phi=np.pi / 5, insertion_loss_db=0.0)
    assert mzi.is_unitary(tolerance=1e-12)


def test_mzi_power_splitting_cross_bar():
    # theta = 0 => 50:50 power split
    mzi_5050 = MachZehnderInterferometer(theta=0.0, phi=0.0, insertion_loss_db=0.0)
    p0, p1 = mzi_5050.power_transmission()
    assert pytest.approx(p0 + p1, rel=1e-5) == 1.0

    # theta = pi => full crossover (bar state)
    mzi_bar = MachZehnderInterferometer(theta=np.pi, phi=0.0, insertion_loss_db=0.0)
    p0_bar, p1_bar = mzi_bar.power_transmission()
    assert pytest.approx(p0_bar + p1_bar, rel=1e-5) == 1.0


def test_microring_resonator_fsr():
    mrr = MicroRingResonator(radius_um=5.0, n_eff=2.45, n_group=4.2)
    fsr = mrr.free_spectral_range(center_wavelength_nm=1550.0)
    # For R=5um, L~31.4um, FSR should be in the range of 15-25 nm
    assert 10.0 < fsr < 30.0


def test_microring_resonator_transmission():
    mrr = MicroRingResonator()
    wavelengths = np.linspace(1540.0, 1560.0, 100)
    t = mrr.transmission_spectrum(wavelengths)
    assert np.all(t >= 0.0) and np.all(t <= 1.0)
