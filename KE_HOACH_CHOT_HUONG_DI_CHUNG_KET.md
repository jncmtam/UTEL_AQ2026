# Kế hoạch chốt hướng đi AGQO đến chung kết

**Mục đích:** thống nhất một câu chuyện có thể bảo vệ trước hội đồng lượng tử lẫn tài chính; khóa các bằng chứng cần có; phân biệt điều đã đo, điều còn phải kiểm chứng và điều chưa được tuyên bố.

**Ngày lập:** 20/10/2026  
**Mốc thi dự kiến theo đề cương hiện có:** bán kết 25/10/2026, chung kết 10/11/2026. Cập nhật nếu ban tổ chức đã công bố lịch mới.

---

## 1. Quyết định đề xuất

### Hướng nên thống nhất

Định vị AGQO là **hệ thống chọn danh mục cổ phiếu có điều chỉnh theo trạng thái rủi ro, có tính đến khả năng giao dịch, được kiểm chứng bằng kiểm định lịch sử ngoài mẫu; QAOA là một bộ giải được đo lường nghiêm ngặt trong cùng bài toán với các bộ giải cổ điển**.

Luận điểm đầu tư không phải “AI và máy tính lượng tử sẽ kiếm tiền”. Luận điểm phải là:

> Khi thị trường có xác suất biến động cao, mô hình điều chỉnh ngân sách rủi ro; bộ chọn danh mục xét rủi ro, lợi nhuận ước lượng, chi phí chuyển danh mục và thanh khoản. Nhóm đo xem quyết định này có cải thiện kết quả ròng ngoài mẫu so với các phương án đơn giản hay không. Trên chính bài toán đó, nhóm đo chất lượng nghiệm, tính khả thi, chi phí tính toán và độ sâu mạch của QAOA so với chuẩn cổ điển.

Cách này tạo được hai loại bằng chứng liên kết với nhau mà không đánh tráo nguyên nhân:

1. **Bằng chứng kinh tế:** danh mục có tạo giá trị ròng sau phí, thanh khoản và rủi ro hay không.
2. **Bằng chứng kỹ thuật:** QAOA giải cùng hàm mục tiêu đến mức nào, với ngân sách lần đo, số lần đánh giá, thời gian, số cổng hai qubit và độ sâu ra sao.

Không tuyên bố QAOA tạo lợi nhuận nếu lợi nhuận đến từ quy tắc AI hoặc cách chọn danh mục. Không tuyên bố ưu thế lượng tử chỉ vì mạch đã chạy trên thiết bị thật. Nếu chiến lược tài chính chưa thắng, kết luận phải nói rõ “chưa có bằng chứng tạo lợi ích ròng”. Nếu QAOA chưa thắng bộ giải cổ điển, kết luận phải nói rõ “chưa có bằng chứng về lợi thế lượng tử ở cấu hình đã thử”.

### Quyết định tóm tắt

- **Giữ làm nền:** bài toán chọn đúng K mã, tỷ trọng bằng nhau, AI chỉ điều chỉnh quản trị rủi ro, so sánh trên cùng hàm mục tiêu, có nghiệm chính xác làm chuẩn.
- **Nâng thành câu chuyện chính:** kiểm tra lợi ích ròng ngoài mẫu và mức độ triển khai được sau phí, doanh số giao dịch và giới hạn thanh khoản.
- **Sửa trong phiên bản kế tiếp, không ghi đè kết quả cũ:** thêm chi phí chuyển danh mục vào hàm mục tiêu; giảm số nút điều chỉnh AI và hiệu chỉnh chúng trên tập huấn luyện/xác nhận.
- **Giữ QAOA như nhánh nghiên cứu có cổng đạt:** kiểm tra lại trạng thái đầu, bộ trộn XY, chuẩn hóa hàm mục tiêu, khởi tạo góc, độ sâu và chi phí mạch trên dữ liệu mới chưa dùng để chọn cấu hình.
- **Không làm:** đổi ngưỡng H2 sau khi đã thấy kết quả; dùng tập kiểm tra để chọn cấu hình; dùng dữ liệu tổng hợp để kể câu chuyện lợi nhuận; tuyên bố “ưu thế lượng tử” khi bộ giải chính xác cổ điển vẫn giải được bài toán đang xét.

---

## 2. Hiện trạng dự án: điều gì đã có và điều gì chưa có

