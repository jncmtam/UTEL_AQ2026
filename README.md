# AGQO | Báo cáo kết quả tài chính và kỹ thuật

**AI Guide for Quantum Optimization · Nghiên cứu tối ưu danh mục cổ phiếu Việt Nam · Cập nhật: 21/10/2026**

> **Kết luận điều hành:** AGQO đã nối được mô hình ngôn ngữ với bộ tối ưu QAOA trong một quy trình có thể kiểm toán. Tuy nhiên, kết quả hiện tại **chưa chứng minh lợi thế tài chính, giá trị gia tăng của LLM hay ưu thế lượng tử**. Trong 16 kỳ danh mục, AGQO đạt CAGR ròng 18,81%, thấp hơn VN30 ở mức 24,58% và bộ chọn quy tắc ở mức 19,98%. QAOA được mô phỏng véc-tơ trạng thái trên CPU; nghiệm cổ điển chính xác vẫn là đối chứng mạnh và nhanh ở quy mô đang thử.

> **Trạng thái hiệu chỉnh dữ liệu ngày 21/10/2026:** mã nguồn đã được sửa để dùng lịch VN30 theo ngày hiệu lực, tách giá VCI điều chỉnh khỏi giá DNSE thô, và hỗ trợ siêu dữ liệu tin GDELT có mốc khả dụng. **Các con số, hình và kết luận hiệu suất bên dưới vẫn là kết quả của lượt chạy cũ trên snapshot thành phần và OHLCV cũ; chưa được tính lại bằng pipeline mới. Không dùng chúng làm bằng chứng đã loại bỏ thiên lệch.** Bộ nạp dữ liệu hiện yêu cầu xác thực miễn phí Vnstock Cộng đồng để lấy giá điều chỉnh trước 365 ngày; cho đến khi dữ liệu được tải lại, pipeline từ chối chạy kiểm định đã hiệu chỉnh.

Báo cáo trình bày luận điểm đầu tư, dữ liệu và nhận định thị trường, cách trí tuệ nhân tạo (AI) và mô hình ngôn ngữ lớn (LLM) hướng dẫn QAOA, kết quả kiểm định, các giới hạn và điều kiện cần đạt trước khi đưa ra tuyên bố mạnh hơn. Đây là nghiên cứu lịch sử, không phải khuyến nghị đầu tư.

## Tóm tắt kết quả

| Góc nhìn | Kết quả đo được | Đánh giá |
|---|---|---|
| Hiệu quả danh mục | AGQO CAGR ròng 18,81%, Sharpe 0,80, sụt giảm tối đa 11,90% | Thấp hơn VN30 và bộ chọn quy tắc trong 16 kỳ |
| Giá trị của LLM | 16/16 phản hồi hợp lệ; không có lần nào bị bộ giám sát thay thế | Chứng minh được tích hợp và tuân thủ định dạng; chưa chứng minh lợi ích tài chính |
| Chất lượng QAOA | Đã đo hối tiếc nghiệm, tỷ lệ thỏa ràng buộc, số qubit, độ sâu và số cổng logic | Có đánh đổi giữa tính khả thi và chất lượng; chưa có ưu thế so với bộ giải cổ điển |
| Tính đại diện dữ liệu của lượt chạy cũ | 37.308 dòng, 30 cổ phiếu cùng VN30 và VN-Index, 04/01/2022–19/10/2026 | Dùng snapshot hiện tại; kết quả cần tính lại bằng lịch thành phần và giá điều chỉnh |
| Kiểm định bổ sung | Một quyết định ngày 30/09, nắm giữ 12 phiên đến 19/10/2026 | Chẩn đoán bổ sung; không phải tập mù độc lập |

## 1. Hiệu quả danh mục và ý nghĩa tài chính

Kiểm định cuốn chiếu chính gồm 16 kỳ tháng, từ 02/06/2025 đến 01/10/2026, với vốn mô phỏng ban đầu 100 triệu đồng. Danh mục chịu phí giao dịch giả định 25 điểm cơ bản mỗi chiều và giới hạn khớp bằng 5% giá trị giao dịch bình quân ngày. Các chỉ số chuẩn chưa trừ chi phí đầu tư.

| Phương pháp | CAGR ròng | Biến động năm hóa | Sharpe | Sụt giảm tối đa | Giá trị cuối từ 100 triệu |
|---|---:|---:|---:|---:|---:|
| VN30 | 24,58% | 20,64% | 1,17 | -9,22% | 134,04 triệu |
| VN-Index | 23,63% | 19,05% | 1,21 | -8,64% | 132,68 triệu |
| Ledoit–Wolf, nghiệm chính xác trên toàn rổ | 49,68% | 29,31% | 1,53 | -15,92% | 171,21 triệu |
| QAOA XY vòng, p=1, 12 mã | 22,07% | 27,55% | 0,85 | -11,90% | 130,45 triệu |
| Bộ chọn quy tắc → QAOA | 19,98% | 25,39% | 0,84 | -11,90% | 127,49 triệu |
| **AGQO: Qwen → giám sát → QAOA** | **18,81%** | **25,44%** | **0,80** | **-11,90%** | **125,84 triệu** |

**Diễn giải cho nhà đầu tư**

