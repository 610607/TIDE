"""Plot entry, first return and reopening results for the six-bead U shape."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
INK, MUTED = "#18353c", "#53696c"
ARMS = [
    ("001011", "1", "Neutral", "#878f92", "-", 4.1),
    ("001011", "4", "001011", "#00695c", "-", 2.6),
    ("011100", "4", "011100", "#ba4b29", (0, (2, 2)), 2.3),
]


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def axis_style(ax, direction):
    ax.grid(axis=direction, color="#e1e7e7", lw=.85)
    ax.set_axisbelow(True)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0, pad=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--out", type=Path, default=HERE / "residence.png")
    args = parser.parse_args()
    curves = read(args.results / "curves.tsv")
    summaries = {(r["sequence"], r["q"]): r for r in read(args.results / "u.tsv")}
    returns = {(r["sequence"], r["q"]): float(r["prob_given_open_first"])
               for r in read(args.results / "after_open.tsv") if r["next_map"] == "6"}

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "text.color": INK, "axes.labelcolor": MUTED, "axes.titlecolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED})
    fig = plt.figure(figsize=(11.2, 7), facecolor="white")
    fig.text(.065, .925, "How long does a six-bead chain keep its U shape?", fontsize=22, weight="bold")
    fig.text(.065, .873, "The U shape has two contacts: positions 1–6 and 2–5.", fontsize=12, color=MUTED)
    handles = [Line2D([], [], color=c, lw=w, linestyle=ls, label=label)
               for _, _, label, c, ls, w in ARMS]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(.957, .895), ncol=3,
               frameon=False, handlelength=2.1, columnspacing=1.3, fontsize=11)
    for k, (title, ylabel, field) in enumerate((
            ("A   After entering the U", "Still in the same U visit", "p_residence_gt"),
            ("B   After leaving the U", "Returned to the U at least once", "p_return_gt"))):
        ax = fig.add_axes([.098 + k*.482, .50, .37, .234])
        ax.set_title(title, loc="left", fontsize=14, weight="bold", pad=13)
        for s, q, _, color, ls, lw in ARMS:
            rows = [r for r in curves if r["sequence"] == s and r["q"] == q and int(r["proposals"])]
            xs = [int(r["proposals"]) for r in rows]
            tails = [float(r[field]) for r in rows]
            ax.plot(xs, [1-v for v in tails] if k else tails, color=color, ls=ls, lw=lw)
        ax.set_xscale("log", base=2)
        ticks = [1, 4, 16, 64, 256, 1024]
        if k:
            ticks = [1, 8, 64, 512, 8192]
        ax.set_xlim(1, ticks[-1])
        ax.set_xticks(ticks, labels=[f"{t:,}" for t in ticks], fontsize=9)
        ax.set(ylim=(-.016, 1.016), yticks=[0, .25, .5, .75, 1],
               xlabel="Move proposals", ylabel=ylabel)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        axis_style(ax, "y")
    fig.text(.098, .397, "The neutral and 011100 residence curves coincide.", color=MUTED, fontsize=10)

    ax = fig.add_axes([.098, .13, .77, .16])
    ax.set_title("C   What happens after a U visit ends?", loc="left", fontsize=14, weight="bold", pad=15)
    for idx, (s, q, _, color, _, _) in enumerate(ARMS):
        values = [float(summaries[s, q]["p_return_before_open"]), returns[s, q]]
        x = [pos + (idx-1)*.20 for pos in (0, 1)]
        rects = ax.bar(x, values, width=.16, color=color)
        ax.bar_label(rects, labels=[f"{v:.1%}" for v in values], padding=3, fontsize=10)
    ax.set(xlim=(-.45, 1.45), ylim=(0, .86), yticks=[0, .25, .50, .75],
           ylabel="Probability")
    ax.set_xticks([0, 1], labels=["Regains U before all contacts open",
                                  "U is next two-contact shape after all contacts open"])
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    axis_style(ax, "y")
    fig.text(.098, .045, "Left: all U exits.   Right: only exits that lost every contact before returning.",
             fontsize=10.5, color=MUTED)
    fig.savefig(args.out, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
