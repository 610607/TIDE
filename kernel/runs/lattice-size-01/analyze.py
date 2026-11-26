"""Compute the preregistered endpoints, tests and descriptive tables of lattice-size-01.

  python3 analyze.py primary   # results/primary -> results/analysis
  python3 analyze.py test      # validation test worlds -> results/validation/test-analysis (code test only)

The rules implemented here are those of protocol.md and docs/research/lattice-size-rq.md. They were
frozen with this file before any study seed ran. Helper statistics (Holm, Kruskal-Wallis,
Clopper-Pearson, entropy) are copied from kernel/runs/dead-code-01/analyze.py. Only the Python
standard library is used.
"""
import argparse
import csv
import gzip
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOCUS = "RCCCJD".encode().hex()
SIZES = (24, 32, 48, 64)
DEPENDENT = ("read_requiring", "fetch_requiring", "both_requiring", "either_sufficient")
ALPHA, UNREACHED_LIMIT, EQUIVALENCE_SD = 0.05, 0.10, 0.5
PERMUTATIONS, BOOTSTRAP, SEED = 100000, 10000, 20261126
NAN = float("nan")
# The test configuration divides every generation count by 16 so that 65,536-tick validation worlds
# exercise each path; it is a code test only.
SETTINGS = {
    "primary": dict(source="primary", out="analysis", seeds=range(32001, 32033), block_a=range(32001, 32017),
                    filters=(576, 1024, 2304, 4096), primary_t=(1024, 4096), start=4096, step=256, end=16384,
                    ext_start=17408, ext_step=1024, ext_end=65536, loss=4, loss_sensitivity=16,
                    permutations=PERMUTATIONS, bootstrap=BOOTSTRAP),
    "test": dict(source="validation", out="validation/test-analysis", seeds=range(29941, 29945),
                 block_a=range(29941, 29943), filters=(36, 64, 144, 256), primary_t=(64, 256), start=256, step=16,
                 end=1024, ext_start=1088, ext_step=64, ext_end=4096, loss=4, loss_sensitivity=16,
                 permutations=2000, bootstrap=500),
}


def t_n(cfg, size):
    return cfg["filters"][SIZES.index(size)]


# ---------------------------------------------------------------- loading

def table(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return NAN


class World:
    def __init__(self, directory, cfg):
        self.name = directory.name
        self.info = table(directory / "world.tsv.gz")[0]
        self.size, self.seed = int(self.info["width"]), int(self.info["seed"])
        self.N = self.size * int(self.info["height"])
        self.tN = t_n(cfg, self.size)
        self.extinct = int(self.info["extinction_tick"]) >= 0
        self.reached = {}  # (series, t, level) -> evaluated
        for r in table(directory / "timepoints.tsv.gz"):
            if r["series"] in ("material", "material_ext"):
                self.reached[(r["series"], int(r["t"]), int(r["level"]))] = int(r["eval_tick"]) >= 0
        self.focus = set()  # (series, t, level) with the focus genotype in F(A)
        self.sets = {}      # material F(A) at t = N, for P1-P3
        for r in table(directory / "filtered.tsv.gz"):
            key = (r["series"], int(r["t"]), int(r["level"]))
            if r["component"] == FOCUS and r["series"] in ("material", "material_ext"):
                self.focus.add(key)
            if r["series"] == "material" and key[1] == self.tN:
                self.sets.setdefault(key[2], {})[r["component"]] = int(r["n_pass"])
        self.census = {int(r["level"]): r for r in table(directory / "census.tsv.gz")}
        self.spatial = {(r["grid"], int(r["level"])): r for r in table(directory / "spatial.tsv.gz")}
        self.assays = {(r["series"], r["genotype"]): r for r in table(directory / "assays.tsv.gz")}
        self.ledger = table(directory / "ledger.tsv.gz")
        self.bedau = table(directory / "bedau.tsv.gz")


# ---------------------------------------------------------------- statistics (helpers copied)

def entropy(counts):
    total = sum(counts)
    return -sum(c / total * math.log2(c / total) for c in counts if c) if total else 0.0


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [NAN] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def sign(x):
    return 0 if (x == 0 or math.isnan(x)) else (1 if x > 0 else -1)


def mean(xs):
    xs = [x for x in xs if not math.isnan(x)]
    return statistics.fmean(xs) if xs else NAN


def median(xs):
    xs = [x for x in xs if not math.isnan(x)]
    return statistics.median(xs) if xs else NAN


def gamma_q(a, x):
    """Regularized upper incomplete gamma Q(a, x), by series for x < a + 1 and continued fraction otherwise."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        term = total = 1.0 / a
        n = a
        while abs(term) > 1e-15 * abs(total):
            n += 1
            term *= x / n
            total += term
        return max(0.0, 1.0 - total * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    b, c, d = x + 1 - a, 1e300, 1 / (x + 1 - a)
    h, i = d, 1
    while True:
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        i += 1
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


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
    if correction <= 0:
        return NAN, NAN
    H /= correction
    df = sum(1 for xs in groups if xs) - 1
    return H, gamma_q(df / 2, H / 2)


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
    return lower, upper


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r, i = [0.0] * len(xs), 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    """Spearman's rho with average ranks for ties; NaN if either variable is constant."""
    if len(x) < 2:
        return NAN
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sx = sum((a - mx) ** 2 for a in rx)
    sy = sum((b - my) ** 2 for b in ry)
    if sx == 0 or sy == 0:
        return NAN
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sx * sy)


