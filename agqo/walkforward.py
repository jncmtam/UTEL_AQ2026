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
from .guide import POLICIES, policy_catalog, validate_guidance
from .market_data import load_market_dataset
from .problem import PortfolioProblem, exact_solve_vectorized
from .simulator import optimize_qaoa


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGQO_STRATEGY_NAME = "AGQO LLM→QAOA / chính sách thích nghi / 12 mã thanh khoản cao"
POLICY_STRATEGY_PREFIX = "Đối chứng chính sách QAOA cố định / "


def _policy_strategy_name(policy_id: str) -> str:
    return f"{POLICY_STRATEGY_PREFIX}{policy_id}"


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
    capital_vnd: float = 100_000_000.0
    fee_bps: float = 25.0
    adtv_participation: float = 0.05
    qaoa_seeds: tuple[int, ...] = (11, 23, 47)
    qaoa_shots: int = 512
    qaoa_max_evaluations: int = 50


def _load_panels(data_path: str | Path, members_path: str | Path):
    data, members = load_market_dataset(data_path, members_path)
    tickers = tuple(members["ticker"].astype(str))
    stock = data.loc[data.instrument_type == "stock"]
    index = data.loc[data.instrument_type == "index"]
    index_open = index.pivot(index="date", columns="ticker", values="open").sort_index()
    index_close = index.pivot(index="date", columns="ticker", values="close").sort_index()
    dates = index_close[["VN30", "VNINDEX"]].dropna().index
    index_open = index_open.reindex(index=dates, columns=["VN30", "VNINDEX"])
    index_close = index_close.reindex(index=dates, columns=["VN30", "VNINDEX"])
    stock_open = stock.pivot(index="date", columns="ticker", values="open").reindex(
        index=dates, columns=tickers
    ).sort_index()
    stock_close = stock.pivot(index="date", columns="ticker", values="close").reindex(
        index=dates, columns=tickers
    ).sort_index()
    volume = stock.pivot(index="date", columns="ticker", values="volume").reindex(
        index=dates, columns=tickers
    ).sort_index()
    stock_returns = stock_close.pct_change(fill_method=None)
    index_returns = index_close["VN30"].pct_change(fill_method=None).rename("VN30")
    traded_value = stock_close * volume
    return (
        data, members, dates, stock_open, stock_close, stock_returns,
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
):
    history = stock_returns.loc[:signal].tail(config.lookback)
    eligible = tuple(
        ticker for ticker in tickers if int(history[ticker].count()) >= config.min_history
    )
    complete = history.loc[:, eligible].dropna(how="any")
    if len(complete) < config.min_history:
        raise ValueError(
            f"Chỉ còn {len(complete)} phiên hoàn chỉnh tại {signal.date()}, "
            f"thấp hơn ngưỡng {config.min_history}."
        )
    liq = traded_value.loc[:signal].tail(20).mean().reindex(eligible).dropna()
    candidates = tuple(liq.sort_values(ascending=False, kind="stable").head(
        config.qaoa_candidates
    ).index)
    if len(candidates) != config.qaoa_candidates:
        raise ValueError(f"Tại {signal.date()} chỉ có {len(candidates)} mã đủ thanh khoản cho QAOA.")
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
    return PortfolioProblem(
        tickers=tickers,
        mu=mu,
        covariance=covariance,
        k=k,
        risk_aversion=policy.risk_aversion,
        previous_weights=previous_weights,
        transaction_costs=np.full(len(tickers), fee_bps / 10_000, dtype=float),
        rebalances_per_year=rebalances_per_year,
    )


