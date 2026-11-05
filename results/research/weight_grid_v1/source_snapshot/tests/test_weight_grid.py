"""Financial projection and independent energy checks for the opt-in lot compiler."""
from dataclasses import replace
from itertools import product

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from agqo.problem import to_ising
from agqo.research.finance import FinancialSpec
from agqo.research.weight_grid import UnsupportedGrid, compile_grid, cost_circuit, portfolios


def example(**kwargs):
    returns = np.array([[.01, -.005, .003], [-.02, .01, .004], [.015, .007, -.01], [.002, -.003, .005]])
    spec = FinancialSpec(('A', 'B', 'C'), ('one', 'two', 'two'), returns,
                         returns @ np.array([.4, .35, .25]), np.array([.5, .5, 0]),
                         2, '2020-01-01', maximum_weight=.7,
                         sector_weight_caps={'one': .7})
    return replace(spec, **kwargs)


def test_exhaustive_projection_and_independent_energy():
    spec = example()
    grid = compile_grid(spec, 3)
    h = to_ising(grid.qubo)
    feasible = []
    invalid_energies = []
    for values in product((0, 1), repeat=grid.n):
        bits = np.array(values)
        # Independent QUBO evaluation, using explicit pair products and Z signs.
        ising = h.constant + h.fields @ (1-2*bits)
        ising += sum(h.couplings[i, j]*(1-2*bits[i])*(1-2*bits[j]) for i in range(grid.n) for j in range(i+1, grid.n))
        assert ising == pytest.approx(grid.qubo.energy(bits), abs=1e-10)
        money = grid.decode(bits)
        valid_register = all(sum(bits[q] for q, (asset, _) in enumerate(grid.registers) if asset == i) <= 1 for i in range(spec.n))
        financial_valid = valid_register and not spec.violations_weights(money)
        residual = grid.residual_penalty(bits)
        raw = grid.objective.energy(bits[:len(grid.registers)])
        assert grid.qubo.energy(bits) == pytest.approx(raw + grid.penalty*residual, abs=1e-10)
        if residual == 0:
            assert financial_valid
            assert grid.qubo.energy(bits) == pytest.approx(spec.metrics_weights(money)['objective'], abs=1e-10)
            assert np.array_equal(grid.encode(money), bits)
            feasible.append(grid.qubo.energy(bits))
        else:
            invalid_energies.append(grid.qubo.energy(bits))
    assert feasible and min(invalid_energies) > min(feasible)
    assert len(feasible) == len(list(portfolios(grid)))
    assert grid.penalty > grid.range_bound


def test_cash_turnover_and_mandates():
    spec = example(previous_weights=np.array([.5, 0, 0]), maximum_weight=.75,
                   turnover_cap=.5, sector_count_caps={'two': 1}, include=('A',),
                   exclude=('C',), max_replacements=1)
    grid = compile_grid(spec, 4)
    weights = np.array([.5, .5, 0])
    bits = grid.encode(weights)
    assert grid.residual_penalty(bits) == 0
    assert spec.metrics_weights(weights)['one_way_turnover'] == .5
    eq = next(v for v in grid.equalities if v['label'] == 'one_way_turnover_including_cash')
    assert eq['target'] == 0
    for w in portfolios(grid):
        assert grid.residual_penalty(grid.encode(w)) == 0
        assert grid.objective.energy(grid.encode(w)[:len(grid.registers)]) == pytest.approx(spec.metrics_weights(w)['objective'], abs=1e-12)


def test_off_grid_holdings_are_supported_for_cost_but_not_capped_turnover():
    spec = example(previous_weights=np.array([.413, .587, 0]))
    grid = compile_grid(spec, 6)
    w = np.array([.5, .5, 0])
    assert grid.objective.energy(grid.encode(w)[:len(grid.registers)]) == pytest.approx(spec.metrics_weights(w)['objective'])
    with pytest.raises(UnsupportedGrid, match='not rounded'):
        compile_grid(replace(spec, turnover_cap=.5), 6)
    with pytest.raises(UnsupportedGrid, match='no rounding'):
        grid.encode(np.array([.41, .59, 0]))


def test_decimal_boundary_and_grid_infeasibility():
    spec = example(minimum_weight=.1, maximum_weight=.3, k=3, sector_weight_caps={'one': .3})
    grid = compile_grid(spec, 10)
    assert grid.amounts == (1, 2, 3)
    eq = next(v for v in grid.equalities if v['label'] == 'sector_weight:one')
    assert eq['target'] == 3
    assert not list(portfolios(grid))  # Continuous budget is also impossible here.
    with pytest.raises(ValueError, match='no positive amount'):
        compile_grid(replace(spec, minimum_weight=.21, maximum_weight=.29), 3)
    contradiction = compile_grid(example(include=('A',), exclude=('A',)), 3)
    assert not list(portfolios(contradiction))
    # Continuous .5/.5 is feasible but cannot be represented on an odd denominator.
    with pytest.raises(ValueError, match='no positive amount'):
        compile_grid(example(minimum_weight=.5, maximum_weight=.5), 3)


def test_explicit_gate_evolution_matches_direct_financial_hamiltonian():
    grid = compile_grid(example(sector_weight_caps={}), 3)
    qc = cost_circuit(grid, .173)
    # Check all computational inputs simultaneously via superposition, <=16 qubits.
    initial = np.ones(2**grid.n, dtype=complex) / np.sqrt(2**grid.n)
    actual = Statevector(initial).evolve(qc).data
    energies = np.array([grid.qubo.energy([(index >> q) & 1 for q in range(grid.n)]) for index in range(2**grid.n)])
    assert np.max(abs(actual - initial * np.exp(-.173j*energies))) < 1e-10


def test_resource_guard_and_risk_return_transfer():
    with pytest.raises(UnsupportedGrid, match='512'):
        compile_grid(example(), 1000)
    spec = example(objective_kind='risk_return')
    grid = compile_grid(spec, 6)
    for w in portfolios(grid):
        x = grid.encode(w)
        assert grid.objective.energy(x[:len(grid.registers)]) == pytest.approx(spec.metrics_weights(w)['objective'], abs=1e-10)
    with pytest.raises(ValueError, match='limit'):
        list(portfolios(grid, limit=1))
