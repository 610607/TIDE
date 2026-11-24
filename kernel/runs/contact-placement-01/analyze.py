"""Audit byte-level attribution and summarize paired digital reader movements."""
import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from run import CASE, check, read

BRANCHES = ("ordinary", "contact", "sham")
ARMS = ("east", "read", "place", "bearing")
STAGES = ("facing", "facing_room", "held", "pointed_held", "executed_s", "selected_focal",
          "reserve_won", "blocked_full", "blocked_contest", "selected_first", "selected_six",
          "selected_exact", "any_first", "any_six", "any_exact")
SCREENS = ("paired", "reader_pinned", "no_contact_destination", "no_matched_distance_kind", "no_matched_room")


def identity(row):
    return tuple(row[k] for k in CASE)


def table(path, rows):
    with path.open("w", newline="") as stream:
        out = csv.DictWriter(stream, rows[0], delimiter="\t", lineterminator="\n")
        out.writeheader()
        out.writerows(rows)


def delta(a, b):
    x, y = abs(a % 16 - b % 16), abs(a // 16 - b // 16)
    return min(x, 16 - x), min(y, 4 - y)


def faces(site, bearing, focal):
    dx, dy = ((0, 1), (1, 0), (0, -1), (-1, 0))[bearing]
    return 16 * ((site // 16 + dy) % 4) + ((site % 16 + dx) % 16) == focal


def audit_traces(attempts, cases, branches, case_id=identity, focal_columns=("focal_site", "focal_born")):
    totals = defaultdict(Counter)
    for row in attempts:
        key = case_id(row)
        branch = branches[key][row["branch"]]
        fork = cases[key]
        focal, born, actor = (int(row[k]) for k in (*focal_columns, "actor"))
        chosen = int(branch["reader_at"]) == actor and row["actor_born"] == fork["reader_born"]
        check(chosen == bool(int(row["selected"])) and actor != focal, "executor attribution")
        genome = bytes.fromhex(fork["product"])
        trace = [w.split("/") for w in row["trace"].split(",")]
        check(0 < len(trace) == int(row["n_writes"]) <= len(genome) == 6, "trace length")
        aligned = True
        changed = 0
        product = bytearray()
        last = int(fork["tick"]) - 1
        for index, (t, site, birth, kind, offset, raw, copied) in enumerate(trace):
            t, site, birth, offset, raw, copied = map(int, (t, site, birth, offset, raw, copied))
            check(last < t <= int(branch["end"]), "copy time")
            last = t
            same = kind == "o" and site == focal and birth == born
            if same:
                check(t <= born + 81 and 0 <= offset < 6 and raw == genome[offset], "living donor bytes")
            aligned &= same and offset == index
            check(index != 0 or aligned, "opening write")
            changed += raw != copied
            product.append(copied)
        check(aligned == bool(int(row["aligned"])) and changed == int(row["substitutions"]), "trace totals")
        divided = row["status"] == "birth"
        if divided:
            check(len(trace) == 6 and product.hex() == row["product"], "division product")
        if row["status"] != "cutoff":
            check(last < int(row["finish"]) <= int(branch["end"]), "termination time")
        exact = len(trace) == 6 and aligned and not changed and divided
        tally = totals[(key, row["branch"])]
        for group in (("any", "selected") if chosen else ("any",)):
            tally[group + "_first"] += 1
            tally[group + "_six"] += len(trace) == 6 and aligned
            tally[group + "_exact"] += exact
    for key, triple in branches.items():
        for name, branch in triple.items():
            for group in ("any", "selected"):
                for stage in ("first", "six", "exact"):
                    field = group + "_" + stage
                    check(int(branch[field]) == totals[(key, name)][field], "trace/branch discrepancy")


def load(directory):
    screen = read(directory / "screen.tsv")
    cases = {identity(r): r for r in screen}
    check(len(cases) == len(screen) == 5039, "duplicate or missing case")
    branches = defaultdict(dict)
    for row in read(directory / "branches.tsv"):
        key, name = identity(row), row["branch"]
        check(name not in branches[key] and cases[key]["status"] == "paired", "invalid branch")
        branches[key][name] = row
    for key, fork in cases.items():
        check(fork["status"] in SCREENS, "screening reason")
        if fork["status"] != "paired":
            continue
        near, sham, origin, focal, born, tick = (int(fork[k]) for k in
            ("contact", "sham", "reader_origin", "focal_site", "focal_born", "tick"))
        check(sum(delta(focal, near)) == 1 and min(sum(delta(focal, sham)), sum(delta(focal, origin))) > 1,
              "template distance")
        check(delta(origin, near) == delta(origin, sham) == (int(fork["dx"]), int(fork["dy"])), "sham distance")
        check(int(fork["maker_born"]) + 81 < tick <= int(fork["next_natural_s"]) <= born + 81, "window")
        check(set(branches[key]) == set(BRANCHES), "missing paired outcome")
        for name, site in zip(BRANCHES, (origin, near, sham)):
            b = branches[key][name]
            check(site == int(b["reader_at"]) and int(b["end"]) == min(2048, born + 162), "branch identity")
            check(b["initial_living"] == branches[key]["ordinary"]["initial_living"] and
                  int(b["initial_living"]) + int(b["births"]) - int(b["deaths"]) == int(b["living"]), "population")
            check(int(b["final_copies"]) <= int(b["living"]), "copy abundance")
            if name != "contact":
                check(int(b["selected_first"]) == 0, "nonlocal read")
        check(int(branches[key]["ordinary"]["any_exact"]) == 0, "archived natural endpoint")
    attempts = read(directory / "attempts.tsv")
    audit_traces(attempts, cases, branches)
    audit_reuse(directory, attempts, cases)
    return screen, branches


def exact_birth(attempt):
    return (attempt["status"] == "birth" and attempt["n_writes"] == "6" and
            attempt["aligned"] == "1" and attempt["substitutions"] == "0")


def audit_reuse(directory, attempts, cases):
    def child_id(row):
        return (*identity(row), row["child_site"], row["child_born"])

    eligible = {(*identity(a), a["target"], a["finish"]): a for a in attempts
                if a["branch"] == "contact" and exact_birth(a)}
    products = read(directory / "reuse.tsv")
    check(len(products) == len(eligible) == 50 and {child_id(r) for r in products} == set(eligible),
          "offspring enrollment mismatch")
    copies, outcomes = {}, {}
    reads = read(directory / "reuse-attempts.tsv")
    for r in products:
        key = child_id(r)
        a = eligible[key]
        born = int(r["child_born"])
        check(r["maker_site"] == a["actor"] and r["maker_born"] == a["actor_born"] and
              r["child_genome"] == a["product"] == cases[identity(r)]["product"], "offspring pedigree")
        check(int(r["end"]) == min(2048, born + 162) and int(r["window_complete"]) == (born + 81 <= 2048)
              and int(r["initial_living"]) + int(r["births"]) - int(r["deaths"]) == int(r["living"]),
              "offspring follow-up window or balance")
        copies[key] = dict(tick=born+1, reader_born=r["maker_born"], product=r["child_genome"])
        tally = [item for item in reads if child_id(item) == key]
        selected = [item for item in tally if item["selected"] == "1"]
        other = [item for item in tally if item["selected"] == "0" and exact_birth(item)]
        post_death = sum(int(item["trace"].split("/", 1)[0]) > int(r["maker_born"]) + 81 for item in other)
        check(len(other) == int(r["other_exact"]) and post_death == int(r["post_death_exact"]),
              "offspring executor and timing")
        b = dict(reader_at=r["maker_site"], end=r["end"], any_first=r["first"], any_six=r["six"],
                 any_exact=r["exact"], selected_exact=r["maker_exact"], selected_first=len(selected),
                 selected_six=sum(item["aligned"] == "1" and item["n_writes"] == "6" for item in selected))
        outcomes[key] = {"contact": b}
    audit_traces(reads, copies, outcomes, child_id, ("child_site", "child_born"))


def estimate(values, seed_count):
    # Ratio of summed paired differences to summed cases, clustered by original seed.
    # Empty clusters have zero score, and are included in the finite-sample correction.
    by_seed = defaultdict(list)
    for seed, value in values:
        by_seed[seed].append(value)
    denominator = len(values)
    rate = sum(sum(x) for x in by_seed.values()) / denominator
    squares = sum((sum(x) - len(x) * rate) ** 2 for x in by_seed.values())
    half = 1.96 * math.sqrt(seed_count / (seed_count - 1) * squares) / denominator
    return [f"{x:.8f}" for x in (rate, rate - half, rate + half)]


def summarize(directory, screen, branches):
    screens, summaries, effects = [], [], []
    cohorts = [("pooled", screen, 2048)]
    for name, low in (("block1", 19521), ("block2", 20545)):
        cohorts.append((name, [r for r in screen if low <= int(r["seed"]) < low + 1024], 1024))
    cohorts.extend((a, [r for r in screen if r["arm"] == a], 2048) for a in ARMS)
    for cohort, rows, seeds in cohorts:
        matched = [r for r in rows if r["status"] == "paired"]
        counts = Counter(r["status"] for r in rows)
        screens.append(dict(cohort=cohort, screened=len(rows), **{k: counts[k] for k in SCREENS}))
        for name in BRANCHES:
            outcomes = [branches[identity(r)][name] for r in matched]
            item = dict(cohort=cohort, branch=name, pairs=len(matched))
            item.update({stage: sum(int(b[stage]) > 0 for b in outcomes) for stage in STAGES})
            item.update({field + "_total": sum(int(b[field]) for b in outcomes)
                         for field in ("any_first", "any_six", "any_exact", "selected_exact", "final_copies")})
            item.update({status: sum(b["status"] == status for b in outcomes)
                         for status in ("extinct", "stagnant", "reproducing")})
            summaries.append(item)
        for field in ("any_exact", "exact_birth_count", "final_copies"):
            def endpoint(row):
                if field == "any_exact":
                    return int(int(row[field]) > 0)
                return int(row["any_exact" if field == "exact_birth_count" else field])
            values = []
            for r in matched:
                pair = branches[identity(r)]
                values.append((r["seed"], endpoint(pair["contact"]) - endpoint(pair["sham"])))
            rate, lo, hi = estimate(values, seeds)
            effects.append(dict(cohort=cohort, endpoint=field, pairs=len(matched),
                                positive=sum(d > 0 for _, d in values), tied=sum(d == 0 for _, d in values),
                                negative=sum(d < 0 for _, d in values), difference=rate, low95=lo, high95=hi))
    strata = []
    for facing in (0, 1):
        for room in (0, 1):
            group = [r for r in screen if r["status"] == "paired" and
                     faces(int(r["contact"]), int(r["bearing"]), int(r["focal_site"])) == facing and
                     (int(r["free_neighbors"]) > 0) == room]
            near = [branches[identity(r)]["contact"] for r in group]
            strata.append(dict(initial_facing=facing, initial_room=room, pairs=len(group),
                               **{k: sum(int(b[k]) > 0 for b in near)
                                  for k in ("facing_room", "selected_focal", "selected_first", "selected_six", "selected_exact")}))
    for name, rows in (("screening", screens), ("summary", summaries), ("contrasts", effects), ("initial-state", strata)):
        table(directory / (name + ".tsv"), rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    directory = parser.parse_args().directory
    summarize(directory, *load(directory))
