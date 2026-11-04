from copy import deepcopy
import pytest
from jsonschema import ValidationError
from agqo.research.cloud_pipeline import contexts
from agqo.research.quantum import compile_cost
from agqo.research.edge_program import VERSION, schema, requests_for, normalize, admit
from agqo.synthesis.typed import domain
from agqo.synthesis.decoding import decoder_schema


def fixture(spec):
    free = domain(spec)["free_qubits"]
    return {
        "version": VERSION,
        "depth": 1,
        "preparation": "compiler_counter_dicke_v1",
        "exchanges": {
            f"p{i}": {"edge": f"EDGE_{free[i - 1]}_{free[i]}", "group": i % 2}
            for i in range(1, len(free))
        },
        "explanation": {
            k: "Software fixture, not model output."
            for k in ("connections", "sharing", "falsifier")
        },
    }


def test_decoder_contract_has_no_unsupported_uniqueness_or_redundant_citations():
    _, spec = contexts()[0]
    s = schema(spec)
    assert decoder_schema(s) == s
    assert "parents" not in s["properties"] and "evidence" not in s["properties"]
    a, b = [
        x["request"]
        for x in requests_for(
            spec,
            compile_cost(spec, True),
            {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255},
            100,
        )
    ]
    assert a["payload"] == b["payload"] and a["schema"] == b["schema"]
    assert a["system"] != b["system"] and a["seed"] == b["seed"]


def test_single_edge_choice_maps_exactly_to_connected_exchange_and_source_map():
    _, spec = contexts()[0]
    program = fixture(spec)
    old = deepcopy(program)
    value = normalize(program, spec)
    assert program == old
    assert value["parents"] == {f"p{i}": i - 1 for i in range(1, spec.n)}
    assert sorted(value["schedule"]) == list(range(spec.n - 1))
    budget = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}
    h = compile_cost(spec, True)
    request = requests_for(spec, h, budget, 100)[1]["request"]
    result = admit(program, spec, h, budget, request)
    assert result["status"] == "accepted" and not result["fallback_used"]
    assert result["source_map"]["LLM"] == ["exchange_edge_ids", "beta_sharing"]
    assert result["gate_ir"]["hamiltonian_hash"] == h["hamiltonian_hash"]


def test_wrong_edge_or_extra_model_schedule_is_rejected_without_repair():
    _, spec = contexts()[1]
    program = fixture(spec)
    program["exchanges"]["p1"]["edge"] = "EDGE_0_1"
    with pytest.raises(ValidationError):
        normalize(program, spec)
    program = fixture(spec)
    program["schedule"] = [0]
    with pytest.raises(ValidationError):
        normalize(program, spec)
