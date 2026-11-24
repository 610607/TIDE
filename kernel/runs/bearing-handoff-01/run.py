"""Replay the stationary factorial and compare both anchor arms with the preceding archive."""
import argparse
import csv
import io
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("east", "read", "place", "bearing")


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def check(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    binary = args.binary.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    archive = HERE.parent / "spatial-transport-01" / "results"
    anchors = {(r["seed"],r["arm"]): r for r in read(archive / "seeds.tsv") if r["arm"] in ("east","bearing")}
    prior_products = defaultdict(list)
    for r in read(archive / "products.tsv"):
        if r["arm"] in ("east","bearing"):
            prior_products[r["seed"],r["arm"]].append(r)

    def replay(job):
        seed, arm = job
        with tempfile.TemporaryDirectory(prefix="tide-bearing-") as name:
            tmp = Path(name)
            cmd = [binary, seed, arm, tmp] + (["--reverse"] if args.reverse else [])
            subprocess.run(cmd, check=True)
            raw = [(tmp / n).read_text() for n in ("seed.tsv", "products.tsv")]
        world, = csv.DictReader(io.StringIO(raw[0]), delimiter="\t")
        unlike = [p for p in csv.DictReader(io.StringIO(raw[1]), delimiter="\t") if p["executor"] != p["product"]]
        check((world["seed"], world["arm"]) == job and int(world["exact_births"]) == len(unlike), f"{job} birth count")
        if job in anchors:
            check(world == anchors[job] and unlike == prior_products[job], f"{job} anchor mismatch")
        return raw

    jobs = ((str(seed),arm) for seed in range(19521,21569) for arm in ARMS)
    with (args.output / "fields.tsv").open("w") as fields, (args.output / "products.tsv").open("w") as products:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for i, pair in enumerate(pool.map(replay, jobs)):
                for stream, raw in zip((fields,products),pair):
                    stream.write(raw if i == 0 else raw.partition("\n")[2])
                if (i+1)%1024 == 0:
                    print(f"{i+1}/8192 fields verified", flush=True)


if __name__ == "__main__":
    main()
