"""Distinguish mutation on either edge of the archived confirmed three-individual pedigrees."""
import argparse
import csv
import subprocess
from pathlib import Path

from study import BUILD, HERE, HORIZON, require, rows_to_file, table


def event_key(row):
    return tuple(row[key] for key in ("seed", "tick", "daughter_site"))


def copy_trace(tide, seed):
    pending, births, first = {}, {}, {}
    trace = subprocess.check_output([tide, "trace", "fetch", seed], text=True)
    for e in csv.DictReader(trace.splitlines(), delimiter="\t"):
        actor = e["actor"], e["born"]
        if e["fetch_kind"] != "-" and actor not in first:
            first[actor] = e
        if e["effect"] == "reserve":
            pending[actor] = []
        elif e["effect"] == "copy":
            pending[actor].append(e)
        elif e["effect"] == "birth":
            births[(e["target"], e["tick"])] = (actor, pending.pop(actor), e)
    return births, first


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--tide",type=Path,default=BUILD/"tide")
    args = parser.parse_args()
    rows = table(HORIZON/"events.tsv")
    field_rows = {}
    for p in [HORIZON.parent/"pilot-01/links.tsv", HORIZON.parent/"replication-01/links.tsv",
              HORIZON/"field-links.tsv"]:
        field_rows.update((event_key(r),r) for r in table(p))
    traces, results, witnesses = {}, [], []
    for r in rows:
        if r["confirmed4096"] != "1":
            continue
        f = field_rows[event_key(r)]
        mother = f["mother_site"],f["mother_born"]
        child = f["child_site"],f["child_born"]
        grandchild = f["daughter_site"],f["tick"]
        first_change = f["mother_genome"] != f["child_genome"]
        next_change = f["child_genome"] != f["daughter_hex"]
        require((not first_change and not next_change) == (r["three_identical_genomes"] == "1"),
                "archived genome comparison differs")
        results.append(dict(cohort=r["cohort"],seed=r["seed"],tick=r["tick"],daughter_site=r["daughter_site"],
            mother_site=mother[0],mother_born=mother[1],mother_hex=f["mother_genome"],child_site=child[0],
            child_born=child[1],child_hex=f["child_genome"],grandchild_hex=f["daughter_hex"],
            change_to_tested_child=int(first_change),change_to_grandchild=int(next_change),
            mother_assay=r["mother_assay"],child_assay=r["child_assay"]))
        if not first_change:
            continue
        seed = r["seed"]
        if seed not in traces:
            traces[seed] = copy_trace(args.tide.resolve(),seed)
        births, first = traces[seed]
        for role, actor, offspring, product in [("mother",mother,child,f["child_genome"]),
                                                ("child",child,grandchild,f["daughter_hex"])]:
            parent, copies, birth = births[offspring]
            contact = first[parent]
            require(parent == actor and product == birth["product_hex"] and
                bytes(int(e["input"]) for e in copies).hex() == f[role+"_genome"] and
                bytes(int(e["output"]) for e in copies).hex() == product and
                all(e["read_site"] == actor[0] and e["target"] == offspring[0] for e in copies),
                "field lineage or copy provenance differs")
            require(contact["tick"] == f[role+"_contact_tick"] and contact["fetch_site"] == f[role+"_donor_site"]
                    and contact["fetch_kind"] == "occupied" and contact["fetch_hex"] == f[role+"_donor_hex"]
                    and int(contact["tick"]) <= int(birth["tick"]), "first field donor differs")
            for e in copies:
                witnesses.append(dict(seed=seed,confirmed_tick=r["tick"],role=role,site=actor[0],born=actor[1],
                    donor_site=contact["fetch_site"],first_fetch=contact["tick"],donor_hex=contact["fetch_hex"],
                    copy_tick=e["tick"],instruction_site=e["fetch_site"],read_site=e["read_site"],
                    write_site=e["target"],offset=e["write_offset"],input_hex=f"{int(e['input']):02x}",
                    output_hex=f"{int(e['output']):02x}",product_tick=birth["tick"],product_hex=product))
    args.out.mkdir(exist_ok=True,parents=True)
    rows_to_file(args.out/"archived-pairs.tsv",results)
    rows_to_file(args.out/"archived-witness.tsv",witnesses)


if __name__ == "__main__":
    main()
