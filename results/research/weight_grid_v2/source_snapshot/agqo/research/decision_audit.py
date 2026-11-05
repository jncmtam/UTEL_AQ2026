"""Allocation-table and frozen-distribution diagnostics, never a production oracle."""

from collections import Counter
from pathlib import Path
import json
from time import perf_counter
import numpy as np

from agqo.synthesis.profile import digest
from .counterfactual_editor import prepare as old_inputs
from .data import sha, write_json
from .frozen_numerics import bind
from .improvement import decode
from .finance import allocate
from .symmetry import ConservedBasis
from .cloud_pipeline import objective_bound
from .finite_budget import decision_metrics, expected_minimum, hit_probability

RUN_ID = "decision_audit_v1"


def validate_allocation(spec, index, allocation):
    if not allocation.get("feasible") or allocation["status"] != "optimal":
        return False
    bits = [(index >> q) & 1 for q in range(spec.n)]
    w = np.asarray(allocation["weights"], float)
    if allocation["support"] != bits or spec.violations(bits) or spec.violations_weights(w):
        raise ValueError("Cached allocation violates the frozen financial mandate.")
    if np.any(abs(w[np.array(bits) == 0]) > 1e-8):
        raise ValueError("Cached support membership changed.")
    matrix, linear, offset = spec.quadratic()
    value = float(w @ matrix @ w + linear @ w + offset + spec.cost_weight*spec.cost_rate*abs(w-spec.previous_weights).sum())
    if abs(value-allocation["objective"]) > 1e-10:
        raise ValueError("Cached allocation does not reproduce financial F.")
    return True


def prepare():
    original = old_inputs()
    cases = original["cases"]
    cache = {c["id"]: {} for c in cases}
    decoded = {c["id"]: bind(decode(c["spec"]), c["frozen_numerics"])[0] for c in cases}
    provenance, reused, duplicates, ignored = [], 0, 0, 0
    for run_id in ("live_gpu_optimization_v1", "counterfactual_editor_v4"):
        root = Path("results/research") / run_id
        manifest = json.loads((root / "orchestration/download_manifest.json").read_text())
        for name, expected in manifest.items():
            if sha(root / "evaluation" / name) != expected:
                raise ValueError("Source experiment artifact changed.")
        for file in sorted((root / "evaluation/runs").glob("*.json")):
            row = json.loads(file.read_text())
            cid = row["case_id"]
            if cid not in cache or row["status"] != "completed":
                continue
            stats = json.loads((root / "evaluation/cases" / cid / "sufficient_statistics.json").read_text())
            if stats["source_spec_hash"] != decoded[cid].fingerprint():
                raise ValueError("Cached record belongs to another financial instance.")
            provenance.append({"path": str(file), "sha256": sha(file)})
            for key, allocation in row["result"]["allocation_results"].items():
                if not validate_allocation(decoded[cid], int(key), allocation):
                    ignored += 1
                    continue
                if key in cache[cid]:
                    old = cache[cid][key]
                    if abs(old["allocation"]["objective"]-allocation["objective"]) > 1e-10:
                        raise ValueError("Conflicting cached financial values.")
                    old["duplicate_count"] += 1
                    duplicates += 1
                else:
                    cache[cid][key] = {"allocation": allocation, "first_source": str(file), "duplicate_count": 0}
                    reused += 1
    frozen = Path("results/research/counterfactual_editor_v4/evaluation")
    samplers = []
    for file in sorted((frozen / "runs").glob("*.json")):
        row = json.loads(file.read_text())
        if row["phase"] == "evaluation" and row["method"] in ("aggregate", "counterfactual", "current", "teacher"):
            if row["status"] != "completed":
                raise ValueError("The fixed sampler source did not complete.")
            samplers.append({"case_id": row["case_id"], "method": row["method"], "seed": row["seed"],
                "gate_ir": row["admission"]["gate_ir"], "verification": row["admission"]["verification"],
                "angles": row["result"]["angles"], "fit_incumbent": row["result"]["observations"][511]["best_objective"],
                "observed_best_576": row["result"]["allocation"]["objective"],
                "source_file": str(file), "source_sha256": sha(file)})
    result = {"cases": cases, "cache": cache, "samplers": samplers,
        "dataset_manifest": original["dataset_manifest"], "cache_provenance": provenance,
        "cache_counts": {"unique_reused": reused, "duplicate_records": duplicates, "ignored_unresolved_or_nonoptimal": ignored}}
    result["input_hash"] = digest(result)
    return result


