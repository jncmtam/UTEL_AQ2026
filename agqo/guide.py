"""Bộ chính sách hữu hạn và xác thực quyết định LLM cho AGQO."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .insights import supported_insight_codes


@dataclass(frozen=True)
class QAOAPolicy:
    """Một cấu hình được phép để LLM chọn; mọi trường đều chạy được trong bộ giải."""

    policy_id: str
    risk_aversion: float
    shrinkage: float
    mixer: str
    depth: int
    shots: int
    n_qubits: int
    mixer_layout: str
    description: str


POLICIES: dict[str, QAOAPolicy] = {
    policy.policy_id: policy
    for policy in (
        QAOAPolicy("n08_defensive_x_p1", 8.0, 0.70, "X", 1, 1024, 8, "single", "8 qubits; X mixer; p=1; defensive risk penalty."),
        QAOAPolicy("n08_balanced_xy_ring_p1", 5.0, 0.40, "XY", 1, 1024, 8, "ring", "8 qubits; XY ring mixer; p=1."),
        QAOAPolicy("n08_balanced_xy_ring_p2", 5.0, 0.40, "XY", 2, 1024, 8, "ring", "8 qubits; XY ring mixer; p=2."),
        QAOAPolicy("n12_balanced_x_p1", 5.0, 0.40, "X", 1, 1024, 12, "single", "12 qubits; X mixer; p=1."),
        QAOAPolicy("n12_balanced_x_p2", 5.0, 0.40, "X", 2, 1024, 12, "single", "12 qubits; X mixer; p=2."),
        QAOAPolicy("n12_balanced_xy_ring_p1", 5.0, 0.40, "XY", 1, 1024, 12, "ring", "12 qubits; XY ring mixer; p=1."),
        QAOAPolicy("n12_balanced_xy_ring_p2", 5.0, 0.40, "XY", 2, 1024, 12, "ring", "12 qubits; XY ring mixer; p=2."),
        QAOAPolicy("n12_diversified_xy_linear_p2", 5.0, 0.70, "XY", 2, 1024, 12, "linear", "12 qubits; XY linear mixer; p=2; stronger diagonal covariance shrinkage."),
        QAOAPolicy("n12_diversified_xy_complete_p1", 5.0, 0.70, "XY", 1, 1024, 12, "complete", "12 qubits; complete XY mixer; p=1; stronger diagonal covariance shrinkage."),
        QAOAPolicy("n12_correlation_xy_p2", 5.0, 0.40, "XY", 2, 1024, 12, "correlation", "12 qubits; correlation-informed XY mixer; p=2."),
        QAOAPolicy("n16_balanced_x_p1", 5.0, 0.40, "X", 1, 1024, 16, "single", "16 qubits; X mixer; p=1."),
        QAOAPolicy("n16_balanced_xy_ring_p1", 5.0, 0.40, "XY", 1, 1024, 16, "ring", "16 qubits; XY ring mixer; p=1."),
        QAOAPolicy("n16_balanced_xy_ring_p2", 5.0, 0.40, "XY", 2, 1024, 16, "ring", "16 qubits; XY ring mixer; p=2."),
        QAOAPolicy("n16_correlation_xy_p2", 5.0, 0.40, "XY", 2, 1024, 16, "correlation", "16 qubits; correlation-informed XY mixer; p=2."),
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
PROMPT_CACHE_VERSION = "agqo-prompt-v9-en-rag-submodel-allowlisted-structured"
QWEN3_MODEL_NAME = "Qwen/Qwen3-8B"
QWEN3_MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def policy_catalog() -> list[dict[str, Any]]:
    """Trả danh mục cấu hình theo thứ tự ổn định để đưa vào lời nhắc và lưu báo cáo."""
    return [asdict(POLICIES[key]) for key in sorted(POLICIES)]


def decision_json_schema(
    allowed_policy_ids: set[str] | None = None,
    allowed_evidence_ids: set[str] | None = None,
    allowed_insight_codes: list[str] | None = None,
) -> dict[str, Any]:
    """Lược đồ gọn: mô hình chỉ trả lựa chọn và mã insight, không viết nhận định tự do."""
    policy_ids = sorted(POLICIES if allowed_policy_ids is None else allowed_policy_ids)
    evidence_ids = sorted(allowed_evidence_ids) if allowed_evidence_ids is not None else None
    insight_codes = allowed_insight_codes or list(INSIGHT_CODES)
    return {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string", "enum": policy_ids},
            "insight_codes": {
                "type": "array",
                "items": {"type": "string", "enum": insight_codes},
                "minItems": 1,
            },
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string", **({"enum": evidence_ids} if evidence_ids is not None else {})},
                "minItems": 1,
            },
        },
        "required": ["policy_id", "insight_codes", "evidence_ids"],
        "additionalProperties": False,
    }


def validate_guidance(
    raw: dict[str, Any],
    allowed_evidence_ids: set[str] | None = None,
    allowed_policy_ids: set[str] | None = None,
    allowed_insight_codes: set[str] | None = None,
) -> dict[str, Any]:
    """Kiểm tra đầu ra LLM bằng luật cục bộ; không tin lời giải thích để thực thi mã."""
    if not isinstance(raw, dict):
        raise ValueError("Lời hướng dẫn AGQO phải là một đối tượng JSON.")
    allowed_fields = {"policy_id", "insight_codes", "evidence_ids"}
    unexpected_fields = set(raw) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Đầu ra có trường ngoài lược đồ: {sorted(unexpected_fields)}.")
    policy_id = raw.get("policy_id")
    permitted_policies = set(POLICIES) if allowed_policy_ids is None else set(allowed_policy_ids)
    if not permitted_policies or not permitted_policies.issubset(POLICIES):
        raise ValueError("Danh sách policy được phép không hợp lệ hoặc rỗng.")
    if not isinstance(policy_id, str) or policy_id not in permitted_policies:
        raise ValueError(f"Mã cấu hình LLM không được phép: {policy_id!r}.")
    codes = raw.get("insight_codes")
    permitted_insights = set(INSIGHT_CODES) if allowed_insight_codes is None else set(allowed_insight_codes)
    if not permitted_insights or not permitted_insights.issubset(INSIGHT_CODES):
        raise ValueError("Danh sách insight được phép không hợp lệ hoặc rỗng.")
    if not isinstance(codes, list) or not codes or any(
        not isinstance(code, str) or code not in permitted_insights for code in codes
    ):
        raise ValueError("Mã insight phải thuộc danh sách insight được phép.")
    evidence_ids = raw.get("evidence_ids")
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("Quyết định phải viện dẫn ít nhất một mã bằng chứng.")
    if any(not isinstance(item, str) for item in evidence_ids):
        raise ValueError("Mã bằng chứng phải là chuỗi.")
    if allowed_evidence_ids is not None and any(item not in allowed_evidence_ids for item in evidence_ids):
        raise ValueError("Quyết định viện dẫn mã bằng chứng không có trong dữ liệu đầu vào.")
    return {
        "policy_id": policy_id,
        "insight_codes": list(dict.fromkeys(codes)),
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
    }


def repair_guidance(
    raw: dict[str, Any],
    allowed_evidence_ids: set[str],
    allowed_policy_ids: set[str] | None = None,
    allowed_insight_codes: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Normalize malformed model fields into a valid, auditable safe decision."""
    if not isinstance(raw, dict):
        raw = {}
    repaired: list[str] = []
    allowed_fields = {"policy_id", "insight_codes", "evidence_ids"}
    if set(raw) - allowed_fields:
        repaired.append("unsupported_free_text_fields_removed")
    permitted_policies = set(POLICIES) if allowed_policy_ids is None else set(allowed_policy_ids)
    if not permitted_policies or not permitted_policies.issubset(POLICIES):
        raise ValueError("Danh sách policy được phép không hợp lệ hoặc rỗng.")
    permitted_insights = set(INSIGHT_CODES) if allowed_insight_codes is None else set(allowed_insight_codes)
    if not permitted_insights or not permitted_insights.issubset(INSIGHT_CODES):
        raise ValueError("Danh sách insight được phép không hợp lệ hoặc rỗng.")
    policy_id = raw.get("policy_id")
    if not isinstance(policy_id, str) or policy_id not in permitted_policies:
        warmup = "n12_balanced_xy_ring_p1"
        policy_id = warmup if warmup in permitted_policies else sorted(permitted_policies)[0]
        repaired.append("policy_id_to_warmup_default")
    codes = raw.get("insight_codes")
    if not isinstance(codes, list):
        codes = []
        repaired.append("insight_codes_type")
    valid_codes = list(dict.fromkeys(code for code in codes if isinstance(code, str) and code in permitted_insights))
    if len(valid_codes) != len(codes):
        repaired.append("unknown_insight_codes_removed")
    if not valid_codes:
        fallback_insight = (
            "mixed_signals"
            if "mixed_signals" in permitted_insights
            else sorted(permitted_insights)[0]
        )
        valid_codes = [fallback_insight]
        repaired.append("insight_codes_defaulted")
    evidence_ids = raw.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        evidence_ids = []
        repaired.append("evidence_ids_type")
    valid_evidence = list(dict.fromkeys(item for item in evidence_ids if isinstance(item, str) and item in allowed_evidence_ids))
    evidence_invalid = len(valid_evidence) != len(evidence_ids)
    if evidence_invalid:
        repaired.append("unsupported_evidence_ids_removed")
    if not valid_evidence:
        if not allowed_evidence_ids:
            raise ValueError("Không có bằng chứng hợp lệ để sửa quyết định LLM.")
        valid_evidence = [sorted(allowed_evidence_ids)[0]]
        repaired.append("evidence_id_defaulted")
    return validate_guidance(
        {
            "policy_id": policy_id,
            "insight_codes": valid_codes,
            "evidence_ids": valid_evidence,
        },
        allowed_evidence_ids,
        permitted_policies,
        permitted_insights,
    ), list(dict.fromkeys(repaired))


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
            # Keep the tracked decision artifact aligned to the active English prompt.
            # Older entries remain reproducible from Git history and should not be
            # mixed into a final report for a newer prompt version.
            self.cache = {
                key: value
                for key, value in loaded.items()
                if isinstance(value, dict)
                and value.get("prompt_version") == PROMPT_CACHE_VERSION
            }

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = _canonical_hash({"namespace": self.cache_namespace, "payload": payload})
        if key in self.cache:
            saved = dict(self.cache[key])
            saved["cache_hit"] = True
            return saved
        response = self.invoke(payload)
        if not isinstance(response, dict):
            raise ValueError("Dịch vụ Modal trả kết quả không đúng cấu trúc.")
        decision = validate_guidance(
            response.get("decision", {}),
            set(payload.get("evidence_ids", [])),
            set(payload.get("eligible_policy_ids", POLICIES)),
            set(payload.get("allowed_insight_codes", INSIGHT_CODES)),
        )
        result = {
            **response,
            "decision": decision,
            "cache_key": key,
            "cache_hit": False,
            "prompt_version": PROMPT_CACHE_VERSION,
        }
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
    """English operating instructions for Qwen3; no hidden reasoning is requested."""
    return (
        "You are a constrained decision controller in AGQO (AI Guide for Quantum Optimization), not a financial analyst. "
        "Qwen3-8B may not know the project's finance definitions and must not fill gaps from memory. The supplied, "
        "date-cutoff payload and its retrieved method_notes are the only authority. They define this dataset's units, "
        "financial metrics, QAOA objective, solver metrics, and known data limitations. Follow those definitions exactly. "
        "The task is narrow: choose one policy_id from eligible_policy_ids, choose only currently supported insight codes, "
        "and cite evidence IDs already supplied. QAOA—not the LLM—selects the assets. Do not invent returns, explain "
        "causality, choose securities, tune values outside the catalog, or write prose.\n\n"
        "Use this decision order: (1) exclude every policy outside eligible_policy_ids; this list enforces at least six "
        "completed outcomes and matured solver evidence, or names the mandatory warm-up policy when history is short; "
        "(2) compare only outcomes whose exit_date is no later than as_of_date; (3) compare net return together with "
        "Sharpe, drawdown, CVaR, turnover and fees; (4) check exact-solver regret and feasible-shot rate; (5) where "
        "financial and solver evidence is similar, prefer fewer logical two-qubit gates; (6) do not let one metric, one "
        "seed, self-confidence, or a noisy short history dominate. Logical gate counts are simulator proxies, not "
        "hardware depth, runtime, or evidence of quantum advantage.\n\n"
        "The logistic submodel estimates only a high-volatility regime, not returns. If fewer than six monthly forecasts "
        "have matured or Brier skill is not positive, treat its probability as unverified and do not use it alone to "
        "increase risk or QAOA depth. Brier score is lower-is-better; overlapping 21-session labels are not independent. "
        "Use insight_code_rules as exact thresholds. Only codes listed in allowed_insight_codes can be returned; if none "
        "of the measured warning conditions apply, use mixed_signals.\n\n"
        "Return exactly one JSON object matching response_schema from the payload, with no Markdown or additional fields. "
        "This is research, not investment advice."
    )


