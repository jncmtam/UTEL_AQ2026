#!/usr/bin/env python3
"""Tạo bộ hình bổ sung, catalog và caption kiểm tra được cho báo cáo AGQO."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agqo.figure_catalog import build_catalog, update_markdown_captions, validate_markdown_images, write_catalog
from agqo.research_visuals import (
    build_actual_circuit_comparison,
    build_market_regime_figure,
    build_monthly_return_heatmap,
    build_pipeline_diagram,
)


ROOT = Path(__file__).resolve().parents[1]

def ensure_visual_appendix(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    base_text = text.split("\n## Hình bổ sung:", maxsplit=1)[0]
    figure_prefix = Path(os.path.relpath(ROOT / "results/final/figures", path.parent)).as_posix()
    appendix = f"""\n\n## Hình bổ sung: thị trường, pipeline và circuit đã chạy\n\nCác hình này kết nối trạng thái dữ liệu với luồng AGQO và circuit được dựng từ log thực tế. Mỗi hình có tên, giải thích, nguồn, kỳ, đơn vị và lưu ý đi kèm.\n\n![Kiến trúc AGQO từ dữ liệu đến bằng chứng]({figure_prefix}/12_agqo_pipeline.png)\n\n![Giá, biến động, độ rộng và phân tán thị trường]({figure_prefix}/13_market_regime_timeline.png)\n\n![Bản đồ lợi suất tháng theo cổ phiếu]({figure_prefix}/14_cross_section_monthly_returns.png)\n\n![Mạch QAOA qua ba bối cảnh thị trường đã lưu]({figure_prefix}/15_actual_qaoa_circuit_comparison.png)\n"""
    conclusion = "\n## Kết luận\n"
    if conclusion in base_text:
        before, after = base_text.split(conclusion, maxsplit=1)
        updated = before.rstrip() + appendix + conclusion + after
    else:
        updated = base_text.rstrip() + appendix
    path.write_text(updated.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/vn30_snapshot_20261002/ohlcv_daily.csv")
    parser.add_argument("--members", type=Path, default=ROOT / "data/vn30_snapshot_20261002/members.csv")
    parser.add_argument("--result", type=Path, default=ROOT / "results/final/agqo_final_walkforward.json")
    parser.add_argument("--figures", type=Path, default=ROOT / "results/final/figures")
    args = parser.parse_args()

    build_pipeline_diagram(args.figures)
    build_market_regime_figure(args.data, args.members, args.figures)
    build_monthly_return_heatmap(args.data, args.members, args.figures)
    build_actual_circuit_comparison(
        args.result,
        args.data,
        args.members,
        args.figures,
        args.result.parent / "circuit_metadata.json",
    )

    image_paths = [path.relative_to(ROOT).as_posix() for path in sorted(args.figures.rglob("*.png"))]
    catalog = build_catalog(image_paths)
    write_catalog(args.result.parent / "figure_catalog.json", catalog)

    readme = ROOT / "README.md"
    report = args.result.parent / "BAO_CAO_AGQO_CUOI_CUNG.md"
    for markdown in (readme, report):
        if markdown.exists():
            ensure_visual_appendix(markdown)
            update_markdown_captions(markdown, ROOT, catalog)
    errors = [
        error
        for markdown in (readme, report)
        if markdown.exists()
        for error in validate_markdown_images(markdown, ROOT)
    ]
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Đã tạo {len(image_paths)} hình; catalog: {args.result.parent / 'figure_catalog.json'}")
    print(f"Đã kiểm tra caption và đường dẫn ảnh trong {readme.name} và {report.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
