#!/usr/bin/env python3
"""Tables and bullet figures for the v20 README section. Usage: v20_md.py <v19 dir> <v20 dir>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from v20 import series, offs, RUNS  # noqa: E402
from v19 import pct  # noqa: E402

A, B = Path(sys.argv[1]), Path(sys.argv[2])
S = {r: (series(A, r), series(B, r)) for r in RUNS}
P = lambda a, b: f"{a} / {b}"

print("### strict sites (v19 / v20)")
print("| tick | " + " | ".join(RUNS) + " |")
print("| --- |" + " --- |" * len(RUNS))
for i in range(10):
    t = S[RUNS[0]][0][i]["t"]
    print(f"| {t//1000}k | " + " | ".join(P(S[r][0][i]["rn"], S[r][1][i]["rn"]) for r in RUNS) + " |")


def tot(xs, lo=150000, hi=500000):
    ys = [x for x in xs if lo < x["t"] <= hi]
    s = lambda k: sum(x[k] for x in ys)
    selfw = sum(x["writer"]["self"] for x in ys)
    br = [sum(x["e"]["start"]["born_rep_start0"][i] for x in ys) for i in range(2)]
    m = sum((x["rp"] + x["rn"]) / 2 for x in ys) / len(ys)
    d = dict(net=ys[-1]["rn"] - ys[0]["rp"], copy=sum(x["born"][0] for x in ys),
             reig=sum(x["born"][1] for x in ys), dec=s("dec"), wick=s("wick"), out=s("out"), inn=s("inn"),
             selfw=selfw, forw=s("out") - selfw,
             s0=sum(offs(x, "out_offsets_self", {0}) for x in ys), f30=s("src_foreign"),
             f3640=sum(offs(x, "out_offsets_foreign", {36, 38, 40}) for x in ys),
             ftail=sum(offs(x, "out_offsets_foreign", set(range(47, 54))) for x in ys),
             ipn=s("inn") - s("out"), off=pct(br[1] - br[0], br[1]), m=m, n=len(ys),
             w_rep=sum(x["writer"]["rep"] for x in ys), w_oth=sum(x["writer"]["other"] for x in ys),
             starved=s("starved"))
    d["rate"] = lambda v: v / m / 10 / len(ys)
    return d


print("\n### after 150k (v19 / v20)")
cols = ["net", "copy", "reig", "dec", "wick", "selfw", "forw", "s0", "f30", "f3640", "ftail", "ipn", "off"]
print("| run | net | copy births | re-ignitions | decay | wick | lost in place: self-written | foreign-written "
      "| self-written at offset 0 | neighbor fill of 30 | 36, 38, 40 | 47-53 | in place, net | births off offset 0 |")
print("| --- |" + " --- |" * len(cols))
T = {r: (tot(S[r][0]), tot(S[r][1])) for r in RUNS}
for r in RUNS:
    a, b = T[r]
    cells = []
    for c in cols:
        if c in ("net", "ipn"):
            cells.append(P(f"{a[c]:+d}", f"{b[c]:+d}"))
        elif c == "off":
            cells.append(P(f"{a[c]:.1f}%", f"{b[c]:.1f}%"))
        else:
            cells.append(P(a[c], b[c]))
    print(f"| {r} | " + " | ".join(cells) + " |")

print("\n### per strict site per 5000 ticks after 150k, copy error (s1 / s2)")
print("| | copy births | decay | re-ignitions minus wick ends | self-written loss | foreign-written loss "
      "| in place, net | net |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for k, tag in [(0, "v19"), (1, "v20")]:
    def cell(f):
        return P(*(f(T[r][k]) for r in ["m195_s1", "m195_s2"]))
    print(f"| {tag} | " + " | ".join([
        cell(lambda d: f"{d['rate'](d['copy']):.3f}"), cell(lambda d: f"{d['rate'](d['dec']):.3f}"),
        cell(lambda d: f"{d['rate'](d['reig'] - d['wick']):+.3f}"), cell(lambda d: f"{d['rate'](d['selfw']):.3f}"),
        cell(lambda d: f"{d['rate'](d['forw']):.3f}"), cell(lambda d: f"{d['rate'](d['ipn']):+.3f}"),
        cell(lambda d: f"{d['rate'](d['net']):+.3f}")]) + " |")

print("\n### bullet figures")
for r in RUNS:
    a, b = T[r]
    ch = lambda k: f"{pct(b[k] - a[k], a[k]):+.0f}%" if a[k] else "n/a"
    chr_ = lambda k: (f"{pct(b['rate'](b[k]) - a['rate'](a[k]), a['rate'](a[k])):+.0f}%" if a[k] else "n/a")
    print(r, "mean strict", round(a["m"]), round(b["m"]), "| change: selfw", ch("selfw"), "per site", chr_("selfw"),
          "forw", ch("forw"), "per site", chr_("forw"), "f30", ch("f30"), "f3640", ch("f3640"), "ftail", ch("ftail"),
          "out", ch("out"), "ipn", ch("ipn"), "reig x", round(b["reig"] / a["reig"], 2), "wick x",
          round(b["wick"] / max(a["wick"], 1), 2), "| writers rep", a["w_rep"], b["w_rep"], "other", a["w_oth"], b["w_oth"],
          "| starved", a["starved"], b["starved"])
    # self-written instruction offsets and changed offsets (v20)
    ys = [x for x in S[r][1] if x["t"] > 150000]
    at, so = {}, {}
    for x in ys:
        for k, n in x["e"].get("self_at", []):
            at[int(k)] = at.get(int(k), 0) + int(n)
        for k, n in x["e"].get("out_offsets_self", []):
            so[int(k)] = so.get(int(k), 0) + int(n)
    sw = sum(x["writer"]["self"] for x in ys)
    if sw:
        print("   v20 self_at top", [(k, v, f"{pct(v, sw):.0f}%") for k, v in sorted(at.items(), key=lambda kv: -kv[1])[:5]],
              "changed offsets 1:", so.get(1, 0), "4-6:", sum(so.get(i, 0) for i in (4, 5, 6)))
    # by point: strict child share, filled own-site pointer, other sites
    for k, tag in [(0, "v19"), (1, "v20")]:
        xs = S[r][k]
        last = xs[-1]
        rc = [x.get("rep_child_strict") for x in xs if x.get("rep_child_strict") is not None]
        print(f"   {tag} 500k other={last.get('other_sites')} rep_filled%={pct(last.get('rep_filled', 0), last.get('rep_sites', 1)):.1f} "
              f"child_strict% range {min(rc):.1f}-{max(rc):.1f} at500k {rc[-1]:.1f}")
# refusals in window before 200k
for r in RUNS:
    a = [x for x in S[r][0] if x["t"] == 200000][0]; b = [x for x in S[r][1] if x["t"] == 200000][0]
    print(r, "starved window to 200k", a["starved"], b["starved"])
