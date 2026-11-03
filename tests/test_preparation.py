from dataclasses import replace
from math import comb
import numpy as np
import pytest
from qiskit.quantum_info import Statevector
from agqo.research.preparation import (
    counter_circuit,
    counter_qubits,
    with_counter_dicke,
)
from agqo.research.finance import FinancialSpec
from agqo.research.design import baseline, lower
from agqo.research.quantum import compile_cost, execute, verify
from agqo.research.symmetry import ConservedBasis


@pytest.mark.parametrize("n", range(1, 9))
def test_counter_preparation_every_cardinality_amplitudes_and_clean_workspace(n):
    for k in range(n + 1):
        qc = counter_circuit(n, k)
        state = Statevector.from_instruction(qc).data
        expected = np.zeros(len(state), complex)
        for index in range(1 << n):
            if index.bit_count() == k:
                expected[index] = 1 / np.sqrt(comb(n, k))
        assert np.max(abs(state - expected)) < 1e-9
        assert np.sum(abs(state[1 << n :]) ** 2) < 1e-9
        assert qc.num_qubits == n + counter_qubits(n, k)


def financial_spec(n=6):
    r = np.random.default_rng(411).normal(0, 0.01, (50, n))
    return FinancialSpec(
        tuple(f"A{i}" for i in range(n)),
        ("S",) * n,
        r,
        r.mean(axis=1),
        np.r_[np.ones(3) / 3, np.zeros(n - 3)],
        3,
        "2020-01-01",
        maximum_weight=0.6,
    )


def test_counter_full_qaoa_crosscheck_with_frozen_assets_and_slack():
    spec = replace(
        financial_spec(), include=("A0",), exclude=("A5",), sector_count_caps={"S": 3}
    )
    h = compile_cost(spec, constrained_subspace=True)
    ir = with_counter_dicke(lower(baseline(spec), spec, h), spec)
    report = verify(ir, spec, h)
    assert report["valid"], report
    assert min(report["crosscheck_state_fidelities"]) > 1 - 1e-9
    assert report["resources"]["preparation_workspace_qubits"] == 2
    assert report["resources"]["qubits"] == h["qubits"] + 2
    basis = ConservedBasis(spec, h)
    angles = [0.31, -0.64]
    full = execute(ir, h, angles)
    compressed = basis.execute(ir, h, angles)
    assert np.max(abs(full[basis.indices] - compressed)) < 1e-9
    assert report["resources"]["transpiled_cx"] > 0


def test_counter_claim_and_mixed_initialization_are_rejected():
    spec = financial_spec()
    h = compile_cost(spec, constrained_subspace=True)
    ir = with_counter_dicke(lower(baseline(spec), spec, h), spec)
    ir["preparation"]["ones"] += 1
    assert not verify(ir, spec, h)["valid"]
    ir["preparation"] = []
    assert not verify(ir, spec, h)["valid"]
    ir = with_counter_dicke(lower(baseline(spec), spec, h), spec)
    ir["preparation"]["ones"] = float(ir["preparation"]["ones"])
    assert not verify(ir, spec, h)["valid"]
    ir = with_counter_dicke(lower(baseline(spec), spec, h), spec)
    ir["initialization"] = [
        {
            "op": "RZ",
            "qubits": [0],
            "angle": {"parameter": None, "scale": 0, "offset": 0.2},
        }
    ]
    assert not verify(ir, spec, h)["valid"]
