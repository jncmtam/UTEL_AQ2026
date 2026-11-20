"""Build the editable semifinal deck (native PowerPoint text, shapes and charts).

    python submission/deck/make_data.py          # chart data from saved runs (data/*.csv)
    python submission/deck/build_deck.py         # -> submission/drafts/<UTC time>/AGQO_BanKet_Slide.pptx

Edit points: words in story.yaml, numbers in data/*.csv (regenerate with make_data.py), colours and type sizes in
theme.json, layouts in the functions below (one function per slide). Every run writes a NEW draft folder, so a
deck edited by hand is never overwritten. See EDIT_MAP.md.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import pandas as pd
import yaml
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
SHOTS = ROOT / "docs" / "prototype_shots" / "v32"
TH = json.loads((HERE / "theme.json").read_text())
D, S, SEM = TH["dark"], TH["series"], TH["semantic"]
FONT = TH["font"]["deck"]
W, H = 13.333, 7.5
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h)


def vi(x: float, d: int = 2) -> str:
    """Vietnamese number: 1.234,56"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def pct(x: float, d: int = 2) -> str:
    return vi(x, d) + "%"


# ================================================================== facts from data
def facts() -> dict:
    lot = pd.read_csv(DATA / "c1_lot_cost.csv")
    opt = pd.read_csv(DATA / "c2_options.csv").set_index("option")
    kp = pd.read_csv(DATA / "c3_pitch_kpis.csv").set_index("method")
    src = json.loads((DATA / "SOURCES.json").read_text())
    tr = src["c3_pitch_trades"]
    acc = pd.read_csv(DATA / "c4_accounts.csv").set_index("capital_vnd")
    ci = pd.read_csv(DATA / "c4_accounts_ci.csv")
    pr = pd.read_csv(DATA / "c4_pitch_rules.csv").set_index("label").te_pct
    reg = pd.read_csv(DATA / "c5_register.csv").set_index("ticker")
    w = pd.read_csv(DATA / "c3_pitch_weights.csv")
    c6 = pd.read_csv(DATA / "c6_circuits.csv").set_index("arm2").success_pct
    rat = src["c6_circuits"]["ratios"]
    c20 = lambda comp: ci[(ci.capital_vnd == 20e6) & (ci.comparison == comp)].iloc[0]
    r, g = c20("agqo vs practitioner"), c20("agqo vs greedy")
    bank = next(c for c in tr["checks"] if c["kind"] == "sector_cap")["value_pct"]
    nav = 20e6
    round_inv = kp.loc["Nearest-lot rounding", "invested_pct"]
    ideal_ssi = w[(w.method == "Ideal (fractional shares)") & (w.ticker == "SSI")].weight_pct.iloc[0]
    ideal_fpt = w[(w.method == "Ideal (fractional shares)") & (w.ticker == "FPT")].weight_pct.iloc[0]
    return {
        "vic_pct": vi(lot.set_index("ticker").lot_pct_of_20m["VIC"], 0),
        "n_over10": int((lot.lot_pct_of_20m > 10).sum()),
        "etf_te_d": pct(opt.iloc[0].te_daily_pct), "etf_te_w": pct(opt.iloc[0].te_weekly_pct),
        "odd_te": pct(opt.iloc[1].te_daily_pct), "agqo_none": pct(pr["none|agqo"]), "agqo_rules": pct(pr["rules|agqo"]),
        "greedy_est": pct(kp.loc["Greedy lot filling", "estimated_te_pct"]),
        "round_est": pct(kp.loc["Nearest-lot rounding", "estimated_te_pct"]), "agqo_est": pct(kp.loc["AGQO", "estimated_te_pct"]),
        "round_holdings": int(kp.loc["Nearest-lot rounding", "holdings"]), "agqo_holdings": int(kp.loc["AGQO", "holdings"]),
        "round_cash": pct(100 - round_inv, 0), "agqo_cash_m": vi(tr["cash_after_fees_vnd"] / 1e6, 1),
        "agqo_cash_vnd": vi(tr["cash_after_fees_vnd"], 0), "fees_vnd": vi(tr["fees_vnd"], 0), "bank_pct": pct(bank),
        "d20_round": vi(-r.diff_pp, 2), "d20_round_ci": f"{vi(-r.ci_high, 2)}; {vi(-r.ci_low, 2)}",
        "d20_greedy": vi(g.diff_pp, 2), "d20_greedy_ci": f"{vi(g.ci_low, 2)}; +{vi(g.ci_high, 2)}",
        "r_round": pct(pr["rules|practitioner"]), "r_greedy": pct(pr["rules|greedy"]), "r_agqo": pct(pr["rules|agqo"]),
        "fpt_ideal": pct(ideal_fpt, 1), "fpt_lot": pct(lot.set_index("ticker").lot_pct_of_20m["FPT"], 1),
        "ssi_lots": vi(reg.loc["SSI", "continuous_lots"], 2), "ssi_fixed": int(reg.loc["SSI", "fixed_lots"]),
        "ssi_lot": pct(reg.loc["SSI", "lot_pct"], 1), "ssi_ideal": pct(ideal_ssi, 1),
        "ratio_warm": vi(rat["agqo vs warm_start_only"], 1), "ratio_textbook": vi(rat["agqo vs textbook"], 0),
        "frozen": pct(c6["frozen"], 1), "nopolish": pct(c6["polish_ablation"], 1), "agqo_q": pct(c6["agqo"], 1),
        "textbook": pct(c6["textbook"], 1), "warm": pct(c6["warm_start_only"], 1),
        "_acc": acc, "_lot": lot, "_w": w, "_kp": kp, "_c6": c6, "_tr": tr, "_pr": pr,
    }


