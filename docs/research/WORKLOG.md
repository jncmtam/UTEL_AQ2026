# Research and implementation worklog

Date: 2026-11-02. Authoritative short handoff: [AGENTS.md](../../AGENTS.md).

## Current workflow rule

Before a new model, benchmark or technical experiment is chosen, record its
question, published evidence, data suitability, alternative, expected measurement,
full cost boundary and stop rule. Update this log immediately after the result.
Do not silently resume a prior inference sweep after an interruption.

## Entry 01 — Work inherited before the research-first correction

**What existed:** versioned financial/quantum/data modules; allocation and joint
SCIP references; continuous-account primitive; compiler verification; connected
exchange grammar; structural runner and English replay viewer. English migration,
market-data audit, model qualification and main evaluation are incomplete.

**Measured:** the earlier baseline suite had 92 tests. Nine added financial,
quantum, accounting, data-gate and walk-forward tests passed with the baseline
suite (101 tests). This is software correctness evidence, not investment value.
The offline structural smoke recorded 12 valid classical designs. Its three
sizes and low optimization budget are diagnostic only.

**Correction:** implementing a connected grammar and starting model comparison
before settling the data/technical rationale was premature. Prototype settings
are now provisional, with no claim they are the best design. Existing code is
retained as a testable prototype rather than treated as a research conclusion.

## Entry 02 — Stop the existing paid experiment

**Trigger:** user requested literature and data analysis before further choices.

**Action:** read the saved dispatch/ledger, requested cancellation of the active
80B Modal FunctionCall with container termination, and inspected the app inventory.
Both apps then reported zero tasks; the local runner also ended.

**Already completed:** one 30B batch had returned, with three structurally accepted
circuits in the partial records. That is exploratory infrastructure evidence only.
It is not sufficient to choose 30B or claim portfolio benefit.

**Interrupted:** 80B records in that runner are failed/interrupted due to user
steering. Do not count them as evidence that the model cannot generate circuits.
The ledger records `failed_reservation_charged`; retain that cost accounting.
USD1.84 and USD3.06 were reservations, not invoices. No new inference was launched.

**Evidence:** `results/research/modal_v3/USER_STEERING.md`, saved dispatch/receipt,
`records.json`, and `budget.json`. This run predates the new research protocol and
must not be relabeled as a frozen comparison under it.

## Entry 03 — Review empirical publications

**Question:** what justifies a model and circuit method for the actual task?

**Action:** checked primary pages/tables for QGAS, Agent-Q, QUASAR, QuanBench+,
a recent evaluator audit, Qiskit verifiable rewards, strong classical portfolio
benchmarks, direct-indexing QAOA, tracker maintenance, ADAPT/Dynamic-ADAPT, XY
topology/warm starts and Dicke preparation. Exact links and versions are in
[EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md).

**Finding:** syntax, quantum semantics, architecture utility and financial utility
are different outcomes. Published evidence does not select a universal best model.
Evaluator reliability and strong adaptive/classical comparators are mandatory.

**Decision:** shortlist quantum specialists plus one existing general coder as a
control. Defer 397B/480B; do not automatically escalate to 80B. No final model is
selected. Verify native interface and checkpoint before a justified probe.

## Entry 04 — Assess the downloaded stock panel

**Question:** what properties are present, and can this dataset support the claim?

**Action:** ran `scripts/assess_us_dataset.py` against existing raw local files.
No new data download or portfolio optimizer was run. Development statistics use
2014–2018; later rows receive coverage checks only. File hashes are recorded.

**Finding:** 29/30 stocks downloaded, UTX missing; permanent security identities
and historical context remain unverified. Common return structure and dense cost
interactions provide specific technical hypotheses, but no hardness proof.

**Decision:** keep the dataset as an audit candidate. Do not drop UTX, substitute
symbols, infer lineage from current company names or present it as final data.
[DATA_SUITABILITY.md](DATA_SUITABILITY.md) maps every measured property to a
possible use, limitation and required control.

## Entry 05 — Replace assumption-driven selection with gates

**Action:** wrote [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md).