| Mảng | Trạng thái hiện tại | Ý nghĩa khi bảo vệ |
|---|---|---|
| Bài toán danh mục | Chọn K = 6 trong N mã, tỷ trọng bằng nhau; hàm mục tiêu rủi ro trừ lợi nhuận ước lượng | Rõ ràng, chuyển được sang QUBO và Ising; chưa mô tả đầy đủ chi phí giao dịch trong hàm tối ưu |
| AI | Hồi quy logistic dự báo biến động thị trường cao trong 21 phiên tới; xác suất điều chỉnh hệ số ngại rủi ro và mức co rút hiệp phương sai | AI dự báo trạng thái rủi ro, không dự báo mã thắng hay lợi nhuận riêng từng mã; hiện chưa có bằng chứng nó cải thiện kết quả danh mục |
| QAOA | Độ sâu p = 1; bộ trộn X có hạng phạt và XY dạng vòng Trotter bậc một; 512 lần đo mỗi lần gọi; tối đa 50 lần đánh giá; ba giá trị khởi tạo | Có thiết kế chạy được và sổ đo; mới là cấu hình đầu, chưa chứng minh tính tốt nhất |
| Đối chuẩn lượng tử | 36 bài toán tổng hợp, N = 8, 12, 16, K = 6; so với nghiệm chính xác | Phép đo tái lập được, nhưng không đại diện dữ liệu thị trường và không đạt ngưỡng H2 |
| Kết quả H2 | X đạt 18/36, XY đạt 0/36; ngưỡng đã khóa là 29/36. X đạt 12/12 ở N = 8, 6/12 ở N = 12, 0/12 ở N = 16. XY vẫn cho nghiệm khả thi nhưng khoảng cách mục tiêu kém | Phải báo là H2 chưa đạt. Không xóa kết quả hoặc nới ngưỡng |
| Chuẩn cổ điển | Duyệt chính xác đến N = 30, K ≤ 6; một phép thử N = 30, K = 6 mất 3,987 giây trên máy 8 lõi/16 GB hiện có | Đây là bằng chứng chống lại tuyên bố QAOA cần thiết cho VN30 ở quy mô hiện tại |
| Dữ liệu tài chính | Chưa có dữ liệu VN30/VN100 đã được xác minh quyền sử dụng và lịch thành phần theo ngày hiệu lực | Chưa có kết quả CAGR, Sharpe, mức giảm tối đa, lợi nhuận ròng hoặc sức chứa |
| Kiểm định lịch sử | Chưa có bộ nhập dữ liệu và quy trình khớp lệnh/chi phí hoàn chỉnh trong mã | Chưa thể tuyên bố chiến lược kiếm tiền hoặc thắng đối chuẩn |
| Tài nguyên | Mã chạy trên máy hiện có; chưa có GPU/QPU nào tham gia kết quả H2 | Không nên đặt trọng tâm thuyết trình vào phần cứng chưa tạo ra kết quả |

**Tóm tắt bằng chứng:** nền tảng kỹ thuật và đặc tả đã có; bằng chứng tài chính chưa có; phép thử lượng tử đầu tiên có kết quả âm theo tiêu chí đã đặt. Đây là tình trạng nghiên cứu hợp lệ, nhưng chưa phải câu chuyện đầu tư hoặc ưu thế lượng tử.

---

## 3. So sánh ba hướng đi

| Hướng | Mô tả | Điểm mạnh | Điểm yếu | Đánh giá |
|---|---|---|---|---|
| A. Giữ nguyên bản hiện tại làm hướng chung kết | Trình bày AI + QAOA chọn cổ phiếu; tiếp tục p = 1 và thử thêm dữ liệu tổng hợp | Có mã, có công thức, dễ trình diễn | H2 chưa đạt; chưa có dữ liệu tài chính; N = 30 giải chính xác nhanh; người nghe dễ xem đây là ghép công nghệ | Không chọn làm câu chuyện chính |
| B. Chứng minh chiến lược đầu tư trước, đối chuẩn QAOA song song | Xây phiên bản có xét chi phí và thanh khoản; kiểm định ngoài mẫu; tách đóng góp AI và bộ giải; chỉ tuyên bố lợi thế lượng tử nếu đạt cổng | Đánh đúng câu hỏi “có giá trị kinh tế không”; tạo kết luận cho cả hội đồng tài chính và lượng tử; vẫn giữ được đóng góp kỹ thuật | Đòi hỏi dữ liệu có quyền, quy trình ngoài mẫu và kỷ luật không sửa tập kiểm tra | **Chọn làm hướng chính** |
| C. Đặt cược vào tuyên bố ưu thế QAOA | Tăng độ sâu, thử bộ trộn mới/QPU và tập trung vào số qubit | Hấp dẫn với người quan tâm phần cứng | Hiện không có lợi thế so với nghiệm chính xác; phần cứng nhỏ, hàm mục tiêu dày; dễ bị bác nếu bỏ qua bộ giải cổ điển | Chỉ là nhánh điều kiện, không phải luận điểm đầu tư |

### Vì sao hướng B hợp lý nhất

1. Trả lời câu hỏi quan trọng nhất của giám khảo tài chính bằng lợi nhuận ròng, mức giảm rủi ro, chi phí và thanh khoản.
2. Không để thất bại của một cấu hình QAOA quyết định toàn bộ giá trị của dự án.
3. Giữ được câu hỏi nghiên cứu lượng tử có thể bác bỏ: cấu hình nào tìm nghiệm tốt hơn ở cùng ngân sách, và cái giá là bao nhiêu độ sâu/cổng/lần đo.
4. Cho phép kết luận âm có ích: nếu AI không thêm giá trị, bỏ AI; nếu QAOA thua, báo giới hạn và xác định phần cần cải thiện.
5. Tránh khẳng định một “sản phẩm kiếm tiền” trước khi có dữ liệu sạch và kiểm định ngoài mẫu.

---

## 4. Phiên bản có sức thuyết phục kinh tế hơn

### 4.1. Câu chuyện sản phẩm

Đề xuất đổi cách mô tả từ **“AI chọn cổ phiếu bằng lượng tử”** thành:

> Hệ thống hỗ trợ chọn sáu mã có thanh khoản trong rổ có thành phần lịch sử rõ ràng. Mô hình nhỏ ước lượng xác suất thị trường bước vào giai đoạn biến động cao; bộ chọn điều chỉnh mức chấp nhận rủi ro. Danh mục được đánh giá theo lợi nhuận ròng sau chi phí, doanh số giao dịch, giới hạn thanh khoản và mức giảm vốn. QAOA được kiểm tra như một phương pháp giải cùng bài toán tối ưu, không được mặc định là nguồn tạo lợi nhuận.

