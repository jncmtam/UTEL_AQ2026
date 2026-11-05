"""Audit downloaded live GPU optimization evidence; never dispatch or rerun search."""

from collections import Counter
from pathlib import Path
import argparse
import json
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from agqo.research.data import sha, write_json
from agqo.synthesis.profile import digest

try:
    from scripts.summarize_tail_pilot import audit_run
except ModuleNotFoundError:
    from summarize_tail_pilot import audit_run

RUN_ID = "live_gpu_optimization_v1"
MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
REVISION = "b2cff646eb4bb1d68355c01b18ae02e7cf42d120"
EVALUATION_METHODS = ("llm_selected", "random_selected", "fixed_path", "fixed_star", "uniform_conditioned", "allocation_swap")
DESIGN_METHODS = tuple(f"{family}_r{i}" for family in ("llm", "random") for i in range(3)) + EVALUATION_METHODS[2:]
CLASSICAL = {"uniform_conditioned", "allocation_swap"}


def load(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_grid(cases):
    return {(case, "design", method, 11) for case in cases for method in DESIGN_METHODS} | {
        (case, "evaluation", method, seed) for case in cases for method in EVALUATION_METHODS for seed in (23, 47)
    }


def failure_stage(record):
    """Keep response/admission rejections distinct from numerical execution errors."""
    if record["status"] == "completed":
        return None
    admission = record.get("admission") or {}
    status, reason = admission.get("status", ""), str(record.get("reason", admission.get("reason", "")))
    if status == "no_eligible_candidate":
        return "selection_no_eligible_architecture"
    if record["status"] == "failed":
        return record["phase"] + "_numerical_evaluation"
    if "resources" in status:
        return "resource_admission"
    if "validation" in status:
        return "quantum_or_program_validation"
    if "Unusable live completion" in reason:
        return "inference_response"
    if "ValidationError" in reason:
        return "response_schema"
    return "evidence_or_program_admission"


def architecture_diagnostic(program, request, previous_program, free):
    """Describe actual choices and presentation bias without attributing causality."""
    choices = program.get("exchanges") if isinstance(program, dict) else None
    previous = previous_program.get("exchanges") if isinstance(previous_program, dict) else None
    keys = [f"p{i}" for i in range(1, len(free))]
    if not isinstance(choices, dict) or not all(isinstance(choices.get(k), dict) and "edge" in choices[k] and "group" in choices[k] for k in keys):
        return {"first_enum_count": None, "first_enum_fraction": None, "edge_count": len(keys),
                "ordered_edges": None, "ordered_edge_hash": None, "group_hash": None,
                "program_choice_hash": None, "identical_to_previous": None,
                "is_star": None, "is_path": None}
    edges = [choices[k]["edge"] for k in keys]
    groups = [choices[k]["group"] for k in keys]
    contracts = request["schema"]["properties"]["exchanges"]["properties"]
    first = sum(choices[k]["edge"] == contracts[k]["properties"]["edge"]["enum"][0] for k in keys)
    degrees = {q: 0 for q in free}
    adjacency = {q: set() for q in free}
    valid = True
    for edge in edges:
        try:
            left, right = map(int, edge.removeprefix("EDGE_").split("_"))
            if left not in degrees or right not in degrees or left == right:
                valid = False
                break
            degrees[left] += 1
            degrees[right] += 1
            adjacency[left].add(right)
            adjacency[right].add(left)
        except (ValueError, AttributeError):
            valid = False
            break
    reached, pending = set(), [free[0]] if free else []
    while pending:
        node = pending.pop()
        if node not in reached:
            reached.add(node)
            pending.extend(adjacency[node] - reached)
    tree = valid and len(edges) == len(free) - 1 and len(reached) == len(free)
    return {"first_enum_count": first, "first_enum_fraction": first / len(keys) if keys else None,
            "edge_count": len(keys), "ordered_edges": edges, "ordered_edge_hash": digest(edges),
            "group_hash": digest(groups), "program_choice_hash": digest({k: choices[k] for k in keys}),
            "identical_to_previous": choices == previous if previous is not None else None,
            "is_star": bool(tree and max(degrees.values(), default=0) == len(free) - 1),
            "is_path": bool(tree and max(degrees.values(), default=0) <= 2)}


def independent_selection_key(row):
    """Recompute the registered ranking without importing the implementation."""
    result = row.get("result", {})
    allocation = result.get("allocation")
    if row.get("status") != "completed" or not allocation or not result.get("fitting_record", {}).get("final_eligible", False):
        return (1, float("inf"), float("inf"))
    return (0, allocation["objective"], row["admission"]["verification"]["resources"]["transpiled_depth"])


def cuda_check(value, label, state_calls=None):
    require(value.get("cuda") is True, f"Missing actual CUDA metadata: {label}")
    require(value.get("execution") == "ideal_cuda_simulation", f"Unexpected execution: {label}")
    require(str(value.get("device", "")).startswith("cuda"), f"Unexpected device: {label}")
    require("A100" in value.get("gpu_name", ""), f"Unexpected GPU: {label}")
    require(value.get("state_dtype") == "complex128", f"Unexpected state dtype: {label}")
    require(value.get("cpu_fallback") is False and value.get("quantum_hardware") is False, f"Incorrect execution attribution: {label}")
    require(value.get("execute_calls", 0) > 0 and value.get("cuda_stream_elapsed_ms", 0) > 0, f"No measured CUDA execution: {label}")
    if state_calls is not None:
        require(value["execute_calls"] == state_calls, f"State-call accounting mismatch: {label}")


def compare(frame, cases):
    """Keep every intended pair, including missing/failed objectives."""
    rows = []
    for case in cases:
        for seed in (23, 47):
            group = frame[(frame.case_id == case) & (frame.phase == "evaluation") & (frame.seed == seed)]
            actual = group[group.method == "llm_selected"].iloc[0]
            for reference in EVALUATION_METHODS[1:]:
                baseline = group[group.method == reference].iloc[0]
                valid = bool(pd.notna(actual.best_objective) and pd.notna(baseline.best_objective) and baseline.best_objective > 0 and actual.status == baseline.status == "completed")
                rows.append({
                    "case_id": case, "seed": seed, "reference": reference,
                    "llm_status": actual.status, "reference_status": baseline.status,
                    "llm_objective": actual.best_objective, "reference_objective": baseline.best_objective,
                    "valid_pair": valid,
                    "difference_pct": 100 * (actual.best_objective / baseline.best_objective - 1) if valid else None,
                    "absolute_difference": actual.best_objective - baseline.best_objective if valid else None,
                    "llm_final_eligible": actual.final_eligible,
                    "reference_final_eligible": baseline.final_eligible,
                })
    return pd.DataFrame(rows)


def qualification(comparisons, expected_pairs):
    """Prespecified >=2% pooled gain and <=5% mean case regression, both controls."""
    rows = []
    for reference, part in comparisons.groupby("reference", sort=False):
        valid = part[part.valid_pair]
        full = len(valid) == len(part) == expected_pairs
        eligible = full and bool(valid.llm_final_eligible.fillna(False).all())
        case_mean = valid.groupby("case_id").difference_pct.mean()
        pooled = float(valid.difference_pct.mean()) if len(valid) else None
        worst = float(case_mean.max()) if len(case_mean) else None
        met = bool(eligible and pooled <= -2 and worst <= 5)
        rows.append({
            "reference": reference, "expected_pairs": len(part), "valid_pairs": len(valid),
            "mean_difference_pct": pooled,
            "median_difference_pct": float(valid.difference_pct.median()) if len(valid) else None,
            "worst_case_mean_difference_pct": worst,
            "case_mean_difference_pct": {str(k): float(v) for k, v in case_mean.items()},
            "wins": int((valid.absolute_difference < -1e-12).sum()),
            "ties": int((valid.absolute_difference.abs() <= 1e-12).sum()),
            "losses": int((valid.absolute_difference > 1e-12).sum()),
            "complete_pairs_and_llm_feasibility": bool(eligible),
            "target_met": met,
        })
    primary = [row for row in rows if row["reference"] in {"random_selected", "fixed_star"}]
    supported = len(primary) == 2 and all(row["target_met"] for row in primary)
    return rows, "supported" if supported else "unsupported"


def plots(path, frame, comparisons, structures, cases):
    # Architecture change is a descriptive diagnostic, never a benefit metric.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for ax, key, title in zip(axes, ("edge_changes", "group_changes"), ("Changed exchange choices", "Changed beta groups")):
        for case in cases:
            values = [s for s in structures if s["case_id"] == case]
            ax.plot([s["round"] for s in values], [s[key] for s in values], marker="o", label=case)
        ax.set(title=title, xlabel="Live proposal round (initial = 0)", ylabel="Changes relative to initial proposal", xticks=[0, 1, 2])
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Actual model architecture changes; changed gates alone do not establish usefulness")
    fig.savefig(path / "architecture-changes.png", dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    labels, means = [], []
    for i, reference in enumerate(EVALUATION_METHODS[1:]):
        part = comparisons[(comparisons.reference == reference) & comparisons.valid_pair]
        labels.append(reference.replace("_", " "))
        means.append(float(part.difference_pct.mean()) if len(part) else np.nan)
        if len(part):
            ax.scatter(np.full(len(part), i) + np.linspace(-.12, .12, len(part)), part.difference_pct, color="#8b9aaa", alpha=.7, s=25)
    ax.scatter(range(len(means)), means, s=100, color="#12645b", marker="D", label="Mean paired difference")
    ax.axhline(0, color="#333333", linewidth=1)
    ax.axhline(-2, color="#326fb0", linestyle="--", label="Registered 2% improvement target")
    ax.set(xticks=range(len(labels)), xticklabels=labels, ylabel="100 × (LLM objective / reference − 1)", title="Frozen circuit selection, seeds 23/47 on opened development data\nNegative favors LLM; dots are related cases/seeds, not confidence intervals")
    ax.tick_params(axis="x", labelrotation=18)
    ax.grid(axis="y", alpha=.2)
    ax.legend(fontsize=8)
    fig.savefig(path / "relative-objective.png", dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    labels, design, evaluation = [], [], []
    for method in EVALUATION_METHODS:
        family = method.removesuffix("_selected")
        selected_design = frame[(frame.phase == "design") & (frame.method.str.startswith(family + "_r") if method.endswith("_selected") else frame.method == method)]
        selected_evaluation = frame[(frame.phase == "evaluation") & (frame.method == method)]
        labels.append(method.replace("_", " "))
        design.append(float(selected_design.observations.fillna(0).sum()))
        evaluation.append(float(selected_evaluation.observations.fillna(0).sum()))
    ax.bar(labels, design, label="All design proposals/draws", color="#4e8f85")
    ax.bar(labels, evaluation, bottom=design, label="Evaluation draws", color="#91b4d4")
    ax.tick_params(axis="x", labelrotation=18)
    ax.set(ylabel="Recorded support observations", title="Cumulative design + evaluation sampling effort across all four cases\nTokens, verification, allocator work and GPU-residency costs are additional")
    ax.legend()
    fig.savefig(path / "complete-sampling-costs.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", choices=(RUN_ID,), default=RUN_ID)
    args = parser.parse_args()
    path = Path("results/research") / args.run_id
    require(not (path / "RESULTS.md").exists(), "Derived report already exists; retain it and use a presentation revision.")
    orchestration, evaluation = path / "orchestration", path / "evaluation"
    require((orchestration / "completed.json").exists(), "Completed downloaded GPU artifacts are required; this script never dispatches work.")
    complete = load(orchestration / "completed.json")
    require(complete == load(evaluation / "completion.json"), "Controller/worker completion differs.")
    manifest = load(orchestration / "download_manifest.json")
    for name, expected in manifest.items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, f"Unsafe manifest path: {name}")
        require(sha(evaluation / relative) == expected, f"Downloaded artifact hash differs: {name}")
    protocol = load(evaluation / "protocol.json")
    prepared = load(orchestration / "prepared.json")
    require(protocol == prepared["protocol"], "Frozen worker/controller protocol differs.")
    for name, expected in protocol["package_source_hashes"].items():
        require(sha(evaluation / "source_snapshot" / name) == expected, f"Worker package snapshot differs: {name}")
    for name, expected in protocol["controller_hashes"].items():
        source = Path(name)
        if source.is_absolute():
            source = source.relative_to(Path.cwd())
        require(sha(orchestration / "source_snapshot" / source) == expected, f"Controller snapshot differs: {name}")
    data = load(evaluation / "dataset_manifest.json")
    cases = list(data["case_hashes"])
    require(len(cases) == 4, "Expected four registered development cases.")
    cuda_selfcheck = load(evaluation / "cuda_selfcheck.json")
    require({c["case_id"] for c in cuda_selfcheck} == set(cases) and len(cuda_selfcheck) == 4, "CUDA selfcheck case coverage differs.")
    for row in cuda_selfcheck:
        cuda_check(row, row["case_id"])
        require(row["maximum_amplitude_residual"] <= 1e-10, "CUDA amplitude selfcheck failed.")

    records = [load(file) for file in sorted((evaluation / "runs").glob("*.json"))]
    lookup = {(r["case_id"], r["phase"], r["method"], r["seed"]): r for r in records}
    require(len(lookup) == len(records) and set(lookup) == expected_grid(cases), "Missing, duplicate or unexpected run; failures must remain explicit.")
    require(len(records) == complete["runs"] == 88, "Run denominator mismatch.")
    require(sum(r["status"] == "completed" for r in records) == complete["completed_runs"], "Completed-run count differs.")
    lock = load(evaluation / "selection_lock.json")
    require(lock["selection_hash"] == digest({k: v for k, v in lock.items() if k != "selection_hash"}), "Winner selection lock hash differs.")
    require(lock["selection_hash"] == complete["selection_hash"] and lock["inputs_hash"] == complete["inputs_hash"] == prepared["inputs_hash"], "Frozen selection/input identity differs.")
    require(lock["selection_seed"] == 11 and lock["evaluation_seeds"] == [23, 47], "Selection/evaluation seeds changed.")
    for case in cases:
        for family in ("llm", "random"):
            candidates = [lookup[(case, "design", f"{family}_r{i}", 11)] for i in range(3)]
            winner = min(candidates, key=independent_selection_key)
            chosen = lock["selected"][case][family + "_selected"]
            eligible = independent_selection_key(winner)[0] == 0
            require(chosen["method"] == (winner["method"] if eligible else None), f"Selected {family} winner differs: {case}")
            require(chosen["design_objective"] == (winner.get("result", {}).get("allocation") or {}).get("objective"), f"Selected objective differs: {case}/{family}")
            if eligible:
                require(chosen["admission"] == winner["admission"], "Selected architecture differs from winner.")
            else:
                require(chosen["admission"] == {"status": "no_eligible_candidate"}, "No-winner status concealed.")
        for method in ("fixed_path", "fixed_star"):
            require(lock["selected"][case][method]["admission"] == lookup[(case, "design", method, 11)]["admission"], "Fixed architecture changed after selection.")
        for method in EVALUATION_METHODS[:4]:
            for seed in (23, 47):
                require(lookup[(case, "evaluation", method, seed)]["admission"] == lock["selected"][case][method]["admission"], "Evaluation architecture differs from selection lock.")

    rows, prefixes, failures = [], [], []
    rescored, residual, cuda_runs = 0, 0., 0
    for record in records:
        case, method, phase = record["case_id"], record["method"], record["phase"]
        expected_observations = 1728 if phase == "design" and method in CLASSICAL else 576
        stats = load(evaluation / "cases" / case / "sufficient_statistics.json")
        common = {k: record[k] for k in ("case_id", "method", "phase", "seed", "status")}
        common.update(n=len(stats["linear"]), declared_observation_budget=expected_observations,
                      admission_status=(record.get("admission") or {}).get("status", "not_applicable"),
                      reason=record.get("reason"), failure_stage=failure_stage(record))
        if record["status"] == "completed":
            points, row, count, error = audit_run(record, stats, None, expected_observations)
            row.update(common)
            if method not in CLASSICAL:
                metadata = record["result"].get("simulation_execution", {})
                cuda_check(metadata, f"{case}/{phase}/{method}/{record['seed']}", record["result"]["state_evaluations"])
                require(metadata["simulation_states"] == record["result"]["simulation_states"], "Simulation state count differs.")
                require(record["admission"]["status"] == "accepted" and record["admission"]["verification"]["valid"], "Completed unverified circuit.")
                row.update(cuda=True, gpu=metadata["gpu_name"], cuda_stream_elapsed_ms=metadata["cuda_stream_elapsed_ms"])
                cuda_runs += 1
            else:
                require("simulation_execution" not in record["result"], "Classical sampler attributed to CUDA circuit.")
                row.update(cuda=False)
            resources = (record.get("admission") or {}).get("verification", {}).get("resources", {})
            row.update(cx=resources.get("transpiled_cx"), depth=resources.get("transpiled_depth"))
            rows.append(row)
            prefixes.extend({**point, "phase": phase} for point in points)
            rescored += count
            residual = max(residual, error)
        else:
            failures.append(common)
            rows.append({**common, "best_objective": None, "observations": None, "final_eligible": False,
                         "allocation_queries": None, "elapsed_seconds": None, "pooled_feasible_fraction": None,
                         "final64_feasible_fraction": None, "cuda": None})
    frame = pd.DataFrame(rows)
    comparisons = compare(frame, cases)
    pair_summary, usefulness = qualification(comparisons, len(cases) * 2)

    model_rows, structures, prompt_index = [], [], []
    response_lines = ["# Exact live model responses", "", "These are actual saved GPU generations, not reconstructed responses. All failed/truncated outputs remain included. Numerical evaluation and rationales are separate evidence.", ""]
    system_lines = ["# Exact live system prompts", "", "The complete logical request (including user payload and response schema) is linked below each entry.", ""]
    runtime_rows = []
    previous_programs = {}
    for round_index in range(3):
        request_file = evaluation / "llm" / f"round_{round_index}_requests.json"
        answer_file = evaluation / "llm" / f"round_{round_index}_answers.json"
        requests, answers = load(request_file), load(answer_file)
        runtime = load(evaluation / "llm" / f"round_{round_index}_runtime.json")
        require(len(requests) == len(answers) == 4, "Live generation denominator differs.")
        require(runtime["execution"] == "live_modal_gpu_not_replay" and "A100" in runtime["gpu"], "No real model GPU evidence.")
        require(runtime["model"] == MODEL and runtime["revision"] == REVISION and runtime["round_index"] == round_index, "Model/revision/round identity differs.")
        require(runtime["model_load_count"] == 1 and runtime["generation_seconds"] > 0, "Resident model/runtime evidence missing.")
        runtime_rows.append(runtime)
        response_lookup = {a["request_hash"]: a for a in answers}
        require(len(response_lookup) == 4 and set(response_lookup) == {r["request_hash"] for r in requests}, "Live answer/request identities differ.")
        for case, request in zip(cases, requests, strict=True):
            require(request["request_hash"] == digest({k: v for k, v in request.items() if k != "request_hash"}), "Saved live request hash differs.")
            answer = response_lookup[request["request_hash"]]
            require(answer["model"] == MODEL and answer["revision"] == REVISION and answer["execution"] == "live_modal_vllm", "Unattributed live answer.")
            require(answer["usage"]["input_tokens"] > 0 and answer["usage"]["output_tokens"] > 0, "Missing actual token accounting.")
            if answer["status"] == "ok":
                require(answer["finish_reason"] == "stop" and json.loads(answer["raw_text"]) == answer["response"], "Raw response differs from parsed program.")
            row = lookup[(case, "design", f"llm_r{round_index}", 11)]
            stats = load(evaluation / "cases" / case / "sufficient_statistics.json")
            require(request["payload"]["exchange_table"]["problem_hash"] == stats["source_spec_hash"], "Prompt is linked to the wrong financial case.")
            if row["admission"]["status"] == "accepted":
                require(row["admission"]["source_response_hash"] == digest(answer["response"]), "Admitted architecture is not the actual model output.")
            require(row["request_hash"] == answer["request_hash"], "Model/run request linkage differs.")
            history = request["payload"]["prior_live_proposals"]
            require(len(history) == round_index, "Feedback omits earlier proposals.")
            for prior_index, previous in enumerate(history):
                require(previous["request_hash"] == lookup[(case, "design", f"llm_r{prior_index}", 11)]["request_hash"], "Feedback references a different proposal.")
            initial = lookup[(case, "design", "llm_r0", 11)]["admission"].get("normalized_program")
            current = row["admission"].get("normalized_program")
            edge_changes = group_changes = None
            if initial and current:
                edge_changes = sum(initial["parents"][k] != current["parents"][k] for k in initial["parents"])
                group_changes = sum(a != b for a, b in zip(initial["groups"], current["groups"], strict=True))
            structures.append({"case_id": case, "round": round_index, "edge_changes": edge_changes, "group_changes": group_changes,
                               "schedule_changed": initial["schedule"] != current["schedule"] if initial and current else None})
            diagnostic = architecture_diagnostic(answer.get("response"), request, previous_programs.get(case), request["payload"]["exchange_table"]["free_qubits"])
            diagnostic.update(case_id=case, round=round_index,
                              selected=lock["selected"][case]["llm_selected"]["method"] == f"llm_r{round_index}")
            previous_programs[case] = answer.get("response")
            model_rows.append({"case_id": case, "round": round_index, "status": answer["status"], "finish_reason": answer["finish_reason"],
                               "admission": row["admission"]["status"], "request_hash": answer["request_hash"], **answer["usage"], **diagnostic})
            relative_request = str(request_file.relative_to(path))
            relative_answer = str(answer_file.relative_to(path))
            prompt_index.append({"case_id": case, "round": round_index, "request_hash": request["request_hash"], "request_file": relative_request, "answer_file": relative_answer})
            response_lines += [f"## {case} — round {round_index}", "", f"Status: `{answer['status']}`; finish: `{answer['finish_reason']}`; admission: `{row['admission']['status']}`.", "", f"Request hash: `{request['request_hash']}`. [Exact request, user payload and schema]({relative_request}); [raw receipt/tokens]({relative_answer}).", "", "````text", answer["raw_text"], "````", ""]
            system_lines += [f"## {case} — round {round_index}", "", f"[Complete request]({relative_request}), hash `{request['request_hash']}`.", "", "````text", request["system"], "````", ""]
    require(len(model_rows) == complete["live_requests"] == 12, "Live request count differs from completion.")
    cost = load(orchestration / "cost_report.json")
    require(cost["reservation_is_not_invoice"] is True, "Reservation incorrectly described as invoice.")
    require(abs(cost["reserved_usd_total"] - sum(j["reserved_usd"] for j in cost["ledger"]["jobs"])) < 1e-8, "Reservation ledger total differs.")
    admitted = sum(r["admission"] == "accepted" for r in model_rows)
    tokens_in = sum(r["input_tokens"] for r in model_rows)
    tokens_out = sum(r["output_tokens"] for r in model_rows)
    enum_count = sum(r["first_enum_count"] or 0 for r in model_rows)
    enum_denominator = sum(r["edge_count"] for r in model_rows if r["first_enum_count"] is not None)
    enum_fraction = enum_count / enum_denominator if enum_denominator else None
    enum_interpretation = (
        "Most chosen edges equal the first presented enum: enum-order bias remains plausible; graph changes do not establish causal financial adaptation."
        if enum_fraction is not None and enum_fraction >= .5 else
        "First-enum choices do not comprise a majority, but enum-order bias is not ruled out; no controlled counterfactual isolates causal data/feedback adaptation."
    )
    stage_counts = dict(Counter(r["failure_stage"] for r in failures))
    analysis = {
        "raw_hashes_verified": len(manifest), "expected_runs": 88, "completed_runs": int((frame.status == "completed").sum()),
        "failed_or_rejected_runs": failures, "live_generations": 12, "normal_completions": sum(r["status"] == "ok" for r in model_rows),
        "admitted_model_proposals": admitted, "cuda_circuit_runs": cuda_runs, "cuda_selfchecks": cuda_selfcheck,
        "observations": int(frame.observations.fillna(0).sum()), "allocation_queries": int(frame.allocation_queries.fillna(0).sum()),
        "feasible_allocations_independently_rescored": rescored, "maximum_objective_residual": residual,
        "model": MODEL, "revision": REVISION, "input_tokens": tokens_in, "output_tokens": tokens_out,
        "generation_seconds": sum(r["generation_seconds"] for r in runtime_rows),
        "model_load_seconds": runtime_rows[0]["model_load_seconds"], "worker_elapsed_seconds": complete["elapsed_seconds"],
        "selection_hash_verified": lock["selection_hash"], "winner_selection_independently_verified": True,
        "comparisons": pair_summary, "registered_usefulness_target": usefulness,
        "architecture_changes": structures, "model_attempts": model_rows, "cost": cost,
        "enum_first_choice_count": enum_count, "enum_choice_denominator": enum_denominator,
        "enum_first_choice_fraction": enum_fraction, "enum_diagnostic_interpretation": enum_interpretation,
        "failure_stage_counts": stage_counts,
        "selected_llm_architecture_diagnostics": [r for r in model_rows if r["selected"]],
        "financial_value": "unqualified", "quantum_advantage": "unqualified", "independent_financial_test": False,
        "scope": "Opened conditional US development data and previously opened stochastic evaluation seeds; no market or independent financial qualification",
    }
    frame.to_csv(path / "metrics.csv", index=False)
    comparisons.to_csv(path / "comparisons.csv", index=False)
    pd.DataFrame(prefixes).to_csv(path / "prefix_metrics.csv", index=False)
    pd.DataFrame(model_rows).to_csv(path / "model_attempts.csv", index=False)
    write_json(path / "analysis.json", analysis)
    write_json(path / "prompt_index.json", prompt_index)
    (path / "ACTUAL_RESPONSES.md").write_text("\n".join(response_lines) + "\n")
    (path / "SYSTEM_PROMPTS.md").write_text("\n".join(system_lines) + "\n")
    plots(path, frame, comparisons, structures, cases)
    lines = [
        "# Live GPU LLM/QAOA optimization results", "",
        f"**Registered usefulness target: {usefulness.upper()}.** One real pinned Coder30 model generated 12 proposals in three resident-GPU rounds, with measured feedback between rounds. {admitted}/12 proposals passed admission. {analysis['completed_runs']}/88 intended numerical runs completed; {len(failures)} failed/rejected runs remain in the denominator.", "",
        "This is a conditional algorithm experiment on opened US development cases, not an independent financial test, investment-return result or physical quantum execution. Evaluation seeds 23/47 were previously opened; a winner lock prevents within-run seed-based architecture selection but does not create a pristine holdout.", "",
        "## What actually ran", "",
        f"Model `{MODEL}`, revision `{REVISION}`, BF16/vLLM0.15, one Modal A10080GB. Real input/output tokens: {tokens_in:,}/{tokens_out:,}. The model remained resident across three inference batches. CUDA complex128 executed state preparation, cost phases and exchange gates; CPU executed compilation, independent verification, optimizer control, sampling RNG and CLARABEL allocation in the same GPU worker. This is a hybrid workflow; allocating a GPU does not make every operation GPU work.", "",
        f"All {len(manifest)} downloaded checksums passed. Independently rescored {rescored:,} feasible cached allocations, maximum residual {residual:.3g}. Verified all four CUDA/NumPy amplitude checks (threshold1e-10), every completed circuit's CUDA metadata, and the winner lock/ranking. {analysis['observations']:,} total observations and {analysis['allocation_queries']:,} allocator queries were retained.", "",
        "[Exact raw outputs](ACTUAL_RESPONSES.md) · [Exact system prompts](SYSTEM_PROMPTS.md) · [Prompt/schema index](prompt_index.json) · [Audit](analysis.json) · [Frozen winner lock](evaluation/selection_lock.json) · [GPU selfchecks](evaluation/cuda_selfcheck.json)", "",
        "## Frozen evaluation comparison", "",
        "Each entry is the mean of paired percentage differences in best allocated **training** objective F; negative favors the LLM. All intended pairs are in comparisons.csv, including failed/unavailable results. Pooled values use available valid pairs but the registered target requires all expected pairs and LLM final empirical feasibility. Related cases/seeds are descriptive observations, not independent replication or significance tests.", "",
        "| Reference | Valid/expected pairs | Mean difference | Worst case mean | Wins/ties/losses |", "|---|---:|---:|---:|---|",
    ]
    for item in pair_summary:
        mean = f"{item['mean_difference_pct']:+.3f}%" if item["mean_difference_pct"] is not None else "unavailable"
        worst = f"{item['worst_case_mean_difference_pct']:+.3f}%" if item["worst_case_mean_difference_pct"] is not None else "unavailable"
        lines.append(f"| {item['reference']} | {item['valid_pairs']}/{item['expected_pairs']} | {mean} | {worst} | {item['wins']}/{item['ties']}/{item['losses']} |")
    lines += ["", "![Relative allocated objective](relative-objective.png)", "",
        "The preregistered target requires at least2% pooled improvement against **both** matched random architecture search and fixed star, with no case-level mean regression over5%. Failure to meet either comparator, missing pairs or unqualified final LLM batches makes that target unsupported. A circuit comparison alone never establishes financial or quantum advantage.", "",
        "## Architecture adaptation and attribution", "",
        f"Across parseable actual responses, {enum_count}/{enum_denominator} chosen edges equal the first presented schema enum ({enum_fraction:.1%}). {enum_interpretation}" if enum_fraction is not None else "No parseable program supplies an enum-choice diagnostic.", "",
        "[Per-proposal choice diagnostics](model_attempts.csv) retain ordered edge lists, edge/group hashes, equality to the previous proposal and selected-program star/path indicators. Hash equality is a structural diagnostic, not proof of financial equivalence.", "",
        "![Actual architecture changes](architecture-changes.png)", "",
        "LLM owns exchange-edge choices and beta sharing. Compiler owns gate scheduling, counter-Dicke preparation and immutable cost synthesis; numerical optimization owns angles. Each revision sees all preceding measured proposals. Edge enums are deterministically permuted; removing the prior first-enum star bias is an interface intervention, not evidence that the model became more intelligent. Different edges and fluent rationales are insufficient without measured usefulness. Explanations are unverified model prose.", "",
        "## Complete costs and unequal fixed-reference design budgets", "",
        "![Complete design and evaluation observations](complete-sampling-costs.png)", "",
        "Per case, LLM and random search each receive three576-observation design runs (1,728 total); conditioned uniform/swap receive1,728 design observations. Fixed path/star receive one576-observation design run each. Every selected/control method then receives two576-observation evaluation runs. The fixed-versus-searched comparison is therefore **not equal in complete design budget**. Duplicate proposals, rejected/failed candidates and every fitting/final sample count; failed execution costs may be unknown rather than zero.", "",
        f"Recorded worker duration {complete['elapsed_seconds']:.2f}s; model generation {analysis['generation_seconds']:.2f}s; one model-load record {analysis['model_load_seconds']:.2f}s. The model stayed resident during finance work, so whole-worker GPU reservation includes that idle/host-work time. Total reservation USD{cost['reserved_usd_total']:.6f}, **not an invoice**. [Cost ledger](orchestration/cost_report.json) and before/after account snapshots remain in orchestration. Image builds, local input preparation and account billing changes do not constitute an isolated job bill.", "",
        "## Limits and scientific decision", "",
        "The source corpus is real US equity data with full-year membership conditioning. Four dependent cases use first126 estimation rows and artificial policy buckets. Historical DJIA/DIA identity/action/sector admission remains closed; no independent financial partition was opened. Empirical95% final-batch feasibility is not a population certificate. B is still the equal-weight Hamiltonian proxy while measured F comes from continuous allocation; feedback does not resolve their mathematical mismatch. Generalization, investment benefit, market deployability and quantum advantage remain unqualified.", "",
        f"The narrow registered usefulness hypothesis is **{usefulness}** on this development experiment. The result does not justify a model-size sweep. Preserve all attempts and use the strong direct finance comparison, formulation mismatch and data-admission gate to determine the next intervention.", "",
        "## Explicit failures", "", f"Failure/rejection stages: {json.dumps(stage_counts, sort_keys=True)}. Admission/schema/resource rejections are distinguished from numerical design/evaluation execution failures and no-eligible-selection outcomes. No failed or rejected run was removed from the expected grid. Details follow (empty means all intended runs completed).", "", "```json", json.dumps(failures, indent=2), "```", "",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    findings = ["# Findings from the live GPU run", "", f"The registered architecture-usefulness target is **{usefulness}**. This is distinct from financial qualification, which remains unestablished.", "", f"Actual live GPU generations:12; admitted:{admitted}; completed intended runs:{analysis['completed_runs']}/88. All raw generations, failed/rejected runs and design-search effort are retained.", ""]
    for item in pair_summary:
        if item["mean_difference_pct"] is not None:
            findings.append(f"- LLM versus {item['reference']}: {item['mean_difference_pct']:+.3f}% mean paired allocated-F difference ({item['valid_pairs']}/{item['expected_pairs']} valid pairs; lower is better).")
        else:
            findings.append(f"- LLM versus {item['reference']}: unavailable; no valid paired financial decisions.")
    findings += ["", enum_interpretation, "", "Feedback and changed architecture are mechanisms tested here, not proofs of reasoning quality. Matched random search is the architecture-value test; allocation-aware swap is the stronger direct finance reference. Star/path comparisons have smaller design budgets. Numerical circuit admission is not a financial win.", "", "Read RESULTS.md for complete budgets, audit evidence and scope; ACTUAL_RESPONSES.md exposes exact model text. No physical quantum computer or independent investment evaluation was used.", ""]
    (path / "FINDINGS.md").write_text("\n".join(findings))
    (path / "PROGRESS.md").write_text(f"# Progress\n\nLive single-model Modal GPU execution and local read-only evidence audit are complete. {admitted}/12 model proposals admitted; {analysis['completed_runs']}/88 runs completed; {len(failures)} failed/rejected. Registered usefulness target: **{usefulness}**. All {len(manifest)} raw hashes checked and {rescored:,} feasible allocations independently rescored.\n\nNo additional inference, rerun or model escalation is scheduled. Open dependencies remain formulation utility, historical data admission and a genuinely independent financial study.\n")
    shutil.copyfile(__file__, path / "report_generator.py")
    products = ["analysis.json", "metrics.csv", "comparisons.csv", "prefix_metrics.csv", "model_attempts.csv", "prompt_index.json", "ACTUAL_RESPONSES.md", "SYSTEM_PROMPTS.md", "RESULTS.md", "FINDINGS.md", "PROGRESS.md", "architecture-changes.png", "relative-objective.png", "complete-sampling-costs.png", "report_generator.py"]
    write_json(path / "report_manifest.json", {"raw_downloads_unchanged": True, "derived_sha256": {name: sha(path / name) for name in products}})
    print(json.dumps({key: analysis[key] for key in ("completed_runs", "live_generations", "admitted_model_proposals", "cuda_circuit_runs", "observations", "allocation_queries", "feasible_allocations_independently_rescored", "registered_usefulness_target", "comparisons")}, indent=2))


if __name__ == "__main__":
    main()
