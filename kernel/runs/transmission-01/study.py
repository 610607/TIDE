"""Replay the frozen pedigrees and take an individual-level census of reader opportunities."""
import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
HORIZON = HERE.parent / "horizon-01"
PERSIST = HERE.parent / "persistence-01"
sys.path.insert(0, str(HORIZON))
from measure import ANCESTOR, Assays, Setup, require, table

READER = b"RSCLD".hex()
BUILD = HERE.parents[1] / "build"
ROOT = (36, 0)
LIMIT = 4096


@dataclass
class Contact:
    tick: int
    site: int
    kind: str
    genome: str


@dataclass
class View:
    tick: int
    other_readers: int
    banks: list


@dataclass
class Individual:
    genome: str
    parent: tuple | None = None
    inputs: str = ""
    first: Contact | None = None
    hits: int = 0
    children: list = field(default_factory=list)
    death: int | None = None
    views: list = field(default_factory=list)
    attempt: int | None = None
    first_effect: str = "-"

    def exposed_births(self):
        return [kid for kid in self.children if self.first and self.first.tick <= kid[1]]


def replay(binary, arm, seed, reverse):
    command = [binary, arm, str(seed)] + (["--reverse"] if reverse else [])
    people = {ROOT: Individual(ANCESTOR)}
    hashes = {}
    for line in subprocess.check_output(command, text=True).splitlines():
        kind, t, *args = line.split("\t")
        tick = int(t)
        if kind == "checkpoint":
            hashes[tick] = args[0]
            continue
        cpu = int(args[0]), int(args[1])
        p = people[cpu]
        if kind == "birth":
            child = int(args[2]), tick
            require(child not in people, "reused birth identity")
            p.children.append(child)
            people[child] = Individual(args[3], cpu, args[4])
        elif kind == "hit":
            if not p.first:
                p.first = Contact(tick, int(args[2]), args[3], args[4])
            p.hits += 1
        elif kind == "death":
            require(p.death is None, "duplicate death")
            p.death = tick
        elif kind == "view":
            require(p.genome == READER and p.attempt is None, "unexpected spatial census")
            p.views.append(View(tick, int(args[2]), [bank.split(":") for bank in args[3:]]))
        elif kind == "attempt":
            require(p.views[-1].tick == tick - 1 and p.attempt is None, "missing first attempt snapshot")
            p.attempt, p.first_effect = tick, args[2]
        else:
            raise ValueError(kind)
    return people, hashes


def census(people, tick):
    births = sum(cpu != ROOT and cpu[1] <= tick for cpu in people)
    deaths = sum(p.death is not None and p.death <= tick for p in people.values())
    living = 1 + births - deaths
    recent = sum(cpu != ROOT and tick-80 < cpu[1] <= tick for cpu in people)
    status = "extinct" if living == 0 else "reproducing" if recent else "stagnant"
    return dict(births=births, deaths=deaths, living=living, final80_births=recent, status=status)


def check_reference(stats, digest, row):
    require(digest == row["state_fnv64"] and all(str(v) == row[k] for k, v in stats.items()),
            f"field checkpoint changed in seed {row['seed']}")


def direction(src, dest):
    x, y = src % 8, src // 8
    for d, (dx, dy) in enumerate(((0,1), (1,0), (0,-1), (-1,0))):
        if ((y+dy) % 8) * 8 + (x+dx) % 8 == dest:
            return d
    raise ValueError("nonlocal contact")


def own_assay(assays, arm, cpu, individual):
    hit = individual.first
    if hit is None:
        return "-", "no_contact"
    if hit.kind != "o":
        return "-", {"r":"reserved_first", "f":"free_first"}[hit.kind]
    case = Setup(arm, individual.genome, hit.genome, direction(cpu[0], hit.site))
    return case.key(), assays.run(case, LIMIT)[1]


