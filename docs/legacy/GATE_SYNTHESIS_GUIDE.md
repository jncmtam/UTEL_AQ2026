# Gate-level QAOA synthesis — chạy và kiểm chứng

Nhánh `agqo.synthesis` bổ sung sinh danh sách cổng có cấu trúc trên bài toán repair hiện tại. Mô hình tài chính không bị đổi giữa các mạch. LLM thiết kế initialization/mixer và parameter sharing; COST do compiler toán học triển khai. Không thực thi mã Python hoặc biểu thức chuỗi từ model.

Pipeline này có CLI riêng `python -m agqo.synthesis`; giao diện `agqo.repair serve` hiện vẫn dùng selector/catalog cũ. Không coi kết quả trên giao diện cũ là một lần sinh GateIR bằng model 80B/30B.

## Đầu vào và đầu ra

`financial_ir.json`: objective, coefficients, mandate, bit mapping và hash bài toán. `data_profile.json`: correlation, clusters, phổ covariance, rank/condition, coefficient IDs, vị thế và độ nhạy cửa sổ. `hamiltonian_ir.json`: hash, phase convention, explicit energy table và chi phí dựng bảng.

`GateIR`: ánh xạ qubit–asset, initial basis, gates chuẩn bị, các lớp COST/mixer, khai báo tham số và lý do dẫn feature IDs. Cổng được compiler chuyển thành Qiskit và QASM. `source_map.json` phân biệt instruction từ GateIR với canonical COST. Model không được thay hệ số cost hoặc bỏ điều kiện để cải thiện điểm.

Artifact gồm `circuit.qasm` đã gán góc, `circuit_parameterized.qasm` và `circuit_parameterized.qpy`. Bản có tham số dùng Walsh transform chính xác để viết diagonal thành các Z-string giao hoán, rồi dùng parity ladder + RZ cho từng hạng. Không giả định Qiskit DiagonalGate nhận được vector số phức còn symbolic. Độ sâu/CX của bản này ghi riêng trong `symbolic_resources.json`, có thể lớn hơn bản đã bind và tối ưu.

Verifier kiểm schema, hash, arity/qubit, stage/parameter, paired exchange, đối chiếu NumPy với Qiskit tại nhiều góc, leakage và tài nguyên sau transpile. Khi angle đi vào code chỉ được tính bằng AST `offset + scale * parameter`. Tính đúng cardinality không có nghĩa giữ đúng giới hạn ngành/turnover: nghiệm tài chính được kiểm tra riêng.

## Lệnh chạy

```sh
.venv/bin/python -m agqo.synthesis search --mode rules --n 4 --output results/synthesis/offline_search
.venv/bin/python -m agqo.synthesis billing
.venv/bin/modal deploy modal_gate_synthesis.py
.venv/bin/python -m agqo.synthesis pilot --mode modal --model both --output results/synthesis/pilot
.venv/bin/python -m agqo.synthesis report --output results/synthesis/pilot
.venv/bin/python -m agqo.synthesis benchmark --mode disabled --model next80 --output results/synthesis/structural_suite
```

`rules` là baseline không phải LLM. `disabled` ghi `not_run`, không tạo mạch giả. `replay` chỉ dùng bản ghi đúng request hash/model. Pilot chạy hai model tuần tự, mỗi model cùng ba instance N=4,6,8 và tối đa hai vòng sửa. Nó là development pilot đã mở, không phải holdout.

Lệnh benchmark định nghĩa 12 bài ngoài pilot với bốn nhóm: seed mới, mất tương quan, đổi cụm và tổ hợp mandate mới. `--mode disabled` chỉ kiểm tra đường đi và ghi chưa chạy. Khi đủ điều kiện mới dùng `--mode modal`, đọc ledger trước để tránh chạy trùng hoặc vượt credit. Các phiên bản prompt/biên dịch khác phải dùng thư mục kết quả riêng.

Full search chạy tối đa 4+2+2 đề xuất, sàng lọc ngân sách nhỏ, chọn tối đa hai finalist rồi tăng ngân sách. Tất cả proposals/trials/shots đều được tính; quality phản hồi chỉ đến từ objective tại cutoff, không nhận future returns hay nghiệm exact trong prompt. Chạy ablation bằng `--ablation constraints_only|no_correlation|shuffled` và `--feedback none|verifier|full`.

`--angle-initialization standard` là mặc định để đo tác động kiến trúc; `--angle-initialization proposed` dùng góc model đưa ra nếu có, nhưng giữ cùng seed/optimizer/budget. Hai lựa chọn phải chạy thành các artifact riêng, không chọn cấu hình bằng kết quả test đẹp hơn.

## Model và runtime

