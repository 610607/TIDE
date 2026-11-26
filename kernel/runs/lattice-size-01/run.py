"""Run the lattice-size study in resumable batches and archive every batch in git.

  python3 run.py validate   # controls, observer identity, regression, origin replay, extended-window timing
  python3 run.py primary    # sizes 24, 32, 48, 64 x seeds 32001-32032, 16 batches of 8 worlds

A world is complete when results/<set>/L<size>-<seed>/ exists; it is written to a temporary
directory and renamed. A rerun skips complete worlds and commits any batch left uncommitted.
--deadline SECONDS starts no new batch unless the elapsed time plus 1.25 times the longest batch so
far (or --first-batch before any batch has run) stays within it, so that a run under a wall-clock
limit ends between batches.

Validation records the digests of the files it tested in results/validation/digests.sha256. The
primary set refuses to run unless revision.sha256 exists, matches the files, and equals those
digests: the code is frozen after it passed validation. Validation also decides agreed item 13, the
extended window, from its timings; the decision is read from results/validation/extended.tsv.
"""
import argparse
import csv
import gzip
import hashlib
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
BINARY = ROOT / "kernel/build/lattice-size/study"
RESULTS = HERE / "results"
FROZEN = ("kernel/runs/lattice-size-01/Makefile", "kernel/runs/lattice-size-01/analyze.py",
          "kernel/runs/lattice-size-01/protocol.md", "kernel/runs/lattice-size-01/run.py",
          "kernel/runs/lattice-size-01/study.cpp", "kernel/src/vm.cpp", "kernel/src/vm.hpp",
          "docs/research/lattice-size-rq.md")
TABLES = ("world", "timepoints", "filtered", "bedau", "collapsed", "assays", "ledger", "census", "spatial")
SIZES = (24, 32, 48, 64)
FILTERS = (576, 1024, 2304, 4096)          # t = N at 24, 32, 48 and 64
TEST_FILTERS = (36, 64, 144, 256)          # the same divided by 16, for 65,536-tick validation worlds
BATCH, JOBS = 8, 4
HORIZON = 1 << 22
SEEDS = range(32001, 32033)
VALIDATION_SEEDS = range(29941, 29945)
EXTENDED = ["--extend", "1024", "65536"]
EXTENDED_LIMIT = 0.10
CELL = ["--arm", "read_fetch", "--reclamation", "retain"]
FOCUS = "RCCCJD".encode().hex()
FOUNDER = "R..CLD".encode().hex()
REGRESSION_SOURCE = ROOT / "kernel/runs/dead-code-01/results/primary/read_fetch-retain-31001"
REGRESSION = ["--size", "32", "32", "--filter", "1024", "256", "16384", "--sensitivity", "256,2048",
              "--horizon", str(HORIZON), "--seed", "31001"] + CELL
REGRESSION_TABLES = ("timepoints", "filtered", "bedau", "collapsed", "ledger", "census")
TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01GJrPGAhYtymMTQHquWQkvB")


def size_args(size, filters, step, end, horizon):
    t = filters[SIZES.index(size)]
    others = ",".join(str(x) for x in filters if x != t)
    return ["--size", str(size), str(size), "--filter", str(t), str(step), str(end), "--sensitivity", others,
            "--horizon", str(horizon)] + CELL


def primary_args(size, seed, extended):
    return size_args(size, FILTERS, 256, 16384, HORIZON) + (EXTENDED if extended else []) + ["--seed", str(seed)]


def test_args(size, seed):
    return size_args(size, TEST_FILTERS, 16, 1024, 1 << 16) + ["--extend", "64", "4096", "--seed", str(seed)]


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


