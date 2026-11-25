"""Classify live copying events and successive role replacement by individual identity."""
from collections import defaultdict
from dataclasses import dataclass

from run import AGE, FOLLOW


@dataclass(frozen=True)
class Person:
    id: int
    born: int
    genome: str
    confirmed: bool
    actor: int = -1
    donor: int = -1
    intact: bool = False
    first_read: int = -1
    donor_born: int = -1


def from_record(row, confirmed):
    child, born, actor, donor = map(int, (row["id"], row["born"], row["actor"], row["donor"]))
    trace = [part.split("/") for part in row["writes"].split(",")]
    assert len(trace) == 6
    ticks = [int(v[0]) for v in trace]
    assert ticks == sorted(set(ticks)) and ticks[-1] < born
    aligned = all(int(v[4]) == j and v[5] == trace[0][5] for j, v in enumerate(trace))
    assert donor == (int(trace[0][5]) if aligned else -1)
    inputs, product = bytes.fromhex(row["inputs"]), bytes.fromhex(row["genome"])
    assert len(inputs) == len(product) == 6
    if all(v[3] != "?" for v in trace):
        assert sum(x != y for x, y in zip(inputs, product)) == int(row["substitutions"])
    donor_born = -1
    if donor >= 0:
        _, site, start, _, _, _ = trace[0]
        donor_born = int(start)
        assert all(v[1] == site and v[2] == start and v[3] == ("s" if donor == actor else "o")
                   and donor_born < int(v[0]) <= donor_born + AGE for v in trace)
    return Person(child, born, row["genome"], confirmed, actor, donor,
                  donor >= 0 and inputs == product, ticks[0], donor_born)


class Pedigree:
    def __init__(self, people):
        self.people = {p.id: p for p in people}
        self.ancestors = {}
        self.copies = defaultdict(list)
        self.confirmed_copies = []
        for p in sorted(self.people.values(), key=lambda n: (n.born, n.id)):
            actor = self.people.get(p.actor)
            donor = self.people.get(p.donor)
            if p.intact and donor:
                assert p.genome == donor.genome and p.donor_born == donor.born
            if p.confirmed:
                ancestors = {p.id}
                for parent in (actor, donor if p.intact else None):
                    if parent and parent.confirmed and parent.genome == p.genome:
                        assert parent.born < p.born
                        ancestors.update(self.ancestors[parent.id])
                self.ancestors[p.id] = ancestors
            if p.intact and p.actor != p.donor and actor and actor.confirmed and actor.genome == p.genome:
                self.copies[p.actor].append(p)
                if p.confirmed:
                    self.confirmed_copies.append(p)

    def chains(self, start, cutoff):
        """Yield every maximal event chain. Events are identified by their child."""
        previous_reader = self.people[start.actor]
        last_death = max(previous_reader.born, start.donor_born) + AGE
        extended = False
        for child in self.confirmed_copies:
            if child.first_read <= last_death or child.born > cutoff or child.genome != start.genome:
                continue
            roles = [self.people.get(i) for i in (child.actor, child.donor)]
            if any(p is None or not p.confirmed or p.born <= last_death - AGE for p in roles):
                continue
            paths = [self.ancestors[p.id] for p in roles]
            if not all(start.actor in path for path in paths) or not any(start.id in path for path in paths):
                continue
            extended = True
            for chain in self.chains(child, cutoff):
                yield (start.id, *chain)
        if not extended:
            yield (start.id,)

    def score(self, root):
        cutoff = root.born + FOLLOW
        copies = [p for p in self.copies[root.id] if p.born <= cutoff]
        starts = [p for p in copies if p.confirmed]
        chains = [chain for p in starts for chain in self.chains(p, cutoff)]
        return len(copies), len(starts), chains
