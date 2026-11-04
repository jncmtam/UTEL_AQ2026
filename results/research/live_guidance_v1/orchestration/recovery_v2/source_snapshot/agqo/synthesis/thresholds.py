"""Pre-registered project targets, distinct from empirical results in related papers."""
from dataclasses import asdict, dataclass
import numpy as np


@dataclass(frozen=True)
class Targets:
    version: str = "synthesis-targets-v1"
    first_valid_rate: float = 0.8
    repaired_instance_rate: float = 0.9
    state_fidelity_min: float = 1 - 1e-9
    cardinality_leak_max: float = 1e-9
    feasible_probability_median: float = 0.9
    normalized_gap_median_max: float = 0.05
    relative_gap_improvement: float = 0.2
    relative_cx_reduction: float = 0.2
    minimum_independent_instances: int = 10

    def to_dict(self):
        return asdict(self)


def wilson_interval(successes,total):
    if total<1:return None
    z=1.959963984540054;p=successes/total;denominator=1+z*z/total
    center=(p+z*z/(2*total))/denominator
    half=z*np.sqrt(p*(1-p)/total+z*z/(4*total*total))/denominator
    return [max(0.,float(center-half)),min(1.,float(center+half))]


def quality(problem, compiled, evaluation):
    feasible_values = compiled["objective"][compiled["feasible"]]
    if not len(feasible_values):
        return {"reference_status": "infeasible", "normalized_gap": None, "target_available": False}
    optimum, maximum = float(feasible_values.min()), float(feasible_values.max())
    span = maximum - optimum
    gap = None if not evaluation.get("feasible") else max(0., evaluation["objective"] - optimum)
    normalized = None if gap is None else 0. if span <= 1e-14 and gap <= 1e-12 else gap / max(span, 1e-14)
    return {"reference_status": "optimal", "reference_objective": optimum, "feasible_objective_span": span,
            "normalized_gap": normalized, "target_available": True}


def assess(records, independent_instances, targets=Targets()):
    first = [r for r in records if r.get("round", 0) == 0]
    first_rate = sum(r.get("verification", {}).get("valid", False) for r in first) / max(1, len(first))
    winners = [r for r in records if r.get("chosen")]
    probabilities = [r["evaluation"].get("sampled_feasible_probability", 0) for r in winners if r.get("quality", {}).get("target_available")]
    gaps = [1.0 if r["quality"]["normalized_gap"] is None else r["quality"]["normalized_gap"] for r in winners if r.get("quality", {}).get("target_available")]
    valid_instances = len({r["case_id"] for r in records if r.get("verification", {}).get("valid")})
    gates = {"G1_first_valid": first_rate >= targets.first_valid_rate,
             "G1_repaired_instances": valid_instances / max(1, independent_instances) >= targets.repaired_instance_rate,
             "G2_feasibility": bool(probabilities) and float(np.median(probabilities)) >= targets.feasible_probability_median,
             "G2_quality": bool(gaps) and float(np.median(gaps)) <= targets.normalized_gap_median_max}
    return {"first_valid_rate": first_rate, "valid_instance_rate": valid_instances / max(1, independent_instances),
            "first_valid_wilson95": wilson_interval(sum(r.get("verification",{}).get("valid",False) for r in first),len(first)),
            "valid_instance_wilson95": wilson_interval(valid_instances,independent_instances),
            "median_feasible_probability": None if not probabilities else float(np.median(probabilities)),
            "median_normalized_gap": None if not gaps else float(np.median(gaps)), "gates": gates,
            "sample_sufficient_for_qualification": independent_instances >= targets.minimum_independent_instances,
            "qualified": independent_instances >= targets.minimum_independent_instances and all(gates.values()),
            "interpretation": "Project targets, not paper-reported thresholds. Small pilot is diagnostic only; Wilson intervals assume Bernoulli cases and are descriptive for these heterogeneous tasks."}
