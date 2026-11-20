"""Run directories that trace every result to a code revision, an input snapshot and a config.

Layout of one run (local copy under results/runs/, remote copy on the Modal Volume):

    <run_id>/
      run.json          id, kind, git revision, dirty flag, data SHA-256, config, seeds, timings,
                        status ("ok" | "partial" | "failed"), every error message
      log.txt           progress lines
      *.json / *.csv    outputs of the run

run_id = <UTC yyyymmdd-HHMMSS>-<git short sha>-<kind>. Failed and partial runs are kept.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA_DIR, ROOT

RUNS_DIR = ROOT / "results" / "runs"


def git_revision() -> dict:
    """Revision of the source tree. On Modal the tree has no .git: the orchestrator passes it in."""
    env = os.environ.get("AGQO_GIT_REVISION")
    if env:
        return json.loads(env)
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                             text=True).strip())
        return {"sha": sha, "short": sha[:7], "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"sha": "unknown", "short": "unknown", "dirty": None}


def data_sha256(path: Path = DATA_DIR / "ohlcv_daily.csv") -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def new_run_id(kind: str, rev: dict | None = None) -> str:
    rev = rev or git_revision()
    return f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{rev['short']}-{kind}"


@dataclass
class Run:
    """A run directory with a manifest that is rewritten after every step (partial runs stay readable)."""

    kind: str
    base: Path = RUNS_DIR
    config: dict = field(default_factory=dict)
    run_id: str | None = None

    def __post_init__(self):
        self.rev = git_revision()
        self.run_id = self.run_id or new_run_id(self.kind, self.rev)
        self.dir = self.base / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()
        self.manifest = {"run_id": self.run_id, "kind": self.kind, "git": self.rev, "data_sha256": data_sha256(),
                         "config": self.config, "python": platform.python_version(),
                         "host": os.environ.get("MODAL_TASK_ID") and "modal" or platform.node(),
                         "modal_task_id": os.environ.get("MODAL_TASK_ID"),
                         "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "status": "running", "steps": [], "errors": []}
        self._write()

    def log(self, msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with (self.dir / "log.txt").open("a") as f:
            f.write(line + "\n")

    def save(self, name: str, obj) -> Path:
        p = self.dir / name
        if name.endswith(".csv"):
            obj.to_csv(p, index=False)
        else:
            p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=_default))
        return p

    def step(self, name: str, status: str = "ok", **info) -> None:
        self.manifest["steps"].append({"step": name, "status": status, "t_s": round(time.time() - self.t0, 1)} | info)
        self._write()

    def error(self, where: str, exc: BaseException) -> None:
        self.manifest["errors"].append({"where": where, "error": f"{type(exc).__name__}: {exc}",
                                        "traceback": traceback.format_exc()[-4000:]})
        self.log(f"ERROR in {where}: {type(exc).__name__}: {exc}")
        self._write()

    def finish(self, status: str | None = None, **summary) -> dict:
        if status is None:
            status = "partial" if self.manifest["errors"] else "ok"
        self.manifest |= {"status": status, "seconds": round(time.time() - self.t0, 1),
                          "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "summary": summary}
        self._write()
        return self.manifest

    def _write(self) -> None:
        (self.dir / "run.json").write_text(json.dumps(self.manifest, indent=1, ensure_ascii=False, default=_default))


def _default(o):
    if hasattr(o, "item"):
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)