- Primary: `Qwen/Qwen3-Coder-Next-FP8`, revision `da6e2ed27304dd39abadd9c82ef50e8de67bdd4c`, một H200.
- Comparator: `Qwen/Qwen3-Coder-30B-A3B-Instruct`, revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`, BF16 trên một A100 80GB.
- Runtime `vllm==0.15.0`, `jsonschema==4.26.0`. Structured decoding dùng `StructuredOutputsParams(json=SCHEMA)`; tính đúng số học/quantum vẫn do verifier riêng.
- Context 16K, output tối đa 4096 tokens; quá context thì báo lỗi, không âm thầm cắt profile. Worker không giữ GPU khi đang chờ CPU đánh giá; batch mới có thể phải tải lại model từ Volume cache.

MoE kích hoạt 3B mỗi token vẫn phải chứa toàn bộ trọng số 80B trong bộ nhớ; không coi nó là model 3B về VRAM. Fit một H200 phải được smoke test. Nếu 80B không chạy được trong cấu hình pin, ghi failure và chuyển 30B, không tự nâng sang nhiều GPU.

Smoke đầu tiên gặp lỗi grammar backend `Unimplemented keys: ["uniqueItems"]` trước khi có đầu ra LLM. Adapter v1 loại keyword đó khỏi token-mask schema; schema chấp nhận và quantum verifier vẫn kiểm uniqueness đầy đủ. Test cố ý trùng qubit bị chặn. Đây là thay đổi tương thích decoder được ghi trong receipt, không phải nới điều kiện chấp nhận mạch.

## Budget

`results/synthesis/budget.json` dùng file lock, trần 25 USD một đợt, chỉ một reservation GPU đang chạy. Mỗi dispatch lấy snapshot billing qua SDK; snapshot quá 5 phút bị từ chối. Tính bảo thủ trên tổng metered cost của tháng và allowance 30 USD do người dùng xác nhận; SDK không cung cấp một trường credit còn lại độc lập. Buffer tháng 2 USD và margin 25% trong mỗi reservation.

`*_dispatch.json` lưu FunctionCall ID trước khi chờ; `*_receipt.json` ghi GPU/VRAM/runtime/token. Job thất bại vẫn giữ reservation, cần đối soát thủ công trước khi giải phóng. Reservation là cận dự kiến, không phải hóa đơn; chi phí khởi động/tải model có tính phí và billing có thể cập nhật trễ.

Worker `prefetch_model` tải checkpoint bằng CPU vào Volume trước khi cấp GPU; CPU prefetch có thể chạy cùng một job GPU nhưng vẫn giữ nguyên luật chỉ một reservation GPU. Receipt prefetch ghi `cpu_prefetch_not_inference`, không được coi là một lần chạy model thành công. CUDA VRAM và latency chỉ lấy từ receipt suy luận thật.

Nếu tiến trình cục bộ bị ngắt khi remote đang chạy, không dispatch job mới: lấy FunctionCall ID từ checkpoint và dùng Modal FunctionCall để nhận/cancel, sau đó đối soát ledger. Không xóa ledger để có lại ngân sách.

## Ngưỡng và giới hạn

Đọc [SYNTHESIS_THRESHOLDS](SYNTHESIS_THRESHOLDS.md) trước kết quả: tolerance số học, pass rate, feasibility/gap và G3 improvement là các mục tiêu khác nhau. Ba instance chưa đủ qualification; việc model sinh đúng mạch không chứng minh giá trị tài chính hoặc quantum advantage.

Oracle COST bảng `2^N` vẫn là giới hạn tăng theo hàm mũ, N<=12. Độ sâu/CX sau transpile là trên basis chung, không phải thiết bị cụ thể. Khi phép kiểm inactive parameter phát hiện basis+p1, report gắn warning; không tuyên bố đã học từ Hamiltonian chỉ vì có COST trong circuit.
# Follow-up có kiểu sau pilot v1

V1 lưu nguyên kết quả và raw response trong `results/synthesis/pilot`. V2 thay đổi grammar sau khi phân tích lỗi v1: model chọn cạnh EXCHANGE và chia sẻ beta; compiler giữ basis/COST và hạ từng khối thành RXX–RYY. Đây là task hẹp hơn, không trộn tỷ lệ đúng giữa hai protocol.

```bash
.venv/bin/python -m agqo.synthesis.typed_pilot --mode modal
.venv/bin/python -m agqo.synthesis.evidence_report
# Chỉ tái tính từ cache; không gọi GPU:
.venv/bin/python -m agqo.synthesis.typed_pilot --mode replay
```

V2 một đề xuất/model/case, không paid retry. Mỗi lần gọi Modal vẫn đi qua ledger chung và billing guard. Chạy lại mode modal sẽ dùng cache nếu request hash/model revision khớp; không sửa protocol trong thư mục đã khóa. Kế hoạch, phương pháp hiện đại và stop rules: [SYNTHESIS_RESEARCH_DECISION](SYNTHESIS_RESEARCH_DECISION.md). Báo cáo so sánh: `results/synthesis/typed_pilot/REPORT.md`.

