from pathlib import Path
import pytest
from agqo.research.sources import relative_sources


def test_absolute_controller_is_archived_under_snapshot_instead_of_source_root(
    tmp_path,
):
    root = tmp_path / "project"
    script = root / "scripts" / "run.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('fixture')\n")
    values = relative_sources(root, [script, Path("scripts/run.py")])
    assert values == [Path("scripts/run.py"), Path("scripts/run.py")]
    assert all(not value.is_absolute() for value in values)
    assert all(
        (root / "archive" / value).is_relative_to(root / "archive") for value in values
    )
    assert script.read_text() == "print('fixture')\n"


def test_missing_or_escaped_snapshot_sources_are_rejected(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n")
    with pytest.raises(ValueError):
        relative_sources(root, [outside])
    with pytest.raises(ValueError):
        relative_sources(root, ["missing.py"])