def _past_strategy_metrics(
    signal: pd.Timestamp,
    strategy_targets: dict[str, list[tuple[str, ...]]],
    tickers: tuple[str, ...],
    stock_open: pd.DataFrame,
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
            targets[:completed], tickers, stock_open,
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
    fee_bps: float,
) -> dict[str, Any]:
    """Tạo insight có căn cứ từ dữ liệu quá khứ để LLM chọn trong bộ chính sách."""
    values = returns.loc[:, eligible]
    correlation = values.corr().to_numpy(dtype=float)
    upper = correlation[np.triu_indices_from(correlation, k=1)]
    recent = (1 + values.tail(20)).prod(axis=0) - 1
    candidate_liquidity = liquidity.reindex(candidates).dropna()
    bank_share = float(np.mean([groups.get(ticker) == "Ngân hàng" for ticker in eligible]))
    candidate_groups = pd.Series([groups.get(ticker, "Không rõ") for ticker in candidates])
    candidate_group_fraction = (
        candidate_groups.value_counts(normalize=True).sort_index().to_dict()
    )
    row = features.loc[signal]
    insight = {
        "as_of_date": str(signal.date()),
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
    }
    return {
        "as_of_date": str(signal.date()),
        "information_cutoff": "Mọi đặc trưng và kết quả quá khứ chỉ đến hết ngày tín hiệu; không chứa lợi nhuận tương lai.",
        "market_insights": insight,
        "past_completed_strategy_metrics": past_strategy_metrics,
        "past_completed_policy_benchmarks": past_policy_metrics,
        "qaoa_objective_specification": {
            "formula": "λ(xᵀΣαx)/K² − (μᵀx)/K + 12 × phí × Σᵢ|xᵢ/K − wᵢ_trước|",
            "transaction_fee_bps_per_side": float(fee_bps),
            "rebalances_per_year": 12,
            "previous_weight_source": "Danh mục AGQO đã chọn ở kỳ trước; ban đầu là tiền mặt.",
        },
        "policy_catalog": policy_catalog(),
        "selection_objective": (
            "Chọn một chính sách QAOA có triển vọng cải thiện lợi nhuận ròng đã điều chỉnh rủi ro "
            "sau khi đã tính phí đổi danh mục năm hóa theo mục tiêu QAOA; "
            "ưu tiên bằng chứng theo từng chính sách từ các kỳ đã đóng, cân nhắc CAGR, Sharpe, Sortino, "
            "sụt giảm, VaR/CVaR, hệ số lợi nhuận, doanh số, chi phí và số kỳ quan sát. "
            "Không coi vài kỳ ngắn là bằng chứng chắc chắn và không dùng kết quả của kỳ hiện tại."
        ),
    }


def _qaoa_best(
    problem: PortfolioProblem,
    mixer: str,
    depth: int,
    config: ResearchConfig,
    shots: int | None = None,
):
    results = [
        optimize_qaoa(
            problem,
            mixer=mixer,
            depth=depth,
            seed=seed,
            max_evaluations=config.qaoa_max_evaluations,
            shots=config.qaoa_shots if shots is None else shots,
        )
        for seed in config.qaoa_seeds
    ]
    feasible = [result for result in results if result.best_bits is not None]
    best = min(feasible, key=lambda result: result.best_feasible_score) if feasible else None
    return best, results


