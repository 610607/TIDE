"""Plot the birth-direction comparison and the three transport endpoints."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

INK, SOFT, GRID = "#173542", "#47606a", "#d9e3e6"
TEAL, AMBER = "#087c73", "#aa5913"
DIRECTIONS = (("north", "#b1cbd4"), ("east", TEAL), ("south", "#efb461"), ("west", "#9e99bc"))


def style(ax):
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(GRID)
    ax.tick_params(length=0, colors=SOFT, pad=6)
    ax.set_axisbelow(True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    with (args.results / "cohorts.tsv").open() as f:
        data = {(r["cohort"], r["arm"]):r for r in csv.DictReader(f, delimiter="\t")}
    pooled = {arm:data["pooled",arm] for arm in ("east","bearing","low","high")}
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":INK,"axes.labelcolor":SOFT})
    fig = plt.figure(figsize=(13.4,8.05),facecolor="white")
    fig.text(.066,.937,"More movement brought more encounters and fewer exact copies",
             size=21,weight="bold")
    fig.text(.066,.897,"2,048 matched seeds   /   16 × 4 fields   /   2,048 ticks   /   six-byte programs",
             size=11.7,color=SOFT)
    fig.text(.066,.817,"Changing only the newborn’s direction",size=15,weight="bold")
    fig.text(.066,.776,"Direction of the intact living template relative to its executor",size=10.5,color=SOFT)
    ax=fig.add_axes([.160,.631,.388,.100])
    for y,arm in ((1,"east"),(0,"bearing")):
        row=pooled[arm]
        left=0
        for key,color in DIRECTIONS:
            val=100*int(row[key])/int(row["exact_births"])
            ax.barh(y,val,left=left,height=.51,color=color)
            if val>=8:
                ax.text(left+val/2,y,f"{val:.0f}%",ha="center",va="center",fontsize=9.5,
                        weight="bold",color="white" if key=="east" else INK)
            left+=val
    ax.set(yticks=[0,1],yticklabels=["Random at birth","East at birth"],xlim=(0,100),ylim=(-.45,1.45),xticks=[])
    ax.tick_params(length=0)
    ax.spines[:].set_visible(False)
    ax.legend(handles=[Patch(color=c,label=k.title()) for k,c in DIRECTIONS],ncol=4,frameon=False,
              loc="upper center",bbox_to_anchor=(.5,-.06),fontsize=9,handlelength=1.1)
    fig.text(.609,.776,"Exact births",size=11,weight="bold")
    fig.text(.776,.776,"Newborn used again\nas a living template¹",size=11,weight="bold")
    for y,arm in ((.701,"east"),(.649,"bearing")):
        r=pooled[arm]
        fig.text(.609,y,f"{int(r['exact_births']):,}",size=15,weight="bold")
        fig.text(.776,y,f"{int(r['template_again']):,} / {int(r['complete']):,}",size=15,weight="bold")
    fig.text(.609,.596,"¹ Among newborns with complete lifetime follow-up.",size=9.3,color=SOFT)
    fig.text(.066,.508,"Changing only the rate of passive movement",size=15,weight="bold")
    fig.text(.066,.469,"Newborns face east in all three arms. Point labels pool both seed cohorts.",color=SOFT,size=10.3)
    metrics=(("encounters_per_world","Potential donor pairs per world","{:.0f}"),
             ("productive_pair_pct","Pairs yielding an exact birth (%)","{:.2f}"),
             ("follow_on_per_world","Copies transmitting again per world¹","{:.2f}"))
    for i,(key,title,fmt) in enumerate(metrics):
        a=fig.add_axes([.068+i*.319,.177,.262,.205])
        style(a)
        vals=[float(pooled[arm][key]) for arm in ("east","low","high")]
        a.plot(range(3),vals,color=TEAL,lw=2.3,marker="o",markersize=6)
        top=max(vals)*1.25
        for j,v in enumerate(vals):
            a.text(j,v+top*.07,fmt.format(v),ha="center",color=INK,weight="bold",size=10)
        a.set(xlim=(-.20,2.20),ylim=(0,top),xticks=[0,1,2],xticklabels=["None","Low","High"])
        a.grid(axis="y",color=GRID,lw=.7)
        a.set_title(title,loc="left",fontsize=10.7,weight="bold",pad=10,color=INK)
    fig.text(.067,.090,"Low and high select each candidate edge with probability 1/64 and 1/4 per tick.",size=10,color=SOFT)
    switches=[float(pooled[arm]["supplier_switch_pct"]) for arm in ("east","low","high")]
    fig.text(.067,.055,"Among allocations whose first byte came from an unlike living donor, a later read changed source identity in "
             +", ".join(f"{x:.1f}%" for x in switches)+" (none, low, high).",size=9.6,color=SOFT)
    fig.savefig(args.png,dpi=175,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    main()
