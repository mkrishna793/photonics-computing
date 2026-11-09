"""Photonics Computing Engine: Optical Matrix-Vector Acceleration and Coherent Mesh Simulation.

Powered by Prime Agent RLM Architecture and PRAXIST Research Lineage.
"""

from photonics.devices.mzi import MachZehnderInterferometer, DirectionalCoupler
from photonics.devices.ring_resonator import MicroRingResonator
from photonics.core.unitary import clements_decompose, clements_reconstruct, reckon_decompose
from photonics.simulation.optical_engine import OpticalTensorCore, OpticalGEMMResult
from photonics.benchmarks.benchmark_suite import PhotonicBenchmarkSuite

__all__ = [
    "MachZehnderInterferometer",
    "DirectionalCoupler",
    "MicroRingResonator",
    "clements_decompose",
    "clements_reconstruct",
    "reckon_decompose",
    "OpticalTensorCore",
    "OpticalGEMMResult",
    "PhotonicBenchmarkSuite",
]

__version__ = "0.1.0"
