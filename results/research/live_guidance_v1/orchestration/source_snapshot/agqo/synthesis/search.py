"""Budgeted generate–verify–evaluate–repair search with complete checkpoints."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
import json
import numpy as np

from agqo.repair.solvers import exact_solve, milp_solve
from .builders import build_rule
from .client import request_for
from .compiler import export_artifacts, verify
from .profile import data_profile, digest, financial_ir, hamiltonian_ir
from .optimizer import optimize


@dataclass(frozen=True)
class SearchConfig:
    initial_proposals: int = 4
    repair_rounds: int = 2
    proposals_per_repair: int = 2
    screen_evaluations: int = 8
    screen_shots: int = 64
    final_evaluations: int = 24
    final_shots: int = 128
    finalists: int = 2
    seed: int = 11
    max_tokens: int = 4096
    use_proposed_angles: bool = False

    def __post_init__(self):
        if not 1 <= self.initial_proposals <= 4 or not 0 <= self.repair_rounds <= 2 or not 1 <= self.proposals_per_repair <= 2:
            raise ValueError("Search envelope exceeded.")
        if any(type(v) is not int or v < 1 for v in (self.screen_evaluations, self.screen_shots, self.final_evaluations, self.final_shots, self.finalists)):
            raise ValueError("Positive integer shot/evaluation budgets required.")


def _rank(candidate):
    evaluation = candidate.get("evaluation", {})
    resource = candidate.get("verification", {}).get("resources", {})
    return (0 if evaluation.get("feasible") else 1, -evaluation.get("sampled_feasible_probability", 0),
            evaluation.get("objective", float("inf")), resource.get("transpiled_cx", float("inf")))


def run_search(problem, directory, client=None, config=SearchConfig(), ablation="full", feedback_level="full", donor=None):
    if feedback_level not in {"none", "verifier", "full"}:
        raise ValueError("Unknown feedback level.")
    start = perf_counter()
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    h, compiled = hamiltonian_ir(problem)
    profile = data_profile(problem)
    definition = {"version": "gate-search-v1", "problem_hash": problem.fingerprint(), "hamiltonian_hash": h["hamiltonian_hash"],
                  "config": asdict(config), "ablation": ablation, "feedback_level": feedback_level,
                  "origin": "rule_baseline_not_llm" if client is None else client.mode,
                  "data_profile_hash": digest(profile),
                  "source_sha256": digest({p.name: p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})}
    (path / "protocol.json").write_text(json.dumps(definition, indent=2))
    (path / "financial_ir.json").write_text(json.dumps(financial_ir(problem), ensure_ascii=False, indent=2))
    (path / "data_profile.json").write_text(json.dumps(profile, indent=2, allow_nan=False))
    (path / "hamiltonian_ir.json").write_text(json.dumps(h, indent=2, allow_nan=False))
    candidates, feedback, total_shots = [], [], 0
    rounds = 1 if feedback_level == "none" else 1 + config.repair_rounds
    for round_index in range(rounds):
        count = config.initial_proposals if round_index == 0 else config.proposals_per_repair
        offset = len(candidates)
        if client is None:
            answers = [{"status": "ok", "response": build_rule(problem, h, profile, seed=config.seed + offset + i),
                        "execution": "rule_baseline_not_llm", "amortized_inference_seconds": 0} for i in range(count)]
        else:
            requests = [request_for(problem, h, config.seed + offset + i, feedback, ablation, donor, config.max_tokens) for i in range(count)]
            try:
                answers = client.batch(requests)
            except ValueError as exc:
                answers = [{"status": "budget_blocked", "reason": str(exc)} for _ in requests]
        for index, answer in enumerate(answers):
            candidate = {"id": f"r{round_index}_c{index}", "round": round_index, "inference": answer,
                         "origin": answer.get("execution", "not_run")}
            if answer["status"] == "ok" and isinstance(answer.get("response"), dict):
                ir = answer["response"]
                verification = verify(ir, problem, h, compiled)
                candidate.update(gate_ir=ir, verification=verification)
                if verification["valid"]:
                    evaluation = optimize(ir, problem, compiled, config.seed, config.screen_evaluations, config.screen_shots,
                                          use_proposed_angles=config.use_proposed_angles)
                    total_shots += evaluation["total_shots"]
                    candidate["evaluation"] = evaluation
            else:
                candidate["verification"] = {"valid": False, "errors": [{"code": answer["status"], "message": answer.get("reason", answer.get("finish_reason", "No verified output"))}]}
            candidates.append(candidate)
        feedback = []
        for candidate in candidates[-count:]:
            record = {"candidate_id": candidate["id"], "gate_ir": candidate.get("gate_ir"), "verification": candidate["verification"]}
            if feedback_level == "full" and "evaluation" in candidate:
                record["measured_quality"] = {k: candidate["evaluation"].get(k) for k in ("objective", "sampled_feasible_probability", "feasible", "total_shots")}
            feedback.append(record)
        # Bound feedback prompt growth; keep latest counterexamples and compact resource evidence.
        feedback = feedback[:2]
        (path / "checkpoint.json").write_text(json.dumps({"definition": definition, "round": round_index, "candidates": candidates, "total_shots": total_shots}, ensure_ascii=False, indent=2, allow_nan=False))
        if all(a["status"] in {"not_run", "budget_blocked", "error"} for a in answers):
            break
    valid = [c for c in candidates if c["verification"]["valid"]]
    finalists = sorted(valid, key=_rank)[:config.finalists]
    for candidate in finalists:
        candidate["screen_evaluation"] = candidate["evaluation"]
        final = optimize(candidate["gate_ir"], problem, compiled, config.seed, config.final_evaluations, config.final_shots,
                         use_proposed_angles=config.use_proposed_angles)
        candidate["evaluation"] = final
        total_shots += final["total_shots"]
    winner = min(finalists, key=_rank) if finalists else None
    reference, mip = exact_solve(problem), milp_solve(problem)
    if winner:
        export_artifacts(winner["gate_ir"], compiled, winner["evaluation"]["angles"], path / "winner", winner["verification"])
    inference_seconds = sum(c["inference"].get("amortized_inference_seconds", 0) for c in candidates)
    theoretical_cap = (config.initial_proposals + config.repair_rounds * config.proposals_per_repair) * (config.screen_evaluations + 1) * config.screen_shots + config.finalists * (config.final_evaluations + 1) * config.final_shots
    output = {"version": "gate-search-v1", "definition": definition, "status": "verified_candidate" if winner else "no_verified_candidate",
              "winner_id": None if winner is None else winner["id"], "candidates": candidates,
              "exact_reference": reference, "milp_reference": mip, "total_shots": total_shots, "shot_budget_cap": theoretical_cap,
              "oracle_classical_states": compiled["states"], "oracle_construction_seconds": compiled["seconds"],
              "elapsed_seconds": perf_counter() - start, "charged_recorded_inference_seconds": inference_seconds,
              "claims": {"model_qualified": False, "quantum_advantage": "not_established", "note": "One search is not model qualification; oracle construction remains exponential."}}
    (path / "search.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    return output
