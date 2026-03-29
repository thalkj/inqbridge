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
    fast_mode: bool = False,
    auto_capture: bool = False,
    auto_fix: bool = False,
) -> dict:
    """Execute a full audited Inquisit run.

    This is the primary entry point for the runner. It:
    1. Discovers include dependencies
    2. Creates a timestamped run directory
    3. Snapshots all source files with hashes
    4. Optionally creates fast-mode or auto-capture temp copies
    5. Launches Inquisit with CLI flags
    6. On compile error with auto_fix, attempts fixes and retries once
    7. Collects data files and screen captures
    8. Writes a manifest.json

    Args:
        script_path: Path to the .iqx script.
        mode: 'human' or 'monkey'.
        subject_id: Subject identifier.
        group_id: Group identifier.
        run_id: Optional override for the run ID.
        timeout_seconds: Max time before killing Inquisit.
        artifacts_dir: Override for artifacts output directory.
        inquisit_exe: Override for Inquisit executable path.
        fast_mode: If True, override timings to near-zero for quick checks.
        auto_capture: If True, inject screenCapture=true into all trials.
        auto_fix: If True, attempt to auto-fix compile errors and retry.

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

    # Step 3: Snapshot ORIGINAL sources (for traceability)
    source_snapshot = snapshot_sources(script_path, includes, run_dir)

    # Step 4: Create temp copies if needed
    temp_paths_to_clean: list[Path] = []
    exec_script = script_path

    if fast_mode:
        from .fast_mode import create_fast_copies, cleanup_fast_copies
        exec_script, _fast_incs, fast_temps = create_fast_copies(script_path, includes)
        temp_paths_to_clean.extend(fast_temps)
    elif auto_capture:
        from .capture_manager import create_captured_copies, cleanup_temp_copies
        exec_script, _cap_incs, cap_temps = create_captured_copies(script_path, includes)
        temp_paths_to_clean.extend(cap_temps)

    try:
        # Step 5: Launch Inquisit
        result = launch_inquisit(
            script_path=exec_script,
            run_dir=run_dir,
            mode=mode,
            subject_id=subject_id,
            group_id=group_id,
            timeout_seconds=timeout_seconds,
            inquisit_exe=exe,
        )

        # Step 5b: Collect artifacts from ORIGINAL script directory
        script_dir = script_path.parent
        all_data = collect_data_files(script_dir, run_dir, script_name=script_path.stem)
        raw_data = [f for f in all_data if "raw" in f.lower()]
        summary_data = [f for f in all_data if "summary" in f.lower()]
        if not raw_data and not summary_data:
            raw_data = all_data
        screen_caps = collect_screen_captures(script_dir, run_dir)

        # Step 6: Determine verdict
        verdict, notes = determine_verdict(result.return_code, result.timed_out, raw_data)

        # Step 6b: Auto-fix on compile error
        auto_fix_report = None
        if auto_fix and verdict == "compile_error":
            auto_fix_report = _attempt_auto_fix_and_retry(
                script_path=script_path,
                includes=includes,
                run_dir=run_dir,
                mode=mode,
                subject_id=subject_id,
                group_id=group_id,
                timeout_seconds=timeout_seconds,
                exe=exe,
            )
            if auto_fix_report and auto_fix_report.get("retry_verdict"):
                verdict = auto_fix_report["retry_verdict"]
                notes.append(f"Auto-fix applied: {auto_fix_report['fixed_count']} fixes")
                if auto_fix_report.get("retry_data"):
                    raw_data = auto_fix_report["retry_data"]["raw"]
                    summary_data = auto_fix_report["retry_data"]["summary"]
                    screen_caps = auto_fix_report["retry_data"]["captures"]

        if fast_mode:
            notes.append("Fast-mode: timings overridden to near-zero")
        if auto_capture:
            notes.append("Auto-capture: screenCapture=true injected into all trials")

    finally:
        # Cleanup temp copies
        for p in temp_paths_to_clean:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

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

    response = {
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

    if auto_fix_report:
        response["auto_fix"] = auto_fix_report

    return response


def _attempt_auto_fix_and_retry(
    script_path: Path,
    includes: list[Path],
    run_dir: Path,
    mode: str,
    subject_id: str,
    group_id: str,
    timeout_seconds: int,
    exe: Path,
) -> dict | None:
    """Run preflight, auto-fix issues, and retry once."""
    from .preflight import preflight_check
    from .auto_fix import attempt_auto_fix

    # Run preflight to identify issues
    preflight_result = preflight_check(script_path, include_search_dirs=[INCLUDES_DIR])
    if preflight_result["passed"]:
        return {"fixed_count": 0, "message": "Preflight passed but script still failed — issue is beyond static analysis"}

    # Attempt fixes
    fix_report = attempt_auto_fix(script_path, includes, preflight_result["issues"])

    if fix_report["fixed_count"] == 0:
        return {
            "fixed_count": 0,
            "unfixable": fix_report["unfixable"],
            "message": "No auto-fixable issues found",
        }

    # Retry
    retry_result = launch_inquisit(
        script_path=script_path,
        run_dir=run_dir,
        mode=mode,
        subject_id=subject_id,
        group_id=group_id,
        timeout_seconds=timeout_seconds,
        inquisit_exe=exe,
    )

    script_dir = script_path.parent
    retry_data_all = collect_data_files(script_dir, run_dir, script_name=script_path.stem)
    retry_raw = [f for f in retry_data_all if "raw" in f.lower()]
    retry_summary = [f for f in retry_data_all if "summary" in f.lower()]
    if not retry_raw and not retry_summary:
        retry_raw = retry_data_all
    retry_caps = collect_screen_captures(script_dir, run_dir)

    retry_verdict, retry_notes = determine_verdict(
        retry_result.return_code, retry_result.timed_out, retry_raw
    )

    return {
        "fixed_count": fix_report["fixed_count"],
        "fixed": fix_report["fixed"],
        "unfixable": fix_report["unfixable"],
        "files_modified": fix_report["files_modified"],
        "retry_verdict": retry_verdict,
        "retry_notes": retry_notes,
        "retry_data": {
            "raw": retry_raw,
            "summary": retry_summary,
            "captures": retry_caps,
        },
    }
