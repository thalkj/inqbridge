"""Runner configuration and constants."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _discover_inquisit_exe() -> Path:
    """Find the Inquisit executable: local.json > auto-scan > hardcoded default."""
    # 1) Read from local.json if it exists
    local_cfg = PROJECT_ROOT / "local.json"
    if local_cfg.is_file():
        try:
            data = json.loads(local_cfg.read_text(encoding="utf-8"))
            exe_str = data.get("inquisit_exe")
            if exe_str:
                return Path(exe_str)
        except (json.JSONDecodeError, KeyError):
            pass

    # 2) Auto-scan common install location
    search_base = Path(r"C:\Program Files\Millisecond Software")
    if search_base.is_dir():
        candidates = sorted(search_base.glob("Inquisit*/Inquisit.exe"), reverse=True)
        if candidates:
            return candidates[0]

    # 3) Hardcoded fallback
    return Path(r"C:\Program Files\Millisecond Software\Inquisit 6\Inquisit.exe")


INQUISIT_EXE = _discover_inquisit_exe()
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
INCLUDES_DIR = PROJECT_ROOT / "includes"
MEDIA_DIR = PROJECT_ROOT / "media"

ALLOWED_MODES = ("human", "monkey")
