"""Thí nghiệm walk-forward nối dự báo AI, tối ưu QAOA và kiểm định tài chính."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from math import comb
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from .ai import fit_regime_model, fit_regime_model_as_of, forward_volatility, regime_controls
from .estimators import build_ledoit_wolf_problem, build_regime_problem
from .evaluation import compare_monthly_returns, summarize_monthly_returns
from .market_data import load_market_dataset
from .problem import exact_solve_vectorized
from .simulator import optimize_qaoa


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def _qaoa_best(problem, mixer: str, depth: int, config: ResearchConfig):
    results = [
        optimize_qaoa(
            problem,
            mixer=mixer,
            depth=depth,
            seed=seed,
            max_evaluations=config.qaoa_max_evaluations,
            shots=config.qaoa_shots,
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
) -> dict[str, object]:
    """Chạy toàn bộ thí nghiệm AI–QAOA trên kỳ kiểm tra khóa trước."""
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

    strategy_names = (
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
    targets: dict[str, list[tuple[str, ...]]] = {name: [] for name in strategy_names}
    signal_rows = []
    qaoa_rows = []
    optimality_rows = []
    entries, exits, liquidities = [], [], []
    exact_full_solve_seconds = 0.0
    exact_12_solve_seconds = 0.0
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
        exact12_tickers = tuple(candidates[i] for i in np.flatnonzero(exact12_bits))
        targets[strategy_names[5]].append(exact12_tickers)
        all_scores = []
        from itertools import combinations
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
    key_names = (strategy_names[0], strategy_names[3], strategy_names[5], strategy_names[6], strategy_names[7], strategy_names[8])
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
    for variant in ("X_p1", "X_p2", "XY_p1"):
        subset = [row for row in qaoa_rows if row["variant"] == variant]
        runs = [run for row in subset for run in row["runs"]]
        regrets = [
            row["normalized_objective_regret"]
            for row in subset
            if row["normalized_objective_regret"] is not None
        ]
        qaoa_summary[variant] = {
            "monthly_instances": len(subset),
            "seed_runs": len(runs),
            "feasible_seed_run_fraction": float(
                np.mean([run["best_bits"] is not None for run in runs])
            ) if runs else None,
            "instances_with_regret_le_5_percent": int(
                sum(regret <= 0.05 for regret in regrets)
            ),
            "mean_normalized_regret": float(np.mean(regrets)) if regrets else None,
            "median_normalized_regret": float(np.median(regrets)) if regrets else None,
            "mean_best_seed_feasible_probability": float(np.mean([
                row["best_sampled_feasible_probability"] for row in subset
                if row["best_sampled_feasible_probability"] is not None
            ])) if subset else None,
            "total_cpu_simulation_seconds": float(sum(
                run["elapsed_seconds"] for run in runs
            )),
        }

    cost_sensitivity = {}
    for name in (strategy_names[3], strategy_names[6], strategy_names[7], strategy_names[8]):
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
            "objective": "min λ(xᵀΣx)/K² − (μᵀx)/K, với Σ co về đường chéo theo α; ràng buộc tổng xᵢ=K.",
            "primary_qaoa_strategy": strategy_names[6],
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
        ],
    }
    out = Path(output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return results
