# 💡 Photonics Computing Accelerator Engine

A high-performance coherent photonic computing and optical matrix-vector acceleration (GEMM) platform, powered by the **Prime Agent Recursive Language Model (RLM)** architecture, **Superpowers TDD**, and the **Sapient PRAXIST Multi-Agent Research Lineage**.

---

## 🚀 Key Capabilities

- **Coherent Optical Matrix-Vector Multiplication**: Simulates optical propagation through programmable Mach-Zehnder Interferometer (MZI) meshes.
- **Unitary Matrix Decomposition**: Exact Reck et al. (PRL 1994) triangular mesh decomposition and Clements et al. (Optica 2016) rectangular mesh decomposition with machine-precision reconstruction ($\|U - U_{\text{recon}}\|_F < 10^{-12}$).
- **Integrated Hardware Device Models**:
  - **Mach-Zehnder Interferometer (MZI)**: Directional couplers, thermal/electro-optic phase shifters ($\theta, \phi$), insertion loss, and phase noise tolerance.
  - **Micro-Ring Resonators (MRR)**: Through/drop ports, Free Spectral Range (FSR), Q-factor, and WDM spectral weighting.
- **Physical Benchmarking**: Energy dissipation ($\text{fJ/MAC}$), time-of-flight latency ($\text{ps}$), and optical matrix fidelity compared against modern electronic processors.
- **Dual-Kernel Engine**: Integrated with persistent Python IPython and C++20 (`xeus-cpp`) kernels via Prime Agent RLM.

---

## 🏗️ Quickstart

### 1. Environment Activation
```bash
# Activate virtual environment
source .venv/bin/activate
```

### 2. Run Test Suite
```bash
PYTHONPATH=src ./.venv/bin/pytest -v
```

### 3. Run Pre-Flight Code Integrity Gate
```bash
./.venv/bin/python scripts/verify_integrity.py
```

### 4. Interactive RLM REPL Session
```bash
./.venv/bin/python scripts/prime_repl_session.py
```

### 5. Multi-Agent PRAXIST Research Runner
```bash
# Plan a new research wave with orthogonal Quality-Diversity lanes
./.venv/bin/python scripts/run_praxist_wave.py --plan --topic "Clements vs Reck MZI Mesh Scaling in Silicon Photonics"

# View current Frontier, Incubator, and Negative Evidence ledger
./.venv/bin/python scripts/run_praxist_wave.py --status
```

---

## 🛠️ Python Usage Example

```python
import numpy as np
from scipy.stats import unitary_group
from photonics import OpticalTensorCore, MachZehnderInterferometer

# 1. Initialize an 8x8 Coherent Photonic Mesh
core = OpticalTensorCore(n_channels=8, mzi_loss_db=0.05, phase_noise_std=0.002)

# 2. Program target unitary matrix
target_u = unitary_group.rvs(8)
core.set_unitary(target_u)

# 3. Propagate coherent optical input field
x_in = np.ones(8, dtype=complex) / np.sqrt(8)
result = core.forward(x_in, noisy=True)

print(f"Matrix Fidelity: {result.fidelity:.6f}")
print(f"Time-of-Flight Latency: {result.time_of_flight_ps:.2f} ps")
print(f"Energy per MAC: {result.energy_mac_fj:.2f} fJ/MAC")
```

---

## 🏛️ Prime Agent Architecture

This project is configured with:
- **`.prime-kernel/workspace.db`**: Project-isolated SQLite database tracking task DAGs, evolutionary lineages, and test verifications.
- **`.prime-research/`**: PRAXIST evidence graph retaining verified findings (`Frontier`), active hypotheses (`Incubator`), discoveries (`Gems`), and disproven dead-ends (`Negative Evidence`).
- **`AGENTS.md`**: Full operational protocol for AI agents and slash commands `/prime-coder` and `/prime-research`.
