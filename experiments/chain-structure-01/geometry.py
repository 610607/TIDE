"""Six-bead self-avoiding walks and reversible local bending proposals."""

from collections import Counter
from itertools import combinations

LENGTH = 6
STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))
DISPLACEMENTS = ((1, 1), (1, -1), (-1, 1), (-1, -1),
                 (2, 0), (-2, 0), (0, 2), (0, -2))
# Neighbors have opposite checkerboard parity. Index gaps must be odd.
PAIRS = tuple((i, j) for i, j in combinations(range(LENGTH), 2)
              if j - i >= 3 and (j - i) % 2 == 1)
STRAIGHT = tuple((i, 0) for i in range(LENGTH))
COMPACT = ((0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1))


def walks(path=((0, 0),)):
    if len(path) == LENGTH:
        yield path
        return
    x, y = path[-1]
    for dx, dy in STEPS:
        site = (x + dx, y + dy)
        if site not in path:
            yield from walks((*path, site))


def adjacent(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def contact_mask(shape):
    return sum(1 << bit for bit, (i, j) in enumerate(PAIRS)
               if adjacent(shape[i], shape[j]))


def unlike_mask(sequence):
    return sum(1 << bit for bit, (i, j) in enumerate(PAIRS)
               if sequence[i] != sequence[j])


def reverse_mask(mask):
    result = 0
    for bit, (i, j) in enumerate(PAIRS):
        if mask & (1 << bit):
            pair = (LENGTH - 1 - j, LENGTH - 1 - i)
            result |= 1 << PAIRS.index(pair)
    return result


def local_moves(shape):
    """One outcome per uniformly proposed (bead, displacement), including stays."""
    for i, (x, y) in enumerate(shape):
        for dx, dy in DISPLACEMENTS:
            new = (x + dx, y + dy)
            if (new in shape or (i and not adjacent(shape[i - 1], new))
                    or (i + 1 < LENGTH and not adjacent(new, shape[i + 1]))):
                yield shape
                continue
            moved = (*shape[:i], new, *shape[i + 1:])
            if i == 0:
                moved = tuple((a - new[0], b - new[1]) for a, b in moved)
            yield moved


def components(rows):
    remaining = set(range(len(rows)))
    sizes = []
    while remaining:
        pending = [remaining.pop()]
        size = 0
        while pending:
            current = pending.pop()
            size += 1
            for other in rows[current]:
                if other in remaining:
                    remaining.remove(other)
                    pending.append(other)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def graph(shapes):
    indices = {shape: i for i, shape in enumerate(shapes)}
    rows = [tuple(indices[other] for other in local_moves(shape)) for shape in shapes]
    counts = [Counter(row) for row in rows]
    for i, row in enumerate(counts):
        assert row[i] > 0
        assert sum(row.values()) == LENGTH * len(DISPLACEMENTS)
        assert all(n == counts[j][i] for j, n in row.items())
    return rows
