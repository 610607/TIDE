"""Independently reconstruct births, paid material, exact paths and sequence frequencies."""
import argparse
import csv
import gzip
import math
import shutil
import statistics
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "template-pool-01/results"
H = 2048
ARMS = ("closed_stable", "fed_stable", "closed_break", "fed_break", "fed_break_rotated")
AGES = (0, 32, 64, 128, 256, 512, 1024, H)
WINDOWS = (128, 256, 512, 1024, 1536, H)
BLOCKS = {"A": range(27713, 28737), "B": range(28737, 29761), "both": range(27713, 29761)}


def rows(path):
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt") as f:
        yield from csv.DictReader(f, delimiter="\t")


def save(path, records):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=records[0], delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(records)


def archive(raw):
    screening = {int(r["seed"]): r for r in rows(raw / "screen.tsv")}
    assert list(screening) == list(BLOCKS["both"])
    anchors = {int(r["seed"]): r for r in rows(raw / "history.tsv")}
    history = defaultdict(list)
    for r in rows(OLD / "products.tsv.gz"):
        if r["arm"] == "empty" and r["branch"] == "first":
            history[int(r["seed"])].append(tuple(int(r[k], 2 if k == "sequence" else 10)
                                                  for k in ("id", "tick", "sequence", "guide")))
    for r in rows(OLD / "worlds.tsv.gz"):
        if (r["arm"], r["branch"]) != ("empty", "first"):
            continue
        seed = int(r["seed"])
        s = screening[seed]
        if history[seed]:
            assert (1, int(s["tick"]), int(s["sequence"]), -1) == history[seed][0]
            assert all(anchors[seed][k] == r[k] for k in ("products", "free0", "free1", "accepted", "rejected", "missing", "partials"))
        else:
            assert seed not in anchors and s["tick"] == s["sequence"] == "-1"
            assert (s["free0"], s["free1"], s["partial"]) == (r["free0"], r["free1"], r["partials"])
    assert set(anchors) == {s for s, r in screening.items() if int(r["tick"]) > 0}
    return screening, history


