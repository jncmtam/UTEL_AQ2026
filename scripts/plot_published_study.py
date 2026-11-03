"""Derived scientific figures from frozen development records, without rescoring."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from agqo.research.data import sha, write_json


def main(directory):
    path = Path(directory)
    output = path / "figures"; output.mkdir(exist_ok=True)
    rows = [json.loads(line) for line in (path / "decisions.jsonl").read_text().splitlines()]
    selected = [row for row in rows if row["case"] == "n30_k6_base"]
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    names = [row["method"] for row in selected]
    values = [row.get("allocation", {}).get("objective", np.nan) * 1e6 for row in selected]
    ax.bar(names, values, color=["#5680a8"] * 3 + ["#9caa40", "#9caa40", "#b66b63"])
    reference = next(row for row in selected if row["method"] == "joint_scip")
    ax.axhline(reference["reference"]["lower_bound"] * 1e6, linestyle="--", color="black", label="SCIP lower bound (15 s)")
    ax.set(ylabel="Allocated training objective × 10⁶ (lower is better)",
           title="30-asset development case: tracking MSE + weighted assumed cost")
    ax.tick_params(axis="x", rotation=18); ax.legend()
    fig.savefig(output / "allocated-objective.png", dpi=180); plt.close(fig)
    circuits = selected[:3]
    fig, ax = plt.subplots(figsize=(8.4, 4.8), layout="constrained")
    ax.bar([row["method"] for row in circuits], [row["selection"]["nonnegligible_probability_supports"] for row in circuits], color="#5680a8")
    ax.axhline(593775, color="black", linestyle="--", label="All 6-of-30 supports retained")
    ax.set_yscale("log")
    ax.set(ylabel="Supports with probability > 10⁻¹² (log scale)",
           title="Representing every support does not ensure broad shallow-circuit exploration")
    ax.legend(); fig.savefig(output / "support-coverage.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
    for ax, case in zip(axes, ("n10_k3_base", "n10_k3_exclude_incumbent")):
        report = json.loads((path / "postrun_analysis" / f"{case}_all_supports.json").read_text())
        valid = [row for row in report["supports"] if row["allocation"]["feasible"]]
        ax.scatter([row["proxy"] * 1e6 for row in valid],
                   [row["allocation"]["objective"] * 1e6 for row in valid], s=15, alpha=0.65)
        ax.set(xlabel="Equal-weight selection proxy × 10⁶", ylabel="Allocated objective × 10⁶",
               title=case.replace("_", " ") + f"\nSpearman {report['rank_correlation']:.3f}")
    fig.savefig(output / "proxy-faithfulness.png", dpi=180); plt.close(fig)
    write_json(output / "manifest.json", {"scope":"Derived opened-development figures, no new inference or scoring.",
        "source_hashes": {name:sha(path / name) for name in ("protocol.json", "decisions.jsonl", "postrun_analysis/analysis.json")},
        "script_sha256":sha(__file__), "figures":["allocated-objective.png", "support-coverage.png", "proxy-faithfulness.png"]})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/research/published_development_v3")
