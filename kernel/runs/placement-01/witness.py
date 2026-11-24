"""Reconstruct clonal reader families containing a confirmed natural two-link pedigree."""
import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lineage-01"))
from audit import END, READER, donor_for_intact_copy, replay, require, rows_to_file, table

FAMILY = "seed root_site root_born members max_clonal_depth max_live_depth final_living last_birth extinction".split()
MEMBER = ("seed root_site root_born site born parent_site parent_born parent_hex inputs_hex genome_hex "
          "clonal_depth live_depth death children qualifying_live_supplier qualifying_supplier_born source_writes").split()


def family_witness(seed, world, selected):
    roots, depths, live_depths = {}, {}, {}
    for cpu, p in world.people.items():
        if p.genome != READER:
            continue
        if p.parent in roots:
            roots[cpu] = roots[p.parent]
            depths[cpu] = depths[p.parent] + 1
            link = donor_for_intact_copy(world,p.parent,cpu)
            live_depths[cpu] = 1 + live_depths[p.parent] if link else 0
        else:
            roots[cpu], depths[cpu], live_depths[cpu] = cpu, 0, 0
    families, members = [], []
    for root in sorted({roots[c] for c in selected}):
        identities = [cpu for cpu, r in roots.items() if r == root]
        people = [world.people[cpu] for cpu in identities]
        living = sum(p.death is None for p in people)
        families.append(dict(zip(FAMILY,(seed,*root,len(people),max(depths[c] for c in identities),
            max(live_depths[c] for c in identities),living,max(c[1] for c in identities),
            "-" if living else max(p.death for p in people)),strict=True)))
        for cpu, p in zip(identities,people,strict=True):
            link = donor_for_intact_copy(world,p.parent,cpu) if live_depths[cpu] else None
            members.append(dict(zip(MEMBER,(seed,*root,*cpu,*p.parent,world.people[p.parent].genome,
                p.inputs,p.genome,depths[cpu],live_depths[cpu],p.death or "-",len(p.children),
                *(link or ("-","-")),world.external_writes.get(cpu,"-")),strict=True)))
    return families, members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("field", type=Path)
    parser.add_argument("--reverse",action="store_true")
    args=parser.parse_args()
    out=args.out
    seeds=table(out/"seeds.tsv")
    links=table(out/"links.tsv")
    chains=table(out/"chains.tsv")
    selected=[r for r in chains if r["confirmed"]=="1"]
    families, members = [], []
    for seed in sorted({r["seed"] for r in selected},key=int):
        world=replay(args.field.resolve(),16,int(seed),args.reverse)
        require(world.hashes[END]==next(r["state_fnv64"] for r in seeds if r["seed"]==seed),
                "witness field differs")
        cases=[(int(r["mother_site"]),int(r["mother_born"])) for r in selected if r["seed"]==seed]
        f, m=family_witness(seed,world,cases)
        families.extend(f)
        members.extend(m)
    rows_to_file(out/"families.tsv",families,FAMILY)
    rows_to_file(out/"members.tsv",members,MEMBER)
    status=Counter(r["status"] for r in seeds)
    summary=dict(seeds=len(seeds), reproducing=status["reproducing"], stagnant=status["stagnant"], extinct=status["extinct"])
    for key in ("births","readers","reader_mother_births","live_intact_births","raw_chains",
                "confirmed_chains","candidate_pairs","live_first_pairs","confirmed_pairs"):
        summary[key]=sum(int(r[key]) for r in seeds)
        summary[key+"_seeds"]=sum(int(r[key])>0 for r in seeds)
    summary["censored_link_daughters"]=sum(r["child_death"]=="-" for r in links)
    rows_to_file(out/"summary.tsv",[summary])
    # Each row in links is one daughter; count children for which she supplied the parent CPU.
    origins={(r["seed"],r["child_site"],r["child_born"]): r for r in links}
    continuation=Counter()
    for r in links:
        parent=(r["seed"],r["mother_site"],r["mother_born"])
        if parent in origins:
            continuation[parent]+=1
    placements=[]
    for direction in "WNSE":
        daughters=[key for key, r in origins.items() if r["placement"]==direction]
        placements.append(dict(placement=direction,daughters=len(daughters),
                               seeds=len({k[0] for k in daughters}),
                               daughters_continuing=sum(continuation[k]>0 for k in daughters),
                               live_grandchildren=sum(continuation[k] for k in daughters)))
    rows_to_file(out/"placements.tsv",placements)


if __name__ == "__main__":
    main()
