"""v24 per-site rate decomposition. Usage: v24_decomp.py run.tsv... (early/late windows by env
EARLY="100000,150000" LATE="350000,400000,450000,500000").
Rates are per strict entry-0 site per 5k ticks (window count / mean count / 10)."""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import load, ledger, ROUTES, CLS
EARLY = [int(x) for x in os.environ.get("EARLY", "100000,150000").split(",")]
LATE = [int(x) for x in os.environ.get("LATE", "350000,400000,450000,500000").split(",")]
TERMS = (["P", "delta", "reig0", "gain", "decay", "wick"] + ["L_" + r for r in ROUTES] +
         ["N_" + c for c in CLS if c != "exact"] + ["dS"])
def rates(W, ticks):
    acc = {t: 0.0 for t in TERMS}
    ticks = [tk for tk in ticks if tk in W and "e0" in W[tk]]
    for tk in ticks:
        r = ledger(W[tk]); S = r["S"]
        v = {"P": r["copies"], "delta": r["born_copy0"] - r["strict_copies"], "reig0": r["reig0"],
             "gain": r["gain"], "decay": r["decay"], "wick": r["wick"], "dS": r["dS"]}
        for k in ROUTES: v["L_" + k] = r["L_" + k]
        for c in CLS:
            if c != "exact": v["N_" + c] = r["N_" + c]
        for t in TERMS: acc[t] += v[t] / S / 10 / len(ticks)
    return acc
PUSH = {"decay": 1, "wick": 1, **{"L_" + r: 1 for r in ROUTES}, **{"N_" + c: 1 for c in CLS if c != "exact"},
        "reig0": -1, "gain": -1, "delta": -1}
out = {}
for path in (sys.argv[1:] if __name__ == "__main__" else []):
    W = load(path); name = path.split("/")[-1].replace(".tsv", "")
    e, l = rates(W, EARLY), rates(W, LATE)
    # identity per window: P - sum N + delta + reig0 + gain - decay - wick - sum L = dS
    chk = max(abs(x["P"] - sum(x["N_" + c] for c in CLS if c != "exact") + x["delta"] + x["reig0"] + x["gain"]
                  - x["decay"] - x["wick"] - sum(x["L_" + r] for r in ROUTES) - x["dS"]) for x in (e, l))
    push = {t: s * (l[t] - e[t]) for t, s in PUSH.items()}
    D = sum(push.values())
    out[name] = (e, l, push, D)
    print(f"== {name}  identity residual {chk:.2e}  D={D:.4f}  dP={l['P']-e['P']:.4f}  d(dS)={l['dS']-e['dS']:.4f}")
    for t in TERMS:
        ps = f"{100*push[t]/D:+6.1f}%" if t in push else ""
        print(f"  {t:14s} early {e[t]:.4f}  late {l[t]:.4f}  change {l[t]-e[t]:+.4f}  {ps}")