Cách mô tả này chính xác hơn hiện trạng. AI không chọn mã trực tiếp và không dự báo lợi nhuận riêng từng mã. Cơ chế kinh tế cần chứng minh là “điều chỉnh rủi ro có ích trong trạng thái biến động”, không phải “AI tìm cổ phiếu tăng giá”.

### 4.2. Giữ phiên bản hiện tại làm đối chứng gốc

Gọi phiên bản hiện tại là **V0** và đóng băng cấu hình trước khi thay đổi:

\[
f(x)=\lambda\frac{x^\top\Sigma x}{K^2}-\frac{\mu^\top x}{K},
\qquad \sum_i x_i=K.
\]

V0 có các điểm mạnh: công thức gọn; cùng một mục tiêu cho mọi bộ giải; AI không làm thay đổi vector lợi nhuận; có thể so nghiệm chính xác. Các điểm yếu cần nói rõ: lợi nhuận trung bình lịch sử rất nhiễu; chi phí giao dịch nằm ngoài mục tiêu tối ưu; cùng một xác suất AI đồng thời thay đổi cả \(\lambda\) và \(\alpha\), nên chưa phân biệt được cơ chế nào tạo ra hiệu quả; phép ánh xạ tuyến tính từ xác suất sang hai hệ số chưa được kiểm chứng kinh tế.

Không xóa V0. Dùng nó để đo xem mỗi sửa đổi có thực sự giúp hơn bản ban đầu hay không.

### 4.3. Phiên bản đề xuất V1: mục tiêu hướng đến danh mục có thể giao dịch

Giữ ràng buộc chọn K mã, nhưng xét chi phí giao dịch dự kiến trực tiếp trong hàm mục tiêu. Tại tháng t, ký hiệu:

- \(x_i\in\{0,1\}\): có chọn mã i hay không.
- \(w^{pre}_{i,t}\): tỷ trọng thực tế của mã i ngay trước tái cân bằng.
- \(\mu_{m,t}\), \(\Sigma_{m,t}\): lợi nhuận và hiệp phương sai ước lượng theo tháng, cùng đơn vị thời gian.
- \(c_{i,t}\): chi phí giao dịch ước lượng trên mỗi đồng giá trị mua/bán của mã i, gồm các khoản có căn cứ hoặc kịch bản độ nhạy.

Mục tiêu thử nghiệm:

\[
J_t(x)=
\lambda_t\frac{x^\top\Sigma_{m,t}x}{K^2}
-\frac{\mu_{m,t}^\top x}{K}
+\sum_i c_{i,t}\left|\frac{x_i}{K}-w^{pre}_{i,t}\right|.
\]

Vì \(w^{pre}_{i,t}\) là số đã biết tại ngày ra quyết định, hạng chi phí là tuyến tính theo \(x_i\) khi đưa vào QUBO. Mọi bộ giải nhận cùng \(J_t\). Tài khoản mô phỏng vẫn chỉ trừ chi phí một lần trong lợi nhuận thực hiện; hạng chi phí ở đây giúp bộ chọn tránh những thay đổi danh mục không đáng giá, không phải khoản trừ thứ hai.

Quy tắc triển khai kèm theo:

- Lọc mã bằng dữ liệu có sẵn trước thời điểm quyết định; lưu quy tắc về lịch sử giá, thanh khoản và tình trạng giao dịch.
- Giới hạn quy mô lệnh theo tỷ lệ ADTV đã đăng ký trước; báo phần lệnh không thể khớp.
- Phát tín hiệu sau phiên cuối tháng, mô phỏng khớp từ phiên kế tiếp.
- Báo lợi nhuận gộp, lợi nhuận ròng, chi phí, doanh số giao dịch, lệnh không khớp và sức chứa giả định riêng.
- Dùng các kịch bản chi phí 10/25/50 điểm cơ bản và tỷ lệ tham gia ADTV 1%/5%/10% như phân tích độ nhạy ban đầu. Thay bằng biểu phí/thuế có nguồn nếu xác minh được; ghi rõ phần nào là giả định.

V1 tạo mối nối có ý nghĩa giữa bài toán kỹ thuật và kinh tế: QUBO không còn tối ưu một mục tiêu trừu tượng rồi mới kiểm tra một chi phí hoàn toàn khác. Tuy nhiên, phải chạy V0 và V1 trên cùng giai đoạn, cùng dữ liệu và cùng mô hình khớp để chứng minh hạng chi phí có ích.

### 4.4. Làm cho phần AI dễ tin hơn

Thay vì điều chỉnh đồng thời \(\lambda\) và \(\alpha\) ngay từ đầu:

1. Giữ bộ dự báo biến động cao 21 phiên, nhưng đo chất lượng xác suất ngoài mẫu bằng log-loss, Brier và biểu đồ hiệu chỉnh xác suất; đối chiếu với xác suất nền và một quy tắc biến động lăn đơn giản.
2. Thử AI chỉ điều chỉnh \(\lambda\), giữ \(\alpha\) cố định hoặc dùng Ledoit–Wolf.
3. Chỉ giữ AI điều chỉnh \(\alpha\) nếu thí nghiệm riêng cho thấy nó thêm giá trị ngoài mẫu.
4. Chọn ánh xạ xác suất sang mức rủi ro trên tập huấn luyện/xác nhận; không giữ mặc định công thức tuyến tính chỉ vì đã viết mã.
5. Chọn ánh xạ theo một quy tắc đã định, chẳng hạn tối ưu lợi nhuận ròng có ràng buộc mức giảm vốn hoặc biến động mục tiêu. Không chọn theo lợi nhuận tập kiểm tra.
6. Nếu xác suất không hiệu chỉnh tốt hoặc AI không hơn đối chứng đơn giản, bỏ AI khỏi thông điệp chính và báo đó là kết quả.

