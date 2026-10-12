# ĐẶC TẢ NGHIÊN CỨU, TRIỂN KHAI VÀ ĐỀ NGHỊ CẤP PHÁT TÀI NGUYÊN
## AGQO (Artificial Intelligence-Guided Quantum Optimization — tối ưu hóa lượng tử có hướng dẫn bởi trí tuệ nhân tạo)

**Mã đề tài:** AGQO-2026  
**Đơn vị đề xuất:** Nhóm nghiên cứu AGQO  
**Thời điểm lập:** 12/10/2026  
**Kính gửi:** Giảng viên hướng dẫn và Hội đồng chuyên môn  
**Mục đích sử dụng:** Chốt cách hiểu bài toán, giao việc triển khai, chuẩn hóa thực nghiệm và làm căn cứ đề nghị cấp phát tài nguyên tính toán.

---

## 1. Mục đích và phạm vi

Tài liệu này là bản đặc tả nghiên cứu và kỹ thuật của AGQO. Người đọc cần có thể bắt đầu triển khai mà không phải tự suy đoán công thức, dữ liệu, phép đối chứng, cách tính tài nguyên hoặc tiêu chí kết luận.

Tài liệu đồng thời phục vụ ba mục đích:

1. Xác định câu hỏi nghiên cứu có thể bác bỏ bằng số liệu.
2. Quy định quy trình thực nghiệm có thể tái lập và tránh rò rỉ thông tin tương lai.
3. Trình bày yêu cầu tài nguyên vừa đủ, nêu rõ phần nào bắt buộc và phần nào chỉ phục vụ mở rộng nghiên cứu.

Đề tài không giả định thuật toán lượng tử tốt hơn thuật toán cổ điển. Việc chạy được mạch trên thiết bị lượng tử không phải bằng chứng về lợi ích tài chính. Kết luận chỉ được đưa ra từ dữ liệu, phép đối chứng và tiêu chí đã khóa trước khi xem kết quả trên tập kiểm tra cuối.

### 1.1. Kết quả bàn giao

Đến vòng bán kết ngày 25/10/2026:

- Quy trình chạy được từ dữ liệu kiểm tra đến bảng kết quả.
- Bộ kiểm thử chứng minh công thức mục tiêu, QUBO (Quadratic Unconstrained Binary Optimization, bài toán tối ưu nhị phân bậc hai không ràng buộc) và Hamiltonian Ising tương đương.
- Kết quả đối chứng cổ điển và QAOA (Quantum Approximate Optimization Algorithm, thuật toán tối ưu gần đúng lượng tử) trên bài toán nhỏ, kèm nhật ký.
- Kiểm định lịch sử sơ bộ nếu dữ liệu và quyền sử dụng đã được xác minh.
- Bảng tài nguyên đã dùng và nhu cầu còn lại đến ngày 10/11/2026.

Đến vòng chung kết ngày 10/11/2026:

- Quy trình kiểm định cuốn chiếu trên giai đoạn dữ liệu xác minh được.
- Phân tích sau chi phí giao dịch và kiểm tra độ nhạy.
- So sánh mô hình có AI hướng dẫn và mô hình không có AI hướng dẫn.
- So sánh bộ trộn X và bộ trộn XY trên máy mô phỏng; QPU là nhánh bổ sung.
- Báo cáo giới hạn, rủi ro và bằng chứng chưa đủ.

Nếu lịch ban tổ chức thay đổi, cập nhật các mốc theo thông báo có ngày tháng; không tự suy diễn lịch mới.

---

## 2. Tóm tắt điều hành

AGQO nghiên cứu bài toán chọn đúng K cổ phiếu trong N mã ứng viên, sau đó gán tỷ trọng bằng nhau. Mô hình rủi ro–lợi nhuận được chuyển thành bài toán tối ưu nhị phân bậc hai. Thuật toán tối ưu gần đúng lượng tử (QAOA, Quantum Approximate Optimization Algorithm) tìm nghiệm gần tối ưu. Một mô hình học máy nhỏ được thử làm bộ điều chỉnh hệ số rủi ro theo xác suất thị trường bước vào trạng thái biến động cao.

**Thiết kế chốt:**

- **Thị trường:** cổ phiếu HOSE (Ho Chi Minh Stock Exchange, Sở Giao dịch Chứng khoán Thành phố Hồ Chí Minh); ưu tiên VN30 (chỉ số gồm 30 cổ phiếu). VN100 (chỉ số gồm 100 cổ phiếu) là phần mở rộng.
- **Tần suất:** tái cân bằng tháng; quyết định sau phiên cuối tháng, giả lập giao dịch tại giá mở cửa phiên kế tiếp.
- **Danh mục:** K = 6, tỷ trọng bằng nhau; kiểm tra độ nhạy K = 5 và K = 8.
- **Dữ liệu:** giá, khối lượng và giá trị giao dịch hằng ngày; yêu cầu từ 2017 để tạo cửa sổ khởi động 252 phiên, đánh giá từ 2018 đến kỳ nắm giữ đầy đủ gần nhất có quyền sử dụng. Thành phần chỉ số phải gắn với ngày có hiệu lực.
- **AI (Artificial Intelligence, trí tuệ nhân tạo):** hồi quy logistic dự báo xác suất biến động chỉ số cao trong 21 phiên tiếp theo. Mô hình chỉ điều chỉnh hệ số ngại rủi ro và mức co rút hiệp phương sai trong miền đã khóa. Đây là giả thuyết cần kiểm chứng, không phải khẳng định tạo lợi nhuận.
- **Bộ giải lượng tử:** QAOA với p = 1 làm cấu hình chính, p = 2 là độ nhạy. So sánh X-mixer (bộ trộn dùng phép Pauli X) có hạng phạt để buộc chọn đúng K mã với XY-mixer (bộ trộn dùng phép Pauli X và Y) bảo toàn số bit 1. Chạy máy mô phỏng trước.
- **Đối chứng cổ điển:** duyệt chính xác toàn bộ tổ hợp tại N = 30, K = 6; thêm giải thuật tham lam và mô phỏng tôi luyện cho bài toán lớn hơn hoặc kiểm tra độ bền.
- **GPU (Graphics Processing Unit, bộ xử lý đồ họa):** không cần cho hồi quy logistic hoặc kiểm định lịch sử cỡ VN30. Đề nghị GPU để chạy song song mô phỏng trạng thái lượng tử và thử số qubit lớn hơn. Mức đề nghị: 1 GPU có 24 GB bộ nhớ hình ảnh (VRAM, Video Random Access Memory), tối đa 40 giờ trong 4 tuần.
- **QPU (Quantum Processing Unit, bộ xử lý lượng tử):** không bắt buộc để kết luận tài chính. Đề nghị ưu tiên 8–12 qubit; N = 16 chỉ mở rộng nếu số cổng và hạn mức cho phép. Hạn mức kế hoạch khoảng 0,8 triệu lần đo; mức thực tế tùy nhà cung cấp.
- **CPU (Central Processing Unit, bộ xử lý trung tâm):** cấu hình khuyến nghị 16 lõi ảo, 64 GB RAM (Random Access Memory, bộ nhớ truy cập ngẫu nhiên), 100 GB ổ lưu trữ nhanh.

Một điểm cần trình bày với giảng viên: tại VN30 và K = 6 có C(30,6) = 593.775 danh mục khả thi. Đây là quy mô có thể duyệt chính xác bằng CPU trong nhiều môi trường thông thường. Vì vậy, nhóm không xin QPU với lý do “cần phần cứng lượng tử để giải danh mục VN30”. Lý do xin là để đánh giá thực nghiệm phương pháp lượng tử, kiểm tra mạch và nhiễu, và đào tạo năng lực nghiên cứu. CPU vẫn bảo đảm tiến độ.

---

## 3. Từ viết tắt và quy ước

| Ký hiệu | Cụm từ đầy đủ | Nghĩa trong tài liệu |
|---|---|---|
| AGQO | Artificial Intelligence-Guided Quantum Optimization | Tối ưu hóa lượng tử có hướng dẫn bởi trí tuệ nhân tạo |
| AI | Artificial Intelligence | Trí tuệ nhân tạo |
| ML | Machine Learning | Học máy |
| LLM | Large Language Model | Mô hình ngôn ngữ lớn |
| QAOA | Quantum Approximate Optimization Algorithm | Thuật toán tối ưu gần đúng lượng tử |
| QUBO | Quadratic Unconstrained Binary Optimization | Tối ưu nhị phân bậc hai không ràng buộc |
| QPU | Quantum Processing Unit | Bộ xử lý lượng tử |
| CPU | Central Processing Unit | Bộ xử lý trung tâm |
| GPU | Graphics Processing Unit | Bộ xử lý đồ họa |
| RAM | Random Access Memory | Bộ nhớ truy cập ngẫu nhiên |
| VRAM | Video Random Access Memory | Bộ nhớ hình ảnh trên GPU |
| API | Application Programming Interface | Giao diện lập trình ứng dụng |
| SDK | Software Development Kit | Bộ công cụ phát triển phần mềm |
| HOSE | Ho Chi Minh Stock Exchange | Sở Giao dịch Chứng khoán Thành phố Hồ Chí Minh |
| VN30/VN100 | Chỉ số HOSE gồm 30/100 cổ phiếu | Chỉ số thị trường; không đồng nghĩa với dữ liệu lịch sử miễn phí |
| SSI | SSI Securities Corporation | Công ty Cổ phần Chứng khoán SSI; ứng viên cung cấp dữ liệu [12] |
| OHLC | Open, High, Low, Close | Giá mở cửa, cao nhất, thấp nhất, đóng cửa |
| CSV | Comma-Separated Values | Tệp dữ liệu dạng giá trị phân cách bằng dấu phẩy |
| JSON | JavaScript Object Notation | Định dạng trao đổi dữ liệu có cấu trúc |
| COBYLA | Constrained Optimization BY Linear Approximations | Tối ưu không đạo hàm dựa trên xấp xỉ tuyến tính có ràng buộc |
| SPSA | Simultaneous Perturbation Stochastic Approximation | Xấp xỉ ngẫu nhiên bằng nhiễu đồng thời |
| CAGR | Compound Annual Growth Rate | Tỷ lệ tăng trưởng kép hằng năm |
| MDD | Maximum Drawdown | Mức sụt giảm lớn nhất từ đỉnh đến đáy |
| SD | Standard Deviation | Độ lệch chuẩn |
| ADTV | Average Daily Trading Value | Giá trị giao dịch bình quân ngày |
| PBO | Probability of Backtest Overfitting | Xác suất quá khớp kiểm định lịch sử |
| CSCV | Combinatorially Symmetric Cross-Validation | Kiểm định chéo đối xứng tổ hợp |
| VND | Vietnamese đồng | Đồng Việt Nam |
| UTC | Coordinated Universal Time | Giờ phối hợp quốc tế |
| CUDA | Compute Unified Device Architecture | Nền tảng tính toán song song của NVIDIA |
| PCG64 | Permuted Congruential Generator, 64-bit | Bộ sinh số giả ngẫu nhiên xác định 64 bit |
| SHA-256 | Secure Hash Algorithm, 256-bit | Hàm băm mật mã 256 bit |
| MIQP | Mixed-Integer Quadratic Programming | Tối ưu bậc hai với biến nguyên hỗn hợp |
| bps | basis point | Điểm cơ bản; 1 bps = 0,01% |
| SSD | Solid-State Drive | Ổ lưu trữ thể rắn |
| GB | Gigabyte | (10^9) byte, đơn vị dung lượng thập phân |
| MiB | Mebibyte | (2^{20}) byte |
| GiB | Gibibyte | (2^{30}) byte |
| RQ | Research Question | Mã câu hỏi nghiên cứu |
| H | Hypothesis | Mã giả thuyết nghiên cứu |
| ID | Identifier | Mã nhận dạng |
| L2 | L2 norm regularization | Phạt theo bình phương chuẩn Euclid |
| SWAP | SWAP gate | Cổng hoán đổi vị trí của hai qubit |
| X, Y, Z | Các ma trận Pauli X, Pauli Y, Pauli Z | Phép toán cơ bản trên qubit |

