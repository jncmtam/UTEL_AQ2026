# Thực nghiệm Modal: GateIR tự do và typed exchange

Đây là kết quả phát triển trên ba instance synthetic N=4,6,8; không phải kiểm tra ngoài mẫu hoặc giao dịch thật.
Raw inference, request hash, model revision, verifier và các seed được lưu cùng thư mục. Không loại failure khỏi tỷ lệ đạt.

## Kết luận về sinh đúng

| Protocol | Model | Đúng lần đầu | Có mạch sau sửa |
|---|---|---:|---:|
| GateIR v1, tối đa 2 sửa | next80 | 33.3% | 33.3% |
| GateIR v1, tối đa 2 sửa | coder30 | 0.0% | 0.0% |
| Typed v2, không sửa | coder30 | 66.7% | 66.7% |
| Typed v2, không sửa | next80 | 66.7% | 66.7% |

V2 khóa cardinality/include/exclude và hạ EXCHANGE thành cặp RXX–RYY bằng compiler. Tỷ lệ đúng v2 không thể quy hoàn toàn cho model; v2 là task hẹp hơn. Chỉ có ba bài độc lập nên chưa model nào được qualification.
Pilot chỉ gồm K-of-N và exclude S00 ở N=6,8; chưa kiểm tra live đầy đủ tổ hợp sector cap/turnover hay mandate mâu thuẫn. N=8 bị chặn bởi quy tắc thiết kế mixer liên thông của protocol; đồ thị không liên thông tự nó không có nghĩa mạch không unitary hoặc phá cardinality.
Lượt khởi động đầu v1 gặp lỗi backend structured decoding không hỗ trợ uniqueItems trước khi sinh token. Đã sửa adapter, vẫn giữ strict validator. Lượt lỗi hạ tầng được tính ngân sách, tách khỏi tỷ lệ đúng ngữ nghĩa của các đề xuất model thực sự sinh ra.
V1 từng có tín hiệu giảm CX khi so với fixed p=2. Sau đối chiếu thêm fixed p=1, tín hiệu đó biến mất; báo cáo hiện dùng baseline cùng độ sâu và không giữ kết luận giảm cổng cũ.

## Chất lượng và đối chứng cùng grammar

Mỗi phương pháp một kiến trúc; ba seed, 16 evaluations ×128 shots và 128 shots đo cuối mỗi seed. P(optimum) là xác suất lý tưởng của trạng thái cuối, không phải tần suất best-of-shots.

| Case | Phương pháp | Hợp lệ | Feasible shots | Best gap | P(optimum) | CX | Tham số active/tổng |
|---|---|---|---:|---:|---:|---:|---:|
| n4 | coder30 | đạt | 100.0% | 0.0% | 82.3% | 30 | 3/3 |
| n4 | correlation_path | đạt | 100.0% | 0.0% | 86.6% | 30 | 2/2 |
| n4 | fixed_path | đạt | 100.0% | 0.0% | 86.7% | 30 | 2/2 |
| n4 | next80 | đạt | 100.0% | 0.0% | 80.4% | 34 | 3/3 |
| n4 | random_path | đạt | 100.0% | 0.0% | 86.7% | 30 | 2/2 |
| n6 | coder30 | đạt | 100.0% | 1.0% | 0.0% | 86 | 3/3 |
| n6 | correlation_path | đạt | 100.0% | 1.0% | 0.0498% | 82 | 2/2 |
| n6 | fixed_path | đạt | 100.0% | 0.0000% | 90.8% | 82 | 2/2 |
| n6 | next80 | đạt | 100.0% | 1.0% | 0.0050% | 86 | 3/3 |
| n6 | random_path | đạt | 100.0% | 0.0000% | 6.8% | 82 | 2/2 |
| n8 | coder30 | lỗi | 0.0% | — | — | — | — |
| n8 | correlation_path | đạt | 100.0% | 7.4% | 0.1% | 282 | 2/2 |
| n8 | fixed_path | đạt | 100.0% | 0.0000% | 87.1% | 282 | 2/2 |
| n8 | next80 | lỗi | 0.0% | — | — | — | — |
| n8 | random_path | đạt | 100.0% | 0.0000% | 6.0% | 282 | 2/2 |

Lỗi coder30 n8: [{"code": "typed_program", "message": "Mixer graph is disconnected on free qubits."}]

Lỗi next80 n8: [{"code": "typed_program", "message": "Mixer graph is disconnected on free qubits."}]

## Kiểm tra độ khó của chỉ số best-of-shots

| Case | Số nghiệm khả thi | P(optimum) nếu lấy đều | P(best-of-128 gặp optimum) |
|---|---:|---:|---:|
| n4 | 6 | 16.7% | >99.99% |
| n6 | 10 | 10.0% | >99.99% |
| n8 | 35 | 2.9% | 97.6% |

Phân phối đều được tính bằng vét cạn để chẩn đoán benchmark nhỏ. Best gap=0 có thể dễ đạt mà không cần LLM hay QAOA; phải đọc thêm phân phối và chất lượng kỳ vọng. Không đổi ngưỡng v1 sau khi xem kết quả.
File selected_edge_evidence.json tra lại tài sản, correlation và hệ số J thật của từng cạnh được chọn. Rationale tự do của LLM chưa được xác minh ngữ nghĩa: việc cite đúng feature ID không chứng minh giải thích đúng hoặc descriptor gây ra lựa chọn cạnh. Cần profile ablation trên tập độc lập.

## Điều kiện tăng thêm G3

- coder30 n4: chưa đạt; so fixed_path; giảm CX 0.0%; giảm gap tương đối —.
- coder30 n6: chưa đạt; so fixed_path; giảm CX -4.9%; giảm gap tương đối —.
- coder30 n8: chưa đạt; so fixed_path; giảm CX —; giảm gap tương đối —.
- next80 n4: chưa đạt; so fixed_path; giảm CX -13.3%; giảm gap tương đối —.
- next80 n6: chưa đạt; so fixed_path; giảm CX -4.9%; giảm gap tương đối —.
- next80 n8: chưa đạt; so fixed_path; giảm CX —; giảm gap tương đối —.

Ngay cả một case đạt cũng chưa là cải thiện tổng quát. Chưa có đối chứng ADAPT, structure search nhiều ứng viên hoặc profile ablation live; không kết luận LLM vượt các phương pháp đó.

## Chi phí và khả năng tái lập

Tổng reservation bảo thủ: **23.91/25 USD**, gồm lượt lỗi hạ tầng và các lượt sửa v1. Đây không phải số tiền đã tính hóa đơn.
Billing snapshot 2026-10-31T15:59:58.263403+00:00: metered cả tháng **6.0360 USD**, billed **0.00 USD**; có thể điều chỉnh trễ, không phải chi phí riêng v2 hoặc số dư credit còn lại.
- coder30: 17722 input + 851 output tokens; batch end-to-end 121.6s gồm cold start/load.
- next80: 17722 input + 826 output tokens; batch end-to-end 210.8s gồm cold start/load.

COST vẫn dựng từ bảng 2^N trên CPU, resource target generic rz/sx/x/cx, không phải topology/QPU cụ thể. Mọi kết quả quantum là mô phỏng.

Kế hoạch và nguồn: [quyết định nghiên cứu](../../../docs/SYNTHESIS_RESEARCH_DECISION.md); [ngưỡng](../../../docs/SYNTHESIS_THRESHOLDS.md).
Tái tính báo cáo: `.venv/bin/python -m agqo.synthesis.evidence_report` (không gọi GPU).