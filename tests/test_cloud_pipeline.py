import io
import zipfile
import hashlib
from dataclasses import replace
import numpy as np
import pytest

from agqo.research.cloud_pipeline import (
    common_program,
    contexts,
    sampled_allocation_search,
    objective_bound,
)
from agqo.research.design import lower, request, schema
from agqo.research.quantum import compile_cost, verify
from scripts.run_modal_pipeline import unpack_verified


def test_common_grammar_locks_preparation_and_keeps_legacy_unchanged():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    program = common_program(spec)
    assert schema(spec)["properties"]["preparation"]["type"] == "array"
    req = request(spec, h, common_preparation=True)
    assert (
        req["schema"]["properties"]["preparation"]["const"]
        == "compiler_counter_dicke_v1"
    )
    ir = lower(program, spec, h, common_preparation=True)
    assert ir["initialization"] == []
    assert ir["preparation"]["kind"] == "dicke_sequential_counter_v1"
    assert verify(ir, spec, h)["valid"]
    program["schedule"] = [0] * len(program["schedule"])
    with pytest.raises(ValueError, match="permutation"):
        lower(program, spec, h, common_preparation=True)


def test_f_feedback_counts_all_shots_caches_and_preserves_target():
    _, spec = contexts()[0]
    h = compile_cost(spec, True)
    ir = lower(common_program(spec), spec, h, common_preparation=True)
    result = sampled_allocation_search(
        spec, ir, h, evaluations=2, shots=8, final_shots=8
    )
    assert result["total_shots"] == 24
    assert result["unique_support_checks"] + result["cache_hits"] == 24
    assert result["allocation_queries"] <= result["unique_support_checks"]
    assert len(result["history"]) == 3
    assert result["allocation"]["feasible"]
    assert not result["fallback_used"]
    weights = result["allocation"]["weights"]
    assert np.isclose(
        spec.metrics_weights(weights)["objective"], result["allocation"]["objective"]
    )
    assert result["allocation"]["objective"] < objective_bound(spec)


def test_uniform_keeps_infeasible_draws_in_denominator():
    _, spec = contexts()[0]
    impossible = replace(spec, maximum_weight=0.2)
    result = sampled_allocation_search(
        impossible, None, None, uniform=True, evaluations=1, shots=16, final_shots=16
    )
    assert result["total_shots"] == 32
    assert result["allocation"] is None
    assert result["allocation_feasible_sample_fraction"] == 0
    assert result["status"] == "unknown"
    assert result["history"][0]["mean_normalized_allocated_loss"] == 2


def zipped(name, content):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, content)
    return {
        "archive": buffer.getvalue(),
        "sha256_files": {name: hashlib.sha256(content).hexdigest()},
    }


def test_download_checks_paths_hashes_and_preserves_local_files(tmp_path):
    unpack_verified(zipped("sub/file.txt", b"verified"), tmp_path)
    with pytest.raises(ValueError, match="overwrite"):
        unpack_verified(zipped("sub/file.txt", b"changed"), tmp_path)
    with pytest.raises(ValueError, match="Unsafe"):
        unpack_verified(zipped("../escape", b"bad"), tmp_path)
    tampered = zipped("other", b"original")
    tampered["sha256_files"]["other"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        unpack_verified(tampered, tmp_path)
