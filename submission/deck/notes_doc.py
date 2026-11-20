"""Write the talk track, the three-minute cut and the Q&A cards from story.yaml / qa.yaml (same facts as the deck).

    python submission/deck/notes_doc.py        # -> docs/submission/LOI_NOI_THUYET_TRINH.md
"""

from pathlib import Path

import yaml

from build_deck import HERE, ROOT, facts, fill


def main() -> Path:
    story = yaml.safe_load((HERE / "story.yaml").read_text())
    qa = yaml.safe_load((HERE / "qa.yaml").read_text())
    F = facts()
    out = ["# Lời nói thuyết trình, bản 3 phút và thẻ hỏi–đáp", "",
           "Sinh tự động từ `submission/deck/story.yaml` và `qa.yaml` (cùng số liệu với deck). Sửa ở đó rồi chạy lại "
           "`python submission/deck/notes_doc.py`.", "", "## Bản đầy đủ (8 slide, khoảng 8–9 phút)", ""]
    for i, s in enumerate(story["slides"], 1):
        n = s["notes"]
        out += [f"### Slide {i}. {fill(s['headline'], F)}", "",
                f"- **Câu mở:** {fill(n['first'], F)}", f"- **Nhìn vào:** {fill(n['cue'], F)}",
                f"- **Ý chính:** {fill(n['takeaway'], F)}", f"- **Chuyển ý:** {fill(n['handoff'], F)}", ""]
    out += ["## Bản 3 phút (slide 1, 3, 4, 8)", "",
            "Bỏ slide 2, 5, 6, 7; nếu được hỏi về lượng tử, mở slide 6 hoặc phụ lục A2–A4.", ""]
    for i, s in enumerate(story["slides"], 1):
        if s.get("cut3"):
            n = s["notes"]
            out += [f"**Slide {i} (~45 giây).** {fill(n['first'], F)} {fill(n['takeaway'], F)}", ""]
    out += ["Câu cuối: " + fill(story["slides"][-1]["close"], F), "", "## Thẻ hỏi–đáp", ""]
    for k, c in enumerate(qa["cards"], 1):
        out += [f"**{k}. {c['q']}**", "", fill(c["a"], F), "", f"*Mở:* {c['evidence']}", ""]
    path = ROOT / "docs" / "submission" / "LOI_NOI_THUYET_TRINH.md"
    path.write_text("\n".join(out))
    print(path)
    return path


if __name__ == "__main__":
    main()
