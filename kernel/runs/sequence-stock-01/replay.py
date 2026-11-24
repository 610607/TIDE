"""Replay both archived cohorts and index the uncompressed observer output."""
import argparse
import csv
import gzip
import hashlib
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLES = ("world", "sequences", "stocks", "births")


def references():
    for cohort in ("pilot", "replication"):
        path = HERE.parent / "six-origin-01" / cohort / "seeds.tsv"
        with path.open() as f:
            for row in csv.DictReader(f, delimiter="\t"):
                yield cohort, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("index", type=Path)
    parser.add_argument("--details", type=Path, help="retain compressed tables for every seed")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    args.index.parent.mkdir(parents=True, exist_ok=True)

    def replay(item):
        cohort, ref = item
        seed = ref["seed"]
        with tempfile.TemporaryDirectory(prefix="tide-stock-") as name:
            tmp = Path(name)
            command = [args.binary.resolve(), seed, tmp]
            if args.reverse:
                command.append("--reverse")
            subprocess.run(command, check=True)
            with (tmp / "world.tsv").open() as f:
                world, = csv.DictReader(f, delimiter="\t")
            if any(ref[k] != v for k, v in world.items()):
                raise ValueError(f"world ledger differs from archive for {seed}")
            hashes = []
            if args.details:
                target = args.details / seed
                target.mkdir(parents=True, exist_ok=True)
            for table in TABLES:
                raw = (tmp / f"{table}.tsv").read_bytes()
                hashes.append(hashlib.sha256(raw).hexdigest())
                if args.details:
                    (target / f"{table}.tsv.gz").write_bytes(gzip.compress(raw, compresslevel=1, mtime=0))
        return [cohort, seed, world["state_fnv64"], *hashes]

    with args.index.open("w") as f, ThreadPoolExecutor(max_workers=args.jobs) as pool:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["cohort", "seed", "state_fnv64", *[f"{t}_sha256" for t in TABLES]])
        for i, record in enumerate(pool.map(replay, references()), 1):
            writer.writerow(record)
            if i % 256 == 0:
                f.flush()
                print(f"{i} world ledgers verified", flush=True)


if __name__ == "__main__":
    main()
