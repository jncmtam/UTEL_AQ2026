# Chạy lại nghiên cứu V3.2 trên Modal

Mọi thí nghiệm V3.2 chạy qua một notebook: `notebooks/AGQO_V3_2_Research_Modal.ipynb`. Notebook chỉ gửi việc sang
Modal và lưu bản sao kết quả; phần tính toán nằm trong container Modal. Cần làm xong các bước 2–4 của
[hướng dẫn Modal](HUONG_DAN_MODAL.md) trước.

## 1. Chạy notebook

Cách 1, mở trong Jupyter hoặc Modal Notebooks rồi chạy từng ô theo thứ tự. Đổi danh sách `TASKS` ở ô tham số.

Cách 2, chạy không cần giao diện bằng papermill từ thư mục gốc dự án. Mỗi lần chạy lưu một bản notebook đã thực thi
làm bằng chứng:

```bash
papermill notebooks/AGQO_V3_2_Research_Modal.ipynb results/runs/notebooks/$(date -u +%Y%m%d-%H%M%S)-run.ipynb -k agqo-venv -p TASKS '["smoke","pytest"]'
```

Lần đầu cần đăng ký nhân Jupyter của môi trường ảo:

```bash
python -m ipykernel install --user --name agqo-venv
```

Nếu sửa nội dung notebook, sửa trong `notebooks/build_notebook.py` rồi tạo lại notebook:

```bash
python notebooks/build_notebook.py
```

## 2. Các việc (TASKS) và ý nghĩa

| TASK | Chạy ở đâu | Làm gì | Thời gian |
|---|---|---|---|
| `smoke` | Modal CPU | Kiểm tra image, mã băm SHA-256 của tệp giá | < 1 phút |
| `reproduce` | Modal CPU | Chạy lại các ca lỗi đã báo (trần ngân hàng sau phí, giữ 1 mã, yêu cầu không khả thi, câu mơ hồ, bộ kiểm tra lời giải thích) | < 1 phút |
| `pytest` | Modal CPU | Toàn bộ bộ kiểm thử, kể cả các phép mô phỏng mạch | < 1 phút |
| `knn_table` | Modal CPU, ~100 container | Chấm điểm 1.080 lịch mạch trên 690 bài toán | ~6 phút |
| `knn_study` | Notebook (chỉ đọc bảng) | Chẩn đoán, chọn biến thể k-NN trên tập validation, đánh giá holdout | < 1 phút |
| `knn_refine` | Modal CPU | Tinh chỉnh cục bộ COBYLA so với không tinh chỉnh, trên 330 bài toán holdout | ~1 phút |
| `llm_mandates` | Modal H100 + CPU | Qwen đọc 50 yêu cầu tiếng Việt với hai prompt; mỗi kết quả chạy qua bộ tối ưu | 10–15 phút (gồm khởi động GPU) |
| `llm_circuits` | Modal H100 + CPU | Qwen đề xuất mạch hai vòng; so với tìm kiếm ngẫu nhiên cùng ngân sách | 10–20 phút |
| `presets` | Modal CPU | Đo từng mẫu của ứng dụng; lưu kết quả để ứng dụng phát lại | ~3 phút |
| `account_benchmark` | Modal CPU | Tài khoản 20 triệu và giới hạn do giá đã điều chỉnh | ~3 phút |

## 3. Tìm kết quả

Mỗi lần chạy tạo một thư mục `results/runs/<run_id>/`, với `run_id = <giờ UTC>-<mã commit>-<loại việc>`.
Bản sao cũng nằm trên Modal Volume `agqo-v32-runs`. Trong mỗi thư mục:

- `run.json`: mã commit, cờ “dirty” (có thay đổi chưa commit hay không), mã băm dữ liệu, cấu hình, các bước, lỗi và
  trạng thái `ok`, `partial` hoặc `failed`. Lần chạy hỏng vẫn được giữ.
- `log.txt`: tiến trình theo thời gian.
- Tệp kết quả, ví dụ `holdout_results.json`, `mandate_eval_v2.json`, `circuit_llm.json`, `presets.json`.
- `llm_log.jsonl` (thí nghiệm LLM): từng lời gọi với prompt hệ thống, câu hỏi, câu trả lời thô, trạng thái, số token,
  mô hình và GPU.

Xem nhanh một lần chạy:

```bash
python -c "import json,sys; m=json.load(open(sys.argv[1])); print(m['status'], m.get('summary'))" results/runs/<run_id>/run.json
```

## 4. Phát lại thí nghiệm LLM không cần GPU

Nhật ký `llm_log.jsonl` cho phép phát lại đúng từng câu trả lời: `LLMClient("replay", ..., replay_from=<log>)` tìm câu
trả lời theo mã băm của yêu cầu (prompt hệ thống, câu hỏi, lược đồ, seed, nhiệt độ). Nếu prompt hay dữ liệu thay đổi,
mã băm đổi và cần gọi lại GPU.

## 5. Đọc kết quả cho đúng

- **Tỷ lệ thành công của mạch** là xác suất một lần đo cho ra danh mục đủ tiền và cách tối ưu không quá 5%. Tối ưu
  được biết chính xác vì máy tính cổ điển liệt kê đủ 2^16 tổ hợp; vì vậy không có kết quả nào ở đây là “ưu thế lượng tử”.
- **Đơn vị kiểm định là ngày.** Các bài toán cùng một ngày được lấy trung bình trước khi so sánh cặp, để không thổi phồng
  số mẫu.
- **Tập holdout chỉ mở một lần**, sau khi đã chọn biến thể trên tập validation. Mọi thay đổi sau đó ghi ở mục 8 của
  [giao thức](../research/PROTOCOL_V3_2.md).
- **Bộ câu tiếng Việt do nhóm viết.** Kết quả cho biết trình phân tích xử lý cách diễn đạt thực tế ra sao, chưa thay
  được thử nghiệm với người dùng độc lập.
- **Giá lịch sử đã được điều chỉnh** cổ tức và chia tách. Xem mục giới hạn trong [kết quả V3.2](../RESULTS_V3_2.md).

## 6. Khi gặp lỗi

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `You can't iter(Function.map()) from an async function` | Gọi `.map()` thẳng trong nhân Jupyter | Dùng `fanout(...)` trong `agqo/research/orchestrate.py` (đã làm sẵn trong notebook) |
| `weights missing` khi gọi LLM | Chưa tải trọng số Qwen | `modal run modal_app.py::download_weights` |
| Lời gọi LLM chờ 5–7 phút | GPU đang khởi động lần đầu | Bình thường; lần sau nhanh hơn nếu container còn bật |
| `run.json` có `"dirty": true` | Có thay đổi chưa commit lúc chạy | Commit rồi chạy lại nếu cần kết quả gắn chặt với một commit |
| Một số mạch bị loại với `layers=… outside` | Vượt giới hạn của bộ kiểm tra mạch | Bộ kiểm tra cho phép 1–8 lớp, ≤ 1.500 cổng hai qubit, ≤ 60 lần đánh giá |
