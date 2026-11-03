"""One immutable financial objective and full compliance checker for every solver."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import numpy as np

from .mandates import MandateSpec


@dataclass(frozen=True)
class ProblemInstance:
    instance_id: str
    tickers: tuple[str, ...]
    sectors: tuple[str, ...]
    returns: np.ndarray
    benchmark: np.ndarray
    previous_weights: np.ndarray
    mandate: MandateSpec
    cost_rates: np.ndarray
    cost_weight: float = 0.01
    provenance: str = "synthetic"
    cutoff: str = "unspecified"

    def __post_init__(self):
        n = len(self.tickers)
        if self.mandate.status != "ready":
            raise ValueError("Mandate chưa sẵn sàng: " + "; ".join(self.mandate.issues))
        if len(set(self.tickers)) != n or len(self.sectors) != n or type(self.k) is not int or not 1 <= self.k <= n:
            raise ValueError("Universe/ngành/K không hợp lệ.")
        for name in ("returns", "benchmark", "previous_weights", "cost_rates"):
            a = np.array(getattr(self, name), dtype=float, copy=True)
            if not np.isfinite(a).all():
                raise ValueError(name + " phải hữu hạn.")
            a.setflags(write=False)
            object.__setattr__(self, name, a)
        if self.returns.ndim != 2 or self.returns.shape[1] != n or self.returns.shape[0] < 2 or self.benchmark.shape != (self.returns.shape[0],):
            raise ValueError("Kích thước chuỗi lợi suất không khớp.")
        if (self.returns <= -1).any() or (self.benchmark <= -1).any():
            raise ValueError("Lợi suất phải lớn hơn -100%.")
        if self.previous_weights.shape != (n,) or (self.previous_weights < 0).any() or not np.isclose(self.previous_weights.sum(), 1):
            raise ValueError("Tỷ trọng trước giao dịch phải không âm và tổng bằng 1.")
        if self.cost_rates.shape != (n,) or (self.cost_rates < 0).any() or (self.cost_rates >= 1).any():
            raise ValueError("Chi phí mỗi chiều phải trong [0,1).")
        if isinstance(self.cost_weight, bool) or not np.isfinite(self.cost_weight) or self.cost_weight < 0:
            raise ValueError("Hệ số chi phí không hợp lệ.")
        if not set(self.mandate.include + self.mandate.exclude) <= set(self.tickers) or not set(self.mandate.sector_caps) <= set(self.sectors):
            raise ValueError("Mandate có tài sản/ngành ngoài universe.")
        if any(not np.isfinite(v) or not 0 <= v <= 1 for v in self.mandate.sector_caps.values()) or (self.mandate.turnover_cap is not None and (not np.isfinite(self.mandate.turnover_cap) or not 0 <= self.mandate.turnover_cap <= 2)):
            raise ValueError("Giới hạn ngành/turnover không hợp lệ.")
        if self.mandate.cost_weight is not None and (not np.isfinite(self.mandate.cost_weight) or self.mandate.cost_weight < 0):
            raise ValueError("Ưu tiên chi phí không hợp lệ.")

    @property
    def n(self):
        return len(self.tickers)

    @property
    def k(self):
        return self.mandate.k

    @property
    def effective_cost_weight(self):
        return self.cost_weight if self.mandate.cost_weight is None else self.mandate.cost_weight

    def bits(self, bits):
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("Nghiệm phải có đúng N bit.")
        return x

    def weights(self, bits):
        return self.bits(bits) / self.k

    def metrics_weights(self, weights):
        w = np.asarray(weights, dtype=float)
        delta = w - self.previous_weights
        active = self.returns @ w - self.benchmark
        loss = float(np.mean(active**2))
        cost = float(self.cost_rates @ np.abs(delta))
        return {"tracking_mse": loss, "tracking_rmse": float(np.sqrt(loss)),
                "tracking_error_per_period": float(np.std(active, ddof=1)),
                "two_way_turnover": float(np.abs(delta).sum()), "transaction_cost": cost,
                "objective": loss + self.effective_cost_weight * cost,
                "number_of_trades": int(np.count_nonzero(np.abs(delta) > 1e-10))}

    def score(self, bits):
        return self.metrics_weights(self.weights(bits))["objective"]

    def violations_weights(self, weights, target=True):
        w = np.asarray(weights, dtype=float)
        m, violations = self.mandate, {}
        if target:
            violations["cardinality"] = abs(int(np.count_nonzero(w > 1e-10)) - self.k)
        for ticker in m.include:
            violations["include:" + ticker] = float(w[self.tickers.index(ticker)] <= 1e-10)
        for ticker in m.exclude:
            violations["exclude:" + ticker] = float(w[self.tickers.index(ticker)])
        for sector, cap in m.sector_caps.items():
            exposure = sum(w[i] for i, s in enumerate(self.sectors) if s == sector)
            violations["sector:" + sector] = max(0.0, float(exposure - cap))
        if m.turnover_cap is not None:
            violations["turnover"] = max(0.0, float(np.abs(w - self.previous_weights).sum() - m.turnover_cap))
        return {k: v for k, v in violations.items() if v > 1e-9}

    def violations(self, bits):
        x = self.bits(bits)
        v = self.violations_weights(x / self.k)
        if int(x.sum()) != self.k:
            v["cardinality"] = float(abs(x.sum() - self.k))
        return v

    def feasible(self, bits):
        return not self.violations(bits)

    def fingerprint(self):
        payload = {"tickers": self.tickers, "sectors": self.sectors,
                   "returns": self.returns.tolist(), "benchmark": self.benchmark.tolist(),
                   "previous": self.previous_weights.tolist(), "rates": self.cost_rates.tolist(),
                   "k": self.k, "include": self.mandate.include, "exclude": self.mandate.exclude,
                   "caps": self.mandate.sector_caps, "turnover": self.mandate.turnover_cap,
                   "lambda": self.effective_cost_weight}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def objective_qubo(self):
        from agqo.problem import Qubo
        r, b, k = self.returns, self.benchmark, self.k
        gram = r.T @ r / len(r) / k**2
        linear = np.diag(gram) - 2 * (r.T @ b) / len(r) / k
        delta = np.abs(1 / k - self.previous_weights) - self.previous_weights
        linear += self.effective_cost_weight * self.cost_rates * delta
        return Qubo(linear, 2 * np.triu(gram, 1),
                    float(np.mean(b**2) + self.effective_cost_weight * (self.cost_rates @ self.previous_weights)))


def heldout_metrics(problem: ProblemInstance, weights, returns, benchmark):
    """Buy-and-hold within a period, with drift; transaction fee deducted once at entry."""
    r, b = np.asarray(returns), np.asarray(benchmark)
    if r.ndim != 2 or r.shape[1] != problem.n or b.shape != (len(r),) or len(r) < 2 or not np.isfinite(r).all() or not np.isfinite(b).all() or (r <= -1).any() or (b <= -1).any():
        raise ValueError("Dữ liệu ngoài mẫu không hợp lệ.")
    w = np.asarray(weights, dtype=float).copy()
    fee = problem.metrics_weights(w)["transaction_cost"]
    path = []
    for row in r:
        ret = float(w @ row)
        path.append(ret)
        w = w * (1 + row) / (1 + ret)
    net = np.asarray(path)
    net[0] = (1 - fee) * (1 + net[0]) - 1
    active = net - b
    return {"heldout_tracking_rmse": float(np.sqrt(np.mean(active**2))),
            "heldout_tracking_error_per_period": float(np.std(active, ddof=1)),
            "heldout_net_return": float(np.prod(1 + net) - 1),
            "benchmark_return": float(np.prod(1 + b) - 1), "exit_weights": w.tolist(),
            "net_returns": net.tolist(), "benchmark_returns": b.tolist()}
