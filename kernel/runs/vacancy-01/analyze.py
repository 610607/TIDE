"""Summarize paired field branches and reproduce the selected natural pedigrees."""
import argparse
import csv
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "geometry-01"))
import geometry


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write(path, columns, records):
    with path.open("w", newline="") as stream:
        table = csv.writer(stream, delimiter="\t", lineterminator="\n")
        table.writerow(columns.split())
        table.writerows(records)


def case(row):
    return tuple(row[k] for k in ("cohort", "seed", "site", "born", "opening"))


def success(row):
    return row["first_live_intact"] == "1"


def compare(cohort, pairs, first, second):
    scores = [(key[1], success(arms[first]), success(arms[second]))
              for key, arms in pairs if first in arms and second in arms]
    by_seed = defaultdict(list)
    for seed, a, b in scores:
        by_seed[seed].append((a, b))
    event_counts = Counter((a, b) for _, a, b in scores)
    seed_counts = Counter((any(a for a, _ in values), any(b for _, b in values))
                          for values in by_seed.values())
    return (cohort, first, second, len(scores), event_counts[1, 1], event_counts[1, 0],
            event_counts[0, 1], event_counts[0, 0], len(by_seed), seed_counts[1, 1],
            seed_counts[1, 0], seed_counts[0, 1], seed_counts[0, 0])


def summarize(initial, priority):
    combined = {name: read(initial / name) + read(priority / name)
                for name in ("seeds.tsv", "readers.tsv", "encounters.tsv")}
    cases = {case(r): r for r in combined["encounters.tsv"]}
    arms = defaultdict(dict)
    local_winners = {}
    for r in read(priority / "branches.tsv"):
        key = case(r)
        option = (key, r["local_option"])
        if r["arm"] == "local" and r["opening_effect"] == "reserve":
            local_winners[option] = r
        if r["arm"] == "grant" and option in local_winners:
            assert r["end_fnv64"] == local_winners[option]["end_fnv64"]
        if r["preferred"] == "1" or r["local_option"] == "-1":
            assert r["arm"] not in arms[key]
            arms[key][r["arm"]] = r
    products = read(priority / "products.tsv")
    first_products = {}
    for r in products:
        if r["parent_depth"] == "0" and r["arm"] == "grant":
            first_products.setdefault((case(r), r["local_option"]), r)

    totals, comparisons, timing = [], [], []
    for cohort in ("historical", "prospective", "replication"):
        fields = [s for s in combined["seeds.tsv"] if s["cohort"] == cohort]
        readers = [r for r in combined["readers.tsv"] if r["cohort"] == cohort]
        pairs = [(key, a) for key, a in arms.items() if key[0] == cohort]
        totals.append((cohort, len(fields), sum(int(s["births"]) for s in fields),
                       *(sum(s["status"] == status for s in fields)
                         for status in ("reproducing", "stagnant", "extinct")),
                       len(readers), sum(r["first_copy"] != "0" for r in readers),
                       sum(r["first_bank"] == "occupied" and r["first_source_hex"] == "5253434c44"
                           for r in readers),
                       len(pairs), len({k[1] for k, _ in pairs}),
                       len({k[1] for k, a in pairs if success(a["ordinary"])})))
        for first, second in (("local", "ordinary"), ("local", "remote"), ("grant", "local"),
                              ("grant", "grant_denied")):
            comparisons.append(compare(cohort, pairs, first, second))
        for key, a in pairs:
            c = cases[key]
            opening = int(c["opening"])
            donor_left = int(c["donor_born"]) + 81 - opening
            focal_left = int(c["born"]) + 81 - opening
            sufficient = donor_left >= 10 and focal_left > 12
            gr = a.get("grant")
            product = first_products.get((key, gr["local_option"])) if gr else None
            changed = product and product["inputs_hex"] != product["product_hex"]
            if not gr:
                result = "no_local_fork"
            elif success(gr):
                result = "live_intact"
            elif focal_left <= 12:
                result = "focal_age_limit"
            elif donor_left < 10:
                result = "donor_age_limit"
            elif changed:
                result = "substitution"
            else:
                result = "other_failure"
            timing.append((*key, donor_left, focal_left, int(sufficient), opening+10, opening+12,
                           gr["first_birth"] if gr else "-", product["original_live_bytes"] if product else "-",
                           int(changed) if product else "-", result))
    write(priority / "summary.tsv", "cohort seeds births reproducing stagnant extinct readers first_attempts "
          "live_match_at_first_attempt encounters encounter_seeds ordinary_positive_seeds", totals)
    write(priority / "comparisons.tsv", "cohort first second paired_cases both first_only second_only neither "
          "paired_seeds seed_both seed_first_only seed_second_only seed_neither", comparisons)
    write(priority / "timing.tsv", "cohort seed site born opening donor_death_minus_opening "
          "focal_death_minus_opening sufficient_age_window immediate_last_copy immediate_division "
          "grant_first_birth original_live_bytes substituted grant_outcome", timing)
    return cases, arms, products, combined["seeds.tsv"]


