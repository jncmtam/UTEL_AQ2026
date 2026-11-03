# Tài liệu kỹ thuật AGQO

## 1. Mục tiêu hệ thống

AGQO (AI Guide for Quantum Optimization) dùng AI để đọc tín hiệu và bằng chứng tài chính đã quan sát, sau đó hướng dẫn lựa chọn cấu hình QAOA. QAOA giải bài toán chọn danh mục; bộ giám sát độc lập quyết định đề xuất nào đủ bằng chứng để thực thi. Các cách giải cổ điển và cấu hình lượng tử cố định vẫn chạy làm đối chứng.

Luồng xử lý:

```text
OHLCV cục bộ
  ├─ LogisticRegression: xác suất chế độ biến động cao
  ├─ Bộ phân tích dữ liệu: xu hướng, tương quan, độ rộng, thanh khoản
  ├─ Bảng kết quả các chính sách đã thoát lệnh
  └─ RAG cục bộ: công thức, định nghĩa, giới hạn và nguyên tắc benchmark
          ↓ payload có mốc thời gian, bằng chứng và mã tham chiếu
Qwen3-8B trên Modal → đề xuất policy_id
          ↓ xác thực schema + allow-list
Bộ giám sát theo số liệu quá khứ → policy thực thi
          ↓
QAOA mô phỏng véc-tơ trạng thái → nghiệm chính xác / greedy / annealing đối chiếu
          ↓
Sổ giao dịch sau phí, giới hạn ADTV, Sharpe, Sortino, drawdown, CVaR
```

LLM không chọn mã cổ phiếu, không tự viết mạch, không tự đặt λ/α/p/qubit/shots và không thay thế bộ giải QAOA.

## 2. Dữ liệu và cách xử lý

### Lịch thành phần theo ngày hiệu lực

`data/vn30_snapshot_20261002/vn30_anchor_2026-02-02.csv` lưu snapshot gốc bất biến. `scripts/build_vn30_membership_history.py` đảo ngược các lần thay đổi đã ghi nhận để dựng mốc đầu 2022, sau đó áp dụng thay đổi tiến về trước và tạo:

- `vn30_membership_history.csv`: các khoảng `valid_from`–`valid_to`, luôn phải có đúng 30 mã tại từng mốc.
- `vn30_membership_events.csv`: ngày thông báo/ngày hiệu lực, mã thêm/bớt và đường dẫn nguồn.
- `members.csv`: rổ mới nhất trong lịch đã dựng, dùng cho các biểu đồ mô tả hiện tại.

`agqo/universe.py` kiểm tra số lượng rổ, khoảng hiệu lực chồng lấn và đường dẫn HTTPS. `agqo/walkforward.py` chỉ cho phép một mã vào danh sách ứng viên nếu mã đó thuộc VN30 tại ngày tín hiệu. Bộ nạp walk-forward từ chối snapshot tĩnh.

Đây là lịch sử tổng hợp có dẫn nguồn công khai, chưa phải cơ sở dữ liệu HOSE đầy đủ và đã kiểm toán. Các kỳ không có thông báo thay đổi được giữ nguyên giữa hai mốc đã biết; cần đối chiếu toàn bộ thông báo rà soát quý, thay đổi ngoài kỳ và mã đổi tên trước khi coi lịch là hoàn chỉnh. Vì vậy mã đã loại bỏ việc áp ngược rổ hiện tại, nhưng chưa thể tuyên bố mọi sai lệch đại diện đã được loại bỏ.

### Giá điều chỉnh và giả định giao dịch

`scripts/download_vn30_dataset.py` lưu cùng lúc hai cơ sở giá:

- `open/high/low/close/volume`: giá thô từ DNSE; dùng làm giá vào lệnh mô phỏng và tính `close × volume` làm đại diện thanh khoản.
- `open_adjusted/high_adjusted/low_adjusted/close_adjusted`: giá VCI qua Vnstock 5.1.0; dùng để ước lượng lợi suất và đánh dấu giá trị danh mục qua thời gian. Tài liệu Vnstock ghi giá OHLC VCI đã điều chỉnh theo sự kiện quyền; nguồn VCI/KBS có thể khác nhau.

