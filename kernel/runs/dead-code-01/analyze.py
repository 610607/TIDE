"""Compute the preregistered endpoints, tests and descriptive tables of dead-code-01.

  python3 analyze.py primary   # results/primary -> results/analysis
  python3 analyze.py scale     # results/scale -> results/scale-analysis (descriptive only)

The rules implemented here are those of protocol.md and docs/research/dead-code-rq.md, which
reuse the interpretation rules of docs/research/access-dynamics-rq.md. They were frozen with this
file before any study seed ran. The MODES, Bedau and test functions are copied unchanged from
kernel/runs/access-dynamics-01/analyze.py. Only the Python standard library is used.
"""
import argparse
import csv
import gzip
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELLS = ("self-retain", "read-retain", "read-empty", "read_fetch-retain", "read_fetch-empty")
SCALE_CELLS = CELLS[1:]
CLAIMS = (("D1", "read-retain", "read-empty"), ("D2", "read_fetch-retain", "read_fetch-empty"))
REPLICATION = (("C3", "read_fetch-retain", "self-retain"),)
ENDPOINTS = ("P1", "P2", "P3", "P4")
MECHANISMS = ("M1", "M2", "M3", "M4", "M5")
# Directions predicted for retain minus empty. P1, P2 and P4 keep their primary-family outcome.
BUFFER = {"M1": 1, "M3": -1, "M4": 1, "M5": 1, "P2": -1}
RAW = {"M2": 1, "P1": 1, "P2": 1, "P4": 1}
CLASSES = ("independent", "read_requiring", "fetch_requiring", "both_requiring", "either_sufficient",
           "template_only", "other", "residue_requiring", "residue_requiring_direct", "residue_requiring_indirect")
DEPENDENT = ("read_requiring", "fetch_requiring", "both_requiring", "either_sufficient", "residue_requiring",
             "residue_requiring_direct", "residue_requiring_indirect")
RCCCJD = "524343434a44"
SUBSTITUTION_PPM = 20000
SETTINGS = {
    "primary": dict(t=1024, step=256, start=1024, end=16384, stagnation_from=12288, seeds=range(31001, 31033),
                    sensitivity_t=(256, 2048), out="analysis", cells=CELLS),
    "scale": dict(t=4096, step=1024, start=4096, end=16384, stagnation_from=12288, seeds=range(31101, 31109),
                  sensitivity_t=(), out="scale-analysis", cells=SCALE_CELLS),
    # Code test only: short worlds run with --filter 64 16 1024 --sensitivity 16,128.
    "test": dict(t=64, step=16, start=64, end=1024, stagnation_from=768, seeds=(), sensitivity_t=(16, 128),
                 out="test-analysis", cells=CELLS),
}
ALPHA, UNREACHED_LIMIT, EQUIVALENCE_SD, BOOTSTRAP, BOOT_SEED = 0.05, 0.10, 0.5, 10000, 20261125
NAN = float("nan")


# ---------------------------------------------------------------- loading