Thiết kế gọn nên là: mô hình dự báo trạng thái → hệ số rủi ro thay đổi theo quy tắc đã hiệu chỉnh → bộ tối ưu có xét chi phí → danh mục thực thi theo giới hạn thanh khoản. Mỗi mũi tên phải có một phép đối chiếu riêng.

---

## 5. Tiêu chí chứng minh giá trị tài chính

### 5.1. Cổng dữ liệu: chưa qua thì chưa có tuyên bố lợi nhuận

Trước khi tính hiệu quả đầu tư, phải xác nhận:

- Giá đã điều chỉnh và cách xử lý cổ tức, chia/tách, quyền mua, đổi mã.
- Thành phần VN30/VN100 theo ngày hiệu lực; rổ hiện tại không thay thế được lịch sử.
- Mã niêm yết mới, bị hủy niêm yết, tạm ngừng và dữ liệu thiếu.
- Quyền sử dụng, lưu trữ và trình chiếu số liệu.
- Thời điểm ra quyết định và thời điểm giá có thể dùng để khớp lệnh.

Nếu thiếu lịch thành phần lịch sử hoặc quyền sử dụng, chỉ được trình bày kiểm thử kỹ thuật/tổng hợp. Không gắn lợi nhuận giả định với thị trường thật.

### 5.2. Đối chuẩn tài chính tối thiểu

Tất cả đối chuẩn dùng cùng thời điểm quyết định, chi phí, quy tắc thực thi và tập mã có thể biết tại thời điểm đó:

1. Chỉ số VN30 có cổ tức nếu dữ liệu tổng lợi nhuận được cấp phép; nếu không, nêu rõ loại chỉ số được dùng.
2. Tỷ trọng bằng nhau trên tập thành viên đủ điều kiện theo ngày.
3. Danh mục sáu mã thanh khoản cao nhất theo quy tắc khóa trước.
4. Danh mục phương sai tối thiểu dùng hiệp phương sai Ledoit–Wolf.
5. V0 với \(\lambda=5,\alpha=0.40\) và bộ giải chính xác.
6. V1 có/không có AI, cùng bộ giải chính xác.
7. Danh mục ngẫu nhiên sáu mã làm mốc tham khảo, không làm đối chuẩn thắng/thua duy nhất.

Không cần thử hàng chục chiến lược để tạo ấn tượng. Mỗi phương án mới làm tăng rủi ro chọn nhầm kết quả tốt do thử quá nhiều cấu hình.

### 5.3. Chỉ số phải công bố

**Lợi nhuận và rủi ro:** lợi nhuận gộp/ròng, tỷ suất tăng trưởng kép hàng năm (CAGR), biến động năm hóa, tỷ số Sharpe với lãi suất phi rủi ro được nêu rõ, mức giảm vốn tối đa (MDD), thời gian hồi phục, Sortino nếu đủ dữ liệu, chênh lệch lợi nhuận so với từng đối chuẩn.

**Khả năng thực thi:** doanh số giao dịch một chiều và hai chiều, chi phí ước tính, tỷ lệ khớp, phần lệnh chưa khớp, mức sử dụng ADTV, kết quả ở các quy mô vốn 50/100/500 triệu đồng.

**Độ ổn định:** kết quả từng năm và từng giai đoạn thị trường; khoảng tin cậy 95% cho chênh lệch lợi nhuận theo tháng bằng lấy mẫu khối; độ nhạy với chi phí và thanh khoản; mọi cấu hình đã thử.

### 5.4. Cổng đạt/trượt đề xuất

Đây là ngưỡng quản trị dự án để thống nhất trước khi mở tập kiểm tra, không phải bảo đảm lợi nhuận:

- **Cổng AI:** xác suất AI phải có log-loss/Brier tốt hơn quy tắc dự báo đơn giản trên dữ liệu ngoài mẫu và có hiệu chỉnh xác suất chấp nhận được. Nếu không đạt, không nói AI tạo giá trị.
- **Cổng chiến lược:** lợi nhuận vượt đối chuẩn phải dương sau chi phí ở kịch bản cơ sở 25 điểm cơ bản; khoảng tin cậy của chênh lệch phải được báo, và mục tiêu mạnh là cận dưới 95% lớn hơn 0. Đồng thời phải có ít nhất một lợi ích quản trị rủi ro rõ ràng, như Sharpe tốt hơn hoặc MDD thấp hơn, mà không làm lợi nhuận ròng sụp đổ.
- **Cổng độ nhạy:** báo riêng ở 10/25/50 điểm cơ bản. Nếu chỉ tốt ở chi phí gần bằng 0, không gọi đây là phương án có khả năng kiếm tiền.
- **Cổng triển khai:** không vi phạm giới hạn thanh khoản đã đặt; nếu phần lớn lệnh không khớp, kết quả lý thuyết không được gọi là danh mục có thể đầu tư.
- **Cổng đủ dữ liệu:** nếu số kỳ kiểm tra không đủ để phân biệt chênh lệch, kết luận là “chưa đủ bằng chứng”, kể cả khi điểm ước lượng nhìn đẹp.

Một giai đoạn kiểm định lịch sử ngắn có thể không đủ lực thống kê. Vì vậy, đây là cổng của tuyên bố, không phải lý do chỉnh tham số đến khi vượt cổng.

### 5.5. Chống chọn kết quả đẹp

