"""Deep visual QA: content region detection and layout analysis for Inquisit screen captures.

Uses PIL edge detection and connected component labeling to find content regions,
then checks for overlap, small fonts, alignment issues. Produces per-capture element
inventories and text descriptions that an LLM can use to judge layout quality.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageFilter


@dataclass
class ElementRegion:
    bbox: tuple[int, int, int, int]  # (left, top, right, bottom)
    area: int
    center: tuple[int, int]
    estimated_type: str  # "text_line", "button", "block", "small_element"
    height_pct: float  # height as % of image height


# ---------------------------------------------------------------------------
# Union-Find (internal)
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        while self.parent.get(x, x) != x:
            self.parent[x] = self.parent.get(self.parent[x], self.parent[x])
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# ---------------------------------------------------------------------------
# Connected component labeling
# ---------------------------------------------------------------------------

def _connected_components(
    binary: list[list[bool]], width: int, height: int
) -> list[tuple[int, int, int, int]]:
    """Two-pass connected component labeling with union-find.

    Args:
        binary: 2-D grid (row-major) where True = foreground.
        width: Number of columns.
        height: Number of rows.

    Returns:
        List of bounding boxes ``(left, top, right, bottom)`` per component.
    """
    if not height or not width:
        return []

    uf = _UnionFind()
    labels: list[list[int]] = [[0] * width for _ in range(height)]
    next_label = 1

    # Pass 1 -- assign provisional labels
    for y in range(height):
        for x in range(width):
            if not binary[y][x]:
                continue

            left_label = labels[y][x - 1] if x > 0 and binary[y][x - 1] else 0
            above_label = labels[y - 1][x] if y > 0 and binary[y - 1][x] else 0

            if left_label == 0 and above_label == 0:
                labels[y][x] = next_label
                uf.parent[next_label] = next_label
                next_label += 1
            elif left_label != 0 and above_label == 0:
                labels[y][x] = left_label
            elif left_label == 0 and above_label != 0:
                labels[y][x] = above_label
            else:
                # Both neighbors have labels -- pick one and union
                labels[y][x] = left_label
                uf.union(left_label, above_label)

    # Pass 2 -- resolve labels and collect bounding boxes
    boxes: dict[int, list[int]] = {}  # root -> [min_x, min_y, max_x, max_y]

    for y in range(height):
        for x in range(width):
            lbl = labels[y][x]
            if lbl == 0:
                continue
            root = uf.find(lbl)
            labels[y][x] = root
            if root not in boxes:
                boxes[root] = [x, y, x, y]
            else:
                b = boxes[root]
                if x < b[0]:
                    b[0] = x
                if y < b[1]:
                    b[1] = y
                if x > b[2]:
                    b[2] = x
                if y > b[3]:
                    b[3] = y

    return [(b[0], b[1], b[2], b[3]) for b in boxes.values()]


# ---------------------------------------------------------------------------
# Region detection
# ---------------------------------------------------------------------------

def detect_content_regions(img: Image.Image) -> list[ElementRegion]:
    """Detect content regions in an image via edge detection and component labeling.

    Steps:
        1. Convert to grayscale
        2. Apply edge detection filter
        3. Binarize (pixel > 30 = foreground)
        4. Downsample to ~480px width for performance
        5. Connected component labeling
        6. Filter noise (area < 100px at downsampled scale)
        7. Scale bounding boxes back to original resolution
        8. Classify by aspect ratio

    Returns:
        List of ElementRegion sorted top-to-bottom.
    """
    orig_w, orig_h = img.size

    # 1-2: grayscale + edge detection
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)

    # 3-4: downsample for performance
    target_w = 480
    if orig_w > target_w:
        scale = target_w / orig_w
        ds_w = target_w
        ds_h = max(1, int(orig_h * scale))
        edges_ds = edges.resize((ds_w, ds_h), Image.NEAREST)
    else:
        scale = 1.0
        ds_w, ds_h = orig_w, orig_h
        edges_ds = edges

    # Binarize
    pixels = edges_ds.load()
    binary: list[list[bool]] = []
    for y in range(ds_h):
        row: list[bool] = []
        for x in range(ds_w):
            row.append(pixels[x, y] > 30)
        binary.append(row)

    # 5: connected components
    raw_boxes = _connected_components(binary, ds_w, ds_h)

    # 6: filter noise and full-frame artifacts
    min_area = 100
    max_area_pct = 0.90  # ignore regions covering >90% of downsampled image
    ds_total = ds_w * ds_h
    filtered: list[tuple[int, int, int, int]] = []
    for left, top, right, bottom in raw_boxes:
        w = right - left + 1
        h = bottom - top + 1
        area = w * h
        if area < min_area:
            continue
        if ds_total > 0 and area > ds_total * max_area_pct:
            continue  # skip border/full-frame artifacts
        filtered.append((left, top, right, bottom))

    # 7: scale back to original resolution
    inv_scale = 1.0 / scale
    regions: list[ElementRegion] = []
    for left, top, right, bottom in filtered:
        o_left = int(left * inv_scale)
        o_top = int(top * inv_scale)
        o_right = min(int(right * inv_scale), orig_w - 1)
        o_bottom = min(int(bottom * inv_scale), orig_h - 1)

        w = o_right - o_left + 1
        h = o_bottom - o_top + 1
        area = w * h
        cx = o_left + w // 2
        cy = o_top + h // 2
        height_pct = (h / orig_h) * 100.0 if orig_h > 0 else 0.0

        # 8: classify
        if area < 500:
            etype = "small_element"
        elif w / h > 3:
            etype = "text_line"
        elif w / h > 1.5:
            etype = "button"
        else:
            etype = "block"

        regions.append(ElementRegion(
            bbox=(o_left, o_top, o_right, o_bottom),
            area=area,
            center=(cx, cy),
            estimated_type=etype,
            height_pct=round(height_pct, 2),
        ))

    # Sort top to bottom, then left to right
    regions.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
    return regions


# ---------------------------------------------------------------------------
# Issue detectors
# ---------------------------------------------------------------------------

def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    """Compute pixel area of intersection between two (left, top, right, bottom) boxes."""
    ix_left = max(a[0], b[0])
    iy_top = max(a[1], b[1])
    ix_right = min(a[2], b[2])
    iy_bottom = min(a[3], b[3])
    if ix_right <= ix_left or iy_bottom <= iy_top:
        return 0
    return (ix_right - ix_left) * (iy_bottom - iy_top)


def detect_overlap(regions: list[ElementRegion]) -> list[dict]:
    """Detect pairs of regions with significant overlap.

    Flags overlap when the intersection exceeds 10% of the smaller region's area.

    Returns:
        List of issue dicts with keys: issue_type, severity, description, regions.
    """
    issues: list[dict] = []
    n = len(regions)
    for i in range(n):
        for j in range(i + 1, n):
            inter = _intersection_area(regions[i].bbox, regions[j].bbox)
            if inter == 0:
                continue
            smaller_area = min(regions[i].area, regions[j].area)
            if smaller_area == 0:
                continue
            overlap_pct = inter / smaller_area
            if overlap_pct > 0.10:
                severity = "high" if overlap_pct > 0.50 else "medium"
                issues.append({
                    "issue_type": "overlap",
                    "severity": severity,
                    "description": (
                        f"Regions {i} and {j} overlap by {overlap_pct:.0%} "
                        f"of the smaller region's area."
                    ),
                    "regions": [i, j],
                })
    return issues


def detect_font_too_small(
    regions: list[ElementRegion], img_height: int
) -> list[dict]:
    """Flag text_line regions whose height is less than 1.5% of image height.

    Returns:
        List of issue dicts with keys: issue_type, severity, description, region_index.
    """
    issues: list[dict] = []
    for idx, r in enumerate(regions):
        if r.estimated_type != "text_line":
            continue
        if r.height_pct < 1.0:
            issues.append({
                "issue_type": "font_too_small",
                "severity": "high",
                "description": (
                    f"Region {idx} (text_line) height is {r.height_pct:.1f}% of "
                    f"image height ({img_height}px) -- likely unreadable."
                ),
                "region_index": idx,
            })
        elif r.height_pct < 1.5:
            issues.append({
                "issue_type": "font_too_small",
                "severity": "medium",
                "description": (
                    f"Region {idx} (text_line) height is {r.height_pct:.1f}% of "
                    f"image height ({img_height}px) -- may be hard to read."
                ),
                "region_index": idx,
            })
    return issues


def detect_alignment_inconsistent(
    regions: list[ElementRegion], img_width: int
) -> list[dict]:
    """Check for inconsistent left-edge alignment among vertically grouped regions.

    Groups regions whose X-centers are within 3% of image width.  For groups of
    3+ members, flags if left edges differ by more than 2% of image width.

    Returns:
        List of issue dicts with keys: issue_type, severity, description.
    """
    if img_width == 0 or len(regions) < 3:
        return []

    center_tol = img_width * 0.03
    edge_tol = img_width * 0.02

    # Group by X-center proximity (greedy clustering)
    used: set[int] = set()
    groups: list[list[int]] = []

    for i, ri in enumerate(regions):
        if i in used:
            continue
        group = [i]
        used.add(i)
        for j in range(i + 1, len(regions)):
            if j in used:
                continue
            if abs(ri.center[0] - regions[j].center[0]) <= center_tol:
                group.append(j)
                used.add(j)
        if len(group) >= 3:
            groups.append(group)

    issues: list[dict] = []
    for group in groups:
        lefts = [regions[idx].bbox[0] for idx in group]
        min_left = min(lefts)
        max_left = max(lefts)
        if max_left - min_left > edge_tol:
            issues.append({
                "issue_type": "alignment_inconsistent",
                "severity": "medium",
                "description": (
                    f"Column of {len(group)} elements has left-edge spread of "
                    f"{max_left - min_left}px (tolerance {edge_tol:.0f}px)."
                ),
            })
    return issues


# ---------------------------------------------------------------------------
# Layout description (for LLM reasoning)
# ---------------------------------------------------------------------------

def generate_layout_description(
    regions: list[ElementRegion], img_size: tuple[int, int]
) -> str:
    """Generate a human-readable text summary of the detected layout.

    Describes: count, spatial distribution, centering, and density.
    """
    w, h = img_size
    n = len(regions)

    if n == 0:
        return "No content regions detected. The image appears blank or uniform."

    parts: list[str] = [f"{n} content region{'s' if n != 1 else ''} detected."]

    # Spatial distribution by vertical thirds
    upper = [r for r in regions if r.center[1] < h / 3]
    middle = [r for r in regions if h / 3 <= r.center[1] < 2 * h / 3]
    lower = [r for r in regions if r.center[1] >= 2 * h / 3]

    dist_parts: list[str] = []
    if upper:
        types_upper = _summarize_types(upper)
        dist_parts.append(f"{len(upper)} {types_upper} in upper third")
    if middle:
        types_mid = _summarize_types(middle)
        dist_parts.append(f"{len(middle)} {types_mid} in middle third")
    if lower:
        types_lower = _summarize_types(lower)
        dist_parts.append(f"{len(lower)} {types_lower} in lower third")
    if dist_parts:
        parts.append("Spatial distribution: " + ", ".join(dist_parts) + ".")

    # Centering analysis
    if w > 0:
        center_x = w / 2
        tol = w * 0.15
        centered = [r for r in regions if abs(r.center[0] - center_x) <= tol]
        left_aligned = [r for r in regions if r.center[0] < w * 0.35]
        right_aligned = [r for r in regions if r.center[0] > w * 0.65]

        if len(centered) > n * 0.7:
            parts.append("Content is predominantly centered.")
        elif len(left_aligned) > n * 0.7:
            parts.append("Content is predominantly left-aligned.")
        elif len(right_aligned) > n * 0.7:
            parts.append("Content is predominantly right-aligned.")
        else:
            parts.append("Content is distributed across the horizontal extent.")

    # Density
    total_region_area = sum(r.area for r in regions)
    img_area = w * h if w * h > 0 else 1
    fill = total_region_area / img_area
    if fill < 0.10:
        parts.append("Sparse display with ample whitespace.")
    elif fill < 0.40:
        parts.append("Moderate content density.")
    else:
        parts.append("Dense layout with limited whitespace.")

    return " ".join(parts)


def _summarize_types(regions: list[ElementRegion]) -> str:
    """Summarize region types for a group, e.g. 'elements (2 text lines, 1 block)'."""
    counts: dict[str, int] = {}
    for r in regions:
        counts[r.estimated_type] = counts.get(r.estimated_type, 0) + 1
    if len(counts) == 1:
        etype, cnt = next(iter(counts.items()))
        label = etype.replace("_", " ") + ("s" if cnt > 1 else "")
        return label
    type_strs = []
    for etype, cnt in sorted(counts.items()):
        label = etype.replace("_", " ") + ("s" if cnt > 1 else "")
        type_strs.append(f"{cnt} {label}")
    return "elements (" + ", ".join(type_strs) + ")"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def score_layout_deep(
    image_paths: list[Path],
    purpose_hint: str | None = None,
) -> list[dict]:
    """Analyse screen captures for deep layout quality.

    For each image: detect content regions, run issue detectors, produce a
    text description suitable for LLM reasoning.

    Args:
        image_paths: Paths to PNG/BMP capture files.
        purpose_hint: Optional description of what the screen should show
            (reserved for future use).

    Returns:
        List of result dicts, one per image.
    """
    results: list[dict] = []

    for p in image_paths:
        try:
            img = Image.open(p)
            w, h = img.size

            regions = detect_content_regions(img)

            # Collect technical issues from all detectors
            tech_issues: list[dict] = []
            tech_issues.extend(detect_overlap(regions))
            tech_issues.extend(detect_font_too_small(regions, h))
            tech_issues.extend(detect_alignment_inconsistent(regions, w))

            description = generate_layout_description(regions, (w, h))

            results.append({
                "path": str(p),
                "image_size": [w, h],
                "regions_detected": len(regions),
                "region_inventory": [asdict(r) for r in regions],
                "technical_issues": tech_issues,
                "layout_description": description,
                "error": None,
            })

        except Exception as e:
            results.append({
                "path": str(p),
                "image_size": None,
                "regions_detected": 0,
                "region_inventory": [],
                "technical_issues": [],
                "layout_description": "",
                "error": str(e),
            })

    return results
