"""Pre-flight validation for .iqx scripts.

Catches common issues BEFORE launching Inquisit, which has unhelpful error messages:
- Missing file references (<picture>, <sound>, <video> elements)
- Unclosed brackets in attribute values
- Elements referenced but never defined (stimulusframes, block/trials, etc.)

All checks are static — they parse the script text without running it.
"""
from __future__ import annotations

import re
from pathlib import Path

from .includes import discover_includes, INCLUDE_PATTERN


# ---------------------------------------------------------------------------
# File reference checker
# ---------------------------------------------------------------------------

# Elements that reference external files via / items
_FILE_ELEMENT_TYPES = {"picture", "sound", "video"}

# Pattern: <picture name> ... / items = ("file1.png", "file2.png") ... </picture>
_ELEMENT_BLOCK_PATTERN = re.compile(
    r"<(\w+)\s+(\w+)\s*>(.*?)</\1>", re.IGNORECASE | re.DOTALL
)

# Pattern for / items = (...) inside an element block
_ITEMS_PATTERN = re.compile(
    r"/\s*items\s*=\s*\(([^)]*)\)", re.IGNORECASE
)

# Pattern for individual quoted filenames
_QUOTED_STRING = re.compile(r'"([^"]+)"')


def check_missing_files(
    script_path: Path,
    include_paths: list[Path] | None = None,
) -> list[dict]:
    """Check that all file references in <picture>, <sound>, <video> elements exist.

    Inquisit treats missing file references as a fatal compile error —
    the script exits with code 0, no data, and an unhelpful 'Network Error'.

    Args:
        script_path: Path to the main .iqx script.
        include_paths: Additional included files to check.

    Returns:
        List of issue dicts with keys: check, severity, element_type,
        element_name, missing_file, message.
    """
    script_dir = script_path.parent
    all_paths = [script_path] + (include_paths or [])

    combined_source = ""
    for p in all_paths:
        if p.is_file():
            try:
                combined_source += p.read_text(encoding="utf-8-sig") + "\n"
            except Exception:
                pass

    issues: list[dict] = []

    for m in _ELEMENT_BLOCK_PATTERN.finditer(combined_source):
        elem_type = m.group(1).lower()
        elem_name = m.group(2)
        body = m.group(3)

        if elem_type not in _FILE_ELEMENT_TYPES:
            continue

        items_match = _ITEMS_PATTERN.search(body)
        if not items_match:
            continue

        raw_items = items_match.group(1)
        filenames = _QUOTED_STRING.findall(raw_items)

        for fname in filenames:
            # Skip Inquisit built-in references (e.g., expressions, wildcards)
            if fname.startswith("%") or fname.startswith("$"):
                continue

            file_path = script_dir / fname
            if not file_path.is_file():
                issues.append({
                    "check": "missing_file",
                    "severity": "error",
                    "element_type": elem_type,
                    "element_name": elem_name,
                    "missing_file": fname,
                    "message": (
                        f"<{elem_type} {elem_name}> references '{fname}' "
                        f"but file not found at {file_path}"
                    ),
                })

    return issues


# ---------------------------------------------------------------------------
# Bracket matching
# ---------------------------------------------------------------------------

def check_brackets(
    script_path: Path,
    include_paths: list[Path] | None = None,
) -> list[dict]:
    """Check for unclosed or mismatched brackets in attribute values.

    Inquisit uses [ ] for expressions in /ontrialbegin, /ontrialend, etc.
    An unclosed bracket causes a silent compilation failure.

    Args:
        script_path: Path to the main .iqx script.
        include_paths: Additional included files to check.

    Returns:
        List of issue dicts with keys: check, severity, file, line,
        attribute, message.
    """
    all_paths = [script_path] + (include_paths or [])
    issues: list[dict] = []

    for p in all_paths:
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8-sig").splitlines()
        except Exception:
            continue

        _check_brackets_in_file(p, lines, issues)

    return issues


