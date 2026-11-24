"""Reconstruct every externally sourced natural birth and test both reproducing CPUs."""
import argparse
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "geometry-01"))
from geometry import END, ROOT, census, check_reference, replay, require, rows_to_file, table

ANCESTOR = b"R..CLD".hex()
EDGE = ("seed mother_site mother_born daughter_site daughter_born mother_hex inputs_hex daughter_hex "
        "changed template_differs copy_substitutions external_bytes source_kinds single_live_intact "
        "daughter_living_at_cutoff daughter_births daughter_external_births mother_dependent "
        "daughter_dependent confirmed_edge exact_grandchildren live_pair_grandchildren source_writes").split()
TRIPLE = ("seed mother_site mother_born daughter_site daughter_born grandchild_site grandchild_born "
          "mother_hex daughter_hex grandchild_hex changed both_dependent retains_daughter "
          "both_single_live_intact").split()
FOCAL = ("seed site born genome_hex start_fnv64 death exposed_births ordinary_births "
         "denied_births blocked_attempts dependent").split()
METRICS = ("external_births external_mothers dependent_mothers changed_external_daughters "
           "changed_from_dependent changed_from_dependent_with_birth changed_from_dependent_with_external_birth "
           "candidate_edges changed_candidate_edges confirmed_unchanged_edges primary_changed_edges "
           "exact_changed_edges live_pair_changed_edges censored_external_daughters "
           "censored_changed_from_dependent_without_external_birth").split()


def provenance(world, child, writes):
    person = world.people[child]
    records = [v.split("/") for v in writes.split(",")]
    kinds = ["s"] * 6
    donors = set()
    aligned = True
    for write, time, site, offset, kind, born, _ in records:
        i, t, s, j, b = map(int, (write, time, site, offset, born))
        require(kinds[i] == "s" and s != person.parent[0] and kind in ("o", "r", "f"), "invalid external copy")
        kinds[i] = kind
        aligned &= i == j
        if kind == "o":
            donor = world.people[s,b]
            require(b < t <= (donor.death or END) and donor.genome[2*j:2*j+2] == person.inputs[2*i:2*i+2],
                    "living donor does not match opening byte")
            donors.add((s,b))
    intact = kinds == ["o"]*6 and aligned and len(donors) == 1 and person.inputs == person.genome
    return len(records), "".join(kinds), int(intact)


def forks(seed, world, children, binary, tmp, reverse):
    targets = "".join(f"16 {seed} {s} {b} {world.people[s,b].genome}\n" for s,b in sorted(children))
    if not targets:
        return {}, []
    scores, products, windows = (tmp / name for name in ("scores", "products", "windows"))
    subprocess.run([binary, scores, products, windows] + (["--reverse"] if reverse else []),
                   input=targets, text=True, check=True)
    arms, births = defaultdict(dict), defaultdict(list)
    for r in table(scores):
        key = int(r["site"]), int(r["born"])
        require(r["branch"] not in arms[key], "duplicate permission branch")
        arms[key][r["branch"]] = r
    for r in table(products):
        key = int(r["site"]), int(r["born"]), r["branch"]
        births[key].append((int(r["child_site"]), int(r["tick"]), r["inputs_hex"], r["product_hex"]))
    require(set(arms) == set(children), "incomplete focal coverage")
    dependent, rows = {}, []
    for cpu, modes in sorted(arms.items()):
        p = world.people[cpu]
        require(set(modes) == {"ordinary", "deny_all", "deny_own"} and
                len({r["start_fnv64"] for r in modes.values()}) == 1, "unmatched checkpoints")
        for mode, r in modes.items():
            require(int(r["death"]) == (p.death or cpu[1]+81) and
                    len(births[cpu+(mode,)]) == int(r["births"]), "incomplete focal lifetime")
        ordinary, denied = modes["ordinary"], modes["deny_all"]
        expected = [(*kid, world.people[kid].inputs, world.people[kid].genome) for kid in p.children]
        require(expected == [b for b in births[cpu+("ordinary",)] if b[1] <= END], "ordinary products differ")
        require(int(ordinary["births"]) > 0 and int(ordinary["reads"]) > 0 and denied["reads"] == "0",
                "unexpected focal exposure")
        dependent[cpu] = int(denied["births"] == "0")
        require(not dependent[cpu] or int(denied["blocked_attempts"]) > 0, "missing blocked copy")
        rows.append(dict(zip(FOCAL, (seed,*cpu,p.genome,ordinary["start_fnv64"],ordinary["death"],
                         len(children[cpu]),ordinary["births"],denied["births"],denied["blocked_attempts"],
                         dependent[cpu]), strict=True)))
    return dependent, rows


