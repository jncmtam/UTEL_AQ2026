# Checkpoints

A running log. Each entry: what was done, the evidence, and what it means. Newest last.

| CP | Date (ICT) | Done | Evidence |
|---|---|---|---|
| 0 | 14 Nov 00:45 | v1 archived on git branch `archive/agqo-v1-research`; work continues on `v2/llm-core` | `git branch -a` |
| 1 | 14 Nov 01:25 | New LLM-core codebase (~20 files): data, features, exact lot QUBO, verifier, simulator, Qiskit export, LLM analyst + architect, backtest, report | `pytest -q` → 16 passed |
| 2 | 14 Nov 01:35 | Baseline run without LLM (controls: default, random search, classical evolution) | `results/baseline/`, `docs/RESULTS.md`, figures 01–08 |
| 3 | – | Modal deploy + smoke test | `results/smoke/llm_log.jsonl` with `execution: live_modal_vllm` |
| 4 | – | Live LLM run (coder30) | `results/llm_coder30/llm_log.jsonl`, regenerated RESULTS.md |
| 5 | – | Model ablation (instruct30 or qwen8b) | second run directory |
| 6 | – | IBM hardware sample (optional) | `results/hardware_run.json` |
| 7 | – | Slides + rehearsal | – |

## CP1 — design decisions

* **Task changed from 8-stock selection to whole-lot rounding of the full universe.** The fair
  practitioner baseline (continuous QP over ~25 members, nearest-lot rounding) tracked VN30 at
  2.8 % TE, whereas the best 8-stock basket reached 5.6 %. Restricting the register to 8 stocks
  would have handicapped the product. The 8-stock basket remains as a secondary mandate mode,
  where the LLM analyst picks the basket.
* **Penalty calibration.** λ = 0.005, target invested 98 %: on the 2023–Q2 2024 quarters the QUBO
  minimum then coincides with the exact constrained optimum (gap 0.002). This is a fixed compiler
  setting, not tuned on test quarters.
* **Covariance.** Joint [assets, index] covariance shrunk 5 % towards its diagonal. Shrinking only
  the asset block produced negative TE² (caught by a test).
* **Practitioner baseline made fair.** Floor rounding left 36 % cash (a straw man). It was replaced
  by nearest-lot rounding with a budget trim.

## CP2 — baseline findings

* Design search: textbook QAOA 0.16 % → best searched design 2.68 % training success (17×).
* Transfer: frozen designs keep 3.6 % per-shot success on 11 unseen quarters (80× random guessing).
* Alignment matters: warm_start + warm_x averages 1.53 % vs 0.12 % for the uniform/X family.
* Finance: exact or QAOA rounding 2.71–2.75 % realised TE vs 2.82 % practitioner rounding. The edge
  is small and noisy; the ex-ante improvement is 11 bp.
* Simulated annealing also finds the optimum at 16 qubits, so no quantum advantage is claimed.
