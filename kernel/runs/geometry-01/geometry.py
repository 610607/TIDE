"""Measure the prespecified geometry endpoints on resolved field histories."""
import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "transmission-01"
sys.path.insert(0, str(PREVIOUS))
from study import (ANCESTOR, BUILD, LIMIT, READER, ROOT, Assays, Contact, Individual,
                   Setup, View, census, check_reference, require, rows_to_file, table)

WIDTHS = (8, 4, 16)
SEEDS = range(321, 577)
END = 2048


@dataclass
class Field:
    people: dict
    hashes: dict
    external_writes: dict


def replay(binary, width, seed, reverse):
    cmd = [binary, str(width), str(seed)]
    if reverse:
        cmd.append("--reverse")
    people, hashes, sources = {ROOT: Individual(ANCESTOR)}, {}, {}
    for line in subprocess.check_output(cmd, text=True).splitlines():
        event, time, *data = line.split("\t")
        tick = int(time)
        if event == "hash":
            hashes[tick] = data[0]
            continue
        cpu = int(data[0]), int(data[1])
        p = people[cpu]
        if event == "birth":
            child = int(data[2]), tick
            require(child not in people, "duplicate birth")
            p.children.append(child)
            people[child] = Individual(data[3], cpu, data[4])
            if data[5] != "-":
                sources[child] = data[5]
        elif event == "read":
            if p.first is None:
                p.first = Contact(tick, int(data[2]), data[3], data[4])
            p.hits += 1
        elif event == "death":
            require(p.death is None, "duplicate death")
            p.death = tick
        elif event == "window":
            require(p.genome == READER and p.attempt is None, "unexpected reader")
            p.views.append(View(tick, int(data[2]), [v.split(":") for v in data[3:]]))
        elif event == "attempt":
            require(p.attempt is None and p.views[-1].tick == tick-1, "missing opening state")
            p.attempt, p.first_effect = tick, data[2]
        else:
            raise ValueError(event)
    require(set(hashes) == {512, END}, "missing checkpoint")
    return Field(people, hashes, sources)


def neighbor_direction(width, a, b):
    height = 64 // width
    x, y = a % width, a // width
    for d, (dx, dy) in enumerate(((0,1), (1,0), (0,-1), (-1,0))):
        if ((y+dy) % height)*width + (x+dx) % width == b:
            return d
    raise ValueError("nonlocal field contact")


def own_assay(width, assays, cpu, p):
    hit = p.first
    if hit.kind != "o":
        return "-", {"r":"reserved_first", "f":"free_first"}[hit.kind]
    case = Setup("read", p.genome, hit.genome, neighbor_direction(width, cpu[0], hit.site))
    return case.key(), assays.run(case, LIMIT)[1]


def reader_window(cpu, p, assays):
    last = p.attempt-1 if p.attempt else p.death-1 if p.death else END
    require([v.tick for v in p.views] == list(range(cpu[1],last+1)), "missing reader window")
    live_donors = {g for v in p.views for kind,g in v.banks if kind == "o"}
    compatible = {g for g in sorted(live_donors) if assays.run(Setup("read", READER, g, 1), LIMIT)[1] == "dependent"}

    def match(bank):
        return bank[0] == "o" and bank[1] in compatible

    east = p.views[-1].banks[1]
    return dict(site=cpu[0], born=cpu[1], last_view=last, attempt=p.attempt or "-",
                first_effect=p.first_effect, first_bank=east[0] if p.attempt else "-",
                first_genome=east[1] if p.attempt else "-", other_live_exact=int(any(v.other_readers for v in p.views)),
                compatible_any=int(any(match(b) for v in p.views for b in v.banks)),
                compatible_east=int(any(match(v.banks[1]) for v in p.views)),
                compatible_at_attempt=int(match(east)) if p.attempt else "-",
                exact_east_bank_kinds="".join(sorted({v.banks[1][0] for v in p.views if v.banks[1][1]==READER})) or "-",
                reads=p.hits, births=len(p.children), death=p.death or "-")


PAIR = """width seed tick grandchild_site mother_site mother_born mother_hex mother_first_tick
mother_first_kind mother_first_site mother_first_hex mother_assay mother_result child_site child_born
child_hex child_first_tick child_first_kind child_first_site child_first_hex child_assay child_result
grandchild_hex confirmed""".split()
PRODUCT = """width seed mother_site mother_born mother_hex child_site child_born child_hex inputs_hex
external_writes child_reads child_births qualified_child_births""".split()


