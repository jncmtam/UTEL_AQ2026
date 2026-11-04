"""Explicit non-LLM schedules, also serving as test fixtures and baselines."""
from __future__ import annotations
import numpy as np


def rotation(op, targets, parameter=None, scale=2.0, offset=0.0):
    return {"op": op, "qubits": list(targets), "angle": {"parameter": parameter, "scale": scale, "offset": offset}}


def exchange(i, j, parameter=None, offset=0.0):
    return [rotation(op, [i, j], parameter, offset=offset) for op in ("RXX", "RYY")]


def build_rule(problem, hamiltonian, profile, depth=2, seed=None, fixed=False, basis_init=False):
    n = problem.n
    if seed is not None:
        order = np.random.default_rng(seed).permutation(n).tolist()
    elif fixed:
        order = list(range(n))
    else:
        # Correlation-neighbor path, with full connectivity; never drops cost terms.
        c = np.asarray(profile["correlation"])
        order, remaining = [int(np.argmax(problem.previous_weights))], set(range(n))
        remaining.remove(order[0])
        while remaining:
            j = max(sorted(remaining), key=lambda j: abs(c[order[-1], j]))
            order.append(j); remaining.remove(j)
    edges = [(order[i], order[(i + 1) % n]) for i in range(n)]
    bits = np.zeros(n, dtype=int)
    bits[np.argsort(-problem.previous_weights, kind="stable")[:problem.k]] = 1
    parameters, layers = [], []
    for layer in range(depth):
        parameters.extend([{"id": f"gamma_{layer}", "kind": "cost", "initial": None},
                           {"id": f"beta_{layer}", "kind": "mixer", "initial": None}])
        schedule = edges if layer % 2 == 0 else list(reversed(edges))
        layers.append({"cost": {"op": "COST", "parameter": f"gamma_{layer}", "hamiltonian_hash": hamiltonian["hamiltonian_hash"]},
                       "mixer": [gate for i, j in schedule for gate in exchange(i, j, f"beta_{layer}")]})
    initial = [] if basis_init else [gate for i, j in edges for gate in exchange(i, j, offset=0.37)]
    return {"version": "gate-ir-v1", "problem_hash": problem.fingerprint(), "hamiltonian_hash": hamiltonian["hamiltonian_hash"],
            "qubit_to_asset": list(range(n)), "mode": "preserve_cardinality", "initial_bits": bits.tolist(),
            "parameters": parameters, "initialization": initial, "layers": layers,
            "rationale": [{"feature_ids": [] if fixed or seed is not None else ["CORRELATION", "INCUMBENT"],
                           "decision": "Non-LLM baseline: cyclic exchanges with deterministic/random/correlation-neighbor ordering."}]}
