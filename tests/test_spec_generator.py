"""Tests for runner.spec_generator."""
import pytest
from pathlib import Path

from runner.spec_generator import generate_spec


@pytest.fixture
def simple_script(tmp_path):
    script = tmp_path / "test.iqx"
    script.write_text("""\
<values>
/ condition = 1
/ debug_mode = 0
</values>

<text fixation>
/ items = ("+")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 50%)
</text>

<text stimulus>
/ items = ("Word1", "Word2", "Word3")
/ fontstyle = ("Arial", 4%)
/ position = (50%, 50%)
</text>

<list words>
/ items = ("Word1", "Word2", "Word3", "Word4")
</list>

<trial test_trial>
/ stimulustimes = [0=fixation; 500=stimulus]
/ validresponse = ("e", "i")
/ correctresponse = ("e")
/ posttrialpause = 200
</trial>

<trial instruction_trial>
/ stimulustimes = [0=fixation]
/ validresponse = (" ")
/ recorddata = false
</trial>

<block instructions_block>
/ trials = [1=instruction_trial]
</block>

<block test_block>
/ trials = [1-20=test_trial]
</block>

<expt>
/ blocks = [1=instructions_block; 2=test_block]
</expt>
""", encoding="utf-8")
    return script


def test_basic_spec(simple_script):
    """Spec is generated with all expected sections."""
    spec = generate_spec(simple_script)

    assert "participant_flow" in spec
    assert "response_mapping" in spec
    assert "data_schema" in spec
    assert "stimuli_inventory" in spec
    assert "warnings" in spec


def test_block_count(simple_script):
    """Block count matches the experiment definition."""
    spec = generate_spec(simple_script)
    assert spec["participant_flow"]["total_blocks"] == 2


def test_trial_count(simple_script):
    """Trial count includes range-based trial counts."""
    spec = generate_spec(simple_script)
    assert spec["participant_flow"]["total_trials"] == 21  # 1 + 20


def test_response_mapping(simple_script):
    """Response keys are extracted from trials."""
    spec = generate_spec(simple_script)
    assert "test_trial" in spec["response_mapping"]
    assert spec["response_mapping"]["test_trial"]["valid_responses"] == ["e", "i"]
    assert spec["response_mapping"]["test_trial"]["correct_response"] == ["e"]


def test_data_schema(simple_script):
    """Data schema includes accuracy when correctresponse is present."""
    spec = generate_spec(simple_script)
    assert spec["data_schema"]["has_accuracy_scoring"] is True
    assert "correct" in spec["data_schema"]["standard_columns"]


def test_custom_values(simple_script):
    """Custom values are detected."""
    spec = generate_spec(simple_script)
    assert "condition" in spec["data_schema"]["custom_values"]


def test_stimuli_inventory(simple_script):
    """Stimuli counts are correct."""
    spec = generate_spec(simple_script)
    assert spec["stimuli_inventory"]["summary"]["text_elements"] == 2
    assert spec["stimuli_inventory"]["summary"]["lists"] == 1
    assert spec["stimuli_inventory"]["lists"][0]["item_count"] == 4


def test_duration_estimate(simple_script):
    """Duration estimate is reasonable (> 0)."""
    spec = generate_spec(simple_script)
    assert spec["participant_flow"]["estimated_duration_seconds"] > 0


def test_no_warnings_clean_script(simple_script):
    """Clean script has no screenCapture warnings."""
    spec = generate_spec(simple_script)
    assert not any("screenCapture" in w for w in spec["warnings"])


def test_screencapture_warning(tmp_path):
    """Script with screenCapture=true triggers a warning."""
    script = tmp_path / "test.iqx"
    script.write_text("""\
<trial t>
/ screenCapture = true
/ validresponse = (" ")
</trial>
<block b>
/ trials = [1=t]
</block>
<expt>
/ blocks = [1=b]
</expt>
""")
    spec = generate_spec(script)
    assert any("screenCapture" in w for w in spec["warnings"])


def test_empty_script(tmp_path):
    """Empty script produces a valid (if empty) spec."""
    script = tmp_path / "empty.iqx"
    script.write_text("")
    spec = generate_spec(script)
    assert spec["participant_flow"]["total_blocks"] == 0
    assert spec["participant_flow"]["total_trials"] == 0