def permutation_test(x, y, n, seed):
    """Two-sided permutation p for Spearman's rho, permuting the x labels; p = (count + 1) / (n + 1)."""
    r0 = spearman(x, y)
    if math.isnan(r0):
        return r0, 1.0
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    cx, cy = [a - mx for a in rx], [b - my for b in ry]
    den = math.sqrt(sum(a * a for a in cx) * sum(b * b for b in cy))
    rng = random.Random(seed)
    target, count = abs(r0) * den - 1e-9, 0
    perm = list(cx)
    for _ in range(n):
        rng.shuffle(perm)
        if abs(sum(a * b for a, b in zip(perm, cy))) >= target:
            count += 1
    return r0, (count + 1) / (n + 1)


def stratified(rng, groups):
    """One bootstrap resample of each size's worlds, within size."""
    return {k: [v[rng.randrange(len(v))] for _ in v] for k, v in groups.items()}


def percentile(values, lo, hi):
    v = sorted(x for x in values if not math.isnan(x))
    if not v:
        return NAN, NAN
    return v[int(lo * len(v))], v[min(len(v) - 1, math.ceil(hi * len(v)) - 1)]


def pooled_sd(groups):
    num_, den = 0.0, 0
    for xs in groups.values():
        xs = [x for x in xs if not math.isnan(x)]
        if len(xs) > 1:
            num_ += (len(xs) - 1) * statistics.variance(xs)
            den += len(xs) - 1
    return math.sqrt(num_ / den) if den else NAN


# ---------------------------------------------------------------- per-world endpoints

def episodes(present, levels, step, k):
    """Episodes on a presence sequence: an episode starts at a present timepoint outside an episode
    and ends with a loss after k consecutive absent timepoints. Returns counts and lengths."""
    n_ep = losses = absent = 0
    inside, first, last, longest, start = False, None, None, 0, None
    for L, p in zip(levels, present):
        if p:
            if not inside:
                inside, start, n_ep = True, L, n_ep + 1
                first = L if first is None else first
            last, absent = L, 0
        elif inside:
            absent += 1
            if absent == k:
                losses += 1
                inside = False
                longest = max(longest, last - start + step)
    if inside:
        longest = max(longest, last - start + step)
    return dict(episodes=n_ep, losses=losses, longest=longest, first=first if first is not None else NAN)


def presence(w, cfg, series, t, levels):
    """Focus presence in F(A) at the reached levels. Levels after extinction count as absent."""
    seq, used = [], []
    for L in levels:
        r = w.reached.get((series, t, L))
        if r or (r is None and w.extinct):
            seq.append((series, t, L) in w.focus)
            used.append(L)
    return used, seq


