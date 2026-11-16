"""Build the contest slide deck AQ2026-R2-Madoi-Slide.pptx (Vietnamese, dark trading-terminal theme).

    python -m agqo.figures_vi                 # figures (docs/figures_vi/dark)
    python app/capture.py <url>               # prototype screenshots (docs/prototype_shots)
    python submission/build_slides.py         # -> submission/out/AQ2026-R2-Madoi-Slide.pptx

python-pptx writes the shapes; slide transitions and entrance animations are added as raw
PresentationML (<p:transition>, <p:timing>) because python-pptx has no API for them. Every slide
carries its spoken script in the speaker notes.
"""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figures_vi" / "dark"
SHOT = ROOT / "docs" / "prototype_shots"
OUT = ROOT / "submission" / "out" / "AQ2026-R2-Madoi-Slide.pptx"
URL = "https://data1--agqo-demo.us-east.modal.run"
RUN = ROOT / "results" / "final"

BG, PANEL, LINE = "0B1220", "111A2E", "1E2B44"
INK, MUTED = "E6EDF7", "8B9AB3"
UP, DOWN, AMBER, AI, Q, CL, GOLD = "22C55E", "EF4444", "F59E0B", "38BDF8", "A78BFA", "34D399", "FACC15"
FONT = "Arial"
W, H = 13.333, 7.5


def rgb(h):
    return RGBColor.from_string(h)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.layout = self.prs.slide_layouts[6]
        self.anims: dict[int, list] = {}
        self.n = 0

    # ---------------------------------------------------------- slide + primitives
    def slide(self, kicker: str | None, title: str | None, notes: str, transition: str = "fade"):
        s = self.prs.slides.add_slide(self.layout)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(BG)
        self.n += 1
        self.anims[id(s)] = []
        s._agqo_transition = transition
        if kicker:
            chip = self.box(s, 0.6, 0.38, 0.3 + 0.105 * len(kicker), 0.34, kicker.upper(), 11, GOLD, bold=True,
                            fill=None, line=GOLD, shape=MSO_SHAPE.ROUNDED_RECTANGLE, align=PP_ALIGN.CENTER)
            chip.adjustments[0] = 0.5
        if title:
            self.text(s, 0.6, 0.82, 12.1, 0.9, title, 30, INK, bold=True)
        self.text(s, 0.6, 7.05, 6, 0.3, "AGQO · AI–Quantum Challenge 2026 · Vòng 2", 9, MUTED)
        self.text(s, 12.0, 7.05, 0.75, 0.3, str(self.n), 9, MUTED, align=PP_ALIGN.RIGHT)
        s.notes_slide.notes_text_frame.text = notes
        return s

    def text(self, s, x, y, w, h, text, size=16, color=INK, bold=False, italic=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, runs=None, spacing=None):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paras = runs if runs is not None else [[(text, {})]]
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if spacing:
                p.space_after = Pt(spacing)
            for t, o in para:
                r = p.add_run()
                r.text = t
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.italic = o.get("italic", italic)
                f.color.rgb = rgb(o.get("color", color))
        return tb

    def box(self, s, x, y, w, h, text="", size=14, color=INK, bold=False, fill=PANEL, line=LINE,
            shape=MSO_SHAPE.ROUNDED_RECTANGLE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, runs=None, lw=1.25):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = min(0.5, 0.12 / max(min(w, h), 0.01))
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(lw)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        tf = sh.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.14)
        tf.margin_top = tf.margin_bottom = Inches(0.06)
        tf.vertical_anchor = anchor
        paras = runs if runs is not None else ([[(text, {})]] if text else [])
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            for t, o in para:
                r = p.add_run()
                r.text = t
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.italic = o.get("italic", False)
                f.color.rgb = rgb(o.get("color", color))
        return sh

    def image(self, s, path, x, y, w, h, frame=False):
        """Fit the picture inside the (x, y, w, h) box, centred; returns the picture shape."""
        iw, ih = Image.open(path).size
        r = min(w / iw, h / ih)
        pw, ph = iw * r, ih * r
        px, py = x + (w - pw) / 2, y + (h - ph) / 2
        if frame:
            self.box(s, px - 0.06, py - 0.06, pw + 0.12, ph + 0.12, fill=PANEL, line=LINE)
        return s.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(pw), Inches(ph))

    def caption(self, s, x, y, w, text):
        return self.text(s, x, y, w, 0.5, text, 11, MUTED, italic=True, align=PP_ALIGN.CENTER)

    def stat(self, s, x, y, w, h, big, label, color=UP, big_size=34):
        return self.box(s, x, y, w, h, runs=[[(big, {"size": big_size, "bold": True, "color": color})],
                                             [(label, {"size": 12, "color": MUTED})]], anchor=MSO_ANCHOR.MIDDLE)

    def anim(self, s, shape, effect="fade", gap=0.35, dur=0.5):
        self.anims[id(s)].append((shape, effect, gap, dur))
        return shape

    # ---------------------------------------------------------- transitions and animations (raw XML)
    def finish(self):
        P = "http://schemas.openxmlformats.org/presentationml/2006/main"
        for s in self.prs.slides:
            sld = s._element
            tr = {"fade": '<p:fade/>', "push": '<p:push dir="u"/>', "wipe": '<p:wipe dir="r"/>',
                  "cover": '<p:cover dir="l"/>', "split": '<p:split orient="vert" dir="out"/>'}[s._agqo_transition]
            sld.append(etree.fromstring(f'<p:transition xmlns:p="{P}" spd="med">{tr}</p:transition>'))
            items = self.anims[id(s)]
            if items:
                sld.append(etree.fromstring(timing_xml(items, P)))
        self.prs.save(OUT)


def _effect(spid, effect, dur_ms, ids):
    """Behaviours of one entrance effect (presetID, subtype, xml)."""
    vis = (f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
           f'</p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
           f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>')

    def fx(filt):
        return (f'<p:animEffect transition="in" filter="{filt}"><p:cBhvr><p:cTn id="{next(ids)}" dur="{dur_ms}"/>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>')

    def prop(attr, frm, to):
        return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{next(ids)}" dur="{dur_ms}" fill="hold"/>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst>'
                f'</p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="{frm}"/></p:val></p:tav><p:tav tm="100000">'
                f'<p:val><p:strVal val="{to}"/></p:val></p:tav></p:tavLst></p:anim>')

    if effect == "fade":
        return 10, 0, vis + fx("fade")
    if effect == "wipe":
        return 22, 8, vis + fx("wipe(left)")
    if effect == "rise":                       # "Fly in" from slightly below, with fade
        return 42, 0, vis + fx("fade") + prop("ppt_x", "#ppt_x", "#ppt_x") + prop("ppt_y", "#ppt_y+.1", "#ppt_y")
    if effect == "zoom":                       # "Fade zoom"
        return 53, 16, vis + prop("ppt_w", "0", "#ppt_w") + prop("ppt_h", "0", "#ppt_h") + fx("fade")
    raise ValueError(effect)


