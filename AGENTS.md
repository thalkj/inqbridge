# InqBridge - Codex Project Guide

Use the `inqbridge` skill for any Inquisit `.iqx`, experiment-folder, Monkey-mode, screenCapture, data-artifact, or InqBridge runner task.

If `LOCAL_WORKSPACE_STATE.md` exists, read it before making git or branch decisions. It is a local-only note for machine-specific state that should not be committed.

If the skill is not listed in the session, read `.claude/skills/inqbridge/SKILL.md` manually before changing experiment files. That file is the long-form workflow source inherited from the original Claude project.

Keep the workflow entrypoints aligned when editing instructions:
- `.claude/skills/inqbridge/SKILL.md` is the detailed reference.
- `AGENTS.md` is the repo-root quick guide Codex reads automatically.
- `%USERPROFILE%\.codex\skills\inqbridge\SKILL.md` is an optional user-profile Codex skill; update it too if present, but do not assume a fresh clone has it.

## Discovery

At the start of an InqBridge task, scan `experiments/` for folders with `EXPERIMENT.md` and read their `Status:` line. If modifying an existing experiment, read its full `EXPERIMENT.md` before editing. If starting a new one, create `experiments/<name>/EXPERIMENT.md` with a status and changelog.

## Fast Workflow

1. Preserve original `.iqx` files; copy into a new experiment folder before editing.
2. Keep experiment folders self-contained and add/update `EXPERIMENT.md`.
3. Run preflight before any Inquisit execution:
   `.venv\Scripts\python.exe -m runner.preflight experiments\name\main.iqx`
4. Use fast monkey runs for compile/data checks:
   `.venv\Scripts\python.exe -m runner.cli experiments\name\main.iqx -m monkey -g 1 -s 9001 --fast-mode`
5. Use fast captured runs for layout smoke checks:
   `.venv\Scripts\python.exe -m runner.cli experiments\name\main.iqx -m monkey -g 1 -s 9101 --fast-mode --auto-capture --timeout 300`

Avoid full-duration `--auto-capture` on a complete experiment unless the user explicitly asks or a small targeted tester is unavailable and the long runtime is acceptable.

For a normal build, follow the same phase order as the Claude skill: design/spec, build modules, preflight and fast Monkey data checks, fast captured layout checks, integration, delivery packaging. Use human mode only when the user explicitly asks.

## Validation Notes

- Inspect manifests and `.iqdat` data, not console output alone.
- If Monkey randomly declines consent and the data has only `consent_trial`, rerun with a fresh subject id.
- Inquisit 6 return code `1` is normal completion for this runner.
- Use `Path(...)` when calling runner Python APIs directly, for example `preflight_check(Path("..."))`.
- `run_monkey` defaults to `auto_capture=false`; enable capture only for layout QA, preferably with `--fast-mode`.
- `auto_capture` injects screenCapture into trial-like elements, including `trial`, `openended`, `likert`, and `slidertrial`.
- If a run times out, check for leftover `Inquisit` processes from that run and stop only those matching the run command line.
- `experiments/`, `artifacts/`, `.mcp.json`, and local settings are ignored intentionally.
