---
name: inquisit-bridge
description: Build and maintain the local Inquisit runner and MCP bridge. Use for tasks involving Inquisit scripts, run artifacts, Monkey mode, screenCapture analysis, layout patching, and traceable experiment iteration.
---

When working on this project:

1. Treat the local runner as authoritative and the MCP wrapper as thin.
2. Preserve executed source snapshots for every run.
3. Use built-in Inquisit screenCapture for layout QA.
4. Use Monkey mode for smoke tests and data-file generation.
5. **Never invoke human mode unless the user explicitly asks for it.** When testing, always use monkey mode to check for errors and fix them. Human mode requires the user to sit at the screen and interact — only run it when directly requested.
6. Use debugTrace hooks and manifest files for traceability.
7. When modifying scripts, prefer include files and defaults for reuse.
8. When fixing layout, patch only the approved layout attributes unless the user asks otherwise.
9. After each layout patch, rerun the same target and compare before/after captures.
10. Summarize what changed, how it was validated, and what remains unverified.

## Debugging Inquisit Scripts — Systematic Approach

### Diagnosing exit code 0 (compile/parse failure)
Inquisit 6 returns **exit code 1** on normal completion (including Ctrl+Q abort). Exit code 0 means the script never ran. When you see exit code 0:

1. **Check stderr** — Inquisit prints resource loading errors there (e.g., missing picture files). These may look like warnings but can be fatal.
2. **Check duration** — Under ~5 seconds usually means compile failure. Over ~10 seconds with no data means a runtime error or monkey-mode failure.
3. **Check data directory** — No new `.iqdat` files = script never started executing trials. Old files from previous runs may still be present (filter by script name and timestamp).

### onPrepare evaluates once, not per-trial
`/ onPrepare = [text.X.skip = (values.something != 1)]` runs **once at script startup**, not each time the trial executes. If `values.something` changes between blocks (e.g., set in `onBlockBegin`), the skip state is frozen at its initial value. **Use `/ ontrialbegin` to set `.skip` dynamically.** This is a silent bug — the script compiles and runs, but the element stays permanently skipped or shown regardless of the current value.

### Common causes of silent compile failure

| Symptom | Cause | Fix |
|---------|-------|-----|
| Exit 0, "Network Error" in stderr | `<picture>` or `<sound>` references a missing file | Remove/comment the element, or provide the file. Inquisit loads ALL elements at startup regardless of which blocks run. |
| Exit 0, no error message | Unclosed `[` bracket in `ontrialbegin`/`ontrialend` | Check bracket balance with a script. Hard to spot in long multi-line attribute blocks. |
| Exit 0, no error message | Element referenced in `stimulusframes` or block `trials` that was never defined | Run a reference checker: extract all names from `stimulusframes`, `stimulustimes`, `trials`, `blocks` and verify each has a matching `<element>` definition. |
| Exit 0, no error message | Name used as wrong element type (e.g., text name used where trial is expected in block `trials`) | Verify element types match their usage context: blocks reference trials/surveypages, stimulusframes reference text/shape/picture. |

### Pre-run checklist for new or AI-generated scripts
1. **File references**: Verify every `<picture>`, `<sound>`, `<video>` element points to a file that exists in the script's directory.
2. **Bracket balance**: Count `[` and `]` in every `ontrialbegin`, `ontrialend`, `onblockbegin`, `onblockend`, and `branch` attribute.
3. **Element existence**: Extract all names from `stimulusframes`, `stimulustimes`, block `trials`, experiment `blocks`, and `preinstructions`/`postinstructions`. Verify each is defined with the correct element type.
4. **Tag balance**: Count opening `<element name>` tags vs closing `</element>` tags per type.
5. **Self-references**: Trials that use `trial.trialname.correct`, `trial.trialname.response`, etc. must use their own name, not a copy-pasted name from another trial.

### Isolating failures incrementally
When a full experiment fails, reduce `prove_eksp` (or the test experiment) to just 1 block. If that works, add blocks back one at a time. This quickly narrows which block introduces the parse error.

### Stale data files
Inquisit writes to `data/` relative to the script. Old `.iqdat` files persist between runs. The runner may collect them and report a false "completed" verdict. Before a diagnostic run, clean or note the existing files so you can tell which are new.

### Timeout estimation for monkey mode
Long experiments with animated trials (`stimulustimes` going to 14000ms+) need generous timeouts. Rough estimate: count trials, multiply by average trial duration (including animations, not just response time). Experience blocks with 45 trials at 5s each = 225s alone. Default to 600s for complex experiments.
