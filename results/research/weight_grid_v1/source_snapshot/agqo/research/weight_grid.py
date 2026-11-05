"""Opt-in NAV weight-grid QUBO, distinct from the continuous primary task.

Valid registers select at most one positive amount per asset. Financial cost is
exact on that grid. Constraint penalties are conservative, not performance-tuned.
No generated code, stock filtering, LLM call or exponential cost oracle is used.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from math import ceil, comb, floor

import numpy as np

from agqo.problem import Qubo, to_ising
from agqo.synthesis.profile import digest


class UnsupportedGrid(ValueError):
    """A requested financial contract cannot be represented by this compiler."""


def _decimal(value):
    return Fraction(str(float(value)))


@dataclass(frozen=True)
class WeightGrid:
    spec: object
    units: int
    amounts: tuple[int, ...]
    registers: tuple[tuple[int, int], ...]
    weight_map: np.ndarray
    objective: Qubo
    qubo: Qubo
    penalty: float
    range_bound: float
    equalities: tuple[dict, ...]
    one_hot_pairs: tuple[tuple[int, int], ...]
    slack: tuple[dict, ...]

    @property
    def n(self):
        return self.qubo.n

    def decode(self, bits):
        bits = self._bits(bits)
        return self.weight_map @ bits

    def _bits(self, bits):
        bits = np.asarray(bits, dtype=float)
        if bits.shape != (self.n,) or not np.isin(bits, (0, 1)).all():
            raise ValueError("Expected one binary value per encoded variable.")
        return bits

    def residual_penalty(self, bits):
        bits = self._bits(bits)
        value = sum(bits[i] * bits[j] for i, j in self.one_hot_pairs)
        for eq in self.equalities:
            residual = sum(a * bits[int(i)] for i, a in eq['coefficients'].items()) - eq['target']
            value += residual**2
        return int(value)

    def encode(self, weights):
        """Encode a feasible exact-grid target, including unique binary slacks."""
        weights = np.asarray(weights, float)
        if self.spec.violations_weights(weights):
            raise ValueError("Target violates the financial specification.")
        amounts = np.rint(weights * self.units).astype(int)
        if not np.allclose(amounts / self.units, weights, atol=1e-10, rtol=0):
            raise UnsupportedGrid("Target weights are off the declared grid; no rounding was applied.")
        bits = np.zeros(self.n, dtype=int)
        for i, amount in enumerate(amounts):
            if amount:
                try:
                    bits[self.registers.index((i, int(amount)))] = 1
                except ValueError as error:
                    raise ValueError("Positive target amount is outside the grid position bounds.") from error
        for eq in self.equalities:
            slack = [s for s in self.slack if s['constraint'] == eq['label']]
            if slack:
                remainder = eq['target'] - sum(a * bits[int(i)] for i, a in eq['coefficients'].items())
                if remainder < 0 or remainder >= 2**len(slack):
                    raise ValueError("Target cannot satisfy an encoded inequality.")
                for bit, row in enumerate(slack):
                    bits[row['qubit']] = (remainder >> bit) & 1
        if self.residual_penalty(bits):
            raise ValueError("Target cannot satisfy the encoded constraints.")
        return bits

    def to_dict(self):
        return {
            'version': 'nav-weight-grid-v1', 'problem_hash': self.spec.fingerprint(),
            'units': self.units, 'grid_step': 1 / self.units,
            'amounts': list(self.amounts), 'registers': [list(v) for v in self.registers],
            'qubits': self.n, 'amount_qubits': len(self.registers),
            'slack': list(self.slack), 'equalities': list(self.equalities),
            'one_hot_pairs': [list(v) for v in self.one_hot_pairs],
            'penalty': self.penalty, 'financial_range_bound': self.range_bound,
            'penalty_proof': 'P > sum(abs(nonconstant financial QUBO coefficients)); every nonzero integer violation contributes >=1.',
            'linear': self.qubo.linear.tolist(), 'quadratic': self.qubo.quadratic.tolist(),
            'offset': self.qubo.offset,
            'financial_linear': self.objective.linear.tolist(),
            'financial_quadratic': self.objective.quadratic.tolist(),
            'financial_offset': self.objective.offset,
            'bit_order': 'asset-major positive amount choices, then binary slack; little endian',
            'status': 'discrete_transfer_formulation_not_continuous_primary_task',
        }

    def fingerprint(self):
        return digest(self.to_dict())


def compile_grid(spec, units):
    """Compile financial weights, costs and supported mandates without a truth table."""
    if type(units) is not int or not 1 <= units <= 10000:
        raise ValueError("Grid units must be an integer in [1,10000].")
    amounts = tuple(range(max(1, ceil(_decimal(spec.minimum_weight) * units)),
                          floor(_decimal(spec.maximum_weight) * units) + 1))
    if not amounts:
        raise ValueError("The grid has no positive amount within the position bounds.")
    registers = tuple((i, amount) for i in range(spec.n) for amount in amounts)
    if len(registers) > 512:
        raise UnsupportedGrid("Reference compiler is limited to 512 total binary variables.")
    mapping = np.zeros((spec.n, len(registers)))
    for q, (i, amount) in enumerate(registers):
        mapping[i, q] = amount / units
    matrix, vector, offset = spec.quadratic()
    quadratic = mapping.T @ matrix @ mapping
    cost = spec.cost_weight * spec.cost_rate
    linear = np.diag(quadratic) + mapping.T @ vector
    linear += cost * np.array([abs(amount / units - spec.previous_weights[i]) - spec.previous_weights[i]
                               for i, amount in registers])
    objective = Qubo(linear, np.triu(quadratic + quadratic.T, 1),
                     float(offset + cost * spec.previous_weights.sum()))
    bound = float(abs(objective.linear).sum() + abs(objective.quadratic).sum())
    penalty = 2 * bound + 1e-8
    linear = list(map(float, objective.linear))
    pairs = {(i, j): float(objective.quadratic[i, j]) for i in range(len(registers)) for j in range(i + 1, len(registers))}
    constant = objective.offset
    equalities, slack, one_hot = [], [], []

    def equality(coeff, target, label):
        nonlocal constant
        coeff = {i: int(a) for i, a in coeff.items() if a}
        constant += penalty * target**2
        for i, a in coeff.items():
            linear[i] += penalty * (a * a - 2 * target * a)
            for j, b in coeff.items():
                if i < j:
                    pairs[i, j] = pairs.get((i, j), 0.0) + 2 * penalty * a * b
        equalities.append({'label': label, 'coefficients': {str(i): a for i, a in coeff.items()}, 'target': int(target)})

    def upper(coeff, target, label):
        # Lower bound on this affine expression on valid per-asset registers.
        lower = sum(min([0] + [coeff.get(q, 0) for q, (asset, _) in enumerate(registers) if asset == i]) for i in range(spec.n))
        capacity = max(0, target - lower)
        coeff = dict(coeff)
        for bit in range(int(capacity).bit_length()):
            q = len(linear)
            if q >= 512:
                raise UnsupportedGrid("Reference compiler is limited to 512 total binary variables.")
            linear.append(0.0)
            coeff[q] = 1 << bit
            slack.append({'qubit': q, 'weight': 1 << bit, 'constraint': label})
        equality(coeff, target, label)

    equality({q: amount for q, (_, amount) in enumerate(registers)}, units, 'money_budget')
    equality(dict.fromkeys(range(len(registers)), 1), spec.k, 'cardinality')
    for i in range(spec.n):
        qs = [q for q, (asset, _) in enumerate(registers) if asset == i]
        for a, b in combinations(qs, 2):
            pairs[a, b] = pairs.get((a, b), 0.0) + penalty
            one_hot.append((a, b))
    for names, target, prefix in ((spec.include, 1, 'include:'), (spec.exclude, 0, 'exclude:')):
        for name in names:
            i = spec.tickers.index(name)
            equality({q: 1 for q, (asset, _) in enumerate(registers) if asset == i}, target, prefix + name)
    for sector, cap in spec.sector_count_caps.items():
        upper({q: 1 for q, (i, _) in enumerate(registers) if spec.sectors[i] == sector}, cap, 'sector_count:' + sector)
    for sector, cap in spec.sector_weight_caps.items():
        upper({q: m for q, (i, m) in enumerate(registers) if spec.sectors[i] == sector},
              floor(_decimal(cap) * units), 'sector_weight:' + sector)
    if spec.max_replacements is not None:
        upper({q: 1 for q, (i, _) in enumerate(registers) if spec.previous_weights[i] <= 1e-10},
              spec.max_replacements, 'replacements')
    if spec.turnover_cap is not None:
        old = np.rint(spec.previous_weights * units).astype(int)
        if not np.allclose(old / units, spec.previous_weights, atol=1e-10, rtol=0):
            raise UnsupportedGrid("Turnover cap requires grid-compatible prior holdings; drifted weights were not rounded.")
        upper({q: abs(m - old[i]) - int(old[i]) for q, (i, m) in enumerate(registers)},
              floor(2 * units * _decimal(spec.turnover_cap)) - units, 'one_way_turnover_including_cash')
    total = len(linear)
    full_quadratic = np.zeros((total, total))
    for ij, value in pairs.items():
        full_quadratic[ij] = value
    full_map = np.pad(mapping, ((0, 0), (0, total - len(registers))))
    result = Qubo(np.asarray(linear), full_quadratic, float(constant))
    for array in (full_map, objective.linear, objective.quadratic, result.linear, result.quadratic):
        array.setflags(write=False)
    return WeightGrid(spec, units, amounts, registers, full_map, objective, result,
                      penalty, bound, tuple(equalities), tuple(one_hot), tuple(slack))


def portfolios(grid, limit=1000000):
    """Exhaust financial grid portfolios only, never the full qubit state space."""
    if comb(grid.spec.n, grid.spec.k) * len(grid.amounts)**grid.spec.k > limit:
        raise ValueError("Financial-grid enumeration exceeds the declared limit.")
    for support in combinations(range(grid.spec.n), grid.spec.k):
        for amounts in product(grid.amounts, repeat=grid.spec.k):
            if sum(amounts) != grid.units:
                continue
            weights = np.zeros(grid.spec.n)
            weights[list(support)] = np.asarray(amounts) / grid.units
            if not grid.spec.violations_weights(weights):
                yield weights


def cost_circuit(grid, gamma):
    """Export exp(-i gamma H) with explicit RZ/RZZ gates and its global phase."""
    from qiskit import QuantumCircuit
    if not np.isfinite(gamma):
        raise ValueError("Cost angle must be finite.")
    ising = to_ising(grid.qubo)
    circuit = QuantumCircuit(grid.n)
    circuit.global_phase = -float(gamma) * ising.constant
    for i, h in enumerate(ising.fields):
        if h:
            circuit.rz(2 * gamma * h, i)
    for i, j in zip(*np.nonzero(ising.couplings)):
        circuit.rzz(2 * gamma * ising.couplings[i, j], int(i), int(j))
    return circuit
