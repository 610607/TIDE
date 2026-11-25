"""Plot per-world endpoints and arm trajectories of access-dynamics-01 (descriptive)."""
import argparse
import csv
import gzip
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ARMS = ("self", "read", "read_fetch")
COLORS = {"self": "#3b5c85", "read": "#077c72", "read_fetch": "#ad692e"}
INK, MUTED = "#1b3343", "#526978"
TITLES = {"P1": "P1  total novelty", "P2": "P2  mean change", "P3": "P3  mean ecology (bits)",
          "P4": "P4  mean new activity"}


def read(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def value(x):
    try:
        return float(x)
    except ValueError:
        return float("nan")


def quantiles(xs):
    xs = sorted(x for x in xs if x == x)
    if not xs:
        return (float("nan"),) * 3
    q = statistics.quantiles(xs, n=4, method="inclusive") if len(xs) > 1 else [xs[0]] * 3
    return q[0], statistics.median(xs), q[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=("primary", "scale", "test"), nargs="?", default="primary")
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--out", type=Path)
    a = parser.parse_args()
    analysis = a.results / {"primary": "analysis", "scale": "scale-analysis", "test": "test-analysis"}[a.set]
    endpoints = read(analysis / "endpoints.tsv")
    levels = read(analysis / "levels.tsv")
    worlds = sorted(d for d in (a.results / a.set).iterdir() if d.is_dir() and not d.name.startswith("."))

    fig = plt.figure(figsize=(14, 8.6))
    grid = fig.add_gridspec(2, 4, left=.06, right=.98, top=.86, bottom=.08, hspace=.48, wspace=.38)
    n = len(endpoints) // 3
    fig.text(.06, .95, "Does neighbor access change long-term evolutionary dynamics?", fontsize=19, weight="bold",
             color=INK)
    fig.text(.06, .905, f"{n} matched seeds per arm   /   filled: run   /   hollow: neutral shadow   /   "
                        "bars: median", fontsize=11, color=MUTED)
    for k, e in enumerate(("P1", "P2", "P3", "P4")):
        ax = fig.add_subplot(grid[0, k])
        for i, arm in enumerate(ARMS):
            rows = [r for r in endpoints if r["arm"] == arm]
            run = [value(r[e]) for r in rows]
            shadow = [value(r[f"shadow_{e}"]) for r in rows]
            jitter = [(j % 8 - 3.5) * .035 for j in range(len(rows))]
            ax.scatter([i - .17 + d for d in jitter], run, s=14, color=COLORS[arm], alpha=.8, lw=0)
            ax.scatter([i + .17 + d for d in jitter], shadow, s=14, facecolor="none", edgecolor=COLORS[arm],
                       alpha=.6, lw=.8)
            for x, ys in ((i - .17, run), (i + .17, shadow)):
                m = quantiles(ys)[1]
                ax.hlines(m, x - .13, x + .13, color=INK, lw=2)
        ax.set_xticks(range(3), ARMS)
        ax.set_title(TITLES[e], loc="left", fontsize=11, weight="bold", color=INK)
        ax.spines[["top", "right"]].set_visible(False)

    ax = fig.add_subplot(grid[1, :2])
    for arm in ARMS:
        by = {}
        for r in levels:
            if r["arm"] == arm and r["reached"] == "1":
                by.setdefault((int(r["seed"]), "run"), []).append((int(r["level"]), value(r["novelty"])))
                by.setdefault((int(r["seed"]), "shadow"), []).append((int(r["level"]), value(r["shadow_novelty"])))
        for kind, style in (("run", "-"), ("shadow", "--")):
            curves = {}
            for (seed, kk), pts in by.items():
                if kk != kind:
                    continue
                total = 0
                for L, v in sorted(pts):
                    if v != v:  # unreached level: the curve stops
                        break
                    total += v
                    curves.setdefault(L, []).append(total)
            xs = sorted(curves)
            lo, mid, hi = zip(*(quantiles(curves[x]) for x in xs)) if xs else ((), (), ())
            ax.plot(xs, mid, style, color=COLORS[arm], lw=2, label=f"{arm} {kind}")
            if kind == "run":
                ax.fill_between(xs, lo, hi, color=COLORS[arm], alpha=.15, lw=0)
    ax.set_xlabel("mean generation level")
    ax.set_title("Cumulative novelty across the window (median, interquartile band)", loc="left", fontsize=11,
                 weight="bold", color=INK)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)

    ax = fig.add_subplot(grid[1, 2:])
    for arm in ARMS:
        series = {}
        for d in worlds:
            if not d.name.startswith(arm + "-") or d.name[len(arm) + 1:].count("-"):
                continue
            for r in read(d / "bedau.tsv.gz"):
                series.setdefault(int(r["tick"]), []).append((value(r["D"]), value(r["shadow_D"])))
        xs = sorted(series)
        ax.plot(xs, [statistics.median(v[0] for v in series[x]) for x in xs], "-", color=COLORS[arm], lw=1.6,
                label=f"{arm} run")
        ax.plot(xs, [statistics.median(v[1] for v in series[x]) for x in xs], "--", color=COLORS[arm], lw=1.2,
                label=f"{arm} shadow")
    ax.set_xlabel("tick")
    ax.set_title("Genotype diversity D (median over worlds)", loc="left", fontsize=11, weight="bold", color=INK)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    out = a.out or HERE / ("access-dynamics.png" if a.set == "primary" else "access-dynamics-scale.png")
    fig.savefig(out, dpi=110)
    print(out)


if __name__ == "__main__":
    main()
