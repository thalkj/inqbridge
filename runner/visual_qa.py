"""Visual QA: screen capture deduplication and layout scoring."""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    from PIL import Image
    import imagehash
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False


@dataclass
class LayoutIssue:
    issue_type: str  # text_clipped, low_contrast, crowding, overlap, font_too_small, alignment_inconsistent
    severity: str    # low, medium, high
    description: str
    region: tuple[int, int, int, int] | None = None  # (x, y, w, h)


@dataclass
class CaptureEntry:
    original_path: str
    kept_path: str
    file_hash: str
    perceptual_hash: str | None = None
    is_duplicate: bool = False
    duplicate_of: str | None = None


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _perceptual_hash(path: Path) -> str | None:
    if not HAS_IMAGING:
        return None
    try:
        img = Image.open(path)
        return str(imagehash.phash(img))
    except Exception:
        return None


def deduplicate_captures(
    capture_paths: list[Path],
    hamming_threshold: int = 5,
) -> list[CaptureEntry]:
    """Deduplicate screen captures using file hash and perceptual hash.

    Args:
        capture_paths: List of paths to capture image files.
        hamming_threshold: Max hamming distance for perceptual hash similarity.

    Returns:
        List of CaptureEntry with duplicate flags.
    """
    entries: list[CaptureEntry] = []
    seen_hashes: dict[str, str] = {}  # file_hash -> first path
    seen_phashes: list[tuple[str, str]] = []  # (phash_hex, path)

    for p in capture_paths:
        fhash = _file_sha256(p)
        phash = _perceptual_hash(p)

        entry = CaptureEntry(
            original_path=str(p),
            kept_path=str(p),
            file_hash=fhash,
            perceptual_hash=phash,
        )

        # Exact duplicate check
        if fhash in seen_hashes:
            entry.is_duplicate = True
            entry.duplicate_of = seen_hashes[fhash]
            entries.append(entry)
            continue

        # Perceptual duplicate check
        if phash and HAS_IMAGING:
            for existing_phash, existing_path in seen_phashes:
                try:
                    dist = imagehash.hex_to_hash(phash) - imagehash.hex_to_hash(existing_phash)
                    if dist <= hamming_threshold:
                        entry.is_duplicate = True
                        entry.duplicate_of = existing_path
                        break
                except Exception:
                    pass

        if not entry.is_duplicate:
            seen_hashes[fhash] = str(p)
            if phash:
                seen_phashes.append((phash, str(p)))

        entries.append(entry)

    return entries


def write_capture_index(
    entries: list[CaptureEntry],
    run_id: str,
    output_dir: Path,
) -> Path:
    """Write capture_index.json linking kept images to run context.

    Returns:
        Path to the written index file.
    """
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    index = {
        "run_id": run_id,
        "total_captures": len(entries),
        "unique_captures": sum(1 for e in entries if not e.is_duplicate),
        "duplicates": sum(1 for e in entries if e.is_duplicate),
        "entries": [
            {
                "original_path": e.original_path,
                "kept_path": e.kept_path,
                "file_hash": e.file_hash,
                "perceptual_hash": e.perceptual_hash,
                "is_duplicate": e.is_duplicate,
                "duplicate_of": e.duplicate_of,
            }
            for e in entries
        ],
    }

    index_path = analysis_dir / "capture_index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index_path


def score_layout(image_paths: list[Path]) -> list[dict]:
    """Score layout quality from screen captures.

    Analyzes images for common layout issues. Requires Pillow.

    Args:
        image_paths: Paths to capture images to analyze.

    Returns:
        List of dicts, one per image, with 'path', 'issues', and 'score' keys.
    """
    if not HAS_IMAGING:
        return [{"path": str(p), "issues": [], "score": None, "error": "Pillow not installed"} for p in image_paths]

    results = []
    for p in image_paths:
        issues: list[dict] = []
        try:
            img = Image.open(p)
            width, height = img.size
            pixels = img.convert("RGB")

            # Check 1: Very small image (likely clipped or wrong resolution)
            if width < 200 or height < 150:
                issues.append({
                    "issue_type": "text_clipped",
                    "severity": "high",
                    "description": f"Image very small ({width}x{height}), content may be clipped.",
                })

            # Check 2: Low contrast - sample center region
            cx, cy = width // 2, height // 2
            region_size = min(100, width // 4, height // 4)
            if region_size > 10:
                box = (cx - region_size, cy - region_size, cx + region_size, cy + region_size)
                center = pixels.crop(box)
                center_data = list(center.getdata())
                if center_data:
                    lums = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in center_data]
                    min_l, max_l = min(lums), max(lums)
                    contrast = max_l - min_l
                    if contrast < 30:
                        issues.append({
                            "issue_type": "low_contrast",
                            "severity": "medium",
                            "description": f"Low contrast in center region (range: {contrast:.0f}/255).",
                        })

            # Check 3: Edge content (potential clipping)
            # Check if there's non-background content touching edges
            edge_pixels_top = [pixels.getpixel((x, 0)) for x in range(0, width, max(1, width // 20))]
            edge_pixels_bottom = [pixels.getpixel((x, height - 1)) for x in range(0, width, max(1, width // 20))]
            bg_color = pixels.getpixel((0, 0))
            non_bg_top = sum(1 for p in edge_pixels_top if p != bg_color)
            non_bg_bottom = sum(1 for p in edge_pixels_bottom if p != bg_color)
            if non_bg_top > len(edge_pixels_top) * 0.3:
                issues.append({
                    "issue_type": "text_clipped",
                    "severity": "medium",
                    "description": "Content detected at top edge, may be clipped.",
                })
            if non_bg_bottom > len(edge_pixels_bottom) * 0.3:
                issues.append({
                    "issue_type": "text_clipped",
                    "severity": "medium",
                    "description": "Content detected at bottom edge, may be clipped.",
                })

            # Check 4: Crowding heuristic - ratio of non-background pixels
            total_pixels = width * height
            sample_step = max(1, total_pixels // 10000)
            all_data = list(pixels.getdata())
            sampled = all_data[::sample_step]
            non_bg = sum(1 for p in sampled if p != bg_color)
            fill_ratio = non_bg / len(sampled) if sampled else 0
            if fill_ratio > 0.85:
                issues.append({
                    "issue_type": "crowding",
                    "severity": "medium",
                    "description": f"High content density ({fill_ratio:.0%} non-background), may be crowded.",
                })

            # Score: 100 minus penalties
            penalty = sum(30 if i["severity"] == "high" else 15 if i["severity"] == "medium" else 5 for i in issues)
            score = max(0, 100 - penalty)

            results.append({"path": str(p), "issues": issues, "score": score})

        except Exception as e:
            results.append({"path": str(p), "issues": [], "score": None, "error": str(e)})

    return results
