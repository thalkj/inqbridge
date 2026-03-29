# InquisitBridge - Work State

## Status: ALL PHASES COMPLETE AND VERIFIED

## Completed
- [x] Created InquisitBridge folder and local git
- [x] Located Inquisit 6 exe: `C:\Program Files\Millisecond Software\Inquisit 6\Inquisit.exe`
- [x] Confirmed CLI flags: `-s`, `-g`, `-m monkey|human` (return code 1 = normal)
- [x] Installed Python 3.12 via winget
- [x] Created project structure
- [x] Phase 1: Local Python runner
- [x] Phase 2: Visual QA (dedup found 6/8 perceptual duplicates, scoring works)
- [x] Phase 3: Constrained layout patcher
- [x] Phase 4: MCP server wrapper (7 tools)
- [x] 27 unit tests all passing
- [x] MCP registered in .mcp.json
- [x] End-to-end monkey test verified: script runs, data collected, 8 captures, verdict=completed
- [x] Full pipeline tested: run -> collect -> dedup -> score -> compare

## Changes Made to Computer
- Installed Python 3.12.10 via `winget install Python.Python.3.12`
- Created virtual environment at InquisitBridge/.venv/

## Inquisit 6 Behavior Notes
- Exit code 1 is normal (not an error)
- Screen captures go to `data/screencaptures/` (not `screencaptures/`)
- Captures are .png format (not .bmp as some docs suggest)
- stdout outputs version + numeric data (response codes + latencies)
- Data files go to `data/` relative to the script

## Key Files
- `runner/run.py` - Main entry: `run_script()`
- `runner/cli.py` - CLI: `python -m runner.cli script.iqx -m monkey`
- `mcp_server/main.py` - MCP server (7 tools)
- `scripts/hello_world.iqx` - Sample test script
- `includes/defaults_layout.iqx` - Shared layout defaults

## Next Steps
- User review of the implementation
- Test with more complex .iqx scripts
- Test layout patcher on real scripts
- Consider adding summary data collection (Inquisit may need specific config)
