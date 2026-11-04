"""Bounded, resumable development pilot; no model calls or market qualification."""

from pathlib import Path
import json
import shutil
from time import perf_counter
from collections import Counter

from .budget_search import search, disjoint_schedule
from .cloud_pipeline import common_program
from .data import write_json, sha
from .design import lower
from .improvement import prepare_inputs, decode
from .quantum import compile_cost, verify
from .sources import capture_sources
from agqo.synthesis.profile import digest

METHODS = ["mean_f", "lower_tail_f", "uniform_conditioned", "allocation_swap"]


def source_identity(root):
    files = sorted((root / "agqo").rglob("*.py")) + [
        root / "scripts/run_tail_pilot.py",
        root / "docs/research/TAIL_FITTING_PROTOCOL.md",
        root / "requirements-lock.txt",
        root / "tests/test_sample_loss.py",
    ]
    return {str(p.relative_to(root)): sha(p) for p in files}


def run(directory="results/research/tail_fitting_v1"):
    root = Path(__file__).resolve().parents[2]
    path = Path(directory)
    if (path / "completion.json").exists():
        return {
            **json.loads((path / "completion.json").read_text()),
            "replay_guard": "retained_no_rerun",
        }
    inputs = prepare_inputs()
    prior_protocol = json.loads(
        (root / "results/research/improvement_v1/protocol.json").read_text()
    )
    if prior_protocol["inputs_hash"] != inputs["inputs_hash"]:
        raise ValueError(
            "Saved incumbent targets belong to different financial inputs."
        )
    previous = json.loads(
        (root / "results/research/improvement_v1/references.json").read_text()
    )
    protocol = {
        "version": "feasibility-gated-tail-pilot-v1",
        "inputs_hash": inputs["inputs_hash"],
        "source_manifest": inputs["source_manifest"],
        "source_cutoff": inputs["source_cutoff"],
        "source_identity": source_identity(root),
        "cases": [
            {
                "id": c["id"],
                "family": c["family"],
                "n": len(c["spec"]["tickers"]),
                "hash": c["hash"],
                "target": previous[c["id"]]["allocation"]["objective"] * 1.05,
            }
            for c in inputs["cases"]
        ],
        "seeds": [11, 23, 47],
        "methods": METHODS,
        "evaluations": 8,
        "shots": 64,
        "final_shots": 64,
        "observations_per_run": 576,
        "alpha": 0.25,
        "minimum_feasible_fraction": 0.95,
        "cumulative_run_seconds_ceiling": 1800,
        "expected_runs": 96,
        "target_definition": "1.05*saved feasible5s SCIP incumbent, not optimum or economic margin",
        "investment_universe_approved": False,
        "llm_calls": 0,
        "modal_calls": 0,
        "runtime": "local sequential CPU simulation and classical allocation",
        "raw_return_matrices_published": False,
    }
    if (path / "protocol.json").exists():
        if json.loads((path / "protocol.json").read_text()) != protocol:
            raise ValueError(
                "Prepared protocol, source or data identity changed; no silent resume."
            )
    else:
        if path.exists() and any(path.iterdir()):
            raise ValueError("Unrecognized partial directory; refusing overwrite.")
        write_json(path / "protocol.json", protocol)
        snapshot = capture_sources(path)
        for name in ("scripts/run_tail_pilot.py", "tests/test_sample_loss.py"):
            target = path / "source_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
            snapshot["files"][name] = sha(target)
        write_json(path / "source_snapshot/manifest.json", snapshot)
        write_json(
            path / "dataset_manifest.json",
            {
                "inputs_hash": inputs["inputs_hash"],
                "source": inputs["source_manifest"],
                "cutoff": inputs["source_cutoff"],
                "scope": "Opened conditional US algorithm development only",
                "cases": [
                    {k: c[k] for k in ("id", "hash", "source_columns", "family")}
                    for c in inputs["cases"]
                ],
            },
        )
    records = list((path / "runs").glob("*.json")) if (path / "runs").exists() else []
    spent = sum(json.loads(f.read_text())["elapsed_seconds"] for f in records)
    stopped = False
    for case in inputs["cases"]:
        spec = decode(case["spec"])
        if spec.objective_kind != "tracking_cost" or spec.fingerprint() != case["hash"]:
            raise ValueError("Frozen financial identity/scope mismatch.")
        setup_start = perf_counter()
        h = compile_cost(spec, True)
        ir = lower(
            disjoint_schedule(common_program(spec), spec),
            spec,
            h,
            common_preparation=True,
        )
        setup_file = path / "setup" / f"{case['id']}.json"
        if setup_file.exists():
            setup = json.loads(setup_file.read_text())
            if setup["hamiltonian_hash"] != h["hamiltonian_hash"] or setup[
                "ir_hash"
            ] != digest(ir):
                raise ValueError("Immutable circuit identity changed.")
        else:
            verification = verify(ir, spec, h)
            setup = {
                "hamiltonian_hash": h["hamiltonian_hash"],
                "ir_hash": digest(ir),
                "seconds": perf_counter() - setup_start,
                "verification": verification,
            }
            if not verification["valid"]:
                raise ValueError("Common circuit failed independent verification.")
            write_json(setup_file, setup)
            write_json(path / "circuits" / case["id"] / "gate_ir.json", ir)
            write_json(path / "circuits" / case["id"] / "hamiltonian.json", h)
            matrix, vector, offset = spec.quadratic()
            write_json(
                path / "cases" / case["id"] / "sufficient_statistics.json",
                {
                    "matrix": matrix.tolist(),
                    "linear": vector.tolist(),
                    "offset": offset,
                    "financial_spec_without_returns": {
                        k: v
                        for k, v in case["spec"].items()
                        if k not in ("returns", "benchmark")
                    },
                    "source_spec_hash": case["hash"],
                },
            )
        for method in METHODS:
            for seed in protocol["seeds"]:
                output = path / "runs" / f"{case['id']}__{method}__{seed}.json"
                if output.exists():
                    continue
                attempt = path / "attempts" / output.name
                if attempt.exists():
                    raise ValueError(
                        "Unresolved interrupted attempt retained; review before any redispatch."
                    )
                if spent >= protocol["cumulative_run_seconds_ceiling"]:
                    stopped = True
                    break
                begin = perf_counter()
                record = {
                    "case_id": case["id"],
                    "method": method,
                    "seed": seed,
                    "problem_hash": spec.fingerprint(),
                    "hamiltonian_hash": h["hamiltonian_hash"],
                }
                write_json(attempt, {**record, "status": "running_no_automatic_retry"})
                interrupted = False
                try:
                    result = search(
                        spec,
                        ir,
                        h,
                        seed=seed,
                        evaluations=8,
                        shots=64,
                        final_shots=64,
                        method="uniform"
                        if method == "uniform_conditioned"
                        else "swap"
                        if method == "allocation_swap"
                        else "circuit",
                        fitting="mean"
                        if method == "mean_f"
                        else "lower_tail"
                        if method == "lower_tail_f"
                        else None,
                        tail_alpha=0.25,
                        min_feasible_fraction=0.95,
                    )
                    if result["total_observations"] != 576:
                        raise ValueError("Observation budget mismatch.")
                    record.update(status="completed", result=result)
                except KeyboardInterrupt:
                    interrupted = True
                    record.update(
                        status="interrupted",
                        reason="Execution interrupted; no automatic retry.",
                    )
                    record["allocation_accounting"] = (
                        "Unknown partial run; completed-run totals exclude these unknown attempts."
                    )
                except Exception as exc:
                    record.update(status="error", reason=f"{type(exc).__name__}: {exc}")
                    record["allocation_accounting"] = (
                        "Unknown on unhandled error; completed-run totals exclude these unknown attempts."
                    )
                record["elapsed_seconds"] = perf_counter() - begin
                spent += record["elapsed_seconds"]
                write_json(output, record)
                write_json(
                    attempt, {"status": record["status"], "result_file": str(output)}
                )
                print(
                    case["id"],
                    method,
                    seed,
                    record["status"],
                    f"{spent:.1f}s cumulative",
                    flush=True,
                )
                # Save progress after every completed/error run, before any next evaluation.
                _index(path, protocol, spent, stopped)
                if interrupted:
                    raise KeyboardInterrupt
            if stopped:
                break
        if stopped:
            break
    index = _index(path, protocol, spent, stopped)
    write_json(
        path / "cost_report.json",
        {
            "llm_calls": 0,
            "modal_calls": 0,
            "new_paid_reservation_usd": 0,
            "cumulative_run_seconds": spent,
            "completed_run_allocation_calls": index["allocation_calls"],
            "setup_seconds": sum(
                json.loads(f.read_text())["seconds"]
                for f in (path / "setup").glob("*.json")
            ),
            "scope": "Local CPU diagnostics, not hardware execution or an invoice",
            "equal_observations_not_equal_total_cost": True,
        },
    )
    all_files = {
        str(f.relative_to(path)): sha(f) for f in sorted(path.rglob("*")) if f.is_file()
    }
    summary = {
        **index,
        "status": "budget_stopped"
        if stopped
        else "completed_with_errors"
        if index["errors"]
        else "completed_development_pilot",
        "raw_sha256_files": all_files,
        "llm_calls": 0,
        "modal_calls": 0,
    }
    write_json(path / "completion.json", summary)
    return summary


def _index(path, protocol, spent, stopped):
    files = sorted((path / "runs").glob("*.json"))
    records = [json.loads(f.read_text()) for f in files]
    complete = [r for r in records if r["status"] == "completed"]
    result = {
        "expected_runs": protocol["expected_runs"],
        "completed_runs": len(complete),
        "errors": sum(r["status"] != "completed" for r in records),
        "unrun": protocol["expected_runs"] - len(records),
        "budget_stopped": stopped,
        "cumulative_run_seconds": spent,
        "observations": sum(r["result"]["total_observations"] for r in complete),
        "allocation_calls": sum(r["result"]["allocation_queries"] for r in complete),
        "statuses": dict(Counter(r["status"] for r in records)),
    }
    write_json(path / "run_index.json", result)
    (path / "PROGRESS.md").write_text(
        f"# Progress\n\nCompleted {result['completed_runs']}/{result['expected_runs']} runs; "
        f"errors {result['errors']}, unrun {result['unrun']}. Cumulative run time {spent:.1f}s. "
        "Opened development pilot only; no market or LLM qualification.\n"
    )
    return result
