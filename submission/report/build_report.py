"""Apply the owner's review to their own edited report: English figures, English technical terms, parameter tables,
sentence-initial capitals.

    python submission/report/figures.py                    # figures first
    python submission/report/build_report.py <owner.docx>
        -> submission/drafts/report-<UTC>/AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.docx

The owner's file stays the source of truth: paragraphs are located by their opening words, not by index, and
everything not named here is left as the owner wrote it (apart from the term list and the capital pass).
Inline markup in the strings below: **bold**, `code`, _{subscript}, ^{superscript}.
"""

from __future__ import annotations

import copy
import unicodedata
import re
import sys
import time
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Emu

ROOT = Path(__file__).resolve().parents[2]
FIG = Path(__file__).resolve().parent / "figures"

# ------------------------------------------------------------------ figures: media part -> new png
FIGURES = {"image3.png": "f1a_lot_cost.png", "image4.png": "f1b_one_decision.png", "image5.png": "f2_market.png",
           "image6.png": "f3_pipeline.png", "image7.png": "f4_probability.png", "image8.png": "f5_circuit.png",
           "image9.png": "f6_hardware.png", "image12.png": "f8a_accounts.png", "image13.png": "f8b_scaling.png"}
SHOTS = ROOT / "docs" / "assets" / "screenshots"
FIGURES.update({"image10.png": SHOTS / "pitch_constraints_pending.png", "image11.png": SHOTS / "infeasible.png"})
WIDTH_CM = {"image6.png": 16.5, "image8.png": 15.5, "image7.png": 9.2, "image9.png": 9.0, "image5.png": 9.0, "image10.png": 8.1, "image11.png": 8.1, "image3.png": 7.4, "image4.png": 8.0}
FIRST_COL = 2650                                             # twips, label column of the new tables          # the two wide diagrams get the full text width

# ------------------------------------------------------------------ English technical terms (longest first)
TERMS = [
    ("tìm kiếm ngẫu nhiên thiết kế mạch", "random circuit search"),
    ("QAOA sách giáo khoa", "textbook QAOA"),
    ("khởi động cổ điển", "warm-start baseline"),
    ("hơn khởi động ấm", "hơn warm-start baseline"),
    ("(khởi động ấm)", "(warm-start baseline)"),
    ("độ tự tin khởi động ấm", "warm-start confidence"),
    ("khởi động ấm", "warm start"),
    ("Lượt đo trúng nghiệm gần tối ưu", "Tỷ lệ shot near-optimal"),
    ("lượt đo trúng nghiệm trong 5% tối ưu", "shot near-optimal (trong 5% quanh exact optimum)"),
    ("512 lần đo", "512 shots"), ("lần đo", "shot"), ("lượt đo", "shot"),
    ("thanh ghi 16 qubit an toàn trần", "16-qubit cap-safe register"),
    ("thanh ghi an toàn trần", "cap-safe register"),
    ("thanh ghi nhiều lô", "multi-lot register"),
    ("nghiệm nới lỏng", "continuous relaxation"),
    ("QP liên tục có trần", "capped continuous QP"),
    ("liệt kê cổ điển", "exhaustive enumeration"), ("phép liệt kê", "exhaustive enumeration"),
    ("liệt kê", "exhaustive enumeration"),
    ("Thuật toán tham lam", "Thuật toán greedy"), ("Tham lam", "Greedy"), ("tham lam", "greedy"),
    ("Làm tròn lô gần nhất", "Nearest-lot rounding"), ("làm tròn lô gần nhất", "nearest-lot rounding"),
    ("(làm tròn lô)", "(nearest-lot rounding)"), ("so với làm tròn", "so với nearest-lot rounding"),
    ("Làm tròn lô", "Nearest-lot rounding"),
    ("giải mã theo lược đồ JSON", "JSON-schema constrained decoding"),
    ("mã kiểm tra lược đồ", "code kiểm tra JSON schema"), ("lược đồ JSON", "JSON schema"),
    ("kiểm định chéo", "cross-validation"), ("bootstrap khối", "block bootstrap"),
    ("sai lệch sống sót", "survivorship bias"),
    ("Số cược độc lập", "Effective number of bets"), ("số cược độc lập", "effective number of bets"),
    ("cược độc lập", "effective bets"),
    ("nhân tố thị trường", "market factor"), ("nhân tố chung", "market factor"),
    ("mạch nông 16 CZ do AI chọn theo nhiễu", "shallow circuit noise-aware 16 CZ do AI chọn"),
    ("AI chọn mạch nông theo nhiễu", "AI chọn shallow circuit noise-aware"),
    ("AI chọn mạch nông", "AI chọn shallow circuit"),
    ("mạch nông", "shallow circuit"), ("Mạch sâu", "Deep circuit"), ("mạch sâu", "deep circuit"),
    ("mạch theo nhiễu", "mạch noise-aware"),
    ("tinh chỉnh COBYLA", "COBYLA polish"), ("QAOA + tinh chỉnh", "QAOA + COBYLA polish"),
    ("có tinh chỉnh hay không", "có COBYLA polish hay không"),
    ("trùng tối ưu chính xác", "trùng exact optimum"), ("= tối ưu chính xác", "= exact optimum"),
    ("tới tối ưu chính xác", "tới exact optimum"), ("kết luận kiểm chứng chính xác", "kết luận exact verification"),
    ("ngân sách cổng hai qubit", "two-qubit gate budget"), ("vòng quay", "turnover"),
    ("ma trận J", "coupling matrix J"), ("từng cặp tương tác ZZ", "từng cặp ZZ coupling"),
    ("lịch mạch", "circuit schedule"), ("AI chọn lịch", "AI chọn schedule"), ("1.080 lịch", "1.080 schedule"),
    ("chọn đúng lịch", "chọn đúng schedule"), ("lịch góc", "angle schedule"),
    ("ưu thế lượng tử", "quantum advantage"), ("chọn lịch", "chọn schedule"),
    ("quy tắc từ khoá", "keyword parser"),
    ("Rò rỉ thông tin", "Data leakage"),
    ("12 quý chưa từng thấy", "12 quý out-of-sample"),
    ("LLM calls mới", "LLM call mới"),
    ("Hiệp biến động", "Hiệp phương sai"), ("hiệp biến động", "hiệp phương sai"),
]

