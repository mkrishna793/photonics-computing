# 🌐 Photonics Computing: Autonomous Agent Operating Protocol

Welcome to the **Photonics Computing** workspace. This repository is fully scaffolded and operational with the **Prime Agent Recursive Language Model (RLM)** architecture, integrating:
1. **`/prime-coder`**: Dual-Kernel (IPython & xeus-cpp C++) Engineering Engine with Superpowers TDD.
2. **`/prime-research`**: PRAXIST Lineage-Centered Multi-Agent Research Framework with empirical IPython verification.
3. **`OpenEvolve Prime`**: Evolutionary Program Synthesis & Adversarial Red-Team Falsification Engine.

---

## 📁 Repository Architecture

```
photonics computing/
├── .prime-kernel/                 # Isolated SQLite engine & REPL state (gitignored)
│   ├── workspace.db              # Lineage vault, Task DAG, PRAXIST graph, FTS5 recall
│   └── .gitignore
├── .prime-research/               # PRAXIST Multi-Agent Research Evidence Graph
│   ├── frontier/                 # Pareto-optimal verified findings & physical laws
│   ├── incubator/                # Active multi-generation research hypotheses
│   ├── gems/                     # Non-obvious physical breakthroughs & papers
│   ├── negative_evidence/        # Confirmed dead-ends (avoids redundant token spend)
│   ├── aspects/                  # Subagent high-density finding packets (<500 tokens)
│   ├── raw/                      # Ephemeral web scrapes and simulation dumps (gitignored)
│   └── README.md
├── src/
│   └── photonics/
│       ├── __init__.py           # Package exports
│       ├── core/                 # Reck & Clements unitary matrix decompositions U(N)
│       │   ├── __init__.py
│       │   └── unitary.py
│       ├── devices/              # Hardware component models (MZI, Ring Resonators)
│       │   ├── __init__.py
│       │   ├── mzi.py
│       │   └── ring_resonator.py
│       ├── simulation/           # Coherent Optical Tensor Core & GEMM engine
│       │   ├── __init__.py
│       │   └── optical_engine.py
│       └── benchmarks/           # Energy (fJ/MAC), latency (ps), and fidelity profiling
│           ├── __init__.py
│           └── benchmark_suite.py
├── tests/                         # Superpowers TDD test suite
│   ├── test_mzi.py               # Unit tests for MZI & MRR components
│   ├── test_unitary.py           # Reck unitary decomposition proofs
│   └── test_optical_engine.py    # Optical GEMM & physical benchmarking tests
├── scripts/                       # CLI & REPL utilities
│   ├── prime_repl_session.py     # Persistent RLM REPL session connected to workspace.db
│   ├── run_praxist_wave.py       # PRAXIST research generation runner & status tool
│   └── verify_integrity.py       # Anti-Early-Victory code integrity gate
├── pyproject.toml                 # Package dependencies & pytest configuration
├── requirements.txt               # Direct pip requirements
├── .cursorrules                   # Cursor IDE rules
├── CLAUDE.md                      # Claude Code / Claude Desktop rules
├── .windsurfrules                 # Windsurf rules
├── AGENTS.md                      # This protocol document
└── README.md                      # High-level overview & quickstart guide
```

---

## ⚡ Prime Coder Protocol (`/prime-coder`)

Before writing or editing code in this workspace, follow these 4 phases:

### Phase 1: Writing Plans (Task DAG)
- Decompose complex features or fixes into atomic, ordered steps.
- Register tasks in `.prime-kernel/workspace.db`:
  ```python
  from prime_core import prime_db
  prime_db.create_task_dag([
      {"id": "step-1", "description": "Write failing unit test for Clements mesh", "status": "pending"},
      {"id": "step-2", "description": "Implement rectangular nullification loop", "dependencies": ["step-1"], "status": "pending"},
      {"id": "step-3", "description": "Run verify_integrity.py pre-flight gate", "dependencies": ["step-2"], "status": "pending"}
  ])
  ```

### Phase 2: Systematic Debugging (Root-Cause First)
- Never apply speculative random edits.
- Use the persistent IPython REPL or interactive C++20 kernel (`xeus-cpp`) to empirically verify mathematical equations, pointer layouts, or optical transfer matrices before altering code.

### Phase 3: Test-Driven Development (TDD)
- Write the failing unit test in `tests/test_*.py` first.
- Run pytest to verify the failure mode:
  ```bash
  PYTHONPATH=src ./.venv/bin/pytest tests/test_*.py
  ```
- Implement the minimal code required to pass.
- Verify test passes.

### Phase 4: Anti-Early-Victory Verification Gate
- **Never declare victory after 1 passing test.**
- Run the immutable workspace verification gate:
  ```bash
  ./.venv/bin/python scripts/verify_integrity.py
  ```
- All test runs and syntax passes are logged to `workspace.db` (`verification_log` table).

---

## 🔬 Prime Research Protocol (`/prime-research`)

When performing deep research, literature surveys, or physics evaluations:

### 1. Hub-and-Spoke Context Shield
- Spawn research subagents using `invoke_subagent` with `Model: "flash"`.
- Subagents **never** communicate with each other.
- Raw web scrapes and lengthy papers are stored out-of-band in `.prime-research/raw/` or the SQLite vault (`prime_db.store_variable`).
- Subagents return strictly a **high-density finding packet (< 500 tokens)**:

```markdown
### Finding Packet:
- **Aspect**: [Photonic Topic]
- **Mechanism**: [1-2 sentences on physical/causal optics]
- **Metrics**: [Insertion loss (dB), Energy/MAC (fJ), Latency (ps), FSR (nm)]
- **Caveats**: [Fabrication tolerances, thermal drift, crosstalk]
- **Proposed Lane**: [frontier | incubator | gems | negative_evidence]
- **Sources**: [Verified URLs / DOIs]
```

### 2. The 4 PRAXIST Retention Lanes
- **`Frontier`**: Verified Pareto-optimal architectures and mathematical proofs.
- **`Incubator`**: Active hypotheses under multi-generational investigation.
- **`Gems`**: Rare, surprising breakthroughs.
- **`Negative Evidence`**: Confirmed dead-ends and disproven claims. **Check this ledger before launching new research to avoid wasting tokens.**

### 3. Empirical REPL & Citation Gates
- Verify numerical claims and formulas via `prime_orchestrator.empirically_verify_with_repl(python_code)`.
- Validate all citations via `prime_orchestrator.verify_citations_in_text()`.

---

## 🧬 OpenEvolve Prime Engine

For complex algorithmic bottlenecks (e.g. optimizing optical phase shifter configurations or minimizing mesh waveguide crossings):

1. **Multi-Island Architecture**:
   - **Island 0**: Structural AST mutation & heuristic exploration.
   - **Island 1**: Algorithmic refinement, parameter tuning, crossover.
   - **Island 2**: Stress testing, boundary fuzzing, Pareto frontier verification.
2. **In-Process REPL Fitness Gate**: Evaluated microsecond latency and accuracy with zero hallucinated metrics.
3. **Adversarial Red-Team Falsification**: Subject candidates to extreme edge cases before promotion to the Pareto Frontier.
