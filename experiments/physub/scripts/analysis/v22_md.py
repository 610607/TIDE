"""v22 README tables as first recorded (seed-limited census, c207f47); replaced by
v22_md2.py in v23. Usage: v22_md.py <v22 dir>"""
import re, sys, os
d = sys.argv[1]
def nums(s): return [int(x) for x in s.split('/')]
data = {}
for name in ['m195_s1', 'm195_s2', 'zero_s1', 'zero_s2']:
    rows = {}
    mass = {}
    for line in open(os.path.join(d, name + '.tsv')):
        if line.startswith('# tracemass'):
            t = int(re.search(r'tick=(\d+)', line).group(1))
            mass[t] = nums(re.search(r'active_sites=(\S+)', line).group(1))
        if line.startswith('# tracekey'):
            kv = dict(re.findall(r'(\S+?)=(\S+)', line))
            rows[int(kv['tick'])] = kv
    data[name] = (rows, mass)
ticks = sorted(data['m195_s1'][0])
print('| tick | census strict | `other` | `other` past 48 (%) | strict when topped up | strict + topped | copy births by keys past 48 (%) |')
print('| --- | --- | --- | --- | --- | --- | --- |')
for t in ticks:
    cells = [[] for _ in range(6)]
    for name in ['m195_s1', 'm195_s2', 'zero_s1', 'zero_s2']:
        rows, mass = data[name]
        kv = rows.get(t)
        if kv is None: continue
        a = mass[t]
        un = nums(kv['unseeded_sites(rep/loose/prop/other)'])
        tp = nums(kv['unseeded_topped(rep/loose/prop/other)'])
        cp = int(kv['copies']); cu = int(kv['copies_unseeded'])
        cells[0].append(f"{a[0]:,}"); cells[1].append(f"{a[3]:,}")
        cells[2].append(f"{100*un[3]/max(1,a[3]):.0f}"); cells[3].append(f"{tp[0]:,}")
        cells[4].append(f"{a[0]+tp[0]:,}"); cells[5].append(f"{100*cu/max(1,cp):.0f}")
    def fmt(c): return ' / '.join(c[:2]) + '; ' + ' / '.join(c[2:])
    print(f"| {t//1000}k | " + ' | '.join(fmt(c) for c in cells) + ' |')
print()
for name in ['m195_s1', 'm195_s2', 'zero_s1', 'zero_s2']:
    rows, mass = data[name]
    for lo, hi in [(0, 150000), (150000, 500000)]:
        L = [0,0]; U = [0,0]; T = [0,0]; C = 0; CU = 0; CUS = 0; CS = 0; tops = [0]*4
        for t, kv in rows.items():
            if not (lo < t <= hi): continue
            lo_ = nums(kv['loss(self/foreign)']); lu = nums(kv['loss_unseeded']); lt = nums(kv['loss_unseeded_topped_rep'])
            L = [a+b for a, b in zip(L, lo_)]; U = [a+b for a, b in zip(U, lu)]; T = [a+b for a, b in zip(T, lt)]
            C += int(kv['copies']); CU += int(kv['copies_unseeded']); CUS += int(kv['copies_unseeded_same']); CS += int(kv['copies_same'])
        print(f"{name} ({lo//1000}k,{hi//1000}k] loss self/foreign {L} unseeded {U} ({100*U[1]/max(1,L[1]):.1f}% of foreign) topped strict {T} ({100*T[1]/max(1,U[1]):.1f}%) | copies {C} same {100*CS/max(1,C):.1f}% | by >48 parent {CU} ({100*CU/max(1,C):.1f}%) same {100*CUS/max(1,CU):.1f}%")
