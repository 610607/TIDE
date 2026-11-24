"""Draw the five-byte focal outcomes and the paired six-byte transfer results."""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from study import ALPHABET, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    counts = {panel: Counter() for panel in ("control", "substitution", "permutation")}
    for row in read(args.results/"natural-summary.tsv"):
        for key in ("dependent", "reproduces_under_denial", "no_ordinary_birth"):
            counts[row["panel"]][key] += int(row[key])
    rows = {(r["slot"], r["second_source"]): r for r in read(args.results/"supplied.tsv")}
    ink, soft, green, blue, gray = "#162E38", "#496370", "#00796C", "#466797", "#D3DDE0"
    plt.rcParams.update({"font.family":"DejaVu Sans", "text.color":ink, "font.size":11})
    fig = plt.figure(figsize=(13.4,8.4), facecolor="white")
    fig.text(.06,.929,"How much sequence change can a reader inherit?",size=24,weight="bold")
    fig.text(.06,.875,"A read-dependent individual reproduced with ordinary access and had zero offspring when external reads were denied.",
             color=soft,size=11.7)
    fig.text(.06,.796,"Five-byte natural birth states",size=16,weight="bold")
    fig.text(.54,.796,"Six-byte supplied reader and donors",size=16,weight="bold")
    fig.text(.06,.755,"Each assignment was evaluated in 22 archived newborns.",color=soft)
    fig.text(.54,.755,"Each column replaces the dot in R.SCLD with one instruction.",color=soft)

    keys = ("dependent", "reproduces_under_denial", "no_ordinary_birth")
    items = [("control","Original RSCLD"),("substitution","55 single substitutions"),
             ("permutation","119 alternative orders")]
    ax = fig.add_axes([.06,.385,.422,.29])
    for i,(panel,label) in enumerate(items):
        y = 2-i
        values = counts[panel]
        total = sum(values.values())
        left = 0
        for key,color in zip(keys,(green,blue,gray)):
            width = values[key]/total
            ax.barh(y,width,left=left,color=color,height=.25)
            left += width
        ax.text(0,y+.26,label,va="bottom",weight="bold")
        ax.text(1,y+.26,f"{values['dependent']:,} / {total:,} dependent",va="bottom",ha="right",color=green)
    ax.set(xlim=(0,1),ylim=(-.43,2.62))
    ax.set_axis_off()
    for i, (label, color) in enumerate(zip(("Dependent", "Reproduced under denial", "No ordinary births"),(green,blue,gray))):
        fig.text(.06,.353-i*.035,"■",color=color,size=12)
        fig.text(.077,.353-i*.035,label,color=soft,size=10)

    ops = [op for op in ALPHABET if op != "."]
    matrix = fig.add_axes([.667,.398,.276,.264])
    measures = [("matched","paired_transmission"),("original","exact_continuation"),
                ("matched","exact_continuation")]
    row_labels = ["Dependent daughter¹", "Exact grandchild\nOriginal donor", "Exact grandchild\nMatched donor"]
    for i, ((donor,metric),label) in enumerate(zip(measures,row_labels)):
        y = 2-i
        positives = 0
        for j,op in enumerate(ops):
            result = int(rows[op,donor][metric])
            positives += result
            matrix.scatter(j,y,s=90,color=green if result else "#E1E6E8",marker="o",edgecolors="none")
        matrix.text(-.88,y,label,ha="right",va="center",size=9.6)
        matrix.text(11.05,y,f"{positives}/11",ha="left",va="center",weight="bold",color=green,size=10.2)
    for j,op in enumerate(ops):
        matrix.text(j,2.6,op,ha="center",va="center",family="DejaVu Sans Mono",weight="bold",size=12)
    matrix.set(xlim=(-.55,10.55), ylim=(-.46,2.9))
    matrix.axis("off")
    fig.text(.54,.352,"Green marks a confirmed outcome. Gray marks an absent outcome.",color=soft,size=10)
    fig.text(.54,.312,"¹ The first daughter had the same classification in both donor layouts.",color=soft,size=9.8)
    fig.add_artist(Line2D([.06,.945],[.236,.236],transform=fig.transFigure,color="#D9E2E4"))
    fig.text(.06,.184,"Where the daughter read determined what her offspring inherited",size=15,weight="bold")
    fig.text(.06,.137,"H variant",weight="bold",color=green)
    fig.text(.155,.137,"All six bytes came from the eastern donor. Switching its sequence switched the grandchild's sequence.")
    fig.text(.06,.093,"> variant",weight="bold",color=green)
    fig.text(.155,.093,"A turn redirected all six reads to the mother. Both donor layouts yielded the original sequence.")
    fig.savefig(args.png,dpi=175,facecolor="white")


if __name__ == "__main__":
    main()