# ------------------------------------------------------------------ whole-paragraph rewrites (opening words -> text)
REWRITE = {
    "AGQO giúp nhà đầu tư cá nhân vốn nhỏ":
        "AGQO giúp nhà đầu tư vốn nhỏ sở hữu một danh mục “VN30 theo cách của mình” (bỏ mã, giới hạn ngành, giữ tiền "
        "mặt) chỉ bằng lệnh lô chẵn 100 cổ phiếu. Cái khó: Với 20 triệu đồng, một lô VIC đã đắt hơn cả tài khoản, nên "
        "bài toán thật là chọn mua những lô nào, một bài toán tổ hợp với 65.536 phương án. LLM mã nguồn mở Qwen3.8-27B "
        "đọc yêu cầu tiếng Việt thành ràng buộc kiểm tra được, mạch QAOA 16 qubit do dữ liệu thiết kế lấy mẫu các "
        "phương án tốt, exhaustive enumeration kiểm chứng từng quyết định. Trên 12 quý out-of-sample, danh mục 20 triệu "
        "lệch khỏi VN30 ít hơn gần một nửa (tracking error 12,1% → 6,8%), 0 vi phạm quy tắc.",
    "Hình 1. Trái":
        "Hình 1. Trái: Giá một lô của 30 mã VN30 so với tài khoản 20 triệu (2026-10-01), 26/30 mã vượt 10% tài khoản, "
        "VIC vượt cả tài khoản. Phải: Một quyết định thật cho tài khoản mới 20 triệu. Nearest-lot rounding cho TE 18,4%, "
        "greedy 10,8% (dồn 36% vào MWG), AGQO 9,5% (= exact optimum).",
    "Nguyên nhân gốc":
        "Nguyên nhân gốc: Bộ tối ưu cho tỷ trọng liên tục (“giữ 3,4% VIC”) nhưng tài khoản chỉ giữ được 0 hoặc trọn lô. "
        "Yêu cầu nghiệp vụ: (i) Chỉ lệnh lô chẵn, đủ tiền sau phí 0,15% và thuế "
        "bán 0,1%. (ii) Tuân thủ tuyệt đối quy tắc cá nhân. (iii) Bám VN30 sát nhất. (iv) Giải thích bằng tiếng Việt, "
        "kiểm chứng được.",
    "- Giá: API":
        "- **Giá:** API công khai của DNSE, OHLCV ngày 04/01/2022–13/11/2026 cho 40 mã từng thuộc VN30, chỉ số VN30, "
        "VN-Index và ba ETF VN30 (E1VFVN30, FUESSV30, FUEKIV30). Giá đã được nhà cung cấp điều chỉnh.",
    "- Ngôn ngữ: 35":
        "- **Ngôn ngữ:** 35 câu yêu cầu tiếng Việt có nhãn chuẩn do đội soạn. Dữ liệu công khai, chỉ dùng cho nghiên cứu. "
        "Mỗi tệp có SHA-256 trong manifest để kiểm tra toàn vẹn.",
    "- Tải tự động":
        "Dữ liệu được tải tự động bằng `python -m agqo download`, kiểm tra điều chỉnh giá, lọc mã thiếu lịch sử và "
        "áp dụng covariance shrinkage trước khi dùng. Kết quả từng bước nằm ở Bảng 1.",
    "Chống rò rỉ":
        "**Chống data leakage:** Mọi lựa chọn (hệ số phạt λ, circuit schedule, k của k-NN, có COBYLA polish hay không) "
        "chỉ học trên 48 bài toán năm 2023 (12 tháng × 4 cỡ tài khoản). Kiểm định trên 12 quý out-of-sample "
        "01/2024–10/2026, rổ VN30 theo thời điểm, so sánh cặp bằng Wilcoxon và block bootstrap 21 ngày. Nhờ vậy mọi con số "
        "là kết quả nhà đầu tư thực sự nhận được nếu dùng AGQO từ đầu 2024, không phải kết quả chỉnh cho đẹp trên dữ liệu "
        "kiểm tra.",
    "- Đặc trưng thị trường":
        "- **Đặc trưng thị trường:** Tương quan trung bình, tỷ trọng market factor, effective number of bets (Meucci 2009, "
        "trung bình ≈ 13), cụm tương quan ≥ 0,5.",
    "- Đặc trưng bài toán":
        "- **Đặc trưng cho k-NN:** Warm-start confidence, tỷ lệ qubit đã rõ, log(field/coupling), coupling concentration, "
        "cỡ lô. Không tạo dữ liệu giả vì sẽ làm sai cấu trúc tương quan thật.",
    "Hình 2.":
        "Hình 2. 30 mã VN30 chỉ tương đương ~13 effective bets, market factor chiếm ~40% biến động (12 quý). Nhiều "
        "mã thay thế được cho nhau, nên tài khoản nhỏ không cần mua đủ 30 mã mà cần đúng tổ hợp mã vừa túi tiền.",
    "Dữ liệu → AI":
        "Sáu bước, mỗi bước do đúng một thành phần làm việc nó giỏi nhất và bị kiểm tra chéo (Hình 3). **AI** đọc thị "
        "trường và yêu cầu, **QUBO** mã hoá bài toán lô chẵn, **k-NN** chọn schedule, **QAOA** đề xuất 512 mẫu nhưng "
        "không tự quyết, **exhaustive enumeration** là trọng tài, **LLM** chỉ diễn giải và mọi con số đều được đối chiếu.",
    "Hình 3.":
        "Hình 3. Kiến trúc AGQO. Màu cho biết thành phần đảm nhận từng bước: AI, quantum, tính toán cổ điển chính xác, "
        "dữ liệu và đầu ra.",
    "Trên 12 quý kiểm định, mạch AGQO":
        "Trên 12 quý kiểm định, mạch AGQO đưa **21,3% số shot** vào vùng near-optimal (trong 5% quanh exact optimum), "
        "gấp **6,9×** warm-start baseline, 19× textbook QAOA và 2,8× random circuit search. AGQO thắng 12/12 quý "
        "(p = 0,0005). Quyết định tốt nhất trong 512 mẫu trùng exact optimum ở 12/12 quý (tài khoản 100 triệu).",
    "Hình 4.":
        "Hình 4. Phân bố xác suất đo trên 65.536 tổ hợp theo khoảng cách tới exact optimum, trung bình 12 quý.",
    "Ở 16 qubit, liệt kê":
        "Ở 16 qubit, exhaustive enumeration giải chính xác trong 0,12 giây nên đội không tuyên bố quantum advantage. "
        "Greedy đạt 7,5% (AGQO 6,8%), khác biệt chưa có ý nghĩa thống kê. Lô lẻ bám tốt hơn khi phụ phí lô lẻ dưới 6,8% "
        "(20 triệu) nhưng có rủi ro khớp lệnh chưa mô hình hoá. Deep circuit p = 6 chưa chạy được trên phần cứng nhiễu, "
        "AI chọn shallow circuit 16 cổng CZ thay thế.",
    "Hình 5.":
        "Hình 5. Mạch AGQO (4/16 qubit): Warm start R_{Y}(θ_{k}), cost layer R_{ZZ}, R_{Z}, aligned mixer "
        "U_{M}(β) = R_{Y}(θ_{k})R_{Z}(−2β)R_{Y}(−θ_{k}). Phải: Góc sau COBYLA polish (nét đứt: Linear-ramp khởi tạo).",
    "Hình 6.":
        "Hình 6. Mô phỏng nhiễu IBM Heron: Deep circuit bị nhiễu xoá, shallow circuit 16 CZ do AI chọn vẫn hơn warm-start "
        "baseline 1,6× (11/12 quý). AGQO chọn độ sâu theo nhiễu, không theo lý thuyết.",
    "Prototype web (FastAPI":
        "Prototype web (FastAPI + ECharts, triển khai trên Modal, CPU, tự co giãn) chạy thật toàn bộ quy trình cho một "
        "tài khoản mới trên dữ liệu 01/10/2026: LLM dịch yêu cầu → thống kê thị trường → Hamiltonian → AI chọn schedule "
        "→ QAOA 512 shots → exhaustive enumeration 65.536 tổ hợp → lệnh, phí, kiểm tra quy tắc → LLM giải thích có "
        "đối chiếu số. Câu mẫu phát lại câu trả lời thật đã lưu của Qwen3.8, câu mới gọi GPU H100 trực tiếp. Chưa có: "
        "Đặt lệnh thật, tài khoản người dùng.",
    "Mở link →":
        "Mở link → chọn mẫu hoặc gõ yêu cầu (ví dụ “Không đầu tư bất động sản, ngân hàng tối đa 30%”) → xem các ô ràng "
        "buộc có nhãn nguồn → **Xác nhận** → **Chạy trên Modal** → lệnh, phí, tiền mặt sau phí, kiểm tra từng quy tắc → "
        "**Bên trong quyết định này** (Hamiltonian, mạch, phân bố xác suất, **Tải mạch OpenQASM**). Câu mơ hồ bị hỏi lại, "
        "yêu cầu không khả thi được giải thích, không tạo lệnh.",
    "Hình 7.":
        "Hình 7. Prototype chạy thật (20/11/2026). Trái: Ràng buộc đọc từ câu lệnh, có nhãn nguồn, chờ xác nhận, "
        "nút Chạy khoá. Phải: Yêu cầu không khả thi (mỗi mã ≤ 2%) được giải thích bằng quy tắc chặn, không tạo lệnh.",
    "Hình 8.":
        "Hình 8. Trái: Sai số bám VN30 thực tế theo cỡ tài khoản, 12 quý. Phải: Từ 8 đến 20 qubit, mạch AGQO giữ nguyên "
        "schedule chọn trên dữ liệu 2023 (không học lại) vẫn hơn warm-start baseline, từ 4,3× lên 16,7×. Lợi thế tăng "
        "theo quy mô.",
    "Chia vai":
        "Chia vai: Thành viên A trả lời về tài chính (sai số bám, lô lẻ, ETF), B về lượng tử (QAOA, nhiễu, quantum "
        "advantage), C về AI/LLM (Qwen3.8, kiểm chứng, chi phí). Đã chuẩn bị 75 câu hỏi phản biện kèm số liệu. Năm câu "
        "khó nhất đã được tập dượt: Không có quantum advantage, greedy gần bằng, lô lẻ bám tốt hơn, k-NN schedule chưa "
        "hơn frozen schedule, ETF lợi nhuận cao hơn 1,1%/năm. Nguyên tắc: Trả lời bằng số đo, nói rõ giả định.",
    "MINH CHỨNG BỔ SUNG: Hình 1":
        "MINH CHỨNG BỔ SUNG: Hình 1 tái lập bằng python submission/report/figures.py.",
    "MINH CHỨNG BỔ SUNG: 24/25":
        "MINH CHỨNG BỔ SUNG: 24/25 kiểm thử đạt (pytest), nhật ký LLM trong results/final/llm.",
}

