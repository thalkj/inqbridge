"""Fast-run mode: override stimulustimes and pauses for quick compile/data checks.

Creates temporary copies of scripts with all timing set to near-zero,
runs them, then cleans up. The original scripts are never modified.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path


# Patterns to override
_STIMULUSTIMES_ATTR = re.compile(
    r"(/\s*stimulustimes\s*=\s*\[)([^\]]+)(\])",
    re.IGNORECASE,
)
_POSTTRIALPAUSE = re.compile(
    r"/\s*posttrialpause\s*=\s*\d+",
    re.IGNORECASE,
)
_PRETRIALPAUSE = re.compile(
    r"/\s*pretrialpause\s*=\s*\d+",
    re.IGNORECASE,
)
_TIMEOUT_ATTR = re.compile(
    r"/\s*timeout\s*=\s*\d+",
    re.IGNORECASE,
)


def _collapse_stimulustimes(match: re.Match) -> str:
    """Collapse stimulustimes so all stimuli appear at t=0.

    Input:  [0=fixation; 500=stimulus; 1000=feedback]
    Output: [0=fixation, stimulus, feedback]
    """
    prefix = match.group(1)
    body = match.group(2)
    suffix = match.group(3)

    # Extract all element names, stripping timing prefixes (e.g., "500=")
    names = []
    for part in body.split(";"):
        part = part.strip()
        if not part:
            continue
        # Each part may be: "500=elem1, elem2" or just "elem1, elem2"
        if "=" in part:
            _, elems = part.split("=", 1)
        else:
            elems = part
        for elem in elems.split(","):
            elem = elem.strip()
            if elem:
                names.append(elem)

    return f"{prefix}0={', '.join(names)}{suffix}"


def make_fast_copy(source: str) -> str:
    """Transform script source text for fast-run mode.

    - Collapses stimulustimes to t=0
    - Sets posttrialpause = 0
    - Sets pretrialpause = 0
    - Sets timeout = 100 (not 0 — zero means no timeout in Inquisit)

    Args:
        source: Original .iqx script text.

    Returns:
        Modified script text for fast-run.
    """
    result = source

    # Collapse stimulustimes
    result = _STIMULUSTIMES_ATTR.sub(_collapse_stimulustimes, result)

    # Zero out pauses
    result = _POSTTRIALPAUSE.sub("/ posttrialpause = 0", result)
    result = _PRETRIALPAUSE.sub("/ pretrialpause = 0", result)

    # Minimize timeout (100ms, not 0)
    result = _TIMEOUT_ATTR.sub("/ timeout = 100", result)

    return result


def create_fast_copies(
    script_path: Path,
    include_paths: list[Path],
) -> tuple[Path, list[Path], list[Path]]:
    """Create temporary fast-mode copies of a script and its includes.

    Temp files are created in the same directory as the originals
    (so Inquisit finds stimuli and data/ relative paths correctly).
    Named with a `_fast_tmp` suffix to avoid collisions.

    Args:
        script_path: Path to the main .iqx script.
        include_paths: Paths to all included .iqx files.

    Returns:
        Tuple of (fast_script_path, fast_include_paths, all_temp_paths_to_clean).
    """
    all_temps: list[Path] = []

    def _make_temp(original: Path) -> Path:
        temp_name = original.stem + "_fast_tmp" + original.suffix
        temp_path = original.parent / temp_name
        source = original.read_text(encoding="utf-8-sig")
        fast_source = make_fast_copy(source)
        # Also rewrite include references to point to fast copies
        for inc in include_paths:
            inc_fast_name = inc.stem + "_fast_tmp" + inc.suffix
            fast_source = fast_source.replace(f'"{inc.name}"', f'"{inc_fast_name}"')
        temp_path.write_text(fast_source, encoding="utf-8")
        all_temps.append(temp_path)
        return temp_path

    fast_script = _make_temp(script_path)
    fast_includes = [_make_temp(inc) for inc in include_paths]

    return fast_script, fast_includes, all_temps


def cleanup_fast_copies(temp_paths: list[Path]) -> None:
    """Delete temporary fast-mode copies."""
    for p in temp_paths:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
