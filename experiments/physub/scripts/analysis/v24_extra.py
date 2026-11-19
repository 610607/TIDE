"""v24 extra numbers: env children with offset 30 foreign-written, late level shares,
strict entry-0 counts, re-ignition drops. Usage: v24_extra.py <dir> (EARLY / LATE env)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import load, ledger, ROUTES, CLS
from v24_decomp import rates, PUSH, EARLY, LATE
D = sys.argv[1]
RUNS = ["zero_s1", "zero_s2", "fail_s1", "fail_s2"]
W = {r: load(f"{D}/{r}.tsv") for r in RUNS}
def env30_rate(w, ticks):
    acc = 0.0; ticks = [t for t in ticks if t in w and "e0" in w[t]]
    for t in ticks:
        r = ledger(w[t]); e = w[t]["env"]
        acc += r["N_env"] * (e["has30"] / e["n"] if e["n"] else 0) / r["S"] / 10 / len(ticks)
    return acc
for r in RUNS:
    e, l = rates(W[r], EARLY), rates(W[r], LATE)
    push = {t: s * (l[t] - e[t]) for t, s in PUSH.items()}; Dr = sum(push.values())
    e30, l30 = env30_rate(W[r], EARLY), env30_rate(W[r], LATE)
    out = l["decay"] + l["wick"] + sum(l["L_" + k] for k in ROUTES) + sum(l["N_" + c] for c in CLS if c != "exact")
    lv = lambda ts: 100 * sum(l[t] for t in ts) / out
    print(f"{r}: D={Dr:.3f} env30 early {e30:.4f} late {l30:.4f} push {100*(l30-e30)/Dr:.1f}% of D "
          f"(env push {100*push['N_env']/Dr:.1f}%) | late outflow {out:.3f}: f30 {lv(['L_f30_mov15','L_f30_other']):.1f} "
          f"mov15 {lv(['L_f30_mov15']):.1f} gap {lv(['N_gap']):.1f} env {lv(['N_env']):.1f} multi {lv(['N_multi']):.1f} "
          f"decay {lv(['decay']):.1f} point {lv(['N_point']):.1f} other-inplace {lv(['L_f_ptr','L_f_tail','L_f_other','L_self_0','L_self_other']):.1f} wick {lv(['wick']):.1f}"
          f" | reig0 {e['reig0']:.3f}->{l['reig0']:.3f} ({l['reig0']-e['reig0']:+.3f}, {100*push['reig0']/Dr:.1f}% of D) P {e['P']:.3f}->{l['P']:.3f}")
    print("   S0:", " ".join(f"{t//1000}k:{W[r][t]['e0']['now']}" for t in sorted(W[r]) if "e0" in W[r][t]),
          "| off now:", " ".join(str(W[r][t]['eo']['now']) for t in sorted(W[r]) if "eo" in W[r][t]))
    offb = [sum(W[r][t]["eo"]["born"]) for t in sorted(W[r]) if "eo" in W[r][t]]
    reig = [W[r][t]["e0"]["born"][2] for t in sorted(W[r]) if "e0" in W[r][t]]
    s0 = [sum(W[r][t]["eo"]["loss"]["self_0"]) for t in sorted(W[r]) if "eo" in W[r][t]]
    offL = [sum(sum(v) for v in W[r][t]["eo"]["loss"].values()) for t in sorted(W[r]) if "eo" in W[r][t]]
    print("   off births", offb, "\n   reig0", reig, "\n   off losses", offL, "self_0", s0)
