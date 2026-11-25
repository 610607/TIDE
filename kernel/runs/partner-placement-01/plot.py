"""Plot the paired field outcomes and the first together-only primary pedigree."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from run import rows


def draw(src, dest):
    stats = {r["arm"]: r for r in rows(src / "summary.tsv") if r["block"] == "all" and r["sample"] == "eligible"}
    branches = {(r["case"], r["arm"]): r for r in rows(src / "branches.tsv")}
    key = next(k for k, arm in branches if arm == "together" and int(branches[k, arm]["primary_via_match"])
               and not int(branches[k, "apart"]["primary"]))
    b = branches[key, "together"]
    pedigree = [r for r in rows(src / "nodes.tsv.gz") if r["case"] == key and r["arm"] == "together"]
    later = next(r for r in pedigree if r["primary"] == r["via_match"] == "1")
    by_id = {r["id"]: r for r in pedigree}
    daughter_a, daughter_b = by_id[later["donor"]], by_id[later["actor"]]
    assert daughter_a["from_match"] == "1" and daughter_b["donor"] == b["root"]
    seed, _, start = map(int, key.split("-"))
    genome = bytes.fromhex(later["genome"]).decode()
    sizes = int(stats["together"]["cases"])
    teal, ochre, grey, ink = "#087a70", "#af5b20", "#697888", "#1d303c"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": ink,
                         "axes.labelcolor": ink, "xtick.color": ink, "ytick.color": ink,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (ax, time) = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1, 1.30]})
    fig.subplots_adjust(left=.185, right=.97, top=.73, bottom=.20, wspace=.79)
    fig.text(.035, .94, "Can a changed sequence outlive its first reader?", fontsize=21, weight="bold")
    fig.text(.035, .873, f"{sizes} matched birth environments   ·   one living template delivered per treatment   ·   324 ticks of follow-up",
             fontsize=12, color="#415560")
    metrics = [("root_confirmed", "Focal reproduced and\nrequired external reads"),
               ("direct", "Direct dependent descendant\nwith the focal sequence"),
               ("primary", "Same-sequence dependent\nbirth after focal death")]
    colors = dict(ordinary=grey, apart=ochre, together=teal)
    ax.set_title("A   Outcomes per case", fontsize=13, fontweight="bold", loc="left", pad=17)
    for i, (k, _) in enumerate(metrics):
        for j, arm in enumerate(("ordinary", "apart", "together")):
            n = int(stats[arm][k])
            y = 3 * i + .67 * j
            ax.barh(y, n, height=.52, color=colors[arm])
            ax.text(n + .8, y, str(n), va="center", fontsize=9, color=colors[arm], weight="bold")
    ax.set(yticks=[.67, 3.67, 6.67], yticklabels=[label for _, label in metrics],
           xlim=(0, sizes + 5), ylim=(8, -.6), xticks=[0, 10, 20, 30, 40], xlabel="Cases")
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=.18)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[Line2D([], [], color=colors[a], lw=5, label=t) for a, t in
                       (("ordinary", "Unmodified"), ("apart", "Apart"), ("together", "Together"))],
              loc="upper left", bbox_to_anchor=(-.45, -.19), ncol=3, frameon=False,
              handlelength=1.1, columnspacing=1.2)
    time.set_title(f"B   A traced handoff in seed {seed}", fontsize=13, fontweight="bold", loc="left", pad=17)
    born = [0, 0, *(int(r["born"]) - start for r in (daughter_a, daughter_b, later))]
    labels = ["Natural focal", "Supplied match", "A  ·  focal copied match", "B  ·  copied from focal",
              "C  ·  B copied A"]
    time.axvspan(81, 188, color="#eef6f4")
    time.axvline(81, lw=1.4, color=grey, ls="--")
    for i, t in enumerate(born):
        color = grey if i == 1 else teal
        time.plot([t, t + 81], [i, i], color=color, lw=3.2, solid_capstyle="butt")
        time.scatter([t], [i], c=color, s=46, zorder=2)
        time.text(t + 3, i - .23, f"+{t}", va="center", ha="left", fontsize=9, color=color)
    time.set(xlim=(-4, 188), ylim=(4.85, -.68), yticks=range(5), yticklabels=labels,
             xticks=[0, 40, 81, 120, 160], xlabel="Ticks since the natural focal was born")
    time.tick_params(axis="y", length=0)
    time.spines["left"].set_visible(False)
    fig.text(.55, .069, f"Each line spans one lifetime. All five carry {genome}.", fontsize=10)
    fig.text(.55, .031, "The final copy used six unchanged bytes from living A.", fontsize=10)
    fig.savefig(dest, dpi=175, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    draw(a.source, a.output)
