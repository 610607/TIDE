"""Plot archived, exploratory probe outputs; no new simulation is performed."""

import json
from pathlib import Path

import matplotlib.pyplot as plt

from diagram_style import GRAY, INK, ORANGE, TEAL


def plot_probe():
    data = json.loads(Path(__file__).with_name("probe-data.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(8, 3.5))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.77, bottom=0.2, wspace=0.38)
    panels = [
        ("fidelity_pct", "A  Exact-byte agreement", "Spawns matching current source (%)", 105),
        ("interval_spawns", "B  Birth throughput", "Final-interval spawns (thousands)", 90),
        ("age_death_pct", "C  Recorded death causes", "Cumulative deaths attributed to age (%)", 105),
    ]
    for ax, (field, title, ylabel, limit) in zip(axes, panels):
        plot_points(ax, data["runs"], field)
        ax.set(title=title, ylabel=ylabel, ylim=(0, limit), xlim=(-0.45, 1.45))
        ax.set_xticks([0, 1], ["Unrestricted\nwrites", "Claimed\nwrites"])
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E5ECEF", lw=0.7)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8)
        ax.title.set_fontsize(10)
        ax.yaxis.label.set_fontsize(8.5)
    fig.suptitle("Claimed writes change several observables at once", x=0.52, y=0.98,
                 fontsize=12, weight="bold", color=INK)
    fig.text(0.52, 0.87, "Archived round-3 probe  |  mutation = 0.003  |  five seeds per condition",
             ha="center", fontsize=9, color=GRAY)
    fig.text(0.52, 0.035, "Each point is one run; bars mark medians. Exploratory prototype results, not the fresh TIDE kernel.",
             ha="center", fontsize=8.5, color=GRAY)
    return fig


def plot_points(ax, runs, field):
    for index, (condition, color) in enumerate([("any", ORANGE), ("claimed", TEAL)]):
        subset = sorted((run for run in runs if run["write"] == condition),
                        key=lambda run: run["seed"])
        scale = 1000 if field == "interval_spawns" else 1
        values = [run[field] / scale for run in subset]
        offsets = [-0.16, -0.08, 0, 0.08, 0.16]
        ax.scatter([index + offset for offset in offsets], values, color=color,
                   edgecolor="white", linewidth=0.6, s=40, zorder=3)
        median = sorted(values)[len(values) // 2]
        ax.plot([index - 0.23, index + 0.23], [median, median], color=color,
                linewidth=1.5, zorder=2)
