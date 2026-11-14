#!/usr/bin/env python3
"""Gửi một payload tổng hợp duy nhất để kiểm tra kết nối Qwen3.8-27B trên Modal."""

from __future__ import annotations

import json
import os

from agqo.guide import (
    QWEN38_MODAL_APP,
    QWEN38_MODAL_CLASS,
    QWEN38_MODEL_NAME,
    QWEN38_MODEL_REVISION,
    QWEN38_REASONING_EFFORT,
    PROMPT_CACHE_VERSION,
    ModalQwenGuide,
    policy_catalog,
    validate_guidance,
)
from agqo.insights import insight_code_rules


def main() -> int:
    guide = ModalQwenGuide(
        app_name=os.environ.get("AGQO_QWEN38_MODAL_APP", QWEN38_MODAL_APP),
        class_name=os.environ.get("AGQO_QWEN38_MODAL_CLASS", QWEN38_MODAL_CLASS),
        model_name=os.environ.get("AGQO_QWEN38_MODEL", QWEN38_MODEL_NAME),
        revision=os.environ.get("AGQO_QWEN38_REVISION", QWEN38_MODEL_REVISION),
        reasoning_effort=os.environ.get("AGQO_QWEN38_REASONING_EFFORT", QWEN38_REASONING_EFFORT),
    )
    catalog = policy_catalog()
    policy_evidence = [
        {
            "id": item["policy_id"],
            "n": item["n_qubits"],
            "k": 6,
            "mixer": item["mixer"],
            "layout": item["mixer_layout"],
            "p": item["depth"],
            "lambda": item["risk_aversion"],
            "shrinkage": item["shrinkage"],
            "shots": item["shots"],
            "closed_periods": 0,
        }
        for item in catalog
    ]
    evidence_ids = ["MKT:VOLATILITY", "MKT:TREND", "MKT:CROSS_SECTION", "MKT:LIQUIDITY"]
    evidence_ids.extend(f"POLICY:{row['id']}" for row in policy_evidence)
    payload = {
        "prompt_version": PROMPT_CACHE_VERSION,
        "as_of_date": "2026-08-31",
        "information_cutoff": "Synthetic aggregate payload for endpoint verification only.",
        "market": {
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
            "candidate_group_fraction": {"Banks": 0.33, "Other": 0.67},
            "candidate_median_daily_traded_value_proxy_vnd": 1_000_000_000,
            "candidate_min_daily_traded_value_proxy_vnd": 300_000_000,
            "candidate_max_daily_traded_value_proxy_vnd": 2_000_000_000,
        },
        "comparators": {},
        "submodels": {
            "regime_classifier": {
                "model": "scikit-learn LogisticRegression with StandardScaler",
                "target": "Whether forward 21-session VN30 realized volatility exceeds the training-only 70th percentile.",
                "output": "High-volatility probability only; not a return forecast.",
                "reliability_to_date": {
                    "matured_monthly_signals": 0,
                    "brier_score": None,
                    "expanding_training_prevalence_brier": None,
                    "brier_skill_vs_training_prevalence": None,
                    "interpretation": "No matured forecasts exist; treat this probability as unverified.",
                },
            }
        },
        "policy_candidates": policy_evidence,
        "eligible_policy_ids": ["n12_balanced_xy_ring_p1"],
        "insight_code_rules": insight_code_rules(333_333_333.33),
        "evidence_ids": evidence_ids,
        "evidence": {
            "MKT:VOLATILITY": {"p_high_volatility": 0.75, "vol_20d": 0.32, "ratio_20d_120d": 1.45},
            "MKT:TREND": {"return_20d": -0.04, "return_60d": -0.02},
            "MKT:CROSS_SECTION": {"mean_correlation": 0.58, "positive_fraction_20d": 0.33},
            "MKT:LIQUIDITY": {"eligible_n": 29, "candidate_pool_n": 16, "median_daily_value_vnd": 1_000_000_000},
            **{f"POLICY:{row['id']}": {"closed_periods": 0} for row in policy_evidence},
        },
        "qaoa_objective_specification": {
            "formula": "minimize lambda * (x^T Sigma_alpha x) / K^2 - (mu^T x) / K + annualized modeled transaction cost",
            "transaction_fee_bps_per_side": 25.0,
            "rebalances_per_year": 12,
            "previous_weight_source": "Verification payload; not backtest evidence.",
        },
        "decision_rule": (
            "Verify that the response selects one catalog policy; do not treat this payload as evidence of financial performance."
        ),
    }
    envelope = guide(payload)
    from agqo.guide import enrich_guide_payload
    enriched = enrich_guide_payload(payload)
    decision = validate_guidance(
        envelope.get("decision", {}),
        set(evidence_ids),
        set(enriched["eligible_policy_ids"]),
        set(enriched["allowed_insight_codes"]),
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "model": envelope.get("model"),
                "model_revision": envelope.get("model_revision"),
                "quantization": envelope.get("quantization"),
                "serving": envelope.get("serving"),
                "generation": envelope.get("generation"),
                "latency_seconds": envelope.get("latency_seconds"),
                "validation_repairs": envelope.get("validation_repairs"),
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
