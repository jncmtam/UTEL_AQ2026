# Hồ sơ nghiên cứu AGQO Repair

## Quyết định và mục tiêu

Người quản lý đang có danh mục và mandate. Khi tài sản bị loại, giới hạn ngành thay đổi hoặc yêu cầu giao dịch thắt chặt, hệ thống so phương án giữ nguyên với sửa danh mục. Đầu ra là tập tài sản, thay đổi tỷ trọng, chi phí, mức tracking và bằng chứng tuân thủ. Bản đầu có K tài sản tỷ trọng bằng nhau; chi phí tính từ tỷ trọng trước giao dịch đã trôi theo thị trường. Đây là mô hình nghiên cứu danh mục rời rạc, chưa phải vận hành một ETF thật.

## Ma trận liên quan và phần khác biệt cần kiểm chứng

| Nguồn gốc | Đã có gì | Câu hỏi còn lại của dự án |
|---|---|---|
| [MSCI Index Tracking](https://www.msci.com/documents/10199/7bcc8d27-1780-4385-85dd-19fad2667435) | Tracking, giới hạn giao dịch/tài sản và rủi ro là nhu cầu nghiệp vụ đã có công cụ | Không dùng nguồn này để nói classical không giải được |
| [Lobo–Fazel–Boyd, transaction costs](https://web.stanford.edu/~boyd/papers/portfolio.html) | Tối ưu cổ điển, chi phí và bound mạnh | HiGHS/exact phải là đối chứng trên cùng mô hình |
| [Low-Turnover Rebalancing for Sparse Index Tracking](https://arxiv.org/abs/2512.22109v2) | Xây dựng và bảo trì, sửa cục bộ ít turnover | Maintenance tự nó không phải novelty; phải nghiên cứu thay đổi cấu trúc mandate |
| [Financial Index Tracking via Quantum Computing](https://arxiv.org/abs/2208.11380) | Cardinality và quantum index tracking | Không tuyên bố mới chỉ từ việc chọn ít cổ phiếu bằng quantum |
| [Quantum Portfolio Optimization: Extensive Benchmark v3](https://arxiv.org/abs/2509.17876v3) | MIP/heuristic mạnh trên biến thể được khảo sát | Cần kiểm chứng lợi ích riêng của QAOA, không suy từ NP-hard |
| [Agent-Q](https://arxiv.org/abs/2504.11109v2) | LLM sinh mạch/khởi tạo | Đóng góp ứng viên là đề xuất có kiểm chứng theo mandate và generalization |
| [Autonomous Variational Quantum Circuit Design](https://arxiv.org/abs/2606.13380) | Vòng lặp thiết kế–validator–evaluator | Vòng lặp agent không tự tạo novelty tài chính |
| [XY topologies and warm starting](https://www.nature.com/articles/s41534-026-01192-4) | Lựa chọn topology và khởi tạo có prior art | Cần so baseline tương ứng, ghi rõ prototype chỉ dùng basis incumbent/random |
| [Decomposition pipeline for portfolio optimization](https://journals.aps.org/prresearch/abstract/10.1103/PhysRevResearch.7.023142) | Chia bài toán constrained portfolio thành subproblem | Thu hẹp universe phải đo sai số và chi phí, không đổi âm thầm |

Đây là rà soát có giới hạn, không phải systematic review hoặc chứng minh tính mới. **Research gap vẫn là ứng viên**: liệu trích xuất mandate có bằng chứng và chọn mạch theo cấu trúc có thích nghi tốt hơn khi các ràng buộc được kết hợp theo cách chưa thấy hay không?

## Giả thuyết và điều kiện bác bỏ

**H1 — giá trị quyết định.** Trên các mandate khả thi, hệ thống sửa danh mục khôi phục tuân thủ và đưa ra đánh đổi tracking–chi phí tốt hơn giữ nguyên vi phạm hoặc tái xây bỏ qua chi phí. Đọc đường biên/độ nhạy và held-out tracking. Nếu classical đã đạt cùng kết quả nhanh hơn thì đó là giá trị bài toán/workflow, chưa phải đóng góp quantum.

**H2 — giá trị AI.** Qwen đạt độ đúng ngữ nghĩa/khả năng từ chối tốt hơn parser trên paraphrase và các trường hợp lỗi, đồng thời không làm sai các yêu cầu chuẩn. Sai đơn vị, mất điều kiện và nguồn trích dẫn sai được tính là thất bại. Chọn mạch LLM được so với fixed/rules/random/classical search cùng catalog.

**H3 — giá trị mạch thích nghi.** Ở cùng tổng shots (tính mọi candidate và phép đo cuối), cấu hình do Qwen đề xuất giảm gap tới optimum, tăng feasibility hoặc đạt đánh đổi tài nguyên tốt hơn fixed chọn trên development. Chi phí dựng oracle, inference, tối ưu và retry đều phải hiện diện. Cải thiện không ổn định giữa case hoặc không bù latency bác bỏ lợi ích thực tiễn đang kỳ vọng.

Không đặt ngưỡng tiết kiệm tiền tùy tiện khi chưa có người dùng nghiệp vụ xác nhận. Corpus nhỏ và các cửa sổ dùng chung thị trường chỉ cho phân tích mô tả; không tuyên bố ý nghĩa thống kê từ seed. Chỉ mở rộng sample và đăng ký ngưỡng kinh tế sau khi đã có dữ liệu đáng tin và cấu hình khóa.

## Thiết kế đã cài

Gold mandate + exact/HiGHS; gold + QAOA fixed/rules/random/incumbent/random-init; gold + search classical tính toàn bộ ngân sách; gold + Qwen circuit; Qwen mandate + classical; Qwen mandate + Qwen circuit. Các nghiệm từ pipeline LLM được chấm lại bằng mandate gốc để không được hưởng lợi từ việc bỏ sót giới hạn.

Nhóm thị trường thay đổi dùng các cửa sổ nối tiếp. Trong cùng cửa sổ, thay mandate để cô lập hiệu ứng yêu cầu. Development có cardinality và exclusion; test thêm các tổ hợp gồm inclusion/turnover/sector và bài toán không có nghiệm. Protocol được ghi trước khi chạy test; fixed circuit không được chọn từ test. LLM không nhận nghiệm exact hoặc future returns trong prompt chọn mạch.

## Hướng khai thác sau khi có bằng chứng

1. Tăng corpus do chuyên gia gán nhãn và adjudication; phân biệt kiểm chứng nguồn trích dẫn với chứng minh ngữ nghĩa.
2. Thay oracle bảng đầy đủ bằng encoding có slack/ancilla hoặc mixer chuyên biệt; xác minh cả reachability và tài nguyên thực của ràng buộc.
3. So relaxation warm-start/parameter transfer mạnh hơn basis initialization hiện tại.
4. Đánh giá dữ liệu thị trường có total-return, thành phần theo thời điểm và chi phí triển khai quan sát được.
5. Chỉ đo phần cứng khi có backend và ngân sách đã xác nhận, cùng classical comparator đủ mạnh.

## Kịch bản bảo vệ

“Một danh mục đang hoạt động có thể vi phạm yêu cầu mới. Chúng tôi biến yêu cầu thành mô hình có nguồn bằng chứng, so giữ nguyên với các phương án sửa trên cùng mục tiêu tracking–chi phí, rồi kiểm tra mọi nghiệm. LLM và QAOA được đánh giá riêng. Benchmark cho biết từng thành phần đã tạo thêm giá trị hay chưa; không dùng một mạch hợp lệ làm bằng chứng lợi thế tài chính.”
