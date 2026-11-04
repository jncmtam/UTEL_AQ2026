from copy import deepcopy
import numpy as np
import pytest
from agqo.research.cloud_pipeline import contexts
from agqo.research.finance import FinancialSpec
from agqo.research.quantum import compile_cost
from agqo.research.frozen_numerics import freeze, bind
from agqo.synthesis.profile import digest


def test_frozen_transport_preserves_exact_hamiltonian_despite_tiny_platform_difference(
    monkeypatch,
):
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    frozen = freeze(spec, h)
    original = FinancialSpec.quadratic

    def perturbed(self):
        q, v, c = original(self)
        return q + np.eye(self.n) * 1e-20, v + 1e-20, c

    monkeypatch.setattr(FinancialSpec, "quadratic", perturbed)
    pinned, actual, certificate = bind(spec, frozen)
    assert compile_cost(pinned, True) == actual == h
    assert pinned.fingerprint() == spec.fingerprint()
    assert certificate["executed_hamiltonian_bitwise_original"]
    assert certificate["maximum_matrix_difference"] > 0
    assert not certificate["platform_bitwise_same"]


def test_changed_statistics_and_hashes_fail_closed():
    _, spec = contexts()[0]
    frozen = freeze(spec, compile_cost(spec, True))
    bad = deepcopy(frozen)
    bad["matrix"][0][0] += 0.01
    with pytest.raises(ValueError, match="identity"):
        bind(spec, bad)
    bad["numerical_hash"] = digest(
        {k: v for k, v in bad.items() if k != "numerical_hash"}
    )
    with pytest.raises(ValueError, match="financial objective"):
        bind(spec, bad)
    bad = deepcopy(frozen)
    bad["hamiltonian"]["hamiltonian_hash"] = "wrong"
    bad["numerical_hash"] = digest(
        {k: v for k, v in bad.items() if k != "numerical_hash"}
    )
    with pytest.raises(ValueError, match="Hamiltonian hash"):
        bind(spec, bad)
