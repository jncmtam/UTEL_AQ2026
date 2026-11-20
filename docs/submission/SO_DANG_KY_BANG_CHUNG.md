# Sổ đăng ký bằng chứng (vòng bán kết)

Mỗi con số tiêu đề dùng trong deck, báo cáo, tài liệu và prototype. “Duyệt” = được dùng trên slide chính; “Phụ lục” = chỉ dùng ở
phụ lục hoặc khi được hỏi; “Không dùng” = có trong lịch sử nhưng đã bị thay. Bằng chứng V3 nằm ở `results/final/` (thẻ v3.1.0);
bằng chứng V3.2 ở `results/runs/<run_id>/`, mỗi thư mục có `run.json` (commit, mã băm dữ liệu 7f076128…3042, cấu hình).

| # | Khẳng định | Giá trị | Định nghĩa chỉ số | So với | Tài khoản | Thời gian | Độ bất định | Nguồn | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Một lô VIC so với tài khoản | 110% | giá 1 lô / 20 triệu | — | 20 triệu | đóng cửa 01/10/2026 | — | data/vn30 (snapshot) → `c1_lot_cost.csv` | Duyệt |
| 2 | Mã có một lô > 10% tài khoản | 26/30 | như trên | — | 20 triệu | 01/10/2026 | — | `c1_lot_cost.csv` | Duyệt |
| 3 | Sai số bám **thực tế**, không quy tắc | làm tròn 12,14% · tham lam 7,47% · AGQO 6,77% | độ lệch chuẩn năm hoá của chênh lệch lợi suất ngày so với chỉ số giá VN30 | làm tròn, tham lam | 20 triệu | 12 lần tái cân bằng theo quý 01/2024–10/2026, giữ đến 13/11/2026 | AGQO − làm tròn −5,37 [−6,93; −3,84]; AGQO − tham lam −0,69 [−1,53; +0,02] (bootstrap khối 21 ngày) | `results/runs/20261120-084148-39544db-account-sizes`; trùng V3 `results/final/sweep.csv` | Duyệt |
| 4 | Ở 100 triệu khác biệt nhỏ | −0,07 điểm % [−0,19; +0,04] | như trên | làm tròn | 100 triệu | như trên | khoảng tin cậy qua 0 | V3 `results/final/extras/robustness.csv` | Duyệt |
| 5 | Sai số bám thực tế **có hai quy tắc** | làm tròn 12,67% · tham lam 9,82% · AGQO 9,91% | như #3; quy tắc kiểm tra trên NAV sau phí | làm tròn, tham lam cùng quy tắc | 20 triệu | như #3 | AGQO − làm tròn −2,76 [−3,90; −1,63]; AGQO − tham lam +0,09 [−0,76; +1,01] | `results/runs/20261120-083954-df815a9-pitch` | Duyệt |
| 6 | Quyết định ví dụ (**ước tính**) | AGQO 11,78% · làm tròn 17,68% · tham lam 11,71% · lý tưởng 8,78% | sai số bám ước tính từ hiệp phương sai 250 phiên trước ngày | như trên | 20 triệu, bỏ BĐS, NH ≤ 30% | một quyết định 01/10/2026 | không có (một quyết định) | `pitch_decision.json`; chạy trực tiếp trên prototype cho cùng số | Duyệt |
| 7 | Tiền mặt sau phí, phí, ngân hàng thực tế | 5.002.538 đ · 22.463 đ · 29,38% | tiền mặt sau phí; tỷ trọng trên NAV sau phí | trần 30% | như #6 | 01/10/2026 | — | `pitch_decision.json` | Duyệt |
| 8 | Xác suất gần tối ưu mỗi lần đo | AGQO 21,3% · warm start 3,1% · sách giáo khoa 1,1% · tìm kiếm ngẫu nhiên 7,7% · lịch cố định 23,8% · k-NN không tinh chỉnh 24,0% · oracle 25,2% | P(đủ tiền, thỏa quy tắc, khoảng cách chuẩn hoá ≤ 5%); chuẩn hoá: (mục tiêu − tối ưu)/(trung vị khả thi − tối ưu) | các mạch khác | 100 triệu (tài khoản theo thời gian) | 12 quý 2024–2026; mô phỏng statevector không nhiễu, 16 qubit, 512 lần đo | 12/12 quý, Wilcoxon p = 0,0005 cho AGQO vs warm start/sách giáo khoa/ngẫu nhiên; vs lịch cố định p = 0,47 | `results/final/quantum_test.csv`, `quantum_stats.json` | Duyệt |
| 9 | Tỷ số | 6,9× warm start · 19× sách giáo khoa | tỷ số các trung bình của #8 | — | như #8 | như #8 | KTC tỷ số 4,9–15,8 (warm start) | `quantum_stats.json` | Duyệt (nêu sau xác suất tuyệt đối) |
| 10 | Liệt kê cổ điển | ~0,12 giây ở 16 qubit; 2,4 giây ở 20 | thời gian liệt kê toàn bộ 2^n | — | — | lần chạy đã lưu | — | `results/final/extras/scaling.csv` | Duyệt |
| 11 | Mô hình nhiễu ESP | 1,57× warm start, hơn ở 11/12 quý | tỷ số các trung bình của xác suất ước tính ESP | warm start (ESP) | 100 triệu | 12 quý | ước tính, không phải phần cứng | `results/final/extras/hardware_aware.csv` | Phụ lục |
| 12 | Mô phỏng nhiễu Aer | 3 quý; cổng hai qubit sau biên dịch 2–34, trung bình 16 | mô phỏng FakeKingston | — | — | 2024-01, 2025-07, 2026-10 | 3 điểm | `hardware_aware.csv` | Phụ lục |
| 13 | Quy mô | lịch cố định 30,0% (8 qubit) → 12,9% (20 qubit); tỷ số 4,3× → 16,7× | như #8 | warm start | — | không nhiễu | — | `scaling.csv` | Phụ lục |
| 14 | LLM V3 | 35/35 ràng buộc hiệu lực · 33/35 JSON nghiêm ngặt · từ khóa 24/35 | trên bộ 35 câu do nhóm viết | quy tắc từ khóa | — | — | bộ câu nhóm viết | `results/final/llm/mandate_eval.json` | Phụ lục |
| 15 | LLM V3.2 | 49/50 đúng đến tận lệnh (từ khóa 33/50, prompt V3 46/50) | kết quả cuối sau bộ tối ưu, so với nhãn chuẩn | từ khóa | theo từng câu | — | McNemar p = 3·10⁻⁵ vs từ khóa; p = 0,25 vs prompt V3 | `results/runs/20261120-073653-2291b6a-llm-mandates` | Duyệt (kèm “bộ câu nhóm viết”) |
| 16 | Lời giải thích V3 | số liệu 12/12 khớp; kiểm tra ngữ cảnh 11/12 | kiểm tra tự động | — | 100 triệu | 12 quý | — | `results/final/llm/explanations.json` | Phụ lục |
| 17 | Kiểm tra V3.2 trên lời giải thích V3 | 3/12 bị loại (nói thị trường không cho mua bán lô lẻ), gồm ví dụ đã công bố | kiểm tra khẳng định về thị trường | — | — | — | — | `tests/test_v32_product.py` | Phụ lục |
| 18 | Ràng buộc: hiểu / xác nhận / thỏa | hiểu: LLM hoặc từ khóa · xác nhận: người dùng bấm · thỏa: kiểm tra trên NAV sau phí | ba trạng thái khác nhau | — | — | — | — | prototype; `tests/test_v32_review.py` | Duyệt |
| 19 | Lô lẻ | 2,53% (phí chênh 0–2%: 2,53–2,60%) | sai số bám thực tế, khớp mô phỏng tại giá đóng cửa | — | 20 triệu | 12 quý | chưa mô hình hoá thanh khoản | `extras/robustness.csv` | Duyệt (ghi “mô phỏng”) |
| 20 | ETF E1VFVN30 | 9,28% (ngày) · 5,17% (tuần) | giá thị trường của quỹ so với chỉ số giá VN30 | — | mua và giữ | 2024–2026 | nhiễu giá thị trường | `strategy_performance.csv` | Duyệt |
| 21 | Giới hạn giá đã điều chỉnh | AGQO − làm tròn −4,9 đến −5,4 điểm % khi giá lô cao hơn 0–50% | tài khoản tương đương 20M/f | làm tròn, tham lam | 13,3–20 triệu | 12 quý | không đo được chênh riêng từng mã | `results/runs/20261120-073913-5c9f384-account-benchmark` | Phụ lục |
| 22 | k-NN V3.2 | +0,76 điểm % vs lịch cố định (20/22 tháng, p = 0,0002); bằng lịch theo cỡ tài khoản | xác suất mỗi lần đo | lịch cố định | 5 cỡ × 3 loại quy tắc | holdout 22 tháng 2024–2026 | — | `results/runs/20261120-073008-ab60365-knn-study` | Phụ lục |
| 23 | Độ trễ | CPU 5–11 giây (container ấm); Qwen ~4 giây (GPU ấm); 440 giây (GPU lạnh, nạp 309 giây) | thời gian đo | — | — | các lần chạy 11/2026 | — | `prototype_live_example.json`; agent.md | Duyệt |
| — | “Thị trường không cho mua bán lô lẻ” | — | — | — | — | — | — | 3 lời giải thích V3 | Không dùng |
| — | “12,1% → 6,8%” không kèm tham lam | — | — | — | — | — | thiếu mốc mạnh | trang V3 | Không dùng nếu đứng một mình |

Chi tiết cần đội xác nhận: mã đội, tên đội, thành viên, giảng viên; thời lượng trình bày theo thông báo mới nhất của BTC; có được phép
dùng câu trả lời LLM phát lại trong demo hay không.