Các thuật ngữ chuyên ngành như kiểm định lịch sử (backtest), kiểm định cuốn chiếu (walk-forward), vector trạng thái (statevector), lần đo (shot), bộ trộn (mixer), biên dịch mạch (transpile), trượt giá (slippage), hiệp phương sai (covariance), trạng thái thị trường (regime) và co rút (shrinkage) được giải thích tại lần dùng đầu. Tên công trình, thư viện và tổ chức giữ nguyên theo tên chính thức.

Ngày giao dịch theo múi giờ Việt Nam; ngày tháng dùng YYYY-MM-DD; lợi nhuận trong công thức là số thập phân. Mọi tệp cấu hình/kết quả phải kèm phiên bản dữ liệu, phiên bản chương trình và giá trị khởi tạo ngẫu nhiên.

---

## 4. Bài toán, mục tiêu và giả thuyết

### 4.1. Phát biểu bài toán

Tại thời điểm tái cân bằng t, có N mã đủ điều kiện. Biến nhị phân xᵢ:

- xᵢ = 1 nếu chọn cổ phiếu i.
- xᵢ = 0 nếu không chọn.

Ràng buộc:

\[
\sum_{i=1}^{N}x_i=K,\qquad K=6.
\]

Trọng số sau chọn:

\[
w_i=\frac{x_i}{K}.
\]

Tách hai lớp:

1. **Lựa chọn mã:** quyết định x bằng tối ưu tổ hợp.
2. **Đánh giá danh mục:** tính lợi nhuận, rủi ro, tỷ lệ thay đổi danh mục và phí từ w.

Bản chính không tối ưu trọng số liên tục sau khi chọn. Cách tách này giữ phép biến đổi QUBO dễ kiểm chứng và cô lập câu hỏi “bộ chọn mã có ích không?”. Tối ưu tỷ trọng là hướng mở rộng.

### 4.2. Câu hỏi nghiên cứu

Các mã RQ trong bảng là viết tắt của Research Question (câu hỏi nghiên cứu).

| Mã | Câu hỏi | Phép kiểm tra |
|---|---|---|
| RQ1 | AI có cải thiện danh mục ngoài mẫu so với hệ số cố định không? | So có AI hướng dẫn với cố định, giữ nguyên bộ giải và dữ liệu |
| RQ2 | QAOA có tìm nghiệm gần chính xác trên bài toán mẫu kiểm tra không? | Khoảng cách hàm mục tiêu, tỷ lệ nghiệm khả thi, số lần đánh giá |
| RQ3 | X-mixer và XY-mixer khác nhau thế nào? | Cùng N, K, hàm mục tiêu, ngân sách đánh giá và giá trị khởi tạo ngẫu nhiên |
| RQ4 | Lợi ích có còn sau phí, tỷ lệ thay đổi danh mục và giới hạn thanh khoản không? | Kiểm định lịch sử ròng so đối chuẩn theo tháng |
| RQ5 | Có cần GPU/QPU theo số đo không? | Thời gian, RAM/VRAM, lần đo, số cổng |
| RQ6 | Kết quả có bền qua các giai đoạn không? | Báo riêng từng giai đoạn |

### 4.3. Giả thuyết có thể bác bỏ

Các mã H trong bảng là viết tắt của Hypothesis (giả thuyết nghiên cứu).

- **H1:** AI cải thiện hiệu quả ròng ngoài mẫu so với bộ điều chỉnh cố định.
- **H2a (X):** với p = 1, X-mixer đạt điều kiện H2 trên ít nhất 29/36 bài toán mẫu.
- **H2b (XY):** với p = 1, XY-mixer đạt điều kiện H2 trên ít nhất 29/36 bài toán mẫu.
- **H3:** XY-mixer tăng tỷ lệ khả thi so X-mixer, nhưng có thể tăng số cổng hoặc độ sâu mạch.
- **H4:** Không tuyên bố ưu thế lượng tử về thời gian, chi phí hay lợi nhuận trừ khi thắng bộ giải cổ điển mạnh hơn trên cùng bài toán, chất lượng nghiệm và tổng chi phí.
- **H5:** Nếu lợi nhuận ròng không vượt đối chuẩn hoặc khoảng tin cậy chênh lệch bao gồm 0, kết luận là “chưa có bằng chứng về lợi ích đầu tư”, dù mạch chạy thành công.

H2 đánh giá thuật toán, không đánh giá hiệu quả tài chính. Bộ mẫu có 12 nguồn bài toán: 12 ngày lịch sử nếu dữ liệu đủ quyền, hoặc 12 trường hợp tổng hợp nếu không; từ mỗi nguồn tạo ba kích thước N = 8, 12, 16 với K = 6, tổng cộng 36 bài toán. Mỗi bộ trộn chạy ba giá trị khởi tạo ở p = 1, tối đa 50 lần đánh giá mỗi giá trị. Một bài toán đạt khi cả ba lần khởi tạo cho nghiệm khả thi và trung vị ba khoảng cách chuẩn hóa không quá 5%; ít nhất 29/36 bài toán phải đạt. Với bài toán tối thiểu hóa, \(g=(f_{QAOA}-f_{\mathrm{tối\ ưu}})/\max(f_{\max,\mathrm{khả\ thi}}-f_{\min,\mathrm{khả\ thi}},10^{-12})\), trong đó hai giá trị ở mẫu số là lớn nhất/nhỏ nhất trên toàn bộ nghiệm thỏa ràng buộc. Báo riêng X và XY; p = 2 là độ nhạy và không thay tiêu chí chính.

---

## 5. Bằng chứng hiện có và khoảng trống

### 5.1. Nền tảng

Mô hình trung bình–phương sai bắt nguồn từ Markowitz [1]. Hiệp phương sai mẫu có thể bất ổn khi số tài sản lớn so với số quan sát; co rút là đối chứng cần thiết [2]. QAOA được đề xuất như thuật toán biến phân cho tối ưu tổ hợp [3]. Nghiên cứu QAOA danh mục đã nêu các vấn đề thực tiễn về mã hóa ràng buộc, mạch, tối ưu tham số và đối chuẩn [4].

Tài liệu IBM Quantum có ví dụ danh mục chọn đúng K mã bằng XY-mixer [6]. Điều đó cho thấy phương án có thể triển khai bằng Qiskit; không chứng minh XY-mixer luôn tốt hơn hoặc đem lại lợi ích đầu tư. Tài liệu Qiskit Aer cho biết GPU mô phỏng đòi hỏi cài đặt hỗ trợ GPU, GPU NVIDIA tương thích và phiên bản CUDA phù hợp [7].

### 5.2. Khoảng trống AGQO

Đề tài không tuyên bố phát minh QAOA, QUBO, XY-mixer hay tối ưu danh mục. Đóng góp dự kiến là một đánh giá gắn kết, minh bạch trên thị trường Việt Nam:

- Tách đóng góp AI khỏi đóng góp bộ giải.
- Dùng cùng hàm mục tiêu khi so lượng tử và cổ điển.
- Đo chất lượng nghiệm, tính khả thi, mạch, thời gian và hiệu quả danh mục riêng.
- Đưa phí và sai lệch thành phần chỉ số vào quy trình.
- Báo cả kết quả bất lợi và phần chưa xác minh.

Nếu không có dữ liệu thành phần lịch sử, chỉ được báo cáo kỹ thuật trên rổ hiện tại hoặc dữ liệu tổng hợp; không gọi đó là kiểm định lịch sử không sai lệch.

---

## 6. Đặc tả và quản trị dữ liệu

### 6.1. Trường dữ liệu tối thiểu

| Nhóm | Trường | Mục đích |
|---|---|---|
| Giá ngày | mã, ngày, giá mở cửa/cao nhất/thấp nhất/đóng cửa, giá điều chỉnh hoặc hệ số điều chỉnh | Tính lợi nhuận và giá khớp |
| Thanh khoản | khối lượng, giá trị giao dịch | Lọc và giới hạn quy mô lệnh |
| Hành động doanh nghiệp | cổ tức, chia/tách, quyền mua, đổi mã | Điều chỉnh chuỗi giá |
| Chỉ số | VN30 hoặc đối chuẩn phù hợp | Đối chuẩn và đặc trưng |
| Thành phần | mã, chỉ số, ngày bắt đầu/kết thúc hiệu lực, nguồn | Tránh thiên lệch sống sót |
| Siêu dữ liệu | sàn, ngành, trạng thái, ngày niêm yết/ngừng giao dịch | Kiểm soát tập mã |

Dùng chuỗi giá đã điều chỉnh để tính tổng lợi nhuận nếu nhà cung cấp công bố rõ phương pháp điều chỉnh. Nếu chỉ có giá chưa điều chỉnh, dựng lại bằng hành động doanh nghiệp. Không ghép giá điều chỉnh của một nguồn với sự kiện doanh nghiệp của nguồn khác nếu chưa đối chiếu.

### 6.2. Nguồn và cổng dữ liệu

Tài liệu FastConnect Data của SSI liệt kê API danh sách mã, thành phần chỉ số, OHLC ngày, giá ngày và chỉ số ngày [11]. Tài liệu công khai chưa xác nhận tài khoản nhóm có thể tải lịch sử từ 2017 để khởi động cửa sổ, có quyền lưu/trình chiếu, hoặc có thành phần chỉ số theo từng ngày quá khứ đến 2026.

**Quyết định:** ngày 13/10, Kỹ sư dữ liệu và thực nghiệm xin nhà trường/SSI xác nhận bằng văn bản: thời hạn dữ liệu, trường giá điều chỉnh, thành phần lịch sử, giới hạn truy vấn, quyền sử dụng học thuật và định dạng bàn giao. Đây là cổng bắt buộc trước khi công bố hiệu quả tài chính.

**Phương án dự phòng theo thứ tự:**

1. Dữ liệu có giấy phép do trường/giảng viên sở hữu.
2. Dữ liệu nhà cung cấp cho phép dùng nghiên cứu; lưu xác nhận và điều khoản.
3. Nếu chỉ có rổ hiện tại, dùng cho kiểm thử kỹ thuật, ghi rõ thiên lệch sống sót và không tuyên bố kết quả đại diện lịch sử.
4. Nếu chưa có quyền dùng dữ liệu giá, chạy thuật toán trên dữ liệu tổng hợp và chỉ báo cáo kỹ thuật.

Không dùng thư viện cộng đồng/endpoint không chính thức làm nguồn chính nếu chưa xác minh giấy phép, độ đầy đủ và nguồn gốc.

### 6.3. Tập mã đầu tư

Thành phần VN30 phải lấy theo ngày hiệu lực, không thay bằng danh sách hiện tại cho toàn bộ lịch sử. Quy tắc HOSE phiên bản 4.0 có hiệu lực từ 03/2025; factsheet 02/2026 chỉ là ảnh chụp tại thời điểm đó, không chứng minh thành phần những năm trước [8–10].

- **Chính:** cổ phiếu thuộc VN30 tại ngày hiệu lực từng kỳ nếu có lịch sử thành phần.
- **Kỹ thuật:** rổ VN30 tại ngày chốt dữ liệu; không dùng làm bằng chứng lịch sử sạch.
- **Mở rộng:** VN100, sau khi chuẩn hóa VN30.
- **Tập con lượng tử:** tại mỗi bài toán mẫu, xếp các mã đủ điều kiện theo ADTV 20 phiên gần nhất giảm dần, hòa thì xếp theo mã chứng khoán tăng dần; lấy N = 8, 12 hoặc 16 mã đầu. Khóa danh sách trước khi chạy bộ giải. Quy tắc chỉ dùng dữ liệu quá khứ.

Không chọn mã bằng cách nhìn vào lợi nhuận tương lai của tập kiểm tra.

### 6.4. Kiểm tra và lưu trữ

Mỗi lần nhập phải giữ tệp gốc, bản chuẩn hóa, báo cáo chất lượng, mã băm SHA-256, nguồn/ngày tải/quyền sử dụng/tham số truy vấn và phiên bản xử lý.

Kiểm tra bắt buộc:

