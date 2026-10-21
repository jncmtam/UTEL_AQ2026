"""Thí nghiệm walk-forward nối dự báo AI, tối ưu QAOA và kiểm định tài chính."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import combinations
from math import comb
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from .ai import fit_regime_model, fit_regime_model_as_of, forward_volatility, regime_controls
from .estimators import (
    build_ledoit_wolf_problem,
    build_regime_problem,
    estimate_annual_inputs,
)
from .evaluation import compare_monthly_returns, summarize_monthly_returns
from .guide import (
    POLICIES,
    PROMPT_CACHE_VERSION,
    enrich_guide_payload,
    policy_catalog,
    validate_guidance,
)
from .knowledge import CORPUS_VERSION
from .insights import (
    derive_risk_flags,
    insight_code_rules,
    render_grounded_narrative,
    support_insight_codes,
)
from .market_data import load_market_dataset
from .news import load_news_records, summarize_news_as_of
from .universe import load_membership_history, members_as_of
from .problem import (
    PortfolioProblem,
    anneal_solve,
    build_qubo,
    exact_solve_vectorized,
    greedy_solve,
)
from .simulator import mixer_edges_for_problem, optimize_qaoa


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGQO_STRATEGY_NAME = "AGQO Qwen→giám sát→QAOA / chính sách thích nghi"
RULE_STRATEGY_NAME = "Bộ chọn quy tắc→QAOA / đối chứng không LLM"
POLICY_STRATEGY_PREFIX = "Đối chứng chính sách QAOA cố định / "


def _policy_strategy_name(policy_id: str) -> str:
    policy = POLICIES[policy_id]
    return (
        f"{POLICY_STRATEGY_PREFIX}{policy_id} / {policy.n_qubits} qubit / "
        f"{policy.mixer}-{policy.mixer_layout} p={policy.depth}"
    )


def _choose_rule_policy(
    past_policy_metrics: dict[str, dict[str, Any]],
    past_qaoa_rows: list[dict[str, Any]],
    minimum_periods: int = 6,
) -> str:
    """Chọn chính sách bằng điểm quá khứ đã khóa; thời kỳ khởi động dùng cấu hình nông."""
    warmup_id = "n12_balanced_xy_ring_p1"
    usable: list[tuple[float, int, int, str]] = []
    for policy_id, metrics in past_policy_metrics.items():
        if metrics.get("completed_periods", 0) < minimum_periods:
            continue
        regrets = [
            float(row["normalized_objective_regret"])
            for row in past_qaoa_rows
            if row.get("policy_id") == policy_id
            and row.get("normalized_objective_regret") is not None
        ]
        if len(regrets) < minimum_periods:
            continue
        sharpe = metrics.get("annualized_sharpe_to_date")
        drawdown = metrics.get("max_drawdown_to_date")
        turnover = metrics.get("mean_two_way_turnover")
        if sharpe is None or not np.isfinite(sharpe):
            continue
        utility = (
            float(sharpe)
            - 1.5 * abs(float(drawdown or 0.0))
            - 2.0 * float(np.mean(regrets))
            - 0.10 * float(turnover or 0.0)
        )
        policy = POLICIES[policy_id]
        usable.append((utility, -policy.n_qubits, -policy.depth, policy_id))
    if not usable:
        return warmup_id
    return max(usable)[-1]


def _policy_quality_snapshot(
    policy_id: str,
    past_policy_metrics: dict[str, dict[str, Any]],
    past_qaoa_rows: list[dict[str, Any]],
    minimum_periods: int = 6,
) -> dict[str, float | int | None]:
    """Summarize a policy using only completed outcomes available at this signal."""
    metrics = past_policy_metrics.get(policy_id, {})
    rows = [
        row for row in past_qaoa_rows
        if row.get("policy_id") == policy_id
        and row.get("exit_date")
        and row.get("normalized_objective_regret") is not None
    ]
    regrets = [float(row["normalized_objective_regret"]) for row in rows]
    feasible = [
        float(row["best_sampled_feasible_probability"])
        for row in rows if row.get("best_sampled_feasible_probability") is not None
    ]
    sharpe = metrics.get("annualized_sharpe_to_date")
    drawdown = metrics.get("max_drawdown_to_date")
    turnover = metrics.get("mean_two_way_turnover")
    utility = None
    if sharpe is not None and np.isfinite(sharpe) and regrets:
        utility = (
            float(sharpe)
            - 1.5 * abs(float(drawdown or 0.0))
            - 2.0 * float(np.mean(regrets))
            - 0.10 * float(turnover or 0.0)
        )
    return {
        "completed_periods": min(int(metrics.get("completed_periods", 0)), len(rows)),
        "mean_regret": float(np.mean(regrets)) if regrets else None,
        "feasible_probability": float(np.mean(feasible)) if feasible else None,
        "sharpe": float(sharpe) if sharpe is not None and np.isfinite(sharpe) else None,
        "max_drawdown": float(drawdown) if drawdown is not None else None,
        "utility": utility,
    }


def _supervise_policy_proposal(
    proposed_policy_id: str,
    rule_policy_id: str,
    past_policy_metrics: dict[str, dict[str, Any]],
    past_qaoa_rows: list[dict[str, Any]],
    minimum_periods: int = 6,
) -> tuple[str, str | None, dict[str, Any]]:
    """Keep LLM proposals only when their available evidence passes numeric guardrails."""
    proposed = _policy_quality_snapshot(
        proposed_policy_id, past_policy_metrics, past_qaoa_rows, minimum_periods
    )
    rule = _policy_quality_snapshot(
        rule_policy_id, past_policy_metrics, past_qaoa_rows, minimum_periods
    )
    reason = None
    if proposed_policy_id != rule_policy_id:
        if proposed["completed_periods"] < minimum_periods:
            reason = f"The proposed policy has fewer than {minimum_periods} completed outcomes."
        elif rule["completed_periods"] < minimum_periods:
            reason = f"The rule comparator has fewer than {minimum_periods} completed outcomes; use the warm-up policy."
        elif (
            proposed["feasible_probability"] is not None
            and rule["feasible_probability"] is not None
            and proposed["feasible_probability"] < 0.90
            and proposed["feasible_probability"] + 0.05 < rule["feasible_probability"]
        ):
            reason = "The proposal's measured feasible-shot rate is below 90% and trails the rule comparator by over 5 percentage points."
        elif (
            proposed["mean_regret"] is not None
            and rule["mean_regret"] is not None
            and proposed["mean_regret"] > 0.10
            and proposed["mean_regret"] > rule["mean_regret"] + 0.05
        ):
            reason = "The proposal's mean normalized objective regret exceeds 10% and trails the rule comparator by over 5 percentage points."
        elif (
            proposed["utility"] is not None
            and rule["utility"] is not None
            and proposed["utility"] < rule["utility"] - 0.25
            and proposed["max_drawdown"] is not None
            and rule["max_drawdown"] is not None
            and proposed["max_drawdown"] < rule["max_drawdown"] - 0.03
        ):
            reason = "Historical risk-adjusted utility trails the rule comparator by over 0.25 and drawdown is over 3 percentage points worse."
    executed = (
        "n12_balanced_xy_ring_p1"
        if reason and rule["completed_periods"] < minimum_periods
        else rule_policy_id if reason else proposed_policy_id
    )
    return executed, reason, {"proposed": proposed, "rule": rule}


@dataclass(frozen=True)
class ResearchConfig:
    train_end: str = "2024-10-31"
    validation_start: str = "2024-11-01"
    validation_end: str = "2025-04-30"
    test_start: str = "2025-05-01"
    test_last_signal: str = "2026-08-31"
    horizon: int = 21
    lookback: int = 252
    min_history: int = 126
    k: int = 6
    qaoa_candidates: int = 12
    agqo_candidate_pool: int = 16
    capital_vnd: float = 100_000_000.0
    fee_bps: float = 25.0
    adtv_participation: float = 0.05
    qaoa_seeds: tuple[int, ...] = (11, 23, 47)
    qaoa_shots: int = 1024
    qaoa_max_evaluations: int = 100


def _load_panels(data_path: str | Path, members_path: str | Path):
    data, members = load_market_dataset(
        data_path,
        members_path,
        require_point_in_time_membership=True,
        require_adjusted_prices=True,
    )
    membership_history = load_membership_history(members_path)
    stock = data.loc[data.instrument_type == "stock"]
    index = data.loc[data.instrument_type == "index"]
    index_open = index.pivot(index="date", columns="ticker", values="open").sort_index()
    index_close = index.pivot(index="date", columns="ticker", values="close").sort_index()
    dates = index_close[["VN30", "VNINDEX"]].dropna().index
    index_open = index_open.reindex(index=dates, columns=["VN30", "VNINDEX"])
    index_close = index_close.reindex(index=dates, columns=["VN30", "VNINDEX"])
    stock_close = stock.pivot(index="date", columns="ticker", values="close").reindex(
        index=dates
    ).sort_index()
    stock_adjusted_open = stock.pivot(
        index="date", columns="ticker", values="open_adjusted"
    ).reindex(index=dates).sort_index()
    tickers = tuple(stock_close.columns.astype(str))
    stock_open = stock.pivot(index="date", columns="ticker", values="open").reindex(
        index=dates, columns=tickers
    ).sort_index()
    stock_close = stock_close.reindex(columns=tickers)
    stock_adjusted_open = stock_adjusted_open.reindex(columns=tickers)
    stock_adjusted_close = stock.pivot(
        index="date", columns="ticker", values="close_adjusted"
    ).reindex(index=dates, columns=tickers).sort_index()
    volume = stock.pivot(index="date", columns="ticker", values="volume").reindex(
        index=dates, columns=tickers
    ).sort_index()
    stock_returns = stock_adjusted_close.pct_change(fill_method=None)
    index_returns = index_close["VN30"].pct_change(fill_method=None).rename("VN30")
    traded_value = stock_close * volume
    return (
        data, members, membership_history, dates, stock_open, stock_adjusted_open,
        stock_close, stock_returns,
        index_open, index_close, index_returns, traded_value,
    )


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).expanduser().resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).name


def _index_features(index_returns: pd.Series) -> pd.DataFrame:
    """Đặc trưng AI chỉ dùng chỉ số VN30, không phụ thuộc rổ thành phần hiện tại."""
    result = pd.DataFrame(index=index_returns.index)
    for window in (20, 60, 120):
        result[f"vol_{window}"] = (
            index_returns.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(252)
        )
    for window in (20, 60):
        result[f"return_{window}"] = np.expm1(
            index_returns.rolling(window, min_periods=window).sum()
        )
    result["vol_ratio_20_120"] = result["vol_20"] / result["vol_120"].clip(lower=1e-12)
    return result


def _calendar_signals(dates: pd.DatetimeIndex, start: str, last_signal: str):
    last_month = pd.Timestamp(last_signal).to_period("M")
    exit_signal_cutoff = (last_month + 1).end_time.normalize()
    candidates = pd.Series(dates, index=dates.to_period("M")).groupby(level=0).last()
    signals = pd.DatetimeIndex(
        [date for date in candidates if pd.Timestamp(start) <= date <= exit_signal_cutoff]
    )
    execution = []
    for signal in signals:
        later = dates[dates > signal]
        if len(later):
            execution.append(later[0])
    signal_execution = dict(zip(signals[: len(execution)], execution))
    paired = []
    ordered = list(signal_execution)
    for current, following in zip(ordered[:-1], ordered[1:]):
        if current.to_period("M") <= last_month:
            paired.append((current, signal_execution[current], signal_execution[following]))
    return paired


def _eligible_universe(
    signal: pd.Timestamp,
    tickers: tuple[str, ...],
    stock_returns: pd.DataFrame,
    traded_value: pd.DataFrame,
    config: ResearchConfig,
    membership_history: pd.DataFrame | None = None,
):
    history = stock_returns.loc[:signal].tail(config.lookback)
    if membership_history is None:
        active_tickers = set(tickers)
    else:
        active_tickers = set(members_as_of(membership_history, signal)["ticker"].astype(str))
    eligible = tuple(
        ticker for ticker in tickers
        if ticker in active_tickers and int(history[ticker].count()) >= config.min_history
    )
    complete = history.loc[:, eligible].dropna(how="any")
    if len(complete) < config.min_history:
        raise ValueError(
            f"Chỉ còn {len(complete)} phiên hoàn chỉnh tại {signal.date()}, "
            f"thấp hơn ngưỡng {config.min_history}."
        )
    liq = traded_value.loc[:signal].tail(20).mean().reindex(eligible).dropna()
    pool_size = max(config.qaoa_candidates, config.agqo_candidate_pool)
    candidates = tuple(liq.sort_values(ascending=False, kind="stable").head(pool_size).index)
    if len(candidates) != pool_size:
        raise ValueError(f"Tại {signal.date()} chỉ có {len(candidates)} mã đủ thanh khoản cho AGQO.")
    return complete, eligible, candidates, liq


def _build_problem(
    returns: pd.DataFrame,
    tickers: tuple[str, ...],
    probability: float,
    variant: str,
    k: int,
):
    if variant == "fixed":
        return build_regime_problem(
            returns, tickers, 0.5, k=k, ai_enabled=False, transaction_cost_bps=0.0
        )
    if variant == "ai_both":
        return build_regime_problem(returns, tickers, probability, k=k, ai_enabled=True)
    if variant == "ai_lambda":
        return build_regime_problem(
            returns, tickers, probability, k=k, ai_enabled=True,
            adaptive_lambda=True, adaptive_shrinkage=False,
        )
    if variant == "ai_alpha":
        return build_regime_problem(
            returns, tickers, probability, k=k, ai_enabled=True,
            adaptive_lambda=False, adaptive_shrinkage=True,
        )
    if variant == "ledoit_wolf":
        return build_ledoit_wolf_problem(returns, tickers, k=k, risk_aversion=5.0)
    raise ValueError(f"Phiên bản mục tiêu không hợp lệ: {variant}")


def _build_policy_problem(
    returns: pd.DataFrame,
    tickers: tuple[str, ...],
    policy_id: str,
    k: int,
    previous_tickers: tuple[str, ...] = (),
    fee_bps: float = 25.0,
    rebalances_per_year: int = 12,
) -> PortfolioProblem:
    """Dựng mục tiêu AGQO, gồm rủi ro, lợi nhuận và phí đổi danh mục năm hóa."""
    policy = POLICIES[policy_id]
    mu, covariance = estimate_annual_inputs(returns, "sample")
    covariance = (1 - policy.shrinkage) * covariance + policy.shrinkage * np.diag(
        np.diag(covariance)
    )
    previous_weights = np.asarray(
        [1 / k if ticker in previous_tickers else 0.0 for ticker in tickers],
        dtype=float,
    )
    outside_previous_weight = sum(ticker not in tickers for ticker in previous_tickers) / k
    return PortfolioProblem(
        tickers=tickers,
        mu=mu,
        covariance=covariance,
        k=k,
        risk_aversion=policy.risk_aversion,
        previous_weights=previous_weights,
        transaction_costs=np.full(len(tickers), fee_bps / 10_000, dtype=float),
        rebalances_per_year=rebalances_per_year,
        outside_previous_weight=outside_previous_weight,
        outside_transaction_cost_rate=fee_bps / 10_000,
    )


def _past_strategy_metrics(
    signal: pd.Timestamp,
    strategy_targets: dict[str, list[tuple[str, ...]]],
    tickers: tuple[str, ...],
    stock_open: pd.DataFrame,
    adjusted_open: pd.DataFrame,
    entries: list[pd.Timestamp],
    exits: list[pd.Timestamp],
    liquidities: list[pd.Series],
    config: ResearchConfig,
) -> dict[str, dict[str, Any]]:
    """Chỉ trả kết quả danh mục đã thoát lệnh trước ngày tín hiệu hiện tại."""
    completed = sum(exit_date <= signal for exit_date in exits)
    if completed == 0:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for name, targets in strategy_targets.items():
        if len(targets) < completed:
            continue
        ledger = _capacity_ledger(
            targets[:completed], tickers, stock_open, adjusted_open,
            entries[:completed], exits[:completed], liquidities[:completed],
            config, config.fee_bps, config.adtv_participation,
        )
        values = ledger.net_return.to_numpy(dtype=float)
        stats = summarize_monthly_returns(ledger.net_return)
        tail3 = values[-3:]
        tail6 = values[-6:]
        result[name] = {
            "completed_periods": int(len(values)),
            "trailing_3_period_net_return": float(np.prod(1 + tail3) - 1),
            "trailing_6_period_net_return": float(np.prod(1 + tail6) - 1),
            "cagr_to_date": float(stats["cagr"]),
            "annualized_sharpe_to_date": (
                float(stats["sharpe"]) if np.isfinite(stats["sharpe"]) else None
            ),
            "sortino_to_date": (
                float(stats["sortino"]) if np.isfinite(stats["sortino"]) else None
            ),
            "max_drawdown_to_date": float(stats["max_drawdown"]),
            "monthly_var_95_to_date": float(stats["monthly_var_95"]),
            "monthly_cvar_95_to_date": float(stats["monthly_cvar_95"]),
            "profit_factor_to_date": stats["profit_factor"],
            "positive_month_fraction_to_date": float(stats["positive_month_fraction"]),
            "mean_two_way_turnover": float(ledger.executed_turnover.mean()),
            "total_transaction_cost_vnd": float(ledger.transaction_cost_vnd.sum()),
        }
    return result


def _build_agqo_payload(
    signal: pd.Timestamp,
    features: pd.DataFrame,
    probability: float,
    returns: pd.DataFrame,
    eligible: tuple[str, ...],
    candidates: tuple[str, ...],
    liquidity: pd.Series,
    groups: dict[str, str],
    past_strategy_metrics: dict[str, dict[str, Any]],
    past_policy_metrics: dict[str, dict[str, Any]],
    past_qaoa_rows: list[dict[str, Any]],
    signal_history: list[dict[str, Any]],
    fee_bps: float,
    capital_vnd: float,
    adtv_participation: float,
    k: int,
    news_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tạo bảng chứng cứ gọn, có mã tham chiếu để LLM hướng dẫn QAOA."""
    values = returns.loc[:, eligible]
    correlation = values.corr().to_numpy(dtype=float)
    upper = correlation[np.triu_indices_from(correlation, k=1)]
    recent = (1 + values.tail(20)).prod(axis=0) - 1
    candidate_liquidity = liquidity.reindex(candidates).dropna()
    bank_share = float(np.mean([groups.get(ticker) == "Ngân hàng" for ticker in eligible]))
    candidate_groups = pd.Series([groups.get(ticker, "Không rõ") for ticker in candidates])
    group_names_en = {
        "Ngân hàng": "Banks",
        "Ngành khác": "Other",
        "Công nghệ": "Technology",
        "Bất động sản": "Real estate",
        "Bán lẻ": "Retail",
        "Thực phẩm": "Food",
        "Nguyên vật liệu": "Materials",
        "Năng lượng": "Energy",
        "Tiện ích": "Utilities",
        "Không rõ": "Unclassified",
    }
    candidate_group_fraction = (
        candidate_groups.map(lambda name: group_names_en.get(str(name), str(name)))
        .value_counts(normalize=True).sort_index().to_dict()
    )
    row = features.loc[signal]
    market = {
        "ai_high_volatility_probability": float(probability),
        "vn30_annualized_volatility_20d": float(row["vol_20"]),
        "vn30_annualized_volatility_60d": float(row["vol_60"]),
        "vn30_annualized_volatility_120d": float(row["vol_120"]),
        "vn30_return_20d": float(row["return_20"]),
        "vn30_return_60d": float(row["return_60"]),
        "volatility_ratio_20d_to_120d": float(row["vol_ratio_20_120"]),
        "eligible_stock_count": len(eligible),
        "candidate_stock_count": len(candidates),
        "mean_pairwise_correlation_252d": float(np.nanmean(upper)),
        "90th_percentile_pairwise_correlation_252d": float(np.nanquantile(upper, 0.90)),
        "cross_sectional_20d_return_dispersion": float(recent.std(ddof=1)),
        "fraction_stocks_positive_20d": float((recent > 0).mean()),
        "bank_fraction_of_eligible_stocks": bank_share,
        "candidate_group_fraction": {
            str(group): float(fraction)
            for group, fraction in candidate_group_fraction.items()
        },
        "candidate_median_daily_traded_value_proxy_vnd": float(candidate_liquidity.median()),
        "candidate_min_daily_traded_value_proxy_vnd": float(candidate_liquidity.min()),
        "candidate_max_daily_traded_value_proxy_vnd": float(candidate_liquidity.max()),
        "minimum_daily_value_for_full_position_fill_vnd": float(
            capital_vnd / max(k, 1) / max(adtv_participation, 1e-12)
        ),
        "news_context": news_context or {
            "enabled": False,
            "eligible_record_count": 0,
            "reason": "No local, point-in-time news metadata was supplied.",
            "article_text_or_headlines_retained": False,
        },
    }
    evidence = {
        "MKT:VOLATILITY": {
            "p_high_volatility": round(float(probability), 4),
            "vol_20d": round(float(row["vol_20"]), 4),
            "vol_60d": round(float(row["vol_60"]), 4),
            "ratio_20d_120d": round(float(row["vol_ratio_20_120"]), 4),
        },
        "MKT:TREND": {
            "return_20d": round(float(row["return_20"]), 4),
            "return_60d": round(float(row["return_60"]), 4),
        },
        "MKT:CROSS_SECTION": {
            "mean_correlation": round(float(np.nanmean(upper)), 4),
            "correlation_p90": round(float(np.nanquantile(upper, 0.90)), 4),
            "return_dispersion_20d": round(float(recent.std(ddof=1)), 4),
            "positive_fraction_20d": round(float((recent > 0).mean()), 4),
        },
        "MKT:LIQUIDITY": {
            "eligible_n": len(eligible),
            "candidate_pool_n": len(candidates),
            "median_daily_value_vnd": round(float(candidate_liquidity.median()), 0),
        },
    }
    if news_context and int(news_context.get("eligible_record_count", 0)) > 0:
        evidence["NEWS:ISSUER_COVERAGE"] = {
            "eligible_records": int(news_context["eligible_record_count"]),
            "issuer_name_query_mentions_5d": int(news_context["aggregate_mentions_5d"]),
            "issuer_name_query_mentions_20d": int(news_context["aggregate_mentions_20d"]),
            "timestamp_basis": "GDELT source first-seen timestamp; not publisher publication time",
            "entity_resolution": "Exact company-name query alias; not human-confirmed ticker classification",
            "source_references": news_context.get("source_references", []),
            "text_or_sentiment": "Not retained or inferred",
        }
    matured_ai_rows = [
        item for item in signal_history
        if item.get("signal_date")
        and pd.Timestamp(item["signal_date"]) < signal
        and item.get("exit_date")
        and pd.Timestamp(item["exit_date"]) <= signal
        and item.get("realized_high_volatility") is not None
        and item.get("probability_high_volatility") is not None
    ]
    if matured_ai_rows:
        ai_actual = np.asarray([int(item["realized_high_volatility"]) for item in matured_ai_rows])
        ai_probability = np.asarray([float(item["probability_high_volatility"]) for item in matured_ai_rows])
        baseline_probability = np.asarray([
            float(item.get("training_prevalence", np.mean(ai_actual)))
            for item in matured_ai_rows
        ])
        ai_brier = float(np.mean((ai_probability - ai_actual) ** 2))
        baseline_brier = float(np.mean((baseline_probability - ai_actual) ** 2))
        submodel_reliability = {
            "matured_monthly_signals": len(matured_ai_rows),
            "brier_score": ai_brier,
            "expanding_training_prevalence_brier": baseline_brier,
            "brier_skill_vs_training_prevalence": (
                1 - ai_brier / baseline_brier if baseline_brier > 0 else None
            ),
            "interpretation": "Negative skill means this classifier has been less accurate than its training-prevalence baseline on matured prior signals.",
        }
    else:
        submodel_reliability = {
            "matured_monthly_signals": 0,
            "brier_score": None,
            "expanding_training_prevalence_brier": None,
            "brier_skill_vs_training_prevalence": None,
            "interpretation": "No matured prior monthly forecasts are available; treat this probability as an unverified feature.",
        }
    policy_rows = []
    qaoa_by_policy: dict[str, list[dict[str, Any]]] = {}
    for result in past_qaoa_rows:
        if result.get("policy_id") and result.get("exit_date") and pd.Timestamp(result["exit_date"]) <= signal:
            qaoa_by_policy.setdefault(result["policy_id"], []).append(result)
    for policy_id, policy in sorted(POLICIES.items()):
        history = past_policy_metrics.get(policy_id)
        qaoa_history = qaoa_by_policy.get(policy_id, [])
        policy_tickers = candidates[: policy.n_qubits]
        policy_problem = _build_policy_problem(
            returns.loc[:, policy_tickers], policy_tickers, policy_id, k=6,
            fee_bps=fee_bps,
        )
        qubo = build_qubo(policy_problem, mixer=policy.mixer)
        cost_two_qubit_gates = int(
            policy.depth
            * np.count_nonzero(np.triu(np.abs(qubo.quadratic) > 1e-14, k=1))
        )
        mixer_edges = mixer_edges_for_problem(
            policy_problem.covariance, policy.mixer_layout
        ) if policy.mixer == "XY" else ()
        mixer_two_qubit_gates = (
            int(policy.depth * 2 * len(mixer_edges)) if policy.mixer == "XY" else 0
        )
        policy_action: dict[str, Any] = {
            "id": policy_id,
            "n": policy.n_qubits,
            "k": 6,
            "mixer": policy.mixer,
            "layout": policy.mixer_layout,
            "p": policy.depth,
            "lambda": policy.risk_aversion,
            "shrinkage": policy.shrinkage,
            "shots": policy.shots,
            "closed_periods": 0 if history is None else history["completed_periods"],
            "mixer_edge_count": len(mixer_edges),
            "logical_cost_two_qubit_gate_count": cost_two_qubit_gates,
            "logical_mixer_two_qubit_gate_count": mixer_two_qubit_gates,
            "logical_total_two_qubit_gate_count": (
                cost_two_qubit_gates + mixer_two_qubit_gates
            ),
        }
        policy_evidence: dict[str, Any] = {
            "closed_periods": 0 if history is None else history["completed_periods"],
        }
        if history is not None:
            policy_evidence.update(
                {
                    "cagr": round(history["cagr_to_date"], 5),
                    "sharpe": _finite_or_none(history["annualized_sharpe_to_date"]),
                    "sortino": _finite_or_none(history["sortino_to_date"]),
                    "max_drawdown": round(history["max_drawdown_to_date"], 5),
                    "cvar_95": round(history["monthly_cvar_95_to_date"], 5),
                    "turnover": round(history["mean_two_way_turnover"], 5),
                    "cost_vnd": round(history["total_transaction_cost_vnd"], 0),
                }
            )
        if qaoa_history:
            regrets = [r["normalized_objective_regret"] for r in qaoa_history if r.get("normalized_objective_regret") is not None]
            feasible = [r["best_sampled_feasible_probability"] for r in qaoa_history if r.get("best_sampled_feasible_probability") is not None]
            policy_evidence["mean_regret"] = round(float(np.mean(regrets)), 5) if regrets else None
            policy_evidence["feasible_probability"] = round(float(np.mean(feasible)), 4) if feasible else None
        policy_rows.append(policy_action)
        evidence[f"POLICY:{policy_id}"] = policy_evidence

    eligible_policy_ids = [
        row["id"] for row in policy_rows
        if row["closed_periods"] >= 6
        and evidence[f"POLICY:{row['id']}"].get("mean_regret") is not None
    ]
    if not eligible_policy_ids:
        eligible_policy_ids = ["n12_balanced_xy_ring_p1"]

    compact_comparators = {}
    for key, value in past_strategy_metrics.items():
        if "Ledoit–Wolf" in key:
            comparator_id = "ledoit_wolf_exact_full_universe"
        elif "nghiệm chính xác / 12 mã" in key and "AI điều chỉnh λ và α" in key:
            comparator_id = "ai_parameters_exact_n12"
        elif "AI + QAOA p=1, bộ trộn X" in key:
            comparator_id = "fixed_qaoa_x_p1_n12"
        elif "AI + QAOA p=2, bộ trộn X" in key:
            comparator_id = "fixed_qaoa_x_p2_n12"
        elif "AI + QAOA p=1, bộ trộn XY" in key:
            comparator_id = "fixed_qaoa_xy_p1_n12"
        else:
            continue
        compact_comparators[comparator_id] = {
            "closed_periods": value["completed_periods"],
            "cagr": round(value["cagr_to_date"], 5),
            "sharpe": _finite_or_none(value["annualized_sharpe_to_date"]),
            "max_drawdown": round(value["max_drawdown_to_date"], 5),
            "turnover": round(value["mean_two_way_turnover"], 5),
        }
    return {
        "prompt_version": PROMPT_CACHE_VERSION,
        "as_of_date": str(signal.date()),
        "information_cutoff": "Use features available on the signal date and completed portfolio periods with exit dates no later than the signal date.",
        "dataset_profile": {
            "market": "Vietnam equities; daily point-in-time VN30 constituent intervals; DNSE raw execution prices and VCI rights-adjusted price series.",
            "known_limitations": [
                "Historical membership intervals are curated from exchange review records and should be audited against each source link.",
                "VCI states prices are adjusted for entitlement events; each cash dividend, split, bonus issue and rights event has not been independently reconciled.",
                "Portfolio wealth is marked through adjusted-open return ratios; this is a synthetic total-return approximation, not an event-level cash-and-share ledger.",
                "Close multiplied by volume is a traded-value proxy, not verified exchange turnover.",
                "Historical simulation with modeled fees and capacity is not proof of executable profit.",
                "If news_context is supplied, counts reflect source first-seen timestamps and issuer-name queries; they are not verified publication times, sentiment, or causal attribution.",
            ],
        },
        "submodels": {
            "regime_classifier": {
                "model": "scikit-learn LogisticRegression with StandardScaler",
                "inputs": ["VN30 20/60/120-session realized volatility", "20/60-session return", "20-to-120 volatility ratio"],
                "target": "Whether forward 21-session realized volatility exceeds a training-only 70th-percentile threshold.",
                "output": "Probability of a high-volatility regime; this is not a return forecast or a trading signal.",
                "reliability_to_date": submodel_reliability,
            }
        },
        "market": market,
        "comparators": compact_comparators,
        "policy_candidates": policy_rows,
        "eligible_policy_ids": eligible_policy_ids,
        "insight_code_rules": insight_code_rules(
            market["minimum_daily_value_for_full_position_fill_vnd"]
        ),
        "evidence_ids": list(evidence),
        "evidence": evidence,
        "qaoa_objective_specification": {
            "formula": "minimize lambda * (x^T Sigma_alpha x) / K^2 - (mu^T x) / K + annualized modeled transaction cost",
            "interpretation": "Select exactly K assets; trade off estimated covariance risk, historical expected return and estimated rebalance cost.",
            "covariance_shrinkage": "Sigma_alpha = (1-alpha) * sample_covariance + alpha * diagonal(sample_covariance).",
            "lambda_meaning": "Risk penalty relative to the expected-return term; not a probability.",
            "alpha_meaning": "Diagonal covariance shrinkage strength; not a return forecast.",
            "transaction_fee_bps_per_side": float(fee_bps),
            "rebalances_per_year": 12,
            "previous_weight_source": "Prior AGQO portfolio; initial portfolio is cash.",
        },
        "evaluation_metric_definitions": {
            "net_monthly_return": "Portfolio monthly return after modeled buy and sell fees.",
            "cagr": "(product(1 + net_monthly_return))^(12 / number_of_months) - 1.",
            "sharpe": "sqrt(12) * mean(monthly excess return) / sample standard deviation(monthly excess return); monthly risk-free rate is assumed to be zero.",
            "sortino": "sqrt(12) * mean(monthly excess return) / sqrt(mean(min(monthly excess return, 0)^2)).",
            "max_drawdown": "Minimum compounded-wealth-to-prior-running-peak ratio minus 1; more negative is worse.",
            "monthly_cvar_95": "Mean monthly return among observations at or below the empirical 5th percentile; more negative is worse.",
            "mean_two_way_turnover": "Average sum of absolute portfolio weight changes per rebalance; includes liquidation outside the candidate universe.",
            "normalized_objective_regret": "(best feasible QAOA objective - exact minimum) / objective range across feasible portfolios; lower is better and zero matches the exact optimum.",
            "feasible_sample_probability": "Fraction of measured QAOA shots selecting exactly K assets; it is not a probability of profit.",
            "logical_gate_count": "Simulator-level logical gate proxy, not a hardware-native gate count or runtime advantage claim.",
        },
        "decision_rule": "Select one existing policy id. Prefer completed, fee-adjusted evidence; consider risk, objective regret, feasible-sample rate and logical circuit cost together. Fewer than 6 completed periods is weak evidence. Do not infer future returns or add unsupported facts.",
    }


