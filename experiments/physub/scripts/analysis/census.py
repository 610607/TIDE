"""Per run: census at chosen ticks as active / replicators / pfx_replicators / nonrep(copy,reignite) / ages."""
import sys, pathlib, re

def main(run_dir, ticks):
    for p in sorted(pathlib.Path(run_dir).glob("*.tsv")):
        rows = {}
        for line in p.read_text().splitlines():
            if line.startswith("# census"):
                kv = dict(x.split("=", 1) for x in line[len("# census "):].split())
                rows[int(kv["tick"])] = kv
        final = next((l for l in p.read_text().splitlines() if l.startswith("final")), "")
        last = max(rows) if rows else 0
        cells = []
        for t in ticks:
            kv = rows.get(t)
            if not kv: cells.append(f"{t//1000}k:-"); continue
            s, c, r = kv["nonrep_self/copy/reignite"].split("/")
            a1, a0 = kv["mean_age_rep/nonrep"].split("/")
            cells.append(f"{t//1000}k:{kv['active']}/{kv['replicators']}/{kv['pfx_replicators']}"
                         f" z{c}+r{r} g{kv['replicator_genotypes']}/{kv['genotypes']} age{a1}/{a0}")
        m = re.search(r"final tick=(\d+) active=(\d+)", final)
        end = f"end={m.group(1)}:{m.group(2)}" if m else "running"
        print(f"{p.stem:18s} {end:14s} " + "  ".join(cells))

if __name__ == "__main__":
    ticks = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [20000, 50000, 100000]
    main(sys.argv[1], ticks)
