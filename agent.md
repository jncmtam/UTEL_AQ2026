# AGQO V3.2 — agent progress log

English working log for the V3.2 work that starts from `v3.1.0` (`main` at `11e4c20`). Newest entries at the
bottom of each section. Every result named here has a run directory under `results/runs/<run_id>/` with a
`run.json` manifest (git revision, data SHA-256, config, status, errors).

## Ground rules for this work

- Quantum simulation, benchmark reruns and the test suite run on **Modal CPU** (`modal_research.py`), driven
  by `notebooks/AGQO_V3_2_Research_Modal.ipynb` (executed with papermill from the repo root; the kernel only
  submits work). Live LLM work runs on the existing **Modal H100** app `agqo-llm` (`modal_app.py`).
- Pure-Python checks that do not simulate circuits (parsers, verifiers, accounting helpers) may run locally.
- Archived V3 evidence in `results/final/` is not modified. New runs go to `results/runs/` (local copy) and the
  Modal Volume `agqo-v32-runs` (remote copy). Failed and partial runs are kept.
- Deterministic code owns feasibility and final trade quantities. The LLM only fills constraint fields and
  writes explanations that a verifier checks.

## Environment

- Python venv: `AI-Quantum Challenge 2026/.venv` (Python 3.12, modal 1.6.2, qiskit 2.5.2). Added `papermill`,
  `ipykernel`, `nbformat` to run the notebook; kernel name `agqo-venv`.
- Modal workspace `data1` (profile `data1`). Existing apps: `agqo-web` (submitted Round-2 prototype,
  label `agqo-demo`), `agqo-llm` (Qwen3.8-27B-FP8, vLLM 0.32, H100). New app: `agqo-research` (CPU).
- Price snapshot: `data/vn30/ohlcv_daily.csv` copied from the main checkout (git-ignored), SHA-256
  `7f076128…3042`, matches `data/vn30/manifest.json` and `results/final/run_manifest.json`.

## Log

### 2026-11-20 — Step 1: reproduce the product failures (V3.1 code, Modal CPU)

What: added the research harness (`agqo/research/{runlog,orchestrate,repro}.py`, `modal_research.py`,
`notebooks/build_notebook.py` → `AGQO_V3_2_Research_Modal.ipynb`) without touching product code, then ran
`papermill … -p TASKS '["smoke","reproduce"]'`.

Runs: `20261120-065949-11e4c20-smoke` (image + data hash ok), `20261120-065958-11e4c20-product-failures`.

The reproduction audits each decision independently on the **post-trade NAV** (cash after fees + holdings).

| Case | V3.1 behaviour | Root cause |
|---|---|---|
| 200M, banking ≤ 25% | app check says OK; post-fee banking weight **25.031%** | `Instance.feasible` and `Demo.decide` divide by the pre-trade NAV; fees shrink the post-trade NAV by ~0.15% |
| Hold at most 1 stock (20M, 100M) | crash `LinAlgError: 0-dimensional array` | `market_insight` builds a correlation matrix of one stock; the QAOA path also assumes ≥ 2 qubits |
| 20M, each stock ≤ 2% | crash `ValueError` in `relaxed_solution` | no stock fits one lot under the cap → empty register (0 qubits) |
| 50M, exclude every sector | crash in `shrunk_covariance` | empty universe after exclusions; no infeasibility message |
| Vague instruction ("Đừng mua quá nhiều cổ phiếu ngân hàng") | Qwen asks a question, but `app.js run()` still calls `decideAndShow` and shows the unconstrained trade list | front-end flow ignores `needs_clarification` |
| Explanation with TE values of AGQO and nearest-lot rounding swapped | verifier `ok: true` | `verify_explanation` only checks that each number exists somewhere in the evidence |
| Explanation with a percentage written as "lô" | verifier `ok: true` | no unit check |

Cases that passed the audit: 20M and 500M with banking ≤ 25% (post-fee 22.68%, 24.92%), each stock ≤ 10%,
10% cash (post-fee cash 10.16%), 2 stocks, 5M without rules.

Also noticed: with `max_weight_per_stock` the app lists one check row per stock (30 rows); the check list
should aggregate to one row ("largest single stock").

### 2026-11-20 — Evaluation protocol

Written before any new holdout result was computed: `docs/research/PROTOCOL_V3_2.md`.

### 2026-11-20 — Step 2: product fixes (commit `344bb16`)

- `Instance.fees / post_trade_nav / post_trade_weights`; `feasible` checks caps on post-trade NAV (tolerance 1e-12).
- `backtest.fee_margin`: construction caps = investor cap × (1 − margin) (commission for a cash account,
  2·commission + sales tax with holdings), so all 2^n register states still obey sector and per-stock caps after
  fees. The cash floor stays an exact per-sample check (not cap-safe by construction; test documents this).
- `agqo/feasibility.py`: deterministic pre-solve diagnosis with codes `empty_universe`, `no_affordable_lot`,
  `per_stock_cap_below_one_lot`, `rules_leave_nothing`, `no_feasible_lot_combination` (blocking) and
  `exclusion_overrides_cap`, `sector_cap_below_one_lot`, `per_stock_cap_excludes`, `max_holdings_binds` (notes),
  each with an English and a Vietnamese message.
- `Demo.decide` returns `status` ok | infeasible; registers with < 2 qubits skip QAOA (`quantum.ran = false`,
  exact search); checks are rebuilt from the mandate on post-trade NAV (one row for the per-stock limit).
