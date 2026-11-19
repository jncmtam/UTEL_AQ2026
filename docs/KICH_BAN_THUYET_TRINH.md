# Kịch bản thuyết trình AGQO và chuẩn bị câu hỏi phản biện

Tài liệu này là lời nói, không phải slide. Phần I là bài trình bày khoảng 10 phút, chia theo mốc thời
gian. Phần II là các câu hỏi khó về tài chính và kỹ thuật, kèm câu trả lời ngắn để nói. Phần III là bảng
số liệu cần thuộc. Mọi con số đều lấy từ `results/final/`.

**Quy ước khi nói**
- *[Hình …]*: nếu được chiếu màn hình, mở hình đó trong README. Không chiếu được thì cứ nói, câu chữ đã đủ ý.
- **In đậm** là con số hoặc câu cần nhấn giọng.
- Nói "chúng em", gọi "thưa ban giám khảo" ở mở đầu, chuyển phần và kết luận, không lặp lại liên tục.
- Mỗi con số nói xong thì dừng nửa giây. Giám khảo nhớ con số, không nhớ tính từ.

---

# PHẦN I. BÀI TRÌNH BÀY (khoảng 10 phút)

## 0. Mở đầu (0:00 – 0:40)

> Thưa ban giám khảo, chúng em xin bắt đầu bằng một con số. Ngày 1 tháng 10 năm 2026, một lô cổ phiếu VIC,
> tức 100 cổ phiếu, có giá khoảng **22 triệu đồng**. Một nhà đầu tư mới với tài khoản **20 triệu đồng** muốn nắm giữ danh mục
> giống chỉ số VN30. Bộ tối ưu nói: hãy giữ khoảng 10% VIC. Nhưng tài khoản này chỉ có hai lựa chọn: 0%,
> hoặc 110% số tiền mình có.
>
> Đó là bài toán chúng em giải: **biến một danh mục lý tưởng thành những lô 100 cổ phiếu mà nhà đầu tư nhỏ
> thực sự mua được**, theo đúng quy tắc riêng của họ. Dự án của chúng em tên là **AGQO, AI-Guided Quantum
> Optimisation**: tối ưu lượng tử được dẫn dắt bởi AI.

## 1. Vấn đề tài chính (0:40 – 2:00)

*[Hình 01 và A4]*

> Trên HOSE, cổ phiếu giao dịch theo lô 100. Với tài khoản 100 triệu, theo giá giữa tháng 11, một lô cổ
> phiếu VN30 chiếm từ **1% đến 24%** tài sản. Với tài khoản 20 triệu, lô đắt nhất **vượt quá 100%**.
>
> Cách làm phổ biến là lấy trọng số lý tưởng rồi làm tròn từng mã về lô gần nhất. Với tài khoản 20 triệu,
> cách này làm tròn gần như mọi mã về 0 và **để 90% tài khoản nằm trong tiền mặt**. Kết quả là sai số bám
> so với VN30 lên tới **12,1% mỗi năm**.
>
> Nhà đầu tư có thể mua chứng chỉ quỹ ETF VN30. Nhưng ETF không cho phép nói "tôi không muốn bất động
> sản", hay "ngân hàng tối đa 30%". Trong khi đó, Việt Nam có **hơn 14,3 triệu tài khoản chứng khoán của
> nhà đầu tư cá nhân trong nước** tính đến cuối tháng 10 năm 2026, theo số liệu của Trung tâm Lưu ký. Phần
> lớn là tài khoản nhỏ, đúng chỗ mà bài toán lô chẵn gây hại nhiều nhất.
>
> Chọn mã nào được thêm một lô là một bài toán nhị phân. Với 16 mã, có **65.536 tổ hợp**. Và đó chính là
> thanh ghi lượng tử của chúng em.

## 2. Giải pháp tổng thể (2:00 – 3:00)

*[Hình A1]*

> AGQO có ba vai trò rõ ràng. **AI đọc** thị trường và nhà đầu tư. **Lượng tử lấy mẫu** quyết định mua
> lô. **Máy tính cổ điển kiểm chứng** mọi quyết định trước khi đưa ra.
>
> Nguyên tắc thiết kế quan trọng nhất của chúng em: **không có con số nào của AI đi thẳng vào bộ tối ưu mà
> không qua kiểm tra**. Ràng buộc do LLM tạo ra được code kiểm tra. Lịch tham số do mô hình học chọn chỉ
> định hình mạch. Và không mẫu nào được thực hiện nếu không qua kiểm tra chính xác về tiền mặt, phí, thuế
> và giới hạn của nhà đầu tư.

## 3. Pha 1: AI đọc dữ liệu và đọc nhà đầu tư (3:00 – 4:15)

*[Hình 02, 03]*

> Pha 1a là thống kê. Chúng em dùng dữ liệu ngày của **40 mã từng nằm trong VN30** từ 2022 đến tháng
> 11/2026, có tính đúng thời điểm vào rổ và ra rổ để tránh thiên lệch sống sót. Phát hiện chính: VN30
> hành xử như khoảng **13 nguồn rủi ro độc lập**, không phải 30, và một yếu tố thị trường chung giải thích
> khoảng **40%** biến động. Điều này cho biết khoảng 20 mã nắm giữ theo lô chẵn là đủ để bám chỉ số, và
> quyết định lô của các mã cùng biến động sẽ ảnh hưởng lẫn nhau. Khoảng **90%** độ mạnh liên kết giữa các
> qubit đến từ việc các cổ phiếu cùng biến động. Tức là cổng hai qubit trong mạch mang thông tin rủi ro
> tài chính thật.
>
> Pha 1b là mô hình ngôn ngữ lớn. Chúng em dùng **Qwen3.8-27B**, mô hình mã nguồn mở, chạy bằng vLLM trên
> một GPU H100. Nhà đầu tư viết bằng tiếng Việt: *"Không đầu tư bất động sản, ngân hàng tối đa 30%"*. Mô hình
> trả về JSON theo một lược đồ cố định: mã cổ phiếu và ngành chỉ được chọn trong danh sách, con số có giới
> hạn. Code kiểm tra từng trường rồi mới đưa vào bài toán.
>
> Trên **35 câu lệnh tiếng Việt** gán nhãn tay, mô hình đúng **35/35**, còn bộ quy tắc từ khóa chỉ đúng
> **68,6%**. Khi nhà đầu tư nói mơ hồ, như "đừng mua quá nhiều ngân hàng", mô hình không tự bịa con số mà
> hỏi lại: "Bạn muốn giới hạn tối đa bao nhiêu phần trăm?"

## 4. Từ tài chính sang qubit (4:15 – 5:15)

*[Hình A2, bên phải]*

