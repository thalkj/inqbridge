"""Tests for constrained layout patcher."""
import pytest
from pathlib import Path
from runner.patcher import Patch, validate_patches, apply_patches


def test_allowed_attributes_pass():
    patches = [
        Patch("test.iqx", "<text t>", "position", "50%", "60%"),
        Patch("test.iqx", "<text t>", "size", "80%", "90%"),
        Patch("test.iqx", "<defaults>", "fontstyle", '"Arial" 12pt', '"Arial" 14pt'),
    ]
    errors = validate_patches(patches)
    assert errors == []


def test_forbidden_attributes_blocked():
    patches = [
        Patch("test.iqx", "<text t>", "validresponse", "1 2 3", "1 2 3 4"),
    ]
    errors = validate_patches(patches)
    assert len(errors) == 1
    assert "validresponse" in errors[0]


def test_correctresponse_blocked():
    patches = [
        Patch("test.iqx", "<trial t>", "correctresponse", "1", "2"),
    ]
    errors = validate_patches(patches)
    assert len(errors) == 1


def test_apply_patches_modifies_file(tmp_path):
    script = tmp_path / "test.iqx"
    script.write_text(
        '<text myText>\n/ position = (50%, 50%)\n/ size = (80%, 20%)\n</text>',
        encoding="utf-8",
    )

    patches = [
        Patch(str(script), "<text myText>", "position", "(50%, 50%)", "(60%, 40%)"),
    ]
    results = apply_patches(patches)

    assert results[0]["status"] == "applied"
    content = script.read_text(encoding="utf-8")
    assert "(60%, 40%)" in content
    assert "(50%, 50%)" not in content


def test_dry_run_does_not_modify(tmp_path):
    script = tmp_path / "test.iqx"
    original = '<text myText>\n/ position = (50%, 50%)\n</text>'
    script.write_text(original, encoding="utf-8")

    patches = [
        Patch(str(script), "<text myText>", "position", "(50%, 50%)", "(60%, 40%)"),
    ]
    results = apply_patches(patches, dry_run=True)

    assert results[0]["status"] == "would_apply"
    assert script.read_text(encoding="utf-8") == original


def test_apply_rejects_forbidden(tmp_path):
    script = tmp_path / "test.iqx"
    script.write_text('<trial t>\n/ validresponse = (1, 2)\n</trial>', encoding="utf-8")

    patches = [
        Patch(str(script), "<trial t>", "validresponse", "(1, 2)", "(1, 2, 3)"),
    ]
    with pytest.raises(ValueError, match="validation failed"):
        apply_patches(patches)
