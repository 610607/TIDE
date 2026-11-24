"""Replay the archived fields and fork paired placements for enrolled templates."""
import argparse
import csv
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "handoff-window-01" / "results"
CASE = ("seed", "arm", "focal_site", "focal_born")
INPUT = (*CASE, "maker_born", "product")
TABLES = ("fields", "screen", "branches", "attempts", "reuse", "reuse-attempts")


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def check(ok, message):
    if not ok:
        raise ValueError(message)


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
    expected = set()
    for row in read(ARCHIVE / "case-stages.tsv"):
        if row["complete"] == row["distant_only_executed_s"] == "1":
            check(row["exact_birth"] == "0", "unexpected archived exact birth")
            item = tuple(row[k] for k in INPUT)
            expected.add(item)
            enrollment[int(row["seed"])].append(" ".join(item))
    check(sum(map(len, enrollment.values())) == len(expected) == 5039, "input census mismatch")

    def simulate(first):
        last = first + 15
        lines = [line for seed in range(first, last + 1) for line in enrollment[seed]]
        with tempfile.TemporaryDirectory(prefix="tide-contact-") as temp:
            command = [binary, str(first), str(last), temp]
            if args.reverse:
                command.append("--reverse")
            subprocess.run(command, input="\n".join(lines), text=True, check=True)
            return [(Path(temp) / (name + ".tsv")).read_bytes() for name in TABLES]

    with ExitStack() as stack:
        outputs = [stack.enter_context((args.directory / (name + ".tsv")).open("wb")) for name in TABLES]
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for i, batch in enumerate(pool.map(simulate, range(19521, 21569, 16))):
                for stream, raw in zip(outputs, batch):
                    stream.write(raw if i == 0 else raw.partition(b"\n")[2])
                if (i + 1) % 16 == 0:
                    print(f"{(i+1)*64}/8192 fields", flush=True)

    fields = read(args.directory / "fields.tsv")
    check(len(fields) == 8192 and fields == read(ARCHIVE / "fields.tsv"), "ordinary field ledger mismatch")
    screen = read(args.directory / "screen.tsv")
    check(len(screen) == len(expected) and {tuple(r[k] for k in INPUT) for r in screen} == expected,
          "screening ledger mismatch")


if __name__ == "__main__":
    main()
