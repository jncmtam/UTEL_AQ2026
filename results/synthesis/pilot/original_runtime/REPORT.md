# GateIR — kết quả pilot Modal

Ba instance N=4,6,8 là tập phát triển chẩn đoán. Ngưỡng được ghi trước khi gọi model; cần ít nhất 10 instance độc lập để xét qualification.

| Model | Đúng lần đầu | Có mạch sau sửa | Median feasibility | Median normalized gap | Qualification |
|---|---:|---:|---:|---:|---|
| coder30 | 0.0% | 0.0% | 0.0% | 100.0% | Chưa đủ mẫu |
| next80 | 33.3% | 33.3% | 0.0% | 100.0% | Chưa đủ mẫu |

## Chi tiết từng trường hợp

### coder30

- n4, vòng 0: bị từ chối. Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.; Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.
- n6, vòng 0: bị từ chối. Wrong arity or qubit outside register.
- n8, vòng 0: bị từ chối. Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.
- n4, vòng 1: bị từ chối. Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.; Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.
- n6, vòng 1: bị từ chối. Wrong arity or qubit outside register.
- n8, vòng 1: bị từ chối. Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.
- n4, vòng 2: bị từ chối. Nonrotation gate must have angle=null.; Nonrotation gate must have angle=null.; Nonrotation gate must have angle=null.; Nonrotation gate must have angle=null.
- n6, vòng 2: bị từ chối. Wrong arity or qubit outside register.; Wrong arity or qubit outside register.; Wrong arity or qubit outside register.
- n8, vòng 2: bị từ chối. Wrong arity or qubit outside register.; Nonrotation gate must have angle=null.

| Case | Feasibility (median seed) | Normalized gap | CX sau lowering | Active / declared parameters |
|---|---:|---:|---:|---:|

| Case | Giảm gap so fixed | Giảm CX so fixed | G3 ở case |
|---|---:|---:|---|
| n4 | — | — | chưa đạt |
| n6 | — | — | chưa đạt |
| n8 | — | — | chưa đạt |

Các seed được báo trong JSON riêng; không coi seed là thêm instance tài chính độc lập. Cổng G3 ở một case chỉ là tín hiệu pilot, không đủ cho tuyên bố tổng quát.

### next80

- n4, vòng 0: đạt verifier. 
- n6, vòng 0: bị từ chối. Unproven cardinality preservation. Use adjacent RXX/RYY with identical angle/qubits, or diagonal RZ/RZZ.
- n8, vòng 0: bị từ chối. Unproven cardinality preservation. Use adjacent RXX/RYY with identical angle/qubits, or diagonal RZ/RZZ.
- n6, vòng 1: bị từ chối. ValueError: Cardinality counterexample: qubit_basis_index=0, asset_bits=[0, 0, 0, 0, 0, 0]
- n8, vòng 1: bị từ chối. ValueError: Cardinality counterexample: qubit_basis_index=14, asset_bits=[0, 1, 1, 1, 0, 0, 0, 0]
- n6, vòng 2: bị từ chối. ValueError: Cardinality counterexample: qubit_basis_index=0, asset_bits=[0, 0, 0, 0, 0, 0]
- n8, vòng 2: bị từ chối. ValueError: Cardinality counterexample: qubit_basis_index=14, asset_bits=[0, 1, 1, 1, 0, 0, 0, 0]

| Case | Feasibility (median seed) | Normalized gap | CX sau lowering | Active / declared parameters |
|---|---:|---:|---:|---:|
| n4 | 100.0% | 0.00% | 52 | 3/4 |

| Case | Giảm gap so fixed | Giảm CX so fixed | G3 ở case |
|---|---:|---:|---|
| n4 | — | 31.6% | đạt mục tiêu case |
| n6 | — | — | chưa đạt |
| n8 | — | — | chưa đạt |

Các seed được báo trong JSON riêng; không coi seed là thêm instance tài chính độc lập. Cổng G3 ở một case chỉ là tín hiệu pilot, không đủ cho tuyên bố tổng quát.

## Cách đọc và kết luận

- G0 kiểm nghĩa/phase/register; G1 đo tỷ lệ sinh đúng; G2 đo nghiệm; G3 cần đối chứng tài nguyên/chất lượng trên tập chưa mở.
- Đề xuất lỗi, cắt ngắn và instance không có mạch đúng không bị bỏ khỏi mẫu.
- Bảng trên không khẳng định model đủ chính xác cho mọi mạch. Model lớn hơn chỉ thắng nếu các phép đo ủng hộ.
- Oracle COST vẫn cần 2^N giá trị dựng trên CPU; chưa có cơ sở cho quantum advantage.
- Reservation trong budget.json là cận bảo thủ; hóa đơn billing được chụp riêng, có thể cập nhật trễ.

Nguồn và cơ sở ngưỡng: [SYNTHESIS_THRESHOLDS](../../../docs/SYNTHESIS_THRESHOLDS.md).

![Tỷ lệ mạch đúng trước/sau sửa](01_correctness.png)

**Hình 1. Tỷ lệ mạch đúng trước/sau sửa.** Ba bài N=4,6,8 mỗi model; đề xuất lỗi/cắt ngắn vẫn ở mẫu. Đường 80% là mục tiêu dự án, không phải kết quả paper hay chứng nhận tổng quát. Nguồn: synthetic factor fixtures; không có kết quả QPU.


![Khả thi và chất lượng theo quy mô](02_quality.png)

**Hình 2. Khả thi và chất lượng theo quy mô.** Chỉ case có mạch được verifier chấp nhận mới có đường biểu diễn; case không có mạch bị tính là failure trong bảng G2. Median qua ba seed, chưa là ba bài độc lập. Đường mục tiêu: 90% feasibility, 5% normalized gap. Nguồn: synthetic factor fixtures; không có kết quả QPU.
