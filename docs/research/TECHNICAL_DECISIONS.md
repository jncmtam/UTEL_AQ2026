# Technical decisions derived from evidence and data

Date: 2026-11-02. Status: reviewable decisions; GPU comparison is on hold.

Evidence IDs E1–E13 refer to [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md).
Local measurements refer to [DATA_SUITABILITY.md](DATA_SUITABILITY.md).

## 1. Decision chain and claims

We will use this order:

**financial decision → data suitability → faithful mathematical objective →
classical difficulty → verified circuit baseline → model shortlist → frozen study**.

Every implementation or experiment must answer: what uncertainty is being reduced,
which source or measurement motivates it, what output will settle the question,
and what result would make us stop or change direction?

Primary financial decision: maintain an existing US-equity sparse tracker after a
mandate changes. Separate risk/return experiments test transfer, not the main pitch.
The LLM designs the quantum search program. QAOA proposes supports. A common
allocator assigns weights. Statistics and compiler code own financial arithmetic.

Permitted claims form a ladder:

1. Verified infrastructure and faithful accounting.
2. Better QAOA design within the tested grammar and resource range.
3. Better final portfolio decisions after allocation and total cost accounting.
4. Practical quantum advantage, only with appropriate hardware and full comparisons.

Passing one level does not imply the next. A useful negative result is acceptable;
continuing until a favorable seed appears is not.

## 2. Financial model before solver choice

Let B(S) be the equal-weight selection proxy and F(S) the best feasible allocated
objective for the same support. Compare them explicitly; E8 does not remove their
possible ranking mismatch.

For small cases enumerate supports and solve each allocation. Record allocation
feasibility, rank association, F-regret of the B-optimal support, and the full
support/weight reference or bound. Unknown/time-limited solves are not optima.
Compare final outcomes with the common allocator, including failures. If distortion
from B to F dominates the desired improvement, revise the selection model before
spending on circuit generation. No larger LLM can repair an unfaithful objective.

Use continuous, self-financing accounts and explicit turnover conventions.
Required exits may conflict with turnover limits; diagnose such cases before
optimization. Include holding the incumbent and classical maintenance as references
because E9 already demonstrates the importance of preserving existing trackers.

Financial costs are stated account assumptions with sensitivity analysis, not
historical spread estimates inferred from daily close data.

## 3. Quantum baseline and bounded design freedom

**Adopt:** immutable direct QUBO/Ising compilation; cardinality-conserving exchange
blocks; explicit initialization and parameter ownership; complete post-measurement
financial checking; an independent quantum executor and cost evaluator.

**Compare:** fixed path/ring, correlation rule, random structure, adaptive classical
structure search, and a carefully implemented ADAPT-style operator selector.
E10/E11 justify the adaptive comparator. Do not label the current mutation heuristic
as ADAPT-QAOA. Operator-pool restrictions and every gradient evaluation are counted.

**Not yet selected:** tree-only grammar, one-layer depth, three preparation edges,
COBYLA as universal optimizer, eight proposals per instance, or uniform fixed shot
counts. These are prototype settings, not conclusions from the literature.

Before freezing them, run one non-LLM development study:

- Initialization: fixed-K Dicke construction (E13), incumbent-based exchange
  superposition, and a relaxation warm-start if its preprocessing is accounted for.
- Architecture: path/ring versus a broader connected exchange pool. A tree grammar
  is a reliability control, but may exclude useful structures.
- Parameterization: shared versus grouped angles with comparable optimization cost.
- Optimizer: deterministic expectation optimization for geometry diagnostics;
  finite-shot derivative-free optimization for operational comparison. Do not mix
  access to exact distributions with sampled feedback without labeling it.
- Resource ladder: small analytic cases, then larger resource-feasible structural
  cases. Fix depth/parameter caps from measured cost and trainability, not size pride.

E12 motivates these comparisons but does not prove trainability of our full cost.
The measured dense financial interaction matrix means mixer sparsity alone cannot
make the complete cost layer sparse. Count state preparation, all RZZ gates,
ancillas, routing and transpilation, not just LLM-owned exchange edges.

Do not keep redundant cardinality penalties in a proven fixed-K subspace without
measuring their numerical/resource effect. Prove and test any omitted constant or
redundant term on the supported subspace, record a new Hamiltonian version, and
never silently change a frozen experiment. Slack penalties for other inequalities
may create a scale imbalance; measure feasible probability and gradient/activity
before selecting the encoding.

## 4. Model admission rather than model-size escalation

The initial comparison set is QUASAR 4B (native QASM specialist), Mistral Qiskit
24B (framework specialist), and the existing Qwen Coder 30B (general control).
E3/E6 and the publisher card justify specialist inclusion; they do not guarantee
transfer. 80B is a conditional comparator. 397B/480B remain deferred.

Before loading any new model:

1. Verify public checkpoint identity/revision, license, tokenizer/chat template,
   native format, supported inference engine and approximate memory requirement.
2. Create an interface probe specification from the source's documented use.
3. Define separate native-code correctness and constrained-GateIR transfer tasks.
   Requiring a QASM-trained model to emit new JSON is not a replication of its paper.
4. Freeze prompts, token/repair budgets and comparison methods in Markdown/JSON.
5. Dispatch a bounded batch only when that experiment can resolve an identified gap.

