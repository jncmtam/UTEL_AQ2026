"""Modal GPU app: Qwen3.8-27B (official FP8 checkpoint) served by vLLM with JSON-schema decoding.

The LLM in AGQO reads and writes language, never numbers that reach the optimiser unchecked:
  * mandate compiler - Vietnamese investor instruction -> validated constraints (agqo/llm/tasks.py)
  * explainer        - verified decision evidence -> Vietnamese explanation, every number checked

    modal run modal_app.py::download_weights    # once, ~31 GB into the Volume
    modal deploy modal_app.py
    python -m agqo mandates --llm modal          # 35 instructions in one batch
    python -m agqo explain --llm modal           # one explanation per test quarter

One H100 (~4 USD/hour on Modal); a batch of requests runs in one warm container.
"""

from __future__ import annotations

import os
import time

import modal

APP_NAME = "agqo-llm"
MODEL = "Qwen/Qwen3.8-27B-FP8"
REVISION = "c3a462cc3d38cf351f3b26cbd763469eeb74ef81"
WEIGHTS = "/weights"
MODEL_DIR = f"{WEIGHTS}/{MODEL}/{REVISION}"
VLLM_VERSION = "0.32.0"

app = modal.App(APP_NAME)
volume = modal.Volume.from_name("agqo-qwen38-weights", create_if_missing=True)

download_image = modal.Image.debian_slim(python_version="3.12").uv_pip_install("huggingface_hub[hf_xet]>=1.0,<2")
image = (
    modal.Image.from_registry(
        f"vllm/vllm-openai:v{VLLM_VERSION}",
        setup_dockerfile_commands=['RUN ln -sf "$(command -v python3)" /usr/local/bin/python'],
    )
    .entrypoint([])
    .run_commands("python -m pip install 'transformers>=5.15,<6'")
    .env({"HF_HUB_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
)


@app.function(image=download_image, volumes={WEIGHTS: volume}, cpu=8, memory=16384, timeout=2 * 3600)
def download_weights() -> dict:
    from huggingface_hub import snapshot_download

    t = time.time()
    path = snapshot_download(repo_id=MODEL, revision=REVISION, local_dir=MODEL_DIR, max_workers=16)
    volume.commit()
    return {"path": path, "seconds": round(time.time() - t)}


@app.cls(image=image, gpu="H100", volumes={WEIGHTS: volume}, cpu=8, memory=65536, timeout=3600,
         startup_timeout=3600, scaledown_window=300, max_containers=1)
class Engine:
    @modal.enter()
    def load(self):
        from vllm import LLM

        if not os.path.exists(f"{MODEL_DIR}/config.json"):
            raise RuntimeError("weights missing: run `modal run modal_app.py::download_weights` first")
        t = time.time()
        self.llm = LLM(model=MODEL_DIR, kv_cache_dtype="fp8", max_model_len=32768, max_num_seqs=32,
                       gpu_memory_utilization=0.90, limit_mm_per_prompt={"image": 0, "video": 0})
        self.load_s = time.time() - t

    @modal.method()
    def generate(self, requests: list[dict]) -> list[dict]:
        import torch
        from vllm import SamplingParams
        from vllm.sampling_params import StructuredOutputsParams

        tok = self.llm.get_tokenizer()
        # Non-thinking mode: the JSON grammar applies from the first token (Qwen3.8 model card settings).
        kw = {"enable_thinking": False}
        chats, params, lens = [], [], []
        for r in requests:
            chat = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}]
            ids = tok.apply_chat_template(chat, add_generation_prompt=True, tokenize=True, **kw)
            n_in = len(ids["input_ids"] if hasattr(ids, "keys") else ids)    # transformers 5 returns a dict
            chats.append(chat)
            lens.append(n_in)
            params.append(SamplingParams(temperature=r["temperature"], top_p=0.8, top_k=20, seed=r["seed"],
                                         max_tokens=r["max_tokens"],
                                         structured_outputs=StructuredOutputsParams(json=r["schema"])))
        t = time.time()
        outs = self.llm.chat(chats, sampling_params=params, use_tqdm=False, chat_template_kwargs=kw)
        dt = time.time() - t
        return [{"raw_text": o.outputs[0].text, "finish_reason": o.outputs[0].finish_reason,
                 "usage": {"input_tokens": n, "output_tokens": len(o.outputs[0].token_ids)},
                 "model": MODEL, "revision": REVISION, "execution": "live_modal_vllm",
                 "gpu": torch.cuda.get_device_name(), "batch_generate_s": round(dt, 2),
                 "model_load_s": round(self.load_s, 1)}
                for o, n in zip(outs, lens)]
