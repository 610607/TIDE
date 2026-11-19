"""Mechanism check table: per run, births, exact births %, copies started/cut/born/born_cut."""
import sys, pathlib, re
print("| run | active end | births | exact % | copies started | cut % | born from copies | cut among born % | intact-parent copy births, intact child % |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for p in sorted(pathlib.Path(sys.argv[1]).glob(sys.argv[2] if len(sys.argv) > 2 else "*.tsv")):
    lines = p.read_text().splitlines()
    births = exact = 0.0
    for l in lines[1:]:
        f = l.split("\t")
        if len(f) > 5 and f[0].isdigit():
            b = int(f[2]); births += b; exact += b * float(f[3]) / 100
    phys = [l for l in lines if l.startswith("# physics")]
    kv = dict(x.split("=", 1) for x in phys[-1][len("# physics "):].split()) if phys else {}
    fin = next((l for l in lines if l.startswith("final")), "")
    act = re.search(r"active=(\d+)", fin).group(1) if fin else "?"
    pc = next((l for l in lines if re.match(r"parent intact +copy", l)), "")
    m = re.search(r"births=(\d+) intact_child=([\d.]+)%", pc)
    pcs = f"{m.group(1)}, {float(m.group(2)):.1f}" if m else "-"
    if kv:
        st, cut, born, bc = (int(kv[k]) for k in ("copies_started", "copies_cut", "copies_born", "copies_born_cut"))
        cells = [st, f"{100*cut/st:.1f}" if st else "-", born, f"{100*bc/born:.1f}" if born else "-"]
    else:
        cells = ["-"] * 4
    print(f"| {p.stem} | {act} | {int(births)} | {100*exact/births if births else 0:.1f} | " + " | ".join(map(str, cells)) + f" | {pcs} |")
