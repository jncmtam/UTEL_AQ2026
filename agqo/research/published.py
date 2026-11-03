"""Pinned published US return corpus with narrowly scoped research admission.

This never marks the separate DJIA market manifest as passed. The publisher
conditions securities on full-year membership, so investment-universe claims
remain disallowed. Raw corpus and return matrices stay local.
"""

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import requests
from .data import write_json, sha

REVISION = "73a8d6016588634ba91f7e6d1667f343034ec9b8"
REPOSITORY = "https://github.com/dppalomar/sparseIndexTracking"
FILES = ("data/INDEX_2010.RData", "R/INDEX_2010.R", "LICENSE", "DESCRIPTION")
RETURN_SHA256 = "16db76dccbec4dc12a5128f02a95e860e1cd498b97f4682b694b2e538daceaa7"


def fetch(directory="data/published_us"):
    path = Path(directory)
    raw = path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    files = []
    for relative in FILES:
        target = raw / Path(relative).name
        url = f"https://raw.githubusercontent.com/dppalomar/sparseIndexTracking/{REVISION}/{relative}"
        if not target.exists():
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            target.write_bytes(response.content)
        files.append(
            {
                "path": str(target.relative_to(path)),
                "sha256": sha(target),
                "source": url,
            }
        )
    manifest = {
        "version": "published-us-corpus-v1",
        "repository": REPOSITORY,
        "revision": REVISION,
        "files": files,
        "paper": "https://doi.org/10.1109/TSP.2017.2762286",
        "package": "https://CRAN.R-project.org/package=sparseIndexTracking",
        "scope": "conditional_algorithm_benchmark_only",
        "source_documentation": "Only securities present in the index for the whole 2010 period are included.",
        "investment_universe_approved": False,
        "license_note": "Package declares GPL-3 and a license file. Raw market returns are kept local; no additional redistribution right is assumed.",
        "return_semantics": "Publisher-provided daily arithmetic net returns; independent total-return/corporate-action certification is not claimed.",
    }
    write_json(path / "dataset_manifest.json", manifest)
    return assess(path)


def load(directory="data/published_us"):
    import rdata

    path = Path(directory)
    manifest = json.loads((path / "dataset_manifest.json").read_text())
    if (
        manifest.get("revision") != REVISION
        or manifest.get("scope") != "conditional_algorithm_benchmark_only"
    ):
        raise ValueError("Unexpected source revision or admission scope.")
    expected = {"raw/" + Path(relative).name for relative in FILES}
    if {entry["path"] for entry in manifest["files"]} != expected or len(
        manifest["files"]
    ) != len(expected):
        raise ValueError("Incomplete pinned source manifest.")
    for entry in manifest["files"]:
        file = (path / entry["path"]).resolve()
        if (
            not file.is_relative_to(path.resolve())
            or not file.is_file()
            or sha(file) != entry["sha256"]
        ):
            raise ValueError("Published source checksum mismatch.")
    if sha(path / "raw/INDEX_2010.RData") != RETURN_SHA256:
        raise ValueError("Unexpected pinned return corpus hash.")
    parsed = rdata.parser.parse_file(path / "raw/INDEX_2010.RData")
    elements = parsed.object.value[0].value
    decoded = []
    date_vectors = []
    for element in elements:
        attrs = rdata.conversion.convert(element.attributes)
        shape = tuple(map(int, attrs["dim"]))
        matrix = np.asarray(element.value, dtype=float).reshape(shape, order="F")
        dates = pd.to_datetime(
            np.asarray(attrs["index"]), unit="s", utc=True
        ).tz_localize(None)
        labels = list(map(str, attrs["dimnames"][1]))
        decoded.append((matrix, labels))
        date_vectors.append(dates)
    if len(decoded) != 2 or not date_vectors[0].equals(date_vectors[1]):
        raise ValueError("Source component dates disagree.")
    x, labels = decoded[0]
    benchmark = decoded[1][0].reshape(-1)
    dates = date_vectors[0]
    if (
        x.shape != (252, 386)
        or benchmark.shape != (252,)
        or len(set(labels)) != 386
        or len(labels) != 386
    ):
        raise ValueError("Unexpected pinned corpus dimensions/security labels.")
    if (
        not np.isfinite(x).all()
        or not np.isfinite(benchmark).all()
        or (x < -1).any()
        or (benchmark < -1).any()
    ):
        raise ValueError("Invalid publisher return values.")
    if (
        not dates.is_unique
        or not dates.is_monotonic_increasing
        or str(dates[0].date()) != "2010-01-04"
        or str(dates[-1].date()) != "2010-12-31"
    ):
        raise ValueError("Unexpected source dates.")
    return x, benchmark, dates, labels, manifest


def assess(directory="data/published_us"):
    path = Path(directory)
    x, b, dates, labels, manifest = load(path)
    report = {
        "version": "published-us-assessment-v1",
        "status": "admitted_for_conditional_algorithm_benchmark",
        "investment_universe_approved": False,
        "corporate_action_audit_passed": False,
        "observations": len(x),
        "assets": x.shape[1],
        "first_date": str(dates[0].date()),
        "last_date": str(dates[-1].date()),
        "epsilon_1e_minus_6_cells": int(np.sum(x == 1e-6)),
        "return_min": float(x.min()),
        "return_max": float(x.max()),
        "source_revision": REVISION,
        "unresolved": [
            "Full-year membership conditioning is a selection bias.",
            f"{int(np.sum(x == 1e-6))} values equal 1e-6; preserve publisher preprocessing, do not relabel as measured zeros.",
            "Publisher labels are source identifiers, not verified permanent tradable security identifiers.",
            "Price-versus-total-return handling is not independently certified.",
        ],
        "allowed_claim": "Algorithm quality on this exact published US corpus under declared scenario constraints; not investable historical strategy performance.",
    }
    write_json(path / "assessment.json", report)
    text = [
        "# Published US corpus assessment",
        "",
        f"Source: [{REPOSITORY}]({REPOSITORY}), pinned revision `{REVISION}`.",
        "",
        f"Loaded {x.shape[1]} source-labelled assets and {len(x)} daily observations, {report['first_date']} to {report['last_date']}. Matrix and dates were decoded directly from R attributes; no calendar was guessed.",
        "",
        "**Admission scope: conditional algorithm benchmark only. The original DJIA investment-data gate remains blocked.**",
        "",
        "## Suitability and limits",
        "",
        "- Actual US S&P500 source returns support a standard index-tracking algorithm comparison.",
        "- Selection is conditioned on full-year membership; use the fixed provided universe without an unbiased investment claim.",
        "- Preserve all publisher values, including exact 1e-6 entries. No missing-value imputation or silent cleaning.",
        "- A predeclared hash-ordered subset is a resource-limited benchmark family, not LLM stock selection. Report its restriction against the full source universe.",
        "- Scenario policy buckets are synthetic account categories, not historical industry classifications.",
        "- No contemporary fundamentals, current ticker metadata or later-sector labels are inserted into 2010 inputs.",
    ]
    (path / "ASSESSMENT.md").write_text("\n".join(text) + "\n")
    return report


def family_indices(labels, n):
    if not 1 <= n <= len(labels):
        raise ValueError("Invalid declared benchmark family size.")
    ordered = sorted(
        range(len(labels)),
        key=lambda i: hashlib.sha256(
            ("AGQO-published-family-v1:" + labels[i]).encode()
        ).hexdigest(),
    )
    return sorted(ordered[:n])
