# Lời nói thuyết trình, bản 3 phút và thẻ hỏi–đáp

Sinh tự động từ `submission/deck/story.yaml` và `qa.yaml` (cùng số liệu với deck). Sửa ở đó rồi chạy lại `python submission/deck/notes_doc.py`.

## Bản đầy đủ (8 slide, khoảng 8–9 phút)

### Slide 1. Với 20 triệu đồng, một lô VIC đắt hơn cả tài khoản

- **Câu mở:** Ngày 1 tháng 10 năm 2026, một lô VIC giá 22 triệu đồng, tức bằng 110% tài khoản 20 triệu.
- **Nhìn vào:** Chỉ vào cột VIC vượt qua vạch 100%, rồi lướt sang phải để thấy hàng loạt mã nằm trên vạch 10%.
- **Ý chính:** Với tài khoản nhỏ, mỗi lệnh mua là một bước nhảy lớn về tỷ trọng: bộ tối ưu muốn khoảng 10,7% FPT, nhưng chỉ chọn được 0% hoặc 31,4%.
- **Chuyển ý:** Vậy một người có 20 triệu muốn bám VN30 thì đang có những lựa chọn nào?

### Slide 2. Người có 20 triệu muốn bám VN30 đang có ba lựa chọn, mỗi cái đổi một thứ

- **Câu mở:** Chúng em đặt ba lựa chọn cạnh nhau và cố ý cho mỗi cái một chỗ công bằng.
- **Nhìn vào:** Đi từ trái sang phải; dừng ở dòng thứ hai của mỗi cột: đó là cái giá của lựa chọn.
- **Ý chính:** Lô lẻ bám tốt nhất trong mô phỏng, ETF tiện nhất; danh mục lô chẵn là lựa chọn duy nhất ở đây cho phép đặt quy tắc riêng mà vẫn dùng sổ lệnh chính.
- **Chuyển ý:** Bây giờ mời ban giám khảo xem đúng một quyết định như vậy được tạo ra thế nào.

### Slide 3. Cùng 20 triệu, cùng ngày: AI hiểu yêu cầu, bạn xác nhận, rồi mới có lệnh

- **Câu mở:** Người dùng của chúng em gõ đúng một câu: không đầu tư bất động sản, ngân hàng tối đa 30%.
- **Nhìn vào:** Bấm lần 1 hiện câu yêu cầu, lần 2 hiện hai ràng buộc và nguồn diễn giải, lần 3 hiện hai danh mục. Chờ hai giây trước khi nói.
- **Ý chính:** Làm tròn lô gần nhất chỉ mua được 1 mã và để 89% vốn nằm im; AGQO mua 5 mã, giữ 5,0 triệu tiền mặt sau phí, sai số bám ước tính 11,78% thay vì 17,68%. Ngân hàng thực tế 29,38%, dưới trần.
- **Chuyển ý:** Một quyết định có thể may mắn. Câu hỏi tiếp theo là: qua 12 quý thì sao?

### Slide 4. Qua 12 quý, lợi thế lớn nhất nằm ở tài khoản nhỏ, và thuật toán tham lam theo rất sát

- **Câu mở:** Chúng em chạy lại cùng cách làm qua 12 quý, ở năm cỡ tài khoản, trên cùng một thang đo.
- **Nhìn vào:** Nhìn nhóm cột 20 triệu trước: cột xám đậm cao gấp đôi. Rồi nhìn cột xám nhạt: thuật toán tham lam đứng sát AGQO.
- **Ý chính:** Tối ưu tổ hợp lô là phần tạo ra giá trị; một thuật toán cổ điển tốt đã lấy được gần hết. Từ 100 triệu trở lên, lô đủ nhỏ và khác biệt gần như biến mất.
- **Chuyển ý:** Vậy phần lượng tử nằm ở đâu trong bài toán này? Chúng em giải thích bằng đúng một mã.

### Slide 5. Một qubit là một câu hỏi: mua thêm một lô mã này hay không?

- **Câu mở:** Lấy SSI: bộ tối ưu, nếu được mua lẻ, muốn khoảng 0,44 lô.
- **Nhìn vào:** Đi từ ô SSI xuống bit x, rồi mở rộng ra 16 bit, rồi mới chỉ cặp VPB–TCB và dòng quy tắc.
- **Ý chính:** Bài toán của tài khoản nhỏ là 16 câu hỏi có/không phụ thuộc lẫn nhau. Đó chính xác là dạng bài QAOA nhận vào; và vì chỉ có 65.536 tổ hợp, máy tính cổ điển liệt kê hết để kiểm chứng.
- **Chuyển ý:** Vậy mạch lượng tử đã làm thay đổi điều gì?

### Slide 6. Mạch được thiết kế làm tăng xác suất gặp lựa chọn gần tối ưu ở mỗi lần đo

