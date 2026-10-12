# AGQO — bộ thử nghiệm có thể chạy ngay

## Mục tiêu

Đây là bản triển khai kỹ thuật cho đề cương: mô hình hồi quy logistic ước lượng xác suất biến động cao; xác suất này chỉ điều chỉnh hệ số ngại rủi ro λ và mức co rút hiệp phương sai α. Sau đó bộ giải chọn đúng K = 6 mã theo cùng một hàm mục tiêu rủi ro–lợi nhuận. Không có dự báo lợi nhuận riêng từng mã, mô hình ngôn ngữ lớn hay quyết định mua bán tự động.

Đây là bộ nghiên cứu, không phải hệ thống giao dịch. Mẫu tổng hợp chỉ kiểm tra thuật toán; nó không tạo bằng chứng về lợi nhuận tại Việt Nam. Chưa kèm dữ liệu thị trường có giấy phép.

## Từ viết tắt

- **AI** (Artificial Intelligence, trí tuệ nhân tạo); **LLM** (Large Language Model, mô hình ngôn ngữ lớn).
- **QAOA** (Quantum Approximate Optimization Algorithm, thuật toán tối ưu gần đúng lượng tử); **QUBO** (Quadratic Unconstrained Binary Optimization, tối ưu nhị phân bậc hai không ràng buộc); **QPU** (Quantum Processing Unit, bộ xử lý lượng tử).
- **COBYLA** (Constrained Optimization BY Linear Approximations, tối ưu không đạo hàm bằng xấp xỉ tuyến tính); **H2** (Hypothesis 2, giả thuyết số 2).
- **IBM** (International Business Machines); **CPU** (Central Processing Unit, bộ xử lý trung tâm); **GPU** (Graphics Processing Unit, bộ xử lý đồ họa).
- **RAM** (Random Access Memory, bộ nhớ truy cập ngẫu nhiên); **SSD** (Solid-State Drive, ổ lưu trữ thể rắn); **CUDA** (Compute Unified Device Architecture, kiến trúc tính toán song song của NVIDIA).
- **ADTV** (Average Daily Traded Value, giá trị giao dịch bình quân ngày); **CSV** (Comma-Separated Values, dữ liệu phân tách bằng dấu phẩy).
- **JSON** (JavaScript Object Notation, ký pháp đối tượng JavaScript); **PCG64** (Permuted Congruential Generator 64-bit, bộ sinh số giả ngẫu nhiên 64 bit).

## Hai đường chạy

| Đường chạy | Dùng để làm gì | Có cần thiết bị lượng tử thật? |
|---|---|---|
| Cục bộ | Duyệt chính xác, tham lam, tôi luyện, máy mô phỏng véc-tơ trạng thái, kiểm tra mạch cục bộ | Không |
| Thiết bị lượng tử | Biên dịch mạch, lấy mẫu bằng IBM Quantum Runtime và lưu mã công việc/số cổng/độ sâu | Có tài khoản, token, backend và hạn mức được cấp |

Máy mô phỏng véc-tơ trạng thái trong lõi dùng NumPy và SciPy; mã mạch dùng Qiskit. Có thể bật Qiskit Aer để đối chiếu độc lập mạch với trạng thái lý tưởng. Nhánh thiết bị dùng SamplerV2; cấu hình mẫu không chứa khóa truy cập và sẽ bị chặn trước khi có thông tin hợp lệ.

## Cài đặt

Khuyến nghị Python 3.12. Tại thư mục dự án:

    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements-lock.txt
    python -m pip install -e . --no-deps

Tệp khóa ghim phiên bản chính xác đã cài trên Python 3.12; lệnh cuối đăng ký gói AGQO tại chỗ. Nếu chỉ chạy lõi NumPy, có thể bỏ qua các thư viện Qiskit, Aer và IBM Runtime; khi đó bỏ qua kiểm tra mạch và nhánh QPU.

## Chạy thử lõi

    agqo demo --n 8 --max-evaluations 50
    pytest

