"""v28 role ledger. Usage: v28_an.py run.tsv... (role=1 outputs). Sums # role / # rolelen over
windows (all, to 150k, after 150k) and prints loss classes by route, kept shares, foreign
direction offsets, gains, and the length ledger by role."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import ROUTES
CLS = ["dir_only", "dir_mixed", "opnd", "val", "sub", "none"]
LB = ["add_dir", "add_opnd", "add_val", "add_none", "rem", "sub"]
ROLES4 = ["dir", "opnd", "val", "none"]
ROLES5 = ROLES4 + ["sub"]
def ints(s): return [int(x) for x in s.split("/")]
def flts(s): return [float(x) for x in s.split("/")]
def top(seg, name):
    m = re.search(name + r":((?: \d+:\d+)*)", seg)
    if not m: return {}
    return {int(a): int(b) for a, b in (x.split(":") for x in m.group(1).split())}
def load(path):
    W = {}
    for l in open(path):
        l = l.rstrip("\n")
        m = re.match(r"# (role|rolelen) tick=(\d+)", l)
        if not m: continue
        tk = int(m.group(2)); w = W.setdefault(tk, {})
        if m.group(1) == "role":
            for e, seg in enumerate(l.split(" | ")[1:]):
                d = {"loss": {}, "kept": {}}
                for r in ROUTES:
                    a, b = re.search(rf" {r}=([\d/]+);(\d+)", seg).groups()
                    d["loss"][r] = ints(a); d["kept"][r] = int(b)
                a, b = re.search(r" gain=([\d/]+);undone=(\d+)", seg).groups()
                d["gain"] = ints(a); d["undone"] = int(b)
                d["fdo"] = top(seg, "foreign_dir_off")
                w[e] = d
        else:
            d = {}
            for fw in ("foreign", "self"):
                a, b = re.search(rf" {fw}:([\d/]+);([-\d.e+/]+)", l).groups()
                d["lb_" + fw] = ints(a); d["lbdm_" + fw] = flts(b)
            for c in ("loss_f", "loss_s"):
                a, b, k, kd = re.search(rf" {c}:([\d/]+);([-\d.e+/]+);(\d+)/([-\d.e+]+)", l).groups()
                d[c] = ints(a); d[c + "_dm"] = flts(b); d[c + "_kept"] = int(k); d[c + "_kdm"] = float(kd)
            for s in ("residue", "foreign", "parent"):
                d["tr_" + s] = ints(re.search(rf" {s}=([\d/]+)", l).group(1))
            d["env_n"] = int(re.search(r"env_nonstrict0 n=(\d+)", l).group(1))
            d["env_b"] = ints(re.search(r"foreign_offsets\(dir/opnd/val/none/sub\)=([\d/]+)", l).group(1))
            d["env_dir_only"] = int(re.search(r" dir_only=(\d+)", l).group(1))
            d["env_dir_any"] = int(re.search(r" dir_any=(\d+)", l).group(1))
            d["adf"] = top(l, "add_dir_off_foreign"); d["ads"] = top(l, "add_dir_off_self")
            w["len"] = d
    return W
def add(a, b):
    if isinstance(a, list): return [x + y for x, y in zip(a, b)]
    if isinstance(a, dict): return merge(a, b)
    return a + b
def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = add(out[k], v) if k in out else v
    return out
def total(W, lo, hi):
    acc = None
    for tk in sorted(W):
        if lo < tk <= hi:
            acc = W[tk] if acc is None else merge(acc, W[tk])
    return acc
def pct(a, b): return 100.0 * a / b if b else float("nan")
def report(name, T):
    print(f"-- {name}")
    for e, lab in ((0, "entry0"), (1, "entry_off")):
        d = T[e]
        L = sum(sum(v) for v in d["loss"].values()); K = sum(d["kept"].values())
        cls = [sum(d["loss"][r][i] for r in ROUTES) for i in range(len(CLS))]
        print(f"  {lab}: losses {L} kept {K} ({pct(K, L):.1f}%) classes " +
              " ".join(f"{c}={n}({pct(n, L):.1f}%)" for c, n in zip(CLS, cls)))
        for r in ROUTES:
            n = sum(d["loss"][r])
            if n == 0: continue
            print(f"    {r:11s} {n:6d} ({pct(n, L):4.1f}%) kept {d['kept'][r]:6d} ({pct(d['kept'][r], n):5.1f}%) " +
                  " ".join(f"{c}={pct(x, n):.1f}" for c, x in zip(CLS, d["loss"][r])))
        fdo = sorted(d["fdo"].items(), key=lambda x: -x[1])
        print("    foreign dir fills in losses by offset:", ", ".join(f"{k}:{v}({pct(v, L):.1f}% of losses)" for k, v in fdo))
        G = sum(d["gain"])
        print(f"    gains {G} undone {d['undone']} ({pct(d['undone'], G):.1f}%) " +
              " ".join(f"{c}={n}" for c, n in zip(CLS, d["gain"])))
    l = T["len"]
    for fw in ("foreign", "self"):
        b, dm = l["lb_" + fw], l["lbdm_" + fw]
        print(f"  inplace kept {fw}: bytes " + " ".join(f"{k}={v}" for k, v in zip(LB, b)) +
              f" | dm " + " ".join(f"{k}={v:+.3f}" for k, v in zip(LB, dm)) + f" | sum {sum(dm):+.3f}")
    for c in ("loss_f", "loss_s"):
        print(f"  exit {c}: n " + " ".join(f"{k}={v}" for k, v in zip(CLS, l[c])) +
              " | dm " + " ".join(f"{k}={v:+.3f}" for k, v in zip(CLS, l[c + "_dm"])) +
              f" | sum {sum(l[c + '_dm']):+.3f} | kept {l[c + '_kept']} dm {l[c + '_kdm']:+.3f}")
    for s in ("residue", "foreign", "parent"):
        v = l["tr_" + s]
        print(f"  copy add {s}: " + " ".join(f"{k}={x}" for k, x in zip(ROLES4, v)) + f" (dir {pct(v[0], sum(v)):.1f}%)")
    print(f"  env nonstrict0 n={l['env_n']} offsets " + " ".join(f"{k}={x}" for k, x in zip(ROLES5, l["env_b"])) +
          f" dir_only={l['env_dir_only']} ({pct(l['env_dir_only'], l['env_n']):.1f}%) dir_any={l['env_dir_any']} ({pct(l['env_dir_any'], l['env_n']):.1f}%)")
    print("  add_dir_off foreign:", sorted(l["adf"].items(), key=lambda x: -x[1]), "self:", sorted(l["ads"].items(), key=lambda x: -x[1]))
if __name__ == "__main__":
    for path in sys.argv[1:]:
        W = load(path); name = path.split("/")[-1].replace(".tsv", "")
        for lo, hi, lab in ((0, 10**9, "all"), (0, 150000, "to150k"), (150000, 10**9, "after150k")):
            T = total(W, lo, hi)
            if T: report(f"{name} {lab}", T)
