# LLM sinh mạch và chọn tổ hợp chứng khoán: rà soát theo bằng chứng

Ngày tra cứu: 31/10/2026. Phạm vi: nguồn gốc của tác giả, arXiv, proceedings và artifact chính thức. Đây là rà soát có mục tiêu, không phải systematic review bao phủ mọi công trình.

## Kết luận phục vụ quyết định

**QGAS là công trình trực tiếp nhất tìm được cho giao điểm LLM thiết kế ansatz + portfolio selection. QUASAR là đối chứng chuyên quantum đáng thử nhất trong các artifact đã kiểm tra. Chưa có căn cứ gọi một model hoặc paper là tốt nhất đồng thời về sinh mạch và hiệu quả đầu tư thực tế.**

Không xếp hạng bằng cách so 99,31% syntax của một bài với 83,3% functional correctness của bài khác. Dataset, ngân sách, simulator và tiêu chí thành công khác nhau.

## Ma trận công trình và phạm vi kết luận

| Công trình | Phần đã thực nghiệm | Kết quả kiểm tra được | Giới hạn đối với AGQO |
|---|---|---|---|
| [QGAS — Unleashing the Potential of LLMs for Quantum Computing, 2023](https://arxiv.org/html/2307.08191) | GPT-4 chọn loại block, qubit và ansatz; GPT-3.5 chuyển sang QASM; có human feedback và tối ưu số | Portfolio 4 tài sản, chọn 2, risk factor 0,5. Table I: QGAS 31 gates, objective −0,01347; reference −0,0149; TwoLocal 3 repeats: 34 gates, −0,01303 | Đúng giao điểm cần nghiên cứu nhưng quy mô rất nhỏ, baseline ansatz; chưa chứng minh hiệu quả ngoài mẫu sau chi phí hoặc thắng MILP mạnh. Đây là tìm ansatz variational, không phải mọi cấu trúc đều là QAOA |
| [QUASAR, arXiv:2510.00967](https://arxiv.org/html/2510.00967) | Qwen3-4B được SFT + GRPO với simulator và reward nhiều tầng; sinh OpenQASM | Table 1, Pass@1: SCR 99,31%; SREV 22,41%; HQCR 17,24%. Có public checkpoint và code | 99,31% chỉ là parse đúng. SREV dùng độ lệch expectation với reference ≤0,2; HQCR dùng KL ≤0,1. Dataset là graph optimization, chưa là kiểm chứng portfolio |
| [Agent-Q, QCE 2025](https://arxiv.org/html/2504.11109v2) | Fine-tune sinh circuit trên 12 nhóm graph optimization; đánh giá syntax, expectation và phân phối | Table II: 171/200 =85,5% syntax | Là tiền thân hữu ích; chưa là bằng chứng chọn tổ hợp chứng khoán tốt |
| [QuanBench+, 2026](https://arxiv.org/html/2604.08570) | 42 task tương ứng trên Qiskit/Cirq/PennyLane; đánh giá functional output | Table 3: Qiskit one-shot Gemini-3-Pro 59,5%, GPT-5.1 57,1%, DeepSeek-R1 50%; sau feedback GPT-5.1 83,3% | Có ích để chọn model tổng quát; không có đo stock selection, và không đánh giá các checkpoint 480B/397B mới chọn của AGQO |
| [Protocol-Guided LLM Agent, 2026](https://arxiv.org/html/2609.20258) | Matched ablation 4 endpoint, 3 task, 240 trial; protocol YAML + evaluator repair | Evaluator completion 80,0% →99,2%; mean repairs 2,56 →0,75. Tác giả phân biệt completion với semantic validity | Củng cố grammar/protocol; không chứng minh model lớn tự động giải quyết semantics hay portfolio |
| [Discovering state-of-the-art quantum circuits with LLMs, preprint 15/10/2026](https://arxiv.org/html/2610.22367v1) | Claude Mythos 5 + OpenEvolve, verifier độc lập, nhiều dòng ứng viên và lưu frontier tài nguyên | Tác giả báo giảm cả Toffoli và qubit trên 7/8 task | Mạnh về phát hiện thiết kế và resource optimization trong tập task của bài; không benchmark QAOA danh mục. Không suy giá trị tài chính từ số Toffoli giảm |
| [Generative QAOA and Its Application to Portfolio Optimization, workshop 2025; proceedings 2026](https://static.even3.com/anais/1262964.pdf?v=639115349399794517) | GPT-2 sinh chuỗi góc QAOA, cập nhật theo measured energies | 5 cổ phiếu DAX, chọn 2; depth 10; 60 circuit evaluations so COBYLA 191; cùng tìm tổ hợp tối ưu trong ví dụ | Là generative parameter optimization, chưa là LLM thiết kế layout/gates tự do; một bài nhỏ, không phải bằng chứng tổng quát hoặc backtest ròng |
| [Direct indexing với XY-QAOA, 02/2026](https://arxiv.org/html/2602.14827v1) | Dicke + XY; risk–return selection rồi phân bổ liên tục; walk-forward 10 cổ phiếu | Table III: Sharpe 1,81; monthly turnover 76,8%; tác giả đề xuất đưa turnover vào objective | Không LLM; khác objective tracking–cost. Không dùng Sharpe này làm ngưỡng của AGQO |
| [Quantum Portfolio Optimization: An Extensive Benchmark, v3 10/2026](https://arxiv.org/html/2509.17876v3) | 270 instance; classical tới 1.000 tài sản, quantum tới 30; MIP và heuristic mạnh | MIP chứng minh optimum trong cỡ giây cho các instance của biến thể nghiên cứu; heuristic chuyên biệt vượt quantum dưới runtime cố định | Cần đối chứng classical mạnh, không suy mọi biến thể portfolio đều dễ hoặc mọi quantum đều kém |
| [Large-scale portfolio optimization on a trapped-ion quantum computer, 2026](https://arxiv.org/html/2602.23976) | 250 cổ phiếu, chia cluster theo budget qubit; BF-DCQO, recombination, repair và swap search; có QPU | So candidate pools với random dưới cùng post-processing; subproblem lớn hơn giảm lỗi decomposition | Không LLM và không thuần QAOA; một số subproblem giải bằng Gurobi. Không gán toàn bộ chất lượng hệ thống cho quantum hoặc coi kết quả tốt hơn random là thắng classical tốt nhất |

Các số liệu trên là kết quả tác giả công bố, **chưa được AGQO tái lập**. Không cộng hoặc so tỷ lệ giữa những cột có định nghĩa khác nhau.

## Bằng chứng quan trọng từ QUASAR

Paper tách được khoảng cách giữa chương trình chạy được và chương trình hữu ích: syntax gần 100% nhưng các tiêu chí chất lượng vẫn thấp hơn nhiều. Reference circuit là kết quả tối ưu trong một ansatz, không mặc định là quantum optimum toàn cục.

Hệ quả cho AGQO: chất lượng objective tài chính là tiêu chí chính. Similarity với phân phối reference chỉ là chẩn đoán; một phân phối khác vẫn có thể chọn danh mục tốt hơn. Fidelity NumPy–Qiskit trong verifier hiện tại kiểm tra hai implementation của **cùng mạch**, không buộc ansatz LLM giống ansatz chuẩn.

Public artifact: [Benyucong/rl_quantum_4b](https://huggingface.co/Benyucong/rl_quantum_4b), revision đã kiểm tra `b9581279345436e2b7eadcdf80e4f1417748eb8b`; [repository](https://github.com/benyucong/rl-quantum). Repository hiện mô tả Vista và checkpoint liên quan QUASAR; cần ghi rõ revision/format, không coi hai tên là hai model độc lập. Artifact có thể thay đổi theo thời gian. Training lại paper từ đầu không phải điều kiện để thử inference checkpoint công khai.

## Chọn model và phương pháp theo task

1. **Specialist quantum:** thêm checkpoint QUASAR/Vista 4B vào đối chứng. Kiểm tra native OpenQASM trước, rồi đo khả năng chuyển sang GateIR. Không gọi việc thất bại trên JSON grammar mới là tái lập thất bại của paper.
2. **General coding model lớn:** Qwen3-Coder-480B là ứng viên kiến trúc/code, chưa có paper trên chứng minh nó tốt nhất cho quantum hoặc stocks. Giữ 30B/80B làm baseline.
3. **Reasoning model:** thêm một nhánh suy luận với ngân sách reasoning được ghi. Kết quả benchmark của một endpoint không tự chuyển sang model có tên/tổng tham số tương tự.
4. **Không giao LLM tính covariance hay lựa cổ phiếu bằng lời giải thích.** Code tạo objective, mandate, bounds và DataProfile; LLM đề xuất cấu trúc; simulator/optimizer đo khả năng lấy mẫu tổ hợp. Thay model không được đổi bài toán tài chính.
5. **Tách vai trò:** model hiểu mandate, model đề xuất kiến trúc và compiler hạ gates có thể khác nhau. Nếu compiler đã bảo đảm tính đúng của một khối, không gán lợi ích đó cho LLM.

## “Chọn tổ hợp hiệu quả” cần vượt những phép đo nào?

- Với cùng dữ liệu quá khứ, objective tracking–cost và mandate: xác suất nghiệm khả thi, xác suất nghiệm trong gap 5%, kỳ vọng objective và gap tới exact/bound.
- Với cùng ngân sách tổng: inference, mọi candidate/retry, optimize angles, shots, compile, classical preprocessing và post-processing đều được tính.
- Với dữ liệu ngoài mẫu: tracking thực hiện, turnover từ tỷ trọng đã drift, chi phí và tuân thủ; stress theo thay đổi mandate và thị trường.
- Đối chứng bắt buộc: MILP/exact, heuristic phù hợp, fixed circuit, rule/random cùng grammar; thêm cấu trúc thích nghi cổ điển. Không chỉ dùng baseline dễ thắng.
- Không chọn mạch chỉ vì ít gates; không chọn model chỉ vì syntax cao; không gọi best-of-128 gap=0 là bằng chứng khi random feasible sampling gần chắc cũng gặp optimum.

**Thứ tự nghiên cứu được điều chỉnh:** QGAS cho cách liên kết task tài chính–ansatz; QUASAR/Vista cho semantic reward và specialist; evaluator-guided search cho cách giữ nhiều thiết kế; extensive portfolio benchmark cho chuẩn tài chính/classical. Tổ hợp này là đề xuất thiết kế của AGQO, chưa phải một phương pháp đã được chứng minh tốt nhất.

## Trạng thái dự án ở thời điểm rà soát

- Đã chạy Modal 30B/80B v1/v2; cả hai v2 mới đạt 2/3, chưa qualification, chưa vượt fixed baseline.
- Đã thêm và deploy worker coder480/qwen397, pin revision và engine; **chưa có kết quả GPU inference hai model này** tại thời điểm viết file.
- Ngân sách mới được user mở rộng; ledger cũ giữ nguyên. Trần vận hành mới là 150 USD reservation, không phải số dư tài khoản được API xác nhận.
- Chưa có inference QUASAR/Vista trong AGQO. Không đưa số liệu paper vào bảng kết quả của dự án.
