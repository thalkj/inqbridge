"""Generate a human-readable experiment specification document.

Parses a .iqx script (+ includes) and produces a structured summary:
participant flow, response mapping, data schema, stimuli inventory, etc.
"""
from __future__ import annotations

import re
from pathlib import Path

from .includes import discover_includes
from .preflight import _ELEMENT_DEF_PATTERN


# Block trial counts: / trials = [1-20=trial_name]
_TRIAL_RANGE = re.compile(
    r"/\s*trials\s*=\s*\[([^\]]+)\]", re.IGNORECASE
)

# Experiment block order: / blocks = [1=block1; 2=block2]
_EXPT_BLOCKS = re.compile(
    r"/\s*blocks\s*=\s*\[([^\]]+)\]", re.IGNORECASE
)

# Valid response keys: / validresponse = ("a", "l")
_VALIDRESPONSE = re.compile(
    r'/\s*validresponse\s*=\s*\(([^)]+)\)', re.IGNORECASE
)

# Correct response: / correctresponse = ("a")
_CORRECTRESPONSE = re.compile(
    r'/\s*correctresponse\s*=\s*\(([^)]+)\)', re.IGNORECASE
)

# Stimulus times: / stimulustimes = [0=fix; 500=stim]
_STIMULUSTIMES = re.compile(
    r"/\s*stimulustimes\s*=\s*\[([^\]]+)\]", re.IGNORECASE
)

# Timeout: / timeout = 3000
_TIMEOUT = re.compile(
    r"/\s*timeout\s*=\s*(\d+)", re.IGNORECASE
)

# Post-trial pause: / posttrialpause = 500
_POSTTRIALPAUSE = re.compile(
    r"/\s*posttrialpause\s*=\s*(\d+)", re.IGNORECASE
)

# Pre-trial pause: / pretrialpause = 200
_PRETRIALPAUSE = re.compile(
    r"/\s*pretrialpause\s*=\s*(\d+)", re.IGNORECASE
)

# List items: / items = ("a", "b", "c")
_LIST_ITEMS = re.compile(
    r'/\s*items\s*=\s*\(([^)]+)\)', re.IGNORECASE
)

# Values: / varname = value
_VALUES_DEF = re.compile(
    r'/\s*(\w+)\s*=\s*(.+)', re.IGNORECASE
)

# Screen capture
_SCREENCAPTURE = re.compile(
    r'/\s*screenCapture\s*=\s*true', re.IGNORECASE
)

# Record data
_RECORDDATA_FALSE = re.compile(
    r'/\s*recorddata\s*=\s*false', re.IGNORECASE
)


def _parse_element_blocks(source: str) -> dict[str, list[dict]]:
    """Parse all element blocks and their attributes."""
    elements: dict[str, list[dict]] = {}

    # Match both named (<trial foo>) and unnamed (<expt>, <values>) elements
    block_pattern = re.compile(
        r"<(\w+)(?:\s+(\w+))?\s*>(.*?)</\1>",
        re.IGNORECASE | re.DOTALL,
    )

    for m in block_pattern.finditer(source):
        elem_type = m.group(1).lower()
        elem_name = m.group(2) or ""
        body = m.group(3)
        elements.setdefault(elem_type, []).append({
            "name": elem_name,
            "body": body,
        })

    return elements


def _count_trials_in_block(block_body: str) -> int:
    """Estimate trial count from a block's /trials attribute."""
    m = _TRIAL_RANGE.search(block_body)
    if not m:
        return 0

    content = m.group(1)
    total = 0
    for entry in content.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        # Parse range like "1-20=trial_name"
        range_match = re.match(r"(\d+)-(\d+)", entry)
        if range_match:
            total += int(range_match.group(2)) - int(range_match.group(1)) + 1
        elif re.match(r"\d+=", entry):
            total += 1
        else:
            total += 1

    return total


def _estimate_trial_duration_ms(trial_body: str) -> int:
    """Estimate a single trial's duration in milliseconds."""
    duration = 0

    # Max stimulustimes onset
    st_match = _STIMULUSTIMES.search(trial_body)
    if st_match:
        times = re.findall(r"(\d+)=", st_match.group(1))
        if times:
            duration = max(int(t) for t in times)

    # Add timeout if present, otherwise assume ~2s response time
    timeout_match = _TIMEOUT.search(trial_body)
    if timeout_match:
        duration += int(timeout_match.group(1))
    else:
        duration += 2000  # Assume 2s average response

    # Add pauses
    post_match = _POSTTRIALPAUSE.search(trial_body)
    if post_match:
        duration += int(post_match.group(1))

    pre_match = _PRETRIALPAUSE.search(trial_body)
    if pre_match:
        duration += int(pre_match.group(1))

    return duration


def _extract_response_keys(trial_body: str) -> dict:
    """Extract response key mapping from a trial."""
    info = {}

    vr_match = _VALIDRESPONSE.search(trial_body)
    if vr_match:
        keys = re.findall(r'"([^"]*)"', vr_match.group(1))
        info["valid_responses"] = keys

    cr_match = _CORRECTRESPONSE.search(trial_body)
    if cr_match:
        keys = re.findall(r'"([^"]*)"', cr_match.group(1))
        info["correct_response"] = keys

    return info


