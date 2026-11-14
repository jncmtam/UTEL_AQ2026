"""Vẽ bộ biểu đồ khám phá dữ liệu VN30 bằng Matplotlib."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .market_data import load_market_dataset

NAVY = "#234E70"
BLUE = "#3979A8"
ORANGE = "#E18D45"
GOLD = "#E0B541"
GREEN = "#3B8C72"
RED = "#B95754"
GRAY = "#87929C"
INK = "#263542"
GRID = "#DDE3E8"
PALE = "#F3F6F8"


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _prepare(data_path: str | Path, members_path: str | Path, summary: dict[str, object]):
    data, members = load_market_dataset(data_path, members_path)
    stocks = data.loc[data["instrument_type"] == "stock"].copy()
    indices = data.loc[data["instrument_type"] == "index"].copy()
    excluded = set(summary.get("excluded_short_history", {}))
    tickers = tuple(t for t in members["ticker"].astype(str) if t not in excluded)
    index_prices = indices.pivot(index="date", columns="ticker", values="close").sort_index()
    all_dates = index_prices[["VN30", "VNINDEX"]].dropna().index
    prices = (
        stocks.pivot(index="date", columns="ticker", values="close")
        .reindex(index=all_dates, columns=tickers)
        .sort_index()
    )
    returns = prices.pct_change(fill_method=None)
    complete = returns.dropna(how="any")
    lookback = int(summary["lookback_sessions"])
    window = complete.tail(lookback)
    window_dates = window.index
    turnover = (stocks["close"] * stocks["volume"]).rename("turnover_proxy")
    traded_panel = (
        stocks.assign(turnover_proxy=turnover)
        .pivot(index="date", columns="ticker", values="turnover_proxy")
        .reindex(index=window_dates, columns=tickers)
    )
    groups = members.set_index("ticker")["group"].to_dict()
    selected = set(summary["optimizer"]["selected_tickers"])
    return data, members, stocks, index_prices, prices, returns, window, traded_panel, groups, selected


def _plot_coverage(members: pd.DataFrame, stocks: pd.DataFrame, output: Path) -> Path:
    dates = pd.DatetimeIndex(sorted(stocks["date"].unique()))
    months = pd.period_range(dates.min().to_period("M"), dates.max().to_period("M"), freq="M")
    monthly_denominator = pd.Series(1, index=dates).groupby(dates.to_period("M")).sum().reindex(months, fill_value=0)
    monthly_counts = (
        stocks.assign(month=stocks["date"].dt.to_period("M"))
        .groupby(["ticker", "month"])["date"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(index=members["ticker"], columns=months, fill_value=0)
    )
    coverage = monthly_counts.div(monthly_denominator, axis="columns").clip(0, 1)
    first_dates = stocks.groupby("ticker")["date"].min()
    group_order = {"Ngân hàng": 0, "Ngành khác": 1}
    ordered = sorted(
        members["ticker"],
        key=lambda ticker: (group_order.get(members.set_index("ticker").loc[ticker, "group"], 2), first_dates[ticker]),
    )
    values = coverage.reindex(ordered).to_numpy()

    fig, ax = plt.subplots(figsize=(12, 8))
    image = ax.imshow(values, aspect="auto", interpolation="nearest", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(ordered)), ordered, fontsize=8)
    tick_positions = np.arange(0, len(months), 6)
    ax.set_xticks(tick_positions, [str(months[index]) for index in tick_positions], rotation=0)
    ax.set_xlabel("Tháng (độ phủ theo số phiên có dữ liệu)")
    ax.set_title("Lịch sử dữ liệu không đồng đều giữa 30 mã", loc="left", color=INK, weight="bold", pad=12)
    ax.set_ylabel("Mã cổ phiếu, gom theo nhóm ngành")
    bank_count = int((members.set_index("ticker").loc[ordered, "group"] == "Ngân hàng").sum())
    if 0 < bank_count < len(ordered):
        ax.axhline(bank_count - 0.5, color=ORANGE, linewidth=1.6)
        ax.text(len(months) + 0.4, bank_count / 2 - 0.5, "Ngân hàng", va="center", color=NAVY, fontsize=9)
        ax.text(len(months) + 0.4, bank_count + (len(ordered) - bank_count) / 2 - 0.5, "Ngành khác", va="center", color=NAVY, fontsize=9)
    colorbar = fig.colorbar(image, ax=ax, pad=0.12, fraction=0.03)
    colorbar.set_label("Tỷ lệ phiên có quan sát")
    colorbar.set_ticks([0, 0.5, 1], labels=["0%", "50%", "100%"])
    ax.grid(False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.text(0.11, 0.015, "Màu trắng thường biểu thị mã chưa giao dịch trong giai đoạn đó; không thể giả định đây là ngày nghỉ hay dữ liệu bị thiếu.", fontsize=8, color=GRAY)
    path = output / "01_coverage.png"
    _finish(fig, path)
    return path


def _plot_indices(index_prices: pd.DataFrame, output: Path) -> Path:
    prices = index_prices[["VN30", "VNINDEX"]].dropna()
    normalized = prices.div(prices.iloc[0]).mul(100)
    drawdown = prices.div(prices.cummax()).sub(1)
    fig, (ax_price, ax_dd) = plt.subplots(
        2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]}
    )
    for ticker, color in (("VN30", BLUE), ("VNINDEX", ORANGE)):
        ax_price.plot(normalized.index, normalized[ticker], color=color, linewidth=1.8, label=ticker)
        ax_dd.plot(drawdown.index, drawdown[ticker] * 100, color=color, linewidth=1.35, label=ticker)
        ax_price.annotate(
            f"{normalized[ticker].iloc[-1]:.1f}",
            (normalized.index[-1], normalized[ticker].iloc[-1]),
            xytext=(6, 0), textcoords="offset points", color=color, fontsize=9, va="center",
        )
    ax_price.set_title("Thị trường Việt Nam qua hai chuỗi chỉ số", loc="left", color=INK, weight="bold", pad=12)
    ax_price.set_ylabel("Giá chuẩn hóa (đầu kỳ = 100)")
    ax_price.legend(frameon=False, loc="upper left", ncol=2)
    ax_price.grid(axis="y", color=GRID, linewidth=0.7)
    ax_dd.axhline(0, color=GRAY, linewidth=0.7)
    ax_dd.fill_between(drawdown.index, drawdown["VN30"] * 100, 0, color=BLUE, alpha=0.13)
    ax_dd.plot(drawdown.index, drawdown["VN30"] * 100, color=BLUE, linewidth=1)
    ax_dd.plot(drawdown.index, drawdown["VNINDEX"] * 100, color=ORANGE, linewidth=1)
    ax_dd.set_ylabel("Sụt giảm từ đỉnh (%)")
    ax_dd.grid(axis="y", color=GRID, linewidth=0.7)
    ax_dd.xaxis.set_major_locator(mdates.YearLocator())
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.11, 0.012, f"Giá chỉ số chuẩn hóa từ {prices.index.min():%d/%m/%Y}; phần dưới đo khoảng cách so với đỉnh trước đó.", fontsize=8, color=GRAY)
    for ax in (ax_price, ax_dd):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "02_indices.png"
    _finish(fig, path)
    return path


def _plot_risk_return(
    window: pd.DataFrame,
    traded_panel: pd.DataFrame,
    groups: dict[str, str],
    selected: set[str],
    output: Path,
) -> Path:
    cumulative = (1 + window).prod(axis=0) - 1
    volatility = window.std(ddof=1) * np.sqrt(252)
    liquidity = traded_panel.mean()
    log_liquidity = np.log10(liquidity.clip(lower=1))
    spread = max(float(log_liquidity.max() - log_liquidity.min()), 1e-9)
    sizes = 45 + 160 * (log_liquidity - log_liquidity.min()) / spread
    fig, ax = plt.subplots(figsize=(11, 7))
    for group, color in (("Ngân hàng", BLUE), ("Ngành khác", ORANGE)):
        tickers = [ticker for ticker in window.columns if groups[ticker] == group and ticker not in selected]
        ax.scatter(volatility[tickers] * 100, cumulative[tickers] * 100, s=sizes[tickers], c=color, alpha=0.76, edgecolors="white", linewidths=0.8, label=group)
    chosen = [ticker for ticker in window.columns if ticker in selected]
    ax.scatter(volatility[chosen] * 100, cumulative[chosen] * 100, s=sizes[chosen] + 80, marker="*", c=GOLD, edgecolors=INK, linewidths=0.8, label="Được bộ giải chọn", zorder=4)
    label_set = set(chosen)
    label_set.update(cumulative.nlargest(3).index)
    label_set.update(cumulative.nsmallest(3).index)
    for index, ticker in enumerate(sorted(label_set)):
        ax.annotate(ticker, (volatility[ticker] * 100, cumulative[ticker] * 100), xytext=(5, 5 if index % 2 == 0 else -11), textcoords="offset points", fontsize=8, color=INK)
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.axvline(0, color=GRAY, linewidth=0.8)
    ax.set_title("Lợi suất đi cùng rủi ro nào?", loc="left", color=INK, weight="bold", pad=12)
    ax.set_xlabel("Biến động năm hóa (%)")
    ax.set_ylabel("Lợi suất gộp giá thô trong cửa sổ (%)")
    ax.legend(frameon=False, ncol=3, loc="best")
    ax.grid(color=GRID, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.12, 0.015, "Diện tích bong bóng tỷ lệ với giá trị giao dịch xấp xỉ (giá đóng cửa × khối lượng); các lợi suất chưa điều chỉnh sự kiện doanh nghiệp.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "03_risk_return.png"
    _finish(fig, path)
    return path


def _plot_returns(window: pd.DataFrame, groups: dict[str, str], selected: set[str], output: Path) -> Path:
    cumulative = ((1 + window).prod(axis=0) - 1).sort_values()
    tickers = cumulative.index
    colors = [GOLD if ticker in selected else (BLUE if groups[ticker] == "Ngân hàng" else ORANGE) for ticker in tickers]
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.barh(tickers, cumulative.to_numpy() * 100, color=colors, height=0.72)
    ax.axvline(0, color=INK, linewidth=0.9)
    for y, (ticker, value) in enumerate(cumulative.items()):
        offset = 4 if value >= 0 else -4
        ax.annotate(f"{value:.0%}", (value * 100, y), xytext=(offset, 0), textcoords="offset points", va="center", ha="left" if value >= 0 else "right", fontsize=8, color=INK)
    ax.set_title("30 mã, một cửa sổ: lợi suất phân tán rộng", loc="left", color=INK, weight="bold", pad=12)
    ax.set_xlabel("Lợi suất gộp theo giá đóng cửa thô (%)")
    ax.set_ylabel("Mã, xếp từ thấp đến cao")
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.text(0.12, 0.015, "Vàng: sáu mã trong nghiệm danh mục. Màu xanh: ngân hàng. Màu cam: ngành khác.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "04_returns_rank.png"
    _finish(fig, path)
    return path


def _plot_correlations(window: pd.DataFrame, members: pd.DataFrame, output: Path) -> Path:
    in_window = set(window.columns)
    banks = [t for t in members.loc[members["group"] == "Ngân hàng", "ticker"] if t in in_window]
    others = [t for t in members.loc[members["group"] != "Ngân hàng", "ticker"] if t in in_window]
    ordered = banks + others
    correlation = window[ordered].corr()
    fig, ax = plt.subplots(figsize=(12, 10))
    image = ax.imshow(correlation, cmap="RdYlBu_r", vmin=-1, vmax=1, interpolation="nearest")
    ticks = np.arange(len(ordered))
    ax.set_xticks(ticks, ordered, rotation=90, fontsize=8)
    ax.set_yticks(ticks, ordered, fontsize=8)
    bank_count = len(banks)
    ax.axvline(bank_count - 0.5, color=INK, linewidth=1.2)
    ax.axhline(bank_count - 0.5, color=INK, linewidth=1.2)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.035)
    colorbar.set_label("Tương quan lợi suất ngày")
    ax.set_title("Mã nào cùng biến động?", loc="left", color=INK, weight="bold", pad=12)
    ax.set_xlabel(f"Ngân hàng ({bank_count} mã)  |  Ngành khác ({len(others)} mã)")
    ax.set_ylabel("Ngân hàng được gom ở đầu ma trận")
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    fig.text(0.1, 0.015, f"Tương quan Pearson từ lợi suất ngày trong cửa sổ {len(window)} phiên, chỉ sử dụng các phiên đầy đủ của cả rổ.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "05_correlations.png"
    _finish(fig, path)
    return path


def _plot_liquidity(traded_panel: pd.DataFrame, selected: set[str], output: Path) -> Path:
    liquidity = (traded_panel.mean() / 1e9).sort_values()
    colors = [GOLD if ticker in selected else NAVY for ticker in liquidity.index]
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.barh(liquidity.index, liquidity.to_numpy(), color=colors, height=0.72)
    ax.set_xscale("log")
    ax.set_title("Quy mô giao dịch không đồng đều giữa các mã", loc="left", color=INK, weight="bold", pad=12)
    ax.set_xlabel("Giá × khối lượng bình quân (tỷ đồng/ngày, trục lôgarit)")
    ax.set_ylabel("Mã cổ phiếu")
    ax.grid(axis="x", color=GRID, linewidth=0.7, which="both")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.text(0.14, 0.015, "Chỉ báo thanh khoản xấp xỉ vì nguồn không có giá trị khớp lệnh chính thức. Vàng: sáu mã được chọn.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "06_liquidity.png"
    _finish(fig, path)
    return path


def _plot_risk_regimes(index_prices: pd.DataFrame, output: Path) -> Path:
    returns = index_prices[["VN30", "VNINDEX"]].pct_change(fill_method=None)
    rolling_vol = returns.rolling(60, min_periods=60).std(ddof=1) * np.sqrt(252) * 100
    fig, ax = plt.subplots(figsize=(12, 5.8))
    for ticker, color in (("VN30", BLUE), ("VNINDEX", ORANGE)):
        ax.plot(rolling_vol.index, rolling_vol[ticker], color=color, linewidth=1.35, label=ticker)
        latest = rolling_vol[ticker].dropna().iloc[-1]
        ax.annotate(f"{ticker}: {latest:.1f}%", (rolling_vol[ticker].dropna().index[-1], latest), xytext=(6, 0), textcoords="offset points", va="center", color=color, fontsize=9)
    ax.set_title("Rủi ro thị trường thay đổi theo từng giai đoạn", loc="left", color=INK, weight="bold", pad=12)
    ax.set_ylabel("Biến động năm hóa, cửa sổ trượt 60 phiên (%)")
    ax.set_xlabel("Ngày")
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.11, 0.015, "Độ lệch chuẩn lợi suất ngày trong 60 phiên gần nhất × √252; không phải dự báo biến động.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "07_risk_regimes.png"
    _finish(fig, path)
    return path


def _plot_optimizer(summary: dict[str, object], window: pd.DataFrame, output: Path) -> Path:
    optimizer = summary["optimizer"]
    selected = optimizer["selected_tickers"]
    terms = [
        ("Phạt rủi ro", float(optimizer["risk_penalty_annual"]), RED),
        ("Phần thưởng\nlợi suất", float(optimizer["expected_return_reward_annual"]), GREEN),
        ("Phí vào vị thế", float(optimizer["transaction_cost_annual"]), GRAY),
    ]
    fig, (ax_waterfall, ax_assets) = plt.subplots(2, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [1.15, 1]})
    running = 0.0
    positions = []
    labels = []
    for index, (label, value, color) in enumerate(terms):
        end = running + value
        ax_waterfall.bar(index, abs(value) * 100, bottom=min(running, end) * 100, color=color, width=0.62)
        ax_waterfall.plot([index - 0.31, index + 0.63], [end * 100, end * 100], color=GRAY, linewidth=0.7, alpha=0.8)
        ax_waterfall.text(index, (max(running, end) + 0.003) * 100, f"{value:+.2%}", ha="center", va="bottom", fontsize=9, color=INK)
        positions.append(index)
        labels.append(label)
        running = end
    objective = float(optimizer["objective"])
    ax_waterfall.bar(3, abs(objective) * 100, bottom=min(0, objective) * 100, color=NAVY, width=0.62)
    ax_waterfall.axhline(0, color=INK, linewidth=0.8)
    if objective >= 0:
        ax_waterfall.text(3, (objective + 0.003) * 100, f"{objective:+.2%}", ha="center", va="bottom", fontsize=9, color=INK)
    else:
        ax_waterfall.text(3, objective * 50, f"{objective:+.2%}", ha="center", va="center", fontsize=9, color="white", weight="bold")
    ax_waterfall.set_xticks([*positions, 3], [*labels, "Mục tiêu\ntổng"])
    ax_waterfall.set_ylabel("Đóng góp vào hàm mục tiêu (điểm %/năm)")
    ax_waterfall.set_title("Vì sao bộ giải chọn sáu mã này?", loc="left", color=INK, weight="bold", pad=12)
    ax_waterfall.grid(axis="y", color=GRID, linewidth=0.7)
    ax_waterfall.set_axisbelow(True)
    ax_waterfall.spines[["top", "right"]].set_visible(False)

    selected_mu = window[selected].mean(axis=0) * 252 * 100
    bar_colors = [GREEN if value >= 0 else RED for value in selected_mu]
    ax_assets.bar(selected, selected_mu.to_numpy(), color=bar_colors, width=0.62)
    ax_assets.axhline(0, color=INK, linewidth=0.8)
    for ticker, value in selected_mu.items():
        ax_assets.annotate(f"{value:.1f}%", (ticker, value), xytext=(0, 3 if value >= 0 else -12), textcoords="offset points", ha="center", fontsize=8, color=INK)
    ax_assets.set_ylabel("Lợi suất trung bình năm hóa trong mẫu (%)")
    ax_assets.set_xlabel("Mã được chọn; mỗi mã có tỷ trọng 1/6")
    ax_assets.grid(axis="y", color=GRID, linewidth=0.7)
    ax_assets.set_axisbelow(True)
    ax_assets.spines[["top", "right"]].set_visible(False)
    ax_assets.text(0.99, 0.95, f"Duyệt chính xác {optimizer['exact_combinations_searched']:,} tổ hợp\n{optimizer['exact_solve_seconds']:.2f} giây trên máy hiện tại", transform=ax_assets.transAxes, ha="right", va="top", fontsize=9, color=NAVY)
    fig.text(
        0.11,
        0.012,
        f"Nghiệm tối ưu trong mẫu với λ={optimizer['risk_aversion']:.1f}, co rút hiệp phương sai α={optimizer['diagonal_shrinkage']:.2f} và phí vào vị thế giả định {optimizer['transaction_cost_bps']:.0f} điểm cơ bản; không phải dự báo hay kiểm định ngoài mẫu.",
        fontsize=8,
        color=GRAY,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = output / "08_optimizer.png"
    _finish(fig, path)
    return path


def _plot_benchmark(benchmark_path: str | Path, output: Path) -> Path:
    """Đối chiếu chất lượng và thời gian QAOA trên bộ kiểm tra tổng hợp đã lưu."""
    records = [
        json.loads(line)
        for line in Path(benchmark_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records or any(record.get("data_source") != "synthetic_only" for record in records):
        raise ValueError("Biểu đồ QAOA chỉ nhận nhật ký benchmark tổng hợp đã ghi rõ nguồn dữ liệu.")
    dimensions = sorted({int(record["n"]) for record in records})
    mixers = ("X", "XY")
    colors = {"X": BLUE, "XY": ORANGE}
    width = 0.34
    positions = np.arange(len(dimensions))
    fig, (ax_pass, ax_gap, ax_time) = plt.subplots(1, 3, figsize=(15, 5.8))

    for offset, mixer in enumerate(mixers):
        mixer_records = [record for record in records if record["mixer"] == mixer]
        grouped = {
            n: [record for record in mixer_records if int(record["n"]) == n]
            for n in dimensions
        }
        center = positions + (offset - 0.5) * width
        pass_counts = [sum(bool(record["meets_case_threshold"]) for record in grouped[n]) for n in dimensions]
        ax_pass.bar(center, pass_counts, width, color=colors[mixer], label=f"Bộ trộn {mixer}")
        for x, count in zip(center, pass_counts):
            ax_pass.annotate(f"{count}/{len(grouped[dimensions[0]])}", (x, count), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)

        gaps = [
            float(np.median([record["median_normalized_gap"] for record in grouped[n] if record["median_normalized_gap"] is not None])) * 100
            for n in dimensions
        ]
        ax_gap.plot(positions + (offset - 0.5) * 0.06, gaps, marker="o", color=colors[mixer], linewidth=1.8, label=f"Bộ trộn {mixer}")
        for x, gap in zip(positions + (offset - 0.5) * 0.06, gaps):
            ax_gap.annotate(f"{gap:.1f}%", (x, gap), xytext=(0, 7 if offset == 0 else -13), textcoords="offset points", ha="center", fontsize=8, color=colors[mixer])

        time_positions = positions + (offset - 0.5) * 0.08
        runtimes = [
            np.median([run["elapsed_seconds"] for record in grouped[n] for run in record["runs"]]) * 1000
            for n in dimensions
        ]
        ax_time.plot(time_positions, runtimes, marker="o", color=colors[mixer], linewidth=1.8, label=f"Bộ trộn {mixer}")
        for x, runtime in zip(time_positions, runtimes):
            ax_time.annotate(f"{runtime:.1f} ms", (x, runtime), xytext=(0, 7 if offset == 0 else -13), textcoords="offset points", ha="center", fontsize=8, color=colors[mixer])

    feasible_count = sum(bool(record["all_runs_feasible"]) for record in records)
    overall_passes = {
        mixer: sum(
            bool(record["meets_case_threshold"])
            for record in records
            if record["mixer"] == mixer
        )
        for mixer in mixers
    }
    overall_totals = {
        mixer: sum(record["mixer"] == mixer for record in records)
        for mixer in mixers
    }
    ax_pass.set_title("Cấu hình đạt chuẩn", loc="left", color=INK, weight="bold")
    ax_pass.set_ylabel("Số bài đạt / tổng số bài")
    ax_pass.set_xticks(positions, [f"N = {n}" for n in dimensions])
    cases_per_mixer = max(
        sum(int(record["n"]) == n and record["mixer"] == mixers[0] for record in records)
        for n in dimensions
    )
    ax_pass.set_ylim(0, max(1, cases_per_mixer) * 1.2)
    ax_pass.grid(axis="y", color=GRID, linewidth=0.7)
    ax_pass.set_axisbelow(True)

    ax_gap.set_title("Trung vị độ lệch mục tiêu", loc="left", color=INK, weight="bold")
    ax_gap.set_ylabel("Độ lệch so với nghiệm chính xác (%)")
    ax_gap.set_xticks(positions, [f"N = {n}" for n in dimensions])
    ax_gap.axhline(5, color=RED, linestyle="--", linewidth=1, label="Ngưỡng độ lệch 5%")
    ax_gap.grid(axis="y", color=GRID, linewidth=0.7)
    ax_gap.set_axisbelow(True)

    ax_time.set_title("Thời gian mô phỏng mỗi lượt", loc="left", color=INK, weight="bold")
    ax_time.set_ylabel("Trung vị thời gian (mili giây)")
    ax_time.set_xticks(positions, [f"N = {n}" for n in dimensions])
    ax_time.set_yscale("log")
    ax_time.grid(axis="y", color=GRID, linewidth=0.7, which="both")
    ax_time.set_axisbelow(True)

    handles, labels = ax_gap.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.005))
    fig.suptitle("QAOA p = 1: chất lượng nghiệm giảm khi bài toán lớn dần", x=0.07, y=1.045, ha="left", color=INK, weight="bold", fontsize=15)
    comparison = (
        f"Tổng thể X đạt {overall_passes['X']}/{overall_totals['X']}, XY đạt {overall_passes['XY']}/{overall_totals['XY']}; "
        "cả hai dưới ngưỡng 29/36 đã đăng ký."
        if overall_totals["X"] == 36 and overall_totals["XY"] == 36
        else f"Tổng thể X đạt {overall_passes['X']}/{overall_totals['X']}, XY đạt {overall_passes['XY']}/{overall_totals['XY']}."
    )
    fig.text(0.07, 0.01, f"Dữ liệu tổng hợp, K=6, ba giá trị khởi tạo; cấu hình có mẫu khả thi: {feasible_count}/{len(records)}. {comparison} Thời gian là mô phỏng cổ điển, không phải thời gian QPU.", fontsize=8, color=GRAY)
    for ax in (ax_pass, ax_gap, ax_time):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0.04, 0.08, 1, 0.94))
    path = output / "09_qaoa_benchmark.png"
    _finish(fig, path)
    return path


def create_market_figures(
    data_path: str | Path,
    members_path: str | Path,
    summary: dict[str, object],
    output_dir: str | Path,
    benchmark_path: str | Path | None = None,
) -> list[Path]:
    """Tạo biểu đồ kể chuyện dữ liệu, hiệu suất, rủi ro và nghiệm danh mục."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (_, members, stocks, index_prices, _, _, window, traded_panel, groups, selected) = _prepare(
        data_path, members_path, summary
    )
    paths = [
        _plot_coverage(members, stocks, output),
        _plot_indices(index_prices, output),
        _plot_risk_return(window, traded_panel, groups, selected, output),
        _plot_returns(window, groups, selected, output),
        _plot_correlations(window, members, output),
        _plot_liquidity(traded_panel, selected, output),
        _plot_risk_regimes(index_prices, output),
        _plot_optimizer(summary, window, output),
    ]
    if benchmark_path is not None and Path(benchmark_path).exists():
        paths.append(_plot_benchmark(benchmark_path, output))
    return paths