Lệnh mẫu tạo bài toán tổng hợp có 8 mã, K = 6; so nghiệm chính xác với tham lam, tôi luyện, QAOA với bộ trộn X và XY; dùng ba giá trị khởi tạo ngẫu nhiên 11, 23, 47; ghi nhật ký theo từng dòng vào outputs/. Mỗi lần đánh giá góc lấy mẫu 512 lần đo; trần mỗi lần khởi tạo là 50 đánh giá. Để kiểm tra nhanh, đặt --max-evaluations 6.

Đối chiếu Qiskit Aer với trạng thái lý tưởng:

    python -c 'from agqo.aer import crosscheck_aer; from agqo.problem import synthetic_problem; print(crosscheck_aer(synthetic_problem(20261012, n=8), mixer="XY"))'

Trên GPU, chỉ đổi device="GPU" sau khi đã cài bản Qiskit Aer có CUDA tương thích. Gói GPU chính thức chỉ được phát hành sẵn cho Linux x86-64; máy Mac dùng CPU. Tài liệu Aer nêu rõ máy mặc định chạy CPU và GPU phụ thuộc bản cài, trình điều khiển và CUDA [1].

## Chạy tiêu chí H2

    agqo benchmark --limit 12 --max-evaluations 50

Lệnh trên chạy đủ 12 nguồn tổng hợp × 3 kích thước N = 8, 12, 16 × 2 bộ trộn = 72 cấu hình. Mỗi cấu hình có ba giá trị khởi tạo. X và XY được đánh giá riêng; mỗi nguồn đóng góp ba bài toán vào tiêu chí 29/36 của đề cương. --limit 1 chạy 6 cấu hình. Bộ sinh dùng PCG64 với các giá trị từ 20261012 đến 20261023 và đúng phân phối ma trận nhân tố, biến động riêng, lợi nhuận trong đề cương.

Độ lệch chuẩn hóa được tính từ nghiệm khả thi tốt nhất lấy mẫu ở mỗi lần chạy, so với nghiệm chính xác. Tỷ lệ nghiệm khả thi và năng lượng mục tiêu ước lượng được lưu riêng để không đánh đồng chúng với độ lệch mục tiêu.

Lượt chạy ngày 13/10/2026 trên 36 bài toán tổng hợp đạt 18/36 cấu hình với X và 0/36 với XY, dưới ngưỡng 29/36 đã khóa. X đạt 12/12 ở N=8, 6/12 ở N=12 và 0/12 ở N=16. Chi tiết giới hạn, máy thử và đề nghị tài nguyên nằm trong [báo cáo H2](results/BAO_CAO_THU_NGHIEM_H2_2026-10-13.md); dữ liệu từng cấu hình nằm trong [nhật ký thô](results/synthetic_h2_20261013.jsonl). Đây là kết quả kỹ thuật tổng hợp, không phải lợi nhuận thị trường.

## Lõi toán học

Với vector lợi nhuận năm μ, ma trận hiệp phương sai năm Σ, hệ số ngại rủi ro λ, biến chọn nhị phân x và K mã:

    f(x) = λ xᵀΣx / K² − μᵀx / K

QUBO (Quadratic Unconstrained Binary Optimization, tối ưu nhị phân bậc hai không ràng buộc) của bộ trộn X cộng hạng phạt A(Σxᵢ−K)². Bộ trộn XY dùng mục tiêu gốc và khởi tạo ở chuỗi có đúng K bit 1; các cổng XY trên vòng bảo toàn số bit 1. Vì các cạnh kề nhau không giao hoán, mạch dùng tích Trotter bậc nhất theo thứ tự cạnh trên vòng, giống nhau ở máy mô phỏng và bộ nối QPU. Chuyển sang Hamiltonian Ising theo xᵢ=(1−Zᵢ)/2, giữ hằng số để kiểm chứng mọi chuỗi bit.

