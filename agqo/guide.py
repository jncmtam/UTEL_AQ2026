"""Bộ chính sách hữu hạn và xác thực quyết định LLM cho AGQO."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class QAOAPolicy:
    """Một cấu hình được phép để LLM chọn; mọi trường đều chạy được trong bộ giải."""

    policy_id: str
    risk_aversion: float
    shrinkage: float
    mixer: str
    depth: int
    shots: int
    description: str


POLICIES: dict[str, QAOAPolicy] = {
    policy.policy_id: policy
    for policy in (
        QAOAPolicy("balanced_x_p1", 5.0, 0.40, "X", 1, 512, "Cân bằng, mạch X nông."),
        QAOAPolicy("balanced_x_p2", 5.0, 0.40, "X", 2, 512, "Cân bằng, mạch X sâu hơn."),
        QAOAPolicy("balanced_xy_p1", 5.0, 0.40, "XY", 1, 512, "Cân bằng, bộ trộn bảo toàn số mã."),
        QAOAPolicy("balanced_x_p2_1024", 5.0, 0.40, "X", 2, 1024, "Cân bằng, p=2 và tăng số mẫu."),
        QAOAPolicy("defensive_x_p1", 8.0, 0.70, "X", 1, 512, "Ưu tiên giảm rủi ro và co rút mạnh."),
        QAOAPolicy("defensive_x_p2", 8.0, 0.70, "X", 2, 512, "Ưu tiên giảm rủi ro, p=2."),
        QAOAPolicy("defensive_xy_p1", 8.0, 0.70, "XY", 1, 512, "Phòng thủ với ràng buộc cardinality tự nhiên."),
        QAOAPolicy("diversified_x_p1", 5.0, 0.70, "X", 1, 512, "Tăng co rút để giảm nhiễu hiệp phương sai."),
        QAOAPolicy("diversified_x_p2", 5.0, 0.70, "X", 2, 512, "Co rút mạnh hơn, p=2."),
        QAOAPolicy("growth_x_p1", 2.0, 0.10, "X", 1, 512, "Ít ngại rủi ro hơn, co rút nhẹ."),
        QAOAPolicy("growth_x_p2", 2.0, 0.10, "X", 2, 512, "Ít ngại rủi ro hơn, p=2."),
        QAOAPolicy("diversified_xy_p1", 5.0, 0.70, "XY", 1, 512, "Co rút mạnh và bộ trộn bảo toàn số mã."),
    )
}

INSIGHT_CODES = (
    "high_volatility",
    "volatility_rising",
    "high_correlation",
    "high_dispersion",
    "bank_concentration",
    "low_liquidity",
    "mixed_signals",
)
PROMPT_CACHE_VERSION = "agqo-prompt-v2"
QWEN3_MODEL_NAME = "Qwen/Qwen3-4B"
QWEN3_MODEL_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"


def policy_catalog() -> list[dict[str, Any]]:
    """Trả danh mục cấu hình theo thứ tự ổn định để đưa vào lời nhắc và lưu báo cáo."""
    return [asdict(POLICIES[key]) for key in sorted(POLICIES)]


def decision_json_schema() -> dict[str, Any]:
    """Lược đồ chặt: mô hình chỉ được chọn mã chính sách và insight đã cho phép."""
    return {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string", "enum": sorted(POLICIES)},
            "insight_codes": {
                "type": "array",
                "items": {"type": "string", "enum": list(INSIGHT_CODES)},
            },
            "rationale": {"type": "string"},
            "risk_note": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["policy_id", "insight_codes", "rationale", "risk_note", "confidence"],
        "additionalProperties": False,
    }


def validate_guidance(raw: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra đầu ra LLM bằng luật cục bộ; không tin lời giải thích để thực thi mã."""
    if not isinstance(raw, dict):
        raise ValueError("Lời hướng dẫn AGQO phải là một đối tượng JSON.")
    policy_id = raw.get("policy_id")
    if not isinstance(policy_id, str) or policy_id not in POLICIES:
        raise ValueError(f"Mã cấu hình LLM không được phép: {policy_id!r}.")
    codes = raw.get("insight_codes")
    if not isinstance(codes, list) or not codes or any(code not in INSIGHT_CODES for code in codes):
        raise ValueError("Mã insight phải thuộc danh sách insight được phép.")
    confidence = raw.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Độ tin cậy phải là số trong khoảng từ 0 đến 1.")
    if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        raise ValueError("Độ tin cậy phải là số hữu hạn trong khoảng từ 0 đến 1.")
    rationale, risk_note = raw.get("rationale"), raw.get("risk_note")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 800:
        raise ValueError("Lý do chọn cấu hình phải có từ 1 đến 800 ký tự.")
    if not isinstance(risk_note, str) or not risk_note.strip() or len(risk_note) > 400:
        raise ValueError("Ghi chú rủi ro phải có từ 1 đến 400 ký tự.")
    return {
        "policy_id": policy_id,
        "insight_codes": list(dict.fromkeys(codes)),
        "rationale": rationale.strip(),
        "risk_note": risk_note.strip(),
        "confidence": float(confidence),
    }


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CachedGuide:
    """Lưu quyết định để kiểm toán và tránh gọi lại LLM cho cùng một tín hiệu."""

    def __init__(
        self,
        invoke: Callable[[dict[str, Any]], dict[str, Any]],
        cache_path: str | Path,
        cache_namespace: str = PROMPT_CACHE_VERSION,
    ):
        self.invoke = invoke
        self.cache_path = Path(cache_path)
        self.cache_namespace = cache_namespace
        self.cache: dict[str, Any] = {}
        if self.cache_path.exists():
            loaded = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("Tệp lưu đệm AGQO phải là đối tượng JSON.")
            self.cache = loaded

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = _canonical_hash({"namespace": self.cache_namespace, "payload": payload})
        if key in self.cache:
            saved = dict(self.cache[key])
            saved["cache_hit"] = True
            return saved
        response = self.invoke(payload)
        if not isinstance(response, dict):
            raise ValueError("Dịch vụ Modal trả kết quả không đúng cấu trúc.")
        decision = validate_guidance(response.get("decision", {}))
        result = {**response, "decision": decision, "cache_key": key, "cache_hit": False}
        self.cache[key] = result
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.cache_path.name}.", suffix=".tmp", dir=self.cache_path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.cache, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary_name, self.cache_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return result