1. Khóa (mã, ngày) không trùng.
2. Giá dương, khối lượng không âm.
3. Không tạo giá cho ngày nghỉ.
4. Phân biệt tạm ngừng, chưa niêm yết và lỗi thiếu.
5. Lợi nhuận cực đoan phải đối chiếu sự kiện doanh nghiệp.
6. Khoảng hiệu lực thành phần không chồng lấn; đổi mã lưu riêng.
7. Đặc trưng ở ngày t chỉ đọc dữ liệu không muộn hơn thời điểm quyết định.

---

## 7. Công thức danh mục và quy tắc đánh giá

### 7.1. Ước lượng rủi ro

Tại mỗi kỳ tái cân bằng:

- Cửa sổ ban đầu: 252 phiên gần nhất.
- Mã có dưới 126 phiên hợp lệ không được xét.
- Lợi nhuận ngày từ giá điều chỉnh.
- Lợi nhuận dùng trong hàm mục tiêu là trung bình số học của lợi nhuận ngày đã điều chỉnh, nhân 252: \(\mu_i=252\bar r_i\). Không dùng dự báo lợi nhuận riêng theo mã.
- Hiệp phương sai năm \(\Sigma=252\Sigma_d\).
- Đối chứng tài chính cơ sở: hiệp phương sai co rút Ledoit–Wolf. Nhánh AI dùng hiệp phương sai mẫu co về đường chéo theo hệ số \(\alpha\); đối chứng không AI trong cùng nhánh dùng \(\alpha=0.40\).
- Lưu số quan sát, tỷ lệ thiếu và số điều kiện ma trận.

Lợi nhuận trung bình lịch sử có sai số lớn. Báo thêm danh mục không dùng ước lượng lợi nhuận: tối thiểu rủi ro, chọn thanh khoản cao và tỷ trọng bằng nhau trên VN30.

### 7.2. Hàm mục tiêu

Với tỷ trọng bằng nhau, lợi nhuận kỳ vọng năm là \(\mu^\top x/K\), phương sai năm là \(x^\top\Sigma x/K^2\). Tối thiểu hóa:

\[
f(x)=\lambda\frac{x^\top\Sigma x}{K^2}
-\frac{\mu^{\top}x}{K},
\]

Trong đó, \(x_i\in\{0,1\}\), \(\mu_i\) là lợi nhuận kỳ vọng năm theo trung bình lịch sử ở mục 7.1 và \(\lambda\) là hệ số ngại rủi ro. AI không thay đổi \(\mu\); mọi bộ giải nhận đúng cùng một vector lợi nhuận.

Cấu hình kiểm tra λ cố định {2, 5, 10}; chọn trong huấn luyện/tập xác nhận, không theo tập kiểm tra khóa. K chính 6; độ nhạy K = 5, 8. Tất cả bộ giải dùng cùng dữ liệu, ma trận và hàm mục tiêu.

Không đưa tỷ lệ thay đổi danh mục hay phí giao dịch vào hàm mục tiêu QUBO của cấu hình chính. Tính riêng hai đại lượng này trong kiểm định lịch sử để mọi bộ giải dùng cùng một mục tiêu. Chỉ nghiên cứu hạng phạt tỷ lệ thay đổi danh mục như phần mở rộng đã đăng ký trước. Chuẩn hóa hệ số trước khi chuyển sang Ising; lưu hệ số và không làm tròn tùy tiện.

### 7.3. Phí và thực thi

Điểm cơ bản (basis point, viết tắt bps) bằng 0,01 phần trăm.

Chưa có vốn danh nghĩa hoặc biểu phí tài khoản cụ thể. Đặt vốn mô phỏng cơ sở \(V_0=100.000.000\) đồng; kiểm tra độ nhạy thêm 50.000.000 và 500.000.000 đồng. Đây là giả định để kiểm tra thanh khoản, không phải vốn của nhóm hay đề nghị đầu tư. Dùng các kịch bản chi phí gộp 10, 25, 50 điểm cơ bản (bps) trên tổng giá trị mua/bán; mức 25 là kịch bản giữa, không phải báo giá. Mức gộp đại diện phí, thuế và trượt giá; nếu có biểu phí chính thức, tách từng khoản và thay giả định này.

- Trước mỗi lần tái cân bằng, tính tỷ trọng trôi dạt \(w^{pre}_{i,t}=w^{target}_{i,t-1}(1+R_{i,t})/\sum_j w^{target}_{j,t-1}(1+R_{j,t})\), trong đó \(R_{i,t}\) là tổng lợi nhuận nắm giữ gồm điều chỉnh doanh nghiệp.
- Tỷ lệ thay đổi danh mục một chiều: \(0.5\sum_i|w^{target}_{i,t}-w^{pre}_{i,t}|\). Lần đầu tư đầu tiên được tính là mua 100% vốn.
- Tổng giá trị mua/bán: \(\sum_i|w^{target}_{i,t}-w^{pre}_{i,t}|\times\) vốn giả định.
- Chi phí = tỷ lệ giả định × giá trị mua/bán đã khớp thực tế.
- Giới hạn mỗi lệnh: 5% ADTV 20 phiên; lặp lại ở 1% và 10%.
- Giá trị lệnh mua/bán không vượt tỷ lệ tham gia đã chọn nhân ADTV 20 phiên; nếu vượt, chỉ khớp đến giới hạn và lưu phần chưa khớp.
- Tín hiệu sau giá đóng cửa phiên cuối tháng; khớp giả định ở giá mở cửa phiên kế tiếp. Nếu thiếu giá mở cửa cho một mã, không khớp lệnh của mã đó, giữ vị thế cũ, ghi sai lệch so với danh mục mục tiêu và dùng tỷ trọng thực tế làm đầu vào kỳ sau; không thay bằng giá đóng cửa cùng ngày.
- Kiểm tra lô tối thiểu, bước giá, quy tắc khớp lệnh theo thời điểm mô phỏng. Nếu chưa kiểm tra, gọi kết quả là danh mục lý thuyết.

### 7.4. Chỉ số báo cáo

Báo theo giai đoạn và toàn kỳ: CAGR, biến động năm hóa, Sharpe với lãi suất phi rủi ro được nêu rõ (tạm dùng 0% nếu không có chuỗi đáng tin), MDD, tỷ lệ thay đổi danh mục năm hóa (12 lần tỷ lệ một chiều trung bình tháng), lợi nhuận trước/sau phí, tỷ lệ tháng vượt đối chuẩn, chênh lệch và khoảng tin cậy, tính khả thi, độ lệch so với mục tiêu, số lần gọi bộ giải, thời gian, RAM/VRAM.

Với \(T\) kỳ nắm giữ tháng đầy đủ và lợi nhuận ròng tháng \(r_t\): \(CAGR=[\prod_{t=1}^{T}(1+r_t)]^{12/T}-1\); biến động năm hóa \(=\sqrt{12}\,SD(r_t)\); Sharpe năm hóa \(=\sqrt{12}\,\overline{(r_t-r_{f,t})}/SD(r_t-r_{f,t})\). Nếu không có chuỗi lãi suất phi rủi ro đáng tin, đặt \(r_{f,t}=0\) và ghi rõ. MDD là mức giảm lớn nhất của giá trị danh mục từ đỉnh lũy kế đến đáy sau đỉnh đó.

Đối chuẩn tối thiểu: VN30, tỷ trọng bằng nhau trên toàn bộ tập mã, chọn ngẫu nhiên K mã với giá trị khởi tạo ngẫu nhiên cố định. Không chọn riêng đối chuẩn thuận lợi.

---

## 8. Lớp AI

### 8.1. Ranh giới

AI là bộ ước lượng xác suất nhỏ, không phải tác nhân tự động được tự do chọn mã. AI không được thay tập mã, hàm mục tiêu, chỉ số đánh giá, nhãn hoặc quy tắc sau khi xem tập kiểm tra; không gọi API để quyết định giao dịch; không sửa mã trong khi chạy. LLM chỉ được dùng tùy chọn để tóm tắt tài liệu hoặc hỗ trợ lập trình; không nằm trong vòng quyết định đầu tư. Ngân sách API cho quy trình lõi bằng 0.

### 8.2. Mô hình chốt

Mô hình học trên các ngày giao dịch, nhưng chỉ phát xác suất tại phiên quyết định tái cân bằng tháng. Ký hiệu \(r_{m,d}=\ln(I_d/I_{d-1})\) là lợi nhuận logarit ngày của chỉ số thị trường đến ngày \(d\). Mọi đặc trưng tại ngày \(t\) chỉ dùng dữ liệu có ngày không muộn hơn \(t\).

**Đặc trưng tại ngày \(t\):**

1. Biến động chỉ số năm hóa \(\sigma_{m,L,t}=\sqrt{252}\,\mathrm{SD}(r_{m,d})\) trên \(L\in\{20,60,120\}\) phiên kết thúc tại \(t\), với độ lệch chuẩn mẫu.
2. Lợi nhuận chỉ số cộng dồn trong 20 và 60 phiên: \(R_{m,L,t}=\exp(\sum_{d=t-L+1}^{t}r_{m,d})-1\).
3. Trung vị tương quan Pearson 60 phiên giữa từng cặp thành viên VN30 đủ điều kiện dữ liệu, trước khi chọn K mã; chỉ dùng cặp có ít nhất 50 quan sát hợp lệ trong cửa sổ đó.
4. Tỷ số biến động ngắn/dài \(\sigma_{m,20,t}/\max(\sigma_{m,120,t},10^{-12})\).
5. Tỷ lệ thành viên chỉ số có ít nhất 126 phiên giá hợp lệ trong 252 phiên gần nhất, tính trước khi lọc mã đầu tư.
6. Tỷ lệ thành viên chỉ số tạm ngừng giao dịch tại \(t\), chỉ dùng nếu nguồn dữ liệu có trạng thái lịch sử đáng tin cậy; nếu không có, bỏ đặc trưng này trong toàn bộ thí nghiệm.
7. Trung vị \(\ln(1+\mathrm{ADTV}_{20})\) giữa các mã đủ điều kiện, trong đó ADTV là giá trị giao dịch bình quân 20 phiên và \(\ln\) là logarit tự nhiên.

Chuẩn hóa từng đặc trưng bằng trung bình và độ lệch chuẩn tính trên mẫu huấn luyện của lần khớp mô hình tương ứng. Ký hiệu \(z_t\) là vector gồm bảy đặc trưng đã chuẩn hóa. Không đưa sai số dự báo lợi nhuận vào vì thiết kế không có mô hình dự báo lợi nhuận riêng.

**Nhãn:** \(v_{t}^{+}=\sqrt{252}\,\mathrm{SD}(r_{m,t+1},\ldots,r_{m,t+21})\). Đặt \(y_t=1\) nếu \(v_t^{+}\) lớn hơn phân vị 70% của \(v^{+}\) trong mẫu huấn luyện; ngược lại \(y_t=0\). Phân vị chỉ được tính từ nhãn đã trưởng thành trong tập huấn luyện của lần khớp mô hình. Mẫu có ngày kết thúc nhãn sau ngày khớp bị loại khỏi huấn luyện; như vậy có khoảng cách ít nhất 21 phiên.

**Mô hình:** hồi quy logistic với phạt L2, không cân bằng lại lớp để giữ ý nghĩa xác suất. Thử \(C\in\{0.01,0.1,1,10\}\), dùng log-loss (hàm mất mát logarit) trên giai đoạn xác nhận; chọn giá trị thấp nhất, nếu hòa chọn \(C\) nhỏ hơn. Thống kê chuẩn hóa và ngưỡng nhãn đều chỉ được tính từ tập huấn luyện. Không dùng lợi nhuận danh mục tập kiểm tra để chọn siêu tham số.

**Đầu ra tại ngày tái cân bằng:** xác suất \(p_t=P(y_t=1\mid z_t)\), rồi:

\[
\lambda_t=2+8p_t,\qquad \alpha_t=0.10+0.60p_t.
\]

\(\lambda_t\in[2,10]\) điều chỉnh ngại rủi ro; \(\alpha_t\in[0.10,0.70]\) co hiệp phương sai về đường chéo:

\[
\Sigma_t^{AI}=(1-\alpha_t)\Sigma_t^{\text{mẫu}}
+\alpha_t\operatorname{diag}(\Sigma_t^{\text{mẫu}}).
\]

Trong công thức này, \(\Sigma_t^{\text{mẫu}}\) là hiệp phương sai mẫu năm hóa ở mục 7.1. Đối chứng ngoài nhánh AI dùng hiệp phương sai co rút Ledoit–Wolf.

Đây là cấu hình nghiên cứu, chưa phải giá trị đã tối ưu. Cấu hình không AI trong cùng họ dùng \(\lambda=5,\alpha=0.40\). Chỉ được sửa trước khi mở tập kiểm tra cuối và phải ghi phiên bản, lý do.

### 8.3. Thí nghiệm loại bỏ từng thành phần

So bốn cấu hình cùng bộ giải và thời điểm, cộng một đối chứng tài chính riêng:

1. Không AI trong cùng họ mô hình: λ = 5, α = 0,40.
2. AI điều chỉnh λ; α = 0,40.
3. AI điều chỉnh α; λ = 5.
4. AI điều chỉnh cả λ và α.
5. Đối chứng tài chính riêng: λ = 5, hiệp phương sai Ledoit–Wolf.

Nếu cấu hình 4 không cải thiện ngoài mẫu so với cấu hình 1, không kết luận AI tạo giá trị.

Nếu sau khi loại bỏ các phiên chồng lấn, mẫu tập huấn luyện còn dưới 500 ngày hoặc một vòng kiểm định chỉ có một lớp nhãn, không dùng mô hình để kết luận tài chính. Dùng quy tắc biến động cố định và ghi “chưa đủ dữ liệu xác nhận AI”.

---

## 9. Công thức QUBO và Ising

### 9.1. X-mixer với hạng phạt

Viết hàm mục tiêu nhị phân:

\[
f(x)=\sum_i a_ix_i+\sum_{i<j}b_{ij}x_ix_j,
\]
\[
a_i=\lambda\frac{\Sigma_{ii}}{K^2}-\frac{\mu_i}{K},
\qquad b_{ij}=2\lambda\frac{\Sigma_{ij}}{K^2}.
\]

Phạt trường hợp số mã được chọn khác K:

\[
P(x)=A\left(\sum_i x_i-K\right)^2
=A\left[(1-2K)\sum_i x_i+2\sum_{i<j}x_ix_j+K^2\right].
\]

Vậy \(a_i'=a_i+A(1-2K)\), \(b_{ij}'=b_{ij}+2A\). Hạng hằng AK² không đổi nghiệm nhưng phải lưu để đối chiếu năng lượng.

Tại N nhỏ, tính \(\Delta_f=\max f-\min f\) trên toàn bộ chuỗi bit; đặt A = \(\Delta_f+\epsilon\), với \(\epsilon=1\%\max(\Delta_f,10^{-12})\). Tại N lớn, dùng cận dao động \(\sum_i|a_i|+\sum_{i<j}|b_{ij}|\), cộng 1%. Kiểm tra A/2, A, 2A. Không chọn A theo tập kiểm tra khóa.

### 9.2. XY-mixer

Với XY-mixer, dùng hàm mục tiêu gốc \(f(x)\), không cộng hạng phạt số mã được chọn. Khởi tạo chuỗi bit có đúng K bit 1. Bộ trộn gồm các cặp liền kề trên vòng với hạng \(X_iX_j+Y_iY_j\), bảo toàn số bit 1. Dùng tối thiểu ba khởi tạo khả thi. Mạch chuẩn bị trạng thái Dicke đều chỉ là phép thử phụ vì chi phí chuẩn bị phải tính vào toàn quy trình.

### 9.3. Chuyển Ising và kiểm thử

Dùng quy ước \(x_i=(1-Z_i)/2\). Với QUBO \(Q(x)=c_Q+\sum_i a_ix_i+\sum_{i<j}b_{ij}x_ix_j\), Hamiltonian Ising là:

\[
H_C=c_I+\sum_i h_iZ_i+\sum_{i<j}J_{ij}Z_iZ_j,
\quad J_{ij}=\frac{b_{ij}}{4},
\quad h_i=-\frac{a_i}{2}-\frac14\sum_{j\ne i}b_{\min(i,j),\max(i,j)},
\]
\[
c_I=c_Q+\frac12\sum_i a_i+\frac14\sum_{i<j}b_{ij}.
\]

Với X-mixer, dùng \(a'_i,b'_{ij}\) đã cộng hạng phạt và \(c_Q=AK^2\). Với XY-mixer, dùng hệ số hàm mục tiêu gốc và không cộng hạng phạt. Lưu dấu, hằng số và quy ước tối thiểu hóa; nếu thư viện tối đa hóa, đảo dấu đúng một lần và kiểm tra lại.

Kiểm thử bắt buộc với N ≤ 10:

1. Liệt kê toàn bộ \(2^N\) chuỗi bit.
2. Tính trực tiếp hàm mục tiêu gốc, QUBO và năng lượng Ising.
3. Sai số tuyệt đối < \(10^{-9}\), tính cả hằng số tự do.
4. Nghiệm tối ưu khả thi trùng nhau.
5. XY giữ đúng trọng số Hamming K.
6. Kiểm tra thứ tự bit và ánh xạ bit i sang mã tài sản i.

Với N = 30 có tối đa 30 đường chéo và 435 cặp ngoài đường chéo; QUBO là dày. Ghi số hệ số khác 0. Không cắt tương tác nhỏ nếu chưa có thí nghiệm loại bỏ thành phần đo sai số.

---

## 10. QAOA và phần cứng

### 10.1. Cấu hình mạch

Đặt \(H_C\) là Hamiltonian Ising của mục 9.3. Mỗi lớp lần lượt áp dụng \(U_C(\gamma_\ell)=e^{-i\gamma_\ell H_C}\), rồi \(U_M(\beta_\ell)=e^{-i\beta_\ell H_M}\); lặp \(p\) lớp và đo trên cơ sở tính toán. Với X-mixer, \(H_M=\sum_iX_i\), trạng thái đầu là \(|+\rangle^{\otimes N}\). Với XY-mixer, \(H_M=\sum_{(i,j)\in E}(X_iX_j+Y_iY_j)\), trong đó \(E\) là vòng liên thông gồm các cặp kề nhau và cặp cuối–đầu; trạng thái đầu là chuỗi cơ sở có đúng K bit 1. Hạng này bảo toàn số bit 1.

Cấu hình:

- p = 1 chính; p = 2 độ nhạy; p = 3 chỉ khi còn tài nguyên.
- COBYLA là bộ tối ưu chính, tối đa 50 đánh giá hàm mục tiêu mỗi giá trị khởi tạo ngẫu nhiên.
- SPSA chỉ khi nhiễu lấy mẫu làm COBYLA không ổn định; tính ít nhất hai lần đánh giá mỗi vòng và vẫn giới hạn tổng số lần đánh giá ở 50 cho mỗi giá trị khởi tạo.
- Ba bộ góc khởi tạo ngẫu nhiên trong [-π, π]. Chuyển góc từ bài toán mẫu trước chỉ là nhánh phụ và phải thay một trong ba lần khởi tạo, không cộng thêm lượt chạy vào ngân sách chính.
- Lưu góc, năng lượng, số lần đo, số lần gọi, thời gian, tỷ lệ nghiệm khả thi, biểu đồ phân bố, số cổng, độ sâu mạch và thiết bị.

Dùng PCG64 với giá trị khởi tạo 11, 23, 47. Với X-mixer, trạng thái đầu luôn là \(|+\rangle^{\otimes N}\); với XY-mixer, dùng từng giá trị khởi tạo để xáo trộn thứ tự N mã và đặt bit 1 cho K mã đầu tiên của hoán vị. Sinh các góc ban đầu độc lập, đều trong [-π, π]. Lưu chuỗi bit đầu và góc để chạy lại đúng cấu hình.

COBYLA tối thiểu hóa giá trị kỳ vọng ước lượng của \(H_C\) từ lần đo. Báo riêng giá trị kỳ vọng, nghiệm khả thi tốt nhất đã lấy mẫu và tỷ lệ chuỗi đo khả thi; không thay thế một chỉ số bằng chỉ số khác.

### 10.2. Tầng mô phỏng

| Tầng | Mục đích | Giới hạn |
|---|---|---|
| Vector trạng thái chính xác CPU/GPU | Tối ưu góc và đối chiếu nghiệm lý tưởng | RAM tăng theo \(2^N\), không mô phỏng đầy đủ lỗi |
| Mô phỏng lấy mẫu | Đo nhiễu do số lần đo hữu hạn | Chưa có lỗi phần cứng nếu thiếu mô hình nhiễu |
| Mô phỏng nhiễu | Ước lượng độ nhạy theo mô hình nhiễu | Chỉ đúng trong giới hạn của mô hình |
| QPU thật | Đo ánh xạ, cổng, lần đo và nhiễu thực tế | Không thể suy ra ưu thế lượng tử từ một lần chạy |

QPU chỉ chạy sau khi mạch, ánh xạ, thứ tự bit và hàm mục tiêu đã qua kiểm thử. Nếu không có QPU, dùng mô phỏng; đây không phải điều kiện chặn.

### 10.3. Quy mô và ngưỡng gửi QPU

- Phát triển logic: N = 4, 6, 8.
- So sánh: N = 8, 12, 16.
- Nếu được cấp quyền QPU, ưu tiên N = 8, 12; N = 16 là mức mở rộng tùy theo số cổng và độ sâu mạch.
- VN30: duyệt chính xác toàn bộ tổ hợp và QAOA máy mô phỏng; không yêu cầu chạy đủ 30 qubit trên QPU.
- QPU: 512 lần đo mỗi điểm tham số; lên 1.024 lần đo cho nghiệm cuối nếu đủ hạn mức.
- Không vượt 0,8 triệu lần đo kế hoạch nếu chưa được chấp thuận.

Chỉ gửi mạch nếu công thức đúng; XY cho tỷ lệ nghiệm khả thi ≥ 90% trong mô phỏng lý tưởng hoặc hạng phạt X đã thử 3 mức; số cổng/độ sâu sau biên dịch được lưu; mô phỏng lấy mẫu dùng ít nhất 512 lần đo; còn ngân sách cho 3 giá trị khởi tạo ngẫu nhiên; tải được bảng đếm thô và siêu dữ liệu.

---

## 11. Đối chứng cổ điển và đối chuẩn

### 11.1. Đối chứng

1. Duyệt chính xác toàn bộ tổ hợp nếu N ≤ 30, K ≤ 6 hoặc số tổ hợp dưới 2 triệu.
2. Mô phỏng tôi luyện (simulated annealing) cho bài toán mẫu lớn hơn; lịch làm nguội được khóa trước.
3. Tham lam chọn lần lượt mức tăng hàm mục tiêu nhỏ nhất.
4. Tổ hợp khả thi ngẫu nhiên với giá trị khởi tạo ngẫu nhiên cố định.
5. Bộ giải tối ưu bậc hai với biến nguyên hỗn hợp (MIQP, Mixed-Integer Quadratic Programming) nếu trường có quyền truy cập; ghi phiên bản/cấu hình.

Duyệt chính xác mọi tổ hợp là chuẩn tối ưu toàn cục tại cỡ nhỏ, không phải một phương pháp gần đúng yếu.

### 11.2. Công bằng

- Cùng dữ liệu, hàm mục tiêu, ràng buộc và bài toán mẫu.
- Tính thời gian tiền xử lý, biên dịch mạch, tối ưu góc, đo và hậu xử lý.
- So chất lượng tại cùng ngân sách đánh giá hàm mục tiêu hoặc trình bày đường cong theo ngân sách.
- QPU: báo hàng đợi nếu có, tách thiết bị và thời gian tường.
- So nhiều lần khởi tạo QAOA với cùng số lần khởi tạo của phương pháp gần đúng.
- Nghiệm chính xác làm đối chứng dùng hàm mục tiêu gốc; hạng phạt/hằng số tự do không làm lệch khoảng cách được báo cáo.

---

## 12. Ma trận thí nghiệm và quy tắc kết luận

