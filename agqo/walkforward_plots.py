"""Biểu đồ cho kết quả walk-forward AI–QAOA."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PALETTE = {
    "navy": "#234E70",
    "blue": "#3979A8",
    "orange": "#E18D45",
    "gold": "#D8AA35",
    "green": "#3B8C72",
    "red": "#B95754",
    "purple": "#7967A7",
    "gray": "#7D8994",
    "ink": "#263542",
    "grid": "#DDE3E8",
}

SHORT = {
    "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện": "Cố định, toàn rổ",
    "AI chỉ điều chỉnh λ / nghiệm chính xác / toàn bộ mã đủ điều kiện": "AI chỉ λ, toàn rổ",
    "AI chỉ điều chỉnh α / nghiệm chính xác / toàn bộ mã đủ điều kiện": "AI chỉ α, toàn rổ",
    "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện": "AI λ+α, toàn rổ",
    "Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện": "Ledoit–Wolf, toàn rổ",
    "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao": "AI λ+α, chính xác 12",
    "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao": "QAOA X, p=1",
    "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao": "QAOA X, p=2",
    "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao": "QAOA XY, p=1",
    "AGQO LLM→QAOA / chính sách thích nghi / 12 mã thanh khoản cao": "AGQO LLM→QAOA",
    "VN30": "VN30",
    "VN-Index": "VN-Index",
}


def _save(fig: plt.Figure, output: Path, name: str) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / name
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def build_walkforward_plots(
    result_json: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    result = json.loads(Path(result_json).read_text(encoding="utf-8"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    created = []
    ai = result["ai"]
    portfolio = result["portfolio"]
    performance = portfolio["performance"]
    qaoa = result["qaoa"]

    # 1. Dự báo xác suất và nhãn biến động đã trưởng thành.
    forecasts = pd.DataFrame(ai["daily_forecasts"])
    forecasts["date"] = pd.to_datetime(forecasts["date"])
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.plot(
        forecasts.date,
        forecasts.probability_high_volatility,
        color=PALETTE["blue"],
        linewidth=1.35,
        label="Xác suất AI",
    )
    ax.axhline(
        forecasts.training_prevalence.mean(),
        color=PALETTE["gray"],
        linestyle="--",
        linewidth=1.2,
        label=f"Tỷ lệ nền huấn luyện TB {forecasts.training_prevalence.mean():.0%}",
    )
    actual = forecasts.loc[forecasts.actual_high_volatility == 1]
    ax.scatter(
        actual.date,
        np.full(len(actual), 0.97),
        marker="|",
        s=115,
        linewidths=1.4,
        color=PALETTE["red"],
        label="Nhãn biến động cao đã quan sát",
        zorder=4,
    )
    ax.set_ylim(0, 1.03)
    ax.set_ylabel("Xác suất")
    ax.set_title("AI dự báo chế độ biến động: so với nhãn tương lai", loc="left", weight="bold")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.grid(axis="y", color=PALETTE["grid"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.15))
    fig.subplots_adjust(bottom=0.23)
    fig.text(
        0.11, 0.012,
        "Nhãn dùng biến động VN30 trong 21 phiên sau ngày dự báo; các nhãn ngày chồng lấn.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "01_ai_regime_walkforward.png"))

    # 2. Đường vốn sau phí.
    chosen = [
        "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
        "VN30",
        "VN-Index",
    ]
    agqo_name = "AGQO LLM→QAOA / chính sách thích nghi / 12 mã thanh khoản cao"
    if agqo_name in performance:
        chosen.insert(-2, agqo_name)
    dates = pd.to_datetime(portfolio["entry_dates"])
    line_colors = [
        PALETTE["gray"], PALETTE["green"], PALETTE["purple"], PALETTE["orange"],
        PALETTE["blue"], PALETTE["navy"], PALETTE["gold"], PALETTE["red"], "#222222", "#888888",
    ]
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for name, color in zip(chosen, line_colors):
        values = performance[name]["monthly_returns"]
        nav = 100 * np.r_[1.0, np.cumprod(1 + np.asarray(values))]
        line_width = 2.2 if name in (chosen[1], chosen[4], agqo_name, "VN30") else 1.45
        ax.plot(dates, nav[1:], color=color, linewidth=line_width, label=SHORT[name])
    ax.axhline(100, color=PALETTE["grid"], linewidth=0.8)
    ax.set_ylabel("Giá trị danh mục, đầu kỳ = 100")
    ax.set_title("Đường vốn ngoài mẫu sau phí giao dịch", loc="left", weight="bold")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.grid(axis="y", color=PALETTE["grid"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        frameon=False, ncol=3, loc="upper center",
        bbox_to_anchor=(0.5, -0.14), columnspacing=1.2,
    )
    fig.subplots_adjust(bottom=0.25)
    fig.text(
        0.11, 0.012,
        "16 kỳ từ 02/06/2025 đến 01/10/2026; mô phỏng giá mở cửa, giá thô và vốn ban đầu 100 triệu đồng.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "02_net_equity_curves.png"))

    # 3. Chất lượng QAOA so với nghiệm chính xác.
    monthly = qaoa["monthly_runs"]
    has_agqo = "AGQO" in qaoa["quality_summary"]
    labels = ["X, p=1", "X, p=2", "XY, p=1"] + (["AGQO"] if has_agqo else [])
    keys = ["X_p1", "X_p2", "XY_p1"] + (["AGQO"] if has_agqo else [])
    values = [
        [
            row["normalized_objective_regret"] * 100
            for row in monthly
            if row["variant"] == key and row["normalized_objective_regret"] is not None
        ]
        for key in keys
    ]
    fig, (ax_x, ax_xy) = plt.subplots(1, 2, figsize=(11, 5.3), gridspec_kw={"width_ratios": [1, 0.8]})
    for ax, group_values, group_labels, colors in (
        (ax_x, values[:2], labels[:2], [PALETTE["blue"], PALETTE["navy"]]),
        (ax_xy, values[2:], labels[2:], [PALETTE["orange"], PALETTE["red"]]),
    ):
        box = ax.boxplot(group_values, tick_labels=group_labels, patch_artist=True, showmeans=True)
        for patch, color in zip(box["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.72)
        for i, points in enumerate(group_values, start=1):
            ax.scatter(np.full(len(points), i), points, color=PALETTE["ink"], s=15, alpha=0.55, zorder=3)
        ax.axhline(5, color=PALETTE["red"], linestyle="--", linewidth=1.4, label="Ngưỡng 5%")
        ax.grid(axis="y", color=PALETTE["grid"])
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylabel("Sai lệch chuẩn hóa (%)")
        ax.legend(frameon=False, loc="upper left")
    x_regrets = [value for series in values[:2] for value in series if np.isfinite(value)]
    xy_regrets = [value for series in values[2:] for value in series if np.isfinite(value)]
    ax_x.set_ylim(-1, max(7, (np.ceil(max(x_regrets)) + 1) if x_regrets else 7))
    ax_xy.set_ylim(-1, max(60, (np.ceil(max(xy_regrets) * 1.1)) if xy_regrets else 60))
    fig.suptitle("QAOA có giữ được chất lượng nghiệm trên 16 kỳ?", x=0.08, ha="left", weight="bold")
    fig.text(
        0.12, 0.012,
        "Sai lệch được chia cho biên độ hàm mục tiêu của 924 tổ hợp khả thi N=12, K=6.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "03_qaoa_optimality_gap.png"))

    # 4. Hiệu quả đầu tư và rủi ro.
    fig, ax = plt.subplots(figsize=(10, 6.2))
    for name in chosen:
        metric = performance[name]["metrics"]
        color = line_colors[chosen.index(name)]
        marker = "D" if "QAOA" in name else ("s" if name in ("VN30", "VN-Index") else "o")
        ax.scatter(
            metric["annualized_volatility"] * 100,
            metric["cagr"] * 100,
            s=72,
            color=color,
            marker=marker,
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        ax.annotate(
            SHORT[name],
            (metric["annualized_volatility"] * 100, metric["cagr"] * 100),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    ax.axhline(0, color=PALETTE["gray"], linewidth=0.8)
    ax.set_xlabel("Biến động năm hóa (%)")
    ax.set_ylabel("CAGR ròng (%)")
    ax.set_title("Lợi nhuận có đi cùng rủi ro hợp lý?", loc="left", weight="bold")
    ax.grid(color=PALETTE["grid"])
    ax.spines[["top", "right"]].set_visible(False)
    offsets = {
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao": (-98, -19),
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao": (-88, 13),
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao": (9, 12),
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao": (10, 4),
        agqo_name: (10, -15),
    }
    for annotation in ax.texts:
        annotation.remove()
    for name in chosen:
        metric = performance[name]["metrics"]
        ax.annotate(
            SHORT[name],
            (metric["annualized_volatility"] * 100, metric["cagr"] * 100),
            xytext=offsets.get(name, (5, 5)),
            textcoords="offset points",
            ha="right" if offsets.get(name, (5, 5))[0] < 0 else "left",
            fontsize=8,
        )
    fig.text(
        0.12, 0.012,
        "CAGR và Sharpe dựa trên 16 tháng; kết quả cổ phiếu dùng ảnh chụp thành phần hiện tại và giá thô.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "04_risk_return_tradeoff.png"))

    # 5. Phí giao dịch và độ chặt của giới hạn thanh khoản.
    fig, (ax_fee, ax_capacity) = plt.subplots(1, 2, figsize=(14, 5.7), gridspec_kw={"width_ratios": [1.2, 1]})
    fee_names = [
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
    ]
    line_colors = [PALETTE["green"], PALETTE["blue"], PALETTE["navy"], PALETTE["gold"]]
    if agqo_name in portfolio["cost_capacity_sensitivity"]:
        fee_names.append(agqo_name)
        line_colors.append(PALETTE["red"])
    for name, color in zip(fee_names, line_colors):
        rows = portfolio["cost_capacity_sensitivity"][name]
        selected_rows = sorted(
            [row for row in rows if row["adtv_participation"] == 0.05],
            key=lambda row: row["fee_bps"],
        )
        ax_fee.plot(
            [row["fee_bps"] for row in selected_rows],
            [row["cagr"] * 100 for row in selected_rows],
            marker="o",
            color=color,
            label=SHORT[name],
        )
    ax_fee.set_xlabel("Phí mỗi chiều giao dịch (điểm cơ bản)")
    ax_fee.set_ylabel("CAGR ròng (%)")
    ax_fee.set_title("Nhạy cảm với phí", loc="left", weight="bold")
    ax_fee.grid(color=PALETTE["grid"])
    ax_fee.legend(frameon=False, fontsize=8, loc="upper right")
    requested = []
    for name in fee_names:
        summary = performance[name]["execution_summary"]
        requested.append((SHORT[name], summary["max_requested_adtv_participation"] * 100))
    requested.append((
        "Cố định, toàn rổ",
        performance["Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện"]["execution_summary"]["max_requested_adtv_participation"] * 100,
    ))
    if agqo_name in performance:
        requested.append((
            SHORT[agqo_name],
            performance[agqo_name]["execution_summary"]["max_requested_adtv_participation"] * 100,
        ))
    names, participation = zip(*requested)
    capacity_colors = [PALETTE["gray"], PALETTE["blue"], PALETTE["navy"], PALETTE["gold"], PALETTE["green"]]
    if len(names) > len(capacity_colors):
        capacity_colors.append(PALETTE["red"])
    ax_capacity.barh(names, participation, color=capacity_colors[: len(names)])
    ax_capacity.axvline(1.0, color=PALETTE["red"], linestyle="--", label="Giới hạn thấp nhất: 1% ADTV")
    ax_capacity.set_xlabel("Tỷ lệ lớn nhất lệnh/ADTV (%)")
    ax_capacity.set_title("Sức chứa ở vốn 100 triệu đồng", loc="left", weight="bold")
    for bar, value in zip(ax_capacity.patches, participation):
        ax_capacity.text(value + 0.01, bar.get_y() + bar.get_height() / 2, f"{value:.3f}%", va="center", fontsize=8)
    ax_capacity.grid(axis="x", color=PALETTE["grid"])
    ax_capacity.legend(frameon=False, fontsize=8)
    ax_capacity.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.08, right=0.98, wspace=0.72, bottom=0.19)
    fig.text(
        0.08, 0.012,
        "Tỷ lệ lệnh cao nhất thấp hơn 1%; vì vậy các mức giới hạn 1%, 5% và 10% không ràng buộc trong mẫu này.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "05_cost_and_capacity.png"))

    # 6. Mức tiếp xúc ngân hàng và tần suất được chọn.
    exposure_names = [
        "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
    ]
    if agqo_name in portfolio["selection_summary"]:
        exposure_names.append(agqo_name)
    fig, (ax_bank, ax_names) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [0.8, 1.2]})
    bank_weights = [portfolio["selection_summary"][name]["bank_weight_mean"] * 100 for name in exposure_names]
    exposure_colors = [PALETTE["gray"], PALETTE["green"], PALETTE["orange"], PALETTE["blue"], PALETTE["navy"], PALETTE["gold"], PALETTE["red"]]
    ax_bank.barh([SHORT[name] for name in exposure_names], bank_weights, color=exposure_colors[: len(exposure_names)])
    ax_bank.set_xlabel("Tỷ trọng mục tiêu thuộc nhóm ngân hàng (%)")
    ax_bank.set_title("Độ nghiêng nhóm ngành", loc="left", weight="bold")
    ax_bank.grid(axis="x", color=PALETTE["grid"])
    ax_bank.spines[["top", "right"]].set_visible(False)
    full = portfolio["selection_summary"][exposure_names[1]]["ticker_selection_frequency"]
    guided_name = agqo_name if agqo_name in portfolio["selection_summary"] else exposure_names[3]
    qaoa_x = portfolio["selection_summary"][guided_name]["ticker_selection_frequency"]
    full_map = {row["ticker"]: row["fraction_of_rebalances"] * 100 for row in full}
    qaoa_map = {row["ticker"]: row["fraction_of_rebalances"] * 100 for row in qaoa_x}
    all_tickers = sorted(set(full_map) | set(qaoa_map))
    top = sorted(all_tickers, key=lambda ticker: max(full_map.get(ticker, 0), qaoa_map.get(ticker, 0)), reverse=True)[:10]
    y = np.arange(len(top))
    ax_names.barh(y - 0.18, [full_map.get(t, 0) for t in top], height=0.35, color=PALETTE["green"], label="AI λ+α, toàn rổ")
    ax_names.barh(
        y + 0.18, [qaoa_map.get(t, 0) for t in top], height=0.35,
        color=PALETTE["red"] if guided_name == agqo_name else PALETTE["blue"],
        label=SHORT[guided_name],
    )
    ax_names.set_yticks(y, top)
    ax_names.invert_yaxis()
    ax_names.set_xlabel("Tỷ lệ số tháng được chọn (%)")
    ax_names.set_title("Mã được chọn thường xuyên nhất", loc="left", weight="bold")
    ax_names.grid(axis="x", color=PALETTE["grid"])
    ax_names.legend(frameon=False)
    ax_names.spines[["top", "right"]].set_visible(False)
    created.append(_save(fig, output, "06_exposure_and_holdings.png"))

    # 7. Nghiệm chuẩn chính xác so với thời gian mô phỏng véc-tơ trạng thái.
    variants = ["X_p1", "X_p2", "XY_p1"]
    qseconds = [qaoa["quality_summary"][key]["total_cpu_simulation_seconds"] for key in variants]
    exact_seconds = qaoa["solver_runtime_seconds"].get(
        "exact_ai12_universe_total", qaoa["solver_runtime_seconds"]["exact_12_universe_total"]
    )
    fig, ax = plt.subplots(figsize=(14 if has_agqo else 9, 5.2))
    labels = ["Chính xác cổ điển N=12", "QAOA X, p=1\n48 lượt", "QAOA X, p=2\n48 lượt", "QAOA XY, p=1\n48 lượt"]
    vals = [exact_seconds, *qseconds]
    bar_colors = [PALETTE["gray"], PALETTE["blue"], PALETTE["navy"], PALETTE["gold"]]
    if has_agqo:
        labels.insert(1, "Chính xác\nchính sách AGQO")
        vals.insert(1, qaoa["solver_runtime_seconds"]["exact_agqo_12_universe_total"])
        bar_colors.insert(1, PALETTE["green"])
        labels.append("AGQO LLM→QAOA\nchính sách đã chọn")
        vals.append(qaoa["quality_summary"]["AGQO"]["total_cpu_simulation_seconds"])
        bar_colors.append(PALETTE["red"])
        labels.extend(["Chính xác\nlưới 12 chính sách", "QAOA lưới\n12 chính sách"])
        vals.extend([
            qaoa["solver_runtime_seconds"]["policy_catalog_exact_total"],
            qaoa["solver_runtime_seconds"]["policy_catalog_qaoa_total"],
        ])
        bar_colors.extend([PALETTE["purple"], PALETTE["orange"]])
    bars = ax.bar(labels, vals, color=bar_colors)
    ax.set_yscale("log")
    ax.set_ylabel("Thời gian CPU mô phỏng (giây, thang lôgarit)")
    ax.set_title("Thời gian nghiệm chính xác, QAOA đã chọn và lưới đối chứng", loc="left", weight="bold")
    ax.grid(axis="y", which="both", color=PALETTE["grid"])
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.15, f"{value:.4f}", ha="center", va="bottom", fontsize=8)
    fig.text(
        0.12, 0.012,
        "QAOA dùng véc-tơ trạng thái cổ điển, 3 hạt giống mỗi tháng; không có phép đo trên QPU.",
        fontsize=8, color=PALETTE["gray"],
    )
    created.append(_save(fig, output, "07_solver_runtime.png"))

    # 8. Danh mục thích nghi so với từng chính sách QAOA cố định.
    guidance = result.get("agqo_guidance", {})
    policy_strategy_names = guidance.get("policy_strategy_names", {})
    if guidance.get("enabled") and policy_strategy_names:
        rows = [("AGQO thích nghi", agqo_name, "AGQO")]
        rows.extend(
            (policy_id, strategy_name, f"POLICY:{policy_id}")
            for policy_id, strategy_name in sorted(policy_strategy_names.items())
        )
        labels = [row[0] for row in rows]
        cagr = [performance[row[1]]["metrics"]["cagr"] * 100 for row in rows]
        sharpe = [performance[row[1]]["metrics"]["sharpe"] for row in rows]
        drawdown = [performance[row[1]]["metrics"]["max_drawdown"] * 100 for row in rows]
        regret = [
            qaoa["quality_summary"][row[2]]["mean_normalized_regret"] * 100
            if qaoa["quality_summary"][row[2]]["mean_normalized_regret"] is not None
            else np.nan
            for row in rows
        ]
        y = np.arange(len(rows))
        colors = [PALETTE["red"]] + [PALETTE["blue"]] * (len(rows) - 1)
        fig, axes = plt.subplots(1, 4, figsize=(18, 8), sharey=True)
        panels = (
            (axes[0], cagr, "CAGR ròng (%)", "Lợi nhuận"),
            (axes[1], sharpe, "Sharpe", "Lợi nhuận trên rủi ro"),
            (axes[2], drawdown, "Sụt giảm tối đa (%)", "Mức giảm vốn"),
            (axes[3], regret, "Sai lệch mục tiêu TB (%)", "Chất lượng QAOA"),
        )
        for ax, values, xlabel, title in panels:
            shown = [0.0 if not np.isfinite(value) else value for value in values]
            ax.barh(y, shown, color=colors, alpha=0.88)
            ax.set_title(title, loc="left", weight="bold")
            ax.set_xlabel(xlabel)
            ax.grid(axis="x", color=PALETTE["grid"])
            ax.spines[["top", "right"]].set_visible(False)
            ax.axvline(0, color=PALETTE["gray"], linewidth=0.8)
        axes[0].set_yticks(y, labels)
        axes[0].invert_yaxis()
        axes[3].set_xlim(left=0)
        fig.suptitle(
            "AGQO thích nghi và danh mục chính sách cố định",
            x=0.08, ha="left", weight="bold",
        )
        fig.text(
            0.08, 0.012,
            "Các hàng cố định là đối chứng hậu nghiệm; LLM chỉ dùng kết quả kỳ đã đóng. "
            "Cửa sổ 16 kỳ chưa đủ để kết luận ổn định.",
            fontsize=8, color=PALETTE["gray"],
        )
        fig.subplots_adjust(left=0.18, right=0.99, wspace=0.32, bottom=0.12, top=0.88)
        created.append(_save(fig, output, "08_agqo_policy_comparison.png"))
    return created
