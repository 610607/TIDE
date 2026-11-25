"""Measure contact residence and recurrence in the existing six-bead chain."""

import argparse
from bisect import bisect_right
from collections import Counter
from itertools import accumulate
from pathlib import Path
from random import Random
import sys

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chain-structure-01"))
from geometry import COMPACT, PAIRS, components, contact_mask, graph, unlike_mask, walks
from run import FOCAL, acceptance, table, verify_enumeration

U = contact_mask(COMPACT)
PAIR_BIT = 1 << PAIRS.index((1, 4))
SEED = 29825
BLOCK = 32
STEPS = 32768
WINDOW = 128
HORIZON = 8192
ARMS = ((FOCAL[0], 1), (FOCAL[0], 4), (FOCAL[1], 4))


def num(x):
    return format(x, ".12g")


def symmetry_class(shape):
    images = []
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                images.append(tuple((sx * y, sy * x) if swap else (sx * x, sy * y)
                                    for x, y in shape))
    return min(images)


def move_counts(rows, scale, thresholds):
    counts = np.zeros((len(rows), len(rows)), dtype=np.int64)
    for i, row in enumerate(rows):
        for j, cutoff in zip(row, thresholds[i]):
            counts[i, j] += cutoff
            counts[i, i] += scale - cutoff
    assert np.all(counts.sum(axis=1) == len(rows[0]) * scale)
    return counts


def boundary_law(flows, to_set):
    entries = flows[np.ix_(~to_set, to_set)].sum(axis=0)
    return entries / entries.sum()


def survey_targets(masks, classes, weights, counts, flows):
    targets = [(f"map_{m}", masks == m) for m in sorted(set(masks))]
    targets.append(("pair_2_5", (masks & PAIR_BIT) != 0))
    moving_flux = flows.sum(axis=1) - flows.diagonal()
    denominator = counts[0].sum()
    for name, target in targets:
        crossing = flows[np.ix_(target, ~target)].sum()
        assert crossing == flows[np.ix_(~target, target)].sum() and crossing > 0
        mass = weights[target].sum()
        on_mean = mass * denominator / crossing
        off_mean = (weights.sum() - mass) * denominator / crossing
        occupancy = mass / weights.sum()
        assert np.isclose(occupancy, on_mean / (on_mean + off_mean))
        yield (name, sum(target), len({c for c, member in zip(classes, target) if member}),
               occupancy, on_mean, off_mean, moving_flux[target].sum() / crossing,
               moving_flux[~target].sum() / crossing)


def passage(matrix, flows, starting_set, expected_mean):
    # At t=0 a crossing has just placed the chain on the measured side.
    sub = matrix[np.ix_(starting_set, starting_set)]
    initial = boundary_law(flows, starting_set)
    mean_times = spsolve(csr_matrix(np.eye(len(sub)) - sub), np.ones(len(sub)))
    assert np.isclose(initial @ mean_times, expected_mean, atol=1e-8, rtol=1e-10)
    forward = csr_matrix(sub.T)
    vector = initial.copy()
    points = {0: 1.0}
    median = None
    previous = 1.0
    for t in range(1, HORIZON + 1):
        vector = forward @ vector
        tail = vector.sum()
        assert 0 <= tail <= previous + 1e-13
        previous = tail
        if median is None and tail <= .5:
            median = t
        # Dense near short visits, then retain a grid of ~16 points per doubling.
        if t % (1 << max(0, t.bit_length() - 5)) == 0:
            points[t] = tail
    assert median is not None and WINDOW in points
    return points, median


def hitting_law(matrix, boundary, values):
    """Expected boundary values when first hitting a member of boundary."""
    interior = ~boundary
    result = np.zeros((len(matrix), values.shape[1]))
    result[boundary] = values
    operator = csr_matrix(np.eye(interior.sum()) - matrix[np.ix_(interior, interior)])
    rhs = matrix[np.ix_(interior, boundary)] @ values
    result[interior] = spsolve(operator, rhs).reshape(rhs.shape)
    assert np.max(np.abs(matrix[interior] @ result - result[interior])) < 1e-12
    assert np.min(result) >= -1e-12 and np.max(result) <= 1 + 1e-12
    assert np.allclose(result.sum(axis=1), 1, atol=1e-11, rtol=0)
    return result


def return_routes(matrix, flows, masks):
    target, opened = masks == U, masks == 0
    double_ids = sorted(m for m in set(masks.tolist()) if m.bit_count() == 2)
    double = np.isin(masks, double_ids)
    identity = masks[double, None] == double_ids
    next_double = hitting_law(matrix, double, identity)
    # Extend boundary values back to the first exit. An open-state hit passes
    # along that specific shape's probabilities for the next double contact.
    boundary = opened | target
    values = np.zeros((len(matrix), 1 + len(double_ids)))
    values[target, 0] = 1
    values[opened, 1:] = next_double[opened]
    outcomes = hitting_law(matrix, boundary, values[boundary])
    fractions = boundary_law(flows, ~target) @ outcomes[~target]
    opened_first = sum(fractions[1:])
    assert np.isclose(fractions[0] + opened_first, 1)
    return fractions[0], opened_first, zip(double_ids, fractions[1:] / opened_first)


