"""Export a deck to PDF with Microsoft PowerPoint (macOS) and write PNG contact sheets for review.

    python submission/deck/render.py <deck.pptx> [<out_dir>]

PowerPoint is sandboxed: the file is copied to ~/Library/Containers/com.microsoft.Powerpoint/Data/Documents/agqo,
exported there and the PDF copied back next to the deck.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pymupdf
from PIL import Image

SCRIPT = '''on run argv
  tell application "Microsoft PowerPoint"
    open POSIX file (item 1 of argv)
    delay 3
    set p to active presentation
    save p in POSIX file (item 2 of argv) as save as PDF
    close p saving no
  end tell
end run'''


def export_pdf(pptx: Path) -> Path:
    box = Path.home() / "Library/Containers/com.microsoft.Powerpoint/Data/Documents/agqo"
    box.mkdir(parents=True, exist_ok=True)
    src, dst = box / pptx.name, box / (pptx.stem + ".pdf")
    shutil.copy(pptx, src)
    if dst.exists():
        dst.unlink()
    subprocess.run(["osascript", "-e", SCRIPT, str(src), str(dst)], check=True)
    out = pptx.with_suffix(".pdf")
    shutil.copy(dst, out)
    return out


def sheets(pdf: Path, out_dir: Path, dpi: int = 60) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    ims = []
    for i, page in enumerate(doc):
        f = out_dir / f"page{i + 1:02d}.png"
        page.get_pixmap(dpi=dpi).save(f)
        ims.append(Image.open(f))
    w, h = ims[0].size
    paths = []
    for k in range(0, len(ims), 6):
        sheet = Image.new("RGB", (w * 2, h * 3), "white")
        for i, im in enumerate(ims[k:k + 6]):
            sheet.paste(im, ((i % 2) * w, (i // 2) * h))
        paths.append(out_dir / f"sheet{k // 6}.png")
        sheet.save(paths[-1])
    print(f"{len(doc)} pages -> {out_dir}")
    return paths


if __name__ == "__main__":
    deck = Path(sys.argv[1]).resolve()
    pdf = export_pdf(deck)
    sheets(pdf, Path(sys.argv[2]) if len(sys.argv) > 2 else deck.parent / "render")
