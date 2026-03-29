"""Tests for runner.capture_manager."""
import pytest

from runner.capture_manager import (
    inject_screencapture,
    strip_screencapture,
    create_captured_copies,
    cleanup_temp_copies,
    strip_screencapture_files,
)


def test_inject_adds_to_trial():
    """screenCapture=true is injected into trials that don't have it."""
    source = """<trial test_trial>
/ stimulustimes = [0=stimulus]
/ validresponse = ("e")
</trial>"""
    result = inject_screencapture(source)
    assert "/ screenCapture = true" in result


def test_inject_skips_existing():
    """Trials that already have screenCapture are not modified."""
    source = """<trial test_trial>
/ screenCapture = true
/ stimulustimes = [0=stimulus]
</trial>"""
    result = inject_screencapture(source)
    assert result.count("screenCapture") == 1


def test_strip_removes_all():
    """All screenCapture lines are removed."""
    source = """<trial t1>
/ screenCapture = true
/ validresponse = ("e")
</trial>
<trial t2>
/ screenCapture = true
/ validresponse = ("i")
</trial>"""
    result = strip_screencapture(source)
    assert "screenCapture" not in result
    assert '/ validresponse = ("e")' in result


def test_strip_preserves_other_lines():
    """Non-screenCapture lines are preserved."""
    source = """<trial test>
/ screenCapture = true
/ stimulustimes = [0=fix]
/ validresponse = ("e")
</trial>"""
    result = strip_screencapture(source)
    assert "stimulustimes" in result
    assert "validresponse" in result


def test_create_and_cleanup_captured_copies(tmp_path):
    """Captured copies are created and cleaned up."""
    script = tmp_path / "test.iqx"
    script.write_text('<trial t1>\n/ validresponse = ("e")\n</trial>\n')

    cap_script, _, temps = create_captured_copies(script, [])
    assert cap_script.exists()
    assert "screenCapture" in cap_script.read_text()

    cleanup_temp_copies(temps)
    assert not cap_script.exists()


def test_strip_files(tmp_path):
    """strip_screencapture_files modifies actual files."""
    script = tmp_path / "test.iqx"
    script.write_text('<trial t1>\n/ screenCapture = true\n/ validresponse = ("e")\n</trial>\n')

    result = strip_screencapture_files(script)
    assert len(result["files_modified"]) == 1
    assert result["total_lines_removed"] == 1
    assert "screenCapture" not in script.read_text()
