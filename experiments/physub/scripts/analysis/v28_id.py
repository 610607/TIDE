"""v28 identity: lines of a role=1 run vs the v27 run of the same dynamics, minus role lines
(and route lines when the v27 run had none), over the blocks both files hold; plus role sums
vs route totals. Usage: v28_id.py new.tsv v27.tsv"""
import re, sys

def blocks(path):
    out, cur = {}, None
    for line in open(path):
        line = line.rstrip('\n')
        m = re.match(r'^(\d+)\t', line)
        if m:
            cur = int(m.group(1)); out[cur] = [line]; continue
        if cur is None: continue
        if not line.startswith('#'):
            cur = None; continue
        out[cur].append(line)
    return out

new, old = blocks(sys.argv[1]), blocks(sys.argv[2])
old_has_route = any(l.startswith('# route ') for b in old.values() for l in b)
bad = 0
for t in sorted(set(new) & set(old)):
    keep = lambda l: not (l.startswith('# role ') or l.startswith('# rolelen ') or
                          (not old_has_route and l.startswith('# route')))
    a = [l for l in new[t] if keep(l)]
    b = old[t]
    if a != b:
        bad += 1
        for x, y in zip(a, b):
            if x != y: print('DIFF', t, x[:120], '|', y[:120]); break
        if len(a) != len(b): print('LEN', t, len(a), len(b))
    # role sums vs route totals
    route = [l for l in new[t] if l.startswith('# route ')]
    role = [l for l in new[t] if l.startswith('# role ')]
    if route and role:
        rp = route[0].split(' | ')[1:]
        lp = role[0].split(' | ')[1:]
        for e, (rs, ls) in enumerate(zip(rp, lp)):
            rt = dict((k, sum(map(int, v.split('/')))) for k, v in re.findall(r'(\w+)=(\d+/\d+)', rs.split('loss(')[1]))
            rg = int(re.search(r' gain=(\d+)', rs).group(1))
            lt = {k: sum(map(int, v.split(';')[0].split('/'))) for k, v in re.findall(r'(\w+)=([\d/]+;\d+)', ls)}
            lg = sum(map(int, re.search(r' gain=([\d/]+);', ls).group(1).split('/')))
            for k in rt:
                if rt[k] != lt.get(k): print('SUM', t, e, k, rt[k], lt.get(k)); bad += 1
            if rg != lg: print('GAIN', t, e, rg, lg); bad += 1
print(sys.argv[1].split('/')[-1], 'blocks', sorted(set(new) & set(old)), 'bad', bad)

# rolelen vs length: in-place kept bytes and exits by loss
def num(s): return [float(x) for x in s.split('/')]
for t in sorted(new):
    L = [l for l in new[t] if l.startswith('# length ')]
    R = [l for l in new[t] if l.startswith('# rolelen ')]
    if not (L and R): continue
    L, R = L[0], R[0]
    ln = {k: num(v) for k, v in re.findall(r' (\w+)=([-\d.e+/]+)', L)}
    for fw, cat in (('foreign', 'inplace_f'), ('self', 'inplace_s')):
        m = re.search(fw + r':([\d/]+);([-\d.e+/]+)', R)
        b, d = num(m.group(1)), num(m.group(2))
        dz = b[0] + b[1] + b[2] + b[3] - b[4]
        ok = abs(dz - ln[cat][1]) < 0.5 and abs(sum(d) - ln[cat][2]) < 3e-5
        if not ok: print('INPLACE', t, cat, dz, ln[cat][1], sum(d), ln[cat][2])
    for fw, cat in (('loss_f', 'loss_f'), ('loss_s', 'loss_s')):
        m = re.search(fw + r':([\d/]+);([-\d.e+/]+);(\d+)/([-\d.e+]+)', R)
        n, d = num(m.group(1)), num(m.group(2))
        ok = abs(sum(n) - ln[cat][0]) < 0.5 and abs(sum(d) - ln[cat][2]) < 3e-5
        if not ok: print('EXIT', t, cat, sum(n), ln[cat][0], sum(d), ln[cat][2])
print('rolelen checked')

# whole-file comparison (role lines dropped; route lines too where the v27 run had none)
def filt(path, drop_route):
    out = []
    for l in open(path):
        if l.startswith('# role ') or l.startswith('# rolelen '): continue
        if drop_route and l.startswith('# route'): continue
        out.append(l)
    return out
a, b = filt(sys.argv[1], not old_has_route), filt(sys.argv[2], False)
print('whole file equal:', a == b, len(a), len(b))
