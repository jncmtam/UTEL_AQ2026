# Tài liệu kỹ thuật AGQO

**Phiên bản đang mô tả:** V1 — tối ưu danh mục có tính chi phí giao dịch.<br>
**Mục đích:** giải thích từ đầu đến cuối công nghệ, dữ liệu, thuật toán, hàm và đường đi tạo ra các kết quả trong [báo cáo kết quả AGQO](BAO_CAO_KET_QUA_AGQO.md).

## 1. Tóm tắt kiến trúc

```text
Dữ liệu lịch sử đã được xác minh
        ↓
Đặc trưng thị trường tại thời điểm t
        ↓
Mô hình hồi quy logistic → xác suất biến động cao
        ↓
Điều chỉnh λ; cố định mức co rút α = 0,40 trong V1
        ↓
Ước lượng μ, Σ và ghép chi phí với tỷ trọng trước giao dịch
        ↓
Bài toán chọn K mã → hàm mục tiêu → QUBO → Ising
        ↓
Nghiệm chính xác / tham lam / tôi luyện / QAOA / QPU tùy chọn
        ↓
Danh mục mục tiêu → mô phỏng phí, lợi nhuận ròng, doanh số, thanh khoản
        ↓
So với đối chuẩn và lượng hóa độ không chắc chắn
```

Hiện chưa có bộ đọc dữ liệu thị trường và bộ điều phối toàn bộ chuỗi trên dữ liệu thật. Các lớp ước lượng, tối ưu và đánh giá đã có giao diện để nối dữ liệu vào; lượt V1 được báo cáo dùng dữ liệu tổng hợp.

## 2. Công nghệ đã dùng

| Công nghệ | Phiên bản đã ghim trong môi trường dự án | Vai trò |
|---|---:|---|
| Python | 3.12.12 trong môi trường chạy; dự án cho phép từ 3.12 đến dưới 3.14 | Ngôn ngữ triển khai |
| NumPy | 2.5.4 | Ma trận, véc-tơ trạng thái, lấy mẫu và sinh số PCG64 |
| SciPy | 1.18.1 | Bộ tối ưu COBYLA và tính toán khoa học |
| pandas | 3.0.6 | Bảng lợi nhuận, chỉ số tài sản, lịch tháng và căn chỉnh dữ liệu |
| scikit-learn | 1.9.1 | Hồi quy logistic, chuẩn hóa, hiệp phương sai Ledoit–Wolf và co rút |
| Qiskit | 2.5.2 | Biểu diễn mạch tham số và biên dịch mạch |
| Qiskit Aer | 0.17.2 | Mô phỏng mạch cục bộ và đối chiếu xác suất |
| IBM Quantum Runtime | 0.50.0 | Giao diện SamplerV2 để gửi mạch đến thiết bị nếu được cấp quyền |
| pytest | 9.1.1 | Hạ tầng kiểm thử của kho mã; bộ kiểm thử không được chạy trong lượt tạo tài liệu này |

Các phiên bản được ghi trong `requirements-lock.txt`; các thư viện lượng tử là tùy chọn cài đặt trong `pyproject.toml`. Mã lõi mô phỏng QAOA nhỏ bằng NumPy/SciPy, không bắt buộc gọi dịch vụ lượng tử.

## 3. Vai trò của mô hình ngôn ngữ

**Mô hình ngôn ngữ lớn không nằm trong đường chạy của sản phẩm.** Mã dự án không gọi API mô hình ngôn ngữ, không đưa tin tức vào mô hình ngôn ngữ để chấm mã, và không dùng mô hình ngôn ngữ phát tín hiệu mua bán.

Thành phần “AI” hiện tại là hồi quy logistic của scikit-learn, tức mô hình phân loại có giám sát. Codex/ChatGPT được dùng như công cụ hỗ trợ con người lập kế hoạch, rà soát thiết kế, chỉnh mã và viết tài liệu; đầu ra của công cụ này không phải dữ liệu đầu vào cho kết quả tài chính hay kết quả QAOA. Có thể tái lập phép chạy bằng mã, cấu hình và hạt giống mà không cần mô hình ngôn ngữ.

## 4. Đường đi dữ liệu và mô hình AI

### 4.1. Đặc trưng

`build_daily_features` tạo đặc trưng đến hết phiên t:

