"""Compare two observation horizons on all frozen field records and audit positive pedigrees."""
import argparse
import csv
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent.parent / "build"
ANCESTOR = b"R.CLD".hex()
HORIZONS = (64, 4096)
BRANCHES = ("on", "off", "ancestor_on", "ancestor_off")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def table(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def save(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@dataclass(frozen=True)
class Setup:
    arm: str
    focal: str
    donor: str
    direction: int

    def key(self):
        return f"{self.arm}-{self.focal}-{self.donor}-{'NESW'[self.direction]}"


def setup(row, role):
    return Setup(row["arm"], row[role + "_genome"], row[role + "_donor_hex"], int(row[role + "_direction"]))


@dataclass(frozen=True)
class Generation:
    result: str
    ticks: int
    cycle_start: str
    reads: int
    fetches: int
    product: str


@lru_cache(maxsize=None)
def observe(binary, arm, allow, focal, donor, direction, horizon):
    output = subprocess.check_output(
        [binary, arm, allow, focal, donor, "NESW"[direction], str(horizon)], text=True)
    result, ticks, start, reads, fetches, product = output.strip().split("\t")
    return Generation(result, int(ticks), start, int(reads), int(fetches), product)


def generations(binary, case, branch, horizon):
    focal = ANCESTOR if branch.startswith("ancestor") else case.focal
    allow = branch.split("_")[-1]
    path = []
    for _ in range(3):
        g = observe(binary, case.arm, allow, focal, case.donor, case.direction, horizon)
        path.append((focal, g))
        if g.result != "birth":
            break
        focal = g.product
    return path


def score(path):
    births = [g for _, g in path if g.result == "birth"]
    return (len(births), sum(bool(g.reads or g.fetches) for g in births),
            sum(g.ticks for _, g in path), int(path[-1][1].result == "cycle"))


def classify(scores):
    if any(scores[b][0] != 3 for b in ("ancestor_on", "ancestor_off")):
        return "control_failed"
    if scores["on"][0] == scores["off"][0] == 3:
        return "both_reproduce"
    if scores["on"][1] == 3 and scores["off"][3]:
        return "dependent"
    return "inconclusive"


class Assays:
    def __init__(self, binary):
        self.binary = binary
        self.results = {}
        self.records = []

    def run(self, case, horizon):
        key = (case, horizon)
        if key in self.results:
            return self.results[key]
        scores = {}
        for branch in BRANCHES:
            path = generations(self.binary, case, branch, horizon)
            scores[branch] = score(path)
            for gen, (genome, g) in enumerate(path, 1):
                period = g.ticks - int(g.cycle_start) if g.result == "cycle" else "-"
                self.records.append(dict(assay=case.key(), horizon=horizon, branch=branch,
                    generation=gen, focal_hex=genome, result=g.result, end_tick=g.ticks,
                    first_equal_tick=g.cycle_start, period=period, neighbor_reads=g.reads,
                    neighbor_fetches=g.fetches, product_hex=g.product))
        self.results[key] = (scores, classify(scores))
        return self.results[key]

    def check_controls(self):
        for arm, focal, donor in [("fetch", "RJD", "CCCTP"), ("read", "RSCLD", "RSCLDP"),
                                   ("fetch", "R.CJD", "J.CLD")]:
            case = Setup(arm, focal.encode().hex(), donor.encode().hex(), 1)
            for h in HORIZONS:
                scores, outcome = self.run(case, h)
                require(outcome == "dependent" and scores["off"][0] == 0, "positive control failed")
                require(scores["ancestor_on"][:2] == scores["ancestor_off"][:2] == (3, 0),
                        "ancestor control failed")
                if focal == "R.CJD":
                    require(scores["on"] == (3, 3, 45, 0) and scores["off"] == (0, 0, 8, 1),
                            "seed 8 discovery assay changed")


def measure_pair(assays, cohort, row):
    live = all(row[r + "_bank"] == "occupied" for r in ("mother", "child"))
    timed_out_pair = (live and all(row[r + "_on"].startswith("3/3/") and
                         row[r + "_off"] == "0/0/64/0" for r in ("mother", "child")))
    output = {k: row[k] for k in ("arm", "seed", "tick", "daughter_site", "mother_site", "mother_born", "child_site", "child_born")}
    output.update(cohort=cohort, eligible=int(live), both_denied_timeout64=int(timed_out_pair),
                  confirmed64=int(row["confirmed"]))
    if not live:
        require(output["confirmed64"] == 0, "non-live pair was confirmed")
    for role in ("mother", "child"):
        output[role + "_assay"] = setup(row, role).key() if live else "-"
        output[role + "_64"] = row[role + "_result"]
        output[role + "_4096"] = "outside_paired_live_assay"
        if live:
            scores, short = assays.run(setup(row, role), 64)
            for branch in BRANCHES:
                archived = tuple(map(int, row[f"{role}_{branch}"].split("/")))
                require(scores[branch] == archived, f"archived branch mismatch {output}, {branch}")
            require(short == row[role + "_result"], "archived classification mismatch")
            output[role + "_4096"] = assays.run(setup(row, role), 4096)[1]
    for h in HORIZONS:
        positive = int(all(output[f"{role}_{h}"] == "dependent" for role in ("mother", "child")))
        if h == 64:
            require(positive == output["confirmed64"], "field confirmation mismatch")
        else:
            output["confirmed4096"] = positive
    output.update(family_root_site="-", family_root_born="-", three_identical_genomes="-")
    return output


def field_id(row, site, tick):
    return (int(row[site]), int(row[tick]))


def audit(tide, arm, seed, candidates):
    """Follow physical births and copy events from the original complete field trace."""
    founder = (36, 0)
    genomes = {founder: ANCESTOR}
    parents, first, origins, last_writes, deaths = {}, {}, {}, {}, {}
    roots, depths = {founder: founder}, {founder: 1}
    field = subprocess.check_output([tide, "trace", arm, seed], text=True)
    for e in csv.DictReader(field.splitlines(), delimiter="\t"):
        cpu = field_id(e, "actor", "born")
        tick = int(e["tick"])
        kind = e["effect"]
        channel = "read" if arm == "read" else "fetch"
        if e[channel + "_kind"] != "-" and cpu not in first:
            first[cpu] = (tick, e[channel + "_site"], e[channel + "_kind"], e[channel + "_born"],
                          e[channel + "_hex"])
        if kind == "reserve":
            last_writes[cpu] = []
        elif kind == "copy":
            last_writes[cpu].append((tick, e["read_site"], e["read_offset"], int(e["input"]), int(e["output"])))
        elif kind == "death":
            deaths[cpu] = tick
        elif kind == "birth":
            child = field_id(e, "target", "tick")
            writes = last_writes.pop(cpu)
            require(bytes(w[-1] for w in writes).hex() == e["product_hex"], "copied bytes disagree with field birth")
            parents[child] = cpu
            genomes[child] = e["product_hex"]
            origins[child] = writes
            same = genomes[child] == genomes[cpu]
            roots[child] = roots[cpu] if same else child
            depths[child] = depths[cpu] + 1 if same else 1

    families = {}
    identical = 0
    for row, measured in candidates:
        mother = field_id(row, "mother_site", "mother_born")
        child = field_id(row, "child_site", "child_born")
        daughter = field_id(row, "daughter_site", "tick")
        require(parents[daughter] == child and parents[child] == mother, "broken two-generation field link")
        require(genomes[daughter] == row["daughter_hex"], "granddaughter genome mismatch")
        for role, individual, offspring in [("mother", mother, child), ("child", child, daughter)]:
            hit = first[individual]
            require(hit == (int(row[role + "_contact_tick"]), row[role + "_donor_site"], "occupied",
                            row[role + "_donor_born"], row[role + "_donor_hex"]), "first donor mismatch")
            x, y = individual[0] % 8, individual[0] // 8
            dx, dy = [(0, 1), (1, 0), (0, -1), (-1, 0)][int(row[role + "_direction"])]
            expected_site = ((y + dy) % 8) * 8 + (x + dx) % 8
            require(expected_site == int(hit[1]) and hit[0] <= offspring[1] and
                    genomes[individual] == row[role + "_genome"], "field contact time, direction or genome mismatch")
        root = roots[mother]
        if root not in families:
            members = [person for person, origin in roots.items() if origin == root]
            parent = parents.get(root)
            writes = origins.get(root, [])
            copied = ",".join(f"{t}@{site}.{offset}={src:02x}>{dst:02x}" for t, site, offset, src, dst in writes)
            living = sum(person not in deaths for person in members)
            families[root] = dict(arm=arm, seed=seed, root_site=root[0], root_born=root[1],
                genome_hex=genomes[root], parent_site=parent[0] if parent else "-",
                parent_born=parent[1] if parent else "-", parent_hex=genomes[parent] if parent else "-",
                origin_writes=copied or "-", members=len(members), max_depth=max(depths[p] for p in members),
                last_birth=max(p[1] for p in members), final_living=living,
                extinction_tick="-" if living else max(deaths[p] for p in members),
                confirmed_events=0, genome_retained_events=0)
        families[root]["confirmed_events"] += 1
        retained = genomes[mother] == genomes[child] == genomes[daughter]
        measured.update(family_root_site=root[0], family_root_born=root[1], three_identical_genomes=int(retained))
        families[root]["genome_retained_events"] += retained
        identical += retained
    return list(families.values()), identical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--observe", type=Path, default=BUILD / "observe")
    parser.add_argument("--tide", type=Path, default=BUILD / "tide")
    parser.add_argument("--field-dir", type=Path, default=HERE)
    args = parser.parse_args()
    cohorts = [
        ("discovery", HERE.parent / "pilot-01", "", 1, 8),
        ("replication", HERE.parent / "replication-01", "", 9, 32),
        ("prospective", args.field_dir, "field-", 33, 64)]
    assays = Assays(args.observe.resolve())
    assays.check_controls()
    pairs, seeds, families = [], [], []
    for cohort, directory, prefix, lo, hi in cohorts:
        grouped = defaultdict(list)
        for row in table(directory / (prefix + "links.tsv")):
            grouped[(row["arm"], row["seed"])].append(row)
        field_seeds = table(directory / (prefix + "seeds.tsv"))
        expected = {(arm, str(s)) for arm in ("self", "read", "fetch") for s in range(lo, hi + 1)}
        keys = {(r["arm"], r["seed"]) for r in field_seeds}
        require(keys == expected and len(keys) == len(field_seeds) and set(grouped) <= keys,
                "seed census mismatch")
        for seed in field_seeds:
            arm, number = seed["arm"], seed["seed"]
            rows = grouped[(arm, number)]
            measured = [measure_pair(assays, cohort, r) for r in rows]
            pairs.extend(measured)
            confirmed = [(r, m) for r, m in zip(rows, measured) if m["confirmed4096"]]
            require(len(rows) == int(seed["candidate_births"]) and
                    sum(r["confirmed64"] for r in measured) == int(seed["confirmed_births"]), "field totals differ")
            audited, same = audit(args.tide.resolve(), arm, number, confirmed) if confirmed else ([], 0)
            families.extend(dict(cohort=cohort, **family) for family in audited)
            seeds.append(dict(cohort=cohort, arm=arm, seed=number, status=seed["status"],
                births=seed["births"], candidate_events=len(rows), eligible=sum(r["eligible"] for r in measured),
                confirmed64=seed["confirmed_births"], confirmed4096=len(confirmed),
                genome_retained_events=same, confirmed_mother_families=len(audited), state_fnv64=seed["state_fnv64"]))
    args.out.mkdir(exist_ok=True, parents=True)
    for name, records in [("generations",assays.records), ("events",pairs), ("seeds",seeds), ("families",families)]:
        save(args.out / (name + ".tsv"), records)


if __name__ == "__main__":
    main()
