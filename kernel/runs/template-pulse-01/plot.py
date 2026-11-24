"""Draw the paired retention outcomes and an ordinary template-use witness."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream,delimiter="\t"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("results",type=Path)
    p.add_argument("png",type=Path)
    args = p.parse_args()
    summary = {(r["cohort"],r["stage"]):r for r in read(args.results/"summary.tsv")}
    use = next(r for r in read(args.results/"template-uses.tsv")
               if r["case_id"]=="19722-21-274" and r["arm"]=="ordinary")
    lives = [r for r in read(args.results/"lifetimes.tsv") if r["case_id"]==use["case_id"]
             and r["arm"]=="ordinary" and r["permission"]=="on"]
    roles = {r["role"]:r for r in lives}
    assert roles["grandchild"]["focal_births"]=="0" and use["aligned_bytes"]=="6"
    ink,soft,teal,gray,grid = "#122E38","#4F626A","#007B70","#9AA9AE","#DAE4E5"
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":ink})
    fig = plt.figure(figsize=(13.6,6.8),facecolor="white")
    fig.text(.05,.925,"One matching template, then ordinary copying",size=23,weight="bold")
    fig.text(.05,.865,"40 natural daughter birth states  ·  One intervention during the first allocation  ·  No template supplied to descendants",
             size=11.5,color=soft)
    fig.text(.05,.757,"How far did the daughter's sequence travel?",size=15,weight="bold")
    fig.text(.56,.757,"Who made the copy, and whose bytes were copied?",size=14.3,weight="bold")
    fig.text(.56,.697,"Ordinary replay in seed 19,722",color=soft,size=11)
    ax = fig.add_axes([.227,.293,.225,.347])
    for y,(key,label) in enumerate(reversed([
            ("first_birth","First allocation produced\na grandchild"),
            ("exact_grandchild","Grandchild had the\ndaughter's exact sequence"),
            ("exact_and_dependent","Exact grandchild reproduced\nand required external reads"),
            ("primary","Same sequence reached\na great-grandchild")])):
        row = summary["pooled",key]
        ax.text(-.04,y,label,ha="right",va="center",transform=ax.get_yaxis_transform(),size=10)
        for dy,arm,color in ((.15,"ordinary",gray),(-.15,"matched",teal)):
            n = int(row[arm])
            ax.barh(y+dy,n,height=.235,color=color)
            ax.text(n+.75,y+dy,str(n),va="center",color=ink if arm=="ordinary" else teal,
                    size=10,weight="bold")
    ax.set(xlim=(0,44),ylim=(-.45,3.45))
    ax.axis("off")
    fig.text(.05,.692,"■",color=gray,size=13)
    fig.text(.065,.692,"Ordinary",color=soft)
    fig.text(.15,.692,"■",color=teal,size=13)
    fig.text(.165,.692,"One matching template",color=soft)
    diagram = fig.add_axes([.56,.265,.401,.365])
    diagram.set(xlim=(0,1),ylim=(0,1))
    diagram.axis("off")

    def box(x,y,w,role,genome,sub,fill):
        diagram.add_patch(FancyBboxPatch((x,y),w,.28,boxstyle="round,pad=.013,rounding_size=.025",
                          facecolor=fill,edgecolor=grid))
        diagram.text(x+.022,y+.214,role,size=9,color=soft)
        diagram.text(x+.022,y+.127,genome,size=15,family="DejaVu Sans Mono",weight="bold")
        diagram.text(x+.022,y+.046,sub,size=9,color=soft)

    box(.015,.607,.405,f"Copier at site {use['copier_site']}",
        bytes.fromhex(roles["daughter"]["genome_hex"]).decode(),"Ran the copy instructions","#F1F5F5")
    box(.015,.09,.405,f"Template at site {use['template_site']}",
        bytes.fromhex(use["template_hex"]).decode(),"Supplied six bytes","#EAF5F1")
    box(.626,.349,.353,f"Product at site {use['product_site']}",
        bytes.fromhex(use["product_hex"]).decode(),f"Born at tick {use['product_born']}","#EAF5F1")
    for y,dest,c in ((.745,.54,gray),(.229,.45,teal)):
        diagram.annotate("",xy=(.609,dest),xytext=(.435,y),arrowprops={"arrowstyle":"->","color":c,"lw":1.7})
    fig.add_artist(plt.Line2D([.05,.95],[.229,.229],transform=fig.transFigure,color=grid))
    fig.text(.05,.165,"After withdrawal",size=12,weight="bold")
    pilot,rep = summary["pilot","primary"], summary["replication","primary"]
    fig.text(.05,.107,f"Exact great-grandchild in {pilot['matched']}/{pilot['pairs']} pilot cases and {rep['matched']}/{rep['pairs']} replication cases.",
             size=10.6,color=soft)
    fig.text(.56,.165,"A copy without a parent–child edge from the template",size=11.8,weight="bold")
    fig.text(.56,.107,f"The individual at site {use['template_site']} produced zero offspring in its own lifetime.",size=10.4,color=soft)
    fig.savefig(args.png,dpi=170,facecolor="white")


if __name__=="__main__":
    main()
