"""Allocated fitting contracts, including failures hidden by a favorable tail."""

from dataclasses import replace
import numpy as np
import pytest

from agqo.research.sample_loss import lower_tail_mean, batch_loss
from agqo.research.budget_search import search
from agqo.research.cloud_pipeline import contexts, common_program
from agqo.research.design import lower
from agqo.research.quantum import compile_cost


def circuit_fixture():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    ir = lower(common_program(spec), spec, h, common_preparation=True)
    return spec, ir, h


def test_fractional_empirical_tail_boundary_and_alpha_one():
    values = [0.8, 0.1, 0.4, 0.2, 0.5]
    assert lower_tail_mean(values, 0.3) == pytest.approx((0.1 + 0.5 * 0.2) / 1.5)
    assert lower_tail_mean(values, 1) == pytest.approx(np.mean(values))
    assert lower_tail_mean([0.2, 0.2, 0.2], 0.1) == pytest.approx(0.2)
    assert lower_tail_mean([0.7], 0.25) == pytest.approx(0.7)


@pytest.mark.parametrize(
    "alpha", [0, -1, 1.1, float("nan"), float("inf"), True, "0.25"]
)
def test_invalid_tail_fraction_rejected(alpha):
    with pytest.raises(ValueError):
        lower_tail_mean([0.1, 0.2], alpha)


@pytest.mark.parametrize("losses", [[], [[0.1]], [float("nan")], [float("inf")]])
def test_invalid_tail_vectors_rejected(losses):
    with pytest.raises(ValueError):
        lower_tail_mean(losses, 0.25)


def test_good_tail_cannot_hide_invalid_or_unknown_mass():
    r = batch_loss(
        [0.01, 2, 2, 2],
        [True, False, False, False],
        ["optimal", "infeasible", "unknown", "unknown"],
        kind="lower_tail",
    )
    assert r["lower_tail_loss"] == 0.01
    assert r["feasible_fraction"] == 0.25
    assert r["tail_mass"] == 1
    assert not r["eligible"]
    assert r["objective_loss"] == pytest.approx(2 + 0.95 - 0.25)
    assert r["status_counts"] == {"optimal": 1, "infeasible": 1, "unknown": 2}
    assert r["observations"] == 4


def test_eligible_batch_selects_aggregation_and_keeps_all_observations():
    losses = [0.1, 0.2, 0.3, 2]
    flags = np.array([True, True, True, False], dtype=np.bool_)
    states = ["optimal", "feasible", "optimal", "infeasible"]
    mean = batch_loss(losses, flags, states, min_feasible_fraction=0.75)
    tail = batch_loss(
        losses, flags, states, kind="lower_tail", min_feasible_fraction=0.75
    )
    assert mean["eligible"] and tail["eligible"]
    assert mean["objective_loss"] == pytest.approx(0.65)
    assert tail["objective_loss"] == pytest.approx(0.1)
    assert tail["status_counts"]["infeasible"] == 1


@pytest.mark.parametrize(
    "losses,flags,statuses",
    [
        ([], [], []),
        ([[0.1]], [True], ["optimal"]),
        ([0.1, 0.2], [True], ["optimal", "optimal"]),
        ([0.1], [1], ["optimal"]),
        ([0.1], [True], [None]),
        ([float("nan")], [True], ["optimal"]),
        ([float("inf")], [True], ["optimal"]),
        ([-0.1], [True], ["optimal"]),
        ([2.1], [False], ["infeasible"]),
        ([1.1], [True], ["optimal"]),
        ([0.2], [False], ["unknown"]),
        ([0.1], [True], ["unknown"]),
        ([0.1], [True], ["infeasible"]),
    ],
)
def test_batch_rejects_misalignment_and_inconsistent_statuses(losses, flags, statuses):
    with pytest.raises(ValueError):
        batch_loss(losses, flags, statuses)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "best"},
        {"alpha": 0},
        {"alpha": True},
        {"min_feasible_fraction": 0},
        {"min_feasible_fraction": 1.1},
        {"min_feasible_fraction": False},
    ],
)
def test_invalid_batch_policy_rejected(kwargs):
    with pytest.raises(ValueError):
        batch_loss([0.1], [True], ["optimal"], **kwargs)


