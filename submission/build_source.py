"""Export the committed V3 source without local market data or generated files."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from agqo import __version__

ROOT = Path(__file__).resolve().parent.parent
PROTECTED_PATHS = ("data/vn30/ohlcv_daily.csv", "submission/out/", ".claude/", ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Git commit, branch or tag to export")
    parser.add_argument("--out", type=Path, default=ROOT / "submission" / "out" / f"AGQO-v{__version__}-source.zip")
    args = parser.parse_args()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", "--end-of-options", f"{args.ref}^{{commit}}"], cwd=ROOT, text=True
        ).strip()
        protected = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", commit, "--", *PROTECTED_PATHS], cwd=ROOT, text=True
        ).splitlines()
    except subprocess.CalledProcessError as exc:
        parser.error(f"cannot inspect Git ref {args.ref}: {exc}")
    if protected:
        parser.error(f"ref contains files excluded from the source package: {', '.join(protected)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with args.out.open("xb") as archive:
            created = True
            subprocess.run(["git", "archive", "--format=zip", commit], cwd=ROOT, stdout=archive, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        if created:
            args.out.unlink()
        parser.exit(1, f"Could not export {args.out}: {exc}\n")
    print(f"{args.out} ({commit})")


if __name__ == "__main__":
    main()
