# Kết quả nghiên cứu nói gì (bản dễ đọc)

Bản ghi đầy đủ bằng tiếng Anh, kèm mã lần chạy cho từng con số: [RESEARCH_RESULTS.md](../technical/RESEARCH_RESULTS.md).
Mọi phép mô phỏng chạy trên Modal CPU, mọi lời gọi LLM chạy trên Modal H100.

## 1. Sản phẩm đáng tin hơn

- **Trần tỷ trọng được kiểm tra trên giá trị tài khoản sau phí.** Phí mua làm tài khoản nhỏ đi một chút, nên một
  danh mục “vừa đúng 25%” tính trên vốn ban đầu có thể thành 25,03% sau phí. Bản hiện tại chừa sẵn biên cho phí khi dựng
  bài toán và kiểm tra lại chính xác sau phí. Ca 200 triệu, ngân hàng tối đa 25% giờ ra 24,05%.
- **Yêu cầu không thể đáp ứng được giải thích, không gây lỗi.** Ví dụ “mỗi mã tối đa 2%” với 20 triệu: 2% là 399.400
  đồng, nhỏ hơn một lô rẻ nhất (SHB, 1.135.000 đồng). Trang nói đúng quy tắc nào chặn và không tạo lệnh.
- **“Chỉ giữ 1 mã” chạy được.** Khi chỉ còn một quyết định lô, máy tính tìm chính xác ngay, không cần mạch lượng tử.
- **Câu mơ hồ hoặc mâu thuẫn thì hỏi lại trước.** Nút Chạy bị khóa cho đến khi bạn trả lời; máy chủ cũng từ chối chạy.
- **Lời giải thích của AI bị kiểm tra kỹ hơn.** Nếu AI ghi sai số của phương án này sang phương án khác, hoặc ghi
  sai đơn vị (ví dụ “5,39 lô” thay vì “5,39%”), bộ kiểm tra bắt được.

## 2. AI đọc yêu cầu tiếng Việt

Trên 50 câu mới (24 rõ ràng, 10 mơ hồ, 8 mâu thuẫn, 8 không khả thi), tính đến kết quả cuối cùng sau bộ tối ưu:

| Cách đọc yêu cầu | Đúng đầu-cuối |
|---|---|
| Quy tắc từ khóa | 33/50 |
| Qwen3.8 với prompt ban đầu | 46/50 |
| **Qwen3.8 với prompt tiếng Anh hiện tại** | **49/50** |

Prompt hiện tại hơn quy tắc từ khóa rõ rệt (kiểm định McNemar p = 0,00003). Chênh lệch với prompt ban đầu chưa đủ để kết luận
(3 câu, p = 0,25). Câu duy nhất sai là một mâu thuẫn cần làm phép tính: “mỗi mã tối đa 5%, tối đa 4 mã, và đầu tư hết
tiền” (4 × 5% = 20%). **Bộ câu do nhóm viết**, nên kết quả này chưa thay được thử nghiệm với người dùng thật.

## 3. Tài khoản nhỏ và giới hạn của giá đã điều chỉnh

Với 20 triệu qua 12 quý, sai số bám VN30: làm tròn lô gần nhất 12,14%, thuật toán tham lam 7,47%, AGQO 6,77%
(bằng đúng tối ưu chính xác). Nghiên cứu bổ sung tái lập đúng các số này.

Giá lịch sử là giá đã điều chỉnh cổ tức và chia tách, nên giá một lô trong quá khứ bị tính rẻ hơn thực tế. Chưa có
dữ liệu giá khớp lệnh gốc, nên chúng tôi đo giới hạn: nếu mọi giá lịch sử thực ra cao hơn f lần, bài toán giống hệt
một tài khoản 20 triệu / f.

| Giá lịch sử bị tính rẻ hơn | Tài khoản tương đương | Làm tròn | Tham lam | AGQO |
|---|---|---|---|---|
| 0% | 20 triệu | 12,14% | 7,47% | 6,77% |
| 10% | 18,2 triệu | 12,01% | 8,85% | 6,74% |
| 25% | 16 triệu | 12,45% | 9,32% | 7,53% |
| 50% | 13,3 triệu | 13,27% | 10,61% | 8,36% |

