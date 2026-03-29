# InquisitBridge - Codex Instructions

## First-Run Setup Check
On first interaction in this project, check whether the environment is ready. If any of the following are missing, ask the user if you should help set them up:
1. **Inquisit 6 or 7** — Check if `C:\Program Files\Millisecond Software\Inquisit 6\Inquisit.exe` exists (or ask user for their Inquisit path)
2. **Python 3.12+** — Check if `python --version` works
3. **Virtual environment** — Check if `.venv/` exists in this folder
4. **Dependencies** — Check if `.venv/Scripts/python.exe -c "import mcp; import PIL; import imagehash"` works
5. If anything is missing, offer to run the setup:
   ```
   python -m venv .venv
   .venv\Scripts\pip install Pillow imagehash mcp pytest
   ```

## Project
- **Purpose:** Bridge program allowing LLMs to run Inquisit Scripts
- **Architecture:** Layer A (runner/) is the authoritative local runner. Layer B (mcp_server/) is a thin MCP wrapper.
- **Git:** local only, no remote

## Required Workflow
- Never rely on console output alone.
- Always preserve an executed source snapshot in each run folder.
- Prefer editing saved .iqx files over ephemeral buffers.
- Prefer built-in Inquisit screenCapture over blind OS screenshots.
- Use Monkey runs for smoke tests, not as proof of participant usability.
- Do not change task logic unless explicitly requested.
- When patching layout, only edit position, size, fontStyle, canvasPosition, canvasSize, canvasAspectRatio, or defaults unless told otherwise.
- After changing layout, rerun the same target and compare artifacts.
- Every implementation task must include a validation path.

## Tool-Use Policy
- Use file inspection and editing tools first.
- Use the local Inquisit runner for all execution.
- Use Monkey mode before asking for a human run.
- Use score_layout only after screen captures exist.
- Use patch_layout only after score_layout returns a concrete issue list.
- After patch_layout, immediately rerun the same target and compare captures.

## Allowed Changes
- Create/edit .iqx files and include fragments
- Create/edit runner and MCP wrapper code
- Add debug hooks and screenCapture=true for targeted runs
- Patch layout attributes
- Add tests

## Not Allowed Automatically
- Broad semantic changes to task logic without explicit approval
- Deletion of data/artifact folders
- Silent renaming of elements across many files
- Changing scoring formulas unless explicitly requested
- Changing response logic for human-facing trials without a targeted test plan

## Inquisit CLI Syntax
```
"C:\Program Files\Millisecond Software\Inquisit 6\Inquisit.exe" "scriptpath" -s <subjectid> -g <groupid> -m <monkey|human>
```
Note: Inquisit 6 returns exit code 1 on normal completion. Screen captures go to data/screencaptures/ as .png files.

## Inquisit Documentation
Reference docs are in `docs/`. Do NOT read these on startup — they are large. Instead, search them when you need Inquisit syntax help.
- `docs/inquisit_programmers_manual.txt` — Full programmer's manual (88 pages)
- `docs/script_notes_examples.txt` — Real experiment script examples

### Quick Inquisit Tips
- Access item by index: `text.textname.1` (not `text.textname.item(1)`)
- Multiple ontrialbegin blocks are allowed on the same trial
- `values.*` for runtime variables, `expressions.*` for computed values
- `stimulustimes` controls when stimuli appear (in ms from trial start)
- `/ response = correct` with `/ correctresponse` for accuracy scoring
