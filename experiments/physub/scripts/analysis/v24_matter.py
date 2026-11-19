"""v24 matter table (thousands) and where monomers went from 50k to the last tick.
Usage: v24_matter.py <dir>."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import load
D = sys.argv[1]
RUNS = ["zero_s1", "zero_s2", "fail_s1", "fail_s2"]
W = {r: load(f"{D}/{r}.tsv") for r in RUNS}
def m(r, t):
    x = W[r][t]["mass"]; ab = [int(v) for v in x["active_bytes(rep/loose/prop/other)"].split("/")]
    return {"free": int(x["free"]), "wall": int(x["wall"]), "strict": ab[0], "lp": ab[1] + ab[2], "other": ab[3],
            "inactive": int(x["inactive_bytes"]), "ref": W[r][t]["no_mass"], "istrict": int(x["inactive_strict_key"]),
            "isites": int(x["inactive_sites"])}
ticks = [t for t in (50000, 150000, 250000, 350000, 500000) if all(t in W[r] and "mass" in W[r][t] for r in RUNS)]
print("| tick | free | walls | active strict bytes | active `other` bytes | inactive bytes | refused writes |")
print("| --- | --- | --- | --- | --- | --- | --- |")
f = lambda r, t, k: f"{m(r, t)[k]/1000:.1f}"
for t in ticks:
    cell = lambda k: " / ".join(f(r, t, k) for r in RUNS[:2]) + "; " + " / ".join(f(r, t, k) for r in RUNS[2:])
    ref = " / ".join(f"{m(r, t)['ref']:,}" for r in RUNS[:2]) + "; " + " / ".join(f"{m(r, t)['ref']:,}" for r in RUNS[2:])
    print(f"| {t//1000}k | {cell('free')} | {cell('wall')} | {cell('strict')} | {cell('other')} | {cell('inactive')} | {ref} |")
last = ticks[-1]
for r in RUNS:
    a, b = m(r, 50000), m(r, last)
    d = {k: b[k] - a[k] for k in ("free", "wall", "strict", "lp", "other", "inactive")}
    src = -(d["free"] + d["strict"]); tot = sum(v for v in d.values())
    print(r, last, "left free+strict", src, {k: f"{100*d[k]/src:.0f}%" for k in ("wall", "other", "inactive", "lp")},
          "sum", tot, "inactive sites", a["isites"], "->", b["isites"], "inactive strict keys", a["istrict"], "->", b["istrict"])
    refs = [W[r][t]["no_mass"] for t in sorted(W[r]) if "no_mass" in W[r][t]]
    print("   refusals per window", refs)