Sổ danh mục áp dụng tỷ lệ giá mở cửa điều chỉnh giữa ngày vào và ngày ra cho phần tài sản đang nắm giữ. Phí và giới hạn khớp vẫn dựa trên lệnh danh nghĩa cùng thanh khoản từ giá thô. Đây là mô phỏng lợi suất tổng hợp từ chuỗi giá điều chỉnh, **không** phải sổ kế toán sự kiện doanh nghiệp: mã chưa đối soát độc lập từng cổ tức tiền mặt, chia tách, cổ phiếu thưởng và quyền mua, chưa ghi nhận chính xác ngày tiền/cổ phiếu được ghi có. Giá trị `close × volume` vẫn không xác nhận được giá trị khớp thực tế, chênh lệch giá mua bán, thuế hay độ sâu sổ lệnh.

Vnstock quyền Khách chỉ cung cấp tối đa 365 ngày; truy xuất đủ 2022–2026 cần đăng ký miễn phí quyền Cộng đồng. Bộ tải từ chối ghi tập hoàn chỉnh nếu lịch sử VCI bắt đầu muộn hoặc còn thiếu phiên điều chỉnh. Quyền dùng thư viện không tự cấp quyền chia sẻ dữ liệu DNSE/VCI. Tệp dữ liệu OHLCV không đưa lên Git; nguồn, mã băm và chẩn đoán hệ số điều chỉnh nằm trong `manifest.json`.

### Tin tức và chống nhìn trước

`scripts/fetch_gdelt_news_metadata.py` thu siêu dữ liệu GDELT DOC theo bí danh công ty trong `data/news/company_aliases.csv`. Bộ thu chỉ giữ URL, mã truy vấn, dấu `seendate` lần đầu được GDELT ghi nhận, giờ thu thập tại máy và mã băm; không lưu tiêu đề hoặc nội dung bài. `data/news/manifest.json` kê quyền nguồn, cách ghép thực thể và chính sách thời gian.

`agqo/news.py` chỉ cho một bản ghi vào payload khi cả thời điểm nguồn ghi nhận và giờ thu thập đều không sau ngày tín hiệu. Vì vậy bài được tìm thấy sau này không thể quay ngược để giải thích tín hiệu cũ. `seendate` không được coi là giờ xuất bản; bí danh tìm kiếm chưa được xác nhận thủ công là thực thể đúng mã; số lần nhắc tên không phải cảm xúc, thông tin trọng yếu hay quan hệ nhân quả. Tin chỉ là ngữ cảnh tùy chọn cho LLM, không đi vào dự báo lợi suất hoặc hàm mục tiêu QAOA. Lượt thử GDELT hiện bị HTTP 429; manifest ghi nguồn đang giới hạn, tệp CSV chỉ có tiêu đề cột. Nếu tệp có bản ghi nhưng lượt thu không bao phủ đủ bí danh, walk-forward từ chối dùng chúng. Các kết quả hiện có không dùng tin tức.

### Tình trạng kết quả

37.308 dòng cũ trong `ohlcv_daily.csv` vẫn là dữ liệu thô theo snapshot và chưa có các cột điều chỉnh. Kết quả/báo cáo đã lưu được gắn nhãn cũ; không dùng chúng như bằng chứng đã xử lý ba hạn chế. Cần đăng ký Vnstock Cộng đồng, tải lại toàn kỳ, kiểm tra lịch thành phần và chạy lại walk-forward trước khi trích dẫn số liệu mới.

OHLCV cục bộ không gửi lên Modal; Modal chỉ nhận payload tổng hợp.

## 3. Tiểu mô hình chế độ thị trường

