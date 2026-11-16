"""Render original explanatory diagrams and the archived-probe chart."""

import argparse
from pathlib import Path

from diagram_style import (GRAY, INK, LINE, ORANGE, PALE, PURPLE, TEAL,
                           arrow, box, canvas, cells, label, save)
from plot_probe import plot_probe
from graded_boundaries import graded_boundaries


def substrates():
    fig, ax = canvas(height=4.2)
    for x in (3.3, 6.65):
        ax.plot([x, x], [0.45, 3.85], color=LINE, lw=1)
    label(ax, (1.6, 3.9), "A  Cellular automaton", weight="bold")
    label(ax, (4.98, 3.9), "B  Individual CPU", weight="bold")
    label(ax, (8.35, 3.9), "C  Bound reaction", weight="bold")
    draw_ca(ax)
    draw_vm(ax)
    draw_pair(ax)
    label(ax, (5, 0.18), "Original mechanism sketches; not executable programs or reproduced paper figures.",
          size=8.5, color=GRAY)
    return fig


def draw_ca(ax):
    for row in range(5):
        values = [int(abs(row - 2) + abs(col - 2) <= 1) for col in range(5)]
        cells(ax, (0.75, 1.9 + row * 0.34), values)
    label(ax, (1.6, 1.65), "Local neighborhood at t", size=9)
    arrow(ax, (1.6, 1.43), (1.6, 1.12), color=TEAL)
    box(ax, (0.44, 0.63, 2.32, 0.44), "Shared local transition f", size=9)
    label(ax, (1.6, 0.42), "The pattern is distributed across sites.", size=8.5)


def draw_vm(ax):
    box(ax, (4.32, 2.85, 1.35, 0.6), "CPU / IP", color=ORANGE)
    cells(ax, (3.65, 2.02), [1, 1, 1, 1, 1, 1, 1, 0], color=ORANGE)
    label(ax, (5, 1.76), "Addressable memory\n(instructions and data)", size=9)
    arrow(ax, (4.8, 2.4), (4.8, 2.8), color=ORANGE)
    label(ax, (5.62, 2.6), "fetch", size=8.5, color=ORANGE)
    cells(ax, (4.5, 0.77), [1, 1, 1, 0], color=ORANGE)
    arrow(ax, (4.98, 1.55), (4.98, 1.17), color=ORANGE)
    label(ax, (5.65, 1.35), "copy", size=8.5, color=ORANGE)
    label(ax, (5, 0.47), "Memory is copied before division.", size=8.5)


def draw_pair(ax):
    cells(ax, (7.15, 3.03), [1, 1, 1, 1, 1, 1, 1], color=TEAL)
    cells(ax, (7.15, 2.55), [1, 1, 1, 1, 1, 1, 1], color=PURPLE)
    for x in (7.65, 8.35, 9.05):
        ax.plot([x, x], [2.89, 3.03], color=GRAY, lw=1)
    label(ax, (8.35, 2.3), "Two strings bind", size=9)
    arrow(ax, (8.35, 2.08), (8.35, 1.8))
    box(ax, (7.08, 1.12, 2.55, 0.61), "One reaction context\nexecutes across the pair", size=9)
    arrow(ax, (8.35, 1.08), (8.35, 0.77))
    label(ax, (8.35, 0.49), "Copy / edit / cleave string products", size=8.5)


def provenance():
    fig, ax = canvas(height=4.15)
    label(ax, (5, 3.9), "Execution ownership, instruction source, and byte source can differ",
          weight="bold", size=11)
    box(ax, (0.35, 2.45, 2.3, 0.77), "B: instruction provider", color=PURPLE)
    box(ax, (0.35, 0.85, 2.3, 0.77), "C: copied-byte donor", color=TEAL)
    box(ax, (3.85, 2.45, 2.3, 0.77), "A: executing CPU", color=ORANGE)
    box(ax, (7.35, 0.85, 2.3, 0.77), "D: destination bytes\n(A's writable allocation)", color=TEAL, size=9)
    box(ax, (7.35, 2.45, 2.3, 0.77), "New execution context", color=ORANGE)
    arrow(ax, (2.7, 2.85), (3.8, 2.85), color=PURPLE)
    label(ax, (3.25, 3.33), "permitted\nfetch", size=9, color=PURPLE)
    arrow(ax, (2.7, 1.22), (7.3, 1.22), color=TEAL)
    label(ax, (5, 0.98), "permitted data read  →  permitted write", size=9, color=TEAL)
    arrow(ax, (5, 2.4), (5, 1.35), color=ORANGE, style="--")
    label(ax, (5.16, 1.95), "A executes\nthe copy", size=9, ha="left", color=ORANGE)
    arrow(ax, (6.2, 2.85), (7.3, 2.85), color=ORANGE, style="--")
    label(ax, (6.75, 3.3), "initiate\ndivision", size=9, color=ORANGE)
    arrow(ax, (8.5, 1.68), (8.5, 2.4), color=GRAY)
    label(ax, (8.68, 2.03), "activate", size=9, ha="left", color=GRAY)
    label(ax, (5, 0.43), "Record these causal channels separately; ecological roles follow controlled tests.", size=9)
    label(ax, (5, 0.16), "Generic permitted configuration; locality and the complete TIDE instruction contract remain unspecified.",
          size=8, color=GRAY)
    return fig


