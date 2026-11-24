"""Apply two lineage endpoints to every birth in the archived prospective fields."""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "vacancy-01"
sys.path.insert(0, str(HERE.parent / "geometry-01"))
from geometry import (Assays, END, READER, census, check_reference, neighbor_direction, own_assay,
                      replay, require, rows_to_file, table)

LINK = ("cohort seed mother_site mother_born birth_number child_site child_born donor_site "
        "donor_born depth child_births child_death source_writes").split()
PAIR = ("cohort seed mother_site mother_born child_site child_born grandchild_site grandchild_born "
        "mother_assay mother_result child_assay child_result confirmed").split()


def donor_for_intact_copy(world, mother, child):
    p = world.people[child]
    if p.genome != READER or p.inputs != READER:
        return None
    records = world.external_writes.get(child, "").split(",")
    if len(records) != 5:
        return None
    donors = set()
    for offset, record in enumerate(records):
        write, tick, source, read, bank, born, _ = record.split("/")
        if bank != "o":
            return None
        donor = int(source), int(born)
        require(int(write) == int(read) == offset and donor[0] != mother[0], "invalid reader copy")
        supplier = world.people[donor]
        require(donor[1] < int(tick) and (supplier.death is None or int(tick) <= supplier.death),
                "source lifetime mismatch")
        donors.add(donor)
    if len(donors) == 1:
        donor = donors.pop()
        require(world.people[donor].genome == READER, "intact copy source mismatch")
        return donor
    return None


def audit(row, world, assays):
    cohort, seed = row["cohort"], int(row["seed"])
    stats = census(world.people, END)
    check_reference(stats, world.hashes[END], row)
    require(sum(p.genome == READER for p in world.people.values()) == int(row["readers"]),
            "reader census changed")
    depths, links, pairs = {}, [], []
    reader_mother_births = 0
    # The observer inserts each individual at birth, so every mother precedes her children.
    for mother, parent in world.people.items():
        if parent.genome == READER:
            reader_mother_births += len(parent.children)
            for number, child in enumerate(parent.children, 1):
                donor = donor_for_intact_copy(world, mother, child)
                if donor is None:
                    continue
                depths[child] = depths.get(mother, 0) + 1
                q = world.people[child]
                links.append(dict(zip(LINK, (cohort, seed, *mother, number, *child, *donor,
                    depths[child], len(q.children), q.death or "-", world.external_writes[child]), strict=True)))
        # The frozen behavioral test also admits births with changed product bytes.
        for child in parent.exposed_births():
            offspring = world.people[child]
            for grandchild in offspring.exposed_births():
                ma, mr = own_assay(16, assays, mother, parent)
                ca, cr = own_assay(16, assays, child, offspring)
                pairs.append(dict(zip(PAIR, (cohort, seed, *mother, *child, *grandchild,
                    ma, mr, ca, cr, int(mr == cr == "dependent")), strict=True)))
    score = dict(cohort=cohort, seed=seed, **stats, reader_mother_births=reader_mother_births,
                 live_intact_births=len(links), max_live_depth=max(depths.values(), default=0),
                 candidate_pairs=len(pairs),
                 live_first_pairs=sum(p["mother_assay"] != "-" and p["child_assay"] != "-" for p in pairs),
                 confirmed_pairs=sum(p["confirmed"] for p in pairs), state_fnv64=world.hashes[END])
    return score, links, pairs


def daughter_windows(world):
    targets = table(STUDY / "priority/natural-targets.tsv")
    targets = [(r["role"], (int(r["site"]), int(r["born"]))) for r in targets if r["seed"] == "2437"]
    founder, = [cpu for role, cpu in targets if role == "founder"]
    mother = world.people[founder]
    require(mother.death is not None, "maternal lifetime is censored")
    records = []
    for role, cpu in targets:
        if role != "daughter":
            continue
        daughter = world.people[cpu]
        require(daughter.parent == founder and daughter.death is not None, "unexpected daughter")
        for number, child in enumerate(daughter.children, 1):
            product = world.people[child]
            hits = [s.split("/") for s in world.external_writes[child].split(",")]
            ticks = [int(hit[1]) for hit in hits]
            require(len(ticks) == 5, "incomplete daughter copy history")
            records.append(dict(seed=2437, daughter_site=cpu[0], daughter_born=cpu[1],
                birth_number=number, child_site=child[0], child_born=child[1], first_copy=ticks[0],
                last_copy=ticks[-1], direction_to_mother="NESW"[neighbor_direction(16, cpu[0], founder[0])],
                mother_death=mother.death, mother_alive_reads=sum(t <= mother.death for t in ticks),
                actual_maternal_reads=sum(r[4] == "o" and (int(r[2]), int(r[5])) == founder for r in hits),
                inputs=bytes.fromhex(product.inputs).decode("ascii"),
                product=bytes.fromhex(product.genome).decode("ascii")))
    return sorted(records, key=lambda r: r["child_born"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("binaries", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    rows = [r for f in (STUDY / "seeds.tsv", STUDY / "priority/seeds.tsv")
            for r in table(f) if r["cohort"] in ("prospective", "replication")]
    require([int(r["seed"]) for r in rows] == list(range(577, 3137)), "archived seed list differs")
    assays = Assays(args.binaries.resolve() / "observe")
    assays.check_controls()
    scores, all_links, all_pairs, windows = [], [], [], []
    for row in rows:
        world = replay(args.binaries.resolve() / "field", 16, int(row["seed"]), args.reverse)
        score, links, pairs = audit(row, world, assays)
        scores.append(score)
        all_links.extend(links)
        all_pairs.extend(pairs)
        if row["seed"] == "2437":
            windows = daughter_windows(world)
    args.out.mkdir(parents=True, exist_ok=True)
    rows_to_file(args.out / "seeds.tsv", scores)
    rows_to_file(args.out / "live-links.tsv", all_links, LINK)
    rows_to_file(args.out / "pairs.tsv", all_pairs, PAIR)
    rows_to_file(args.out / "generations.tsv", assays.records)
    rows_to_file(args.out / "daughter-windows.tsv", windows)


if __name__ == "__main__":
    main()
