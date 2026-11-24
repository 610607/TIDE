"""Draw the measured endpoints and the read/birth timeline for an observed reuse."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from run import ARMS, read

INK, SOFT, GRID = "#153441", "#4f646c", "#dbe5e8"
TEAL, AMBER, GRAY = "#13776e", "#ba6817", "#99b2bc"


def style(ax):
    ax.spines[["top","right","left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, pad=5, colors=SOFT)
    ax.set_axisbelow(True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("png",type=Path)
    args=parser.parse_args()
    rows={r["arm"]:r for r in read(args.directory/"cohorts.tsv") if r["cohort"]=="pooled"}
    link=next(r for r in read(args.directory/"links.tsv") if r["arm"]=="read" and r["complete"]=="1"
              and r["original_reuse"]=="1")
    focal=next(r for r in read(args.directory/"products.tsv") if
               (r["seed"],r["arm"],r["child_site"],r["child_born"])==
               (link["seed"],link["arm"],link["focal_site"],link["focal_born"]))
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":INK,"axes.labelcolor":SOFT})
    fig=plt.figure(figsize=(13.6,7.6), facecolor="white")
    fig.text(.062,.924,"Randomizing the read direction let executors reuse their own products",
             size=19.3,weight="bold")
    fig.text(.062,.875,"2,048 matched worlds per arm   /   stationary fields   /   fully followed newborns counted once per outcome",
             size=11,color=SOFT)
    metrics=(("original","Original executor reused it",[0,250,500],540),
             ("handoff","Another executor copied it",[0,5,10],12),
             ("after_death","New executor read it after death¹",[0,2,4],5.2))
    names=["Both east","Read randomized","Placement randomized","Both randomized"]
    for i,(key,title,xticks,limit) in enumerate(metrics):
        ax=fig.add_axes([.174+.284*i,.565,.237,.214])
        style(ax)
        ax.set_title(title,loc="left",color=INK,weight="bold",fontsize=11.1,pad=12)
        ax.set(xlim=(0,limit),ylim=(-.5,3.5),xticks=xticks,yticks=range(4),
               yticklabels=names[::-1] if i==0 else [""]*4)
        ax.grid(axis="x",color=GRID,lw=.75)
        for j,arm in enumerate(ARMS):
            y=3-j
            n=int(rows[arm][key])
            ax.barh(y,n,height=.49,color=TEAL if arm in ("read","bearing") else GRAY)
            ax.text(n+limit*.022,y,str(n),va="center",color=INK,weight="bold")
    fig.text(.062,.481,"¹ All six reads followed the original executor’s death. An individual can appear in more than one panel. Scales differ.",
             color=SOFT,size=9.6)
    fig.text(.062,.391,"One executor first copied a southern donor, then copied its eastern newborn",
             size=15.2,weight="bold")
    name=bytes.fromhex(focal["executor"]).decode()
    seq=bytes.fromhex(focal["product"]).decode()
    fig.text(.062,.345,f"Seed {int(link['seed']):,}   /   read randomized   /   executor {name} at site {link['original_site']}   /   product {seq}",
             size=10.2,color=SOFT)
    ax=fig.add_axes([.198,.123,.726,.155])
    style(ax)
    ax.set(yticks=[0,1],yticklabels=["Reading the new copy","Reading the first donor"],ylim=(-.6,1.6),xlabel="Simulation tick")
    t0,t1=int(focal["read_ticks"].split(",")[0]),int(link["next_born"])
    ax.set_xlim(t0-4,t1+10)
    ax.grid(axis="x",lw=.7,color=GRID)
    for y,r,birth,site in ((1,focal,int(focal["child_born"]),focal["child_site"]),
                           (0,link,int(link["next_born"]),link["next_site"])):
        times=list(map(int,r["read_ticks"].split(",")))
        ax.plot([times[0],birth],[y,y],color=GRID,lw=2,zorder=1)
        ax.scatter(times,[y]*6,s=34,color=TEAL,zorder=3)
        ax.scatter([birth],[y],s=58,marker="D",color=AMBER,zorder=3)
        ax.text(birth+1,y,f"Birth at site {site}",va="center",size=9.3,color=INK)
    ax.legend(handles=[Line2D([],[],linestyle="none",marker="o",color=TEAL,label="One source byte"),
                       Line2D([],[],linestyle="none",marker="D",color=AMBER,label="Exact birth")],
              loc="upper center",bbox_to_anchor=(.48,-.45),frameon=False,ncol=2,fontsize=9)
    fig.savefig(args.png,dpi=175,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    main()
