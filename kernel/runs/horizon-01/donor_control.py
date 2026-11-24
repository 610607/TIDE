"""Replay both predeclared five-byte donors in the read-only assay."""
import argparse
from pathlib import Path

from measure import Assays, BUILD, Setup, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--observe", type=Path, default=BUILD / "observe")
    args = parser.parse_args()
    assays = Assays(args.observe.resolve())
    for donor in ("R.CLD", "RSCLD"):
        assays.run(Setup("read", b"RSCLD".hex(), donor.encode().hex(), 1), 4096)
    args.out.mkdir(exist_ok=True, parents=True)
    save(args.out / "donor-generations.tsv", assays.records)


if __name__ == "__main__":
    main()