- AGQO kém VN30 **5,77 điểm phần trăm CAGR**; vốn mô phỏng cuối kỳ thấp hơn khoảng **8,20 triệu đồng**.
- So với bộ chọn quy tắc không dùng LLM, AGQO kém **1,17 điểm phần trăm CAGR**, tương ứng khoảng **1,65 triệu đồng** giá trị cuối thấp hơn. Dữ liệu này chưa cho thấy LLM làm tăng hiệu quả danh mục.
- Sharpe 0,80 thấp hơn VN30 ở mức 1,17; mức lợi nhuận đạt được chưa bù tương xứng cho biến động đã chịu. Sụt giảm tối đa -11,90% cũng sâu hơn VN30 -9,22%.
- Khoảng tin cậy 95% của lợi nhuận chủ động năm hóa so với VN30 là [-25,00%; 13,67%] với lấy mẫu khối ba tháng và [-19,46%; 8,93%] với khối sáu tháng. Cả hai đều chứa 0; mẫu này không xác nhận lợi nhuận vượt trội.
- Ledoit–Wolf đạt kết quả cao nhất trong bảng, nhưng dùng toàn bộ rổ và có sụt giảm tối đa -15,92%. Đây là đối chứng cần giải thích, không phải bằng chứng rằng kết quả sẽ lặp lại ngoài mẫu.

CAGR là tốc độ tăng trưởng kép năm hóa; Sharpe so sánh lợi nhuận với biến động; sụt giảm tối đa đo mức giảm vốn từ đỉnh đến đáy. Các chỉ số này được tính trên mẫu ngắn 16 kỳ nên còn bất định đáng kể. Hối tiếc QAOA, được trình bày phía dưới, đo độ lệch so với nghiệm tối ưu của hàm toán học; nó không phải lợi nhuận tài chính.

![Đường vốn ròng và các chuẩn so sánh](results/final/figures/02_net_equity_curves.png)

**Đường vốn sau chi phí.** AGQO kết thúc dưới VN30, VN-Index và bộ chọn quy tắc trong giai đoạn này. Đây là bằng chứng chưa ủng hộ tuyên bố AGQO có lợi nhuận vượt trội. Nguồn: kết quả 16 kỳ trong results/final/agqo_final_walkforward.json; kỳ 06/2025–10/2026; vốn mô phỏng 100 triệu đồng.

![Lợi nhuận và rủi ro sau chi phí](results/final/figures/04_risk_return_tradeoff.png)

**Tương quan giữa lợi nhuận và rủi ro.** CAGR cao hơn của Ledoit–Wolf đi cùng mức biến động và sụt giảm lớn hơn; vì vậy không nên xếp hạng chiến lược chỉ theo lợi nhuận. Nguồn: cùng kết quả cuốn chiếu 16 kỳ; các phương pháp có thể khác quy mô tập tài sản.

### Kiểm định đuôi bổ sung: một quyết định, 12 phiên

Ngày quyết định là **30/09/2026**; danh mục vào lệnh theo giá mở cửa ngày **01/10** và được định giá tại giá mở cửa ngày **19/10**. Qwen3-8B được gọi mới trên Modal, không dùng bộ nhớ đệm. Mô hình đề xuất XY vòng p=2 và bộ giám sát chấp nhận lựa chọn đó. Dữ liệu giai đoạn này đã xuất hiện trong các phân tích trước của dự án, vì vậy đây **không phải phép thử mù**; kết quả chỉ có giá trị chẩn đoán cho một quyết định.

Các phương án danh mục cùng kế thừa sổ nắm giữ và vốn AGQO đến ngày tín hiệu rồi chỉ khác ở lần tái cân bằng này. Vì vậy, đây là phép so sánh một bước về quyết định mới, không phải nhiều lần chạy độc lập.

| Phương án | Lợi nhuận ròng 12 phiên | Phí mô phỏng |
|---|---:|---:|
| AGQO: Qwen → giám sát → QAOA | -2,649% | 425.046 đồng |
| Bộ chọn quy tắc → QAOA | -1,073% | 525.545 đồng |
| Nghiệm chính xác cổ điển, cùng hàm mục tiêu | -1,237% | 525.030 đồng |
| Bình quân sáu mã thanh khoản cao | -2,782% | 624.760 đồng |
| VN30 / VN-Index | -2,01% / -2,53% | Không áp phí đầu tư |

AGQO hơn danh mục bình quân sáu mã thanh khoản cao **0,13 điểm phần trăm** và phí thấp hơn khoảng **199.714 đồng**. Tuy nhiên, AGQO kém VN30 0,64 điểm, kém bộ chọn quy tắc 1,58 điểm và kém nghiệm chính xác cổ điển khoảng 1,41 điểm. Kết quả không chứng minh lợi thế tài chính; Sharpe năm hóa trên 12 phiên chỉ mang tính mô tả.

![Lợi nhuận ròng trong phép thử 12 phiên](results/final/figures/tail_probe_20261019/tail_net_returns.png)

**So sánh lợi nhuận đoạn cuối.** Lợi thế nhỏ so với danh mục bình quân sáu mã không bù được mức kém hơn các chuẩn còn lại. Nguồn: results/final/agqo_tail_probe_20261019.json; 01–19/10/2026; lợi nhuận danh mục đã tính phí mô phỏng.

