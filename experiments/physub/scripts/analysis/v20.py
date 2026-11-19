#!/usr/bin/env python3
"""Compare v20 (inert_operand=fail) with v19. Usage: v20.py <runs/v19> <runs/v20>"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from v19 import load, row, pct  # noqa: E402

RUNS = ["m195_s1", "m195_s2", "nomut_s1", "nomut_s2"]


def kv(line):
    return dict(re.findall(r"(\S+?)=(\S+)", line))


def extra(path):
    out = {}
    for line in open(path):
        if line.startswith("# census "):
            d = kv(line); out.setdefault(int(d["tick"]), {})["active"] = int(d["active"])
        elif line.startswith("# lineage "):
            d = kv(line); e = out.setdefault(int(d["tick"]), {})
            for k in ["rep_sites", "loose_sites", "prop_sites", "other_sites", "rep_filled", "other_filled"]:
                e[k] = int(d[k])
        elif line.startswith("# physics "):
            d = kv(line); e = out.setdefault(int(d["tick"]), {})
            e["operand_inert"] = int(d.get("operand_inert", -1))
            e["wick_all"] = int(d["wick"])
        elif line.startswith("# fidelity "):
            d = kv(line); e = out.setdefault(int(d["tick"]), {})
            e["copy_births"] = int(d["self/copy/reignite"].split("/")[1])
            e["reig_births"] = int(d["self/copy/reignite"].split("/")[2])
        elif line.startswith("# fidcopy ") and "parent=rep " in line:
            d = kv(line); e = out.setdefault(int(d["tick"]), {})
            e["rep_child_strict"] = float(d["child_strict%"]); e["rep_copies"] = int(d["births"])
    return out


def offs(x, key, want):
    return sum(int(n) for k, n in x["e"].get(key, []) if int(k) in want)


def series(root, r):
    data = load(root / f"{r}.tsv")
    ex = extra(root / f"{r}.tsv")
    xs = []
    for t, e in sorted(data.items()):
        if "fate" not in e:
            continue
        x = row(r, t, e)
        x.update(ex.get(t, {}))
        xs.append(x)
    return xs


def main():
    a_root, b_root = Path(sys.argv[1]), Path(sys.argv[2])
    S = {}
    for r in RUNS:
        S[r] = (series(a_root, r), series(b_root, r))

    print("## checks v20")
    for r in RUNS:
        bad = [(x["t"], x["bal"], x["rn"], x["mis"], x["untr"], x["stale"], x["repl"]) for x in S[r][1]
               if x["bal"] != x["rn"] or x["mis"] or x["untr"] or x["stale"] or x["repl"]]
        print(r, "points", len(S[r][1]), "bad", bad)

    print("\n## per 50k: strict sites / active / other  (v19 -> v20)")
    for r in RUNS:
        cells = []
        for a, b in zip(*S[r]):
            cells.append(f"{a['t']//1000}k {a['rn']}->{b['rn']} act {a.get('active')}->{b.get('active')} "
                         f"oth {a.get('other_sites')}->{b.get('other_sites')}")
        print(r); print("  " + "\n  ".join(cells))

    print("\n## operand_inert failures (cumulative) at each point, v20")
    for r in RUNS:
        print(r, [x.get("operand_inert") for x in S[r][1]])

    print("\n## per-window flows, v19 | v20: births, decay, wick, out, in, self-written out, foreign out, "
          "out changing 0 (self), fill30 (foreign), 36/38/40 foreign, 47-53 foreign, off-entry strict births %")
    for r in RUNS:
        print(r)
        for a, b in zip(*S[r]):
            def f(x):
                st = x["e"].get("start", {})
                br = st.get("born_rep_start0", [0, 0])
                off = pct(br[1] - br[0], br[1]) if br[1] else float("nan")
                return (f"b{sum(x['born'])} d{x['dec']} w{x['wick']} out{x['out']} in{x['inn']} "
                        f"self{x['writer']['self']} for{x['out'] - x['writer']['self']} "
                        f"s0:{offs(x, 'out_offsets_self', {0})} f30:{x['src_foreign']} "
                        f"f36-40:{offs(x, 'out_offsets_foreign', {36, 38, 40})} "
                        f"f47-53:{offs(x, 'out_offsets_foreign', set(range(47, 54)))} offentry%{off:.1f}")
            print(f"  {a['t']//1000}k {f(a)}\n       {f(b)}")

    print("\n## totals over (150k, 500k] and (0,150k]: v19 vs v20")
    for r in RUNS:
        for lo, hi in [(0, 150000), (150000, 500000)]:
            for tag, xs in zip(["v19", "v20"], S[r]):
                ys = [x for x in xs if lo < x["t"] <= hi]
                s = lambda k: sum(x[k] for x in ys)
                born = sum(sum(x["born"]) for x in ys)
                loss = s("loss")
                selfw = sum(x["writer"]["self"] for x in ys)
                s0 = sum(offs(x, "out_offsets_self", {0}) for x in ys)
                f3640 = sum(offs(x, "out_offsets_foreign", {36, 38, 40}) for x in ys)
                ftail = sum(offs(x, "out_offsets_foreign", set(range(47, 54))) for x in ys)
                br = [sum(x["e"]["start"]["born_rep_start0"][i] for x in ys if "start" in x["e"]) for i in range(2)]
                ss = [sum(x["e"]["start"]["self_start0"][i] for x in ys if "start" in x["e"]) for i in range(2)]
                m = sum((x["rp"] + x["rn"]) / 2 for x in ys) / len(ys)
                rate = lambda v: v / m / 10 / len(ys)
                print(f"{r} ({lo//1000}k,{hi//1000}k] {tag} net={ys[-1]['rn'] - ys[0]['rp']:+d} "
                      f"births={born} decay={s('dec')} ({pct(s('dec'), loss):.1f}%) wick={s('wick')} "
                      f"({pct(s('wick'), loss):.1f}%) out={s('out')} ({pct(s('out'), loss):.1f}%) in={s('inn')} "
                      f"b-e={born - s('dec') - s('wick'):+d} ip_net={s('inn') - s('out'):+d} "
                      f"self={selfw} ({pct(selfw, s('out')):.1f}% of out) self_s0={s0} "
                      f"self_offentry={ss[1] - ss[0]}/{ss[1]} "
                      f"fill30={s('src_foreign')} f36-40>={f3640} ftail>={ftail} "
                      f"offentry_rep_births={br[1] - br[0]}/{br[1]} ({pct(br[1] - br[0], br[1]):.2f}%) "
                      f"rates/site/5k out={rate(s('out')):.3f} wick={rate(s('wick')):.3f} "
                      f"net_ip={rate(s('out') - s('inn')):.3f} decay={rate(s('dec')):.3f}")


if __name__ == "__main__":
    main()
