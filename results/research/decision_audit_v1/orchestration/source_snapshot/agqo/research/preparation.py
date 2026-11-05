"""Compiler-owned sequential Dicke preparation with explicit clean workspace.

This counter construction is not the ancilla-free Bärtschi/Eidenbenz algorithm.
Its complete primitive decomposition is counted by the ordinary transpiler.
"""

from copy import deepcopy
from itertools import combinations
from math import comb
import numpy as np

KIND = "dicke_sequential_counter_v1"


def counter_qubits(n, k):
    if not 0 <= k <= n:
        raise ValueError("Invalid Dicke cardinality.")
    return k.bit_length() if 0 < k < n else 0


def counter_circuit(n, k):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import UCRYGate

    workspace = counter_qubits(n, k)
    qc = QuantumCircuit(n + workspace)
    if k in (0, n):
        if k:
            qc.x(range(n))
        return qc
    counter = list(range(n, n + workspace))
    for bit, q in enumerate(counter):
        if (k >> bit) & 1:
            qc.x(q)
    for asset in range(n):
        remaining = n - asset
        angles = [
            2 * np.arcsin(np.sqrt(j / remaining)) if j <= min(k, remaining) else 0.0
            for j in range(1 << workspace)
        ]
        # Target first, then controls in little-endian binary-counter order.
        qc.append(UCRYGate(angles), [asset, *counter])
        # Decrement under asset=1. Descending order tests the original lower bits.
        for bit in reversed(range(workspace)):
            lower = counter[:bit]
            if lower:
                qc.x(lower)
                qc.mcx([asset, *lower], counter[bit])
                qc.x(lower)
            else:
                qc.cx(asset, counter[bit])
    return qc


def with_counter_dicke(ir, spec):
    value = deepcopy(ir)
    value["initialization"] = []
    value["preparation"] = {
        "kind": KIND,
        "free_qubits": [
            i
            for i, t in enumerate(spec.tickers)
            if t not in spec.include + spec.exclude
        ],
        "ones": spec.k - len(spec.include),
    }
    return value


def workspace_for(ir):
    prep = ir.get("preparation", {})
    return (
        counter_qubits(len(prep["free_qubits"]), prep["ones"])
        if prep.get("kind") == KIND
        else 0
    )


def reference_state(ir):
    """Independent small combinatorial reference; never a circuit synthesizer."""
    n = len(ir["initial_bits"])
    if n > 16:
        raise ValueError("Use the conserved basis for larger reference states.")
    prep = ir["preparation"]
    free, k = prep["free_qubits"], prep["ones"]
    fixed = sum(b << q for q, b in enumerate(ir["initial_bits"]) if q not in free)
    state = np.zeros(1 << n, complex)
    for group in combinations(free, k):
        state[fixed + sum(1 << q for q in group)] = 1 / np.sqrt(comb(len(free), k))
    return state
