# Weight-grid formulation gate

Registered 2026-11-06 before this implementation's results. Initial run ID: weight_grid_v1; corrected controller ID: weight_grid_v2.
This is an opt-in formulation diagnostic, not a replacement for the continuous
primary task, a new LLM qualification, or an investment-performance experiment.

## Evidence and choice

- [Hodson et al., 2019](https://arxiv.org/pdf/1911.05296) study discrete lots,
  trading costs and constraint-preserving mixers on small simulated portfolios.
  Their long/short risk-return encoding differs from our long-only tracking task.
- [Yuan et al.](https://arxiv.org/abs/2410.16265) study discrete global-minimum
  variance portfolios and hard mixers. Their simulation/noise findings do not
  establish a benefit for our mandates or LLM-generated circuits.
- [Alessandroni et al.](https://arxiv.org/abs/2307.10379), published in npj Quantum
  Information (2025), show that excessive constraint penalties harm the normalized
  energy scale. We start with a conservative coefficient-range bound for correctness,
  report the scale, and make no performance claim about that penalty choice.
- [Rubio-Garcia et al.](https://arxiv.org/html/2210.00807v1) demonstrate strong
  classical discrete portfolio search, including warm starts. Discretization alone
  must not be advertised as classical difficulty or quantum advantage.
- Our decision_audit_v1 measured 11.07%/8.35% allocated regret for exact minimization
  of the old proxy. A more powerful circuit generator cannot make B identical to F.

Use one binary indicator y[i,m] per permitted nonzero amount m/M, at most one per
asset. This trades qubits for a transparent selection/weight projection. Binary
amount registers plus activation and absolute-value gadgets are an alternative;
ADMM and a validated allocation surrogate remain separate alternatives. This first
compiler is a correctness reference, not a claim that one-hot is optimal or novel.
Amounts are fractions of NAV, not executable share lots: no share-price, fractional-
share availability, execution-lag or market-admission claim is made.

## Mathematical contract

w[i] = sum_m (m/M)y[i,m], x[i] = sum_m y[i,m] on valid one-hot-per-asset states.
Compile the exact financial quadratic w'Qw + l'w + c. For valid asset registers,
absolute trade cost is exactly old_w[i] + sum_m (|m/M-old_w[i]|-old_w[i])y[i,m].
No coefficients are selected or edited by an LLM. Preserve both constants.

Enforce amount budget sum m*y=M, cardinality sum y=K, required/excluded assets,
sector counts, sector weights and replacement limits. Integer inequalities use
binary slack with a unique encoding per feasible asset assignment. Add pairwise
one-hot penalties. Bound endpoints use decimal-rational ceil/floor, not rounded
floating products. A grid can make a continuously feasible mandate infeasible.

Turnover caps are supported only when previous weights are compatible with M
(to numerical representation tolerance); otherwise raise an explicit unsupported
error. Include previous cash in half-L1 turnover. With integer old amounts a[i],
2*M*turnover = M + sum_(i,m) (|m-a[i]|-a[i])*y[i,m] on fully invested valid targets.
The constant M includes liquidation of previous cash. Never silently snap drifted
holdings. Proportional trading costs support arbitrary prior weights without a cap.

Let S be the sum of absolute nonconstant financial QUBO coefficients. P=2*S+1e-8
exceeds the full binary-cube objective-range bound. Every nonzero integer residual
square or one-hot pair is at least one. Thus, if a feasible encoding exists, an
infeasible state cannot be a mathematical ground state. This is a conservative
real-arithmetic argument; independently measure floating residuals. It does not
certify the continuous problem or establish a useful physical spectral gap.

## Bounded validation and data suitability

1. Exhaust all binary states for fixed small synthetic controls, comparing direct
   financial values, constraint residuals, QUBO and independent Ising energy. Include
   boundary decimals, contradictions, mandatory exits, cash, turnover and unsupported
   off-grid holdings. Small state evolution is optional, <=16 physical qubits only.
2. Prespecified conditional-US slice: first three assets and first 126 rows of the
   already opened family1_n20_base input, no performance-based asset selection;
   K=2, previous weights (0.5,0.5,0), minimum .02, maximum .7, original cost settings,
   policy groups (A,B,B), A weight cap .7, no turnover cap. This is a changed, tiny
   diagnostic instance, not the original N20 task or held-out financial evidence.
3. Evaluate M=6,10,20,40 grids by all valid amount assignments. Compare against
   the same continuous convex allocator across all three supports, reporting
   discretization regret, feasibility, tracking/turnover and compiler resources.
   Do not enumerate all 2^qubits at larger M; enumerate financial grid assignments
   only. Do not simulate a >16-qubit statevector.
4. Resource-only compilation on original N20 base for M=6,10,20; no giant simulation.
   Explain why ordinary asset XY does not preserve encoded money/one-hot semantics.

Acceptance: direct financial/QUBO/Ising residual <=1e-10 on small exhaustive
controls, exact combinatorial zero-penalty/feasibility equivalence, all feasible
small projections pass independent FinancialSpec checks, grid F no better than
continuous optimum beyond solver tolerance. No required performance or investment
improvement. Report every grid, failure, and resource cost. Stop rather than expand
model/GPU search if precision/resources are unattractive.

Budget: local numerical diagnostics only, 0 Modal/model dispatches, 0 paid inference.
Freeze protocol, inputs and actual source bytes in artifacts. Completed-run guard;
no changes to old compiler, primary objective, grammar, defaults or historical runs.

## Controller correction before any measured financial result

The v1 entry point stopped after input/source snapshotting because it requested
`dataset_manifest` while the existing preparation contract returns `source_manifest`.
No allocation, encoding evaluation, GPU job or LLM call occurred. Retain the partial
v1 directory and its original protocol/source bytes. V2 changes only the provenance
field adapter and run ID before any outcome review; all cases, grids, thresholds
and budgets above remain fixed. This is a controller correction, not a new method.

A second local preflight also failed before creating v2 artifacts: the edge-request
wrapper drops the manifest entirely. The corrected entry point now calls the direct
`improvement.prepare_inputs` provider contract, inspected in source and at runtime,
which actually retains `source_manifest`. The financial cases are unchanged. Both
local failures are disclosed; neither consumed Modal or inference resources.
