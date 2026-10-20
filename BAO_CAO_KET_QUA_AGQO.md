# Báo cáo kết quả AGQO

**Ngày cập nhật:** 20/10/2026<br>
**Phiên bản đang giữ làm hướng chính:** V1 — điều chỉnh rủi ro, có tính chi phí đổi danh mục.

## 1. Kết luận ngắn

V1 đã được triển khai và chạy trên một bài toán tổng hợp N = 8, K = 6. Bộ giải chính xác, tham lam và tôi luyện đều tìm cùng một danh mục. QAOA với bộ trộn X tìm đúng nghiệm trong 2/3 lượt; bộ trộn XY giữ tính khả thi trong mọi mẫu nhưng chưa tìm đúng nghiệm ở 3/3 lượt.

Đây là kết quả kỹ thuật trên dữ liệu tổng hợp. **Chưa có kiểm định lịch sử bằng giá thị trường, chưa có bằng chứng sinh lời, và chưa có lượt chạy QPU.** Kết quả H2 cũ vẫn được giữ như hồ sơ đối chứng kỹ thuật: chưa đạt ngưỡng đã đăng ký.

## 2. Kết quả V1 đã chạy

### Cấu hình

| Thuộc tính | Giá trị |
|---|---|
| Dữ liệu | Một bài toán tổng hợp, hạt giống 20261012 |
| Số mã / số mã chọn | N = 8 / K = 6 |
| Xác suất trạng thái biến động | 0,70, đặt để minh họa, không phải dự báo từ mô hình |
| Hệ số ngại rủi ro | λ = 7,60 |
| Mức co rút hiệp phương sai | α = 0,40, giữ cố định |
| Chi phí giao dịch | 25 điểm cơ bản trên mỗi đồng giao dịch mua hoặc bán |
| Số lần tái cân bằng năm hóa | 12 |
| QAOA | p = 1, 512 mẫu mỗi lần đánh giá, tối đa 50 lần đánh giá |
| Hạt giống QAOA | 11, 23, 47 cho mỗi bộ trộn |

### Nghiệm danh mục và chi phí

| Kết quả | Giá trị |
|---|---|
| Danh mục tối ưu | SYN00, SYN02, SYN03, SYN04, SYN06, SYN07 |
| Chuỗi quyết định theo thứ tự SYN00–SYN07 | `[1, 0, 1, 1, 1, 0, 1, 1]` |
| Điểm mục tiêu sau khi tính phí | -0,00698667 |
| Doanh số giao dịch hai chiều | 66,67% giá trị danh mục |
| Chi phí trong mục tiêu năm hóa | 2,00% |
| Tham lam so với nghiệm chính xác | Trùng nghiệm |
| Tôi luyện so với nghiệm chính xác | Trùng nghiệm |

Với cùng λ, α và tỷ trọng ban đầu, bỏ phí cho điểm mục tiêu -0,02698667; thêm phí 25 điểm cơ bản làm điểm tăng đúng 0,02000000, nhưng **không đổi danh mục tối ưu** trên mẫu này. Chi phí 2% là kết quả của giả định 25 điểm cơ bản × doanh số hai chiều 66,67% × 12 lần tái cân bằng. Nó không phải lợi nhuận bị mất đã đo trên thị trường.

### Chất lượng QAOA so với nghiệm chính xác

Khoảng cách được chuẩn hóa theo độ rộng mục tiêu của các danh mục khả thi trong cùng phiên bản. “Lượt đúng nghiệm” đếm số hạt giống mà nghiệm khả thi tốt nhất được lấy mẫu trùng nghiệm chính xác.

| Bộ trộn | Tỷ lệ mẫu khả thi trung bình | Lượt đúng nghiệm | Trung vị khoảng cách | Khoảng cách theo hạt giống 11 / 23 / 47 |
|---|---:|---:|---:|---:|
| X | 19,40% | 2/3 | 0,00% | 7,51% / 0,00% / 0,00% |
| XY | 100,00% | 0/3 | 24,93% | 46,97% / 24,93% / 16,27% |

