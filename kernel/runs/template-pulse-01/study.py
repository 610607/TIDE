"""Audit the matched branches and score post-withdrawal transmission by daughter."""
import argparse
import csv
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "six-origin-01"


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def save(path, rows, columns=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, columns or list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check(ok, message):
    if not ok:
        raise ValueError(message)


def targets():
    entries = {}
    for cohort in ("pilot", "replication"):
        d = SOURCE/cohort
        focals = {(r["seed"],r["site"],r["born"]): r for r in read(d/"focals.tsv")}
        ordinary = defaultdict(list)
        for r in read(d/"retention.tsv"):
            ordinary[r["seed"],r["daughter_site"],r["daughter_born"]].append(r)
        for edge in read(d/"edges.tsv"):
            if edge["changed"] == edge["confirmed_edge"] == "1":
                key = edge["seed"],edge["daughter_site"],edge["daughter_born"]
                focal = focals[key]
                case = "-".join(key)
                check(case not in entries and focal["dependent"]=="1", "invalid enrollment")
                entries[case] = (cohort, focal, ordinary[key])
    check(Counter(v[0] for v in entries.values())=={"pilot":31, "replication":9}, "cohort differs")
    return entries


def audit(out, entries):
    lives, products, copies = {}, defaultdict(list), defaultdict(list)
    for r in read(out/"lifetimes.tsv"):
        key = tuple(r[k] for k in ("case_id","arm","role","permission"))
        check(key not in lives and int(r["death"])==int(r["born"])+81, "invalid focal lifetime")
        check(int(r["initial_living"])+int(r["world_births"])-int(r["world_deaths"])==int(r["living"]),
              "world ledger differs")
        lives[key] = r
    for r in read(out/"births.tsv"):
        products[tuple(r[k] for k in ("case_id","arm","role","permission"))].append(r)
    for r in read(out/"copies.tsv"):
        key = tuple(r[k] for k in ("case_id","arm","role","permission"))
        copies[key+(r["allocation"],)].append(r)
        if r["supplied"]=="1":
            life = lives[key]
            check(key[1:]==("matched","daughter","on") and r["allocation"]=="1" and
                  r["source"]==life["pin_site"] and int(r["tick"])<=int(life["withdrawal"]),
                  "template used beyond its assigned scope")
    for key, life in lives.items():
        check(len(products[key])==int(life["focal_births"]), "missing focal birth")
        for r in products[key]:
            writes = copies[key+(r["allocation"],)]
            check("".join(w["input_hex"] for w in writes)==r["inputs_hex"] and
                  "".join(w["output_hex"] for w in writes)==r["product_hex"], "incomplete product trace")
    uses = defaultdict(list)
    for r in read(out/"template-uses.tsv"):
        f = lives[r["case_id"],r["arm"],"grandchild","on"]
        ticks = [int(t) for t in r["copy_ticks"].split(",")]
        check(r["template_site"]==f["site"] and r["template_born"]==f["born"] and
              r["template_hex"]==f["genome_hex"] and r["copier_site"]!=f["site"] and
              len(ticks)==int(r["bytes_from_template"]) and
              int(f["born"])<min(ticks)<=max(ticks)<int(r["product_born"])<=int(f["death"]),
              "invalid template contribution")
        uses[r["case_id"],r["arm"]].append(r)
    rows, witnesses = [], []
    witness_columns = ("cohort seed case_id arm grandchild_site grandchild_born great_grandchild_site "
                       "great_grandchild_born genome_hex inputs_hex source_sites source_kinds "
                       "allocation_opening_hex bytes_from_living_daughter").split()
    for case,(cohort,focal,archive) in entries.items():
        by_arm = {arm:lives[case,arm,"daughter","on"] for arm in ("ordinary","matched")}
        for name in ("start_hash","genome_hex","first_reserve","pin_tick","pin_site","pin_hash"):
            check(by_arm["ordinary"][name]==by_arm["matched"][name], "pre-intervention states differ")
        check(by_arm["ordinary"]["start_hash"]==focal["start_fnv64"], "natural checkpoint differs")
        expect = [(r["grandchild_site"],r["grandchild_born"],r["inputs_hex"],r["grandchild_hex"]) for r in archive]
        observed = [(r["site"],r["born"],r["inputs_hex"],r["product_hex"])
                    for r in products[case,"ordinary","daughter","on"]]
        check(expect == observed, "ordinary daughter products differ from the historical field")
        genome = focal["genome_hex"]
        for arm,life in by_arm.items():
            first = [r for r in products[case,arm,"daughter","on"] if r["allocation"]=="1"]
            check(len(first)==int(life["first_outcome"]=="birth"), "first-attempt mismatch")
            row = dict(cohort=cohort,seed=focal["seed"],case_id=case,arm=arm,daughter_hex=genome,
                       first_outcome=life["first_outcome"], template_bytes=life["template_bytes"],
                       first_birth=int(bool(first)), input_matches=0, exact_grandchild=0,
                       grandchild_hex="-", ordinary_births=0, denied_births=0,
                       grandchild_dependent=0, exact_and_reproduces=0, exact_and_dependent=0,
                       same_sequence_great_grandchildren=0, primary=0, external_primary=0,
                       products_using_grandchild=0, other_exact_copies_of_grandchild=0)
            if first:
                birth = first[0]
                key = case,arm,"grandchild","on"
                on, off = lives[key],lives[case,arm,"grandchild","off"]
                check(on["start_hash"]==off["start_hash"] and on["site"]==birth["site"] and
                      on["born"]==birth["born"]==life["withdrawal"] and on["genome_hex"]==birth["product_hex"],
                      "post-withdrawal fork mismatch")
                dependent = int(on["focal_births"])>0 and off["focal_births"]=="0"
                check(not dependent or int(off["blocked_attempts"])>0, "loss without denied external copy")
                if arm=="ordinary" and archive[0]["grandchild_dependent"]!="-":
                    check(int(dependent)==int(archive[0]["grandchild_dependent"]), "natural denial differs")
                exact = genome==birth["product_hex"]
                retained = [p for p in products[key] if p["product_hex"]==genome]
                neighbors = uses[case,arm]
                row.update(input_matches=int(birth["inputs_hex"]==genome), exact_grandchild=int(exact),
                           grandchild_hex=birth["product_hex"],ordinary_births=int(on["focal_births"]),
                           denied_births=int(off["focal_births"]),grandchild_dependent=int(dependent),
                           exact_and_reproduces=int(exact and int(on["focal_births"])>0),
                           exact_and_dependent=int(exact and dependent),same_sequence_great_grandchildren=len(retained),
                           primary=int(exact and dependent and bool(retained)),
                           external_primary=int(exact and dependent and any(int(p["external_bytes"]) for p in retained)),
                           products_using_grandchild=len(neighbors), other_exact_copies_of_grandchild=sum(
                               int(r["aligned_bytes"])==len(bytes.fromhex(r["template_hex"])) and
                               r["template_hex"]==r["product_hex"] for r in neighbors))
                if row["primary"]:
                    for p in retained:
                        reads = copies[key+(p["allocation"],)]
                        parent_bytes = sum(r["bank"]=="occupied" and r["source"]==focal["site"] and
                                           r["bank_born"]==focal["born"] for r in reads)
                        witnesses.append(dict(zip(witness_columns,(cohort,focal["seed"],case,arm,on["site"],
                            on["born"],p["site"],p["born"],genome,p["inputs_hex"],
                            ",".join(r["source"] for r in reads),",".join(r["bank"] for r in reads),p["opening_hex"],
                            parent_bytes),strict=True)))
            rows.append(row)
    save(out/"cases.tsv",rows)
    save(out/"witnesses.tsv",witnesses,witness_columns)
    stages = ("first_birth","input_matches","exact_grandchild","exact_and_reproduces",
              "exact_and_dependent","primary","external_primary")
    totals = []
    for cohort in ("pilot","replication","pooled"):
        selected = [r for r in rows if cohort=="pooled" or r["cohort"]==cohort]
        for stage in stages:
            sets = [{r["case_id"] for r in selected if r["arm"]==a and r[stage]} for a in ("ordinary","matched")]
            base, pulse = sets
            totals.append(dict(cohort=cohort,stage=stage,pairs=len(selected)//2,ordinary=len(base),
                               matched=len(pulse),both=len(base & pulse),matched_only=len(pulse-base),
                               ordinary_only=len(base-pulse),matched_seeds=len({r["seed"] for r in selected
                                                                             if r["case_id"] in pulse})))
    save(out/"summary.tsv",totals)
    roles = []
    for cohort in ("pilot","replication","pooled"):
        exact = [r for r in rows if r["arm"]=="matched" and r["exact_grandchild"]
                 and (cohort=="pooled" or r["cohort"]==cohort)]
        own = {r["case_id"] for r in exact if r["same_sequence_great_grandchildren"]}
        other = {r["case_id"] for r in exact if r["other_exact_copies_of_grandchild"]}
        roles.append(dict(cohort=cohort,exact_grandchildren=len(exact),executed_exact_birth=len(own),
                          supplied_exact_neighbor_birth=len(other),both=len(own & other),
                          either_observed=len(own | other)))
    save(out/"roles.tsv",roles)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("binary",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--reverse",action="store_true")
    args = p.parse_args()
    entries = targets()
    args.out.mkdir(parents=True,exist_ok=True)
    data = "".join(" ".join(f[k] for k in ("seed","site","born","genome_hex","start_fnv64"))+"\n"
                   for _,f,_ in entries.values())
    subprocess.run([args.binary.resolve(),args.out]+(["--reverse"] if args.reverse else []),
                   input=data,text=True,check=True)
    audit(args.out,entries)


if __name__=="__main__":
    main()
