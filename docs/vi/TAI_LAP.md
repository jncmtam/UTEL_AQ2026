# AGQO – Hướng dẫn tái lập kỹ thuật

## 1. Cài đặt

Cần Python 3.12, khoảng 8 GB RAM. Từ thư mục gốc của mã nguồn:

```bash
python3.12 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
python -m pip install -e '.[web,llm,quantum,dev]' papermill ipykernel pyyaml python-pptx python-docx pymupdf
```

## 2. Dữ liệu giá và kiểm tra mã băm

Tệp giá `data/vn30/ohlcv_daily.csv` không nằm trong mã nguồn vì nguồn dữ liệu không cấp quyền phân phối lại. Có hai cách:

1. Dùng snapshot được phép sử dụng mà đội cung cấp riêng (đúng snapshot của mọi kết quả), rồi kiểm tra:

```bash
python -m agqo verify-data --run results/final
```

Lệnh in `VN30 price snapshot verified: 7f076128…3042` nếu đúng.

2. Tải lại từ nhà cung cấp (nếu quyền sử dụng cho phép). Dữ liệu tải lại có thể khác snapshot vì nhà cung cấp cập nhật chuỗi lịch sử;
khi đó mã băm khác và kết quả có thể lệch nhẹ:

```bash
python -m agqo download --start 2022-01-01 --end 2026-11-15
```

## 3. Kiểm tra bằng chứng đã lưu, không cần GPU

- Bằng chứng V3: `results/final/` (không sửa). Bằng chứng V3.2: `results/runs/<run_id>/`, mỗi thư mục có `run.json` ghi commit, mã băm
  dữ liệu, cấu hình, các bước và lỗi.
- Phát lại LLM từ nhật ký (không gọi GPU), ghi ra thư mục tạm:

```bash
run_dir=$(mktemp -d) && cp -R results/final/. "$run_dir/" && python -m agqo mandates --llm replay --out "$run_dir"
```

## 4. Chạy thí nghiệm mới (ghi ra chỗ riêng, không đè bằng chứng)

Mọi mô phỏng mạch chạy trên Modal CPU qua notebook; máy cá nhân chỉ gửi việc. Đăng nhập Modal một lần (`modal token new`) và xem
[HUONG_DAN_MODAL.md](HUONG_DAN_MODAL.md). Ví dụ chạy kiểm thử và ca thuyết trình:

```bash
papermill notebooks/AGQO_V3_2_Research_Modal.ipynb results/runs/notebooks/$(date -u +%Y%m%d-%H%M%S)-run.ipynb -k agqo-venv -p TASKS '["pytest","pitch"]'
```

Mỗi lần chạy tạo thư mục mới `results/runs/<giờ UTC>-<commit>-<loại>/`; danh sách TASKS và cách đọc kết quả ở
[NGHIEN_CUU_MODAL.md](NGHIEN_CUU_MODAL.md).

## 5. Chạy prototype

Triển khai lên Modal (trang web + job tính toán):

```bash
modal deploy app/modal_web.py
```

Chạy trang trên máy (mọi lần bấm Chạy vẫn gửi job sang Modal; nếu không có Modal, mẫu dùng bản phát lại có nhãn):

```bash
AGQO_LIVE_LLM=0 uvicorn app.server:api --port 8000
```

## 6. Dựng lại hồ sơ dự thi

```bash
python submission/deck/make_data.py && python submission/deck/figures.py
```

```bash
python submission/deck/build_deck.py
```

```bash
python submission/report/build_report_v32.py
```

Mỗi lệnh ghi vào một thư mục mới trong `submission/drafts/`, không bao giờ ghi đè bản đã sửa tay. Xem `submission/deck/EDIT_MAP.md`.

## 7. Kết quả mong đợi khi tái lập

| Kiểm tra | Mong đợi |
|---|---|
| `pytest` trên Modal | 58 passed |
| Tái hiện lỗi (`reproduce`) | 0 exceptions, 0 silent cap breaches |
| Ca thuyết trình (`pitch`), 12 quý, có hai quy tắc | làm tròn 12,67% · tham lam 9,82% · AGQO 9,91% |
| Tài khoản 20 triệu, không quy tắc | làm tròn 12,14% · tham lam 7,47% · AGQO 6,77% |