- **Câu mở:** Ở đây chúng em đo một thứ rất cụ thể: mỗi lần đo mạch, xác suất ra một danh mục gần tối ưu là bao nhiêu.
- **Nhìn vào:** Đọc từ dưới lên: QAOA sách giáo khoa 1,1%, mốc warm start 3,1%, rồi tới mạch thiết kế khoảng 21–24%.
- **Ý chính:** Thiết kế mạch từ dữ liệu làm tăng xác suất mỗi lần đo khoảng bảy lần so với khởi đầu cổ điển. Nhưng chúng em cũng thấy bước tinh chỉnh không giúp, và lịch cố định đơn giản tốt ngang.
- **Chuyển ý:** Với những gì đã đo được, bước tiếp theo hợp lý là gì?

### Slide 7. Bước tiếp theo: thử nghiệm thí điểm với một công ty chứng khoán, giải bằng cổ điển, giữ QAOA là hướng nghiên cứu

- **Câu mở:** Nếu một công ty chứng khoán muốn thử AGQO, có ba thứ kiểm chứng được ngay và bốn thứ còn thiếu.
- **Nhìn vào:** Đọc cột giữa chậm lại: đây là những thứ chúng em thiếu khi tự chạy prototype.
- **Ý chính:** Ở 16 qubit, triển khai nên dùng bộ giải cổ điển. Phần đã chạy và kiểm chứng được là chuỗi hiểu yêu cầu, xác nhận, tối ưu theo lô và kiểm tra quy tắc.
- **Chuyển ý:** Quay lại với người có 20 triệu lúc đầu.

### Slide 8. Quay lại người có 20 triệu: giờ họ thấy cái giá của từng quy tắc trước khi đặt lệnh

- **Câu mở:** Người có 20 triệu ở đầu bài giờ có một danh mục 5 mã và biết chính xác nó lệch VN30 bao nhiêu.
- **Nhìn vào:** Dừng ở dòng thứ hai: đây là con số họ thường không bao giờ được thấy.
- **Ý chính:** AGQO biến một yêu cầu tiếng Việt thành ràng buộc được xác nhận, một danh mục lô chẵn tối ưu và một bảng kiểm tra quy tắc có thể đối chiếu.
- **Chuyển ý:** Chúng em xin cảm ơn và sẵn sàng nhận câu hỏi; phụ lục có công thức, nhiễu, quy mô và cách tái lập.

## Bản 3 phút (slide 1, 3, 4, 8)

Bỏ slide 2, 5, 6, 7; nếu được hỏi về lượng tử, mở slide 6 hoặc phụ lục A2–A4.

**Slide 1 (~45 giây).** Ngày 1 tháng 10 năm 2026, một lô VIC giá 22 triệu đồng, tức bằng 110% tài khoản 20 triệu. Với tài khoản nhỏ, mỗi lệnh mua là một bước nhảy lớn về tỷ trọng: bộ tối ưu muốn khoảng 10,7% FPT, nhưng chỉ chọn được 0% hoặc 31,4%.

**Slide 3 (~45 giây).** Người dùng của chúng em gõ đúng một câu: không đầu tư bất động sản, ngân hàng tối đa 30%. Làm tròn lô gần nhất chỉ mua được 1 mã và để 89% vốn nằm im; AGQO mua 5 mã, giữ 5,0 triệu tiền mặt sau phí, sai số bám ước tính 11,78% thay vì 17,68%. Ngân hàng thực tế 29,38%, dưới trần.

**Slide 4 (~45 giây).** Chúng em chạy lại cùng cách làm qua 12 quý, ở năm cỡ tài khoản, trên cùng một thang đo. Tối ưu tổ hợp lô là phần tạo ra giá trị; một thuật toán cổ điển tốt đã lấy được gần hết. Từ 100 triệu trở lên, lô đủ nhỏ và khác biệt gần như biến mất.

**Slide 8 (~45 giây).** Người có 20 triệu ở đầu bài giờ có một danh mục 5 mã và biết chính xác nó lệch VN30 bao nhiêu. AGQO biến một yêu cầu tiếng Việt thành ràng buộc được xác nhận, một danh mục lô chẵn tối ưu và một bảng kiểm tra quy tắc có thể đối chiếu.

Câu cuối: Với AGQO, người có 20 triệu biết mỗi quy tắc của mình làm danh mục lệch VN30 thêm bao nhiêu, trước khi bấm đặt lệnh.

## Thẻ hỏi–đáp

**1. Ở 16 qubit máy tính cổ điển liệt kê hết rồi, vậy nghiên cứu QAOA để làm gì?**

Đúng, ở 16 qubit liệt kê toàn bộ 65.536 tổ hợp mất khoảng 0,12 giây, và chúng em dùng chính phép liệt kê đó làm đáp án để chấm mạch. Kích thước này là chỗ duy nhất đo được chính xác mạch tốt hay dở. Khi tăng lên 20 qubit, liệt kê mất 2,4 giây và tăng gấp đôi sau mỗi qubit; xác suất mạch lấy đúng giảm từ 30,0% xuống 12,9%. Vì vậy với sản phẩm hôm nay, chúng em đề xuất bộ giải cổ điển.

