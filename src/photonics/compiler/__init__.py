"""Lumiris-Unified Compiler Pipeline: Bounded Arithmetic, Transcendental Approximations, and Physical Hardware Lowering."""

from photonics.compiler.ir import (
    EncodingType,
    Interval,
    SSANode,
    SSAGraph,
    verify_graph_contracts,
)
from photonics.compiler.transcendental import (
    ChebyshevApproximation,
    PadeApproximation,
    approximate_transcendental,
)
from photonics.compiler.lowering import (
    OpticalMeshBackend,
    MemristorCrossbarBackend,
    CompiledHardwareBundle,
)
from photonics.compiler.certificate import (
    CertificateGenerator,
    IndependentCertificateAuditor,
    VerificationStatus,
)

__all__ = [
    "EncodingType",
    "Interval",
    "SSANode",
    "SSAGraph",
    "verify_graph_contracts",
    "ChebyshevApproximation",
    "PadeApproximation",
    "approximate_transcendental",
    "OpticalMeshBackend",
    "MemristorCrossbarBackend",
    "CompiledHardwareBundle",
    "CertificateGenerator",
    "IndependentCertificateAuditor",
    "VerificationStatus",
]
