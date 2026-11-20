# Bảng thuật ngữ AGQO (dùng chung cho slide, báo cáo, tài liệu và prototype)

Quy ước: lời nói, tiêu đề, chú thích bằng tiếng Việt; nhãn trục, chú giải, nhãn sơ đồ và nhãn mạch trong hình bằng
tiếng Anh kỹ thuật. Thuật ngữ tiếng Anh giữ nguyên khi người trong ngành dùng nguyên; lần đầu xuất hiện thì giải thích
nó làm gì bằng tiếng Việt.

| Thuật ngữ (dùng trong hình) | Cách nói tiếng Việt | Giải thích ngắn | Không dùng |
|---|---|---|---|
| Board lot | lô chẵn (100 cổ phiếu) | Đơn vị đặt lệnh trên sổ lệnh chính của HOSE. AGQO chỉ đặt lệnh theo lô chẵn: đây là **giả định của kịch bản**, không phải lệnh cấm của thị trường | “thị trường cấm lô lẻ” |
| Odd lot | lô lẻ (1–99 cổ phiếu) | Giao dịch trên sổ lệnh lô lẻ riêng, thanh khoản mỏng hơn, có thể chênh giá | |
| Portfolio weight | tỷ trọng | Giá trị một mã chia cho giá trị tài khoản | |
| Cash after fees | tiền mặt còn lại sau phí | Tiền mặt sau khi trừ giá trị mua và phí | |
| Post-trade NAV | giá trị tài khoản sau phí | Tiền mặt sau phí + giá trị cổ phiếu vừa mua; mọi trần tỷ trọng và mức tiền mặt tối thiểu tính trên giá trị này | “vốn ban đầu” khi nói về kiểm tra quy tắc |
| Tracking error | sai số bám | Danh mục chạy lệch chỉ số VN30 bao nhiêu: độ lệch chuẩn của chênh lệch lợi suất hằng ngày giữa danh mục và VN30. Không phải lợi nhuận, không phải khoản lỗ | “rủi ro”, “mức lỗ” |
| Estimated tracking error | sai số bám ước tính | Tính trước khi giao dịch, từ hiệp phương sai 250 phiên trước ngày quyết định, cho **một** quyết định | |
| Annualized tracking error | sai số bám thực tế (năm hoá) | Đo sau khi chạy lại qua 12 quý trong quá khứ, trên chuỗi giá trị tài khoản hằng ngày, nhân √252 | |
| Nearest-lot rounding | làm tròn lô gần nhất | Làm tròn từng mã về lô gần nhất rồi bớt lô cho đủ tiền; mốc so sánh đơn giản | |
| Greedy lot filling | thuật toán tham lam (thêm từng lô) | Mỗi bước thêm một lô làm sai số bám giảm nhiều nhất, khi còn đủ tiền; mốc so sánh mạnh | |
| Exact optimum within the encoded search space | tối ưu chính xác trong không gian tìm kiếm đã mã hoá | Lựa chọn tốt nhất trong 2¹⁶ tổ hợp “thêm một lô hay không” của 16 mã được chọn; tìm bằng liệt kê toàn bộ | “tối ưu toàn cục” |
| QUBO / Ising Hamiltonian | bài toán nhị phân bậc hai / Hamiltonian | Viết mục tiêu sai số bám² + vòng quay + phạt ngân sách thành hàm của các bit | |
| QAOA | QAOA | Thuật toán lượng tử xen kẽ lớp “bài toán” và lớp “trộn” để dồn xác suất về lựa chọn tốt | |
| Warm start | khởi động ấm (warm start) | Bắt đầu mạch từ nghiệm của bài toán liên tục (cho phép mua lẻ phần lô) thay vì trạng thái đồng đều | “thí nghiệm ấm” |
| Warm-start baseline | mốc warm start | Lấy mẫu trực tiếp từ trạng thái warm start, **không có lớp mạch nào**; là mốc cổ điển | |
| Warm-start QAOA | QAOA khởi động ấm | Mạch QAOA dùng warm start làm trạng thái đầu và bộ trộn căn chỉnh tương ứng | |
| Textbook QAOA | QAOA sách giáo khoa | Trạng thái đầu đồng đều, bộ trộn X, p = 2, tối ưu COBYLA | |
| Frozen schedule | lịch cố định | Một lịch góc mạch chọn **trước** khi đánh giá (tốt nhất trung bình trên dữ liệu 2023), dùng cho mọi bài toán | |
| Schedule (linear ramp) | lịch góc (dốc tuyến tính) | Cách đặt góc γ, β qua p lớp: γ tăng dần, β giảm dần | |
| Polish | tinh chỉnh (COBYLA) | 40 bước tối ưu góc trên CVaR của năng lượng, xuất phát từ lịch đã chọn | |
| k-NN schedule selector | k-NN chọn lịch | Chọn lịch đã chạy tốt nhất trên các bài toán 2023 giống bài toán hôm nay nhất | |
| Near-optimal solution probability per shot | xác suất gần tối ưu mỗi lần đo | Xác suất một lần đo cho danh mục đủ tiền, thỏa quy tắc và có khoảng cách chuẩn hoá ≤ 5% | “tỷ lệ giao dịch thành công” |
| Normalised gap | khoảng cách chuẩn hoá | (mục tiêu − tối ưu) / (trung vị các lựa chọn khả thi − tối ưu); 0 = tối ưu, 1 = lựa chọn khả thi điển hình | |
| Shot | lần đo | Một lần chạy mạch và đọc ra một chuỗi bit | |
| Circuit evaluation | lần mô phỏng mạch | Một lần tính toàn bộ trạng thái mạch (bộ tối ưu góc cần nhiều lần) | |
| Two-qubit gates (logical / native) | cổng hai qubit (logic / sau biên dịch) | Logic: 2 × số cặp ZZ × số lớp. Native: sau khi biên dịch lên phần cứng IBM Heron | |
| ESP model | mô hình ESP | Ước tính xác suất mạch chạy không lỗi từ số cổng và tỷ lệ lỗi; không phải chạy phần cứng | |
| Aer noisy simulation | mô phỏng nhiễu Aer | Mô phỏng có mô hình nhiễu của thiết bị IBM giả lập (FakeKingston) | “chạy trên máy lượng tử” |
| Mandate / constraints | yêu cầu cá nhân / ràng buộc | Loại mã, loại ngành, trần ngành, trần mỗi mã, số mã tối đa, tiền mặt tối thiểu | |
| Interpreted / confirmed / satisfied | được hiểu / được xác nhận / được thỏa | Ba trạng thái khác nhau của một ràng buộc: AI hiểu ra; người dùng xác nhận; danh mục cuối cùng thỏa (kiểm tra trên NAV sau phí) | |
| Live / replay / keyword | trực tiếp / phát lại / từ khóa | Nguồn diễn giải: Qwen trả lời ngay; câu trả lời Qwen đã lưu; quy tắc từ khóa không dùng LLM | |
| Adjusted prices | giá đã điều chỉnh | Giá lịch sử đã điều chỉnh cổ tức và chia tách; làm chi phí lô quá khứ thấp hơn giá khớp thật | |