def fill(text, F) -> str:
    """Replace {fact_name} by its value; other braces (e.g. "x ∈ {0, 1}") stay as written."""
    import re

    return re.sub(r"\{([a-z][a-z0-9_]*)\}", lambda m: str(F[m.group(1)]) if m.group(1) in F else m.group(0), str(text))


# ================================================================== theme, master and layouts
def themed_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    master = prs.slide_master
    # theme colours and fonts (Design > Variants > Colors / Fonts in PowerPoint)
    tpart = master.part.part_related_by(RT.THEME)
    root = etree.fromstring(tpart.blob)
    ns = {"a": A}
    scheme = root.find(".//a:clrScheme", ns)
    scheme.set("name", "AGQO")
    colours = {"dk1": D["bg"], "lt1": D["text"], "dk2": D["panel"], "lt2": D["muted"], "accent1": S["agqo"],
               "accent2": S["greedy"], "accent3": S["rounding"], "accent4": SEM["pending"], "accent5": SEM["violation"],
               "accent6": SEM["constraint"], "hlink": S["agqo"], "folHlink": SEM["constraint"]}
    for tag, val in colours.items():
        el = scheme.find(f"a:{tag}", ns)
        for c in list(el):
            el.remove(c)
        etree.SubElement(el, qn("a:srgbClr")).set("val", val)
    fs = root.find(".//a:fontScheme", ns)
    fs.set("name", "AGQO Arial")
    for kind in ("majorFont", "minorFont"):
        fs.find(f"a:{kind}/a:latin", ns).set("typeface", FONT)
    tpart._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    # master background and title/body text styles
    master.background.fill.solid()
    master.background.fill.fore_color.rgb = rgb(D["bg"])
    tx = master._element.find(qn("p:txStyles"))
    for style, size, col, bold in (("p:titleStyle", 30, D["text"], True), ("p:bodyStyle", 18, D["text"], False),
                                   ("p:otherStyle", 16, D["text"], False)):
        lvl = tx.find(qn(style)).find(qn("a:lvl1pPr"))
        rpr = lvl.find(qn("a:defRPr"))
        rpr.set("sz", str(size * 100))
        rpr.set("b", "1" if bold else "0")
        for c in rpr.findall(qn("a:solidFill")):
            rpr.remove(c)
        sf = etree.SubElement(rpr, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", col)
        rpr.insert(0, sf)
    names = {0: "AGQO Title", 5: "AGQO Headline", 6: "AGQO Full bleed", 2: "AGQO Appendix divider"}
    for i, layout in enumerate(prs.slide_layouts):
        if i in names:
            layout._element.cSld.set("name", names[i])
    # headline placeholder geometry on the "AGQO Headline" layout
    lay = prs.slide_layouts[5]
    for ph in lay.placeholders:
        if ph.placeholder_format.type == 1 or ph.placeholder_format.idx == 0:
            ph.left, ph.top, ph.width, ph.height = Inches(0.55), Inches(0.35), Inches(12.2), Inches(1.0)
    return prs


# ================================================================== primitives
class Deck:
    def __init__(self, story: dict, F: dict):
        self.prs = themed_presentation()
        self.story, self.F = story, F
        self.n = 0
        self.clicks: dict[int, list] = {}

    def slide(self, headline: str, notes: dict | str, name: str, layout: int = 5):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[layout])
        self.n += 1
        self.clicks[id(s)] = []
        if s.shapes.title is not None:
            t = s.shapes.title
            t.name = f"{name} Headline"
            t.text = fill(headline, self.F)
            tf = t.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.TOP
            for p in tf.paragraphs:
                p.alignment = PP_ALIGN.LEFT
                for r in p.runs:
                    r.font.size, r.font.bold, r.font.name = Pt(28), True, FONT
                    r.font.color.rgb = rgb(D["text"])
        foot = self.text(s, 0.55, 7.08, 8, 0.28, self.story["meta"]["footer"], 10, D["muted"], name=f"{name} Footer")
        num = self.text(s, 12.2, 7.08, 0.6, 0.28, str(self.n), 10, D["muted"], align=PP_ALIGN.RIGHT, name=f"{name} Page")
        if isinstance(notes, dict):
            notes = "\n".join(f"{k}: {fill(v, self.F)}" for k, v in
                              (("Câu mở", notes["first"]), ("Nhìn vào", notes["cue"]), ("Ý chính", notes["takeaway"]),
                               ("Chuyển ý", notes["handoff"])))
        s.notes_slide.notes_text_frame.text = notes
        return s

    def text(self, s, x, y, w, h, text, size=16, color=None, bold=False, italic=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, name=None, runs=None, spacing=4):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        if name:
            tb.name = name
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paras = runs if runs is not None else [[(fill(text, self.F), {})]]
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = Pt(spacing)
            for t, o in para:
                r = p.add_run()
                r.text = fill(t, self.F)
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.italic = o.get("italic", italic)
                f.color.rgb = rgb(o.get("color", color or D["text"]))
        return tb

    def panel(self, s, x, y, w, h, name, fill_=None, line=None, text=None, size=15, color=None, bold=False,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, runs=None, lw=1.0):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.name = name
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = min(0.5, 0.10 / max(min(w, h), 0.01))
        if fill_:
            sh.fill.solid()
            sh.fill.fore_color.rgb = rgb(fill_)
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
        tf.margin_top = tf.margin_bottom = Inches(0.07)
        tf.vertical_anchor = anchor
        paras = runs if runs is not None else ([[(text, {})]] if text else [])
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = Pt(3)
            for t, o in para:
                r = p.add_run()
                r.text = fill(t, self.F)
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.italic = o.get("italic", False)
                f.color.rgb = rgb(o.get("color", color or D["text"]))
        return sh

    def arrow(self, s, x1, y1, x2, y2, name, color=None, w=1.5):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        c.name = name
        c.line.color.rgb = rgb(color or D["muted"])
        c.line.width = Pt(w)
        ln = c.line._get_or_add_ln()
        etree.SubElement(ln, qn("a:tailEnd")).set("type", "triangle")
        return c

    def picture(self, s, path, x, y, w=None, h=None, name=None):
        pic = s.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
        pic.name = name or path.stem
        pic.line.color.rgb = rgb(D["line"])
        return pic

    def click(self, s, *shapes):
        """One presenter click reveals these shapes together (final static state shows everything)."""
        self.clicks[id(s)].append(shapes)

    # ---------------------------------------------------------- charts
    def chart_style(self, chart, size=14, legend=False, gridlines=True, value_max=None, value_min=0, fmt='0"%"'):
        chart.font.size = Pt(size)
        chart.font.name = FONT
        chart.font.color.rgb = rgb(D["text"])
        chart.has_legend = legend
        if legend:
            chart.legend.position = XL_LEGEND_POSITION.TOP
            chart.legend.include_in_layout = False
            chart.legend.font.size = Pt(size)
            chart.legend.font.color.rgb = rgb(D["text"])
        va = chart.value_axis
        va.has_major_gridlines = gridlines
        if gridlines:
            va.major_gridlines.format.line.color.rgb = rgb(D["grid"])
        va.format.line.fill.background()
        va.tick_labels.font.size = Pt(size - 1)
        va.tick_labels.font.color.rgb = rgb(D["muted"])
        va.tick_labels.number_format = fmt
        va.tick_labels.number_format_is_linked = False
        if value_max is not None:
            va.maximum_scale = value_max
        if value_min is not None:
            va.minimum_scale = value_min
        ca = chart.category_axis
        ca.format.line.color.rgb = rgb(D["line"])
        ca.tick_labels.font.size = Pt(size)
        ca.tick_labels.font.color.rgb = rgb(D["text"])
        ca.has_major_gridlines = False
        return chart

    @staticmethod
    def plot_layout(chart, x, y, w, h):
        """Fix the inner plot area (fractions of the chart frame) so overlays line up."""
        pa = chart._chartSpace.chart.plotArea
        lay = pa.find(qn("c:layout"))
        if lay is None:
            lay = etree.SubElement(pa, qn("c:layout"))
            pa.remove(lay)
            pa.insert(0, lay)
        for c in list(lay):
            lay.remove(c)
        ml = etree.SubElement(lay, qn("c:manualLayout"))
        for tag, val in (("c:layoutTarget", "inner"), ("c:xMode", "edge"), ("c:yMode", "edge"),
                         ("c:x", x), ("c:y", y), ("c:w", w), ("c:h", h)):
            etree.SubElement(ml, qn(tag)).set("val", str(val))

    @staticmethod
    def labels(series_or_plot, size, color, fmt='0.0"%"', pos=None):
        series_or_plot.has_data_labels = True if hasattr(series_or_plot, "has_data_labels") else None
        dl = series_or_plot.data_labels
        dl.number_format = fmt
        dl.number_format_is_linked = False
        dl.font.size = Pt(size)
        dl.font.color.rgb = rgb(color)
        dl.font.name = FONT
        if pos is not None:
            dl.position = pos
        dl.show_value = True
        return dl

    # ---------------------------------------------------------- save with click animations
    def save(self, path: Path):
        for s in self.prs.slides:                         # reading order: footer and page number last
            tree = s.shapes._spTree
            for sh in [x for x in s.shapes if x.name.endswith((" Footer", " Page"))]:
                tree.remove(sh._element)
                tree.append(sh._element)
            groups = self.clicks.get(id(s), [])
            if groups:
                s._element.append(etree.fromstring(click_timing(groups)))
        self.prs.save(path)