- Giữ nguyên các mốc chia thời gian đã ghi trong đề cương: huấn luyện đến 2020, xác nhận 2021–2023, tập kiểm tra khóa từ 2024 đến tháng đầy đủ gần nhất có dữ liệu hợp lệ.
- Chỉ mở tập kiểm tra sau khi chốt dữ liệu, mã, hàm mục tiêu, phí, đối chuẩn và quy tắc chọn tham số.
- Ghi mọi lần thử, kể cả cấu hình không được chọn; không xóa các kết quả âm.
- Dùng lấy mẫu khối để giữ phụ thuộc theo thời gian; có thể báo thêm xác suất quá khớp kiểm định lịch sử hoặc Sharpe đã hiệu chỉnh nếu số thử và độ dài dữ liệu đủ.
- Nếu đã xem tập kiểm tra để điều chỉnh bất kỳ thứ gì, phần đó trở thành dữ liệu phát triển; cần một giai đoạn chưa xem khác để tuyên bố ngoài mẫu.

Các nghiên cứu về xác suất quá khớp kiểm định lịch sử và Sharpe đã hiệu chỉnh nhấn mạnh rằng kết quả tốt nhất trong nhiều lần thử có thể bị thổi phồng do chọn mẫu. Đây là lý do phải giữ sổ lần thử và tập kiểm tra khóa, không chỉ là hình thức báo cáo.

---

## 6. Tiêu chí chứng minh chất lượng kỹ thuật lượng tử

### 6.1. Câu hỏi kỹ thuật mà hội đồng cần nghe

Không chỉ hỏi “mạch có chạy không?”. Hãy trả lời:

1. QAOA tối ưu chính xác hàm nào, với ràng buộc chọn đúng K được mã hóa ra sao?
2. Bộ trộn và trạng thái đầu có giữ mọi mẫu đo trong miền khả thi không?
3. Độ sâu p, số cổng hai qubit và độ sâu sau biên dịch tăng thế nào khi N tăng?
4. Chất lượng nghiệm và xác suất lấy được nghiệm tốt thay đổi thế nào theo p, bộ trộn, số lần đo và giá trị khởi tạo?
5. QAOA so với nghiệm chính xác, tham lam, mô phỏng tôi luyện và bộ giải nguyên hỗn hợp ở cùng ngân sách thế nào?
6. Tính đủ thời gian cổ điển tìm góc, biên dịch, hàng đợi thiết bị, lấy mẫu và hậu xử lý hay chưa?
7. Bài toán nào là khó theo quy tắc xác định trước, không phải được chọn vì QAOA tình cờ cho kết quả kém?

### 6.2. Thiết kế mạch đề xuất

Giữ cấu hình H2 đã công bố làm **thí nghiệm gốc**. Phiên bản cải tiến là thí nghiệm mới, đăng ký trước và dùng tập bài toán mới chưa tham gia chọn thiết kế.

**Bộ trộn XY là nhánh chính để xử lý ràng buộc đúng K.** Cấu hình hiện tại khởi tạo một chuỗi cơ sở khả thi sau khi hoán vị tài sản rồi dùng vòng XY Trotter bậc một. Đây là một lựa chọn cụ thể, không phải đại diện cho mọi bộ trộn XY. Phép thử kế tiếp nên so:

- Trạng thái đầu một danh mục cơ sở khả thi như hiện tại.
- Trạng thái đầu chồng chập đều các danh mục có đúng K bit 1 nếu chuẩn bị được và tính đủ chi phí chuẩn bị.
- Vòng XY với lịch chia lớp cổng hai qubit để đo độ sâu thật.
- Một cấu trúc XY liên thông hơn chỉ khi số cổng/độ sâu sau biên dịch còn trong ngân sách.

Không mặc định trạng thái Dicke, XY đầy đủ hay QAMPA sẽ tốt hơn khi có nhiễu. Đo trên dữ liệu xác nhận rồi khóa một cấu hình để kiểm tra.

**Độ sâu:** giữ p = 1 làm mốc vì đã có kết quả; khảo sát p = 2 và p = 3 trên tập phát triển; chọn một cấu hình theo chất lượng nghiệm trong giới hạn cổng/độ sâu, sau đó đánh giá đúng một lần trên tập khóa. Báo chất lượng theo từng p, không chỉ p tốt nhất.

**Khởi tạo tham số:** đối chiếu giá trị ngẫu nhiên hiện tại với lịch khởi tạo góc có cấu trúc và tiếp nối nghiệm giữa các độ sâu. Ngân sách mỗi cấu hình phải tính đủ số lần đánh giá. Nếu khởi tạo từ một nghiệm cổ điển, so với chi phí và chất lượng của chính nghiệm cổ điển; không ghi toàn bộ kết quả cho QAOA.

**Hàm mục tiêu và hạng phạt:** giữ bộ trộn X làm đối chứng. Thử các mức hạng phạt và chuẩn hóa trên tập phát triển; tránh hạng phạt quá lớn làm lấn át cấu trúc tài chính. Đối với XY, không cộng hạng phạt số lượng mã. Báo năng lượng của hàm gốc, không chỉ năng lượng QUBO có hạng phạt.

Các bài nghiên cứu QAOA cho danh mục đã chỉ ra rằng cách đặt hệ số phạt, tỷ lệ giữa hàm chi phí và bộ trộn, điểm khởi tạo góc và loại bộ trộn đều có thể làm thay đổi kết quả. Nghiên cứu về sự ăn khớp giữa trạng thái đầu và bộ trộn cũng cho thấy cải thiện trong mô phỏng không tự động chuyển thành cải thiện đáng kể trên thiết bị nhiễu. Do đó, các yếu tố này phải là biến thực nghiệm, không phải khẩu hiệu.

### 6.3. Bộ đo kỹ thuật bắt buộc

