# Tài liệu kỹ thuật AGQO

**Phiên bản:** quy trình AI–QAOA ngoài mẫu trên VN30.
**Kết quả chạy gần nhất:** [báo cáo tài chính và kỹ thuật](results/BAO_CAO_AI_QAOA_WALK_FORWARD.md).
**Mục đích:** giải thích dữ liệu, mô hình, hàm mục tiêu, thiết kế QAOA, mô phỏng giao dịch, chỉ số đánh giá và đường tái lập từ đầu đến cuối.

## 1. Kiến trúc

~~~text
OHLCV đã lưu
  → kiểm tra cột, OHLC, mã trùng và lịch dữ liệu
  → tạo chuỗi lợi suất VN30 và đặc trưng thị trường đến ngày t
  → hồi quy logistic dự báo biến động 21 phiên tương lai
  → xác suất AI cùng insight định lượng
  → [AGQO tùy chọn] LLM chọn chính sách QAOA từ kết quả các chính sách đã khép
  → ước lượng μ, Σ từ 252 phiên trước ngày tín hiệu
  → chọn 6 mã bằng nghiệm chính xác hoặc QAOA trên 12 mã thanh khoản cao
  → [AGQO] chạy QAOA theo chính sách được chọn và 12 đối chứng chính sách cố định
  → giao dịch mô phỏng tại giá mở cửa phiên kế tiếp
  → trừ phí, giới hạn lệnh theo ADTV và tính lợi nhuận ròng
  → so với VN30, VN-Index, rủi ro cố định và Ledoit–Wolf
  → ghi JSON, báo cáo, biểu đồ và khoảng tin cậy
~~~

Mô-đun chính của quy trình mới là agqo/walkforward.py. Mạch QAOA mô phỏng ở agqo/simulator.py; hàm mục tiêu, QUBO và bộ giải chính xác ở agqo/problem.py. Mã dựng biểu đồ, báo cáo và lệnh chạy nằm ở agqo/walkforward_plots.py, agqo/walkforward_report.py và scripts/run_ai_qaoa_walkforward.py.

## 2. Công nghệ và vai trò

| Thành phần | Công nghệ | Vai trò trong kết quả |
|---|---|---|
| Ngôn ngữ | Python 3.12 | Điều phối xử lý dữ liệu, ước lượng, bộ giải và báo cáo |
| Bảng dữ liệu | pandas 3.0.6 | Căn ngày, pivot OHLCV, lợi suất và lịch tái cân bằng |
| Tính toán | NumPy 2.5.4 | Ma trận hiệp phương sai, liệt kê tổ hợp, véc-tơ trạng thái và lấy mẫu |
| Mô hình AI | scikit-learn 1.9.1 | StandardScaler, LogisticRegression và Ledoit–Wolf |
| Tối ưu góc | SciPy 1.18.1 | COBYLA tối ưu góc β, γ của QAOA |
| Biểu đồ | Matplotlib 3.11.2 | Bảy biểu đồ cơ sở; thêm biểu đồ so AGQO với 12 chính sách nếu bật LLM; chín biểu đồ khám phá dữ liệu |
| Mạch lượng tử tùy chọn | Qiskit 2.5.2, Aer 0.17.2 | Biên dịch/đối chiếu mạch cục bộ; không tạo các kết quả đã báo cáo |
| Thiết bị tùy chọn | IBM Quantum Runtime 0.50.0 | Lớp gửi mạch phần cứng nếu có tài khoản và ngân sách; chưa được gọi |
| Kiểm thử kho mã | pytest 9.1.1 | Có trong môi trường; bộ kiểm thử không được chạy trong lượt này |
| Mô hình ngôn ngữ tùy chọn | GPT-5 mini qua OpenAI Responses API | Đọc insight quá khứ, chọn mã trong danh mục cấu hình QAOA; kết quả đã lưu hiện chưa gọi mô hình |
| Phục vụ mô hình | Modal | Chạy hàm hướng dẫn và cấp khóa API bằng bí mật Modal |

Đường cơ sở đã lưu chỉ dùng hồi quy logistic; không gọi mô hình ngôn ngữ, không dùng tin tức và không gửi công việc tới thiết bị lượng tử. Đường AGQO bổ sung một LLM làm bộ điều khiển cho QAOA, song song với mô hình logistic. LLM không dự báo giá hay chọn mã trực tiếp; nó chỉ chọn cấu hình trong danh mục đã định nghĩa. Khi chạy AGQO, kết quả cuối cùng phải được xác nhận từ lần chạy thực tế; mã mới không làm thay đổi số liệu đường cơ sở đã lưu.

## 3. Dữ liệu và quy tắc làm sạch

### 3.1. Nguồn và phạm vi