@pytest.mark.parametrize("fitting", ["mean", "lower_tail"])
def test_opt_in_records_exact_fit_final_budgets_and_allocation_accounting(fitting):
    spec, ir, h = circuit_fixture()
    run = search(
        spec,
        ir,
        h,
        fitting=fitting,
        evaluations=3,
        shots=4,
        final_shots=4,
        min_feasible_fraction=1,
    )
    record = run["fitting_record"]
    assert record["kind"] == fitting and record["alpha"] == 0.25
    assert record["minimum_feasible_fraction"] == 1
    assert record["version"] == "feasibility-gated-allocated-fitting-v1"
    batches = record["batches"]
    assert [b["phase"] for b in batches] == ["fit", "fit", "fit", "final"]
    assert [(b["observations_start"], b["observations_end"]) for b in batches] == [
        (1, 4),
        (5, 8),
        (9, 12),
        (13, 16),
    ]
    assert all(b["observations"] == 4 and b["tail_mass"] == 1 for b in batches)
    assert sum(b["allocation_calls"] for b in batches) == run["allocation_queries"]
    assert sum(b["cache_hits"] for b in batches) == sum(
        r["cache_hit"] for r in run["observations"]
    )
    assert run["total_observations"] == 16 and run["state_evaluations"] == 4
    assert record["final_eligible"] == batches[-1]["eligible"]
    assert not run["fallback_used"]


def _without_timing(value):
    if isinstance(value, dict):
        return {
            k: _without_timing(v) for k, v in value.items() if k != "elapsed_seconds"
        }
    if isinstance(value, list):
        return [_without_timing(v) for v in value]
    return value


def test_default_and_explicit_none_replay_preserve_legacy_contract():
    spec, ir, h = circuit_fixture()
    a = search(spec, ir, h, evaluations=3, shots=4, final_shots=4)
    b = search(spec, ir, h, evaluations=3, shots=4, final_shots=4, fitting=None)
    assert "fitting_record" not in a and "fitting_record" not in b
    assert _without_timing(a) == _without_timing(b)


@pytest.mark.parametrize(
    "change,kwargs",
    [
        ({"objective_kind": "risk_return"}, {}),
        ({}, {"target": "proxy"}),
        ({}, {"method": "uniform"}),
        ({}, {"method": "swap"}),
    ],
)
def test_opt_in_rejects_unsupported_objective_or_feedback(change, kwargs):
    spec, ir, h = circuit_fixture()
    with pytest.raises(ValueError, match="allocated tracking_cost"):
        search(replace(spec, **change), ir, h, fitting="lower_tail", **kwargs)


def test_all_unknown_allocations_are_not_reported_proven_infeasible(monkeypatch):
    spec, ir, h = circuit_fixture()
    monkeypatch.setattr(
        "agqo.research.budget_search.allocate",
        lambda *args: {
            "status": "unknown",
            "feasible": False,
            "reason": "Controlled solver failure",
        },
    )
    run = search(
        spec, ir, h, fitting="lower_tail", evaluations=3, shots=4, final_shots=4
    )
    assert run["status"] == "unknown" and run["allocation"] is None
    assert not run["fitting_record"]["best_fit_eligible"]
    assert not run["fitting_record"]["final_eligible"]
    assert (
        sum(
            b["status_counts"].get("unknown", 0)
            for b in run["fitting_record"]["batches"]
        )
        == 16
    )


def test_failed_final_gate_does_not_erase_feasible_portfolio_or_fit_status(monkeypatch):
    """Controlled sampling separates final qualification from pooled/fit evidence."""
    spec, ir, h = circuit_fixture()
    calls = 0

    def controlled_execute(basis, *args):
        nonlocal calls
        calls += 1
        state = np.zeros(len(basis.indices), dtype=complex)
        state[0 if calls <= 3 else 1] = 1
        return state

    from agqo.research.symmetry import ConservedBasis

    basis = ConservedBasis(spec, h)
    good_index = int(basis.indices[0]) & ((1 << spec.n) - 1)

    def controlled_allocate(problem, bits):
        index = sum(int(b) << i for i, b in enumerate(bits))
        if index == good_index:
            return {
                "status": "optimal",
                "feasible": True,
                "objective": 0.0,
                "support": list(bits),
            }
        return {"status": "unknown", "feasible": False}

    monkeypatch.setattr(ConservedBasis, "execute", controlled_execute)
    monkeypatch.setattr("agqo.research.budget_search.allocate", controlled_allocate)
    run = search(
        spec, ir, h, fitting="lower_tail", evaluations=3, shots=4, final_shots=4
    )
    record = run["fitting_record"]
    assert record["best_fit_eligible"] and not record["final_eligible"]
    assert record["batches"][-1]["status_counts"] == {"unknown": 4}
    assert run["status"] == "feasible" and run["allocation"]["objective"] == 0
    assert sum(r["feasible"] for r in run["observations"]) == 12
    assert run["total_observations"] == 16
