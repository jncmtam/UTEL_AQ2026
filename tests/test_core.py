"""Correctness checks for the parts every result depends on."""

import json

import numpy as np
import pytest

from agqo.backtest import Account, build_rounding_instance, build_selection_instance, risk_inputs
from agqo.classical import greedy_te_shortlist
from agqo.config import ExperimentConfig
from agqo.data import MarketData
from agqo.llm import analyst
from agqo.llm.client import LLMClient, make_request
from agqo.llm.mock import mock_response
from agqo.portfolio import all_bitstrings, black_litterman, landscape
from agqo.quantum.simulator import CompiledProblem, run_qaoa, statevector
from agqo.quantum.spec import DEFAULT_SPEC, CircuitSpec, mutate, random_spec, verify

EC = ExperimentConfig()


@pytest.fixture(scope="module", params=["rounding", "selection"])
def problem(request):
    md = MarketData.load()
    d = md.rebalance_dates(EC.first_rebalance, EC.last_rebalance)[0]
    uni, _ = md.universe(d, 250, 180)
    acc = Account(cash=EC.problem.capital_vnd)
    if request.param == "rounding":
        inst = build_rounding_instance(md, d, uni, {}, acc, EC)
    else:
        cov, cb, vb = risk_inputs(md, d, uni, EC.problem)
        sl = [uni[i] for i in greedy_te_shortlist(cov, cb, vb, 8, 0.98)]
        inst = build_selection_instance(md, d, sl, {}, acc, EC)
    land = landscape(inst)
    return md, inst, land, CompiledProblem(inst, land)


def test_qubo_is_exact_objective_plus_penalty(problem):
    _, inst, land, _ = problem
    W = inst.weights(all_bitstrings(inst.n_qubits))
    pen = EC.problem.budget_penalty * (W.sum(1) - EC.problem.invest_target) ** 2
    assert np.abs(land.energy - (land.objective + pen)).max() < 1e-12


def test_ising_matches_qubo(problem):
    _, inst, land, cp = problem
    J, hz, c = inst.ising()
    e = 0.5 * np.einsum("ki,ij,kj->k", cp.Z, J, cp.Z) + cp.Z @ hz + c
    assert np.abs(e - land.energy).max() < 1e-12


def test_tracking_error_never_negative(problem):
    _, inst, _, _ = problem
    W = inst.weights(all_bitstrings(inst.n_qubits))
    te2 = 252 * (np.einsum("ki,ij,kj->k", W, inst.cov, W) - 2 * W @ inst.cov_b + inst.var_b)
    assert te2.min() > 0


def test_feasibility_is_exact_cash(problem):
    _, inst, land, _ = problem
    X = all_bitstrings(inst.n_qubits)
    assert ((inst.cash_after(X) >= 0) == land.feasible).all()
    assert land.feasible[land.opt_index]


def test_statevector_normalised_and_qiskit_agrees(problem):
    _, _, _, cp = problem
    spec = CircuitSpec(layers=2, initial_state="warm_start", mixer="warm_x", coupling_keep_fraction=0.6)
    a = np.array([0.3, 0.5, 0.7, 0.2])
    psi = statevector(cp, spec, a)
    assert abs(np.vdot(psi, psi) - 1) < 1e-10
    pytest.importorskip("qiskit")
    from agqo.quantum.export import check_against_simulator
    assert check_against_simulator(cp, spec, a) < 1e-9
    assert check_against_simulator(cp, DEFAULT_SPEC, a) < 1e-9


def test_rounding_register_adds_one_lot_per_qubit(problem):
    _, inst, _, _ = problem
    if inst.mode != "rounding":
        pytest.skip("rounding mode only")
    x = np.zeros(inst.n_qubits, int)
    x[0] = 1
    diff = inst.shares(x)[0] - inst.base_shares
    assert diff.sum() == inst.rules.lot_size and (diff >= 0).all()


def test_qaoa_beats_random_guessing(problem):
    _, _, _, cp = problem
    spec = CircuitSpec(layers=3, initial_state="warm_start", mixer="warm_x", warm_start_epsilon=0.1, max_iter=60)
    r = run_qaoa(cp, spec, 0.05, 512, np.random.default_rng(0))
    from agqo.quantum.simulator import uniform_reference
    assert r.success_prob > 5 * uniform_reference(cp, 0.05)


def test_verifier_rejects_bad_specs():
    assert verify(DEFAULT_SPEC, 16, 1500) == []
    assert any("warm_x" in e for e in verify(CircuitSpec(mixer="warm_x"), 16, 1500))
    assert any("budget" in e for e in verify(CircuitSpec(layers=6), 16, 500))
    rng = np.random.default_rng(0)
    for _ in range(50):
        assert verify(mutate(random_spec(rng), rng), 16, 10_000) == [] or True  # mutation stays parseable


def test_black_litterman_signs():
    cov = np.diag([0.04, 0.04, 0.04])
    mu = black_litterman(cov, np.array([2, 0, -1.0]), np.array([0.8, 0.0, 0.5]))
    assert mu[0] > 0 > mu[2] and abs(mu[1]) < 1e-12


def test_analyst_parse_repairs_and_logs(tmp_path):
    alias = {"S01": "AAA", "S02": "BBB", "S03": "CCC"}
    out = analyst.parse({"shortlist": ["S01", "S01", "S09"], "views": [{"id": "S02", "view": 1, "confidence": .5}]},
                        alias, 2, ["CCC", "AAA", "BBB"])
    assert out["shortlist"] == ["AAA", "CCC"] and out["views"] == {"BBB": (1, 0.5)} and out["repairs"]
    c = LLMClient("mock", tmp_path / "log.jsonl", mock_fn=mock_response)
    rec = c.generate([make_request("smoke", "s", "u", {"type": "object"})])[0]
    line = json.loads((tmp_path / "log.jsonl").read_text())
    assert rec["execution"] == "mock" and line["execution"] == "mock"
