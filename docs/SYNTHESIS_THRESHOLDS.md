# Ngưỡng đánh giá sinh QAOA từ LLM — đăng ký trước pilot

Ngày: 31/10/2026. Trạng thái: **mục tiêu thiết kế của dự án, chưa phải kết quả đã đạt**. Các paper dưới đây định hướng phép đo và đối chứng; không paper nào bảo đảm một model 80B đạt các ngưỡng này trên mandate của AGQO.

## Cơ sở thực nghiệm và lựa chọn phương pháp

| Nguồn gốc | Thực nghiệm liên quan | Quyết định cho AGQO |
|---|---|---|
| [Agent-Q, QCE 2025](https://arxiv.org/html/2504.11109v2) | Trên 200 bài test, Table II báo 171/200 = 85,5% đúng cú pháp; CodeGemma 7B few-shot đạt 75%. Đây chưa phải functional accuracy | Tách sinh đúng khỏi sinh tốt; thử output thực thi và phân phối thay vì chấm lời giải thích. Mốc 80% của AGQO là mục tiêu kỹ thuật khác task, không phép tái lập 85,5% |
| [QCircuitBench, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/3e343c7fa87656d7e88e9a83cb2a5d10-Paper-Datasets_and_Benchmarks_Track.pdf) | Ba task suites, 25 thuật toán, 120.290 điểm dữ liệu; verification gồm syntax và semantic score; đánh giá fidelity cho tác vụ trạng thái | JSON đúng chưa đủ; thêm state fidelity, kiểm tra source mapping và fault injection |
| [XY-mixer topologies and warm starting, 2025/2026](https://arxiv.org/html/2505.18396v2) | Thử portfolio N=12,14,16 tùy ansatz; pretraining 100 bước trên mạch hạn chế rồi 100 bước refine sau chuyển tham số, so shared-angle/multi-angle | Ưu tiên sparse exchange, giới hạn số tham số; so random, incumbent-superposition và pretraining thực sự. Không gọi basis incumbent là cùng phương pháp của paper |
| [Warm-starting quantum optimization, Quantum 2021](https://arxiv.org/html/2009.10095v4) | Khởi tạo từ relaxation cổ điển, có thử portfolio độ sâu thấp | Theo dõi chi phí tiền xử lý; kiến trúc và khởi tạo góc phải có ablation riêng |
| [Extensive Portfolio Benchmark, v3 2026](https://arxiv.org/html/2509.17876v3) | 270 instance, tới 1.000 tài sản; quantum tới 30 tài sản; ngân sách device/training/sampling 60 giây, không tính build/cloud/result analysis; classical rất mạnh | Exact và HiGHS là chuẩn; AGQO báo thêm tổng pipeline nên không so trực tiếp thời gian 60 giây của paper với end-to-end latency |

Không nhập approximation ratio từ paper Markowitz sang tracking MSE: objective có đơn vị và offset khác. Dùng gap chuẩn hóa theo **khoảng mục tiêu của các nghiệm khả thi cùng instance**; nếu khoảng bằng 0 thì mọi nghiệm khả thi là tối ưu tương đương.

## Các cổng đạt

| Cổng | Ngưỡng đăng ký | Mục đích / cách đọc |
|---|---|---|
| G0 — tính đúng bắt buộc | 100% mạch được chấp nhận giữ đúng problem/Hamiltonian hash, không có tham số ngoài schema; fidelity NumPy–Qiskit >= 1−1e−9; rò cardinality <=1e−9 nếu khai báo bảo toàn | Dung sai số học do dự án chọn; không phải mức fidelity phần cứng |
| G1 — độ tin cậy sinh | Pilot ≥80% đề xuất đầu hợp lệ; sau tối đa 2 vòng sửa ≥90% instance có ít nhất một mạch đúng | Mục tiêu kỹ thuật; pilot 3 kích thước chỉ chẩn đoán, cần ≥10 instance độc lập để xét qualification |
| G2 — khả thi và chất lượng | Trên bài có nghiệm: median xác suất mẫu hợp lệ ≥90%; median normalized best-feasible gap ≤5%; không bỏ failed runs | Ngưỡng nghiệm là mục tiêu nghiên cứu; ghi cả xác suất theo statevector và finite shots |
| G3 — giá trị tăng thêm | Cùng ngân sách tổng: giảm ≥20% gap so fixed nếu baseline gap >0, hoặc giảm ≥20% CX với normalized gap không xấu hơn 1 điểm phần trăm và feasibility không giảm quá 1 điểm phần trăm | Đây là điều kiện cho tuyên bố cải thiện, không kỳ vọng bắt buộc. Baseline gap=0 không được biến thành phần trăm cải thiện |
| G4 — chi phí | Tổng reservation một đợt <=25 USD; không vượt credit còn lại sau buffer; mọi đề xuất lỗi/retry/compiler/oracle đều được tính | Reservation bảo thủ không đồng nghĩa hóa đơn; báo billing trước/sau riêng |

Qubit/depth/CX cap là giới hạn hỗ trợ prototype, không là tuyên bố mạch đạt hữu ích thực tế. Corpus benchmark nhỏ không đủ suy khả năng sinh mạch bất kỳ.

## Thứ tự tiếp cận tối ưu trong ngân sách

1. Khóa objective và COST; để LLM thiết kế initialization, exchange schedule và parameter sharing. Không nhờ LLM tính lại coefficient số học.
2. Ưu tiên sparse connected exchanges với superposition trước COST; basis + p=1 chỉ là baseline vì gamma đầu không hoạt động ngoài global phase.
3. Kiểm schema/analytic conservation trước; chỉ mạch qua mới chạy simulator/Qiskit và optimizer.
4. Pilot 80B/30B cùng ba instance N=4,6,8, cùng output budget, verifier, optimizer và seeds. Retry có phản ví dụ, không giấu thất bại đầu.
5. So fixed/rules/random và selector cũ. Chi phí search bằng tổng mọi trial, không chỉ mạch thắng.
6. Chỉ tăng quy mô/fine-tune khi đã có tập lỗi và kết quả đo; nếu không model nào qua G1–G2 thì ghi chưa đủ điều kiện, không tự chọn model lớn hơn.

Kết quả DLA polynomial trong paper áp dụng generator bị hạn chế, chẳng hạn XY + RZ. Nó **không** chứng minh full COST có barrier nhiều ràng buộc của AGQO dễ train chỉ vì mixer là vòng thưa. Prototype không tuyên bố chứng minh DLA hoặc loại bỏ barren plateaus.

## Giới hạn công bằng

Pilot được mở để chọn prompt/model, không tái gọi là holdout. Một instance được thử nhiều seed không tạo thêm các bài toán độc lập. Correlation/profile ablation dùng Hamiltonian giữ nguyên; đó là tác động của descriptor trong prompt, không phải xóa thông tin toán học khỏi hệ thống. Với oracle bảng đầy đủ, quantum advantage chưa thể được xác lập.
