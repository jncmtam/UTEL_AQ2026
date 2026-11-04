"""Hình nghiên cứu AGQO được tạo từ dữ liệu và kết quả đã lưu."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from .guide import POLICIES
from .market_data import load_market_dataset
from .problem import build_qubo
from .simulator import mixer_edges_for_problem
from .walkforward import _build_policy_problem


INK = "#243443"
BLUE = "#31688e"
ORANGE = "#df8f44"
GREEN = "#3a9278"
RED = "#b84a52"
GRID = "#dbe3e8"
GRAY = "#768591"
PALE = "#f4f7f8"


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def build_pipeline_diagram(output_dir: str | Path) -> Path:
    """Show the actual component boundaries and safety fallbacks in the code."""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    fig.suptitle("AGQO · Luồng quyết định, đối chứng và kiểm toán", x=0.05, ha="left", color=INK, weight="bold", fontsize=17)

    boxes = [
        (0.25, 6.80, 2.45, 1.05, "Dữ liệu giá + chỉ số", "OHLCV · VN30 · VN-Index", "#eaf2f8"),
        (3.05, 6.80, 2.45, 1.05, "Kiểm tra + cutoff t", "Nguồn, chất lượng, thời điểm", "#eaf2f8"),
        (5.85, 6.80, 2.45, 1.05, "Đặc trưng thị trường", "Rủi ro · breadth · phân tán", "#eaf2f8"),
        (8.65, 6.80, 2.45, 1.05, "Tiểu mô hình", "Logistic · xác suất biến động", "#f7f0df"),
        (12.0, 6.80, 3.55, 1.05, "Tin ngoài · hiện tắt", "0 bản ghi đạt timestamp/quyền", "#fbeaec"),
        (12.0, 4.85, 2.80, 1.05, "RAG + payload theo t", "7 ghi chú · metrics · allow-list", "#f1ecf7"),
        (8.85, 4.85, 2.80, 1.05, "Qwen3-8B · Modal", "Chọn policy · JSON allow-list", "#e8f1f8"),
        (5.70, 4.85, 2.80, 1.05, "Giám sát số học", "Kết quả đã khép · fallback", "#fff3e7"),
        (2.55, 4.85, 2.80, 1.05, "Dựng mục tiêu", "μ · Σ · λ · α · K · phí", "#e8f3ee"),
        (2.55, 2.75, 2.80, 1.05, "QAOA mô phỏng CPU", "X/XY · N=8/12/16 · p=1/2", "#e8f3ee"),
        (5.70, 2.75, 2.80, 1.05, "Bộ giải cổ điển", "Exact · tham lam · tôi luyện", "#e8f3ee"),
        (8.85, 2.75, 2.80, 1.05, "Mô phỏng giao dịch", "Phí · sức chứa · lệnh thiếu", "#e8f3ee"),
        (12.0, 2.75, 2.80, 1.05, "Kết quả + báo cáo", "JSON/CSV · catalog · hình", "#e8f3ee"),
    ]
    centers: dict[str, tuple[float, float]] = {}
    for x, y, w, h, title, subtitle, color in boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.10", linewidth=1.2, edgecolor="#6f8491", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center", color=INK, weight="bold", fontsize=9.5)
        ax.text(x + w / 2, y + h * 0.30, subtitle, ha="center", va="center", color=INK, fontsize=7.6)
        centers[title] = (x + w / 2, y + h / 2)

    edges = [
        ("Dữ liệu giá + chỉ số", "Kiểm tra + cutoff t"),
        ("Kiểm tra + cutoff t", "Đặc trưng thị trường"),
        ("Đặc trưng thị trường", "Tiểu mô hình"),
        ("Tiểu mô hình", "RAG + payload theo t"),
        ("Tin ngoài · hiện tắt", "RAG + payload theo t"),
        ("RAG + payload theo t", "Qwen3-8B · Modal"),
        ("Qwen3-8B · Modal", "Giám sát số học"),
        ("Giám sát số học", "Dựng mục tiêu"),
        ("Dựng mục tiêu", "QAOA mô phỏng CPU"),
        ("Dựng mục tiêu", "Bộ giải cổ điển"),
        ("QAOA mô phỏng CPU", "Mô phỏng giao dịch"),
        ("Bộ giải cổ điển", "Mô phỏng giao dịch"),
        ("Mô phỏng giao dịch", "Kết quả + báo cáo"),
    ]
    dims = {title: (w, h) for _, _, w, h, title, *_ in boxes}
    for source, target in edges:
        x0, y0 = centers[source]
        x1, y1 = centers[target]
        if source == "QAOA mô phỏng CPU" and target == "Mô phỏng giao dịch":
            # Route below the classical-solver box so the two output paths stay distinct.
            route_y = 2.25
            start = (x0, y0 - dims[source][1] / 2)
            end = (x1, y1 - dims[target][1] / 2)
            ax.plot([start[0], start[0]], [start[1], route_y], color=GRAY, linewidth=1.15)
            ax.plot([start[0], end[0]], [route_y, route_y], color=GRAY, linewidth=1.15)
            ax.add_patch(FancyArrowPatch((end[0], route_y), end, arrowstyle="-|>", mutation_scale=11, linewidth=1.15, color=GRAY))
            continue
        if abs(y0 - y1) < 0.01:
            direction = 1 if x1 > x0 else -1
            start = (x0 + direction * dims[source][0] / 2, y0)
            end = (x1 - direction * dims[target][0] / 2, y1)
        else:
            direction_x = 1 if x1 > x0 else -1
            start = (x0 + direction_x * min(dims[source][0] * 0.30, abs(x1 - x0) * 0.30), y0 - dims[source][1] / 2)
            end = (x1 - direction_x * min(dims[target][0] * 0.30, abs(x1 - x0) * 0.30), y1 + dims[target][1] / 2)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11, linewidth=1.15, color=GRAY, connectionstyle="arc3,rad=0.0"))
    ax.annotate("Fallback khi thiếu lịch sử / bằng chứng yếu", xy=(7.1, 4.62), ha="center", va="top", fontsize=7.2, color=ORANGE)
    ax.text(5.0, 1.05, "Local: dữ liệu · features · solver · giao dịch · đánh giá", ha="center", va="center", fontsize=8.5, color=GREEN, weight="bold")
    ax.text(11.5, 1.05, "Modal chỉ nhận payload tổng hợp; không gửi OHLCV thô", ha="center", va="center", fontsize=8.5, color=BLUE, weight="bold")
    fig.text(0.05, 0.012, "Tin tức bị tắt khi chưa có timestamp, revision và quyền sử dụng được xác minh. Mô phỏng QAOA hiện chạy trên CPU; không có kết quả QPU.", fontsize=8, color=GRAY)
    return _save(fig, Path(output_dir) / "12_agqo_pipeline.png")


def build_market_regime_figure(data_path: str | Path, members_path: str | Path, output_dir: str | Path) -> Path:
    """Plot regime descriptors from observed prices; do not invent news markers."""
    data, _ = load_market_dataset(data_path, members_path)
    indices = data.loc[data.instrument_type == "index"].pivot(index="date", columns="ticker", values="close").sort_index()
    stocks = data.loc[data.instrument_type == "stock"].pivot(index="date", columns="ticker", values="close").sort_index()
    returns = stocks.pct_change(fill_method=None)
    index_returns = indices["VN30"].pct_change(fill_method=None)
    rolling_20d = index_returns.rolling(20, min_periods=20).std() * np.sqrt(252)
    rolling_120d = index_returns.rolling(120, min_periods=120).std() * np.sqrt(252)
    breadth = (returns.rolling(20, min_periods=20).sum() > 0).mean(axis=1)
    cross_dispersion = returns.rolling(20, min_periods=20).sum().std(axis=1)
    common = indices.index
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True, gridspec_kw={"height_ratios": [1.45, 1, 1]})
    ax = axes[0]
    for ticker, color, label in (("VN30", BLUE, "VN30"), ("VNINDEX", ORANGE, "VN-Index")):
        series = indices[ticker].reindex(common)
        ax.plot(common, series / series.iloc[0] * 100, lw=1.5, color=color, label=label)
    ax.set_ylabel("Chỉ số · đầu kỳ = 100")
    ax.legend(ncol=2, frameon=False, loc="upper left")
    ax.set_title("Giá, rủi ro và độ rộng thị trường theo thời gian", loc="left", color=INK, weight="bold")
    ax.grid(axis="y", color=GRID)
    ax = axes[1]
    ax.plot(common, rolling_20d.reindex(common) * 100, color=RED, lw=1.1, label="Biến động thực hiện 20 phiên")
    ax.plot(common, rolling_120d.reindex(common) * 100, color=BLUE, lw=1.1, label="Biến động thực hiện 120 phiên")
    ax.set_ylabel("Độ lệch chuẩn năm hóa (%)")
    ax.legend(ncol=2, frameon=False, loc="upper left")
    ax.grid(axis="y", color=GRID)
    ax = axes[2]
    ax.plot(common, breadth.reindex(common) * 100, color=GREEN, lw=1.0, label="Tỷ lệ mã dương trong 20 phiên")
    ax.set_ylabel("Độ rộng (%)")
    ax.set_ylim(0, 100)
    ax2 = ax.twinx()
    ax2.plot(common, cross_dispersion.reindex(common) * 100, color=ORANGE, lw=1.0, alpha=0.9, label="Phân tán lợi suất chéo")
    ax2.set_ylabel("Độ lệch chuẩn lợi suất 20 phiên (%)")
    left, right = ax.get_legend_handles_labels()
    r2, l2 = ax2.get_legend_handles_labels()
    ax.legend(left + r2, right + l2, ncol=2, frameon=False, loc="upper left")
    ax.grid(axis="y", color=GRID)
    for panel in axes:
        panel.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("Ngày giao dịch")
    fig.text(0.09, 0.012, "Nguồn: CSV OHLCV cục bộ; kỳ 04/01/2022–19/10/2026. Không gắn tin/sự kiện vì chưa có nguồn timestamped đủ điều kiện. Rổ cổ phiếu là snapshot hiện tại, dùng lịch sử có thiên lệch sống sót.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, Path(output_dir) / "13_market_regime_timeline.png")


def build_monthly_return_heatmap(data_path: str | Path, members_path: str | Path, output_dir: str | Path) -> Path:
    """Cross-sectional month returns with an honest, zero-centred scale."""
    data, members = load_market_dataset(data_path, members_path)
    stocks = data.loc[data.instrument_type == "stock"]
    closes = stocks.pivot(index="date", columns="ticker", values="close").sort_index()
    monthly_close = closes.resample("ME").last()
    monthly_returns = monthly_close.pct_change(fill_method=None).reindex(columns=members["ticker"])
    groups = members.set_index("ticker")["group"].to_dict()
    order = sorted(monthly_returns.columns, key=lambda ticker: (groups.get(ticker, ""), ticker))
    matrix = monthly_returns[order].T * 100
    observed = matrix.to_numpy(dtype=float)
    finite = observed[np.isfinite(observed)]
    clip = max(float(np.nanquantile(np.abs(finite), 0.975)), 10.0)
    fig, ax = plt.subplots(figsize=(16, 9))
    norm = TwoSlopeNorm(vmin=-clip, vcenter=0.0, vmax=clip)
    image = ax.imshow(observed, cmap="RdBu_r", norm=norm, aspect="auto", interpolation="nearest")
    month_labels = [period.strftime("%y-%m") for period in matrix.columns]
    tick_positions = np.arange(0, len(month_labels), 3)
    ax.set_xticks(tick_positions, [month_labels[i] for i in tick_positions], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(order)), order, fontsize=8)
    bank_n = int((members.set_index("ticker").loc[order, "group"] == "Ngân hàng").sum())
    if bank_n < len(order):
        ax.axhline(bank_n - 0.5, color=INK, lw=1.1)
    ax.set_xlabel("Tháng; lợi suất close-to-close (%)")
    ax.set_ylabel("Mã hiện thuộc snapshot VN30")
    ax.set_title("Lợi suất chéo theo tháng: nhiều chế độ, không ép một màu", loc="left", color=INK, weight="bold")
    cbar = fig.colorbar(image, ax=ax, pad=0.015)
    cbar.set_label(f"Lợi suất tháng (%) · thang màu giới hạn ±{clip:.1f}% (giá trị cực trị chỉ bị giới hạn màu)")
    ax.grid(False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.text(0.09, 0.012, f"Nguồn: OHLCV cục bộ; {monthly_returns.index.min():%m/%Y}–{monthly_returns.index.max():%m/%Y}. Nền xám biểu thị thiếu lịch sử, không tự điền. Giá chưa xác nhận điều chỉnh corporate action; thành phần hiện tại áp ngược.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, Path(output_dir) / "14_cross_section_monthly_returns.png")


def build_actual_circuit_comparison(
    result_path: str | Path,
    data_path: str | Path,
    members_path: str | Path,
    output_dir: str | Path,
    catalog_path: str | Path,
) -> Path:
    """Rebuild three observed circuits using stored signal, seed, angles and assets."""
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    data, _ = load_market_dataset(data_path, members_path)
    stock = data.loc[data.instrument_type == "stock"]
    close = stock.pivot(index="date", columns="ticker", values="close").sort_index()
    daily_returns = close.pct_change(fill_method=None)
    market_signals = result["ai"]["monthly_signals"]
    guidance = result["agqo_guidance"]["decisions"]
    max_probability = max(market_signals, key=lambda item: item["probability_high_volatility"])
    max_correlation = max(
        guidance,
        key=lambda item: item["context"]["market"].get("mean_pairwise_correlation_252d", -np.inf),
    )
    selected_contexts = [
        (str(min(market_signals, key=lambda item: item["probability_high_volatility"])["signal_date"]), "n12_balanced_x_p1", "Độ rộng cao · xác suất biến động thấp"),
        (str(max_probability["signal_date"]), "n12_balanced_xy_ring_p2", "Độ rộng yếu · xác suất biến động cao"),
        (str(max_correlation["signal_date"]), "n12_correlation_xy_p2", "Tương quan chéo cao · mixer có cấu trúc"),
    ]
    records: list[dict[str, Any]] = []
    for signal_date, policy_id, context_label in selected_contexts:
        signal = next(item for item in market_signals if str(item["signal_date"]) == signal_date)
        guidance_row = next(item for item in guidance if str(item["signal_date"]) == signal_date)
        market_context = guidance_row["context"].get("market", {})
        candidates = tuple(signal["qaoa_candidate_tickers"])
        window = daily_returns.loc[:signal_date, list(candidates)].tail(252).dropna(how="any")
        policy = POLICIES[policy_id]
        policy_row = next(
            row for row in result["qaoa"]["monthly_runs"]
            if row.get("signal_date") == signal_date and row.get("variant") == f"POLICY:{policy_id}"
        )
        seed = int(policy_row["best_seed"])
        run = next(row for row in policy_row["runs"] if int(row["seed"]) == seed)
        previous_weights = run["previous_weights"]
        previous_tickers = tuple(
            ticker for ticker, weight in zip(candidates, previous_weights) if float(weight) > 1e-12
        )
        problem = _build_policy_problem(
            window, candidates, policy_id, int(result["qaoa"]["k"]),
            previous_tickers=previous_tickers, fee_bps=float(result["config"]["fee_bps"]),
        )
        rng = np.random.Generator(np.random.PCG64(seed))
        asset_order = np.arange(problem.n) if policy.mixer == "X" else rng.permutation(problem.n)
        ordered_tickers = [problem.tickers[i] for i in asset_order]
        ordered_covariance = problem.covariance[np.ix_(asset_order, asset_order)]
        ordered_problem = type(problem)(
            tickers=tuple(ordered_tickers),
            mu=problem.mu[asset_order],
            covariance=ordered_covariance,
            k=problem.k,
            risk_aversion=problem.risk_aversion,
            previous_weights=problem.previous_weights[asset_order],
            transaction_costs=problem.transaction_costs[asset_order],
            rebalances_per_year=problem.rebalances_per_year,
            outside_previous_weight=problem.outside_previous_weight,
            outside_transaction_cost_rate=problem.outside_transaction_cost_rate,
        )
        qubo = build_qubo(ordered_problem, mixer=policy.mixer)
        cost_edges = [
            (int(i), int(j))
            for i in range(problem.n) for j in range(i + 1, problem.n)
            if abs(qubo.quadratic[i, j]) > 1e-14
        ]
        mixer_edges = list(mixer_edges_for_problem(ordered_covariance, policy.mixer_layout))
        initial_bits = ([1] * problem.k + [0] * (problem.n - problem.k)) if policy.mixer == "XY" else None
        bits = run.get("best_bits") or []
        chosen = [problem.tickers[i] for i, bit in enumerate(bits) if int(bit)]
        betas = [float(x) for x in run["angles"][: policy.depth]]
        gammas = [float(x) for x in run["angles"][policy.depth :]]
        record = {
            "signal_date": signal_date,
            "market_context_label": context_label,
            "market_context": {
                key: market_context.get(key)
                for key in (
                    "ai_high_volatility_probability",
                    "vn30_annualized_volatility_20d",
                    "mean_pairwise_correlation_252d",
                    "cross_sectional_20d_return_dispersion",
                    "fraction_stocks_positive_20d",
                )
            },
            "entry_date": policy_row["entry_date"],
            "exit_date": policy_row["exit_date"],
            "policy_id": policy_id,
            "agqo_executed_policy_id": signal.get("agqo_policy_id"),
            "is_agqo_executed_policy": signal.get("agqo_policy_id") == policy_id,
            "n_qubits": problem.n,
            "k": problem.k,
            "mixer": policy.mixer,
            "mixer_layout": policy.mixer_layout,
            "depth": policy.depth,
            "seed": seed,
            "candidate_to_qubit": [{"qubit": i, "ticker": ticker} for i, ticker in enumerate(ordered_tickers)],
            "initial_state_bits_by_qubit": initial_bits,
            "cost_objective": {
                "risk_aversion_lambda": policy.risk_aversion,
                "diagonal_shrinkage_alpha": policy.shrinkage,
                "mean_return_estimator": "252-session arithmetic mean, annualized",
                "covariance_estimator": "252-session sample covariance, annualized and diagonally shrunk",
                "k": problem.k,
                "fee_bps_per_side": float(result["config"]["fee_bps"]),
                "rebalance_periods_per_year": problem.rebalances_per_year,
                "linear_term_count": int(np.count_nonzero(np.abs(qubo.linear) > 1e-14)),
                "pair_interaction_count": len(cost_edges),
                "pair_interaction_edges_by_qubit": cost_edges,
                "coefficient_range": {
                    "linear_min": float(qubo.linear.min()),
                    "linear_max": float(qubo.linear.max()),
                    "pair_min_nonzero": float(min(qubo.quadratic[i, j] for i, j in cost_edges)) if cost_edges else None,
                    "pair_max": float(max(qubo.quadratic[i, j] for i, j in cost_edges)) if cost_edges else None,
                },
            },
            "mixer_edges_by_qubit": mixer_edges,
            "angles": {"beta": betas, "gamma": gammas},
            "shots_per_evaluation": int(run["shots_per_evaluation"]),
            "optimizer_evaluations": int(run["evaluations"]),
            "logical_cost_two_qubit_gates": int(run["logical_cost_two_qubit_gate_count"]),
            "logical_mixer_two_qubit_gates": int(run["logical_mixer_two_qubit_gate_count"]),
            "sampled_feasible_probability": float(run["sampled_feasible_probability"]),
            "best_sampled_portfolio": chosen,
            "best_feasible_objective": float(run["best_feasible_score"]),
            "exact_objective": float(policy_row["exact_score"]),
            "normalized_regret": max(0.0, float(policy_row["normalized_objective_regret"])),
            "execution": "NumPy statevector simulation on CPU; logical gates are simulator metadata, not transpiled hardware counts.",
        }
        records.append(record)

    Path(catalog_path).parent.mkdir(parents=True, exist_ok=True)
    Path(catalog_path).write_text(json.dumps({"source_result": Path(result_path).name, "circuit_records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    for ax, record in zip(axes, records):
        mapping = record["candidate_to_qubit"]
        n = len(mapping)
        angle = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, n, endpoint=False)
        pos = np.column_stack([np.cos(angle), np.sin(angle)])
        for i, j in record["cost_objective"]["pair_interaction_edges_by_qubit"]:
            ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]], color=GRID, lw=0.65, alpha=0.6, zorder=1)
        mixer_color = ORANGE if record["mixer"] == "XY" else BLUE
        for i, j in record["mixer_edges_by_qubit"]:
            ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]], color=mixer_color, lw=2.0, alpha=0.95, zorder=2)
        labels = [row["ticker"] for row in mapping]
        selected = set(record["best_sampled_portfolio"])
        node_colors = [GREEN if ticker in selected else "#315f76" for ticker in labels]
        ax.scatter(pos[:, 0], pos[:, 1], s=430, color=node_colors, edgecolor="white", linewidth=1.0, zorder=3)
        for i, (x, y) in enumerate(pos):
            ax.text(x, y, f"q{i}\n{labels[i]}", color="white", ha="center", va="center", fontsize=6.0, weight="bold", zorder=4, linespacing=0.9)
        execution_label = "AGQO THỰC THI" if record["is_agqo_executed_policy"] else "ĐỐI CHỨNG CỐ ĐỊNH"
        record_title = (
            f"{record['market_context_label']}\n{record['policy_id']} · p={record['depth']} · N={n}, K={record['k']}\n"
            f"[{execution_label}]"
        )
        ax.set_title(record_title, color=INK, weight="bold", fontsize=9)
        ax.set_xlim(-1.28, 1.28)
        ax.set_ylim(-1.55, 1.30)
        ax.set_aspect("equal")
        ax.axis("off")
        details = (
            f"P(biến động cao) {record['market_context']['ai_high_volatility_probability']:.1%} · "
            f"độ rộng {record['market_context']['fraction_stocks_positive_20d']:.1%} · "
            f"tương quan {record['market_context']['mean_pairwise_correlation_252d']:.2f}\n"
            f"RZZ {record['logical_cost_two_qubit_gates']} · mixer 2q {record['logical_mixer_two_qubit_gates']}\n"
            f"shots {record['shots_per_evaluation']} · eval {record['optimizer_evaluations']}\n"
            f"regret {max(0.0, record['normalized_regret']):.2%} · khả thi {record['sampled_feasible_probability']:.1%}\n"
            f"β={np.round(record['angles']['beta'], 3).tolist()} · γ={np.round(record['angles']['gamma'], 3).tolist()}"
        )
        ax.text(0.5, -0.16, details, transform=ax.transAxes, ha="center", va="top", fontsize=7.2, color=INK)
    fig.suptitle("Mạch từ ba bối cảnh thị trường đã lưu · ánh xạ mã–qubit theo seed thực tế", x=0.04, ha="left", color=INK, weight="bold", fontsize=15)
    fig.text(0.09, 0.015, "Nút xanh = mã thuộc nghiệm QAOA tốt nhất đã lấy mẫu; nút xanh đậm = mã ngoài nghiệm. Cạnh xám = RZZ cost; cạnh màu = topology mixer. Policy được gắn nhãn AGQO nếu đã thực thi; hai policy khác là đối chứng cố định. XY dùng RXX+RYY mỗi cạnh/lớp. Chưa transpile hoặc chạy QPU.", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.10, 1, 0.92))
    return _save(fig, Path(output_dir) / "15_actual_qaoa_circuit_comparison.png")