- Tệp dữ liệu cục bộ: data/vn30_snapshot_20261002/ohlcv_daily.csv.
- Kích thước: 37.308 dòng, gồm 30 cổ phiếu và hai chỉ số VN30/VN-Index.
- Thời gian: 04/01/2022–19/10/2026.
- Nguồn bộ lấy: thư viện vnstock-data, mã nguồn ghim trong manifest.
- Đầu cuối giá: DNSE chart API.
- Danh sách thành phần: HODL.VN, ảnh chụp 02/10/2026; không phải lịch thành phần theo ngày hiệu lực của HOSE.
- Độ phủ chưa đều: VPL bắt đầu 13/05/2025; các mã khác có thể có phiên trống.
- Quyền dữ liệu thị trường chưa được xác nhận; OHLCV thô không được đưa vào Git.

Tệp kê khai, ngày tải, mã băm và độ phủ từng mã: data/vn30_snapshot_20261002/manifest.json.

### 3.2. Kiểm tra và căn lịch

load_market_dataset xác nhận cột OHLCV, giá dương, số hữu hạn, khối lượng không âm, mã-ngày không lặp, đủ hai chỉ số và đủ 30 mã trong danh sách.

walkforward._load_panels:

1. Pivot giá mở cửa/đóng cửa và khối lượng theo ngày, mã.
2. Tạo lịch chỉ số chỉ gồm phiên có cả VN30 và VN-Index.
3. Căn dữ liệu cổ phiếu lên cùng lịch chỉ số.
4. Tính lợi suất đóng cửa với fill_method=None; không nội suy giá.
5. Tính giá trị giao dịch ước tính bằng giá đóng cửa nhân khối lượng.

Trong dữ liệu nguồn có một phiên thiếu giá chỉ số. Nếu giữ phiên thiếu trong chuỗi rồi dùng cửa sổ lăn 120 phiên, các đặc trưng sẽ thiếu liên tục qua nhiều tháng. Mã hiện loại phiên không có cả hai chỉ số trước khi tính lợi suất; chuyển động giữa hai quan sát giá vẫn được ghi nhận tại quan sát tiếp theo. Không điền giá giả.

### 3.3. Thiên lệch còn lại

Danh sách VN30 hiện tại được áp ngược lịch sử, nên các mã đã rời chỉ số hoặc bị loại khỏi ảnh chụp không xuất hiện trong tập ứng viên. Đây là thiên lệch sống sót. Giá là OHLCV thô; chưa xác nhận điều chỉnh cổ tức, chia tách, quyền mua hoặc các hành động doanh nghiệp. Mọi lợi suất cổ phiếu vì vậy chỉ mang tính khám phá, không phải kiểm định đầu tư đáng tin.

## 4. Mô hình AI dự báo chế độ biến động

### 4.1. Đặc trưng và nhãn

_index_features chỉ dùng lợi suất chỉ số VN30 đến hết ngày t; không lấy lợi suất các thành phần VN30 làm đầu vào AI. Sáu đặc trưng:

- Độ biến động lịch sử năm hóa trên 20, 60 và 120 phiên.
- Lợi suất lũy kế 20 và 60 phiên.
- Tỷ số độ biến động 20 phiên trên 120 phiên.

forward_volatility tạo nhãn:

~~~text
y(t) = 1 nếu độ lệch chuẩn năm hóa của r(t+1),...,r(t+21)
       lớn hơn phân vị 70% được tính trên tập huấn luyện ban đầu
       0 nếu không
~~~

Nhãn chỉ dùng lợi suất tương lai để chấm sau này. Khi khớp tại ngày tín hiệu t, chỉ nhãn có toàn bộ 21 phiên tương lai trước hoặc bằng t mới được dùng.

### 4.2. Chia tập và chọn mô hình

| Tập | Ngày | Quy tắc |
|---|---|---|
| Huấn luyện ban đầu | đến 31/10/2024 | Tính ngưỡng phân vị, chuẩn hóa đặc trưng và huấn luyện |
| Xác nhận | 01/11/2024–30/04/2025 | Chọn C trong {0,01; 0,1; 1; 10} theo log-loss |
| Kiểm tra dự báo | từ 01/05/2025 | Khóa C/ngưỡng; chỉ mở rộng mẫu bằng nhãn trưởng thành |
| Tín hiệu danh mục | cuối tháng 05/2025–08/2026 | Chọn danh mục ngoài mẫu; giao dịch phiên kế tiếp |

fit_regime_model chặn 21 phiên cuối của mỗi giai đoạn để nhãn không tràn qua ranh giới. StandardScaler chỉ khớp trên tập huấn luyện. C=10 thắng tập xác nhận với log-loss 0,502 trên 99 dự báo; các giá trị C khác có log-loss 0,538; 0,598 và 0,558. Ngưỡng biến động được chốt là 21,95% năm hóa.

fit_regime_model_as_of khớp lại bộ phân loại tại mỗi ngày kiểm tra bằng toàn bộ mẫu đã trưởng thành tới ngày đó. C và ngưỡng không được điều chỉnh lại bằng dữ liệu kiểm tra.

### 4.3. Điều khiển danh mục

regime_controls ánh xạ xác suất p:

~~~text
λ(p) = 2 + 8p
α(p) = 0,10 + 0,60p
~~~

λ kiểm soát mức phạt phương sai. α co ma trận hiệp phương sai về đường chéo, giảm mức phụ thuộc vào tương quan mẫu. Các đối chứng tách tác động:

