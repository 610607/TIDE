"""v30: multi children and off-register parents per window, with no_mass.
Usage: v30_multi.py run.tsv...  (route=1 length=1 outputs)."""
import re, sys
ST = ["none_in", "none_off", "f36_in", "f36_off", "f38_in", "f38_off", "both_in", "both_off"]
for path in sys.argv[1:]:
    W = {}
    for l in open(path):
        m = re.match(r"# (route|routecopy|lengthptr) tick=(\d+)", l)
        if not m: continue
        t = int(m.group(2)); w = W.setdefault(t, {})
        if m.group(1) == "route":
            w["no_mass"] = int(re.search(r"no_mass=(\d+)", l).group(1))
        elif m.group(1) == "routecopy":
            a = l.split(" parent_off:")[0]
            w["cp"] = {c: int(re.search(rf"{c}=(\d+)\(", a).group(1)) for c in ("exact", "point", "gap", "multi", "env")}
        else:
            w["ptr"] = {}
            for s in ST:
                live, rest = re.search(rf" {s}:(\d+);([\d/]+);", l).groups()
                w["ptr"][s] = [int(live)] + [int(x) for x in rest.split("/")]
    name = "/".join(path.split("/")[-2:]).replace(".tsv", "")
    print("==", name)
    tot = {s: [0] * 6 for s in ST}
    for t in sorted(W):
        w = W[t]; cp = w["cp"]; n = sum(cp.values())
        p = w["ptr"]
        off = [sum(p[s][i] for s in ST if s.endswith("_off")) for i in range(6)]
        for s in ST:
            tot[s] = [a + b for a, b in zip(tot[s], p[s])]
        print(f" {t//1000:>3}k no_mass {w['no_mass']:6d} | e0 copies {n:6d} multi {cp['multi']:5d} ({100*cp['multi']/n:4.1f}%) "
              f"gap {cp['gap']:5d} env {cp['env']:5d} | off-register live {off[0]:4d} (none_off {p['none_off'][0]:4d}) "
              f"copies {off[1]:5d} multi {off[4]:5d} | none_off copies {p['none_off'][1]:5d} multi {p['none_off'][4]:5d}")
    allm = sum(tot[s][4] for s in ST); allc = sum(tot[s][1] for s in ST)
    print("  run: copies", allc, "multi", allm, " multi by state:",
          " ".join(f"{s}:{tot[s][4]}" for s in ST if tot[s][4]),
          "| off-register copies", sum(tot[s][1] for s in ST if s.endswith('_off')))
