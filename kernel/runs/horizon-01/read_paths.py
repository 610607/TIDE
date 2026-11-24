"""Follow every exposed birth in the read-only field runs into its daughter's lifetime."""
import argparse
import csv
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from measure import ANCESTOR, BUILD, HERE, Assays, Setup, field_id, require, save, table


@dataclass
class History:
    genome: str
    first_read: dict | None = None
    reads: int = 0
    births: int = 0
    births_after_read: int = 0
    death: int | None = None
    writes: list = field(default_factory=list)


def read_case(cpu, first):
    site = int(first["read_site"])
    x, y = cpu[0] % 8, cpu[0] // 8
    for d, (dx, dy) in enumerate(((0, 1), (1, 0), (0, -1), (-1, 0))):
        if ((y + dy) % 8) * 8 + (x + dx) % 8 == site:
            return d
    raise ValueError("nonlocal read")


def field_paths(binary, cohort, summary, assays):
    seed = summary["seed"]
    history = {(36, 0): History(ANCESTOR)}
    exposed = []
    counts = Counter()
    trace = subprocess.check_output([binary, "trace", "read", seed], text=True)
    for e in csv.DictReader(trace.splitlines(), delimiter="\t"):
        cpu = field_id(e, "actor", "born")
        h = history[cpu]
        effect = e["effect"]
        if e["read_kind"] != "-":
            counts[e["read_kind"]] += 1
            h.reads += 1
            if h.first_read is None:
                h.first_read = e
        if effect == "reserve":
            h.writes.clear()
        elif effect == "copy":
            h.writes.append(e)
        elif effect == "death":
            h.death = int(e["tick"])
        elif effect == "birth":
            child = field_id(e, "target", "tick")
            product = e["product_hex"]
            history[child] = History(product)
            h.births += 1
            require(bytes(int(w["output"]) for w in h.writes).hex() == product, "copy record differs")
            if h.first_read:
                h.births_after_read += 1
                first = h.first_read
                inputs = bytes(int(w["input"]) for w in h.writes).hex()
                different = sum(w["input"] != w["output"] for w in h.writes)
                sources = ",".join(w["read_site"] for w in h.writes)
                kinds = ",".join("self" if w["read_kind"] == "-" else w["read_kind"] for w in h.writes)
                foreign = sum(w["read_kind"] != "-" for w in h.writes)
                case_key, outcome = "-", "nonlive_contact"
                if first["read_kind"] == "occupied":
                    case = Setup("read", h.genome, first["read_hex"], read_case(cpu, first))
                    case_key = case.key()
                    _, outcome = assays.run(case, 4096)
                exposed.append(dict(cohort=cohort, seed=seed, mother_site=cpu[0], mother_born=cpu[1],
                    mother_genome=h.genome, first_read_tick=first["tick"], first_donor_kind=first["read_kind"],
                    first_donor_site=first["read_site"], first_donor_hex=first["read_hex"],
                    child_site=child[0], child_born=child[1], product_hex=product,
                    inputs_hex=inputs, sources=sources, source_kinds=kinds, external_bytes=foreign,
                    substitutions=different, same_as_mother=int(product == h.genome),
                    assay=case_key, assay_class=outcome))
            h.writes.clear()
    require(sum(h.births for h in history.values()) == int(summary["births"]) and
            sum(h.death is not None for h in history.values()) == int(summary["deaths"]),
            "field population ledger differs")
    require(len(exposed) == int(summary["exposed_births"]), "exposed birth count differs")
    for kind, name in (("occupied","live"), ("reserved","reserved"), ("free","free")):
        require(counts[kind] == int(summary[name + "_contacts"]), "external read count differs")
    for r in exposed:
        child = (r["child_site"], r["child_born"])
        h = history[child]
        end = h.death if h.death is not None else 512
        r.update(child_births=h.births, child_reads=h.reads, child_births_after_read=h.births_after_read,
                 child_end="death" if h.death is not None else "cutoff", child_ticks_observed=end-child[1])
    require(sum(r["child_births_after_read"] for r in exposed) == int(summary["candidate_births"]),
            "two-generation screen differs")
    totals = dict(cohort=cohort, seed=seed, field_births=summary["births"],
        external_reads=sum(counts.values()), first_read_mothers=len({(r["mother_site"], r["mother_born"]) for r in exposed}),
        exposed_births=len(exposed), retained_maternal_genome=sum(r["same_as_mother"] for r in exposed),
        children_with_read=sum(r["child_reads"] > 0 for r in exposed),
        children_with_birth=sum(r["child_births"] > 0 for r in exposed))
    return exposed, totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--observe", type=Path, default=BUILD / "observe")
    parser.add_argument("--tide", type=Path, default=BUILD / "tide")
    parser.add_argument("--field-dir", type=Path, default=HERE)
    args = parser.parse_args()
    assays = Assays(args.observe.resolve())
    seeds, births = [], []
    for cohort, path in (("discovery", HERE.parent / "pilot-01/seeds.tsv"),
                         ("replication", HERE.parent / "replication-01/seeds.tsv"),
                         ("prospective", args.field_dir / "field-seeds.tsv")):
        for summary in table(path):
            if summary["arm"] == "read":
                records, totals = field_paths(args.tide.resolve(), cohort, summary, assays)
                births.extend(records)
                seeds.append(totals)
    args.out.mkdir(exist_ok=True, parents=True)
    save(args.out / "read-seeds.tsv", seeds)
    save(args.out / "read-births.tsv", births)
    save(args.out / "read-generations.tsv", assays.records)


if __name__ == "__main__":
    main()
