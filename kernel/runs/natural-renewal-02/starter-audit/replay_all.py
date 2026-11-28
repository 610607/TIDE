"""Compare all primary tables against fresh reverse-order runs; do not write to the archive."""
import gzip
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

study = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('followup', study / 'run.py')
followup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(followup)
sys.path.insert(0, str(followup.OLD))
import analyze


def content(path):
    raw = path.read_bytes()
    return gzip.decompress(raw) if path.suffix == '.gz' else raw


if __name__ == '__main__':
    assert not sys.flags.optimize
    revision = followup.inputs()
    assert revision == (study / 'revision.sha256').read_text()
    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        binary = followup.field(work, '-O3', f'seed>={followup.FIRST} && seed<={followup.LAST}')
        followup.BUILD.mkdir(exist_ok=True)
        for i in range(followup.BATCHES):
            lo = followup.FIRST + i * followup.SIZE
            seeds = range(lo, lo + followup.SIZE)
            archive = followup.RESULTS / f'batch-{i + 1:03d}'
            followup.verified(analyze, archive, seeds, revision)
            followup.score_batch(analyze, binary, seeds, work, reverse=True)
            for name in followup.TABLES:
                assert content(work / name) == content(archive / name), (archive, name)
    print('All reverse-replayed primary tables match the forward archive.')