`agqo/ai.py` dùng `StandardScaler` và `sklearn.linear_model.LogisticRegression`. Đặc trưng của VN30 gồm biến động thực hiện 20/60/120 phiên, lợi suất 20/60 phiên và tỷ số biến động 20/120. Nhãn là việc biến động thực hiện 21 phiên tiếp theo có vượt phân vị 70% được ước lượng từ tập huấn luyện hay không.

Tách mốc mặc định:

| Giai đoạn | Mốc | Vai trò |
|---|---|---|
| Huấn luyện ban đầu | đến 31/10/2024 | Chuẩn hóa, xác lập ngưỡng, fit mô hình |
| Xác nhận | 01/11/2024–30/04/2025 | Chọn C theo log-loss, chặn nhãn tương lai trước ranh giới |
| Walk-forward | từ 01/05/2025 | Mở rộng huấn luyện bằng nhãn đã trưởng thành |

Xác suất này dự báo **chế độ biến động**, không dự báo hướng hay lợi suất. Payload cung cấp Brier và kỹ năng Brier so với nền tỷ lệ nhãn đã biết. Nếu kỹ năng âm hoặc có dưới sáu dự báo tháng đã trưởng thành, prompt yêu cầu Qwen xem xác suất đó là bằng chứng yếu. Không được tăng λ, p hoặc số qubit chỉ vì xác suất biến động cao.

## 4. Qwen3-8B và thiết kế prompt

### Mô hình và suy luận

- Mô hình: `Qwen/Qwen3-8B`, ghim revision `b968826d9c46dd6066d109eabc6255188de91218`.
- Nơi chạy: Modal ưu tiên GPU L4, dự phòng A10 24 GB khi thiếu chỗ; trọng số NF4 4-bit, double quantization, kiểu tính bf16 nếu được hỗ trợ và fp16 nếu không. Ngân sách sinh là 192 token. T4 16 GB đã bị loại khỏi dự phòng sau khi gặp thiếu bộ nhớ GPU lúc sinh.
- Suy luận zero-shot, greedy decoding; không huấn luyện lại mô hình.
- Phiên bản prompt `agqo-prompt-v9-en-rag-submodel-allowlisted-structured`: toàn bộ chỉ dẫn và nhãn dữ liệu gửi đến mô hình được chuẩn hóa bằng tiếng Anh.
- Mỗi tín hiệu có lược đồ riêng với danh sách cấu hình, mã insight và mã bằng chứng được cho phép; đầu ra chỉ gồm `policy_id`, `insight_codes`, `evidence_ids`.

Qwen3-8B không được giả định là chuyên gia tài chính. System prompt nói rõ điều này và cấm mô hình điền khoảng trống bằng kiến thức ghi nhớ. RAG cung cấp định nghĩa CAGR, Sharpe, Sortino, drawdown, CVaR, turnover, regret, tỷ lệ mẫu khả thi, λ, α, hàm mục tiêu, vai trò classifier và giới hạn dữ liệu. Bộ phân tích insight áp dụng ngưỡng tài chính xác định trên số liệu; bộ phân loại logistic chỉ ước tính chế độ biến động; bộ giám sát kiểm tra hiệu quả các cấu hình bằng số liệu lịch sử đã khép. Mô hình không được bịa thống kê, tự đặt tham số, dự báo lợi suất hoặc sinh luận cứ tự do.

### RAG cục bộ

`agqo/knowledge.py` chứa kho ghi chú phiên bản `agqo-local-rag-v3-finance-qaoa-grounding`. Bộ truy xuất từ khóa xác định luôn đưa vào năm ghi chú nền: định nghĩa chỉ số tài chính, giới hạn dữ liệu, benchmark exact/regret, ý nghĩa các trường VN30 và giới hạn của bộ phân loại chế độ. Hai ghi chú liên quan nhất được chọn thêm từ định nghĩa hàm mục tiêu và thiết kế QAOA. Kho nhỏ có bảy ghi chú, nguồn nội bộ hoặc bài phương pháp gốc được ghim rõ; nội dung được nhúng trong payload để kiểm toán. Không tải tài liệu ngoài hoặc gọi dịch vụ nhúng trong lúc chạy.

