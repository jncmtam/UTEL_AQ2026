"""LLM Circuit Architect: evolutionary circuit design with an exact evaluator in the loop.

Method (FunSearch / AlphaEvolve pattern, scaled to a laptop):
  round 0   the LLM reads a numerical summary of the training Hamiltonians and proposes M CircuitSpecs
  round r   the LLM sees the scored leaderboard (and rejected specs with reasons) and proposes M new specs
  every spec is verified (schema, alignment, two-qubit budget) and then scored by exact simulation
The best spec is FROZEN and reused on unseen dates with zero further LLM calls.

Controls with the identical budget (rounds x M designs):
  default   textbook QAOA
  random    uniform random specs
  evolve    classical mutation of the current best specs (no LLM)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from ..quantum.simulator import CompiledProblem, run_qaoa, uniform_reference
from ..quantum.spec import DEFAULT_SPEC, SPEC_SCHEMA, CircuitSpec, mutate, random_spec, verify
from .client import LLMClient, make_request

SYSTEM = """You are the quantum-circuit architect of AGQO. You design QAOA circuits that sample good integer-lot
rebalancing decisions for a VN30 tracking portfolio. The financial Hamiltonian is LOCKED: you cannot change any
coefficient; you only choose how the circuit is built and trained.

Design space (CircuitSpec fields):
- layers p (1-6): alternating phase-separator / mixer layers.
- initial_state: "uniform" (|+>^n) or "warm_start" (product state biased by the continuous relaxation of the problem).
- mixer: "x" (standard) or "warm_x" (Egger et al. 2021 warm-start mixer; requires initial_state "warm_start";
  He et al. 2023 found that aligning the initial state with the mixer ground state helps).
- warm_start_epsilon (0-0.5): clips the relaxed solution to [eps, 1-eps]; larger eps = less biased start.
- coupling_keep_fraction (0.1-1): keep only the strongest ZZ couplings in the phase separator (fewer CX gates;
  samples are still scored on the full objective).
- angle_init "linear_ramp" (annealing-like gamma up, beta down) or "constant"; ramp_dt sets the angle scale.
- optimizer "cobyla" | "nelder_mead" | "none" (fixed schedule, no classical loop); max_iter 10-300 (0 for none).
- cvar_alpha (0.02-1): CVaR fraction of best samples used as the training loss (1 = plain expectation).
Hard rule: two-qubit gates = 2 x kept couplings x layers must not exceed the budget.