- Rủi ro cố định: λ=5, α=0,40.
- AI chỉ λ: λ thay đổi, α=0,40.
- AI chỉ α: λ=5, α thay đổi.
- AI cả hai: λ và α cùng thay đổi.

### 4.4. Chất lượng dự báo đo được

Trên 345 dự báo ngày ngoài mẫu, Brier=0,257 và log-loss=0,748, kém dự báo tỷ lệ nền mở rộng (Brier=0,225; log-loss=0,643). Kỹ năng Brier tương đối là -14,3%. Trên 16 tín hiệu tháng, Brier=0,237 so với 0,217 nền, kỹ năng -9,3%. Các nhãn ngày cách nhau một phiên nhưng nhìn 21 phiên tương lai nên chồng lấn; số dự báo ngày không phải số mẫu độc lập.

Kết luận kỹ thuật: mô hình đã chạy đúng quy tắc thời gian nhưng chưa tạo giá trị dự báo ngoài mẫu so với tỷ lệ nền. Không dùng kết quả lợi nhuận danh mục để tuyên bố AI dự báo đúng chế độ.

### 4.5. Mô hình ngôn ngữ điều khiển QAOA trong AGQO

#### Vai trò

LLM là một bộ chọn tham số có ràng buộc. Nó không thay thế hồi quy logistic, ước lượng tài chính hay bộ giải QAOA. Logistic cung cấp xác suất chế độ; phần xử lý xác định insight; LLM đọc bối cảnh đến ngày tín hiệu và chọn một mã chính sách; bộ tối ưu QAOA chạy cấu hình đó để chọn danh mục. Nghiệm chính xác, các QAOA cố định và Ledoit–Wolf tiếp tục làm đối chứng.

#### Đầu vào được gửi

Payload định lượng được dựng trong `agqo.walkforward._build_agqo_payload` và gồm:

- Ngày tín hiệu và quy tắc cắt dữ liệu tại ngày đó.
- Xác suất biến động cao từ logistic; biến động VN30 20/60/120 phiên; lợi suất 20/60 phiên; tỷ số biến động 20/120.
- Số mã đủ điều kiện, số ứng viên; tương quan cặp trung bình và phân vị 90%; độ phân tán lợi suất 20 phiên; tỷ lệ mã tăng; tỷ lệ ngân hàng.
- Thanh khoản đại diện của 12 ứng viên, tính bằng giá đóng cửa nhân khối lượng bình quân 20 phiên.
- Kết quả tài chính ròng đã khép của từng chính sách cố định và các đối chứng: số kỳ, CAGR, Sharpe, Sortino, sụt giảm, VaR/CVaR tháng, hệ số lợi nhuận, tỷ lệ tháng dương, doanh số và phí.
- Danh mục hữu hạn 12 chính sách, cùng mục tiêu lựa chọn.

Không gửi OHLCV thô, lịch sử từng cây nến, tên mã hay lợi nhuận của kỳ đang quyết định. Lợi nhuận kỳ t chỉ được tính sau ngày thoát; khi chọn kỳ t+1, kết quả này mới xuất hiện trong ngữ cảnh. Tín hiệu đầu tiên chưa có đối chứng chính sách đã khép, do đó quyết định mở đầu dựa vào insight thị trường và quy tắc trong lời nhắc.

#### Danh mục chính sách QAOA

Mỗi cấu hình chọn mức ngại rủi ro λ, tỷ lệ co rút α, bộ trộn, độ sâu p và số mẫu. Số lần tối ưu mỗi seed và danh sách seed tiếp tục theo `ResearchConfig`: mặc định tối đa 50 lần đánh giá và ba seed 11, 23, 47.

| Mã chính sách | λ | α | Bộ trộn | p | Số mẫu mỗi lần đánh giá |
|---|---:|---:|---|---:|---:|
| balanced_x_p1 | 5 | 0,40 | X | 1 | 512 |
| balanced_x_p2 | 5 | 0,40 | X | 2 | 512 |
| balanced_xy_p1 | 5 | 0,40 | XY | 1 | 512 |
| balanced_x_p2_1024 | 5 | 0,40 | X | 2 | 1024 |
| defensive_x_p1 | 8 | 0,70 | X | 1 | 512 |
| defensive_x_p2 | 8 | 0,70 | X | 2 | 512 |
| defensive_xy_p1 | 8 | 0,70 | XY | 1 | 512 |
| diversified_x_p1 | 5 | 0,70 | X | 1 | 512 |
| diversified_x_p2 | 5 | 0,70 | X | 2 | 512 |
| growth_x_p1 | 2 | 0,10 | X | 1 | 512 |
| growth_x_p2 | 2 | 0,10 | X | 2 | 512 |
| diversified_xy_p1 | 5 | 0,70 | XY | 1 | 512 |

#### Đầu ra và thực thi

