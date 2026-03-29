"""Tests for runner.data_qa — monkey data quality assessment."""
import pytest
from pathlib import Path

from runner.data_qa import (
    parse_iqdat,
    parse_script_context,
    profile_trialcode,
    assess_monkey_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASIC_HEADER = "date\ttime\tgroup\tsubject\tblocknum\ttrialnum\tblockcode\ttrialcode\tresponse\tcorrect\tlatency\tstimulusitem1\tstimulusonset1"


def _write_iqdat(path: Path, rows: list[dict]) -> None:
    """Write a synthetic .iqdat file."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    header = list(rows[0].keys())
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(str(row.get(h, "")) for h in header))
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_row(trialcode="classify", response="37", correct="1", latency="300",
              stimulusitem1="HELLO", stimulusonset1="10", **kwargs):
    """Create a synthetic data row dict."""
    row = {
        "date": "2026-03-10", "time": "12:00:00", "group": "1",
        "subject": "1", "blocknum": "1", "trialnum": "1",
        "blockcode": "test", "trialcode": trialcode,
        "response": response, "correct": correct, "latency": latency,
        "stimulusitem1": stimulusitem1, "stimulusonset1": stimulusonset1,
    }
    row.update(kwargs)
    return row


# ---------------------------------------------------------------------------
# parse_iqdat
# ---------------------------------------------------------------------------

def test_parse_iqdat_basic(tmp_path):
    f = tmp_path / "test.iqdat"
    rows = [_make_row(trialcode="classify", response="37", latency="300")]
    _write_iqdat(f, rows)

    cols, parsed = parse_iqdat(f)
    assert "trialcode" in cols
    assert len(parsed) == 1
    assert parsed[0]["trialcode"] == "classify"
    assert parsed[0]["response"] == "37"


def test_parse_iqdat_empty(tmp_path):
    f = tmp_path / "empty.iqdat"
    f.write_text("", encoding="utf-8")

    cols, rows = parse_iqdat(f)
    assert cols == []
    assert rows == []


def test_parse_iqdat_multiple_rows(tmp_path):
    f = tmp_path / "multi.iqdat"
    rows = [
        _make_row(trialcode="classify", response="37", latency="250"),
        _make_row(trialcode="classify", response="38", latency="310"),
        _make_row(trialcode="instructions", response=" ", latency="500"),
    ]
    _write_iqdat(f, rows)

    cols, parsed = parse_iqdat(f)
    assert len(parsed) == 3


# ---------------------------------------------------------------------------
# parse_script_context
# ---------------------------------------------------------------------------

def test_parse_script_context_rt_task():
    script = '''
<trial classify>
/ validresponse = ("a", "l")
/ correctresponse = ("a")
</trial>
'''
    ctx = parse_script_context(script)
    assert "classify" in ctx["trials"]
    assert ctx["trials"]["classify"]["has_correctresponse"] is True
    assert "a" in ctx["trials"]["classify"]["validresponse"]
    assert "l" in ctx["trials"]["classify"]["validresponse"]


def test_parse_script_context_survey():
    script = '''
<surveypage demographics>
/ questions = [1=q_age; 2=q_gender]
</surveypage>
'''
    ctx = parse_script_context(script)
    assert ctx["has_surveys"] is True


def test_parse_script_context_list():
    script = '''
<list targets>
/ items = ("cat", "dog", "bird")
</list>
'''
    ctx = parse_script_context(script)
    assert "targets" in ctx["lists_found"]


def test_parse_script_context_none():
    ctx = parse_script_context(None)
    assert ctx["trials"] == {}
    assert ctx["has_surveys"] is False


def test_parse_script_context_single_validresponse():
    script = '''
<trial instructions>
/ validresponse = (" ")
</trial>
'''
    ctx = parse_script_context(script)
    assert ctx["trials"]["instructions"]["validresponse"] == [" "]


# ---------------------------------------------------------------------------
# profile_trialcode
# ---------------------------------------------------------------------------

def test_profile_trialcode_basic():
    rows = [
        _make_row(response="37", latency="250", stimulusitem1="A"),
        _make_row(response="38", latency="310", stimulusitem1="B"),
        _make_row(response="37", latency="280", stimulusitem1="C"),
    ]
    ctx = {"trials": {"classify": {"validresponse": ["37", "38"], "has_correctresponse": True, "uses_list": True}}}

    profile = profile_trialcode("classify", rows, ctx)
    assert profile["trial_count"] == 3
    assert profile["response_summary"]["unique_responses"] == 2
    assert profile["response_summary"]["all_same"] is False
    assert profile["stimulus_summary"]["unique_items"] == 3


def test_profile_single_response_single_expected():
    """All same response, but script only expects one key → no flag."""
    rows = [_make_row(response=" ") for _ in range(5)]
    ctx = {"trials": {"classify": {"validresponse": [" "], "has_correctresponse": False, "uses_list": False}}}

    profile = profile_trialcode("classify", rows, ctx)
    assert profile["response_summary"]["all_same"] is True
    # Should NOT flag since only one valid response expected
    response_flags = [f for f in profile["flags"] if "all responses identical" in f]
    assert len(response_flags) == 0


def test_profile_single_response_multi_expected():
    """All same response, but script expects multiple keys → should flag."""
    rows = [_make_row(response="37") for _ in range(5)]
    ctx = {"trials": {"classify": {"validresponse": ["37", "38"], "has_correctresponse": False, "uses_list": False}}}

    profile = profile_trialcode("classify", rows, ctx)
    response_flags = [f for f in profile["flags"] if "all responses identical" in f]
    assert len(response_flags) == 1


def test_profile_zero_latency():
    """All zero latencies → flags problem."""
    rows = [_make_row(latency="0") for _ in range(5)]
    ctx = {"trials": {}}

    profile = profile_trialcode("classify", rows, ctx)
    assert profile["latency_summary"]["zero_count"] == 5
    lat_flags = [f for f in profile["flags"] if "zero" in f.lower()]
    assert len(lat_flags) >= 1


def test_profile_accuracy_near_chance():
    """~50% accuracy on 2-choice → informational flag."""
    rows = []
    for i in range(10):
        rows.append(_make_row(correct="1" if i < 5 else "0"))
    ctx = {"trials": {"classify": {"validresponse": ["37", "38"], "has_correctresponse": True, "uses_list": False}}}

    profile = profile_trialcode("classify", rows, ctx)
    assert profile["accuracy_summary"] is not None
    assert 0.4 <= profile["accuracy_summary"]["rate"] <= 0.6
    chance_flags = [f for f in profile["flags"] if "near-chance" in f]
    assert len(chance_flags) == 1


def test_profile_stimulus_same_with_list():
    """All same stimulus when list is used → should flag."""
    rows = [_make_row(stimulusitem1="WORD") for _ in range(5)]
    ctx = {"trials": {"classify": {"validresponse": ["37"], "has_correctresponse": False, "uses_list": True}}}

    profile = profile_trialcode("classify", rows, ctx)
    stim_flags = [f for f in profile["flags"] if "all stimuli identical" in f]
    assert len(stim_flags) == 1


def test_profile_stimulus_same_no_list():
    """All same stimulus when no list → no flag (fixed stimulus is fine)."""
    rows = [_make_row(stimulusitem1="WORD") for _ in range(5)]
    ctx = {"trials": {"classify": {"validresponse": ["37"], "has_correctresponse": False, "uses_list": False}}}

    profile = profile_trialcode("classify", rows, ctx)
    stim_flags = [f for f in profile["flags"] if "all stimuli identical" in f]
    assert len(stim_flags) == 0


# ---------------------------------------------------------------------------
# assess_monkey_data (integration)
# ---------------------------------------------------------------------------

def test_assess_monkey_data_integration(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Write synthetic data
    rows = [
        _make_row(trialcode="classify", response="37", correct="1", latency="280", stimulusitem1="A"),
        _make_row(trialcode="classify", response="38", correct="0", latency="350", stimulusitem1="B"),
        _make_row(trialcode="classify", response="37", correct="1", latency="300", stimulusitem1="C"),
    ]
    _write_iqdat(data_dir / "test_raw_001.iqdat", rows)

    # Write script source
    script = '''
<trial classify>
/ validresponse = ("37", "38")
/ correctresponse = ("37")
</trial>
'''
    (source_dir / "test.iqx").write_text(script, encoding="utf-8")

    report = assess_monkey_data("test-run", data_dir, source_dir)

    assert report["run_id"] == "test-run"
    assert report["total_rows"] == 3
    assert len(report["trialcode_profiles"]) == 1
    assert report["trialcode_profiles"][0]["trialcode"] == "classify"
    assert report["trialcode_profiles"][0]["trial_count"] == 3


def test_assess_monkey_data_no_source(tmp_path):
    """Works without source dir — just no script context."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = [_make_row(trialcode="test")]
    _write_iqdat(data_dir / "raw.iqdat", rows)

    report = assess_monkey_data("no-source-run", data_dir, source_dir=None)
    assert report["total_rows"] == 1
    assert len(report["trialcode_profiles"]) == 1