def click_timing(groups) -> str:
    ids = iter(range(3, 100000))
    pars = []
    for grp in groups:
        outer, inner = next(ids), next(ids)
        effs = []
        for k, sh in enumerate(grp):
            cid, setid, effid = next(ids), next(ids), next(ids)
            effs.append(
                f'<p:par><p:cTn id="{cid}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" '
                f'nodeType="{"clickEffect" if k == 0 else "withEffect"}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{setid}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{sh.shape_id}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
                f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{effid}" dur="400"/><p:tgtEl>'
                f'<p:spTgt spid="{sh.shape_id}"/></p:tgtEl></p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>')
        pars.append(f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
                    f'<p:childTnLst><p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                    f'<p:childTnLst>{"".join(effs)}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    return (f'<p:timing xmlns:p="{P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
            f'<p:childTnLst>{"".join(pars)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl>'
            f'<p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/>'
            f'</p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')


# ================================================================== main slides
def s1_lot(dk: Deck, st: dict):
    F = dk.F
    s = dk.slide(st["headline"], st["notes"], "S1")
    lot = F["_lot"]
    cd = CategoryChartData()
    cd.categories = list(lot.ticker)
    cd.add_series("One board lot, % of a 20M VND account", [round(v, 2) for v in lot.lot_pct_of_20m])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.45), Inches(1.45), Inches(9.0), Inches(5.3), cd)
    gf.name = "S1 Chart lot cost"
    ch = dk.chart_style(gf.chart, 12, value_max=120, fmt='0"%"')
    ch.plots[0].gap_width = 35
    ser = ch.series[0]
    for i, v in enumerate(lot.lot_pct_of_20m):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(SEM["violation"] if v > 100 else SEM["tradeoff"] if v > 10 else S["rounding"])
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.value_axis.has_title = True
    ch.value_axis.axis_title.text_frame.text = "% of account"
    ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(D["muted"])
    x0, y0, w0, h0 = 0.09, 0.04, 0.89, 0.78
    dk.plot_layout(ch, x0, y0, w0, h0)
    # 100% reference line drawn over the fixed plot area (move together with the chart if you edit it)
    cy = 1.45 + 5.3 * (y0 + h0 * (1 - 100 / 120))
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.45 + 9.0 * x0), Inches(cy), Inches(0.45 + 9.0 * (x0 + w0)), Inches(cy))
    ln.name = "S1 Line 100 percent"
    ln.line.color.rgb = rgb(SEM["violation"])
    ln.line.dash_style = 4
    ln.line.width = Pt(1.5)
    dk.text(s, 0.45 + 9.0 * (x0 + w0) - 2.4, cy - 0.32, 2.4, 0.3, "100% = whole account", 12, SEM["violation"],
            align=PP_ALIGN.RIGHT, name="S1 Label 100 percent")
    big = dk.text(s, 9.75, 1.6, 3.2, 1.3, st["big"], 66, SEM["violation"], bold=True, name="S1 Big number")
    dk.text(s, 9.75, 2.85, 3.2, 0.8, st["big_label"], 16, D["text"], name="S1 Big label")
    dk.text(s, 9.75, 3.8, 3.2, 2.4, st["side"], 16, D["muted"], name="S1 Side text")
    legend = dk.text(s, 9.75, 5.95, 3.3, 0.8, "", 12, runs=[
        [("■ ", {"color": SEM["violation"]}), ("> 100%: cannot buy one lot", {"color": D["muted"]})],
        [("■ ", {"color": SEM["tradeoff"]}), ("> 10%: one lot is a big step", {"color": D["muted"]})],
        [("■ ", {"color": S["rounding"]}), ("≤ 10%", {"color": D["muted"]})]], name="S1 Colour key")
    dk.text(s, 0.55, 6.75, 9, 0.3, st["caption"], 11, D["muted"], italic=True, name="S1 Caption")
    return s


