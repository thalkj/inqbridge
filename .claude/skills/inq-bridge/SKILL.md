---
name: inq-bridge
description: Build Inquisit experiments from scratch or iterate on existing ones using the InqBridge MCP tools. Use for tasks involving Inquisit scripts, run artifacts, Monkey mode, screenCapture analysis, layout patching, and traceable experiment iteration.
---

## Setup Check (do this FIRST)

Before using any MCP tools, verify the environment is ready. Handle all steps yourself via Bash — never tell the user to "run setup.bat" or go to a terminal.

1. Check that `.venv/Scripts/python.exe` exists in the project root. If missing:
   - Tell the user what you need to do: create a Python venv and install dependencies (~1 minute).
   - On approval, run via Bash: `python -m venv .venv && .venv/Scripts/pip install -q -e ".[dev]"`
2. Check that `.mcp.json` exists. If missing, create it with the MCP server config pointing to `.venv/Scripts/python.exe -m mcp_server.main` with the project root as cwd.
3. `local.json` is **optional** — Inquisit is auto-discovered from `C:\Program Files\Millisecond Software` by `runner/config.py`. Only needed for a non-standard install path.
4. If MCP tool calls fail with connection errors after setup, the user must restart Claude Code so the MCP server process loads. This is the one step Claude cannot do itself. In the current session, invoke runner modules directly via Bash (e.g., `.venv/Scripts/python -m runner.preflight ...`).

Do NOT tell the user to "run setup.bat". Handle all setup via Bash, asking approval before running commands.

### Permission Warming

After setup, if the user is not in "allow all" mode, run a quick warmup that exercises each tool type once (Bash, Write, MCP preflight, MCP run_monkey, Read). This gets Accept prompts out of the way before the real workflow begins. Tell the user: *"I'll run a quick warmup — you'll see a few Accept prompts. After that the session flows without interruptions."* See CLAUDE.md "Permission Warming" section for the full sequence.

---

## Experiment Discovery (do after setup)

On skill invocation, scan the `experiments/` directory for existing experiments:

1. List all subdirectories under `experiments/` that contain an `EXPERIMENT.md`.
2. For each, read the `Status` line from `EXPERIMENT.md`.
3. Present the list to the user:
   ```
   Found existing experiments:
   • flower_prediction — Status: human-tested
   • my_stroop — Status: building

   Would you like to continue one of these, or start a new experiment?
   ```
4. If the user picks an existing experiment, read its full `EXPERIMENT.md` to understand context before proceeding.
5. If starting new, proceed to the Pre-Coding Intake Checklist.

If no `experiments/` folder exists or it's empty, skip straight to the intake checklist.

---

## Core Principles

1. Treat the runner as authoritative and the MCP wrapper as thin.
2. Preserve executed source snapshots for every run.
3. Use built-in Inquisit screenCapture for layout QA — not OS screenshots.
4. Use Monkey mode for smoke tests and data-file generation.
5. **Never invoke human mode unless the user explicitly asks for it.** Monkey mode is always the default. Human mode requires the user to interact at the screen.
6. Use manifest files for traceability.
7. When modifying scripts, prefer include files and defaults for reuse.
8. When fixing layout, patch only approved layout attributes unless told otherwise.
9. After each layout patch, rerun the same target and compare before/after captures.
10. Summarize what changed, how it was validated, and what remains unverified.

---

## Pre-Coding Intake Checklist

Before writing any experiment code, gather this information from the user. Ask all universal questions; add paradigm-specific questions based on experiment type.

### Universal Questions (always ask)

