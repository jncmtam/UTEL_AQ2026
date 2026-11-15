"""Correctness checks for the parts every result depends on."""

import json

import numpy as np
import pytest

import pandas as pd

from agqo.backtest import Account, build_rounding_instance, etf_buy_and_hold
from agqo.config import DesignConfig, ExperimentConfig
from agqo.data import MarketData
from agqo.insight import coupling_decomposition, hamiltonian_insight, market_insight
from agqo.llm.client import LLMClient, make_request
from agqo.llm.mock import mock_response
from agqo.llm.tasks import TEST_SET, mandate_matches, parse_mandate, verify_explanation
from agqo.mandate import Mandate, rule_parse
from agqo.portfolio import all_bitstrings, landscape
from agqo.quantum.design import (ScheduleModel, cross_validate, design_card, design_features, designed_spec,
                                 schedule_grid, success_table)
from agqo.stats import block_bootstrap_te_diff, paired_test
from agqo.quantum.simulator import (CompiledProblem, initial_state, run_qaoa, statevector, uniform_reference,
                                    warm_start_only)
from agqo.quantum.spec import DEFAULT_SPEC, CircuitSpec, random_spec, verify

EC = ExperimentConfig()


@pytest.fixture(scope="module")
def market():
    return MarketData.load()


@pytest.fixture(scope="module")
def problem(market):
    md = market
    d = md.rebalance_dates(EC.train_start, EC.train_end)[0]
    uni, _ = md.universe(d, 250, 180)
    inst = build_rounding_instance(md, d, uni, Account(cash=EC.problem.capital_vnd), EC)
    land = landscape(inst)
    return md, inst, land, CompiledProblem(inst, land)


# ---------------------------------------------------------------- formulation
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


def test_rounding_register_adds_one_lot_per_qubit(problem):
    _, inst, _, _ = problem
    x = np.zeros(inst.n_qubits, int)
    x[0] = 1
    diff = inst.shares(x)[0] - inst.base_shares
    assert diff.sum() == inst.rules.lot_size and (diff >= 0).all()


# ---------------------------------------------------------------- phase 1: data insight
def test_coupling_decomposition_reproduces_ising_couplings(problem):
    _, inst, _, cp = problem
    risk, budget = coupling_decomposition(inst)
    off = ~np.eye(cp.n, dtype=bool)
    assert np.abs((risk + budget)[off] - cp.J[off]).max() < 1e-12


def test_insights_are_consistent(problem):
    md, inst, land, cp = problem
    inst.meta["relaxed"] = cp.relaxed
    hi = hamiltonian_insight(cp, EC.problem.success_gap)
    mi = market_insight(md, inst, land, [], EC.problem.lookback_days)
    assert abs(hi.coupling_mass_from_risk + hi.coupling_mass_from_budget - 1) < 1e-9
    assert 1 <= hi.pairs_for_90pct_mass <= hi.n_pairs and 0 <= hi.warm_confidence <= 1
    assert sum(len(c) for c in mi.clusters) == mi.usable and 1 <= mi.effective_bets <= mi.usable
    assert mi.te_exact_pct <= mi.te_nearest_pct + 1e-9 or not land.feasible[cp.reference_index()]
    assert len(mi.register) == cp.n


# ---------------------------------------------------------------- phase 2: insight -> circuit
def test_mass_pruning_keeps_requested_coupling_mass(problem):
    _, _, _, cp = problem
    for mass in (0.5, 0.9, 1.0):
        sel = cp.selected_pairs(mass=mass)
        share = (cp.pair_w[sel] ** 2).sum() / (cp.pair_w ** 2).sum()
        assert share >= mass - 1e-9
        assert len(sel) == 1 or (cp.pair_w[sel[:-1]] ** 2).sum() / (cp.pair_w ** 2).sum() < mass  # fewest pairs


def test_rms_scaling_normalises_coefficients(problem):
    _, _, _, cp = problem
    spec = designed_spec(2, 0.1, 0.9, 0.5, 0.6)
    _, sel, scale = cp.phase_terms(spec)
    coeffs = np.concatenate([cp.hz, cp.pair_w[sel]]) / scale
    assert abs(np.sqrt(np.mean(coeffs ** 2)) - 1) < 1e-12


