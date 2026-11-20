"""Report and slide figures with English technical labels (sentence case), drawn from the saved evidence.

    python submission/report/figures.py      # -> submission/report/figures/*.png

One visual language: white background, Arial, AGQO in blue, classical comparators in greys, quantum in violet,
warnings in rose. The quantum circuit is drawn with Qiskit's standard circuit drawer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RUN = ROOT / "results" / "final"
OUT = Path(__file__).resolve().parent / "figures"

INK, MUTED, GRID, PANEL = "#0F172A", "#475569", "#E5E9F0", "#F8FAFC"
AGQO, AGQO_L = "#0284C7", "#7DD3FC"
GREEDY, ROUND, IDEAL = "#64748B", "#CBD5E1", "#94A3B8"
QUANT, AI, CLASS, DATA, WARN, GOOD = "#7C3AED", "#0284C7", "#059669", "#475569", "#E11D48", "#16A34A"
AMBER = "#D97706"

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "axes.edgecolor": "#CBD5E1", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
                     "axes.titleweight": "bold", "axes.titlesize": 11.5, "axes.titlelocation": "left",
                     "axes.titlecolor": INK, "legend.frameon": False, "savefig.dpi": 220, "savefig.bbox": "tight",
                     "savefig.facecolor": "white"})


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / name)
    plt.close(fig)
    return OUT / name


# ------------------------------------------------------------------ 3 pipeline
# Drawn in inches at its printed size (16.5 cm wide): few words per box so the text prints at ~7 pt.
def _node(ax, x, y, w, h, color, title, lines, step=None):
    band = 0.27
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", facecolor="white",
                                edgecolor=color, linewidth=1.3, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y + h - band), w, band, boxstyle="round,pad=0,rounding_size=0.06",
                                facecolor=color, edgecolor=color, linewidth=1.3, zorder=3))
    ax.add_patch(plt.Rectangle((x, y + h - band), w, 0.1, facecolor=color, edgecolor="none", zorder=3))
    tx = x + 0.07
    if step:
        ax.add_patch(plt.Circle((x + 0.15, y + h - band / 2), 0.095, facecolor="white", edgecolor="none", zorder=4))
        ax.text(x + 0.15, y + h - band / 2, step, color=color, fontsize=6.6, weight="bold", ha="center", va="center",
                zorder=5)
        tx = x + 0.29
    ax.text(tx, y + h - band / 2, title, color="white", fontsize=8.6, weight="bold", va="center", zorder=4)
    for k, ln in enumerate(lines):
        ax.text(x + 0.08, y + h - band - 0.19 - 0.19 * k, ln, color=INK, fontsize=8, va="center", zorder=4)


def _edge(ax, a, b, label=None, lpos=None, ha="center"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color=MUTED, lw=1.2, zorder=1,
                                 shrinkA=0, shrinkB=1))
    if label:
        ax.text(lpos[0], lpos[1], label, fontsize=7, color=MUTED, style="italic", ha=ha, va="center", zorder=5)


def pipeline():
    from matplotlib.patches import Patch

    FW, FH = 8.5, 3.75
    fig = plt.figure(figsize=(FW, FH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FW)
    ax.set_ylim(0, FH)
    ax.axis("off")
    W, H, G = 1.42, 0.78, 0.32
    X = [0.04 + k * (W + G) for k in range(5)]
    Y = [0.05, 1.33, 2.61]
    _node(ax, X[0], Y[2], W, H, DATA, "Market data", ["VN30, VN-Index, ETFs", "Daily, 2022–2026"])
    _node(ax, X[0], Y[0], W, H, DATA, "Investor request", ["“No real estate,", "banks ≤ 30%”"])
    _node(ax, X[1], Y[2], W, H, AI, "Market insight", ["Correlation, factors", "Lot cost vs account"], "1a")
    _node(ax, X[1], Y[0], W, H, AI, "LLM parser", ["Qwen3.8-27B → JSON", "Code check, confirm"], "1b")
    _node(ax, X[2], Y[1], W, H, CLASS, "Whole-lot QUBO", ["16 cap-safe qubits", "TE² + turnover"], "2")
    _node(ax, X[3], Y[2], W, H, AI, "Circuit design", ["k-NN on 5 features", "1 of 1,080 schedules"], "3")
    _node(ax, X[3], Y[1], W, H, QUANT, "QAOA sampling", ["Warm start, mixer", "512 shots"], "4")
    _node(ax, X[3], Y[0], W, H, CLASS, "Exact check", ["Fees, tax, caps", r"Enumerate all $2^{16}$"], "5")
    _node(ax, X[4], Y[0], W, H, DATA, "Orders", ["Board-lot trades", "Cash after fees"])
    _node(ax, X[4], Y[1], W, H, AI, "Explanation", ["Vietnamese text", "Numbers checked"], "6")
    mid = lambda y: y + H / 2
    _edge(ax, (X[0] + W, mid(Y[2])), (X[1], mid(Y[2])))
    _edge(ax, (X[0] + W, mid(Y[0])), (X[1], mid(Y[0])))
    _edge(ax, (X[1] + W, mid(Y[2]) - 0.1), (X[2] + 0.35, Y[1] + H), "Weights, risk", (X[2] + 0.42, Y[1] + H + 0.2),
          ha="left")
    _edge(ax, (X[1] + W, mid(Y[0]) + 0.1), (X[2] + 0.35, Y[1]), "Constraints", (X[2] + 0.42, Y[1] - 0.2), ha="left")
    _edge(ax, (X[2] + W - 0.35, Y[1] + H), (X[3], mid(Y[2]) - 0.1), "Features", (X[2] + W - 0.25, Y[1] + H + 0.36),
          ha="right")
    _edge(ax, (X[2] + W, mid(Y[1])), (X[3], mid(Y[1])), "QUBO", ((X[2] + W + X[3]) / 2, mid(Y[1]) + 0.1))
    _edge(ax, (X[3] + W / 2, Y[2]), (X[3] + W / 2, Y[1] + H), "Schedule", (X[3] + W / 2 + 0.06, Y[2] - 0.25), ha="left")
    _edge(ax, (X[3] + W / 2, Y[1]), (X[3] + W / 2, Y[0] + H), "Samples", (X[3] + W / 2 + 0.06, Y[1] - 0.25), ha="left")
    _edge(ax, (X[3] + W, mid(Y[0])), (X[4], mid(Y[0])), "Best", ((X[3] + W + X[4]) / 2, mid(Y[0]) + 0.1))
    _edge(ax, (X[4] + W / 2, Y[0] + H), (X[4] + W / 2, Y[1]))
    hs = [Patch(color=c, label=l) for c, l in [(AI, "AI (statistics, k-NN, LLM)"), (QUANT, "Quantum"),
                                               (CLASS, "Exact classical"), (DATA, "Data and outputs")]]
    ax.legend(handles=hs, loc="upper left", bbox_to_anchor=(X[2] / FW, 0.995), ncol=1, fontsize=7.6, handlelength=1.1,
              columnspacing=1.2, handletextpad=0.5)
    return save(fig, "f3_pipeline.png")


# ------------------------------------------------------------------ 5 circuit (Qiskit standard notation) + schedule
def circuit():
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    from qiskit.circuit import Gate, Parameter

    names = ["VIC", "VHM", "FPT", "HPG"]
    regs = [QuantumRegister(1, n) for n in names]
    qc = QuantumCircuit(*regs, ClassicalRegister(4, "c"))
    q = [r[0] for r in regs]
    g = Parameter("γ")
    for k in range(4):
        qc.append(Gate("ry", 1, [], label=f"RY{k + 1}_____"), [q[k]])
    qc.barrier()
    for i, j in [(0, 1), (2, 3), (1, 2)]:
        qc.rzz(2 * g, q[i], q[j])
    qc.barrier()
    for k in range(4):
        qc.rz(2 * g, q[k])
    for k in range(4):
        qc.append(Gate("um", 1, [], label="UMIX____"), [q[k]])
    qc.barrier()
    qc.measure(q, range(4))

    res = json.loads((RUN / "circuits" / "resources.json").read_text())
    spec, ang = res["spec"], np.array(res["angles"])
    p = spec["layers"]
    fig = plt.figure(figsize=(12.0, 4.0))
    ax = fig.add_axes([0.0, 0.0, 0.66, 0.88])
    qc.draw("mpl", ax=ax, initial_state=True, plot_barriers=False, cregbundle=True, style={
        "name": "iqp", "fontsize": 13, "subfontsize": 11, "linecolor": "#334155",
        "displaycolor": {"ry": (CLASS, "#FFFFFF"), "rz": (QUANT, "#FFFFFF"), "rzz": (QUANT, "#FFFFFF"),
                         "um": (AGQO, "#FFFFFF"), "measure": ("#475569", "#FFFFFF")}})
    xs = {}
    for t in ax.texts:
        s = t.get_text()
        if s.startswith("RY"):
            t.set_text(rf"$R_Y(\theta_{s[2]})$")
            t.set_fontsize(10)
            xs.setdefault("ry", t.get_position()[0])
        elif "ZZ" in s:
            t.set_text(r"$R_{ZZ}(2\gamma_{\ell}\,J_{ij})$")
            t.set_fontsize(9.5)
            xs.setdefault("zz", t.get_position()[0])
        elif s == "2*γ":
            t.set_text(r"$2\gamma h_k$")
            t.set_fontsize(8.5)
        elif s.endswith("R_Z}$"):
            xs["rz"] = t.get_position()[0]
        elif s.startswith("UMIX"):
            t.set_text(r"$U_M(\beta_\ell)$")
            t.set_fontsize(10.5)
            xs["um"] = t.get_position()[0]
        elif s == "0" and t.get_position()[1] < -3.5:
            xs["meas"] = t.get_position()[0]
    x0, x1 = xs["zz"] - 1.25, xs["um"] + 0.72
    ax.add_patch(FancyBboxPatch((x0, -3.55), x1 - x0, 4.5, boxstyle="round,pad=0,rounding_size=0.25",
                                facecolor="#F5F3FF", edgecolor=QUANT, linewidth=1.4, linestyle="--", zorder=0))
    ax.text((x0 + x1) / 2, 1.2, f"QAOA layer ℓ, repeated p = {p} times", ha="center", fontsize=11, color=QUANT,
            weight="bold")
    ax.text((x0 + xs["rz"] + 0.5) / 2, 0.6, r"Cost $U_C(\gamma_\ell)$", ha="center", fontsize=10, color=QUANT)
    ax.text(xs["um"] - 0.3, 0.6, r"Mixer $U_M(\beta_\ell)$", ha="center", fontsize=10, color=AGQO)
    ax.text(xs["ry"], 1.2, "Warm start", ha="center", fontsize=10.5, color=CLASS, weight="bold")
    ax.text(xs["meas"] + 1.5, 1.2, "512 shots", ha="center", fontsize=10.5, color="#475569", weight="bold")
    ax.set_ylim(-4.6, 1.6)
    fig.text(0.01, 0.97, "AGQO circuit, one layer (4 of 16 qubits shown)", fontsize=12.5, weight="bold", color=INK,
             va="top")
    a2 = fig.add_axes([0.73, 0.14, 0.26, 0.68])
    lay = np.arange(1, p + 1)
    k = (np.arange(p) + 0.5) / p
    db = spec["ramp_dbeta"] or spec["ramp_dt"]
    a2.plot(lay, spec["ramp_dt"] * k, "--", color=QUANT, lw=1.3, alpha=0.6)
    a2.plot(lay, db * (1 - k), "--", color=AGQO, lw=1.3, alpha=0.6)
    a2.plot(lay, ang[:p], "o-", color=QUANT, lw=2.4, label=r"$\gamma_\ell$ (cost)")
    a2.plot(lay, ang[p:], "s-", color=AGQO, lw=2.4, label=r"$\beta_\ell$ (mixer)")
    a2.text(p + 0.05, spec["ramp_dt"] * k[-1], "Linear-ramp start", fontsize=8, color=MUTED, va="center")
    a2.set_xlim(0.6, p + 1.9)
    a2.set_xticks(lay)
    a2.set_xlabel("Layer ℓ")
    a2.set_ylabel("Angle (rad)")
    a2.legend(fontsize=9.5, loc="upper left")
    a2.set_title("Angles after COBYLA polish (2026-10-01)", fontsize=11)
    return save(fig, "f5_circuit.png")


# ------------------------------------------------------------------ data charts, drawn at their printed size
# Each canvas is the width it gets in the report (inches), so 7 pt here is 7 pt on paper. Titles state the finding.
SMALL = {"font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
         "legend.fontsize": 6.5, "axes.linewidth": 0.6, "grid.linewidth": 0.5, "savefig.dpi": 300}


def small(fn):
    def wrap():
        with plt.rc_context(SMALL):
            return fn()
    wrap.__name__ = fn.__name__
    return wrap


@small
def lot_cost():
    from agqo.data import MarketData
    from agqo.extras import load_config

    md, ec = MarketData.load(), load_config(RUN)
    d = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
    uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
    pct = (100 * 100 * md.px.loc[d, uni] / 20e6).sort_values(ascending=False)
    n10 = int((pct > 10).sum())
    fig, ax = plt.subplots(figsize=(3.1, 1.4))
    cols = [WARN if v > 100 else AMBER if v > 10 else GREEDY for v in pct]
    ax.bar(range(len(pct)), pct.values, color=cols, width=0.75)
    ax.axhline(100, color=WARN, ls="--", lw=0.8)
    ax.axhline(10, color=AMBER, ls=":", lw=0.8)
    ax.text(len(pct) - 0.5, 103, "= Whole account", color=WARN, ha="right", fontsize=6.3)
    ax.text(len(pct) - 0.5, 13, "10%", color=AMBER, ha="right", fontsize=6.3)
    ax.text(1.2, 104, "VIC: 1 lot = 110%", color=WARN, fontsize=6.6, weight="bold")
    ax.text(len(pct) * 0.42, 62, f"{n10}/{len(pct)} stocks: 1 lot > 10%\nof the account", color=AMBER, fontsize=6.6,
            weight="bold", ha="left")
    ax.set_xticks(range(len(pct)), pct.index, rotation=90, fontsize=4.8)
    ax.set_ylabel("Cost of 1 lot, % of account")
    ax.set_ylim(0, 122)
    ax.set_xlim(-0.7, len(pct) - 0.3)
    ax.grid(axis="x", visible=False)
    ax.set_title("A 20M VND account cannot buy most of VN30", loc="left")
    return save(fig, "f1a_lot_cost.png")


@small
def one_decision():
    ex = json.loads((RUN / "extras" / "examples.json").read_text())["20000000"]
    te = ex["te"]
    cash = {k: 100 * (1 - sum(ex[k])) for k in ("continuous", "practitioner", "greedy", "agqo")}
    g = np.array(ex["greedy"]) * 100
    top = ex["tickers"][int(np.argmax(g))]
    rows = [("Ideal fractional\n(not tradable)", te["continuous"], IDEAL, ""),
            ("Nearest-lot\nrounding", te["practitioner"], ROUND, f"{cash['practitioner']:.0f}% cash idle"),
            ("Greedy", te["greedy"], GREEDY, f"{g.max():.0f}% in {top}"),
            ("AGQO", te["agqo"], AGQO, "= exact whole-lot optimum")]
    fig, ax = plt.subplots(figsize=(3.3, 1.4))
    y = np.arange(len(rows))[::-1]
    for yi, (lab, v, c, note) in zip(y, rows):
        ax.barh(yi, v, color=c, height=0.62)
        ax.text(v + 0.3, yi, f"{v:.1f}%", va="center", fontsize=7, weight="bold", color=AGQO if lab == "AGQO" else INK)
        if note:
            ax.text(v + 5.2, yi, note, va="center", fontsize=6.2, color=MUTED, style="italic")
    ax.set_yticks(y, [r[0] for r in rows])
    ax.get_yticklabels()[-1].set_color(AGQO)
    ax.get_yticklabels()[-1].set_weight("bold")
    ax.set_xlim(0, max(r[1] for r in rows) * 2.05)
    ax.set_xlabel("Expected tracking error vs VN30 (annualised), lower is better")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Same account, four ways to buy lots ({ex['date']})", loc="left")
    return save(fig, "f1b_one_decision.png")


@small
def market():
    ins = pd.DataFrame(json.loads((RUN / "insight.json").read_text()))
    fig, ax = plt.subplots(figsize=(3.9, 1.35))
    x = np.arange(len(ins))
    ax.bar(x, ins.effective_bets, color=AGQO_L, width=0.62, label="Effective number of bets (left)")
    for i, v in enumerate(ins.effective_bets):
        ax.text(i, 0.8, f"{v:.0f}", ha="center", fontsize=6, color=INK, weight="bold")
    ax.set_ylabel("Effective bets")
    ax.set_ylim(0, 24)
    ax.set_xticks(x, [f"Q{(int(d[5:7]) - 1) // 3 + 1}/{d[2:4]}" for d in ins.date], fontsize=6)
    a2 = ax.twinx()
    a2.plot(x, 100 * ins.market_factor_share, "o-", color=QUANT, lw=1.3, ms=3,
            label="Market factor, % of variance (right)")
    a2.set_ylabel("Market factor, %", color=QUANT)
    a2.set_ylim(0, 100)
    a2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2, fontsize=6)
    ax.grid(axis="x", visible=False)
    ax.set_title("30 stocks behave like ~13 independent bets", loc="left")
    return save(fig, "f2_market.png")


BINS = ["optimal", "within 5%", "5–25%", "25–100%", "worse than typical", "over budget"]
BIN_EN = ["Optimal", "Within 5%", "5–25%", "25–100%", "Worse than median", "Over budget"]
BIN_COL = ["#15803D", "#4ADE80", "#FDE047", "#FB923C", "#F43F5E", "#CBD5E1"]


@small
def prob_flow():
    d = pd.read_csv(RUN / "extras" / "distributions.csv")
    order = ["random guessing", "warm start only", "textbook QAOA", "AGQO"]
    lab = ["Random guessing", "Warm-start baseline", "Textbook QAOA", "AGQO circuit"]
    m = d.groupby("arm")[BINS].mean().reindex(order) * 100
    fig, ax = plt.subplots(figsize=(3.9, 1.45))
    left = np.zeros(len(m))
    for c, col, nm in zip(BINS, BIN_COL, BIN_EN):
        ax.barh(range(len(m)), m[c], left=left, color=col, height=0.66, label=nm, edgecolor="white", lw=0.4)
        for i, v in enumerate(m[c]):
            if v > 6:
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=6,
                        color="white" if col in ("#15803D", "#F43F5E") else INK, weight="bold")
        left += m[c].to_numpy()
    near = m["optimal"] + m["within 5%"]
    for i, v in enumerate(near):
        ax.text(101, i, f"{v:.1f}%", va="center", fontsize=6.5, weight="bold", color=GOOD)
    ax.text(101, len(m) - 0.35, "Near-optimal", fontsize=6, color=GOOD, va="bottom")
    ax.set_yticks(range(len(m)), lab)
    ax.get_yticklabels()[-1].set_color(AGQO)
    ax.get_yticklabels()[-1].set_weight("bold")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of measurement probability, %, mean of 12 test quarters")
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.32), fontsize=5.6, handlelength=1, columnspacing=0.8)
    ax.grid(False)
    ax.set_title("AGQO puts 1 in 5 shots near the best answer", loc="left")
    return save(fig, "f4_probability.png")


@small
def hardware():
    h = pd.read_csv(RUN / "extras" / "hardware.csv")
    ha = pd.read_csv(RUN / "extras" / "hardware_aware.csv")
    gm = h.groupby("circuit").mean(numeric_only=True)
    na = ha[ha.date.isin(h.date)].mean(numeric_only=True)
    lab = ["Warm\nstart", "Text-\nbook", "AGQO\np=6", "AGQO\np=2"]
    rows = [gm.loc["warm start only"], gm.loc["textbook QAOA"], gm.loc["AGQO (chosen schedule)"]]
    two = [r.native_2q for r in rows] + [na.native_2q]
    ideal = [r.ideal_success for r in rows] + [na.ideal_success]
    noisy = [r.esp_model_success for r in rows] + [na.esp_fit * na.ideal_success + (1 - na.esp_fit) * na.uniform]
    cols = [GREEDY, ROUND, WARN, AGQO]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(3.8, 1.55), gridspec_kw={"wspace": 0.55})
    x = np.arange(4)
    a1.bar(x, np.maximum(two, 1), color=cols, width=0.62)
    for i, v in enumerate(two):
        a1.text(i, max(v, 1) * 1.5, f"{v:,.0f}", ha="center", fontsize=6.2, color=INK)
    a1.set_yscale("log")
    a1.set_ylim(0.6, 1e5)
    a1.set_ylabel("2-qubit gates on IBM Heron")
    a1.set_xticks(x, lab, fontsize=5.8)
    a1.grid(axis="x", visible=False)
    a1.set_title("Gate cost", loc="left")
    a2.bar(x - 0.19, 100 * np.array(ideal), 0.36, color="#E2E8F0", edgecolor=MUTED, lw=0.5, label="Noiseless")
    a2.bar(x + 0.19, 100 * np.array(noisy), 0.36, color=cols, label="With noise")
    a2.set_xticks(x, lab, fontsize=5.8)
    a2.set_ylabel("Near-optimal shots, %")
    a2.legend(fontsize=5.8, loc="upper left")
    a2.grid(axis="x", visible=False)
    a2.set_title("Noise erases the deep circuit", loc="left")
    return save(fig, "f6_hardware.png")


@small
def accounts():
    rb = pd.read_csv(RUN / "extras" / "robustness.csv")
    b = rb[rb.scenario.str.startswith("base")].set_index("capital_vnd")
    fig, ax = plt.subplots(figsize=(3.0, 1.75))
    x = np.arange(len(b))
    for off, k, c, nm in [(-0.27, "te_practitioner", ROUND, "Nearest-lot rounding"), (0, "te_greedy", GREEDY, "Greedy"),
                          (0.27, "te_whole_lot_optimum", AGQO, "AGQO")]:
        ax.bar(x + off, b[k], 0.26, color=c, label=nm)
        for i, v in enumerate(b[k]):
            ax.text(x[i] + off, v + 0.25, f"{v:.1f}", ha="center", fontsize=6.2, color=AGQO if "optimum" in k else INK,
                    weight="bold" if "optimum" in k else None)
    ax.set_xticks(x, [f"{c / 1e6:.0f}M VND account" for c in b.index])
    ax.set_ylabel("Realised TE vs VN30, %")
    ax.set_ylim(0, b.te_practitioner.max() * 1.55)
    ax.legend(ncol=3, loc="upper center", fontsize=5.8, handlelength=1, columnspacing=0.8)
    r20 = b.loc[20e6]
    ax.text(0.62, r20.te_practitioner * 0.95, f"−{-r20.diff_pp:.1f} pp\n95% CI {r20.ci_low:.1f} to {r20.ci_high:.1f}",
            color=GOOD, fontsize=6.3, weight="bold", va="top")
    ax.grid(axis="x", visible=False)
    ax.set_title("Small accounts gain most", loc="left")
    return save(fig, "f8a_accounts.png")


@small
def scaling():
    s = pd.read_csv(RUN / "extras" / "scaling.csv")
    g = s.groupby("qubits").mean(numeric_only=True)
    r = g.frozen_success / g.warm_success
    fig, a1 = plt.subplots(figsize=(3.4, 1.75))
    x = np.arange(len(g))
    a1.bar(x - 0.2, 100 * g.frozen_success, 0.38, color=AGQO, label="AGQO circuit (2023 schedule, unchanged)")
    a1.bar(x + 0.2, 100 * g.warm_success, 0.38, color=ROUND, label="Warm-start baseline")
    for i, (v, w) in enumerate(zip(100 * g.frozen_success, 100 * g.warm_success)):
        a1.text(i - 0.2, v * 1.15, f"{v:.0f}%", ha="center", fontsize=6, color=AGQO, weight="bold")
        a1.text(i + 0.2, w * 1.15, f"{w:.1f}%", ha="center", fontsize=6, color=MUTED)
        a1.text(i, 200, f"{r.iloc[i]:.1f}×", ha="center", va="center", fontsize=7, color="white", weight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=AMBER, edgecolor="none"))
    a1.set_yscale("log")
    a1.set_ylim(0.3, 420)
    a1.set_yticks([1, 10, 100], ["1%", "10%", "100%"])
    a1.set_ylabel("Near-optimal shots (log)")
    a1.set_xticks(x, [f"{q} qubits\n{2 ** q:,} states" for q in g.index], fontsize=6)
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2, fontsize=5.8)
    a1.grid(axis="x", visible=False)
    a1.set_title("The edge over warm start grows with size (×)", loc="left")
    return save(fig, "f8b_scaling.png")


ALL = [lot_cost, one_decision, market, pipeline, prob_flow, circuit, hardware, accounts, scaling]

if __name__ == "__main__":
    for f in ALL:
        print(f())
