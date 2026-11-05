"""One bounded GPU worker: resident live LLM, CUDA simulation, verified finance."""

from pathlib import Path
import io
import json
import zipfile
import modal

app = modal.App("agqo-live-optimizer")
cache = modal.Volume.from_name("agqo-gate-models", create_if_missing=False)
results = modal.Volume.from_name("agqo-research-runs", create_if_missing=False)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "vllm==0.15.0", "jsonschema==4.26.0", "cvxpy==1.9.3",
        "scipy==1.18.1", "scikit-learn==1.9.1", "pandas==3.0.6",
        "qiskit==2.5.2", "qiskit-qasm3-import==0.6.0",
    )
    .env({"HF_HOME": "/model-cache/huggingface", "VLLM_LOGGING_LEVEL": "WARNING",
          "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn"})
    .add_local_python_source("agqo")
)


@app.function(image=image, gpu="A100-80GB", cpu=4, memory=98304,
              timeout=2400, startup_timeout=600, retries=0, max_containers=1,
              scaledown_window=2, volumes={"/model-cache": cache, "/runs": results})
def optimize(run_id, inputs):
    from time import perf_counter
    from importlib.metadata import version
    import torch
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    from agqo.synthesis.budget import MODEL_CATALOG
    from agqo.synthesis.decoding import decoder_schema
    from agqo.synthesis.profile import digest
    from agqo.research.gpu_optimization import run, RUN_ID
    from agqo.research.cuda_simulation import TorchConservedBasis
    from agqo.research.data import write_json, sha

    if run_id != RUN_ID or not torch.cuda.is_available():
        raise ValueError("Only the new bounded run and real CUDA are admitted.")
    root = Path("/runs") / run_id
    if root.exists():
        raise ValueError("Existing paid run retained; retrieve artifacts, do not redispatch.")
    # Controller source hashes cover the actual package deployed to this worker.
    package_root = Path(__import__("agqo").__file__).resolve().parent.parent
    for name, expected in inputs["live_protocol"]["package_source_hashes"].items():
        if sha(package_root / name) != expected:
            raise ValueError(f"Deployed source differs from prepared source: {name}")
    engine = None
    config = MODEL_CATALOG["coder30"]
    engine_seconds = None

    def generate(requests, round_index):
        nonlocal engine, engine_seconds
        if len(requests) != 4 or round_index not in (0, 1, 2):
            raise ValueError("Only three live batches of four requests are authorized.")
        if engine is None:
            started = perf_counter()
            print(json.dumps({"stage": "loading_model", "model": config["model"], "revision": config["revision"]}), flush=True)
            engine = LLM(model=config["model"], revision=config["revision"], dtype="bfloat16",
                         max_model_len=16384, gpu_memory_utilization=0.88,
                         max_num_seqs=2, enforce_eager=True, enable_prefix_caching=False,
                         trust_remote_code=False)
            engine_seconds = perf_counter()-started
            print(json.dumps({"stage": "engine_ready", "seconds": engine_seconds}), flush=True)
        tokenizer = engine.get_tokenizer()
        messages, params, lengths = [], [], []
        for request in requests:
            if request["request_hash"] != digest({k: v for k, v in request.items() if k != "request_hash"}):
                raise ValueError("Live prompt changed.")
            chat = [{"role": "system", "content": request["system"]},
                    {"role": "user", "content": json.dumps(request["payload"], ensure_ascii=False)}]
            count = len(tokenizer.apply_chat_template(chat, add_generation_prompt=True, tokenize=True))
            if count + request["max_tokens"] > 16384:
                raise ValueError("Actual prompt exceeds context; no silent truncation.")
            messages.append(chat)
            lengths.append(count)
            params.append(SamplingParams(temperature=request["temperature"], top_p=0.9,
                seed=request["seed"], max_tokens=request["max_tokens"],
                structured_outputs=StructuredOutputsParams(json=decoder_schema(request["schema"]))))
        started = perf_counter()
        print(json.dumps({"stage": "live_inference", "round": round_index, "prompt_tokens": lengths}), flush=True)
        outputs = engine.chat(messages, sampling_params=params, use_tqdm=False)
        answers = []
        for request, output, count in zip(requests, outputs, lengths, strict=True):
            completion = output.outputs[0]
            try:
                value = json.loads(completion.text)
                status = "ok" if completion.finish_reason == "stop" else "truncated"
            except json.JSONDecodeError:
                value, status = None, "invalid_json"
            answers.append({"request_hash": request["request_hash"], "status": status,
                "response": value, "raw_text": completion.text, "finish_reason": completion.finish_reason,
                "usage": {"input_tokens": count, "output_tokens": len(completion.token_ids)},
                "model": config["model"], "revision": config["revision"], "execution": "live_modal_vllm"})
        runtime = {"model": config["model"], "revision": config["revision"], "gpu": torch.cuda.get_device_name(),
            "vllm_version": version("vllm"), "torch_version": version("torch"),
            "generation_seconds": perf_counter()-started, "model_load_seconds": engine_seconds,
            "round_index": round_index, "execution": "live_modal_gpu_not_replay",
            "model_load_count": 1, "quantum_hardware": False}
        return answers, runtime

    try:
        summary = run(root, inputs, generate, TorchConservedBasis, checkpoint=results.commit)
        write_json(root / "runtime_packages.json", {p: version(p) for p in ("vllm", "torch", "numpy", "scipy", "cvxpy", "clarabel", "qiskit", "scikit-learn")})
        source = root / "source_snapshot"
        for name in inputs["live_protocol"]["package_source_hashes"]:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((package_root / name).read_bytes())
        files = sorted(p for p in root.rglob("*") if p.is_file())
        hashes = {str(p.relative_to(root)): sha(p) for p in files}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in files:
                archive.write(p, str(p.relative_to(root)))
        return {"summary": summary, "sha256_files": hashes, "archive": stream.getvalue()}
    except Exception as exc:
        write_json(root / "FAILED.json", {"reason": f"{type(exc).__name__}: {exc}", "no_automatic_retry": True})
        raise
    finally:
        cache.commit()
        results.commit()
