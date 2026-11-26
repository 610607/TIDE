"""Per-size intervals for the primary endpoints (brief, interpretation rule 1).

The brief asks that each size's median or proportion be reported with a 95% interval: exact
(Clopper-Pearson) for E1, percentile bootstrap for E2 and E3. The frozen analyze.py omits this
descriptive line, so this script adds it after the run, from results/analysis/worlds.tsv. It decides
nothing and changes no frozen file.

  python3 supplement.py    # writes results/analysis/size-intervals.tsv
"""
import csv
import importlib.util
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("analyze", HERE / "analyze.py")
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)

SEED = 20261127
RESAMPLES = 10_000
ENDPOINTS = ("E1_t1024", "E1_t4096", "E2_t1024", "E2_t4096", "E3")


def main():
    path = HERE / "results" / "analysis" / "worlds.tsv"
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    out = []
    for i, key in enumerate(ENDPOINTS):
        for size in analyze.SIZES:
            values = [float(r[key]) for r in rows if int(r["size"]) == size]
            if not values:
                continue
            if key.startswith("E1"):
                k = sum(v > 0 for v in values)
                lo, hi = analyze.clopper_pearson(k, len(values))
                out.append(dict(endpoint=key, size=size, worlds=len(values), statistic="proportion",
                                value=k / len(values), lo95=lo, hi95=hi, method="Clopper-Pearson"))
            else:
                rng = random.Random(SEED + 10 * i + size)
                boots = [analyze.median([rng.choice(values) for _ in values]) for _ in range(RESAMPLES)]
                lo, hi = analyze.percentile(boots, 0.025, 0.975)
                out.append(dict(endpoint=key, size=size, worlds=len(values), statistic="median",
                                value=analyze.median(values), lo95=lo, hi95=hi,
                                method=f"percentile bootstrap, {RESAMPLES} resamples"))
    analyze.write(HERE / "results" / "analysis" / "size-intervals.tsv", out)
    print(f"{len(out)} rows -> {path.parent / 'size-intervals.tsv'}")


if __name__ == "__main__":
    main()
