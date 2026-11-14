# Running the live LLM on Modal

The LLM runs as a Modal GPU class (`modal_app.py`) serving Qwen3 through vLLM with
**JSON-schema constrained decoding**, so every answer parses. The experiment calls it in
batches; the container stays warm for 10 minutes between batches, so the model loads
once per experiment.

## One-time setup (on your Mac)

```bash
cd "AI-Quantum Challenge 2026"
python3 -m venv .venv && source .venv/bin/activate     # or reuse the existing .venv
pip install -e '.[quantum,llm,dev]'
modal setup                                             # browser login, stores your token
modal deploy modal_app.py                               # builds the vLLM image once
```

The volume `agqo-gate-models` already holds Qwen3-Coder-30B weights from the v1 runs,
so `coder30` starts fastest. Other models download on first use.

## Smoke test (≈ 3–6 min cold start, < 1 min warm)

```bash
python -m agqo smoke-llm --llm modal --model coder30
```

Expected: `"status": "ok"`, `"execution": "live_modal_vllm"`, a parsed JSON answer.

## Full experiment

```bash
python -m agqo run --llm modal --model coder30 --samples 3 --out results/llm_coder30
python -m agqo report --runs results/baseline results/llm_coder30
```

* `--samples 3` asks the analyst three times per quarter (different seeds) and uses
  majority vote + agreement-weighted confidence (self-consistency).
* LLM calls: 1 batch of 15 × samples analyst requests + 4 architect rounds = 5 remote calls.
* Everything sent and received is in `results/llm_coder30/llm_log.jsonl`.
* Replay without GPU cost: `python -m agqo run --llm replay --replay results/llm_coder30/llm_log.jsonl --out results/replay`.

## Choosing the model

| key | model | why |
|---|---|---|
| `coder30` | Qwen3-Coder-30B-A3B-Instruct (pinned revision) | cached, proven on this account, strong at structured JSON |
| `instruct30` | Qwen3-30B-A3B-Instruct-2507 | general reasoning; better candidate for market analysis |
| `qwen8b` | Qwen3-8B (pinned) | cheap ablation: does a small model do as well? |

Compare models by running the experiment once per key and putting all runs in the report.
Pick on test-quarter results, never on parameter count.

## Cost control

* One A100-80GB; `max_containers=1`; idle shutdown after 10 minutes (`scaledown_window`).
* Check live usage in the Modal dashboard; stop with `modal app stop agqo-llm-core`.

## Other endpoints

Any OpenAI-compatible server works (vLLM elsewhere, a hosted API):

```bash
export AGQO_OPENAI_BASE_URL=https://.../v1 AGQO_OPENAI_API_KEY=...
python -m agqo run --llm openai --model <model-name> --out results/llm_api
```
