from dataclasses import replace
import json
import numpy as np
import pytest
from agqo.research.finance import (
    FinancialSpec,
    allocate,
    audit_proxy,
    Account,
    diagnose,
    joint_reference,
)
from agqo.research.quantum import compile_cost, cost_values, verify
from agqo.research.design import baseline, lower
from agqo.research.data import candidate, audit


def fixture(n=6):
    rng = np.random.default_rng(12)
    r = rng.normal(0, 0.01, (80, n))
    b = r.mean(axis=1)
    return FinancialSpec(
        tuple(f"S{i}" for i in range(n)),
        tuple("A" if i < n // 2 else "B" for i in range(n)),
        r,
        b,
        np.r_[np.ones(3) / 3, np.zeros(n - 3)],
        3,
        "2020-01-01",
        sector_count_caps={"A": 2},
        sector_weight_caps={"A": 0.7},
        maximum_weight=0.6,
    )


def test_direct_ising_every_state_and_penalty():
    p = fixture()
    h = compile_cost(p)
    for index in range(1 << h["qubits"]):
        x = (index >> np.arange(h["qubits"])) & 1
        objective = p.score(x[: p.n]) / h["objective_scale"]
        penalty = sum(
            h["penalty"]
            * (sum(a * x[int(i)] for i, a in e["coefficients"].items()) - e["target"])
            ** 2
            for e in h["equalities"]
        )
        assert cost_values(h, [index])[0] == pytest.approx(
            objective + penalty, abs=1e-10
        )
    values = cost_values(h, np.arange(1 << h["qubits"]))
    best = int(np.argmin(values))
    assert p.feasible((best >> np.arange(p.n)) & 1)
    assert "energies" not in h


def test_compilation_scales_without_truth_table():
    p = fixture(30)
    h = compile_cost(p)
    assert h["asset_qubits"] == 30 and len(h["quadratic_zz"]) <= h["qubits"] ** 2


def test_independent_quantum_verifier_and_faults():
    p = fixture()
    h = compile_cost(p)
    ir = lower(baseline(p), p, h)
    v = verify(ir, p, h)
    assert v["valid"], v
    h["linear_z"][0] += 0.1
    assert not verify(ir, p, h)["valid"]


def test_schema_prevents_disconnected_tree_and_bad_schedule():
    p = fixture()
    h = compile_cost(p)
    pr = baseline(p)
    pr["parents"]["p2"] = 2
    with pytest.raises(Exception):
        lower(pr, p, h)
    pr = baseline(p)
    pr["schedule"] = [0] * 5
    with pytest.raises(ValueError):
        lower(pr, p, h)


def test_allocator_preserves_support_and_proxy_audit():
    p = fixture()
    x = np.array([1, 1, 0, 1, 0, 0])
    a = allocate(p, x)
    assert a["feasible"]
    assert np.array_equal(np.array(a["weights"]) > 1e-7, x.astype(bool))
    assert not p.violations_weights(a["weights"])
    report = audit_proxy(p)
    assert report["status"] == "complete"
    assert (
        report["proxy_optimum_allocation_regret"] is None
        or report["proxy_optimum_allocation_regret"] >= -1e-7
    )
    joint = joint_reference(p)
    assert joint["status"] == "optimal"
    assert joint["allocation"]["objective"] == pytest.approx(
        report["best_allocated_objective"], abs=1e-7
    )


def test_mandatory_exit_conflict_and_turnover_units():
    p = replace(fixture(), exclude=("S0",), turnover_cap=0.05)
    assert diagnose(p)["status"] == "infeasible"
    metrics = p.metrics_weights(np.array([0, 1 / 3, 1 / 3, 1 / 3, 0, 0]))
    assert metrics["one_way_turnover"] == pytest.approx(1 / 3)
    assert metrics["two_way_turnover"] == pytest.approx(2 / 3)


def test_self_financing_and_drift_and_zero_return_bankruptcy():
    account = Account(np.array([50000.0, 50000.0]))
    first = account.rebalance([0.8, 0.2], 0.001)
    assert first["nav_after"] + first["fee_dollars"] == pytest.approx(100000.0)
    account.advance_total_return([0.1, -0.1])
    assert account.weights()[0] > 0.8
    before = account.nav
    account.apply_action(np.array([[0.5, 0], [0, 1.0]]), np.array([0.5, 0]))
    assert account.nav == pytest.approx(before)
    assert account.cash > 0
    account.advance_total_return([-1, 0])
    assert account.holdings[0] == 0


def test_data_gate_rejects_unaudited_market_and_tampering(tmp_path):
    m = candidate(tmp_path)
    assert not audit(m, tmp_path)["financial_evaluation_allowed"]
    (tmp_path / "source.txt").write_text("changed")
    m["files"] = [
        {"path": "source.txt", "sha256": "wrong", "source": "https://example.org"}
    ]
    assert any("altered" in x for x in audit(m, tmp_path)["issues"])


def test_continuous_walkforward_lag_no_reset_or_future_data():
    from agqo.research.walkforward import walk_forward

    r = np.full((14, 3), 0.01)
    b = r.mean(axis=1)
    dates = [f"2020-01-{i + 1:02}" for i in range(14)]
    seen = []

    def selector(spec):
        seen.append(spec)
        return {"feasible": True, "status": "feasible", "weights": [1 / 3] * 3}

    out = walk_forward(
        r,
        b,
        dates,
        ("A", "B", "C"),
        ("S", "S", "S"),
        selector,
        k=3,
        lookback=3,
        interval=3,
    )
    assert out["account_reset_count"] == 0
    assert out["decisions"][0]["execution_date"] > out["decisions"][0]["signal_date"]
    assert out["daily"][0]["net_return"] == 0
    assert out["final_nav"] > 100000
    assert seen[0].previous_weights.sum() == 0
    assert seen[1].previous_weights.sum() == pytest.approx(1)
    assert all(len(s.returns) == 3 for s in seen)


def test_certified_penalty_omission_and_dicke_reference():
    from agqo.research.baselines import with_dicke

    p = replace(fixture(), include=("S0",), exclude=("S5",))
    full = compile_cost(p)
    reduced = compile_cost(p, constrained_subspace=True)
    states = np.arange(1 << full["qubits"])
    bits = (states[:, None] >> np.arange(p.n)) & 1
    mask = (bits.sum(axis=1) == p.k) & (bits[:, 0] == 1) & (bits[:, 5] == 0)
    assert np.allclose(
        cost_values(full, states[mask]), cost_values(reduced, states[mask])
    )
    ir = with_dicke(lower(baseline(p), p, reduced), p)
    assert verify(ir, p, reduced)["valid"]
    ir["layers"][0]["mixer"][0]["qubits"] = [0, 2]
    assert not verify(ir, p, reduced)["valid"]


def test_adaptive_search_reports_every_gradient_evaluation():
    from agqo.research.baselines import gradient_adaptive

    p = fixture()
    h = compile_cost(p, True)
    ir, report = gradient_adaptive(p, h, steps=2, angle_evaluations=4)
    assert report["gradient_energy_evaluations"] == 2 * (15 + 14)
    assert report["angle_energy_evaluations"] == 8
    assert verify(ir, p, h)["valid"]


def test_native_probe_checks_semantics_not_printed_claims():
    from agqo.research.probe import check_native

    assert check_native(
        'OPENQASM 3.0; include "stdgates.inc"; qubit[2] q; h q[0]; cx q[0],q[1];',
        "bell",
    )["valid"]
    assert not check_native(
        'OPENQASM 3.0; include "stdgates.inc"; qubit[2] q; h q[0];', "bell"
    )["valid"]
    with pytest.raises(ValueError):
        check_native('OPENQASM 3.0; include "elsewhere"; qubit[2] q;', "bell")


def test_financial_constraint_identity_is_immutable():
    p = fixture()
    old = p.fingerprint()
    with pytest.raises(TypeError):
        p.sector_count_caps["A"] = 0
    assert p.fingerprint() == old


def test_market_block_emits_complete_contract(tmp_path):
    from agqo.research.workflow import run_trajectory, ARTIFACTS

    candidate(tmp_path / "data")
    result = run_trajectory(
        tmp_path / "result", source="market", data_directory=tmp_path / "data"
    )
    assert result["status"] == "blocked"
    assert all((tmp_path / "result" / name).exists() for name in ARTIFACTS)


def test_synthetic_trajectory_emits_continuous_accounts(tmp_path):
    from agqo.research.workflow import run_trajectory

    result = run_trajectory(
        tmp_path,
        periods=1,
        methods=("joint_scip", "allocation_swap"),
        evaluations=4,
        shots=16,
    )
    assert result["status"] == "completed"
    records = [
        json.loads(line)
        for line in (tmp_path / "decisions.jsonl").read_text().splitlines()
    ]
    assert records and all(
        row["execution_date"] > row["signal_date"]
        for row in records
        if row["execution_status"] == "executed"
    )


def test_hold_does_not_rebalance_drift_and_mandate_changes_persist():
    from agqo.research.walkforward import walk_forward

    r = np.tile([0.01, -0.005, 0.0, 0.0], (14, 1))
    dates = [f"2020-01-{i + 1:02}" for i in range(14)]
    seen = []

    def selector(spec):
        seen.append(spec.exclude)
        return {
            "feasible": not spec.violations_weights(spec.previous_weights),
            "weights": spec.previous_weights.tolist(),
            "action": "hold",
        }

    result = walk_forward(
        r,
        np.zeros(14),
        dates,
        ("A", "B", "C", "D"),
        ("S", "S", "S", "S"),
        selector,
        k=3,
        lookback=3,
        interval=3,
        initial_weights=[1 / 3] * 3 + [0],
        mandates={dates[6]: {"exclude": ("A",)}},
    )
    assert result["decisions"][0]["execution_status"] == "held"
    assert all(row["execution_status"] == "no_order" for row in result["decisions"][1:])
    assert result["daily"][-1]["weights"][0] > 1 / 3
    assert seen[0] == () and seen[1] == seen[2] == ("A",)


def test_common_postprocessing_counts_queries_and_preserves_support():
    from agqo.research.runner import postprocess_samples

    p = fixture()
    samples = [11, 11, 19, 35, 7]
    result = postprocess_samples(p, samples, budget=2)
    assert result["allocation_queries"] <= 2
    assert result["feasible"]
    assert p.feasible(result["support"])


def test_paired_statistics_do_not_claim_significance_from_three_sizes():
    from agqo.research.statistics import paired_summary, holm_adjust

    result = paired_summary([[1, 2], [1, 2], [1, 2]])
    assert result["cases"] == 3 and result["status"] == "descriptive_small_sample"
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_invalid_replayed_design_is_reported_without_fallback():
    from agqo.research.workflow import solve_decision

    p = fixture()
    pr = baseline(p)
    pr["parents"]["p1"] = 4
    result = solve_decision(p, "qaoa_reuse", program=pr)
    assert not result["feasible"] and result["status"] == "unknown"


def test_modal_prefetch_budget_failure_is_recorded_without_dispatch(
    tmp_path, monkeypatch
):
    from agqo.synthesis.client import SynthesisClient

    client = SynthesisClient("quasar4", "modal", tmp_path, prefetch=True)

    def fail():
        raise ValueError("Budget exhausted before dispatch.")

    monkeypatch.setattr(client, "prefetch_weights", fail)
    monkeypatch.setattr(
        "agqo.synthesis.client.billing_snapshot",
        lambda: pytest.fail("No billing or GPU call after failed prefetch."),
    )
    records = client.batch([{"request_hash": "unit-test-no-gpu", "payload": "probe"}])
    assert records[0]["status"] == "blocked"
    assert records[0]["execution"] == "not_dispatched"
    assert (tmp_path / "preflight_failures.jsonl").exists()