| Nhánh | AI | Bộ giải | Bộ trộn | N, K | Mục tiêu |
|---|---|---|---|---|---|
| A | Tắt | Nghiệm chính xác | — | 8–30, K=5–6 | Chuẩn nghiệm và thời gian CPU |
| B | Tắt | Tham lam/mô phỏng tôi luyện | — | 8–60 | Đối chứng phương pháp gần đúng |
| C | Tắt | QAOA | X | 8, 12, 16 | Tỷ lệ khả thi, độ lệch so với mục tiêu, số cổng, thời gian |
| D | Tắt | QAOA | XY | 8, 12, 16 | Bảo toàn ràng buộc |
| E | Bật/tắt | Nghiệm chính xác hoặc bộ giải cố định | — | Kiểm định lịch sử VN30 | Đóng góp AI |
| F | Bật/tắt | Quy trình đầy đủ | — | N=30, K=6 | Sau phí |
| G | Tắt | QPU nếu có | X/XY | 8, 12 | Nhiễu phần cứng |

Mỗi cấu hình C/D chạy ba giá trị khởi tạo ngẫu nhiên và tối đa 50 lần đánh giá hàm mục tiêu. Khóa ngày của bài toán mẫu trước khi xem kết quả.

Chọn 12 ngày tái cân bằng trong tập huấn luyện, không lấy từ tập kiểm tra. Tính biến động chỉ số 60 phiên tại từng ngày; chia theo phân vị 33% và 67% của tập huấn luyện, rồi chọn 4 ngày cách đều theo thời gian trong mỗi nhóm thấp, giữa và cao. Với từng ngày, tạo ba bài toán K = 6 bằng cách xếp thành viên chỉ số đủ điều kiện theo ADTV 20 phiên giảm dần, lấy N = 8, 12, 16; hòa thì xếp theo mã chứng khoán tăng dần. Như vậy có 36 bài toán.

Nếu không có dữ liệu lịch sử đủ quyền, thay bằng 12 bài toán tổng hợp được khóa trước và ghi rõ đây chỉ là kiểm tra thuật toán. Dùng bộ sinh NumPy Generator(PCG64) với các giá trị khởi tạo từ 20261012 đến 20261023; mỗi bài toán tạo ma trận tải nhân tố \(B\in\mathbb{R}^{16\times3}\) có phần tử lấy theo phân phối chuẩn với kỳ vọng 0 và độ lệch chuẩn 0,05. Lấy độ lệch chuẩn riêng năm hóa \(s_i\) theo phân phối đều trong [0,15; 0,35] và lợi nhuận kỳ vọng năm \(\mu_i\) theo phân phối đều trong [-0,05; 0,20]. Đặt \(\Sigma=BB^\top+\operatorname{diag}(s_i^2)\); với mỗi N, lấy N hàng/cột đầu và K = 6. Không gộp kết quả tổng hợp với kết quả từ dữ liệu thị trường.

Dùng các mẫu này cho đối chứng chính xác và mô phỏng. Kế hoạch QPU hẹp hơn: lấy ngày giữa có thứ tự sớm nhất trong nhóm biến động trung bình, hoặc bài toán tổng hợp đầu tiên nếu thiếu dữ liệu; chạy một bài toán đã khóa cho mỗi N = 8 và N = 12. Hạn mức 0,8 triệu lần đo không bao phủ cả 12 ngày. Kiểm định lịch sử danh mục vẫn dùng toàn bộ kỳ đánh giá.

**Kết luận AI:** chỉ khi hiệu quả ròng ngoài mẫu tốt hơn, kèm khoảng tin cậy, tỷ lệ thay đổi danh mục và kết quả theo giai đoạn.  
**Kết luận bộ giải:** độ lệch so với mục tiêu và tỷ lệ nghiệm khả thi tại ngân sách tương đương.  
**Kết luận thời gian:** tổng từ đầu vào đến nghiệm đạt chất lượng, gồm tối ưu góc, biên dịch mạch, số lần đo và hậu xử lý.  
**Kết luận đầu tư:** lợi nhuận sau phí, thanh khoản và đối chuẩn trên tập kiểm tra.  
**Chưa đủ bằng chứng:** thiếu thành phần lịch sử, mẫu nhỏ, khoảng tin cậy rộng, kết quả lệ thuộc giá trị khởi tạo ngẫu nhiên hoặc giả định phí.

Không dùng cụm “ưu thế lượng tử” nếu chưa chứng minh ưu thế theo cùng chất lượng nghiệm và tổng ngân sách tính toán trên bài toán mẫu đại diện.

---

## 13. Kiểm định lịch sử và rò rỉ dữ liệu

### 13.1. Chia thời gian

Nếu có dữ liệu sạch/quyền sử dụng:

- Tập huấn luyện ban đầu: 2018-01 đến 2021-12; mô hình học từ các ngày giao dịch, không chỉ từ ngày tái cân bằng tháng.
- Tập xác nhận: 2022-01 đến 2023-12; dùng để chọn \(C\), sau đó khóa \(C\) và mọi quy tắc tiền xử lý.
- Tập kiểm tra khóa: 2024-01 đến tháng đầy đủ gần nhất, dự kiến 2026-09.
- Tháng 10/2026 chưa hoàn tất nên không dùng là tháng tập kiểm tra hoàn chỉnh.
- Lưu riêng ngày quyết định, ngày giao dịch và ngày có dữ liệu.

Tập kiểm tra khóa việc chọn đặc trưng, ngưỡng, siêu tham số và quy tắc đánh giá. Trong mô phỏng triển khai tuần tự, tại mỗi quyết định tháng khớp lại mô hình bằng cửa sổ mở rộng gồm mọi mẫu huấn luyện có nhãn đã hoàn tất ít nhất 21 phiên trước ngày quyết định. Giữ nguyên \(C\) đã chọn; chỉ cập nhật hệ số, thống kê chuẩn hóa và ngưỡng phân vị bằng dữ liệu quá khứ; tính lại nhãn huấn luyện theo ngưỡng của lần khớp đó. Nhãn có cửa sổ tương lai chạm qua ranh giới tập được loại khỏi tập huấn luyện tương ứng. Không chuẩn hóa toàn bộ dữ liệu trước khi tách thời gian. Lợi nhuận kiểm tra chỉ được tính cho các kỳ nắm giữ đã kết thúc đầy đủ.

Nếu không xác minh được thành phần chỉ số lịch sử, chia thời gian không khắc phục thiên lệch sống sót; kết quả chỉ là kỹ thuật/minh họa.

### 13.2. Chuỗi vận hành tháng

1. Chốt dữ liệu đến phiên cuối tháng.
2. Kiểm tra giá, phiên và trạng thái.
3. Tạo tập mã theo thành phần chỉ số có hiệu lực.
4. Tạo đặc trưng từ quá khứ.
5. Áp dụng mô hình theo lịch đã khóa.
6. Ước lượng μ, Σ.
7. Tạo hàm mục tiêu/QUBO.
8. Chạy bộ giải đã đăng ký.
9. Chọn đúng K mã và đặt tỷ trọng mục tiêu bằng nhau.
10. Mua/bán tại giá mở cửa phiên kế tiếp; nắm giữ đến lần thực thi tháng sau. Tính lợi nhuận từ giá thực thi đến giá thực thi tiếp theo, có điều chỉnh hành động doanh nghiệp.
11. Lưu lợi nhuận đến kỳ sau và cấu hình.

Nếu giá mở cửa thiếu cho một mã, không khớp lệnh mã đó, giữ vị thế cũ, thực hiện các lệnh còn đủ giá và ghi tỷ trọng sau giao dịch thực tế. Lần tái cân bằng tiếp theo dùng chính tỷ trọng thực tế này để tính giao dịch.

### 13.3. Thống kê

Tính chênh lệch chiến lược–đối chuẩn theo cùng tháng; lấy mẫu lại theo khối tháng độ dài 3 và 6 với 10.000 lần lặp; báo khoảng tin cậy phần trăm 95%, số tháng, số vòng kiểm định và lượt thử. Nếu thử nhiều cấu hình, ghi đủ số lần. Có thể bổ sung PBO/CSCV khi đủ dữ liệu [5] nhưng không thay tập kiểm tra khóa. Không suy diễn từ một Sharpe hay một lần chạy.

---

## 14. Kiến trúc phần mềm

### 14.1. Luồng

~~~mermaid
flowchart LR
    A[Nhà cung cấp dữ liệu] --> B[Nhập và đóng dấu phiên bản]
    B --> C[Kiểm tra chất lượng]
    C --> D[Đặc trưng và lợi nhuận]
    D --> E[Ước lượng rủi ro]
    D --> F[Bộ điều chỉnh AI]
    E --> G[Tạo hàm mục tiêu và QUBO]
    F --> G
    G --> H[Nghiệm chính xác và phương pháp gần đúng]
    G --> I[QAOA máy mô phỏng]
    I --> J[QPU nếu được cấp]
    H --> K[Chấm nghiệm/danh mục]
    I --> K
    J --> K
    K --> L[Kiểm định lịch sử sau phí]
    L --> M[Nhật ký, bảng và bảng theo dõi]
~~~

### 14.2. Thành phần

| Thành phần | Đầu vào/đầu ra | Quy tắc |
|---|---|---|
| Nhập dữ liệu | giao diện lập trình ứng dụng/tệp → bản gốc, siêu dữ liệu | Không ghi khóa bí mật vào nhật ký |
| Kiểm tra | Bản gốc → lỗi, dữ liệu chuẩn hóa | Dừng khi lỗi nghiêm trọng |
| Đặc trưng | Dữ liệu → bảng tại t | Không đọc tương lai |
| Rủi ro | Lợi nhuận → μ, Σ, cờ chất lượng | Lưu cửa sổ và phương pháp |
| AI | Đặc trưng → p, λ, α | Kẹp đúng miền |
| QUBO | μ, Σ, K, λ, A → ma trận/hằng số | Có kiểm thử đơn vị |
| Bộ giải | QUBO → chuỗi bit/nhật ký | Không tự đổi hàm mục tiêu |
| Kiểm định lịch sử | nghiệm/giá/phí → giá trị danh mục và chỉ số đánh giá | Giao dịch sau tín hiệu |
| Theo dõi | cấu hình/kết quả → CSV/JSON | Mỗi lần chạy có mã lần chạy |
| Bảng theo dõi | tệp kết quả → bảng/biểu đồ | Chỉ hiển thị, không chứa bộ giải |

### 14.3. Thư viện

Chọn Qiskit làm bộ công cụ phát triển phần mềm chính vì có tài liệu về danh mục với ràng buộc số mã được chọn và bộ trộn XY, cùng Qiskit Aer cho CPU/GPU. Không triển khai đồng thời Qiskit và PennyLane trước bán kết. Chỉ thêm PennyLane để kiểm chứng độc lập nếu có người phụ trách và không làm trễ. Dùng scikit-learn cho hồi quy logistic; không thêm PyTorch nếu chưa có thí nghiệm cần mạng sâu. Khóa phiên bản thư viện trong tệp môi trường.

---

## 15. Đề nghị cấp phát tài nguyên

### 15.1. Ba cấu hình

| Tài nguyên | Tối thiểu | Khuyến nghị xin | Mở rộng |
|---|---:|---:|---:|
| CPU | 8 lõi ảo | 16 lõi ảo | 32 lõi ảo |
| RAM | 16 GB | 64 GB | 128 GB |
| GPU | Không bắt buộc | 1 NVIDIA, VRAM 24 GB, tối đa 40 GPU-giờ | 2 GPU nếu đo được nhu cầu |
| SSD | 20 GB | 100 GB | 250 GB |
| Thời gian cấp | 2 tuần | 4 tuần, 12/10–10/11 | Gia hạn sau thử nghiệm thăm dò |
| QPU | Không bắt buộc | N=8–12, trần kế hoạch ~0,8 triệu lần đo | Chỉ mở rộng sau phê duyệt |
| Dữ liệu | Mẫu có quyền | Giá + thành phần lịch sử có xác nhận | VN100 sau VN30 |
| LLM API | 0 lõi | 0 bắt buộc; tùy chọn 1 triệu token hỗ trợ tài liệu nếu duyệt riêng | Không nằm ngân sách GPU/QPU |