class ModalGuide:
    """Máy khách mỏng gọi hàm LLM đã triển khai trên Modal."""

    def __init__(
        self,
        app_name: str = "agqo-llm-guide",
        function_name: str = "guide_qaoa_policy",
        model_name: str = "gpt-5-mini",
    ):
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Cài tiện ích đám mây bằng `pip install -e '.[llm-modal]'`.") from exc
        self.function = modal.Function.from_name(app_name, function_name)
        self.model_name = model_name

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.function.remote({"payload": payload, "model_name": self.model_name})


class ModalQwen3Guide:
    """Máy khách cục bộ gọi bộ suy luận Qwen3 đã triển khai trên Modal."""

    def __init__(
        self,
        app_name: str = "agqo-qwen3-guide",
        function_name: str = "guide_qaoa_policy",
        model_name: str = QWEN3_MODEL_NAME,
        revision: str = QWEN3_MODEL_REVISION,
    ):
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Cài SDK bằng `python -m pip install -e '.[llm-modal]'`.") from exc
        self.function = modal.Function.from_name(app_name, function_name)
        self.model_name = model_name
        self.model_revision = revision

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.function.remote(
            {
                "payload": payload,
                "model_name": self.model_name,
                "revision": self.model_revision,
            }
        )


def qwen3_system_prompt() -> str:
    """Chỉ dẫn chung cho bộ suy luận Qwen3 tại chỗ hoặc trên Modal."""
    return (
        "Bạn là bộ điều khiển AGQO. Chỉ dùng số liệu trong bối cảnh đến ngày as_of_date. "
        "Đọc insight thị trường và kết quả kiểm định các chính sách đã hoàn tất, sau đó chọn "
        "đúng một policy_id từ policy_catalog. Ưu tiên lợi nhuận ròng đã điều chỉnh rủi ro "
        "sau chi phí; xem xét CAGR, Sharpe, Sortino, sụt giảm tối đa, VaR/CVaR, hệ số lợi nhuận, "
        "doanh số, chi phí và số kỳ. Nếu lịch sử ngắn hoặc thiếu, nêu rõ hạn chế và giảm mức khẳng định. "
        "Không dùng kết quả chưa khép, không dự báo lợi nhuận tương lai, không tự tạo tham số, "
        "không chọn cổ phiếu. Chỉ gắn insight_codes được số liệu hỗ trợ. Viết rationale và risk_note "
        "bằng tiếng Việt, dẫn trường số liệu cụ thể. confidence là mức tự đánh giá chưa hiệu chỉnh. "
        "Đây là nghiên cứu, không phải khuyến nghị đầu tư. Trả về duy nhất JSON hợp lệ theo schema "
        f"này, không có lời dẫn: {json.dumps(decision_json_schema(), ensure_ascii=False)}"
    )


