# AGQO — bằng chứng tái cân bằng theo mandate

Nguồn: synthetic

Protocol SHA-256: `32afc2c8a783d113858e9755bd3251886c708c271bad426013f449153d5de0ae`

Kết quả là benchmark nghiên cứu; chưa chứng minh lợi thế lượng tử hoặc tiết kiệm thực tế cho quỹ.

Các kỳ của nguồn OR-Library chưa được xác minh tần suất; chỉ báo số liệu mỗi kỳ, không năm hóa.

| Phương pháp | Đã chạy | Hợp lệ | RMSE ngoài mẫu (%) | Turnover hai chiều (%) |
|---|---:|---:|---:|---:|
| exact | 10/10 | 8 | 0.259 | 37.908 |
| milp_highs | 10/10 | 8 | 0.259 | 37.908 |
| hold | 10/10 | 2 | 0.343 | 0.000 |
| threshold_rebalance | 10/10 | 8 | 0.259 | 37.735 |
| periodic_rebuild | 10/10 | 6 | 0.198 | 200.000 |
| swap_annealing | 20/20 | 16 | 0.259 | 37.908 |
| qaoa_fixed | 20/20 | 16 | 0.259 | 37.908 |
| qaoa_rule | 20/20 | 16 | 0.259 | 37.908 |
| qaoa_random | 20/20 | 16 | 0.259 | 37.908 |
| qaoa_warm_start | 20/20 | 16 | 0.259 | 37.908 |
| qaoa_random_init | 20/20 | 16 | 0.241 | 81.502 |
| classical_circuit_search | 20/20 | 16 | 0.259 | 37.908 |
| qwen_circuit | 0/20 | 0 | — | — |
| qwen_mandate_classical | 0/10 | 0 | — | — |
| qwen_full_pipeline | 0/10 | 0 | — | — |

Giá trị trung bình chỉ gồm nghiệm hợp lệ; tỷ lệ thất bại phải được đọc cùng. Các seed không phải các mẫu tài chính độc lập.

## Bằng chứng và giới hạn

- Exact và MILP cùng mô hình; các nhánh QAOA không được đổi universe, K hoặc mục tiêu.
- Oracle pha chéo được dựng đầy đủ trên 2^N trạng thái; đây là chi phí cổ điển tăng theo hàm mũ và giới hạn quan trọng của prototype.
- Khởi tạo previous bảo toàn số tài sản khi dùng XY; không bảo đảm mọi giới hạn ngành/turnover.
- LLM disabled/error/invalid được ghi đúng trạng thái, không thay bằng quy tắc rồi gắn nhãn Qwen.
- Chuỗi benchmark đã được mở trong quá trình phát triển; tập test là tách theo giao thức, không phải dữ liệu tương lai mới thu.
- Gap phương pháp là giả thuyết; không khẳng định tính mới tuyệt đối từ việc tích hợp.

![Hình 1. Đánh đổi tracking–turnover](figures/01_tracking_turnover.png)

**Hình 1. Đánh đổi tracking–turnover.** Mỗi điểm là trung bình có điều kiện trên những nghiệm hợp lệ. Đọc cùng tỷ lệ khả thi ở Hình 2; đây không phải đường biên hiệu quả đã được chứng minh. Nguồn: synthetic.

![Hình 2. Tỷ lệ phương án đáp ứng yêu cầu](figures/02_feasibility.png)

**Hình 2. Tỷ lệ phương án đáp ứng yêu cầu.** Tất cả giới hạn được kiểm tra bằng mô hình gốc. Case không có nghiệm vẫn xuất hiện trong mẫu; bộ giải báo infeasible không phải là lỗi. Nguồn: synthetic.

![Hình 3. Khoảng cách tới nghiệm tối ưu](figures/03_objective_gap.png)

**Hình 3. Khoảng cách tới nghiệm tối ưu.** Khoảng cách tuyệt đối trên đúng cùng hàm mục tiêu; không chia cho giá trị tối ưu có thể gần 0. Phương án không hợp lệ được báo riêng. Nguồn: synthetic.

![Hình 4. Kiểm tra chuẩn hóa yêu cầu](figures/04_language_ablation.png)

**Hình 4. Kiểm tra chuẩn hóa yêu cầu.** Bộ yêu cầu tự biên soạn có nhãn chuẩn độc lập gồm diễn đạt lại, mâu thuẫn, phủ định và thiếu thông tin; kết quả nhỏ mang tính chẩn đoán. Nguồn: synthetic.

![Hình 5. Độ nhạy tracking–chi phí](figures/05_cost_frontier.png)

**Hình 5. Độ nhạy tracking–chi phí.** Nghiệm exact trên một fixture tổng hợp riêng, thay hệ số chi phí đã khai báo. Biểu đồ minh họa đánh đổi của mô hình, không dùng để chọn cấu hình từ tập test. Nguồn: separate_synthetic_fixture.

![Hình 6. Chất lượng và tài nguyên](figures/06_quality_resources.png)

**Hình 6. Chất lượng và tài nguyên.** Thời gian gồm dựng oracle và tối ưu; nhánh LLM tính thêm latency chọn mạch. Điểm trung bình có điều kiện không thay thế phân tích thất bại hay chứng minh speedup. Nguồn: synthetic.

![Hình 7. Khả năng thích nghi theo nhóm yêu cầu](figures/07_unseen_structure.png)

**Hình 7. Khả năng thích nghi theo nhóm yêu cầu.** Nhóm unseen là tổ hợp giới hạn không dùng để chọn cấu hình cố định. Nhóm không có nghiệm được giữ lại để kiểm tra phản hồi; không kỳ vọng tỷ lệ khả thi dương. Nguồn: synthetic.

## Tái lập

Xem protocol.json, benchmark.json, mandates_gold.json, summary.csv và figure_catalog.json trong cùng thư mục.