"""Worker bodies that Modal containers run (imported inside modal_research.py functions).

They simulate circuits, so they must only be called from a Modal container.
"""

from __future__ import annotations

import time

import numpy as np

from .instances import build, extended_features, load_v3_config

_STATE: dict = {}


def _ctx():
    if not _STATE:
        from ..data import MarketData
        from ..quantum.design import schedule_grid

        ec = load_v3_config()
        _STATE.update(md=MarketData.load(), ec=ec, grid=schedule_grid(ec.design), uni={})
    return _STATE


def schedule_rows(specs: list[dict]) -> list[dict]:
    """Success of every grid schedule (no optimiser) on each instance + features + cheap baselines."""
    from ..quantum.design import _row_success
    from ..quantum.simulator import CompiledProblem, uniform_reference, warm_start_only

    c = _ctx()
    ec, grid = c["ec"], c["grid"]
    out = []
    for s in specs:
        t0 = time.time()
        try:
            inst, land = build(c["md"], ec, s, c["uni"])
            if inst.n_qubits < 2:
                out.append(s | {"error": f"{inst.n_qubits} qubits"})
                continue
            cp = CompiledProblem(inst, land)
            t1 = time.time()
            row = _row_success((cp, grid, ec.problem.success_gap, ec.design.cx_budget))
            t_sim = time.time() - t1
            gap = land.gap()
            warm = {eps: warm_start_only(cp, eps, ec.problem.success_gap, 64, np.random.default_rng(0)).success_prob
                    for eps in sorted(set(grid.epsilon))}
            cx = [2 * len(cp.phase_terms(_spec(r))[1]) * int(r["layers"]) for r in grid.to_dict("records")]
            out.append(s | {"features": extended_features(cp, s), "success": row.tolist(), "cx": cx,
                            "n_qubits": int(cp.n), "uniform_success": uniform_reference(cp, ec.problem.success_gap),
                            "warm_success": {str(k): v for k, v in warm.items()},
                            "near_optimal_states": int((np.isfinite(gap) & (gap <= ec.problem.success_gap)).sum()),
                            "feasible_fraction": float(land.feasible.mean()), "sim_seconds": t_sim,
                            "seconds": time.time() - t0})
        except Exception as e:                                # recorded, never hidden
            out.append(s | {"error": f"{type(e).__name__}: {e}"})
    return out


def _spec(row):
    from ..quantum.design import spec_of

    return spec_of(row)


def evaluate_specs(job: dict) -> list[dict]:
    """Run each CircuitSpec (dict) on each instance spec: QAOA with the spec's own optimiser and budget."""
    from ..quantum.simulator import CompiledProblem, run_qaoa
    from ..quantum.spec import CircuitSpec, verify

    c = _ctx()
    ec = c["ec"]
    out = []
    for s in job["instances"]:
        try:
            inst, land = build(c["md"], ec, s, c["uni"])
            cp = CompiledProblem(inst, land)
        except Exception as e:
            out.append(s | {"error": f"{type(e).__name__}: {e}"})
            continue
        for name, sd in job["specs"].items():
            spec = CircuitSpec.from_dict(sd)
            errs = verify(spec, cp.n, ec.design.cx_budget)
            if not errs and 2 * len(cp.phase_terms(spec)[1]) * spec.layers > ec.design.cx_budget:
                errs = [f"compiled two-qubit gates exceed {ec.design.cx_budget}"]
            if errs:
                out.append(s | {"spec": name, "errors": errs})
                continue
            t0 = time.time()
            r = run_qaoa(cp, spec, ec.problem.success_gap, job.get("shots", 512),
                         np.random.default_rng(job.get("seed", 7)))
            out.append(s | {"spec": name, "errors": [], "success_prob": r.success_prob, "feasible_mass": r.feasible_mass,
                            "best_sample_gap": r.best_sample_gap if np.isfinite(r.best_sample_gap) else None,
                            "evaluations": r.evaluations, "two_qubit_gates": r.two_qubit_gates,
                            "seconds": time.time() - t0})
    return out
