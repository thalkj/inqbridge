"""Discover and resolve Inquisit <include> dependencies."""
import re
from pathlib import Path

# v6 inline: <include>"file.iqx"</include>
_INCLUDE_V6 = re.compile(
    r'<include>\s*"?([^"<>\r\n]+)"?\s*</include>', re.IGNORECASE
)

# v7 multiline: <include>\n/ file = "file.iqjs"\n</include>
_INCLUDE_V7 = re.compile(
    r'<include>\s*/\s*file\s*=\s*"([^"]+)"', re.IGNORECASE
)

# Legacy alias for external code that references INCLUDE_PATTERN
INCLUDE_PATTERN = _INCLUDE_V6


def _extract_include_refs(text: str) -> list[str]:
    """Extract all include file references from script text (v6 and v7 syntax)."""
    refs: list[str] = []
    for m in _INCLUDE_V6.finditer(text):
        refs.append(m.group(1).strip())
    for m in _INCLUDE_V7.finditer(text):
        ref = m.group(1).strip()
        if ref not in refs:
            refs.append(ref)
    return refs


def discover_includes(script_path: Path, search_dirs: list[Path] | None = None) -> list[Path]:
    """Recursively discover all files included via <include> from a script.

    Supports both Inquisit 6 inline syntax and Inquisit 7 multiline syntax:
        v6: <include>"file.iqx"</include>
        v7: <include>
            / file = "file.iqjs"
            </include>

    Args:
        script_path: Path to the main .iqx script.
        search_dirs: Additional directories to search for included files.

    Returns:
        List of resolved Path objects for all included files (deduplicated, in discovery order).
    """
    if search_dirs is None:
        search_dirs = []

    found: list[Path] = []
    seen: set[Path] = set()

    def _resolve(ref: str, relative_to: Path) -> Path | None:
        # Try relative to the referring script first
        candidate = relative_to.parent / ref
        if candidate.is_file():
            return candidate.resolve()
        # Try each search directory
        for d in search_dirs:
            candidate = d / ref
            if candidate.is_file():
                return candidate.resolve()
        return None

    def _scan(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        if not resolved.is_file():
            return
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        for ref in _extract_include_refs(text):
            included = _resolve(ref, resolved)
            if included and included not in seen:
                found.append(included)
                _scan(included)

    _scan(script_path)
    return found
