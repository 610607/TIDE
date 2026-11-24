"""Summarize all eight v31 jobs and check the four v27 replays.

Usage: python3 scripts/analysis/v31_mass.py runs/v31 runs/v27
Counts cover complete census intervals. An early extinction is a terminal outcome.
"""
import re
import sys
from pathlib import Path

INTERVAL = 50_000
END = 500_000


def load(path):
    windows = {}
    final = {}
    with path.open() as source:
        for line in source:
            if line.startswith("final tick="):
                final = dict(word.split("=") for word in line.split()[1:])
            match = re.match(r"# (census|massfate|fate|fateborn|route) tick=(\d+) ", line)
            if match:
                fields = dict(re.findall(r" ([\w]+)=([\d/]+)", line))
                windows.setdefault(int(match[2]), {})[match[1]] = fields
    return windows, final


def evaluate(path, reference):
    windows, final = load(path)
    if not final:
        raise ValueError(f"{path.name}: incomplete; no terminal record")
    end, active = int(final["tick"]), int(final["active"])
    if end > END or (end < END and active != 0):
        raise ValueError(f"{path.name}: unexpected terminal record {final}")
    if list(windows) != list(range(INTERVAL, end + 1, INTERVAL)):
        raise ValueError(f"{path.name}: missing checkpoints")
    if reference:
        archived, archived_final = load(reference)
        if final != archived_final:
            raise ValueError(f"{path.name}: terminal record differs from v27")
    rows = []
    for tick, window in windows.items():
        census, fate = window["census"], window["fate"]
        m = {k: int(v) for k, v in window["massfate"].items()}
        strict = int(census["strict"])
        births = [int(window["fateborn"][k].split("/")[0]) for k in ("rep", "loose", "prop", "other")]
        children = m["strict_clear"] + m["strict_after_refusal"]
        copies = m["copies_clear"] + m["copies_after_refusal"]
        if not (children == births[0] and copies == sum(births)
                and m["newly_refused"] <= m["cross_refused"] <= m["no_mass"]
                and m["strict_clear"] <= m["copies_clear"]
                and m["strict_after_refusal"] <= m["copies_after_refusal"]
                and int(fate["balance"]) == strict == int(fate["rep_now"])
                and all(fate[k] == "0" for k in ("census_mismatch", "untracked", "stale", "replaced"))):
            raise ValueError(f"{path.name}: inconsistent observer counts at {tick}")
        if reference:
            old = archived[tick]
            if (census["strict"] != old["census"]["strict"] or census["active"] != old["census"]["active"]
                    or window["fateborn"] != old["fateborn"] or m["no_mass"] != int(old["route"]["no_mass"])):
                raise ValueError(f"{path.name}: replay differs from v27 at {tick}")
        rows.append(dict(m, tick=tick, strict=strict, children=children, copies=copies))
    return rows, end, active


def summarize(label, rows, end, active):
    by_tick = {r["tick"]: r["strict"] for r in rows}
    change = [(r["strict"] - prev["strict"], r["tick"]) for prev, r in zip(rows, rows[1:])]
    steepest = min((d for d, t in change), default=0)
    falls = ",".join(f"{(t - INTERVAL) // 1000}-{t // 1000}k" for d, t in change if d == steepest and d < 0)
    total = {k: sum(r[k] for r in rows) for k in ("cross_refused", "newly_refused", "children", "copies",
                                                    "strict_after_refusal", "copies_after_refusal")}
    retention = "n/a"
    passed = False
    if end == END and by_tick[INTERVAL]:
        retention = f"{by_tick[END] / by_tick[INTERVAL]:.3f}"
        passed = by_tick[END] >= by_tick[350_000] and by_tick[END] * 5 >= by_tick[INTERVAL] * 4
    print(f"{label}: {'survived' if active else 'extinct'} at {end}; strict 50k/350k/500k "
          + "/".join(str(by_tick.get(t, 'n/a')) for t in (INTERVAL, 350_000, END))
          + f"; retention={retention}; criterion={'pass' if passed else 'fail'}; "
          + f"steepest={falls or 'none'} ({min(steepest, 0):+d}); "
          + " ".join(f"{k}={v}" for k, v in total.items()))


def main():
    run_dir, baseline_dir = map(Path, sys.argv[1:])
    print("job\ttick\tstrict\tcross_refused\tnewly_refused\tstrict_children/copies\tafter_refusal_strict/copies")
    for op in ("zero", "fail"):
        for seed in (1, 2):
            for mass in (48, 64):
                name = f"{op}_s{seed}_m{mass}"
                ref = baseline_dir / f"{op}_m195_s{seed}.tsv" if mass == 48 else None
                rows, end, active = evaluate(run_dir / (name + ".tsv"), ref)
                for r in rows:
                    print(f"{name}\t{r['tick']}\t{r['strict']}\t{r['cross_refused']}\t{r['newly_refused']}\t"
                          f"{r['children']}/{r['copies']}\t{r['strict_after_refusal']}/{r['copies_after_refusal']}")
                summarize(name, rows, end, active)


if __name__ == "__main__":
    main()
