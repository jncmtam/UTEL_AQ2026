"""Figures and the auto-generated results page (docs/RESULTS.md).

Phase 1 (data insight) figures come first, then phase 2 (insight -> circuit), then the tests.

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
ARM_COLOR = {"warm_start_only": SERIES[7], "textbook": SERIES[1], "random": SERIES[3],
             "designed": SERIES[0], "designed_refined": SERIES[6]}
ARM_LABEL = {"warm_start_only": "Warm start only (no quantum layers)", "textbook": "Textbook QAOA",
             "random": "Random search (3 seeds)", "designed": "Insight-designed (transferred)",
             "designed_refined": "Insight-designed + COBYLA polish"}
SHORT_LABEL = {"warm_start_only": "Warm start\nonly", "textbook": "Textbook\nQAOA", "random": "Random\nsearch x3",
               "designed": "Insight-\ndesigned", "designed_refined": "Insight-designed\n+ polish"}
ARM_ORDER = ["warm_start_only", "textbook", "random", "designed", "designed_refined"]
STRAT_COLOR = {
    "QP + nearest-lot rounding (practitioner)": SERIES[7],
    "Equal weight 1/N, whole lots": SERIES[5],
    "QP + exact lot rounding (classical reference)": SERIES[2],
    "QP + textbook QAOA": SERIES[1],
    "AGQO: QP + insight-designed QAOA": SERIES[0],
    "ETF buy-and-hold: E1VFVN30": SERIES[3],
    "ETF buy-and-hold: FUESSV30": SERIES[4],
    "ETF buy-and-hold: FUEKIV30": SERIES[6],
}
AGQO = "AGQO: QP + insight-designed QAOA"


plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12.5, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left", "legend.frameon": False,
    "legend.labelcolor": INK2, "lines.linewidth": 2.0,
})


def _md(df: pd.DataFrame) -> str:
    """Markdown table without the optional `tabulate` dependency."""
    cols = [str(c) for c in df.columns]
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for i, r in df.iterrows():
        out.append(f"| {i} | " + " | ".join("" if pd.isna(v) else (f"{v:,.3f}" if isinstance(v, float) else str(v))
                                            for v in r.values) + " |")
    return "\n".join(out)


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
           hatch="///", linewidth=0, label="member with < 180 days of history")
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
    px = md.px.loc[last, md.members(last)].dropna()
    pct = (px * 100 / capital * 100).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(pct.index, pct.values, color=SERIES[0], height=0.6)
    for i, v in enumerate(pct.values):
        ax.text(v + 0.05, i, f"{v:.1f}%", va="center", color=INK2, fontsize=8)
    ax.set_xlabel(f"one board lot (100 shares) as % of a {capital / 1e6:.0f}M VND account")
    _title(ax, f"Whole lots make small-account weights discrete: one lot costs {pct.min():.1f}–{pct.max():.1f}% of NAV",
           f"Prices on {last.date()}. Rounding a continuous optimiser's weights to lots is exactly where small accounts lose tracking quality.")
    return _save(fig, out / "02_lot_granularity.png")


def _pool_random(q: pd.DataFrame) -> pd.DataFrame:
    q = q.copy()
    q["arm"] = q.arm.where(~q.arm.str.startswith("random_s"), "random")
    return q.groupby(["date", "arm"], as_index=False).mean(numeric_only=True)


def _insight(run: Path) -> pd.DataFrame:
    rows = []
    for r in json.loads((run / "insight.json").read_text()):
        h = r.pop("hamiltonian")
        rows.append({k: v for k, v in r.items() if not isinstance(v, (list, dict))} | {"n_clusters": len(r["clusters"])}
                    | {f"h_{k}": v for k, v in h.items() if not isinstance(v, list)})
    return pd.DataFrame(rows)


def fig_market_structure(run: Path, out: Path) -> str:
    d = _insight(run)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    x = np.arange(len(d))
    a1.plot(x, d.avg_correlation, color=SERIES[0], marker="o", label="average pairwise correlation")
    a1.plot(x, d.market_factor_share, color=SERIES[1], marker="o", label="market-factor share of variance")
    a1.set_ylim(0, max(0.8, d.market_factor_share.max() * 1.15))
    a1.legend(loc="lower left", fontsize=8)
    a1.set_xticks(x, [t[:7] for t in d.date], rotation=60, ha="right", fontsize=8)
    a2.bar(x, d.effective_bets, color=SERIES[2], width=0.6, label="effective independent bets (Meucci)")
    a2.plot(x, d.n_clusters, color=INK2, marker="D", linewidth=0, label="correlation clusters (rho >= 0.5)")
    a2.legend(loc="upper left", fontsize=8)
    a2.set_xticks(x, [t[:7] for t in d.date], rotation=60, ha="right", fontsize=8)
    _title(a1, f"Phase 1 insight: VN30 behaves like ~{d.effective_bets.median():.0f} independent bets, not 30 — one market "
               f"factor explains {100 * d.market_factor_share.median():.0f}% of daily variance",
           "Point-in-time members at each rebalance, 250 trading days before the date. Few effective bets is why a whole-lot "
           "portfolio of fewer stocks can still track the index, and why stocks' lot decisions are coupled.")
    return _save(fig, out / "03_market_structure.png")


def fig_problem_structure(run: Path, out: Path) -> str:
    d = _insight(run)
    cards = pd.DataFrame(json.loads((run / "design_cards.json").read_text()))
    kept = cards.R3_couplings.apply(lambda c: c["kept"])
    total = cards.R3_couplings.apply(lambda c: c["of"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    x = np.arange(len(d))
    a1.bar(x, 100 * d.h_coupling_mass_from_risk, color=SERIES[0], width=0.6, label="from stocks moving together")
    a1.bar(x, 100 * d.h_coupling_mass_from_budget, bottom=100 * d.h_coupling_mass_from_risk, color=SERIES[3],
           width=0.6, label="from the cash budget")
    a1.set_ylabel("share of coupling strength sum J² (%)")
    a1.set_ylim(0, 105)
    a1.legend(loc="lower left", fontsize=8)
    a1.set_xticks(x, [t[:7] for t in d.date], rotation=60, ha="right", fontsize=8)
    a2.bar(x, total, color=GRID, width=0.6, label="all couplings")
    a2.bar(x, kept, color=SERIES[0], width=0.6, label="kept (90% of strength)")
    a2.plot(x, 100 * d.h_warm_confidence, color=SERIES[1], marker="o", label="warm-start confidence (%)")
    a2.legend(loc="upper right", fontsize=8)
    a2.set_xticks(x, [t[:7] for t in d.date], rotation=60, ha="right", fontsize=8)
    _title(a1, f"From data to circuit: {100 * d.h_coupling_mass_from_risk.median():.0f}% of the qubit couplings come from "
               f"co-movement, and {100 * (kept / total).median():.0f}% of the couplings carry 90% of it",
           "Left: where the Ising couplings of the 16-qubit lot problem come from. Right: couplings kept by rule R3 (halving CX "
           "gates) and how decided the classical relaxation already is (rule R1 warm start).")
    return _save(fig, out / "04_problem_structure.png")


def fig_calibration(run: Path, out: Path) -> str:
    g = pd.read_csv(run / "design_calibration.csv")
    spec = json.loads((run / "specs.json").read_text())["designed"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1, 1.3]})
    byp = g.groupby("layers").train_success.max() * 100
    a1.plot(byp.index, byp.values, color=SERIES[0], marker="o")
    a1.set_xlabel("layers p")
    a1.set_ylabel("best training success (%)")
    sub = g[(g.layers == spec["layers"]) & (np.isclose(g.epsilon, spec["warm_start_epsilon"]))]
    piv = sub.pivot(index="dbeta", columns="dgamma", values="train_success") * 100
    im = a2.imshow(piv.values, origin="lower", aspect="auto", cmap="Blues")
    a2.set_xticks(range(piv.shape[1]), piv.columns)
    a2.set_yticks(range(piv.shape[0]), piv.index)
    a2.set_xlabel("ramp height d_gamma (RMS-normalised H)")
    a2.set_ylabel("ramp height d_beta")
    fig.colorbar(im, ax=a2, label="training success (%)")
    _title(a1, f"Calibration on 2023 only: a linear-ramp schedule with p={spec['layers']}, d_gamma={spec['ramp_dt']}, "
               f"d_beta={spec['ramp_dbeta']} is frozen for every later quarter",
           f"{len(g)} schedules, each scored on the 4 training quarters with no per-quarter optimiser. Right: the landscape at "
           f"the chosen p and eps={spec['warm_start_epsilon']}; a broad plateau means the schedule transfers.")
    return _save(fig, out / "05_calibration.png")


def fig_test(run: Path, out: Path) -> str:
    q = _pool_random(pd.read_csv(run / "quantum_test.csv"))
    arms = [a for a in ARM_ORDER if a in set(q.arm)]
    uni = q.groupby("date").uniform_success.first()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.6))
    means = {}
    for i, arm in enumerate(arms):
        d = q[q.arm == arm]
        jit = np.linspace(-0.18, 0.18, len(d))
        a1.scatter(i + jit, d.success_prob * 100, color=ARM_COLOR[arm], s=26, edgecolor=SURFACE, zorder=3)
        means[arm] = d.success_prob.mean() * 100
        a1.hlines(means[arm], i - 0.3, i + 0.3, color=INK, linewidth=2)
        a1.text(i, means[arm] * 1.35, f"{means[arm]:.2f}%", ha="center", color=INK2, fontsize=8)
        a2.bar(i, 100 * d.better_than_rounding.mean(), color=ARM_COLOR[arm], width=0.6)
        a2.text(i, 100 * d.better_than_rounding.mean() + 1, f"{100 * d.better_than_rounding.mean():.0f}%", ha="center",
                color=INK2, fontsize=8)
    a1.axhline(uni.mean() * 100, color=MUTED, linestyle=":", linewidth=1.5)
    a1.set_yscale("log")
    a1.set_ylabel("near-optimal success per shot (%, log)")
    a2.set_ylabel("P(shot beats practitioner rounding) (%)")
    for a in (a1, a2):
        a.set_xticks(range(len(arms)), [ARM_LABEL[x].replace(" (", "\n(") for x in arms], fontsize=7.5)
    w, dz = means.get("warm_start_only", np.nan), means.get("designed", np.nan)
    _title(a1, f"Unseen quarters: the insight-designed circuit is {dz / w:.1f}× the classical warm start it starts from and "
               f"{dz / (uni.mean() * 100):.0f}× random guessing",
           f"{q.date.nunique()} quarters after 2023, schedules frozen on 2023. Left: P(one shot is affordable and within 5% of the "
           "exact optimum); dotted = random guessing. Right: P(one shot is affordable and better than nearest-lot rounding).")
    return _save(fig, out / "06_test_success.png")


def fig_rounding(run: Path, out: Path) -> str:
    q = pd.read_csv(run / "quantum_test.csv")
    q = _pool_random(q)
    arm = "designed"
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
    return _save(fig, out / "07_rounding_quality.png")


def fig_backtest(run: Path, out: Path) -> str:
    p = pd.read_csv(run / "strategy_performance.csv", index_col=0)
    p = p.sort_values("tracking_error_ann_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(p) + 1.8))
    y = np.arange(len(p))
    ax.barh(y, p.tracking_error_ann_pct, color=[STRAT_COLOR.get(s, SERIES[0]) for s in p.index], height=0.6)
    for i, (s, r) in enumerate(p.iterrows()):
        ax.text(r.tracking_error_ann_pct + 0.05, i,
                f"TE {r.tracking_error_ann_pct:.2f}%   vs ETF {r.excess_return_vs_etf_ann_pct:+.2f}%/yr   fees {r.fees_vnd / 1e6:.2f}M",
                va="center", color=INK2, fontsize=8.5)
    ax.set_yticks(y, p.index)
    ax.set_xlabel("annualised realised tracking error vs VN30 (%) — lower is better")
    ax.set_xlim(0, p.tracking_error_ann_pct.max() * 1.75)
    best = p.tracking_error_ann_pct.idxmin()
    _title(ax, f"Walk-forward 2023–2026: best VN30 tracker is “{best}” ({p.loc[best, 'tracking_error_ann_pct']:.2f}% TE)",
           "100M VND account, quarterly rebalance, whole lots, 0.15% commission + 0.1% sell tax; each strategy runs its own account. "
           "'vs ETF' = annualised return minus E1VFVN30 buy-and-hold (both include dividends).")
    return _save(fig, out / "08_backtest_tracking_error.png")


def fig_active(run: Path, out: Path) -> str:
    v = pd.read_csv(run / "daily_values.csv", index_col=0, parse_dates=True)
    idx = v.pop("VN30 index (scaled)")
    keep = [s for s in ["QP + nearest-lot rounding (practitioner)", "Equal weight 1/N, whole lots",
                        "QP + exact lot rounding (classical reference)", AGQO, "ETF buy-and-hold: FUESSV30",
                        "ETF buy-and-hold: FUEKIV30"] if s in v]
    etf = v["ETF buy-and-hold: E1VFVN30"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for s in keep:
        rel = (v[s] / v[s].iloc[0]) / (etf / etf.iloc[0]) * 100 - 100
        ax.plot(rel.index, rel.values, color=STRAT_COLOR[s], label=s, linewidth=1.8)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylabel("cumulative return relative to E1VFVN30 (%)")
    ax.legend(loc="best", fontsize=8.5)
    _title(ax, "Against the ETF a retail investor could buy instead: cumulative return relative to E1VFVN30 buy-and-hold",
           "Account value ÷ E1VFVN30 buy-and-hold account, rebased to the first rebalance (Jan 2023). Fees, taxes and dividends included.")
    return _save(fig, out / "09_relative_to_etf.png")


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
    last = rb[rb.strategy == AGQO].iloc[-1]
    _title(ax, f"Latest decision ({last.date}): {int((t.target_shares > 0).sum())} stocks in whole lots, {tot:.1f}M VND "
               f"invested of a {last.nav_pre / 1e6:.1f}M VND account (100M in Jan 2023)",
           "AGQO account: best affordable sample of the insight-designed circuit for the latest quarter; the circuit is exported as OpenQASM.")
    return _save(fig, out / "10_latest_decision.png")


# ------------------------------------------------------------------ results page
def build_report(runs: list[Path], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    run = runs[-1]
    cfg = json.loads((run / "config.json").read_text())
    man = json.loads((run / "run_manifest.json").read_text())
    figs = [fig_coverage(run, out), fig_lots(run, out, cfg["problem"]["capital_vnd"]), fig_market_structure(run, out),
            fig_problem_structure(run, out), fig_calibration(run, out), fig_test(run, out), fig_rounding(run, out),
            fig_backtest(run, out), fig_active(run, out), fig_latest(run, out)]
    perf = pd.read_csv(run / "strategy_performance.csv", index_col=0)
    q = _pool_random(pd.read_csv(run / "quantum_test.csv"))
    specs = json.loads((run / "specs.json").read_text())
    qt = q.groupby("arm").agg(success_pct=("success_prob", lambda s: 100 * s.mean()),
                              beats_rounding_pct=("better_than_rounding", lambda s: 100 * s.mean()),
                              hit_in_512_shots_pct=("p_hit_in_shots", lambda s: 100 * s.mean()),
                              feasible_mass_pct=("feasible_mass", lambda s: 100 * s.mean()),
                              best_sample_gap=("best_sample_gap", "median"),
                              optimiser_calls=("evaluations", "mean"),
                              cx=("two_qubit_gates", "mean")).reindex([a for a in ARM_ORDER if a in set(q.arm)])
    qt.index = [ARM_LABEL[a] for a in qt.index]
    uni = 100 * q.groupby("date").uniform_success.first().mean()
    sa = q.groupby("date").sa_gap.first()
    d = specs["designed"]
    rel = Path("figures")
    f = lambda i: f"![{figs[i][:-4]}]({rel / figs[i]})"
    lines = [
        "# Results", "",
        f"_Auto-generated by `python -m agqo report` from `{run}` (run time {man['run_seconds']:.0f}s; training quarters "
        f"{man['train_dates'][0]}..{man['train_dates'][-1]}; budget penalty λ = {man['budget_penalty']} calibrated on them)._", "",
        "## 1. Data", f(0), "", f(1), "",
        "## 2. Phase 1 — value extracted from the data", f(2), "", f(3), "",
        "## 3. Phase 2 — insight-driven circuit and optimiser", "",
        "| rule | circuit element | data input | reference |", "|---|---|---|---|",
        "| R1 | warm-start initial state | continuous relaxation of the lot problem | Egger et al. 2021 |",
        "| R2 | aligned warm-start mixer | same relaxation | He et al. 2023 |",
        "| R3 | ZZ couplings kept | strongest pairs covering 90% of sum J² (co-movement + budget) | — |",
        "| R4 | energy scale | RMS of Ising coefficients | Sureshbabu et al. 2024 |",
        "| R5 | angle schedule | linear ramp, frozen after 2023 calibration | Montañez-Barrera & Michielsen 2025 |", "",
        f"Frozen design: p = {d['layers']}, ε = {d['warm_start_epsilon']}, Δγ = {d['ramp_dt']}, Δβ = {d['ramp_dbeta']}, "
        "no per-quarter optimiser (the polished variant adds COBYLA on CVaR, Barkoutsos et al. 2020).", "",
        f(4), "",
        "## 4. Quantum quality on unseen quarters", f(5), "",
        f"Random guessing succeeds {uni:.4f}% per shot. Simulated annealing reaches a median normalised gap of "
        f"{sa.median():.3f}; exact enumeration always finds the optimum. No quantum speed-up is claimed.", "",
        _md(qt), "", f(6), "",
        "## 5. Walk-forward financial backtest", f(7), "", f(8), "",
        _md(perf[["tracking_error_ann_pct", "active_return_ann_pct", "tracking_error_vs_etf_pct",
              "excess_return_vs_etf_ann_pct", "fees_vnd", "turnover_x", "avg_holdings", "avg_invested_pct"]]), "",
        "ETF tracking errors are inflated by daily market-price noise around NAV (E1VFVN30 daily-return correlation with "
        "VN30 ≈ 0.84; FUESSV30 and FUEKIV30 trade ~13k units a day); compare ETFs on total return, not daily TE.", "",
        "`active_return_ann_pct` is measured against the VN30 *price* index, so it includes dividends the index omits; "
        "the ETF columns compare like with like.", "",
        "## 6. Latest decision", f(9), ""]
    Path("docs").mkdir(exist_ok=True)
    (Path("docs") / "RESULTS.md").write_text("\n".join(lines))
    print("figures:", figs)