def check_inputs(inputs):
    if inputs["input_hash"] != digest({k: v for k, v in inputs.items() if k not in ("input_hash", "protocol")}):
        raise ValueError("Prepared source/cache/financial inputs changed.")


def build_tables(directory, inputs, checkpoint=lambda: None):
    check_inputs(inputs)
    path = Path(directory)
    if path.exists():
        raise ValueError("Existing table stage retained; no automatic rerun.")
    path.mkdir(parents=True)
    write_json(path / "protocol.json", inputs["protocol"])
    write_json(path / "dataset_manifest.json", inputs["dataset_manifest"])
    write_json(path / "cache_provenance.json", {"source_files": inputs["cache_provenance"], **inputs["cache_counts"]})
    write_json(path / "frozen_samplers.json", inputs["samplers"])
    start, summaries = perf_counter(), []
    for case in inputs["cases"]:
        cid = case["id"]
        spec, h, certificate = bind(decode(case["spec"]), case["frozen_numerics"])
        basis = ConservedBasis(spec, h)
        matrix, linear, offset = spec.quadratic()
        write_json(path / "cases" / cid / "sufficient_statistics.json", {
            "matrix": matrix.tolist(), "linear": linear.tolist(), "offset": offset,
            "financial_spec_without_returns": {k: v for k, v in spec.to_dict().items() if k not in ("returns", "benchmark")},
            "source_spec_hash": spec.fingerprint()})
        write_json(path / "cases" / cid / "numerical_transport.json", certificate)
        bound, rows, new_queries, reuse = objective_bound(spec), [], 0, 0
        file = path / "cases" / cid / "allocation_table.jsonl"
        with file.open("w") as handle:
            for index in map(int, basis.asset_indices):
                saved = inputs["cache"][cid].get(str(index))
                if saved:
                    allocation = saved["allocation"]
                    validate_allocation(spec, index, allocation)
                    reuse += 1
                    origin = {"kind": "reused", "first_source": saved["first_source"], "duplicate_count": saved["duplicate_count"]}
                else:
                    allocation = allocate(spec, [(index >> q) & 1 for q in range(spec.n)])
                    new_queries += 1
                    origin = {"kind": "new_common_allocator_call"}
                value = allocation["objective"] if allocation.get("feasible") else 2*bound
                if not np.isfinite(value) or not -1e-10 <= value <= 2*bound*(1+1e-7):
                    raise ValueError("Allocation-table loss bound violated.")
                row = {"support_index": index, "allocation": allocation, "operational_score": value, "origin": origin}
                rows.append(row)
                handle.write(json.dumps(row, allow_nan=False)+"\n")
                if len(rows) % 512 == 0:
                    handle.flush()
                    checkpoint()
        valid = [r for r in rows if r["allocation"].get("feasible")]
        if not valid:
            raise ValueError("No feasible numerical allocation reference.")
        best = min(valid, key=lambda r: r["operational_score"])
        status = dict(Counter(r["allocation"]["status"] for r in rows))
        proxy = np.array([spec.score([(r["support_index"] >> q) & 1 for q in range(spec.n)]) for r in rows])
        proxy_index = int(np.argmin(proxy))
        np.save(path / "cases" / cid / "proxy_scores.npy", proxy)
        summary = {"case_id": cid, "supports": len(rows), "new_allocator_calls": new_queries,
            "reused_optimal_allocations": reuse, "status_counts": status, "objective_bound": bound,
            "best_feasible_F": best["operational_score"], "best_support_index": best["support_index"],
            "numerical_reference_complete": all(r["allocation"]["status"] in ("optimal", "infeasible") for r in rows),
            "joint_optimality_certificate": False,
            "proxy_best_support": rows[proxy_index]["support_index"],
            "proxy_best_allocation": rows[proxy_index]["allocation"],
            "proxy_best_allocated_regret_pct": 100*(rows[proxy_index]["operational_score"]/best["operational_score"]-1) if rows[proxy_index]["allocation"].get("feasible") else None}
        summaries.append(summary)
        write_json(path / "cases" / cid / "table_summary.json", summary)
        checkpoint()
    summary = {"input_hash": inputs["input_hash"], "cases": summaries, "elapsed_seconds": perf_counter()-start,
        "new_allocator_calls": sum(s["new_allocator_calls"] for s in summaries), "scope": "Exhaustive numerical diagnostic; exponential, not a deployable financial oracle or solver win"}
    write_json(path / "table_completion.json", summary)
    checkpoint()
    return summary