Qwen được chỉ dẫn đọc bằng chứng theo thứ tự: kết quả tài chính ròng sau phí cùng Sharpe, drawdown, CVaR và turnover; sau đó đối chiếu regret, tỷ lệ mẫu khả thi và số cổng logic hai qubit. Không tối ưu Sharpe hoặc regret riêng lẻ. Payload cung cấp số kỳ đã khép và bộ đếm cổng logic từng chính sách. Lược đồ JSON được giới hạn theo từng tín hiệu: danh sách `eligible_policy_ids` áp dụng ngưỡng sáu kết quả đã khép; `allowed_insight_codes` chỉ gồm mã vượt ngưỡng trên dữ liệu; `evidence_ids` chỉ nhận mã thực sự có trong payload. Nếu lịch sử chưa đủ, mã khởi động bắt buộc là `n12_balanced_xy_ring_p1`. Bộ giám sát số học vẫn quyết định độc lập cấu hình nào được thực thi.

Kho ghi chú không tải tài liệu mới trong lúc chạy. Nội dung, mã ghi chú, nguồn và phiên bản được lưu trong JSON quyết định để kiểm toán. Ghi chú phương pháp Quantum trỏ tới bài QAOA gốc và bài về mixer bảo toàn ràng buộc; định nghĩa tài chính là định nghĩa đang được triển khai trong mã dự án.

### Lược đồ và sửa đầu ra

Đầu ra yêu cầu, không có lời giải thích tự do hay mức tin cậy tự khai:

```json
{
  "policy_id": "one id from the catalog",
  "insight_codes": ["codes allowed for this signal only"],
  "evidence_ids": ["IDs supplied in this payload only"]
}
```

`validate_guidance` từ chối policy, insight hoặc evidence không nằm trong danh sách theo tín hiệu; đồng thời từ chối sai kiểu và trường tự do như `rationale`/`risk_flags`. Nếu JSON sai, hệ thống yêu cầu Qwen sửa một lần; nếu vẫn sai, `repair_guidance` bỏ trường ngoài lược đồ, loại mã không hợp lệ và quay về policy khởi động an toàn. Các lần sửa được lưu tại `validation_repairs`. Sau đó mã cục bộ dựng giải thích tiếng Việt từ các số đo đã xác thực và các mẫu câu cố định; mã rủi ro cũng được tính trực tiếp từ ngưỡng đã công bố. Bộ giám sát vẫn đánh giá đề xuất bằng bằng chứng độc lập.

## 5. Hàm mục tiêu danh mục

Mỗi bài toán chọn đúng K trong N mã:

\[
\min_x\; \lambda\frac{x^T\Sigma_\alpha x}{K^2}
 - \frac{\mu^T x}{K}
 + 12\left(\sum_i c_i\left|\frac{x_i}{K}-w_i^{prev}\right|
 + c_{out}w_{out}^{prev}\right),\qquad \sum_i x_i=K,
\]

trong đó `x_i ∈ {0,1}`, `μ` là lợi suất kỳ vọng năm hóa từ lịch sử, `Σ` là hiệp phương sai năm hóa, `λ` là mức phạt rủi ro, `c_i` là phí theo mỗi đồng giao dịch, `w_prev` là tỷ trọng trước kỳ và 12 là số lần tái cân bằng năm hóa.

Co rút hiệp phương sai:

\[
\Sigma_\alpha=(1-\alpha)\Sigma+\alpha\,\operatorname{diag}(\Sigma).
\]