**Changes:** model-size escalation deferred; grammar/initialization/optimizer/shot
settings reopened as development choices; evaluator audit added; selection-proxy
fidelity and market audit precede financial conclusions; no paper metric copied
as an AGQO investment target.

**Next action:** reconstruct membership and action histories with primary sources,
then specify a small non-LLM initialization/encoding comparison. Before running it,
write a separate protocol containing exact cases, budgets, metrics and stop rules.

## Reusable entry template

### Entry N — Specific question

- **Problem:** uncertainty or user decision this step addresses.
- **Evidence:** exact paper/table/version or measured artifact and its limitation.
- **Data suitability:** available fields, cutoff, units and missing evidence.
- **Alternatives:** at least one plausible simpler comparator.
- **Chosen action:** why it resolves this uncertainty now.
- **Protocol:** inputs/hash, outputs, budget, failure handling and stop rule.
- **Observed result:** include failures and uncertainty; no anticipated values.
- **Interpretation:** what is supported and what remains unknown.
- **Decision:** proceed, revise, defer or stop, with reason.
- **Next dependency:** specific evidence needed before the next action.

## Open work and non-claims

- Full US security/action/sector/as-of audit: incomplete.
- Model native-format probes and production selection: pending.
- Published ADAPT replication and calibrated non-LLM baseline: pending.
- Main frozen benchmark and audited financial walk-forward: not run.
- Complete English migration, final UI, reviewed implementation commit/push: incomplete.
- LLM financial value, superiority to strong classical solvers and quantum
  advantage: unproven.

## Entry 06 — Check whether the lineage warnings have primary support

**Action:** consulted issuer/SEC sources for UTX separation, GE Vernova distribution
and DuPont's 2019 restructuring, linked in DATA_SUITABILITY.md.

**Finding:** these involve distributions and/or multiple successor securities,
not merely text changes in a ticker. We have source-level reasons for the audit
block, while provider adjustment treatment remains unknown.

**Decision:** no naive UTX→RTX or historical DD substitution. Treat any free-price
history as provisional until entitlement and return reconciliation is complete.

## Entry 07 — Validate this research checkpoint

Verified all 30 downloaded file checksums against the acquisition manifest,
relative links in the four research Markdown files, and the assessment's blocked
admission facts. Re-ran the deterministic EDA after restricting extreme-move and
adjustment-factor diagnostics to development data. No paid test was launched.

This checkpoint documents the research correction and data evidence. Earlier
prototype implementation changes remain under review in the working tree; it is
not a delivery claim for the complete approved application.

## Entry 08 — Implement evidence-derived controls and integration

**Authorization:** user requested complete implementation after the review.
**Protocol:** IMPLEMENTATION_PROTOCOL.md was written before these experiments.

**Implemented:** direct compiler supports optional omission of certified zero
asset constraints; verifier requires an analytic certificate and checks frozen
qubits. Added exact small Dicke preparation reference and a finite-difference,
ADAPT-inspired exchange selector with explicit gradient/angle evaluation counts.
The dense Dicke reference is not the efficient paper algorithm.

**Observed:** all 12 configurations in baseline_evidence_v1 passed independent
verification. For N=10, the Dicke reference uses 1,161 CX versus 160 for fixed
exchange. Gradient selection uses extra exact classical energy evaluations; its
quality cannot be advertised as a same-budget win. Full and certified encodings
produce matching sampled results here and equal transpiled CX counts: omitting
zero penalties is not claimed as a gate reduction on these cases.

**Decision:** retain these controls and complete the native specialist interface
probe. No architecture or production model is qualified by this small study.

## Entry 09 — Specialist probe outcome and operational correction

**Observed:** the single QUASAR batch returned three outputs. GateIR transfer
passed verification; native Bell and cost programs violated the requested
no-measurement/register contract. Raw outputs also contain different gate patterns
from the requested primitives. Native failures are not a reproduction of the
paper benchmark, and the one transfer success does not qualify a model.

**Action:** retained all outputs, token/runtime receipts and the full reservation.
No paid retry or larger-model job followed. Added common artifact derivation from
the saved probe without rescoring or inference. The first probe loaded weights on
GPU; this startup cost is retained. New research clients now perform checkpointed
CPU prefetch before GPU dispatch to avoid repeating that operational overhead.

