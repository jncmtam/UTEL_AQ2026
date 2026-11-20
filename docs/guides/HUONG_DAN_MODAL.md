# Cài đặt Modal và triển khai ứng dụng AGQO

Tài liệu này dành cho người lần đầu chạy AGQO trên Modal. Đọc từ trên xuống một lần là đủ để tự triển khai trang web
và kết nối nó với các job tính toán.

## 1. Modal là gì và AGQO dùng nó thế nào

Modal là dịch vụ chạy mã Python trên máy chủ đám mây. Bạn viết một hàm Python, gắn nhãn `@app.function`, rồi
Modal tự dựng container (một "máy ảo" nhỏ có đủ thư viện), chạy hàm và trả kết quả. Máy chỉ được bật khi có việc,
nên chỉ tốn tiền trong lúc chạy.

AGQO dùng ba ứng dụng Modal:

| Ứng dụng | Tệp | Phần cứng | Việc nó làm |
|---|---|---|---|
| `agqo-prototype` | `app/modal_web.py` | CPU | Phục vụ trang web; mỗi lần bấm **Chạy** sinh một job `decide_job` trong container CPU riêng |
| `agqo-llm` | `modal_app.py` | GPU H100 | Chạy mô hình ngôn ngữ Qwen3.8-27B để đọc yêu cầu tiếng Việt và viết lời giải thích |
| `agqo-research` | `modal_research.py` | CPU | Mọi phép mô phỏng mạch lượng tử, kiểm thử và chạy lại nghiên cứu |

Máy tính của bạn chỉ gửi lệnh và nhận kết quả. Không phép mô phỏng mạch nào chạy trên máy cá nhân.

## 2. Cài đặt lần đầu

```bash
python3.12 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
python -m pip install -e '.[web,llm,quantum,dev]' papermill ipykernel
```

Đặt tệp giá được phép sử dụng vào `data/vn30/ohlcv_daily.csv` (xem `data/vn30/README.md`), rồi kiểm tra:

```bash
python -m agqo verify-data --run results/final
```

## 3. Đăng nhập Modal an toàn

```bash
modal token new
```

Lệnh này mở trình duyệt để bạn đăng nhập. Modal lưu khóa truy cập (token) vào tệp `~/.modal.toml` trong thư mục
người dùng, **không** nằm trong thư mục dự án, nên không bị đưa lên Git. Vài nguyên tắc:

- Không dán token vào mã nguồn, notebook, tin nhắn hay ảnh chụp màn hình.
- Không đặt token trong biến môi trường của tệp `.env` trong dự án nếu tệp đó có thể bị chia sẻ.
- Nếu nghi token bị lộ, vào trang Settings → API Tokens trên modal.com, thu hồi token cũ và chạy lại `modal token new`.
- Dùng một workspace Modal riêng cho cuộc thi để dễ theo dõi chi phí; đặt giới hạn chi tiêu trong trang Usage.

Kiểm tra đã đăng nhập:

```bash
modal profile current
```

## 4. Triển khai mô hình ngôn ngữ (một lần)

Tải trọng số Qwen3.8-27B (khoảng 31 GB) vào Volume của Modal, rồi triển khai:

```bash
modal run modal_app.py::download_weights
```

```bash
modal deploy modal_app.py
```

GPU chỉ bật khi có yêu cầu. Lần đầu sau khi nghỉ, mô hình mất khoảng 6 phút để nạp. Một H100 tốn khoảng 4 USD mỗi giờ
khi đang bật; container tự tắt sau 5 phút không có việc.

## 5. Triển khai trang web và job tính toán

```bash
modal deploy app/modal_web.py
```

Lệnh in ra địa chỉ dạng `https://<workspace>--agqo-prototype.us-east.modal.run` (ứng dụng và nhãn đều tên
`agqo-prototype`). Muốn triển khai dưới tên khác, đặt biến môi trường:

```bash
AGQO_WEB_APP=<tên-ứng-dụng> AGQO_WEB_LABEL=<nhãn-url> modal deploy app/modal_web.py
```

Trang web và job được kết nối như sau: trang gọi `POST /api/run`; máy chủ web gọi `decide_job.spawn(...)` của chính
ứng dụng đó trên Modal; job ghi từng bước vào `modal.Dict` tên `agqo-progress`; trang hỏi `GET /api/run/{id}`
mỗi giây để cập nhật thanh tiến trình và nhận kết quả.

Biến môi trường điều chỉnh hành vi (đặt trong `app/modal_web.py` hoặc khi chạy cục bộ):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AGQO_LIVE_LLM` | `1` | `0`: không bao giờ bật GPU; dùng câu trả lời Qwen đã lưu hoặc quy tắc từ khóa |
| `AGQO_LLM_PER_HOUR` | `40` | Giới hạn số lần gọi LLM mỗi giờ để chặn chi phí ngoài ý muốn |
| `AGQO_COMPUTE` | `modal` | `replay`: chỉ phát lại kết quả preset đã lưu, không tính mới |
| `AGQO_ALLOW_LOCAL_COMPUTE` | `0` | `1`: cho phép tính ngay trong máy chủ web khi Modal lỗi (chỉ để phát triển; kết quả bị gắn nhãn “dự phòng”) |

## 6. Chạy trang web trên máy để phát triển

Trang vẫn gửi mọi lần chạy sang Modal (cần bước 5 trước):

```bash
AGQO_LIVE_LLM=0 uvicorn app.server:api --port 8000
```

Mở `http://localhost:8000`. Nếu Modal không gọi được, các preset vẫn chạy bằng chế độ phát lại và được ghi rõ nhãn.

## 7. Chi phí tham khảo

| Việc | Phần cứng | Thời gian | Chi phí ước tính |
|---|---|---|---|
| Một lần bấm Chạy | 2 CPU | 5–15 giây (khởi động container lần đầu thêm 20–60 giây) | dưới 0,01 USD |
| Bảng k-NN (690 bài toán × 1.080 lịch) | CPU | 7,2 giờ máy (2 CPU mỗi container), khoảng 6 phút thực | khoảng 0,5–1 USD |
| Thí nghiệm LLM (một lượt) | 1 H100 | 10–20 phút | 1–2 USD |
