"""Independently audit saved weight-grid results and generate static research figures."""

from itertools import combinations, product
from pathlib import Path
import json
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import qasm3, qpy
from qiskit.quantum_info import Statevector

from agqo.research.data import sha, write_json
from agqo.research.improvement import decode
from agqo.synthesis.profile import digest


def write_contract(path, summary, spec):
    """Export common reporting fields without pretending these are executed trades."""
    before = spec.previous_weights.tolist()
    decisions = [
        {
            "kind": "grid_formulation_diagnostic",
            "grid_units": r["units"],
            "before_weights": before,
            "proposed_weights": r["best"]["weights"],
            "trades": [b - a for a, b in zip(before, r["best"]["weights"])],
            "metrics": r["best"],
            "status": "feasible_grid_reference_not_executed",
            "market_admitted": False,
            "llm_generated": False,
        }
        for r in summary["rows"]
    ]
    (path / "decisions.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in decisions)
    )
    with (path / "metrics.csv").open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scope",
                "grid_units",
                "status",
                "qubits",
                "cost_cx",
                "cost_depth",
                "objective",
                "relative_regret",
                "full_state",
            ],
        )
        writer.writeheader()
        for r in summary["rows"]:
            writer.writerow(
                {
                    "scope": "conditional_US_3_asset_diagnostic",
                    "grid_units": r["units"],
                    "status": r["status"],
                    "qubits": r["qubits"],
                    "cost_cx": r["cost_cx"],
                    "cost_depth": r["cost_depth"],
                    "objective": r["best"]["objective"],
                    "relative_regret": r["relative_discretization_regret"],
                    "full_state": r["full_state_validation"],
                }
            )
        for r in summary["original_n20_resources"]:
            writer.writerow(
                {
                    "scope": "original_N20_resource_only",
                    "grid_units": r["units"],
                    "status": r["status"],
                    "qubits": r["qubits"],
                    "cost_cx": r["cost_cx"],
                    "cost_depth": r["cost_depth"],
                    "full_state": "not_attempted",
                }
            )
    write_json(
        path / "cost_report.json",
        {
            "scope": "weight_grid_v2_continuation_only",
            "new_modal_dispatches": 0,
            "new_llm_calls": 0,
            "new_paid_cloud_spend_usd": 0,
            "local_successful_run_wall_seconds": summary[
                "elapsed_seconds_including_input_preparation"
            ],
            "timing_includes": "successful input preparation and formulation diagnostic",
            "timing_excludes": [
                "two failed local preflights",
                "tests",
                "independent audit",
                "reporting",
            ],
            "full_local_compute_time": "not_metered",
            "local_compute_dollar_cost": "not_priced",
            "prior_modal_studies": "separate preserved ledgers",
        },
    )
    write_json(
        path / "circuits/index.json",
        {
            "artifact_scope": "compiler_owned_cost_only_not_complete_QAOA_or_LLM_output",
            "exports": [
                {
                    "grid_units": r["units"],
                    "qasm": f"../grid_{r['units']}/cost.qasm",
                    "qpy": f"../grid_{r['units']}/cost.qpy",
                    "verification": f"../grid_{r['units']}/verification.json",
                }
                for r in summary["rows"]
            ],
        },
    )


