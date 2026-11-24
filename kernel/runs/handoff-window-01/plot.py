"""Draw the measured handoff opportunities and the provenance of a mixed-source copy."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from run import read

INK,SOFT,GRID="#193440","#4c626d","#dbe5e8"
TEAL,BLUE,GOLD="#11796d","#547a9a","#db9a48"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("png",type=Path)
    args=parser.parse_args()
    row=next(r for r in read(args.directory/"summary.tsv") if
             (r["cohort"],r["arm"],r["coverage"])==("pooled","all","complete"))
    count=lambda k:int(row[k])
    n=count("cases")
    sample=next(a for a in read(args.directory/"attempts.tsv") if
                a["seed"]=="20265" and a["arm"]=="east" and a["aligned"]=="0")
    trace=[s.split("/") for s in sample["trace"].split(",")]
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":INK,"axes.labelcolor":SOFT})
    fig=plt.figure(figsize=(13.8,7.6),facecolor="white")
    fig.text(.055,.925,"Most surviving templates never encountered a neighbor carrying S",size=20,weight="bold")
    fig.text(.055,.878,f"{n:,} complete observation windows after the original executor died   /   four stationary arms   /   2,048 matched seeds",
             color=SOFT,size=11)
    fig.text(.055,.787,"How far did each living template get?",size=14.5,weight="bold")
    fig.text(.055,.746,"Each row counts distinct templates. The horizontal scale is logarithmic.",color=SOFT,size=9.4)
    ax=fig.add_axes([.201,.228,.279,.457])
    opts=(("neighbor","Any living neighbor"),("s_neighbor","Neighbor carrying S"),
          ("held","Reader held an allocation"),("pointed_held","Held allocation and\npointed to template"),
          ("first_read","First aligned byte written"),("six_aligned","Six aligned reads"),("exact_birth","Exact birth"))
    for i,(col,label) in enumerate(opts):
        y=len(opts)-i-1
        v=count(col)
        ax.hlines(y,10,v,lw=2.4,color=GRID)
        ax.scatter(v,y,color=TEAL,s=36,zorder=3)
        ax.annotate(f"{v:,}",(v,y),xytext=(7,0),textcoords="offset points",va="center",size=10,weight="bold")
    ax.set(xscale="log",xlim=(10,55000),ylim=(-.65,6.65),yticks=range(7),yticklabels=[label for _,label in opts[::-1]],
           xlabel="Templates reaching stage")
    ax.set_xticks([10,100,1000,10000],["10","100","1,000","10,000"]); ax.minorticks_off()
    ax.tick_params(length=0,pad=6,colors=SOFT); ax.grid(axis="x",color=GRID,lw=.65)
    ax.spines[["top","right","left"]].set_visible(False); ax.spines["bottom"].set_color(GRID)
    fig.text(.055,.12,"First write to exact birth: {}/{} templates. One template supported two births.".format(
        count("exact_birth"),count("first_read")),size=9.6,color=SOFT)
    fig.text(.541,.787,"Where were the other carriers of S?",size=14.5,weight="bold")
    fig.text(.541,.746,"Classified over the template’s entire post-death window.",color=SOFT,size=9.4)
    dist=fig.add_axes([.542,.647,.410,.053]); dist.axis("off"); dist.set(xlim=(0,n),ylim=(0,1))
    categories=(("no_other_s","Absent from the whole field","#aebfc6"),
                ("distant_only","Present only beyond the four adjacent sites",BLUE),
                ("s_neighbor","Present at an adjacent site",TEAL))
    start=0
    for i,(k,label,color) in enumerate(categories):
        v=count(k)
        dist.add_patch(Rectangle((start,0),v,1,color=color,lw=0)); start+=v
        y=.601-i*.048
        fig.text(.542,y,"■",color=color,size=12)
        fig.text(.563,y,label,size=9.7)
        fig.text(.952,y,f"{v:,}  ({100*v/n:.1f}%)",ha="right",size=9.7,weight="bold")
    fig.text(.541,.411,"One copy finished from retained bytes",size=14.5,weight="bold")
    fig.text(.541,.369,"Seed 20,265  /  fixed bearings  /  source site 6",size=9.4,color=SOFT)
    strip=fig.add_axes([.543,.214,.407,.118]); strip.set(xlim=(0,6),ylim=(0,1)); strip.axis("off")
    for i,s in enumerate(trace):
        color=TEAL if s[3]=="o" else GOLD
        strip.add_patch(Rectangle((i+.04,.35),.90,.61,color=color,lw=0))
        strip.text(i+.49,.65,chr(int(s[5])),ha="center",va="center",size=13,color="white",weight="bold")
        strip.text(i+.49,.1,s[0],ha="center",size=9,color=SOFT)
    fig.text(.542,.173,"Read ticks. The donor died on tick 1,547. The final byte came",size=9.4,color=SOFT)
    fig.text(.542,.14,"from its former site after another program reserved it.",size=9.4,color=SOFT)
    fig.text(.055,.047,"An S instruction enables selection of a neighboring byte source. A carrier may never execute it during the observed window.",
             size=9.5,color=SOFT)
    fig.savefig(args.png,dpi=175,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    main()
