"""v14 summary: census at the last interval plus physics counters, one row per run."""
import sys, pathlib, re
def kvline(line, tag):
    return dict(x.split("=", 1) for x in line[len(tag):].split())
print("| run | replicator peak | end | active | replicators | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | births | from cut copies % | intact-parent copies: intact child % | whole decays (active) |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for p in sorted(pathlib.Path(sys.argv[1]).glob(sys.argv[2] if len(sys.argv) > 2 else "*.tsv")):
    lines = p.read_text().splitlines()
    cen = {int(kvline(l, "# census ")["tick"]): kvline(l, "# census ") for l in lines if l.startswith("# census")}
    phys = [kvline(l, "# physics ") for l in lines if l.startswith("# physics")]
    fin = next((l for l in lines if l.startswith("final")), "")
    m = re.search(r"final tick=(\d+) active=(\d+)", fin)
    end = f"{int(m.group(1))//1000}k" if m and m.group(2) != "0" else (f"extinct {m.group(1)}" if m else "running")
    peak = max(cen.items(), key=lambda kv: int(kv[1]["replicators"])) if cen else None
    pk = f"{peak[1]['replicators']} ({peak[0]//1000}k)" if peak else "-"
    last = cen[max(cen)] if cen else None
    pc = next((l for l in lines if re.match(r"parent intact +copy", l)), "")
    mm = re.search(r"intact_child=([\d.]+)%", pc)
    fid = f"{float(mm.group(1)):.1f}" if mm else "-"
    ph = phys[-1] if phys else {}
    births = ph.get("births", "-")
    cutb = f"{100*int(ph['copies_born_cut'])/int(ph['copies_born']):.1f}" if ph and int(ph["copies_born"]) else "-"
    wd = f"{ph['whole_decays']} ({ph['whole_decays_active']})" if ph and int(ph["whole_decays"]) else "-"
    if last and m and m.group(2) != "0":
        s, c, r = last["nonrep_self/copy/reignite"].split("/")
        a1, a0 = last["mean_age_rep/nonrep"].split("/")
        act = int(last["active"])
        cells = [last["active"], last["replicators"], f"{c} ({100*int(c)/act:.0f}%)", r, f"{a1} / {a0}"]
    else:
        cells = ["0" if m else "-", "", "", "", ""]
    print("| " + " | ".join([p.stem, pk, end] + cells + [births, cutb, fid, wd]) + " |")
