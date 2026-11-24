"""Replay every enrolled maternal descendant and join focal lifetime forks by birth identity."""
import argparse
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "placement-01"))
from natural import END, identity, replay, require, rows_to_file, table


def pedigree(world, root):
    members = {}
    for cpu, person in world.people.items():
        if cpu == root:
            members[cpu] = 0
        elif person.parent in members:
            members[cpu] = members[person.parent] + 1
    require(root in members, "missing pedigree founder")
    return members


def classify(ordinary, denied):
    if int(ordinary["births"]) == 0:
        return "no_ordinary_birth"
    if int(denied["births"]) > 0:
        return "reproduces_under_denial"
    require(int(denied["blocked_attempts"]) > 0, "lost reproduction without a blocked copy")
    return "dependent"


def score_family(out, root, seed, world, focal_live, binary, reverse):
    members = pedigree(world, root)
    out.mkdir(parents=True, exist_ok=True)
    inputs = []
    for site, born in members:
        genome = world.people[site, born].genome
        flag = " live" if (site, born) in focal_live else ""
        inputs.append(f"16 {seed} {site} {born} {genome}{flag}\n")
    paths = [out / name for name in ("scores.tsv", "products.tsv", "openings.tsv")]
    subprocess.run([binary, *paths] + (["--reverse"] if reverse else []),
                   input="".join(inputs), text=True, check=True)
    scores = defaultdict(dict)
    for row in table(paths[0]):
        key = int(row["site"]), int(row["born"])
        require(row["branch"] not in scores[key], "duplicate focal arm")
        scores[key][row["branch"]] = row
    products = defaultdict(list)
    for row in table(paths[1]):
        cpu = int(row["site"]), int(row["born"])
        products[cpu, row["branch"]].append(row)
    require(set(scores) == set(members), "incomplete case list")
    runs, classes, rows = {}, {}, []
    for cpu, depth in members.items():
        p = world.people[cpu]
        arms = scores[cpu]
        modes = {"ordinary", "deny_all", "deny_own"}
        if cpu in focal_live:
            modes.add("deny_live")
        require(set(arms) == modes and len({arm["start_fnv64"] for arm in arms.values()}) == 1,
                "birth-state fork mismatch")
        require(all(int(arm["death"]) == (p.death or cpu[1]+81) for arm in arms.values()),
                "focal lifetime mismatch")
        for mode, arm in arms.items():
            require(len(products[cpu, mode]) == int(arm["births"]), "incomplete outcome ledger")
        observed = [(int(r["child_site"]), int(r["tick"]), r["inputs_hex"], r["product_hex"])
                    for r in products[cpu, "ordinary"] if int(r["tick"]) <= END]
        expected = [(*child, world.people[child].inputs, world.people[child].genome) for child in p.children]
        require(observed == expected, "ordinary offspring differ from field")
        ordinary, denied = arms["ordinary"], arms["deny_all"]
        state = classify(ordinary, denied)
        classes[cpu] = state
        runs[cpu] = runs.get(p.parent, 0) + 1 if state == "dependent" else 0
        rows.append(dict(seed=seed, root_site=root[0], root_born=root[1], site=cpu[0], born=cpu[1],
                         parent_site=p.parent[0], parent_born=p.parent[1], genome_hex=p.genome,
                         parent_hex=world.people[p.parent].genome, depth=depth, death=ordinary["death"],
                         field_children=len(p.children), ordinary_births=ordinary["births"],
                         denied_births=denied["births"], blocked_attempts=denied["blocked_attempts"],
                         start_fnv64=ordinary["start_fnv64"], classification=state,
                         parent_class=classes.get(p.parent, "outside"), dependent_run=runs[cpu]))
    counts = Counter(classes.values())
    longest = max(runs.values())
    summary = dict(seed=seed, root_site=root[0], root_born=root[1], members=len(members),
                   genomes=len({r["genome_hex"] for r in rows}), max_depth=max(members.values()),
                   living_at_cutoff=sum(world.people[c].death is None for c in members),
                   dependent=counts["dependent"], reproduces_under_denial=counts["reproduces_under_denial"],
                   no_ordinary_birth=counts["no_ordinary_birth"], max_dependent_individuals=longest,
                   max_dependent_edges=max(0, longest-1),
                   changed_dependent_edges=sum(r["dependent_run"] >= 2 and r["genome_hex"] != r["parent_hex"]
                                               for r in rows),
                   restarted_dependent_runs=sum(r["dependent_run"] == 1 and r["depth"] > 0 for r in rows),
                   state_fnv64=world.hashes[END])
    return rows, summary, scores, products


