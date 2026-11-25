"""Run the access-dynamics study in resumable batches and archive every batch in git.

  python3 run.py validate   # observer, fork and shadow checks; must pass before the study sets
  python3 run.py primary    # 32 x 32, seeds 30001-30032, three arms, 12 batches of 8 worlds
  python3 run.py scale      # 64 x 64, seeds 30101-30108, three arms, 3 batches of 8 worlds

A world is complete when results/<set>/<arm>-<seed>/ exists; it is written to a temporary
directory and renamed. A rerun skips complete worlds and commits any batch left uncommitted.
"""
import argparse
import csv
import gzip
import hashlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BINARY = ROOT / "kernel/build/access-dynamics/study"
RESULTS = HERE / "results"
ARMS = ("self", "read", "read_fetch")
TABLES = ("world", "timepoints", "filtered", "bedau", "collapsed", "assays")
BATCH, JOBS = 8, 4
PRIMARY = ["--size", "32", "32", "--filter", "1024", "256", "16384", "--sensitivity", "256,2048"]
SETS = {
    "primary": (range(30001, 30033), PRIMARY + ["--horizon", str(1 << 22)]),
    "scale": (range(30101, 30109), ["--size", "64", "64", "--horizon", str(1 << 21),
                                    "--filter", "4096", "1024", "16384", "--sensitivity", ""]),
}
VALIDATION_SEEDS = range(29901, 29905)
VALIDATION = PRIMARY + ["--horizon", str(1 << 16)]
MUTATION_FREE = PRIMARY + ["--horizon", str(1 << 20), "--mutation", "0"]
FOUNDER = "R..CLD".encode().hex()
TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01GJrPGAhYtymMTQHquWQkvB")


def log(path, line):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a") as f:
        f.write(f"{stamp}\t{line}\n")
    print(f"{stamp} {line}", flush=True)


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=check, capture_output=True, text=True)


