"""Run both clock schedules for each matched seed and merge the observer ledgers."""
import argparse
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

ARMS = ("high", "burst")
FIRST, SPLIT, STOP = 21569, 23617, 25665
TABLES = {"seed": "fields", "products": "products", "switches": "switches", "budget": "budgets", "phase": "phases"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    binary = args.binary.resolve()
    args.directory.mkdir(parents=True, exist_ok=True)

    def field(job):
        seed, arm = job
        with tempfile.TemporaryDirectory(prefix="tide-timing-") as name:
            cmd = [binary, str(seed), arm, name]
            if args.reverse:
                cmd.append("--reverse")
            subprocess.run(cmd, check=True)
            return [(Path(name) / (k + ".tsv")).read_bytes() for k in TABLES]

    with ExitStack() as stack, ThreadPoolExecutor(max_workers=args.jobs) as pool:
        streams = [stack.enter_context((args.directory / (v + ".tsv")).open("wb")) for v in TABLES.values()]
        for first in range(FIRST, STOP, 128):
            jobs = [(s, a) for s in range(first, first + 128) for a in ARMS]
            for job, batch in zip(jobs, pool.map(field, jobs)):
                for stream, raw in zip(streams, batch):
                    stream.write(raw if job == (FIRST, ARMS[0]) else raw.partition(b"\n")[2])
            if (first + 128 - FIRST) % 512 == 0:
                print(f"{(first+128-FIRST)*2:,}/8,192 fields", flush=True)


if __name__ == "__main__":
    main()
