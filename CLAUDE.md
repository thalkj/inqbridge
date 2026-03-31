# InqBridge - Inquisit Experiment Building Guide

## Setup (MUST CHECK FIRST)

**Before doing any experiment work**, verify the environment is ready. Check these in order and handle each step yourself via Bash — never tell the user to "run setup.bat" or go to a terminal.

1. **Virtual environment**: Check whether `.venv/Scripts/python.exe` exists in the project root.
   - If missing, tell the user: "I need to create a Python virtual environment and install dependencies (~1 minute). OK to proceed?"
   - On approval, run via Bash: `python -m venv .venv && .venv/Scripts/pip install -q -e ".[dev]"`
   - After creating the venv, the MCP server will load on the next Claude Code restart. In the current session, invoke runner modules directly via Bash (e.g., `.venv/Scripts/python -m runner.preflight ...`).

2. **MCP config**: Check whether `.mcp.json` exists in the project root.
   - If missing, create it via Write tool with this content (use the actual absolute project root path):
     ```json
     {
       "mcpServers": {
         "inq-bridge": {
           "command": "<PROJECT_ROOT>\\.venv\\Scripts\\python.exe",
           "args": ["-m", "mcp_server.main"],
           "cwd": "<PROJECT_ROOT>"
         }
       }
     }
     ```
   - Also ensure `.claude/settings.local.json` exists with `"enableAllProjectMcpServers": true` and `"enabledMcpjsonServers": ["inq-bridge"]`.

3. **Inquisit discovery** (`local.json`): This file is **optional** if only one Inquisit version is installed. `runner/config.py` auto-discovers Inquisit from `C:\Program Files\Millisecond Software`. However, if multiple versions are installed, **ask the user which version they are licensed for** — a newer version on disk does not mean the user has a license. Create `local.json` with their chosen path.

4. **MCP server not responding**: If MCP tool calls fail with connection errors after setup, tell the user to restart Claude Code so the MCP server process loads. This is the one step that cannot be automated. In the meantime, use Bash to invoke runner modules directly.

## Permission Warming (do after setup)

Many users run Claude Code without blanket "dangerous access" permissions — each new tool category requires an explicit Accept click. To avoid interrupting the experiment workflow later, run a **warming sequence** right after setup that exercises each tool type once. This gets the user's accepts upfront so the rest of the session flows smoothly.

