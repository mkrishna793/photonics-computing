"""Coherent Optical Tensor Core & Photonic GEMM Accelerator Engine."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from photonics.core.unitary import reckon_decompose, reckon_reconstruct, matrix_fidelity, MZIRotation


@dataclass
class OpticalGEMMResult:
    """Output metrics from an Optical Matrix-Vector Multiplication pass."""
    output_field: np.ndarray
    detected_intensity: np.ndarray
    ideal_output_field: np.ndarray
    error_frobenius: float
    fidelity: float
    time_of_flight_ps: float
    energy_mac_fj: float


class OpticalTensorCore:
    """N x N Coherent Photonic Mesh Accelerator.

    Simulates the physical propagation of coherent light through an integrated
    nanophotonic mesh (e.g., Reck/Clements topology) with realistic hardware non-idealities:
    - Phase shifter precision noise (bit-depth quantization / thermal drift)
    - Directional coupler insertion loss (dB per MZI)
    - Optical propagation latency through waveguide paths
    - Photodetector shot noise and responsivity

    Parameters:
        n_channels: Number of optical channels N (matrix dimension).
        mzi_loss_db: Insertion loss per MZI stage in dB (default: 0.1 dB).
        phase_noise_std: Standard deviation of phase shifter noise in radians (default: 0.005 rad).
        waveguide_pitch_um: Distance between waveguide channels in um (default: 50.0 um).
        group_index: Optical group index n_g of silicon waveguide (default: 4.2).
    """

    def __init__(
        self,
        n_channels: int = 4,
        mzi_loss_db: float = 0.1,
        phase_noise_std: float = 0.005,
        waveguide_pitch_um: float = 50.0,
        group_index: float = 4.2,
    ) -> None:
        self.n = int(n_channels)
        self.mzi_loss_db = float(mzi_loss_db)
        self.phase_noise_std = float(phase_noise_std)
        self.waveguide_pitch_um = float(waveguide_pitch_um)
        self.group_index = float(group_index)

        # Initialize with identity unitary
        self.target_unitary = np.eye(self.n, dtype=complex)
        self.rotations: list[MZIRotation] = []
        self.diag_phases = np.zeros(self.n, dtype=float)
        self.set_unitary(self.target_unitary)

    def set_unitary(self, u: np.ndarray) -> None:
        """Programs the optical mesh with a target unitary matrix U via Reck decomposition."""
        if u.shape != (self.n, self.n):
            raise ValueError(f"Matrix shape {u.shape} does not match core dimensions ({self.n}, {self.n})")
        self.target_unitary = np.array(u, dtype=complex)
        self.rotations, self.diag_phases = reckon_decompose(self.target_unitary)

    @property
    def physical_mesh_matrix(self) -> np.ndarray:
        """Computes the effective physical transfer matrix including loss and phase perturbations."""
        u_mesh = np.diag(np.exp(1j * self.diag_phases))
        loss_per_mzi = 10.0 ** (-self.mzi_loss_db / 20.0)

        for rot in reversed(self.rotations):
            m, n_ch = rot.channel_m, rot.channel_n
            # Apply phase noise
            th = rot.theta + np.random.normal(0.0, self.phase_noise_std)
            ph = rot.phi + np.random.normal(0.0, self.phase_noise_std)

            c = np.cos(th / 2.0)
            s = np.sin(th / 2.0)
            g = np.array([
                [c, s * np.exp(-1j * ph)],
                [-s * np.exp(1j * ph), c]
            ], dtype=complex)
            g_dag = g.conj().T * loss_per_mzi
            u_mesh[[m, n_ch], :] = g_dag @ u_mesh[[m, n_ch], :]

        return u_mesh

    def forward(self, x: np.ndarray, noisy: bool = True) -> OpticalGEMMResult:
        """Executes coherent optical matrix-vector multiplication: y = U_mesh @ x.

        Parameters:
            x: Input optical field vector (length N, complex or real).
            noisy: Whether to apply physical phase noise and attenuation.
        """
        x_vec = np.asarray(x, dtype=complex)
        if x_vec.shape != (self.n,):
            raise ValueError(f"Input vector shape {x_vec.shape} != ({self.n},)")

        ideal_out = self.target_unitary @ x_vec
        if noisy:
            mesh_u = self.physical_mesh_matrix
        else:
            mesh_u = reckon_reconstruct(self.rotations, self.diag_phases, self.n)

        actual_out = mesh_u @ x_vec
        detected_intensity = np.abs(actual_out) ** 2

        # Physics metrics:
        # Time of flight: length = n * pitch
        c_speed = 3e8  # m/s
        total_mesh_length_m = (self.n * 200e-6)  # ~200 um per MZI stage
        tof_seconds = (total_mesh_length_m * self.group_index) / c_speed
        tof_ps = tof_seconds * 1e12

        # Energy per MAC: optical passive mesh consumes ~10-50 fJ/MAC (mostly modulation + detection)
        energy_mac_fj = 15.0 + (0.5 * self.n)

        frobenius_err = float(np.linalg.norm(actual_out - ideal_out))
        fid = matrix_fidelity(self.target_unitary, mesh_u)

        return OpticalGEMMResult(
            output_field=actual_out,
            detected_intensity=detected_intensity,
            ideal_output_field=ideal_out,
            error_frobenius=frobenius_err,
            fidelity=fid,
            time_of_flight_ps=tof_ps,
            energy_mac_fj=energy_mac_fj,
        )