- Độ biến động thị trường 20, 60 và 120 phiên.
- Lợi nhuận thị trường cộng dồn 20 và 60 phiên.
- Tỷ số biến động 20/120 phiên.
- Trung vị tương quan 60 phiên giữa các mã.
- Tỷ lệ mã có đủ lịch sử 252 phiên.
- Trung vị log giá trị giao dịch bình quân 20 phiên.
- Tỷ lệ mã tạm ngừng chỉ khi có chuỗi dữ liệu lịch sử đã được xác minh.

Tại đầu cửa sổ dữ liệu, đặc trưng chưa đủ lịch sử được giữ thiếu và không đưa vào huấn luyện/chấm điểm.

### 4.2. Nhãn, chia tập và huấn luyện

`forward_volatility` tạo nhãn tương lai bằng độ biến động của lợi nhuận thị trường trong 21 phiên sau ngày t. Mốc chia tập hiện có trong đề cương là huấn luyện đến 2020, xác nhận 2021–2023, kiểm tra từ 2024 đến tháng đầy đủ mới nhất.

`fit_regime_model`:

1. Bỏ hàng có đặc trưng thiếu và không dùng nhãn chưa trưởng thành qua ranh giới thời gian.
2. Tạo ngưỡng biến động cao từ phân vị 70 của tập huấn luyện; cùng ngưỡng đó được dùng cho các tập sau.
3. Khớp `StandardScaler` trên huấn luyện.
4. Chọn độ điều chuẩn logistic `C` bằng hàm mất mát logarit trên xác nhận.
5. Khớp lại trên huấn luyện cộng xác nhận sau khi chọn cấu hình; tập kiểm tra không tham gia.

`RegimeModel.predict_probability` trả về xác suất trạng thái biến động cao. `evaluate_regime_model` và `evaluate_regime_probabilities` đo hàm mất mát logarit, điểm Brier, so sánh với xác suất nền lấy từ huấn luyện và lập bảng hiệu chỉnh. Chưa có dữ liệu thật để báo các chỉ số AI ngoài mẫu.

### 4.3. Cách xác suất điều chỉnh danh mục

Trong V1, AI chỉ điều chỉnh hệ số ngại rủi ro:

\[
\lambda(p)=\lambda_{min}+(\lambda_{max}-\lambda_{min})p,
\qquad \lambda_{min}=2,\;\lambda_{max}=10.
\]

Với xác suất minh họa p = 0,70, λ = 7,60. Đây là ánh xạ ban đầu, chưa được tối ưu hay xác nhận bằng kiểm định ngoài mẫu. Mức co rút hiệp phương sai giữ α = 0,40 để tách đóng góp của AI khỏi đóng góp của việc đổi cách ước lượng rủi ro.

## 5. Ước lượng tài chính và hàm mục tiêu V1

### 5.1. Đầu vào

`estimate_annual_inputs` nhận lợi nhuận ngày đã căn chỉnh theo mã:

- Lợi nhuận kỳ vọng năm hóa: trung bình ngày × 252.
- Hiệp phương sai năm hóa: hiệp phương sai ngày × 252; có thể dùng mẫu hoặc Ledoit–Wolf.
- Nếu dùng co rút đường chéo, phương sai riêng được giữ, còn hiệp phương sai chéo được nhân với `1 - alpha`.

### 5.2. Bài toán chọn danh mục

Với N mã, mỗi biến `x_i` nhận 0 hoặc 1; danh mục chọn đúng K mã và chia tỷ trọng bằng nhau. Mục tiêu năm hóa cần tối thiểu hóa:

\[
J(x)=\lambda\frac{x^\top\Sigma x}{K^2}
-\frac{\mu^\top x}{K}
+R\sum_i c_i\left|\frac{x_i}{K}-w_i^{trước}\right|,
\qquad \sum_i x_i=K.
\]

Trong đó μ là lợi nhuận kỳ vọng, Σ là hiệp phương sai, cᵢ là phí trên mỗi đồng mua/bán, `w_i^{trước}` là tỷ trọng trước giao dịch, và R là số lần tái cân bằng năm hóa. V1 mặc định dùng 25 điểm cơ bản và 12 lần một năm; đây là tham số giả định, phải thay bằng dữ liệu có căn cứ trước khi kết luận tài chính.

`PortfolioProblem.score`, `two_way_turnover` và `annual_transaction_cost` chấm mục tiêu, doanh số và phí cho từng danh mục. `build_investable_problem` tạo V1; `build_regime_problem` cho phép đối chứng rộng hơn; `build_ledoit_wolf_problem` dựng đối chứng tài chính Ledoit–Wolf.

