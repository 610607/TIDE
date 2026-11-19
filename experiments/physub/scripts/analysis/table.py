"""Markdown table per run: end, replicator peak (tick), at 100k: replicators, pfx, nonrep copy-born, reignited, nonrep age."""
import sys, pathlib, re
rows = []
for p in sorted(pathlib.Path(sys.argv[1]).glob("*.tsv")):
    text = p.read_text().splitlines()
    cen = {}
    for line in text:
        if line.startswith("# census"):
            kv = dict(x.split("=", 1) for x in line[len("# census "):].split())
            cen[int(kv["tick"])] = kv
    final = next((l for l in text if l.startswith("final")), "")
    m = re.search(r"final tick=(\d+) active=(\d+)", final)
    end_tick, end_act = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    peak = max(cen.items(), key=lambda kv: int(kv[1]["replicators"])) if cen else None
    last = cen.get(100000)
    def f(kv):
        s, c, r = kv["nonrep_self/copy/reignite"].split("/")
        a1, a0 = kv["mean_age_rep/nonrep"].split("/")
        return [kv["active"], kv["replicators"], kv["pfx_replicators"], c, r, a1, a0]
    cells = f(last) if last else ["extinct at %d" % end_tick if end_act == 0 else "-"] + [""] * 6
    pk = f"{peak[1]['replicators']} ({peak[0]//1000}k)" if peak else "-"
    rows.append([p.stem, pk] + cells)
print("| run | replicator peak | active | replicators | pfx | non-rep copy-born | re-ignited | age rep / non-rep |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} / {r[8]} |" if r[3] else f"| {r[0]} | {r[1]} | {r[2]} | | | | | |")