`α` điều chỉnh co rút về ma trận đường chéo; nó không phải xác suất hoặc dự báo lợi suất. `λ` điều chỉnh tương quan rủi ro/lợi suất ước lượng, không phải mức confidence. Lớp mô phỏng giao dịch vẫn tính phí tiền mặt, lệnh khớp thiếu và sức chứa ADTV riêng, vì hàm mục tiêu không mô hình toàn bộ khớp lệnh thực tế.

## 6. Danh mục cấu hình QAOA

AGQO chạy 14 chính sách cố định song song để tạo bằng chứng quá khứ. Mỗi chính sách dùng K=6 và 1.024 shots.

| Số qubit N | Cấu hình tiêu biểu |
|---:|---|
| 8 | X p=1 λ=8 α=0,70; XY vòng p=1/2 λ=5 α=0,40 |
| 12 | X p=1/2; XY vòng p=1/2; XY đường thẳng p=2 λ=5 α=0,70; XY đầy đủ p=1 λ=5 α=0,70; XY tương quan p=2 |
| 16 | X p=1; XY vòng p=1/2; XY tương quan p=2 |

Policy IDs, tham số đầy đủ và mô tả chạy nằm trong `agqo/guide.py`; kết quả policy-by-policy nằm ở JSON cuối.

### Bộ trộn

- **X:** chồng chập đều bằng H, mỗi lớp có RX. Hạng phạt `(Σx_i−K)^2` buộc nghiệm tốt có đúng K; trạng thái đo vẫn có thể sai cardinality. Hệ số phạt được chặn theo biên độ mục tiêu trên toàn siêu lập phương để nghiệm vi phạm cardinality không thể thắng nghiệm khả thi.
- **XY:** khởi tạo trạng thái cơ sở có K bit 1; mỗi cạnh áp dụng RXX và RYY. Cổng trao đổi bảo toàn số bit 1, nên mạch giữ cardinality trong số học lý tưởng.
- **Bố trí XY:** vòng N cạnh; đường thẳng N−1 cạnh; đầy đủ `N(N−1)/2` cạnh; tương quan là vòng liên thông cộng hai láng giềng tương quan mạnh cho mỗi mã.
- **Độ sâu p:** số lớp cost/mixer xen kẽ. Tăng p tăng số tham số góc và số cổng. Chỉ giữ p lớn nếu giảm regret/đạt nghiệm khả thi tốt hơn đủ để biện minh chi phí.

Cost Hamiltonian giữ tương tác hiệp phương sai dày nên có tối đa `N(N−1)/2` cổng RZZ mỗi lớp. Bộ trộn XY có hai cổng hai qubit RXX/RYY trên mỗi cạnh mỗi lớp. Các số trong JSON là bộ đếm cổng logic ở mức simulator, không phải số cổng vật lý sau transpile.

`agqo/simulator.py` dùng NumPy, véc-tơ trạng thái và COBYLA (SciPy). Mỗi seed khởi tạo góc khác nhau; mô hình chọn mẫu khả thi tốt nhất trong các seed. Nếu không có mẫu khả thi, đường chạy ghi rõ và dùng nghiệm chính xác. Thí nghiệm cuối đặt ngân sách tối đa 100 đánh giá mục tiêu mỗi seed; tối ưu góc dùng lấy mẫu hữu hạn 1.024 shots.

## 7. Bộ chọn quy tắc và giám sát an toàn

Đối chứng `RULE_ADAPTIVE` không gọi LLM. Nó dùng các kết quả đã khép, tối thiểu sáu kỳ tài chính và sáu bài toán QAOA đủ dữ liệu, rồi tối đa hóa:

\[
U=\text{Sharpe}-1.5|\text{MaxDD}|-2\,\overline{\text{regret}}-0.10\,\text{turnover}.
\]

Trước khi đủ dữ liệu, cấu hình khởi động là `n12_balanced_xy_ring_p1`. Sau khi LLM đề xuất một policy, bộ giám sát chỉ dùng kỳ có ngày thoát không muộn hơn tín hiệu hiện tại. Nó quay về bộ chọn quy tắc khi:

