# Performance and contribution strategy

Date: 2026-11-04, Asia/Ho_Chi_Minh. Evidence-informed recommendation, not an
executed experiment, confirmed novelty claim, or change to production semantics.
No model selection, new paid work, holdout opening or software experiment here.

## Recommended research question

Can verified, allocation-aware circuit edits adapt a portfolio support sampler
after an investment mandate changes, reaching a specified feasible tracking/cost
quality with less complete adaptation effort than circuit reuse, full redesign
and strong classical alternatives?

Keep the financial task: repair an existing constrained US-equity tracking
portfolio. LLM proposes circuit architecture/edits; QAOA samples supports over the
entire admitted universe; one common numerical allocator assigns weights. No
LLM stock filtering. Quantum superiority and model usefulness are separate claims.

## Why this direction follows from evidence

- Opened N20 development results: scheduled circuit vs conditioned uniform is
  -7.63% at8 observations, +1.88% at88; allocation-aware local swap is -16.74% and
  -10.12%. These are related training-objective comparisons, not return effects.
  Early samples precede angle adaptation. A larger LLM is not the first remedy.
- Current exchange descriptors are exact for B, not the continuous allocated F.
  The proxy-optimum allocation can be worse than another support's allocation.
- Mean sampled F guides fitting, but the decision selects the best observed F.
  Different distribution objectives can favor different circuits; the mismatch
  is real, but its causal contribution to the measured deficit is not established.
- Eight guided requests/964 pair records exist; no model has run under that new
  contract. Traceability is not evidence of useful adaptation.

Read improvement_v1/INSIGHTS.md and data_guidance_v1/RESULTS.md before interpreting
any proposed improvement as an observed outcome.

## Primary literature and novelty boundaries