def _capacity_ledger(
    targets: list[tuple[str, ...]],
    tickers: tuple[str, ...],
    stock_open: pd.DataFrame,
    entries: list[pd.Timestamp],
    exits: list[pd.Timestamp],
    liquidities: list[pd.Series],
    config: ResearchConfig,
    fee_bps: float,
    participation: float,
) -> pd.DataFrame:
    """Mô phỏng tiền mặt, cổ phiếu, phí và lệnh khớp một phần theo ADTV."""
    shares = pd.Series(0.0, index=tickers)
    cash = float(config.capital_vnd)
    previous_nav = cash
    fee_rate = fee_bps / 10_000
    rows = []
    for target, entry, exit_date, adv in zip(targets, entries, exits, liquidities):
        prices_in = stock_open.loc[entry].reindex(tickers)
        prices_out = stock_open.loc[exit_date].reindex(tickers)
        if target and prices_in[list(target)].isna().any():
            raise ValueError(f"Thiếu giá mở cửa ở ngày vào {entry.date()}.")
        if shares.abs().sum() and prices_in[shares.abs() > 0].isna().any():
            raise ValueError(f"Thiếu giá mở cửa để định giá danh mục tại {entry.date()}.")
        if prices_out[shares.abs() > 0].isna().any():
            raise ValueError(f"Thiếu giá mở cửa để định giá danh mục tại {exit_date.date()}.")
        current_values = shares * prices_in.fillna(0.0)
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
            shares[ticker] -= fill / prices_in[ticker]
            fee = fill * fee_rate
            cash += fill - fee
            traded += fill
            cost += fee
        current_values = shares * prices_in.fillna(0.0)
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
            shares[ticker] += fill / prices_in[ticker]
            fee = fill * fee_rate
            cash -= fill + fee
            traded += fill
            cost += fee
        if prices_out[shares.abs() > 0].isna().any():
            raise ValueError(f"Thiếu giá mở cửa để định giá lệnh vừa khớp tại {exit_date.date()}.")
        nav_after_trade = float(cash + (shares * prices_in.fillna(0.0)).sum())
        end_value = float(cash + (shares * prices_out.fillna(0.0)).sum())
        net_return = end_value / previous_nav - 1
        gross_return = net_return
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
) -> dict[str, object]:
    """Chạy các đối chứng hiện tại và tùy chọn bộ điều khiển LLM→QAOA AGQO."""
    started = perf_counter()
    (
        data, members, dates, stock_open, stock_close, stock_returns,
        index_open, index_close, index_returns, traded_value,
    ) = _load_panels(data_path, members_path)
    tickers = tuple(members.ticker.astype(str))
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
    )
    policy_strategy_names = {
        policy_id: _policy_strategy_name(policy_id) for policy_id in sorted(POLICIES)
    }
    strategy_names = baseline_strategy_names + (
        ((AGQO_STRATEGY_NAME,) + tuple(policy_strategy_names.values())) if guide else ()
    )
    targets: dict[str, list[tuple[str, ...]]] = {name: [] for name in strategy_names}
    signal_rows = []
    qaoa_rows = []
    optimality_rows = []
    guidance_rows = []
    entries, exits, liquidities = [], [], []
    group_by_ticker = members.set_index("ticker")["group"].astype(str).to_dict()
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
            signal, tickers, stock_returns, traded_value, config
        )
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
                "qaoa_candidate_tickers": list(candidates),
                "eligible_tickers": list(eligible),
                "complete_estimation_rows": len(returns),
            }
        )
        entries.append(entry)
        exits.append(exit_date)
        liquidities.append(liquidity)

        agqo_policy = None
        if guide is not None:
            history = _past_strategy_metrics(
                signal, targets, tickers, stock_open, entries, exits, liquidities, config
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
            payload = _build_agqo_payload(
                signal, features, probability, returns, eligible, candidates, liquidity,
                group_by_ticker, comparator_metrics, past_policy_metrics, config.fee_bps,
            )
            envelope = guide(payload)
            if not isinstance(envelope, dict):
                raise ValueError("Bộ điều khiển AGQO phải trả về một đối tượng JSON.")
            decision = validate_guidance(envelope.get("decision", {}))
            agqo_policy = POLICIES[decision["policy_id"]]
            guidance_rows.append(
                {
                    "signal_date": str(signal.date()),
                    "information_cutoff": str(signal.date()),
                    "context": payload,
                    "decision": decision,
                    "policy": asdict(agqo_policy),
                    "model": envelope.get("model"),
                    "model_revision": envelope.get("model_revision"),
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
            returns.loc[:, candidates], candidates, probability, "ai_both", config.k
        )
        ai12_problem = ai12_built[0] if isinstance(ai12_built, tuple) else ai12_built
        exact12_start = perf_counter()
        exact12_bits, exact12_score = exact_solve_vectorized(ai12_problem)
        exact12_elapsed = perf_counter() - exact12_start
        exact_12_solve_seconds += exact12_elapsed
        exact_ai12_solve_seconds += exact12_elapsed
        exact12_tickers = tuple(candidates[i] for i in np.flatnonzero(exact12_bits))
        targets[strategy_names[5]].append(exact12_tickers)
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
                    tuple(candidates[i] for i, bit in enumerate(qaoa_best.best_bits) if bit)
                )
                best_score = float(qaoa_best.best_feasible_score)
                regret = float((best_score - exact12_score) / feasible_span) if feasible_span > 0 else 0.0
            qaoa_rows.append(
                {
                    "signal_date": str(signal.date()),
                    "entry_date": str(entry.date()),
                    "variant": label,
                    "n_qubits": ai12_problem.n,
                    "k": config.k,
                    "depth": depth,
                    "mixer": mixer,
                    "exact_score": float(exact12_score),
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
                previous_policy_target = tuple(targets[policy_strategy_names[policy_id]][-1]) if targets[policy_strategy_names[policy_id]] else ()
                policy_problem = _build_policy_problem(
                    returns.loc[:, candidates], candidates, policy_id, config.k,
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
                    policy_problem, policy.mixer, policy.depth, config, shots=policy.shots
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
                target = tuple(candidates[i] for i in np.flatnonzero(selected_bits))
                targets[policy_strategy_names[policy_id]].append(target)
                run_dicts = [run.to_dict() for run in runs]
                variant = f"POLICY:{policy_id}"
                policy_row = {
                    "signal_date": str(signal.date()),
                    "entry_date": str(entry.date()),
                    "variant": variant,
                    "policy_id": policy_id,
                    "n_qubits": policy_problem.n,
                    "k": config.k,
                    "depth": policy.depth,
                    "mixer": policy.mixer,
                    "shots": policy.shots,
                    "exact_score": float(exact_score),
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

            previous_agqo_target = (
                tuple(targets[AGQO_STRATEGY_NAME][-1]) if targets[AGQO_STRATEGY_NAME] else ()
            )
            agqo_problem = _build_policy_problem(
                returns.loc[:, candidates], candidates, agqo_policy.policy_id, config.k,
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
                shots=agqo_policy.shots,
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
            selected_target = tuple(candidates[i] for i in np.flatnonzero(selected_bits))
            targets[AGQO_STRATEGY_NAME].append(selected_target)
            agqo_qaoa_seconds += sum(run.elapsed_seconds for run in agqo_runs)
            agqo_row = {
                "signal_date": str(signal.date()),
                "entry_date": str(entry.date()),
                "variant": "AGQO",
                "policy_id": agqo_policy.policy_id,
                "n_qubits": agqo_problem.n,
                "k": config.k,
                "depth": agqo_policy.depth,
                "mixer": agqo_policy.mixer,
                "shots": agqo_policy.shots,
                "exact_score": float(agqo_exact_score),
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
            signal_rows[-1]["agqo_policy_parameters"] = asdict(agqo_policy)
            guidance_rows[-1]["qaoa_result"] = {
                key: agqo_row[key]
                for key in (
                    "exact_score", "qaoa_best_score", "normalized_objective_regret",
                    "best_seed", "best_sampled_feasible_probability", "fallback_used",
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
            strategy_targets, tickers, stock_open, entries, exits, liquidities,
            config, config.fee_bps, config.adtv_participation,
        )
        for name, strategy_targets in targets.items()
    }
    gross_ledgers = {
        name: _capacity_ledger(
            strategy_targets, tickers, stock_open, entries, exits, liquidities,
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
    group_by_ticker = members.set_index("ticker")["group"].astype(str).to_dict()
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
    ) + ((AGQO_STRATEGY_NAME,) if guide else ())
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
        (("AGQO",) + tuple(f"POLICY:{policy_id}" for policy_id in sorted(POLICIES)))
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
    ) + ((AGQO_STRATEGY_NAME,) if guide else ())
    if guide:
        sensitivity_names += tuple(policy_strategy_names.values())
    for name in sensitivity_names:
        rows = []
        for fee in (10.0, 25.0, 50.0):
            for capacity in (0.01, 0.05, 0.10):
                ledger = _capacity_ledger(
                    targets[name], tickers, stock_open, entries, exits, liquidities,
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

    results = {
        "project": "AGQO VN30 AI–QAOA walk-forward",
        "generated_at_local": pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").isoformat(),
        "data": {
            "path": _portable_path(data_path),
            "rows": int(len(data)),
            "ticker_count": int(data.ticker.nunique()),
            "first_date": str(data.date.min().date()),
            "last_date": str(data.date.max().date()),
            "price_basis": "OHLCV thô; trạng thái điều chỉnh cổ tức/quyền chưa xác nhận.",
            "membership": "Ảnh chụp thành phần VN30 hiện tại áp ngược lịch sử; tồn tại thiên lệch sống sót.",
            "opening_price_assumption": "Mô phỏng khớp tại giá mở cửa phiên kế tiếp; giá thô, chưa tính trượt giá/thuế/lô giao dịch.",
        },
        "config": asdict(config),
        "agqo_guidance": {
            "enabled": guide is not None,
            "controller": "LLM trên Modal; đầu ra JSON có cấu trúc, chọn trong danh mục chính sách hữu hạn.",
            "policy_catalog": policy_catalog() if guide else [],
            "decisions": guidance_rows,
            "decision_count": len(guidance_rows),
            "recorded_token_usage": recorded_llm_tokens,
            "information_cutoff_rule": "Tại tín hiệu t chỉ cung cấp chỉ số thị trường đến t và kết quả danh mục có ngày thoát lệnh không muộn hơn t.",
            "selection_parameters": ["risk_aversion", "shrinkage", "mixer", "depth", "shots"],
            "counterfactual_policy_benchmarks": (
                "Mỗi tín hiệu chạy bóng tất cả chính sách trong danh mục; LLM chỉ nhận số liệu tài chính của những kỳ đã đóng."
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
            "implementation": "Mô phỏng véc-tơ trạng thái bằng NumPy; COBYLA tối ưu góc; lấy mẫu hữu hạn; chưa chạy QPU.",
            "objective": (
                "AGQO: min λ(xᵀΣαx)/K² − (μᵀx)/K + 12 × phí × Σᵢ|xᵢ/K − wᵢ_trước|; ràng buộc tổng xᵢ=K."
                if guide else
                "Đường cơ sở: min λ(xᵀΣαx)/K² − (μᵀx)/K; ràng buộc tổng xᵢ=K. Phí được trừ trong sổ giao dịch."
            ),
            "transaction_cost_in_objective": bool(guide),
            "primary_qaoa_strategy": AGQO_STRATEGY_NAME if guide else strategy_names[6],
            "n_qubits": config.qaoa_candidates,
            "k": config.k,
            "p_values": [1, 2],
            "mixers": ["X có phạt cardinality", "XY vòng bảo toàn số bit 1"],
            "seeds": list(config.qaoa_seeds),
            "shots_per_evaluation": config.qaoa_shots,
            "max_evaluations_per_seed": config.qaoa_max_evaluations,
            "exact_comparison_scope": "Nghiệm chính xác trên cùng 12 ứng viên thanh khoản tại mỗi tín hiệu; thêm nghiệm chính xác trên toàn bộ mã đủ điều kiện làm đối chứng tài chính.",
            "normalized_objective_regret_definition": "(điểm QAOA tốt nhất − điểm tối ưu chính xác) / (điểm lớn nhất − điểm nhỏ nhất trên mọi tổ hợp khả thi N=12, K=6).",
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
                "exact_agqo_12_universe_total": exact_agqo_solve_seconds,
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
