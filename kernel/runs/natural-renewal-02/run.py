"""Run and verify the fixed untreated renewal cohort without changing the reference VM."""
import argparse
import fcntl
import gzip
import hashlib
import os
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.with_name("natural-renewal-01")
HISTORY = OLD.with_name("trait-lineage-01")
VM = ROOT / "kernel/src"
BUILD = HERE / "build"
RESULTS = HERE / "results/primary"
RECEIPT = BUILD / "validated.sha256"
FIRST, LAST, SIZE, BATCHES = 100001, 105300, 100, 53
VALIDATION = (26720, 26757, 27266, 27319)
RAW = ("world.tsv", "nodes.tsv.gz", "contacts.tsv")
TABLES = (*RAW, "changed.tsv", "starts.tsv", "endpoints.tsv")
STAMP = "complete.sha256"
INPUTS = (
    HERE / "protocol.md", HERE / "run.py", HERE / "README.md",
    *(OLD / name for name in ("protocol.md", "field.cpp", "run.py", "analyze.py", "pedigree.py", "controls.py")),
    HISTORY / "field.cpp", OLD.with_name("vacancy-01") / "common.hpp",
    VM / "vm.cpp", VM / "vm.hpp", VM / "assay.cpp", VM / "assay.hpp", VM.parent / "tests/vm_tests.cpp",
    *(OLD / "results" / name for name in TABLES),
    *(OLD.with_name("partner-placement-01") / "results" / name
      for name in ("branches.tsv", "cases.tsv", "nodes.tsv.gz")),
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    return "".join(f"{digest(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in INPUTS)


def compile_cpp(binary, optimization, *args):
    subprocess.run([os.environ.get("CXX", "c++"), optimization, "-Wall", "-Wextra", "-Werror",
                    "-std=c++20", f"-I{VM}", VM / "vm.cpp", *args, "-o", binary], check=True)
    return binary


def field(work, optimization, condition):
    # Generate history.hpp exactly as the original Makefile does.
    history, marker, _ = (HISTORY / "field.cpp").read_bytes().partition(b"\nint main(")
    require(marker, "historical main not found")
    (work / "history.hpp").write_bytes(history + b"\n")
    source = (OLD / "field.cpp").read_bytes()
    guard = b'seed>=26689 && seed<=27712,"seed outside protocol"'
    require(source.count(guard) == 1, "historical seed guard not found exactly once")
    generated = work / "field.cpp"
    generated.write_bytes(source.replace(guard, condition.encode("ascii") + b',"seed outside protocol"'))
    return compile_cpp(work / "field", optimization, f"-I{work}", f"-I{HISTORY}", generated)


def score_batch(analysis, binary, seeds, directory, reverse=False):
    changed, starts, endpoints = [], [], []
    with ExitStack() as stack:
        streams = []
        for name in RAW:
            out = stack.enter_context((directory / name).open("wb"))
            if name.endswith(".gz"):
                out = stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=out,
                                                       mtime=0, compresslevel=6))
            streams.append(out)
        with tempfile.TemporaryDirectory(prefix="world-", dir=BUILD) as tmp:
            world_dir = Path(tmp)
            for i, seed in enumerate(seeds):
                subprocess.run([binary, str(seed), tmp, *(["--reverse"] if reverse else [])], check=True)
                data = []
                for name, stream in zip(RAW, streams):
                    path = world_dir / name.removesuffix(".gz")
                    raw = path.read_bytes()
                    stream.write(raw if i == 0 else raw.partition(b"\n")[2])
                    records = list(analysis.rows(path))
                    require(all(r["seed"] == str(seed) for r in records), f"{path.name}: wrong seed {seed}")
                    data.append(records)
                worlds, nodes, contacts = data
                w, = worlds
                people, contact = ({int(r["id"]): r for r in rows} for rows in (nodes, contacts))
                require(len(people) == len(nodes) and len(contact) == len(contacts), f"{seed}: duplicate IDs")
                endpoints.append(analysis.scan(w, people, contact, changed, starts))
    analysis.save(directory / "changed.tsv", analysis.CHANGED_FIELDS, changed)
    analysis.save(directory / "starts.tsv", analysis.START_FIELDS, starts)
    analysis.save(directory / "endpoints.tsv", " ".join(endpoints[0]), endpoints)


def completion(directory, revision):
    return f"inputs {hashlib.sha256(revision.encode()).hexdigest()}\n" + "".join(
        f"{digest(directory / name)}  {name}\n" for name in TABLES)


def verified(analysis, directory, seeds, revision):
    names = {*TABLES, STAMP}
    require(directory.is_dir() and not directory.is_symlink() and
            {p.name for p in directory.iterdir()} == names and
            all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),
            f"{directory}: incomplete batch")
    require((directory / STAMP).read_text() == completion(directory, revision),
            f"{directory}: completion digest mismatch")
    worlds = list(analysis.rows(directory / "world.tsv"))
    endpoints = list(analysis.rows(directory / "endpoints.tsv"))
    for records in (worlds, endpoints):
        require([int(r["seed"]) for r in records] == list(seeds), f"{directory}: wrong seed ledger")
    return endpoints


