# AGQO – Chạy thử nhanh

**Prototype đã triển khai (không cần tài khoản):** https://data1--agqo-demo.us-east.modal.run

## Chạy trên máy (Python 3.12, không cần GPU)

```bash
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                                 # 25 passed
AGQO_LIVE_LLM=0 uvicorn app.server:api --port 8000        # mở http://localhost:8000
```

## Tái lập kết quả

```bash
python -m agqo mandates --llm replay   # 35 yêu cầu tiếng Việt, phát lại LLM từ nhật ký
python -m agqo run                     # huấn luyện 2023 + kiểm định 12 quý (~20 phút CPU)
python -m agqo explain --llm replay    # 12 lời giải thích, kiểm tra số và ý nghĩa
python -m agqo extras                  # nhiễu IBM Heron, 8–20 qubit, độ bền
python -m agqo report                  # hình + docs/RESULTS.md
```

## Bản đồ thư mục

| Thư mục | Nội dung |
|---|---|
| `agqo/` | lõi: dữ liệu, danh mục lô chẵn, QUBO, QAOA, LLM, kiểm định |
| `app/` | prototype web (FastAPI + ECharts), triển khai Modal |
| `modal_app.py` | Qwen3.8-27B trên vLLM, GPU H100 |
| `data/vn30/` | dữ liệu giá ngày 2022–2026, thành phần VN30 theo thời điểm |
| `results/final/` | mọi kết quả, nhật ký mọi lời gọi LLM |
| `docs/` | phương pháp, kết quả, 75 câu hỏi phản biện, kịch bản thuyết trình, hình |
| `submission/` | mã tạo slide, báo cáo, hướng dẫn |

Chi tiết: `AQ2026-R2-Madoi-Huong_dan.pdf`.