1. **What is the experiment about?** Brief description of the task and hypothesis.
2. **How many conditions/groups?** Between-subjects groups, within-subjects conditions, or both.
3. **Estimated duration?** How long should a participant session take.
4. **Demographics to collect?** Default: age, gender, education. Offer to customize (add handedness, ethnicity, etc.). Library fragments available in `includes/library/demographics_full.iqx`.
5. **Contact information?** Researcher name, email, IRB/ethics number — shown on consent and debrief screens. Library: `includes/library/consent_screen.iqx`, `includes/library/debrief_standard.iqx`.
6. **Completion code needed?** For Prolific/MTurk — generates a unique code at the end. Library: `includes/library/completion_code.iqx`.
7. **Anonymity level?** Anonymous (no identifiable data), coded (completion code but no personal info), or identified (collects name/email).
8. **Attention checks?** Default: 1-2 instructed response items. Library: `includes/library/attention_checks.iqx` (instructed response, catch trial, content check).
9. **Response modality?** Keyboard keys, mouse clicks, or mixed.
10. **Target platform?** Lab computer, participant's own computer, specific screen size requirements.
11. **Stimuli needed?** Ask what visual/audio stimuli the experiment requires (images, sounds, videos). For each stimulus type, clarify:
    - **Can Claude generate it?** (charts, bar graphs, simple shapes, text-on-colored-background, fixation crosses → yes, generate with Python/matplotlib)
    - **User-provided?** (photos, specific images, audio recordings → user must supply these files before building)
    - **Not yet available?** → Generate labeled placeholder images (colored rectangles with text like "PLACEHOLDER: [stimulus description]") so the script compiles and layout can be tested. Use `.png` format, reasonable size (e.g., 400x300px). Record what needs replacing in a `stimuli/README.txt` manifest.

### Paradigm-Specific Questions (ask based on experiment type)

- **IAT**: target categories, attribute categories, number of blocks, practice block sizes
- **Stroop**: color set, word set, congruent/incongruent ratio
- **Survey**: scales to include, response format (Likert points), reverse-coded items
- **RT task**: stimulus types, foreperiod range, number of trials per condition

After collecting answers, proceed with the from-scratch workflow below. Use `scaffold_experiment` with the appropriate type and fill in the gathered details.

---

## From-Scratch Workflow

Use this workflow when building a new experiment. For iterating on an existing script, skip to the relevant phase.

### Phase 1 — Design

1. **Create the experiment folder** `experiments/<name>/` and write an initial `EXPERIMENT.md` with status `planning`, a description, and the design plan.
2. **Identify experiment components**: demographics, instructions, practice, test blocks, debrief, etc.
3. **List each module**, its purpose, and its dependencies on other modules.
4. **Consult the reference library** (`scripts/library_v6/`): Before writing code, grep for matching paradigms or element types. 202 working Inquisit 6 scripts are included. See CLAUDE.md "Reference Library" section for key scripts by paradigm and grep examples.
5. **Use `scaffold_experiment`** to generate starter files — or start from blank .iqx files.
   - For known paradigms (IAT, Stroop, survey, RT task): scaffold generates realistic reference templates.
   - For novel designs: use `experiment_type = "custom"` for minimal stubs.
   - Templates are starting points, not constraints — modify or discard freely.
5. **Update EXPERIMENT.md**: list the modules table and stimuli table.

### Phase 2 — Build & Test Modules

Each module is a standalone .iqx that can be tested independently.

**Naming convention:**
- `{experiment}_{role}_inc.iqx` — include files (config, instructions, practice, test, debrief)
- `test_{role}.iqx` — standalone testers that include config + one module
- `main.iqx` — the combined experiment

**Placeholder convention for inter-module dependencies:**
```
// PLACEHOLDER: replaced when merged with config_inc.iqx
<values>
/ condition_label = "PLACEHOLDER"
</values>
```

**Per-module test cycle (repeat until clean):**
1. `preflight_check` on the module
2. `run_monkey` with `fast_mode=True` (no captures needed yet — focus on compile + data correctness)
3. Inspect data file: check trial counts, trialcodes, custom values, stimulus content
4. Fix issues, repeat

**Layout gate (once per module, after data is correct):**
1. `run_monkey` with `auto_capture=True` (normal speed so captures are representative)
2. `score_layout` + `score_layout_deep` on captures
3. Read the screen captures to visually inspect layout
4. Fix layout issues if any, re-capture and compare
5. **Update EXPERIMENT.md**: set status to `building`, add changelog entry for what was built/fixed.

### Phase 3 — Integrate

1. Create `main.iqx` with `<include>` directives for all modules.
2. Create or update `config_inc.iqx` with shared `<values>`, `<defaults>`, `<expressions>`.
3. Replace all PLACEHOLDER values with real references.
4. Run `validate_merge` on all include files — zero conflicts required.
5. `preflight_check` on `main.iqx`.
6. `run_monkey` with `fast_mode=True` — verify compile + data.
7. `compare_runs` if iterating from a previous version.

### Phase 3b — Layout Gate (before suggesting human run)

