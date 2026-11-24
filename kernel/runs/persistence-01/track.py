"""Reconstruct fixed founder families and distinguish new origins of identical genomes."""
import argparse
import csv
import subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "horizon-01"


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Family:
    def __init__(self, record):
        self.record = record
        self.root = (int(record["root_site"]), int(record["root_born"]))
        self.genome = record["genome_hex"]
        self.living = self.births = self.depth = self.last_birth = 0
        self.extinction = "-"
        self.other_inherited = self.other_origins = 0

    def checkpoint(self, tick):
        if tick == 512:
            expected = self.record
            for value, key in [(self.births, "members"), (self.living, "final_living"),
                               (self.depth, "max_depth"), (self.last_birth, "last_birth"),
                               (self.extinction, "extinction_tick")]:
                require(str(value) == expected[key], f"family prefix mismatch {key}")
        return dict(seed=self.record["seed"], root_site=self.root[0], root_born=self.root[1],
                    genome_hex=self.genome, tick=tick, members=self.births, living=self.living,
                    max_depth=self.depth, last_birth=self.last_birth, extinction_tick=self.extinction,
                    other_identical_inherited_since512=self.other_inherited,
                    other_identical_new_origins_since512=self.other_origins)


def track(binary, seed, prefix, inputs):
    families = [Family(row) for row in inputs]
    # Individual identity is the site and the tick of birth. Each child starts a
    # new clonal root when its bytes differ from the actual field parent's.
    founder = (36, 0)
    live = {founder: (b"R.CLD".hex(), founder, 1)}
    world_rows, family_rows, birth_ticks = [], [], []
    deaths = 0
    trace = subprocess.check_output([binary, seed], text=True)
    for line in trace.splitlines():
        kind, time, *data = line.split("\t")
        tick = int(time)
        if kind == "checkpoint":
            recent = sum(t > tick - 80 for t in birth_ticks)
            status = "extinct" if not live else "reproducing" if recent else "stagnant"
            if tick == 512:
                observed = [data[0], status, str(len(birth_ticks)), str(deaths), str(len(live)), str(recent)]
                require(observed == [prefix[k] for k in ("state_fnv64", "status", "births", "deaths",
                                                          "living", "final80_births")], "field prefix mismatch")
            world_rows.append(dict(seed=seed, tick=tick, status=status, births=len(birth_ticks),
                deaths=deaths, living=len(live), final80_births=recent, state_fnv64=data[0]))
            family_rows.extend(f.checkpoint(tick) for f in families)
            continue
        cpu = (int(data[0]), int(data[1]))
        genome, parent_root, depth = live[cpu]
        if kind == "death":
            deaths += 1
            del live[cpu]
            for f in families:
                if parent_root == f.root:
                    f.living -= 1
                    if not f.living:
                        f.extinction = tick
            continue
        require(kind == "birth", "unexpected event")
        child, product = (int(data[2]), tick), data[3]
        root = parent_root if genome == product else child
        child_depth = depth + 1 if genome == product else 1
        live[child] = (product, root, child_depth)
        birth_ticks.append(tick)
        for f in families:
            if root == f.root:
                require(f.extinction == "-" and product == f.genome, "clonal continuity broken")
                f.living += 1
                f.births += 1
                f.last_birth = tick
                f.depth = max(f.depth, child_depth)
            elif tick > 512 and product == f.genome:
                if genome == product:
                    f.other_inherited += 1
                else:
                    f.other_origins += 1
    require([r["tick"] for r in world_rows] == [512,1024,2048,4096], "missing checkpoint")
    return world_rows, family_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--field", type=Path, default=HERE.parent.parent / "build/field")
    args = parser.parse_args()
    grouped = defaultdict(list)
    for row in read(SOURCE / "families.tsv"):
        if row["cohort"] == "prospective":
            grouped[row["seed"]].append(row)
    worlds, families = [], []
    for seed in read(SOURCE / "field-seeds.tsv"):
        number = seed["seed"]
        if seed["arm"] == "fetch" and number in grouped:
            w, f = track(args.field.resolve(), number, seed, grouped[number])
            worlds.extend(w)
            families.extend(f)
    require(len(worlds) == 4 * len(grouped) and len(families) == 4 * sum(map(len, grouped.values())),
            "missing tracked families")
    args.out.mkdir(exist_ok=True, parents=True)
    write(args.out / "fields.tsv", worlds)
    write(args.out / "families.tsv", families)


if __name__ == "__main__":
    main()