def world_endpoints(w, cfg):
    W = list(range(cfg["start"], cfg["end"] + 1, cfg["step"]))
    G = num(w.info["G_material"])
    reach = cfg["end"] + max(cfg["filters"])
    row = dict(world=w.name, size=w.size, seed=w.seed, block="A" if w.seed in cfg["block_a"] else "B", N=w.N,
               t_N=w.tN, status=w.info["status"], extinct=int(w.extinct), G=G,
               unreached=int(not w.extinct and G < reach))
    for t in cfg["filters"]:
        used, seq = presence(w, cfg, "material", t, W)
        row[f"E1_t{t}"] = int(any(seq))
        row[f"E2_t{t}"] = sum(seq) / len(used) if used else NAN
        e = episodes(seq, used, cfg["step"], cfg["loss"])
        e16 = episodes(seq, used, cfg["step"], cfg["loss_sensitivity"])
        row.update({f"episodes_t{t}": e["episodes"], f"losses_t{t}": e["losses"], f"longest_t{t}": e["longest"],
                    f"first_t{t}": e["first"], f"losses16_t{t}": e16["losses"], f"longest16_t{t}": e16["longest"],
                    f"end_t{t}": int(bool(seq) and used[-1] == W[-1] and seq[-1])})
    row["E1_tN"], row["E2_tN"] = row[f"E1_t{w.tN}"], row[f"E2_t{w.tN}"]
    # Filter-free presence (E3) from the census at the same levels.
    ff_levels, ff = [], []
    for L in W:
        c = w.census.get(L)
        if c is not None or w.extinct:
            ff_levels.append(L)
            ff.append(c is not None and int(c["focus"]) > 0)
    row["E3"] = sum(ff) / len(ff_levels) if ff_levels else NAN
    e = episodes(ff, ff_levels, cfg["step"], cfg["loss"])
    e16 = episodes(ff, ff_levels, cfg["step"], cfg["loss_sensitivity"])
    row.update(ff_episodes=e["episodes"], ff_losses=e["losses"], ff_longest=e["longest"], ff_first=e["first"],
               ff_losses16=e16["losses"], ff_longest16=e16["longest"],
               ff_end=int(bool(ff) and ff_levels[-1] == W[-1] and ff[-1]))
    # Extended window at t = N (descriptive).
    X = list(range(cfg["ext_start"], cfg["ext_end"] + 1, cfg["ext_step"]))
    used, seq = presence(w, cfg, "material_ext", w.tN, X)
    row.update(ext_unreached=int(not w.extinct and G < cfg["ext_end"] + w.tN), ext_levels=len(used),
               E1_ext=int(any(seq)), E2_ext=sum(seq) / len(used) if used else NAN,
               ext_end=int(bool(seq) and used[-1] == X[-1] and seq[-1]))
    ext_ff = [int(w.spatial[("ext", L)]["carriers"]) > 0 for L in X if ("ext", L) in w.spatial]
    if w.extinct:
        ext_ff += [False] * (len(X) - len(ext_ff))
    row["E3_ext"] = sum(ext_ff) / len(ext_ff) if ext_ff else NAN
    # Origins and carriers in the window, from the spatial rows at the main grid.
    sp = {L: w.spatial.get(("main", L)) for L in [W[0] - cfg["step"]] + W}
    lo, hi = sp.get(W[0]), sp.get(W[-1])
    if lo is not None and hi is not None:
        origins = int(hi["focus_origins"]) - int(lo["focus_origins"])
        births = int(hi["births"]) - int(lo["births"])
        row.update(origins=origins, origins_per_generation=origins / (W[-1] - W[0]),
                   origins_per_million_births=1e6 * origins / births if births else NAN)
    else:
        row.update(origins=NAN, origins_per_generation=NAN, origins_per_million_births=NAN)
    carriers, shares, present_counts, clusters, largest, joins, xis, censored = [], [], [], [], [], [], [], []
    for L in W:
        r, c = sp.get(L), w.census.get(L)
        k = int(r["carriers"]) if r else 0
        alive = int(c["alive"]) if c else 0
        carriers.append(k)
        shares.append(k / alive if alive else 0.0)
        if k > 0:
            present_counts.append(k)
            clusters.append(int(r["clusters"]))
            largest.append(int(r["largest"]) / k)
            if k > 1:
                joins.append((int(r["pairs"]) / k) / (4 * (k - 1) / (w.N - 1)))
            if int(r["xi"]) > 0:
                xis.append(int(r["xi"]))
                censored.append(int(r["xi_censored"]))
    row.update(mean_carriers=mean(carriers), mean_share=mean(shares), median_carriers_present=median(present_counts),
               median_clusters=median(clusters), median_largest_share=median(largest), mean_join_ratio=mean(joins),
               median_xi=median(xis), xi_censored_fraction=mean(censored) if censored else NAN)
    # Loss anatomy: filter-free global losses in the window and clusters at the preceding level;
    # levels where the cluster count fell while carriers remained.
    before, drops = [], 0
    for prev, L in zip([W[0] - cfg["step"]] + W[:-1], W):
        a, b = sp.get(prev), sp.get(L)
        ka, kb = (int(a["carriers"]) if a else 0), (int(b["carriers"]) if b else 0)
        if ka > 0 and kb == 0:
            before.append(int(a["clusters"]))
        if ka > 0 and kb > 0 and int(b["clusters"]) < int(a["clusters"]):
            drops += 1
    row.update(global_losses=len(before), losses_after_one_cluster=sum(1 for c in before if c == 1),
               cluster_drops=drops)
    # Fetch sources of focus births (ledger).
    fetch = {k: 0 for k in ("fetch_living", "fetch_own_reservation_written", "fetch_own_reservation_unwritten",
                            "fetch_other_reservation_written", "fetch_other_reservation_unwritten", "fetch_free")}
    focus_births = 0
    for r in w.ledger:
        if r["focus"] == "1" and r["outcome"] == "birth":
            focus_births += int(r["attempts"])
            for k in fetch:
                fetch[k] += int(r[k])
    total = sum(fetch.values())
    row["ledger_focus_births"] = focus_births
    for k, v in fetch.items():
        row[f"share_{k}"] = v / total if total else NAN
    # MODES P1-P3 at t = N and Bedau P4, for continuity (descriptive).
    seen, previous, novelty, change, ecol = set(), None, 0, [], []
    for L in range(0, cfg["end"] + 1, cfg["step"]):
        if not (w.reached.get(("material", w.tN, L)) or w.extinct):
            previous = None
            continue
        F = w.sets.get(L, {})
        if L >= cfg["start"]:
            novelty += len(set(F) - seen)
            if previous is not None:
                change.append(len(set(F) - previous))
            ecol.append(entropy(list(F.values())))
        seen |= set(F)
        previous = set(F)
    row.update(P1=novelty, P2=mean(change), P3=mean(ecol), P4=num(w.info["P4_run"]),
               P4_shadow=num(w.info["P4_shadow"]))
    # Strategy classes at t = N (descriptive).
    for cls in DEPENDENT:
        seq = []
        for L in W:
            F = w.sets.get(L, {}) if (w.reached.get(("material", w.tN, L)) or w.extinct) else None
            if F is None:
                continue
            classes = set()
            for g in F:
                a = w.assays.get(("material", g))
                if a is None:
                    raise ValueError(f"{w.name}: no material assay for {g} at level {L}")
                classes.add(a["class"])
            seq.append(cls in classes)
        row[f"class_{cls}_established"] = int(any(seq))
        row[f"class_{cls}_fraction"] = sum(seq) / len(seq) if seq else NAN
    a = w.assays.get(("material", FOCUS))
    row["focus_class"] = a["class"] if a else ""
    row.update(focus_origins_total=int(w.info["focus_origins"]), focus_births_total=int(w.info["focus_births"]))
    return row


