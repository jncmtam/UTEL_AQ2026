"""Exact enumeration, HiGHS MILP linearization, and budgeted swap annealing."""
from __future__ import annotations

from itertools import combinations
from time import perf_counter
import math
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from .model import ProblemInstance


def result(problem, method, bits, status, start, **metadata):
    if bits is not None:
        bits = problem.bits(bits).astype(int)
        valid = problem.feasible(bits)
        metrics = problem.metrics_weights(bits / problem.k)
        violations = problem.violations(bits)
    else:
        valid, metrics, violations = False, {}, {}
    return {"method": method, "status": status, "bits": None if bits is None else bits.tolist(),
            "feasible": valid, "violations": violations, **metrics,
            "problem_hash": problem.fingerprint(), "elapsed_seconds": perf_counter() - start,
            "fallback_used": False, **metadata}


def exact_solve(problem: ProblemInstance, max_states=2_000_000, time_limit=30.0):
    start, best, score, count = perf_counter(), None, math.inf, 0
    if math.comb(problem.n, problem.k) > max_states:
        return result(problem, "exact", None, "unknown", start, evaluations=0, reason="enumeration_limit")
    for chosen in combinations(range(problem.n), problem.k):
        if perf_counter() - start > time_limit:
            return result(problem, "exact", best, "feasible" if best is not None else "unknown", start, evaluations=count, reason="time_limit")
        x = np.zeros(problem.n, dtype=int)
        x[list(chosen)] = 1
        count += 1
        if problem.feasible(x):
            value = problem.score(x)
            if value < score:
                best, score = x.copy(), value
    return result(problem, "exact", best, "optimal" if best is not None else "infeasible", start, evaluations=count,
                  lower_bound=None if best is None else score)


def milp_solve(problem: ProblemInstance, time_limit=30.0):
    """Binary pair-product reformulation: y_ij=x_i*x_j; no quadratic approximation."""
    start = perf_counter()
    q, n = problem.objective_qubo(), problem.n
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    size = n + len(pairs)
    c = np.r_[q.linear, [q.quadratic[i, j] for i, j in pairs]]
    rows, lows, highs = [], [], []

    def add(coefficients, low=-np.inf, high=np.inf):
        rows.append(coefficients); lows.append(low); highs.append(high)

    add({i: 1 for i in range(n)}, problem.k, problem.k)
    for ticker in problem.mandate.include:
        add({problem.tickers.index(ticker): 1}, 1, 1)
    for ticker in problem.mandate.exclude:
        add({problem.tickers.index(ticker): 1}, 0, 0)
    for sector, cap in problem.mandate.sector_caps.items():
        add({i: 1 / problem.k for i, s in enumerate(problem.sectors) if s == sector}, high=cap)
    if problem.mandate.turnover_cap is not None:
        delta = np.abs(1 / problem.k - problem.previous_weights) - problem.previous_weights
        add(dict(enumerate(delta)), high=problem.mandate.turnover_cap - problem.previous_weights.sum())
    for index, (i, j) in enumerate(pairs, n):
        add({index: 1, i: -1}, high=0)
        add({index: 1, j: -1}, high=0)
        add({index: 1, i: -1, j: -1}, low=-1)
    a = lil_matrix((len(rows), size))
    for row, coefficients in enumerate(rows):
        for col, value in coefficients.items():
            a[row, col] = value
    # Scale tiny return-squared coefficients to a stable optimization range.
    scale = max(float(np.max(np.abs(c))), 1e-12)
    answer = milp(c / scale, integrality=np.r_[np.ones(n), np.zeros(len(pairs))],
                  bounds=Bounds(np.zeros(size), np.ones(size)),
                  constraints=LinearConstraint(a.tocsr(), lows, highs),
                  options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    bits = None if answer.x is None else np.rint(answer.x[:n]).astype(int)
    if bits is not None and not problem.feasible(bits):
        bits = None
    status = "optimal" if answer.status == 0 and bits is not None else "infeasible" if answer.status == 2 else "feasible" if bits is not None else "unknown"
    bound = getattr(answer, "mip_dual_bound", None)
    return result(problem, "milp_highs", bits, status, start,
                  lower_bound=None if bound is None or not np.isfinite(bound) else float(bound * scale + q.offset),
                  mip_gap=None if bits is None else float(getattr(answer, "mip_gap", 0)),
                  solver_message=str(answer.message), formulation="exact_binary_pair_linearization")


def anneal_solve(problem: ProblemInstance, seed=11, evaluations=1000):
    start, rng = perf_counter(), np.random.default_rng(seed)
    x = np.zeros(problem.n, dtype=int)
    x[np.argsort(-problem.previous_weights, kind="stable")[:problem.k]] = 1
    best = x.copy() if problem.feasible(x) else None
    q = problem.objective_qubo()
    scale = max(float(np.abs(q.linear).sum() + np.abs(q.quadratic).sum()), 1e-12)

    def energy(candidate):
        v = problem.violations(candidate)
        return problem.score(candidate) / scale + (0 if not v else 2 + sum(v.values()))

    current = energy(x)
    for step in range(evaluations):
        y = x.copy()
        if problem.k < problem.n:
            y[rng.choice(np.flatnonzero(x))] = 0
            y[rng.choice(np.flatnonzero(x == 0))] = 1
        value = energy(y)
        temperature = max(0.002, 0.5 * (1 - step / max(evaluations, 1)))
        if value < current or rng.random() < np.exp(min(0, (current - value) / temperature)):
            x, current = y, value
        if problem.feasible(y) and (best is None or problem.score(y) < problem.score(best)):
            best = y.copy()
    return result(problem, "swap_annealing", best, "feasible" if best is not None else "unknown", start,
                  seed=seed, evaluations=evaluations)


def hold_result(problem):
    start = perf_counter()
    w = problem.previous_weights
    violations = problem.violations_weights(w)
    return {"method": "hold", "status": "feasible" if not violations else "violates_mandate", "bits": None,
            "weights": w.tolist(), "feasible": not violations, "violations": violations,
            **problem.metrics_weights(w), "problem_hash": problem.fingerprint(),
            "elapsed_seconds": perf_counter() - start, "fallback_used": False}
