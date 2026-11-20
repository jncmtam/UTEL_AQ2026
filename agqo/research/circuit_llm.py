"""V3.2 circuit-design experiment (protocol §3b): the LLM proposes structured QAOA candidates, code validates
and scores them with a deterministic evaluator on Modal CPU, and a second round sees the first round's scores.

Control: random search over the same component space with the same budget (16 evaluated candidates, 3 seeds).
"""

from __future__ import annotations

import json

import numpy as np

from ..llm.client import make_request
from ..quantum.spec import ANGLE_INITS, BOUNDS, INITS, MIXERS, OPTIMIZERS, SCALES, CircuitSpec, verify

PROMPT_VERSION = "circuit-v3.2-2026-11-20"
CX_BUDGET = 1500
EVAL_BUDGET = 60            # circuit evaluations per instance, including the final one
N_CANDIDATES = 8

SYSTEM = """You design quantum circuits for a binary optimisation problem and are scored by a deterministic simulator.

Problem. A small investor buys whole lots (100 shares) of VN30 stocks to track the VN30 index. A classical solver
fixes most lots; n <= 16 binary decisions remain, x_k = 1 means "buy one more lot of stock k". The cost is a QUBO
E(x) = x'Qx + h'x + c that is exactly the annualised tracking error squared plus a small turnover term plus a
budget penalty. Its Ising form is H = sum_{i<j} J_ij Z_i Z_j + sum_i h_i Z_i. Couplings are dense (all pairs),
mostly positive (stocks substitute for each other), and their strength is concentrated: a few pairs carry most of
sum J^2. A continuous relaxation x* in [0,1]^n is available before any circuit runs; it already points to good
solutions on many qubits (warm-start confidence is typically 0.4-0.7). Some bit strings overspend the cash and are
infeasible; the budget penalty pushes them up in energy but does not remove them.

Objective. Maximise the mean, over 24 design instances (2023 data; account sizes 20, 100 and 500 million VND), of
the success probability: the probability that one measurement returns a feasible bit string whose true cost is
within 5% of the optimum (normalised gap <= 0.05; the gap is 0 at the optimum and 1 at the median feasible
portfolio). Ties: fewer two-qubit gates.

Allowed components (QAOA family; the simulator supports nothing else):
- initial_state: "uniform" (|+>^n) or "warm_start" (R_y(theta_k)|0> with sin^2(theta_k/2) = x*_k clipped to
  [warm_start_epsilon, 1 - warm_start_epsilon]).
- mixer: "x" (exp(-i beta X) on every qubit) or "warm_x" (the warm-start mixer of Egger et al. 2021, whose ground
  state is the warm-start state; requires initial_state "warm_start").
- layers p: 1..8.
- coupling pruning: coupling_mass in [0, 1] keeps the fewest strongest ZZ terms covering that share of sum J^2
  (0 disables it and coupling_keep_fraction in [0.1, 1] keeps that share of pairs, strongest first).
- hamiltonian_scale: "max" (divide H by its largest coefficient) or "rms" (divide by the RMS of the coefficients).
- angle_init: "linear_ramp" (gamma_k rises to ramp_dt, beta_k falls from ramp_dbeta; a discretised anneal) or
  "constant" (gamma = ramp_dt/2, beta = ramp_dbeta/2). ramp_dt in [0.05, 2], ramp_dbeta in [0, 2]
  (0 means use ramp_dt).
- optimizer: "none" (use the initial angles), "cobyla" or "nelder_mead" on CVaR_alpha of the full QUBO energy,
  with max_iter steps (cvar_alpha in [0.02, 1]).
- warm_start_epsilon in [0, 0.5].

Budgets (a candidate that breaks one is rejected without being run):
- two-qubit gates = 2 x kept ZZ pairs x layers <= 1500. A 16-qubit instance has 120 pairs, so without pruning
  p <= 6; with coupling_mass < 1 deeper circuits fit.
- circuit evaluations per instance <= 60: optimizer "none" uses 1, an optimiser uses max_iter + 1, so max_iter <= 59.
- if optimizer is "none", max_iter must be 0; otherwise max_iter >= 10.

Return JSON with exactly {n} candidates. Make them different from each other so that their scores teach you
something; give each a one-sentence rationale in English."""

ROUND2 = """Scores of your first {n} candidates on the 24 design instances (mean success probability, feasible
probability mass, circuit evaluations, two-qubit gates; rejected candidates show the reason):

{table}

Propose {n} new candidates that you expect to score higher. You may refine the best ones or test a new idea.
Return JSON with exactly {n} candidates."""