# ------------------------------------------------------------------ list blocks -> tables
# (first paragraph opening, last paragraph opening, header, rows, paragraph to keep before the table or None)
TABLES = [
    ("Bài toán tối ưu tổ hợp", "Thước đo:", ("Thành phần", "Nội dung"), [
        ("Loại bài toán", "QUBO: Mỗi quyết định “mua thêm một lô” là 0 hoặc 1, rủi ro lệch chỉ số là tổng theo từng cặp "
                          "mã. Đúng dạng QAOA giải, exhaustive enumeration kiểm chứng"),
        ("Đầu vào", "Vốn, danh mục hiện có, yêu cầu tiếng Việt, giá và hiệp phương sai 250 phiên"),
        ("Cách mã hoá", "Bước 1 giải capped continuous QP (tỷ trọng liên tục, có trần). Bước 2 chọn 16 mã mà việc làm "
                        "tròn lô ảnh hưởng nhiều nhất, mỗi qubit x_{k} ∈ {0, 1} trả lời “Mua thêm một lô mã k?”"),
        ("Hàm mục tiêu", "E(x) = 252(wᵀΣw − 2wᵀc + σ_{b}²) + γ‖w − w_{cũ}‖² + λ(1ᵀw − t)², với w = w_{0} + Ax, "
                         "γ = 0,002 (turnover), λ = 0,01 (ngân sách)"),
        ("Đầu ra và thước đo", "Lệnh lô chẵn. Đo bằng sai số bám VN30 năm hoá, số vi phạm quy tắc, tỷ lệ shot "
                               "near-optimal (trong 5% quanh exact optimum)"),
    ]),
    ("(1) ", "(4) ", ("Thách thức", "Cách đội xử lý"), [
        ("Ràng buộc trần làm hỏng QUBO", "Phạt bậc hai vẫn để ba lô cùng vượt trần. **Cap-safe register**: Chỉ mã "
                                         "thêm được một lô mà vẫn giữ mọi trần mới có qubit, cả 2^{16} trạng thái đều "
                                         "hợp lệ"),
        ("Ngôn ngữ tự nhiên",
         "LLM + JSON schema, code kiểm tra từng ràng buộc, hỏi lại khi câu mơ hồ hoặc không dấu"),
        ("Nhiễu phần cứng", "AI chọn shallow circuit noise-aware"),
    ]),
    ("Giả định:", "Giả định:", ("Hạng mục", "Giá trị"), [
        ("Giả định giao dịch", "Phí 0,15% hai chiều, thuế bán 0,1%, đầu tư 98% NAV, tái cân bằng theo quý, giá đóng cửa"),
        ("Kích thước", "16 qubit (65.536 phương án), 512 shots, có two-qubit gate budget"),
        ("Chọn trên dữ liệu 2023", "λ = 0,01, γ = 0,002, k-NN với k = 10 (cross-validation theo tháng), bật COBYLA polish "
                                   "trên CVaR"),
        ("Kiểm tra", "25 kiểm thử tự động. Mạch xuất bằng Qiskit 2.5 khớp mô phỏng numpy. Mô hình dựng lại chọn đúng "
                     "schedule ở 12/12 quý"),
    ]),
    ("Đo trên bản triển khai", "Đo trên bản triển khai", ("Phép đo trên bản triển khai", "Kết quả"), [
        ("Một quyết định 16 qubit", "Tính toán khoảng 2 giây CPU (QUBO 0,01 giây, exhaustive enumeration 0,12 giây, QAOA + "
                                    "COBYLA polish ~1 giây). Job Modal trọn vẹn 5–11 giây, cold start thêm 20–60 giây"),
        ("LLM call mới", "440 giây khi GPU cold start (nạp mô hình 309 giây), vài giây khi GPU đang chạy"),
        ("Câu thử khó", "“Tôi làm ở ngân hàng nên không muốn giữ thêm cổ phiếu ngân hàng, và giữ lại 10% tiền mặt”. "
                        "Qwen3.8 dịch đúng cả hai ý, keyword parser bỏ sót ý thứ nhất"),
        ("Kiểm thử và hạn chế", "24/25 kiểm thử tự động đạt. GPU cold start khoảng 6 phút, giới hạn 40 LLM call mỗi "
                                "giờ để kiểm soát chi phí"),
    ]),
    ("Mã nguồn Python có chú thích", "- Liên kết chạy demo", ("Thành phần", "Nội dung"), [
        ("`agqo/`", "Mã nguồn Python có chú thích: Dữ liệu, danh mục, lượng tử, LLM, kiểm định, báo cáo"),
        ("`app/`, `modal_app.py`", "Máy chủ web và giao diện (Modal), LLM trên GPU"),
        ("`tests/`, `results/final`", "Kiểm thử, mọi kết quả và nhật ký LLM"),
        ("LLM replay", "Phát lại từ nhật ký bằng `--llm replay`, không cần GPU"),
        ("Tái lập (Python 3.12, 8 GB RAM)", "`pip install -r requirements.txt` → `python -m agqo run` (≈ 20 phút CPU) → "
                                            "`python -m agqo report`"),
        ("Link demo", "https://data1--agqo-demo.us-east.modal.run"),
    ]),
    ("- Chi phí:", "- Rủi ro:", ("Khía cạnh", "Cách xử lý"), [
        ("Chi phí", "Tối ưu khoảng 2 giây CPU mỗi quyết định (gần như không đáng kể). LLM khoảng 4 USD/giờ H100 khi chạy, "
                    "tự tắt sau 5 phút, khoảng 1–2 USD cho một lô yêu cầu, có thể dùng chung GPU"),
        ("Bảo mật", "LLM mã nguồn mở tự vận hành, dữ liệu khách hàng không gửi ra bên thứ ba. LLM không bao giờ tạo "
                    "tỷ trọng hay lệnh"),
        ("Rủi ro LLM hiểu sai", "Code kiểm tra JSON schema, hỏi lại khi mơ hồ, khách xác nhận trước khi đặt lệnh"),
        ("Rủi ro dữ liệu lỗi", "Kiểm tra biên độ giá và manifest"),
        ("Rủi ro mô hình lỗi thời", "Huấn luyện lại hằng năm, giám sát sai số bám"),
    ]),
    ("Q1/2027", "Q1/2027", ("Mốc", "Nội dung"), [
        ("Q1/2027", "Thí điểm API với một công ty chứng khoán (tài khoản thử nghiệm)"),
        ("Q2/2027", "Chạy mạch noise-aware trên IBM Heron (tệp OpenQASM đã sẵn)"),
        ("Q3/2027", "Multi-lot register (≥ 60 qubit, nơi exhaustive enumeration không còn khả thi), mở rộng VN100, kết "
                    "hợp lô chẵn và lô lẻ"),
        ("Q4/2027", "Ra mắt tính năng, báo cáo giải thích hằng quý"),
        ("Nguồn lực", "3 kỹ sư, 1 chuyên gia tuân thủ"),
        ("Mốc kiểm chứng", "Sai số bám thực tế, tỷ lệ yêu cầu dịch đúng, 0 vi phạm"),
    ]),
]

