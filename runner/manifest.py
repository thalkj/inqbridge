"""Write and read run manifest files."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import INQUISIT_EXE


def write_manifest(
    run_dir: Path,
    run_id: str,
    script_entry: str,
    source_snapshot: list[dict],
    mode: str,
    subject_id: str,
    group_id: str,
    command: str,
    return_code: int | None,
    raw_data_files: list[str],
    summary_data_files: list[str],
    screen_captures: list[str],
    verdict: str,
    duration_seconds: float = 0.0,
    notes: list[str] | None = None,
    inquisit_exe: Path | None = None,
) -> Path:
    """Write manifest.json to the run directory.

    Returns:
        Path to the written manifest file.
    """
    exe = inquisit_exe or INQUISIT_EXE
    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inquisit_path": str(exe),
        "script_entry": script_entry,
        "executed_snapshot": {"files": source_snapshot},
        "mode": mode,
        "subject_id": subject_id,
        "group_id": group_id,
        "command": command,
        "return_code": return_code,
        "duration_seconds": duration_seconds,
        "stdout_file": "stdout.txt",
        "stderr_file": "stderr.txt",
        "raw_data_files": raw_data_files,
        "summary_data_files": summary_data_files,
        "screen_captures": screen_captures,
        "verdict": verdict,
        "notes": notes or [],
    }

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def read_manifest(manifest_path: Path) -> dict:
    """Load a manifest.json file."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def determine_verdict(
    return_code: int | None,
    timed_out: bool,
    raw_data_files: list[str],
) -> tuple[str, list[str]]:
    """Determine run verdict and notes based on execution results.

    Inquisit 6 exit codes (opposite of Unix convention):
        - Exit code 1 = normal completion (script ran to end or Ctrl+Q abort)
        - Exit code 0 = compilation/startup failure (script never ran)

    Returns:
        (verdict, notes) tuple.
    """
    notes = []

    if timed_out:
        return "timeout", ["Inquisit process exceeded timeout limit."]

    if return_code is None:
        return "error", ["No return code captured."]

    # Inquisit 6: exit code 0 = FAILURE (compilation error, missing files, etc.)
    if return_code == 0:
        notes.append(
            "Inquisit returned code 0 — script failed to compile or run. "
            "Common causes: missing <picture>/<sound> files, syntax errors, "
            "or unclosed brackets. Check stderr for 'Network Error' or other hints."
        )
        return "compile_error", notes

    # Inquisit 6: exit code 1 = normal completion (or Ctrl+Q abort)
    if return_code == 1:
        notes.append("Inquisit returned code 1 (normal for Inquisit 6).")
    elif return_code not in (0, 1):
        notes.append(f"Unexpected return code: {return_code}")
        return "error", notes

    if not raw_data_files:
        notes.append("No raw data files collected.")
        return "completed_no_data", notes

    return "completed", notes
