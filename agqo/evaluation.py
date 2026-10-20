"""Đánh giá lợi nhuận tháng, chi phí đổi danh mục và sức chứa giao dịch."""

from __future__ import annotations

from math import ceil

import numpy as np
import pandas as pd


def _cost_matrix_bps(
    transaction_cost_bps: float | pd.Series | pd.DataFrame | np.ndarray,
    index: pd.Index,
    columns: pd.Index,
) -> np.ndarray:
    if np.isscalar(transaction_cost_bps):
        values = np.full((len(index), len(columns)), float(transaction_cost_bps), dtype=float)
    elif isinstance(transaction_cost_bps, pd.Series):
        values = np.broadcast_to(
            transaction_cost_bps.reindex(columns).to_numpy(dtype=float),
            (len(index), len(columns)),
        ).copy()
    elif isinstance(transaction_cost_bps, pd.DataFrame):
        values = transaction_cost_bps.reindex(index=index, columns=columns).to_numpy(dtype=float)
    else:
        raw = np.asarray(transaction_cost_bps, dtype=float)
        if raw.ndim == 0:
            values = np.full((len(index), len(columns)), float(raw), dtype=float)
        elif raw.shape == (len(columns),):
            values = np.broadcast_to(raw, (len(index), len(columns))).copy()
        elif raw.shape == (len(index), len(columns)):
            values = raw.copy()
        else:
            raise ValueError("Chi phí phải là số, vector theo mã hoặc bảng theo tháng và mã.")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Chi phí giao dịch phải hữu hạn và không âm.")
    return values / 10_000.0


