# AGQO agent handoff

Updated: 2026-11-02 (Asia/Ho_Chi_Minh).
Read this file first. Read only the modules needed for the next task. Update this
handoff after each meaningful implementation or experiment. Never infer success
from the existence of a result directory.

## Active research-first steering (takes priority over the old execution order)
- Read docs/research/WORKLOG.md and TECHNICAL_DECISIONS.md before choosing any model, benchmark or new technical experiment.
- Every new step requires a published-evidence/data-suitability rationale and a Markdown log entry. Do not run speculative GPU sweeps or escalate model size.
- The active 80B Modal call was cancelled on user steering. Both apps subsequently showed zero tasks. The completed 30B batch is exploratory only; cancelled 80B is not model-quality evidence.
- Next: source historical security/action identities and specify a non-LLM baseline comparison, then freeze a protocol before any dependent inference.

## User contract
- Implement the approved English-language AGQO pipeline, run bounded Modal tests,
  preserve honest negative results, commit/push to the existing GitHub branch.
- US equities only; free data; historical cohort with auditable identities and
  corporate actions. LLM designs quantum circuits, never preselects stock winners.
- Primary finance task: mandate-aware tracking/cost repair. Risk/return is separate.
- No promise of superior returns, classical speedup, or quantum advantage.
- User authorizes Modal spending. Existing expanded policy uses a USD150 reservation
  ceiling per experiment, sequential workers, at most four H200s. It is not a balance.
- Project code, maintained docs, UI and reports must be English. Raw historical
  evidence is immutable. User-facing chat may remain Vietnamese.

## Repository and commands
- Root: /Users/jant/Documents/ChatGPT/AI-Quantum Challenge 2026
- Branch: codex/verified-large-model-synthesis
- Remote: https://github.com/jncmtam/UTEL_AQ2026.git
- Python: .venv/bin/python (Python 3.12); dependencies include CVXPY 1.9.3,
  PySCIPOpt 6.3.0, Qiskit, SciPy and Modal.
- Test: .venv/bin/python -m pytest -q
- Focused new tests: .venv/bin/python -m pytest tests/test_research.py -q
- Modal inventory: .venv/bin/modal app list --json
- Existing CLI: python -m agqo.synthesis (legacy), python -m agqo.repair.
- New production entry point: python -m agqo.research (see runner status below).

## Established evidence (do not rerun without reason)
- Baseline suite before new research code: 92 tests passed.
- Legacy free GateIR pilot: 80B valid 1/3, 30B 0/3; no qualified winner.
- Typed v2 pilot: each model valid 2/3; fixed path better on N=6 (Popt ~90.8%).
- Uniform feasible sampling N=8 already finds optimum with ~97.6% probability in
  128 samples. Best-of-shots alone is not a useful achievement.
- Existing Modal apps: agqo-gate-synthesis, agqo-qwen3-guide; profile data1.
  Authentication verified previously; v3 30B batch completed before steering; 80B cancelled. No model qualified.
- 397B/480B workers were deployed previously but have no successful inference
  evidence. Do not choose models by parameter count.

## New code currently under development
- agqo/research/finance.py: FinancialSpec v3; independent support constraints vs
  allocation constraints; CLARABEL convex allocator; small support/proxy audit;
  full support+weight SCIP reference; conflicting mandate diagnosis; Account
  with self-financing fee accounting, drift and audited action maps.
- agqo/research/quantum.py: direct polynomial QUBO/Ising compilation; integer
  slack penalties; NumPy executor independently checked against Qiskit; gate
  resources; finite-shot optimization; QASM/QPY/source-map exports. Compilation
  supports larger registers, simulator capped at 16 qubits. No speedup claim.
- agqo/research/design.py: connected-by-construction tree grammar v3; LLM owns
  parent choices, scheduling, sharing, preparation and depth. Rule/random/mutation
  and reuse baselines. Canonical cost remains compiler-owned.
- agqo/research/data.py: historical DJIA 2013-09-23 cohort candidate + DIA;
  local-only Yahoo raw downloads; SEC submissions adapter; fail-closed audit.
- tests/test_research.py: financial/quantum/accounting/data integration tests.
- Raw downloads: data/us_equities/raw (gitignored). Manifest/audit are tracked.
  Full historical identities, corporate actions, sector vintages and aligned
  total-return prices are NOT verified. Financial market evaluation must block.
  Ticker DD/UTX lineage cannot be guessed from today's ticker history.

## Semantics and correctness traps
- v3 turnover = half L1 including cash. Legacy uses two-way risky-weight L1;
  do not silently reinterpret historical records.
- Selection uses equal-weight proxy B(S). Allocator solves F(S). Report proxy
  regret and allocation failures; do not claim optimizing B solves F.
- QAOA preserves cardinality/include/exclude via asset exchanges; inequalities
  use explicit slack penalties. Weight caps/turnover are allocator constraints.
- Connected asset graph does not certify connectivity of every fully feasible
  portfolio under extra constraints.
- First cost layer after a basis state has only global phase. Verifier must flag
  inactive cost parameters; use preparation before cost.
- Corporate actions in adjusted total returns must not be applied a second time.
- An old DiagonalGate/Walsh cost oracle is exponential and retained only as legacy
  reference. New production compiler must not build a 2^N truth table.
- Generated/downloaded files are not experimental success. Report failure,
  unsupported and inconclusive explicitly; no silent classical fallback.

## Current verified status and next work
- All 101 tests passed after the v3 additions. Offline structural smoke: 12/12
  baseline designs valid. Neither result establishes financial performance.
- Runner/CLI and artifact contract now exist in agqo/research/runner.py and
  __main__.py; English read-only viewer in server.py; continuous-account routine
  in walkforward.py. Integration and full English migration remain incomplete.
- Development-only data EDA: 29 stocks + DIA; UTX missing; 1,257 complete returns
  in 2014–2018, median pair correlation ~0.375, covariance participation ratio
  ~5.200. No security identity verified; financial evaluation remains blocked.
- Read docs/research/EVIDENCE_REVIEW.md for 13 empirical/theoretical sources and
  source-specific limits; DATA_SUITABILITY.md for interpretation; WORKLOG.md for
  actions already taken. Do not reread all legacy source files.
- Reproduce data assessment: .venv/bin/python scripts/assess_us_dataset.py
- Resume order: historical lineage audit → model-faithfulness and classical
  references → non-LLM ansatz/encoding study → pinned native specialist probes →
  preregistered held-out evaluation. No automatic paid continuation.
- Model shortlist is provisional: QUASAR 4B, Mistral Qiskit 24B, existing Qwen 30B
  control. 80B conditional; 397B/480B deferred. See evidence review for revisions.

## Where to inspect only when needed
- Modal budget/client: agqo/synthesis/budget.py and client.py;
  config/synthesis-expanded-budget.json; modal_gate_synthesis.py.
- Legacy paper evidence: docs/LLM_QUANTUM_FINANCE_LITERATURE.md.
- Legacy pilot: results/synthesis/typed_pilot/REPORT.md.
- Current detailed implementation status: docs/IMPLEMENTATION_PROGRESS.md.
