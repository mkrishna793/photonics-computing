# 💡 Lumiris: Photonic & Memristive Computing Compiler Platform

Lumiris is a formally verified, physics-aware compiler and execution platform for optical and analog computing, integrating:
1. **Bounded Interval SSA Compiler & Exact Rational Certificates**: Fail-closed physical safety, nonzero-divisor verification, and dual-verification auditing.
2. **Coherent Optical Matrix-Vector Core (GEMM)**: SVD factorizations ($A = U \Sigma V^\dagger$), Reck/Clements MZI meshes, complex field propagation, and active thermal crosstalk inversion.
3. **Differential Memristor Crossbar Engine**: In-memory computing with differential conductance pairs ($W = \alpha(G^+ - G^-)$), finite DAC quantization, wire resistance ($IR$ drops), and retention drift.
4. **L1 Transcendental Approximation Pass**: Chebyshev minimax polynomials and Padé approximants for $\exp(x), \tanh(x), \text{sigmoid}(x), \sin(x), \cos(x), \sqrt{x}$ with certified error bounds.
5. **Lean 4 / Mathlib Formal Proofs**: Mathematical theorems covering optical energy conservation ($M^\dagger M = I$), DAC monotonicity, and interval error compositions.

---

## 🏛️ System Architecture

```
L0/L1 Math Frontend    Any real mathematics: expressions, tensors, activations
      │                Approximations: exp, tanh, sigmoid -> Chebyshev minimax Horner form
      ▼
L2 SSA Text IR         Core Analog Algebra (+, -, *, /) with tight interval bounds [lo, hi]
(lumiris 1)            Explicit domain contracts & composed absolute error budgets
      │
      ▼
L3 Physical Lowering   Maps abstract ops to physical devices:
                       ├── OpticalMeshBackend: SVD + Reck/Clements MZIs + Thermal Crosstalk Inversion
                       └── MemristorCrossbarBackend: Differential Conductance + IR Drop Analysis
      │
      ▼
Independent Gate       Dual-Verification Auditor (scripts/check_certificate.py)
(Cryptographic SHA256) Re-evaluates exact Fraction arithmetic without trusting the compiler
      │
      ▼
L4 Physical Knobs      Actuator signals: DAC integer codes, heater voltages (V), conductances (G)
      │
      ▼
L5 Small World (SW-1)  Simulation & physics validation: optical time-of-flight, shot/thermal noise,
                       and energy conservation (residual <= 10^-12)
```

---

## 🚀 Quickstart

### 1. Python Environment Setup
```bash
# Setup virtual environment with dependencies
source .venv/bin/activate
```

### 2. Run Comprehensive Test Suite (50/50 Tests)
```bash
PYTHONPATH=src:scripts pytest -v
```

### 3. Run Rust Reference Compiler & MZI Demonstration
```bash
# Executable demonstration script (Rust compiler -> Python checker -> SW-1 simulation)
./scripts/demo.sh artifacts/demo-run
```

---

## 💻 Python Usage Example

```python
import numpy as np
from photonics import (
    OpticalMeshBackend,
    MemristorCrossbarBackend,
    approximate_transcendental,
    OpticalTensorCore,
    Interval
)

# 1. Compile arbitrary matrix to Silicon Photonic MZI Mesh
optical_compiler = OpticalMeshBackend()
weight_matrix = np.array([
    [ 0.45, -0.22,  0.78,  0.11],
    [-0.15,  0.64, -0.33,  0.52],
    [ 0.81, -0.40,  0.19, -0.67],
    [-0.30,  0.55, -0.85,  0.24]
])
bundle = optical_compiler.lower_gemm(weight_matrix, node_name="photonic_gemm")
print(f"Total MZIs: {bundle.control_registers['total_mzis']} | Bound: {bundle.physical_error_bound:.6f}")

# 2. Simulate coherent optical propagation with thermal crosstalk pre-compensation
core = OpticalTensorCore(n_channels=4, enable_thermal_crosstalk=True, precompensate_crosstalk=True)
core.set_general_matrix(weight_matrix)
res = core.forward(np.ones(4) / 2.0)
print(f"Time-of-Flight Latency: {res.time_of_flight_ps:.2f} ps | ENOB: {res.enob_bits:.1f} bits")

# 3. Compile a Sigmoid Activation Function with Certified Error Bound < 1e-3
sig_approx = approximate_transcendental("sigmoid", Interval(-2.0, 2.0), target_tolerance=1e-3)
print(f"Sigmoid Degree {sig_approx.degree} Polynomial Error: {sig_approx.max_truncation_error:.6f}")
```

---

## 📁 Repository Map

```text
├── src/photonics/
│   ├── compiler/             # Lumiris SSA IR, Chebyshev approximations, Lowering, Certificates
│   │   ├── ir.py             # SSA interval arithmetic, physical encodings, domain checks
│   │   ├── transcendental.py # Chebyshev minimax & Pade polynomial expansions in Horner form
│   │   ├── lowering.py       # SVD optical mesh & differential memristor backends
│   │   └── certificate.py    # Independent Fraction auditor & cryptographic SHA-256 signatures
│   ├── core/
│   │   └── unitary.py        # Reck & Clements unitary matrix decompositions into MZI Givens rotations
│   ├── devices/
│   │   ├── mzi.py            # Mach-Zehnder Interferometers & Thermal Crosstalk Inversion
│   │   ├── ring_resonator.py # Micro-Ring Resonators (FSR, Q-factor, spectral weighting)
│   │   └── memristor.py      # Differential ReRAM crossbars, IR drops, retention drift
│   ├── simulation/
│   │   └── optical_engine.py # OpticalTensorCore, complex field propagation, PIN photodetectors
│   └── benchmarks/
│       └── benchmark_suite.py# Photonic vs Electronic comparative energy/latency profiling
├── tests/                    # Comprehensive unit tests (50/50 passing in 1.20s)
├── scripts/                  # Upstream verification, checker, and simulation runners
├── Lean-Semantics/
│   ├── rust/                 # Offline dependency-free Rust reference compiler
│   └── lean/                 # Lean 4 / Mathlib formal verification theorems
├── docs/                     # Verification boundaries, IR formats, and milestones
└── pyproject.toml            # Package configuration
```
