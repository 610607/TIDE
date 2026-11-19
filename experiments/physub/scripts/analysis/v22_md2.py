"""v22 tables under the topped-up census: strict, of which past 48, seed-limited strict, other, other past 48, copies by parents past 48; and loss table."""
import re, sys, os
d = sys.argv[1]
def nums(s): return [int(x) for x in s.split('/')]
names = ['m195_s1', 'm195_s2', 'zero_s1', 'zero_s2']
data = {}
for name in names:
    rows, mass = {}, {}
    for line in open(os.path.join(d, name + '.tsv')):
        if line.startswith('# tracemass'):
            t = int(re.search(r'tick=(\d+)', line).group(1))
            mass[t] = nums(re.search(r'active_sites=(\S+)', line).group(1))
        if line.startswith('# tracekey'):
            kv = dict(re.findall(r'(\S+?)=(\S+)', line)); rows[int(kv['tick'])] = kv
    data[name] = (rows, mass)
print('| tick | strict | of which past 48 | seed-limited strict | `other` | `other` past 48 (%) | copy births by parents past 48 (% of the window) |')
print('| --- | --- | --- | --- | --- | --- | --- |')
for t in sorted(data['m195_s1'][0]):
    cells = [[] for _ in range(6)]
    for name in names:
        rows, mass = data[name]; kv = rows[t]; a = mass[t]
        rb = nums(kv['rep_bytes']); past = sum(rb[3:]); assert sum(rb) == a[0]
        un = nums(kv['unseeded_sites(rep/loose/prop/other)']); assert un[0] == past
        cp = int(kv['copies']); cu = int(kv['copies_unseeded'])
        for i, v in enumerate([f"{a[0]:,}", f"{past:,}", f"{a[0]-past:,}", f"{a[3]:,}", f"{100*un[3]/max(1,a[3]):.0f}", f"{100*cu/max(1,cp):.0f}"]):
            cells[i].append(v)
    fmt = lambda c: ' / '.join(c[:2]) + '; ' + ' / '.join(c[2:])
    print(f"| {t//1000}k | " + ' | '.join(fmt(c) for c in cells) + ' |')
print()
# strict sites by byte bins at 50k and 500k; other past 48 bins
for t in (50000, 500000):
    for name in names:
        kv = data[name][0][t]; rb = nums(kv['rep_bytes']); ob = nums(kv['other_bytes'])
        print(t, name, 'rep<=40 %.0f%%' % (100*rb[0]/sum(rb)), '45-48 %.0f%%' % (100*rb[2]/sum(rb)), 'past48 %.0f%%' % (100*sum(rb[3:])/sum(rb)),
              '53-64 of past %.0f%%' % (100*sum(rb[4:])/max(1,sum(rb[3:]))), 'other past48 53-64 %.0f%%' % (100*sum(ob[4:])/max(1,sum(ob[3:]))))
print()
for name in names:
    rows = data[name][0]
    for lo, hi in [(0, 150000), (150000, 500000)]:
        L = [0,0]; U = [0,0]; C = CU = CUS = CS = 0
        for t, kv in rows.items():
            if not (lo < t <= hi): continue
            L = [a+b for a, b in zip(L, nums(kv['loss(self/foreign)']))]; U = [a+b for a, b in zip(U, nums(kv['loss_unseeded']))]
            C += int(kv['copies']); CU += int(kv['copies_unseeded']); CUS += int(kv['copies_unseeded_same']); CS += int(kv['copies_same'])
        print(f"{name} ({lo//1000}k,{hi//1000}k] foreign {L[1]:,} past48 {100*U[1]/max(1,L[1]):.1f}% | self {L[0]:,} ({U[0]:,} past 48, {100*U[0]/max(1,L[0]):.1f}%) | copies {C:,} by>48 {100*CU/max(1,C):.1f}% same all {100*CS/max(1,C):.1f} >48 {100*CUS/max(1,CU):.1f}")
