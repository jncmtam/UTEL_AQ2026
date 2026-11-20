# AGQO V3.2

AGQO giúp nhà đầu tư mô phỏng danh mục bám VN30 theo quy tắc riêng và giao dịch theo lô chẵn. Hệ thống chuyển yêu cầu tiếng Việt thành ràng buộc, so sánh cách chọn lô bằng QAOA mô phỏng với các phương pháp cổ điển, rồi kiểm tra danh mục và hiển thị danh sách lệnh dự kiến.

- **V3.2:** [prototype tương tác chạy job Modal thật](https://data1--agqo-v32.us-east.modal.run/), [kết quả V3.2 dễ đọc](docs/vi/KET_QUA_V3_2.md) và [bản ghi nghiên cứu](docs/RESULTS_V3_2.md), [giao thức đánh giá](docs/research/PROTOCOL_V3_2.md), [nhật ký làm việc](agent.md)
- **Hướng dẫn V3.2:** [cài Modal và triển khai](docs/vi/HUONG_DAN_MODAL.md), [chạy lại nghiên cứu](docs/vi/NGHIEN_CUU_MODAL.md), [demo vòng chung kết](docs/vi/DEMO_VONG_CHUNG_KET.md), [lộ trình](docs/vi/LO_TRINH.md)
- [Chạy thử và tái lập thí nghiệm V3](CHAY_THU.md)
- [Web demo V3 đã nộp vòng 2](https://data1--agqo-demo.us-east.modal.run/)
- [Thiết kế và các kết quả chính](docs/TECHNICAL_OVERVIEW.md), [phương pháp](docs/METHODS.md) và [bảng kết quả](docs/RESULTS.md)
- [Tài liệu và mã tạo hồ sơ dự thi](submission/README.md), [kịch bản trình bày](docs/KICH_BAN_THUYET_TRINH.md) và [câu hỏi phản biện](docs/QA.md)

## V3.2 thay đổi gì

- **Tin cậy hơn:** mọi trần tỷ trọng kiểm tra trên giá trị tài khoản sau phí; yêu cầu không khả thi được giải thích
  thay vì gây lỗi; “chỉ giữ 1 mã” chạy bằng tìm kiếm chính xác; câu mơ hồ hoặc mâu thuẫn phải được trả lời trước khi
  có lệnh; bộ kiểm tra lời giải thích bắt được số gán nhầm phương án hoặc sai đơn vị.
- **Dùng được trong buổi thi:** chọn mẫu hoặc gõ yêu cầu → các ô ràng buộc có nhãn nguồn (bạn nhập, từ mẫu, từ câu
  lệnh, chưa đặt) → bấm Chạy → một job Modal thật với tiến trình, lỗi và nút thử lại; kết quả ghi rõ chạy thật, phát
  lại hay dự phòng.
- **Nghiên cứu chạy lại trên Modal**, đăng ký giao thức trước khi mở tập holdout: LLM đọc yêu cầu đúng đầu-cuối 49/50
  câu mới (từ khóa 33/50; bộ câu do nhóm viết); k-NN hơn lịch cố định +0,76 điểm % nhưng chỉ bằng quy tắc “một lịch
  cho mỗi cỡ tài khoản”; mạch do LLM thiết kế hơn tìm kiếm ngẫu nhiên nhưng thua lịch chọn bằng dữ liệu; lợi thế ở
  tài khoản 20 triệu giữ được khi giả định giá lô lịch sử cao hơn tới 50%.

## Cấu trúc mã nguồn

| Vị trí | Nội dung |
| --- | --- |
| `agqo/` | Lõi V3, từ tải dữ liệu, lập danh mục và kiểm định đến CLI `python -m agqo` |
| `agqo/llm/`, `modal_app.py` | Ràng buộc tiếng Việt, lời giải thích, phát lại nhật ký và phục vụ Qwen trên Modal |
| `agqo/quantum/` | Mô phỏng QAOA, thiết kế mạch, xuất OpenQASM và đường chạy IBM tùy chọn |
| `app/` | Prototype FastAPI, giao diện và cấu hình deploy web (`app/modal_web.py`: trang + job `decide_job`) |
| `agqo/research/`, `modal_research.py`, `notebooks/` | Nghiên cứu V3.2: tái hiện lỗi, k-NN, thí nghiệm LLM, preset, benchmark; mọi phép mô phỏng chạy trên Modal CPU qua notebook |
| `results/runs/`, `results/v32/` | Mỗi lần chạy V3.2 một thư mục (`run.json` ghi commit, mã băm dữ liệu, cấu hình, lỗi); dữ liệu ứng dụng phát lại |
| `data/vn30/` | Thành phần VN30 theo thời điểm và manifest của bộ giá lịch sử |
| `results/final/` | Kết quả và nhật ký của thí nghiệm V3 đã lưu |
| `docs/`, `submission/`, `tests/` | Tài liệu nghiên cứu, mã dựng hồ sơ và kiểm thử |

## Phiên bản và lịch sử

`main` là nhánh chính. V3.2 phát triển từ thẻ `v3.1.0`. Số phiên bản mà CLI và gói Python cùng sử dụng nằm trong `agqo/__init__.py` và có thể kiểm tra bằng `python -m agqo --version`. Các mốc trước hợp nhất nằm trên các nhánh `archive/`. Chúng giữ lịch sử nghiên cứu và đường lui cho từng phiên bản.

Kết quả V3 là bằng chứng nghiên cứu trên dữ liệu lịch sử. Liệt kê chính xác dùng để kiểm chứng nghiệm trong thanh ghi 16 qubit. Các kết quả lượng tử được đo bằng mô phỏng và không chứng minh ưu thế lượng tử. Xem [giới hạn](docs/TECHNICAL_OVERVIEW.md#21--discussion-what-it-means) và [phạm vi dữ liệu](data/vn30/README.md).