1. `run_monkey` with `auto_capture=True` on the full experiment.
2. `score_layout` + `score_layout_deep` — check for clipping, overlap, font size issues.
3. Read captures to visually verify the participant experience.
4. Fix any layout issues, re-capture, compare.
5. Only after layout is clean, suggest a human run to the user.
6. **Update EXPERIMENT.md**: set status to `monkey-tested`, add changelog entry.

### Phase 4 — Polish & Deliver

1. Run `prepare_delivery` — it strips screenCapture, removes debug elements, validates, generates a spec, and packages everything into a self-contained folder.
2. Human-mode run for participant experience validation (or user waives this).
3. Edge case testing: longest text, unusual characters, missing stimuli.
4. **Delivery checklist** (prepare_delivery handles most of this automatically):
   - All PLACEHOLDER values resolved (`validate_merge` confirms)
   - No `/ screenCapture = true` remaining
   - No debug overlays
   - Script is self-contained (folder with main .iqx, all includes, all stimuli)
   - Top-of-script comment explains the experiment
   - All elements have purpose comments
5. **Update EXPERIMENT.md**: set status to `human-tested` or `delivered`, add final changelog entry.

### Working with Existing Scripts

When debugging or modifying a large existing script:
1. Run `generate_spec` to understand the script's structure.
2. If the script is monolithic and hard to debug, use `decompose_script` to split it into testable modules.
3. Test individual modules with `run_monkey(fast_mode=True)`.
4. After fixes, validate and recombine.

### Library Fragments

Pre-built include fragments are available in `includes/library/`:
- `demographics_full.iqx` — age, gender, education, handedness, ethnicity
- `consent_screen.iqx` — informed consent with configurable PLACEHOLDER values
- `debrief_standard.iqx` — thank you + purpose + contact info
- `completion_code.iqx` — unique completion code generator (for Prolific/MTurk)
- `attention_checks.iqx` — instructed response, catch trial, content check

All fragments use namespace prefixes (`demo_`, `consent_`, `debrief_`, `compcode_`, `attn_`) to avoid conflicts when included together.

---

## MCP Tool Reference

### Pre-execution
| Tool | When to use |
|------|-------------|
| **preflight_check** | BEFORE every execution. Catches missing files, bracket bugs, phantom references. |
| **scaffold_experiment** | Starting a new experiment. Generates module templates, main.iqx, and testers. |
| **validate_merge** | Before combining modules. Checks namespace conflicts and unresolved placeholders. |
| **generate_spec** | Produce a structured summary of any script: participant flow, response mapping, data schema, stimuli inventory. |
| **decompose_script** | Split a monolithic .iqx into modular includes for independent testing and debugging. |

### Execution
| Tool | When to use |
|------|-------------|
| **run_monkey** | Smoke testing. Supports `fast_mode` (collapsed timings), `auto_capture` (inject screenCapture), `auto_fix` (retry on compile error). |
| **run_script** | Full run (human or monkey mode). Same `fast_mode`/`auto_capture`/`auto_fix` parameters. Human mode only when user requests it. |

### Post-execution Analysis
| Tool | When to use |
|------|-------------|
| **list_runs** | Find previous run IDs (newest first, filterable by script name). |
| **read_manifest** | Load a run's full metadata summary. |
| **read_data_preview** | Inspect first N lines of data files from a run. |
| **score_layout** | Quick layout heuristics: clipping, contrast, crowding. |
| **score_layout_deep** | Detailed analysis: element overlap, font size, alignment. |
| **assess_data_quality** | Per-trialcode profiles: response variety, accuracy, latency, flags. |

### Iteration
| Tool | When to use |
|------|-------------|
| **patch_layout** | Apply constrained layout edits. Only after score_layout identifies issues. |
| **compare_runs** | Diff two runs (before/after patching or changes). |

### Delivery
| Tool | When to use |
|------|-------------|
| **prepare_delivery** | Final packaging: strips screenCapture, removes debug elements, runs validation, generates spec, copies all dependencies into a self-contained folder. |

### Run Parameters

