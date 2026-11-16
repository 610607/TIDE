"""Static design vocabulary for the second literature pass; no simulation."""

from matplotlib.patches import Rectangle

from diagram_style import (GRAY, INK, LINE, ORANGE, PALE, PURPLE, TEAL,
                           arrow, box, canvas, label)


def graded_boundaries():
    fig, ax = canvas(height=4.75)
    ax.plot([5.05, 5.05], [0.75, 4.35], color=LINE, lw=1)
    label(ax, (2.5, 4.48), "A  Channel-dependent transmission", size=10, weight="bold")
    label(ax, (7.55, 4.48), "B  An explicit amount ledger", size=10, weight="bold")
    draw_channels(ax)
    draw_ledger(ax)
    label(ax, (5, 0.53), "An observer's inferred individual need not coincide with a material barrier or an access-permission region.",
          size=8.5)
    label(ax, (5, 0.2), "Original candidate schematic: no empirical permeability values, simulation results, or approved TIDE transitions.",
          size=8, color=GRAY)
    return fig


def draw_channels(ax):
    ax.add_patch(Rectangle((2.34, 1.17), 0.5, 2.66, facecolor=PALE,
                           edgecolor=TEAL, linewidth=1.2))
    label(ax, (2.6, 4.05), "Local interface state", size=9, color=TEAL)
    channels = ["write", "damage", "data read", "instruction fetch", "material", "signal / sensing"]
    symbols = [r"$T_{w}$", r"$T_{d}$", r"$T_{r}$", r"$T_{f}$", r"$T_{m}$", r"$T_{s}$"]
    for index, (channel, symbol) in enumerate(zip(channels, symbols)):
        y = 3.55 - index * 0.43
        label(ax, (0.12, y), channel, size=8.5, ha="left")
        arrow(ax, (1.72, y), (2.27, y), color=TEAL)
        arrow(ax, (2.91, y), (4.05, y), color=TEAL)
        label(ax, (4.45, y), symbol, size=12)
    label(ax, (2.5, 0.91), "Each channel needs its own transition semantics.", size=8.5)


def draw_ledger(ax):
    box(ax, (5.4, 2.95, 1.75, 0.64), "Available\namount Mᵢ", color=ORANGE, size=9)
    box(ax, (7.75, 2.95, 1.75, 0.64), "Neighbor\namount Mⱼ", color=ORANGE, size=9)
    arrow(ax, (7.2, 3.27), (7.7, 3.27), color=ORANGE)
    label(ax, (7.45, 3.68), "q", size=10, color=ORANGE)
    label(ax, (6.25, 2.67), "subtract q", size=8.5, color=ORANGE)
    label(ax, (8.65, 2.67), "add q", size=8.5, color=ORANGE)
    box(ax, (6.5, 1.52, 2.05, 0.61), "Bound material Bₑ", color=PURPLE, size=9)
    arrow(ax, (6.24, 2.5), (6.8, 2.18), color=PURPLE)
    label(ax, (6.11, 2.14), "build", size=8.5, color=PURPLE)
    arrow(ax, (8.6, 1.82), (9.46, 1.82), color=GRAY)
    label(ax, (9.1, 2.15), "release /\nexport", size=8, color=GRAY)
    label(ax, (7.5, 1.08), r"$\Delta\sum(M+B)=\sum S-\sum L$", size=11)
    label(ax, (7.5, 0.79), "Every source S and sink L must be named.", size=8.5)