def rows_to_file(path, rows, empty_columns=None):
    with path.open("w", newline="") as stream:
        columns = list(rows[0]) if rows else empty_columns
        if not columns:
            raise ValueError(f"missing output schema for {path}")
        w = csv.DictWriter(stream, columns, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def descendants(people, root):
    stack = [(root, 0, True)]
    while stack:
        cpu, depth, clonal = stack.pop()
        yield cpu, depth, clonal
        for kid in reversed(people[cpu].children):
            stack.append((kid, depth+1, clonal and people[kid].genome == people[cpu].genome))


FETCH_COLUMNS = """seed root_site root_born depth parent_site parent_born parent_hex child_site
child_born child_hex copy_inputs_hex substitutions parent_common_assay child_common_assay
parent_common child_common retained_capacity parent_own_assay child_own_assay parent_own child_own
parent_contact_by_birth child_first_contact_tick child_field_births child_births_after_contact
field_supported""".split()


def fetch_study(args, assays):
    roots = [r for r in table(HORIZON / "families.tsv") if r["cohort"] == "prospective"]
    events = [r for r in table(HORIZON / "events.tsv") if r["cohort"] == "prospective" and r["confirmed4096"] == "1"]
    checkpoints = table(PERSIST / "fields.tsv")
    old_families = {(r["seed"], int(r["root_site"]), int(r["root_born"])): r
                    for r in table(PERSIST / "families.tsv") if r["tick"] == "4096"}
    families, changes = [], []
    for seed in sorted({r["seed"] for r in roots}, key=int):
        people, hashes = replay(args.field, "fetch", seed, args.reverse)
        for row in checkpoints:
            if row["seed"] == seed:
                t = int(row["tick"])
                check_reference(census(people, t), hashes[t], row)
        for r in (r for r in roots if r["seed"] == seed):
            root = int(r["root_site"]), int(r["root_born"])
            field_events = [e for e in events if e["seed"] == seed and
                            (int(e["family_root_site"]), int(e["family_root_born"])) == root]
            anchor = min(field_events, key=lambda e: (int(e["tick"]), int(e["daughter_site"])))
            arm, founder_hex, donor, side = anchor["mother_assay"].split("-")
            require(people[root].genome == founder_hex == r["genome_hex"], "wrong family anchor")
            members = list(descendants(people, root))
            clones = [cpu for cpu, _, clonal in members if clonal]
            prefix = old_families[(seed,*root)]
            require(len(clones) == int(prefix["members"]) and max(c[1] for c in clones) == int(prefix["last_birth"])
                    and all(people[c].death is not None for c in clones)
                    and max(people[c].death for c in clones) == int(prefix["extinction_tick"]),
                    "clonal history changed")
            edges = []
            for child, depth, _ in members:
                q = people[child]
                if child == root or people[q.parent].genome == q.genome:
                    continue
                parent, p = q.parent, people[q.parent]
                a, b = (Setup(arm, g, donor, "NESW".index(side)) for g in (p.genome, q.genome))
                pa, qa = assays.run(a, LIMIT)[1], assays.run(b, LIMIT)[1]
                pk, po = own_assay(assays, arm, parent, p)
                qk, qo = own_assay(assays, arm, child, q)
                prior = bool(p.first and p.first.tick <= child[1])
                births = len(q.exposed_births())
                retained = pa == qa == "dependent"
                field_supported = retained and prior and births > 0 and po == qo == "dependent"
                substitutions = sum(x != y for x,y in zip(bytes.fromhex(q.inputs), bytes.fromhex(q.genome)))
                edges.append(dict(zip(FETCH_COLUMNS, (seed,*root,depth,*parent,p.genome,*child,q.genome,
                    q.inputs,substitutions,a.key(),b.key(),pa,qa,int(retained),pk,qk,po,qo,int(prior),
                    q.first.tick if q.first else "-",len(q.children),births,int(field_supported)), strict=True)))
            changes.extend(edges)
            living = sum(people[c].death is None for c,_,_ in members)
            families.append(dict(seed=seed,root_site=root[0],root_born=root[1],genome_hex=founder_hex,
                anchor_event_tick=anchor["tick"],anchor_assay=anchor["mother_assay"],clonal_members=len(clones),
                all_members=len(members),genomes=len({people[c].genome for c,_,_ in members}),
                changed_births=len(edges),retained_capacity=sum(e["retained_capacity"] for e in edges),
                field_supported=sum(e["field_supported"] for e in edges),last_birth=max(c[1] for c,_,_ in members),
                final_living=living,extinction_tick="-" if living else max(people[c].death for c,_,_ in members)))
    return families, changes


def reader_record(seed, cpu, p, people, assays):
    views = p.views
    end = p.attempt-1 if p.attempt else p.death-1 if p.death else 512
    require([v.tick for v in views] == list(range(cpu[1], end+1)), "incomplete opportunity window")
    donors = {g for v in views for k,g in v.banks if k == "o"}
    compatible = {g for g in donors if assays.run(Setup("read", READER, g, 1), LIMIT)[1] == "dependent"}

    def live_match(bank):
        return bank[0] == "o" and bank[1] in compatible

    initial = views[0]
    east = views[-1].banks[1]
    exact = {k for v in views for k,g in v.banks if g == READER}
    return dict(seed=seed,site=cpu[0],born=cpu[1],death=p.death or "-",window_last=end,
        first_attempt=p.attempt or "-",first_effect=p.first_effect,
        first_east_bank=east[0] if p.attempt else "-",first_east_hex=east[1] if p.attempt else "-",
        exact_other_live_at_birth=int(initial.other_readers > 0),
        exact_other_live_in_window=int(any(v.other_readers for v in views)),
        exact_local_bank_kinds="".join(sorted(exact)) or "-",
        exact_east_bank_kinds="".join(sorted({v.banks[1][0] for v in views if v.banks[1][1] == READER})) or "-",
        compatible_any_at_birth=int(any(map(live_match, initial.banks))),
        compatible_east_at_birth=int(live_match(initial.banks[1])),
        compatible_any_in_window=int(any(live_match(bank) for v in views for bank in v.banks)),
        compatible_east_in_window=int(any(live_match(v.banks[1]) for v in views)),
        compatible_east_at_attempt=int(live_match(east)) if p.attempt else "-",
        live_genomes_in_window=",".join(sorted(donors)) or "-",successful_reads=p.hits,field_births=len(p.children),
        reader_products=sum(people[kid].genome == READER for kid in p.children),
        products_with_reads=sum(people[kid].hits > 0 for kid in p.children))


PAIR_COLUMNS = """seed event_tick product_site mother_site mother_born child_site child_born
mother_assay mother_result child_assay child_result confirmed""".split()
PRODUCT_COLUMNS = """seed mother_site mother_born child_site child_born inputs_hex product_hex
successful_reads births births_after_contact death""".split()


def read_study(args, assays):
    archives = []
    for f in (HERE.parent/"pilot-01/seeds.tsv", HERE.parent/"replication-01/seeds.tsv", HORIZON/"field-seeds.tsv"):
        archives.extend(table(f))
    reference = {r["seed"]:r for r in archives if r["arm"] == "read"}
    historical = {(int(r["seed"]),int(r["child_site"]),int(r["child_born"])):r
                  for r in table(HORIZON/"read-births.tsv")}
    verified_births = set()
    seeds, readers, products, links = [], [], [], []
    for seed in range(1,321):
        people, hashes = replay(args.field, "read", seed, args.reverse)
        stats = census(people, 512)
        observations, pairs = [], []
        exposed = 0
        for cpu, p in people.items():
            if p.genome == READER:
                observations.append(reader_record(seed, cpu, p, people, assays))
            for child in p.exposed_births():
                exposed += 1
                q = people[child]
                if seed <= 64:
                    orig = historical[(seed,*child)]
                    require(p.genome == orig["mother_genome"] and q.genome == orig["product_hex"] and
                            (int(orig["mother_site"]), int(orig["mother_born"])) == cpu,
                            "historical exposed birth changed")
                    verified_births.add((seed,*child))
                for kid in q.exposed_births():
                    pk, po = own_assay(assays,"read",cpu,p)
                    qk, qo = own_assay(assays,"read",child,q)
                    pairs.append(dict(zip(PAIR_COLUMNS,(seed,kid[1],kid[0],*cpu,*child,pk,po,qk,qo,
                        int(po == qo == "dependent")), strict=True)))
            if p.genome == READER:
                for child in p.children:
                    q = people[child]
                    products.append(dict(zip(PRODUCT_COLUMNS,(seed,*cpu,*child,q.inputs,q.genome,q.hits,
                        len(q.children),len(q.exposed_births()),q.death or "-"), strict=True)))
        total_hits = sum(p.hits for p in people.values())
        if seed <= 64:
            old = reference[str(seed)]
            check_reference(stats, hashes[512], old)
            require(total_hits == sum(int(old[k+"_contacts"]) for k in ("free","live","reserved"))
                    and len(pairs) == int(old["candidate_births"]) and exposed == int(old["exposed_births"]),
                    "historical screen changed")
        seeds.append(dict(seed=seed,cohort="historical" if seed <= 64 else "prospective",**stats,
            newborn_readers=len(observations),readers_attempting=sum(o["first_attempt"] != "-" for o in observations),
            readers_copying=sum(bool(o["successful_reads"]) for o in observations),
            readers_dividing=sum(bool(o["field_births"]) for o in observations),
            reader_births=sum(o["field_births"] for o in observations),
            exact_other_live=sum(o["exact_other_live_in_window"] for o in observations),
            compatible_any=sum(o["compatible_any_in_window"] for o in observations),
            compatible_east=sum(o["compatible_east_in_window"] for o in observations),
            compatible_at_attempt=sum(o["compatible_east_at_attempt"] == 1 for o in observations),
            external_reads=total_hits,all_exposed_births=exposed,candidate_events=len(pairs),
            confirmed_events=sum(p["confirmed"] for p in pairs),state_fnv64=hashes[512]))
        readers.extend(observations)
        links.extend(pairs)
    require(verified_births == historical.keys(), "historical exposed birth omitted")
    return seeds, readers, products, links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--field",type=Path,default=BUILD/"transmission/field")
    parser.add_argument("--observe",type=Path,default=BUILD/"observe")
    parser.add_argument("--reverse",action="store_true")
    args = parser.parse_args()
    assays = Assays(args.observe.resolve())
    assays.check_controls()
    families, changes = fetch_study(args, assays)
    seeds, readers, products, links = read_study(args, assays)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows, schema in [("families",families,None),("changed-births",changes,FETCH_COLUMNS),
            ("read-seeds",seeds,None),("readers",readers,None),("reader-products",products,PRODUCT_COLUMNS),
            ("read-links",links,PAIR_COLUMNS),("generations",assays.records,None)]:
        rows_to_file(args.out/(name+".tsv"),rows,schema)


if __name__ == "__main__":
    main()