![Đường vốn trong phép thử 12 phiên](results/final/figures/tail_probe_20261019/tail_equity_paths.png)

**Diễn biến vốn hằng ngày.** Đường danh mục phản ánh lượng khớp giả định và tiền mặt còn lại; hai chỉ số không chịu phí đầu tư. Mười hai phiên là quá ngắn để diễn giải Sharpe năm hóa như một ước lượng ổn định. Nguồn: cùng phép thử bổ sung; 01–19/10/2026.

## 2. Dữ liệu và nhận định thị trường

Lượt chạy cũ dùng **37.308 quan sát OHLCV** — giá mở cửa, cao, thấp, đóng cửa và khối lượng — của 30 cổ phiếu cùng VN30 và VN-Index, từ 04/01/2022 đến 19/10/2026. Bộ dữ liệu đó không có lịch sử thành phần theo ngày và chưa có cột giá điều chỉnh; các thống kê lịch sử bên dưới mô tả đúng bộ dữ liệu cũ, không đại diện cho lượt hiệu chỉnh đang được thiết lập.

Trong 252 phiên gần nhất của dữ liệu:

- VN30 giảm **8,60%**, VN-Index giảm **4,26%** theo giá chỉ số.
- VIC tăng **101,56%**, trong khi DGC giảm **56,67%**; kết quả giữa các cổ phiếu phân tán mạnh.
- Tương quan lợi suất BID–VCB là **0,813** và GAS–PLX là **0,809**. Các mã cùng nhóm có thể cùng chịu một nguồn rủi ro, làm giảm hiệu quả đa dạng hóa.
- Ở ngày tín hiệu 30/09/2026, biến động thực hiện 20 ngày của VN30 là **13,6%**, lợi suất VN30 20 ngày là **-3,8%**, độ phân tán chéo là **4,4%** và tương quan trung bình là **0,311**. Mô hình phụ ước lượng xác suất chế độ biến động cao **20,6%**.

**Ý nghĩa tài chính:** chỉ xếp hạng cổ phiếu theo lợi nhuận gần đây có nguy cơ tập trung vào vài mã cùng chịu rủi ro. Vì vậy bài toán tối ưu cân nhắc lợi suất kỳ vọng, hiệp phương sai và chi phí tái cân bằng. Đây là mô tả dựa trên giá hiện có; chưa thể xem là lợi suất tổng đã điều chỉnh cổ tức hay bằng chứng nhân quả.

![Diễn biến VN30 và VN-Index cùng các nhịp sụt giảm](results/final/figures/data/02_indices.png)

**Bối cảnh thị trường chung.** Chỉ số chuẩn hóa và độ sụt giảm đặt hiệu quả danh mục vào bối cảnh thị trường, đồng thời nhắc rằng chỉ số giá không thay thế chỉ số tổng lợi suất. Nguồn: dữ liệu VN30 và VNINDEX; 04/01/2022–19/10/2026.

![Xếp hạng lợi suất giữa các cổ phiếu](results/final/figures/data/04_returns_rank.png)

**Độ phân tán kết quả giữa các mã.** Khoảng cách lớn giữa mã tăng mạnh và giảm mạnh cho thấy rủi ro chọn lọc tài sản đáng kể. Đây là thống kê 252 phiên gần nhất, không đại diện cho vũ trụ đầu tư đã biết tại từng ngày lịch sử.

![Tương quan lợi suất giữa các cổ phiếu](results/final/figures/data/05_correlations.png)

**Cấu trúc tương quan.** Các cặp tương quan cao có thể cùng giảm khi một cú sốc tác động đến cả nhóm; hệ số tương quan mô tả quan hệ đồng biến, không xác lập quan hệ nhân quả. Nguồn: 252 phiên kết thúc ngày 19/10/2026.

![Lợi suất tháng theo mã cổ phiếu](results/final/figures/14_cross_section_monthly_returns.png)

**Bản đồ lợi suất chéo theo tháng.** Thang màu phân kỳ quanh mức 0 làm nổi bật cả tháng tăng lẫn tháng giảm, cùng các khoảng thiếu lịch sử. Màu được giới hạn để dễ đọc; số liệu gốc không bị thay đổi. Nguồn: giá đóng cửa tháng; 01/2022–10/2026.

![Độ phủ dữ liệu theo mã](results/final/figures/data/01_coverage.png)

**Mức độ đầy đủ của lịch sử.** VPL có 360 phiên, trong khi phần lớn mã có 1.192 phiên; thiếu dữ liệu ảnh hưởng đến số tài sản có thể xét tại từng thời điểm. Ngày không có quan sát có thể do lịch giao dịch, ngừng giao dịch hoặc thiếu nguồn cấp dữ liệu.

### Những giới hạn cần đọc cùng các nhận định

