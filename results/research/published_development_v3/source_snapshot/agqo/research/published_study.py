"""Opened development comparison on the pinned, selection-conditioned US corpus."""

from pathlib import Path
from time import perf_counter
import csv
import json
import math
import numpy as np
from .data import write_json
from .published import load, family_indices, assess
from .finance import FinancialSpec, joint_reference, Account
from .design import baseline, lower, request
from .quantum import compile_cost, verify, evaluate, export
from .runner import postprocess_samples
from .workflow import swap_allocate
from agqo.synthesis.profile import data_profile, digest


def conditional_path(spec, weights, returns, benchmark):
    """One decision at training close; trade at next session close, then drift.

    These are publisher-return diagnostics, not audited tradeable prices. The
    existing account earns the first test return before execution and pays fees.
    """
    account = Account(
        100000 * spec.previous_weights.copy(),
        100000 * (1 - spec.previous_weights.sum()),
    )
    daily = []
    order = None
    for t, row in enumerate(returns):
        before = account.nav
        account.advance_total_return(row)
        if t == 0:
            order = account.rebalance(weights, spec.cost_rate)
        daily.append(account.nav / before - 1)
    return {
        "scope": "conditional_publisher_return_buy_and_hold_diagnostic",
        "execution_lag_sessions": 1,
        "rebalance_count": 1,
        "daily_tracking_rmse": float(
            np.sqrt(np.mean((np.array(daily) - benchmark) ** 2))
        ),
        "net_return": account.nav / 100000 - 1,
        "benchmark_return": float(np.prod(1 + benchmark) - 1),
        "fees_paid_dollars": order["fee_dollars"],
        "final_weights": account.weights().tolist(),
        "investment_universe_approved": False,
    }


def source_relaxation(x, b, previous, maximum_weight=0.6):
    """Numerical lower reference after dropping cardinality/minimum positions."""
    import cvxpy as cp

    start = perf_counter()
    w = cp.Variable(x.shape[1])
    objective = cp.sum_squares(x @ w - b) / len(b) + 0.01 * 0.0005 * cp.norm1(
        w - previous
    )
    problem = cp.Problem(
        cp.Minimize(objective * 1e6), [w >= 0, w <= maximum_weight, cp.sum(w) == 1]
    )
    try:
        problem.solve(solver="CLARABEL", max_iter=300, time_limit=30)
        status = str(problem.status)
        value = float(objective.value) if status == "optimal" else None
    except Exception as exc:
        status, value = "failed", None
        return {
            "status": status,
            "error": str(exc),
            "objective": value,
            "elapsed_seconds": perf_counter() - start,
        }
    return {
        "status": status,
        "objective": value,
        "assets": x.shape[1],
        "elapsed_seconds": perf_counter() - start,
        "scope": "Numerical convex relaxation reference, not a certified integer optimum or measured universe-restriction loss.",
    }