Lợi thế so với làm tròn giữ quanh 5 điểm %. So với thuật toán tham lam, ở đúng 20 triệu chênh lệch **chưa có ý nghĩa
thống kê** (khoảng tin cậy −1,5 đến +0,02 điểm %), nhưng có ý nghĩa ở các tài khoản tương đương nhỏ hơn. Chênh lệch
riêng theo từng mã (ví dụ ngân hàng chia cổ tức bằng cổ phiếu nhiều) chưa đo được.

## 4. k-NN chọn lịch mạch: có ích, nhưng chưa hơn một quy tắc đơn giản

Trên 330 bài toán holdout mới (22 tháng × 5 cỡ tài khoản × 3 loại quy tắc):

- k-NN chọn trên tập validation: 15,34% lượt đo gần tối ưu, so với 14,58% của lịch cố định (+0,76 điểm %, thắng 20/22
  tháng, p = 0,0002). Lợi ích có ở mọi cỡ tài khoản và mọi loại quy tắc.
- Nhưng **chỉ cần chọn một lịch riêng cho mỗi cỡ tài khoản** cũng đạt đúng +0,76 điểm %. Cấu hình k-NN của nghiên cứu chính tốt hơn
  quy tắc đó một chút (+0,28 điểm %).
- Lý do nghiên cứu chính thấy k-NN thua lịch cố định (21,3% so với 23,8%) là bước **tinh chỉnh COBYLA** trên tài khoản 100 triệu,
  không phải do k-NN chọn sai. Nghiên cứu bổ sung đo lại: tinh chỉnh giúp nhiều ở 20 triệu (5,7% → 10,5%), gần như không giúp ở
  100–200 triệu, và tốn gấp 41 lần số lần mô phỏng.

## 5. AI thiết kế mạch lượng tử

Qwen3.8 nhận mô tả bài toán, các thành phần mạch được phép, ngân sách (≤ 1.500 cổng hai qubit, ≤ 60 lần mô phỏng mỗi
bài toán) và mục tiêu, rồi đề xuất 2 vòng × 8 mạch; vòng 2 được xem điểm của vòng 1. Mọi mạch được kiểm tra hợp lệ
trước khi mô phỏng. Trên 330 bài toán holdout:

| Mạch | Lượt đo gần tối ưu |
|---|---|
| Lịch chọn bằng dữ liệu (chấm 1.080 lịch) + tinh chỉnh | 15,31% |
| Lịch chọn bằng dữ liệu | 14,35% |
| **Mạch tốt nhất do Qwen đề xuất** | **9,83%** |
| Tìm kiếm ngẫu nhiên cùng ngân sách (3 lần) | 2,6–3,9% |

Qwen hơn tìm kiếm ngẫu nhiên rõ rệt (+6,4 điểm %, thắng cả 22/22 tháng): nó chọn đúng các ý cấu trúc như khởi động
ấm và bộ trộn căn chỉnh. Nhưng nó thua xa lịch chọn bằng dữ liệu (−4,5 điểm %) mà lại tốn gấp 60 lần số lần mô phỏng.
Vì vậy AGQO giữ cách chọn lịch bằng dữ liệu; LLM chỉ hữu ích như một gợi ý ban đầu về cấu trúc mạch.

## 6. Các mẫu trong ứng dụng

| Mẫu | Kết quả đo trên Modal (12 quý) |
|---|---|
| 20 triệu, không quy tắc | Có lợi: 6,77% so với 12,14% của làm tròn |
| 200 triệu, ngân hàng ≤ 25% | Có lợi: 3,57% so với 4,34%; trần làm tăng sai số bám 1,07 điểm %; 0 vi phạm |
| 100 triệu, bỏ bất động sản và VIC/VHM/VRE | Có lợi nhỏ: 6,39% so với 6,63%; quy tắc làm tăng 3,43 điểm % |
| 500 triệu, không quy tắc | Không khác biệt rõ: lô đã đủ nhỏ |
| Chỉ 1 mã (20 triệu) | Không khác biệt (tìm chính xác); sai số bám rất cao, đúng như dự kiến |
| Mỗi mã ≤ 2% (20 triệu) | Không khả thi, nêu đúng quy tắc chặn |
| Câu mơ hồ về ngân hàng | Hỏi lại, không tạo lệnh |

## 7. Điều chúng tôi không khẳng định

- Không có ưu thế lượng tử: máy tính cổ điển liệt kê hết các tổ hợp và dùng đúng phép đó để kiểm chứng.
- Kết quả dựa trên giá lịch sử đã điều chỉnh và một bộ câu do nhóm viết.
- Sai số bám là số đo trên quá khứ, không phải dự báo lợi nhuận.
