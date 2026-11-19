"""v18 T3 (top genotypes in run and alone) and m groups. Usage: v18_t3.py scan.tsv [groups]"""
import sys, statistics as st
rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
H, rows = rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]
u = 0.003
f = lambda x, k: float(x[k])
rng = lambda v, fmt="{:.1f}": fmt.format(min(v)) if fmt.format(min(v)) == fmt.format(max(v)) else f"{fmt.format(min(v))}-{fmt.format(max(v))}"
print("| tick | copies | in-run strict % | alone: strict % | alone: exact % | (1-u)^m % | m | sensitive length | pred % |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for t in sorted({int(x["tick"]) for x in rows}):
    xs = [x for x in rows if int(x["tick"]) == t]
    n = sum(int(x["run_births"]) for x in xs)
    run = sum(int(x["run_births"]) * f(x, "run_child_strict%") for x in xs) / n
    print(f"| {t//1000}k | {n} | {run:.1f} | {rng([f(x,'first_strict%') for x in xs])} | {rng([f(x,'first_exact%') for x in xs])} | "
          f"{rng([100*(1-u)**int(x['m']) for x in xs])} | {rng([int(x['m']) for x in xs], '{:d}')} | "
          f"{rng([f(x,'sub_sensitive_len') for x in xs])} | {rng([f(x,'pred%') for x in xs])} |")
print("\nfirst copies:", sum(int(x["first_n"]) for x in rows), "gap/multi max", max(f(x, "first_gap%") for x in rows), max(f(x, "first_multi%") for x in rows),
      "exact range", min(f(x, "first_exact%") for x in rows), max(f(x, "first_exact%") for x in rows),
      "exact+point min", min(f(x, "first_exact%") + f(x, "first_point%") for x in rows),
      "ko range", min(int(x["ko_nonstrict"]) for x in rows), max(int(x["ko_nonstrict"]) for x in rows),
      "strict range", min(f(x, "first_strict%") for x in rows), max(f(x, "first_strict%") for x in rows))
groups = [tuple(map(int, g.split("-"))) if "-" in g else (int(g), int(g)) for g in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["37", "38-39", "40-42", "43-45", "46-49", "50-53", "54-56"])]
print("\n| m | genotype-points | exact % | (1-u)^m % | strict % |")
print("| --- | --- | --- | --- | --- |")
for a, b in groups:
    xs = [x for x in rows if a <= int(x["m"]) <= b]
    if not xs: continue
    mm = st.mean(int(x["m"]) for x in xs)
    print(f"| {a if a == b else f'{a}-{b}'} | {len(xs)} | {st.mean(f(x,'first_exact%') for x in xs):.1f} | {100*(1-u)**mm:.1f} | {st.mean(f(x,'first_strict%') for x in xs):.1f} |")
from collections import Counter
print("m histogram", sorted(Counter(int(x["m"]) for x in rows).items()))