- **Thành phần chỉ số — đã sửa trong mã, chưa chạy lại kết quả.** [Lịch thành phần theo thời gian](data/vn30_snapshot_20261002/vn30_membership_history.csv) và [nhật ký rà soát](data/vn30_snapshot_20261002/vn30_membership_events.csv) bao phủ 2022–2026, neo vào [snapshot kỳ tháng 1/2026](data/vn30_snapshot_20261002/vn30_anchor_2026-02-02.csv), gồm các lần đổi mã PNJ/VIB, KDH/BCM, NVL/PDR–SHB/SSB, POW/LPB, BVH/DGC, BCM/VPL, DGC/BSR và PLX/TPB–MCH/TCX. Mỗi tín hiệu walk-forward chỉ xét thành viên có hiệu lực tại ngày đó. Lịch là bản tổng hợp các thông báo tìm được, chưa đối chiếu toàn bộ kỳ rà soát quý; các kết quả cũ vẫn bị thiên lệch thành phần cho tới khi chạy lại.
- **Giá sự kiện doanh nghiệp — đã nối nguồn và đường tính, chưa tải lại toàn kỳ.** Bộ nạp giữ OHLC thô DNSE cho giả định giá khớp và `close × volume`, đồng thời dùng OHLC VCI đã điều chỉnh để ước lượng lợi suất và đánh dấu giá trị danh mục theo tỷ lệ giá mở cửa điều chỉnh. Phí và sức chứa vẫn mô phỏng theo lệnh danh nghĩa với dữ liệu thô. Đây chưa phải sổ sự kiện doanh nghiệp: chưa đối soát từng cổ tức, chia tách, cổ phiếu thưởng, quyền mua và thời điểm ghi có; các giả định khớp không có sổ lệnh thực. Vnstock ở quyền Khách chỉ trả tối đa 365 ngày; cần đăng ký miễn phí Cộng đồng bằng `vnstock register`, kiểm tra `vnstock status`, rồi tải lại lịch sử 2022–2026. Nguồn VCI và KBS có thể điều chỉnh khác nhau; `close × volume` vẫn chỉ là đại diện thanh khoản, không phải giá trị khớp lệnh xác nhận.
- **Tin tức — bộ nạp và bộ lọc thời điểm đã có, nguồn đang giới hạn truy cập.** Tùy chọn GDELT chỉ giữ đường dẫn, mã truy vấn, dấu lần đầu được ghi nhận, giờ thu thập và mã băm; tiêu đề và nội dung bài không được lưu. Điều khoản GDELT cho phép dùng và phân phối lại dữ liệu GDELT khi ghi nguồn, còn điều khoản của nhà xuất bản vẫn áp dụng cho bài gốc. `seendate` là giờ GDELT ghi nhận nguồn lần đầu, không phải giờ đăng bài; mã được gắn theo bí danh công ty truy vấn nên chưa phải phân loại mã đã được người xác nhận. Lượt thử hiện trả HTTP 429; manifest ghi rõ nguồn tạm giới hạn, tệp bản tin chỉ có tiêu đề cột, và bộ chạy sẽ từ chối tệp có bản ghi nếu thiếu lượt thu đủ toàn bộ bí danh. Bản tin tải ngược sau ngày tín hiệu bị loại. Tin tức **chưa tham gia** các kết quả hiện có.
- **Quyền dữ liệu giá.** Tệp OHLCV đầy đủ không được theo dõi bởi Git. Giấy phép phần mềm Vnstock không cấp quyền phân phối dữ liệu từ DNSE/VCI; cần kiểm tra điều khoản từng nhà cung cấp trước khi công bố hoặc chia sẻ lại dữ liệu.

## 3. Kiến trúc AI–Quantum và vai trò của từng thành phần

AGQO không giao cho mô hình ngôn ngữ lớn (LLM) quyền chọn cổ phiếu hay tự đặt góc lượng tử. Mã phân tích tạo tín hiệu từ dữ liệu có mốc thời gian; Qwen chọn một cấu hình QAOA trong danh sách cho phép; QAOA tối ưu tập sáu cổ phiếu; bộ giám sát kiểm tra đầu ra và quy trình đánh giá tính lợi nhuận sau chi phí.

![Luồng AGQO từ dữ liệu đến kết quả tài chính](results/final/figures/12_agqo_pipeline.png)

**Quy trình AGQO.** Luồng cho thấy ranh giới dữ liệu, truy xuất ghi chú, Qwen, bộ giám sát, QAOA và đối chứng cổ điển. Nhánh GDELT là tùy chọn, cần thu thập siêu dữ liệu tại thời điểm thực; chưa có bản ghi trong lượt kết quả cũ. Mạch QAOA hiện được mô phỏng trên CPU, chưa chạy QPU.

| Chặng | Công nghệ hoặc chức năng | Vai trò |
|---|---|---|
| Dữ liệu và đặc trưng | Python, pandas, NumPy; [market_data.py](agqo/market_data.py), [insights.py](agqo/insights.py) | Làm sạch, cắt theo ngày tín hiệu; tính biến động, xu hướng, tương quan, độ rộng, phân tán và đại diện thanh khoản |
| Dự báo chế độ | LogisticRegression của scikit-learn | Ước lượng xác suất VN30 vào chế độ biến động cao trong 21 phiên; không dự báo lợi suất hay chọn cổ phiếu |
| Truy xuất tri thức | Kỹ thuật truy xuất tăng cường cho sinh nội dung (RAG) trong [knowledge.py](agqo/knowledge.py) | Cung cấp bảy ghi chú về chỉ số, dữ liệu, hàm mục tiêu, QAOA, đối chứng và giới hạn |
| Hướng dẫn bộ tối ưu | Qwen/Qwen3-8B, NF4 4-bit, Transformers trên Modal | Đọc payload và đề xuất một chính sách từ danh sách cho phép |
| Giám sát | Bộ kiểm tra JSON và quy tắc trong [guide.py](agqo/guide.py) | Từ chối cấu hình ngoài danh sách, kiểm tra dữ kiện; tạo đường dự phòng |
| Tối ưu lượng tử | QAOA véc-tơ trạng thái NumPy trong [simulator.py](agqo/simulator.py) | Lấy mẫu nghiệm nhị phân dưới ràng buộc chọn đúng K mã |
| Đánh giá | [evaluation.py](agqo/evaluation.py), [walkforward.py](agqo/walkforward.py) | Đối chiếu nghiệm, tính phí, lợi nhuận, rủi ro, tính khả thi và chất lượng nghiệm |

