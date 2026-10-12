import numpy as np
import pytest

from agqo.problem import build_qubo, synthetic_problem
from agqo.qpu import (
    QpuConfig,
    _finalize_shots,
    _reserve_shots,
    build_parameterized_circuit,
    validate_qpu_config,
)
from agqo.aer import crosscheck_aer


def test_qpu_configuration_blocks_placeholders_before_network():
    config = QpuConfig("FILL_IN", "FILL_IN", "FILL_IN_FROM_PROVIDER", "TOKEN", 512, 50, 800_000)
    with pytest.raises(ValueError, match="điền"):
        validate_qpu_config(config)


def test_qpu_ledger_reserves_and_caps_cumulative_shots(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN", "test-only")
    path = tmp_path / "ledger.json"
    config = QpuConfig("channel", "instance", "backend", "TOKEN", 512, 2, 1536, ledger_path=str(path))
    first = _reserve_shots(config)
    _finalize_shots(config, first, 512)
    second = _reserve_shots(config)
    assert first != second
    with pytest.raises(ValueError, match="vượt trần"):
        _reserve_shots(config)


def test_qiskit_parameterized_circuits_are_well_formed():
    pytest.importorskip("qiskit")
    problem = synthetic_problem(20261012, n=8, k=6)
    for mixer in ("X", "XY"):
        bits = np.array([1, 1, 1, 1, 1, 1, 0, 0]) if mixer == "XY" else None
        circuit, parameters = build_parameterized_circuit(build_qubo(problem, mixer), mixer, 1, bits)
        assert circuit.num_qubits == 8
        assert circuit.num_clbits == 8
        assert len(parameters) == 2
        assert len(circuit.parameters) == 2


def test_aer_samples_match_the_ideal_xy_feasible_subspace():
    pytest.importorskip("qiskit_aer")
    result = crosscheck_aer(synthetic_problem(20261012, n=8, k=6), mixer="XY", shots=512)
    assert result["ideal_feasible_probability"] > 1 - 1e-10
    assert result["sampled_feasible_probability"] == 1.0
    assert result["total_variation_distance"] < 0.2


def test_parameterized_qpu_circuits_transpile_and_bind_on_local_backend():
    pytest.importorskip("qiskit_aer")
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_aer import AerSimulator

    problem = synthetic_problem(20261012, n=8, k=6)
    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    for mixer in ("X", "XY"):
        bits = np.array([1, 1, 1, 1, 1, 1, 0, 0]) if mixer == "XY" else None
        circuit, parameters = build_parameterized_circuit(build_qubo(problem, mixer), mixer, 1, bits)
        isa_circuit = pass_manager.run(circuit)
        bound = isa_circuit.assign_parameters(dict(zip(parameters, (0.31, -0.52))))
        counts = backend.run(bound, shots=64, seed_simulator=11).result().get_counts()
        assert sum(counts.values()) == 64