- Keyword fallback asks for clarification on vague limits (`mandate.rule_clarification`).
- Explanation verifier: `agqo/llm/attribution.py` turns the evidence into facts (value, unit, metric, entity) and
  checks, per clause, that a number is attached to the right strategy/metric and has the right unit. It catches
  the swapped AGQO/rounding values and wrong units; verdicts on the 12 archived V3 explanations are unchanged.
- Runs: `20261120-071253-344bb16-pytest` (39 passed on Modal CPU), `20261120-071234-344bb16-product-failures`
  (0 exceptions, 0 silent cap breaches, 2 infeasible with reason, verifier rejects the swap). The reported case now
  ends at 24.05% banking on post-fee NAV in a live app run.

### 2026-11-20 — Step 3: interactive app (commit `607c888`, Modal app `agqo-web-v32`)

- Page flow: presets (`agqo/presets.py`) or Vietnamese text → structured, editable constraint fields with a
  provenance badge each (Bạn nhập / Từ mẫu / Từ câu lệnh / Chưa đặt + default) → Run.
- Run = `POST /api/run` → `decide_job.spawn` in its own Modal CPU container; stages written to the Modal Dict
  `agqo-v32-progress`; `GET /api/run/{id}` polls; errors show a retry button. Results are labelled
  live Modal / replay of a saved Modal run / in-process fallback (fallback only with AGQO_ALLOW_LOCAL_COMPUTE=1).
- A pending clarification disables Run in the page and the API returns 409.
- Verified in the browser (desktop and 375 px): 200M banking ≤ 25% (live, 10.9 s, 24.05%), infeasible preset
  (blocking message shown, no trades), vague preset (question, Run disabled, answer → cap filled from text),
  one-stock preset (exact search, no circuit), exclusions preset.
- URL: https://data1--agqo-v32.us-east.modal.run (the Round-2 URL `agqo-demo` is unchanged).

### 2026-11-20 — Step 4: k-NN study (protocol §4)

- Table run `20261120-071428-5f548ba-knn-table`: 690 instances × 1,080 schedules, 0 errors, 7.2 CPU-hours on Modal
  in about 6 minutes (first attempt `…071346…` failed: Modal refuses `Function.map` iteration inside Jupyter's
  event loop; fixed with a worker thread).
- Study run `20261120-073008-ab60365-knn-study` (the earlier `…072848…` run reported K2 without the selected
  variant's fallback; protocol §8 records the fix).
- **K1 diagnosis.** The top of the schedule landscape is flat (best − 10th best = 2.7 pp; ~9.5 schedules within
  90% of the best). Every selector is optimistic in-sample by ~6–7 pp because 2023 H2 differs from 2023 H1;
  feature distance correlates only moderately with schedule-profile dissimilarity (Spearman 0.32). In V3 the
  loss "k-NN + polish 21.3% vs frozen 23.8%" came from the COBYLA polish, not the selection: V3's own
  `polish_ablation` arm (k-NN without polish) scored 24.0% vs frozen 23.8%.
- **K2 (primary, holdout 22 dates × 15 instances).** Selected variant `ext/rank/manhattan/inverse/k=3/mean/
  fallback`: 15.34% vs frozen 14.58%, +0.76 pp [0.37, 1.11], 20/22 dates, Wilcoxon p = 0.0002. K3 persists (5/5
  sizes, 3/3 constraint types). K4 fallback non-inferior.
- **But** a per-account-size frozen schedule (no k-NN) gets the same +0.76 pp (k-NN vs stratum frozen −0.00 pp,
  p = 0.97). The V3 k-NN configuration is best on holdout (+1.05 pp vs frozen, +0.28 pp vs stratum, p = 0.025):
  validation with 4 dates chose a variant that generalised slightly worse. Oracle 17.8%: about 3.2 pp headroom.
- **Refinement ablation** `20261120-…-knn-refine` (second run; the first was partial: `verify` capped depth at 6
  while the grid uses 8 layers, fixed): 40 COBYLA steps add +1.34 pp to frozen and +1.03 pp to k-NN, almost all at
  20M (5.7% → 10.5%); neutral or slightly negative at 100–200M; cost 41 evaluations instead of 1 (2.1 s vs 0.05 s
  per instance); feasible mass drops 0.82 → 0.77. k-NN+polish vs frozen+polish +0.45 pp (p = 0.054).
- Conclusion for the product: the gain from k-NN is real on a diverse instance pool but equals a simpler
  "schedule per account size" rule; polish helps small accounts and costs 40× more simulation.

## Open questions and decisions

- **Historical traded prices.** The only price series available is the provider's back-adjusted series. The
  file labelled `vn30_provisional_raw_20261114` in the old `pipeline-modal` worktree is identical to the
  adjusted series (ACB 2022-01-04 close 13,900 in both; ACB traded near 33,000 then), so it is not raw data.
  Decision: quantify the limitation (see protocol §5) instead of guessing corporate actions. Obtaining a
  corporate-actions file (dividends, splits, ex-dates) is the prerequisite for a real rerun; licensing is the
  owner's call.
- **Submitted prototype.** `agqo-web` (label `agqo-demo`) is the URL already handed to the organisers. V3.2 is
  deployed under a separate label so the submitted URL keeps working until the owner decides to switch.
