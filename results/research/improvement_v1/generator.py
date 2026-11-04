"""Audit and explain frozen improvement controls without new search or inference."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from agqo.research.data import sha, write_json


def main():
    path = Path("results/research/improvement_v1")
    if (path / "RESULTS.md").exists():
        raise ValueError("Preserve the completed derived report.")
    expected = json.loads((path / "orchestration/download_manifest.json").read_text())
    for name, checksum in expected.items():
        assert sha(path / name) == checksum, name
    records = json.loads((path / "records.json").read_text())
    ablation = json.loads((path / "ablation.json").read_text())
    frame = pd.read_csv(path / "metrics.csv")
    assert len(records) == 168 and len(frame) == 672
    maximum_residual, allocations = 0.0, 0
    for record in records:
        sufficient = json.loads(
            (
                path / "cases" / record["case_id"] / "sufficient_statistics.json"
            ).read_text()
        )
        matrix, linear = (
            np.asarray(sufficient["matrix"]),
            np.asarray(sufficient["linear"]),
        )
        spec = sufficient["financial_spec_without_returns"]
        result = record["result"]
        assert result["total_observations"] == 88 and len(result["observations"]) == 88
        for observation in result["observations"]:
            index = observation["support_index"]
            assert int(index).bit_count() == spec["k"]
            for ticker in spec["include"]:
                assert index & (1 << spec["tickers"].index(ticker))
            for ticker in spec["exclude"]:
                assert not index & (1 << spec["tickers"].index(ticker))
        for allocation in result["allocation_results"].values():
            if not allocation.get("feasible"):
                continue
            w = np.asarray(allocation["weights"])
            value = float(
                w @ matrix @ w
                + linear @ w
                + sufficient["offset"]
                + spec["cost_weight"]
                * spec["cost_rate"]
                * abs(w - np.asarray(spec["previous_weights"])).sum()
            )
            residual = abs(value - allocation["objective"])
            assert residual < 1e-10
            maximum_residual = max(maximum_residual, residual)
            allocations += 1
    final = frame[(frame.n == 20) & (frame.draws == 88)]
    keys = ["case_id", "seed"]
    uniform = final[final.method == "uniform_conditioned"][
        keys + ["best_objective"]
    ].rename(columns={"best_objective": "uniform"})
    swap = final[final.method == "allocation_swap"][keys + ["best_objective"]].rename(
        columns={"best_objective": "swap"}
    )
    fixed = final[final.method == "fixed"][keys + ["best_objective"]].rename(
        columns={"best_objective": "fixed"}
    )
    paired = final.merge(uniform, on=keys).merge(swap, on=keys).merge(fixed, on=keys)
    paired["relative_to_uniform_pct"] = 100 * (
        paired.best_objective / paired.uniform - 1
    )
    paired["relative_to_swap_pct"] = 100 * (paired.best_objective / paired.swap - 1)
    paired["relative_to_fixed_pct"] = 100 * (paired.best_objective / paired.fixed - 1)
    summaries = []
    for method, group in paired.groupby("method"):
        difference = group.best_objective - group.uniform
        summaries.append(
            {
                "method": method,
                "pairs": len(group),
                "mean_vs_uniform_pct": float(group.relative_to_uniform_pct.mean()),
                "median_vs_uniform_pct": float(group.relative_to_uniform_pct.median()),
                "mean_vs_swap_pct": float(group.relative_to_swap_pct.mean()),
                "mean_vs_fixed_pct": float(group.relative_to_fixed_pct.mean()),
                "wins_ties_losses_vs_uniform": [
                    int((difference < -1e-10).sum()),
                    int((abs(difference) <= 1e-10).sum()),
                    int((difference > 1e-10).sum()),
                ],
                "feasible_rows": int(group.best_objective.notna().sum()),
            }
        )
    write_json(
        path / "analysis.json",
        {
            "n20_final": summaries,
            "audited_files": len(expected),
            "audited_feasible_allocations": allocations,
            "max_objective_residual": maximum_residual,
            "new_inference_or_search_calls": 0,
        },
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), layout="constrained")
    reduced = [r for r in ablation if r["method"] == "depth1_scheduled_edit"]
    x = np.arange(len(reduced))
    for ax, metric, title in zip(
        axes, ["transpiled_cx", "transpiled_depth"], ["Logical CX", "Logical depth"]
    ):
        a = [r["original_resources"][metric] for r in reduced]
        b = [r["verification"]["resources"][metric] for r in reduced]
        for offset, values, label, color in [
            (-0.18, a, "Original LLM", "#8c659d"),
            (0.18, b, "Classical edit + schedule", "#2b8976"),
        ]:
            bars = ax.bar(x + offset, values, 0.35, label=label, color=color)
            ax.bar_label(bars, fontsize=9, padding=3)
        ax.set(xticks=x, xticklabels=[r["case_id"] for r in reduced], title=title)
        ax.set_ylim(0, max(a) * 1.25)
        ax.legend(fontsize=8)
    fig.suptitle("Opened synthetic control: identical selected F in all 12 edited runs")
    fig.savefig(path / "resource-improvement.png", dpi=160)
    plt.close(fig)
    methods = [
        "fixed",
        "rules",
        "scheduled",
        "depth2_pattern",
        "proxy_feedback",
        "uniform_conditioned",
        "allocation_swap",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for ax, case in zip(axes.flat, frame[frame.n == 20].case_id.unique()):
        for method in methods:
            group = frame[(frame.case_id == case) & (frame.method == method)]
            mean = group.groupby("draws").best_objective.mean() * 1e6
            ax.plot(mean.index, mean.values, marker="o", markersize=3, label=method)
        ax.set(
            title=case,
            xlabel="Observed supports (all optimizer/final draws)",
            ylabel="Best allocated training objective ×10⁶",
        )
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, fontsize=9)
    fig.suptitle(
        "N20/K5: limited-budget quality; means across three seeds, no significance claim"
    )
    fig.savefig(path / "budget-curves.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    averages = paired.groupby("method").relative_to_uniform_pct.mean().reindex(methods)
    bars = ax.bar(
        averages.index,
        averages.values,
        color=[
            "#527c9d",
            "#58a192",
            "#277b62",
            "#94709b",
            "#c69c42",
            "#87929f",
            "#b15c4c",
        ],
    )
    ax.bar_label(bars, fmt="%.2f%%", padding=3)
    ax.axhline(0, color="#26384d", lw=1)
    ax.tick_params(axis="x", rotation=20)
    ax.set(
        ylabel="Mean paired objective difference (%)\nnegative is better",
        title="88 observations: conditioned uniform is a strong comparator",
    )
    fig.savefig(path / "conditioned-comparison.png", dpi=160)
    plt.close(fig)
    resource_rows = []
    for r in reduced:
        old, new = r["original_resources"], r["verification"]["resources"]
        resource_rows.append(
            {
                "case": r["case_id"],
                "old_cx": old["transpiled_cx"],
                "new_cx": new["transpiled_cx"],
                "cx_reduction": 1 - new["transpiled_cx"] / old["transpiled_cx"],
                "old_depth": old["transpiled_depth"],
                "new_depth": new["transpiled_depth"],
                "depth_reduction": 1
                - new["transpiled_depth"] / old["transpiled_depth"],
                "quality_unchanged": all(
                    abs(run["allocation"]["objective"] - original) < 1e-10
                    for run, original in zip(
                        r["runs"], r["original_objectives"], strict=True
                    )
                ),
            }
        )
    cost = json.loads((path / "orchestration/budget.json").read_text())
    lines = [
        "# Improvement results and technical decisions",
        "",
        "Date: 2026-11-04. Development controls; no new LLM inference or investment-performance claim.",
        "",
        "## Concrete circuit improvement",
        "",
        "| Opened case | CX before → after | CX reduction | Depth before → after | Depth reduction | Same selected F? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in resource_rows:
        lines.append(
            f"| {r['case']} | {r['old_cx']} → {r['new_cx']} | {r['cx_reduction']:.1%} | {r['old_depth']} → {r['new_depth']} | {r['depth_reduction']:.1%} | {r['quality_unchanged']} |"
        )
    lines += [
        "",
        "Removing the extra layer reduces both gates and parameters. Greedy edge coloring groups disjoint exchanges, reducing the scheduled critical path. This changes the unitary, so every edit was independently verified and refitted. Attribution is deterministic classical postprocessing of saved LLM proposals, not improved LLM reasoning. These are opened synthetic cases, not an independent non-inferiority study.",
        "",
        "![Circuit improvement](resource-improvement.png)",
        "",
        "**Figure 1. Verified resource reductions.** Source: ablation.json. Full compiler-owned cost and counter-Dicke preparation are counted. All12 edited runs retained the original selected F within tolerance; hardware noise/routing are not measured.",
        "",
        "## Benchmark now distinguishes methods",
        "",
        "Two disjoint20-stock families from pinned US returns, N12/K3 and N20/K5, base/exclusion mandates, three seeds and seven methods produce168 runs and672 prefix rows. N20 base has15,504 supports; exclusion has11,628. Only first126 estimation rows were used. Full-year membership conditioning and artificial policy buckets prevent an unbiased historical financial claim.",
        "",
        "![Budget curves](budget-curves.png)",
        "",
        "**Figure 2. Allocated quality versus budget.** Source: metrics.csv. Lower is better. All optimizer/final observations count. Families, nested sizes, mandates and seeds are related; these are descriptive training curves, not independent market confidence intervals.",
        "",
        "| N20 method,88 observations | Mean vs conditioned uniform | Median vs uniform | Mean vs local swap | Wins/ties/losses vs uniform |",
        "|---|---:|---:|---:|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['method']} | {s['mean_vs_uniform_pct']:+.2f}% | {s['median_vs_uniform_pct']:+.2f}% | {s['mean_vs_swap_pct']:+.2f}% | {s['wins_ties_losses_vs_uniform']} |"
        )
    lines += [
        "",
        "Positive differences mean a worse allocated training objective, not a loss in realized investment returns. Each N20 method has12 case/seed pairs, with dependencies. Uniform now respects includes/excludes and cardinality; there is no artificial forbidden-stock feasibility advantage.",
        "",
        "![Conditioned comparison](conditioned-comparison.png)",
        "",
        "**Figure 3. Stronger comparator reveals the remaining gap.** Source: paired metrics at88 observations. Negative means better than conditioned uniform. No significance or out-of-sample financial effect is asserted.",
        "",
        "## What to keep and what to change",
        "",
        "1. Keep one-layer resource eligibility and disjoint scheduling as explicit tested controls. The new cost-aware request API requires one layer and measured qubit/CX/depth budgets; verifier-backed admission, not prompt text, enforces resource eligibility. No new model generated a proposal under that contract in this study.",
        "2. Keep conditioned uniform and allocation-aware local search as strong references. The original integration's tied optimum score was a ceiling effect; these budget curves are more discriminating.",
        "3. Circuit scheduling can change the quality/resource frontier, but the current circuit family does not establish a better overall solution than strong classical search. More depth is not an earned default.",
        "4. Mean allocated-F feedback and proxy feedback must be compared empirically. Direct F feedback aligns the scoring units but does not guarantee a better sampled portfolio; noisy low-budget fitting and circuit expressiveness remain unresolved.",
        "5. Do not scale the LLM from this evidence. The next formulation/optimizer study must explain why the quantum sampler should improve useful-tail probability under matched total cost. Historical source reconstruction remains required before any investment test.",
        "",
        "## Accounting and verification",
        "",
        f"- All{len(expected)} downloaded files hash-checked;{allocations} feasible allocations independently rescored from sufficient statistics; max objective residual{maximum_residual:.3g}.",
        f"- Conservative CPU reservation USD{sum(j['reserved_usd'] for j in cost['jobs']):.6f}; not an invoice. No GPU/model inference used.",
        "- Quantum simulation uses the conserved subspace, crosschecked against the full executor on small instances. Large physical registers use the existing analytic certificate; no full N23 Qiskit statevector validation is claimed.",
        "- SCIP references have their actual status, incumbent and bound in references.json. N20 time-limited incumbents are not global optima.",
        "- Wall times include sampling/simulation/allocation; compile/verifier overhead is recorded separately once per method. Classical simulation timing does not establish a hardware speed advantage.",
        "",
        "## Reproduction",
        "",
        "See [frozen protocol](../../../docs/research/IMPROVEMENT_PROTOCOL.md), source_snapshot, protocol.json, ablation.json, records.json, metrics.csv, references.json and orchestration receipts. Raw/case return matrices are not published; case hashes and source-column identities permit reconstruction from the pinned local corpus.",
        "",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines))
    (path / "PROGRESS.md").write_text(
        "# Improvement progress\n\nCompleted:168 published-US development runs,672 budget rows and6 explicit circuit-edit variants. Reduced opened-case gate cost while preserving selected F; stronger classical search remains the reference. No new inference or financial qualification.\n"
    )
    write_json(
        path / "derived_manifest.json",
        {
            "generator_sha256": sha(__file__),
            "source_download_manifest_sha256": sha(
                path / "orchestration/download_manifest.json"
            ),
            "output_sha256": {
                name: sha(path / name)
                for name in [
                    "RESULTS.md",
                    "analysis.json",
                    "resource-improvement.png",
                    "budget-curves.png",
                    "conditioned-comparison.png",
                ]
            },
            "new_inference_or_search_calls": 0,
        },
    )
    print(
        json.dumps(
            {"circuit_edits": resource_rows, "n20_comparison": summaries}, indent=2
        )
    )


if __name__ == "__main__":
    main()