def timing_xml(items, P):
    """All entrances start automatically after the slide appears, staggered (with-previous + delay)."""
    counter = iter(range(3, 10_000))
    pars, t = [], 0.0
    for k, (shape, effect, gap, dur) in enumerate(items):
        t += gap if k else 0.25
        preset, sub, body = _effect(shape.shape_id, effect, int(dur * 1000), counter)
        pid, cid = next(counter), next(counter)
        pars.append(f'<p:par><p:cTn id="{pid}" fill="hold"><p:stCondLst><p:cond delay="{int(t * 1000)}"/></p:stCondLst>'
                    f'<p:childTnLst><p:par><p:cTn id="{cid}" presetID="{preset}" presetClass="entr" presetSubtype="{sub}" '
                    f'fill="hold" nodeType="withEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{body}'
                    f'</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    grp = next(counter)
    bld = "".join(f'<p:bldP spid="{sh.shape_id}" grpId="0"/>' for sh, e, *_ in items if sh.has_text_frame and sh.text_frame.text)
    return (f'<p:timing xmlns:p="{P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            f'<p:par><p:cTn id="{grp}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0">'
            f'<p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>{"".join(pars)}</p:childTnLst></p:cTn></p:par>'
            f'</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
            + (f'<p:bldLst>{bld}</p:bldLst>' if bld else "") + '</p:timing>')


# ====================================================================== the deck
def _tape():
    import sys
    sys.path.insert(0, str(ROOT))
    from agqo.data import MarketData
    from agqo.extras import load_config

    md, ec = MarketData.load(), load_config(RUN)
    dt = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
    uni, _ = md.universe(dt, ec.problem.lookback_days, ec.problem.min_history)
    px = (100 * 100 * md.px.loc[dt, uni] / 20e6).sort_values(ascending=False)
    return list(px.items())[:12]


TAPE: list = []


def build(live_example: dict | None = None):
    global TAPE
    TAPE = _tape()
    d = Deck()
    facts = json.loads((ROOT / "docs" / "figures_vi" / "facts.json").read_text())
    st = json.loads((RUN / "quantum_stats.json").read_text())
    A, B = d.anim, d.box

    # 1 ── title
    s = d.slide(None, None, transition="fade", notes=(
        "Kính thưa Ban Giám khảo. Hôm nay đội chúng em trình bày AGQO: giúp một nhà đầu tư nhỏ nắm giữ danh mục bám VN30 "
        "theo đúng quy tắc riêng của mình, bằng các lô 100 cổ phiếu thật. AI hiểu yêu cầu và đọc thị trường, mạch lượng tử "
        "QAOA chọn tổ hợp lô, và máy tính cổ điển kiểm chứng từng quyết định trước khi ra lệnh."))
    tape = []
    for t, pct in TAPE:
        tape += [(t + " ", {"bold": True, "color": INK}), (f"{pct:.0f}%   ".replace(".", ","), {"color": DOWN if pct > 10 else UP})]
    A(s, d.text(s, 0.0, 0.25, W, 0.35, "", runs=[tape], size=12, align=PP_ALIGN.CENTER), "wipe", dur=1.4)
    A(s, d.text(s, 0.7, 0.62, 12, 0.3, "giá 1 lô / tài khoản 20 triệu đồng · 01/10/2026", 9, MUTED, italic=True, align=PP_ALIGN.CENTER), "fade", gap=0.1)
    A(s, d.text(s, 0.7, 1.3, 11.5, 0.4, "AI–QUANTUM CHALLENGE 2026 · VÒNG 2 · TÀI CHÍNH ĐỊNH LƯỢNG", 13, GOLD, bold=True), "fade")
    A(s, d.text(s, 0.7, 1.75, 11.9, 1.75, "", runs=[
        [("Bám ", {"size": 46, "bold": True}), ("VN30", {"size": 46, "bold": True, "color": UP}), (" theo cách của bạn,", {"size": 46, "bold": True})],
        [("bằng từng ", {"size": 46, "bold": True}), ("lô 100 cổ phiếu", {"size": 46, "bold": True, "color": GOLD})]]), "rise")
    A(s, d.text(s, 0.7, 3.6, 11.5, 0.8, "AGQO · AI-Guided Quantum Optimisation: AI đọc thị trường và yêu cầu của bạn, mạch lượng tử "
                                       "QAOA chọn tổ hợp lô, máy tính cổ điển kiểm chứng từng quyết định.", 18, "C7D2E4"), "fade")
    for i, (big, lab, c) in enumerate([("12,1% → 6,8%", "sai số bám VN30, tài khoản 20 triệu", UP),
                                       ("6,9×", "lượt đo trúng nghiệm tốt so với khởi động cổ điển", AI),
                                       ("35/35", "yêu cầu tiếng Việt LLM dịch đúng", Q), ("0", "vi phạm quy tắc cá nhân, 12 quý", GOLD)]):
        A(s, d.stat(s, 0.7 + i * 3.05, 4.7, 2.85, 1.4, big, lab, c, 26), "rise", gap=0.18)
    A(s, d.text(s, 0.7, 6.4, 11.5, 0.3, "Đội [Tên đội] · Mã đội [Madoi] · Prototype: " + URL, 12, MUTED), "fade")

    # 2 ── the hook
    lot = facts["lot"]
    s = d.slide("01 · Vấn đề", "20 triệu đồng có mua nổi “một rổ VN30”?", transition="push", notes=(
        f"Sàn HOSE khớp lệnh theo lô 100 cổ phiếu. Với 20 triệu đồng, một lô {lot['max_ticker']} đã bằng {lot['max']:.0f}% tài khoản; "
        f"{lot['over10']} trên 30 mã có một lô vượt 10% tài khoản. Bộ tối ưu nói 'giữ 3,4% VIC', tài khoản chỉ có thể giữ 0% "
        "hoặc trọn một lô. Mua lô nào, bỏ lô nào là một bài toán tổ hợp nhị phân: 2 mũ n lựa chọn."))
    A(s, d.image(s, FIG / "01_lot_cost.png", 0.5, 1.75, 8.6, 4.5), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 6.35, 8.6, f"Hình 1. Giá một lô (100 cổ phiếu) của 30 mã VN30 theo % tài khoản 20 triệu, ngày {lot['date']} (thang log)."), "fade")
    A(s, d.stat(s, 9.45, 1.85, 3.3, 1.45, f"{lot['max']:.0f}%".replace(".", ","), f"một lô {lot['max_ticker']} so với tài khoản 20 triệu", DOWN, 40), "rise")
    A(s, d.stat(s, 9.45, 3.45, 3.3, 1.45, f"{lot['over10']}/30", "mã có một lô vượt 10% tài khoản", AMBER, 40), "rise")
    A(s, B(s, 9.45, 5.05, 3.3, 1.2, runs=[[("Mỗi mã: mua thêm một lô hay không?", {"size": 14, "bold": True})],
                                         [("→ 2ⁿ tổ hợp: bài toán tối ưu nhị phân", {"size": 13, "color": Q})]]), "rise")

    # 3 ── who / alternatives
    s = d.slide("01 · Vấn đề", "14,3 triệu tài khoản, nhưng chưa có cách nào trọn vẹn", transition="fade", notes=(
        "Cuối tháng 10/2026 Việt Nam có hơn 14,3 triệu tài khoản chứng khoán cá nhân trong nước, phần lớn là tài khoản nhỏ. "
        "Họ có ba lựa chọn: ETF thì không cho bỏ một mã hay giới hạn ngành; làm tròn lô thì để tiền nằm im; lô lẻ thì sổ lệnh "
        "mỏng, khó khớp. AGQO là lựa chọn duy nhất vừa cá nhân hoá, vừa chỉ dùng lệnh lô chẵn, vừa bám chỉ số tốt."))
    rows = [("Lựa chọn", "Quy tắc riêng", "Chỉ lệnh lô chẵn", "Sai số bám (20tr)", "Hạn chế"),
            ("ETF VN30", "✗", "✓", "—", "không bỏ được mã, không giới hạn ngành"),
            ("Làm tròn lô gần nhất", "✓", "✓", "12,1%", "phần lớn tiền nằm im"),
            ("Lô lẻ (1–99 cp)", "✓", "✗", "thấp", "sổ lệnh riêng, mỏng; rủi ro khớp lệnh"),
            ("AGQO", "✓", "✓", "6,8%", "cần quy trình tối ưu (đã tự động hoá)")]
    tbl = s.shapes.add_table(len(rows), 5, Inches(0.6), Inches(1.95), Inches(12.1), Inches(3.6))
    t = tbl.table
    for j, wd in enumerate([2.8, 1.7, 1.9, 2.0, 3.7]):
        t.columns[j].width = Inches(wd)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = rgb("16233B" if i == 0 else ("0F2A22" if r[0] == "AGQO" else PANEL))
            c.text = ""
            p = c.text_frame.paragraphs[0]
            run = p.add_run()
            run.text = v
            col = INK
            if v == "✓":
                col = UP
            elif v == "✗":
                col = DOWN
            elif i == 0:
                col = MUTED
            elif r[0] == "AGQO" and j in (0, 3):
                col = UP
            run.font.size, run.font.name, run.font.color.rgb = Pt(15 if i else 12), FONT, rgb(col)
            run.font.bold = i == 0 or r[0] == "AGQO" or v in "✓✗"
            p.alignment = PP_ALIGN.CENTER if j in (1, 2, 3) else PP_ALIGN.LEFT
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
    A(s, tbl, "wipe", dur=1.0)
    A(s, d.text(s, 0.6, 5.85, 12.1, 0.8, "", runs=[[("Người dùng: ", {"bold": True, "color": GOLD}),
        ("nhà đầu tư cá nhân vốn nhỏ muốn “VN30 theo cách của mình”, và công ty chứng khoán muốn cung cấp danh mục chỉ số cá nhân hoá "
         "(direct indexing) cho khách hàng nhỏ.", {})]], size=16), "fade")
    A(s, d.text(s, 0.6, 6.55, 12.1, 0.4, "Nguồn: VSDC (14,3 triệu tài khoản cá nhân trong nước, cuối 10/2026); HOSE cho giao dịch lô lẻ từ 12/09/2022.", 10, MUTED, italic=True), "fade")

    # 4 ── architecture
    s = d.slide("02 · Giải pháp", "AI đọc · lượng tử lấy mẫu · cổ điển kiểm chứng", transition="push", notes=(
        "Đây là toàn bộ kiến trúc. Màu xanh dương là AI: thống kê đọc thị trường, LLM Qwen3.8 dịch yêu cầu tiếng Việt, "
        "mô hình k-NN chọn cấu hình mạch. Màu tím là lượng tử: mạch QAOA 16 qubit lấy 512 mẫu. Màu xanh lá là cổ điển: "
        "kiểm tra tiền, phí, thuế, trần và liệt kê đủ 65.536 tổ hợp. Nguyên tắc: không đầu ra nào của AI đi tới lệnh mà chưa được kiểm tra."))
    A(s, d.image(s, FIG / "02_pipeline.png", 0.5, 1.7, 12.3, 5.0), "zoom", dur=0.9)
    A(s, d.caption(s, 0.6, 6.62, 12.1, "Hình 2. Kiến trúc AGQO. Mọi ràng buộc của LLM được mã nguồn kiểm tra; mọi mẫu lượng tử được kiểm tra chính xác trước khi thành lệnh."), "fade")

    # 5 ── contributions
    s = d.slide("02 · Giải pháp", "Bốn đóng góp mới, mỗi đóng góp có kiểm định", transition="fade", notes=(
        "Bốn đóng góp. Một: thanh ghi qubit an toàn trần, mọi trạng thái đều tuân thủ quy tắc nên Hamiltonian đúng bằng mục tiêu tài chính. "
        "Hai: mạch QAOA được thiết kế từ đặc trưng dữ liệu, năm quy tắc từ tài liệu khoa học. Ba: LLM là trình biên dịch chứ không phải "
        "nhà tiên tri: nó không bao giờ đưa ra tỷ trọng. Bốn: đánh giá có thể kiểm toán: liệt kê chính xác làm trọng tài, kiểm định cặp trên 12 quý chưa thấy."))
    cards = [("1", "Thanh ghi qubit an toàn trần", "Quy tắc của nhà đầu tư quyết định mã nào có qubit, nên cả 2¹⁶ trạng thái đều hợp lệ. Hamiltonian = đúng mục tiêu bám chỉ số.", Q),
             ("2", "Mạch QAOA do dữ liệu thiết kế", "5 quy tắc (khởi động ấm, bộ trộn căn chỉnh, tỉa tương tác, thang RMS, dốc tuyến tính) bật theo thống kê của từng quý.", AI),
             ("3", "LLM là trình biên dịch, không phải nhà tiên tri", "Qwen3.8 dịch tiếng Việt thành ràng buộc JSON được kiểm tra; giải thích được đối chiếu từng con số. Không bao giờ tạo tỷ trọng hay lệnh.", CL),
             ("4", "Đánh giá kiểm toán được", "Liệt kê chính xác 65.536 tổ hợp làm trọng tài; 9 mốc so sánh mạch; kiểm định cặp trên 12 quý chưa thấy; báo cáo cả kết quả âm.", GOLD)]
    for i, (n, ttl, body, c) in enumerate(cards):
        x, y = 0.6 + (i % 2) * 6.15, 1.85 + (i // 2) * 2.45
        A(s, B(s, x, y, 5.95, 2.2, fill=PANEL, line=LINE), "rise", gap=0.25)
        A(s, B(s, x + 0.3, y + 0.35, 0.75, 0.75, n, 26, BG, bold=True, fill=c, line=None, shape=MSO_SHAPE.OVAL, align=PP_ALIGN.CENTER), "zoom", gap=0.1)
        A(s, d.text(s, x + 1.3, y + 0.3, 4.4, 1.8, "", runs=[[(ttl, {"size": 18, "bold": True, "color": c})], [(body, {"size": 14, "color": "C7D2E4"})]], spacing=6), "fade", gap=0.1)

    # 6 ── market insight
    mk = facts["market"]
    s = d.slide("03 · AI đọc thị trường", "VN30 không phải 30 cược độc lập: chỉ khoảng 13", transition="push", notes=(
        f"Bước 1a: AI thống kê đọc thị trường mỗi quý. Trung bình VN30 chỉ tương đương {mk['bets']:.0f} cược độc lập, và một nhân tố thị trường "
        f"chung giải thích khoảng {mk['factor']:.0f}% phương sai. Ý nghĩa tài chính: khoảng 20 mã chọn khéo là đủ bám chỉ số. Ý nghĩa lượng tử: "
        "các mã cùng cụm thay thế được nhau, nên quyết định mua lô của chúng phụ thuộc nhau, đó chính là các tương tác ZZ giữa qubit."))
    A(s, d.image(s, FIG / "03_market.png", 0.5, 1.75, 8.2, 4.4), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 6.2, 8.2, "Hình 3. Số cược độc lập (Meucci 2009) và tỷ trọng phương sai của nhân tố thị trường, 12 quý kiểm định."), "fade")
    A(s, d.stat(s, 9.0, 1.85, 3.75, 1.35, f"≈ {mk['bets']:.0f}".replace(".", ","), "cược độc lập thực sự trong ~30 mã", AI, 38), "rise")
    A(s, d.stat(s, 9.0, 3.35, 3.75, 1.35, f"≈ {mk['factor']:.0f}%", "phương sai do một nhân tố thị trường", GOLD, 38), "rise")
    A(s, B(s, 9.0, 4.85, 3.75, 1.4, runs=[[("Tài chính: ", {"bold": True, "color": UP}), ("~20 mã chọn khéo là đủ bám chỉ số.", {})],
                                         [("Lượng tử: ", {"bold": True, "color": Q}), ("mã cùng cụm → tương tác ZZ giữa qubit.", {})]], size=13), "rise")

    # 7 ── LLM compiler
    s = d.slide("03 · AI hiểu nhà đầu tư", "LLM dịch tiếng Việt thành ràng buộc kiểm tra được", transition="fade", notes=(
        "Bước 1b: nhà đầu tư nói tiếng Việt tự nhiên. Qwen3.8-27B, mô hình mã nguồn mở chạy bằng vLLM trên một GPU H100, chỉ được phép trả lời "
        "theo một lược đồ JSON cố định, và mã nguồn kiểm tra từng trường. Trên 35 câu thử, LLM đúng 35/35, quy tắc từ khoá chỉ 68,6%. "
        "Khi câu nói mơ hồ như 'tôi muốn ít rủi ro hơn', LLM không đoán mà hỏi lại."))
    live = live_example or {}
    A(s, B(s, 0.6, 1.85, 5.6, 1.25, runs=[[("Nhà đầu tư nói:", {"size": 12, "color": MUTED})],
          [("“" + live.get("text", "Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này") + "”", {"size": 16, "bold": True})]],
          fill="16233B", line=AI), "rise")
    A(s, d.text(s, 0.6, 3.2, 5.6, 0.4, "↓  Qwen3.8-27B · vLLM · H100 · đầu ra JSON theo lược đồ", 13, AI, bold=True), "fade")
    rows_kw = live.get("keyword", "giữ 10% tiền mặt (bỏ sót “không muốn giữ cổ phiếu ngân hàng”)")
    rows_llm = live.get("llm", "loại ngành Ngân hàng · tiền mặt ≥ 10%")
    A(s, B(s, 0.6, 3.7, 5.6, 1.05, runs=[[("Quy tắc từ khoá: ", {"bold": True, "color": DOWN}), (rows_kw, {})]], size=14), "rise")
    A(s, B(s, 0.6, 4.9, 5.6, 1.05, runs=[[("Qwen3.8: ", {"bold": True, "color": UP}), (rows_llm, {})]], size=14, line=UP), "rise")
    A(s, d.text(s, 0.6, 6.1, 5.6, 0.8, "Câu mơ hồ (“Tôi muốn ít rủi ro hơn”) → LLM hỏi lại thay vì đoán: “Bạn muốn giảm rủi ro bằng cách nào? …”", 12, MUTED, italic=True), "fade")
    A(s, d.stat(s, 6.6, 1.85, 3.0, 1.6, "35/35", "câu thử dịch đúng (Qwen3.8)", UP, 44), "zoom")
    A(s, d.stat(s, 9.75, 1.85, 3.0, 1.6, "68,6%", "quy tắc từ khoá", DOWN, 44), "zoom")
    A(s, B(s, 6.6, 3.65, 6.15, 2.6, runs=[[("Vì sao tin được LLM?", {"size": 16, "bold": True, "color": GOLD})],
          [("• Chỉ trả lời theo lược đồ JSON (giải mã có ràng buộc).", {})], [("• Mã nguồn kiểm tra mã, ngành, trần, số mã, tiền mặt.", {})],
          [("• Nhiệt độ 0, nhật ký đầy đủ, phát lại không cần GPU.", {})], [("• LLM không bao giờ tạo ra tỷ trọng hay lệnh.", {})]], size=14), "rise")

    # 8 ── finance to qubits
    s = d.slide("04 · Tài chính → qubit", "Hamiltonian chính là mục tiêu bám chỉ số", transition="push", notes=(
        "Đây là cầu nối tài chính và lượng tử. Mỗi qubit trả lời một câu hỏi: có mua thêm một lô mã này không. Năng lượng E của một chuỗi bit "
        "là sai số bám bình phương, cộng chi phí vòng quay, cộng phạt ngân sách. Các trần của nhà đầu tư được xử lý ngay khi chọn mã nào có qubit, "
        "nên mọi trạng thái đều hợp lệ và Hamiltonian đúng bằng mục tiêu tài chính. Bản đồ nhiệt bên dưới là ma trận tương tác thật của quý 10/2026."))
    A(s, d.image(s, ROOT / "docs" / "figures_vi" / "eq_dark.png", 0.6, 1.7, 12.1, 1.35), "zoom")
    A(s, d.image(s, FIG / "04_hamiltonian.png", 0.5, 3.1, 8.3, 3.45), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 6.55, 8.3, "Hình 4. Tương tác J (trái) và trường h (phải) của 16 qubit, tài khoản mới 20 triệu, 01/10/2026."), "fade")
    for i, (ttl, body, c) in enumerate([("1 qubit = 1 câu hỏi", "“Mua thêm 1 lô mã k?” → x_k ∈ {0, 1}", Q),
                                        ("Tương tác J", "hai mã cùng biến động: mua cả hai là thừa", DOWN),
                                        ("Thanh ghi an toàn trần", "mọi 2¹⁶ trạng thái tuân thủ quy tắc", UP)]):
        A(s, B(s, 9.1, 3.2 + i * 1.12, 3.65, 1.0, runs=[[(ttl, {"bold": True, "color": c, "size": 15})], [(body, {"size": 12.5, "color": "C7D2E4"})]]), "rise")

    # 9 ── circuit
    cr = facts["circuit"]["row"]
    s = d.slide("04 · Mạch lượng tử", "Mạch QAOA được dữ liệu “viết” ra", transition="fade", notes=(
        "Mạch không phải mạch sách giáo khoa. Năm quy tắc từ tài liệu khoa học, mỗi quy tắc đọc một thống kê của bài toán: R1 khởi động ấm từ "
        "nghiệm nới lỏng liên tục; R2 bộ trộn có trạng thái riêng chính là trạng thái khởi đầu; R3 chỉ giữ các tương tác mạnh; R4 chia Hamiltonian "
        f"cho căn bình phương trung bình hệ số để góc dùng lại được giữa các quý; R5 góc dốc tuyến tính như tôi luyện đoạn nhiệt. Quý gần nhất dùng p = {int(cr['layers'])} lớp."))
    A(s, d.image(s, FIG / "05_circuit.png", 0.5, 1.7, 12.3, 4.0), "wipe", dur=1.2)
    A(s, d.caption(s, 0.5, 5.7, 12.3, "Hình 5. Một lớp QAOA của AGQO (4 trên 16 qubit) và lịch góc γ, β của quý 10/2026."), "fade")
    for i, (r, txt, src) in enumerate([("R1", "Khởi động ấm", "Egger 2021"), ("R2", "Bộ trộn căn chỉnh", "He 2023"), ("R3", "Tỉa tương tác", "khối lượng J²"),
                                       ("R4", "Thang RMS", "Sureshbabu 2024"), ("R5", "Dốc tuyến tính", "LR-QAOA 2025")]):
        A(s, B(s, 0.6 + i * 2.45, 6.15, 2.3, 0.75, runs=[[(r + "  ", {"bold": True, "color": Q, "size": 16}), (txt, {"bold": True, "size": 13})],
                                                       [(src, {"size": 10.5, "color": MUTED})]], align=PP_ALIGN.CENTER), "rise", gap=0.15)

    # 10 ── AI guidance
    sc = facts["schedules"]
    s = d.slide("05 · AI dẫn dắt mạch", "AI chọn cấu hình mạch từ " + f"{sc['n']:,}".replace(",", ".") + " ứng viên", transition="push", notes=(
        f"Bước 2b: mỗi lịch mạch gồm số lớp p, độ kẹp ε, khối lượng tương tác giữ lại, độ dốc của γ và β. Chúng em chấm điểm {sc['n']} lịch trên 48 "
        f"bài toán huấn luyện năm 2023. Lịch trung vị chỉ đạt {sc['median']:.1f}% lượt đo tốt; lịch tốt nhất đạt {sc['best']:.1f}%. Mô hình k-NN đọc 5 "
        "đặc trưng của bài toán mới và chọn lịch tốt nhất trên 10 bài toán giống nhất. Mô hình không bao giờ nhìn dữ liệu kiểm định 2024–2026."))
    A(s, d.image(s, FIG / "06_schedules.png", 0.5, 1.75, 8.3, 3.7), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 5.4, 8.3, f"Hình 6. Chất lượng của {sc['in_budget']} lịch mạch trong ngân sách cổng, chấm trên 48 bài toán năm 2023."), "fade")
    A(s, d.stat(s, 9.1, 1.8, 3.65, 1.15, f"{sc['median']:.1f}%".replace(".", ","), "lượt đo tốt của lịch trung vị", MUTED, 30), "rise")
    A(s, d.stat(s, 9.1, 3.05, 3.65, 1.15, f"{sc['best']:.1f}%".replace(".", ","), f"lịch tốt nhất: gấp {sc['best'] / sc['median']:.1f} lần trung vị".replace(".", ","), GOLD, 30), "rise")
    A(s, d.stat(s, 9.1, 4.3, 3.65, 1.15, "k = 10", "láng giềng gần nhất quyết định lịch", AI, 30), "rise")
    A(s, B(s, 0.6, 5.95, 12.15, 0.85, runs=[[("Học trên 2023, kiểm định trên 2024–2026. ", {"bold": True, "color": GOLD}),
        ("5 đặc trưng: độ tự tin khởi động ấm · tỷ lệ qubit đã rõ · trường/tương tác · độ tập trung tương tác · cỡ lô. "
         "k = 10 chọn bằng kiểm định chéo theo tháng.", {})]], size=13.5), "rise")

    # 11 ── quantum result
    a, b, c = st["agqo vs warm_start_only"], st["agqo vs textbook"], st["agqo vs random"]
    s = d.slide("06 · Kết quả lượng tử", "Xác suất dồn về nghiệm tốt: thắng cả 12/12 quý", transition="fade", notes=(
        f"Kết quả lượng tử trên 12 quý chưa từng thấy. Mạch AGQO đưa {facts['prob']['agqo_good']:.0f}% lượt đo vào vùng trong 5% của tối ưu, so với "
        f"{facts['prob']['rand_good']:.1f}% nếu đoán ngẫu nhiên. So với trạng thái khởi động cổ điển, tỷ lệ trúng nghiệm gần tối ưu gấp {a['ratio']:.1f} lần, "
        f"so với QAOA sách giáo khoa gấp {b['ratio']:.0f} lần, so với tìm kiếm ngẫu nhiên thiết kế mạch gấp {c['ratio']:.1f} lần. Thắng 12/12 quý, Wilcoxon p = 0,0005."))
    for i, (x, lab, col) in enumerate([(a, "so với khởi động ấm cổ điển", UP), (b, "so với QAOA sách giáo khoa", AI), (c, "so với tìm kiếm ngẫu nhiên", Q)]):
        A(s, d.stat(s, 0.6 + i * 4.1, 1.8, 3.9, 1.35, f"{x['ratio']:.1f}×".replace(".", ","), f"{lab} · {x['wins']}/12 quý · p = 0,0005", col, 38), "zoom", gap=0.25)
    A(s, d.image(s, FIG / "07_probability.png", 0.5, 3.3, 12.3, 3.2), "wipe", dur=1.2)
    A(s, d.caption(s, 0.5, 6.5, 12.3, "Hình 7. Phân bố xác suất đo trên 65.536 tổ hợp lô theo khoảng cách tới tối ưu chính xác, trung bình 12 quý kiểm định."), "fade")

    # 12 ── one decision
    dc = facts["decision"]
    s = d.slide("07 · Kết quả tài chính", "Một quyết định thật: tài khoản mới 20 triệu", transition="push", notes=(
        f"Một quyết định thật ngày {dc['date']}. Màu xám là tỷ trọng lý tưởng nếu mua được cổ phiếu lẻ. Làm tròn lô gần nhất làm tròn gần như tất cả "
        f"về 0 và để {dc['cash_naive']:.0f}% tiền nằm im, sai số bám {dc['te']['practitioner']:.1f}%. Thuật toán tham lam thêm từng lô nhưng dồn 36% vào một mã, "
        f"{dc['te']['greedy']:.1f}%. AGQO chọn tổ hợp lô bám tốt nhất, {dc['te']['agqo']:.1f}%, chính là tối ưu chính xác của thanh ghi 16 qubit."))
    A(s, d.image(s, FIG / "10_one_decision.png", 0.5, 1.75, 8.9, 4.4), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 6.2, 8.9, f"Hình 8. Tỷ trọng 16 vị thế lớn nhất theo bốn cách, {dc['date']}; dưới mỗi mã là giá một lô theo % tài khoản."), "fade")
    for i, (big, lab, col) in enumerate([(f"{dc['te']['practitioner']:.1f}%", f"làm tròn: {dc['cash_naive']:.0f}% tiền nằm im", DOWN),
                                         (f"{dc['te']['greedy']:.1f}%", "tham lam: dồn 36% vào một mã", AMBER),
                                         (f"{dc['te']['agqo']:.1f}%", "AGQO = tối ưu chính xác", AI)]):
        A(s, d.stat(s, 9.7, 1.85 + i * 1.5, 3.05, 1.3, big.replace(".", ","), "sai số bám dự kiến · " + lab, col, 32), "rise")

    # 13 ── accounts over 12 quarters
    s = d.slide("07 · Kết quả tài chính", "Qua 12 quý: tài khoản nhỏ hưởng lợi nhiều nhất", transition="fade", notes=(
        "Chạy thật qua 12 quý, 711 phiên. Với 20 triệu, sai số bám giảm từ 12,1% xuống 6,8%, khoảng tin cậy 95% của mức giảm từ 3,8 đến 6,9 điểm "
        "phần trăm. Thuật toán tham lam là đối thủ mạnh, 7,5%; AGQO vẫn tốt hơn vì tối ưu chính xác cả tổ hợp. Với 100 triệu, lô đã đủ nhỏ so với "
        "tài khoản nên ba cách gần như bằng nhau: AGQO phát huy đúng nơi cần, tài khoản nhỏ."))
    A(s, d.image(s, FIG / "09_accounts.png", 0.5, 1.75, 7.2, 4.4), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 6.2, 7.2, "Hình 9. Sai số bám VN30 thực tế (năm hoá), 01/2024–11/2026, theo cỡ tài khoản."), "fade")
    A(s, d.stat(s, 8.0, 1.85, 4.75, 1.4, "12,1% → 6,8%", "sai số bám, tài khoản 20 triệu · KTC 95% của mức giảm: 3,8–6,9 điểm %", UP, 34), "zoom")
    A(s, B(s, 8.0, 3.45, 4.75, 2.75, runs=[[("Đọc biểu đồ thế nào?", {"bold": True, "color": GOLD, "size": 15})],
          [("• Sai số bám = độ lệch hằng năm so với VN30: càng thấp càng giống chỉ số.", {})],
          [("• Tham lam (7,5%) là đối thủ mạnh; AGQO tốt hơn vì xét cả tổ hợp lô cùng lúc.", {})],
          [("• 100 triệu: lô đã nhỏ so với vốn, ba cách gần như bằng nhau.", {})]], size=13.5), "rise")

    # 14 ── mandates
    s = d.slide("07 · Kết quả tài chính", "Quy tắc cá nhân: 0 vi phạm, chi phí được đo", transition="push", notes=(
        "Ba yêu cầu thật do LLM dịch được chạy qua 12 quý: 0 vi phạm. Quan trọng hơn, AGQO cho nhà đầu tư biết giá của quy tắc: ví dụ bỏ bất động "
        "sản và giới hạn ngân hàng 30% làm sai số bám tăng thêm 3,8 điểm phần trăm. Đây là thông tin một ETF không thể cung cấp."))
    A(s, d.image(s, FIG / "11_mandates.png", 0.5, 1.8, 12.3, 4.0), "wipe", dur=1.0)
    A(s, d.caption(s, 0.5, 5.8, 12.3, "Hình 10. Sai số bám và chi phí của từng quy tắc (so với không có quy tắc), tài khoản 100 triệu, 12 quý."), "fade")
    A(s, B(s, 0.6, 6.25, 12.15, 0.65, runs=[[("Giá trị cho nhà đầu tư: ", {"bold": True, "color": GOLD}),
        ("biết trước “quy tắc của tôi tốn bao nhiêu độ bám chỉ số”, và chắc chắn quy tắc không bao giờ bị vi phạm.", {})]], size=14), "rise")

    # 15 ── explainer
    ex = json.loads((RUN / "llm" / "explanations.json").read_text())
    quote = ex["rows"][-1]["explanation"]["summary_vi"]
    sents = quote.replace("\n", " ").split(". ")
    q, out_ = "", []
    for x in sents:
        if len(q) + len(x) > 360:
            break
        out_.append(x)
        q = ". ".join(out_)
    quote = q.rstrip(".") + "."
    s = d.slide("08 · AI giải thích", "Lời giải thích tiếng Việt: từng con số được đối chiếu", transition="fade", notes=(
        "Sau khi quyết định, Qwen3.8 viết giải thích tiếng Việt từ một bảng bằng chứng do mã nguồn tạo ra. Mỗi con số trong lời giải thích được đối chiếu "
        "tự động với bằng chứng, mỗi lệnh được so khớp, và từ phiên bản này chúng em kiểm tra cả ý nghĩa: con số sai số bám phải đi kèm 'so với chỉ số VN30'. "
        "Kết quả: 12/12 lời giải thích đúng mọi con số, 11/12 đúng cả ý nghĩa."))
    A(s, B(s, 0.6, 1.85, 6.0, 2.6, runs=[[("Qwen3.8 viết (quý 10/2026):", {"size": 12, "color": MUTED})], [("“" + quote + "”", {"size": 15, "italic": True})]],
          line=AI), "rise")
    A(s, d.text(s, 0.6, 4.6, 6.0, 0.6, "Mã nguồn đối chiếu tự động: mọi con số có trong bằng chứng? mọi lệnh khớp? mỗi con số đi kèm đúng ý nghĩa?", 12, MUTED, italic=True), "fade")
    A(s, d.image(s, FIG / "14_llm.png", 6.85, 1.85, 5.95, 3.3), "wipe")
    A(s, d.caption(s, 6.85, 5.15, 5.95, "Hình 11. Trái: dịch yêu cầu. Phải: kiểm tra số và ý nghĩa của 12 lời giải thích."), "fade")
    for i, (big, lab, col) in enumerate([("12/12", "đúng mọi con số", UP), ("11/12", "đúng cả ý nghĩa (lời nhắc cũ: 0/12)", AI), ("0", "lệnh bị mô tả sai", GOLD)]):
        A(s, d.stat(s, 0.6 + i * 4.1, 5.6, 3.9, 1.2, big, lab, col, 30), "zoom", gap=0.2)

    # 16 ── hardware + scaling
    sr = facts["scaling"]["ratio"]
    s = d.slide("09 · Phần cứng & mở rộng", "Sẵn sàng cho máy lượng tử thật", transition="push", notes=(
        "Trên mô phỏng nhiễu của IBM Heron 156 qubit, mạch sâu 6 lớp có hơn bốn nghìn cổng CZ và bị nhiễu xoá sạch. AI dẫn dắt theo nhiễu chọn mạch "
        "nông chỉ 16 cổng CZ, vẫn tốt hơn khởi động cổ điển 1,6 lần, 11/12 quý. Khi tăng từ 8 lên 20 qubit, lịch học năm 2023 dùng nguyên không chỉnh "
        f"vẫn thắng khởi động ấm từ {sr['8']}× lên {sr['20']}×: lợi thế tăng theo quy mô bài toán."))
    A(s, d.image(s, FIG / "12_hardware.png", 0.45, 1.75, 6.6, 3.6), "wipe")
    A(s, d.caption(s, 0.45, 5.35, 6.6, "Hình 12. Cổng hai qubit sau định tuyến và tỷ lệ trúng có nhiễu IBM Heron (FakeKingston)."), "fade")
    A(s, d.image(s, FIG / "13_scaling.png", 7.25, 1.75, 5.6, 3.6), "wipe")
    A(s, d.caption(s, 7.25, 5.35, 5.6, "Hình 13. Từ 8 đến 20 qubit: mạch AGQO so với khởi động ấm."), "fade")
    for i, (big, lab, col) in enumerate([("16 CZ", "mạch theo nhiễu do AI chọn", AI), ("1,6×", "hơn khởi động ấm khi có nhiễu, 11/12 quý", UP),
                                         (f"{sr['8']}× → {sr['20']}×".replace(".", ","), "lợi thế tăng theo số qubit", GOLD)]):
        A(s, d.stat(s, 0.6 + i * 4.1, 5.85, 3.9, 1.05, big, lab, col, 26), "zoom", gap=0.2)

    # 17 ── prototype
    s = d.slide("10 · Prototype", "Prototype chạy thật: 5 giây cho một quyết định", transition="fade", notes=(
        "Prototype là một ứng dụng web đã triển khai. Ban Giám khảo nhập số vốn và yêu cầu tiếng Việt; hệ thống chạy trực tiếp cả bảy bước: LLM đọc yêu cầu, "
        "thống kê thị trường, Hamiltonian, AI chọn mạch, QAOA lấy 512 mẫu, liệt kê chính xác và xuất lệnh, kèm tệp mạch OpenQASM chạy được trên IBM. "
        "Bây giờ chúng em xin demo trực tiếp."))
    A(s, d.image(s, SHOT / "00_hero.png", 0.6, 1.75, 6.0, 3.5, frame=True), "zoom")
    A(s, d.image(s, SHOT / "p5_circuit.png", 6.85, 1.75, 5.9, 2.35, frame=True), "zoom")
    A(s, d.image(s, SHOT / "p6_sampling.png", 6.85, 4.25, 5.9, 2.35, frame=True), "zoom")
    A(s, d.caption(s, 0.6, 5.35, 6.0, "Hình 14. Trang chính, mạch QAOA và kết quả lấy mẫu trong prototype."), "fade")
    A(s, B(s, 0.6, 5.85, 6.0, 1.0, runs=[[("▶ ", {"color": UP, "bold": True}), (URL, {"bold": True, "color": AI})],
                                        [("Mở link → nhập vốn và yêu cầu → “Chạy AGQO” (không cần tài khoản)", {"size": 12, "color": MUTED})]], size=15, line=UP), "rise")

    # 18 ── why trust it (honesty framed as strength)
    s = d.slide("11 · Vì sao tin được", "Mọi kết quả đều có trọng tài chính xác", transition="push", notes=(
        "Vì sao Ban Giám khảo có thể tin các con số này. Ở 16 qubit, máy tính cổ điển liệt kê hết 65.536 tổ hợp trong 0,12 giây. Chúng em không tuyên bố "
        "ưu thế lượng tử; chúng em dùng chính phép liệt kê đó làm trọng tài cho mọi kết quả. Huấn luyện chỉ năm 2023, kiểm định trên 12 quý chưa thấy, "
        "và chúng em báo cáo cả những gì chưa thắng, như lô lẻ hay tài khoản lớn. Khi bài toán vượt 60 qubit, liệt kê là không thể, và mạch đã sẵn sàng."))
    items = [("Trọng tài chính xác", "Liệt kê đủ 2¹⁶ tổ hợp trong 0,12 giây: mỗi kết quả lượng tử được chấm bằng đáp án đúng.", UP),
             ("Không rò rỉ dữ liệu", "Mọi lựa chọn (mạch, k, tinh chỉnh) học trên 2023; kiểm định 2024–2026 chưa từng thấy.", AI),
             ("Kiểm định cặp", "Wilcoxon và bootstrap khối 21 ngày; 9 mốc so sánh mạch; mốc tài chính mạnh (tham lam, lô lẻ, ETF).", Q),
             ("Nói rõ phạm vi", "Không tuyên bố ưu thế lượng tử ở 16 qubit; lợi ích tập trung ở tài khoản nhỏ; lô lẻ là phương án thay thế khi phí thấp.", GOLD)]
    for i, (ttl, body, col) in enumerate(items):
        x, y = 0.6 + (i % 2) * 6.15, 1.95 + (i // 2) * 1.95
        A(s, B(s, x, y, 5.95, 1.7, runs=[[(ttl, {"bold": True, "color": col, "size": 19})], [(body, {"size": 15, "color": "C7D2E4"})]]), "rise", gap=0.25)
    A(s, B(s, 0.6, 5.95, 12.15, 0.9, runs=[[("Khi bài toán lớn lên ", {"bold": True, "color": GOLD}),
        ("(30 mã × 2 lô = 60 qubit, 10¹⁸ tổ hợp), liệt kê là không thể. Mạch, mô hình chọn lịch và đường xuất OpenQASM đã sẵn sàng cho phần cứng.", {})]], size=14), "rise")

    # 19 ── deployment
    s = d.slide("12 · Triển khai", "Từ prototype đến sản phẩm của công ty chứng khoán", transition="fade", notes=(
        "Triển khai: AGQO phù hợp làm tính năng 'VN30 theo cách của bạn' trong ứng dụng của công ty chứng khoán. Chi phí: phần tối ưu chạy trên CPU vài giây "
        "mỗi quyết định; LLM mã nguồn mở tự vận hành, khoảng 1–2 USD cho một lô yêu cầu, dữ liệu khách hàng không rời hạ tầng. Lộ trình: tích hợp API đặt lệnh, "
        "chạy thử trên phần cứng IBM, mở rộng thanh ghi nhiều lô."))
    steps = [("Q1/2027", "Thí điểm", "API nội bộ với một công ty chứng khoán; tài khoản thử nghiệm; kiểm tra lệnh lô chẵn thực tế.", AI),
             ("Q2/2027", "Phần cứng thật", "Chạy mạch theo nhiễu trên IBM Heron (tệp OpenQASM đã sẵn); so sánh với mô phỏng.", Q),
             ("Q3/2027", "Mở rộng", "Thanh ghi nhiều lô (≥ 60 qubit), thêm VN100; kết hợp lô chẵn + lô lẻ khi phí thấp.", CL),
             ("Q4/2027", "Sản phẩm", "Tính năng “VN30 của tôi” trong app môi giới; báo cáo giải thích tiếng Việt hằng quý.", GOLD)]
    for i, (when, ttl, body, col) in enumerate(steps):
        x = 0.6 + i * 3.08
        A(s, B(s, x, 1.95, 2.9, 0.55, when, 15, BG, bold=True, fill=col, line=None, align=PP_ALIGN.CENTER), "wipe", gap=0.3)
        A(s, B(s, x, 2.6, 2.9, 2.2, runs=[[(ttl, {"bold": True, "size": 18, "color": col})], [(body, {"size": 14, "color": "C7D2E4"})]]), "rise", gap=0.1)
    for i, (big, lab, col) in enumerate([("~2 giây", "CPU cho một quyết định (16 qubit)", UP), ("1–2 USD", "một lô yêu cầu LLM trên 1 GPU H100", AI),
                                         ("100%", "dữ liệu khách hàng ở lại hạ tầng (LLM mở)", GOLD)]):
        A(s, d.stat(s, 0.6 + i * 4.1, 5.25, 3.9, 1.35, big, lab, col, 30), "zoom", gap=0.2)

    # 20 ── closing
    s = d.slide(None, None, transition="fade", notes=(
        "Tóm lại: AGQO biến một yêu cầu tiếng Việt thành một danh mục lô chẵn bám VN30, có kiểm chứng. Tài khoản 20 triệu giảm sai số bám từ 12,1% xuống 6,8%; "
        "mạch lượng tử do dữ liệu thiết kế tốt hơn 6,9 lần khởi động cổ điển; 0 vi phạm quy tắc. Chúng em xin cảm ơn và sẵn sàng nhận câu hỏi."))
    A(s, d.text(s, 0.8, 1.2, 11.7, 1.2, "", runs=[[("Tài khoản nhỏ. ", {"size": 46, "bold": True}), ("Kỷ luật lớn.", {"size": 46, "bold": True, "color": GOLD})]]), "rise")
    A(s, d.text(s, 0.8, 2.45, 11.7, 0.8, "AGQO biến một câu nói tiếng Việt thành danh mục lô chẵn bám VN30, có kiểm chứng.", 20, "C7D2E4"), "fade")
    for i, (big, lab, col) in enumerate([("12,1% → 6,8%", "sai số bám, tài khoản 20 triệu", UP), ("6,9×", "mạch AGQO so với khởi động cổ điển", AI),
                                         ("0", "vi phạm quy tắc cá nhân", GOLD)]):
        A(s, d.stat(s, 0.8 + i * 4.0, 3.55, 3.8, 1.6, big, lab, col, 36), "zoom", gap=0.25)
    A(s, d.text(s, 0.8, 5.6, 11.7, 0.6, "Xin cảm ơn Ban Giám khảo!", 28, INK, bold=True), "fade")
    A(s, d.text(s, 0.8, 6.25, 11.7, 0.4, "Prototype: " + URL + "   ·   Đội [Tên đội] · Mã đội [Madoi]", 13, AI), "fade")

    d.finish()
    return OUT


if __name__ == "__main__":
    import sys

    live = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else None
    print(build(live))
