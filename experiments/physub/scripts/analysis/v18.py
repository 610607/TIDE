#!/usr/bin/env python3
"""Summarize v18 fidelity runs. Usage: v18.py <runs/v18> [scan.tsv]"""
import re
import sys
from pathlib import Path

RUNS = ["m195_s1", "m195_s2", "t2_s1", "t3_s1"]


def kv(line):
    return dict(re.findall(r"(\S+?)=(\S+)", line))


def classes(d):
    out = {}
    for c in ["exact", "point", "gap", "multi", "env", "parent_filled"]:
        raw = d.get(c, d.get("shift")) if c == "multi" else d[c]
        m = re.match(r"(\d+)\((\d+)\)", raw)
        out[c] = (int(m.group(1)), int(m.group(2)))
    return out


def load(path):
    data = {}
    for line in open(path):
        if not line.startswith("# "):
            continue
        d = kv(line)
        if "tick" not in d:
            continue
        t = int(d["tick"])
        e = data.setdefault(t, {"fidcopy": {}, "fidtop": []})
        if line.startswith("# fidcopy"):
            d["cls"] = classes(kv(line.split("diffs/birth:")[0]))
            e["fidcopy"][d["parent"]] = d
        elif line.startswith("# fidtop"):
            e["fidtop"].append(d)
        elif line.startswith("# census"):
            e["census"] = d
        elif line.startswith("# lineage"):
            e["lineage"] = d
        elif line.startswith("# fidelity"):
            e["fidelity"] = d
        elif line.startswith("# fidgeno"):
            e["fidgeno"] = d
        elif line.startswith("# fidreig"):
            e["fidreig"] = d
    return data


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def main():
    root = Path(sys.argv[1])
    all_data = {r: load(root / f"{r}.tsv") for r in RUNS if (root / f"{r}.tsv").exists()}
    ticks = sorted({t for d in all_data.values() for t in d if t % 50000 == 0})

    print("## copy births by parent status (window 5000): births share% and child strict%")
    print("run tick | rep n (strict%) | loose n | prop n | other n (strict%) | rep share of copies%")
    for r, d in all_data.items():
        for t in ticks:
            if t not in d or "rep" not in d[t]["fidcopy"]:
                continue
            fc = d[t]["fidcopy"]
            n = {k: int(fc[k]["births"]) for k in fc}
            tot = sum(n.values())
            print(f"{r} {t//1000}k | {n['rep']} ({float(fc['rep']['child_strict%']):.1f}) | "
                  f"{n['loose']} ({float(fc['loose']['child_strict%']):.1f}) | {n['prop']} | "
                  f"{n['other']} ({float(fc['other']['child_strict%']):.1f}) | {pct(n['rep'], tot):.1f}")

    print("\n## rep parents: class shares% of copies, and strict share within class")
    print("run tick | exact | point (strict%) | gap | multi | env (strict%) | filled (strict%) | strict% | len")
    for r, d in all_data.items():
        for t in ticks:
            if t not in d or "rep" not in d[t]["fidcopy"]:
                continue
            f = d[t]["fidcopy"]["rep"]
            c = f["cls"]
            n = int(f["births"])
            s = lambda k: f"{pct(c[k][0], n):.1f}"
            w = lambda k: f"{pct(c[k][1], c[k][0]):.0f}"
            print(f"{r} {t//1000}k | {s('exact')} | {s('point')} ({w('point')}) | {s('gap')} | "
                  f"{s('multi')} ({w('multi')}) | {s('env')} ({w('env')}) | {s('parent_filled')} ({w('parent_filled')}) | "
                  f"{float(f['child_strict%']):.1f} | {float(f['parent_len']):.1f}")

    print("\n## losses among rep-parent copies (percentage points of all rep-parent copies)")
    print("run tick | point loss | gap loss | multi loss | env loss | total loss")
    for r, d in all_data.items():
        for t in ticks:
            if t not in d or "rep" not in d[t]["fidcopy"]:
                continue
            f = d[t]["fidcopy"]["rep"]
            c = f["cls"]
            n = int(f["births"])
            loss = {k: pct(c[k][0] - c[k][1], n) for k in ["exact", "point", "gap", "multi", "env"]}
            print(f"{r} {t//1000}k | {loss['point']:.1f} | {loss['gap']:.1f} | {loss['multi']:.1f} | "
                  f"{loss['env']:.1f} | {sum(loss.values()):.1f}")

    print("\n## lineage (active sites by status) and filled sites")
    for r, d in all_data.items():
        for t in ticks:
            if t not in d or "lineage" not in d[t]:
                continue
            l = d[t]["lineage"]
            act = sum(int(l[f"{s}_sites"]) for s in ["rep", "loose", "prop", "other"])
            print(f"{r} {t//1000}k active={act} rep={l['rep_sites']} loose={l['loose_sites']} "
                  f"prop={l['prop_sites']} other={l['other_sites']} filled rep/loose/prop/other="
                  f"{l['rep_filled']}/{l['loose_filled']}/{l['prop_filled']}/{l['other_filled']}")

    print("\n## fidelity window counts, genotype quartiles, re-ignitions")
    for r, d in all_data.items():
        for t in ticks:
            if t not in d or "fidelity" not in d[t]:
                continue
            f, g, ri = d[t]["fidelity"], d[t]["fidgeno"], d[t]["fidreig"]
            print(f"{r} {t//1000}k births={f['births']} s/c/r={f['self/copy/reignite']} "
                  f"blocked={f['ext_blocked']} conflicts={f['conflicts']} walled={f['walled']} | "
                  f"geno={g['rep_parent_genotypes']} min10={g['with_min10']} q={g['child_strict%_q25/q50/q75']} | "
                  f"reig strict%={ri['child_strict%']} igniter_rep%={ri['igniter_rep%']} same%={ri['same_as_igniter%']}")

    if len(sys.argv) > 2:
        print("\n## top genotypes: in-run strict share vs isolated first copies")
        rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[2])]
        head, rows = rows[0], rows[1:]
        for row in rows:
            x = dict(zip(head, row))
            print(f"{x['label']} {int(x['tick'])//1000}k r{x['rank']} {x['status']} n={x['run_births']} "
                  f"run={float(x['run_child_strict%']):.1f} iso={float(x['first_strict%']):.1f} "
                  f"(exact {float(x['first_exact%']):.1f}, multi {float(x['first_multi%']):.1f}) "
                  f"pred={float(x['pred%']):.1f} m={x['m']} ko={x['ko_nonstrict']}/{x['ko_n']} "
                  f"sens={float(x['sub_sensitive_len']):.1f}")


if __name__ == "__main__" and sys.argv[-1] != "len":
    main()


def length_parts(root):
    """Top genotypes: non-inert bytes in polite's region (0-45, volatile excluded), filled
    own-site pointer bytes (30, 34, 36, 38, 40) and the tail (46-63)."""
    vol = {31, 32, 33, 44}
    ptr = {30, 34, 36, 38, 40}
    for r in RUNS:
        for line in open(Path(root) / f"{r}.tsv"):
            if not line.startswith("# fidtop"):
                continue
            d = kv(line)
            key = bytes.fromhex(d["hex"])
            region = sum(1 for k in range(46) if k not in vol and key[k])
            filled = sum(1 for k in ptr if key[k])
            tail = sum(1 for k in range(46, 64) if key[k])
            print(f"{r} {int(d['tick'])//1000}k r{d['rank']} {d['status']} births={d['births']} "
                  f"strict%={d['child_strict%']} region={region} filled={filled} tail={tail}")


if __name__ == "__main__" and sys.argv[-1] == "len":
    length_parts(sys.argv[1])
