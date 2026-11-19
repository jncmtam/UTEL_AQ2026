"""Command line. The full pipeline, in order:

  python -m agqo download                       # keyless VN30 members, indices and ETFs (data/vn30)
  python -m agqo mandates --llm modal           # LLM mandate compiler vs keyword rules (35 instructions)
  python -m agqo run                            # training, AI-guided QAOA, walk-forward, statistics (CPU)
  python -m agqo explain --llm modal            # Vietnamese explanations with number verification
  python -m agqo extras                         # hardware, scaling, robustness, distributions (CPU)
  python -m agqo report                         # figures + docs/RESULTS.md

`--llm replay` re-reads results/final/llm/llm_log.jsonl (no GPU); `--llm none` skips the LLM.
  python -m agqo hardware --qasm results/final/circuits/<file>.qasm [--confirm]   # optional IBM run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .config import RESULTS_DIR, ExperimentConfig


def _client(kind: str, out: Path):
    if kind == "none":
        return None
    from .llm.client import LLMClient

    log = out / "llm" / "llm_log.jsonl"
    if kind == "replay":        # read the live log, write the replayed calls to a separate file
        return LLMClient("replay", out / "llm" / "llm_log.replay.jsonl", replay_from=log)
    return LLMClient(kind, log)


def main() -> None:
    ap = argparse.ArgumentParser(prog="agqo")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--start", default="2022-01-01")
    dl.add_argument("--end", default=None, help="last day (default: today)")
    for name in ("mandates", "explain"):
        p = sub.add_parser(name)
        p.add_argument("--llm", choices=["modal", "replay", "none"], default="modal")
        p.add_argument("--out", type=Path, default=RESULTS_DIR)
    r = sub.add_parser("run")
    r.add_argument("--out", type=Path, default=RESULTS_DIR)
    ex = sub.add_parser("extras")
    ex.add_argument("--run", type=Path, default=RESULTS_DIR)
    rep = sub.add_parser("report")
    rep.add_argument("--run", type=Path, default=RESULTS_DIR)
    rep.add_argument("--out", type=Path, default=Path("docs/figures"))
    h = sub.add_parser("hardware")
    h.add_argument("--qasm", type=Path, required=True)
    h.add_argument("--backend", default="ibm_kingston")
    h.add_argument("--shots", type=int, default=2000)
    h.add_argument("--confirm", action="store_true")
    h.add_argument("--out", type=Path, default=Path("results/hardware_run.json"))
    a = ap.parse_args()

    if a.cmd == "download":
        from .download import download
        download(start=a.start, end=a.end)
    elif a.cmd == "mandates":
        from .data import MarketData
        from .llm.tasks import evaluate_mandates

        md = MarketData.load()
        res = evaluate_mandates(_client(a.llm, a.out), {t: md.sector(t) for t in md.close.columns})
        (a.out / "llm").mkdir(parents=True, exist_ok=True)
        (a.out / "llm" / "mandate_eval.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        print(json.dumps(res["score"], indent=2))
    elif a.cmd == "run":
        from .experiment import run
        run(a.out, ExperimentConfig())
    elif a.cmd == "explain":
        from .llm.tasks import describe_evidence, explain_request, verify_explanation

        evidence = [describe_evidence(e) for e in json.loads((a.out / "evidence.json").read_text())]
        (a.out / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False))
        recs = _client(a.llm, a.out).generate([explain_request(e, seed=i) for i, e in enumerate(evidence)])
        rows = []
        for e, rec in zip(evidence, recs):
            p = rec["parsed"] if rec["status"] == "ok" else None
            rows.append({"date": e["date"], "explanation": p, "check": verify_explanation(p, e),
                         "usage": rec["usage"], "model": rec["model"], "execution": rec["execution"]})
        score = {"explanations": len(rows),
                 "all_numbers_verified": sum(not r["check"]["unverified_numbers"] and not r["check"]["trade_mismatches"]
                                             for r in rows),
                 "context_issues": sum(len(r["check"].get("context_issues", [])) for r in rows),
                 "faithful_pct": 100 * sum(r["check"]["ok"] for r in rows) / len(rows)}
        (a.out / "llm" / "explanations.json").write_text(json.dumps({"score": score, "rows": rows}, indent=1,
                                                                    ensure_ascii=False))
        print(json.dumps(score, indent=2))
    elif a.cmd == "extras":
        from .extras import run_extras
        run_extras(a.run)
    elif a.cmd == "report":
        from .report import build_report
        build_report(a.run, a.out)
    elif a.cmd == "hardware":
        from .quantum.hardware import run_on_ibm

        rec = run_on_ibm(a.qasm, a.backend, a.shots, a.confirm, a.out)
        print(json.dumps({k: v for k, v in rec.items() if k != "counts"}, indent=2))


if __name__ == "__main__":
    main()
