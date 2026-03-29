# InquisitBridge - Claude Instructions

## First-Run Setup Check
On first interaction in this project, check whether the environment is ready:
1. **`local.json`** — Check if it exists. If not, tell the user to run `setup.bat` which handles everything below automatically.
2. **`.mcp.json`** — Check if it exists. If not, same: run `setup.bat`.
3. **`.venv/`** — Check if it exists with working deps. If not, same: run `setup.bat`.

`setup.bat` creates the venv, installs dependencies, discovers Inquisit installations (prompts if multiple found), and writes both `local.json` and `.mcp.json`.

## Working Preferences
1. **Plan before executing** - Make a thorough plan before starting any implementation.
2. **Ask upfront** - User cannot answer questions mid-task. Identify and ask all important questions before starting work.
3. **Don't touch computer settings** - Avoid modifying system/computer settings unless clearly safe. Document any changes made.
4. **Stay in scope** - Work only within the InquisitBridge folder and ClaudeAccess subfolders unless strictly necessary.
5. **Permission for critical changes** - If critical computer-level changes are needed, wait until the last moment and ask for explicit permission before proceeding.

## Project
- **Purpose:** Bridge program allowing LLMs to run Inquisit Scripts
- **Inquisit exe:** Auto-discovered from `local.json` (written by `setup.bat`), falls back to scanning `C:\Program Files\Millisecond Software\`
- **Git:** local only, no remote
- **Python:** 3.12 installed at `C:\Users\thalk\AppData\Local\Programs\Python\Python312`

## Architecture
- **Layer A (Runner):** Local audited runner - launches Inquisit, captures artifacts, decides pass/fail
- **Layer B (MCP):** Thin MCP wrapper - exposes the runner to Claude Code as tools

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
- **Always use percentage-based positioning** — never raw pixels. Use `/ hposition = 50%` and `/ vposition = 50%`, not pixel coordinates. If you need to compute a value from pixels, multiply by `1%` (e.g., `display.width * 0.25` expressed as `25%`). Percentages ensure scripts work on any resolution.

## Final Script Delivery Rules
- **Self-contained**: A finished script must be a folder containing the main .iqx and all include files, stimuli, and dependencies. No external references that the recipient won't have.
- **No screenCapture in final**: Remove `/ screenCapture = true` from all trials and blocks before delivering. screenCapture is a debug tool, not for participants.
- **Human verification required**: Every final script must pass a human-mode run before being considered ready. Monkey mode validates mechanics; only a human run validates the actual participant experience. If the user explicitly requests monkey-only delivery, that is acceptable but should be noted.

## Code Commenting Standards for .iqx Scripts
- **Top of script**: Comment explaining the experiment's purpose, flow, and expected participant experience. E.g., "This IAT measures implicit associations between flowers/insects and pleasant/unpleasant words across 7 blocks."
- **Element purpose**: Every non-trivial element (`<text>`, `<trial>`, `<block>`, `<list>`) should have a one-line comment explaining what it does. E.g., `// Fixation cross shown for 500ms before each target stimulus`.
- **Complex expressions/values**: If a `/ ontrialbegin` or `values.*` or `expressions.*` line involves a multi-step pipeline, add a comment explaining the logic. E.g., `// Compute running accuracy for the last 20 trials to decide whether to show feedback`.
- **Experiment flow**: Comment the block/expt structure to show the participant's journey. E.g., `// Block 1: Practice (10 trials) → Block 2: Test (40 trials) → Block 3: Debrief`.
- **Non-obvious Inquisit idioms**: When using uncommon patterns (e.g., `branch`, conditional `skip`, `list.nextvalue`), explain why.

## Screen Capture Strategy During Development
- **Enable screenCapture per trial** during development: Add `/ screenCapture = true` to trials you want to inspect visually. Remove before delivery.
- **Segment trials for visual checks**: When building a complex trial with multiple `stimulustimes` entries, first test the stimuli as separate short trials (each showing one stimulus combination) and capture those individually. This lets you see each visual layer before compositing them.
- **Use score_layout and score_layout_deep**: After a monkey run with captures, run both layout analysis tools. `score_layout` gives quick heuristics (clipping, contrast, crowding); `score_layout_deep` gives element inventories, overlap detection, font size analysis, and alignment checks.
- **Compare before/after**: Use `compare_runs` after any layout change to verify improvements and catch regressions.

## Debug Mode
When developing a script, maintain a parallel debug version with an overlay showing element characteristics:
- **Debug overlay approach**: Add a `<text debug_overlay>` element pinned to the bottom of the screen (e.g., `/ vposition = 95%`, `/ fontstyle = ("Consolas", 1.5%)`) that displays the current trial's key properties: element names visible, their hposition/vposition, stimulustimes, and size.
- **Maintained as a separate version**: Keep `script_debug.iqx` alongside the main `script.iqx`. The debug version includes extra trials or `ontrialbegin` logic that populates the overlay text. Never ship the debug version.
- **Toggle via values**: Use `values.debug_mode = 1` at the top so the overlay can be conditionally shown: `/ ontrialbegin = [if (values.debug_mode == 1) trial.current.insertstimulusframe(text.debug_overlay, 1)]` or similar.
- **What to display**: Element name, hposition, vposition, stimulustime onset, font size, and any dynamic values relevant to the trial.

