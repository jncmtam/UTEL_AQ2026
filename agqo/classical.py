"""Classical baselines: shortlist rules, exact discrete optimum, annealing, QP + rounding."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .portfolio import Instance, Landscape


# ---------------------------------------------------------------- shortlists
def continuous_min_te(cov: np.ndarray, cov_b: np.ndarray, budget: float,
                      mu: np.ndarray | None = None, eta: float = 0.0,
                      w_prev: np.ndarray | None = None, gamma: float = 0.0) -> np.ndarray:
    """min 252 (w'Sw - 2 w'c) - eta mu'w + gamma ||w - w_prev||^2, w >= 0, sum w <= budget."""
    n = len(cov_b)
    mu = np.zeros(n) if mu is None else mu
    w_prev = np.zeros(n) if w_prev is None else w_prev
    P = 252 * cov + gamma * np.eye(n)
    q = -2 * 252 * cov_b - eta * mu - 2 * gamma * w_prev
    f = lambda w: w @ P @ w + q @ w
    g = lambda w: 2 * P @ w + q
    cons = [{"type": "ineq", "fun": lambda w: budget - w.sum(), "jac": lambda w: -np.ones(n)}]
    w0 = np.full(n, budget / n)
    res = minimize(f, w0, jac=g, method="SLSQP", bounds=[(0, budget)] * n, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-12})
    return np.clip(res.x, 0, None)


def te_of(w: np.ndarray, cov: np.ndarray, cov_b: np.ndarray, var_b: float) -> float:
    return float(np.sqrt(max(252 * (w @ cov @ w - 2 * w @ cov_b + var_b), 0)))


def greedy_te_shortlist(cov: np.ndarray, cov_b: np.ndarray, var_b: float, k: int, budget: float) -> list[int]:
    """Forward selection: repeatedly add the stock that most lowers the best continuous TE."""
    chosen: list[int] = []
    rest = list(range(len(cov_b)))
    for _ in range(k):
        best, best_te = None, np.inf
        for j in rest:
            s = chosen + [j]
            w = continuous_min_te(cov[np.ix_(s, s)], cov_b[s], budget)
            te = te_of(w, cov[np.ix_(s, s)], cov_b[s], var_b)
            if te < best_te:
                best, best_te = j, te
        chosen.append(best)
        rest.remove(best)
    return chosen


def liquidity_shortlist(liquidity: np.ndarray, k: int) -> list[int]:
    return list(np.argsort(-liquidity)[:k])


# ---------------------------------------------------------------- solvers on the QUBO
def exact_optimum(land: Landscape) -> int:
    return land.opt_index


def simulated_annealing(inst: Instance, land: Landscape, sweeps: int = 200, restarts: int = 8,
                        seed: int = 0) -> tuple[int, int]:
    """Metropolis annealing on the penalised QUBO; returns (best feasible index, energy evaluations)."""
    rng = np.random.default_rng(seed)
    Q, h, _ = inst.qubo
    n = inst.n_qubits
    scale = np.abs(Q).max() + np.abs(h).max()
    best_idx, best_obj, evals = None, np.inf, 0
    pow2 = 2 ** np.arange(n)
    for _ in range(restarts):
        x = rng.integers(0, 2, n)
        for t in np.linspace(1.0, 0.002, sweeps):
            for k in rng.permutation(n):
                d = (1 - 2 * x[k]) * (h[k] + 2 * Q[k] @ x)
                evals += 1
                if d < 0 or rng.random() < np.exp(-d / (t * scale)):
                    x[k] ^= 1
            idx = int(x @ pow2)
            if land.feasible[idx] and land.objective[idx] < best_obj:
                best_idx, best_obj = idx, land.objective[idx]
    return best_idx, evals          # None if annealing never found an affordable portfolio


def round_to_lots(w: np.ndarray, prices: np.ndarray, nav: float, lot: int, max_invest: float = 0.985) -> np.ndarray:
    """Practitioner rounding: nearest whole lot, then trim the most over-rounded lots until affordable."""
    target = w * nav / prices
    shares = np.round(target / lot) * lot
    while (shares * prices).sum() > max_invest * nav:
        excess = (shares - target) * prices
        excess[shares <= 0] = -np.inf
        shares[int(np.argmax(excess))] -= lot
    return shares
