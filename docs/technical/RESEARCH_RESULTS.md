# AGQO follow-up study: results

Research record of the follow-up study (protocol: [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md); log: [agent.md](../../agent.md)).
Every number names its run directory under `results/runs/`. Main-study evidence in `results/final/` is unchanged and still
described in [RESULTS.md](RESULTS.md). All simulations ran on Modal CPU, all LLM calls on a Modal H100.

## 1. Product reliability

| Failure reported against the earlier prototype | Earlier prototype (run `…065958-11e4c20-product-failures`) | Current code (run `…071234-344bb16-product-failures`) |
|---|---|---|
| 200M, banking ≤ 25% | check "OK", post-fee weight 25.031% | 24.05% in a live app run; every register state ≤ 25% after fees (test) |
| Hold at most 1 stock | crash (`LinAlgError`) | decision by exact search, no circuit; 1 holding |
| Each stock ≤ 2% at 20M | crash (`ValueError`) | status infeasible: "2% of 20M = 399,400 VND < cheapest lot 1,135,000 VND" |
| Exclude every sector | crash | status infeasible: `empty_universe` |
| Vague instruction | question shown, trade list shown anyway | Run disabled until answered or skipped; API returns 409 |
| Swapped TE values in an explanation | accepted | rejected (`misattributed`), wrong unit rejected (`wrong_unit`) |

Test suite on Modal CPU: 39 passed after the fixes (`…071253-344bb16-pytest`), later runs listed in agent.md.
The attribution verifier gives the same verdict as the main study on all 12 archived live explanations (no new false alarm).

## 2. k-NN schedule selection (protocol §4)

Table: 690 instances × 1,080 schedules (`…071428-5f548ba-knn-table`); study: `…073008-ab60365-knn-study`;
refinement: the second `knn-refine` run. Holdout = 22 non-quarter months 2024–2026 × 5 account sizes × 3
constraint types; tests are paired by date.

| Arm (holdout, mean success) | % | vs frozen (pp, 95% CI, wins/22, p) |
|---|---|---|
| Oracle (best schedule per instance) | 17.80 | +3.21 |
| k-NN, original configuration (5 features, k = 10) | 15.63 | +1.05 [0.77, 1.31], 19/22, p < 0.001 |
| **k-NN selected on validation** (ext features, rank scaling, Manhattan, inverse weights, k = 3, fallback) | **15.34** | **+0.76 [0.37, 1.11], 20/22, p = 0.0002** |
| Frozen schedule per account size | 15.35 | +0.76 [0.54, 0.99], 22/22 |
| Frozen schedule (one for all) | 14.58 | — |
| Best of 108 random schedules (chosen on calibration) | 13.65 | |
| Best of 24 random schedules | 10.80 | |
| Random schedule from the grid | 4.72 | |
| Warm start only (no circuit layers) | 2.17 | |

- K2 (primary) holds; K3 holds (positive in 5/5 sizes and 3/3 constraint types); K4 (fallback non-inferior) holds.
- **The gain is the same as conditioning on account size**: selected k-NN vs per-size frozen −0.00 pp (p = 0.97).
  The original k-NN configuration beats the per-size rule by +0.28 pp (p = 0.025); the 4-date validation picked a
  variant that generalised slightly worse.
- K1 diagnosis: the top of the landscape is flat (best − 10th best 2.7 pp); every selector is optimistic in-sample
  by 6–7 pp (2023 H1 → H2 shift); feature distance only moderately predicts which schedules work (Spearman 0.32).
- **Why the main study reported k-NN below the frozen schedule**: the main-study comparison was k-NN + COBYLA polish (21.3%) vs frozen
  without polish (23.8%); the main study's own polish ablation (k-NN without polish, 24.0%) was level with frozen. The loss
  came from the polish on the main study's 100M trajectory accounts, not from the selection.
- Local refinement (40 COBYLA steps on CVaR 0.1), holdout: +1.34 pp on the frozen schedule, +1.03 pp on k-NN, almost
  entirely at 20M (5.7% → 10.5%); neutral or slightly negative at 100–200M; 41 circuit evaluations instead of 1
  (2.1 s vs 0.05 s per instance); feasible probability mass 0.82 → 0.77.

