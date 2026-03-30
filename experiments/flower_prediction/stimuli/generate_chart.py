"""
Generate bar chart for flower_prediction Study 1a (Inquisit experiment).
Distribution: 35 prior flowers with 0-5 spotted petals.
  0 spots: 3  |  1 spot: 4  |  2 spots: 4
  3 spots: 6  |  4 spots: 8  |  5 spots: 10

Run this script once before launching the Inquisit experiment.
Output: chart.png (in the same stimuli/ folder as this script).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Distribution data
petals = [0, 1, 2, 3, 4, 5]
counts = [3, 4, 4, 6, 8, 10]

fig, ax = plt.subplots(figsize=(5.5, 4.2))

bars = ax.bar(
    petals, counts,
    color="#4878a8",
    edgecolor="black",
    linewidth=0.8,
    width=0.65,
)

# Axis labels and ticks
ax.set_xlabel("Number of Spotted Petals", fontsize=12, labelpad=8)
ax.set_ylabel("Number of Flowers", fontsize=12, labelpad=8)
ax.set_xticks(petals)
ax.set_xticklabels([str(p) for p in petals], fontsize=11)
ax.set_yticks(range(0, 12, 2))
ax.set_yticklabels([str(y) for y in range(0, 12, 2)], fontsize=11)
ax.set_ylim(0, 11)
ax.set_xlim(-0.5, 5.5)

# Clean styling
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(axis="both", direction="out", length=4)
ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax.set_axisbelow(True)

# Frequency labels on bars
for bar, count in zip(bars, counts):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.15,
        str(count),
        ha="center", va="bottom", fontsize=10, color="black"
    )

fig.tight_layout()

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chart.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Chart saved to: {out_path}")
