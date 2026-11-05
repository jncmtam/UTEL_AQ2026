"""Actual measured gate edits, a live feedback ablation and a numerical teacher."""

from copy import deepcopy
from pathlib import Path
import json
from time import perf_counter
import numpy as np

from agqo.synthesis.profile import digest
from agqo.synthesis.typed import domain
from .budget_search import admit_cost_aware_program, search
from .data import write_json, sha
from .edge_program import prepare as edge_inputs, requests_for, normalize
from .frozen_numerics import bind
from .gpu_optimization import make_request, permuted_schema, admit_response, selection_key
from .guidance import exchange_features
from .improvement import decode
from .quantum import export

RUN_ID = "counterfactual_editor_v1"
VERSION = "measured-gate-editor-v1"


def prepare():
    inputs = edge_inputs()
    inputs["cases"] = [c for c in inputs["cases"] if "n20" in c["id"]]
    inputs["requests"] = []
    inputs["inputs_hash"] = digest({"cases": inputs["cases"], "interface_version": inputs["interface_version"]})
    old = Path("results/research/live_gpu_optimization_v1/evaluation")
    lock = json.loads((old / "selection_lock.json").read_text())
    parents = {}
    for case in inputs["cases"]:
        cid = case["id"]
        method = lock["selected"][cid]["llm_selected"]["method"]
        index = int(method.removeprefix("llm_r"))
        answers = json.loads((old / "llm" / f"round_{index}_answers.json").read_text())
        previous = json.loads((old / "runs" / f"{cid}__design__{method}__11.json").read_text())
        answer = next(a for a in answers if a["request_hash"] == previous["request_hash"])
        anchors = {}
        for name in (method, "fixed_star", "fixed_path"):
            file = old / "runs" / f"{cid}__design__{name}__11.json"
            anchors[name] = {"record": json.loads(file.read_text()), "source_file": str(file), "source_sha256": sha(file)}
        parents[cid] = {"actual_program": answer["response"], "anchors": anchors, "old_request_hash": answer["request_hash"]}
    inputs["parents"] = parents
    inputs["dataset_manifest"] = json.loads((old / "dataset_manifest.json").read_text())
    return inputs


def neighbors(program, spec):
    """Four deterministic one-edit controls, never credited as model design."""
    free = domain(spec)["free_qubits"]
    features = exchange_features(spec)["edges"]
    candidates, seen = [], set()

    def add(key, edge=None, group=None, reason=""):
        value = deepcopy(program)
        old = deepcopy(value["exchanges"][key])
        if edge is not None:
            value["exchanges"][key]["edge"] = edge
        if group is not None:
            value["exchanges"][key]["group"] = group
        signature = digest(value["exchanges"])
        if old == value["exchanges"][key] or signature in seen:
            return
        seen.add(signature)
        candidates.append({"id": f"edit_{len(candidates)}", "program": value,
            "patch": {"child": key, "old": old, "new": deepcopy(value["exchanges"][key])}, "construction": reason})

    add(f"p{len(free)-1}", edge=f"EDGE_{free[-2]}_{free[-1]}", reason="pathward rewire of final child")
    alternatives = [e for e in features if program["exchanges"][e["parent_key"]]["edge"] != e["id"]]
    for reverse in (True, False):
        for edge in sorted(alternatives, key=lambda e: (e["rms_delta_B"], e["id"]), reverse=reverse):
            old_count = len(candidates)
            add(edge["parent_key"], edge=edge["id"], reason="high-RMS alternative" if reverse else "low-RMS alternative")
            if len(candidates) > old_count:
                break
    # A circuit may already contain the pathward edge. Complete the same
    # three-rewire budget deterministically rather than duplicating a control.
    for edge in sorted(alternatives, key=lambda e: (e["rms_delta_B"], e["id"]), reverse=True):
        if len(candidates) >= 3:
            break
        add(edge["parent_key"], edge=edge["id"], reason="next distinct RMS-ordered alternative")
    chosen = max(features, key=lambda e: e["rms_delta_B"])["parent_key"]
    add(chosen, group=1-program["exchanges"][chosen]["group"], reason="split highest-sensitivity exchange beta group")
    if len(candidates) != 4:
        raise ValueError("The frozen neighborhood requires four unique one-edit programs.")
    return candidates


