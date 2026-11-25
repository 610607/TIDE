"""Score uninterrupted confirmed pedigrees, aligned material paths and regenerated programs."""
import argparse
import csv
import gzip
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path

from run import CONTROL, FIRST, HERE, SPLIT, STOP, check, read


def save(path, columns, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decode(row):
    text = ("genome", "inputs", "checkpoint", "writes")
    p = {k: v if k in text else int(v) for k, v in row.items()}
    inp, out = bytes.fromhex(p["inputs"]), bytes.fromhex(p["genome"])
    check(len(inp) == len(out) == 6 and sum(a != b for a,b in zip(inp,out)) == p["substitutions"], "product bytes")
    trace = [r.split("/") for r in p["writes"].split(",")]
    check(len(trace) == 6, "six writes")
    last = -1
    sources = []
    for i, (tick, site, born, kind, offset, person) in enumerate(trace):
        tick, site, born, offset, person = map(int, (tick,site,born,offset,person))
        check(last < tick < p["born"] and 0 <= site < 64 and 0 <= offset < 6, "write order")
        if kind in ("s","o"):
            check(born < tick <= born+81 and 0 <= person < p["id"] and (kind=="s") == (person==p["actor"]), "living source")
        else:
            check(kind in ("r","f") and born == person == -1, "inactive source")
        sources.append(person if offset == i else -1)
        last = tick
    donor = sources[0] if len(set(sources)) == 1 else -1
    check(p["actor"] < p["id"] and p["donor"] == donor and sum(r[3] != "s" for r in trace) == p["external"], "birth sources")
    tested = p["checkpoint"] != "-"
    check(tested == (p["denied_births"] >= 0) and p["ordinary_births"] >= p["exposed_births"], "assay coverage")
    check(p["confirmed"] == (tested and p["ordinary_births"] > 0 and p["denied_births"] == 0 and p["blocked"] > 0),
          "assay decision")
    return p


def anchor(world, nodes):
    pilot = HERE.parent / "six-origin-01" / "pilot"
    ref, = [r for r in read(pilot/"reference.tsv") if int(r["seed"]) == CONTROL]
    for a,b in (("state_fnv64","hash_end"), ("births","births"), ("deaths","deaths"), ("living","living"),
                ("final80_births","last80_births"), ("status","status")):
        check(world[b] == ref[a], "historical field mismatch")
    ids = {(p["site"], p["born"]): p for p in nodes.values()}
    for r in read(pilot/"focals.tsv"):
        if int(r["seed"]) != CONTROL:
            continue
        p = ids[int(r["site"]),int(r["born"])]
        for a,b in (("genome_hex","genome"), ("start_fnv64","checkpoint"), ("ordinary_births","ordinary_births"),
                    ("denied_births","denied_births"), ("blocked_attempts","blocked"), ("dependent","confirmed")):
            check(str(p[b]) == r[a], "historical focal mismatch")
    pairs = 0
    for r in read(pilot/"edges.tsv"):
        if int(r["seed"]) == CONTROL and r["confirmed_edge"] == "1":
            mother=ids[int(r["mother_site"]),int(r["mother_born"])]
            child=ids[int(r["daughter_site"]),int(r["daughter_born"])]
            check(mother["confirmed"] and child["confirmed"] and child["actor"] == mother["id"], "historical edge")
            pairs += 1
    check(pairs > 0, "missing positive control")


ROOT_COLUMNS = ("seed","root","born","max_depth","max_span","max_genomes","changed","post","primary","strict",
                "three_programs","material_change_on_path","post_nonroot_genome","witness")
TERMINALS = ("no_successor","no_birth","no_exposed_birth","reproduced_denied","unconfirmed_other","beyond_cutoff")
MATERIAL = ("material_reached","material_depth","material_span","material_bridge","bridge_passive","bridge_changed_post")


def trace_field(world, nodes, returns, roots_out, material_out):
    seed, horizon = int(world["seed"]), int(world["horizon"])
    positive = {i for i,p in nodes.items() if p["confirmed"]}
    outgoing = defaultdict(list)
    material = defaultdict(list)
    direct_births, exposed_births = Counter(), Counter()
    for i,p in nodes.items():
        direct_births[p["actor"]] += 1
        exposed_births[p["actor"]] += p["external"] > 0
        if p["donor"] in nodes:
            donor = nodes[p["donor"]]
            check(donor["genome"] == p["inputs"], "aligned donor inputs")
            if p["born"] <= horizon:
                material[p["donor"]].append(i)
        if p["born"] <= horizon:
            check((p["checkpoint"] != "-") == (p["exposed_births"] > 0), "missing completed lifetime")
        for parent in {p["actor"], p["donor"]} & positive:
            check(nodes[parent]["born"] < p["born"] <= nodes[parent]["born"]+162, "noncausal edge")
            outgoing[parent].append(i)
    edges = Counter()
    for i in positive:
        p=nodes[i]
        check(p["ordinary_births"] == direct_births[i] and p["exposed_births"] == exposed_births[i],
              "confirmed individual's offspring ledger incomplete")
        a,d=p["actor"] in positive,p["donor"] in positive
        edges["actor_edges"]+=a
        edges["donor_edges"]+=d
        edges["shared_edges"]+=a and d and p["actor"]==p["donor"]
    roots = sorted(i for i in positive if not ({nodes[i]["actor"], nodes[i]["donor"]} & positive))
    seen=set()
    records=[]
    for root in roots:
        r=dict(seed=seed,root=root,born=nodes[root]["born"],max_depth=1,max_span=0,max_genomes=1,
               changed=0,post=0,primary=0,strict=0,three_programs=0,material_change_on_path=0,post_nonroot_genome=0,witness="-")
        stack=[((root,), False)]
        while stack:
            path, mut = stack.pop()
            i=path[-1]; seen.add(i)
            seqs={nodes[j]["genome"] for j in path}
            span=nodes[i]["born"]-r["born"]
            changed=len(seqs)>1
            post=span>81
            r["max_depth"]=max(r["max_depth"],len(path))
            r["max_span"]=max(r["max_span"],span)
            r["max_genomes"]=max(r["max_genomes"],len(seqs))
            r["changed"]|=int(changed); r["post"]|=int(post)
            if changed and post:
                r["primary"]=1
                r["strict"]=int(r["born"]<=horizon-162)
                r["three_programs"]|=int(len(seqs)>=3)
                r["material_change_on_path"]|=int(mut)
                r["post_nonroot_genome"]|=int(nodes[i]["genome"]!=nodes[root]["genome"])
                if r["witness"]=="-" or len(path)>len(r["witness"].split(",")):
                    r["witness"]=",".join(map(str,path))
            for child in outgoing[i]:
                if child in positive:
                    q=nodes[child]
                    stack.append((path+(child,),mut or (q["donor"]==i and q["substitutions"]>0)))
        records.append(r)
    check(seen==positive,"missing confirmed component")
    roots_out.extend(records)
    ends=Counter({k:0 for k in TERMINALS})
    leaves=0
    for i in positive:
        children=outgoing[i]
        if any(c in positive for c in children):
            continue
        leaves+=1
        ends["no_successor"]+=not children
        for c in children:
            q=nodes[c]
            if q["born"]>horizon: fate="beyond_cutoff"
            elif not q["ordinary_births"]: fate="no_birth"
            elif not q["exposed_births"]: fate="no_exposed_birth"
            elif q["denied_births"]>0: fate="reproduced_denied"
            else: fate="unconfirmed_other"
            ends[fate]+=1
    m=Counter({k:0 for k in MATERIAL})
    for origin in sorted(positive):
        stack=[(origin,0,False,False,False)]
        while stack:
            i,depth,gap,passive,changed=stack.pop()
            for c in material[i]:
                q=nodes[c]
                difference=changed or q["substitutions"]>0
                span=q["born"]-nodes[origin]["born"]
                m["material_depth"]=max(m["material_depth"],depth+1)
                m["material_span"]=max(m["material_span"],span)
                if c in positive:
                    m["material_reached"]+=1; m["material_bridge"]+=gap
                    m["bridge_passive"]+=gap and passive
                    m["bridge_changed_post"]+=gap and difference and span>81
                    material_out.append(dict(seed=seed,origin=origin,descendant=c,transfers=depth+1,span=span,
                                             gap=int(gap),passive=int(passive),changed=int(difference)))
                stack.append((c,depth+1,gap or c not in positive,passive or not q["ordinary_births"],difference))
    for r in returns:
        p=nodes[int(r["id"])]
        check(p["confirmed"] and p["born_absent"] and p["substitutions"] and r["genome"]==p["genome"]
              and int(r["prior_confirmed"])>0, "substitution return")
    return dict(seed=seed,horizon=horizon,tested=sum(p["denied_births"]>=0 for p in nodes.values()),
                confirmed=len(positive),roots=len(roots),**{k:edges[k] for k in ("actor_edges","donor_edges","shared_edges")},
                **{k:max((r[k] for r in records),default=0) for k in ("max_depth","max_span","max_genomes")},
                **{k:sum(r[k] for r in records) for k in ("changed","post","primary","strict","three_programs","material_change_on_path","post_nonroot_genome")},
                leaves=leaves,**ends,**m,returns=len(returns),outside=sum(r["ancestor_present"]=="0" for r in returns))


def main(directory):
    worlds=read(directory/"world.tsv")
    check([int(w["seed"]) for w in worlds]==[CONTROL,*range(FIRST,STOP)],"missing fields")
    returns=defaultdict(list)
    for r in read(directory/"returns.tsv"):
        returns[int(r["seed"])].append(r)
    roots, materials, endpoints = [], [], []
    with gzip.open(directory/"nodes.tsv.gz","rt") as stream:
        groups=groupby(csv.DictReader(stream,delimiter="\t"),lambda r:int(r["seed"]))
        group=next(groups,None)
        for w in worlds:
            seed=int(w["seed"])
            check(int(w["horizon"])==(2048 if seed==CONTROL else 8192) and
                  1+int(w["births"])-int(w["deaths"])==int(w["living"]),"field ledger")
            nodes={}
            if group and group[0]==seed:
                for row in group[1]:
                    p=decode(row); check(p["id"] not in nodes,"duplicate node"); nodes[p["id"]]=p
                group=next(groups,None)
            if seed==CONTROL: anchor(w,nodes)
            endpoints.append(trace_field(w,nodes,returns.pop(seed,[]),roots,materials))
        check(not group and not returns,"unknown seed")
    save(directory/"roots.tsv",ROOT_COLUMNS,roots)
    save(directory/"material-pairs.tsv",("seed","origin","descendant","transfers","span","gap","passive","changed"),materials)
    save(directory/"endpoints.tsv",endpoints[0],endpoints)
    summary=[]
    for label,seeds in (("block1",range(FIRST,SPLIT)),("block2",range(SPLIT,STOP)),("pooled",range(FIRST,STOP))):
        subset=[e for e in endpoints if e["seed"] in seeds]
        data=dict(cohort=label,worlds=len(subset))
        for k in ("tested","confirmed","roots","primary","strict","three_programs","returns","outside",*TERMINALS):
            data[k]=sum(r[k] for r in subset)
        for k in ("confirmed","changed","post","primary","strict","three_programs","material_change_on_path","post_nonroot_genome",
                  "material_reached","material_bridge","bridge_passive","bridge_changed_post","returns","outside"):
            data[k+"_worlds"]=sum(r[k]>0 for r in subset)
        for k in ("max_depth","max_span","max_genomes","material_depth","material_span"):
            data[k]=max(r[k] for r in subset)
        for status in ("reproducing","stagnant","extinct"):
            data[status]=sum(int(w["seed"]) in seeds and w["status"]==status for w in worlds)
        summary.append(data)
    save(directory/"summary.tsv",summary[0],summary)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    main(p.parse_args().directory)