# 3.2: the five design rules become a table between the intro sentence and the LLM / k-NN sentence
RULES_INTRO = ("**QAOA** phù hợp vì bài toán là QUBO nhị phân với tương tác cặp đúng bằng hiệp phương sai của cổ phiếu. "
               "Đội không dùng QAOA nguyên bản mà thêm năm quy tắc thiết kế, mỗi quy tắc giải một điểm yếu cụ thể:")
RULES = [("R1 · Warm start", "Xuất phát từ continuous relaxation, mạch bắt đầu ngay cạnh nghiệm tốt (Egger 2021)"),
         ("R2 · Aligned mixer", "Mixer chuẩn xoá thông tin warm start, aligned mixer giữ nó lại (He 2023)"),
         ("R3 · Coupling-mass pruning", "Bỏ ZZ coupling yếu, giữ phần lớn khối lượng J²: Bớt cổng, bài toán gần như giữ nguyên"),
         ("R4 · RMS scaling", "Đưa mọi bài toán về cùng thang, một bộ góc dùng được nhiều quý (Sureshbabu 2024)"),
         ("R5 · Linear-ramp schedule", "γ tăng, β giảm như anneal rời rạc, góc khởi tạo ổn định (LR-QAOA 2025)")]
RULES_AFTER = ("**LLM Qwen3.8-27B** (mã nguồn mở, vLLM, 1 GPU H100, JSON-schema constrained decoding, temperature 0) "
               "chỉ dịch ngôn ngữ, không tạo tỷ trọng. **k-NN** chọn 1 trong 1.080 schedule (p, ε, coupling mass, Δγ, "
               "Δβ) theo 10 bài toán năm 2023 giống nhất.")

