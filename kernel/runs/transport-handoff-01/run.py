"""Replay archived movement arms and collect all intact living-donor births in new fields."""
import argparse
import csv
import io
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "spatial-transport-01" / "results"
ARMS = ("east", "low", "high")
FIRST, SPLIT, STOP = 19521, 21569, 23617


def check(ok, why):
    if not ok:
        raise ValueError(why)


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    binary = args.binary.resolve()
    args.directory.mkdir(parents=True, exist_ok=True)
    archived = {(int(r["seed"]), r["arm"]): r for r in read(ARCHIVE / "seeds.tsv") if r["arm"] in ARMS}
    births = defaultdict(list)
    for row in read(ARCHIVE / "products.tsv"):
        if row["arm"] in ARMS:
            births[int(row["seed"]), row["arm"]].append(row)

    def simulate(job):
        seed, arm = job
        with tempfile.TemporaryDirectory(prefix="tide-handoff-") as name:
            cmd = [binary, str(seed), arm, name]
            if args.reverse:
                cmd.append("--reverse")
            subprocess.run(cmd, check=True)
            field, products, switches = [(Path(name) / f).read_text() for f in ("seed.tsv", "products.tsv", "switches.tsv")]
        row, = csv.DictReader(io.StringIO(field), delimiter="\t")
        check((int(row["seed"]), row["arm"]) == job, "misidentified field")
        unlike = [p for p in csv.DictReader(io.StringIO(products), delimiter="\t") if p["product"] != p["executor"]]
        check(len(unlike) == int(row["exact_births"]), "enrollment mismatch")
        if seed < SPLIT:
            check(archived[job] == row and births[job] == unlike, f"archived ledger mismatch for {job}")
        return field, products, switches

    with ExitStack() as stack:
        outputs = [stack.enter_context((args.directory / n).open("w")) for n in ("fields.tsv", "products.tsv", "switches.tsv")]
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for start in range(FIRST, STOP, 128):
                jobs = [(s, a) for s in range(start, start + 128) for a in ARMS]
                for (seed, arm), pair in zip(jobs, pool.map(simulate, jobs)):
                    for out, raw in zip(outputs, pair):
                        out.write(raw if (seed, arm) == (FIRST, ARMS[0]) else raw.partition("\n")[2])
                if (start + 128 - FIRST) % 512 == 0:
                    print(f"{(start+128-FIRST)*len(ARMS):,}/12,288 fields", flush=True)


if __name__ == "__main__":
    main()
