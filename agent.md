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

## Open questions and decisions

- **Historical traded prices.** The only price series available is the provider's back-adjusted series. The
  file labelled `vn30_provisional_raw_20261114` in the old `pipeline-modal` worktree is identical to the
  adjusted series (ACB 2022-01-04 close 13,900 in both; ACB traded near 33,000 then), so it is not raw data.
  Decision: quantify the limitation (see protocol §5) instead of guessing corporate actions. Obtaining a
  corporate-actions file (dividends, splits, ex-dates) is the prerequisite for a real rerun; licensing is the
  owner's call.
- **Submitted prototype.** `agqo-web` (label `agqo-demo`) is the URL already handed to the organisers. V3.2 is
  deployed under a separate label so the submitted URL keeps working until the owner decides to switch.
