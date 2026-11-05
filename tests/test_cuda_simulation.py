"""Optional torch executor crosschecks; CPU mode is a named diagnostic only."""

from copy import deepcopy
from dataclasses import replace
import importlib.util

import numpy as np
import pytest

from agqo.research.cloud_pipeline import contexts, common_program
from agqo.research.cuda_simulation import TorchConservedBasis
from agqo.research.design import baseline, lower
from agqo.research.quantum import compile_cost, execute, circuit
from agqo.research.symmetry import ConservedBasis
from agqo.research.budget_search import search


def test_cuda_default_never_falls_back_when_cuda_is_unavailable():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    if importlib.util.find_spec("torch") is None:
        with pytest.raises(RuntimeError, match="PyTorch is required"):
            TorchConservedBasis(spec, h)
        return
    import torch

    if not torch.cuda.is_available():
        with pytest.raises(RuntimeError, match="no CPU simulation fallback"):
            TorchConservedBasis(spec, h)


@pytest.mark.parametrize("counter", [False, True])
@pytest.mark.parametrize("frozen", [False, True])
def test_explicit_torch_cpu_reference_matches_full_and_numpy(counter, frozen):
    pytest.importorskip("torch")
    _, spec = contexts()[0]
    if frozen:
        spec = replace(spec, include=(spec.tickers[1],), exclude=(spec.tickers[0],))
    h = compile_cost(spec, True)
    program = common_program(spec) if counter else baseline(spec)
    ir = lower(program, spec, h, common_preparation=counter)
    torch_basis = TorchConservedBasis(spec, h, device="cpu")
    reference = ConservedBasis(spec, h)
    for seed in (2, 7, 19):
        angles = np.random.default_rng(seed).normal(size=len(ir["parameters"]))
        actual = torch_basis.execute(ir, h, angles)
        expected = reference.execute(ir, h, angles)
        full = execute(ir, h, angles)
        assert np.max(abs(actual - expected)) < 1e-10
        assert np.max(abs(actual - full[reference.indices])) < 1e-10
        assert np.vdot(actual, actual).real == pytest.approx(1, abs=1e-10)
    from qiskit.quantum_info import Statevector

    qiskit_state = Statevector.from_instruction(circuit(ir, h, angles)[0]).data
    assert np.max(abs(actual - qiskit_state[reference.indices])) < 1e-10
    assert torch_basis.metadata()["execution"] == "cpu_unit_crosscheck_only"
    assert torch_basis.metadata()["execute_calls"] == 3
    assert not torch_basis.metadata()["cpu_fallback"]


def test_torch_diagonal_rotations_and_rejection_are_independent_of_numpy_update():
    pytest.importorskip("torch")
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    ir = lower(common_program(spec), spec, h, common_preparation=True)
    angle = {"parameter": None, "scale": 0, "offset": -0.23}
    ir["layers"][0]["mixer"].extend([
        {"op": "RZ", "qubits": [0], "angle": angle},
        {"op": "RZZ", "qubits": [0, 2], "angle": angle},
    ])
    basis = TorchConservedBasis(spec, h, device="cpu")
    angles = [0.23] * len(ir["parameters"])
    actual = basis.execute(ir, h, angles)
    expected = ConservedBasis(spec, h).execute(ir, h, angles)
    assert np.max(abs(actual - expected)) < 1e-10
    broken = deepcopy(ir)
    broken["layers"][0]["mixer"].pop(1)
    with pytest.raises(ValueError, match="Unpaired exchange"):
        basis.execute(broken, h, angles)
    with pytest.raises(ValueError, match="bound to the original Hamiltonian"):
        basis.execute(ir, {**h, "hamiltonian_hash": "changed"}, angles)


def test_shared_search_uses_explicit_executor_and_emits_runtime_metadata():
    pytest.importorskip("torch")
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    ir = lower(common_program(spec), spec, h, common_preparation=True)
    created = []

    def factory(actual_spec, actual_h):
        value = TorchConservedBasis(actual_spec, actual_h, device="cpu")
        created.append(value)
        return value

    result = search(spec, ir, h, seed=11, evaluations=2, shots=2, final_shots=2, basis_factory=factory)
    assert len(created) == 1
    assert created[0].execute_calls == result["state_evaluations"] == 3
    assert result["simulation_execution"]["execute_calls"] == 3
    assert result["simulation_execution"]["execution"] == "cpu_unit_crosscheck_only"
    assert result["simulation_execution"]["cuda"] is False
