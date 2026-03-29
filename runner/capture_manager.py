"""Manage screenCapture injection and stripping for development and delivery.

- inject: add `/ screenCapture = true` to all trials in temp copies (for dev runs)
- strip: remove `/ screenCapture = true` from actual files (for delivery)
"""
from __future__ import annotations

import re
from pathlib import Path


# Pattern: <trial name> ... </trial>
_TRIAL_BLOCK = re.compile(
    r"(<trial\s+\w+\s*>)(.*?)(</trial>)",
    re.IGNORECASE | re.DOTALL,
)

# Existing screenCapture line
_SCREENCAPTURE_LINE = re.compile(
    r"^\s*/\s*screenCapture\s*=\s*(true|false)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def inject_screencapture(source: str) -> str:
    """Add `/ screenCapture = true` to every trial that doesn't already have it.

    Args:
        source: Script text.

    Returns:
        Modified script text with screenCapture injected.
    """
    def _inject_in_trial(match: re.Match) -> str:
        open_tag = match.group(1)
        body = match.group(2)
        close_tag = match.group(3)

        # Skip if already has screenCapture
        if _SCREENCAPTURE_LINE.search(body):
            return match.group(0)

        # Add screenCapture = true as first attribute
        return f"{open_tag}\n/ screenCapture = true{body}{close_tag}"

    return _TRIAL_BLOCK.sub(_inject_in_trial, source)


def strip_screencapture(source: str) -> str:
    """Remove all `/ screenCapture = true` lines from script text.

    Args:
        source: Script text.

    Returns:
        Modified script text with screenCapture lines removed.
    """
    return _SCREENCAPTURE_LINE.sub("", source)


def create_captured_copies(
    script_path: Path,
    include_paths: list[Path],
) -> tuple[Path, list[Path], list[Path]]:
    """Create temporary copies with screenCapture injected into all trials.

    Temp files are in the same directory as originals (for Inquisit path resolution).

    Args:
        script_path: Main script path.
        include_paths: Include file paths.

    Returns:
        (captured_script, captured_includes, all_temp_paths)
    """
    all_temps: list[Path] = []

    def _make_temp(original: Path) -> Path:
        temp_name = original.stem + "_cap_tmp" + original.suffix
        temp_path = original.parent / temp_name
        source = original.read_text(encoding="utf-8-sig")
        captured = inject_screencapture(source)
        # Rewrite include references
        for inc in include_paths:
            inc_cap_name = inc.stem + "_cap_tmp" + inc.suffix
            captured = captured.replace(f'"{inc.name}"', f'"{inc_cap_name}"')
        temp_path.write_text(captured, encoding="utf-8")
        all_temps.append(temp_path)
        return temp_path

    cap_script = _make_temp(script_path)
    cap_includes = [_make_temp(inc) for inc in include_paths]

    return cap_script, cap_includes, all_temps


def cleanup_temp_copies(temp_paths: list[Path]) -> None:
    """Delete temporary captured copies."""
    for p in temp_paths:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


def strip_screencapture_files(
    script_path: Path,
    include_paths: list[Path] | None = None,
) -> dict:
    """Permanently remove `/ screenCapture = true` from script and includes.

    This modifies the actual files — use for delivery preparation.

    Args:
        script_path: Main script path.
        include_paths: Include file paths.

    Returns:
        Dict with files modified and lines removed per file.
    """
    all_files = [script_path] + (include_paths or [])
    results = {"files_modified": [], "total_lines_removed": 0}

    for f in all_files:
        if not f.is_file():
            continue
        source = f.read_text(encoding="utf-8-sig")
        matches = _SCREENCAPTURE_LINE.findall(source)
        if matches:
            cleaned = strip_screencapture(source)
            f.write_text(cleaned, encoding="utf-8")
            results["files_modified"].append(str(f.name))
            results["total_lines_removed"] += len(matches)

    return results
