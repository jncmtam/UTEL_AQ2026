"""Frozen, resumable experiment artifacts with honest failed-run accounting."""

from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import csv
import json
from time import perf_counter
import numpy as np
from agqo.synthesis.budget import MODEL_CATALOG, configured_budget, billing_snapshot
from agqo.synthesis.client import SynthesisClient
from agqo.synthesis.profile import digest, data_profile
from .data import write_json
from .finance import (
    FinancialSpec,
    allocate,
    audit_proxy,
    joint_reference,
    diagnose,
    Account,
)
from .design import baseline, lower, request, mutate
from .quantum import compile_cost, verify, evaluate, export


def cases(split="development"):
    output = []
    for n in (6, 8, 10):
        seed = {"development": 2101, "validation": 5101, "test": 7101}[split] + n
        rng = np.random.default_rng(seed)
        factors = rng.normal(0, 0.008, (252, 2))
        loadings = rng.normal(0, 1, (2, n))
        returns = factors @ loadings + rng.normal(0.0002, 0.006, (252, n))
        benchmark = returns.mean(axis=1)
        k = 3 if n == 6 else 4
        spec = FinancialSpec(
            tuple(f"ASSET_{i:02}" for i in range(n)),
            tuple("Sector_A" if i < n // 2 else "Sector_B" for i in range(n)),
            returns,
            benchmark,
            np.r_[np.ones(k) / k, np.zeros(n - k)],
            k,
            "synthetic_cutoff",
            sector_count_caps={"Sector_A": k - 1},
            sector_weight_caps={"Sector_A": 0.7},
            maximum_weight=0.5,
            provenance="synthetic_structural_diagnostic_not_market",
        )
        output.append((f"{split}_n{n}", spec))
    return output


def evaluate_design(spec, h, program, seeds, evaluations, shots, path):
    ir = lower(program, spec, h)
    verification = verify(ir, spec, h)
    output = {"program": program, "verification": verification, "runs": []}
    if verification["valid"]:
        for seed in seeds:
            run = evaluate(ir, spec, h, seed, evaluations, shots)
            run["allocation"] = postprocess_samples(
                spec, run["sampled_support_indices"], budget=32
            )
            output["runs"].append(run)
        if output["runs"]:
            export(ir, h, output["runs"][0]["angles"], verification, path)
    return output


def run(
    directory,
    mode="offline",
    models=("coder30", "next80"),
    split="development",
    evaluations=16,
    shots=128,
    seeds=(11, 23, 47),
    proposals=1,
    ablation="full",
    feedback="quality",
):
    if mode not in ("offline", "modal", "replay") or proposals not in (1, 4, 8):
        raise ValueError("Unsupported mode or proposal budget.")
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    context = cases(split)
    protocol = {
        "version": "research-v3.3",
        "mode": mode,
        "split": split,
        "models": {m: MODEL_CATALOG[m] for m in models},
        "ablation": ablation,
        "feedback": feedback,
        "cases": [{"id": name, "hash": spec.fingerprint()} for name, spec in context],
        "seeds": list(seeds),
        "evaluations_per_candidate_seed": evaluations,
        "shots": shots,
        "proposals_per_method": proposals,
        "targets": {
            "first_pass_validity": 0.95,
            "relative_gap_or_resource_improvement": 0.2,
            "fidelity": 1 - 1e-9,
            "cardinality_leakage": 1e-9,
        },
        "purpose": "structural_smoke_not_model_qualification",
        "finance_claims_allowed": False,
        "selection_rule": "validity_then_selection_feasibility_then_conditional_proxy_regret_then_cx",
        "feedback_schedule": "Four initial proposals, then two rounds of two when budget=8; all trials charged.",
        "baseline_scope": "Same grammar, angle budgets and proposal counts; fixed/rules use repeated angle starts, LLM inference adds overhead.",
        "postprocessing": "At most 32 unique sampled, support-feasible portfolios, ordered by proxy then support index; common allocator; choose allocated objective. All queries counted.",
        "source_hash": digest(
            {f.name: f.read_text() for f in sorted(Path(__file__).parent.glob("*.py"))}
        ),
    }
    frozen = path / "protocol.json"
    if frozen.exists() and json.loads(frozen.read_text()) != protocol:
        raise ValueError("Protocol differs: use a new output directory.")
    write_json(frozen, protocol)
    write_json(
        path / "dataset_manifest.json",
        {
            "version": "synthetic-v3",
            "dataset_kind": "synthetic_structural_diagnostic",
            "financial_evaluation_allowed": False,
            "reason": "Software and method smoke only; historical US cohort audit is separate.",
            "cases": protocol["cases"],
        },
    )
    records = []
    references = {}
    contexts = {}
    for name, spec in context:
        diagnosis = diagnose(spec)
        h = compile_cost(spec)
        contexts[name] = (spec, h)
        references[name] = {
            "diagnosis": diagnosis,
            "joint_reference": joint_reference(spec),
            "proxy_audit": audit_proxy(spec),
        }
        write_json(path / name / "financial_spec.json", spec.to_dict())
        write_json(path / name / "hamiltonian.json", h)
        for method in ("fixed", "rules", "random", "adaptive"):
            best_program = baseline(spec, "rules" if method == "adaptive" else method)
            best_rank = (1, 1, float("inf"), float("inf"))
            for candidate in range(proposals):
                program = (
                    mutate(best_program, spec, 1000 + candidate)
                    if method == "adaptive" and candidate
                    else baseline(spec, "random", seed=1000 + candidate)
                    if method == "random"
                    else best_program
                )
                record = {
                    "case_id": name,
                    "method": method,
                    "candidate": candidate,
                    "execution": "classical_design",
                }
                try:
                    record.update(
                        evaluate_design(
                            spec,
                            h,
                            program,
                            tuple(seed + 100 * candidate for seed in seeds),
                            evaluations,
                            shots,
                            path / "circuits" / name / method / str(candidate),
                        )
                    )
                except Exception as exc:
                    record.update(
                        verification={
                            "valid": False,
                            "errors": [{"message": str(exc)}],
                        },
                        runs=[],
                    )
                records.append(record)
                if (
                    method == "adaptive"
                    and record.get("runs")
                    and (candidate == 0 or rank(record) < best_rank)
                ):
                    best_program = program
                    best_rank = rank(record)
        # Uniform feasible sampling is a necessary control on small spaces.
        uniform_runs = []
        from itertools import combinations

        supports = []
        for selected in combinations(range(spec.n), spec.k):
            bits = np.zeros(spec.n, int)
            bits[list(selected)] = 1
            if spec.feasible(bits):
                supports.append(sum(int(bit) << q for q, bit in enumerate(bits)))
        for seed in seeds:
            total = (evaluations + 1) * shots
            samples = (
                np.random.default_rng(seed).choice(supports, size=total).tolist()
                if supports
                else []
            )
            uniform_runs.append(
                {
                    "seed": seed,
                    "selection_feasible_probability": 1.0 if supports else 0.0,
                    "expected_proxy_regret": None,
                    "allocation": postprocess_samples(spec, samples, 32),
                    "total_shots": total,
                    "execution": "classical_uniform_feasible_enumerated_reference",
                    "evaluated_feasible_support_count": len(supports),
                }
            )
        records.append(
            {
                "case_id": name,
                "method": "uniform_feasible",
                "candidate": 0,
                "execution": "classical_sampling_control",
                "verification": {
                    "valid": True,
                    "circuit": False,
                    "resources": {"transpiled_cx": 0},
                },
                "runs": uniform_runs,
            }
        )
        write_json(path / "references.json", references)
        write_json(path / "records.json", records)
    billing_before = None
    if mode == "modal":
        billing_before = billing_snapshot()
        write_json(path / "billing_before.json", billing_before)
    if mode != "offline":
        for model in models:
            ledger = configured_budget(ledger_path=str(path / "budget.json"))
            client = SynthesisClient(
                model, mode, path / "inference", ledger=ledger, prefetch=True
            )
            for candidate in range(proposals):
                requests = []
                for name, (spec, h) in contexts.items():
                    previous = [
                        r
                        for r in records
                        if r["case_id"] == name and r["method"] == model
                    ]
                    feedback_items = []
                    if candidate >= 4 and feedback != "none":
                        feedback_items = [
                            {
                                "verification": r["verification"],
                                "quality": [
                                    {
                                        "selection_feasible_probability": s.get(
                                            "selection_feasible_probability"
                                        ),
                                        "expected_proxy_regret": s.get(
                                            "expected_proxy_regret"
                                        ),
                                    }
                                    for s in r["runs"]
                                ]
                                if feedback == "quality"
                                else [],
                            }
                            for r in previous[: 4 + 2 * ((candidate - 4) // 2)][-2:]
                        ]
                    donor = (
                        data_profile(
                            replace(
                                spec,
                                returns=np.random.default_rng(993)
                                .permutation(spec.returns.T)
                                .T,
                            )
                        )
                        if ablation == "shuffled"
                        else None
                    )
                    requests.append(
                        request(
                            spec,
                            h,
                            seed=100 + candidate,
                            feedback=feedback_items,
                            ablation=ablation,
                            donor=donor,
                        )
                    )
                answers = client.batch(requests)
                for (name, (spec, h)), req, answer in zip(
                    contexts.items(), requests, answers, strict=True
                ):
                    record = {
                        "case_id": name,
                        "method": model,
                        "candidate": candidate,
                        "request_hash": req["request_hash"],
                        "inference": answer,
                        "execution": answer.get("execution", answer.get("status")),
                        "verification": {"valid": False, "errors": []},
                        "runs": [],
                    }
                    if answer.get("status") == "ok":
                        try:
                            record.update(
                                evaluate_design(
                                    spec,
                                    h,
                                    answer["response"],
                                    seeds,
                                    evaluations,
                                    shots,
                                    path / "circuits" / name / model / str(candidate),
                                )
                            )
                        except Exception as exc:
                            record["verification"] = {
                                "valid": False,
                                "errors": [{"message": str(exc)}],
                            }
                    else:
                        record["verification"]["errors"] = [
                            {"message": answer.get("reason", answer.get("status"))}
                        ]
                    records.append(record)
                write_json(path / "records.json", records)
    # These are independent state-matched decisions, not continuous trajectories.
    # Continuous accounts are evaluated by workflow.run_trajectory.
    decisions = []
    for method in sorted({r["method"] for r in records}):
        for name, spec in context:
            eligible = [
                r
                for r in records
                if r["case_id"] == name and r["method"] == method and r.get("runs")
            ]
            if not eligible:
                decisions.append(
                    {"case_id": name, "method": method, "status": "no_valid_circuit"}
                )
                continue
            chosen = min(eligible, key=rank)
            run0 = chosen["runs"][0]
            allocation = run0["allocation"]
            decision = {
                "case_id": name,
                "method": method,
                "candidate": chosen["candidate"],
                "allocation": allocation,
                "execution": "synthetic_matched_state_decision",
            }
            if allocation.get("feasible"):
                account = Account(
                    100000 * spec.previous_weights.copy(),
                    100000 * (1 - spec.previous_weights.sum()),
                )
                decision["order"] = account.rebalance(
                    allocation["weights"], spec.cost_rate
                )
                decision["post_trade_weights"] = account.weights().tolist()
            decisions.append(decision)
    (path / "decisions.jsonl").write_text(
        "".join(json.dumps(d, allow_nan=False) + "\n" for d in decisions)
    )
    rows = []
    for record in records:
        for result in record.get("runs") or [{}]:
            rows.append(
                {
                    "case_id": record["case_id"],
                    "method": record["method"],
                    "candidate": record["candidate"],
                    "valid": record["verification"]["valid"],
                    "seed": result.get("seed"),
                    "execution": record["execution"],
                    "selection_feasible_probability": result.get(
                        "selection_feasible_probability"
                    ),
                    "expected_proxy_regret": result.get("expected_proxy_regret"),
                    "probability_optimal": result.get("probability_optimal"),
                    "allocation_feasible": result.get("allocation", {}).get(
                        "feasible", False
                    ),
                    "allocation_queries": result.get("allocation", {}).get(
                        "allocation_queries", 0
                    ),
                    "allocated_objective": result.get("allocation", {}).get(
                        "objective"
                    ),
                    "shots": result.get("total_shots", 0),
                    "transpiled_cx": record["verification"]
                    .get("resources", {})
                    .get("transpiled_cx"),
                }
            )
    with (path / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    cost = {
        "mode": mode,
        "elapsed_seconds": perf_counter() - start,
        "total_optimizer_shots": sum(r["shots"] for r in rows),
        "billing_before": billing_before,
        "billing_after": billing_snapshot() if mode == "modal" else None,
        "reservation_is_not_invoice": True,
        "failed_trials_included": True,
    }
    write_json(path / "cost_report.json", cost)
    report(path, records, references, protocol)
    return {
        "output": str(path),
        "candidates": len(records),
        "valid": sum(r["verification"]["valid"] for r in records),
        "mode": mode,
    }


def rank(record):
    runs = record.get("runs", [])
    if not runs:
        return (1, 1, float("inf"), float("inf"))
    return (
        0,
        -float(np.mean([r["selection_feasible_probability"] for r in runs])),
        float(
            np.mean(
                [
                    r["expected_proxy_regret"]
                    if r["expected_proxy_regret"] is not None
                    else 1e9
                    for r in runs
                ]
            )
        ),
        record["verification"].get("resources", {}).get("transpiled_cx", 1e9),
    )


def report(path, records, references, protocol):
    lines = [
        "# AGQO measured results",
        "",
        "Execution: "
        + protocol["mode"]
        + ". Dataset: synthetic structural diagnostics.",
        "",
        "**No market investment-performance or quantum-advantage claim is supported by this run.**",
        "",
        "| Method | Valid / proposals | Mean selection feasibility | Mean conditional proxy regret |",
        "|---|---:|---:|---:|",
    ]
    for method in sorted({r["method"] for r in records}):
        rs = [r for r in records if r["method"] == method]
        runs = [s for r in rs for s in r["runs"]]
        prob = (
            float(np.mean([s["selection_feasible_probability"] for s in runs]))
            if runs
            else None
        )
        gap = [
            s["expected_proxy_regret"]
            for s in runs
            if s["expected_proxy_regret"] is not None
        ]
        lines.append(
            f"| {method} | {sum(r['verification']['valid'] for r in rs)}/{len(rs)} | {prob} | {float(np.mean(gap)) if gap else None} |"
        )
    lines += [
        "",
        "## Hypothesis assessment",
        "",
        "- Financial usefulness: **inconclusive**; market-data audit has not passed.",
        "- LLM contribution: **inconclusive**; three structural smoke cases do not qualify a model.",
        "- Quantum advantage: **unsupported** by ideal CPU simulation.",
        "",
        "All invalid proposals remain in the denominator. Seeds are not independent financial cases.",
        "Proxy and allocation objectives are separate. See references.json for proxy distortion and full SCIP reference.",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    (path / "PROGRESS.md").write_text(
        "# Experiment progress\n\nCompleted: frozen protocol, compiler verification, classical designs, numerical evaluation and artifact export.\n\nNext gate: complete US-data lineage audit; expand preregistered independent cases before qualification.\n"
    )


def postprocess_samples(spec, indices, budget=32):
    candidates = []
    for index in set(map(int, indices)):
        bits = (index >> np.arange(spec.n)) & 1
        if spec.feasible(bits):
            candidates.append((spec.score(bits), index, bits))
    candidates.sort(key=lambda row: (row[0], row[1]))
    allocations = []
    for _, index, bits in candidates[:budget]:
        allocation = allocate(spec, bits)
        allocations.append(allocation)
    feasible = [a for a in allocations if a["feasible"]]
    chosen = (
        min(feasible, key=lambda a: a["objective"])
        if feasible
        else {"status": "unknown", "feasible": False}
    )
    return {
        **chosen,
        "allocation_queries": len(allocations),
        "sampled_unique_supports": len(candidates),
        "allocation_failures": len(allocations) - len(feasible),
        "fallback_used": False,
    }
