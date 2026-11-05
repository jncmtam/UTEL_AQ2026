"""Validate LLM insight tags and render finance explanations from measured fields."""

from __future__ import annotations

from typing import Any


INSIGHT_THRESHOLDS = {
    "high_volatility_probability": 0.65,
    "minimum_matured_classifier_signals": 6,
    "minimum_positive_brier_skill": 0.0,
    "volatility_ratio_20d_to_120d": 1.25,
    "mean_pairwise_correlation_252d": 0.55,
    "cross_sectional_20d_return_dispersion": 0.04,
    "bank_fraction_of_eligible_stocks": 0.35,
}

RISK_THRESHOLDS = {
    "minimum_completed_policy_periods": 6,
    "maximum_drawdown": -0.15,
    "mean_two_way_turnover": 1.0,
    "mean_normalized_regret": 0.10,
}

_INSIGHT_EVIDENCE = {
    "high_volatility": ("MKT:VOLATILITY",),
    "volatility_rising": ("MKT:VOLATILITY",),
    "high_correlation": ("MKT:CROSS_SECTION",),
    "high_dispersion": ("MKT:CROSS_SECTION",),
    "bank_concentration": ("MKT:CROSS_SECTION",),
    "low_liquidity": ("MKT:LIQUIDITY",),
    "mixed_signals": ("MKT:VOLATILITY", "MKT:CROSS_SECTION"),
}


def insight_code_rules(liquidity_threshold_vnd: float) -> dict[str, dict[str, Any]]:
    """Return explicit descriptive thresholds shared with the English prompt."""
    return {
        "high_volatility": {
            "condition": "AI high-volatility probability >= threshold, at least minimum_matured_signals exist, and Brier skill is positive.",
            "threshold": INSIGHT_THRESHOLDS["high_volatility_probability"],
            "minimum_matured_signals": INSIGHT_THRESHOLDS["minimum_matured_classifier_signals"],
            "minimum_brier_skill": INSIGHT_THRESHOLDS["minimum_positive_brier_skill"],
        },
        "volatility_rising": {
            "condition": "20-session to 120-session annualized volatility ratio >= threshold.",
            "threshold": INSIGHT_THRESHOLDS["volatility_ratio_20d_to_120d"],
        },
        "high_correlation": {
            "condition": "Trailing mean pairwise correlation >= threshold.",
            "threshold": INSIGHT_THRESHOLDS["mean_pairwise_correlation_252d"],
        },
        "high_dispersion": {
            "condition": "Cross-sectional standard deviation of compounded 20-session stock returns >= threshold.",
            "threshold": INSIGHT_THRESHOLDS["cross_sectional_20d_return_dispersion"],
        },
        "bank_concentration": {
            "condition": "Bank share of eligible stocks >= threshold.",
            "threshold": INSIGHT_THRESHOLDS["bank_fraction_of_eligible_stocks"],
        },
        "low_liquidity": {
            "condition": "Median candidate close-times-volume proxy over the prior 20 sessions < minimum daily value needed to fill one equal-weight position at the configured participation limit.",
            "threshold_vnd": float(liquidity_threshold_vnd),
        },
        "mixed_signals": {
            "condition": "Use only when none of the other insight conditions are supported.",
        },
    }


