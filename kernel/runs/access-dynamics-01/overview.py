"""One-page overview of the access-dynamics-01 results (descriptive figure).

Reads only committed analysis outputs and per-world tables; runs no simulation.
Writes access-dynamics-overview.png next to this script.
"""
import csv
import gzip
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
ARMS = ("self", "read", "read_fetch")
COLOR = {"self": "#257de0", "read": "#f47230", "read_fetch": "#00b894"}
INK, MUTED, RULE, EMPTY = "#191919", "#666666", "#e3e3e3", "#f1f1f1"
RCCCJD = "524343434a44"


def table(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def fmt_p(p):
    p = float(p)
    if p >= 0.01:
        return f"{p:.2g}"
    mant, exp = f"{p:.1e}".split("e")
    return f"{mant}×10$^{{{int(exp)}}}$"


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color=RULE, lw=0.8)
    ax.set_axisbelow(True)


def arm_axis(ax):
    ax.set_xticks(range(3), ["self", "read", "read_fetch"])
    for lbl, arm in zip(ax.get_xticklabels(), ARMS):
        lbl.set_color(INK)
    ax.set_xlim(-0.5, 2.5)


def strip(ax, rows, key):
    """Per-seed lines across arms, dots per arm, median bars."""
    by = {a: {int(r["seed"]): float(r[key]) for r in rows if r["arm"] == a} for a in ARMS}
    seeds = sorted(by["self"])
    for s in seeds:
        ax.plot(range(3), [by[a][s] for a in ARMS], color="#c9c9c9", lw=0.6, zorder=1)
    for i, a in enumerate(ARMS):
        ys = [by[a][s] for s in seeds]
        ax.scatter([i] * len(ys), ys, s=22, color=COLOR[a], edgecolor="white", lw=0.8, zorder=3)
        m = statistics.median(ys)
        ax.hlines(m, i - 0.22, i + 0.22, color=INK, lw=2.2, zorder=4)
    return by


def bracket(ax, x0, x1, y, text, bold=False):
    h = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.012
    ax.plot([x0, x0, x1, x1], [y - h, y, y, y - h], color=MUTED, lw=0.9, clip_on=False)
    ax.text((x0 + x1) / 2, y + h, text, ha="center", va="bottom", fontsize=8.6, color=INK,
            weight="bold" if bold else "normal", clip_on=False)


def presence(set_name, t, start, step, end):
    """Rows of booleans: RCCCJD in the material filtered set at each window level."""
    levels = list(range(start, end + 1, step))
    rows = []
    for d in sorted((RES / set_name).glob("read_fetch-*")):
        if not d.is_dir():
            continue
        here = {int(r["level"]) for r in table(d / "filtered.tsv.gz")
                if r["series"] == "material" and int(r["t"]) == t and r["component"] == RCCCJD}
        rows.append((int(d.name.split("-")[1]), [L in here for L in levels]))
    return levels, rows


def episodes(path):
    rows = [r for r in table(path) if r["arm"] == "read_fetch" and r["cls"] == "fetch_requiring"]
    return (sum(int(r["established"]) for r in rows), len(rows), sum(int(r["episodes"]) for r in rows),
            sum(int(r["losses"]) for r in rows), statistics.fmean(float(r["fraction"]) for r in rows))


def raster(ax, levels, rows, title, note):
    for y, (_, cells) in enumerate(rows):
        for x, on in enumerate(cells):
            ax.add_patch(Rectangle((x, len(rows) - 1 - y), 0.92, 0.84,
                                   color=COLOR["read_fetch"] if on else EMPTY, lw=0))
    ax.set_xlim(0, len(levels))
    ax.set_ylim(0, len(rows))
    ticks = [i for i, L in enumerate(levels) if L % 4096 == 0]
    ax.set_xticks([i + 0.46 for i in ticks], [f"{levels[i]:,}" for i in ticks])
    ax.set_yticks([len(rows) - 1 - i + 0.42 for i in (0, len(rows) - 1)],
                  [str(rows[0][0]), str(rows[-1][0])])
    ax.tick_params(length=0, colors=MUTED, labelsize=8.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("mean generation of the timepoint", fontsize=9, color=MUTED)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK, weight="bold")
    ax.text(0, -0.16, note, transform=ax.transAxes, fontsize=8.6, color=INK,
            va="top", linespacing=1.45)