### Thiết kế Qwen và kiểm soát đầu ra

Qwen3-8B dùng prompt **tiếng Anh phiên bản 9**. Prompt quy định ngày cắt dữ liệu, cách hiểu các thước đo, giới hạn bằng chứng, các chính sách có thể chọn và đầu ra JSON có cấu trúc. Thiết kế giả định mô hình có thể thiếu kiến thức tài chính chuyên sâu: số liệu và định nghĩa chuẩn được tính hoặc truy xuất từ tài liệu dự án, còn các phát biểu về kết quả được dựng từ dữ liệu đã kiểm chứng.

Trong 16 quyết định chính, Qwen tạo 16 phản hồi hợp lệ, không cần sửa định dạng và không bị bộ giám sát thay thế; tổng cộng 127.783 token đầu vào và 849 token đầu ra. Qwen chọn chính sách XY vòng p=1 bảy lần, XY vòng p=2 chín lần. Sự tuân thủ này xác nhận hợp đồng đầu ra hoạt động, nhưng chưa cho thấy mô hình lựa chọn tốt hơn quy tắc.

### Mô hình phụ chưa có kỹ năng dự báo dương

LogisticRegression được dùng để ước lượng chế độ biến động, không phải dự báo hướng giá. Điểm Brier của mô hình là **0,237**, kém mức nền **0,217**; kỹ năng Brier là **-9,32%**. Điểm Brier càng thấp càng tốt, nên mô hình phụ hiện chưa cải thiện dự báo nền. Hệ thống xem đây là tín hiệu yếu và không cho phép nó tự ý tăng rủi ro hoặc độ sâu mạch.

![Kiểm toán lựa chọn của Qwen và cấu hình được chạy](results/final/figures/11_agqo_decision_audit.png)

**Kiểm toán quyết định LLM.** Hình đối chiếu chính sách Qwen đề xuất với chính sách được bộ giám sát thực thi. Đầu ra hợp lệ cho thấy hoạt động kỹ thuật, không chứng minh lợi ích đầu tư; các quyết định thuộc 16 tín hiệu từ 05/2025 đến 08/2026.

## 4. Bài toán tài chính và thiết kế QAOA

Mỗi qubit biểu diễn một mã trong tập ứng viên. Biến nhị phân xᵢ bằng 1 khi mã i được chọn. Bài toán chọn đúng K=6 mã trong N ứng viên và tối thiểu hóa bằng thuật toán tối ưu gần đúng lượng tử có tham số (QAOA):

$$
\min_{x_i\in\{0,1\},\;\sum_i x_i=K}
\quad
\frac{\lambda}{K^2}x^T\Sigma_\alpha x
-
\frac{1}{K}\mu^Tx
+
C_{\text{tái cân bằng}}(x)
$$

Trong đó μ là lợi suất kỳ vọng ước lượng từ quá khứ; Σ là hiệp phương sai lợi suất; Σα=(1−α)Σ+α diag(Σ) là ma trận hiệp phương sai co rút; λ điều chỉnh mức đánh đổi giữa rủi ro và lợi suất; C tái cân bằng mô phỏng chi phí đổi danh mục. Ràng buộc tổng xᵢ=K bảo đảm danh mục chọn đúng sáu mã.

Qwen chỉ chọn chính sách đã định nghĩa trước, gồm số qubit, hệ số λ, mức co rút α, bộ trộn, bố trí kết nối, độ sâu p và số lần lấy mẫu. QAOA mới là bộ giải bài toán chọn mã; bộ giải cổ điển được chạy song song để đo hối tiếc và kiểm tra liệu QAOA có cần thiết hay không.

### Kết quả so sánh thiết kế QAOA

Đã thử 14 chính sách với 8, 12 và 16 qubit, K=6; thay đổi bộ trộn X/XY, độ sâu p=1/2 và cấu trúc kết nối. Cấu hình dùng 1.024 lượt lấy mẫu, COBYLA tối đa 100 lần đánh giá cho mỗi lần khởi tạo và ba lần khởi tạo cố định. Bảng dưới đây tổng hợp bốn thiết kế đại diện trên 16 bài toán của đợt đánh giá chính.