`agqo.guide.decision_json_schema` yêu cầu đầu ra JSON có `policy_id`, các mã insight, lý do, ghi chú rủi ro và mức tin cậy tự khai. `validate_guidance` xác nhận mã chính sách và mã insight, miền tin cậy, kiểu dữ liệu và độ dài văn bản. Các tham số được lấy lại từ đối tượng chính sách cục bộ; lời giải thích của LLM không được chạy như mã.

Với mỗi chính sách, AGQO tối ưu hàm mục tiêu có tính phí đổi danh mục ước lượng:

~~~text
J_AGQO(x) = λ(xᵀΣαx)/K² − (μᵀx)/K
            + 12 × (phí mỗi chiều / 10.000) × Σᵢ |xᵢ/K − wᵢ_trước|
~~~

`w_trước` là tỷ trọng mục tiêu của chính sách cố định ở kỳ trước, hoặc danh mục AGQO thích nghi ở kỳ trước. Kỳ đầu bắt đầu bằng tiền mặt. Hạng phí dùng cùng thang năm hóa với μ, Σ; sổ giao dịch sau đó vẫn mô phỏng phí thực tế từng lệnh và giới hạn ADTV. Đường cơ sở cũ không bị thay đổi và tiếp tục dùng mục tiêu rủi ro/lợi nhuận không có hạng phí trực tiếp.

`modal_agqo.py` khai báo ứng dụng `agqo-llm-guide` và hàm `guide_qaoa_policy` trên Modal. Hàm gọi GPT-5 mini bằng OpenAI Responses API với đầu ra JSON theo lược đồ chặt, ghi mã mô hình, mã phản hồi và số token; khóa `OPENAI_API_KEY` được lấy từ bí mật Modal `agqo-openai`. Tùy chọn `store=False` tránh lưu nội dung phản hồi phía API. Hàm chỉ cần CPU và không nạp bộ dữ liệu thị trường.

`CachedGuide` lưu quyết định theo mã băm SHA-256 của nội dung tín hiệu, tên ứng dụng/hàm, tên mô hình và phiên bản lời nhắc; dữ liệu được ghi vào tệp tạm rồi thay thế nguyên tử. Việc này hỗ trợ kiểm toán, tránh gọi lại API khi chạy lại đúng đầu vào và giữ lại số token của phản hồi. Tệp lưu đệm mặc định là `results/agqo_llm_decisions.json` và bị loại khỏi Git. Đổi insight, lịch sử chính sách hoặc danh mục sẽ tạo khóa mới; khi chỉnh lời nhắc, cần tăng `PROMPT_CACHE_VERSION` trong `agqo/guide.py`.

Trong từng tín hiệu, walk-forward chạy QAOA cho cả 12 chính sách ở chế độ bóng. Chỉ danh mục theo chính sách LLM chọn được ghi vào dòng lợi nhuận AGQO thích nghi; từng chính sách còn lại tạo một đường đối chứng cố định. Khi tín hiệu kế tiếp đến, LLM nhận các kết quả đã đóng của cả 12 đường đối chứng. Mỗi đường được so với nghiệm chính xác của cùng hàm mục tiêu riêng, không so điểm mục tiêu của hai λ/α khác nhau với nhau. Sau khi chọn chính sách, AGQO còn chạy cấu hình đó trên mục tiêu có trọng số danh mục AGQO kỳ trước; vì vậy nghiệm động có thể khác đường cố định cùng mã chính sách.

#### Giới hạn đánh giá

Đây là điều khiển tuần tự dựa trên lợi nhuận quá khứ đã đóng, không phải một tập kiểm tra cuối cùng không bị chạm. Dù không rò rỉ lợi nhuận kỳ hiện tại hoặc tương lai, các quyết định sau có thích nghi từ kết quả của các kỳ đầu trong cùng cửa sổ; khoảng tin cậy của hiệu quả tổng thể vì vậy không thể được diễn giải như thử nghiệm hoàn toàn độc lập. Thêm một tập thời gian khóa riêng, sau khi cố định lời nhắc, danh mục và mô hình, trước khi tuyên bố khả năng khái quát.

Mức tin cậy là trường do LLM tự khai, không được hiệu chỉnh xác suất và không dùng làm thước đo hiệu quả. Hiệu quả tài chính và chất lượng QAOA được báo cáo thành hai nhóm riêng. Không tuyên bố LLM tạo lợi nhuận nếu AGQO không vượt các chính sách cố định, phương pháp AI hiện có và đối chuẩn theo tiêu chí đăng ký trước.

## 5. Hàm mục tiêu và bài toán chọn cổ phiếu

### 5.1. Đầu vào tài chính

Tại mỗi tín hiệu cuối tháng, mã đủ điều kiện phải có ít nhất 126 quan sát trong tối đa 252 phiên gần nhất. Ma trận ước lượng sử dụng các ngày lợi suất đầy đủ đồng thời cho toàn bộ mã trong vũ trụ tại tín hiệu.

estimate_annual_inputs tính:

~~~text
μ = trung bình lợi suất ngày × 252
Σ = hiệp phương sai ngày × 252
~~~

Với co rút đường chéo:

~~~text
Σα = (1−α)Σ + α diag(diag(Σ))
~~~

