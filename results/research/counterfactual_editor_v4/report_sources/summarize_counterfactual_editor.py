"""Read-only audit of actual counterfactual-feedback generations and decisions."""

from copy import deepcopy
from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from agqo.research.data import sha, write_json
from agqo.synthesis.profile import digest
try:
    from scripts.summarize_tail_pilot import audit_run
except ModuleNotFoundError:
    from summarize_tail_pilot import audit_run

ROOT = Path("results/research/counterfactual_editor_v4")


def family_signature(ir):
    """Ignore names/prose; keep physical order, sharing, preparation and angles."""
    value = deepcopy({k: ir.get(k) for k in ("initial_bits", "initialization", "preparation", "layers")})
    names = {}

    def canonical(node):
        if isinstance(node, list):
            return [canonical(n) for n in node]
        if not isinstance(node, dict):
            return node
        result = {}
        for k, v in node.items():
            if k == "parameter" and v is not None:
                names.setdefault(v, f"p{len(names)}")
                result[k] = names[v]
            else:
                result[k] = canonical(v)
        return result
    return digest(canonical(value))


def main():
    p, e = ROOT, ROOT / "evaluation"
    if (p / "RESULTS.md").exists():
        raise ValueError("Existing report retained; do not overwrite evidence.")
    read = lambda path: json.loads(path.read_text())
    manifest = read(p / "orchestration/download_manifest.json")
    for name, value in manifest.items():
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(e / name) == value, name
    complete = read(e / "completion.json")
    assert complete == read(p / "orchestration/completed.json")
    if complete["live_requests"] == 0:
        write_json(p / "analysis.json", {"status": "blocked_uninformative_neighborhood", "complete": complete, "hashes_verified": len(manifest)})
        (p / "RESULTS.md").write_text("# No live inference justified\n\nThe bounded GPU neighborhood stage found no informative better-F contrast. No model was loaded or invoked; paid search was stopped rather than fabricating improvement.\n")
        return
    protocol = read(e / "protocol.json")
    prepared = read(p / "orchestration/prepared.json")
    assert protocol == prepared["protocol"]
    for name, value in protocol["package_source_hashes"].items():
        assert sha(e / "source_snapshot" / name) == value
    requests, answers = read(e / "prepared_requests.json"), read(e / "answers.json")
    assert len(requests) == len(answers) == complete["live_requests"] == 4
    lookup = {a["request_hash"]: a for a in answers}
    assert set(lookup) == {r["request"]["request_hash"] for r in requests}
    anchors, admissions = read(e / "historical_anchors.json"), read(e / "admissions.json")
    for cid, source in anchors.items():
        for anchor in source["anchors"].values():
            file = Path(anchor["source_file"])
            assert sha(file) == anchor["source_sha256"]
            assert read(file) == anchor["record"]
    cases = list(anchors)
    methods = ("aggregate", "counterfactual", "current", "teacher", "allocation_swap")
    expected = {(c, "design", f"edit_{i}", 11) for c in cases for i in range(4)} | {(c, "evaluation", m, s) for c in cases for m in methods for s in (23, 47)}
    records = [read(f) for f in sorted((e / "runs").glob("*.json"))]
    assert {(r["case_id"], r["phase"], r["method"], r["seed"]) for r in records} == expected
    assert len(records) == complete["runs"] == 28
    rows, rescored, residual, cuda_runs = [], 0, 0., 0
    for r in records:
        common = {k: r[k] for k in ("case_id", "phase", "method", "seed", "status")}
        if r["status"] != "completed":
            rows.append({**common, "best_objective": None, "final_eligible": False, "observations": 0, "reason": r.get("reason")})
            continue
        stats = read(e / "cases" / r["case_id"] / "sufficient_statistics.json")
        _, result, n, error = audit_run(r, stats, None, 576)
        if r["admission"] is not None:
            meta = r["result"]["simulation_execution"]
            assert meta["cuda"] and meta["execute_calls"] == r["result"]["state_evaluations"] == 9
            assert meta["execution"] == "ideal_cuda_simulation" and not meta["cpu_fallback"]
            cuda_runs += 1
        rows.append({**result, **common})
        rescored += n
        residual = max(residual, error)
    frame = pd.DataFrame(rows)
    attempts, texts = [], ["# Exact live gate-edit responses", ""]
    for entry in requests:
        request = entry["request"]
        assert request["request_hash"] == digest({k: v for k, v in request.items() if k != "request_hash"})
        answer = lookup[request["request_hash"]]
        if answer["status"] == "ok":
            assert json.loads(answer["raw_text"]) == answer["response"] and answer["finish_reason"] == "stop"
        assert answer["execution"] == "live_modal_vllm"
        cid, arm = entry["case_id"], entry["arm"]
        actual = admissions[cid][arm]
        if actual["status"] == "accepted":
            assert actual["source_response_hash"] == digest(answer["response"])
        known = [a["record"]["admission"]["gate_ir"] for a in anchors[cid]["anchors"].values()]
        known += [r["admission"]["gate_ir"] for r in records if r["case_id"] == cid and r["phase"] == "design" and r["admission"]["status"] == "accepted"]
        sig = family_signature(actual["gate_ir"]) if actual["status"] == "accepted" else None
        novelty = bool(sig and sig not in {family_signature(ir) for ir in known})
        changed = bool(sig and sig != family_signature(admissions[cid]["current"]["gate_ir"]))
        attempts.append({"case_id": cid, "arm": arm, "status": answer["status"], "admission": actual["status"], "novel_vs_all_supplied": novelty, "changed_from_current": changed, "physical_family_signature": sig, **answer["usage"]})
        texts += [f"## {cid}: {arm}", "", f"Request `{request['request_hash']}`; status `{answer['status']}`; admission `{actual['status']}`.", "", "````text", answer["raw_text"], "````", ""]
    comparisons = []
    for cid in cases:
        for seed in (23, 47):
            subset = frame[(frame.case_id == cid) & (frame.phase == "evaluation") & (frame.seed == seed)]
            actual = subset[subset.method == "counterfactual"].iloc[0]
            for ref in ("aggregate", "current", "teacher", "allocation_swap"):
                other = subset[subset.method == ref].iloc[0]
                valid = actual.status == other.status == "completed" and pd.notna(actual.best_objective) and pd.notna(other.best_objective)
                comparisons.append({"case_id": cid, "seed": seed, "reference": ref, "valid": valid, "difference_pct": 100*(actual.best_objective/other.best_objective-1) if valid else None, "llm_final_eligible": bool(actual.final_eligible)})
    comp = pd.DataFrame(comparisons)
    summary = []
    for ref, part in comp.groupby("reference", sort=False):
        valid = part[part.valid]
        full = len(valid) == 4 and valid.llm_final_eligible.all()
        mean = float(valid.difference_pct.mean()) if len(valid) else None
        worst = float(valid.groupby("case_id").difference_pct.mean().max()) if len(valid) else None
        summary.append({"reference": ref, "pairs": len(valid), "mean_difference_pct": mean, "worst_case_mean_pct": worst, "threshold_met": bool(full and mean <= -2 and worst <= 5)})
    novelty = all(a["novel_vs_all_supplied"] for a in attempts if a["arm"] == "counterfactual")
    target = novelty and all(s["threshold_met"] for s in summary if s["reference"] in ("aggregate", "teacher"))
    runtime = read(e / "gpu_runtime.json")
    assert runtime["execution"] == "live_modal_gpu_not_replay" and any(g in runtime["gpu"] for g in ("A100", "H200"))
    assert all(a["model"] == runtime["model"] and a["revision"] == runtime["revision"] for a in answers)
    cost = read(p / "orchestration/cost_report.json")
    analysis = {"registered_target": "supported" if target else "unsupported", "hashes_verified": len(manifest), "runs": len(records), "completed_runs": sum(r["status"] == "completed" for r in records), "live_requests": 4, "admitted": sum(a["admission"] == "accepted" for a in attempts), "observations": int(frame.observations.sum()), "feasible_allocations_rescored": rescored, "maximum_F_residual": residual, "cuda_runs": cuda_runs, "attempts": attempts, "comparisons": summary, "runtime": runtime, "cost": cost, "prior_study_reserved_usd": 3.64, "failed_startup_reserved_usd": 3.64, "financial_qualification": False, "independent_financial_test": False}
    write_json(p / "analysis.json", analysis)
    frame.to_csv(p / "metrics.csv", index=False)
    comp.to_csv(p / "comparisons.csv", index=False)
    pd.DataFrame(attempts).to_csv(p / "model_attempts.csv", index=False)
    (p / "ACTUAL_RESPONSES.md").write_text("\n".join(texts))
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    for i, ref in enumerate([s["reference"] for s in summary]):
        values = comp[(comp.reference == ref) & comp.valid].difference_pct
        ax.scatter(np.full(len(values), i), values, color="gray", alpha=.6)
        ax.scatter(i, values.mean(), marker="D", color="#14645b", s=90)
    ax.axhline(0, color="black")
    ax.axhline(-2, linestyle="--", color="#3473a8")
    ax.set(xticks=range(len(summary)), xticklabels=[s["reference"] for s in summary], ylabel="Detailed-feedback F / reference F − 1 (%)", title="Measured edit feedback: opened US development cases\nNegative favors detailed LLM; dots are dependent pairs")
    fig.savefig(p / "feedback-comparison.png", dpi=170)
    plt.close(fig)
    lines = ["# Counterfactual gate-editor results", "", f"Registered incremental-LLM target: **{analysis['registered_target']}**. Actual live GPU requests4; admitted{analysis['admitted']}/4; completed{analysis['completed_runs']}/28. Verified{len(manifest)} downloaded hashes and independently rescored{rescored:,} feasible allocations (max residual{residual:.3g}).", "", "One pinned Coder30 on one available H200/A10080GB generated actual full circuits after either aggregate-only or measured gate-edit feedback. CUDA executes quantum evolution; CPU executes compilation/control/CLARABEL allocation. All comparisons use opened, conditional US estimation data and previously opened seeds; no independent investment test or quantum hardware execution.", "", "| Reference | Valid/4 pairs | Detailed LLM mean F difference |", "|---|---:|---:|"]
    for s in summary:
        value = f"{s['mean_difference_pct']:+.3f}%" if s["mean_difference_pct"] is not None else "unavailable"
        lines.append(f"| {s['reference']} | {s['pairs']}/4 | {value} |")
    lines += ["", "![Feedback comparison](feedback-comparison.png)", "", "## Did the model contribute a new circuit?", "", "```json", json.dumps(attempts, indent=2), "```", "", "Physical-family signatures remove prose and parameter renaming, retaining preparation, actual gate order and sharing. Merely selecting a known numerical candidate is not an incremental LLM discovery. Both2% margins (aggregate and numerical teacher), no>5% case regression, empirical final feasibility and novelty versus all supplied candidates are required. Four dependent pairs cannot qualify a production model or financial advantage.", "", "## Complete evidence and costs", "", "[Exact raw responses](ACTUAL_RESPONSES.md) · [Full requests, numerical feedback and schemas](evaluation/prepared_requests.json) · [Actual GPU proof](evaluation/gpu_runtime.json) · [Source-bound historical anchors](evaluation/historical_anchors.json) · [Numerical teacher lock](evaluation/teacher_lock.json) · [All runs](metrics.csv) · [Audit](analysis.json)", "", f"The new worker took{complete['elapsed_seconds']:.2f}s; reserved USD{cost['reserved_usd_total']:.2f}, not an invoice. Prior source study reservedUSD3.64. Shared numerical-neighborhood costs, all new attempts and historical anchor costs remain explicit. The numerical teacher is the direct lookup control. A better model-assisted decision is not a model discovery if the program was supplied. Prior preparation v1 was stopped on tokenizer sizing with zero GPU dispatch; v2 declares a coefficient-list context projection in both arms, while exact full COST/H remains unchanged.", "", "Historical investable-data admission and B-versus-F formulation mismatch remain unresolved. No automatic model sweep or additional paid retry is scheduled. Negative results remain part of the project."]
    (p / "RESULTS.md").write_text("\n".join(lines)+"\n")
    (p / "PROGRESS.md").write_text(f"# Progress\n\nNew live gate-edit study complete and audited. Target **{analysis['registered_target']}**;{analysis['admitted']}/4 admitted;{analysis['completed_runs']}/28 runs completed. No additional inference scheduled. Read RESULTS.md and analysis.json.\n")
    print(json.dumps({k: analysis[k] for k in ("registered_target", "live_requests", "admitted", "completed_runs", "observations", "feasible_allocations_rescored", "comparisons", "attempts")}, indent=2))


if __name__ == "__main__":
    main()
