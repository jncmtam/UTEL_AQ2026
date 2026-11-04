# Feasibility-gated allocated-tail fitting pilot

Date: 2026-11-04. Frozen before implementation and outcome inspection. Local
CPU-only opened development study; no new model, GPU, market admission or test-set
qualification. Extends CONTRIBUTION_STRATEGY.md without changing prior runs.

## Evidence, rationale and alternatives

[Barkoutsos et al., Quantum2020](https://arxiv.org/abs/1907.04769v3) supports testing
lower-tail CVaR aggregation rather than only mean energy. [Yu/Jin, IEICE2025](https://www.jstage.jst.go.jp/article/transinf/E108.D/7/E108.D_2024EDP7254/_article)
already applies CVaR-QAOA to portfolios; CVaR itself is not our novelty. Their
iteration counts are not complete-cost financial acceptance thresholds.
[Stopfer/Wagner v3](https://arxiv.org/abs/2509.17876v3) motivates strong classical
controls, although its variance objective differs from our tracking/cost task.

Our opened controls show a mean-vs-best-of-budget distinction and a classical
local-search lead. Tail fitting might change finite-budget sampling quality;
it cannot remove the B/F proxy mismatch. Alternatives are existing mean fitting,
conditioned uniform and direct allocation-aware swap search.

## Software contract

Add opt-in `fitting=mean|lower_tail` to budget_search.search. Default None retains
the existing legacy mean-feedback numerical path. New fitting is restricted to
allocated tracking_cost; risk_return requires separately signed normalization.
Compiler COST remains B, not a coherent F oracle. No change to coefficient hashes.

Each sample has normalized allocated F in [0,1] when feasible, otherwise loss2.
Existing floating-point bound tolerance is retained; no clipping. Unknown and
infeasible statuses remain distinct and in every denominator. Empirical lower-tail
loss averages the lowest alpha mass of *all* observations, with fractional boundary
weight when alpha*n is noninteger. It is not financial return-tail risk.

Both opt-in mean and tail modes use the same empirical feasibility gate. If the
batch's feasible fraction is below q, optimizer loss is `2+q-feasible_fraction`;
otherwise it is the declared mean/tail loss. The disjoint ranges prioritize
feasibility without omitting invalid observations. This is a measured batch gate,
not a statistical certificate of population feasibility. Record every batch,
best-fit gate status and final batch gate separately. A feasible portfolio found
in the pooled observations is retained even if the fitted distribution is unqualified.

## Frozen development pilot

- Use exactly improvement_v1's eight opened cases, first126 observations of the
  pinned 2010 US corpus, families0/1, N12/K3 and N20/K5, base/exit. No new market
  or held-out returns. Full-year membership conditioning and artificial policy
  buckets remain; no investability/financial-return claim.
- Common single-layer disjoint-scheduled path, compiler counter-Dicke preparation,
  paper_rms_v1 coordinates, immutable B and unchanged F allocator.
- Four arms: gated mean-F, gated lower-tail-F, conditioned uniform, allocation swap.
  Seeds11/23/47. Eight angle evaluations*64 samples +64 final samples =576
  observations/run,96 runs,55,296 observations total. Classical controls have the
  same observation budget. This is not equal total runtime or allocator cost;
  actual allocations/cache hits, simulation calls, setup and times are reported.
- alpha=.25 yields16 tail observations per fitting batch; q=.95 empirical batch
  feasibility. These are frozen diagnostic settings, not tuned economic thresholds.
- Report prefix best feasible F at64/128/256/512/576 observations. Also report all
  sample feasibility, final64-shot feasibility, unknown counts and gate failures.
- An algorithmic hit target is 1.05 times the previously saved feasible5s SCIP
  incumbent per case (from improvement_v1). This is a prespecified opened-data
  reference, not a global optimum or economically justified financial margin.
  Report observed pooled/final hit fractions, not independent Bernoulli significance.
- No new SCIP search, architecture search, LLM inference or hyperparameter sweep.
  Each run has a separate allocator cache. All optimizer/final observations remain
  in the decision pool. Every failed/unknown attempt is retained.

## Budget, acceptance and stop rule

Local CPU only, no paid reservation. Single sequential process; checkpoint each
run, resume only identical protocol/input/source hashes. Stop at all96 runs or
1800 cumulative run seconds, checked between runs (an in-flight bounded run may
finish beyond this threshold); interrupted/error results remain explicit and are
never counted completed. No automatic rerun of completed runs. Write run/source
identities before fitting and preserve partial results. Budget is a diagnostic
ceiling, not a guaranteed runtime estimate.

Software: fractional CVaR arithmetic, alpha1 mean identity, pathological invalid
mass, status separation, preserved feasible decision with failed distribution
gate, exact sample/solver accounting, separate final gate, tracking-only scope
and legacy equivalence. All existing tests must pass.

Performance: report paired tail-minus-mean F and actual quality/cost frontier
against uniform and swap, with all related cases/seeds. No significance claim
from two families. A sampler win only against mean fitting is an aggregation
result, not overall financial advantage. If it does not offer a useful frontier
against strong search, stop model escalation and report the limitation. No alpha
or seed adjustments after outcomes; any further study requires a new protocol.

## Required artifacts

Frozen protocol/input/source hashes, raw per-run observations and allocation
results, batch fitting records, immutable Hamiltonian identity and verification,
sufficient financial statistics for independent rescoring (no raw source returns
published), prefix metrics, hit/feasibility diagnostics, local cost/runtime report,
plots, RESULTS.md and PROGRESS.md. Attribute all results to CPU simulation/classical
controls; no new LLM or quantum-hardware result.
