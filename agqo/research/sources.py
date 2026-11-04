"""Archive actual source bytes so an uncommitted experiment is reproducible."""

from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import platform
import shutil
from .data import sha, write_json


def capture_sources(directory):
    root = Path(__file__).resolve().parents[2]
    output = Path(directory) / "source_snapshot"
    files = sorted((root / "agqo").rglob("*.py"))
    files += [
        root / "pyproject.toml",
        root / "requirements-lock.txt",
        root / "docs/research/COMPLETION_PROTOCOL.md",
        root / "docs/research/PREPARATION_PROTOCOL.md",
        root / "docs/research/FORMULATION_PROTOCOL.md",
        root / "docs/research/CONDITIONING_PROTOCOL.md",
        root / "docs/research/QUALIFICATION_PROTOCOL.md",
        root / "docs/research/DELIVERY_VISUAL_PROTOCOL.md",
        root / "docs/research/MODAL_E2E_PROTOCOL.md",
        root / "docs/research/IMPROVEMENT_PROTOCOL.md",
    ]
    manifest = {"python": platform.python_version(), "files": {}, "packages": {}}
    for source in files:
        relative = source.relative_to(root)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest["files"][str(relative)] = sha(target)
    for package in (
        "numpy",
        "scipy",
        "pandas",
        "cvxpy",
        "pyscipopt",
        "qiskit",
        "rdata",
        "exchange_calendars",
    ):
        try:
            manifest["packages"][package] = version(package)
        except PackageNotFoundError:
            manifest["packages"][package] = "unavailable"
    write_json(output / "manifest.json", manifest)
    return manifest
