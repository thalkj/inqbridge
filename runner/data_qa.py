"""Data QA: parse .iqdat files and produce per-trialcode qualitative profiles."""
import csv
import re
import statistics
from pathlib import Path


def parse_iqdat(path: Path) -> tuple[list[str], list[dict]]:
    """Parse a tab-separated .iqdat file.

    Args:
        path: Path to the .iqdat file.

    Returns:
        Tuple of (column_names, rows) where rows are list of dicts.
    """
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return ([], [])

    lines = text.splitlines()
    if not lines:
        return ([], [])

    reader = csv.DictReader(lines, delimiter="\t")
    fieldnames = list(reader.fieldnames) if reader.fieldnames else []
    rows = list(reader)
    return (fieldnames, rows)


def parse_script_context(script_source: str | None) -> dict:
    """Extract trial metadata from .iqx script source text.

    Looks for validresponse, correctresponse, list elements, and surveypages.

    Args:
        script_source: Raw text of an .iqx file, or None.

    Returns:
        Dict with 'trials', 'has_surveys', and 'lists_found' keys.
    """
    if not script_source:
        return {"trials": {}, "has_surveys": False, "lists_found": []}

    trials: dict[str, dict] = {}
    has_surveys = False
    lists_found: list[str] = []

    # Find <list NAME> elements
    for m in re.finditer(r"<list\s+(\w+)\s*>", script_source, re.IGNORECASE):
        lists_found.append(m.group(1))

    # Detect <surveypage ...>
    if re.search(r"<surveypage\s+\w+", script_source, re.IGNORECASE):
        has_surveys = True

    # Find <trial NAME> ... </trial> blocks
    trial_pattern = re.compile(
        r"<trial\s+(\w+)\s*>(.*?)</trial>", re.IGNORECASE | re.DOTALL
    )
    for m in trial_pattern.finditer(script_source):
        trial_name = m.group(1).lower()
        body = m.group(2)

        # Extract validresponse values
        valid_responses: list[str] = []
        vr_match = re.search(
            r"/\s*validresponse\s*=\s*\(([^)]*)\)", body, re.IGNORECASE
        )
        if vr_match:
            raw = vr_match.group(1)
            valid_responses = [
                v.strip().strip('"').strip("'")
                for v in raw.split(",")
                if v.strip().strip('"').strip("'")
            ]

        # Check for correctresponse
        has_cr = bool(
            re.search(r"/\s*correctresponse\s*=", body, re.IGNORECASE)
        )

        # Check if trial uses a list-based stimulus (stimulusframes referencing
        # a text that itself uses a list, or the trial body referencing list.)
        uses_list = bool(
            re.search(r"\blist\.\w+", body, re.IGNORECASE)
        )

        trials[trial_name] = {
            "validresponse": valid_responses,
            "has_correctresponse": has_cr,
            "uses_list": uses_list,
        }

    return {
        "trials": trials,
        "has_surveys": has_surveys,
        "lists_found": lists_found,
    }


def profile_trialcode(
    trialcode: str,
    rows: list[dict],
    script_context: dict,
) -> dict:
    """Build a qualitative profile for all rows matching a trialcode.

    Args:
        trialcode: The trialcode value to filter on.
        rows: All data rows (from parse_iqdat).
        script_context: Output of parse_script_context.

    Returns:
        Dict with summary statistics and context-aware flags.
    """
    matching = [r for r in rows if r.get("trialcode") == trialcode]
    flags: list[str] = []

    trial_count = len(matching)
    if trial_count == 0:
        flags.append("no data rows")
        return {
            "trialcode": trialcode,
            "trial_count": 0,
            "response_summary": {
                "unique_responses": 0,
                "distribution": {},
                "all_same": True,
            },
            "latency_summary": {
                "mean": 0, "median": 0, "stdev": 0,
                "min": 0, "max": 0, "zero_count": 0,
            },
            "accuracy_summary": None,
            "stimulus_summary": {
                "unique_items": 0, "all_same": True, "sample_items": [],
            },
            "onset_summary": {"all_valid": True, "negative_count": 0},
            "flags": flags,
            "script_context": _trial_context(trialcode, script_context),
        }

    # --- Response summary ---
    responses = [r.get("response", "") for r in matching]
    response_dist: dict[str, int] = {}
    for resp in responses:
        response_dist[resp] = response_dist.get(resp, 0) + 1
    unique_responses = len(response_dist)
    all_same_response = unique_responses <= 1

    response_summary = {
        "unique_responses": unique_responses,
        "distribution": response_dist,
        "all_same": all_same_response,
    }

    # --- Latency summary ---
    latencies: list[float] = []
    for r in matching:
        raw = r.get("latency", "")
        if raw != "":
            try:
                latencies.append(float(raw))
            except (ValueError, TypeError):
                pass

    if latencies:
        lat_mean = statistics.mean(latencies)
        lat_median = statistics.median(latencies)
        lat_stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        lat_min = min(latencies)
        lat_max = max(latencies)
        zero_count = sum(1 for v in latencies if v == 0)
    else:
        lat_mean = lat_median = lat_stdev = lat_min = lat_max = 0.0
        zero_count = 0

    latency_summary = {
        "mean": round(lat_mean, 1),
        "median": round(lat_median, 1),
        "stdev": round(lat_stdev, 1),
        "min": lat_min,
        "max": lat_max,
        "zero_count": zero_count,
    }

    # --- Accuracy summary ---
    correct_vals = [r.get("correct", "") for r in matching]
    has_accuracy = any(v != "" for v in correct_vals)
    accuracy_summary = None
    if has_accuracy:
        correct_count = sum(1 for v in correct_vals if v == "1")
        incorrect_count = sum(1 for v in correct_vals if v == "0")
        total_judged = correct_count + incorrect_count
        rate = correct_count / total_judged if total_judged > 0 else 0.0
        accuracy_summary = {
            "correct": correct_count,
            "incorrect": incorrect_count,
            "rate": round(rate, 2),
        }

    # --- Stimulus summary ---
    stim_items = [r.get("stimulusitem1", "") for r in matching]
    unique_stim = list(dict.fromkeys(s for s in stim_items if s))
    stim_all_same = len(unique_stim) <= 1

    stimulus_summary = {
        "unique_items": len(unique_stim),
        "all_same": stim_all_same,
        "sample_items": unique_stim[:3],
    }

    # --- Onset summary ---
    onsets: list[float] = []
    for r in matching:
        raw = r.get("stimulusonset1", "")
        if raw != "":
            try:
                onsets.append(float(raw))
            except (ValueError, TypeError):
                pass
    negative_count = sum(1 for v in onsets if v < 0)
    onset_summary = {
        "all_valid": negative_count == 0,
        "negative_count": negative_count,
    }

    # --- Context-aware flags ---
    tc = _trial_context(trialcode, script_context)
    expected = tc.get("expected_responses", [])

    # Flag: all same response when multiple valid responses exist
    if all_same_response and len(expected) > 1:
        only_resp = list(response_dist.keys())[0] if response_dist else "?"
        flags.append(
            f"all responses identical ({only_resp}) but script expects "
            f"multiple keys {expected}"
        )

    # Flag: all same stimulus when list is used
    uses_list = tc.get("uses_stimulus_list", False)
    if stim_all_same and uses_list and len(unique_stim) > 0:
        flags.append(
            f"all stimuli identical ('{unique_stim[0]}') but script uses a "
            f"stimulus list"
        )

    # Flag: near-chance accuracy (informational)
    if accuracy_summary and len(expected) >= 2:
        chance = 1.0 / len(expected)
        if abs(accuracy_summary["rate"] - chance) <= 0.15:
            flags.append(
                f"near-chance accuracy ({accuracy_summary['rate']}) "
                f"— expected for monkey on {len(expected)}-choice task"
            )

    # Flag: all latencies zero (problem)
    if latencies and all(v == 0 for v in latencies):
        flags.append("all latencies zero — stimuli may not have displayed")

    return {
        "trialcode": trialcode,
        "trial_count": trial_count,
        "response_summary": response_summary,
        "latency_summary": latency_summary,
        "accuracy_summary": accuracy_summary,
        "stimulus_summary": stimulus_summary,
        "onset_summary": onset_summary,
        "flags": flags,
        "script_context": tc,
    }


