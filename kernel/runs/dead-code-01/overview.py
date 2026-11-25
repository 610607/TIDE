"""One-page overview of the dead-code-01 primary results (descriptive figure).

Written after the frozen analysis had run. Reads only committed analysis outputs and per-world
tables; runs no simulation. Writes dead-code-overview.png next to this script.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE / "results" / "analysis"
INK, MUTED, RULE, BAND = "#191919", "#666666", "#e3e3e3", "#eef3fb"
RETAIN, EMPTY, SELF = "#257de0", "#f47230", "#8c8c8c"
OUTCOME = {"differs": INK, "equivalent": "#257de0", "inconclusive": "#b5b5b5"}
CELLS = ("self-retain", "read-retain", "read-empty", "read_fetch-retain", "read_fetch-empty")
CELL_COLOR = {"self-retain": SELF, "read-retain": RETAIN, "read-empty": EMPTY,
              "read_fetch-retain": RETAIN, "read_fetch-empty": EMPTY}


def table(name):
    with open(ANALYSIS / name) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def style(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    if grid:
        getattr(ax, f"{grid}axis").grid(True, color=RULE, lw=0.8)
    ax.set_axisbelow(True)


def scaled_tests(ax):
    """Mean paired difference and its 90% bootstrap interval, in units of the equivalence bound."""
    rows = []
    for name, group in (("tests.tsv", "primary"), ("mechanisms.tsv", "mechanism"), ("replication.tsv", "C3")):
        for r in table(name):
            rows.append((group, r))
    order = [("primary", "D1"), ("primary", "D2"), ("mechanism", "D1"), ("mechanism", "D2"), ("C3", "C3")]
    labels, y = [], 0
    ticks = []
    for group, claim in order:
        block = [r for g, r in rows if g == group and r["claim"] == claim]
        for r in block:
            b = float(r["equivalence_bound"])
            lo, hi, mean = float(r["ci90_low"]) / b, float(r["ci90_high"]) / b, float(r["mean_difference"]) / b
            c = OUTCOME[r["outcome"]]
            ax.plot([lo, hi], [y, y], color=c, lw=2.2, solid_capstyle="round")
            ax.plot(mean, y, "o", ms=5, color=c, mec="white", mew=1)
            ticks.append(y)
            labels.append(f"{claim} {r['endpoint']}")
            y -= 1
        y -= 0.6
    ax.axvspan(-1, 1, color=BAND, zorder=0)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(ticks, labels, fontsize=8.5, color=INK)
    ax.set_xlim(-4.2, 6.5)
    ax.set_xlabel("difference ÷ equivalence bound (shaded: ±1)", fontsize=9, color=MUTED)
    style(ax, grid="x")
    for name, c in OUTCOME.items():
        ax.plot([], [], color=c, lw=2.2, label=name)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.set_title("A  Paired tests: retain − empty (D1 read, D2 read_fetch)\n    and read_fetch-retain − self-retain (C3)",
                 loc="left", fontsize=10, color=INK)


def m2(ax):
    rows = table("endpoints.tsv")
    by = {c: {int(r["seed"]): float(r["M2"]) for r in rows if r["cell"] == c} for c in CELLS}
    seeds = sorted(by["self-retain"])
    for a, b in ((1, 2), (3, 4)):
        for s in seeds:
            ax.plot([a, b], [by[CELLS[a]][s], by[CELLS[b]][s]], color="#cfcfcf", lw=0.6, zorder=1)
    for i, c in enumerate(CELLS):
        ys = [by[c][s] for s in seeds]
        ax.scatter([i] * len(ys), ys, s=12, color=CELL_COLOR[c], alpha=0.75, lw=0, zorder=2)
        med = sorted(ys)[len(ys) // 2 - 1: len(ys) // 2 + 1]
        m = sum(med) / 2
        ax.plot([i - 0.28, i + 0.28], [m, m], color=INK, lw=1.6, zorder=3)
    ax.set_yscale("log")
    ax.set_xticks(range(5), ["self\nretain", "read\nretain", "read\nempty", "read_fetch\nretain", "read_fetch\nempty"],
                  fontsize=8.5, color=INK)
    ax.set_ylabel("per 10⁶ births", fontsize=9, color=MUTED)
    style(ax)
    ax.set_title("B  M2: substitution-free births with a new genotype\n    (bar: median; lines pair seeds)",
                 loc="left", fontsize=10, color=INK)


def rcccjd(ax):
    rows = table("rcccjd_worlds.tsv")
    by = {c: {int(r["seed"]): (int(r["established"]), float(r["fraction"])) for r in rows if r["cell"] == c}
          for c in ("read_fetch-retain", "read_fetch-empty")}
    seeds = sorted(by["read_fetch-retain"])
    for s in seeds:
        ax.plot([0, 1], [by["read_fetch-retain"][s][1], by["read_fetch-empty"][s][1]], color="#cfcfcf", lw=0.6)
    for i, (c, col) in enumerate((("read_fetch-retain", RETAIN), ("read_fetch-empty", EMPTY))):
        ys = [by[c][s][1] for s in seeds]
        n = sum(by[c][s][0] for s in seeds)
        ax.scatter([i] * len(ys), ys, s=14, color=col, alpha=0.8, lw=0, zorder=2)
        ax.text(i, 0.262, f"established in {n}/32", ha="center", va="top", fontsize=8.5, color=INK)
    ax.set_xticks([0, 1], ["read_fetch\nretain", "read_fetch\nempty"], fontsize=8.5, color=INK)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.01, 0.27)
    ax.set_ylabel("share of 61 window timepoints", fontsize=9, color=MUTED)
    style(ax)
    ax.set_title("C  RCCCJD in the filtered set\n    (fetch-requiring; lines pair seeds)", loc="left", fontsize=10, color=INK)


def main():
    fig = plt.figure(figsize=(12, 7.2), facecolor="white")
    grid = fig.add_gridspec(2, 2, width_ratios=[1.15, 1], height_ratios=[1, 1], wspace=0.28, hspace=0.45)
    scaled_tests(fig.add_subplot(grid[:, 0]))
    m2(fig.add_subplot(grid[0, 1]))
    rcccjd(fig.add_subplot(grid[1, 1]))
    fig.suptitle("dead-code-01: retaining vs clearing dead code, 32 × 32, seeds 31001–31032",
                 x=0.06, ha="left", fontsize=11.5, color=INK)
    fig.savefig(HERE / "dead-code-overview.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