Mức 1 triệu token là trần tùy chọn, không phải nhu cầu của quy trình. Chưa chọn nhà cung cấp/mô hình nên chưa thể ghi chi phí tiền mặt. Nếu được duyệt, chi phí tính theo bảng giá chính thức tại ngày sử dụng: (token đầu vào ÷ 1.000.000 × đơn giá đầu vào) + (token đầu ra ÷ 1.000.000 × đơn giá đầu ra).

### 15.2. Dung lượng dữ liệu

Giả định dự phòng 100 mã, 2.600 phiên từ năm khởi động đến 2026, 10 trường số mỗi mã/ngày:

\[
100\times2.600\times10\times8=20.800.000\ \text{byte}\approx19,8\ \text{MiB}.
\]

Đây là số thô 64-bit, chưa gồm định dạng, phiên bản điều chỉnh, nhật ký và siêu dữ liệu. 20 GB tối thiểu, 100 GB khuyến nghị chủ yếu dành cho nhiều bản dữ liệu, môi trường, nhật ký, điểm khôi phục và biểu đồ; giá ngày đơn thuần không cần hàng chục GB.

### 15.3. Khối lượng duyệt tổ hợp trên CPU

Từ 2018-01 đến 2026-09 có tối đa 105 kỳ tháng. Nếu chạy VN30, K=6 ở mọi kỳ, trần số danh mục được chấm là 105 × 593.775 = 62.346.375. Đây là số danh mục ứng viên, không phải thời gian chạy đã đo; cần tính theo lô và chạy thử nghiệm thăm dò. Đề nghị 16 lõi để xử lý nhiều kỳ và giá trị khởi tạo ngẫu nhiên song song; đo thời gian thực tế trên nút tính toán được cấp.

### 15.4. RAM vector trạng thái

Với số phức 128-bit:

\[
M(N)=16\times2^N\ \text{byte}.
\]

| Qubit | Trạng thái thuần | Nhận định |
|---:|---:|---|
| 20 | 16 MiB | Thoải mái CPU |
| 24 | 256 MiB | Phù hợp lặp |
| 26 | 1 GiB | Cần thêm bộ đệm |
| 28 | 4 GiB | Cần tính thêm bộ nhớ phụ đáng kể |
| 30 | 16 GiB | 64 GB RAM an toàn hơn |
| 32 | 64 GiB | Vượt RAM 64 GB khi tính bộ nhớ phụ |

Thực tế cần nhiều hơn vector trạng thái thuần. 40 GPU-giờ là **trần dự phòng đề nghị**, chưa phải thời gian chạy đã đối chuẩn. Chạy thử nghiệm thăm dò 12/16/20 qubit trong hai ngày đầu, đo thời gian mỗi lần đánh giá và bộ nhớ đỉnh rồi mới đặt lịch mở rộng. Không vượt 28 qubit trên GPU 24 GB nếu chưa đo đúng nền tảng thực thi.

### 15.5. Ngân sách QPU

Phép tính hạn mức:

- Hạn mức bao phủ một bài toán mẫu đã khóa cho mỗi cỡ N = 8 và N = 12; không bao phủ 12 ngày kiểm tra bằng mô phỏng.
- 2 cỡ N = 8, 12.
- 2 bộ trộn.
- 2 độ sâu p = 1, 2.
- 3 giá trị khởi tạo ngẫu nhiên.
- 50 đánh giá mỗi cấu hình.

Tổng \(2\times2\times2\times3\times50=1.200\) lần đánh giá hàm mục tiêu. Với 512 lần đo mỗi lần đánh giá, tổng cơ sở là 614.400 lần đo. Cộng 25% dự phòng là 768.000; xin trần kế hoạch 0,8 triệu. Nếu đo lại nghiệm cuối với 1.024 lần đo, phần tăng thêm tính vào cùng hạn mức; phải giảm số lần chạy khác để không vượt trần.

Đây là kế hoạch, không phải hạn mức đã được xác nhận. Nếu bộ tối ưu vượt 50 lần đánh giá, không tự tăng ngân sách; giảm số cấu hình hoặc tối ưu trên máy mô phỏng. Chi phí tiền mặt chưa thể ước lượng khi chưa có nhà cung cấp, gói dịch vụ, hạn mức và báo giá. Xin quyền truy cập học thuật trước, không điền giá giả định.

### 15.6. Bảng đề nghị gửi thầy

| Hạng mục | Mức xin | Lý do | Bằng chứng bàn giao |
|---|---|---|---|
| CPU/RAM | 16 lõi, 64 GB trong 4 tuần | Nghiệm chính xác, máy mô phỏng, kiểm định lịch sử và xử lý song song | Thời gian chạy, RAM đỉnh, cấu hình |
| GPU | 1 NVIDIA 24 GB, tối đa 40 giờ | Vector trạng thái và lô nhiều giá trị khởi tạo ngẫu nhiên | Đo CPU/GPU cùng mạch, VRAM |
| SSD | 100 GB | Dữ liệu có quyền, nhật ký, môi trường | Danh mục tệp, mã băm, dung lượng |
| QPU | N=8–12, trần khoảng 0,8 triệu lần đo | Đo nhiễu, biên dịch mạch và mạch thật | mạch, siêu dữ liệu, lần đo, tính khả thi |
| Dữ liệu | Giá và thành phần lịch sử có quyền | Tránh thiên lệch sống sót | Xác nhận nguồn/phạm vi/quyền |
| API cho LLM | Không xin cho quy trình lõi | LLM không quyết định danh mục | Không có lượt gọi giao diện lập trình ứng dụng trong cấu hình chính |

GPU/QPU phục vụ kiểm định lượng tử, không phải vì kiểm định lịch sử VN30 hoặc hồi quy logistic không chạy được trên máy thông thường. Nếu chỉ có CPU, nhóm vẫn hoàn thành công thức, đối chứng chính xác, thử nghiệm nhỏ và báo cáo.

### 15.7. Độ tin cậy

| Ước lượng | Tin cậy | Ghi chú |
|---|---|---|
| Dung lượng dữ liệu ngày | Cao | Tính theo số mã/phiên/cột |
| RAM vector trạng thái thuần | Cao | Công thức chính xác, chưa gồm bộ nhớ phụ |
| RAM đỉnh | Trung bình | Tùy phiên bản/nền tảng thực thi |
| 40 GPU-giờ | Thấp–trung bình | Hạn mức dự phòng, chưa đo |
| 0,8 triệu lần đo | Trung bình | Từ ma trận thí nghiệm, phụ thuộc nền tảng thực thi |
| Thời gian/chi phí QPU | Chưa xác nhận | Cần nhà cung cấp |
| 100 GB SSD | Cao | Có khoảng đệm lớn |

---

## 16. Lịch tiến độ và phân công

### 16.1. Mốc thực hiện

| Hạn | Công việc | Người phụ trách | Điều kiện hoàn thành |
|---|---|---|---|
| 13/10 | Xin dữ liệu; khóa hàm mục tiêu, K và thư viện | Trưởng nhóm kỹ thuật + Trưởng nhóm tài chính | Cấu hình, thư yêu cầu |
| 14/10 | Nhập mẫu, kiểm cấu trúc dữ liệu, dựng dữ liệu tổng hợp | Kỹ sư dữ liệu | Báo cáo dữ liệu/mã băm |
| 15/10 | Kiểm thử đơn vị gốc→QUBO→Ising; chính xác N≤12 | Trưởng nhóm kỹ thuật | Tất cả kiểm thử qua |
| 17/10 | Đối chứng cổ điển, QAOA N=8/12 | Trưởng nhóm kỹ thuật và kỹ sư dữ liệu | Ba giá trị khởi tạo ngẫu nhiên, khoảng cách, thống kê mạch |
| 19/10 | Logistic và kiểm định cuốn chiếu kỹ thuật | Trưởng nhóm kỹ thuật và trưởng nhóm tài chính | Dự đoán theo thời điểm, kiểm tra rò rỉ thông tin |
| 21/10 | Kiểm định lịch sử sơ bộ hoặc kết luận cổng dữ liệu chưa đạt | Trưởng nhóm tài chính và kỹ sư dữ liệu | Bảng phí/đối chuẩn, giới hạn |
| 23/10 | Rà soát phản biện và demo | Cả nhóm | Không trình bày kết quả chưa chạy |
| 25/10 | Bàn giao bán kết | Phụ trách sản phẩm | Slide, demo dự phòng, nhật ký |
| 26–31/10 | Mở rộng kiểm định cuốn chiếu/thí nghiệm loại bỏ thành phần | Trưởng nhóm kỹ thuật và trưởng nhóm tài chính | Kết quả khóa cấu hình |
| 01–04/11 | QPU nếu có; nếu không máy mô phỏng có nhiễu | Trưởng nhóm kỹ thuật | Nhật ký nền tảng thực thi hoặc ghi chưa truy cập |
| 05–07/11 | Thống kê, kiểm tra dữ liệu, phản biện | Trưởng nhóm tài chính và kỹ sư dữ liệu | Kết quả có nguồn/khoảng tin cậy |
| 08–09/11 | Khóa mã và tái chạy | Phụ trách sản phẩm và cả nhóm | Hướng dẫn chạy lại |
| 10/11 | Bàn giao chung kết | Cả nhóm | Báo cáo và demo nhất quán |

Nếu dữ liệu hoặc QPU đến trễ, tiếp tục bằng dữ liệu tổng hợp/mô phỏng; ghi phần tài chính/QPU là chưa xác minh.

### 16.2. Vai trò

| Vai trò | Trách nhiệm | Bàn giao |
|---|---|---|
| Trưởng nhóm kỹ thuật | Công thức, QUBO, Ising, mạch, bộ giải, môi trường | thành phần, tập kiểm tra, nhật ký cổng/thời gian |
| Trưởng nhóm tài chính | Tập mã, hàm mục tiêu tài chính, đối chuẩn, phí, kiểm định cuốn chiếu | Quy tắc dữ liệu, kiểm định lịch sử, diễn giải |
| Kỹ sư dữ liệu và thực nghiệm | Nhập/kiểm dữ liệu, quản lý phiên bản, thực thi ma trận | Danh mục tệp, kiểm tra, kết quả |
| Phụ trách sản phẩm và trình bày | Tài liệu, sơ đồ, biểu đồ, demo | Hồ sơ gửi thầy và slide |

Nhóm điền tên cá nhân trước khi gửi. Người phụ trách cuối cho mỗi sản phẩm bàn giao vẫn là vai trò được ghi.

### 16.3. Cắt phạm vi khi trễ

- 15/10 chưa qua toán: dừng mô phỏng lớn.
- 17/10 chưa có dữ liệu/quyền: không trình bày hiệu quả tài chính.
- 19/10 mô hình logistic thiếu mẫu: dùng đối chứng cố định, ghi AI chưa kiểm chứng.
- 21/10 chưa có QPU: dùng máy mô phỏng có nhiễu, không ảnh hưởng kết luận chính.
- Thiếu tài nguyên: bỏ p=3, VN100, giảm ngày QAOA; giữ chính xác, p=1, thí nghiệm loại bỏ thành phần và phí.

---

## 17. Sổ đăng ký rủi ro

