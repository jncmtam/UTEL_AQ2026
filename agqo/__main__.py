"""Command line.

  python -m agqo download                                        # keyless VN30 stocks, indices and ETFs
  python -m agqo run --out results/baseline                      # data insight -> designed QAOA -> backtest
  python -m agqo report --runs results/baseline
  python -m agqo smoke-llm --llm modal --model coder30           # one tiny live request
  python -m agqo hardware --qasm results/baseline/circuits/<arm>_<date>.qasm [--confirm]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from .config import ExperimentConfig


def main() -> None:
    ap = argparse.ArgumentParser(prog="agqo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--rounds", type=int)
    r.add_argument("--proposals", type=int)
    rep = sub.add_parser("report")
    rep.add_argument("--runs", type=Path, nargs="+", required=True)
    rep.add_argument("--out", type=Path, default=Path("docs/figures"))
    s = sub.add_parser("smoke-llm")
    s.add_argument("--llm", choices=["modal", "openai"], default="modal")
    s.add_argument("--model", default="coder30")
    h = sub.add_parser("hardware")
    h.add_argument("--qasm", type=Path, required=True)
    h.add_argument("--backend", default="ibm_kingston")
    h.add_argument("--shots", type=int, default=2000)
    h.add_argument("--confirm", action="store_true")
    h.add_argument("--out", type=Path, default=Path("results/hardware_run.json"))
    dl = sub.add_parser("download")
    dl.add_argument("--start", default="2022-01-01")
    dl.add_argument("--end", default=None, help="last day (default: today)")
    a = ap.parse_args()

    if a.cmd == "download":
        from .download import download
        download(start=a.start, end=a.end)
    elif a.cmd == "run":
        from .experiment import run

        ec = ExperimentConfig()
        if a.rounds or a.proposals:
            ec = dataclasses.replace(ec, search=dataclasses.replace(
                ec.search, rounds=a.rounds or ec.search.rounds,
                proposals_per_round=a.proposals or ec.search.proposals_per_round))
        run(a.out, ec)
    elif a.cmd == "report":
        from .report import build_report
        build_report(a.runs, a.out)
    elif a.cmd == "smoke-llm":
        from .llm.client import LLMClient, make_request

        c = LLMClient(a.llm, Path("results/smoke/llm_log.jsonl"), model=a.model)
        schema = {"type": "object", "properties": {"answer": {"type": "integer"}, "why": {"type": "string"}},
                  "required": ["answer", "why"], "additionalProperties": False}
        rec = c.generate([make_request("smoke", "Answer in JSON.", "How many qubits does a 3-asset, "
                                       "2-bit-per-asset register need?", schema, max_tokens=128)])[0]
        print(json.dumps({k: rec[k] for k in ("status", "parsed", "model", "execution", "usage")}, indent=2))
    elif a.cmd == "hardware":
        from .quantum.hardware import run_on_ibm

        rec = run_on_ibm(a.qasm, a.backend, a.shots, a.confirm, a.out)
        print(json.dumps({k: v for k, v in rec.items() if k != "counts"}, indent=2))


if __name__ == "__main__":
    main()