Mỗi bài toán, bộ trộn, độ sâu và giá trị khởi tạo cần lưu:

- N, K, ma trận đầu vào, mã băm, giá trị khởi tạo và thứ tự mã.
- Hàm mục tiêu gốc, hệ số chuẩn hóa, hạng phạt, đồ thị bộ trộn, trạng thái đầu.
- Độ sâu p, số lần đánh giá hàm mục tiêu, số lần đo mỗi đánh giá, tổng lần đo.
- Tỷ lệ mẫu khả thi, xác suất nghiệm tối ưu/đạt ngưỡng nếu có, nghiệm khả thi tốt nhất đã lấy, giá trị kỳ vọng ước lượng.
- Khoảng cách mục tiêu chuẩn hóa so với nghiệm chính xác.
- Thời gian tối ưu góc, biên dịch, thời gian thiết bị/hàng đợi nếu có, thời gian hậu xử lý.
- Cổng hai qubit, độ sâu hai qubit, số cổng SWAP, ánh xạ qubit và thiết bị sau biên dịch.
- Kết quả lý tưởng, kết quả có sai số lấy mẫu, kết quả có nhiễu mô phỏng và kết quả thiết bị thật thành các cột riêng.

### 6.4. Đối chuẩn công bằng

- Với N ≤ 30, K ≤ 6, giữ duyệt chính xác làm chuẩn tối ưu toàn cục.
- So thêm thuật toán tham lam, mô phỏng tôi luyện và bộ giải nguyên hỗn hợp nếu trường có quyền dùng.
- Mọi phương pháp dùng cùng mục tiêu, dữ liệu, ràng buộc, giá trị khởi tạo tương ứng và ngân sách tính toán.
- Báo đường cong chất lượng theo thời gian hoặc ngân sách đánh giá; không so QAOA 50 lần gọi với thuật toán cổ điển chạy vô hạn.
- Báo cả thời gian tổng, gồm tối ưu góc và điều phối thiết bị, không chỉ thời gian thực hiện một mạch.
- Phân tầng độ khó bằng đặc tính đã định trước hoặc thời gian của bộ giải cổ điển trên tập phát triển. Không chọn mẫu kiểm tra sau khi xem kết quả QAOA.
- Tập 36 bài toán H2 hiện tại đã được xem; không dùng nó làm tập kiểm tra kín cho phiên bản cải tiến. Tạo bộ sinh và giá trị khởi tạo mới, giữ một phần chưa mở đến sau khi khóa cấu hình.

### 6.5. Cổng đạt/trượt kỹ thuật đề xuất

- **Tính đúng:** hàm mục tiêu trực tiếp, QUBO và Ising khớp trong sai số đã khóa; XY bảo toàn K trong mô phỏng lý tưởng; ánh xạ bit–mã được kiểm tra.
- **Chất lượng nghiệm:** đạt tỷ lệ khả thi tối thiểu 95% cho cấu hình XY dự kiến chạy thiết bị; trung vị khoảng cách mục tiêu không quá 5%; báo phân vị 90 thay vì chỉ báo trung vị.
- **Ổn định:** kết quả không phụ thuộc một giá trị khởi tạo duy nhất; báo từng lần chạy và khoảng dao động.
- **Chi phí mạch:** công bố ngân sách cổng hai qubit/độ sâu trước khi chạy; cấu hình vượt ngân sách bị loại theo quy tắc đã khóa.
- **So sánh cổ điển:** nếu mục tiêu là tuyên bố lợi thế, phải thắng ít nhất một đối chứng cổ điển mạnh ở cùng chất lượng và ngân sách tổng. Nếu không thắng, chỉ được nói “đã triển khai và đo được”, không nói “nhanh hơn” hay “tốt hơn”.
- **Mở rộng:** chỉ bàn về khả năng mở rộng khi có đường cong theo N, chất lượng, thời gian và cổng; một phép chạy N nhỏ không chứng minh ưu thế quy mô lớn.

Ngưỡng 29/36 của H2 cũ giữ nguyên và kết luận hiện tại là chưa đạt. Các ngưỡng nêu ở đây áp dụng cho thí nghiệm mới sau khi đã thống nhất và trước khi tạo/mở bộ kiểm tra mới; không dùng để thay đổi kết quả cũ.

---

## 7. Cầu nối giữa kỹ thuật và tài chính

### 7.1. Tách nguyên nhân tạo lợi ích

Chạy các so sánh theo lớp, không trộn tất cả thành một con số:

| Câu hỏi | Cách giữ các yếu tố khác cố định | Kết quả cần công bố |
|---|---|---|
| AI có dự báo được trạng thái biến động không? | AI so với xác suất nền và quy tắc biến động đơn giản | Log-loss, Brier, hiệu chỉnh xác suất |
| AI có cải thiện quyết định rủi ro không? | Cùng bộ giải chính xác, cùng dữ liệu; AI bật/tắt | Lợi nhuận ròng, Sharpe, MDD, doanh số |
| Chi phí chuyển danh mục có giúp không? | V0 so với V1, cùng AI và bộ giải | Lợi nhuận ròng, phí, doanh số, tỷ lệ khớp |
| QAOA giải bài toán tốt đến đâu? | Cùng bài toán và ngân sách với nghiệm chính xác/cổ điển | Khoảng cách, khả thi, thời gian, cổng, độ sâu |
| QAOA có làm thay đổi kết quả đầu tư không? | Dùng danh mục QAOA và nghiệm chính xác cho cùng kỳ, cùng thực thi | Chênh lệch danh mục và lý do: chất lượng nghiệm hay ngẫu nhiên |

