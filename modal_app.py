"""Modal GPU app: Qwen3 served by vLLM with JSON-schema-constrained decoding.

Deploy once, then the experiment calls it remotely in batches:

    modal deploy modal_app.py
    python -m agqo smoke-llm --llm modal --model coder30
    python -m agqo run --llm modal --model coder30 --out results/llm_coder30

The container stays warm for `scaledown_window` seconds between batches, so the
model loads once per experiment. Weights are cached in the Modal volume
`agqo-gate-models` (already populated with Qwen3-Coder-30B by the v1 runs).
"""

from __future__ import annotations

import json
import time

import modal

APP_NAME = "agqo-llm-core"
MODELS = {
    # key: (HF repo, pinned revision or None = latest main, max context). All run on one A100-80GB.
    "coder30": ("Qwen/Qwen3-Coder-30B-A3B-Instruct", "b2cff646eb4bb1d68355c01b18ae02e7cf42d120", 16384),
    "instruct30": ("Qwen/Qwen3-30B-A3B-Instruct-2507", None, 16384),
    "qwen8b": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218", 16384),
}

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm==0.15.0", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/model-cache/huggingface", "HF_HUB_ENABLE_HF_TRANSFER": "1",
          "VLLM_LOGGING_LEVEL": "WARNING", "VLLM_WORKER_MULTIPROC_METHOD": "spawn"})
)
cache = modal.Volume.from_name("agqo-gate-models", create_if_missing=True)
app = modal.App(APP_NAME)


@app.cls(image=image, gpu="A100-80GB", volumes={"/model-cache": cache}, timeout=3600,
         startup_timeout=1800, scaledown_window=600, max_containers=1)
class Engine:
    model_key: str = modal.parameter(default="coder30")

    @modal.enter()
    def load(self):
        from vllm import LLM

        repo, rev, ctx = MODELS[self.model_key]
        t = time.time()
        self.llm = LLM(model=repo, revision=rev, dtype="bfloat16", max_model_len=ctx,
                       gpu_memory_utilization=0.88, max_num_seqs=16, enable_prefix_caching=True,
                       trust_remote_code=False)
        self.repo, self.rev, self.ctx = repo, rev, ctx
        self.load_s = time.time() - t
        cache.commit()

    @modal.method()
    def generate(self, requests: list[dict]) -> list[dict]:
        import torch
        from vllm import SamplingParams
        from vllm.sampling_params import StructuredOutputsParams

        tok = self.llm.get_tokenizer()
        # Qwen3-8B is a hybrid reasoning model: disable thinking so the JSON grammar starts at token 1.
        tmpl = {"enable_thinking": False} if self.model_key == "qwen8b" else {}
        chats, params, lens = [], [], []
        for r in requests:
            chat = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}]
            n_in = len(tok.apply_chat_template(chat, add_generation_prompt=True, tokenize=True, **tmpl))
            if n_in + r["max_tokens"] > self.ctx:
                raise ValueError(f"prompt of {n_in} tokens exceeds context; refusing to truncate")
            chats.append(chat)
            lens.append(n_in)
            params.append(SamplingParams(temperature=r["temperature"], top_p=0.9, seed=r["seed"],
                                         max_tokens=r["max_tokens"],
                                         structured_outputs=StructuredOutputsParams(json=r["schema"])))
        t = time.time()
        outs = self.llm.chat(chats, sampling_params=params, use_tqdm=False, chat_template_kwargs=tmpl or None)
        dt = time.time() - t
        gpu = torch.cuda.get_device_name()
        return [{"raw_text": o.outputs[0].text, "finish_reason": o.outputs[0].finish_reason,
                 "usage": {"input_tokens": n, "output_tokens": len(o.outputs[0].token_ids)},
                 "model": self.repo, "revision": self.rev or "unpinned-main",
                 "execution": "live_modal_vllm", "gpu": gpu, "batch_generate_s": round(dt, 2),
                 "model_load_s": round(self.load_s, 1)}
                for o, n in zip(outs, lens)]


@app.local_entrypoint()
def smoke(model_key: str = "coder30"):
    schema = {"type": "object", "properties": {"qubits": {"type": "integer"}}, "required": ["qubits"]}
    out = Engine(model_key=model_key).generate.remote([{
        "system": "Answer in JSON.", "user": "A register with 8 assets and 2 bits per asset has how many qubits?",
        "schema": schema, "seed": 0, "temperature": 0.0, "max_tokens": 64}])
    print(json.dumps(out, indent=2))
