"""Audit complete natural fields, score both role replacements and retain all denominators."""
import argparse
import csv
import gzip
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path

from controls import archive, fixture, rows
from pedigree import Pedigree, from_record
from run import ENROLL, FIRST, FOLLOW, SPLIT, STOP


def save(path, columns, data):
    with path.open("w", newline="") as stream:
        out = csv.DictWriter(stream, columns.split(), delimiter="\t", lineterminator="\n")
        out.writeheader()
        out.writerows(data)


STAGES = ("readers", "at_birth", "contact", "read_match", "intact", "start", "renew", "repeat")
BROAD = tuple(k for k in STAGES if k not in ("at_birth", "contact", "read_match"))
CHANGED_FIELDS = ("seed id born site maker maker_genome genome ordinary_births blocked at_birth contact_ticks "
                  "matching_reads first_contact first_read birth_distance min_distance anywhere_ticks "
                  "live_donor_births intact_births starts depth")
START_FIELDS = "seed reader changed child donor first_read born depth chain"


def scan(w, data, contact, changed_rows, start_rows):
    seed = int(w["seed"])
    score = {"seed": seed}
    assert 1 + int(w["births"]) - int(w["deaths"]) == int(w["living"])
    assert int(w["horizon"]) == ENROLL + FOLLOW
    people = []
    for row in data.values():
        tested = int(row["denied_births"]) >= 0
        if int(row["born"]) <= ENROLL + FOLLOW:
            assert tested == (int(row["exposed_births"]) > 0)
        passed = tested and int(row["ordinary_births"]) > 0 and row["denied_births"] == "0" and int(row["blocked"]) > 0
        assert passed == (row["confirmed"] == "1")
        people.append(from_record(row, passed))
    pedigree = Pedigree(people)
    totals = {"changed": Counter(), "all": Counter()}
    children = defaultdict(list)
    for p in people:
        children[p.actor].append(p)
    for root in people:
        if not root.confirmed or root.born > ENROLL:
            continue
        maker = pedigree.people.get(root.actor)
        changed = bool(maker and maker.confirmed and maker.genome != root.genome)
        copies, starts, chains = pedigree.score(root)
        depth = max((len(c) - 1 for c in chains), default=0)
        stages = dict(readers=1, intact=int(copies > 0), start=int(starts > 0), renew=int(depth >= 1), repeat=int(depth >= 2))
        totals["all"].update(stages)
        totals["all"]["depth"] = max(depth, totals["all"]["depth"])
        for chain in chains:
            child = pedigree.people[chain[0]]
            start_rows.append(dict(seed=seed, reader=root.id, changed=int(changed), child=child.id, donor=child.donor,
                                   first_read=child.first_read, born=child.born, depth=len(chain) - 1,
                                   chain=",".join(map(str, chain))))
        if not changed:
            continue
        opportunity = contact.pop(root.id)
        observed = {k: int(v) for k, v in opportunity.items() if k not in ("seed", "id")}
        assert 0 <= observed["matching_reads"] <= observed["contact_ticks"] <= 80
        assert observed["contact_ticks"] <= observed["anywhere_ticks"] <= 80
        assert (observed["min_distance"] >= 1) == (observed["anywhere_ticks"] > 0)
        assert (observed["first_contact"] > root.born) == (observed["contact_ticks"] > 0)
        assert (observed["first_read"] > root.born) == (observed["matching_reads"] > 0)
        if copies:
            assert observed["matching_reads"] >= copies * 6
        stages.update(at_birth=observed["at_birth"], contact=int(observed["contact_ticks"] > 0),
                      read_match=int(observed["matching_reads"] > 0))
        assert not stages["at_birth"] or stages["contact"]
        totals["changed"].update(stages)
        totals["changed"]["depth"] = max(depth, totals["changed"]["depth"])
        row = data[root.id]
        assert len(children[root.id]) == int(row["ordinary_births"])
        changed_rows.append(dict(seed=seed, id=root.id, born=root.born, site=row["site"], maker=root.actor,
                                 maker_genome=maker.genome, genome=root.genome, ordinary_births=row["ordinary_births"],
                                 blocked=row["blocked"], **observed, intact_births=copies, starts=starts, depth=depth,
                                 live_donor_births=sum(p.donor >= 0 and p.donor != root.id for p in children[root.id])))
    assert not contact
    for group, stages in (("changed", STAGES), ("all", BROAD)):
        for k in (*stages, "depth"):
            score[group + "_" + k] = totals[group][k]
    return score


def main(directory):
    archive()
    fixture()
    worlds = list(rows(directory / "world.tsv"))
    assert [int(w["seed"]) for w in worlds] == list(range(FIRST, STOP))
    contacts = defaultdict(dict)
    for c in rows(directory / "contacts.tsv"):
        contacts[int(c["seed"])][int(c["id"])] = c
    changed, starts, endpoints = [], [], []
    with gzip.open(directory / "nodes.tsv.gz", "rt") as stream:
        groups = groupby(csv.DictReader(stream, delimiter="\t"), lambda r: int(r["seed"]))
        entry = next(groups, None)
        for w in worlds:
            seed = int(w["seed"])
            data = {}
            if entry and entry[0] == seed:
                data = {int(r["id"]): r for r in entry[1]}
                entry = next(groups, None)
            endpoints.append(scan(w, data, contacts.pop(seed, {}), changed, starts))
        assert entry is None and not contacts
    save(directory / "changed.tsv", CHANGED_FIELDS, changed)
    save(directory / "starts.tsv", START_FIELDS, starts)
    save(directory / "endpoints.tsv", " ".join(endpoints[0]), endpoints)
    summary = []
    for block, lo, hi in (("A", FIRST, SPLIT), ("B", SPLIT, STOP), ("pooled", FIRST, STOP)):
        entries = [e for e in endpoints if lo <= e["seed"] < hi]
        sample = [w for w in worlds if lo <= int(w["seed"]) < hi]
        counts = Counter(w["status"] for w in sample)
        for group, stages in (("changed", STAGES), ("all", BROAD)):
            for stage in stages:
                key = group + "_" + stage
                summary.append(dict(block=block, cohort=group, stage=stage, total_worlds=len(entries),
                                    worlds=sum(e[key] > 0 for e in entries), readers=sum(e[key] for e in entries),
                                    depth=max(e[group + "_depth"] for e in entries),
                                    births=sum(int(w["births"]) for w in sample),
                                    reproducing=counts["reproducing"], stagnant=counts["stagnant"], extinct=counts["extinct"]))
    save(directory / "summary.tsv", " ".join(summary[0]), summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    main(parser.parse_args().directory)
