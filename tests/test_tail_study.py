import json

from agqo.research import tail_study


def test_completed_pilot_guard_does_not_load_data_or_restart_work(tmp_path, monkeypatch):
    completion = {"status": "completed_development_pilot", "completed_runs": 96}
    target = tmp_path / "completion.json"
    target.write_text(json.dumps(completion))

    def forbidden():
        raise AssertionError("A completed pilot must not reload data or restart search.")

    monkeypatch.setattr(tail_study, "prepare_inputs", forbidden)
    result = tail_study.run(tmp_path)
    assert result["replay_guard"] == "retained_no_rerun"
    assert result["status"] == completion["status"]
    assert json.loads(target.read_text()) == completion
