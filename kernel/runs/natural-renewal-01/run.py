"""Run both fixed untreated seed blocks and retain the ledger and pedigrees."""
import argparse
import gzip
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRST, SPLIT, STOP = 26689, 27201, 27713
ENROLL, FOLLOW, AGE = 8192, 324, 81


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--reverse", action="store_true")
    a = parser.parse_args()
    binary = a.binary.resolve()
    a.directory.mkdir(parents=True, exist_ok=True)
    tables = ("world", "nodes", "contacts")

    def run(seed):
        with tempfile.TemporaryDirectory(prefix="tide-renewal-") as tmp:
            subprocess.run([binary, str(seed), tmp, *(["--reverse"] if a.reverse else [])], check=True)
            return [(Path(tmp) / (k + ".tsv")).read_bytes() for k in tables]

    with ThreadPoolExecutor(max_workers=a.jobs) as pool, ExitStack() as stack:
        streams = []
        for k in tables:
            compressed = k == "nodes"
            out = stack.enter_context((a.directory / (k + (".tsv.gz" if compressed else ".tsv"))).open("wb"))
            if compressed:
                out = stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0, compresslevel=6))
            streams.append(out)
        for i, batch in enumerate(pool.map(run, range(FIRST, STOP)), 1):
            for stream, data in zip(streams, batch):
                stream.write(data if i == 1 else data.partition(b"\n")[2])
            if i % 128 == 0:
                print(f"{i}/{STOP - FIRST} untreated fields", flush=True)


if __name__ == "__main__":
    main()
