# What the decision audit changes

The observed5.96% deterioration was not simply a mean-versus-one-lucky-draw reporting issue. Under the recorded fit histories, the conditional expected final-decision gap is5.81%. The detailed circuits have7.98% lower operational mean loss on average but3.26% worse expected final-only best-of64. These four related pairs do not establish an unconditional policy-level cause; they do show that mean quality is an inadequate decision proxy here.

The exhaustive numerical reference covers27,132 supports, with27,105 optimal-status feasible allocations and27 infeasible supports. All27 infeasibilities independently contradict the sector budget: a fully invested portfolio selected entirely from a group capped below100%. No exact-arithmetic joint certificate is claimed. Local allocation-aware swap matches the numerical feasible incumbent in both cases at both source seeds. This benchmark currently offers no observed quality headroom over that classical reference. The best base portfolio needs only one new position relative to the original support; the exit portfolio needs two. That small repair radius helps explain why informed local search is an appropriate strong baseline. A15504-support count alone does not establish practical search difficulty.

Even selecting the **exact minimum of the current equal-weight B proxy** leaves11.07%/8.35% allocated-F regret. A perfect proxy solver therefore does not solve the continuous allocation problem in these cases. This does not prove QAOA cannot sample better F supports; it proves the two optimization targets are not identical. Correlation between B and F (~0.64/~0.63) is not sufficient faithfulness evidence.

## Decision units, not just a loss number

| Case / selector | Estimation daily tracking RMSE (bps) | One-way turnover | Proportional transaction cost (bps NAV) |
|---|---:|---:|---:|
| family1_n20_base / best_allocated_F | 41.269 | 31.477% | 3.148 |
| family1_n20_base / proxy_optimum_after_allocation | 42.911 | 40.000% | 4.000 |
| family1_n20_exit / proxy_optimum_after_allocation | 42.911 | 40.000% | 4.000 |
| family1_n20_exit / best_allocated_F | 40.848 | 40.000% | 4.000 |

The base-case continuous reference improves tracking and reduces turnover/cost versus the proxy-optimum allocation. After the exclusion mandate, it improves tracking at the same modeled transaction cost. These figures are estimation-window diagnostics under the supplied proportional-cost model; they do not include fixed trade fees, slippage or taxes, and are not future returns. The source universe and artificial policy groups remain conditional research data.

## What was actually improved

The code now measures expected best-of-budget quality and conditional final-decision quality while keeping feasibility/failure mass. It constructs a checked numerical reference, verifies allocation values independently, and records both new and reused computation. It makes no unsupported claim that the LLM or optimizer has become financially better. The exact table is exponential preprocessing and makes classical lookup trivial; it is not a deployable quantum oracle.

The next technical gate is a faithful weight/selection formulation, plus a benchmark with demonstrated classical quality/resource headroom. Another model-size, CVaR-alpha or prompt sweep on these two cases would not answer that problem. See the linked next-gate specification; no new paid work is scheduled by it.

[Detailed audit and curves](RESULTS.md) · [Decision-unit records](financial_comparison.json) · [Reference checks](SUPPLEMENTAL_AUDIT.json) · [Next formulation gate](../../../docs/research/FORMULATION_NEXT_GATE.md)