## Edge Case Testing
Before finalizing any script, test these edge cases via targeted monkey runs:
- **Longest text**: Set the stimulus to the longest possible string the experiment might encounter. Check for text clipping, overflow, or overlap with other elements.
- **Unusual characters**: Test with Unicode edge cases (accented characters, CJK characters, RTL text) if the experiment may encounter them.
- **Screen resolution independence**: Since all positioning is percentage-based, verify captures look correct. The layout analysis tools detect clipping and overlap automatically.
- **Rapid responses**: Monkey mode naturally tests this — check that zero-latency or near-zero-latency responses don't break trial sequencing.
- **Missing stimuli**: If using list-based stimuli, verify behavior when the list is exhausted or when a stimulus file is missing.

## Human-Perspective Script Review
When working on any .iqx script, mentally walk through it as if you were the participant sitting in front of the screen:
- **Read the experiment flow**: Follow the `<expt>` → `<block>` → `<trial>` chain. For each trial, ask: What does the participant see? What are they supposed to do? Is it obvious what response is expected? Are instructions clear before they need to act?
- **Check trial logic**: Does the `stimulustimes` sequence make sense experientially? Is there enough time to read instructions before stimuli appear? Are response windows reasonable? Does feedback (if any) appear at the right moment?
- **Verify block progression**: Does the order of blocks make sense? Is there practice before test? Does difficulty escalate appropriately? Are breaks provided in long experiments?
- **Spot confusing elements**: Would a naive participant understand what to do without external explanation? Are response key mappings shown on screen? Are category labels visible during classification tasks?
- **This is integrated, not a separate step**: Do this mental walkthrough whenever you read or edit a script — it is part of how you work on scripts, not something triggered separately. Flag concerns inline as you work (e.g., "This trial shows the stimulus for only 50ms but the instruction text hasn't appeared yet — participants may miss it").

## Ctrl+Q (Abort) Handling
- **What happens**: Pressing Ctrl+Q during a run causes Inquisit to immediately end the script and save any data collected up to that point. The `script.completed` property returns 0 (vs 1 for normal completion).
- **Exit code**: Inquisit still returns exit code 1 (same as normal completion in Inquisit 6), so the runner cannot distinguish abort from completion by exit code alone.
- **Data implications**: Partial data files will exist. The `assess_data_quality` tool can detect unusually low trial counts per trialcode compared to expected block sizes.
- **Runner behavior**: The runner will report verdict `completed` if data files exist, even on abort. Check `script.completed` in summary data or compare expected vs actual trial counts to detect aborted runs.
- **During human testing**: Ctrl+Q is expected and normal — testers may need to abort. The data from partial runs is still useful for validating what displayed correctly up to that point.

## Lessons Learned (Hard Bugs)

### Inquisit compiles ALL elements at startup
Even if you only run one block, Inquisit compiles every `<picture>`, `<sound>`, `<text>`, `<trial>`, etc. in the entire script. A missing image file for a block you're not testing will still cause a fatal compile error. **If you remove pictures from the experiment, also remove/comment out the `<picture>` elements themselves.**

### Exit code 0 = failure, 1 = success (opposite of Unix)
Inquisit 6 returns exit code 0 when compilation fails — no data, no helpful error, just a "Network Error" in stderr. Exit code 1 means normal completion. The runner now handles this correctly with a `compile_error` verdict.

### Silent bracket bugs
An unclosed `[` in `/ontrialbegin = [` that spans multiple lines, followed by another `/ontrialbegin = [` before the first closes, causes silent compilation failure. This is nearly invisible in long scripts with mixed indentation. **Always run preflight checks before executing.**

### AI-generated scripts have phantom references
LLM-generated code often references elements that look correct but were never defined (e.g., `restaurantInstructions_smallreuse`, `Predtext2`). The structure looks complete — trials have proper logic, handlers, etc. — but the stimulus elements simply don't exist. **Always run the undefined-reference preflight check on AI-generated scripts.**

### Stale data from previous runs
Inquisit writes data to `data/` relative to the script. If you ran `hello_world.iqx` previously, those .iqdat files persist. Running a different script in the same folder may pick up old data files. The runner now filters collected data files by script name.

## Segmented Development Workflow
For complex experiments (500+ lines), build and test independent parts separately before combining:

### How to segment
1. **Identify independent parts**: demographics block, instruction screens, practice trials, test trials, debrief. Each becomes its own mini-script during development.
2. **Each segment is a standalone .iqx**: Include only the elements that segment needs — its own `<values>`, `<text>`, `<trial>`, `<block>`, and a minimal `<expt>`.
3. **Test each segment independently**: Monkey run + screen captures + layout analysis. Fix issues in isolation where the error surface is small.
4. **Combine using `<include>`**: The final script uses `<include>` to merge segment files. All elements share one namespace, so `<values>` defined in one include are visible to all others.

