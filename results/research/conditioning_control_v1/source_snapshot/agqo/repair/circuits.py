"""Validated circuit grammar and finite-shot QAOA over an explicit diagonal oracle.

Hard sector/turnover constraints generally are not a quadratic polynomial without
ancillas. This prototype uses an exponentially materialized diagonal phase table,
not a fictitious ancilla-free QUBO. Its construction cost is explicitly reported.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
import numpy as np
from scipy.optimize import minimize

from agqo.simulator import _mix_x, _mix_xy, mixer_edges_for_problem
from .solvers import result


@dataclass(frozen=True)
class CircuitSpec:
    mixer: str = "XY"
    topology: str = "ring"
    depth: int = 1
    initialization: str = "previous"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, obj):
        if not isinstance(obj, dict) or set(obj) != {"mixer", "topology", "depth", "initialization"}:
            raise ValueError("CircuitSpec không khớp schema.")
        value = cls(**obj)
        if value.mixer not in {"X", "XY"} or type(value.depth) is not int or not 1 <= value.depth <= 2:
            raise ValueError("Mạch chỉ hỗ trợ mixer X/XY và p=1/2.")
        if value.topology not in {"single", "ring", "complete"} or value.initialization not in {"previous", "random"}:
            raise ValueError("Topology/khởi tạo ngoài grammar.")
        if (value.mixer == "X") != (value.topology == "single"):
            raise ValueError("X dùng single; XY dùng ring/complete.")
        return value


CATALOG = tuple(CircuitSpec("XY", topology, depth, "previous") for topology in ("ring", "complete") for depth in (1, 2))


def rule_spec(problem):
    constrained = bool(problem.mandate.sector_caps or problem.mandate.turnover_cap is not None)
    return CircuitSpec("XY", "ring", 2 if constrained else 1, "previous")


def compile_diagonal(problem, max_qubits=12):
    start = perf_counter()
    if problem.n > max_qubits:
        raise ValueError(f"Exact diagonal prototype giới hạn N<={max_qubits}; không tự thu hẹp universe.")
    indices = np.arange(1 << problem.n, dtype=np.uint64)
    bits = ((indices[:, None] >> np.arange(problem.n, dtype=np.uint64)) & 1).astype(np.int8)
    q = problem.objective_qubo()
    objective = q.offset + bits @ q.linear + np.einsum("bi,ij,bj->b", bits, q.quadratic, bits)
    feasible = np.asarray([problem.feasible(x) for x in bits])
    span = max(float(np.ptp(objective)), 1e-12)
    energies = (objective - objective.min()) / span + 2.0 * (~feasible)
    return {"bits": bits, "objective": objective, "feasible": feasible, "energies": energies,
            "seconds": perf_counter() - start, "states": len(bits), "scale": span,
            "encoding": "explicit_diagonal_hard_barrier_not_qubo",
            "limitation": "Exponential classical table construction; no speedup or scalable hardware claim."}


def initial_bits(problem, spec, seed):
    x = np.zeros(problem.n, dtype=np.int8)
    if spec.initialization == "previous":
        x[np.argsort(-problem.previous_weights, kind="stable")[:problem.k]] = 1
    else:
        x[np.random.default_rng(seed).choice(problem.n, problem.k, replace=False)] = 1
    return x


def simulate(problem, spec, angles, compiled, seed=11):
    size = len(compiled["energies"])
    if spec.mixer == "X":
        state = np.full(size, 1 / np.sqrt(size), dtype=complex)
    else:
        state = np.zeros(size, dtype=complex)
        index = sum(int(v) << i for i, v in enumerate(initial_bits(problem, spec, seed)))
        state[index] = 1
    edges = mixer_edges_for_problem(np.eye(problem.n), spec.topology) if spec.mixer == "XY" else ()
    edges = tuple(dict.fromkeys(tuple(sorted(edge)) for edge in edges if edge[0] != edge[1]))
    for layer in range(spec.depth):
        state *= np.exp(-1j * angles[spec.depth + layer] * compiled["energies"])
        if spec.mixer == "X":
            _mix_x(state, problem.n, angles[layer])
        else:
            _mix_xy(state, problem.n, angles[layer], edges)
    return state


def qiskit_circuit(problem, spec, angles, compiled, seed=11):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import DiagonalGate
    qc = QuantumCircuit(problem.n)
    if spec.mixer == "X":
        qc.h(range(problem.n))
    else:
        for i, v in enumerate(initial_bits(problem, spec, seed)):
            if v:
                qc.x(i)
    edges = mixer_edges_for_problem(np.eye(problem.n), spec.topology) if spec.mixer == "XY" else ()
    edges = tuple(dict.fromkeys(tuple(sorted(edge)) for edge in edges if edge[0] != edge[1]))
    for layer in range(spec.depth):
        qc.append(DiagonalGate(np.exp(-1j * angles[spec.depth + layer] * compiled["energies"])), range(problem.n))
        if spec.mixer == "X":
            qc.rx(2 * angles[layer], range(problem.n))
        else:
            for i, j in edges:
                qc.rxx(2 * angles[layer], i, j)
                qc.ryy(2 * angles[layer], i, j)
    return qc


def run_qaoa(problem, spec=CircuitSpec(), seed=11, evaluations=40, shots=256, export_circuit=False):
    spec = CircuitSpec.from_dict(spec.to_dict())
    if type(evaluations) is not int or evaluations < 1 or type(shots) is not int or shots < 1:
        raise ValueError("Ngân sách evaluations/shots phải dương.")
    start, rng = perf_counter(), np.random.default_rng(seed)
    compiled = compile_diagonal(problem)
    calls = 0
    initial = rng.uniform(-np.pi, np.pi, size=2 * spec.depth)

    def objective(angles):
        nonlocal calls
        calls += 1
        probabilities = np.abs(simulate(problem, spec, angles, compiled, seed))**2
        samples = rng.choice(len(probabilities), shots, p=probabilities / probabilities.sum())
        return float(compiled["energies"][samples].mean())

    # COBYLA enforces a minimum call count internally; a wrapper enforces our actual cap.
    best_angles, best_energy = initial.copy(), float("inf")

    class BudgetExhausted(Exception):
        pass

    def bounded(angles):
        nonlocal best_angles, best_energy
        if calls >= evaluations:
            raise BudgetExhausted
        energy = objective(angles)
        if energy < best_energy:
            best_angles, best_energy = angles.copy(), energy
        return energy

    try:
        minimize(bounded, initial, method="COBYLA", options={"maxiter": max(evaluations, 2 * spec.depth + 2), "rhobeg": 0.5})
    except BudgetExhausted:
        pass
    probabilities = np.abs(simulate(problem, spec, best_angles, compiled, seed))**2
    samples = rng.choice(len(probabilities), shots, p=probabilities / probabilities.sum())
    valid = samples[compiled["feasible"][samples]]
    index = None if not len(valid) else int(valid[np.argmin(compiled["objective"][valid])])
    bits = None if index is None else compiled["bits"][index]
    record = result(problem, "qaoa", bits, "feasible" if bits is not None else "unknown", start,
                    seed=seed, circuit_spec=spec.to_dict(), angles=best_angles.tolist(),
                    evaluations=calls, shots_per_evaluation=shots, total_shots=(calls + 1) * shots,
                    sampled_feasible_probability=len(valid) / shots,
                    ideal_feasible_probability=float(probabilities @ compiled["feasible"]),
                    cardinality_only_preserved_by_mixer=spec.mixer == "XY",
                    initialization_feasible=problem.feasible(initial_bits(problem, spec, seed)) if spec.mixer == "XY" else None,
                    oracle={k: v for k, v in compiled.items() if k not in {"bits", "objective", "feasible", "energies"}})
    if export_circuit:
        from qiskit import qasm3, transpile
        qc = qiskit_circuit(problem, spec, best_angles, compiled, seed)
        circuit = transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1)
        record["circuit"] = {"qasm3": qasm3.dumps(circuit), "depth": circuit.depth(),
                             "two_qubit_gates": int(circuit.count_ops().get("cx", 0)),
                             "target": "generic_rz_sx_x_cx_not_hardware_backend"}
    record["elapsed_seconds"] = perf_counter() - start
    return record
