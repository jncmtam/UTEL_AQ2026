#!/usr/bin/env python3
"""Chạy kiểm định AI–QAOA và dựng báo cáo, biểu đồ từ dữ liệu cục bộ."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agqo.guide import (
    CachedGuide,
    ModalQwen3Guide,
    PROMPT_CACHE_VERSION,
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_REVISION,
    TransformersQwen3Guide,
)
from agqo.walkforward import ResearchConfig, run_walkforward
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
        default=ROOT / "data/vn30_snapshot_20261002/members.csv",
        help="Đường dẫn CSV thành phần VN30.",
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
        choices=("none", "qwen3", "modal-qwen3"),
        default="none",
        help="Chọn Qwen3 chạy cục bộ, Qwen3 trên Modal, hoặc tắt hướng dẫn LLM.",
    )
    parser.add_argument(
        "--guide-cache",
        type=Path,
        default=ROOT / "results/final/qwen3_decisions.json",
        help="Tệp lưu lời khuyên LLM đã xác thực để tránh gọi lại cùng tín hiệu.",
    )
    parser.add_argument(
        "--qwen3-model",
        default=os.environ.get("AGQO_QWEN3_MODEL", QWEN3_MODEL_NAME),
        help="Tên mô hình Qwen3 trên Hugging Face; mặc định Qwen/Qwen3-8B.",
    )
    parser.add_argument(
        "--qwen3-revision",
        default=os.environ.get("AGQO_QWEN3_REVISION", QWEN3_MODEL_REVISION),
        help="Mã phiên bản Hugging Face; mặc định ghim vào phiên bản đã kiểm tra.",
    )
    parser.add_argument(
        "--qwen3-modal-app",
        default=os.environ.get("AGQO_QWEN3_MODAL_APP", "agqo-qwen3-guide"),
        help="Tên ứng dụng Modal đã triển khai cho Qwen3.",
    )
    parser.add_argument(
        "--qwen3-modal-function",
        default=os.environ.get("AGQO_QWEN3_MODAL_FUNCTION", "guide_qaoa_policy"),
        help="Tên hàm Qwen3 trong ứng dụng Modal.",
    )
    args = parser.parse_args()

    guide = None
    if args.llm_guide == "qwen3":
        model_name = args.qwen3_model
        qwen_guide = TransformersQwen3Guide(
            model_name=model_name,
            revision=args.qwen3_revision,
        )
        guide = CachedGuide(
            qwen_guide,
            args.guide_cache,
            cache_namespace=(
                f"{PROMPT_CACHE_VERSION}:transformers:{model_name}:"
                f"{qwen_guide.model_revision}"
            ),
        )
    elif args.llm_guide == "modal-qwen3":
        model_name, revision = args.qwen3_model, args.qwen3_revision
        guide = CachedGuide(
            ModalQwen3Guide(
                app_name=args.qwen3_modal_app,
                function_name=args.qwen3_modal_function,
                model_name=model_name,
                revision=revision,
            ),
            args.guide_cache,
            cache_namespace=(
                f"{PROMPT_CACHE_VERSION}:modal-qwen3:{args.qwen3_modal_app}:"
                f"{args.qwen3_modal_function}:{model_name}:{revision}"
            ),
        )
    result = run_walkforward(args.data, args.members, args.json, ResearchConfig(), guide=guide)
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
        agqo = result["portfolio"]["performance"]["AGQO Qwen→giám sát→QAOA / chính sách thích nghi"]["metrics"]
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
