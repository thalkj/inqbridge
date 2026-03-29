"""Tests for runner.scaffold."""
import pytest
from pathlib import Path

from runner.scaffold import scaffold_experiment, SUPPORTED_TYPES, DEFAULT_MODULES


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "test_experiment"


def test_custom_scaffold(output_dir):
    """Custom experiment generates all default modules + main + testers."""
    result = scaffold_experiment(
        experiment_name="my_task",
        experiment_type="custom",
        output_dir=output_dir,
    )
    assert "error" not in result
    assert result["experiment_type"] == "custom"
    assert "config" in result["modules"]
    assert "test" in result["modules"]

    # main.iqx should exist
    main = output_dir / "main.iqx"
    assert main.is_file()
    content = main.read_text(encoding="utf-8")
    assert "my_task_config_inc.iqx" in content
    assert "<expt>" in content

    # Module files should exist
    for role in result["modules"]:
        inc_file = output_dir / f"my_task_{role}_inc.iqx"
        assert inc_file.is_file(), f"Missing: {inc_file.name}"


def test_iat_scaffold(output_dir):
    """IAT scaffold generates paradigm-specific templates."""
    result = scaffold_experiment(
        experiment_name="flower_iat",
        experiment_type="iat",
        output_dir=output_dir,
    )
    assert "error" not in result

    # IAT config should have category labels
    config = output_dir / "flower_iat_config_inc.iqx"
    content = config.read_text(encoding="utf-8")
    assert "category_a_label" in content.lower() or "Category A" in content

    # IAT test should have iat-specific trials
    test = output_dir / "flower_iat_test_inc.iqx"
    content = test.read_text(encoding="utf-8")
    assert "iat" in content.lower()


def test_all_types_generate(tmp_path):
    """Every supported type generates without error."""
    for exp_type in SUPPORTED_TYPES:
        out = tmp_path / exp_type
        result = scaffold_experiment(
            experiment_name=f"test_{exp_type}",
            experiment_type=exp_type,
            output_dir=out,
        )
        assert "error" not in result, f"Failed for type: {exp_type}"
        assert len(result["created_files"]) > 0


def test_standalone_testers_created(output_dir):
    """Standalone test files are generated for each non-config module."""
    result = scaffold_experiment(
        experiment_name="my_task",
        experiment_type="custom",
        output_dir=output_dir,
    )
    tester_files = result["tester_files"]
    assert len(tester_files) > 0

    for tester_path in tester_files:
        p = Path(tester_path)
        assert p.is_file()
        content = p.read_text(encoding="utf-8")
        assert "<include>" in content
        assert "<expt>" in content


def test_custom_modules(output_dir):
    """Custom module list overrides defaults."""
    result = scaffold_experiment(
        experiment_name="minimal",
        experiment_type="custom",
        modules=["config", "test"],
        output_dir=output_dir,
    )
    assert result["modules"] == ["config", "test"]
    assert (output_dir / "minimal_config_inc.iqx").is_file()
    assert (output_dir / "minimal_test_inc.iqx").is_file()
    assert not (output_dir / "minimal_practice_inc.iqx").exists()


def test_unknown_type():
    """Unknown experiment type returns an error."""
    result = scaffold_experiment(
        experiment_name="bad",
        experiment_type="unknown_paradigm",
    )
    assert "error" in result


def test_unknown_role_generates_stub(output_dir):
    """Unknown module role generates a minimal stub."""
    result = scaffold_experiment(
        experiment_name="my_task",
        experiment_type="custom",
        modules=["config", "calibration"],
        output_dir=output_dir,
    )
    assert "error" not in result
    stub = output_dir / "my_task_calibration_inc.iqx"
    assert stub.is_file()
    content = stub.read_text(encoding="utf-8")
    assert "calibration" in content.lower()