> Mỗi qubit mang một ý nghĩa tài chính: **"có mua thêm một lô mã này hay không"**. Hamiltonian của chúng
> em **chính là** mục tiêu tài chính, không phải một hàm xấp xỉ: phương sai sai số bám so với VN30, cộng
> chi phí thay đổi danh mục, cộng một phạt ngân sách. Chúng em kiểm tra đẳng thức này trên toàn bộ 65.536
> trạng thái, sai số dưới 10⁻¹².
>
> Điểm mới thứ nhất: **giới hạn của nhà đầu tư nằm trong thanh ghi, không nằm trong hàm phạt**. Ban đầu
> chúng em thử phạt từng cặp vi phạm, và nó thất bại: ba lô thêm có thể vượt trần ngành dù từng cặp đều
> hợp lệ, mà QUBO không phạt được bộ ba. Nên chúng em xây thanh ghi sao cho mã thuộc nhóm bị giới hạn chỉ
> được cấp qubit khi tất cả các lô thêm của nhóm vẫn nằm dưới trần. Kết quả: **cả 65.536 trạng thái đều
> tuân thủ quy tắc**, ngay từ cấu trúc.

## 5. Pha 2: mạch lượng tử được viết từ dữ liệu (5:15 – 6:30)

*[Hình A2, bên trái; hình 04]*

> Mạch QAOA của chúng em có năm quy tắc thiết kế, mỗi quy tắc đọc từ một đặc trưng của dữ liệu:
> - **Khởi động ấm**: giải bài toán nới lỏng liên tục, rồi đặt góc quay ban đầu cho từng qubit.
> - **Mixer căn chỉnh** với trạng thái khởi động đó.
> - **Giữ những liên kết mạnh nhất**.
> - **Chuẩn hóa Hamiltonian theo độ lớn trung bình**, để một bộ tham số dùng được cho mọi quý.
> - **Lịch tham số tăng tuyến tính**, chỉ hai con số thay vì hàng chục góc tự do.
>
> Năm quy tắc này đều lấy từ các công trình đã công bố, từ 2021 đến 2025.
>
> Phần "AI dẫn dắt" là một mô hình học có giám sát. Chúng em mô phỏng chính xác **1.080 lịch tham số** trên
> **48 bài toán huấn luyện** của năm 2023. Với một quý mới, mô hình tìm những bài toán giống nhất theo 5
> đặc trưng dữ liệu, rồi chọn độ sâu và góc cho mạch. Toàn bộ hiệu chỉnh chỉ dùng dữ liệu năm 2023. Mọi kết
> quả sau đây là trên **12 quý từ 2024 đến 2026 mà mô hình chưa từng thấy**.

## 6. Kết quả lượng tử (6:30 – 7:30)

*[Hình A3, 05]*

> Thước đo của chúng em là xác suất một lần đo cho ra quyết định gần tối ưu, tức cách tối ưu chính xác
> không quá 5%. Đáp án tối ưu được biết chắc vì chúng em liệt kê đủ 65.536 trường hợp.
>
> Đoán ngẫu nhiên đạt **0,2%**. Chỉ dùng trạng thái khởi động cổ điển đạt **3,1%**. QAOA sách giáo khoa đạt
> **1,1%**. Mạch AGQO đạt **21,3%**: gấp **6,9 lần** khởi động cổ điển, **19 lần** QAOA sách giáo khoa,
> **2,8 lần** tìm kiếm ngẫu nhiên trên không gian thiết kế. Thắng trong **12 trên 12 quý**, kiểm định
> Wilcoxon **p = 0,0005**, mức nhỏ nhất có thể với 12 quý. Trong cả 12 quý, 512 lần đo của AGQO đều chứa
> đúng nghiệm tối ưu.

## 7. Kết quả tài chính (7:30 – 8:45)

*[Hình 08, 10]*

> Với tài khoản **20 triệu**, sai số bám so với VN30 giảm từ **12,1% xuống 6,8%** mỗi năm. Khoảng tin cậy
> 95% của mức giảm là từ 3,8 đến 6,9 điểm phần trăm, xa số 0. Bằng tiền, độ lệch điển hình mỗi năm so với
> chỉ số giảm từ khoảng **2,4 triệu xuống 1,4 triệu đồng**.
>
> Chúng em cũng so với một đối thủ mạnh hơn: thuật toán tham lam, thêm từng lô có lợi nhất. Nó đạt **7,5%**.
> Nghĩa là phần lớn lợi ích đến từ việc *tối ưu quyết định lô*. Giải chính xác như AGQO thêm 0,7 điểm khi
> tái cân bằng theo quý, và 1,3 điểm có ý nghĩa thống kê khi tái cân bằng theo tháng.
>
> Về quy tắc cá nhân: ba câu lệnh tiếng Việt, áp dụng suốt 12 quý, **0 lần vi phạm**. AGQO còn cho nhà đầu
> tư thấy **cái giá của từng quy tắc**. Loại bất động sản và giới hạn ngân hàng 30% làm sai số bám tăng
> **3,8 điểm**. Đó là thông tin mà một quỹ ETF không thể đưa ra.

## 8. Phần cứng lượng tử thực tế (8:45 – 9:30)

*[Hình A5]*

> Chúng em biên dịch mạch lên mô hình nhiễu đã hiệu chuẩn của máy **IBM Heron 156 qubit**. Mạch sâu nhất,
> tốt nhất khi không có nhiễu, cần **4.355 cổng hai qubit** và sụp về mức đoán ngẫu nhiên.
>
> Khi mục tiêu đổi thành *thành công khi có nhiễu*, cùng cơ chế dẫn dắt của AI chọn một mạch nông chỉ
> **16 cổng hai qubit**. Mạch này vẫn giữ **1,6 lần** lợi thế so với khởi động cổ điển, 11/12 quý,
> p = 0,001. Mô phỏng nhiễu đầy đủ bằng Qiskit Aer cho kết quả khớp.

## 9. Điều chúng em không tuyên bố (9:30 – 10:00)

*[Hình A8]*

> Chúng em xin nói thẳng những điều mình **không** tuyên bố, vì chúng đều nằm trên bảng đánh giá:
> - **Không có ưu thế lượng tử**: với 16 qubit, máy tính cổ điển liệt kê chính xác trong 0,12 giây.
> - Thuật toán tham lam đạt được phần lớn lợi ích.
> - Mua lô lẻ bám chỉ số tốt hơn, nếu chi phí lô lẻ đủ thấp.
> - Mô hình học lịch tham số không thắng một lịch cố định.
> - Quỹ ETF có lợi nhuận cao hơn 1,1% mỗi năm.
>
> Chúng em tin rằng một kết quả trung thực, đo đầy đủ, có giá trị hơn một tuyên bố lớn không kiểm chứng
> được.

## 10. Kết luận (10:00 – 10:30)