def extended_decision():
    path = RESULTS / "validation" / "extended.tsv"
    if not path.exists():
        sys.exit("validation has not decided the extended window")
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    return rows[0]["adopt"] == "1"


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
    """Run one observed world into directory/name; raise on any failure. Returns seconds."""
    dest = directory / name
    if dest.exists():
        return None
    tmp = Path(tempfile.mkdtemp(prefix=f".tmp-{name}-", dir=directory))
    try:
        code, out, err, seconds, rss = run(args, tmp)
        record = (f"command\tstudy {' '.join(args)}\nrevision\t{revision}\nexit\t{code}\nhash_end\t{out}\n"
                  f"seconds\t{seconds:.1f}\nmax_rss_kb\t{rss}\nstderr\t{err}\n")
        if code != 0:
            (directory / f"{name}.failed.txt").write_text(record)
            raise RuntimeError(f"{name} failed: {err}")
        for table_name in TABLES:
            src = tmp / f"{table_name}.tsv"
            with open(src, "rb") as f, open(tmp / f"{table_name}.tsv.gz", "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as z:
                    shutil.copyfileobj(f, z)
            src.unlink()
        (tmp / "log.txt").write_text(record)
        tmp.rename(dest)
        return seconds
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


def primary(deadline, first_batch):
    verify_freeze()
    extended = extended_decision()
    started = time.monotonic()
    directory = RESULTS / "primary"
    directory.mkdir(parents=True, exist_ok=True)
    progress = directory / "progress.log"
    revision = git("rev-parse", "HEAD").stdout.strip()
    # Two seeds per batch, all four sizes, largest first so that four workers stay busy.
    pairs = [SEEDS[i:i + 2] for i in range(0, len(SEEDS), 2)]
    batches = [[(size, seed) for size in reversed(SIZES) for seed in pair] for pair in pairs]
    longest = first_batch
    for k, batch in enumerate(batches, 1):
        names = [f"L{size}-{seed}" for size, seed in batch]
        if all((directory / n).exists() for n in names) and \
                not git("status", "--porcelain", "--", *(str(directory / n) for n in names)).stdout.strip():
            continue
        elapsed = time.monotonic() - started
        if deadline and elapsed + 1.25 * longest > deadline:
            log(progress, f"stopping before batch {k}/{len(batches)}: deadline")
            commit([directory], "chore(runs): record lattice-size primary progress", f"Kernel revision {revision}.")
            push()
            return
        log(progress, f"batch {k}/{len(batches)} start{' (extended window)' if extended else ''}: {' '.join(names)}")
        begun, failed = time.monotonic(), None
        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            futures = {n: pool.submit(world, directory, n, primary_args(size, seed, extended), revision)
                       for n, (size, seed) in zip(names, batch)}
            for n, f in futures.items():
                try:
                    s = f.result()
                    log(progress, f"world {n}: {'skipped' if s is None else f'{s:.0f} s'}")
                except Exception as e:  # noqa: BLE001 - recorded and stops the set
                    failed = failed or str(e)
                    log(progress, f"world {n}: FAILED {e}")
        longest = max(longest, time.monotonic() - begun)
        status = "FAILED" if failed else "done"
        log(progress, f"batch {k}/{len(batches)} {status}")
        commit([directory], f"chore(runs): record lattice-size primary batch {k}/{len(batches)}",
               f"Worlds {', '.join(names)}. Kernel revision {revision}. {status}.")
        push()
        log(progress, f"batch {k}/{len(batches)} pushed")
        if failed:
            sys.exit(f"stopped: {failed}")
    log(progress, "primary complete")
    commit([directory], "chore(runs): record lattice-size primary completion", f"Kernel revision {revision}.")
    push()


def table(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def gz_text(path):
    with gzip.open(path, "rt") as f:
        return f.read()


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

    def info(name, item, observed):
        checks.append((name, item, "-", observed, "info"))

    log(progress, "validation start")
    # 1. Controls.
    code, out, err, _, _ = run(["--controls"])
    (directory / "controls.tsv").write_text(out + "\n")
    lines = {tuple(line.split("\t")[:2]): line.split("\t")[2:] for line in out.splitlines()} if code == 0 else {}
    for name, cls in (("R..CLD", "independent"), ("RSCLD", "read_requiring"), ("RJD", "fetch_requiring")):
        check("classifier_control", name, cls, (lines.get(("classifier", name)) or [f"exit {code}: {err}"])[-1])
    expected_spatial = {  # carriers, clusters, largest, pairs, xi, censored, rho(1..4)
        "empty": "0 0 0 0 -1 0 nan,nan,nan,nan",
        "wrap_pair_and_single": "3 2 2 2 1 0 0.1257,-0.0492,-0.0492,-0.0492",
        "row": "8 1 8 16 4 1 0.4286,0.4286,0.4286,0.4286",
        "checkerboard": "32 32 1 0 1 0 -1.0000,1.0000,-1.0000,1.0000",
        "stripes2": "32 2 16 96 2 0 0.5000,0.0000,0.5000,1.0000",
    }
    for name, value in expected_spatial.items():
        check("spatial_fixture", name, value, " ".join(lines.get(("spatial", name), ["missing"])))
    for name, value in (("from_other", "1"), ("from_focus", "0"), ("other_child", "0")):
        check("origin_rule_fixture", name, value, " ".join(lines.get(("origin", name), ["missing"])))

    # 2. Worlds, run four at a time.
    plain = {name: args for name, args in
             [(f"L{s}-{seed}", test_args(s, seed)) for seed in VALIDATION_SEEDS for s in SIZES]}
    timing = {}
    for s in (24, 32):
        base = size_args(s, FILTERS, 256, 16384, HORIZON) + ["--seed", str(VALIDATION_SEEDS[0])]
        timing[f"timing-L{s}-{VALIDATION_SEEDS[0]}"] = base
        timing[f"timing-L{s}-{VALIDATION_SEEDS[0]}-extended"] = base + EXTENDED
    mutation_free = {f"L24-{VALIDATION_SEEDS[0]}-mutation-free":
                     size_args(24, FILTERS, 256, 16384, 1 << 20) + ["--mutation", "0", "--focus", "R..CLD",
                                                                     "--seed", str(VALIDATION_SEEDS[0])]}
    regression = {"regression-31001": REGRESSION}
    jobs = {**regression, **plain, **mutation_free}

    def one(item):
        name, args = item
        r = {"seconds": world(directory, name, args, revision)}
        if name in plain:
            r["bare"] = run(args + ["--bare"])
            with tempfile.TemporaryDirectory() as tmp:
                r["perturbed"] = run(args + ["--shadow-perturb", "1"], tmp)
                r["perturbed_bedau"] = (Path(tmp) / "bedau.tsv").read_text() if r["perturbed"][0] == 0 else ""
        return r

    # The four timing worlds run alone and together, so that each pair shares its load.
    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        results = dict(zip(timing, pool.map(one, timing.items())))
    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        results.update(zip(jobs, pool.map(one, jobs.items())))
    for name, r in results.items():
        log(progress, f"world {name}: {r['seconds']}")

    for name, args in plain.items():
        r = results[name]
        world_info = table(directory / name / "world.tsv.gz")[0]
        hash_end = world_info["hash_end"]
        check("bare_hash_equals_observer_hash", name, r["bare"][1], hash_end)
        check("shadow_perturbation_keeps_run_hash", name, hash_end, r["perturbed"][1])
        own = [line.split("\t")[7:] for line in gz_text(directory / name / "bedau.tsv.gz").splitlines()]
        other = [line.split("\t")[7:] for line in r["perturbed_bedau"].splitlines()]
        check("shadow_perturbation_changes_shadow", name, "yes", "yes" if own != other else "no")
        # The study aborts unless every ordinary fork reproduced the carrier's recorded births.
        check("ordinary_fork_births_match", name, "all", "all")
        info("assayed_carriers", name, world_info["assayed"])
        spatial = table(directory / name / "spatial.tsv.gz")
        census = {r["level"]: r for r in table(directory / name / "census.tsv.gz")}
        check("spatial_carriers_equal_census_focus", name, "yes",
              "yes" if all(census[r["level"]]["focus"] == r["carriers"] for r in spatial if r["grid"] == "main") else "no")

    # 3. Regression against dead-code-01's committed read_fetch-retain-31001.
    name = "regression-31001"
    for t in REGRESSION_TABLES:
        same = gz_text(directory / name / f"{t}.tsv.gz") == gz_text(REGRESSION_SOURCE / f"{t}.tsv.gz")
        check("regression_identical", f"{name}/{t}", "identical", "identical" if same else "different")
    new, old = table(directory / name / "world.tsv.gz")[0], table(REGRESSION_SOURCE / "world.tsv.gz")[0]
    for column in ("hash_end", "event_digest", "births", "deaths", "G_material", "P4_run", "P4_shadow"):
        check("regression_world", f"{name}/{column}", old[column], new[column])
    info("regression_seconds", name, f"{results[name]['seconds']:.1f} (dead-code 383-440 s)")

    # 4. Replay the regression world's first focus origin with the bare kernel.
    tick, site, exe = new["first_origin_tick"], new["first_origin_site"], new["first_origin_executor_site"]
    code, out, err, _, _ = run(REGRESSION + ["--check-origin", tick, site, exe])
    fields = out.split("\t") if code == 0 else [f"exit {code}: {err}"]
    check("origin_replay_executor_bytes", name, new["first_origin_executor_genotype"], fields[0])
    check("origin_replay_birth", name, "1 1 1", " ".join(fields[1:4]))
    check("origin_parent_not_focus", name, "yes",
          "yes" if new["first_origin_parent_genotype"] not in ("", FOCUS) else "no")
    info("first_origin", name, f"tick {tick}, site {site}, executor {exe}, substituted {new['first_origin_substituted']}")

    # 5. Mutation-free world with the founder as focus: one genotype and no origins.
    name = f"L24-{VALIDATION_SEEDS[0]}-mutation-free"
    w = table(directory / name / "world.tsv.gz")[0]
    check("mutation_free_focus_births_equal_births", name, w["births"], w["focus_births"])
    check("mutation_free_no_origins", name, 0, w["focus_origins"])
    filtered = table(directory / name / "filtered.tsv.gz")
    check("mutation_free_one_genotype_filtered", name, f"{{'{FOUNDER}'}}",
          str({r["component"] for r in filtered if r["series"] != "shadow"}))
    check("mutation_free_one_genotype_D", name, "{'1'}", str({r["D"] for r in table(directory / name / "bedau.tsv.gz")}))
    assays = table(directory / name / "assays.tsv.gz")
    check("mutation_free_complexity", name, "4", ",".join(sorted({r["informative"] for r in assays})))
    census = {r["level"]: r for r in table(directory / name / "census.tsv.gz")}
    check("mutation_free_carriers_equal_alive", name, "yes",
          "yes" if all(census[r["level"]]["alive"] == r["carriers"]
                       for r in table(directory / name / "spatial.tsv.gz") if r["grid"] == "main") else "no")

    # 6. Extended window (agreed item 13): same run, extra rows only; adopt if under 10% extra time.
    overheads = []
    for s in (24, 32):
        a, b = directory / f"timing-L{s}-{VALIDATION_SEEDS[0]}", directory / f"timing-L{s}-{VALIDATION_SEEDS[0]}-extended"
        wa, wb = table(a / "world.tsv.gz")[0], table(b / "world.tsv.gz")[0]
        check("extended_keeps_run_hash", f"L{s}", wa["hash_end"], wb["hash_end"])
        for t, drop in (("timepoints", "material_ext\t"), ("filtered", "material_ext\t"), ("spatial", "ext\t")):
            x = gz_text(a / f"{t}.tsv.gz")
            y = "".join(line for line in gz_text(b / f"{t}.tsv.gz").splitlines(True) if not line.startswith(drop))
            check("extended_adds_rows_only", f"L{s}/{t}", "identical", "identical" if x == y else "different")
        for t in ("census", "assays", "ledger", "bedau", "collapsed"):
            same = gz_text(a / f"{t}.tsv.gz") == gz_text(b / f"{t}.tsv.gz")
            check("extended_adds_rows_only", f"L{s}/{t}", "identical", "identical" if same else "different")
        ta, tb = results[a.name]["seconds"], results[b.name]["seconds"]
        overheads.append((tb - ta) / ta)
        info("extended_overhead", f"L{s}", f"{ta:.1f} s -> {tb:.1f} s ({100 * (tb - ta) / ta:+.1f}%)")
        info("unreached_material_ext", f"L{s}", wb["unreached_material_ext"])
    adopt = int(max(overheads) < EXTENDED_LIMIT)
    with open(directory / "extended.tsv", "w") as f:
        f.write("max_overhead\tlimit\tadopt\n" + f"{max(overheads):.4f}\t{EXTENDED_LIMIT}\t{adopt}\n")
    info("extended_window_adopted", "item 13", adopt)

    # 7. The analysis script runs end to end on the 16 short validation worlds.
    p = subprocess.run([sys.executable, str(HERE / "analyze.py"), "test"], capture_output=True, text=True)
    check("analysis_test_runs", "analyze.py test", 0, p.returncode)
    if p.returncode:
        info("analysis_test_stderr", "analyze.py test", p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "")

    with open(directory / "checks.tsv", "w") as f:
        f.write("check\tworld\texpected\tobserved\tresult\n")
        for row in checks:
            f.write("\t".join(map(str, row)) + "\n")
    failed = [c for c in checks if c[4] == "FAIL"]
    status = f"FAILED {len(failed)} checks" if failed else "passed"
    if not failed and digests() == tested:
        (directory / "digests.sha256").write_text(tested)
    log(progress, f"validation {status}")
    commit([directory], "chore(runs): record lattice-size validation",
           f"Controls, seeds {VALIDATION_SEEDS[0]}-{VALIDATION_SEEDS[-1]} at four sizes for 65,536 ticks, the "
           f"dead-code 31001 regression world, timing worlds and a mutation-free world. Kernel revision "
           f"{revision}. Validation {status}.")
    push()
    log(progress, "validation pushed")
    if failed:
        sys.exit("validation failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("set", choices=("validate", "primary"))
    parser.add_argument("--deadline", type=float, default=0, help="start no batch that would end after this")
    parser.add_argument("--first-batch", type=float, default=3600, help="batch length assumed before one has run")
    a = parser.parse_args()
    subprocess.run(["make", "-C", str(HERE)], check=True, capture_output=True)
    if a.set == "validate":
        validate()
    else:
        primary(a.deadline, a.first_batch)


if __name__ == "__main__":
    main()