## Entry 10 — Continuous decisions, English application and explicit blocking

**Implemented:** complete artifact bundles, CLI stage/checkpoint execution,
allocation-aware local search, sample-to-allocation postprocessing with a shared
32-query ceiling, profile ablation/feedback switches, and offline replay.
The English application compares local decisions and revalidates the saved LLM
design; a failed replay is visible and never silently replaced.

**Accounting correction:** continuous repair runs now begin from the same existing
three-asset account. The exclusion introduced at the second decision persists.
Hold means no order, rather than rebalancing back to yesterday's weights. A new
trajectory output is used after this protocol change; previous raw runs remain.

**Boundary:** the market path writes a blocked artifact contract and nonzero gate
exit code while historical identity/action evidence is incomplete. No historical
investment result is manufactured to make the pipeline appear successful.

## Entry 11 — Delivery validation (2026-11-03)

**Measured:** all 112 tests passed, including a blocked Modal prefetch test proving
that an exhausted/failed preflight records the failure without GPU dispatch.
Static F checks passed. HTTP validation passed for the English app, synthetic
comparison, exclusion/turnover conflict and market rejection. No visual screenshot
was taken, so this is API/page-content validation rather than a screenshot claim.

**Artifacts:** delivery_pipeline_v1, delivery_structural_v1 and quasar_interface_v1
contain protocols, records, financial/circuit evidence and English reports. The
delivery pipeline includes source-checksummed resource and tracking/cost figures.
The raw provider data is excluded from Git; its manifest/audit remain versioned.

**Status:** software integration is implemented. The market-data research gate is
still blocked, and no production LLM or quantum advantage is qualified. Both Modal
apps had zero tasks at the final check. Existing local server listens on port 8765.

## Entry 12 — Completion audit and stronger data evidence (2026-11-03)

**Question:** which previous delivery gaps can be closed without weakening the
research/data gates?

**Protocol:** COMPLETION_PROTOCOL.md written before new experiments.

**Source finding:** DIA's October 2013 N-30D filing contains all 30 positions and
an independent valuation anchor. A factual extract and anchor comparison are saved
under data/us_equities/review and results/data_assessment. This is stronger than
the earlier three-replacement announcement, but it does not verify every later
corporate action or prove the original Sept 23 composition by itself. Publication
time remains unresolved. Direct SEC API/source downloads returned HTTP403; indexed
filing access was available. No fabricated full-document checksum is recorded.

**Diagnostic:** several vendor closes differ from the filing by later split or
spin-off factors; smaller differences also occur for Nasdaq stocks. These are
reconciliation questions, not evidence that every vendor return is wrong.

**Additional published source:** sparseIndexTracking's author-maintained INDEX_2010
contains actual US S&P500 constituent and index returns. Its source explicitly
includes only securities present for the whole year. It can support a disclosed
selection-conditioned algorithm benchmark, not an unbiased investment universe.
It will not silently replace or pass the historical cohort's original audit.

**Technical action:** implement exact conserved-cardinality simulation with a new
larger-register GateIR version; retain every asset support and explicit slack.
Small-instance full-state equivalence and memory-cap tests precede any large run.

## Entry 13 — Conserved simulation and conditional US study

**Implemented:** GateIR v2 extends asset registers while preserving v1. The executor
represents every fixed-cardinality support, frozen inclusion/exclusion and explicit
slack; trusted XX/YY pairs execute as blocks. It rejects state counts above 2m before
allocation. Independent small full-state checks pass. N30/K6 executed 593,775 states.
Large verification is analytic plus the small-crosschecked executor, not a full
Qiskit N30 statevector comparison. Canonical coefficients remain unchanged when
the designer's context uses a documented, hashed descriptor projection.

**Source:** pinned author corpus INDEX_2010 decodes 386 source labels ×252 dated
returns; SHA256 16db76dccbec4dc12a5128f02a95e860e1cd498b97f4682b694b2e538daceaa7.
Dates come from R attributes. Full-year membership conditioning remains a disclosed
bias. It receives algorithm-only admission and does not pass the original market gate.

