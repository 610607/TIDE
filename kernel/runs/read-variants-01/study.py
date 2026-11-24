"""Run the frozen panels, verify historical controls and score first-daughter transfers."""
import argparse
import csv
import itertools
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "inheritance-01/pedigrees"
ALPHABET = "R.JTSH+>CLDP"
READER = "RSCLD"
PADDED = "R.SCLD"


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def save(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def target(row):
    return tuple(int(row[key]) for key in ("seed", "site", "born"))


def selected():
    return {target(r): r for r in read(ARCHIVE/"individuals.tsv")
            if r["parent_class"] == "dependent" and r["genome_hex"] == READER.encode().hex()}


def classify(on, off):
    if int(on["focal_births"]) == 0:
        return "no_ordinary_birth"
    if int(off["focal_births"]):
        return "reproduces_under_denial"
    check(int(off["blocked_attempts"]) > 0, "denial removed births without blocking reads")
    return "dependent"


def live_transfer(birth, program, donor):
    genome = program.encode().hex()
    hits = [record.split("/") for record in birth["reads"].split(",")]
    return (birth["inputs_hex"] == birth["product_hex"] == genome and len(hits) == len(program)
            and all((site, offset, kind, born) == (str(donor), str(i), "occupied", "0")
                    for i, (site, offset, kind, born, _) in enumerate(hits)))


def supplied_case(case, arms, products):
    program, site = case["assigned"], case["site"]
    on, off = (arms["focal", site, "0", mode] for mode in ("on", "off"))
    first = products["focal", site, "0", "on"][:1]
    row = dict(assigned=program, slot=program[1], second_source=case["second_source"],
               founder_class=classify(on, off), daughter_site="-", daughter_born="-", daughter_hex="-",
               live_first_source=0, daughter_class="absent", daughter_slot1_executions=0,
               daughter_births=0, daughter_denied_births=0, paired_transmission=0,
               exact_continuation=0, same_program_from_any_source=0, first_exact_grandchild="-",
               ordinary_grandchild_products="-")
    if not first:
        return row
    birth = first[0]
    kid = birth["child_site"], birth["child_born"]
    key = ("daughter", *kid)
    normal, denied = arms[key+("on",)], arms[key+("off",)]
    outcome = classify(normal, denied)
    observed = products[key+("on",)]
    exact = [r for r in observed if live_transfer(r, program, 45)]
    source = live_transfer(birth, program, 37)
    qualifies = source and row["founder_class"] == outcome == "dependent"
    row.update(daughter_site=kid[0], daughter_born=kid[1], daughter_hex=birth["product_hex"],
               live_first_source=int(source), daughter_class=outcome,
               daughter_slot1_executions=normal["slot1_executions"], daughter_births=normal["focal_births"],
               daughter_denied_births=denied["focal_births"], paired_transmission=int(qualifies),
               exact_continuation=int(qualifies and bool(exact)),
               same_program_from_any_source=int(any(r["product_hex"] == program.encode().hex() for r in observed)),
               first_exact_grandchild=exact[0]["child_born"] if qualifies and exact else "-",
               ordinary_grandchild_products=",".join(r["product_hex"] for r in observed) or "-")
    return row


def audit(out, targets):
    cases = read(out/"cases.tsv")
    check(len({r["case_id"] for r in cases}) == len(cases), "duplicate case")
    lives, products = defaultdict(dict), defaultdict(lambda: defaultdict(list))
    for r in read(out/"lifetimes.tsv"):
        key = tuple(r[k] for k in ("role", "site", "born", "permission"))
        arms = lives[r["case_id"]]
        check(key not in arms, "duplicate lifetime")
        arms[key] = r
    for r in read(out/"products.tsv"):
        key = tuple(r[k] for k in ("role", "parent_site", "parent_born", "permission"))
        check(len(r["reads"].split(",")) == len(bytes.fromhex(r["inputs_hex"])) == len(bytes.fromhex(r["product_hex"])),
              "incomplete source provenance")
        products[r["case_id"]][key].append(r)
    case_ids = {r["case_id"] for r in cases}
    check(set(lives) == case_ids and set(products) <= case_ids, "foreign or missing case")
    historic = defaultdict(list)
    for path in ARCHIVE.glob("forks-*/products.tsv"):
        for r in read(path):
            if r["branch"] in ("ordinary", "deny_all"):
                historic[target(r), r["branch"]].append(tuple(r[k] for k in
                    ("child_site", "tick", "inputs_hex", "product_hex")))
    panels, counts, supplied = defaultdict(set), defaultdict(Counter), []
    for r in cases:
        arms, births = lives[r["case_id"]], products[r["case_id"]]
        for key, arm in arms.items():
            check(len(births[key]) == int(arm["focal_births"]), "missing product")
            check(arm["start_hash"] == arms[key[:3]+("on",)]["start_hash"], "unmatched fork")
            check(int(arm["initial_living"])+int(arm["world_births"])-int(arm["world_deaths"]) == int(arm["living"]),
                  "unbalanced population ledger")
            if key[-1] == "off":
                check(arm["external_reads"] == "0", "denied successful external read")
        site, born = r["site"], r["born"]
        on, off = [arms["focal", site, born, mode] for mode in ("on", "off")]
        state = classify(on, off)
        check(r["start_hash"] == on["start_hash"] and int(r["dependent"]) == int(state == "dependent"),
              "focal classification or start mismatch")
        check(len(arms) == 2+2*int(r["daughters_tested"]), "missing daughter fork")
        if state == "dependent" or r["panel"] == "supplied":
            daughter_states = []
            for birth in births["focal", site, born, "on"]:
                kid = ("daughter", birth["child_site"], birth["child_born"])
                daughter_states.append((classify(arms[kid+("on",)], arms[kid+("off",)]), birth["product_hex"]))
            check(len(daughter_states) == int(r["daughters_tested"]) and
                  sum(s == "dependent" for s, _ in daughter_states) == int(r["dependent_daughters"]) and
                  sum(s == "dependent" and g == r["assigned"].encode().hex() for s, g in daughter_states)
                  == int(r["dependent_same_sequence"]), "daughter outcomes differ")
        if r["panel"] == "supplied":
            supplied.append(supplied_case(r, arms, births))
            continue
        cpu = target(r)
        archived = targets[cpu]
        check(r["background_hash"] == archived["start_fnv64"], "wrong natural environment")
        panel, variant = r["panel"], r["assigned"]
        panels[cpu, panel].add(variant)
        score = counts[cpu[0], panel]
        score["cases"] += 1
        score[state] += 1
        score["with_dependent_daughter"] += int(r["dependent_daughters"]) > 0
        score["with_same_dependent_daughter"] += int(r["dependent_same_sequence"]) > 0
        if panel == "control":
            check(on["focal_births"] == archived["ordinary_births"] and
                  off["focal_births"] == archived["denied_births"] and off["blocked_attempts"] == archived["blocked_attempts"]
                  and state == archived["classification"] and r["start_hash"] == r["background_hash"],
                  "archived permission control differs")
            for mode, previous in (("on", "ordinary"), ("off", "deny_all")):
                observed = [tuple(b[k] for k in ("child_site", "child_born", "inputs_hex", "product_hex"))
                            for b in births["focal", site, born, mode]]
                check(observed == historic[cpu, previous], "archived control products differ")
    changes = {READER[:i]+op+READER[i+1:] for i, old in enumerate(READER) for op in ALPHABET if old != op}
    orders = {"".join(ops) for ops in itertools.permutations(READER)} - {READER}
    for cpu in targets:
        check(panels[cpu, "control"] == {READER} and panels[cpu, "substitution"] == changes and
              panels[cpu, "permutation"] == orders, "incomplete natural panel")
    check({(r["slot"], r["second_source"]) for r in supplied} ==
          set(itertools.product(ALPHABET, ("original", "matched"))) and len(supplied) == 24,
          "incomplete supplied comparison")
    controls = [r for r in supplied if r["assigned"] == PADDED]
    check(all(controls[0][k] == controls[1][k] for k in controls[0] if k != "second_source"),
          "identical supplied assignments differ")
    columns = ("cases", "dependent", "reproduces_under_denial", "no_ordinary_birth",
               "with_dependent_daughter", "with_same_dependent_daughter")
    save(out/"natural-summary.tsv", [dict(seed=seed, panel=panel, **{k: n[k] for k in columns})
         for (seed, panel), n in sorted(counts.items())])
    save(out/"supplied.tsv", supplied)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("binary", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--reverse", action="store_true")
    args = p.parse_args()
    targets = selected()
    check(Counter(k[0] for k in targets) == {3562:12, 11942:10}, "unexpected enrollment")
    args.out.mkdir(exist_ok=True, parents=True)
    data = "".join(f"{seed} {site} {born} {r['start_fnv64']}\n" for (seed,site,born), r in targets.items())
    subprocess.run([args.binary.resolve(), args.out] + (["--reverse"] if args.reverse else []),
                   input=data, text=True, check=True)
    audit(args.out, targets)


if __name__ == "__main__":
    main()
