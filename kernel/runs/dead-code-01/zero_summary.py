"""Summarize the post hoc zero-byte replays of dead-code-01 (descriptive; not preregistered).

  python3 zero_summary.py

Written after the frozen analysis had run. Reads results/posthoc/zero-births/<cell>-<seed>.tsv,
written by zero_births.cpp, and each world's results/primary/<cell>-<seed>/world.tsv.gz. Stops
unless every replay reproduces its world's birth count and M2 numerator. Writes
results/posthoc/zero-births.tsv (one row per world) and results/posthoc/zero-births-summary.tsv
(retain minus empty per arm, for M2 as preregistered and for M2 without all-zero births). The
p-values use the frozen signed-rank test and are uncorrected.
"""
import csv
import gzip
import sys
from pathlib import Path

from analyze import median, wilcoxon

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = RESULTS / "posthoc"
SEEDS = range(31001, 31033)
ARMS = ("read", "read_fetch")
COLUMNS = ("arm", "reclamation", "seed", "ticks", "births", "with_zero", "all_zero", "m2_numerator",
           "all_zero_in_m2", "zero_products")


def replay(cell, seed):
    with open(OUT / "zero-births" / f"{cell}-{seed}.tsv") as f:
        row = dict(zip(COLUMNS, f.read().rstrip("\n").split("\t")))
    return {k: (row[k] if k in ("arm", "reclamation", "zero_products") else int(row[k])) for k in COLUMNS}


def world(cell, seed):
    with gzip.open(RESULTS / "primary" / f"{cell}-{seed}" / "world.tsv.gz", "rt") as f:
        return next(csv.DictReader(f, delimiter="\t"))


def main():
    rows, bad = [], []
    for arm in ARMS:
        for rec in ("retain", "empty"):
            cell = f"{arm}-{rec}"
            for seed in SEEDS:
                r, w = replay(cell, seed), world(cell, seed)
                if (r["births"], r["m2_numerator"]) != (int(w["births"]), int(w["substitution_free_novel_births"])):
                    bad.append(f"{cell}-{seed}")
                per = 1e6 / r["births"]
                rows.append(dict(cell=cell, seed=seed, block="A" if seed <= 31016 else "B", births=r["births"],
                                 with_zero=r["with_zero"], all_zero=r["all_zero"], m2_numerator=r["m2_numerator"],
                                 all_zero_in_m2=r["all_zero_in_m2"], M2=r["m2_numerator"] * per,
                                 M2_without_all_zero=(r["m2_numerator"] - r["all_zero_in_m2"]) * per))
    if bad:
        sys.exit("replay does not reproduce world.tsv: " + " ".join(bad))
    columns = list(rows[0])
    with open(OUT / "zero-births.tsv", "w") as f:
        f.write("\t".join(columns) + "\n")
        for r in rows:
            f.write("\t".join(f"{r[c]:.6g}" if isinstance(r[c], float) else str(r[c]) for c in columns) + "\n")
    by = {(r["cell"], r["seed"]): r for r in rows}
    summary = []
    for arm in ARMS:
        for endpoint in ("M2", "M2_without_all_zero"):
            d = {s: by[(f"{arm}-retain", s)][endpoint] - by[(f"{arm}-empty", s)][endpoint] for s in SEEDS}
            values = list(d.values())
            summary.append(dict(arm=arm, endpoint=endpoint,
                                median_retain=median([by[(f"{arm}-retain", s)][endpoint] for s in SEEDS]),
                                median_empty=median([by[(f"{arm}-empty", s)][endpoint] for s in SEEDS]),
                                median_difference=median(values),
                                median_difference_A=median([d[s] for s in SEEDS if s <= 31016]),
                                median_difference_B=median([d[s] for s in SEEDS if s > 31016]),
                                retain_higher=sum(x > 0 for x in values), retain_lower=sum(x < 0 for x in values),
                                uncorrected_p=wilcoxon(values)))
    columns = list(summary[0])
    with open(OUT / "zero-births-summary.tsv", "w") as f:
        f.write("\t".join(columns) + "\n")
        for r in summary:
            f.write("\t".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in columns) + "\n")
    for r in summary:
        print("\t".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in columns))


if __name__ == "__main__":
    main()
