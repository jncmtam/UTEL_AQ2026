# Bàn giao hồ sơ vòng bán kết (đội AQ2026-169)

## Tệp nộp (thư mục `submission/final/`, không đưa lên Git)

| Mục nộp | Tệp | Kiểm tra |
|---|---|---|
| Báo cáo giải pháp | AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.pdf (2,8 MB; kèm .docx) | 12 trang (PDF xuất từ Word), theo mẫu BTC, đã điền thông tin đội |
| Slide trình bày | AQ2026-R2-AQ2026-169-Slide.pptx (0,4 MB) | Bìa + 8 slide chính + 13 phụ lục; chữ, biểu đồ, sơ đồ chỉnh được; ghi chú người nói. PDF dự phòng kèm theo |
| Mã nguồn và dữ liệu chạy thử | AQ2026-R2-AQ2026-169-Ma_nguon.zip (~18 MB) | `git archive` của commit chứa ghi chú này (phiên bản 1.0.0, cấu trúc thư mục mới); giải nén, đặt tệp giá, mã băm khớp, 58/58 test pass trên Modal |
| Hướng dẫn cài đặt và sử dụng | AQ2026-R2-AQ2026-169-Huong_dan.pdf (4 trang; kèm .docx) | Có URL prototype, ghi rõ không cần tài khoản thử nghiệm |
| Đường dẫn prototype | https://data1--agqo-prototype.us-east.modal.run | Ứng dụng Modal `agqo-prototype`; luồng mẫu chạy thật ngày 20/11/2026 (job 8 giây). Các địa chỉ cũ (`agqo-demo`, `agqo-v32`) vẫn chạy nhưng không còn nằm trong hồ sơ |

## Đã kiểm tra

- Số liệu khớp giữa deck, báo cáo và hướng dẫn (22 con số tiêu đề, dò tự động trên PDF); không còn câu “thị trường cấm lô lẻ”; không
  còn chỗ trống của mẫu ngoài trang hướng dẫn gốc của BTC.
- Xem từng trang deck và báo cáo sau khi xuất PDF (cắt chữ, cỡ chữ, dấu tiếng Việt, nhãn biểu đồ).
- Sửa thử một tiêu đề, một số liệu biểu đồ, một nhãn sơ đồ trong PPTX: bố cục giữ nguyên.
- Tập dượt trên bản đã triển khai: nút Chạy khóa trước khi xác nhận; job Modal 14 giây khi container nguội, 5–11 giây khi ấm; câu
  mơ hồ bị khóa để hỏi lại; yêu cầu “mỗi mã ≤ 2%” báo không khả thi. Đường phát lại có kiểm thử riêng (`tests/test_app.py`).

## Số liệu đã tính lại cho vòng này

Ca thuyết trình (20 triệu, bỏ bất động sản, ngân hàng ≤ 30%), sai số bám theo cỡ tài khoản kèm thuật toán tham lam, kiểm thử,
tái hiện lỗi, thăm dò Qwen với câu phủ định. Danh sách đầy đủ và nguồn: `docs/submission/SO_DANG_KY_BANG_CHUNG.md`.

## Đội cần xác nhận trước khi nộp

1. **Dữ liệu mẫu trong ZIP (đã quyết 20/11/2026: giữ như hiện tại).** ZIP có thành phần VN30, manifest và toàn bộ kết quả đã lưu, không có tệp giá DNSE (không có quyền phân phối lại); hướng dẫn chỉ lệnh `python -m agqo download` và kiểm tra mã băm.
2. **Giảng viên hướng dẫn:** báo cáo ghi “Không có”.
3. **Thành viên (cập nhật 20/11/2026):** đội còn 3 người: Chu Minh Tâm (đội trưởng), Đặng Nguyễn An Nhiên, Phạm Mạnh
   Quyền. Bìa, bảng thành viên và slide đọc danh sách từ `submission/team.local.json`.
4. **Thời lượng trình bày:** chưa có thông báo của BTC trong máy; deck có bản đầy đủ (~8–9 phút) và bản 3 phút.
5. **Demo dùng câu trả lời Qwen đã lưu** (có nhãn “phát lại”) vì GPU khởi động lạnh mất ~440 giây; phần tối ưu chạy trực tiếp.
6. Prototype phải chạy được trong thời gian chấm: ứng dụng Modal `agqo-prototype` đang triển khai; nên kiểm tra hạn mức chi tiêu Modal.

## Sửa an toàn

Xem `submission/deck/EDIT_MAP.md`. Sửa tay trên bản PPTX trong `submission/final/`; chạy lại script chỉ tạo bản mới trong
`submission/drafts/`, không đè bản đã sửa. Thông tin cá nhân của đội nằm ở `submission/team.local.json` (không đưa lên Git).
