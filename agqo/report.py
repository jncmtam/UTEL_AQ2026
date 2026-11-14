"""Figures and the auto-generated results page (docs/RESULTS.md).

Every figure title states the takeaway; the subtitle says exactly what is plotted.
Colors follow a fixed categorical order (validated palette); text stays in ink tones.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

INK, INK2, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#8a8984", "#fcfcfb", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ARM_COLOR = {"default": SERIES[1], "random": SERIES[3], "evolve": SERIES[2], "llm": SERIES[0]}
ARM_LABEL = {"default": "Default QAOA", "random": "Random search", "evolve": "Classical evolution",
             "llm": "LLM architect"}
STRAT_COLOR = {
    "QP + nearest-lot rounding": SERIES[7],
    "QP + exact lot rounding": SERIES[2],
    "QP + QAOA rounding (default circuit)": SERIES[1],
    "QP + QAOA rounding (evolved circuit)": SERIES[6],
    "LLM views + QP + exact rounding": SERIES[4],
    "AGQO: LLM views + QP + QAOA (LLM circuit)": SERIES[0],
    "Basket: liquidity top-8": SERIES[3],
    "Basket: greedy-TE top-8": SERIES[5],
    "Basket: LLM analyst top-8": SERIES[4],
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left", "legend.frameon": False,
    "legend.labelcolor": INK2, "lines.linewidth": 2.0,
})


def _title(ax, title: str, subtitle: str) -> None:
    """Figure-level, left-aligned headline (the takeaway) and a subtitle (what is plotted)."""
    import textwrap

    fig = ax.figure
    ax.set_axisbelow(True)
    t = textwrap.fill(title, 95)
    st = textwrap.fill(subtitle, 125)
    fig._agqo_title = (t, st)


def _save(fig, path: Path) -> str:
    t, st = getattr(fig, "_agqo_title", ("", ""))
    h = fig.get_size_inches()[1]
    lines = t.count("\n") + st.count("\n") + 2
    top = 1 - (0.30 + 0.19 * lines) / h
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.text(0.012, 1 - 0.12 / h, t, ha="left", va="top", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.012, 1 - (0.16 + 0.21 * (t.count("\n") + 1)) / h, st, ha="left", va="top", fontsize=9.5, color=INK2)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path.name


# ------------------------------------------------------------------ figures
def fig_coverage(run: Path, out: Path) -> str:
    c = pd.read_csv(run / "coverage.csv")
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(c))
    ax.bar(x, c.usable, color=SERIES[0], width=0.6, label="usable (≥180 days of history)")
    ax.bar(x, c.members - c.usable, bottom=c.usable, color=GRID, width=0.6, edgecolor=MUTED,
           hatch="///", linewidth=0, label="member without price file")
    ax.set_xticks(x, [d[:7] for d in c.date], rotation=45, ha="right")
    ax.set_ylim(0, 32)
    ax.set_ylabel("VN30 members")
    ax.legend(loc="lower right", ncol=2)
    _title(ax, f"Point-in-time universe: {c.usable.min()}–{c.usable.max()} of 30 VN30 members are usable each quarter",
           "Membership as published by HOSE at each rebalance date; excluded names are listed in coverage.csv, never hidden.")
    return _save(fig, out / "01_universe_coverage.png")


def fig_lots(run: Path, out: Path, capital: float) -> str:
    from .data import MarketData

    md = MarketData.load()
    last = md.close.index[-1]
    px = md.close.loc[last].dropna()
    pct = (px * 100 / capital * 100).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(pct.index, pct.values, color=SERIES[0], height=0.6)
    for i, v in enumerate(pct.values):
        ax.text(v + 0.05, i, f"{v:.1f}%", va="center", color=INK2, fontsize=8)
    ax.set_xlabel(f"one board lot (100 shares) as % of a {capital / 1e6:.0f}M VND account")
    _title(ax, f"Whole lots make small-account weights discrete: one lot costs {pct.min():.1f}–{pct.max():.1f}% of NAV",
           f"Prices on {last.date()}. Rounding a continuous optimiser's weights to lots is exactly where small accounts lose tracking quality.")
    return _save(fig, out / "02_lot_granularity.png")


def fig_search(run: Path, out: Path) -> str:
    h = pd.read_csv(run / "circuit_search.csv")
    fig, ax = plt.subplots(figsize=(10, 4.6))
    finals = {}
    for arm in ["default", "random", "evolve", "llm"]:
        d = h[h.arm == arm].sort_values("order")
        if d.empty:
            continue
        y = np.maximum.accumulate(d.fitness.to_numpy()) * 100
        x = np.arange(1, len(y) + 1)
        if arm == "default":
            ax.axhline(y[0], color=ARM_COLOR[arm], linestyle="--", linewidth=1.5)
            ax.text(1, y[0], f" {ARM_LABEL[arm]} {y[0]:.2f}%", color=INK2, va="bottom", fontsize=9)
        else:
            ax.step(x, y, where="post", color=ARM_COLOR[arm], label=ARM_LABEL[arm])
            ax.text(x[-1] + 0.3, y[-1], f"{ARM_LABEL[arm]} {y[-1]:.2f}%", color=INK2, va="center", fontsize=9)
        finals[arm] = y[-1]
    ax.set_xlabel("circuit designs evaluated (same budget for every arm)")
    ax.set_ylabel("best success probability (%)")
    ax.set_xlim(0.5, h.groupby("arm").size().max() + 7)
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.45))
    lead = max((a for a in finals if a != "default"), key=finals.get)
    _title(ax, f"Circuit design search: {ARM_LABEL[lead]} reaches {finals[lead]:.2f}% vs {finals['default']:.2f}% for textbook QAOA",
           "Success = probability one measurement returns an affordable lot-rounding decision within 5% (normalised) of the exact optimum; mean of 4 training quarters (2023).")
    return _save(fig, out / "03_circuit_search.png")


def fig_resources(run: Path, out: Path) -> str:
    h = pd.read_csv(run / "circuit_search.csv")
    h = h[h.errors == "[]"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for arm in ["random", "evolve", "llm", "default"]:
        d = h[h.arm == arm]
        if d.empty:
            continue
        ax.scatter(d.m_two_qubit_gates, d.fitness * 100, s=46 if arm != "default" else 90,
                   color=ARM_COLOR[arm], edgecolor=SURFACE, linewidth=1.5, label=ARM_LABEL[arm],
                   marker="D" if arm == "default" else "o", zorder=3)
    ax.set_xlabel("two-qubit (CX) gates per circuit")
    ax.set_ylabel("training success probability (%)")
    ax.legend(loc="upper right")
    _title(ax, "Better circuits are not bigger circuits: success depends on initial state and mixer, not CX count",
           "Every admitted design from the search. Aligned warm-start designs (warm_start + warm_x) dominate, as He et al. (2023) "
           "predict; rejected designs are logged in circuit_search.csv.")
    return _save(fig, out / "04_design_resources.png")


def fig_test(run: Path, out: Path) -> str:
    q = pd.read_csv(run / "quantum_test.csv")
    arms = [a for a in ["default", "random", "evolve", "llm"] if a in set(q.arm)]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    uni = q.groupby("date").uniform_success.first()
    means = {}
    for i, arm in enumerate(arms):
        d = q[q.arm == arm]
        jitter = np.linspace(-0.18, 0.18, len(d))
        ax.scatter(i + jitter, d.success_prob * 100, color=ARM_COLOR[arm], s=30, edgecolor=SURFACE, zorder=3)
        m = d.success_prob.mean() * 100
        means[arm] = m
        ax.hlines(m, i - 0.3, i + 0.3, color=INK, linewidth=2)
        ax.text(i + 0.33, m, f"mean {m:.2f}%\n{m / (uni.mean() * 100):.0f}× random", color=INK2, va="center", fontsize=8.5)
    ax.axhline(uni.mean() * 100, color=MUTED, linestyle=":", linewidth=1.5)
    ax.text(len(arms) - 0.5, uni.mean() * 100, "random guessing", color=MUTED, va="bottom", ha="right", fontsize=8.5)
    ax.set_yscale("log")
    ax.set_xticks(range(len(arms)), [ARM_LABEL[a] for a in arms])
    ax.set_ylabel("success probability per shot (%, log)")
    lead = max(means, key=means.get)
    _title(ax, f"Frozen designs on {q.date.nunique()} unseen quarters: the {ARM_LABEL[lead].lower()} design samples "
               f"near-optimal lot decisions {means[lead] / (uni.mean() * 100):.0f}× more often than random guessing",
           "Designs were chosen on 2023 data only and re-used without any new search or LLM call. Dots = quarters, bar = mean.")
    return _save(fig, out / "05_test_success.png")


def fig_rounding(run: Path, out: Path) -> str:
    q = pd.read_csv(run / "quantum_test.csv")
    arm = q.groupby("arm").success_prob.mean().idxmax()
    d = q[q.arm == arm].set_index("date")
    cap = 2.0
    series = [("nearest-lot rounding", d.nearest_rounding_gap, SERIES[7]),
              (f"QAOA best of 512 shots ({ARM_LABEL[arm]})", d.best_sample_gap, ARM_COLOR[arm]),
              ("simulated annealing", d.sa_gap, SERIES[3])]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(len(d))
    wbar = 0.26
    for i, (lab, v, col) in enumerate(series):
        vv = v.replace(np.inf, np.nan)
        ax.bar(x + (i - 1) * wbar, np.minimum(vv.fillna(cap), cap), width=wbar - 0.03, color=col, label=lab,
               hatch=["///" if np.isinf(t) else "" for t in v], edgecolor=SURFACE)
    ax.set_xticks(x, [t[:7] for t in d.index], rotation=45, ha="right")
    ax.set_ylabel("normalised gap to exact optimum (0 = optimal)")
    ax.set_ylim(0, cap * 1.05)
    ax.legend(loc="upper left", fontsize=8.5)
    hit_q = int((d.best_sample_gap <= 0.05).sum())
    hit_n = int((d.nearest_rounding_gap <= 0.05).sum())
    dte = (d.te_nearest_pct - d.te_exact_pct).replace(np.inf, np.nan).mean() * 100
    _title(ax, f"Plain rounding leaves value on the table: QAOA is within 5% of optimal in {hit_q}/{len(d)} unseen "
               f"quarters, nearest-lot rounding in {hit_n}/{len(d)}",
           f"Gap 1 = a typical random affordable portfolio; hatched = over budget (unaffordable). Ex-ante, exact rounding "
           f"lowers tracking error by {dte:.0f} bp on average vs nearest rounding.")
    return _save(fig, out / "05b_rounding_quality.png")


def fig_backtest(run: Path, out: Path) -> str:
    p = pd.read_csv(run / "strategy_performance.csv", index_col=0)
    p = p.sort_values("tracking_error_ann_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(p) + 1.8))
    y = np.arange(len(p))
    ax.barh(y, p.tracking_error_ann_pct, color=[STRAT_COLOR.get(s, SERIES[0]) for s in p.index], height=0.6)
    for i, (s, r) in enumerate(p.iterrows()):
        ax.text(r.tracking_error_ann_pct + 0.05, i,
                f"TE {r.tracking_error_ann_pct:.2f}%   active {r.active_return_ann_pct:+.2f}%/yr   fees {r.fees_vnd / 1e6:.2f}M",
                va="center", color=INK2, fontsize=8.5)
    ax.set_yticks(y, p.index)
    ax.set_xlabel("annualised realised tracking error vs VN30 (%) — lower is better")
    ax.set_xlim(0, p.tracking_error_ann_pct.max() * 1.75)
    best = p.tracking_error_ann_pct.idxmin()
    _title(ax, f"Out-of-sample 2023–2026: best tracker is “{best}” ({p.loc[best, 'tracking_error_ann_pct']:.2f}% TE)",
           "100M VND account, quarterly rebalance, whole lots, 0.15% commission + 0.1% sell tax. Each strategy runs its own account.")
    return _save(fig, out / "06_backtest_tracking_error.png")


def fig_active(run: Path, out: Path) -> str:
    v = pd.read_csv(run / "daily_values.csv", index_col=0, parse_dates=True)
    idx = v.pop("VN30 index (scaled)")
    keep = [s for s in ["QP + nearest-lot rounding", "QP + exact lot rounding", "QP + QAOA rounding (evolved circuit)",
                        "AGQO: LLM views + QP + QAOA (LLM circuit)", "Basket: greedy-TE top-8"] if s in v]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for s in keep:
        rel = (v[s] / v[s].iloc[0]) / (idx / idx.iloc[0]) * 100 - 100
        ax.plot(rel.index, rel.values, color=STRAT_COLOR[s], label=s, linewidth=1.8)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylabel("cumulative return relative to VN30 (%)")
    ax.legend(loc="best", fontsize=8.5)
    _title(ax, "Relative performance stays close to the index: the portfolios track VN30 rather than bet against it",
           "Account value ÷ VN30 level, rebased to the first rebalance (Jan 2023). Fees and taxes included.")
    return _save(fig, out / "07_relative_performance.png")


def fig_latest(run: Path, out: Path) -> str:
    t = pd.read_csv(run / "latest_trades.csv")
    t = t[t.target_shares > 0].sort_values("target_value_vnd")
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(t) + 2.2))
    y = np.arange(len(t))
    ax.barh(y, t.target_value_vnd / 1e6, color=SERIES[0], height=0.6)
    for i, r in enumerate(t.itertuples()):
        lots = int(r.target_shares // 100)
        ax.text(r.target_value_vnd / 1e6 + 0.3, i, f"{lots} lot{'s' if lots != 1 else ''} @ {r.price_vnd:,.0f} VND",
                va="center", color=INK2, fontsize=8.5)
    ax.set_yticks(y, t.ticker)
    ax.set_xlabel("target position (million VND)")
    ax.set_xlim(0, t.target_value_vnd.max() / 1e6 * 1.45)
    tot = t.target_value_vnd.sum() / 1e6
    rb = pd.read_csv(run / "rebalances.csv")
    last = rb[rb.strategy == "QP + exact lot rounding"].iloc[-1]
    _title(ax, f"Latest decision ({last.date}): {int((t.target_shares > 0).sum())} stocks in whole lots, {tot:.1f}M VND "
               f"invested of a {last.nav_pre / 1e6:.1f}M VND account (100M in Jan 2023)",
           "Exact lot-rounding optimum for the latest quarter (reference account). The same 16-qubit problem is exported as OpenQASM.")
    return _save(fig, out / "08_latest_decision.png")


def fig_llm(run: Path, out: Path) -> str | None:
    dec = json.loads((run / "analyst_decisions.json").read_text())
    if not dec.get("llm"):
        return None
    rows = []
    for d, v in dec["llm"].items():
        g = set(dec["greedy"][d]["shortlist"])
        rows.append({"date": d, "overlap": len(g & set(v["shortlist"])),
                     "views": sum(1 for x in v["views"].values() if x[0] != 0)})
    r = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(r))
    ax.bar(x, r.overlap, color=SERIES[0], width=0.6, label="stocks shared with greedy-TE rule")
    ax.plot(x, r.views, color=SERIES[1], marker="o", markersize=6, label="non-zero LLM views")
    ax.set_xticks(x, [d[:7] for d in r.date], rotation=45, ha="right")
    ax.set_ylim(0, 9)
    ax.legend(loc="lower right", ncol=2)
    _title(ax, f"The LLM analyst agrees with the rule on {r.overlap.mean():.1f} of 8 basket stocks and issues "
               f"{r.views.mean():.1f} non-zero views per quarter",
           "Per quarter: overlap of the LLM's anonymised 8-stock basket with the greedy tracking-error rule, and its views.")
    return _save(fig, out / "09_llm_analyst.png")


# ------------------------------------------------------------------ results page
def build_report(runs: list[Path], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    run = next((r for r in runs if (r / "llm_log.jsonl").exists()), runs[-1])
    cfg = json.loads((run / "config.json").read_text())
    figs = [fig_coverage(run, out), fig_lots(run, out, cfg["problem"]["capital_vnd"]), fig_search(run, out),
            fig_resources(run, out), fig_test(run, out), fig_rounding(run, out), fig_backtest(run, out), fig_active(run, out),
            fig_latest(run, out)]
    llm_fig = fig_llm(run, out)
    perf = pd.read_csv(run / "strategy_performance.csv", index_col=0)
    q = pd.read_csv(run / "quantum_test.csv")
    best = json.loads((run / "best_specs.json").read_text())
    man = json.loads((run / "run_manifest.json").read_text())
    qt = q.groupby("arm").agg(success_pct=("success_prob", lambda s: 100 * s.mean()),
                              hit_in_512_shots_pct=("p_hit_in_shots", lambda s: 100 * s.mean()),
                              feasible_mass_pct=("feasible_mass", lambda s: 100 * s.mean()),
                              best_sample_gap=("best_sample_gap", "median"),
                              circuit_evaluations=("evaluations", "mean"),
                              cx=("two_qubit_gates", "first"))
    uni = 100 * q.groupby("date").uniform_success.first().mean()
    sa = q.groupby("date").sa_gap.first()
    rel = Path("figures")
    lines = [
        "# Results", "",
        f"_Auto-generated by `python -m agqo report` from `{run}` "
        f"(LLM backend: `{man['llm_backend']}`, model: `{man['llm_model']}`, run time {man['run_seconds']:.0f}s)._", "",
    ]
    if man["llm_backend"] in (None, "mock"):
        lines += ["> **No live LLM in this run.** LLM arms are absent (or mock). Run "
                  "`python -m agqo run --llm modal --out results/llm_coder30` then re-run the report.", ""]
    lines += [
        "## 1. Data", f"![coverage]({rel / figs[0]})", "", f"![lots]({rel / figs[1]})", "",
        "## 2. Circuit design (training quarters)", f"![search]({rel / figs[2]})", "", f"![resources]({rel / figs[3]})", "",
        "Best design found by each arm:", "", "| arm | layers | init | mixer | keep | optimizer | iters | CVaR α | train success |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, b in best.items():
        s, m = b["spec"], b["train_metrics"]
        lines.append(f"| {arm} | {s['layers']} | {s['initial_state']} | {s['mixer']} | {s['coupling_keep_fraction']:.2f} | "
                     f"{s['optimizer']} | {s['max_iter']} | {s['cvar_alpha']:.2f} | {100 * m.get('success_prob', 0):.2f}% |")
    lines += ["", "## 3. Quantum quality on unseen quarters", f"![test]({rel / figs[4]})", "",
              f"Random guessing succeeds with {uni:.4f}% per shot. Simulated annealing (25,600 spin flips) reaches a median "
              f"normalised gap of {sa.median():.3f}; the exact optimum is always known by enumeration.", "",
              qt.round(3).to_markdown(), "",
              f"![rounding]({rel / figs[5]})", "",
              "## 4. Financial out-of-sample backtest", f"![te]({rel / figs[6]})", "", f"![rel]({rel / figs[7]})", "",
              perf[["tracking_error_ann_pct", "active_return_ann_pct", "correlation", "fees_vnd", "turnover_x",
                    "avg_holdings", "avg_invested_pct"]].round(3).to_markdown(), "",
              "## 5. Latest decision", f"![latest]({rel / figs[8]})", ""]
    if llm_fig:
        lines += ["## 6. LLM market analyst", f"![llm]({rel / llm_fig})", ""]
    Path("docs").mkdir(exist_ok=True)
    (Path("docs") / "RESULTS.md").write_text("\n".join(lines))
    print("figures:", figs + ([llm_fig] if llm_fig else []))
