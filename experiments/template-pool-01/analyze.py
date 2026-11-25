"""Audit individual products and summarize paired chamber observations."""
import argparse
import csv
import gzip
import math
import shutil
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

PATTERN, REORDER = "001011", "011100"
ARMS = ("empty", "pattern", "reorder", "blind")
BRANCHES = ("first", "transfer_active", "transfer_blind")
SEEDS = range(27713, 29761)
BLOCKS = {"A": range(27713, 28737), "B": range(28737, 29761), "both": SEEDS}


def comp(s):
    return s.translate(str.maketrans("01", "10"))


def rows(path):
    with path.open() as stream:
        yield from csv.DictReader(stream, delimiter="\t")


def save(path, records):
    with path.open("w", newline="") as stream:
        out = csv.DictWriter(stream, fieldnames=records[0], delimiter="\t", lineterminator="\n")
        out.writeheader()
        out.writerows(records)


@dataclass(frozen=True)
class Product:
    seq: str
    guide: int
    tick: int


@dataclass
class Sample:
    supplied: str
    selected: int
    products: list
    counts: Counter

    def share(self, target):
        return self.counts[target] / len(self.products) if self.products else 0.0

    def traced_return(self, parent, target):
        if parent.selected < 1:
            return False
        retained = parent.products[parent.selected - 1]
        return (retained.guide == 0 and retained.seq == comp(target)
                and any(p.guide == 0 and p.seq == target for p in self.products))


def load(src):
    births = defaultdict(list)
    for r in rows(src / "products.tsv"):
        key = (int(r["seed"]), r["arm"], r["branch"])
        history = births[key]
        assert int(r["id"]) == len(history) + 1
        tick, guide = int(r["tick"]), int(r["guide"])
        assert (history[-1].tick if history else 0) < tick <= 160
        assert -1 <= guide <= len(history)
        assert len(r["sequence"]) == 6 and set(r["sequence"]) <= set("01")
        history.append(Product(r["sequence"], guide, tick))
    samples = {}
    for r in rows(src / "worlds.tsv"):
        key = (int(r["seed"]), r["arm"], r["branch"])
        products = births.pop(key, [])
        assert key not in samples and len(products) == int(r["products"])
        supplied = r["supplied"]
        assert supplied != "-" or all(p.guide != 0 for p in products)
        tails = [s.split("/") for s in r["partials"].split(",")]
        assert len(tails) == 4
        docked = [int(g) for _, g in tails if int(g) >= 0]
        assert len(set(docked)) == len(docked)
        assert all(g <= len(products) and (g > 0 or supplied != "-") for g in docked)
        assert all(s == "-" or (0 < len(s) < 6 and set(s) <= set("01")) for s, _ in tails)
        material = "".join(p.seq for p in products) + "".join(s for s, _ in tails if s != "-")
        for bit in "01":
            assert material.count(bit) + int(r["free" + bit]) == 64
        assert len(material) == int(r["accepted"])
        assert 160 == len(material) + int(r["rejected"]) + int(r["missing"])
        samples[key] = Sample(supplied, int(r["selected_first_id"]), products, Counter(p.seq for p in products))
    assert not births
    assert set(samples) == {(s, a, b) for s in SEEDS for a in ARMS for b in BRANCHES}
    for seed in SEEDS:
        for arm, supplied in zip(ARMS, ("-", PATTERN, REORDER, PATTERN)):
            start = samples[seed, arm, "first"]
            assert start.supplied == supplied
            if start.products:
                assert 1 <= start.selected <= len(start.products)
                retained = start.products[start.selected - 1].seq
            else:
                assert start.selected == -1
                retained = "-"
            for b in BRANCHES[1:]:
                child = samples[seed, arm, b]
                assert child.selected == start.selected and child.supplied == retained
    return samples


def differences(samples, seed):
    def fraction(arm, target, branch="first"):
        return samples[seed, arm, branch].share(target)
    a, b = comp(PATTERN), comp(REORDER)
    active, blind = (samples[seed, "pattern", name] for name in BRANCHES[1:])
    target = comp(active.supplied)
    return {
        "round1_pattern_minus_empty": fraction("pattern", a) - fraction("empty", a),
        "round1_pattern_minus_blind": fraction("pattern", a) - fraction("blind", a),
        "round1_pattern_minus_reorder_on_pattern_complement": fraction("pattern", a) - fraction("reorder", a),
        "round1_reorder_minus_pattern_on_reorder_complement": fraction("reorder", b) - fraction("pattern", b),
        "round2_active_minus_blind_on_transfer_complement": active.share(target) - blind.share(target),
        "round2_pattern_minus_empty_on_original": active.share(PATTERN) - fraction("empty", PATTERN, "transfer_active"),
    }


