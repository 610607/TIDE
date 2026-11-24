"""Render the observable reader branches and classify every individual in the two pedigrees."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


HERE = Path(__file__).resolve().parent
READER = "5253434c44"
INK, MUTED, GRID = "#162E38", "#48636E", "#DCE4E6"
TEAL, BLUE, GRAY = "#00796C", "#466797", "#D1D8DB"
CLASSES = ["dependent", "reproduces_under_denial", "no_ordinary_birth"]
COLORS = dict(zip(CLASSES, (TEAL, BLUE, GRAY)))


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def branch(ax, rows, root, links):
    selected, exact, children = {}, set(), {}
    for row in rows:
        cpu = int(row["site"]), int(row["born"])
        parent = int(row["parent_site"]), int(row["parent_born"])
        if cpu != root and parent not in exact:
            continue
        selected[cpu] = row
        children[cpu] = []
        if cpu != root:
            children[parent].append(cpu)
        if row["genome_hex"] == READER:
            exact.add(cpu)
    y, tips = {}, []

    def layout(cpu):
        if children[cpu]:
            positions = [layout(kid) for kid in children[cpu]]
            y[cpu] = (positions[0]+positions[-1])/2
        else:
            y[cpu] = len(tips)
            tips.append(cpu)
        return y[cpu]

    layout(root)
    for parent, kids in children.items():
        for kid in kids:
            live = (parent, kid) in links
            ax.plot([parent[1]-root[1], kid[1]-root[1]], [y[parent], y[kid]],
                    color=TEAL if live else "#A6B3B8", lw=2.4 if live else 1.1, zorder=2)
    for cpu, row in selected.items():
        ax.scatter(cpu[1]-root[1], y[cpu], marker="o" if cpu in exact else "D", s=65,
                   color=COLORS[row["classification"]], edgecolor="white", lw=.9, zorder=3)
    ax.set_ylim(-.7, len(tips)-.3)
    ax.set_xlim(-9, 310)
    ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID, lw=.8)
    ax.set_xlabel("Ticks since the founder's birth", color=MUTED)
    for spine in ("left", "top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, colors=MUTED, pad=7)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pedigrees", type=Path)
    parser.add_argument("natural", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    summaries = read(args.pedigrees / "summary.tsv")
    people = read(args.pedigrees / "individuals.tsv")
    if [r["seed"] for r in summaries] != ["3562", "11942"]:
        raise ValueError("the two-panel figure expects the archived index and replication families")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
                         "axes.titlecolor": INK, "axes.labelcolor": MUTED})
    fig = plt.figure(figsize=(13.8, 8.9), facecolor="white")
    fig.text(.065, .948, "Read dependence in two independently evolved families",
             fontsize=23, weight="bold")
    fig.text(.065, .901, "Each node is a real birth. Its color shows whether that individual reproduced when external reads were denied.",
             color=MUTED, fontsize=12)
    labels = [("Dependent", TEAL), ("Reproduced under denial", BLUE), ("No ordinary births", GRAY)]
    handles = [Line2D([], [], marker="o", color="none", markerfacecolor=c, markeredgecolor="none",
                      markersize=9, label=s) for s, c in labels]
    handles += [Line2D([], [], marker="D", color="none", markeredgecolor=MUTED,
                       markerfacecolor="white", label="Changed program", markersize=7),
                Line2D([], [], color=TEAL, lw=2.4, label="Intact copy from a live reader")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.057,.864), frameon=False,
               ncol=5, fontsize=10.2, handlelength=1.4, columnspacing=1.6)
    sources = [HERE.parent/"placement-01/natural", args.natural]
    for i, (s, source) in enumerate(zip(summaries, sources)):
        seed, root = s["seed"], (int(s["root_site"]), int(s["root_born"]))
        links = {((int(r["mother_site"]), int(r["mother_born"])), (int(r["child_site"]), int(r["child_born"])))
                 for r in read(source/"links.tsv") if r["seed"] == seed}
        x = .065 + .465*i
        fig.text(x, .786, f"{'Index' if i == 0 else 'Replication'} family   /   Seed {int(seed):,}",
                 fontsize=17, weight="bold")
        fig.text(x, .751, f"Founder born at tick {root[1]}   ·   {s['members']} total family members", color=MUTED)
        ax = fig.add_axes([x, .441, .405, .27])
        branch(ax, [r for r in people if r["seed"] == seed], root, links)
    fig.text(.065, .342, "Trees show the founder's continuous RSCLD branch and its first changed children. Other descendants are included below.",
             fontsize=10.8, color=MUTED)
    fig.add_artist(Line2D([.065, .945], [.305, .305], transform=fig.transFigure, color=GRID))
    fig.text(.065, .257, "Full lifetime outcomes across each entire pedigree", fontsize=16, weight="bold")
    ax = fig.add_axes([.258, .107, .587, .113])
    for i, row in enumerate(summaries):
        left, total = 0, int(row["members"])
        for key in CLASSES:
            n = int(row[key])
            width = n / total
            ax.barh(1-i, width, left=left, color=COLORS[key], height=.55)
            if width > .10:
                ax.text(left+width/2, 1-i, str(n), va="center", ha="center",
                        color=INK if key == "no_ordinary_birth" else "white", weight="bold")
            left += width
        ax.text(-.012, 1-i, f"{row['dependent']} dependent", va="center", ha="right", color=TEAL, weight="bold")
        ax.text(1.015, 1-i, f"n = {total}", va="center", color=MUTED)
        ax.text(-.33, 1-i, f"Seed {int(row['seed']):,}", va="center", weight="bold")
    ax.set(xlim=(0,1), ylim=(-.5,1.5))
    ax.axis("off")
    fig.text(.065, .052, "In seed 3,562, RSCLD reappeared in a changed branch at tick 1,757 and again required external reads. Its only child had no offspring.",
             fontsize=10.8, color=MUTED)
    fig.savefig(args.png, dpi=165, facecolor="white")


if __name__ == "__main__":
    main()