def scheduling():
    fig, ax = canvas(height=4.0)
    label(ax, (5, 3.75), r"One binary rule, two read-visibility semantics:  $x_i \leftarrow x_i \vee x_{i-1}$",
          size=11, weight="bold")
    label(ax, (5, 3.38), "Five-site ring; indices modulo 5; one local update per site", size=9, color=GRAY)
    initial = [1, 0, 0, 0, 0]
    parallel = [initial[i] | initial[(i - 1) % 5] for i in range(5)]
    sequential = initial.copy()
    for index in range(5):
        sequential[index] |= sequential[(index - 1) % 5]
    for x, title in [(0.6, "A  Snapshot synchronous"), (5.6, "B  In-place sweep 0 → 4")]:
        label(ax, (x + 1.7, 2.93), title, weight="bold")
        cells(ax, (x + 0.2, 2.18), initial, size=0.6, text=True)
        label(ax, (x - 0.03, 2.48), "in", size=9, ha="right")
    cells(ax, (0.8, 0.8), parallel, size=0.6, text=True)
    cells(ax, (5.8, 0.8), sequential, size=0.6, text=True)
    for i in range(5):
        arrow(ax, (1.1 + i * 0.6, 2.1), (1.1 + i * 0.6, 1.48), color=TEAL)
    label(ax, (2.3, 1.77), "all read the same input", size=8.5,
          bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})
    for i in range(4):
        arrow(ax, (6.13 + i * 0.6, 1.67), (6.66 + i * 0.6, 1.67), color=ORANGE)
    label(ax, (7.3, 1.99), "later sites see earlier writes", size=8.5, color=ORANGE)
    label(ax, (5, 0.38), "Different one-sweep results despite equal numbers of local updates.", size=9)
    label(ax, (5, 0.14), "Didactic construction, not a TIDE run. Both trajectories eventually reach 11111 under this particular rule.",
          size=8, color=GRAY)
    return fig


def measurement():
    fig, ax = canvas(height=4.25)
    label(ax, (5, 3.98), "Changing byte strings and changing replication strategies are different observations",
          size=10.5, weight="bold")
    for y, name in [(2.9, "Genotype"), (2.04, "Strategy")]:
        label(ax, (0.9, y), name, ha="right", size=9)
    for index, genome in enumerate(["g₀", "g₁", "g₂", "g₃", "g₄"]):
        x = 1.4 + index * 1.1
        box(ax, (x, 2.64, 0.65, 0.52), genome, color=GRAY)
        strategy = "S₀" if index < 4 else "S₁"
        box(ax, (x, 1.78, 0.65, 0.52), strategy,
            color=TEAL if index < 4 else ORANGE)
        arrow(ax, (x + 0.32, 2.58), (x + 0.32, 2.36), color=GRAY)
        if index < 4:
            arrow(ax, (x + 0.7, 2.9), (x + 1.04, 2.9), color=GRAY)
    label(ax, (8.1, 2.92), "Constructed descent chain", size=9)
    label(ax, (8.1, 2.02), "Mutation-free replay\nin a declared test context", size=9)
    ax.plot([1.45, 8.55], [1.15, 1.15], color=LINE, lw=2)
    ax.plot([7.7, 7.7], [0.48, 1.38], color=INK, ls="--", lw=1.2)
    ax.plot([6.5, 7.7], [1.15, 1.15], color=ORANGE, lw=3)
    ax.plot([7.7, 8.5], [1.15, 1.15], color=ORANGE, lw=2, ls=":")
    ax.plot([8.5, 8.5], [1.05, 1.25], color=GRAY, lw=1)
    ax.plot(6.5, 1.15, "o", color=ORANGE)
    label(ax, (6.5, 0.85), "late birth", size=8.5)
    label(ax, (7.7, 1.57), "observation ends", size=8.5)
    label(ax, (8.65, 0.85), "lag threshold", size=8.5)
    label(ax, (3.55, 0.83), "Still alive, but too young to assess\npersistence at the chosen lag", size=8.5)
    label(ax, (5, 0.22), "Synthetic categories and times; no measured trajectory. A new strategy still needs heredity and causal fitness tests.",
          size=8, color=GRAY)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    generators = {"soft-substrates": substrates, "replication-provenance": provenance,
                  "update-semantics": scheduling, "measurement-limits": measurement,
                  "probe-tradeoffs": plot_probe, "graded-boundaries": graded_boundaries}
    for name, generator in generators.items():
        save(generator(), name, output=args.output, preview=args.preview)
        print(f"Rendered {name}")


if __name__ == "__main__":
    main()