def observed_run(initial, rows, thresholds, divisor, draws, is_target):
    """Exclude the initial partial interval and crossing starts too close to the end."""
    state = initial
    present = is_target[state]
    crossings = []
    for t, (slot, uniform) in enumerate(draws, start=1):
        if uniform // divisor < thresholds[state][slot]:
            state = rows[state][slot]
        if is_target[state] != present:
            present = is_target[state]
            crossings.append((t, present))
    totals, eligible, successes = Counter(), Counter(), Counter()
    for idx, (t, entered) in enumerate(crossings):
        totals[entered] += 1
        if t + WINDOW > len(draws):
            continue
        eligible[entered] += 1
        duration = crossings[idx + 1][0] - t if idx + 1 < len(crossings) else len(draws) - t + 1
        successes[entered] += (duration > WINDOW) if entered else (duration <= WINDOW)
    return [totals[True], totals[False], eligible[True], successes[True], eligible[False], successes[False]]


def simulate(out, masks, rows, models, predictions):
    raw, blocks = [], {}
    largest_scale = max(model[0] for model in models.values())
    is_target = [m == U for m in masks]
    for seed in range(SEED, SEED + 2 * BLOCK):
        block = 1 + (seed - SEED) // BLOCK
        rng = Random(seed)
        draws = [(rng.randrange(len(rows[0])), rng.randrange(largest_scale)) for _ in range(STEPS)]
        for (sequence, q), (scale, thresholds, cumulative) in models.items():
            # A separate stream gives an integer ticket in the arm's stationary law.
            ticket = Random(seed + 1000000).randrange(cumulative[-1])
            initial = bisect_right(cumulative, ticket)
            assert largest_scale % scale == 0
            values = observed_run(initial, rows, thresholds, largest_scale // scale, draws, is_target)
            raw.append((sequence, q, block, seed, initial, *values))
            key = (sequence, q, block)
            blocks.setdefault(key, np.zeros(4, dtype=int))
            blocks[key] += values[2:]
    table(out / "runs.tsv", ("sequence", "q", "block", "seed", "initial_state", "entries", "exits",
                             "eligible_entries", "long_visits", "eligible_exits", "prompt_returns"), raw)
    block_rows = []
    for (s, q, block), counts in sorted(blocks.items()):
        for i, name in enumerate(("residence_gt_128", "return_le_128")):
            n, successes = counts[2*i:2*i+2]
            assert n > 0
            expected = predictions[s, q][i]
            delta = successes / n - expected
            block_rows.append((s, q, block, name, n, successes, num(successes/n), num(expected),
                               num(delta), int(abs(delta) > .04)))
    table(out / "blocks.tsv", ("sequence", "q", "block", "endpoint", "eligible", "successes",
                               "fraction", "predicted", "difference", "flag"), block_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "results")
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    shapes = sorted(walks())
    verify_enumeration(shapes)
    rows = graph(shapes)
    assert components(rows) == [len(shapes)]
    masks = np.array([contact_mask(s) for s in shapes])
    classes = [symmetry_class(s) for s in shapes]
    target = masks == U
    models, predictions = {}, {}
    survey, curves, summary, routes = [], [], [], []
    for s, q in ARMS:
        weights = [q ** (unlike_mask(s) & int(m)).bit_count() for m in masks]
        scale, thresholds = acceptance(s, q, masks.tolist(), rows)
        models[s, q] = (scale, thresholds, list(accumulate(weights)))
        counts = move_counts(rows, scale, thresholds)
        weights = np.array(weights)
        flows = weights[:, None] * counts
        assert np.array_equal(flows, flows.T)
        matrix = counts / counts[0].sum()
        targets = list(survey_targets(masks, classes, weights, counts, flows))
        for name, count, orbits, *statistics in targets:
            survey.append((s, q, name, count, orbits, *map(num, statistics)))
        u_stats = next(row for row in targets if row[0] == f"map_{U}")
        inside, median_on = passage(matrix, flows, target, u_stats[4])
        outside, median_off = passage(matrix, flows, ~target, u_stats[5])
        # Every move out of an indexed U opens the ends and keeps the 2–5 contact.
        # Its shape-independent exit hazard gives a second residence distribution.
        assert np.all(matrix[np.ix_(target, (masks != PAIR_BIT) & ~target)] == 0)
        hazards = matrix[np.ix_(target, ~target)].sum(axis=1)
        assert np.allclose(hazards, 1 / u_stats[4])
        assert all(abs(tail - (1 - hazards[0])**t) < 1e-12 for t, tail in inside.items())
        predictions[s, q] = (inside[WINDOW], 1 - outside[WINDOW])
        for t, tail in inside.items():
            curves.append((s, q, t, num(tail), num(outside[t])))
        direct, opened_first, destinations = return_routes(matrix, flows, masks)
        summary.append((s, q, median_on, median_off, num(inside[WINDOW]), num(1-outside[WINDOW]),
                        num(direct), num(opened_first)))
        routes.extend((s, q, m, num(prob)) for m, prob in destinations)
    table(out / "targets.tsv", ("sequence", "q", "target", "shapes", "symmetry_classes", "occupancy",
                                "mean_residence", "mean_return", "mean_residence_moves", "mean_return_moves"), survey)
    table(out / "curves.tsv", ("sequence", "q", "proposals", "p_residence_gt", "p_return_gt"), curves)
    table(out / "u.tsv", ("sequence", "q", "median_residence", "median_return", "p_residence_gt_128",
                          "p_return_le_128", "p_return_before_open", "p_open_before_return"), summary)
    table(out / "after_open.tsv", ("sequence", "q", "next_map", "prob_given_open_first"), routes)
    simulate(out, masks.tolist(), rows, models, predictions)


if __name__ == "__main__":
    main()
