#!/usr/bin/env python3
"""Chạy kiểm định AI–QAOA và dựng báo cáo, biểu đồ từ dữ liệu cục bộ."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agqo.guide import (
    CachedGuide,
    QWEN38_MODAL_APP,
    QWEN38_MODAL_CLASS,
    QWEN38_MODEL_NAME,
    QWEN38_MODEL_REVISION,
    QWEN38_REASONING_EFFORT,
    ModalQwenGuide,
    PROMPT_CACHE_VERSION,
)
from agqo.walkforward import AGQO_STRATEGY_NAME, ResearchConfig, run_walkforward
from agqo.final_visuals import build_final_visuals
from agqo.market_data import analyze_market_dataset, summary_json
from agqo.plots import create_market_figures
from agqo.walkforward_plots import build_walkforward_plots
from agqo.walkforward_report import write_walkforward_report


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "data/vn30_snapshot_20261002/ohlcv_daily.csv",
        help="Đường dẫn CSV OHLCV đã lưu cục bộ.",
    )
    parser.add_argument(
        "--members",
        type=Path,
        default=ROOT / "data/vn30_snapshot_20261002/vn30_membership_history.csv",
        help="Đường dẫn CSV lịch thành phần VN30 theo ngày hiệu lực.",
    )
    parser.add_argument(
        "--news",
        type=Path,
        default=None,
        help="Tệp CSV siêu dữ liệu GDELT đã thu thập tại thời điểm thực; bỏ trống thì không dùng tin tức.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=ROOT / "results/final/agqo_final_walkforward.json",
        help="Tệp kết quả chi tiết dạng JSON.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "results/final/BAO_CAO_AGQO_CUOI_CUNG.md",
        help="Tệp báo cáo tiếng Việt.",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "results/final/figures",
        help="Thư mục lưu biểu đồ.",
    )
    parser.add_argument(
        "--llm-guide",
        choices=("none", "modal-qwen38"),
        default="none",
        help="Chọn Qwen3.8-27B trên Modal (vLLM, 1×H100) hoặc tắt hướng dẫn LLM.",
    )
    parser.add_argument(
        "--guide-cache",
        type=Path,
        default=ROOT / "results/final/qwen38_decisions.json",
        help="Tệp lưu lời khuyên LLM đã xác thực để tránh gọi lại cùng tín hiệu.",
    )
    parser.add_argument(
        "--qwen-model",
        default=os.environ.get("AGQO_QWEN38_MODEL", QWEN38_MODEL_NAME),
        help="Tên mô hình trên Hugging Face; mặc định Qwen/Qwen3.8-27B-FP8.",
    )
    parser.add_argument(
        "--qwen-revision",
        default=os.environ.get("AGQO_QWEN38_REVISION", QWEN38_MODEL_REVISION),
        help="Mã phiên bản Hugging Face; mặc định ghim vào phiên bản đã kiểm tra.",
    )
    parser.add_argument(
        "--qwen-reasoning-effort",
        choices=("low", "medium", "xhigh"),
        default=os.environ.get("AGQO_QWEN38_REASONING_EFFORT", QWEN38_REASONING_EFFORT),
        help="Mức suy luận Qwen3.8-27B; mặc định medium.",
    )
    parser.add_argument(
        "--qwen-modal-app",
        default=os.environ.get("AGQO_QWEN38_MODAL_APP", QWEN38_MODAL_APP),
        help="Tên ứng dụng Modal đã triển khai cho Qwen3.8-27B.",
    )
    parser.add_argument(
        "--qwen-modal-class",
        default=os.environ.get("AGQO_QWEN38_MODAL_CLASS", QWEN38_MODAL_CLASS),
        help="Tên lớp suy luận Qwen3.8-27B trong ứng dụng Modal.",
    )
    args = parser.parse_args()

    guide = None
    if args.llm_guide == "modal-qwen38":
        guide = CachedGuide(
            ModalQwenGuide(
                app_name=args.qwen_modal_app,
                class_name=args.qwen_modal_class,
                model_name=args.qwen_model,
                revision=args.qwen_revision,
                reasoning_effort=args.qwen_reasoning_effort,
            ),
            args.guide_cache,
            cache_namespace=(
                f"{PROMPT_CACHE_VERSION}:modal-qwen38:{args.qwen_modal_app}:{args.qwen_modal_class}:"
                f"{args.qwen_model}:{args.qwen_revision}:{args.qwen_reasoning_effort}"
            ),
        )
    result = run_walkforward(
        args.data, args.members, args.json, ResearchConfig(), guide=guide, news_path=args.news
    )
    figures = build_walkforward_plots(args.json, args.figures)
    figures.extend(build_final_visuals(args.json, args.figures))
    dataset_summary = analyze_market_dataset(args.data, args.members)
    dataset_summary_path = args.json.parent / "dataset_summary.json"
    dataset_summary_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_summary_path.write_text(summary_json(dataset_summary) + "\n", encoding="utf-8")
    figures.extend(
        create_market_figures(
            args.data,
            args.members,
            dataset_summary,
            args.figures / "data",
        )
    )
    report = write_walkforward_report(args.json, args.report, args.figures)
    print(f"Đã lưu dữ liệu đo: {args.json}")
    print(f"Đã lưu báo cáo: {report}")
    print(f"Đã tạo {len(figures)} biểu đồ trong: {args.figures}")
    print(
        "CAGR ròng: "
        f"AI toàn rổ={result['portfolio']['performance']['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện']['metrics']['cagr']:.2%}; "
        f"QAOA X p=1={result['portfolio']['performance']['AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao']['metrics']['cagr']:.2%}; "
        f"VN30={result['portfolio']['performance']['VN30']['metrics']['cagr']:.2%}."
    )
    if result["agqo_guidance"]["enabled"]:
        agqo = result["portfolio"]["performance"][AGQO_STRATEGY_NAME]["metrics"]
        print(
            "AGQO LLM→QAOA: "
            f"CAGR={agqo['cagr']:.2%}, Sharpe={agqo['sharpe']:.2f}, "
            f"MaxDD={agqo['max_drawdown']:.2%}; "
            f"LLM đã chọn {result['agqo_guidance']['decision_count']} cấu hình; "
            f"{result['agqo_guidance']['recorded_token_usage']['total_tokens']:,} token trong phản hồi đã lưu."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
