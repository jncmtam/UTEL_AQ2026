# Đăng ký nghiên cứu và sổ rủi ro AGQO

**Phiên bản:** 1.0 · **Ngày khóa đăng ký:** 21/10/2026 · **Trạng thái:** đăng ký cho giai đoạn kiểm định tiếp theo; các kết quả 2025–2026 đã được xem và chỉ còn mang tính chẩn đoán.

## Câu hỏi có thể bác bỏ

Trong một giai đoạn kiểm định theo thời gian chưa được mở, liệu bộ điều khiển AI dùng dữ liệu thị trường và kết quả bộ giải đã trưởng thành đến ngày quyết định có thể chọn cấu hình QAOA giúp tăng giá trị danh mục ròng sau chi phí so với chính sách cố định tốt nhất và bộ chọn quy tắc, đồng thời bộ giải đạt chất lượng và ngân sách tài nguyên đã định trước?

Ba mệnh đề phải có bằng chứng riêng. Kết quả này không gộp “LLM trả lời được”, “QAOA tạo mạch hợp lệ” và “chiến lược sinh lợi” thành một tuyên bố.

## Giả thuyết, phép đo và cổng đạt

| Mệnh đề | Giả thuyết kiểm định | Chỉ số chính | Cổng đạt đã khóa |
|---|---|---|---|
| Giá trị tài chính | AGQO cải thiện kết quả danh mục sau phí ngoài mẫu | Lợi nhuận chủ động năm hóa theo cặp so với VN30; Sharpe, sụt giảm tối đa và CVaR là chỉ số bảo vệ | Cận dưới khoảng tin cậy khối 95% của lợi nhuận chủ động lớn hơn 0; mức tăng năm hóa điểm ước lượng ít nhất 2 điểm phần trăm; sụt giảm tối đa không xấu hơn VN30 quá 2 điểm phần trăm; kết quả giữ được sau phí, sức chứa và kiểm tra độ nhạy |
| Giá trị AI | Qwen có ích hơn bộ chọn quy tắc và chính sách cố định tốt nhất được chọn trên dữ liệu huấn luyện/kiểm định | Chênh lệch lợi nhuận ròng và tiện ích rủi ro trên cùng ngày, cùng danh mục ứng viên, cùng ngân sách solver | Cải thiện có ý nghĩa kinh tế so với cả hai đối chứng; kiểm định khóa và chỉ số đã đăng ký trước; có kiểm tra RAG, không RAG, quy tắc và cố định |
| Giá trị tin tức | Siêu dữ liệu nguồn tin có thể cung cấp bối cảnh tốt hơn các đặc trưng giá, thanh khoản và độ rộng đơn thuần | Chênh lệch giữa biến thể không tin và biến thể có tin trên cùng cửa sổ, danh mục và chính sách | Chỉ bật ngữ cảnh GDELT khi manifest xác nhận đủ bí danh, quyền nguồn, phiên bản, dấu lần đầu ghi nhận và giờ thu thập; không diễn giải số lần nhắc tên thành cảm xúc hoặc nguyên nhân. Muốn tuyên bố sự kiện đã xuất bản trước tín hiệu phải có giờ xuất bản của nhà phát hành; muốn tuyên bố giá trị phải cải thiện ngoài mẫu theo cùng cổng kinh tế |
| Giá trị bộ giải lượng tử | QAOA có điểm chất lượng/tài nguyên đáng dùng so với bộ giải cổ điển mạnh | Regret chuẩn hóa, xác suất nghiệm khả thi, thời gian đến ngưỡng, số lần đánh giá, số cổng logic và sau transpile khi có phần cứng | Trên ít nhất một quy mô thực tiễn đã xác định trước: regret trung bình không quá 5%, xác suất nghiệm khả thi tối thiểu 90%, ngân sách được cân bằng và có lợi thế chất lượng–tài nguyên so với bộ giải cổ điển mạnh. Mô phỏng CPU không thể tự nó qua cổng ưu thế lượng tử |
| Độ tin cậy chế độ | Tiểu mô hình chế độ biến động tốt hơn dự báo tần suất nền | Brier skill theo dự báo đã trưởng thành và hiệu chỉnh xác suất | Brier skill dương trên chuỗi đủ dài, theo thời gian; nếu không thì xác suất chỉ là thông tin phụ và không được dùng để tăng rủi ro |

