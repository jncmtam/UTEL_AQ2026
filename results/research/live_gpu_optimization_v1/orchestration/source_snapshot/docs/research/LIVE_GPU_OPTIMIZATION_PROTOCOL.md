# Live LLM feedback optimization on Modal GPU

Registered: 2026-11-05, before live outputs. Run: `live_gpu_optimization_v1`.
The user explicitly requests one model and a new complete live GPU run. This
supersedes the prior no-new-inference stop for this bounded experiment only.

## Evidence, choice and alternative

[Agent-Q](https://arxiv.org/abs/2504.11109v2) evaluates generated parameterized
circuits and motivates measured feedback, but does not establish financial
utility for our checkpoint. [Hadfield et al.](https://arxiv.org/abs/1709.03489v2)
supports constraint-preserving alternating operators. The
[Qwen model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)
documents 30.5B total / 3.3B active parameters and coding capabilities; no quantum
accuracy guarantee follows. Sources checked again on 2026-11-05.

Choose only pinned `Qwen/Qwen3-Coder-30B-A3B-Instruct`, revision
`b2cff646eb4bb1d68355c01b18ae02e7cf42d120`, BF16 / vLLM 0.15.0 / one A10080GB.
It already loads successfully and generated 8/8 valid v2 programs. The diagnosed
defect is identical first-enum star graphs, not insufficient weight count.
Alternative: 80B or a quantum specialist; rejected for this run because current
evidence does not show better financial circuit design. No model sweep/fine-tuning.

## Data suitability and scope

Use exactly the four opened US cases in live_edge_v2: N12/K3 and N20/K5, each
base/mandatory-exit. All supports remain represented; no LLM stock filtering.
The pinned author's 2010 US corpus has 386 securities and 252 returns; these cases
use its first126 rows. It has real cross-sectional dependence and benchmark
returns, but full-year membership conditioning and artificial policy buckets.
Cases/seeds are dependent development comparisons, not independent market tests.
Historical DJIA/DIA admission remains closed. No investment-return or historical
deployability claim will be made and no final financial partition is opened.

## Live intervention

One resident GPU worker loads the model once. Three sequential rounds of four
requests: initial data-conditioned circuit, then two revisions with actual measured
allocated-F and resource feedback. Exactly12 maximum generations; invalid outputs
remain in the denominator. Temperature0.6/top_p0.9, seeds500+100*round+case,
max2048 output tokens, max16K total context. No automatic repair/additional rounds.

Use existing edge-v2 program grammar and exact cost/preparation. Permute each
child's edge enum deterministically by case/round seed (choices unchanged) to
remove the systematic first-enum star presentation. This is an interface change,
not evidence of improved model intelligence. Never prohibit a star, force a new
graph, change financial coefficients, or attribute compiler scheduling to LLM.
Expose all prior live proposals' summaries, not only successful revisions.

LLM sees exchange-B moments, correlation stability, holdings/mandates and measured
F feedback. It proposes exchange edges and beta sharing. B remains the immutable
equal-weight proxy; F is continuous allocated tracking/cost. Neither prompt text
nor feedback resolves their mathematical mismatch. Text rationales are unverified.

## Execution and controls

GPU handles real vLLM inference and torch complex128 conserved-state QAOA evolution.
No CPU simulation fallback: verify CUDA availability and crosscheck NumPy vs CUDA
amplitudes before any generation, residual<=1e-10. CPU handles exact compilation,
independent verification, COBYLA control and CLARABEL allocation inside the same
GPU container. This hybrid workflow is not physical quantum hardware execution.

Every architecture gets eight angle evaluations of64 draws plus64 final draws,
gated mean allocated-F fitting at empirical feasibility>=95%, seed11 for design.
Three random architecture proposals per case receive the same grammar, resource
caps, angle/observation budget and common preparation as the three LLM proposals.
Numerical random search chooses its best proposal; it is a search control, not a
replication of semantic feedback. Fixed scheduled path, deterministic star,
conditioned uniform and allocation-aware swap are mandatory references. Classical
samplers get 3*576 development draws, matching total architecture-search samples.
No shared allocation cache across runs; failures/duplicate programs stay charged.

Choose each LLM/random winner by best observed allocated F on seed11, requiring
an eligible final feasibility batch; break ties by compiled depth. Rejected and
ineligible candidates cannot win. Fixed references use one576-draw design run;
the LLM/random searches use three576-draw runs. Report those different design
budgets explicitly and do not call fixed-vs-search an equal-total-budget comparison.
Freeze each LLM/random winner on seed11 **before** evaluation seeds23/47. Evaluate
all six selected/control methods on both seeds, each with576 draws; all angle
fitting is still on the same training data. These are fresh stochastic seeds,
not independent financial out-of-sample tests. Charge architecture search in full;
do not describe selected-method test costs alone as end-to-end cost.

## Acceptance and stopping

- Engineering: 12 attempted responses retained; every admitted program independently
  checked; CUDA/NumPy selfcheck passes; exact H/hash/caps retained; financial audit
  and all artifact checksums pass. Failures remain explicit.
- Usefulness target (not guarantee): feasible live designs plus >=2% pooled
  allocated-objective improvement over matched random search and fixed star, with
  no>5% case-level mean regression; report every paired result and feasibility.
- Strong finance reference: report allocation-aware swap even if it wins. No
  usefulness qualification if LLM fails the target; no population inference from
  four related development cases. No escalation to hide a negative result.
- One GPU job, timeout2400s + startup600s, max1 container, retries0, scale down2s.
  Per-experiment reservation ceiling15USD, bounded also by the authorized150USD
  policy. Reserve startup/runtime/CPU/RAM with margin using live billing rates.
  A reservation is not a bill. Keep before/after snapshots. Do not assume credit.
- Stop on incompatible runtime, CUDA/hash/numerical verification failure, budget
  refusal or timeout. Retain call ID and remote volume checkpoints; retrieve an
  existing call without redispatch. No automatic new paid attempt.

## Artifacts

Save protocol/source snapshot, data manifest, every logical prompt/schema, actual
model raw text/tokens/finish reason, per-round admission/evaluation/feedback,
selection lock, every run, decision/weight/trade records, executable circuit
exports, CUDA proof, checksum manifest, cost report, English results/progress and
visual comparisons. Preserve earlier v1/v2 evidence unchanged. Update AGENTS.md,
README/worklog and commit/push reviewed files on the existing branch.