def _finite_or_none(value: float | None) -> float | None:
    return float(value) if value is not None and np.isfinite(value) else None


def _qaoa_best(
    problem: PortfolioProblem,
    mixer: str,
    depth: int,
    config: ResearchConfig,
    shots: int | None = None,
    mixer_layout: str = "ring",
):
    results = [
        optimize_qaoa(
            problem,
            mixer=mixer,
            depth=depth,
            seed=seed,
            max_evaluations=config.qaoa_max_evaluations,
            shots=config.qaoa_shots if shots is None else shots,
            mixer_layout=mixer_layout,
        )
        for seed in config.qaoa_seeds
    ]
    feasible = [result for result in results if result.best_bits is not None]
    best = min(feasible, key=lambda result: result.best_feasible_score) if feasible else None
    return best, results


def _run_policy_qaoa_selection(
    returns: pd.DataFrame,
    tickers: tuple[str, ...],
    policy_id: str,
    previous_tickers: tuple[str, ...],
    config: ResearchConfig,
    signal: pd.Timestamp,
    entry: pd.Timestamp,
    exit_date: pd.Timestamp,
    variant: str,
) -> tuple[tuple[str, ...], dict[str, Any], float, float]:
    """Chạy một cấu hình AGQO cùng nghiệm chuẩn và trả danh mục, nhật ký, thời gian."""
    policy = POLICIES[policy_id]
    selected = tickers[: policy.n_qubits]
    problem = _build_policy_problem(
        returns.loc[:, selected], selected, policy_id, config.k,
        previous_tickers=previous_tickers, fee_bps=config.fee_bps,
    )
    started = perf_counter()
    exact_bits, exact_score = exact_solve_vectorized(problem)
    exact_elapsed = perf_counter() - started
    scores = [
        problem.score(np.fromiter((i in chosen for i in range(problem.n)), dtype=np.int8))
        for chosen in combinations(range(problem.n), problem.k)
    ]
    objective_span = max(scores) - min(scores)
    best, runs = _qaoa_best(
        problem, policy.mixer, policy.depth, config,
        shots=policy.shots, mixer_layout=policy.mixer_layout,
    )
    if best is None:
        bits, best_score, regret = exact_bits, None, None
        fallback = "exact_classical_no_feasible_qaoa_sample"
    else:
        bits = np.asarray(best.best_bits, dtype=np.int8)
        best_score = float(best.best_feasible_score)
        regret = float((best_score - exact_score) / objective_span) if objective_span > 0 else 0.0
        fallback = None
    target = tuple(selected[i] for i in np.flatnonzero(bits))
    row = {
        "signal_date": str(signal.date()),
        "entry_date": str(entry.date()),
        "exit_date": str(exit_date.date()),
        "variant": variant,
        "policy_id": policy_id,
        "n_qubits": problem.n,
        "k": config.k,
        "depth": policy.depth,
        "mixer": policy.mixer,
        "mixer_layout": policy.mixer_layout,
        "shots": policy.shots,
        "mixer_edge_count": runs[0].mixer_edge_count if runs else None,
        "logical_cost_two_qubit_gate_count": runs[0].logical_cost_two_qubit_gate_count if runs else None,
        "logical_mixer_two_qubit_gate_count": runs[0].logical_mixer_two_qubit_gate_count if runs else None,
        "exact_score": float(exact_score),
        "objective_span": float(objective_span),
        "qaoa_best_score": best_score,
        "normalized_objective_regret": regret,
        "best_seed": None if best is None else best.seed,
        "best_sampled_feasible_probability": None if best is None else best.sampled_feasible_probability,
        "fallback_used": fallback,
        "runs": [run.to_dict() for run in runs],
    }
    return target, row, exact_elapsed, float(sum(run.elapsed_seconds for run in runs))