def table(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class World:
    def __init__(self, directory):
        self.name = directory.name
        self.info = table(directory / "world.tsv.gz")[0]
        self.arm, self.reclamation, self.seed = self.info["arm"], self.info["reclamation"], int(self.info["seed"])
        self.cell = f"{self.arm}-{self.reclamation}"
        self.extinct = int(self.info["extinction_tick"]) >= 0
        self.points = {}
        for r in table(directory / "timepoints.tsv.gz"):
            self.points[(r["series"], int(r["t"]), int(r["level"]))] = r
        self.filtered = {}
        for r in table(directory / "filtered.tsv.gz"):
            key = (r["series"], int(r["t"]), int(r["level"]))
            self.filtered.setdefault(key, {})[r["component"]] = int(r["n_pass"])
        self.bedau = table(directory / "bedau.tsv.gz")
        self.collapsed = table(directory / "collapsed.tsv.gz")
        self.assays = {(r["series"], r["genotype"]): r for r in table(directory / "assays.tsv.gz")}
        self.ledger = table(directory / "ledger.tsv.gz")
        self.census = {int(r["level"]): r for r in table(directory / "census.tsv.gz")}
        self.neutrality = {r["genotype"]: r for r in table(directory / "neutrality.tsv.gz")}


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NAN
    return v


# ---------------------------------------------------------------- MODES (copied; F(A) kept, residue classes added)

def entropy(counts):
    total = sum(counts)
    return -sum(c / total * math.log2(c / total) for c in counts if c) if total else 0.0


def informative_mask(genotype, assay):
    """Component with non-informative sites masked, from the knockout assay of the genotype."""
    b = bytes.fromhex(genotype)
    ordinary = int(assay["ordinary"])
    keep = [ordinary > 0 and int(assay[f"ko{i}"]) < ordinary for i in range(len(b))]
    return "".join(f"{c:02x}" if k else "**" for c, k in zip(b, keep))


def modes(w, cfg, series, t, components=None, assay_series=None):
    """Per-level MODES statistics. Levels after extinction are empty; unreached levels are None."""
    out = {}
    seen, previous = set(), None
    for level in range(0, cfg["end"] + 1, cfg["step"]):
        row = w.points.get((series, t, level))
        if row is not None and int(row["eval_tick"]) >= 0:
            raw = w.filtered.get((series, t, level), {})
        elif row is None and w.extinct:
            raw = {}
        else:
            out[level] = None
            previous = None
            continue
        F = {}
        for g, n in raw.items():
            c = components(w, g) if components else g
            F[c] = F.get(c, 0) + n
        stats = {
            "change": len(set(F) - previous) if previous is not None else NAN,
            "novelty": len(set(F) - seen),
            "ecology": entropy(list(F.values())),
            "richness": len(F),
            "complexity": NAN,
            "classes": set(),
            "set": F,
        }
        if assay_series:
            infos = []
            for g in raw:
                a = w.assays.get((assay_series, g))
                if a is None:
                    raise ValueError(f"{w.name}: no {assay_series} assay for {g} at level {level}")
                infos.append(int(a["informative"]))
                stats["classes"].add(a["class"])
                if a["residue_requiring"] == "1":
                    stats["classes"].add("residue_requiring")
                    stats["classes"].add("residue_requiring_indirect" if a["class"] == "independent"
                                         else "residue_requiring_direct")
            stats["complexity"] = max(infos, default=0)
        out[level] = stats
        seen |= set(F)
        previous = set(F)
    return out


def window(cfg):
    return range(cfg["start"], cfg["end"] + 1, cfg["step"])


def modes_endpoints(w, cfg, m):
    levels = [m[L] for L in window(cfg)]
    reached = [s for s in levels if s is not None]
    unreached = (not w.extinct) and len(reached) < len(levels)
    if not reached:
        return dict(P1=NAN, P2=NAN, P3=NAN, reached=0, unreached=unreached)
    return dict(P1=sum(s["novelty"] for s in reached), P2=statistics.fmean(s["change"] for s in reached),
                P3=statistics.fmean(s["ecology"] for s in reached), reached=len(reached), unreached=unreached)


def bedau_p4(w, column):
    values = [num(r[column]) for r in w.bedau]
    return NAN if not values or any(math.isnan(v) for v in values) else statistics.fmean(values)


# ---------------------------------------------------------------- statistics

def wilcoxon(d):
    """Exact two-sided signed-rank p, conditional on the observed ranks (zeros dropped, ties averaged)."""
    d = [x for x in d if x != 0]
    n = len(d)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    rank2 = [0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        for k in range(i, j + 1):
            rank2[order[k]] = i + j + 2  # twice the average rank
        i = j + 1
    total = sum(rank2)
    w = sum(r for r, x in zip(rank2, d) if x > 0)
    dist = {0: 1}
    for r in rank2:
        nxt = dict(dist)
        for s, c in dist.items():
            nxt[s + r] = nxt.get(s + r, 0) + c
        dist = nxt
    observed = abs(2 * w - total)
    return min(1.0, sum(c for s, c in dist.items() if abs(2 * s - total) >= observed) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [NAN] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def median(xs):
    return statistics.median(xs) if xs else NAN


def sign(x):
    return 0 if (x == 0 or math.isnan(x)) else (1 if x > 0 else -1)


def sd(xs):
    return statistics.stdev(xs) if len(xs) > 1 else NAN


def bootstrap_ci(d):
    rng = random.Random(BOOT_SEED)
    n = len(d)
    means = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAP))
    return means[int(0.05 * BOOTSTRAP)], means[math.ceil(0.95 * BOOTSTRAP) - 1]


def kruskal(groups):
    values = sorted((v, g) for g, xs in enumerate(groups) for v in xs)
    N = len(values)
    if N < 2 or sum(1 for xs in groups if xs) < 2:
        return NAN, NAN
    ranks, i, ties = [0.0] * N, 0, 0.0
    while i < N:
        j = i
        while j + 1 < N and values[j + 1][0] == values[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j + 2) / 2
        ties += (j - i + 1) ** 3 - (j - i + 1)
        i = j + 1
    sums = [0.0] * len(groups)
    for (v, g), r in zip(values, ranks):
        sums[g] += r
    H = 12 / (N * (N + 1)) * sum(s * s / len(xs) for s, xs in zip(sums, groups) if xs) - 3 * (N + 1)
    correction = 1 - ties / (N ** 3 - N)
    H = H / correction if correction > 0 else NAN
    df = sum(1 for xs in groups if xs) - 1
    p = math.exp(-H / 2) if df == 2 else math.erfc(math.sqrt(H / 2)) if df == 1 else NAN
    return H, p


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, alpha=0.05):
    def solve(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p), alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: -binom_cdf(k, n, p), -alpha / 2)
    one_sided = 1 - alpha ** (1 / n) if k == 0 else NAN
    return lower, upper, one_sided


def fit_models(x, y):
    """Least-squares fits; AIC = n ln(RSS/n) + 2k. Returns {model: (aic, params)}."""
    n = len(x)
    if n < 4:
        return {}

    def linear(u):
        mu, my = statistics.fmean(u), statistics.fmean(y)
        suu = sum((a - mu) ** 2 for a in u)
        b = sum((a - mu) * (c - my) for a, c in zip(u, y)) / suu if suu else 0.0
        a0 = my - b * mu
        return sum((c - a0 - b * a) ** 2 for a, c in zip(u, y)), (a0, b)

    def aic(rss, k):
        return n * math.log(max(rss, 1e-12) / n) + 2 * k

    my = statistics.fmean(y)
    fits = {"constant": (aic(sum((c - my) ** 2 for c in y), 1), (my,))}
    rss, p = linear(x)
    fits["linear"] = (aic(rss, 2), p)
    rss, p = linear([math.log(a) for a in x])
    fits["logarithmic"] = (aic(rss, 2), p)
    best = None
    span = max(x) - min(x)
    for i in range(200):
        s = span * 10 ** (-2 + 4 * i / 199)
        rss, (c, a) = linear([1 - math.exp(-(a_ - min(x)) / s) for a_ in x])
        if best is None or rss < best[0]:
            best = (rss, (c, a, s))
    fits["saturating_exponential"] = (aic(best[0], 3), best[1])
    return fits


# ---------------------------------------------------------------- tests