# ---------------------------------------------------------------- tests and rules

def by_size(rows, key):
    return {s: [r[key] for r in rows if r["size"] == s] for s in SIZES if any(r["size"] == s for r in rows)}


def spearman_size(rows, key):
    xs = [r["size"] for r in rows if not math.isnan(r[key])]
    ys = [r[key] for r in rows if not math.isnan(r[key])]
    return xs, ys


def boot_spearman(rows, key, cfg, seed):
    groups = {s: [r for r in rows if r["size"] == s and not math.isnan(r[key])] for s in SIZES}
    groups = {s: v for s, v in groups.items() if v}
    rng = random.Random(seed)
    values = []
    for _ in range(cfg["bootstrap"]):
        sample = [r for v in stratified(rng, groups).values() for r in v]
        values.append(spearman([r["size"] for r in sample], [r[key] for r in sample]))
    return percentile(values, 0.025, 0.975)


def equivalence(rows, key, cfg, seed):
    groups = by_size(rows, key)
    lo_s, hi_s = min(groups), max(groups)
    margin = EQUIVALENCE_SD * pooled_sd(groups)
    rng = random.Random(seed)
    diffs = []
    for _ in range(cfg["bootstrap"]):
        s = stratified(rng, {lo_s: groups[lo_s], hi_s: groups[hi_s]})
        diffs.append(mean(s[hi_s]) - mean(s[lo_s]))
    lo, hi = percentile(diffs, 0.05, 0.95)
    eq = not math.isnan(margin) and not math.isnan(lo) and -margin <= lo and hi <= margin
    return mean(groups[hi_s]) - mean(groups[lo_s]), lo, hi, margin, eq


