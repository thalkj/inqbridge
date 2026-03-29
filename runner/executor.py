"""Launch Inquisit and capture execution results."""
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import INQUISIT_EXE


@dataclass
class ExecutionResult:
    command: str
    return_code: int | None
    stdout_file: Path
    stderr_file: Path
    duration_seconds: float
    timed_out: bool = False


def launch_inquisit(
    script_path: Path,
    run_dir: Path,
    mode: str = "human",
    subject_id: str = "1",
    group_id: str = "1",
    timeout_seconds: int = 600,
    inquisit_exe: Path | None = None,
) -> ExecutionResult:
    """Launch Inquisit with the given script and CLI options.

    Args:
        script_path: Absolute path to the .iqx script to run.
        run_dir: Directory where stdout/stderr will be captured.
        mode: 'human' or 'monkey'.
        subject_id: Subject ID to pass via -s.
        group_id: Group ID to pass via -g.
        timeout_seconds: Max seconds to wait before killing the process.
        inquisit_exe: Override path to Inquisit.exe.

    Returns:
        ExecutionResult with captured output info.
    """
    exe = inquisit_exe or INQUISIT_EXE
    if not exe.is_file():
        raise FileNotFoundError(f"Inquisit executable not found: {exe}")

    script_abs = script_path.resolve()
    if not script_abs.is_file():
        raise FileNotFoundError(f"Script not found: {script_abs}")

    cmd = [
        str(exe),
        str(script_abs),
        "-s", str(subject_id),
        "-g", str(group_id),
        "-m", mode,
    ]

    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"

    command_str = " ".join(f'"{c}"' if " " in c else c for c in cmd)

    start = time.monotonic()
    timed_out = False
    return_code = None

    with open(stdout_path, "w", encoding="utf-8") as out_f, \
         open(stderr_path, "w", encoding="utf-8") as err_f:
        try:
            proc = subprocess.run(
                cmd,
                stdout=out_f,
                stderr=err_f,
                timeout=timeout_seconds,
                cwd=str(script_path.parent),
            )
            return_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True

    duration = time.monotonic() - start

    return ExecutionResult(
        command=command_str,
        return_code=return_code,
        stdout_file=stdout_path,
        stderr_file=stderr_path,
        duration_seconds=round(duration, 2),
        timed_out=timed_out,
    )