Tối ưu góc dùng COBYLA (Constrained Optimization BY Linear Approximations, tối ưu không đạo hàm bằng xấp xỉ tuyến tính) với trần số lần gọi hàm mục tiêu. Mạch QPU được tạo từ chính hệ số Ising đó; nghiệm đo được đảo thứ tự bit của Qiskit trước khi ánh xạ lại mã.

## Lớp AI và ước lượng tài chính

agqo/ai.py tạo biến động 20/60/120 phiên, lợi nhuận chỉ số 20/60 phiên, tương quan trung vị 60 phiên, tỷ số biến động, tỷ lệ mã đủ lịch sử và giá trị giao dịch bình quân ngày. Mã thành viên và mã đủ điều kiện được xác định theo từng ngày. Nếu nguồn lịch sử tạm ngừng giao dịch được xác nhận, có thể truyền thêm tỷ lệ tạm ngừng; nếu không thì cột này không tồn tại ở bất kỳ kỳ nào.

Nhãn là biến động của 21 phiên sau ngày t. Hàm khớp loại mẫu chưa trưởng thành trước ranh giới từng tập, lấy ngưỡng phân vị 70% từ tập huấn luyện, chuẩn hóa trên tập huấn luyện, chọn C bằng log-loss xác nhận, rồi khớp lại trước tập kiểm tra. Cần ít nhất 500 mẫu huấn luyện và cả hai lớp trong huấn luyện/xác nhận; nếu thiếu, hàm dừng thay vì tạo kết luận AI.

agqo/estimators.py tính μ = 252 × trung bình lợi nhuận ngày; hiệp phương sai mẫu hoặc Ledoit–Wolf được năm hóa ×252. Hàm build_regime_problem nối xác suất AI với λ/α và tạo đối tượng đầu vào dùng chung cho bộ giải. Mức co rút đường chéo bị chặn trong [0,10; 0,70]. Các hàm này chưa tải dữ liệu và không tự chọn ngày/mã.

## Nối dữ liệu thị trường

Chưa đưa dữ liệu VN30/VN100 vào kho mã. Trước khi đưa kết quả tài chính vào báo cáo, cần cung cấp dữ liệu được phép sử dụng và lịch thành phần chỉ số theo ngày hiệu lực. Cấu trúc cần chuẩn hóa:

- Giá ngày đã điều chỉnh và giá mở cửa cho từng mã.
- Giá trị giao dịch ngày để tính ADTV 20 phiên.
- Giá đóng cửa chỉ số thị trường.
- Lịch thành phần lịch sử: mã, ngày bắt đầu hiệu lực, ngày hết hiệu lực.
- Cờ tạm ngừng lịch sử chỉ khi nhà cung cấp xác nhận độ tin cậy.

Không thay lịch thành phần lịch sử bằng danh sách hiện tại. Chưa có bộ đọc CSV và kiểm định lịch sử đầy đủ trong bản này; vì vậy không đưa ra CAGR, Sharpe, mức giảm tối đa hay tuyên bố hiệu quả đầu tư. Các quyết định quản trị dữ liệu, thời kỳ huấn luyện/xác nhận/kiểm tra khóa, phí, thanh khoản và vốn giả định vẫn theo proposal.

## Nhánh QPU để điền sau

1. Sao chép config/qpu.example.toml thành config/qpu.toml.
2. Điền kênh dịch vụ, mã phiên bản dịch vụ và tên backend trong cấu hình cá nhân.
3. Đặt token ở biến môi trường, ví dụ export IBM_QUANTUM_TOKEN='…'. Không ghi token vào tệp cấu hình hoặc nhật ký.
4. Chạy kiểm tra không gửi: agqo qpu.
5. Chỉ gửi khi đã xác nhận thiết bị, số lần đo và hạn mức: agqo qpu --n 8 --mixer XY --submit.

