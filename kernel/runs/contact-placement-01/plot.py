"""Plot paired case effects, reading stages and an observed relocation in a digital field."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from run import CASE, read

BLUE, TEAL, GOLD, GRAY, INK = "#365786", "#08766e", "#a05d20", "#74818e", "#1b2e3e"


def panel(ax, label, title):
    ax.set_title(label + "   " + title, loc="left", color=INK, fontsize=13, weight="bold", pad=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(color=GRAY, labelcolor=INK)


def main(directory, output):
    fig, axs = plt.subplots(2, 2, figsize=(13.6, 8.2), gridspec_kw={"height_ratios": [1.28, 1]})
    fig.subplots_adjust(left=.16, right=.97, top=.83, bottom=.10, wspace=.64, hspace=.62)
    fig.text(.035, .955, "Can a distant reader copy a surviving template if brought next to it?",
             color=INK, fontsize=21, weight="bold")
    fig.text(.035, .912, "5,039 historical windows screened   /   3,439 paired placements   /   one swap per branch",
             color=GRAY, fontsize=12)
    summary = next(r for r in read(directory / "summary.tsv") if r["cohort"] == "pooled" and r["branch"] == "contact")
    effects = [r for r in read(directory / "contrasts.tsv") if r["endpoint"] == "any_exact"]
    ax = axs[0, 0]
    panel(ax, "A", "Extra windows with an exact birth")
    cohort_labels = ["All pairs", "Seed block 1", "Seed block 2", "Both east", "Read randomized",
                     "Placement randomized", "Both randomized"]
    pos = np.array([7, 5.7, 4.7, 3.3, 2.3, 1.3, .3])
    for i, (row, y) in enumerate(zip(effects, pos)):
        mean, low, high = [100 * float(row[k]) for k in ("difference", "low95", "high95")]
        ax.errorbar(mean, y, xerr=[[mean-low], [high-mean]], fmt="o", markersize=8 if i == 0 else 5,
                    color=TEAL if i == 0 else BLUE, capsize=3, lw=1.7)
    ax.set_yticks(pos, cohort_labels)
    ax.set_ylim(-.4, 7.8)
    ax.set_xlim(-.12, 4.05)
    ax.axvline(0, color=GRAY, ls=":", lw=1)
    ax.grid(axis="x", alpha=.15)
    ax.set_xlabel("Adjacent minus distant control (percentage points)\n95% intervals clustered by original seed", fontsize=10)

    ax = axs[0, 1]
    panel(ax, "B", "What the adjacent reader did")
    keys = ["pairs", "facing", "selected_focal", "selected_first", "selected_six", "selected_exact"]
    labels = ["Placed adjacent", "Faced template", "Selected template with S", "Wrote first aligned byte",
              "Read six aligned bytes", "Completed exact birth"]
    values = [int(summary[k]) for k in keys]
    ax.barh(range(len(keys)), values, height=.52, color=[GRAY, BLUE, BLUE, TEAL, TEAL, TEAL])
    ax.set_yticks(range(len(keys)), labels)
    ax.invert_yaxis()
    for y, v in enumerate(values):
        ax.text(v + 52, y, f"{v:,}", va="center", fontsize=10, color=INK)
    ax.set_xlim(0, 4000)
    ax.set_xticks([0, 1000, 2000, 3000])
    ax.grid(axis="x", alpha=.15)
    ax.set_xlabel("Windows reaching each event", fontsize=10)

    attempts = read(directory / "attempts.tsv")
    example = next(a for a in attempts if a["status"] == "birth" and a["aligned"] == "1" and a["substitutions"] == "0")
    fork = next(s for s in read(directory / "screen.tsv") if all(s[k] == example[k] for k in CASE))
    xy = lambda site: (int(site) % 16, int(site) // 16)
    ax = axs[1, 0]
    panel(ax, "C", f"One pair at tick {fork['tick']} (seed {fork['seed']})")
    ax.set_xlim(-.5, 15.5)
    ax.set_ylim(-.5, 3.5)
    ax.set_xticks(range(0, 16, 2))
    ax.set_yticks(range(4))
    ax.set_xticks(np.arange(-.5, 16, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 4, 1), minor=True)
    ax.grid(which="minor", color="#d8dfe4")
    ax.tick_params(which="minor", length=0)
    ax.set_aspect("equal", anchor="NW")
    for key, label, color, marker in (("focal_site", "Template", TEAL, "s"), ("reader_origin", "Reader origin", GRAY, "o"),
                                     ("contact", "Adjacent", BLUE, "D"), ("sham", "Distant control", GOLD, "X")):
        ax.scatter(*xy(fork[key]), s=110, marker=marker, color=color, edgecolor="white", lw=.6,
                   label=label, zorder=5)
    ax.legend(loc="upper center", bbox_to_anchor=(.50, -.24), ncol=2, frameon=False, fontsize=9)
    ax.set_ylabel("Lattice row", fontsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax = axs[1, 1]
    panel(ax, "D", "Six bytes traced to the living template")
    trace = [v.split("/") for v in example["trace"].split(",")]
    ts = [int(v[0]) for v in trace]
    finish = int(example["finish"])
    ax.plot([ts[0], finish], [0, 0], color="#c8d7db", lw=2)
    ax.scatter(ts, [0]*len(ts), s=215, marker="s", color=TEAL, zorder=3)
    for tick, part in zip(ts, trace):
        ax.text(tick, 0, chr(int(part[5])), color="white", fontsize=12, ha="center", va="center",
                fontfamily="monospace", zorder=4)
    ax.scatter([finish], [0], s=95, color=BLUE, marker="D", zorder=4)
    ax.text(finish, .22, "Birth", ha="center", color=BLUE, fontsize=10, weight="bold")
    ax.text(.02, .93, f"Template at site {fork['focal_site']}    →    reader at {fork['contact']}    →    offspring at {example['target']}",
            transform=ax.transAxes, color=INK, fontsize=10)
    ax.set_xlim(ts[0]-1, finish+1)
    ax.set_ylim(-.55, .85)
    ax.set_yticks([])
    ax.set_xticks(ts + [finish])
    ax.set_xlabel("Simulation tick", fontsize=10)
    ax.spines["left"].set_visible(False)
    copies = read(directory / "reuse.tsv")
    same = sum(int(r["maker_exact"]) > 0 for r in copies)
    others = sum(int(r["other_exact"]) > 0 for r in copies)
    fig.text(.035, .018, f"{len(copies)} offspring followed through death    /    {same} supplied another exact birth to the same reader"
             f"    /    {others} supplied one to a different reader", fontsize=11, color=TEAL, weight="bold")
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.directory, args.output)