Goal: maximise SUCCESS = probability that one measurement returns an affordable portfolio within 2 % (normalised)
of the exact optimum, averaged over the training dates. Fewer optimizer iterations and CX gates are better at equal
success. Propose diverse, testable designs; learn from the leaderboard. Return JSON matching the schema."""


def proposal_schema(m: int) -> dict:
    return {"type": "object",
            "properties": {"analysis": {"type": "string", "maxLength": 600},
                           "proposals": {"type": "array", "items": SPEC_SCHEMA, "minItems": m, "maxItems": m}},
            "required": ["analysis", "proposals"], "additionalProperties": False}


def problem_summary(problems: list[CompiledProblem], cx_budget: int, success_gap: float) -> dict:
    cp = problems[0]
    qs = []
    for p in problems:
        w = np.abs(p.pair_w)
        w = w / max(w.max(), 1e-12)
        top = np.sort(w)[::-1]
        qs.append({
            "coupling_abs_quantiles_q25_q50_q75_q90": np.round(np.quantile(w, [.25, .5, .75, .9]), 3).tolist(),
            "share_of_coupling_mass_in_top25pct_pairs": round(float(top[: len(top) // 4].sum() / top.sum()), 3),
            "max_field_over_max_coupling": round(float(np.abs(p.hz).max() / max(np.abs(p.pair_w).max(), 1e-12)), 3),
            "relaxed_solution_mean_distance_to_binary": round(float(np.minimum(p.relaxed, 1 - p.relaxed).mean()), 3),
            "feasible_fraction_of_bitstrings": round(float(p.land.feasible.mean()), 4),
            "random_guess_success_probability": round(uniform_reference(p, success_gap), 5),
        })
    enc = ("rounding: every stock starts at the floor of the continuous optimum; qubit k adds one board lot "
           "to register stock k (the integer-lot rounding decision)" if cp.inst.mode == "rounding" else
           "selection: qubit k = i*b + j adds 2^j position units of stock i (concentrated basket)")
    return {"n_qubits": cp.n, "register_stocks": len(cp.inst.register), "stocks_in_portfolio": cp.inst.n,
            "coupling_pairs": len(cp.pair_w), "two_qubit_gate_budget": cx_budget, "encoding": enc,
            "budget_note": "an affordability penalty couples all qubits; infeasible portfolios are never executed",
            "training_instances": qs}


@dataclass
class Evaluated:
    arm: str
    round: int
    spec: CircuitSpec
    errors: list[str]
    fitness: float
    metrics: dict = field(default_factory=dict)

    def row(self) -> dict:
        return {"arm": self.arm, "round": self.round, "fitness": self.fitness, "errors": self.errors,
                **{f"m_{k}": v for k, v in self.metrics.items()}, **{f"s_{k}": v for k, v in self.spec.to_dict().items()}}


class Evaluator:
    def __init__(self, problems: list[CompiledProblem], cx_budget: int, success_gap: float, shots: int, seed: int):
        self.problems, self.cx_budget, self.gap, self.shots, self.seed = problems, cx_budget, success_gap, shots, seed
        self._cache: dict[tuple, Evaluated] = {}

    def __call__(self, spec: CircuitSpec, arm: str, rnd: int) -> Evaluated:
        errs = verify(spec, self.problems[0].n, self.cx_budget)
        if errs:
            return Evaluated(arm, rnd, spec, errs, 0.0, {})
        if spec.key() in self._cache:
            e = self._cache[spec.key()]
            return Evaluated(arm, rnd, spec, [], e.fitness, dict(e.metrics))
        rs = [run_qaoa(p, spec, self.gap, self.shots, np.random.default_rng(self.seed + i))
              for i, p in enumerate(self.problems)]
        m = {"success_prob": float(np.mean([r.success_prob for r in rs])),
             "feasible_mass": float(np.mean([r.feasible_mass for r in rs])),
             "best_sample_gap": float(np.mean([min(r.best_sample_gap, 10) for r in rs])),
             "evaluations": float(np.mean([r.evaluations for r in rs])),
             "two_qubit_gates": rs[0].two_qubit_gates}
        e = Evaluated(arm, rnd, spec, [], m["success_prob"], m)
        self._cache[spec.key()] = e
        return e


def _leaderboard(history: list[Evaluated], k: int = 8) -> dict:
    ok = sorted([h for h in history if not h.errors], key=lambda h: -h.fitness)[:k]
    bad = [h for h in history if h.errors][-4:]
    fmt = lambda h: {"spec": {k2: v for k2, v in h.spec.to_dict().items() if k2 != "rationale"},
                     "success_prob": round(h.fitness, 4),
                     **{k2: round(v, 4) if isinstance(v, float) else v for k2, v in h.metrics.items() if k2 != "success_prob"}}
    return {"best_designs": [fmt(h) for h in ok],
            "rejected_designs": [{"spec": {k2: v for k2, v in h.spec.to_dict().items() if k2 != "rationale"},
                                  "reasons": h.errors} for h in bad]}


def search(arm: str, ev: Evaluator, rounds: int, m: int, seed: int, llm: LLMClient | None = None,
           summary: dict | None = None) -> list[Evaluated]:
    rng = np.random.default_rng(seed)
    history: list[Evaluated] = []
    if arm == "default":
        return [ev(DEFAULT_SPEC, arm, 0)]
    for r in range(rounds):
        if arm == "random":
            specs = [random_spec(rng) for _ in range(m)]
        elif arm == "evolve":
            if r == 0:
                specs = [DEFAULT_SPEC] + [random_spec(rng) for _ in range(m - 1)]
            else:
                parents = sorted([h for h in history if not h.errors], key=lambda h: -h.fitness)[:3]
                specs = [mutate(parents[i % len(parents)].spec, rng) for i in range(m)]
        elif arm == "llm":
            payload = {"round": r, "designs_requested": m, "problem": summary}
            if r > 0:
                payload["leaderboard"] = _leaderboard(history)
            req = make_request("circuit_architect", SYSTEM, payload, proposal_schema(m),
                               seed=seed + r, temperature=0.8, max_tokens=4096)
            rec = llm.generate([req])[0]
            props = (rec["parsed"] or {}).get("proposals", []) if rec["status"] == "ok" else []
            specs = []
            for p in props[:m]:
                try:
                    specs.append(CircuitSpec.from_dict(p))
                except TypeError:
                    specs.append(CircuitSpec(layers=-1, rationale="unparseable"))
            while len(specs) < m:   # missing proposals are charged as rejected designs
                specs.append(CircuitSpec(layers=-1, rationale="missing proposal"))
        else:
            raise ValueError(arm)
        history += [ev(s, arm, r) for s in specs]
    return history


def best(history: list[Evaluated]) -> Evaluated:
    ok = [h for h in history if not h.errors]
    return max(ok, key=lambda h: (round(h.fitness, 4), -h.metrics.get("two_qubit_gates", 0)))


def dump(history: list[Evaluated]) -> str:
    return json.dumps([h.row() for h in history])