def primary_tests(rows, cfg, inconclusive):
    keys = [f"E1_t{t}" for t in cfg["primary_t"]] + [f"E2_t{t}" for t in cfg["primary_t"]] + ["E3"]
    out = []
    for i, key in enumerate(keys):
        xs, ys = spearman_size(rows, key)
        rho, p = permutation_test(xs, ys, cfg["permutations"], SEED + i)
        blocks = {}
        for b in ("A", "B"):
            sub = [r for r in rows if r["block"] == b]
            blocks[b] = spearman(*spearman_size(sub, key))
        groups = by_size(rows, key)
        H, kw_p = kruskal([groups[s] for s in groups])
        diff, lo, hi, margin, eq = equivalence(rows, key, cfg, SEED + 100 + i)
        row = dict(endpoint=key, rho=rho, p=p, rho_A=blocks["A"], rho_B=blocks["B"], kruskal_H=H, kruskal_p=kw_p,
                   largest_minus_smallest=diff, eq_lo90=lo, eq_hi90=hi, eq_margin=margin, equivalent=int(eq))
        for s in groups:
            row[f"mean_L{s}"] = mean(groups[s])
        out.append(row)
    for row, adj in zip(out, holm([r["p"] for r in out])):
        row["p_holm"] = adj
        same = sign(row["rho_A"]) == sign(row["rho_B"]) == sign(row["rho"]) != 0
        if inconclusive:
            row["outcome"] = "inconclusive"
        elif adj < ALPHA and same:
            row["outcome"] = "differs"
        elif row["equivalent"]:
            row["outcome"] = "equivalent"
        else:
            row["outcome"] = "inconclusive"
    return out


def mean_e2(rows, size, t):
    return mean([r[f"E2_t{t}"] for r in rows if r["size"] == size])


