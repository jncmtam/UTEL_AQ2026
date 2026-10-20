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
PROMPT_CACHE_VERSION = "agqo-prompt-v1"


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


def create_guide_prompt(payload: dict[str, Any]) -> str:
    """Đóng gói bối cảnh định lượng, không gửi chuỗi dữ liệu tương lai hay OHLCV thô."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