class TransformersQwen3Guide:
    """Chạy Qwen3 ngay trong máy tính Modal Notebook; không cần dịch vụ suy luận/API LLM."""

    def __init__(
        self,
        model_name: str = QWEN3_MODEL_NAME,
        max_new_tokens: int = 192,
        require_gpu: bool = True,
        revision: str | None = QWEN3_MODEL_REVISION,
        quantize_4bit: bool = True,
    ):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("Cần tên mô hình Qwen3 hợp lệ.")
        if max_new_tokens < 64:
            raise ValueError("Ngân sách sinh phải ít nhất 64 token.")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError(
                "Cài Transformers và PyTorch trong Modal Notebook trước khi nạp Qwen3."
            ) from exc

        if require_gpu and not torch.cuda.is_available():
            raise RuntimeError(
                "Không tìm thấy GPU. Trong Modal Notebook, chọn GPU L4/A10 rồi khởi động lại kernel; "
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
        self.quantize_4bit = bool(quantize_4bit and torch.cuda.is_available())
        load_options = {"revision": revision} if revision else {}
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **load_options)
        if self.quantize_4bit:
            compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            )
            load_options["quantization_config"] = quantization_config
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=dtype,
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
        prompt_payload = enrich_guide_payload(payload)
        user_prompt = json.dumps(prompt_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        messages = [
            {"role": "system", "content": qwen3_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        raw_text, input_tokens, output_tokens = self._generate(messages)
        try:
            allowed_evidence_ids = set(prompt_payload.get("evidence_ids", []))
            allowed_policy_ids = set(prompt_payload.get("eligible_policy_ids", POLICIES))
            allowed_insight_codes = set(prompt_payload.get("allowed_insight_codes", INSIGHT_CODES))
            decision = validate_guidance(
                self._read_json(raw_text), allowed_evidence_ids, allowed_policy_ids, allowed_insight_codes
            )
            validation_repairs: list[str] = []
        except (ValueError, json.JSONDecodeError):
            messages.extend(
                [
                    {"role": "assistant", "content": raw_text},
                    {
                        "role": "user",
                        "content": (
                            "The previous response was invalid JSON or violated the schema. Return exactly one valid JSON object containing only the required fields from the schema. Select policy_id only from eligible_policy_ids. Do not add rationale, risk flags, or any prose."
                        ),
                    },
                ]
            )
            raw_text, retry_input_tokens, retry_output_tokens = self._generate(messages)
            input_tokens += retry_input_tokens
            output_tokens += retry_output_tokens
            try:
                decision = validate_guidance(
                    self._read_json(raw_text), allowed_evidence_ids, allowed_policy_ids, allowed_insight_codes
                )
                validation_repairs = ["format_retry_used"]
            except (ValueError, json.JSONDecodeError):
                try:
                    retry_object = self._read_json(raw_text)
                except (ValueError, json.JSONDecodeError):
                    retry_object = {}
                decision, validation_repairs = repair_guidance(
                    retry_object, allowed_evidence_ids, allowed_policy_ids, allowed_insight_codes
                )
                validation_repairs.insert(0, "format_retry_used")
        return {
            "decision": decision,
            "validation_repairs": validation_repairs,
            "model": self.model_name,
            "model_revision": self.model_revision,
            "response_id": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        "quantization": "NF4 4-bit" if self.quantize_4bit else "bf16/fp16/fp32",
        }


def enrich_guide_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the versioned local retrieval results for persistence and inference."""
    from .knowledge import CORPUS_VERSION, retrieve_method_notes

    enriched = dict(payload)
    enriched["local_knowledge_base_version"] = CORPUS_VERSION
    enriched["method_notes"] = retrieve_method_notes(payload, top_k=7)
    eligible_policy_ids = set(enriched.get("eligible_policy_ids", POLICIES))
    if not eligible_policy_ids:
        eligible_policy_ids = {"n12_balanced_xy_ring_p1"}
    allowed_evidence_ids = set(enriched.get("evidence_ids", []))
    allowed_insights = supported_insight_codes(enriched)
    enriched["allowed_insight_codes"] = allowed_insights
    enriched["response_schema"] = decision_json_schema(
        eligible_policy_ids, allowed_evidence_ids, allowed_insights
    )
    enriched["controller_contract"] = {
        "task": "Select one eligible QAOA policy and identify supported market insight codes.",
        "selection_order": [
            "Only compare matured, completed policy outcomes available by as_of_date.",
            "Compare net return with Sharpe, drawdown, CVaR, turnover, fees, exact-solver regret, and feasible-shot rate.",
            "If evidence is comparable, prefer fewer logical two-qubit gates.",
        ],
        "policy_allowlist": sorted(eligible_policy_ids),
        "insight_allowlist": allowed_insights,
        "output": "JSON only; no rationale or risk flags. Local deterministic code creates Vietnamese explanations.",
    }
    return enriched


def create_guide_prompt(payload: dict[str, Any]) -> str:
    """Attach relevant local reference notes and serialize a compact, auditable prompt."""
    enriched = enrich_guide_payload(payload)
    return json.dumps(enriched, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
