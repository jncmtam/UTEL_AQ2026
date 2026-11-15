"""Presentation figures: architecture, circuit, probability flow, a concrete decision, hardware,
scaling, robustness and the evaluation board. Built from results/final and results/final/extras."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from .report import GRID, INK, INK2, MUTED, SERIES, SURFACE, _save

AI, QC, CL, DATA = "#2a78d6", "#6250d6", "#1baf7a", "#8a8984"       # AI / quantum / classical / data
LIGHT = {AI: "#e3eefb", QC: "#ebe8fb", CL: "#e2f5ee", DATA: "#efefec"}


def _box(ax, x, y, w, h, title, body, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", linewidth=1.6,
                                edgecolor=color, facecolor=LIGHT[color]))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=9.6, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.62, body, ha="center", va="top", fontsize=7.9, color=INK2, linespacing=1.35)


def _arrow(ax, a, b, color=MUTED, text=None, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, linewidth=1.4, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.14, text, ha="center", fontsize=7.2, color=INK2)


def fig_architecture(run: Path, out: Path) -> str:
    fig, ax = plt.subplots(figsize=(14, 6.9))
    ax.set_xlim(0, 16.1)
    ax.set_ylim(0.2, 7.8)
    ax.axis("off")
    W, H = 2.9, 1.75
    _box(ax, 0.2, 5.9, W, H, "Market data", "DNSE daily OHLCV 2022–2026\n40 stocks ever in VN30\n(point-in-time membership)\nVN30, VN-Index, 3 VN30 ETFs", DATA)
    _box(ax, 0.2, 1.4, W, H, "Investor", "\"Không đầu tư bất động sản,\nngân hàng tối đa 30%\"\naccount size, current holdings", DATA)
    _box(ax, 3.7, 5.9, W, H, "1a · Market insight", "correlation, market factor,\neffective bets, clusters,\nlot cost, rounding cost\n(statistics)", AI)
    _box(ax, 3.7, 1.4, W, H, "1b · LLM mandate compiler", "Qwen3.8-27B · vLLM · 1×H100\nJSON-schema output\nexclusions, caps, holdings, cash\n→ validated by code", AI)
    _box(ax, 7.2, 3.65, W, H, "Whole-lot problem", "continuous QP with caps\n→ cap-safe 16-qubit register\nQUBO = TE² + turnover\n+ budget penalty (exact)", CL)
    _box(ax, 7.2, 5.9, W, H, "2a · Problem insight", "warm start x* (relaxation)\ncoupling sources & mass\nRMS energy scale\n5 features per quarter", AI)
    _box(ax, 10.7, 5.9, W, H, "2b · AI guidance", "k-NN schedule model\ntrained on 48 problems (2023)\nchooses p, ε, mass, Δγ, Δβ\n+ CVaR polish (train rule)", AI)
    _box(ax, 10.7, 3.65, W, H, "QAOA circuit", "R1 warm start · R2 aligned mixer\nR3 couplings · R4 RMS scale\nR5 linear ramp · 512 shots\nsimulator / Qiskit / IBM", QC)
    _box(ax, 10.7, 1.4, W, H, "Exact verification", "cash, fees, tax, caps per sample\nall 2^16 states enumerated\n→ best affordable decision", CL)
    _box(ax, 14.0, 3.65, 2.0, H, "Output", "trade list in\nwhole lots,\nfees and tax", DATA)
    _box(ax, 14.0, 1.4, 2.0, H, "LLM explainer", "Vietnamese note\nevery number\nchecked", AI)
    _arrow(ax, (3.1, 6.78), (3.7, 6.78))
    _arrow(ax, (3.1, 2.28), (3.7, 2.28))
    _arrow(ax, (6.6, 6.2), (7.2, 4.9), text="weights, risk")
    _arrow(ax, (6.6, 2.5), (7.2, 4.1), text="constraints")
    _arrow(ax, (8.65, 5.4), (8.65, 5.9))
    _arrow(ax, (10.1, 6.78), (10.7, 6.78), text="features")
    _arrow(ax, (12.15, 5.9), (12.15, 5.4), text="schedule")
    _arrow(ax, (10.1, 4.5), (10.7, 4.5), text="Hamiltonian")
    _arrow(ax, (12.15, 3.65), (12.15, 3.15), text="samples")
    _arrow(ax, (13.6, 2.6), (14.0, 4.2), text="decision")
    _arrow(ax, (15.0, 3.65), (15.0, 3.15))
    for c, lab, x in [(AI, "AI (statistics, learned model, LLM)", 0.3), (QC, "quantum", 5.2), (CL, "classical / exact", 7.0),
                      (DATA, "data and outputs", 9.4)]:
        ax.add_patch(FancyBboxPatch((x, 0.35), 0.35, 0.3, boxstyle="round,pad=0.02", facecolor=LIGHT[c], edgecolor=c))
        ax.text(x + 0.5, 0.5, lab, va="center", fontsize=8.5, color=INK2)
    return _save(fig, out / "A1_architecture.png",
                 "AGQO architecture: AI reads the market and the investor, guides a quantum circuit, and classical "
                 "checks verify every decision",
                 "Blue = AI components, purple = quantum, green = exact classical computation. No AI output reaches the "
                 "optimiser without validation; no sample is executed unless it passes the exact cash, fee, tax and cap checks.")


def fig_circuit(run: Path, out: Path) -> str:
    ex = json.loads((run / "extras" / "examples.json").read_text())["100000000"]
    fig = plt.figure(figsize=(14, 5.6))
    ax = fig.add_axes([0.02, 0.06, 0.58, 0.78])
    ax.set_xlim(0, 13)
    ax.set_ylim(-0.6, 4.3)
    ax.axis("off")
    reg = ex["register"][:4]
    ys = [3.5, 2.5, 1.5, 0.5]
    for y, t in zip(ys, reg):
        ax.plot([0.9, 12.6], [y, y], color=INK2, linewidth=1)
        ax.text(0.8, y, f"{t}  |0⟩", ha="right", va="center", fontsize=9, color=INK)

    def gate(x, y, txt, c, w=1.1):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.27), w, 0.54, boxstyle="round,pad=0.02", facecolor=LIGHT[c],
                                    edgecolor=c, linewidth=1.3, zorder=3))
        ax.text(x, y, txt, ha="center", va="center", fontsize=7.4, color=INK, zorder=4)
    for y in ys:
        gate(1.6, y, "Ry(θk)", AI)
        gate(3.05, y, "Rz(2γhk)", QC)
    for i, (a, b) in enumerate([(0, 1), (0, 2), (1, 3), (2, 3)]):
        x = 4.3 + 0.75 * i
        ax.plot([x, x], [ys[a], ys[b]], color=QC, linewidth=1.6)
        ax.plot([x, x], [ys[a], ys[b]], "o", color=QC, markersize=5)
    ax.text(5.4, 4.05, "ZZ(2γJ_kl) for kept pairs", ha="center", fontsize=8, color=QC)
    for y in ys:
        gate(8.0, y, "Ry(θ)·Rz(−2β)·Ry(−θ)", AI, w=2.3)
        gate(10.1, y, "…", DATA, w=0.5)
        gate(11.8, y, "measure", CL, w=1.1)
    ax.add_patch(FancyBboxPatch((2.3, -0.15), 7.0, 4.05, boxstyle="round,pad=0.02", facecolor="none",
                                edgecolor=MUTED, linestyle="--"))
    ax.text(5.8, -0.45, "one QAOA layer, repeated p times with γ rising and β falling (R5)", ha="center", fontsize=8,
            color=INK2)
    ax.text(1.6, 4.05, "R1 warm\nstart", ha="center", fontsize=8, color=AI)
    ax.text(3.05, 4.05, "fields\n(R4 scaled)", ha="center", fontsize=8, color=QC)
    ax.text(8.0, 4.05, "R2 aligned mixer", ha="center", fontsize=8, color=AI)
    ax2 = fig.add_axes([0.665, 0.12, 0.27, 0.68])
    J = np.array(ex["J"])
    r = ex["register"]
    sect = [ex["sector"][ex["tickers"].index(t)] for t in r]
    order = np.argsort(sect, kind="stable")
    Jo = J[np.ix_(order, order)]
    vmax = np.abs(Jo).max()
    im = ax2.imshow(Jo, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax2.set_xticks(range(len(r)), [r[i] for i in order], rotation=90, fontsize=7)
    ax2.set_yticks(range(len(r)), [f"{r[i]} ({sect[i][:4]})" for i in order], fontsize=7)
    ax2.grid(False)
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.03).set_label("coupling J_kl", fontsize=8)
    ax2.set_title("couplings of the latest quarter (16 qubits)", fontsize=9, color=INK2)
    return _save(fig, out / "A2_circuit.png",
                 "The circuit is written by the data: warm-start angles from the relaxation, couplings from how stocks "
                 "move together, angles scaled by the Hamiltonian's RMS",
                 "Left: one layer for 4 of the 16 qubits (qubit k = 'buy one more lot of stock k'). Right: the real coupling "
                 "matrix J for Oct 2026, ordered by sector; strong couplings (dark) are pairs whose extra lots change "
                 "tracking error together.")


def fig_distribution(run: Path, out: Path) -> str:
    d = pd.read_csv(run / "extras" / "distributions.csv")
    cols = ["optimal", "within 5%", "5–25%", "25–100%", "worse than typical", "over budget"]
    colors = ["#008300", "#1baf7a", "#a6d8c0", "#eda100", "#e34948", GRID]
    m = d.groupby("arm")[cols].mean().reindex(["random guessing", "warm start only", "textbook QAOA", "AGQO"]) * 100
    fig, ax = plt.subplots(figsize=(11, 4.0))
    left = np.zeros(len(m))
    for c, col in zip(cols, colors):
        ax.barh(range(len(m)), m[c], left=left, color=col, height=0.6, label=c, edgecolor=SURFACE)
        for i, v in enumerate(m[c]):
            if v > 4:
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color="white" if col in ("#008300", "#e34948") else INK)
        left += m[c].to_numpy()
    ax.set_yticks(range(len(m)), m.index)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of measurement probability (%), mean over 12 test quarters")
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8)
    ax.grid(False)
    a = m.loc["AGQO"]
    return _save(fig, out / "A3_probability_flow.png",
                 f"Where the probability goes: AGQO puts {a['optimal'] + a['within 5%']:.0f}% of its shots within 5% of the "
                 f"best affordable portfolio, against {m.loc['random guessing', 'optimal'] + m.loc['random guessing', 'within 5%']:.1f}% "
                 "for random guessing",
                 "Each bar is a measurement distribution over the 65,536 lot decisions, binned by how far each decision is "
                 "from the exact optimum (normalised gap). Green = good portfolios, red = worse than a typical affordable one.")


def fig_example(run: Path, out: Path) -> str:
    ex = json.loads((run / "extras" / "examples.json").read_text())["20000000"]
    t = np.array(ex["tickers"])
    c, p, g, a = (np.array(ex[k]) * 100 for k in ("continuous", "practitioner", "greedy", "agqo"))
    top = np.argsort(-c)[:16]
    fig, ax = plt.subplots(figsize=(12.5, 4.8))
    x = np.arange(len(top))
    w = 0.2
    for off, v, col, lab in [(-1.5, c, MUTED, f"ideal fractional weights (TE {ex['te']['continuous']:.1f}%)"),
                             (-0.5, p, SERIES[7], f"naive nearest-lot rounding (TE {ex['te']['practitioner']:.1f}%, "
                                                  f"{100 - p.sum():.0f}% cash)"),
                             (0.5, g, SERIES[3], f"greedy lot filling (TE {ex['te']['greedy']:.1f}%)"),
                             (1.5, a, SERIES[0], f"AGQO whole-lot decision (TE {ex['te']['agqo']:.1f}%)")]:
        ax.bar(x + off * w, v[top], w, color=col, label=lab)
    ax.set_xticks(x, [f"{t[j]}\n{ex['lot_pct'][j]:.0f}%" for j in top], fontsize=8.5)
    ax.set_xlabel("stock (and the cost of one 100-share lot as % of the account)", fontsize=8.5)
    ax.set_ylabel("weight in the 20M VND account (%)")
    ax.legend(fontsize=8.5, ncol=2, loc="upper right")
    ax.set_ylim(0, max(c[top].max(), a[top].max(), g[top].max()) * 1.45)
    return _save(fig, out / "A4_one_decision.png",
                 f"One real decision ({ex['date']}, 20M VND): when one lot costs {min(ex['lot_pct'][j] for j in top):.0f}–"
                 f"{max(ex['lot_pct'][j] for j in top):.0f}% of the account, which stocks get a lot "
                 f"decides tracking error — {ex['te']['practitioner']:.1f}% naive, {ex['te']['greedy']:.1f}% greedy, "
                 f"{ex['te']['agqo']:.1f}% AGQO (ex-ante)",
                 "Bars: weights of the 16 largest target positions. Grey = what the continuous optimiser wants; red = round each "
                 "stock to its nearest lot, then trim to the budget; amber = add the most useful lot one at a time; blue = "
                 "AGQO's sampled whole-lot portfolio (equal to the exact optimum of the 16-qubit register).")


def fig_hardware(run: Path, out: Path) -> str:
    from .stats import paired_test

    h = pd.read_csv(run / "extras" / "hardware.csv")
    ha = pd.read_csv(run / "extras" / "hardware_aware.csv")
    hs = json.loads((run / "extras" / "hardware_aware.json").read_text())
    order = ["warm start only", "textbook QAOA", "AGQO (chosen schedule)", "AGQO shallow (p=2, 75% couplings)"]
    g = h.groupby("circuit").mean(numeric_only=True).reindex(order)
    na = ha[ha.date.isin(h.date)].mean(numeric_only=True)
    labels = ["warm start\n(0 layers)", "textbook\nQAOA p=2", "AGQO deep\np=6, all pairs", "AGQO shallow\np=2, 75%",
              "AGQO noise-aware\np=2, 25%"]
    two_q = list(g.native_2q) + [na.native_2q]
    esp = list(g.esp) + [na.esp_transpiled]
    ideal = list(g.ideal_success) + [na.ideal_success]
    noisy = list(g.esp_model_success) + [na.esp_fit * na.ideal_success + (1 - na.esp_fit) * na.uniform]
    aer = list(g.get("aer_noisy_success", pd.Series(np.nan, index=g.index))) + [na.aer_noisy_success]
    cols = [SERIES[7], SERIES[1], SERIES[6], SERIES[3], SERIES[0]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8))
    x = np.arange(len(labels))
    a1.bar(x, np.maximum(two_q, 1), color=cols, width=0.6)
    for i, (v, e) in enumerate(zip(two_q, esp)):
        a1.text(i, max(v, 1) * 1.2, f"{v:.0f} CZ\nESP {e:.2g}", ha="center", fontsize=8, color=INK2)
    a1.set_yscale("log")
    a1.set_ylim(0.5, 4e4)
    a1.set_ylabel("native two-qubit gates after routing (log)")
    a1.set_xticks(x, labels, fontsize=7.6)
    a2.bar(x - 0.2, 100 * np.array(ideal), 0.38, color=GRID, edgecolor=MUTED, label="noiseless")
    a2.bar(x + 0.2, 100 * np.array(noisy), 0.38, color=cols, label="with Heron noise (ESP model)")
    a2.plot(x + 0.2, 100 * np.array(aer), "D", color=INK, markersize=6, label="full Aer noise simulation")
    a2.axhline(100 * g.uniform_success.mean(), color=MUTED, linestyle=":", label="random guessing")
    a2.set_xticks(x, labels, fontsize=7.6)
    a2.set_ylabel("near-optimal success per shot (%)")
    a2.legend(fontsize=7.5, loc="upper left")
    t = paired_test(ha.esp_model_success, ha.warm_esp_model)
    return _save(fig, out / "A5_hardware.png",
                 f"On IBM Heron noise, depth is the enemy: the deep circuit collapses, while the noise-aware AI guidance picks a "
                 f"{na.native_2q:.0f}-gate circuit that keeps {t['ratio']:.1f}x its warm start ({t['wins']}/12 quarters, "
                 f"p={t['wilcoxon_p']:.4f})",
                 "Circuits transpiled to FakeKingston (156-qubit Heron r2, calibrated errors, optimisation level 3) for 3 test "
                 "quarters. ESP = product of (1 − error) over all gates; noisy success = ESP × noiseless + (1 − ESP) × random. "
                 f"Diamonds: full Aer noise simulation, 1,000 shots. The deep circuit would need a two-qubit error of "
                 f"{100 * hs['two_qubit_error_needed_for_esp_0.5']:.3f}% (today {100 * hs['median_cz_error_today']:.2f}%) to keep half its advantage.")


def fig_scaling(run: Path, out: Path) -> str:
    s = pd.read_csv(run / "extras" / "scaling.csv")
    g = s.groupby("qubits").mean(numeric_only=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4))
    n = np.arange(8, 61)
    a1.plot(n, 2.0 ** n, color=SERIES[7], label="lot decisions to check (2^n)")
    a1.plot(n, 2 * n * (n - 1) / 2 * 6, color=SERIES[0], label="AGQO logical CX gates (p = 6, all couplings)")
    a1.plot(g.index, g.enumeration_s * 1e6, "o", color=SERIES[7], label="measured enumeration time (µs)")
    a1.axvline(60, color=MUTED, linestyle=":")
    a1.text(59, 1e9, "30 stocks × 2 lots\n= 60 qubits", ha="right", fontsize=8, color=INK2)
    a1.set_yscale("log")
    a1.set_xlabel("qubits n (stocks that get a lot decision)")
    a1.legend(fontsize=7.5, loc="upper left")
    a2.plot(g.index, 100 * g.frozen_success, "o-", color=SERIES[0], label="AGQO frozen 2023 schedule")
    a2.plot(g.index, 100 * g.warm_success, "s-", color=SERIES[7], label="warm start only")
    a2.plot(g.index, 100 * g.uniform_success, "^-", color=MUTED, label="random guessing")
    a2.set_yscale("log")
    a2.set_xlabel("qubits n")
    a2.set_ylabel("near-optimal success per shot (%, log)")
    a2.legend(fontsize=7.5)
    ratio = (g.frozen_success / g.warm_success)
    sa = s.groupby("qubits").sa_gap.agg(lambda v: int((v <= 1e-9).sum()))
    sa5 = s.groupby("qubits").sa_gap.agg(lambda v: int((v <= 0.05).sum()))
    return _save(fig, out / "A6_scaling.png",
                 f"Scaling: the problem grows exponentially while the circuit grows quadratically, and the 2023 schedule "
                 f"still beats its warm start {ratio.min():.1f}–{ratio.max():.1f}x from 8 to 20 qubits",
                 "Left: size of the search space vs circuit size; enumeration is instant at 16 qubits but impossible near 60. "
                 "Right: same schedule (trained on 16-qubit 2023 problems, RMS-scaled) applied unchanged to 8–20 qubits on "
                 f"the 12 test quarters. One short annealing run is exact in {sa[8]}/12, {sa[12]}/12, {sa[16]}/12, {sa[20]}/12 quarters "
                 f"at 8/12/16/20 qubits (within 5%: {sa5[16]}/12 at 16, {sa5[20]}/12 at 20).")


def fig_robustness(run: Path, out: Path) -> str:
    r = pd.read_csv(run / "extras" / "robustness.csv")
    base = r[r.te_practitioner.notna()]
    odd = r[r.te_odd_lot.notna()]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.0))
    scen = list(base.scenario.drop_duplicates())
    for k, (cap, kind, col, mk) in enumerate([(20e6, "naive", SERIES[7], "o"), (20e6, "greedy", SERIES[3], "s"),
                                               (100e6, "naive", SERIES[6], "o"), (100e6, "greedy", SERIES[0], "s")]):
        d = base[base.capital_vnd == cap].set_index("scenario").reindex(scen)
        dv = d.diff_pp if kind == "naive" else d.diff_vs_greedy_pp
        lo = d.ci_low if kind == "naive" else d.greedy_ci_low
        hi = d.ci_high if kind == "naive" else d.greedy_ci_high
        y = np.arange(len(scen)) + (k - 1.5) * 0.17
        a1.errorbar(dv, y, xerr=[dv - lo, hi - dv], fmt=mk, color=col, capsize=2.5,
                    label=f"{cap / 1e6:.0f}M: AGQO/exact vs {kind} rounding")
    a1.set_yticks(range(len(scen)), scen, fontsize=8)
    a1.set_ylim(-0.5, len(scen) + 0.5)
    a1.axvline(0, color=MUTED)
    a1.set_xlabel("difference in tracking error, pp (95% CI); left of 0 = AGQO tracks better")
    a1.legend(fontsize=7.4, loc="upper left", ncol=2)
    for i, cap in enumerate((20e6, 100e6)):
        d = odd[odd.capital_vnd == cap]
        prem = d.scenario.str.extract(r"premium ([\d.]+)%")[0].astype(float)
        b = base[(base.capital_vnd == cap) & base.scenario.str.startswith("base")].iloc[0]
        col = SERIES[7] if i == 0 else SERIES[0]
        a2.plot(prem, d.return_odd_lot - b.return_whole_lot_optimum, "o-", color=col,
                label=f"{cap / 1e6:.0f}M: return, odd lots − AGQO")
        a2.plot(prem, d.te_odd_lot - b.te_whole_lot_optimum, "s--", color=col,
                label=f"{cap / 1e6:.0f}M: tracking error, odd lots − AGQO")
    a2.axhline(0, color=MUTED)
    a2.set_xlabel("assumed extra cost of trading the odd-lot part (% of its value)")
    a2.set_ylabel("percentage points per year")
    a2.legend(fontsize=7.4, loc="center", bbox_to_anchor=(0.55, 0.27))
    return _save(fig, out / "A7_robustness.png",
                 "Robustness: AGQO's whole-lot decision beats naive rounding at 20M under every fee level and rebalancing "
                 "frequency; a greedy heuristic closes most of the gap; odd-lot trading is the honest alternative",
                 "Left: AGQO/exact whole-lot decision minus a baseline (naive nearest-lot rounding, or greedy lot filling), "
                 "moving-block bootstrap CIs, 2024–2026. Right: buying 1-share odd lots (HOSE, since Sep 2022) at the ideal "
                 "weights with an assumed extra cost on the odd-lot part; above 0 = odd lots ahead. Fill risk is not modelled.")


def odd_lot_break_even(rb: pd.DataFrame) -> dict:
    """Odd-lot cost (% of the odd part) at which odd-lot execution's return falls to AGQO's (linear fit)."""
    out = {}
    for cap, d in rb[rb.te_odd_lot.notna()].groupby("capital_vnd"):
        prem = d.scenario.str.extract(r"premium ([\d.]+)%")[0].astype(float)
        base = rb[(rb.capital_vnd == cap) & rb.scenario.str.startswith("base")].iloc[0]
        slope, icpt = np.polyfit(prem, d.return_odd_lot - base.return_whole_lot_optimum, 1)
        out[cap] = -icpt / slope
    return out


def fig_board(run: Path, out: Path) -> str:
    st = json.loads((run / "quantum_stats.json").read_text())
    man = json.loads((run / "run_manifest.json").read_text())
    mand = pd.read_csv(run / "mandates.csv")
    me = json.loads((run / "llm" / "mandate_eval.json").read_text())["score"]
    ex = json.loads((run / "llm" / "explanations.json").read_text())["score"]
    cv = pd.read_csv(run / "schedule_cv.csv")
    ci = man["te_ci"]
    sw = man["sweep_ci"]
    agqo_pract = next(v for k, v in ci.items() if k.startswith("AGQO") and "Practitioner" in k)
    from .stats import paired_test
    ha = pd.read_csv(run / "extras" / "hardware_aware.csv")
    hw_t = paired_test(ha.esp_model_success, ha.warm_esp_model)
    rb = pd.read_csv(run / "extras" / "robustness.csv")
    gr = rb[(rb.capital_vnd == 20e6) & rb.scenario.str.startswith("base")].iloc[0]
    hs = json.loads((run / "extras" / "hardware_aware.json").read_text())
    hw = pd.read_csv(run / "extras" / "hardware.csv")
    deep_esp = hw[hw.circuit == "AGQO (chosen schedule)"].esp.mean()
    be = odd_lot_break_even(rb)
    rows = [
        ("Quantum", "AGQO circuit vs its classical warm start", f"{st['agqo vs warm_start_only']['ratio']:.1f}x success",
         f"12/12 quarters, p={st['agqo vs warm_start_only']['wilcoxon_p']:.4f}", "pass"),
        ("Quantum", "vs textbook QAOA", f"{st['agqo vs textbook']['ratio']:.0f}x", f"12/12, p={st['agqo vs textbook']['wilcoxon_p']:.4f}", "pass"),
        ("Quantum", "vs random search over designs", f"{st['agqo vs random']['ratio']:.1f}x", f"12/12, p={st['agqo vs random']['wilcoxon_p']:.4f}", "pass"),
        ("Quantum", "AGQO decision = exact optimum (100M)", "12/12 quarters", "gap 0 in every quarter", "pass"),
        ("AI", "learned schedule vs frozen schedule (CV)", f"{100 * cv.cv_success.max():.1f}% vs {100 * cv[cv.k == 0].cv_success.iloc[0]:.1f}%",
         f"test: {st['agqo vs frozen']['wins']}/12, p={st['agqo vs frozen']['wilcoxon_p']:.2f}", "no gain"),
        ("AI", "CVaR polish (chosen on training)", "train +1.5 pts", f"test {st['agqo vs polish_ablation']['ratio']:.2f}x, p={st['agqo vs polish_ablation']['wilcoxon_p']:.2f}", "no gain"),
        ("AI", "LLM mandate compiler (35 VN instructions)", f"{me['llm_effective_pct']:.0f}% correct", f"keyword rules {me['rule_effective_pct']:.1f}%", "pass"),
        ("AI", "LLM explanations: numbers and meaning checked",
         f"{ex['all_numbers_verified']}/{ex['explanations']} numbers, "
         f"{round(ex['faithful_pct'] * ex['explanations'] / 100)}/{ex['explanations']} meaning",
         "old prompt: 12/12 numbers, 0/12 meaning", "pass"),
        ("Finance", "vs naive rounding, 20M VND", f"{sw['20000000']['te_a']:.1f}% vs {sw['20000000']['te_b']:.1f}%",
         f"CI {sw['20000000']['ci_low']:+.1f} to {sw['20000000']['ci_high']:+.1f} pp", "pass"),
        ("Finance", "vs greedy lot filling (strong heuristic), 20M", f"{gr['te_whole_lot_optimum']:.1f}% vs {gr['te_greedy']:.1f}%",
         f"CI {gr['greedy_ci_low']:+.2f} to {gr['greedy_ci_high']:+.2f} pp (monthly: significant)", "not significant"),
        ("Finance", "Tracking error at 100M VND", f"{agqo_pract['te_a']:.2f}% vs {agqo_pract['te_b']:.2f}%",
         f"CI {agqo_pract['ci_low']:+.2f} to {agqo_pract['ci_high']:+.2f} pp", "not significant"),
        ("Finance", "Personal rules respected", f"{int(mand.rule_violations_at_rebalance.sum())} violations", "3 mandates × 12 quarters", "pass"),
        ("Finance", "Return vs VN30 ETF (E1VFVN30)", "−1.1%/yr", "ETF cheaper, reinvests dividends", "trails"),
        ("Quantum", "Noise-aware circuit on IBM Heron noise vs warm start", f"{hw_t['ratio']:.1f}x success",
         f"{hw_t['wins']}/12, p={hw_t['wilcoxon_p']:.4f}; Aer check on 3", "pass"),
        ("Quantum", "Deep circuit (p=6) on today's hardware", f"ESP ≈ {deep_esp:.4f}",
         f"needs ~{hs['median_cz_error_today'] / hs['two_qubit_error_needed_for_esp_0.5']:.0f}x lower 2-qubit error", "fails today"),
        ("Finance", "Odd-lot execution (HOSE since 2022) vs AGQO whole lots",
         "odd lots track better", f"unless odd-lot cost > {be[20e6]:.1f}% (20M), {be[100e6]:.1f}% (100M)", "alternative"),
        ("Quantum", "Quantum advantage", "none", "enumeration exact in 0.12 s", "not claimed"),
    ]
    fig, ax = plt.subplots(figsize=(13, 0.48 * len(rows) + 1.4))
    ax.axis("off")
    color = {"pass": "#1baf7a", "no gain": "#eda100", "not significant": "#eda100", "trails": "#e34948",
             "not claimed": MUTED, "fails today": "#e34948", "alternative": "#eda100"}
    heads = ["area", "test", "result", "evidence", "verdict"]
    xs = [0.0, 0.08, 0.45, 0.66, 0.9]
    for x, hd in zip(xs, heads):
        ax.text(x, 1.0, hd, fontsize=9.5, weight="bold", color=INK, transform=ax.transAxes)
    for i, r in enumerate(rows):
        y = 1 - (i + 1) / (len(rows) + 1)
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((-0.01, y - 0.025), 1.02, 1 / (len(rows) + 1), transform=ax.transAxes,
                                       color="#f3f3f0", zorder=0))
        for x, v in zip(xs[:4], r[:4]):
            ax.text(x, y, v, fontsize=8.6, color=INK2, transform=ax.transAxes, va="bottom")
        ax.text(xs[4], y, f"● {r[4]}", fontsize=8.8, color=color[r[4]], transform=ax.transAxes, va="bottom", weight="bold")
    return _save(fig, out / "A8_evaluation_board.png", "Evaluation board: every claim, its baseline and its evidence",
                 "Green = supported with the stated statistics; amber = tested and not supported; red = trails the alternative; "
                 "grey = deliberately not claimed. Test period 2024-01 to 2026-11; all calibration on 2023.")


def build_visuals(run: Path, out: Path) -> list[str]:
    figs = [fig_architecture(run, out), fig_circuit(run, out), fig_distribution(run, out), fig_example(run, out)]
    ex = run / "extras"
    if (ex / "hardware.csv").exists():
        figs.append(fig_hardware(run, out))
    if (ex / "scaling.csv").exists():
        figs.append(fig_scaling(run, out))
    if (ex / "robustness.csv").exists():
        figs.append(fig_robustness(run, out))
    figs.append(fig_board(run, out))
    return figs
