"""v25 analysis: python3 v25_an.py runs/v25"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from v25_len import load, CATS, TSRC, ISRC, WR, FIELDS, ZBINS, EXT
D = sys.argv[1]
RUNS = [r for r in ["zero_s1", "zero_s2", "fail_s1", "fail_s2", "zero_nomut_s1", "fail_nomut_s1"]
        if os.path.exists(f"{D}/{r}.tsv") and os.path.getsize(f"{D}/{r}.tsv")]
P = 1.95e-6
PTR = [34, 36, 38, 40]; TAIL = list(range(46, 64))
def grp(d, ks): return sum(d.get(k, 0) for k in ks)
def f(x, n=3): return f"{x:.{n}f}"
EARLY = (50000, 150000); LATE = (350000, 500000)
for r in RUNS:
    W = load(f"{D}/{r}.tsv"); T = sorted(W)
    print(f"\n===== {r} windows={len(T)} last={T[-1]}")
    bad = [(t, W[t]["check"], W[t]["dmean"] - W[t]["sum_dm"]) for t in T if W[t]["check"][:2] != [0, 0] or abs(W[t]["dmean"] - W[t]["sum_dm"]) > 1e-9]
    print("checks bad:", bad, " empty:", [W[t]["check"][2] for t in T])
    print("tick  n  mean  dmean | trans psel other_in | decay wick loss_f loss_s | inpl_f inpl_s")
    tot = {}
    for t in T:
        w = W[t]; c = {k: v[2] for k, v in w["cat"].items()}
        g = dict(trans=w["trans"], psel=c["copy_sp"] - w["trans"],
                 other_in=c["copy_op"] + c["reignite"] + c["self"] + c["gain"] + c["found"],
                 decay=c["decay"], wick=c["wick"], loss_f=c["loss_f"], loss_s=c["loss_s"],
                 inpl_f=c["inplace_f"], inpl_s=c["inplace_s"])
        for k, v in g.items(): tot[k] = tot.get(k, 0) + v
        print(t, w["n"][1], f(w["mean"][1]), f(w["dmean"]), "|", " ".join(f(g[k]) for k in g))
    print("TOTAL", f(W[T[-1]]["mean"][1] - 40.0), "|", " ".join(f"{k}={f(v)}" for k, v in tot.items()))
    # 50k-500k excluding the first window (founder transient)
    tot2 = {}
    for t in T[1:]:
        w = W[t]; c = {k: v[2] for k, v in w["cat"].items()}
        for k, v in dict(trans=w["trans"], psel=c["copy_sp"] - w["trans"], other_in=c["copy_op"] + c["reignite"] + c["self"] + c["gain"],
                         decay=c["decay"], wick=c["wick"], loss_f=c["loss_f"], loss_s=c["loss_s"], inpl_f=c["inplace_f"], inpl_s=c["inplace_s"]).items():
            tot2[k] = tot2.get(k, 0) + v
    if len(T) > 1:
        print("50k->end", f(W[T[-1]]["mean"][1] - W[T[0]]["mean"][1]), "|", " ".join(f"{k}={f(v)}" for k, v in tot2.items()))
    # entries/exits counts and mean z per category, pooled after 50k
    print("cat counts/meanz (after first window):")
    for cat in CATS:
        n = sum(W[t]["cat"][cat][0] for t in T[1:]); z = sum(W[t]["cat"][cat][1] for t in T[1:])
        print(f"  {cat}: n={n} zsum={z} mean={z/n if n else 0:.2f}", end="")
    print()
    zp = sum(W[t]["zp"] for t in T[1:]); ncs = sum(W[t]["cat"]["copy_sp"][0] for t in T[1:])
    print(f"  copy_sp parents mean z={zp/max(1,ncs):.2f}  mean(child-parent)={sum(W[t]['cat']['copy_sp'][1] for t in T[1:])/max(1,ncs):.4f}")
    # sources
    def pool(key, ts):
        out = {}
        for t in ts:
            for k, v in W[t][key].items(): out[k] = out.get(k, 0) + (v[0] if isinstance(v, tuple) else v)
        return out
    for lab, ts in [("all", T), ("early", [t for t in T if EARLY[0] <= t <= EARLY[1]]), ("late", [t for t in T if LATE[0] <= t <= LATE[1]])]:
        if not ts: continue
        ts_ = pool("tsrc", ts); is_ = pool("isrc", ts); iwc = [sum(W[t]["iwc"][i] for t in ts) for i in range(6)]
        subs = sum(W[t]["subs"] for t in ts); ncopy = sum(W[t]["cat"]["copy_sp"][0] for t in ts)
        dmt = {k: sum(W[t]["tsrc"][k][1] for t in ts) for k in TSRC}
        addin = sum(is_[k] for k in ISRC[:5])
        print(f" [{lab}] strict copies by strict0 parents={ncopy} trans bytes:", ts_, "subs", subs, "dm_trans", {k: f(v, 3) for k, v in dmt.items()})
        print(f" [{lab}] inplace bytes:", is_, "add total", addin, "shares:", {k: f(is_[k] / addin, 3) for k in ISRC[:5]} if addin else "")
        print(f" [{lab}] foreign add writer (rep/loose/prop/other/self/none):", iwc, [f(x / max(1, sum(iwc)), 3) for x in iwc])
        # per offset in place adds by group
        io = {}
        for t in ts:
            for k, v in W[t]["ioff"].items():
                if k not in io: io[k] = [0] * len(v)
                io[k] = [a + b for a, b in zip(io[k], v)]
        to = {}
        for t in ts:
            for k, v in W[t]["toff"].items():
                if k not in to: to[k] = [0] * len(v)
                to[k] = [a + b for a, b in zip(to[k], v)]
        def gsum(d, ks, idx): return sum(d[k][i] for k in ks if k in d for i in idx)
        print(f" [{lab}] inplace adds by offset group (aligned/shift/nbrsrc/other/self):",
              {g: [gsum(io, ks, [i]) for i in range(5)] for g, ks in [("30", [30]), ("ptr", PTR), ("tail", TAIL), ("rest", ["rest"])]})
        print(f" [{lab}] trans by offset group (res/for/par/lgap/lpar/lfor):",
              {g: [gsum(to, ks, [i]) for i in range(6)] for g, ks in [("30", [30]), ("ptr", PTR), ("tail", TAIL), ("rest", ["rest"])]})
    # standing occupancy + exits use
    print(" standing filled per site (30/ptr/tail) at window end:")
    for t in T:
        w = W[t]; n = w["alive_n"]
        print(f"   {t}: n={n} 30={w['alive'][30]/n:.3f} ptr={grp(w['alive'], PTR)/n:.3f} tail={grp(w['alive'], TAIL)/n:.3f}  ptr_each={[round(w['alive'][k]/n,3) for k in PTR]}")
    ex = {}
    for t in T:
        for k, v in W[t]["ex"].items(): ex[k] = [a + b for a, b in zip(ex.get(k, [0, 0, 0]), v)]
    exn = sum(W[t]["ex_n"] for t in T)
    for g, ks in [("30", [30]), ("ptr", PTR), ("tail", TAIL)]:
        n = sum(ex[k][0] for k in ks); e = sum(ex[k][1] for k in ks); c = sum(ex[k][2] for k in ks)
        print(f"  exits={exn} {g}: filled={n} executed={e} ({e/max(1,n):.3f}) control={c} ({c/max(1,n):.3f})")
    print("  per ptr exec/ctl:", {k: (ex[k][0], ex[k][1], ex[k][2]) for k in PTR})
    # bins
    for lab, ts in [("early", [t for t in T if EARLY[0] <= t <= EARLY[1]]), ("late", [t for t in T if LATE[0] <= t <= LATE[1]]), ("all", T)]:
        if not ts: continue
        print(f" [{lab}] bin: expo_share copies/5k strict/copy exact/copy decay/5k n_eff wick/5k loss_f/5k loss_s/5k net/5k")
        tot_e = sum(W[t]["bins"][b][0] for t in ts for b in ZBINS)
        for b in ZBINS:
            v = [sum(W[t]["bins"][b][i] for t in ts) for i in range(8)]
            e = v[0]
            if e == 0: continue
            cp = v[1] / e * 5000; sf = v[2] / max(1, v[1]); ef = v[3] / max(1, v[1])
            de = v[4] / e; neff = -__import__("math").log(1 - de) / -__import__("math").log(1 - P) if de < 1 else 0
            net = (v[2] - v[4] - v[5] - v[6] - v[7]) / e * 5000
            print(f"   {b:>6} {e/tot_e:.3f} {cp:.3f} {sf:.3f} {ef:.3f} {de*5000:.3f} {neff:.1f} {v[5]/e*5000:.4f} {v[6]/e*5000:.4f} {v[7]/e*5000:.4f} {net:+.3f}  (copies={v[1]})")
        print(f" [{lab}] comp:")
        for cname in sorted(W[ts[0]]["comp"]):
            v = [sum(W[t]["comp"][cname][i] for t in ts) for i in range(8)]
            e = v[0]
            if e == 0: continue
            de = v[4] / e
            print(f"   {cname} {e/tot_e:.3f} cp={v[1]/e*5000:.3f} sf={v[2]/max(1,v[1]):.3f} ef={v[3]/max(1,v[1]):.3f} dec={de*5000:.3f} neff={de/P:.1f} lossf={v[6]/e*5000:.4f} net={(v[2]-v[4]-v[5]-v[6]-v[7])/e*5000:+.3f} copies={v[1]}")
    # pointer state (lengthptr)
    if "ptr" in W[T[0]]:
        for lab, ts in [("early", [t for t in T if EARLY[0] <= t <= EARLY[1]]), ("late", [t for t in T if LATE[0] <= t <= LATE[1]]), ("all", T)]:
            if not ts: continue
            names = list(W[ts[0]]["ptr"])
            totb = sum(W[t]["ptr"][n][1][0] for t in ts for n in names)
            totw = sum(W[t]["ptr"][n][2][0] for t in ts for n in names)
            totm = sum(W[t]["ptr"][n][1][3] for t in ts for n in names)
            print(f" [{lab}] ptr: class live(mean) | copies share strict/copy exact/copy multi env | mov15 adds share by_rep | multi share")
            for n in names:
                live = sum(W[t]["ptr"][n][0] for t in ts) / len(ts)
                pb = [sum(W[t]["ptr"][n][1][i] for t in ts) for i in range(5)]
                pw = [sum(W[t]["ptr"][n][2][i] for t in ts) for i in range(2)]
                print(f"   {n:9} {live:8.1f} | {pb[0]:6d} {pb[0]/max(1,totb):.3f} {pb[1]/max(1,pb[0]):.3f} {pb[2]/max(1,pb[0]):.3f} {pb[3]:5d} {pb[4]:5d} | {pw[0]:6d} {pw[0]/max(1,totw):.3f} {pw[1]/max(1,pw[0]):.3f} | {pb[3]/max(1,totm):.3f}")
            sh = {}
            for t in ts:
                for k, v in W[t]["shift"].items(): sh[k] = sh.get(k, 0) + v
            tot = sum(sh.values())
            print(f" [{lab}] shift adds by (src-dst) mod 64, top:", sorted(sh.items(), key=lambda kv: -kv[1])[:12], "total", tot)