**Định nghĩa kết quả chính.** Lợi nhuận tháng sau chi phí gồm phí mua/bán, thuế, trượt giá và phần lệnh không khớp khi dữ liệu cho phép. Hiện hệ thống mới mô hình hóa 25 điểm cơ bản mỗi chiều và giới hạn tham gia giá trị giao dịch bình quân ngày; chưa có dữ liệu báo giá, thuế đầy đủ, bước giá hoặc khớp lệnh thực tế. Vì vậy chưa đủ điều kiện mở cổng tài chính đã nêu.

**Khoảng tin cậy.** So sánh ghép cặp theo lợi nhuận tháng; bootstrap theo khối ba tháng là phân tích chính, khối sáu tháng là độ nhạy. Báo cả số tháng, chênh lệch chủ động, cận dưới/cận trên và hiệu ứng. Không coi 16 tháng là mẫu lớn.

**Giai đoạn kiểm định.** Cửa sổ 2025-05 đến 2026-08 đã được xem trong các vòng trước. Nó được đánh dấu `diagnostic_opened`, không phải tập kiểm định khóa. Phần dữ liệu 2026-09 đến 2026-10 chỉ có quá ít tháng để thay thế tập kiểm định. Giai đoạn khóa tiếp theo chỉ được mở sau khi có đủ dữ liệu mới, nguồn có quyền sử dụng phù hợp, giá điều chỉnh hoặc total-return được kiểm tra, và thành phần chỉ số theo thời điểm.

## Bản đồ thí nghiệm hiện tại

| Lớp | Đã có | Kết quả hiện tại | Khoảng trống để kết luận |
|---|---|---|---|
| Giá thị trường của lượt chạy đã công bố | 37.308 dòng OHLCV, 30 mã và hai chỉ số, 04/01/2022–19/10/2026 | Không trùng khóa ngày–mã, không ô trống, OHLC nhất quán trong tệp | Kết quả cũ dùng snapshot hiện tại và giá thô; không đại diện cho mã nguồn hiệu chỉnh mới, phải tính lại |
| Mã nguồn hiệu chỉnh dữ liệu | Lịch thành phần có khoảng hiệu lực; OHLC VCI điều chỉnh và OHLC DNSE thô; bộ lọc tin theo thời điểm | Bộ nạp từ chối snapshot tĩnh, thiếu giá điều chỉnh hoặc thiếu lịch sử mã; tin hồi cứu sau ngày quyết định bị loại | Chưa tải lại toàn kỳ do quyền Khách Vnstock giới hạn 365 ngày; lịch thành phần là bản tổng hợp cần kiểm tra mọi kỳ rà soát; chưa có bản ghi tin |
| AI chế độ | LogisticRegression + StandardScaler; đặc trưng VN30 20/60/120 phiên | Brier 0,237 so với nền 0,217; kỹ năng Brier âm khoảng 9,3% | Không có bằng chứng mô hình chế độ thêm giá trị; nhãn 21 phiên chồng lấn |
| LLM | Qwen3-8B, prompt tiếng Anh phiên bản v9, RAG cục bộ và danh sách lựa chọn cho phép | 16/16 câu trả lời hợp lệ; không sửa định dạng hay thay bằng giám sát theo bản ghi; lợi nhuận ròng thấp hơn bộ chọn quy tắc | Không có thử nghiệm đối chứng prompt/RAG hay so mô hình theo cùng payload; độ hợp lệ không chứng minh giá trị kinh tế |
| Danh mục | 16 kỳ tháng, vốn mô phỏng 100 triệu đồng, 25 điểm cơ bản mỗi chiều | AGQO CAGR 18,81%, Sharpe 0,80, sụt giảm tối đa −11,90%; VN30 24,58%, 1,17, −9,22%; bộ chọn quy tắc 19,98%, 0,84, −11,90% | Khoảng tin cậy chủ động còn chứa 0; kỳ đã mở; thiên lệch sống sót; thiếu thuế, spread và dữ liệu khớp lệnh |
| Bộ giải | QAOA mô phỏng statevector NumPy/COBYLA, N=8/12/16, X và XY, p=1/2, 1.024 shots, ba seed | Đối chiếu với nghiệm chính xác trên cùng mục tiêu; regret và tỷ lệ khả thi biến đổi theo mixer/topology | Chưa có QPU, transpile theo backend, nhiễu, chi phí phần cứng hay lợi thế so với nghiệm vét cạn ở quy mô hiện tại |
| Tin tức | Bộ kiểm tra nguồn/mốc thời gian đã được thêm; danh sách ứng viên là HOSE và SSC | Không có bản ghi tin đủ điều kiện; tính năng chủ động tắt | Cần kiểm tra điều khoản nguồn, quyền lưu siêu dữ liệu, API/lịch sử và phiên bản bài trước khi thu thập |