def attribution(rows, tests, cfg):
    """Rule 5: split the earlier contrast into size and filter parts at sizes 32 and 64."""
    t1, t2 = cfg["primary_t"]
    small, large = 32, 64
    delta = mean_e2(rows, large, t2) - mean_e2(rows, small, t1)
    groups = {s: [r for r in rows if r["size"] == s] for s in (small, large)}
    rng = random.Random(SEED + 200)
    boots = {k: [] for k in ("S_t1", "S_t2", "F_small", "F_large")}
    for _ in range(cfg["bootstrap"]):
        s = stratified(rng, groups)
        m = {(L, t): mean([r[f"E2_t{t}"] for r in s[L]]) for L in (small, large) for t in (t1, t2)}
        boots["S_t1"].append(m[(large, t1)] - m[(small, t1)])
        boots["S_t2"].append(m[(large, t2)] - m[(small, t2)])
        boots["F_small"].append(m[(small, t2)] - m[(small, t1)])
        boots["F_large"].append(m[(large, t2)] - m[(large, t1)])
    point = dict(S_t1=mean_e2(rows, large, t1) - mean_e2(rows, small, t1),
                 S_t2=mean_e2(rows, large, t2) - mean_e2(rows, small, t2),
                 F_small=mean_e2(rows, small, t2) - mean_e2(rows, small, t1),
                 F_large=mean_e2(rows, large, t2) - mean_e2(rows, large, t1))
    parts = []
    for k, v in point.items():
        lo, hi = percentile(boots[k], 0.05, 0.95)
        on_delta_side = (sign(delta) > 0 and lo > 0) or (sign(delta) < 0 and hi < 0)
        parts.append(dict(part=k, value=v, lo90=lo, hi90=hi, entirely_on_delta_side=int(on_delta_side)))
    t = {r["endpoint"]: r for r in tests}
    keys = [f"E2_t{t1}", f"E2_t{t2}", "E3"]
    size_differs = all(t[k]["outcome"] == "differs" and sign(t[k]["rho"]) == sign(delta) for k in keys)
    size_equivalent = all(t[k]["outcome"] == "equivalent" for k in keys)
    filter_side = any(p["entirely_on_delta_side"] for p in parts if p["part"].startswith("F_"))
    if size_differs and not filter_side:
        outcome = "size, not filter length"
    elif size_equivalent and filter_side:
        outcome = "filter length, not size"
    elif size_differs and filter_side:
        outcome = "both"
    else:
        outcome = "inconclusive"
    summary = dict(delta=delta, check_S_t2_plus_F_small=point["S_t2"] + point["F_small"],
                   check_S_t1_plus_F_large=point["S_t1"] + point["F_large"], outcome=outcome)
    return parts, summary


def neutral_scaling(rows, tests, cfg):
    """Rule 6: for E1 or E2 differing at a fixed t, test the t = N diagonal, uncorrected."""
    out = []
    t = {r["endpoint"]: r for r in tests}
    for fam in ("E1", "E2"):
        fixed = [t[f"{fam}_t{x}"] for x in cfg["primary_t"] if t[f"{fam}_t{x}"]["outcome"] == "differs"]
        if not fixed:
            continue
        xs, ys = spearman_size(rows, f"{fam}_tN")
        rho, p = permutation_test(xs, ys, cfg["permutations"], SEED + 300 + len(out))
        direction = sign(fixed[0]["rho"])
        label = ("beyond the filter's neutral scaling" if p < ALPHA and sign(rho) == direction
                 else "consistent with the filter's neutral scaling")
        out.append(dict(endpoint=f"{fam}_tN", rho=rho, p_uncorrected=p, label=label))
    return out