def compare(values, seeds, blocks, variant, comparisons, endpoints, forced):
    """Paired tests for the given comparisons and endpoints; Holm across all tests of this call.
    The reference cell supplies Glass's delta and the equivalence bound."""
    rows = []
    for claim, arm, ref in comparisons:
        for e in endpoints:
            pairs = [(s, values[(arm, s)][e], values[(ref, s)][e]) for s in seeds
                     if (arm, s) in values and (ref, s) in values
                     and not math.isnan(values[(arm, s)][e]) and not math.isnan(values[(ref, s)][e])]
            d = [a - b for _, a, b in pairs]
            refs = [b for _, _, b in pairs]
            row = dict(variant=variant, claim=claim, arm=arm, reference=ref, endpoint=e, n=len(d),
                       mean_difference=statistics.fmean(d) if d else NAN, median_difference=median(d),
                       median_block_A=median([a - b for s, a, b in pairs if s in blocks[0]]),
                       median_block_B=median([a - b for s, a, b in pairs if s in blocks[1]]),
                       reference_sd=sd(refs), p=wilcoxon(d) if d else NAN)
            row["glass_delta"] = row["mean_difference"] / row["reference_sd"] if row["reference_sd"] else NAN
            lo, hi = bootstrap_ci(d) if d else (NAN, NAN)
            bound = EQUIVALENCE_SD * row["reference_sd"] if not math.isnan(row["reference_sd"]) else NAN
            row.update(ci90_low=lo, ci90_high=hi, equivalence_bound=bound)
            row["forced_inconclusive"] = forced.get((claim, e), "")
            rows.append(row)
    adjusted = holm([1.0 if math.isnan(r["p"]) else r["p"] for r in rows])
    for r, p in zip(rows, adjusted):
        r["p_holm"] = p
        same = sign(r["median_block_A"]) == sign(r["median_block_B"]) != 0
        differs = p < ALPHA and same
        equivalent = (not math.isnan(r["ci90_low"]) and not math.isnan(r["equivalence_bound"]) and
                      -r["equivalence_bound"] <= r["ci90_low"] and r["ci90_high"] <= r["equivalence_bound"])
        r["blocks_agree"] = same
        r["direction"] = sign(r["median_block_A"]) if differs else 0
        if r["forced_inconclusive"]:
            r["outcome"] = "inconclusive"
        elif differs:
            r["outcome"] = "differs"
        elif equivalent:
            r["outcome"] = "equivalent"
        else:
            r["outcome"] = "inconclusive"
    return rows


def claim_outcomes(rows, comparisons):
    out = []
    for claim, arm, ref in comparisons:
        mine = [r for r in rows if r["claim"] == claim]
        if any(r["outcome"] == "differs" for r in mine):
            outcome = "supported"
        elif mine and all(r["outcome"] == "equivalent" for r in mine):
            outcome = "no detectable effect at this scale"
        else:
            outcome = "inconclusive"
        out.append(dict(claim=claim, arm=arm, reference=ref, outcome=outcome,
                        differs=",".join(r["endpoint"] for r in mine if r["outcome"] == "differs"),
                        equivalent=",".join(r["endpoint"] for r in mine if r["outcome"] == "equivalent"),
                        inconclusive=",".join(r["endpoint"] for r in mine if r["outcome"] == "inconclusive")))
    return out


def neutral_expectation(tests, values, seeds):
    """Rule 6: for each endpoint that differs, compare run-minus-shadow between the same cells."""
    out = []
    for r in tests:
        if r["outcome"] != "differs" or r["endpoint"] not in ENDPOINTS:
            continue
        d = []
        for s in seeds:
            x, y = values.get((r["arm"], s)), values.get((r["reference"], s))
            if x is None or y is None:
                continue
            dx = x["primary"][r["endpoint"]] - x["shadow"][r["endpoint"]]
            dy = y["primary"][r["endpoint"]] - y["shadow"][r["endpoint"]]
            if not (math.isnan(dx) or math.isnan(dy)):
                d.append(dx - dy)
        p = wilcoxon(d) if d else NAN
        beyond = p < ALPHA and sign(median(d)) == sign(r["median_difference"]) != 0
        out.append(dict(claim=r["claim"], endpoint=r["endpoint"], n=len(d), median_difference=median(d), p=p,
                        label="beyond the neutral expectation" if beyond else "matched by the shadow"))
    return out


def pattern(primary_rows, mechanism_rows, claim):
    """Pattern rule of the brief for one access arm."""
    outcome = {r["endpoint"]: r for r in primary_rows + mechanism_rows if r["claim"] == claim}

    def consistent(directions):
        hits = [e for e in directions if e in outcome and outcome[e]["outcome"] == "differs"]
        towards = [e for e in hits if outcome[e]["direction"] == directions[e]]
        against = [e for e in hits if outcome[e]["direction"] == -directions[e]]
        return bool(towards) and not against, towards, against

    buffer_ok, buffer_for, buffer_against = consistent(BUFFER)
    raw_ok, raw_for, raw_against = consistent(RAW)
    label = ("both" if buffer_ok and raw_ok else "buffer-consistent" if buffer_ok else
             "raw-consistent" if raw_ok else "neither")
    return dict(claim=claim, pattern=label, buffer_towards=",".join(buffer_for),
                buffer_against=",".join(buffer_against), raw_towards=",".join(raw_for),
                raw_against=",".join(raw_against))


# ---------------------------------------------------------------- mechanism endpoints

def sampled_levels(cfg):
    """M4 sampling: every eighth window timepoint from the first, and the last."""
    levels = [L for L in window(cfg) if (L - cfg["start"]) % (8 * cfg["step"]) == 0]
    return levels + ([cfg["end"]] if cfg["end"] not in levels else [])


