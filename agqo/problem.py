"""Mô hình danh mục, QUBO, Ising và các đối chứng cổ điển."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass(frozen=True)
class PortfolioProblem:
    """Đầu vào chung để mọi bộ giải chấm đúng cùng một danh mục."""

    tickers: tuple[str, ...]
    mu: np.ndarray
    covariance: np.ndarray
    k: int = 6
    risk_aversion: float = 5.0
    previous_weights: np.ndarray | None = None
    transaction_costs: np.ndarray | None = None
    rebalances_per_year: int = 12

    def __post_init__(self) -> None:
        n = len(self.tickers)
        if n == 0 or self.mu.shape != (n,) or self.covariance.shape != (n, n):
            raise ValueError("Kích thước mã, lợi nhuận và hiệp phương sai không khớp.")
        if not 1 <= self.k <= n or not np.isfinite(self.risk_aversion) or self.risk_aversion < 0:
            raise ValueError("Cần 1 <= K <= N và hệ số ngại rủi ro không âm.")
        if not np.isfinite(self.mu).all() or not np.isfinite(self.covariance).all():
            raise ValueError("Lợi nhuận và hiệp phương sai phải hữu hạn.")
        if not np.allclose(self.covariance, self.covariance.T, atol=1e-10):
            raise ValueError("Ma trận hiệp phương sai phải đối xứng.")
        if np.linalg.eigvalsh(self.covariance).min() < -1e-9:
            raise ValueError("Ma trận hiệp phương sai phải bán xác định dương.")
        previous = (
            np.zeros(n, dtype=float)
            if self.previous_weights is None
            else np.asarray(self.previous_weights, dtype=float)
        )
        costs = (
            np.zeros(n, dtype=float)
            if self.transaction_costs is None
            else np.asarray(self.transaction_costs, dtype=float)
        )
        if previous.shape != (n,) or not np.isfinite(previous).all() or (previous < 0).any():
            raise ValueError("Tỷ trọng trước giao dịch phải là vector hữu hạn, không âm và có N phần tử.")
        if previous.sum() > 1 + 1e-8:
            raise ValueError("Tổng tỷ trọng trước giao dịch không được vượt quá 1.")
        if costs.shape != (n,) or not np.isfinite(costs).all() or (costs < 0).any():
            raise ValueError("Chi phí giao dịch phải là vector hữu hạn, không âm và có N phần tử.")
        if (costs >= 1).any():
            raise ValueError("Chi phí trên mỗi đồng giao dịch phải nhỏ hơn 100%.")
        if not isinstance(self.rebalances_per_year, (int, np.integer)) or self.rebalances_per_year < 1:
            raise ValueError("Số lần tái cân bằng năm hóa phải là số nguyên dương.")
        object.__setattr__(self, "rebalances_per_year", int(self.rebalances_per_year))
        object.__setattr__(self, "previous_weights", previous)
        object.__setattr__(self, "transaction_costs", costs)

    @property
    def n(self) -> int:
        return len(self.tickers)

    def score(self, bits: np.ndarray) -> float:
        """Tính mục tiêu năm hóa, gồm phí tái cân bằng dự kiến nếu có."""
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("Danh mục phải là chuỗi N bit.")
        target_weights = x / self.k
        annual_cost = self.rebalances_per_year * float(
            self.transaction_costs @ np.abs(target_weights - self.previous_weights)
        )
        return float(
            self.risk_aversion * (x @ self.covariance @ x) / self.k**2
            - (self.mu @ x) / self.k
            + annual_cost
        )

    def two_way_turnover(self, bits: np.ndarray) -> float:
        """Tổng giá trị mua và bán theo tỷ trọng danh mục."""
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("Danh mục phải là chuỗi N bit.")
        return float(np.abs(x / self.k - self.previous_weights).sum())

    def annual_transaction_cost(self, bits: np.ndarray) -> float:
        """Chi phí giao dịch năm hóa trong cùng đơn vị lợi nhuận với score."""
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("Danh mục phải là chuỗi N bit.")
        traded_weights = np.abs(x / self.k - self.previous_weights)
        return float(self.rebalances_per_year * (self.transaction_costs @ traded_weights))


@dataclass(frozen=True)
class Qubo:
    """Q(x)=offset + linear·x + tổng quadratic[i,j] x_i x_j, i<j."""

    linear: np.ndarray
    quadratic: np.ndarray
    offset: float = 0.0

    @property
    def n(self) -> int:
        return len(self.linear)

    def energy(self, bits: np.ndarray) -> float:
        x = np.asarray(bits, dtype=float)
        return float(self.offset + self.linear @ x + np.sum(self.quadratic * np.outer(x, x)))


@dataclass(frozen=True)
class Ising:
    """H=c + ΣhᵢZᵢ + ΣJᵢⱼZᵢZⱼ theo quy ước x=(1-Z)/2."""

    constant: float
    fields: np.ndarray
    couplings: np.ndarray


def build_qubo(problem: PortfolioProblem, mixer: str = "X", penalty: float | None = None) -> Qubo:
    """Đổi cùng hàm mục tiêu sang QUBO; chỉ bộ trộn X cần phạt sai số lượng mã."""
    n, k = problem.n, problem.k
    linear = problem.risk_aversion * np.diag(problem.covariance) / k**2 - problem.mu / k
    quadratic = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            quadratic[i, j] = 2 * problem.risk_aversion * problem.covariance[i, j] / k**2

    # Với x_i ∈ {0,1}, |x_i/K - w_i| = w_i + (|1/K-w_i|-w_i)x_i.
    # Hằng số và hệ số tuyến tính này mã hóa chi phí đổi danh mục chính xác.
    cost_scale = float(problem.rebalances_per_year)
    previous = problem.previous_weights
    rates = problem.transaction_costs
    offset = cost_scale * float(rates @ previous)
    linear += cost_scale * rates * (np.abs(1 / k - previous) - previous)

    if mixer.upper() == "XY":
        return Qubo(linear=linear, quadratic=quadratic, offset=offset)
    if mixer.upper() != "X":
        raise ValueError("Bộ trộn hợp lệ là X hoặc XY.")

    # Hạng phạt lớn hơn toàn bộ độ dao động khả thi để nghiệm sai K không thắng.
    if penalty is None:
        feasible = []
        for chosen in combinations(range(n), k):
            bits = np.zeros(n, dtype=np.int8)
            bits[list(chosen)] = 1
            feasible.append(problem.score(bits))
        span = max(feasible) - min(feasible)
        penalty = max(span, 1e-12) * 1.01
    if penalty <= 0:
        raise ValueError("Hệ số phạt phải dương.")
    linear = linear + penalty * (1 - 2 * k)
    for i in range(n):
        for j in range(i + 1, n):
            quadratic[i, j] += 2 * penalty
    return Qubo(linear=linear, quadratic=quadratic, offset=offset + penalty * k**2)


def to_ising(qubo: Qubo) -> Ising:
    """Chuyển QUBO sang Ising, giữ hằng số để kiểm chứng năng lượng tuyệt đối."""
    n = qubo.n
    fields = -0.5 * qubo.linear.copy()
    constant = qubo.offset + 0.5 * qubo.linear.sum()
    couplings = qubo.quadratic.copy()
    for i in range(n):
        for j in range(i + 1, n):
            b = qubo.quadratic[i, j]
            couplings[i, j] = b / 4
            fields[i] -= b / 4
            fields[j] -= b / 4
            constant += b / 4
    return Ising(float(constant), fields, couplings)


def exact_solve(problem: PortfolioProblem) -> tuple[np.ndarray, float]:
    """Duyệt mọi tổ hợp khả thi; chuẩn nghiệm toàn cục cho N nhỏ/VN30, K=6."""
    if problem.n > 30 or problem.k > 6:
        raise ValueError("Duyệt chính xác giới hạn ở N<=30 và K<=6 theo proposal.")
    best_bits, best_value = None, np.inf
    for chosen in combinations(range(problem.n), problem.k):
        bits = np.zeros(problem.n, dtype=np.int8)
        bits[list(chosen)] = 1
        value = problem.score(bits)
        if value < best_value:
            best_bits, best_value = bits, value
    assert best_bits is not None
    return best_bits, float(best_value)


def greedy_solve(problem: PortfolioProblem) -> tuple[np.ndarray, float]:
    """Đối chứng tham lam: mỗi bước thêm mã làm giảm mục tiêu nhiều nhất."""
    bits = np.zeros(problem.n, dtype=np.int8)
    for _ in range(problem.k):
        choices = []
        for i in np.flatnonzero(bits == 0):
            candidate = bits.copy()
            candidate[i] = 1
            choices.append((problem.score(candidate), i))
        bits[min(choices)[1]] = 1
    return bits, problem.score(bits)


def anneal_solve(
    problem: PortfolioProblem, seed: int = 11, steps: int = 20_000
) -> tuple[np.ndarray, float]:
    """Tôi luyện trên không gian khả thi bằng phép đổi một mã đang chọn/một mã bỏ."""
    if problem.k == problem.n:
        bits = np.ones(problem.n, dtype=np.int8)
        return bits, problem.score(bits)
    rng = np.random.Generator(np.random.PCG64(seed))
    bits = np.zeros(problem.n, dtype=np.int8)
    bits[rng.choice(problem.n, problem.k, replace=False)] = 1
    current = problem.score(bits)
    best_bits, best_value = bits.copy(), current
    neighbor_deltas = []
    for selected in np.flatnonzero(bits):
        for rejected in np.flatnonzero(bits == 0):
            candidate = bits.copy()
            candidate[selected], candidate[rejected] = 0, 1
            neighbor_deltas.append(problem.score(candidate) - current)
    scale = max(float(np.std(neighbor_deltas)), float(np.mean(np.abs(neighbor_deltas))), 1e-4)
    for step in range(steps):
        chosen = rng.choice(np.flatnonzero(bits))
        rejected = rng.choice(np.flatnonzero(bits == 0))
        candidate = bits.copy()
        candidate[chosen], candidate[rejected] = 0, 1
        value = problem.score(candidate)
        temperature = scale * (1 - step / max(steps, 1)) + scale * 0.01
        if value < current or rng.random() < np.exp((current - value) / temperature):
            bits, current = candidate, value
        if current < best_value:
            best_bits, best_value = bits.copy(), current
    return best_bits, float(best_value)


def synthetic_problem(seed: int, n: int = 16, k: int = 6) -> PortfolioProblem:
    """Sinh mẫu độc lập theo proposal: 3 nhân tố, biến động riêng và lợi nhuận giới hạn."""
    if not 1 <= n <= 16:
        raise ValueError("Mẫu tổng hợp quy định N từ 1 đến 16.")
    rng = np.random.Generator(np.random.PCG64(seed))
    loading = rng.normal(0.0, 0.05, size=(16, 3))
    specific_vol = rng.uniform(0.15, 0.35, size=16)
    mu = rng.uniform(-0.05, 0.20, size=16)
    covariance = loading @ loading.T + np.diag(specific_vol**2)
    return PortfolioProblem(
        tickers=tuple(f"SYN{i:02d}" for i in range(n)),
        mu=mu[:n],
        covariance=covariance[:n, :n],
        k=k,
    )

