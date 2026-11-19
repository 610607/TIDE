"""v22 census seeding limit per checkpoint, from tracekey and tracemass lines.
Usage: v22.py <v22 dir>"""
import re, sys, os
d = sys.argv[1]
def nums(s): return [int(x) for x in s.split('/')]
for name in sorted(os.listdir(d)):
    if not name.endswith('.tsv'): continue
    print('########', name)
    rows = []
    mass = {}
    for line in open(os.path.join(d, name)):
        if line.startswith('# tracemass'):
            t = int(re.search(r'tick=(\d+)', line).group(1))
            mass[t] = nums(re.search(r'active_sites=(\S+)', line).group(1))
        if not line.startswith('# tracekey'): continue
        kv = dict(re.findall(r'(\S+?)=(\S+)', line))
        t = int(kv['tick'])
        rows.append((t, kv))
    print('tick | strict(census) | other | other>48 | other>48 topped strict/loose/prop/other | rep bytes 45-48 | loss self/for | unseeded self/for (topped strict) | copies | by >48 parent (same) ')
    tot = [0]*8
    for t, kv in rows:
        a = mass.get(t, [0,0,0,0])
        un = nums(kv['unseeded_sites(rep/loose/prop/other)'])
        tp = nums(kv['unseeded_topped(rep/loose/prop/other)'])
        rb = nums(kv['rep_bytes'])
        ob = nums(kv['other_bytes'])
        lo = nums(kv['loss(self/foreign)']); lu = nums(kv['loss_unseeded']); lt = nums(kv['loss_unseeded_topped_rep'])
        cp = int(kv['copies']); cu = int(kv['copies_unseeded']); cus = int(kv['copies_unseeded_same']); cs = int(kv['copies_same'])
        print(f"{t//1000}k | {a[0]} | {a[3]} | {un[3]} ({100*un[3]/max(1,a[3]):.0f}%) keys={kv['unseeded_keys']} | {tp} | {rb[2]} | {lo} | {lu} ({lt}) | {cp} same {cs} | {cu} ({cus}) | other_bytes={ob}")
        for i, v in enumerate(lo + lu + lt + [cp, cu]): tot[i] += v
    print('totals loss self/for', tot[0:2], 'unseeded', tot[2:4], 'topped strict', tot[4:6], 'copies', tot[6], 'by unseeded parent', tot[7])