def natural_audit(priority, binaries, reverse, cases, arms, products, seeds):
    positive = [k for k, a in arms.items() if k[0] != "historical" and success(a["ordinary"])]
    targets, origins, expected, pairs = {}, [], {}, []
    assays = geometry.Assays(binaries / "observe")
    assays.check_controls()
    for key in positive:
        c = cases[key]
        seed, focal, born = key[1:4]
        births = [r for r in products if case(r) == key and r["arm"] == "ordinary"]
        selected = {(seed, focal, born): "founder"}
        for r in births:
            if r["parent_depth"] == "0" and r["child_depth"] == "1" and r["original_live_bytes"] == "5":
                selected[seed, r["child_site"], r["tick"]] = "daughter"
        targets.update(selected)
        for identity in selected:
            _, site, t = identity
            expected[identity] = [(r["tick"], r["child_site"], r["inputs_hex"], r["product_hex"])
                                  for r in births if r["parent_site"] == site and r["parent_born"] == t]
        # A second observer on the unmodified VM identifies births of both members of the pair.
        world = geometry.replay(binaries / "field", 16, int(seed), bool(reverse))
        terminal = next(s["state_fnv64"] for s in seeds if s["seed"] == seed)
        assert world.hashes[2048] == terminal
        for role, site, t in (("founder", focal, born), ("donor", c["donor_site"], c["donor_born"])):
            identity = int(site), int(t)
            person = world.people[identity]
            origins.append((seed, role, site, t, *person.parent, world.people[person.parent].genome,
                            person.inputs, person.genome, world.external_writes.get(identity, "-")))
        founder = int(focal), int(born)
        mother = world.people[founder]
        for child in mother.exposed_births():
            daughter = world.people[child]
            for grandchild in daughter.exposed_births():
                ma, mr = geometry.own_assay(16, assays, founder, mother)
                da, dr = geometry.own_assay(16, assays, child, daughter)
                pairs.append((seed, *founder, *child, *grandchild, ma, mr, da, dr,
                              int(mr == dr == "dependent")))
    write(priority / "natural-pairs.tsv", "seed founder_site founder_born daughter_site daughter_born "
          "grandchild_site grandchild_born founder_assay founder_result daughter_assay daughter_result confirmed", pairs)
    geometry.rows_to_file(priority / "natural-generations.tsv", assays.records)
    write(priority / "natural-origins.tsv", "seed role site born parent_site parent_born parent_hex "
          "inputs_hex product_hex external_byte_sources", origins)
    write(priority / "natural-targets.tsv", "seed site born role", [(*k, v) for k, v in targets.items()])
    score_file = priority / "natural-scores.tsv"
    product_file = priority / "natural-products.tsv"
    window_file = priority / "natural-openings.tsv"
    data = "".join(f"16 {s} {i} {t}\n" for s, i, t in targets)
    subprocess.run([binaries / "natural", score_file, product_file, window_file, *reverse],
                   input=data, text=True, check=True)
    observed = defaultdict(list)
    for r in read(product_file):
        if r["branch"] == "ordinary":
            observed[r["seed"], r["site"], r["born"]].append(tuple(
                r[k] for k in ("tick", "child_site", "inputs_hex", "product_hex")))
    for identity in targets:
        assert observed[identity] == expected[identity], "ordinary lifetime products differ from field"
    for r in read(score_file):
        if r["branch"] == "deny_all":
            assert r["births"] == "0" and r["reads"] == "0"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("initial", type=Path)
    parser.add_argument("priority", type=Path)
    parser.add_argument("binaries", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    results = summarize(args.initial, args.priority)
    natural_audit(args.priority, args.binaries.resolve(), ["--reverse"] if args.reverse else [], *results)
