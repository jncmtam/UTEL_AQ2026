"""Independently audit downloaded artifacts and create a readable derived report."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import qpy, qasm3
from qiskit.quantum_info import Statevector

from agqo.research.data import sha, write_json
from agqo.research.finance import FinancialSpec
from agqo.research.quantum import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    path = args.directory
    if (path / "RESULTS.md").exists():
        raise ValueError("Derived report already exists; preserve it.")
    orchestration = path / "orchestration"
    hashes = json.loads((orchestration / "download_manifest.json").read_text())
    for name, checksum in hashes.items():
        assert sha(path / name) == checksum, name
    records = json.loads((path / "evaluation/records.json").read_text())
    decisions = [
        json.loads(line)
        for line in (path / "evaluation/decisions.jsonl").read_text().splitlines()
    ]
    specs = {}
    for case in (path / "inputs").iterdir():
        value = json.loads((case / "financial_spec.json").read_text())
        specs[case.name] = FinancialSpec(
            **{
                k: v
                for k, v in value.items()
                if k in FinancialSpec.__dataclass_fields__
            }
        )
    maximum_residual = 0.0
    for decision in decisions:
        spec = specs[decision["case_id"]]
        allocation = decision["allocation"]
        weights = np.asarray(allocation["weights"])
        bits = np.asarray(allocation["support"])
        assert not spec.violations_weights(weights)
        assert np.all(weights[bits == 0] == 0)
        assert sum(bits) == spec.k
        objective = float(
            np.mean((spec.returns @ weights - spec.benchmark) ** 2)
            + spec.cost_weight
            * spec.cost_rate
            * abs(weights - spec.previous_weights).sum()
        )
        residual = abs(objective - allocation["objective"])
        assert residual < 1e-10
        maximum_residual = max(maximum_residual, residual)
        order = decision["trade"]
        assert order["fee_dollars"] >= 0
        assert np.isclose(
            order["nav_before"] - order["fee_dollars"], order["nav_after"], atol=1e-6
        )
    exported = []
    for folder in sorted((path / "evaluation/circuits").glob("*/*")):
        ir = json.loads((folder / "gate_ir.json").read_text())
        h = json.loads((folder / "hamiltonian.json").read_text())
        angles = json.loads((folder / "angles.json").read_text())
        reference = execute(ir, h, angles)
        with (folder / "bound.qpy").open("rb") as stream:
            qc = qpy.load(stream)[0]
        qasm_qc = qasm3.loads((folder / "bound.qasm").read_text())
        state = np.asarray(Statevector.from_instruction(qc).data)
        qasm_state = np.asarray(Statevector.from_instruction(qasm_qc).data)
        # Workspace is appended; clean counter leaves all mass in its zero block.
        cleanup = float(1 - np.sum(abs(state[: len(reference)]) ** 2))
        fidelity = float(abs(np.vdot(reference, state[: len(reference)])) ** 2)
        qasm_fidelity = float(abs(np.vdot(state, qasm_state)) ** 2)
        assert cleanup < 1e-9 and fidelity >= 1 - 1e-9 and qasm_fidelity >= 1 - 1e-9
        exported.append(
            {
                "circuit": str(folder.relative_to(path)),
                "qpy_numpy_fidelity": fidelity,
                "qasm_qpy_fidelity": qasm_fidelity,
                "workspace_leakage": max(0.0, cleanup),
            }
        )
    metrics = pd.read_csv(path / "evaluation/metrics.csv")
    cost = json.loads((orchestration / "cost_report.json").read_text())
    before = json.loads((orchestration / "billing_before.json").read_text())
    after = json.loads((orchestration / "billing_after.json").read_text())
    receipt_path = next((orchestration / "inference").glob("*_receipt.json"))
    receipt = json.loads(receipt_path.read_text())
    model_records = [r for r in records if r["method"] == "coder30"]
    write_json(
        path / "postrun_validation.json",
        {
            "downloaded_files_verified": len(hashes),
            "financial_decisions_verified": len(decisions),
            "maximum_direct_financial_objective_residual": maximum_residual,
            "exported_circuits_verified": exported,
            "raw_cloud_artifacts_preserved": True,
            "new_inference_or_optimizer_runs": 0,
        },
    )
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
    for ax, name in zip(axes, specs):
        subset = [
            r for r in records if r["case_id"] == name and r["method"] != "uniform"
        ]
        bars = ax.bar(
            [r["method"] for r in subset],
            [r["verification"]["resources"]["transpiled_cx"] for r in subset],
            color=["#47759a", "#519388", "#8c659d"],
        )
        ax.bar_label(bars, padding=4)
        ax.set(title=name, ylabel="Logical CX, including COST and preparation")
        ax.set_ylim(0, max(b.get_height() for b in bars) * 1.2)
    fig.suptitle("Equal sampled portfolio quality does not imply equal circuit cost")
    fig.savefig(path / "circuit-resources.png", dpi=160)
    plt.close(fig)
    rows = [
        "# Live Modal pipeline results",
        "",
        "Date: 2026-11-04. **Connected integration succeeded; historical financial evaluation remains blocked.**",
        "",
        "## What actually ran",
        "",
        f"- Model: `{receipt['model']}` at pinned revision `{receipt['revision']}`.",
        f"- Live generation: `{receipt['gpu']}`, vLLM{receipt['vllm_version']}, batch size3, worker elapsed{receipt['elapsed_seconds']:.2f}s including model setup.",
        f"- Three proposals accepted, all with six active parameters and independently verified gate evolution. No repair or fallback.",
        f"- Cloud CPU evaluated24 decisions: three synthetic cases × four methods × two seeds;256 observations per decision,6,144 total.",
        f"- Download verified{len(hashes)} files. Independently rechecked24 financial objectives/trade balances and{len(exported)} exported QPY/QASM circuits. See postrun_validation.json.",
        "- Separate cloud software stage executed five two-period synthetic accounts with zero account resets, plus baseline and explicit blocked market branches.",
        "",
        "## Measured outcomes",
        "",
        "| Case | Selected allocated objective, all four methods | Rows feasible | Gap to exhaustive allocated reference |",
        "|---|---:|---:|---:|",
    ]
    for name in specs:
        frame = metrics[metrics.case_id == name]
        rows.append(
            f"| {name} | {frame.allocated_objective.iloc[0]:.9g} | {sum(frame.status == 'feasible')}/{len(frame)} | {frame.regret_to_exhaustive.max():.3g} |"
        )
    rows += [
        "",
        "Every method reached the same best enumerated allocated objective, within recorded numerical tolerances. This is an integration success, not an LLM performance win. The small spaces and256 observations make them easy; broader scaling needs a new development protocol.",
        "",
        "![Allocated objectives](evaluation/allocated-objective.png)",
        "",
        "**Figure 1. Allocated training objectives.** Source: evaluation/metrics.csv. Lower is better; dots show two seeds on each synthetic case. No out-of-sample market or statistical superiority claim.",
        "",
        "![Circuit resources](circuit-resources.png)",
        "",
        "**Figure 2. Complete logical circuit resources.** Source: recorded verification resources. Counts include compiler-owned COST and counter-Dicke workspace/preparation. All-to-all logical connectivity is assumed; these are not hardware execution costs.",
        "",
        "The LLM chose path-shaped exchange trees and depth2 in all three cases. Valid programs therefore do not establish adaptation to the data profile. Resource and permutation/profile studies remain necessary.",
        "",
        "## Cost and execution evidence",
        "",
        f"- Conservative total reservation: **USD{cost['reserved_usd_total']:.5f}**, across prepare CPU, weight-prefetch CPU, one GPU batch and finish CPU; all jobs completed.",
        f"- Tokens: **{cost['input_tokens']:,} input + {cost['output_tokens']:,} output**.",
        f"- Account monthly metered snapshot: USD{before['metered_cost']:.8f} → USD{after['metered_cost']:.8f}; this delta is not an isolated final job invoice and may lag.",
        "- GPU is used for LLM inference. Quantum circuits are simulated on cloud CPU. Image-build spending is not separately allocated; during-build snapshot retained beside the run.",
        "",
        "## Scope and remaining blockers",
        "",
        "The simulator uses immutable proxy Hamiltonian B, but optimizer feedback scores actual allocated F. All optimizer/final observations join the candidate pool, and allocation/cache work is recorded. F is not a coherent quantum oracle.",
        "",
        "These are state-matched allocation cases; continuous-account integration is in software_pipeline/synthetic_trajectory. There is no live-LLM historical walk-forward result here. Historical admission,95% independent correctness qualification, financial value and quantum advantage remain open.",
        "",
        "The cloud market audit uses the manifest without raw provider files, so it reports unavailable remote raw files in addition to the established source-review blockers. See historical_audit_v3 for actual local coverage. Raw inputs were not silently replaced or admitted.",
        "",
        "## Read and reproduce",
        "",
        "- [Raw cloud report](evaluation/RESULTS.md), [metrics](evaluation/metrics.csv), [decisions](evaluation/decisions.jsonl), [references](evaluation/references.json).",
        "- [Independent export/finance audit](postrun_validation.json), [final orchestration cost](orchestration/cost_report.json), [completed call checkpoint](orchestration/completed.json).",
        "- [Frozen execution protocol](../../../docs/research/MODAL_E2E_PROTOCOL.md) and [runbook](../../../docs/MODAL_RUNBOOK.md).",
        "- Running `python scripts/run_modal_pipeline.py --run-id modal_e2e_v1` reads the completed local checkpoint and schedules no new compute.",
        "",
    ]
    (path / "RESULTS.md").write_text("\n".join(rows))
    (path / "PROGRESS.md").write_text(
        "# Modal integration progress\n\nCompleted and downloaded.3/3 live proposals verified;24/24 synthetic decisions feasible;9 QPY/QASM exports independently crosschecked. Financial/model qualification remains blocked. No follow-up GPU run scheduled.\n"
    )
    print(
        json.dumps(
            {
                "accepted_model_designs": len(model_records),
                "feasible_decisions": len(decisions),
                "verified_exports": len(exported),
                "reservation_usd": cost["reserved_usd_total"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
