# Plan: the final 48 hours

Owner: solo. Start: 14 Nov 2026, 00:40 (Asia/Ho_Chi_Minh). Every step has a command, an
output that proves it is done, and a fallback. Record each finished step in
[CHECKPOINTS.md](CHECKPOINTS.md).

```mermaid
gantt
    dateFormat  YYYY-MM-DD HH:mm
    axisFormat  %d %b %H:%M
    section Day 1 — build and measure
    CP1 Rebuild codebase (done)                 :done, cp1, 2026-11-14 00:40, 45m
    CP2 Baseline run, no LLM (done)             :done, cp2, after cp1, 20m
    CP3 Modal deploy + smoke test               :cp3, 2026-11-14 09:00, 1h
    CP4 Live LLM run (coder30, 3 samples)       :cp4, after cp3, 2h
    CP5 Second model (instruct30) ablation      :cp5, after cp4, 2h
    CP6 Regenerate report, read results         :cp6, after cp5, 1h
    section Day 2 — prove and present
    CP7 IBM hardware sample (optional)          :cp7, 2026-11-15 08:00, 2h
    CP8 Slides from README figures              :cp8, after cp7, 4h
    CP9 Rehearse defence questions              :cp9, after cp8, 2h
    CP10 Freeze: tag release                    :milestone, cp10, after cp9, 0h
```

| CP | What | Command | Done when | Fallback |
|---|---|---|---|---|
| 1 | New LLM-core codebase, tests | `pytest -q` | 9 tests pass | — |
| 2 | Baseline (no LLM) | `python -m agqo run --out results/baseline` | `results/baseline/run_manifest.json` exists | — |
| 3 | Modal live model | `modal deploy modal_app.py`, `python -m agqo smoke-llm` | `"execution": "live_modal_vllm"` | `--model qwen8b`; or any OpenAI-compatible API |
| 4 | Full LLM experiment | `python -m agqo run --llm modal --model coder30 --samples 3 --out results/llm_coder30` | `llm_log.jsonl` has 50 records, all `ok` or repaired | reduce `--samples 1` |
| 5 | Model ablation | same with `--model instruct30 --out results/llm_instruct30` | second run present | skip; report one model |
| 6 | Report | `python -m agqo report --runs results/baseline results/llm_coder30` | `docs/RESULTS.md` shows LLM sections | — |
| 7 | Hardware | `python -m agqo hardware --qasm results/llm_coder30/circuits/llm_*.qasm --confirm` | `results/hardware_run.json` with counts | present the dry-run resource report |
| 8 | Slides | README figures 01→09 in order | 10–12 slides | README itself |
| 9 | Defence prep | answer the questions below out loud | — | — |

## Decision rules (set before seeing the LLM results)

* **LLM architect claim** holds only if its frozen design beats *both* random search and
  classical evolution on the 11 unseen quarters (mean success probability). Otherwise
  report "LLM matches search with fewer evaluations" or a negative result, honestly.
* **LLM analyst claim** holds only if "LLM analyst → exact" has lower realised tracking
  error than "Greedy-TE top-8 → exact". Otherwise its value is the explanation layer
  (regime, rationale), not tracking quality.
* **Quantum claim** is limited to: exact formulation, verified circuits, design quality vs
  random guessing, hardware-executable export. No speed-up claim.

## Questions judges will ask

1. *Why quantum if enumeration solves 16 qubits instantly?* — The register grows as
   assets × bits; 30 stocks × 3 bits = 90 qubits (2⁹⁰ portfolios). We show the method,
   the exact formulation and transferable circuit designs at a size where we can still
   verify against ground truth.
2. *Does the LLM just memorise history?* — Tickers and dates are anonymised; all features
   are computed by code; every prompt/answer is logged.
3. *What if the LLM is wrong?* — It cannot change the financial objective; every output is
   schema-checked, repaired with a logged rule and verified before use. A classical
   fallback always exists.
4. *Is the backtest realistic?* — Whole lots, commission, sale tax, quarterly rebalance,
   point-in-time membership, separate accounts per strategy; limitations listed in
   METHODS §7.
