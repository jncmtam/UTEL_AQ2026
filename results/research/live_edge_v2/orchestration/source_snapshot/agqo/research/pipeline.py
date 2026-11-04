"""Checkpointed execution of the reviewed research workflow."""

from pathlib import Path
import json
from .data import audit, write_json, candidate
from .workflow import run_trajectory, artifact_bundle


def execute_pipeline(
    directory, *, mode="offline", data_directory="data/us_equities", periods=2
):
    from .baselines import study
    from agqo.synthesis.profile import digest

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    manifest = candidate(data_directory)
    protocol = {
        "version": "implementation-pipeline-v1.1",
        "mode": mode,
        "periods": periods,
        "data_directory": str(data_directory),
        "dataset_hash": digest(manifest),
        "evidence": "docs/research/IMPLEMENTATION_PROTOCOL.md",
        "no_automatic_model_size_escalation": True,
        "source_hash": digest(
            {f.name: f.read_text() for f in sorted(Path(__file__).parent.glob("*.py"))}
        ),
    }
    target = path / "protocol.json"
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError("Pipeline settings differ from the frozen output directory.")
    write_json(target, protocol)
    stages = (
        json.loads((path / "stages.json").read_text())
        if (path / "stages.json").exists()
        else {}
    )

    def checkpoint(name, action):
        if name in stages:
            result = stages[name]
            if (
                "output" in result
                and not (Path(result["output"]) / "RESULTS.md").exists()
            ):
                raise ValueError(
                    "Checkpoint is incomplete; do not infer success from a stage name."
                )
            return result
        result = action()
        stages[name] = result
        write_json(path / "stages.json", stages)
        return result

    manifest = candidate(data_directory)
    admission = audit(manifest, data_directory)
    write_json(path / "data_audit.json", admission)
    checkpoint(
        "non_llm_baseline", lambda: study(path / "baseline_study", evaluations=12)
    )
    checkpoint(
        "synthetic_trajectory",
        lambda: run_trajectory(
            path / "synthetic_trajectory", periods=periods, evaluations=12
        ),
    )
    checkpoint(
        "market_admission",
        lambda: run_trajectory(
            path / "market_trajectory",
            source="market",
            data_directory=data_directory,
            periods=periods,
        ),
    )
    if mode == "modal":
        from .probe import run_probe

        checkpoint(
            "specialist_interface",
            lambda: run_probe(path / "specialist_interface", mode="modal"),
        )
    elif mode == "replay":
        source = path / "specialist_interface" / "records.json"
        stages["specialist_interface"] = {
            "status": "replayed" if source.exists() else "not_run",
            "source": str(source),
        }
    else:
        stages["specialist_interface"] = {
            "status": "not_run",
            "reason": "Offline mode makes no model calls.",
        }
    write_json(path / "stages.json", stages)
    decisions = [
        json.loads(line)
        for line in (path / "synthetic_trajectory" / "decisions.jsonl")
        .read_text()
        .splitlines()
    ]
    import csv

    with (path / "synthetic_trajectory" / "metrics.csv").open() as stream:
        metrics = list(csv.DictReader(stream))
    result = artifact_bundle(
        path,
        protocol,
        manifest,
        decisions,
        metrics,
        status="completed_with_data_blockers"
        if not admission["financial_evaluation_allowed"]
        else "completed",
        reason="Software stages executed; market conclusions remain blocked until data admission passes. Native probes do not qualify a model.",
        cost={
            "inference_execution": mode,
            "stage_cost_reports": {
                k: str(Path(v["output"]) / "cost_report.json")
                for k, v in stages.items()
                if "output" in v
            },
            "reservation_is_not_invoice": True,
            "no_automatic_model_escalation": True,
        },
    )
    write_json(
        path / "circuits" / "artifact_locations.json",
        {
            "baseline": "../baseline_study/circuits",
            "trajectory": "../synthetic_trajectory/circuits",
        },
    )
    (path / "RESULTS.md").open("a").write(
        "\n## Stage outputs\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in stages.items())
        + "\n"
    )
    return result
