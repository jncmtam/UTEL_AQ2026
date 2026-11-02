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
