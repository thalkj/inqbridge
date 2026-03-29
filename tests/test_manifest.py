"""Tests for manifest generation and verdict logic."""
import json
import pytest
from pathlib import Path
from runner.manifest import write_manifest, read_manifest, determine_verdict


def test_write_and_read_manifest(tmp_path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()

    path = write_manifest(
        run_dir=run_dir,
        run_id="test-run-001",
        script_entry="scripts/test.iqx",
        source_snapshot=[{"path": "source/test.iqx", "sha256": "abc123"}],
        mode="monkey",
        subject_id="1",
        group_id="1",
        command='"Inquisit.exe" "test.iqx" -s 1 -g 1 -m monkey',
        return_code=0,
        raw_data_files=["data/raw_test.txt"],
        summary_data_files=["data/summary_test.txt"],
        screen_captures=[],
        verdict="completed",
    )

    assert path.is_file()
    manifest = read_manifest(path)
    assert manifest["run_id"] == "test-run-001"
    assert manifest["mode"] == "monkey"
    assert manifest["verdict"] == "completed"
    assert len(manifest["executed_snapshot"]["files"]) == 1


def test_verdict_completed():
    """Inquisit 6: exit code 1 with data = completed."""
    verdict, notes = determine_verdict(1, False, ["data/raw.txt"])
    assert verdict == "completed"


def test_verdict_timeout():
    verdict, notes = determine_verdict(None, True, [])
    assert verdict == "timeout"


def test_verdict_inquisit6_return_code_1():
    """Inquisit 6 returns code 1 on normal completion."""
    verdict, notes = determine_verdict(1, False, ["data/raw.txt"])
    assert verdict == "completed"


def test_verdict_error():
    verdict, notes = determine_verdict(2, False, ["data/raw.txt"])
    assert verdict == "error"


def test_verdict_no_data():
    """Inquisit 6: exit code 1 but no data files = completed_no_data."""
    verdict, notes = determine_verdict(1, False, [])
    assert verdict == "completed_no_data"


def test_verdict_compile_error():
    """Inquisit 6: exit code 0 = compile/startup failure."""
    verdict, notes = determine_verdict(0, False, [])
    assert verdict == "compile_error"
    assert any("code 0" in n for n in notes)


def test_manifest_has_required_fields(tmp_path):
    run_dir = tmp_path / "run_002"
    run_dir.mkdir()

    write_manifest(
        run_dir=run_dir,
        run_id="test-run-002",
        script_entry="scripts/test.iqx",
        source_snapshot=[],
        mode="human",
        subject_id="42",
        group_id="3",
        command="test command",
        return_code=0,
        raw_data_files=[],
        summary_data_files=[],
        screen_captures=[],
        verdict="completed_no_data",
    )

    manifest = read_manifest(run_dir / "manifest.json")
    required = ["run_id", "timestamp_utc", "inquisit_path", "script_entry",
                 "executed_snapshot", "mode", "subject_id", "group_id", "command",
                 "return_code", "verdict"]
    for field in required:
        assert field in manifest, f"Missing required field: {field}"