## 6. Biểu diễn QUBO và Ising

### 6.1. QUBO

`build_qubo` đưa phương sai thành hệ số bậc hai, lợi nhuận và chi phí thành hệ số tuyến tính. Với biến nhị phân, chi phí tuyệt đối có thể viết chính xác:

\[
\left|\frac{x_i}{K}-w_i^{trước}\right|
=w_i^{trước}+
\left(\left|\frac{1}{K}-w_i^{trước}\right|-w_i^{trước}\right)x_i.
\]

Hằng số được lưu trong phần bù QUBO. Nhờ đó điểm QUBO của mọi trạng thái khả thi bằng đúng mục tiêu danh mục, kể cả phần phí.

Với bộ trộn X, QUBO thêm hạng phạt:

\[
P\left(\sum_i x_i-K\right)^2,
\]

để mẫu sai số lượng mã không thắng do hạng phạt quá thấp. Nếu không truyền P, mã chọn mức lớn hơn khoảng dao động mục tiêu khả thi. Với XY, không thêm phạt số lượng vì bộ trộn bảo toàn số bit 1.

### 6.2. Ising và mạch

`to_ising` đổi biến theo `x = (1 - Z)/2`, giữ trường, tương tác cặp và hằng số. Ở mỗi lớp QAOA, mạch áp dụng pha hàm mục tiêu rồi bộ trộn:

- X: trạng thái chồng chập Hadamard, pha chi phí bằng cổng RZ/RZZ và bộ trộn RX.
- XY: trạng thái đầu có đúng K bit 1; bộ trộn trên vòng dùng cặp RXX/RYY theo tích Trotter bậc một, giữ số mã đã chọn.

Trạng thái đầu XY hiện là **một trạng thái cơ sở khả thi duy nhất** sau khi hoán vị mã; đây không phải chồng chập đều trên mọi danh mục K mã. Đây là lựa chọn triển khai hiện tại và là một yếu tố cần nghiên cứu nếu muốn cải thiện chất lượng XY.

Độ sâu p hiện dùng trong thí nghiệm là 1. `optimize_qaoa` chọn góc β, γ bằng COBYLA; mỗi lần đánh giá lấy 512 mẫu. H2 cũ giới hạn 50 lần đánh giá và dùng ba hạt giống.

Kết quả `QaoaResult` lưu bộ trộn, p, hạt giống, N/K, λ, tỷ trọng và phí trước giao dịch, số lần đánh giá, mục tiêu ước lượng, điểm tốt nhất trong mẫu khả thi, tỷ lệ khả thi đo được và lý tưởng, số mẫu, chuỗi bit tốt nhất, góc tối ưu và thời gian mô phỏng.

Khi đọc nhật ký, dùng `best_feasible_score` để so điểm tài chính. `objective_estimate` là kỳ vọng năng lượng QUBO lấy mẫu; với bộ trộn X, năng lượng này có thể bao gồm hạng phạt. Trong đầu ra QPU, trường `best_feasible_qubo_energy` được giữ vì tương thích nhật ký cũ nhưng hiện chứa cùng điểm mục tiêu danh mục như `best_feasible_score`, không phải năng lượng QUBO thuần.

## 7. Các bộ giải và chuẩn so sánh

| Bộ giải | Hàm | Cách làm |
|---|---|---|
| Nghiệm chính xác | `exact_solve` | Duyệt toàn bộ tổ hợp khả thi; hiện giới hạn N ≤ 30, K ≤ 6 |
| Tham lam | `greedy_solve` | Lần lượt thêm mã làm giảm mục tiêu nhiều nhất |
| Tôi luyện | `anneal_solve` | Đổi một mã đang chọn với một mã ngoài danh mục; chỉ đi trong miền K khả thi |
| QAOA mô phỏng | `statevector`, `optimize_qaoa` | Mô phỏng véc-tơ trạng thái NumPy, lấy mẫu hữu hạn và tối ưu góc bằng COBYLA |
| Mạch Aer | `crosscheck_aer` | Đối chiếu phân bố mạch Qiskit với véc-tơ trạng thái; không gọi mạng |
| QPU tùy chọn | `run_qpu` | Biên dịch mạch theo thiết bị, gửi bằng SamplerV2, ghi số mẫu, cổng và độ sâu |

