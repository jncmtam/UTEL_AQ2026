"""Compile a verified CircuitSpec into a Qiskit circuit / OpenQASM for hardware runs.

Optional dependency: qiskit. The numpy simulator and this compiler implement the
same gates; `check_against_simulator` confirms they agree on small instances.
"""

from __future__ import annotations

import numpy as np

from .simulator import CompiledProblem, warm_angles
from .spec import CircuitSpec


def build_circuit(cp: CompiledProblem, spec: CircuitSpec, angles: np.ndarray, measure: bool = True):
    from qiskit import QuantumCircuit

    n, p = cp.n, spec.layers
    _, sel, scale = cp.phase_terms(spec)          # same pruning and scale as the simulator
    qc = QuantumCircuit(n, name="agqo_qaoa")
    thetas = warm_angles(cp, spec.warm_start_epsilon)
    if spec.initial_state == "uniform":
        qc.h(range(n))
    else:
        for q in range(n):
            qc.ry(float(thetas[q]), q)
    gam, bet = angles[:p], angles[p:]
    for g, b in zip(gam, bet):
        # exp(-i g H/scale):  RZ(2 g h) and RZZ(2 g J)
        for q in range(n):
            qc.rz(float(2 * g * cp.hz[q] / scale), q)
        for (i, j), w in zip(cp.pairs[sel], cp.pair_w[sel]):
            qc.rzz(float(2 * g * w / scale), int(i), int(j))
        for q in range(n):
            if spec.mixer == "x":
                qc.rx(float(2 * b), q)
            else:
                qc.ry(float(-thetas[q]), q)
                qc.rz(float(-2 * b), q)
                qc.ry(float(thetas[q]), q)
    if measure:
        qc.measure_all()
    return qc


def to_qasm(qc) -> str:
    from qiskit import qasm2
    return qasm2.dumps(qc)


def check_against_simulator(cp: CompiledProblem, spec: CircuitSpec, angles: np.ndarray) -> float:
    """Max |prob difference| between Qiskit Statevector and the numpy simulator."""
    from qiskit.quantum_info import Statevector

    from .simulator import statevector

    qc = build_circuit(cp, spec, angles, measure=False)
    p_q = np.abs(Statevector(qc).data) ** 2
    p_n = np.abs(statevector(cp, spec, angles)) ** 2
    return float(np.abs(p_q - p_n).max())


def resource_report(qc) -> dict:
    from qiskit import transpile

    t = transpile(qc.remove_final_measurements(inplace=False), basis_gates=["cx", "rz", "sx", "x"],
                  optimization_level=1)
    ops = t.count_ops()
    return {"qubits": qc.num_qubits, "cx": int(ops.get("cx", 0)), "depth": int(t.depth()),
            "single_qubit": int(sum(v for k, v in ops.items() if k != "cx"))}
