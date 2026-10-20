# AGQO: tối ưu danh mục với chuẩn đối chiếu lượng tử

Dự án nghiên cứu cách chọn danh mục cổ phiếu theo lợi suất, rủi ro và chi phí giao dịch; sau đó đối chiếu QAOA với nghiệm chính xác cổ điển. Đây là nguyên mẫu nghiên cứu, chưa phải hệ thống giao dịch hay khuyến nghị đầu tư.

## Kết quả chính

- **Dữ liệu thị trường:** 37.308 dòng OHLCV của 30 mã VN30, chỉ số VN30 và VN-Index; từ 04/01/2022 đến 19/10/2026.
- **Nghiệm trên rổ 30 mã:** bộ giải chính xác duyệt đủ 593.775 danh mục gồm sáu mã và chọn **HDB, SSB, GAS, SAB, VIC, VJC** trong 4,96 giây trên máy chạy hiện tại.
- **Đối chiếu lượng tử:** trên 36 bài toán tổng hợp, QAOA với bộ trộn X đạt ngưỡng ở 18 bài; bộ trộn XY đạt 0. Ngưỡng đã đăng ký là 29/36. Kết quả này chưa ủng hộ tuyên bố ưu thế lượng tử.
- **Phát hiện tài chính:** trong 252 phiên gần nhất, VN30 giảm 8,60%, VN-Index giảm 4,26%, danh mục đều 30 mã giảm 6,74%, trước chi phí.
- **Giới hạn quan trọng:** giá cổ phiếu chưa xác nhận đã điều chỉnh quyền/cổ tức; thành phần VN30 hiện tại được áp ngược vào lịch sử. Chưa có kiểm định ngoài mẫu hoặc lượt chạy QPU thật.

Kết quả đầy đủ, cách diễn giải từng biểu đồ và các giới hạn được trình bày trong [báo cáo phân tích](results/BAO_CAO_KET_QUA.md). Danh mục tối ưu dùng thống kê trong mẫu, không phải lợi nhuận đã đạt được hay dự báo.

## Bộ dữ liệu và nguồn

