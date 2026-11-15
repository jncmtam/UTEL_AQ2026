"""Black-box circuit search: the control the insight-driven design must beat.

Random search draws CircuitSpecs uniformly from the whole design space (any mixer, initial
state, depth, pruning, optimiser) and keeps the best one on the training quarters. It uses
no data insight, so it answers: "is the designed circuit better than tuning blindly with the
same training data?". It runs with several seeds because a single search is noisy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .simulator import CompiledProblem, run_qaoa
from .spec import CircuitSpec, random_spec, verify


@dataclass
class Evaluated:
    arm: str
    order: int
    spec: CircuitSpec
    errors: list[str]
    fitness: float
    metrics: dict = field(default_factory=dict)

    def row(self) -> dict:
        return {"arm": self.arm, "order": self.order, "fitness": self.fitness, "errors": self.errors,
                **{f"m_{k}": v for k, v in self.metrics.items()},
                **{f"s_{k}": v for k, v in self.spec.to_dict().items()}}


class Evaluator:
    """Scores a spec on the training problems (mean success probability per shot)."""

    def __init__(self, problems: list[CompiledProblem], cx_budget: int, success_gap: float, shots: int, seed: int):
        self.problems, self.cx_budget, self.gap, self.shots, self.seed = problems, cx_budget, success_gap, shots, seed
        self._cache: dict[tuple, Evaluated] = {}

    def __call__(self, spec: CircuitSpec, arm: str, order: int) -> Evaluated:
        errs = verify(spec, self.problems[0].n, self.cx_budget)
        if errs:
            return Evaluated(arm, order, spec, errs, 0.0, {})
        if spec.key() in self._cache:
            e = self._cache[spec.key()]
            return Evaluated(arm, order, spec, [], e.fitness, dict(e.metrics))
        rs = [run_qaoa(p, spec, self.gap, self.shots, np.random.default_rng(self.seed + i))
              for i, p in enumerate(self.problems)]
        m = {"success_prob": float(np.mean([r.success_prob for r in rs])),
             "feasible_mass": float(np.mean([r.feasible_mass for r in rs])),
             "best_sample_gap": float(np.mean([min(r.best_sample_gap, 10) for r in rs])),
             "evaluations": float(np.mean([r.evaluations for r in rs])),
             "two_qubit_gates": max(r.two_qubit_gates for r in rs)}
        e = Evaluated(arm, order, spec, [], m["success_prob"], m)
        self._cache[spec.key()] = e
        return e


def random_search(ev: Evaluator, n_designs: int, seed: int, arm: str = "random") -> list[Evaluated]:
    rng = np.random.default_rng(seed)
    return [ev(random_spec(rng), arm, i) for i in range(n_designs)]


def best(history: list[Evaluated]) -> Evaluated:
    ok = [h for h in history if not h.errors]
    return max(ok, key=lambda h: (round(h.fitness, 4), -h.metrics.get("two_qubit_gates", 0)))
