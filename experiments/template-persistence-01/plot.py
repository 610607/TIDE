"""Plot survival, the paired order contrast and a traced long-lived family."""
import argparse
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze import H, rows


def draw(src, dest):
    field = [r for r in rows(src / "outcomes.tsv") if r["arm"] == "fed_break"]
    snapshots = [r for r in rows(src / "survival.tsv") if (r["block"], r["arm"]) == ("both", "fed_break")]
    contrast = [r for r in rows(src / "order.tsv") if r["block"] == "both"]
    example = max(field, key=lambda p: (int(p["depth"]), int(p["last_post_return"])))
    seed = example["seed"]
    nodes = {int(r["id"]): r for r in rows(src / "chains.tsv.gz") if r["seed"] == seed and r["arm"] == "fed_break"}
    last = max(nodes.values(), key=lambda r: (int(r["depth"]), int(r["born"])))
    line = []
    while last:
        line.append(last)
        last = nodes.get(int(last["guide"]))
    line.reverse()
    teal, rust, gray, ink = "#007a70", "#af5928", "#738697", "#203441"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": ink,
                         "axes.labelcolor": ink, "xtick.color": ink, "ytick.color": ink,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(12.4, 7.45))
    fig.text(.065, .94, "How long does a first chain leave a trace?", weight="bold", fontsize=21)
    fig.text(.066, .891, f"{len(field):,} naturally assembled origins   ·   fresh pieces supplied   ·   both completed and growing chains can break",
             fontsize=12, color="#4f6874")
    ax = fig.add_axes((.081, .49, .39, .29))
    ax.set_title("A   Survival from first assembly", loc="left", weight="bold", fontsize=13, pad=14)
    for name, color, label in (("founder_death", gray, "Original chain"), ("exact_loss", teal, "Exact family")):
        losses = Counter(int(r[name]) for r in field if int(r[name]) >= 0)
        alive = len(field)
        values = []
        for t in range(H + 1):
            alive -= losses[t]
            values.append(100 * alive / len(field))
        ax.step(range(H + 1), values, where="post", lw=2, color=color, label=label)
    ax.plot([int(r["age"]) for r in snapshots], [100 * int(r["broad"]) / len(field) for r in snapshots],
            "o--", color=rust, ms=3, lw=1.4, label="Family allowing mismatches")
    ax.set(xlim=(0, H), ylim=(-2, 103), xticks=[0, 512, 1024, 1536, H], yticks=[0, 25, 50, 75, 100],
           xlabel="Encounters since first assembly", ylabel="Worlds with a living carrier (%)")
    ax.grid(axis="y", alpha=.18)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    bx = fig.add_axes((.625, .49, .33, .29))
    bx.set_title("B   Initial order and later births", loc="left", weight="bold", fontsize=13, pad=14)
    bx.axvline(0, color=gray, ls="--", lw=1)
    for i, r in enumerate(contrast):
        v, lo, hi = [100 * float(r[k]) for k in ("effect", "low95", "high95")]
        bx.plot([lo, hi], [i, i], color=teal, lw=2)
        bx.scatter(v, i, color=teal, s=25)
        bx.text(hi + .35, i, f"{v:+.2f}", va="center", color=teal, fontsize=9)
    bx.set(xlim=(-1.4, 17.5), ylim=(5.55, -.55), yticks=range(6),
           yticklabels=[f"{r['start']}–{r['end']}" for r in contrast],
           xticks=[0, 5, 10, 15], xlabel="Paired order effect (percentage points)", ylabel="Encounter window")
    bx.spines["left"].set_visible(False)
    bx.tick_params(axis="y", length=0)
    cx = fig.add_axes((.082, .115, .82, .22))
    cx.set_title(f"C   An exact family in seed {seed}   ·   each line is one intact chain", loc="left",
                 fontsize=12.5, weight="bold", pad=11)
    last_death = max(int(r["death"]) for r in line)
    for i, r in enumerate(line):
        born, death = int(r["born"]), int(r["death"])
        col = rust if i % 2 else teal
        cx.plot([born, death], [i, i], lw=3.2, color=col, solid_capstyle="butt")
        cx.scatter(born, i, s=24, color=col, zorder=3)
        if i:
            cx.plot([born, born], [i - 1, i], lw=.8, color=gray, ls=":")
    cx.axvline(int(line[0]["death"]), ls="--", lw=1., color=gray)
    cx.text(int(line[0]["death"])+12, .2, "origin broke", fontsize=9, color=gray)
    cx.set(xlim=(-15, last_death + 40), ylim=(len(line)-.45, -.65), yticks=[0, 2, 4, 6, 8],
           ylabel="Transfer depth", xlabel="Encounters since first assembly")
    cx.grid(axis="x", alpha=.14)
    fig.text(.083, .028, "Exact families alternate between the origin and its complement. Panel B compares the natural origin with a composition-preserving rotation (95% intervals).",
             fontsize=9, color="#4f6874")
    fig.savefig(dest, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    draw(a.directory, a.output)
