"""Exact fixed-cardinality simulation without allocating a full 2**N register.

Every free K-of-N support is retained. Paired XX/YY rotations are applied as one
exchange block, because their individual intermediate states leave this subspace.
Explicit slack qubits remain fully represented. This is a classical simulator.
"""

from itertools import combinations
from math import comb
import numpy as np
from agqo.synthesis.ir import angle_value


class ConservedBasis:
    def __init__(self, spec, h, max_states=2_000_000):
        n = spec.n
        ones = {spec.tickers.index(t) for t in spec.include}
        zeros = {spec.tickers.index(t) for t in spec.exclude}
        free = sorted(set(range(n)) - ones - zeros)
        k = spec.k - len(ones)
        ancillas = h["qubits"] - n
        if ones & zeros or not 0 <= k <= len(free):
            raise ValueError("Empty conserved asset subspace.")
        count = comb(len(free), k) * (1 << ancillas)
        if h["qubits"] >= 63 or count > max_states:
            raise ValueError(
                f"Conserved simulation needs {count} states, cap={max_states}."
            )
        fixed = sum(1 << q for q in ones)
        assets = np.array(
            sorted(
                fixed + sum(1 << q for q in group) for group in combinations(free, k)
            ),
            dtype=np.int64,
        )
        self.indices = np.concatenate(
            [assets + (slack << n) for slack in range(1 << ancillas)]
        )
        self.asset_indices = assets
        self.asset_count = len(assets)
        self.n = n
        self.ancillas = ancillas
        self.pairs = {}

    def pair(self, q, r=None):
        key = (q, r)
        if key not in self.pairs:
            if r is None:
                left = np.flatnonzero(((self.indices >> q) & 1) == 0)
                flipped = self.indices[left] ^ (1 << q)
            else:
                left = np.flatnonzero(
                    (((self.indices >> q) & 1) == 0) & (((self.indices >> r) & 1) == 1)
                )
                flipped = self.indices[left] ^ (1 << q) ^ (1 << r)
            right = np.searchsorted(self.indices, flipped)
            if np.any(right >= len(self.indices)) or np.any(
                self.indices[right] != flipped
            ):
                raise ValueError("Gate leaves the declared conserved basis.")
            self.pairs[key] = (left, right)
        return self.pairs[key]

    def gates(self, state, gates, values):
        i = 0
        while i < len(gates):
            gate = gates[i]
            op = gate["op"]
            targets = gate["qubits"]
            theta = angle_value(gate["angle"], values) if gate["angle"] else None
            if op in ("RZ", "RZZ"):
                z = np.ones(len(state), dtype=np.int8)
                for q in targets:
                    z *= 1 - 2 * ((self.indices >> q) & 1).astype(np.int8)
                state *= np.exp(-0.5j * theta * z)
                i += 1
                continue
            if op in ("RXX", "RYY") and i + 1 < len(gates):
                other = gates[i + 1]
                if (
                    {op, other["op"]} != {"RXX", "RYY"}
                    or sorted(targets) != sorted(other["qubits"])
                    or gate["angle"] != other["angle"]
                ):
                    raise ValueError("Unpaired exchange in conserved executor.")
                left, right = self.pair(*targets)
                a = state[left].copy()
                b = state[right].copy()
                state[left] = np.cos(theta) * a - 1j * np.sin(theta) * b
                state[right] = np.cos(theta) * b - 1j * np.sin(theta) * a
                i += 2
                continue
            raise ValueError(f"Gate {op} is not certified in the conserved executor.")

    def execute(self, ir, h, angles, energy=None):
        from .quantum import cost_values

        values = {p["id"]: v for p, v in zip(ir["parameters"], angles, strict=True)}
        state = np.zeros(len(self.indices), complex)
        initial = sum(int(b) << q for q, b in enumerate(ir["initial_bits"]))
        index = int(np.searchsorted(self.indices, initial))
        if index >= len(self.indices) or self.indices[index] != initial:
            raise ValueError("Initial basis state is outside the declared subspace.")
        state[index] = 1
        prep = ir.get("preparation", {})
        if prep.get("kind") == "dicke_sequential_counter_v1":
            state[:] = 0
            # Counter workspace is clean at exit by construction. Slack=0 is the
            # first sorted asset block; no asset support is filtered or selected.
            state[: self.asset_count] = 1 / np.sqrt(self.asset_count)
        elif prep:
            raise ValueError(
                "Dense Dicke synthesis is a small full-state reference only."
            )
        else:
            self.gates(state, ir["initialization"], values)
        for q in range(self.n, h["qubits"]):
            left, right = self.pair(q)
            a = state[left].copy()
            b = state[right].copy()
            state[left] = (a + b) / np.sqrt(2)
            state[right] = (a - b) / np.sqrt(2)
        energy = cost_values(h, self.indices) if energy is None else energy
        for layer in ir["layers"]:
            state *= np.exp(-1j * values[layer["cost"]["parameter"]] * energy)
            self.gates(state, layer["mixer"], values)
            beta = next(
                g["angle"]["parameter"]
                for g in layer["mixer"]
                if g.get("angle") and g["angle"].get("parameter")
            )
            for q in range(self.n, h["qubits"]):
                left, right = self.pair(q)
                a = state[left].copy()
                b = state[right].copy()
                theta = 2 * values[beta]
                state[left] = np.cos(theta / 2) * a - 1j * np.sin(theta / 2) * b
                state[right] = np.cos(theta / 2) * b - 1j * np.sin(theta / 2) * a
        return state
