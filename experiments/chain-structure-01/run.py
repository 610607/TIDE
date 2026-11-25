"""Enumerate the exact ensembles, then sample them using paired random proposals."""

import argparse
import csv
from collections import Counter
from fractions import Fraction
from itertools import accumulate, combinations, product
from pathlib import Path
from random import Random

from geometry import (COMPACT, LENGTH, PAIRS, STEPS, STRAIGHT, components, contact_mask,
                      graph, reverse_mask, unlike_mask, walks)

FOCAL = ("001011", "011100")
BURN = 1024
OBSERVED = 8192
FIRST_SEED = 29761
BLOCK_SIZE = 32


def table(path, header, rows):
    with path.open("w", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def verify_enumeration(shapes):
    # Independent exhaustive direction strings, filtering overlaps only at the end.
    direct = set()
    for steps in product(STEPS, repeat=LENGTH - 1):
        coords = tuple(zip(accumulate((s[0] for s in steps), initial=0),
                           accumulate((s[1] for s in steps), initial=0)))
        if len(set(coords)) == LENGTH:
            direct.add(coords)
    assert len(direct) == len(shapes) == 284 and direct == set(shapes)
    for shape in shapes:
        observed_pairs = {(i, j) for i, j in combinations(range(LENGTH), 2)
                          if j > i + 1 and (shape[j][0] - shape[i][0],
                                           shape[j][1] - shape[i][1]) in STEPS}
        observed_mask = contact_mask(shape)
        assert observed_pairs == {p for b, p in enumerate(PAIRS) if observed_mask & (1 << b)}


def map_masses(degeneracy, sequence, q):
    favored = unlike_mask(sequence)
    return {m: n * q ** (m & favored).bit_count() for m, n in degeneracy.items()}


def collapse(weights, key):
    result = Counter()
    for m, w in weights.items():
        result[key(m)] += w
    return result


def tv(left, right):
    ln, rn = sum(left.values()), sum(right.values())
    return sum(abs(Fraction(left.get(m, 0), ln) - Fraction(right.get(m, 0), rn))
               for m in left.keys() | right.keys()) / 2


def exact_tables(out, degeneracy):
    seqs = ["".join(s) for s in product("01", repeat=LENGTH) if s.count("0") == 3]
    laws = {(s, q): map_masses(degeneracy, s, q) for s in seqs for q in (1, 4)}
    by_map, by_sequence, by_pair = [], [], []
    for (s, q), masses in laws.items():
        complement = "".join("1" if bead == "0" else "0" for bead in s)
        assert masses == laws[complement, q]
        assert collapse(masses, reverse_mask) == laws[s[::-1], q]
        if q == 1:
            assert masses == degeneracy
        z = sum(masses.values())
        by_map.extend((s, q, m, degeneracy[m], w, z) for m, w in sorted(masses.items()))
        n = collapse(masses, int.bit_count)
        assert max(n) == 2
        by_sequence.append((s, q, z, n[0], n[1], n[2], float(1 - Fraction(n[0], z))))
        for b, (i, j) in enumerate(PAIRS):
            w = sum(v for m, v in masses.items() if m & (1 << b))
            by_pair.append((s, q, i + 1, j + 1, w, z, w / z))
    table(out / "maps.tsv", ("sequence", "q", "mask", "shapes", "mass", "total_mass"), by_map)
    table(out / "sequences.tsv", ("sequence", "q", "total_mass", "mass_0", "mass_1", "mass_2",
                                  "p_any_contact"), by_sequence)
    table(out / "pairs.tsv", ("sequence", "q", "i", "j", "mass", "total_mass", "probability"), by_pair)
    contrasts = []
    for q in (1, 4):
        a, b = (laws[s, q] for s in FOCAL)
        for name, key in (("indexed_map", lambda m: m),
                          ("reversal_identified", lambda m: min(m, reverse_mask(m))),
                          ("contact_count", int.bit_count)):
            d = tv(collapse(a, key), collapse(b, key))
            contrasts.append((q, name, str(d), float(d)))
    table(out / "contrast.tsv", ("q", "observable", "exact_tv", "tv"), contrasts)
    return laws


def acceptance(sequence, q, masks, rows):
    weights = [q ** (m & unlike_mask(sequence)).bit_count() for m in masks]
    scale = max(weights)
    # Every weight is a power of q. All acceptance thresholds are exact integers.
    by_state = [[min(scale, scale * weights[j] // weights[i]) for j in row]
                for i, row in enumerate(rows)]
    for i, row in enumerate(rows):
        for j, cutoff in zip(row, by_state[i]):
            assert weights[i] * cutoff == min(weights[i], weights[j]) * scale
    return scale, by_state


def sample(start, masks, rows, thresholds, draws, divisor):
    current = start
    hist = Counter()
    gained = lost = 0
    for t, (slot, uniform) in enumerate(draws):
        previous = masks[current]
        if uniform // divisor < thresholds[current][slot]:
            current = rows[current][slot]
        if t >= BURN:
            m = masks[current]
            hist[m] += 1
            gained += bool(m & ~previous)
            lost += bool(previous & ~m)
    assert sum(hist.values()) == OBSERVED
    return hist, gained, lost


def trajectories(out, shapes, masks, rows, laws):
    arms = [(FOCAL[0], 1), (FOCAL[0], 4), (FOCAL[1], 4)]
    kernels = {arm: acceptance(*arm, masks, rows) for arm in arms}
    uniform_bound = max(scale for scale, _ in kernels.values())
    starts = {"straight": shapes.index(STRAIGHT), "compact": shapes.index(COMPACT)}
    mask_ids = sorted(set(masks))
    records = []
    pooled = {}
    for seed in range(FIRST_SEED, FIRST_SEED + 2 * BLOCK_SIZE):
        block = 1 + (seed - FIRST_SEED) // BLOCK_SIZE
        rng = Random(seed)
        draws = [(rng.randrange(len(rows[0])), rng.randrange(uniform_bound))
                 for _ in range(BURN + OBSERVED)]
        for arm, (scale, thresholds) in kernels.items():
            assert uniform_bound % scale == 0
            for label, start in starts.items():
                hist, gained, lost = sample(start, masks, rows, thresholds, draws, uniform_bound // scale)
                pooled.setdefault((*arm, label, block), Counter()).update(hist)
                records.append((*arm, label, block, seed, gained, lost, *(hist[m] for m in mask_ids)))
    table(out / "runs.tsv", ("sequence", "q", "start", "block", "seed", "gain_steps",
                             "loss_steps", *(f"mask_{m}" for m in mask_ids)), records)
    diagnostics = []
    for (s, q, label, block), hist in sorted(pooled.items()):
        assert sum(hist.values()) == BLOCK_SIZE * OBSERVED
        d = tv(hist, laws[s, q])
        diagnostics.append((s, q, label, block, sum(hist.values()), float(d), int(d > Fraction(1, 40))))
    table(out / "sampler.tsv", ("sequence", "q", "start", "block", "samples", "tv", "flag_above_0.025"),
          diagnostics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    shapes = sorted(walks())
    verify_enumeration(shapes)
    masks = [contact_mask(shape) for shape in shapes]
    rows = graph(shapes)
    assert components(rows) == [len(shapes)], "Disconnected local graph: see protocol fallback"
    degeneracy = Counter(masks)
    laws = exact_tables(args.out, degeneracy)
    trajectories(args.out, shapes, masks, rows, laws)
    print(f"{len(shapes)} connected walks, {len(degeneracy)} contact maps, {len(laws)} exact ensembles")


if __name__ == "__main__":
    main()
