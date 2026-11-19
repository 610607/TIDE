"""v21 tables per window from trace lines: foreign writes (FO), ignitions off entry (IGN)
and activation ends by start offset (END). Usage: v21_table.py run.tsv..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v21 import load
from collections import Counter
runs = sys.argv[1:]
def agg(d, lo, hi):
    A = dict(n=0, v0=0, w={k: [0,0,0] for k in ["rep","loose","prop","other","none"]}, kind=[0,0,0,0], wstart0=0,
             src_own=0, dir=0, dir_only=0, wip=Counter(), offs=Counter(), diroffs=Counter(), not_mov=0,
             r0=[0,0,0], roff=[0,0,0], ign={k: [0,0,0] for k in ["rep","loose","prop","other","self","none"]}, same=0,
             prev=[0,0], gap=0, iip=Counter(), entry=Counter(), births=0, off0=0, end=[[0]*4,[0]*4], nm=[])
    for t, e in sorted(d.items()):
        if not (lo < t <= hi): continue
        if 'no_mass' in e: A['nm'].append(e['no_mass'])
        o = e.get('out')
        if o:
            for k in ['n','v0','wstart0','src_own','dir','dir_only','not_mov']: A[k] += o[k]
            for k, v in o['w'].items(): A['w'][k] = [a+b for a, b in zip(A['w'][k], v)]
            A['kind'] = [a+b for a, b in zip(A['kind'], o['kind'])]
            A['wip'].update(o['wip']); A['offs'].update(o['offs']); A['diroffs'].update(o['diroffs'])
        g = e.get('ign')
        if g:
            A['births'] += g['births']; A['off0'] += g['off0']
            A['r0'] = [a+b for a, b in zip(A['r0'], g['r0'])]; A['roff'] = [a+b for a, b in zip(A['roff'], g['roff'])]
            for k, v in g['ign'].items(): A['ign'][k] = [a+b for a, b in zip(A['ign'][k], v)]
            A['same'] += g['same']; A['prev'] = [a+b for a, b in zip(A['prev'], g['prev'])]; A['gap'] += g['gap']
            A['iip'].update(g['iip']); A['entry'].update(g['entry'])
        en = e.get('end')
        if en:
            for i in range(2): A['end'][i] = [a+b for a, b in zip(A['end'][i], en[i])]
    return A
pc = lambda a, b: f"{100*a/b:.1f}" if b else "-"
for r in runs:
    d = load(r)
    for lo, hi in [(0, 150000), (150000, 500000)]:
        A = agg(d, lo, hi); n = A['n']
        W = A['w']; tot = lambda k: sum(W[k])
        age = [sum(W[k][i] for k in W) for i in range(3)]
        tail = sum(v for k, v in A['offs'].items() if k >= 46)
        d3440 = sum(A['diroffs'].get(k, 0) for k in (34, 36, 38, 40))
        print(f"== {r.split('/')[-1]} ({lo//1000}k,{hi//1000}k]")
        print(f" FO n={n} victim0={pc(A['v0'],n)} other={pc(tot('other'),n)} rep={pc(tot('rep'),n)} loose+prop={pc(tot('loose')+tot('prop'),n)} "
              f"age<1k={pc(age[0],n)} 1k-10k={pc(age[1],n)} >=10k={pc(age[2],n)} copyborn={pc(A['kind'][1],n)} reig={pc(A['kind'][2],n)} "
              f"wstart0={pc(A['wstart0'],n)} ip15={pc(A['wip'].get(15,0),n)} not_mov={A['not_mov']} src_own={pc(A['src_own'],n)} "
              f"dir={pc(A['dir'],n)} dir_only={A['dir_only']} off30={pc(A['diroffs'].get(30,0),n)} d34-40={pc(d3440,n)} tail46-63>={pc(tail,n)} other_offs={pc(n - A['diroffs'].get(30,0) - d3440 - tail, n)}")
        rb = sum(A['r0']) + sum(A['roff']); ro = sum(A['roff'])
        I = A['ign']; it = sum(sum(v) for v in I.values())
        iage = [sum(I[k][i] for k in I) for i in range(3)]
        top_e = A['entry'].most_common(6); top_i = A['iip'].most_common(8)
        print(f" IGN strict births={rb} off0={ro} ({pc(ro,rb)}%) off0 reig={pc(A['roff'][2],ro)} igniter other={pc(sum(I['other']),it)} rep={pc(sum(I['rep']),it)} "
              f"age<1k={pc(iage[0],it)} >=10k={pc(iage[2],it)} same={A['same']} prev_off0_wick={pc(A['prev'][1],ro)} gap={A['gap']/max(1,sum(A['prev'])):.0f} "
              f"entry={[(k, pc(v, ro)) for k, v in top_e]} ip={[(k, pc(v, ro)) for k, v in top_i]}")
        s0, so = A['end']
        print(f" END start0 decay/wick={s0[0]}/{s0[1]} life={s0[2]/max(1,s0[0]+s0[1]):.0f} copies={s0[3]}; off0 decay/wick={so[0]}/{so[1]} ({pc(so[1],so[0]+so[1])}% wick) life={so[2]/max(1,so[0]+so[1]):.0f} copies={so[3]}; "
              f"strict reig total={A['r0'][2]+A['roff'][2]} (off0 {pc(A['roff'][2], A['r0'][2]+A['roff'][2])}%) strict wick total={s0[1]+so[1]} (off0 {pc(so[1], s0[1]+so[1])}%) all births={A['births']} off0={pc(A['off0'],A['births'])} no_mass={A['nm']}")
