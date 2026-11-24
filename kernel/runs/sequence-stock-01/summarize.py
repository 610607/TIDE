"""Reduce the verified whole-world ledgers to the registered sequence endpoints."""
import argparse
import csv
import gzip
import hashlib
import io
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path

from replay import TABLES, references

ROUTES = ("self", "live", "residual", "assembly", "substitution")
RETURNS = tuple("return_" + route for route in ROUTES)
MAXIMA = ("self_depth", "live_depth", "self_span", "live_span", "max_occupied_run", "max_stored_run")
WITNESS = "522e2e504c44"
END = 2048


def check(condition, message):
    if not condition:
        raise ValueError(message)


def rows(raw):
    return csv.DictReader(io.StringIO(raw.decode("ascii")), delimiter="\t")


def table(file, columns):
    writer = csv.DictWriter(file, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    return writer


def aggregate(rows_by_seed, sequence_sets):
    counts = Counter()
    for r in rows_by_seed:
        for k, v in r.items():
            if k in MAXIMA:
                counts[k] = max(counts[k], v)
            elif k not in ("cohort", "seed"):
                counts[k] += v
    counts["worlds"] = len(rows_by_seed)
    for k, v in sequence_sets.items():
        counts["distinct_" + k] = len(v)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("details", type=Path)
    parser.add_argument("index", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    archived = list(references())
    index = list(rows(args.index.read_bytes()))
    check(len(archived) == len(index) == 2048, "incomplete cohorts")
    seed_rows = []
    sets = defaultdict(lambda: defaultdict(set))
    live_columns = ("cohort", "seed", "tick", "product_site", "product", "donor_site",
                    "donor_born", "executor_site", "executor_born", "executor",
                    "donor_direct_births", "donor_lifetime_complete")
    with ExitStack() as opened:
        def output(name):
            return opened.enter_context((args.output / name).open("w", newline=""))

        live_out = table(output("living-template-births.tsv"), live_columns)
        binary = opened.enter_context((args.output / "world-sequences.tsv.gz").open("wb"))
        packed = opened.enter_context(gzip.GzipFile(filename="", fileobj=binary, mode="wb", compresslevel=6, mtime=0))
        for world_number, ((cohort, ref), digest) in enumerate(zip(archived, index)):
            seed = ref["seed"]
            check((cohort, seed, ref["state_fnv64"]) ==
                  (digest["cohort"], digest["seed"], digest["state_fnv64"]), f"index mismatch at {seed}")
            ledgers = {}
            for name in TABLES:
                data = gzip.decompress((args.details / seed / f"{name}.tsv.gz").read_bytes())
                check(hashlib.sha256(data).hexdigest() == digest[name + "_sha256"], f"{seed} {name} hash")
                ledgers[name] = data
            sequence_lines = ledgers["sequences"].splitlines(keepends=True)
            if world_number == 0:
                packed.write(b"seed\t" + sequence_lines[0])
            prefix = seed.encode("ascii") + b"\t"
            packed.write(b"".join(prefix + line for line in sequence_lines[1:]))
            stats = dict(cohort=cohort, seed=seed, births=int(ref["births"]), deaths=int(ref["deaths"]),
                         living=int(ref["living"]), reproducing=int(ref["status"] == "reproducing"),
                         stagnant=int(ref["status"] == "stagnant"), extinct=int(ref["status"] == "extinct"))
            sums = Counter()
            seqsets = sets[cohort]
            for row in rows(ledgers["sequences"]):
                seq = row.pop("sequence")
                r = {k: int(v) for k, v in row.items()}
                check(0 <= r["max_occupied_run"] <= r["occupied_ticks"] <= r["stored_ticks"] <= END+1
                      and r["max_occupied_run"] <= r["max_stored_run"] <= r["stored_ticks"]
                      and 0 <= r["peak_occupied"] <= r["peak_stored"] <= 64, f"{seed} sequence stock")
                for k in (*ROUTES, *RETURNS, "external_births", "different_live", "occupied_copy_ticks",
                          "reserved_copy_ticks", "free_copy_ticks", "occupied_end", "reserved_end", "free_end"):
                    sums[k] += r[k]
                for k in MAXIMA:
                    sums[k] = max(sums[k], r[k])
                if r["stored_ticks"]:
                    seqsets["stored"].add(seq)
                if r["occupied_ticks"]:
                    seqsets["occupied"].add(seq)
                if r["different_live"]:
                    seqsets["different_live"].add(seq)
            check(sum(sums[k] for k in ROUTES) == stats["births"] and sums["occupied_end"] == stats["living"]
                  and sums["external_births"] == int(ref["external_births"]), f"{seed} census mismatch")
            direct = Counter()
            living_copies = []
            expected_area = 81  # founder contributes snapshots 0 through 80
            birth_routes = Counter()
            return_routes = Counter()
            witness_rows = []
            birth_reader = rows(ledgers["births"])
            for r in birth_reader:
                t = int(r["tick"])
                expected_area += min(81, END + 1 - t)
                direct[r["executor_site"], r["executor_born"]] += 1
                birth_routes[r["route"]] += 1
                return_routes[r["route"]] += int(r["restored"])
                if r["route"] == "live":
                    living_copies.append(r)
                if seed == "19722" and (WITNESS in (r["executor"], r["product"]) or
                                        any(s.endswith("/" + WITNESS) for s in r["sources"].split(","))):
                    witness_rows.append(r)
            check(expected_area == sums["occupied_copy_ticks"], f"{seed} occupied copy-time mismatch")
            check(all(birth_routes[k] == sums[k] and return_routes[k] == sums["return_" + k]
                      for k in ROUTES), f"{seed} detailed birth route mismatch")
            primary = zero_direct = censored = 0
            for r in living_copies:
                donors = set()
                for offset, source in enumerate(r["sources"].split(",")):
                    _, site, source_offset, kind, born, _, seq = source.split("/")
                    check(int(source_offset) == offset and kind == "o" and seq == r["product"]
                          and site != r["executor_site"], f"{seed} invalid live template")
                    donors.add((site, born))
                check(len(donors) == 1, f"{seed} multiple template identities")
                donor, = donors
                num_direct = direct[donor]
                complete = int(donor[1]) + 81 <= END
                if r["executor"] != r["product"]:
                    primary += 1
                    censored += not complete
                    zero_direct += complete and num_direct == 0
                live_out.writerow(dict(cohort=cohort, seed=seed, donor_site=donor[0], donor_born=donor[1],
                                       donor_direct_births=num_direct, donor_lifetime_complete=int(complete),
                                       **{k: r[k] for k in ("tick", "product_site", "product", "executor_site",
                                                             "executor_born", "executor")}))
            check(primary == sums["different_live"], f"{seed} primary endpoint mismatch")
            stats.update(sums, different_live_worlds=int(primary > 0), zero_direct_complete=zero_direct,
                         zero_direct_complete_worlds=int(zero_direct > 0), censored_primary=censored)
            seed_rows.append(stats)
            if seed == "19722":
                stock_reader = rows(ledgers["stocks"])
                stock_out = table(output("witness-stocks.tsv"), stock_reader.fieldnames)
                stock_out.writerows(r for r in stock_reader if r["sequence"] == WITNESS)
                birth_out = table(output("witness-births.tsv"), birth_reader.fieldnames)
                birth_out.writerows(witness_rows)
        table(output("seeds.tsv"), seed_rows[0]).writerows(seed_rows)
        pooled_sets = {k: sets["pilot"][k] | sets["replication"][k] for k in sets["pilot"]}
        summaries = []
        for cohort in ("pilot", "replication", "pooled"):
            selected = [r for r in seed_rows if cohort == "pooled" or r["cohort"] == cohort]
            totals = aggregate(selected, pooled_sets if cohort == "pooled" else sets[cohort])
            summaries.append(dict(cohort=cohort, **totals))
        table(output("cohorts.tsv"), summaries[0]).writerows(summaries)


if __name__ == "__main__":
    main()