def run(directory, data_directory="data/published_us"):
    path = Path(directory)
    if (path / "protocol.json").exists():
        raise ValueError(
            "Use a new output directory; this development protocol is immutable."
        )
    x, b, dates, labels, manifest = load(data_directory)
    assessment = assess(data_directory)
    protocol = {
        "version": "conditional-published-development-v3",
        "previous_run": "published_development_v1 retains the excluded-seed search failure. V2 fixes the classical seed and distinguishes support search status from continuous allocation optimality.",
        "scope": assessment["allowed_claim"],
        "investment_universe_approved": False,
        "training_observations": 126,
        "test_observations": 126,
        "cutoff": str(dates[125].date()),
        "seed": 11,
        "cases": [[10, 3, "base"], [10, 3, "exclude_incumbent"], [30, 6, "base"]],
        "methods": [
            "fixed",
            "rules",
            "random",
            "uniform",
            "allocation_swap",
            "joint_scip",
        ],
        "evaluations": 4,
        "shots_per_evaluation": 64,
        "final_shots": 64,
        "common_allocation_queries": 32,
        "scip_time_limit_seconds": 15,
        "simulator_cap_states": 2000000,
        "family_rule": "SHA256(AGQO-published-family-v1:+source_label), take N, restore source order",
        "no_llm_stock_filtering": True,
        "new_inference_calls": 0,
        "scenario_buckets": "Synthetic policy categories, not historical sectors.",
        "acceptance": "Source/date/hash checks, small-state equivalence, complete costs/exports; no superiority claim from this development study.",
        "reference_protocol": "docs/research/COMPLETION_PROTOCOL.md",
        "code_hashes": {
            name: digest(Path(__file__).with_name(name).read_text())
            for name in (
                "published_study.py",
                "published.py",
                "symmetry.py",
                "quantum.py",
                "design.py",
                "finance.py",
                "workflow.py",
                "runner.py",
            )
        },
    }
    from .sources import capture_sources

    protocol["source_snapshot_manifest_hash"] = digest(capture_sources(path))
    write_json(path / "protocol.json", protocol)
    write_json(path / "dataset_manifest.json", {**manifest, "assessment": assessment})
    (path / "circuits").mkdir(exist_ok=True)
    records = []
    start = perf_counter()
    references = {}
    for n, k, scenario in protocol["cases"]:
        case = f"n{n}_k{k}_{scenario}"
        indices = family_indices(labels, n)
        previous = np.r_[np.ones(k) / k, np.zeros(n - k)]
        spec = FinancialSpec(
            tuple(labels[i] for i in indices),
            tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(n)),
            x[:126, indices],
            b[:126],
            previous,
            k,
            protocol["cutoff"],
            exclude=(labels[indices[0]],) if scenario == "exclude_incumbent" else (),
            sector_weight_caps={"policy_A": 0.7},
            maximum_weight=0.6,
            provenance="published_selection_conditioned_us_2010",
        )
        full_previous = np.zeros(x.shape[1])
        full_previous[indices] = previous
        references[case] = source_relaxation(x[:126], b[:126], full_previous)
        h = compile_cost(spec, constrained_subspace=True)
        write_json(path / case / "data_profile.json", data_profile(spec))
        write_json(path / case / "hamiltonian.json", h)
        write_json(path / case / "designer_request.json", request(spec, h))
        write_json(
            path / case / "family.json",
            {
                "source_indices": indices,
                "source_labels": list(spec.tickers),
                "problem_hash": spec.fingerprint(),
                "all_cardinality_supports": math.comb(n - len(spec.exclude), k),
            },
        )
        print(
            f"Running {case}: all {math.comb(n - len(spec.exclude), k):,} cardinality supports retained.",
            flush=True,
        )
        for mode in protocol["methods"]:
            row = {"case": case, "method": mode, "feasible": False, "status": "failed"}
            method_start = perf_counter()
            try:
                if mode in ("fixed", "rules", "random"):
                    program = baseline(spec, mode, seed=11)
                    ir = lower(program, spec, h)
                    verification = verify(ir, spec, h)
                    row["verification"] = verification
                    write_json(
                        path / "circuits" / f"{case}_{mode}" / "program.json", program
                    )
                    if not verification["valid"]:
                        raise ValueError("Circuit failed independent verification.")
                    row["selection"] = evaluate(
                        ir, spec, h, seed=11, evaluations=4, shots=64
                    )
                    export(
                        ir,
                        h,
                        row["selection"]["angles"],
                        verification,
                        path / "circuits" / f"{case}_{mode}",
                    )
                    row["allocation"] = postprocess_samples(
                        spec, row["selection"]["sampled_support_indices"], 32
                    )
                elif mode == "uniform":
                    rng = np.random.default_rng(11)
                    free = [
                        i
                        for i, name in enumerate(spec.tickers)
                        if name not in spec.exclude
                    ]
                    samples = [
                        sum(
                            1 << int(i) for i in rng.choice(free, size=k, replace=False)
                        )
                        for _ in range(64)
                    ]
                    row["selection"] = {
                        "support_draws": 64,
                        "extra_optimizer_samples": 0,
                        "scope": "Same final sample pool; QAOA additionally uses 256 optimizer shots and exact classical diagnostics.",
                    }
                    row["allocation"] = postprocess_samples(spec, samples, 32)
                elif mode == "allocation_swap":
                    row["allocation"] = swap_allocate(spec, 32)
                else:
                    row["reference"] = joint_reference(spec, time_limit=15)
                    row["allocation"] = row["reference"].get(
                        "allocation", {"feasible": False, "status": "unknown"}
                    )
                allocation = row["allocation"]
                status = "feasible" if allocation["feasible"] else allocation["status"]
                if mode == "joint_scip" and row["reference"]["status"] == "optimal":
                    status = "optimal"
                row.update(
                    status=status,
                    allocation_status=allocation["status"],
                    feasible=allocation["feasible"],
                )
                if allocation["feasible"]:
                    row["conditional_path"] = conditional_path(
                        spec, allocation["weights"], x[126:, indices], b[126:]
                    )
            except Exception as exc:
                row.update(status="failed", feasible=False, error=str(exc))
            row["elapsed_seconds"] = perf_counter() - method_start
            records.append(row)
            # Durable checkpoint after every method, including failures.
            (path / "decisions.jsonl").write_text(
                "".join(json.dumps(r, allow_nan=False) + "\n" for r in records)
            )
            print(
                f"  {mode}: {row['status']} ({row['elapsed_seconds']:.2f}s)", flush=True
            )
    write_json(path / "source_universe_relaxations.json", references)
    columns = [
        "case",
        "method",
        "status",
        "feasible",
        "allocated_objective",
        "tracking_rmse",
        "test_tracking_rmse",
        "selection_feasible_probability",
        "simulation_states",
        "probability_supports",
        "cx",
        "depth",
        "allocation_queries",
        "elapsed_seconds",
    ]
    with (path / "metrics.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in records:
            a = row.get("allocation", {})
            s = row.get("selection", {})
            v = row.get("verification", {}).get("resources", {})
            writer.writerow(
                {
                    "case": row["case"],
                    "method": row["method"],
                    "status": row["status"],
                    "feasible": row["feasible"],
                    "allocated_objective": a.get("objective"),
                    "tracking_rmse": a.get("tracking_rmse"),
                    "test_tracking_rmse": row.get("conditional_path", {}).get(
                        "daily_tracking_rmse"
                    ),
                    "selection_feasible_probability": s.get(
                        "selection_feasible_probability"
                    ),
                    "simulation_states": s.get("simulation_states"),
                    "probability_supports": s.get("nonnegligible_probability_supports"),
                    "cx": v.get("transpiled_cx"),
                    "depth": v.get("transpiled_depth"),
                    "allocation_queries": a.get("allocation_queries"),
                    "elapsed_seconds": row["elapsed_seconds"],
                }
            )
    cost = {
        "new_inference_calls": 0,
        "gpu_seconds": 0,
        "execution": "classical CPU ideal simulation",
        "elapsed_seconds": perf_counter() - start,
        "rows": [
            {
                "case": r["case"],
                "method": r["method"],
                "elapsed_seconds": r["elapsed_seconds"],
                "optimization_shots": r.get("selection", {}).get("total_shots", 0),
                "diagnostic_supports_scored": r.get("selection", {}).get(
                    "diagnostic_supports_scored", 0
                ),
                "verification_seconds": r.get("verification", {}).get(
                    "elapsed_seconds", 0
                ),
            }
            for r in records
        ],
        "accounting_note": "Classical full-support energy scoring, activity tests and allocation queries are diagnostics; not hardware access or a quantum runtime comparison.",
    }
    write_json(path / "cost_report.json", cost)
    lines = [
        "# Conditional published-US development results",
        "",
        protocol["scope"],
        "",
        "**This corpus does not pass the separate historical DJIA investment-data gate.**",
        "",
        "| Case | Method | Status | Allocated objective | Test daily tracking RMSE | Seconds |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in records:
        objective = r.get("allocation", {}).get("objective")
        test = r.get("conditional_path", {}).get("daily_tracking_rmse")
        lines.append(
            f"| {r['case']} | {r['method']} | {r['status']} | {objective if objective is not None else '—'} | {test if test is not None else '—'} | {r['elapsed_seconds']:.2f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "All 30 source-labelled assets participate in the larger family. Every 6-of-30 support is represented by the simulator; shallow circuits need not assign meaningful probability to all of them. See probability_supports in metrics.csv.",
        "Families are hash-ordered resource-limited subsets of 386 source assets. The LLM does not pick these assets. The continuous 386-asset relaxation is a lower reference, not a measured restriction penalty or equal-budget algorithm.",
        "Training and test rows remain chronological. The single trade occurs after the first test session, charges assumed costs, and then drifts without daily resets. Membership conditioning and uncertified publisher return semantics remain limitations.",
        "Four objective evaluations and one seed only test execution and accounting. They do not tune circuits adequately or establish comparative superiority. Every failure remains in the denominator.",
        "H1 (real-world financial value): inconclusive. H2 (LLM value): inconclusive; no LLM is run. H3 (adaptive QAOA value): inconclusive. Ideal classical simulation does not establish quantum advantage.",
    ]
    (path / "RESULTS.md").write_text("\n\n".join(lines) + "\n")
    failures = sum(not r["feasible"] for r in records)
    (path / "PROGRESS.md").write_text(
        f"# Progress\n\nCompleted {len(records)} method/case rows; {failures} without a feasible result.\n\nInvestment-data admission and model qualification remain open. No new Modal calls.\n"
    )
    return {
        "status": "completed",
        "rows": len(records),
        "failures": failures,
        "investment_universe_approved": False,
        "protocol_hash": digest(protocol),
        "output": str(path),
    }
