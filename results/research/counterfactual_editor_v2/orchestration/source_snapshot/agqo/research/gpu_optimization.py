"""Live circuit proposals, measured feedback, and frozen CUDA evaluation.

No model output is synthesized here. ``generate`` must be an actual model callback;
the Modal entry point supplies a resident pinned vLLM engine.
"""

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import random
from time import perf_counter
import numpy as np
from jsonschema import Draft202012Validator

from agqo.synthesis.profile import digest
from agqo.synthesis.typed import domain
from .budget_search import search, disjoint_schedule, admit_cost_aware_program
from .cloud_pipeline import common_program
from .data import write_json
from .edge_program import requests_for, schema, normalize
from .frozen_numerics import bind
from .improvement import decode
from .quantum import export

VERSION = "live-gpu-feedback-optimization-v1"
RUN_ID = "live_gpu_optimization_v1"
ROUNDS = 3
SEEDS = (23, 47)
SYSTEM_ADDITION = """
You are in a bounded live architecture optimization loop, not a prose exercise.
Inspect actual edge-table numbers before choosing connections and beta sharing.
Enum ordering is randomized presentation, NOT a ranking. A first-enum choice,
star, path, large RMS or high correlation is not inherently optimal. You may keep
a previous program if measurement supports reuse. In revision rounds, use the
measured allocated-F/feasibility/resource history to decide which edges/groups to
retain or change. Never claim an unmeasured improvement. Explain concrete chosen
edge IDs and numerical contrasts briefly; do not invent a constraint guarantee.
All 3 proposals and all angle/financial evaluations count against your budget.
The compiler, not you, owns gate scheduling/preparation/exact COST. You never
select stocks or weights. Lower allocated F is better; B is only its proxy.
"""


def permuted_schema(spec, seed):
    """Change only enum presentation; the legal program set is unchanged."""
    value = schema(spec)
    for key, child in value["properties"]["exchanges"]["properties"].items():
        order = child["properties"]["edge"]["enum"]
        order.sort(key=lambda edge: hashlib.sha256(f"{seed}:{key}:{edge}".encode()).hexdigest())
    return value


def make_request(base, spec, case_index, round_index, history):
    if not 0 <= round_index < ROUNDS or len(history) != round_index:
        raise ValueError("Feedback history must contain every preceding proposal.")
    value = deepcopy(base)
    seed = 500 + 100 * round_index + case_index
    value.update(schema=permuted_schema(spec, seed), seed=seed, temperature=0.6)
    value["system"] += SYSTEM_ADDITION
    value["payload"].update(
        prompt_version=VERSION,
        round_index=round_index,
        prior_live_proposals=history,
        enum_order="deterministic hash permutation; no edge ranking",
        architecture_budget={"total_proposals": ROUNDS, "remaining_after_this": ROUNDS-round_index-1},
    )
    value.pop("request_hash", None)
    value["request_hash"] = digest(value)
    return value


def admit_response(answer, request, spec, h, budget):
    """Validate source identities and the actual model response before lowering."""
    try:
        if request["request_hash"] != digest({k: v for k, v in request.items() if k != "request_hash"}):
            raise ValueError("Live request identity changed.")
        if answer["request_hash"] != request["request_hash"]:
            raise ValueError("Model response belongs to another request.")
        if answer.get("status") != "ok":
            raise ValueError(f"Unusable live completion: {answer.get('status')}")
        if request["schema"] != permuted_schema(spec, request["seed"]):
            raise ValueError("Live response domain changed.")
        if request["payload"]["exchange_table"]["problem_hash"] != spec.fingerprint():
            raise ValueError("Financial evidence identity changed.")
        if request["payload"]["hamiltonian"]["hamiltonian_hash"] != h["hamiltonian_hash"]:
            raise ValueError("Immutable COST identity changed.")
        if request["payload"]["compiled_resource_budget"] != budget:
            raise ValueError("Resource budget changed.")
        Draft202012Validator(request["schema"]).validate(answer["response"])
        program = normalize(answer["response"], spec)
        result = admit_cost_aware_program(program, spec, h, budget)
        result.update(normalized_program=program, source_response_hash=digest(answer["response"]))
        return result
    except Exception as exc:
        return {"status": "rejected", "reason": f"{type(exc).__name__}: {exc}", "fallback_used": False}


def random_program(spec, seed):
    rng = random.Random(seed)
    free = domain(spec)["free_qubits"]
    return {
        "version": "data-edge-program-v2", "depth": 1,
        "preparation": "compiler_counter_dicke_v1",
        "exchanges": {f"p{i}": {"edge": f"EDGE_{free[rng.randrange(i)]}_{free[i]}", "group": rng.randrange(2)} for i in range(1, len(free))},
        "explanation": {k: "Random architecture search control; not model output." for k in ("connections", "sharing", "falsifier")},
    }


