# Financial formulation identity gate

Date: 2026-11-03, before the following audit. This is an opened development
diagnostic, not a new held-out experiment. No LLM/GPU inference.

## Why this gate precedes model selection

Counter-Dicke preparation removed sparse coverage, but N10 allocated quality
worsened and matched-total-draw classical sampling remained stronger at N30.
The selection proxy B(S) assumes equal weights, while the allocator F(S) optimizes
weights. Better B is therefore not automatically a better financial decision.
Changing the LLM cannot make these definitions identical.

Compare two explicitly different financial mandates using the existing model:

1. **Continuous allocation (unchanged primary task):** position bounds .02 to .60.
   Measure B/F rank and proxy-optimal allocation regret across every small support.
2. **Equal-weight target alternative:** minimum=maximum=1/K. The target decision
   is explicitly equal-weight at rebalance; weights may drift after execution.
   The same allocator must keep support membership and return exactly x/K. On
   feasible supports, its objective must equal the independently evaluated B.

The alternative does not silently replace the primary task, make the corpus an
unbiased investment universe, or claim all managers prefer equal-weight holdings.
Its advantage is an exact support QUBO with matching downstream semantics. Its
limitation is loss of allocation flexibility. Richer discrete-weight encoding or an
allocation-aware outer solver remain alternatives with greater qubit/classical cost.

## Audit

Use the same pinned hash-ordered N10/K3 family, first126 observations, base and
exclude-incumbent scenarios. Keep tracking, transaction costs and synthetic policy
weight cap unchanged. Enumerate120/84 support assignments; preserve infeasible
allocations. Compare allocated F against direct tracking-MSE plus trade-cost from
the target weights, not just against a second copy of the QUBO function.

Acceptance for the equal-weight alternative: every feasible target has max position
deviation <=1e-7 and financial objective difference <=1e-9. Infeasible support
weights must remain rejected. Exact linear/quadratic encoding identity is a
correctness gate, not an empirical superiority target. Continuous proxy regret is
reported with no post-hoc threshold picked to fit the observations.

Write a separate protocol/source snapshot/manifest/records/metrics/report. No new
quantum run is needed for this identity audit. If the equal-weight gate fails,
repair the model before any claim or model run; do not loosen its tolerance.