| Cấu hình | Số bài regret ≤5% | Hối tiếc mục tiêu trung bình | Mẫu đúng K | Cổng hai qubit logic |
|---|---:|---:|---:|---:|
| X, p=1 | 16/16 | 0,28% | 40,81% | 66 |
| XY vòng, p=1 | 0/16 | 20,04% | 100,00% | 90 |
| XY vòng, p=2 | 4/16 | 13,85% | 100,00% | 180 |
| XY theo tương quan, p=2 | 13/16 | 2,53% | 100,00% | 240 |

Bộ trộn X p=1 có hối tiếc thấp và ít cổng hơn, nhưng chỉ 40,81% mẫu thỏa đúng K=6. Bộ trộn XY giữ đúng số mã trong mọi mẫu ở cấu hình đã thử, nhưng XY vòng p=1 có hối tiếc cao. XY theo tương quan p=2 giảm hối tiếc trung bình xuống 2,53%, đổi lại cần khoảng 240 cổng logic hai qubit. Không có thiết kế nào tốt nhất đồng thời trên mọi tiêu chí.

Hối tiếc là khoảng cách giữa nghiệm QAOA và nghiệm vét cạn trên **cùng hàm mục tiêu**, đã chuẩn hóa theo miền giá trị khả thi. Hối tiếc thấp chỉ cho thấy bộ giải bám sát mô hình toán học; không khẳng định danh mục có lợi nhuận cao. Số cổng là ước lượng logic của mô phỏng, chưa tính biên dịch phần cứng hoặc nhiễu.

![Bố trí cổng và các bộ trộn QAOA](results/final/figures/09_qaoa_gate_and_mixer_design.png)

**Cấu trúc mạch QAOA.** Hình minh họa cách hàm mục tiêu được mã hóa vào cổng và cách bộ trộn X/XY di chuyển giữa nghiệm; đây là sơ đồ phương pháp, không phải một lần chạy phần cứng.

![Hối tiếc so với chi phí cổng logic](results/final/figures/10_qaoa_quality_vs_gate_cost.png)

**Chất lượng nghiệm và tài nguyên mạch.** Tăng số cổng hoặc độ sâu không tự động làm hối tiếc giảm; cần chọn cấu hình theo đường đánh đổi chất lượng–tài nguyên thay vì chỉ tăng p.

![Mạch QAOA đã chạy ở các bối cảnh thị trường](results/final/figures/15_actual_qaoa_circuit_comparison.png)

**Mạch từ các lần chạy đã lưu.** Ba trường hợp thể hiện ánh xạ mã–qubit, góc tối ưu, cạnh của hàm chi phí, bộ trộn, số lượt lấy mẫu và nghiệm được lấy mẫu; các mạch là mô phỏng logic, chưa được biên dịch hoặc đo trên QPU.

### Phép thử đuôi cho thấy thêm điều gì về mạch?

Trong phép thử ngày 30/09/2026, Qwen chọn XY vòng p=2: hối tiếc mục tiêu **10,64%**, tỷ lệ mẫu đúng K **100%**, 180 cổng hai qubit logic và lợi nhuận ròng -2,649%. Nghiệm vét cạn trên cùng hàm mục tiêu đạt lợi nhuận -1,237%. Với X p=1, hối tiếc là 0% và có 66 cổng, nhưng chỉ 25,10% mẫu tốt nhất thỏa K. XY đường thẳng p=2 có hối tiếc 2,17%, đúng K 100%, 176 cổng và lợi nhuận -1,073%. Kết quả cho thấy bộ trộn có thể cải thiện tính khả thi, nhưng chính sách LLM chọn không đạt nghiệm gần nhất hay lợi nhuận cao nhất trong phép thử này.

![Đánh đổi giữa cổng và hối tiếc trong các cấu hình](results/final/figures/tail_probe_20261019/tail_circuit_regret.png)

**Đối chiếu kiến trúc trên tín hiệu cuối.** Thêm qubit hoặc lớp mạch không bảo đảm nghiệm tốt hơn; hình phân biệt tính khả thi, hối tiếc mục tiêu và số cổng. Đây là bộ mô phỏng cổ điển, không phải ưu thế lượng tử.

| Cấu hình | Qubit | Bộ trộn / độ sâu | Cổng hai qubit logic | Hối tiếc | Tỷ lệ khả thi ở lần khởi tạo tốt nhất | Lợi nhuận ròng |
|---|---:|---|---:|---:|---:|---:|
| XY vòng, p=1, 8 qubit | 8 | XY / 1 | 44 | 8,04% | 100% | -3,05% |
| X, p=1, 12 qubit | 12 | X / 1 | 66 | 0,00% | 25,10% | -1,24% |
| XY vòng, p=1, 12 qubit | 12 | XY / 1 | 90 | 11,91% | 100% | -1,96% |
| XY đường thẳng, p=2, 12 qubit | 12 | XY / 2 | 176 | 2,17% | 100% | -1,07% |
| XY vòng, p=2, 12 qubit — lựa chọn của Qwen | 12 | XY / 2 | 180 | 10,64% | 100% | -2,65% |
| XY vòng, p=2, 16 qubit | 16 | XY / 2 | 304 | 3,18% | 100% | -4,06% |

Các mức lợi nhuận trong bảng là kết quả của đúng phép thử một quyết định; không dùng để xếp hạng chiến lược dài hạn. Tỷ lệ khả thi là xác suất lấy được nghiệm đúng K ở lần khởi tạo tốt nhất trong ba lần đã chạy.

