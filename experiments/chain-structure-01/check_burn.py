"""Supplementary initial-state bias check over the original observation window."""

import argparse
from collections import Counter
from pathlib import Path

from geometry import COMPACT, STRAIGHT, contact_mask, graph, unlike_mask, walks
from run import BURN, FOCAL, OBSERVED, acceptance, table


def propagate(rows, scale, thresholds, start):
    # Combine proposals to the same shape, including moves rejected by attraction.
    edges = []
    for i, row in enumerate(rows):
        counts = Counter()
        for j, cutoff in zip(row, thresholds[i]):
            counts[j] += cutoff
            counts[i] += scale - cutoff
        total = len(row) * scale
        assert sum(counts.values()) == total
        edges.append([(j, n / total) for j, n in counts.items() if n])
    p = [float(i == start) for i in range(len(rows))]
    accumulated = [0.0] * len(p)
    for step in range(1, BURN + OBSERVED + 1):
        new = [0.0] * len(rows)
        for mass, outgoing in zip(p, edges):
            for j, prob in outgoing:
                new[j] += mass * prob
        p = new
        if step == BURN:
            at_burn = p.copy()
        elif step > BURN:
            for j, v in enumerate(p):
                accumulated[j] += v
    window = [v / OBSERVED for v in accumulated]
    assert all(abs(sum(law) - 1) < 1e-12 for law in (at_burn, window))
    return at_burn, window


def map_distance(shape_law, weights, masks):
    differences = Counter()
    z = sum(weights)
    for p, w, m in zip(shape_law, weights, masks):
        differences[m] += p - w / z
    return sum(abs(v) for v in differences.values()) / 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    shapes = sorted(walks())
    rows = graph(shapes)
    masks = [contact_mask(shape) for shape in shapes]
    result = []
    for s, q in ((FOCAL[0], 1), (FOCAL[0], 4), (FOCAL[1], 4)):
        scale, thresholds = acceptance(s, q, masks, rows)
        weights = [q ** (m & unlike_mask(s)).bit_count() for m in masks]
        for label, initial in (("straight", STRAIGHT), ("compact", COMPACT)):
            at_burn, window = propagate(rows, scale, thresholds, shapes.index(initial))
            result.append((s, q, label, map_distance(at_burn, weights, masks),
                           map_distance(window, weights, masks)))
    table(args.out / "burn.tsv", ("sequence", "q", "start", "burn_map_tv", "expected_window_map_tv"),
          result)


if __name__ == "__main__":
    main()
