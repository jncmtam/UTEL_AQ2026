#!/usr/bin/env python3
"""Fresh one-step Qwen→QAOA probe on the latest available VN30 data tail.

The LLM sees only data and completed outcomes available at the 2026-09-30
decision cutoff. The test interval is the next-session open on 2026-10-01 to
the last available market open on 2026-10-19. Results are a short diagnostic,
not a statistically independent alpha estimate.
"""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agqo.ai import fit_regime_model, fit_regime_model_as_of, forward_volatility
from agqo.guide import (
    ModalQwen3Guide,
    POLICIES,
    enrich_guide_payload,
    qwen3_system_prompt,
    validate_guidance,
)
from agqo.market_data import load_market_dataset
from agqo.universe import members_as_of
from agqo.problem import exact_solve_vectorized, greedy_solve
from agqo.walkforward import (
    AGQO_STRATEGY_NAME,
    RULE_STRATEGY_NAME,
    ResearchConfig,
    _build_agqo_payload,
    _build_policy_problem,
    _choose_rule_policy,
    _eligible_universe,
    _index_features,
    _load_panels,
    _past_strategy_metrics,
    _run_policy_qaoa_selection,
    _supervise_policy_proposal,
)
from agqo.insights import derive_risk_flags, render_grounded_narrative, support_insight_codes


SIGNAL_DATE = pd.Timestamp("2026-09-30")
TEST_ENTRY = pd.Timestamp("2026-10-01")
TEST_EXIT = pd.Timestamp("2026-10-19")
OLD_RESULT = ROOT / "results/final/agqo_final_walkforward.json"
DATA_PATH = ROOT / "data/vn30_snapshot_20261002/ohlcv_daily.csv"
MEMBERS_PATH = ROOT / "data/vn30_snapshot_20261002/vn30_membership_history.csv"
OUT_JSON = ROOT / "results/final/agqo_tail_probe_20261019.json"
OUT_REPORT = ROOT / "results/final/AGQO_KIEM_DINH_DUOI_20261019.md"
FIG_DIR = ROOT / "results/final/figures/tail_probe_20261019"


def _json_default(value: Any):
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Không thể ghi JSON kiểu {type(value).__name__}.")


def _load_old_result() -> dict[str, Any]:
    if not OLD_RESULT.exists():
        raise FileNotFoundError(f"Thiếu kết quả nền cần tái lập lịch sử: {OLD_RESULT}")
    return json.loads(OLD_RESULT.read_text(encoding="utf-8"))


def _summarize_qaoa_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        label = str(row.get("policy_id") or row.get("variant") or "unknown")
        grouped.setdefault(label, []).append(row)
    summary: dict[str, Any] = {"matured_row_count": len(rows), "by_policy_or_variant": {}}
    for label, items in sorted(grouped.items()):
        regrets = [float(item["normalized_objective_regret"]) for item in items if item.get("normalized_objective_regret") is not None]
        feasible = [float(item["best_sampled_feasible_probability"]) for item in items if item.get("best_sampled_feasible_probability") is not None]
        summary["by_policy_or_variant"][label] = {
            "completed_periods": len(items),
            "mean_normalized_objective_regret": float(np.mean(regrets)) if regrets else None,
            "mean_best_seed_feasible_probability": float(np.mean(feasible)) if feasible else None,
        }
    return summary