1. Policy đề xuất chưa có sáu kỳ kết quả đã khép.
2. Tỷ lệ mẫu khả thi của đề xuất dưới 90% và thấp hơn đối chứng trên 5 điểm phần trăm.
3. Regret trung bình vượt 10% và tệ hơn đối chứng trên 5 điểm phần trăm.
4. Điểm tiện ích lịch sử thấp hơn đối chứng trên 0,25 đồng thời MaxDD tệ hơn trên 3 điểm phần trăm.

Các ngưỡng là guardrail kỹ thuật đã khóa trong mã, không phải bằng chứng chúng tối ưu tài chính. Đề xuất LLM, policy thực thi, số liệu kiểm tra và lý do fallback được lưu song song.

## 8. Bộ đối chứng và thước đo

### Tài chính

- CAGR ròng, biến động năm hóa, Sharpe, Sortino, Calmar, MaxDD.
- VaR/CVaR tháng 95%, hệ số lợi nhuận, tỷ lệ tháng dương.
- Chi phí giao dịch, turnover hai chiều, tỷ lệ lệnh không khớp do sức chứa/vốn, ADTV.
- Lợi nhuận vượt VN30/VN-Index và khoảng tin cậy bootstrap khối 3/6 tháng.

Sharpe dùng lãi suất phi rủi ro tháng bằng 0 và hệ số năm hóa `sqrt(12)`. CVaR95 là trung bình lợi suất tháng tại hoặc dưới phân vị 5%. Kỳ mẫu 16 tháng làm các chỉ số đuôi rất nhiễu.

### Chất lượng solver

- Nghiệm vét cạn chính xác cho cùng bài toán N/K làm chuẩn toàn cục.
- Greedy và simulated annealing là heuristic cổ điển; QAOA được so trên cùng hàm mục tiêu.
- Regret chuẩn hóa bằng chênh mục tiêu với exact chia cho biên độ mục tiêu trong các nghiệm khả thi.
- Tỷ lệ feasible là tỷ phần shots có đúng K mã, không phải xác suất sinh lời.
- Báo regret qua ngày và seed, tần suất exact fallback, thời gian CPU và gate proxy.

### Đối chứng tài chính

VN30, VN-Index, nghiệm chính xác toàn rổ, Ledoit–Wolf, AI điều chỉnh λ/α, QAOA cố định X/XY, AI→QAOA với danh mục 12 mã, bộ chọn quy tắc→QAOA, AGQO sau giám sát, greedy và simulated annealing.

## 9. Mã nguồn và chức năng

| Tệp | Vai trò |
|---|---|
| `agqo/market_data.py` | Nạp/kiểm tra dữ liệu thô, cột giá điều chỉnh và lịch thành phần theo ngày |
| `agqo/universe.py` | Kiểm tra khoảng hiệu lực và trả rổ VN30 tại ngày tín hiệu |
| `agqo/news.py` | Kiểm tra dấu thời gian, quyền truy xuất và lọc siêu dữ liệu tin theo thời điểm |
| `agqo/ai.py` | Đặc trưng và hồi quy logistic walk-forward |
| `agqo/knowledge.py` | Kho ghi chú RAG cục bộ và bộ truy xuất |
| `agqo/guide.py` | Prompt tiếng Anh, schema, allow-list, cache, sửa đầu ra, kết nối Modal/Transformers |
| `agqo/estimators.py` | μ/Σ, shrinkage, mô hình rủi ro |
| `agqo/problem.py` | Hàm mục tiêu, QUBO/Ising, exact/greedy/annealing |
| `agqo/simulator.py` | Mô phỏng QAOA véc-tơ trạng thái, mixer X/XY, gate metrics |
| `agqo/qpu.py` | Mạch Qiskit và cầu nối QPU tùy chọn, không dùng tạo kết quả hiện tại |
| `agqo/walkforward.py` | Lắp ghép tín hiệu, guardrail, chiến lược, sổ giao dịch và JSON |
| `agqo/walkforward_plots.py` | Biểu đồ tài chính và QAOA |
| `agqo/final_visuals.py` | Sơ đồ cổng, trade-off gate/regret, audit đề xuất/thực thi |
| `agqo/walkforward_report.py` | Sinh báo cáo tiếng Việt từ JSON |
| `modal_qwen3_agqo.py` | Endpoint Qwen3 trên Modal; cache model trên Modal Volume |
| `scripts/check_modal_qwen3.py` | Kiểm tra endpoint bằng payload giả lập |
| `scripts/run_ai_qaoa_walkforward.py` | Lệnh chạy đầy đủ, xuất JSON, hình và báo cáo |
| `scripts/build_vn30_membership_history.py` | Dựng lịch thành phần VN30 từ snapshot neo và sự kiện có nguồn |
| `scripts/download_vn30_dataset.py` | Tải giá DNSE thô và VCI điều chỉnh, kiểm tra độ bao phủ và tạo manifest |
| `scripts/fetch_gdelt_news_metadata.py` | Thu siêu dữ liệu tin GDELT gần thời gian thực, không lưu tiêu đề/nội dung |

