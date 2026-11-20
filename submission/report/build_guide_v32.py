"""Guide document (judge quick start + reproducibility) from the two Markdown sources.

    python submission/report/build_guide_v32.py    # -> submission/drafts/guide-<UTC>/AQ2026-R2-Madoi-Huong_dan.docx

Sources: docs/vi/HUONG_DAN_GIAM_KHAO.md and docs/vi/TAI_LAP.md (edit those, then rerun). Handles headings,
paragraphs, numbered and bulleted lists, tables, fenced code and **bold**.
"""

import re
import time
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SRC = [ROOT / "docs/vi/HUONG_DAN_GIAM_KHAO.md", ROOT / "docs/vi/TAI_LAP.md"]
SHOT = ROOT / "docs/prototype_shots/v32/pitch_constraints_pending.png"
INK, ACC, MUTED = RGBColor(0x0F, 0x17, 0x2A), RGBColor(0x02, 0x84, 0xC7), RGBColor(0x47, 0x55, 0x69)


def runs(p, text, size=10.5, mono=False):
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    for k, seg in enumerate(re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)):
        if not seg:
            continue
        bold, code = seg.startswith("**"), seg.startswith("`")
        r = p.add_run(seg.strip("*`") if (bold or code) else seg)
        r.bold = bold
        r.font.size = Pt(size)
        r.font.name = "Consolas" if (code or mono) else "Arial"
        r.font.color.rgb = INK


def build() -> Path:
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Arial", Pt(10.5)
    for i, src in enumerate(SRC):
        if i:
            doc.add_page_break()
        lines = src.read_text().splitlines()
        k = 0
        while k < len(lines):
            ln = lines[k]
            if ln.startswith("```"):
                k += 1
                while not lines[k].startswith("```"):
                    p = doc.add_paragraph()
                    runs(p, lines[k], 9, mono=True)
                    p.paragraph_format.left_indent = Cm(0.6)
                    k += 1
            elif ln.startswith("#"):
                lvl = len(ln) - len(ln.lstrip("#"))
                p = doc.add_paragraph()
                r = p.add_run(ln.lstrip("# ").strip())
                r.bold = True
                r.font.size = Pt({1: 18, 2: 13, 3: 11}[min(lvl, 3)])
                r.font.color.rgb = ACC if lvl == 1 else INK
                p.paragraph_format.space_before = Pt(10 if lvl > 1 else 0)
                if lvl == 1 and i == 0 and SHOT.exists():
                    pass
            elif ln.startswith("|"):
                rows = []
                while k < len(lines) and lines[k].startswith("|"):
                    if not re.match(r"^\|[-| :]+\|$", lines[k]):
                        rows.append([c.strip() for c in lines[k].strip("|").split("|")])
                    k += 1
                k -= 1
                t = doc.add_table(rows=len(rows), cols=len(rows[0]))
                t.style = "Light Grid Accent 1"
                for r_, row in enumerate(rows):
                    for c_, val in enumerate(row):
                        cell = t.cell(r_, c_)
                        cell.text = ""
                        runs(cell.paragraphs[0], f"**{val}**" if r_ == 0 else val, 9.5)
                doc.add_paragraph()
            elif re.match(r"^\s*(\d+\.|-)\s", ln):
                text = re.sub(r"^\s*(\d+\.|-)\s", "", ln)
                while k + 1 < len(lines) and lines[k + 1].startswith("  ") and not re.match(r"^\s*(\d+\.|-)\s", lines[k + 1]):
                    k += 1
                    text += " " + lines[k].strip()
                p = doc.add_paragraph(style="List Number" if re.match(r"^\s*\d+\.", ln) else "List Bullet")
                runs(p, text)
            elif ln.strip():
                text = ln
                while k + 1 < len(lines) and lines[k + 1].strip() and not re.match(r"^(#|\||```|\s*(\d+\.|-)\s)", lines[k + 1]):
                    k += 1
                    text += " " + lines[k].strip()
                runs(doc.add_paragraph(), text)
            k += 1
        if i == 0 and SHOT.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(SHOT), width=Cm(15))
            c = doc.add_paragraph()
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = c.add_run("Bước 3 của prototype: ràng buộc từ câu lệnh, có nhãn nguồn, chờ xác nhận trước khi chạy.")
            r.italic, r.font.size, r.font.color.rgb = True, Pt(9), MUTED
    out_dir = ROOT / "submission" / "drafts" / ("guide-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
    out_dir.mkdir(parents=True, exist_ok=False)
    out = out_dir / "AQ2026-R2-Madoi-Huong_dan.docx"
    doc.save(out)
    print(out)
    return out


if __name__ == "__main__":
    build()
