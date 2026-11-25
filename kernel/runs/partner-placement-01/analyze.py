"""Audit rooted pedigrees and tabulate outcomes at case and original-world level."""
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from run import rows

BLOCKS = ("pilot", "replication", "long-A", "long-B")
ARMS = ("ordinary", "apart", "together")
METRICS = ("root_confirmed", "partner_reads", "intact", "direct", "primary", "primary_via_match")


def write(path, fields, records):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def summarize(out):
    cases = {"-".join(r[k] for k in ("seed", "site", "born")): r for r in rows(out / "cases.tsv")}
    sites = {r["case"]: r for r in rows(out / "placement.tsv")}
    branches = {(r["case"], r["arm"]): r for r in rows(out / "branches.tsv")}
    nodes = defaultdict(list)
    for r in rows(out / "nodes.tsv.gz"):
        nodes[r["case"], r["arm"]].append(r)
    assert set(cases) == set(sites)
    assert set(branches) == {(k, arm) for k in cases for arm in
                             (ARMS if sites[k]["status"] == "eligible" else ("ordinary",))}
    for (key, arm), b in branches.items():
        c = cases[key]
        assert int(b["initial_living"]) + int(b["births"]) - int(b["deaths"]) == int(b["living"])
        if arm == "ordinary":
            assert b["start_hash"] == c["hash"]
        else:
            assert int(b["initial_living"]) == 2 + int(branches[key, "ordinary"]["initial_living"])
        if arm == "apart":
            assert b["root"] == branches[key, "together"]["root"]
            assert b["start_hash"] != branches[key, "together"]["start_hash"]
        root, match = int(b["root"]), int(b["match"])
        reached = {root} if b["root_confirmed"] == "1" else set()
        via = set()
        counts = Counter()
        for n in nodes[key, arm]:
            actor, donor, node = (int(n[k]) for k in ("actor", "donor", "id"))
            parents = {actor, donor}
            exact = n["genome"] == c["genome"]
            traces = [part.split("/") for part in n["writes"].split(",")]
            aligned = all(int(v[4]) == j and v[5] == traces[0][5] for j, v in enumerate(traces))
            assert len(traces) == 6 and donor == (int(traces[0][5]) if aligned else -1)
            if all(v[3] != "?" for v in traces):
                source, product = bytes.fromhex(n["inputs"]), bytes.fromhex(n["genome"])
                assert len(source) == len(product) == 6
                assert sum(a != b for a, b in zip(source, product)) == int(n["substitutions"])
            from_match = match >= 0 and actor == root and donor == match and int(n["substitutions"]) == 0 and exact
            assert from_match == (n["from_match"] == "1")
            counts["intact"] += from_match
            confirmed = int(n["exposed"]) > 0 and n["denied"] == "0" and int(n["blocked"]) > 0
            on_path = bool(parents & reached) and confirmed
            assert on_path == (n["on_path"] == "1")
            if on_path:
                reached.add(node)
                if from_match or parents & via:
                    via.add(node)
            assert (node in via) == (n["via_match"] == "1")
            counts["direct"] += on_path and exact and root in parents
            late = on_path and exact and int(n["born"]) > int(c["born"]) + 81
            assert late == (n["primary"] == "1")
            counts["primary"] += late
            counts["primary_via_match"] += late and node in via
        assert all(counts[k] == int(b[k]) for k in ("intact", "direct", "primary", "primary_via_match"))

    summary, paired = [], []
    for block in (*BLOCKS, "all"):
        source = [k for k, c in cases.items() if block == "all" or c["block"] == block]
        eligible = [k for k in source if sites[k]["status"] == "eligible"]
        for group, keys, arms in (("all", source, ("ordinary",)), ("eligible", eligible, ARMS)):
            for arm in arms:
                data = [branches[k, arm] for k in keys]
                record = dict(block=block, sample=group, arm=arm, cases=len(keys),
                              seeds=len({cases[k]["seed"] for k in keys}))
                for key in METRICS:
                    record[key] = sum(int(r[key]) > 0 for r in data)
                for status in ("extinct", "stagnant", "reproducing"):
                    record[status] = sum(r["status"] == status for r in data)
                # Supplementary duration of the observed confirmed path, measured from delivery.
                record["last_descendant_age"] = max(
                    (int(n["born"]) - int(cases[k]["born"]) for k in keys for n in nodes[k, arm]
                     if n["on_path"] == "1"), default=-1)
                summary.append(record)
        for unit in ("case", "seed"):
            for metric in METRICS:
                outcomes = defaultdict(lambda: [False, False])
                for key in eligible:
                    group = key if unit == "case" else cases[key]["seed"]
                    for i, arm in enumerate(("together", "apart")):
                        outcomes[group][i] |= int(branches[key, arm][metric]) > 0
                pairs = Counter(tuple(v) for v in outcomes.values())
                paired.append(dict(block=block, unit=unit, metric=metric, total=len(outcomes),
                                   together_only=pairs[True, False], apart_only=pairs[False, True],
                                   both=pairs[True, True], neither=pairs[False, False]))
    write(out / "summary.tsv", list(summary[0]), summary)
    write(out / "paired.tsv", list(paired[0]), paired)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    summarize(parser.parse_args().directory)
