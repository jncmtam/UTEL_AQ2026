"""Print figures for the report (white background, English labels) from the same data as the deck.

    python submission/deck/figures.py          # -> submission/deck/figures/*.png (+ the deck theme colours)

Change a label or colour here (or in theme.json) and rerun; the data stay in data/*.csv.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "figures"
TH = json.loads((HERE / "theme.json").read_text())
L, SL, SEM = TH["light"], TH["series_light"], TH["semantic"]
c = lambda h: "#" + h
plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.edgecolor": c(L["line"]), "axes.labelcolor": c(L["text"]),
                     "xtick.color": c(L["muted"]), "ytick.color": c(L["muted"]), "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": c(L["grid"]), "grid.linewidth": 0.6,
                     "axes.axisbelow": True, "figure.dpi": 200, "savefig.bbox": "tight"})


def f1_lot():
    d = pd.read_csv(DATA / "c1_lot_cost.csv")
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    col = [c(SEM["violation"]) if v > 100 else c(SEM["tradeoff"]) if v > 10 else c(SL["rounding"]) for v in d.lot_pct_of_20m]
    ax.bar(d.ticker, d.lot_pct_of_20m, color=col, width=0.75)
    ax.axhline(100, color=c(SEM["violation"]), ls="--", lw=1)
    ax.text(len(d) - 0.5, 103, "100% = whole account", ha="right", color=c(SEM["violation"]), fontsize=8)
    ax.set_ylabel("One board lot, % of 20M VND")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT / "f1_lot_cost.png")


def f3_pitch():
    w = pd.read_csv(DATA / "c3_pitch_weights.csv")
    kp = pd.read_csv(DATA / "c3_pitch_kpis.csv").set_index("method")
    order = ["Nearest-lot rounding", "Greedy lot filling", "AGQO"]
    held = sorted(set(w[(w.method.isin(order)) & (w.weight_pct > 0)].ticker))
    ideal = w[w.method == "Ideal (fractional shares)"].set_index("ticker").weight_pct
    held = sorted(held, key=lambda t: -ideal.get(t, 0))
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    x = range(len(held))
    cols = {"Nearest-lot rounding": c(SL["rounding"]), "Greedy lot filling": c(SL["greedy"]), "AGQO": c(SL["agqo"])}
    for k, m in enumerate(order):
        s = w[w.method == m].set_index("ticker").weight_pct
        ax.bar([i + (k - 1) * 0.26 for i in x], [s.get(t, 0) for t in held], width=0.26, color=cols[m],
               label=f"{m}: est. TE {kp.loc[m, 'estimated_te_pct']:.2f}%, {kp.loc[m, 'holdings']:.0f} stock{'s' if kp.loc[m, 'holdings'] != 1 else ''}")
    ax.scatter(list(x), [ideal.get(t, 0) for t in held], marker="_", s=180, color=c(L["text"]), label="Ideal (fractional shares)", zorder=3)
    ax.set_xticks(list(x), held)
    ax.set_ylabel("Weight, % of account")
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT / "f3_pitch_weights.png")


def f4_accounts():
    a = pd.read_csv(DATA / "c4_accounts.csv")
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    labels = [f"{int(v / 1e6)}M" for v in a.capital_vnd]
    for k, (col, lab, colour) in enumerate((("practitioner", "Nearest-lot rounding", SL["rounding"]),
                                             ("greedy", "Greedy lot filling", SL["greedy"]), ("agqo", "AGQO", SL["agqo"]))):
        xs = [i + (k - 1) * 0.26 for i in range(len(a))]
        ax.bar(xs, a[col], width=0.26, color=c(colour), label=lab)
        for xx, v in zip(xs, a[col]):
            ax.text(xx, v + 0.15, f"{v:.1f}", ha="center", fontsize=6.5, color=c(L["text"]))
    ax.set_xticks(range(len(a)), [l + " VND" for l in labels])
    ax.set_ylabel("Annualised tracking error, %")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT / "f4_accounts.png")


def f6_circuits():
    d = pd.read_csv(DATA / "c6_circuits.csv").set_index("arm2")
    order = ["textbook", "warm_start_only", "random_search", "agqo", "polish_ablation", "frozen"]
    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    col = [c(SL["agqo"]) if a == "agqo" else c(SL["exact"]) if a in ("frozen", "polish_ablation") else c(SL["rounding"]) for a in order]
    ax.barh([d.loc[a, "label"] for a in order], [d.loc[a, "success_pct"] for a in order], color=col)
    for i, a in enumerate(order):
        ax.text(d.loc[a, "success_pct"] + 0.4, i, f"{d.loc[a, 'success_pct']:.1f}%", va="center", fontsize=7.5)
    ax.set_xlabel("Near-optimal solution probability per shot, %")
    ax.set_xlim(0, 30)
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT / "f6_circuits.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for f in (f1_lot, f3_pitch, f4_accounts, f6_circuits):
        f()
    print(sorted(p.name for p in OUT.glob("*.png")))
