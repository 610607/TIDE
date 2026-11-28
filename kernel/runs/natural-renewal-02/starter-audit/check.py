"""Post hoc verification of field replay, independently scored starts and starter attrition."""
import argparse
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
OLD = STUDY.with_name('natural-renewal-01')
VM = STUDY.parents[1] / 'src'
sys.path[:0] = [str(OLD / 'starter-audit'), str(OLD)]
from audit import audit, save
from controls import rows


def reconstruct(records):
    """Classify first renewals from raw permissions, six source writes and same-type ancestry."""
    confirmed, parents, copies = set(), {}, []
    for i, r in sorted(records.items(), key=lambda pair: (int(pair[1]['born']), pair[0])):
        passed = (int(r['ordinary_births']) > 0 and int(r['exposed_births']) > 0
                  and int(r['denied_births']) == 0 and int(r['blocked']) > 0)
        assert passed == (r['confirmed'] == '1')
        if not passed:
            continue
        confirmed.add(i)
        actor = int(r['actor'])
        writes = [s.split('/') for s in r['writes'].split(',')]
        assert len(writes) == 6
        w0 = writes[0]
        intact = (r['genome'] == r['inputs'] and int(r['substitutions']) == 0 and
                  all(w[1:4] == w0[1:4] and w[3] == 'o' and int(w[4]) == j and w[5] == w0[5]
                      for j, w in enumerate(writes)))
        sources = [actor]
        if intact:
            donor = int(w0[5])
            assert donor >= 0 and donor != actor
            sources.append(donor)
            if actor in confirmed and r['genome'] == records[actor]['genome']:
                copies.append((actor, donor, i, int(w0[0]), int(w0[2])))
        parents[i] = [j for j in sources if j in confirmed and records[j]['genome'] == r['genome']]

    def reaches(node, ancestor):
        todo, seen = [node], set()
        while todo:
            cur = todo.pop()
            if cur == ancestor:
                return True
            if cur not in seen:
                seen.add(cur)
                todo.extend(parents[cur])
        return False

    def born(i):
        return int(records[i]['born'])

    result = {}
    for actor, donor, child, _, donor_born in copies:
        cutoff = born(actor) + 324
        if born(actor) > 8192 or born(child) > cutoff:
            continue
        original = max(born(actor), donor_born)
        successors = []
        for a, d, c, first_read, _ in copies:
            if d not in confirmed or first_read <= original + 81 or born(c) > cutoff:
                continue
            if (min(born(a), born(d)) > original and reaches(a, actor) and reaches(d, actor)
                    and (reaches(a, child) or reaches(d, child))):
                successors.append(c)
        result[actor, donor, child] = successors
    return result


def main(out):
    assert not sys.flags.optimize
    out.mkdir(parents=True, exist_ok=True)
    families, pairs, products, ticks = [], [], [], []
    status, renewed, starters = Counter(), 0, 0
    expected_seed = 100001
    with TemporaryDirectory() as tmp:
        binary = Path(tmp) / 'replay'
        subprocess.run(['c++', '-O3', '-Wall', '-Wextra', '-Werror', '-std=c++20', f'-I{VM}',
                        VM / 'vm.cpp', OLD / 'starter-audit/replay.cpp', '-o', binary], check=True)
        for directory in sorted((STUDY / 'results/primary').glob('batch-*')):
            groups = defaultdict(dict)
            for r in rows(directory / 'nodes.tsv.gz'):
                by_id = groups[int(r['seed'])]
                assert int(r['id']) not in by_id
                by_id[int(r['id'])] = r
            by_seed = defaultdict(list)
            for s in rows(directory / 'starts.tsv'):
                by_seed[int(s['seed'])].append(s)
            for w in rows(directory / 'world.tsv'):
                seed = int(w['seed'])
                assert seed == expected_seed
                expected_seed += 1
                status[w['status']] += 1
                records = groups.pop(seed, {})
                derived = reconstruct(records)
                archived = by_seed.pop(seed, [])
                assert set(derived) == {(int(s['reader']), int(s['donor']), int(s['child'])) for s in archived}
                starters += bool(derived)
                renewed += any(derived.values())
                for s in archived:
                    k = tuple(int(s[name]) for name in ('reader', 'donor', 'child'))
                    assert not derived[k] and int(s['depth']) == 0
                    f, ps, births, events = audit(binary, True, s, records, w)
                    families.append(f)
                    for acc, data in ((pairs, ps), (products, births), (ticks, events)):
                        acc.extend(dict(starter_reader=s['reader'], starter_copy=s['child'], **row) for row in data)
            assert not groups and not by_seed
    assert expected_seed == 105301
    for name, data in [('families', families), ('pairs', pairs), ('products', products), ('ticks', ticks)]:
        save(out / (name + '.tsv'), ' '.join(data[0]), data)
    print('World statuses:', dict(status))
    print('Starter-bearing worlds, starting copies, renewed worlds:', starters, len(families), renewed)
    for k, v in [('confirmed_later', 2), ('overlapping_pairs', 1), ('adjacent_pairs', 1), ('postdeath_peer_bytes', 1)]:
        cases = [f for f in families if f[k] >= v]
        print(k, '>=', v, ':', len(cases), 'starts in', len({f['seed'] for f in cases}), 'worlds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    main(parser.parse_args().out)
