"""Draw the two episodes of an exact sequence and its cohort context."""
import argparse
import csv
import gzip
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

INK, SOFT, GRID = "#193541", "#4d626b", "#dbe5e7"
OCC, RESERVED, FREE = "#177b73", "#edae55", "#a8c2d0"
KINDS = ("occupied", "reserved", "free")


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def survival(counts):
    total = sum(counts)
    tail = total
    for n in counts:
        yield 100 * tail / total
        tail -= n


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(GRID)
    ax.tick_params(length=0, pad=6, colors=SOFT)
    ax.set_axisbelow(True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    stock = read(args.results / "witness-stocks.tsv")
    births = [r for r in read(args.results / "witness-births.tsv") if r["product"] == stock[0]["sequence"]]
    cohorts = read(args.results / "cohorts.tsv")
    lengths = {k: [0] * 2050 for k in ("max_occupied_run", "max_stored_run")}
    with gzip.open(args.results / "world-sequences.tsv.gz", "rt") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if int(row["occupied_ticks"]):
                for k, histogram in lengths.items():
                    histogram[int(row[k])] += 1
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                         "axes.labelcolor": SOFT, "axes.titlecolor": INK})
    fig = plt.figure(figsize=(13.4, 8.9), facecolor="white")
    fig.text(.072, .945, "Who copies a digital sequence, and how long does it persist?",
             size=22, weight="bold")
    fig.text(.072, .908, "Natural six-byte fields   /   2,048 worlds   /   2,048 ticks per world",
             size=12, color=SOFT)
    fig.text(.072, .843, "R..PLD in seed 19,722", size=16, weight="bold")
    fig.legend(handles=[Patch(color=c, label=s) for s, c in zip(("Living", "Reserved", "Free storage"),
                                                                 (OCC, RESERVED, FREE))],
               loc="center right", bbox_to_anchor=(.953, .851), frameon=False, ncol=3, handlelength=1.3)
    tick = [0] + [int(r["tick"]) for r in stock] + [2048]
    quantities = [[0] + [int(r[k]) for r in stock] + [int(stock[-1][k])] for k in KINDS]
    labels = {"residual": "Reserved bytes", "live": "Living donor", "substitution": "Substitution"}
    for i, (low, high) in enumerate(((255, 425), (1575, 1785))):
        ax = fig.add_axes([.075 + .465*i, .593, .4, .190])
        style(ax)
        ax.stackplot(tick, *quantities, step="post", colors=(OCC, RESERVED, FREE), linewidth=0)
        for row in births:
            t = int(row["tick"])
            if low <= t <= high:
                ax.plot([t, t], [2.06, 2.29], color=SOFT, lw=.8)
                ax.text(t, 2.34, f"{labels[row['route']]}\n{t}", ha="center", fontsize=9, linespacing=1.3)
        ax.set(xlim=(low, high), ylim=(0, 3.13), yticks=[0, 1, 2], xlabel="Simulation tick")
        if i == 0:
            ax.set_ylabel("Exact copies on the field")
        ax.grid(axis="y", color=GRID, lw=.65)
    fig.text(.075, .509, "Separate time windows. No bank contained R..PLD from tick 414 through 1,592.",
             color=SOFT, size=10)
    fig.text(.072, .433, "How many worlds had a neighbor make a copy?", size=13.7, weight="bold")
    fig.text(.072, .403, "Executor and living template carry different sequences.", size=10, color=SOFT)
    fig.text(.538, .433, "How long did an exact sequence remain present?", size=13.7, weight="bold")
    n = sum(lengths["max_occupied_run"])
    fig.text(.538, .403, f"{n:,} world–sequence pairs with at least one living copy.", size=10, color=SOFT)
    bar = fig.add_axes([.075, .18, .38, .176])
    style(bar)
    for i, row in enumerate(cohorts[:2]):
        for dy, k, color in ((.17, "different_live_worlds", OCC), (-.17, "zero_direct_complete_worlds", FREE)):
            y = 1-i+dy
            value = int(row[k])
            bar.barh(y, value, height=.24, color=color)
            bar.text(value+16, y, f"{value:,}", va="center", size=10, weight="bold")
    bar.set(xlim=(0, 1024), ylim=(-.45, 1.5), yticks=[0, 1], yticklabels=["Replication", "Pilot"],
            xticks=[0, 256, 512, 768, 1024], xlabel="Worlds out of 1,024 per cohort")
    bar.grid(axis="x", color=GRID, lw=.7)
    bar.legend(handles=[Patch(color=OCC, label="Any such copy"),
                        Patch(color=FREE, label="Includes a donor with zero lifetime births")],
               loc="upper left", bbox_to_anchor=(-.01, -.37), frameon=False, fontsize=9)
    dur = fig.add_axes([.545, .18, .391, .176])
    style(dur)
    for k, color, name in (("max_stored_run", "#a96316", "Any bank"), ("max_occupied_run", OCC, "Living only")):
        dur.step(range(1, 2050), list(survival(lengths[k]))[1:], where="post", label=name, lw=1.8, color=color)
    dur.set(xscale="log", yscale="log", xlim=(1, 2049), ylim=(.5, 130),
            xlabel="Longest uninterrupted presence (tick snapshots)", ylabel="Pairs reaching duration (%)")
    dur.set_xticks([1, 10, 81, 324, 2049], ["1", "10", "81", "324", "2,049"])
    dur.set_yticks([1, 10, 100], ["1", "10", "100"])
    dur.minorticks_off()
    dur.grid(axis="y", color=GRID, lw=.7)
    dur.legend(loc="lower left", fontsize=9, frameon=False)
    fig.text(.538, .085, "At 162 snapshots, {:.1f}% remained continuously stored and {:.1f}%".format(
        100*sum(lengths["max_stored_run"][162:])/n, 100*sum(lengths["max_occupied_run"][162:])/n),
        size=9.5, color=SOFT)
    fig.text(.538, .064, "remained continuously present in living individuals.", size=9.5, color=SOFT)
    fig.savefig(args.png, dpi=175, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    main()