### Include mechanics
- `<include>` merges files at compile time — all elements share a single namespace.
- Values, trials, text elements defined in any include are accessible from any other include.
- **Name conflicts are fatal**: If two includes both define `<text instructions>`, compilation fails. Use prefixes (e.g., `demo_instructions`, `test_instructions`).

### What `<include>` CANNOT do
- No conditional includes (all includes are always compiled)
- No parameterized includes (no way to pass arguments)
- Included files cannot be tested standalone if they reference elements from other includes

### Batch (separate scripts, no shared state)
`<batch>` runs multiple .iqx files sequentially. Only `subjectid`, `groupid`, and `sessionid` are passed between scripts — no `<values>` sharing. Use batch for truly independent tasks (e.g., a battery of different tests), not for splitting one experiment.

### Recommended segment structure
```
experiment/
  main.iqx                    # <expt> + <include> directives only
  config_inc.iqx              # Shared <values>, <defaults>, <expressions>
  demographics_inc.iqx        # Demographics block + its trials/text
  instructions_inc.iqx        # All instruction screens
  practice_inc.iqx            # Practice block + trials
  test_inc.iqx                # Main test block + trials + lists
  debrief_inc.iqx             # Debrief block
  test_demographics.iqx       # Standalone test: imports config + demographics
  test_practice.iqx           # Standalone test: imports config + practice
```

## Tool-Use Policy
- **Run preflight checks before every Inquisit execution** — catches missing files, bracket bugs, and phantom references before Inquisit's unhelpful error messages.
- Use file inspection and editing tools first.
- Use the local Inquisit runner for all execution.
- Use Monkey mode before asking for a human run.
- Use score_layout only after screen captures exist.
- Use patch_layout only after score_layout returns a concrete issue list.
- After patch_layout, immediately rerun the same target and compare captures.

## Allowed Changes (First Version)
- Create/edit .iqx files
- Create/edit include fragments
- Create/edit runner code
- Create/edit MCP wrapper
- Add debug hooks
- Add screenCapture=true for targeted runs
- Patch layout attributes
- Add tests for the runner

## Not Allowed Automatically
- Broad semantic changes to task logic without explicit approval
- Deletion of data/artifact folders
- Silent renaming of elements across many files
- Changing scoring formulas unless explicitly requested
- Changing response logic for human-facing trials without a targeted test plan

## Inquisit 6 CLI Syntax
```
"C:\Program Files\Millisecond Software\Inquisit 6\Inquisit.exe" "scriptpath" -s <subjectid> -g <groupid> -m <monkey|human>
```
Exit codes (opposite of Unix): **1 = success** (normal completion or Ctrl+Q abort), **0 = failure** (compile error, missing files). Screen captures go to data/screencaptures/ as .png files.

## Inquisit Documentation
Reference docs are in `docs/`. Do NOT read these on startup — they are large. Instead, search them with Grep when you need Inquisit syntax help.
- `docs/inquisit_programmers_manual.txt` — Full programmer's manual (88 pages, covers all elements, attributes, expressions, functions)
- `docs/script_notes_examples.txt` — Real experiment script examples with values, expressions, trials, stimulustimes, etc.

### Quick Inquisit Tips
- Access item by index: `text.textname.1` (not `text.textname.item(1)`)
- Multiple ontrialbegin blocks are allowed on the same trial
- `values.*` for runtime variables, `expressions.*` for computed values
- `stimulustimes` controls when stimuli appear (in ms from trial start)
- `/ response = correct` with `/ correctresponse` for accuracy scoring

### Reference Library
- `scripts/library_v6/` — 202 plain-text .iqx files (directly greppable). **Use these when stuck** — grep for Inquisit elements, attributes, or patterns to see real implementations. E.g., `grep -r "stimulustimes" scripts/library_v6/` to see how timing is used across experiments.
- `scripts/library_v7/` — 385 unzipped Inquisit 7 script folders (may contain multiple files per task).
- `scripts/library_index.md` — Index with counts and grep usage examples.
- **When to use**: When you need to see how a specific Inquisit feature is used in practice, or when documentation is unclear. Grep the v6 library first (single files, easier to parse), then v7 if needed.
- **If libraries are empty**: Run `scripts/download_library_v6.py` and/or `scripts/download_library.py` to populate them from millisecond.com. These are large downloads (200+ files each) and are gitignored.

### Screen Capture Policy (capture_policy parameter)
The `run_script` tool accepts a `capture_policy` parameter but screen capture is actually controlled by `/ screenCapture = true` on individual trials in the .iqx script. The capture_policy parameter is reserved for future use. To get screen captures:
1. Add `/ screenCapture = true` to the trials you want to inspect
2. Run with `run_monkey` or `run_script`
3. Captures appear in the run's `screencaptures/` folder
4. Remove `/ screenCapture = true` before final delivery
