"""Run the dead-code study in resumable batches and archive every batch in git.

  python3 run.py validate   # observer, fork, shadow, self-null and residue checks; must pass first
  python3 run.py primary    # 32 x 32, seeds 31001-31032, five cells, 20 batches of 8 worlds
  python3 run.py scale      # 64 x 64, seeds 31101-31108, four cells, 4 batches of 8 worlds

A world is complete when results/<set>/<cell>-<seed>/ exists; it is written to a temporary
directory and renamed. A rerun skips complete worlds and commits any batch left uncommitted.
--stop-after SECONDS starts no new batch once that much time has passed, so that a run under a
wall-clock limit ends between batches.

Validation records the digests of the files it tested in results/validation/digests.sha256. The
study sets refuse to run unless revision.sha256 exists, matches the files, and equals those
digests: the code is frozen after it passed validation.
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
BINARY = ROOT / "kernel/build/dead-code/study"
RESULTS = HERE / "results"
FROZEN = ("kernel/runs/dead-code-01/Makefile", "kernel/runs/dead-code-01/analyze.py",
          "kernel/runs/dead-code-01/protocol.md", "kernel/runs/dead-code-01/run.py",
          "kernel/runs/dead-code-01/study.cpp", "kernel/src/vm.cpp", "kernel/src/vm.hpp",
          "docs/research/dead-code-rq.md")
PRIMARY_CELLS = (("self", "retain"), ("read", "retain"), ("read", "empty"), ("read_fetch", "retain"),
                 ("read_fetch", "empty"))
SCALE_CELLS = PRIMARY_CELLS[1:]
VALIDATION_CELLS = PRIMARY_CELLS + (("self", "empty"),)
TABLES = ("world", "timepoints", "filtered", "bedau", "collapsed", "assays", "ledger", "census", "neutrality")
BATCH, JOBS = 8, 4
PRIMARY = ["--size", "32", "32", "--filter", "1024", "256", "16384", "--sensitivity", "256,2048"]
SETS = {
    "primary": (range(31001, 31033), PRIMARY_CELLS, PRIMARY + ["--horizon", str(1 << 22)]),
    "scale": (range(31101, 31109), SCALE_CELLS, ["--size", "64", "64", "--horizon", str(1 << 21),
                                                 "--filter", "4096", "1024", "16384", "--sensitivity", ""]),
}
VALIDATION_SEEDS = range(29921, 29925)
VALIDATION = PRIMARY + ["--horizon", str(1 << 16)]
MUTATION_FREE = PRIMARY + ["--horizon", str(1 << 20), "--mutation", "0"]
FOUNDER = "R..CLD".encode().hex()
# Columns that may differ between self-retain and self-empty worlds: the reclamation label, the
# state hash, timings, and census counts of free banks that hold bytes.
SELF_NULL_EXEMPT = {"world": {"reclamation", "hash_end", "pass1_seconds", "pass2_seconds"},
                    "census": {"free_with_bytes", "free_empty", "focus_bearing_free_with_bytes",
                               "focus_bearing_free_empty", "focus_neighbors_free_with_bytes"}}
TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01GJrPGAhYtymMTQHquWQkvB")


def log(path, line):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a") as f:
        f.write(f"{stamp}\t{line}\n")
    print(f"{stamp} {line}", flush=True)


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=check, capture_output=True, text=True)


def digests():
    return "".join(f"{hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}  {name}\n" for name in FROZEN)


def verify_freeze():
    """Refuse to run unless the frozen files match revision.sha256 and validation tested them."""
    frozen = HERE / "revision.sha256"
    tested = RESULTS / "validation" / "digests.sha256"
    if not frozen.exists():
        sys.exit("not frozen: revision.sha256 is missing")
    if frozen.read_text() != digests():
        sys.exit("frozen files changed since revision.sha256")
    if not tested.exists() or tested.read_text() != frozen.read_text():
        sys.exit("validation did not test the frozen files")
    checks = RESULTS / "validation" / "checks.tsv"
    if not checks.exists() or "\tFAIL\n" in checks.read_text():
        sys.exit("validation has not passed")


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


def cell_args(arm, reclamation, seed):
    return ["--arm", arm, "--reclamation", reclamation, "--seed", str(seed)]


def study(name, stop_after):
    verify_freeze()
    started = time.monotonic()
    seeds, cells, base = SETS[name]
    directory = RESULTS / name
    directory.mkdir(parents=True, exist_ok=True)
    progress = directory / "progress.log"
    revision = git("rev-parse", "HEAD").stdout.strip()
    jobs = [(seed, arm, rec) for seed in seeds for arm, rec in cells]
    batches = [jobs[i:i + BATCH] for i in range(0, len(jobs), BATCH)]
    for k, batch in enumerate(batches, 1):
        names = [f"{arm}-{rec}-{seed}" for seed, arm, rec in batch]
        if all((directory / n).exists() for n in names) and \
                not git("status", "--porcelain", "--", *(str(directory / n) for n in names)).stdout.strip():
            continue
        if stop_after and time.monotonic() - started > stop_after:
            log(progress, f"stopping before batch {k}/{len(batches)}: time limit")
            commit([directory], f"chore(runs): record dead-code {name} progress", f"Kernel revision {revision}.")
            push()
            return
        log(progress, f"batch {k}/{len(batches)} start: {' '.join(names)}")
        failed = None
        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            futures = {n: pool.submit(world, directory, n, base + cell_args(arm, rec, seed), revision)
                       for n, (seed, arm, rec) in zip(names, batch)}
            for n, f in futures.items():
                try:
                    log(progress, f"world {n}: {f.result()}")
                except Exception as e:  # noqa: BLE001 - recorded and stops the set
                    failed = failed or str(e)
                    log(progress, f"world {n}: FAILED {e}")
        status = "FAILED" if failed else "done"
        log(progress, f"batch {k}/{len(batches)} {status}")
        commit([directory], f"chore(runs): record dead-code {name} batch {k}/{len(batches)}",
               f"Worlds {', '.join(names)}. Kernel revision {revision}. {status}.")
        push()
        log(progress, f"batch {k}/{len(batches)} pushed")
        if failed:
            sys.exit(f"stopped: {failed}")
    log(progress, f"{name} complete")
    commit([directory], f"chore(runs): record dead-code {name} completion", f"Kernel revision {revision}.")
    push()


def table(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def validate():
    directory = RESULTS / "validation"
    directory.mkdir(parents=True, exist_ok=True)
    progress = directory / "progress.log"
    revision = git("rev-parse", "HEAD").stdout.strip()
    tested = digests()
    checks = []

    def check(name, item, expected, observed):
        ok = str(expected) == str(observed)
        checks.append((name, item, expected, observed, "pass" if ok else "FAIL"))
        return ok

    log(progress, "validation start")
    code, out, err, _, _ = run(["--controls"])
    (directory / "controls.tsv").write_text("focal\tordinary\treads_denied\tfetch_denied\tboth_denied\tinformative"
                                           "\tclass\tresidue_cleared\tresidue_requiring\n" + out + "\n")
    expected = {"R..CLD": "independent\t1\t0", "RSCLD": "read_requiring\t1\t0", "RJD": "fetch_requiring\t1\t0",
                "residue": "fetch_requiring\t0\t1"}
    rows = {line.split("\t")[0]: "\t".join(line.split("\t")[6:]) for line in out.splitlines()} if code == 0 else {}
    for focal, cls in expected.items():
        check("classifier_control", focal, cls, rows.get(focal, f"exit {code}: {err}"))

    worlds = [(f"{arm}-{rec}-{seed}", VALIDATION + cell_args(arm, rec, seed))
              for seed in VALIDATION_SEEDS for arm, rec in VALIDATION_CELLS]
    worlds.append((f"self-retain-{VALIDATION_SEEDS[0]}-mutation-free",
                   MUTATION_FREE + cell_args("self", "retain", VALIDATION_SEEDS[0])))

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
        info = table(directory / name / "world.tsv.gz")[0]
        hash_end = info["hash_end"]
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
        checks.append(("neutrality_genotypes", name, "-", info["neutrality_genotypes"], "info"))
        visible = info["reclamation"] == "retain" and info["arm"] != "self"
        changed = sum(a["residue_cleared"] != a["ordinary"] for a in assays)
        if visible:
            checks.append(("residue_fork_changed_births", name, "-", changed, "info"))
        else:
            check("residue_fork_null_without_visible_residue", name, 0, changed)
        if info["reclamation"] == "empty":
            ledger = table(directory / name / "ledger.tsv.gz")
            used = sum(int(row[c]) for row in ledger for c in ("bytes_free", "fetch_free", "residue_bytes",
                                                                "residue_fetch"))
            check("empty_reclamation_no_residue_source", name, 0, used)
            census = table(directory / name / "census.tsv.gz")
            check("empty_reclamation_no_free_bytes", name, 0, sum(int(row["free_with_bytes"]) for row in census))

    # Self null: retain and empty give identical events, genealogies and outputs in the self arm.
    for seed in VALIDATION_SEEDS:
        a, b = directory / f"self-retain-{seed}", directory / f"self-empty-{seed}"
        for t in TABLES:
            x, y = table(a / f"{t}.tsv.gz"), table(b / f"{t}.tsv.gz")
            exempt = SELF_NULL_EXEMPT.get(t, set())
            same = len(x) == len(y) and all({k: v for k, v in p.items() if k not in exempt} ==
                                            {k: v for k, v in q.items() if k not in exempt} for p, q in zip(x, y))
            check(f"self_null_{t}", f"self-{seed}", "identical", "identical" if same else "different")
        ea = table(a / "world.tsv.gz")[0]["event_digest"]
        check("self_null_event_digest", f"self-{seed}", ea, table(b / "world.tsv.gz")[0]["event_digest"])

    name = f"self-retain-{VALIDATION_SEEDS[0]}-mutation-free"
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
    neutral = table(directory / name / "neutrality.tsv.gz")
    check("mutation_free_neutrality_sampled", name, f"{{'{FOUNDER}'}}", str({r["genotype"] for r in neutral}))

    with open(directory / "checks.tsv", "w") as f:
        f.write("check\tworld\texpected\tobserved\tresult\n")
        for row in checks:
            f.write("\t".join(map(str, row)) + "\n")
    failed = [c for c in checks if c[4] == "FAIL"]
    status = f"FAILED {len(failed)} checks" if failed else "passed"
    if not failed and digests() == tested:
        (directory / "digests.sha256").write_text(tested)
    log(progress, f"validation {status}")
    commit([directory], "chore(runs): record dead-code validation",
           f"Seeds {VALIDATION_SEEDS[0]}-{VALIDATION_SEEDS[-1]} in six cells for 65,536 ticks and one mutation-free "
           f"self world. Kernel revision {revision}. Validation {status}.")
    push()
    log(progress, "validation pushed")
    if failed:
        sys.exit("validation failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("set", choices=("validate", "primary", "scale"))
    parser.add_argument("--stop-after", type=float, default=0, help="start no batch after this many seconds")
    a = parser.parse_args()
    subprocess.run(["make", "-C", str(HERE)], check=True, capture_output=True)
    if a.set == "validate":
        validate()
    else:
        study(a.set, a.stop_after)


if __name__ == "__main__":
    main()