### Quy mô hiện tại chưa tạo nhu cầu cho QAOA

Với 12 ứng viên và chọn 6 mã chỉ có **924** tổ hợp khả thi. Với 30 ứng viên, có **593.775** tổ hợp; nghiệm cổ điển chính xác đã duyệt không gian này trong khoảng **5,76 giây** trên môi trường nghiên cứu. Do đó, hiện chưa có căn cứ nói QAOA nhanh hơn hoặc cần thiết hơn. Bằng chứng thuyết phục tiếp theo cần xác định vùng quy mô mà QAOA cải thiện chất lượng, thời gian hoặc chi phí so với các bộ giải cổ điển mạnh trên cùng bài toán.

## 5. Tuyên bố nào được dữ liệu hỗ trợ?

| Tuyên bố | Trạng thái bằng chứng | Cách diễn đạt có thể bảo vệ |
|---|---|---|
| AGQO tích hợp AI để hướng dẫn bộ tối ưu lượng tử | Đã thể hiện qua 16 quyết định hợp lệ và quy trình có giám sát | “Quy trình lai chạy được và truy vết được từ tín hiệu đến danh mục.” |
| LLM tăng lợi nhuận danh mục | Chưa được chứng minh; AGQO kém bộ quy tắc và VN30 | “Cần kiểm định đối chứng ngoài mẫu để định lượng đóng góp của LLM.” |
| QAOA giải bài toán có ràng buộc | Đã đo mẫu thỏa ràng buộc, hối tiếc và số cổng ở nhiều thiết kế | “Đã lượng hóa đánh đổi thiết kế của mô phỏng QAOA.” |
| QAOA vượt bộ giải cổ điển | Chưa được chứng minh; nghiệm chính xác nhanh ở quy mô hiện tại | “Chưa có lợi thế về chất lượng, tốc độ hoặc chi phí.” |
| Dự án đạt ưu thế lượng tử | Chưa có QPU hoặc đo nhiễu phần cứng | “Đây là nghiên cứu thuật toán lượng tử mô phỏng, chưa phải ưu thế lượng tử.” |

Điểm mạnh hiện tại là thiết kế có đối chứng, lưu được quyết định và công khai kết quả bất lợi. Giá trị nghiên cứu không nằm ở lời hứa tạo tiền, mà ở việc đã xác định được các khoảng trống định lượng cần lấp để kiểm chứng luận điểm AI Guide for Quantum Optimization.

## 6. Rủi ro và điều kiện để nâng cấp kết luận

| Ưu tiên | Việc cần hoàn tất | Bằng chứng cần thu được |
|---|---|---|
| Dữ liệu không thiên lệch | Dùng lịch thành phần có ngày hiệu lực, gồm mã rời chỉ số; xác nhận giá điều chỉnh cổ tức, chia tách và quyền mua | Lợi suất tái lập được mà không dùng thông tin thành phần tương lai |
| Phép thử ngoài mẫu | Khóa giai đoạn tương lai chưa được xem, đăng ký trước chính sách chọn mô hình và chỉ mở kết quả sau khi đóng băng mã | Lợi nhuận chủ động, Sharpe và sụt giảm với khoảng bất định; hiệu chỉnh thử nhiều cấu hình |
| Giá trị tăng thêm của AI | So với chính sách cố định, bộ quy tắc, lựa chọn ngẫu nhiên có kiểm soát và phiên bản bỏ RAG trên cùng dữ liệu | Cải thiện một chỉ số đã đăng ký trước, lặp lại trên giai đoạn độc lập |
| Năng lực dự báo | So điểm Brier, điểm mất mát logarit và hiệu chỉnh xác suất theo thời gian với mức nền và mô hình đơn giản | Kỹ năng dự báo chế độ dương và ổn định |
| Khả năng cạnh tranh của QAOA | Mở rộng tập ứng viên, tăng số lần khởi tạo; so với vét cạn, tham lam, tôi luyện mô phỏng và bộ giải cổ điển mạnh | Đường đánh đổi chất lượng–thời gian–cổng–tính khả thi cho thấy vùng có lợi thế |
| Khả năng chạy phần cứng | Biên dịch mạch, đo độ sâu, nhiễu, số lượt đo, thời gian và chi phí trên thiết bị mục tiêu | Kết quả QPU lặp lại được so với cùng ngân sách cổ điển |
| Khả năng giao dịch | Thêm thuế, chênh lệch giá mua-bán, trượt giá, lô giao dịch và khớp lệnh theo thời điểm | Lợi nhuận ròng còn tồn tại sau ma sát thị trường thực |

Chỉ gọi AGQO có lợi thế đầu tư nếu chiến lược vượt chuẩn sau mọi chi phí trên giai đoạn ngoài mẫu mới, với bất định và mức sụt giảm được báo cáo. Chỉ gọi QAOA có lợi thế kỹ thuật nếu chất lượng, thời gian hoặc chi phí tốt hơn bộ giải cổ điển trên cùng quy mô và điều kiện.

## 7. Dữ liệu, phần mềm và tái lập

### Nguồn dữ liệu và quyền sử dụng