> Tóm lại, AGQO mang lại ba điều:
> - **Cho tài chính**: nhà đầu tư nhỏ nắm giữ "VN30 theo cách của mình" bằng lô chẵn, sai số bám giảm gần
>   một nửa, mọi quy tắc được tôn trọng tuyệt đối.
> - **Cho AI**: LLM được dùng đúng chỗ, như một trình biên dịch ngôn ngữ sang ràng buộc, luôn có kiểm tra.
> - **Cho lượng tử**: một phương pháp thiết kế mạch từ dữ liệu, kiểm chứng trên quý chưa thấy, và biết
>   tự điều chỉnh theo nhiễu phần cứng.
>
> Bước tiếp theo của chúng em: chạy mạch trên máy IBM thật, thêm lựa chọn bù lô lẻ, và mở rộng lên toàn bộ
> VN30 khoảng 60 qubit. Chúng em xin cảm ơn ban giám khảo và rất mong nhận được câu hỏi.

---

## Bản rút gọn 3 phút (khi bị giới hạn thời gian)

> Đầu tháng 10/2026, một lô VIC giá khoảng 22 triệu; một tài khoản 20 triệu muốn giữ danh mục giống VN30: bộ tối ưu nói giữ 10% VIC,
> nhưng tài khoản chỉ có thể giữ 0% hoặc 110%. Làm tròn thông thường để 90% tài khoản trong tiền mặt, sai
> số bám 12,1% một năm. ETF thì không cho nhà đầu tư loại ngành hay giới hạn ngân hàng.
>
> AGQO giải bài toán này bằng ba lớp. AI đọc thị trường và đọc câu lệnh tiếng Việt của nhà đầu tư: mô hình
> mở Qwen3.8 đúng 35/35 câu, bộ quy tắc từ khóa 68,6%. Bài toán được đưa về 16 qubit, mỗi qubit là "mua
> thêm một lô hay không". Hamiltonian chính là mục tiêu tài chính, và mọi trạng thái đều tuân thủ quy tắc
> nhà đầu tư. Mạch lượng tử được thiết kế từ dữ liệu. Trên 12 quý chưa thấy, nó lấy được nghiệm gần tối ưu
> nhiều gấp 6,9 lần khởi động cổ điển và 19 lần QAOA sách giáo khoa, 12/12 quý.
>
> Về tài chính: tài khoản 20 triệu giảm sai số bám từ 12,1% xuống 6,8%, 0 vi phạm quy tắc. Trên mô phỏng
> nhiễu IBM Heron, mạch nông do AI chọn vẫn giữ 1,6 lần lợi thế.
>
> Chúng em không tuyên bố ưu thế lượng tử, và chúng em đo cả các phương án cạnh tranh: thuật toán tham lam,
> lô lẻ, ETF. Đóng góp của chúng em là một phương pháp kiểm chứng được, trung thực, sẵn sàng mở rộng.

---

# PHẦN II. CÂU HỎI PHẢN BIỆN VÀ CÁCH TRẢ LỜI

**Nguyên tắc trả lời: thừa nhận → con số → định vị lại.**
1. Câu đầu tiên thừa nhận điểm đúng của giám khảo.
2. Đưa con số chính xác và phép kiểm định đứng sau nó.
3. Nói kết quả đó có ý nghĩa gì với điều mình *thực sự* tuyên bố.

Không tranh cãi với kết quả âm, vì chính chúng em đã đưa nó lên bảng đánh giá. Mỗi câu trả lời nên nói
dưới 30 giây.

**Câu đệm khi cần vài giây suy nghĩ:**
- "Đây đúng là điểm chúng em đã đo, xin phép trả lời bằng số liệu."
- "Câu hỏi này có hai phần, em xin trả lời phần … trước."
- Khi không biết: "Phần này chúng em chưa đo, nên em không muốn đoán. Cách chúng em sẽ kiểm tra là …"

---

## A. Năm câu khó nhất (học thuộc)

**A1. "Không có ưu thế lượng tử, vậy dùng lượng tử làm gì?"**
> Dạ đúng, và chúng em ghi rõ điều đó ngay trang đầu. Với 16 qubit, liệt kê cổ điển giải chính xác trong
> 0,12 giây. Điều chúng em khẳng định là một *phương pháp*: mạch thiết kế từ dữ liệu vượt chính điểm khởi
> đầu cổ điển của nó 6,9 lần và QAOA sách giáo khoa 19 lần, 12/12 quý chưa thấy. Khi bài toán lớn lên, liệt
> kê tăng theo 2 mũ n, mạch chỉ tăng theo n bình phương. Với toàn bộ VN30 khoảng 60 qubit, liệt kê với tốc
> độ chúng em đo được sẽ mất khoảng 10⁵ năm. Chúng em xây dựng sẵn khung so sánh trung thực cho thời điểm
> đó, và vẫn phải thắng được thuật toán ủ mô phỏng ở kích thước đó. Chúng em không nói trước là sẽ thắng.

**A2. "Thuật toán tham lam gần bằng, vậy phương pháp của các bạn thêm được gì?"**
> Dạ đúng, chính chúng em đưa thuật toán tham lam vào vì nó là đối thủ đơn giản mạnh nhất. Ở 20 triệu:
> tham lam 7,5%, AGQO 6,8%, làm tròn thông thường 12,1%. Phần lớn lợi ích đến từ việc tối ưu quyết định lô.
> Giải chính xác thêm 0,7 điểm theo quý, sát ngưỡng ý nghĩa, và 1,3 điểm theo tháng, có ý nghĩa thống kê.
> Ngoài ra AGQO bảo đảm 0 vi phạm quy tắc từ cấu trúc, biết chính xác khoảng cách tới tối ưu, và không dồn
> tiền: trong ví dụ mới nhất, thuật toán tham lam bỏ 36% tài khoản vào một mã MWG.

*Hỏi tiếp: "Nhưng tham lam lời 26%/năm, AGQO chỉ 16%?"*
> Lợi nhuận đó đến từ một khoản cược tập trung tình cờ trúng trong 12 quý, và sai số bám của nó cao hơn.
> Nhà đầu tư yêu cầu bám VN30, không yêu cầu cược vào một mã. Với 1–2 lô mỗi mã, lợi nhuận ở 20 triệu dao
> động từ 12% đến 26% chủ yếu do may rủi. Vì vậy chúng em đánh giá bằng sai số bám có khoảng tin cậy, không
> bằng lợi nhuận.

**A3. "Từ 2022 HOSE cho giao dịch lô lẻ, sao không mua lô lẻ?"**
> Chúng em đã kiểm tra: lô lẻ bám tốt hơn, sai số 2,5% so với 6,8% ở 20 triệu, và lợi nhuận cao hơn, miễn là
> chi phí thêm của phần lô lẻ dưới khoảng 6,8% ở 20 triệu, hoặc 2,6% ở 100 triệu. Điều chúng em chưa mô hình
> là rủi ro không khớp: sổ lệnh lô lẻ tách riêng, mỏng hơn, chỉ nhận lệnh giới hạn. Nên lô lẻ là phương án
> thật, và phiên bản tiếp theo sẽ thêm "lô chẵn cộng bù lô lẻ" vào thanh ghi. AGQO phù hợp khi thanh khoản lô
> lẻ kém, khi công ty chứng khoán thu phí tối thiểu mỗi lệnh, hoặc khi nhà đầu tư chỉ muốn lệnh lô chẵn.

