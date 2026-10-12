# Báo cáo thử nghiệm kỹ thuật AGQO

**Ngày chạy:** 13/10/2026  
**Phạm vi:** kiểm tra kỹ thuật trên dữ liệu tổng hợp; không phải kiểm định lợi nhuận thị trường.  
**Dữ liệu đầu vào:** 12 bộ ma trận tổng hợp, giá trị khởi tạo PCG64 từ 20261012 đến 20261023. Mỗi bộ tạo bài toán N = 8, 12, 16; K = 6. Không dùng dữ liệu giá VN30/VN100.

**Từ viết tắt:** QAOA (Quantum Approximate Optimization Algorithm, thuật toán tối ưu gần đúng lượng tử); COBYLA (Constrained Optimization BY Linear Approximations, tối ưu không đạo hàm bằng xấp xỉ tuyến tính); H2 (Hypothesis 2, giả thuyết số 2); PCG64 (Permuted Congruential Generator 64-bit, bộ sinh số giả ngẫu nhiên 64 bit); CPU (Central Processing Unit, bộ xử lý trung tâm); GPU (Graphics Processing Unit, bộ xử lý đồ họa); RAM (Random Access Memory, bộ nhớ truy cập ngẫu nhiên); SSD (Solid-State Drive, ổ lưu trữ thể rắn); QPU (Quantum Processing Unit, bộ xử lý lượng tử).

## 1. Cấu hình đã chạy

- QAOA (Quantum Approximate Optimization Algorithm, thuật toán tối ưu gần đúng lượng tử), p = 1.
- So sánh bộ trộn X có hạng phạt với bộ trộn XY bảo toàn số mã.
- COBYLA có giới hạn tối đa 50 lần đánh giá cho từng giá trị khởi tạo; mỗi lần dùng 512 mẫu đo.
- Ba giá trị khởi tạo: 11, 23, 47. Thứ tự tài sản trong bộ trộn XY được xáo lại theo từng giá trị.
- Bộ trộn XY được thực thi bằng tích Trotter bậc nhất theo thứ tự cạnh trên vòng; kết quả áp dụng cho đúng mạch này.
- Chuẩn so sánh là nghiệm chính xác duyệt đủ C(N, 6) tổ hợp.
- Tổng cộng 36 bài toán × 2 bộ trộn = 72 cấu hình; 216 lượt tối ưu. COBYLA dừng sau 13–36 lần đánh giá tùy lượt, không vượt giới hạn 50.

## 2. Kết quả theo tiêu chí H2

Một cấu hình đạt khi cả ba lượt có ít nhất một nghiệm khả thi được lấy mẫu và trung vị khoảng cách chuẩn hóa không quá 5%. Ngưỡng chấp nhận của đề cương là ít nhất 29/36 cấu hình cho từng bộ trộn.

| Bộ trộn | Đạt | Trung vị khoảng cách chuẩn hóa trên 36 cấu hình | Cấu hình có đủ nghiệm khả thi | Kết luận H2 |
|---|---:|---:|---:|---|
| X | 18/36 | 4,22% | 36/36 | Chưa đạt ngưỡng 29/36 |
| XY | 0/36 | 29,57% | 36/36 | Chưa đạt ngưỡng 29/36 |

| Kích thước | X đạt | Trung vị khoảng cách X | XY đạt | Trung vị khoảng cách XY |
|---:|---:|---:|---:|---:|
| N = 8 | 12/12 | 0,00% | 0/12 | 20,31% |
| N = 12 | 6/12 | 4,22% | 0/12 | 31,53% |
| N = 16 | 0/12 | 13,44% | 0/12 | 32,83% |

**Diễn giải:** bộ trộn XY giữ ràng buộc K trong cả 36 bài toán, nhưng tích Trotter đã thử chưa tạo ra nghiệm tốt theo hàm mục tiêu. Bộ trộn X đạt tốt ở N = 8, giảm ở N = 12 và không đạt cấu hình nào ở N = 16. Kết quả hiện tại không đạt H2a/H2b với các cấu hình p = 1 đã chạy; không nên điều chỉnh ngưỡng sau khi đã xem kết quả.

## 3. Khối lượng tính đã đo

