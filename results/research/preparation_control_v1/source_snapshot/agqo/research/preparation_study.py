"""Frozen non-LLM preparation control, with full source/resource accounting."""

from pathlib import Path
from time import perf_counter
import csv
import json
import math
import numpy as np
from .data import write_json
from .published import load, family_indices
from .published_study import conditional_path
from .finance import FinancialSpec
from .design import baseline, lower
from .quantum import compile_cost, verify, evaluate, export
from .preparation import with_counter_dicke
from .runner import postprocess_samples
from .sources import capture_sources
from agqo.synthesis.profile import digest


def run(directory, data_directory="data/published_us"):
    path = Path(directory)
    if (path / "protocol.json").exists():
        raise ValueError("Use a new output directory; never overwrite this experiment.")
    x, b, dates, labels, manifest = load(data_directory)
    protocol = {
        "version": "preparation-control-v1",
        "evidence": "docs/research/PREPARATION_PROTOCOL.md",
        "scope": "Opened conditional-US development; no model/financial/quantum advantage qualification.",
        "cases": [[10, 3], [30, 6]],
        "seeds": [11, 23, 37],
        "methods": ["three_pair", "counter_dicke", "uniform"],
        "evaluations": 16,
        "shots": 128,
        "allocation_queries": 32,
        "training_rows": 126,
        "cutoff": str(dates[125].date()),
        "test_rows": 126,
        "new_inference_calls": 0,
        "same_financial_objective_and_cost_hamiltonian": True,
        "workspace": "Clean binary counter; counted in circuit resources, eliminated only from ideal simulation after analytic proof and small-case checks.",
        "acceptance": {
            "amplitude_tolerance": 1e-9,
            "workspace_leakage_tolerance": 1e-9,
            "max_simulation_states": 2000000,
        },
        "source_snapshot_manifest_hash": digest(capture_sources(path)),
    }
    write_json(path / "protocol.json", protocol)
    write_json(path / "dataset_manifest.json", manifest)
    (path / "circuits").mkdir(exist_ok=True)
    start = perf_counter()
    records = []
    for n, k in protocol["cases"]:
        indices = family_indices(labels, n)
        spec = FinancialSpec(
            tuple(labels[i] for i in indices),
            tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(n)),
            x[:126, indices],
            b[:126],
            np.r_[np.ones(k) / k, np.zeros(n - k)],
            k,
            protocol["cutoff"],
            sector_weight_caps={"policy_A": 0.7},
            maximum_weight=0.6,
            provenance="published_selection_conditioned_us_2010",
        )
        h = compile_cost(spec, constrained_subspace=True)
        for mode in protocol["methods"]:
            ir = None
            verification = None
            if mode != "uniform":
                ir = lower(baseline(spec, "fixed"), spec, h)
                if mode == "counter_dicke":
                    ir = with_counter_dicke(ir, spec)
                verification = verify(ir, spec, h)
                write_json(
                    path / "circuits" / f"n{n}_{mode}" / "verification.json",
                    verification,
                )
            for seed in protocol["seeds"]:
                clock = perf_counter()
                row = {
                    "n": n,
                    "k": k,
                    "method": mode,
                    "seed": seed,
                    "status": "failed",
                    "feasible": False,
                    "problem_hash": spec.fingerprint(),
                    "hamiltonian_hash": h["hamiltonian_hash"],
                    "all_cardinality_supports": math.comb(n, k),
                }
                if verification is not None:
                    row["verification"] = verification
                try:
                    if mode == "uniform":
                        rng = np.random.default_rng(seed)
                        samples = [
                            sum(1 << int(i) for i in rng.choice(n, k, replace=False))
                            for _ in range(128)
                        ]
                        row["selection"] = {
                            "final_support_draws": 128,
                            "optimizer_shots": 0,
                            "execution": "classical_uniform_cardinality_sampler",
                        }
                    else:
                        if not verification["valid"]:
                            raise ValueError(
                                "Preparation/circuit correctness gate failed; no dense fallback."
                            )
                        row["selection"] = evaluate(
                            ir, spec, h, seed=seed, evaluations=16, shots=128
                        )
                        samples = row["selection"]["sampled_support_indices"]
                        export(
                            ir,
                            h,
                            row["selection"]["angles"],
                            verification,
                            path / "circuits" / f"n{n}_{mode}" / f"seed_{seed}",
                        )
                    allocation = postprocess_samples(spec, samples, 32)
                    row.update(
                        allocation=allocation,
                        feasible=allocation["feasible"],
                        status="feasible"
                        if allocation["feasible"]
                        else allocation["status"],
                    )
                    if allocation["feasible"]:
                        row["conditional_path"] = conditional_path(
                            spec, allocation["weights"], x[126:, indices], b[126:]
                        )
                except Exception as exc:
                    row["error"] = str(exc)
                row["elapsed_seconds"] = perf_counter() - clock
                records.append(row)
                (path / "decisions.jsonl").write_text(
                    "".join(json.dumps(r, allow_nan=False) + "\n" for r in records)
                )
                print(
                    f"N{n} {mode} seed={seed}: {row['status']} ({row['elapsed_seconds']:.2f}s)",
                    flush=True,
                )
    fields = [
        "n",
        "k",
        "method",
        "seed",
        "status",
        "allocated_objective",
        "proxy_expectation",
        "proxy_regret",
        "feasible_probability",
        "probability_supports",
        "simulation_states",
        "qubits",
        "workspace_qubits",
        "cx",
        "depth",
        "allocation_queries",
        "seconds",
    ]
    with (path / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in records:
            a = r.get("allocation", {})
            s = r.get("selection", {})
            v = r.get("verification", {}).get("resources", {})
            writer.writerow(
                {
                    "n": r["n"],
                    "k": r["k"],
                    "method": r["method"],
                    "seed": r["seed"],
                    "status": r["status"],
                    "allocated_objective": a.get("objective"),
                    "proxy_expectation": s.get("conditional_proxy_expectation"),
                    "proxy_regret": s.get("expected_proxy_regret"),
                    "feasible_probability": s.get("selection_feasible_probability"),
                    "probability_supports": s.get("nonnegligible_probability_supports"),
                    "simulation_states": s.get("simulation_states"),
                    "qubits": v.get("qubits"),
                    "workspace_qubits": v.get("preparation_workspace_qubits"),
                    "cx": v.get("transpiled_cx"),
                    "depth": v.get("transpiled_depth"),
                    "allocation_queries": a.get("allocation_queries"),
                    "seconds": r["elapsed_seconds"],
                }
            )
    write_json(
        path / "cost_report.json",
        {
            "new_inference_calls": 0,
            "gpu_seconds": 0,
            "cpu_elapsed_seconds": perf_counter() - start,
            "exact_diagnostics_not_hardware_access": True,
            "rows": [
                {
                    "n": r["n"],
                    "method": r["method"],
                    "seed": r["seed"],
                    "optimization_and_final_shots": r.get("selection", {}).get(
                        "total_shots", 0
                    ),
                    "classical_uniform_draws": r.get("selection", {}).get(
                        "final_support_draws", 0
                    ),
                    "diagnostic_supports_scored": r.get("selection", {}).get(
                        "diagnostic_supports_scored", 0
                    ),
                    "allocation_queries": r.get("allocation", {}).get(
                        "allocation_queries", 0
                    ),
                    "elapsed_seconds": r["elapsed_seconds"],
                }
                for r in records
            ],
            "verification_cost": "One verification per case/preparation, reused across seeds; includes exact classical parameter-activity checks.",
            "logical_resources": "Full preparation/cost decomposition, all-to-all basis; no device routing or noise.",
        },
    )
    lines = [
        "# Broad-support preparation control",
        "",
        protocol["scope"],
        "",
        "| N | Method | Seed | Status | Allocated objective | Probability supports | Qubits | CX | Depth |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for r in records:
        a = r.get("allocation", {})
        s = r.get("selection", {})
        v = r.get("verification", {}).get("resources", {})
        lines.append(
            f"| {r['n']} | {r['method']} | {r['seed']} | {r['status']} | {a.get('objective', '—')} | {s.get('nonnegligible_probability_supports', '—')} | {v.get('qubits', '—')} | {v.get('transpiled_cx', '—')} | {v.get('transpiled_depth', '—')} |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "Counter-Dicke is a distinct compiler-owned construction, not a replication of the ancilla-free paper. Workspace is physically counted and proven clean before cost/mixer execution. Large ideal simulation eliminates that clean workspace; full large-register Qiskit comparison is not claimed.",
        "",
        "The fixed mixer graph, financial coefficients, shots and post-allocation policy are identical between circuit preparations. Uniform classical draws additionally avoid all optimizer shots and circuit overhead. Increased preparation depth may erase any benefit under noise; this run is ideal CPU simulation.",
        "",
        "Read proxy and allocated objectives separately. More support coverage alone does not establish better decisions. Three seeds, opened data and selection-conditioned membership do not qualify an LLM or unbiased investment strategy.",
        "",
        "H1 financial value: inconclusive. H2 LLM value: inconclusive (no LLM run). H3 adaptive QAOA value: inconclusive. Quantum advantage: unsupported by these ideal classical simulations.",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    failures = sum(not r["feasible"] for r in records)
    (path / "PROGRESS.md").write_text(
        f"# Progress\n\nFinished {len(records)} rows, {failures} without a feasible allocation. All failures retained. No new inference; original investment-data gate remains blocked.\n"
    )
    return {
        "status": "completed",
        "rows": len(records),
        "failures": failures,
        "output": str(path),
    }
