"""v25 length lines (length=1). load(path) -> {tick: {...}}."""
import re
CATS = ["copy_sp", "copy_op", "reignite", "self", "gain", "found", "decay", "wick", "loss_f",
        "loss_s", "inplace_f", "inplace_s"]
TSRC = ["add_residue", "add_foreign", "add_parent", "lost_gap", "lost_parent", "lost_foreign"]
ISRC = ["add_mov15_aligned", "add_mov15_shift", "add_mov15_nbrsrc", "add_foreign_other",
        "add_self", "rem_self", "rem_foreign"]
WR = ["rep", "loose", "prop", "other", "self", "none"]
FIELDS = ["expo", "copies", "strict", "exact", "decay", "wick", "loss_f", "loss_s"]
ZBINS = ["<=40", "41-44", "45-48", "49-52", "53-56", "57-60", "61-64"]
EXT = [30, 34, 36, 38, 40] + list(range(46, 64))
def nums(s): return [float(x) if "." in x or "e" in x else int(x) for x in s.split("/")]
def load(path):
    W = {}
    for l in open(path):
        m = re.match(r"# (length|lengthsrc|lengthoff|lengthuse|lengthbin|lengthcomp|lengthptr) tick=(\d+)", l)
        if not m: continue
        tag, tk = m.group(1), int(m.group(2)); w = W.setdefault(tk, {}); l = l.strip()
        if tag == "length":
            n0, n1 = map(int, re.search(r" n=(\d+)/(\d+)", l).groups())
            m0, m1 = map(float, re.search(r" mean=([\d.]+)/([\d.]+)", l).groups())
            w["n"] = (n0, n1); w["mean"] = (m0, m1)
            w["dmean"] = float(re.search(r"dmean=(\S+)", l).group(1))
            w["sum_dm"] = float(re.search(r"sum_dm=(\S+)", l).group(1))
            w["check"] = [int(re.search(rf"{k}=(-?\d+)", l).group(1)) for k in ("check_n", "check_z", "empty")]
            w["cat"] = {}
            for c in CATS:
                n, z, dm = re.search(rf" {c}=(\d+)/(-?\d+)/(\S+)", l).groups()
                w["cat"][c] = (int(n), int(z), float(dm))
            w["trans"] = float(re.search(r" trans=(\S+)", l).group(1))
            w["zp"] = int(re.search(r" zp=(\d+)", l).group(1))
        elif tag == "lengthsrc":
            w["tsrc"] = {k: (int(a), float(b)) for k, a, b in re.findall(r" (\w+)=(\d+)/(\S+)", l.split(" inplace")[0]) if k in TSRC}
            w["subs"] = int(re.search(r" subs=(\d+)", l).group(1))
            ip = l.split(" inplace")[1]
            w["isrc"] = {k: int(re.search(rf" {k}=(\d+)", ip).group(1)) for k in ISRC}
            w["iwc"] = [int(x) for x in re.search(r"foreign_add_writer=([\d/]+)", l).group(1).split("/")]
        elif tag == "lengthoff":
            a, b = l.split(" | inplace")
            def offs(s):
                d = {}
                for k, v in re.findall(r" (\d+|rest):([\d/]+)", s): d[k if k == "rest" else int(k)] = [int(x) for x in v.split("/")]
                return d
            w["toff"] = offs(a.split(")", 1)[1]); w["ioff"] = offs(b.split(")", 1)[1])
        elif tag == "lengthuse":
            a, b = l.split(" | exits=")
            w["alive_n"] = int(re.search(r"alive=(\d+)", a).group(1))
            w["alive"] = {int(k): int(v) for k, v in re.findall(r" (\d+):(\d+)", a.split(":", 1)[1])}
            w["ex_n"] = int(b.split("(")[0])
            w["ex"] = {int(k): (int(x), int(y), int(z)) for k, x, y, z in re.findall(r" (\d+):(\d+)/(\d+)/(\d+)", b)}
        elif tag == "lengthbin":
            w["bins"] = {k: [int(x) for x in v.split("/")] for k, v in re.findall(r" ([<=\d-]+):([\d/]+)", l.split(")", 1)[1])}
        elif tag == "lengthptr":
            body, sh = l.split(" shift_by(src-dst):")
            w["ptr"] = {}
            for name, live, pb, pw in re.findall(r" (\w+_(?:in|off)):(\d+);([\d/]+);([\d/]+)", body):
                w["ptr"][name] = (int(live), [int(x) for x in pb.split("/")], [int(x) for x in pw.split("/")])
            w["shift"] = {int(k): int(v) for k, v in re.findall(r" (\d+):(\d+)", sh)}
        elif tag == "lengthcomp":
            w["comp"] = {k: [int(x) for x in v.split("/")] for k, v in re.findall(r" (p\dt\d):([\d/]+)", l)}
    return W
if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        W = load(p)
        for tk in sorted(W):
            w = W[tk]
            print(tk, w["n"], w["mean"], round(w["dmean"] - w["sum_dm"], 12), w["check"], {c: round(v[2], 4) for c, v in w["cat"].items()},
                  "trans", round(w["trans"], 4), "tsrc", w["tsrc"], "isrc", w["isrc"], "iwc", w["iwc"])