## Quy mô bài toán và đối chứng công bằng

- Với 30 mã, chọn đúng 6 có 593.775 danh mục khả thi; nghiệm vét cạn đã chạy được trong khoảng 5,76 giây ở môi trường nghiên cứu được ghi nhận. Đây là bằng chứng hiện tại chống lại luận điểm “QAOA cần thiết” ở quy mô này.
- Với 12 mã, có 924 danh mục khả thi; với 16 mã, 8.008. Các kích thước này phù hợp để kiểm tra chính xác circuit, ràng buộc và sai số solver, nhưng không tự tạo ra thách thức tính toán thực tiễn.
- Mọi so sánh solver phải nhận cùng μ, Σ, λ, α, K, chi phí và tỷ trọng cũ. Báo chất lượng theo cùng ngân sách số lần đánh giá/shot, thời gian CPU và thời gian đến ngưỡng; exact là chuẩn khi vét cạn khả thi. Tham lam và tôi luyện mô phỏng là đối chứng phụ, không thay exact.
- Mọi đối chiếu lợi nhuận giữa rổ 12/16 mã và toàn bộ 30 mã phải ghi khác biệt phạm vi. Kết quả Ledoit–Wolf toàn rổ không phải đối chứng ngang tập ứng viên với QAOA 12 mã.

## Sổ rủi ro dữ liệu và suy luận

| Mã | Rủi ro | Tình trạng | Ảnh hưởng | Hành động đóng rủi ro |
|---|---|---|---|---|
| D1 | Thiên lệch sống sót do dùng thành phần VN30 hiện tại cho quá khứ | Đã triển khai một phần; cần kiểm toán | Làm sai tập tài sản có thể đầu tư tại ngày quyết định | Đã dựng khoảng hiệu lực từ snapshot neo và các lần thay đổi có nguồn; đối chiếu toàn bộ kỳ rà soát quý, thay đổi ngoài kỳ và mã đổi tên trước khi đóng |
| D2 | Điều chỉnh giá cho chia tách, cổ tức, quyền mua chưa xác nhận | Đã nối chuỗi điều chỉnh; cần xác minh | Có thể làm sai lợi nhuận, biến động, thanh khoản và bài toán tối ưu | Tải VCI đầy đủ; đối soát total-return với nguồn được phép và sổ sự kiện theo mã/ngày; đóng băng phiên bản |
| D3 | Quyền truy cập và tái phân phối của dữ liệu bên thứ ba | Đang mở | Không thể công bố tệp thô hoặc chuyển dữ liệu cho dịch vụ ngoài khi chưa có quyền | Giữ dữ liệu tại máy người dùng; kiểm tra điều khoản của nhà cung cấp gốc riêng với giấy phép thư viện |
| D4 | Thiên lệch nhìn trước/nhãn chồng lấn | Cần thêm kiểm tra | Làm quá lạc quan độ chính xác AI hoặc chọn policy | Ghi thời điểm tín hiệu/khớp/lối ra; purge/embargo theo 21 phiên; chỉ dùng kết quả đã đáo hạn |
| D5 | Tập kiểm định đã xem qua | Đang mở | Tối ưu quá mức theo một cửa sổ thị trường | Đóng băng mã và báo cáo trước khi thu thập giai đoạn mới; không tái sử dụng 2025–2026 làm holdout |
| D6 | Đo thanh khoản bằng giá đóng cửa × khối lượng | Đang mở | Không tính spread, market impact, trượt giá và khả năng khớp từng lệnh | Gọi đây là proxy; thêm báo giá/turnover đáng tin khi có quyền; stress chi phí và participation |
| M1 | Qwen có thể chọn policy hợp lệ nhưng không tăng giá trị | Đã thấy tín hiệu âm | Không có luận cứ cho đóng góp kinh tế của LLM | So ablation no-RAG/RAG, quy tắc, cố định, lặp seed trên cùng payload và ngân sách; lấy utility ngoài mẫu làm cổng |
| Q1 | Mạch đẹp nhưng không gắn với circuit thật/ánh xạ tài sản | Đã xử lý một phần | Hình minh họa không chứng minh cấu hình đã chạy | Sinh catalog mạch từ record theo signal, seed, permutation, ticker-map, góc, cổng và cạnh mixer; phân biệt circuit logic với mạch sau transpile |
| Q2 | QAOA chạy mô phỏng cổ điển, không có phần cứng | Đang mở | Không thể tuyên bố ưu thế lượng tử, nhiễu hay chi phí thực thi | Giữ tuyên bố ở chất lượng solver mô phỏng; chỉ mở cổng hardware khi backend, transpile, shots và đối chứng được cân bằng |
| N1 | Tin tức hồi cứu, dấu xuất bản không xác nhận hoặc ghép sai mã | Đang mở; news tắt sau HTTP 429 | Rò rỉ tương lai, phủ sai mã và câu chuyện nhân quả hậu nghiệm | Bộ lọc mã nguồn đòi dấu `seendate` và giờ thu thập trước cutoff; hiện không có bản ghi. Sau khi nguồn cho phép, chỉ bật lượt thu đủ bí danh; dùng nguồn phát hành có thời điểm xuất bản và ghép mã kiểm chứng trước mọi nhận định sự kiện |

