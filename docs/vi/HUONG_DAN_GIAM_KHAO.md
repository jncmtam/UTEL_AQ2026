# AGQO – Hướng dẫn nhanh cho giám khảo

Đội AQ2026-169 (UTEL) · **Prototype: https://data1--agqo-v32.us-east.modal.run** · **Không cần tài khoản thử nghiệm**: trang công
khai, mở bằng trình duyệt là dùng được (máy tính hoặc điện thoại).

## 1. Thử trong 3 phút, không cần cài đặt

1. Mở https://data1--agqo-v32.us-east.modal.run (lần mở đầu có thể mất 20–60 giây để máy chủ khởi động).
2. Ở mục **02 · Thử ngay**, bấm mẫu **“20 triệu, bỏ bất động sản, ngân hàng tối đa 30%”**.
3. Ở bước 3, xem hai ô có nhãn **“Từ câu lệnh”**: *Loại ngành: Bất động sản* và *Ngân hàng ≤ 30%*. Dòng nguồn cho biết câu được
   diễn giải bởi **câu trả lời Qwen đã lưu (phát lại)**. Nút Chạy đang khóa.
4. Bấm **✔ Xác nhận các ràng buộc này**, rồi **▶ Chạy trên Modal**. Thanh tiến trình hiện từng bước của job.

**Kết quả mong đợi** (giá ngày 01/10/2026; các số có thể lệch rất nhỏ giữa các lần chạy vì lấy mẫu mạch):

| Mục | Giá trị |
|---|---|
| Nhãn | ● Chạy thật trên Modal · container … · khoảng 5–11 giây |
| Lệnh mua | 5 mã, mỗi mã 1 lô: MSN, VPB, TCB, SSI, VIB |
| Phí giao dịch ước tính | 22.463 đ |
| Tiền mặt còn lại sau phí | 5.002.538 đ |
| Sai số bám ước tính | 11,78% (làm tròn lô gần nhất: 17,68%; tham lam cùng quy tắc: 11,71%) |
| Kiểm tra | ✔ Ngân hàng 29,38% ≤ 30% · ✔ không giữ bất động sản · ✔ đủ tiền sau phí |

Thử thêm: mẫu **“Câu mơ hồ”** (hệ thống hỏi lại và khóa nút Chạy), mẫu **“Mỗi mã tối đa 2%”** (báo không khả thi, nêu quy tắc chặn),
hoặc gõ câu của bạn ở bước 2 rồi bấm **Diễn giải thành ràng buộc**.

## 2. Đọc nhãn cho đúng

| Nhãn | Nghĩa |
|---|---|
| Bạn nhập · Từ mẫu · Từ câu lệnh · Chưa đặt | Nguồn của từng ô ràng buộc |
| Qwen trả lời trực tiếp / câu trả lời Qwen đã lưu (phát lại) / quy tắc từ khóa | Ai diễn giải câu của bạn. GPU khởi động lạnh mất khoảng 6–7 phút, nên câu mẫu dùng câu trả lời đã lưu |
| ● Chạy thật trên Modal | Danh mục vừa được tính trong một container Modal |
| ↺ Phát lại kết quả Modal đã lưu | Không khởi động được job; trang hiện kết quả đã lưu của đúng mẫu đó, không tính lại |
| Sai số bám ước tính | Tính trước giao dịch cho một quyết định; khác sai số bám thực tế đo qua 12 quý |
| NAV sau phí | Tiền mặt sau phí + giá trị cổ phiếu vừa mua; mọi quy tắc tính trên giá trị này |

## 3. Nếu có sự cố

- Thanh tiến trình đứng ở “Đang xếp hàng” lâu: chờ thêm 30 giây hoặc bấm **Thử lại** khi trang báo lỗi.
- Trang báo “Không khởi động được job”: chọn một mẫu (có bản phát lại, ghi rõ nhãn).
- Muốn thấy bên trong: mở **“Bên trong quyết định này”** để xem Hamiltonian, mạch QAOA, phân bố xác suất; nút **Tải mạch OpenQASM**
  tải đúng mạch đã chạy.

## 4. Tệp trong hồ sơ

| Tệp | Nội dung |
|---|---|
| AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.pdf | Báo cáo theo mẫu BTC |
| AQ2026-R2-AQ2026-169-Slide.pptx (+ .pdf) | 8 slide chính + 13 phụ lục; ghi chú người nói trong từng slide |
| AQ2026-R2-AQ2026-169-Ma_nguon.zip | Mã nguồn gắn với một commit, cấu hình, thành phần VN30, kết quả đã lưu, kiểm thử; tệp giá tải bằng lệnh `python -m agqo download` (xem phần tái lập) |
| AQ2026-R2-AQ2026-169-Huong_dan.pdf | Tài liệu này và phần tái lập |