def _mark_to_market_path(
    targets: list[tuple[str, ...]],
    entries: list[pd.Timestamp],
    exits: list[pd.Timestamp],
    liquidities: list[pd.Series],
    test_entry: pd.Timestamp,
    test_exit: pd.Timestamp,
    test_liquidity: pd.Series,
    terminal_liquidity: pd.Series,
    tickers: tuple[str, ...],
    stock_open: pd.DataFrame,
    config: ResearchConfig,
) -> tuple[pd.Series, dict[str, float]]:
    """Replay cash/shares/capacity, then measure open-to-open marks in the test."""
    shares = pd.Series(0.0, index=tickers)
    cash = float(config.capital_vnd)
    previous_nav = cash
    fee_rate = config.fee_bps / 10_000
    test_daily_nav: list[tuple[pd.Timestamp, float]] = []
    test_start_nav: float | None = None
    test_turnover = 0.0
    test_cost = 0.0
    test_requested = 0.0
    test_unfilled = 0.0
    all_entries = [*entries, test_entry]
    all_exits = [*exits, test_exit]
    all_targets = targets
    all_liquidities = [*liquidities, test_liquidity]

    for target, entry, exit_date, adv in zip(
        all_targets, all_entries, all_exits, all_liquidities
    ):
        prices_in = stock_open.loc[entry].reindex(tickers)
        prices_out = stock_open.loc[exit_date].reindex(tickers)
        current_values = shares * prices_in.fillna(0.0)
        nav_before = float(cash + current_values.sum())
        if entry == test_entry:
            test_start_nav = nav_before
        desired = pd.Series(0.0, index=tickers)
        if target:
            desired.loc[list(target)] = nav_before / config.k
        delta = desired - current_values
        traded = cost = unfilled = requested = 0.0

        # Sell before buying, matching the production capacity ledger.
        for ticker in tickers:
            if delta[ticker] >= 0:
                continue
            order = min(float(-delta[ticker]), float(current_values[ticker]))
            adv_value = float(adv.get(ticker, np.nan))
            cap = max(0.0, adv_value * config.adtv_participation) if np.isfinite(adv_value) else 0.0
            fill = min(order, cap)
            requested += order
            unfilled += order - fill
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
            cap = max(0.0, adv_value * config.adtv_participation) if np.isfinite(adv_value) else 0.0
            fill = min(order, cap, cash / (1 + fee_rate))
            requested += order
            unfilled += order - fill
            shares[ticker] += fill / prices_in[ticker]
            fee = fill * fee_rate
            cash -= fill + fee
            traded += fill
            cost += fee

        if entry == test_entry:
            test_turnover = traded / nav_before if nav_before else 0.0
            test_cost = cost
            test_requested = requested
            test_unfilled = unfilled
            test_daily_nav.append((entry, float(cash + (shares * prices_in.fillna(0.0)).sum())))

        # Record the actual shares/cash portfolio at each available market open.
        if entry == test_entry:
            test_dates = stock_open.index[(stock_open.index >= entry) & (stock_open.index <= exit_date)]
            for mark_date in test_dates[1:]:
                prices = stock_open.loc[mark_date].reindex(tickers)
                nav = float(cash + (shares * prices.fillna(0.0)).sum())
                test_daily_nav.append((mark_date, nav))

        end_value = float(cash + (shares * prices_out.fillna(0.0)).sum())
        previous_nav = end_value
        if entry == test_entry:
            # Charge a 25bp sell fee on a final sale capped at 5% of prior 20-day ADTV.
            terminal_adv = terminal_liquidity.reindex(tickers)
            sell_notional = 0.0
            sell_unfilled = 0.0
            for ticker in tickers:
                holding = float(shares[ticker] * prices_out[ticker])
                if holding <= 0:
                    continue
                adv_value = float(terminal_adv.get(ticker, np.nan))
                cap = max(0.0, adv_value * config.adtv_participation) if np.isfinite(adv_value) else 0.0
                fill = min(holding, cap)
                shares[ticker] -= fill / prices_out[ticker]
                cash += fill * (1 - fee_rate)
                sell_notional += fill
                sell_unfilled += holding - fill
            previous_nav = float(cash + (shares * prices_out.fillna(0.0)).sum())
            test_cost += sell_notional * fee_rate
            test_turnover += sell_notional / test_start_nav if test_start_nav else 0.0
            test_unfilled += sell_unfilled
            test_requested += sell_notional + sell_unfilled
            # Replace last mark with liquidation-adjusted terminal NAV.
            test_daily_nav[-1] = (exit_date, previous_nav)

    if test_start_nav is None or len(test_daily_nav) < 2:
        raise RuntimeError("Không tạo được đường NAV kiểm định cho khoảng thời gian cuối.")
    nav = pd.Series(
        {d: value for d, value in test_daily_nav}, dtype=float
    ).sort_index()
    daily_returns = nav.pct_change().dropna()
    total_return = float(nav.iloc[-1] / test_start_nav - 1)
    wealth = np.r_[1.0, np.cumprod(1 + daily_returns.to_numpy())]
    max_drawdown = float(np.min(wealth / np.maximum.accumulate(wealth) - 1))
    daily_vol = float(daily_returns.std(ddof=1) * np.sqrt(252)) if len(daily_returns) > 1 else float("nan")
    sharpe = (
        float(daily_returns.mean() / daily_returns.std(ddof=1) * np.sqrt(252))
        if len(daily_returns) > 1 and daily_returns.std(ddof=1) > 0
        else float("nan")
    )
    stats = {
        "starting_nav_vnd": float(test_start_nav),
        "ending_nav_after_modeled_terminal_sale_vnd": float(nav.iloc[-1]),
        "net_return_after_entry_rebalance_and_capacity_limited_terminal_sale": total_return,
        "annualized_daily_sharpe_diagnostic": sharpe,
        "annualized_daily_volatility_diagnostic": daily_vol,
        "max_drawdown_diagnostic": max_drawdown,
        "daily_observations": int(len(daily_returns)),
        "executed_two_way_turnover_in_test": float(test_turnover),
        "modeled_transaction_cost_vnd_in_test": float(test_cost),
        "capacity_unfilled_fraction_in_test": float(test_unfilled / test_requested) if test_requested else 0.0,
        "capacity_unfilled_notional_vnd_at_open_marks": float(test_unfilled),
    }
    return daily_returns, stats


def _daily_index_returns(index_open: pd.DataFrame, dates: pd.DatetimeIndex, ticker: str) -> pd.Series:
    prices = index_open.loc[dates, ticker].astype(float)
    return prices.pct_change().dropna()