def _trial_context(trialcode: str, script_context: dict) -> dict:
    """Extract per-trial context from the full script context."""
    trials = script_context.get("trials", {})
    tc_lower = trialcode.lower()
    info = trials.get(tc_lower, {})
    return {
        "has_correct_response": info.get("has_correctresponse", False),
        "expected_responses": info.get("validresponse", []),
        "uses_stimulus_list": info.get("uses_list", False),
    }


def assess_monkey_data(
    run_id: str,
    data_dir: Path,
    source_dir: Path | None = None,
) -> dict:
    """Assess monkey-run data quality across all .iqdat files.

    Args:
        run_id: Identifier for this run.
        data_dir: Directory containing .iqdat files.
        source_dir: Optional directory containing .iqx source files.

    Returns:
        Full report dict with per-trialcode profiles and overall flags.
    """
    # Collect .iqdat files
    iqdat_files = sorted(data_dir.glob("*.iqdat"))
    data_files = [str(p) for p in iqdat_files]

    # Parse all data
    all_rows: list[dict] = []
    all_columns: list[str] = []
    for f in iqdat_files:
        cols, rows = parse_iqdat(f)
        if cols and not all_columns:
            all_columns = cols
        all_rows.extend(rows)

    # Parse script context if source available
    script_context: dict = {"trials": {}, "has_surveys": False, "lists_found": []}
    if source_dir and source_dir.is_dir():
        iqx_files = sorted(source_dir.glob("*.iqx"))
        combined_source = ""
        for iqx in iqx_files:
            try:
                combined_source += iqx.read_text(encoding="utf-8-sig") + "\n"
            except Exception:
                pass
        if combined_source:
            script_context = parse_script_context(combined_source)

    # Group rows by trialcode
    trialcodes: list[str] = []
    seen: set[str] = set()
    for r in all_rows:
        tc = r.get("trialcode", "")
        if tc and tc not in seen:
            trialcodes.append(tc)
            seen.add(tc)

    # Profile each trialcode
    profiles = [
        profile_trialcode(tc, all_rows, script_context)
        for tc in trialcodes
    ]

    # Overall flags
    overall_flags: list[str] = []
    if not all_rows:
        overall_flags.append("no data rows found in any .iqdat file")
    if not iqdat_files:
        overall_flags.append("no .iqdat files found in data directory")

    # Check for trialcodes with no data
    empty_profiles = [p for p in profiles if p["trial_count"] == 0]
    if empty_profiles:
        names = [p["trialcode"] for p in empty_profiles]
        overall_flags.append(f"trialcodes with no data: {names}")

    # Check if any trialcode had all-zero latencies
    zero_lat_profiles = [
        p for p in profiles
        if p["trial_count"] > 0
        and p["latency_summary"]["zero_count"] == p["trial_count"]
    ]
    if zero_lat_profiles:
        names = [p["trialcode"] for p in zero_lat_profiles]
        overall_flags.append(f"trialcodes with all-zero latencies: {names}")

    return {
        "run_id": run_id,
        "data_files": data_files,
        "total_rows": len(all_rows),
        "trialcode_profiles": profiles,
        "overall_flags": overall_flags,
    }
