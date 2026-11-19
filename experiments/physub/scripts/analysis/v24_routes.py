"""v24 loss-route ledger. Usage: v24_routes.py run.tsv... (route=1 outputs).
Per strict activation ignited at offset 0 ("entry 0"), per 50k window: inflow (copies by
strict entry-0 parents, re-ignitions at 0, gains) and losses (decay, wick, in-place by route,
non-strict children by difference class). Rates per strict entry-0 site per 5k ticks use the
mean of the window's start and end counts."""
import sys, re, statistics as st
ROUTES = ["f30_mov15", "f30_other", "f_ptr", "f_tail", "f_other", "self_0", "self_other"]
CLS = ["exact", "point", "gap", "multi", "env"]
VIA = ["filled_36_38", "filled_ref", "inert", "dest_32", "other", "not_ignite"]
WR = ["rep", "loose", "prop", "other", "self", "none"]
def parse_entry(seg):
    d = {}
    for k in ("prev", "now", "balance", "gain", "found"):
        d[k] = int(re.search(rf"\b{k}=(-?\d+)", seg).group(1))
    d["born"] = [int(x) for x in re.search(r"born_self/copy/reignite=(\d+)/(\d+)/(\d+)", seg).groups()]
    d["end"] = [int(x) for x in re.search(r"end_decay/wick=(\d+)/(\d+)", seg).groups()]
    d["loss"] = {r: [int(x) for x in re.search(rf"{r}=(\d+)/(\d+)", seg).groups()] for r in ROUTES}
    return d
def load(path):
    W = {}
    for l in open(path):
        m = re.match(r"# (route|routecopy|routeign|tracemass|fidelity) tick=(\d+)", l)
        if not m: continue
        tag, tk = m.group(1), int(m.group(2)); w = W.setdefault(tk, {})
        if tag == "route":
            parts = l.split(" | ")
            w["no_mass"] = int(re.search(r"no_mass=(\d+)", parts[0]).group(1))
            w["e0"] = parse_entry(parts[1]); w["eo"] = parse_entry(parts[2])
        elif tag == "routecopy":
            a, b = l.split(" parent_off:")
            b, envs = b.split(" env_nonstrict0:")
            w["cp0"] = {c: [int(x) for x in re.search(rf"{c}=(\d+)\((\d+)\)", a).groups()] for c in CLS}
            w["cpo"] = {c: [int(x) for x in re.search(rf"{c}=(\d+)\((\d+)\)", b).groups()] for c in CLS}
            w["env"] = {k: int(re.search(rf"\b{k}=(\d+)", envs).group(1)) for k in ("n", "only30", "has30", "residue_only")}
            w["env"]["writer30"] = [int(x) for x in re.search(r"writer30=([\d/]+)", envs).group(1).split("/")]
            w["env"]["offsets"] = envs.split("offsets:")[1].strip()
        elif tag == "routeign":
            w["via"] = {k: [int(x) for x in re.search(rf" {k}:([\d/]+)", l).group(1).split("/")] for k in WR}
            w["ptr"] = l.split("ptr:")[1].strip()
        elif tag == "tracemass":
            w["mass"] = {k: v for k, v in (x.split("=", 1) for x in l.split()[3:] if "=" in x)}
    return W
def ledger(w):
    e = w["e0"]; S = (e["prev"] + e["now"]) / 2
    cp = w["cp0"]
    copies = sum(n for n, s in cp.values())
    r = {"S": S, "dS": e["now"] - e["prev"],
         "copies": copies, "strict_copies": sum(s for n, s in cp.values()),
         "reig0": e["born"][2], "gain": e["gain"] + e["found"],
         "decay": e["end"][0], "wick": e["end"][1]}
    for k in ROUTES: r["L_" + k] = sum(e["loss"][k])
    for c in CLS: r["N_" + c] = cp[c][0] - cp[c][1]
    # identity: copies + reig0 + gain = decay + wick + losses + nonstrict + dS (+ entry-0 copy births not by strict entry-0 parents)
    r["born_copy0"] = e["born"][1]
    return r
if __name__ == "__main__":
    for path in sys.argv[1:]:
        W = load(path)
        print("==", path.split("/")[-1])
        for tk in sorted(W):
            if "e0" not in W[tk]: continue
            r = ledger(W[tk]); e = W[tk]["e0"]; o = W[tk]["eo"]
            print(tk // 1000, "S0", e["now"], "bal_ok", e["balance"] == e["now"] and o["balance"] == o["now"],
                  "copies", r["copies"], "strict", r["strict_copies"], "born_copy0", r["born_copy0"], "reig0", r["reig0"],
                  "gain", r["gain"], "decay", r["decay"], "wick", r["wick"],
                  "L", {k: e["loss"][k] for k in ROUTES},
                  "N", {c: r["N_" + c] for c in CLS}, "no_mass", W[tk]["no_mass"])
            print("    off: born", o["born"], "end", o["end"], "L", {k: o["loss"][k] for k in ROUTES if sum(o["loss"][k])},
                  "via", {k: v for k, v in W[tk]["via"].items() if sum(v)}, "ptr", W[tk]["ptr"][:80])
            print("    env", W[tk]["env"])
