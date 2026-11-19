"""v28 compact rows for the README. Usage: v28_tab.py run.tsv... (role=1 outputs)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import ROUTES
from v28_an import load, total, pct, CLS

def row(name, T):
    d = T[0]
    L = sum(sum(v) for v in d["loss"].values()); K = sum(d["kept"].values())
    cls = [sum(d["loss"][r][i] for r in ROUTES) for i in range(len(CLS))]
    rs = {r: sum(d["loss"][r]) for r in ROUTES}
    selfn = rs["self_0"] + rs["self_other"]
    self_dir = d["loss"]["self_other"][0] + d["loss"]["self_0"][0]
    fdo = d["fdo"]
    off = " ".join(f"{k}:{pct(fdo.get(k, 0), L):.1f}" for k in (36, 30, 38, 40, 34))
    G = sum(d["gain"])
    print(f"{name}: L={L} kept={pct(K, L):.1f}% dir_only={pct(cls[0], L):.1f}% dir_mixed={cls[1]} "
          f"| off% {off} | f30={pct(rs['f30_mov15'] + rs['f30_other'], L):.1f} f_ptr={pct(rs['f_ptr'], L):.1f} "
          f"f_tail={pct(rs['f_tail'], L):.1f} f_other={pct(rs['f_other'], L):.1f} self={pct(selfn, L):.1f} "
          f"(self dir_only {pct(self_dir, L):.1f}) | none={pct(cls[5], L):.1f} opnd={pct(cls[2], L):.1f} "
          f"val={pct(cls[3], L):.1f} sub={pct(cls[4], L):.1f} | gains={G} undone={d['undone']} "
          f"({pct(d['undone'], G):.1f}%) gain_dir_only={d['gain'][0]}")
    e = T[1]
    Le = sum(sum(v) for v in e["loss"].values()); Ke = sum(e["kept"].values())
    print(f"   entry_off: L={Le} kept={Ke} ({pct(Ke, Le):.1f}%) sub={pct(sum(e['loss'][r][4] for r in ROUTES), Le):.1f}%"
          f" gains={sum(e['gain'])} undone={e['undone']}")
    l = T["len"]
    dm = l["lbdm_foreign"]; b = l["lb_foreign"]
    s = sum(dm)
    print(f"   inplace_f credit {s:+.2f}: dir {dm[0]:+.2f} ({pct(dm[0], s):.0f}%) none {dm[3]:+.2f} "
          f"({pct(dm[3], s):.0f}%) opnd {dm[1]:+.2f} val {dm[2]:+.2f} | bytes dir {b[0]} none {b[3]} "
          f"| self {sum(l['lbdm_self']):+.3f}")
    x = l["loss_f_dm"]
    print(f"   exit loss_f {sum(x):+.2f}: dir_only {x[0]:+.2f} kept {l['loss_f_kdm']:+.2f} "
          f"({pct(l['loss_f_kdm'], sum(x)):.0f}%) n={sum(l['loss_f'])} kept_n={l['loss_f_kept']} "
          f"| loss_s {sum(l['loss_s_dm']):+.2f}")
    tr = {k: l["tr_" + k] for k in ("residue", "foreign", "parent")}
    print("   copy adds dir%: " + " ".join(f"{k} {pct(v[0], sum(v)):.1f} (n={sum(v)})" for k, v in tr.items()) +
          f" | env n={l['env_n']} dir_any {pct(l['env_dir_any'], l['env_n']):.1f}% "
          f"dir_only {pct(l['env_dir_only'], l['env_n']):.1f}%")
    print("   add_dir_off foreign:", sorted(l["adf"].items(), key=lambda x: -x[1])[:4])

for path in sys.argv[1:]:
    W = load(path); name = path.split("/")[-1].replace(".tsv", "")
    for lo, hi, lab in ((0, 10**9, "all"), (150000, 10**9, "after150k")):
        T = total(W, lo, hi)
        if T: row(f"{name} {lab}", T)
