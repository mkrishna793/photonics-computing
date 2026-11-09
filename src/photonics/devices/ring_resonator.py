"""Micro-Ring Resonator (MRR) device model for WDM Photonic Accelerators."""

from __future__ import annotations
import numpy as np


class MicroRingResonator:
    """All-Pass / Add-Drop Micro-Ring Resonator (MRR).

    Used in WDM-based photonic matrix multiplication (e.g., Broadcast-and-Weight)
    for spectral weighting, optical activation functions, and filtering.

    Parameters:
        radius_um: Ring radius in micrometers (default: 5.0 um).
        n_eff: Effective refractive index of optical waveguide (default: 2.45 for SOI).
        n_group: Group index of waveguide (default: 4.2 for SOI).
        coupling_coefficient: Self-coupling coefficient r (default: 0.98).
        loss_db_per_cm: Waveguide propagation loss in dB/cm (default: 2.0 dB/cm).
    """

    def __init__(
        self,
        radius_um: float = 5.0,
        n_eff: float = 2.45,
        n_group: float = 4.2,
        coupling_coefficient: float = 0.98,
        loss_db_per_cm: float = 2.0,
    ) -> None:
        self.radius_um = float(radius_um)
        self.n_eff = float(n_eff)
        self.n_group = float(n_group)
        self.r = float(coupling_coefficient)
        self.loss_db_per_cm = float(loss_db_per_cm)

    @property
    def perimeter_m(self) -> float:
        """Circumference of the ring in meters."""
        return 2.0 * np.pi * (self.radius_um * 1e-6)

    @property
    def round_trip_attenuation(self) -> float:
        """Field transmission factor 'a' over one round trip."""
        # alpha in m^-1: loss_db_per_cm / 4.343 * 100
        alpha_m = (self.loss_db_per_cm / 4.3429448) * 100.0
        return float(np.exp(-alpha_m * self.perimeter_m / 2.0))

    def free_spectral_range(self, center_wavelength_nm: float = 1550.0) -> float:
        """Calculates Free Spectral Range (FSR) in nm."""
        lam = center_wavelength_nm * 1e-9
        fsr_m = (lam ** 2) / (self.n_group * self.perimeter_m)
        return float(fsr_m * 1e9)

    def transmission_spectrum(self, wavelengths_nm: np.ndarray) -> np.ndarray:
        """Calculates optical power transmission T(lambda) = |E_through / E_in|^2."""
        lams = np.asarray(wavelengths_nm, dtype=float) * 1e-9
        phi = (2.0 * np.pi * self.n_eff * self.perimeter_m) / lams
        a = self.round_trip_attenuation
        r = self.r

        num = (r ** 2) - 2.0 * r * a * np.cos(phi) + (a ** 2)
        den = 1.0 - 2.0 * r * a * np.cos(phi) + ((r * a) ** 2)
        return num / den

    def weight_transmission(self, delta_phase: float) -> float:
        """Modulates optical weight transmission via electro-optic or thermo-optic phase tuning."""
        a = self.round_trip_attenuation
        r = self.r
        phi = delta_phase
        num = (r ** 2) - 2.0 * r * a * np.cos(phi) + (a ** 2)
        den = 1.0 - 2.0 * r * a * np.cos(phi) + ((r * a) ** 2)
        return float(num / den)