def selection_key(row):
    """Training-only decision quality; failed/ineligible proposals cannot win."""
    result = row.get("result", {})
    allocation = result.get("allocation")
    eligible = result.get("fitting_record", {}).get("final_eligible", False)
    if row.get("status") != "completed" or not allocation or not eligible:
        return (1, float("inf"), float("inf"))
    resources = row["admission"]["verification"]["resources"]
    return (0, allocation["objective"], resources["transpiled_depth"])


def feedback(row, answer):
    result = row.get("result", {})
    batches = result.get("fitting_record", {}).get("batches", [])
    return {
        "request_hash": answer["request_hash"],
        "actual_previous_program": answer.get("response"),
        "admission_status": row["admission"]["status"],
        "reason": row.get("reason", row["admission"].get("reason")),
        "resources": row["admission"].get("verification", {}).get("resources"),
        "best_allocated_F": (result.get("allocation") or {}).get("objective"),
        "final_normalized_mean_F": batches[-1]["mean_loss"] if batches else None,
        "final_feasible_fraction": batches[-1]["feasible_fraction"] if batches else None,
        "normalization": "F / a common conservative problem bound; lower is better",
        "observation_count": result.get("total_observations", 0),
        "scope": "training-data measurement, not future returns or a quantum gradient",
    }


