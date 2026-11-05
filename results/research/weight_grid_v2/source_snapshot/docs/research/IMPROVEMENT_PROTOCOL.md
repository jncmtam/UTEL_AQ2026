# Cost-aware circuits and discriminating US-data benchmark

Date: 2026-11-04. Frozen before implementation and execution. Development study;
no production LLM selection, final financial test or new GPU inference.

## Evidence and rationale

The completed Modal integration found equal small-case allocated quality and
32–52% extra CX in the LLM designs. It cannot justify model-size escalation.
[Stopfer/Wagner v3](https://arxiv.org/abs/2509.17876v3) motivates strong classical
references, without transferring conclusions from their different objective.
[ADAPT-QAOA](https://arxiv.org/abs/2005.10258v3) motivates testing compact ansatz
choices; our layer edits/schedules are not an ADAPT replication.
[Weighted-QAOA Eq8](https://arxiv.org/html/2305.15201v3) supplies the existing RMS
coordinates. [Dicke preparation](https://arxiv.org/abs/1904.07358) motivates broad
support, but our counter construction remains distinct and fully counted.

Keep continuous tracking/cost allocation and immutable B cost. Evaluate sampled F
directly; it is still classical feedback rather than a coherent F oracle. Preserve
all prior runs. A more discriminating benchmark may expose worse results; this is
an accepted outcome rather than a reason to tune until a win appears.

## A. Opened circuit ablation

Load the three actual saved Coder30 common-counter programs from modal_e2e_v1.
Explicitly remove their second layer by setting depth1 before normal compilation;
never alter cost coefficients or replace raw proposals. Use the original6×32+64
draw budget and seeds11/23. Compare against recorded original quality/resources.
Attribute savings to the deterministic edit, not the LLM. This is a post-run
mechanism control on opened synthetic cases, not independent non-inferiority proof.

Add deterministic exchange scheduling by greedy edge coloring: group disjoint
edges into consecutive rounds. Because overlapping exchanges do not generally
commute, this is a new circuit requiring verification/refitting, not an equivalent
unitary rewrite. No optimal graph-coloring or guaranteed depth claim.

## B. Published-US development benchmark

Use pinned INDEX_2010, first126 estimation observations only. Holdout returns are
not scored. Full-year membership conditioning remains; this is a real-return
algorithm benchmark, not unbiased investable-history evidence. Policy_A/B buckets
are artificial scenario labels, not verified historical sectors.

Select40 securities by SHA256("AGQO-improvement-family-v1:"+source label), split
into two disjoint20-security families. Each family uses N12/K3 and N20/K5, with
base and mandatory-exit mandates:8 cases. N12 is nested inside its N20 family;
mandates and sizes are related, not8 independent markets. No LLM stock filtering.

Common preparation: counter-Dicke. Common coordinates: paper_rms_v1. Seeds11/23/47.
Per circuit:10 angle evaluations×8 observations, then8 final observations =88.
All observed optimizer/final supports enter the candidate pool. Sample checkpoints
8/24/48/88; also report actual allocation calls/cache hits and cumulative runtime.
No exact-state expectation or optimum is used in fitting.

Methods: fixed path depth1; correlation-tree depth1; disjoint-scheduled path depth1;
path depth2 (the observed LLM structural pattern, explicitly classical and not a
fresh LLM output); conditioned uniform; allocation-aware local swap. The swap is
a tailored classical reference, with its support-query budget separately labeled.
For the fixed path also compare proxy-energy versus allocated-F feedback under
the same sampling budget, so feedback benefit is measured rather than assumed.

Uniform draws directly from free K-of-N combinations with includes/excludes fixed,
then applies the same support/allocation checks. It does not repeatedly propose
forbidden assets. No enumeration of the full universe just to sample uniform.
Cases do not have sector-count caps, so both quantum initialization and uniform
preserve the same binary constraints; sector weights remain post-allocation checks.

Run joint SCIP at5s/case; retain status, incumbent and bound. No global-optimum
claim without certificate. Report signed difference to the incumbent and absolute
allocated objective. References consume real measured time; they are not free.

## Cost eligibility

Provide a deterministic gate-resource eligibility checker that rejects extra CX or
depth beyond a declared reference budget and retains rejection/provenance. It does
not substitute a baseline and call that an LLM result. Apply it diagnostically to
the recorded two-layer proposals. On original tied cases, choose the cheaper
valid design; on new cases report the full quality/resource frontier, not a hidden
weighted score. Costs of candidate evaluation remain counted even when rejected.

## Acceptance and stop rule

- Software: conserved/full-state and finite-sample consistency, conditioned sampling,
  all-shot prefix accounting, immutable cost/legacy defaults, gate/parameter/resource
  validation, direct F checks and source/package snapshots.
- Opened ablation: report actual CX/depth change and every quality change. Do not
  declare success merely from cutting layers if allocated quality degrades.
- Benchmark: show whether88 observations still saturate the reference; report
  quality by budget and method, with failures and caching visible. Three seeds are
  descriptive. No market significance or economically justified margin is assumed.
- No new LLM/GPU sweep in this study. If circuits fail to offer a useful frontier
  against the conditioned sampler/local search, report that result and stop model
  escalation. Never retain only favorable families or seeds.

## Execution and provenance

One bounded Modal CPU function,4 cores/16GiB, timeout1800s/startup180s, retries0,
max1 container. Shared USD150 reservation policy, fresh billing, checkpointed call
ID, conservative CPU reservation, no automatic paid retry. Compile/test locally
before dispatch. Only anonymized126-row case matrices are supplied for private
cloud computation; provider raw files are not published. Publish source checksums,
case hashes, sufficient statistics/coefficients and outputs; source data stays local.
No final-market or published holdout returns enter this experiment.

Persist protocol, input identities, source snapshot, records, prefix metrics,
references, circuit exports/verifications, ablation and eligibility reports, cost,
plots and English findings. Download and verify every cloud artifact hash. Record
negative findings and the specific next technical decision they imply.
