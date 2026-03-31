"""
Generate random-dot-motion stimulus images for the Undo Threshold experiment.

Each image shows a field of dots. A proportion (coherence) of dots are displaced
in a consistent direction (left or right), while the remaining dots are placed
randomly. Higher coherence = easier to detect the direction.

Output: 90 PNG images in stimuli/ + image_list.txt for Inquisit <item> inputfile.
  - 2 directions (left, right) x 3 coherence levels (high=80%, medium=50%, low=30%)
  - 15 unique images per cell = 90 total
"""

import os
import random
from pathlib import Path
from PIL import Image, ImageDraw

# ── Configuration ──────────────────────────────────────────────────────
SEED = 42
IMG_SIZE = 400          # 400x400 px
NUM_DOTS = 150          # total dots per image
DOT_RADIUS = 4          # dot radius in pixels
DISPLACEMENT = 18       # coherent dot displacement in pixels (direction signal)
BG_COLOR = (240, 240, 240)  # light gray background
DOT_COLOR = (30, 30, 30)    # dark dots

COHERENCE_LEVELS = {
    "high": 0.80,
    "medium": 0.50,
    "low": 0.30,
}
DIRECTIONS = ["left", "right"]
IMAGES_PER_CELL = 15

MARGIN = 30  # keep dots away from edges


def generate_dot_image(direction: str, coherence: float, rng: random.Random) -> Image.Image:
    """
    Generate a single dot-motion stimulus image.

    Coherent dots appear as pairs: a faint 'origin' dot and a solid 'displaced' dot
    shifted in the target direction. This creates a static motion impression.
    Non-coherent dots are placed randomly (no pairing).
    """
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)

    n_coherent = int(NUM_DOTS * coherence)
    n_random = NUM_DOTS - n_coherent

    # Direction multiplier: left = negative x displacement, right = positive
    dx = -DISPLACEMENT if direction == "left" else DISPLACEMENT

    # Draw coherent dots (paired: origin + displaced)
    for _ in range(n_coherent):
        # Origin position (the "from" position)
        ox = rng.randint(MARGIN + abs(DISPLACEMENT), IMG_SIZE - MARGIN - abs(DISPLACEMENT))
        oy = rng.randint(MARGIN, IMG_SIZE - MARGIN)

        # Displaced position (the "to" position — where the dot "moved")
        tx = ox + dx
        ty = oy + rng.randint(-3, 3)  # slight vertical jitter

        # Draw faint origin dot (motion trail effect)
        draw.ellipse(
            [ox - DOT_RADIUS, oy - DOT_RADIUS, ox + DOT_RADIUS, oy + DOT_RADIUS],
            fill=(180, 180, 180)  # lighter = faint trail
        )
        # Draw solid displaced dot (current position)
        draw.ellipse(
            [tx - DOT_RADIUS, ty - DOT_RADIUS, tx + DOT_RADIUS, ty + DOT_RADIUS],
            fill=DOT_COLOR
        )

    # Draw random (noise) dots — no pairing, no directional signal
    for _ in range(n_random):
        rx = rng.randint(MARGIN, IMG_SIZE - MARGIN)
        ry = rng.randint(MARGIN, IMG_SIZE - MARGIN)
        draw.ellipse(
            [rx - DOT_RADIUS, ry - DOT_RADIUS, rx + DOT_RADIUS, ry + DOT_RADIUS],
            fill=DOT_COLOR
        )

    return img


def main():
    rng = random.Random(SEED)
    out_dir = Path(__file__).parent / "stimuli"
    out_dir.mkdir(exist_ok=True)

    filenames = []

    for direction in DIRECTIONS:
        for coh_label, coh_value in COHERENCE_LEVELS.items():
            for i in range(1, IMAGES_PER_CELL + 1):
                fname = f"{direction}_{coh_label}_{i:02d}.png"
                img = generate_dot_image(direction, coh_value, rng)
                img.save(out_dir / fname)
                filenames.append(fname)

    # Write image_list.txt for Inquisit <item> / inputfile
    list_path = out_dir / "image_list.txt"
    with open(list_path, "w") as f:
        for fname in filenames:
            f.write(fname + "\n")

    print(f"Generated {len(filenames)} images in {out_dir}")
    print(f"Image list written to {list_path}")

    # Print summary
    for direction in DIRECTIONS:
        for coh_label in COHERENCE_LEVELS:
            count = sum(1 for fn in filenames if fn.startswith(f"{direction}_{coh_label}_"))
            print(f"  {direction}_{coh_label}: {count} images")


if __name__ == "__main__":
    main()