def byte_row(ax, x, y, text, label, w=0.42, h=0.42, hi=None, face="white", edge=INK, below=False):
    for i, ch in enumerate(text):
        fc = hi.get(i, face) if hi else face
        ax.add_patch(Rectangle((x + i * w, y), w * 0.94, h, facecolor=fc, edgecolor=edge, lw=1))
        ax.text(x + i * w + w * 0.47, y + h / 2, ch, ha="center", va="center", fontsize=11,
                family="DejaVu Sans Mono", color=INK, weight="bold")
        ax.text(x + i * w + w * 0.47, y - 0.13, str(i), ha="center", va="center", fontsize=7, color=MUTED)
    if below:
        ax.text(x, y - 0.3, label, ha="left", va="top", fontsize=9, color=INK)
    else:
        ax.text(x, y + h + 0.13, label, ha="left", va="bottom", fontsize=9, color=INK)


def arrow(ax, a, b, text=None, rad=0.0, tx=None, ty=None, color=INK):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, lw=1.2, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text(tx, ty, text, fontsize=8.6, color=INK, ha="left", va="center", linespacing=1.35)


def main():
    endpoints = table(RES / "analysis" / "endpoints.tsv")
    tests = {(r["claim"], r["endpoint"]): r for r in table(RES / "analysis" / "tests.tsv")
             if r["variant"] == "primary"}
    claims = {r["claim"]: r for r in table(RES / "analysis" / "claims.tsv")}
    neutral = {(r["claim"], r["endpoint"]): r for r in table(RES / "analysis" / "neutral.tsv")}
    a0 = sorted(float(r["a0"]) for r in endpoints)

    fig = plt.figure(figsize=(16, 11.6), facecolor="white")
    fig.text(0.04, 0.965, "Does neighbor access change long-term evolutionary dynamics?  access-dynamics-01 at a glance",
             fontsize=17, weight="bold", color=INK)
    fig.text(0.04, 0.938, "Same R..CLD ancestor in three access arms, 32 matched seeds each, 32 × 32 torus, "
             "4,194,304 ticks. Tests and outcomes follow the preregistered rules; "
             "every value is read from the committed analysis files.", fontsize=10, color=MUTED)
    outcome = {c: claims[c]["outcome"] for c in ("C1", "C2", "C3")}
    fig.text(0.04, 0.914, f"C1 read vs self: {outcome['C1']}      C2 read_fetch vs read: {outcome['C2']}      "
             f"C3 read_fetch vs self: {outcome['C3']} (P4 only)", fontsize=10.5, color=INK, weight="bold")

    grid = fig.add_gridspec(2, 6, left=0.05, right=0.985, top=0.83, bottom=0.14, hspace=0.66, wspace=0.75,
                            height_ratios=[1, 0.92])

    # A. P4, paired across arms.
    ax = fig.add_subplot(grid[0, :3])
    by = strip(ax, endpoints, "P4")
    style(ax)
    arm_axis(ax)
    top = max(max(v.values()) for v in by.values())
    ax.set_ylim(0, top * 1.42)
    ax.set_ylabel("mean new activity per sample", fontsize=9.5, color=MUTED)
    ax.text(0.0, 1.11, "A   P4, Bedau mean new activity: the only endpoint that differs", transform=ax.transAxes,
            fontsize=11.5, weight="bold", color=INK)
    t1, t2, t3 = tests[("C1", "P4")], tests[("C2", "P4")], tests[("C3", "P4")]
    bracket(ax, 0, 1, top * 1.06, f"C1 on P4: {t1['outcome']} (Holm p = {fmt_p(t1['p_holm'])})")
    bracket(ax, 1, 2, top * 1.06, f"C2 on P4: {t2['outcome']}")
    bracket(ax, 0, 2, top * 1.24, f"C3 on P4: {t3['outcome']}   median paired difference "
            f"+{float(t3['median_difference']):,.0f}, Holm p = {fmt_p(t3['p_holm'])}", bold=True)
    n3 = neutral[("C3", "P4")]
    ax.text(0.0, -0.16, "Lines join one seed across arms; bars are medians. "
            f"Run-minus-shadow difference for C3: p = {fmt_p(n3['p'])} ({n3['label']}).\n"
            f"P4 is broad: a$_0$ < 0 in every world ({a0[0]:,.0f} to {a0[-1]:,.0f}), so it sums the activity of all "
            "genotypes except the few with the longest presence.\nNeutral-shadow P4 is about 415 in every arm "
            "(not drawn).", transform=ax.transAxes, fontsize=8.6, color=INK, va="top", linespacing=1.45)

    # B. MODES endpoints.
    names = {"P1": "P1  novelty (genotypes)", "P2": "P2  change per timepoint", "P3": "P3  ecology (bits)"}
    short = {"equivalent": "equiv.", "inconclusive": "inconcl.", "differs": "DIFFERS"}
    for k, e in enumerate(("P1", "P2", "P3")):
        ax = fig.add_subplot(grid[0, 3 + k])
        strip(ax, endpoints, e)
        style(ax)
        arm_axis(ax)
        ax.tick_params(axis="x", labelsize=8, rotation=0)
        ax.set_xticklabels(["self", "read", "read_\nfetch"])
        ax.set_title(names[e], loc="left", fontsize=10, weight="bold", color=INK)
        lines = [f"{c}: {short[tests[(c, e)]['outcome']]}" for c in ("C1", "C2", "C3")]
        ax.text(0.0, -0.2, "\n".join(lines), transform=ax.transAxes, fontsize=8.6, color=INK, va="top",
                linespacing=1.4)
        if k == 0:
            ax.text(0.0, 1.11, "B   MODES endpoints: no comparison differs", transform=ax.transAxes,
                    fontsize=11.5, weight="bold", color=INK)

    # C. RCCCJD in the filtered sets over time.
    sub = grid[1, :3].subgridspec(1, 2, width_ratios=[2.3, 1], wspace=0.18)
    lv, rows = presence("primary", 1024, 1024, 256, 16384)
    est, n, ep, loss, frac = episodes(RES / "analysis" / "strategy_worlds.tsv")
    ax = fig.add_subplot(sub[0, 0])
    raster(ax, lv, rows, "32 × 32, filter t = 1,024",
           f"Established in {est}/{n} worlds: {ep} establishments,\n{loss} losses; "
           f"present at {100 * frac:.1f}% of timepoints on average.")
    ax.text(0, 1.11, "C   Fetch-requiring RCCCJD in read_fetch worlds: one row per world, filled = in the "
            "persistence-filtered set", transform=ax.transAxes, fontsize=11.5, weight="bold", color=INK)
    lv, rows = presence("scale", 4096, 4096, 1024, 16384)
    est, n, ep, loss, frac = episodes(RES / "scale-analysis" / "strategy_worlds.tsv")
    ax = fig.add_subplot(sub[0, 1])
    raster(ax, lv, rows, "64 × 64, t = 4,096",
           f"Established in {est}/{n} worlds:\n{ep} establishments, {loss} losses;\n"
           f"present at {100 * frac:.0f}% of timepoints.\nLattice size and filter length\nboth differ: "
           "descriptive only.")

    # D. Mechanism schematic (code inspection).
    ax = fig.add_subplot(grid[1, 3:])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    ax.text(0, 6.15, "D   How RCCCJD borrows the second half of its copy", fontsize=11.5, weight="bold",
            color=INK, va="top")
    mint = {i: "#e8f6f1" for i in range(4)}
    byte_row(ax, 0.3, 2.0, "RCCCJD", "focal carrier (own code; J executes here)", hi=mint, below=True)
    byte_row(ax, 5.6, 2.0, "R..CLD", "east neighbor at its bearing (living or dead)", below=True)
    byte_row(ax, 0.3, 4.6, "RCC???", "its reservation (the offspring)", face="#fafafa")
    arrow(ax, (0.93, 2.5), (0.93, 4.5), "1  R reserves a free site;\n    C C C copy own bytes 0\u20132",
          tx=1.15, ty=3.95)
    arrow(ax, (2.82, 2.21), (5.52, 2.21))
    ax.text(2.95, 2.4, "2  J jumps to the neighbor's\n    offset 0 (needs fetch)", fontsize=8.6, color=INK,
            va="bottom", linespacing=1.35)
    arrow(ax, (7.1, 2.5), (2.85, 4.8), rad=0.28)
    ax.text(6.0, 5.75, "3  there, R and the dots are no-ops,\n    C L loops to copy bytes 3\u20135,\n"
            "    D divides: the offspring is RCCCJD", fontsize=8.6, color=INK, va="top", linespacing=1.35)
    ax.text(0.3, 1.15, "Fetch denied: J falls through to the local D, the copy is incomplete and the reservation "
            "is released, so no birth.\nAn RCCCJD neighbor also works: C C C copy bytes 3\u20135, J is a no-op "
            "abroad, D divides.\nMechanism from code inspection. Each of the 18 assayed first carriers made "
            "zero births with fetch denied.", fontsize=8.4, color=MUTED, va="top", linespacing=1.45)

    out = HERE / "access-dynamics-overview.png"
    fig.savefig(out, dpi=200, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