def support_insight_codes(
    payload: dict[str, Any], proposed_codes: list[str]
) -> tuple[list[str], list[str]]:
    """Remove insight tags whose explicit project thresholds are not met."""
    market = payload.get("market", {}) if isinstance(payload.get("market"), dict) else {}
    submodels = payload.get("submodels", {}) if isinstance(payload.get("submodels"), dict) else {}
    classifier = submodels.get("regime_classifier", {})
    reliability = classifier.get("reliability_to_date", {}) if isinstance(classifier, dict) else {}
    liquidity_rules = payload.get("insight_code_rules", {}).get("low_liquidity", {})
    liquidity_threshold = liquidity_rules.get("threshold_vnd") if isinstance(liquidity_rules, dict) else None

    probability = market.get("ai_high_volatility_probability")
    matured = reliability.get("matured_monthly_signals", 0)
    brier_skill = reliability.get("brier_skill_vs_training_prevalence")
    vol_ratio = market.get("volatility_ratio_20d_to_120d")
    correlation = market.get("mean_pairwise_correlation_252d")
    dispersion = market.get("cross_sectional_20d_return_dispersion")
    bank_fraction = market.get("bank_fraction_of_eligible_stocks")
    median_value = market.get("candidate_median_daily_traded_value_proxy_vnd")

    supports = {
        "high_volatility": (
            isinstance(probability, (int, float))
            and probability >= INSIGHT_THRESHOLDS["high_volatility_probability"]
            and isinstance(matured, int)
            and matured >= INSIGHT_THRESHOLDS["minimum_matured_classifier_signals"]
            and isinstance(brier_skill, (int, float))
            and brier_skill > INSIGHT_THRESHOLDS["minimum_positive_brier_skill"]
        ),
        "volatility_rising": (
            isinstance(vol_ratio, (int, float))
            and vol_ratio >= INSIGHT_THRESHOLDS["volatility_ratio_20d_to_120d"]
        ),
        "high_correlation": (
            isinstance(correlation, (int, float))
            and correlation >= INSIGHT_THRESHOLDS["mean_pairwise_correlation_252d"]
        ),
        "high_dispersion": (
            isinstance(dispersion, (int, float))
            and dispersion >= INSIGHT_THRESHOLDS["cross_sectional_20d_return_dispersion"]
        ),
        "bank_concentration": (
            isinstance(bank_fraction, (int, float))
            and bank_fraction >= INSIGHT_THRESHOLDS["bank_fraction_of_eligible_stocks"]
        ),
        "low_liquidity": (
            isinstance(median_value, (int, float))
            and isinstance(liquidity_threshold, (int, float))
            and median_value < liquidity_threshold
        ),
    }
    known_codes = set(supports) | {"mixed_signals"}
    valid = list(dict.fromkeys(code for code in proposed_codes if code in known_codes and (code == "mixed_signals" or supports[code])))
    repairs = []
    if len(valid) != len(proposed_codes):
        repairs.append("unsupported_insight_codes_removed")
    valid = [code for code in valid if code != "mixed_signals"]
    if not valid:
        valid = ["mixed_signals"]
        if "insight_codes_defaulted" not in repairs:
            repairs.append("insight_codes_defaulted")
    return valid, repairs


def supported_insight_codes(payload: dict[str, Any]) -> list[str]:
    """Compute the insight-code allow-list from measured fields and fixed thresholds."""
    proposed = [
        "high_volatility",
        "volatility_rising",
        "high_correlation",
        "high_dispersion",
        "bank_concentration",
        "low_liquidity",
        "mixed_signals",
    ]
    supported, _ = support_insight_codes(payload, proposed)
    return supported


def derive_risk_flags(payload: dict[str, Any], policy_id: str) -> list[str]:
    """Create risk flags from the same past-only evidence used by the guardrail."""
    evidence = payload.get("evidence", {}) if isinstance(payload.get("evidence"), dict) else {}
    policy = evidence.get(f"POLICY:{policy_id}", {})
    if not isinstance(policy, dict):
        policy = {}
    flags = []
    if int(policy.get("closed_periods", 0) or 0) < RISK_THRESHOLDS["minimum_completed_policy_periods"]:
        flags.append("short_history")
    submodels = payload.get("submodels", {}) if isinstance(payload.get("submodels"), dict) else {}
    classifier = submodels.get("regime_classifier", {})
    reliability = classifier.get("reliability_to_date", {}) if isinstance(classifier, dict) else {}
    matured = reliability.get("matured_monthly_signals", 0)
    brier_skill = reliability.get("brier_skill_vs_training_prevalence")
    if (
        not isinstance(matured, int)
        or matured < INSIGHT_THRESHOLDS["minimum_matured_classifier_signals"]
        or not isinstance(brier_skill, (int, float))
        or brier_skill <= 0
    ):
        flags.append("weak_ai_forecast")
    drawdown = policy.get("max_drawdown")
    turnover = policy.get("turnover")
    regret = policy.get("mean_regret")
    if isinstance(drawdown, (int, float)) and drawdown <= RISK_THRESHOLDS["maximum_drawdown"]:
        flags.append("high_drawdown")
    if isinstance(turnover, (int, float)) and turnover >= RISK_THRESHOLDS["mean_two_way_turnover"]:
        flags.append("high_turnover")
    if isinstance(regret, (int, float)) and regret >= RISK_THRESHOLDS["mean_normalized_regret"]:
        flags.append("high_regret")
    return flags