**A4. "Mô hình AI học lịch tham số không thắng lịch cố định, vậy AI ở đâu?"**
> Dạ đúng, trên tập kiểm tra mô hình học chỉ thắng 7/12 quý, p = 0,47, và chúng em ghi là "không có lợi ích".
> AI thực sự tạo giá trị ở ba chỗ:
> - Các quy tắc thiết kế mạch đọc từ dữ liệu. Chính cấu trúc này vượt QAOA sách giáo khoa 19 lần.
> - LLM biên dịch tiếng Việt thành ràng buộc: 35/35 so với 68,6%.
> - Cơ chế dẫn dắt trở nên quyết định trên phần cứng: chọn theo thành công khi có nhiễu ra mạch 16 cổng giữ
>   1,6 lần lợi thế, trong khi lựa chọn không tính nhiễu sụp về ngẫu nhiên.

**A5. "ETF lời hơn, sao nhà đầu tư lại dùng AGQO?"**
> Với nhà đầu tư không có quy tắc riêng, ETF là lựa chọn đúng, chúng em nói rõ điều đó. E1VFVN30 lời hơn
> khoảng 1,1%/năm vì phí thấp và tái đầu tư cổ tức. AGQO dành cho người mà ETF không phục vụ: muốn loại
> ngành, giới hạn ngân hàng, giới hạn số mã, hoặc muốn trực tiếp sở hữu cổ phiếu. Với các quy tắc đó, 0 vi
> phạm, và nhà đầu tư thấy rõ giá của từng quy tắc. Ngoài ra AGQO bám *chỉ số* VN30 sát hơn *giá giao dịch*
> của ETF: 3,2% so với 5,2% theo tuần.

---

## B. Câu hỏi tài chính

**B1. Tại sao mục tiêu là sai số bám mà không phải lợi nhuận hay Sharpe?**
> Nhà đầu tư yêu cầu "VN30 theo cách của tôi". Sai số bám là lời hứa đo được: tài khoản lệch bao xa so với
> chỉ số họ muốn theo. Tối đa lợi nhuận là một khoản cược chủ động, mà 12 quý dữ liệu không đủ để chứng
> minh. Danh mục bám chỉ số có Sharpe và sụt giảm gần bằng chỉ số. Chúng em vẫn báo cáo lợi nhuận, chỉ
> không tối ưu nó.

**B2. Các bạn lấy trọng số VN30 chính thức ở đâu?**
> Chúng em không cần trọng số chính thức. Bước liên tục tối thiểu hóa phương sai của chênh lệch lợi suất
> giữa danh mục và chỉ số VN30 trên 250 phiên trước ngày quyết định. Cách này giống hồi quy theo lợi suất,
> tự phản ánh tỷ lệ tự do chuyển nhượng và trần tỷ trọng của chỉ số mà không cần biết công thức.

**B3. Có thiên lệch sống sót không?**
> Không. Chúng em dùng cả 40 mã từng thuộc VN30, với ngày vào và ra rổ theo từng kỳ review của HOSE, mỗi
> dòng có nguồn. Ví dụ NVL, PDR bị loại tháng 8/2023, POW bị loại 2/2025, vẫn có trong dữ liệu ở thời
> điểm chúng còn trong rổ.

**B4. Có nhìn trước tương lai không?**
> Không. Mỗi quyết định chỉ dùng dữ liệu trước ngày đó. Mọi hiệu chỉnh đều dùng riêng năm 2023: hệ số phạt,
> bảng 1.080 lịch, mô hình học, quyết định có tinh chỉnh hay không, mạch theo nhiễu. Kiểm tra bắt đầu từ
> 2024.

**B5. Giá điều chỉnh có làm sai chi phí lô trong quá khứ không?**
> Có, và chúng em ghi rõ. Giá được nhà cung cấp điều chỉnh hồi tố cho cổ tức cổ phiếu và chia tách, nên lợi
> suất đúng nhưng mức giá quá khứ thấp hơn thực tế. Nghĩa là lô trong quá khứ thực ra *thô hơn*, nên kết
> quả backtest đang *thận trọng* với lợi ích của AGQO. Quyết định hôm nay dùng giá thực.

**B6. Phí, thuế, trượt giá được tính thế nào?**
> Phí 0,15% mỗi chiều và thuế bán 0,1% nằm trong mục tiêu và trong mọi kiểm tra khả thi. Ở 100 triệu, phí
> 12 quý tổng cộng khoảng 0,57 triệu đồng. Kiểm tra độ bền với phí 0,10% và 0,25%, kết luận không đổi.
> Trượt giá chưa mô hình: chúng em giao dịch tại giá đóng cửa. Với lệnh vài lô cổ phiếu VN30, tác động
> giá rất nhỏ so với thanh khoản ngày.

**B7. Thanh toán T+2, biên độ ±7% thì sao?**
> Mô hình giả định mua và bán trong cùng phiên tại giá đóng cửa. Thanh toán T+2 và việc được dùng tiền bán
> chờ về hay không phụ thuộc công ty chứng khoán, chúng em chưa mô hình. Mỗi quý chỉ đổi vài lô, nên nếu
> phải bán trước, mua sau một hai phiên, sai lệch là nhỏ. Ngày chạm biên độ cũng chưa được mô hình. Chúng
> em liệt kê cả hai trong phần hạn chế.

**B8. Cổ tức tiền mặt?**
> Giá điều chỉnh của nhà cung cấp đã phản ánh cổ tức trong lợi suất, nhưng cách họ xử lý cổ tức tiền mặt
> chúng em chưa kiểm chứng độc lập. Khi so với ETF, cả hai phía đều tính phí, thuế và cổ tức.

**B9. 12 quý có quá ít không?**
> 12 là số quyết định. Nhưng sai số bám được ước lượng trên 711 phiên giao dịch giữa các quyết định, bằng
> bootstrap khối 21 ngày để giữ tự tương quan. Ở 20 triệu, khoảng tin cậy từ −6,9 đến −3,8 điểm, xa 0. Ở
> 100 triệu thì không có ý nghĩa thống kê, và chúng em nói vậy. Chúng em cũng thử tái cân bằng hàng tháng,
> nhiều quyết định hơn, kết luận giữ nguyên.

**B10. Ước lượng hiệp phương sai 250 phiên có ổn định không?**
> Ma trận được co về đường chéo 5% để ổn định. Quan trọng hơn, kết quả được đo ngoài mẫu: quyết định dùng
> ước lượng quá khứ, sai số bám đo trên giá thực sau đó. Nếu ước lượng tệ, sai số bám ngoài mẫu sẽ tệ.