Danh mục chọn đúng K=6 mã và chia tỷ trọng đều 1/6. Hàm mục tiêu QUBO chính không nhúng chi phí giao dịch:

~~~text
min J(x) = λ(xᵀΣαx)/K² − (μᵀx)/K
s.t. xᵢ ∈ {0,1}; Σᵢxᵢ = K
~~~

Chi phí được đo trong lớp thực thi lệnh. Cách tách này giúp mọi nghiệm QAOA và nghiệm chính xác tối ưu cùng một hàm mục tiêu tài chính.

### 5.2. Vũ trụ và cách giảm kích thước cho QAOA

- Nghiệm chính xác cổ điển chạy trên toàn bộ 29–30 mã đủ điều kiện, tùy thời điểm VPL đủ lịch sử.
- QAOA không chạy trên đủ 30 mã. Mỗi tín hiệu chọn trước 12 mã đủ điều kiện có giá trị giao dịch ước tính bình quân 20 phiên cao nhất.
- Bên trong 12 mã, QAOA chọn K=6. Có C(12,6)=924 trạng thái khả thi.
- Cách lọc thanh khoản là bước tiền xử lý cổ điển; kết quả QAOA chỉ tối ưu trong tập 12 mã đã lọc, không thể so trực tiếp nghiệm đó với nghiệm tối ưu toàn rổ.

## 6. QUBO, Ising và QAOA

### 6.1. QUBO

Với xᵢ là biến có/không chọn mã:

~~~text
Q(x) = λ/K² · ΣᵢΣⱼ Σαᵢⱼ xᵢxⱼ − 1/K · Σᵢ μᵢxᵢ
~~~

build_qubo đưa hạng chéo hiệp phương sai vào hệ số tương tác cặp. Với bộ trộn X, mã thêm hạng phạt:

~~~text
P(Σᵢxᵢ − K)²
~~~

P được đặt lớn hơn khoảng dao động của mục tiêu trên các trạng thái khả thi để mẫu sai số lượng mã không thắng. Bộ trộn XY bảo toàn tổng số bit 1 nên không cần hạng phạt cardinality.

to_ising đổi biến theo x=(1−Z)/2, bao gồm trường Z, tương tác ZZ và phần hằng. Trong lượt kiểm tra, mục tiêu tài chính trước hết được kiểm tra lại bằng PortfolioProblem.score; các nghiệm khả thi được so theo điểm gốc.

### 6.2. Mã hóa và cấu trúc mạch

- 12 mã ứng viên tương ứng 12 qubit; mỗi qubit mang biến chọn một cổ phiếu.
- K=6; bộ duyệt chuẩn kiểm tra đủ 924 tổ hợp.
- 2¹²=4.096 trạng thái cơ sở trong mô phỏng véc-tơ trạng thái.
- Ma trận hiệp phương sai dày tạo 12×11/2=66 tương tác cặp trong mỗi lớp cost. p=2 có hai lớp cost; số gate vật lý sau biên dịch còn phụ thuộc kiến trúc và cách tách cổng.
- X: khởi tạo chồng chập đều; cost dùng pha QUBO; mixer áp dụng RX trên từng qubit. Ràng buộc K chỉ được giữ bằng hạng phạt và lọc mẫu.
- XY: khởi tạo một chuỗi K-bit khả thi; mixer áp dụng trao đổi lân cận trên vòng bằng tích Trotter; số bit 1 luôn bảo toàn.

XY hiện bắt đầu từ một trạng thái cơ sở khả thi, không phải chồng chập đều trên 924 danh mục. Đây là lựa chọn thuật toán cần cân nhắc khi phát triển tiếp.

### 6.3. Bộ tối ưu và tiêu chí kỹ thuật

optimize_qaoa mô phỏng QAOA bằng NumPy trên CPU, tối ưu các góc β,γ bằng COBYLA. Mỗi lần chấm lấy mẫu hữu hạn 512 trạng thái; tối đa 50 lần đánh giá mỗi seed. Mỗi cấu hình có ba seed 11, 23, 47; từ ba kết quả, giữ danh mục khả thi có điểm QUBO tốt nhất. Cả ba cấu hình được chạy lại ở từng tín hiệu tháng.

Độ lệch chuẩn hóa dùng để so các bài toán có thang điểm khác nhau:

~~~text
regret = (điểm QAOA tốt nhất − điểm tối ưu chính xác)
         / (điểm lớn nhất − điểm nhỏ nhất trên 924 tổ hợp khả thi)
~~~

Ngưỡng kỹ thuật đã dùng trong báo cáo là regret ≤5%:

| Bộ trộn / độ sâu | Kỳ đạt / 16 | Sai lệch trung bình | Seed tối ưu có mẫu khả thi | Xác suất khả thi TB của seed được chọn |
|---|---:|---:|---:|---:|
| X, p=1 | 15 | 0,82% | 48/48 | 55,70% |
| X, p=2 | 16 | 0,49% | 48/48 | 75,38% |
| XY, p=1 | 1 | 20,20% | 48/48 | 100,00% |

