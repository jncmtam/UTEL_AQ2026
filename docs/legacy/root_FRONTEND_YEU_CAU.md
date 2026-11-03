# Đề bài frontend cho AGQO

**Mục tiêu:** dựng giao diện trình bày và khám phá kết quả của pipeline AGQO: dữ liệu thị trường → insight định lượng → Qwen hướng dẫn cấu hình → bộ giám sát → QAOA chọn danh mục → đối chứng cổ điển → kiểm định tài chính. Giao diện phải giúp người xem hiểu được cả quyết định và mức độ bằng chứng, không biến kết quả nghiên cứu thành lời hứa lợi nhuận.

## 1. Người dùng và câu hỏi giao diện phải trả lời

Ban giám khảo hoặc thành viên nhóm cần trả lời nhanh:

1. Dữ liệu nào được dùng, cho giai đoạn nào, và dữ liệu có điểm hạn chế gì?
2. Thị trường đang ở trạng thái nào; insight nào được số liệu hỗ trợ?
3. LLM nhận đầu vào gì, chọn cấu hình nào, dựa trên bằng chứng nào; bộ giám sát có giữ hay thay đề xuất?
4. QAOA đã giải bài toán gì, với bao nhiêu qubit, độ sâu, mixer, bố trí cổng; nghiệm so với exact/greedy ra sao?
5. Kết quả đầu tư sau phí so với VN30, VN-Index và các đối chứng thế nào?
6. Phần nào là kết quả đã đo, phần nào là mã đã chuẩn bị nhưng chưa được chạy lại?

## 2. Phạm vi bản đầu

- Một trang web thích ứng máy tính và điện thoại, ưu tiên trình chiếu trên màn hình lớn.
- Bản đầu có thể đọc trực tiếp các JSON/CSV/PNG tĩnh trong kho dự án; không cần dựng dịch vụ backend mới.
- Nếu cần API, frontend định nghĩa lớp nạp dữ liệu riêng để sau này thay nguồn tĩnh bằng API mà không viết lại thành phần hiển thị.
- Không cần tài khoản, giao dịch thật, khuyến nghị mua bán, hoặc chỉnh tham số mô hình trực tiếp.
- Không tạo số liệu giả để lấp phần thiếu. Giá trị rỗng phải thể hiện là “chưa có dữ liệu/chưa chạy”.

## 3. Các màn hình / khu vực đề xuất

### A. Tóm tắt điều hành

- Tên AGQO và mô tả một câu: “AI hướng dẫn lựa chọn cấu hình; QAOA tạo danh mục; bộ giải cổ điển và kiểm định tài chính đo chất lượng.”
- Thẻ trạng thái bằng chứng: **kết quả cũ**, **pipeline hiệu chỉnh chưa chạy lại**, **tin tức chưa được dùng**, **QAOA mô phỏng CPU**.
- KPI giai đoạn cũ: CAGR ròng, Sharpe, sụt giảm tối đa, giá trị cuối; đặt cạnh VN30, VN-Index, quy tắc → QAOA và exact cổ điển.
- Hiển thị rõ hơn/kém bao nhiêu điểm phần trăm và một câu diễn giải bằng ngôn ngữ thường.
- Không tô “xanh thắng cuộc” cho AGQO nếu số liệu không thắng benchmark.

### B. Câu chuyện thị trường và dữ liệu

- Đường giá chuẩn hóa của VN30/VN-Index và các chiến lược; bộ lọc giai đoạn.
- Bản đồ lợi suất theo mã/tháng, ma trận tương quan, lợi suất/rủi ro, thanh khoản và độ phủ dữ liệu.
- Bộ lọc ngày tín hiệu để xem volatility, trend, độ rộng, phân tán chéo, tương quan và xác suất chế độ biến động.
- Tooltip giải nghĩa từng chỉ số, cửa sổ tính, đơn vị, thời điểm dữ liệu khả dụng.
- Cờ dữ liệu: ảnh chụp thành phần lịch sử, giá OHLCV chưa xác nhận điều chỉnh, tin tức không khả dụng do GDELT trả 429.

### C. Trình xem quyết định AGQO

Với mỗi kỳ tín hiệu, trình bày theo thứ tự:

1. Ngày chốt thông tin và ngày vào/ra lệnh.
2. Insight định lượng và mã bằng chứng.
3. Đề xuất Qwen: mã chính sách, model/revision, prompt version, token, có dùng cache hay không.
4. Kết quả giám sát: giữ hay thay; lý do và các ngưỡng kiểm tra.
5. Cấu hình QAOA được chạy: N qubit, K mã, mixer X/XY, layout, p, shots, seed.
6. Rổ cổ phiếu được chọn và tỷ trọng/lượng nắm nếu có trong dữ liệu kết quả.
7. Kết quả QAOA so với nghiệm chính xác/greedy: objective, regret, feasible-shot rate, runtime.
8. Kết quả tài chính: gross/net return, phí, turnover, phần lệnh không khớp và benchmark.

### D. Phòng thí nghiệm QAOA

- Chọn kỳ và cấu hình để so sánh N=8/12/16, mixer X/XY, p, layout.
- Hiển thị circuit/đồ thị cổng từ metadata đã lưu; ánh xạ qubit ↔ ticker; cost edges và mixer edges.
- KPI riêng cho thuật toán: hối tiếc mục tiêu, tỷ lệ khả thi, số cổng hai qubit, độ sâu logic, thời gian mô phỏng.
- Nhãn thường trực: “statevector chạy trên CPU; chưa chạy phần cứng lượng tử”.
- Không nhầm hối tiếc objective với lợi nhuận tài chính.

