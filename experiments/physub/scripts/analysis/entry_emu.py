# Usage: entry_emu.py (no input; prints traces).
# Own-site emulation of ps_exec.cpp plan() for polite entered off offset 0 (code inspection aid).
OPS = ["MOV","INC","DEC","JZ","JMP","RND","IGNITE","WALL","UNWALL"]
def op(n): return n + 1
polite = [op(0),34,36, op(0),34,38, op(5),32, op(0),32,40, op(3),44, op(4),45, op(0),30,32,
          op(1),31, op(1),33, op(3),33, op(4),43, op(6),32, op(4),30,
          0,192,1,192,0,42,0,31,0,33,0,44,192,15,0,6] + [0]*18
def run(mem, ip, mode, steps=40):
    mem = mem[:]; log = []
    for _ in range(steps):
        b = mem[ip % 64]
        if b == 0: log.append(f"ip {ip}: INERT -> wick"); break
        o = (b - 1) % 9; L = 3 if o == 0 else 2
        opnds = [mem[(ip + k) % 64] for k in range(1, L)]
        nxt = (ip + L) % 64
        if mode == "fail" and any(v == 0 for v in opnds):
            log.append(f"ip {ip}: {OPS[o]} {opnds} fails (INERT operand)"); ip = nxt; continue
        x = opnds[0] % 64
        if o == 0:
            def ptr(p): d = mem[p % 64]; return ("own" if d == 0 else f"nbr{(d-1)%4}", mem[(p+1) % 64] % 64)
            s, dd = ptr(opnds[0]), ptr(opnds[1])
            val = mem[s[1]] if s[0] == "own" else "?"
            log.append(f"ip {ip}: MOV src {s} -> dst {dd} (byte {val})")
            if dd[0] == "own" and val != "?": mem[dd[1]] = val
        elif o in (1, 2):
            new = (mem[x] + (1 if o == 1 else -1)) % 256
            log.append(f"ip {ip}: {OPS[o]} [{x}] {mem[x]} -> {new}"); mem[x] = new
        elif o == 3:
            z = mem[x] == 0; log.append(f"ip {ip}: JZ [{x}]={mem[x]} {'skip' if z else ''}")
            if z: nxt = (nxt + (1 if mem[nxt] == 0 else 3 if (mem[nxt]-1) % 9 == 0 else 2)) % 64
        elif o == 4: log.append(f"ip {ip}: JMP [{x}] -> {mem[x] % 64}"); nxt = mem[x] % 64
        elif o == 5: log.append(f"ip {ip}: RND -> [{x}] (random)"); mem[x] = 77
        elif o == 6:
            d = mem[x]; log.append(f"ip {ip}: IGNITE ptr [{x}] dir {'own' if d == 0 else (d-1)%4} offset {mem[(x+1)%64] % 64}")
        else:
            d = mem[x]; log.append(f"ip {ip}: {OPS[o]} dir byte [{x}]={d} {'(own: no edge)' if d == 0 else 'edge ' + str((d-1)%4)}")
        ip = nxt
    return log, mem
for entry, fill in [(33, {33: 192}), (31, {31: 192, 32: 1}), (31, {31: 192, 32: 77})]:
    for mode in ("zero", "fail"):
        m = polite[:]
        for k, v in fill.items(): m[k] = v
        log, after = run(m, entry, mode)
        changed = [k for k in range(64) if after[k] != m[k]]
        print(f"== entry {entry} fill {fill} mode {mode}: changed offsets {changed}")
        for l in log: print("   ", l)
# Misaligned polite at ip 1 and 4 with filled 36 / 38
for ip, fill in [(1, {36: 2}), (4, {38: 2})]:
    m = polite[:]; m.update if False else None
    for k, v in fill.items(): m[k] = v
    log, _ = run(m, ip, "fail", steps=1); print(f"== ip {ip} fill {fill}:", log)
