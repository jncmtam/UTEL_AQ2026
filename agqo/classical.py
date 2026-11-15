"""Classical baselines: continuous QP, exact discrete optimum, simulated annealing, practitioner rounding."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .portfolio import Instance, Landscape


# ---------------------------------------------------------------- continuous optimum
def continuous_min_te(cov: np.ndarray, cov_b: np.ndarray, budget: float, w_prev: np.ndarray | None = None,
                      gamma: float = 0.0, caps: list | None = None) -> np.ndarray:
    """min 252 (w'Sw - 2 w'c) + gamma ||w - w_prev||^2  s.t.  w >= 0, sum w <= budget, sum(w[mask]) <= cap."""
    n = len(cov_b)
    w_prev = np.zeros(n) if w_prev is None else w_prev
    P = 252 * cov + gamma * np.eye(n)
    q = -2 * 252 * cov_b - 2 * gamma * w_prev
    f = lambda w: w @ P @ w + q @ w
    g = lambda w: 2 * P @ w + q
    cons = [{"type": "ineq", "fun": lambda w: budget - w.sum(), "jac": lambda w: -np.ones(n)}]
    for mask, cap in caps or []:
        mf = mask.astype(float)
        cons.append({"type": "ineq", "fun": lambda w, mf=mf, cap=cap: cap - mf @ w, "jac": lambda w, mf=mf: -mf})
    w0 = np.full(n, min(budget / n, min([c / max(m.sum(), 1) for m, c in caps or []] or [1.0])))
    res = minimize(f, w0, jac=g, method="SLSQP", bounds=[(0, budget)] * n, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-12})
    return np.clip(res.x, 0, None)


# ---------------------------------------------------------------- solvers on the QUBO
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


def round_to_lots(w: np.ndarray, prices: np.ndarray, nav: float, lot: int, max_invest: float = 0.985,
                  caps: list | None = None) -> np.ndarray:
    """Practitioner rounding: nearest whole lot, then trim the most over-rounded lots until affordable
    and within the investor's caps."""
    target = w * nav / prices
    shares = np.round(target / lot) * lot

    def violated() -> bool:
        wv = shares * prices / nav
        return (shares * prices).sum() > max_invest * nav or any(wv[m].sum() > c + 1e-9 for m, c in caps or [])

    while violated():
        excess = (shares - target) * prices
        excess[shares <= 0] = -np.inf
        shares[int(np.argmax(excess))] -= lot
    return shares
