"""Tests for runner.preflight — pre-flight validation for .iqx scripts."""
import pytest
from pathlib import Path

from runner.preflight import (
    check_missing_files,
    check_brackets,
    check_undefined_references,
    preflight_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_script(path: Path, content: str) -> Path:
    """Write a script file and return its path."""
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# check_missing_files
# ---------------------------------------------------------------------------

def test_missing_files_flags_absent_picture(tmp_path):
    """Picture element referencing a non-existent file should be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<picture mypic>
/ items = ("image1.png", "image2.png")
</picture>
''')
    # Create only image1.png
    (tmp_path / "image1.png").write_bytes(b"PNG")

    issues = check_missing_files(script)
    assert len(issues) == 1
    assert issues[0]["check"] == "missing_file"
    assert issues[0]["missing_file"] == "image2.png"
    assert issues[0]["element_name"] == "mypic"


def test_missing_files_passes_all_present(tmp_path):
    """No issues when all referenced files exist."""
    script = _write_script(tmp_path / "test.iqx", '''
<picture mypic>
/ items = ("image1.png")
</picture>
''')
    (tmp_path / "image1.png").write_bytes(b"PNG")

    issues = check_missing_files(script)
    assert len(issues) == 0


def test_missing_files_checks_sound_and_video(tmp_path):
    """Sound and video elements should also be checked."""
    script = _write_script(tmp_path / "test.iqx", '''
<sound mysound>
/ items = ("beep.wav")
</sound>
<video myvideo>
/ items = ("clip.mp4")
</video>
''')

    issues = check_missing_files(script)
    assert len(issues) == 2
    types = {i["element_type"] for i in issues}
    assert types == {"sound", "video"}


def test_missing_files_ignores_text_elements(tmp_path):
    """Text elements don't reference files — should not be checked."""
    script = _write_script(tmp_path / "test.iqx", '''
<text mytext>
/ items = ("Hello world")
</text>
''')

    issues = check_missing_files(script)
    assert len(issues) == 0


def test_missing_files_empty_script(tmp_path):
    """Empty script should produce no issues."""
    script = _write_script(tmp_path / "test.iqx", "")
    issues = check_missing_files(script)
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# check_brackets
# ---------------------------------------------------------------------------

def test_brackets_flags_unclosed(tmp_path):
    """Unclosed bracket in ontrialbegin should be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ ontrialbegin = [values.x = 1;
/ ontrialend = [values.y = 2]
</trial>
''')

    issues = check_brackets(script)
    assert len(issues) >= 1
    assert any(i["check"] == "bracket_mismatch" for i in issues)


def test_brackets_passes_balanced(tmp_path):
    """Balanced brackets should produce no issues."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ ontrialbegin = [values.x = 1; values.y = 2]
/ ontrialend = [values.z = 3]
</trial>
''')

    issues = check_brackets(script)
    assert len(issues) == 0


def test_brackets_multiline_balanced(tmp_path):
    """Multi-line bracket expression that closes properly is fine."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ ontrialbegin = [if (values.x == 1)
  values.y = 2;
  values.z = 3;
]
</trial>
''')

    issues = check_brackets(script)
    assert len(issues) == 0


def test_brackets_flags_eof_unclosed(tmp_path):
    """Bracket unclosed at end of file should be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ ontrialbegin = [values.x = 1;
  values.y = 2;
''')

    issues = check_brackets(script)
    assert len(issues) >= 1
    assert any("end of file" in i["message"] for i in issues)


def test_brackets_extra_closing(tmp_path):
    """Extra closing bracket should be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ ontrialbegin = [values.x = 1]]
</trial>
''')

    issues = check_brackets(script)
    assert len(issues) >= 1


def test_brackets_ignores_comments(tmp_path):
    """Comment lines should be skipped."""
    script = _write_script(tmp_path / "test.iqx", '''