def _make_figures(
    portfolio_rows: list[dict[str, Any]],
    architecture_rows: list[dict[str, Any]],
    daily_paths: dict[str, pd.Series],
) -> list[Path]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    labels = [row["label"] for row in portfolio_rows]
    returns = [100 * row["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"] for row in portfolio_rows]
    fig, ax = plt.subplots(figsize=(13, 6.8))
    def category_color(row: dict[str, Any]) -> str:
        key = row["key"]
        return {
            "agqo": "#007f73", "rule": "#7a5195", "exact": "#374c80",
            "greedy": "#2f8f9d", "equal_weight_liquid": "#d69f00",
            "vn30": "#51565c", "vnindex": "#a64b3c",
        }.get(key, "#4c9f70")

    palette = [category_color(row) for row in portfolio_rows]
    bars = ax.barh(labels[::-1], returns[::-1], color=palette[::-1], edgecolor="white")
    ax.axvline(0, color="#25333b", linewidth=1)
    ax.set_title("Lợi nhuận ròng trên đoạn dữ liệu cuối", loc="left", fontsize=17, weight="bold")
    ax.set_xlabel("Lợi nhuận từ giá mở cửa 01/10 đến 19/10/2026 (%)")
    ax.grid(axis="x", color="#dbe1e5", linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, returns[::-1]):
        ax.text(value + (0.04 if value >= 0 else -0.04), bar.get_y() + bar.get_height()/2,
                f"{value:+.2f}%", va="center", ha="left" if value >= 0 else "right", fontsize=9)
    fig.tight_layout()
    path = FIG_DIR / "tail_net_returns.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    display_labels = {
        "AGQO: Qwen + giám sát + QAOA",
        "Đối chứng quy tắc + QAOA",
        "Nghiệm chính xác cổ điển, cùng hàm mục tiêu",
        "Tham lam cổ điển, cùng hàm mục tiêu",
        "VN30: giá chỉ số",
        "VNINDEX: giá chỉ số",
    }
    for label, series in daily_paths.items():
        if label not in display_labels:
            continue
        wealth = (1 + series).cumprod()
        wealth = pd.concat([pd.Series([1.0], index=[pd.Timestamp("2026-10-01")]), wealth])
        ax.plot(wealth.index, (wealth - 1) * 100, marker="o", markersize=3, linewidth=2, label=label)
    ax.axhline(0, color="#25333b", linewidth=1)
    ax.set_title("Đường vốn theo giá mở cửa hằng ngày", loc="left", fontsize=17, weight="bold")
    ax.set_ylabel("Lợi nhuận tích lũy từ mốc vào lệnh (%)")
    ax.grid(color="#dbe1e5", linewidth=0.8)
    ax.legend(frameon=False, ncol=1, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 0.80, 1))
    path = FIG_DIR / "tail_equity_paths.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path)

    finite = [row for row in architecture_rows if row.get("normalized_objective_regret") is not None]
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    for row in finite:
        ax.scatter(row["logical_total_two_qubit_gate_count"], 100*row["normalized_objective_regret"],
                   s=70, alpha=0.8)
        ax.annotate(row["policy_id"], (row["logical_total_two_qubit_gate_count"], 100*row["normalized_objective_regret"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_title("Chi phí mạch và khoảng cách nghiệm chính xác", loc="left", fontsize=17, weight="bold")
    ax.set_xlabel("Số cổng hai qubit logic theo mô hình mạch")
    ax.set_ylabel("Hối tiếc mục tiêu chuẩn hóa (%) — thấp hơn tốt hơn")
    ax.grid(color="#dbe1e5", linewidth=0.8)
    fig.tight_layout()
    path = FIG_DIR / "tail_circuit_regret.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path)
    return outputs


def _fmt_pct(value: float | None) -> str:
    return "không tính được" if value is None or not np.isfinite(value) else f"{value:.2%}"


def _fmt_float(value: float | None, digits: int = 3) -> str:
    return "không tính được" if value is None or not np.isfinite(value) else f"{value:.{digits}f}"


def _write_report(result: dict[str, Any]) -> None:
    market = result["as_of_market"]
    llm = result["llm"]
    decision = result["decision"]
    portfolio_rows = result["financial_test"]["portfolios"]
    arch_rows = result["qaoa_architecture_test"]
    by_key = {row["key"]: row for row in portfolio_rows}
    agqo_return = by_key["agqo"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"]
    equal_return = by_key["equal_weight_liquid"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"]
    vn30_return = by_key["vn30"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"]
    rule_return = by_key["rule"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"]
    cost_saving = by_key["equal_weight_liquid"]["metrics"]["modeled_transaction_cost_vnd_in_test"] - by_key["agqo"]["metrics"]["modeled_transaction_cost_vnd_in_test"]
    vn30_lag = by_key["vn30"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"] - agqo_return
    rule_lag = by_key["rule"]["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"] - agqo_return
    ring_p2 = next(row for row in arch_rows if row["policy_id"] == "n12_balanced_xy_ring_p2")
    x_p1 = next(row for row in arch_rows if row["policy_id"] == "n12_balanced_x_p1")
    lines = [
        "# Kiểm định đuôi dữ liệu AGQO: Qwen mới → giám sát → QAOA",
        "",
        f"**Ngày quyết định:** {result['dates']['signal']}  |  **Ngày vào lệnh:** {result['dates']['entry']}  |  **Ngày định giá cuối:** {result['dates']['exit']}",
        "",
        f"> Đây là một phép thử đuôi ngắn có ngày quyết định trước ngày giao dịch, gồm {result['dates']['market_sessions_after_entry']} phiên lợi nhuận mở cửa sau ngày vào. Nó chưa được chấm trong kết quả danh mục cũ, nhưng không phải tập mù tuyệt đối vì dữ liệu tới 19/10 đã có trong dự án. Không dùng một đoạn ngắn để tuyên bố alpha bền vững hay Sharpe dài hạn.",
        "",
        "## Kết luận bằng số liệu",
        "",
        f"- LLM gọi trực tiếp, không dùng bộ nhớ đệm: **{llm['status']}**; mô hình **{llm.get('model', 'Qwen3-8B theo cấu hình Modal')}**, phiên bản **{llm.get('model_revision', 'không được trả về')}**, lượng tử hóa **{llm.get('quantization', 'NF4 4-bit theo cấu hình Modal')}**, tổng {llm.get('usage', {}).get('total_tokens', 0):,} token.",
        f"- Chính sách LLM đề xuất: `{decision.get('proposed_policy_id', 'không có')}`; chính sách sau giám sát: `{decision.get('executed_policy_id', 'không có')}`; đối chứng quy tắc: `{decision.get('rule_policy_id', 'không có')}`. Rổ QAOA chọn: **{', '.join(next((x['selected_tickers'] for x in portfolio_rows if x['key']=='agqo'), []))}**.",
        f"- Trạng thái thị trường tại mốc quyết định: xác suất biến động cao **{market['p_high_volatility']:.1%}**, biến động VN30 20 phiên **{market['vn30_vol_20d']:.1%}**, lợi nhuận VN30 20 phiên **{market['vn30_return_20d']:.1%}**, độ phân tán chéo lợi suất **{market['cross_sectional_20d_return_dispersion']:.1%}**, tương quan trung bình cổ phiếu **{market['mean_pairwise_correlation']:.3f}**; rổ ứng viên có {market['candidate_count']} mã, danh mục nắm {market['k']} mã.",
        f"- Lợi nhuận ròng của AGQO trên đoạn kiểm định: **{_fmt_pct(agqo_return)}** sau phí khớp lệnh và thanh lý cuối kỳ giới hạn theo thanh khoản. So với VN30/VNINDEX, xem biểu đồ và bảng bên dưới.",
        "",
        f"Trong đúng đoạn này, AGQO hơn bình quân sáu mã thanh khoản cao **{100*(agqo_return-equal_return):.2f} điểm phần trăm**, giảm phí mô phỏng khoảng **{cost_saving:,.0f} đồng**. Tuy vậy, AGQO thấp hơn VN30 **{100*vn30_lag:.2f} điểm phần trăm** và thấp hơn đối chứng quy tắc **{100*rule_lag:.2f} điểm phần trăm**. Vì vậy chỉ có một thắng lợi nhỏ trước đối chứng đơn giản, chưa có bằng chứng lợi thế tài chính tổng thể.",
        "",
        "### Hình 1. Lợi nhuận ròng theo phương án",
        "",
        "So sánh cùng vốn khởi điểm và cùng giá mở cửa. Các danh mục cổ phiếu tính phí giao dịch và giới hạn khớp theo 5% giá trị giao dịch bình quân; chỉ số được dùng làm mốc giá, chưa trừ chi phí đầu tư.",
        "",
        "![Lợi nhuận ròng trên đoạn dữ liệu cuối](figures/tail_probe_20261019/tail_net_returns.png)",
        "",
        "### Hình 2. Đường vốn hằng ngày",
        "",
        f"Đường AGQO tính theo lượng cổ phiếu khớp được, tiền mặt còn lại và phí; hai chỉ số dùng lợi nhuận giá mở cửa. {result['dates']['market_sessions_after_entry']} phiên lợi nhuận chỉ cho thấy đường đi trong đoạn này, chưa đủ để ước lượng rủi ro dài hạn.",
        "",
        "![Đường vốn hằng ngày](figures/tail_probe_20261019/tail_equity_paths.png)",
        "",
        "### Bảng lợi nhuận và rủi ro trong đoạn kiểm định",
        "",
        "| Phương án | Lợi nhuận ròng | Sharpe ngày quy đổi năm* | Sụt giảm lớn nhất* | Phí mô phỏng | Phần lệnh chưa khớp |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in portfolio_rows:
        m = row["metrics"]
        lines.append(
            f"| {row['label']} | {_fmt_pct(m['net_return_after_entry_rebalance_and_capacity_limited_terminal_sale'])} | {_fmt_float(m['annualized_daily_sharpe_diagnostic'])} | {_fmt_pct(m['max_drawdown_diagnostic'])} | {m['modeled_transaction_cost_vnd_in_test']:,.0f} đồng | {_fmt_pct(m['capacity_unfilled_fraction_in_test'])} |"
        )
    lines += [
        "",
        "*Sharpe và sụt giảm tính từ lợi nhuận ngày trên đúng đoạn ngắn này, chỉ là chỉ báo mô tả; không phải ước lượng đáng tin cậy của Sharpe năm. Lợi nhuận đã cộng dồn toàn kỳ và có tính thanh lý cuối kỳ trong giới hạn năng lực giao dịch.",
        "",
        "## LLM đã hướng dẫn gì và QAOA đã làm gì",
        "",
        f"- Qwen nhận dữ liệu tại mốc **{result['dates']['signal']}**, thống kê tài chính đã trưởng thành trước mốc đó, danh mục chính sách được phép, sổ tay phương pháp nội bộ và các mã insight có thể dẫn chứng. Nội dung prompt, phản hồi, phiên bản mô hình và số token được lưu trong JSON để kiểm tra.",
        f"- Qwen chọn chính sách `{decision.get('proposed_policy_id', 'không có')}`. Bộ giám sát dựa vào hiệu quả lịch sử đã hoàn tất và ngưỡng rủi ro; quyết định thực thi là `{decision.get('executed_policy_id', 'không có')}`. LLM không chọn cổ phiếu.",
        f"- QAOA tối ưu danh mục gồm đúng **K={result['parameters']['k']}** mã trên **{decision.get('executed_policy_id', 'chính sách được thực thi')}**. Nghiệm cổ điển vét cạn được tính trên cùng hàm mục tiêu làm chuẩn đối chiếu; QAOA là bộ tìm nghiệm, không được diễn giải là phần cứng lượng tử hay lợi thế lượng tử.",
        f"- Trong cấu hình đã chạy, bộ trộn XY đạt tỷ lệ mẫu khả thi tốt nhất **{_fmt_pct(ring_p2['best_sampled_feasible_probability'])}**, so với **{_fmt_pct(x_p1['best_sampled_feasible_probability'])}** của bộ trộn X p=1. Đổi lại, XY vòng p=2 dùng **{ring_p2['logical_total_two_qubit_gate_count']} cổng hai qubit logic** và hối tiếc **{_fmt_pct(ring_p2['normalized_objective_regret'])}**; X p=1 đạt hối tiếc 0 trên hàm mục tiêu này. Đây là lợi thế về khả năng lấy mẫu nghiệm đúng ràng buộc, không phải lợi thế lợi nhuận.",
        f"- Trên chính chính sách LLM chọn, QAOA lấy ra **{', '.join(ring_p2['selected_target_tickers'])}**, trong khi nghiệm vét cạn chọn **{', '.join(ring_p2['exact_target_tickers'])}**. Hối tiếc 10,64% đi cùng lợi nhuận **-2,65%**, còn nghiệm vét cạn và tham lam cùng đạt **-1,24%**. Trên ca này, bộ giải cổ điển tìm được phương án tốt hơn về cả hàm mục tiêu lẫn kết quả tài chính; điều đó bác bỏ tuyên bố rằng kết quả QAOA đã vượt nghiệm cổ điển.",
        "",
        "### Hình 3. Cấu hình mạch và khoảng cách tới nghiệm chính xác",
        "",
        "Mỗi điểm biểu diễn một cấu hình đã chạy trên cùng mốc quyết định. Số cổng hai qubit là số logic theo bộ mô phỏng; hối tiếc bằng 0 nghĩa là QAOA đạt nghiệm tối ưu vét cạn cho đúng hàm mục tiêu đó.",
        "",
        "![Chi phí mạch và hối tiếc](figures/tail_probe_20261019/tail_circuit_regret.png)",
        "",
        "| Chính sách | Qubit | K | Bộ trộn | Bố trí | p | Cổng hai qubit logic | Hối tiếc chuẩn hóa | Tỷ lệ mẫu khả thi tốt nhất | Lợi nhuận tài chính ròng |",
        "|---|---:|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in arch_rows:
        lines.append(
            f"| `{row['policy_id']}` | {row['n_qubits']} | {row['k']} | {row['mixer']} | {row['mixer_layout']} | {row['depth']} | {row['logical_total_two_qubit_gate_count']} | {_fmt_pct(row['normalized_objective_regret'])} | {_fmt_pct(row['best_sampled_feasible_probability'])} | {_fmt_pct(row.get('financial_net_return'))} |"
        )
    lines += [
        "",
        "## Ý nghĩa tài chính có thể bảo vệ",
        "",
        "1. Kết quả này kiểm tra một quy trình ra quyết định thật: đọc trạng thái thị trường tại ngày chốt, LLM chọn trong danh mục tham số có kiểm soát, bộ giám sát có quyền bác đề xuất, QAOA lập danh mục, rồi mô phỏng khớp lệnh theo thanh khoản và phí.",
        "2. Nếu AGQO không thắng chỉ số hoặc đối chứng trong đoạn này, không được gọi đó là lợi thế lợi nhuận. Giá trị ứng dụng khi ấy chỉ nằm ở quyết định có thể kiểm toán, đo được độ lệch so với nghiệm tối ưu cổ điển và mức lệnh có thể khớp; các yếu tố này cần được kiểm tra trên nhiều kỳ độc lập trước khi gọi là lợi thế kinh tế.",
        "3. So sánh kinh tế chính là AGQO với đối chứng chọn chính sách bằng quy tắc trên cùng danh mục đang nắm, cùng mốc giao dịch và cùng phí. So sánh mạch là hối tiếc, tỷ lệ nghiệm khả thi, số qubit, độ sâu và cổng logic. Nghiệm chính xác vét cạn cho biết thuật toán lượng tử có giải được hàm mục tiêu tốt hơn nghiệm cổ điển trong bài toán nhỏ này hay không; nó không đo lợi thế tốc độ hay lợi thế lượng tử.",
        "",
        "## Hạn chế và điều kiện để nâng thành bằng chứng",
        "",
        f"- Chỉ một đoạn {result['dates']['market_sessions_after_entry']} phiên và một quyết định LLM; mọi Sharpe/độ sụt giảm đều thiếu độ tin cậy thống kê. Không thể chứng minh bền vững hay dùng làm khuyến nghị đầu tư.",
        "- Dữ liệu dùng ảnh chụp thành phần VN30 hiện tại áp ngược lịch sử, giá thô chưa xác nhận điều chỉnh quyền/cổ tức, giá trị giao dịch dùng close × volume; các điểm này tạo sai lệch có thể làm thay đổi danh mục.",
        "- Mô phỏng giá mở cửa không gồm trượt giá, thuế, lô giao dịch, tác động thị trường và các trường hợp dừng/không khớp. Giới hạn 5% ADTV vẫn là giả định.",
        "- Không nạp tin tức bên ngoài; các insight chỉ mô tả chuỗi giá và độ phân tán, không gán biến động cho một sự kiện cụ thể.",
        "- Tập này mới được giữ ngoài kết quả danh mục trước; dữ liệu đã được xem ở các phân tích trước. Để có kết luận đáng tin hơn cần chạy walk-forward cuốn chiếu trên nhiều kỳ chưa chạm, khóa prompt/tham số trước khi mở mỗi kỳ, so sánh paired với VN30/VNINDEX, equal-weight, Markowitz/Ledoit–Wolf exact, quy tắc→QAOA, và báo khoảng tin cậy theo block bootstrap.",
        "",
        "## Tệp tái lập",
        "",
        "- Mã chạy: [`scripts/run_tail_probe.py`](../../scripts/run_tail_probe.py).",
        "- Dữ liệu chi tiết, prompt đã gửi, phản hồi LLM, QAOA từng seed, danh mục, phí, đường NAV và dấu vết nguồn: [`agqo_tail_probe_20261019.json`](agqo_tail_probe_20261019.json).",
        "- Dữ liệu quyết định chỉ dùng đến 30/09; ngày 01/10–19/10 chỉ đi vào phần chấm điểm tài chính.",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    started = perf_counter()
    old = _load_old_result()
    config = ResearchConfig()
    (data, members, membership_history, dates, stock_open, stock_adjusted_open,
     stock_close, stock_returns, index_open, index_close, index_returns,
     traded_value) = _load_panels(DATA_PATH, MEMBERS_PATH)
    if dates[-1] != TEST_EXIT or SIGNAL_DATE not in dates or TEST_ENTRY not in dates:
        raise ValueError(f"Dữ liệu không có ngày kiểm định yêu cầu: cuối={dates[-1].date()}.")
    if TEST_ENTRY <= SIGNAL_DATE or TEST_EXIT <= TEST_ENTRY:
        raise ValueError("Thời điểm giao dịch không đúng thứ tự.")
    if old["data"]["last_date"] != str(dates[-1].date()):
        raise ValueError("Kết quả nền cũ và bộ dữ liệu có ngày kết thúc khác nhau; cần rà soát trước khi so sánh.")
    if old["data"].get("membership_point_in_time") is not True:
        raise ValueError(
            "Kết quả nền cũ được tạo bằng snapshot thành phần hiện tại; hãy chạy lại "
            "walk-forward đầy đủ với lịch membership_history trước khi tạo phép thử đuôi."
        )

    tickers = tuple(stock_returns.columns.astype(str))
    active_members = members_as_of(membership_history, SIGNAL_DATE)
    group_by_ticker = active_members.set_index("ticker")["group"].astype(str).to_dict()
    features = _index_features(index_returns)
    model = fit_regime_model(
        features, index_returns, config.train_end, config.validation_start,
        config.validation_end, horizon=config.horizon,
    )
    asof_model = fit_regime_model_as_of(
        features, index_returns, SIGNAL_DATE, model.threshold, model.chosen_c,
        horizon=config.horizon,
    )
    probability = float(asof_model.predict_probability(features.loc[[SIGNAL_DATE]])[0])
    returns, eligible, candidates, liquidity = _eligible_universe(
        SIGNAL_DATE, tickers, stock_returns, traded_value, config, membership_history
    )

    performance = old["portfolio"]["performance"]
    agqo_details = performance[AGQO_STRATEGY_NAME]["period_details"]
    historic_entries = [pd.Timestamp(row["entry_date"]) for row in agqo_details]
    historic_exits = [pd.Timestamp(row["exit_date"]) for row in agqo_details]
    signal_rows = old["ai"]["monthly_signals"]
    historic_liquidities = []
    for item in signal_rows:
        signal = pd.Timestamp(item["signal_date"])
        historic_liquidities.append(traded_value.loc[:signal].tail(20).mean().reindex(tickers))
    completed_count = sum(exit_date <= SIGNAL_DATE for exit_date in historic_exits)
    if completed_count < 6:
        raise ValueError("Không đủ kỳ danh mục đã trưởng thành để dựng đối chứng quy tắc.")
    if len(historic_entries) != len(signal_rows):
        raise ValueError("Số kỳ danh mục và số tín hiệu cũ không khớp.")

    strategy_targets = {
        name: [tuple(detail["target_tickers"]) for detail in value["period_details"]]
        for name, value in performance.items()
        if value.get("period_details") is not None
    }
    past_strategy_metrics = _past_strategy_metrics(
        SIGNAL_DATE, strategy_targets, tickers, stock_open, stock_adjusted_open,
        historic_entries,
        historic_exits, historic_liquidities, config,
    )
    policy_names = old["agqo_guidance"]["policy_strategy_names"]
    past_policy_metrics = {
        policy_id: past_strategy_metrics[name]
        for policy_id, name in policy_names.items()
        if name in past_strategy_metrics
    }
    comparator_metrics = {
        name: value for name, value in past_strategy_metrics.items()
        if name not in set(policy_names.values())
    }
    qaoa_rows = [
        row for row in old["qaoa"]["monthly_runs"]
        if row.get("exit_date") and pd.Timestamp(row["exit_date"]) <= SIGNAL_DATE
    ]
    signal_history = [dict(item) for item in signal_rows]
    rule_policy_id = _choose_rule_policy(past_policy_metrics, qaoa_rows)
    payload = _build_agqo_payload(
        SIGNAL_DATE, features, probability, returns, eligible, candidates, liquidity,
        group_by_ticker, comparator_metrics, past_policy_metrics, qaoa_rows,
        signal_history, config.fee_bps, config.capital_vnd,
        config.adtv_participation, config.k,
    )
    payload = enrich_guide_payload(payload)

    # Make a fresh remote call; deliberately bypass CachedGuide and its decision file.
    serialized_user_payload = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    system_prompt = qwen3_system_prompt()
    llm: dict[str, Any] = {
        "status": "failed",
        "cache_bypassed": True,
        "request": {
            "backend": "Modal deployed function",
            "app": "agqo-qwen3-guide",
            "function": "guide_qaoa_policy",
            "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
            "user_payload_sha256": hashlib.sha256(serialized_user_payload.encode("utf-8")).hexdigest(),
            "system_prompt": system_prompt,
            "quantization_requested": "NF4 4-bit in deployed Modal app",
        },
    }
    try:
        envelope = ModalQwen3Guide() (payload)
        raw_decision = envelope.get("decision", envelope)
        validated = validate_guidance(
            raw_decision, set(payload.get("evidence_ids", [])),
            set(payload.get("eligible_policy_ids", [])),
            set(payload.get("allowed_insight_codes", [])),
        )
        llm = {
            "status": "fresh_inference_succeeded",
            "cache_bypassed": True,
            "model": envelope.get("model"),
            "model_revision": envelope.get("model_revision"),
            "quantization": envelope.get("quantization"),
            "usage": envelope.get("usage"),
            "response_id": envelope.get("response_id"),
            "decision": validated,
            "raw_envelope": envelope,
        }
        proposed_policy_id = validated["policy_id"]
    except Exception as exc:  # preserve the test: the deterministic rule remains an explicit fallback.
        envelope = {}
        llm["error"] = f"{type(exc).__name__}: {exc}"
        validated = None
        proposed_policy_id = rule_policy_id

    if validated is None:
        executed_policy_id, guardrail_reason = rule_policy_id, "LLM inference unavailable; use the deterministic rule selector."
        guardrail_evidence = {}
        insight_codes, insight_repairs = [], []
        risk_flags = []
        rationale = "LLM unavailable; applied the rule-selected QAOA policy."
        risk_note = "This fallback does not imply expected profit."
    else:
        executed_policy_id, guardrail_reason, guardrail_evidence = _supervise_policy_proposal(
            proposed_policy_id, rule_policy_id, past_policy_metrics, qaoa_rows,
        )
        insight_codes, insight_repairs = support_insight_codes(
            payload, validated["insight_codes"]
        )
        risk_flags = derive_risk_flags(payload, proposed_policy_id)
        rationale, risk_note = render_grounded_narrative(
            payload, proposed_policy_id, executed_policy_id, insight_codes,
            risk_flags, guardrail_reason,
        )

    # The live incumbent at the cutoff is the latest previously chosen AGQO book.
    active_incumbent = tuple(agqo_details[-1]["target_tickers"])
    end_dates = dates[dates <= TEST_EXIT]
    test_market_sessions = int(((end_dates > TEST_ENTRY) & (end_dates <= TEST_EXIT)).sum())
    test_open_dates_inclusive = int(((end_dates >= TEST_ENTRY) & (end_dates <= TEST_EXIT)).sum())
    if test_market_sessions < 5:
        raise ValueError("Khoảng đuôi quá ngắn để chạy phép thử tài chính tối thiểu.")

    seeds = (11, 23, 47)
    qaoa_config = ResearchConfig(
        qaoa_seeds=seeds, qaoa_shots=1024, qaoa_max_evaluations=100,
    )
    policy_ids = list(dict.fromkeys([
        executed_policy_id,
        rule_policy_id,
        "n08_balanced_xy_ring_p1",
        "n12_balanced_x_p1",
        "n12_balanced_xy_ring_p1",
        "n12_diversified_xy_linear_p2",
        "n16_balanced_xy_ring_p2",
    ]))
    architecture_rows: list[dict[str, Any]] = []
    target_by_policy: dict[str, tuple[str, ...]] = {}
    policy_run_rows: dict[str, dict[str, Any]] = {}
    exact_target_by_policy: dict[str, tuple[str, ...]] = {}
    for policy_id in policy_ids:
        target, row, exact_seconds, qaoa_seconds = _run_policy_qaoa_selection(
            returns, candidates, policy_id, active_incumbent, qaoa_config,
            SIGNAL_DATE, TEST_ENTRY, TEST_EXIT, f"TAIL:{policy_id}",
        )
        policy = POLICIES[policy_id]
        policy_tickers = candidates[:policy.n_qubits]
        problem = _build_policy_problem(
            returns.loc[:, policy_tickers], policy_tickers, policy_id, config.k,
            previous_tickers=active_incumbent, fee_bps=config.fee_bps,
        )
        exact_bits, exact_score = exact_solve_vectorized(problem)
        exact_target = tuple(policy_tickers[i] for i in np.flatnonzero(exact_bits))
        row["exact_solver_seconds"] = exact_seconds
        row["qaoa_total_seed_seconds"] = qaoa_seconds
        row["logical_total_two_qubit_gate_count"] = int(
            row.get("logical_cost_two_qubit_gate_count", 0)
            + row.get("logical_mixer_two_qubit_gate_count", 0)
        )
        row["exact_target_tickers"] = list(exact_target)
        row["selected_target_tickers"] = list(target)
        row["exact_score_recomputed"] = float(exact_score)
        target_by_policy[policy_id] = target
        exact_target_by_policy[policy_id] = exact_target
        policy_run_rows[policy_id] = row
        architecture_rows.append(row)

    # Classical greedy solution on the same policy objective as the executed QAOA.
    selected_policy = POLICIES[executed_policy_id]
    selected_tickers = candidates[:selected_policy.n_qubits]
    selected_problem = _build_policy_problem(
        returns.loc[:, selected_tickers], selected_tickers, executed_policy_id,
        config.k, previous_tickers=active_incumbent, fee_bps=config.fee_bps,
    )
    greedy_bits, greedy_score = greedy_solve(selected_problem)
    greedy_target = tuple(selected_tickers[i] for i in np.flatnonzero(greedy_bits))
    exact_target = exact_target_by_policy[executed_policy_id]

    # Same AGQO historical account and same active book for every one-step action.
    agqo_history_targets = [tuple(row["target_tickers"]) for row in agqo_details]
    full_entries = [*historic_entries, TEST_ENTRY]
    full_exits = [*historic_exits, TEST_EXIT]
    full_liquidities = [*historic_liquidities, liquidity]
    terminal_liquidity = traded_value.loc[traded_value.index < TEST_EXIT].tail(20).mean().reindex(tickers)
    actions: list[tuple[str, str, tuple[str, ...]]] = [
        ("AGQO: Qwen + giám sát + QAOA", "agqo", target_by_policy[executed_policy_id]),
        ("Đối chứng quy tắc + QAOA", "rule", target_by_policy[rule_policy_id]),
        ("Nghiệm chính xác cổ điển, cùng hàm mục tiêu", "exact", exact_target),
        ("Tham lam cổ điển, cùng hàm mục tiêu", "greedy", greedy_target),
        ("Bình quân 6 mã thanh khoản cao", "equal_weight_liquid", tuple(candidates[:config.k])),
    ]
    for policy_id in policy_ids:
        if policy_id in (executed_policy_id, rule_policy_id):
            continue
        p = POLICIES[policy_id]
        actions.append((
            f"QAOA đối chứng {policy_id}", f"qaoa:{policy_id}", target_by_policy[policy_id]
        ))

    portfolio_rows: list[dict[str, Any]] = []
    daily_paths: dict[str, pd.Series] = {}
    for label, key, target in actions:
        trajectory = [*agqo_history_targets, target]
        daily, metrics = _mark_to_market_path(
            trajectory, historic_entries, historic_exits, historic_liquidities,
            TEST_ENTRY, TEST_EXIT, liquidity, terminal_liquidity, tickers, stock_open, qaoa_config,
        )
        portfolio_rows.append({"label": label, "key": key, "selected_tickers": list(target), "metrics": metrics})
        daily_paths[label] = daily

    benchmark_dates = dates[(dates >= TEST_ENTRY) & (dates <= TEST_EXIT)]
    benchmark_dates = pd.DatetimeIndex(benchmark_dates)
    for ticker, label in (("VN30", "VN30: giá chỉ số"), ("VNINDEX", "VNINDEX: giá chỉ số")):
        daily = _daily_index_returns(index_open, benchmark_dates, ticker)
        wealth = (1 + daily).cumprod()
        dd = wealth / np.maximum.accumulate(np.r_[1.0, wealth.to_numpy()])[-len(wealth):] - 1 if len(wealth) else np.array([])
        sharpe = float(daily.mean() / daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 and daily.std(ddof=1) > 0 else float("nan")
        metrics = {
            "starting_nav_vnd": config.capital_vnd,
            "ending_nav_after_modeled_terminal_sale_vnd": config.capital_vnd * (1 + float(wealth.iloc[-1] - 1)),
            "net_return_after_entry_rebalance_and_capacity_limited_terminal_sale": float(wealth.iloc[-1] - 1) if len(wealth) else 0.0,
            "annualized_daily_sharpe_diagnostic": sharpe,
            "annualized_daily_volatility_diagnostic": float(daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 else float("nan"),
            "max_drawdown_diagnostic": float(np.min(dd)) if len(dd) else 0.0,
            "daily_observations": int(len(daily)),
            "executed_two_way_turnover_in_test": 0.0,
            "modeled_transaction_cost_vnd_in_test": 0.0,
            "capacity_unfilled_fraction_in_test": 0.0,
            "capacity_unfilled_notional_vnd_at_open_marks": 0.0,
        }
        portfolio_rows.append({"label": label, "key": ticker.lower(), "selected_tickers": [ticker], "metrics": metrics})
        daily_paths[label] = daily

    for row in architecture_rows:
        match = next((item for item in portfolio_rows if item["key"] == f"qaoa:{row['policy_id']}"), None)
        if row["policy_id"] == executed_policy_id:
            match = next(item for item in portfolio_rows if item["key"] == "agqo")
        elif row["policy_id"] == rule_policy_id:
            match = next(item for item in portfolio_rows if item["key"] == "rule")
        row["financial_net_return"] = None if match is None else match["metrics"]["net_return_after_entry_rebalance_and_capacity_limited_terminal_sale"]

    if validated is not None:
        llm["supported_insight_codes"] = insight_codes
        llm["insight_repairs"] = insight_repairs
        llm["risk_flags"] = risk_flags
        llm["grounded_narrative"] = rationale
        llm["risk_note"] = risk_note

    market_summary = {
        "p_high_volatility": probability,
        "vn30_vol_20d": float(features.loc[SIGNAL_DATE, "vol_20"]),
        "vn30_vol_60d": float(features.loc[SIGNAL_DATE, "vol_60"]),
        "vn30_return_20d": float(features.loc[SIGNAL_DATE, "return_20"]),
        "vn30_return_60d": float(features.loc[SIGNAL_DATE, "return_60"]),
        "volatility_ratio_20d_to_120d": float(features.loc[SIGNAL_DATE, "vol_ratio_20_120"]),
        "mean_pairwise_correlation": float(returns.loc[:, eligible].corr().to_numpy()[np.triu_indices(len(eligible), 1)].mean()),
        "cross_sectional_20d_return_dispersion": float(payload["market"]["cross_sectional_20d_return_dispersion"]),
        "candidate_count": len(candidates),
        "eligible_count": len(eligible),
        "k": config.k,
        "candidates": list(candidates),
        "active_incumbent_tickers": list(active_incumbent),
        "candidate_group_counts": members.set_index("ticker").reindex(candidates)["group"].value_counts().to_dict(),
    }
    result = {
        "title": "AGQO fresh-inference tail probe",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dates": {"signal": str(SIGNAL_DATE.date()), "entry": str(TEST_ENTRY.date()), "exit": str(TEST_EXIT.date()), "market_sessions_after_entry": test_market_sessions, "open_dates_inclusive": test_open_dates_inclusive},
        "test_design": {
            "classification": "new-tail diagnostic; data window previously visible in project analyses; not a blind holdout",
            "information_cutoff": str(SIGNAL_DATE.date()),
            "market_outcome_window": [str(TEST_ENTRY.date()), str(TEST_EXIT.date())],
            "data_last_date": str(dates[-1].date()),
            "decision_payload_excludes_post_signal_outcomes": True,
            "fresh_llm_call_cache_bypassed": True,
            "portfolio_paths_share_same_historical_agqo_book": True,
            "historical_performance_used_in_llm_prompt_matured_periods": completed_count,
            "active_incumbent_used_for_objective_cost_state": list(active_incumbent),
        },
        "data": old["data"],
        "parameters": {
            "capital_vnd": config.capital_vnd,
            "fee_bps_per_side": config.fee_bps,
            "adtv_participation": config.adtv_participation,
            "k": config.k,
            "qaoa_seeds": list(seeds),
            "qaoa_shots_per_seed": 1024,
            "qaoa_max_evaluations_per_seed": 100,
            "policies_run": policy_ids,
            "model_threshold_annualized_volatility": model.threshold,
            "model_C": model.chosen_c,
        },
        "as_of_market": market_summary,
        "history_used_for_decision": {
            "source_result_file": str(OLD_RESULT.relative_to(ROOT)),
            "source_result_sha256": hashlib.sha256(OLD_RESULT.read_bytes()).hexdigest(),
            "completed_strategy_metrics": past_strategy_metrics,
            "rule_policy_id": rule_policy_id,
            "matured_qaoa_evidence_summary": _summarize_qaoa_rows(qaoa_rows),
        },
        "prompt_payload": payload,
        "llm": llm,
        "decision": {
            "proposed_policy_id": proposed_policy_id,
            "executed_policy_id": executed_policy_id,
            "rule_policy_id": rule_policy_id,
            "active_incumbent_tickers": list(active_incumbent),
            "guardrail_reason": guardrail_reason,
            "guardrail_evidence": guardrail_evidence,
            "validated_decision": validated,
        },
        "qaoa_architecture_test": architecture_rows,
        "financial_test": {
            "interpretation": f"{test_market_sessions}-session one-step test; net portfolio uses simulated partial fills, modeled fees and capacity-limited terminal sales; index price benchmarks exclude investability costs.",
            "daily_path_dates": [str(d.date()) for d in benchmark_dates],
            "portfolios": portfolio_rows,
            "daily_returns": {label: {str(d.date()): float(v) for d, v in series.items()} for label, series in daily_paths.items()},
        },
        "limitations": [
            f"Only one LLM decision and {test_market_sessions} market sessions; annualized Sharpe is descriptive and unstable.",
            "This data tail was not scored in the old portfolio table but the market dates were already present in project artifacts; it is not a blind holdout.",
            "Point-in-time membership is used from the documented VN30 review timeline; reviewed intervals should still be audited against HOSE source records.",
            "VCI price adjustment is used for returns, but each cash dividend, split, bonus issue and rights event has not been independently reconciled; tax, lot size, impact and halted-stock execution are not modeled.",
            "Raw close×volume remains a liquidity proxy and does not replace confirmed traded value or order-book capacity.",
            "QAOA runs on a classical simulator; gate counts are logical circuit proxies and cannot establish quantum advantage.",
            "No external news feed was used in this probe; price moves are not attributed to specific events.",
            "The monthly historical portfolio entries/exits in source results remain based on the existing backtest assumptions.",
        ],
        "runtime_seconds": None,
    }
    figures = _make_figures(portfolio_rows, architecture_rows, daily_paths)
    result["figures"] = [str(path.relative_to(ROOT / "results/final")) for path in figures]
    result["runtime_seconds"] = float(perf_counter() - started)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    _write_report(result)
    print(f"LLM: {llm['status']} | proposed={proposed_policy_id} | executed={executed_policy_id} | rule={rule_policy_id}")
    print(f"Window: {TEST_ENTRY.date()} → {TEST_EXIT.date()} ({test_market_sessions} sessions); signal={SIGNAL_DATE.date()}")
    for row in portfolio_rows:
        print(f"{row['label']}: net={row['metrics']['net_return_after_entry_rebalance_and_capacity_limited_terminal_sale']:.3%}, Sharpe*={row['metrics']['annualized_daily_sharpe_diagnostic']:.3f}, DD*={row['metrics']['max_drawdown_diagnostic']:.3%}")
    print(f"Saved {OUT_JSON}")
    print(f"Saved {OUT_REPORT}")
    print(f"Runtime {result['runtime_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