def outcomes(width, seed, world, assays):
    readers, products, pairs = [], [], []
    for cpu, p in world.people.items():
        if p.genome == READER:
            readers.append(dict(width=width, seed=seed, **reader_window(cpu, p, assays)))
        for child in p.exposed_births():
            q = world.people[child]
            child_births = q.exposed_births()
            products.append(dict(zip(PRODUCT, (width,seed,*cpu,p.genome,*child,q.genome,q.inputs,
                world.external_writes.get(child, "-"),q.hits,len(q.children),len(child_births)), strict=True)))
            for kid in child_births:
                pk, po = own_assay(width, assays, cpu, p)
                qk, qo = own_assay(width, assays, child, q)
                confirmed = int(po == qo == "dependent")
                pairs.append(dict(zip(PAIR, (width,seed,kid[1],kid[0],*cpu,p.genome,p.first.tick,
                    p.first.kind,p.first.site,p.first.genome,pk,po,*child,q.genome,q.first.tick,
                    q.first.kind,q.first.site,q.first.genome,qk,qo,world.people[kid].genome,confirmed), strict=True)))
    return readers, products, pairs


def paired_contrasts(runs):
    by_key = {(r["width"],r["seed"]):r for r in runs}
    results = []
    for width in (4,16):
        for endpoint in ("compatible_at_attempt", "confirmed_pairs"):
            outcomes = [(by_key[(8,s)][endpoint] > 0, by_key[(width,s)][endpoint] > 0) for s in SEEDS]
            square_only = outcomes.count((True,False))
            rectangle_only = outcomes.count((False,True))
            results.append(dict(width=width, endpoint=endpoint, paired_seeds=len(outcomes),
                neither=outcomes.count((False,False)), both=outcomes.count((True,True)),
                square_only=square_only, rectangle_only=rectangle_only,
                rectangle_minus_square_seeds=rectangle_only-square_only))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--field", type=Path, default=BUILD/"geometry/field")
    parser.add_argument("--observe", type=Path, default=BUILD/"observe")
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    assays = Assays(args.observe.resolve())
    assays.check_controls()
    reference = {int(r["seed"]):r for r in table(PREVIOUS/"read-seeds.tsv")}
    checks = []
    for seed in range(65,69):
        world = replay(args.field.resolve(),8,seed,args.reverse)
        stats = census(world.people,512)
        check_reference(stats,world.hashes[512],reference[seed])
        checks.append(dict(width=8,seed=seed,tick=512,**stats,state_fnv64=world.hashes[512]))

    seeds, checkpoints, readers, products, candidates = [], [], [], [], []
    for width in WIDTHS:
        for seed in SEEDS:
            world = replay(args.field.resolve(),width,seed,args.reverse)
            observations, births, pairs = outcomes(width,seed,world,assays)
            readers.extend(observations)
            products.extend(births)
            candidates.extend(pairs)
            for t,digest in world.hashes.items():
                checkpoints.append(dict(width=width,seed=seed,tick=t,**census(world.people,t),state_fnv64=digest))
            seeds.append(dict(width=width,seed=seed,readers=len(observations),
                attempted=sum(r["attempt"] != "-" for r in observations),
                other_live_exact=sum(r["other_live_exact"] for r in observations),
                compatible_any=sum(r["compatible_any"] for r in observations),
                compatible_east=sum(r["compatible_east"] for r in observations),
                compatible_at_attempt=sum(r["compatible_at_attempt"] == 1 for r in observations),
                exposed_births=len(births),field_pairs=len(pairs),
                live_pairs=sum(r["mother_first_kind"] == r["child_first_kind"] == "o" for r in pairs),
                confirmed_pairs=sum(r["confirmed"] for r in pairs)))
    args.out.mkdir(exist_ok=True,parents=True)
    for name,data,schema in [("prefix-checks",checks,None),("checkpoints",checkpoints,None),("seeds",seeds,None),
            ("readers",readers,None),("products",products,PRODUCT),("pairs",candidates,PAIR),
            ("contrasts",paired_contrasts(seeds),None),("generations",assays.records,None)]:
        rows_to_file(args.out/(name+".tsv"), data, schema)


if __name__ == "__main__":
    main()
