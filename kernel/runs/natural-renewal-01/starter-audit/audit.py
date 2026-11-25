"""Locate the first missing conditions in every archived natural starter family."""
import argparse
import csv
import io
import subprocess
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from controls import rows
from pedigree import Pedigree, from_record
from run import AGE, FOLLOW


def save(path, columns, data):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, columns.split(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def distance(a, b):
    dx, dy = abs(a % 16 - b % 16), abs(a // 16 - b // 16)
    return min(dx, 16 - dx) + min(dy, 4 - dy)


def audit(binary, reverse, start, records, world):
    seed = start["seed"]
    tree = Pedigree(from_record(row, row["confirmed"] == "1") for row in records.values())
    root, child = (tree.people[int(start[k])] for k in ("reader", "child"))
    assert child.actor == root.id and child.donor == int(start["donor"])
    assert tree.score(root)[2] == [(child.id,)] and root.genome == child.genome
    cutoff = root.born + FOLLOW
    older_birth = max(root.born, child.donor_born)
    last_death = older_birth + AGE
    descendants = [p for p in tree.people.values() if p.confirmed and older_birth < p.born <= cutoff
                   and root.id in tree.ancestors[p.id]]
    sites = {i: int(r["site"]) for i, r in records.items()}
    directions, watch = {}, []
    for a, b in permutations(descendants, 2):
        if not any(child.id in tree.ancestors[p.id] for p in (a, b)):
            continue
        # At its last opening the donor can still be read. A dying executor cannot execute.
        first = max(last_death, a.born, b.born) + 1
        last = min(a.born + AGE - 1, b.born + AGE, cutoff)
        if first > last:
            continue
        site, peer_site = sites[a.id], sites[b.id]
        directions[a.id, b.id] = dict(seed=seed, actor=a.id, peer=b.id, actor_site=site,
                                       peer_site=peer_site, distance=distance(site, peer_site),
                                       first=first, last=last)
        watch.append((a.id, site, a.born, b.id, peer_site, b.born, first, last))
    cmd = [binary, seed, world["horizon"], world["hash2048"], world["hash_end"], world["hash_tail"]]
    if reverse:
        cmd.append("--reverse")
    replay = subprocess.run(cmd, text=True, input="".join(" ".join(map(str, w)) + "\n" for w in watch),
                            capture_output=True)
    if replay.returncode:
        raise RuntimeError(f"seed {seed}: {replay.stderr}")
    trace = list(csv.DictReader(io.StringIO(replay.stdout), delimiter="\t"))
    by_pair = defaultdict(list)
    for t in trace:
        if t["effect"] != "death":
            by_pair[int(t["actor"]), int(t["peer"])].append(t)
    assert directions.keys() == by_pair.keys()
    for key, p in directions.items():
        obs, peer = by_pair[key], p["peer_site"]
        assert [int(o["tick"]) for o in obs] == list(range(p["first"], p["last"] + 1))
        p.update(facing=sum(int(o["bearing_site"]) == peer for o in obs),
                 selects_peer=sum(o["op"] == "S" and int(o["bearing_site"]) == peer for o in obs),
                 copies_peer=sum(o["effect"] == "copy" and int(o["read_site"]) == peer for o in obs),
                 busy_reserve=sum(o["op"] == "R" and o["effect"] == "busy" for o in obs),
                 no_vacancy=sum(o["free_neighbors"] == "0" for o in obs))
    products = []
    for p in tree.people.values():
        if p.actor != child.id:
            continue
        row = records[p.id]
        products.append(dict(seed=seed, starter_child=child.id, product=p.id, born=p.born,
                             inputs=bytes.fromhex(row["inputs"]).decode(),
                             output=bytes.fromhex(row["genome"]).decode(),
                             kinds="".join(w.split("/")[3] for w in row["writes"].split(",")),
                             substitutions=row["substitutions"], same=int(p.genome == root.genome),
                             confirmed=int(p.confirmed)))
    assert len(products) == int(records[child.id]["ordinary_births"])
    pairs = {frozenset(k) for k in directions}
    adjacent = {frozenset(k) for k, d in directions.items() if d["distance"] == 1}
    family = dict(seed=seed, reader=root.id, child=child.id, donor=child.donor,
                  genome=bytes.fromhex(root.genome).decode(), last_original_death=last_death,
                  confirmed_later=len(descendants), overlapping_pairs=len(pairs),
                  adjacent_pairs=len(adjacent), postdeath_peer_bytes=sum(p["copies_peer"] for p in directions.values()),
                  child_births=len(products), same_child_births=sum(p["same"] for p in products),
                  renewal_depth=int(start["depth"]))
    return family, list(directions.values()), products, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    archive = HERE.parent / "results"
    starts = list(rows(archive / "starts.tsv"))
    worlds = {w["seed"]: w for w in rows(archive / "world.tsv")}
    seeds = {s["seed"] for s in starts}
    assert len(starts) == len(seeds) == 7 and len(worlds) == 1024
    records = defaultdict(dict)
    for r in rows(archive / "nodes.tsv.gz"):
        if r["seed"] in seeds:
            records[r["seed"]][int(r["id"])] = r
    families, pairs, products, trace = [], [], [], []
    for s in starts:
        f, ps, births, events = audit(args.binary.resolve(), args.reverse, s, records[s["seed"]], worlds[s["seed"]])
        families.append(f)
        pairs.extend(ps)
        products.extend(births)
        trace.extend(events)
    for name, data in (("families", families), ("pairs", pairs), ("products", products), ("ticks", trace)):
        save(args.out / (name + ".tsv"), " ".join(data[0]), data)


if __name__ == "__main__":
    main()
