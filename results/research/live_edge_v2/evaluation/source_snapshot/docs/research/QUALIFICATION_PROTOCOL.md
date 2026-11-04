# Historical data, model qualification and independent financial evaluation

Date: 2026-11-03. Written before this audit and any new qualification run.
The requested outcome is a testable hypothesis, not a promised positive result.

## Evidence and authorization boundary

Read EVIDENCE_REVIEW.md and CONTROL_FINDINGS in control_summary_v1. Published
weighted-QAOA scaling and our controls show that numerical conditioning matters;
our measured B/F mismatch is mathematical, not a language-model capacity issue.
The [LLM evaluator audit](https://arxiv.org/html/2610.28678) motivates independent
semantic checks and case-level uncertainty, not a universal model leaderboard.

The historical SEC 13F Q4-2013 list is an additional candidate identity source.
Its coverage date is December15, run date December23; neither proves September23
index membership or complete subsequent security lineage. It prohibits redistribution:
keep source/identifier extracts local, publish only provenance and aggregate review.
Direct SEC downloads may remain inaccessible; never invent a checksum.

## Gate A: comprehensive audit, without opening strategy outcomes

Preserve every original asset, raw file and source checksum. Independently check
source-symbol agreement, NY-session dates, duplicates, OHLC/volume validity,
missing sessions, adjusted-close coverage, dividends/split metadata and adjustment
factor consistency. Compare an independent exchange-session calendar, not generic
weekdays. Adjustment-factor tests are internal diagnostics, not independent proof
of total-return accuracy. Do not apply split adjustments twice.

Run return-shape diagnostics only through2018. Later rows may be inspected for
data hygiene, timestamps and entitlements, with no portfolio outcomes, model
ranking or return-profile fitting. Record this exposure distinction explicitly.
Context availability uses publication timestamps, never fiscal period end.

Create per-security unresolved issues and a source-backed corporate-action ledger.
CIK identifies an issuer, not by itself a historical common-share class. An
observation-date holding snapshot does not establish publication availability.
Do not remove UTX or relabel current DD/GE histories to pass the gate. Zero detected
numerical errors cannot turn missing evidence into verified lineage.

Acceptance requires complete dated identity, entitlement, sector-policy and aligned
return reconciliation under the existing market contract. Otherwise write BLOCKED
with a concrete repair queue and do not run a financial test on this candidate.

## Gate B: model qualification, separated from financial success

Shortlist remains Qwen Coder30 (general control), Qiskit Mistral24 (framework
specialist), QUASAR4 (quantum specialist with adverse local evidence). Check exact
public revisions/tokenizer/runtime again before a new model run. Do not escalate
to80/397/480B because the existing financial formulation is unfaithful.

Before comparing models, freeze a separate circuit-design protocol with the same
verified preparation/conditioning/candidate pooling for every method, or an
explicitly versioned expanded grammar. V3's three-edge preparation is not a fair
substitute for the newly tested broad-support control. Preserve raw model failures;
no silent graph repair or classical fallback is credited to an LLM.

Use pilot development cases only to select one candidate. Then lock checkpoint,
prompt, grammar, optimizer, feedback and budgets. Reliability confirmation uses
72 independently authored mathematical instances: all72 first-pass successes are
needed for a two-sided exact95% binomial lower bound above95%. With failures report
the interval and fail this reliability criterion; do not add tasks until it passes.
Independence is an assumption to justify, not merely different sampler seeds.
No financial winner can be selected from this correctness test.

## Gate C: frozen independent financial evaluation

Proposed temporal partitions: development2014–2018, validation2019–2021, final
test2022–2025. Audit prior artifact exposure before calling any partition unopened.
Historical out-of-sample is not guaranteed outside an LLM's pretraining corpus.
Only anonymous past-window profiles/coefficients may enter circuit prompts.

Primary task remains continuous-allocation tracking/cost repair. Keep equal-weight
targets as a labeled alternative. Before main evaluation either qualify B/F
faithfulness against an economically justified margin or revise the formulation
under a new protocol. A larger model cannot change B into F.

Freeze the selected model on validation only, then execute the final test once.
All methods carry independent continuous accounts from identical holdings, next-
session execution, persistent mandates, cash and all entitlements, and assumed
cost sensitivity. Compare hold, joint SCIP/bounds, allocation-aware maintenance,
uniform total-draw/time controls, fixed/rule/adaptive quantum designs and the LLM.
Count all optimizer samples, candidate allocations, invalid designs, repairs,
inference/startup and transpilation. Predeclare candidate pooling and fallback rules.

Primary utility: compliance plus out-of-sample tracking/cost frontier, not alpha.
Set the account's acceptable tracking deterioration and meaningful cost saving on
development before seeing validation/test outcomes. If not economically specified,
report a frontier without claiming a threshold-based win. Cluster uncertainty by
decision window/trajectory, not quantum seed; adjust planned multiple comparisons.
Estimate confirmation sample size on development. A small final sample is inconclusive.

## Scaling decision

Scale a model only if reliability passes, its matched-budget architecture improves
final allocated outcomes on validation, independent test supports the prespecified
financial effect with uncertainty, and measured end-to-end cost is acceptable.
Then preregister a new size comparison. Otherwise diagnose data/formulation/grammar/
optimizer/model separately. Report unsupported or inconclusive hypotheses honestly.

No new paid sweep or final financial test is launched while GatesA/C remain blocked.
This is an experiment stop rule, not a request for additional user permission.

## CPU-only runtime preflight addendum

The full checkpoint inventory shows Qiskit Mistral24 ships both HF and native
tokenizer/config metadata, but only HF weight shards. The initial inference that
params.json was absent was incorrect and was caught by the inventory regression
test. vLLM0.17.1's native weight loader requires consolidated*.safetensors, which
this pinned repository lacks. Before any GPU run, correct the worker
backend to match the pinned artifact and test tokenization/chat rendering only on
Modal CPU. Permit the three shortlisted checkpoints sequentially, no model weights,
no GPU and no generated financial decisions. Reserve CPU/RAM before each bounded
300-second call plus startup/margin, at mostUSD1 per job, retain failures and billing
snapshots. This does not qualify native code generation or financial utility and
does not reopen the completed QUASAR inference probe.
