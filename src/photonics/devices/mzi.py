"""Mach-Zehnder Interferometer (MZI) and Directional Coupler models for photonic tensor meshes."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class DirectionalCoupler:
    """50:50 Directional Coupler (symmetric optical beamsplitter).

    Transfer matrix:
        B = (1 / sqrt(2)) * [[1,  i],
                             [i,  1]]
    """
    coupling_ratio: float = 0.5
    excess_loss_db: float = 0.05  # Standard silicon photonics coupler loss (~0.05 dB)

    @property
    def matrix(self) -> np.ndarray:
        kappa = np.sqrt(self.coupling_ratio)
        tau = np.sqrt(1.0 - self.coupling_ratio)
        loss_factor = 10.0 ** (-self.excess_loss_db / 20.0)
        return loss_factor * np.array([
            [tau, 1j * kappa],
            [1j * kappa, tau]
        ], dtype=complex)


class MachZehnderInterferometer:
    """Tunable 2x2 Mach-Zehnder Interferometer (MZI).

    Consists of two 50:50 directional couplers with an internal phase shifter theta
    (controlling optical power splitting) and an external phase shifter phi (controlling output phase).

    Transfer matrix:
        T(theta, phi) = P_ext @ B @ P_int @ B
        where:
            P_int = [[exp(i * theta), 0],
                     [0,              1]]
            P_ext = [[exp(i * phi),   0],
                     [0,              1]]
    """

    def __init__(
        self,
        theta: float = 0.0,
        phi: float = 0.0,
        insertion_loss_db: float = 0.0,
        coupler_loss_db: float = 0.0,
        phase_error_std: float = 0.0,
    ) -> None:
        self.theta = float(theta)
        self.phi = float(phi)
        self.insertion_loss_db = float(insertion_loss_db)
        self.coupler_loss_db = float(coupler_loss_db)
        self.phase_error_std = float(phase_error_std)
        self.coupler = DirectionalCoupler(excess_loss_db=coupler_loss_db)

    def get_transfer_matrix(self, noisy: bool = False) -> np.ndarray:
        """Computes the 2x2 complex transfer matrix of the MZI."""
        th = self.theta
        ph = self.phi
        if noisy and self.phase_error_std > 0.0:
            th += np.random.normal(0.0, self.phase_error_std)
            ph += np.random.normal(0.0, self.phase_error_std)

        b = self.coupler.matrix
        p_int = np.array([[np.exp(1j * th), 0.0], [0.0, 1.0]], dtype=complex)
        p_ext = np.array([[np.exp(1j * ph), 0.0], [0.0, 1.0]], dtype=complex)

        t = p_ext @ b @ p_int @ b
        loss_factor = 10.0 ** (-self.insertion_loss_db / 20.0)
        return loss_factor * t

    def propagate(self, input_field: np.ndarray, noisy: bool = False) -> np.ndarray:
        """Propagates complex optical field vector [E_in_0, E_in_1]^T through MZI."""
        e_in = np.asarray(input_field, dtype=complex)
        if e_in.shape != (2,):
            raise ValueError(f"Input field must have shape (2,), got {e_in.shape}")
        return self.get_transfer_matrix(noisy=noisy) @ e_in

    def power_transmission(self) -> tuple[float, float]:
        """Calculates optical power transmission into port 0 and port 1 given unit power into port 0."""
        t = self.get_transfer_matrix(noisy=False)
        p0 = float(np.abs(t[0, 0]) ** 2)
        p1 = float(np.abs(t[1, 0]) ** 2)
        return p0, p1

    def is_unitary(self, tolerance: float = 1e-6) -> bool:
        """Validates unitary energy conservation (assuming 0 dB insertion loss)."""
        temp_loss = self.insertion_loss_db
        temp_coupler_loss = self.coupler.excess_loss_db
        try:
            self.insertion_loss_db = 0.0
            self.coupler.excess_loss_db = 0.0
            u = self.get_transfer_matrix(noisy=False)
            diff = np.max(np.abs(u @ u.conj().T - np.eye(2)))
            return bool(diff < tolerance)
        finally:
            self.insertion_loss_db = temp_loss
            self.coupler.excess_loss_db = temp_coupler_loss
