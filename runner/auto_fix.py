"""Auto-fix common Inquisit compile errors detected by preflight.

Attempts safe, conservative fixes for compile failures:
- Missing file references: comments out the element
- Phantom references: removes the reference from stimulusframes/stimulustimes
- Bracket bugs: flagged but NOT auto-fixed (too risky)
"""
from __future__ import annotations

import re
from pathlib import Path


def attempt_auto_fix(
    script_path: Path,
    include_paths: list[Path],
    issues: list[dict],
) -> dict:
    """Attempt to auto-fix preflight issues in script files.

    Only fixes issues that are safe to auto-fix. Bracket bugs are
    reported but not touched.

    Args:
        script_path: Main script path.
        include_paths: Include file paths.
        issues: List of issue dicts from preflight_check.

    Returns:
        Dict with 'fixed' (list of fixes applied), 'unfixable' (list of
        issues that couldn't be auto-fixed), 'files_modified' (list of paths).
    """
    fixed: list[dict] = []
    unfixable: list[dict] = []
    files_modified: set[str] = set()

    # Group issues by type
    missing_file_issues = [i for i in issues if i.get("check") == "missing_file"]
    bracket_issues = [i for i in issues if i.get("check") == "bracket_mismatch"]
    undefined_issues = [i for i in issues if i.get("check") == "undefined_reference"]

    # Bracket bugs: never auto-fix
    for issue in bracket_issues:
        unfixable.append({
            **issue,
            "reason": "Bracket bugs require manual review — auto-fix is too risky",
        })

    # Missing file references: comment out the element
    if missing_file_issues:
        _fix_missing_files(script_path, include_paths, missing_file_issues, fixed, files_modified)

    # Phantom references: remove from stimulusframes/stimulustimes
    if undefined_issues:
        _fix_undefined_refs(script_path, include_paths, undefined_issues, fixed, unfixable, files_modified)

    return {
        "fixed_count": len(fixed),
        "fixed": fixed,
        "unfixable_count": len(unfixable),
        "unfixable": unfixable,
        "files_modified": sorted(files_modified),
    }


def _fix_missing_files(
    script_path: Path,
    include_paths: list[Path],
    issues: list[dict],
    fixed: list[dict],
    files_modified: set[str],
) -> None:
    """Comment out elements that reference missing files."""
    all_files = [script_path] + list(include_paths)

    # Collect element names to disable
    elements_to_disable: set[tuple[str, str]] = set()
    for issue in issues:
        elem_type = issue.get("element_type", "")
        elem_name = issue.get("element_name", "")
        if elem_type and elem_name:
            elements_to_disable.add((elem_type.lower(), elem_name.lower()))

    for fpath in all_files:
        if not fpath.is_file():
            continue
        source = fpath.read_text(encoding="utf-8-sig")
        modified = False

        for elem_type, elem_name in elements_to_disable:
            # Pattern: <picture name> ... </picture>
            pattern = re.compile(
                rf"(<{elem_type}\s+{elem_name}\s*>.*?</{elem_type}>)",
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(source)
            if match:
                original_block = match.group(1)
                # Comment out each line
                commented = "\n".join(
                    f"// AUTO-DISABLED: {line}" if line.strip() else line
                    for line in original_block.splitlines()
                )
                source = source.replace(original_block, commented)
                modified = True
                fixed.append({
                    "fix": "commented_out_element",
                    "element": f"<{elem_type} {elem_name}>",
                    "file": fpath.name,
                    "reason": f"Missing file reference",
                })

        if modified:
            fpath.write_text(source, encoding="utf-8")
            files_modified.add(str(fpath))


def _fix_undefined_refs(
    script_path: Path,
    include_paths: list[Path],
    issues: list[dict],
    fixed: list[dict],
    unfixable: list[dict],
    files_modified: set[str],
) -> None:
    """Remove undefined references from stimulusframes and stimulustimes."""
    all_files = [script_path] + list(include_paths)

    # Collect undefined names
    undefined_names: set[str] = set()
    for issue in issues:
        name = issue.get("undefined_name", "").lower()
        if name:
            undefined_names.add(name)

    if not undefined_names:
        return

    for fpath in all_files:
        if not fpath.is_file():
            continue
        source = fpath.read_text(encoding="utf-8-sig")
        original_source = source
        modified = False

        for name in undefined_names:
            # Remove from stimulustimes: [0=fixation; 500=UNDEFINED; 1000=stimulus]
            # Remove the entry containing the undefined name
            def _remove_from_bracket_list(match: re.Match) -> str:
                prefix = match.group(1)
                body = match.group(2)
                suffix = match.group(3)

                parts = []
                for entry in body.split(";"):
                    entry_stripped = entry.strip()
                    # Check if this entry contains the undefined name
                    entry_names = re.findall(r'\b(\w+)\b', entry_stripped)
                    entry_names_lower = [n.lower() for n in entry_names]
                    if name not in entry_names_lower:
                        parts.append(entry.strip())
                    # If entry has multiple comma-separated names, only remove the undefined one
                    elif "," in entry_stripped:
                        # "500=good, UNDEFINED, other" → "500=good, other"
                        sub_parts = []
                        if "=" in entry_stripped:
                            time_prefix, rest = entry_stripped.split("=", 1)
                            for sub in rest.split(","):
                                if sub.strip().lower() != name:
                                    sub_parts.append(sub.strip())
                            if sub_parts:
                                parts.append(f"{time_prefix}={', '.join(sub_parts)}")
                        else:
                            for sub in entry_stripped.split(","):
                                if sub.strip().lower() != name:
                                    sub_parts.append(sub.strip())
                            if sub_parts:
                                parts.append(", ".join(sub_parts))

                return f"{prefix}{'; '.join(parts)}{suffix}"

            # Apply to stimulustimes
            pattern_st = re.compile(
                r"(/\s*stimulustimes\s*=\s*\[)([^\]]+)(\])",
                re.IGNORECASE,
            )
            new_source = pattern_st.sub(_remove_from_bracket_list, source)

            # Apply to stimulusframes
            pattern_sf = re.compile(
                r"(/\s*stimulusframes\s*=\s*\[)([^\]]+)(\])",
                re.IGNORECASE,
            )
            new_source = pattern_sf.sub(_remove_from_bracket_list, new_source)

            if new_source != source:
                source = new_source
                modified = True
                fixed.append({
                    "fix": "removed_undefined_reference",
                    "name": name,
                    "file": fpath.name,
                    "reason": f"Element '{name}' was referenced but never defined",
                })

        if modified:
            fpath.write_text(source, encoding="utf-8")
            files_modified.add(str(fpath))
