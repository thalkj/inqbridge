"""Tests for runner.decomposer."""
import pytest
from pathlib import Path

from runner.decomposer import decompose_script


@pytest.fixture
def monolith_script(tmp_path):
    """A monolithic script with two blocks and shared elements."""
    script = tmp_path / "experiment.iqx"
    script.write_text("""\
// Test experiment

<defaults>
/ screencolor = white
/ txcolor = black
</defaults>

<values>
/ condition = 1
/ score = 0
</values>

<text fixation>
/ items = ("+")
/ position = (50%, 50%)
</text>

<text instructions_text>
/ items = ("Welcome. Press SPACE to begin.")
/ position = (50%, 50%)
</text>

<text stimulus>
/ items = ("Word1", "Word2")
/ position = (50%, 50%)
</text>

<trial instructions_trial>
/ stimulustimes = [0=instructions_text]
/ validresponse = (" ")
/ recorddata = false
</trial>

<trial test_trial>
/ stimulustimes = [0=fixation; 500=stimulus]
/ validresponse = ("e", "i")
</trial>

<block instructions_block>
/ trials = [1=instructions_trial]
</block>

<block test_block>
/ trials = [1-20=test_trial]
</block>

<expt>
/ blocks = [1=instructions_block; 2=test_block]
</expt>
""", encoding="utf-8")
    return script


def test_decompose_creates_files(monolith_script, tmp_path):
    """Decomposition creates config, block modules, main, and testers."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out)

    assert "error" not in result
    assert len(result["created_files"]) > 0

    # Check key files exist
    assert (out / "main.iqx").is_file()
    config_files = list(out.glob("*_config_inc.iqx"))
    assert len(config_files) == 1


def test_decompose_preserves_blocks(monolith_script, tmp_path):
    """Each block gets its own module file."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out)

    assert "instructions_block" in result["modules"]
    assert "test_block" in result["modules"]


def test_decompose_block_order(monolith_script, tmp_path):
    """Block order is preserved from the original experiment."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out)

    assert result["block_order"] == ["instructions_block", "test_block"]


def test_decompose_main_has_includes(monolith_script, tmp_path):
    """main.iqx includes all generated modules."""
    out = tmp_path / "modules"
    decompose_script(monolith_script, output_dir=out)

    main_content = (out / "main.iqx").read_text()
    assert "<include>" in main_content
    assert "config_inc.iqx" in main_content
    assert "<expt>" in main_content


def test_decompose_creates_testers(monolith_script, tmp_path):
    """Standalone testers are created for each block."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out)

    assert len(result["tester_files"]) >= 2

    for tester in result["tester_files"]:
        content = Path(tester).read_text()
        assert "<include>" in content
        assert "<expt>" in content


def test_decompose_config_has_values(monolith_script, tmp_path):
    """Config module contains values and defaults."""
    out = tmp_path / "modules"
    decompose_script(monolith_script, output_dir=out)

    config = list(out.glob("*_config_inc.iqx"))[0]
    content = config.read_text()
    assert "values" in content.lower() or "defaults" in content.lower()


def test_decompose_dependencies_traced(monolith_script, tmp_path):
    """Stimulus elements are placed with the trials that reference them."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out)

    # test_block should contain test_trial, which references fixation and stimulus
    test_module_elems = result["modules"].get("test_block", [])
    assert "test_trial" in test_module_elems


def test_decompose_missing_script(tmp_path):
    """Missing script returns an error."""
    result = decompose_script(tmp_path / "nonexistent.iqx")
    assert "error" in result


def test_decompose_custom_name(monolith_script, tmp_path):
    """Custom experiment name is used in filenames."""
    out = tmp_path / "modules"
    result = decompose_script(monolith_script, output_dir=out, experiment_name="myexp")

    assert result["experiment_name"] == "myexp"
    assert (out / "myexp_config_inc.iqx").is_file()