Lợi nhuận chiến lược và chất lượng bộ giải là hai đại lượng khác nhau. Nghiệm chính xác cổ điển phải dùng làm chuẩn cho lợi ích tài chính. QAOA chỉ có thể đóng góp kinh tế nếu việc dùng nghiệm gần tối ưu của nó cải thiện quy mô, tốc độ hoặc chi phí trong một bài toán mà đối chứng cổ điển phù hợp không giải tốt hơn.

### 7.2. Khi nào có thể nói “có khả năng tạo tiền”

Chỉ dùng thông điệp đó khi có:

1. Lịch sử thành phần chỉ số và dữ liệu giá hợp lệ, có quyền sử dụng.
2. Kiểm định ngoài mẫu theo thời gian, khớp lệnh sau tín hiệu.
3. Lợi nhuận ròng sau chi phí, không chỉ lợi nhuận gộp.
4. Đối chuẩn tài chính hợp lý và chiến lược đơn giản.
5. Mức giảm vốn, doanh số, thanh khoản và quy mô vốn mô phỏng.
6. Khoảng bất định và đầy đủ số lần thử.
7. Kết quả không biến mất khi tăng chi phí và giảm thanh khoản.

Nếu thiếu một trong các điểm trên, dùng cách nói “giả thuyết đầu tư đang được kiểm chứng” hoặc “kiểm thử kỹ thuật trên dữ liệu tổng hợp”, không dùng “kiếm tiền”, “đánh bại thị trường” hay “sinh lợi ổn định”.

---

## 8. Bản trình bày cho hai nhóm giám khảo

### 8.1. Tuyên bố cho hội đồng tài chính

> Bài toán thực tế của chúng tôi là chọn sáu mã có thanh khoản trong rổ lịch sử đúng tại thời điểm ra quyết định. Mô hình chỉ dự báo nguy cơ biến động cao để điều chỉnh mức chấp nhận rủi ro. Chiến lược được so với chỉ số, danh mục tỷ trọng bằng nhau và phương sai tối thiểu; chúng tôi tính phí, doanh số và lệnh không khớp. Tuyên bố lợi ích chỉ dựa trên kỳ kiểm tra ngoài mẫu và kết quả ròng.

Điền số liệu sau khi đủ dữ liệu:

> Trong giai đoạn [ngày bắt đầu–ngày kết thúc], phiên bản [V0/V1] đạt [CAGR ròng], biến động [x], MDD [y], Sharpe [z], lợi nhuận vượt [đối chuẩn] [a] với khoảng tin cậy [b]. Doanh số giao dịch năm hóa [c], chi phí [d], sức chứa theo giả định vốn [e]. So với bản không AI, phần tăng/giảm là [f]. Ở kịch bản chi phí 50 điểm cơ bản, kết quả [còn/không còn] giữ được.

Không điền chỗ trống bằng số giả. Nếu chưa có số liệu đáng tin, trình bày như mục tiêu cần kiểm chứng và nói rõ chưa có bằng chứng.

### 8.2. Tuyên bố cho hội đồng lượng tử

> Bài toán chọn đúng K mã được mã hóa thành QUBO. Bộ trộn XY giữ nguyên số mã được chọn; bộ trộn X được giữ làm đối chứng có hạng phạt. Trên bộ bài toán khóa mới, chúng tôi đo chất lượng nghiệm so với nghiệm chính xác, khả năng lấy mẫu nghiệm khả thi, độ sâu và số cổng hai qubit sau biên dịch, số lần đo và tổng thời gian tối ưu. Vì nghiệm chính xác giải được VN30 nhanh, chúng tôi không tuyên bố QAOA cần thiết ở quy mô đó.

Điền số liệu sau khi chạy thí nghiệm mới:

> Với N = [n], K = [k], bộ trộn [cấu hình], trạng thái đầu [cấu hình], p = [p], [số] lần đo và [số] lần gọi, tỷ lệ nghiệm khả thi là [a], khoảng cách trung vị/phân vị 90 là [b/c], số cổng hai qubit là [d], độ sâu là [e]. So với [đối chứng cổ điển], QAOA [thắng/hòa/thua] theo [chỉ số] và tiêu tốn [ngân sách]. Đây là [bằng chứng có/không có] về lợi ích tại cấu hình đã thử.

### 8.3. Câu trả lời ngắn khi bị hỏi “điểm ăn tiền là gì?”

> Điểm ăn tiền không phải nhãn AI hay việc chạy được QPU. Đó là một quyết định danh mục có thể kiểm tra được: dự báo trạng thái rủi ro, chọn mã theo một mục tiêu có xét chi phí, rồi chứng minh ngoài mẫu lợi ích ròng hoặc công bố minh bạch rằng chưa có. Phần lượng tử tạo giá trị khi cho thấy chính xác nó cải thiện chất lượng/ngân sách giải ở đâu so với chuẩn cổ điển; hiện kết quả H2 chưa chứng minh điều đó.

---

## 9. Cổng quyết định từ nay đến chung kết

