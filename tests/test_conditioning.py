from copy import deepcopy
import numpy as np
import pytest
from agqo.research.conditioning import coordinates
from agqo.research.finance import FinancialSpec
from agqo.research.design import baseline, lower
from agqo.research.quantum import compile_cost, execute, evaluate
from agqo.synthesis.profile import digest


def test_paper_equation8_scale_and_hamiltonian_identity():
    h = {
        "linear_z": [3.0, 4.0, 0.0],
        "quadratic_zz": [{"qubits": [0, 1], "coefficient": 2.0}],
        "hamiltonian_hash": "locked",
    }
    ir = {"parameters": [{"kind": "cost"}, {"kind": "mixer"}]}
    before = digest(h)
    scale, record = coordinates(ir, h, "paper_rms_v1")
    assert scale == pytest.approx([1 / np.sqrt(16.5), 1])
    assert record["optimizer_loss_scale"] == pytest.approx(1 / np.sqrt(16.5))
    assert digest(h) == before
    with pytest.raises(ValueError):
        coordinates(ir, h, "unknown")


def test_positive_hamiltonian_rescaling_preserves_conditioned_unitary_and_exports_physical_angles():
    r = np.random.default_rng(448).normal(0, 0.01, (40, 6))
    p = FinancialSpec(
        tuple(f"A{i}" for i in range(6)),
        ("S",) * 6,
        r,
        r.mean(axis=1),
        np.r_[np.ones(3) / 3, np.zeros(3)],
        3,
        "2020-01-01",
        maximum_weight=0.6,
    )
    h = compile_cost(p, True)
    ir = lower(baseline(p), p, h)
    changed = deepcopy(h)
    changed["constant"] *= 7
    changed["linear_z"] = (np.array(h["linear_z"]) * 7).tolist()
    for term in changed["quadratic_zz"]:
        term["coefficient"] *= 7
    coordinates_raw = np.array([0.2, -0.7])
    first, _ = coordinates(ir, h, "paper_rms_v1")
    second, _ = coordinates(ir, changed, "paper_rms_v1")
    assert (
        np.max(
            abs(
                execute(ir, h, coordinates_raw * first)
                - execute(ir, changed, coordinates_raw * second)
            )
        )
        < 1e-9
    )
    result = evaluate(ir, p, h, evaluations=4, shots=16, conditioning="paper_rms_v1")
    assert np.array(result["angles"]) == pytest.approx(
        np.array(result["optimizer_coordinates"]) * first
    )
    assert (
        result["optimizer_conditioning"]["hamiltonian_hash_unchanged"]
        == h["hamiltonian_hash"]
    )
