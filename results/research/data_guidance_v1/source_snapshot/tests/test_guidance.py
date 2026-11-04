from copy import deepcopy
from dataclasses import replace
from itertools import combinations
import numpy as np
import pytest

from agqo.research.cloud_pipeline import contexts, common_program
from agqo.research.guidance import (
    VERSION,
    exchange_features,
    guided_request,
    check_evidence,
    admit_guided_program,
)
from agqo.research.quantum import compile_cost
from agqo.research.budget_search import cost_aware_request
from agqo.synthesis.profile import digest


def response_fixture(spec):
    """Deterministic software fixture, never a recorded LLM response."""
    p = common_program(spec)
    f = exchange_features(spec)
    free = f["free_qubits"]
    p["version"] = VERSION
    note = {
        "feature_ids": ["RESOURCE_BUDGET"],
        "hypothesis": "Shared parameters reduce optimization dimension.",
        "falsifier": "A matched-budget two-group design obtains better allocated F.",
    }
    p["evidence"] = {
        "parent_edges": {
            f"p{i}": f"EDGE_{free[p['parents'][f'p{i}']]}_{free[i]}"
            for i in range(1, len(free))
        },
        "schedule": deepcopy(note),
        "sharing": deepcopy(note),
    }
    return p


@pytest.mark.parametrize(
    "n,k,include,exclude",
    [
        (6, 2, (), ()),
        (6, 3, ("ASSET_01",), ("ASSET_00",)),
        (6, 4, (), ()),
        (6, 1, (), ()),
        (6, 5, (), ()),
    ],
)
def test_swap_moments_match_exhaustive_supports(n, k, include, exclude):
    _, spec = contexts()[0]
    assert spec.n == n
    spec = replace(spec, k=k, include=include, exclude=exclude)
    f = exchange_features(spec)
    for edge in f["edges"]:
        i, j = edge["qubits"]
        others = [q for q in f["free_qubits"] if q not in (i, j)]
        deltas = []
        for support in combinations(others, f["remaining_cardinality"] - 1):
            bits = np.zeros(n, dtype=int)
            bits[f["frozen_one"] + list(support) + [i]] = 1
            before = spec.score(bits)
            bits[i], bits[j] = 0, 1
            deltas.append(spec.score(bits) - before)
        assert edge["mean_delta_B_i_to_j"] == pytest.approx(np.mean(deltas), abs=1e-16)
        assert edge["variance_delta_B"] == pytest.approx(np.var(deltas), abs=1e-20)
        assert edge["rms_delta_B"] == pytest.approx(
            np.sqrt(np.mean(np.square(deltas))), abs=1e-16
        )
    assert f["allocation_queries"] == f["support_enumerations"] == 0


def test_two_free_assets_and_constant_objective_are_finite():
    _, spec = contexts()[0]
    spec = replace(
        spec,
        k=1,
        exclude=spec.tickers[2:],
        returns=np.zeros_like(spec.returns),
        benchmark=np.zeros_like(spec.benchmark),
        cost_weight=0,
    )
    f = exchange_features(spec)
    assert len(f["edges"]) == 1
    assert f["edges"][0]["rms_delta_B"] == 0
    r = guided_request(spec, compile_cost(spec, True), BUDGET)
    assert r["payload"]["exchange_table"]["scale"] == 1


def test_benchmark_changes_sensitivity_even_with_identical_asset_correlations():
    _, spec = contexts()[0]
    changed = replace(spec, benchmark=spec.returns[:, 0] * 2)
    a, b = exchange_features(spec), exchange_features(changed)
    assert [e["correlation"] for e in a["edges"]] == [
        e["correlation"] for e in b["edges"]
    ]
    assert not np.allclose(
        [e["rms_delta_B"] for e in a["edges"]],
        [e["rms_delta_B"] for e in b["edges"]],
        rtol=1e-8,
        atol=1e-14,
    )


def test_consistent_asset_permutation_preserves_pair_statistics_and_frozen_bits():
    _, spec = contexts()[0]
    spec = replace(spec, include=("ASSET_01",), exclude=("ASSET_00",))
    order = [4, 0, 3, 1, 5, 2]
    permuted = replace(
        spec,
        tickers=tuple(spec.tickers[i] for i in order),
        sectors=tuple(spec.sectors[i] for i in order),
        returns=spec.returns[:, order],
        previous_weights=spec.previous_weights[order],
    )
    before, after = exchange_features(spec), exchange_features(permuted)
    lookup = {tuple(spec.tickers[i] for i in e["qubits"]): e for e in before["edges"]}
    for edge in after["edges"]:
        names = tuple(permuted.tickers[i] for i in edge["qubits"])
        reverse = names not in lookup
        old = lookup[names[::-1] if reverse else names]
        assert edge["rms_delta_B"] == pytest.approx(old["rms_delta_B"], abs=1e-16)
        assert edge["mean_delta_B_i_to_j"] == pytest.approx(
            old["mean_delta_B_i_to_j"] * (-1 if reverse else 1), abs=1e-16
        )
    assert "ASSET_01" not in [permuted.tickers[q] for q in after["free_qubits"]]
    assert "ASSET_00" not in [permuted.tickers[q] for q in after["free_qubits"]]


BUDGET = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}


def test_request_has_complete_pair_table_and_deterministic_hash_without_cost_change():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    saved = deepcopy(h)
    legacy = cost_aware_request(spec, h, BUDGET)
    r = guided_request(spec, h, BUDGET)
    assert r["payload"]["hamiltonian"] == h == saved
    assert r["schema"]["properties"]["version"] == {"const": VERSION}
    assert r["schema"]["properties"]["depth"] == {"const": 1}
    assert sum(map(len, r["payload"]["exchange_table"]["rows"].values())) == 15
    assert r == guided_request(spec, h, BUDGET)
    assert r["request_hash"] == digest(
        {k: v for k, v in r.items() if k != "request_hash"}
    )
    assert legacy == cost_aware_request(spec, h, BUDGET)
    with pytest.raises(ValueError, match="disagree"):
        guided_request(spec, {**h, "problem_hash": "other"}, BUDGET)


def test_citation_link_is_checked_against_the_actual_selected_gate():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    r = guided_request(spec, h, BUDGET)
    p = response_fixture(spec)
    assert check_evidence(p, r)["valid_links"]
    p["evidence"]["parent_edges"]["p2"] = "EDGE_0_2"
    with pytest.raises(ValueError, match="selected exchange"):
        check_evidence(p, r)
    assert admit_guided_program(p, spec, h, BUDGET)["status"] == "rejected_evidence"
    p["evidence"]["parent_edges"].pop("p1")
    assert admit_guided_program(p, spec, h, BUDGET)["status"] == "rejected_evidence"


def test_valid_evidence_never_substitutes_for_quantum_or_resource_verification():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    p = response_fixture(spec)
    result = admit_guided_program(p, spec, h, BUDGET)
    assert result["status"] == "accepted" and result["verification"]["valid"]
    assert result["gate_ir"]["hamiltonian_hash"] == h["hamiltonian_hash"]
    assert not result["fallback_used"]
    assert (
        admit_guided_program(p, spec, h, {**BUDGET, "transpiled_cx": 1})["status"]
        == "rejected_resources"
    )
    p["schedule"] = [0] * len(p["schedule"])
    result = admit_guided_program(p, spec, h, BUDGET)
    assert result["evidence_check"]["valid_links"]
    assert result["status"] == "rejected_validation"