def s2_options(dk: Deck, st: dict):
    s = dk.slide(st["headline"], st["notes"], "S2")
    cols = st["columns"]
    x, wcol = 0.55, 4.0
    accents = [S["etf"], S["odd_lot"], S["agqo"]]
    for i, c in enumerate(cols):
        cx = x + i * (wcol + 0.15)
        head = dk.panel(s, cx, 1.55, wcol, 0.75, f"S2 Option {i + 1} name", fill_=D["panel"], line=accents[i], lw=2,
                        text=c["name"], size=20, bold=True, color=accents[i] if i == 2 else D["text"])
        rows = []
        labels = ["Được gì", "Đổi lại", "Bám VN30"]
        for j, line in enumerate(c["lines"][:3]):
            rows.append([(labels[j] + "  ", {"size": 12, "color": D["muted"], "bold": True})])
            rows.append([(line, {"size": 18, "color": SEM["tradeoff"] if j == 1 else D["text"]})])
        body = dk.panel(s, cx, 2.4, wcol, 3.75, f"S2 Option {i + 1} body", fill_=D["panel"], line=D["line"], runs=rows,
                        anchor=MSO_ANCHOR.TOP)
    dk.text(s, 0.55, 6.3, 12.2, 0.7, st["footnote"], 11, D["muted"], italic=True, name="S2 Footnote")
    return s


