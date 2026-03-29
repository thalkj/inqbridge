"""Tests for runner.auto_fix."""
import pytest
from pathlib import Path

from runner.auto_fix import attempt_auto_fix


@pytest.fixture
def tmp_iqx(tmp_path):
    def _make(name, content):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p
    return _make


def test_fix_missing_file(tmp_iqx):
    """Missing file reference causes the element to be commented out."""
    script = tmp_iqx("test.iqx", """\
<picture logo>
/ items = ("missing_logo.png")
</picture>
<text greeting>
/ items = ("Hello")
</text>
""")
    issues = [{
        "check": "missing_file",
        "severity": "error",
        "element_type": "picture",
        "element_name": "logo",
        "missing_file": "missing_logo.png",
        "message": "missing file",
    }]

    result = attempt_auto_fix(script, [], issues)
    assert result["fixed_count"] == 1
    assert "commented_out_element" in result["fixed"][0]["fix"]

    # Verify the file was modified
    content = script.read_text()
    assert "AUTO-DISABLED" in content
    # The text element should still be there
    assert "<text greeting>" in content


def test_fix_undefined_reference(tmp_iqx):
    """Undefined reference is removed from stimulustimes."""
    script = tmp_iqx("test.iqx", """\
<text greeting>
/ items = ("Hello")
</text>
<trial test_trial>
/ stimulustimes = [0=greeting; 500=nonexistent_element]
/ validresponse = (" ")
</trial>
""")
    issues = [{
        "check": "undefined_reference",
        "severity": "error",
        "context": "stimulustimes",
        "undefined_name": "nonexistent_element",
        "message": "not defined",
    }]

    result = attempt_auto_fix(script, [], issues)
    assert result["fixed_count"] == 1

    content = script.read_text()
    assert "nonexistent_element" not in content
    assert "greeting" in content


def test_bracket_bugs_not_fixed(tmp_iqx):
    """Bracket bugs are flagged as unfixable."""
    script = tmp_iqx("test.iqx", "<trial t>\n/ ontrialbegin = [\n</trial>\n")
    issues = [{
        "check": "bracket_mismatch",
        "severity": "error",
        "file": str(script),
        "line": 2,
        "attribute": "ontrialbegin",
        "message": "unclosed bracket",
    }]

    result = attempt_auto_fix(script, [], issues)
    assert result["fixed_count"] == 0
    assert result["unfixable_count"] == 1


def test_no_issues():
    """No issues means nothing to fix."""
    result = attempt_auto_fix(Path("dummy.iqx"), [], [])
    assert result["fixed_count"] == 0
    assert result["unfixable_count"] == 0