def render_grounded_narrative(
    payload: dict[str, Any],
    proposed_policy_id: str,
    executed_policy_id: str,
    insight_codes: list[str],
    risk_flags: list[str],
    guardrail_reason: str | None,
) -> tuple[str, str]:
    """Build Vietnamese decision text from validated values and fixed phrases."""
    market = payload.get("market", {}) if isinstance(payload.get("market"), dict) else {}
    policy_rows = payload.get("policy_candidates", [])
    policy = next(
        (row for row in policy_rows if isinstance(row, dict) and row.get("id") == proposed_policy_id),
        {},
    )
    n = policy.get("n", "?")
    mixer = policy.get("mixer", "?")
    layout = policy.get("layout", "?")
    depth = policy.get("p", "?")
    gate_count = policy.get("logical_total_two_qubit_gate_count")
    gate_text = f", khoảng {gate_count} cổng hai qubit logic mỗi mạch" if isinstance(gate_count, int) else ""
    insight_text = []
    for code in insight_codes:
        if code == "high_volatility":
            probability = market.get("ai_high_volatility_probability")
            insight_text.append(f"xác suất biến động cao {probability:.0%} với Brier skill dương")
        elif code == "volatility_rising":
            ratio = market.get("volatility_ratio_20d_to_120d")
            insight_text.append(f"tỷ số biến động 20/120 phiên là {ratio:.2f}")
        elif code == "high_correlation":
            correlation = market.get("mean_pairwise_correlation_252d")
            insight_text.append(f"tương quan cặp trung bình là {correlation:.2f}")
        elif code == "high_dispersion":
            dispersion = market.get("cross_sectional_20d_return_dispersion")
            insight_text.append(f"độ phân tán lợi suất 20 phiên là {dispersion:.1%}")
        elif code == "bank_concentration":
            fraction = market.get("bank_fraction_of_eligible_stocks")
            insight_text.append(f"ngân hàng chiếm {fraction:.1%} rổ đủ điều kiện")
        elif code == "low_liquidity":
            value = market.get("candidate_median_daily_traded_value_proxy_vnd")
            threshold = payload.get("insight_code_rules", {}).get("low_liquidity", {}).get("threshold_vnd")
            insight_text.append(
                f"trung vị giá trị giao dịch đại diện {value:,.0f} đồng thấp hơn ngưỡng lấp đầy {threshold:,.0f} đồng"
            )
        elif code == "mixed_signals":
            insight_text.append("chưa có điều kiện cảnh báo nào vượt ngưỡng đã định")
    if not insight_text:
        insight_text.append("chưa có điều kiện cảnh báo nào vượt ngưỡng đã định")
    rationale = (
        f"Đề xuất {n} qubit, bộ trộn {mixer}/{layout}, p={depth}{gate_text}; "
        + "; ".join(insight_text)
        + "."
    )

    risk_text = []
    if "short_history" in risk_flags:
        risk_text.append("Chính sách chưa có đủ sáu kỳ đã khép.")
    if "weak_ai_forecast" in risk_flags:
        risk_text.append("Brier skill của bộ dự báo không dương hoặc chưa đủ sáu tín hiệu tháng đã trưởng thành.")
    if "high_drawdown" in risk_flags:
        risk_text.append("Sụt giảm lịch sử vượt ngưỡng 15%.")
    if "high_turnover" in risk_flags:
        risk_text.append("Doanh số giao dịch hai chiều bình quân từ 100% vốn mỗi kỳ.")
    if "high_regret" in risk_flags:
        risk_text.append("Sai lệch mục tiêu QAOA bình quân từ 10%.")
    if guardrail_reason:
        if "fewer than 6 completed outcomes" in guardrail_reason:
            risk_text.append("Bộ giám sát dùng cấu hình khởi động vì thiếu lịch sử.")
        elif "regret exceeds 10%" in guardrail_reason:
            risk_text.append("Bộ giám sát chuyển sang đối chứng vì regret cao.")
        elif "feasible-shot rate" in guardrail_reason:
            risk_text.append("Bộ giám sát chuyển sang đối chứng vì tỷ lệ mẫu khả thi thấp.")
        elif "risk-adjusted utility" in guardrail_reason:
            risk_text.append("Bộ giám sát chuyển sang đối chứng vì lợi ích lịch sử kém hơn.")
    if executed_policy_id != proposed_policy_id:
        risk_text.append(f"Cấu hình thực thi: {executed_policy_id}.")
    if not risk_text:
        risk_text.append("Kết quả lịch sử chưa bảo đảm lợi nhuận trong tương lai.")
    return rationale, " ".join(risk_text)