| Thời điểm dự kiến | Việc phải chốt | Điều kiện dừng/đổi hướng |
|---|---|---|
| 20–21/10 | Xác minh quyền dữ liệu, lịch thành phần lịch sử, giá điều chỉnh, phí và thời gian bàn giao | Nếu không có dữ liệu hợp lệ, khóa nhánh tài chính là “chưa đủ bằng chứng”; không dựng lợi nhuận từ dữ liệu tổng hợp |
| 21–22/10 | Chốt V0, định nghĩa V1, chia thời gian, đối chuẩn, phí, chỉ số và sổ lần thử | Không mở tập kiểm tra nếu quy tắc còn thay đổi |
| 22–24/10 | Chuẩn bị câu chuyện bán kết: phát hiện H2 âm, bằng chứng mã, thiết kế V1, cổng tài chính/lượng tử | Không trình bày tuyên bố lợi nhuận hoặc ưu thế lượng tử |
| 25/10 | Bán kết theo lịch hiện có | Thu nhận câu hỏi hội đồng như yêu cầu kiểm tra, không dùng để sửa tập kiểm tra đã xem |
| 26–31/10 | Nếu dữ liệu hợp lệ: hoàn thiện chuỗi kiểm định lịch sử và chạy đối chuẩn tài chính; nếu không, hoàn thiện bộ kiểm thử kỹ thuật và giới hạn | Nếu AI không hơn đối chứng, chuyển phần AI khỏi luận điểm chính |
| 26/10–03/11 | Tạo bộ QAOA mới; thử trạng thái đầu, chuẩn hóa, bộ trộn và p trên tập phát triển; đếm mạch sau biên dịch | Nếu cổng/độ sâu vượt ngân sách, giữ mô phỏng và bỏ tuyên bố về phần cứng |
| 04–06/11 | Khóa phiên bản, mở bộ kiểm tra mới đúng một lần, lập bảng tài chính và bảng lượng tử | Không sửa tham số sau khi mở; mọi sửa đổi cần bộ kiểm tra mới |
| 07–09/11 | Viết kết luận, biểu đồ, giới hạn, kịch bản hỏi đáp, chạy lại tái lập từ nhật ký | Không bổ sung cấu hình chỉ để làm đẹp kết quả |
| 10/11 | Chung kết theo lịch hiện có | Nêu rõ mức bằng chứng và giới hạn |

Nếu lịch thi thay đổi, giữ nguyên thứ tự cổng và thay ngày; không rút bỏ cổng dữ liệu hoặc tập kiểm tra khóa.

---

## 10. Bảng quyết định cuối trước khi nộp

| Bằng chứng tại ngày khóa | Cách định vị AGQO |
|---|---|
| AI dự báo tốt, danh mục ròng tốt hơn đối chuẩn, độ nhạy phí chấp nhận được; QAOA chưa thắng cổ điển | **Câu chuyện chính là quản trị rủi ro danh mục; QAOA là nghiên cứu đối chuẩn trung thực, chưa có lợi thế ở cấu hình thử** |
| AI không dự báo/cải thiện; phương án tài chính đơn giản tốt hơn; QAOA có kết quả kỹ thuật tái lập | **Câu chuyện chính là bộ kiểm chứng tối ưu danh mục; bỏ tuyên bố AI tạo giá trị** |
| Chiến lược tốt nhưng thiếu dữ liệu hợp lệ/kiểm định ngoài mẫu | **Chỉ là kết quả thăm dò; không tuyên bố tạo tiền** |
| QAOA thắng một bộ giải yếu nhưng chưa so nghiệm chính xác hoặc bộ giải nguyên hỗn hợp | **Chưa có bằng chứng lợi thế; cần so sánh mạnh hơn** |
| QAOA có chất lượng/ngân sách tốt hơn đối chứng mạnh trên tập chưa mở và phần cứng có độ sâu khả thi | **Có thể tuyên bố lợi ích kỹ thuật giới hạn đúng bài toán, cỡ mẫu, nền tảng và ngân sách đã thử** |
| QAOA hoặc AI có kết quả âm nhưng quy trình sạch, đối chuẩn đúng, dữ liệu tái lập | **Báo kết quả âm có giá trị; mô tả giới hạn, không biến thành tuyên bố thắng** |

### Kết luận thống nhất đề xuất

**Chọn hướng B:** chứng minh giá trị tài chính của quyết định danh mục có xét rủi ro, chi phí và thanh khoản; dùng thí nghiệm loại bỏ thành phần để đo riêng đóng góp AI; dùng QAOA như một bộ giải cần vượt qua chuẩn chất lượng/chi phí rõ ràng. Giữ kết quả H2 hiện tại là chưa đạt. Không tuyên bố có lợi nhuận hoặc ưu thế lượng tử cho đến khi các cổng tương ứng được vượt qua.

---

## 11. Nguồn tham khảo phục vụ thiết kế

- [Đề cương nghiên cứu và triển khai AGQO hiện tại](AGQO_Final_Research_Proposal.md).
- [Báo cáo thử nghiệm H2 ngày 13/10/2026](results/BAO_CAO_THU_NGHIEM_H2_2026-10-13.md).
- [Mã mô hình, bộ ước lượng và bộ mô phỏng hiện tại](agqo/problem.py).
- [Nghiên cứu đối chuẩn QAOA cho lựa chọn danh mục, gồm hạng phạt, bộ trộn và tối ưu tham số](https://doi.org/10.1007/s11128-022-03766-5).
- [Nghiên cứu về sự ăn khớp giữa trạng thái đầu và bộ trộn XY, cùng phép thử trên thiết bị 32 qubit](https://www.nature.com/articles/s41534-023-00787-5).
- [Nghiên cứu về xác suất quá khớp khi dùng kiểm định lịch sử](https://doi.org/10.21314/JCF.2016.322).
- [Nghiên cứu về Sharpe đã hiệu chỉnh để giảm sai lệch do chọn trong nhiều lần thử và phân phối không chuẩn](https://doi.org/10.3905/jpm.2014.40.5.094).

Các bài nghiên cứu giúp đặt thiết kế phép thử; chúng không chứng minh trước rằng AGQO sẽ có kết quả tương tự.