Mỗi lần đánh giá dùng 512 lần đo; trần mặc định 50 lần đánh giá. Sổ outputs/qpu_shot_ledger.json giữ chỗ cho ngân sách tổng 800.000 lần đo trước khi gửi và chốt số thực tế sau khi hoàn tất. Dữ liệu tổng hợp là đầu vào mặc định cho phép thử QPU. Chưa có token, backend hay job nào được gửi trong lượt xây dựng này. Tài liệu IBM mô tả SamplerV2 nhận mạch và trả mẫu đo; cấu hình mode=backend gắn job với backend được chọn [2][3].

## Tài nguyên theo proposal

- **CPU (Central Processing Unit, bộ xử lý trung tâm):** 16 lõi ảo, 64 GB RAM (Random Access Memory, bộ nhớ truy cập ngẫu nhiên) và 100 GB SSD (Solid-State Drive, ổ lưu trữ thể rắn) trong 4 tuần là mức đề nghị để chạy song song toàn bộ lịch thí nghiệm, không phải yêu cầu tối thiểu của demo. Với N = 30, K = 6 có 593.775 tổ hợp; mã duyệt chính xác giới hạn N ≤ 30, K ≤ 6.
- **GPU (Graphics Processing Unit, bộ xử lý đồ họa):** tối đa 40 giờ, bộ nhớ đồ họa 24 GB chỉ xin sau khi đo lợi ích tăng tốc trên nút Linux có CUDA. Hồi quy logistic và mẫu N = 8–16 hiện không cần GPU.
- **QPU (Quantum Processing Unit, bộ xử lý lượng tử):** ưu tiên 8–12 qubit, trần kế hoạch 800.000 lần đo; không phải điều kiện hoàn thành. Bộ nối hiện giới hạn mỗi lần chạy trong ngân sách cấu hình.

Đề nghị tài nguyên là theo đề cương; chưa có benchmark trên máy 16 lõi/64 GB hay chi phí nhà cung cấp. Aer có thể mô phỏng trạng thái trên GPU với một số phương thức và bản cài phù hợp, nhưng GPU không tự động cần thiết hoặc tự động nhanh hơn [1].

Phép đo bổ sung trên máy thử 8 lõi/16 GB đã duyệt chính xác một bài toán tổng hợp N=30, K=6 trong 3,987 giây. Con số này không đại diện cho toàn bộ kiểm định lịch sử; nó cho thấy CPU/GPU/QPU trong đề nghị là dự phòng cho chạy song song, mở rộng và đo mạch, không phải điều kiện để tìm nghiệm VN30.

## Tệp chính

- agqo/problem.py: công thức danh mục, QUBO, Ising, duyệt chính xác, tham lam, tôi luyện, dữ liệu tổng hợp.
- agqo/simulator.py: QAOA véc-tơ trạng thái, bộ trộn X/XY và tối ưu COBYLA.
- agqo/ai.py: đặc trưng, nhãn 21 phiên, hồi quy logistic, ánh xạ λ/α.
- agqo/estimators.py: trung bình lợi nhuận, hiệp phương sai mẫu/Ledoit–Wolf và nối xác suất AI thành λ/α.
- agqo/aer.py: kiểm tra chéo mạch bằng Qiskit Aer.
- agqo/qpu.py: tạo mạch, kiểm tra cấu hình và IBM Quantum Runtime.
- tests/: kiểm tra tương đương mục tiêu/QUBO/Ising, bảo toàn K, giới hạn bộ giải và mạch Qiskit.

## Tài liệu chính thức

1. [Qiskit Aer — AerSimulator và hỗ trợ GPU](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html).
2. [IBM Quantum — SamplerV2](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/sampler-v2).
3. [IBM Quantum — chạy công việc trên thiết bị](https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-sampler).
4. [Qiskit Algorithms — QAOA và bộ trộn ràng buộc](https://qiskit-community.github.io/qiskit-algorithms/stubs/qiskit_algorithms.QAOA.html).
5. [scikit-learn — hiệp phương sai Ledoit–Wolf](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.ledoit_wolf.html).
