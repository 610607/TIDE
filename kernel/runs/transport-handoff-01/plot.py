"""Draw the field-level handoff result and one recorded loss of a living byte source."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

from run import ARMS, SPLIT, read

INK, MUTED = "#1d3344", "#586a77"
TEAL, NAVY, AMBER = "#107c73", "#365680", "#b7702e"
PALE, GRAY = "#b6c5d0", "#dfe5e9"
NAMES = ["Stationary", "Low exchange", "High exchange"]


def chart(ax, label, title):
    ax.set_title(f"{label}   {title}", loc="left", color=INK, weight="bold", fontsize=13, pad=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelcolor=INK, color=GRAY)
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)


def main(directory, output):
    data = {(r["cohort"], r["arm"]): r for r in read(directory / "cohorts.tsv") if r["window"] == "complete"}
    switches = {r["arm"]: r for r in read(directory / "switch-summary.tsv") if r["cohort"] == "prospective"}
    example = next(r for r in read(directory / "switches.tsv") if int(r["seed"]) >= SPLIT and r["arm"] == "high"
                   and r["site"] == r["previous_site"] and int(r["donor_now"]) >= 0 and r["source_bank"] == "occupied")
    fig, grid = plt.subplots(2, 2, figsize=(12.6, 8.6))
    fig.subplots_adjust(left=.09, right=.97, bottom=.09, top=.83, wspace=.29, hspace=.77)
    fig.text(.045, .95, "Passive movement, encounters and reader handoff", color=INK, fontsize=21, weight="bold")
    fig.text(.045, .908, "Each cohort contains 2,048 matched seeds per setting. All newborns start facing east.",
             color=MUTED, fontsize=12)
    x = np.arange(3)
    ax = grid[0, 0]
    chart(ax, "A", "Worlds with a different-reader handoff")
    for cohort, offset, color in (("historical", -.18, PALE), ("prospective", .18, TEAL)):
        v = [int(data[cohort, a]["handoff_world"]) for a in ARMS]
        bars = ax.bar(x + offset, v, .32, color=color, label=cohort.capitalize())
        ax.bar_label(bars, padding=3, color=INK, fontsize=11, weight="bold")
    ax.set_ylim(0, 8)
    ax.set_yticks([0, 2, 4, 6])
    ax.set_xticks(x, NAMES)
    ax.set_ylabel("Worlds out of 2,048")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax = grid[0, 1]
    chart(ax, "B", "Potential encounters per new world")
    v = [int(data["prospective", a]["encounters"]) / int(data["prospective", a]["worlds"]) for a in ARMS]
    bars = ax.bar(x, v, .51, color=NAVY)
    ax.bar_label(bars, labels=[f"{n:.1f}" for n in v], padding=3, fontsize=11, color=INK)
    ax.set_xticks(x, NAMES)
    ax.set_ylim(0, 445)
    ax.set_ylabel("Unique reader–potential donor pairs")
    ax = grid[1, 0]
    chart(ax, "C", "Copies switching source mid-allocation")
    bottom = np.zeros(3)
    for k, label, color in (("same_site_displaced", "Living donor moved", TEAL),
                            ("same_site_after_death", "Donor already dead", AMBER),
                            ("changed_address", "Read address changed", GRAY)):
        v = np.array([100 * int(switches[a][k]) / int(switches[a]["starts"]) for a in ARMS])
        ax.bar(x, v, .48, bottom=bottom, color=color, label=label)
        bottom += v
    for i, n in enumerate(bottom):
        ax.text(i, n + 1.1, f"{n:.1f}%", ha="center", color=INK, fontsize=10, weight="bold")
    ax.set_xticks(x, NAMES)
    ax.set_ylim(0, 57)
    ax.set_ylabel("% of eligible copy starts (new seeds)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.8)
    ax = grid[1, 1]
    chart(ax, "D", "One read address, two different donors")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(.005, .99, f"New seed {example['seed']}   /   high exchange   /   reader at site {example['actor_site']}",
            fontsize=10, color=MUTED, va="top")
    for y, tick, text, extra, color in (
        (.65, example["previous_tick"], f"Read site {example['previous_site']}", "Original donor", TEAL),
        (.23, example["tick"], f"Read site {example['site']}", "Replacement donor", NAVY)):
        ax.text(.005, y, "Tick " + tick, color=INK, va="center", weight="bold", fontsize=11)
        ax.add_patch(FancyBboxPatch((.245, y-.12), .70, .23, boxstyle="round,pad=0.012,rounding_size=0.025",
                                    facecolor=color, edgecolor="none"))
        ax.text(.28, y, text + "   ·   " + extra, color="white", va="center", fontsize=10.3)
    ax.annotate("", xy=(.14, .34), xytext=(.14, .55), arrowprops={"arrowstyle": "->", "color": MUTED})
    ax.text(.25, .435, f"Original donor moved to site {example['donor_now']}", color=TEAL, va="center", fontsize=10.2)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.directory, args.output)
