"""v29 per-checkpoint series: strict, active, mean z (strict, length line), active sites by
tracemass class, free monomers, inactive sites. Usage: v29_series.py run.tsv..."""
import re, sys
def get(l, k):
    m = re.search(rf"\b{k}=([-\d./]+)", l); return m.group(1) if m else None
for path in sys.argv[1:]:
    rows = {}
    for l in open(path):
        m = re.match(r"# (census|length|tracemass|physics) tick=(\d+)", l)
        if not m: continue
        t = int(m.group(2)); r = rows.setdefault(t, {})
        if m.group(1) == "census":
            r["strict"] = int(get(l, "strict")); r["active"] = int(get(l, "active")); r["rep"] = int(get(l, "replicators"))
        elif m.group(1) == "length":
            r["z"] = float(get(l, "mean").split("/")[1])
        elif m.group(1) == "tracemass":
            r["sites"] = get(l, "active_sites"); r["free"] = int(get(l, "free")); r["inact"] = int(get(l, "inactive_sites"))
            r["code"] = int(get(l, "code"))
        elif m.group(1) == "physics":
            r["blk"] = get(l, "ext_active_blocked"); r["dec"] = int(get(l, "whole_decays")); r["born"] = int(get(l, "copies_born"))
    print("==", path)
    prev = {"dec": 0, "born": 0, "blk": "0"}
    for t in sorted(rows):
        r = rows[t]
        if "strict" not in r: continue
        blk = int(r.get("blk") or 0) - int(prev["blk"] or 0)
        print(f"{t//1000:>4}k strict {r['strict']:5d} rep {r['rep']:5d} active {r['active']:5d} z {r.get('z',0):6.2f} "
              f"sites(rep/loose/prop/other) {r['sites']:>20} inact {r['inact']:5d} free {r['free']:6d} code {r['code']} "
              f"born {r['born']-prev['born']:6d} decays {r['dec']-prev['dec']:6d} blocked {blk}")
        prev = {"dec": r["dec"], "born": r["born"], "blk": r.get("blk") or "0"}
