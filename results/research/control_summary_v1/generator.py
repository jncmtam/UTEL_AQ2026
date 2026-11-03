"""Descriptive report and figures from frozen controls; no new optimization."""

from pathlib import Path
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from agqo.research.data import write_json, sha


def records(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def main():
    root = Path("results/research")
    output = root / "control_summary_v1"
    if output.exists():
        raise ValueError("Preserve the previous control summary.")
    output.mkdir(parents=True)
    prep = records(root / "preparation_control_v1/decisions.jsonl")
    conditioned = records(root / "conditioning_control_v1/decisions.jsonl")
    formulas = json.loads((root / "formulation_identity_v1/audit.json").read_text())[
        "summaries"
    ]
    matched = json.loads(
        (root / "preparation_control_v1/postrun_control_audit/audit.json").read_text()
    )["rows"]
    lines = [
        "# Controlled follow-up findings",
        "",
        "Opened US development data, ideal CPU simulation and no new model inference. These controls diagnose the algorithm; they do not qualify a production LLM or investment strategy.",
        "",
        "## Broad-support preparation",
        "",
        "| N30 control | Mean allocated training objective | Meaningful supports | Physical qubits | CX | Logical depth |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in ["three_pair", "counter_dicke", "uniform"]:
        subset = [r for r in prep if r["n"] == 30 and r["method"] == method]
        objective = np.mean([r["allocation"]["objective"] for r in subset])
        s = subset[0].get("selection", {})
        v = subset[0].get("verification", {}).get("resources", {})
        coverage = [
            r.get("selection", {}).get("nonnegligible_probability_supports")
            for r in subset
        ]
        coverage = str(coverage) if method != "uniform" else "128 draws"
        lines.append(
            f"| {method} | {objective:.8g} | {coverage} | {v.get('qubits', '—')} | {v.get('transpiled_cx', '—')} | {v.get('transpiled_depth', '—')} |"
        )
    m = np.mean([r["allocation"]["objective"] for r in matched if r["n"] == 30])
    lines += [
        f"| uniform_total_shots (post-run audit) | {m:.8g} | 2176 draws | — | — | — |",
        "",
        "The counter prepares the complete uniform K-of-N state without dense synthesis. It uses a distinct binary-counter construction with clean workspace, not the cited ancilla-free algorithm. It removes sparse coverage, while increasing N30 depth from445 to2428. Uniform sampling with the same total draw allowance remains stronger on this case.",
        "",
        "## Financial formulation identity",
        "",
        "| Scenario | Target-weight policy | Identity gate | Proxy-optimal allocation regret |",
        "|---|---|---|---:|",
    ]
    for r in formulas:
        regret = r.get("relative_regret")
        lines.append(
            f"| {r['scenario']} | {r['policy']} | {r['equal_weight_identity_passed']} | {regret:.2%} |"
        )
    lines += [
        "",
        "Equal-weight targets give exact B=F on feasible supports within numerical tolerance. They are a different explicit mandate; the primary continuous-allocation task is retained. Its proxy distortion is not solved by broader initialization.",
        "",
        "## Paper-based optimizer conditioning",
        "",
        "The [published Eq8 RMS rule](https://arxiv.org/html/2305.15201v3#S3.SS2) is applied as gamma and loss coordinates on the unchanged Hamiltonian. Defaults and older frozen runs are retained. Means below are descriptive across three seeds on the same opened case.",
        "",
        "| N | Financial policy | Raw coordinates | Paper RMS coordinates | Uniform2176 draws |",
        "|---:|---|---:|---:|---:|",
    ]
    for n in [10, 30]:
        for policy in ["continuous", "equal_weight_target"]:
            values = []
            for method in ["raw", "paper_rms", "uniform_total_shots"]:
                subset = [
                    r
                    for r in conditioned
                    if r["n"] == n
                    and r["weight_policy"] == policy
                    and r["method"] == method
                ]
                values.append(
                    float(
                        np.mean(
                            [
                                r["allocation"]["objective"]
                                for r in subset
                                if r["feasible"]
                            ]
                        )
                    )
                )
            lines.append(
                f"| {n} | {policy} | {values[0]:.8g} | {values[1]:.8g} | {values[2]:.8g} |"
            )
    lines += [
        "",
        "Paper RMS scaling improves the mean selection-proxy expectation on these cases, but that is not a universal allocated-objective improvement. In N30 continuous allocation, the mean financial objective worsens. Under the equal-weight target it improves, yet the matched-draw classical reference remains stronger.",
        "",
        "Circuit postprocessing uses only final samples; the uniform2176 control uses the maximum optimizer-plus-final draw count. A next protocol must explicitly decide whether all measured optimizer bitstrings join the candidate pool. No hidden pooling is applied retrospectively.",
        "",
        "## Decision before more inference",
        "",
        "- Keep counter-Dicke and paper RMS as explicit non-LLM controls; do not replace earlier methods silently.",
        "- Resolve the financial target and proxy faithfulness before a model sweep. Continuous and equal-weight scores must remain separate.",
        "- Predeclare candidate pooling, total-draw/time budgets and strong classical comparisons.",
        "- Preserve original US investment-data blockers; the published corpus has full-year selection conditioning.",
        "- Freeze a revised study before evaluating any LLM on unopened structures. Current results do not select a model or demonstrate quantum advantage.",
        "",
        "No inferential significance claim: only two opened sizes and three seeds per case. Seed variation is not independent market evidence.",
    ]
    (output / "FINDINGS.md").write_text("\n".join(lines) + "\n")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), layout="constrained")
    methods = ["raw", "paper_rms", "uniform_total_shots"]
    for ax, policy in zip(axes, ["continuous", "equal_weight_target"]):
        values = []
        low = []
        high = []
        for method in methods:
            a = (
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
            values.append(a.mean())
            low.append(a.mean() - a.min())
            high.append(a.max() - a.mean())
        ax.bar(
            methods,
            values,
            yerr=[low, high],
            capsize=5,
            color=["#5680a8", "#509b83", "#9caa40"],
        )
        ax.set(
            title=policy.replace("_", " "),
            ylabel="Allocated training objective ×10⁶ (lower is better)",
        )
        ax.tick_params(axis="x", rotation=15)
    fig.suptitle(
        "N30: ranges across three seeds, opened development; no significance claim"
    )
    fig.savefig(output / "conditioning-financial-objective.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), layout="constrained")
    a = next(
        r["verification"]["resources"]
        for r in prep
        if r["n"] == 30 and r["method"] == "three_pair"
    )
    b = next(
        r["verification"]["resources"]
        for r in prep
        if r["n"] == 30 and r["method"] == "counter_dicke"
    )
    for ax, key, label in zip(
        axes,
        ["qubits", "transpiled_cx", "transpiled_depth"],
        ["Physical qubits", "Logical CX", "Logical depth"],
    ):
        ax.bar(
            ["three pair", "counter Dicke"],
            [a[key], b[key]],
            color=["#5680a8", "#509b83"],
        )
        ax.set(title=label)
    fig.suptitle("Full preparation and cost resources, all-to-all logical basis")
    fig.savefig(output / "preparation-resources.png", dpi=180)
    plt.close(fig)
    inputs = [
        "preparation_control_v1/decisions.jsonl",
        "preparation_control_v1/postrun_control_audit/audit.json",
        "conditioning_control_v1/decisions.jsonl",
        "formulation_identity_v1/audit.json",
    ]
    write_json(
        output / "manifest.json",
        {
            "input_sha256": {name: sha(root / name) for name in inputs},
            "script_sha256": sha(__file__),
            "new_optimization_or_inference": False,
        },
    )
    print(output)


if __name__ == "__main__":
    main()