**Observed:** published_development_v1 exposed a classical seed wasting its budget
on an excluded asset; fixed before v2. Reports distinguish global support status from
conditional allocation. V3 archives actual source bytes/package versions to remove
uncommitted-source ambiguity. Earlier intermediate runs remain preserved; v3 is the
canonical study. All 18 v3 rows are feasible. No new model inference or GPU job.

**Negative findings:** N30 fixed/rules/random have only 21/273/1,446 meaningful-
probability supports (>1e-12) despite representing all 593,775. They trail uniform
sampling on the allocated training objective. Exact proxy optimum allocates to
1.67205e-5, ~13.92% worse than SCIP's 1.46777e-5 incumbent. SCIP's 15-second run
does not prove optimality (bound gap ~32.18%). Small proxy rank correlations
0.934/0.922 do not eliminate economically material regret. These are opened
development findings, with four optimization calls and one seed, not qualification.

**Post-run data analysis:** full source training covariance rank 125 from 126 rows;
raw condition number undefined; shrinkage condition ~4060.5; participation ratio
~3.41. These describe sample structure, not evidence of combinatorial hardness.
Exact proxy diagnostics and full support allocation on small cases are additional
classical work, explicitly recorded. No change to raw returns or later-label metadata.

**Decision:** resolve proxy faithfulness and broad-support preparation before a new
model sweep. Increasing parameter count does not address the identified weaknesses.

## Entry 14 — Native failure diagnosis, decision semantics and final UI QA

**Model:** normalization-only diagnostics remove empty reasoning tags, unused bit
declarations and terminal measurements. No gate/angle repair. Bell fidelity .4956;
cost fidelity .5163. Both remain semantically wrong. Frozen QUASAR probe remains 1/3.
No paid retry. Mid-circuit measurements remain rejected.

**Decision correction:** all heuristic/QAOA decisions now report feasible rather than
globally optimal; allocation_status records the convex subproblem. Trajectory v2
and interactive decisions use the common 32-query sample allocator. Raw older
results retain their original conditional labels. New tests check excluded-seed
repair and the global/conditional distinction.

**UI:** Chrome checks passed at 1440px/390px. Screenshots inspected. A blocked market
request initially left prior synthetic holdings/decisions visible; this was found,
fixed and checked in ui_qa_v4 with a specific stale-evidence assertion. No uncaught
browser exceptions or page overflow. Mobile metric table scrolls horizontally.

**Reproducibility:** canonical source snapshot, 8-artifact contract, plots and source
hashes saved. Markdown table spacing is corrected in the canonical derived report;
the original report remains RESULTS.original.md. Raw metrics/decisions are unchanged.
All 120 tests pass and static F checks pass. Modal profile data1 remains connected;
both deployed apps reported zero tasks. Historical source reconciliation, production
model selection, financial benefit and quantum advantage remain unqualified.

**Current entry point:** COMPLETION_REPORT.md consolidates actual findings and next
dependencies. AGENTS.md/agent.md and root PROGRESS.md carry the compact handoff.

Repeated interactive requests now retain separate UUID/source-identified records;
an integration check verifies neither measurement overwrites the other. The final
API metadata change does not alter the visually inspected layout. Logical gate
resources exclude hardware routing/noise. A post-run hold diagnostic records base
training MSE 3.45880e-5 /4.36185e-5 at N10/N30; the exclusion case disallows hold.

## Entry 15 — Broad-support control, published-method boundary

**Protocol:** PREPARATION_PROTOCOL.md was written before code/run. Rechecked the
primary Dicke paper and official Qiskit uniformly controlled rotation API. The
new sequential binary-counter construction is explicitly not a replication of
the cited ancilla-free O(kn) construction. The Dicke recurrence proves uniform
amplitudes and a clean final counter, without postselection.

**Verified:** exact amplitudes/cleanup across every n=1..8 and k=0..n; complete
QAOA evolution with frozen assets/slack against independent Qiskit; malformed or
mixed preparation metadata rejected. Workspace is counted in QASM/transpilation,
and eliminated only from ideal simulation after the trusted construction.