def generate_spec(
    script_path: Path,
    include_search_dirs: list[Path] | None = None,
) -> dict:
    """Generate a structured experiment specification.

    Args:
        script_path: Path to the main .iqx script.
        include_search_dirs: Directories to search for includes.

    Returns:
        Dict with experiment spec: flow, responses, data schema,
        stimuli inventory, duration estimate, and warnings.
    """
    includes = discover_includes(
        script_path, search_dirs=include_search_dirs or []
    )

    all_files = [script_path] + includes
    combined_source = ""
    for f in all_files:
        if f.is_file():
            try:
                combined_source += f.read_text(encoding="utf-8-sig") + "\n"
            except Exception:
                pass

    elements = _parse_element_blocks(combined_source)

    # --- Participant flow ---
    blocks_info = []
    trial_lookup = {}

    # Index trials
    for trial in elements.get("trial", []):
        trial_lookup[trial["name"].lower()] = trial

    # Parse experiment block order
    expt_blocks_order = []
    for expt in elements.get("expt", []):
        m = _EXPT_BLOCKS.search(expt["body"])
        if m:
            for entry in m.group(1).split(";"):
                entry = entry.strip()
                if "=" in entry:
                    _, name = entry.split("=", 1)
                    expt_blocks_order.append(name.strip().lower())
                elif entry:
                    expt_blocks_order.append(entry.strip().lower())

    # Parse each block
    block_lookup = {b["name"].lower(): b for b in elements.get("block", [])}
    total_trials = 0
    total_duration_ms = 0

    for block_name in expt_blocks_order:
        block = block_lookup.get(block_name)
        if not block:
            blocks_info.append({"name": block_name, "status": "not_found"})
            continue

        trial_count = _count_trials_in_block(block["body"])
        total_trials += trial_count

        # Estimate duration from trial types referenced
        avg_trial_ms = 3000  # Default
        m = _TRIAL_RANGE.search(block["body"])
        if m:
            trial_refs = re.findall(r"(?:\d+[-=])?(\w+)", m.group(1))
            durations = []
            for ref in trial_refs:
                trial = trial_lookup.get(ref.lower())
                if trial:
                    durations.append(_estimate_trial_duration_ms(trial["body"]))
            if durations:
                avg_trial_ms = sum(durations) / len(durations)

        block_duration_ms = trial_count * avg_trial_ms
        total_duration_ms += block_duration_ms

        blocks_info.append({
            "name": block_name,
            "trial_count": trial_count,
            "estimated_duration_seconds": round(block_duration_ms / 1000, 1),
        })

    # --- Response mapping ---
    response_map = {}
    for trial in elements.get("trial", []):
        keys = _extract_response_keys(trial["body"])
        if keys:
            records_data = not _RECORDDATA_FALSE.search(trial["body"])
            response_map[trial["name"]] = {**keys, "records_data": records_data}

    # --- Data schema prediction ---
    data_columns = [
        "date", "time", "group", "subject", "session",
        "blockcode", "blocknum", "trialcode", "trialnum",
        "response", "latency",
    ]
    has_accuracy = any(
        _CORRECTRESPONSE.search(t["body"]) for t in elements.get("trial", [])
    )
    if has_accuracy:
        data_columns.extend(["correct", "stimulusonset"])

    # Add custom values
    custom_values = []
    for val in elements.get("values", []):
        for line in val["body"].splitlines():
            vm = re.match(r'\s*/\s*(\w+)\s*=', line)
            if vm:
                custom_values.append(vm.group(1))

    # --- Stimuli inventory ---
    stimuli = {
        "text_elements": len(elements.get("text", [])),
        "picture_elements": len(elements.get("picture", [])),
        "sound_elements": len(elements.get("sound", [])),
        "video_elements": len(elements.get("video", [])),
        "lists": len(elements.get("list", [])),
        "survey_pages": len(elements.get("surveypage", [])),
    }

    # List item counts
    list_details = []
    for lst in elements.get("list", []):
        items_match = _LIST_ITEMS.search(lst["body"])
        item_count = 0
        if items_match:
            item_count = len(re.findall(r'"[^"]*"', items_match.group(1)))
        list_details.append({"name": lst["name"], "item_count": item_count})

    # --- Warnings ---
    warnings = []
    has_screencapture = bool(_SCREENCAPTURE.search(combined_source))
    if has_screencapture:
        warnings.append("screenCapture=true is still enabled in some trials (remove before delivery)")

    placeholder_count = len(re.findall(r"PLACEHOLDER", combined_source))
    if placeholder_count > 0:
        warnings.append(f"{placeholder_count} PLACEHOLDER values found — replace before deployment")

    return {
        "participant_flow": {
            "blocks": blocks_info,
            "total_blocks": len(blocks_info),
            "total_trials": total_trials,
            "estimated_duration_seconds": round(total_duration_ms / 1000, 1),
            "estimated_duration_minutes": round(total_duration_ms / 60000, 1),
        },
        "response_mapping": response_map,
        "data_schema": {
            "standard_columns": data_columns,
            "custom_values": custom_values,
            "has_accuracy_scoring": has_accuracy,
        },
        "stimuli_inventory": {
            "summary": stimuli,
            "lists": list_details,
        },
        "source_files": [str(f.name) for f in all_files if f.is_file()],
        "warnings": warnings,
    }
