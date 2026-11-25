"""Compute the preregistered endpoints, tests and descriptive tables of access-dynamics-01.

  python3 analyze.py primary   # results/primary -> results/analysis
  python3 analyze.py scale     # results/scale -> results/scale-analysis (descriptive only)

The rules implemented here are those of protocol.md and docs/research/access-dynamics-rq.md.
They were frozen with this file before any study seed ran. Only the Python standard library is
used.
"""
import argparse
import csv
import gzip
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("self", "read", "read_fetch")
CLAIMS = (("C1", "read", "self"), ("C2", "read_fetch", "read"), ("C3", "read_fetch", "self"))
ENDPOINTS = ("P1", "P2", "P3", "P4")
CLASSES = ("independent", "read_requiring", "fetch_requiring", "both_requiring", "either_sufficient",
           "template_only", "other")
DEPENDENT = ("read_requiring", "fetch_requiring", "both_requiring", "either_sufficient")
SETTINGS = {
    "primary": dict(t=1024, step=256, start=1024, end=16384, stagnation_from=12288, seeds=range(30001, 30033),
                    sensitivity_t=(256, 2048), out="analysis"),
    "scale": dict(t=4096, step=1024, start=4096, end=16384, stagnation_from=12288, seeds=range(30101, 30109),
                  sensitivity_t=(), out="scale-analysis"),
    # Code test only: short worlds run with --filter 64 16 1024 --sensitivity 16,128.
    "test": dict(t=64, step=16, start=64, end=1024, stagnation_from=768, seeds=(), sensitivity_t=(16, 128),
                 out="test-analysis"),
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
        self.arm, self.seed = self.info["arm"], int(self.info["seed"])
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


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NAN
    return v


# ---------------------------------------------------------------- MODES

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
        }
        if assay_series:
            infos = []
            for g in raw:
                a = w.assays.get((assay_series, g))
                if a is None:
                    raise ValueError(f"{w.name}: no {assay_series} assay for {g} at level {level}")
                infos.append(int(a["informative"]))
                stats["classes"].add(a["class"])
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

def compare(values, seeds, blocks, variant, endpoints, forced):
    """Paired tests for C1-C3 on the given endpoints; Holm across all tests of this variant."""
    rows = []
    for claim, arm, ref in CLAIMS:
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
        if r["forced_inconclusive"]:
            r["outcome"] = "inconclusive"
        elif differs:
            r["outcome"] = "differs"
        elif equivalent:
            r["outcome"] = "equivalent"
        else:
            r["outcome"] = "inconclusive"
    return rows


def claim_outcomes(rows):
    out = []
    for claim, arm, ref in CLAIMS:
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


