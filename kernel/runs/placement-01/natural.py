"""Screen the fixed prospective seed range and check individual lifetimes in matched fields."""
import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lineage-01"))
from audit import Assays, END, LINK, PAIR, audit, neighbor_direction, replay, require, rows_to_file, table

CHAIN = "seed mother_site mother_born daughter_site daughter_born grandchild_site grandchild_born depth confirmed".split()
FOLLOW = ("seed mother_site mother_born daughter_site daughter_born grandchild_site grandchild_born "
          "inputs_hex product_hex copies_mother_alive copies_from_live_mother source_writes").split()


def identity(row, role):
    return int(row[role + "_site"]), int(row[role + "_born"])


def inspect_links(seed, world, links, expected, chains, follow):
    by_child = {identity(r, "child"): r for r in links}
    for link in links:
        parent, child = identity(link, "mother"), identity(link, "child")
        link["placement"] = "NESW"[neighbor_direction(16, parent[0], child[0])]
        prior = by_child.get(parent)
        if prior:
            chains.append(dict(zip(CHAIN[:-1], (seed, *identity(prior, "mother"), *parent, *child, link["depth"]), strict=True)))
        for cpu in (parent, child):
            p = world.people[cpu]
            expected[(seed, *cpu)] = (p.death, [(kid[1], kid[0], world.people[kid].inputs, world.people[kid].genome)
                                               for kid in p.children])
        for kid in world.people[child].children:
            product = world.people[kid]
            writes = world.external_writes[kid]
            hits = [item.split("/") for item in writes.split(",")]
            require(len(hits) == 5, "reader birth with incomplete external writes")
            death = world.people[parent].death
            alive = sum(death is None or int(h[1]) <= death for h in hits)
            maternal = sum(h[4] == "o" and (int(h[2]), int(h[5])) == parent for h in hits)
            follow.append(dict(zip(FOLLOW, (seed,*parent,*child,*kid,product.inputs,product.genome,
                                            alive,maternal,writes), strict=True)))


def permission_forks(binary, out, expected, chains, reverse):
    data = "".join(f"16 {seed} {site} {born}\n" for seed, site, born in sorted(expected))
    scores, products, windows = [out / ("lifetime-" + name + ".tsv") for name in ("scores", "products", "openings")]
    subprocess.run([binary, scores, products, windows] + (["--reverse"] if reverse else []),
                   input=data, text=True, check=True)
    index = defaultdict(dict)
    for r in table(scores):
        key = tuple(int(r[k]) for k in ("seed","site","born"))
        index[key][r["branch"]] = r
    observed = defaultdict(list)
    for r in table(products):
        if r["branch"] == "ordinary" and int(r["tick"]) <= END:
            key = tuple(int(r[k]) for k in ("seed","site","born"))
            observed[key].append((int(r["tick"]),int(r["child_site"]),r["inputs_hex"],r["product_hex"]))
    for key, (death, births) in expected.items():
        arms = index[key]
        require(set(arms) == {"ordinary", "deny_all", "deny_own"} and
                len({a["start_fnv64"] for a in arms.values()}) == 1, "mismatched birth states")
        require(observed[key] == births and int(arms["ordinary"]["death"]) == (death or key[2]+81),
                "ordinary lifetime disagrees with untreated field")
    positives = defaultdict(int)
    for chain in chains:
        tested = [index[(chain["seed"], *identity(chain, role))] for role in ("mother","daughter")]
        chain["confirmed"] = int(all(int(arms["ordinary"]["births"]) > 0 and
                                     int(arms["deny_all"]["blocked_attempts"]) > 0 and
                                     arms["deny_all"]["births"] == "0" for arms in tested))
        positives[chain["seed"]] += chain["confirmed"]
    return positives


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference", type=Path)
    p.add_argument("field_binaries", type=Path)
    p.add_argument("lifetime", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--reverse", action="store_true")
    args = p.parse_args()
    fields = table(args.reference)
    require([int(r["seed"]) for r in fields] == list(range(3137,11329)), "wrong prospective seed budget")
    args.out.mkdir(parents=True,exist_ok=True)
    field_bin = args.field_binaries.resolve()
    assays = Assays(field_bin / "observe")
    assays.check_controls()
    scores, full_links, full_pairs, follow, chains, expected = [], [], [], [], [], {}
    for r in fields:
        seed = int(r["seed"])
        world = replay(field_bin / "field",16,seed,args.reverse)
        score, links, pairs = audit(dict(r,cohort="prospective"),world,assays)
        inspect_links(seed,world,links,expected,chains,follow)
        score.update(readers=int(r["readers"]), raw_chains=sum(x["depth"] >= 2 for x in links),
                     confirmed_chains=0)
        scores.append(score)
        full_links.extend(links)
        full_pairs.extend(pairs)
        if (seed-3136) % 1024 == 0:
            print(f"{seed-3136}/8192 fields checked",flush=True)
    positives = permission_forks(args.lifetime.resolve(),args.out,expected,chains,args.reverse)
    for r in scores:
        r["confirmed_chains"] = positives[r["seed"]]
    rows_to_file(args.out / "seeds.tsv",scores)
    rows_to_file(args.out / "links.tsv",full_links,LINK + ["placement"])
    rows_to_file(args.out / "pairs.tsv",full_pairs,PAIR)
    rows_to_file(args.out / "chains.tsv",chains,CHAIN)
    rows_to_file(args.out / "descendants.tsv",follow,FOLLOW)
    rows_to_file(args.out / "generations.tsv",assays.records)


if __name__ == "__main__":
    main()
