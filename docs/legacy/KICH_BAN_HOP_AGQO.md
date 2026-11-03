# Kịch bản trình bày AGQO trong cuộc họp nhóm

**Thời lượng:** khoảng 4–5 phút  
**Mục tiêu:** thống nhất mọi người hiểu đúng phần đã làm, bằng chứng hiện có, giới hạn và phần frontend cần triển khai.

## 1. Mở đầu — bài toán và ý tưởng

“Em xin cập nhật phần backend của AGQO. Bài toán của nhóm là chọn một danh mục cổ phiếu có ràng buộc: từ nhóm ứng viên, chọn đúng sáu mã sao cho cân bằng lợi suất kỳ vọng, rủi ro tương quan và chi phí giao dịch.

Ý tưởng AGQO là AI hướng dẫn bộ tối ưu lượng tử. LLM không tự chọn cổ phiếu và cũng không tự bịa công thức. Hệ thống tính insight từ dữ liệu, đưa bằng chứng và danh sách cấu hình được phép cho Qwen chọn chính sách QAOA. Bộ giám sát kiểm tra lựa chọn đó; sau cùng QAOA tạo danh mục. Bộ giải cổ điển được dùng làm chuẩn để biết QAOA tìm nghiệm tốt đến đâu.”

## 2. Những gì backend đã có

“Em đã nối các phần thành một pipeline có thể truy vết: dữ liệu giá → đặc trưng và insight → Qwen3-8B với prompt tiếng Anh có cấu trúc và tài liệu RAG → bộ giám sát → QAOA → đối chứng cổ điển → mô phỏng hiệu quả tài chính.

QAOA hiện được mô phỏng bằng statevector trên CPU. Mỗi qubit đại diện cho một cổ phiếu ứng viên; trạng thái bit quyết định có chọn mã đó hay không. Các cấu hình đã lưu thử 8, 12 và 16 qubit, chọn K bằng 6, mixer X hoặc XY, độ sâu p bằng 1 hoặc 2 và nhiều bố trí kết nối. Nghiệm chính xác, greedy và simulated annealing giúp đo regret, khả năng thỏa ràng buộc và thời gian giải.

Ngoài ra, em đã thêm lịch thành phần VN30 theo ngày hiệu lực vào pipeline, tách hướng xử lý giá thô và giá điều chỉnh, cùng một bộ thu thập metadata tin tức có lọc theo thời điểm. Đây là phần chuẩn bị để giảm sai lệch dữ liệu.”

## 3. Nói bằng số liệu — và giới hạn của số liệu

“Lượt backtest hiện có dùng 37.308 dòng dữ liệu, 30 cổ phiếu cùng VN30 và VN-Index, từ ngày 4 tháng 1 năm 2022 đến 19 tháng 10 năm 2026. Trong 16 kỳ tháng đã đo, AGQO đạt CAGR ròng 18,81%, Sharpe 0,80 và sụt giảm tối đa 11,90%. VN30 đạt CAGR 24,58%, Sharpe 1,17 và sụt giảm tối đa 9,22%. Bộ chọn quy tắc không dùng LLM đạt CAGR 19,98%.

Vì vậy em không kết luận AGQO đang thắng về lợi nhuận. Kết quả này cho thấy pipeline tích hợp đã chạy và tạo được phép so sánh định lượng; nó chưa chứng minh LLM tăng lợi nhuận hay QAOA tốt hơn bộ giải cổ điển. Đoạn kiểm định phụ 12 phiên cũng là chẩn đoán ngắn, không phải tập mù.”

## 4. Trạng thái dữ liệu cần cả nhóm nắm

“Có một điểm quan trọng: các con số vừa nêu thuộc lượt chạy cũ. Mã mới đã có lịch thành phần theo thời gian và yêu cầu giá điều chỉnh, nhưng kết quả chưa được tính lại vì dữ liệu Vnstock Guest giới hạn lịch sử 365 ngày. Cần đăng ký miễn phí Vnstock Cộng đồng rồi tải lại dữ liệu 2022–2026. Cho tới lúc đó, không được nói các kết quả cũ đã loại bỏ thiên lệch sống sót hay đã xử lý đầy đủ cổ tức và chia tách.

