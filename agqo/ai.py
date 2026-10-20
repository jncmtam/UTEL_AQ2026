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
    training_prevalence: float = 0.30
    validation_log_losses: tuple[tuple[float, float], ...] = ()
    training_samples: int = 0
    validation_samples: int = 0
    validation_prevalence: float = float("nan")

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
    return RegimeModel(
        final_scaler,
        final_model,
        threshold,
        chosen_c,
        tuple(features.columns),
        float(final_y.mean()),
        tuple((float(c), float(loss_value)) for loss_value, c in scored),
        int(len(raw_train)),
        int(len(raw_val)),
        float(y_val.mean()),
    )


def fit_regime_model_as_of(
    features: pd.DataFrame,
    market_returns: pd.Series,
    as_of: pd.Timestamp | str,
    threshold: float,
    chosen_c: float,
    horizon: int = 21,
    minimum_samples: int = 500,
) -> RegimeModel:
    """Khớp lại mô hình bằng các nhãn đã trưởng thành tại ngày tín hiệu.

    Ngưỡng phân loại và C phải được chốt từ tập huấn luyện/xác nhận ban đầu;
    hàm chỉ mở rộng mẫu huấn luyện theo thời gian, không tối ưu lại trên tập kiểm tra.
    """
    if horizon < 1 or minimum_samples < 2 or chosen_c <= 0:
        raise ValueError("Cần chân trời, số mẫu tối thiểu và C hợp lệ.")
    cutoff = pd.Timestamp(as_of)
    positions = np.arange(len(features))
    cutoff_position = int(features.index.searchsorted(cutoff, side="right") - 1)
    if cutoff_position < 0:
        raise ValueError("Ngày tín hiệu nằm trước dữ liệu.")
    matured = (positions + horizon <= cutoff_position) & (features.index <= cutoff)
    raw = features.loc[matured].replace([np.inf, -np.inf], np.nan)
    target = forward_volatility(market_returns.reindex(features.index), horizon)
    valid = raw.notna().all(axis=1) & target.loc[raw.index].notna()
    raw = raw.loc[valid]
    if len(raw) < minimum_samples:
        raise ValueError(
            f"Tại {cutoff.date()} chỉ có {len(raw)} nhãn trưởng thành; cần {minimum_samples}."
        )
    labels = (target.loc[raw.index] > float(threshold)).astype(int).to_numpy()
    if np.unique(labels).size < 2:
        raise ValueError("Tại ngày tín hiệu, dữ liệu huấn luyện chỉ có một lớp.")
    scaler = StandardScaler().fit(raw)
    classifier = LogisticRegression(C=float(chosen_c), solver="lbfgs", max_iter=2_000)
    classifier.fit(scaler.transform(raw), labels)
    return RegimeModel(
        scaler=scaler,
        classifier=classifier,
        threshold=float(threshold),
        chosen_c=float(chosen_c),
        feature_names=tuple(features.columns),
        training_prevalence=float(labels.mean()),
    )


def regime_controls(probability: float) -> tuple[float, float]:
    """Ánh xạ xác suất biến động cao sang λ∈[2,10], α∈[0.10,0.70]."""
    p = float(np.clip(probability, 0.0, 1.0))
    return 2.0 + 8.0 * p, 0.10 + 0.60 * p


def risk_aversion_from_probability(
    probability: float, minimum: float = 2.0, maximum: float = 10.0
) -> float:
    """Ánh xạ xác suất trạng thái cao sang λ với miền hiệu chỉnh tường minh."""
    if not np.isfinite(minimum) or not np.isfinite(maximum) or minimum < 0 or maximum < minimum:
        raise ValueError("Cần 0 <= λ tối thiểu <= λ tối đa, cả hai đều hữu hạn.")
    p = float(np.clip(probability, 0.0, 1.0))
    return float(minimum + (maximum - minimum) * p)


