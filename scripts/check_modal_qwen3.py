#!/usr/bin/env python3
"""Gửi một payload tổng hợp duy nhất để kiểm tra kết nối Qwen3 trên Modal."""

from __future__ import annotations

import json
import os

from agqo.guide import (
    ModalQwen3Guide,
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_REVISION,
    policy_catalog,
    validate_guidance,
)


def main() -> int:
    app_name = os.environ.get("AGQO_QWEN3_MODAL_APP", "agqo-qwen3-guide")
    function_name = os.environ.get(
        "AGQO_QWEN3_MODAL_FUNCTION", "guide_qaoa_policy"
    )
    model_name = os.environ.get("AGQO_QWEN3_MODEL", QWEN3_MODEL_NAME)
    revision = os.environ.get("AGQO_QWEN3_REVISION", QWEN3_MODEL_REVISION)
    guide = ModalQwen3Guide(app_name, function_name, model_name, revision)
    payload = {
        "as_of_date": "2026-08-31",
        "information_cutoff": "Payload tổng hợp giả lập chỉ để kiểm tra dịch vụ.",
        "market_insights": {
            "ai_high_volatility_probability": 0.75,
            "vn30_annualized_volatility_20d": 0.32,
            "vn30_annualized_volatility_60d": 0.27,
            "vn30_annualized_volatility_120d": 0.22,
            "vn30_return_20d": -0.04,
            "vn30_return_60d": -0.02,
            "volatility_ratio_20d_to_120d": 1.45,
            "mean_pairwise_correlation_252d": 0.58,
            "90th_percentile_pairwise_correlation_252d": 0.81,
            "cross_sectional_20d_return_dispersion": 0.06,
            "fraction_stocks_positive_20d": 0.33,
            "bank_fraction_of_eligible_stocks": 0.30,
            "candidate_group_fraction": {"Ngân hàng": 0.33, "Khác": 0.67},
            "candidate_median_daily_traded_value_proxy_vnd": 1_000_000_000,
            "candidate_min_daily_traded_value_proxy_vnd": 300_000_000,
            "candidate_max_daily_traded_value_proxy_vnd": 2_000_000_000,
        },
        "past_completed_strategy_metrics": {},
        "past_completed_policy_benchmarks": {},
        "qaoa_objective_specification": {
            "formula": "λ(xᵀΣαx)/K² − (μᵀx)/K + chi phí đổi danh mục",
            "transaction_fee_bps_per_side": 25.0,
            "rebalances_per_year": 12,
            "previous_weight_source": "Payload kiểm tra; không phải dữ liệu kiểm định.",
        },
        "policy_catalog": policy_catalog(),
        "selection_objective": (
            "Chỉ kiểm tra khả năng trả về một cấu hình thuộc danh mục; "
            "không dùng payload này làm bằng chứng hiệu quả tài chính."
        ),
    }
    envelope = guide(payload)
    decision = validate_guidance(envelope.get("decision", {}))
    print(
        json.dumps(
            {
                "status": "ok",
                "model": envelope.get("model"),
                "model_revision": envelope.get("model_revision"),
                "decision": decision,
                "usage": envelope.get("usage"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
