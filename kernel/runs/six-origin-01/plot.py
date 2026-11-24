"""Compare independent-world incidence and subsequent family outcomes in the two cohorts."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("study", type=Path)
    p.add_argument("png", type=Path)
    args = p.parse_args()
    folders = [args.study / n for n in ("pilot", "replication")]
    summaries = [{r["metric"]: int(r["worlds"]) for r in read(d/"summary.tsv")} for d in folders]
    follow = [read(d/"retention.tsv") for d in folders]
    names = ["Pilot", "Replication"]
    colors = ["#007A70", "#80538B"]
    ink, soft, grid = "#162D37", "#48606D", "#DBE3E5"
    plt.rcParams.update({"font.family":"DejaVu Sans", "text.color":ink, "font.size":11})
    fig = plt.figure(figsize=(12.8, 7.9))
    fig.text(.055,.925,"Natural inheritance from a six-byte ancestor",size=23,weight="bold")
    fig.text(.055,.87,"One independent R..CLD founder per world   ·   1,024 worlds per cohort   ·   2,048 ticks per world",color=soft)
    fig.legend([Line2D([],[],marker="o",color=c,lw=0,markersize=8) for c in colors],names,
               loc="upper left",bbox_to_anchor=(.046,.838),ncol=2,frameon=False,handlelength=1)
    fig.text(.055,.738,"Worlds with at least one observation",size=15,weight="bold")
    fig.text(.56,.738,"Offspring of changed, dependent daughters",size=15,weight="bold")
    fig.text(.055,.685,"Counts on a logarithmic scale",color=soft,size=10.5)
    fig.text(.56,.685,"Each count is a grandchild born by the field cutoff.",color=soft,size=10.5)
    ax = fig.add_axes([.217,.353,.262,.258])
    fields = [("dependent_mothers","Dependent reproducer"),
              ("primary_changed_edges","Changed dependent\nmother–daughter pair"),
              ("live_pair_changed_edges","Both births copied from\nsingle living suppliers¹")]
    for i, (key,label) in enumerate(fields):
        y = 2-i
        ax.text(-.025,y,label,ha="right",va="center",transform=ax.get_yaxis_transform(),size=9.4)
        for j, summary in enumerate(summaries):
            count = summary[key]
            dy = .15 if j == 0 else -.15
            ax.plot(count,y+dy,"o",color=colors[j],ms=6,clip_on=False)
            ax.annotate(f"{count:,}",(count,y+dy),xytext=(5,0),textcoords="offset points",
                        ha="left",va="center",color=colors[j],size=9.4)
    ax.set(xscale="log",xlim=(.85,3000),ylim=(-.43,2.45),yticks=[])
    ax.set_xticks([1,10,100,1000],["1","10","100","1,000"])
    ax.tick_params(axis="x",which="both",length=0,colors=soft)
    ax.grid(axis="x",which="major",color=grid)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    labels = ["All grandchildren", "Read-dependent\nreproducers observed", "Same sequence\nas daughter"]
    stats = []
    for records in follow:
        observed = [r for r in records if r["in_window"] == "1"]
        stats.append([len(observed),sum(r["grandchild_dependent"]=="1" for r in observed),
                      sum(r["exact_sequence"]=="1" for r in observed)])
    bars = fig.add_axes([.724,.353,.208,.258])
    for i,label in enumerate(labels):
        y = 2-i
        bars.text(-.04,y,label,ha="right",va="center",transform=bars.get_yaxis_transform(),size=9.4)
        for j, values in enumerate(stats):
            n = values[i]
            yy = y+(.15 if j == 0 else -.15)
            bars.barh(yy,n,height=.22,color=colors[j])
            bars.text(n+1,yy,str(n),va="center",size=10,color=colors[j])
    bars.set(xlim=(0,max(s[0] for s in stats)*1.16+3),ylim=(-.43,2.45))
    bars.axis("off")
    fig.text(.055,.277,"¹ Each birth received every byte unchanged from one living external individual.",size=10,color=soft)
    fig.add_artist(Line2D([.055,.945],[.242,.242],transform=fig.transFigure,color=grid))
    availability = [r for d in folders for r in read(d/"availability.tsv")]
    first = sum(r["first_has_template"]=="1" for r in availability)
    ever = sum(r["any_opening_has_template"]=="1" for r in availability)
    fig.text(.055,.19,f"{first} of {len(availability)} copies had the daughter's complete program in a neighbor at the first external read.",
             size=13.5,weight="bold")
    fig.text(.055,.146,f"A matching neighboring bank appeared during a recorded external read in {ever} of the {len(availability)} births.",
             size=10.5,color=soft)
    witness = next(r for r in read(folders[0]/"grandchildren.tsv") if r["seed"]=="19995"
                   and r["changed"]==r["both_dependent"]==r["both_single_live_intact"]=="1")
    stages = [f"{bytes.fromhex(witness[role+'_hex']).decode()} (tick {witness[role+'_born']})"
              for role in ("mother","daughter","grandchild")]
    fig.text(.055,.077,"Live donors, seed 19,995      " + "   →   ".join(stages),family="DejaVu Sans Mono",size=10.7)
    fig.savefig(args.png,dpi=175,facecolor="white")


if __name__ == "__main__":
    main()
