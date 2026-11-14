"""Dịch vụ Qwen3.8-27B trên Modal (vLLM, 1×H100, FP8); chỉ nhận insight tổng hợp, không nhận OHLCV.

Triển khai:
    modal run modal_qwen38_agqo.py::download_weights   # một lần, ~31 GB vào Volume
    modal deploy modal_qwen38_agqo.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import modal

from agqo.guide import (
    QWEN38_MODAL_APP,
    QWEN38_MODEL_NAME,
    QWEN38_MODEL_REVISION,
    QWEN38_REASONING_EFFORT,
    controller_system_prompt,
    create_guide_prompt,
    enrich_guide_payload,
    read_json_object,
    repair_guidance,
    split_reasoning,
    validate_guidance,
)


APP_NAME = os.environ.get("AGQO_QWEN38_MODAL_APP", QWEN38_MODAL_APP)
MODEL_NAME = os.environ.get("AGQO_QWEN38_MODEL", QWEN38_MODEL_NAME)
MODEL_REVISION = os.environ.get("AGQO_QWEN38_REVISION", QWEN38_MODEL_REVISION)
WEIGHTS_VOLUME_NAME = os.environ.get("AGQO_QWEN38_VOLUME", "agqo-qwen38-weights")
GPU_SPEC = os.environ.get("AGQO_QWEN38_GPU", "H100:1")
TENSOR_PARALLEL = int(GPU_SPEC.split(":")[1]) if ":" in GPU_SPEC else 1
MAX_MODEL_LEN = int(os.environ.get("AGQO_QWEN38_MAX_MODEL_LEN", "65536"))
MAX_NEW_TOKENS = int(os.environ.get("AGQO_QWEN38_MAX_NEW_TOKENS", "16384"))
USE_MTP = os.environ.get("AGQO_QWEN38_MTP", "0").strip().lower() in {"1", "true", "yes"}
VLLM_VERSION = "0.32.0"

WEIGHTS_ROOT = "/weights"
MODEL_DIR = f"{WEIGHTS_ROOT}/{MODEL_NAME}/{MODEL_REVISION}"
# Chỉ thay đổi tên/khoảng giá trị ở đây cũng làm đổi khóa cache phía client.
SAMPLING = {"temperature": 1.0, "top_p": 0.95}

app = modal.App(APP_NAME)
weights = modal.Volume.from_name(WEIGHTS_VOLUME_NAME, create_if_missing=True)

download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("huggingface_hub[hf_xet]>=1.0,<2")
    .add_local_python_source("agqo")
)

vllm_image = (
    modal.Image.from_registry(
        f"vllm/vllm-openai:v{VLLM_VERSION}",
        # Ảnh vLLM chỉ có `python3`; Modal cần lệnh `python` trên PATH.
        setup_dockerfile_commands=["RUN ln -sf \"$(command -v python3)\" /usr/local/bin/python"],
    )
    .entrypoint([])
    .run_commands("python -m pip install 'transformers>=5.15,<6'")
    .env(
        {
            "HF_HUB_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    .add_local_python_source("agqo")
)


@app.function(
    image=download_image,
    volumes={WEIGHTS_ROOT: weights},
    cpu=8,
    memory=16384,
    timeout=6 * 60 * 60,
)
def download_weights() -> dict[str, Any]:
    """Tải đúng revision đã ghim vào Volume; chạy lại sẽ chỉ tải phần còn thiếu."""
    from huggingface_hub import snapshot_download

    started = time.time()
    path = snapshot_download(
        repo_id=MODEL_NAME,
        revision=MODEL_REVISION,
        local_dir=MODEL_DIR,
        max_workers=16,
    )
    weights.commit()
    total = sum(
        os.path.getsize(os.path.join(root, name))
        for root, _, names in os.walk(path)
        for name in names
    )
    return {
        "model": MODEL_NAME,
        "revision": MODEL_REVISION,
        "path": path,
        "bytes": total,
        "seconds": round(time.time() - started, 1),
    }


def _seed_for(messages: list[dict[str, str]]) -> int:
    """Seed tất định theo nội dung prompt để lần chạy lại trên cùng phần cứng có thể tái lập."""
    digest = hashlib.sha256(
        json.dumps(messages, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


@app.cls(
    image=vllm_image,
    volumes={WEIGHTS_ROOT: weights},
    gpu=GPU_SPEC,
    cpu=16,
    memory=65536,
    timeout=60 * 60,
    startup_timeout=60 * 60,
    scaledown_window=15 * 60,
    retries=0,
)
class Qwen38Guide:
    """Một yêu cầu mỗi lúc: engine vLLM offline không an toàn cho gọi song song.

    Qwen3.8-27B chọn một chính sách QAOA trong danh sách cho phép và trả JSON đã kiểm tra."""

    @modal.enter()
    def load(self) -> None:
        from vllm import LLM

        if not os.path.exists(os.path.join(MODEL_DIR, "config.json")):
            raise RuntimeError(
                f"Chưa có trọng số tại {MODEL_DIR}. Chạy `modal run modal_qwen38_agqo.py::download_weights` trước."
            )
        options: dict[str, Any] = {}
        if USE_MTP:
            options["speculative_config"] = {"method": "mtp", "num_speculative_tokens": 3}
        started = time.time()
        self.llm = LLM(
            model=MODEL_DIR,
            tensor_parallel_size=TENSOR_PARALLEL,
            kv_cache_dtype="fp8",
            # Mô hình là VL; AGQO chỉ gửi văn bản nên tắt đầu vào ảnh/video để dành bộ nhớ cho KV cache.
            limit_mm_per_prompt={"image": 0, "video": 0},
            max_model_len=MAX_MODEL_LEN,
            max_num_seqs=8,
            gpu_memory_utilization=0.92,
            **options,
        )
        self.load_seconds = round(time.time() - started, 1)

    def _generate(
        self, messages: list[dict[str, str]], reasoning_effort: str
    ) -> tuple[str, str, int, int, int]:
        from vllm import SamplingParams

        seed = _seed_for(messages)
        params = SamplingParams(max_tokens=MAX_NEW_TOKENS, seed=seed, **SAMPLING)
        output = self.llm.chat(
            messages,
            params,
            chat_template_kwargs={"reasoning_effort": reasoning_effort},
            use_tqdm=False,
        )[0]
        completion = output.outputs[0]
        reasoning, answer = split_reasoning(completion.text)
        return (
            reasoning,
            answer,
            len(output.prompt_token_ids or []),
            len(completion.token_ids),
            seed,
        )

    @modal.method()
    def guide_qaoa_policy(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("payload"), dict):
            raise ValueError("Yêu cầu cần có payload định lượng dạng đối tượng JSON.")
        if request.get("model_name", MODEL_NAME) != MODEL_NAME:
            raise ValueError(
                f"Client yêu cầu {request.get('model_name')}, nhưng ứng dụng đang chạy {MODEL_NAME}."
            )
        if request.get("revision", MODEL_REVISION) != MODEL_REVISION:
            raise ValueError(
                "Revision Qwen3.8-27B trong lệnh chạy không khớp với bản đã triển khai. "
                "Triển khai lại với AGQO_QWEN38_REVISION tương ứng."
            )
        effort = request.get("reasoning_effort", QWEN38_REASONING_EFFORT)
        if effort not in {"low", "medium", "xhigh"}:
            raise ValueError("reasoning_effort chỉ nhận low, medium hoặc xhigh.")

        started = time.time()
        prompt_payload = enrich_guide_payload(request["payload"])
        messages = [
            {"role": "system", "content": controller_system_prompt()},
            {"role": "user", "content": create_guide_prompt(prompt_payload)},
        ]
        reasoning, answer, input_tokens, output_tokens, seed = self._generate(messages, effort)
        reasoning_hashes = [hashlib.sha256(reasoning.encode("utf-8")).hexdigest()]
        allowed_evidence_ids = set(prompt_payload.get("evidence_ids", []))
        allowed_policy_ids = set(prompt_payload.get("eligible_policy_ids", [])) or {
            "n12_balanced_xy_ring_p1"
        }
        allowed_insight_codes = set(prompt_payload.get("allowed_insight_codes", [])) or {
            "mixed_signals"
        }
        try:
            decision = validate_guidance(
                read_json_object(answer), allowed_evidence_ids, allowed_policy_ids,
                allowed_insight_codes,
            )
            validation_repairs: list[str] = []
        except (ValueError, json.JSONDecodeError):
            messages.extend(
                [
                    {"role": "assistant", "content": answer or "(no final answer)"},
                    {
                        "role": "user",
                        "content": (
                            "The previous final answer was missing, invalid JSON, or violated response_schema. "
                            "Read response_schema in the payload and return exactly one JSON object matching it. "
                            "Do not add rationale, risk flags, confidence, or prose."
                        ),
                    },
                ]
            )
            reasoning, answer, retry_in, retry_out, _ = self._generate(messages, effort)
            reasoning_hashes.append(hashlib.sha256(reasoning.encode("utf-8")).hexdigest())
            input_tokens += retry_in
            output_tokens += retry_out
            try:
                decision = validate_guidance(
                    read_json_object(answer), allowed_evidence_ids, allowed_policy_ids,
                    allowed_insight_codes,
                )
                validation_repairs = ["format_retry_used"]
            except (ValueError, json.JSONDecodeError):
                try:
                    retry_object = read_json_object(answer)
                except (ValueError, json.JSONDecodeError):
                    retry_object = {}
                decision, validation_repairs = repair_guidance(
                    retry_object, allowed_evidence_ids, allowed_policy_ids, allowed_insight_codes
                )
                validation_repairs.insert(0, "format_retry_used")

        return {
            "decision": decision,
            "validation_repairs": validation_repairs,
            "model": MODEL_NAME,
            "model_revision": MODEL_REVISION,
            "quantization": "FP8 (official Qwen3.8-27B-FP8 checkpoint); FP8 KV cache",
            "serving": {
                "engine": f"vLLM {VLLM_VERSION}",
                "gpu": GPU_SPEC,
                "tensor_parallel_size": TENSOR_PARALLEL,
                "max_model_len": MAX_MODEL_LEN,
                "mtp_speculative_decoding": USE_MTP,
                "engine_load_seconds": self.load_seconds,
            },
            "generation": {
                "reasoning_effort": effort,
                "seed": seed,
                "max_new_tokens": MAX_NEW_TOKENS,
                **SAMPLING,
            },
            "reasoning_sha256": reasoning_hashes,
            "latency_seconds": round(time.time() - started, 2),
            "response_id": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }
