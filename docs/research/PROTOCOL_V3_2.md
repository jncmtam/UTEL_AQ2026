# AGQO V3.2 evaluation protocol (pre-registered)

Written on 2026-11-20 before any V3.2 holdout result was computed. Changes after that date are listed in §8 with
a reason. All simulations run on Modal CPU (`modal_research.py`), all live LLM calls on Modal H100
(`modal_app.py`), driven by `notebooks/AGQO_V3_2_Research_Modal.ipynb`. Every run writes `run.json` with the git
revision, the price-snapshot SHA-256, the configuration, seeds and errors.

## 1. Data and splits

Price snapshot `7f076128…3042` (the V3 snapshot). Back-adjusted price levels (see §5).

| Split | Dates (first trading day of the month) | Use |
|---|---|---|
| Calibration | 2023-01 … 2023-08 | fit every selector (frozen schedule, k-NN, LLM design feedback) |
| Validation | 2023-09 … 2023-12 | choose among selector variants, set the support threshold |
| Holdout | 2024-01 … 2026-10, **months that are not quarter starts** (22 dates) | final comparison, examined once |
| V3 test (secondary) | the 12 quarter starts 2024-01 … 2026-10 already reported in V3 | reported separately, never used to choose |

Instances: a fresh cash account at each date for five account sizes (20, 50, 100, 200, 500 M VND) and three
constraint types (none; banking ≤ 25%; no real estate) → 120 calibration, 60 validation, 330 holdout instances.
Each instance is the V3 16-qubit cap-safe lot-rounding QUBO with exact enumeration of its 2^n states.

Unit of analysis for tests: the **date**. Metrics are averaged over the instances of one date before a paired
test, so the holdout gives 22 paired values (no pseudo-replication across sizes and constraint types).

## 2. Product reliability (regression suite)

Pass criteria, checked by tests that run on Modal CPU:
1. Every cap, the per-stock limit and the minimum cash are evaluated on the post-trade NAV (cash after fees plus
   holdings). The 200M / banking ≤ 25% case must hold on that basis.
2. `max_holdings = 1` and `2` return a decision; registers with fewer than 2 qubits skip QAOA and say so.
3. Infeasible requests return status `infeasible` with the binding condition(s), never an exception.
4. An instruction that needs clarification produces no personalised trade list until it is answered.
5. The explanation verifier rejects (a) two evidence numbers swapped between strategies, (b) a number with the
   wrong unit, and still accepts the correct sentence.

## 3. LLM experiments (English prompts, Vietnamese investor inputs)

Model: Qwen3.8-27B-FP8 (revision `c3a462cc`), vLLM 0.32, non-thinking mode, JSON-schema constrained decoding,
temperature 0, seed = item index. Prompt versions are stored with every logged call.

### 3a. Instruction parsing

Evaluation set `agqo/research/mandate_eval_v2.py`, written before the first run, disjoint from the V3 set:
clear (24), ambiguous (10), conflicting (8), infeasible-by-construction (8). Gold: every constraint field, the
expected status (`ok`, `needs_clarification`, `conflict`) and, for ambiguous items, the field that is missing.

Arms: keyword rules; V3 prompt; V3.2 prompt (English system prompt with explicit status rules).

Metrics: field accuracy (per field), exact-mandate accuracy on clear items, status accuracy, clarification
precision/recall, clarification-question quality (deterministic rubric: Vietnamese question, one question mark,
names the missing dimension, ≤ 200 characters, no invented limit), conflict recall, and **end-to-end
compliance**: the parsed mandate is run through the optimiser at the item's account size on Modal CPU and the
final outcome is judged against the gold mandate (trades audited on post-trade NAV for `ok` items; status
`infeasible` with the right condition for infeasible items; no trade list for ambiguous items).

Primary claim allowed: V3.2 prompt vs keyword rules on end-to-end correct outcome (McNemar, two-sided α = 0.05).
The set is team-written; results are not a substitute for independent users (stated next to every number).

### 3b. Circuit design and optimisation

Design set: 24 calibration instances (8 dates × sizes 20/100/500M, no constraint). The LLM receives the problem
specification, the allowed components (initial state, mixer, depth, coupling pruning, Hamiltonian scale, angle
schedule, optimiser and its budget, CVaR α), the budgets (two-qubit gates ≤ 1500, ≤ 60 circuit evaluations per
instance) and the objective (maximise mean probability of a near-optimal feasible sample; ties → fewer
two-qubit gates). Two rounds of 8 candidates; round 2 sees the round-1 scores. Every candidate is validated
(schema, `verify`, compiled gate count, evaluation budget) before simulation; failures are logged.