TABLE_SEMICOLONS = {4, 6, 7, 10}

# "Why" and "what the number says" boxes: (anchor paragraph opening, insert before the anchor?, label, text)
INSIGHTS = [
    ("Nguyên nhân gốc", False, "Vì sao không làm tròn lô:",
     "Ở tài khoản 20 triệu, nearest-lot rounding đưa gần hết mã về 0 lô: **90% tiền nằm im**, tracking error 18,4%. "
     "Cần chọn cả tổ hợp lô, vì mã rẻ thay được mã đắt khi tương quan cao."),
    ("Trên 12 quý kiểm định, mạch AGQO", False, "Con số nói gì:",
     "Cứ 5 shot có 1 shot nằm trong 5% quanh tối ưu, nên 512 shots gần như chắc chắn chứa nghiệm tốt. Gấp 6,9× "
     "warm-start baseline: Phần lượng tử đóng góp thật. Gấp 19× textbook QAOA: Thiết kế mạch quan trọng hơn số qubit."),
    ("Ở 16 qubit, exhaustive", False, "Vì sao vẫn cần QAOA:",
     "Ở 16 qubit, enumeration là trọng tài chứ không phải đối thủ. Khi chuyển sang multi-lot register (≥ 60 qubit, "
     "hơn 10^{18} phương án), enumeration không còn khả thi, còn lợi thế của mạch AGQO tăng theo quy mô (Hình 8)."),
    ("Prototype web (FastAPI", False, "Vì sao LLM chỉ dịch ngôn ngữ:",
     "LLM có thể hiểu sai hoặc bịa số. Vì vậy mỗi ràng buộc nó đọc ra đều được code kiểm tra, gắn nhãn nguồn và chờ "
     "người dùng xác nhận trước khi chạy."),
    ("Với tài khoản 20 triệu", False, "Con số nói gì:",
     "Lợi ích tập trung ở tài khoản nhỏ, đúng phân khúc ETF không cá nhân hoá được. Ở 100 triệu, lô đã đủ nhỏ để làm "
     "tròn cũng ổn, nên AGQO không hứa hẹn quá mức ở đó."),
]

KPI_MEANING = ["Ý NGHĨA",
               "Đi sát VN30 gần gấp đôi, KTC 95% −6,9 đến −3,8 điểm %",
               "Cứ 5 shot có 1 shot gần tối ưu, thắng 12/12 quý",
               "Hiểu đúng cả câu không dấu, câu hai ý",
               "Quy tắc là ràng buộc cứng, không phải gợi ý",
               "Đủ nhanh để trả lời trực tiếp"]