Mã tải dữ liệu mới dùng Vnstock 5.1.0 để lấy OHLC đã điều chỉnh từ VCI và gọi DNSE chart API để lưu giá thô. Cài bằng `python -m pip install -r requirements-data.txt`, sau đó đăng ký miễn phí quyền Cộng đồng bằng `vnstock register`; kiểm tra quyền bằng `vnstock status`. Quyền Khách bị giới hạn một năm lịch sử và không đủ để tạo lại tập 2022–2026.

Trước khi tải lại, chạy `python scripts/build_vn30_membership_history.py`, rồi `python scripts/download_vn30_dataset.py`. Tệp giá nằm trong máy nghiên cứu và không được theo dõi bởi Git. Kê khai nguồn, dấu băm và trạng thái điều chỉnh nằm trong [manifest dữ liệu](data/vn30_snapshot_20261002/manifest.json); lịch thành phần nằm trong [lịch hiệu lực](data/vn30_snapshot_20261002/vn30_membership_history.csv). Vnstock là công cụ kết nối, không phải nhà cung cấp dữ liệu; giấy phép phần mềm không mặc nhiên cấp quyền phân phối dữ liệu thị trường. [Điều khoản sử dụng Vnstock](https://www.vnstocks.com/onboard/giay-phep-su-dung).

Để thu thập tin gần đây theo thời gian thực, dùng `python scripts/fetch_gdelt_news_metadata.py --days 30`. Cần truy vấn đủ mọi bí danh; `--ticker FPT` chỉ dành cho chẩn đoán và không được bộ chạy chấp nhận làm nguồn toàn danh mục. Chỉ truyền `--news data/news/gdelt_metadata.csv` cho `scripts/run_ai_qaoa_walkforward.py` khi manifest có `status=collected_metadata_only`, `complete_universe_query=true` và `news_context_available=true`. Bộ thu thập chờ tối thiểu năm giây giữa các truy vấn, không lưu tiêu đề hay toàn văn. [Điều khoản dữ liệu GDELT](https://www.gdeltproject.org/about.html).

HOSE áp dụng phiên bản 4.0 của phương pháp chỉ số từ kỳ rà soát tháng 07/2025; tài liệu nêu giới hạn tỷ trọng ngành 40%. Đây là bối cảnh về cấu tạo chỉ số, không phải tín hiệu dự báo. [Thông cáo HOSE tháng 07/2025](https://staticfile.hsx.vn/Uploads/UploadDocuments/2391309/TCBC_%20Cai%20tien%20chi%20so%20VN30%20t7.2025.pdf).

### Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Phân tích và dữ liệu | Python 3.12, pandas, NumPy, SciPy |
| Mô hình phụ | scikit-learn LogisticRegression |
| LLM | Qwen3-8B, Transformers, bitsandbytes NF4, triển khai trên Modal |
| Tối ưu QAOA | Mô phỏng véc-tơ trạng thái NumPy trên CPU; COBYLA để tối ưu góc |
| Hình ảnh | Matplotlib |
| Phần cứng lượng tử | Không có kết quả QPU trong báo cáo; Qiskit/Aer và IBM Quantum chỉ là tùy chọn |

Không cần khóa API OpenAI. Việc chạy Qwen trên Modal có thể phát sinh chi phí GPU.

### Hồ sơ kết quả

- [Báo cáo cuốn chiếu chi tiết](results/final/BAO_CAO_AGQO_CUOI_CUNG.md)
- [Kết quả cuốn chiếu dạng JSON](results/final/agqo_final_walkforward.json)
- [Báo cáo phép thử đuôi 12 phiên](results/final/AGQO_KIEM_DINH_DUOI_20261019.md)
- [Dữ liệu phép thử đuôi dạng JSON](results/final/agqo_tail_probe_20261019.json)
- [Tóm tắt dữ liệu và nhận định](results/final/dataset_summary.json)
- [16 quyết định Qwen đã kiểm tra](results/final/qwen3_decisions.json)
- [Tài liệu kỹ thuật AGQO](TAI_LIEU_KY_THUAT_AGQO.md)
- [Sổ tay Qwen3 trên Modal](notebooks/AGQO_Qwen3_Modal.ipynb)
- [Kế hoạch nghiên cứu vòng tiếp theo](AGQO_NEXT_ROUND_MASTER_PROMPT.md)

### Chạy lại

Sao chép tệp mẫu config/modal-qwen3.env.example thành config/modal-qwen3.env. Điền các giá trị cần thay đổi trong tệp này và xác thực tài khoản bằng lệnh modal setup; không lưu mã thông báo bí mật vào tệp. Sau khi chuẩn bị môi trường Python, có thể triển khai mô hình và chạy lại quy trình:

    cp config/modal-qwen3.env.example config/modal-qwen3.env
    source .venv/bin/activate
    set -a
    source config/modal-qwen3.env
    set +a
    modal deploy modal_qwen3_agqo.py
    python scripts/check_modal_qwen3.py
    python scripts/run_ai_qaoa_walkforward.py --llm-guide modal-qwen3

Phép thử đuôi được chạy bằng python scripts/run_tail_probe.py. Tệp kết quả ghi lại cấu hình, phản hồi mô hình, chính sách được dùng, nghiệm đối chứng, phí, lợi nhuận và siêu dữ liệu mạch.
