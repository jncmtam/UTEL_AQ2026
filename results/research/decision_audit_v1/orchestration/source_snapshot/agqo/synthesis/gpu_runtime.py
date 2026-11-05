"""Pinned real single-batch generation; no replay or fabricated responses."""

import json
from time import perf_counter


def generate_coder30(requests):
    import torch
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    from .budget import MODEL_CATALOG
    from .decoding import decoder_schema
    from .profile import digest

    if not torch.cuda.is_available() or len(requests) != 4:
        raise ValueError("Four live requests and actual CUDA are required.")
    c = MODEL_CATALOG["coder30"]
    started = perf_counter()
    print(json.dumps({"stage": "loading_model", "model": c["model"], "revision": c["revision"]}), flush=True)
    engine = LLM(model=c["model"], revision=c["revision"], dtype="bfloat16",
                 max_model_len=16384, gpu_memory_utilization=.88, max_num_seqs=2,
                 enforce_eager=True, enable_prefix_caching=False, trust_remote_code=False)
    load_seconds = perf_counter()-started
    tokenizer = engine.get_tokenizer()
    messages, params, counts = [], [], []
    for request in requests:
        if request["request_hash"] != digest({k: v for k, v in request.items() if k != "request_hash"}):
            raise ValueError("Prepared live request changed.")
        chat = [{"role": "system", "content": request["system"]},
                {"role": "user", "content": json.dumps(request["payload"], ensure_ascii=False)}]
        count = len(tokenizer.apply_chat_template(chat, tokenize=True, add_generation_prompt=True))
        if count+request["max_tokens"] > 16384:
            raise ValueError(f"Prompt {count}+output exceeds16K; no truncation.")
        counts.append(count)
        messages.append(chat)
        params.append(SamplingParams(temperature=.6, top_p=.9, seed=request["seed"], max_tokens=request["max_tokens"], structured_outputs=StructuredOutputsParams(json=decoder_schema(request["schema"]))))
    print(json.dumps({"stage": "live_inference", "prompt_tokens": counts}), flush=True)
    start = perf_counter()
    outputs = engine.chat(messages, sampling_params=params, use_tqdm=False)
    answers = []
    for request, output, count in zip(requests, outputs, counts, strict=True):
        completion = output.outputs[0]
        try:
            value = json.loads(completion.text)
            status = "ok" if completion.finish_reason == "stop" else "truncated"
        except json.JSONDecodeError:
            value, status = None, "invalid_json"
        answers.append({"request_hash": request["request_hash"], "status": status,
            "response": value, "raw_text": completion.text, "finish_reason": completion.finish_reason,
            "usage": {"input_tokens": count, "output_tokens": len(completion.token_ids)},
            "model": c["model"], "revision": c["revision"], "execution": "live_modal_vllm"})
    return answers, {"model": c["model"], "revision": c["revision"], "gpu": torch.cuda.get_device_name(),
        "execution": "live_modal_gpu_not_replay", "model_load_seconds": load_seconds,
        "generation_seconds": perf_counter()-start, "vllm_version": vllm.__version__,
        "torch_version": torch.__version__, "quantum_hardware": False}
