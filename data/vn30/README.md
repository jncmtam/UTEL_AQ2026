# Dữ liệu VN30 của AGQO

- `vn30_membership_history.csv` ghi thành phần theo ngày hiệu lực. `vn30_membership_events.csv` và tệp mốc đi kèm lưu các thay đổi, nguồn đối chiếu.
- `manifest.json` mô tả tập giá dùng cho mọi kết quả trong repository, gồm phạm vi, SHA-256 và giả định về điều chỉnh giá.
- `ohlcv_daily.csv` là đầu vào giá của bộ kiểm thử, demo cục bộ và các phép chạy lại. Tệp này nằm ngoài Git và ZIP mã nguồn. Chỉ dùng hoặc chia sẻ dữ liệu theo quyền áp dụng cho nguồn.

Để đối chiếu đúng kết quả đã lưu, dùng snapshot được phép sử dụng, có SHA-256 khớp `manifest.json` và `results/final/run_manifest.json`. Lệnh `python -m agqo verify-data --run results/final` kiểm tra cả hai mốc.

Nếu quyền sử dụng nguồn cho phép, `python -m agqo download --start 2022-01-01 --end 2026-11-15` tạo tệp giá và manifest từ nhà cung cấp. Lệnh ghi vào thư mục này, nên lưu riêng snapshot cũ trước khi tải. Dữ liệu lấy lại có thể khác snapshot đã dùng do nhà cung cấp cập nhật chuỗi lịch sử. [Hướng dẫn cài đặt](../../README.md#5-cài-đặt)
