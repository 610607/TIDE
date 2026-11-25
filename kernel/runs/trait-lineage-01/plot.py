"""Plot world incidence and the longest changed, post-root behavioral pedigree."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from run import CONTROL, read

INK, MUTED, TEAL, BLUE, GOLD = "#1b3343", "#526978", "#077c72", "#3b5c85", "#ad692e"


def main(directory, output):
    pooled, = [r for r in read(directory/"summary.tsv") if r["cohort"]=="pooled"]
    roots = [r for r in read(directory/"roots.tsv") if int(r["seed"])!=CONTROL and r["primary"]=="1"]
    example = max(roots, key=lambda r:(len(r["witness"].split(",")),-int(r["seed"]),-int(r["root"])))
    people = {r["id"]:r for r in read(directory/"nodes.tsv.gz") if r["seed"]==example["seed"]}
    path = [people[k] for k in example["witness"].split(",")]
    fig,(left,right)=plt.subplots(1,2,figsize=(13.2,5.1),gridspec_kw={"width_ratios":[1,1.35]})
    fig.subplots_adjust(left=.22,right=.97,bottom=.24,top=.73,wspace=.63)
    fig.text(.035,.93,"How long does an inherited reading requirement last?",fontsize=21,weight="bold",color=INK)
    fig.text(.035,.85,"1,024 new stationary worlds   /   8,192 ticks per world   /   dependence tested by removing read access",
             fontsize=11,color=MUTED)
    left.set_title("A   Worlds meeting each condition",loc="left",weight="bold",fontsize=12,color=INK,pad=15)
    fields=("confirmed_worlds","changed_worlds","primary_worlds","post_nonroot_genome_worlds")
    labels=("Confirmed read dependence","Two linked programs differ","Changed path outlives root¹","Later program differs from root¹")
    values=[int(pooled[k]) for k in fields]
    for y,v in enumerate(values):
        left.hlines(y,0,v,color="#cbdbdc",lw=4)
        left.plot(v,y,"o",color=TEAL,ms=8)
        left.annotate(f"{v:,}",(v,y),xytext=(8,0),textcoords="offset points",va="center",color=INK,weight="bold")
    left.set_xscale("symlog",linthresh=1)
    left.set(xlim=(-.06,4000),ylim=(3.6,-.6),yticks=range(4),yticklabels=labels,xlabel="Worlds (log scale above 1)")
    left.set_xticks([0,1,10,100,1000],["0","1","10","100","1,000"])
    right.set_title(f"B   One confirmed pedigree (seed {example['seed']})",loc="left",weight="bold",fontsize=12,color=INK,pad=15)
    root=path[0]
    root_death=int(root["born"])+81
    right.axvline(root_death,ls="--",lw=1.3,color=GOLD)
    right.text(root_death+2,-.52,"Root dies",color=GOLD,fontsize=9)
    labels=[]
    for y,p in enumerate(path):
        birth=int(p["born"]); color=BLUE if p["genome"]==root["genome"] else TEAL
        right.plot((birth,birth+81),(y,y),lw=5,color=color,alpha=.55,solid_capstyle="butt")
        right.plot(birth,y,"o",color=color,ms=8)
        right.annotate(str(birth),(birth,y),xytext=(0,8),textcoords="offset points",ha="center",color=INK,fontsize=9)
        seq=bytes.fromhex(p["genome"]).decode("ascii")
        labels.append(f"{seq}   site {p['site']}")
    right.set(yticks=range(len(path)),yticklabels=labels,ylim=(len(path)-.4,-.8),xlabel="Tick (dot at birth, line through death)")
    for ax in (left,right):
        ax.spines[["top","right","left"]].set_visible(False)
        ax.tick_params(axis="y",length=0,pad=5,labelsize=10)
        ax.grid(axis="x",alpha=.14)
        ax.set_axisbelow(True)
    fig.text(.035,.065,"¹ A confirmed descendant must be born after the first carrier dies. The final row also requires that descendant to carry different bytes.",
             fontsize=10,color=MUTED)
    fig.savefig(output,dpi=160,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    main(a.directory,a.output)