def chain_context(seed, world, chains, links, scores, products):
    contexts = []
    for chain in chains:
        mother, daughter, grandchild = [identity(chain, k) for k in ("mother", "daughter", "grandchild")]
        for role, cpu, child in (("mother", mother, daughter), ("daughter", daughter, grandchild)):
            link = links[child]
            donor = identity(link, "donor")
            first_copy = int(link["source_writes"].split(",")[0].split("/")[1])
            donor_death = world.people[donor].death or donor[1]+81
            def matches(mode):
                return any(int(r["tick"]) == child[1] and int(r["child_site"]) == child[0] and
                           r["inputs_hex"] == r["product_hex"] == world.people[child].genome and
                           (int(r["live_donor_site"]), r["live_donor_born"]) == (donor[0], str(donor[1]))
                           for r in products[cpu, mode])
            require(matches("ordinary"), "ordinary qualifying source differs")
            live = scores[cpu]["deny_live"]
            kinds = [r["source_kinds"] for r in products[cpu, "deny_live"]]
            require(all("o" not in k for k in kinds), "living source supplied a denied birth")
            require(not matches("deny_live") and int(live["blocked_attempts"]) > 0,
                    "living-source denial missed the natural transfer")
            contexts.append(dict(seed=seed, chain_mother_born=mother[1], chain_daughter_born=daughter[1],
                                 chain_grandchild_born=grandchild[1], role=role, site=cpu[0], born=cpu[1],
                                 child_site=child[0], child_born=child[1], placement=link["placement"],
                                 donor_site=donor[0], donor_born=donor[1],
                                 daughter_reads_mother=int(role=="daughter" and donor==mother),
                                 first_copy=first_copy, donor_death=donor_death,
                                 donor_steps_to_death=donor_death-first_copy,
                                 ordinary_births=scores[cpu]["ordinary"]["births"],
                                 deny_all_births=scores[cpu]["deny_all"]["births"],
                                 deny_live_births=live["births"], deny_live_blocks=live["blocked_attempts"],
                                 deny_live_product_sources=",".join(kinds) or "-",
                                 deny_live_original_transfer=int(matches("deny_live"))))
    return contexts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("natural", type=Path)
    parser.add_argument("field", type=Path)
    parser.add_argument("lifetime", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    previous = HERE.parent / "placement-01/natural"
    replication = table(args.natural / "families.tsv")
    cases = [(previous, 3562, (17, 425))]
    cases.extend((args.natural, int(r["seed"]), identity(r, "root")) for r in replication)
    members, summaries, contexts = [], [], []
    for source, seed, root in cases:
        world = replay(args.field.resolve(), 16, seed, args.reverse)
        reference = next(r for r in table(source/"seeds.tsv") if int(r["seed"]) == seed)
        require(world.hashes[END] == reference["state_fnv64"], "family field hash differs")
        clonal_family = {(int(r["site"]), int(r["born"])) for r in table(source/"members.tsv")
                         if int(r["seed"]) == seed and identity(r, "root") == root}
        chains = [r for r in table(source/"chains.tsv") if int(r["seed"]) == seed and
                  r["confirmed"] == "1" and identity(r, "mother") in clonal_family]
        links = {identity(r, "child"): r for r in table(source/"links.tsv") if int(r["seed"]) == seed}
        focal_live = {identity(r, role) for r in chains for role in ("mother", "daughter")} if replication else set()
        folder = args.out / f"forks-{seed}-{root[0]}-{root[1]}"
        rows, summary, scores, products = score_family(folder, root, seed, world, focal_live,
                                                       args.lifetime.resolve(), args.reverse)
        members.extend(rows)
        summaries.append(summary)
        if replication:
            contexts.extend(chain_context(seed, world, chains, links, scores, products))
    rows_to_file(args.out / "individuals.tsv", members)
    rows_to_file(args.out / "summary.tsv", summaries)
    if contexts:
        rows_to_file(args.out / "chain-context.tsv", contexts)


if __name__ == "__main__":
    main()
