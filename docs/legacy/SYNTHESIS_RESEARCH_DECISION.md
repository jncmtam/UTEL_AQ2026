# Quyết định nghiên cứu và thí nghiệm tiếp theo

Ngày 31/10/2026. Giao thức v2 được xác định **sau khi xem lỗi v1**, trước khi gọi GPU cho v2. Đây là cải tiến trên tập phát triển đã mở, không phải kiểm tra độc lập.

## Vấn đề đã đo được

Pilot v1 cho phép model sinh cổng riêng lẻ. Next-80B đúng 1/3 instance; Coder-30B đúng 0/3. Sau hai vòng phản hồi, tỷ lệ không tăng. Lỗi gồm H dùng hai qubit hoặc có góc quay, mixer thiếu chứng cứ ghép RXX–RYY, và basis có số bit 1 khác K. JSON hợp lệ không bảo đảm ngữ nghĩa quantum. Mạch N=4 hợp lệ vẫn có tham số không hoạt động; best-of-shots đạt optimum chưa chứng minh phân phối tốt.

Đây là bằng chứng chống việc giải quyết lỗi chỉ bằng tăng số tham số model hoặc tiếp tục retry. Chưa model nào đủ điều kiện làm model chính thức.

## Công trình quyết định hướng đi

- [Agent-Q, QCE 2025](https://arxiv.org/html/2504.11109v2): 85,5% syntax trên 200 bài test; các phép đo cú pháp và chất lượng tối ưu là khác nhau. AGQO không dùng tỷ lệ này làm lời bảo đảm correctness hoặc mục tiêu lợi nhuận.
- [QCircuitBench, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/3e343c7fa87656d7e88e9a83cb2a5d10-Paper-Datasets_and_Benchmarks_Track.pdf): kết hợp sinh chương trình với verification; lỗi model có tính lặp lại, fine-tuning không luôn hơn few-shot. Vì vậy ưu tiên biểu diễn và tập lỗi trước fine-tuning.
- [XY topology và warm starting](https://arxiv.org/html/2505.18396v2): ràng buộc cardinality có cấu trúc exchange; topology và parameterization cần được đánh giá riêng. Kết quả trainability của tập generator hạn chế không suy rộng sang COST đầy đủ của AGQO.
- [Evaluator-guided circuit discovery, preprint 15/10/2026](https://arxiv.org/abs/2610.22367): LLM đề xuất, evaluator độc lập kiểm tra và chấm. Vì đã có prior art, bản thân vòng LLM–verifier không đủ làm novelty.
- [Extensive Portfolio Benchmark, v3 07/10/2026](https://arxiv.org/html/2509.17876v3): MIP và heuristic chuyên biệt rất mạnh trên biến thể portfolio của bài. Do đó phải giữ đối chứng cổ điển và không dùng greedy yếu làm chuẩn duy nhất.
- Công trình sát nghiệp vụ: [Direct indexing với XY và Trotterized initialization, 02/2026](https://arxiv.org/html/2602.14827v1) đã có Dicke initialization, cardinality-preserving mixer và walk-forward trên 10 cổ phiếu. Table III báo Sharpe 1,81, nhưng turnover tháng 76,8%; tác giả đề xuất đưa turnover vào objective. Đây là kết quả của bài, không phải kết quả AGQO hay ngưỡng cần sao chép. Bài dùng risk–return selection rồi phân bổ liên tục; AGQO đang kiểm tra equal-weight tracking–cost và thay đổi mandate. Không nhận “direct indexing + XY” là khoảng trống.

**Suy luận thiết kế của dự án:** dùng grammar có kiểu cho khối exchange là cách xử lý trực tiếp các lỗi v1. Các paper trên định hướng cấu trúc kiểm chứng và đối chứng; chúng không báo kết quả cho grammar hoặc mandate của AGQO.

## V2: giới hạn cú pháp để nghiên cứu phần có ý nghĩa

LLM nhận FinancialIR, DataProfile và danh sách cạnh hợp lệ. Nó quyết định:

1. Cạnh trao đổi để tạo superposition trước COST.
2. Các cạnh và thứ tự mixer, tạo một đồ thị liên thông trên qubit tự do.
3. Nhóm dùng chung beta cho từng cạnh.

Compiler giữ basis có K tài sản, khóa bit include/exclude, COST và tên tham số. Mỗi EXCHANGE được hạ thành RXX(2β), RYY(2β) liền nhau. Khởi tạo dùng một cạnh occupied–empty với góc cố định 0,37 rad; không coi đây là relaxation warm-start của Egger. Không tự sửa đồ thị sai, không thay mạch LLM bằng baseline.

V2 nghiên cứu một lớp mạch hẹp hơn v1. Mạch vẫn được xuất ở mức cổng thực. Tính đúng đến từ grammar/compiler và verifier, không được quy toàn bộ cho năng lực quantum của LLM. Include/exclude được bảo toàn thêm theo thiết kế; sector/turnover vẫn phải kiểm tra bằng objective và nghiệm. Giữ N qubit, chưa loại qubit frozen khỏi COST.

## Thí nghiệm đã khóa trước lượt gọi mới

- Cùng ba bài phát triển N=4,6,8; cùng objective/hash như v1.
- Một đề xuất mỗi model mỗi bài; **không retry trả phí**. Output tối đa 1.536 token.
- Next-80B/H200 và Coder-30B/A100 chạy tuần tự, revision giữ nguyên.
- Mỗi mạch hợp lệ: ba seed 11/23/47, tối đa 16 lần đánh giá × 128 shots, cộng 128 shots đo cuối mỗi seed.
- Baseline fixed path, correlation path và một random path: cùng grammar, basis, COST, preparation budget, số lớp, seed và optimizer budget. Random chỉ một kiến trúc, không best-of-many.
- Kiểm schema/graph → analytic conservation → NumPy/Qiskit fidelity → gamma activity → tối ưu góc → tài chính/tài nguyên. Dừng nếu kiểm chứng không đạt.
- Giữ nguyên G0–G4 trong [ngưỡng đăng ký](SYNTHESIS_THRESHOLDS.md). Báo thêm P(optimum), P(gap ≤5%) và kỳ vọng objective có điều kiện, vì best-of-128 dễ đạt optimum ở không gian nhỏ. Các chỉ số bổ sung là chẩn đoán, chưa phải tiêu chí đăng ký trước của v1.
- Reservation v1 là 19,01 USD gồm lỗi hạ tầng đã tính. V2 thêm tối đa 4,90 USD, tổng 23,91 USD <25 USD; ledger còn kiểm tra billing tháng và buffer. Không mặc định credit còn lại bằng 30 USD.

`results/synthesis/typed_pilot/protocol.json` khóa request hashes, model revision, ngân sách, seed và stop rule trước inference. Raw output và mọi lỗi được lưu.

## Các cổng quyết định sau pilot

1. **V2 vẫn sai:** xử lý lỗi compiler/schema/model cụ thể trước, không mở benchmark rộng.
2. **V2 đúng nhưng không hơn rules/random:** giữ grammar làm hạ tầng, chưa tuyên bố LLM hữu ích cho circuit design. Không chọn model dựa trên kích thước.
3. **V2 có tín hiệu:** chọn model có cost–quality tốt hơn; khóa prompt/compiler rồi mới chạy tối thiểu 10 bài độc lập, ablation profile đầy đủ/bỏ correlation/tráo profile. Chi phí phải bao gồm tìm cấu hình và inference.
4. **Chỉ thắng best-of-shots:** kiểm tra phân phối, uniform feasible sampling và kỳ vọng cost; chưa tăng depth chỉ để tạo đường biểu diễn đẹp.
5. **LLM chỉ giúp circuit nhưng kém MILP:** báo đóng góp phương pháp, không báo cải thiện tài chính hay quantum advantage.

Nghiên cứu tiếp theo đáng làm là: cấu trúc dữ liệu có giúp LLM chọn exchange schedule và chia sẻ tham số **tốt hơn baseline cùng grammar trên mandate chưa thấy** không? Hướng này có thể bị bác bỏ bằng ablation; chưa được khẳng định là research gap độc quyền. Chưa dùng simulated N≤8 để suy lợi ích quỹ đầu tư hoặc tốc độ QPU.

## Các phương pháp nâng cao: thứ tự ưu tiên và đối chứng

| Phương pháp | Lý do / cơ sở | Điều kiện mới triển khai |
|---|---|---|
| Typed exchange + evaluator | Xử lý đúng lỗi đã quan sát; output ngắn, compiler hạ cổng tường minh | Đang thực hiện ở v2; không phải thuật toán quantum mới |
| Bộ chọn operator bằng gradient | [ADAPT-QAOA](https://arxiv.org/abs/2005.10258) đã xây ansatz từ operator pool; là đối chứng thích nghi quan trọng hơn chỉ fixed ring | Sau G1; tính toàn bộ chi phí đo gradient, dùng cùng pool. Không gọi heuristic chọn cạnh đơn giản là tái lập ADAPT |
| Loại lớp/parameter ít tác dụng | [Dynamic-ADAPT-QAOA, PRA 2024](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.109.032420) báo giảm depth/CNOT và kiểm tra noise trên Max-Cut 6–10 qubit | Sau khi xác định cost parameter và distribution có hoạt động; chưa suy kết quả Max-Cut sang mandate tài chính |
| Relaxation warm-start / pretraining hạn chế generator | Có cơ sở thực nghiệm từ Egger và XY warm-start; khác việc lấy danh mục cũ làm basis | Tách khởi tạo khỏi cấu trúc, báo preprocessing; chưa thêm khi correctness chưa đạt |
| Constrained counterdiabatic QAOA | [CCD-QAOA, preprint 05/2026](https://arxiv.org/abs/2605.06858) dùng commutator với XY, báo cải thiện approximation ratio ở cùng depth | Chỉ sau baseline XY; phải so CX/chi phí, không chỉ số lớp. Chưa có implementation hoặc kết quả AGQO cho CCD |

Không triển khai đồng loạt các hướng này: thử v2 trước để quyết định có nên tiếp tục vai trò LLM hay không. Nếu mở benchmark nghiên cứu, ADAPT/operator selection và tìm cấu trúc cổ điển cùng ngân sách là đối chứng cần bổ sung; ba path baseline của pilot chưa đủ để kết luận thắng phương pháp hiện đại.

## Thực hiện và tái lập

### Quyết định sau lượt v2

Kết quả thực: cả Next-80B và Coder-30B đúng 2/3 ngay lần đầu; N=8 cùng bị từ chối vì mixer bỏ qubit tự do khỏi đồ thị. Liên thông là yêu cầu thiết kế đã khóa của protocol, không phải điều kiện để mạch unitary. Hai model chưa đạt G1 80%, không có case đạt G3 khi so fixed path cùng grammar. Trên N=6, fixed path có median P(optimum) khoảng 90,8%, trong khi hai mạch LLM có xác suất rất thấp, dù best gap chỉ khoảng 1%. Correlation path cũng kém fixed ở các bài này; không có căn cứ mặc định tương quan cao là mixer tốt.

**Chưa chọn model chính thức.** Nếu tiếp tục sửa grammar trên tập phát triển, dùng 30B làm ứng viên thực dụng: độ tin cậy bằng 80B trên pilot này, batch khoảng 122s thay vì 211s và GPU rẻ hơn. Đây là quyết định vận hành tạm thời, không chứng nhận 30B tổng quát tốt hơn 80B.

Bước tiếp theo trước khi xin thêm tài nguyên: (1) biểu diễn spanning-tree hoặc thứ tự qubit để compiler bảo đảm liên thông, ghi protocol mới thay vì sửa số liệu v2; (2) giữ fixed path mạnh, thêm operator/structure selector cổ điển cùng ngân sách và uniform feasible sampling; (3) thử initialization full-support/Dicke hoặc warm-start với ablation riêng, vì một exchange preparation có thể giới hạn support; (4) thiết kế tập độc lập N=10,12 và thay đổi mandate, tránh chỉ số best-of-128 gần bão hòa ở N≤8; (5) chỉ mở live benchmark khi correctness đạt và có tín hiệu vượt baseline. Các bước này **chưa chạy live**, không nằm trong kết luận v2.

Đợt này kết thúc ở reservation 23,91/25 USD; billed snapshot 0 USD sau credit. Tài liệu kết quả: `results/synthesis/typed_pilot/REPORT.md`. Không fine-tune, tăng GPU hoặc gọi thêm model để tìm một kết quả đẹp hơn.

```bash
.venv/bin/python -m pytest tests/test_typed_synthesis.py -q
.venv/bin/python -m agqo.synthesis.typed_pilot --mode modal
# Tính lại chỉ dùng raw record đã lưu, không gọi GPU:
.venv/bin/python -m agqo.synthesis.typed_pilot --mode replay
```

Kết quả v1 giữ riêng trong `results/synthesis/pilot`; v2 ở `results/synthesis/typed_pilot`. Bộ 12 bài structural hiện có chỉ được chuẩn bị, chưa có live benchmark để kết luận tổng quát.