def _capacity_ledger(
    targets: list[tuple[str, ...]],
    tickers: tuple[str, ...],
    stock_open: pd.DataFrame,
    adjusted_open: pd.DataFrame,
    entries: list[pd.Timestamp],
    exits: list[pd.Timestamp],
    liquidities: list[pd.Series],
    config: ResearchConfig,
    fee_bps: float,
    participation: float,
) -> pd.DataFrame:
    """Mark positions to adjusted total-return prices and cap trades on raw turnover."""
    holdings = pd.Series(0.0, index=tickers)
    cash = float(config.capital_vnd)
    previous_nav = cash
    fee_rate = fee_bps / 10_000
    rows = []
    for target, entry, exit_date, adv in zip(targets, entries, exits, liquidities):
        prices_in = stock_open.loc[entry].reindex(tickers)
        adjusted_in = adjusted_open.loc[entry].reindex(tickers)
        adjusted_out = adjusted_open.loc[exit_date].reindex(tickers)
        if target and prices_in[list(target)].isna().any():
            raise ValueError(f"Thiếu giá mở cửa ở ngày vào {entry.date()}.")
        if holdings.abs().sum() and adjusted_in[holdings.abs() > 0].isna().any():
            raise ValueError(f"Thiếu giá điều chỉnh để định giá danh mục tại {entry.date()}.")
        if holdings.abs().sum() and adjusted_out[holdings.abs() > 0].isna().any():
            raise ValueError(f"Thiếu giá điều chỉnh để định giá danh mục tại {exit_date.date()}.")
        current_values = holdings.copy()
        nav_before = float(cash + current_values.sum())
        desired = pd.Series(0.0, index=tickers)
        if target:
            desired.loc[list(target)] = nav_before / config.k
        delta = desired - current_values
        traded = 0.0
        cost = 0.0
        capacity_unfilled = 0.0
        funding_unfilled = 0.0
        max_requested_participation = 0.0
        adv = adv.reindex(tickers)
        for ticker in tickers:
            if delta[ticker] >= 0:
                continue
            order = min(float(-delta[ticker]), float(current_values[ticker]))
            adv_value = float(adv.get(ticker, np.nan))
            cap = max(0.0, adv_value * participation) if np.isfinite(adv_value) else 0.0
            fill = min(order, cap)
            max_requested_participation = max(
                max_requested_participation, order / adv_value if adv_value > 0 else 0.0
            )
            capacity_unfilled += order - fill
            holdings[ticker] -= fill
            fee = fill * fee_rate
            cash += fill - fee
            traded += fill
            cost += fee
        current_values = holdings.copy()
        for ticker in tickers:
            if delta[ticker] <= 0:
                continue
            order = float(desired[ticker] - current_values[ticker])
            adv_value = float(adv.get(ticker, np.nan))
            cap = max(0.0, adv_value * participation) if np.isfinite(adv_value) else 0.0
            cap_limited_order = min(order, cap)
            affordable = cash / (1 + fee_rate)
            fill = min(cap_limited_order, affordable)
            max_requested_participation = max(
                max_requested_participation, order / adv_value if adv_value > 0 else 0.0
            )
            capacity_unfilled += order - cap_limited_order
            funding_unfilled += cap_limited_order - fill
            holdings[ticker] += fill
            fee = fill * fee_rate
            cash -= fill + fee
            traded += fill
            cost += fee
        nav_after_trade = float(cash + holdings.sum())
        active = holdings.abs() > 0
        if active.any():
            total_return_factors = adjusted_out[active] / adjusted_in[active]
            if not np.isfinite(total_return_factors.to_numpy()).all() or (total_return_factors <= 0).any():
                raise ValueError(f"Lợi suất giá mở cửa điều chỉnh không hợp lệ đến {exit_date.date()}.")
            holdings.loc[active] *= total_return_factors
        end_value = float(cash + holdings.sum())
        net_return = end_value / previous_nav - 1
        gross_return = (end_value + cost) / previous_nav - 1 if previous_nav else np.nan
        rows.append(
            {
                "entry_date": entry,
                "exit_date": exit_date,
                "net_return": net_return,
                "gross_return": gross_return,
                "nav_before_trade": nav_before,
                "nav_after_trade": nav_after_trade,
                "ending_nav": end_value,
                "cash_weight_after_trade": cash / nav_after_trade if nav_after_trade else np.nan,
                "executed_turnover": traded / nav_before,
                "executed_notional_vnd": traded,
                "transaction_cost_vnd": cost,
                "capacity_unfilled_notional_vnd": capacity_unfilled,
                "funding_unfilled_notional_vnd": funding_unfilled,
                "requested_notional_vnd": traded + capacity_unfilled + funding_unfilled,
                "capacity_unfilled_fraction": (
                    capacity_unfilled / (traded + capacity_unfilled + funding_unfilled)
                    if traded + capacity_unfilled + funding_unfilled else 0.0
                ),
                "funding_unfilled_fraction": (
                    funding_unfilled / (traded + capacity_unfilled + funding_unfilled)
                    if traded + capacity_unfilled + funding_unfilled else 0.0
                ),
                "max_requested_adtv_participation": max_requested_participation,
                "target_tickers": list(target),
            }
        )
        previous_nav = end_value
    return pd.DataFrame(rows).set_index("entry_date")