**Measured:** preparation_control_v1 has 18 feasible rows. At N30 all 593,775
supports have meaningful probability. Mean allocated objective 1.72646e-5 versus
2.07900e-5 for sparse initialization, but resources rise 30→33 qubits, 998→1798 CX,
445→2428 depth. A clearly labeled post-run uniform 2176-draw reference reaches
1.63856e-5 and remains stronger. Three seeds/two opened cases are descriptive.

## Entry 16 — Financial formulation identity rather than model guessing

**Protocol:** FORMULATION_PROTOCOL.md, before 408 support allocations. Both
continuous and explicitly equal-weight-target mandates use the common allocator
and identical tracking/cost/policy assumptions. No primary-task substitution.

**Measured:** equal-weight target identity B=F passes within 1e-9 objective/1e-7
weight tolerance. Continuous proxy-optimal allocation regret 3.32% (base) and 7.13%
(exclusion) remains. Infeasible allocations are retained. Independent tests also
verify financial/Ising/allocator asset-permutation consistency and cap rejection.

**Decision:** the financial target must be fixed before choosing model quality
metrics. Richer weights or an allocation-aware outer method need their own resource
contract; an energy-only improvement cannot qualify continuous portfolio repair.

## Entry 17 — Published weighted-QAOA conditioning, not a new algorithm

**Source:** Sureshbabu et al., Quantum 8, 1231 (2024), Eq8 and portfolio Section6.2.
CONDITIONING_PROTOCOL.md was written before the control. The paper's 7.4× iteration
result concerns its own random mean-variance instances, not our US tracking task.

**Implemented:** optional RMS gamma/loss coordinates on the immutable Hamiltonian;
physical angles and optimizer coordinates are stored separately. Tests prove Eq8
and uniform-rescaling unitary equivalence. No optimum/truth table is used to set
the scale. Legacy defaults and frozen results are unchanged.

**Measured:** conditioning_control_v1 has 36 feasible rows with both financial
policies and the predeclared 2176-draw classical reference. Proxy expectation improves
on the opened cases. At N30 mean continuous F worsens 1.72646e-5→1.82890e-5, while
equal-weight F improves 2.25953e-5→2.15969e-5. Classical remains stronger under both.
No significance claim or qualified model follows. Optimizer bitstrings were not
pooled into final candidate selection; a future protocol must predeclare that rule.

## Entry 18 — Follow-up validation and delivery checkpoint

All 135 tests pass; static F checks and replay pass. Source snapshots/contracts
verified for preparation/formulation/conditioning bundles (75/77/79 source files).
Derived figures were visually inspected; generator/input hashes are retained.
The summary is control_summary_v1/FINDINGS.md. No new GPU inference, model switch,
market-data admission, or quantum/financial superiority claim. User-authorized
Git checkpoint d9b48b1 is already pushed; these follow-up controls form a separate
reviewable commit on the same branch.

## 2026-11-03 / 2026-11-04 — historical audit and qualification continuation

- Wrote QUALIFICATION_PROTOCOL.md before the audit/model preflight. Kept the
  original continuous tracking/cost task, source-review blockers and unopened
  strategy-outcome boundary. Defined exact 72-case independent correctness
  confirmation, final-test prerequisites and a conditional scaling decision.
- Implemented source-symbol/checksum, NY-session/calendar, OHLC/volume, coverage,
  dividend/split and backward-cash-adjustment diagnostics. Installed/pinned
  exchange_calendars4.13.2 and its dependencies. Initial v1 serialization failed
  on a NumPy integer; converted the count to a Python int, then retained the
  completed v1 output. V2 adds explicit non-integer provider-label classification.
- Available-source findings:29 cohort stocks plus DIA; UTX missing;3520 rows/file;
  0 missing internal sessions, bad prices, OHLC violations, bad volume or unexplained
  adjustment changes;1726 provider dividends,17 split labels,1725 internal cash
  checks with0 residuals above5e-5. Eleven non-integer split labels affect7 stocks.
  These checks use vendor algebra, not independently verified economic entitlements.