p=2 X là lựa chọn có chất lượng mục tiêu mạnh nhất trong lượt chạy. Đổi lại, thời gian mô phỏng tổng 48 lượt tăng từ khoảng 0,91 lên 1,96 giây. XY đạt khả thi chắc chắn nhưng điểm mục tiêu kém xa nghiệm chính xác.

### 6.4. QAOA thực sự và phần chưa chạy

Kết quả trong JSON được tạo bằng bộ mô phỏng véc-tơ trạng thái NumPy; Qiskit/Aer không được dùng để tạo những số liệu này và không có lượt chạy IBM QPU. Vì vậy:

- Có bằng chứng rằng ánh xạ bài toán sang QUBO và quá trình tối ưu góc hoạt động trên 12 qubit mô phỏng.
- Chưa có bằng chứng về mạch đã biên dịch, độ sâu vật lý, nhiễu thiết bị, thời gian QPU hay ưu thế lượng tử.
- “12 qubit” là số biến được mô phỏng, không có nghĩa 12 qubit vật lý đã chạy.
- Trên N=12, nghiệm chính xác cổ điển hoàn tất 16 bài toán trong khoảng 0,0036 giây; QAOA p=1 cần khoảng 0,91 giây cho 48 lượt mô phỏng.
- Bộ chính xác véc-tơ hóa giải 593.775 tổ hợp N=30,K=6; năm cấu hình nghiệm toàn rổ trong 16 tín hiệu mất khoảng 5,11 giây tổng.

Không tuyên bố QAOA nhanh hơn, rẻ hơn hay kiếm tiền tốt hơn ở quy mô hiện tại.

## 7. Mô phỏng thực thi và chỉ số tài chính

### 7.1. Quy tắc nắm giữ và giao dịch

- Tín hiệu được tính sau giá đóng cửa phiên cuối tháng.
- Giao dịch tại giá mở cửa phiên chỉ số tiếp theo.
- Nắm giữ đến giá mở cửa kỳ tái cân bằng kế tiếp.
- Vốn khởi đầu: 100.000.000 đồng.
- Phí cơ sở: 25 điểm cơ bản trên cả mua và bán; độ nhạy 10/25/50 điểm cơ bản.
- Giới hạn lệnh: 5% ADTV; độ nhạy 1/5/10%.
- Bán trước để giải phóng tiền, sau đó mua; lệnh vượt giới hạn thanh khoản được khớp một phần. Mọi tài sản đang nắm giữ phải có giá mở cửa đầu/cuối kỳ.
- Giá trị giao dịch ước tính từ giá đóng cửa × khối lượng trong 20 phiên trước tín hiệu.

Đây là mô hình thực thi giản lược: chưa có giá trị khớp lệnh chính thức, bảng lệnh, trượt giá, thuế, bước giá, lô chẵn hay lãi tiền mặt. Với vốn 100 triệu, lệnh lớn nhất là khoảng 0,037% ADTV trên chiến lược toàn rổ và khoảng 0,012% trên QAOA X, thấp hơn ngưỡng 1%; giới hạn ADTV không ràng buộc trong mẫu.

### 7.2. Đối chứng và chỉ số

Đối chứng gồm:

1. Rủi ro cố định λ=5, α=0,40, nghiệm chính xác toàn rổ.
2. AI chỉ điều chỉnh λ.
3. AI chỉ điều chỉnh α.
4. AI điều chỉnh λ và α.
5. Hiệp phương sai Ledoit–Wolf với λ=5.
6. Nghiệm chính xác AI trên cùng 12 mã lọc thanh khoản.
7. QAOA X p=1, X p=2, XY p=1 trên cùng 12 mã.
8. VN30 và VN-Index theo cùng ngày mở cửa vào/ra.

`summarize_monthly_returns` tính các thước đo trên lợi nhuận ròng theo tháng: CAGR ghép lãi; lợi nhuận số học năm hóa; biến động năm hóa; Sharpe năm hóa với lãi suất phi rủi ro bằng 0; Sortino dùng độ lệch chuẩn phần lợi nhuận dưới lãi suất phi rủi ro; sụt giảm tối đa; Calmar = CAGR / trị tuyệt đối của sụt giảm tối đa; VaR tháng 95% là phân vị 5% lợi nhuận; CVaR tháng 95% là lợi nhuận trung bình trong phần đuôi dưới VaR; hệ số lợi nhuận = tổng tháng lãi / trị tuyệt đối tổng tháng lỗ; tỷ lệ tháng dương và giá trị cuối kỳ. Với chuỗi không có lỗ hoặc không có mức giảm vốn, Calmar/hệ số lợi nhuận có thể không xác định và được lưu là `null`.

`compare_monthly_returns` ghép lợi nhuận từng kỳ với VN30 hoặc VN-Index. `paired_block_bootstrap_mean_ci` lấy mẫu khối tròn 10.000 lần, độ dài khối 3 và 6 tháng, để giữ một phần phụ thuộc theo thời gian. Các khoảng này vẫn có bất định lớn với 16 kỳ và không khắc phục được việc AGQO thích nghi từ những kỳ đã đóng trước đó.