| Source checked | Established contribution | Implication for AGQO |
|---|---|---|
| [Agent-Q, QCE2025, v2](https://arxiv.org/abs/2504.11109v2) | LLM fine-tuning for parameterized circuit generation/optimization | Generating QAOA with an LLM is not the novelty |
| [Autonomous circuit design, June2026](https://arxiv.org/abs/2606.13380) | Iterative LLM design/validation/evaluation on feature maps and molecular ansatzes | A multistage feedback workflow alone is insufficient |
| [Certified agent circuit optimization, Oct2026](https://arxiv.org/abs/2610.31352) | Frozen exact verification and agent-driven optimization on three compilation tasks | Independent verification plus agent edits already has precedent |
| [Barkoutsos et al., Quantum2020](https://arxiv.org/abs/1907.04769v3) | Lower-tail CVaR aggregation for variational combinatorial optimization | A justified fitting baseline, not a new AGQO technique |
| [Yu/Jin, IEICE2025](https://www.jstage.jst.go.jp/article/transinf/E108.D/7/E108.D_2024EDP7254/_article) | CVaR-QAOA portfolio experiments on Nasdaq data | CVaR plus portfolio selection is also established; their iteration counts do not supply matched-cost thresholds |
| [Gambella/Simonetto, IEEE TQE2020, v2](https://arxiv.org/abs/2001.02069v2) | Binary/convex ADMM decomposition with simulated quantum subproblems | A formulation alternative, not a promised convergence/speedup fix |
| [Stopfer/Wagner, v3 Oct2026](https://arxiv.org/abs/2509.17876v3) | Strong MIP/tailored heuristics dominate their variance-minimizing portfolio variant | Strong direct classical finance baselines remain mandatory; their task differs from ours |

These primary sources support the method choices and reject broad novelty claims.
The combined mandate-change/allocation-aware circuit-editing question is a
candidate contribution requiring a fuller nearest-neighbor literature review.
No absence-of-prior-work claim is established by this bounded review.

## Priority 1: align the measured and trained financial target

For support S and effective mandate m, define F_m(S) as the common allocator's
minimum tracking/cost objective subject to weights and mandate constraints.
Retain infeasible and solver-unknown statuses separately. B_m(S) remains the
equal-weight proxy used in the immutable cost Hamiltonian.

First compare mean-F fitting with a prespecified lower-tail-F fitting objective
using one common verified compact circuit. Here lower-tail CVaR averages the best
fraction of *sampled portfolio scores*. This is not financial tail-risk CVaR of
future stock returns. It may align better with finding a good candidate, but is
not identical to minimizing expected best-of-budget F and is not guaranteed better.

Feasible probability is a separate admission/selection criterion across all shots.
A lower-tail score must not hide low feasible mass, dropped failed allocations or
solver-unknown cases. Use the same declared treatment of those statuses in every
arm. Report best feasible F and probability of hitting a development-fixed quality
target, not just the average fitting loss.

Small tails need adequate samples. At alpha=.25,8 shots supply only2 tail scores;
64 shots supply16. These are arithmetic examples, not a selected new budget or
power calculation. Freeze alpha, shots, optimizer evaluations and pilot cost in a
separate executable protocol before running. All observed supports, solves,
failures, cached lookups and architecture/gradient evaluations count.

The current B phase separator still is not a coherent F oracle. Feedback changes
alone do not fix this structural limitation. If useful downstream quality does
not emerge, derive a binary/continuous decomposition classically before using
QAOA. Check that its binary step is genuinely combinatorial rather than solvable
by sorting, and charge outer iterations. Do not silently replace the continuous
financial task by an equal-weight task to obtain a win.

## Priority 2: study reuse, retuning, edits and redesign after changes

Start from a previously verified circuit and documented incumbent portfolio.
Change one mandate element, then combinations: exclusion, sector cap, turnover
limit or cardinality. Include no-change controls and genuine conflicts.

Compare four adaptation choices: reuse a valid structure; retune its angles;
apply bounded structural edits; or design from scratch. Compiler-owned cost,
frozen bits and required preparation are updated consistently for the new problem.
Reuse cannot mean retaining an invalid old Hamiltonian or disadvantaged broken
circuit. Specify and charge a deterministic validity-preserving rebase where
register/preparation changes make literal reuse impossible.

LLM edits can change exchange edges, ordering and beta sharing within an admitted
grammar. Preserve every asset in the financial universe. Connected exchanges
support cardinality reachability under the stated executor conditions, not every
inequality-feasible portfolio or arbitrary finite-depth expressivity.

The current parent<child grammar is dependent on asset ordering and excludes some
tree topologies for a given labeling. Before a new comparison, either explicitly
retain and test this restriction or version a general connected-edge-list grammar
with independent connectivity/cardinality checks. A descriptor permutation test
does not establish permutation robustness of the generated circuit.

Measure adaptation cost: model tokens/time, feature construction, verification,
new angle evaluations, allocation solves, failed proposals and compiled resources.
Also report total cost over a fixed sequence of changes, including the initial
circuit. Warm/cold costs and amortization assumptions must be explicit.

## Priority 3: guide with changes and allocation evidence

Use data changes rather than a repeated dump of correlations:

| Evidence | Possible circuit decision | Essential qualification |
|---|---|---|
| Existing exact B-exchange moments and window stability | Propose exchange rewiring or sharing | Sensitivity is neither improvement direction nor quantum gradient |
| Newly binding limits, frozen bits, incumbent violations | Rebase domain/preparation and change exchanges | Weighted constraints still require allocator checks |
| A small common calibration pool's B-vs-F errors | Detect unreliable proxy regions; choose a bounded edit to test | These are paid-in-budget classical allocation probes, not free descriptors or a global F model |
| Sampled feasibility and quality/resource feedback | Keep, edit or abandon a proposal | All observations/failures count; no silent fallback attribution |

Numerical code computes features and retains cutoff/hash/source references. An LLM
chooses a testable edit; the compiler owns coefficients. Any allocator feedback
supplied to the LLM must also be available to rule/adaptive classical comparators
under the same total budget. The classical preprocessing itself may explain the
gain; directly test that possibility.

## Priority 4: establish the LLM's incremental contribution

Keep fixed model/revision, common preparation, compiler, angle optimizer, accepted
grammar and total costs. Required circuit-design comparisons are fixed/rules,
random edits, adaptive numerical mutation, LLM without numerical guidance, and
LLM with guidance. Separate existing-circuit reuse/retuning from full redesign.
Use a staged/factorial subset first to avoid an uncontrolled experiment matrix.

Add consistent asset permutations; benchmark changes with identical asset-return
correlations; mandate-only changes; descriptor removal; and unseen combinations.
Changing prose or gates is not sufficient: the change must improve downstream
quality/resources. Descriptor shuffling leaves the Hamiltonian as another data
channel, so it does not remove all instance information.

Compare the *whole system* against conditioned uniform, warm-started allocation-aware
local search, a strong sparse-tracking method and SCIP solutions/bounds. A win over
fixed QAOA supports a circuit-method claim; a win over direct finance baselines
is a stronger separate claim. Do not conflate them.

## Priority 5: build the benchmark that matches the contribution

Use paired before/after mandate cases: unchanged requirements/new returns;
unchanged returns/new requirement; both changed; conflicts; and unseen compound
requirements. Distinguish persistent account trajectories from common-state
algorithm comparisons. Report both initial noncompliance and post-decision compliance.

Keep the conditional 2010 corpus for mechanics. Its full-year membership and
artificial policy buckets prohibit an investable-history claim. Investment testing
still requires source-backed universe/identities/actions/prices/classifications;
missing UTX and incomplete lineages remain blockers. If source search fails, any
new historical scope must be versioned and chosen without reviewing its strategy
outcomes. Do not silently drop difficult names.

Use new families/periods for confirmation after auditing prior exposure. Quantum
seeds and repeated mandates on one return panel are not independent market samples.
Choose case count from a pilot variance/effect analysis at the family/time-block
level, then freeze it. Repeatedly inspecting a test set consumes independence.

## Results that would support a strong competition story

| Claim | Required evidence | Failure condition |
|---|---|---|
| Reliable circuit design | Independent semantic/resource admission and uncertainty over new tasks | Only selected valid runs or citations presented |
| Useful adaptation | Same financial quality with less complete adaptation cost, or better quality at matched cost | Retuning or simple mutation matches the LLM |
| Useful numerical guidance | Guided LLM improves held-out quality/resource tradeoff over unguided LLM and rules | Changes in explanation/topology only |
| Financial value | Admitted continuous accounts; tracking/cost/compliance benefit in decision units | Better B or training F only |
| Quantum advantage | Separate appropriate hardware and full-cost scaling evidence | CPU simulator performance alone |

Predeclare economic quality margins in tracking-error/cost basis points using the
account use case and development sensitivity, not borrowed percentages from a
different paper. For adaptation, compare paired costs at fixed quality or paired
quality at fixed cost, with family/time dependence respected. Choose superiority
or quality-noninferiority/resource-saving hypotheses before evaluation.

A useful paper/demo can show the chain: mandate change -> measured structural
evidence -> exact circuit edit -> verification -> feasible trades -> tracking/cost
frontier. The benchmark and failure taxonomy are supporting contributions. Traceability
alone and a generic LLM/QAOA combination are not the primary novelty claim.

## Concrete next action and stop rules

Prepare a *separate preregistered CPU-only development pilot*: one compact verified
circuit, mean-F versus lower-tail-F fitting, conditioned uniform and allocation-aware
local search. Use explicit B/F status, feasibility, sample/allocation/time accounting
and a justified quality target. Retain the existing dataset solely for mechanics.
This memo schedules no pilot and has no paid-compute reservation.

Proceed to a bounded model-guidance/editing comparison only if a useful circuit
quality/cost opportunity is demonstrated. If only quantum-circuit controls improve,
limit the claim to that level. If the LLM cannot beat rules/numerical edits, stop
LLM scaling. If the sampler cannot compete with informed classical portfolio
search, report the limit and revisit the formulation before adding more complexity.

In parallel, complete source reconstruction. Open independent market outcomes
only after historical admission and a frozen evaluation protocol. No guaranteed
performance, confirmed new research gap or competition placement is promised.