## 10. Chạy lại

```bash
source .venv/bin/activate
set -a
source config/modal-qwen3.env
set +a
modal deploy modal_qwen3_agqo.py
python scripts/check_modal_qwen3.py
python scripts/build_vn30_membership_history.py
python scripts/download_vn30_dataset.py
python scripts/run_ai_qaoa_walkforward.py --llm-guide modal-qwen3
```

Nếu bật ngữ cảnh tin, thu thập đủ mọi bí danh bằng `python scripts/fetch_gdelt_news_metadata.py --days 30` rồi truyền `--news data/news/gdelt_metadata.csv`. Lượt chỉ giới hạn một mã dành cho chẩn đoán, không được coi là nguồn toàn danh mục. Chỉ bật khi manifest xác nhận `collected_metadata_only`, `complete_universe_query=true` và `news_context_available=true`; bản ghi hồi cứu sẽ không được dùng cho quyết định có ngày trước `collected_at`.

Mẫu cấu hình là `config/modal-qwen3.env.example`. `AGQO_QWEN3_GPU=L4,A10` yêu cầu Modal thử L4 trước rồi A10 nếu L4 không có chỗ; thứ tự là ưu tiên cấp GPU chứ không làm hai GPU chạy đồng thời. Thay đổi tên app, revision hoặc ngân sách token ở đó; không đưa token vào Git. Lệnh chạy `--llm-guide qwen3` dùng model tại máy hiện tại nếu máy có CUDA và bộ nhớ phù hợp. `--llm-guide none` chỉ tạo đối chứng, không gọi mô hình ngôn ngữ.

Kết quả cuối: `results/final/agqo_final_walkforward.json`, `results/final/dataset_summary.json`, `results/final/BAO_CAO_AGQO_CUOI_CUNG.md`, `results/final/figures/` (11 hình walk-forward/QAOA và 8 hình khám phá dữ liệu) và `results/final/qwen3_decisions.json` (chỉ các quyết định prompt v9).

## 11. Tài liệu tham khảo

- [Qwen3-8B model card và lịch sử phiên bản](https://huggingface.co/Qwen/Qwen3-8B)
- [Transformers: lượng tử hóa bitsandbytes 4-bit/NF4](https://huggingface.co/docs/transformers/main/quantization/bitsandbytes?bnb=4-bit)
- [Modal: GPU cloud](https://modal.com/docs/guide/gpu)
- [Farhi, Goldstone, Gutmann (2014), A Quantum Approximate Optimization Algorithm](https://arxiv.org/abs/1411.4028)
- [Hadfield và cộng sự, From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz](https://arxiv.org/abs/1709.03489)
