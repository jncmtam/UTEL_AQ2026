# AGQO V3

AGQO giúp nhà đầu tư mô phỏng danh mục bám VN30 theo quy tắc riêng và giao dịch theo lô chẵn. Hệ thống chuyển yêu cầu tiếng Việt thành ràng buộc, so sánh cách chọn lô bằng QAOA mô phỏng với các phương pháp cổ điển, rồi kiểm tra danh mục và hiển thị danh sách lệnh dự kiến.

- [Chạy thử và tái lập thí nghiệm](CHAY_THU.md)
- [Web demo công khai](https://data1--agqo-demo.us-east.modal.run/)
- [Thiết kế và các kết quả chính](docs/TECHNICAL_OVERVIEW.md), [phương pháp](docs/METHODS.md) và [bảng kết quả](docs/RESULTS.md)
- [Tài liệu và mã tạo hồ sơ dự thi](submission/README.md), [kịch bản trình bày](docs/KICH_BAN_THUYET_TRINH.md) và [câu hỏi phản biện](docs/QA.md)

## Cấu trúc mã nguồn

| Vị trí | Nội dung |
| --- | --- |
| `agqo/` | Lõi V3, từ tải dữ liệu, lập danh mục và kiểm định đến CLI `python -m agqo` |
| `agqo/llm/`, `modal_app.py` | Ràng buộc tiếng Việt, lời giải thích, phát lại nhật ký và phục vụ Qwen trên Modal |
| `agqo/quantum/` | Mô phỏng QAOA, thiết kế mạch, xuất OpenQASM và đường chạy IBM tùy chọn |
| `app/` | Prototype FastAPI, giao diện và cấu hình deploy web |
| `data/vn30/` | Thành phần VN30 theo thời điểm và manifest của bộ giá lịch sử |
| `results/final/` | Kết quả và nhật ký của thí nghiệm V3 đã lưu |
| `docs/`, `submission/`, `tests/` | Tài liệu nghiên cứu, mã dựng hồ sơ và kiểm thử |

## Phiên bản và lịch sử

`main` là nhánh chính của V3. Số phiên bản mà CLI và gói Python cùng sử dụng nằm trong `agqo/__init__.py` và có thể kiểm tra bằng `python -m agqo --version`. Các mốc trước hợp nhất nằm trên các nhánh `archive/`. Chúng giữ lịch sử nghiên cứu và đường lui cho từng phiên bản.

Kết quả V3 là bằng chứng nghiên cứu trên dữ liệu lịch sử. Liệt kê chính xác dùng để kiểm chứng nghiệm trong thanh ghi 16 qubit. Các kết quả lượng tử được đo bằng mô phỏng và không chứng minh ưu thế lượng tử. Xem [giới hạn](docs/TECHNICAL_OVERVIEW.md#21--discussion-what-it-means) và [phạm vi dữ liệu](data/vn30/README.md).