def measurement(row):
    result = row.get("result", {})
    batches = result.get("fitting_record", {}).get("batches", [])
    return {"status": row["status"], "admission": (row.get("admission") or {}).get("status"),
        "best_F": (result.get("allocation") or {}).get("objective"),
        "final_normalized_mean_F": batches[-1]["mean_loss"] if batches else None,
        "final_feasible_fraction": batches[-1]["feasible_fraction"] if batches else None,
        "resources": (row.get("admission") or {}).get("verification", {}).get("resources"),
        "reason": row.get("reason"), "metric": "allocated estimation F; lower is better, not a future return"}


def request(base, spec, index, arm, current, current_measurement, alternatives):
    value = make_request(base, spec, index, 0, [])
    value["seed"] = 800+index
    value["schema"] = permuted_schema(spec, value["seed"])
    value["system"] += "\nImprove or retain the supplied actual circuit. You may change any legal edges/groups. Detailed feedback, when supplied, describes measured one-edit alternatives, not suggestions proved optimal. Compare their actual F and resources. You may reuse one or combine changes; explicitly distinguish reuse from an untested hypothesis. Do not invent a quantum/financial guarantee. Return the complete new circuit in the same schema."
    value["payload"].update(prompt_version=VERSION, current_actual_program=current,
        current_measured_result=current_measurement, feedback_arm=arm,
        measured_alternatives=alternatives if arm == "counterfactual" else [],
        attribution="Known-candidate reuse is not an incremental LLM discovery; the numerical teacher is scored separately.")
    value.pop("request_hash")
    value["request_hash"] = digest(value)
    return value