def _check_brackets_in_file(
    file_path: Path, lines: list[str], issues: list[dict]
) -> None:
    """Check bracket balance within a single file."""
    # Track bracket depth across continuation lines within attribute blocks
    in_bracket_expr = False
    bracket_depth = 0
    attr_start_line = 0
    attr_name = ""

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments (lines starting with // or **)
        if stripped.startswith("//") or stripped.startswith("**"):
            continue

        # Detect attribute assignment lines: / attrname = [
        attr_match = re.match(r"/\s*(\w+)\s*=\s*(.*)", stripped)
        if attr_match and not in_bracket_expr:
            attr_name = attr_match.group(1)
            rest = attr_match.group(2)
            open_count = rest.count("[")
            close_count = rest.count("]")
            if open_count > close_count:
                in_bracket_expr = True
                bracket_depth = open_count - close_count
                attr_start_line = i
            elif close_count > open_count:
                issues.append({
                    "check": "bracket_mismatch",
                    "severity": "error",
                    "file": str(file_path),
                    "line": i,
                    "attribute": attr_name,
                    "message": (
                        f"Line {i}: Extra closing bracket(s) in "
                        f"/{attr_name} ({close_count - open_count} unmatched ']')"
                    ),
                })
            continue

        # If we're inside an unclosed bracket expression, track depth
        if in_bracket_expr:
            # Check if a new attribute starts before the bracket was closed
            new_attr = re.match(r"/\s*(\w+)\s*=\s*", stripped)
            if new_attr and "[" not in stripped:
                # New attribute started without closing the bracket
                issues.append({
                    "check": "bracket_mismatch",
                    "severity": "error",
                    "file": str(file_path),
                    "line": attr_start_line,
                    "attribute": attr_name,
                    "message": (
                        f"Line {attr_start_line}: Unclosed '[' in "
                        f"/{attr_name} — new attribute /{new_attr.group(1)} "
                        f"starts at line {i} before bracket was closed"
                    ),
                })
                in_bracket_expr = False
                bracket_depth = 0
                # Re-process this line as a new attribute
                rest = stripped[new_attr.end():]
                open_count = rest.count("[")
                close_count = rest.count("]")
                if open_count > close_count:
                    in_bracket_expr = True
                    bracket_depth = open_count - close_count
                    attr_start_line = i
                    attr_name = new_attr.group(1)
                continue

            bracket_depth += stripped.count("[")
            bracket_depth -= stripped.count("]")
            if bracket_depth <= 0:
                if bracket_depth < 0:
                    issues.append({
                        "check": "bracket_mismatch",
                        "severity": "error",
                        "file": str(file_path),
                        "line": i,
                        "attribute": attr_name,
                        "message": (
                            f"Line {i}: Extra closing bracket(s) in "
                            f"/{attr_name} continuation ({-bracket_depth} extra ']')"
                        ),
                    })
                in_bracket_expr = False
                bracket_depth = 0

    # If file ends with unclosed bracket
    if in_bracket_expr:
        issues.append({
            "check": "bracket_mismatch",
            "severity": "error",
            "file": str(file_path),
            "line": attr_start_line,
            "attribute": attr_name,
            "message": (
                f"Line {attr_start_line}: Unclosed '[' in /{attr_name} — "
                f"reached end of file with {bracket_depth} unclosed bracket(s)"
            ),
        })


# ---------------------------------------------------------------------------
# Element reference checker
# ---------------------------------------------------------------------------

# Elements that define named things
_ELEMENT_DEF_PATTERN = re.compile(
    r"<(\w+)\s+(\w+)\s*>", re.IGNORECASE
)

# References in stimulusframes: / stimulusframes = [1=elem1, elem2; 2=elem3]
_STIMULUSFRAMES_PATTERN = re.compile(
    r"/\s*stimulusframes\s*=\s*\[([^\]]*)\]", re.IGNORECASE
)

# References in block /trials: / trials = [1=trial1; 2=trial2]
_BLOCK_TRIALS_PATTERN = re.compile(
    r"/\s*trials\s*=\s*\[([^\]]*)\]", re.IGNORECASE
)

# References in expt /blocks: / blocks = [1=block1; 2=block2]
_EXPT_BLOCKS_PATTERN = re.compile(
    r"/\s*blocks\s*=\s*\[([^\]]*)\]", re.IGNORECASE
)

# References in stimulustimes: / stimulustimes = [0=elem1; 500=elem2]
_STIMULUSTIMES_PATTERN = re.compile(
    r"/\s*stimulustimes\s*=\s*\[([^\]]*)\]", re.IGNORECASE
)

# Pattern to extract element names from bracket lists like [1=name1, name2; 2=name3]
_BRACKET_REFS = re.compile(r"(?:[\d]+=)?(\w+)")


def check_undefined_references(
    script_path: Path,
    include_paths: list[Path] | None = None,
) -> list[dict]:
    """Check that elements referenced in trials/blocks/stimulusframes are defined.

    AI-generated scripts often reference elements that were never defined.
    This catches those before Inquisit's cryptic compilation failure.

    Args:
        script_path: Path to the main .iqx script.
        include_paths: Additional included files to check.

    Returns:
        List of issue dicts with keys: check, severity, context,
        undefined_name, message.
    """
    all_paths = [script_path] + (include_paths or [])

    combined_source = ""
    for p in all_paths:
        if p.is_file():
            try:
                combined_source += p.read_text(encoding="utf-8-sig") + "\n"
            except Exception:
                pass

    # Step 1: Collect all defined element names
    defined: set[str] = set()
    for m in _ELEMENT_DEF_PATTERN.finditer(combined_source):
        elem_name = m.group(2).lower()
        defined.add(elem_name)

    # Step 2: Collect all referenced names and their contexts
    references: list[tuple[str, str, str]] = []  # (name, context_type, context_detail)

    # Inquisit keywords that look like element names but aren't
    _KEYWORDS = {
        "correct", "incorrect", "noresponse", "timeout", "nogo",
        "sequence", "random", "replace", "noreplacenorepeat",
        "values", "expressions", "parameters", "text", "picture",
        "sound", "video", "shape", "trial", "block", "expt",
        "surveypage", "list", "item", "display", "script",
        "monkey", "mouse", "keyboard", "clearscreen", "noreplace",
    }

    def _extract_refs(pattern, source, context_type):
        for m in pattern.finditer(source):
            bracket_content = m.group(1)
            # Split by ; for frame groups, then by , for items within
            for part in bracket_content.split(";"):
                for ref_match in _BRACKET_REFS.finditer(part):
                    name = ref_match.group(1).lower()
                    if name not in _KEYWORDS and not name.isdigit():
                        references.append((name, context_type, bracket_content.strip()))

    _extract_refs(_STIMULUSFRAMES_PATTERN, combined_source, "stimulusframes")
    _extract_refs(_STIMULUSTIMES_PATTERN, combined_source, "stimulustimes")
    _extract_refs(_BLOCK_TRIALS_PATTERN, combined_source, "block/trials")
    _extract_refs(_EXPT_BLOCKS_PATTERN, combined_source, "expt/blocks")

    # Step 3: Flag references that don't match any definition
    issues: list[dict] = []
    seen: set[str] = set()

    for name, context_type, context_detail in references:
        if name in defined:
            continue
        if name in seen:
            continue
        seen.add(name)

        issues.append({
            "check": "undefined_reference",
            "severity": "error",
            "context": context_type,
            "undefined_name": name,
            "message": (
                f"'{name}' is referenced in {context_type} but no "
                f"<element {name}> definition was found in the script"
            ),
        })

    return issues


# ---------------------------------------------------------------------------
# Main preflight entry point
# ---------------------------------------------------------------------------

def preflight_check(
    script_path: Path,
    include_search_dirs: list[Path] | None = None,
) -> dict:
    """Run all pre-flight checks on a script.

    Discovers includes, then runs: missing files, bracket matching,
    and undefined reference checks.

    Args:
        script_path: Path to the main .iqx script.
        include_search_dirs: Directories to search for included files.

    Returns:
        Dict with 'passed' (bool), 'issues' (list of issue dicts),
        and 'checks_run' (list of check names).
    """
    from .includes import discover_includes

    # discover_includes returns list[Path]
    include_paths = discover_includes(
        script_path, search_dirs=include_search_dirs or []
    )

    all_issues: list[dict] = []
    all_issues.extend(check_missing_files(script_path, include_paths))
    all_issues.extend(check_brackets(script_path, include_paths))
    all_issues.extend(check_undefined_references(script_path, include_paths))

    errors = [i for i in all_issues if i["severity"] == "error"]

    return {
        "passed": len(errors) == 0,
        "issues": all_issues,
        "error_count": len(errors),
        "warning_count": len(all_issues) - len(errors),
        "checks_run": ["missing_files", "bracket_matching", "undefined_references"],
    }
