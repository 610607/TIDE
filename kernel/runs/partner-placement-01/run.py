"""Select all archived changed executor edges and run the three field branches."""
import argparse
import csv
import gzip
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        yield from csv.DictReader(stream, delimiter="\t")


def cases():
    cases = []
    for block in ("pilot", "replication"):
        source = HERE.parent / "six-origin-01" / block
        focals = {(r["seed"], r["site"], r["born"]): r for r in rows(source / "focals.tsv")}
        for r in rows(source / "edges.tsv"):
            if r["changed"] == r["confirmed_edge"] == "1":
                f = focals[r["seed"], r["daughter_site"], r["daughter_born"]]
                cases.append((block, r["seed"], f["site"], f["born"], f["genome_hex"],
                              r["mother_site"], r["mother_born"], r["mother_hex"], f["start_fnv64"],
                              f["ordinary_births"], f["denied_births"], f["blocked_attempts"]))
    nodes = {(r["seed"], r["id"]): r for r in rows(
        HERE.parent / "trait-lineage-01/results/nodes.tsv.gz") if r["confirmed"] == "1" and r["seed"] != "19995"}
    for (seed, _), f in nodes.items():
        m = nodes.get((seed, f["actor"]))
        if m and m["genome"] != f["genome"]:
            block = "long-A" if int(seed) < 26177 else "long-B"
            cases.append((block, seed, f["site"], f["born"], f["genome"], m["site"], m["born"], m["genome"],
                          f["checkpoint"], f["ordinary_births"], f["denied_births"], f["blocked"]))
    assert len(cases) == len({r[1:4] for r in cases}) == 75
    return sorted(cases, key=lambda r: (int(r[1]), int(r[3]), int(r[2])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    out = args.directory
    out.mkdir(parents=True, exist_ok=True)
    data = cases()
    header = "block seed site born genome maker maker_born maker_genome hash ordinary denied blocked"
    with (out / "cases.tsv").open("w") as stream:
        print(*header.split(), sep="\t", file=stream)
        for row in data:
            print(*row, sep="\t", file=stream)
    command = [args.binary.resolve(), out]
    if args.reverse:
        command.append("--reverse")
    subprocess.run(command, input="".join(" ".join(row) + "\n" for row in data), text=True, check=True)
    nodes = out / "nodes.tsv"
    with nodes.open("rb") as src, nodes.with_suffix(".tsv.gz").open("wb") as target:
        with gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0, compresslevel=6) as dest:
            shutil.copyfileobj(src, dest)
    nodes.unlink()


if __name__ == "__main__":
    main()