def archive_table(name):
    p = OLD / "results" / name
    data = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
    header, *rows = data.splitlines(keepends=True)
    selected = {str(seed).encode() for seed in VALIDATION}
    return header + b"".join(row for row in rows if row.partition(b"\t")[0] in selected)


def validate(analysis, work, revision):
    RECEIPT.unlink(missing_ok=True)
    tests = compile_cpp(work / "vm_tests", "-O2", VM / "assay.cpp", VM.parent / "tests/vm_tests.cpp")
    subprocess.run([tests], check=True)
    print("Archived classifier replacements:", analysis.archive(), flush=True)
    analysis.fixture()
    print("Synthetic classifier controls passed.", flush=True)
    guard = " || ".join(f"seed=={seed}" for seed in VALIDATION)
    for optimization, reverse in (("-O2", False), ("-O3", True)):
        binary = field(work, optimization, guard)
        subprocess.run([binary, "--test"], check=True)
        directory = work / optimization
        directory.mkdir()
        score_batch(analysis, binary, VALIDATION, directory, reverse)
        for name in TABLES:
            p = directory / name
            actual = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
            require(actual == archive_table(name), f"{optimization}: archive mismatch in {name}")
        (directory / STAMP).write_text(completion(directory, revision))
        verified(analysis, directory, VALIDATION, revision)
        print(f"{optimization} {'reverse' if reverse else 'forward'}: all six tables match archive "
              f"byte for byte for {', '.join(map(str, VALIDATION))}.", flush=True)
    require(revision == inputs(), "inputs changed during validation")
    receipt = work / RECEIPT.name
    receipt.write_text(revision)
    receipt.replace(RECEIPT)
    print("Validation passed for revision.sha256.", flush=True)


def report(endpoints):
    starters = [e for e in endpoints if int(e["all_start"]) > 0]
    print(f"Starter-bearing worlds: {len(starters)}/{len(endpoints)} (target 29).")
    for label, key in (("At least one renewal", "all_renew"), ("Repeated renewal", "all_repeat")):
        for group, sample in (("all worlds", endpoints), ("starter-bearing worlds", starters)):
            n = len(sample)
            hits = sum(int(e[key]) > 0 for e in sample)
            result = f"{hits}/{n}" if n else "undefined (no starters)"
            if n and not hits:
                result += f"; exact one-sided 95% upper bound {1 - 0.05 ** (1 / n):.6%}"
            print(f"{label}, {group}: {result}")
    if len(starters) < 29 and not any(int(e["all_renew"]) for e in starters):
        print("Conditional target unresolved; no additional worlds.")


def primary(analysis, work, revision, all_batches):
    require(RECEIPT.is_file() and RECEIPT.read_text() == revision,
            "run --validate on the frozen inputs first")
    RESULTS.mkdir(parents=True, exist_ok=True)
    binary, endpoints = None, []
    for i in range(BATCHES if all_batches else 1):
        lo = FIRST + i * SIZE
        seeds = range(lo, lo + SIZE)
        dest = RESULTS / f"batch-{i + 1:03d}"
        if dest.exists() or dest.is_symlink():
            entries = verified(analysis, dest, seeds, revision)
            print(f"{dest.name} ({lo}–{seeds[-1]}): verified, skipped", flush=True)
        else:
            if binary is None:
                binary = field(work, "-O2", f"seed>={FIRST} && seed<={LAST}")
            print(f"{dest.name} ({lo}–{seeds[-1]}): running", flush=True)
            with tempfile.TemporaryDirectory(prefix=".tmp-", dir=RESULTS) as tmp:
                stage = Path(tmp)
                score_batch(analysis, binary, seeds, stage)
                require(revision == inputs(), "inputs changed during run")
                (stage / STAMP).write_text(completion(stage, revision))
                entries = verified(analysis, stage, seeds, revision)
                stage.rename(dest)
            print(f"{dest.name}: complete", flush=True)
        endpoints.extend(entries)
    if all_batches:
        report(endpoints)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="archive-only controls and replay")
    mode.add_argument("--first-batch", action="store_true", help="run or verify only batch 001")
    mode.add_argument("--all", action="store_true", help="run or verify all 53 batches in order")
    args = parser.parse_args()
    require(not sys.flags.optimize, "Python assertions must be enabled for the historical checks")
    require(FIRST + SIZE * BATCHES - 1 == LAST, "inconsistent primary seed range")
    revision = (HERE / "revision.sha256").read_text()
    require(revision == inputs(), "frozen inputs do not match revision.sha256")
    BUILD.mkdir(exist_ok=True)
    with (BUILD / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix="run-", dir=BUILD) as tmp:
            # Read the verified historical sources, not any pre-existing bytecode cache.
            sys.dont_write_bytecode = True
            sys.pycache_prefix = str(Path(tmp) / "pycache")
            sys.path.insert(0, str(OLD))
            import analyze

            if args.validate:
                validate(analyze, Path(tmp), revision)
            else:
                primary(analyze, Path(tmp), revision, args.all)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Stopped: {exc}")
