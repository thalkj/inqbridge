"""Tests for runner.artifacts."""
import os
import time

from runner.artifacts import collect_data_files, collect_screen_captures


def test_collect_data_files_filters_by_modified_after(tmp_path):
    """Only same-script data files modified during the run are collected."""
    script_dir = tmp_path / "experiment"
    data_dir = script_dir / "data"
    run_dir = tmp_path / "run"
    data_dir.mkdir(parents=True)

    old_file = data_dir / "main_raw_old.iqdat"
    new_file = data_dir / "main_raw_new.iqdat"
    other_file = data_dir / "other_raw_new.iqdat"
    old_file.write_text("old")
    marker = time.time()
    time.sleep(0.01)
    new_file.write_text("new")
    other_file.write_text("other")
    old_mtime = marker - 10
    os.utime(old_file, (old_mtime, old_mtime))

    collected = collect_data_files(
        script_dir,
        run_dir,
        script_name="main",
        modified_after=marker,
    )

    assert collected == ["data/main_raw_new.iqdat"]
    assert (run_dir / "data" / "main_raw_new.iqdat").exists()
    assert not (run_dir / "data" / "main_raw_old.iqdat").exists()
    assert not (run_dir / "data" / "other_raw_new.iqdat").exists()


def test_collect_screen_captures_filters_by_modified_after(tmp_path):
    """Only captures modified during the run are collected."""
    script_dir = tmp_path / "experiment"
    cap_dir = script_dir / "data" / "screencaptures"
    run_dir = tmp_path / "run"
    cap_dir.mkdir(parents=True)

    old_file = cap_dir / "old.png"
    new_file = cap_dir / "new.png"
    old_file.write_bytes(b"old")
    marker = time.time()
    time.sleep(0.01)
    new_file.write_bytes(b"new")
    old_mtime = marker - 10
    os.utime(old_file, (old_mtime, old_mtime))

    collected = collect_screen_captures(
        script_dir,
        run_dir,
        modified_after=marker,
    )

    assert collected == ["screencaptures/new.png"]
    assert (run_dir / "screencaptures" / "new.png").exists()
    assert not (run_dir / "screencaptures" / "old.png").exists()
