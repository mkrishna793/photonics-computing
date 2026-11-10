"""Photonics & Memristive Computing Engine: Optical Tensor Core, Memristor Crossbars, and Lumiris Compiler Pipeline.

Powered by Prime Agent RLM Architecture and PRAXIST Research Lineage.
"""

from photonics.devices.mzi import MachZehnderInterferometer, DirectionalCoupler, ThermalCrosstalkModel
from photonics.devices.ring_resonator import MicroRingResonator
from photonics.devices.memristor import MemristorCrossbar, MemristorConfig
from photonics.core.unitary import clements_decompose, clements_reconstruct, reckon_decompose, matrix_fidelity
from photonics.simulation.optical_engine import OpticalTensorCore, OpticalGEMMResult, Photodetector, PhotodetectorConfig
from photonics.benchmarks.benchmark_suite import PhotonicBenchmarkSuite
from photonics.compiler.ir import SSAGraph, SSANode, Interval, EncodingType, verify_graph_contracts
from photonics.compiler.transcendental import ChebyshevApproximation, PadeApproximation, approximate_transcendental, lower_approximation_to_ssa
from photonics.compiler.lowering import OpticalMeshBackend, MemristorCrossbarBackend, CompiledHardwareBundle
from photonics.compiler.certificate import CertificateGenerator, IndependentCertificateAuditor, VerificationStatus

__all__ = [
    # Devices
    "MachZehnderInterferometer",
    "DirectionalCoupler",
    "ThermalCrosstalkModel",
    "MicroRingResonator",
    "MemristorCrossbar",
    "MemristorConfig",
    # Core unitary
    "clements_decompose",
    "clements_reconstruct",
    "reckon_decompose",
    "matrix_fidelity",
    # Simulation
    "OpticalTensorCore",
    "OpticalGEMMResult",
    "Photodetector",
    "PhotodetectorConfig",
    # Benchmarking
    "PhotonicBenchmarkSuite",
    # Compiler & Verification
    "SSAGraph",
    "SSANode",
    "Interval",
    "EncodingType",
    "verify_graph_contracts",
    "ChebyshevApproximation",
    "PadeApproximation",
    "approximate_transcendental",
    "lower_approximation_to_ssa",
    "OpticalMeshBackend",
    "MemristorCrossbarBackend",
    "CompiledHardwareBundle",
    "CertificateGenerator",
    "IndependentCertificateAuditor",
    "VerificationStatus",
]

__version__ = "0.2.0"
