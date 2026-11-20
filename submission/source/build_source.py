"""Export the committed source (git archive) without the market price file or generated files.

    python submission/source/build_source.py [--ref HEAD] [--out submission/out/AGQO-source.zip]
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_PATHS = ("data/vn30/ohlcv_daily.csv", "submission/out/", ".claude/", ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Git commit, branch or tag to export")
    parser.add_argument("--out", type=Path, help="ZIP path (default: submission/out/AGQO-v<VERSION>-source.zip)")
    args = parser.parse_args()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", "--end-of-options", f"{args.ref}^{{commit}}"], cwd=ROOT, text=True
        ).strip()
        package = subprocess.check_output(["git", "show", f"{commit}:agqo/__init__.py"], cwd=ROOT, text=True)
        protected = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", commit, "--", *PROTECTED_PATHS], cwd=ROOT, text=True
        ).splitlines()
    except subprocess.CalledProcessError as exc:
        parser.error(f"cannot inspect Git ref {args.ref}: {exc}")
    version = re.search(r'^__version__\s*=\s*"(\d+\.\d+\.\d+)"$', package, re.MULTILINE)
    if not version:
        parser.error(f"ref {args.ref} does not declare an AGQO package version")
    if protected:
        parser.error(f"ref contains files excluded from the source package: {', '.join(protected)}")

    out = args.out or ROOT / "submission" / "out" / f"AGQO-v{version.group(1)}-source.zip"
    created = False
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as archive:
            created = True
            subprocess.run(["git", "archive", "--format=zip", commit], cwd=ROOT, stdout=archive, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        if created:
            out.unlink()
        parser.exit(1, f"Could not export {out}: {exc}\n")
    print(f"{out} ({commit})")


if __name__ == "__main__":
    main()