def _weights_chart(dk, s, x, y, w, h, method, name, color):
    wdf = dk.F["_w"]
    d = wdf[(wdf.method == method) & (wdf.weight_pct > 0)].sort_values("weight_pct")
    cd = CategoryChartData()
    cd.categories = list(d.ticker)
    cd.add_series(f"{method}: weight, % of account", [round(v, 2) for v in d.weight_pct])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    gf.name = name
    ch = dk.chart_style(gf.chart, 12, value_max=40, gridlines=False, fmt='0"%"')
    ch.value_axis.visible = False
    ch.plots[0].gap_width = 45
    ser = ch.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(color)
    ch.plots[0].has_data_labels = True
    dk.labels(ch.plots[0], 12, D["text"], '0.0"%"', XL_LABEL_POSITION.OUTSIDE_END)
    return gf


def s3_demo(dk: Deck, st: dict):
    F = dk.F
    s = dk.slide(st["headline"], st["notes"], "S3")
    q = dk.panel(s, 0.55, 1.55, 3.6, 1.3, "S3 Instruction", fill_=D["panel"], line=D["line"],
                 runs=[[("Yêu cầu", {"size": 12, "color": D["muted"], "bold": True})], [(st["instruction"], {"size": 18})]],
                 anchor=MSO_ANCHOR.TOP)
    chips = []
    for i, c in enumerate(st["chips"]):
        chips.append(dk.panel(s, 0.55, 3.05 + i * 0.62, 3.6, 0.5, f"S3 Constraint {i + 1}", fill_=None, line=SEM["constraint"],
                              text="✔ " + c, size=15, color=SEM["constraint"]))
    src = dk.text(s, 0.55, 4.35, 3.6, 0.9, st["source"], 12, D["muted"], name="S3 Source")
    arrow = dk.arrow(s, 4.25, 3.4, 4.6, 3.4, "S3 Arrow")
    kp, tr = F["_kp"], F["_tr"]
    panels = []
    for k, (title, method, color, est, extra) in enumerate((
            (st["left_title"], "Nearest-lot rounding", S["rounding"], kp.loc["Nearest-lot rounding", "estimated_te_pct"],
             f"Đầu tư {vi(kp.loc['Nearest-lot rounding', 'invested_pct'], 0)}% · tiền nằm im {vi(100 - kp.loc['Nearest-lot rounding', 'invested_pct'], 0)}%"),
            (st["right_title"], "AGQO", S["agqo"], kp.loc["AGQO", "estimated_te_pct"],
             f"Tiền mặt sau phí {F['agqo_cash_m']} triệu · phí {F['fees_vnd']} đ"))):
        x = 4.75 + k * 4.25
        box = dk.panel(s, x, 1.55, 4.05, 4.95, f"S3 Outcome {k + 1} frame", fill_=D["panel"], line=color if k else D["line"],
                       lw=2 if k else 1)
        ttl = dk.text(s, x + 0.2, 1.65, 3.7, 0.45, title, 20, color if k else D["text"], bold=True, name=f"S3 Outcome {k + 1} title")
        ch = _weights_chart(dk, s, x + 0.1, 2.15, 3.85, 2.55, method, f"S3 Outcome {k + 1} weights", color)
        kpi = dk.text(s, x + 0.2, 4.8, 3.7, 1.6, "", 15, runs=[
            [("Sai số bám ước tính  ", {"size": 13, "color": D["muted"]}), (pct(est), {"size": 26, "bold": True,
                                                                                    "color": color if k else D["text"]})],
            [(f"{int(kp.loc[method, 'holdings'])} mã · " + extra, {"size": 13, "color": D["text"]})]],
            name=f"S3 Outcome {k + 1} numbers")
        panels.append((box, ttl, ch, kpi))
    dk.text(s, 0.55, 6.62, 12.2, 0.4, st["caption"], 11, D["muted"], italic=True, name="S3 Caption")
    dk.click(s, q)
    dk.click(s, *chips, src, arrow)
    dk.click(s, *[x for p in panels for x in p])
    return s