def test_designed_circuit_is_valid_and_qiskit_agrees(problem):
    _, _, _, cp = problem
    spec = designed_spec(3, 0.1, 0.9, 0.5, 0.6)
    assert verify(spec, cp.n, 1500) == []
    a = np.array([0.1, 0.3, 0.5, 0.5, 0.3, 0.1])
    psi = statevector(cp, spec, a)
    assert abs(np.vdot(psi, psi) - 1) < 1e-10
    pytest.importorskip("qiskit")
    from agqo.quantum.export import check_against_simulator
    assert check_against_simulator(cp, spec, a) < 1e-9
    assert check_against_simulator(cp, DEFAULT_SPEC, a[:4]) < 1e-9


def test_warm_start_only_is_the_product_state(problem):
    _, _, _, cp = problem
    r = warm_start_only(cp, 0.1, 0.05, 512, np.random.default_rng(0))
    spec = CircuitSpec(initial_state="warm_start", warm_start_epsilon=0.1)
    assert np.abs(r.probs - np.abs(initial_state(cp, spec)) ** 2).max() < 1e-12
    assert 0 <= r.better_than_ref <= r.feasible_mass <= 1


def test_designed_circuit_beats_warm_start_and_random_guessing(problem):
    _, _, _, cp = problem
    spec = designed_spec(4, 0.1, 0.9, 0.5, 0.6)
    r = run_qaoa(cp, spec, 0.05, 512, np.random.default_rng(0))
    w = warm_start_only(cp, 0.1, 0.05, 512, np.random.default_rng(0))
    assert r.success_prob > w.success_prob > uniform_reference(cp, 0.05)


def test_schedule_model_and_cross_validation(problem):
    _, _, _, cp = problem
    dc = DesignConfig(layers_grid=(1, 2), epsilon_grid=(0.1,), coupling_mass_grid=(0.9,), dgamma_grid=(0.2, 0.5),
                      dbeta_grid=(0.6,))
    grid = schedule_grid(dc)
    table = success_table([cp, cp], grid, 0.05, 1500, workers=1)
    assert table.shape == (2, 4) and (table >= 0).all() and np.allclose(table[0], table[1])
    feats = pd.DataFrame([design_features(cp), design_features(cp)])
    frozen = ScheduleModel.fit(feats, table, 0)
    assert frozen.choose({}) == int(np.argmax(table.mean(0)))           # k = all -> frozen schedule
    cv = cross_validate(feats, table, np.array([0, 1]), (1, 0))
    assert set(cv.k) == {0, 1} and (cv.cv_success <= table.max() + 1e-12).all()
    spec = designed_spec(2, 0.1, 0.9, 0.5, 0.6)
    card = design_card(cp, spec, design_features(cp))
    assert card["two_qubit_gates"] == 2 * card["R3_couplings"]["kept"] * spec.layers


def test_mandate_changes_universe_and_feasibility(market):
    md = market
    d = md.rebalance_dates(EC.train_start, EC.train_end)[0]
    uni, _ = md.universe(d, 250, 180)
    m = Mandate(exclude_sectors=["Real estate"], sector_caps={"Banking": 0.30}, min_cash_pct=5.0)
    inst = build_rounding_instance(md, d, uni, Account(cash=EC.problem.capital_vnd), EC, m)
    assert not any(md.sector(t) == "Real estate" for t in inst.tickers)
    bank = np.array([md.sector(t) == "Banking" for t in inst.tickers])
    land = landscape(inst)
    W = inst.weights(all_bitstrings(inst.n_qubits))
    assert (W[land.feasible][:, bank].sum(1) <= 0.30 + 1e-9).all()     # every executable choice obeys the cap
    assert (W[:, bank].sum(1) <= 0.30 + 1e-9).all()                    # ...and so does every one of the 2^n states
    assert abs(inst.invest_target - 0.95) < 1e-12


def test_rule_parser_and_mandate_validation():
    tk = {"VIC", "VHM", "SSI"}
    m = rule_parse("Bỏ VIC, ngân hàng tối đa 30%, giữ 5% tiền mặt", tk)
    assert m.exclude_tickers == ["VIC"] and m.sector_caps == {"Banking": 0.3} and m.min_cash_pct == 5.0
    bad, _, errs = parse_mandate({"exclude_tickers": ["XXX"], "exclude_sectors": [], "sector_caps": []}, tk)
    assert bad.is_empty() and errs
    gold = TEST_SET[2][1]
    assert all(mandate_matches(Mandate(sector_caps={"Banking": 0.3001}), gold).values())