def _daily_regime_evaluation(
    features: pd.DataFrame,
    market_returns: pd.Series,
    threshold: float,
    chosen_c: float,
    test_start: str,
    horizon: int,
):
    target = forward_volatility(market_returns.reindex(features.index), horizon)
    end_date = features.index[-horizon - 1]
    dates = features.index[
        (features.index >= pd.Timestamp(test_start)) & (features.index <= end_date)
    ]
    rows = []
    for date in dates:
        if features.loc[date].isna().any() or not np.isfinite(features.loc[date].to_numpy()).all():
            continue
        model = fit_regime_model_as_of(
            features, market_returns, date, threshold, chosen_c, horizon=horizon
        )
        probability = float(model.predict_probability(features.loc[[date]])[0])
        rows.append(
            {
                "date": date,
                "probability_high_volatility": probability,
                "training_prevalence": model.training_prevalence,
                "actual_high_volatility": int(target.loc[date] > threshold),
            }
        )
    forecasts = pd.DataFrame(rows).set_index("date")
    if forecasts.empty:
        raise ValueError("Không có dự báo chế độ nào trong giai đoạn kiểm tra.")
    y = forecasts.actual_high_volatility.to_numpy(dtype=int)
    p = forecasts.probability_high_volatility.to_numpy(dtype=float)
    baseline = forecasts.training_prevalence.to_numpy(dtype=float).clip(1e-6, 1 - 1e-6)
    p_clipped = p.clip(1e-6, 1 - 1e-6)
    brier = float(np.mean((p - y) ** 2))
    baseline_brier = float(np.mean((baseline - y) ** 2))
    loss = float(log_loss(y, p_clipped, labels=[0, 1]))
    base_loss = float(-np.mean(y * np.log(baseline) + (1 - y) * np.log1p(-baseline)))
    metrics = {
        "n_daily_overlapping_forecasts": int(len(y)),
        "first_date": str(forecasts.index.min().date()),
        "last_date": str(forecasts.index.max().date()),
        "observed_high_volatility_rate": float(y.mean()),
        "mean_forecast_probability": float(p.mean()),
        "log_loss": loss,
        "expanding_base_rate_log_loss": base_loss,
        "brier_score": brier,
        "expanding_base_rate_brier": baseline_brier,
        "brier_skill_vs_expanding_base_rate": float(1 - brier / baseline_brier) if baseline_brier else None,
        "positive_brier_skill": bool(brier < baseline_brier),
        "overlap_note": "Nhãn 21 phiên tương lai chồng lấn; số dự báo ngày không phải số quan sát độc lập.",
    }
    return forecasts, metrics


