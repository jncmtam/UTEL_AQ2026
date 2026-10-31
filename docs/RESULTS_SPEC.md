# Đặc tả kết quả và tiêu chí công bố AGQO

Phiên bản: results-spec-v1, ngày 31/10/2026.

## Đơn vị đánh giá

Một instance là một FinancialIR bất biến: universe, cửa sổ quá khứ, benchmark, vị thế đã drift, chi phí và mandate tại cutoff. Mỗi instance có `problem_hash`; Hamiltonian có hash riêng. Seed optimizer không tạo thêm instance tài chính độc lập.

Mỗi experiment có protocol đã khóa trước inference: model/revision/engine, prompt/schema hash, compiler/source hash, instance/split, candidate/retry cap, optimizer/shot budget, tiêu chí chọn và ngân sách tiền. Nếu đổi grammar sau khi xem lỗi, tạo protocol mới và ghi đó là tập phát triển đã mở.

## Trạng thái thực thi

| Trạng thái | Cách ghi nhận |
|---|---|
| live_modal_vllm | Có function receipt, model/revision khớp và raw response thật |
| cached_live_record / replay | Tái dùng output live cũ; không tính thành inference mới hoặc mẫu độc lập |
| rules / random | Baseline không LLM; không gán output này cho model |
| disabled / not_run | Chưa chạy; không tính là bằng chứng về chất lượng model |
| infrastructure_error | Chưa sinh được đề xuất do runtime/backend; vẫn tính chi phí, tách khỏi model semantic failure |
| invalid / truncated | Đề xuất thật nhưng không đạt; giữ trong mẫu và tổng chi phí |
| fallback | Ghi solver thật đã dùng, nguyên nhân và tài nguyên; không tính công của fallback cho QAOA |

## Bốn tầng kết quả

1. **Sinh chương trình:** first-pass validity và sau số vòng sửa cố định; schema, mapping, graph/design rules và full cost semantics riêng. Syntax đúng không đồng nghĩa quantum hoặc finance đúng.
2. **Mạch thực thi:** NumPy–Qiskit fidelity cho cùng candidate; norm, cardinality leak, parameter activity, compiled depth/CX và provenance. COST được tính sau lowering, không là một gate giá rẻ.
3. **Tối ưu tổ hợp:** xác suất mẫu khả thi, xác suất optimum/near-optimum, kỳ vọng objective, best feasible objective, gap tới exact/bound, và mọi failure.
4. **Tài chính ngoài mẫu:** tracking, turnover từ drift, phí giao dịch, compliance và hold-vs-repair. Không suy alpha từ tối ưu in-sample hoặc syntax benchmark.

Hàm mục tiêu hiện tại là tracking MSE + lambda × transaction cost; các giới hạn bắt buộc giữ nguyên giữa phương pháp. Gap chuẩn hóa theo khoảng objective của các nghiệm khả thi trong cùng instance. Nếu không có feasible sample thì gap unavailable và failure được tính vào đánh giá; không loại hàng đó để median đẹp hơn.

## Ngưỡng và so sánh

Ngưỡng G0–G4 gốc ở [SYNTHESIS_THRESHOLDS](SYNTHESIS_THRESHOLDS.md). Đây là mục tiêu dự án, không phải chỉ số paper được chuyển sang finance. Pilot ba bài chỉ chẩn đoán; qualification cần ít nhất 10 instance độc lập theo protocol gốc, cùng kiểm tra giới hạn thống kê và coverage.

G3 yêu cầu đối chứng cùng objective, dữ liệu, grammar và tổng ngân sách; giảm ít nhất 20% gap nếu baseline gap khác 0, hoặc giảm ít nhất 20% CX với gap không kém quá 1 điểm phần trăm và feasibility không giảm quá 1 điểm phần trăm. Một case đạt chưa là kết luận tổng quát. Baseline gap=0 không có phần trăm cải thiện gap hợp lệ.

Chất lượng phân phối là bắt buộc để diễn giải pilot nhỏ. Similarity với reference là chẩn đoán, không thay thế objective: circuit khác reference vẫn có thể tốt hơn về tài chính.

## Tài nguyên, artifacts và nguồn gốc

Tổng tài nguyên gồm mọi đề xuất, retry, inference, load/cold start, compiler, oracle preprocessing, tối ưu góc, shots và post-processing. Reservation là cận bảo thủ khác invoice. Metered/billed cả tháng khác chi phí experiment hoặc số dư credit.

Artifacts tối thiểu: protocol, raw request/response, receipt, verification, GateIR, seed runs, baselines, summary/report và chi phí. Artifact circuit thực thi gồm bound QASM, parameterized QASM/QPY nếu hỗ trợ, source map và transpile metadata. Cần lưu provenance LLM/compiler/classical solver riêng.

Paper chỉ là nguồn related work. Bảng kết quả AGQO chỉ chứa run của AGQO và ghi rõ synthetic/market, simulator/QPU, development/holdout. Coder480/397 hoặc checkpoint specialist chưa inference phải ghi **chưa chạy**, không mượn điểm benchmark chung để điền kết quả dự án.
