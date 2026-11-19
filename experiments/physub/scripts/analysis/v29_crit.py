"""v29 criterion 1: strict census counts per checkpoint, 500k/50k, and 350k->500k.
Usage: v29_crit.py run.tsv... (ps_probe outputs with census=1)."""
import re, sys

def strict_series(path):
    out = {}
    for line in open(path):
        if line.startswith("# census "):
            t = int(re.search(r"tick=(\d+)", line).group(1))
            out[t] = int(re.search(r" strict=(\d+)", line).group(1))
    return out

for path in sys.argv[1:]:
    s = strict_series(path)
    name = path.split("/")[-2] + "/" + path.split("/")[-1].replace(".tsv", "")
    ticks = [t for t in sorted(s) if t % 50000 == 0]
    if 500000 not in s or 50000 not in s:
        print(name, "incomplete", {t: s[t] for t in ticks}); continue
    late = [t for t in (350000, 400000, 450000, 500000)]
    xs, ys = late, [s[t] for t in late]
    mx, my = sum(xs) / 4, sum(ys) / 4
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    ratio = s[500000] / s[50000]
    no_fall = s[500000] >= s[350000]
    ok = no_fall and ratio >= 0.8
    print(f"{name}: {'PASS' if ok else 'FAIL'} 500k/50k={ratio:.3f} 350k->500k {s[350000]}->{s[500000]} "
          f"({s[500000]-s[350000]:+d}; slope {slope*50000:+.0f} per 50k) series "
          + " ".join(f"{t//1000}k:{s[t]}" for t in ticks))