| Rủi ro | Xác suất/tác động | Dấu hiệu | Giảm thiểu | Người phụ trách |
|---|---|---|---|---|
| Thiếu thành phần lịch sử | Cao/cao | Chỉ tải được rổ hiện tại | Xin xác nhận 13/10; không tuyên bố kiểm định lịch sử sạch | Tài chính |
| Giá điều chỉnh không rõ | Vừa/cao | Nguồn lệch nhau | Đối chiếu hành động doanh nghiệp, chọn nguồn chuẩn | Dữ liệu |
| AI quá khớp | Cao/cao | Huấn luyện/tập kiểm tra lệch lớn | Logistic nhỏ, tập kiểm tra khóa, thí nghiệm loại bỏ thành phần | Tài chính |
| Hiệp phương sai kém điều kiện | Vừa/cao | Gần suy biến | 252 phiên, Ledoit–Wolf, kiểm tra số điều kiện | Kỹ thuật |
| Hạng phạt sai | Vừa/cao | Điều kiện số lượng mã sai hoặc hàm mục tiêu bị chi phối | A/2, A, 2A; báo tính khả thi | Kỹ thuật |
| Mạch dày và sâu | Cao/cao | SWAP/cổng hai qubit tăng | QPU N nhỏ, đo biên dịch mạch trước | Kỹ thuật |
| Nhiễu QPU | Cao/vừa | Tỷ lệ nghiệm khả thi thấp | Khởi tạo từ chuỗi khả thi, số lần đo, máy mô phỏng/chính xác phương án dự phòng | Kỹ thuật |
| GPU không đủ | Vừa/vừa | Thử nghiệm thăm dò chậm | Thử nghiệm thăm dò 12/16/20, cắt cấu hình | Dữ liệu |
| Phí xóa lợi thế lợi nhuận | Vừa/cao | Tỷ lệ thay đổi danh mục lớn, lợi nhuận sau phí âm | Ba mức phí, giới hạn thanh khoản | Tài chính |
| Giao dịch cùng phiên tín hiệu | Thấp/rất cao | Dùng giá đóng cửa để khớp cùng giá đóng cửa | Tín hiệu sau giá đóng cửa, giao dịch ở phiên sau | Tài chính |
| Tập kiểm tra dùng chọn tham số | Vừa/rất cao | Chỉnh sau khi xem tập kiểm tra | Khóa tập kiểm tra và lưu mọi lượt | Cả nhóm |
| Lịch thi đấu đổi | Thấp/vừa | Thông báo mới | Cập nhật có nguồn, cắt phạm vi | Sản phẩm |
| Tuyên bố lượng tử quá mức | Vừa/cao | Chỉ dựa vào “đã chạy QPU” | Tiêu chí cùng ngân sách tính toán, báo kết quả âm | Sản phẩm |
| Khóa bí mật giao diện lập trình ứng dụng bị lộ | Thấp/cao | Token trong nhật ký | Lưu khóa bí mật ngoài mã nguồn, che thông tin nhạy cảm trong nhật ký | Dữ liệu |

---

## 18. Tự phản biện và trả lời bảo vệ

### Tính mới và giá trị

**1. AGQO mới ở điểm nào nếu QAOA danh mục đã có?**  
Phản biện: ghép AI và QAOA không tự tạo tính mới.  
Trả lời: không tuyên bố mới ở thuật toán cơ bản; đóng góp dự kiến là tách AI, ràng buộc, mạch và kiểm định lịch sử trên dữ liệu Việt Nam.  
Bằng chứng: thí nghiệm loại bỏ thành phần, quy tắc dữ liệu, nhật ký.  
Giới hạn: chỉ demo tích hợp thì đóng góp chủ yếu là kỹ thuật.

**2. Đây có thể chỉ là tích hợp nhiều công nghệ?**  
Phản biện: có nếu thiếu giả thuyết bác bỏ.  
Trả lời: H1–H5 và ma trận đối chứng cho phép kết quả âm.  
Bằng chứng: cấu hình khóa trước tập kiểm tra khóa.  
Giới hạn: ít giai đoạn thị trường.

**3. Có được khẳng định ưu thế lượng tử không?**  
Không từ việc chạy QPU. Chỉ kết luận nếu so bộ giải cổ điển phù hợp, cùng nghiệm mục tiêu, tính cả hàng đợi, mạch, lần đo, tối ưu và hậu xử lý.

### Dữ liệu và tài chính

**4. Vì sao bắt đầu bằng VN30?**  
Giảm rủi ro dữ liệu và tiến độ; VN100 mở rộng. Điểm yếu: chính xác bộ giải mạnh ở quy mô này.

**5. Rổ VN30 hiện tại đủ kiểm định lịch sử quá khứ không?**  
Không. Cần lịch sử thành phần có ngày hiệu lực; nếu không có, chỉ báo cáo kỹ thuật/minh họa.

**6. 8 năm dữ liệu có đủ dự báo lợi nhuận?**  
Không thể bảo đảm. Dùng mô hình nhỏ, kiểm định cuốn chiếu và khoảng bất định; không tuyên bố ổn định dài hạn.

**7. Trung bình lịch sử có đáng tin?**  
Nhiễu. So với hàm mục tiêu không dùng lợi nhuận, co rút về 0 và chỉ tối ưu rủi ro; báo từng giai đoạn.

**8. Phí giả định có phải biểu phí chính thức?**  
Không. 10/25/50 bps là kịch bản độ nhạy; thay bằng biểu phí/thuế đã xác minh nếu có.

**9. Giá mở cửa phiên sau có bảo đảm khớp không?**  
Không. Giới hạn theo 1/5/10% ADTV; dữ liệu ngày không tái tạo sổ lệnh.

### AI

**10. Tại sao cần AI thay vì λ cố định?**  
Có thể không cần. So cấu hình AI với cố định; nếu AI không thắng ngoài mẫu thì bỏ khỏi lõi.

**11. Tại sao không dùng LLM?**  
LLM không mặc nhiên phù hợp chuỗi số và khó tái lập; chỉ hỗ trợ tài liệu, không quyết định danh mục.

**12. Nhãn biến động cao có nghĩa là dự báo lợi nhuận tốt?**  
Không. Nhãn chỉ điều chỉnh rủi ro.

**13. Làm sao tránh rò rỉ thông tin do nhãn tương lai?**  
Loại khỏi tập huấn luyện mọi mẫu có cửa sổ nhãn 21 phiên chạm qua ranh giới tập; kiểm tra ngày của từng đặc trưng/nhãn và lưu mốc kết thúc huấn luyện.

### QUBO/QAOA

**14. QUBO có tương đương toàn bộ bài toán tài chính?**  
Không. Nó tương đương với hàm mục tiêu lựa chọn mã đã đặc tả; phí và thực thi được chấm ở kiểm định lịch sử.

**15. Chọn hạng phạt A thế nào?**  
Cận dao động hàm mục tiêu, thử A/2, A, 2A, báo tính khả thi/khoảng cách; không chọn theo tập kiểm tra.

**16. Vì sao so X và XY?**  
Đo đánh đổi giữa tính khả thi, số cổng, độ sâu mạch và nghiệm; XY có thể tốn mạch hơn.

**17. XY bảo đảm đi tới mọi danh mục khả thi?**  
Bảo toàn trọng số Hamming (số bit 1) không bảo đảm mạch nông phân bố tốt. Dùng đồ thị liên thông, nhiều giá trị khởi tạo ngẫu nhiên, tăng p nếu đủ.

**18. Vì sao chỉ p=1,2?**  
Giới hạn tính toán/thời hạn; p=3 chỉ mở rộng. Kết quả âm ở p thấp không bác bỏ mọi biến thể.

**19. Chạy QAOA trên VN30 thật được không?**  
Mạch 30 qubit và hàm mục tiêu dày có thể rất sâu trên QPU. Dùng chính xác/máy mô phỏng VN30, QPU chỉ N nhỏ.

**20. Nghiệm duyệt chính xác làm QAOA thừa không?**  
Với 30,6 có 593.775 nghiệm; chính xác có thể đủ nhanh. Vì vậy QAOA là đối tượng đối chuẩn, không phải bộ giải cần thiết tại quy mô hiện tại.

### Đối chuẩn và tài nguyên

**21. Nghiệm duyệt chính xác có đại diện bộ giải thực tế?**  
Là chuẩn nghiệm tối ưu ở cỡ nhỏ; bổ sung phương pháp gần đúng/MIQP ở cỡ lớn hơn.

**22. Tại sao xin GPU nếu dữ liệu nhỏ?**  
Không xin GPU để xử lý dữ liệu; xin để mô phỏng vector trạng thái và chạy nhiều cấu hình theo lô. Thử nghiệm thăm dò CPU/GPU sẽ cho biết có cần dùng hết hạn mức không.

**23. Tại sao xin QPU nếu có máy mô phỏng?**  
Để đo nhiễu/ánh xạ thật và đào tạo; không là điều kiện hoàn thành.

**24. 0,8 triệu lần đo đủ không?**  
Tính từ 1.200 điểm × 512 lần đo, cộng 25%. Nếu vượt, giảm cấu hình thay vì tự tăng.

**25. 40 GPU-giờ dựa đối chuẩn nào?**  
Chưa đo. Đây là trần dự phòng có độ tin cậy thấp–trung bình; thử nghiệm thăm dò ở 12/16/20 qubit trước.

### Thực tế và tái lập

**26. Lợi ích còn sau phí?**  
Chưa biết; báo trước/sau chi phí, độ nhạy theo phí, tỷ lệ thay đổi danh mục và thanh khoản.

**27. Sharpe tốt có đủ?**  
Không. Báo mọi lượt thử, tập kiểm tra khóa, khoảng tin cậy và từng giai đoạn.

**28. Tái lập được không?**  
Lưu mã băm dữ liệu, giá trị khởi tạo ngẫu nhiên, phiên bản, cấu hình, mạch, bảng đếm thô, siêu dữ liệu và ngày nền tảng thực thi. Nhiễu QPU không thể tái tạo y hệt.

**29. QAOA thua cổ điển thì dự án thất bại?**  
Không; kết luận đúng là chưa có lợi thế ở cấu hình đã thử. Kết quả âm đáng tin vẫn có giá trị.

**30. Không có dữ liệu trước bán kết thì trình bày gì?**  
Trình bày đặc tả, kiểm thử đơn vị, đối chuẩn tổng hợp, mạch máy mô phỏng và trạng thái yêu cầu dữ liệu; không thay bằng số liệu giả. Kết luận tài chính để mở.

---

## 19. Đóng góp, giới hạn và điều kiện mở rộng

### 19.1. Đóng góp có thể bàn giao

- Quy trình nghiên cứu có nhật ký và cấu hình tái lập.
- Công thức QUBO/Ising cho lựa chọn K mã tỷ trọng bằng nhau, có kiểm thử.
- Đối chuẩn X/XY với đối chứng chính xác, đo chất lượng, tính khả thi, cổng và thời gian.
- Thí nghiệm loại bỏ từng thành phần để đo riêng bộ điều chỉnh AI.
- Kiểm định lịch sử có phí, tỷ lệ thay đổi danh mục, thanh khoản và giới hạn dữ liệu.
- Yêu cầu tài nguyên tính từ vector trạng thái, lần đo, lưu trữ.

### 19.2. Giới hạn cần công bố

- Thành phần chỉ số lịch sử và quyền sử dụng chưa được xác minh tại ngày lập.
- Dữ liệu ngày không mô hình hóa đủ sổ lệnh, chênh lệch giá mua/bán và tác động thị trường.
- Lợi nhuận trung bình lịch sử có độ nhiễu lớn.
- Logistic và một nhãn trạng thái thị trường không đại diện toàn bộ tài chính định lượng.
- Máy mô phỏng không thay QPU; QPU nhỏ không chứng minh khả năng mở rộng quy mô.
- VN30 K=6 có thể giải chính xác cổ điển; không có lý do thực dụng thay chính xác ở cỡ này.
- Thời hạn ngắn giới hạn số chế độ, cấu hình và thống kê.

### 19.3. Chỉ xin mở rộng sau 10/11 nếu

1. GPU rút ngắn đáng kể tổng thời gian chạy trên bài toán mẫu khóa.
2. QPU có kết quả hữu ích theo tiêu chí đã định, không chỉ chạy mạch.
3. AI cải thiện ngoài mẫu, bền qua giai đoạn/phí.
4. Có dữ liệu thành phần lịch sử có quyền để lên VN100.
5. Có bài toán mẫu lớn mà bộ giải cổ điển hiện tại không giải trong ngân sách đã đặt.

Nếu không điều kiện nào đạt, không đề nghị thêm tài nguyên.

---

## 20. Phụ lục A — Ký hiệu

