"""Pinned, self-hosted vLLM batch workers. No public or per-token shared endpoint."""
from __future__ import annotations

import json
import time
import modal

app = modal.App("agqo-gate-synthesis")
cache = modal.Volume.from_name("agqo-gate-models", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .uv_pip_install("vllm==0.15.0", "jsonschema==4.26.0")
         .env({"HF_HOME": "/model-cache/huggingface", "VLLM_LOGGING_LEVEL": "WARNING"})
         .add_local_python_source("agqo"))
modern_image = (modal.Image.debian_slim(python_version='3.12')
                .uv_pip_install('vllm==0.17.1','jsonschema==4.26.0')
                .env({'HF_HOME':'/model-cache/huggingface','VLLM_LOGGING_LEVEL':'WARNING'})
                .add_local_python_source('agqo'))


def generate(model_key, requests):
    start = time.monotonic()
    maximum=32 if model_key in {'coder480','qwen397'} else 8
    if not isinstance(requests, list) or not 1 <= len(requests) <= maximum:
        raise ValueError(f"Batch must have 1–{maximum} requests.")
    from agqo.synthesis.budget import MODEL_CATALOG
    from agqo.synthesis.decoding import decoder_schema
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    import torch
    config = MODEL_CATALOG[model_key]
    print(json.dumps({"stage": "loading_model", "model": config["model"], "revision": config["revision"], "requests": len(requests)}), flush=True)
    engine = LLM(model=config["model"], revision=config["revision"], dtype=config["dtype"],
                 tensor_parallel_size=config.get('tensor_parallel_size',1), max_model_len=16384,
                 gpu_memory_utilization=0.90 if model_key in {'coder480','qwen397'} else 0.88,
                 max_num_seqs=2, enforce_eager=True, enable_prefix_caching=False,
                 trust_remote_code=False)
    print(json.dumps({"stage": "engine_ready", "seconds": time.monotonic() - start}), flush=True)
    tokenizer = engine.get_tokenizer()
    messages, params, prompt_lengths = [], [], []
    for request in requests:
        chat = [{"role": "system", "content": request["system"]},
                {"role": "user", "content": json.dumps(request["payload"], ensure_ascii=False)}]
        chat_kwargs={'enable_thinking':False} if model_key=='qwen397' else {}
        count = len(tokenizer.apply_chat_template(chat, add_generation_prompt=True, tokenize=True,**chat_kwargs))
        if count + request["max_tokens"] > 16384:
            raise ValueError(f"Prompt length {count} plus output budget exceeds 16K; no silent data truncation.")
        messages.append(chat); prompt_lengths.append(count)
        params.append(SamplingParams(temperature=request.get("temperature", 0.4), top_p=0.9,
                                     seed=request["seed"], max_tokens=request["max_tokens"],
                                     structured_outputs=StructuredOutputsParams(json=decoder_schema(request["schema"]))))
    print(json.dumps({"stage": "generating", "prompt_tokens": prompt_lengths}), flush=True)
    outputs = engine.chat(messages, sampling_params=params, use_tqdm=False,
                          **({'chat_template_kwargs':{'enable_thinking':False}} if model_key=='qwen397' else {}))
    answers = []
    for request, output, count in zip(requests, outputs, prompt_lengths, strict=True):
        completion = output.outputs[0]
        try:
            value = json.loads(completion.text)
            status = "ok" if completion.finish_reason == "stop" else "truncated"
        except json.JSONDecodeError:
            value, status = None, "invalid_json"
        answers.append({"request_hash": request["request_hash"], "status": status, "response": value,
                        "raw_text": completion.text, "finish_reason": completion.finish_reason,
                        "usage": {"input_tokens": count, "output_tokens": len(completion.token_ids)}})
    print(json.dumps({"stage": "generation_done", "seconds": time.monotonic() - start,
                      "statuses": [a["status"] for a in answers]}), flush=True)
    cache.commit()
    import vllm
    return {"model": config["model"], "revision": config["revision"], "model_key": model_key,
            "answers": answers, "execution": "live_modal_vllm", "vllm_version": vllm.__version__,
            "elapsed_seconds": time.monotonic() - start, "runtime_adapter": "uniqueItems_checked_by_independent_validator_v1",
            "gpu": torch.cuda.get_device_name(),
            # vLLM engine owns allocations in a child process. The parent's
            # allocator peak can be zero and must not be reported as model VRAM.
            "parent_process_cuda_peak_bytes_not_model_vram": torch.cuda.max_memory_allocated(),
            "gpu_memory_measurement": "device_free_snapshot_not_engine_peak",
            "gpu_memory_total_bytes": torch.cuda.get_device_properties(0).total_memory,
            "gpu_memory_free_bytes": torch.cuda.mem_get_info()[0], "batch_size": len(requests)}


@app.function(image=image, gpu="H200", cpu=4, memory=131072, timeout=900,
              startup_timeout=600, retries=0, max_containers=1, scaledown_window=2,
              volumes={"/model-cache": cache})
def next80_batch(requests):
    return generate("next80", requests)


@app.function(image=image, gpu="A100-80GB", cpu=4, memory=98304, timeout=900,
              startup_timeout=600, retries=0, max_containers=1, scaledown_window=2,
              volumes={"/model-cache": cache})
def coder30_batch(requests):
    return generate("coder30", requests)


@app.function(image=image,gpu='H200:4',cpu=16,memory=393216,timeout=1800,
              startup_timeout=900,retries=0,max_containers=1,scaledown_window=2,
              volumes={'/model-cache':cache})
def coder480_batch(requests):
    return generate('coder480',requests)


@app.function(image=modern_image,gpu='H200:4',cpu=16,memory=393216,timeout=1800,
              startup_timeout=900,retries=0,max_containers=1,scaledown_window=2,
              volumes={'/model-cache':cache})
def qwen397_batch(requests):
    return generate('qwen397',requests)


@app.function(image=image, cpu=4, memory=16384, timeout=2400, startup_timeout=180,
              retries=0, max_containers=1, scaledown_window=2, volumes={"/model-cache": cache})
def prefetch_model(model_key):
    """Download public pinned weights on CPU, before paying to load them on GPU."""
    from pathlib import Path
    from huggingface_hub import snapshot_download
    from agqo.synthesis.budget import MODEL_CATALOG
    config=MODEL_CATALOG[model_key]
    start=time.monotonic()
    location=snapshot_download(config['model'],revision=config['revision'],
                               allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.jinja'],max_workers=8)
    cache.commit()
    return {'model':config['model'],'revision':config['revision'],'seconds':time.monotonic()-start,
            'weight_bytes':sum(p.stat().st_size for p in Path(location).rglob('*.safetensors')),
            'execution':'cpu_prefetch_not_inference'}