### E. Nhật ký bằng chứng và giới hạn

- Bảng quyết định có thể lọc/tải xuống CSV.
- Nguồn, hàm băm, dấu thời gian, phiên bản prompt/model và tham số chạy.
- Nhật ký các giới hạn cùng trạng thái: đã cài đặt trong mã / đã tải dữ liệu / đã tính kết quả / chưa xử lý.
- Tin tức phải hiện là “không tham gia kết quả” nếu manifest chưa có dữ liệu hoàn chỉnh.

## 4. Nguồn dữ liệu đang có trong dự án

- `results/final/agqo_final_walkforward.json`: cấu hình, hiệu quả danh mục, dự báo, các lần chạy QAOA và hướng dẫn AI. Đây là kết quả cũ, không phải kết quả đã hiệu chỉnh.
- `results/final/agqo_tail_probe_20261019.json`: chẩn đoán 12 phiên cho quyết định 30/09/2026; không phải phép thử mù.
- `results/final/dataset_summary.json`: thống kê dữ liệu/độ phủ và insight mô tả.
- `results/final/circuit_metadata.json`: ánh xạ mã-qubit, thiết kế cost/mixer và thông tin mạch đã chạy.
- `results/final/qwen3_decisions.json`: đầu ra Qwen đã lưu, prompt/model/revision/token.
- `results/final/figure_catalog.json` và `results/final/figures/`: ảnh biểu đồ đã dựng.
- `data/vn30_snapshot_20261002/vn30_membership_history.csv` và `vn30_membership_events.csv`: lịch thành phần được tổng hợp trong bản sửa gần nhất; chưa tái chạy walk-forward với dữ liệu đã điều chỉnh.
- `data/news/manifest.json`, `gdelt_metadata.csv`: trạng thái thu thập tin hiện rỗng, HTTP 429.

## 5. Hợp đồng dữ liệu frontend đề nghị

Chuẩn hóa thành một đối tượng `DashboardData` (có thể tạo adapter từ các tệp hiện có):

```ts
type DashboardData = {
  provenance: { generatedAt: string; sourceFiles: string[]; runStatus: "legacy_result" | "corrected_pending" | "corrected_complete" };
  caveats: Array<{ id: string; status: "measured" | "implemented_not_rerun" | "unavailable"; message: string }>;
  summary: Array<{ strategy: string; cagrNet: number | null; sharpe: number | null; maxDrawdown: number | null; terminalValue: number | null }>;
  equitySeries: Array<{ date: string; strategy: string; nav: number }>;
  marketInsights: Array<{ asOf: string; key: string; value: number | string | null; unit: string; interpretation: string; evidenceId?: string }>;
  decisions: Array<{ signalDate: string; llmPolicy: string; executedPolicy: string; guardrailReason?: string; insightCodes: string[]; evidenceIds: string[]; qaoaConfig: { nQubits: number; k: number; mixer: string; layout: string; depth: number; shots: number }; selectedTickers: string[]; qaoa: { regret: number | null; feasibleRate: number | null; runtimeSeconds: number | null; twoQubitGates?: number }; finance: { netReturn: number | null; fees: number | null; turnover: number | null } }>;
  figures: Array<{ id: string; title: string; caption: string; path: string; source: string }>;
  news: { status: "available" | "unavailable"; count: number; explanation: string };
};
```

Giữ giá trị tài chính ở dạng số gốc trong adapter; định dạng phần trăm/tiền chỉ ở lớp trình bày. Không suy ra trường bị thiếu bằng cách đoán.

## 6. Tiêu chí nghiệm thu

- Một người mới có thể giải thích được pipeline trong 60 giây chỉ bằng trang tổng quan.
- Từ KPI có thể đi tới kỳ tín hiệu và bằng chứng gốc liên quan.
- Luôn phân biệt số liệu tài chính với metric solver; thể hiện benchmark và dấu âm/dương rõ ràng.
- Tất cả chart có tiêu đề, đơn vị, chú giải, thời gian, nguồn và mô tả ngắn; trạng thái thiếu dữ liệu nhìn thấy được.
- Không có biểu đồ nhiệt một màu do chọn sai metric hoặc do thiếu dữ liệu mà không cảnh báo.
- UI hoạt động ở màn hình trình chiếu 16:9 và độ rộng điện thoại; tương phản màu đủ tốt, không chỉ dựa vào màu để biểu thị kết quả.
- Không làm hỏng đường dẫn ảnh tương đối trong kho; kiểm tra tất cả biểu đồ trên bản build.
- Có README ngắn: cách chạy, cấu trúc component, mapping trường dữ liệu.

## 7. Gợi ý chia việc

- **Frontend 1 — Tổng quan & câu chuyện hiệu quả:** KPI, benchmark, equity curves, trạng thái bằng chứng.
- **Frontend 2 — Insight & dữ liệu:** dashboard thị trường, bản đồ lợi suất/tương quan/độ phủ, bộ lọc ngày.
- **Frontend 3 — AI/QAOA explorer:** decision trace, guardrail, cấu hình/qubit/circuit, so sánh với exact.
- **Frontend 4 hoặc người tích hợp — Data adapter & QA:** adapter từ JSON/CSV, types, trạng thái lỗi/thiếu dữ liệu, điều hướng và kiểm tra giao diện.

Nếu nhóm ít người, gộp nhiệm vụ 1+2 và 3+4. Chốt giao diện/API contract trước khi chia component; làm từ dữ liệu đã lưu trước, sau đó thay sang dữ liệu hiệu chỉnh khi backtest mới có.
