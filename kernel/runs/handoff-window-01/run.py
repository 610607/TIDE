"""Replay every stationary factorial world with the previously enrolled templates."""
import argparse
import csv
import gzip
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "bearing-handoff-01" / "results"
ARMS = ("east", "read", "place", "bearing")


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def check(ok, why):
    if not ok:
        raise ValueError(why)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    binary = args.binary.resolve()
    args.directory.mkdir(parents=True, exist_ok=True)
    enrollment = defaultdict(list)
    for row in read(ARCHIVE / "products.tsv"):
        if row["executor"] != row["product"]:
            enrollment[int(row["seed"])].append(" ".join(row[k] for k in ("seed","arm","child_site","child_born",
                                                                          "executor_birth_site","executor_born","product")))
    tables = ("fields", "windows", "neighbors", "attempts", "availability")

    def run(first):
        last = first + 15
        lines = [s for seed in range(first,last+1) for s in enrollment[seed]]
        with tempfile.TemporaryDirectory(prefix="tide-window-") as name:
            cmd = [binary, str(first), str(last), name] + (["--reverse"] if args.reverse else [])
            subprocess.run(cmd, input="\n".join(lines)+"\n", text=True, check=True)
            return [(Path(name) / (t+".tsv")).read_bytes() for t in tables]

    with ExitStack() as stack:
        outputs = []
        for name in tables:
            packed = name=="neighbors"
            path = args.directory / (name+".tsv"+(".gz" if packed else ""))
            stream = stack.enter_context(path.open("wb"))
            if packed:
                stream = stack.enter_context(gzip.GzipFile(filename="",fileobj=stream,mode="wb",mtime=0,compresslevel=6))
            outputs.append(stream)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for i,batch in enumerate(pool.map(run, range(19521,21569,16))):
                for stream,raw in zip(outputs,batch):
                    stream.write(raw if i==0 else raw.partition(b"\n")[2])
                if (i+1)%16==0:
                    print(f"{(i+1)*64}/8192 fields",flush=True)

    baseline = read(ARCHIVE / "fields.tsv")
    fields = read(args.directory / "fields.tsv")
    check(len(fields)==len(baseline)==8192, "missing field")
    for current,prior in zip(fields,baseline):
        check(all(v==prior[k] for k,v in current.items()), f"field mismatch {current}")


if __name__=="__main__":
    main()