def run(directory, inputs, generate, basis_factory, checkpoint=lambda: None):
    path = Path(directory)
    if path.exists():
        raise ValueError("Existing paid edit study retained; no automatic retry.")
    if inputs["inputs_hash"] != digest({"cases": inputs["cases"], "interface_version": inputs["interface_version"]}):
        raise ValueError("Prepared inputs changed.")
    path.mkdir(parents=True)
    write_json(path / "protocol.json", inputs["live_protocol"])
    write_json(path / "dataset_manifest.json", inputs["dataset_manifest"])
    write_json(path / "historical_anchors.json", inputs["parents"])
    start, records, prepared, selections = perf_counter(), [], [], {}
    cases = {}

    def evaluate(cid, name, admission, phase, seed):
        spec, h = cases[cid]
        row = {"case_id": cid, "method": name, "phase": phase, "seed": seed, "admission": admission}
        if admission is not None and admission["status"] != "accepted":
            row.update(status="rejected", reason=admission.get("reason", admission["status"]))
        else:
            try:
                row.update(status="completed", result=search(spec, admission["gate_ir"] if admission else None, h,
                    method="swap" if admission is None else "circuit", seed=seed,
                    evaluations=8, shots=64, final_shots=64,
                    fitting="mean" if admission else None, basis_factory=basis_factory))
            except Exception as exc:
                row.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
        records.append(row)
        write_json(path / "runs" / f"{cid}__{phase}__{name}__{seed}.json", row)
        print(json.dumps({"stage": "evaluated", "case_id": cid, "method": name, "phase": phase, "status": row["status"]}), flush=True)
        checkpoint()
        return row

    for index, case in enumerate(inputs["cases"]):
        cid = case["id"]
        spec, h, certificate = bind(decode(case["spec"]), case["frozen_numerics"])
        cases[cid] = (spec, h)
        current = inputs["parents"][cid]["actual_program"]
        current_row = next(a["record"] for k, a in inputs["parents"][cid]["anchors"].items() if k.startswith("llm_"))
        from .cuda_simulation import crosscheck_cuda
        check = crosscheck_cuda(spec, h, current_row["admission"]["gate_ir"], [np.linspace(.1, .4, len(current_row["result"]["angles"]))])
        write_json(path / "cases" / cid / "cuda_selfcheck.json", check)
        write_json(path / "cases" / cid / "numerical_transport.json", certificate)
        matrix, linear, offset = spec.quadratic()
        write_json(path / "cases" / cid / "sufficient_statistics.json", {"matrix": matrix.tolist(), "linear": linear.tolist(), "offset": offset,
            "financial_spec_without_returns": {k: v for k, v in spec.to_dict().items() if k not in ("returns", "benchmark")}, "source_spec_hash": spec.fingerprint()})
        options, alternatives = [current_row], []
        for edit in neighbors(current, spec):
            admission = admit_cost_aware_program(normalize(edit["program"], spec), spec, h, case["resource_budget"])
            row = evaluate(cid, edit["id"], admission, "design", 11)
            row["source_program"] = edit["program"]
            write_json(path / "runs" / f"{cid}__design__{edit['id']}__11.json", row)
            options.append(row)
            alternatives.append({"id": edit["id"], "patch": edit["patch"], "measurement": measurement(row), "origin": "numerical one-edit control"})
        for name, anchor in inputs["parents"][cid]["anchors"].items():
            row = anchor["record"]
            if not name.startswith("llm_"):
                options.append(row)
                parent = current_row["admission"]["normalized_program"]
                other = row["admission"]["gate_ir"]
                alternatives.append({"id": name, "known_program": "all first-free-qubit star/group1" if name == "fixed_star" else "fixed path with compiler-shared beta",
                    "measurement": measurement(row), "origin": anchor["source_file"], "source_sha256": anchor["source_sha256"],
                    "physical_program_hash": digest(other), "current_parent_count": len(parent["parents"])})
        teacher = min(options, key=selection_key)
        if selection_key(teacher)[0]:
            raise ValueError("No eligible numerical teacher; stop before model load.")
        selections[cid] = {"current": current_row["admission"], "teacher": teacher["admission"], "teacher_origin": teacher["method"],
            "teacher_design_measurement": measurement(teacher), "supplied_physical_hashes": [digest(r["admission"]["gate_ir"]) for r in options if r["admission"]["status"] == "accepted"]}
        base = requests_for(spec, h, case["resource_budget"], 800+index)[1]["request"]
        prepared += [{"case_id": cid, "arm": arm, "request": request(base, spec, index, arm, current, measurement(current_row), alternatives)} for arm in ("aggregate", "counterfactual")]
    contrast = any(selections[cid]["teacher_design_measurement"]["best_F"] < next(a["record"] for k, a in inputs["parents"][cid]["anchors"].items() if k.startswith("llm_"))["result"]["allocation"]["objective"]-1e-12 for cid in cases)
    if not contrast:
        write_json(path / "BLOCKED.json", {"reason": "No measured better-F contrast; no new model load justified.", "new_model_requests": 0})
        checkpoint()
        return {"status": "uninformative_neighborhood", "live_requests": 0, "runs": len(records)}
    write_json(path / "prepared_requests.json", prepared)
    write_json(path / "teacher_lock.json", selections)
    checkpoint()
    answers, runtime = generate([p["request"] for p in prepared])
    write_json(path / "answers.json", answers)
    write_json(path / "gpu_runtime.json", runtime)
    checkpoint()
    if len(answers) != 4 or {a["request_hash"] for a in answers} != {p["request"]["request_hash"] for p in prepared}:
        raise ValueError("Response/request identity changed.")
    lookup = {a["request_hash"]: a for a in answers}
    for entry in prepared:
        cid, arm = entry["case_id"], entry["arm"]
        case = next(c for c in inputs["cases"] if c["id"] == cid)
        spec, h = cases[cid]
        admission = admit_response(lookup[entry["request"]["request_hash"]], entry["request"], spec, h, case["resource_budget"])
        selections[cid][arm] = admission
    write_json(path / "admissions.json", selections)
    for cid, selected in selections.items():
        for method in ("aggregate", "counterfactual", "current", "teacher", "allocation_swap"):
            for seed in (23, 47):
                admission = selected[method] if method != "allocation_swap" else None
                row = evaluate(cid, method, admission, "evaluation", seed)
                if admission and row["status"] == "completed" and seed == 23:
                    export(admission["gate_ir"], cases[cid][1], row["result"]["angles"], admission["verification"], path / "circuits" / cid / method)
    summary = {"status": "completed", "live_requests": 4, "runs": len(records), "completed_runs": sum(r["status"] == "completed" for r in records),
        "elapsed_seconds": perf_counter()-start, "inputs_hash": inputs["inputs_hash"], "financial_qualification": False}
    write_json(path / "completion.json", summary)
    checkpoint()
    return summary
