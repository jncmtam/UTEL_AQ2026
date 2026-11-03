"""Financial correctness, evidence refusal, matched budgets and actual circuit equivalence."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import numpy as np
import pytest

from agqo.repair.benchmark import Protocol, _search, mandate_corpus, evaluate_language
from agqo.repair.circuits import CircuitSpec, compile_diagonal, qiskit_circuit, run_qaoa, simulate
from agqo.repair.data import synthetic_data, make_window, parse_or_prices
from agqo.repair.llm import QwenClient, mandate_request
from agqo.repair.mandates import normalize_rules, validate_mandate
from agqo.repair.model import heldout_metrics
from agqo.repair.server import create_server
from agqo.repair.solvers import exact_solve, milp_solve
from agqo.repair.workflow import decide


def fixture(text="Hold 3 assets", seed=1):
    data = synthetic_data(seed=seed, n=6)
    return make_window(data, n=6, k=3, text=text)[0]


def test_financial_qubo_equals_tracking_and_drifted_trading_cost_for_all_bits():
    p = fixture()
    q = p.objective_qubo()
    assert not np.allclose(p.previous_weights[:3], np.ones(3) / 3, atol=1e-4)
    for bits in product((0, 1), repeat=p.n):
        assert q.energy(bits) == pytest.approx(p.score(bits), abs=1e-14)
    x = np.array([0, 1, 1, 1, 0, 0])
    assert p.metrics_weights(x / p.k)["two_way_turnover"] == pytest.approx(np.abs(x / p.k - p.previous_weights).sum())
    assert p.metrics_weights(x / p.k)["transaction_cost"] == pytest.approx(0.0025 * np.abs(x / p.k - p.previous_weights).sum())


@pytest.mark.parametrize("text", ["Hold 3 assets", "Hold 3 assets; Exclude S00; Must hold S05", "Hold 3 assets; Sector Banks at most 34%", "Hold 3 assets; Turnover at most 90%", "Hold 3 assets; Exclude S00; Turnover at most 1%"])
def test_milp_matches_exhaustive_feasibility_and_global_optimum(text):
    p = fixture(text)
    exact, mip = exact_solve(p), milp_solve(p)
    assert exact["status"] == mip["status"]
    if exact["status"] == "optimal":
        assert exact["objective"] == pytest.approx(mip["objective"], abs=1e-10)
        assert mip["lower_bound"] == pytest.approx(mip["objective"], abs=1e-10)
        assert p.feasible(mip["bits"])


def test_budget_limits_cannot_be_reported_as_infeasible():
    assert exact_solve(fixture(), max_states=1)["status"] == "unknown"
    assert exact_solve(fixture(), time_limit=-1)["status"] == "unknown"


def test_mandates_fail_closed_and_keep_exact_source_evidence():
    p = fixture()
    sectors = tuple(sorted(set(p.sectors)))
    m = normalize_rules("Giữ 3 mã; Loại mã S00; Turnover không quá 120%", p.tickers, sectors)
    assert m.status == "ready" and m.turnover_cap == 1.2
    for evidence in m.evidence:
        assert m.source_text[evidence["start"]:evidence["end"]] == evidence["quote"]
    assert normalize_rules("Hold 3 assets; Avoid risky companies", p.tickers, sectors).status == "needs_clarification"
    assert normalize_rules("Hold 3 assets; Do not exclude S00", p.tickers, sectors).status == "needs_clarification"
    assert normalize_rules("Hold at most 3 assets", p.tickers, sectors).status == "needs_clarification"
    assert normalize_rules("Hold 3 assets; Exclude S00; Must hold S00", p.tickers, sectors).status == "conflict"
    assert normalize_rules("Hold 3 assets; Hold 4 assets", p.tickers, sectors).status == "conflict"
    assert normalize_rules("Hold 3 assets; Cost weight 0.01", p.tickers, sectors).cost_weight == 0.01


def test_llm_cannot_fabricate_offsets_units_boolean_k_or_swallow_unparsed_clauses():
    p = fixture()
    request = mandate_request("Hold 4 assets; Exclude S00", p.tickers, p.sectors)
    validate_mandate(request["example"]["response"], request["example"]["source_text"], p.tickers, p.sectors)
    base = {"constraints": [{"kind": "cardinality", "target": None, "value": True, "start": 0, "end": 13, "quote": "Hold 3 assets"}], "issues": []}
    with pytest.raises(ValueError):
        validate_mandate(base, "Hold 3 assets", p.tickers, p.sectors)
    base["constraints"][0]["value"] = 3
    base["constraints"][0]["end"] = 12
    with pytest.raises(ValueError, match="span"):
        validate_mandate(base, "Hold 3 assets", p.tickers, p.sectors)
    base["constraints"][0].update(end=26, quote="Hold 3 assets; Exclude S00")
    with pytest.raises(ValueError):
        validate_mandate(base, "Hold 3 assets; Exclude S00", p.tickers, p.sectors)


def test_diagonal_oracle_matches_full_hard_constraints_not_cardinality_only():
    p = fixture("Hold 3 assets; Exclude S00; Sector Banks at most 34%")
    oracle = compile_diagonal(p)
    assert np.all(oracle["energies"][~oracle["feasible"]] >= 2)
    assert np.all(oracle["energies"][oracle["feasible"]] <= 1 + 1e-10)
    for i, bits in enumerate(oracle["bits"]):
        assert oracle["feasible"][i] == p.feasible(bits)
        assert oracle["objective"][i] == pytest.approx(p.score(bits))


@pytest.mark.parametrize("spec", [CircuitSpec(), CircuitSpec("XY", "complete", 2, "random"), CircuitSpec("X", "single", 1, "random")])
def test_actual_qiskit_circuit_matches_cpu_statevector(spec):
    pytest.importorskip("qiskit")
    from qiskit.quantum_info import Statevector
    p = fixture("Hold 3 assets; Exclude S00")
    compiled = compile_diagonal(p)
    angles = np.linspace(0.13, 0.8, 2 * spec.depth)
    expected = simulate(p, spec, angles, compiled)
    actual = Statevector.from_instruction(qiskit_circuit(p, spec, angles, compiled)).data
    assert abs(np.vdot(actual, expected)) == pytest.approx(1, abs=1e-10)
    if spec.mixer == "XY":
        cardinal = compiled["bits"].sum(axis=1) == p.k
        assert np.abs(expected[~cardinal]).sum() < 1e-10


def test_qaoa_final_shots_and_search_are_charged_and_reproducible():
    p = fixture()
    a, b = run_qaoa(p, evaluations=3, shots=32), run_qaoa(p, evaluations=3, shots=32)
    assert a["bits"] == b["bits"] and a["angles"] == b["angles"]
    assert a["evaluations"] <= 3
    assert a["total_shots"] == (a["evaluations"] + 1) * 32
    if a["bits"]:
        assert p.feasible(a["bits"])
    protocol = Protocol(n=6, k=3, evaluations=12, shots=32)
    search = _search(p, protocol, 11)
    assert search["total_shots"] <= (protocol.evaluations + 1) * protocol.shots
    assert sum(c["total_shots"] for c in search["search_candidates"]) == search["total_shots"]


def test_future_data_never_changes_problem_or_current_decision():
    data = synthetic_data(n=6)
    p, r, b = make_window(data, n=6, k=3, text="Hold 3 assets")
    data.returns[80:] = 0.3
    changed, _, _ = make_window(data, n=6, k=3, text="Hold 3 assets")
    assert p.fingerprint() == changed.fingerprint()
    assert exact_solve(p)["bits"] == exact_solve(changed)["bits"]
    x = exact_solve(p)["bits"]
    metrics = heldout_metrics(p, np.asarray(x) / p.k, r, b)
    assert len(metrics["net_returns"]) == len(b)
    with pytest.raises(ValueError, match="overlap"):
        Protocol(test_starts=(0,))


def test_or_library_orientation_and_refusal_of_truncated_file():
    # 2 assets, 3 periods; benchmark and each asset occupy separate contiguous rows.
    text = "2 3\n100 110 121 133.1\n10 12 12 15\n20 20 22 22"
    d = parse_or_prices(text)
    assert d.returns.shape == (3, 2)
    assert np.allclose(d.benchmark, 0.1)
    assert np.allclose(d.returns[:, 0], [0.2, 0, 0.25])
    assert d.provenance["periods_per_year"] is None
    with pytest.raises(ValueError):
        parse_or_prices(text.rsplit(" ", 1)[0])


def test_disabled_qwen_is_not_a_rule_fallback_and_corpus_has_independent_gold():
    p = fixture()
    client = QwenClient()
    spec, trace = client.propose(p)
    assert spec is None and trace["status"] == "not_run"
    corpus = mandate_corpus(p.tickers, tuple(sorted(set(p.sectors))), k=3)
    rows = evaluate_language(corpus, p.tickers, tuple(sorted(set(p.sectors))), client)
    assert all(r["status"] == "not_run" and r["correct"] is None for r in rows if r["method"] == "qwen")
    assert next(r for r in rows if r["method"] == "rules" and r["case_id"] == "paraphrase")["correct"] is False


def test_invalid_llm_attempts_remain_in_semantic_and_feasibility_denominators():
    from agqo.repair.report import summarize
    class InvalidClient:
        def normalize(self, *args):
            return None, {"status": "invalid", "reason": "fixture_bad_evidence"}
    p = fixture()
    rows = evaluate_language(mandate_corpus(p.tickers, tuple(sorted(set(p.sectors))), 3), p.tickers, tuple(sorted(set(p.sectors))), InvalidClient())
    assert all(r["correct"] is False for r in rows if r["method"] == "qwen")
    output = {"records": [{"case": {"start": 1, "family": "test"}, "result": {"method": "qwen", "status": "invalid", "feasible": False, "elapsed_seconds": 2}}]}
    assert summarize(output)["methods"][0]["feasible_rate"] == 0


def test_full_decision_workflow_never_recommends_infeasible_targets():
    d = decide(synthetic_data(), "Hold 4 assets; Exclude S00; Turnover at most 120%", evaluations=8, shots=32)
    recommended = next(r for r in d["results"] if r["method"] == d["recommended_method"])
    assert recommended["feasible"] and recommended["trades"][0]["target"] == 0
    assert d["circuit_trace"]["status"] == "not_run"
    no = decide(synthetic_data(), "Hold 4 assets; Exclude S00; Turnover at most 1%", evaluations=8, shots=32)
    assert no["status"] == "infeasible" and no["recommended_method"] is None


def test_local_api_refuses_cross_origin_and_serves_complete_ui(tmp_path):
    server = create_server(0, results_dir=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        assert b"Portfolio Repair Lab" in urlopen(url).read()
        request = Request(url + "/api/normalize", data=json.dumps({"text": "Hold 4 assets"}).encode(), headers={"Content-Type": "application/json"})
        response = json.load(urlopen(request))
        assert response["mandate"]["status"] == "ready"
        request.add_header("Origin", "https://external.example")
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 403
    finally:
        server.shutdown(); server.server_close(); thread.join()
