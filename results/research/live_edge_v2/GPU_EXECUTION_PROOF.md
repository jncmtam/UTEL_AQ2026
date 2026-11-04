# Actual GPU execution

Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`. Revision: `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`.

Worker GPU: **NVIDIA A100-SXM4-80GB**. Engine vLLM0.15.0. Execution: `live_modal_vllm`. Batch size:8.

Worker wall time including setup: 407.669s; client-observed batch time including queue/RPC: 420.272s.

Function call: `fc-01M6K8232X70FADT178C1HEWJV`. All eight responses stopped normally. Input tokens:76,782; output tokens:4,870.

[Original GPU receipt](orchestration/inference/9d87ed2a1a26410391e130497d0391f0_receipt.json) · [Raw answers](orchestration/answers.json) · [Exact readable outputs](ACTUAL_RESPONSES.md).

GPU generates the model output. Subsequent QAOA simulation and financial allocation run on Modal CPU. No quantum hardware was used. Device free-memory snapshots are not peak engine VRAM measurements. No third inference batch is scheduled.
