"""Caller-side helpers for the research notebook: submit to Modal, keep a local copy of each run.

The caller only submits work and writes files. Simulations and benchmarks run in Modal containers.
"""

from __future__ import annotations

import json
from pathlib import Path

from .runlog import RUNS_DIR, git_revision


def revision() -> dict:
    """Revision handed to every Modal function (the container has no .git)."""
    rev = git_revision()
    if rev.get("dirty"):
        print(f"warning: working tree has uncommitted changes on top of {rev['short']}; the run records dirty=true")
    return rev


def keep(result: dict, base: Path = RUNS_DIR) -> Path:
    """Write the files a Modal function returned to results/runs/<run_id>/ and return that path."""
    d = base / result["run_id"]
    for name, text in result["files"].items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return d


def manifest(path: Path) -> dict:
    return json.loads((Path(path) / "run.json").read_text())


def show(path: Path) -> None:
    m = manifest(path)
    print(f"{m['run_id']}: status={m['status']} seconds={m.get('seconds')} errors={len(m['errors'])}")
    for k, v in (m.get("summary") or {}).items():
        print(f"  {k}: {v}")
