"""Secondary, post-result diagnostics from saved actual observations; no search."""

from pathlib import Path
import json
import pandas as pd
from agqo.research.data import write_json


def main():
    root = Path("results/research/counterfactual_editor_v4")
    evaluation = root / "evaluation"
    admissions = json.loads((evaluation / "admissions.json").read_text())
    rows = []
    for cid, variants in admissions.items():
        for seed in (23, 47):
            baseline = json.loads((evaluation / "runs" / f"{cid}__evaluation__aggregate__{seed}.json").read_text())["result"]
            actual = json.loads((evaluation / "runs" / f"{cid}__evaluation__counterfactual__{seed}.json").read_text())["result"]
            b, a = variants["aggregate"], variants["counterfactual"]
            rows.append({"case_id": cid, "seed": seed,
                "best_F_difference_pct": 100*(actual["allocation"]["objective"]/baseline["allocation"]["objective"]-1),
                "final_mean_normalized_F_difference_pct": 100*(actual["fitting_record"]["batches"][-1]["mean_loss"]/baseline["fitting_record"]["batches"][-1]["mean_loss"]-1),
                "depth_difference_pct": 100*(a["verification"]["resources"]["transpiled_depth"]/b["verification"]["resources"]["transpiled_depth"]-1),
                "aggregate_parameters": len(b["gate_ir"]["parameters"]),
                "detailed_parameters": len(a["gate_ir"]["parameters"])})
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "secondary_diagnostics.csv", index=False)
    means = frame.drop(columns="seed").groupby("case_id").mean(numeric_only=True).to_dict("index")
    write_json(root / "secondary_diagnostics.json", {
        "scope": "Post-result descriptive analysis, not a new experiment or changed acceptance criterion",
        "case_means": means})
    print(json.dumps(means, indent=2))


if __name__ == "__main__":
    main()
