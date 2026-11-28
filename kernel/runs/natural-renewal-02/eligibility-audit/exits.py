"""Post hoc: classify every birth that left a starter's confirmed same-program lineage.

Reads only archived tables. A starter's lineage is every confirmed individual whose
same-sequence ancestry (actual division or intact living donation, as in the original
pedigree) reaches the starting reader. Every recorded birth executed by, or copied intact
from, a lineage member that is not itself in the lineage is an exit, classified by the
first eligibility condition it fails.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
OLD = STUDY.with_name('natural-renewal-01')
sys.path[:0] = [str(OLD)]
from controls import rows  # noqa: E402
from pedigree import Pedigree, from_record  # noqa: E402
from run import AGE, FOLLOW  # noqa: E402

# Exit classes in the order they are tested.
CLASSES = (
    'after_window',      # born after the reader's 324-tick window
    'substituted',       # different program, at least one copy substitution
    'other_input',       # different program from unsubstituted input bytes
    'no_offspring',      # same program, no births in its lifetime: cannot be assayed
    'self_only',         # same program, births but none used external material
    'independent',       # same program, reproduced with neighbor reads denied
    'never_blocked',     # same program, no external copy was blocked under denial
)


def classify(row, root_genome, cutoff):
    if int(row['born']) > cutoff:
        return 'after_window'
    if row['genome'] != root_genome:
        return 'substituted' if int(row['substitutions']) > 0 else 'other_input'
    assert row['confirmed'] == '0'
    if int(row['ordinary_births']) == 0:
        return 'no_offspring'
    if int(row['exposed_births']) == 0:
        return 'self_only'
    if int(row['denied_births']) > 0:
        return 'independent'
    assert int(row['blocked']) == 0
    return 'never_blocked'


def source(p, records):
    """Where the six input bytes came from."""
    row = records[p.id]
    sites = {w.split('/')[1] for w in row['writes'].split(',')}
    if sites == {row['site']}:
        return 'own_reservation'  # residual bytes already in the bank being written
    if p.donor >= 0 and p.donor != p.actor:
        return 'one_living_neighbor'  # aligned: the inputs are that neighbor's program
    if p.donor == p.actor:
        return 'executor'
    return 'mixed'


def family(start, records):
    tree = Pedigree(from_record(r, r['confirmed'] == '1') for r in records.values())
    root, child = (tree.people[int(start[k])] for k in ('reader', 'child'))
    cutoff = root.born + FOLLOW
    older_birth = max(root.born, child.donor_born)
    lineage = {i for i, a in tree.ancestors.items() if root.id in a}
    later = [i for i in lineage if older_birth < tree.people[i].born <= cutoff]
    exits, births, after_turnover = [], 0, Counter()
    for p in sorted(tree.people.values(), key=lambda n: (n.born, n.id)):
        parents = {p.actor} | ({p.donor} if p.intact else set())
        if not parents & lineage:
            continue
        births += 1
        if p.id in lineage:
            continue
        kind = classify(records[p.id], root.genome, cutoff)
        exits.append(dict(seed=start['seed'], reader=root.id, product=p.id, born=p.born,
                          executor=p.actor, executor_in_lineage=int(p.actor in lineage),
                          genome=bytes.fromhex(p.genome).decode(), substitutions=records[p.id]['substitutions'],
                          ordinary_births=records[p.id]['ordinary_births'],
                          exposed_births=records[p.id]['exposed_births'],
                          denied_births=records[p.id]['denied_births'], exit=kind,
                          kinds=''.join(w.split('/')[3] for w in records[p.id]['writes'].split(',')),
                          source=source(p, records),
                          after_turnover=int(p.born > older_birth + AGE)))
        if p.born > older_birth + AGE:
            after_turnover[kind] += 1
    return dict(seed=start['seed'], reader=root.id, child=child.id, genome=bytes.fromhex(root.genome).decode(),
                lineage=len(lineage), confirmed_later=len(later), lineage_births=births,
                exits=len(exits), **{k: sum(e['exit'] == k for e in exits) for k in CLASSES}), exits


def cohort(name, batches):
    for directory in batches:
        groups = defaultdict(dict)
        for r in rows(directory / 'nodes.tsv.gz'):
            groups[r['seed']][int(r['id'])] = r
        for s in rows(directory / 'starts.tsv'):
            f, e = family(s, groups[s['seed']])
            yield dict(cohort=name, **f), e


def save(path, data):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, list(data[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    audited = {(r['seed'], r['reader']): r for r in rows(STUDY / 'starter-audit/results/families.tsv')}
    audited.update({(r['seed'], r['reader']): r for r in rows(OLD / 'starter-audit/results/families.tsv')})
    families, exits = [], []
    sources = [('natural-renewal-01', [OLD / 'results']),
               ('natural-renewal-02', sorted((STUDY / 'results/primary').glob('batch-*')))]
    for name, batches in sources:
        for f, e in cohort(name, batches):
            # The lineage definition must reproduce the archived starter audit.
            assert int(audited[f['seed'], str(f['reader'])]['confirmed_later']) == f['confirmed_later'], f
            families.append(f)
            exits.extend(dict(cohort=name, **x) for x in e)
    assert sum(f['cohort'] == 'natural-renewal-02' for f in families) == 31
    assert sum(f['cohort'] == 'natural-renewal-01' for f in families) == 7
    save(out / 'families.tsv', families)
    save(out / 'exits.tsv', exits)
    summary = []
    for name in ('natural-renewal-01', 'natural-renewal-02'):
        fs = [f for f in families if f['cohort'] == name]
        es = [e for e in exits if e['cohort'] == name]
        keys = sorted({(e['exit'], e['source']) for e in es}, key=lambda k: (CLASSES.index(k[0]), k[1]))
        for kind, src in keys + [('all', 'all')]:
            sel = [e for e in es if kind in ('all', e['exit']) and src in ('all', e['source'])]
            summary.append(dict(cohort=name, exit=kind, source=src, births=len(sel),
                                after_turnover=sum(e['after_turnover'] for e in sel),
                                starts_with_any=len({(e['seed'], e['reader']) for e in sel}),
                                starts=len(fs)))
    save(out / 'summary.tsv', summary)
    for r in summary:
        print('\t'.join(str(v) for v in r.values()))


if __name__ == '__main__':
    assert not sys.flags.optimize
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    main(parser.parse_args().out)