On the 12 test quarters (already reported in the main study, secondary): selected k-NN +0.56 pp vs frozen (p = 0.03),
original k-NN +1.30 pp (12/12), per-size frozen +0.88 pp.

## 3. Small-account benchmark and the price-level limitation (protocol §5)

Run `…073913-5c9f384-account-benchmark`, 12 test quarters, realised annualised tracking error vs VN30.
Historical traded prices and a corporate-actions file are not available, so the adjusted-price limitation is
bounded instead: understating every historical price by a factor f is the same problem as an account of 20M / f.

| Account (equivalent price understatement) | Nearest-lot rounding | Greedy lot filling | AGQO | Exact | AGQO − rounding (95% CI) | AGQO − greedy (95% CI) |
|---|---|---|---|---|---|---|
| 20M (none) | 12.14% | 7.47% | 6.77% | 6.77% | −5.37 [−6.93, −3.84] | −0.69 [−1.53, +0.02] |
| 18.2M (10%) | 12.01% | 8.85% | 6.74% | 6.76% | −5.27 [−6.75, −3.80] | −2.11 [−2.69, −1.64] |
| 16M (25%) | 12.45% | 9.32% | 7.53% | 7.53% | −4.92 [−6.61, −3.19] | −1.80 [−2.78, −0.96] |
| 13.3M (50%) | 13.27% | 10.61% | 8.36% | 8.36% | −4.92 [−6.74, −3.10] | −2.25 [−3.27, −1.46] |

- The current code reproduces the main-study 20M numbers exactly (12.143 / 7.468 / 6.774).
- The advantage over nearest-lot rounding stays near 5 pp across the bound; the advantage over the greedy
  heuristic is **not significant at 20M** (CI includes 0) but is at the smaller equivalent accounts.
- AGQO equals the exact whole-lot optimum in every row: the benefit comes from optimising the lot combination;
  the circuit finds the same answer that classical enumeration finds.
- Not quantified: stock-specific adjustment (for example banks that paid large stock dividends).

## 4. Product presets (protocol §6)

Run `…073818-5c9f384-presets`. Latest date = 2026-10-01 decision; 12-quarter realised tracking error with the
preset's rules.

| Preset | Outcome | Realised TE AGQO vs rounding (12 quarters) | Cost of the rules vs no rules | Violations |
|---|---|---|---|---|
| 20M, no rules | favourable | 6.77% vs 12.14% | — | 0 |
| 200M, banking ≤ 25% | favourable | 3.57% vs 4.34% (−0.77 [−1.22, −0.36]) | +1.07 pp | 0 |
| 100M, no real estate, no VIC/VHM/VRE | favourable (small) | 6.39% vs 6.63% (−0.24 [−0.49, −0.02]) | +3.43 pp | 0 |
| 500M, no rules | no clear difference | 2.47% vs 2.51% (CI includes 0) | — | 0 |
| 20M, hold 1 stock | no difference (exact search) | 16.19% vs 16.19% | +9.41 pp | 0 |
| 20M, each stock ≤ 2% | infeasible, rule named | — | — | — |
| Vague "đừng mua quá nhiều ngân hàng" | asks a question, no trades | — | — | — |

## 5. LLM experiment 1: Vietnamese instructions → constraints (protocol §3a)

Run `20261120-073653-2291b6a-llm-mandates`. Qwen3.8-27B-FP8 (revision `c3a462cc`, vLLM 0.32, H100, temperature 0,
JSON-schema decoding), 100 calls, 0 invalid answers, 80,318 input and 10,840 output tokens. 50 new Vietnamese
instructions written for the follow-up study (24 clear, 10 ambiguous, 8 conflicting, 8 infeasible at their account size).
**The set is team-written; these numbers do not replace a test with independent users.**

