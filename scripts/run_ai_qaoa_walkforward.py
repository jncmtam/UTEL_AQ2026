#!/usr/bin/env python3
"""Chạy kiểm định AI–QAOA và dựng báo cáo, biểu đồ từ dữ liệu cục bộ."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agqo.guide import (
    CachedGuide,
    ModalGuide,
    PROMPT_CACHE_VERSION,
    TransformersQwen3Guide,
)
from agqo.walkforward import ResearchConfig, run_walkforward
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
        default=ROOT / "results/vn30_ai_qaoa_walkforward.json",
        help="Tệp kết quả chi tiết dạng JSON.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "results/BAO_CAO_AI_QAOA_WALK_FORWARD.md",
        help="Tệp báo cáo tiếng Việt.",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "results/figures/walkforward",
        help="Thư mục lưu biểu đồ.",
    )
    parser.add_argument(
        "--llm-guide",
        choices=("none", "modal", "qwen3"),
        default="none",
        help="Bật bộ điều khiển Qwen3 cục bộ (trong Modal Notebook) hoặc bộ OpenAI Modal cũ.",
    )
    parser.add_argument(
        "--guide-cache",
        type=Path,
        default=ROOT / "results/agqo_llm_decisions.json",
        help="Tệp lưu lời khuyên LLM đã xác thực để tránh gọi lại cùng tín hiệu.",
    )
    parser.add_argument("--modal-app", default="agqo-llm-guide")
    parser.add_argument("--modal-function", default="guide_qaoa_policy")
    parser.add_argument(
        "--qwen3-model",
        default=os.environ.get("AGQO_QWEN3_MODEL", "Qwen/Qwen3-4B"),
        help="Tên mô hình Qwen3 trên Hugging Face; mặc định Qwen/Qwen3-4B.",
    )
    parser.add_argument(
        "--qwen3-revision",
        default=os.environ.get("AGQO_QWEN3_REVISION"),
        help="Mã nhánh hoặc mã phiên bản Hugging Face; để trống sẽ ghi lại mã đã tải.",
    )
    args = parser.parse_args()

    guide = None
    if args.llm_guide == "modal":
        model_name = os.environ.get("AGQO_LLM_MODEL", "gpt-5-mini")
        guide = CachedGuide(
            ModalGuide(args.modal_app, args.modal_function, model_name=model_name),
            args.guide_cache,
            cache_namespace=(
                f"{PROMPT_CACHE_VERSION}:{args.modal_app}:{args.modal_function}:"
                f"{model_name}"
            ),
        )
    elif args.llm_guide == "qwen3":
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
    result = run_walkforward(args.data, args.members, args.json, ResearchConfig(), guide=guide)
    figures = build_walkforward_plots(args.json, args.figures)
    report = write_walkforward_report(args.json, args.report)
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
        agqo = result["portfolio"]["performance"]["AGQO LLM→QAOA / chính sách thích nghi / 12 mã thanh khoản cao"]["metrics"]
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
