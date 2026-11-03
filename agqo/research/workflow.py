"""End-to-end decisions and continuous evaluations with explicit admission gates."""

from __future__ import annotations
from pathlib import Path
from itertools import combinations
from time import perf_counter
import csv, json
from jsonschema.exceptions import ValidationError
import numpy as np
from .finance import allocate, joint_reference, diagnose
from .data import write_json, audit, load_market
from .design import baseline, lower
from .quantum import compile_cost, verify, evaluate, export
from .walkforward import walk_forward

ARTIFACTS = (
    "protocol.json",
    "dataset_manifest.json",
    "decisions.jsonl",
    "circuits",
    "metrics.csv",
    "cost_report.json",
    "RESULTS.md",
    "PROGRESS.md",
)


def swap_allocate(spec, budget=32):
    """Allocation-aware local search. All attempted supports consume the budget."""
    start = perf_counter()
    count = 0
    best = None
    seen = set()
    seed = np.zeros(spec.n, int)
    seed[np.argsort(-spec.previous_weights, kind="stable")[: spec.k]] = 1

    def score(x):
        nonlocal count, best
        key = tuple(x)
        if key in seen or count >= budget:
            return
        seen.add(key)
        count += 1
        if not spec.feasible(x):
            return
        result = allocate(spec, x)
        if result["feasible"] and (
            best is None or result["objective"] < best["objective"]
        ):
            best = result

    score(seed)
    if best is None:
        for chosen in combinations(range(spec.n), spec.k):
            x = np.zeros(spec.n, int)
            x[list(chosen)] = 1
            score(x)
            if best is not None or count >= budget:
                break
    while best is not None and count < budget:
        before = best["support"]
        x = np.array(before)
        for i in np.flatnonzero(x):
            for j in np.flatnonzero(x == 0):
                y = x.copy()
                y[i] = 0
                y[j] = 1
                score(y)
                if count >= budget:
                    break
            if count >= budget:
                break
        if best["support"] == before:
            break
    return {
        **(best or {"status": "unknown", "feasible": False}),
        "method": "allocation_swap",
        "support_evaluations": count,
        "elapsed_seconds": perf_counter() - start,
        "fallback_used": False,
    }


def solve_decision(
    spec,
    method="joint_scip",
    *,
    evaluations=24,
    shots=128,
    seed=11,
    circuit_directory=None,
    program=None,
):
    diagnosis = diagnose(spec)
    if diagnosis["status"] == "infeasible":
        return {
            "status": "infeasible",
            "feasible": False,
            "diagnosis": diagnosis,
            "method": method,
        }
    if method == "joint_scip":
        reference = joint_reference(spec)
        return {
            **reference.get("allocation", {}),
            **{k: v for k, v in reference.items() if k != "allocation"},
            "reference_allocation_status": reference.get("allocation", {}).get(
                "status"
            ),
        }
    if method == "allocation_swap":
        return swap_allocate(spec)
    if method == "hold":
        w = spec.previous_weights
        violations = spec.violations_weights(w)
        return {
            "method": "hold",
            "status": "feasible" if not violations else "violates_mandate",
            "feasible": not violations,
            "action": "hold",
            "weights": w.tolist(),
            "violations": violations,
            **spec.metrics_weights(w),
            "fallback_used": False,
        }
    if method not in ("qaoa_fixed", "qaoa_rules", "qaoa_reuse"):
        raise ValueError("Unsupported decision method.")
    h = compile_cost(spec, constrained_subspace=True)
    design = (
        program
        if method == "qaoa_reuse"
        else baseline(spec, "rules" if method == "qaoa_rules" else "fixed")
    )
    if design is None:
        return {
            "status": "unknown",
            "feasible": False,
            "reason": "A saved design is required for reuse.",
            "method": method,
        }
    try:
        ir = lower(design, spec, h)
        verification = verify(ir, spec, h)
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        return {
            "status": "unknown",
            "feasible": False,
            "reason": str(exc),
            "method": method,
        }
    if not verification["valid"]:
        return {
            "status": "unsupported",
            "feasible": False,
            "verification": verification,
            "method": method,
        }
    result = evaluate(ir, spec, h, seed, evaluations, shots)
    if circuit_directory:
        export(ir, h, result["angles"], verification, circuit_directory)
    allocation = (
        allocate(spec, result["bits"])
        if result["bits"] is not None
        else {"status": "unknown", "feasible": False}
    )
    return {
        **allocation,
        "method": method,
        "selection": result,
        "verification": verification,
        "design": design,
        "fallback_used": False,
    }