def simulate_monthly_portfolios(
    target_weights: pd.DataFrame,
    monthly_asset_returns: pd.DataFrame,
    transaction_cost_bps: float | pd.Series | pd.DataFrame | np.ndarray = 25.0,
    initial_weights: pd.Series | None = None,
    adtv: pd.DataFrame | None = None,
    initial_capital: float = 100_000_000.0,
    max_adtv_participation: float = 0.05,
) -> pd.DataFrame:
    """Tính lợi nhuận ròng tháng với lệnh mục tiêu tại đầu mỗi kỳ.

    Mỗi hàng của hai bảng ứng với cùng một lần tái cân bằng: trọng số mục tiêu
    được khớp ở đầu kỳ, rồi lợi nhuận tài sản của kỳ được áp dụng. Mô hình giả
    định khớp đủ lệnh; khi có ADTV, hàm chỉ đánh dấu vi phạm sức chứa chứ không
    tự giả lập phần khớp thiếu. Chi phí được tính trên cả giá trị mua và bán.
    """
    if not target_weights.index.equals(monthly_asset_returns.index):
        raise ValueError("Ngày của trọng số mục tiêu và lợi nhuận phải trùng khớp.")
    if not target_weights.columns.equals(monthly_asset_returns.columns):
        raise ValueError("Cột tài sản của trọng số mục tiêu và lợi nhuận phải cùng thứ tự.")
    if target_weights.empty or target_weights.columns.empty:
        raise ValueError("Cần ít nhất một kỳ và một tài sản.")
    if not target_weights.index.is_unique or not target_weights.columns.is_unique:
        raise ValueError("Ngày và mã tài sản không được trùng.")
    weights = target_weights.to_numpy(dtype=float)
    returns = monthly_asset_returns.to_numpy(dtype=float)
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Trọng số mục tiêu phải hữu hạn và không âm.")
    if not np.allclose(weights.sum(axis=1), 1.0, atol=1e-8):
        raise ValueError("Mỗi danh mục mục tiêu phải đầu tư đủ 100% vốn.")
    if not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("Lợi nhuận tài sản phải hữu hạn và lớn hơn -100% mỗi kỳ.")
    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("Vốn ban đầu phải hữu hạn và dương.")
    if not np.isfinite(max_adtv_participation) or not 0 < max_adtv_participation <= 1:
        raise ValueError("Giới hạn tham gia ADTV phải hữu hạn và thuộc (0,1].")

    columns = target_weights.columns
    if initial_weights is None:
        current = np.zeros(len(columns), dtype=float)
    else:
        if not initial_weights.index.is_unique:
            raise ValueError("Mã tài sản trong trọng số ban đầu không được trùng.")
        aligned = initial_weights.reindex(columns)
        if aligned.isna().any():
            raise ValueError("Trọng số ban đầu phải có giá trị cho mọi mã trong danh mục.")
        current = aligned.to_numpy(dtype=float)
        if not np.isfinite(current).all() or (current < 0).any() or current.sum() > 1 + 1e-8:
            raise ValueError("Trọng số ban đầu phải hữu hạn, không âm và tổng không quá 100%.")

    cost_rates = _cost_matrix_bps(transaction_cost_bps, target_weights.index, columns)
    adtv_values = None
    if adtv is not None:
        if not adtv.index.equals(target_weights.index) or not adtv.columns.equals(columns):
            raise ValueError("Bảng ADTV phải khớp ngày và thứ tự mã của danh mục.")
        adtv_values = adtv.to_numpy(dtype=float)
        if not np.isfinite(adtv_values).all() or (adtv_values <= 0).any():
            raise ValueError("ADTV phải hữu hạn và dương cho mọi lệnh cần đánh giá.")

    rows = []
    net_capital = gross_capital = float(initial_capital)
    for t, date in enumerate(target_weights.index):
        target = weights[t]
        delta = target - current
        traded = np.abs(delta)
        two_way_turnover = float(traded.sum())
        one_way_turnover = (
            float(target.sum()) if current.sum() <= 1e-12 else 0.5 * two_way_turnover
        )
        transaction_cost = float(cost_rates[t] @ traded)
        if transaction_cost >= 1:
            raise ValueError("Chi phí thực hiện một lần tái cân bằng không được vượt toàn bộ vốn.")
        gross_return = float(target @ returns[t])
        net_return = float((1 - transaction_cost) * (1 + gross_return) - 1)
        capital_before_trade = net_capital
        net_capital *= 1 + net_return
        gross_capital *= 1 + gross_return
        net_nav = net_capital / initial_capital
        gross_nav = gross_capital / initial_capital

        if adtv_values is None:
            required_participation = float("nan")
            within_capacity = None
        else:
            traded_value = traded * capital_before_trade
            participations = traded_value / adtv_values[t]
            required_participation = float(np.max(participations))
            within_capacity = bool(required_participation <= max_adtv_participation)

        rows.append(
            {
                "date": date,
                "pre_trade_weights": current.tolist(),
                "target_weights": target.tolist(),
                "trade_weight_changes": delta.tolist(),
                "gross_return": gross_return,
                "transaction_cost_rate": transaction_cost,
                "net_return": net_return,
                "two_way_turnover": two_way_turnover,
                "one_way_turnover": one_way_turnover,
                "gross_nav": gross_nav,
                "net_nav": net_nav,
                "required_max_adtv_participation": required_participation,
                "within_adtv_limit": within_capacity,
            }
        )
        portfolio_after_returns = target * (1 + returns[t])
        current = portfolio_after_returns / (1 + gross_return)
        rows[-1]["post_period_weights"] = current.tolist()
    return pd.DataFrame(rows).set_index("date")