- Bộ thử đầy đủ gồm 2.409.984 mẫu đo mô phỏng trong các lần gọi mục tiêu của COBYLA, cộng 110.592 mẫu cuối để chấm nghiệm khả thi. Đây là mẫu trên máy cổ điển, không phải số lần đo QPU.
- Tổng thời gian nội bộ ghi nhận cho 216 lượt QAOA là 13,11 giây; thời gian này không gồm toàn bộ khởi tạo, duyệt nghiệm chính xác và ghi tệp.
- Trung vị thời gian một lượt QAOA: 0,0183 giây; theo N, trung vị lần lượt là 0,0110 giây, 0,0183 giây và 0,1494 giây cho N = 8, 12, 16.
- Bài toán N = 30, K = 6 có 593.775 tổ hợp. Một lượt duyệt chính xác trên mẫu tổng hợp mất 3,987 giây trên máy hiện có.

## 4. Máy và giới hạn của phép đo

Môi trường thử: Mac15,12, kiến trúc arm64, 8 lõi xử lý, RAM 16 GB, Python 3.12; NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, Qiskit 2.5.2, Qiskit Aer 0.17.2, IBM Quantum Runtime 0.50.0.

Máy này không có GPU NVIDIA/CUDA được dùng trong phép thử và không có QPU được gửi lệnh. Các số thời gian trên chỉ mô tả máy cục bộ và mẫu tổng hợp. Không được suy diễn thành hiệu năng trên cụm 16 lõi, thiết bị lượng tử, hoặc dữ liệu thị trường.

## 5. Đề nghị tài nguyên có căn cứ

| Tài nguyên | Đề nghị | Căn cứ và điều kiện |
|---|---|---|
| CPU | Máy 8 lõi/16 GB đã đủ cho thí nghiệm kỹ thuật hiện tại; đề nghị nút dùng chung 8 lõi/32 GB làm mức nền, ưu tiên quyền dùng 16 lõi/64 GB trong 4 tuần nếu chạy song song 105 kỳ, kiểm định cuốn chiếu và mở rộng VN100 | Máy 8 lõi/16 GB đã duyệt chính xác một mẫu N=30, K=6 trong 3,987 giây và chạy đủ ma trận H2. Mức 16/64 là dự phòng để tăng song song, không phải điều kiện cho bản hiện tại. |
| GPU | Chưa cấp thường trực; nếu có cụm Linux/CUDA thì cấp thử tối đa 40 giờ, GPU có 24 GB bộ nhớ đồ họa | Bản hiện tại chạy N≤16 nhanh trên CPU. Chỉ giữ đề nghị thử GPU cho mô phỏng dày hơn sau khi so thời gian CPU/GPU bằng cùng mạch và phiên bản Aer. |
| QPU | 8–12 qubit, trần tổng 800.000 mẫu đo, nếu có chương trình học thuật | Dùng để đo mạch thật, lỗi và kết quả lấy mẫu; không có bằng chứng hiện tại rằng QPU cần thiết để giải VN30 hoặc rằng sẽ nhanh hơn CPU. Sổ ngân sách trong mã giữ chỗ tổng số mẫu trước khi gửi. |
| Lưu trữ | 100 GB SSD | Mức dự phòng đề cương cho dữ liệu giá, phiên bản dữ liệu, bảng đếm và nhật ký; chưa đo nhu cầu thực tế vì chưa có dữ liệu thị trường. |

Không ước tính chi phí QPU bằng tiền vì chưa chọn nhà cung cấp, gói dịch vụ hoặc hạn mức.

## 6. Việc cần làm trước kết luận tài chính

1. Nhận dữ liệu giá có quyền sử dụng và lịch thành phần VN30 lịch sử theo ngày hiệu lực.
2. Hoàn thiện bộ nhập dữ liệu, khớp ở giá mở cửa phiên kế tiếp, giới hạn thanh khoản và phí theo các kịch bản đã đăng ký.
3. Chạy các nhánh AI bật/tắt cùng đối chứng Ledoit–Wolf; chỉ mở tập kiểm tra 2024 trở đi sau khi khóa toàn bộ lựa chọn.
4. Giữ p = 1 làm thí nghiệm chính. Báo p = 2 riêng như độ nhạy; không thay kết quả H2 chính bằng p = 2.
5. Nếu tiếp tục nghiên cứu XY, kiểm tra độ nhạy bộ khởi tạo và thứ tự vòng trên tập huấn luyện, giữ cùng ngân sách và báo cả độ sâu/số cổng. Không dùng các thay đổi này để tuyên bố H2 đã đạt nếu chưa chạy lại đủ 36 cấu hình theo quy tắc định trước.

## 7. Tệp kết quả

Dữ liệu từng cấu hình, từng giá trị khởi tạo, số lần đánh giá, góc tối ưu, tỷ lệ khả thi và khoảng cách được lưu tại [synthetic_h2_20261013.jsonl](synthetic_h2_20261013.jsonl). Các kết quả kỹ thuật không được gộp với một kiểm định tài chính trong tương lai.
