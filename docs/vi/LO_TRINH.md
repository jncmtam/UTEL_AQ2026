# Lộ trình: những việc chưa làm trong V3.2

Bản demo vòng chung kết ưu tiên một luồng hoàn chỉnh và tin cậy: chọn mẫu hoặc nhập yêu cầu → xem lại ràng buộc →
chạy job Modal → đọc kết quả. Các mục dưới đây chưa có trong bản này. Mỗi mục ghi rõ phạm vi và điều kiện cần có trước.

| # | Hạng mục | Phạm vi | Điều kiện trước |
|---|---|---|---|
| 1 | Chạy lại kiểm định với giá giao dịch lịch sử | Dựng lại giá chưa điều chỉnh từ giá đã điều chỉnh và danh sách sự kiện doanh nghiệp (cổ tức tiền, cổ tức cổ phiếu, chia tách, ngày giao dịch không hưởng quyền); tính chi phí lô theo giá khớp thật; cộng cổ phiếu thưởng vào tài khoản | Tệp sự kiện doanh nghiệp có quyền sử dụng cho cả 40 mã từng thuộc VN30, 2022–2026 |
| 2 | Thử với người dùng độc lập | 20–30 nhà đầu tư cá nhân tự viết yêu cầu; nhóm gán nhãn mù; đo lại độ chính xác, chất lượng câu hỏi làm rõ và tỷ lệ tuân thủ đầu-cuối | Mẫu đồng ý tham gia, cách lưu dữ liệu ẩn danh, thời gian tuyển người |
| 3 | Tài khoản đang có cổ phiếu | Form nhập danh mục hiện tại; lệnh bán và thuế bán; trần tính trên NAV sau phí và thuế (mã nguồn đã hỗ trợ, giao diện chưa có) | Thiết kế form và kiểm tra dữ liệu nhập |
| 4 | Giá thị trường cập nhật | Thay ảnh chụp dữ liệu đến 2026-10-01 bằng giá cuối ngày gần nhất; ghi rõ thời điểm giá | Nguồn dữ liệu có giấy phép hiển thị công khai |
| 5 | Chọn lịch mạch theo cỡ tài khoản | Thay k-NN bằng quy tắc “một lịch cho mỗi cỡ tài khoản” (cùng hiệu quả, đơn giản hơn) hoặc giữ cấu hình k-NN V3; tinh chỉnh COBYLA chỉ cho tài khoản dưới 50 triệu | Quyết định sản phẩm dựa trên kết quả nghiên cứu k-NN V3.2 |
| 6 | Chạy trên phần cứng lượng tử thật | Gửi mạch OpenQASM của một quyết định lên IBM; so phân bố đo với mô phỏng nhiễu | Token IBM Quantum và ngân sách giờ máy; mã `python -m agqo hardware` đã có |
| 7 | Lưu lịch sử lần chạy bền vững | Lưu mã lần chạy và kết quả vào Modal Volume để máy chủ web khởi động lại không làm mất kết quả đang xem | Chính sách lưu và xóa dữ liệu người dùng |
| 8 | Bảo vệ địa chỉ công khai | Giới hạn số lần chạy theo IP, khóa tạm khi quá tải, trang trạng thái | Quyết định ai được dùng bản demo sau cuộc thi |
| 9 | Xuất lệnh cho công ty chứng khoán | Tệp CSV theo mẫu lệnh của công ty chứng khoán; cảnh báo giá trần/sàn | Mẫu tệp của ít nhất một công ty chứng khoán; tư vấn pháp lý: AGQO là công cụ mô phỏng, không phải lời khuyên đầu tư |
