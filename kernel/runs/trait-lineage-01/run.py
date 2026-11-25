"""Run the archived positive control and every preregistered natural field."""
import argparse
import csv
import gzip
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROL, FIRST, SPLIT, STOP = 19995, 25665, 26177, 26689


def read(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def check(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--reverse", action="store_true")
    a = parser.parse_args()
    binary = a.binary.resolve()
    a.directory.mkdir(parents=True, exist_ok=True)
    tables = ("world", "nodes", "returns")

    def field(seed):
        with tempfile.TemporaryDirectory(prefix="tide-trait-") as name:
            args = [binary, str(seed), name]
            if a.reverse:
                args.append("--reverse")
            subprocess.run(args, check=True)
            return [(Path(name) / (k+".tsv")).read_bytes() for k in tables]

    with ExitStack() as stack, ThreadPoolExecutor(max_workers=a.jobs) as pool:
        streams = []
        for k in tables:
            suffix = ".tsv.gz" if k == "nodes" else ".tsv"
            out = stack.enter_context((a.directory / (k+suffix)).open("wb"))
            if k == "nodes":
                out = stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0, compresslevel=6))
            streams.append(out)
        for i, batch in enumerate(pool.map(field, [CONTROL, *range(FIRST, STOP)])):
            for stream, data in zip(streams, batch):
                stream.write(data if i == 0 else data.partition(b"\n")[2])
            if i and i % 128 == 0:
                print(f"{i}/1024 new fields", flush=True)


if __name__ == "__main__":
    main()
