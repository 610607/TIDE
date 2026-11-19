"""v26 erase vs fill. Usage: v26_cmp.py <erase dir> <fill dir> (zero_s1 zero_s2 fail_s1 fail_s2 .tsv).
Rates per strict entry-0 site per 5k ticks as v24_decomp (EARLY 100k-150k, LATE 350k-500k)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
import v24_routes, v25_len
from v24_decomp import rates, EARLY, LATE
RUNS = ["zero_s1", "zero_s2", "fail_s1", "fail_s2"]
DIRS = {"erase": sys.argv[1], "fill": sys.argv[2]}
def done(p): return os.path.exists(p) and any(l.startswith("final tick=500000") for l in open(p))
def data(p):
    rows, fin, fid, cen = {}, {}, {}, {}
    hdr = None
    for l in open(p):
        if l.startswith("tick\t"): hdr = l.split(); continue
        if l.startswith("final "): fin = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", l)}; continue
        if l.startswith("# fidelity "):
            fid[int(re.search(r"tick=(\d+)", l).group(1))] = {k: int(v) for k, v in re.findall(r" (ext_blocked|no_mass|conflicts|walled)=(\d+)", l)}
            continue
        if l.startswith("# census "):
            cen[int(re.search(r"tick=(\d+)", l).group(1))] = {k: int(v) for k, v in re.findall(r" (active|replicators|strict|born_fail)=(\d+)", l)}
            continue
        if hdr and l[0].isdigit():
            v = l.split("\t")
            if len(v) == len(hdr): rows[int(v[0])] = {k: float(x) for k, x in zip(hdr, v)}
    return rows, fin, fid, cen
L = range(350000, 500001, 50000)
def mean(xs): xs = list(xs); return sum(xs) / len(xs) if xs else float("nan")
out = {}
for mode, d in DIRS.items():
    for r in RUNS:
        p = f"{d}/{r}.tsv"
        if not done(p): continue
        rows, fin, fid, cen = data(p)
        W = v24_routes.load(p); Z = v25_len.load(p)
        e, la = rates(W, EARLY), rates(W, LATE)
        o = {}
        o["active late"] = mean(rows[t]["active"] for t in L)
        o["strict late"] = mean(cen[t]["strict"] for t in L)
        o["strict 500k"] = cen[500000]["strict"]
        o["mean z 100k"] = Z[100000]["mean"][1]; o["mean z 250k"] = Z[250000]["mean"][1]; o["mean z 500k"] = Z[500000]["mean"][1]
        o["exact% late"] = mean(rows[t]["exact%"] for t in L)
        o["copies /50k late"] = mean(rows[t]["copies"] for t in L)
        o["reignites /50k late"] = mean(rows[t]["reignites"] for t in L)
        o["ext_blocked /5k late"] = mean(fid[t]["ext_blocked"] for t in L)
        o["ext_erased /50k late"] = mean(rows[t]["ext_erased"] for t in L)
        o["stalls /50k late"] = mean(rows[t]["stalls"] for t in L)
        o["energy late"] = mean(rows[t]["energy"] for t in L)
        o["final ext_blocked"] = fin["ext_blocked"]; o["final ext_erased"] = fin["ext_erased"]
        o["final free"] = fin["free"]; o["final code"] = fin["code"]
        for tag, rr in (("early", e), ("late", la)):
            o[f"P {tag}"] = rr["P"]; o[f"reig0 {tag}"] = rr["reig0"]; o[f"decay {tag}"] = rr["decay"]
            o[f"Lf {tag}"] = sum(rr["L_" + k] for k in ("f30_mov15", "f30_other", "f_ptr", "f_tail", "f_other"))
            for k in ("f30_mov15", "f30_other", "f_ptr", "f_tail", "f_other"): o[f"L_{k} {tag}"] = rr["L_" + k]
            o[f"Ls {tag}"] = rr["L_self_0"] + rr["L_self_other"]
            o[f"N {tag}"] = sum(rr["N_" + c] for c in ("point", "gap", "multi", "env"))
            o[f"N_env {tag}"] = rr["N_env"]
            o[f"dS {tag}"] = rr["dS"]
        # in-place, per 5k activation-ticks of strict entry-0 (length exposure), whole run and late
        for tag, ts in (("all", sorted(Z)), ("late", [t for t in Z if t >= 350000])):
            ex = sum(sum(Z[t]["bins"][b][0] for b in v25_len.ZBINS) for t in ts)
            o[f"expo {tag}"] = ex
            o[f"loss_f/5k {tag}"] = sum(Z[t]["cat"]["loss_f"][0] for t in ts) / ex * 5000
            o[f"loss_s/5k {tag}"] = sum(Z[t]["cat"]["loss_s"][0] for t in ts) / ex * 5000
            o[f"rem_foreign/5k {tag}"] = sum(Z[t]["isrc"]["rem_foreign"] for t in ts) / ex * 5000
            o[f"add_foreign/5k {tag}"] = sum(sum(Z[t]["isrc"][k] for k in v25_len.ISRC[:4]) for t in ts) / ex * 5000
            o[f"inplace_f dz/5k {tag}"] = sum(Z[t]["cat"]["inplace_f"][1] for t in ts) / ex * 5000
            o[f"inplace_f n/5k {tag}"] = sum(Z[t]["cat"]["inplace_f"][0] for t in ts) / ex * 5000
            o[f"loss_f z {tag}"] = sum(Z[t]["cat"]["loss_f"][1] for t in ts) / max(1, sum(Z[t]["cat"]["loss_f"][0] for t in ts))
            o[f"trans/copy {tag}"] = sum(Z[t]["cat"]["copy_sp"][1] for t in ts) / max(1, sum(Z[t]["cat"]["copy_sp"][0] for t in ts))
            o[f"copy add_foreign/copy {tag}"] = sum(Z[t]["tsrc"]["add_foreign"][0] for t in ts) / max(1, sum(Z[t]["cat"]["copy_sp"][0] for t in ts))
        out[(mode, r)] = o
keys = list(next(iter(out.values())).keys()) if out else []
cols = [(m, r) for r in RUNS for m in DIRS if (m, r) in out]
print("| metric | " + " | ".join(f"{m} {r}" for m, r in cols) + " |")
for k in keys:
    def f(x):
        return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.3f}" if abs(x) < 10 else f"{x:.1f}"
    print(f"| {k} | " + " | ".join(f(out[c][k]) for c in cols) + " |")
