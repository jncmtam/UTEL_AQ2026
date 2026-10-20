"""Dịch vụ LLM có cấu trúc trên Modal cho bộ điều khiển AGQO."""

from __future__ import annotations

import json
import os

import modal

from agqo.guide import create_guide_prompt, decision_json_schema


APP_NAME = "agqo-llm-guide"
SECRET_NAME = os.environ.get("AGQO_MODAL_SECRET_NAME", "agqo-openai")
DEFAULT_MODEL_NAME = "gpt-5-mini"

app = modal.App(APP_NAME)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("openai>=1.66,<3")
    .add_local_python_source("agqo")
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(SECRET_NAME, required_keys=["OPENAI_API_KEY"])],
    timeout=90,
    retries=0,
)
def guide_qaoa_policy(request: dict) -> dict:
    """Chọn một chính sách trong danh mục hữu hạn, không tạo tham số tự do."""
    from openai import OpenAI

    if not isinstance(request, dict) or not isinstance(request.get("payload"), dict):
        raise ValueError("Yêu cầu Modal phải có payload định lượng dạng đối tượng JSON.")
    payload = request["payload"]
    model_name = request.get("model_name", DEFAULT_MODEL_NAME)
    if not isinstance(model_name, str) or not model_name.strip() or len(model_name) > 100:
        raise ValueError("Tên mô hình LLM không hợp lệ.")

    instructions = (
        "Bạn là bộ hướng dẫn lượng tử của AGQO, kết nối insight tài chính với cấu hình QAOA. Đọc dữ liệu định lượng "
        "đến as_of_date và chọn đúng một policy_id trong policy_catalog. So sánh past_completed_policy_benchmarks "
        "theo từng chính sách; ưu tiên số kỳ đủ dài, CAGR ròng, Sharpe, Sortino, mức giảm vốn, VaR/CVaR, hệ số lợi nhuận, "
        "doanh số và chi phí. Cân nhắc xác suất biến động, tương quan, độ rộng, cơ cấu ngành và thanh khoản hiện tại. "
        "Mục tiêu QAOA có cộng phí đổi danh mục năm hóa dựa trên danh mục AGQO kỳ trước. Nếu lịch sử ngắn "
        "hoặc thiếu, hãy nói rõ và giảm mức khẳng định. Không dùng kết quả chưa khép, không dự đoán lợi nhuận tương lai, "
        "không tự tạo tham số và không chọn mã cổ phiếu. Chỉ gắn insight_codes được số liệu hỗ trợ. Lý do và ghi chú rủi ro "
        "phải viết bằng tiếng Việt, viện dẫn trường số liệu cụ thể. Mức tin cậy là đánh giá tự khai, không phải xác suất "
        "đã hiệu chỉnh. Đây là quyết định nghiên cứu, không phải khuyến nghị đầu tư."
    )
    client = OpenAI(timeout=75, max_retries=0)
    response = client.responses.create(
        model=model_name,
        input=[
            {"role": "developer", "content": instructions},
            {"role": "user", "content": create_guide_prompt(payload)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "agqo_qaoa_guidance",
                "strict": True,
                "schema": decision_json_schema(),
            }
        },
        max_output_tokens=500,
        store=False,
    )
    if not response.output_text:
        raise RuntimeError("Mô hình không trả quyết định JSON; kiểm tra trạng thái hoặc nội dung từ chối của phản hồi.")
    decision = json.loads(response.output_text)
    usage = None
    if response.usage is not None:
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    return {
        "decision": decision,
        "model": response.model,
        "response_id": response.id,
        "usage": usage,
    }


@app.local_entrypoint()
def main(payload_json: str = "") -> None:
    """Lệnh kiểm tra thủ công tùy chọn, nhận bối cảnh JSON từ dòng lệnh."""
    if not payload_json:
        raise ValueError("Cần truyền --payload-json với một đối tượng JSON định lượng.")
    result = guide_qaoa_policy.remote(
        {"payload": json.loads(payload_json), "model_name": os.environ.get("AGQO_LLM_MODEL", DEFAULT_MODEL_NAME)}
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