- **`fast_mode`**: Creates temp copies with all stimulustimes collapsed to t=0, pauses zeroed, timeouts minimized. Use for quick compile/data checks. Original script untouched.
- **`auto_capture`**: Injects `/ screenCapture = true` into temp copies of all trials. Default on for `run_monkey`. Captures appear without modifying the real script.
- **`auto_fix`**: On compile error, runs preflight, auto-fixes missing file references and phantom references, retries once. Bracket bugs are flagged but not auto-fixed.

---

## Common Experiment Patterns

These are reference patterns showing typical module breakdowns and Inquisit-specific gotchas. They are not mandatory structures — modify to fit your experiment.

### IAT (Implicit Association Test)
- **Modules**: config, instructions, practice_compatible, practice_incompatible, test_compatible, test_incompatible, debrief
- **Key elements**: Category labels (`<text>` pinned to top corners), stimulus `<list>`s, `<trial>` with two `validresponse` keys
- **Gotcha**: 7 blocks with different trial counts and category pairings. Category labels must be `/ erase = false` so they stay visible.
- **Data**: D-score computed from latencies in compatible vs incompatible blocks.

### Stroop
- **Modules**: config, instructions, practice, test_congruent, test_incongruent, debrief
- **Key elements**: Color words as `<text>` stimuli with `/ txcolor` set dynamically, response keys for color names
- **Gotcha**: `txcolor` must be set via `/ ontrialbegin` using list values — can't use `/ txcolor = list.colors.nextvalue` directly in the element definition.

### Survey / Questionnaire
- **Modules**: config, demographics, scales (one per questionnaire), debrief
- **Key elements**: `<surveypage>`, `<radiobuttons>`, `<textbox>`, `<dropdown>`
- **Gotcha**: Surveypages use a different data format than trials. Data is in columns named after the question element, not in a `response` column.

### Simple RT Task
- **Modules**: config, instructions, practice, test, debrief
- **Key elements**: Fixation cross (`<text>`), target stimulus, variable foreperiod via `<list>`
- **Gotcha**: Use `/ stimulustimes` sequencing carefully: fixation → blank gap → stimulus. Set `/ beginresponsetime` to control when responses start being accepted.

### Likert Scales
- **Key elements**: `<radiobuttons>` with `/ options` and `/ orientation = horizontal`
- **Gotcha**: Long option labels overflow on small screens. Keep labels short or use `/ orientation = vertical`.

---

## Debugging Inquisit Scripts — Systematic Approach

### Diagnosing exit code 0 (compile/parse failure)
Inquisit 6 returns **exit code 1** on normal completion (including Ctrl+Q abort). Exit code 0 means the script never ran:
1. **Check stderr** — Inquisit prints resource loading errors there. These may look like warnings but can be fatal.
2. **Check duration** — Under ~5 seconds usually means compile failure. Over ~10 seconds with no data means a runtime error.
3. **Check data directory** — No new `.iqdat` files = script never started executing.

### onPrepare evaluates once, not per-trial
`/ onPrepare = [text.X.skip = (values.something != 1)]` runs **once at script startup**, not each time the trial executes. **Use `/ ontrialbegin` to set `.skip` dynamically.** This is a silent bug — the element stays permanently skipped or shown.

### Common causes of silent compile failure

| Symptom | Cause | Fix |
|---------|-------|-----|
| Exit 0, "Network Error" in stderr | Missing file in `<picture>` or `<sound>` | Remove/comment the element, or provide the file |
| Exit 0, no error message | Unclosed `[` bracket | Check bracket balance with preflight_check |
| Exit 0, no error message | Phantom element reference | Run preflight_check — catches undefined references |
| Exit 0, no error message | Name used as wrong element type | Verify element types match usage context |

### Pre-run checklist for new or AI-generated scripts
1. **File references**: Verify every `<picture>`, `<sound>`, `<video>` points to an existing file.
2. **Bracket balance**: Use preflight_check — it catches unclosed brackets automatically.
3. **Element existence**: Use preflight_check — it catches phantom references.
4. **Tag balance**: Count opening vs closing tags per element type.
5. **Self-references**: Trials using `trial.trialname.correct` must use their own name, not a copy-pasted name.

### Isolating failures incrementally
When a full experiment fails, reduce to just 1 block. If that works, add blocks back one at a time to narrow down which block introduces the error.

### Timeout estimation for monkey mode
Long experiments with animated trials (`stimulustimes` going to 14000ms+) need generous timeouts. Count trials × average trial duration. Default to 600s for complex experiments.
