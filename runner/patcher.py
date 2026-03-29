"""Constrained layout patcher for Inquisit scripts.

Only edits allowed layout attributes:
- position, size, fontStyle
- canvasPosition, canvasSize, canvasAspectRatio
- <defaults> block attributes
"""
import re
from dataclasses import dataclass
from pathlib import Path

ALLOWED_ATTRIBUTES = frozenset({
    "position",
    "size",
    "fontstyle",
    "canvasposition",
    "canvassize",
    "canvasaspectratio",
    # Within <defaults> blocks, these are also allowed:
    "screencolor",
    "txcolor",
    "txbgcolor",
    "font",
    "fontsize",
})

# Attributes that are always forbidden to edit
FORBIDDEN_ATTRIBUTES = frozenset({
    "validresponse",
    "correctresponse",
    "response",
    "isCorrect",
    "branch",
    "skip",
    "timeout",
    "pretrialpause",
    "posttrialpause",
    "stimulusframes",
    "responseframes",
})


@dataclass
class Patch:
    file_path: str
    element_context: str  # e.g. "<text myText>" or "<defaults>"
    attribute: str
    old_value: str
    new_value: str
    line_number: int | None = None


def _is_attribute_allowed(attr: str, in_defaults: bool = False) -> bool:
    """Check if an attribute is in the allowed set."""
    attr_lower = attr.lower().strip()
    if attr_lower in {a.lower() for a in FORBIDDEN_ATTRIBUTES}:
        return False
    if in_defaults:
        return True  # Defaults can have broader layout attributes
    return attr_lower in ALLOWED_ATTRIBUTES


def _find_attribute_in_text(text: str, attr: str) -> list[tuple[int, str, str]]:
    """Find all occurrences of 'attr = value' in text.

    Returns list of (line_index, full_match, current_value).
    """
    # Match: / attr = value  or  /attr = "value"
    pattern = re.compile(
        rf'^\s*(/\s*{re.escape(attr)}\s*=\s*)(.+)$',
        re.IGNORECASE | re.MULTILINE,
    )
    results = []
    for match in pattern.finditer(text):
        line_start = text.count('\n', 0, match.start())
        prefix = match.group(1)
        value = match.group(2).strip()
        results.append((line_start, match.group(0), value))
    return results


def validate_patches(patches: list[Patch]) -> list[str]:
    """Validate that all patches only modify allowed attributes.

    Returns list of error messages (empty = all valid).
    """
    errors = []
    for p in patches:
        in_defaults = "<defaults>" in p.element_context.lower()
        if not _is_attribute_allowed(p.attribute, in_defaults):
            errors.append(
                f"Attribute '{p.attribute}' is not in the allowed set. "
                f"Context: {p.element_context} in {p.file_path}"
            )
    return errors


def apply_patches(patches: list[Patch], dry_run: bool = False) -> list[dict]:
    """Apply validated patches to source files.

    Args:
        patches: List of Patch objects to apply.
        dry_run: If True, report what would change without writing.

    Returns:
        List of dicts describing each applied change.
    """
    errors = validate_patches(patches)
    if errors:
        raise ValueError(f"Patch validation failed:\n" + "\n".join(errors))

    # Group patches by file
    by_file: dict[str, list[Patch]] = {}
    for p in patches:
        by_file.setdefault(p.file_path, []).append(p)

    results = []
    for file_path, file_patches in by_file.items():
        path = Path(file_path)
        if not path.is_file():
            results.append({"file": file_path, "status": "error", "message": "File not found"})
            continue

        text = path.read_text(encoding="utf-8")
        modified = text

        for patch in file_patches:
            # Build pattern to find the specific attribute assignment
            pattern = re.compile(
                rf'(/\s*{re.escape(patch.attribute)}\s*=\s*){re.escape(patch.old_value)}',
                re.IGNORECASE,
            )
            new_text = pattern.sub(rf'\g<1>{patch.new_value}', modified, count=1)

            if new_text == modified:
                results.append({
                    "file": file_path,
                    "attribute": patch.attribute,
                    "status": "not_found",
                    "message": f"Could not find '{patch.attribute} = {patch.old_value}' in {patch.element_context}",
                })
            else:
                modified = new_text
                results.append({
                    "file": file_path,
                    "attribute": patch.attribute,
                    "status": "applied" if not dry_run else "would_apply",
                    "old_value": patch.old_value,
                    "new_value": patch.new_value,
                    "context": patch.element_context,
                })

        if not dry_run and modified != text:
            path.write_text(modified, encoding="utf-8")

    return results


def generate_patches_from_issues(
    issues: list[dict],
    script_path: str,
) -> list[Patch]:
    """Generate suggested patches from layout scoring issues.

    This is a heuristic suggestion generator. Each patch should be reviewed.

    Args:
        issues: List of issue dicts from score_layout.
        script_path: Path to the script to patch.

    Returns:
        List of suggested Patch objects.
    """
    patches = []
    for issue in issues:
        issue_type = issue.get("issue_type", "")

        if issue_type == "font_too_small":
            patches.append(Patch(
                file_path=script_path,
                element_context="<defaults>",
                attribute="fontsize",
                old_value="",  # Will need to be filled by caller
                new_value="",
                line_number=None,
            ))

        if issue_type == "text_clipped":
            patches.append(Patch(
                file_path=script_path,
                element_context="<defaults>",
                attribute="canvassize",
                old_value="",
                new_value="",
                line_number=None,
            ))

    return patches
