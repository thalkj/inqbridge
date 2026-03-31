# Difficulties Log — Undo Threshold Experiment

This file records implementation difficulties, workarounds, and lessons learned during development. Updated as issues arise.

## Format
Each entry: date, category, description, resolution/status.

---

## Log

### 2026-03-31 | Picture loading | `<picture>` with 90 items via `/ inputfile` fails to initialize
- **Symptom**: "Unable to initialize <picture ut_dot_stimulus> item number X" — different X each run (77, 46)
- **Analysis**: All 90 PNG files verified valid (400×400 RGB). Preflight passes. Error occurs during Inquisit's prepare() phase.
- **Hypothesis**: Inquisit 6 may struggle pre-loading 90 × 400×400 PNG images via `/ inputfile`. The randomness of which item fails suggests a resource/timing issue.
- **Attempted**: Both fast_mode and normal mode fail identically.
- **Resolution**: Switched from `/ inputfile` to inline numbered items in `<item>`. This fixed the loading issue. Root cause unclear — possibly OneDrive path or inputfile parsing. Also resized images to 200×200 as precaution.

### 2026-03-31 | Data logic | `trial.X.response` returns scancode, not key name
- **Symptom**: `ut_initial_correct` always 0. Data shows response=32 (d) and response=37 (k) instead of "d"/"k".
- **Analysis**: Inquisit's `trial.X.response` returns keyboard scancodes. `trial.X.responsetext` returns the string.
- **Resolution**: Changed all `trial.X.response` comparisons to `trial.X.responsetext`. Added `/ iscorrectresponse` for native correctness tracking. BUT see next entry — responsetext has its own trap.

### 2026-03-31 | Data logic | `responsetext` returns "0" on timeout, not empty string
- **Symptom**: Timeouts leaking into correction trials; `correction_made=1` when no key was pressed.
- **Analysis**: When a trial times out, `trial.X.responsetext` returns the string "0" (not ""). So `responsetext != ""` is TRUE on timeout, causing downstream logic to treat "0" as a real response.
- **Resolution**: Use `trial.X.response != 0` (numeric scancode) for timeout detection, and `trial.X.response != 0` for "was a key pressed?" checks. Reserve `.responsetext` only for reading the actual key name.

### 2026-03-31 | Workflow | `auto_capture=true` generates excessive captures (562 for 180 trials)
- **Symptom**: 562 screen captures for a 90+90 trial experiment. score_layout/score_layout_deep takes too long.
- **Analysis**: `auto_capture` injects `screenCapture=true` into ALL trials (test, practice, feedback, instruction, correction). Most captures are redundant — same layout with different dot images.
- **Resolution**: For layout checks, manually read 5-6 representative captures instead of running score_layout on 562 files. Only use `auto_capture` when you need comprehensive visual checks. For targeted captures, manually add `/ screenCapture = true` to specific trials.
- **Lesson for CLAUDE.md**: Add guidance on when NOT to use auto_capture.

### 2026-03-31 | Data logic | `concat()` takes only 2 arguments in Inquisit 6
- **Symptom**: Completion code was empty string despite `concat("9", d1, d2, d3)` in ontrialbegin.
- **Resolution**: Chain concat calls: `concat(a, b)` then `concat(result, c)`. Inquisit 6's concat is binary, not variadic.

### 2026-03-31 | Design | Undo timeout trials produce no data row
- **Symptom**: Undo block has <90 correction_trial rows. Timeouts in initial trial branch to feedback_timeout, skipping the correction_trial which is the only trial with recorddata=true.
- **Impact**: Low for humans (few timeouts). High for monkey (~30% timeouts). Not a bug — by design, timeouts mean no decision was made.
- **Resolution**: Acceptable. Document for analysts: missing rows in undo condition = timeouts.

### 2026-03-31 | UX feedback from human test
- Instructions: "moving dots" was confusing — they're static images with motion trails. Fixed to explain shadow/trail metaphor.
- "BLOCK: FINAL CHOICE" felt abrupt — rewritten as "PART: IMMEDIATE DECISIONS" with gentler framing.
- Correction window text was distracting — removed it, made correction window silent.
- "MAIN TASK" didn't specify which condition — now says "MAIN TASK — IMMEDIATE DECISIONS" or "— DECISIONS WITH CORRECTION".
- Practice abort was too harsh — now continues after 3 failed attempts but flags participant with 9-prefix on completion code.
- Correction window (300ms) felt too quick — increased to 500ms.
- Added completion code generation (3 digits 1-6, 9-prefix for practice failures).
