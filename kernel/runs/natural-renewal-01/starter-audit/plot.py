"""Draw the retrospective family census and the deadline in seed 27266."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).resolve().parent


def read(name):
    with (HERE / "results" / (name + ".tsv")).open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    families = read("families")
    ticks = [r for r in read("ticks") if r["seed"] == "27266" and r["actor"] == "3310"]
    keys = ["overlapping_pairs", "adjacent_pairs", "postdeath_peer_bytes"]
    counts = [len(families), *(sum(int(r[key]) > 0 for r in families) for key in keys)]
    # Six ordered inputs with no substitution in the only family that read from its peer.
    copies = [r for r in ticks if r["effect"] == "copy" and r["read_site"] == "17"]
    assert [int(r["read_offset"]) for r in copies] == [int(r["write_offset"]) for r in copies] == list(range(6))
    assert all(r["input"] == r["output"] for r in copies)
    assert bytes(int(r["output"]) for r in copies) == b"R.SCLD"
    assert counts[-1] == 1 and ticks[-1]["pending_op"] == "D" and ticks[-1]["effect"] == "death"
    assert ticks[-1]["allocation_after"] == "free" and ticks[-1]["written"] == "6"
    counts.append(sum(int(r["renewal_depth"]) > 0 for r in families))
    ink, teal, rust = "#20383d", "#177065", "#b14a30"
    plt.rcParams.update({"font.size": 11, "text.color": ink, "axes.labelcolor": ink,
                         "xtick.color": ink, "ytick.color": ink, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig = plt.figure(figsize=(10.4, 6.2))
    fig.text(.06,.93,"How far did the seven copying families progress?", fontsize=21, weight="bold")
    fig.text(.06,.875,"Seven untreated starter families found in 1,024 worlds with the original VM rules.",
             fontsize=11.7)
    ax = fig.add_axes([.39,.475,.52,.305])
    labels = ["Confirmed starting copy", "Two eligible descendants alive together",
              "Descendants at adjacent sites", "All six bytes written from living peer", "Renewal birth"]
    ax.barh(range(5),counts,color=["#71848a",teal,teal,teal,rust],height=.57)
    for i,n in enumerate(counts):
        ax.text(n+.10,i,str(n),va="center",weight="bold")
    ax.set(yticks=range(5), yticklabels=labels, xlim=(0,7.6), xlabel="Families")
    ax.invert_yaxis()
    ax.tick_params(length=0, pad=7)
    ax.spines[["bottom","left"]].set_visible(False)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x",color="#e1e8e8",lw=.8)
    ax.set_axisbelow(True)
    fig.text(.06,.335,"Seed 27266   ·   Two descendants at neighboring sites",fontsize=14,weight="bold")
    tx = fig.add_axes([.083,.155,.845,.12])
    reserve = next(int(r["tick"]) for r in ticks if r["effect"] == "reserve")
    death = int(ticks[-1]["tick"])
    tx.hlines(0,reserve,death,linewidth=2,color="#b3bfc0")
    tx.scatter([reserve],[0],color=ink,s=40)
    tx.annotate("Reserves site 32", (reserve,0), xytext=(0,13),textcoords="offset points",ha="left")
    for r in copies:
        t = int(r["tick"])
        tx.scatter(t,0,color=teal,s=44)
        tx.annotate(chr(int(r["output"])),(t,0),xytext=(0,12),textcoords="offset points",ha="center",
                    color=teal,weight="bold")
    tx.scatter([death],[0],color=rust,marker="X",s=80)
    tx.annotate("Death", (death,0), xytext=(0,13),textcoords="offset points",ha="center",color=rust)
    tx.set(xlim=(reserve-.4,death+.6),ylim=(-.35,.6),yticks=[],
           xticks=[reserve]+[int(r["tick"]) for r in copies]+[death],xlabel="Field tick")
    tx.spines[:].set_visible(False)
    tx.tick_params(length=0)
    fig.text(.06,.043,"The reserved bank held R.SCLD. The age limit released it with division (D) pending.", fontsize=11)
    fig.savefig(HERE / "starter-families.png", dpi=165)
    plt.close(fig)


if __name__ == "__main__":
    main()
