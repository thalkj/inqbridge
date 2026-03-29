# InqBridge - Inquisit Experiment Building Guide

## Setup
If `local.json` or `.mcp.json` are missing, run `setup.bat`. See README.md for details.

## Experiment Quality Rules
- Never rely on console output alone.
- Always preserve an executed source snapshot in each run folder.
- Prefer editing saved .iqx files over ephemeral buffers.
- Prefer built-in Inquisit screenCapture over blind OS screenshots.
- Use Monkey runs for smoke tests, not as proof of participant usability.
- Do not change task logic unless explicitly requested.
- When patching layout, only edit position, size, fontStyle, canvasPosition, canvasSize, canvasAspectRatio, or defaults unless told otherwise.
- After changing layout, rerun the same target and compare artifacts.
- Every implementation task must include a validation path.
- **Always use percentage-based positioning** — never raw pixels. Use `/ hposition = 50%` and `/ vposition = 50%`, not pixel coordinates. Percentages ensure scripts work on any resolution.

## Final Script Delivery Rules
- **Self-contained**: A finished script must be a folder containing the main .iqx and all include files, stimuli, and dependencies. No external references that the recipient won't have.
- **No screenCapture in final**: Remove `/ screenCapture = true` from all trials and blocks before delivering. screenCapture is a debug tool, not for participants.
- **Human verification required**: Every final script must pass a human-mode run before being considered ready. Monkey mode validates mechanics; only a human run validates the actual participant experience. If the user explicitly requests monkey-only delivery, that is acceptable but should be noted.

## Code Commenting Standards for .iqx Scripts
- **Top of script**: Comment explaining the experiment's purpose, flow, and expected participant experience.
- **Element purpose**: Every non-trivial element (`<text>`, `<trial>`, `<block>`, `<list>`) should have a one-line comment explaining what it does.
- **Complex expressions/values**: If a `/ ontrialbegin` or `values.*` or `expressions.*` line involves a multi-step pipeline, add a comment explaining the logic.
- **Experiment flow**: Comment the block/expt structure to show the participant's journey. E.g., `// Block 1: Practice (10 trials) → Block 2: Test (40 trials) → Block 3: Debrief`.
- **Non-obvious Inquisit idioms**: When using uncommon patterns (e.g., `branch`, conditional `skip`, `list.nextvalue`), explain why.

## Screen Capture Strategy During Development
- **Enable screenCapture per trial** during development: Add `/ screenCapture = true` to trials you want to inspect visually. Remove before delivery.
- **Segment trials for visual checks**: When building a complex trial with multiple `stimulustimes` entries, first test the stimuli as separate short trials and capture those individually.
- **Use score_layout and score_layout_deep**: After a monkey run with captures, run both layout analysis tools. `score_layout` gives quick heuristics; `score_layout_deep` gives element inventories, overlap detection, font size analysis, and alignment checks.
- **Compare before/after**: Use `compare_runs` after any layout change to verify improvements and catch regressions.

## Debug Mode
When developing a script, maintain a parallel debug version with an overlay showing element characteristics:
- **Debug overlay approach**: Add a `<text debug_overlay>` element pinned to the bottom of the screen (e.g., `/ vposition = 95%`, `/ fontstyle = ("Consolas", 1.5%)`) that displays the current trial's key properties.
- **Maintained as a separate version**: Keep `script_debug.iqx` alongside the main `script.iqx`. Never ship the debug version.
- **Toggle via values**: Use `values.debug_mode = 1` at the top so the overlay can be conditionally shown.

## Edge Case Testing
Before finalizing any script, test these edge cases via targeted monkey runs:
- **Longest text**: Set the stimulus to the longest possible string. Check for clipping, overflow, or overlap.
- **Unusual characters**: Test with Unicode edge cases (accented characters, CJK, RTL text) if applicable.
- **Screen resolution independence**: Percentage-based positioning ensures this. Layout tools detect clipping automatically.
- **Rapid responses**: Monkey mode tests this — check that zero-latency responses don't break trial sequencing.
- **Missing stimuli**: If using list-based stimuli, verify behavior when the list is exhausted.

## Human-Perspective Script Review
When working on any .iqx script, mentally walk through it as if you were the participant:
- **Read the experiment flow**: Follow `<expt>` → `<block>` → `<trial>`. What does the participant see? Is it obvious what response is expected?
- **Check trial logic**: Does `stimulustimes` sequencing make sense? Enough time to read instructions? Response windows reasonable?
- **Verify block progression**: Practice before test? Difficulty escalation? Breaks in long experiments?
- **Spot confusing elements**: Response key mappings shown? Category labels visible during classification?
- **Integrated, not separate**: Do this walkthrough whenever you read or edit a script. Flag concerns inline.

## Ctrl+Q (Abort) Handling
- Pressing Ctrl+Q causes Inquisit to end immediately and save partial data. Exit code remains 1 (same as completion).
- The runner reports `completed` if data files exist. Check `script.completed` or trial counts to detect aborts.
- Ctrl+Q is expected during human testing — partial run data is still useful.

