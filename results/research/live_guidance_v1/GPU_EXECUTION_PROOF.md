# Actual GPU execution

Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`. Revision: `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`.

GPU reported by worker: **NVIDIA A100-SXM4-80GB**. Engine: vLLM0.15.0. Execution: `live_modal_vllm`. Batch size: 8.

Worker elapsed time including model setup: 278.725s. Client-observed batch time including RPC/queue overhead: 287.181s.

Function call: `fc-01M6K6HDDEC06TY8VGE1JKMS0A`.

All eight responses stopped normally. Input tokens: 77,758; output tokens: 7,581.

[Original GPU receipt](orchestration/inference/145c98a5aa9d4f229e56d8966b638ce0_receipt.json) · [Exact outputs](ACTUAL_RESPONSES.md) · [Raw per-request answers](orchestration/answers.json).

GPU inference generates circuit programs. CPU verification, QAOA simulation and continuous portfolio allocation are separate stages. No quantum processor was used.

The first CPU evaluator failed an exact canonical hash check. Its failure is retained and a separately registered CPU-only numerical-transport recovery reuses these exact model outputs. No GPU inference was repeated.
