"""Check Vietnamese diacritics on the declared maintained English surface."""

from pathlib import Path
import re
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    paths = list(root.glob("*.md"))
    paths += [p for p in (root / "docs").rglob("*.md") if "legacy" not in p.parts]
    for name in ["agqo/research", "agqo/repair"]:
        paths += [
            p
            for p in (root / name).rglob("*")
            if p.suffix in (".py", ".html", ".js", ".css")
        ]
    paths += [
        root / p
        for p in [
            "modal_gate_synthesis.py",
            "scripts/build_evidence_gallery.py",
            "scripts/preflight_llm_tokenizers.py",
        ]
    ]
    pattern = re.compile("[ăâđêôơưĂÂĐÊÔƠƯạ-ỹ]")
    exceptions = {
        "agqo/repair/benchmark.py": '("canonical_vi",',
        "agqo/repair/mandates.py": 'text.lower().replace("đ", "d")',
    }
    issues = []
    accepted = []
    for path in sorted(set(paths)):
        relative = str(path.relative_to(root))
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if not pattern.search(line):
                continue
            record = f"{relative}:{number}"
            if relative in exceptions and exceptions[relative] in line:
                accepted.append(record + " — legacy input compatibility")
            else:
                issues.append(record)
    print(f"Checked {len(set(paths))} maintained source and documentation files.")
    for item in accepted:
        print("Accepted:", item)
    for item in issues:
        print("Review:", item)
    print("PASS" if not issues else "FAIL")
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
