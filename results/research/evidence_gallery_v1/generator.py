"""Render English figures from saved evidence; never run inference or optimization."""

import argparse
from html import escape
import json
from pathlib import Path
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np

from agqo.research.data import sha, write_json
from agqo.research.qualification import reliability


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/research"
COLORS = {
    "clear": "#227c69",
    "review": "#d59835",
    "missing": "#be4c4c",
    "unrun": "#e4e9f0",
}


def load(relative):
    return json.loads((ROOT / relative).read_text())


def jsonlines(relative):
    return [json.loads(line) for line in (ROOT / relative).read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/research/evidence_gallery_v1")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError("Preserve existing figures; use a new output directory.")
    output.mkdir(parents=True)
    shutil.copyfile(__file__, output / "generator.py")
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    inputs = [
        "results/research/historical_audit_v3/audit.json",
        "results/research/tokenizer_preflight_v1/records.json",
        "results/research/tokenizer_preflight_v1/budget.json",
        "results/research/formulation_identity_v1/audit.json",
        "results/research/conditioning_control_v1/decisions.jsonl",
        "results/research/preparation_control_v1/decisions.jsonl",
        "results/research/independent_test_readiness_v1/BLOCKED.json",
        "results/research/delivery_structural_v1/circuits/development_n6/rules/0/gate_ir.json",
        "docs/research/QUALIFICATION_PROTOCOL.md",
        "docs/research/DELIVERY_VISUAL_PROTOCOL.md",
    ]
    cards = []

    def save(fig, name, title, caption, category):
        fig.savefig(output / (name + ".png"), dpi=160, bbox_inches="tight")
        fig.savefig(output / (name + ".svg"), bbox_inches="tight")
        plt.close(fig)
        cards.append(
            {"name": name, "title": title, "caption": caption, "category": category}
        )

    history = load(inputs[0])
    rows = history["rows"]
    # 0=missing/blocked, 1=numerically clear, 2=review, 3=not independently verified.
    matrix = []
    for row in rows:
        exists = "observations" in row
        numeric = exists and all(
            row.get(k, 1) == 0
            for k in [
                "invalid_price_rows",
                "ohlc_violations",
                "invalid_volume_rows",
                "duplicate_dates",
            ]
        )
        coverage = exists and all(
            p["missing_sessions"] == 0 for p in row["period_coverage"].values()
        )
        matrix.append(
            [
                1 if exists else 0,
                1 if coverage else 0,
                1 if numeric else 0,
                2
                if row.get("unclassified_noninteger_split_labels")
                else 3
                if exists
                else 0,
                3,
                3,
                3,
            ]
        )
    fig, ax = plt.subplots(figsize=(12, 12), layout="constrained")
    ax.imshow(
        matrix,
        cmap=ListedColormap(
            [COLORS["missing"], COLORS["clear"], COLORS["review"], COLORS["unrun"]]
        ),
        vmin=-0.5,
        vmax=3.5,
        aspect="auto",
    )
    ax.set(
        yticks=range(len(rows)),
        yticklabels=[r["ticker"] for r in rows],
        xticks=range(7),
        xticklabels=[
            "Source\npresent",
            "Period\ncoverage",
            "Numerical\nchecks",
            "Action\nreview",
            "Share-class\nidentity",
            "Full\nlineage",
            "Dated\nsector",
        ],
    )
    ax.tick_params(length=0)
    ax.set_title(
        "29 of 30 cohort stocks + DIA available; no complete lineage certified", pad=20
    )
    for y, line in enumerate(matrix):
        for x, value in enumerate(line):
            ax.text(
                x,
                y,
                {0: "missing", 1: "clear", 2: "flagged", 3: "unverified"}[value],
                ha="center",
                va="center",
                fontsize=9,
                color="white" if value in (0, 1) else "#26364a",
            )
    save(
        fig,
        "data-readiness",
        "Historical data: numerical hygiene versus investability",
        "Source/coverage/numerical columns are diagnostics only. Action labels flagged for review are not necessarily bad prices. All share-class, complete lineage and dated-sector reviews remain unverified; UTX is missing. DIA is an ETF proxy, not the official index.",
        "Data",
    )

    flagged = [r for r in rows if r.get("unclassified_noninteger_split_labels")]
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    bars = ax.bar(
        [r["ticker"] for r in flagged],
        [len(r["unclassified_noninteger_split_labels"]) for r in flagged],
        color=COLORS["review"],
    )
    ax.bar_label(bars, padding=4)
    ax.set(
        ylim=(0, 3.8),
        yticks=range(4),
        ylabel="Provider labels requiring classification",
        title="11 non-integer split labels across 7 securities",
    )
    save(
        fig,
        "action-review",
        "Provider adjustment factors need economic interpretation",
        "The vendor may encode a spin-off or other noncash adjustment as a split. For example, a 1.046 price factor is not 0.2 Kyndryl shares per IBM share. Primary event candidates remain a partial ledger; dividends and all other actions also need source reconciliation.",
        "Data",
    )

    tokens = load(inputs[1])
    labels = {
        "coder30": "Qwen Coder 30B",
        "mistral24q": "Qiskit Mistral 24B",
        "quasar4": "QUASAR 4B",
    }
    fig, ax = plt.subplots(figsize=(12, 3.6), layout="constrained")
    readiness = [[1, 1, 3, 3, 0], [1, 1, 3, 3, 0], [1, 1, 2, 3, 0]]
    ax.imshow(
        readiness,
        cmap=ListedColormap(
            [COLORS["missing"], COLORS["clear"], COLORS["review"], COLORS["unrun"]]
        ),
        vmin=-0.5,
        vmax=3.5,
        aspect="auto",
    )
    ax.set(
        yticks=range(3),
        yticklabels=[labels[r["key"]] for r in tokens],
        xticks=range(5),
        xticklabels=[
            "Artifact\ninventory",
            "CPU\ntokenizer",
            "Current native /\ntransfer probe",
            "72-case\nconfirmation",
            "Independent\nfinancial test",
        ],
    )
    words = [
        ["inspected", "passed", "unqualified", "unrun", "blocked"],
        ["inspected", "passed", "unrun", "unrun", "blocked"],
        ["inspected", "passed", "1/3 accepted", "unrun", "blocked"],
    ]
    for y in range(3):
        for x in range(5):
            ax.text(
                x,
                y,
                words[y][x],
                ha="center",
                va="center",
                color="white" if readiness[y][x] in (0, 1) else "#26364a",
                fontsize=10,
            )
    ax.set_title("Three tokenizer passes; zero production models qualified", pad=16)
    ax.tick_params(length=0)
    save(
        fig,
        "model-readiness",
        "Model selection has separate gates",
        "Artifact inspection and CPU chat rendering do not load model weights or test gate generation. QUASAR's completed interface probe accepted 1/3 tasks; older coder pilots are exploratory. The shortlist is provisional and no GPU sweep was added.",
        "Models",
    )

    n = np.arange(1, 73)
    # Exact all-success interval lower bound: Beta(alpha/2; n, 1).
    lower = np.power(0.025, 1 / n)
    fig, ax = plt.subplots(figsize=(10, 4.4), layout="constrained")
    ax.plot(
        n,
        lower * 100,
        color="#336d9d",
        lw=2.5,
        label="Exact two-sided 95% lower bound, all cases successful",
    )
    ax.axhline(95, ls="--", color=COLORS["review"], label="Required lower bound: 95%")
    ax.scatter([72], [lower[-1] * 100], color=COLORS["clear"], s=60, zorder=4)
    ax.annotate(
        f"72/72 target: {lower[-1]:.4%}",
        (72, lower[-1] * 100),
        xytext=(35, 83),
        arrowprops={"arrowstyle": "->"},
    )
    ax.set(
        xlim=(1, 75),
        ylim=(0, 101),
        xlabel="Independent confirmation cases (all successful)",
        ylabel="Lower confidence bound (%)",
        title="Protocol illustration only: no model has run this confirmation",
    )
    ax.legend(loc="lower right", fontsize=9)
    save(
        fig,
        "reliability-target",
        "Why a small successful pilot is insufficient",
        "A planning illustration, not observed model performance. The locked 72-case confirmation needs 72 first-pass successes for this criterion. Independence must be justified; task seeds are not independent market or semantic cases. Do not extend the set until it passes.",
        "Models",
    )

    formulas = load(inputs[3])["summaries"]
    fig, ax = plt.subplots(figsize=(10, 4.3), layout="constrained")
    x = np.arange(2)
    for offset, policy, color in [
        (-0.18, "continuous", "#336d9d"),
        (0.18, "equal_weight_target", "#227c69"),
    ]:
        values = [
            100
            * next(
                r["relative_regret"]
                for r in formulas
                if r["scenario"] == s and r["policy"] == policy
            )
            for s in ["base", "exclude_incumbent"]
        ]
        bars = ax.bar(
            x + offset, values, width=0.34, label=policy.replace("_", " "), color=color
        )
        ax.bar_label(bars, labels=[f"{v:.2f}%" for v in values], padding=5)
    ax.set(
        xticks=x,
        xticklabels=["Base mandate", "Exclude incumbent"],
        ylim=(0, 9),
        ylabel="Allocation regret of proxy-optimal support (%)",
        title="N10: optimizing selection energy B does not generally optimize allocation F",
    )
    ax.legend(loc="upper left")
    save(
        fig,
        "proxy-allocation-gap",
        "Formulation mismatch survives a better circuit",
        "Exhaustive opened-development support audit. The continuous objective has 3.32% / 7.13% regret at the proxy optimum. Equal-weight targets pass B=F identity but define a different financial mandate. These are training-objective diagnostics, not realized returns.",
        "Finance",
    )

    conditioned = jsonlines(inputs[4])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
    methods = ["raw", "paper_rms", "uniform_total_shots"]
    for ax, policy in zip(axes, ["continuous", "equal_weight_target"]):
        for pos, method in enumerate(methods):
            values = (
                np.array(
                    [
                        r["allocation"]["objective"]
                        for r in conditioned
                        if r["n"] == 30
                        and r["weight_policy"] == policy
                        and r["method"] == method
                    ]
                )
                * 1e6
            )
            ax.bar(
                pos,
                values.mean(),
                color=["#336d9d", "#227c69", "#91822c"][pos],
                alpha=0.8,
            )
            ax.scatter(
                pos + np.linspace(-0.06, 0.06, len(values)),
                values,
                color="#25364b",
                s=20,
                zorder=3,
            )
        ax.set(
            xticks=range(3),
            xticklabels=["Raw QAOA", "RMS QAOA", "Uniform\n2,176 draws"],
            ylabel="Allocated training objective ×10⁶",
            title=policy.replace("_", " "),
        )
        ax.set_ylim(bottom=0)
    fig.suptitle(
        "N30: lower is better; dots are three seeds, not independent market tests"
    )
    save(
        fig,
        "allocated-quality",
        "The classical control remains stronger",
        "Opened conditional US corpus, ideal simulation. RMS coordinates improve energy geometry but worsen the continuous allocated objective here. Uniform uses the maximum optimizer-plus-final draw allowance; quantum postprocessing used final samples only. This pooling difference is explicit and no runtime or significance win is claimed.",
        "Finance",
    )

    preparation = jsonlines(inputs[5])
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), layout="constrained")
    for ax, key, title in zip(
        axes,
        ["qubits", "transpiled_cx", "transpiled_depth"],
        ["Physical qubits", "Logical CX gates", "Logical depth"],
    ):
        values = [
            next(
                r["verification"]["resources"][key]
                for r in preparation
                if r["n"] == 30 and r["method"] == method
            )
            for method in ["three_pair", "counter_dicke"]
        ]
        bars = ax.bar(["Sparse", "Counter-Dicke"], values, color=["#336d9d", "#227c69"])
        ax.bar_label(bars, padding=4)
        ax.set(title=title, ylim=(0, max(values) * 1.22))
    fig.suptitle("Broader support coverage has a measured circuit cost")
    save(
        fig,
        "preparation-cost",
        "Coverage alone does not establish utility",
        "Counter-Dicke reaches all 593,775 N30/K6 supports, using 33 physical qubits, 1,798 CX and depth 2,428. Workspace and cost compilation are counted. Counts assume all-to-all logical connectivity. No physical-device execution or full N33 Qiskit statevector validation is claimed.",
        "Quantum",
    )

    gate_ir = load(inputs[7])
    gates = gate_ir["layers"][0]["mixer"]
    fig, ax = plt.subplots(figsize=(13, 4.8), layout="constrained")
    for q in range(6):
        ax.plot([-1, len(gates)], [q, q], color="#a9b6c6", lw=1)
        ax.text(-1.1, q, f"asset q{q}", ha="right", va="center")
    for position, gate in enumerate(gates):
        lo, hi = sorted(gate["qubits"])
        ax.plot([position, position], [lo, hi], color="#336d9d", lw=2)
        for q in [lo, hi]:
            ax.add_patch(
                Rectangle(
                    (position - 0.4, q - 0.3),
                    0.8,
                    0.6,
                    facecolor="#edf4fa",
                    edgecolor="#336d9d",
                    zorder=3,
                )
            )
            ax.text(
                position, q, gate["op"], fontsize=8, va="center", ha="center", zorder=4
            )
    ax.set(
        xlim=(-2.3, len(gates)),
        ylim=(5.8, -1.1),
        title="Actual N6 rule-control mixer excerpt: paired RXX / RYY exchange gates",
    )
    ax.axis("off")
    save(
        fig,
        "mixer-gates",
        "What circuit design changes",
        "Drawn from the saved verified rule-control GateIR, not an LLM-generated success. Only the first asset-register mixer is shown; preparation, immutable compiler-owned COST, slack and measurement are omitted. Each RXX/RYY pair shares its angle; a lone RXX does not preserve cardinality.",
        "Quantum",
    )

    records = [
        {
            "problem_hash": f"planning-{i}",
            "split": "confirmation",
            "execution_status": "executed",
            "first_pass_valid": True,
        }
        for i in range(72)
    ]
    summary = {
        "source_files_present": sum("observations" in r for r in rows),
        "cohort_stocks_present": sum(
            "observations" in r and r["ticker"] != "DIA" for r in rows
        ),
        "missing_tickers": [r["ticker"] for r in rows if r["status"] == "missing"],
        "provider_dividends": sum(r.get("provider_dividends", 0) for r in rows),
        "provider_split_labels": sum(r.get("provider_splits", 0) for r in rows),
        "unclassified_split_labels": sum(
            len(r.get("unclassified_noninteger_split_labels", [])) for r in rows
        ),
        "cash_checks": sum(r.get("cash_adjustment_checks", 0) for r in rows),
        "cash_residual_flags": sum(
            r.get("cash_adjustment_residual_above_5e_minus_5", 0) for r in rows
        ),
        "tokenizer_passes": sum(r["status"] == "tokenizer_ready_only" for r in tokens),
        "cpu_preflight_reservation_usd_not_invoice": sum(
            j["reserved_usd"] for j in load(inputs[2])["jobs"]
        ),
        "confirmation_illustration_only": reliability(records),
        "final_test_status": load(inputs[6])["status"],
        "new_model_inference_calls": 0,
        "new_optimization_calls": 0,
        "new_strategy_outcomes_opened": False,
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "input_sha256": {p: sha(ROOT / p) for p in inputs},
            "generator_sha256": sha(__file__),
            "figures": cards,
            "scope": "Descriptive evidence and explicitly labeled protocol illustrations only.",
        },
    )
    lines = [
        "# Evidence gallery",
        "",
        "English visual guide to recorded evidence. No new model inference, optimization or strategy outcomes.",
        "",
    ]
    for card in cards:
        lines += [
            f"## {card['title']}",
            "",
            f"![{card['title']}]({card['name']}.png)",
            "",
            card["caption"],
            "",
        ]
    (output / "GALLERY.md").write_text("\n".join(lines))
    sections = "".join(
        f'<article data-category="{c["category"]}"><p class="tag">{c["category"]}</p><h2>{escape(c["title"])}</h2><a href="{c["name"]}.svg"><img src="{c["name"]}.png" alt="{escape(c["title"])}" loading="lazy"></a><p>{escape(c["caption"])}</p></article>'
        for c in cards
    )
    (output / "index.html").write_text(
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AGQO | Evidence gallery</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f2f5f8;color:#21354b;font:17px/1.6 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:36px 24px}h1{font-size:clamp(30px,5vw,54px);line-height:1.1}h2{font-size:26px;line-height:1.25}.lead{max-width:850px}.status{padding:18px 22px;border-left:5px solid #d59835;background:#fff3d7}nav{display:flex;gap:10px;flex-wrap:wrap;margin:28px 0}button{background:white;border:1px solid #a9b6c6;border-radius:8px;padding:10px 20px;font:inherit;cursor:pointer}button[aria-pressed=true]{background:#21354b;color:white}article{background:white;padding:26px;border-radius:14px;margin:24px 0;box-shadow:0 3px 15px #21354b0a}img{width:100%;height:auto}.tag{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#227c69;font-weight:700}a{color:#235e8f}footer{font-size:14px;margin:35px 0}[hidden]{display:none}</style>
<main><p class="tag">AGQO / research evidence / 2026-11-04</p><h1>What works, what is measured,<br>what still blocks the claim.</h1><p class="lead">A visual audit of historical data, circuit design and model readiness. Every measured figure comes from saved artifacts. Reliability targets are labeled as planning illustrations.</p><div class="status"><strong>Financial evaluation remains blocked.</strong> No production LLM, investment outperformance or quantum advantage is qualified.</div><nav aria-label="Filter evidence">"""
        + "".join(
            f'<button type="button" aria-pressed="{str(c == "All").lower()}" data-filter="{c}">{c}</button>'
            for c in ["All", "Data", "Models", "Finance", "Quantum"]
        )
        + """</nav>"""
        + sections
        + """<footer>Click a figure for its vector original. <a href="manifest.json">Source checksums</a> · <a href="summary.json">Machine-readable summary</a> · <a href="GALLERY.md">Markdown version</a><p>This gallery reads local saved artifacts only. It cannot launch a model or execute a trade.</p></footer></main><script>document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('article').forEach(a=>a.hidden=button.dataset.filter!=='All'&&a.dataset.category!==button.dataset.filter)}));</script></html>"""
    )
    print(output)


if __name__ == "__main__":
    main()
