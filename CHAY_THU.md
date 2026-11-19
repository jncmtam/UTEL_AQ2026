# Chạy thử AGQO V3

[Mở prototype công khai](https://data1--agqo-demo.us-east.modal.run/) để dùng thử trên dữ liệu lịch sử. Các lệnh bên dưới chạy từ thư mục gốc của snapshot V3.

## Cài đặt và chạy trên máy

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[web,quantum,dev]'
python -m agqo --version
```

Trên Windows PowerShell, dùng `.venv\Scripts\Activate.ps1`. Cài toàn bộ công cụ phát triển, kể cả tạo hồ sơ và mô phỏng nhiễu, bằng `python -m pip install -r requirements.txt`.

Đặt bản giá được phép sử dụng tại `data/vn30/ohlcv_daily.csv`. Xem [cách chuẩn bị dữ liệu](data/vn30/README.md) để biết khi nào cần đúng snapshot lưu trong manifest. Sau khi có dữ liệu:

```bash
python -m pytest -q
AGQO_LIVE_LLM=0 python -m uvicorn app.server:api --port 8000
```

Mở [localhost:8000](http://localhost:8000). Trên PowerShell, đặt `$env:AGQO_LIVE_LLM = '0'` ở dòng riêng trước khi chạy Uvicorn. Chế độ này dùng câu trả lời Qwen đã lưu cho các ví dụ có trong nhật ký và quy tắc từ khóa cho câu mới. QAOA chạy mô phỏng trên CPU.

## Đối chiếu bằng chứng đã lưu

Giữ `results/final/` làm mốc và phát lại LLM trên một bản sao. Các lệnh Bash/zsh sau dùng nhật ký đã ghi và không gọi GPU:

```bash
run_dir=$(mktemp -d)
cp -R results/final/. "$run_dir/"
python -m agqo mandates --llm replay --out "$run_dir"
python -m agqo explain --llm replay --out "$run_dir"
python -m agqo hardware --qasm results/final/circuits/agqo_2026-10-01.qasm
```

Phép kiểm tra mạch chỉ đọc OpenQASM nếu không có `--confirm`. Các bảng đã lưu được mô tả trong [kết quả V3](docs/RESULTS.md).

## Chạy thí nghiệm mới

Ghi ra một thư mục mới. Để gọi Qwen trực tiếp, cài `.[llm]`, đăng nhập Modal và chạy `modal run modal_app.py::download_weights` rồi `modal deploy modal_app.py` một lần. Để chạy các nghiên cứu mô phỏng nhiễu, cài `.[studies]`.

```bash
run_dir=$(mktemp -d)
python -m agqo mandates --llm modal --out "$run_dir"
python -m agqo run --out "$run_dir"
python -m agqo explain --llm modal --out "$run_dir"
python -m agqo extras --run "$run_dir"
python -m agqo report --run "$run_dir" --out "$run_dir/figures" --document "$run_dir/RESULTS.md"
```

Phát lại LLM khớp theo nội dung yêu cầu đã lưu. Nếu dữ liệu hoặc đầu vào thay đổi, cần tạo nhật ký cho lần chạy mới.
