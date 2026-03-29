"""Tests for visual QA module."""
import json
import pytest
from pathlib import Path

from runner.visual_qa import deduplicate_captures, write_capture_index


def _create_bmp_like_file(path: Path, content: bytes = b"BM" + b"\x00" * 100):
    """Create a small file that looks like a BMP."""
    path.write_bytes(content)


def test_dedup_exact_duplicates(tmp_path):
    content = b"BM" + b"\xff" * 100
    a = tmp_path / "cap1.bmp"
    b = tmp_path / "cap2.bmp"
    a.write_bytes(content)
    b.write_bytes(content)

    entries = deduplicate_captures([a, b])
    assert len(entries) == 2
    assert not entries[0].is_duplicate
    assert entries[1].is_duplicate
    assert entries[1].duplicate_of == str(a)


def test_dedup_unique_files(tmp_path):
    a = tmp_path / "cap1.bmp"
    b = tmp_path / "cap2.bmp"
    a.write_bytes(b"BM" + b"\x00" * 100)
    b.write_bytes(b"BM" + b"\xff" * 100)

    entries = deduplicate_captures([a, b])
    assert not entries[0].is_duplicate
    assert not entries[1].is_duplicate


def test_write_capture_index(tmp_path):
    a = tmp_path / "cap1.bmp"
    a.write_bytes(b"BM" + b"\x00" * 50)
    entries = deduplicate_captures([a])

    index_path = write_capture_index(entries, "test-run", tmp_path)
    assert index_path.is_file()

    index = json.loads(index_path.read_text())
    assert index["run_id"] == "test-run"
    assert index["total_captures"] == 1
    assert index["unique_captures"] == 1


def test_empty_captures():
    entries = deduplicate_captures([])
    assert entries == []