def neutrality_endpoint(w, cfg, column):
    """Mean over sampled, evaluated, non-empty levels of the n_pass-weighted neutrality in F(A)."""
    per_level = []
    for L in sampled_levels(cfg):
        row = w.points.get(("material", cfg["t"], L))
        if row is None or int(row["eval_tick"]) < 0:
            continue
        F = w.filtered.get(("material", cfg["t"], L), {})
        if not F:
            continue
        total = weight = 0.0
        for g, n in F.items():
            x = w.neutrality.get(g)
            if x is None:
                raise ValueError(f"{w.name}: no neutrality for {g} at level {L}")
            total += n * int(x[column]) / int(x["neighbors"])
            weight += n
        per_level.append(total / weight)
    return statistics.fmean(per_level) if per_level else NAN


def persistence(m, cfg):
    """M5: mean run of consecutive evaluated window timepoints that a genotype stays in F(A)."""
    runs, current = [], {}
    for L in window(cfg):
        s = m[L]
        present = set(s["set"]) if s is not None else set()
        for g in list(current):
            if g not in present:
                runs.append(current.pop(g))
        for g in present:
            current[g] = current.get(g, 0) + 1
    runs += list(current.values())
    return statistics.fmean(runs) if runs else NAN


def mechanism_values(w, m, cfg):
    i = w.info
    births, deaths = num(i["births"]), num(i["deaths"])
    subst = num(i["substitution_newborn_deaths"])
    return dict(M1=num(i["substitution_newborn_deaths_with_birth"]) / subst if subst else NAN,
                M2=num(i["substitution_free_novel_births"]) / births * 1e6 if births else NAN,
                M3=num(i["deaths_without_birth"]) / deaths if deaths else NAN,
                M4=neutrality_endpoint(w, cfg, "viable_ordinary"),
                M4_cleared=neutrality_endpoint(w, cfg, "viable_cleared"),
                M5=persistence(m, cfg))


# ---------------------------------------------------------------- strategies and RCCCJD

def strategy_episodes(m, cfg, cls):
    present = [(L, (m[L] is not None and cls in m[L]["classes"])) for L in window(cfg) if m[L] is not None]
    established, first, episodes, losses, absent = False, NAN, 0, 0, 0
    for L, here in present:
        if here:
            if not established:
                established, episodes, absent = True, episodes + 1, 0
                if math.isnan(first):
                    first = L
            absent = 0
        elif established:
            absent += 1
            if absent == 4:
                established, losses = False, losses + 1
    fraction = sum(h for _, h in present) / len(present) if present else NAN
    return dict(established=int(episodes > 0), first_level=first, episodes=episodes, losses=losses, fraction=fraction)


# ---------------------------------------------------------------- pooled thresholds

def bin_lo(b, per_octave):
    return math.ceil(2 ** (b / per_octave) - 1e-9)


def pooled_thresholds(worlds):
    run, shadow, amax = {}, {}, 0
    for w in worlds:
        amax = max(amax, num(w.info["a_max"]))
        for r in w.collapsed:
            b = int(r["bin"]) // 8
            run[b] = run.get(b, 0) + float(r["run_count"])
            shadow[b] = shadow.get(b, 0) + float(r["shadow_count"])
    tr, ts = sum(run.values()), sum(shadow.values())
    astar, sign0 = NAN, 0
    for b in sorted(set(run) | set(shadow)):
        s = sign(run.get(b, 0) / tr - shadow.get(b, 0) / ts)
        if not s:
            continue
        if not sign0:
            sign0 = s
        elif s != sign0:
            astar = bin_lo(b, 8)
            break
    return astar, astar - 0.05 * (amax - astar), astar + 0.05 * (amax - astar), amax


def pooled_p4(w, a0, a1):
    """A_new under pooled thresholds from the stored fine-bin weight sums, prorated within a bin."""
    if math.isnan(a0):
        return NAN
    total = 0.0
    for r in w.collapsed:
        b = int(r["bin"])
        lo, hi = bin_lo(b, 64), bin_lo(b + 1, 64) - 1
        hi = max(hi, lo)
        inside = max(0, min(hi, math.floor(a1)) - max(lo, math.ceil(a0)) + 1)
        total += float(r["run_weight_sum"]) * inside / (hi - lo + 1)
    return total


# ---------------------------------------------------------------- output

def fmt(v):
    if isinstance(v, float):
        return "nan" if math.isnan(v) else f"{v:.6g}"
    return str(v)


def write(path, rows, columns=None):
    if columns is None:
        columns = list(rows[0]) if rows else []
    with open(path, "w") as f:
        f.write("\t".join(columns) + "\n")
        for r in rows:
            f.write("\t".join(fmt(r.get(c, "")) for c in columns) + "\n")


def md_table(rows, columns):
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines += ["| " + " | ".join(fmt(r.get(c, "")) for c in columns) + " |" for r in rows]
    return "\n".join(lines)


# ---------------------------------------------------------------- RCCCJD and the ledger (descriptive)

def rcccjd_episodes(m, cfg):
    """Establishment and loss levels of the RCCCJD component in F(A), as for strategy classes."""
    present = [(L, RCCCJD in m[L]["set"]) for L in window(cfg) if m[L] is not None]
    established, absent, first_absent, events = False, 0, None, []
    for L, here in present:
        if here:
            if not established:
                established = True
                events.append(("establish", L))
            absent = 0
        elif established:
            absent += 1
            if absent == 1:
                first_absent = L
            if absent == 4:
                established = False
                events.append(("loss", first_absent))
    fraction = sum(h for _, h in present) / len(present) if present else NAN
    return events, fraction