def audit_gpu(directory, inputs, checkpoint=lambda: None):
    from .cuda_simulation import TorchConservedBasis, crosscheck_cuda
    check_inputs(inputs)
    path = Path(directory)
    if (path / "completion.json").exists():
        raise ValueError("Completed GPU audit retained; no repeat dispatch.")
    table_summary = json.loads((path / "table_completion.json").read_text())
    if table_summary["input_hash"] != inputs["input_hash"]:
        raise ValueError("CPU table source identity differs.")
    start, records, physical = perf_counter(), [], {}
    for case in inputs["cases"]:
        cid = case["id"]
        spec, h, _ = bind(decode(case["spec"]), case["frozen_numerics"])
        table = [json.loads(s) for s in (path / "cases" / cid / "allocation_table.jsonl").read_text().splitlines()]
        indices = np.array([r["support_index"] for r in table])
        scores = np.array([r["operational_score"] for r in table])
        feasible = np.array([r["allocation"].get("feasible", False) for r in table])
        uncertain = np.array([r["allocation"]["status"] not in ("optimal", "infeasible") for r in table])
        lower = scores.copy()
        lower[uncertain] = 0.
        summary = json.loads((path / "cases" / cid / "table_summary.json").read_text())
        threshold = 1.05*summary["best_feasible_F"]
        samplers = [s for s in inputs["samplers"] if s["case_id"] == cid]
        first = samplers[0]
        write_json(path / "cases" / cid / "cuda_selfcheck.json", crosscheck_cuda(spec, h, first["gate_ir"], [first["angles"]]))
        for sampler in samplers + [{"method": "uniform_conditioned", "seed": None, "fit_incumbent": None}]:
            if sampler["method"] == "uniform_conditioned":
                probability = np.ones(len(indices))/len(indices)
                signature, execution = "uniform", {"execution": "analytic_conditioned_uniform_not_quantum"}
            else:
                ir = sampler["gate_ir"]
                signature = digest({"physical_ir": {k: ir.get(k) for k in ("initial_bits", "initialization", "preparation", "layers", "parameters")}, "h": h["hamiltonian_hash"], "angles": sampler["angles"]})
                if signature not in physical:
                    basis = TorchConservedBasis(spec, h)
                    if not np.array_equal(basis.asset_indices, indices):
                        raise ValueError("Probability basis and exhaustive table differ.")
                    state = basis.execute(sampler["gate_ir"], h, sampler["angles"])
                    p = (abs(state)**2).reshape((-1, len(indices))).sum(axis=0)
                    if abs(p.sum()-1)>1e-10:
                        raise ValueError("CUDA sampler is not normalized.")
                    p /= p.sum()
                    physical[signature] = (p, basis.execution_metadata())
                    dest = path / "probabilities" / f"{signature}.npz"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    np.savez_compressed(dest, indices=indices, probabilities=p)
                probability, execution = physical[signature]
            good_mass = float(probability[feasible & (scores<=threshold)].sum())
            curves = []
            for shots in (1, 8, 64, 576, 4096):
                row = decision_metrics(scores, probability, feasible, shots, sampler.get("fit_incumbent"))
                row.update(hit_probability=hit_probability(min(1., good_mass), shots),
                    status_sensitivity_lower=expected_minimum(lower, probability, shots, sampler.get("fit_incumbent")),
                    status_sensitivity_upper=expected_minimum(scores, probability, shots, sampler.get("fit_incumbent")))
                curves.append(row)
            record = {"case_id": cid, "method": sampler["method"], "seed": sampler["seed"],
                "sampler_signature": signature, "execution": execution, "curves": curves,
                "fit_incumbent": sampler.get("fit_incumbent"), "observed_best_576": sampler.get("observed_best_576"),
                "algorithmic_hit_threshold": threshold, "uncertain_probability": float(probability[uncertain].sum()),
                "source_file": sampler.get("source_file"), "source_sha256": sampler.get("source_sha256")}
            records.append(record)
            write_json(path / "distribution_records.json", records)
            checkpoint()
    summary = {"input_hash": inputs["input_hash"], "logical_distributions": len(records),
        "unique_cuda_evaluations": len(physical), "new_llm_calls": 0, "new_angle_optimizations": 0,
        "elapsed_gpu_stage_seconds": perf_counter()-start, "financial_qualification": False}
    write_json(path / "completion.json", summary)
    checkpoint()
    return summary
