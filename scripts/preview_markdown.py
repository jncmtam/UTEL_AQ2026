"""Generate an app-local Markdown preview with absolute asset and file links."""

from pathlib import Path
import argparse
import re
from urllib.parse import urlsplit, unquote


def preview(source):
    source = Path(source).resolve(strict=True)
    if source.suffix.lower() != ".md":
        raise ValueError("Choose a Markdown report.")
    root = Path(__file__).resolve().parents[1]
    links, images = 0, 0
    pattern = re.compile(r'(!?\[[^\]\n]*\])\((<[^>\n]+>|[^\s)\n]+)(\s+"[^"]*")?\)')

    def replace(match):
        nonlocal links, images
        label, value, title = (
            match.group(1),
            match.group(2).strip("<>"),
            match.group(3) or "",
        )
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        target = (source.parent / unquote(parsed.path)).resolve()
        if not target.exists():
            raise ValueError(f"Missing local report link: {value}")
        links += 1
        images += int(label.startswith("!"))
        suffix = ("?" + parsed.query if parsed.query else "") + (
            "#" + parsed.fragment if parsed.fragment else ""
        )
        return f"{label}(<{target}{suffix}>{title})"

    text = pattern.sub(replace, source.read_text())
    folder = root / ".local-previews"
    folder.mkdir(exist_ok=True)
    target = folder / f"{source.parent.name}_{source.stem}.md"
    target.write_text(
        f"<!-- Local preview of {source}; canonical evidence unchanged. -->\n\n" + text
    )
    return target, links, images


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    args = parser.parse_args()
    path, links, images = preview(args.source)
    print(f"Preview: {path}\nResolved {links} local links, including {images} images.")
