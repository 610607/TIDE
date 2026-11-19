#!/usr/bin/env python3
"""Markdown tables for the v19 README section. Usage: v19_md.py <runs dir>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from v19 import load, row, pct  # noqa: E402

root = Path(sys.argv[1])
R = {r: [row(r, t, e) for t, e in sorted(load(root / f"{r}.tsv").items()) if "fate" in e]
     for r in ["m195_s1", "m195_s2", "nomut_s1", "nomut_s2"]}


def pair(a, b):
    return f"{a} / {b}"


print("### strict flows per window (s1 / s2)")
print("| tick | strict at end | births | ended: decay | ended: wick | lost in place "
      "| of which neighbor fill of 30 | gained in place | births - ends | in place, net |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for a, b in zip(R["m195_s1"], R["m195_s2"]):
    f = lambda x, k: x[k]
    born = lambda x: sum(x["born"])
    be = lambda x: sum(x["born"]) - x["dec"] - x["wick"]
    ip = lambda x: x["inn"] - x["out"]
    print(f"| {a['t']//1000}k | {pair(a['rn'], b['rn'])} | {pair(born(a), born(b))} | "
          f"{pair(a['dec'], b['dec'])} | {pair(a['wick'], b['wick'])} | {pair(a['out'], b['out'])} | "
          f"{pair(a['src_foreign'], b['src_foreign'])} | {pair(a['inn'], b['inn'])} | "
          f"{pair(f'{be(a):+d}', f'{be(b):+d}')} | {pair(f'{ip(a):+d}', f'{ip(b):+d}')} |")

print("\n### per strict site per 5000 ticks: in-place loss, neighbor fill of 30, decay")
for r in ["m195_s1", "m195_s2", "nomut_s1", "nomut_s2"]:
    out = []
    for x in R[r]:
        if x["t"] <= 150000:
            continue
        m = (x["rp"] + x["rn"]) / 2
        out.append(f"{x['t']//1000}k {x['out']/m/10:.3f}/{x['src_foreign']/m/10:.3f}/{x['dec']/m/10:.3f}")
    print(r, " ".join(out))

print("\n### totals over (150k, 500k]")
print("| run | net | births | decay | wick | lost in place | neighbor fill of 30 | gained in place "
      "| births - ends | in place, net |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for r, xs in R.items():
    xs = [x for x in xs if x["t"] > 150000]
    s = lambda k: sum(x[k] for x in xs)
    born = sum(sum(x["born"]) for x in xs)
    loss = s("loss")
    be = born - s("dec") - s("wick")
    print(f"| {r} | {xs[-1]['rn'] - xs[0]['rp']:+d} | {born} | {s('dec')} ({pct(s('dec'), loss):.1f}%) | "
          f"{s('wick')} ({pct(s('wick'), loss):.1f}%) | {s('out')} ({pct(s('out'), loss):.1f}%) | "
          f"{s('src_foreign')} ({pct(s('src_foreign'), loss):.1f}%) | {s('inn')} | {be:+d} | "
          f"{s('inn') - s('out'):+d} |")

print("\n### in-place losses over (150k, 500k] by writer and status after")
W = ["rep", "loose", "prop", "other", "self", "none"]
for r, xs in R.items():
    xs = [x for x in xs if x["t"] > 150000]
    tot = sum(x["out"] for x in xs)
    w = {k: sum(x["writer"][k] for x in xs) for k in W}
    to = {a: [sum(x["out_to"][a][i] for x in xs) for i in range(6)] for a in ["loose", "prop", "other"]}
    print(r, "n=", tot, "writers%", {k: f"{pct(v, tot):.1f}" for k, v in w.items()},
          "to%", {a: f"{pct(sum(v), tot):.1f}" for a, v in to.items()},
          "to_prop self%", f"{pct(to['prop'][4], sum(to['prop'])):.1f}",
          "to_other by", dict(zip(W, to["other"])))

print("\n### offset 30 fills over (150k, 500k]")
for r, xs in R.items():
    xs = [x for x in xs if x["t"] > 150000]
    src = sum(x["src"] for x in xs)
    only = sum(x["only"] for x in xs)
    fw = [sum(x["srcw"][i] for x in xs) for i in range(6)]
    foreign = sum(x["src_foreign"] for x in xs)
    names = sum(x["src_names"] for x in xs)
    jump = [sum(x["jump"][i] for x in xs) for i in range(3)]
    conv = sum(int(x["conv"]["copies"]) for x in xs)
    crep = sum(int(x["conv"]["child_rep"]) for x in xs)
    csame = sum(int(x["conv"]["child_same"]) for x in xs)
    csrc = sum(int(x["conv"]["child_src"]) for x in xs)
    alive = [int(x["conv"]["alive"]) for x in xs]
    endc = [sum(x["end_conv"][i] for x in xs) for i in range(2)]
    print(f"{r} src={src} only={only} writers(rep/loose/prop/other/self/none)={fw} "
          f"foreign={foreign} names_writer={names} ({pct(names, foreign):.1f}%) "
          f"jump0/op/other={jump} ({pct(jump[2], sum(jump)):.1f}% other) "
          f"conv copies={conv} child strict {pct(crep, conv):.1f}% same {pct(csame, conv):.1f}% "
          f"src {pct(csrc, conv):.1f}% alive {min(alive)}-{max(alive)} ends decay/wick {endc}")

print("\n### ends by status: decay share of ends, by window (s1 / s2)")
for t_i in range(10):
    cells = []
    for st in ["rep", "loose", "prop", "other"]:
        v = []
        for r in ["m195_s1", "m195_s2"]:
            e = R[r][t_i]["e"]["end"][st]
            v.append(f"{pct(e[0], sum(e)):.0f}")
        cells.append(f"{st} {'/'.join(v)}")
    print(R["m195_s1"][t_i]["t"] // 1000, "k", " ".join(cells))
for r in ["m195_s1", "m195_s2", "nomut_s1", "nomut_s2"]:
    tot = {st: [sum(x["e"]["end"][st][i] for x in R[r]) for i in range(2)]
           for st in ["rep", "loose", "prop", "other"]}
    print(r, "all windows decay%:", {st: f"{pct(v[0], sum(v)):.1f} (n={sum(v)})" for st, v in tot.items()})

print("\n### fatestart over windows")
for r, xs in R.items():
    for lo, hi in [(0, 150000), (150000, 500000)]:
        ys = [x for x in xs if lo < x["t"] <= hi and "start" in x["e"]]
        if not ys:
            continue
        g = lambda k, i: sum(y["e"]["start"][k][i] for y in ys)
        at = {}
        for y in ys:
            for k, n in y["e"]["self_at"]:
                at[int(k)] = at.get(int(k), 0) + int(n)
        top = sorted(at.items(), key=lambda kv: -kv[1])[:8]
        self_n = g("self_start0", 1)
        print(f"{r} ({lo//1000}k,{hi//1000}k] out_start0={g('out_start0', 0)}/{g('out_start0', 1)} "
              f"self_start0={g('self_start0', 0)}/{self_n} ({pct(g('self_start0', 0), self_n):.1f}%) "
              f"born_rep_start0={g('born_rep_start0', 0)}/{g('born_rep_start0', 1)} "
              f"({pct(g('born_rep_start0', 0), g('born_rep_start0', 1)):.2f}%) self_at(top10 per window, summed)="
              f"{[(k, n, f'{pct(n, self_n):.0f}%') for k, n in top]}")

print("\n### fill-converted activations (foreign write to offset 30 alone)")
for r, xs in R.items():
    for lo, hi in [(0, 150000), (150000, 500000)]:
        ys = [x for x in xs if lo < x["t"] <= hi and "fill" in x["e"]]
        if not ys:
            continue
        g = lambda k: sum(int(y["e"]["fill"][k]) for y in ys)
        ends = [sum(int(y["e"]["fill"]["ends_decay/wick"].split("/")[i]) for y in ys) for i in range(2)]
        n = g("copies")
        alive = [int(y["e"]["fill"]["alive"]) for y in ys]
        conv = sum(y["src_foreign"] for y in ys)
        print(f"{r} ({lo//1000}k,{hi//1000}k] converted={conv} alive {min(alive)}-{max(alive)} copies={n} "
              f"({n/conv if conv else 0:.2f} per conversion) child strict {pct(g('child_rep'), n):.1f}% "
              f"same {pct(g('child_same'), n):.1f}% src {pct(g('child_src'), n):.1f}% ends decay/wick={ends} "
              f"mean life {g('life_sum')/sum(ends) if sum(ends) else 0:.0f}")

print("\n### offsets of in-place losses by writer, summed over (150k, 500k] (top 8 per window)")
for r, xs in R.items():
    for key in ["out_offsets_foreign", "out_offsets_self"]:
        acc = {}
        for x in xs:
            if x["t"] <= 150000 or key not in x["e"]:
                continue
            for k, n in x["e"][key]:
                acc[int(k)] = acc.get(int(k), 0) + int(n)
        print(r, key, sorted(acc.items(), key=lambda kv: -kv[1])[:10])
