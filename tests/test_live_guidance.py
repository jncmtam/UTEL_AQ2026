from copy import deepcopy
import pytest
from agqo.research.cloud_pipeline import contexts
from agqo.research.quantum import compile_cost
from agqo.research.live_guidance import paired_requests, evaluate
from agqo.synthesis.profile import digest


def test_guidance_ablation_changes_only_system_with_matching_schema_and_context():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    before = deepcopy(h)
    arms = paired_requests(
        spec, h, {"qubits": 10, "transpiled_cx": 130, "transpiled_depth": 255}, 100
    )
    a, b = [v["request"] for v in arms]
    assert a["payload"] == b["payload"]
    assert a["schema"] == b["schema"]
    assert a["seed"] == b["seed"]
    assert a["system"] in b["system"] and a["system"] != b["system"]
    assert "depth1..2" not in b["system"]
    assert "preparation exchange edges" not in b["system"]
    assert h == before
    for r in (a, b):
        assert r["request_hash"] == digest(
            {k: v for k, v in r.items() if k != "request_hash"}
        )
        assert r["schema"]["properties"]["depth"] == {"const": 1}


def test_cloud_evaluation_refuses_changed_input_before_any_search(tmp_path):
    with pytest.raises(ValueError, match="changed"):
        evaluate(tmp_path / "fresh", {"inputs_hash": "wrong", "cases": []}, [])
    assert not (tmp_path / "fresh").exists()
