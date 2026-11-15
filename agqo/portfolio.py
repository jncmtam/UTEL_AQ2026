"""Integer-lot rebalancing problem and its exact QUBO compilation.

Decision: whole board lots per stock. Shares = base + B x for a bit vector x, so the
portfolio weights are affine in the bits, w = w_base + A x (see `Instance`).

Objective (annualised):
    F(w) = 252 * Var(R w - r_index) + gamma * ||w - w_prev||^2
Every term is quadratic in w, and w is affine in x, so the QUBO is the *exact*
discrete objective, not an equal-weight proxy. A budget penalty
lambda * (sum w - target)^2 steers the circuit towards affordable portfolios;
feasibility (cash >= 0 after fees and tax, plus the investor's caps) is always
checked exactly.

The investor's mandate can remove stocks and add caps, but no AI component edits
a coefficient here: this module is the single owner of the Hamiltonian.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
from scipy.optimize import minimize

from .config import MarketRules, ProblemConfig


@dataclass
class Instance:
    """One rebalancing decision as a binary problem.

    Shares of stock j = base_shares_j + sum_k x_k * bit_lots_k * lot   over bits k with bit_stock_k = j.
    base = nearest lot of the continuous optimum (floor for register stocks); qubit k adds one lot
    to register stock k: the hard integer part of a small account.
    """

    date: str
    tickers: list[str]                 # all stocks that can be held (N)
    prices: np.ndarray                 # price per share at execution (N)
    nav: float
    cov: np.ndarray                    # daily covariance of returns (N x N)
    cov_b: np.ndarray                  # daily covariance(stocks, index) (N)
    var_b: float                       # daily index variance
    prev_shares: np.ndarray            # current holding (N)
    other_value: float                 # value of holdings outside `tickers` (sold)
    cash: float
    base_shares: np.ndarray            # fixed part of the decision (N)
    bit_stock: np.ndarray              # stock index of each qubit (Q)
    bit_lots: np.ndarray               # lots added by each qubit (Q)
    cfg: ProblemConfig
    rules: MarketRules
    invest_target: float = 0.98
    caps: list = field(default_factory=list)   # [(mask over tickers, max weight)] from the mandate
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.tickers)

    @property
    def n_qubits(self) -> int:
        return len(self.bit_stock)

    @cached_property
    def register(self) -> list[str]:
        return [self.tickers[j] for j in dict.fromkeys(self.bit_stock.tolist())]

    @cached_property
    def B(self) -> np.ndarray:
        """Bits -> shares (Q x N)."""
        b = np.zeros((self.n_qubits, self.n))
        b[np.arange(self.n_qubits), self.bit_stock] = self.bit_lots * self.rules.lot_size
        return b

    @cached_property
    def A(self) -> np.ndarray:
        """Bits -> weights (N x Q)."""
        return (self.B * self.prices / self.nav).T

    @cached_property
    def w_base(self) -> np.ndarray:
        return self.base_shares * self.prices / self.nav

    @cached_property
    def w_prev(self) -> np.ndarray:
        return self.prev_shares * self.prices / self.nav

    def shares(self, x: np.ndarray) -> np.ndarray:
        return self.base_shares + np.atleast_2d(x) @ self.B

    def weights(self, x: np.ndarray) -> np.ndarray:
        return self.w_base + np.atleast_2d(x) @ self.A.T

    # ---------- objective in weight space ----------
    @cached_property
    def quad_w(self) -> tuple[np.ndarray, np.ndarray, float]:
        """F(w) + penalty = w'Mw + m'w + c (penalty included)."""
        c = self.cfg
        t = self.invest_target
        M = 252 * self.cov + c.turnover_weight * np.eye(self.n) + c.budget_penalty * np.ones((self.n, self.n))
        m = -2 * 252 * self.cov_b - 2 * c.turnover_weight * self.w_prev - 2 * c.budget_penalty * t * np.ones(self.n)
        const = 252 * self.var_b + c.turnover_weight * self.w_prev @ self.w_prev + c.budget_penalty * t ** 2
        return M, m, const

    def true_objective_w(self, w: np.ndarray) -> np.ndarray:
        """Objective without the budget penalty (what the decision is judged on)."""
        w = np.atleast_2d(w)
        c = self.cfg
        te2 = 252 * (np.einsum("ki,ij,kj->k", w, self.cov, w) - 2 * w @ self.cov_b + self.var_b)
        turn = c.turnover_weight * ((w - self.w_prev) ** 2).sum(1)
        return te2 + turn

    def tracking_error(self, w: np.ndarray) -> np.ndarray:
        w = np.atleast_2d(w)
        te2 = 252 * (np.einsum("ki,ij,kj->k", w, self.cov, w) - 2 * w @ self.cov_b + self.var_b)
        return np.sqrt(np.maximum(te2, 0))

    # ---------- QUBO ----------
    @cached_property
    def qubo(self) -> tuple[np.ndarray, np.ndarray, float]:
        """E(x) = x'Qx + h'x + const with Q symmetric, zero diagonal (binary x)."""
        M, m, const = self.quad_w
        A, w0 = self.A, self.w_base
        Qf = A.T @ M @ A
        h = A.T @ (2 * M @ w0 + m) + np.diag(Qf)       # x_k^2 = x_k
        Q = Qf - np.diag(np.diag(Qf))
        return Q, h, float(w0 @ M @ w0 + m @ w0 + const)

    def qubo_energy(self, x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(x).astype(float)
        Q, h, c = self.qubo
        return np.einsum("ki,ij,kj->k", x, Q, x) + x @ h + c

    # ---------- exact accounting ----------
    def cash_after(self, x: np.ndarray) -> np.ndarray:
        r = self.rules
        new = self.shares(x)
        delta = (new - self.prev_shares) * self.prices
        buys = np.clip(delta, 0, None).sum(-1)
        sells = np.clip(-delta, 0, None).sum(-1) + self.other_value
        fees = r.commission * (buys + sells) + r.sell_tax * sells
        return self.cash + self.other_value + (self.prev_shares * self.prices).sum() - (new * self.prices).sum(-1) - fees

    def feasible(self, x: np.ndarray) -> np.ndarray:
        ok = self.cash_after(x) >= 0
        if self.caps:
            W = self.weights(x)
            for mask, cap in self.caps:
                ok &= W[:, mask].sum(1) <= cap + 1e-9
        return ok

    def ising(self) -> tuple[np.ndarray, np.ndarray, float]:
        """x = (1 - z)/2 -> E = sum_{i<j} J_ij z_i z_j + sum h_i z_i + c (J symmetric, used once per pair)."""
        Q, h, c = self.qubo
        J = Q / 2.0
        hz = -h / 2.0 - Q.sum(1) / 2.0
        cz = c + h.sum() / 2.0 + Q.sum() / 4.0
        return J, hz, cz


def all_bitstrings(n: int) -> np.ndarray:
    k = np.arange(2 ** n, dtype=np.int64)
    return ((k[:, None] >> np.arange(n)) & 1).astype(np.int8)


@dataclass
class Landscape:
    """Exhaustive table of every bitstring: the classical ground truth for metrics."""

    energy: np.ndarray          # QUBO energy (with penalty)
    objective: np.ndarray       # true objective (no penalty)
    feasible: np.ndarray
    opt_index: int
    opt_value: float
    median_feasible: float

    def gap(self, idx: np.ndarray | None = None) -> np.ndarray:
        """Normalised gap: 0 = exact optimum, 1 = median feasible portfolio, inf = infeasible."""
        obj = self.objective if idx is None else self.objective[idx]
        feas = self.feasible if idx is None else self.feasible[idx]
        g = (obj - self.opt_value) / max(self.median_feasible - self.opt_value, 1e-12)
        return np.where(feas, g, np.inf)


def landscape(inst: Instance) -> Landscape:
    X = all_bitstrings(inst.n_qubits)
    W = inst.weights(X)
    energy = inst.qubo_energy(X)
    obj = inst.true_objective_w(W)
    feas = inst.feasible(X)
    if not feas.any():
        raise ValueError("No affordable portfolio in the encoding.")
    fo = np.where(feas, obj, np.inf)
    k = int(np.argmin(fo))
    return Landscape(energy, obj, feas, k, float(obj[k]), float(np.median(obj[feas])))


def relaxed_solution(inst: Instance) -> np.ndarray:
    """Continuous relaxation x in [0,1]^n of the (convex) QUBO, used for warm starts."""
    M, m, _ = inst.quad_w
    A = inst.A
    P = A.T @ M @ A
    q = A.T @ (2 * M @ inst.w_base + m)
    f = lambda x: x @ P @ x + q @ x
    g = lambda x: 2 * P @ x + q
    res = minimize(f, np.full(inst.n_qubits, 0.5), jac=g, method="L-BFGS-B",
                   bounds=[(0, 1)] * inst.n_qubits)
    return res.x
