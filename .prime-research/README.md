# 🔬 PRAXIST Research Lineage & Evidence Graph

This directory houses the inherited evidence graph and research dossiers for **Photonics Computing**, structured according to the **Sapient PRAXIST Lineage Architecture** powered by the **Prime Agent RLM persistent IPython kernel**.

---

## 🏛️ The 4 Durable Retention Lanes

All research findings are classified into one of 4 strict retention lanes:

| Retention Lane | Directory | Definition & Retention Criteria |
| :--- | :--- | :--- |
| **`Frontier`** | `frontier/` | Highest-confidence, Pareto-optimal verified findings, proven architectures, and empirical benchmark limits. |
| **`Incubator`** | `incubator/` | Active hypotheses under multi-generational investigation (e.g. Clements vs Reck MZI mesh scaling bounds). |
| **`Gems`** | `gems/` | Rare, surprising, non-obvious breakthroughs, novel physical mechanisms, or unheralded literature discoveries. |
| **`Negative Evidence`** | `negative_evidence/` | Confirmed dead-ends, disproven theories, high-loss topologies, or physical limits (e.g. thermal crosstalk breakdowns). Sub-agents check this ledger first to **never waste tokens re-researching dead ends**. |

---

## 🛡️ Research Subagent Rules (Strict Hub-and-Spoke Context Shield)

When spawning or acting as a research subagent:
1. **Subagents NEVER communicate with each other**: Eliminates $O(N^2)$ chatter and prevents hallucinated telephone distortion.
2. **Context Isolation**: Subagents run in an isolated environment (`Model: "flash"`).
3. **Token Shield (< 500 tokens)**: Save raw web scrapes, PDFs, and full markdown notes to `.prime-research/aspects/aspect_<name>.md` or the project SQLite vault (`prime_db.store_variable`). Subagents return strictly a high-density packet adhering to the template below.
4. **Empirical Verification Gate**: Benchmark claims, latency deltas, insertion losses, and power dissipation formulas must be empirically verified via `prime_orchestrator.empirically_verify_with_repl(python_code)` before committing to the Frontier.
5. **Blackbox CitationAgent Gate**: Every claim must link to a valid source paper, DOI, or arXiv citation.

---

## 📋 Subagent Finding Packet Template (< 500 Tokens)

```markdown
### Finding Packet:
- **Aspect**: [Photonic Architecture / Component / Algorithmic Facet]
- **Mechanism**: [1-2 sentences explaining the causal physics, optical interference, or routing logic]
- **Metrics**: [Empirical data: Insertion loss (dB), Energy/MAC (fJ/OP), Latency (ps), Bandwidth (GHz)]
- **Caveats**: [Fabrication tolerances, thermal drift, phase noise, or scaling bottlenecks]
- **Proposed Lane**: [frontier | incubator | gems | negative_evidence]
- **Sources**: [arXiv / Nature Photonics / IEEE JSTQE URLs / DOIs]
```
