"""Đặc trưng thị trường không nhìn trước và bộ điều chỉnh AI đúng proposal."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.preprocessing import StandardScaler


def build_daily_features(
    market_returns: pd.Series,
    asset_returns: pd.DataFrame,
    traded_value: pd.DataFrame,
    members_by_date: dict[pd.Timestamp, tuple[str, ...]] | None = None,
    halted_fraction: pd.Series | None = None,
) -> pd.DataFrame:
    """Tạo đặc trưng tại phiên t từ dữ liệu đến t; bỏ hẳn cột tạm ngừng nếu thiếu nguồn."""
    market_returns = market_returns.sort_index().astype(float)
    asset_returns = asset_returns.reindex(market_returns.index).astype(float)
    traded_value = traded_value.reindex(index=market_returns.index, columns=asset_returns.columns)
    rows = []
    for t in range(len(market_returns)):
        row: dict[str, float] = {}
        current_date = market_returns.index[t]
        for window in (20, 60, 120):
            sample = market_returns.iloc[max(0, t - window + 1) : t + 1]
            row[f"vol_{window}"] = float(sample.std(ddof=1) * np.sqrt(252)) if len(sample) == window else np.nan
        for window in (20, 60):
            sample = market_returns.iloc[max(0, t - window + 1) : t + 1]
            row[f"return_{window}"] = float(np.expm1(sample.sum())) if len(sample) == window else np.nan
        row["vol_ratio_20_120"] = row["vol_20"] / max(row["vol_120"], 1e-12)
        asset_window = asset_returns.iloc[max(0, t - 59) : t + 1]
        members = (members_by_date or {}).get(current_date, tuple(asset_returns.columns))
        valid_members = [name for name in members if name in asset_window]
        correlations = asset_window.loc[:, valid_members].corr(min_periods=50)
        upper = correlations.where(np.triu(np.ones(correlations.shape), 1).astype(bool)).stack().dropna()
        row["median_corr_60"] = float(upper.median()) if not upper.empty else np.nan
        asset_history = asset_returns.iloc[max(0, t - 251) : t + 1].loc[:, valid_members]
        eligible = [name for name in valid_members if asset_history[name].count() >= 126]
        row["eligible_fraction_252"] = len(eligible) / len(valid_members) if valid_members else np.nan
        adtv = traded_value.iloc[max(0, t - 19) : t + 1].loc[:, eligible].mean()
        row["median_log_adtv_20"] = (
            float(np.log1p(adtv.replace([np.inf, -np.inf], np.nan).dropna()).median())
            if eligible else np.nan
        )
        if halted_fraction is not None:
            # Chỉ thêm cột này khi nguồn trạng thái lịch sử được xác nhận cho toàn giai đoạn.
            row["halted_fraction"] = float(halted_fraction.reindex(market_returns.index).iloc[t])
        rows.append(row)
    return pd.DataFrame(rows, index=market_returns.index)


def forward_volatility(market_returns: pd.Series, horizon: int = 21) -> pd.Series:
    """Tại ngày t, nhãn chỉ nhìn lợi nhuận từ t+1 đến t+horizon."""
    values = market_returns.to_numpy(dtype=float)
    forward = np.full(values.size, np.nan)
    for t in range(values.size - horizon):
        future = values[t + 1 : t + horizon + 1]
        if np.isfinite(future).all():
            forward[t] = np.std(future, ddof=1) * np.sqrt(252)
    return pd.Series(forward, index=market_returns.index, name="forward_volatility")


@dataclass
class RegimeModel:
    """Bộ biến đổi đã khớp trước kỳ kiểm tra; lưu ngưỡng và siêu tham số để tái lập."""

    scaler: StandardScaler
    classifier: LogisticRegression
    threshold: float
    chosen_c: float
    feature_names: tuple[str, ...]

    def predict_probability(self, features: pd.DataFrame) -> np.ndarray:
        missing = set(self.feature_names) - set(features.columns)
        if missing:
            raise ValueError(f"Thiếu đặc trưng lúc suy luận: {sorted(missing)}")
        return self.classifier.predict_proba(self.scaler.transform(features.loc[:, self.feature_names]))[:, 1]


def fit_regime_model(
    features: pd.DataFrame,
    market_returns: pd.Series,
    train_end: str,
    validation_start: str,
    validation_end: str,
    c_values: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0),
    horizon: int = 21,
) -> RegimeModel:
    """Chọn C bằng log-loss xác nhận; chuẩn hóa và ngưỡng nhãn chỉ khớp trên train."""
    target = forward_volatility(market_returns.reindex(features.index), horizon)
    positions = np.arange(len(features))
    train_dates = np.flatnonzero(features.index <= pd.Timestamp(train_end))
    validation_dates = np.flatnonzero(features.index <= pd.Timestamp(validation_end))
    if not len(train_dates) or not len(validation_dates):
        raise ValueError("Ngày chia tập nằm ngoài khoảng dữ liệu.")
    train_cutoff, validation_cutoff = train_dates[-1], validation_dates[-1]
    # Nhãn phải kết thúc trước ranh giới của chính tập đó, tránh tràn nhãn sang giai đoạn sau.
    train_mask = (features.index <= pd.Timestamp(train_end)) & (positions + horizon <= train_cutoff)
    val_mask = (
        (features.index >= pd.Timestamp(validation_start))
        & (features.index <= pd.Timestamp(validation_end))
        & (positions + horizon <= validation_cutoff)
    )
    raw_train = features.loc[train_mask].replace([np.inf, -np.inf], np.nan)
    raw_val = features.loc[val_mask].replace([np.inf, -np.inf], np.nan)
    valid_train = raw_train.notna().all(axis=1) & target.loc[raw_train.index].notna()
    valid_val = raw_val.notna().all(axis=1) & target.loc[raw_val.index].notna()
    raw_train, raw_val = raw_train.loc[valid_train], raw_val.loc[valid_val]
    if len(raw_train) < 500 or raw_val.empty:
        raise ValueError("AI chưa đủ dữ liệu: cần ít nhất 500 mẫu huấn luyện và mẫu xác nhận.")
    threshold = float(target.loc[raw_train.index].quantile(0.70))
    y_train = (target.loc[raw_train.index] > threshold).astype(int).to_numpy()
    y_val = (target.loc[raw_val.index] > threshold).astype(int).to_numpy()
    if np.unique(y_train).size < 2 or np.unique(y_val).size < 2:
        raise ValueError("Một giai đoạn chỉ có một lớp nhãn; không dùng AI để kết luận tài chính.")
    scaler = StandardScaler().fit(raw_train)
    x_train, x_val = scaler.transform(raw_train), scaler.transform(raw_val)
    scored = []
    for c in sorted(c_values):
        model = LogisticRegression(C=c, solver="lbfgs", max_iter=2_000)
        model.fit(x_train, y_train)
        scored.append((log_loss(y_val, model.predict_proba(x_val)[:, 1]), c))
    chosen_c = min(scored)[1]
    # Sau khi C được chốt, fit lại trước giai đoạn khóa; tập kiểm tra không tham gia.
    combined = pd.concat([raw_train, raw_val]).sort_index()
    combined_target = target.loc[combined.index]
    mature_index = features.index[positions + horizon <= validation_cutoff]
    final_mask = combined.index.isin(mature_index) & combined_target.notna()
    final_x = combined.loc[final_mask]
    final_y = (combined_target.loc[final_x.index] > threshold).astype(int).to_numpy()
    final_scaler = StandardScaler().fit(final_x)
    final_model = LogisticRegression(C=chosen_c, solver="lbfgs", max_iter=2_000)
    final_model.fit(final_scaler.transform(final_x), final_y)
    return RegimeModel(final_scaler, final_model, threshold, chosen_c, tuple(features.columns))


def regime_controls(probability: float) -> tuple[float, float]:
    """Ánh xạ xác suất biến động cao sang λ∈[2,10], α∈[0.10,0.70]."""
    p = float(np.clip(probability, 0.0, 1.0))
    return 2.0 + 8.0 * p, 0.10 + 0.60 * p


def diagonal_shrinkage(sample_covariance: np.ndarray, alpha: float) -> np.ndarray:
    """Co hiệp phương sai mẫu về đường chéo, giữ nguyên phương sai riêng từng mã."""
    covariance = np.asarray(sample_covariance, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("Hiệp phương sai phải là ma trận vuông.")
    alpha = float(np.clip(alpha, 0.10, 0.70))
    return (1 - alpha) * covariance + alpha * np.diag(np.diag(covariance))