def audit(w, chains, origin, snaps, reference):
    seed, arm = int(w["seed"]), w["arm"]
    root, fork = int(origin["sequence"]), int(origin["tick"])
    if arm.endswith("rotated"):
        root = ((root << 1) & 63) | (root >> 5)
    seqs, births, deaths, depth = [None], [-1], [-1], [-1]
    broad = [False]
    same_order_births = []
    by_window = [Counter() for _ in WINDOWS]
    historical = []
    waste = [0, 0]
    stock = [0, 0]
    for r in chains:
        i, seq, t, d, guide, gap, recorded = map(int, (r[k] for k in ("id", "sequence", "born", "death", "guide", "interrupted", "depth")))
        assert i == len(seqs) and (t == 0 if i == 1 else births[-1] < t <= H)
        assert 0 <= seq < 64 and (d == -1 or t < d <= H and d % 8 == 0)
        assert (guide == -1 or 0 < guide < i) and (gap == -1 or 0 < gap < i)
        exact, related = -1, False
        if i == 1:
            assert guide == gap == -1 and seq == root
            exact, related = 0, True
        elif guide > 0:
            assert gap == -1 and (deaths[guide] == -1 or deaths[guide] > t)
            related = broad[guide]
            if depth[guide] >= 0 and seq == (seqs[guide] ^ 63):
                exact = depth[guide] + 1
        if gap > 0:
            assert guide == -1 and 0 < deaths[gap] <= t
        assert recorded == exact
        seqs.append(seq)
        births.append(t)
        deaths.append(d)
        depth.append(exact)
        broad.append(related)
        ones = seq.bit_count()
        for bit, units in enumerate((6 - ones, ones)):
            (waste if d >= 0 else stock)[bit] += units
        if t > 0:
            by_window[next(j for j, stop in enumerate(WINDOWS) if t <= stop)][seq] += 1
            if seq == root:
                same_order_births.append(i)
        if t + fork <= 160 and arm == "closed_stable":
            historical.append((i, t + fork, seq, guide))
    if arm == "closed_stable":
        assert historical == reference
    assert not arm.endswith("stable") or all(d == -1 for d in deaths)
    tail = [s.split("/") for s in w["partials"].split(",")]
    assert len(tail) == 4 and len({g for _, g in tail if int(g) > 0}) == sum(int(g) > 0 for _, g in tail)
    for seq, guide in tail:
        assert int(guide) == -1 or 0 < int(guide) < len(seqs) and deaths[int(guide)] == -1
        assert seq == "-" or (len(seq) < 6 and set(seq) <= set("01"))
        for bit in (0, 1):
            stock[bit] += seq.count(str(bit))
    accepted = 0
    for bit in (0, 1):
        val = lambda k: int(w[k + str(bit)])
        assert val("feed") == (H // 4 if arm.startswith("fed") else 0)
        assert val("full_waste") == waste[bit]
        assert 64 + val("feed") == val("free") + stock[bit] + waste[bit] + val("partial_waste") + val("overflow")
        accepted += stock[bit] + waste[bit] + val("partial_waste")
    assert accepted == int(w["accepted"])
    assert accepted + int(w["rejected"]) + int(w["missing"]) == fork + H
    members = [i for i in range(1, len(seqs)) if depth[i] >= 0]
    loss = -1 if any(deaths[i] == -1 for i in members) else max(deaths[i] for i in members)
    post = [i for i in same_order_births if i in members and deaths[1] >= 0 and births[i] > deaths[1]]
    assert (int(w["loss"]), int(w["origin_death"]), int(w["post_return"]), int(w["max_depth"])) == (loss, deaths[1], len(post), max(depth))
    checks = []
    for age in AGES:
        live = [i for i in range(1, len(seqs)) if births[i] <= age and (deaths[i] == -1 or deaths[i] > age)]
        exact = sum(depth[i] >= 0 for i in live)
        assert (len(live), exact) == snaps[age]
        assert (exact > 0) == (loss < 0 or age < loss)
        checks.append(dict(seed=seed, arm=arm, age=age, founder=int(1 in live), exact=int(exact > 0),
                           broad=int(any(broad[i] for i in live)), order=int(any(seqs[i] == root for i in live))))
    assert snaps[H][1] == int(w["exact_final"])
    late = sum(t > H - 128 for t in births[1:])
    state = "empty" if not live else "active" if late else "stagnant"
    latest = max(members, key=lambda i: (births[i], i))
    result = dict(seed=seed, arm=arm, root=root, founder_death=deaths[1], exact_loss=loss, depth=max(depth),
                  exact_members=len(members), last_exact_birth=births[latest], last_exact_id=latest,
                  exact_end=int(loss < 0), founder_end=int(deaths[1] < 0), primary=int(loss < 0 and deaths[1] >= 0),
                  post_return=int(bool(post)), last_post_return=max((births[i] for i in post), default=-1),
                  broad_end=checks[-1]["broad"], order_end=checks[-1]["order"],
                  broad_order_end=int(any(broad[i] and seqs[i] == root for i in live)),
                  reborn=int(loss >= 0 and any(births[i] > loss for i in same_order_births)),
                  late_births=late, no_birth=int(len(seqs) == 2), live_end=len(live), status=state)
    return result, checks, by_window


def summarize(outcomes, checks):
    summary, curves = [], []
    for block, seeds in BLOCKS.items():
        for arm in ARMS:
            cohort = [r for r in outcomes if r["seed"] in seeds and r["arm"] == arm]
            losses = sorted(H + 1 if r["exact_loss"] < 0 else r["exact_loss"] for r in cohort)
            r = dict(block=block, arm=arm, screened=len(seeds), enrolled=len(cohort))
            for key in ("primary", "exact_end", "founder_end", "broad_end", "order_end", "broad_order_end", "post_return", "reborn", "no_birth"):
                r[key] = sum(p[key] for p in cohort)
            for key in ("active", "stagnant", "empty"):
                r[key] = sum(p["status"] == key for p in cohort)
            for q in (50, 90, 95):
                v = losses[math.ceil(q / 100 * len(losses)) - 1]
                r["loss_p" + str(q)] = v if v <= H else -1
            r["max_depth"] = max(p["depth"] for p in cohort)
            r["last_exact_birth"] = max(p["last_exact_birth"] for p in cohort)
            summary.append(r)
            for t in AGES:
                data = checks[arm, t]
                subset = [p for p in data if p["seed"] in seeds]
                curves.append(dict(block=block, arm=arm, age=t, enrolled=len(subset),
                                   **{k: sum(p[k] for p in subset) for k in ("founder", "exact", "broad", "order")}))
    return summary, curves


def order_contrast(pairs):
    records = []
    for block, seeds in BLOCKS.items():
        eligible = [(s, p) for s, p in pairs.items() if s in seeds and p["root"] not in (p["rotated"], p["rotated"] ^ 63)]
        for j, end in enumerate(WINDOWS):
            effects, empty_a, empty_b = [], 0, 0
            for _, p in eligible:
                def preference(counts):
                    total = sum(counts.values())
                    return (counts[p["root"]] + counts[p["root"] ^ 63] -
                            counts[p["rotated"]] - counts[p["rotated"] ^ 63]) / total if total else 0
                a, b = p["fed_break"][j], p["fed_break_rotated"][j]
                empty_a += not a
                empty_b += not b
                effects.append((preference(a) - preference(b)) / 2)
            effect = statistics.mean(effects)
            half = 1.96 * statistics.stdev(effects) / math.sqrt(len(effects))
            records.append(dict(block=block, start=1 if j == 0 else WINDOWS[j-1] + 1, end=end,
                                eligible=len(effects), empty_natural=empty_a, empty_reordered=empty_b,
                                effect=f"{effect:.8f}", low95=f"{effect-half:.8f}", high95=f"{effect+half:.8f}"))
    return records


def main(raw, dest):
    screen, historical = archive(raw)
    worlds = {(int(w["seed"]), w["arm"]): w for w in rows(raw / "worlds.tsv")}
    snaps = defaultdict(dict)
    for s in rows(raw / "snapshots.tsv"):
        snaps[int(s["seed"]), s["arm"]][int(s["age"])] = tuple(map(int, (s["live"], s["exact"])))
    assert set(worlds) == set(snaps) == {(s, a) for s, r in screen.items() if int(r["tick"]) > 0 for a in ARMS}
    outcomes, checks, pairs = [], defaultdict(list), defaultdict(dict)
    for key, group in groupby(rows(raw / "chains.tsv"), lambda r: (int(r["seed"]), r["arm"])):
        seed, arm = key
        outcome, snapshots, counts = audit(worlds.pop(key), group, screen[seed], snaps.pop(key), historical[seed])
        outcomes.append(outcome)
        for r in snapshots:
            checks[arm, r["age"]].append(r)
        if arm in ("fed_break", "fed_break_rotated"):
            pk = "root" if arm == "fed_break" else "rotated"
            pairs[seed].update({pk: outcome["root"], arm: counts})
    assert not worlds and not snaps
    summary, curves = summarize(outcomes, checks)
    dest.mkdir(parents=True, exist_ok=True)
    for name, batch in (("outcomes", outcomes), ("summary", summary), ("survival", curves), ("order", order_contrast(pairs))):
        save(dest / (name + ".tsv"), batch)
    shutil.copyfile(raw / "screen.tsv", dest / "screen.tsv")
    for name in ("chains", "worlds", "history", "snapshots"):
        with (raw / (name + ".tsv")).open("rb") as src, (dest / (name + ".tsv.gz")).open("wb") as out:
            with gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0, compresslevel=6) as zipped:
                shutil.copyfileobj(src, zipped)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.input, a.output)
