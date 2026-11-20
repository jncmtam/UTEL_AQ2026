"""Export a DOCX to PDF with Microsoft Word (macOS) and print the page count.

    python submission/report/docx2pdf.py <file.docx>        # writes <file>.pdf next to it
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pymupdf

SCRIPT = '''on run argv
tell application "Microsoft Word"
  open POSIX file (item 1 of argv)
  delay 3
  set d to active document
  save as d file name (item 2 of argv) file format format PDF
  close d saving no
end tell
end run'''

src = Path(sys.argv[1]).resolve()
box = Path.home() / "Library/Containers/com.microsoft.Word/Data/Documents/agqo"
box.mkdir(parents=True, exist_ok=True)
a, b = box / src.name, box / (src.stem + ".pdf")
shutil.copy(src, a)
if b.exists():
    b.unlink()
subprocess.run(["osascript", "-e", SCRIPT, str(a), str(b)], check=True)
out = src.with_suffix(".pdf")
shutil.copy(b, out)
print(out, "pages:", len(pymupdf.open(out)))
