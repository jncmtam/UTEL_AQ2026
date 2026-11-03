# AGQO — Verified LLM-Designed QAOA for Portfolio Repair

AGQO studies whether an LLM can design useful QAOA circuits for maintaining a
constrained US-equity portfolio. The LLM designs initialization, exchange gates,
scheduling and parameter sharing. Numerical code computes financial coefficients;
a canonical compiler owns the cost Hamiltonian. QAOA proposes asset combinations,
and a common classical allocator assigns weights.

**Current evidence:** the software pipeline and structural controls run locally.
An exact conserved-cardinality backend now executes a 30-asset/6-holding case
(593,775 supports). A published 386-asset US corpus is admitted for conditional
algorithm comparisons. The historical investment dataset remains blocked pending
identity/corporate-action review.
No production model, investment outperformance or quantum advantage is established.

## Start here

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,simulator,llm-modal,published-data]'
.venv/bin/python -m pytest -q
.venv/bin/python -m agqo.research trajectory --source synthetic --output results/research/my_demo
.venv/bin/python -m agqo.research serve --output results/research/my_demo --port 8765
```

Open http://127.0.0.1:8765/ for the English decision application. Compare the current
holdings, exclusions, sector limit and turnover with hold, SCIP, local swap and
QAOA alternatives. UI evaluation uses synthetic data and local simulation; it never
launches an unbounded GPU request.

## Evidence before experiments

- [Published results and model rationale](docs/research/EVIDENCE_REVIEW.md).
- [Measured dataset suitability](docs/research/DATA_SUITABILITY.md).
- [Technical choices and stop rules](docs/research/TECHNICAL_DECISIONS.md).
- [Implementation protocol](docs/research/IMPLEMENTATION_PROTOCOL.md).
- [Worklog](docs/research/WORKLOG.md), updated as measurements and decisions change.
- [Completion review and measured remaining gaps](docs/research/COMPLETION_REPORT.md).
- [Agent handoff](AGENTS.md), read this first when resuming work.

## Reproducible workflow

```bash
# Audit free US-equity data; missing evidence returns exit code 2.
.venv/bin/python -m agqo.research candidate
.venv/bin/python -m agqo.research fetch
.venv/bin/python scripts/assess_us_dataset.py
.venv/bin/python -m agqo.research audit

# Non-LLM initialization/encoding/adaptive controls.
.venv/bin/python -m agqo.research baseline --output results/research/my_baselines

# Pinned published US returns; conditional algorithm scope, not an unbiased backtest.
.venv/bin/python -m agqo.research published-fetch
.venv/bin/python -m agqo.research published-study --output results/research/my_published

# Complete software workflow; market blockers remain explicit (exit code 2).
.venv/bin/python -m agqo.research pipeline --output results/research/my_pipeline

# Bounded, preregistered specialist interface probe. Requires Modal authentication.
.venv/bin/python -m agqo.research probe --mode modal --models quasar4 --output results/research/my_probe

# A structural design study, including common allocation and failed proposals.
.venv/bin/python -m agqo.research smoke --mode offline --output results/research/my_structural

# Read an existing complete run without inference charges.
.venv/bin/python -m agqo.research replay --output results/research/my_demo

# Admitted market data only; writes all artifacts even when blocked.
.venv/bin/python -m agqo.research trajectory --source market --output results/research/my_market
```

Use a new output directory when changing a frozen protocol. Original raw responses,
interruptions and unsuccessful runs remain evidence. A cached artifact is not a
new live model result. See [the user guide](docs/USER_GUIDE.md) for the data contract.

## What is implemented

| Component | Behavior |
|---|---|
| Financial specification | Tracking/cost or separate risk/return; support constraints separated from weight/turnover constraints |
| Allocation and references | CLARABEL allocation, support-proxy audit, full SCIP support/weight reference, allocation-aware swaps |
| Accounting | Dollar holdings and cash, fees paid from NAV, drift, one-session execution lag, no account reset |
| Quantum compiler | Direct QUBO/Ising coefficients and explicit slack; optional certified subspace encoding; no cost truth table in compilation |
| Verification | Schema, source/hash, cost coefficients, gate semantics, invariants, NumPy/Qiskit checks, activity and resources |
| Designs | LLM-owned gate structure, fixed/rule/random/adaptive controls, Dicke reference, reuse and mutation interfaces |
| Modal | Pinned checkpoints, shared model registry, CPU prefetch, sequential bounded GPU work, cached requests, ledger and receipts |
| Application | English mandate editor, decision comparison, trades and verification, read-only experiment replay |
| Reporting | JSON/CSV/QASM/QPY plus English Markdown results, progress and uncertainty/claim limits |

The full statevector is capped at 16 total qubits. GateIR v2 supports up to 40 asset
qubits with certified fixed-cardinality execution, capped at 2,000,000 represented
states including explicit slack. V1's 12-asset schema stays unchanged. The larger
backend uses an analytic gate certificate and small-instance crosschecks; it does
not claim an independent full Qiskit statevector check at 30 qubits. Both backends
are classical simulation. Compilation alone does not imply hardware execution.
Dicke synthesis in the baseline study is an explicit small reference, whose cost
is reported; it is not the efficient preparation algorithm from the cited paper.
The gradient baseline is ADAPT-inspired, with its extra classical evaluations
counted, rather than a claim of reproducing every paper setting.

## Artifacts and status

Every trajectory/pipeline produces `protocol.json`, `dataset_manifest.json`,
`decisions.jsonl`, `circuits/`, `metrics.csv`, `cost_report.json`, `RESULTS.md`, and
`PROGRESS.md`. Blocked market runs still produce this contract with a reason and
empty decision records. Specialist probes and baseline studies additionally keep
their task-specific protocols and raw records.

Read [project status](docs/PROJECT_STATUS.md) and [result semantics](docs/RESULTS_SPEC.md).
A favorable energy or sampled optimum does not establish financial utility.
Common postprocessing is charged; allocation failures remain visible.

## Historical compatibility

Existing `agqo`, `agqo-repair` and `agqo-synthesize` entry points remain available.
They include historical experiments and bilingual input parsing. The maintained
US workflow is `agqo-research`. Historical VN30 results and Vietnamese explanatory
material are preserved under `results/` and `docs/legacy/`; they are not evidence
for this US-equity study. Raw provider payloads stay local because redistribution
rights have not been established.