def analyze(seed, world, binary, tmp, reverse):
    by_parent, sources = defaultdict(list), {}
    for kid, writes in world.external_writes.items():
        by_parent[world.people[kid].parent].append(kid)
        sources[kid] = provenance(world, kid, writes)
    dep, focal = forks(seed, world, by_parent, binary, tmp, reverse)
    counts = Counter(external_mothers=len(dep), dependent_mothers=sum(dep.values()))
    edges, triples = [], []
    for daughter, writes in world.external_writes.items():
        d = world.people[daughter]
        mother = d.parent
        m = world.people[mother]
        ext, kinds, live = sources[daughter]
        changed = int(d.genome != m.genome)
        daughter_births = by_parent.get(daughter, [])
        both = bool(dep[mother] and dep.get(daughter, 0))
        exact = paired_live = 0
        for grandchild in daughter_births:
            g = world.people[grandchild]
            same = g.genome == d.genome
            serial_live = bool(live and sources[grandchild][2])
            exact += both and same
            paired_live += both and serial_live
            triples.append(dict(zip(TRIPLE, (seed,*mother,*daughter,*grandchild,m.genome,d.genome,g.genome,
                                             changed,int(both),int(same),int(serial_live)), strict=True)))
        differences = sum(a != b for a,b in zip(bytes.fromhex(d.genome), bytes.fromhex(d.inputs), strict=True))
        edges.append(dict(zip(EDGE, (seed,*mother,*daughter,m.genome,d.inputs,d.genome,changed,
                    int(d.inputs != m.genome),differences,ext,kinds,live,int(d.death is None),
                    len(d.children),len(daughter_births),dep[mother],dep.get(daughter,"-"),
                    int(both),exact,paired_live,writes), strict=True)))
        counts["external_births"] += 1
        counts["changed_external_daughters"] += changed
        counts["changed_from_dependent"] += changed and dep[mother]
        counts["changed_from_dependent_with_birth"] += bool(changed and dep[mother] and d.children)
        counts["changed_from_dependent_with_external_birth"] += bool(changed and dep[mother] and daughter_births)
        counts["candidate_edges"] += bool(daughter_births)
        counts["changed_candidate_edges"] += bool(changed and daughter_births)
        counts["confirmed_unchanged_edges"] += both and not changed
        counts["primary_changed_edges"] += both and changed
        counts["exact_changed_edges"] += bool(changed and exact)
        counts["live_pair_changed_edges"] += bool(changed and paired_live)
        counts["censored_external_daughters"] += d.death is None
        counts["censored_changed_from_dependent_without_external_birth"] += bool(
            changed and dep[mother] and not daughter_births and d.death is None)
    return {k: counts[k] for k in METRICS}, focal, edges, triples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    bin_dir = args.build.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out/"reference.tsv").open("w") as reference:
        subprocess.run([bin_dir/"reference", args.out/"controls.tsv"] + (["--reverse"] if args.reverse else []),
                       stdout=reference, check=True)
    references = table(args.out/"reference.tsv")
    require([int(r["seed"]) for r in references] == list(range(19521,20545)), "cohort differs")
    seeds, focals, edges, triples = [], [], [], []
    with TemporaryDirectory() as temp:
        for r in references:
            seed = int(r["seed"])
            w = replay(bin_dir/"field", 16, seed, args.reverse)
            # The shared event format records only offspring genomes. Supply this study's root metadata.
            w.people[ROOT].genome = ANCESTOR
            check_reference(census(w.people, END), w.hashes[END], r)
            require(all(len(p.genome) == 12 for p in w.people.values()), "program length changed")
            metrics, f, e, t = analyze(seed, w, bin_dir/"lifetime", Path(temp), args.reverse)
            seeds.append(dict(r, **metrics))
            focals.extend(f)
            edges.extend(e)
            triples.extend(t)
            if len(seeds) % 256 == 0:
                print(f"{len(seeds)}/1024 worlds checked", flush=True)
    rows_to_file(args.out/"seeds.tsv", seeds)
    rows_to_file(args.out/"focals.tsv", focals, FOCAL)
    rows_to_file(args.out/"edges.tsv", edges, EDGE)
    rows_to_file(args.out/"grandchildren.tsv", triples, TRIPLE)
    summary = []
    for k in ("births", *METRICS):
        summary.append(dict(metric=k, events=sum(int(r[k]) for r in seeds),
                            worlds=sum(int(r[k]) > 0 for r in seeds)))
    rows_to_file(args.out/"summary.tsv", summary)


if __name__ == "__main__":
    main()
