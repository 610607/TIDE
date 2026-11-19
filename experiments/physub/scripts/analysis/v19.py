#!/usr/bin/env python3
"""Summarize v19 fate runs. Usage: v19.py <runs/v19> [run ...]"""
import re
import sys
from pathlib import Path

ST = ["rep", "loose", "prop", "other"]
WR = ["rep", "loose", "prop", "other", "self", "none"]


def kv(line):
    return {k.strip("("): v.strip(")") for k, v in re.findall(r"(\S+?)=(\S+)", line)}


def nums(s):
    return [int(x) for x in s.split("/")]


def load(path):
    data = {}
    for line in open(path):
        if not line.startswith("# fate"):
            continue
        tag = line.split()[1]
        d = kv(line)
        t = int(d["tick"])
        e = data.setdefault(t, {})
        if tag == "fate":
            e["fate"] = d
        elif tag == "fateborn":
            e["born"] = {s: nums(d[s]) for s in ST}
        elif tag == "fateend":
            e["end"] = {s: nums(d[s]) for s in ST}
            e["end_conv"] = nums(d["converted"])
        elif tag == "fatechange":
            m = dict(re.findall(r"(rep|loose|prop|other)>(\S+)", line))
            e["change"] = {s: nums(m[s]) for s in ST}
            e["other_untested"] = int(d["other_untested"])
            e["found"] = nums(d["found_at_census"])
            w = dict(re.findall(r"(rep|loose|prop|other):(\S+)", line.split("writers")[1]))
            e["change_writer"] = {s: nums(w[s]) for s in ST}
        elif tag == "fateout":
            e["out"] = d
            if "offsets_foreign:" in line:
                fo, se = line.split("offsets_foreign:")[1].split("offsets_self:")
                e["out_offsets_foreign"] = re.findall(r"(\d+):(\d+)", fo)
                e["out_offsets_self"] = re.findall(r"(\d+):(\d+)", se)
                e["out_offsets"] = e["out_offsets_foreign"]
            else:
                e["out_offsets"] = re.findall(r"(\d+):(\d+)", line.split("offsets:")[1])
            bt = line.split("by_to")[1].split("src_ptr")[0]
            e["out_to"] = {k: nums(v) for k, v in re.findall(r"(loose|prop|other):(\S+)", bt)}
            e["src_writer"] = nums(d["src_writer"])
            e["src_names"] = int(d["src_names_writer"])
        elif tag == "fateconv":
            e["conv"] = kv(line.split(" fill:")[0])
            if " fill:" in line:
                e["fill"] = kv(line.split(" fill:")[1])
        elif tag == "fatestart":
            e["start"] = {k: nums(d[k]) for k in ["out_start0", "self_start0", "born_rep_start0"]}
            e["self_at"] = re.findall(r"(\d+):(\d+)", line.split("self_instr_at:")[1])
    return data


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def row(r, t, e):
    f, o, c = e["fate"], e["out"], e["conv"]
    rp, rn = int(f["rep_prev"]), int(f["rep_now"])
    born = nums(f["born_copy/reignite/self"])
    dec, wick = int(f["end_decay"]), int(f["end_wick"])
    out, inn = int(f["out_in_place"]), int(f["in_in_place"])
    found = int(f["found_at_census"])
    loss = dec + wick + out
    src = int(o["with_src"])
    return dict(run=r, t=t, rp=rp, rn=rn, born=born, dec=dec, wick=wick, out=out, inn=inn,
                found=found, loss=loss, src=src, only=int(o["only_src"]),
                jump=nums(o["jump_0/op/other"]), bal=int(f["balance"]),
                mis=int(f["census_mismatch"]), untr=int(f["untracked"]), stale=int(f["stale"]),
                repl=int(f["replaced"]), starved=int(f["starved"]),
                writer={k: int(o[k]) for k in WR}, vol=int(o["vol_foreign_rep"]),
                conv=c, offs=e["out_offsets"], end_conv=e["end_conv"], e=e,
                out_to=e["out_to"], srcw=e["src_writer"], src_names=e["src_names"],
                src_foreign=sum(e["src_writer"][:4]) + e["src_writer"][5],
                src_self=e["src_writer"][4])