**Warming sequence** (run these in order, explain to the user what you're doing):
1. **Bash**: `echo "InqBridge permission check"` — warms Bash access
2. **Write**: Create a temp file `experiments/_warmup_test.iqx` with a minimal hello-world script
3. **MCP preflight_check**: Run on the warmup script — warms MCP tool access
4. **MCP run_monkey**: Run the warmup script with `fast_mode=True` — warms Inquisit execution
5. **Read**: Read back the data file from the warmup run — warms file read access
6. **Cleanup**: Delete the warmup script and artifacts

Tell the user upfront: *"I'll run a quick warmup sequence that touches each tool type once — you'll see a few Accept prompts. After that the session will flow without interruptions."*

If the user has already granted broad permissions, skip this step.

## Experiment Quality Rules
- **Do not set `/ required = true` on survey questions** unless the user explicitly asks or the response value is needed downstream (piping, branching, group allocation). Default to `/ required = false`.
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
- **`/ screenCapture` only works on `<trial>` elements** in Inquisit 6. It does NOT work on `<openended>`, `<likert>`, `<slidertrial>`, or `<surveypage>`. For experiments that primarily use these elements (surveys, text-entry tasks), layout must be verified via a human run instead.
- **Do NOT capture during iterative debugging**: When fixing compile errors or data issues, use `fast_mode=True` without `auto_capture`. Captures are useless if the script doesn't compile, and layout doesn't change between data-logic fixes.
- **Capture once before human run**: When the script compiles cleanly, data looks correct, and you're ready to suggest a human run — do one final `run_monkey` with `auto_capture=True`. Then run `score_layout` + `score_layout_deep` and **read the captures yourself** to visually inspect for overlapping text, clipping, elements too close together, or anything visually awkward.
- **Segment trials for visual checks**: When building a complex trial with multiple `stimulustimes` entries, first test the stimuli as separate short trials and capture those individually.
- **Compare before/after**: Use `compare_runs` after any layout change to verify improvements and catch regressions.
- **Deduplication is automatic**: `score_layout` and `score_layout_deep` call `deduplicate_captures()` internally (SHA-256 + perceptual hash). Identical/near-identical frames are marked, not scored twice.

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

### `/ iti` is not a valid trial attribute
Use `/ posttrialpause` instead of `/ iti`. There is no `/ iti` attribute in Inquisit 6. This causes a silent compile error (`Expression contains an unknown element or property name`).

### `/ size` is not a valid block attribute
Blocks do not have a `/ size` attribute. Instead, use explicit position indices in `/ trials` to control how many trials run. Example for 5 repetitions of a 3-trial cycle: `/ trials = [1,4,7,10,13 = trialA; 2,5,8,11,14 = trialB; 3,6,9,12,15 = trialC]`.

### `/ validresponse = (noresponse)` requires a timeout or trialduration
A trial with `noresponse` must also have `/ trialduration` or `/ timeout` set, otherwise Inquisit rejects it. For auto-advancing trials, just set `/ trialduration` and omit `/ validresponse` entirely.

### `<instruct>` vs `<page>` for block/expt instructions
Blocks and experiments reference `<page>` elements in `/ preinstructions` and `/ postinstructions`, NOT `<instruct>` elements. Using `<instruct>` wrappers with `/ lines` causes "defined more than once" errors. Just define `<page>` elements and reference them directly: `/ preinstructions = (my_page)`.

### `list.X.nextvalue` returns one value per evaluation cycle
Calling `list.X.nextvalue` multiple times in a single `ontrialbegin = [...]` block returns the **same** value each time. To draw N independent random values, use N separate `<list>` elements (e.g., `letters1`, `letters2`, `letters3`, `letters4`).

### `<data>` element needed to export custom values
Custom `values.*` fields do not appear in the .iqdat file by default. Add a `<data>` element with `/ columns = [...]` listing the standard columns plus any `values.*` you need. Without this, only built-in columns (latency, response, etc.) are recorded.

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

## Experiment Folder Convention

Each experiment lives in its own folder under `experiments/`. This keeps experiment work separate from platform code without requiring git knowledge.

### Folder structure
```
experiments/
  flower_prediction/
    EXPERIMENT.md        ← Required: status, plan, changelog, known issues
    main.iqx             ← Entry point
    config_inc.iqx       ← Shared config
    *_inc.iqx            ← Module includes
    stimuli/             ← Images, sounds, etc.
    data/                ← Inquisit output (auto-created)
```

### EXPERIMENT.md (required per experiment)
Every experiment folder must have an `EXPERIMENT.md` with:
- **Status**: `planning` | `building` | `monkey-tested` | `human-tested` | `delivered`
- **Description**: One paragraph explaining the experiment
- **Plan**: Design decisions and module breakdown
- **Modules**: Table of files and their roles
- **Stimuli**: Table of stimuli files, their source (generated/provided/placeholder), and notes
- **Changelog**: Dated entries tracking what changed and why
- **Known Issues**: Anything unresolved

### Rules
- **Platform changes go in the project root** (CLAUDE.md, SKILL.md, runner/, mcp_server/, etc.)
- **Experiment changes go in experiments/<name>/** — never mix platform and experiment changes in the same commit
- **Do not delete experiment folders** — mark status as `abandoned` if no longer needed
- **Stimuli stay inside the experiment folder** — keeps each experiment self-contained

## Safety Guardrails
- **Never modify a user's original .iqx script.** When asked to work on an existing Inquisit file, copy it (or extract the relevant parts) into a new file and work on the copy. The original stays untouched as a reference. Name the copy clearly (e.g., `original_v2.iqx` or copy into a new experiment folder).
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
- **No `/ iti` attribute** — use `/ posttrialpause` on trials
- **No `/ size` on blocks** — control trial count via explicit position indices in `/ trials`
- **Instructions use `<page>`, not `<instruct>`** — `/ preinstructions = (page_name)`
- **`noresponse` needs a duration** — set `/ trialduration` or `/ timeout`
- **One `nextvalue` per list per cycle** — use separate `<list>` elements for independent draws
- **Add `<data>` for custom values** — `values.*` won't appear in .iqdat without explicit `/ columns`

### Reference Library — 202 Real Inquisit 6 Scripts
`scripts/library_v6/` contains 202 complete, working .iqx scripts from the Millisecond test library. These are **the single most valuable resource** for building correct Inquisit syntax. Each file is a standalone experiment (surveys, RT tasks, IATs, cognitive tasks, etc.).

**When to consult the library:**
- **Before writing any new element type** you haven't used before (e.g., first time using `<radiobuttons>`, `<slider>`, `<likert>`, `<picture>`, `<sound>`, `<shape>`, etc.) — grep the library to see how real scripts use it.
- **When you get a compile error** you don't understand — grep for the attribute or element that's failing and see how working scripts handle it.
- **When building a known paradigm** (IAT, Stroop, dot-probe, flanker, go/no-go, etc.) — find the matching library script and use it as a reference for structure, trial flow, and scoring.
- **When unsure about attribute syntax** — e.g., how to set `stimulustimes`, `beginresponsetime`, `validresponse`, `ontrialbegin`, conditional branching, etc.

**How to use the library:**
```
# Find scripts that use a specific element or attribute
Grep: pattern="<likert" path="scripts/library_v6/"
Grep: pattern="/ correctresponse" path="scripts/library_v6/"

# Find a specific paradigm (e.g., IAT, Stroop, flanker)
Grep: pattern="<trial " path="scripts/library_v6/iat_rf.iqx"  (read the whole IAT script)
Grep: pattern="flanker" path="scripts/library_v6/"

# See how scoring or data export works
Grep: pattern="<data>" path="scripts/library_v6/"
Grep: pattern="expressions\." path="scripts/library_v6/"
```

**Key scripts by paradigm** (filenames are self-explanatory):
- IAT: `iat_rf.iqx`, `briefiat_german.iqx`, `eatingiat.iqx`, `angeriat.iqx`
- Stroop: `stroopwithcontrolkeyboard_romanian.iqx`, `foodstroop_keyboardinput.iqx`
- Go/No-Go: `affectivegonogo.iqx`, `shiftgng.iqx`
- Dot-probe: `genericdotprobe_words.iqx`, `dpdt_richards.iqx`
- Flanker: `flankertask.iqx`
- Surveys: `demographicsurvey.iqx`, `phq_9.iqx`, `gad_7.iqx`, `dass21.iqx`, `bdi_orig.iqx`
- RT tasks: `srtvisual.iqx`, `fourchoicereactiontimetask.iqx`, `lexicaldecisiontask.iqx`
- Memory: `sternbergmemorytask.iqx`, `corsiblocktappingtask.iqx`, `automatedospan.iqx`
- Task switching: `taskswitching.iqx`, `numberlettertask.iqx`

Also available:
- `scripts/library_v7/` — 385 Inquisit 7 script folders (if downloaded via `scripts/download_library.py`). Use v6 first — it's simpler.
- `scripts/library_index.md` — Full index with grep examples.

### Screen Capture Policy
Screen capture is controlled by `/ screenCapture = true` on individual trials in the .iqx script. To get captures:
1. Add `/ screenCapture = true` to trials you want to inspect
2. Run with `run_monkey` or `run_script`
3. Captures appear in the run's `screencaptures/` folder
4. Remove `/ screenCapture = true` before final delivery