## Điều kiện chấp nhận tin ngoài

Nhánh GDELT chỉ được dùng như **bối cảnh về độ phủ truy vấn**: URL, mã truy vấn, mã bằng chứng, dấu lần đầu nguồn ghi nhận, giờ thu thập và mã băm siêu dữ liệu. Không lưu tiêu đề/toàn văn, không suy ra cảm xúc và không gọi đây là giờ xuất bản. Bộ chạy chỉ chấp nhận manifest xác nhận đã truy vấn đủ bí danh và cả hai mốc không sau cutoff. Phân tích sự kiện đã xuất bản cần nguồn riêng có tiêu đề/siêu dữ liệu được cấp quyền, giờ công bố kèm múi giờ và mã sửa đổi; mọi kết luận nhân quả cần thiết kế kiểm định riêng.

Lịch thành phần hiện được dựng từ các thông báo rà soát công khai gắn theo từng kỳ trong `data/vn30_snapshot_20261002/vn30_membership_events.csv`; đây là bản tổng hợp mã nguồn, chưa thay thế dữ liệu lịch sử chính thức có bản quyền và chưa rà hết các kỳ không thay đổi. Tin tức ngoài dùng GDELT DOC theo chế độ thu thập siêu dữ liệu; tệp hiện có không chứa bản ghi và lần thử truy vấn nhận HTTP 429, nên tin chưa tham gia phân tích. Trạng thái, quyền và giới hạn được ghi trong [manifest tin tức](data/news/manifest.json).

Trong bước rà soát nguồn công khai, thông cáo HOSE về kỳ rà soát tháng 7/2025 ghi nhận đây là kỳ đầu áp dụng phiên bản 4.0 của phương pháp chỉ số; tài liệu cũng nêu giới hạn tỷ trọng ngành 40% trong bản cập nhật liên quan. Đây là thông tin về cách cấu tạo chỉ số, hữu ích khi diễn giải rủi ro dùng snapshot thành phần hiện tại. Nó **không** được đưa vào đặc trưng mô hình, không phải bản tin gắn với từng mã và không chứng minh nguyên nhân cho lợi suất quan sát. [Thông cáo HOSE tháng 7/2025](https://staticfile.hsx.vn/Uploads/UploadDocuments/2391309/TCBC_%20Cai%20tien%20chi%20so%20VN30%20t7.2025.pdf).

## Hướng quyết định

1. Không tối ưu thêm số qubit hay kích thước LLM trên cửa sổ đã xem để tìm con số đẹp.
2. Đăng ký quyền Vnstock Cộng đồng miễn phí, tải lại chuỗi VCI toàn kỳ, kiểm toán toàn bộ lịch VN30 và giữ manifest chỉ rõ nguồn/quyền/mã băm.
3. Đóng băng tập ngoài mẫu mới và ngưỡng kinh tế trước khi chạy.
4. Chạy lại đối chứng tài chính cùng vũ trụ, phí, lịch tái cân bằng; đánh giá AI bằng ablation cùng ngân sách.
5. Chạy đối chứng QAOA–exact–heuristic; tăng N chỉ khi exact bắt đầu tốn kém và bài toán vẫn tương đương về ý nghĩa tài chính.
6. Chỉ bật news/RAG sau khi thu được bản ghi có mốc thời gian và quyền dùng; nếu chưa có thì giữ tắt.

**Kết luận hiện tại:** giá trị tích hợp AGQO đã được chứng minh; giá trị tài chính tăng thêm của LLM, độ tin cậy dự báo chế độ, và lợi thế tài nguyên của QAOA đều **chưa được xác lập**. Phân tích tiếp theo phải tạo dữ liệu ngoài mẫu và cải thiện nguồn dữ liệu trước khi thêm độ phức tạp.
