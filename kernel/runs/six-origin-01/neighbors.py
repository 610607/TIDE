"""Post hoc lookup of intact local templates at the actual external-copy openings."""
import argparse
import csv
import subprocess
from pathlib import Path


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("cohort", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    cohort = args.cohort
    edges = {(r["seed"],r["daughter_site"],r["daughter_born"]): r for r in read(cohort/"edges.tsv")}
    queries, products = {}, []
    for r in read(cohort/"retention.tsv"):
        if r["in_window"] != "1":
            continue
        edge = edges.get((r["seed"],r["grandchild_site"],r["grandchild_born"]))
        records = []
        for write in edge["source_writes"].split(",") if edge else ():
            index,tick,source,offset,kind,born,owner = write.split("/")
            query = tuple(map(int,(r["seed"],tick,r["daughter_site"],r["daughter_born"],source,offset)))
            if query in queries:
                raise ValueError("duplicate copy event")
            queries[query] = (r["inputs_hex"][2*int(index):2*int(index)+2], kind, born, owner)
            records.append(query)
        products.append((r,records))
    query_text = "".join(" ".join(map(str,q))+"\n" for q in sorted(queries))
    with (cohort/"neighborhoods.tsv").open("w") as out:
        subprocess.run([args.reference.resolve(), "--neighbors"] + (["--reverse"] if args.reverse else []),
                       input=query_text,text=True,stdout=out,check=True)
    observed = {}
    for snap in read(cohort/"neighborhoods.tsv"):
        key = tuple(int(snap[k]) for k in ("seed","tick","site","born","source","offset"))
        banks = {int(s[0]): s[1:] for s in (snap[d].split("/") for d in "NESW")}
        kind,born,owner,genome = banks[key[4]]
        byte = genome[2*key[5]:2*key[5]+2]
        if (byte, kind[0], born, owner) != queries[key]:
            raise ValueError("selected neighbor differs from traced source")
        observed[key] = banks
    if observed.keys() != queries.keys():
        raise ValueError("missing opening snapshot")
    columns = ("seed daughter_site daughter_born grandchild_site grandchild_born external_copies "
               "first_has_template any_opening_has_template stable_neighbor_has_template "
               "any_opening_selected_template").split()
    with (cohort/"availability.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        for r,records in products:
            sets = [{site for site,b in observed[q].items() if b[-1] == r["daughter_hex"]} for q in records]
            outcomes = ([int(bool(sets[0])),int(any(sets)),int(bool(set.intersection(*sets))),
                         int(any(q[4] in present for q,present in zip(records,sets,strict=True)))]
                        if sets else ["-"]*4)
            writer.writerow([*(r[k] for k in columns[:5]),len(records),*outcomes])


if __name__ == "__main__":
    main()