| Ký hiệu | Định nghĩa |
|---|---|
| N | Số mã trong tập mã |
| K | Số mã bắt buộc chọn |
| \(x_i\) | Biến nhị phân chọn mã i |
| \(\mu_i\) | Lợi nhuận kỳ vọng năm |
| \(\bar r_i\) | Lợi nhuận ngày trung bình của mã i |
| \(\Sigma\) | Hiệp phương sai năm |
| \(\lambda\) | Hệ số ngại rủi ro |
| \(\alpha\) | Hệ số co về đường chéo |
| A | Hạng phạt số lượng mã của bộ trộn X |
| \(p_t\) | Xác suất trạng thái thị trường biến động cao |
| \(\gamma,\beta\) | Góc của hàm mục tiêu và bộ trộn |
| \(C(N,K)\) | Số tổ hợp K phần tử từ N |
| \(M(N)\) | Bộ nhớ vector trạng thái thuần |

---

## 21. Phụ lục B — Cấu hình JSON mẫu

Tệp cấu hình phải đi cùng mã nguồn. Trường nguồn/mã băm/mã phiên bản/mã lần chạy bắt buộc được điền trong lần chạy có kết quả công bố.

~~~json
{
  "project": "AGQO-2026",
  "data": {
    "market": "HOSE",
    "frequency": "daily",
    "start_date": "2017-01-01",
    "end_date": "latest_complete_session",
    "universe": "historical_VN30_if_licensed",
    "source_id": "fill_after_confirmation",
    "data_hash": "sha256_required"
  },
  "portfolio": {
    "rebalance": "monthly",
    "decision_time": "last_session_close",
    "execution_time": "next_session_open",
    "n_assets": 30,
    "k_assets": 6,
    "weighting": "equal",
    "estimation_window_sessions": 252,
    "minimum_valid_sessions": 126
  },
  "objective": {
    "risk_aversion_fixed": 5.0,
    "risk_aversion_ai_range": [2.0, 10.0],
    "covariance_method": "ledoit_wolf",
    "ai_covariance_method": "sample_to_diagonal",
    "ai_fixed_shrinkage_baseline": 0.40,
    "ai_shrinkage_range": [0.10, 0.70],
    "cardinality_penalty_multiplier": 1.01
  },
  "qaoa": {
    "sdk": "Qiskit",
    "p_values": [1, 2],
    "mixers": ["X", "XY"],
    "optimizer": "COBYLA",
    "max_objective_evaluations": 50,
    "seeds": [11, 23, 47],
    "shots_primary": 512,
    "shots_optional_final": 1024,
    "qpu_max_shot_budget": 800000
  },
  "backtest": {
    "initial_capital_vnd": 100000000,
    "capital_sensitivity_vnd": [50000000, 500000000],
    "training": ["2018-01-01", "2021-12-31"],
    "validation": ["2022-01-01", "2023-12-31"],
    "locked_test_start": "2024-01-01",
    "cost_sensitivity_bps": [10, 25, 50],
    "participation_caps": [0.01, 0.05, 0.10],
    "liquidity_window_sessions": 20
  },
  "reproducibility": {
    "code_commit": "required",
    "environment_lock_hash": "required",
    "run_id": "required",
    "created_at_utc": "required",
    "operator": "required"
  }
}
~~~

---

## 22. Phụ lục C — Nhật ký thí nghiệm

| Trường | Ý nghĩa |
|---|---|
| run_id, timestamp_utc | Mã và thời điểm chạy |
| data_hash, code_commit, environment | Dữ liệu, mã và môi trường |
| instance_id, n, k | Ngày rebalance và kích thước |
| objective_hash | Mã băm hệ số hàm mục tiêu |
| ai_mode | off, lambda_only, shrinkage_only, both |
| mixer, p, seed | Thiết kế mạch và giá trị khởi tạo ngẫu nhiên |
| optimizer, evaluations, shots | Cấu hình tối ưu/đo |
| feasible_rate | Tỷ lệ chuỗi bit thỏa điều kiện chọn đúng K mã |
| best_objective, exact_objective, khoảng cách | Chất lượng nghiệm |
| circuit_depth, two_qubit_gates | Độ sâu và cổng |
| wall_time_seconds | Thời gian tường |
| peak_ram_mb, peak_vram_mb | Bộ nhớ đỉnh |
| nền tảng thực thi, raw_counts_path | Máy mô phỏng/QPU và bảng đếm thô |
| notes | Lỗi/sai lệch/ghi chú |

Không sửa nhật ký cũ; ghi chú bổ sung dùng cùng run_id và thời điểm ghi mới.

---

## 23. Phụ lục D — Tiêu chí nghiệm thu

### Trước dữ liệu thị trường

- [ ] Nguồn và quyền sử dụng được lưu.
- [ ] Mã băm dữ liệu và kiểm tra chất lượng có.
- [ ] Ánh xạ qubit–mã đã kiểm thử.
- [ ] Gốc/QUBO/Ising khớp < \(10^{-9}\) với N ≤ 10.
- [ ] Nghiệm chính xác và kết quả duyệt toàn bộ tổ hợp trùng nhau.
- [ ] X hạng phạt đã kiểm tra; XY giữ nguyên số lượng mã.
- [ ] Không có đặc trưng đọc tương lai.
- [ ] Giá trị khởi tạo ngẫu nhiên, phiên bản, cấu hình và nhật ký có đủ.

### Trước kết quả đầu tư

- [ ] Thành phần lịch sử xác minh hoặc giới hạn sai lệch được nêu cạnh kết quả.
- [ ] Giá điều chỉnh/hành động doanh nghiệp đối chiếu.
- [ ] Giá khớp sau tín hiệu.
- [ ] Phí, tỷ lệ thay đổi danh mục, thanh khoản có báo cáo.
- [ ] Có VN30 và tỷ trọng bằng nhau đối chuẩn.
- [ ] Tập kiểm tra không dùng chọn tham số.
- [ ] Có từng giai đoạn và khoảng bất định.
- [ ] Kết quả âm được giữ nguyên.

### Trước QPU

- [ ] Mạch lý tưởng đã qua kiểm thử.
- [ ] Số cổng, độ sâu mạch, cổng SWAP và ánh xạ đã được lưu.
- [ ] Ngân sách lần đo đã tính.
- [ ] Có ba giá trị khởi tạo ngẫu nhiên hoặc giải thích việc giảm.
- [ ] Có nghiệm chính xác hoặc kết quả mô phỏng cho cùng bài toán mẫu.
- [ ] Tải được bảng đếm thô và siêu dữ liệu.

---

## 24. Tài liệu tham khảo

Tài liệu nhà cung cấp mô tả tính năng; không phải bằng chứng độc lập về ưu thế thuật toán.

### Học thuật

1. Markowitz, H. (1952). “Portfolio Selection.” *The Journal of Finance*, 7(1), 77–91. Nền tảng mô hình trung bình–phương sai. [DOI 10.1111/j.1540-6261.1952.tb01525.x](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x)

2. Ledoit, O. và Wolf, M. (2004). “Honey, I Shrunk the Sample Covariance Matrix.” *The Journal of Portfolio Management*, 30(4), 110–119. Cơ sở đối chứng co rút. [DOI 10.3905/jpm.2004.110](https://doi.org/10.3905/jpm.2004.110)

3. Farhi, E., Goldstone, J. và Gutmann, S. (2014). “A Quantum Approximate Optimization Algorithm.” Đề xuất QAOA. [arXiv:1411.4028](https://arxiv.org/abs/1411.4028)

4. Brandhofer, S., Braun, D., Dehn, V., Hellstern, G., Hüls, M., Ji, Y., Polian, I., Bhatia, A. S. và Wellens, T. (2022; tập 22, bài 25, xuất bản số 2023). “Benchmarking the performance of portfolio optimization with QAOA.” *Quantum Information Processing*. Phân tích hệ số phạt, XY-mixer, nhiễu lấy mẫu, lỗi cổng và tối ưu tham số. [DOI 10.1007/s11128-022-03766-5](https://doi.org/10.1007/s11128-022-03766-5)

5. Bailey, D. H., Borwein, J. M., López de Prado, M. và Zhu, Q. J. (2017). “The Probability of Backtest Overfitting.” *Journal of Computational Finance*. Cơ sở thận trọng với nhiều lần thử kiểm định lịch sử. [DOI 10.21314/JCF.2016.322](https://doi.org/10.21314/JCF.2016.322)

### Tài liệu kỹ thuật chính thức

6. IBM Quantum Documentation. “Quantum approximate multi-objective optimization.” Ví dụ danh mục có ràng buộc chọn đúng số mã và bộ trộn XY; không chứng minh XY luôn tốt hơn. [IBM Quantum](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-multi-objective-optimization)

7. Qiskit Aer. “AerSimulator” và “Running with multiple-GPUs and/or multiple nodes.” GPU mô phỏng và điều kiện bộ nhớ/cài đặt. [AerSimulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html), [GPU nhiều thiết bị](https://qiskit.github.io/qiskit-aer/howtos/running_gpu.html)

### Dữ liệu và thị trường

8. HOSE. “HOSE-INDEX Ground Rules — Version 4.0”, Quyết định 747/QĐ-SGDHCM ngày 30/12/2024; quy tắc quản lý chỉ số, có thể được cập nhật. [Bản quy tắc chính thức](https://staticfile.hsx.vn/Uploads/LocalFiles/ef15ff11e799483abd11677ad0443887/20250114_20241230_QD%20747%20HOSE%20Index%20Ground%20Rules.pdf)

9. HOSE. “Cải tiến chỉ số VN30”, thông tin hiệu lực quy tắc 4.0 từ 03/2025. [Thông cáo HOSE](https://staticfile.hsx.vn/Uploads/UploadDocuments/2391309/TCBC_%20Cai%20tien%20chi%20so%20VN30%20t7.2025.pdf)

10. HOSE. “Factsheet Bộ chỉ số HOSE-Index”, 02/2026. Chỉ xác nhận định nghĩa/thành phần tại thời điểm factsheet, không thay dữ liệu thành phần lịch sử. [Factsheet](https://staticfile.hsx.vn/Uploads/UploadDocuments/2438018/Form_Factsheet_MCIndices_VN_T02.2026.pdf)

11. SSI FastConnect Data. “Danh sách API” và “API Specs”. Tài liệu liệt kê API giá ngày, OHLC, danh sách mã và thành phần chỉ số; chưa xác nhận quyền/lịch sử của nhóm. [Danh sách API tiếng Việt](https://guide.ssi.com.vn/ssi-products/tieng-viet/fastconnect-data/danh-sach-cac-api), [đặc tả API](https://guide.ssi.com.vn/ssi-products/fastconnect-data/api-specs)

12. SSI Securities Corporation. Thông tin doanh nghiệp và tên pháp lý tiếng Anh hiện hành. [Công bố thông tin năm 2025](https://www.ssi.com.vn/en/investor-relation/information-disclosure/detail/disclosure-of-the-2025-annual-report-and-2025-sustainable-development-report)

---

## 25. Kết luận và đề nghị

Nhóm kính đề nghị giảng viên xem xét:

1. Cấp quyền dữ liệu giá và thành phần lịch sử hoặc giới thiệu nguồn có giấy phép phù hợp.
2. Cấp môi trường 16 lõi ảo, 64 GB RAM, 100 GB SSD từ 12/10 đến 10/11/2026.
3. Cấp tối đa 40 GPU-giờ trên GPU 24 GB VRAM; nhóm sẽ báo cáo thử nghiệm thăm dò để điều chỉnh mức dùng.
4. Nếu có chương trình phù hợp, cấp thử QPU N=8–12 với hạn mức kế hoạch khoảng 0,8 triệu lần đo; QPU không phải điều kiện hoàn thành.
5. Không phân bổ API cho LLM cho quy trình chính vì LLM không quyết định danh mục.

Nhóm cam kết dùng tài nguyên theo ma trận đã ghi, lưu nhật ký, giữ đối chứng cổ điển và công bố kết quả âm. Nếu thử nghiệm thăm dò cho thấy GPU không tăng tốc hoặc QPU không khả dụng, nhóm sẽ giảm phạm vi và hoàn thành bằng CPU cùng máy mô phỏng.

**Đại diện nhóm:** ____________________  
**Trưởng nhóm kỹ thuật:** ____________________  
**Trưởng nhóm tài chính:** ____________________  
**Ngày xác nhận:** ____________________