Controls with the same budget of 16 evaluated candidates: random search over the same component space (3 seeds).
Reference: the V3 frozen grid schedule (found with 1,080 candidates).

Primary: best LLM candidate (chosen on the design set) vs best random-search candidate, on the holdout, paired by
date, Wilcoxon one-sided α = 0.05. The frozen schedule comparison is exploratory.

## 4. k-NN schedule selection (standalone track)

Candidate space: the V3 grid of 1,080 linear-ramp schedules (p, ε, coupling mass, Δγ, Δβ). Success table: exact
statevector success of every schedule on every instance, no per-instance optimiser.

Hypotheses
- **K1 (diagnosis).** V3 k-NN lost to the frozen schedule because the top of the schedule landscape is flat and
  the per-neighbourhood argmax overfits (winner's curse). Evidence: in-sample vs out-of-sample regret, spread of
  the top-10 schedules, agreement between a neighbour's best schedule and the instance's own best.
- **K2 (primary).** The k-NN variant chosen on validation beats the frozen schedule on holdout mean success.
  Paired Wilcoxon over the 22 holdout dates, one-sided α = 0.05, plus a date-block bootstrap 95% CI.
- **K3.** A gain "persists" only if its sign is positive in ≥ 4 of 5 account sizes and 3 of 3 constraint types.
- **K4.** Support fallback (frozen schedule when the nearest calibration instance is farther than the validation
  90th-percentile distance) is non-inferior to frozen with margin 0.5 percentage points.

Variant space searched on validation only: feature set (V3 five; V3 + log capital, qubit count, constraint flags;
rank-transformed), scaling (z-score, median/IQR), distance (Euclidean, Manhattan, cosine), weighting (uniform,
inverse distance, Gaussian kernel at the median distance), k ∈ {3, 5, 10, 20, 40}, aggregation (mean success,
mean rank, mean shrunk toward the global mean with m = k), fallback (none, distance threshold). Selection rule:
highest validation mean success; ties → simpler variant (fewer features, uniform weights, larger k).

Baselines on the same table: frozen (best mean on calibration), per-stratum frozen (best schedule per account
size on calibration), random schedule from the grid (expected value), best-of-B random schedules chosen on
calibration (B = 24 and 108), oracle (best schedule per holdout instance, upper bound), warm start alone.

Ablation of local refinement: 40 COBYLA steps on CVaR(0.1) from the frozen schedule and from the selected k-NN
schedule, on all holdout instances.

Reported for every arm: mean success, feasible mass, best-of-512-shots gap, two-qubit gates, circuit evaluations,
simulation wall time, by account size and constraint type.

## 5. Small-account benchmark and the price-level limitation

Historical traded (unadjusted) prices and a corporate-actions file are not available. Back-adjusted levels
understate historical lot costs. Because fees are proportional, multiplying every price by f on a date is the
same problem as dividing the account by f. The 20M benchmark is therefore rerun with the fixed V3.2 code at
20, 18.2, 16 and 13.3 M VND (f = 1, 1.1, 1.25, 1.5) for nearest-lot rounding, greedy lot filling, exact lot
rounding and AGQO, on the 12 V3 quarters. This bounds a uniform understatement; stock-specific adjustment
(e.g. banks with large stock dividends) stays unquantified and is reported as such.

## 6. Presets

Each product preset is run on Modal CPU at its account size on the latest rebalance date and over the 12 V3
quarters. Reported: tracking error vs VN30, cost vs the unconstrained portfolio, holdings, cash, fees, post-fee
compliance, and the outcome class (favourable, unfavourable, infeasible).

## 7. Reporting rules

Negative and inconclusive results stay in the record. Numbers from team-written test sets are labelled as such.
No quantum advantage is claimed: exact enumeration solves every 16-qubit instance.

## 8. Changes after registration

- 2026-11-20, k-NN study, reporting fix (no change to data, variants or selection rule): the first analysis run
  (`20261120-072848-204ca51-knn-study`) evaluated K2 on the selected variant *without* its support fallback,
  although validation had selected the variant *with* fallback. The rerun reports K2 on the variant exactly as
  selected and keeps the no-fallback version as a separate row. Added two descriptive comparisons against the
  per-stratum frozen baseline. Both runs are kept.