A candidate is retained for improved functional reliability or useful quality/cost
trade-off on our task. No production winner is selected by the reviewed papers.
If all models fail at the same grammar/encoding bottleneck, fix that bottleneck
instead of automatically increasing parameters.

## 5. Benchmark design and evaluator audit

Three distinct benchmark layers are required:

| Layer | Unit | Main measurements | What it cannot establish |
|---|---|---|---|
| Program correctness | Declared quantum behavior with independent fixtures | Schema, gates, Hamiltonian/bit order, invariants, semantic execution, truncation and first-pass/repair success | Portfolio quality |
| Architecture utility | Same Hamiltonian/constraints with matched design/search budgets | Feasibility, expected regret, probability of useful feasible samples, parameters, two-qubit depth and complete search cost | Investment performance or quantum speedup on a simulator |
| Financial decision | Same audited historical state, then each method's own continuous account | Compliance, tracking RMSE/TE, turnover, realized costs, allocated regret/bounds and stability | Universal alpha or a benefit outside the tested universe |

E5 requires an audit of the evaluator itself: positive controls, known wrong signs,
wrong qubit mappings, missing costs, unexecuted tests, reference-code isolation,
cardinality-breaking gates, and candidate code that prints the expected answer
without producing the required behavior. Generated general-purpose code must run
in an isolated environment; valid GateIR remains declarative data.

Do not require distribution fidelity to one optimizer-produced circuit as the sole
criterion of optimality: different distributions can produce equally useful
portfolios. Fidelity is appropriate for compiler-equivalence tests. For sampled
behavior checks, calibrate acceptance against the reference sampler's own
finite-shot variability, as motivated by E4; do not copy its KL threshold blindly.

### Data and mandate factors

- Development 2014–2018; validation 2019–2021; historical test 2022–2025 only after
  dataset admission. Historical test dates are not guaranteed unknown to LLM training.
- Hold market fixed and change mandate; hold mandate fixed and change market.
- Include mandatory exits, sector count/weight distinctions, turnover, replacement
  budgets, jointly infeasible requirements and no-change cases.
- Anonymize asset labels for architecture experiments; permute labels/qubits
  consistently. This tests invariance, not complete protection from pretraining.
- Full profile, constraint-only, additional-correlation-descriptor ablation and
  profile interventions; keep canonical financial coefficients fixed. Removing
  correlation prose does not remove covariance information from the coefficients.

Start with a declared diagnostic set rather than a huge model grid. Determine
sample size from observed development variability and a prespecified meaningful
effect, then freeze it before a final test. Three sizes and multiple seeds are not
independent financial evidence. Cluster uncertainty by decision window/trajectory;
use paired comparisons and correct planned multiple model comparisons.

### Budgets and selection

Report both equal angle/shot budgets (mechanism comparison) and complete time/cost
budgets (operational comparison). All prompts, invalid proposals, repairs,
verification, gradients, initialization, angle fitting and allocation count.
A parameter-rich proposal is charged for its extra optimization requirements.

Predeclare one primary architecture metric after the financial tolerance is set:
probability of obtaining an allocation-feasible portfolio within the allowed
financial regret at a stated complete budget. Also report feasible mass, expected
conditional regret and cost. Conditional quality cannot hide infeasible mass.
Where an exact allocation optimum is unavailable, use certified bounds or report
unknown; never call the best observed method ground truth.

## 6. What counts as good evidence

- **Correctness:** every accepted artifact meets the declared invariants and
  independent reference checks; numerical tolerances are engineering tolerances.
- **Model reliability:** report first-pass and bounded-repair outcomes with intervals
  on independent tasks. Existing 95% is an engineering aspiration, not a paper-derived
  prediction for this task.
- **Method contribution:** a prespecified effect against the strongest matched
  adaptive baseline, with uncertainty and unseen structures. Existing 20% improvement
  is provisional, not a statistically justified financial margin.
- **Financial value:** compliance and an interpretable tracking–cost Pareto trade-off,
  robust to costs/estimation, plus full accounting. Choose the acceptable tracking
  deterioration from the intended account use case and lock it on development.

Do not convert the Sharpe, energy, KL or turnover numbers in E1–E13 into AGQO pass
thresholds. Their objective units, universes, time horizons and evaluation access
are different.

## 7. Gate ledger and stop rules

| Gate | Required artifact | Present status | If it fails |
|---|---|---|---|
| Research rationale | Evidence matrix and method-specific justification | Initial targeted review complete; exclusive novelty unresolved | Narrow/change the research question |
| Data suitability | Complete identity/action/as-of audit | Blocked: UTX and all permanent identities; context absent | Repair evidence or revise period explicitly |
| Financial fidelity | B-versus-F distortion and joint reference on approved cases | Synthetic infrastructure exists; market assessment blocked | Revise selection formulation |
| Classical difficulty | Time/bounds and tailored local search on same formulation | Not established on admitted market data | Report ease; no hardness/speedup claim |
| Quantum baseline | Initialization/encoding/resource study without LLM | Prototype only; not a frozen winner | Fix encoding/ansatz before model comparison |
| Model interface | Native/IR probes, pinned checkpoints and frozen protocol | Pending specialists; no final model | Analyze interface/task failures |
| Main study | Paired, frozen evaluation and complete cost | Not started under this protocol | Report unsupported/inconclusive result |

Next work is data/identity review and the non-LLM baseline specification, not an
additional large-model batch. Continue to log each result and decision in
[WORKLOG.md](WORKLOG.md) before starting the next dependent action.