def schema(n: int = N_CANDIDATES) -> dict:
    num = lambda lo, hi: {"type": "number", "minimum": lo, "maximum": hi}
    cand = {"type": "object", "properties": {
        "initial_state": {"type": "string", "enum": list(INITS)},
        "mixer": {"type": "string", "enum": list(MIXERS)},
        "layers": {"type": "integer", "minimum": 1, "maximum": 8},
        "coupling_mass": num(0.0, 1.0), "coupling_keep_fraction": num(0.1, 1.0),
        "hamiltonian_scale": {"type": "string", "enum": list(SCALES)},
        "angle_init": {"type": "string", "enum": list(ANGLE_INITS)},
        "ramp_dt": num(0.05, 2.0), "ramp_dbeta": num(0.0, 2.0),
        "optimizer": {"type": "string", "enum": list(OPTIMIZERS)},
        "max_iter": {"type": "integer", "minimum": 0, "maximum": 300},
        "cvar_alpha": num(0.02, 1.0), "warm_start_epsilon": num(0.0, 0.5),
        "rationale_en": {"type": "string", "maxLength": 300}},
        "required": ["initial_state", "mixer", "layers", "coupling_mass", "coupling_keep_fraction", "hamiltonian_scale",
                     "angle_init", "ramp_dt", "ramp_dbeta", "optimizer", "max_iter", "cvar_alpha", "warm_start_epsilon",
                     "rationale_en"],
        "additionalProperties": False}
    return {"type": "object", "properties": {"candidates": {"type": "array", "items": cand, "minItems": n, "maxItems": n}},
            "required": ["candidates"], "additionalProperties": False}


def request(round_: int, history: list[dict] | None = None, seed: int = 0) -> dict:
    user = f"Round {round_}: propose {N_CANDIDATES} candidates."
    if round_ > 1:
        user = ROUND2.format(n=N_CANDIDATES, table=json.dumps(history, indent=1))
    return make_request(f"circuit_designer_r{round_}", SYSTEM.replace("{n}", str(N_CANDIDATES)), user, schema(), seed=seed,
                        temperature=0.4, max_tokens=4000)


def validate(c: dict, n_qubits: int = 16) -> tuple[CircuitSpec | None, list[str]]:
    """Schema-valid JSON -> CircuitSpec, or the reasons it is rejected before any simulation."""
    d = {k: v for k, v in c.items() if k != "rationale_en"}
    try:
        spec = CircuitSpec.from_dict(d | {"rationale": c.get("rationale_en", "")})
    except TypeError as e:
        return None, [f"malformed: {e}"]
    errs = verify(spec, n_qubits, CX_BUDGET)
    evals = 1 if spec.optimizer == "none" else spec.max_iter + 1
    if evals > EVAL_BUDGET:
        errs.append(f"{evals} circuit evaluations exceed the budget of {EVAL_BUDGET}")
    return (None if errs else spec), errs


def random_candidate(rng: np.random.Generator) -> CircuitSpec:
    """Uniform draw from the same component space and budgets as the LLM (rejection-sampled until valid)."""
    while True:
        init = str(rng.choice(INITS))
        mixer = "warm_x" if (init == "warm_start" and rng.random() < 0.5) else "x"
        opt = str(rng.choice(OPTIMIZERS))
        mass = float(np.round(rng.uniform(0, 1), 3)) if rng.random() < 0.5 else 0.0
        spec = CircuitSpec(layers=int(rng.integers(1, 9)), initial_state=init, mixer=mixer,
                           warm_start_epsilon=float(np.round(rng.uniform(0, 0.5), 3)),
                           coupling_keep_fraction=float(np.round(rng.uniform(0.1, 1.0), 3)), coupling_mass=mass,
                           hamiltonian_scale=str(rng.choice(SCALES)), angle_init=str(rng.choice(ANGLE_INITS)),
                           ramp_dt=float(np.round(rng.uniform(0.05, 2.0), 3)), ramp_dbeta=float(np.round(rng.uniform(0, 2.0), 3)),
                           optimizer=opt, max_iter=0 if opt == "none" else int(rng.integers(10, EVAL_BUDGET)),
                           cvar_alpha=float(np.round(rng.uniform(0.02, 1.0), 3)), rationale="random search")
        if not verify(spec, 16, CX_BUDGET):
            return spec


def design_instances(md) -> list[dict]:
    from .instances import split_dates

    return [{"split": "calibration", "date": str(d.date()), "capital_vnd": c, "constraint": "none"}
            for d in split_dates(md, "calibration") for c in (20e6, 100e6, 500e6)]


def summarise(rows: list[dict], names: list[str]) -> dict[str, dict]:
    """Mean metrics per spec over the design instances; a spec rejected on any instance is rejected."""
    out = {}
    for name in names:
        rs = [r for r in rows if r.get("spec") == name]
        errs = sorted({e for r in rs for e in r.get("errors", [])})
        ok = [r for r in rs if not r.get("errors")]
        if errs or not ok:
            out[name] = {"rejected": errs or ["not evaluated"]}
            continue
        out[name] = {"mean_success": float(np.mean([r["success_prob"] for r in ok])),
                     "feasible_mass": float(np.mean([r["feasible_mass"] for r in ok])),
                     "evaluations": float(np.mean([r["evaluations"] for r in ok])),
                     "two_qubit_gates": int(max(r["two_qubit_gates"] for r in ok)),
                     "seconds": float(np.mean([r["seconds"] for r in ok])), "instances": len(ok)}
    return out
