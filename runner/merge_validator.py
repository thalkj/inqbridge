"""Validate namespace compatibility before merging modules via <include>.

Checks for:
- Element name conflicts (same name defined in multiple files)
- Element type mismatches (same name, different element types)
- Remaining PLACEHOLDER values that need to be replaced
- Cross-file references (informational: element in file A references element in file B)
"""
from __future__ import annotations

import re
from pathlib import Path

from .preflight import _ELEMENT_DEF_PATTERN, _STIMULUSFRAMES_PATTERN, _STIMULUSTIMES_PATTERN
from .preflight import _BLOCK_TRIALS_PATTERN, _EXPT_BLOCKS_PATTERN, _BRACKET_REFS


# Pattern for PLACEHOLDER markers in values
_PLACEHOLDER_PATTERN = re.compile(
    r'(?://\s*PLACEHOLDER\b.*|"PLACEHOLDER")', re.IGNORECASE
)


def _extract_definitions(source: str) -> list[tuple[str, str]]:
    """Extract all (element_type, element_name) pairs from source text."""
    defs = []
    for m in _ELEMENT_DEF_PATTERN.finditer(source):
        elem_type = m.group(1).lower()
        elem_name = m.group(2).lower()
        defs.append((elem_type, elem_name))
    return defs


def _extract_references(source: str) -> set[str]:
    """Extract all element names referenced in stimulusframes, stimulustimes, trials, blocks."""
    refs: set[str] = set()
    for pattern in [_STIMULUSFRAMES_PATTERN, _STIMULUSTIMES_PATTERN,
                    _BLOCK_TRIALS_PATTERN, _EXPT_BLOCKS_PATTERN]:
        for m in pattern.finditer(source):
            bracket_content = m.group(1)
            for part in bracket_content.split(";"):
                for ref_match in _BRACKET_REFS.finditer(part):
                    name = ref_match.group(1).lower()
                    if not name.isdigit():
                        refs.add(name)
    return refs


def validate_merge(
    include_files: list[Path],
    main_file: Path | None = None,
) -> dict:
    """Validate namespace compatibility across files to be merged via <include>.

    Args:
        include_files: List of .iqx files that will be combined.
        main_file: Optional main .iqx that includes all others.

    Returns:
        Dict with 'passed' (bool), 'conflicts', 'type_mismatches',
        'placeholders', 'cross_references', and 'definitions_per_file'.
    """
    all_files = list(include_files)
    if main_file and main_file not in all_files:
        all_files.insert(0, main_file)

    # Per-file data
    file_defs: dict[str, list[tuple[str, str]]] = {}   # path -> [(type, name)]
    file_refs: dict[str, set[str]] = {}                  # path -> {name}
    file_sources: dict[str, str] = {}                    # path -> source text

    for f in all_files:
        if not f.is_file():
            continue
        try:
            source = f.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        key = str(f)
        file_sources[key] = source
        file_defs[key] = _extract_definitions(source)
        file_refs[key] = _extract_references(source)

    # Build global namespace: name -> [(type, file)]
    namespace: dict[str, list[tuple[str, str]]] = {}
    for fpath, defs in file_defs.items():
        for elem_type, elem_name in defs:
            namespace.setdefault(elem_name, []).append((elem_type, fpath))

    # Check conflicts: same name in multiple files
    conflicts = []
    for name, locations in namespace.items():
        files = list({loc[1] for loc in locations})
        if len(files) > 1:
            conflicts.append({
                "name": name,
                "defined_in": [Path(f).name for f in files],
                "message": f"'{name}' is defined in multiple files: {', '.join(Path(f).name for f in files)}",
            })

    # Check type mismatches: same name, different types
    type_mismatches = []
    for name, locations in namespace.items():
        types = list({loc[0] for loc in locations})
        if len(types) > 1:
            type_mismatches.append({
                "name": name,
                "types": types,
                "message": f"'{name}' is defined as different types: {', '.join(types)}",
            })

    # Check for PLACEHOLDER values
    placeholders = []
    for fpath, source in file_sources.items():
        for m in _PLACEHOLDER_PATTERN.finditer(source):
            line_num = source[:m.start()].count("\n") + 1
            placeholders.append({
                "file": Path(fpath).name,
                "line": line_num,
                "match": m.group(0).strip(),
                "message": f"Unresolved placeholder in {Path(fpath).name} line {line_num}: {m.group(0).strip()}",
            })

    # Check cross-references: references in file A to elements defined only in file B
    all_defined = {name for name in namespace}
    cross_refs = []
    for fpath, refs in file_refs.items():
        local_defs = {name for _, name in file_defs.get(fpath, [])}
        for ref_name in refs:
            if ref_name in all_defined and ref_name not in local_defs:
                # This reference is satisfied by another file
                defining_files = [Path(loc[1]).name for loc in namespace[ref_name]]
                cross_refs.append({
                    "from_file": Path(fpath).name,
                    "references": ref_name,
                    "defined_in": defining_files,
                })

    # Summary per file
    defs_per_file = {}
    for fpath, defs in file_defs.items():
        defs_per_file[Path(fpath).name] = [
            {"type": t, "name": n} for t, n in defs
        ]

    has_errors = len(conflicts) > 0 or len(type_mismatches) > 0
    has_placeholders = len(placeholders) > 0

    return {
        "passed": not has_errors and not has_placeholders,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "type_mismatch_count": len(type_mismatches),
        "type_mismatches": type_mismatches,
        "placeholder_count": len(placeholders),
        "placeholders": placeholders,
        "cross_reference_count": len(cross_refs),
        "cross_references": cross_refs,
        "definitions_per_file": defs_per_file,
    }
