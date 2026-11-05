"""Máy mô phỏng véc-tơ trạng thái nhỏ, độc lập với QPU và có thể chạy trên CPU."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter

import numpy as np
from scipy.optimize import minimize

from .problem import PortfolioProblem, Qubo, build_qubo


@dataclass(frozen=True)
class QaoaResult:
    mixer: str
    mixer_layout: str
    depth: int
    seed: int
    n: int
    k: int
    risk_aversion: float
    previous_weights: tuple[float, ...]
    transaction_cost_rates: tuple[float, ...]
    rebalances_per_year: int
    evaluations: int
    objective_estimate: float
    best_feasible_score: float | None
    sampled_feasible_probability: float
    ideal_feasible_probability: float
    shots_per_evaluation: int
    mixer_edge_count: int
    logical_cost_two_qubit_gate_count: int
    logical_mixer_two_qubit_gate_count: int
    best_bits: tuple[int, ...] | None
    angles: tuple[float, ...]
    elapsed_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


def _basis_energies(qubo: Qubo) -> np.ndarray:
    """Tính trước năng lượng mọi chuỗi bit để mỗi lần gọi bộ tối ưu chỉ còn phép nhân."""
    states = np.arange(1 << qubo.n, dtype=np.uint64)
    bits = ((states[:, None] >> np.arange(qubo.n, dtype=np.uint64)) & 1).astype(float)
    return (
        qubo.offset
        + bits @ qubo.linear
        + np.einsum("bi,ij,bj->b", bits, qubo.quadratic, bits, optimize=True)
    )


def _mix_x(state: np.ndarray, n: int, beta: float) -> None:
    """Áp dụng tuần tự exp(-i β Xᵢ), tương đương cổng RX(2β) trên mọi qubit."""
    cosine, sine = np.cos(beta), -1j * np.sin(beta)
    indexes = np.arange(state.size, dtype=np.uint64)
    for q in range(n):
        mask = 1 << q
        lower = (indexes & mask) == 0
        left = indexes[lower]
        right = left | mask
        a, b = state[left].copy(), state[right].copy()
        state[left], state[right] = cosine * a + sine * b, sine * a + cosine * b


def mixer_edges_for_problem(
    covariance: np.ndarray, layout: str
) -> tuple[tuple[int, int], ...]:
    """Tạo đồ thị bộ trộn XY; đồ thị tương quan luôn liên thông để phủ tập khả thi."""
    n = covariance.shape[0]
    layout = layout.lower()
    if layout == "single":
        return ()
    if layout == "ring":
        return tuple((i, (i + 1) % n) for i in range(n))
    if layout == "linear":
        return tuple((i, i + 1) for i in range(n - 1))
    if layout == "complete":
        return tuple((i, j) for i in range(n) for j in range(i + 1, n))
    if layout != "correlation":
        raise ValueError("Bố trí bộ trộn hợp lệ: single, ring, linear, complete hoặc correlation.")
    scale = np.sqrt(np.maximum(np.diag(covariance), 1e-18))
    correlation = covariance / np.outer(scale, scale)
    edges = {tuple(sorted((i, (i + 1) % n))) for i in range(n)}
    # Mỗi mã nối thêm với hai mã đồng biến mạnh nhất; vòng bảo đảm tính liên thông.
    for i in range(n):
        order = np.argsort(-np.abs(correlation[i]))
        added = 0
        for j in order:
            if i == j:
                continue
            edges.add(tuple(sorted((i, int(j)))))
            added += 1
            if added == 2:
                break
    return tuple(sorted(edges))


def _mix_xy(state: np.ndarray, n: int, beta: float, edges: tuple[tuple[int, int], ...]) -> None:
    """Tích Trotter bậc nhất trên đồ thị; mỗi cạnh bảo toàn số bit 1."""
    indexes = np.arange(state.size, dtype=np.uint64)
    cosine, sine = np.cos(2 * beta), -1j * np.sin(2 * beta)
    for i, j in edges:
        mi, mj = 1 << i, 1 << j
        swap = mi | mj
        active = (((indexes & mi) == 0) & ((indexes & mj) != 0))
        left, right = indexes[active], indexes[active] ^ swap
        a, b = state[left].copy(), state[right].copy()
        state[left], state[right] = cosine * a + sine * b, sine * a + cosine * b


def statevector(
    qubo: Qubo,
    mixer: str,
    angles: np.ndarray,
    depth: int,
    initial_index: int,
    energies: np.ndarray | None = None,
    mixer_layout: str = "ring",
    mixer_edges: tuple[tuple[int, int], ...] | None = None,
) -> np.ndarray:
    """Tạo trạng thái QAOA p lớp theo đúng thứ tự cost rồi mixer của proposal."""
    n, size = qubo.n, 1 << qubo.n
    energies = _basis_energies(qubo) if energies is None else energies
    if mixer == "X":
        state = np.full(size, 1 / np.sqrt(size), dtype=np.complex128)
    else:
        if mixer_edges is not None:
            edges = mixer_edges
        elif mixer_layout == "correlation":
            edges = mixer_edges_for_problem(np.eye(n), "ring")
        else:
            edges = mixer_edges_for_problem(np.eye(n), mixer_layout)
        state = np.zeros(size, dtype=np.complex128)
        state[initial_index] = 1.0
    for layer in range(depth):
        beta, gamma = angles[layer], angles[depth + layer]
        state *= np.exp(-1j * gamma * energies)
        if mixer == "X":
            _mix_x(state, n, beta)
        else:
            _mix_xy(state, n, beta, edges)
    return state


def optimize_qaoa(
    problem: PortfolioProblem,
    mixer: str = "X",
    depth: int = 1,
    seed: int = 11,
    max_evaluations: int = 50,
    shots: int = 512,
    mixer_layout: str = "ring",
    analytic_objective: bool = False,
) -> QaoaResult:
    """Tối ưu góc bằng COBYLA; số lần gọi mục tiêu không vượt ngân sách đã khóa."""
    mixer = mixer.upper()
    if mixer not in {"X", "XY"} or depth < 1 or max_evaluations < 1 or shots < 1:
        raise ValueError("Cần mixer X/XY, p>=1, số lần đánh giá và số shot dương.")
    if mixer == "X" and mixer_layout != "single":
        mixer_layout = "single"
    if mixer == "XY" and mixer_layout not in {"ring", "linear", "complete", "correlation"}:
        raise ValueError("XY cần một bố trí ring, linear, complete hoặc correlation.")
    if problem.n > 20:
        raise ValueError("Máy mô phỏng véc-tơ trạng thái này dành cho N<=20.")
    if mixer == "XY" and problem.n < 3:
        raise ValueError("Vòng XY cần ít nhất ba qubit.")
    rng = np.random.Generator(np.random.PCG64(seed))
    if mixer == "XY":
        # Mỗi seed xáo thứ tự tài sản; vòng XY vì thế cũng đổi liên kết giữa các mã.
        asset_order = rng.permutation(problem.n)
        ordered_problem = PortfolioProblem(
            tuple(problem.tickers[i] for i in asset_order),
            problem.mu[asset_order],
            problem.covariance[np.ix_(asset_order, asset_order)],
            k=problem.k,
            risk_aversion=problem.risk_aversion,
            previous_weights=problem.previous_weights[asset_order],
            transaction_costs=problem.transaction_costs[asset_order],
            rebalances_per_year=problem.rebalances_per_year,
            outside_previous_weight=problem.outside_previous_weight,
            outside_transaction_cost_rate=problem.outside_transaction_cost_rate,
        )
        initial_index = (1 << problem.k) - 1
    else:
        asset_order = np.arange(problem.n)
        ordered_problem = problem
        initial_index = 0
    qubo = build_qubo(ordered_problem, mixer=mixer)
    energies = _basis_energies(qubo)
    edges = mixer_edges_for_problem(ordered_problem.covariance, mixer_layout)
    start = perf_counter()
    calls = 0

    def objective(angles: np.ndarray) -> float:
        nonlocal calls
        calls += 1
        state = statevector(
            qubo, mixer, angles, depth, initial_index, energies,
            mixer_layout=mixer_layout, mixer_edges=edges,
        )
        probabilities = np.abs(state) ** 2
        if analytic_objective:
            return float(probabilities @ energies)
        # Lấy mẫu hữu hạn mô phỏng sai số đo khi tối ưu góc.
        samples = rng.choice(len(state), size=shots, p=probabilities)
        return float(np.mean(energies[samples]))

    initial_angles = rng.uniform(-np.pi, np.pi, size=2 * depth)
    result = minimize(
        objective,
        initial_angles,
        method="COBYLA",
        options={"maxiter": max_evaluations, "rhobeg": 0.5, "tol": 1e-3},
    )
    final_state = statevector(
        qubo, mixer, result.x, depth, initial_index, energies,
        mixer_layout=mixer_layout, mixer_edges=edges,
    )
    probabilities = np.abs(final_state) ** 2
    samples = rng.choice(len(probabilities), size=shots, p=probabilities)
    ideal_feasible_probability = float(
        sum(probabilities[i] for i in range(len(probabilities)) if int(i).bit_count() == problem.k)
    )
    feasible = [i for i in samples if int(i).bit_count() == problem.k]
    best_bits, best_score = None, None
    for index in feasible:
        bits = np.fromiter(((int(index) >> i) & 1 for i in range(problem.n)), dtype=np.int8)
        original_bits = np.zeros(problem.n, dtype=np.int8)
        original_bits[asset_order] = bits
        score = problem.score(original_bits)
        if best_score is None or score < best_score:
            best_bits, best_score = original_bits, score
    return QaoaResult(
        mixer=mixer,
        mixer_layout=mixer_layout,
        depth=depth,
        seed=seed,
        n=problem.n,
        k=problem.k,
        risk_aversion=problem.risk_aversion,
        previous_weights=tuple(float(x) for x in problem.previous_weights),
        transaction_cost_rates=tuple(float(x) for x in problem.transaction_costs),
        rebalances_per_year=problem.rebalances_per_year,
        evaluations=calls,
        objective_estimate=float(result.fun),
        best_feasible_score=None if best_score is None else float(best_score),
        sampled_feasible_probability=float(len(feasible) / shots),
        ideal_feasible_probability=ideal_feasible_probability,
        shots_per_evaluation=shots,
        mixer_edge_count=len(edges),
        logical_cost_two_qubit_gate_count=int(
            depth * np.count_nonzero(np.triu(np.abs(qubo.quadratic) > 1e-14, k=1))
        ),
        logical_mixer_two_qubit_gate_count=(
            int(depth * 2 * len(edges)) if mixer == "XY" else 0
        ),
        best_bits=None if best_bits is None else tuple(int(x) for x in best_bits),
        angles=tuple(float(x) for x in result.x),
        elapsed_seconds=perf_counter() - start,
    )
