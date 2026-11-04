"""English CLI for data admission, reviewed experiments and portfolio decisions."""

import argparse, json
from pathlib import Path
from .data import candidate, fetch_prices, audit, write_json
from agqo.synthesis.budget import MODEL_CATALOG


def main():
    parser = argparse.ArgumentParser(
        description="AGQO verified US-equity portfolio research"
    )
    parser.add_argument(
        "command",
        choices=[
            "candidate",
            "fetch",
            "audit",
            "history-audit",
            "smoke",
            "baseline",
            "probe",
            "trajectory",
            "pipeline",
            "replay",
            "serve",
            "published-fetch",
            "published-study",
            "preparation-study",
            "formulation-audit",
            "conditioning-study",
        ],
    )
    parser.add_argument("--data", default="data/us_equities")
    parser.add_argument("--output", default="results/research/pipeline_v1")
    parser.add_argument(
        "--mode", choices=["offline", "modal", "replay"], default="offline"
    )
    parser.add_argument(
        "--models", nargs="+", choices=list(MODEL_CATALOG), default=["quasar4"]
    )
    parser.add_argument(
        "--split", choices=["development", "validation", "test"], default="development"
    )
    parser.add_argument(
        "--ablation",
        choices=["full", "constraints_only", "no_correlation", "shuffled"],
        default="full",
    )
    parser.add_argument(
        "--feedback", choices=["none", "verifier", "quality"], default="quality"
    )
    parser.add_argument(
        "--source", choices=["synthetic", "market"], default="synthetic"
    )
    parser.add_argument("--periods", type=int, default=2)
    parser.add_argument("--evaluations", type=int, default=16)
    parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--proposals", type=int, choices=[1, 4, 8], default=1)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.evaluations < 1 or args.shots < 1 or args.periods < 1:
        parser.error("Budgets and periods must be positive.")
    if args.command == "published-fetch":
        from .published import fetch

        result = fetch(
            "data/published_us" if args.data == "data/us_equities" else args.data
        )
    elif args.command in (
        "published-study",
        "preparation-study",
        "formulation-audit",
        "conditioning-study",
    ):
        if args.command == "conditioning-study":
            from .preparation_study import run_conditioning as published_run
        elif args.command == "formulation-audit":
            from .formulation_study import run as published_run
        elif args.command == "preparation-study":
            from .preparation_study import run as published_run
        else:
            from .published_study import run as published_run

        if args.mode != "offline":
            parser.error(
                "This frozen development command is CPU-only; no Modal inference is dispatched."
            )
        result = published_run(
            args.output,
            "data/published_us" if args.data == "data/us_equities" else args.data,
        )
    elif args.command == "candidate":
        result = candidate(args.data)
    elif args.command == "fetch":
        result = fetch_prices(args.data)
    elif args.command == "audit":
        result = audit(candidate(args.data), args.data)
        write_json(Path(args.data) / "data_audit.json", result)
    elif args.command == "history-audit":
        from .history_audit import run as history_run

        if args.mode != "offline":
            parser.error(
                "Historical hygiene auditing is CPU-only and never dispatches inference."
            )
        result = history_run(args.output, args.data)
    elif args.command == "baseline":
        from .baselines import study

        result = study(args.output, args.evaluations)
    elif args.command == "probe":
        from .probe import run_probe

        if len(args.models) != 1:
            parser.error("A bounded specialist probe accepts one model.")
        result = run_probe(
            args.output,
            "disabled" if args.mode == "offline" else args.mode,
            args.models[0],
        )
    elif args.command == "trajectory":
        from .workflow import run_trajectory

        result = run_trajectory(
            args.output,
            source=args.source,
            data_directory=args.data,
            periods=args.periods,
            evaluations=args.evaluations,
            shots=args.shots,
        )
    elif args.command == "pipeline":
        from .pipeline import execute_pipeline

        result = execute_pipeline(
            args.output, mode=args.mode, data_directory=args.data, periods=args.periods
        )
    elif args.command == "replay":
        from .workflow import ARTIFACTS

        missing = [
            name for name in ARTIFACTS if not (Path(args.output) / name).exists()
        ]
        if missing:
            parser.error("Incomplete artifact contract: " + ", ".join(missing))
        result = {
            "status": "replay_only",
            "output": args.output,
            "inference_calls": 0,
            "report": (Path(args.output) / "RESULTS.md").read_text(),
        }
    elif args.command == "serve":
        from .server import serve

        serve(args.output, args.port)
        return
    else:
        from .runner import run

        result = run(
            args.output,
            args.mode,
            tuple(args.models),
            evaluations=args.evaluations,
            shots=args.shots,
            proposals=args.proposals,
            split=args.split,
            ablation=args.ablation,
            feedback=args.feedback,
        )
    print(json.dumps(result, indent=2, allow_nan=False))
    return (
        2
        if result.get("status") in ("blocked", "completed_with_data_blockers", "failed")
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
