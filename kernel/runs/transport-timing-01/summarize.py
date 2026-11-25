"""Verify matched offers, join living-donor identities and compare the timing schedules."""
import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev

from simulate import ARMS, FIRST, SPLIT, STOP

PREVIOUS = Path(__file__).resolve().parent.parent / "transport-handoff-01"
sys.path.insert(0, str(PREVIOUS))
from analyze import score, save
from run import check, read

COHORTS = {"archived": range(FIRST, SPLIT), "new": range(SPLIT, STOP), "pooled": range(FIRST, STOP)}
STAGES = ("starts", "switches", "six", "exact")


def key(row):
    return int(row["seed"]), row["arm"]


def group(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    return grouped


def anchor(rows, name):
    expected = [r for r in read(PREVIOUS / "results" / (name + ".tsv")) if FIRST <= int(r["seed"]) < SPLIT and r["arm"] == "high"]
    observed = [r for r in rows if int(r["seed"]) < SPLIT and r["arm"] == "high"]
    check(observed == expected, "archived uniform mismatch in " + name)


def audit(directory):
    raw = {n: read(directory / (n + ".tsv")) for n in ("fields", "products", "switches", "budgets", "phases")}
    for n in ("fields", "products", "switches"):
        anchor(raw[n], n)
    worlds = {(s, a) for s in range(FIRST, STOP) for a in ARMS}
    for n in ("fields", "budgets"):
        check(len(raw[n]) == len(worlds) and {key(r) for r in raw[n]} == worlds, "missing or duplicate " + n)
    for rows in raw.values():
        check(all(key(r) in worlds for r in rows), "out-of-scope field")
    budgets = {key(r): r for r in raw["budgets"]}
    for s in range(FIRST, STOP):
        u, b = (budgets[s, a] for a in ARMS)
        check(all(u[k] == b[k] for k in ("sweeps", "offers", "offset", "edge_digest")), "different offered edges")
        check(int(u["sweeps"]) == int(u["active_ticks"]) == 2048 and int(b["active_ticks"]) == 512
              and 0 <= int(u["offset"]) < 32, "invalid schedule budget")
    products, switches, phases = (group(raw[n]) for n in ("products", "switches", "phases"))
    all_fields, links, phase_bins = {}, [], defaultdict(Counter)
    for w in raw["fields"]:
        job = key(w)
        rows = products[job]
        outcome = score(w, rows, links)
        budget = budgets[job]
        offset = int(budget["offset"])
        exact_at = Counter((int(r["read_ticks"].split(",")[0])-1-offset) % 32 for r in rows if r["executor"] != r["product"])
        per_phase = {int(r["phase"]): Counter({k: int(r[k]) for k in STAGES}) for r in phases[job]}
        check(len(per_phase) == len(phases[job]) and all(0 <= p < 32 for p in per_phase), "invalid phase records")
        counts = Counter()
        for p in range(32):
            c = per_phase.get(p, Counter())
            check(0 <= c["exact"] == exact_at[p] <= c["six"] <= c["starts"] - c["switches"] and c["switches"] >= 0,
                  "inconsistent phase counts")
            counts.update(c)
            phase_bins[job[0] >= SPLIT, job[1], p].update(c)
        check(counts["starts"] == int(w["started_unlike"]) and counts["switches"] == len(switches[job]) ==
              int(w["switched_supplier"]) and counts["exact"] == int(w["exact_births"]), "first-write totals")
        moves, swaps, offers = int(w["individual_moves"]), int(budget["swaps"]), int(budget["offers"])
        check(swaps <= offers and swaps <= moves <= 2*swaps, "exchange balance")
        all_fields[job] = dict(**outcome, **{k: counts[k] for k in STAGES}, encounters=int(w["encounters"]),
                               moves=moves, swaps=swaps, offers=offers, worlds=1,
                               **{k: int(w["status"] == k) for k in ("reproducing", "stagnant", "extinct")})
    save(directory / "links.tsv", links)
    save(directory / "endpoints.tsv", list(all_fields.values()))
    for name, data in (("links", links), ("endpoints", all_fields.values())):
        expected = [r for r in read(PREVIOUS / "results" / (name+".tsv")) if FIRST <= int(r["seed"]) < SPLIT and r["arm"] == "high"]
        observed = [r for r in data if r["seed"] < SPLIT and r["arm"] == "high"]
        check(len(expected) == len(observed) and all(all(str(got[k]) == v for k,v in want.items())
              for got, want in zip(observed, expected)), "archived handoff mismatch")
    return all_fields, phase_bins


def ratio_difference(fields, seeds, numerator, denominator, scale):
    rates, influence = [], []
    for arm in ARMS:
        records = [fields[s, arm] for s in seeds]
        den = sum(r[denominator] for r in records)
        rate = sum(r[numerator] for r in records) / den
        rates.append(rate)
        influence.append([scale * len(seeds) * (r[numerator]-rate*r[denominator])/den for r in records])
    delta = scale * (rates[1]-rates[0])
    paired = [b-a for a,b in zip(*influence)]
    half = 1.96 * stdev(paired) / math.sqrt(len(seeds))
    return {"delta": f"{delta:.6f}", "low95": f"{delta-half:.6f}" if half else "",
            "high95": f"{delta+half:.6f}" if half else ""}


def summarize(directory):
    fields, phases = audit(directory)
    cohorts, contrasts, positions = [], [], []
    for name, seeds in COHORTS.items():
        for arm in ARMS:
            totals = Counter()
            for s in seeds:
                totals.update({k:v for k,v in fields[s,arm].items() if k not in ("seed","arm")})
            bound = -math.expm1(math.log(.05)/len(seeds)) * 1000
            cohorts.append(dict(cohort=name, arm=arm, **totals,
                                zero_upper95_per_1000=f"{bound:.5f}" if not totals["complete_handoff_world"] else "NA"))
            for p in range(32):
                selected = [name == "new"] if name != "pooled" else [False, True]
                c = Counter()
                for new in selected:
                    c.update(phases[new, arm, p])
                label = "active" if p < 8 else "long_quiet" if p <= 22 else "short_quiet"
                positions.append(dict(cohort=name, arm=arm, phase=p, period=label, **{k:c[k] for k in STAGES}))
        metrics = (("handoff_worlds_per_1000", "complete_handoff_world", "worlds", 1000),
                   ("strict_worlds_per_1000", "strict_handoff_world", "worlds", 1000),
                   ("switch_pct", "switches", "starts", 100), ("six_pct", "six", "starts", 100),
                   ("exact_per_world", "exact", "worlds", 1))
        for label, num, den, scale in metrics:
            row = dict(cohort=name, metric=label, **ratio_difference(fields, seeds, num, den, scale),
                       gained="NA", lost="NA", tied="NA", exact_p="NA")
            if num.endswith("_world"):
                d = [fields[s,"burst"][num] - fields[s,"high"][num] for s in seeds]
                gained, lost = d.count(1), d.count(-1)
                n = gained+lost
                tail = sum(math.comb(n,j) for j in range(min(gained,lost)+1))
                row.update(gained=gained, lost=lost, tied=d.count(0), exact_p=f"{min(1,2*tail/2**n):.7f}")
            contrasts.append(row)
    save(directory / "cohorts.tsv", cohorts)
    save(directory / "contrasts.tsv", contrasts)
    save(directory / "phase-summary.tsv", positions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    summarize(parser.parse_args().directory)