def s4_backtest(dk: Deck, st: dict):
    F = dk.F
    s = dk.slide(st["headline"], st["notes"], "S4")
    acc = F["_acc"]
    cd = CategoryChartData()
    cd.categories = [f"{int(c / 1e6)}M VND" for c in acc.index]
    for col, label in (("practitioner", "Nearest-lot rounding"), ("greedy", "Greedy lot filling"), ("agqo", "AGQO")):
        cd.add_series(label, [round(v, 2) for v in acc[col]])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.45), Inches(1.5), Inches(8.3), Inches(5.0), cd)
    gf.name = "S4 Chart TE by account size"
    ch = dk.chart_style(gf.chart, 13, legend=True, value_max=14, fmt='0"%"')
    ch.plots[0].gap_width = 60
    ch.plots[0].overlap = -5
    for ser, col in zip(ch.series, (S["rounding"], S["greedy"], S["agqo"])):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
    ch.plots[0].has_data_labels = True
    dk.labels(ch.plots[0], 11, D["text"], '0.0', XL_LABEL_POSITION.OUTSIDE_END)
    ch.value_axis.has_title = True
    ch.value_axis.axis_title.text_frame.text = "Annualised tracking error vs VN30"
    ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(D["muted"])
    boxes = []
    colors = [S["agqo"], S["greedy"], SEM["constraint"]]
    for i, c in enumerate(st["callouts"]):
        boxes.append(dk.panel(s, 9.0, 1.6 + i * 1.55, 3.85, 1.38, f"S4 Callout {i + 1}", fill_=D["panel"], line=colors[i],
                              text=c, size=15, anchor=MSO_ANCHOR.MIDDLE))
    dk.text(s, 0.55, 6.55, 12.2, 0.5, st["caption"], 11, D["muted"], italic=True, name="S4 Caption")
    return s


def s5_mapping(dk: Deck, st: dict):
    F = dk.F
    s = dk.slide(st["headline"], st["notes"], "S5")
    # one stock: continuous target -> fixed lots + one binary choice
    stock = dk.panel(s, 0.55, 1.6, 2.4, 1.2, "S5 Stock", fill_=D["panel"], line=D["line"],
                     runs=[[("SSI", {"size": 30, "bold": True})], [("Brokerage", {"size": 13, "color": D["muted"]})]],
                     align=PP_ALIGN.CENTER)
    steps = []
    for i, t in enumerate(st["steps"]):
        steps.append(dk.panel(s, 3.25, 1.55 + i * 0.68, 5.6, 0.58, f"S5 Step {i + 1}", fill_=None, line=D["line"], text=t, size=15))
    # bit diagram: fixed lots + qubit
    fixed = dk.panel(s, 9.15, 1.55, 1.7, 0.95, "S5 Fixed lots", fill_=S["rounding"], line=None,
                     runs=[[("fixed", {"size": 12, "color": D["bg"]})], [(f"{F['ssi_fixed']} lots", {"size": 18, "bold": True, "color": D["bg"]})]],
                     align=PP_ALIGN.CENTER)
    plus = dk.text(s, 10.9, 1.75, 0.35, 0.5, "+", 26, D["muted"], align=PP_ALIGN.CENTER, name="S5 Plus")
    qubit = dk.panel(s, 11.3, 1.55, 1.55, 0.95, "S5 Qubit", fill_=None, line=S["agqo"], lw=2,
                     runs=[[("x ∈ {0, 1}", {"size": 18, "bold": True, "color": S["agqo"]})], [("+1 lot?", {"size": 12, "color": D["muted"]})]],
                     align=PP_ALIGN.CENTER)
    # sixteen bits
    bits = []
    reg = pd.read_csv(DATA / "c5_register.csv")
    for i, r in enumerate(reg.itertuples()):
        x = 0.55 + i * 0.77
        on = int(r.agqo_bit) == 1
        bits.append(dk.panel(s, x, 3.85, 0.7, 0.9, f"S5 Bit {r.ticker}", fill_=S["agqo"] if on else None,
                             line=S["agqo"] if on else D["line"],
                             runs=[[(r.ticker, {"size": 11, "bold": True, "color": D["bg"] if on else D["text"]})],
                                   [(str(int(r.agqo_bit)), {"size": 16, "bold": True, "color": D["bg"] if on else D["muted"]})]],
                             align=PP_ALIGN.CENTER))
    for b in bits:
        b.text_frame.margin_left = b.text_frame.margin_right = Inches(0.02)
    scale = dk.text(s, 0.55, 4.85, 12.2, 0.4, st["scale"] + "   ·   ô sáng = AGQO chọn mua thêm một lô (quyết định 01/10/2026)",
                    16, D["text"], name="S5 Scale")
    pair = dk.panel(s, 0.55, 5.4, 6.0, 0.95, "S5 Pairwise interaction", fill_=None, line=SEM["constraint"], text=st["pair"], size=14)
    rule = dk.panel(s, 6.75, 5.4, 6.05, 0.95, "S5 Rules", fill_=None, line=SEM["tradeoff"], text=st["rule"], size=14)
    dk.click(s, stock, *steps[:2], fixed, plus, qubit)
    dk.click(s, steps[2])
    dk.click(s, *bits, scale)
    dk.click(s, pair, rule)
    return s