| Thuộc tính | Chi tiết |
|---|---|
| Phạm vi | 30 mã cổ phiếu, VN30 và VN-Index |
| Số dòng | 37.308 dòng OHLCV ngày |
| Khoảng ngày dữ liệu | 04/01/2022–19/10/2026 |
| Ngày chụp rổ VN30 | 02/10/2026; danh sách bên thứ ba, không phải lịch thành phần lịch sử của HOSE |
| Ngày tải | 20/10/2026 lúc 09:28 UTC (16:28 giờ Việt Nam) |
| Thư viện lấy dữ liệu | [`vnstock-data`](https://github.com/nguyenthdat/vnstock-data), mã nguồn `d6bafb23dd02f3f63273f12b1f3e3949877b2242` |
| Nguồn giá được thư viện gọi | [DNSE chart API](https://services.entrade.com.vn/chart-api/v2/ohlcs) |
| Nguồn danh sách mã | [HODL.VN](https://www.hodl.vn/bai-hoc/vn30-gom-nhung-ma-nao), bản chụp ngày 02/10/2026 |
| Tệp kê khai và mã băm | [`manifest.json`](data/vn30_snapshot_20261002/manifest.json) |
| Danh sách mã | [`members.csv`](data/vn30_snapshot_20261002/members.csv) |

### Các mốc thời gian trong dữ liệu

| Ngày | Mốc |
|---|---|
| 04/01/2022 | Phiên đầu tiên có trong dữ liệu của phần lớn mã và hai chỉ số |
| 13/05/2025 | Phiên đầu tiên có dữ liệu của VPL; vì vậy lịch sử 30 mã không đồng đều |
| 14/10/2025 | Bắt đầu cửa sổ 252 phiên hoàn chỉnh dùng cho phân tích gần nhất |
| 02/10/2026 | Ngày chụp danh sách thành phần VN30 dùng trong dự án |
| 13/10/2026 | Chạy bộ đối chiếu QAOA H2 trên bài toán tổng hợp |
| 19/10/2026 | Ngày cuối của dữ liệu giá đã lưu |
| 20/10/2026 | Tải bộ dữ liệu cố định, lập báo cáo và biểu đồ |

### Cách xử lý dữ liệu

1. Bộ tải gọi `stock_historical_data` cho 30 cổ phiếu, VN30 và VNINDEX.
2. Nếu nguồn trả nhiều đoạn nến cho cùng ngày, gộp thành một nến ngày: giá mở cửa đầu tiên, giá cao nhất, giá thấp nhất, giá đóng cửa cuối cùng và tổng khối lượng.
3. Kiểm tra mã trùng, giá không dương, khối lượng âm và cấu trúc cột OHLCV; lưu độ phủ và mã băm SHA-256 trong tệp kê khai.
4. Căn chỉnh cổ phiếu theo các phiên có đủ dữ liệu cho cả 30 mã; tính lợi suất đóng cửa, biến động, sụt giảm, tương quan và giá trị giao dịch xấp xỉ.
5. Dùng 252 phiên hoàn chỉnh gần nhất làm đầu vào cho nghiệm danh mục. Kết quả và biểu đồ được dựng từ cùng bộ dữ liệu.

**Giới hạn quyền dữ liệu:** thư viện lấy dữ liệu là mã nguồn mở, nhưng giấy phép của thư viện không cấp quyền phân phối lại dữ liệu thị trường. Vì vậy, tệp OHLCV đầy đủ được giữ trong bản làm việc cục bộ và không đưa vào GitHub. Mã tải dữ liệu, tệp kê khai, danh sách mã và các kết quả tổng hợp được lưu trong kho. Hãy kiểm tra điều khoản của nhà cung cấp trước khi công bố hoặc phân phối dữ liệu thô.

Để tải lại bộ dữ liệu vào thư mục mặc định:

```bash
python -m pip install -r requirements-data.txt
python scripts/download_vn30_dataset.py
```

Lệnh phân tích yêu cầu tệp `data/vn30_snapshot_20261002/ohlcv_daily.csv` đã có tại chỗ. Tải lại dữ liệu phụ thuộc dịch vụ bên ngoài; giá có thể thay đổi khi nguồn cập nhật lịch sử.

## Nhận định tài chính trên 252 phiên gần nhất

Các con số dưới đây là lợi suất giá đóng cửa **trước chi phí**, trong chính cửa sổ được dùng để ước lượng đầu vào. Danh mục đều 30 mã được tái cân bằng mỗi phiên chỉ là đường tham chiếu mô tả, không phải chiến lược được kiểm định ngoài mẫu.

| Chuỗi | Lợi suất gộp | Biến động năm hóa | Sụt giảm tối đa | Tỷ lệ phiên tăng |
|---|---:|---:|---:|---:|
| VN30 | -8,60% | 20,44% | -16,96% | 47,22% |
| VN-Index | -4,26% | 20,36% | -16,38% | 49,60% |
| Danh mục đều 30 mã, tái cân bằng mỗi phiên | -6,74% | 19,33% | -16,49% | 54,37% |

**Diễn giải:** cả ba chuỗi đều giảm trong cửa sổ này. Danh mục đều giảm ít hơn VN30 nhưng nhiều hơn VN-Index; tỷ lệ phiên tăng cao hơn vẫn không ngăn được lợi suất gộp âm. Đây là ví dụ vì sao không thể dùng tỷ lệ phiên tăng riêng lẻ để kết luận hiệu quả đầu tư.

### Phân tán lợi suất giữa các mã

| Nhóm | Mã | Lợi suất gộp | Biến động năm hóa | Sụt giảm tối đa | Giá trị giao dịch xấp xỉ (tỷ đồng/ngày) |
|---|---|---:|---:|---:|---:|
| Tăng mạnh | VIC | 101,56% | 51,19% | -32,07% | 804,6 |
| Tăng mạnh | GAS | 30,24% | 49,68% | -49,96% | 169,9 |
| Tăng mạnh | HDB | 17,45% | 31,55% | -18,86% | 301,5 |
| Tăng mạnh | VJC | 16,24% | 39,08% | -30,72% | 204,9 |
| Tăng mạnh | GVR | 11,57% | 47,80% | -43,17% | 125,5 |
| Giảm mạnh | DGC | -56,67% | 47,00% | -62,42% | 158,2 |
| Giảm mạnh | VRE | -44,50% | 49,27% | -49,18% | 235,2 |
| Giảm mạnh | SHB | -40,86% | 27,17% | -44,26% | 871,4 |
| Giảm mạnh | SSI | -34,22% | 35,13% | -41,70% | 606,8 |
| Giảm mạnh | FPT | -31,56% | 32,06% | -40,83% | 675,7 |

> Lợi suất cổ phiếu tính từ giá thô, chưa xác nhận điều chỉnh cổ tức, chia tách hoặc quyền mua. Giá trị giao dịch là xấp xỉ `giá đóng cửa × khối lượng`, không phải giá trị khớp lệnh do sở giao dịch xác nhận.

### Tương quan và mức tập trung

- 14/30 mã thuộc nhóm ngân hàng (46,7% theo số mã). Rổ chọn sáu mã có thể giữ lại rủi ro chung của ngành nếu chỉ xếp hạng từng cổ phiếu độc lập.
- Tương quan cặp trung bình là **0,305**, trung vị **0,264**. Các mã không biến động độc lập; ma trận hiệp phương sai có vai trò trực tiếp trong kiểm soát rủi ro danh mục.
- Cặp tương quan cao nhất: BID–VCB (**0,813**), GAS–PLX (**0,809**), CTG–MBB (**0,741**), TPB–VIB (**0,737**), BID–CTG (**0,733**).
- Cặp tương quan thấp nhất: GVR–VIC (**-0,047**), PLX–VHM (**-0,043**), GVR–VHM (**-0,018**), PLX–VIC (**-0,011**), VIC–VNM (**-0,004**).

## Bài toán danh mục và biện luận

### Kết quả trên dữ liệu thị trường

| Thiết lập | Kết quả |
|---|---|
| Vũ trụ / số mã chọn | N=30, K=6; chia đều tỷ trọng trong các mã được chọn |
| Hàm mục tiêu | Phạt phương sai, thưởng lợi suất ước lượng và tính phí giao dịch |
| Hệ số ngại rủi ro | λ=5,0 |
| Co rút hiệp phương sai | α=0,40 |
| Phí | 25 điểm cơ bản cho một lần mua từ tiền mặt; chưa mô phỏng tái cân bằng định kỳ |
| Bộ giải | Duyệt chính xác mọi tổ hợp khả thi |
| Số tổ hợp đã xét | C(30,6) = 593.775 |
| Thời gian trên máy hiện tại | 4,96 giây |
| Nghiệm | **HDB, SSB, GAS, SAB, VIC, VJC** |
| Lợi suất trung bình lịch sử năm hóa của nghiệm | 29,43% |
| Biến động mô hình năm hóa | 18,85% |

Điểm mục tiêu gồm phạt rủi ro năm hóa **0,17773**, phần thưởng lợi suất **-0,29435** và phí giả định **0,00250**, tổng điểm **-0,11412**. Nghiệm chính xác chứng minh rằng bộ giải đã tìm cực tiểu toàn cục **cho đúng hàm mục tiêu và ước lượng trong mẫu này**. Con số 29,43% là trung bình lịch sử dùng trong mục tiêu, không phải lợi nhuận thực tế, kết quả kiểm định ngoài mẫu hay cam kết cho tương lai.

### Kiểm tra phương pháp V1 trên dữ liệu tổng hợp nhỏ

Thí nghiệm riêng dùng N=8, K=6, hạt giống 20261012; xác suất trạng thái biến động 0,70 chỉ đặt để minh họa, không phải dự báo từ mô hình. V1 cố định α=0,40, dùng λ=7,60, phí giả định 25 điểm cơ bản và 12 lần tái cân bằng năm hóa.

| Bộ giải | Kết quả |
|---|---|
| Duyệt chính xác | SYN00, SYN02, SYN03, SYN04, SYN06, SYN07; điểm mục tiêu sau phí -0,00698667 |
| Tham lam | Tìm cùng danh mục với nghiệm chính xác |
| Tôi luyện | Tìm cùng danh mục với nghiệm chính xác |
| QAOA, bộ trộn X | Đúng nghiệm ở 2/3 hạt giống |
| QAOA, bộ trộn XY | 0/3 lượt đúng nghiệm; độ lệch trung vị 24,93% |

Phí làm điểm mục tiêu tăng 0,02000000 nhưng không đổi nghiệm trong ví dụ này. Bài toán nhỏ và ba hạt giống chỉ xác nhận đường chạy, không đủ để kết luận chất lượng trên thị trường.

### Đối chiếu QAOA trên 36 bài toán tổng hợp

Thiết kế dùng QAOA độ sâu p=1, K=6, N=8/12/16, ba hạt giống 11/23/47, 512 mẫu mỗi lần đánh giá, tối đa 36 lần đánh giá mỗi lượt. Có 72 cấu hình bộ trộn (216 lượt tối ưu); tổng thời gian mô phỏng cổ điển 13,11 giây. Một cấu hình được tính là đạt nếu cả ba lượt có nghiệm khả thi và độ lệch chuẩn hóa trung vị không quá 5%. Ngưỡng đăng ký trước là 29/36.

| Bộ trộn | Đạt ngưỡng | Độ lệch trung vị | Khả thi ở cả ba lượt |
|---|---:|---:|---:|
| X | 18/36 | 4,22% | 36/36 |
| XY | 0/36 | 29,57% | 36/36 |

| Kích thước N | X đạt | Độ lệch X | XY đạt | Độ lệch XY |
|---:|---:|---:|---:|---:|
| 8 | 12/12 | 0,00% | 0/12 | 20,31% |
| 12 | 6/12 | 4,22% | 0/12 | 31,53% |
| 16 | 0/12 | 13,44% | 0/12 | 32,83% |

**Biện luận kỹ thuật:** bộ trộn XY giữ đúng số mã trong các mẫu đã đo nhưng chưa tìm được nghiệm đủ tốt; bộ trộn X giảm chất lượng khi tăng N. Cả hai đều không đạt ngưỡng tổng thể. Trên N=30, bộ giải chính xác cổ điển đã giải bài toán trong vài giây; QAOA mô phỏng véc-tơ trạng thái không chạy trên đủ 30 mã. Vì vậy, lợi thế đã chứng minh hiện nay là nghiệm chuẩn chính xác và quy trình đo được, chưa phải ưu thế lượng tử. Chưa chạy QPU thật.

Bản ghi đầy đủ theo cấu hình và hạt giống: [`qaoa_h2_20261013.jsonl`](results/qaoa_h2_20261013.jsonl).

## Hình ảnh và câu chuyện dữ liệu

Các biểu đồ dưới đây được dựng từ bản dữ liệu đã lưu và 252 phiên phân tích, trừ biểu đồ QAOA dùng bài toán tổng hợp. Mọi diễn giải lợi suất cổ phiếu cần lưu ý giá thô và thiên lệch sống sót.

### 1. Độ phủ dữ liệu

![Độ phủ dữ liệu theo thời gian](results/figures/vn30/01_coverage.png)

Các khoảng trống biểu thị thời kỳ mã chưa có dữ liệu; VPL có lịch sử ngắn hơn phần lớn rổ.

### 2. Diễn biến chỉ số

![Diễn biến VN30 và VN-Index](results/figures/vn30/02_indices.png)

Chuẩn hóa chỉ số về 100 để so xu hướng và mức sụt giảm từ đỉnh.

### 3. Rủi ro và lợi suất theo mã

![Rủi ro và lợi suất theo mã](results/figures/vn30/03_risk_return.png)

Đặt lợi suất cạnh biến động giúp thấy lợi suất cao có thể đi cùng rủi ro lớn; kích thước điểm là giá trị giao dịch xấp xỉ, ngôi sao đánh dấu nghiệm tối ưu.

### 4. Xếp hạng lợi suất

![Xếp hạng lợi suất 30 mã](results/figures/vn30/04_returns_rank.png)

Cho thấy độ phân tán lớn giữa các mã; nghiệm sáu mã được tô màu riêng.

### 5. Tương quan

![Ma trận tương quan các mã](results/figures/vn30/05_correlations.png)

Những cụm tương quan cao làm rõ rủi ro chung mà việc xếp hạng từng mã có thể bỏ qua.

### 6. Thanh khoản xấp xỉ

![Giá trị giao dịch xấp xỉ](results/figures/vn30/06_liquidity.png)

Ước tính từ giá đóng cửa nhân khối lượng; dùng trục lôgarit để thể hiện các quy mô khác nhau.

### 7. Chế độ rủi ro thị trường

![Biến động trượt 60 phiên của hai chỉ số](results/figures/vn30/07_risk_regimes.png)

Biến động thay đổi theo thời gian; một tham số rủi ro cố định có thể không phản ánh mọi giai đoạn.

### 8. Cấu phần nghiệm danh mục

![Cấu phần mục tiêu và sáu mã được chọn](results/figures/vn30/08_optimizer.png)

Tách phần phạt rủi ro, thưởng lợi suất và chi phí để giải thích vì sao nghiệm tối ưu không chỉ chọn sáu mã tăng mạnh nhất.

### 9. Chuẩn QAOA

![Kết quả đối chiếu QAOA](results/figures/vn30/09_qaoa_benchmark.png)

Độ lệch, tỷ lệ đạt và thời gian mô phỏng theo kích thước bài toán tổng hợp; thời gian này không phải thời gian QPU.

## Công nghệ và cách tái lập

| Thành phần | Công nghệ / chức năng |
|---|---|
| Ngôn ngữ | Python 3.12 |
| Tính toán số | NumPy, SciPy |
| Xử lý dữ liệu | pandas |
| Mô hình chế độ rủi ro | scikit-learn; mã có hồi quy logistic, nhưng chưa có kết quả dự báo ngoài mẫu được báo cáo |
| Tối ưu cổ điển | Duyệt chính xác, tham lam, tôi luyện mô phỏng |
| Mô phỏng QAOA | Mô phỏng véc-tơ trạng thái bằng NumPy, COBYLA tối ưu góc, bộ trộn X và XY |
| Mạch lượng tử | Qiskit và Qiskit Aer cho biên dịch/đối chiếu cục bộ |
| Phần cứng lượng tử | IBM Quantum Runtime tùy chọn; chưa dùng để tạo kết quả trong báo cáo |
| Biểu đồ | Matplotlib |
| Mô hình ngôn ngữ lớn | Không được gọi trong đường chạy; không sinh tín hiệu giao dịch |

Cài đặt môi trường từ thư mục dự án:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

Sau khi có tệp OHLCV cục bộ, dựng lại báo cáo và chín hình:

```bash
python -m agqo.cli market-data
```

Chạy ví dụ tổng hợp hoặc dựng lại bộ đối chiếu QAOA:

```bash
agqo demo --n 8 --model-version v1
agqo benchmark --limit 12 --max-evaluations 50
```

Lệnh QPU chỉ gửi công việc khi có cấu hình, thông tin xác thực và cờ `--submit`.

## Cấu trúc dự án

```text
agqo/                         mô hình, hàm mục tiêu, bộ giải, phân tích và biểu đồ
config/                       cấu hình mẫu cho QPU
data/vn30_snapshot_20261002/  kê khai và danh sách mã; OHLCV đầy đủ chỉ lưu cục bộ
results/                      báo cáo, chín hình và nhật ký QAOA tổng hợp
scripts/                      bộ tải dữ liệu thị trường
tests/                        kiểm tra công thức và bộ giải
```

## Tài liệu chi tiết

- [Báo cáo phân tích đầy đủ](results/BAO_CAO_KET_QUA.md)
- [Tài liệu kỹ thuật: công nghệ, hàm và quy trình](TAI_LIEU_KY_THUAT_AGQO.md)
- [Kê khai dữ liệu, độ phủ và mã băm](data/vn30_snapshot_20261002/manifest.json)