def patterns(rows, cfg):
    """Rule 7: descriptive pattern labels."""
    out = []
    # Supply-like: log-log slope of mean origins per generation against N contains 1, and the
    # filter-free longest episode has no detectable association with L.
    groups = {s: [r for r in rows if r["size"] == s] for s in SIZES if any(r["size"] == s for r in rows)}

    def slope(g):
        pts = [(math.log(s * s), math.log(m)) for s, v in g.items()
               if (m := mean([r["origins_per_generation"] for r in v])) > 0]
        if len(pts) < 2:
            return NAN
        mx, my = statistics.fmean(p[0] for p in pts), statistics.fmean(p[1] for p in pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        return sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    rng = random.Random(SEED + 400)
    slopes = [slope(stratified(rng, groups)) for _ in range(cfg["bootstrap"])]
    s_lo, s_hi = percentile(slopes, 0.025, 0.975)
    ep_rho = spearman(*spearman_size(rows, "ff_longest"))
    ep_lo, ep_hi = boot_spearman(rows, "ff_longest", cfg, SEED + 401)
    supply = (not math.isnan(s_lo)) and s_lo <= 1 <= s_hi and ep_lo <= 0 <= ep_hi
    out.append(dict(pattern="supply-like (A1a)", statistic="origins slope; rho(L, ff_longest)",
                    value=f"{slope(groups):.4g} [{s_lo:.4g}, {s_hi:.4g}]; {ep_rho:.4g} [{ep_lo:.4g}, {ep_hi:.4g}]",
                    holds=int(supply)))
    # Smooth: longest filter-free episode rises with L, and no adjacent step carries more than half
    # of the rise in mean E2, at both primary filters.
    smooth_steps, shares = [], []
    for t in cfg["primary_t"]:
        m = [mean_e2(rows, s, t) for s in groups]
        rise = m[-1] - m[0]
        steps = [b - a for a, b in zip(m, m[1:])]
        smooth_steps.append(rise > 0 and max(steps) <= 0.5 * rise)
        shares.append(f"t{t} rise {rise:.4g}, largest step {max(steps) / rise:.4g}" if rise > 0
                      else f"t{t} rise {rise:.4g}")
    smooth = ep_lo > 0 and all(smooth_steps)
    out.append(dict(pattern="smooth (A1b)", statistic="rho(L, ff_longest) interval; rise in mean E2 and largest step share",
                    value=f"[{ep_lo:.4g}, {ep_hi:.4g}]; " + "; ".join(shares),
                    holds=int(smooth)))
    # Pattern-like: xi has no detectable association with L, xi < L/4 at the largest size, and at the
    # smallest size most filter-free global losses follow a level with one cluster.
    xi_rho = spearman(*spearman_size(rows, "median_xi"))
    xi_lo, xi_hi = boot_spearman(rows, "median_xi", cfg, SEED + 402)
    largest, smallest = max(groups), min(groups)
    xi_large = median([r["median_xi"] for r in groups[largest]])
    losses = sum(r["global_losses"] for r in groups[smallest])
    one = sum(r["losses_after_one_cluster"] for r in groups[smallest])
    pat = (not math.isnan(xi_lo)) and xi_lo <= 0 <= xi_hi and xi_large < largest / 4 and losses > 0 and one / losses > 0.5
    out.append(dict(pattern="pattern-like (A2)", statistic="rho(L, xi); median xi at largest L; one-cluster share at smallest L",
                    value=f"{xi_rho:.4g} [{xi_lo:.4g}, {xi_hi:.4g}]; {xi_large:.4g}; {one}/{losses}", holds=int(pat)))
    return out


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
    cfg = SETTINGS[parser.parse_args().set]
    source = HERE / "results" / cfg["source"]
    out = HERE / "results" / cfg["out"]
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for size in SIZES:
        for seed in cfg["seeds"]:
            d = source / f"L{size}-{seed}"
            if (d / "world.tsv.gz").exists():
                rows.append(world_endpoints(World(d, cfg), cfg))
    write(out / "worlds.tsv", rows)
    # Rule 4: more than 10% unreached among living worlds at any size makes every endpoint inconclusive.
    reach = []
    for s in SIZES:
        living = [r for r in rows if r["size"] == s and not r["extinct"]]
        unreached = sum(r["unreached"] for r in living)
        reach.append(dict(size=s, worlds=sum(1 for r in rows if r["size"] == s), living=len(living),
                          extinct=sum(1 for r in rows if r["size"] == s and r["extinct"]),
                          stagnant=sum(1 for r in rows if r["size"] == s and r["status"] == "stagnant"),
                          unreached=unreached,
                          ext_unreached=sum(r["ext_unreached"] for r in living),
                          too_many_unreached=int(bool(living) and unreached / len(living) > UNREACHED_LIMIT)))
    write(out / "reach.tsv", reach)
    inconclusive = any(r["too_many_unreached"] for r in reach)
    tests = primary_tests(rows, cfg, inconclusive)
    write(out / "tests.tsv", tests)
    parts, summary = attribution(rows, tests, cfg)
    write(out / "attribution.tsv", parts)
    write(out / "attribution-summary.tsv", [summary])
    scaling = neutral_scaling(rows, tests, cfg)
    write(out / "neutral-scaling.tsv", scaling, ["endpoint", "rho", "p_uncorrected", "label"])
    pats = patterns(rows, cfg)
    write(out / "patterns.tsv", pats)
    # Size x filter cross (descriptive) and per-size secondary summaries.
    cross = []
    for s in SIZES:
        sub = [r for r in rows if r["size"] == s]
        if not sub:
            continue
        for t in cfg["filters"]:
            cross.append(dict(size=s, t=t, diagonal=int(t == t_n(cfg, s)), worlds=len(sub),
                              established=sum(r[f"E1_t{t}"] for r in sub), mean_E2=mean([r[f"E2_t{t}"] for r in sub]),
                              median_E2=median([r[f"E2_t{t}"] for r in sub]),
                              episodes=sum(r[f"episodes_t{t}"] for r in sub), losses=sum(r[f"losses_t{t}"] for r in sub),
                              losses16=sum(r[f"losses16_t{t}"] for r in sub),
                              median_longest=median([r[f"longest_t{t}"] for r in sub]),
                              present_at_end=sum(r[f"end_t{t}"] for r in sub)))
    write(out / "cross.tsv", cross)
    keys = ("E3", "ff_episodes", "ff_losses", "ff_losses16", "ff_longest", "ff_end", "E1_ext", "E2_ext", "E3_ext",
            "ext_end", "origins_per_generation", "origins_per_million_births", "mean_carriers", "mean_share",
            "median_carriers_present", "median_clusters", "median_largest_share", "mean_join_ratio", "median_xi",
            "xi_censored_fraction", "global_losses", "losses_after_one_cluster", "cluster_drops",
            "share_fetch_living", "share_fetch_own_reservation_written", "P1", "P2", "P3", "P4", "P4_shadow")
    secondary = []
    for s in SIZES:
        sub = [r for r in rows if r["size"] == s]
        if not sub:
            continue
        row = dict(size=s, worlds=len(sub))
        for k in keys:
            vals = [float(r[k]) for r in sub]
            row[f"mean_{k}"] = mean(vals)
            row[f"median_{k}"] = median(vals)
        secondary.append(row)
    write(out / "secondary.tsv", secondary)
    classes = []
    for s in SIZES:
        sub = [r for r in rows if r["size"] == s]
        if not sub:
            continue
        for cls in DEPENDENT:
            k = sum(r[f"class_{cls}_established"] for r in sub)
            lo, hi = clopper_pearson(k, len(sub))
            classes.append(dict(size=s, cls=cls, established=k, worlds=len(sub), ci_lo=lo, ci_hi=hi,
                                mean_fraction=mean([r[f"class_{cls}_fraction"] for r in sub])))
        focus = {}
        for r in sub:
            focus[r["focus_class"] or "not assayed"] = focus.get(r["focus_class"] or "not assayed", 0) + 1
        classes.append(dict(size=s, cls="focus genotype class: " + ", ".join(f"{k} {v}" for k, v in sorted(focus.items())),
                            worlds=len(sub)))
    write(out / "classes.tsv", classes, ["size", "cls", "established", "worlds", "ci_lo", "ci_hi", "mean_fraction"])
    with open(out / "summary.md", "w") as f:
        f.write(f"# lattice-size-01 analysis ({cfg['source']})\n\n## Reach\n\n")
        f.write(md_table(reach, list(reach[0])) + "\n\n## Primary tests\n\n")
        f.write(md_table(tests, ["endpoint", "rho", "p", "p_holm", "rho_A", "rho_B", "outcome"]
                         + [f"mean_L{s}" for s in SIZES]) + "\n\n## Attribution\n\n")
        f.write(md_table(parts, list(parts[0])) + "\n\n" + md_table([summary], list(summary)) + "\n\n")
        f.write("## Neutral scaling\n\n" + (md_table(scaling, ["endpoint", "rho", "p_uncorrected", "label"])
                                           if scaling else "No fixed-filter E1 or E2 endpoint differed.") + "\n\n")
        f.write("## Patterns (descriptive)\n\n" + md_table(pats, list(pats[0])) + "\n\n## Size x filter\n\n")
        f.write(md_table(cross, list(cross[0])) + "\n")
    print(f"{len(rows)} worlds analysed -> {out}")


if __name__ == "__main__":
    main()
