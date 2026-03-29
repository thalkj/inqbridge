"""MCP server exposing InquisitBridge runner as tools.

Thin wrapper - all logic lives in the runner package.
"""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from runner.run import run_script
from runner.manifest import read_manifest
from runner.visual_qa import deduplicate_captures, score_layout, write_capture_index
from runner.patcher import Patch, apply_patches, validate_patches
from runner.data_qa import assess_monkey_data
from runner.visual_qa_deep import score_layout_deep as _score_layout_deep
from runner.preflight import preflight_check as _preflight_check
from runner.config import ARTIFACTS_DIR, SCRIPTS_DIR, INCLUDES_DIR


app = Server("inquisit-bridge")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="run_script",
            description="Run an Inquisit script in human or monkey mode. Creates a full audited run with manifest, source snapshot, and artifact collection. WORKFLOW: always run preflight_check first. After this, use score_layout/score_layout_deep for visual analysis and assess_data_quality for data analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Path to the .iqx script (relative to scripts/ or absolute)"},
                    "mode": {"type": "string", "enum": ["human", "monkey"], "default": "monkey"},
                    "subject_id": {"type": "string", "default": "1"},
                    "group_id": {"type": "string", "default": "1"},
                    "capture_policy": {"type": "string", "enum": ["targeted", "all", "none"], "default": "targeted"},
                    "timeout_seconds": {"type": "integer", "default": 600},
                },
                "required": ["script_path"],
            },
        ),
        Tool(
            name="run_monkey",
            description="Convenience wrapper: run a script in Monkey mode for smoke testing. WORKFLOW: always run preflight_check first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "subject_id": {"type": "string", "default": "1"},
                    "group_id": {"type": "string", "default": "1"},
                },
                "required": ["script_path"],
            },
        ),
        Tool(
            name="read_manifest",
            description="Load a previous run's manifest.json and return a summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Run ID (folder name under artifacts/)"},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="read_data_preview",
            description="Show the first N lines of raw and summary data files from a run.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "max_lines": {"type": "integer", "default": 20},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="score_layout",
            description="Analyze screen captures from a run for layout issues (clipping, contrast, crowding, overlap). Use after run_script/run_monkey when screenCapture was enabled. For deeper analysis, also run score_layout_deep.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="patch_layout",
            description="Apply constrained layout edits. Only modifies allowed attributes: position, size, fontStyle, canvasPosition, canvasSize, canvasAspectRatio, defaults. Use after score_layout identifies concrete issues. After patching, rerun the script and use compare_runs to verify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "element_context": {"type": "string"},
                                "attribute": {"type": "string"},
                                "old_value": {"type": "string"},
                                "new_value": {"type": "string"},
                            },
                            "required": ["file_path", "element_context", "attribute", "old_value", "new_value"],
                        },
                    },
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["patches"],
            },
        ),
        Tool(
            name="compare_runs",
            description="Compare two runs: before/after manifests, capture counts, and verdict changes. Use after patch_layout + rerun to verify improvements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id_before": {"type": "string"},
                    "run_id_after": {"type": "string"},
                },
                "required": ["run_id_before", "run_id_after"],
            },
        ),
        Tool(
            name="assess_data_quality",
            description="Assess monkey run data quality: per-trialcode profiles with response variety, accuracy distribution, latency patterns, stimulus presentation, and context-aware flags. Returns structured summaries for LLM interpretation. Use after run_script/run_monkey to check whether each trial type produced meaningful data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Run ID (folder name under artifacts/)"},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="score_layout_deep",
            description="Deep layout analysis: detect element overlap, font too small, alignment issues. Produces per-capture element inventories and text descriptions for LLM interpretation. More thorough than score_layout. Use after run_script/run_monkey when screenCapture was enabled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Run ID (folder name under artifacts/)"},
                    "purpose_hint": {
                        "type": "string",
                        "description": "Optional hint about experiment type to tune thresholds (e.g. rt_task, survey, iat)",
                    },
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="preflight_check",
            description="Run pre-flight validation on a .iqx script BEFORE executing it. Catches: missing file references (<picture>/<sound>/<video> pointing to non-existent files), unclosed brackets in attribute expressions, and elements referenced but never defined (phantom references from AI-generated code). Always run this before run_script/run_monkey.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Path to the .iqx script (relative to scripts/ or absolute)"},
                },
                "required": ["script_path"],
            },
        ),
    ]


