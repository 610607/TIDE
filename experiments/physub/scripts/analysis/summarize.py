"""Summarize ps_probe TSV outputs: per run, key columns at chosen ticks and the final lines."""
import sys, pathlib

COLS = ["active", "pfx_active", "copies", "intact_copies", "blank", "open0", "dead"]

def load(path):
    rows, tail = [], []
    header = None
    for line in path.read_text().splitlines():
        if line.startswith("tick\t"):
            header = line.split("\t"); continue
        if header and line and line[0].isdigit() and "\t" in line:
            rows.append(dict(zip(header, line.split("\t")))); continue
        tail.append(line)
    return rows, tail

def main(run_dir, ticks):
    for p in sorted(pathlib.Path(run_dir).glob("*.tsv")):
        rows, tail = load(p)
        by_tick = {int(r["tick"]): r for r in rows}
        last = max(by_tick) if by_tick else 0
        cells = []
        for t in ticks:
            r = by_tick.get(t)
            cells.append("-" if r is None else "/".join(r[c] for c in ["active", "pfx_active", "copies"]))
        final = next((l for l in tail if l.startswith("final")), "")
        print(f"{p.stem:20s} last={last:6d}  " + "  ".join(f"{t//1000}k:{c}" for t, c in zip(ticks, cells)))
        if last and by_tick[last]:
            r = by_tick[last]
            print(f"{'':20s} census@{last//1000}k blank/open0/dead={r['blank']}/{r['open0']}/{r['dead']}  {final}")
        for l in tail:
            if l.startswith("parent "):
                print(f"{'':20s} {l}")

if __name__ == "__main__":
    ticks = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [20000, 50000, 100000]
    main(sys.argv[1], ticks)
