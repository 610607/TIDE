"""One-page overview of the lattice-size-01 primary results (descriptive figure).

Written after the frozen analysis had run. Reads only committed analysis outputs; runs no
simulation. Writes lattice-size-overview.png next to this script.
"""
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE / "results" / "analysis"
INK, MUTED, RULE = "#191919", "#666666", "#e3e3e3"
T1, T2 = "#257de0", "#f47230"          # t = 1,024 and t = 4,096
SIZES = (24, 32, 48, 64)
FLOOR = 2e-5                            # zero origins are drawn here; one origin is 8.1e-5


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


def jitter(i, n):
    return [(k - (n - 1) / 2) * 0.012 for k in range(n)]


def strip(ax, x, ys, color):
    ys = sorted(ys)
    offsets = jitter(0, len(ys))
    ax.scatter([x + o for o in offsets], ys, s=11, color=color, alpha=0.8, lw=0, zorder=2)
    m = sum(ys) / len(ys)
    ax.plot([x - 0.22, x + 0.22], [m, m], color=INK, lw=1.6, zorder=3)


def size_axis(ax):
    ax.set_xticks(range(4), [f"{s} × {s}" for s in SIZES], fontsize=8.5, color=INK)
    ax.set_xlim(-0.6, 3.6)


def e2(ax, worlds):
    for i, s in enumerate(SIZES):
        sub = [r for r in worlds if int(r["size"]) == s]
        strip(ax, i - 0.2, [float(r["E2_t1024"]) for r in sub], T1)
        strip(ax, i + 0.2, [float(r["E2_t4096"]) for r in sub], T2)
    ax.scatter([], [], s=14, color=T1, label="t = 1,024")
    ax.scatter([], [], s=14, color=T2, label="t = 4,096")
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    size_axis(ax)
    ax.set_ylim(-0.03, 1.03)
    ax.set_ylabel("share of 49 window timepoints", fontsize=9, color=MUTED)
    style(ax)
    ax.set_title("A  E2: RCCCJD in the filtered set, fixed filters\n    (dots: worlds; bar: mean)",
                 loc="left", fontsize=10, color=INK)


def e3(ax, worlds):
    for i, s in enumerate(SIZES):
        sub = [r for r in worlds if int(r["size"]) == s]
        strip(ax, i, [float(r["E3"]) for r in sub], T1)
    size_axis(ax)
    ax.set_ylim(-0.03, 1.03)
    ax.set_ylabel("share of 49 window levels", fontsize=9, color=MUTED)
    style(ax)
    ax.set_title("B  E3: a living RCCCJD carrier, no filter\n    (dots: worlds; bar: mean)",
                 loc="left", fontsize=10, color=INK)


def attribution(ax):
    parts = {r["part"]: r for r in table("attribution.tsv")}
    delta = float(table("attribution-summary.tsv")[0]["delta"])
    rows = [("Δ = E2(64, 4,096) − E2(32, 1,024)", delta, None, None),
            ("S₁₀₂₄  size, at t = 1,024", *(float(parts["S_t1"][k]) for k in ("value", "lo90", "hi90"))),
            ("S₄₀₉₆  size, at t = 4,096", *(float(parts["S_t2"][k]) for k in ("value", "lo90", "hi90"))),
            ("F₃₂  filter, at 32 × 32", *(float(parts["F_small"][k]) for k in ("value", "lo90", "hi90"))),
            ("F₆₄  filter, at 64 × 64", *(float(parts["F_large"][k]) for k in ("value", "lo90", "hi90")))]
    for y, (label, v, lo, hi) in enumerate(rows):
        if lo is not None:
            ax.plot([lo, hi], [-y, -y], color=T1, lw=2.4, solid_capstyle="round")
        ax.plot(v, -y, "o", ms=6, color=INK if lo is None else T1, mec="white", mew=1)
        ax.text(v, -y + 0.28, f"{v:+.3f}", ha="center", fontsize=8, color=INK)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks([-y for y in range(len(rows))], [r[0] for r in rows], fontsize=8.5, color=INK)
    ax.set_xlim(-0.45, 0.9)
    ax.set_ylim(-len(rows) + 0.4, 0.7)
    ax.set_xlabel("difference in mean E2 (line: 90% bootstrap interval)", fontsize=9, color=MUTED)
    style(ax, grid="x")
    ax.set_title("C  Attribution: Δ = S₄₀₉₆ + F₃₂ = S₁₀₂₄ + F₆₄", loc="left", fontsize=10, color=INK)


def origins(ax, worlds):
    means = []
    for s in SIZES:
        n = s * s
        ys = [float(r["origins_per_generation"]) for r in worlds if int(r["size"]) == s]
        zeros = sum(y == 0 for y in ys)
        shown = [y if y > 0 else FLOOR for y in sorted(ys)]
        offsets = [math.exp(o * 0.7) for o in jitter(0, len(shown))]
        ax.scatter([n * o for o in offsets], shown, s=11, color=T1, alpha=0.8, lw=0, zorder=2)
        m = sum(ys) / len(ys)
        means.append((n, m))
        ax.plot([n / 1.18, n * 1.18], [m, m], color=INK, lw=1.6, zorder=3)
        if zeros:
            ax.text(n, FLOOR / 1.6, f"{zeros} at 0", ha="center", va="top", fontsize=7.5, color=MUTED)
    n0, m0 = means[0]
    xs = [500, 4700]
    ax.plot(xs, [m0 * x / n0 for x in xs], color=MUTED, lw=1, ls="--", zorder=1)
    ax.text(4700, m0 * 4700 / n0 * 0.75, "slope 1", ha="right", va="top", fontsize=8, color=MUTED)
    slope = table("patterns.tsv")[0]["value"].split(" ")[0]
    ax.text(560, 0.6, f"log–log slope of the means: {slope}", fontsize=8.5, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([s * s for s in SIZES], [f"{s * s:,}" for s in SIZES], fontsize=8.5, color=INK)
    ax.minorticks_off()
    ax.set_xlim(480, 5000)
    ax.set_ylim(FLOOR / 5, 2)
    ax.set_xlabel("sites N", fontsize=9, color=MUTED)
    ax.set_ylabel("origins per generation", fontsize=9, color=MUTED)
    style(ax)
    ax.set_title("D  RCCCJD origins, Ḡ 4,096–16,384\n    (dots: worlds; bar: mean)", loc="left", fontsize=10, color=INK)


def main():
    worlds = table("worlds.tsv")
    fig = plt.figure(figsize=(12, 8), facecolor="white")
    grid = fig.add_gridspec(2, 2, wspace=0.42, hspace=0.45)
    e2(fig.add_subplot(grid[0, 0]), worlds)
    e3(fig.add_subplot(grid[0, 1]), worlds)
    attribution(fig.add_subplot(grid[1, 0]))
    origins(fig.add_subplot(grid[1, 1]), worlds)
    fig.suptitle("lattice-size-01: read_fetch-retain on four torus sizes, seeds 32001–32032 at each size",
                 x=0.06, ha="left", fontsize=11.5, color=INK)
    fig.savefig(HERE / "lattice-size-overview.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