def main():
    root = Path(sys.argv[1])
    runs = sys.argv[2:] or ["m195_s1", "m195_s2", "nomut_s1", "nomut_s2"]
    rows = []
    for r in runs:
        p = root / f"{r}.tsv"
        if not p.exists():
            continue
        for t, e in sorted(load(p).items()):
            if "fate" in e:
                rows.append(row(r, t, e))

    print("## checks: balance == rep_now, census_mismatch, untracked, stale, replaced")
    for x in rows:
        ok = x["bal"] == x["rn"]
        print(f"{x['run']} {x['t']//1000}k bal={x['bal']} rep_now={x['rn']} ok={ok} "
              f"mis={x['mis']} untr={x['untr']} stale={x['stale']} repl={x['repl']} "
              f"starved={x['starved']}")

    print("\n## strict flows per 50k window")
    print("run tick | prev->now (net) | born copy/reig/self | in place in (census) | "
          "end decay | end wick | out in place | loss shares decay/wick/out %")
    for x in rows:
        b = x["born"]
        print(f"{x['run']} {x['t']//1000}k | {x['rp']}->{x['rn']} ({x['rn']-x['rp']:+d}) | "
              f"{b[0]}/{b[1]}/{b[2]} | {x['inn']} ({x['found']}) | {x['dec']} | {x['wick']} | "
              f"{x['out']} | {pct(x['dec'], x['loss']):.1f}/{pct(x['wick'], x['loss']):.1f}/"
              f"{pct(x['out'], x['loss']):.1f}")

    print("\n## in-place strict losses: offset 30, writers, jump target")
    print("run tick | out | with_src (only) % | writer rep/loose/prop/other/self/none | "
          "jump 0/op/other | vol_foreign_rep | top offsets")
    for x in rows:
        w = x["writer"]
        print(f"{x['run']} {x['t']//1000}k | {x['out']} | {pct(x['src'], x['out']):.1f} "
              f"({pct(x['only'], x['out']):.1f}) | "
              f"{'/'.join(str(w[k]) for k in WR)} | {'/'.join(map(str, x['jump']))} | "
              f"{x['vol']} | {' '.join(f'{k}:{n}' for k, n in x['offs'][:6])}")

    print("\n## in-place strict losses by status after (writers rep/loose/prop/other/self/none) "
          "and offset-30 writers")
    for x in rows:
        bt = " ".join(f"to_{k}={sum(v)}({'/'.join(map(str, v))})" for k, v in x["out_to"].items())
        print(f"{x['run']} {x['t']//1000}k out={x['out']} {bt} | src={x['src']} "
              f"self={x['src_self']} foreign={x['src_foreign']} "
              f"(writer {'/'.join(map(str, x['srcw']))}) names_writer={x['src_names']}")

    print("\n## ignition offsets and self-writing instructions")
    for x in rows:
        st = x["e"].get("start")
        if not st:
            continue
        print(f"{x['run']} {x['t']//1000}k out_start0={st['out_start0'][0]}/{st['out_start0'][1]} "
              f"self_start0={st['self_start0'][0]}/{st['self_start0'][1]} "
              f"born_rep_start0={st['born_rep_start0'][0]}/{st['born_rep_start0'][1]} "
              f"self_at {' '.join(f'{k}:{n}' for k, n in x['e']['self_at'][:8])}")

    print("\n## converted activations: copies and their children; ends")
    for x in rows:
        c = x["conv"]
        n = int(c["copies"])
        print(f"{x['run']} {x['t']//1000}k alive={c['alive']} copies={n} "
              f"child_rep={pct(int(c['child_rep']), n):.1f}% "
              f"child_same={pct(int(c['child_same']), n):.1f}% "
              f"child_src={pct(int(c['child_src']), n):.1f}% "
              f"ends decay/wick={x['end_conv'][0]}/{x['end_conv'][1]}")

    print("\n## in-place change matrix and writers (from status: to rep/loose/prop/other)")
    for x in rows:
        e = x["e"]
        ch = " ".join(f"{s}>{'/'.join(map(str, e['change'][s]))}" for s in ST[:3])
        wr = " ".join(f"{s}:{'/'.join(map(str, e['change_writer'][s]))}" for s in ST)
        print(f"{x['run']} {x['t']//1000}k {ch} other_untested={e['other_untested']} "
              f"found={'/'.join(map(str, e['found']))} | writers {wr}")

    print("\n## ends by status (decay/wick) and births by status (copy/reignite/self)")
    for x in rows:
        e = x["e"]
        en = " ".join(f"{s}={e['end'][s][0]}/{e['end'][s][1]}" for s in ST)
        bo = " ".join(f"{s}={'/'.join(map(str, e['born'][s]))}" for s in ST)
        print(f"{x['run']} {x['t']//1000}k ends {en} | born {bo}")

    print("\n## totals over 150k-500k (windows ending 200k..500k) and 0-150k")
    for r in runs:
        for lo, hi in [(0, 150000), (150000, 500000)]:
            xs = [x for x in rows if x["run"] == r and lo < x["t"] <= hi]
            if not xs:
                continue
            s = lambda k: sum(x[k] for x in xs)
            born = [sum(x["born"][i] for x in xs) for i in range(3)]
            loss = s("loss")
            conv = sum(int(x["conv"]["copies"]) for x in xs)
            csrc = sum(int(x["conv"]["child_src"]) for x in xs)
            crep = sum(int(x["conv"]["child_rep"]) for x in xs)
            wsum = {k: sum(x["writer"][k] for x in xs) for k in WR}
            print(f"{r} ({lo//1000}k,{hi//1000}k] net={xs[-1]['rn']-xs[0]['rp']:+d} "
                  f"born={born[0]}/{born[1]}/{born[2]} in={s('inn')} loss={loss} "
                  f"decay={s('dec')} ({pct(s('dec'), loss):.1f}%) wick={s('wick')} "
                  f"({pct(s('wick'), loss):.1f}%) out={s('out')} ({pct(s('out'), loss):.1f}%) "
                  f"src_foreign={s('src_foreign')} ({pct(s('src_foreign'), loss):.1f}% of loss, "
                  f"{pct(s('src_foreign'), s('out')):.1f}% of out) src_self={s('src_self')} "
                  f"to_loose={sum(sum(x['out_to']['loose']) for x in xs)} "
                  f"to_prop={sum(sum(x['out_to']['prop']) for x in xs)} "
                  f"to_other={sum(sum(x['out_to']['other']) for x in xs)} "
                  f"out_src={s('src')} ({pct(s('src'), loss):.1f}% of loss, "
                  f"{pct(s('src'), s('out')):.1f}% of out; only {pct(s('only'), s('out')):.1f}%) "
                  f"net_in_place={s('inn')-s('out'):+d} writers={wsum} "
                  f"conv_copies={conv} child_src={pct(csrc, conv):.1f}% "
                  f"child_rep={pct(crep, conv):.1f}%")


if __name__ == "__main__":
    main()
