"""Coherent Optical Tensor Core, SVD Multiplier, and Photodetector Receiver Engine."""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from photonics.core.unitary import reckon_decompose, reckon_reconstruct, matrix_fidelity, MZIRotation
from photonics.devices.mzi import ThermalCrosstalkModel


@dataclass
class PhotodetectorConfig:
    """Receiver specifications for integrated PIN / Germanium waveguide photodetectors."""
    responsivity_aw: float = 0.8         # Responsivity at 1550 nm (0.8 A/W)
    dark_current_a: float = 1.0e-8       # Dark current (10 nA)
    bandwidth_hz: float = 10.0e9         # Receiver bandwidth (10 GHz)
    load_resistance_ohm: float = 50.0    # TIA/receiver load (50 Ohms)
    temperature_kelvin: float = 300.0    # Operating temperature (300 K)
    saturation_power_w: float = 10.0e-3  # Photodiode optical saturation power (10 mW)


class Photodetector:
    """Photodiode receiver simulating shot noise, thermal noise, and signal-to-noise ratio."""

    def __init__(self, config: Optional[PhotodetectorConfig] = None) -> None:
        self.cfg = config or PhotodetectorConfig()
        self.q = 1.602176634e-19         # Elementary charge (Coulombs)
        self.k_b = 1.380649e-23          # Boltzmann constant (J/K)

    def detect(self, optical_power_watts: np.ndarray, noisy: bool = True) -> tuple[np.ndarray, dict[str, float]]:
        """Converts optical power vector P into photocurrents with physical noise.

        Noise equations:
            sigma_shot^2 = 2 * q * (I_signal + I_dark) * Bandwidth
            sigma_thermal^2 = (4 * k_B * T * Bandwidth) / R_load
        """
        p = np.clip(np.asarray(optical_power_watts, dtype=float), 0.0, self.cfg.saturation_power_w)
        i_signal = self.cfg.responsivity_aw * p

        # Noise variances
        var_shot = 2.0 * self.q * (i_signal + self.cfg.dark_current_a) * self.cfg.bandwidth_hz
        var_thermal = (4.0 * self.k_b * self.cfg.temperature_kelvin * self.cfg.bandwidth_hz) / self.cfg.load_resistance_ohm
        total_noise_std = np.sqrt(var_shot + var_thermal)

        if noisy:
            noise = np.random.normal(0.0, total_noise_std, size=p.shape)
            i_detected = np.maximum(0.0, i_signal + noise)
        else:
            i_detected = i_signal

        # Signal-to-noise ratio
        signal_power = np.mean(i_signal ** 2) if np.mean(i_signal) > 0 else 1e-18
        noise_power = np.mean(total_noise_std ** 2)
        snr_linear = signal_power / (noise_power + 1e-20)
        snr_db = 10.0 * np.log10(snr_linear) if snr_linear > 0 else 0.0
        enob = max(0.0, (snr_db - 1.76) / 6.02)

        metrics = {
            "snr_db": float(snr_db),
            "enob_bits": float(enob),
            "shot_noise_rms_amperes": float(np.mean(np.sqrt(var_shot))),
            "thermal_noise_rms_amperes": float(np.sqrt(var_thermal)),
        }
        return i_detected, metrics


@dataclass
class OpticalGEMMResult:
    """Output metrics from an Optical Matrix-Vector Multiplication pass."""
    output_field: np.ndarray
    detected_intensity: np.ndarray
    photocurrent_amperes: np.ndarray
    ideal_output_field: np.ndarray
    error_frobenius: float
    fidelity: float
    time_of_flight_ps: float
    energy_mac_fj: float
    snr_db: float
    enob_bits: float