# ---------------------------------------------------------------- strategies

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
        expected = {(arm, s) for arm in ARMS for s in cfg["seeds"]}
        found = {(w.arm, w.seed) for w in worlds}
        if found != expected:
            raise SystemExit(f"missing worlds: {sorted(expected - found)[:5]}")
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
    for w in worlds:
        key = (w.arm, w.seed)
        values[key] = {}
        for v, (series, tt, comp, assay_series) in variants.items():
            m = modes(w, cfg, series, tt, comp, assay_series)
            series_cache[(key, v)] = m
            values[key][v] = modes_endpoints(w, cfg, m)
        values[key]["primary"]["P4"] = bedau_p4(w, "A_new")
        values[key]["shadow"]["P4"] = bedau_p4(w, "shadow_A_new")
        m = series_cache[(key, "primary")]
        reached = [m[L] for L in window(cfg) if m[L] is not None]
        late = [m[L] for L in window(cfg) if L >= cfg["stagnation_from"]]
        alive = not w.extinct
        evo_stagnant = ("unreached" if any(s is None for s in late) else
                        int(all(s["novelty"] == 0 for s in late))) if alive else 0
        b = w.bedau
        row = dict(arm=w.arm, seed=w.seed, block="A" if w.seed in blocks[0] else "B", status=w.info["status"],
                   extinction_tick=int(w.info["extinction_tick"]),
                   demographic_stagnation=int(w.info["status"] == "stagnant"),
                   evolutionary_stagnation=evo_stagnant, unreached=int(values[key]["primary"]["unreached"]),
                   reached_timepoints=values[key]["primary"]["reached"])
        for e in ENDPOINTS:
            row[e] = values[key]["primary"][e]
            row[f"shadow_{e}"] = values[key]["shadow"][e]
            row[f"run_minus_shadow_{e}"] = row[e] - row[f"shadow_{e}"]
        row["complexity_max"] = max((s["complexity"] for s in reached), default=NAN)
        row["complexity_mean"] = statistics.fmean(s["complexity"] for s in reached) if reached else NAN
        for col in ("D", "A_cum", "mean_cum", "median_cum", "population", "shadow_D", "shadow_A_cum",
                    "shadow_mean_cum", "shadow_median_cum"):
            row[f"mean_{col}"] = statistics.fmean(num(r[col]) for r in b) if b else NAN
        for col in ("births", "variation_births", "living_end", "mean_interval_material", "mean_interval_executor",
                    "G_material", "G_shadow", "a_star", "a0", "a1", "a_max", "assayed", "pass1_seconds"):
            row[col] = num(w.info[col])
        endpoint_rows.append(row)
        for cls in CLASSES:
            strategy_rows.append(dict(arm=w.arm, seed=w.seed, cls=cls, **strategy_episodes(m, cfg, cls)))
        for L in window(cfg):
            s, sh = m[L], series_cache[(key, "shadow")][L]
            level_rows.append(dict(arm=w.arm, seed=w.seed, level=L, reached=int(s is not None),
                                   change=s["change"] if s else NAN, novelty=s["novelty"] if s else NAN,
                                   ecology=s["ecology"] if s else NAN, complexity=s["complexity"] if s else NAN,
                                   richness=s["richness"] if s else NAN,
                                   shadow_change=sh["change"] if sh else NAN,
                                   shadow_novelty=sh["novelty"] if sh else NAN,
                                   shadow_ecology=sh["ecology"] if sh else NAN))
    write(out / "endpoints.tsv", endpoint_rows)
    write(out / "levels.tsv", level_rows)
    write(out / "strategy_worlds.tsv", strategy_rows)

    # Strategy counts per arm.
    strategy_summary = []
    for arm in ARMS:
        for cls in CLASSES:
            rows = [r for r in strategy_rows if r["arm"] == arm and r["cls"] == cls]
            k = sum(r["established"] for r in rows)
            lo, hi, upper = clopper_pearson(k, len(rows)) if rows else (NAN, NAN, NAN)
            firsts = [r["first_level"] for r in rows if r["established"]]
            strategy_summary.append(dict(arm=arm, cls=cls, worlds=len(rows), established=k, ci95_low=lo, ci95_high=hi,
                                         one_sided_upper95=upper, median_first_level=median(firsts),
                                         episodes=sum(r["episodes"] for r in rows),
                                         losses=sum(r["losses"] for r in rows),
                                         mean_fraction=statistics.fmean(r["fraction"] for r in rows
                                                                        if not math.isnan(r["fraction"]))
                                         if rows else NAN))
    write(out / "strategies.tsv", strategy_summary)

    # Arm summaries.
    arm_rows = []
    for arm in ARMS:
        rows = [r for r in endpoint_rows if r["arm"] == arm]
        living = [r for r in rows if r["extinction_tick"] < 0]
        s = dict(arm=arm, worlds=len(rows), extinct=len(rows) - len(living),
                 demographic_stagnation=sum(r["demographic_stagnation"] for r in rows),
                 evolutionary_stagnation=sum(r["evolutionary_stagnation"] == 1 for r in rows),
                 unreached=sum(r["unreached"] for r in living),
                 unreached_fraction=(sum(r["unreached"] for r in living) / len(living)) if living else NAN)
        for e in ENDPOINTS + tuple(f"shadow_{e}" for e in ENDPOINTS) + ("complexity_max", "mean_D", "mean_population"):
            xs = [r[e] for r in rows if not math.isnan(r[e])]
            s[f"median_{e}"] = median(xs)
        arm_rows.append(s)
    write(out / "arms.tsv", arm_rows)

    if a.set == "scale":
        summary = ["# Scale check (descriptive)", "", "Generated by analyze.py; no tests are run on the scale check.", "",
                   md_table(arm_rows, list(arm_rows[0])), "", "## Strategies", "",
                   md_table([r for r in strategy_summary if r["cls"] in DEPENDENT + ("independent",)],
                            ["arm", "cls", "worlds", "established", "ci95_low", "ci95_high"])]
        (out / "summary.md").write_text("\n".join(summary) + "\n")
        return

    # Forced inconclusive: more than 10% unreached living worlds in an arm (P1-P3 only).
    def forced_for(variant):
        frac = {}
        for arm in ARMS:
            living = [k for k in values if k[0] == arm and not
                      next(w for w in worlds if (w.arm, w.seed) == k).extinct]
            frac[arm] = (sum(values[k][variant]["unreached"] for k in living) / len(living)) if living else 0.0
        forced = {}
        for claim, arm, ref in CLAIMS:
            if frac[arm] > UNREACHED_LIMIT or frac[ref] > UNREACHED_LIMIT:
                for e in ("P1", "P2", "P3"):
                    forced[(claim, e)] = "unreached"
        return forced

    flat = {k: v["primary"] for k, v in values.items()}
    tests = compare(flat, seeds, blocks, "primary", ENDPOINTS, forced_for("primary"))
    write(out / "tests.tsv", tests)
    claims = claim_outcomes(tests)
    write(out / "claims.tsv", claims)

    # Neutral expectation for endpoints that differ.
    neutral = []
    for r in tests:
        if r["outcome"] != "differs":
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
        neutral.append(dict(claim=r["claim"], endpoint=r["endpoint"], n=len(d), median_difference=median(d), p=p,
                            label="beyond the neutral expectation" if beyond else "matched by the shadow"))
    write(out / "neutral.tsv", neutral, ["claim", "endpoint", "n", "median_difference", "p", "label"])

    # Kruskal-Wallis, reported only.
    kw = []
    for e in ENDPOINTS:
        groups = [[flat[(arm, s)][e] for s in seeds if (arm, s) in flat and not math.isnan(flat[(arm, s)][e])]
                  for arm in ARMS]
        H, p = kruskal(groups)
        kw.append(dict(endpoint=e, H=H, p=p, n=sum(map(len, groups))))
    write(out / "kruskal.tsv", kw)

    # Sensitivity analyses: same rules, Holm within each variant.
    sensitivity = []
    for v in [k for k in variants if k not in ("primary", "shadow")]:
        sensitivity += compare({k: x[v] for k, x in values.items()}, seeds, blocks, v, ("P1", "P2", "P3"),
                               forced_for(v))
    astar, a0, a1, amax = pooled_thresholds(worlds)
    pooled = {(w.arm, w.seed): {"P4": pooled_p4(w, a0, a1)} for w in worlds}
    sensitivity += compare(pooled, seeds, blocks, "pooled_thresholds", ("P4",), {})
    write(out / "sensitivity.tsv", sensitivity)
    sens_claims = []
    for v in sorted({r["variant"] for r in sensitivity}):
        for c in claim_outcomes([r for r in sensitivity if r["variant"] == v]):
            sens_claims.append(dict(variant=v, **c))
    write(out / "sensitivity_claims.tsv", sens_claims)

    # Boundedness, descriptive: arm means over levels, and per-world cumulative novelty.
    bounded = []
    metrics = ("change", "cumulative_novelty", "ecology", "complexity")
    for arm in ARMS:
        per_level = {}
        world_fits = {}
        for w in [w for w in worlds if w.arm == arm]:
            m = series_cache[((w.arm, w.seed), "primary")]
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
            row = dict(arm=arm, metric=f"arm_mean_{k}", points=len(xs), best=best)
            for name, (aic_, params) in fits.items():
                row[f"aic_{name}"] = aic_
                row[f"params_{name}"] = ";".join(fmt(float(p)) for p in params)
            bounded.append(row)
        bounded.append(dict(arm=arm, metric="world_cumulative_novelty_best_counts", points=sum(world_fits.values()),
                            best=";".join(f"{k}={v}" for k, v in sorted(world_fits.items()))))
    columns = ["arm", "metric", "points", "best"] + [f"{p}_{n}" for n in ("constant", "linear", "logarithmic",
                                                                           "saturating_exponential")
                                                     for p in ("aic", "params")]
    write(out / "boundedness.tsv", bounded, columns)

    summary = [
        "# access-dynamics-01 primary analysis", "",
        "Generated by analyze.py from results/primary under the rules frozen in protocol.md.", "",
        "## Claims", "", md_table(claims, ["claim", "arm", "reference", "outcome", "differs", "equivalent",
                                         "inconclusive"]), "",
        "## Tests", "", md_table(tests, ["claim", "endpoint", "n", "median_difference", "median_block_A",
                                        "median_block_B", "glass_delta", "p", "p_holm", "ci90_low", "ci90_high",
                                        "equivalence_bound", "outcome"]), "",
        "## Neutral expectation", "", md_table(neutral, ["claim", "endpoint", "n", "median_difference", "p", "label"])
        if neutral else "No endpoint differs, so no neutral comparison applies.", "",
        "## Arms", "", md_table(arm_rows, list(arm_rows[0])), "",
        "## Kruskal-Wallis (reported only)", "", md_table(kw, ["endpoint", "H", "p", "n"]), "",
        "## Strategies (descriptive)", "",
        md_table(strategy_summary, ["arm", "cls", "worlds", "established", "ci95_low", "ci95_high",
                                    "one_sided_upper95", "median_first_level", "episodes", "losses",
                                    "mean_fraction"]), "",
        "## Sensitivity analyses (descriptive)", "",
        f"Pooled thresholds: a* = {fmt(astar)}, a0 = {fmt(a0)}, a1 = {fmt(a1)}, a_max = {fmt(amax)}.", "",
        md_table(sens_claims, ["variant", "claim", "outcome", "differs", "equivalent", "inconclusive"]), "",
    ]
    (out / "summary.md").write_text("\n".join(summary) + "\n")


if __name__ == "__main__":
    main()
