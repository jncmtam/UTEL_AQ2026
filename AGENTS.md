# AGQO agent handoff

Updated: 2026-11-04, Asia/Ho_Chi_Minh. Read this first; inspect only modules needed
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
- Latest continuation:146 tests pass; historical_audit_v3 snapshots its actual source.
  Available source hygiene:29/30 stocks+DIA,3520 rows/file,0 missing internal sessions
  or bad numeric price/volume rows.1726 dividend records,17 provider split labels,
  1725 cash checks,0 residual flags;11 non-integer labels across7 stocks need review.
  UTX/full identity/action/sector/tradability reconstruction remains blocked.
- Qualification protocol/status are in docs/research/QUALIFICATION_{PROTOCOL,STATUS}.md.
  Exact reliability/final-test integrity code is implemented.72/72 is a planned
  confirmation threshold, never an observed model result. Actual test readiness blocked.
- tokenizer_preflight_v1:3/3 pinned Modal CPU tokenizer/chat passes; no weights,
  GPU or new inference.USD0.079125 reservation is not a bill. Mistral has native+HF
  metadata but HF-only weight shards; fixed HF backend. Earlier params-absence
  inference was wrong. No full GPU-load/generation qualification. Both apps idle.
- English README/root guides and repair UI/report/errors; eight PNG/SVG figures and
  filterable evidence_gallery_v1. Generator uses saved evidence only. Language audit:
  scripts/audit_english_surface.py; preserve original evidence and bilingual inputs.
  Root originals archived byte-for-byte under docs/legacy/root_*.md.
- Previous135-test control checkpoint: static F checks passed; English UI/API and Chrome
  desktop/mobile visual checks completed. Final evidence: ui_qa_v4 (stale synthetic
  evidence is cleared after a blocked market request).
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
- published_development_v3 is the canonical conditional US study: pinned author's
  2010 corpus, 386 securities ×252 dated returns. Full-year membership selection
  means algorithm scope only, not unbiased investment evidence. Raw stays local.
  All 18 rows feasible; N30/K6 represents all 593,775 supports with no LLM filtering.
- That N30 case: fixed/rules/random meaningful-probability supports 21/273/1,446;
  all three worse than uniform on allocated training objective. Exact proxy-optimum
  allocation is ~13.92% worse than the 15-second SCIP incumbent. SCIP gap ~32.18%;
  global optimum unknown. Do not start a larger model sweep to hide these defects.
- quasar_native_diagnostics_v1: normalization-only unitary diagnostics still fail,
  Bell fidelity .4956 and cost .5163. Frozen probe score remains 1/3. No new GPU job.
- preparation_control_v1: 18/18 feasible rows. Counter-Dicke gives all 593,775
  meaningful supports at N30, but costs 33 qubits/1798 CX/depth 2428 (old sparse
  30/998/445). Counter construction is not the cited ancilla-free algorithm.
- formulation_identity_v1: 408 allocation queries, equal-weight-target identity
  passes; continuous proxy allocation regret 3.32%/7.13% in N10 scenarios. Primary
  continuous task unchanged. Do not tune models to hide this formulation mismatch.
- conditioning_control_v1: 36/36 feasible rows, published Eq8 RMS coordinates
  versus raw and matched 2176-draw uniform reference, both weight policies. RMS
  improves proxy expectation but worsens mean N30 continuous allocated quality;
  matched-draw classical is stronger. No model/quantum advantage qualified.
- Latest consolidated control report: results/research/control_summary_v1/FINDINGS.md.
  Pre-experiment protocols: PREPARATION_PROTOCOL.md, FORMULATION_PROTOCOL.md,
  CONDITIONING_PROTOCOL.md. Defaults and earlier raw runs are unchanged.

## Implemented modules (read only the relevant one)
- finance.py: immutable FinancialSpec; CLARABEL allocator; SCIP full reference;
  proxy distortion; mandate diagnosis; self-financing Account.
- quantum.py: direct Ising+slack; certified zero-penalty omission; independent
  NumPy/Qiskit verifier; finite-shot fitting; QASM/QPY/source-map export.
- symmetry.py: exact fixed-cardinality/slack executor, crosschecked on small cases.
  sources.py archives source bytes/package versions for new published experiments.
- preparation.py: compiler-owned sequential counter-Dicke preparation, with clean
  counted workspace; exact amplitudes/cleanup checked for every n1..8/k0..n.
- conditioning.py: opt-in paper_rms_v1 Eq8 coordinate/loss transform; immutable
  H/hash retained, physical angles exported. evaluate default remains none.
- preparation_study.py: preparation and conditioning controls. formulation_study.py:
  support-by-support financial identity audit. CLI preparation-study,
  conditioning-study, formulation-audit; all CPU-only.
