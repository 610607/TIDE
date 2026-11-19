"""Strict ledger per 50k window from v23 fate/trace/fidcopy lines. Usage: routes_ledger.py run.tsv..."""
import sys, re
def kv(l):
    d = {}
    for x in l.split():
        if "=" in x:
            k, v = x.split("=", 1); d[k] = v
    return d
for path in sys.argv[1:]:
    W = {}
    for l in open(path):
        if not l.startswith("# "): continue
        tag = l.split()[1]
        m = re.search(r"tick=(\d+)", l)
        if not m: continue
        tk = int(m.group(1)); w = W.setdefault(tk, {})
        if tag in ("fate", "fatestart", "traceign", "traceend", "fidelity", "tracemass"):
            w[tag] = l
        elif tag == "fidcopy" and "parent=rep " in l:
            w["fidcopy"] = l
        elif tag == "fateout":
            w["fateout"] = l
    print("==", path.split("/")[-1])
    print("tick S born0(c/r) bornoff ends0(d/w) endsoff(d/w) out out0 fill30 self self0 in | 5k: rep_births strict exact point(s) gap(s) multi(s) env(s) no_mass")
    for tk in sorted(W):
        w = W[tk]
        if "fate" not in w: continue
        f = kv(w["fate"]); fs = kv(w["fatestart"]); fo = kv(w["fateout"])
        ti = w["traceign"]; te = w["traceend"]
        r0 = re.search(r"rep_start0\(self/copy/reignite\)=(\d+)/(\d+)/(\d+)", ti).groups()
        ro = re.search(r"rep_off0\(self/copy/reignite\)=(\d+)/(\d+)/(\d+)", ti).groups()
        e0 = re.search(r"rep_start0: decay/wick=(\d+)/(\d+)", te).groups()
        eo = re.search(r"rep_off0: decay/wick=(\d+)/(\d+)", te).groups()
        fc = w["fidcopy"]
        cls = {k: re.search(k + r"=(\d+)\((\d+)\)", fc).groups() for k in ("exact", "point", "gap", "multi", "env")}
        fid = kv(w["fidelity"])
        print(tk//1000, f["rep_now"], f"{r0[1]}/{r0[2]}", int(ro[1]) + int(ro[2]), f"{e0[0]}/{e0[1]}", f"{eo[0]}/{eo[1]}",
              f["out_in_place"], fs["out_start0"].split("/")[0], fo["only_src"], fo.get("self"), fs["self_start0"].split("/")[0], f["in_in_place"], "|",
              kv(fc)["births"], kv(fc)["child_strict%"], " ".join(f"{k}={a}({b})" for k, (a, b) in cls.items()), fid["no_mass"])