class TransformersQwen3Guide:
    """Chạy Qwen3 ngay trong máy tính Modal Notebook; không cần dịch vụ suy luận/API LLM."""

    def __init__(
        self,
        model_name: str = QWEN3_MODEL_NAME,
        max_new_tokens: int = 480,
        require_gpu: bool = True,
        revision: str | None = QWEN3_MODEL_REVISION,
    ):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("Cần tên mô hình Qwen3 hợp lệ.")
        if max_new_tokens < 64:
            raise ValueError("Ngân sách sinh phải ít nhất 64 token.")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Cài Transformers và PyTorch trong Modal Notebook trước khi nạp Qwen3."
            ) from exc

        if require_gpu and not torch.cuda.is_available():
            raise RuntimeError(
                "Không tìm thấy GPU. Trong Modal Notebook, chọn GPU T4/L4 rồi khởi động lại kernel; "
                "hoặc dùng Qwen3-0.6B với require_gpu=False để thử trên CPU."
            )
        if torch.cuda.is_available():
            dtype = (
                torch.bfloat16
                if torch.cuda.is_bf16_supported()
                else torch.float16
            )
        else:
            dtype = torch.float32
        self.torch = torch
        self.model_name = model_name
        self.requested_revision = revision
        self.max_new_tokens = int(max_new_tokens)
        load_options = {"revision": revision} if revision else {}
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **load_options)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map="auto",
            **load_options,
        )
        self.model_revision = (
            revision
            or getattr(self.model.config, "_commit_hash", None)
            or "unresolved"
        )
        self.model.eval()

    @staticmethod
    def _read_json(text: str) -> dict[str, Any]:
        """Đọc JSON thuần hoặc phần JSON trong hàng rào mã; không thực thi văn bản mô hình."""
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

    def _generate(self, messages: list[dict[str, str]]) -> tuple[str, int, int]:
        torch = self.torch
        encoded = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_tensors="pt",
            return_dict=True,
        )
        device = self.model.get_input_embeddings().weight.device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        input_tokens = int(encoded["input_ids"].shape[-1])
        with torch.inference_mode():
            output = self.model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
        generated = output[0, input_tokens:]
        return (
            self.tokenizer.decode(generated, skip_special_tokens=True).strip(),
            input_tokens,
            int(generated.numel()),
        )

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Bối cảnh AGQO phải là một đối tượng JSON.")
        user_prompt = create_guide_prompt(payload)
        messages = [
            {"role": "system", "content": qwen3_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        raw_text, input_tokens, output_tokens = self._generate(messages)
        try:
            decision = validate_guidance(self._read_json(raw_text))
        except (ValueError, json.JSONDecodeError):
            messages.extend(
                [
                    {"role": "assistant", "content": raw_text},
                    {
                        "role": "user",
                        "content": (
                            "Đầu ra trước sai định dạng hoặc vi phạm schema. Hãy sửa và chỉ trả một "
                            "đối tượng JSON hợp lệ có đủ mọi trường bắt buộc; không thêm văn bản."
                        ),
                    },
                ]
            )
            raw_text, retry_input_tokens, retry_output_tokens = self._generate(messages)
            input_tokens += retry_input_tokens
            output_tokens += retry_output_tokens
            decision = validate_guidance(self._read_json(raw_text))
        return {
            "decision": decision,
            "model": self.model_name,
            "model_revision": self.model_revision,
            "response_id": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }


def create_guide_prompt(payload: dict[str, Any]) -> str:
    """Đóng gói bối cảnh định lượng, không gửi chuỗi dữ liệu tương lai hay OHLCV thô."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