*Mở:* Slide 6, phụ lục A4; results/final/extras/scaling.csv

**2. Vì sao người dùng chọn lô chẵn thay vì ETF hay lô lẻ?**

Nếu không có quy tắc riêng, ETF tiện hơn và lô lẻ bám tốt hơn trong mô phỏng của chúng em (2,53%). Lô chẵn có ý nghĩa khi người dùng muốn bỏ một ngành hay giới hạn ngân hàng, điều ETF không làm được, và muốn đặt lệnh trên sổ lệnh chính. Lô lẻ có sổ lệnh riêng, thanh khoản mỏng hơn; mô phỏng của chúng em chưa tính trượt giá đó.

*Mở:* Slide 2, phụ lục A8

**3. k-NN thêm được gì khi kiểm định?**

Trên 330 bài toán holdout mới, k-NN hơn lịch cố định 0,76 điểm % xác suất mỗi lần đo, thắng 20/22 tháng. Nhưng chỉ cần chọn một lịch riêng cho mỗi cỡ tài khoản cũng được đúng mức đó. Con số 21,3% < 23,8% của nghiên cứu chính đến từ bước tinh chỉnh COBYLA, không phải từ k-NN: bỏ tinh chỉnh thì k-NN đạt 24,0%.

*Mở:* Phụ lục A6; docs/technical/RESEARCH_RESULTS.md §2

**4. Nếu AI hiểu sai yêu cầu thì ai phát hiện?**

Có ba lớp. Một, ràng buộc AI hiểu được hiện thành các ô có nhãn nguồn; người dùng phải bấm xác nhận thì mới có lệnh, câu mơ hồ hay mâu thuẫn thì phải trả lời trước. Hai, bộ tối ưu và phép kiểm tra quy tắc là mã cố định, tính trên giá trị tài khoản sau phí. Ba, lời giải thích của AI bị đối chiếu từng con số với dữ liệu; câu nào sai, kể cả câu nói thị trường cấm lô lẻ, bị thay bằng giải thích tạo tự động.

*Mở:* Slide 3; phụ lục A5; tests/test_review.py

**5. Thuật toán tham lam ngang AGQO, vậy AGQO đóng góp gì?**

Chúng em đưa thuật toán tham lam vào chính vì nó mạnh. Ở 20 triệu, chênh lệch với AGQO là −0,69 điểm % với khoảng tin cậy từ −1,53 đến +0,02, chưa có ý nghĩa thống kê; khi có hai quy tắc thì gần như bằng nhau. Phần tạo giá trị là tối ưu cả tổ hợp lô thay vì làm tròn từng mã; AGQO cho nghiệm tối ưu chính xác trong không gian đã mã hoá và kiểm chứng được.

*Mở:* Slide 4; phụ lục A7

**6. Có phải ưu thế lượng tử không?**

Không. Mọi kết quả lượng tử là mô phỏng; mô hình nhiễu ESP và mô phỏng Aer cho thấy mạch nông vẫn có tín hiệu, nhưng chúng em chưa chạy phần cứng thật và không khẳng định ưu thế.

*Mở:* Phụ lục A3, A10

**7. Vì sao danh mục AGQO ở slide 3 để lại 5 triệu tiền mặt?**

Với 20 triệu và hai quy tắc, nhiều lô quá lớn: một lô MSN đã là 35% tài khoản. Mua thêm một lô bất kỳ còn lại sẽ làm danh mục lệch VN30 nhiều hơn là giữ tiền. Con số tiền mặt sau phí hiện ngay cạnh lệnh để người dùng thấy đánh đổi đó.

*Mở:* Slide 3; ảnh màn hình docs/assets/screenshots/pitch_result.png

**8. Giá lịch sử đã điều chỉnh có làm sai kết quả tài khoản nhỏ không?**

Có thể, vì giá lô quá khứ bị tính rẻ hơn giá khớp thật. Chúng em chưa có giá khớp gốc nên đo giới hạn: nếu giá lô cao hơn tới 50%, AGQO vẫn thấp hơn làm tròn khoảng 4,9 điểm %. Chênh lệch riêng từng mã thì chưa đo được.

*Mở:* Phụ lục A7

**9. Demo dùng LLM trực tiếp hay phát lại?**

Trang ghi rõ từng trường hợp. Trong buổi thi chúng em dùng câu trả lời Qwen đã lưu cho câu mẫu, vì GPU khởi động lạnh mất 440 giây; phần tối ưu vẫn chạy trực tiếp trên Modal, khoảng 5–11 giây. Nếu GPU đã ấm, Qwen trả lời trong khoảng 4 giây.

*Mở:* Phụ lục A9

**10. Quy tắc 30% tính trên cơ sở nào?**

Trên giá trị tài khoản sau phí: tiền mặt còn lại sau khi trả phí cộng giá trị cổ phiếu vừa mua. Bản trước tính trên vốn ban đầu nên từng báo đạt ở 25,03%; bản này siết trần theo biên phí và kiểm tra lại sau phí.

*Mở:* Slide 3; tests/test_product.py
