"""Tests for runner.merge_validator."""
import pytest
from pathlib import Path

from runner.merge_validator import validate_merge


@pytest.fixture
def tmp_iqx(tmp_path):
    """Helper to create temporary .iqx files."""
    def _make(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p
    return _make


def test_no_conflicts(tmp_iqx):
    """Two files with distinct element names pass validation."""
    f1 = tmp_iqx("module_a.iqx", """\
<text greeting>
/ items = ("Hello")
</text>
<trial greeting_trial>
/ stimulustimes = [0=greeting]
/ validresponse = (" ")
</trial>
""")
    f2 = tmp_iqx("module_b.iqx", """\
<text farewell>
/ items = ("Goodbye")
</text>
<trial farewell_trial>
/ stimulustimes = [0=farewell]
/ validresponse = (" ")
</trial>
""")
    result = validate_merge([f1, f2])
    assert result["passed"] is True
    assert result["conflict_count"] == 0
    assert result["placeholder_count"] == 0


def test_name_conflict(tmp_iqx):
    """Same element name in two files is flagged as a conflict."""
    f1 = tmp_iqx("module_a.iqx", """\
<text instructions>
/ items = ("Module A instructions")
</text>
""")
    f2 = tmp_iqx("module_b.iqx", """\
<text instructions>
/ items = ("Module B instructions")
</text>
""")
    result = validate_merge([f1, f2])
    assert result["passed"] is False
    assert result["conflict_count"] == 1
    assert result["conflicts"][0]["name"] == "instructions"


def test_type_mismatch(tmp_iqx):
    """Same name as different element types is flagged."""
    f1 = tmp_iqx("module_a.iqx", """\
<text stimulus>
/ items = ("Hello")
</text>
""")
    f2 = tmp_iqx("module_b.iqx", """\
<picture stimulus>
/ items = ("image.png")
</picture>
""")
    result = validate_merge([f1, f2])
    assert result["type_mismatch_count"] == 1
    assert "text" in result["type_mismatches"][0]["types"]
    assert "picture" in result["type_mismatches"][0]["types"]


def test_placeholder_detection(tmp_iqx):
    """Unresolved PLACEHOLDER values are flagged."""
    f1 = tmp_iqx("config.iqx", """\
<values>
// PLACEHOLDER: replace with actual condition label
/ condition_label = "PLACEHOLDER"
</values>
""")
    result = validate_merge([f1])
    assert result["passed"] is False
    assert result["placeholder_count"] == 2  # comment + value


def test_cross_references(tmp_iqx):
    """Cross-file references are reported (informational)."""
    f1 = tmp_iqx("config.iqx", """\
<text shared_label>
/ items = ("Label")
</text>
""")
    f2 = tmp_iqx("test.iqx", """\
<trial test_trial>
/ stimulustimes = [0=shared_label]
/ validresponse = (" ")
</trial>
""")
    result = validate_merge([f1, f2])
    assert result["cross_reference_count"] >= 1
    xref = result["cross_references"][0]
    assert xref["references"] == "shared_label"
    assert "config.iqx" in xref["defined_in"]


def test_empty_file_list():
    """Empty file list passes with no issues."""
    result = validate_merge([])
    assert result["passed"] is True
    assert result["conflict_count"] == 0


def test_missing_file(tmp_path):
    """Non-existent files are silently skipped."""
    result = validate_merge([tmp_path / "nonexistent.iqx"])
    assert result["passed"] is True