def background(seed, chamber):
    """Supplementary exact paths rooted at an unguided product in the first empty arm."""
    paths = {}
    longest = ()
    guided = 0
    for i, p in enumerate(chamber.products, 1):
        if p.guide < 0:
            paths[i] = (i,)
        else:
            assert p.guide > 0
            guided += 1
            if p.guide in paths and p.seq == comp(chamber.products[p.guide - 1].seq):
                paths[i] = (*paths[p.guide], i)
        if i in paths and len(paths[i]) > len(longest):
            longest = paths[i]
    witness = [chamber.products[i - 1] for i in longest]
    return dict(seed=seed, products=len(chamber.products), guided_products=guided,
                depth=len(longest) - 1, ids=",".join(map(str, longest)) or "-",
                sequences=",".join(p.seq for p in witness) or "-",
                ticks=",".join(str(p.tick) for p in witness) or "-")


def analyze(src, dest):
    samples = load(src)
    dest.mkdir(parents=True, exist_ok=True)
    summaries, spectra, contrasts, returns = [], [], [], []
    for block, seeds in BLOCKS.items():
        for arm in ARMS:
            for branch in BRANCHES:
                batch = [samples[seed, arm, branch] for seed in seeds]
                counts = sum((s.counts for s in batch), Counter())
                total = sum(counts.values())
                summaries.append(dict(block=block, arm=arm, branch=branch, worlds=len(seeds), products=total,
                                      zero_output=sum(not s.products for s in batch),
                                      no_transfer=sum(s.selected == -1 for s in batch),
                                      pattern_share_mean=f"{statistics.mean(s.share(PATTERN) for s in batch):.8f}",
                                      complement_share_mean=f"{statistics.mean(s.share(comp(PATTERN)) for s in batch):.8f}",
                                      supplied_complement_share_mean=f"{statistics.mean(s.share(comp(s.supplied)) for s in batch):.8f}"))
                for i in range(64):
                    seq = format(i, "06b")
                    spectra.append(dict(block=block, arm=arm, branch=branch, sequence=seq, count=counts[seq],
                                        total=total, pooled_share=f"{counts[seq] / total:.8f}" if total else "0"))
            if arm not in ("pattern", "reorder"):
                continue
            target = PATTERN if arm == "pattern" else REORDER
            for branch in BRANCHES[1:]:
                selected, echo, at_least_one = 0, 0, 0
                for seed in seeds:
                    start, later = samples[seed, arm, "first"], samples[seed, arm, branch]
                    at_least_one += any(p.guide == 0 and p.seq == comp(target) for p in start.products)
                    if start.selected > 0:
                        p = start.products[start.selected - 1]
                        selected += p.guide == 0 and p.seq == comp(target)
                    echo += later.traced_return(start, target)
                returns.append(dict(block=block, arm=arm, branch=branch, worlds=len(seeds),
                                    direct_exact_first=at_least_one, selected_direct_exact=selected, direct_exact_return=echo))
        paired = [differences(samples, seed) for seed in seeds]
        for name in paired[0]:
            values = [r[name] for r in paired]
            mean = statistics.mean(values)
            half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
            contrasts.append(dict(block=block, contrast=name, worlds=len(values), mean_delta=f"{mean:.8f}",
                                  low95=f"{mean - half:.8f}", high95=f"{mean + half:.8f}",
                                  positive=sum(v > 0 for v in values), negative=sum(v < 0 for v in values)))
    for name, records in (("summary", summaries), ("spectra", spectra), ("contrasts", contrasts), ("returns", returns)):
        save(dest / (name + ".tsv"), records)
    save(dest / "background.tsv", [background(s, samples[s, "empty", "first"]) for s in SEEDS])
    for name in ("worlds", "products"):
        with (src / (name + ".tsv")).open("rb") as source, (dest / (name + ".tsv.gz")).open("wb") as file:
            with gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0, compresslevel=6) as output:
                shutil.copyfileobj(source, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    analyze(args.input, args.output)
