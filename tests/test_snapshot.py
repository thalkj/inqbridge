"""Tests for source snapshotting."""
import pytest
from pathlib import Path
from runner.snapshot import snapshot_sources, sha256_file


def test_snapshot_main_script(tmp_path):
    script = tmp_path / "test.iqx"
    script.write_text('<expt>\n</expt>', encoding="utf-8")
    dest = tmp_path / "run_001"

    entries = snapshot_sources(script, [], dest)

    assert len(entries) == 1
    assert entries[0]["path"] == "source/test.iqx"
    assert len(entries[0]["sha256"]) == 64  # SHA-256 hex length
    assert (dest / "source" / "test.iqx").is_file()


def test_snapshot_with_includes(tmp_path):
    script = tmp_path / "main.iqx"
    inc = tmp_path / "inc.iqx"
    script.write_text('<include>"inc.iqx"</include>', encoding="utf-8")
    inc.write_text('<text t>\n</text>', encoding="utf-8")
    dest = tmp_path / "run_002"

    entries = snapshot_sources(script, [inc], dest)

    assert len(entries) == 2
    assert (dest / "source" / "main.iqx").is_file()
    assert (dest / "source" / "inc.iqx").is_file()


def test_snapshot_hash_matches(tmp_path):
    script = tmp_path / "test.iqx"
    content = '<text>\n/ items = ("hello world")\n</text>'
    script.write_text(content, encoding="utf-8")
    dest = tmp_path / "run_003"

    entries = snapshot_sources(script, [], dest)
    copied = dest / "source" / "test.iqx"

    assert entries[0]["sha256"] == sha256_file(copied)
    assert entries[0]["sha256"] == sha256_file(script)