def run(directory, inputs, generate, basis_factory, checkpoint=lambda: None):
    """Run once in the live GPU worker; preserve partial evidence on failure."""
    path = Path(directory)
    if path.exists() and any(path.iterdir()):
        raise ValueError("Existing GPU run retained; no automatic paid rerun.")
    if inputs["inputs_hash"] != digest({"cases": inputs["cases"], "interface_version": inputs["interface_version"]}):
        raise ValueError("Prepared financial identity changed.")
    path.mkdir(parents=True)
    write_json(path / "protocol.json", inputs["live_protocol"])
    write_json(path / "dataset_manifest.json", inputs["dataset_manifest"])
    start = perf_counter()
    cases, histories, all_rows = {}, {}, []
    # Before loading model weights, crosscheck the actual CUDA executor on each case.
    checks = []
    from .symmetry import ConservedBasis
    for case in inputs["cases"]:
        spec, h, certificate = bind(decode(case["spec"]), case["frozen_numerics"])
        program = disjoint_schedule(common_program(spec), spec)
        admitted = admit_cost_aware_program(program, spec, h, case["resource_budget"])
        if admitted["status"] != "accepted":
            raise ValueError("Common fixed reference fails the frozen resource/quantum contract.")
        ir = admitted["gate_ir"]
        angles = np.linspace(0.13, 0.37, len(ir["parameters"]))
        gpu = basis_factory(spec, h)
        expected = ConservedBasis(spec, h).execute(ir, h, angles)
        actual = gpu.execute(ir, h, angles)
        residual = float(np.max(abs(expected-actual)))
        if residual > 1e-10 or not gpu.execution_metadata()["cuda"]:
            raise ValueError("Actual CUDA/NumPy state evolution selfcheck failed.")
        checks.append({"case_id": case["id"], "maximum_amplitude_residual": residual, **gpu.execution_metadata()})
        matrix, linear, offset = spec.quadratic()
        write_json(path / "cases" / case["id"] / "sufficient_statistics.json", {
            "matrix": matrix.tolist(), "linear": linear.tolist(), "offset": offset,
            "financial_spec_without_returns": {k: v for k, v in spec.to_dict().items() if k not in ("returns", "benchmark")},
            "source_spec_hash": spec.fingerprint(),
        })
        write_json(path / "cases" / case["id"] / "numerical_transport.json", certificate)
        base = requests_for(spec, h, case["resource_budget"], 500)[1]["request"]
        cases[case["id"]] = (case, spec, h, base)
        histories[case["id"]] = []
    write_json(path / "cuda_selfcheck.json", checks)
    checkpoint()

    def evaluate(case_id, method, admission, phase, seed, draws_multiplier=1):
        case, spec, h, _ = cases[case_id]
        row = {"case_id": case_id, "method": method, "phase": phase, "seed": seed, "admission": admission}
        if admission is not None and admission["status"] != "accepted":
            row.update(status="rejected", reason=admission.get("reason", admission["status"]))
        else:
            try:
                result = search(spec, admission["gate_ir"] if admission else None, h,
                    method="uniform" if method == "uniform_conditioned" else "swap" if method == "allocation_swap" else "circuit",
                    seed=seed, evaluations=8 if draws_multiplier == 1 else 26,
                    shots=64, final_shots=64, fitting="mean" if admission else None,
                    basis_factory=basis_factory)
                row.update(status="completed", result=result)
            except Exception as exc:
                row.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
        write_json(path / "runs" / f"{case_id}__{phase}__{method}__{seed}.json", row)
        all_rows.append(row)
        print(json.dumps({"stage": "evaluated", "case_id": case_id, "method": method, "phase": phase, "status": row["status"], "objective": (row.get("result", {}).get("allocation") or {}).get("objective")}), flush=True)
        checkpoint()
        return row

    # The model remains resident across feedback calls; no old response replay.
    for round_index in range(ROUNDS):
        requests = [make_request(base, spec, i, round_index, histories[case_id]) for i, (case_id, (case, spec, h, base)) in enumerate(cases.items())]
        write_json(path / "llm" / f"round_{round_index}_requests.json", requests)
        answers, runtime = generate(requests, round_index)
        write_json(path / "llm" / f"round_{round_index}_answers.json", answers)
        write_json(path / "llm" / f"round_{round_index}_runtime.json", runtime)
        checkpoint()
        if len(answers) != len(requests) or {a["request_hash"] for a in answers} != {r["request_hash"] for r in requests}:
            raise ValueError("Live response/request identities disagree.")
        lookup = {a["request_hash"]: a for a in answers}
        for (case_id, (case, spec, h, _)), request in zip(cases.items(), requests, strict=True):
            answer = lookup[request["request_hash"]]
            admission = admit_response(answer, request, spec, h, case["resource_budget"])
            row = evaluate(case_id, f"llm_r{round_index}", admission, "design", 11)
            row["request_hash"] = answer["request_hash"]
            # Persist request linkage after evaluation; numerical rows are unchanged.
            write_json(path / "runs" / f"{case_id}__design__llm_r{round_index}__11.json", row)
            histories[case_id].append(feedback(row, answer))
        write_json(path / "feedback.json", histories)
        checkpoint()

    for case_id, (case, spec, h, _) in cases.items():
        for i in range(ROUNDS):
            program = random_program(spec, 9000 + 100 * list(cases).index(case_id) + i)
            admission = admit_cost_aware_program(normalize(program, spec), spec, h, case["resource_budget"])
            admission["source_control_program"] = program
            evaluate(case_id, f"random_r{i}", admission, "design", 11)
        for method in ("fixed_path", "fixed_star"):
            program = common_program(spec)
            if method == "fixed_star":
                program["parents"] = {key: 0 for key in program["parents"]}
                program["groups"] = [1] * len(program["groups"])
            admission = admit_cost_aware_program(disjoint_schedule(program, spec), spec, h, case["resource_budget"])
            evaluate(case_id, method, admission, "design", 11)
        for method in ("uniform_conditioned", "allocation_swap"):
            evaluate(case_id, method, None, "design", 11, draws_multiplier=3)

    # Freeze all winners before accessing any evaluation-seed outcome.
    selected = {}
    for case_id in cases:
        selected[case_id] = {}
        for family in ("llm", "random"):
            candidates = [r for r in all_rows if r["case_id"] == case_id and r["phase"] == "design" and r["method"].startswith(family + "_r")]
            best = min(candidates, key=selection_key)
            selected[case_id][family+"_selected"] = {"method": best["method"] if selection_key(best)[0] == 0 else None, "design_objective": (best.get("result", {}).get("allocation") or {}).get("objective"), "admission": best["admission"] if selection_key(best)[0] == 0 else {"status": "no_eligible_candidate"}}
        for method in ("fixed_path", "fixed_star"):
            row = next(r for r in all_rows if r["case_id"] == case_id and r["method"] == method)
            selected[case_id][method] = {"admission": row["admission"]}
    lock = {"version": VERSION, "inputs_hash": inputs["inputs_hash"], "selection_seed": 11, "evaluation_seeds": list(SEEDS), "selected": selected}
    lock["selection_hash"] = digest(lock)
    write_json(path / "selection_lock.json", lock)
    checkpoint()
    for case_id, values in selected.items():
        for method in ("llm_selected", "random_selected", "fixed_path", "fixed_star", "uniform_conditioned", "allocation_swap"):
            admission = values[method]["admission"] if method in values else None
            for seed in SEEDS:
                row = evaluate(case_id, method, admission, "evaluation", seed)
                if admission and row["status"] == "completed" and seed == SEEDS[0]:
                    export(admission["gate_ir"], cases[case_id][2], row["result"]["angles"], admission["verification"], path / "circuits" / case_id / method)
    with (path / "decisions.jsonl").open("w") as file:
        for row in all_rows:
            result = row.get("result", {})
            allocation = result.get("allocation")
            spec = cases[row["case_id"]][1]
            file.write(json.dumps({"case_id": row["case_id"], "method": row["method"], "phase": row["phase"], "seed": row["seed"], "status": row["status"], "previous_weights": spec.previous_weights.tolist(), "allocation": allocation, "weight_changes": (np.asarray(allocation["weights"])-spec.previous_weights).tolist() if allocation else None, "execution": "conditional_training_decision_not_market_execution"})+"\n")
    summary = {"version": VERSION, "inputs_hash": inputs["inputs_hash"], "live_requests": ROUNDS*len(cases), "runs": len(all_rows), "completed_runs": sum(r["status"] == "completed" for r in all_rows), "elapsed_seconds": perf_counter()-start, "financial_qualification": "not_established", "quantum_hardware": False, "selection_hash": lock["selection_hash"]}
    write_json(path / "completion.json", summary)
    checkpoint()
    return summary