- Recorded ten primary-source action candidates, explicitly partial and unaccepted.
  Full share-class lineage, publication timing, cash-in-lieu, descendant prices,
  sectors and investable trading/reinvestment semantics remain missing. SEC direct
  requests returned403; no full PDF hash or identity-table visual verification
  claimed. Did not replace UTX with RTX, remove assets or change the universe policy.
- Audited pinned HF artifact inventories for coder30/mistral24q/quasar4. Initially
  inferred Mistral native metadata was absent from a partial view; the full inventory
  regression disproved that. Correct finding: native config/tokenizer metadata exists,
  but the pinned repo has HF weight shards and no consolidated*.safetensors required
  by vLLM0.17.1's native weight loader. Changed its registry to HF tokenizer/config
  and safetensors loading. Preserved the correction in the protocol/status.
- Added/deployed a bounded CPU tokenizer preflight and ran three sequential calls
  under reservations.3/3 passed pinned chat rendering, no weights/GPU/inference.
  Reservation USD0.079125 is not an invoice; billing snapshots/receipts retained.
  Shared preflight image is not every production GPU worker. No inference sweep or
  completed specialist-probe rerun. Both deployed apps were idle at the recorded check.
- Implemented exact-binomial reliability checks, duplicate/extension protection,
  fail-closed final-test prerequisites and data/hash lock verification. Actual
  independent_test_readiness_v1 is blocked: no final lock or strategy outcomes.
  Initial targeted tests exposed a fixture list-alias bug and the erroneous
  metadata assumption; both corrected. The7 new targeted tests then passed.

## 2026-11-04 — English visual delivery and verification

- Wrote DELIVERY_VISUAL_PROTOCOL.md before rendering. Added `history-audit` CLI,
  structured malformed-source failures and audit-v3 source/environment snapshot.
  Completed historical_audit_v3 with exit2 because financial admission remains blocked.
  V1/v2/raw files remain unchanged. Four malformed-source regressions bring the
  total to146 tests. The v3 snapshot records audit-time bytes before later
  presentation translation; it is not claimed to equal the final checkout.
- Rebuilt README in English with role ownership, data suitability, model criteria,
  measured negative results, independent-test/scaling dependencies, artifact map,
  reproduction commands, six embedded charts and two Mermaid diagrams.
- Added eight PNG/SVG figures and an offline topic-filtered gallery under
  evidence_gallery_v1. Rendered only saved results;0 new optimizations/inference
  and no new strategy outcomes. Included generator/input hashes. The72/72 curve
  is explicitly a planning illustration. Contact sheets were visually inspected.
- Copied four superseded root documents byte-for-byte to docs/legacy/root_* and
  replaced their entry points with current English guides. Translated repair
  compatibility UI, report templates and validator/CLI errors. Preserved the
  Vietnamese input fixture and normalization support. Figure helpers now compose
  English captions while accepting historical caption syntax. Raw results and
  snapshots were not translated or re-scored.
- First full run during translation exposed a Vietnamese-only caption validator
  and tests matching old Vietnamese error text. Updated the caption convention
  and English assertions while preserving the original legacy caption/input checks.
  Subsequent full suite:146 passed; targeted F lint and JS syntax checks passed.
- Language scan passed over76 maintained source/doc files with only two declared
  bilingual-input exceptions. Added LANGUAGE_AND_ARCHIVES.md to disclose scope;
  older VN30 presentation catalogs/utilities remain historical compatibility code.
- Browser verified gallery Models/Finance filters, restoration ofAll, and no
  horizontal overflow at observed DOM widths1163/354. Inspected plot contact sheets
  and gallery screenshots. Checked translated repair UI: valid English mandate,
  explicit English conflict diagnosis, solve disabled for conflict, no console errors.
  All UI actions used local rules only. Gallery left available on localhost8766.
- QUALIFICATION_STATUS.md, PROJECT_STATUS.md, COMPLETION_REPORT.md, PROGRESS.md and
  AGENTS.md now distinguish software delivery from unqualified models/financial value.
  Financial data and continuous B/F fidelity remain the next substantive gates;
  increasing parameter count is not treated as their remedy.
