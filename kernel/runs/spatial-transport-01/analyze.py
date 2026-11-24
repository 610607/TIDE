"""Summarize paired spatial runs with the seed as the independent unit."""
import argparse
import csv
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean, stdev

from run import ARMS, check, read


# Each value is a pooled numerator / denominator with an explicit reporting scale.
METRICS = {
    "encounters_per_world": ("encounters", "worlds", 1),
    "encounters_per_reader": ("encounters", "readers", 1),
    "productive_pair_pct": ("productive_pairs", "encounters", 100),
    "follow_on_pct": ("any_again", "complete", 100),
    "follow_on_per_world": ("any_again", "worlds", 1),
    "exact_per_world": ("exact_births", "worlds", 1),
    "exact_per_100k_living_ticks": ("exact_births", "living_ticks", 100000),
    "east_pct": ("east", "exact_births", 100),
    "supplier_switch_pct": ("switched_supplier", "started_unlike", 100),
    "moves_per_100_living_ticks": ("individual_moves", "living_ticks", 100),
}


def save(path, records):
    with path.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=records[0], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def donor_reuse(directory):
    """Link fully followed newborns to subsequent, unlike-executor births using their own bytes."""
    by_arm = defaultdict(list)
    for row in read(directory / "products.tsv"):
        by_arm[row["arm"]].append(row)
    summary = []
    for arm in ARMS:
        children = by_arm[arm]
        uses = defaultdict(list)
        for row in children:
            uses[row["seed"], row["donor_birth_site"], row["donor_born"]].append(row)
        eligible = [r for r in children if r["complete"] == "1" and r["template_again"] == "1"]
        linked = original = east_reuse = 0
        for row in eligible:
            later = uses[row["seed"], row["child_site"], row["child_born"]]
            linked += bool(later)
            first_reuse = next((r for r in later if r["executor_birth_site"] == row["executor_birth_site"]
                                and r["executor_born"] == row["executor_born"]), None)
            if first_reuse:
                original += 1
                east_reuse += first_reuse["first_direction"] == "E"
        summary.append(dict(arm=arm, supplied_again=len(eligible), worlds=len({r["seed"] for r in eligible}),
                            supplied_to_unlike=linked, reused_by_original_executor=original,
                            first_original_reuse_from_east=east_reuse))
    save(directory / "reuse.tsv", summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = {a: {} for a in ARMS}
    for row in read(args.output / "seeds.tsv"):
        numbers = {k: int(v) for k,v in row.items() if k not in ("seed","arm","status","state_fnv64")}
        numbers.update(worlds=1, exact_worlds=int(numbers["exact_births"] > 0),
                       **{s: int(row["status"] == s) for s in ("extinct","stagnant","reproducing")})
        data[row["arm"]][int(row["seed"])] = numbers
    cohorts, contrasts = [], []
    for group, seeds in (("pilot", range(19521,20545)), ("replication", range(20545,21569)),
                         ("pooled", range(19521,21569))):
        totals = {}
        for arm in ARMS:
            sums = Counter()
            for seed in seeds:
                sums.update(data[arm][seed])
            totals[arm] = sums
            rates = {k: f"{scale*sums[num]/sums[den]:.6f}" for k,(num,den,scale) in METRICS.items()}
            cohorts.append(dict(cohort=group, arm=arm, **sums, **rates))
        for arm in ARMS[1:]:
            for metric, (num, den, scale) in METRICS.items():
                base, test = totals["east"], totals[arm]
                r0, r1 = base[num]/base[den], test[num]/test[den]
                delta = scale*(r1-r0)
                influence = []
                for seed in seeds:
                    x, y = data["east"][seed], data[arm][seed]
                    influence.append(scale*len(seeds)*((y[num]-r1*y[den])/test[den] -
                                                       (x[num]-r0*x[den])/base[den]))
                check(abs(mean(influence)) < 1e-7, "paired influence mean")
                half_width = 1.96*stdev(influence)/sqrt(len(seeds))
                contrasts.append(dict(cohort=group, arm=arm, baseline="east", metric=metric,
                                      delta=f"{delta:.6f}", lo95=f"{delta-half_width:.6f}",
                                      hi95=f"{delta+half_width:.6f}"))
    save(args.output / "cohorts.tsv", cohorts)
    save(args.output / "contrasts.tsv", contrasts)
    donor_reuse(args.output)


if __name__ == "__main__":
    main()
