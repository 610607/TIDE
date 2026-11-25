"""Draw the distribution of live matches and the two prospective world blocks."""
import argparse
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from controls import rows


def draw(directory, dest):
    changed = list(rows(directory / "changed.tsv"))
    summary = {(r["block"], r["stage"]): r for r in rows(directory / "summary.tsv") if r["cohort"] == "all"}
    def category(distance):
        if int(distance) < 0:
            return 0
        return 1 if int(distance) > 1 else 2
    birth, lifetime = [Counter(category(r[k]) for r in changed) for k in ("birth_distance", "min_distance")]
    ink, teal, gray = "#1e3644", "#087d70", "#7e94a0"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": ink,
                         "xtick.color": ink, "ytick.color": ink, "axes.labelcolor": ink,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (bars, table) = plt.subplots(1, 2, figsize=(12, 7.1), gridspec_kw={"width_ratios": [1, 1.32]})
    fig.subplots_adjust(left=.075, right=.97, bottom=.445, top=.765, wspace=.20)
    fig.text(.055, .929, "Could a changed reader find a living copy of its program?", size=20, weight="bold")
    fig.text(.057, .877, "1,024 untreated worlds  ·  one founder per world  ·  no supplied template or movement",
             size=12, color="#4d6670")
    bars.set_title("A   Closest matching individual", loc="left", fontsize=13, weight="bold", pad=19)
    for i in range(3):
        for offset, col, data, label in ((-.17, gray, birth, "At birth"), (.17, teal, lifetime, "Closest over lifetime")):
            n = data[i]
            bars.bar(i + offset, n, width=.30, color=col, label=label if i == 0 else None)
            bars.text(i + offset, n + .65, str(n), ha="center", color=col, weight="bold", size=10)
    bars.set(xticks=range(3), xticklabels=["No other copy\nin the world", "Two or more\nsteps away", "One step\naway"],
             ylabel="Changed readers", ylim=(0, len(changed) * 1.15))
    bars.set_axisbelow(True)
    bars.grid(axis="y", alpha=.18)
    bars.tick_params(axis="x", length=0)
    bars.legend(loc="upper center", bbox_to_anchor=(.50, -.24), frameon=False, ncol=2, handlelength=1.3)
    table.set_axis_off()
    table.set_title("B   Copying and renewal in all confirmed readers", loc="left", fontsize=13, weight="bold", pad=19)
    table.set(xlim=(0, 1), ylim=(0, 1))
    cols = (.70, .84, .97)
    for x, label in zip(cols, ("A", "B", "Total")):
        table.text(x, 1., label, ha="right", va="center", weight="bold", color=teal)
    table.text(0, 1., "Worlds with at least one event", va="center", color="#4d6670")
    data = [("readers", "Read-dependent reproducer"), ("intact", "Copied a matching live template"),
            ("start", "Its copy also required external reads"), ("renew", "Descendants replaced both roles"),
            ("repeat", "Replaced both roles twice")]
    for i, (key, label) in enumerate(data):
        y = .83 - i * .185
        table.plot([0, 1], [y + .095, y + .095], lw=.7, color="#d7e0e4")
        table.text(0, y, label, va="center", fontsize=10.5)
        for j, (x, block) in enumerate(zip(cols, ("A", "B", "pooled"))):
            table.text(x, y, f'{int(summary[block, key]["worlds"]):,}', ha="right", va="center",
                       weight="bold" if j == 2 else "normal", color=teal if j == 2 else ink, fontsize=11)
    fig.text(.55, .375, "Each block contains 512 worlds.", size=10, color="#4d6670")

    # A natural changed birth with the original matching template still alive.
    case, = [r for r in changed if r["seed"] == "26757" and r["id"] == "4648"]
    family = {r["id"]: r for r in rows(directory / "nodes.tsv.gz") if r["seed"] == case["seed"]}
    child, maker = family[case["id"]], family[case["maker"]]
    source = child["writes"].split(",")[0].split("/")
    assert child["inputs"] == child["genome"] and child["donor"] == source[5] and child["external"] == "6"
    assert int(source[2]) + 81 > int(child["born"])
    sites = list(map(int, (child["site"], maker["site"], source[1])))
    assert sites == list(range(sites[0], sites[0] + 3)) and sites[0] // 16 == sites[2] // 16
    panel = fig.add_axes((.057, .09, .91, .166))
    panel.axis("off")
    panel.set_title(f'C   A natural birth in seed {case["seed"]}, tick {child["born"]}', loc="left",
                    fontsize=13, weight="bold", pad=6)
    for i, (site, role, seq) in enumerate(zip(sites, ("Newborn", "Executor", "Live template"),
                                               (child["genome"], maker["genome"], child["inputs"]))):
        x = i * .161
        panel.add_patch(Rectangle((x, .18), .161, .68, facecolor="#e6f3ef" if i != 1 else "#eef0f1",
                                  edgecolor="#9fb1b5", lw=1))
        panel.text(x + .0805, .64, f"{role}  ·  {site}", ha="center", va="center", weight="bold")
        panel.text(x + .0805, .37, bytes.fromhex(seq).decode(), ha="center", va="center", family="monospace")
    panel.text(.52, .53, "The executor copied six bytes from its right neighbor\ninto its left neighbor. The newborn could read one step.\nIts original living template was two steps away.",
               va="center", fontsize=10.8, linespacing=1.4)
    fig.text(.057, .035, f"Panel A follows {len(changed)} changed readers across all 80 execution ticks. Panel B includes all confirmed readers regardless of parental sequence.",
             color="#4d6670", size=10)
    fig.savefig(dest, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    draw(a.directory, a.output)
