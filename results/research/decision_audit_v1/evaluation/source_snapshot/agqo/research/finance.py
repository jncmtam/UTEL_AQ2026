"""Support selection, convex allocation, certificates, and self-financing accounting.

Selection scores are explicit equal-weight proxies. Allocated objectives are
reported separately; a selector optimum is never presented as an allocation optimum.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from itertools import combinations
from time import perf_counter
import math
from types import MappingProxyType
import numpy as np
from scipy.optimize import brentq
from scipy.stats import spearmanr
from sklearn.covariance import LedoitWolf
from agqo.problem import Qubo
from agqo.repair.mandates import MandateSpec
from agqo.synthesis.profile import digest


@dataclass(frozen=True)
class FinancialSpec:
    tickers: tuple[str, ...]
    sectors: tuple[str, ...]
    returns: np.ndarray
    benchmark: np.ndarray
    previous_weights: np.ndarray
    k: int
    cutoff: str
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    sector_count_caps: dict[str, int] = field(default_factory=dict)
    sector_weight_caps: dict[str, float] = field(default_factory=dict)
    turnover_cap: float | None = None
    max_replacements: int | None = None
    minimum_weight: float = 0.02
    maximum_weight: float = 0.35
    cost_weight: float = 0.01
    cost_rate: float = 0.0005
    objective_kind: str = "tracking_cost"
    risk_aversion: float = 5.0
    mean_shrinkage: float = 0.5
    horizon: int = 21
    provenance: str = "synthetic_diagnostic"

    def __post_init__(self):
        for name in ("tickers", "sectors", "include", "exclude"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        for name in ("sector_count_caps", "sector_weight_caps"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        if len(set(self.include)) != len(self.include) or len(set(self.exclude)) != len(
            self.exclude
        ):
            raise ValueError("Repeated required/excluded security.")
        for name in ("returns", "benchmark", "previous_weights"):
            value = np.array(getattr(self, name), dtype=float, copy=True)
            if not np.isfinite(value).all():
                raise ValueError(f"{name} must contain finite numbers.")
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        if (
            len(set(self.tickers)) != self.n
            or len(self.sectors) != self.n
            or type(self.k) is not int
            or not 1 <= self.k <= self.n
        ):
            raise ValueError("Invalid security register or cardinality.")
        if (
            self.returns.ndim != 2
            or self.returns.shape[1] != self.n
            or len(self.returns) < 3
            or self.benchmark.shape != (len(self.returns),)
        ):
            raise ValueError("Return and benchmark dimensions disagree.")
        if (self.returns < -1).any() or (self.benchmark < -1).any():
            raise ValueError("Returns below -100% are invalid.")
        if (
            self.previous_weights.shape != (self.n,)
            or (self.previous_weights < 0).any()
            or self.previous_weights.sum() > 1 + 1e-9
        ):
            raise ValueError(
                "Previous risky weights must be nonnegative and sum to at most one."
            )
        if not set(self.include + self.exclude) <= set(self.tickers):
            raise ValueError("Unknown mandated security.")
        if not 0 < self.minimum_weight <= self.maximum_weight <= 1:
            raise ValueError("Invalid position bounds.")
        if (
            not all(
                np.isfinite(x)
                for x in (
                    self.cost_rate,
                    self.cost_weight,
                    self.risk_aversion,
                    self.mean_shrinkage,
                )
            )
            or not 0 <= self.cost_rate < 1
            or min(self.cost_weight, self.risk_aversion) < 0
            or not 0 <= self.mean_shrinkage <= 1
        ):
            raise ValueError("Invalid cost, risk, or shrinkage parameter.")
        if (
            self.objective_kind not in ("tracking_cost", "risk_return")
            or type(self.horizon) is not int
            or self.horizon < 1
        ):
            raise ValueError("Unsupported objective or horizon.")
        if self.turnover_cap is not None and (
            not np.isfinite(self.turnover_cap) or not 0 <= self.turnover_cap <= 1
        ):
            raise ValueError(
                "V3 turnover is one-way NAV turnover in [0,1], including cash."
            )
        if self.max_replacements is not None and (
            type(self.max_replacements) is not int
            or not 0 <= self.max_replacements <= self.n
        ):
            raise ValueError("Invalid replacement limit.")
        for sector, cap in self.sector_count_caps.items():
            if (
                sector not in self.sectors
                or type(cap) is not int
                or not 0 <= cap <= self.n
            ):
                raise ValueError("Invalid sector count cap.")
        for sector, cap in self.sector_weight_caps.items():
            if sector not in self.sectors or not np.isfinite(cap) or not 0 <= cap <= 1:
                raise ValueError("Invalid sector weight cap.")

    @property
    def n(self):
        return len(self.tickers)

    @property
    def cost_rates(self):
        return np.full(self.n, self.cost_rate)

    @property
    def effective_cost_weight(self):
        return self.cost_weight

    @property
    def mandate(self):
        # Adapter exposes only support constraints, never weight caps as count caps.
        return MandateSpec(
            "Verified structured mandate",
            k=self.k,
            include=self.include,
            exclude=self.exclude,
            status="ready",
            origin="financial-spec-v3",
        )

    def to_dict(self):
        output = {name: getattr(self, name) for name in self.__dataclass_fields__}
        for name in ("returns", "benchmark", "previous_weights"):
            output[name] = output[name].tolist()
        for name in ("sector_count_caps", "sector_weight_caps"):
            output[name] = dict(output[name])
        return {
            "version": "financial-spec-v3",
            "turnover_convention": "half_L1_including_cash",
            **output,
        }

    def fingerprint(self):
        return digest(self.to_dict())

    def bits(self, bits):
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("Expected N binary support indicators.")
        return x

    def weights(self, bits):
        return self.bits(bits) / self.k

    def quadratic(self):
        if self.objective_kind == "tracking_cost":
            return (
                self.returns.T @ self.returns / len(self.returns),
                -2 * self.returns.T @ self.benchmark / len(self.returns),
                float(np.mean(self.benchmark**2)),
            )
        covariance = LedoitWolf().fit(self.returns).covariance_
        mu = self.returns.mean(axis=0)
        mu = (1 - self.mean_shrinkage) * mu + self.mean_shrinkage * mu.mean()
        return self.horizon * self.risk_aversion * covariance, -self.horizon * mu, 0.0

    def objective_qubo(self):
        matrix, vector, offset = self.quadratic()
        matrix = matrix / self.k**2
        delta = np.abs(1 / self.k - self.previous_weights) - self.previous_weights
        linear = (
            np.diag(matrix)
            + vector / self.k
            + self.cost_weight * self.cost_rate * delta
        )
        return Qubo(
            linear,
            2 * np.triu(matrix, 1),
            offset + self.cost_weight * self.cost_rate * self.previous_weights.sum(),
        )

    def metrics_weights(self, weights):
        w = np.asarray(weights, dtype=float)
        matrix, vector, offset = self.quadratic()
        delta = np.abs(w - self.previous_weights)
        cash_delta = abs((1 - w.sum()) - (1 - self.previous_weights.sum()))
        cost = self.cost_rate * delta.sum()
        active = self.returns @ w - self.benchmark
        return {
            "objective": float(
                w @ matrix @ w + vector @ w + offset + self.cost_weight * cost
            ),
            "tracking_mse": float(np.mean(active**2)),
            "tracking_rmse": float(np.sqrt(np.mean(active**2))),
            "tracking_error_per_period": float(np.std(active, ddof=1)),
            "one_way_turnover": float((delta.sum() + cash_delta) / 2),
            "two_way_turnover": float(delta.sum() + cash_delta),
            "transaction_cost": float(cost),
            "number_of_trades": int(np.count_nonzero(delta > 1e-8)),
        }

    def score(self, bits):
        return self.metrics_weights(self.weights(bits))["objective"]

    def violations(self, bits):
        x = self.bits(bits)
        v = {}
        if x.sum() != self.k:
            v["cardinality"] = float(abs(x.sum() - self.k))
        for name in self.include:
            if not x[self.tickers.index(name)]:
                v["include:" + name] = 1
        for name in self.exclude:
            if x[self.tickers.index(name)]:
                v["exclude:" + name] = 1
        for sector, cap in self.sector_count_caps.items():
            excess = sum(x[i] for i, s in enumerate(self.sectors) if s == sector) - cap
            if excess > 0:
                v["sector_count:" + sector] = float(excess)
        if self.max_replacements is not None:
            excess = x[self.previous_weights <= 1e-10].sum() - self.max_replacements
            if excess > 0:
                v["replacements"] = float(excess)
        return v

    def feasible(self, bits):
        return not self.violations(bits)

    def violations_weights(self, w, target=True):
        w = np.asarray(w, dtype=float)
        if w.shape != (self.n,) or not np.isfinite(w).all():
            return {"invalid_weights": 1}
        v = self.violations((w > 1e-7).astype(int)) if target else {}
        if abs(w.sum() - 1) > 1e-7:
            v["budget"] = float(abs(w.sum() - 1))
        if (w < -1e-8).any():
            v["negative_weight"] = float(-w.min())
        active = w > 1e-7
        if (w > self.maximum_weight + 1e-7).any() or (
            w[active] < self.minimum_weight - 1e-7
        ).any():
            v["position_bounds"] = 1
        for sector, cap in self.sector_weight_caps.items():
            excess = sum(w[i] for i, s in enumerate(self.sectors) if s == sector) - cap
            if excess > 1e-7:
                v["sector_weight:" + sector] = float(excess)
        turnover = self.metrics_weights(w)["one_way_turnover"]
        if self.turnover_cap is not None and turnover > self.turnover_cap + 1e-7:
            v["turnover"] = turnover - self.turnover_cap
        return v


def diagnose(spec):
    errors = []
    if set(spec.include) & set(spec.exclude):
        errors.append("A security is both required and excluded.")
    if len(set(spec.include)) > spec.k or spec.n - len(set(spec.exclude)) < spec.k:
        errors.append("Cardinality conflicts with required/excluded securities.")
    if (
        spec.k * spec.minimum_weight > 1 + 1e-10
        or spec.k * spec.maximum_weight < 1 - 1e-10
    ):
        errors.append("Position bounds cannot fund a fully invested K-asset portfolio.")
    mandatory_exit = sum(
        spec.previous_weights[spec.tickers.index(t)] for t in set(spec.exclude)
    )
    if spec.turnover_cap is not None and mandatory_exit > spec.turnover_cap + 1e-10:
        errors.append(
            f"Mandatory exits require at least {mandatory_exit:.6f} one-way turnover; cap is {spec.turnover_cap:.6f}."
        )
    return {
        "status": "infeasible" if errors else "not_proven_infeasible",
        "reasons": errors,
        "mandatory_exit_turnover_lower_bound": float(mandatory_exit),
    }


def allocate(spec, bits):
    import cvxpy as cp

    start = perf_counter()
    x = spec.bits(bits)
    if not spec.feasible(x):
        return {
            "status": "infeasible",
            "feasible": False,
            "violations": spec.violations(x),
        }
    w = cp.Variable(spec.n)
    matrix, vector, offset = spec.quadratic()
    delta = cp.norm1(w - spec.previous_weights)
    constraints = [
        cp.sum(w) == 1,
        w >= spec.minimum_weight * x,
        w <= spec.maximum_weight * x,
    ]
    for sector, cap in spec.sector_weight_caps.items():
        constraints.append(
            cp.sum(w[[i for i, s in enumerate(spec.sectors) if s == sector]]) <= cap
        )
    if spec.turnover_cap is not None:
        constraints.append(
            (delta + 1 - spec.previous_weights.sum()) / 2 <= spec.turnover_cap
        )
    scale = max(
        np.linalg.norm(matrix, ord=2),
        np.max(np.abs(vector)),
        spec.cost_weight * spec.cost_rate,
        1e-8,
    )
    objective = (
        cp.quad_form(w, cp.psd_wrap(matrix))
        + vector @ w
        + offset
        + spec.cost_weight * spec.cost_rate * delta
    )
    problem = cp.Problem(cp.Minimize(objective / scale), constraints)
    try:
        problem.solve(
            solver="CLARABEL",
            max_iter=300,
            tol_gap_abs=1e-10,
            tol_feas=1e-10,
            tol_gap_rel=1e-10,
        )
    except cp.error.SolverError as exc:
        return {"status": "unknown", "feasible": False, "reason": str(exc)}
    if problem.status not in ("optimal", "optimal_inaccurate") or w.value is None:
        return {
            "status": "infeasible" if problem.status == "infeasible" else "unknown",
            "feasible": False,
            "solver_status": problem.status,
        }
    weights = np.asarray(w.value)
    weights[x == 0] = 0
    violations = spec.violations_weights(weights)
    return {
        "status": "optimal"
        if problem.status == "optimal" and not violations
        else "feasible"
        if not violations
        else "unknown",
        "feasible": not violations,
        "support": x.astype(int).tolist(),
        "weights": weights.tolist(),
        "violations": violations,
        **spec.metrics_weights(weights),
        "elapsed_seconds": perf_counter() - start,
        "solver": "CLARABEL",
        "selection_proxy_objective": spec.score(x),
        "support_changed": False,
    }


def audit_proxy(spec, max_supports=5000):
    if math.comb(spec.n, spec.k) > max_supports:
        return {"status": "unknown", "reason": "Support enumeration budget exceeded."}
    rows = []
    for selected in combinations(range(spec.n), spec.k):
        x = np.zeros(spec.n, dtype=int)
        x[list(selected)] = 1
        if not spec.feasible(x):
            continue
        allocation = allocate(spec, x)
        rows.append(
            {"bits": x.tolist(), "proxy": spec.score(x), "allocation": allocation}
        )
    valid = [r for r in rows if r["allocation"]["feasible"]]
    if not valid:
        return {
            "status": "infeasible"
            if all(r["allocation"]["status"] == "infeasible" for r in rows)
            else "unknown",
            "supports": rows,
        }
    proxy_best = min(rows, key=lambda r: r["proxy"])
    best = min(valid, key=lambda r: r["allocation"]["objective"])
    correlation = (
        spearmanr(
            [r["proxy"] for r in valid], [r["allocation"]["objective"] for r in valid]
        ).statistic
        if len(valid) > 2
        else float("nan")
    )
    complete = all(r["allocation"]["status"] in ("optimal", "infeasible") for r in rows)
    return {
        "status": "complete" if complete else "unknown",
        "supports": rows,
        "feasible_allocation_fraction": len(valid) / len(rows),
        "rank_correlation": float(correlation) if np.isfinite(correlation) else None,
        "best_allocated_objective": best["allocation"]["objective"],
        "best_allocated_bits": best["bits"],
        "proxy_optimum_allocation_feasible": proxy_best["allocation"]["feasible"],
        "proxy_optimum_allocation_regret": proxy_best["allocation"]["objective"]
        - best["allocation"]["objective"]
        if proxy_best["allocation"]["feasible"]
        else None,
    }


@dataclass
class Account:
    """Dollar holdings and cash; adjusted total-return mode never adds dividends twice."""

    holdings: np.ndarray
    cash: float = 0.0

    def __post_init__(self):
        self.holdings = np.array(self.holdings, dtype=float, copy=True)
        if (
            self.holdings.ndim != 1
            or not np.isfinite(self.holdings).all()
            or (self.holdings < 0).any()
            or not np.isfinite(self.cash)
            or self.cash < 0
            or self.nav <= 0
        ):
            raise ValueError(
                "Account requires finite nonnegative holdings and cash, and positive NAV."
            )

    @property
    def nav(self):
        return float(self.holdings.sum() + self.cash)

    def weights(self):
        if self.nav <= 0:
            raise ValueError("A bankrupt account has no normalized weights.")
        return self.holdings / self.nav

    def rebalance(self, target, rate):
        target = np.asarray(target, dtype=float)
        if (
            target.shape != self.holdings.shape
            or not np.isfinite(target).all()
            or (target < 0).any()
            or target.sum() > 1 + 1e-10
            or not 0 <= rate < 1
            or self.nav <= 0
        ):
            raise ValueError("Invalid self-financing order.")
        before = self.nav
        invested_nav = brentq(
            lambda v: v + rate * np.abs(target * v - self.holdings).sum() - before,
            0,
            before,
            xtol=1e-10,
        )
        trades = target * invested_nav - self.holdings
        fee = float(rate * np.abs(trades).sum())
        self.holdings = target * invested_nav
        self.cash = float((1 - target.sum()) * invested_nav)
        return {
            "nav_before": before,
            "nav_after": self.nav,
            "fee_dollars": fee,
            "trade_dollars": trades.tolist(),
            "self_financing_residual": self.nav + fee - before,
        }

    def advance_total_return(self, returns):
        returns = np.asarray(returns, dtype=float)
        if (
            returns.shape != self.holdings.shape
            or not np.isfinite(returns).all()
            or (returns < -1).any()
        ):
            raise ValueError("Invalid total returns.")
        before = self.nav
        self.holdings *= 1 + returns
        return self.nav / before - 1

    def apply_action(self, transfer, cash_per_dollar):
        """Audited raw-value event: map old dollar exposures to new assets and cash.

        Do not call this in adjusted-total-return mode. The caller supplies the
        event-date valuation map, not a guessed ticker substitution.
        """
        transfer, cash_per_dollar = np.asarray(transfer), np.asarray(cash_per_dollar)
        if (
            transfer.shape != (len(self.holdings), len(self.holdings))
            or cash_per_dollar.shape != self.holdings.shape
            or not np.isfinite(transfer).all()
            or not np.isfinite(cash_per_dollar).all()
            or (transfer < 0).any()
            or (cash_per_dollar < 0).any()
        ):
            raise ValueError("Invalid corporate-action map.")
        if not np.allclose(transfer.sum(axis=0) + cash_per_dollar, 1, atol=1e-9):
            raise ValueError("Event-date value must be conserved.")
        self.cash += float(cash_per_dollar @ self.holdings)
        self.holdings = transfer @ self.holdings


def joint_reference(spec, time_limit=30):
    """Full support-and-weight convex MIQP, solved by SCIP with explicit bounds."""
    from pyscipopt import Model, quicksum

    start = perf_counter()
    model = Model("AGQO full allocation reference")
    model.hideOutput()
    model.setRealParam("limits/time", float(time_limit))
    model.setRealParam("limits/gap", 0.0)
    x = [model.addVar(vtype="B", name=f"x{i}") for i in range(spec.n)]
    w = [
        model.addVar(lb=0, ub=spec.maximum_weight, name=f"w{i}") for i in range(spec.n)
    ]
    d = [model.addVar(lb=0, name=f"d{i}") for i in range(spec.n)]
    model.addCons(quicksum(x) == spec.k)
    model.addCons(quicksum(w) == 1)
    for i in range(spec.n):
        model.addCons(w[i] >= spec.minimum_weight * x[i])
        model.addCons(w[i] <= spec.maximum_weight * x[i])
        model.addCons(d[i] >= w[i] - float(spec.previous_weights[i]))
        model.addCons(d[i] >= float(spec.previous_weights[i]) - w[i])
    for t in spec.include:
        model.addCons(x[spec.tickers.index(t)] == 1)
    for t in spec.exclude:
        model.addCons(x[spec.tickers.index(t)] == 0)
    for sector, cap in spec.sector_count_caps.items():
        model.addCons(
            quicksum(x[i] for i, s in enumerate(spec.sectors) if s == sector) <= cap
        )
    for sector, cap in spec.sector_weight_caps.items():
        model.addCons(
            quicksum(w[i] for i, s in enumerate(spec.sectors) if s == sector) <= cap
        )
    if spec.max_replacements is not None:
        model.addCons(
            quicksum(x[i] for i in range(spec.n) if spec.previous_weights[i] <= 1e-10)
            <= spec.max_replacements
        )
    if spec.turnover_cap is not None:
        model.addCons(
            (quicksum(d) + 1 - float(spec.previous_weights.sum())) / 2
            <= spec.turnover_cap
        )
    matrix, vector, offset = spec.quadratic()
    scale = max(
        np.linalg.norm(matrix, ord=2),
        np.max(abs(vector)),
        spec.cost_rate * spec.cost_weight,
        1e-8,
    )
    expr = quicksum(
        float(matrix[i, j] / scale) * w[i] * w[j]
        for i in range(spec.n)
        for j in range(spec.n)
    )
    expr += (
        quicksum(float(vector[i] / scale) * w[i] for i in range(spec.n))
        + offset / scale
    )
    expr += spec.cost_weight * spec.cost_rate / scale * quicksum(d)
    epigraph = model.addVar(lb=-model.infinity(), name="objective")
    model.addCons(epigraph >= expr)
    model.setObjective(epigraph)
    model.optimize()
    status = str(model.getStatus())
    solution = model.getBestSol()
    dual = float(model.getDualbound()) * scale
    result = {
        "status": "optimal"
        if status == "optimal"
        else "infeasible"
        if status == "infeasible"
        else "unknown",
        "solver_status": status,
        "method": "joint_scip",
        "lower_bound": dual if abs(dual) < 1e15 else None,
        "elapsed_seconds": perf_counter() - start,
        "feasible": False,
    }
    if solution is not None:
        bits = np.array([round(model.getSolVal(solution, v)) for v in x])
        allocation = allocate(spec, bits)
        result.update(
            feasible=allocation["feasible"], allocation=allocation, bits=bits.tolist()
        )
        if status != "optimal" and allocation["feasible"]:
            result["status"] = "feasible"
    return result
