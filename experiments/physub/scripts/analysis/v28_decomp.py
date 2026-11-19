"""v28: shares of v24's D carried by in-place losses the counterfactual keeps, and by losses
by class. Usage: v28_decomp.py run.tsv... (role=1 outputs; EARLY/LATE as v24_decomp)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import v24_decomp as vd
from v24_routes import load as rload, ledger, ROUTES
from v28_an import load as lload, CLS
for path in sys.argv[1:]:
    W = rload(path); R = lload(path); name = path.split("/")[-1].replace(".tsv", "")
    e, l = vd.rates(W, vd.EARLY), vd.rates(W, vd.LATE)
    push = {t: s * (l[t] - e[t]) for t, s in vd.PUSH.items()}
    D = sum(push.values())
    def rate(ticks, f):
        ticks = [tk for tk in ticks if tk in W and "e0" in W[tk] and tk in R]
        return sum(f(R[tk][0]) / ledger(W[tk])["S"] / 10 / len(ticks) for tk in ticks)
    kept = lambda d: sum(d["kept"].values())
    allL = lambda d: sum(sum(v) for v in d["loss"].values())
    print(f"== {name} D={D:.4f}")
    for lab, f in [("all in-place", allL), ("kept", kept)] + \
                   [(c, (lambda i: lambda d: sum(d["loss"][r][i] for r in ROUTES))(i)) for i, c in enumerate(CLS)]:
        a, b = rate(vd.EARLY, f), rate(vd.LATE, f)
        print(f"  {lab:13s} early {a:.4f} late {b:.4f} push {b-a:+.4f} share of D {100*(b-a)/D:+.1f}%")
