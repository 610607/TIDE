"""v19 per-checkpoint rates (wick plus net in-place loss, decay, out, births minus ends) per
mean active count, from v19.py output. Usage: v19_rates.py v19_output.txt"""
import re, sys
for path in sys.argv[1:]:
    rows = [l for l in open(path) if re.match(r'^(m195|nomut)_s\d \d+k \| \d+->', l)]
    out = {}
    for l in rows:
        f = [x.strip() for x in l.split('|')]
        run, tk = f[0].split(); tk = int(tk[:-1])
        a, b = re.match(r'(\d+)->(\d+)', f[1]).groups(); a, b = int(a), int(b)
        cp, rg, sf = map(int, f[2].split('/')); inn = int(f[3].split()[0]); dec = int(f[4]); wick = int(f[5]); o = int(f[6])
        if tk <= 150: continue
        m = (a + b) / 2 / 10
        out.setdefault(run, []).append((tk, (wick + o - inn) / m, dec / m, o / m, cp / m, cp + rg - dec - wick))
    for run, v in out.items():
        print(run, 'wick+net_in', f"{min(x[1] for x in v):.3f}-{max(x[1] for x in v):.3f}", 'decay', f"{min(x[2] for x in v):.3f}-{max(x[2] for x in v):.3f}",
              'out', f"{min(x[3] for x in v):.3f}-{max(x[3] for x in v):.3f}", 'births-ends', min(x[5] for x in v), max(x[5] for x in v))
