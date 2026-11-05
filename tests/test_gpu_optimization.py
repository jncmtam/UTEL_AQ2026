from copy import deepcopy
from jsonschema import Draft202012Validator
import pytest

from agqo.research.cloud_pipeline import contexts
from agqo.research.quantum import compile_cost
from agqo.research.edge_program import requests_for, schema
from agqo.research.gpu_optimization import (
    permuted_schema, make_request, random_program, admit_response, selection_key,
)
from agqo.synthesis.profile import digest


def test_permuted_enum_does_not_change_legal_program_domain():
    _, spec = contexts()[0]
    old, new = schema(spec), permuted_schema(spec, 501)
    old_children = old["properties"]["exchanges"]["properties"]
    new_children = new["properties"]["exchanges"]["properties"]
    for key in old_children:
        assert set(old_children[key]["properties"]["edge"]["enum"]) == set(new_children[key]["properties"]["edge"]["enum"])
    assert old != new
    for i in range(5):
        Draft202012Validator(new).validate(random_program(spec, i))


def test_live_feedback_is_hash_bound_without_mutating_source_request():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    budget = {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}
    base = requests_for(spec, h, budget, 500)[1]["request"]
    saved = deepcopy(base)
    history = [{"best_allocated_F": 0.1}]
    value = make_request(base, spec, 0, 1, history)
    assert base == saved
    assert value["payload"]["prior_live_proposals"] == history
    assert value["request_hash"] == digest({k: v for k, v in value.items() if k != "request_hash"})
    with pytest.raises(ValueError, match="history"):
        make_request(base, spec, 0, 2, history)
    answer = {"request_hash": "wrong", "status": "ok", "response": random_program(spec, 1)}
    assert admit_response(answer, value, spec, h, budget)["status"] == "rejected"
    answer["request_hash"] = value["request_hash"]
    value["payload"]["compiled_resource_budget"]["qubits"] += 1
    assert admit_response(answer, value, spec, h, budget)["status"] == "rejected"


def test_frozen_selection_cannot_use_ineligible_or_failed_candidate():
    good = {"status": "completed", "result": {"allocation": {"objective": 0.3}, "fitting_record": {"final_eligible": True}}, "admission": {"verification": {"resources": {"transpiled_depth": 20}}}}
    bad = deepcopy(good)
    bad["result"]["allocation"]["objective"] = 0.1
    bad["result"]["fitting_record"]["final_eligible"] = False
    assert min([bad, good], key=selection_key) is good
    assert selection_key({"status": "failed"})[0] == 1