QPU chưa được dùng để tạo các kết quả trong báo cáo. Mã QPU có chốt cấu hình, yêu cầu token qua biến môi trường, giới hạn ngân sách mẫu và sổ giữ chỗ; phần này mới là đường chạy sẵn sàng có điều kiện, chưa phải bằng chứng thiết bị.

## 8. Đánh giá kết quả tài chính

`simulate_monthly_portfolios` nhận bảng trọng số mục tiêu và lợi nhuận tháng cùng ngày, cùng mã. Mỗi kỳ, hàm tính thay đổi vị thế, phí mua/bán, lợi nhuận gộp và ròng, doanh số một/hai chiều, giá trị tài khoản và mức tham gia ADTV.

`summarize_monthly_returns` trả về số tháng, tăng trưởng kép, biến động năm hóa, Sharpe, Sortino, mức sụt giảm tối đa, tỷ lệ tháng dương và giá trị cuối kỳ. `compare_monthly_returns` căn hai chuỗi theo các tháng chung, tính chênh lệch lợi nhuận và gọi `paired_block_bootstrap_mean_ci` để lập khoảng tin cậy bằng lấy mẫu khối tròn; mặc định khối ba tháng, 10.000 lần lấy mẫu, hạt giống 11.

Chi phí trong hàm mục tiêu giúp bộ chọn cân nhắc trước khi đổi danh mục; trong mô phỏng danh mục tháng, phí khớp lệnh được trừ một lần khỏi tài khoản. Hai bước có vai trò khác nhau, không trừ hai lần cùng một khoản trên một đường lợi nhuận.

Giới hạn quan trọng: mô phỏng giả định đủ khớp lệnh. ADTV chỉ gắn cờ vượt giới hạn tham gia; chưa phân bổ lệnh qua nhiều ngày, mô phỏng khớp một phần, chênh lệch mua/bán hay tác động thị trường. Các hàm đánh giá chưa được chạy trên dữ liệu thị trường trong dự án hiện tại.

## 9. Danh mục hàm theo tệp

### `agqo/ai.py`

| Hàm / lớp | Vai trò |
|---|---|
| `build_daily_features` | Tạo đặc trưng thị trường theo dữ liệu đến phiên hiện tại |
| `forward_volatility` | Tạo nhãn biến động tương lai |
| `RegimeModel` | Giữ bộ chuẩn hóa, bộ phân loại, ngưỡng và xác suất nền huấn luyện |
| `fit_regime_model` | Chia thời gian, chọn C trên xác nhận, khớp mô hình cuối |
| `regime_controls` | Ánh xạ cũ đồng thời sang λ và α; giữ cho đối chứng V0 |
| `risk_aversion_from_probability` | Ánh xạ xác suất sang λ trong miền chỉ định của V1 |
| `evaluate_regime_probabilities` | Đo hàm mất mát logarit, điểm Brier và hiệu chỉnh |
| `evaluate_regime_model` | Chấm mô hình trên khoảng thời gian được chỉ định |
| `diagonal_shrinkage` | Co hiệp phương sai về đường chéo |

### `agqo/estimators.py`

| Hàm | Vai trò |
|---|---|
| `estimate_annual_inputs` | Tính μ và Σ năm hóa |
| `build_regime_problem` | Dựng bài toán có điều khiển chế độ và các tùy chọn đối chứng |
| `build_investable_problem` | Dựng V1: α cố định, AI chỉ đổi λ, có phí và tỷ trọng cũ |
| `build_ledoit_wolf_problem` | Dựng đối chứng hiệp phương sai Ledoit–Wolf |

### `agqo/problem.py`

| Hàm / lớp | Vai trò |
|---|---|
| `PortfolioProblem` | Lưu đầu vào, ràng buộc, mục tiêu, chi phí và doanh số |
| `Qubo`, `Ising` | Lưu các hệ số của hai biểu diễn nhị phân/Pauli |
| `build_qubo`, `to_ising` | Chuyển bài toán danh mục sang biểu diễn cho QAOA |
| `exact_solve`, `greedy_solve`, `anneal_solve` | Ba đối chứng cổ điển |
| `synthetic_problem` | Sinh bài toán tái lập bằng PCG64; không sinh dữ liệu thị trường |

### `agqo/simulator.py`, `agqo/aer.py`, `agqo/qpu.py`

