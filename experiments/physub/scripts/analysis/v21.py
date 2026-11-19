#!/usr/bin/env python3
"""Summarize v21 trace lines. Usage: v21.py <runs/v21>"""
import re
import sys
from pathlib import Path

W = ["rep", "loose", "prop", "other", "self", "none"]


def tops(line, name, nxt):
    part = line.split(f" {name}:")[1]
    for n in nxt:
        if f" {n}:" in part:
            part = part.split(f" {n}:")[0]
    return {int(k): int(v) for k, v in re.findall(r"(\d+):(\d+)", part)}


def triples(line, label):
    seg = line.split(label)[1]
    return {k: [int(a), int(b), int(c)] for k, a, b, c in re.findall(r"(rep|loose|prop|other|self|none):(\d+)/(\d+)/(\d+)", seg)}


def load(path):
    out = {}
    for line in open(path):
        if line.startswith("# fidelity "):
            t = int(re.search(r"tick=(\d+)", line).group(1))
            out.setdefault(t, {})["no_mass"] = int(re.search(r"no_mass=(\d+)", line).group(1))
        if not line.startswith("# trace"):
            continue
        tag = line.split()[1]
        t = int(re.search(r"tick=(\d+)", line).group(1))
        e = out.setdefault(t, {})
        g = lambda k: re.search(rf" {re.escape(k)}=(\S+)", line).group(1)
        if tag == "traceout":
            seg = line.split("writer(status:age<1k/1k-10k/>=10k)")[1].split(" writer_kind")[0]
            e["out"] = dict(n=int(g("n")), v0=int(g("victim_start0")),
                            w={k: [int(a), int(b), int(c)] for k, a, b, c in re.findall(r"(\w+):(\d+)/(\d+)/(\d+)", seg)},
                            kind=[int(x) for x in g("writer_kind(self/copy/reignite/seeded)").split("/")],
                            wstart0=int(g("writer_start0")), not_mov=int(g("not_mov")), src_own=int(g("src_own")),
                            dir=int(g("dir")), dir_only=int(g("dir_only")),
                            wip=tops(line, "writer_ip", ["offsets", "dir_offsets"]),
                            offs=tops(line, "offsets", ["dir_offsets"]), diroffs=tops(line, "dir_offsets", []))
        elif tag == "traceign":
            seg = line.split("igniter(status:age<1k/1k-10k/>=10k)")[1].split(" same_key")[0]
            e["ign"] = dict(births=int(g("births")), off0=int(g("off0")),
                            r0=[int(x) for x in g("rep_start0(self/copy/reignite)").split("/")],
                            roff=[int(x) for x in g("rep_off0(self/copy/reignite)").split("/")],
                            ign={k: [int(a), int(b), int(c)] for k, a, b, c in re.findall(r"(\w+):(\d+)/(\d+)/(\d+)", seg)},
                            same=int(g("same_key")),
                            prev=[int(x) for x in g("prev_rep_wick(start0/off0)").split("/")],
                            gap=int(g("prev_gap_sum")),
                            iip=tops(line, "igniter_ip", ["entry"]), entry=tops(line, "entry", []))
        elif tag == "traceend":
            m = re.findall(r"decay/wick=(\d+)/(\d+) life_sum=(\d+) copies=(\d+)", line)
            e["end"] = [[int(x) for x in t4] for t4 in m]
        elif tag == "tracemass":
            d = dict(re.findall(r"(\S+?)=(\S+)", line))
            e["mass"] = {k: ([int(x) for x in v.split("/")] if "/" in v else int(v)) for k, v in d.items() if k != "tick"}
    return out


