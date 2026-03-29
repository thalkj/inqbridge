"""Collect Inquisit output artifacts (data files, screen captures)."""
import shutil
from pathlib import Path


def collect_data_files(
    script_dir: Path,
    run_dir: Path,
    script_name: str | None = None,
) -> list[str]:
    """Copy data files from script's data/ folder into run_dir/data/.

    Inquisit writes raw and summary data files into a data/ subfolder
    relative to the script location.

    Args:
        script_dir: Directory containing the executed script.
        run_dir: Target directory for collected artifacts.
        script_name: If provided, only collect files whose names contain this
            stem (case-insensitive). Prevents collecting stale data from
            previous runs of different scripts in the same directory.

    Returns:
        List of relative paths (from run_dir) of collected files.
    """
    data_src = script_dir / "data"
    if not data_src.is_dir():
        return []

    data_dst = run_dir / "data"
    data_dst.mkdir(parents=True, exist_ok=True)

    # Build a filter if script_name is provided
    stem_lower = script_name.lower().replace(" ", "").replace("-", "").replace("_", "") if script_name else None

    collected = []
    for f in data_src.iterdir():
        if not f.is_file():
            continue
        # Filter out stale data from other scripts
        if stem_lower:
            fname_lower = f.name.lower().replace(" ", "").replace("-", "").replace("_", "")
            if stem_lower not in fname_lower:
                continue
        dst = data_dst / f.name
        shutil.copy2(f, dst)
        collected.append(f"data/{f.name}")
    return collected


def collect_screen_captures(script_dir: Path, run_dir: Path) -> list[str]:
    """Copy screen captures from script's screencaptures/ or data/screencaptures/ folder.

    Inquisit 6 writes .png files when screenCapture=true on elements.
    The captures may be in screencaptures/ or data/screencaptures/ relative to the script.

    Returns:
        List of relative paths (from run_dir) of collected captures.
    """
    # Inquisit 6 puts captures under data/screencaptures/
    cap_src = script_dir / "data" / "screencaptures"
    if not cap_src.is_dir():
        # Fall back to screencaptures/ directly
        cap_src = script_dir / "screencaptures"
    if not cap_src.is_dir():
        return []

    cap_dst = run_dir / "screencaptures"
    cap_dst.mkdir(parents=True, exist_ok=True)

    collected = []
    for f in cap_src.iterdir():
        if f.is_file() and f.suffix.lower() in (".bmp", ".png", ".jpg"):
            dst = cap_dst / f.name
            shutil.copy2(f, dst)
            collected.append(f"screencaptures/{f.name}")
    return collected