**B11. Danh mục tập trung ngân hàng gần 40%, có rủi ro không?**
> Đó là cấu trúc của chính VN30, và bám chỉ số nghĩa là chấp nhận cấu trúc đó. Nếu nhà đầu tư không muốn,
> họ nói "ngân hàng tối đa 30%". AGQO tuân thủ 100% và cho biết cái giá: khoảng +3,8 điểm sai số bám khi
> kết hợp với loại bất động sản.

**B12. Thị trường sập thì AGQO bảo vệ nhà đầu tư thế nào?**
> AGQO không phải công cụ quản trị rủi ro thị trường. Nó bám VN30, nên VN30 giảm thì danh mục giảm tương
> tự. Nhà đầu tư có thể đặt quy tắc giữ tiền mặt tối thiểu, và quy tắc đó được kiểm tra chính xác trên mọi
> mẫu. Chúng em không hứa hẹn lợi nhuận hay phòng vệ.

**B13. Tại sao ở 50 triệu lợi nhuận lên tới 27%/năm, vượt xa chỉ số?**
> Dạ đó là may rủi của vài lô rơi vào mã tăng mạnh trong giai đoạn này, chúng em không tuyên bố. Sai số bám
> ở 50 triệu là 3,8%, và chúng em chỉ khẳng định điều đó. Đây cũng là lý do chúng em không dùng lợi nhuận
> làm thước đo chính.

**B14. Mô hình kinh doanh là gì? Ai trả tiền?**
> Hướng hợp lý là tích hợp vào ứng dụng của công ty chứng khoán như một tính năng "danh mục VN30 cá nhân
> hóa" cho tài khoản nhỏ. Chi phí vận hành thấp: một quyết định chạy khoảng 1 giây trên CPU, phần LLM tốn
> vài cent mỗi lần. Công ty chứng khoán có lợi từ giao dịch và giữ chân khách hàng nhỏ. Đây là định hướng,
> chúng em chưa có khách hàng thử nghiệm.

**B15. Đây có phải tư vấn đầu tư cần giấy phép không?**
> AGQO đề xuất danh sách lệnh để nhà đầu tư tự xem và tự đặt. Hệ thống không thực hiện giao dịch. Phần
> giải thích được yêu cầu không hứa lợi nhuận, không đưa lời khuyên. Nếu triển khai thật, sản phẩm nên đi
> qua một công ty chứng khoán có giấy phép, và họ chịu trách nhiệm tuân thủ.

**B16. Lợi ích 5,4 điểm sai số bám có ý nghĩa gì với người dùng?**
> Với tài khoản 20 triệu, độ lệch điển hình mỗi năm so với VN30 giảm từ khoảng ±2,4 triệu xuống ±1,4 triệu
> đồng. Nhà đầu tư nhận được đúng thứ mình yêu cầu, sát hơn gần gấp đôi.

**B17. Tần suất tái cân bằng hợp lý là bao nhiêu?**
> Mặc định theo quý. Chúng em thử hàng tháng: ở 20 triệu, lợi ích so với làm tròn thông thường vẫn khoảng
> −5,7 điểm, và lợi ích so với thuật toán tham lam trở nên có ý nghĩa (−1,3 điểm). Đổi lại, phí tăng. Đây là
> lựa chọn nhà đầu tư có thể đặt.

---

## C. Câu hỏi về dữ liệu

**C1. Dữ liệu lấy từ đâu, có hợp pháp không?**
> Dữ liệu ngày từ API biểu đồ công khai của DNSE, từ 1/2022 đến 15/11/2026: 52.686 dòng, gồm 40 mã, VN30,
> VN-Index và 3 quỹ ETF VN30. File gốc không đưa lên GitHub vì chưa có quyền phân phối lại. Ai cũng có thể
> tải lại bằng một lệnh. Có mã băm SHA-256 để xác minh.

**C2. Danh sách thành phần VN30 theo thời gian lấy ở đâu?**
> Từ các thông báo review của HOSE, mỗi dòng có đường dẫn nguồn. Chúng em dựng lại các lần thay đổi từ 2022
> đến kỳ tháng 7/2026, kể cả một lần thay đổi bất thường tháng 5/2026.

**C3. Mã mới niêm yết, thiếu lịch sử thì sao?**
> Một mã cần ít nhất 180 trong 250 phiên trước đó mới được dùng. Mã thiếu lịch sử bị loại tạm thời và được
> ghi lại.

---

## D. Câu hỏi về AI và LLM

**D1. Các bạn gọi LLM như thế nào?**
> Mô hình Qwen3.8-27B, bản FP8 chính thức, cố định theo một phiên bản cụ thể, chạy bằng vLLM 0.32 trên một
> GPU H100 của Modal. Mỗi yêu cầu gồm:
> - lời nhắc hệ thống
> - câu của nhà đầu tư
> - một lược đồ JSON
> - seed và nhiệt độ
>
> vLLM giải mã có ràng buộc theo lược đồ, nên đầu ra luôn đúng cấu trúc. Chúng em tắt chế độ suy nghĩ để
> ràng buộc áp dụng từ token đầu tiên. Mọi lời nhắc, câu trả lời và số token đều được ghi vào nhật ký. Có
> chế độ phát lại để tái tạo kết quả mà không cần GPU.

**D2. Tại sao chọn Qwen3.8 mà không phải GPT hay Claude?**
> Ba lý do:
> - **Riêng tư:** câu lệnh của nhà đầu tư là dữ liệu tài chính cá nhân, nên chạy trên hạ tầng của mình.
> - **Tái lập:** mô hình mở được cố định đúng một phiên bản.
> - **Chi phí:** mô hình 27B vừa một GPU H100.
>
> Chúng em đã cân nhắc mô hình lớn hơn như GLM-5.3, khoảng 756 GB, nhưng chi phí vượt ngân sách. Trình biên
> dịch đã đạt 35/35, nên mô hình lớn hơn không thay đổi kết quả đo được.

**D3. LLM có bịa con số không?**
> Có thể viết sai, nhưng không thể hiển thị sai. Có bốn lớp:
> - **Lược đồ:** mã và ngành chỉ được chọn trong danh sách, số có giới hạn.
> - **Kiểm tra bằng code:** câu trả lời lỗi thành ràng buộc rỗng và được đếm.
> - **Hỏi lại:** câu mơ hồ thì hỏi lại, không đoán.
> - **Kiểm tra giải thích:** mọi con số phải có trong gói bằng chứng do code tạo, mọi ghi chú giao dịch
>   phải khớp lệnh thật, và có thêm kiểm tra ý nghĩa.
>
> Khi thêm kiểm tra ý nghĩa, prompt đầu tiên trượt 0/12: số đúng, nhưng nói sai tham chiếu, ví dụ "so với lý
> tưởng" thay vì "so với VN30". Chúng em đổi tên các trường bằng chứng cho rõ nghĩa và chạy lại: số liệu
> 12/12, ý nghĩa 11/12. Trường hợp còn lại được báo cáo, không che giấu.

