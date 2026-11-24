"""Check post-death sources and reduce neighbor observations to one row per template."""
import argparse
import csv
import gzip
from collections import Counter
from pathlib import Path
from statistics import median

from run import ARCHIVE, ARMS, check, read

STAGES = ("neighbor", "s_neighbor", "held", "pointed_held", "first_read", "six_aligned", "exact_birth")
DIAGNOSTICS = ("facing", "facing_room", "selected_facing", "won_facing", "blocked_full", "blocked_contest")
AVAILABILITY = ("global_s","distant_only","no_other_s","other_executed_s","neighbor_executed_s",
                "distant_only_executed_s")
PAIR_SUMS = ("neighbor_count","s_neighbor_count","neighbor_ticks","s_neighbor_ticks","facing_ticks",
             "facing_room_ticks","won_ticks","blocked_full_ticks","blocked_contest_ticks","attempts")
FLAGS = STAGES + DIAGNOSTICS + AVAILABILITY


def key(row):
    return row["seed"],row["arm"],row["focal_site"],row["focal_born"]


def save(path,rows):
    with path.open("w") as f:
        out=csv.DictWriter(f,fieldnames=rows[0].keys(),delimiter="\t",lineterminator="\n")
        out.writeheader()
        out.writerows(rows)


def cases(directory):
    records=read(directory/"windows.tsv")
    data={key(r):dict(r, **dict.fromkeys(FLAGS+PAIR_SUMS,0)) for r in records}
    expected={(r["seed"],r["arm"],r["child_site"],r["child_born"]):r
              for r in read(ARCHIVE/"products.tsv") if r["product"]!=r["executor"]}
    check(len(data)==len(records) and data.keys()==expected.keys(),"focal identities")
    for k,c in data.items():
        old=expected[k]
        check((c["maker_site"],c["maker_born"],c["product"],c["complete"])==
              (old["executor_site"],old["executor_born"],old["product"],old["complete"]),"focal provenance")
        check(int(c["open_ticks"])==max(0,min(2048,int(c["focal_born"])+81)-int(c["maker_born"])-81),
              "follow-up length")
    return data


def count_neighbors(directory,data):
    pairs=set()
    with gzip.open(directory/"neighbors.tsv.gz","rt") as f:
        for row in csv.DictReader(f,delimiter="\t"):
            k=key(row)
            c=data[k]
            identity=(*k,row["site"],row["born"])
            check(identity not in pairs and (row["site"],row["born"])!=(c["maker_site"],c["maker_born"]),
                  "duplicate pair or original executor")
            pairs.add(identity)
            first,last,ticks=(int(row[x]) for x in ("first","last","ticks"))
            check(int(c["maker_born"])+81 < first <= last <= min(2048,int(c["focal_born"])+81) and
                  int(row["born"]) < first and last<=int(row["born"])+81 and last-first+1==ticks, "neighbor overlap")
            c["neighbor"]=1; c["neighbor_count"]+=1; c["neighbor_ticks"]+=ticks
            if b"S" not in bytes.fromhex(row["genome"]):
                check(int(row["pointer_held"])==0,"external pointer without source instruction")
                continue
            c["s_neighbor"]=1; c["s_neighbor_count"]+=1; c["s_neighbor_ticks"]+=ticks
            for flag,col in (("facing","facing"),("facing_room","facing_room"),("held","held"),
                             ("pointed_held","pointer_held"),("selected_facing","selected"),
                             ("won_facing","reserve_won"),("blocked_full","blocked_full"),
                             ("blocked_contest","blocked_contest")):
                c[flag] |= int(row[col])>0
            for col,out in (("facing","facing_ticks"),("facing_room","facing_room_ticks"),("reserve_won","won_ticks"),
                            ("blocked_full","blocked_full_ticks"),("blocked_contest","blocked_contest_ticks")):
                c[out]+=int(row[col])
    return pairs


