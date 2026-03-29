"""Delivery preparation: strip debug artifacts, validate, and package.

Combines several delivery-prep steps into one tool:
1. Strip screenCapture=true
2. Strip debug overlay elements
3. Run validate_merge (check no placeholders)
4. Run preflight_check
5. Generate experiment spec
6. Package into self-contained folder
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .capture_manager import strip_screencapture_files
from .includes import discover_includes
from .merge_validator import validate_merge
from .preflight import preflight_check
from .spec_generator import generate_spec


def _strip_debug_elements(script_path: Path, include_paths: list[Path]) -> dict:
    """Remove elements with names starting with 'debug_' from scripts.

    Args:
        script_path: Main script path.
        include_paths: Include file paths.

    Returns:
        Dict with files modified and elements removed.
    """
    import re

    all_files = [script_path] + list(include_paths)
    results = {"files_modified": [], "elements_removed": []}

    debug_pattern = re.compile(
        r"<(\w+)\s+(debug_\w+)\s*>.*?</\1>",
        re.IGNORECASE | re.DOTALL,
    )

    for fpath in all_files:
        if not fpath.is_file():
            continue
        source = fpath.read_text(encoding="utf-8-sig")
        matches = list(debug_pattern.finditer(source))
        if matches:
            for m in reversed(matches):
                results["elements_removed"].append(f"<{m.group(1)} {m.group(2)}>")
                source = source[:m.start()] + source[m.end():]
            fpath.write_text(source, encoding="utf-8")
            results["files_modified"].append(fpath.name)

    return results


def prepare_delivery(
    script_path: Path,
    output_dir: Path | None = None,
    include_search_dirs: list[Path] | None = None,
) -> dict:
    """Prepare a script for delivery.

    Steps:
    1. Strip screenCapture=true from all files
    2. Strip debug overlay elements (named debug_*)
    3. Validate merge (check for placeholders and conflicts)
    4. Run preflight check
    5. Generate experiment spec
    6. Package into self-contained folder

    Args:
        script_path: Path to the main .iqx script.
        output_dir: Where to write the delivery package. Defaults to
                     script_path.parent / "{stem}_delivery".
        include_search_dirs: Directories to search for includes.

    Returns:
        Dict with delivery report: steps completed, issues found, output path.
    """
    search_dirs = include_search_dirs or []
    includes = discover_includes(script_path, search_dirs=search_dirs)

    report = {
        "steps": [],
        "issues": [],
        "passed": True,
    }

    # Step 1: Strip screenCapture
    cap_result = strip_screencapture_files(script_path, includes)
    report["steps"].append({
        "step": "strip_screencapture",
        "files_modified": cap_result["files_modified"],
        "lines_removed": cap_result["total_lines_removed"],
    })

    # Step 2: Strip debug elements
    debug_result = _strip_debug_elements(script_path, includes)
    report["steps"].append({
        "step": "strip_debug_elements",
        "files_modified": debug_result["files_modified"],
        "elements_removed": debug_result["elements_removed"],
    })

    # Step 3: Validate merge
    all_files = [script_path] + includes
    merge_result = validate_merge(all_files)
    report["steps"].append({
        "step": "validate_merge",
        "passed": merge_result["passed"],
        "conflicts": merge_result["conflict_count"],
        "placeholders": merge_result["placeholder_count"],
    })
    if not merge_result["passed"]:
        report["passed"] = False
        if merge_result["placeholder_count"] > 0:
            report["issues"].append(
                f"{merge_result['placeholder_count']} unresolved PLACEHOLDER values"
            )
        if merge_result["conflict_count"] > 0:
            report["issues"].append(
                f"{merge_result['conflict_count']} namespace conflicts"
            )

    # Step 4: Preflight check
    preflight_result = preflight_check(script_path, include_search_dirs=search_dirs)
    report["steps"].append({
        "step": "preflight_check",
        "passed": preflight_result["passed"],
        "error_count": preflight_result["error_count"],
    })
    if not preflight_result["passed"]:
        report["passed"] = False
        report["issues"].append(
            f"Preflight found {preflight_result['error_count']} errors"
        )

    # Step 5: Generate spec
    spec = generate_spec(script_path, include_search_dirs=search_dirs)
    report["spec"] = spec
    report["steps"].append({"step": "generate_spec", "completed": True})

    if spec.get("warnings"):
        for w in spec["warnings"]:
            report["issues"].append(w)

    # Step 6: Package
    if output_dir is None:
        output_dir = script_path.parent / f"{script_path.stem}_delivery"
    output_dir.mkdir(parents=True, exist_ok=True)

    packaged_files = []

    # Copy main script
    shutil.copy2(script_path, output_dir / script_path.name)
    packaged_files.append(script_path.name)

    # Copy includes
    for inc in includes:
        if inc.is_file():
            shutil.copy2(inc, output_dir / inc.name)
            packaged_files.append(inc.name)

    # Copy media files referenced in scripts (pictures, sounds, videos)
    _copy_media_files(script_path, includes, output_dir)

    report["steps"].append({
        "step": "package",
        "output_dir": str(output_dir),
        "files_packaged": packaged_files,
    })
    report["output_dir"] = str(output_dir)

    return report


def _copy_media_files(
    script_path: Path,
    include_paths: list[Path],
    output_dir: Path,
) -> None:
    """Copy referenced media files (images, sounds, videos) to output."""
    import re

    items_pattern = re.compile(r'/\s*items\s*=\s*\(([^)]+)\)', re.IGNORECASE)
    quoted = re.compile(r'"([^"]+)"')
    media_types = {"picture", "sound", "video"}

    block_pattern = re.compile(
        r"<(\w+)\s+(\w+)\s*>(.*?)</\1>",
        re.IGNORECASE | re.DOTALL,
    )

    all_files = [script_path] + list(include_paths)
    script_dir = script_path.parent

    for fpath in all_files:
        if not fpath.is_file():
            continue
        source = fpath.read_text(encoding="utf-8-sig")

        for m in block_pattern.finditer(source):
            elem_type = m.group(1).lower()
            if elem_type not in media_types:
                continue
            body = m.group(3)
            items_match = items_pattern.search(body)
            if not items_match:
                continue
            filenames = quoted.findall(items_match.group(1))
            for fname in filenames:
                if fname.startswith("%") or fname.startswith("$"):
                    continue
                src = script_dir / fname
                if src.is_file():
                    dest = output_dir / fname
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
