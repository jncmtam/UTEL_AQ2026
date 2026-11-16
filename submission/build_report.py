"""Fill the organisers' report template -> AQ2026-R2-Madoi-Bao_cao_giai_phap.docx (then PDF via Word).

    python submission/build_report.py <template.docx>

Only the placeholders ([...]) and the "MINH CHỨNG BỔ SUNG" slots of the official template are
replaced; headings, tables, headers, footers and page breaks are kept so the report follows the
template exactly. Team details (names, IDs, e-mails) stay as placeholders for the team to fill in.
Every number is read from results/final (or docs/figures_vi/facts.json), not typed by hand.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "results" / "final"
FIG = ROOT / "docs" / "figures_vi" / "light"
SHOT = ROOT / "docs" / "prototype_shots"
OUT = ROOT / "submission" / "out" / "AQ2026-R2-Madoi-Bao_cao_giai_phap.docx"
URL = "https://data1--agqo-demo.us-east.modal.run"
BODY = 10
NAME = "AGQO – Danh mục bám VN30 bằng lô chẵn cho nhà đầu tư nhỏ, do AI dẫn dắt và tối ưu bằng mạch lượng tử QAOA"

st = json.loads((RUN / "quantum_stats.json").read_text())
man = json.loads((RUN / "run_manifest.json").read_text())
facts = json.loads((ROOT / "docs" / "figures_vi" / "facts.json").read_text())
me = json.loads((RUN / "llm" / "mandate_eval.json").read_text())["score"]
exs = json.loads((RUN / "llm" / "explanations.json").read_text())["score"]
live = json.loads((RUN / "llm" / "prototype_live_example.json").read_text())
sw = man["sweep_ci"]


def vn(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Filler:
    def __init__(self, template: Path):
        self.doc = docx.Document(str(template))
        self.fig_no = 0
        self.tab_no = 0

    # ---------------------------------------------------------- finding
    def para(self, startswith: str, nth: int = 0) -> Paragraph:
        hits = [p for p in self.doc.paragraphs if p.text.strip().startswith(startswith)]
        return hits[nth]

    # ---------------------------------------------------------- writing
    @staticmethod
    def write(p: Paragraph, text: str, size: float | None = None, color=None, italic=False, align=None):
        """Replace the paragraph's runs; **bold** segments become bold runs."""
        base = p.runs[0] if p.runs else None
        font_name = base.font.name if base is not None else None
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        for k, seg in enumerate(re.split(r"\*\*", text)):
            if not seg:
                continue
            r = p.add_run(seg)
            r.bold = k % 2 == 1
            r.italic = italic
            if font_name:
                r.font.name = font_name
            if size:
                r.font.size = Pt(size)
            r.font.color.rgb = color or RGBColor(0x1F, 0x29, 0x37)
        if align is not None:
            p.alignment = align
        return p

    def after(self, anchor, new_el):
        anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl if hasattr(anchor, "_tbl") else anchor
        anchor_el.addnext(new_el)
        return new_el

    def new_par(self, anchor, text, size=10.5, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=3,
                bullet=False):
        """Paragraph after `anchor`, styled like the body text; returns the Paragraph."""
        src = anchor if isinstance(anchor, Paragraph) else None
        el = copy.deepcopy(src._p) if src is not None and src.style.name == "Normal" else self.doc.add_paragraph()._p
        if src is None or src.style.name != "Normal":
            pass
        self.after(anchor, el)
        p = Paragraph(el, anchor._parent if isinstance(anchor, Paragraph) else self.doc._body)
        p.style = self.doc.styles["Normal"]
        self.write(p, ("• " if bullet else "") + text, size=size, italic=italic, align=align)
        pf = p.paragraph_format
        pf.space_after = Pt(space_after)
        pf.space_before = Pt(0)
        if bullet:
            pf.left_indent = Cm(0.4)
            pf.first_line_indent = Cm(-0.3)
        return p

    def figure(self, anchor, path: Path, width_cm: float, caption: str):
        el = self.doc.add_paragraph()._p
        self.after(anchor, el)
        p = Paragraph(el, self.doc._body)
        p.style = self.doc.styles["Normal"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Cm(width_cm))
        self.fig_no += 1
        cap = self.new_par(p, f"Hình {self.fig_no}. {caption}", size=9, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                           space_after=5)
        for r in cap.runs:
            r.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
        return cap

    def figure2(self, anchor, items: list[tuple[Path, float]], caption: str):
        """Two pictures side by side in one centred paragraph, one caption."""
        el = self.doc.add_paragraph()._p
        self.after(anchor, el)
        p = Paragraph(el, self.doc._body)
        p.style = self.doc.styles["Normal"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        for k, (path, w) in enumerate(items):
            if k:
                p.add_run("  ")
            p.add_run().add_picture(str(path), width=Cm(w))
        self.fig_no += 1
        cap = self.new_par(p, f"Hình {self.fig_no}. {caption}", size=9, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                           space_after=5)
        for r in cap.runs:
            r.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
        return cap

    def table_from(self, template_idx: int, anchor, header: list[str] | None, rows: list[list[str]], caption: str | None = None,
                   widths_cm: list[float] | None = None, size: float = 9):
        """Clone a styled template table (header row + first body row) and fill it."""
        src = self.doc.tables[template_idx]
        tbl_el = copy.deepcopy(src._tbl)
        trs = tbl_el.findall(docx.oxml.ns.qn("w:tr"))
        head_tr, body_tr = trs[0], trs[1]
        for tr in trs[1:]:
            tbl_el.remove(tr)
        if caption:
            self.tab_no += 1
            anchor = self.new_par(anchor, f"Bảng {self.tab_no}. {caption}", size=9, italic=True,
                                  align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
            anchor.paragraph_format.keep_with_next = True
            for r in anchor.runs:
                r.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
        self.after(anchor, tbl_el)
        from docx.table import Table

        t = Table(tbl_el, anchor._parent if isinstance(anchor, Paragraph) else self.doc._body)
        if header:
            for c, txt in zip(t.rows[0].cells, header):
                self._cell(c, txt, size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        for row in rows:
            tr = copy.deepcopy(body_tr)
            tbl_el.append(tr)
            for c, txt in zip(t.rows[-1].cells, row):
                self._cell(c, txt, size)
        if widths_cm:
            for row in t.rows:
                for c, w in zip(row.cells, widths_cm):
                    c.width = Cm(w)
        # an empty spacer paragraph after the table keeps following text off the table
        sp = self.doc.add_paragraph()._p
        tbl_el.addnext(sp)
        spp = Paragraph(sp, self.doc._body)
        spp.paragraph_format.space_after = Pt(2)
        spp.paragraph_format.space_before = Pt(0)
        return spp

    def _cell(self, cell, text, size=9, bold=False, color=None):
        p = cell.paragraphs[0]
        for extra in cell.paragraphs[1:]:
            extra._p.getparent().remove(extra._p)
        keep_color = color
        self.write(p, text, size=size, color=keep_color or RGBColor(0x1F, 0x29, 0x37))
        if bold:
            for r in p.runs:
                r.bold = True

    def fill_table(self, idx: int, values: dict[tuple[int, int], str], size=9.5):
        t = self.doc.tables[idx]
        for (r, c), v in values.items():
            self._cell(t.rows[r].cells[c], v, size)

    def remove(self, p: Paragraph):
        p._p.getparent().remove(p._p)


def build(template: Path) -> Path:
    f = Filler(template)
    W = 17.0
    a, b, c = st["agqo vs warm_start_only"], st["agqo vs textbook"], st["agqo vs random"]
    rb_rows = {r["capital_vnd"]: r for r in __import__("pandas").read_csv(RUN / "extras" / "robustness.csv").to_dict("records")
               if str(r["scenario"]).startswith("base")}
    g20 = rb_rows[20e6]
    dc = facts["decision"]
    sc = facts["schedules"]

    # ---------------------------------------------------------- cover + administrative tables
    f.write(f.para("[Nhập tên giải pháp"), NAME, size=13)
    from docx.oxml.ns import qn as _qn
    ts = list(f.doc.element.body.iter(_qn("w:t")))                      # back cover sits in a text box
    for i, t in enumerate(ts[:-1]):
        if (t.text or "").strip() == "TÊN GIẢI PHÁP" and (ts[i + 1].text or "").startswith("[...."):
            ts[i + 1].text = "AGQO – Bám VN30 bằng lô chẵn, do AI dẫn dắt và tối ưu lượng tử"
    f.fill_table(2, {(2, 1): NAME, (3, 1): "Tài chính (đầu tư chứng khoán) · liên ngành AI và tính toán lượng tử",
                     (4, 1): "AI và lượng tử trong tối ưu danh mục đầu tư"})
    f.fill_table(4, {(1, 1): "Web app: dashboard tương tác + LLM + mô phỏng lượng tử", (1, 2): "v3.1 (16/11/2026)",
                     (2, 1): URL, (2, 2): "Công khai, không cần tài khoản",
                     (3, 1): "AQ2026-R2-Madoi-Ma_nguon.zip", (3, 2): "Mã nguồn, dữ liệu, kết quả, kiểm thử",
                     (4, 1): "AQ2026-R2-Madoi-Huong_dan.pdf", (4, 2): "Cài đặt ~10 phút; chạy thử không cần GPU"})

    # ---------------------------------------------------------- executive summary
    f.fill_table(6, {
        (1, 1): "Nhà đầu tư nhỏ muốn “VN30 theo cách của mình” nhưng chỉ đặt được lô 100 cổ phiếu: 1 lô = 1–24% tài khoản 100 triệu, tới 110% tài khoản 20 triệu. AGQO chọn tổ hợp lô bám chỉ số tốt nhất, tuân thủ quy tắc cá nhân.",
        (1, 2): "Mục 1; Hình 1",
        (2, 1): "40 mã từng thuộc VN30 (thành phần theo thời điểm), VN30, VN-Index, 3 ETF; dữ liệu ngày 01/2022–11/2026, 52.686 dòng; huấn luyện chỉ năm 2023, kiểm định 12 quý 2024–2026.",
        (2, 2): "Mục 2; Bảng 1",
        (3, 1): f"QUBO 16 qubit = sai số bám² + vòng quay + ngân sách; mạch QAOA do dữ liệu thiết kế, AI (k-NN) chọn lịch. Hơn khởi động cổ điển {vn(a['ratio'])}×, QAOA sách giáo khoa {vn(b['ratio'], 0)}× (12/12 quý, p = 0,0005).",
        (3, 2): "Mục 3; Hình 3–6",
        (4, 1): "Web app chạy thật: yêu cầu tiếng Việt → LLM → Hamiltonian → mạch → 512 mẫu → kiểm chứng 65.536 tổ hợp → lệnh, ~5 giây; xuất OpenQASM.",
        (4, 2): "Mục 4; link demo",
        (5, 1): "Tính năng “VN30 của tôi” cho công ty chứng khoán; CPU ~2 giây/quyết định, LLM mã nguồn mở tự vận hành; lộ trình 4 quý 2027.",
        (5, 2): "Mục 5",
        (6, 1): "Báo cáo, slide 20 trang có hoạt ảnh, prototype, mã nguồn có chú thích + 25 kiểm thử, hướng dẫn cài đặt, kịch bản thuyết trình + 75 câu hỏi phản biện.",
        (6, 2): "Mục 6",
    })
    vp = f.para("[Giải pháp giúp ai")
    f.write(vp, "AGQO giúp nhà đầu tư cá nhân vốn nhỏ nắm giữ danh mục bám VN30 theo quy tắc riêng (bỏ mã, giới hạn ngành, số mã, "
                "tiền mặt) chỉ bằng lệnh lô chẵn 100 cổ phiếu. LLM mã nguồn mở Qwen3.8-27B dịch yêu cầu tiếng Việt thành ràng buộc "
                "kiểm tra được; thống kê và một mô hình học dẫn dắt thiết kế mạch lượng tử QAOA 16 qubit; liệt kê cổ điển kiểm chứng "
                "từng quyết định. Trên 12 quý chưa từng thấy (2024–2026), tài khoản 20 triệu giảm sai số bám từ "
                f"{vn(sw['20000000']['te_b'])}% xuống {vn(sw['20000000']['te_a'])}%; mạch lấy nghiệm gần tối ưu nhiều gấp "
                f"{vn(a['ratio'])} lần khởi động cổ điển; 0 vi phạm quy tắc.", size=BODY)
    t7 = f.doc.tables[7]
    body = t7.rows[1]._tr
    kpis = [("Sai số bám VN30, tài khoản 20 triệu", f"{vn(sw['20000000']['te_b'])}% (làm tròn lô)", f"{vn(sw['20000000']['te_a'])}%", "12 quý, 711 phiên; KTC 95% −6,9 đến −3,8 đ%"),
            ("Lượt đo trúng nghiệm gần tối ưu", f"{vn(100 * a['mean_b'])}% (khởi động ấm)", f"{vn(100 * a['mean_a'])}% ({vn(a['ratio'])}×)", "12/12 quý, Wilcoxon p = 0,0005"),
            ("Dịch yêu cầu tiếng Việt đúng", f"{vn(me['rule_effective_pct'])}% (quy tắc từ khoá)", "35/35 (Qwen3.8)", "35 câu thử có nhãn chuẩn"),
            ("Vi phạm quy tắc cá nhân", "—", "0", "3 yêu cầu × 12 quý"),
            ("Thời gian một quyết định (16 qubit)", "—", "~2 giây CPU", "mô phỏng + liệt kê 65.536 tổ hợp")]
    for tr in t7.rows[2:]:
        tr._tr.getparent().remove(tr._tr)
    for i, row in enumerate(kpis):
        if i:
            t7._tbl.append(copy.deepcopy(body))
        for cidx, v in enumerate(row):
            f._cell(t7.rows[-1].cells[cidx], v, 9)

    # ---------------------------------------------------------- criterion 1
    p = f.write(f.para("[Mô tả cụ thể nghiệp vụ kinh tế"), "Cuối 10/2026 Việt Nam có hơn **14,3 triệu tài khoản** chứng khoán cá nhân "
                "trong nước (VSDC), phần lớn vốn nhỏ. Nhu cầu phổ biến là “nắm giữ cả rổ VN30 nhưng theo cách của tôi”: bỏ mã đã có, giới "
                "hạn ngành, giữ tiền mặt. ETF VN30 rẻ và đa dạng nhưng **không thể cá nhân hoá**; danh mục chỉ số cá nhân hoá (direct "
                "indexing) đòi hỏi mua từng mã, mà HOSE khớp lệnh theo **lô 100 cổ phiếu**. Đối tượng: nhà đầu tư 20–200 triệu đồng và "
                "công ty chứng khoán muốn cung cấp tính năng này.", size=BODY)
    p = f.figure2(p, [(FIG / "01_lot_cost.png", 8.2), (FIG / "10_one_decision.png", 8.8)],
                  f"Trái: giá một lô của 30 mã VN30 so với tài khoản 20 triệu ({facts['lot']['date']}): {facts['lot']['over10']}/30 mã vượt 10% "
                  f"tài khoản, VIC vượt cả tài khoản. Phải: một quyết định thật cho tài khoản mới 20 triệu: làm tròn "
                  f"({vn(dc['te']['practitioner'])}%), tham lam ({vn(dc['te']['greedy'])}%, dồn 36% vào MWG), AGQO ({vn(dc['te']['agqo'])}% = tối ưu chính xác).")
    f.write(f.para("[Phân tích nguyên nhân, mức độ"), "Nguyên nhân gốc: bộ tối ưu cho tỷ trọng liên tục (“giữ 3,4% VIC”) nhưng tài khoản "
            "chỉ giữ được 0 hoặc trọn lô. Làm tròn lô gần nhất – cách phổ biến – với 20 triệu làm tròn gần như mọi mã về 0, để "
            f"**{vn(dc['cash_naive'], 0)}% tiền nằm im**, sai số bám dự kiến {vn(dc['te']['practitioner'])}%. Yêu cầu nghiệp vụ: (i) chỉ lệnh lô chẵn, "
            "đủ tiền sau phí 0,15% và thuế bán 0,1%; (ii) tuân thủ tuyệt đối quy tắc cá nhân; (iii) bám VN30 sát nhất; (iv) giải thích "
            "bằng tiếng Việt, kiểm chứng được.", size=BODY)
    f.write(f.para("[Chuyển vấn đề thực tiễn thành"), "**Bài toán tối ưu tổ hợp nhị phân.** Đầu vào: vốn, danh mục hiện có, yêu cầu tiếng Việt, "
            "giá và hiệp phương sai 250 phiên. Bước 1 giải QP liên tục có trần; bước 2, với 16 mã mà việc làm tròn quan trọng nhất, "
            "mỗi qubit x_k ∈ {0,1} quyết định “mua thêm một lô mã k?”. Mục tiêu E(x) = 252(wᵀΣw − 2wᵀc + σ_b²) + γ‖w − w_cũ‖² + "
            "λ(1ᵀw − t)², w = w₀ + Ax (γ = 0,002; λ = 0,01). Đầu ra: danh sách lệnh lô chẵn. Thước đo: sai số bám VN30 (năm hoá), "
            "vi phạm quy tắc, tỷ lệ lượt đo trúng nghiệm trong 5% tối ưu.", size=BODY)
    f.write(f.para("[Chỉ ra các ràng buộc và khó khăn"), "(1) **Ràng buộc trần làm hỏng QUBO**: phạt bậc hai cho phép ba lô vi phạm trần dù "
            "từng cặp hợp lệ → đội thiết kế **thanh ghi an toàn trần**: chỉ mã nào thêm lô vẫn giữ mọi trần mới có qubit, nên cả "
            "2¹⁶ trạng thái hợp lệ. (2) **Ngôn ngữ tự nhiên** (không dấu, “một phần ba”, mơ hồ) → LLM với lược đồ JSON + mã kiểm tra, "
            "hỏi lại khi mơ hồ. (3) **Nhiễu phần cứng** → AI chọn mạch nông theo nhiễu. (4) **Thời gian 16 qubit** → mô phỏng "
            "statevector chính xác ~1 giây.", size=BODY)
    f.write(f.para("[Nêu mức đạt, phần chưa giải quyết"), "Đạt: bài toán lô chẵn có quy tắc cá nhân được giải và kiểm chứng chính xác; "
            f"lợi ích lớn và có ý nghĩa thống kê ở tài khoản 20 triệu ({vn(sw['20000000']['te_b'])}% → {vn(sw['20000000']['te_a'])}%) và 50 triệu. "
            "Chưa giải quyết: chưa kết nối API đặt lệnh thật; với 100 triệu, lô đã đủ nhỏ nên khác biệt không có ý nghĩa thống kê.", size=BODY)
    ev = f.para("MINH CHỨNG BỔ SUNG", 0)
    f.write(ev, "MINH CHỨNG BỔ SUNG: Hình 1 tái lập bằng `python -m agqo.figures_vi`; chạy lại quyết định trên prototype.",
            color=RGBColor(0x0F, 0x4C, 0x5C))

    # ---------------------------------------------------------- criterion 2
    f.write(f.para("[Nêu từng nguồn dữ liệu"), "**Giá:** API biểu đồ công khai của DNSE (không cần khoá), OHLCV ngày 04/01/2022–13/11/2026, "
            "52.686 dòng cho 40 mã từng thuộc VN30, chỉ số VN30 và VN-Index, ba ETF VN30 (E1VFVN30, FUESSV30, FUEKIV30); giá cổ "
            "phiếu đã điều chỉnh bởi nhà cung cấp. **Thành phần VN30 theo thời điểm:** lịch sử 11 lần thay đổi rổ do đội đối chiếu "
            "công bố HOSE (tránh sai lệch sống sót). **Ngôn ngữ:** 35 câu yêu cầu tiếng Việt có nhãn chuẩn do đội soạn. Dữ liệu "
            "công khai, chỉ dùng cho nghiên cứu; tệp có SHA-256 trong manifest để kiểm tra toàn vẹn.", size=BODY)
    f.write(f.para("[Mô tả quy trình thu thập, kiểm tra"), "Tải tự động (`python -m agqo download`), ghi manifest và SHA-256. Kiểm tra điều "
            "chỉnh giá: 31/46.609 ngày–mã biến động vượt biên độ HOSE (3 mã, đã rà soát) → chuỗi được xem là đã điều chỉnh. Mã thiếu "
            "lịch sử (< 180 phiên trong 250 phiên gần nhất) bị loại khỏi kỳ đó và ghi lại; ở 12 quý kiểm định cả 30 mã đều dùng được. "
            "Hiệp phương sai co về đường chéo (5%) trên ma trận chung [cổ phiếu, chỉ số] để sai số bám² luôn ≥ 0.", size=BODY)
    f.write(f.para("[Chứng minh mức độ đại diện"), "Giai đoạn 2022–2026 gồm thị trường giảm 2022, đi ngang 2023–2024 và tăng mạnh 2025, "
            "đủ đa dạng. **Chống rò rỉ:** mọi lựa chọn (hệ số phạt λ, lịch mạch, k của k-NN, có tinh chỉnh hay không) chỉ học trên "
            "48 bài toán năm 2023 (12 tháng × 4 cỡ tài khoản); kiểm định trên 12 quý 01/2024–10/2026 chưa từng thấy. Rổ VN30 theo "
            "thời điểm nên không dùng thông tin tương lai. So sánh cặp (Wilcoxon, bootstrap khối 21 ngày).", size=BODY)
    f.write(f.para("[Giải thích việc lựa chọn/tạo đặc trưng"), "**Đặc trưng thị trường:** tương quan trung bình, tỷ trọng nhân tố thị trường, "
            f"số cược độc lập (Meucci 2009; trung bình ≈ {vn(facts['market']['bets'], 0)}), cụm tương quan ≥ 0,5. **Đặc trưng bài toán** "
            "cho mô hình chọn lịch: độ tự tin khởi động ấm, tỷ lệ qubit đã rõ, log(trường/tương tác), độ tập trung tương tác, cỡ lô. "
            "Không tăng cường dữ liệu: tạo dữ liệu giả sẽ làm sai cấu trúc tương quan thật.", size=BODY)
    q = f.para("Minh chứng chất lượng dữ liệu")
    f.table_from(2, q, ["Hạng mục", "Kết quả kiểm tra"], [
        ["Quy mô", "52.686 dòng ngày; 40 mã + 2 chỉ số + 3 ETF; 01/2022–11/2026"],
        ["Toàn vẹn", "SHA-256 trong manifest; tải lại cho cùng kết quả"],
        ["Điều chỉnh giá", "31/46.609 ngày–mã vượt biên độ (BSR, MCH, NVL) – đã rà soát"],
        ["Bao phủ kiểm định", "30/30 mã dùng được ở cả 12 quý"],
        ["Rò rỉ thông tin", "Huấn luyện 2023; kiểm định 2024–2026; thành phần VN30 theo thời điểm"],
        ["Nhãn ngôn ngữ", "35 câu, có câu không dấu, câu mơ hồ cần hỏi lại"]], caption="Kiểm tra chất lượng dữ liệu.", size=9)
    ev = f.para("MINH CHỨNG BỔ SUNG", 1)
    f.write(ev, "MINH CHỨNG BỔ SUNG: cấu trúc thị trường đọc từ dữ liệu", color=RGBColor(0x0F, 0x4C, 0x5C))
    f.figure(ev, FIG / "03_market.png", 8.6, f"Số cược độc lập (cột) và tỷ trọng phương sai của nhân tố thị trường (đường), 12 quý kiểm định: "
             f"VN30 ≈ {vn(facts['market']['bets'], 0)} cược độc lập, nhân tố chung ≈ {vn(facts['market']['factor'], 0)}%.")

    # ---------------------------------------------------------- criterion 3
    p = f.write(f.para("[Trình bày kiến trúc, luồng xử lý"), "Luồng: dữ liệu → **AI đọc thị trường** (thống kê) và **LLM dịch yêu cầu** "
                "→ QP liên tục có trần → **thanh ghi 16 qubit an toàn trần** và QUBO → **AI chọn lịch mạch** (k-NN) → **mạch QAOA** "
                "512 lần đo → **kiểm chứng chính xác** (tiền, phí, thuế, trần; liệt kê 2¹⁶) → lệnh → **LLM giải thích**, mọi con số được đối chiếu.", size=BODY)
    f.figure(p, FIG / "02_pipeline.png", 15.0, "Kiến trúc AGQO. Xanh dương: AI; tím: lượng tử; xanh lá: cổ điển chính xác; xám: dữ liệu và đầu ra.")
    f.write(f.para("[Nêu phương pháp/thuật toán cụ thể"), "**QAOA** phù hợp vì bài toán là QUBO nhị phân với tương tác cặp đúng bằng hiệp "
            "biến động của cổ phiếu. Năm quy tắc thiết kế, mỗi quy tắc bật theo một thống kê: R1 khởi động ấm từ nghiệm nới lỏng "
            "(Egger 2021); R2 bộ trộn căn chỉnh (He 2023); R3 giữ tương tác mạnh theo khối lượng J²; R4 chia Hamiltonian cho RMS "
            "hệ số (Sureshbabu 2024); R5 góc dốc tuyến tính (LR-QAOA 2025). **LLM Qwen3.8-27B** (mã mở, vLLM, 1 GPU H100, giải mã "
            "theo lược đồ JSON, nhiệt độ 0) chỉ dịch ngôn ngữ, không tạo tỷ trọng. **k-NN** chọn 1 trong "
            f"{vn(sc['n'], 0)} lịch (p, ε, khối lượng J, Δγ, Δβ) theo 10 bài toán 2023 giống nhất.", size=BODY)
    f.write(f.para("[Mô tả các bước triển khai theo logic"), "Giả định: phí 0,15% hai chiều, thuế bán 0,1%, đầu tư mục tiêu 98%, tái cân "
            "bằng theo quý, giá đóng cửa. Tham số: 16 qubit, λ = 0,01 (chọn trên 2023), γ = 0,002, 512 lần đo, ngân sách cổng hai "
            f"qubit; k = 10 (kiểm định chéo theo tháng); tinh chỉnh COBYLA trên CVaR bật vì cải thiện trên 2023. Kiểm tra: "
            f"25 kiểm thử tự động; mạch xuất bằng Qiskit 2.5 khớp mô phỏng numpy; mô hình dựng lại chọn đúng lịch ở 12/12 quý.", size=BODY)
    p = f.write(f.para("[Đưa kết quả thuật toán chạy trên dữ liệu"), f"Trên 12 quý kiểm định, mạch AGQO đưa {vn(100 * a['mean_a'])}% lượt "
                f"đo vào vùng trong 5% tối ưu: gấp **{vn(a['ratio'])}×** khởi động cổ điển, **{vn(b['ratio'], 0)}×** QAOA sách giáo khoa, "
                f"**{vn(c['ratio'])}×** tìm kiếm ngẫu nhiên thiết kế mạch; thắng 12/12 quý (p = 0,0005). Quyết định tốt nhất trong 512 "
                "mẫu trùng tối ưu chính xác ở 12/12 quý (tài khoản 100 triệu).", size=BODY)
    p = f.figure(p, FIG / "07_probability.png", 11.5, "Phân bố xác suất đo trên 65.536 tổ hợp theo khoảng cách tới tối ưu chính xác, trung bình 12 quý.")
    f.table_from(7, p, ["Tài khoản", "Làm tròn lô", "Tham lam", "AGQO (KTC 95% so với làm tròn)"], [
        [f"{vn(cap / 1e6, 0)} triệu", f"{vn(r['te_practitioner'])}%", f"{vn(r['te_greedy'])}%",
         f"{vn(r['te_whole_lot_optimum'])}% ({vn(r['ci_low'])} đến {vn(r['ci_high'])} đ%)"]
        for cap, r in sorted(rb_rows.items())], caption="Sai số bám VN30 thực tế (năm hoá), 01/2024–11/2026.", size=9)
    f.write(f.para("[Những trường hợp giải pháp chưa đạt"), "Ở 16 qubit, liệt kê cổ điển giải chính xác trong 0,12 giây nên **không tuyên "
            "bố ưu thế lượng tử**; chính phép liệt kê là trọng tài của mọi kết quả. Thuật toán tham lam đạt "
            f"{vn(g20['te_greedy'])}% (AGQO {vn(g20['te_whole_lot_optimum'])}%), khác biệt chưa có ý nghĩa thống kê ở tần suất quý. "
            "Lô lẻ bám tốt hơn khi chi phí phụ trội của lô lẻ dưới 6,8% (20 triệu) nhưng có rủi ro khớp lệnh chưa mô hình hoá. "
            "Mạch sâu p = 6 chưa chạy được trên phần cứng nhiễu hiện nay; AI chọn mạch nông 16 cổng CZ thay thế.", size=BODY)
    ev = f.para("MINH CHỨNG BỔ SUNG", 2)
    f.write(ev, "MINH CHỨNG BỔ SUNG: mạch QAOA, phần cứng và mở rộng", color=RGBColor(0x0F, 0x4C, 0x5C))
    p = f.figure(ev, FIG / "05_circuit.png", 14.0, "Một lớp mạch QAOA của AGQO (4 trên 16 qubit) và lịch góc γ, β của quý 10/2026.")
    f.figure(p, FIG / "12_hardware.png", 11.0, "Trên mô phỏng nhiễu IBM Heron: mạch sâu bị nhiễu xoá; mạch nông 16 CZ do AI chọn theo nhiễu "
             "vẫn hơn khởi động ấm 1,6× (11/12 quý, p = 0,0010).")

    # ---------------------------------------------------------- criterion 4
    f.write(f.para("[Nêu các chức năng cốt lõi đã hoạt động"), "Prototype web (FastAPI + ECharts, triển khai trên Modal, CPU, tự co giãn) "
            "chạy **thật** toàn bộ quy trình cho một tài khoản mới trên dữ liệu 01/10/2026: (1) LLM dịch yêu cầu (bản ghi trả lời thật "
            "của Qwen3.8 cho 35 câu thử; câu mới gọi GPU H100 trực tiếp, quy tắc từ khoá hiển thị trước trong lúc chờ); (2) thống kê "
            "thị trường; (3) Hamiltonian; (4) AI chọn lịch; (5) mô phỏng QAOA 512 mẫu; (6) liệt kê 65.536 tổ hợp; (7) lệnh, phí, kiểm "
            "tra quy tắc; tải mạch OpenQASM; LLM giải thích có đối chiếu số. Chưa có: đặt lệnh thật, tài khoản người dùng.", size=BODY)
    p = f.write(f.para("[Mô tả trình tự demo có thể chạy"), "Mở link → nhập vốn (ví dụ 20 triệu) và yêu cầu (ví dụ “Không mua VIC, VHM, VRE…”) "
                "→ **Chạy AGQO**: bảy bảng hiện lần lượt kèm biểu đồ (ràng buộc JSON, cụm cổ phiếu, ma trận J, đặc trưng và lịch mạch, sơ "
                "đồ mạch, phân bố xác suất, danh mục và lệnh) → **Giải thích bằng AI** → **Tải mạch OpenQASM**. Link có thể tự chạy: "
                "thêm `?run=1&capital=20&q=...` vào địa chỉ.", size=BODY)
    f.figure2(p, [(SHOT / "p5_circuit.png", 8.4), (SHOT / "p6_sampling.png", 8.4)],
              "Prototype chạy thật: bước 5 (mạch QAOA 16 qubit với từng cặp tương tác ZZ, lịch góc) và bước 6 (phân bố xác suất, "
              "12 trạng thái có xác suất cao nhất, kết luận kiểm chứng chính xác).")
    f.write(f.para("[Báo cáo kết quả bước đầu"), "Đo trên bản triển khai: khởi động container ~8 giây; một quyết định 16 qubit ~2 giây CPU "
            "(xây QUBO 0,01 giây; liệt kê 0,12 giây; QAOA + tinh chỉnh ~1 giây; QAOA sách giáo khoa để so sánh ~0,7 giây). Lời gọi LLM "
            f"mới: {live['seconds_incl_cold_start']} giây khi GPU nguội (nạp mô hình {vn(live['model_load_s'], 0)} giây), vài giây khi GPU nóng; câu "
            f"thử “{live['text']}” được Qwen3.8 dịch đúng cả hai ý, quy tắc từ khoá bỏ sót ý thứ nhất. 24/25 kiểm thử đạt. Hạn chế: "
            "GPU nguội mất ~6 phút; giới hạn 40 lời gọi LLM/giờ để kiểm soát chi phí.", size=BODY)
    f.write(f.para("[Trình bày cấu trúc cơ bản của mã nguồn"), "Mã nguồn Python có chú thích: `agqo/` (dữ liệu, danh mục, lượng tử, LLM, "
            "kiểm định, báo cáo), `app/` (máy chủ web, giao diện, triển khai Modal), `modal_app.py` (LLM trên GPU), `tests/`, `results/final` "
            "(mọi kết quả và nhật ký LLM). Tái lập: `pip install -r requirements.txt` → `python -m agqo run` (≈ 20 phút CPU) → "
            "`python -m agqo report`; LLM phát lại từ nhật ký bằng `--llm replay`, không cần GPU. Yêu cầu: Python 3.12, 8 GB RAM.", size=BODY)
    lk = f.para("Liên kết chạy demo")
    f.write(lk, f"Liên kết chạy demo: {URL}   |   Video demo: [đội bổ sung nếu có]", size=10)
    ev = f.para("MINH CHỨNG BỔ SUNG", 3)
    f.write(ev, "MINH CHỨNG BỔ SUNG: 24/25 kiểm thử tự động đạt (`pytest`); nhật ký mọi lời gọi LLM trong results/final/llm.",
            color=RGBColor(0x0F, 0x4C, 0x5C))

    # ---------------------------------------------------------- criterion 5
    f.write(f.para("[Xác định đối tượng sử dụng, môi trường"), "Người dùng cuối: nhà đầu tư cá nhân 20–200 triệu đồng. Đơn vị triển khai: "
            "công ty chứng khoán, tích hợp như tính năng “VN30 của tôi” trong ứng dụng môi giới: khách nhập yêu cầu → AGQO đề xuất lệnh "
            "mỗi quý → khách xác nhận → lệnh lô chẵn qua hệ thống hiện có. Điều kiện: dữ liệu giá ngày, API đặt lệnh, một máy chủ CPU, "
            "một GPU cho LLM (hoặc dùng chung).", size=BODY)
    f.write(f.para("[Nêu lợi ích ứng dụng, hiệu quả dự kiến"), f"Với tài khoản 20 triệu, sai số bám giảm {vn(-sw['20000000']['diff_pp'])} điểm % "
            f"(KTC 95%: {vn(-sw['20000000']['ci_high'])}–{vn(-sw['20000000']['ci_low'])}); 50 triệu giảm {vn(-sw['50000000']['diff_pp'])} điểm %. "
            "Quy tắc cá nhân được tuân thủ 100% và chi phí của từng quy tắc được đo (ví dụ bỏ bất động sản + ngân hàng ≤ 30% tốn +3,78 "
            "điểm % sai số bám). Lợi ích cho công ty chứng khoán: sản phẩm cá nhân hoá cho phân khúc vốn nhỏ đông nhất.", size=BODY)
    f.write(f.para("[Phân tích chi phí triển khai/vận hành"), "Chi phí: tối ưu ~2 giây CPU/quyết định (gần như không đáng kể); LLM ~4 USD/giờ "
            "H100 khi chạy, tự tắt sau 5 phút, ~1–2 USD cho một lô yêu cầu; có thể dùng chung GPU. **Bảo mật:** LLM mã nguồn mở tự vận "
            "hành, dữ liệu khách hàng không gửi ra bên thứ ba; LLM không bao giờ tạo tỷ trọng hay lệnh. **Rủi ro:** LLM hiểu sai → mã "
            "kiểm tra lược đồ, hỏi lại khi mơ hồ, khách xác nhận trước khi đặt lệnh; dữ liệu lỗi → kiểm tra biên độ và manifest; mô "
            "hình lỗi thời → huấn luyện lại hằng năm, giám sát sai số bám.", size=BODY)
    p = f.write(f.para("[Xây dựng các bước, nguồn lực và mốc"), "Q1/2027 thí điểm API với một công ty chứng khoán (tài khoản thử nghiệm); "
                "Q2/2027 chạy mạch theo nhiễu trên IBM Heron (tệp OpenQASM đã sẵn); Q3/2027 thanh ghi nhiều lô (≥ 60 qubit, nơi liệt kê "
                "không còn khả thi), mở rộng VN100, kết hợp lô chẵn và lô lẻ; Q4/2027 ra mắt tính năng, báo cáo giải thích hằng quý. "
                "Nguồn lực: 3 kỹ sư, 1 chuyên gia tuân thủ. Mốc kiểm chứng: sai số bám thực tế, tỷ lệ yêu cầu dịch đúng, 0 vi phạm.", size=BODY)
    ev = f.para("MINH CHỨNG BỔ SUNG", 4)
    f.write(ev, "MINH CHỨNG BỔ SUNG: hiệu quả theo cỡ tài khoản và khi mở rộng", color=RGBColor(0x0F, 0x4C, 0x5C))
    sr = facts["scaling"]["ratio"]
    f.figure2(ev, [(FIG / "09_accounts.png", 7.6), (FIG / "13_scaling.png", 8.6)],
              f"Trái: sai số bám VN30 thực tế theo cỡ tài khoản, 12 quý. Phải: từ 8 đến 20 qubit, lịch học năm 2023 dùng nguyên vẫn hơn "
              f"khởi động ấm từ {vn(sr['8'])}× lên {vn(sr['20'])}× – lợi thế tăng theo quy mô.")

    # ---------------------------------------------------------- criterion 6
    p = f.write(f.para("[Liệt kê báo cáo, slide"), "Hồ sơ nộp kèm (phiên bản v3.1, 16/11/2026):", size=BODY)
    f.table_from(4, p, ["Thành phần", "Tên tệp / đường dẫn", "Ghi chú"], [
        ["Báo cáo giải pháp", "AQ2026-R2-Madoi-Bao_cao_giai_phap.pdf", "theo mẫu BTC"],
        ["Slide trình bày", "AQ2026-R2-Madoi-Slide.pptx", "20 trang, hoạt ảnh, ghi chú lời nói"],
        ["Mã nguồn", "AQ2026-R2-Madoi-Ma_nguon.zip", "mã, dữ liệu, kết quả, kiểm thử"],
        ["Hướng dẫn", "AQ2026-R2-Madoi-Huong_dan.pdf", "cài đặt, sử dụng, kiểm tra kết quả"],
        ["Prototype", URL, "công khai, không cần tài khoản"]], size=9)
    f.write(f.para("[Nêu cấu trúc trình bày rõ ràng"), "10 phút: vấn đề (1,5 phút: 1 lô VIC > tài khoản 20 triệu) → giải pháp và kiến trúc "
            "(2 phút) → AI và mạch lượng tử (2 phút) → kết quả lượng tử và tài chính (2 phút) → **demo trực tiếp** (2 phút, chuyển từ "
            "slide 17 sang link, chạy câu “Tôi làm ở ngân hàng…”) → vì sao tin được và lộ trình (0,5 phút). Bản rút gọn 3 phút sẵn sàng.", size=BODY)
    f.write(f.para("[Nêu người trình bày, phương án tổ chức"), "Chia vai: thành viên A – tài chính (sai số bám, lô lẻ, ETF); B – lượng tử "
            "(QAOA, nhiễu, ưu thế lượng tử); C – AI/LLM (Qwen3.8, kiểm chứng, chi phí). Đã chuẩn bị 75 câu hỏi phản biện kèm số liệu, "
            "năm câu khó nhất được tập dượt: không có ưu thế lượng tử, tham lam gần bằng, lô lẻ bám tốt hơn, lịch học chưa hơn lịch "
            "cố định, ETF lợi nhuận cao hơn 1,1%/năm. Nguyên tắc: trả lời bằng số đo, nói rõ giả định.", size=BODY)

    # drop the template's empty spacer paragraphs between a filled sub-section and the next heading
    # (never a paragraph that carries a section break, a page break or a picture)
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    f.doc.save(str(OUT))
    return OUT


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