def test_explanation_numbers_must_come_from_evidence():
    ev = {"date": "2026-10-01", "trades": [{"ticker": "VCB", "action": "mua", "lots": 2, "value_million_vnd": 10.76}],
          "tracking_error_pct": {"agqo_choice": 2.65}}
    good = {"summary_vi": "Sai số bám 2,65% sau khi mua 2 lô VCB.", "trade_notes": [
        {"ticker": "VCB", "action": "mua", "lots": 2, "reason_vi": "10,76 triệu đồng"}], "risk_notes_vi": ["Rủi ro."]}
    assert verify_explanation(good, ev)["ok"]
    bad = dict(good, summary_vi="Lợi nhuận kỳ vọng 12%.")
    assert verify_explanation(bad, ev)["unverified_numbers"] == ["12"]


def test_statistics():
    a, b = np.array([3.0, 4, 5, 6, 7, 8]), np.array([1.0, 1, 2, 2, 3, 3])
    t = paired_test(a, b)
    assert t["wins"] == 6 and t["ratio_ci_low"] > 1 and t["wilcoxon_p"] < 0.05
    idx = pd.bdate_range("2024-01-01", periods=300)
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(0, 0.002, 300), idx)
    r = block_bootstrap_te_diff(x, 2 * x)
    assert r["diff_pp"] < 0 and r["ci_high"] < 0


def test_verifier_rejects_bad_specs():
    assert verify(DEFAULT_SPEC, 16, 1500) == []
    assert any("warm_x" in e for e in verify(CircuitSpec(mixer="warm_x"), 16, 1500))
    assert any("budget" in e for e in verify(CircuitSpec(layers=6), 16, 500))
    assert any("hamiltonian_scale" in e for e in verify(CircuitSpec(hamiltonian_scale="bad"), 16, 1500))
    rng = np.random.default_rng(0)
    assert all(isinstance(verify(random_spec(rng), 16, 1500), list) for _ in range(20))


# ---------------------------------------------------------------- benchmarks and plumbing
def test_etf_buy_and_hold_is_affordable(market):
    md = market
    if md.etf_close.empty:
        pytest.skip("no ETF data")
    t = md.etf_close.columns[0]
    v, fee = etf_buy_and_hold(md, t, md.index.index[300], md.index.index[-1], EC)
    assert v.iloc[0] <= EC.problem.capital_vnd and v.min() > 0 and fee > 0 and v.notna().all()


def test_llm_client_logs_every_call(tmp_path):
    c = LLMClient("mock", tmp_path / "log.jsonl", mock_fn=mock_response)
    rec = c.generate([make_request("smoke", "s", "u", {"type": "object"})])[0]
    line = json.loads((tmp_path / "log.jsonl").read_text())
    assert rec["execution"] == "mock" and line["execution"] == "mock"


# ---------------------------------------------------------------- judge studies (agqo/extras.py, agqo/visuals.py)
def test_greedy_baseline_buys_affordable_whole_lots(market):
    from agqo.extras import greedy_target

    md = market
    d = md.rebalance_dates(EC.train_start, EC.train_end)[0]
    uni, _ = md.universe(d, 250, 180)
    g = greedy_target(md, d, uni, Account(cash=20e6), EC)
    sh = np.array(list(g.values()))
    spend = (sh * md.px.loc[d, list(g)].to_numpy()).sum()
    assert (sh % EC.rules.lot_size == 0).all() and sh.min() >= 0
    assert 0 < spend * (1 + EC.rules.commission) <= 20e6


def test_odd_lot_break_even_is_where_returns_meet():
    from agqo.visuals import odd_lot_break_even

    rb = pd.DataFrame([
        {"capital_vnd": 1.0, "scenario": "base (0.15% commission, quarterly)", "te_odd_lot": np.nan,
         "return_odd_lot": np.nan, "return_whole_lot_optimum": 10.0},
        *[{"capital_vnd": 1.0, "scenario": f"odd-lot execution, premium {p}%", "te_odd_lot": 1.0,
           "return_odd_lot": 14.0 - 2 * p, "return_whole_lot_optimum": np.nan} for p in (0.0, 1.0, 1.5)]])
    assert abs(odd_lot_break_even(rb)[1.0] - 2.0) < 1e-9
