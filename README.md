# InqBridge

An unofficial, AI-assisted tool for building and testing [Inquisit](https://www.millisecond.com/) experiments using [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Write .iqx scripts, run them via Monkey mode, analyze screen captures and data quality, patch layout issues, and deliver tested experiments — all through natural language and MCP tools.

> **Not affiliated with Millisecond Software.** Inquisit is a product of [Millisecond Software](https://www.millisecond.com/). This tool automates scripting workflows but requires a valid Inquisit license.

> **Not actively maintained.** This was developed as a research tool and is released as-is. Feel free to fork, adapt, and extend to your needs. Issues and pull requests may not be reviewed.

## Citation

If you use InqBridge in your research, please cite:

> Halkjelsvik, T. (2026, March 31). *InqBridge: Unofficial tool for AI-assisted Inquisit scripting* (Version 0.1) [Computer software/Source code]. GitHub. https://github.com/username/inqbridge

BibTeX:
```bibtex
@software{halkjelsvik2026inqbridge,
  author    = {Halkjelsvik, Torleif},
  title     = {{InqBridge}: Unofficial tool for {AI}-assisted {Inquisit} scripting},
  year      = {2026},
  month     = {3},
  version   = {0.1},
  url       = {https://github.com/username/inqbridge},
  note      = {Computer software/Source code}
}
```

## What You Get

**16 MCP tools** for the full experiment lifecycle:

| Phase | Tools |
|-------|-------|
| **Scaffold** | `scaffold_experiment` — generate starter templates for IAT, Stroop, survey, RT task, or custom experiments |
| **Validate** | `preflight_check` — catch missing files, bracket bugs, phantom references before running |
| | `validate_merge` — check namespace conflicts before combining modules |
| **Execute** | `run_monkey`, `run_script` — run with `fast_mode`, `auto_capture`, and `auto_fix` support |
| **Analyze** | `score_layout`, `score_layout_deep` — visual QA on screen captures |
| | `assess_data_quality` — per-trialcode profiles with context-aware flags |
| | `read_manifest`, `read_data_preview` — inspect run metadata and data |
| | `generate_spec` — structured experiment summary (flow, responses, data schema, stimuli) |
| **Iterate** | `patch_layout` — constrained layout edits (position, size, font only) |
| | `compare_runs` — diff before/after runs to verify changes |
| | `decompose_script` — split monolithic scripts into testable modules |
| **Manage** | `list_runs` — browse previous runs with verdicts and capture counts |
| **Deliver** | `prepare_delivery` — strip debug artifacts, validate, generate spec, package |

Also included:
- **202 reference scripts** from the Millisecond test library (`scripts/library_v6/`) — greppable syntax examples for every major paradigm
- **Syntax cheat sheet** (`docs/inquisit_cheat_sheet.txt`) — 20 patterns with working examples and common mistakes
- **Reusable module library** (`includes/library/`) — demographics, consent, debrief, completion codes, attention checks
- **Programmer's manual** (`docs/inquisit_programmers_manual.txt`) — searchable Inquisit 6 reference

## Requirements

- Windows 10/11
- Python 3.12+
- Inquisit 6 (from [Millisecond Software](https://www.millisecond.com/)) — a valid license is required
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — available as CLI, desktop app, or IDE extension
- An Anthropic API key or Claude Pro/Max subscription (for Claude Code)

## Getting Started

1. Clone or download this repo.
2. Open Claude Code in the folder.
3. Say `/inq-bridge` or just describe the experiment you want to build.

That's it. Claude handles environment setup, Inquisit discovery, and the full build-test-iterate workflow. You'll see a few permission prompts the first time — accept them and the rest of the session flows smoothly.

**Example prompts:**
- *"Build a Stroop task with practice and test blocks"*
- *"I have this .iqx script, can you debug it?"*
- *"Create an IAT measuring attitudes toward healthy food"*
- *"I want to replicate Study 1 from this paper: [paste details]"*

## How It Works

InqBridge combines three layers:

1. **`CLAUDE.md`** — Project instructions loaded automatically every conversation. Contains setup steps, Inquisit syntax rules, safety guardrails, and lessons learned from hard bugs.
2. **`SKILL.md`** (`.claude/skills/inq-bridge/`) — Activated when you say `/inq-bridge`. Contains the experiment workflow: intake checklist, build phases, testing gates, and delivery steps.
3. **MCP server** — 16 tools that Claude calls during the workflow. Runs preflight checks, executes Inquisit scripts, analyzes captures and data, patches layouts, and packages deliverables.

Each experiment lives in its own folder under `experiments/` with an `EXPERIMENT.md` tracking file (status, changelog, known issues). This keeps experiment work separate from platform code.

## Troubleshooting

If MCP tools aren't responding:
- Restart Claude Code (needed once after initial setup so it picks up `.mcp.json`)
- Check that Inquisit 6 is installed in `C:\Program Files\Millisecond Software`
- If multiple Inquisit versions are installed, Claude will ask which one you're licensed for

## Machine-Specific Files (gitignored)

These are generated by Claude during setup:
- `.mcp.json` — MCP server launch config (absolute paths for your machine)
- `local.json` — your Inquisit executable path (only if auto-discovery needs overriding)
- `.venv/` — Python virtual environment

## License

MIT. See [LICENSE](LICENSE) for details.

The 202 Inquisit reference scripts in `scripts/library_v6/` are from the [Millisecond Test Library](https://www.millisecond.com/library) and are included for reference purposes. They remain the property of Millisecond Software.
