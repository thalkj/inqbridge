"""Main runner: orchestrates a full Inquisit run with traceability."""
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import collect_data_files, collect_screen_captures
from .config import ARTIFACTS_DIR, INCLUDES_DIR, INQUISIT_EXE
from .executor import launch_inquisit
from .includes import discover_includes
from .manifest import determine_verdict, write_manifest
from .snapshot import snapshot_sources


def generate_run_id(script_path: Path, mode: str, subject_id: str, group_id: str) -> str:
    """Generate a timestamped run ID."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    stem = script_path.stem.replace(" ", "-")
    return f"{ts}_{stem}_{mode}_s{subject_id}_g{group_id}"


def run_script(
    script_path: str | Path,
    mode: str = "human",
    subject_id: str = "1",
    group_id: str = "1",
    run_id: str | None = None,
    timeout_seconds: int = 600,
    artifacts_dir: str | Path | None = None,
    inquisit_exe: str | Path | None = None,
) -> dict:
    """Execute a full audited Inquisit run.

    This is the primary entry point for the runner. It:
    1. Discovers include dependencies
    2. Creates a timestamped run directory
    3. Snapshots all source files with hashes
    4. Launches Inquisit with CLI flags
    5. Collects data files and screen captures
    6. Writes a manifest.json

    Args:
        script_path: Path to the .iqx script.
        mode: 'human' or 'monkey'.
        subject_id: Subject identifier.
        group_id: Group identifier.
        run_id: Optional override for the run ID.
        timeout_seconds: Max time before killing Inquisit.
        artifacts_dir: Override for artifacts output directory.
        inquisit_exe: Override for Inquisit executable path.

    Returns:
        Dict with run_id, manifest_path, verdict, and artifact counts.
    """
    script_path = Path(script_path).resolve()
    art_dir = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
    exe = Path(inquisit_exe) if inquisit_exe else INQUISIT_EXE

    if mode not in ("human", "monkey"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'human' or 'monkey'.")

    # Step 1: Discover includes
    includes = discover_includes(script_path, search_dirs=[INCLUDES_DIR])

    # Step 2: Create run directory
    if not run_id:
        run_id = generate_run_id(script_path, mode, subject_id, group_id)
    run_dir = art_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Snapshot sources
    source_snapshot = snapshot_sources(script_path, includes, run_dir)

    # Step 4: Launch Inquisit
    result = launch_inquisit(
        script_path=script_path,
        run_dir=run_dir,
        mode=mode,
        subject_id=subject_id,
        group_id=group_id,
        timeout_seconds=timeout_seconds,
        inquisit_exe=exe,
    )

    # Step 5: Collect artifacts (filter by script name to avoid stale data)
    script_dir = script_path.parent
    all_data = collect_data_files(script_dir, run_dir, script_name=script_path.stem)
    raw_data = [f for f in all_data if "raw" in f.lower()]
    summary_data = [f for f in all_data if "summary" in f.lower()]
    if not raw_data and not summary_data:
        raw_data = all_data
    screen_caps = collect_screen_captures(script_dir, run_dir)

    # Step 6: Determine verdict
    verdict, notes = determine_verdict(result.return_code, result.timed_out, raw_data)

    # Step 7: Write manifest
    script_entry = str(script_path.relative_to(script_path.parent.parent)) if script_path.parent.parent.exists() else script_path.name
    manifest_path = write_manifest(
        run_dir=run_dir,
        run_id=run_id,
        script_entry=script_entry,
        source_snapshot=source_snapshot,
        mode=mode,
        subject_id=subject_id,
        group_id=group_id,
        command=result.command,
        return_code=result.return_code,
        raw_data_files=raw_data,
        summary_data_files=summary_data,
        screen_captures=screen_caps,
        verdict=verdict,
        duration_seconds=result.duration_seconds,
        notes=notes,
        inquisit_exe=exe,
    )

    return {
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "verdict": verdict,
        "notes": notes,
        "artifact_counts": {
            "source_files": len(source_snapshot),
            "raw_data_files": len(raw_data),
            "summary_data_files": len(summary_data),
            "screen_captures": len(screen_caps),
        },
    }