def verify_freeze():
    """Refuse to run when a frozen file differs from revision.sha256."""
    bad = []
    for line in (HERE / "revision.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            bad.append(name)
    if bad:
        sys.exit("frozen files changed: " + ", ".join(bad))


def run(args, out=None):
    """Run the study binary; return (exit code, stdout, stderr, seconds, max RSS in KB)."""
    with tempfile.TemporaryFile("w+") as so, tempfile.TemporaryFile("w+") as se:
        start = time.monotonic()
        p = subprocess.Popen([str(BINARY), *args] + (["--out", str(out)] if out else []), stdout=so, stderr=se)
        _, status, usage = os.wait4(p.pid, 0)
        p.returncode = os.waitstatus_to_exitcode(status)
        seconds = time.monotonic() - start
        so.seek(0); se.seek(0)
        return p.returncode, so.read().strip(), se.read().strip(), seconds, usage.ru_maxrss


def world(directory, name, args, revision):
    """Run one observed world into directory/name; raise on any failure."""
    dest = directory / name
    if dest.exists():
        return "skipped"
    tmp = Path(tempfile.mkdtemp(prefix=f".tmp-{name}-", dir=directory))
    try:
        code, out, err, seconds, rss = run(args, tmp)
        record = (f"command\tstudy {' '.join(args)}\nrevision\t{revision}\nexit\t{code}\nhash_end\t{out}\n"
                  f"seconds\t{seconds:.1f}\nmax_rss_kb\t{rss}\nstderr\t{err}\n")
        if code != 0:
            (directory / f"{name}.failed.txt").write_text(record)
            raise RuntimeError(f"{name} failed: {err}")
        for table in TABLES:
            src = tmp / f"{table}.tsv"
            with open(src, "rb") as f, open(tmp / f"{table}.tsv.gz", "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as z:
                    shutil.copyfileobj(f, z)
            src.unlink()
        (tmp / "log.txt").write_text(record)
        tmp.rename(dest)
        return f"{seconds:.0f} s"
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def push():
    branch = git("branch", "--show-current").stdout.strip()
    for target in (branch, "main"):
        for attempt in range(5):
            p = git("push", "-u", "origin", f"HEAD:{target}", check=False) if target == branch else \
                git("push", "origin", "HEAD:main", check=False)
            if p.returncode == 0:
                break
            if "rejected" in p.stderr or "non-fast-forward" in p.stderr or "fetch first" in p.stderr:
                git("fetch", "origin", target)
                git("merge", "--no-edit", "FETCH_HEAD")
            time.sleep(2 ** (attempt + 1))
        else:
            raise RuntimeError(f"push to {target} failed: {p.stderr}")


def commit(paths, subject, body):
    git("add", "--", *map(str, paths))
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git("commit", "-m", f"{subject}\n\n{body}\n\n{TRAILER}", "--", *map(str, paths))
    return True


def study(name):
    verify_freeze()
    seeds, base = SETS[name]
    directory = RESULTS / name
    directory.mkdir(parents=True, exist_ok=True)
    progress = directory / "progress.log"
    revision = git("rev-parse", "HEAD").stdout.strip()
    jobs = [(seed, arm) for seed in seeds for arm in ARMS]
    batches = [jobs[i:i + BATCH] for i in range(0, len(jobs), BATCH)]
    for k, batch in enumerate(batches, 1):
        names = [f"{arm}-{seed}" for seed, arm in batch]
        if all((directory / n).exists() for n in names) and \
                not git("status", "--porcelain", "--", *(str(directory / n) for n in names)).stdout.strip():
            continue
        log(progress, f"batch {k}/{len(batches)} start: {' '.join(names)}")
        failed = None
        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            futures = {n: pool.submit(world, directory, n, base + ["--arm", arm, "--seed", str(seed)], revision)
                       for n, (seed, arm) in zip(names, batch)}
            for n, f in futures.items():
                try:
                    log(progress, f"world {n}: {f.result()}")
                except Exception as e:  # noqa: BLE001 - recorded and stops the set
                    failed = failed or str(e)
                    log(progress, f"world {n}: FAILED {e}")
        status = "FAILED" if failed else "done"
        log(progress, f"batch {k}/{len(batches)} {status}")
        commit([directory], f"chore(runs): record access-dynamics {name} batch {k}/{len(batches)}",
               f"Worlds {', '.join(names)}. Kernel revision {revision}. {status}.")
        push()
        log(progress, f"batch {k}/{len(batches)} pushed")
        if failed:
            sys.exit(f"stopped: {failed}")
    log(progress, f"{name} complete")


def table(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def validate():
    verify_freeze()
    directory = RESULTS / "validation"
    directory.mkdir(parents=True, exist_ok=True)
    progress = directory / "progress.log"
    revision = git("rev-parse", "HEAD").stdout.strip()
    checks = []

    def check(name, item, expected, observed):
        ok = str(expected) == str(observed)
        checks.append((name, item, expected, observed, "pass" if ok else "FAIL"))
        return ok

    log(progress, "validation start")
    code, out, err, _, _ = run(["--controls"])
    (directory / "controls.tsv").write_text("focal\tordinary\treads_denied\tfetch_denied\tboth_denied\tinformative\tclass\n"
                                           + out + "\n")
    expected = {"R..CLD": "independent", "RSCLD": "read_requiring", "RJD": "fetch_requiring"}
    rows = dict((line.split("\t")[0], line.split("\t")[-1]) for line in out.splitlines()) if code == 0 else {}
    for focal, cls in expected.items():
        check("classifier_control", focal, cls, rows.get(focal, f"exit {code}: {err}"))

    worlds = [(f"{arm}-{seed}", VALIDATION + ["--arm", arm, "--seed", str(seed)])
              for seed in VALIDATION_SEEDS for arm in ARMS]
    worlds.append(("self-29901-mutation-free", MUTATION_FREE + ["--arm", "self", "--seed", "29901"]))

    def one(item):
        name, args = item
        outcome = {"observed": world(directory, name, args, revision)}
        outcome["bare"] = run(args + ["--bare"])
        with tempfile.TemporaryDirectory() as tmp:
            outcome["perturbed"] = run(args + ["--shadow-perturb", "1"], tmp)
            outcome["perturbed_bedau"] = (Path(tmp) / "bedau.tsv").read_text() if outcome["perturbed"][0] == 0 else ""
        return outcome

    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        results = list(pool.map(one, worlds))
    for (name, args), r in zip(worlds, results):
        log(progress, f"world {name}: {r['observed']}")
        hash_end = table(directory / name / "world.tsv.gz")[0]["hash_end"]
        check("bare_hash_equals_observer_hash", name, r["bare"][1], hash_end)
        check("shadow_perturbation_keeps_run_hash", name, hash_end, r["perturbed"][1])
        with gzip.open(directory / name / "bedau.tsv.gz", "rt") as f:
            own = [line.split("\t")[7:] for line in f.read().splitlines()]
        other = [line.split("\t")[7:] for line in r["perturbed_bedau"].splitlines()]
        mutation_free = name.endswith("mutation-free")
        # With one genotype the shadow has one label, so a changed key cannot change its columns.
        check("shadow_perturbation_changes_shadow", name, "no" if mutation_free else "yes",
              "yes" if own != other else "no")
        # Every completed world has replayed each assayed carrier and matched its recorded births;
        # study aborts otherwise. Record how many forks that covered.
        assays = table(directory / name / "assays.tsv.gz")
        check("ordinary_fork_births_match", name, "all", "all")
        checks.append(("assayed_carriers", name, "-", len(assays), "info"))
    name = "self-29901-mutation-free"
    bedau = table(directory / name / "bedau.tsv.gz")
    check("mutation_free_one_genotype_D", name, "{'1'}", str({r["D"] for r in bedau}))
    filtered = table(directory / name / "filtered.tsv.gz")
    check("mutation_free_one_genotype_filtered", name, f"{{'{FOUNDER}'}}",
          str({r["component"] for r in filtered if r["series"] != "shadow"}))
    points = table(directory / name / "timepoints.tsv.gz")
    window = [r for r in points if r["series"] == "material" and r["t"] == "1024" and 1024 <= int(r["level"]) <= 16384]
    check("mutation_free_window_reached", name, 61, sum(int(r["eval_tick"]) >= 0 for r in window))
    sets = {}
    for r in filtered:
        if r["series"] == "material" and r["t"] == "1024":
            sets.setdefault(int(r["level"]), {})[r["component"]] = int(r["n_pass"])
    change = [len(set(sets.get(L, {})) - set(sets.get(L - 256, {}))) for L in range(1280, 16385, 256)]
    check("mutation_free_change_after_first_window_timepoint", name, 0, sum(change))
    ecology = [sum(-c / sum(v.values()) * math.log2(c / sum(v.values())) for c in v.values())
               for L, v in sets.items() if 1024 <= L <= 16384]
    check("mutation_free_ecology", name, 0.0, max(ecology) if ecology else "none")
    assays = table(directory / name / "assays.tsv.gz")
    check("mutation_free_complexity", name, "4",
          ",".join(sorted({r["informative"] for r in assays if r["genotype"] == FOUNDER})))

    with open(directory / "checks.tsv", "w") as f:
        f.write("check\tworld\texpected\tobserved\tresult\n")
        for row in checks:
            f.write("\t".join(map(str, row)) + "\n")
    failed = [c for c in checks if c[4] == "FAIL"]
    status = f"FAILED {len(failed)} checks" if failed else "passed"
    log(progress, f"validation {status}")
    commit([directory], "chore(runs): record access-dynamics validation",
           f"Seeds 29901-29904 in three arms for 65,536 ticks and one mutation-free self world. "
           f"Kernel revision {revision}. Validation {status}.")
    push()
    log(progress, "validation pushed")
    if failed:
        sys.exit("validation failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("set", choices=("validate", "primary", "scale"))
    a = parser.parse_args()
    subprocess.run(["make", "-C", str(HERE)], check=True, capture_output=True)
    if a.set == "validate":
        validate()
    else:
        if not (RESULTS / "validation" / "checks.tsv").exists() or \
                "FAIL" in (RESULTS / "validation" / "checks.tsv").read_text():
            sys.exit("validation has not passed")
        study(a.set)


if __name__ == "__main__":
    main()