| Hàm / lớp | Vai trò |
|---|---|
| `_basis_energies` | Tính trước năng lượng mọi trạng thái cơ sở |
| `_mix_x`, `_mix_xy_ring` | Áp dụng hai bộ trộn trong mô phỏng véc-tơ trạng thái |
| `statevector`, `optimize_qaoa`, `QaoaResult` | Chạy mô phỏng, tối ưu góc và lưu kết quả |
| `crosscheck_aer` | Đối chiếu mạch Aer với mô phỏng NumPy |
| `QpuConfig`, `load_qpu_config`, `validate_qpu_config` | Đọc và kiểm tra cấu hình thiết bị |
| `_update_ledger`, `_reserve_shots`, `_finalize_shots` | Khóa và ghi sổ ngân sách mẫu |
| `build_parameterized_circuit` | Tạo mạch có tham số β, γ |
| `_counts_energy`, `_two_qubit_gate_metrics` | Chấm mẫu và tính chỉ số mạch sau biên dịch |
| `run_qpu` | Gửi và đọc công việc lượng tử khi cấu hình/token cho phép |

### `agqo/evaluation.py`, `agqo/cli.py`

| Hàm | Vai trò |
|---|---|
| `_cost_matrix_bps` | Căn chi phí theo mã và kỳ |
| `simulate_monthly_portfolios` | Tính đường lợi nhuận ròng và thanh khoản |
| `summarize_monthly_returns` | Tính chỉ số lợi nhuận và rủi ro |
| `paired_block_bootstrap_mean_ci` | Khoảng tin cậy lấy mẫu khối |
| `compare_monthly_returns` | So sánh hai chiến lược trên tháng ghép cặp |
| `_save` | Ghi từng bản ghi JSONL |
| `_demo` | Chạy mẫu V1 hoặc so sánh với V0 |
| `_benchmark` | Chạy bộ H2 tổng hợp |
| `_qpu`, `main` | Điều khiển nhánh QPU và giao diện dòng lệnh |

`_save` ghi từng bản ghi thành một dòng JSONL trong thư mục `outputs/`; mặc định tên tệp dùng thời gian UTC. Bản chạy V1 trong báo cáo được gọi từ môi trường `.venv` và kết quả tóm tắt được đưa vào báo cáo, không lưu tệp kết quả tạm làm nguồn dữ liệu thị trường.

## 10. Tái lập đường chạy

Trong môi trường đã tạo theo `requirements-lock.txt`:

```bash
./.venv/bin/python -m agqo.cli demo \
  --n 8 \
  --model-version v1 \
  --transaction-cost-bps 25 \
  --max-evaluations 50 \
  --output outputs/agqo_v1_demo.jsonl
```

Lệnh này dùng dữ liệu tổng hợp. Để chạy bộ H2 đầy đủ theo giao diện hiện có, dùng `agqo benchmark --limit 12 --max-evaluations 50`; kết quả H2 trong thư mục `results/` là lượt chạy lịch sử trước V1. Nhánh QPU chỉ chạy khi cấu hình, token và quyền sử dụng thiết bị đã sẵn sàng; không bật gửi công việc trong tài liệu này.

## 11. Những phần cần phát triển tiếp

1. Bộ nhập dữ liệu có nguồn, quyền sử dụng, lịch thành phần lịch sử và kiểm tra sự kiện doanh nghiệp.
2. Bộ điều phối kiểm định cuốn chiếu tạo trọng số tháng từ dữ liệu tại thời điểm đó, không nhìn trước.
3. Mô hình khớp lệnh có phí, thuế, chênh lệch mua/bán, trượt giá, ADTV, lệnh khớp một phần và tác động giá.
4. Đối chuẩn tài chính chạy trên đúng cùng ngày, tài sản, chi phí và thời điểm khớp.
5. Tập bài toán lượng tử mới chưa dùng để chọn thiết kế; đối chiếu p = 1, 2, 3, nhiều trạng thái đầu và cấu trúc bộ trộn trong cùng ngân sách.
6. Nếu chạy thiết bị thật, ghi riêng thời gian hàng đợi, biên dịch, thời gian thiết bị, số cổng hai qubit, độ sâu hai qubit và kết quả có nhiễu.

## Tệp liên quan

- [Báo cáo kết quả đạt được](BAO_CAO_KET_QUA_AGQO.md)
- [Hướng dẫn sử dụng](README.md)
- [Đề cương nghiên cứu](AGQO_Final_Research_Proposal.md)
- [Kế hoạch hướng đến chung kết](KE_HOACH_CHOT_HUONG_DI_CHUNG_KET.md)