Khoảng tin cậy không sửa được thiên lệch sống sót, dữ liệu giá thô, việc thử nhiều cấu hình hoặc số kỳ nhỏ. Cần diễn giải như kiểm tra thăm dò.

### 7.3. Kết quả tài chính có thể nói

- AI λ+α toàn rổ: CAGR ròng 44,60%, Sharpe 1,47, sụt giảm tối đa -15,93%, giá trị cuối 163,52 triệu đồng.
- Đối chứng Ledoit–Wolf: CAGR 49,68%, Sharpe 1,53; cao hơn cấu hình AI trong cửa sổ.
- VN30: CAGR 24,58%, Sharpe 1,17, sụt giảm -9,22%.
- QAOA X p=1: CAGR 16,24%, Sharpe 0,65, dưới VN30. Khoảng lấy mẫu khối lợi nhuận vượt của QAOA so với VN30 cắt qua 0.
- QAOA XY p=1 có CAGR 24,70% trong mẫu nhưng sai lệch mục tiêu trung bình 20,20%, doanh số hai chiều 98,84% và phí 5,23 triệu. Kết quả ngắn hạn này không chứng minh chất lượng tối ưu hay hiệu quả ổn định.
- Tỷ trọng ngân hàng chiếm trung bình 45,8% của AI toàn rổ, 55,2% của QAOA X p=1 và 58,3% của QAOA X p=2. VIC xuất hiện ở 16/16 kỳ của AI toàn rổ.

## 8. Tệp, hàm và đầu ra

### 8.1. Mô hình và ước lượng

| Tệp / hàm | Chức năng |
|---|---|
| agqo/ai.py · build_daily_features | Bộ đặc trưng tổng quát có thành phần cổ phiếu; không dùng trong walk-forward mới |
| agqo/ai.py · _index_features | Sáu đặc trưng chỉ số được dùng thật trong quy trình mới |
| agqo/ai.py · forward_volatility | Tạo nhãn biến động tương lai và giữ thiếu nhãn chưa trưởng thành |
| agqo/ai.py · fit_regime_model | Chọn C trên tập xác nhận có purge thời gian |
| agqo/ai.py · fit_regime_model_as_of | Khớp lại tại ngày tín hiệu bằng nhãn đã trưởng thành |
| agqo/ai.py · regime_controls | Ánh xạ xác suất sang λ, α |
| agqo/estimators.py · estimate_annual_inputs | Tính μ, Σ năm hóa |
| agqo/estimators.py · build_regime_problem | Mục tiêu với điều khiển chế độ và các ablation |
| agqo/estimators.py · build_ledoit_wolf_problem | Chuẩn hiệp phương sai Ledoit–Wolf |

### 8.2. Bài toán và bộ giải

| Tệp / hàm | Chức năng |
|---|---|
| agqo/problem.py · PortfolioProblem | Mã, μ, Σ, K, λ, tỷ trọng cũ, phí và cách tính điểm |
| agqo/problem.py · build_qubo / to_ising | Ánh xạ bài toán sang QUBO và Ising |
| agqo/problem.py · exact_solve | Duyệt tổ hợp chuẩn chậm hơn nhưng đơn giản |
| agqo/problem.py · exact_solve_vectorized | Duyệt chính xác theo ma trận tổ hợp được lưu đệm; dùng trong walk-forward |
| agqo/problem.py · greedy_solve / anneal_solve | Đối chứng cổ điển tham lam và tôi luyện |
| agqo/simulator.py · statevector | Áp lớp pha cost và bộ trộn trên véc-tơ trạng thái |
| agqo/simulator.py · _mix_x / _mix_xy_ring | Bộ trộn X và XY vòng |
| agqo/simulator.py · optimize_qaoa | Lấy mẫu, tối ưu COBYLA, trả điểm tốt nhất khả thi |

### 8.3. Đánh giá và kết xuất

| Tệp / hàm | Chức năng |
|---|---|
| agqo/walkforward.py · run_walkforward | Chạy chia tập, tín hiệu tháng, bộ giải, thực thi, benchmark và JSON |
| agqo/walkforward.py · _capacity_ledger | Sổ tiền mặt/cổ phiếu, phí, lệnh khớp một phần và ADTV |
| agqo/evaluation.py · summarize_monthly_returns | CAGR, lợi nhuận năm hóa, biến động, Sharpe, Sortino, Calmar, VaR/CVaR, hệ số lợi nhuận, tháng dương, sụt giảm |
| agqo/evaluation.py · compare_monthly_returns | Chênh lệch đối chuẩn và khoảng tin cậy |
| agqo/walkforward_plots.py · build_walkforward_plots | Tạo bảy biểu đồ cơ sở và biểu đồ chính sách AGQO khi bật |
| agqo/walkforward_report.py · write_walkforward_report | Dựng báo cáo tiếng Việt |
| agqo/guide.py · policy_catalog / validate_guidance | Lấy danh mục chính sách và kiểm tra đầu ra LLM |
| agqo/guide.py · CachedGuide / ModalGuide | Lưu đệm theo đầu vào, kiểm toán quyết định và gọi hàm Modal đã triển khai |
| modal_agqo.py · guide_qaoa_policy | Gọi GPT-5 mini bằng đầu ra JSON có cấu trúc; không nhận OHLCV thô |
| scripts/run_ai_qaoa_walkforward.py | Lệnh chạy trọn quy trình |

