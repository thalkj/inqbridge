"""Tests for runner.run orchestration."""
from runner.executor import ExecutionResult
from runner.run import run_script


def test_run_script_combines_fast_mode_and_auto_capture(tmp_path, monkeypatch):
    """fast_mode + auto_capture should execute a fast captured temp copy."""
    script = tmp_path / "main.iqx"
    script.write_text(
        """<trial show>
/ stimulustimes = [0=fix; 500=stim]
</trial>
<openended recall>
/ stimulusframes = [1=prompt]
</openended>
""",
        encoding="utf-8",
    )

    observed = {}

    def fake_launch_inquisit(
        script_path,
        run_dir,
        mode,
        subject_id,
        group_id,
        timeout_seconds,
        inquisit_exe,
    ):
        observed["script_name"] = script_path.name
        observed["source"] = script_path.read_text(encoding="utf-8")
        stdout = run_dir / "stdout.txt"
        stderr = run_dir / "stderr.txt"
        stdout.write_text("fake")
        stderr.write_text("")
        return ExecutionResult(
            command="fake",
            return_code=1,
            stdout_file=stdout,
            stderr_file=stderr,
            duration_seconds=0.01,
        )

    monkeypatch.setattr("runner.run.launch_inquisit", fake_launch_inquisit)

    run_script(
        script,
        mode="monkey",
        fast_mode=True,
        auto_capture=True,
        artifacts_dir=tmp_path / "artifacts",
        inquisit_exe=tmp_path / "fake-inquisit.exe",
    )

    assert observed["script_name"] == "main_fast_tmp_cap_tmp.iqx"
    assert "/ screenCapture = true" in observed["source"]
    assert "0=fix, stim" in observed["source"]
    assert "<openended recall>" in observed["source"]
