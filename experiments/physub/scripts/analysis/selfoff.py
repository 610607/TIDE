"""Self-written in-place losses changing offset 0, per period; foreign offsets 36/38/40 and 47-53."""
import re, sys
for p in sys.argv[1:]:
    per = {}
    for l in open(p):
        if not l.startswith('# fateout '): continue
        t = int(re.search(r'tick=(\d+)', l).group(1)); k = 0 if t <= 150000 else 1
        self_n = int(re.search(r' self=(\d+)', l).group(1))
        so = dict((int(a), int(b)) for a, b in re.findall(r'(\d+):(\d+)', l.split('offsets_self:')[1]))
        fo = dict((int(a), int(b)) for a, b in re.findall(r'(\d+):(\d+)', l.split('offsets_foreign:')[1].split('offsets_self')[0]))
        d = per.setdefault(k, [0, 0, 0, 0])
        d[0] += self_n; d[1] += so.get(0, 0); d[2] += sum(fo.get(x, 0) for x in (36, 38, 40)); d[3] += sum(fo.get(x, 0) for x in range(47, 54))
    for k, d in sorted(per.items()):
        print(p.split('/')[-1], ['to150k', '150-500k'][k], f"self={d[0]} off0={d[1]} ({100*d[1]/max(1,d[0]):.1f}%) foreign36/38/40>={d[2]} tail47-53>={d[3]}")
