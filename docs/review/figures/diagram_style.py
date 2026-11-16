"""Shared styling for original review schematics; no external figure assets."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

INK = "#17324D"
TEAL = "#087E8B"
ORANGE = "#C06A24"
PURPLE = "#79549A"
PALE = "#EEF4F6"
GRAY = "#61717E"
LINE = "#CCD8DF"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": LINE,
    "xtick.color": GRAY, "ytick.color": GRAY,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})


def canvas(*, height=4.3):
    fig, ax = plt.subplots(figsize=(8, height * 0.8))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
    ax.set(xlim=(0, 10), ylim=(0, height))
    ax.axis("off")
    return fig, ax


def label(ax, xy, content, *, size=10, color=INK, ha="center", **kwargs):
    return ax.text(*xy, content, fontsize=size, color=color, ha=ha,
                   va="center", linespacing=1.35, **kwargs)


def box(ax, bounds, content="", *, color=TEAL, fill=PALE, size=10):
    x, y, width, height = bounds
    patch = FancyBboxPatch((x, y), width, height,
                          boxstyle="round,pad=0.02,rounding_size=0.07",
                          edgecolor=color, facecolor=fill, linewidth=1.2)
    ax.add_patch(patch)
    if content:
        label(ax, (x + width / 2, y + height / 2), content, size=size)


def arrow(ax, start, end, *, color=INK, style="-", curve=0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                mutation_scale=11, linewidth=1.4,
                                color=color, linestyle=style,
                                connectionstyle=f"arc3,rad={curve}"))


def cells(ax, origin, values, *, color=TEAL, size=0.34, text=False):
    x, y = origin
    for index, value in enumerate(values):
        ax.add_patch(Rectangle((x + index * size, y), size, size,
                               facecolor=color if value else "white",
                               edgecolor=LINE, linewidth=0.8))
        if text:
            label(ax, (x + (index + 0.5) * size, y + size / 2), str(value),
                  color="white" if value else INK, size=10)


def save(fig, name, *, output, preview=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / f"{name}.pdf", metadata={
        "Title": name.replace("-", " "), "Author": "TIDE Research Notes",
        "CreationDate": None, "ModDate": None,
    })
    if preview:
        Path(preview).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(preview) / f"{name}.png", dpi=180)
    plt.close(fig)