def _resolve_script(script_path: str) -> Path:
    """Resolve script path - try relative to scripts/ first, then absolute."""
    p = Path(script_path)
    if p.is_absolute() and p.is_file():
        return p
    candidate = SCRIPTS_DIR / script_path
    if candidate.is_file():
        return candidate
    if p.is_file():
        return p.resolve()
    raise FileNotFoundError(f"Script not found: {script_path}")


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "run_script":
            script = _resolve_script(arguments["script_path"])
            result = run_script(
                script_path=script,
                mode=arguments.get("mode", "monkey"),
                subject_id=arguments.get("subject_id", "1"),
                group_id=arguments.get("group_id", "1"),
                timeout_seconds=arguments.get("timeout_seconds", 600),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "run_monkey":
            script = _resolve_script(arguments["script_path"])
            result = run_script(
                script_path=script,
                mode="monkey",
                subject_id=arguments.get("subject_id", "1"),
                group_id=arguments.get("group_id", "1"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "read_manifest":
            run_id = arguments["run_id"]
            manifest_path = ARTIFACTS_DIR / run_id / "manifest.json"
            if not manifest_path.is_file():
                return [TextContent(type="text", text=f"Manifest not found for run: {run_id}")]
            manifest = read_manifest(manifest_path)
            return [TextContent(type="text", text=json.dumps(manifest, indent=2))]

        elif name == "read_data_preview":
            run_id = arguments["run_id"]
            max_lines = arguments.get("max_lines", 20)
            run_dir = ARTIFACTS_DIR / run_id
            data_dir = run_dir / "data"
            if not data_dir.is_dir():
                return [TextContent(type="text", text=f"No data directory found for run: {run_id}")]

            preview = {}
            for f in sorted(data_dir.iterdir()):
                if f.is_file():
                    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines]
                    preview[f.name] = lines

            return [TextContent(type="text", text=json.dumps(preview, indent=2))]

        elif name == "score_layout":
            run_id = arguments["run_id"]
            cap_dir = ARTIFACTS_DIR / run_id / "screencaptures"
            if not cap_dir.is_dir():
                return [TextContent(type="text", text=f"No screen captures found for run: {run_id}")]

            image_paths = sorted(cap_dir.glob("*"))
            image_paths = [p for p in image_paths if p.suffix.lower() in (".bmp", ".png", ".jpg")]

            if not image_paths:
                return [TextContent(type="text", text="No image files found in screencaptures/")]

            # Deduplicate
            entries = deduplicate_captures(image_paths)
            write_capture_index(entries, run_id, ARTIFACTS_DIR / run_id)

            # Score unique captures
            unique_paths = [Path(e.kept_path) for e in entries if not e.is_duplicate]
            scores = score_layout(unique_paths)

            result = {
                "run_id": run_id,
                "total_captures": len(entries),
                "unique_captures": len(unique_paths),
                "layout_scores": scores,
            }
            # Write scores
            analysis_dir = ARTIFACTS_DIR / run_id / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)
            (analysis_dir / "layout_scores.json").write_text(
                json.dumps(scores, indent=2), encoding="utf-8"
            )

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "patch_layout":
            patch_dicts = arguments["patches"]
            dry_run = arguments.get("dry_run", False)
            patches = [
                Patch(
                    file_path=p["file_path"],
                    element_context=p["element_context"],
                    attribute=p["attribute"],
                    old_value=p["old_value"],
                    new_value=p["new_value"],
                )
                for p in patch_dicts
            ]

            # Validate first
            errors = validate_patches(patches)
            if errors:
                return [TextContent(type="text", text=json.dumps({"status": "validation_failed", "errors": errors}, indent=2))]

            results = apply_patches(patches, dry_run=dry_run)
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "compare_runs":
            run_before = arguments["run_id_before"]
            run_after = arguments["run_id_after"]

            m_before_path = ARTIFACTS_DIR / run_before / "manifest.json"
            m_after_path = ARTIFACTS_DIR / run_after / "manifest.json"

            if not m_before_path.is_file():
                return [TextContent(type="text", text=f"Before manifest not found: {run_before}")]
            if not m_after_path.is_file():
                return [TextContent(type="text", text=f"After manifest not found: {run_after}")]

            m_before = read_manifest(m_before_path)
            m_after = read_manifest(m_after_path)

            comparison = {
                "before_run_id": run_before,
                "after_run_id": run_after,
                "verdict_change": f"{m_before.get('verdict')} -> {m_after.get('verdict')}",
                "before_captures": len(m_before.get("screen_captures", [])),
                "after_captures": len(m_after.get("screen_captures", [])),
                "before_data_files": len(m_before.get("raw_data_files", [])),
                "after_data_files": len(m_after.get("raw_data_files", [])),
                "source_changes": _compare_snapshots(
                    m_before.get("executed_snapshot", {}).get("files", []),
                    m_after.get("executed_snapshot", {}).get("files", []),
                ),
            }

            return [TextContent(type="text", text=json.dumps(comparison, indent=2))]

        elif name == "assess_data_quality":
            run_id = arguments["run_id"]
            run_dir = ARTIFACTS_DIR / run_id
            data_dir = run_dir / "data"
            source_dir = run_dir / "source"

            if not data_dir.is_dir():
                return [TextContent(type="text", text=f"No data directory for run: {run_id}")]

            report = assess_monkey_data(
                run_id=run_id,
                data_dir=data_dir,
                source_dir=source_dir if source_dir.is_dir() else None,
            )

            # Write report
            analysis_dir = run_dir / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)
            (analysis_dir / "data_quality.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )

            return [TextContent(type="text", text=json.dumps(report, indent=2))]

        elif name == "score_layout_deep":
            run_id = arguments["run_id"]
            purpose_hint = arguments.get("purpose_hint")
            cap_dir = ARTIFACTS_DIR / run_id / "screencaptures"
            if not cap_dir.is_dir():
                return [TextContent(type="text", text=f"No screen captures found for run: {run_id}")]

            image_paths = sorted(cap_dir.glob("*"))
            image_paths = [p for p in image_paths if p.suffix.lower() in (".bmp", ".png", ".jpg")]

            if not image_paths:
                return [TextContent(type="text", text="No image files found in screencaptures/")]

            # Deduplicate first
            entries = deduplicate_captures(image_paths)
            unique_paths = [Path(e.kept_path) for e in entries if not e.is_duplicate]

            # Deep analysis
            scores = _score_layout_deep(unique_paths, purpose_hint=purpose_hint)

            result = {
                "run_id": run_id,
                "total_captures": len(entries),
                "unique_captures": len(unique_paths),
                "deep_layout_results": scores,
            }

            # Write results
            analysis_dir = ARTIFACTS_DIR / run_id / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)
            (analysis_dir / "layout_scores_deep.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "preflight_check":
            script = _resolve_script(arguments["script_path"])
            result = _preflight_check(script, include_search_dirs=[INCLUDES_DIR])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


def _compare_snapshots(before: list[dict], after: list[dict]) -> list[dict]:
    """Compare source snapshots between runs."""
    before_map = {f["path"]: f["sha256"] for f in before}
    after_map = {f["path"]: f["sha256"] for f in after}

    changes = []
    all_paths = set(before_map) | set(after_map)
    for p in sorted(all_paths):
        b = before_map.get(p)
        a = after_map.get(p)
        if b and not a:
            changes.append({"path": p, "change": "removed"})
        elif a and not b:
            changes.append({"path": p, "change": "added"})
        elif a != b:
            changes.append({"path": p, "change": "modified"})

    return changes


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
