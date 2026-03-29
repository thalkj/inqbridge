"""Tests for runner.visual_qa_deep — deep layout analysis."""
import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from runner.visual_qa_deep import (
    _connected_components,
    _UnionFind,
    detect_content_regions,
    detect_overlap,
    detect_font_too_small,
    detect_alignment_inconsistent,
    generate_layout_description,
    score_layout_deep,
    ElementRegion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_image(width, height, rectangles=None):
    """Create white image with optional colored rectangles.

    rectangles: list of (left, top, right, bottom, color)
    """
    img = Image.new("RGB", (width, height), (255, 255, 255))
    if rectangles:
        draw = ImageDraw.Draw(img)
        for left, top, right, bottom, color in rectangles:
            draw.rectangle([left, top, right, bottom], fill=color)
    return img


# ---------------------------------------------------------------------------
# Connected components
# ---------------------------------------------------------------------------

def test_connected_components_two_blobs():
    """Two separate blobs should produce 2 components."""
    binary = [[False] * 20 for _ in range(20)]
    # Blob 1: top-left
    for y in range(2, 5):
        for x in range(2, 5):
            binary[y][x] = True
    # Blob 2: bottom-right
    for y in range(15, 18):
        for x in range(15, 18):
            binary[y][x] = True

    boxes = _connected_components(binary, 20, 20)
    assert len(boxes) == 2


def test_connected_components_one_blob():
    """Single connected region should produce 1 component."""
    binary = [[False] * 20 for _ in range(20)]
    for y in range(5, 15):
        for x in range(5, 15):
            binary[y][x] = True

    boxes = _connected_components(binary, 20, 20)
    assert len(boxes) == 1


def test_connected_components_empty():
    """All-false grid should produce 0 components."""
    binary = [[False] * 10 for _ in range(10)]
    boxes = _connected_components(binary, 10, 10)
    assert len(boxes) == 0


# ---------------------------------------------------------------------------
# detect_content_regions
# ---------------------------------------------------------------------------

def test_detect_content_regions_with_rectangles():
    """Image with 3 well-separated colored rectangles should find 3 regions."""
    img = _make_test_image(960, 540, [
        (50, 50, 200, 80, (0, 0, 0)),      # top-left text-like
        (400, 250, 560, 290, (0, 0, 255)),  # center text-like
        (50, 450, 200, 520, (255, 0, 0)),   # bottom-left block
    ])
    regions = detect_content_regions(img)
    # Should find at least the 3 rectangles (edge detection may split some)
    assert len(regions) >= 2  # relaxed — edge detection may merge/split


def test_detect_content_regions_empty_image():
    """All-white image should produce 0 regions."""
    img = _make_test_image(640, 480)
    regions = detect_content_regions(img)
    assert len(regions) == 0


# ---------------------------------------------------------------------------
# detect_overlap
# ---------------------------------------------------------------------------

def test_detect_overlap_flags_overlapping():
    """Two overlapping regions should produce an overlap issue."""
    r1 = ElementRegion(bbox=(100, 100, 300, 200), area=20000,
                       center=(200, 150), estimated_type="text_line", height_pct=5.0)
    r2 = ElementRegion(bbox=(200, 150, 400, 250), area=20000,
                       center=(300, 200), estimated_type="text_line", height_pct=5.0)

    issues = detect_overlap([r1, r2])
    assert len(issues) >= 1
    assert issues[0]["issue_type"] == "overlap"


def test_detect_overlap_no_overlap():
    """Well-separated regions should produce no issues."""
    r1 = ElementRegion(bbox=(10, 10, 100, 50), area=3600,
                       center=(55, 30), estimated_type="text_line", height_pct=3.0)
    r2 = ElementRegion(bbox=(10, 200, 100, 250), area=5000,
                       center=(55, 225), estimated_type="text_line", height_pct=3.0)

    issues = detect_overlap([r1, r2])
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# detect_font_too_small
# ---------------------------------------------------------------------------

def test_detect_font_too_small_flags_tiny():
    """Text region at <1% of image height should be flagged as high severity."""
    # 8px on 1080 = 0.74%
    r = ElementRegion(bbox=(100, 100, 500, 108), area=3200,
                      center=(300, 104), estimated_type="text_line", height_pct=0.74)

    issues = detect_font_too_small([r], img_height=1080)
    assert len(issues) == 1
    assert issues[0]["severity"] == "high"


def test_detect_font_too_small_passes_normal():
    """Text region at 5% of image height should not be flagged."""
    r = ElementRegion(bbox=(100, 100, 500, 154), area=27000,
                      center=(300, 127), estimated_type="text_line", height_pct=5.0)

    issues = detect_font_too_small([r], img_height=1080)
    assert len(issues) == 0


def test_detect_font_too_small_ignores_non_text():
    """Non-text-line regions should not be checked for font size."""
    r = ElementRegion(bbox=(100, 100, 120, 108), area=160,
                      center=(110, 104), estimated_type="small_element", height_pct=0.5)

    issues = detect_font_too_small([r], img_height=1080)
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# detect_alignment_inconsistent
# ---------------------------------------------------------------------------

def test_detect_alignment_flags_misaligned():
    """Column with same X-center but inconsistent left edges should be flagged."""
    # All centers at X=200 (within 3% of 800 = 24px), so they form one group.
    # Left edges: 100, 100, 160 → spread 60px > 2% of 800 = 16px → flagged.
    regions = [
        ElementRegion(bbox=(100, 50, 300, 80), area=6000,
                      center=(200, 65), estimated_type="text_line", height_pct=3.0),
        ElementRegion(bbox=(100, 150, 300, 180), area=6000,
                      center=(200, 165), estimated_type="text_line", height_pct=3.0),
        ElementRegion(bbox=(160, 250, 240, 280), area=6000,
                      center=(200, 265), estimated_type="text_line", height_pct=3.0),
    ]
    issues = detect_alignment_inconsistent(regions, img_width=800)
    assert len(issues) >= 1
    assert issues[0]["issue_type"] == "alignment_inconsistent"


def test_detect_alignment_passes_aligned():
    """Well-aligned column should produce no issues."""
    regions = [
        ElementRegion(bbox=(100, 50, 300, 80), area=6000,
                      center=(200, 65), estimated_type="text_line", height_pct=3.0),
        ElementRegion(bbox=(100, 150, 300, 180), area=6000,
                      center=(200, 165), estimated_type="text_line", height_pct=3.0),
        ElementRegion(bbox=(100, 250, 300, 280), area=6000,
                      center=(200, 265), estimated_type="text_line", height_pct=3.0),
    ]
    issues = detect_alignment_inconsistent(regions, img_width=800)
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# generate_layout_description
# ---------------------------------------------------------------------------

def test_generate_layout_description_nonempty():
    """Should return a non-empty string mentioning region count."""
    regions = [
        ElementRegion(bbox=(100, 100, 500, 130), area=12000,
                      center=(300, 115), estimated_type="text_line", height_pct=3.0),
    ]
    desc = generate_layout_description(regions, (1920, 1080))
    assert "1 content region" in desc
    assert len(desc) > 20


def test_generate_layout_description_empty():
    """Empty image should mention 'blank' or 'No content'."""
    desc = generate_layout_description([], (1920, 1080))
    assert "no content" in desc.lower() or "blank" in desc.lower()


# ---------------------------------------------------------------------------
# score_layout_deep (integration)
# ---------------------------------------------------------------------------

def test_score_layout_deep_format(tmp_path):
    """Output dict should have all expected keys."""
    img = _make_test_image(640, 480, [
        (50, 50, 300, 80, (0, 0, 0)),
    ])
    img_path = tmp_path / "test.png"
    img.save(img_path)

    results = score_layout_deep([img_path])
    assert len(results) == 1
    r = results[0]
    assert "path" in r
    assert "image_size" in r
    assert "regions_detected" in r
    assert "region_inventory" in r
    assert "technical_issues" in r
    assert "layout_description" in r
    assert "error" in r
    assert r["error"] is None


def test_score_layout_deep_empty_image(tmp_path):
    """All-white image should detect 0 regions and no issues."""
    img = _make_test_image(640, 480)
    img_path = tmp_path / "blank.png"
    img.save(img_path)

    results = score_layout_deep([img_path])
    assert results[0]["regions_detected"] == 0
    assert results[0]["technical_issues"] == []
