"""Run all four field configurations and validate their matched stationary baseline."""
import argparse
import csv
import io
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("east", "bearing", "low", "high")


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    binary = args.binary.resolve()
    natural = HERE.parent / "six-origin-01"
    archive = {r["seed"]: r for group in ("pilot", "replication") for r in read(natural / group / "seeds.tsv")}
    stocks = HERE.parent / "sequence-stock-01" / "results"
    expected = defaultdict(set)
    for r in read(stocks / "living-template-births.tsv"):
        if r["executor"] != r["product"]:
            expected[r["seed"]].add(tuple(r[k] for k in ("tick", "product_site", "product", "executor_site",
                                                        "executor_born", "executor", "donor_site", "donor_born")))
    args.output.mkdir(parents=True, exist_ok=True)

    def run(item):
        seed, arm = item
        with tempfile.TemporaryDirectory(prefix="tide-spatial-") as name:
            directory = Path(name)
            command = [binary, seed, arm, directory]
            subprocess.run(command + (["--reverse"] if args.reverse else []), check=True)
            seed_raw = (directory / "seed.tsv").read_text()
            products_raw = (directory / "products.tsv").read_text()
        row, = csv.DictReader(io.StringIO(seed_raw), delimiter="\t")
        products = list(csv.DictReader(io.StringIO(products_raw), delimiter="\t"))
        check(row["seed"] == seed and row["arm"] == arm, f"{seed} {arm} configuration")
        n = {k: int(v) for k, v in row.items() if k not in ("arm", "state_fnv64", "status")}
        check(0 <= n["productive_pairs"] <= n["read_pairs"] <= n["encounters"] and
              0 <= n["facing_room_pairs"] <= n["facing_pairs"] <= n["encounters"], f"{seed} {arm} pairs")
        check(len(products) == n["exact_births"] == n["complete"] + n["incomplete"] ==
              sum(n[k] for k in ("north", "east", "south", "west")), f"{seed} {arm} births")
        check(sum(n[k] for k in ("born_n", "born_e", "born_s", "born_w")) == n["births"], "orientations")
        check(n["any_again"] == sum(p["complete"] == "1" and "1" in (p["self_again"], p["template_again"])
                                    for p in products), "product follow-up")
        if arm == "east":
            check(all(row[k] == archive[seed][k] for k in ("births", "deaths", "living", "final80_births",
                                                          "status", "state_fnv64", "external_births")), f"{seed} baseline")
            observed = {tuple(p[k] for k in ("child_born", "child_site", "product", "executor_site", "executor_born",
                                            "executor", "donor_birth_site", "donor_born")) for p in products}
            check(observed == expected[seed] and len(observed) == len(products), f"{seed} exact products")
            for p in products:
                src, exe = int(p["donor_birth_site"]), int(p["executor_site"])
                dx, dy = (src % 16 - exe % 16) % 16, (src // 16 - exe // 16) % 4
                check({(0,1):"N", (1,0):"E", (0,3):"S", (15,0):"W"}[dx,dy] == p["first_direction"],
                      f"{seed} archived direction")
        return seed_raw, products_raw

    items = ((str(seed), arm) for seed in range(19521, 21569) for arm in ARMS)
    with (args.output / "seeds.tsv").open("w") as seeds, (args.output / "products.tsv").open("w") as births:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for i, (seed_raw, products_raw) in enumerate(pool.map(run, items)):
                for f, raw in ((seeds, seed_raw), (births, products_raw)):
                    f.write(raw if i == 0 else raw.partition("\n")[2])
                if (i+1) % 1024 == 0:
                    print(f"{i+1}/8192 fields", flush=True)


if __name__ == "__main__":
    main()