def s6_circuit(dk: Deck, st: dict):
    F = dk.F
    s = dk.slide(st["headline"], st["notes"], "S6")
    c6 = pd.read_csv(DATA / "c6_circuits.csv").set_index("arm2")
    order = ["textbook", "warm_start_only", "random_search", "agqo", "polish_ablation", "frozen"]
    cd = CategoryChartData()
    cd.categories = [c6.loc[a, "label"] for a in order]
    cd.add_series("Near-optimal solution probability per shot", [round(c6.loc[a, "success_pct"], 2) for a in order])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.45), Inches(1.5), Inches(8.2), Inches(4.4), cd)
    gf.name = "S6 Chart probability per shot"
    ch = dk.chart_style(gf.chart, 14, value_max=30, fmt='0"%"')
    ch.plots[0].gap_width = 40
    ser = ch.series[0]
    cols = {"textbook": S["textbook"], "warm_start_only": S["warm_start"], "random_search": S["random"], "agqo": S["agqo"],
            "polish_ablation": S["exact"], "frozen": S["exact"]}
    for i, a in enumerate(order):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(cols[a])
    ch.plots[0].has_data_labels = True
    dk.labels(ch.plots[0], 14, D["text"], '0.0"%"', XL_LABEL_POSITION.OUTSIDE_END)
    mult = dk.text(s, 8.95, 1.6, 3.9, 1.2, st["multiplier"], 22, S["agqo"], bold=True, name="S6 Multiplier")
    side = dk.text(s, 8.95, 2.95, 3.9, 2.8, st["side"], 15, D["text"], name="S6 Side note")
    dk.text(s, 0.55, 6.0, 12.2, 0.9, st["conditions"], 12, D["muted"], name="S6 Conditions")
    return s


def s7_next(dk: Deck, st: dict):
    s = dk.slide(st["headline"], st["notes"], "S7")
    colors = [SEM["pass"], SEM["tradeoff"], S["agqo"]]
    for i, c in enumerate(st["columns"]):
        x = 0.55 + i * 4.15
        dk.panel(s, x, 1.6, 4.0, 0.7, f"S7 Column {i + 1} title", fill_=D["panel"], line=colors[i], lw=2, text=c["name"],
                 size=18, bold=True)
        dk.panel(s, x, 2.4, 4.0, 3.5, f"S7 Column {i + 1} body", fill_=D["panel"], line=D["line"], anchor=MSO_ANCHOR.TOP,
                 runs=[[("• " + l, {"size": 16})] for l in c["lines"]])
    dk.panel(s, 0.55, 6.05, 12.25, 0.75, "S7 Status", fill_=None, line=SEM["tradeoff"], text=st["status"], size=14,
             color=SEM["tradeoff"])
    return s


def s8_close(dk: Deck, st: dict):
    s = dk.slide(st["headline"], st["notes"], "S8")
    for i, l in enumerate(st["lines"]):
        dk.panel(s, 0.55, 1.75 + i * 0.95, 12.25, 0.8, f"S8 Line {i + 1}", fill_=D["panel"], line=S["agqo"] if i == 0 else D["line"],
                 text=l, size=20, bold=i == 0)
    dk.text(s, 0.9, 5.0, 11.6, 1.4, st["close"], 24, S["agqo"], bold=True, name="S8 Closing sentence")
    return s


def cover(dk: Deck, meta: dict):
    s = dk.slide("", "Trang bìa: điền mã đội, tên đội. Không nói gì ở trang này; chuyển ngay sang trang 1.", "S0", layout=6)
    dk.text(s, 0.8, 2.0, 11.8, 1.2, "AGQO", 60, S["agqo"], bold=True, name="S0 Product")
    dk.text(s, 0.8, 3.15, 11.8, 1.2, meta["title"].split("—", 1)[-1].strip(), 28, D["text"], bold=True, name="S0 Title")
    dk.text(s, 0.8, 4.4, 11.8, 0.9, "Mã đội: [Mã đội]   ·   Tên đội: [Tên đội]   ·   AI–Quantum Challenge 2026, vòng bán kết", 16,
            D["muted"], name="S0 Team")
    dk.text(s, 0.8, 5.0, 11.8, 0.6, "Prototype: https://data1--agqo-v32.us-east.modal.run", 14, D["muted"], name="S0 Link")
    for sh in list(s.shapes):
        if sh.name == "S0 Page":
            sh._element.getparent().remove(sh._element)
    dk.n = 0                                                  # main slides are numbered from 1


