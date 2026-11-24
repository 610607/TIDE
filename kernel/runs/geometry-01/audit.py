"""Select the complete follow-up cohort and reconcile each ordinary fork to the field."""
import argparse
import subprocess
from collections import defaultdict
from pathlib import Path

from geometry import BUILD, END, READER, require, rows_to_file, table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--fork", type=Path, default=BUILD / "geometry/fork")
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    products = table(args.data/"products.tsv")
    reasons = defaultdict(set)
    expected = defaultdict(list)
    for r in table(args.data/"readers.tsv"):
        if r["compatible_east"] == "1":
            reasons[(r["width"],r["seed"],r["site"],r["born"])].add("compatible_east")
    for r in products:
        mother = (r["width"],r["seed"],r["mother_site"],r["mother_born"])
        child = (r["width"],r["seed"],r["child_site"],r["child_born"])
        expected[mother].append((r["child_born"],r["child_site"],r["inputs_hex"],r["child_hex"]))
        if r["mother_hex"] == r["child_hex"] == READER:
            reasons[mother].add("reader_mother")
            reasons[child].add("reader_daughter")
    keys = sorted(reasons,key=lambda k: tuple(map(int,k)))
    columns = ("width","seed","site","born")
    outputs = ["forks.tsv", "fork-products.tsv", "fork-openings.tsv"]
    command = [args.fork.resolve(), *(args.data/name for name in outputs)]
    if args.reverse:
        command.append("--reverse")
    subprocess.run(command, input="".join("\t".join(k)+"\n" for k in keys), text=True, check=True)
    observed = defaultdict(list)
    for r in table(args.data/outputs[1]):
        if r["branch"] == "ordinary" and int(r["tick"]) <= END:
            key = tuple(r[c] for c in columns)
            observed[key].append((r["tick"],r["child_site"],r["inputs_hex"],r["product_hex"]))
    branches = defaultdict(dict)
    for r in table(args.data/outputs[0]):
        key = tuple(r[c] for c in columns)
        branches[key][r["branch"]] = r["start_fnv64"]
        require(int(r["death"]) == int(r["born"])+81, "fork ended before age death")
    for k in keys:
        require(observed[k] == expected[k], "ordinary fork differs from original births")
        require(set(branches[k]) == {"ordinary","deny_own","deny_all"} and len(set(branches[k].values())) == 1,
                "fork initial states did not match")
    rows_to_file(args.data/"fork-targets.tsv", [dict(zip(columns,k),reason=",".join(sorted(reasons[k])))
                                                for k in keys], [*columns,"reason"])


if __name__ == "__main__":
    main()
