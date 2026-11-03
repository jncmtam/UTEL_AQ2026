"""Run with python -m agqo.repair or the agqo-repair entrypoint."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from .benchmark import Protocol, run_benchmark
from .data import fetch_or_library, import_market_csv, parse_or_prices, synthetic_data
from .llm import QwenClient
from .report import create_report
from .workflow import decide


def main():
    parser = argparse.ArgumentParser(description="AGQO mandate-aware tracker repair")
    parser.add_argument("command", choices=["demo", "benchmark", "serve", "fetch-or", "normalize"])
    parser.add_argument("--source", choices=["synthetic", "or-library", "market"], default="synthetic")
    parser.add_argument("--or-file", default="data/repair/indtrack1.txt")
    parser.add_argument("--market-csv"); parser.add_argument("--market-manifest")
    parser.add_argument("--output", default="results/repair")
    parser.add_argument("--llm", choices=["disabled", "modal", "replay"], default="disabled")
    parser.add_argument("--replay-file")
    parser.add_argument("--text", default="Hold 4 assets; Exclude S00; Sector Banks at most 25%; Turnover at most 120%")
    parser.add_argument("--evaluations", type=int, default=32)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--seeds", default="11,23,47")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--export-circuit", action="store_true")
    args = parser.parse_args()
    if args.command == "fetch-or":
        print(fetch_or_library(Path(args.or_file).parent)); return 0
    if args.command == "serve":
        from .server import create_server
        server = create_server(args.port, args.llm, args.output, args.or_file)
        print(f"AGQO Repair: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    if args.source == "or-library":
        data = parse_or_prices(Path(args.or_file).read_text(), expected_n=31)
    elif args.source == "market":
        if not args.market_csv or not args.market_manifest:
            parser.error("market cần --market-csv và --market-manifest")
        data = import_market_csv(args.market_csv, args.market_manifest)
    else:
        data = synthetic_data()
    directory = Path(args.output); directory.mkdir(parents=True, exist_ok=True)
    client = QwenClient(args.llm, args.replay_file, directory / "llm_audit.jsonl")
    if args.command == "normalize":
        m, trace = client.normalize(args.text, data.tickers[:8], tuple(sorted(set(data.sectors[:8]))))
        print(json.dumps({"mandate": None if m is None else m.to_dict(), "trace": trace}, ensure_ascii=False, indent=2)); return 0
    if args.command == "benchmark":
        protocol = Protocol(evaluations=args.evaluations, shots=args.shots, seeds=tuple(int(x) for x in args.seeds.split(",")))
        output = run_benchmark(data, directory, protocol, client, progress=lambda x: print(x, flush=True))
        create_report(output, directory)
        print(str(directory / "REPORT.md")); return 0
    output = decide(data, args.text, client, evaluations=args.evaluations, shots=args.shots, export_circuit=args.export_circuit)
    (directory / "decision.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    for row in output["results"]:
        if "circuit" in row:
            (directory / (row["method"] + ".qasm")).write_text(row["circuit"]["qasm3"])
    print(json.dumps({"status": output["status"], "recommended_method": output.get("recommended_method"), "output": str(directory / "decision.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