- published.py/published_study.py: pinned source decoding and bounded CPU study;
  CLI published-fetch/published-study. Install optional .[published-data].
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
- history_audit.py: CPU-only source/calendar/action hygiene, malformed input failures,
  snapshotting; CLI history-audit. qualification.py: exact binomial confirmation and
  immutable final-test locks; no automatic source attestation or strategy execution.
- synthesis/client.py and budget.py: model registry, CPU prefetch, reservations,
  cache/identity validation, dispatch receipts, recorded preflight failures.

## Scientific correctness traps
- B(S) proxy optimum is not F(S) allocation optimum; report distortion/failures.
- v3 turnover is half L1 including cash; legacy records retain two-way semantics.
- XY preserves cardinality; weight caps/turnover need allocation checks. Connected
  asset trees do not prove every inequality-feasible portfolio is reachable.
- Basis+p=1 can make gamma inactive. Do not claim cost learning in that case.
- Dicke baseline is dense small synthesis, not the O(kn) cited construction.
- New counter-Dicke is a different explicit construction, also not that paper's
  ancilla-free implementation. Its clean workspace is eliminated only in ideal
  simulation and counted in exported circuits/resources. No full N33 Qiskit check.
- Paper RMS rescaling changes optimizer geometry, not the financial objective or
  quantum algorithm; improved proxy expectation does not establish improved F.
- Current candidate pooling is final samples only. A next frozen study should
  count/use all observed optimizer shots explicitly and retain matched-draw controls.
- Gradient baseline is ADAPT-inspired, not a full paper replication; count gradients.
- Cost compilation is polynomial. Full statevector remains capped at 16 total
  qubits; GateIR v1 remains max12 assets. V2 allows max40 assets with a <=2m-state
  conserved simulator, including slack. This was executed at N30/K6, but remains
  exponential classical simulation. Large verification uses an analytic certificate
  and the small-crosschecked executor; no full Qiskit N30 statevector check claimed.
- Heuristic/QAOA decision status is feasible; conditional allocation_status may
  be optimal. Only a joint certificate supports global optimality. Trajectory v2
  applies the same 32-query sample allocator as structural/published experiments.
- True hold never trades to yesterday's weights. Mandate changes persist.
- Corporate actions must not be counted twice in adjusted-total-return mode.
- Blocked/failed/interrupted/unknown are distinct; no silent classical fallback.
- Software success, model correctness, financial value and quantum advantage are
  separate claims. Current hardware advantage and market outperformance unproven.

## Next dependencies and documentation
- Recommended next study: docs/research/REMEDIATION_PLAN.md. Parallel dependencies
  are source reconstruction and a preregistered allocation-aware non-LLM CPU pilot.
  This is a proposal, not an executed protocol or a change to existing B/F semantics.
- Main open dependency: historical membership/security/action/sector reconciliation
  and audited aligned US prices. Current candidate has 29/30 stocks, missing UTX,
  zero verified permanent identities; DD/GE lineage also needs reconstruction.
- Development-only EDA: 1,257 returns (2014–2018), pair correlation median ~0.375,
  covariance participation ratio ~5.200. No hardship/speedup inference from that.
- After data admission: financial proxy-faithfulness and classical difficulty,
  then independently powered frozen model/circuit/financial studies.
- Current source/proxy/coverage findings and next gates are consolidated in
  docs/research/QUALIFICATION_STATUS.md, with broader history in COMPLETION_REPORT.md.
  Read the status before another model experiment; do not rerun completed CPU probes.
- LLM connected-exchange-v3 still has the old bounded preparation domain. Before
  any new model comparison, freeze either a revised grammar or common verified
  preparation/conditioning across all methods. No inference sweep is scheduled.
- COMPLETION_PROTOCOL.md preregistered this continuation. DATA_RECONCILIATION.md
  explains DIA October-2013 anchors and the UTX/RTX mapping limit. SEC direct access
  returned403; no full source download hash or exact acceptance time invented.
- Source snapshots in published_development_v3 preserve the actual run code;
  v1/v2 intermediate results remain exploratory. Current UI/status fixes postdate
  that snapshot. Source-snapshot overlay supports exact scientific reruns.
- Read docs/research/WORKLOG.md for chronological facts; EVIDENCE_REVIEW.md for 13
  sources/revisions; DATA_SUITABILITY.md for data interpretation; TECHNICAL_DECISIONS.md
  and IMPLEMENTATION_PROTOCOL.md for the rationale. Active guide: docs/USER_GUIDE.md.
- Historical Vietnamese documentation is under docs/legacy/. Do not re-read it
  unless reproducing a historical protocol.