**D4. Nếu nhà đầu tư cố tình "tấn công" bằng câu lệnh, kiểu prompt injection?**
> Đầu ra bị khóa bởi lược đồ: chỉ có các trường loại mã, loại ngành, trần ngành, trần mỗi mã, số mã tối đa,
> tiền mặt tối thiểu, tất cả có giới hạn. Dù câu lệnh nói gì, LLM không thể tạo trọng số, lệnh giao dịch
> hay thay đổi bộ tối ưu. Tệ nhất là một ràng buộc sai, mà nhà đầu tư thấy được trước khi đặt lệnh.

**D5. Bộ test 35 câu do các bạn tự viết, có thiên lệch không?**
> Có thể, và chúng em ghi rõ. Bộ test bao phủ:
> - loại mã, loại ngành, trần ngành
> - phân số bằng chữ như "một phần ba"
> - tiếng Việt không dấu
> - số mã tối đa, tiền mặt
> - câu mơ hồ
>
> Nhưng đó không phải câu của người dùng thật. Bước tiếp theo là thu thập câu lệnh thật.

**D6. Bộ quy tắc từ khóa thua ở đâu?**
> Thua ở:
> - tiếng Việt không dấu, như "khong mua co phieu ngan hang qua 25%"
> - phân số như "một phần ba" hay "1/4"
> - tên ngành nói theo cách đời thường: năng lượng, hàng không, chứng khoán, bảo hiểm
> - các cách nói như "hạn chế bất động sản ở mức 5%"
>
> Và nó không thể hỏi lại khi câu mơ hồ.

**D7. Độ trễ và chi phí LLM?**
> - **Trình biên dịch:** 35 yêu cầu, khoảng 22.600 token vào và 3.200 token ra.
> - **Giải thích:** 12 yêu cầu sinh trong 13 giây trên GPU đã khởi động sẵn.
> - **Khởi động lạnh:** tải mô hình 31 GB mất khoảng 5 phút.
>
> Toàn bộ các lần chạy LLM của dự án tốn khoảng 1 đến 2 đô la.

**D8. Tại sao không để LLM tự thiết kế mạch lượng tử hay tự chọn cổ phiếu?**
> Chúng em đã thử cho LLM sinh mạch ở phiên bản trước và bỏ đi. Mạch sinh từ văn bản không kiểm chứng được
> trước khi chạy, và thực nghiệm không cho thấy giá trị. LLM giỏi ngôn ngữ, nên chúng em dùng nó cho ngôn
> ngữ. Phần số học giao cho thống kê, mô hình học kiểm định chéo và tối ưu chính xác.

**D9. k láng giềng gần nhất có đáng gọi là AI không?**
> Đó là học có giám sát: từ đặc trưng dữ liệu đến quyết định, siêu tham số k chọn bằng kiểm định chéo
> bỏ-một-tháng. Đây cũng là ý tưởng chuyển giao tham số đã có trong các nghiên cứu QAOA. Với 48 bài toán
> huấn luyện, mô hình nhỏ và kiểm toán được là kích thước đúng. Mạng sâu sẽ quá khớp.

**D10. Năm đặc trưng đầu vào của mô hình là gì?**
> - Độ tự tin của khởi động ấm
> - Tỷ lệ qubit gần như đã quyết định
> - Tỷ lệ độ lớn trường đơn so với liên kết
> - Mức tập trung của liên kết
> - Tỷ trọng trung bình của một lô
>
> Tất cả tính được mà không cần biết đáp án.

---

## E. Câu hỏi về bài toán lượng tử và mạch QAOA

**E1. Một qubit nghĩa là gì?**
> Qubit k bằng 1 nghĩa là mua thêm một lô của mã k so với mức sàn. 16 mã có quyết định làm tròn quan trọng
> nhất được cấp qubit, các mã khác lấy lô gần nhất. Trọng số danh mục là hàm tuyến tính của các bit.

**E2. Hamiltonian cụ thể là gì?**
> E bằng 252 nhân phương sai chênh lệch so với VN30, cộng gamma nhân bình phương thay đổi trọng số, cộng
> lambda nhân bình phương sai lệch so với mức đầu tư mục tiêu. Gamma bằng 0,002. Lambda bằng 0,01, chọn
> trên dữ liệu 2023. Đổi biến x = (1 − z)/2 cho ra trường đơn h và liên kết J để đưa vào mạch.

**E3. Tại sao 16 qubit?**
> 16 là kích thước lớn nhất mà chúng em liệt kê được đầy đủ cho mọi quyết định trong backtest: 65.536 trạng
> thái, 0,12 giây. Nhờ đó mọi khẳng định đều có đáp án đúng để so. Nghiên cứu mở rộng chạy từ 8 đến 20
> qubit.

**E4. Chọn lambda thế nào?**
> Lambda là giá trị lớn nhất trong lưới thử mà trạng thái năng lượng thấp nhất của QUBO vẫn trùng nghiệm tối
> ưu khả thi trên nhiều bài toán huấn luyện nhất. Phạt mạnh hơn giữ được nhiều xác suất trong vùng khả thi
> mà không dịch chuyển nghiệm tối ưu.

**E5. Ràng buộc tiền mặt tối thiểu không nằm trong Hamiltonian?**
> Đúng, nó được kiểm tra chính xác trên từng mẫu. Mẫu nào không đủ tiền thì không bao giờ được thực hiện.
> Nếu không mẫu nào đạt, hệ thống dùng danh mục làm tròn xuống, luôn khả thi, và đếm là một lần dự phòng.
> Trên tập kiểm tra có 0 lần dự phòng.

**E6. Khởi động ấm làm gì? Có làm QAOA thừa không?**
> Chúng em giải bài toán nới lỏng liên tục trên đoạn [0, 1] cho mỗi biến. Kết quả quyết định góc quay ban
> đầu: sin bình phương của nửa góc bằng giá trị nới lỏng. Chính trạng thái này, đo ngay mà không qua lớp
> nào, là đối thủ chính của chúng em. AGQO vượt nó 6,9 lần, nên các lớp lượng tử có giá trị thật. Thước đo
> phù hợp là xác suất một lần đo tốt hơn nghiệm làm tròn cổ điển: AGQO 40%, khởi động ấm 16%.

**E7. Mixer căn chỉnh là gì?**
> Mixer là Ry(θ) nhân Rz(−2β) nhân Ry(−θ). Trạng thái cơ bản của nó chính là trạng thái khởi động ấm. Mạch
> bắt đầu đúng ở trạng thái cơ bản của mixer, điều kiện mà lập luận đoạn nhiệt yêu cầu, theo He và cộng sự
> 2023.

**E8. Các góc được tối ưu thế nào? Có gặp "barren plateau" không?**
> Chúng em cố ý *không* tối ưu nhiều góc. Lịch tăng tuyến tính rút 2p góc xuống còn hai số, Δγ và Δβ. Mô hình
> học chọn chúng từ bảng 2023. Có thêm một bước tinh chỉnh tùy chọn 40 lần COBYLA trên CVaR. QAOA sách giáo
> khoa cần khoảng 100 lần gọi tối ưu mà vẫn kém 19 lần. Ít tham số tự do cũng là cách tránh vùng gradient
> phẳng, và giảm số lần chạy trên phần cứng.

