"""Join both transfers by individual identity, then compare the four arms by matched seed."""
import argparse
import csv
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean, stdev

from run import ARMS, check, read

FOLLOW = ("original", "handoff", "after_death", "original_and_handoff",
          "handoff_unlike", "after_death_unlike", "self_again", "any_supplier")
OUTCOMES = ("enrolled", "original", "handoff", "after_death")
CONTRASTS = {"read_only_minus_fixed": (-1,1,0,0), "place_only_minus_fixed": (-1,0,1,0),
             "both_minus_fixed": (-1,0,0,1), "interaction": (1,-1,-1,1)}


def save(path, rows, columns=None):
    with path.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=columns or rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def identity(row, role):
    site, birth = ("child_site","child_born") if role == "child" else (role+"_birth_site",role+"_born")
    return int(row[site]), int(row[birth])


def direction(origin, target):
    dx = (target%16 - origin%16)%16
    dy = (target//16 - origin//16)%4
    return {(0,1):"N", (1,0):"E", (0,3):"S", (15,0):"W"}[dx,dy]


def validate(row):
    child, executor, donor = (identity(row,k) for k in ("child","executor","donor"))
    times = [int(t) for t in row["read_ticks"].split(",")]
    sites = [int(s) for s in row["read_sites"].split(",")]
    check(len(times)==len(sites)==6 and all(x<y for x,y in zip(times,times[1:])), "six aligned read times")
    check(all(s == donor[0] for s in sites) and donor[0]!=executor[0] and
          direction(executor[0],donor[0])==row["first_direction"], "stationary source")
    check(direction(executor[0],child[0]) in "NESW" and child[0]!=donor[0] and executor[0]==int(row["executor_site"]),
          "stationary placement")
    check(max(donor[1],executor[1]) < times[0] <= times[-1] <= donor[1]+81 and
          times[-1] < child[1] <= executor[1]+80, "instruction timing")
    check(int(row["complete"]) == (child[1]+81<=2048), "follow-up window")


def score(world, products, links):
    key = {"seed":int(world["seed"]), "arm":world["arm"]}
    uses = defaultdict(list)
    for p in products:
        validate(p)
        uses[identity(p,"donor")].append(p)
    totals = Counter(dict(births=int(world["births"]), enrolled=0, complete=0, incomplete=0,
                          **{k:0 for k in FOLLOW}, **{f"{p}_{k}":0 for p in ("east","other")
                                                        for k in ("complete","original","handoff","after_death")}))
    for k in ("reproducing","stagnant","extinct"):
        totals[k] = int(world["status"]==k)
    for p in products:
        if p["product"] == p["executor"]:
            continue
        child, maker = identity(p,"child"), identity(p,"executor")
        landing = direction(maker[0],child[0])
        pos = "east" if landing=="E" else "other"
        totals["enrolled"] += 1
        complete = int(p["complete"])
        flags = {k:False for k in FOLLOW}
        flags["self_again"] = bool(int(p["self_again"]))
        for later in uses[child]:
            check(later["product"]==p["product"], "transferred sequence mismatch")
            actor = identity(later,"executor")
            first = int(later["read_ticks"].split(",")[0])
            same = actor==maker
            after = first > maker[1]+81
            unlike = later["executor"] != later["product"]
            check(not same or not after, "original actor after its death")
            flags["original"] |= same
            flags["handoff"] |= not same
            flags["after_death"] |= not same and after
            flags["handoff_unlike"] |= not same and unlike
            flags["after_death_unlike"] |= not same and after and unlike
            links.append(dict(**key, focal_site=child[0], focal_born=child[1], sequence=p["product"],
                              original_site=maker[0], original_born=maker[1], original_death=maker[1]+81,
                              placement=landing, first_donor_direction=p["first_direction"],
                              complete=complete, next_site=later["child_site"],
                              next_born=later["child_born"], next_executor_site=actor[0], next_executor_born=actor[1],
                              next_executor=later["executor"], original_reuse=int(same), after_death=int(after),
                              next_unlike=int(unlike), read_ticks=later["read_ticks"], read_sites=later["read_sites"]))
        flags["original_and_handoff"] = flags["original"] and flags["handoff"]
        flags["any_supplier"] = flags["original"] or flags["handoff"]
        check(flags["any_supplier"]==bool(int(p["template_again"])), "lifetime template flag")
        totals["complete" if complete else "incomplete"] += 1
        if complete:
            totals[pos+"_complete"] += 1
            for k,v in flags.items():
                totals[k] += v
            for k in ("original","handoff","after_death"):
                totals[pos+"_"+k] += flags[k]
    check(totals["enrolled"]==int(world["exact_births"]) and totals["complete"]==int(world["complete"])
          and totals["self_again"]==int(world["self_again"]), "field census mismatch")
    for k in OUTCOMES:
        totals[k+"_worlds"] = int(totals[k]>0)
    return dict(**key, **totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    d = args.directory
    grouped = defaultdict(list)
    for p in read(d/"products.tsv"):
        grouped[int(p["seed"]),p["arm"]].append(p)
    links, fields = [], {}
    for world in read(d/"fields.tsv"):
        key = int(world["seed"]), world["arm"]
        check(key not in fields, "duplicate field")
        fields[key] = score(world, grouped.pop(key,[]), links)
    check(not grouped and len(fields)==8192, "incomplete field coverage")
    save(d/"endpoints.tsv", list(fields.values()))
    save(d/"links.tsv", links)
    summaries, contrasts = [], []
    for cohort, seeds in (("pilot",range(19521,20545)), ("replication",range(20545,21569)),
                          ("pooled",range(19521,21569))):
        for arm in ARMS:
            sums = Counter()
            for seed in seeds:
                sums.update({k:v for k,v in fields[seed,arm].items() if k not in ("seed","arm")})
            summaries.append(dict(cohort=cohort,arm=arm,worlds=len(seeds),**sums))
        for outcome in OUTCOMES:
            for contrast, weights in CONTRASTS.items():
                diffs = [sum(weight*fields[seed,arm][outcome] for arm,weight in zip(ARMS,weights)) for seed in seeds]
                delta = 1000*mean(diffs)
                half = 1960*stdev(diffs)/sqrt(len(diffs))
                contrasts.append(dict(cohort=cohort,outcome=outcome,contrast=contrast,per_1000_worlds=f"{delta:.3f}",
                                      lo95=f"{delta-half:.3f}",hi95=f"{delta+half:.3f}",positive=sum(n>0 for n in diffs),
                                      zero=diffs.count(0),negative=sum(n<0 for n in diffs)))
    save(d/"cohorts.tsv",summaries)
    save(d/"contrasts.tsv",contrasts)


if __name__=="__main__":
    main()
