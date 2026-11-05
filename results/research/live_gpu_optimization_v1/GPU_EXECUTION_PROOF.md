# Actual GPU execution proof

- Modal app: agqo-live-optimizer; call `fc-01M6N1M0D678WSXN6DXG5ZRVM4`.
- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`, revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`; BF16/vLLM0.15.0.
- Device: NVIDIA A100-SXM4-80GB; real resident inference, not cached responses.
- Twelve normal model completions,12 admitted programs,127,641 input /7,257 output tokens.
- Four actual CUDA/NumPy selfchecks passed;64 circuit runs used complex128 CUDA evolution.
- Eighty-eight complete numerical runs;59,904 support observations;36,621 allocation queries.
- Independent audit rescored36,494 feasible allocations, maximum F residual1.63e-19.
- All359 downloaded hashes checked. Sixteen QPY/QASM exports parsed;8 small full-state checks passed,8 larger ones explicitly skipped under the16-physical-qubit cap. See EXPORT_AUDIT.json.
- Worker runtime1101.621s; model load132.732s; generation339.567s. Whole-worker GPU residency includes CPU work.
- Reserved USD3.64, not a provider invoice. Before/after snapshots are in orchestration/.
- Compilation, optimizer control, sampling RNG and CLARABEL allocation are CPU operations inside the GPU worker. This is ideal classical quantum simulation, not a quantum processor.

Exact requests, schemas, raw text, usage and round receipts are in evaluation/llm/.
The numerical claims are conditional training-objective comparisons, not investment returns.