def summarize_monthly_returns(
    monthly_returns: pd.Series, monthly_risk_free_rate: float = 0.0
) -> dict[str, float | int]:
    """Tóm tắt lợi nhuận tháng bằng CAGR, biến động, Sharpe và mức giảm vốn."""
    values = monthly_returns.to_numpy(dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Cần chuỗi lợi nhuận tháng hữu hạn, không rỗng và lớn hơn -100%.")
    if not np.isfinite(monthly_risk_free_rate) or monthly_risk_free_rate <= -1:
        raise ValueError("Lãi suất phi rủi ro tháng phải hữu hạn và lớn hơn -100%.")
    wealth = np.cumprod(1 + values)
    cagr = float(wealth[-1] ** (12 / len(values)) - 1)
    volatility = float(np.std(values, ddof=1) * np.sqrt(12)) if len(values) > 1 else float("nan")
    excess = values - monthly_risk_free_rate
    excess_std = float(np.std(excess, ddof=1)) if len(values) > 1 else 0.0
    sharpe = float(np.mean(excess) / excess_std * np.sqrt(12)) if excess_std > 0 else float("nan")
    peaks = np.maximum.accumulate(np.concatenate(([1.0], wealth)))[1:]
    drawdowns = wealth / peaks - 1
    downside_deviation = float(np.sqrt(np.mean(np.minimum(excess, 0.0) ** 2)))
    sortino = (
        float(np.mean(excess) / downside_deviation * np.sqrt(12))
        if downside_deviation > 0
        else float("nan")
    )
    return {
        "months": int(len(values)),
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": float(np.min(drawdowns)),
        "positive_month_fraction": float(np.mean(values > 0)),
        "ending_value_per_unit": float(wealth[-1]),
    }


def paired_block_bootstrap_mean_ci(
    monthly_excess_returns: pd.Series | np.ndarray,
    block_length: int = 3,
    resamples: int = 10_000,
    seed: int = 11,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """Khoảng tin cậy lấy mẫu khối cho lợi nhuận vượt đối chuẩn theo tháng."""
    values = np.asarray(monthly_excess_returns, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Chênh lệch lợi nhuận phải là vector hữu hạn, không rỗng.")
    if not isinstance(block_length, int) or block_length < 1:
        raise ValueError("Độ dài khối phải là số nguyên dương.")
    if not isinstance(resamples, int) or resamples < 1:
        raise ValueError("Số lần lấy mẫu lại phải là số nguyên dương.")
    if not 0 < confidence < 1:
        raise ValueError("Mức tin cậy phải nằm trong khoảng (0,1).")

    rng = np.random.Generator(np.random.PCG64(seed))
    blocks_per_sample = ceil(len(values) / block_length)
    starts = rng.integers(0, len(values), size=(resamples, blocks_per_sample))
    offsets = np.arange(block_length)
    indices = (starts[:, :, None] + offsets) % len(values)
    samples = indices.reshape(resamples, -1)[:, : len(values)]
    annualized_means = 12 * values[samples].mean(axis=1)
    tail = (1 - confidence) / 2
    lower, upper = np.quantile(annualized_means, (tail, 1 - tail))
    return {
        "months": int(len(values)),
        "block_length": block_length,
        "resamples": resamples,
        "annualized_mean_excess": float(12 * values.mean()),
        "confidence": float(confidence),
        "lower": float(lower),
        "upper": float(upper),
        "seed": int(seed),
    }


def compare_monthly_returns(
    candidate_returns: pd.Series,
    benchmark_returns: pd.Series,
    candidate_name: str = "candidate",
    benchmark_name: str = "benchmark",
    monthly_risk_free_rate: float = 0.0,
    block_length: int = 3,
    resamples: int = 10_000,
    seed: int = 11,
) -> dict[str, object]:
    """So sánh hai chuỗi lợi nhuận cùng tháng và ước lượng khoảng tin cậy theo cặp."""
    if not candidate_returns.index.is_unique or not benchmark_returns.index.is_unique:
        raise ValueError("Ngày trong hai chuỗi lợi nhuận không được trùng.")
    paired = pd.concat(
        [candidate_returns.rename("candidate"), benchmark_returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    if paired.empty:
        raise ValueError("Hai chuỗi không có tháng hợp lệ chung để so sánh.")
    if (paired <= -1).any().any() or not np.isfinite(paired.to_numpy(dtype=float)).all():
        raise ValueError("Lợi nhuận ghép cặp phải hữu hạn và lớn hơn -100%.")

    candidate = paired["candidate"]
    benchmark = paired["benchmark"]
    active = candidate - benchmark
    return {
        "months": int(len(paired)),
        "candidate_name": candidate_name,
        "benchmark_name": benchmark_name,
        "candidate_metrics": summarize_monthly_returns(candidate, monthly_risk_free_rate),
        "benchmark_metrics": summarize_monthly_returns(benchmark, monthly_risk_free_rate),
        "annualized_mean_active_return": float(12 * active.mean()),
        "positive_active_month_fraction": float((active > 0).mean()),
        "active_return_confidence_interval": paired_block_bootstrap_mean_ci(
            active,
            block_length=block_length,
            resamples=resamples,
            seed=seed,
        ),
    }