**E9. Độ sâu p = 6 với 1.440 cổng hai qubit có quá sâu không?**
> Có, với phần cứng hiện nay. Sau khi định tuyến lên IBM Heron, mạch cần 4.355 cổng CZ. Vì vậy chúng em có
> phiên bản theo nhiễu: p = 2, chỉ giữ 25% khối lượng liên kết, 16 cổng CZ, vẫn giữ 1,6 lần lợi thế. Mạch
> sâu chỉ dùng được khi lỗi cổng hai qubit giảm khoảng 11 lần, từ 0,18% xuống 0,016%.

**E10. Mô phỏng bằng gì? Qiskit dùng ở đâu?**
> Mô phỏng vector trạng thái chính xác bằng NumPy. Qiskit 2.5 dùng để dựng mạch, biên dịch và xuất
> OpenQASM. Một bài test kiểm tra rằng mạch Qiskit cho đúng phân phối xác suất như bộ mô phỏng. Phần nhiễu
> dùng Qiskit Aer và mô hình FakeKingston.

**E11. Lấy quyết định cuối cùng từ 512 lần đo thế nào?**
> Mỗi mẫu được kiểm tra chính xác về tiền mặt, phí, thuế và giới hạn. Mẫu khả thi có mục tiêu thấp nhất được
> chọn. Trong cả 12 quý, 512 lần đo đều chứa đúng nghiệm tối ưu.

**E12. Nếu bỏ phần lượng tử thì sản phẩm vẫn chạy chứ?**
> Dạ vẫn chạy, ở 16 qubit liệt kê cổ điển cho cùng quyết định, và chúng em nói thẳng điều đó. Phần lượng
> tử là phương pháp cho thanh ghi lớn hơn, nơi không liệt kê được nữa. Ở đó chúng em đã có sẵn ba thứ: thiết
> kế mạch từ dữ liệu, lịch chuyển giao theo kích thước, và cơ chế chọn mạch theo nhiễu. Đóng góp của chúng
> em là phương pháp, không phải lời hứa tăng tốc.

**E13. Sao không dùng quantum annealing (D-Wave) hay VQE?**
> Bài toán là QUBO nên annealing lượng tử hoàn toàn phù hợp. Chúng em chọn QAOA vì chạy được trên máy cổng
> IBM và có lý thuyết rõ để thiết kế mạch từ dữ liệu: khởi động ấm, mixer căn chỉnh. Ủ mô phỏng cổ điển
> được dùng làm đối chứng. So với annealing lượng tử là hướng mở rộng tự nhiên.

---

## F. Câu hỏi về đánh giá và thống kê

**F1. "Thành công" được định nghĩa thế nào?**
> Xác suất một lần đo cho quyết định khả thi, cách tối ưu không quá 5% trên thang chuẩn hóa: 0 là tối ưu,
> 1 là một danh mục khả thi điển hình. Tối ưu và điển hình đều biết chính xác nhờ liệt kê.

**F2. Tại sao dùng Wilcoxon?**
> So sánh cặp theo từng quý, không giả định phân phối chuẩn, phù hợp với 12 cặp. Thắng 12/12 cho p = 0,0005,
> giá trị nhỏ nhất có thể. Chúng em kèm thêm khoảng bootstrap cho tỷ số trung bình.

**F3. Kiểm định nhiều lần có làm sai p-value không?**
> Ba so sánh chính đều p = 0,0005. Điều chỉnh Bonferroni cho cả 7 kiểm định mạch trên bảng vẫn còn p ≤
> 0,004. Những kết quả sát ngưỡng như thuật toán tham lam hay tài khoản 100 triệu được ghi là "không có ý
> nghĩa".

**F4. Tại sao bootstrap khối 21 ngày?**
> Lợi suất ngày có tự tương quan và cụm biến động. Lấy mẫu theo khối khoảng một tháng giao dịch giữ được
> cấu trúc đó. Bootstrap thường sẽ cho khoảng tin cậy hẹp sai.

**F5. Có tinh chỉnh trên tập kiểm tra không?**
> Không. Mọi lựa chọn cố định trên 2023. Lịch "oracle", dùng đáp án kiểm tra, chỉ đạt 25,2% so với 21,3%,
> cho thấy tinh chỉnh trên test cũng không thêm được bao nhiêu. Và lịch cố định thắng lịch học trên test,
> ngược với dấu hiệu quá khớp.

**F6. Đã so với những đối chứng nào?**
> - **Lượng tử:** đoán ngẫu nhiên, khởi động ấm, QAOA sách giáo khoa, tìm kiếm ngẫu nhiên thiết kế (3 seed),
>   lịch cố định, lịch oracle, tinh chỉnh ngược, ủ mô phỏng, liệt kê chính xác.
> - **Tài chính:** làm tròn thông thường, thuật toán tham lam, chia đều 1/N, làm tròn chính xác, QAOA sách
>   giáo khoa, lô lẻ, và 3 quỹ ETF VN30.

---

## G. Câu hỏi về phần cứng và mở rộng

**G1. Đã chạy trên máy lượng tử thật chưa?**
> Chưa, vì cần token IBM và thời gian xếp hàng. Lệnh chạy đã sẵn sàng. Thay vào đó, chúng em biên dịch lên
> FakeKingston, mô hình 156 qubit IBM Heron r2 với tỷ lệ lỗi đã hiệu chuẩn, lỗi CZ trung vị 0,18%. Chúng em
> chạy mô phỏng nhiễu đầy đủ bằng Aer trên 3 quý. Mô phỏng Aer cho 7,8%, mô hình ước lượng cho 6,6%, khá
> sát nhau.

**G2. ESP là gì? Có quá đơn giản không?**
> ESP là tích của (1 − lỗi) qua mọi cổng và phép đo, tức xác suất không có lỗi nào. Mô hình giả định khi có
> lỗi thì kết quả như ngẫu nhiên. Đó là một xấp xỉ, nên chúng em kiểm tra lại bằng mô phỏng Aer đầy đủ, và
> hai cách cho kết quả gần nhau.

**G3. Mở rộng lên lớn hơn thì sao?**
> Từ 8 đến 20 qubit, cùng một lịch 2023 không chỉnh gì vẫn vượt khởi động ấm từ 4,3 lần lên 16,7 lần:
> lợi thế *tăng* theo kích thước. Liệt kê tăng từ 0,5 mili giây lên 2,4 giây. Ủ mô phỏng vẫn gần tối ưu ở 20
> qubit, nên nó vẫn là chuẩn cổ điển phải vượt qua.

