"""Figures and the auto-generated results page (docs/RESULTS.md).

Every figure title states the takeaway; the subtitle says exactly what is plotted. Colours follow
a fixed categorical order; text stays in ink tones.
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .experiment import AGQO, EQUAL, EXACT, PRACT, TEXTBOOK

INK, INK2, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#8a8984", "#fcfcfb", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ARMS = ["warm_start_only", "textbook", "random", "frozen", "agqo", "polish_ablation", "oracle"]
ARM_LABEL = {"warm_start_only": "Warm start\nonly (p=0)", "textbook": "Textbook\nQAOA", "random": "Random\nsearch x3",
             "frozen": "Frozen\nschedule", "agqo": "AGQO\n(AI-guided)", "polish_ablation": "Polish\nablation",
             "oracle": "Oracle\n(upper bound)"}
ARM_COLOR = {"warm_start_only": SERIES[7], "textbook": SERIES[1], "random": SERIES[3], "frozen": SERIES[6],
             "agqo": SERIES[0], "polish_ablation": SERIES[4], "oracle": MUTED}
STRAT_COLOR = {PRACT: SERIES[7], EQUAL: SERIES[5], EXACT: SERIES[2], TEXTBOOK: SERIES[1], AGQO: SERIES[0],
               "ETF E1VFVN30": SERIES[3], "ETF FUESSV30": SERIES[4], "ETF FUEKIV30": SERIES[6]}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "legend.frameon": False, "legend.labelcolor": INK2,
    "lines.linewidth": 2.0,
})


def _md(df: pd.DataFrame, fmt: str = "{:,.3f}") -> str:
    """Markdown table without the optional `tabulate` dependency."""
    cols = [str(c) for c in df.columns]
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for i, r in df.iterrows():
        out.append(f"| {i} | " + " | ".join("" if pd.isna(v) else (fmt.format(v) if isinstance(v, (float, np.floating))
                                                                    else str(v)) for v in r.values) + " |")
    return "\n".join(out)


def _save(fig, path: Path, title: str, subtitle: str) -> str:
    w, h = fig.get_size_inches()
    t, st = textwrap.fill(title, int(min(100, 8.2 * w))), textwrap.fill(subtitle, int(min(130, 11.5 * w)))
    lines = t.count("\n") + st.count("\n") + 2
    fig.tight_layout(rect=(0, 0, 1, 1 - (0.30 + 0.19 * lines) / h))
    fig.text(0.012, 1 - 0.12 / h, t, ha="left", va="top", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.012, 1 - (0.16 + 0.21 * (t.count("\n") + 1)) / h, st, ha="left", va="top", fontsize=9.5, color=INK2)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path.name


def _quarters(ax, labels):
    ax.set_xticks(range(len(labels)), [x[:7] for x in labels], rotation=60, ha="right", fontsize=8)


def _pool(q: pd.DataFrame) -> pd.DataFrame:
    q = q.copy()
    q["arm"] = q.arm.where(~q.arm.str.startswith("random_s"), "random")
    return q.groupby(["date", "arm"], as_index=False).mean(numeric_only=True)


def _insight(run: Path) -> pd.DataFrame:
    rows = []
    for r in json.loads((run / "insight.json").read_text()):
        h = r["hamiltonian"]
        rows.append({k: v for k, v in r.items() if not isinstance(v, (list, dict))} | {"n_clusters": len(r["clusters"])}
                    | {f"h_{k}": v for k, v in h.items() if not isinstance(v, list)}
                    | {f"s_{k}": v for k, v in r["chosen_schedule"].items()})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ data and phase 1
def fig_lots(run: Path, out: Path, capital: float) -> str:
    from .data import MarketData

    md = MarketData.load()
    last = md.close.index[-1]
    pct = (md.px.loc[last, md.members(last)] * 100 / capital * 100).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(pct.index, pct.values, color=SERIES[0], height=0.6)
    for i, v in enumerate(pct.values):
        ax.text(v + 0.05, i, f"{v:.1f}%", va="center", color=INK2, fontsize=8)
    ax.set_xlabel(f"one board lot (100 shares) as % of a {capital / 1e6:.0f}M VND account")
    return _save(fig, out / "01_lot_granularity.png",
                 f"Whole lots make a small account's weights discrete: one lot costs {pct.min():.1f}–{pct.max():.1f}% of NAV",
                 f"Current VN30 members, prices on {last.date()}. A continuous optimiser's weights cannot be bought as computed; "
                 "choosing which stocks get one more lot is the integer problem AGQO solves.")


def fig_market(run: Path, out: Path) -> str:
    d = _insight(run)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    x = np.arange(len(d))
    a1.plot(x, d.avg_correlation, color=SERIES[0], marker="o", label="average pairwise correlation")
    a1.plot(x, d.market_factor_share, color=SERIES[1], marker="o", label="market-factor share of variance")
    a1.set_ylim(0, 0.8)
    a1.legend(loc="lower left", fontsize=8)
    _quarters(a1, d.date)
    a2.bar(x, d.effective_bets, color=SERIES[2], width=0.6, label="effective independent bets (Meucci)")
    a2.plot(x, d.n_clusters, color=INK2, marker="D", linewidth=0, label="correlation clusters (rho >= 0.5)")
    a2.set_ylim(0, 1.3 * max(d.effective_bets.max(), d.n_clusters.max()))
    a2.legend(loc="upper left", fontsize=8, ncol=2)
    _quarters(a2, d.date)
    return _save(fig, out / "02_market_structure.png",
                 f"Phase 1 insight: VN30 behaves like ~{d.effective_bets.median():.0f} independent bets, not 30; one market "
                 f"factor explains {100 * d.market_factor_share.median():.0f}% of daily variance",
                 "Point-in-time members at each test quarter, 250 sessions before the date. Few effective bets is why whole-lot "
                 "portfolios can track the index, and why the stocks' lot decisions are coupled.")


def fig_problem(run: Path, out: Path) -> str:
    d = _insight(run)
    cards = pd.DataFrame(json.loads((run / "design_cards.json").read_text()))
    kept = cards.R3_couplings.apply(lambda c: c["kept"])
    total = cards.R3_couplings.apply(lambda c: c["of"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    x = np.arange(len(d))
    a1.bar(x, 100 * d.h_coupling_mass_from_risk, color=SERIES[0], width=0.6, label="stocks moving together")
    a1.bar(x, 100 * d.h_coupling_mass_from_budget, bottom=100 * d.h_coupling_mass_from_risk, color=SERIES[3],
           width=0.6, label="cash budget")
    a1.set_ylabel("share of coupling strength sum J² (%)")
    a1.set_ylim(0, 115)
    a1.legend(loc="upper left", fontsize=8, ncol=2)
    _quarters(a1, d.date)
    a2.bar(x, total, color=GRID, width=0.6, label="all couplings")
    a2.bar(x, kept, color=SERIES[0], width=0.6, label="kept in AGQO's circuit")
    a2.plot(x, 100 * d.h_warm_confidence, color=SERIES[1], marker="o", label="warm-start confidence (%)")
    a2.set_ylim(0, 1.3 * max(total.max(), 100))
    a2.legend(loc="upper left", fontsize=8, ncol=3)
    _quarters(a2, d.date)
    return _save(fig, out / "03_problem_structure.png",
                 f"From data to circuit: {100 * d.h_coupling_mass_from_risk.median():.0f}% of qubit coupling strength comes "
                 f"from co-movement; AGQO keeps a median {kept.median():.0f} of {total.iloc[0]} couplings",
                 "Left: where the Ising couplings of each quarter's 16-qubit lot problem come from. Right: couplings kept by "
                 "the chosen coupling mass (fewer CX gates) and how decided the classical relaxation already is.")


# ------------------------------------------------------------------ phase 2: AI guidance
def fig_guidance(run: Path, out: Path) -> str:
    cv = pd.read_csv(run / "schedule_cv.csv")
    d = _insight(run)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    cols = [SERIES[6] if k == 0 else SERIES[0] for k in cv.k]
    a1.bar(range(len(cv)), 100 * cv.cv_success, color=cols, width=0.6)
    for i, v in enumerate(cv.cv_success):
        a1.text(i, 100 * v + 0.2, f"{100 * v:.1f}%", ha="center", color=INK2, fontsize=8)
    a1.set_xticks(range(len(cv)), cv.label, fontsize=8)
    a1.set_ylabel("leave-one-month-out success per shot (%)")
    x = np.arange(len(d))
    a2.plot(x, d.s_layers, color=SERIES[0], marker="o", label="layers p")
    a2.plot(x, 10 * d.s_dgamma, color=SERIES[1], marker="s", label="10 x ramp height d_gamma")
    a2.plot(x, 10 * d.s_coupling_mass, color=SERIES[2], marker="^", label="10 x coupling mass kept")
    a2.set_ylim(0, 13.5)
    a2.legend(loc="lower right", fontsize=8)
    _quarters(a2, d.date)
    best = cv.sort_values("cv_success", ascending=False).iloc[0]
    return _save(fig, out / "04_ai_guidance.png",
                 f"Phase 2 guidance: the schedule model ({best.label}) reaches {100 * best.cv_success:.1f}% cross-validated "
                 f"success vs {100 * cv[cv.k == 0].cv_success.iloc[0]:.1f}% for one frozen schedule",
                 "Left: success on held-out 2023 months when the schedule is chosen from the k most similar training problems "
                 "(insight features); 'all' = one frozen schedule. Right: what the model chose for each test quarter.")


def fig_quantum(run: Path, out: Path) -> str:
    q = _pool(pd.read_csv(run / "quantum_test.csv"))
    st = json.loads((run / "quantum_stats.json").read_text())
    arms = [a for a in ARMS if a in set(q.arm)]
    uni = q.groupby("date").uniform_success.first()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8))
    for i, arm in enumerate(arms):
        d = q[q.arm == arm]
        a1.scatter(i + np.linspace(-0.18, 0.18, len(d)), 100 * d.success_prob, color=ARM_COLOR[arm], s=24,
                   edgecolor=SURFACE, zorder=3)
        m = 100 * d.success_prob.mean()
        a1.hlines(m, i - 0.3, i + 0.3, color=INK, linewidth=2)
        a1.text(i, m * 1.45, f"{m:.1f}%", ha="center", color=INK2, fontsize=8)
        b = 100 * d.better_than_rounding.mean()
        a2.bar(i, b, color=ARM_COLOR[arm], width=0.6)
        a2.text(i, b + 1, f"{b:.0f}%", ha="center", color=INK2, fontsize=8)
    a1.axhline(100 * uni.mean(), color=MUTED, linestyle=":", linewidth=1.5)
    a1.set_yscale("log")
    a1.set_ylabel("near-optimal success per shot (%, log)")
    a2.set_ylabel("P(shot beats practitioner rounding) (%)")
    for a in (a1, a2):
        a.set_xticks(range(len(arms)), [ARM_LABEL[x] for x in arms], fontsize=7.5)
    w, tb, rs = st["agqo vs warm_start_only"], st["agqo vs textbook"], st["agqo vs random"]
    return _save(fig, out / "05_quantum_test.png",
                 f"12 unseen quarters: AGQO's circuit samples near-optimal lot decisions {w['ratio']:.1f}x as often as its "
                 f"classical warm start, {tb['ratio']:.0f}x textbook QAOA and {rs['ratio']:.1f}x random search",
                 f"Wins / Wilcoxon p: vs warm start {w['wins']}/12, p={w['wilcoxon_p']:.4f}; vs textbook {tb['wins']}/12, "
                 f"p={tb['wilcoxon_p']:.4f}; vs random search {rs['wins']}/12, p={rs['wilcoxon_p']:.4f}. Dotted = random guessing. "
                 "Right: P(one shot is affordable and better than nearest-lot rounding). Oracle uses the test answer.")


def fig_rounding(run: Path, out: Path) -> str:
    q = _pool(pd.read_csv(run / "quantum_test.csv"))
    d = q[q.arm == "agqo"].set_index("date")
    cap = 2.0
    he = int((d.best_sample_gap <= 1e-9).sum())
    series = [("nearest-lot rounding", d.nearest_rounding_gap, SERIES[7]),
              (f"AGQO best of 512 shots (gap 0 in {he}/{len(d)}: bars invisible)", d.best_sample_gap, SERIES[0]),
              ("simulated annealing, one run", d.sa_gap, SERIES[3])]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    x = np.arange(len(d))
    for i, (lab, v, col) in enumerate(series):
        vv = v.replace(np.inf, np.nan)
        ax.bar(x + (i - 1) * 0.26, np.minimum(vv.fillna(cap), cap), width=0.23, color=col, label=lab,
               hatch=["///" if np.isinf(t) else "" for t in v], edgecolor=SURFACE)
    _quarters(ax, list(d.index))
    ax.set_ylabel("gap to optimum (0 = optimal)")
    ax.set_ylim(0, cap * 1.05)
    ax.legend(loc="upper left", fontsize=8.5)
    hq, hn = int((d.best_sample_gap <= 0.05).sum()), int((d.nearest_rounding_gap <= 0.05).sum())
    se, s5 = int((d.sa_gap <= 1e-9).sum()), int((d.sa_gap <= 0.05).sum())
    return _save(fig, out / "06_rounding_quality.png",
                 f"AGQO's best sample is within 5% of the exact optimum in {hq}/{len(d)} quarters; nearest-lot rounding in "
                 f"{hn}/{len(d)}",
                 f"Gap 1 = a typical affordable portfolio; hatched = over budget. AGQO's 512 shots contain the exact optimum in "
                 f"{he}/{len(d)} quarters; one short simulated-annealing run (25,600 flips) is exact in {se}/{len(d)} and within "
                 f"5% in {s5}/{len(d)}. Enumeration solves 16 qubits exactly in a fraction of a second: no quantum advantage.")


# ------------------------------------------------------------------ finance
def fig_backtest(run: Path, out: Path) -> str:
    p = pd.read_csv(run / "strategy_performance.csv", index_col=0)
    man = json.loads((run / "run_manifest.json").read_text())
    p = p.sort_values("tracking_error_weekly_ann_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(p) + 1.8))
    y = np.arange(len(p))
    ax.barh(y, p.tracking_error_weekly_ann_pct, color=[STRAT_COLOR.get(s, SERIES[0]) for s in p.index], height=0.6)
    for i, (s, r) in enumerate(p.iterrows()):
        ax.text(r.tracking_error_weekly_ann_pct + 0.05, i, f"weekly TE {r.tracking_error_weekly_ann_pct:.2f}%   return "
                f"{r.return_ann_pct:+.1f}%/yr   vs ETF {r.excess_return_vs_etf_ann_pct:+.2f}%/yr", va="center",
                color=INK2, fontsize=8.5)
    ax.set_yticks(y, p.index)
    ax.set_xlabel("annualised tracking error vs VN30 from weekly returns (%) — lower is better")
    ax.set_xlim(0, p.tracking_error_weekly_ann_pct.max() * 2.0)
    c = man["te_ci"][f"{AGQO} vs {PRACT}"]
    return _save(fig, out / "07_backtest.png",
                 f"Walk-forward 2024–2026 at 100M VND: AGQO tracks VN30 with {c['te_a']:.2f}% daily TE vs {c['te_b']:.2f}% for "
                 f"practitioner rounding (difference {c['diff_pp']:+.2f} pp, 95% CI {c['ci_low']:+.2f} to {c['ci_high']:+.2f})",
                 "Quarterly rebalance, whole lots, 0.15% commission + 0.1% sale tax; each strategy runs its own account. Weekly TE "
                 "is shown because ETF market prices carry daily noise around NAV. 'vs ETF' = return minus E1VFVN30 buy-and-hold.")


def fig_sweep(run: Path, out: Path) -> str:
    s = pd.read_csv(run / "sweep.csv")
    ci = json.loads((run / "run_manifest.json").read_text())["sweep_ci"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for name in (PRACT, EXACT, AGQO):
        d = s[s.strategy == name]
        a1.plot(d.capital_vnd / 1e6, d.tracking_error_ann_pct, marker="o", color=STRAT_COLOR[name], label=name)
    a1.set_xscale("log")
    a1.set_xlabel("account size (million VND, log)")
    a1.set_ylabel("tracking error vs VN30 (%)")
    a1.legend(fontsize=8)
    caps = sorted(ci, key=float)
    xs = np.array([float(c) / 1e6 for c in caps])
    diff = np.array([ci[c]["diff_pp"] for c in caps])
    lo, hi = np.array([ci[c]["ci_low"] for c in caps]), np.array([ci[c]["ci_high"] for c in caps])
    a2.fill_between(xs, lo, hi, color=SERIES[0], alpha=0.18, linewidth=0)
    a2.plot(xs, diff, color=SERIES[0], marker="o")
    a2.axhline(0, color=MUTED, linewidth=1)
    a2.set_xscale("log")
    a2.set_xlabel("account size (million VND, log)")
    a2.set_ylabel("TE(AGQO) - TE(practitioner), pp")
    for a in (a1, a2):
        a.set_xticks(xs, [f"{v:.0f}" for v in xs])
        a.minorticks_off()
    small = ci[caps[0]]
    return _save(fig, out / "08_account_size.png",
                 f"Whole lots matter most for small accounts: at {float(caps[0]) / 1e6:.0f}M VND AGQO changes tracking error by "
                 f"{small['diff_pp']:+.2f} pp vs practitioner rounding (95% CI {small['ci_low']:+.2f} to {small['ci_high']:+.2f})",
                 "Same 12 quarters for every account size. Right: paired difference with a moving-block bootstrap interval "
                 "(21-day blocks); below zero = AGQO tracks better.")


def fig_etf(run: Path, out: Path) -> str:
    v = pd.read_csv(run / "daily_values.csv", index_col=0, parse_dates=True)
    etf = v["ETF E1VFVN30"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for s in [PRACT, EQUAL, EXACT, AGQO, "ETF FUESSV30", "ETF FUEKIV30"]:
        if s in v:
            rel = (v[s] / v[s].iloc[0]) / (etf / etf.iloc[0]) * 100 - 100
            ax.plot(rel.index, rel.values, color=STRAT_COLOR[s], label=s, linewidth=2.4 if s == AGQO else 1.4)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylabel("cumulative return relative to E1VFVN30 (%)")
    ax.legend(loc="best", fontsize=8)
    return _save(fig, out / "09_vs_etf.png",
                 "Against the VN30 ETF a retail investor could buy instead: cumulative return relative to E1VFVN30 buy-and-hold",
                 "Account value divided by an E1VFVN30 buy-and-hold account of the same size, from the first test rebalance "
                 "(Jan 2024). Fees, taxes and dividends included on both sides.")


def fig_mandates(run: Path, out: Path) -> str:
    m = pd.read_csv(run / "mandates.csv")
    a = m[m.strategy == AGQO].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    y = np.arange(len(a))
    ax.barh(y, a.tracking_error_ann_pct, color=[MUTED] + [SERIES[0]] * (len(a) - 1), height=0.6)
    for i, r in a.iterrows():
        ax.text(r.tracking_error_ann_pct + 0.05, i, f"TE {r.tracking_error_ann_pct:.2f}%  ({r.te_cost_vs_unconstrained_pp:+.2f} "
                f"pp)  holdings {r.avg_holdings:.0f}  violations {int(r.rule_violations_at_rebalance)}", va="center",
                color=INK2, fontsize=8.5)
    ax.set_yticks(y, [textwrap.shorten(t, 60) for t in a.instruction], fontsize=8.5)
    ax.set_xlim(0, a.tracking_error_ann_pct.max() * 2.1)
    ax.set_xlabel("tracking error vs VN30 (%)")
    return _save(fig, out / "10_mandates.png",
                 "Personal rules have a measurable tracking cost, and every executed portfolio obeys them",
                 "AGQO at 100M VND, 2024–2026, with each Vietnamese instruction compiled by the LLM into constraints. 'Violations' "
                 "counts rebalances where any rule was broken after execution.")


def fig_latest(run: Path, out: Path) -> str:
    t = pd.read_csv(run / "latest_trades.csv")
    t = t[t.target_shares > 0].sort_values("target_value_vnd")
    rb = pd.read_csv(run / "rebalances.csv")
    last = rb[rb.strategy == AGQO].iloc[-1]
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
    return _save(fig, out / "11_latest_decision.png",
                 f"Latest decision ({last.date}): {len(t)} stocks in whole lots, {t.target_value_vnd.sum() / 1e6:.1f}M VND invested "
                 f"of a {last.nav_pre / 1e6:.1f}M VND account (100M in Jan 2024)",
                 "AGQO account: best affordable sample of the AI-guided circuit; the circuit is exported as OpenQASM.")


# ------------------------------------------------------------------ results page
def build_report(run: Path, out: Path, document: Path = Path("docs/RESULTS.md")) -> None:
    out.mkdir(parents=True, exist_ok=True)
    figure_dir = Path(os.path.relpath(out.resolve(), document.parent.resolve()))
    cfg = json.loads((run / "config.json").read_text())
    man = json.loads((run / "run_manifest.json").read_text())
    figs = [fig_lots(run, out, cfg["problem"]["capital_vnd"]), fig_market(run, out), fig_problem(run, out),
            fig_guidance(run, out), fig_quantum(run, out), fig_rounding(run, out), fig_backtest(run, out),
            fig_sweep(run, out), fig_etf(run, out), fig_mandates(run, out), fig_latest(run, out)]
    def figure_link(filename: str) -> str:
        return f"![{Path(filename).stem}](<{(figure_dir / filename).as_posix()}>)"

    f = lambda i: figure_link(figs[i])
    q = _pool(pd.read_csv(run / "quantum_test.csv"))
    qt = q.groupby("arm").agg(success_pct=("success_prob", lambda s: 100 * s.mean()),
                              beats_rounding_pct=("better_than_rounding", lambda s: 100 * s.mean()),
                              hit_in_512_shots_pct=("p_hit_in_shots", lambda s: 100 * s.mean()),
                              feasible_mass_pct=("feasible_mass", lambda s: 100 * s.mean()),
                              median_best_gap=("best_sample_gap", "median"), circuit_evals=("evaluations", "mean"),
                              cx=("two_qubit_gates", "mean"), layers=("layers", "mean")).reindex(
        [a for a in ARMS if a in set(q.arm)])
    qt.index = [ARM_LABEL[a].replace("\n", " ") for a in qt.index]
    st = pd.DataFrame(json.loads((run / "quantum_stats.json").read_text())).T[
        ["n", "wins", "mean_a", "mean_b", "ratio", "ratio_ci_low", "ratio_ci_high", "wilcoxon_p"]]
    perf = pd.read_csv(run / "strategy_performance.csv", index_col=0)[
        ["tracking_error_ann_pct", "tracking_error_weekly_ann_pct", "return_ann_pct", "active_return_ann_pct",
         "excess_return_vs_etf_ann_pct", "fees_vnd", "avg_holdings"]]
    ci = pd.DataFrame(man["te_ci"]).T[["te_a", "te_b", "diff_pp", "ci_low", "ci_high", "p_one_sided"]]
    sw = pd.read_csv(run / "sweep.csv").pivot(index="capital_vnd", columns="strategy", values="tracking_error_ann_pct")
    sw.index = [f"{c / 1e6:.0f}M VND" for c in sw.index]
    swci = pd.DataFrame(man["sweep_ci"]).T[["diff_pp", "ci_low", "ci_high", "p_one_sided"]]
    swci.index = [f"{float(c) / 1e6:.0f}M VND" for c in swci.index]
    mand = pd.read_csv(run / "mandates.csv").set_index(["instruction", "strategy"])[
        ["source", "tracking_error_ann_pct", "te_cost_vs_unconstrained_pp", "avg_holdings", "fallbacks",
         "qaoa_success_mean", "rule_violations_at_rebalance"]]
    mand.index = [f"{a} · {b.split(':')[0]}" for a, b in mand.index]
    cv = pd.read_csv(run / "schedule_cv.csv").set_index("label")[["cv_success", "cv_success_sd", "n"]]
    lines = ["# Results", "",
             f"_Auto-generated by `python -m agqo report` from `{run.name}` (run {man['run_seconds']:.0f}s). Training: "
             f"{man['train_dates'][0]} .. {man['train_dates'][-1]} (monthly, 4 account sizes). Test: {man['test_dates'][0]} .. "
             f"{man['test_dates'][-1]} (quarterly). Budget penalty λ = {man['budget_penalty']}._", "",
             "## 1. Data and phase 1 insight", f(0), "", f(1), "", f(2), "",
             "## 2. Phase 2: AI-guided circuit", f(3), "", _md(cv), "",
             "## 3. Quantum quality on the 12 test quarters", f(4), "", _md(qt), "",
             "Paired tests across quarters (a vs b; ratio of mean success with a 95% bootstrap interval):", "", _md(st, "{:.4g}"),
             "", f(5), "",
             "## 4. Financial walk-forward (100M VND, 2024-01 .. latest)", f(6), "", _md(perf), "",
             "Tracking-error differences, moving-block bootstrap (21-day blocks, 2,000 resamples); `p_one_sided` = share of "
             "resamples in which the first strategy does not track better:", "", _md(ci), "",
             "## 5. Account size", f(7), "", _md(sw), "", _md(swci), "",
             "## 6. Against the ETFs", f(8), "",
             "## 7. Personal mandates", f(9), "", _md(mand), ""]
    llm = run / "llm"
    if (llm / "mandate_eval.json").exists():
        sc = json.loads((llm / "mandate_eval.json").read_text())["score"]
        lines += ["## 8. LLM evaluation", "",
                  f"Mandate compiler on {sc['items']} hand-labelled Vietnamese instructions: Qwen3.8-27B effective-constraint "
                  f"match **{sc.get('llm_effective_pct', float('nan')):.1f}%** (strict JSON match "
                  f"{sc.get('llm_exact_pct', float('nan')):.1f}%), keyword rules {sc['rule_effective_pct']:.1f}%; clarification "
                  f"decisions correct {sc.get('llm_clarification_correct', '-')}/{sc['items']}; invalid outputs "
                  f"{sc.get('llm_invalid', '-')}.", ""]
    if (llm / "explanations.json").exists():
        ex = json.loads((llm / "explanations.json").read_text())
        s, last = ex["score"], ex["rows"][-1]
        lines += [f"Explainer: {s['all_numbers_verified']}/{s['explanations']} quarterly explanations had every number and "
                  f"trade verified against the evidence ({s['faithful_pct']:.0f}%). Latest ({last['date']}):", "",
                  "> " + (last["explanation"] or {}).get("summary_vi", "").replace("\n", " "), ""]
    lines += ["## 9. Latest decision", f(10), ""]
    if (run / "extras").exists():
        from .visuals import build_visuals
        vis = build_visuals(run, out)
        lines += ["## 10. Presentation figures", ""] + [figure_link(v) for v in vis] + [""]
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text("\n".join(lines))
    print("figures:", figs)