# ================================================================== appendix
def appendix(dk: Deck, items: list[dict]):
    s = dk.slide("Phụ lục", "Phần phụ lục: chỉ mở khi được hỏi. Mỗi trang trả lời một câu hỏi.", "A0")
    dk.text(s, 0.55, 2.6, 12.2, 2.5, "", 22, runs=[[(f"{it['id']}  ", {"size": 20, "bold": True, "color": S["agqo"]}),
                                                    (it["headline"].split("·", 1)[-1].strip(), {"size": 20})]
                                                   for it in items], name="A0 Contents", spacing=6)
    for it in items:
        s = dk.slide(it["headline"], it.get("notes") or f"Mở trang này khi được hỏi về: {it['headline'].split('·', 1)[-1].strip()}. "
                     "Đọc dòng đầu, chỉ vào nguồn ở chú thích, rồi quay lại câu hỏi.", it["id"])
        kind = it["kind"]
        if kind == "table":
            rows = it["rows"]
            tbl = s.shapes.add_table(len(rows), len(rows[0]), Inches(0.55), Inches(1.55), Inches(12.2),
                                     Inches(0.5 * len(rows))).table
            s.shapes[-1].name = f"{it['id']} Table"
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    cell = tbl.cell(r, c)
                    cell.text = fill(str(val), dk.F)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = rgb(D["panel"] if r else D["line"])
                    for p in cell.text_frame.paragraphs:
                        for run in p.runs:
                            run.font.size, run.font.name = Pt(13), FONT
                            run.font.bold = r == 0
                            run.font.color.rgb = rgb(D["text"])
        elif kind == "chart":
            df = pd.read_csv(DATA / it["data"])
            cd = CategoryChartData()
            cd.categories = [str(v) for v in df[it["x"]]]
            for col, label in it["series"]:
                cd.add_series(label, [round(float(v), 3) for v in df[col]])
            ctype = {"line": XL_CHART_TYPE.LINE_MARKERS, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
                     "column": XL_CHART_TYPE.COLUMN_CLUSTERED}[it["type"]]
            gf = s.shapes.add_chart(ctype, Inches(0.45), Inches(1.5), Inches(8.0), Inches(5.0), cd)
            gf.name = f"{it['id']} Chart"
            ch = dk.chart_style(gf.chart, 13, legend=len(it["series"]) > 1, value_max=it.get("max"), fmt=it.get("fmt", '0"%"'))
            pal = [S["agqo"], S["greedy"], S["rounding"], SEM["constraint"]]
            for ser, col in zip(ch.series, pal):
                if it["type"] == "line":
                    ser.format.line.color.rgb = rgb(col)
                    ser.format.line.width = Pt(2.5)
                    ser.marker.format.fill.solid()
                    ser.marker.format.fill.fore_color.rgb = rgb(col)
                else:
                    ser.format.fill.solid()
                    ser.format.fill.fore_color.rgb = rgb(col)
            if it.get("labels", True):
                ch.plots[0].has_data_labels = True
                dk.labels(ch.plots[0], 12, D["text"], it.get("label_fmt", '0.0'), XL_LABEL_POSITION.ABOVE
                          if it["type"] == "line" else XL_LABEL_POSITION.OUTSIDE_END)
            if it.get("x_title"):
                ch.category_axis.has_title = True
                ch.category_axis.axis_title.text_frame.text = it["x_title"]
                r0 = ch.category_axis.axis_title.text_frame.paragraphs[0].runs[0]
                r0.font.size, r0.font.color.rgb = Pt(12), rgb(D["muted"])
            dk.text(s, 8.75, 1.6, 4.1, 4.9, "", 14, runs=[[(l, {"size": 14})] for l in it["side"]], name=f"{it['id']} Side")
        elif kind == "shots":
            x = 0.55
            for k, (fname, cap) in enumerate(it["shots"]):
                path = SHOTS / fname
                pic = dk.picture(s, path, x, 1.55, w=it.get("width", 6.0), name=f"{it['id']} Screenshot {k + 1}")
                if pic.height > Inches(4.6):                      # keep inside the slide
                    ratio = Inches(4.6) / pic.height
                    pic.height, pic.width = Inches(4.6), int(pic.width * ratio)
                dk.text(s, x, 1.65 + pic.height / 914400, pic.width / 914400, 0.6, cap, 13, D["muted"],
                        name=f"{it['id']} Screenshot {k + 1} caption")
                x += pic.width / 914400 + 0.25
        elif kind == "text":
            dk.text(s, 0.55, 1.55, 12.2, 5.2, "", 16, runs=[[(l, {"size": it.get("size", 16)})] for l in it["lines"]],
                    name=f"{it['id']} Body")
        if it.get("caption"):
            dk.text(s, 0.55, 6.6, 12.2, 0.4, it["caption"], 11, D["muted"], italic=True, name=f"{it['id']} Caption")


def build(out_dir: Path | None = None) -> Path:
    story = yaml.safe_load((HERE / "story.yaml").read_text())
    apx = yaml.safe_load((HERE / "appendix.yaml").read_text())
    F = facts()
    dk = Deck(story, F)
    builders = {"s1_lot": s1_lot, "s2_options": s2_options, "s3_demo": s3_demo, "s4_backtest": s4_backtest,
                "s5_mapping": s5_mapping, "s6_circuit": s6_circuit, "s7_next": s7_next, "s8_close": s8_close}
    cover(dk, story["meta"])
    for st in story["slides"]:
        builders[st["id"]](dk, st)
    appendix(dk, apx["items"])
    out_dir = out_dir or ROOT / "submission" / "drafts" / time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=False)          # never overwrite an earlier draft
    path = out_dir / "AGQO_BanKet_Slide.pptx"
    dk.save(path)
    (out_dir / "facts.json").write_text(json.dumps({k: v for k, v in F.items() if not k.startswith("_")}, indent=1,
                                                   ensure_ascii=False))
    print(path)
    return path


if __name__ == "__main__":
    build()
