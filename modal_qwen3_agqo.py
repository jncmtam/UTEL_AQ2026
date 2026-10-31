"""Dịch vụ Qwen3 trên Modal; máy cá nhân chỉ gửi insight tổng hợp, không gửi OHLCV."""

from __future__ import annotations

import json
import os
from typing import Any

import modal

from agqo.guide import (
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_REVISION,
    create_guide_prompt,
    enrich_guide_payload,
    qwen3_system_prompt,
    repair_guidance,
    validate_guidance,
)


APP_NAME = os.environ.get("AGQO_QWEN3_MODAL_APP", "agqo-qwen3-guide")
FUNCTION_NAME = os.environ.get(
    "AGQO_QWEN3_MODAL_FUNCTION", "guide_qaoa_policy"
)
MODEL_NAME = os.environ.get("AGQO_QWEN3_MODEL", QWEN3_MODEL_NAME)
MODEL_REVISION = os.environ.get("AGQO_QWEN3_REVISION", QWEN3_MODEL_REVISION)
MODEL_VOLUME_NAME = os.environ.get("AGQO_QWEN3_VOLUME", "agqo-qwen3-model-cache")
MODEL_CACHE_PATH = "/model-cache"
MAX_NEW_TOKENS = int(os.environ.get("AGQO_QWEN3_MAX_NEW_TOKENS", "192"))
GPU_TYPES = [
    item.strip()
    for item in os.environ.get("AGQO_QWEN3_GPU", "L4,A10").split(",")
    if item.strip()
]
LOAD_IN_4BIT = os.environ.get("AGQO_QWEN3_LOAD_IN_4BIT", "1").strip().lower() not in {"0", "false", "no"}

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name(MODEL_VOLUME_NAME, create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "torch>=2.6,<3", "transformers>=4.51,<5", "accelerate>=1.6",
        "bitsandbytes>=0.46,<1",
    )
    .add_local_python_source("agqo")
)

_TOKENIZER = None
_MODEL = None
_MODEL_REVISION = None
_TORCH = None


def _load_model():
    """Nạp một lần trong mỗi container và dùng Volume để giữ trọng số đã tải."""
    global _TOKENIZER, _MODEL, _MODEL_REVISION, _TORCH
    if _MODEL is not None:
        return _TOKENIZER, _MODEL, _MODEL_REVISION, _TORCH

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError(f"Modal function cần GPU; kiểm tra cấu hình {GPU_TYPES}.")
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    _TOKENIZER = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        cache_dir=f"{MODEL_CACHE_PATH}/huggingface",
    )
    load_options = {}
    if LOAD_IN_4BIT:
        load_options["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
    _MODEL = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        dtype=dtype,
        device_map="auto",
        cache_dir=f"{MODEL_CACHE_PATH}/huggingface",
        **load_options,
    )
    _MODEL.eval()
    _MODEL_REVISION = (
        getattr(_MODEL.config, "_commit_hash", None) or MODEL_REVISION
    )
    _TORCH = torch
    model_cache.commit()
    return _TOKENIZER, _MODEL, _MODEL_REVISION, _TORCH


def _generate(tokenizer, model, torch, messages: list[dict[str, str]], max_new_tokens: int | None = None):
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_tensors="pt",
        return_dict=True,
    )
    device = model.get_input_embeddings().weight.device
    encoded = {key: value.to(device) for key, value in encoded.items()}
    input_tokens = int(encoded["input_ids"].shape[-1])
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=MAX_NEW_TOKENS if max_new_tokens is None else max_new_tokens,
            do_sample=False,
            use_cache=True,
        )
    generated = output[0, input_tokens:]
    return (
        tokenizer.decode(generated, skip_special_tokens=True).strip(),
        input_tokens,
        int(generated.numel()),
    )