def evaluate_regime_probabilities(
    labels: np.ndarray | pd.Series,
    probabilities: np.ndarray | pd.Series,
    bins: int = 10,
    baseline_probability: float = 0.30,
) -> dict[str, object]:
    """Đo chất lượng xác suất AI và hiệu chỉnh so với dự báo tỷ lệ nền."""
    y = np.asarray(labels, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.shape != y.shape or not len(y):
        raise ValueError("Nhãn và xác suất phải là hai vector một chiều cùng độ dài, không rỗng.")
    if not np.isfinite(y).all() or not np.isin(y, (0, 1)).all():
        raise ValueError("Nhãn phải chỉ chứa 0 hoặc 1 và không được thiếu.")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Xác suất phải hữu hạn và thuộc đoạn [0,1].")
    if not isinstance(bins, int) or bins < 1:
        raise ValueError("Số khoảng hiệu chỉnh phải là số nguyên dương.")
    if not np.isfinite(baseline_probability) or not 0 <= baseline_probability <= 1:
        raise ValueError("Xác suất nền phải hữu hạn và thuộc đoạn [0,1].")

    epsilon = np.finfo(float).eps
    clipped = np.clip(p, epsilon, 1 - epsilon)
    prevalence = float(y.mean())
    baseline = float(np.clip(baseline_probability, epsilon, 1 - epsilon))
    log_loss_value = float(-np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped)))
    baseline_log_loss = float(-np.mean(y * np.log(baseline) + (1 - y) * np.log1p(-baseline)))
    brier = float(np.mean((p - y) ** 2))
    baseline_brier = float(np.mean((baseline_probability - y) ** 2))

    bin_ids = np.minimum((p * bins).astype(int), bins - 1)
    calibration = []
    for bin_id in range(bins):
        selected = bin_ids == bin_id
        if selected.any():
            calibration.append(
                {
                    "bin": bin_id,
                    "count": int(selected.sum()),
                    "mean_probability": float(p[selected].mean()),
                    "observed_frequency": float(y[selected].mean()),
                }
            )
    return {
        "n": int(len(y)),
        "positive_rate": prevalence,
        "baseline_probability": float(baseline_probability),
        "log_loss": log_loss_value,
        "base_rate_log_loss": baseline_log_loss,
        "brier_score": brier,
        "base_rate_brier_score": baseline_brier,
        "brier_skill_vs_base_rate": (
            float(1 - brier / baseline_brier) if baseline_brier > 0 else float("nan")
        ),
        "calibration_bins": calibration,
    }


def evaluate_regime_model(
    model: RegimeModel,
    features: pd.DataFrame,
    market_returns: pd.Series,
    start: str,
    end: str,
    horizon: int = 21,
    bins: int = 10,
) -> dict[str, object]:
    """Chấm xác suất trên giai đoạn đã khóa, chỉ giữ nhãn tương lai đã trưởng thành."""
    if horizon < 1:
        raise ValueError("Khoảng dự báo phải là số phiên dương.")
    target = forward_volatility(market_returns.reindex(features.index), horizon)
    period = features.loc[(features.index >= pd.Timestamp(start)) & (features.index <= pd.Timestamp(end))]
    if period.empty:
        raise ValueError("Giai đoạn đánh giá không có ngày dữ liệu.")
    period_clean = period.replace([np.inf, -np.inf], np.nan)
    valid = period_clean.notna().all(axis=1) & target.reindex(period.index).notna()
    period = period.loc[valid]
    if period.empty:
        raise ValueError("Không có dự báo nào có đủ đặc trưng và nhãn đã trưởng thành.")
    probabilities = model.predict_probability(period)
    labels = (target.loc[period.index] > model.threshold).astype(int).to_numpy()
    metrics = evaluate_regime_probabilities(
        labels,
        probabilities,
        bins=bins,
        baseline_probability=model.training_prevalence,
    )
    metrics["start"] = str(period.index.min().date())
    metrics["end"] = str(period.index.max().date())
    metrics["threshold"] = float(model.threshold)
    metrics["horizon"] = int(horizon)
    return metrics


def diagonal_shrinkage(sample_covariance: np.ndarray, alpha: float) -> np.ndarray:
    """Co hiệp phương sai mẫu về đường chéo, giữ nguyên phương sai riêng từng mã."""
    covariance = np.asarray(sample_covariance, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("Hiệp phương sai phải là ma trận vuông.")
    alpha = float(np.clip(alpha, 0.10, 0.70))
    return (1 - alpha) * covariance + alpha * np.diag(np.diag(covariance))
