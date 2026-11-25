"""Render a common conformation and exact contact probabilities from the run tables."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from geometry import COMPACT, PAIRS, contact_mask, unlike_mask

HERE = Path(__file__).parent
ZERO, ONE = "#f1d49c", "#265466"
INK, QUIET = "#19343c", "#51656a"
ATTRACTION = "#b95332"
ARMS = (("001011", 1, "Neutral · either order", "#929d9f"),
        ("001011", 4, "001011", "#12675c"), ("011100", 4, "011100", "#bd5638"))


def diagram(ax, sequence):
    fav = unlike_mask(sequence)
    m = contact_mask(COMPACT)
    n = (m & fav).bit_count()
    x, y = zip(*COMPACT)
    ax.plot(x, y, color=INK, lw=3.2, zorder=1)
    for bit, (i, j) in enumerate(PAIRS):
        if m & (1 << bit):
            color = ATTRACTION if fav & (1 << bit) else "#94a1a2"
            ax.plot([x[i], x[j]], [y[i], y[j]], lw=2.8, color=color, ls=(0, (2.5, 2)), zorder=2)
    for pos, (symbol, a, b) in enumerate(zip(sequence, x, y), start=1):
        ax.scatter(a, b, s=545, color=ONE if symbol == "1" else ZERO, edgecolors="white",
                   linewidths=1.5, zorder=3)
        ax.text(a, b, str(pos), color="white" if symbol == "1" else INK, ha="center",
                va="center", fontsize=11, weight="bold", zorder=4)
    ax.set(xlim=(-.43, 2.43), ylim=(-.34, 1.35), aspect="equal")
    ax.axis("off")
    ax.set_title(sequence, loc="left", color=INK, weight="bold", fontsize=14, pad=3)
    ax.text(0, -.08, f"{n} unlike contact{'s' if n != 1 else ''}   ·   shape weight {4**n}",
            transform=ax.transAxes, fontsize=10.5, color=QUIET)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--out", type=Path, default=HERE / "contacts.png")
    args = parser.parse_args()
    with (args.results / "pairs.tsv").open() as f:
        probs = {(r["sequence"], int(r["q"]), int(r["i"]), int(r["j"])): float(r["probability"])
                 for r in csv.DictReader(f, delimiter="\t")}

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": QUIET, "ytick.color": INK})
    fig = plt.figure(figsize=(11, 6.0), facecolor="white")
    fig.text(.052, .935, "Which positions meet when a chain bends?", fontsize=23, weight="bold")
    fig.text(.052, .879, "Six beads on a square lattice  /  three of each type  /  exact equilibrium probabilities",
             color=QUIET, fontsize=12)
    fig.text(.052, .779, "A   One allowed shape", fontsize=14, weight="bold")
    fig.text(.432, .779, "B   Contact frequency across all 284 shapes", fontsize=14, weight="bold")

    for bottom, (s, _, _, _) in zip((.445, .135), ARMS[1:]):
        diagram(fig.add_axes([.061, bottom, .263, .235]), s)
    fig.text(.052, .722, "Numbers give backbone position.", fontsize=10, color=QUIET)
    fig.text(.052, .059, "Bead type", color=INK, fontsize=10)
    for x, symbol, color in ((.137, "0", ZERO), (.179, "1", ONE)):
        fig.add_artist(plt.Line2D([x], [.066], transform=fig.transFigure, marker="o",
                                  markersize=8, color=color, linestyle="none"))
        fig.text(x + .010, .059, symbol, color=INK, fontsize=10)
    fig.text(.052, .025, "Dashed contacts: orange = unlike, gray = like.", fontsize=9, color=QUIET)

    pairs = [(1, 4), (3, 6), (1, 6), (2, 5)]
    ax = fig.add_axes([.494, .164, .449, .493])
    for j, (s, q, label, color) in enumerate(ARMS):
        values = [probs[s, q, i, k] for i, k in pairs]
        ys = [3 - n + (1 - j) * .225 for n in range(len(pairs))]
        ax.barh(ys, values, height=.188, color=color, label=label, zorder=2)
        for y, v in zip(ys, values):
            ax.text(v + .006, y, f"{v:.1%}", va="center", fontsize=9, color=INK)
    ax.set(yticks=range(3, -1, -1), yticklabels=[f"{i}–{j}" for i, j in pairs],
           xlim=(0, .50), ylim=(-.54, 3.54), xlabel="Probability that the two positions touch")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="x", color="#e0e6e6", lw=.8, zorder=0)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0, pad=7)
    ax.xaxis.labelpad = 9
    ax.legend(loc="lower left", bbox_to_anchor=(-.15, 1.005), frameon=False, ncol=3, handlelength=1.1,
              columnspacing=1.35, fontsize=10.5)
    fig.text(.432, .045, "Several pairs can touch at once. Each bar is a marginal probability.",
             fontsize=10, color=QUIET)
    fig.savefig(args.out, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