class OpticalTensorCore:
    """N x N Coherent Photonic Mesh Accelerator supporting SVD Factorization and General GEMM.

    Simulates the physical propagation of coherent light through programmable
    interferometer meshes with realistic physical non-idealities:
    - Directional coupler insertion loss and waveguide attenuation
    - Phase shifter precision noise & thermal crosstalk pre-compensation
    - SVD matrix decomposition for arbitrary non-unitary transformations A = U * Sigma * V^dagger
    - Realistic photodetector shot and Johnson noise
    """

    def __init__(
        self,
        n_channels: int = 4,
        mzi_loss_db: float = 0.1,
        waveguide_loss_db_per_cm: float = 1.5,
        phase_noise_std: float = 0.005,
        waveguide_pitch_um: float = 50.0,
        group_index: float = 4.2,
        enable_thermal_crosstalk: bool = True,
        precompensate_crosstalk: bool = True,
    ) -> None:
        self.n = int(n_channels)
        self.mzi_loss_db = float(mzi_loss_db)
        self.waveguide_loss_db_per_cm = float(waveguide_loss_db_per_cm)
        self.phase_noise_std = float(phase_noise_std)
        self.phase_error_std = float(phase_noise_std)
        self.waveguide_pitch_um = float(waveguide_pitch_um)
        self.group_index = float(group_index)
        self.enable_thermal_crosstalk = enable_thermal_crosstalk
        self.precompensate_crosstalk = precompensate_crosstalk

        self.thermal_model = ThermalCrosstalkModel()
        self.detector = Photodetector()

        # Matrices
        self.target_matrix = np.eye(self.n, dtype=complex)
        self.is_unitary_mode: bool = True

        # Unitary decomposition containers
        self.rotations: list[MZIRotation] = []
        self.diag_phases = np.zeros(self.n, dtype=float)

        # SVD containers for general matrices
        self.u_rotations: list[MZIRotation] = []
        self.u_diag: np.ndarray = np.zeros(self.n, dtype=float)
        self.singular_values: np.ndarray = np.ones(self.n, dtype=float)
        self.vh_rotations: list[MZIRotation] = []
        self.vh_diag: np.ndarray = np.zeros(self.n, dtype=float)

        self.set_unitary(np.eye(self.n, dtype=complex))

    def set_unitary(self, u: np.ndarray) -> None:
        """Programs mesh with target unitary matrix U."""
        if u.shape != (self.n, self.n):
            raise ValueError(f"Matrix shape {u.shape} does not match core dimensions ({self.n}, {self.n})")
        self.target_matrix = np.array(u, dtype=complex)
        self.is_unitary_mode = True
        self.rotations, self.diag_phases = reckon_decompose(self.target_matrix)

    def set_general_matrix(self, a: np.ndarray) -> None:
        """Programs core with an arbitrary N x N matrix via SVD: A = U * Sigma * V^dagger."""
        if a.shape != (self.n, self.n):
            raise ValueError(f"Matrix shape {a.shape} does not match core dimensions ({self.n}, {self.n})")
        self.target_matrix = np.array(a, dtype=complex)
        self.is_unitary_mode = False

        u_mat, s_vals, vh_mat = np.linalg.svd(self.target_matrix)
        self.singular_values = s_vals
        self.u_rotations, self.u_diag = reckon_decompose(u_mat)
        self.vh_rotations, self.vh_diag = reckon_decompose(vh_mat)

    def _simulate_mesh_transfer(
        self,
        rotations: list[MZIRotation],
        diag_phases: np.ndarray,
        noisy: bool,
    ) -> np.ndarray:
        """Simulates physical MZI mesh transfer matrix with loss, phase noise, and thermal crosstalk."""
        n_rot = len(rotations)
        raw_thetas = np.array([r.theta for r in rotations])
        raw_phis = np.array([r.phi for r in rotations])

        if noisy and self.enable_thermal_crosstalk and n_rot > 1:
            if self.precompensate_crosstalk:
                # Pre-compensate drive phases
                driven_thetas = self.thermal_model.precompensate(raw_thetas)
                effective_thetas = self.thermal_model.apply_crosstalk(driven_thetas)
            else:
                effective_thetas = self.thermal_model.apply_crosstalk(raw_thetas)
        else:
            effective_thetas = raw_thetas

        u_mesh = np.diag(np.exp(1j * diag_phases))
        loss_per_mzi = 10.0 ** (-self.mzi_loss_db / 20.0)

        for idx, rot in enumerate(reversed(rotations)):
            rev_idx = n_rot - 1 - idx
            m, n_ch = rot.channel_m, rot.channel_n
            th = effective_thetas[rev_idx]
            ph = raw_phis[rev_idx]

            if noisy and self.phase_error_std > 0.0:
                th += np.random.normal(0.0, self.phase_error_std)
                ph += np.random.normal(0.0, self.phase_error_std)

            c = np.cos(th / 2.0)
            s = np.sin(th / 2.0)
            g = np.array([
                [c, s * np.exp(-1j * ph)],
                [-s * np.exp(1j * ph), c]
            ], dtype=complex)
            g_dag = g.conj().T * loss_per_mzi
            u_mesh[[m, n_ch], :] = g_dag @ u_mesh[[m, n_ch], :]

        # Waveguide propagation loss across the chip
        total_length_cm = (self.n * 200.0e-4)  # 200 um per stage in cm
        waveguide_loss_factor = 10.0 ** (-self.waveguide_loss_db_per_cm * total_length_cm / 20.0)
        return waveguide_loss_factor * u_mesh

    def forward(self, x: np.ndarray, noisy: bool = True) -> OpticalGEMMResult:
        """Executes coherent optical matrix-vector multiplication."""
        x_vec = np.asarray(x, dtype=complex)
        if x_vec.shape != (self.n,):
            raise ValueError(f"Input vector shape {x_vec.shape} != ({self.n},)")

        ideal_out = self.target_matrix @ x_vec

        if self.is_unitary_mode:
            if noisy:
                mesh_mat = self._simulate_mesh_transfer(self.rotations, self.diag_phases, noisy=True)
            else:
                mesh_mat = reckon_reconstruct(self.rotations, self.diag_phases, self.n)
            actual_out = mesh_mat @ x_vec
        else:
            # SVD Mode: x -> V^dagger -> Sigma -> U
            if noisy:
                vh_mesh = self._simulate_mesh_transfer(self.vh_rotations, self.vh_diag, noisy=True)
                u_mesh = self._simulate_mesh_transfer(self.u_rotations, self.u_diag, noisy=True)
            else:
                vh_mesh = reckon_reconstruct(self.vh_rotations, self.vh_diag, self.n)
                u_mesh = reckon_reconstruct(self.u_rotations, self.u_diag, self.n)
            # Attenuator bank
            actual_out = u_mesh @ (self.singular_values * (vh_mesh @ x_vec))

        detected_intensity = np.abs(actual_out) ** 2
        # Scale intensity to milliwatts optical power for detector model
        optical_power_w = detected_intensity * 1.0e-3
        photocurrents, det_metrics = self.detector.detect(optical_power_w, noisy=noisy)

        # Physics metrics
        c_speed = 3e8  # m/s
        total_mesh_length_m = (self.n * 200e-6) * (2 if not self.is_unitary_mode else 1)
        tof_ps = ((total_mesh_length_m * self.group_index) / c_speed) * 1e12
        energy_mac_fj = 15.0 + (0.5 * self.n)

        frobenius_err = float(np.linalg.norm(actual_out - ideal_out))
        if self.is_unitary_mode:
            fid = matrix_fidelity(self.target_matrix, mesh_mat)
        else:
            norm_target = np.linalg.norm(self.target_matrix)
            fid = max(0.0, 1.0 - (frobenius_err / (norm_target + 1e-12)))

        return OpticalGEMMResult(
            output_field=actual_out,
            detected_intensity=detected_intensity,
            photocurrent_amperes=photocurrents,
            ideal_output_field=ideal_out,
            error_frobenius=frobenius_err,
            fidelity=fid,
            time_of_flight_ps=tof_ps,
            energy_mac_fj=energy_mac_fj,
            snr_db=det_metrics["snr_db"],
            enob_bits=det_metrics["enob_bits"],
        )
