"""Independently audit downloaded live proposals and explain measured outcomes."""

from pathlib import Path
import argparse
import json
import shutil
import math
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from agqo.research.data import sha, write_json

try:
    from scripts.summarize_tail_pilot import audit_run
except ModuleNotFoundError:
    from summarize_tail_pilot import audit_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        choices=("live_guidance_v1", "live_edge_v2"),
        default="live_guidance_v1",
    )
    args = parser.parse_args()
    path = Path("results/research") / args.run_id
    if (path / "RESULTS.md").exists():
        raise ValueError("Derived report retained; use a new presentation revision.")
    orchestration, evaluation = path / "orchestration", path / "evaluation"
    completed = json.loads((orchestration / "completed.json").read_text())
    hashes = json.loads((orchestration / "download_manifest.json").read_text())
    for name, value in hashes.items():
        assert sha(evaluation / name) == value, name
    admissions = json.loads((evaluation / "admissions.json").read_text())
    protocol = json.loads((orchestration / "protocol.json").read_text())
    answers = json.loads((orchestration / "answers.json").read_text())
    requests = json.loads((orchestration / "prepared_requests.json").read_text())
    assert {r["request"]["request_hash"] for r in requests} == {
        a["request_hash"] for a in answers
    }
    source = json.loads(
        Path("results/research/tail_fitting_v1/protocol.json").read_text()
    )
    targets = {c["id"]: c["target"] for c in source["cases"]}
    sizes = {
        c["id"]: len(
            json.loads(
                (
                    evaluation / "cases" / c["id"] / "sufficient_statistics.json"
                ).read_text()
            )["linear"]
        )
        for c in protocol["cases"]
    }
    rows, prefixes, failures = [], [], []
    rescored, residual = 0, 0.0
    for file in sorted((evaluation / "runs").glob("*.json")):
        record = json.loads(file.read_text())
        if record["status"] != "completed":
            failures.append(record)
            continue
        case = record["case_id"]
        stats = json.loads(
            (evaluation / "cases" / case / "sufficient_statistics.json").read_text()
        )
        points, row, count, error = audit_run(record, stats, targets[case], 576)
        row["n"] = sizes[case]
        rows.append(row)
        prefixes.extend(points)
        rescored += count
        residual = max(residual, error)
    frame, prefix = pd.DataFrame(rows), pd.DataFrame(prefixes)
    frame.to_csv(path / "metrics.csv", index=False)
    prefix.to_csv(path / "prefix_metrics.csv", index=False)
    model_rows = [r for r in admissions if r["method"] in ("guided", "context_only")]
    assert len(model_rows) == len(answers) == 8
    accepted = sum(r["admission"]["status"] == "accepted" for r in model_rows)
    assert accepted == completed["model_accepted"]
    expected_runs = (
        sum(r["admission"]["status"] == "accepted" for r in admissions) * 3 + 4 * 2 * 3
    )
    assert len(rows) + len(failures) == expected_runs == completed["runs"]
    pairs = []
    for reference in (
        "context_only",
        "fixed_scheduled",
        "uniform_conditioned",
        "allocation_swap",
    ):
        base = frame[frame.method == reference][
            ["case_id", "seed", "best_objective"]
        ].rename(columns={"best_objective": "reference"})
        paired = frame[frame.method == "guided"].merge(base, on=["case_id", "seed"])
        paired = paired[
            paired.best_objective.notna()
            & paired.reference.notna()
            & (paired.reference > 0)
        ]
        if len(paired):
            difference = 100 * (paired.best_objective / paired.reference - 1)
            delta = paired.best_objective - paired.reference
            pairs.append(
                {
                    "reference": reference,
                    "pairs": len(paired),
                    "mean_pct": float(difference.mean()),
                    "median_pct": float(difference.median()),
                    "wins": int((delta < -1e-12).sum()),
                    "ties": int((abs(delta) <= 1e-12).sum()),
                    "losses": int((delta > 1e-12).sum()),
                }
            )
    structural = []

    def normalized(row):
        value = row["admission"].get("normalized_program", row.get("program"))
        return value if isinstance(value, dict) and "parents" in value else None

    for case in sizes:
        data = {r["method"]: r for r in model_rows if r["case_id"] == case}
        a, b = normalized(data["context_only"]), normalized(data["guided"])
        if isinstance(a, dict) and isinstance(b, dict):
            structural.append(
                {
                    "case_id": case,
                    "parent_changes": sum(
                        a["parents"][k] != b["parents"][k] for k in a["parents"]
                    ),
                    "schedule_changed": a["schedule"] != b["schedule"],
                    "groups_changed": a["groups"] != b["groups"],
                    "guidance_usefulness_not_proven_by_changes": True,
                }
            )
    fig, axes = plt.subplots(4, 2, figsize=(12, 15), layout="constrained")
    for line, case in enumerate(sizes):
        for column, arm in enumerate(("context_only", "guided")):
            ax = axes[line, column]
            entry = next(
                r for r in requests if r["case_id"] == case and r["arm"] == arm
            )
            free = entry["request"]["payload"]["exchange_table"]["free_qubits"]
            admission = next(
                r for r in model_rows if r["case_id"] == case and r["method"] == arm
            )
            program = normalized(admission)
            positions = {
                q: (
                    math.cos(2 * math.pi * i / len(free)),
                    math.sin(2 * math.pi * i / len(free)),
                )
                for i, q in enumerate(free)
            }
            if isinstance(program, dict) and "parents" in program:
                for child in range(1, len(free)):
                    a, b = free[program["parents"][f"p{child}"]], free[child]
                    x, y = positions[a], positions[b]
                    color = (
                        "#c37b20" if program["groups"][child - 1] == 0 else "#365eae"
                    )
                    ax.plot([x[0], y[0]], [x[1], y[1]], color=color, alpha=0.7)
            for q, (x, y) in positions.items():
                ax.scatter(
                    [x], [y], s=210, color="#e3f0ed", edgecolors="#206a60", zorder=3
                )
                ax.text(x, y, str(q), ha="center", va="center", fontsize=8, zorder=4)
            ax.set_title(
                f"{case} / {arm}\n{admission['admission']['status']}", fontsize=10
            )
            ax.set_aspect("equal")
            ax.axis("off")
    fig.suptitle(
        "Actual LLM exchange trees: orange beta-group0, blue beta-group1\nNodes are free asset qubits, not stocks selected for the portfolio",
        fontsize=12,
    )
    fig.savefig(path / "circuit-structures.png", dpi=160)
    plt.close(fig)
    cost = json.loads((orchestration / "cost_report.json").read_text())
    analysis = {
        "raw_files_verified": len(hashes),
        "completed_runs": len(rows),
        "errors": failures,
        "observations": int(frame.observations.sum()),
        "allocation_queries": int(frame.allocation_queries.sum()),
        "feasible_allocations_rescored": rescored,
        "maximum_objective_residual": residual,
        "model_acceptance": f"{accepted}/8",
        "paired_guided_comparisons": pairs,
        "structure_changes": structural,
        "cost": cost,
        "scope": "Opened conditional US development; no investment/hardware advantage qualification",
    }
    write_json(path / "analysis.json", analysis)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for ax, case in zip(axes.flat, sizes):
        part = prefix[prefix.case_id == case]
        for method, group in part.groupby("method"):
            curve = group.groupby("draws").best_objective.mean()
            ax.plot(curve.index, curve.values * 1e6, marker="o", label=method)
        ax.set(
            title=case, xlabel="All observed supports", ylabel="Best allocated F x 1e6"
        )
        ax.grid(alpha=0.2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4)
    fig.suptitle(
        "Live model designs and controls — equal observations, unequal complete costs"
    )
    fig.savefig(path / "quality-by-budget.png", dpi=160)
    plt.close(fig)
    lines = [
        "# Live LLM/QAOA guidance results",
        "",
        "Real pinned Qwen Coder30 inference on Modal, followed by independent circuit/resource admission and CPU portfolio evaluation. Four opened conditional US development cases; no independent investment test or quantum hardware execution.",
        "",
        f"**Model proposals admitted: {accepted}/8.** Completed {len(rows)} runs; {len(failures)} execution errors. Rejected proposals remain in the eight-request denominator. Acceptance means quantum/evidence/resource admission, not financial superiority.",
        "",
        "## Exact prompts and responses",
        "",
        "[Exact system prompts](SYSTEM_PROMPTS.md) · [All full requests](orchestration/prepared_requests.json) · [Raw answers and usage](orchestration/answers.json) · [All admissions](evaluation/admissions.json). Both arms share numerical context/schema/seed; the guided arm adds an explicit procedure. Compiler owns preparation and COST, numerical optimizer owns angles.",
        "",
        "## Admission and resources",
        "",
        "| Case | Arm/control | Admission | CX | Depth |",
        "|---|---|---|---:|---:|",
    ]
    if args.run_id == "live_edge_v2":
        lines[2:2] = [
            "V2 is a new interface-development study: model selects edge IDs/groups once; compiler derives traceability and disjoint scheduling. Caps use the saved unscheduled fixed baseline for every method. These changes prevent attributing v1-v2 gains solely to prompting/model quality. Original v1 remains0/8 admitted. The within-v2 context/guided comparison shares schema, inputs, caps and compiler.",
            "",
        ]
    for r in admissions:
        resources = r["admission"].get("verification", {}).get("resources", {})
        lines.append(
            f"| {r['case_id']} | {r['method']} | {r['admission']['status']} | {resources.get('transpiled_cx', '—')} | {resources.get('transpiled_depth', '—')} |"
        )
    lines += [
        "",
        "## Financial comparison",
        "",
        "Positive means guided is worse. Means of paired allocated-training-objective percentage differences; comparison includes only pairs with both feasible decisions, while admission failures remain visible above. These are related cases/seeds, not returns or significance.",
        "",
        "| Guided versus | Pairs | Mean difference | Median | Wins/ties/losses |",
        "|---|---:|---:|---:|---|",
    ]
    for r in pairs:
        lines.append(
            f"| {r['reference']} | {r['pairs']} | {r['mean_pct']:+.2f}% | {r['median_pct']:+.2f}% | {r['wins']}/{r['ties']}/{r['losses']} |"
        )
    lines += [
        "",
        "![Quality by budget](quality-by-budget.png)",
        "",
        "All methods receive576 observations/run where admitted. Actual allocator queries, cached observations, simulation calls and time differ. Full data is in metrics.csv/prefix_metrics.csv. Infeasible/unknown outcomes and final empirical gate statuses remain explicit. COST is B and allocated feedback is F, so this does not fix their formulation mismatch.",
        "",
        "## What the model changed",
        "",
        "| Case | Changed parent choices | Changed schedule | Changed beta groups |",
        "|---|---:|---|---|",
    ]
    for r in structural:
        lines.append(
            f"| {r['case_id']} | {r['parent_changes']} | {r['schedule_changed']} | {r['groups_changed']} |"
        )
    lines += [
        "",
        "![Actual LLM circuit structures](circuit-structures.png)",
        "",
        "Different structures/citations alone are not evidence of useful adaptation. No automatic repair, bigger-model escalation or tuning to this result.",
        "",
        "## Audit and cost",
        "",
        f"Verified {len(hashes)} downloaded hashes and rescored {rescored:,} feasible cached allocations; maximum objective residual {residual:.3g}. All batch/final feasibility and sample/cache/solver accounting checked independently.",
        "",
        f"Input tokens {cost['input_tokens']:,}; output tokens {cost['output_tokens']:,}. Total reservation USD{cost['reserved_usd_total']:.6f}, not an invoice. Account billing snapshots and GPU/prefetch/CPU call IDs are retained in orchestration. Build/input preparation overhead is not isolated by these function reservations or recorded evaluation timings.",
        "",
        "## Limits and next decision",
        "",
        "The corpus has full-year membership conditioning/artificial policy buckets; first126 observations only. This is a state-matched portfolio-repair algorithm study, not continuous investable account performance. No population-feasibility certification from empirical95% batch gates. Large circuits use analytic/conserved verification, not a claimed full N23 Qiskit statevector run.",
        "",
        "A win against another circuit arm is a narrow result; direct allocation-aware search is the stronger financial reference. If guided proposals do not improve a useful quality/resource frontier, retain the negative result and revisit formulation/design before any model sweep.",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    (path / "PROGRESS.md").write_text(
        f"# Progress\n\nModal batch and CPU evaluation completed. {accepted}/8 admitted model proposals; {len(rows)} audited runs. No independent model/financial qualification. Read RESULTS.md and analysis.json.\n"
    )
    shutil.copyfile(__file__, path / "report_generator.py")
    write_json(
        path / "report_manifest.json",
        {
            "raw_downloads_unchanged": True,
            "derived_sha256": {
                name: sha(path / name)
                for name in (
                    "analysis.json",
                    "RESULTS.md",
                    "PROGRESS.md",
                    "metrics.csv",
                    "prefix_metrics.csv",
                    "quality-by-budget.png",
                    "circuit-structures.png",
                    "report_generator.py",
                )
            },
        },
    )
    print(
        json.dumps(
            {
                k: analysis[k]
                for k in (
                    "model_acceptance",
                    "completed_runs",
                    "observations",
                    "allocation_queries",
                    "feasible_allocations_rescored",
                    "paired_guided_comparisons",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
