from pathlib import Path

from agqo.figure_catalog import update_markdown_captions, validate_markdown_images


ROOT = Path(__file__).resolve().parents[1]


def test_readme_and_result_report_have_existing_images_with_captions():
    paths = [
        ROOT / "README.md",
        ROOT / "results/final/BAO_CAO_AGQO_CUOI_CUNG.md",
    ]
    for path in paths:
        if path.exists():
            assert validate_markdown_images(path, ROOT) == []


def test_validator_rejects_missing_caption_and_asset(tmp_path):
    doc = tmp_path / "sample.md"
    doc.write_text("![Chart](missing.png)\n", encoding="utf-8")
    errors = validate_markdown_images(doc, tmp_path)
    assert any("image does not exist" in error for error in errors)
    assert any("missing figure title" in error for error in errors)


def test_caption_updater_replaces_stale_caption_and_uses_relative_asset_path(tmp_path):
    image = tmp_path / "chart.png"
    image.write_bytes(b"image")
    doc = tmp_path / "report.md"
    doc.write_text("![Old title](chart.png)\n\n**Hình 1. Old.** stale text\n", encoding="utf-8")
    catalog = [{
        "number": 2,
        "path": "chart.png",
        "title": "Current chart",
        "caption": "Updated description with enough words to satisfy the report caption quality rule.",
        "source": "sample data",
        "period": "2026",
        "units": "count",
        "caveat": "Illustrative only.",
    }]
    update_markdown_captions(doc, tmp_path, catalog)
    result = doc.read_text(encoding="utf-8")
    assert "**Figure 2. Current chart.**" in result
    assert "stale text" not in result
    assert validate_markdown_images(doc, tmp_path) == []