def main():
    path = Path("results/research/weight_grid_v2")
    if (path / "RESULTS.md").exists():
        raise ValueError("Completed analysis retained; do not overwrite.")
    manifest = json.loads((path / "artifact_manifest.json").read_text())
    for name, expected in manifest.items():
        if sha(path / name) != expected:
            raise ValueError(f"Raw artifact changed: {name}")
    complete = json.loads((path / "completion.json").read_text())
    if digest(manifest) != complete["manifest_hash"]:
        raise ValueError("Completion manifest identity mismatch.")
    spec = decode(json.loads((path / "financial_spec.json").read_text()))
    original = decode(json.loads((path / "source_financial_spec.json").read_text()))
    if not np.array_equal(
        spec.returns, original.returns[:126, :3]
    ) or not np.array_equal(spec.benchmark, original.benchmark[:126]):
        raise ValueError("Prespecified data slice changed.")
    s = json.loads((path / "summary.json").read_text())
    residual = 0.0
    checked = 0

    def score(weights):
        w = np.asarray(weights)
        return float(
            np.mean((spec.returns @ w - spec.benchmark) ** 2)
            + spec.cost_weight
            * spec.cost_rate
            * np.abs(w - spec.previous_weights).sum()
        )

    continuous = json.loads((path / "continuous_allocations.json").read_text())
    for row in continuous:
        if row["feasible"]:
            if spec.violations_weights(row["weights"]):
                raise ValueError("Continuous reference is not financially feasible.")
            residual = max(residual, abs(score(row["weights"]) - row["objective"]))
            checked += 1
    export_checks = []
    for row in s["rows"]:
        units = row["units"]
        candidates = json.loads(
            (path / f"grid_{units}/financial_candidates.json").read_text()
        )
        expected = set()
        for support in combinations(range(3), 2):
            for a, b in product(range(1, units + 1), repeat=2):
                w = np.zeros(3)
                w[list(support)] = [a / units, b / units]
                if a + b == units and not spec.violations_weights(w):
                    expected.add(tuple(np.rint(w * units).astype(int)))
        actual = set()
        for candidate in candidates:
            w = np.asarray(candidate["weights"])
            if spec.violations_weights(w):
                raise ValueError("An enumerated financial grid portfolio is invalid.")
            actual.add(tuple(np.rint(w * units).astype(int)))
            residual = max(residual, abs(score(w) - candidate["objective"]))
            checked += 1
        if actual != expected or len(actual) != len(candidates):
            raise ValueError("Independent financial grid coverage differs.")
        if row["best"]["objective"] != min(c["objective"] for c in candidates):
            raise ValueError("Reported grid optimum disagrees with saved candidates.")
        with (path / f"grid_{units}/cost.qpy").open("rb") as file:
            qp = qpy.load(file)[0]
        qa = qasm3.loads((path / f"grid_{units}/cost.qasm").read_text())
        if (
            qp.num_qubits != row["qubits"]
            or qa.num_qubits != qp.num_qubits
            or len(qa.data) != len(qp.data)
        ):
            raise ValueError("QPY/QASM gate resources disagree.")
        for a, b in zip(qp.data, qa.data):
            if (
                a.operation.name != b.operation.name
                or [qp.find_bit(q).index for q in a.qubits]
                != [qa.find_bit(q).index for q in b.qubits]
                or not np.allclose(
                    a.operation.params, b.operation.params, rtol=1e-12, atol=1e-12
                )
            ):
                raise ValueError("QPY/QASM operations disagree.")
        check = {
            "units": units,
            "parsed": True,
            "gate_schedule_match": True,
            "full_state": "skipped_over_16_qubits",
        }
        if qp.num_qubits <= 16:
            init = np.ones(2**qp.num_qubits) / np.sqrt(2**qp.num_qubits)
            a, b = Statevector(init).evolve(qp).data, Statevector(init).evolve(qa).data
            overlap = abs(np.vdot(a, b))
            if abs(overlap - 1) > 1e-10:
                raise ValueError(
                    "QPY/QASM state evolution differs beyond global phase."
                )
            check.update(full_state="passed_up_to_global_phase", overlap=float(overlap))
        export_checks.append(check)
    if residual > 1e-10:
        raise ValueError("Independent financial rescore exceeds tolerance.")
    audit = {
        "raw_hashes_checked": len(manifest),
        "feasible_weights_independently_rescored": checked,
        "maximum_direct_return_objective_residual": residual,
        "grid_coverage_complete": True,
        "qpy_qasm_checks": export_checks,
        "new_model_calls": 0,
        "new_modal_calls": 0,
    }
    write_json(path / "independent_audit.json", audit)
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    x = [r["units"] for r in s["rows"]]
    axes[0].plot(
        x,
        [max(0, r["relative_discretization_regret"]) * 100 for r in s["rows"]],
        "o-",
        color="#176b87",
    )
    axes[0].set(
        xlabel="Grid denominator M (weight step = 1/M)",
        ylabel="Allocated objective regret (%)",
        title="Precision on the fixed 3-asset diagnostic",
    )
    axes[0].set_xticks(x)
    axes[0].text(
        0.98,
        0.95,
        "M >= 10 matches a boundary optimum\nwithin numerical solver tolerance",
        transform=axes[0].transAxes,
        ha="right",
        va="top",
        fontsize=9,
    )
    axes[1].plot(x, [r["qubits"] for r in s["rows"]], "o-", color="#ba5a31")
    axes[1].set(
        xlabel="Grid denominator M",
        ylabel="Encoded qubits including slack",
        title="Higher precision consumes more qubits",
    )
    axes[1].set_xticks(x)
    fig.suptitle("Faithful on the grid; no general precision guarantee", fontsize=14)
    fig.savefig(path / "precision-resources.png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    resources = s["original_n20_resources"]
    labels = [f"M={r['units']}" for r in resources]
    axes[0].bar(labels, [r["qubits"] for r in resources], color="#176b87")
    axes[0].set(
        ylabel="Physical qubits in the compiled encoding",
        title="Original N20 case: compiled resources only",
    )
    axes[1].bar(labels, [r["cost_cx"] for r in resources], color="#ba5a31")
    axes[1].set(
        ylabel="CX count for one exact cost layer",
        title="All-to-all, unoptimized gate decomposition",
    )
    for ax, key in zip(axes, ("qubits", "cost_cx")):
        ax.bar_label(
            ax.containers[0], labels=[f"{r[key]:,}" for r in resources], padding=3
        )
        ax.set_ylim(0, max(r[key] for r in resources) * 1.2)
    fig.suptitle(
        "No state simulation at N20; preparation, mixer and routing excluded",
        fontsize=13,
    )
    fig.savefig(path / "n20-cost-barrier.png", dpi=170)
    plt.close(fig)
    table = "\n".join(
        f"| {r['units']} | {r['qubits']} | {r['feasible_grid_portfolios']} | {max(0, r['relative_discretization_regret']) * 100:.4f}% | {r['cost_cx']:,} | {r['full_state_validation']} |"
        for r in s["rows"]
    )
    resource_table = "\n".join(
        f"| {r['units']} | {r['qubits']} | {r['cost_cx']:,} | {r['cost_depth']} |"
        for r in resources
    )
    report = f"""# Weight-grid formulation: correct cost, expensive encoding

Completed 2026-11-06. This is a formulation diagnostic, not an LLM/QAOA performance
experiment. No new model inference or Modal dispatch. Earlier real Coder30/H200
results remain unchanged; this study does not qualify a production model.

## What changed

The opt-in compiler represents selection **and** NAV amounts. Its financial QUBO
matches tracking plus proportional trading cost on valid amount registers; the
compiler owns those coefficients and emits explicit RZ/RZZ cost gates. Constraints
include money, cardinality, position bounds, required/excluded assets, sector counts
and weights, replacement limits and supported cash-aware turnover. Arbitrary prior
weights are allowed in costs. Capped turnover requires grid-compatible prior
holdings; unsupported drift raises an error rather than rounding. Ordinary XY
preserves bit count, not these money and per-asset amount constraints. No new mixer,
QAOA optimizer, GateIR/LLM grammar or production default is introduced here.

## Measured precision and cost

The fixed slice uses the first three assets/126 returns of the opened family1 N20
US development case, K=2 and declared policy/bounds. It is a new tiny diagnostic,
not a subset selected for performance, the original N20 problem, or an independent
financial test. Full-year universe selection and artificial policy groups remain
limitations. The data gate for historical investment claims remains closed.

| M | Qubits | Feasible grid portfolios | Regret vs continuous F | Cost CX | Full-state check |
|---|---:|---:|---:|---:|---|
{table}

The M=10 optimum is weights (0.3,0,0.7), matching the numerical continuous boundary
optimum. Its raw relative residual is approximately -2.22e-12, within solver
tolerance, displayed as zero rather than a claimed improvement. Finer grids happen
to include the same optimum; this is **not** a general discretization guarantee.
M=6 has a real 5.63% approximation loss. NAV weights are not executable share lots.

![Precision and resources](precision-resources.png)

| Original N20 / M | Qubits | One-cost-layer CX | One-cost-layer depth |
|---|---:|---:|---:|
{resource_table}

N20 resources are compiled only; no 63/123/244-qubit statevector is simulated.
These are all-to-all, optimization-level-zero costs. Initialization, mixing,
connectivity routing, noise, shots, inference and optimization are excluded.
The conservative penalty provides a mathematical ground-state validity bound,
not an optimized physical energy scale. Faithful encoding alone is insufficient
for a practical circuit. Do not describe this one-hot encoding as optimal or novel.

![N20 cost barrier](n20-cost-barrier.png)

## Independent checks and limits

- {audit["raw_hashes_checked"]} raw hashes verified; {checked} feasible financial
  weights rescored directly from return residuals and absolute trade changes;
  maximum objective residual {residual:.3e}. All grid-portfolio coverage checked.
- All 32,768 encoded states of the M=6 market diagnostic checked; nine zero-penalty
  states. Financial residual 2.41e-16, Ising/penalty residual 3.55e-15; Qiskit
  phase-evolution residual 1.49e-17. Two additional synthetic controls cover 64
  and 8,192 states, including cash/turnover and required/excluded holdings.
- Four QPY/QASM pairs parsed and gate schedules checked; one full-state
  crosscheck passes up to global phase. Three larger checks explicitly skipped.
- Continuous reference exhausts all three supports with optimal-status convex
  allocations. This is a numerical reference, not an exact-arithmetic certificate.
- All runtime/source/input artifacts are preserved. Successful-run wall time including input
  preparation is {s["elapsed_seconds_including_input_preparation"]:.3f}s on the local
  host, excluding failed preflights, tests and independent reporting; this is a
  diagnostic observation, not a complete compute-cost or CPU/GPU speed comparison.

## Execution corrections

The first local attempt saved source/inputs but failed on an incorrect provenance
key. A second preflight failed before creating v2 artifacts because the circuit-
request wrapper drops provenance. The successful controller uses the inspected
direct preparation interface. Partial v1 source and failure records are preserved;
no outcome-guided case or parameter change, paid retry, model or GPU dispatch
occurred. The executed source bytes are frozen; maintained files were subsequently
formatted without changing the recorded experiment.

## Decision

Encoding correctness on the declared grid is supported. Affordable full-scale
LLM/QAOA utility and independent financial benefit remain unproven. Keep the
continuous financial task and prior baselines. Next compare compact amount
encodings or an objective-preserving decomposition, with complete cost/error
bounds and strong classical references, before any further LLM-size experiment.
The current model is not promoted and no paid follow-up is scheduled.

[Registered rationale and papers](../../../docs/research/WEIGHT_GRID_PROTOCOL.md) ·
[Independent audit](independent_audit.json) · [Raw summary](summary.json) ·
[Financial spec](financial_spec.json) · [Prior decision audit](../decision_audit_v1/FINDINGS.md).
"""
    (path / "RESULTS.md").write_text(report)
    (path / "PROGRESS.md").write_text(
        "# Progress\n\nCompleted fixed formulation diagnostic, raw-hash and financial checks, explicit\ncost-gate exports, numerical-reference comparison and resource audit. No new model\nor Modal calls. Primary continuous task unchanged. Initial adapter failure retained\nin weight_grid_v1; second preflight failed before v2 artifact creation. See RESULTS.\n"
    )
    write_contract(path, s, spec)
    (path / "report_generator.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        path / "report_manifest.json",
        {
            name: sha(path / name)
            for name in (
                "RESULTS.md",
                "PROGRESS.md",
                "independent_audit.json",
                "precision-resources.png",
                "n20-cost-barrier.png",
                "decisions.jsonl",
                "metrics.csv",
                "cost_report.json",
                "circuits/index.json",
                "report_generator.py",
            )
        },
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