| Bộ trộn | Hạt giống | Điểm tốt nhất lấy được | Tỷ lệ mẫu khả thi | Khoảng cách chuẩn hóa |
|---|---:|---:|---:|---:|
| X | 11 | -0,00367543 | 10,16% | 7,51% |
| X | 23 | -0,00698667 | 18,55% | 0,00% |
| X | 47 | -0,00698667 | 29,49% | 0,00% |
| XY | 11 | 0,01373569 | 100,00% | 46,97% |
| XY | 23 | 0,00401033 | 100,00% | 24,93% |
| XY | 47 | 0,00018922 | 100,00% | 16,27% |

XY bảo toàn đúng K nên mẫu đo đều khả thi. Điều đó chưa đảm bảo nghiệm tốt: cả ba lượt XY đều cách nghiệm chính xác. X có ít mẫu khả thi hơn nhưng tìm đúng nghiệm ở hai hạt giống. Đây chỉ là một bài toán nhỏ với ba hạt giống, chưa đủ để kết luận bộ trộn nào tốt hơn trên tập lớn.

## 3. Dữ liệu của bài toán V1

Toàn bộ đầu vào bên dưới được sinh giả lập, không lấy từ giá chứng khoán Việt Nam. Lợi nhuận kỳ vọng và độ biến động là tham số năm hóa. Tỷ trọng trước giao dịch gồm sáu mã, mỗi mã 1/6.

| Mã | Lợi nhuận kỳ vọng năm hóa | Độ biến động năm hóa | Tỷ trọng trước giao dịch | Có trong nghiệm V1 |
|---|---:|---:|---:|---|
| SYN00 | 6,5134% | 23,2262% | 16,6667% | Có |
| SYN01 | 3,3189% | 25,3355% | 16,6667% | Không |
| SYN02 | 16,5411% | 33,4376% | 0,0000% | Có |
| SYN03 | 9,9800% | 27,8680% | 16,6667% | Có |
| SYN04 | 16,1332% | 32,5293% | 0,0000% | Có |
| SYN05 | -2,1951% | 26,3775% | 16,6667% | Không |
| SYN06 | 17,6589% | 33,4724% | 16,6667% | Có |
| SYN07 | 9,5540% | 17,4772% | 16,6667% | Có |

Hiệp phương sai đầu vào, trước co rút; thứ tự hàng/cột SYN00 đến SYN07, đơn vị là bình phương lợi nhuận năm hóa. Các số được làm tròn tám chữ số.

| | SYN00 | SYN01 | SYN02 | SYN03 | SYN04 | SYN05 | SYN06 | SYN07 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **SYN00** | 0,05394578 | 0,00103412 | -0,00044524 | 0,00361323 | 0,00322340 | -0,00426066 | 0,00035561 | -0,00190895 |
| **SYN01** | 0,00103412 | 0,06418885 | -0,00434365 | -0,00073054 | -0,00202305 | 0,00088329 | 0,00496531 | 0,00135787 |
| **SYN02** | -0,00044524 | -0,00434365 | 0,11180738 | 0,00449040 | 0,00679209 | -0,00553366 | -0,01384120 | -0,00437470 |
| **SYN03** | 0,00361323 | -0,00073054 | 0,00449040 | 0,07766233 | 0,00417921 | -0,00634759 | -0,00454916 | -0,00247369 |
| **SYN04** | 0,00322340 | -0,00202305 | 0,00679209 | 0,00417921 | 0,10581524 | -0,00454958 | -0,00902338 | -0,00581688 |
| **SYN05** | -0,00426066 | 0,00088329 | -0,00553366 | -0,00634759 | -0,00454958 | 0,06957734 | 0,00536291 | 0,00263350 |
| **SYN06** | 0,00035561 | 0,00496531 | -0,01384120 | -0,00454916 | -0,00902338 | 0,00536291 | 0,11203992 | 0,00591085 |
| **SYN07** | -0,00190895 | 0,00135787 | -0,00437470 | -0,00247369 | -0,00581688 | 0,00263350 | 0,00591085 | 0,03054514 |