def run_walkforward(
    data_path: str | Path,
    members_path: str | Path,
    output_json: str | Path,
    config: ResearchConfig = ResearchConfig(),
    guide: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    news_path: str | Path | None = None,
) -> dict[str, object]:
    """Chạy các đối chứng hiện tại và tùy chọn bộ điều khiển LLM→QAOA AGQO."""
    started = perf_counter()
    (
        data, members, membership_history, dates, stock_open, stock_adjusted_open,
        stock_close, stock_returns,
        index_open, index_close, index_returns, traded_value,
    ) = _load_panels(data_path, members_path)
    if news_path is not None:
        news_file = Path(news_path)
        if not news_file.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp tin tức đã chỉ định: {news_file}")
        news_records = load_news_records(news_file)
        news_manifest_path = news_file.with_name("manifest.json")
        if news_records and news_manifest_path.exists():
            news_manifest = json.loads(news_manifest_path.read_text(encoding="utf-8"))
            if (
                news_manifest.get("status") != "collected_metadata_only"
                or news_manifest.get("complete_universe_query") is not True
                or news_manifest.get("news_context_available") is not True
            ):
                raise ValueError(
                    "Manifest tin không xác nhận lượt thu thập đầy đủ cho toàn bộ bí danh; "
                    "không đưa tập tin một phần hoặc bị giới hạn tốc độ vào hướng dẫn LLM."
                )
    else:
        news_records = []
    tickers = tuple(stock_returns.columns.astype(str))
    features = _index_features(index_returns)
    model = fit_regime_model(
        features,
        index_returns,
        train_end=config.train_end,
        validation_start=config.validation_start,
        validation_end=config.validation_end,
        horizon=config.horizon,
    )
    forward_vol = forward_volatility(index_returns, config.horizon)
    oos_daily, ai_metrics = _daily_regime_evaluation(
        features, index_returns, model.threshold, model.chosen_c,
        config.test_start, config.horizon,
    )
    paired_signals = _calendar_signals(dates, config.test_start, config.test_last_signal)
    if not paired_signals:
        raise ValueError("Không tạo được các kỳ nắm giữ tháng trong giai đoạn kiểm tra.")

    baseline_strategy_names = (
        "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI chỉ điều chỉnh λ / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI chỉ điều chỉnh α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
        "Tham lam / 12 mã thanh khoản cao",
        "Tôi luyện mô phỏng / 12 mã thanh khoản cao",
    )
    policy_strategy_names = {
        policy_id: _policy_strategy_name(policy_id) for policy_id in sorted(POLICIES)
    }
    strategy_names = baseline_strategy_names + (
        ((AGQO_STRATEGY_NAME, RULE_STRATEGY_NAME) + tuple(policy_strategy_names.values())) if guide else ()
    )
    targets: dict[str, list[tuple[str, ...]]] = {name: [] for name in strategy_names}
    signal_rows = []
    qaoa_rows = []
    optimality_rows = []
    guidance_rows = []
    entries, exits, liquidities = [], [], []
    group_by_ticker = membership_history.drop_duplicates("ticker").set_index("ticker")["group"].astype(str).to_dict()
    exact_full_solve_seconds = 0.0
    exact_12_solve_seconds = 0.0
    exact_ai12_solve_seconds = 0.0
    exact_agqo_solve_seconds = 0.0
    agqo_qaoa_seconds = 0.0
    policy_catalog_exact_solve_seconds = 0.0
    policy_catalog_qaoa_seconds = 0.0
    for signal, entry, exit_date in paired_signals:
        fitted = fit_regime_model_as_of(
            features, index_returns, signal, model.threshold, model.chosen_c,
            horizon=config.horizon,
        )
        probability = float(fitted.predict_probability(features.loc[[signal]])[0])
        controls_lambda, controls_alpha = regime_controls(probability)
        returns, eligible, candidates, liquidity = _eligible_universe(
            signal, tickers, stock_returns, traded_value, config, membership_history
        )
        baseline_candidates = candidates[: config.qaoa_candidates]
        if len(eligible) < config.k or len(candidates) < config.k:
            raise ValueError(f"Không đủ mã tại {signal.date()} để chọn K={config.k}.")
        signal_rows.append(
            {
                "signal_date": str(signal.date()),
                "entry_date": str(entry.date()),
                "exit_date": str(exit_date.date()),
                "probability_high_volatility": probability,
                "training_prevalence": fitted.training_prevalence,
                "realized_forward_volatility": float(forward_vol.loc[signal]),
                "realized_high_volatility": int(
                    forward_vol.loc[signal] > model.threshold
                ),
                "lambda": controls_lambda,
                "alpha": controls_alpha,
                "eligible_universe_n": len(eligible),
                "qaoa_candidate_tickers": list(baseline_candidates),
                "agqo_candidate_pool_tickers": list(candidates),
                "eligible_tickers": list(eligible),
                "complete_estimation_rows": len(returns),
            }
        )
        entries.append(entry)
        exits.append(exit_date)
        liquidities.append(liquidity)

        agqo_policy = None
        rule_policy_id = None
        if guide is not None:
            history = _past_strategy_metrics(
                signal, targets, tickers, stock_open, stock_adjusted_open,
                entries, exits, liquidities, config
            )
            past_policy_metrics = {
                policy_id: history[strategy_name]
                for policy_id, strategy_name in policy_strategy_names.items()
                if strategy_name in history
            }
            comparator_metrics = {
                name: metrics for name, metrics in history.items()
                if name not in policy_strategy_names.values()
            }
            past_qaoa_rows = [
                row for row in qaoa_rows
                if row.get("exit_date") and pd.Timestamp(row["exit_date"]) <= signal
            ]
            rule_policy_id = _choose_rule_policy(past_policy_metrics, past_qaoa_rows)
            payload = _build_agqo_payload(
                signal, features, probability, returns, eligible, candidates, liquidity,
                group_by_ticker, comparator_metrics, past_policy_metrics,
                past_qaoa_rows, signal_rows, config.fee_bps, config.capital_vnd,
                config.adtv_participation, config.k,
                summarize_news_as_of(news_records, signal, candidates) if news_records else None,
            )
            payload = enrich_guide_payload(payload)
            envelope = guide(payload)
            if not isinstance(envelope, dict):
                raise ValueError("Bộ điều khiển AGQO phải trả về một đối tượng JSON.")
            decision = validate_guidance(
                envelope.get("decision", {}), set(payload.get("evidence_ids", [])),
                set(payload.get("eligible_policy_ids", [])),
                set(payload.get("allowed_insight_codes", [])),
            )
            proposed_policy_id = decision["policy_id"]
            executed_policy_id, guardrail_reason, guardrail_evidence = _supervise_policy_proposal(
                proposed_policy_id,
                rule_policy_id,
                past_policy_metrics,
                past_qaoa_rows,
            )
            raw_insight_codes = decision["insight_codes"]
            supported_codes, insight_repairs = support_insight_codes(
                payload, raw_insight_codes
            )
            decision["llm_insight_codes"] = raw_insight_codes
            decision["insight_codes"] = supported_codes
            decision["insight_repairs"] = insight_repairs
            decision["risk_flags"] = derive_risk_flags(payload, proposed_policy_id)
            decision["rationale"], decision["risk_note"] = render_grounded_narrative(
                payload, proposed_policy_id, executed_policy_id, supported_codes,
                decision["risk_flags"], guardrail_reason,
            )
            required_evidence_ids = [
                evidence_id
                for code in supported_codes
                for evidence_id in {
                    "high_volatility": ("MKT:VOLATILITY",),
                    "volatility_rising": ("MKT:VOLATILITY",),
                    "high_correlation": ("MKT:CROSS_SECTION",),
                    "high_dispersion": ("MKT:CROSS_SECTION",),
                    "bank_concentration": ("MKT:CROSS_SECTION",),
                    "low_liquidity": ("MKT:LIQUIDITY",),
                    "mixed_signals": ("MKT:VOLATILITY", "MKT:CROSS_SECTION"),
                }[code]
                if evidence_id in payload.get("evidence_ids", [])
            ]
            decision["evidence_ids"] = list(dict.fromkeys(
                [*decision["evidence_ids"], *required_evidence_ids]
            ))
            agqo_policy = POLICIES[executed_policy_id]
            guidance_rows.append(
                {
                    "signal_date": str(signal.date()),
                    "information_cutoff": str(signal.date()),
                    "context": payload,
                    "decision": decision,
                    "proposed_policy_id": proposed_policy_id,
                    "executed_policy_id": executed_policy_id,
                    "guardrail_reason": guardrail_reason,
                    "guardrail_evidence": guardrail_evidence,
                    "policy": asdict(agqo_policy),
                    "rule_comparator_policy_id": rule_policy_id,
                    "model": envelope.get("model"),
                    "model_revision": envelope.get("model_revision"),
                    "quantization": envelope.get("quantization"),
                    "validation_repairs": envelope.get("validation_repairs", []),
                    "response_id": envelope.get("response_id"),
                    "usage": envelope.get("usage"),
                    "cache_key": envelope.get("cache_key"),
                    "cache_hit": envelope.get("cache_hit", False),
                }
            )

        definitions = [
            (strategy_names[0], "fixed", eligible),
            (strategy_names[1], "ai_lambda", eligible),
            (strategy_names[2], "ai_alpha", eligible),
            (strategy_names[3], "ai_both", eligible),
            (strategy_names[4], "ledoit_wolf", eligible),
        ]
        for name, variant, universe in definitions:
            subset = returns.loc[:, universe]
            built = _build_problem(subset, universe, probability, variant, config.k)
            problem = built[0] if isinstance(built, tuple) else built
            solve_start = perf_counter()
            bits, _ = exact_solve_vectorized(problem)
            elapsed = perf_counter() - solve_start
            if len(universe) == len(eligible):
                exact_full_solve_seconds += elapsed
            else:
                exact_12_solve_seconds += elapsed
            targets[name].append(tuple(universe[i] for i in np.flatnonzero(bits)))

        ai12_built = _build_problem(
            returns.loc[:, baseline_candidates], baseline_candidates, probability, "ai_both", config.k
        )
        ai12_problem = ai12_built[0] if isinstance(ai12_built, tuple) else ai12_built
        exact12_start = perf_counter()
        exact12_bits, exact12_score = exact_solve_vectorized(ai12_problem)
        exact12_elapsed = perf_counter() - exact12_start
        exact_12_solve_seconds += exact12_elapsed
        exact_ai12_solve_seconds += exact12_elapsed
        exact12_tickers = tuple(baseline_candidates[i] for i in np.flatnonzero(exact12_bits))
        targets[strategy_names[5]].append(exact12_tickers)
        greedy_bits, _ = greedy_solve(ai12_problem)
        anneal_bits, _ = anneal_solve(
            ai12_problem, seed=20261021 + len(entries), steps=20_000
        )
        targets[strategy_names[9]].append(
            tuple(baseline_candidates[i] for i in np.flatnonzero(greedy_bits))
        )
        targets[strategy_names[10]].append(
            tuple(baseline_candidates[i] for i in np.flatnonzero(anneal_bits))
        )
        all_scores = []
        for chosen in combinations(range(ai12_problem.n), ai12_problem.k):
            bits = np.zeros(ai12_problem.n, dtype=np.int8)
            bits[list(chosen)] = 1
            all_scores.append(ai12_problem.score(bits))
        feasible_span = max(all_scores) - min(all_scores)
        for label, mixer, depth, strategy_name in (
            ("X_p1", "X", 1, strategy_names[6]),
            ("X_p2", "X", 2, strategy_names[7]),
            ("XY_p1", "XY", 1, strategy_names[8]),
        ):
            qaoa_best, runs = _qaoa_best(ai12_problem, mixer, depth, config)
            if qaoa_best is None:
                targets[strategy_name].append(
                    targets[strategy_name][-1] if targets[strategy_name] else tuple()
                )
                best_score = None
                regret = None
            else:
                targets[strategy_name].append(
                tuple(baseline_candidates[i] for i, bit in enumerate(qaoa_best.best_bits) if bit)
                )
                best_score = float(qaoa_best.best_feasible_score)
                regret = float((best_score - exact12_score) / feasible_span) if feasible_span > 0 else 0.0
            qaoa_rows.append(
                {
                    "signal_date": str(signal.date()),
                    "entry_date": str(entry.date()),
                    "exit_date": str(exit_date.date()),
                    "variant": label,
                    "n_qubits": ai12_problem.n,
                    "k": config.k,
                    "depth": depth,
                    "mixer": mixer,
                    "mixer_layout": "single" if mixer == "X" else "ring",
                    "mixer_edge_count": 0 if mixer == "X" else ai12_problem.n,
                    "logical_cost_two_qubit_gate_count": (
                        runs[0].logical_cost_two_qubit_gate_count if runs else None
                    ),
                    "logical_mixer_two_qubit_gate_count": (
                        runs[0].logical_mixer_two_qubit_gate_count if runs else None
                    ),
                    "exact_score": float(exact12_score),
                    "objective_span": float(feasible_span),
                    "qaoa_best_score": best_score,
                    "normalized_objective_regret": regret,
                    "best_seed": None if qaoa_best is None else qaoa_best.seed,
                    "best_sampled_feasible_probability": None if qaoa_best is None else qaoa_best.sampled_feasible_probability,
                    "runs": [run.to_dict() for run in runs],
                }
            )
            if regret is not None:
                optimality_rows.append(
                    {"signal_date": str(signal.date()), "variant": label, "regret": regret}
                )

        if agqo_policy is not None:
            for policy_id, policy in sorted(POLICIES.items()):
                policy_tickers = candidates[: policy.n_qubits]
                previous_policy_target = tuple(targets[policy_strategy_names[policy_id]][-1]) if targets[policy_strategy_names[policy_id]] else ()
                policy_problem = _build_policy_problem(
                    returns.loc[:, policy_tickers], policy_tickers, policy_id, config.k,
                    previous_tickers=previous_policy_target,
                    fee_bps=config.fee_bps,
                )
                exact_start = perf_counter()
                exact_bits, exact_score = exact_solve_vectorized(policy_problem)
                exact_elapsed = perf_counter() - exact_start
                exact_12_solve_seconds += exact_elapsed
                policy_catalog_exact_solve_seconds += exact_elapsed
                policy_scores = []
                for chosen in combinations(range(policy_problem.n), policy_problem.k):
                    bits = np.zeros(policy_problem.n, dtype=np.int8)
                    bits[list(chosen)] = 1
                    policy_scores.append(policy_problem.score(bits))
                objective_span = max(policy_scores) - min(policy_scores)
                qaoa_best, runs = _qaoa_best(
                    policy_problem, policy.mixer, policy.depth, config, shots=policy.shots,
                    mixer_layout=policy.mixer_layout,
                )
                if qaoa_best is None:
                    selected_bits = exact_bits
                    best_score = None
                    regret = None
                    fallback_used = "exact_classical_no_feasible_qaoa_sample"
                else:
                    selected_bits = np.asarray(qaoa_best.best_bits, dtype=np.int8)
                    best_score = float(qaoa_best.best_feasible_score)
                    regret = (
                        float((best_score - exact_score) / objective_span)
                        if objective_span > 0 else 0.0
                    )
                    fallback_used = None
                target = tuple(policy_tickers[i] for i in np.flatnonzero(selected_bits))
                targets[policy_strategy_names[policy_id]].append(target)
                run_dicts = [run.to_dict() for run in runs]
                variant = f"POLICY:{policy_id}"
                policy_row = {
                    "signal_date": str(signal.date()),
                    "entry_date": str(entry.date()),
                    "exit_date": str(exit_date.date()),
                    "variant": variant,
                    "policy_id": policy_id,
                    "n_qubits": policy_problem.n,
                    "k": config.k,
                    "depth": policy.depth,
                    "mixer": policy.mixer,
                    "mixer_layout": policy.mixer_layout,
                    "mixer_edge_count": (
                        runs[0].mixer_edge_count if runs else None
                    ),
                    "logical_cost_two_qubit_gate_count": (
                        runs[0].logical_cost_two_qubit_gate_count if runs else None
                    ),
                    "logical_mixer_two_qubit_gate_count": (
                        runs[0].logical_mixer_two_qubit_gate_count if runs else None
                    ),
                    "shots": policy.shots,
                    "exact_score": float(exact_score),
                    "objective_span": float(objective_span),
                    "qaoa_best_score": best_score,
                    "normalized_objective_regret": regret,
                    "best_seed": None if qaoa_best is None else qaoa_best.seed,
                    "best_sampled_feasible_probability": (
                        None if qaoa_best is None else qaoa_best.sampled_feasible_probability
                    ),
                    "fallback_used": fallback_used,
                    "runs": run_dicts,
                }
                qaoa_rows.append(policy_row)
                policy_catalog_qaoa_seconds += sum(
                    run.elapsed_seconds for run in runs
                )
                if regret is not None:
                    optimality_rows.append(
                        {"signal_date": str(signal.date()), "variant": variant, "regret": regret}
                    )

            previous_rule_target = tuple(
                targets[RULE_STRATEGY_NAME][-1] if targets[RULE_STRATEGY_NAME] else ()
            )
            rule_target, rule_row, rule_exact_elapsed, rule_qaoa_elapsed = _run_policy_qaoa_selection(
                returns, candidates, rule_policy_id, previous_rule_target, config,
                signal, entry, exit_date, "RULE_ADAPTIVE",
            )
            targets[RULE_STRATEGY_NAME].append(rule_target)
            qaoa_rows.append(rule_row)
            exact_12_solve_seconds += rule_exact_elapsed
            policy_catalog_qaoa_seconds += rule_qaoa_elapsed
            if rule_row["normalized_objective_regret"] is not None:
                optimality_rows.append(
                    {
                        "signal_date": str(signal.date()),
                        "variant": "RULE_ADAPTIVE",
                        "regret": rule_row["normalized_objective_regret"],
                    }
                )

            previous_agqo_target = (
                tuple(targets[AGQO_STRATEGY_NAME][-1]) if targets[AGQO_STRATEGY_NAME] else ()
            )
            agqo_problem = _build_policy_problem(
                returns.loc[:, candidates[: agqo_policy.n_qubits]],
                candidates[: agqo_policy.n_qubits], agqo_policy.policy_id, config.k,
                previous_tickers=previous_agqo_target,
                fee_bps=config.fee_bps,
            )
            exact_start = perf_counter()
            agqo_exact_bits, agqo_exact_score = exact_solve_vectorized(agqo_problem)
            selected_exact_elapsed = perf_counter() - exact_start
            exact_12_solve_seconds += selected_exact_elapsed
            exact_agqo_solve_seconds += selected_exact_elapsed
            agqo_scores = []
            for chosen in combinations(range(agqo_problem.n), agqo_problem.k):
                bits = np.zeros(agqo_problem.n, dtype=np.int8)
                bits[list(chosen)] = 1
                agqo_scores.append(agqo_problem.score(bits))
            agqo_span = max(agqo_scores) - min(agqo_scores)
            agqo_best, agqo_runs = _qaoa_best(
                agqo_problem, agqo_policy.mixer, agqo_policy.depth, config,
                shots=agqo_policy.shots, mixer_layout=agqo_policy.mixer_layout,
            )
            if agqo_best is None:
                selected_bits = agqo_exact_bits
                best_score = None
                regret = None
                fallback_used = "exact_classical_no_feasible_qaoa_sample"
            else:
                selected_bits = np.asarray(agqo_best.best_bits, dtype=np.int8)
                best_score = float(agqo_best.best_feasible_score)
                regret = (
                    float((best_score - agqo_exact_score) / agqo_span)
                    if agqo_span > 0 else 0.0
                )
                fallback_used = None
            selected_target = tuple(candidates[: agqo_policy.n_qubits][i] for i in np.flatnonzero(selected_bits))
            targets[AGQO_STRATEGY_NAME].append(selected_target)
            agqo_qaoa_seconds += sum(run.elapsed_seconds for run in agqo_runs)
            agqo_row = {
                "signal_date": str(signal.date()),
                "entry_date": str(entry.date()),
                "exit_date": str(exit_date.date()),
                "variant": "AGQO",
                "policy_id": agqo_policy.policy_id,
                "n_qubits": agqo_problem.n,
                "k": config.k,
                "depth": agqo_policy.depth,
                "mixer": agqo_policy.mixer,
                "mixer_layout": agqo_policy.mixer_layout,
                "mixer_edge_count": (
                    agqo_runs[0].mixer_edge_count if agqo_runs else None
                ),
                "logical_cost_two_qubit_gate_count": (
                    agqo_runs[0].logical_cost_two_qubit_gate_count if agqo_runs else None
                ),
                "logical_mixer_two_qubit_gate_count": (
                    agqo_runs[0].logical_mixer_two_qubit_gate_count if agqo_runs else None
                ),
                "shots": agqo_policy.shots,
                "exact_score": float(agqo_exact_score),
                "objective_span": float(agqo_span),
                "qaoa_best_score": best_score,
                "normalized_objective_regret": regret,
                "best_seed": None if agqo_best is None else agqo_best.seed,
                "best_sampled_feasible_probability": (
                    None if agqo_best is None else agqo_best.sampled_feasible_probability
                ),
                "fallback_used": fallback_used,
                "runs": [run.to_dict() for run in agqo_runs],
            }
            qaoa_rows.append(agqo_row)
            if regret is not None:
                optimality_rows.append(
                    {
                        "signal_date": str(signal.date()),
                        "variant": "AGQO",
                        "regret": regret,
                    }
                )
            signal_rows[-1]["agqo_policy_id"] = agqo_policy.policy_id
            signal_rows[-1]["agqo_proposed_policy_id"] = guidance_rows[-1]["proposed_policy_id"]
            signal_rows[-1]["agqo_guardrail_reason"] = guidance_rows[-1]["guardrail_reason"]
            signal_rows[-1]["rule_policy_id"] = rule_policy_id
            signal_rows[-1]["agqo_policy_parameters"] = asdict(agqo_policy)
            guidance_rows[-1]["qaoa_result"] = {
                key: agqo_row[key]
                for key in (
                    "exact_score", "qaoa_best_score", "normalized_objective_regret",
                    "best_seed", "best_sampled_feasible_probability", "fallback_used",
                )
            }
            guidance_rows[-1]["rule_qaoa_result"] = {
                key: rule_row[key]
                for key in (
                    "policy_id", "exact_score", "qaoa_best_score",
                    "normalized_objective_regret", "best_seed",
                    "best_sampled_feasible_probability", "fallback_used",
                )
            }

    monthly_y = np.asarray(
        [row["realized_high_volatility"] for row in signal_rows], dtype=int
    )
    monthly_p = np.asarray(
        [row["probability_high_volatility"] for row in signal_rows], dtype=float
    ).clip(1e-6, 1 - 1e-6)
    monthly_base = np.asarray(
        [row["training_prevalence"] for row in signal_rows], dtype=float
    ).clip(1e-6, 1 - 1e-6)
    monthly_brier = float(np.mean((monthly_p - monthly_y) ** 2))
    monthly_base_brier = float(np.mean((monthly_base - monthly_y) ** 2))
    ai_metrics["monthly_signal_metrics"] = {
        "n": int(len(monthly_y)),
        "observed_high_volatility_rate": float(monthly_y.mean()),
        "mean_forecast_probability": float(monthly_p.mean()),
        "log_loss": float(log_loss(monthly_y, monthly_p, labels=[0, 1])),
        "expanding_base_rate_log_loss": float(-np.mean(
            monthly_y * np.log(monthly_base)
            + (1 - monthly_y) * np.log1p(-monthly_base)
        )),
        "brier_score": monthly_brier,
        "expanding_base_rate_brier": monthly_base_brier,
        "brier_skill_vs_expanding_base_rate": float(
            1 - monthly_brier / monthly_base_brier
        ) if monthly_base_brier else None,
    }

    strategy_ledgers = {
        name: _capacity_ledger(
            strategy_targets, tickers, stock_open, stock_adjusted_open,
            entries, exits, liquidities,
            config, config.fee_bps, config.adtv_participation,
        )
        for name, strategy_targets in targets.items()
    }
    gross_ledgers = {
        name: _capacity_ledger(
            strategy_targets, tickers, stock_open, stock_adjusted_open,
            entries, exits, liquidities,
            config, 0.0, config.adtv_participation,
        )
        for name, strategy_targets in targets.items()
    }
    for name, ledger in strategy_ledgers.items():
        ledger["gross_return"] = gross_ledgers[name]["net_return"].to_numpy()
    benchmark_rows = []
    for entry, exit_date in zip(entries, exits):
        row = {"entry_date": entry}
        for ticker in ("VN30", "VNINDEX"):
            row[ticker] = float(
                index_open.loc[exit_date, ticker] / index_open.loc[entry, ticker] - 1
            )
        benchmark_rows.append(row)
    benchmarks = pd.DataFrame(benchmark_rows).set_index("entry_date")
    returns_by_strategy = {
        name: ledger.net_return.rename(name) for name, ledger in strategy_ledgers.items()
    }
    returns_by_strategy["VN30"] = benchmarks.VN30
    returns_by_strategy["VN-Index"] = benchmarks.VNINDEX
    performance = {}
    selection_summary = {}
    group_by_ticker = membership_history.drop_duplicates("ticker").set_index("ticker")["group"].astype(str).to_dict()
    for name, series in returns_by_strategy.items():
        ledger = strategy_ledgers.get(name)
        if ledger is not None:
            targets_for_strategy = targets[name]
            selection_counts: dict[str, int] = {}
            monthly_bank_shares = []
            for target in targets_for_strategy:
                for ticker in target:
                    selection_counts[ticker] = selection_counts.get(ticker, 0) + 1
                monthly_bank_shares.append(
                    sum(group_by_ticker.get(ticker) == "Ngân hàng" for ticker in target)
                    / config.k
                )
            selection_summary[name] = {
                "target_rebalances": len(targets_for_strategy),
                "bank_weight_mean": float(np.mean(monthly_bank_shares)),
                "bank_weight_min": float(np.min(monthly_bank_shares)),
                "bank_weight_max": float(np.max(monthly_bank_shares)),
                "ticker_selection_frequency": [
                    {
                        "ticker": ticker,
                        "selected_months": count,
                        "fraction_of_rebalances": count / len(targets_for_strategy),
                        "group": group_by_ticker.get(ticker, "Không rõ"),
                    }
                    for ticker, count in sorted(
                        selection_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
            }
        performance[name] = {
            "metrics": summarize_monthly_returns(series),
            "monthly_returns": [float(x) for x in series],
            "gross_monthly_returns": (
                [float(x) for x in strategy_ledgers[name].gross_return]
                if name in strategy_ledgers else None
            ),
            "execution_summary": (
                {
                    "total_transaction_cost_vnd": float(ledger.transaction_cost_vnd.sum()),
                    "mean_executed_turnover": float(ledger.executed_turnover.mean()),
                    "total_capacity_unfilled_vnd": float(
                        ledger.capacity_unfilled_notional_vnd.sum()
                    ),
                    "mean_capacity_unfilled_fraction": float(
                        ledger.capacity_unfilled_fraction.mean()
                    ),
                    "total_funding_unfilled_vnd": float(
                        ledger.funding_unfilled_notional_vnd.sum()
                    ),
                    "mean_funding_unfilled_fraction": float(
                        ledger.funding_unfilled_fraction.mean()
                    ),
                    "max_requested_adtv_participation": float(
                        ledger.max_requested_adtv_participation.max()
                    ),
                    "mean_cash_weight_after_trade": float(
                        ledger.cash_weight_after_trade.mean()
                    ),
                }
                if ledger is not None else None
            ),
            "period_details": (
                strategy_ledgers[name].reset_index().assign(
                    entry_date=lambda frame: frame.entry_date.dt.strftime("%Y-%m-%d"),
                    exit_date=lambda frame: frame.exit_date.dt.strftime("%Y-%m-%d"),
                ).to_dict("records")
                if name in strategy_ledgers else None
            ),
        }
    comparisons = {}
    key_names = (
        strategy_names[0], strategy_names[3], strategy_names[5],
        strategy_names[6], strategy_names[7], strategy_names[8],
    ) + ((AGQO_STRATEGY_NAME, RULE_STRATEGY_NAME) if guide else ())
    if guide:
        key_names += tuple(policy_strategy_names.values())
    for name in key_names:
        for benchmark in ("VN30", "VN-Index"):
            compare = compare_monthly_returns(
                returns_by_strategy[name], returns_by_strategy[benchmark],
                candidate_name=name, benchmark_name=benchmark,
                block_length=3, resamples=10_000, seed=11,
            )
            ci6 = compare_monthly_returns(
                returns_by_strategy[name], returns_by_strategy[benchmark],
                candidate_name=name, benchmark_name=benchmark,
                block_length=6, resamples=10_000, seed=23,
            )["active_return_confidence_interval"]
            comparisons[f"{name} vs {benchmark}"] = {
                **compare,
                "active_return_confidence_interval_block6": ci6,
            }

    qaoa_summary = {}
    qaoa_variants = ("X_p1", "X_p2", "XY_p1") + (
        (("AGQO", "RULE_ADAPTIVE") + tuple(f"POLICY:{policy_id}" for policy_id in sorted(POLICIES)))
        if guide else ()
    )
    for variant in qaoa_variants:
        subset = [row for row in qaoa_rows if row["variant"] == variant]
        runs = [run for row in subset for run in row["runs"]]
        feasible_probabilities = [
            row["best_sampled_feasible_probability"]
            for row in subset
            if row["best_sampled_feasible_probability"] is not None
        ]
        regrets = [
            row["normalized_objective_regret"]
            for row in subset
            if row["normalized_objective_regret"] is not None
        ]
        seed_regrets = [
            (run["best_feasible_score"] - row["exact_score"]) / row["objective_span"]
            for row in subset
            for run in row["runs"]
            if row.get("objective_span", 0) > 0 and run.get("best_feasible_score") is not None
        ]
        qaoa_summary[variant] = {
            "monthly_instances": len(subset),
            "seed_runs": len(runs),
            "exact_fallback_months": int(sum(
                row.get("fallback_used") is not None for row in subset
            )),
            "feasible_seed_run_fraction": float(
                np.mean([run["best_bits"] is not None for run in runs])
            ) if runs else None,
            "instances_with_regret_le_5_percent": int(
                sum(regret <= 0.05 for regret in regrets)
            ),
            "mean_normalized_regret": float(np.mean(regrets)) if regrets else None,
            "median_normalized_regret": float(np.median(regrets)) if regrets else None,
            "mean_seed_normalized_regret": float(np.mean(seed_regrets)) if seed_regrets else None,
            "median_seed_normalized_regret": float(np.median(seed_regrets)) if seed_regrets else None,
            "seed_runs_regret_le_5_percent": int(sum(value <= 0.05 for value in seed_regrets)),
            "mean_best_seed_feasible_probability": (
                float(np.mean(feasible_probabilities)) if feasible_probabilities else None
            ),
            "total_cpu_simulation_seconds": float(sum(
                run["elapsed_seconds"] for run in runs
            )),
        }

    cost_sensitivity = {}
    sensitivity_names = (
        strategy_names[3], strategy_names[6], strategy_names[7], strategy_names[8]
    ) + ((AGQO_STRATEGY_NAME, RULE_STRATEGY_NAME) if guide else ())
    if guide:
        sensitivity_names += tuple(policy_strategy_names.values())
    for name in sensitivity_names:
        rows = []
        for fee in (10.0, 25.0, 50.0):
            for capacity in (0.01, 0.05, 0.10):
                ledger = _capacity_ledger(
                    targets[name], tickers, stock_open, stock_adjusted_open,
                    entries, exits, liquidities,
                    config, fee, capacity,
                )
                stats = summarize_monthly_returns(ledger.net_return)
                rows.append(
                    {
                        "fee_bps": fee,
                        "adtv_participation": capacity,
                        "cagr": stats["cagr"],
                        "sharpe": stats["sharpe"],
                        "max_drawdown": stats["max_drawdown"],
                        "ending_value_per_unit": stats["ending_value_per_unit"],
                        "total_cost_vnd": float(ledger.transaction_cost_vnd.sum()),
                        "mean_capacity_unfilled_fraction": float(
                            ledger.capacity_unfilled_fraction.mean()
                        ),
                        "mean_funding_unfilled_fraction": float(
                            ledger.funding_unfilled_fraction.mean()
                        ),
                        "max_requested_adtv_participation": float(
                            ledger.max_requested_adtv_participation.max()
                        ),
                    }
                )
        cost_sensitivity[name] = rows

    recorded_llm_tokens = {
        key: int(sum(
            (record.get("usage") or {}).get(key, 0)
            for record in guidance_rows
        ))
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    guardrail_counts: dict[str, int] = {}
    proposal_counts: dict[str, int] = {}
    execution_counts: dict[str, int] = {}
    for record in guidance_rows:
        proposed_id = record.get("proposed_policy_id", "unknown")
        executed_id = record.get("executed_policy_id", "unknown")
        proposal_counts[proposed_id] = proposal_counts.get(proposed_id, 0) + 1
        execution_counts[executed_id] = execution_counts.get(executed_id, 0) + 1
        if record.get("guardrail_reason"):
            guardrail_counts[record["guardrail_reason"]] = guardrail_counts.get(record["guardrail_reason"], 0) + 1
    repair_count = sum(bool(record.get("validation_repairs")) for record in guidance_rows)

    results = {
        "project": "AGQO VN30 AI–QAOA walk-forward",
        "generated_at_local": pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").isoformat(),
        "data": {
            "path": _portable_path(data_path),
            "rows": int(len(data)),
            "ticker_count": int(data.ticker.nunique()),
            "first_date": str(data.date.min().date()),
            "last_date": str(data.date.max().date()),
            "return_price_basis": "VCI OHLC điều chỉnh theo sự kiện quyền; dùng close_adjusted cho lợi suất.",
            "execution_price_basis": "DNSE OHLC thô; dùng open/close cho giá khớp giả định và close×volume làm đại diện thanh khoản.",
            "portfolio_marking_basis": "Dùng tỷ lệ open_adjusted giữa ngày vào và ngày ra; lợi suất tổng hợp, không phải sổ kế toán tiền mặt/cổ phiếu theo từng sự kiện doanh nghiệp.",
            "membership": "Dùng lịch VN30 theo ngày hiệu lực; mỗi tín hiệu chỉ xét thành viên có hiệu lực ở ngày tín hiệu.",
            "membership_point_in_time": True,
            "membership_history_path": _portable_path(members_path),
            "membership_history_coverage": [str(membership_history.valid_from.min().date()), str(membership_history.valid_to.max().date())],
            "corporate_action_completeness": "Nguồn VCI xác nhận giá đã điều chỉnh theo sự kiện quyền; chưa đối chiếu độc lập từng cổ tức, chia tách, cổ phiếu thưởng và quyền mua.",
            "liquidity_measure": "close thô nhân volume là đại diện thanh khoản, không phải giá trị khớp lệnh đã xác nhận.",
            "news_context_enabled": bool(news_records),
            "news_records_loaded": len(news_records),
            "news_usage": "GDELT source first-seen timestamps and ticker-name query counts only; no headline, article text, sentiment or causal attribution." if news_records else "No external news records supplied; news is not used in guidance or result explanation.",
            "opening_price_assumption": "Mô phỏng khớp tại giá mở cửa phiên kế tiếp; giá thô, chưa tính trượt giá/thuế/lô giao dịch.",
        },
        "config": asdict(config),
        "agqo_guidance": {
            "enabled": guide is not None,
            "controller": "Qwen3-8B NF4 4-bit trên Modal L4 ưu tiên, A10 dự phòng; chỉ chọn mã chính sách QAOA hữu hạn có bằng chứng.",
            "prompt_version": PROMPT_CACHE_VERSION,
            "retrieval_knowledge_base": f"{CORPUS_VERSION}; RAG từ tài liệu dự án phiên bản hóa, có giải nghĩa chỉ số tài chính và QAOA.",
            "finance_support": "Bộ insight định lượng có ngưỡng cố định, bộ phân loại LogisticRegression chỉ dự báo chế độ biến động, và bộ giám sát số học; Qwen không tự tạo luận cứ tài chính.",
            "execution_guardrail": {
                "enabled": bool(guide),
                "minimum_completed_periods": 6,
                "feasible_sample_floor": 0.90,
                "regret_warning_floor": 0.10,
                "purpose": "Preserve the LLM proposal for audit; execute the proposal only when completed-history evidence passes numeric feasibility, regret and risk checks against the rule selector.",
                "fallback_count": int(sum(guardrail_counts.values())),
                "repaired_llm_response_count": repair_count,
                "proposal_policy_counts": proposal_counts,
                "executed_policy_counts": execution_counts,
                "fallback_reasons": guardrail_counts,
            },
            "policy_catalog": policy_catalog() if guide else [],
            "decisions": guidance_rows,
            "decision_count": len(guidance_rows),
            "recorded_token_usage": recorded_llm_tokens,
            "information_cutoff_rule": "At signal t, provide market statistics through t and portfolio results with exit dates no later than t.",
            "selection_parameters": ["n_qubits", "risk_aversion", "shrinkage", "mixer", "mixer_layout", "depth", "shots"],
            "counterfactual_policy_benchmarks": (
                "Mỗi tín hiệu chạy bóng mọi cấu hình cố định để xây bảng chứng cứ; LLM chỉ nhận số liệu của các kỳ đã đóng."
                if guide else None
            ),
            "policy_strategy_names": policy_strategy_names if guide else {},
            "optimizer_and_seed_policy": {
                "optimizer": "COBYLA",
                "max_evaluations_per_seed": config.qaoa_max_evaluations,
                "seeds": list(config.qaoa_seeds),
                "selection": "Nghiệm khả thi tốt nhất trong các hạt giống; nếu không có mẫu khả thi thì dùng nghiệm chính xác và ghi rõ dự phòng.",
            },
        },
        "ai": {
            "feature_names": list(features.columns),
            "target": f"Biến động VN30 năm hóa trong {config.horizon} phiên kế tiếp vượt ngưỡng phân vị 70% của tập huấn luyện.",
            "training_end": config.train_end,
            "validation_start": config.validation_start,
            "validation_end": config.validation_end,
            "test_start": config.test_start,
            "chosen_c": float(model.chosen_c),
            "validation_log_loss_by_c": {
                str(c): loss for c, loss in model.validation_log_losses
            },
            "training_samples_before_validation": model.training_samples,
            "validation_samples": model.validation_samples,
            "validation_high_volatility_rate": model.validation_prevalence,
            "threshold_annualized_volatility": float(model.threshold),
            "training_prevalence_after_validation": float(model.training_prevalence),
            "metrics": ai_metrics,
            "monthly_signals": signal_rows,
            "daily_forecasts": [
                {
                    "date": str(index.date()),
                    "probability_high_volatility": float(row.probability_high_volatility),
                    "actual_high_volatility": int(row.actual_high_volatility),
                    "training_prevalence": float(row.training_prevalence),
                }
                for index, row in oos_daily.iterrows()
            ],
        },
        "portfolio": {
            "capital_vnd": config.capital_vnd,
            "fee_bps_base": config.fee_bps,
            "adtv_participation_base": config.adtv_participation,
            "period_count": len(entries),
            "entry_dates": [str(date.date()) for date in entries],
            "exit_dates": [str(date.date()) for date in exits],
            "performance": performance,
            "selection_summary": selection_summary,
            "comparisons": comparisons,
            "cost_capacity_sensitivity": cost_sensitivity,
        },
        "qaoa": {
            "implementation": "Mô phỏng véc-tơ trạng thái bằng NumPy; COBYLA tối ưu góc bằng lấy mẫu hữu hạn; chưa chạy QPU.",
            "objective": (
                "AGQO: min λ(xᵀΣαx)/K² − (μᵀx)/K + 12 × phí × Σᵢ|xᵢ/K − wᵢ_trước|; ràng buộc tổng xᵢ=K."
                if guide else
                "Đường cơ sở: min λ(xᵀΣαx)/K² − (μᵀx)/K; ràng buộc tổng xᵢ=K. Phí được trừ trong sổ giao dịch."
            ),
            "transaction_cost_in_objective": bool(guide),
            "primary_qaoa_strategy": AGQO_STRATEGY_NAME if guide else strategy_names[6],
            "n_qubits": config.qaoa_candidates,
            "agqo_qubit_options": sorted({policy.n_qubits for policy in POLICIES.values()}) if guide else [],
            "agqo_max_candidate_pool": config.agqo_candidate_pool,
            "k": config.k,
            "p_values": sorted({policy.depth for policy in POLICIES.values()}) if guide else [1, 2],
            "mixers": ["X có phạt cardinality", "XY bảo toàn số bit 1 với đồ thị đường thẳng, vòng, đầy đủ hoặc tương quan"],
            "seeds": list(config.qaoa_seeds),
            "shots_per_evaluation": config.qaoa_shots,
            "max_evaluations_per_seed": config.qaoa_max_evaluations,
            "exact_comparison_scope": "Nghiệm chính xác trên cùng N ứng viên và cùng λ, α, phí, tỷ trọng trước; các cấu hình N=8/12/16 đều có đối chứng riêng.",
            "normalized_objective_regret_definition": "(điểm QAOA tốt nhất − điểm tối ưu chính xác) / (điểm lớn nhất − điểm nhỏ nhất trên cùng N và K tổ hợp khả thi).",
            "monthly_runs": qaoa_rows,
            "normalized_regret_summary": (
                pd.DataFrame(optimality_rows).groupby("variant").regret.agg(
                    ["count", "mean", "median", "max"]
                ).to_dict("index") if optimality_rows else {}
            ),
            "quality_summary": qaoa_summary,
            "statevector_basis_states": 1 << config.qaoa_candidates,
            "feasible_combinations_per_month": comb(config.qaoa_candidates, config.k),
            "dense_cost_pair_terms_per_layer": int(
                config.qaoa_candidates * (config.qaoa_candidates - 1) / 2
            ),
            "solver_runtime_seconds": {
                "exact_full_universe_total": exact_full_solve_seconds,
                "exact_12_universe_total": exact_12_solve_seconds,
                "exact_ai12_universe_total": exact_ai12_solve_seconds,
                "exact_agqo_universe_total": exact_agqo_solve_seconds,
                "agqo_qaoa_total": agqo_qaoa_seconds,
                "policy_catalog_exact_total": policy_catalog_exact_solve_seconds,
                "policy_catalog_qaoa_total": policy_catalog_qaoa_seconds,
                "end_to_end_elapsed": perf_counter() - started,
            },
        },
        "limitations": [
            "Chỉ có khoảng 16 kỳ nắm giữ tháng kiểm tra; chưa đủ để kết luận lợi thế kinh tế ổn định.",
            "Giá OHLCV chưa xác nhận điều chỉnh cổ tức, chia tách và quyền mua.",
            "Dùng ảnh chụp thành phần VN30 ngày 02/10/2026 cho lịch sử; có thiên lệch sống sót.",
            "Khả năng khớp lệnh chỉ mô phỏng giới hạn theo tỷ lệ ADTV; không có dữ liệu sổ lệnh, bước giá, thuế và lô giao dịch.",
            "AI dùng nhãn biến động tương lai 21 phiên chồng lấn; số dự báo ngày không độc lập.",
            "QAOA là mô phỏng véc-tơ trạng thái cổ điển, không phải bằng chứng ưu thế lượng tử hay kết quả QPU.",
            "LLM chỉ chọn trong danh mục chính sách cho phép; hiệu quả chính sách AGQO phải được đánh giá ngoài mẫu và không được suy diễn thành bảo đảm lợi nhuận.",
            *(
                [
                    "AGQO dùng lợi nhuận của các kỳ kiểm tra đã đóng để điều chỉnh lựa chọn ở kỳ sau; đây là walk-forward thích nghi, cần thêm một giai đoạn cuối khóa riêng trước khi kết luận tổng quát."
                ]
                if guide else []
            ),
        ],
    }
    out = Path(output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return results
