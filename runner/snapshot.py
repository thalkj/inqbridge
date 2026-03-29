"""Source snapshot: copy and hash executed scripts for traceability."""
import hashlib
import shutil
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_sources(
    main_script: Path,
    includes: list[Path],
    dest_dir: Path,
) -> list[dict]:
    """Copy the main script and all includes into dest_dir/source/, recording hashes.

    Args:
        main_script: Path to the main .iqx file.
        includes: List of resolved include file paths.
        dest_dir: The run artifact directory.

    Returns:
        List of dicts with 'path' (relative to dest_dir) and 'sha256' keys.
    """
    source_dir = dest_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []

    # Copy main script
    dst = source_dir / main_script.name
    shutil.copy2(main_script, dst)
    rel = f"source/{main_script.name}"
    manifest_entries.append({"path": rel, "sha256": sha256_file(dst)})

    # Copy includes
    for inc in includes:
        dst = source_dir / inc.name
        if dst.exists():
            # Avoid name collisions by prefixing parent dir name
            dst = source_dir / f"{inc.parent.name}_{inc.name}"
        shutil.copy2(inc, dst)
        rel = f"source/{dst.name}"
        manifest_entries.append({"path": rel, "sha256": sha256_file(dst)})

    return manifest_entries
