"""Kiểm chứng chéo mạch Qiskit bằng Qiskit Aer trên máy cục bộ."""

from __future__ import annotations

import numpy as np

from .problem import PortfolioProblem, build_qubo
from .qpu import build_parameterized_circuit
from .simulator import statevector


def crosscheck_aer(
    problem: PortfolioProblem,
    mixer: str = "XY",
    seed: int = 11,
    shots: int = 512,
    device: str = "CPU",
) -> dict:
    """Đối chiếu xác suất trạng thái NumPy với số đo từ mạch Aer, không gọi dịch vụ mạng."""
    try:
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise RuntimeError("Cài máy mô phỏng mạch bằng pip install -e .[simulator].") from exc
    rng = np.random.Generator(np.random.PCG64(seed))
    mixer = mixer.upper()
    initial_bits = None
    initial_index = 0
    if mixer == "XY":
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
        )
        initial_bits = np.zeros(problem.n, dtype=np.int8)
        initial_bits[: problem.k] = 1
        initial_index = int(sum(int(bit) << i for i, bit in enumerate(initial_bits)))
    else:
        ordered_problem = problem
    angles = rng.uniform(-np.pi, np.pi, size=2)
    qubo = build_qubo(ordered_problem, mixer=mixer)
    circuit, parameters = build_parameterized_circuit(qubo, mixer, 1, initial_bits)
    bound = circuit.assign_parameters(dict(zip(parameters, angles)))
    backend = AerSimulator(method="statevector", device=device)
    counts = backend.run(bound, shots=shots, seed_simulator=seed).result().get_counts()

    # Đảo chuỗi đo của Qiskit về chỉ số tài sản trước khi so phân bố xác suất.
    observed = np.zeros(1 << problem.n, dtype=float)
    for bitstring, count in counts.items():
        index = sum(int(bit) << i for i, bit in enumerate(bitstring.replace(" ", "")[::-1]))
        observed[index] += count / shots
    ideal = np.abs(statevector(qubo, mixer, angles, 1, initial_index)) ** 2
    exact_feasible = sum(
        probability for index, probability in enumerate(ideal) if index.bit_count() == problem.k
    )
    sampled_feasible = sum(
        count for bitstring, count in counts.items()
        if bitstring.replace(" ", "").count("1") == problem.k
    ) / shots
    return {
        "mixer": mixer,
        "seed": seed,
        "shots": shots,
        "device": device,
        "ideal_feasible_probability": float(exact_feasible),
        "sampled_feasible_probability": float(sampled_feasible),
        "total_variation_distance": float(0.5 * np.abs(observed - ideal).sum()),
        "angles": [float(value) for value in angles],
    }