def artifact_bundle(
    directory, protocol, manifest, decisions, metrics, *, status, cost=None, reason=None
):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    (path / "circuits").mkdir(exist_ok=True)
    target = path / "protocol.json"
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError("Output protocol differs; choose another directory.")
    write_json(target, protocol)
    write_json(path / "dataset_manifest.json", manifest)
    (path / "decisions.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in decisions)
    )
    fields = sorted({k for row in metrics for k in row}) or ["method", "status"]
    with (path / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(metrics)
    write_json(
        path / "cost_report.json",
        cost
        or {
            "inference_usd": 0,
            "inference_calls": 0,
            "reservation_is_not_invoice": True,
        },
    )
    lines = [
        "# AGQO evaluation results",
        "",
        f"Status: **{status}**.",
        "",
        reason or "",
        "",
        "## Hypotheses",
        "",
        "- Financial contribution: **inconclusive** until admitted market evidence and paired comparisons are available.",
        "- LLM contribution: **inconclusive** unless the frozen design comparison establishes it.",
        "- Quantum advantage: **unsupported** by CPU simulation.",
        "",
        "## Measurements",
        "",
        "| Method | Status | Net return | Tracking RMSE | Turnover |",
        "|---|---|---:|---:|---:|",
    ]
    for row in metrics:
        lines.append(
            f"| {row.get('method')} | {row.get('status')} | {row.get('net_return')} | {row.get('tracking_rmse')} | {row.get('one_way_turnover')} |"
        )
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    (path / "PROGRESS.md").write_text(
        f"# Evaluation progress\n\nStatus: {status}.\n\n{reason or 'All requested software branches executed.'}\n\nSee docs/research/WORKLOG.md for the evidence and next dependency.\n"
    )
    return {
        "status": status,
        "output": str(path),
        "artifacts": list(ARTIFACTS),
        "reason": reason,
    }


def run_trajectory(
    directory,
    *,
    source="synthetic",
    data_directory="data/us_equities",
    methods=("hold", "joint_scip", "allocation_swap", "qaoa_fixed", "qaoa_rules"),
    periods=4,
    evaluations=16,
    shots=128,
    replay_program=None,
):
    import pandas as pd

    path = Path(directory)
    protocol = {
        "version": "trajectory-v1",
        "source": source,
        "methods": list(methods),
        "periods": periods,
        "lookback": 252,
        "interval": 21,
        "execution_lag_sessions": 1,
        "evaluations": evaluations,
        "shots": shots,
        "k": 3,
        "initial_account": "equal_weight_first_3",
        "mandate_change": "exclude_first_security_from_second_decision_persistently",
        "evidence": "docs/research/IMPLEMENTATION_PROTOCOL.md",
    }
    if periods < 1 or evaluations < 1 or shots < 1:
        raise ValueError("Positive periods, evaluations and shots are required.")
    target = path / "protocol.json"
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError("Frozen trajectory differs; use a new output directory.")
    if source == "market":
        manifest = json.loads(
            (Path(data_directory) / "dataset_manifest.json").read_text()
        )
        admission = audit(manifest, data_directory)
        if not admission["financial_evaluation_allowed"]:
            return artifact_bundle(
                path,
                protocol,
                manifest,
                [],
                [],
                status="blocked",
                reason="Market data audit: " + "; ".join(admission["issues"]),
            )
        frame, manifest = load_market(data_directory)
        frame = frame.loc["2014-01-01":]
        benchmark = frame[manifest["benchmark"]].to_numpy()
        r = frame.drop(columns=[manifest["benchmark"]]).to_numpy()
        tickers = tuple(s["asset_id"] for s in manifest["securities"])
        sectors = tuple(s["sector"] for s in manifest["securities"])
        dates = [d.isoformat() for d in frame.index]
    elif source == "synthetic":
        rng = np.random.default_rng(20261102)
        n = 6
        r = rng.normal(0.0002, 0.01, (252 + 21 * periods + 2, n))
        benchmark = r.mean(axis=1)
        dates = [d.isoformat() for d in pd.bdate_range("2015-01-02", periods=len(r))]
        tickers = tuple(f"ASSET_{i:02}" for i in range(n))
        sectors = ("Sector_A",) * 3 + ("Sector_B",) * 3
        manifest = {
            "version": "synthetic-trajectory-v1",
            "dataset_kind": "synthetic_diagnostic",
            "financial_claims_allowed": False,
            "seed": 20261102,
        }
    else:
        raise ValueError("Unsupported trajectory source.")
    length = min(len(r), 252 + 21 * periods + 1)
    r = r[:length]
    benchmark = benchmark[:length]
    dates = dates[:length]
    decisions = []
    metrics = []
    start = perf_counter()
    for method in methods:
        count = 0

        def selector(spec):
            nonlocal count
            count += 1
            return solve_decision(
                spec,
                method,
                evaluations=evaluations,
                shots=shots,
                circuit_directory=path / "circuits" / method / str(count),
                program=replay_program,
            )

        initial = np.r_[np.ones(3) / 3, np.zeros(len(tickers) - 3)]
        mandates = {dates[273]: {"exclude": (tickers[0],)}} if len(dates) > 273 else {}
        result = walk_forward(
            r,
            benchmark,
            dates,
            tickers,
            sectors,
            selector,
            k=3,
            provenance=source,
            initial_weights=initial,
            mandates=mandates,
        )
        daily = result["daily"]
        returns = np.array([d["net_return"] for d in daily])
        b = np.array([d["benchmark_return"] for d in daily])
        # Include the cash leg in one-way NAV turnover, as in FinancialSpec v3.
        one_way = 0.0
        for d in result["decisions"]:
            if "order" in d:
                trades = np.array(d["order"]["trade_dollars"])
                one_way += (
                    (abs(trades).sum() + abs(trades.sum()))
                    / 2
                    / d["order"]["nav_before"]
                )
        metrics.append(
            {
                "method": method,
                "status": "completed",
                "net_return": result["final_nav"] / result["initial_nav"] - 1,
                "tracking_rmse": float(np.sqrt(np.mean((returns - b) ** 2))),
                "tracking_error_per_period": float(np.std(returns - b, ddof=1)),
                "one_way_turnover": float(one_way),
                "fees_dollars": sum(
                    d.get("order", {}).get("fee_dollars", 0)
                    for d in result["decisions"]
                ),
                "compliant_decisions": sum(
                    d.get("allocation", {}).get("feasible", False)
                    for d in result["decisions"]
                ),
                "orders_executed": sum(
                    d["execution_status"] == "executed" for d in result["decisions"]
                ),
                "held_decisions": sum(
                    d["execution_status"] == "held" for d in result["decisions"]
                ),
                "failed_or_no_order_decisions": sum(
                    d["execution_status"] not in ("executed", "held")
                    for d in result["decisions"]
                ),
                "account_reset_count": result["account_reset_count"],
            }
        )
        for d in result["decisions"]:
            decisions.append({"method": method, **d})
        write_json(path / "trajectories" / f"{method}.json", result)
    return artifact_bundle(
        path,
        protocol,
        manifest,
        decisions,
        metrics,
        status="completed",
        reason="Synthetic integration run; these measurements do not establish investment performance."
        if source == "synthetic"
        else "Audited market evaluation; hypotheses require the prespecified paired analysis.",
        cost={
            "elapsed_seconds": perf_counter() - start,
            "inference_calls": 0,
            "inference_usd": 0,
            "reservation_is_not_invoice": True,
        },
    )