def insight(doc, opening, before, label, text):
    anchor = find(doc, opening)
    el = copy.deepcopy(anchor._p)
    from docx.text.paragraph import Paragraph
    from docx.oxml import OxmlElement
    p = Paragraph(el, anchor._parent)
    rich(p, f"**{label}** {text}")
    for r in p.runs:
        r.font.size = Emu(120650)                 # 9.5 pt
        r.italic = False
    ppr = el.get_or_add_pPr()
    for tag in ("w:numPr", "w:ind", "w:pBdr", "w:shd", "w:jc"):
        x = ppr.find(qn(tag))
        if x is not None:
            ppr.remove(x)
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    for k, v in (("w:val", "single"), ("w:sz", "18"), ("w:space", "6"), ("w:color", "0284C7")):
        left.set(qn(k), v)
    bdr.append(left)
    shd = OxmlElement("w:shd")
    for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", "EAF4FB")):
        shd.set(qn(k), v)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "140")
    ind.set(qn("w:right"), "60")
    ppr.append(bdr)
    ppr.append(shd)
    ppr.append(ind)
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Emu(25400), Emu(50800), 1.0
    pf.alignment = None
    (anchor._p.addprevious if before else anchor._p.addnext)(el)
DROP_AFTER = {"- Tải tự động": 3}                      # 2.2: three bullets folded into Table 1
DUPLICATE_QUALITY_ROWS = {"Quy mô", "Toàn vẹn", "Rò rỉ thông tin", "Nhãn ngôn ngữ"}
QUALITY_ROWS = [("Lịch sử thiếu", "Mã có < 180 phiên trong 250 phiên gần nhất bị loại khỏi kỳ đó và được ghi lại"),
                ("Covariance shrinkage", "5% về đường chéo trên ma trận chung [cổ phiếu, chỉ số], sai số bám² luôn ≥ 0")]      # summary and data-quality tables: "a; b" -> "a, b"


# ------------------------------------------------------------------ helpers
TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|_\{.+?\}|\^\{.+?\})")


def rich(p, text, rpr=None):
    """Replace the paragraph's runs with `text` (inline markup), keeping the first run's formatting."""
    runs = p._p.findall(qn("w:r"))
    base = copy.deepcopy(rpr if rpr is not None else (runs[0].find(qn("w:rPr")) if runs else None))
    for r in p._p.findall(qn("w:r")) + p._p.findall(qn("w:hyperlink")):
        p._p.remove(r)
    for seg in TOKEN.split(text):
        if not seg:
            continue
        r = p.add_run()
        if base is not None:
            r._r.insert(0, copy.deepcopy(base))
            b = r._r.rPr.find(qn("w:b"))
            if b is not None:
                r._r.rPr.remove(b)
        if seg.startswith("**"):
            r.text, r.bold = seg[2:-2], True
        elif seg.startswith("`"):
            r.text, r.font.name = seg[1:-1], "Consolas"
            r.font.size = Emu(114300)
        elif seg.startswith("_{"):
            r.text, r.font.subscript = seg[2:-1], True
        elif seg.startswith("^{"):
            r.text, r.font.superscript = seg[2:-1], True
        else:
            r.text = seg


def replace_in_paragraph(p, old, new):
    """Run-aware find/replace: the replacement takes the formatting of the run where the match starts."""
    while True:
        runs = p.runs
        full = "".join(r.text for r in runs)
        k = full.find(old)
        if k < 0 or not runs:
            return
        pos, start, end = 0, None, None
        for i, r in enumerate(runs):
            n = len(r.text)
            if start is None and k < pos + n:
                start = (i, k - pos)
            if start is not None and k + len(old) <= pos + n:
                end = (i, k + len(old) - pos)
                break
            pos += n
        (si, so), (ei, eo) = start, end
        if si == ei:
            t = runs[si].text
            runs[si].text = t[:so] + new + t[eo:]
        else:
            runs[si].text = runs[si].text[:so] + new
            for j in range(si + 1, ei):
                runs[j].text = ""
            runs[ei].text = runs[ei].text[eo:]


SKIP_CAP = re.compile(r"^((?:i|ii|iii|iv|v|vi)\)|[^\s]*[.@_][^\s]|\S+\s@|k-NN|vLLM|pytest|python|pip|https?|agqo|app/|results|tests|e\.g|p =|x_|q=)")


def capitalise(p):
    """Upper-case the first letter of the paragraph, of each sentence, and after ': ' (not inside code runs)."""
    runs = [r for r in p.runs if r.font.name != "Consolas"]
    full = "".join(r.text for r in runs)
    if not full.strip():
        return
    targets = set()
    m = re.match(r"^[\s\-–•]*", full)
    if m and m.end() < len(full):
        targets.add(m.end())
    for m in re.finditer(r"(?:[.!?]|:)\s+[“\"(]?", full):
        targets.add(m.end())
    pos = 0
    for r in runs:
        t = list(r.text)
        for i in range(len(t)):
            g = pos + i
            if g in targets and t[i].islower() and "LATIN" in unicodedata.name(t[i], "") and not SKIP_CAP.match(full[g:]):
                t[i] = t[i].upper()
        r.text = "".join(t)
        pos += len(t)


def find(doc, opening):
    for p in doc.paragraphs:
        if p.text.strip().startswith(opening):
            return p
    raise KeyError(opening)