Đầu ra đã lưu:

- results/vn30_ai_qaoa_walkforward.json: mọi cấu hình, xác suất, danh mục theo tháng, lợi nhuận từng kỳ, phí, đối chuẩn, khoảng tin cậy và từng seed QAOA.
- results/BAO_CAO_AI_QAOA_WALK_FORWARD.md: báo cáo phân tích.
- results/figures/walkforward/: bảy biểu đồ đường cơ sở; thêm 08_agqo_policy_comparison.png khi bật LLM.
- results/figures/vn30/: bảy biểu đồ khám phá dữ liệu giá thô 252 phiên; phần tóm tắt insight nằm trong README.

## 9. Tái lập

Yêu cầu tệp OHLCV cục bộ có trong manifest. Từ thư mục gốc dự án:

~~~bash
python scripts/run_ai_qaoa_walkforward.py
~~~

Đường cơ sở giữ nguyên, không gọi mô hình ngôn ngữ. Để chạy AGQO, cần có quyền sử dụng Modal và khóa OpenAI:

~~~bash
python -m pip install -e '.[llm-modal]'
modal setup
modal secret create agqo-openai OPENAI_API_KEY=YOUR_OPENAI_API_KEY
AGQO_MODAL_SECRET_NAME=agqo-openai modal deploy modal_agqo.py
python scripts/run_ai_qaoa_walkforward.py --llm-guide modal
~~~

Mặc định là `gpt-5-mini`; có thể đặt `AGQO_LLM_MODEL` trước lệnh chạy cục bộ để chọn mô hình tương thích. Tên mô hình được gửi rõ cho Modal và nằm trong không gian khóa bộ nhớ đệm. Mỗi tín hiệu chưa có bộ nhớ đệm gọi Modal một lần; các lượt chạy lại cùng payload dùng lại kết quả cũ. Khi bật AGQO, mỗi tín hiệu chạy QAOA cho cả 12 chính sách để tạo đường đối chứng bóng; chi phí và thời gian tính toán cao hơn đáng kể so với đường cơ sở.

Lệnh dựng lại JSON, bảy biểu đồ đường cơ sở (thêm biểu đồ số 8 khi AGQO bật) và báo cáo. Thiết lập mặc định trong ResearchConfig:

- Huấn luyện đến 31/10/2024; xác nhận đến 30/04/2025; kiểm tra dự báo từ 01/05/2025.
- Tín hiệu danh mục cuối tháng đến 31/08/2026; kỳ thoát cuối 01/10/2026.
- Chân trời nhãn 21 phiên; cửa sổ tài chính 252 phiên; tối thiểu 126 quan sát; K=6, 12 qubit QAOA.
- Vốn 100 triệu đồng; phí 25 điểm cơ bản; giới hạn ADTV 5%.
- p=1 X, p=2 X và p=1 XY; 512 mẫu, 50 lần đánh giá, ba seed.

Không chạy bộ kiểm thử tự động trong lượt này. Đã kiểm tra cú pháp mô-đun, so khớp nghiệm véc-tơ hóa với bộ duyệt cũ trên một bài toán tổng hợp N=12,K=6, chạy thử một kỳ để kiểm tra đường xuất, rồi chạy đủ 16 kỳ và dựng lại biểu đồ/báo cáo.

## 10. Hướng phát triển và tiêu chí đạt

| Hạng mục | Tiêu chí đề xuất trước khi công bố kết luận |
|---|---|
| Dữ liệu | Giá điều chỉnh; thành phần VN30 theo ngày hiệu lực; ghi rõ nguồn/quyền dữ liệu |
| Dự báo AI | Brier và log-loss thắng tỷ lệ nền trong nhiều cửa sổ cuốn chiếu; kiểm tra hiệu chỉnh |
| Kinh tế | Lợi nhuận ròng sau phí/thuế/trượt giá vượt đối chuẩn; kiểm soát giảm vốn, turnover, ngành và sức chứa |
| QAOA | Sai lệch mục tiêu, tỷ lệ khả thi, độ lặp lại, thời gian và số cổng báo đủ seed |
| Ưu thế lượng tử | So sánh cùng bài toán và chất lượng với solver cổ điển hiện đại; chạy QPU và công bố lỗi, độ sâu, thời gian, shot |
| Tính khái quát | Có giai đoạn kiểm tra cuối giữ kín, tiêu chí đăng ký trước và không chọn theo kết quả tốt nhất hậu nghiệm |

Ở quy mô hiện tại, hướng có căn cứ nhất là dùng Ledoit–Wolf và nghiệm chính xác làm chuẩn tài chính; dùng QAOA X p=2 như nhánh nghiên cứu thuật toán có thể đo; giữ mô hình AI ở trạng thái cần cải thiện thay vì khẳng định nó tạo lợi nhuận.
