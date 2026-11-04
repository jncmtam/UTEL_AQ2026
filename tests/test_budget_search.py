from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from agqo.research.budget_search import (
    conditioned_draws,
    disjoint_schedule,
    resource_eligibility,
    search,
    prefix_rows,
    cost_aware_request,
    admit_cost_aware_program,
)
from agqo.research.cloud_pipeline import contexts, common_program
from agqo.research.design import lower
from agqo.research.quantum import compile_cost, execute
from agqo.research.symmetry import ConservedBasis


def test_conditioned_sampler_retains_all_free_supports_without_forbidden_bits():
    _, spec = contexts()[0]
    spec = replace(spec, include=(spec.tickers[1],), exclude=(spec.tickers[0],))
    draws = conditioned_draws(spec, np.random.default_rng(10), 4000)
    assert all(i.bit_count() == spec.k and i & 2 and not i & 1 for i in map(int, draws))
    assert len(set(draws)) == 6
    with pytest.raises(ValueError):
        conditioned_draws(
            replace(spec, include=spec.exclude), np.random.default_rng(1), 1
        )


def test_new_scheduling_does_not_mutate_program_and_conserved_execution_matches():
    _, spec = contexts()[0]
    original = common_program(spec)
    saved = deepcopy(original)
    scheduled = disjoint_schedule(original, spec)
    assert original == saved
    assert sorted(scheduled["schedule"]) == original["schedule"]
    assert scheduled["schedule"] != original["schedule"]
    h = compile_cost(spec, True)
    ir = lower(scheduled, spec, h, common_preparation=True)
    angles = np.array([0.3] * len(ir["parameters"]))
    basis = ConservedBasis(spec, h)
    full = execute(ir, h, angles)
    compressed = basis.execute(ir, h, angles)
    embedded = np.zeros_like(full)
    embedded[basis.indices] = compressed
    assert abs(np.vdot(full, embedded)) ** 2 > 1 - 1e-10


def test_prefixes_count_every_optimizer_observation_and_caches():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    ir = lower(common_program(spec), spec, h, common_preparation=True)
    result = search(spec, ir, h, evaluations=3, shots=4, final_shots=4)
    assert result["total_observations"] == 16
    assert result["state_evaluations"] == 4
    points = prefix_rows(result, (4, 8, 16, 32))
    assert [r["draws"] for r in points] == [4, 8, 16]
    best = [r["best_objective"] for r in points]
    assert best == sorted(best, reverse=True)
    assert result["allocation_queries"] <= 16
    assert sum(not r["cache_hit"] for r in result["observations"]) == len(
        result["allocation_results"]
    )


def test_resource_gate_rejects_overhead_without_relabeling_fallback():
    reference = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 250}
    candidate = {**reference, "transpiled_cx": 194}
    result = resource_eligibility(candidate, reference)
    assert not result["eligible"] and not result["fallback_used"]
    assert result["exceeded"] == ["transpiled_cx"]
    assert resource_eligibility(reference, reference)["eligible"]
    with pytest.raises(ValueError):
        resource_eligibility({}, reference)


def test_cost_aware_prompt_locks_depth_budget_and_preserves_hamiltonian():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    before = deepcopy(h)
    budget = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}
    value = cost_aware_request(spec, h, budget)
    assert value["schema"]["properties"]["depth"] == {"const": 1}
    assert value["payload"]["compiled_resource_budget"] == budget
    assert h == before
    changed = cost_aware_request(spec, h, {**budget, "transpiled_depth": 225})
    assert changed["request_hash"] != value["request_hash"]
    with pytest.raises(ValueError):
        cost_aware_request(spec, h, {**budget, "transpiled_cx": None})


def test_admission_rejects_extra_layers_and_excess_resources_before_fitting():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    program = common_program(spec)
    budget = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}
    assert admit_cost_aware_program(program, spec, h, budget)["status"] == "accepted"
    assert (
        admit_cost_aware_program({**program, "depth": 2}, spec, h, budget)["status"]
        == "rejected_validation"
    )
    rejected = admit_cost_aware_program(
        program, spec, h, {**budget, "transpiled_cx": 1}
    )
    assert rejected["status"] == "rejected_resources" and not rejected["fallback_used"]


def test_cost_aware_pipeline_uniform_uses_the_same_fixed_bits():
    from agqo.research.cloud_pipeline import sampled_allocation_search

    _, spec = contexts()[1]
    result = sampled_allocation_search(
        spec,
        None,
        None,
        uniform=True,
        uniform_conditioned=True,
        evaluations=1,
        shots=16,
        final_shots=16,
    )
    assert all(not int(index) & 1 for index in result["allocation_results"])
    assert result["total_shots"] == 32