## 4. Kết quả lượng tử lịch sử

Thí nghiệm H2 ngày 13/10/2026 được chạy trước V1 trên 36 bài toán tổng hợp. Đây là kết quả cũ cần giữ làm đối chứng, không phải kết quả V1.

| Bộ trộn | Cấu hình đạt / 36 | Khoảng cách trung vị | Có mẫu khả thi trong mọi cấu hình | Ngưỡng cần đạt |
|---|---:|---:|---:|---:|
| X | 18/36 | 4,22% | 36/36 | 29/36 |
| XY | 0/36 | 29,57% | 36/36 | 29/36 |

| Kích thước | X đạt | XY đạt |
|---:|---:|---:|
| N = 8 | 12/12 | 0/12 |
| N = 12 | 6/12 | 0/12 |
| N = 16 | 0/12 | 0/12 |

**Kết luận:** H2 chưa đạt ngưỡng đã đăng ký cho cả hai bộ trộn. Không nới ngưỡng sau khi xem kết quả. Nghiệm chính xác cổ điển đã giải được một bài toán N = 30, K = 6 trong 3,987 giây trên máy 8 lõi/16 GB theo báo cáo cũ; vì vậy chưa có cơ sở nói QAOA cần thiết hoặc vượt trội ở quy mô này.

## 5. Những gì đã đạt được và chưa đạt được

### Đã đạt được

- Có phiên bản V1 với chi phí giao dịch nằm trong hàm mục tiêu và biểu diễn QUBO chính xác.
- Có nghiệm chính xác làm chuẩn và các đối chứng tham lam, tôi luyện, QAOA.
- Có khung mô phỏng lợi nhuận ròng theo tháng, chi phí, doanh số, chỉ số rủi ro/lợi nhuận và cờ giới hạn thanh khoản.
- Có công cụ đánh giá chất lượng xác suất AI và hiệu chỉnh xác suất.
- Kết quả H2 cũ và lượt minh họa V1 đều có cấu hình, hạt giống và giới hạn phép đo rõ ràng.

### Chưa đạt được

- Chưa có dữ liệu VN30/VN100 có quyền sử dụng và thành phần lịch sử theo ngày.
- Chưa chạy kiểm định cuốn chiếu ngoài mẫu; chưa có lợi nhuận ròng, tăng trưởng kép, Sharpe, mức sụt giảm hoặc sức chứa trên thị trường.
- Chưa chứng minh AI tốt hơn xác suất nền hay quy tắc biến động đơn giản.
- Chưa chạy QPU thật; chưa có số liệu nhiễu thiết bị hoặc so sánh thời gian/chi phí lượng tử với máy cổ điển.
- Mô phỏng thanh khoản chưa khớp lệnh từng phần và chưa tính tác động giá.

## 6. Quyết định tiếp theo

Giữ V1 làm nhánh phát triển chính; giữ V0 và H2 cũ chỉ làm đường chuẩn lịch sử. Việc tiếp theo có giá trị nhất là nạp dữ liệu hợp lệ, khóa quy tắc khớp lệnh và đối chuẩn, rồi chạy kiểm định ngoài mẫu. Chỉ sau đó mới kết luận chiến lược có giá trị kinh tế hay không.

Ở nhánh lượng tử, tạo tập bài toán mới để chọn cấu hình; giữ tập kiểm tra kín; báo khoảng cách tới nghiệm chính xác, tỷ lệ khả thi, số lần đo, thời gian tổng và độ phức tạp mạch. Kết quả hiện tại không ủng hộ tuyên bố ưu thế lượng tử.

## 7. Nguồn trong dự án

- [Dữ liệu chi tiết H2](results/synthetic_h2_20261013.jsonl)
- [Báo cáo H2 lịch sử](results/BAO_CAO_THU_NGHIEM_H2_2026-10-13.md)
- [Tài liệu kỹ thuật của phiên bản V1](TAI_LIEU_KY_THUAT_AGQO.md)
- [Đề cương nghiên cứu](AGQO_Final_Research_Proposal.md)
