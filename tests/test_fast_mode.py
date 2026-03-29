"""Tests for runner.fast_mode."""
import pytest

from runner.fast_mode import make_fast_copy, create_fast_copies, cleanup_fast_copies


def test_collapse_stimulustimes():
    """Stimulustimes entries are collapsed to t=0."""
    source = """<trial test>
/ stimulustimes = [0=fixation; 500=stimulus; 1000=feedback]
/ validresponse = ("e", "i")
</trial>"""
    result = make_fast_copy(source)
    assert "0=fixation, stimulus, feedback" in result
    assert "500=" not in result
    assert "1000=" not in result


def test_zero_pauses():
    """Post-trial and pre-trial pauses are set to 0."""
    source = """<trial test>
/ posttrialpause = 500
/ pretrialpause = 200
</trial>"""
    result = make_fast_copy(source)
    assert "/ posttrialpause = 0" in result
    assert "/ pretrialpause = 0" in result


def test_minimize_timeout():
    """Timeout is set to 100ms (not 0)."""
    source = """<trial test>
/ timeout = 5000
</trial>"""
    result = make_fast_copy(source)
    assert "/ timeout = 100" in result


def test_no_change_to_other_attributes():
    """Non-timing attributes are preserved."""
    source = """<trial test>
/ validresponse = ("e", "i")
/ correctresponse = ("e")
/ stimulustimes = [0=fixation; 500=stimulus]
</trial>"""
    result = make_fast_copy(source)
    assert '/ validresponse = ("e", "i")' in result
    assert '/ correctresponse = ("e")' in result


def test_create_and_cleanup_fast_copies(tmp_path):
    """Fast copies are created and cleaned up properly."""
    script = tmp_path / "test.iqx"
    script.write_text('<trial t1>\n/ stimulustimes = [0=fix; 500=stim]\n</trial>\n')

    include = tmp_path / "inc.iqx"
    include.write_text('<text fix>\n/ items = ("+")\n</text>\n')

    fast_script, fast_incs, temps = create_fast_copies(script, [include])

    assert fast_script.exists()
    assert "_fast_tmp" in fast_script.name
    assert "0=fix, stim" in fast_script.read_text()

    cleanup_fast_copies(temps)
    assert not fast_script.exists()


def test_fast_copy_rewrites_includes(tmp_path):
    """Include references in fast copies point to the fast versions."""
    script = tmp_path / "main.iqx"
    script.write_text('<include>"helper.iqx"</include>\n<trial t>\n/ stimulustimes = [0=x]\n</trial>\n')

    inc = tmp_path / "helper.iqx"
    inc.write_text('<text x>\n/ items = ("hi")\n</text>\n')

    fast_script, _, temps = create_fast_copies(script, [inc])
    content = fast_script.read_text()
    assert "helper_fast_tmp.iqx" in content

    cleanup_fast_copies(temps)


def test_multiple_stimulustimes_entries():
    """Multiple stimulustimes with comma-separated elements work."""
    source = """<trial test>
/ stimulustimes = [0=label_left, label_right; 500=stimulus]
</trial>"""
    result = make_fast_copy(source)
    assert "0=label_left, label_right, stimulus" in result