**G4. Toàn bộ VN30 cần bao nhiêu qubit?**
> Khoảng 60, nếu mỗi mã có tối đa hai lô quyết định. Mã hóa nhiều lô cho một mã chưa được cài đặt. Đó là
> bước mở rộng tiếp theo.

---

## H. Câu hỏi về sản phẩm, đạo đức, quy trình

**H1. Một quyết định mất bao lâu?**
> Khoảng 1 giây trên laptop: dựng bài toán 0,008 giây, liệt kê 65.536 trạng thái 0,12 giây, mô phỏng mạch
> và tinh chỉnh 1 giây. Toàn bộ thực nghiệm 12 quý với mọi đối chứng mất khoảng 20 phút trên 8 nhân CPU.

**H2. Làm sao biết code đúng?**
> 25 bài test tự động, gồm:
> - QUBO bằng đúng mục tiêu tài chính trên mọi trạng thái
> - mọi trạng thái của thanh ghi tuân thủ giới hạn
> - mạch Qiskit khớp bộ mô phỏng
> - kiểm tra giải thích bắt được số bịa và tham chiếu sai
> - thuật toán tham lam chỉ mua lô chẵn trong khả năng tiền mặt

**H3. Có dùng AI để viết code không?**
> Có. Chúng em dùng trợ lý lập trình AI dưới sự chỉ đạo của nhóm và ghi rõ trong báo cáo. Nhóm chọn phương
> pháp, kiểm tra kết quả và giải thích được từng thành phần. LLM của sản phẩm là Qwen3.8 mã nguồn mở, chạy
> trên tài khoản của nhóm.

**H4. Dữ liệu cá nhân của nhà đầu tư được bảo vệ thế nào?**
> LLM chạy trên mô hình mở, trong hạ tầng của nhóm. Câu lệnh không gửi cho nhà cung cấp mô hình bên thứ ba.
> Bản sản phẩm sẽ chỉ lưu mã băm của dữ liệu người dùng thay vì lưu lời nhắc đầy đủ.

**H5. Có công bằng với nhà đầu tư nhỏ không?**
> Đó chính là mục tiêu: lợi ích lớn nhất ở tài khoản nhỏ, nơi công cụ tổ chức bỏ qua. AGQO cũng minh bạch
> cái giá của từng lựa chọn để nhà đầu tư quyết định có hiểu biết.

---

# PHẦN III. SỐ LIỆU CẦN THUỘC

| chủ đề | con số |
|---|---|
| Lô VIC | khoảng 22 triệu đồng/lô ngày 1/10/2026 (110% tài khoản 20 triệu); khoảng 24 triệu giữa tháng 11 |
| Chi phí một lô ở tài khoản 100 triệu | 1,1% – 24,3% |
| Tài khoản cá nhân trong nước | hơn 14,3 triệu (cuối 10/2026, VSDC) |
| Dữ liệu | 40 mã, 1/2022 – 11/2026, 52.686 dòng; train 2023; test 12 quý, 711 phiên |
| Cấu trúc VN30 | khoảng 13 nguồn rủi ro độc lập; yếu tố thị trường khoảng 40%; khoảng 90% liên kết đến từ đồng biến động |
| LLM | Qwen3.8-27B FP8, vLLM 0.32, 1×H100; 35/35 so với 68,6%; giải thích: số liệu 12/12, ý nghĩa 11/12 (prompt đầu 0/12) |
| Bài toán | 16 qubit, 65.536 trạng thái, liệt kê 0,12 giây; λ = 0,01, γ = 0,002 |
| Huấn luyện mạch | 1.080 lịch × 48 bài toán; k = 10; CV 16,1% so với 15,7% |
| Thành công mỗi lần đo | ngẫu nhiên 0,2% · khởi động ấm 3,1% · sách giáo khoa 1,1% · tìm kiếm ngẫu nhiên 7,7% · **AGQO 21,3%** · cố định 23,8% · oracle 25,2% |
| Tỷ số | 6,9× / 19× / 2,8×; 12/12 quý; p = 0,0005 |
| Lần đo tốt hơn làm tròn | AGQO 40% · khởi động ấm 16% · sách giáo khoa 14% |
| 20 triệu | làm tròn 12,1% · tham lam 7,5% · **AGQO 6,8%** · lô lẻ 2,5%; CI −6,9 đến −3,8 |
| 100 triệu | 3,03% so với 2,96% (không có ý nghĩa); ETF lời hơn 1,1%/năm; theo tuần 3,2% so với 5,2% |
| Quy tắc | 0 vi phạm; giá: +3,8 điểm (không BĐS, NH ≤ 30%), +1,0 điểm (12 mã, 10%, 5% tiền mặt) |
| Lô lẻ hòa vốn | chi phí thêm 6,8% (20 triệu), 2,6% (100 triệu) |
| Phần cứng | mạch sâu 4.355 CZ, ESP 0,0002; mạch theo nhiễu 16 CZ, ESP 0,88, 1,6×, 11/12, p = 0,001; cần lỗi 0,016% (nay 0,18%) |
| Mở rộng | 8 → 20 qubit: 4,3× → 16,7× so với khởi động ấm; 60 qubit liệt kê khoảng 10⁵ năm |
| Ủ mô phỏng | chính xác 6/12 quý, trong 5% ở 12/12 |
| Vận hành | 1 giây/quyết định; LLM tổng khoảng 1–2 USD; 25 bài test |

---

# PHẦN IV. THUẬT NGỮ VIỆT – ANH (khi giám khảo dùng tiếng Anh)

| tiếng Việt | tiếng Anh |
|---|---|
| sai số bám | tracking error |
| lô chẵn / lô lẻ | board lot / odd lot |
| khởi động ấm | warm start |
| mixer căn chỉnh | aligned mixer |
| lịch tham số tăng tuyến tính | linear-ramp schedule (LR-QAOA) |
| chuẩn hóa theo độ lớn trung bình | RMS scaling |
| thanh ghi an toàn giới hạn | cap-safe register |
| xác suất thành công ước lượng | estimated success probability (ESP) |
| giải mã có ràng buộc | constrained / structured decoding |
| kiểm định chéo bỏ-một-tháng | leave-one-month-out cross-validation |
| bootstrap khối | moving-block bootstrap |
| ủ mô phỏng | simulated annealing |

# PHẦN V. PHÂN VAI GỢI Ý (nhóm 3 người)

- **Người 1, tài chính:** mở đầu, vấn đề, kết quả tài chính, kết luận. Trả lời nhóm câu hỏi A2, A3, A5
  và B.
- **Người 2, AI:** Pha 1, LLM, AI dẫn dắt. Trả lời A4, C và D.
- **Người 3, lượng tử:** từ tài chính sang qubit, mạch, kết quả lượng tử, phần cứng, điều không tuyên bố.
  Trả lời A1, E, F và G.

Câu hỏi về sản phẩm, đạo đức (H): người nào gần nhất trả lời. Khi một người trả lời xong, người khác chỉ
bổ sung nếu có **con số mới**, không nhắc lại.
