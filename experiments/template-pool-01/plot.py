"""Plot all 64 product frequencies and the pedigrees arising without a supplied chain."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze import PATTERN, REORDER, comp, rows


def plot(src, dest):
    spectrum = [r for r in rows(src / "spectra.tsv") if r["block"] == "both" and r["branch"] == "first"]
    background = list(rows(src / "background.tsv"))
    example = max(background, key=lambda r: int(r["depth"]))
    ink, teal, orange, gray = "#203846", "#007b72", "#b75a27", "#637685"
    plt.rcParams.update({"font.size": 10.5, "font.family": "DejaVu Sans", "text.color": ink,
                         "axes.labelcolor": ink, "xtick.color": ink, "ytick.color": ink,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(12.4, 6.7))
    fig.text(.065, .93, "Can a single chain change what a pool builds?", fontsize=21, weight="bold")
    fig.text(.066, .872, f"{len(background):,} matched trials   ·   64 pieces of each type   ·   160 encounters per round",
             fontsize=12, color=gray)
    ax = fig.add_axes((.075, .37, .48, .39))
    ax.set_title("A   Distribution of all first-round products", loc="left", weight="bold", pad=18, fontsize=13)
    arms = (("empty", "No chain supplied", gray), ("pattern", f"Guide {PATTERN}", teal),
            ("reorder", f"Guide {REORDER}", orange))
    for arm, label, color in arms:
        data = sorted((r for r in spectrum if r["arm"] == arm), key=lambda r: r["sequence"])
        ax.plot(range(64), [100 * float(r["pooled_share"]) for r in data], lw=1.5, color=color, label=label)
        if arm != "empty":
            seq = comp(PATTERN if arm == "pattern" else REORDER)
            i = int(seq, 2)
            value = 100 * float(data[i]["pooled_share"])
            ax.scatter(i, value, color=color, s=22, zorder=3)
            ax.text(i, value + .8, seq, ha="center", color=color, family="monospace", fontsize=10)
    ax.set(xlim=(-1, 64), ylim=(0, 22), yticks=[0, 5, 10, 15, 20], ylabel="Share of all products (%)",
           xticks=[0, 15, 31, 47, 63], xticklabels=["000000", "001111", "011111", "101111", "111111"],
           xlabel="Six-symbol product, in binary order")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=.18)
    bars = fig.add_axes((.745, .37, .225, .39))
    bars.set_title("B   Starting from free pieces", x=-.51, loc="left", weight="bold", pad=18, fontsize=13)
    counts = [sum(int(r["depth"]) >= d for r in background) for d in range(4)]
    for i, n in enumerate(counts):
        bars.barh(i, n, height=.46, color=[gray, "#61a39b", teal, "#135951"][i])
        bars.text(n + 37, i, f"{n:,}", va="center", weight="bold")
    bars.set(yticks=range(4), yticklabels=["First chain formed", "One exact transfer", "Two in succession",
                                            "Three in succession"], xlim=(0, 2160), ylim=(3.66, -.66),
             xticks=[0, 1000, 2000], xlabel="Worlds out of 2,048")
    bars.spines["left"].set_visible(False)
    bars.tick_params(axis="y", length=0)
    bars.grid(axis="x", alpha=.18)
    bars.set_axisbelow(True)
    fig.text(.066, .213, f"C   Longest observed chain of exact transfers without a supplied template   ·   seed {example['seed']}",
             fontsize=12.5, weight="bold")
    seqs, ticks = example["sequences"].split(","), example["ticks"].split(",")
    for i, (seq, tick) in enumerate(zip(seqs, ticks)):
        x = .077 + .222 * i
        fig.text(x, .126, seq, fontsize=17, family="monospace", color=teal if i % 2 else ink)
        fig.text(x, .083, f"encounter {tick}", fontsize=10, color=gray)
        if i + 1 < len(seqs):
            fig.text(x + .13, .123, "→", fontsize=22, color=gray)
    fig.savefig(dest, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    plot(a.directory, a.output)
