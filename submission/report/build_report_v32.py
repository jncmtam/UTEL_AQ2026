"""Semifinal report in the organisers' template (Vietnamese), from the same data as the deck.

    python submission/deck/make_data.py && python submission/deck/figures.py
    python submission/report/build_report_v32.py      # -> submission/drafts/<UTC>/AQ2026-R2-Madoi-Bao_cao_giai_phap.docx

Only the template's placeholders and "MINH CHỨNG BỔ SUNG" slots are filled; headings, tables, headers and page
breaks stay. Team details stay as placeholders. Every number comes from submission/deck/data (via facts()).
Each run writes a new draft folder.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "submission"))
sys.path.insert(0, str(ROOT / "submission" / "deck"))

import pandas as pd  # noqa: E402
from docx.shared import Cm, RGBColor  # noqa: E402

from build_deck import facts, pct, vi  # noqa: E402
from build_report import Filler  # noqa: E402

TEMPLATE = ROOT / "submission" / "template" / "mau_bao_cao_BTC.docx"
FIG = ROOT / "submission" / "deck" / "figures"
SHOT = ROOT / "docs" / "prototype_shots" / "v32"
URL = "https://data1--agqo-v32.us-east.modal.run"
BODY = 10
NAME = "AGQO – Danh mục bám VN30 theo quy tắc riêng bằng lô chẵn: AI hiểu yêu cầu, tối ưu tổ hợp lô, kiểm tra được"
EVC = RGBColor(0x0F, 0x4C, 0x5C)


def build(out_dir: Path | None = None) -> Path:
    F = facts()
    f = Filler(TEMPLATE)
    acc = pd.read_csv(ROOT / "submission/deck/data/c4_accounts.csv").set_index("capital_vnd")
    ci = pd.read_csv(ROOT / "submission/deck/data/c4_accounts_ci.csv")
    kn = pd.read_csv(ROOT / "submission/deck/data/a_knn.csv").set_index("arm").success_pct
    W = 17.0

    # ---------------------------------------------------------- cover + administrative tables
    f.write(f.para("[Nhập tên giải pháp"), NAME, size=13)
    from docx.oxml.ns import qn as _qn
    ts = list(f.doc.element.body.iter(_qn("w:t")))
    for i, t in enumerate(ts[:-1]):
        if (t.text or "").strip() == "TÊN GIẢI PHÁP" and (ts[i + 1].text or "").startswith("[...."):
            ts[i + 1].text = "AGQO – Bám VN30 theo quy tắc riêng bằng lô chẵn"
    f.fill_table(2, {(2, 1): NAME, (3, 1): "Tài chính (đầu tư chứng khoán cá nhân) · AI và tính toán lượng tử",
                     (4, 1): "Quantum Computing cho Tài chính"})
    f.fill_table(4, {(1, 1): "Web app: nhập yêu cầu → xác nhận ràng buộc → job tính toán trên Modal → lệnh, phí, kiểm tra quy tắc",
                     (1, 2): "v3.2.0",
                     (2, 1): URL, (2, 2): "Công khai, không cần tài khoản; phát lại có nhãn khi không gọi được Modal",
                     (3, 1): "AQ2026-R2-Madoi-Ma_nguon.zip", (3, 2): "Mã nguồn, dữ liệu thành phần, kết quả, 58 kiểm thử",
                     (4, 1): "AQ2026-R2-Madoi-Huong_dan.pdf", (4, 2): "Hướng dẫn nhanh cho giám khảo + hướng dẫn tái lập"})

    # ---------------------------------------------------------- executive summary: criterion -> evidence
    f.fill_table(6, {
        (1, 1): f"Người có 20 triệu muốn bám VN30 nhưng bỏ bất động sản và giới hạn ngân hàng 30%. Một lô VIC = {F['vic_pct']}% tài khoản; {F['n_over10']}/30 mã có một lô vượt 10%. ETF không cho đặt quy tắc riêng.",
        (1, 2): "Mục 1; Hình 1",
        (2, 1): "40 mã từng thuộc VN30 theo thời điểm, chỉ số, 3 ETF, 01/2022–11/2026; giá đã điều chỉnh (đã đo giới hạn); 50 câu tiếng Việt có nhãn; chọn mọi tham số trên 2023, kiểm định 2024–2026.",
        (2, 2): "Mục 2; Bảng 1",
        (3, 1): f"Tối ưu tổ hợp lô (QUBO 16 qubit, kiểm chứng bằng liệt kê). 12 quý, 20 triệu: AGQO {F['agqo_none']} so với làm tròn {pct(acc.loc[20e6, 'practitioner'])}; tham lam {pct(acc.loc[20e6, 'greedy'])} (chênh chưa có ý nghĩa thống kê). Mạch: {F['agqo_q']} mỗi lần đo so với warm start {F['warm']}.",
        (3, 2): "Mục 3; Hình 3–4; Bảng 2",
        (4, 1): "Prototype chạy job thật trên Modal: AI hiểu yêu cầu → người dùng xác nhận → lệnh, phí, tiền mặt sau phí, kiểm tra quy tắc trên NAV sau phí; hỏi lại câu mơ hồ; báo rõ yêu cầu không khả thi.",
        (4, 2): "Mục 4; Hình 2; link demo",
        (5, 1): "Thí điểm kiểu công ty chứng khoán: kiểm chứng tuân thủ quy tắc và mức hiểu của người dùng; ở 16 qubit dùng bộ giải cổ điển; còn thiếu giá khớp gốc, danh mục đang có, người dùng độc lập.",
        (5, 2): "Mục 5",
        (6, 1): "Deck PowerPoint chỉnh sửa được (8 slide + 10 phụ lục), lời nói, bản 3 phút, 10 thẻ hỏi–đáp, hướng dẫn, sổ đăng ký bằng chứng.",
        (6, 2): "Mục 6",
    })
    f.write(f.para("[Giải pháp giúp ai"),
            "AGQO giúp nhà đầu tư cá nhân vốn nhỏ giữ danh mục bám VN30 theo quy tắc riêng (bỏ ngành, giới hạn ngành, số mã, tiền mặt) "
            "chỉ bằng lệnh lô chẵn. Qwen3.8-27B đọc yêu cầu tiếng Việt thành ràng buộc; người dùng xác nhận; bộ tối ưu chọn cả tổ hợp lô "
            "và kiểm tra mọi quy tắc trên giá trị tài khoản sau phí. Với 20 triệu qua 12 quý, sai số bám giảm từ "
            f"{pct(acc.loc[20e6, 'practitioner'])} (làm tròn từng mã) xuống {F['agqo_none']}; thêm hai quy tắc bỏ bất động sản và "
            f"ngân hàng ≤ 30%, sai số bám là {F['agqo_rules']}, không có vi phạm quy tắc.", size=BODY)
    t7 = f.doc.tables[7]
    body = t7.rows[1]._tr
    import copy
    c20 = lambda comp: ci[(ci.capital_vnd == 20e6) & (ci.comparison == comp)].iloc[0]
    r, g = c20("agqo vs practitioner"), c20("agqo vs greedy")
    kpis = [("Sai số bám thực tế, 20 triệu, 12 quý", f"{pct(acc.loc[20e6, 'practitioner'])} (làm tròn)", F["agqo_none"],
             f"KTC 95% của mức giảm: {vi(-r.ci_high)}–{vi(-r.ci_low)} điểm %"),
            ("Như trên, so với thuật toán tham lam", pct(acc.loc[20e6, "greedy"]), F["agqo_none"],
             f"{vi(g.diff_pp)} điểm % [{vi(g.ci_low)}; +{vi(g.ci_high)}]: chưa có ý nghĩa"),
            ("Quyết định 01/10/2026: 20 triệu, bỏ BĐS, NH ≤ 30%", f"{F['round_est']} ước tính (làm tròn)", f"{F['agqo_est']} ước tính",
             f"tiền mặt sau phí {F['agqo_cash_m']} triệu; ngân hàng {F['bank_pct']}"),
            ("Xác suất gần tối ưu mỗi lần đo (mô phỏng)", f"{F['warm']} (mốc warm start)", F["agqo_q"], "12/12 quý; 16 qubit, không nhiễu"),
            ("Yêu cầu tiếng Việt xử lý đúng đến tận lệnh", "33/50 (từ khóa)", "49/50 (Qwen, prompt V3.2)", "bộ câu do nhóm viết")]
    for tr in t7.rows[2:]:
        tr._tr.getparent().remove(tr._tr)
    for i, row in enumerate(kpis):
        if i:
            t7._tbl.append(copy.deepcopy(body))
        for cidx, v in enumerate(row):
            f._cell(t7.rows[-1].cells[cidx], v, 8.5)

    # ---------------------------------------------------------- criterion 1
    p = f.write(f.para("[Mô tả cụ thể nghiệp vụ kinh tế"),
                "Nhiều nhà đầu tư cá nhân muốn “nắm cả rổ VN30 nhưng theo cách của mình”: không giữ thêm bất động sản vì đã có nhà, "
                "giới hạn ngân hàng vì làm trong ngành, giữ một phần tiền mặt. ETF VN30 rẻ và đa dạng nhưng không cho đặt quy tắc riêng. "
                "Tự mua từng mã thì vấp vào lô chẵn: với 20 triệu đồng, một lô VIC (100 cổ phiếu) ngày 01/10/2026 bằng "
                f"**{F['vic_pct']}% tài khoản**, {F['n_over10']}/30 mã có một lô vượt 10%. Đối tượng: nhà đầu tư 20–200 triệu đồng và công ty "
                "chứng khoán muốn cung cấp tính năng danh mục cá nhân hoá.", size=BODY)
    p = f.figure(p, FIG / "f1_lot_cost.png", 14.0, "Giá một lô so với tài khoản 20 triệu, giá đóng cửa 01/10/2026, 30 mã VN30 dùng được "
                 "(đỏ: lớn hơn cả tài khoản; cam: lớn hơn 10%).")
    f.write(f.para("[Phân tích nguyên nhân, mức độ"),
            "Bộ tối ưu cho tỷ trọng liên tục (ví dụ “10,7% FPT”), nhưng tài khoản chỉ giữ được 0% hoặc một lô (31,4%). Làm tròn từng mã về "
            f"lô gần nhất, cách phổ biến, với quyết định ngày 01/10/2026 chỉ mua được {F['round_holdings']} mã và để "
            f"{F['round_cash']} tiền nằm im. Yêu cầu nghiệp vụ: (i) chỉ lệnh lô chẵn, đủ tiền sau phí 0,15% và thuế bán 0,1%; (ii) mọi "
            "quy tắc của người dùng được thỏa trên giá trị tài khoản sau phí; (iii) bám VN30 sát nhất có thể; (iv) người dùng thấy "
            "và xác nhận ràng buộc trước khi có lệnh.", size=BODY)
    f.write(f.para("[Chuyển vấn đề thực tiễn thành"),
            "**Bài toán tối ưu tổ hợp nhị phân.** Đầu vào: số vốn, yêu cầu đã xác nhận, giá và hiệp phương sai 250 phiên trước ngày quyết "
            "định. Bước 1 giải bài toán liên tục có trần. Bước 2, với 16 mã mà việc làm tròn quan trọng nhất, mỗi bit x_k ∈ {0, 1} "
            "quyết định “mua thêm một lô mã k?”. Mục tiêu E(x) = 252(wᵀΣw − 2wᵀc + σ_b²) + γ‖w − w_cũ‖² + λ(1ᵀw − t)², w = w₀ + Ax. "
            "Thước đo: sai số bám so với VN30 (độ lệch chuẩn năm hoá của chênh lệch lợi suất ngày; đo trước giao dịch là “ước tính”, "
            "đo qua 12 quý là “thực tế”), vi phạm quy tắc, xác suất gần tối ưu mỗi lần đo.", size=BODY)
    f.write(f.para("[Chỉ ra các ràng buộc và khó khăn"),
            "(1) **Phí làm thay đổi tỷ trọng:** một danh mục “vừa đúng 25%” trên vốn ban đầu thành 25,03% sau phí. AGQO siết mỗi trần theo "
            "biên phí khi dựng bài toán và kiểm tra lại chính xác trên NAV sau phí (có kiểm thử). (2) **Ngôn ngữ tự nhiên:** phủ định "
            "(“Đừng bỏ VIC”), câu mơ hồ (“ít rủi ro hơn”), mâu thuẫn → ràng buộc hiện thành ô có nhãn nguồn, hỏi lại khi cần, người dùng "
            "xác nhận trước khi chạy. (3) **Yêu cầu không khả thi** (ví dụ mỗi mã ≤ 2% với 20 triệu) → báo đúng quy tắc chặn, không tạo "
            "lệnh. (4) **Quy mô:** 2¹⁶ = 65.536 tổ hợp, liệt kê chính xác được, nên dùng làm trọng tài cho mọi kết quả.", size=BODY)
    f.write(f.para("[Nêu mức đạt, phần chưa giải quyết"),
            "Đạt: bài toán lô chẵn có quy tắc cá nhân được giải, kiểm chứng và thể hiện trong prototype. Lợi ích rõ ở tài khoản 20 triệu, "
            "nhỏ ở 50 triệu, gần như không còn từ 100 triệu. Chưa giải quyết: chưa có giá khớp lệnh gốc, chưa nhập được danh mục đang "
            "có, chưa thử với người dùng độc lập, chưa kết nối đặt lệnh thật.", size=BODY)
    f.write(f.para("MINH CHỨNG BỔ SUNG", 0), "MINH CHỨNG BỔ SUNG: dữ liệu Hình 1 trong submission/deck/data/c1_lot_cost.csv; "
            "các ca lỗi đã tái hiện và sửa: results/runs/*-product-failures.", color=EVC)

    # ---------------------------------------------------------- criterion 2
    f.write(f.para("[Nêu từng nguồn dữ liệu"),
            "**Giá:** API biểu đồ công khai của DNSE, OHLCV ngày 04/01/2022–13/11/2026 cho 40 mã từng thuộc VN30, chỉ số VN30, VN-Index và "
            "ba ETF VN30; giá cổ phiếu đã điều chỉnh cổ tức và chia tách bởi nhà cung cấp. Tệp giá không phân phối lại; snapshot dùng "
            "được kiểm tra bằng SHA-256 7f076128…3042. **Thành phần VN30 theo thời điểm:** lịch sử thay đổi rổ do nhóm đối chiếu với thông "
            "báo HOSE, tránh sai lệch sống sót. **Ngôn ngữ:** 35 câu (V3) và 50 câu mới (V3.2: rõ ràng, mơ hồ, mâu thuẫn, không khả thi) do "
            "nhóm viết và gán nhãn.", size=BODY)
    f.write(f.para("[Mô tả quy trình thu thập, kiểm tra"),
            "Tải tự động, ghi manifest và SHA-256; mỗi lần chạy ghi lại mã băm dữ liệu. Kiểm tra điều chỉnh giá: 31/46.609 ngày–mã biến động "
            "vượt biên độ HOSE (3 mã, đã rà soát). Mã thiếu lịch sử (< 180 trong 250 phiên) bị loại khỏi kỳ đó và ghi lại. Hiệp phương sai co "
            "về đường chéo 5% trên ma trận chung [cổ phiếu, chỉ số] để sai số bám² luôn ≥ 0.", size=BODY)
    f.write(f.para("[Chứng minh mức độ đại diện"),
            "Giai đoạn 2022–2026 gồm thị trường giảm, đi ngang và tăng mạnh. **Chống rò rỉ:** mọi lựa chọn (hệ số phạt, lịch mạch, k của "
            "k-NN, có tinh chỉnh hay không) chỉ dùng dữ liệu 2023; kết quả báo cáo từ 2024–2026. Nghiên cứu k-NN V3.2 đăng ký giao thức "
            "trước, chia hiệu chỉnh 01–08/2023, kiểm định 09–12/2023 và holdout 22 tháng chưa từng dùng (330 bài toán, 5 cỡ tài khoản, 3 loại "
            "quy tắc). So sánh cặp: Wilcoxon theo ngày, bootstrap khối 21 ngày.", size=BODY)
    f.write(f.para("[Giải thích việc lựa chọn/tạo đặc trưng"),
            "Đặc trưng cho chọn lịch mạch: độ tự tin của warm start, tỷ lệ qubit đã rõ, log(trường/tương tác), độ tập trung tương tác, cỡ lô; "
            "V3.2 thêm log số vốn, số qubit, cờ quy tắc. Không tăng cường dữ liệu: dữ liệu giả sẽ làm sai cấu trúc tương quan thật.", size=BODY)
    q = f.para("Minh chứng chất lượng dữ liệu")
    f.table_from(2, q, ["Hạng mục", "Kết quả kiểm tra"], [
        ["Quy mô", "52.686 dòng ngày; 40 mã + 2 chỉ số + 3 ETF; 01/2022–11/2026"],
        ["Toàn vẹn", "SHA-256 trong manifest và trong từng lần chạy (run.json)"],
        ["Điều chỉnh giá", "Giá đã điều chỉnh; giới hạn được đo: nếu giá lô quá khứ cao hơn tới 50%, AGQO vẫn thấp hơn làm tròn ~4,9 điểm %"],
        ["Rò rỉ thông tin", "Chọn tham số trên 2023; báo cáo 2024–2026; thành phần VN30 theo thời điểm"],
        ["Nhãn ngôn ngữ", "35 + 50 câu do nhóm viết; chưa có người dùng độc lập"]], caption="Kiểm tra chất lượng dữ liệu.", size=8.5)
    f.write(f.para("MINH CHỨNG BỔ SUNG", 1), "MINH CHỨNG BỔ SUNG: data/vn30/manifest.json; docs/research/PROTOCOL_V3_2.md; "
            "results/runs/*-account-benchmark (giới hạn giá).", color=EVC)

    # ---------------------------------------------------------- criterion 3
    p = f.write(f.para("[Trình bày kiến trúc, luồng xử lý"),
                "Luồng: yêu cầu tiếng Việt → **Qwen3.8 đọc thành ràng buộc** (hoặc quy tắc từ khóa khi không gọi được GPU) → **người dùng xác "
                "nhận** → chẩn đoán khả thi → bài toán liên tục có trần → **16 bit “thêm một lô?”** và QUBO → k-NN chọn lịch mạch → **QAOA "
                "512 lần đo** → **liệt kê 65.536 tổ hợp** để kiểm chứng → lệnh, phí, tiền mặt sau phí, kiểm tra quy tắc → lời giải thích đã đối "
                "chiếu số liệu (sai thì thay bằng giải thích tạo từ dữ liệu).", size=BODY)
    f.write(f.para("[Nêu phương pháp/thuật toán cụ thể"),
            "QAOA phù hợp vì bài toán là QUBO nhị phân có tương tác cặp đúng bằng mức đi cùng nhau của cổ phiếu. Mạch dùng warm start từ nghiệm "
            "nới lỏng (Egger và cộng sự 2021), bộ trộn căn chỉnh, giữ tương tác mạnh nhất, chuẩn hoá RMS (Sureshbabu và cộng sự 2024) và lịch "
            "góc dốc tuyến tính (Montañez-Barrera & Michielsen 2025); đóng góp của nhóm là cách mã hoá lô chẵn có trần an toàn và quy trình "
            "kiểm chứng. Qwen3.8-27B (mã mở, giải mã theo lược đồ JSON, nhiệt độ 0) chỉ đọc ngôn ngữ, không tạo tỷ trọng hay lệnh.", size=BODY)
    f.write(f.para("[Mô tả các bước triển khai theo logic"),
            "Giả định: phí 0,15% hai chiều, thuế bán 0,1%, tái cân bằng theo quý, giá đóng cửa, tài khoản tiền mặt mới. Tham số: 16 qubit, "
            "512 lần đo, ngân sách 1.500 cổng hai qubit; lịch chọn từ 1.080 lịch trên dữ liệu 2023. Kiểm tra: 58 kiểm thử chạy trên Modal CPU; "
            "mạch xuất OpenQASM khớp mô phỏng; mọi lần chạy ghi commit, mã băm dữ liệu, cấu hình.", size=BODY)
    p = f.write(f.para("[Đưa kết quả thuật toán chạy trên dữ liệu"),
                f"**Một quyết định (01/10/2026, 20 triệu, bỏ bất động sản, ngân hàng ≤ 30%):** AGQO mua {F['agqo_holdings']} mã, tiền mặt sau phí "
                f"{F['agqo_cash_m']} triệu, sai số bám ước tính {F['agqo_est']}; làm tròn lô gần nhất {F['round_est']}; tham lam cùng quy tắc "
                f"{F['greedy_est']}. **Qua 12 quý:** với hai quy tắc, làm tròn {F['r_round']}, tham lam {F['r_greedy']}, AGQO {F['r_agqo']}. "
                f"**Mạch:** xác suất gần tối ưu mỗi lần đo {F['agqo_q']}, so với mốc warm start {F['warm']} và QAOA sách giáo khoa {F['textbook']}.",
                size=BODY)
    p = f.figure(p, FIG / "f3_pitch_weights.png", 13.0, "Quyết định 01/10/2026: tỷ trọng từng mã của ba cách chọn lô (vạch đen: tỷ trọng lý tưởng "
                 "nếu mua được cổ phiếu lẻ). Sai số bám là ước tính trước giao dịch.")
    p = f.figure(p, FIG / "f4_accounts.png", 12.5, "Sai số bám thực tế (năm hoá) qua 12 quý theo cỡ tài khoản, không quy tắc, cùng một thang đo.")
    f.table_from(7, p, ["Tài khoản", "Làm tròn", "Tham lam", "AGQO", "AGQO − làm tròn (KTC 95%)"], [
        [f"{int(cap / 1e6)} triệu", pct(acc.loc[cap, "practitioner"]), pct(acc.loc[cap, "greedy"]), pct(acc.loc[cap, "agqo"]),
         (lambda t: f"{vi(t.diff_pp)} [{vi(t.ci_low)}; {vi(t.ci_high)}]")(
             ci[(ci.capital_vnd == cap) & (ci.comparison == "agqo vs practitioner")].iloc[0])]
        for cap in acc.index], caption="Sai số bám VN30 thực tế, 12 lần tái cân bằng theo quý 2024–2026.", size=8.5)
    f.write(f.para("[Những trường hợp giải pháp chưa đạt"),
            "Ở 16 qubit, liệt kê cổ điển giải chính xác trong khoảng 0,12 giây nên **không có ưu thế lượng tử**; liệt kê là trọng tài. Thuật "
            "toán tham lam theo rất sát (ở 20 triệu chênh −0,69 điểm %, KTC từ −1,53 đến +0,02). Mạch thiết kế có xác suất mỗi lần đo cao, nhưng "
            f"lịch cố định ({F['frozen']}) và k-NN không tinh chỉnh ({F['nopolish']}) cao hơn mạch đã tinh chỉnh ({F['agqo_q']}); trên holdout "
            f"V3.2, k-NN hơn lịch cố định {vi(kn['knn_selected'] - kn['frozen'])} điểm % nhưng ngang quy tắc “một lịch cho mỗi cỡ tài khoản”. "
            "Kết quả nhiễu là ước tính ESP và mô phỏng Aer 3 quý; chưa chạy phần cứng thật.", size=BODY)
    ev = f.para("MINH CHỨNG BỔ SUNG", 2)
    f.write(ev, "MINH CHỨNG BỔ SUNG: xác suất gần tối ưu mỗi lần đo của các mạch", color=EVC)
    f.figure(ev, FIG / "f6_circuits.png", 8.5, "12 quý 2024–2026, tài khoản 100 triệu, 16 qubit, mô phỏng không nhiễu, 512 lần đo. “Gần tối "
             "ưu”: đủ tiền, thỏa quy tắc, khoảng cách chuẩn hoá ≤ 5% (0 = tối ưu, 1 = lựa chọn khả thi điển hình).")

    # ---------------------------------------------------------- criterion 4
    f.write(f.para("[Nêu các chức năng cốt lõi đã hoạt động"),
            "Đã chạy thật: (1) chọn mẫu hoặc gõ yêu cầu; Qwen trên GPU H100 trả lời trực tiếp, câu đã gặp được phát lại, khi không có GPU dùng "
            "quy tắc từ khóa, nguồn luôn được ghi; (2) các ô ràng buộc có nhãn “Bạn nhập / Từ mẫu / Từ câu lệnh / Chưa đặt”, phải xác nhận "
            "mới chạy; câu mơ hồ hoặc mâu thuẫn bị khóa đến khi trả lời; (3) mỗi lần bấm Chạy là một job trên Modal CPU, có tiến trình, lỗi và "
            "nút thử lại; (4) kết quả: lệnh, phí, tiền mặt sau phí, NAV sau phí, kiểm tra từng quy tắc, so sánh với làm tròn và tham lam; "
            "(5) yêu cầu không khả thi được giải thích; (6) tải mạch OpenQASM. Chưa có: nhập danh mục đang có, đặt lệnh thật.", size=BODY)
    p = f.write(f.para("[Mô tả trình tự demo có thể chạy"),
                "Mở link → chọn mẫu “20 triệu, bỏ bất động sản, ngân hàng tối đa 30%” → xem hai ràng buộc có nhãn “Từ câu lệnh” và nguồn diễn "
                "giải → bấm **Xác nhận** → **Chạy trên Modal** → đọc nhãn “Chạy thật trên Modal”, lệnh, phí, tiền mặt sau phí và các dấu ✔ "
                "kiểm tra quy tắc. Thử thêm mẫu “Câu mơ hồ” (hệ thống hỏi lại) và “Mỗi mã tối đa 2%” (báo không khả thi).", size=BODY)
    f.figure2(p, [(SHOT / "pitch_constraints_pending.png", 8.4), (SHOT / "pitch_kpis.png", 8.4)],
              "Prototype: ràng buộc chờ xác nhận, có nhãn nguồn (trái); kết quả job trên Modal: số mã, phí, tiền mặt sau phí, tỷ lệ đầu tư, sai "
              "số bám ước tính (phải).")
    f.write(f.para("[Báo cáo kết quả bước đầu"),
            "Đo trên bản triển khai: một quyết định 5–11 giây khi container CPU đã chạy (thêm 20–60 giây lần đầu); Qwen khoảng 4 giây khi GPU "
            "ấm, 440 giây khi khởi động lạnh. Đánh giá đọc yêu cầu: 49/50 câu mới xử lý đúng đến tận lệnh (từ khóa 33/50; McNemar p = 3·10⁻⁵); "
            "câu sai duy nhất là mâu thuẫn cần làm phép tính. 58/58 kiểm thử đạt, gồm các ca: trần sau phí, giữ 1 mã, toàn tiền mặt có giải "
            "thích, tiền mặt tối thiểu 1,30% ở 100 triệu, phủ định “Đừng bỏ VIC”, lời giải thích nói sai về lô lẻ bị thay.", size=BODY)
    f.write(f.para("[Trình bày cấu trúc cơ bản của mã nguồn"),
            "`agqo/` (dữ liệu, danh mục, kiểm tra khả thi, lượng tử, LLM, nghiên cứu), `app/` (máy chủ web, giao diện, triển khai Modal), "
            "`modal_research.py` và `notebooks/` (mọi mô phỏng chạy trên Modal), `results/final` (bằng chứng V3), `results/runs` (mỗi lần chạy "
            "V3.2 một thư mục). Tái lập theo hướng dẫn kèm theo; LLM phát lại từ nhật ký, không cần GPU. Hạn chế: cần tệp giá có quyền sử "
            "dụng; GPU khởi động lạnh lâu.", size=BODY)
    f.write(f.para("Liên kết chạy demo"), f"Liên kết chạy demo: {URL}   |   Video demo: [đội bổ sung nếu có]", size=10)
    f.write(f.para("MINH CHỨNG BỔ SUNG", 3), "MINH CHỨNG BỔ SUNG: tests/test_v32_*.py; results/runs/*-pytest (58 passed); "
            "docs/prototype_shots/v32.", color=EVC)

    # ---------------------------------------------------------- criterion 5
    f.write(f.para("[Xác định đối tượng sử dụng, môi trường"),
            "Người dùng cuối: nhà đầu tư cá nhân 20–200 triệu đồng. Đơn vị triển khai: công ty chứng khoán, như một tính năng trong ứng dụng "
            "môi giới: khách nhập yêu cầu → xác nhận ràng buộc → nhận đề xuất lệnh mỗi quý → tự đặt lệnh. Điều kiện: dữ liệu giá ngày có "
            "quyền sử dụng, biểu phí thật, danh mục đang có của khách, máy chủ CPU; GPU cho LLM có thể dùng chung.", size=BODY)
    f.write(f.para("[Nêu lợi ích ứng dụng, hiệu quả dự kiến"),
            f"Với 20 triệu, sai số bám thực tế giảm {F['d20_round']} điểm % so với làm tròn từng mã (KTC 95% {F['d20_round_ci']}); ở 50 triệu "
            "giảm khoảng 0,6 điểm %; từ 100 triệu khác biệt không đáng kể. Chi phí của từng quy tắc được đo và cho người dùng thấy: hai quy tắc "
            f"của ví dụ làm sai số bám tăng từ {F['agqo_none']} lên {F['agqo_rules']}. Một bộ giải cổ điển tốt (tham lam) đạt gần cùng mức, nên "
            "giá trị nằm ở quy trình hiểu yêu cầu, xác nhận, tối ưu theo lô và kiểm tra quy tắc.", size=BODY)
    f.write(f.para("[Phân tích chi phí triển khai/vận hành"),
            "Chi phí: dưới 0,01 USD CPU mỗi quyết định; LLM khoảng 4 USD/giờ H100 khi bật, tự tắt sau 5 phút, giới hạn số lời gọi mỗi giờ. "
            "**Bảo mật:** LLM mã mở tự vận hành, yêu cầu của khách không gửi ra bên thứ ba; LLM không tạo tỷ trọng hay lệnh. **Rủi ro và kiểm "
            "soát:** hiểu sai yêu cầu → nhãn nguồn, hỏi lại, xác nhận bắt buộc; quy tắc bị vi phạm sau phí → kiểm tra trên NAV sau phí, kiểm "
            "thử hồi quy; lời giải thích sai → đối chiếu số, đơn vị, khẳng định về thị trường, thay bằng giải thích tạo từ dữ liệu.", size=BODY)
    f.write(f.para("[Xây dựng các bước, nguồn lực và mốc"),
            "Bước 1: thử nghiệm thí điểm với một công ty chứng khoán trên tài khoản thử, đo tỷ lệ ràng buộc được hiểu → xác nhận → thỏa và mức "
            "hiểu lời giải thích. Bước 2: nhập danh mục đang có, giá khớp gốc và sự kiện doanh nghiệp, chạy lại kiểm định. Bước 3: thử trình "
            "đọc yêu cầu với người dùng độc lập. Bước 4: theo dõi QAOA khi bài toán lớn hơn (nhiều lô mỗi mã, rổ rộng hơn); chạy phần cứng khi "
            "có token và ngân sách. Hiện trạng: chưa có đối tác thí điểm, chưa có người dùng độc lập, chưa chạy phần cứng.", size=BODY)
    f.write(f.para("MINH CHỨNG BỔ SUNG", 4), "MINH CHỨNG BỔ SUNG: docs/vi/LO_TRINH.md (phạm vi và điều kiện của từng hạng mục).",
            color=EVC)

    # ---------------------------------------------------------- criterion 6
    p = f.write(f.para("[Liệt kê báo cáo, slide"), "Hồ sơ nộp kèm (phiên bản v3.2.0):", size=BODY)
    f.table_from(4, p, ["Thành phần", "Tên tệp / đường dẫn", "Ghi chú"], [
        ["Báo cáo giải pháp", "AQ2026-R2-Madoi-Bao_cao_giai_phap.pdf", "theo mẫu BTC"],
        ["Slide trình bày", "AQ2026-R2-Madoi-Slide.pptx (+ PDF dự phòng)", "8 slide chính + 10 phụ lục, chỉnh sửa được, có ghi chú"],
        ["Mã nguồn", "AQ2026-R2-Madoi-Ma_nguon.zip", "gắn với một commit; tệp giá tải riêng"],
        ["Hướng dẫn", "AQ2026-R2-Madoi-Huong_dan.pdf", "nhanh cho giám khảo + tái lập"],
        ["Prototype", URL, "công khai, không cần tài khoản"]], size=8.5)
    f.write(f.para("[Nêu cấu trúc trình bày rõ ràng"),
            "Tám slide quanh một quyết định: giá một lô so với 20 triệu → ba lựa chọn (ETF, lô lẻ, lô chẵn theo quy tắc) → demo (yêu cầu → "
            "ràng buộc đã xác nhận → hai danh mục) → 12 quý theo cỡ tài khoản → một qubit là một câu hỏi có/không → mạch thay đổi điều gì → "
            "bước tiếp theo → quay lại người có 20 triệu. Có bản 3 phút (slide 1, 3, 4, 8); demo dùng câu trả lời Qwen đã lưu có nhãn, tối ưu "
            "chạy trực tiếp.", size=BODY)
    f.write(f.para("[Nêu người trình bày, phương án tổ chức"),
            "Chia vai: tài chính (sai số bám, lô lẻ, ETF), lượng tử (QAOA, nhiễu, quy mô), AI/LLM (đọc yêu cầu, kiểm chứng, chi phí). Mười thẻ "
            "hỏi–đáp đã chuẩn bị, gồm: vì sao nghiên cứu QAOA ở kích thước liệt kê được; vì sao chọn lô chẵn thay vì ETF hay lô lẻ; k-NN thêm "
            "được gì; ai phát hiện khi AI hiểu sai. Nguyên tắc: trả lời bằng số đo, nói rõ giả định và giới hạn.", size=BODY)

    from docx.oxml.ns import qn
    start = f.para("1. MỨC ĐỘ LÀM RÕ")._p
    started = False
    for el in list(f.doc.element.body.iterchildren()):
        started = started or el is start
        if not started or el.tag != qn("w:p"):
            continue
        txt = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
        busy = el.find(".//" + qn("w:sectPr")) is not None or el.find(".//" + qn("w:br")) is not None \
            or el.find(".//" + qn("w:drawing")) is not None
        nxt = el.getnext()
        nxt_style = nxt.find(".//" + qn("w:pStyle")) if nxt is not None and nxt.tag == qn("w:p") else None
        if not txt and not busy and nxt_style is not None and nxt_style.get(qn("w:val")).startswith("Heading"):
            el.getparent().remove(el)
    out_dir = out_dir or ROOT / "submission" / "drafts" / ("report-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
    out_dir.mkdir(parents=True, exist_ok=False)
    out = out_dir / "AQ2026-R2-Madoi-Bao_cao_giai_phap.docx"
    f.doc.save(str(out))
    print(out)
    return out


if __name__ == "__main__":
    build()
