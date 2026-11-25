"""Reconstruct two successive transfers by moving birth identity and score paired fields."""
import argparse
import csv
from collections import Counter, defaultdict
from math import comb, sqrt
from pathlib import Path
from statistics import mean, stdev

from run import ARMS, FIRST, HERE, SPLIT, STOP, check, read

COHORTS = {"historical": range(FIRST, SPLIT), "prospective": range(SPLIT, STOP), "pooled": range(FIRST, STOP)}
WINDOWS = ("complete", "strict", "incomplete")
MEASURES = ("copies", "original", "handoff", "post", "handoff_world", "post_world")
STATES = ("reproducing", "stagnant", "extinct")


def save(path, rows):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, rows[0], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def person(row, role):
    key = "child_site" if role == "child" else role + "_birth_site"
    return int(row[key]), int(row[role + "_born"])


def direction(origin, target):
    dx = (target % 16 - origin % 16) % 16
    dy = (target // 16 - origin // 16) % 4
    return {(0, 1): "N", (1, 0): "E", (0, 3): "S", (15, 0): "W"}[dx, dy]


def verify_birth(r):
    child, maker, donor = (person(r, role) for role in ("child", "executor", "donor"))
    actor = int(r["executor_site"])
    times = [int(t) for t in r["read_ticks"].split(",")]
    sites = [int(s) for s in r["read_sites"].split(",")]
    check(len(times) == len(sites) == 6 and all(a < b for a, b in zip(times, times[1:])), "six ordered reads")
    check(max(maker[1], donor[1]) < times[0] and times[-1] <= donor[1] + 81 and
          times[-1] < child[1] <= min(maker[1] + 80, 2048), "copy from living donor")
    check(maker != donor and len(bytes.fromhex(r["product"])) == 6 and len(bytes.fromhex(r["executor"])) == 6,
          "external six-byte birth")
    check(direction(actor, sites[0]) == r["first_direction"] and
          all(direction(actor, s) in "NESW" for s in sites) and direction(actor, child[0]) in "NESW",
          "pinned executor geometry")
    if r["arm"] == "east":
        check(actor == maker[0] and all(s == donor[0] for s in sites), "stationary identity")
    check(int(r["complete"]) == (child[1] + 81 <= 2048), "lifetime classification")


def score(world, products, links):
    seed, arm = int(world["seed"]), world["arm"]
    newborns = {person(p, "child") for p in products}
    check(len(newborns) == len(products), "duplicate product")
    uses = defaultdict(list)
    for p in products:
        verify_birth(p)
        uses[person(p, "donor")].append(p)
    counts = Counter({f"{w}_{k}": 0 for w in WINDOWS for k in MEASURES})
    for p in products:
        if p["product"] == p["executor"]:
            continue
        child, maker = person(p, "child"), person(p, "executor")
        flags = {"original": False, "handoff": False, "post": False}
        for link in uses[child]:
            reader = person(link, "executor")
            next_child = person(link, "child")
            same = reader == maker
            post = int(link["read_ticks"].split(",")[0]) > maker[1] + 81
            check(p["product"] == link["product"] and (not same or not post), "link provenance")
            flags["original"] |= same
            flags["handoff"] |= not same
            flags["post"] |= post
            links.append(dict(seed=seed, arm=arm, focal_site=child[0], focal_born=child[1], sequence=p["product"],
                              original_site=maker[0], original_born=maker[1], original_death=maker[1] + 81,
                              placement=direction(int(p["executor_site"]), child[0]),
                              first_donor_direction=p["first_direction"], complete=int(p["complete"]),
                              next_site=next_child[0], next_born=next_child[1], next_executor_site=reader[0],
                              next_executor_born=reader[1], next_executor=link["executor"], original_reuse=int(same),
                              after_death=int(post), next_unlike=int(link["executor"] != link["product"]),
                              read_ticks=link["read_ticks"], read_sites=link["read_sites"]))
        check(bool(uses[child]) == bool(int(p["template_again"])), "mismatch with VM lifetime flag")
        windows = ["complete" if int(p["complete"]) else "incomplete"]
        if child[1] <= 1886:
            windows.append("strict")
        for w in windows:
            counts[w + "_copies"] += 1
            for k, hit in flags.items():
                counts[w + "_" + k] += hit
    for w in WINDOWS:
        for k in ("handoff", "post"):
            counts[w + "_" + k + "_world"] = int(counts[w + "_" + k] > 0)
    for w in ("complete", "incomplete"):
        check(counts[w + "_copies"] == int(world[w]), "world enrollments")
    check(1 + int(world["births"]) - int(world["deaths"]) == int(world["living"]), "world population")
    check(int(world["exact_births"]) == counts["complete_copies"] + counts["incomplete_copies"], "enrolled total")
    check(world["status"] in STATES, "field status")
    return dict(seed=seed, arm=arm, **counts)


def paired(fields, seeds, arm, w):
    diffs = [fields[s, arm][w + "_handoff_world"] - fields[s, "east"][w + "_handoff_world"] for s in seeds]
    positive, negative = diffs.count(1), diffs.count(-1)
    discordant = positive + negative
    tail = sum(comb(discordant, j) for j in range(min(positive, negative) + 1))
    p = min(1., 2 * tail / (2 ** discordant))
    rate = 1000 * mean(diffs)
    half = 1960 * stdev(diffs) / sqrt(len(diffs))
    return dict(gained=positive, lost=negative, tied=diffs.count(0), delta_per_1000=f"{rate:.5f}",
                low95=f"{rate-half:.5f}" if discordant else "", high95=f"{rate+half:.5f}" if discordant else "",
                exact_p=f"{p:.7f}")


def audit_switches(directory, worlds):
    types = ("same_site_displaced", "same_site_after_death", "changed_address")
    counts = defaultdict(Counter)
    seen = set()
    for row in read(directory / "switches.tsv"):
        seed, arm = int(row["seed"]), row["arm"]
        data = {k: int(v) for k, v in row.items() if k not in ("arm", "source_bank")}
        tick, site = data["tick"], data["site"]
        marker = (seed, arm, tick, data["actor_site"])
        check(marker not in seen and 1 <= data["write_offset"] <= 5, "invalid switch")
        seen.add(marker)
        check(data["actor_born"] < data["previous_tick"] < tick <= data["actor_born"] + 80 and
              data["donor_born"] < data["previous_tick"] <= data["donor_born"] + 81, "switch timing")
        check((data["donor_now"] >= 0) == (tick <= data["donor_born"] + 81) and
              data["donor_now"] != site, "switched donor identity")
        check((row["source_bank"] == "occupied") == (data["source_born"] >= 0) and
              (data["source_born"], data["source_birth_site"]) != (data["donor_born"], data["donor_birth_site"]),
              "incoming bank occupancy")
        if site != data["previous_site"]:
            cause = "changed_address"
        elif data["donor_now"] >= 0:
            cause = "same_site_displaced"
            check(arm != "east", "displacement in stationary world")
        else:
            cause = "same_site_after_death"
        counts[seed, arm][cause] += 1
    check(counts.keys() <= worlds.keys(), "unknown field in switch ledger")
    for key, w in worlds.items():
        check(sum(counts[key].values()) == int(w["switched_supplier"]), "field switch total")
    summary = []
    for cohort, seeds in COHORTS.items():
        for arm in ARMS:
            starts = sum(int(worlds[s, arm]["started_unlike"]) for s in seeds)
            sums = {k: sum(counts[s, arm][k] for s in seeds) for k in types}
            summary.append(dict(cohort=cohort, arm=arm, starts=starts, switches=sum(sums.values()), **sums))
    save(directory / "switch-summary.tsv", summary)


def main(directory):
    births = defaultdict(list)
    for r in read(directory / "products.tsv"):
        births[int(r["seed"]), r["arm"]].append(r)
    fields, links = {}, []
    totals = {}
    for r in read(directory / "fields.tsv"):
        key = int(r["seed"]), r["arm"]
        check(key not in fields, "duplicate field")
        fields[key] = score(r, births.pop(key, []), links)
        totals[key] = r
    check(not births and fields.keys() == {(s, a) for s in COHORTS["pooled"] for a in ARMS}, "seed coverage")
    historical = [r for r in links if r["arm"] == "east" and r["seed"] < SPLIT]
    reference = [r for r in read(HERE.parent / "bearing-handoff-01" / "results" / "links.tsv") if r["arm"] == "east"]
    check([{k: str(v) for k, v in r.items()} for r in historical] == reference, "archived stationary handoff links")
    save(directory / "links.tsv", links)
    save(directory / "endpoints.tsv", list(fields.values()))
    summaries, contrasts = [], []
    for cohort, seeds in COHORTS.items():
        for arm in ARMS:
            raw = [totals[s, arm] for s in seeds]
            common = dict(cohort=cohort, arm=arm, worlds=len(seeds))
            for k in ("births", "encounters", "started_unlike", "switched_supplier", "exact_births", "individual_moves",
                      "living_ticks"):
                common[k] = sum(int(r[k]) for r in raw)
            for state in STATES:
                common[state] = sum(r["status"] == state for r in raw)
            for w in WINDOWS:
                counts = {k: sum(fields[s, arm][w + "_" + k] for s in seeds) for k in MEASURES}
                denom = counts["copies"]
                summaries.append(dict(**common, window=w, **counts,
                                      handoff_per_1000_worlds=f"{1000*counts['handoff_world']/len(seeds):.5f}",
                                      handoff_per_1000_copies=f"{1000*counts['handoff']/denom:.5f}" if denom else ""))
                if arm != "east" and w != "incomplete":
                    contrasts.append(dict(cohort=cohort, arm=arm, reference="east", window=w,
                                          **paired(fields, seeds, arm, w)))
    save(directory / "cohorts.tsv", summaries)
    save(directory / "contrasts.tsv", contrasts)
    audit_switches(directory, totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    main(parser.parse_args().directory)
