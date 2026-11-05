from copy import deepcopy
from itertools import combinations
import pytest
from agqo.research.cloud_pipeline import contexts
from agqo.research.finance import allocate
from agqo.research.decision_audit import validate_allocation, check_inputs
from agqo.synthesis.profile import digest


def test_cached_financial_values_are_rescored_and_nonoptimal_records_not_reused():
    _, spec = contexts()[0]
    bits = next(bits for group in combinations(range(spec.n), spec.k)
                if spec.feasible(bits := [int(q in group) for q in range(spec.n)]))
    result = allocate(spec, bits)
    assert result["status"] == "optimal"
    index = sum(v << q for q, v in enumerate(bits))
    assert validate_allocation(spec, index, result)
    bad = deepcopy(result)
    bad["objective"] += 1e-4
    with pytest.raises(ValueError, match="reproduce"):
        validate_allocation(spec, index, bad)
    bad = deepcopy(result)
    bad["status"] = "feasible"
    assert not validate_allocation(spec, index, bad)
    assert not validate_allocation(spec, index, {"status": "unknown", "feasible": False})


def test_frozen_cache_and_cases_identity_cannot_be_overwritten_by_protocol():
    value = {"cases": [{"hash": "one"}], "cache": {}}
    value["input_hash"] = digest(value)
    value["protocol"] = {"evidence": "separate control metadata"}
    check_inputs(value)
    value["cases"][0]["hash"] = "two"
    with pytest.raises(ValueError, match="changed"):
        check_inputs(value)
