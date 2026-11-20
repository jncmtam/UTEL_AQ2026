# Kịch bản demo vòng chung kết

Mục tiêu: trong 3–4 phút, giám khảo tự chọn một mẫu hoặc gõ yêu cầu, xem ràng buộc được hiểu ra sao, bấm **Chạy** và
nhận kết quả từ một job Modal thật.

Địa chỉ: https://data1--agqo-v32.us-east.modal.run (ứng dụng `agqo-web-v32`). Địa chỉ vòng 2 (`agqo-demo`) vẫn
giữ bản V3 cũ.

## 1. Chuẩn bị (30 phút trước)

1. Mở trang một lần để container web khởi động.
2. Bấm chạy mẫu “Tài khoản nhỏ 20 triệu” một lần để container `decide_job` khởi động (lần đầu mất 20–60 giây,
   các lần sau 5–15 giây).
3. Nếu muốn dùng Qwen trực tiếp: gõ một câu mới (chưa có trong nhật ký) ở bước 2 và bấm “Diễn giải” với ô “Gọi Qwen3.8”
   được chọn, để GPU khởi động (khoảng 6 phút). Sau 5 phút không dùng, GPU tự tắt.
4. Muốn container luôn sẵn sàng trong buổi thi: trên modal.com, mở ứng dụng `agqo-web-v32`, hàm `decide_job`, đặt
   “min containers” = 1 trong thời gian thi rồi trả về 0. Việc này tốn tiền trong lúc bật.
5. Mở sẵn một tab dự phòng với `?preset=bank25_200&run=1&live=0`: trang tự chọn mẫu và chạy.

## 2. Luồng trình bày đề xuất

| Bước | Thao tác | Điều cần nói |
|---|---|---|
| 1 | Kéo thanh số vốn ở mục 01 | Với 20 triệu, một lô VIC chiếm hơn 100% vốn; làm tròn từng mã làm lệch danh mục |
| 2 | Chọn mẫu “200 triệu, ngân hàng tối đa 25%” | Các ô được điền và gắn nhãn “Từ mẫu”; ô chưa đặt ghi rõ mặc định |
| 3 | Bấm **Chạy trên Modal** | Thanh tiến trình hiện từng bước trong container Modal: kiểm tra khả thi → QUBO → k-NN chọn lịch → QAOA → kiểm tra trên NAV sau phí |
| 4 | Đọc kết quả | Nhãn “Chạy thật trên Modal”; lệnh mua, phí, tiền mặt còn lại; ngân hàng thực tế dưới 25% tính trên NAV sau phí; so sánh với làm tròn |
| 5 | Chọn mẫu “Câu mơ hồ” | Hệ thống hỏi lại, nút Chạy bị khóa, không có lệnh nào; trả lời “tối đa 25%” → ô trần ngân hàng được điền “Từ câu lệnh” |
| 6 | Chọn mẫu “Mỗi mã tối đa 2%” | Kết quả “không khả thi” và nêu đúng quy tắc chặn: 2% của 20 triệu nhỏ hơn một lô rẻ nhất |
| 7 | Mở “Bên trong quyết định này” (tuỳ thời gian) | Hamiltonian, mạch, phân bố xác suất, đối chiếu với liệt kê toàn bộ |

Câu nên nói về lượng tử: “Ở 16 qubit, máy tính cổ điển liệt kê hết 65.536 tổ hợp trong chưa tới một giây. Chúng tôi
dùng chính phép liệt kê đó để kiểm chứng từng quyết định. Mạch QAOA được thiết kế để dồn xác suất vào nghiệm tốt;
chúng tôi không tuyên bố ưu thế lượng tử.”

## 3. Nhãn kết quả nghĩa là gì

| Nhãn | Ý nghĩa |
|---|---|
| ● Chạy thật trên Modal | Kết quả vừa được tính trong container Modal; có mã container và thời gian |
| ↺ Phát lại kết quả Modal đã lưu | Không khởi động được job; trang hiện kết quả của lần chạy Modal đã lưu cho đúng mẫu đó, kèm mã lần chạy |
| ⚠ Dự phòng | Tính ngay trong máy chủ web (chỉ khi bật `AGQO_ALLOW_LOCAL_COMPUTE=1`); không dùng khi thi |

## 4. Xử lý sự cố nhanh

| Hiện tượng | Cách xử lý |
|---|---|
| Thanh tiến trình đứng ở “Đang xếp hàng” quá 60 giây | Container đang khởi động hoặc Modal chậm. Chờ thêm, hoặc bấm **Thử lại** khi trang báo lỗi |
| Trang báo “Không khởi động được job trên Modal” | Kiểm tra mạng; chọn một mẫu (mẫu có bản phát lại); nói rõ với giám khảo đây là bản phát lại |
| Trang báo “Không tìm thấy lần chạy này” | Máy chủ web vừa khởi động lại; bấm chạy lại |
| Qwen không trả lời sau vài phút | GPU khởi động lần đầu mất khoảng 6 phút; kết quả quy tắc từ khóa đã hiện sẵn, có thể chạy ngay |
| Nút Chạy bị mờ | Còn câu hỏi làm rõ chưa trả lời, hoặc một ô có giá trị không hợp lệ (dòng chữ vàng dưới form) |
| Trang trắng hoặc lỗi tải dữ liệu | Tải lại trang; nếu vẫn lỗi, chạy `modal deploy app/modal_web.py` từ thư mục dự án |

## 5. Những điều không nên hứa

- Sai số bám là ước tính trước giao dịch trên dữ liệu lịch sử, không phải dự báo lợi nhuận.
- Giá lịch sử là giá đã điều chỉnh; con số ở tài khoản nhỏ có giới hạn này (xem [kết quả V3.2](../RESULTS_V3_2.md)).
- Bộ câu tiếng Việt dùng để đo LLM do nhóm viết, chưa phải người dùng độc lập.
