"""Draw the exchange clocks, copying stages, phase profile and world-level handoffs."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

UNIFORM, BURST, INK = "#536786", "#007871", "#1d3446"
MUTED, ACTIVE, SHORT = "#516677", "#f5e6d2", "#eef0f4"


def read(d, name):
    with (d / (name + ".tsv")).open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def panel(ax, letter, title):
    ax.set_title(letter + "   " + title, loc="left", weight="bold", color=INK, fontsize=13, pad=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=.17)


def main(d, output):
    cohorts = {(r["cohort"], r["arm"]): r for r in read(d, "cohorts")}
    phases = {(r["arm"], int(r["phase"])): r for r in read(d, "phase-summary") if r["cohort"] == "new"}
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.4))
    fig.subplots_adjust(left=.09, right=.97, top=.82, bottom=.10, wspace=.29, hspace=.62)
    fig.text(.045, .95, "Copying across intervals of movement and rest", color=INK, fontsize=22, weight="bold")
    fig.text(.045, .903, "Same ordered edge offers in each seed pair   /   2,048 archived seeds and 2,048 new seeds",
             fontsize=12, color=MUTED)
    x = np.arange(32)
    ax = axes[0, 0]
    panel(ax, "A", "The two exchange schedules")
    ax.stairs([4]*8+[0]*24, np.arange(-.5, 32), baseline=None, color=BURST, lw=3, label="Burst")
    ax.axhline(1, color=UNIFORM, ls="--", lw=2, label="Uniform")
    ax.set(xlim=(-.5, 31.5), ylim=(-.35, 5.25), yticks=[0, 1, 2, 3, 4], xticks=[0, 8, 16, 24, 31],
           xlabel="Instruction tick within a rotated cycle", ylabel="Post-commit sweeps per tick")
    ax.legend(frameon=False, loc="upper right", ncol=2)
    ax.text(19, .32, "24 quiet ticks", ha="center", color=BURST)
    ax = axes[0, 1]
    panel(ax, "B", "Outcomes per 100 copy starts")
    for arm, shift, color in (("high", -.19, UNIFORM), ("burst", .19, BURST)):
        r = cohorts["new", arm]
        rates = [100*int(r[k])/int(r["starts"]) for k in ("switches", "six", "exact")]
        bars = ax.bar(np.arange(3)+shift, rates, .35, color=color, label="Uniform" if arm=="high" else "Burst")
        ax.bar_label(bars, labels=[f"{v:.1f}" for v in rates], fontsize=9, padding=3)
    ax.set(ylim=(0, 78), xticks=range(3), xticklabels=["Source switched", "Six aligned reads", "Exact birth"],
           ylabel="% of starts from an unlike living donor")
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax = axes[1, 0]
    panel(ax, "C", "Reading continuity by first-write timing")
    ax.axvspan(-.5, 7.5, color=ACTIVE, zorder=0)
    ax.axvspan(22.5, 31.5, color=SHORT, zorder=0)
    for arm, color in (("high", UNIFORM), ("burst", BURST)):
        rates = [100*int(phases[arm,p]["six"])/int(phases[arm,p]["starts"]) for p in x]
        ax.plot(x, rates, color=color, lw=2, marker="o", ms=3, label="Uniform" if arm=="high" else "Burst")
    ax.set(xlim=(-.5,31.5), ylim=(0,110), xticks=[0,8,16,23,31], yticks=[0,25,50,75,100],
           xlabel="Cycle position of the first written byte", ylabel="Six aligned reads (% of starts)")
    for p, text in ((3.5,"Moving"), (15,"≥10 quiet ticks"), (27,"<10 quiet")):
        ax.text(p, 103, text, ha="center", fontsize=9, color=MUTED)
    ax = axes[1, 1]
    panel(ax, "D", "Worlds with a different-reader handoff")
    for arm, shift, color in (("high", -.19, UNIFORM), ("burst", .19, BURST)):
        counts = [int(cohorts[c, arm]["complete_handoff_world"]) for c in ("archived", "new")]
        bars = ax.bar(np.arange(2)+shift, counts, .35, color=color)
        ax.bar_label(bars, padding=3, fontsize=11, weight="bold")
    ax.set(xticks=[0,1], xticklabels=["Archived seeds", "New seeds"], yticks=[0,1,2,3,4], ylim=(0,4.3),
           ylabel="Worlds out of 2,048 per schedule")
    fig.text(.045, .022, "Panels B and C use new seeds. In panel C, background bands show the burst clock. Panel D requires full newborn lifetimes.",
             color=MUTED, fontsize=10)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    main(a.directory, a.output)
