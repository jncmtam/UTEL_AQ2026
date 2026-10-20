"""Ước lượng lợi nhuận và rủi ro theo cửa sổ đã khóa trong proposal."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import ledoit_wolf

from .ai import regime_controls, risk_aversion_from_probability
from .problem import PortfolioProblem


def estimate_annual_inputs(
    daily_returns: pd.DataFrame,
    covariance_method: str = "sample",
    diagonal_alpha: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Trả về mu và Sigma năm hóa; không dự báo lợi nhuận riêng theo mã."""
    values = daily_returns.to_numpy(dtype=float)
    if values.ndim != 2 or values.shape[0] < 2 or not np.isfinite(values).all():
        raise ValueError("Cần ma trận lợi nhuận ngày đầy đủ, hữu hạn và có ít nhất 2 phiên.")
    mu = values.mean(axis=0) * 252
    if covariance_method == "ledoit_wolf":
        covariance, _ = ledoit_wolf(values)
    elif covariance_method == "sample":
        covariance = np.cov(values, rowvar=False, ddof=1)
    else:
        raise ValueError("Phương pháp hiệp phương sai là sample hoặc ledoit_wolf.")
    covariance = covariance * 252
    if diagonal_alpha is not None:
        alpha = float(np.clip(diagonal_alpha, 0.10, 0.70))
        covariance = (1 - alpha) * covariance + alpha * np.diag(np.diag(covariance))
    return mu, covariance


def build_regime_problem(
    daily_returns: pd.DataFrame,
    tickers: tuple[str, ...],
    probability_high_volatility: float,
    k: int = 6,
    ai_enabled: bool = True,
    adaptive_lambda: bool = True,
    adaptive_shrinkage: bool = True,
    transaction_cost_bps: float | np.ndarray = 0.0,
    previous_weights: np.ndarray | None = None,
    rebalances_per_year: int = 12,
    risk_aversion_min: float = 2.0,
    risk_aversion_max: float = 10.0,
) -> tuple[PortfolioProblem, dict[str, object]]:
    """Dựng V0 hoặc bài toán có phí đổi danh mục; mọi bộ giải dùng cùng mục tiêu."""
    if daily_returns.shape[1] != len(tickers):
        raise ValueError("Số cột lợi nhuận phải khớp số mã theo đúng thứ tự.")
    sample_mu, sample_covariance = estimate_annual_inputs(daily_returns, "sample")
    if ai_enabled:
        probability = float(np.clip(probability_high_volatility, 0.0, 1.0))
        adaptive_risk = risk_aversion_from_probability(
            probability, minimum=risk_aversion_min, maximum=risk_aversion_max
        )
        _, adaptive_alpha = regime_controls(probability)
        risk_aversion = adaptive_risk if adaptive_lambda else 5.0
        alpha = adaptive_alpha if adaptive_shrinkage else 0.40
    else:
        # Đối chứng không AI trong cùng họ dùng đúng λ=5, α=0,40 của proposal.
        probability, risk_aversion, alpha = float("nan"), 5.0, 0.40
    covariance = (1 - alpha) * sample_covariance + alpha * np.diag(np.diag(sample_covariance))
    cost_values = np.asarray(transaction_cost_bps, dtype=float)
    if cost_values.ndim == 0:
        cost_values = np.full(len(tickers), float(cost_values), dtype=float)
    if cost_values.shape != (len(tickers),) or not np.isfinite(cost_values).all() or (cost_values < 0).any():
        raise ValueError("Chi phí giao dịch phải là số điểm cơ bản không âm cho mỗi mã.")
    costs = cost_values / 10_000.0
    problem = PortfolioProblem(
        tickers,
        sample_mu,
        covariance,
        k=k,
        risk_aversion=risk_aversion,
        previous_weights=previous_weights,
        transaction_costs=costs,
        rebalances_per_year=rebalances_per_year,
    )
    metadata = {
        "probability_high_volatility": probability,
        "risk_aversion": risk_aversion,
        "diagonal_alpha": alpha,
        "adaptive_lambda": float(adaptive_lambda and ai_enabled),
        "adaptive_shrinkage": float(adaptive_shrinkage and ai_enabled),
        "mean_transaction_cost_bps": float(cost_values.mean()),
        "transaction_cost_bps_by_asset": cost_values.tolist(),
        "rebalances_per_year": float(rebalances_per_year),
        "risk_aversion_min": float(risk_aversion_min),
        "risk_aversion_max": float(risk_aversion_max),
    }
    return problem, metadata


def build_investable_problem(
    daily_returns: pd.DataFrame,
    tickers: tuple[str, ...],
    probability_high_volatility: float,
    k: int = 6,
    transaction_cost_bps: float | np.ndarray = 25.0,
    previous_weights: np.ndarray | None = None,
    rebalances_per_year: int = 12,
    ai_enabled: bool = True,
    adaptive_lambda: bool = True,
    risk_aversion_min: float = 2.0,
    risk_aversion_max: float = 10.0,
) -> tuple[PortfolioProblem, dict[str, object]]:
    """Tạo V1: AI chỉ điều chỉnh λ; co rút giữ cố định và phí vào hàm mục tiêu."""
    problem, metadata = build_regime_problem(
        daily_returns,
        tickers,
        probability_high_volatility,
        k=k,
        ai_enabled=ai_enabled,
        adaptive_lambda=adaptive_lambda,
        adaptive_shrinkage=False,
        transaction_cost_bps=transaction_cost_bps,
        previous_weights=previous_weights,
        rebalances_per_year=rebalances_per_year,
        risk_aversion_min=risk_aversion_min,
        risk_aversion_max=risk_aversion_max,
    )
    metadata["model_version"] = 1
    return problem, metadata


def build_ledoit_wolf_problem(
    daily_returns: pd.DataFrame,
    tickers: tuple[str, ...],
    k: int = 6,
    risk_aversion: float = 5.0,
    transaction_cost_bps: float | np.ndarray = 0.0,
    previous_weights: np.ndarray | None = None,
    rebalances_per_year: int = 12,
) -> PortfolioProblem:
    """Dựng đối chứng tài chính riêng: lợi nhuận lịch sử và hiệp phương sai Ledoit–Wolf."""
    if daily_returns.shape[1] != len(tickers):
        raise ValueError("Số cột lợi nhuận phải khớp số mã theo đúng thứ tự.")
    mu, covariance = estimate_annual_inputs(daily_returns, "ledoit_wolf")
    cost_values = np.asarray(transaction_cost_bps, dtype=float)
    if cost_values.ndim == 0:
        cost_values = np.full(len(tickers), float(cost_values), dtype=float)
    if cost_values.shape != (len(tickers),) or not np.isfinite(cost_values).all() or (cost_values < 0).any():
        raise ValueError("Chi phí giao dịch phải là số điểm cơ bản không âm cho mỗi mã.")
    return PortfolioProblem(
        tickers,
        mu,
        covariance,
        k=k,
        risk_aversion=risk_aversion,
        previous_weights=previous_weights,
        transaction_costs=cost_values / 10_000.0,
        rebalances_per_year=rebalances_per_year,
    )
