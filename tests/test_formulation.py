from dataclasses import replace
import numpy as np
import pytest
from agqo.research.finance import FinancialSpec, allocate
from agqo.research.quantum import compile_cost, cost_values


def instance():
    r = np.random.default_rng(377).normal(0, 0.01, (80, 4))
    return FinancialSpec(
        ("A", "B", "C", "D"),
        ("X", "X", "Y", "Y"),
        r,
        0.8 * r[:, 0] + 0.2 * r[:, 2],
        np.array([0.5, 0, 0.5, 0]),
        2,
        "2020-01-01",
        include=("A",),
        exclude=("D",),
        minimum_weight=0.05,
        maximum_weight=0.9,
        cost_weight=0,
        sector_weight_caps={"X": 0.8},
    )


def test_equal_weight_encoding_matches_finance_and_continuous_is_distinct():
    p = instance()
    bits = np.array([1, 0, 1, 0])
    continuous = allocate(p, bits)
    equal = allocate(replace(p, minimum_weight=0.5, maximum_weight=0.5), bits)
    direct = np.mean(((p.returns[:, 0] + p.returns[:, 2]) / 2 - p.benchmark) ** 2)
    assert equal["feasible"] and continuous["feasible"]
    assert equal["objective"] == pytest.approx(direct, abs=1e-9)
    assert p.score(bits) == pytest.approx(direct, abs=1e-12)
    assert continuous["objective"] < direct * 0.001
    assert np.max(abs(np.asarray(equal["weights"]) - bits / 2)) < 1e-7


def test_financial_objective_allocation_and_ising_are_asset_permutation_invariant():
    p = instance()
    order = np.array([2, 0, 3, 1])
    bits = np.array([1, 0, 1, 0])
    other = replace(
        p,
        tickers=tuple(p.tickers[i] for i in order),
        sectors=tuple(p.sectors[i] for i in order),
        returns=p.returns[:, order],
        previous_weights=p.previous_weights[order],
    )
    assert other.score(bits[order]) == pytest.approx(p.score(bits), abs=1e-12)
    left, right = allocate(p, bits), allocate(other, bits[order])
    assert left["feasible"] and right["feasible"]
    assert right["objective"] == pytest.approx(left["objective"], abs=1e-10)
    assert (
        np.max(abs(np.array(right["weights"]) - np.array(left["weights"])[order]))
        < 1e-7
    )
    first, second = compile_cost(p, True), compile_cost(other, True)
    i = sum(int(b) << q for q, b in enumerate(bits))
    j = sum(int(b) << q for q, b in enumerate(bits[order]))
    assert cost_values(first, [i])[0] == pytest.approx(
        cost_values(second, [j])[0], abs=1e-10
    )


def test_equal_weight_allocator_cannot_bypass_sector_weight_cap():
    p = replace(instance(), minimum_weight=0.5, maximum_weight=0.5)
    bits = np.array([1, 1, 0, 0])
    assert p.feasible(bits)  # Selection constraints and allocation are distinct.
    result = allocate(p, bits)
    assert not result["feasible"] and result["status"] == "infeasible"
