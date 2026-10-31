# AGQO Repair — bản triển khai và kết quả kiểm chứng

Đã triển khai một prototype end-to-end: mandate có bằng chứng → mô hình tracking–chi phí → exact/HiGHS/annealing/QAOA → kiểm tra nghiệm → phương án giao dịch và giao diện cục bộ. Qwen3-8B đã được gọi thực qua endpoint `repair_json` trên Modal; các raw response, lần retry, token và latency nằm trong audit. Lần tái lập dùng lại bản ghi đúng request hash và được gắn `cached_live_record`.

## Bằng chứng đã chạy

- Toàn bộ suite: **50 tests passed**. Có kiểm tra objective/encoding mọi bit trên bài nhỏ, nghiệm tối ưu MILP so exact, trạng thái Qiskit so simulator, ràng buộc, cutoff, ngân sách shots và API.
- Ba bộ kết quả: tổng hợp không LLM, tổng hợp với Qwen, OR-Library. Có **644 bản ghi solver ở test và 96 ở development**; đây là bản ghi lặp/cặp, không phải 740 mẫu tài chính độc lập.
- Mỗi bộ có protocol khóa trước lượt chạy, hash mã nguồn và instance, JSON/CSV, bảy biểu đồ có caption và báo cáo. `verification.json` xác nhận hash, mọi nghiệm được chấm theo mục tiêu gốc và tổng shots không vượt ngân sách.
- Demo đã xuất mạch QASM 3 thực, có metadata transpile. Trạng thái mạch được đối soát với simulator trong tests.
- Giao diện đã kiểm tra trên bố cục hẹp và desktop: chuẩn hóa, bằng chứng nguồn, chặn yêu cầu mâu thuẫn, chạy quyết định và hiển thị giao dịch/đối chứng. Ảnh: `ui-desktop.jpg`.

## Kết quả chính và cách diễn giải

**Hiểu yêu cầu:** corpus biên soạn 12 trường hợp. Parser đúng 11/12; Qwen đúng 10/12 theo tiêu chí ngữ nghĩa/trạng thái. Qwen xử lý được một paraphrase parser từ chối, nhưng hai phản hồi khác bị validator loại. Các phản hồi invalid được tính là thất bại, không biến mất khỏi mẫu. Kết quả này chưa chứng minh LLM tốt hơn parser; validator đã ngăn dùng các phản hồi sai.

**Bộ giải:** trên benchmark tổng hợp có 10 case test, exact và HiGHS đều xác nhận 8 case có nghiệm và 2 case không có nghiệm. QAOA fixed và Qwen-selected đều tìm được nghiệm tối ưu trong 16/20 lượt seed/case; bốn lượt còn lại thuộc hai case không có nghiệm. Vì chất lượng ở các case khả thi bằng nhau, chưa có bằng chứng chọn mạch bằng LLM cải thiện nghiệm.

Thời gian trung bình đo/ghi nhận trên các lượt này khoảng **0,014 giây cho fixed QAOA** và **4,49 giây cho Qwen-selected QAOA**, tính thêm latency inference đã lưu. Đây là số liệu máy hiện tại/call đã ghi, không phải cam kết SLA hoặc ước lượng chi phí cloud. Chọn mạch bằng LLM chưa bù được chi phí tăng thêm ở bộ bài nhỏ này.

**Quy mô:** case study OR-Library dùng tám tài sản đầu và chỉ số công khai, không gán ngành giả. Audit riêng so với HiGHS toàn bộ 31 tài sản cho thấy các case khả thi mất khoảng **0,000082–0,000158 đơn vị hàm mục tiêu** do thu hẹp universe. Đây là chênh lệch tracking MSE cộng phí có trọng số, không phải tỷ lệ lợi nhuận. Vì thế không được lấy QAOA tám mã so với toàn bộ 31 mã rồi quy chênh lệch cho solver.

## Những gì chưa được xác lập

- Giá trị tích hợp và kiểm chứng đã được thể hiện; ưu thế LLM, ưu thế lượng tử và tiết kiệm thực tế cho quỹ **chưa được chứng minh**.
- Research gap vẫn là giả thuyết cần rà soát, không phải chứng nhận tính mới.
- Oracle diagonal `2^N` có chi phí cổ điển hàm mũ; prototype giới hạn N<=12. Bản benchmark đã chạy ở N=8, K=4. Đây không phải bài toán đủ khó để chứng minh lợi thế tính toán.
- Ràng buộc và ngành của fixture tổng hợp là kịch bản biên soạn. OR-Library thiếu ngày/ngành/treatment độc lập, nên không năm hóa hoặc gọi đây là vận hành một quỹ thật.
- Các cửa sổ lịch sử đã được mở trong phát triển. Việc tách test theo protocol không biến chúng thành dữ liệu tương lai hoàn toàn mới.
- Warm-start hiện là basis incumbent, không phải relaxation warm-start hay phương pháp học tham số. Tax, execution lots, spread quan sát, market impact và QPU chưa thuộc bản triển khai này.

## Mở ứng dụng và tái lập

Tại thư mục dự án:

```sh
.venv/bin/python -m agqo.repair serve --llm modal
```

Mở `http://127.0.0.1:8765`. Có thể dùng `serve` không có `--llm modal` để chạy hoàn toàn cục bộ và ghi LLM là chưa chạy.

Hướng dẫn: [REPAIR_GUIDE](../../docs/REPAIR_GUIDE.md). Cơ sở nghiên cứu và giới hạn novelty: [REPAIR_RESEARCH](../../docs/REPAIR_RESEARCH.md).

- [Báo cáo tổng hợp](REPORT.md)
- [Báo cáo Qwen](live/REPORT.md)
- [Báo cáo OR-Library](or_library/REPORT.md)
- [Kiểm chứng artifact](verification.json)
- [Mạch demo](demo/qaoa_rule.qasm)