## Lessons Learned (Hard Bugs)

### Inquisit compiles ALL elements at startup
Even if you only run one block, Inquisit compiles every element in the script. A missing image file for a block you're not testing causes a fatal compile error. **If you remove pictures, also remove the `<picture>` elements.**

### Exit code 0 = failure, 1 = success (opposite of Unix)
Inquisit 6 returns exit code 0 on compilation failure — no data, no helpful error. Exit code 1 means normal completion.

### Silent bracket bugs
An unclosed `[` in `/ontrialbegin = [` causes silent compilation failure. **Always run preflight checks before executing.**

### AI-generated scripts have phantom references
LLM-generated code often references elements that were never defined. The structure looks complete but the stimulus elements don't exist. **Always run the undefined-reference preflight check.**

### Stale data from previous runs
Inquisit writes data to `data/` relative to the script. Old `.iqdat` files persist between runs. The runner filters by script name, but be aware of this.

## Modular Development
For complex experiments (500+ lines), build and test independent modules before combining. See the SKILL.md workflow for the full pipeline. Use `scaffold_experiment` to generate starter templates and `validate_merge` to check namespace conflicts before combining.

### Library Fragments
Pre-built include fragments in `includes/library/`: demographics, consent, debrief, completion code, attention checks. All use namespace prefixes to avoid conflicts. Include them with `<include>` like any other module.

### Include mechanics
- `<include>` merges files at compile time — all elements share a single namespace.
- **Name conflicts are fatal**: Use prefixes (e.g., `demo_instructions`, `test_instructions`).
- No conditional includes, no parameterized includes.
- Included files cannot be tested standalone if they reference elements from other includes — use standalone tester scripts.

### Batch (separate scripts, no shared state)
`<batch>` runs multiple .iqx files sequentially. Only `subjectid`, `groupid`, and `sessionid` are passed. Use batch for truly independent tasks, not for splitting one experiment.

## Tool-Use Policy
- **Run preflight checks before every Inquisit execution.**
- Use Monkey mode before asking for a human run.
- Use `fast_mode=True` on `run_monkey` for quick compile/data checks — it collapses all stimulustimes to t=0 and zeros pauses.
- `auto_capture` is on by default for `run_monkey` — it injects `/ screenCapture = true` into temp copies without modifying the real script.
- `auto_fix` is on by default — on compile error, it runs preflight, auto-fixes missing files and phantom references, and retries once.
- Use score_layout only after screen captures exist.
- Use patch_layout only after score_layout returns concrete issues.
- After patch_layout, immediately rerun and compare captures.
- Use `validate_merge` before combining modules.
- Use `list_runs` to find previous run IDs.
- Use `generate_spec` to understand any script's structure before modifying it.
- Use `decompose_script` to split a large monolithic script into testable modules.
- Use `prepare_delivery` for final packaging — it strips screenCapture, removes debug elements, validates, and packages.

## Safety Guardrails
- Do not change task logic, scoring formulas, or response logic without explicit approval.
- Do not delete data/artifact folders.
- Do not silently rename elements across files.

## Inquisit CLI Syntax
```
Inquisit.exe "scriptpath" -s <subjectid> -g <groupid> -m <monkey|human>
```
The Inquisit path is auto-discovered from `local.json`. Exit codes: **1 = success**, **0 = failure**. Screen captures go to `data/screencaptures/` as .png files.

## Inquisit Documentation
Reference docs are in `docs/`. Do NOT read these on startup — they are large. Search them with Grep when you need syntax help.
- `docs/inquisit_programmers_manual.txt` — Full programmer's manual (88 pages)
- `docs/script_notes_examples.txt` — Real experiment script examples

### Quick Inquisit Tips
- Access item by index: `text.textname.1` (not `text.textname.item(1)`)
- Multiple ontrialbegin blocks are allowed on the same trial
- `values.*` for runtime variables, `expressions.*` for computed values
- `stimulustimes` controls when stimuli appear (in ms from trial start)
- `/ response = correct` with `/ correctresponse` for accuracy scoring

### Reference Library
- `scripts/library_v6/` — 202 plain-text .iqx files (directly greppable). **Use these when stuck.** Grep the v6 library first (single files, easier to parse), then v7 if needed.
- `scripts/library_v7/` — 385 unzipped Inquisit 7 script folders.
- `scripts/library_index.md` — Index with counts and grep usage examples.
- **If libraries are empty**: Run `scripts/download_library_v6.py` and/or `scripts/download_library.py`.

### Screen Capture Policy
Screen capture is controlled by `/ screenCapture = true` on individual trials in the .iqx script. To get captures:
1. Add `/ screenCapture = true` to trials you want to inspect
2. Run with `run_monkey` or `run_script`
3. Captures appear in the run's `screencaptures/` folder
4. Remove `/ screenCapture = true` before final delivery