def add(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            add(dst.setdefault(k, {}), v)
        elif isinstance(v, list):
            if k not in dst:
                dst[k] = [0] * len(v) if not isinstance(v[0], list) else [[0] * len(x) for x in v]
            for i, x in enumerate(v):
                if isinstance(x, list):
                    for j, y in enumerate(x):
                        dst[k][i][j] += y
                else:
                    dst[k][i] += x
        else:
            dst[k] = dst.get(k, 0) + v


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def top(d, n=10):
    return " ".join(f"{k}:{v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n])


def main():
    root = Path(sys.argv[1])
    for r in ["m195_s1", "m195_s2", "nomut_s1", "zero_s1"]:
        p = root / f"{r}.tsv"
        if not p.exists():
            continue
        data = load(p)
        print(f"\n######## {r}")
        print("## per window: no_mass | mass free/code | active bytes rep/other | inactive sites/bytes/strict_key/strict_bytes | "
              "foreign n, dir, writer other<1k | rep births off0 (reig) / start0 | ign other | prev_rep_wick off0")
        for t, e in sorted(data.items()):
            if "out" not in e:
                continue
            m, o, g = e["mass"], e["out"], e["ign"]
            print(f"{t//1000}k nomass={e.get('no_mass')} free={m['free']} code={m['code']} "
                  f"act_rep={m['active_bytes(rep/loose/prop/other)'][0]} act_oth={m['active_bytes(rep/loose/prop/other)'][3]} "
                  f"sites rep/oth={m['active_sites'][0]}/{m['active_sites'][3]} "
                  f"inact={m['inactive_sites']}/{m['inactive_bytes']} strictkey={m['inactive_strict_key']}/{m['inactive_strict_bytes']} "
                  f"| fo n={o['n']} dir={o['dir']} dir_only={o['dir_only']} w={o['w']} "
                  f"| rep off0={sum(g['roff'])} ({g['roff'][2]} reig) start0={sum(g['r0'])} ign={g['ign']} prev={g['prev']}")
        for lo, hi in [(0, 150000), (150000, 500000)]:
            acc = {}
            for t, e in data.items():
                if lo < t <= hi and "out" in e:
                    add(acc, {k: e[k] for k in ["out", "ign", "end"]})
            if "out" not in acc:
                continue
            o, g, en = acc["out"], acc["ign"], acc["end"]
            n = o["n"]
            wt = {k: sum(v) for k, v in o["w"].items()}
            print(f"\n## ({lo//1000}k,{hi//1000}k] foreign-written strict losses n={n} victim_start0={o['v0']} ({pct(o['v0'], n):.1f}%)")
            print("  writer status share%:", {k: f"{pct(v, n):.1f}" for k, v in wt.items()},
                  " by age (<1k/1k-10k/>=10k):", o["w"])
            print("  writer kind self/copy/reig/seeded:", o["kind"], " writer_start0:", o["wstart0"], f"({pct(o['wstart0'], n):.1f}%)",
                  " not_mov:", o["not_mov"], " src_own:", o["src_own"], f"({pct(o['src_own'], n):.1f}%)")
            print(f"  dir fill (victim pointer-direction INERT byte filled): {o['dir']} ({pct(o['dir'], n):.1f}%), only dir: {o['dir_only']} ({pct(o['dir_only'], n):.1f}%)")
            print("  writer_ip:", top(o["wip"], 10))
            print("  offsets:", top(o["offs"], 24))
            print("  dir offsets:", top(o["diroffs"], 10))
            tot_off = sum(g["roff"])
            ig = {k: sum(v) for k, v in g["ign"].items()}
            print(f"  strict births: start0 {sum(g['r0'])} (self/copy/reig {g['r0']}), off0 {tot_off} (self/copy/reig {g['roff']}) "
                  f"= {pct(tot_off, tot_off + sum(g['r0'])):.1f}%; all births {g['births']} off0 {g['off0']} ({pct(g['off0'], g['births']):.1f}%)")
            print("  off0 strict igniters share%:", {k: f"{pct(v, tot_off):.1f}" for k, v in ig.items()}, " by age:", g["ign"])
            print(f"  off0 same key as igniter: {g['same']} ({pct(g['same'], tot_off):.1f}%); previous activation strict+wick start0/off0: {g['prev']} "
                  f"({pct(sum(g['prev']), tot_off):.1f}%), mean gap {g['gap']/max(sum(g['prev']),1):.0f}")
            print("  igniter_ip:", top(g["iip"], 10))
            print("  entry:", top(g["entry"], 12))
            s0, s1 = en
            print(f"  strict ends start0 decay/wick={s0[0]}/{s0[1]} mean life {s0[2]/max(s0[0]+s0[1],1):.0f} copies {s0[3]}; "
                  f"off0 decay/wick={s1[0]}/{s1[1]} mean life {s1[2]/max(s1[0]+s1[1],1):.0f} copies {s1[3]}")


if __name__ == "__main__":
    main()