def check_attempts(directory,data,pairs):
    expected=Counter()
    for r in read(ARCHIVE/"links.tsv"):
        if r["after_death"]=="1":
            expected[(*key(r),r["next_executor_site"],r["next_executor_born"],r["next_site"],r["next_born"],
                      r["sequence"],r["read_ticks"],r["read_sites"])]+=1
    observed=Counter()
    for r in read(directory/"attempts.tsv"):
        k=key(r); c=data[k]
        check((*k,r["actor"],r["actor_born"]) in pairs, "unseen candidate")
        trace=[s.split("/") for s in r["trace"].split(",")]
        check(len(trace)==int(r["n_writes"]) and 1<=len(trace)<=6, "write count")
        times=[int(s[0]) for s in trace]
        check(all(a<b for a,b in zip(times,times[1:])) and times[0]>int(c["maker_born"])+81,
              "read time or original death")
        aligned=True
        for i,s in enumerate(trace):
            live=(s[1],s[2],s[3])==(c["focal_site"],c["focal_born"],"o")
            if live:
                check(int(s[0])<=int(c["focal_born"])+81 and
                      int(s[5])==bytes.fromhex(c["product"])[int(s[4])],"opening byte")
            aligned &= live and int(s[4])==i
            if i==0:
                check(aligned,"unaligned start")
        changed=sum(s[5]!=s[6] for s in trace)
        check(int(r["aligned"])==aligned and int(r["substitutions"])==changed,"read audit")
        if r["status"]=="birth":
            check(bytes(int(s[6]) for s in trace).hex()==r["product"] and int(r["finish"])>times[-1],"output audit")
        c["attempts"]+=1; c["first_read"]=1
        if len(trace)==6 and aligned:
            c["six_aligned"]=1
            if not changed and r["status"]=="birth":
                c["exact_birth"]=1
                observed[(*k,r["actor"],r["actor_born"],r["target"],r["finish"],r["product"],
                          ",".join(s[0] for s in trace),",".join(s[1] for s in trace))]+=1
    check(observed==expected,"post-death births, identities or six read ticks differ from the independent link archive")


def availability(directory,data):
    seen=set()
    for r in read(directory/"availability.tsv"):
        k=key(r)
        check(k not in seen,"duplicated availability window")
        seen.add(k)
        c=data[k]
        whole,far,active,near_active=(int(r[x]) for x in
            ("global_s_ticks","distant_s_ticks","other_executed_s_ticks","neighbor_executed_s_ticks"))
        n=int(c["open_ticks"])
        check(0<=near_active<=active<=whole<=n and 0<=far<=whole,"global availability counts")
        check(not c["s_neighbor"] or whole>0,"missing adjacent carrier in global scan")
        if not c["s_neighbor"]:
            check(far==whole and near_active==0,"nonlocal carrier audit")
        c["global_s"]=int(whole>0)
        c["distant_only"]=int(whole>0 and not c["s_neighbor"])
        c["no_other_s"]=int(n>0 and not whole)
        c["other_executed_s"]=int(active>0)
        c["neighbor_executed_s"]=int(near_active>0)
        c["distant_only_executed_s"]=int(active>0 and c["distant_only"])
        check(c["distant_only"]+c["no_other_s"]+c["s_neighbor"]==(n>0),"availability classification")
    check(seen==data.keys(),"missing availability window")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    d=parser.parse_args().directory
    data=cases(d)
    pairs=count_neighbors(d,data)
    availability(d,data)
    check_attempts(d,data,pairs)
    for c in data.values():
        check(all(c[a]>=c[b] for a,b in zip(STAGES,STAGES[1:])),"stages are not nested")
        check(c["facing"]>=c["facing_room"] and c["s_neighbor"]>=c["facing"],"facing screen")
    save(d/"case-stages.tsv",list(data.values()))
    summaries=[]
    for cohort,low,high in (("pilot",19521,20544),("replication",20545,21568),("pooled",19521,21568)):
        for arm in (*ARMS,"all"):
            for coverage in ("complete","truncated"):
                rows=[c for c in data.values() if low<=int(c["seed"])<=high and
                      (c["arm"]==arm or arm=="all") and (c["complete"]=="1")==(coverage=="complete")]
                tick_counts=sorted(int(r["open_ticks"]) for r in rows)
                check(bool(tick_counts),"empty summary cell")
                sums={k:sum(int(r[k]) for r in rows) for k in FLAGS+PAIR_SUMS}
                summaries.append(dict(cohort=cohort,arm=arm,coverage=coverage,cases=len(rows),
                                      no_window=tick_counts.count(0),ticks_total=sum(tick_counts),
                                      ticks_min=tick_counts[0],ticks_median=median(tick_counts),ticks_max=tick_counts[-1],
                                      **sums))
    save(d/"summary.tsv",summaries)


if __name__=="__main__":
    main()