def make_table(doc, template, header, rows):
    tbl = copy.deepcopy(template._tbl)
    trs = tbl.findall(qn("w:tr"))
    head, body = trs[0], trs[1:3]
    for tr in trs:
        tbl.remove(tr)

    def fill(tr, values, bold_first=False):
        tr = copy.deepcopy(tr)
        for c, (tc, val) in enumerate(zip(tr.findall(qn("w:tc")), values)):
            ps = tc.findall(qn("w:p"))
            for extra in ps[1:]:
                tc.remove(extra)
            from docx.text.paragraph import Paragraph
            para = Paragraph(ps[0], None)
            r0 = ps[0].find(qn("w:r"))
            rpr = r0.find(qn("w:rPr")) if r0 is not None else None
            rich(para, f"**{val}**" if (bold_first and c == 0 and not val.startswith("`")) else val, rpr)
        tbl.append(tr)

    fill(head, header)
    for i, row in enumerate(rows):
        fill(body[i % len(body)], row, bold_first=True)
    # compact rows and a narrower label column: parameter tables should read at a glance, not fill the page
    total = sum(int(g.get(qn("w:w"))) for g in tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol")))
    widths = [FIRST_COL, total - FIRST_COL]
    for g, w in zip(tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol")), widths):
        g.set(qn("w:w"), str(w))
    for tr in tbl.findall(qn("w:tr")):
        for tc, w in zip(tr.findall(qn("w:tc")), widths):
            tc.find(qn("w:tcPr")).find(qn("w:tcW")).set(qn("w:w"), str(w))
            for sp in tc.iter(qn("w:spacing")):
                sp.set(qn("w:before"), "20")
                sp.set(qn("w:after"), "20")
                sp.set(qn("w:line"), "235")
                sp.set(qn("w:lineRule"), "auto")
    return tbl


def replace_block(doc, template, first, last, header, rows, intro=None, after=None):
    p0 = find(doc, first)
    body = p0._p.getparent()
    kids = list(body)
    i0 = kids.index(p0._p)
    i1 = next(i for i in range(i0, len(kids)) if kids[i].tag == qn("w:p") and
              "".join(t.text or "" for t in kids[i].iter(qn("w:t"))).strip().startswith(last))
    anchor = kids[i0]
    tbl = make_table(doc, template, header, rows)
    if intro is not None:
        from docx.text.paragraph import Paragraph
        rich(Paragraph(anchor, p0._parent), intro)
        anchor.addnext(tbl)
        start = i0 + 1
    else:
        anchor.addprevious(tbl)
        start = i0
    tail = tbl
    if after is not None:
        np_ = copy.deepcopy(anchor)
        from docx.text.paragraph import Paragraph
        rich(Paragraph(np_, p0._parent), after)
        tbl.addnext(np_)
        tail = np_
    for el in kids[start:i1 + 1]:
        if el is not anchor or intro is None:
            body.remove(el)
    # a little air after the table
    spacer = copy.deepcopy(anchor if intro is not None else kids[i1])
    for r in spacer.findall(qn("w:r")):
        spacer.remove(r)
    from docx.text.paragraph import Paragraph
    sp = Paragraph(spacer, p0._parent).paragraph_format
    sp.space_before, sp.space_after, sp.line_spacing = Emu(0), Emu(0), 0.6
    spacer_pr = spacer.find(qn("w:pPr"))
    if spacer_pr is not None:
        for tag in ("w:numPr", "w:ind"):
            el = spacer_pr.find(qn(tag))
            if el is not None:
                spacer_pr.remove(el)


def swap_figures(doc):
    for rel in doc.part.rels.values():
        if "image" not in rel.reltype:
            continue
        name = Path(rel.target_part.partname).name
        if name not in FIGURES and name not in WIDTH_CM:
            continue
        from PIL import Image
        import io
        if name in FIGURES:
            png = FIGURES[name] if isinstance(FIGURES[name], Path) else FIG / FIGURES[name]
            rel.target_part._blob = png.read_bytes()
        w, h = Image.open(io.BytesIO(rel.target_part.blob)).size
        for blip in doc.element.body.iter(qn("a:blip")):
            if blip.get(qn("r:embed")) != rel.rId:
                continue
            inline = next(a for a in blip.iterancestors() if a.tag in (qn("wp:inline"), qn("wp:anchor")))
            ext = inline.find(qn("wp:extent"))
            cx = int(WIDTH_CM[name] * 360000) if name in WIDTH_CM else int(ext.get("cx"))
            cy = int(cx * h / w)
            ext.set("cx", str(cx))
            ext.set("cy", str(cy))
            for x in inline.iter(qn("a:ext")):
                if x.get("cx"):
                    x.set("cx", str(cx))
                    x.set("cy", str(cy))


PACKAGE_TEXT = [
    ("data1--agqo-demo.us-east.modal.run", "data1--agqo-prototype.us-east.modal.run"),
    ("AQ2026-R2-Madoi-", "AQ2026-R2-AQ2026-169-"),
    ("v3.1 (16/11/2026)", "Bản nộp (20/11/2026)"), ("phiên bản v3.1, 16/11/2026", "bản nộp ngày 20/11/2026"),
    ("24/25 kiểm thử tự động đạt", "58/58 kiểm thử tự động đạt trên Modal CPU"),
    ("24/25 kiểm thử đạt (pytest)", "58/58 kiểm thử đạt (pytest, Modal CPU)"),
    ("25 kiểm thử tự động.", "58 kiểm thử tự động, đạt 58/58 trên Modal CPU."),
    ("+ 25 kiểm thử", "+ 58 kiểm thử"),
    ("slide 20 trang có hoạt ảnh", "slide 8 trang chính + 13 phụ lục có hoạt ảnh"),
    ("20 trang, hoạt ảnh, ghi chú lời nói", "8 slide chính + 13 phụ lục, hoạt ảnh, ghi chú lời nói"),
    ("→ LLM → Hamiltonian", "→ LLM → người dùng xác nhận → Hamiltonian"),
]


def package_facts(doc):
    """Team code, members, advisor, URL, file names, version and test count as in the submission package."""
    import json
    tf = ROOT / "submission" / "team.local.json"
    team = json.loads(tf.read_text()) if tf.exists() else None
    paras = list(doc.paragraphs) + [p for t in doc.tables for r in t.rows for c in r.cells for p in c.paragraphs]
    for p in paras:
        for old, new in PACKAGE_TEXT:
            if old in p.text:
                replace_in_paragraph(p, old, new)
    for rel in doc.part.rels.values():                      # hyperlink targets
        if rel.is_external and "agqo-demo" in rel.target_ref:
            rel._target = rel.target_ref.replace("agqo-demo", "agqo-prototype")
    if team is None:
        return
    code, num = team["team_code"], team["team_code"].split("-")[-1]
    for p in paras:
        for r in p.runs:
            if r.text.strip() == num and ("Mã đội" in p.text or "MÃ ĐỘI" in p.text):
                r.text = r.text.replace(num, code)
        if p.text.strip().startswith(f"{num} / "):
            for r in p.runs:
                if r.text.lstrip().startswith(num):
                    r.text = r.text.replace(num, code, 1)
                    break
    info = doc.tables[2]
    for row in info.rows:
        if row.cells[0].text.strip().startswith("Giảng viên") and not row.cells[1].text.strip():
            cell = row.cells[1].paragraphs[0]
            ref = row.cells[0].paragraphs[0]._p.find(qn("w:r"))
            rich(cell, team.get("advisor") or "Không có", ref.find(qn("w:rPr")) if ref is not None else None)
    # members missing from the cover list and the member table
    roster = doc.tables[3]
    listed = {r.cells[1].text.strip() for r in roster.rows[1:]}
    cover = [p for p in doc.paragraphs[:22] if re.match(r"^\d+\.\s", p.text.strip())]
    for m in team["members"]:
        if m["name"] in listed:
            continue
        n = len(roster.rows)
        tr = copy.deepcopy(roster.rows[-1]._tr)
        roster._tbl.append(tr)
        row = roster.rows[-1]
        email = m["email"].replace("@", " @")
        school = m["school"].replace("Đại học ", "Đại học ") if m["school"] != "Đại học Kinh tế - Luật" else "Kinh tế - Luật"
        for cell, val in zip(row.cells, [str(n), m["name"], m["major"], school, m["id"], email, m["phone"], m["role"]]):
            para = cell.paragraphs[0]
            r0 = para._p.find(qn("w:r"))
            rich(para, val, r0.find(qn("w:rPr")) if r0 is not None else None)
        listed.add(m["name"])
        if cover:
            last = cover[-1]
            el = copy.deepcopy(last._p)
            from docx.text.paragraph import Paragraph
            np_ = Paragraph(el, last._parent)
            runs = np_.runs
            runs[0].text = f"{len(cover) + 1}.  "
            runs[1].text = m["name"]
            for r in runs[2:]:
                r.text = ""
            runs[-1].text = " " * round(5 + 2.2 * max(0, 20 - len(m["name"]))) + m["role"]   # line up the role column
            nxt = last._p.getnext()
            last._p.addnext(el)
            # keep the cover height: drop one empty spacer paragraph after the list
            if nxt is not None and nxt.tag == qn("w:p") and not "".join(t.text or "" for t in nxt.iter(qn("w:t"))).strip():
                nxt.getparent().remove(nxt)
            cover.append(np_)


def main(src: str) -> Path:
    doc = Document(src)
    template = doc.tables[10]
    semi_tables = [doc.tables[i] for i in TABLE_SEMICOLONS]
    kpi = doc.tables[7]
    swap_figures(doc)
    # 3.2 rules table first (it rewrites the paragraph that opens with "QAOA phù hợp")
    replace_block(doc, template, "QAOA phù hợp", "QAOA phù hợp", ("Quy tắc", "Vì sao cần"), RULES, RULES_INTRO,
                  RULES_AFTER)
    for first, last, header, rows in TABLES:
        replace_block(doc, template, first, last, header, rows)
    for opening, n in DROP_AFTER.items():
        p = find(doc, opening)._p
        for _ in range(n):
            nxt = p.getnext()
            nxt.getparent().remove(nxt)
    qt = template._tbl
    for sp in qt.iter(qn("w:spacing")):
        sp.set(qn("w:before"), "20")
        sp.set(qn("w:after"), "20")
    for tr in list(qt.findall(qn("w:tr")))[1:]:
        first = "".join(t.text or "" for t in tr.find(qn("w:tc")).iter(qn("w:t"))).strip()
        if first in DUPLICATE_QUALITY_ROWS:              # already stated in 2.1-2.3
            qt.remove(tr)
    for k, (lab, val) in enumerate(QUALITY_ROWS):
        last = qt.findall(qn("w:tr"))[-2 + (k % 2)]
        tr = copy.deepcopy(last)
        from docx.text.paragraph import Paragraph
        for tc, v in zip(tr.findall(qn("w:tc")), (lab, val)):
            p_ = tc.find(qn("w:p"))
            rich(Paragraph(p_, None), v, p_.find(qn("w:r")).find(qn("w:rPr")))
        qt.append(tr)
    pipe = find(doc, "Pipeline:")
    pipe._p.getparent().remove(pipe._p)
    for opening, text in REWRITE.items():
        rich(find(doc, opening), text)
    package_facts(doc)
    for c, text in zip([row.cells[3] for row in kpi.rows], KPI_MEANING):
        para = c.paragraphs[0]
        r0 = para._p.find(qn("w:r"))
        rich(para, text, r0.find(qn("w:rPr")) if r0 is not None else None)
    for args in INSIGHTS:
        insight(doc, *args)
    allp = list(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                allp += cell.paragraphs
    for p in allp:
        for old, new in TERMS:
            if old in p.text:
                replace_in_paragraph(p, old, new)
    for p in doc.paragraphs:
        if p.style.name == "Normal" and "; " in p.text:
            replace_in_paragraph(p, "; ", ". ")
    for t in semi_tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_in_paragraph(p, "; ", ", ")
    for p in allp:
        if p.style.name.startswith(("Normal", "List", "Body", "Caption", "Heading 2")):
            capitalise(p)
    out_dir = ROOT / "submission" / "drafts" / ("report-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
    out_dir.mkdir(parents=True)
    out = out_dir / "AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.docx"
    doc.save(out)
    print(out)
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "submission/report/user_base/user_2026-11-20.docx"))
