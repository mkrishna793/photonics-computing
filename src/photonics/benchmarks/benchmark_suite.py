"""Benchmark suite comparing coherent photonic cores to electronic digital processors."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.stats import unitary_group
from photonics.simulation.optical_engine import OpticalTensorCore


@dataclass
class BenchmarkProfile:
    dimension: int
    optical_latency_ps: float
    electronic_est_latency_ps: float
    optical_energy_per_mac_fj: float
    electronic_energy_per_mac_fj: float
    energy_advantage_ratio: float
    latency_advantage_ratio: float
    matrix_fidelity: float


class PhotonicBenchmarkSuite:
    """Rigorous physical and computational benchmarking for photonic tensor hardware."""

    def __init__(self, electronic_baseline_energy_fj: float = 2500.0) -> None:
        """
        electronic_baseline_energy_fj: Estimated energy per INT8/FP16 MAC on modern 5nm electronic TPU/GPU (~2,500 fJ).
        """
        self.electronic_energy_fj = float(electronic_baseline_energy_fj)

    def benchmark_core(self, n_channels: int = 8, n_trials: int = 10) -> BenchmarkProfile:
        """Profiles an N x N photonic core across random unitary transformations."""
        core = OpticalTensorCore(n_channels=n_channels, phase_noise_std=0.002, mzi_loss_db=0.05)
        
        latencies_ps = []
        energies_fj = []
        fidelities = []

        for _ in range(n_trials):
            u_test = unitary_group.rvs(n_channels)
            core.set_unitary(u_test)
            x_test = np.random.randn(n_channels) + 1j * np.random.randn(n_channels)
            x_test /= np.linalg.norm(x_test)

            res = core.forward(x_test, noisy=True)
            latencies_ps.append(res.time_of_flight_ps)
            energies_fj.append(res.energy_mac_fj)
            fidelities.append(res.fidelity)

        avg_lat = float(np.mean(latencies_ps))
        avg_energy = float(np.mean(energies_fj))
        avg_fid = float(np.mean(fidelities))

        # Electronic latency estimate: SRAM read + ALU execution (~1.5 ns = 1500 ps)
        electronic_lat_ps = 1500.0

        energy_adv = self.electronic_energy_fj / avg_energy
        lat_adv = electronic_lat_ps / avg_lat

        return BenchmarkProfile(
            dimension=n_channels,
            optical_latency_ps=avg_lat,
            electronic_est_latency_ps=electronic_lat_ps,
            optical_energy_per_mac_fj=avg_energy,
            electronic_energy_per_mac_fj=self.electronic_energy_fj,
            energy_advantage_ratio=energy_adv,
            latency_advantage_ratio=lat_adv,
            matrix_fidelity=avg_fid,
        )