@app.function(
    name=FUNCTION_NAME,
    image=image,
    volumes={MODEL_CACHE_PATH: model_cache},
    gpu=GPU_TYPES[0] if len(GPU_TYPES) == 1 else GPU_TYPES,
    timeout=900,
    retries=0,
    scaledown_window=60,
)
def guide_qaoa_policy(request: dict[str, Any]) -> dict[str, Any]:
    """Chọn một chính sách được cho phép bằng Qwen3 và trả lời dạng JSON đã kiểm tra."""
    if not isinstance(request, dict) or not isinstance(request.get("payload"), dict):
        raise ValueError("Yêu cầu cần có payload định lượng dạng đối tượng JSON.")
    if request.get("model_name", MODEL_NAME) != MODEL_NAME:
        raise ValueError(
            f"CLI yêu cầu {request.get('model_name')}, nhưng ứng dụng đang chạy {MODEL_NAME}."
        )
    if request.get("revision", MODEL_REVISION) != MODEL_REVISION:
        raise ValueError(
            "Phiên bản Qwen3 trong lệnh chạy không khớp với phiên bản đã triển khai. "
            "Hãy triển khai lại ứng dụng với AGQO_QWEN3_REVISION tương ứng."
        )

    tokenizer, model, revision, torch = _load_model()
    prompt_payload = enrich_guide_payload(request["payload"])
    messages = [
        {"role": "system", "content": qwen3_system_prompt()},
        {"role": "user", "content": create_guide_prompt(prompt_payload)},
    ]
    raw_text, input_tokens, output_tokens = _generate(
        tokenizer, model, torch, messages
    )
    allowed_evidence_ids = set(prompt_payload.get("evidence_ids", []))
    allowed_policy_ids = set(prompt_payload.get("eligible_policy_ids", [])) or {
        "n12_balanced_xy_ring_p1"
    }
    allowed_insight_codes = set(prompt_payload.get("allowed_insight_codes", [])) or {"mixed_signals"}
    try:
        decision = validate_guidance(
            TransformersJsonReader.read(raw_text), allowed_evidence_ids, allowed_policy_ids,
            allowed_insight_codes,
        )
        validation_repairs = []
    except (ValueError, json.JSONDecodeError):
        messages.extend(
            [
                {"role": "assistant", "content": raw_text},
                {
                    "role": "user",
                    "content": (
                        "The previous response was invalid JSON or violated response_schema. Read response_schema in the payload and return exactly one JSON object matching it. Do not add rationale, risk flags, confidence, or prose."
                    ),
                },
            ]
        )
        raw_text, retry_input_tokens, retry_output_tokens = _generate(
            tokenizer, model, torch, messages
        )
        input_tokens += retry_input_tokens
        output_tokens += retry_output_tokens
        try:
            decision = validate_guidance(
                TransformersJsonReader.read(raw_text), allowed_evidence_ids, allowed_policy_ids,
                allowed_insight_codes,
            )
            validation_repairs = ["format_retry_used"]
        except (ValueError, json.JSONDecodeError):
            try:
                retry_object = TransformersJsonReader.read(raw_text)
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
        "model_revision": revision,
        "quantization": "NF4 4-bit" if LOAD_IN_4BIT else "bf16/fp16",
        "response_id": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


@app.function(name="repair_json", image=image, volumes={MODEL_CACHE_PATH: model_cache},
              gpu=GPU_TYPES[0] if len(GPU_TYPES) == 1 else GPU_TYPES,
              timeout=900, retries=0, scaledown_window=60)
def repair_json(request: dict[str, Any]) -> dict[str, Any]:
    """Separate repair contract; legacy policy endpoint remains unchanged."""
    if not isinstance(request, dict) or request.get("task") not in {"normalize_mandate", "propose_circuit"}:
        raise ValueError("Unsupported repair task.")
    tokenizer, model, revision, torch = _load_model()
    messages = [{"role": "system", "content": request["system"]},
                {"role": "user", "content": json.dumps({k: v for k, v in request.items() if k != "system"}, ensure_ascii=False)}]
    raw, input_tokens, output_tokens = _generate(tokenizer, model, torch, messages, max_new_tokens=1200)
    return {"response": TransformersJsonReader.read(raw), "raw_text": raw,
            "model": MODEL_NAME, "model_revision": revision,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                      "total_tokens": input_tokens + output_tokens}}


class TransformersJsonReader:
    """Đọc JSON do mô hình trả về; không thực thi mã trong câu trả lời."""

    @staticmethod
    def read(text: str) -> dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1]
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            start, end = stripped.find("{"), stripped.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("Qwen3 không trả đối tượng JSON có thể đọc được.")
            value = json.loads(stripped[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("Đầu ra Qwen3 phải là một đối tượng JSON.")
        return value
