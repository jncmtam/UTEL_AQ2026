from copy import deepcopy
from agqo.research.cloud_pipeline import contexts
from agqo.research.gpu_optimization import random_program
from agqo.research.counterfactual_editor import neighbors, request
from agqo.research.edge_program import schema, requests_for
from agqo.research.quantum import compile_cost
from agqo.synthesis.profile import digest
from jsonschema import Draft202012Validator


def test_neighbor_controls_are_unique_single_edits_and_keep_every_asset():
    _, spec = contexts()[0]
    current = random_program(spec, 31)
    before = deepcopy(current)
    edits = neighbors(current, spec)
    assert len(edits) == len({digest(e["program"]["exchanges"]) for e in edits}) == 4
    for edit in edits:
        candidate = edit["program"]
        Draft202012Validator(schema(spec)).validate(candidate)
        changes = [k for k in current["exchanges"] if candidate["exchanges"][k] != current["exchanges"][k]]
        assert changes == [edit["patch"]["child"]]
        assert edit["patch"]["old"] == current["exchanges"][changes[0]]
    assert current == before


def test_feedback_ablation_changes_only_counterfactual_information():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    base = requests_for(spec, h, {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}, 1)[1]["request"]
    args = [base, spec, 0]
    current = random_program(spec, 31)
    alternatives = [{"id": "edit0", "measurement": {"best_F": .1}}]
    a = request(*args, "aggregate", current, {"best_F": .2}, alternatives)
    b = request(*args, "counterfactual", current, {"best_F": .2}, alternatives)
    assert a["schema"] == b["schema"] and a["seed"] == b["seed"] and a["system"] == b["system"]
    assert a["payload"]["measured_alternatives"] == []
    assert b["payload"]["measured_alternatives"] == alternatives
    assert a["payload"]["current_actual_program"] == b["payload"]["current_actual_program"]
    assert a["payload"]["architecture_budget"] == {"total_proposals": 1, "remaining_after_this": 0}
    assert "All 3 proposals" not in a["system"]
    assert "linear_z" not in a["payload"]["hamiltonian"]
    assert "linear_z" in base["payload"]["hamiltonian"]
    assert a["payload"]["hamiltonian"]["hamiltonian_hash"] == h["hamiltonian_hash"]
    assert a["request_hash"] != b["request_hash"]
