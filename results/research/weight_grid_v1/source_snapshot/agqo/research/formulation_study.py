"""Exact small-support comparison of distinct target-weight financial semantics."""

from dataclasses import replace
from itertools import combinations
from pathlib import Path
from time import perf_counter
import csv
import json
import numpy as np
from .published import load, family_indices
from .finance import FinancialSpec, allocate
from .data import write_json
from .sources import capture_sources
from agqo.synthesis.profile import digest


def run(directory, data_directory="data/published_us"):
    path = Path(directory)
    if (path / "protocol.json").exists():
        raise ValueError("Use a new audit output directory.")
    x, b, dates, labels, manifest = load(data_directory)
    protocol = {
        "version": "formulation-identity-audit-v1",
        "evidence": "docs/research/FORMULATION_PROTOCOL.md",
        "scope": "Opened conditional corpus; distinct financial mandates, no primary-task replacement.",
        "n": 10,
        "k": 3,
        "training_rows": 126,
        "cutoff": str(dates[125].date()),
        "scenarios": ["base", "exclude_incumbent"],
        "policies": ["continuous", "equal_weight_target"],
        "acceptance": {"objective_abs_tolerance": 1e-9, "weight_abs_tolerance": 1e-7},
        "new_inference_calls": 0,
        "source_snapshot_manifest_hash": digest(capture_sources(path)),
    }
    write_json(path / "protocol.json", protocol)
    write_json(path / "dataset_manifest.json", manifest)
    (path / "circuits").mkdir(exist_ok=True)
    indices = family_indices(labels, 10)
    rows = []
    summaries = []
    start = perf_counter()
    for scenario in protocol["scenarios"]:
        base = FinancialSpec(
            tuple(labels[i] for i in indices),
            tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(10)),
            x[:126, indices],
            b[:126],
            np.r_[np.ones(3) / 3, np.zeros(7)],
            3,
            protocol["cutoff"],
            exclude=(labels[indices[0]],) if scenario == "exclude_incumbent" else (),
            sector_weight_caps={"policy_A": 0.7},
            maximum_weight=0.6,
            provenance="published_selection_conditioned_us_2010",
        )
        for policy in protocol["policies"]:
            spec = (
                base
                if policy == "continuous"
                else replace(base, minimum_weight=1 / 3, maximum_weight=1 / 3)
            )
            members = []
            for group in combinations(range(10), 3):
                bits = np.zeros(10, int)
                bits[list(group)] = 1
                if not spec.feasible(bits):
                    continue
                allocated = allocate(spec, bits)
                w = bits / 3
                direct = float(
                    np.mean((spec.returns @ w - spec.benchmark) ** 2)
                    + spec.cost_weight
                    * spec.cost_rate
                    * np.abs(w - spec.previous_weights).sum()
                )
                row = {
                    "scenario": scenario,
                    "policy": policy,
                    "support": bits.tolist(),
                    "proxy": spec.score(bits),
                    "direct_equal_weight_objective": direct,
                    "allocation": allocated,
                }
                if allocated["feasible"]:
                    row["target_weight_deviation"] = float(
                        np.max(abs(np.asarray(allocated["weights"]) - w))
                    )
                    row["objective_difference"] = float(allocated["objective"] - direct)
                rows.append(row)
                members.append(row)
            valid = [r for r in members if r["allocation"]["feasible"]]
            proxy_best = min(members, key=lambda r: r["proxy"])
            best = (
                min(valid, key=lambda r: r["allocation"]["objective"])
                if valid
                else None
            )
            equal = policy == "equal_weight_target"
            passed = (
                all(
                    abs(r["objective_difference"]) <= 1e-9
                    and r["target_weight_deviation"] <= 1e-7
                    for r in valid
                )
                if equal
                else None
            )
            complete = all(
                r["allocation"]["status"] in ("optimal", "infeasible") for r in members
            )
            summary = {
                "scenario": scenario,
                "policy": policy,
                "supports": len(members),
                "feasible_allocations": len(valid),
                "allocation_audit_complete": complete,
                "equal_weight_identity_passed": passed if complete and valid else None,
                "max_objective_difference": max(
                    abs(r["objective_difference"]) for r in valid
                )
                if valid
                else None,
                "max_target_weight_deviation": max(
                    r["target_weight_deviation"] for r in valid
                )
                if valid
                else None,
                "best_allocated_objective": best["allocation"]["objective"]
                if best
                else None,
                "proxy_optimum_allocated_objective": proxy_best["allocation"].get(
                    "objective"
                ),
                "proxy_optimum_feasible": proxy_best["allocation"]["feasible"],
                "problem_hash": spec.fingerprint(),
            }
            if best and proxy_best["allocation"]["feasible"]:
                regret = (
                    proxy_best["allocation"]["objective"]
                    - best["allocation"]["objective"]
                )
                summary["proxy_optimum_allocation_regret"] = regret
                summary["relative_regret"] = regret / max(
                    abs(best["allocation"]["objective"]), 1e-12
                )
            summaries.append(summary)
            (path / "decisions.jsonl").write_text(
                "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows)
            )
    write_json(path / "audit.json", {"summaries": summaries, "new_inference_calls": 0})
    with (path / "metrics.csv").open("w", newline="") as stream:
        fields = sorted({key for r in summaries for key in r})
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    write_json(
        path / "cost_report.json",
        {
            "new_inference_calls": 0,
            "gpu_seconds": 0,
            "allocation_queries": len(rows),
            "elapsed_seconds": perf_counter() - start,
            "execution": "classical exact support enumeration and convex allocation",
        },
    )
    text = [
        "# Financial formulation identity audit",
        "",
        protocol["scope"],
        "",
        "| Scenario | Target weights | Feasible/attempted | Exact-identity gate | Relative proxy allocation regret |",
        "|---|---|---:|---|---:|",
    ]
    for r in summaries:
        text.append(
            f"| {r['scenario']} | {r['policy']} | {r['feasible_allocations']}/{r['supports']} | {r['equal_weight_identity_passed']} | {r.get('relative_regret', 'unavailable')} |"
        )
    text += [
        "",
        "The equal-weight alternative is a different, explicit financial mandate. Its allocator remains common and keeps the support, but cannot redistribute weights. Numerical identity does not establish its economic superiority. Continuous allocation remains the primary task and its distortion remains visible.",
        "",
        "Do not label a proxy-energy improvement as continuous-allocation financial value. Select the business target before model tuning; richer weight encodings and allocation-aware outer methods require separately counted resources. No model, investment performance or quantum advantage is qualified by this audit.",
    ]
    (path / "RESULTS.md").write_text("\n".join(text) + "\n")
    gate = all(
        r["equal_weight_identity_passed"] is True
        for r in summaries
        if r["policy"] == "equal_weight_target"
    )
    (path / "PROGRESS.md").write_text(
        f"# Progress\n\nEqual-weight identity gate passed: {gate}. Primary continuous task unchanged; no inference.\n"
    )
    return {
        "status": "completed" if gate else "failed",
        "equal_weight_identity_passed": gate,
        "allocation_queries": len(rows),
        "output": str(path),
    }