def ledger_summary(w):
    """Per-world sums of the mechanism ledger, for births, abandoned divisions and RCCCJD births."""
    out = {}
    groups = {"birth": lambda r: r["outcome"] == "birth", "failed": lambda r: r["outcome"] == "failed_division",
              "died": lambda r: r["outcome"] == "death",
              "focus_birth": lambda r: r["outcome"] == "birth" and r["focus"] == "1",
              "focus_failed": lambda r: r["outcome"] == "failed_division" and r["focus"] == "1"}
    fetch_cols = ("fetch_living", "fetch_own_reservation_written", "fetch_own_reservation_unwritten",
                  "fetch_other_reservation_written", "fetch_other_reservation_unwritten", "fetch_free")
    byte_cols = ("bytes_own", "bytes_living", "bytes_own_reservation_written", "bytes_own_reservation_unwritten",
                 "bytes_other_reservation_written", "bytes_other_reservation_unwritten", "bytes_free")
    for g, keep in groups.items():
        rows = [r for r in w.ledger if keep(r)]
        n = sum(int(r["attempts"]) for r in rows)
        out[f"{g}_attempts"] = n
        out[f"{g}_mean_substitutions"] = (sum(int(r["substitutions"]) * int(r["attempts"]) for r in rows) / n
                                          if n else NAN)
        out[f"{g}_with_substitution"] = (sum(int(r["attempts"]) for r in rows if int(r["substitutions"]) > 0) / n
                                         if n else NAN)
        for c in ("with_residue_bytes", "with_residue_fetch", "with_fetch", "with_own_reservation_fetch"):
            out[f"{g}_{c}"] = sum(int(r[c]) for r in rows) / n if n else NAN
        written = sum(int(r["written"]) for r in rows)
        out[f"{g}_residue_byte_share"] = sum(int(r["residue_bytes"]) for r in rows) / written if written else NAN
        fetched = sum(int(r[c]) for r in rows for c in fetch_cols)
        out[f"{g}_fetched"] = fetched
        for c in fetch_cols:
            out[f"{g}_{c}_share"] = sum(int(r[c]) for r in rows) / fetched if fetched else NAN
        for c in byte_cols:
            out[f"{g}_{c}_share"] = sum(int(r[c]) for r in rows) / written if written else NAN
    rows = [r for r in w.ledger if r["outcome"] == "failed_division" and r["focus"] == "1" and
            int(r["substitutions"]) > 0]
    out["focus_failed_substituted_own_reservation_fetch"] = sum(int(r["with_own_reservation_fetch"]) for r in rows)
    return out


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("set", choices=tuple(SETTINGS))
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--unchecked", action="store_true", help="skip the seed-range check (code tests only)")
    a = parser.parse_args()
    cfg = SETTINGS[a.set]
    worlds = [World(d) for d in sorted((a.results / a.set).iterdir()) if d.is_dir() and not d.name.startswith(".")]
    seeds = sorted({w.seed for w in worlds})
    if not a.unchecked:
        expected = {(c, s) for c in cfg["cells"] for s in cfg["seeds"]}
        found = {(w.cell, w.seed) for w in worlds}
        if found != expected:
            raise SystemExit(f"missing or extra worlds: {sorted(expected ^ found)[:5]}")
    cells = [c for c in cfg["cells"] if any(w.cell == c for w in worlds)]
    half = len(seeds) // 2
    blocks = (set(seeds[:half]), set(seeds[half:]))
    out = a.results / cfg["out"]
    out.mkdir(parents=True, exist_ok=True)
    t = cfg["t"]

    def informative(w, g):
        return informative_mask(g, w.assays[("material", g)])

    variants = {
        "primary": ("material", t, None, "material"),
        "shadow": ("shadow", t, None, None),
        "executor": ("executor", t, None, "executor"),
        "informative_sites": ("material", t, informative, None),
    }
    for s in cfg["sensitivity_t"]:
        variants[f"t{s}"] = ("material", s, None, None)

    endpoint_rows, values, series_cache, strategy_rows, level_rows = [], {}, {}, [], []
    ledger_rows, rcccjd_rows, rcccjd_events = [], [], []
    for w in worlds:
        key = (w.cell, w.seed)
        values[key] = {}
        for v, (series, tt, comp, assay_series) in variants.items():
            m = modes(w, cfg, series, tt, comp, assay_series)
            series_cache[(key, v)] = m
            values[key][v] = modes_endpoints(w, cfg, m)
        values[key]["primary"]["P4"] = bedau_p4(w, "A_new")
        values[key]["shadow"]["P4"] = bedau_p4(w, "shadow_A_new")
        m = series_cache[(key, "primary")]
        values[key]["primary"].update(mechanism_values(w, m, cfg))
        reached = [m[L] for L in window(cfg) if m[L] is not None]
        late = [m[L] for L in window(cfg) if L >= cfg["stagnation_from"]]
        alive = not w.extinct
        evo_stagnant = ("unreached" if any(s is None for s in late) else
                        int(all(s["novelty"] == 0 for s in late))) if alive else 0
        b = w.bedau
        row = dict(cell=w.cell, arm=w.arm, reclamation=w.reclamation, seed=w.seed,
                   block="A" if w.seed in blocks[0] else "B", status=w.info["status"],
                   extinction_tick=int(w.info["extinction_tick"]),
                   demographic_stagnation=int(w.info["status"] == "stagnant"),
                   evolutionary_stagnation=evo_stagnant, unreached=int(values[key]["primary"]["unreached"]),
                   reached_timepoints=values[key]["primary"]["reached"])
        for e in ENDPOINTS:
            row[e] = values[key]["primary"][e]
            row[f"shadow_{e}"] = values[key]["shadow"][e]
            row[f"run_minus_shadow_{e}"] = row[e] - row[f"shadow_{e}"]
        for e in MECHANISMS + ("M4_cleared",):
            row[e] = values[key]["primary"][e]
        row["complexity_max"] = max((s["complexity"] for s in reached), default=NAN)
        row["complexity_mean"] = statistics.fmean(s["complexity"] for s in reached) if reached else NAN
        for col in ("D", "A_cum", "mean_cum", "median_cum", "population", "shadow_D", "shadow_A_cum",
                    "shadow_mean_cum", "shadow_median_cum"):
            row[f"mean_{col}"] = statistics.fmean(num(r[col]) for r in b) if b else NAN
        for col in ("births", "variation_births", "substitution_births", "substitution_free_variation_births",
                    "substitution_free_novel_births",
                    "living_end", "mean_interval_material", "mean_interval_executor", "G_material", "G_shadow",
                    "a_star", "a0", "a1", "a_max", "assayed", "neutrality_genotypes", "pass1_seconds",
                    "pass2_seconds"):
            row[col] = num(w.info[col])
        births = row["births"]
        row["variation_share"] = row["variation_births"] / births if births else NAN
        row["substitution_share"] = row["substitution_births"] / births if births else NAN
        row["substitution_free_variation_share"] = row["substitution_free_variation_births"] / births if births else NAN
        row["binomial_substitution_share"] = 1 - (1 - SUBSTITUTION_PPM / 1e6) ** 6
        endpoint_rows.append(row)
        for cls in CLASSES:
            strategy_rows.append(dict(cell=w.cell, seed=w.seed, cls=cls, **strategy_episodes(m, cfg, cls)))
        events, fraction = rcccjd_episodes(m, cfg)
        rcccjd_rows.append(dict(cell=w.cell, seed=w.seed, established=int(any(k == "establish" for k, _ in events)),
                                episodes=sum(k == "establish" for k, _ in events),
                                losses=sum(k == "loss" for k, _ in events), fraction=fraction))
        for kind, L in events:
            c = w.census.get(L, {})
            focus = num(c.get("focus"))
            rcccjd_events.append(dict(cell=w.cell, seed=w.seed, event=kind, level=L, tick=c.get("tick", ""),
                                      alive=num(c.get("alive")), free_with_bytes=num(c.get("free_with_bytes")),
                                      carriers=focus,
                                      bearing_living=num(c.get("focus_bearing_living")) / focus if focus else NAN,
                                      bearing_reserved=num(c.get("focus_bearing_reserved")) / focus if focus else NAN,
                                      bearing_free_with_bytes=num(c.get("focus_bearing_free_with_bytes")) / focus
                                      if focus else NAN,
                                      bearing_free_empty=num(c.get("focus_bearing_free_empty")) / focus if focus else NAN,
                                      residue_neighbors_per_carrier=num(c.get("focus_neighbors_free_with_bytes")) / focus
                                      if focus else NAN,
                                      carrier_neighbors_per_carrier=num(c.get("focus_neighbors_focus")) / focus
                                      if focus else NAN))
        ledger_rows.append(dict(cell=w.cell, seed=w.seed, **ledger_summary(w)))
        for L in window(cfg):
            s, sh = m[L], series_cache[(key, "shadow")][L]
            level_rows.append(dict(cell=w.cell, seed=w.seed, level=L, reached=int(s is not None),
                                   change=s["change"] if s else NAN, novelty=s["novelty"] if s else NAN,
                                   ecology=s["ecology"] if s else NAN, complexity=s["complexity"] if s else NAN,
                                   richness=s["richness"] if s else NAN,
                                   shadow_change=sh["change"] if sh else NAN,
                                   shadow_novelty=sh["novelty"] if sh else NAN,
                                   shadow_ecology=sh["ecology"] if sh else NAN))
    write(out / "endpoints.tsv", endpoint_rows)
    write(out / "levels.tsv", level_rows)
    write(out / "strategy_worlds.tsv", strategy_rows)
    write(out / "rcccjd_worlds.tsv", rcccjd_rows)
    write(out / "rcccjd_events.tsv", rcccjd_events,
          ["cell", "seed", "event", "level", "tick", "alive", "free_with_bytes", "carriers", "bearing_living",
           "bearing_reserved", "bearing_free_with_bytes", "bearing_free_empty", "residue_neighbors_per_carrier",
           "carrier_neighbors_per_carrier"])
    write(out / "ledger_worlds.tsv", ledger_rows)

    # Strategy counts per cell (M6, descriptive).
    strategy_summary = []
    for cell in cells:
        for cls in CLASSES:
            rows = [r for r in strategy_rows if r["cell"] == cell and r["cls"] == cls]
            k = sum(r["established"] for r in rows)
            lo, hi, upper = clopper_pearson(k, len(rows)) if rows else (NAN, NAN, NAN)
            firsts = [r["first_level"] for r in rows if r["established"]]
            fractions = [r["fraction"] for r in rows if not math.isnan(r["fraction"])]
            strategy_summary.append(dict(cell=cell, cls=cls, worlds=len(rows), established=k, ci95_low=lo,
                                         ci95_high=hi, one_sided_upper95=upper, median_first_level=median(firsts),
                                         episodes=sum(r["episodes"] for r in rows),
                                         losses=sum(r["losses"] for r in rows),
                                         mean_fraction=statistics.fmean(fractions) if fractions else NAN))
    write(out / "strategies.tsv", strategy_summary)

    # Cell summaries, including the variation decomposition and ledger means (descriptive).
    cell_rows = []
    for cell in cells:
        rows = [r for r in endpoint_rows if r["cell"] == cell]
        living = [r for r in rows if r["extinction_tick"] < 0]
        s = dict(cell=cell, worlds=len(rows), extinct=len(rows) - len(living),
                 demographic_stagnation=sum(r["demographic_stagnation"] for r in rows),
                 evolutionary_stagnation=sum(r["evolutionary_stagnation"] == 1 for r in rows),
                 unreached=sum(r["unreached"] for r in living),
                 unreached_fraction=(sum(r["unreached"] for r in living) / len(living)) if living else NAN)
        for e in (ENDPOINTS + tuple(f"shadow_{e}" for e in ENDPOINTS) + MECHANISMS +
                  ("M4_cleared", "complexity_max", "mean_D", "mean_population", "variation_share",
                   "substitution_share", "substitution_free_variation_share")):
            xs = [r[e] for r in rows if not math.isnan(r[e])]
            s[f"median_{e}"] = median(xs)
        s["binomial_substitution_share"] = 1 - (1 - SUBSTITUTION_PPM / 1e6) ** 6
        lrows = [r for r in ledger_rows if r["cell"] == cell]
        for col in ("birth_residue_byte_share", "birth_with_residue_bytes", "birth_with_residue_fetch",
                    "birth_with_fetch", "birth_mean_substitutions", "failed_mean_substitutions",
                    "failed_with_substitution", "birth_with_substitution", "died_mean_substitutions",
                    "focus_birth_attempts", "focus_birth_with_residue_fetch", "focus_birth_with_own_reservation_fetch",
                    "focus_birth_fetch_living_share", "focus_birth_fetch_own_reservation_written_share",
                    "focus_birth_fetch_own_reservation_unwritten_share",
                    "focus_birth_fetch_other_reservation_written_share",
                    "focus_birth_fetch_other_reservation_unwritten_share", "focus_birth_fetch_free_share",
                    "focus_failed_attempts", "focus_failed_with_substitution",
                    "focus_failed_substituted_own_reservation_fetch"):
            xs = [r[col] for r in lrows if not (isinstance(r[col], float) and math.isnan(r[col]))]
            s[f"mean_{col}"] = statistics.fmean(xs) if xs else NAN
        rc = [r for r in rcccjd_rows if r["cell"] == cell]
        s["rcccjd_established"] = sum(r["established"] for r in rc)
        s["rcccjd_episodes"] = sum(r["episodes"] for r in rc)
        s["rcccjd_losses"] = sum(r["losses"] for r in rc)
        s["rcccjd_mean_fraction"] = statistics.fmean(r["fraction"] for r in rc if not math.isnan(r["fraction"])) \
            if rc else NAN
        cell_rows.append(s)
    write(out / "cells.tsv", cell_rows)

    if a.set == "scale":
        summary = ["# dead-code-01 scale check (descriptive)", "",
                   "Generated by analyze.py; no tests are run on the scale check.", "",
                   md_table(cell_rows, list(cell_rows[0])), "", "## Strategies", "",
                   md_table([r for r in strategy_summary if r["cls"] in DEPENDENT + ("independent",)],
                            ["cell", "cls", "worlds", "established", "ci95_low", "ci95_high", "episodes", "losses",
                             "mean_fraction"])]
        (out / "summary.md").write_text("\n".join(summary) + "\n")
        return

    # Forced inconclusive: more than 10% unreached living worlds in a cell (P1-P3 and M5 only).
    def forced_for(variant, comparisons, endpoints):
        frac = {}
        for cell in cells:
            living = [k for k in values if k[0] == cell and not
                      next(w for w in worlds if (w.cell, w.seed) == k).extinct]
            frac[cell] = (sum(values[k][variant]["unreached"] for k in living) / len(living)) if living else 0.0
        forced = {}
        for claim, arm, ref in comparisons:
            if frac.get(arm, 0) > UNREACHED_LIMIT or frac.get(ref, 0) > UNREACHED_LIMIT:
                for e in endpoints:
                    forced[(claim, e)] = "unreached"
        return forced

    flat = {k: v["primary"] for k, v in values.items()}
    tests = compare(flat, seeds, blocks, "primary", CLAIMS, ENDPOINTS, forced_for("primary", CLAIMS, ("P1", "P2", "P3")))
    write(out / "tests.tsv", tests)
    claims = claim_outcomes(tests, CLAIMS)
    write(out / "claims.tsv", claims)
    neutral = neutral_expectation(tests, values, seeds)
    write(out / "neutral.tsv", neutral, ["claim", "endpoint", "n", "median_difference", "p", "label"])

    # Replication of the access study's C3 on the new seeds, Holm over its own four tests.
    replication = compare(flat, seeds, blocks, "replication", REPLICATION, ENDPOINTS,
                          forced_for("primary", REPLICATION, ("P1", "P2", "P3")))
    write(out / "replication.tsv", replication)
    replication_claims = claim_outcomes(replication, REPLICATION)
    write(out / "replication_claims.tsv", replication_claims)
    replication_neutral = neutral_expectation(replication, values, seeds)
    write(out / "replication_neutral.tsv", replication_neutral, ["claim", "endpoint", "n", "median_difference", "p",
                                                                 "label"])

    # Mechanism family: M1-M5 for D1 and D2, Holm over these 10 tests.
    mechanisms = compare(flat, seeds, blocks, "mechanism", CLAIMS, MECHANISMS,
                         forced_for("primary", CLAIMS, ("M5",)))
    write(out / "mechanisms.tsv", mechanisms)
    patterns = [pattern(tests, mechanisms, claim) for claim, _, _ in CLAIMS]
    write(out / "patterns.tsv", patterns)

    # Descriptive: the D2 effect minus the D1 effect per seed, and M4 against its residue-cleared value.
    contrasts = []
    for e in ENDPOINTS + MECHANISMS:
        d = []
        for s in seeds:
            try:
                v = ((flat[("read_fetch-retain", s)][e] - flat[("read_fetch-empty", s)][e]) -
                     (flat[("read-retain", s)][e] - flat[("read-empty", s)][e]))
            except KeyError:
                continue
            if not math.isnan(v):
                d.append(v)
        contrasts.append(dict(contrast="D2_minus_D1", endpoint=e, n=len(d), median_difference=median(d),
                              p=wilcoxon(d) if d else NAN))
    for cell in ("read-retain", "read_fetch-retain"):
        d = [flat[(cell, s)]["M4"] - flat[(cell, s)]["M4_cleared"] for s in seeds
             if (cell, s) in flat and not math.isnan(flat[(cell, s)]["M4"] - flat[(cell, s)]["M4_cleared"])]
        contrasts.append(dict(contrast=f"M4_minus_cleared_{cell}", endpoint="M4", n=len(d),
                              median_difference=median(d), p=wilcoxon(d) if d else NAN))
    write(out / "contrasts.tsv", contrasts)

    # Sensitivity analyses: same rules, Holm within each variant (descriptive).
    sensitivity = []
    for v in [k for k in variants if k not in ("primary", "shadow")]:
        sensitivity += compare({k: x[v] for k, x in values.items()}, seeds, blocks, v, CLAIMS, ("P1", "P2", "P3"),
                               forced_for(v, CLAIMS, ("P1", "P2", "P3")))
    astar, a0, a1, amax = pooled_thresholds(worlds)
    pooled = {(w.cell, w.seed): {"P4": pooled_p4(w, a0, a1)} for w in worlds}
    sensitivity += compare(pooled, seeds, blocks, "pooled_thresholds", CLAIMS, ("P4",), {})
    write(out / "sensitivity.tsv", sensitivity)
    sens_claims = []
    for v in sorted({r["variant"] for r in sensitivity}):
        for c in claim_outcomes([r for r in sensitivity if r["variant"] == v], CLAIMS):
            sens_claims.append(dict(variant=v, **c))
    write(out / "sensitivity_claims.tsv", sens_claims)

    # Boundedness, descriptive: cell means over levels, and per-world cumulative novelty.
    bounded = []
    metrics = ("change", "cumulative_novelty", "ecology", "complexity")
    for cell in cells:
        per_level, world_fits = {}, {}
        for w in [w for w in worlds if w.cell == cell]:
            m = series_cache[((w.cell, w.seed), "primary")]
            cumulative, xs, ys = 0, [], []
            for L in window(cfg):
                if m[L] is None:
                    continue
                cumulative += m[L]["novelty"]
                vals = dict(change=m[L]["change"], cumulative_novelty=cumulative, ecology=m[L]["ecology"],
                            complexity=m[L]["complexity"])
                for k, x in vals.items():
                    per_level.setdefault((k, L), []).append(x)
                xs.append(L); ys.append(cumulative)
            fits = fit_models(xs, ys)
            if fits:
                best = min(fits, key=lambda k: fits[k][0])
                world_fits[best] = world_fits.get(best, 0) + 1
        for k in metrics:
            xs = [L for L in window(cfg) if (k, L) in per_level]
            ys = [statistics.fmean(per_level[(k, L)]) for L in xs]
            fits = fit_models(xs, ys)
            if not fits:
                continue
            best = min(fits, key=lambda name: fits[name][0])
            row = dict(cell=cell, metric=f"cell_mean_{k}", points=len(xs), best=best)
            for name, (aic_, params) in fits.items():
                row[f"aic_{name}"] = aic_
                row[f"params_{name}"] = ";".join(fmt(float(p)) for p in params)
            bounded.append(row)
        bounded.append(dict(cell=cell, metric="world_cumulative_novelty_best_counts", points=sum(world_fits.values()),
                            best=";".join(f"{k}={v}" for k, v in sorted(world_fits.items()))))
    columns = ["cell", "metric", "points", "best"] + [f"{p}_{n}" for n in ("constant", "linear", "logarithmic",
                                                                            "saturating_exponential")
                                                      for p in ("aic", "params")]
    write(out / "boundedness.tsv", bounded, columns)

    test_cols = ["claim", "endpoint", "n", "median_difference", "median_block_A", "median_block_B", "glass_delta", "p",
                 "p_holm", "ci90_low", "ci90_high", "equivalence_bound", "outcome"]
    summary = [
        "# dead-code-01 primary analysis", "",
        "Generated by analyze.py from results/primary under the rules frozen in protocol.md.", "",
        "## Claims D1 and D2", "", md_table(claims, ["claim", "arm", "reference", "outcome", "differs", "equivalent",
                                                    "inconclusive"]), "",
        "## Tests (Holm over 8)", "", md_table(tests, test_cols), "",
        "## Neutral expectation", "", md_table(neutral, ["claim", "endpoint", "n", "median_difference", "p", "label"])
        if neutral else "No endpoint differs, so no neutral comparison applies.", "",
        "## Mechanism family (Holm over 10)", "", md_table(mechanisms, test_cols), "",
        "## Patterns", "", md_table(patterns, list(patterns[0])), "",
        "## Replication of C3 (Holm over 4, reported separately)", "",
        md_table(replication_claims, ["claim", "arm", "reference", "outcome", "differs", "equivalent",
                                      "inconclusive"]), "",
        md_table(replication, test_cols), "",
        md_table(replication_neutral, ["claim", "endpoint", "n", "median_difference", "p", "label"])
        if replication_neutral else "No replication endpoint differs.", "",
        "## Contrasts (descriptive, uncorrected)", "", md_table(contrasts, list(contrasts[0])), "",
        "## Cells", "", md_table(cell_rows, list(cell_rows[0])), "",
        "## Strategies (descriptive)", "",
        md_table(strategy_summary, ["cell", "cls", "worlds", "established", "ci95_low", "ci95_high",
                                    "one_sided_upper95", "median_first_level", "episodes", "losses",
                                    "mean_fraction"]), "",
        "## Sensitivity analyses (descriptive)", "",
        f"Pooled thresholds: a* = {fmt(astar)}, a0 = {fmt(a0)}, a1 = {fmt(a1)}, a_max = {fmt(amax)}.", "",
        md_table(sens_claims, ["variant", "claim", "outcome", "differs", "equivalent", "inconclusive"]), "",
    ]
    (out / "summary.md").write_text("\n".join(summary) + "\n")


if __name__ == "__main__":
    main()