| Metric | Keyword rules | Qwen, first prompt | **Qwen, current English prompt** |
|---|---|---|---|
| End-to-end correct outcome | 66% (33/50) | 92% (46/50) | **98% (49/50)** |
| — clear (24) | 91.7% | 100% | 100% |
| — ambiguous (10): no trades until answered | 50% | 100% | 100% |
| — conflicting (8): no trades until resolved | 0% | 50% | 87.5% |
| — infeasible (8): blocked with the right rule | 75% | 100% | 100% |
| Exact constraints on clear items | 70.8% | 100% | 100% |
| Field accuracy (6 fields × 50) | 93.0% | 97.0% | 98.0% |
| Clarification recall / precision | 27.8% / 100% | 77.8% / 100% | 94.4% / 100% |
| Conflicts labelled as conflicts | — | — | 87.5% |
| Question quality (rubric 0–1) | 0.90 | 0.98 | 0.99 |

End-to-end means: the parsed rules went through the deterministic optimiser on Modal CPU and the outcome was judged
against the gold rules (trades audited on post-trade NAV for clear items; status infeasible with the right blocking
rule; no trade list for ambiguous and conflicting items). Primary test, current prompt vs keyword rules: 16 items only
current-prompt correct, 0 only keyword correct, exact McNemar p = 3·10⁻⁵. Current vs first prompt: 3 vs 0, p = 0.25 (not
significant). The single current-prompt miss is k05, "each stock ≤ 5%, at most 4 stocks, and invest all the money": the
contradiction needs arithmetic (4 × 5% = 20%); Qwen returned the two limits with status ok (and "0% cash" for "invest
all"), so the optimiser followed them and invested at most about 20%. One question had a doubled question mark ("??"), which the rubric counts against it.

## 6. LLM experiment 2: circuit design and optimisation (protocol §3b)

Run `20261120-074358-ef91bb6-llm-circuits`. English prompt with the problem specification, the allowed QAOA
components, budgets (≤ 1,500 two-qubit gates, ≤ 60 circuit evaluations per instance) and the objective; two rounds
of 8 structured candidates (temperature 0.4, JSON-schema decoding); round 2 saw round 1's scores. All 16
candidates passed validation (schema, `verify`, compiled gate count, evaluation budget). Control: random search
over the same space, 16 candidates per seed, 3 seeds. Design set: 24 calibration instances (8 dates × 20/100/500M).

| Circuit (holdout, 330 instances) | Success | Feasible mass | Evaluations | Two-qubit gates | Seconds / instance |
|---|---|---|---|---|---|
| frozen grid schedule (found by scoring 1,080 schedules) + 40 COBYLA steps | 15.31% | 0.77 | 41 | 1,440 | 2.0 |
| frozen grid schedule | 14.35% | 0.84 | 1 | 1,440 | 0.05 |
| **Best LLM candidate** (round 2: warm start, warm mixer, p = 4, max scaling, linear ramp, COBYLA 59 steps on CVaR 0.1) | **9.83%** | 0.81 | 59.7 | 960 | 2.1 |
| Best random-search candidate (3 seeds) | 2.62–3.91% | 0.71–0.78 | 34–52 | 7–1,302 | 1.3–2.7 |

- Primary (LLM vs budget-matched random search): +6.43 pp vs the mean of the three seeds, better on 22/22 holdout
  dates (exact one-sided Wilcoxon p ≈ 2·10⁻⁷). The LLM's structural choices (warm start with the aligned mixer,
  CVaR objective) carry most of that gain.
- Exploratory: the LLM candidate is far below the data-driven schedule, −4.53 pp vs the frozen grid schedule and
  −5.49 pp vs frozen + polish (0/22 dates), while using 60× more circuit evaluations than the frozen schedule. On
  the design set its rounds improved from 1.1% to 3.9%. Most candidates used "max" Hamiltonian scaling and none set a
  separate β ramp height (ramp_dbeta = 0 in all 16), whereas the grid fixes RMS scaling (rule R4) and tunes the γ and
  β ramp heights separately; this study does not isolate which of those differences matters.
- Conclusion: in this setting the LLM is a useful prior over circuit structure but not a substitute for scoring
  schedules on data. AGQO keeps the data-driven schedule.
