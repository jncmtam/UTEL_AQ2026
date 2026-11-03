# Tiến độ AGQO và trạng thái bằng chứng

Cập nhật: 31/10/2026. Trạng thái theo đầu ra thực tế, không dùng phần trăm hoàn thành ước lượng.

| Hạng mục | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|
| Mô hình sửa danh mục tracking–cost theo mandate | Đã triển khai | `agqo/repair/`; objective dùng chung, drift và transaction cost; exact/MILP/annealing/QAOA |
| Mandate có cấu trúc và kiểm tra | Đã triển khai | Rules + LLM endpoint, bằng chứng văn bản và validator; còn mở rộng corpus diễn đạt tự nhiên |
| DataProfile/Hamiltonian/GateIR/compiler | Đã triển khai và kiểm thử | `agqo/synthesis/`; hash bất biến, angle AST, NumPy/Qiskit, conservation và source map |
| Pilot live 80B/30B, GateIR v1 | Đã chạy, chưa đạt | 80B: 1/3; 30B: 0/3 sau sửa. Xem `results/synthesis/pilot/REPORT.md` |
| Pilot live typed exchange v2 | Đã chạy, chưa qualification | Mỗi model 2/3; chưa hơn fixed path. Xem `results/synthesis/typed_pilot/REPORT.md` |
| Benchmark structural 12 bài | Chuẩn bị, chưa chạy live | Record disabled/not_run không tính là kết quả LLM |
| Rà paper LLM–quantum–finance | Đã cập nhật | `LLM_QUANTUM_FINANCE_LITERATURE.md`: QGAS, QUASAR, QuanBench+, evaluator-guided discovery và các đối chứng portfolio |
| Mở rộng Modal theo quyền user | Đã cấu hình | Policy riêng trần 150 USD reservation; ledger USD25 trước đó giữ nguyên |
| Coder480 / Qwen397 | Đã thêm worker và deploy, chưa inference | Revision pin, TP=4 H200; Qwen397 dùng image vLLM 0.17.1 riêng. Chưa xác nhận VRAM/quality bằng GPU smoke test |
| Specialist QUASAR/Vista 4B | Đã xác minh artifact, chưa chạy AGQO | Cần thử native QASM và kiểm soát chuyển định dạng GateIR; không coi cùng checkpoint là hai model độc lập |
| Chọn model chính thức | Chưa đủ bằng chứng | 30B chỉ là lựa chọn phát triển tạm thời; 480B/397B là ứng viên, không phải winner |
| Kiểm tra ngoài mẫu tài chính | Chưa hoàn tất | Cần dữ liệu phù hợp và benchmark thay đổi mandate; synthetic pilot không chứng minh lợi ích đầu tư thực |
| Quantum advantage / alpha vượt thị trường | Chưa chứng minh | Không phải kết luận được suy từ gap=0 trên N≤8 |

## Kết quả đã đạt và ý nghĩa

V2 tăng tỷ lệ đáp ứng protocol so v1, nhưng task hẹp hơn và compiler đảm bảo nhiều thuộc tính. Không gán toàn bộ cải thiện đó cho LLM. Mixer N=8 bị từ chối do yêu cầu liên thông đã khóa; đây không phải bằng chứng mạch không unitary.

Trên N=6, fixed-path đạt median xác suất optimum khoảng 90,8%, cao hơn hai mạch LLM trong pilot. Ngay cả khi LLM đạt best gap khoảng 1%, chất lượng phân phối vẫn chưa đạt đối chứng. Điều này quyết định chưa mở rộng expensive benchmark chỉ để lấy thêm mẫu giống cũ.

Ở N=8, uniform feasible sampling có khoảng 97,6% khả năng gặp optimum trong 128 mẫu. Benchmark tiếp theo phải tránh chỉ đánh giá best-of-shots trên không gian quá nhỏ.

## Việc tiếp theo theo thứ tự phụ thuộc

1. Soát interface native QASM của quantum specialist; freeze protocol mới khi đổi grammar.
2. Xây biểu diễn đảm bảo liên thông và tách ablation initialization/architecture/angle initialization.
3. Smoke test model lớn trước, rồi so cùng instance, verifier và tổng ngân sách. Không chọn bằng số tham số.
4. Khóa prompt/compiler/model, mở tập độc lập N=10,12 và tổ hợp mandate; đo full/no-correlation/shuffled profile, không thay Hamiltonian giữa ablation.
5. Bổ sung classical structure selection/ADAPT-inspired comparator có đo chi phí, rồi mới xét đóng góp LLM/QAOA.
6. Đánh giá ngoài mẫu tracking–turnover–cost và giao diện quyết định từ kết quả đã kiểm chứng.

## Chi phí và phiên bản

Pilot cũ: reservation 23,91/25 USD, gồm lượt lỗi hạ tầng. Billing snapshot sau pilot: metered cả tháng 6,036 USD, billed 0 USD; không phải số dư credit.

User đã mở rộng quyền sử dụng Modal ở lượt sau. `config/synthesis-expanded-budget.json` ghi điều kiện mới; 150 USD là trần vận hành cho đợt tiếp theo, không phải mức chi dự kiến hoặc xác nhận balance. Việc deploy worker không được tính thành một inference thành công.

Nguồn kết quả và quy tắc ghi nhận: [RESULTS_SPEC](RESULTS_SPEC.md). Nguồn nghiên cứu: [literature review](LLM_QUANTUM_FINANCE_LITERATURE.md).
