# AGQO agent handoff

Updated: 2026-11-03, Asia/Ho_Chi_Minh. Read this first; inspect only modules needed
for the next action. Update this file and the worklog after meaningful changes.

## User contract and workflow
- Implement the English US-equity LLM/QAOA research application; preserve honest
  negative results and commit/push to the existing GitHub branch.
- Before choosing a model/benchmark/experiment, record published evidence, data
  suitability, alternative, budget, acceptance criteria and stop rule in Markdown.
- LLM designs circuits, never preselects stock winners. Numerical code owns
  financial coefficients; compiler locks cost. QAOA samples supports; common
  allocator assigns weights. Primary task is mandate-aware tracking/cost repair.
- US data is free-source only. Do not replace missing securities or certify
  historical identity/actions from current ticker names. Market gate stays closed
  until source review is complete. Synthetic data validates software only.
- Modal usage is authorized under config/synthesis-expanded-budget.json (USD150
  reservation ceiling per experiment, not an account balance). Sequential bounded
  GPU jobs; no speculative escalation to 397B/480B. No new paid job is scheduled.
- Active code/docs/UI/reports are English. Raw historical evidence and archived
  compatibility material are preserved. Chat with the user may be Vietnamese.

## Location and commands
- Root: /Users/jant/Documents/ChatGPT/AI-Quantum Challenge 2026
- Branch: codex/verified-large-model-synthesis
- Remote: https://github.com/jncmtam/UTEL_AQ2026.git
- Python: .venv/bin/python, Python 3.12. Editable package installed; lock file
  includes CVXPY 1.9.3, PySCIPOpt 6.3.0, Qiskit, SciPy and Modal.
- Tests: .venv/bin/python -m pytest -q
- Lint: .venv/bin/ruff check agqo/research tests/test_research.py --select F
- CLI: .venv/bin/agqo-research --help (or python -m agqo.research).
- Demo: python -m agqo.research serve --output results/research/delivery_pipeline_v1
  --port 8765. Local server was running on 127.0.0.1:8765 at last check.
- Data EDA: python scripts/assess_us_dataset.py. Raw provider files stay gitignored.
- Modal inventory: .venv/bin/modal app list --json. Profile data1; both apps had
  zero tasks after the bounded probe. Do not relaunch a completed probe by default.

## Verified current evidence — do not repeat unnecessarily
- All 112 tests passed; static F checks passed; English UI/API integration checked.
- delivery_pipeline_v1 completed software stages with explicit market data blockers;
  contains full JSON/CSV/circuit/Markdown artifact contract and diagnostic figures.
- delivery_structural_v1: 15 accepted controls (12 circuits + 3 classical uniform
  feasible controls), structural diagnostics only, not model qualification.
- baseline_evidence_v1: 12/12 independent circuit verifications. Dense Dicke can
  improve feasibility with more CX. Gradient baseline uses extra exact classical
  evaluations; do not advertise a same-budget win.
- quasar_interface_v1: one bounded live batch, 1/3 accepted: GateIR transfer passed;
  two native QASM tasks violated the contract. Raw outputs/receipts preserved.
  No repair or model-size escalation. No production model is qualified.
- Probe reservation USD1.37 is not an invoice. Monthly metered snapshots increased
  from ~0.5200 to ~0.7365 USD during the run; not an isolated final job bill.
- Older v1: 80B 1/3 valid, 30B 0/3. Typed v2: both 2/3; fixed better on N=6.
  128 uniform feasible draws on the old N=8 case already find optimum ~97.6%.
- The older interrupted 80B batch was cancelled by user steering; it is NOT model
  incapability evidence. The earlier 30B v3 batch remains exploratory only.

## Implemented modules (read only the relevant one)
- finance.py: immutable FinancialSpec; CLARABEL allocator; SCIP full reference;
  proxy distortion; mandate diagnosis; self-financing Account.
- quantum.py: direct Ising+slack; certified zero-penalty omission; independent
  NumPy/Qiskit verifier; finite-shot fitting; QASM/QPY/source-map export.
- design.py: connected tree exchange grammar, LLM requests, rules/random/mutation.
- baselines.py: full/subspace encoding, dense Dicke reference, gradient adaptation.
- runner.py: frozen structural comparison, feedback/profile ablations, common
  allocation postprocessing (32-query cap), uniform feasible reference.
- workflow.py/walkforward.py: common-state decisions vs continuous accounts;
  persistent mandates, true hold, next-session execution; full blocked artifacts.
- data.py: candidate acquisition and fail-closed source-backed market gate.
- probe.py: native QASM+IR probes; generated Python is never executed.
- pipeline.py: checkpointed integration stages. server.py: English interactive
  local comparison and replay; no unbounded inference from UI.
- synthesis/client.py and budget.py: model registry, CPU prefetch, reservations,
  cache/identity validation, dispatch receipts, recorded preflight failures.

## Scientific correctness traps
- B(S) proxy optimum is not F(S) allocation optimum; report distortion/failures.
- v3 turnover is half L1 including cash; legacy records retain two-way semantics.
- XY preserves cardinality; weight caps/turnover need allocation checks. Connected
  asset trees do not prove every inequality-feasible portfolio is reachable.
- Basis+p=1 can make gamma inactive. Do not claim cost learning in that case.
- Dicke baseline is dense small synthesis, not the O(kn) cited construction.
- Gradient baseline is ADAPT-inspired, not a full paper replication; count gradients.
- Cost compilation is polynomial; simulator still exponential and capped at 16
  total qubits, GateIR at 12 asset qubits. Compilation is not N=30 execution.
- True hold never trades to yesterday's weights. Mandate changes persist.
- Corporate actions must not be counted twice in adjusted-total-return mode.
- Blocked/failed/interrupted/unknown are distinct; no silent classical fallback.
- Software success, model correctness, financial value and quantum advantage are
  separate claims. Current hardware advantage and market outperformance unproven.

## Next dependencies and documentation
- Main open dependency: historical membership/security/action/sector reconciliation
  and audited aligned US prices. Current candidate has 29/30 stocks, missing UTX,
  zero verified permanent identities; DD/GE lineage also needs reconstruction.
- Development-only EDA: 1,257 returns (2014–2018), pair correlation median ~0.375,
  covariance participation ratio ~5.200. No hardship/speedup inference from that.
- After data admission: financial proxy-faithfulness and classical difficulty,
  then independently powered frozen model/circuit/financial studies.
- Read docs/research/WORKLOG.md for chronological facts; EVIDENCE_REVIEW.md for 13
  sources/revisions; DATA_SUITABILITY.md for data interpretation; TECHNICAL_DECISIONS.md
  and IMPLEMENTATION_PROTOCOL.md for the rationale. Active guide: docs/USER_GUIDE.md.
- Historical Vietnamese documentation is under docs/legacy/. Do not re-read it
  unless reproducing a historical protocol.