Tin tức cũng chưa được đưa vào mô hình. Lần thu GDELT bị HTTP 429 và manifest ghi rõ không có bản tin khả dụng. Vì vậy các insight hiện chỉ mô tả giá, biến động, tương quan, độ rộng và thanh khoản; không gán biến động cho tin tức cụ thể.”

## 5. Việc cần frontend làm

“Em muốn frontend kể đúng câu chuyện backend này theo từng bước, thay vì chỉ trưng biểu đồ. Trang tổng quan cần đặt AGQO cạnh VN30, VN-Index, quy tắc và nghiệm cổ điển; hiển thị rõ lãi/lỗ sau phí, Sharpe và sụt giảm. Trang insight cần cho xem trạng thái thị trường theo ngày, lợi suất chéo, tương quan và độ phủ dữ liệu.

Một trang truy vết quyết định cần cho thấy ngày chốt dữ liệu, insight nào được dùng, Qwen đề xuất gì, bộ giám sát giữ hay thay, cấu hình QAOA nào chạy, sáu mã được chọn, rồi regret và kết quả tài chính ra sao. Một trang QAOA cần trực quan hóa qubit, mixer, độ sâu, layout và so sánh với exact. Mọi chart cần tiêu đề, đơn vị, kỳ, nguồn và một câu giải nghĩa.

Bản đầu có thể đọc thẳng các JSON, CSV và ảnh đã lưu trong dự án, chưa cần API mới. Cần có nhãn dễ thấy: kết quả cũ; lượt hiệu chỉnh chưa chạy lại; QAOA mô phỏng CPU; tin tức chưa tham gia. Không được điền số giả vào phần chưa có dữ liệu.”

## 6. Chốt cuộc họp

“Sau cuộc họp, em đề xuất chia frontend thành ba luồng: tổng quan hiệu quả và benchmark; insight thị trường và dữ liệu; truy vết LLM–QAOA và mạch. Một người tích hợp làm data adapter và kiểm tra hiển thị. Cả nhóm thống nhất hợp đồng dữ liệu trước, rồi làm giao diện từ tệp kết quả đang có.

Song song, backend cần mở quyền tải dữ liệu Vnstock, tải lại giá điều chỉnh và tính lại walk-forward. Khi có kết quả mới, frontend thay dữ liệu qua adapter và cập nhật trạng thái bằng chứng. Mục tiêu là trình bày trung thực: hiện ta có một hệ thống nghiên cứu tích hợp và kiểm toán được; bước tiếp theo là kiểm định lại dữ liệu đúng chuẩn và chứng minh giá trị so với đối chứng.”

## Câu hỏi có thể gặp

**“Vậy QAOA đang tạo ra giá trị gì?”**  
“Hiện tại QAOA là bộ giải tổ hợp trong kiến trúc AGQO và là đối tượng đo chất lượng nghiệm, khả năng thỏa ràng buộc và chi phí mạch. Chưa có bằng chứng nó tạo lợi thế tài chính hoặc ưu thế tính toán so với exact/heuristic ở kích thước đang thử.”

**“LLM có tự suy luận tài chính không?”**  
“LLM chọn trong danh sách chính sách cho phép và viện dẫn mã insight/bằng chứng. Insight số học do pipeline tính; RAG cung cấp định nghĩa và giới hạn; bộ giám sát có quyền từ chối. Kết quả hiện chưa chứng minh quyết định của LLM tốt hơn bộ chọn quy tắc.”

**“Có thể trình bày CAGR 18,81% như kết quả cuối không?”**  
“Chỉ trình bày là kết quả của lượt chạy cũ, trên 16 kỳ và dữ liệu chưa hiệu chỉnh/thiên lệch thành phần. Phải đặt cạnh chuẩn và nói rõ chưa phải kết quả đã sửa dữ liệu.”