// / ontrialbegin = [unclosed
** / ontrialbegin = [also unclosed
<trial mytrial>
/ ontrialbegin = [values.x = 1]
</trial>
''')

    issues = check_brackets(script)
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# check_undefined_references
# ---------------------------------------------------------------------------

def test_undefined_refs_flags_missing_stimulus(tmp_path):
    """Stimulus referenced in stimulusframes but not defined should be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<text mytext>
/ items = ("Hello")
</text>
<trial mytrial>
/ stimulusframes = [1=mytext, ghostelement]
</trial>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 1
    assert issues[0]["undefined_name"] == "ghostelement"
    assert issues[0]["context"] == "stimulusframes"


def test_undefined_refs_passes_all_defined(tmp_path):
    """All referenced elements are defined — no issues."""
    script = _write_script(tmp_path / "test.iqx", '''
<text mytext>
/ items = ("Hello")
</text>
<text othertext>
/ items = ("World")
</text>
<trial mytrial>
/ stimulusframes = [1=mytext, othertext]
</trial>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 0


def test_undefined_refs_checks_stimulustimes(tmp_path):
    """Elements in stimulustimes should also be checked."""
    script = _write_script(tmp_path / "test.iqx", '''
<text mytext>
/ items = ("Hello")
</text>
<trial mytrial>
/ stimulustimes = [0=mytext; 500=missingtext]
</trial>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 1
    assert issues[0]["undefined_name"] == "missingtext"


def test_undefined_refs_checks_block_trials(tmp_path):
    """Trials referenced in block should be checked."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial realtrial>
/ stimulusframes = [1=clearscreen]
</trial>
<block myblock>
/ trials = [1=realtrial; 2=phantomtrial]
</block>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 1
    assert issues[0]["undefined_name"] == "phantomtrial"


def test_undefined_refs_checks_expt_blocks(tmp_path):
    """Blocks referenced in expt should be checked."""
    script = _write_script(tmp_path / "test.iqx", '''
<block realblock>
/ trials = [1=clearscreen]
</block>
<expt myexpt>
/ blocks = [1=realblock; 2=ghostblock]
</expt>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 1
    assert issues[0]["undefined_name"] == "ghostblock"


def test_undefined_refs_ignores_keywords(tmp_path):
    """Inquisit keywords like 'clearscreen' should not be flagged."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial mytrial>
/ stimulusframes = [1=clearscreen]
</trial>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 0


def test_undefined_refs_empty_script(tmp_path):
    """Empty script should produce no issues."""
    script = _write_script(tmp_path / "test.iqx", "")
    issues = check_undefined_references(script)
    assert len(issues) == 0


def test_undefined_refs_deduplicates(tmp_path):
    """Same missing name referenced multiple times should only flag once."""
    script = _write_script(tmp_path / "test.iqx", '''
<trial trial1>
/ stimulusframes = [1=ghost]
</trial>
<trial trial2>
/ stimulusframes = [1=ghost]
</trial>
''')

    issues = check_undefined_references(script)
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# preflight_check (integration)
# ---------------------------------------------------------------------------

def test_preflight_check_clean_script(tmp_path):
    """Clean script should pass all checks."""
    script = _write_script(tmp_path / "test.iqx", '''
<text mytext>
/ items = ("Hello world")
</text>
<trial mytrial>
/ stimulusframes = [1=mytext]
/ ontrialbegin = [values.x = 1]
</trial>
<block myblock>
/ trials = [1=mytrial]
</block>
<expt myexpt>
/ blocks = [1=myblock]
</expt>
<values>
/ x = 0
</values>
''')

    result = preflight_check(script)
    assert result["passed"] is True
    assert result["error_count"] == 0
    assert "missing_files" in result["checks_run"]
    assert "bracket_matching" in result["checks_run"]
    assert "undefined_references" in result["checks_run"]


def test_preflight_check_multiple_issues(tmp_path):
    """Script with multiple problems should report all of them."""
    script = _write_script(tmp_path / "test.iqx", '''
<picture mypic>
/ items = ("missing.png")
</picture>
<trial mytrial>
/ stimulusframes = [1=ghostelement]
/ ontrialbegin = [values.x = 1;
/ ontrialend = [values.y = 2]
</trial>
''')

    result = preflight_check(script)
    assert result["passed"] is False
    assert result["error_count"] >= 2  # missing file + bracket or ref issue


# ---------------------------------------------------------------------------
# Existing test updates: verify exit code 0 = compile_error
# ---------------------------------------------------------------------------

def test_determine_verdict_exit_code_0():
    """Exit code 0 from Inquisit should produce compile_error verdict."""
    from runner.manifest import determine_verdict

    verdict, notes = determine_verdict(return_code=0, timed_out=False, raw_data_files=[])
    assert verdict == "compile_error"
    assert any("code 0" in n for n in notes)


def test_determine_verdict_exit_code_1_with_data():
    """Exit code 1 with data should still be 'completed'."""
    from runner.manifest import determine_verdict

    verdict, notes = determine_verdict(
        return_code=1, timed_out=False,
        raw_data_files=["data/test_raw.iqdat"]
    )
    assert verdict == "completed"
