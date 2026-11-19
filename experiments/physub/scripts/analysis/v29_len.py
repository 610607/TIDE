"""Sum v25 length-ledger dm terms over windows. Usage: v29_len.py run.tsv..."""
import re, sys
TERMS = ["copy_sp", "copy_op", "reignite", "self", "gain", "found", "decay", "wick", "loss_f", "loss_s", "inplace_f", "inplace_s"]
for path in sys.argv[1:]:
    acc = {t: 0.0 for t in TERMS}; dmean = 0.0; src = {}
    for l in open(path):
        if l.startswith("# length "):
            dmean += float(re.search(r"dmean=([-\d.e]+)", l).group(1))
            for t in TERMS:
                acc[t] += float(re.search(rf" {t}=[\d]+/-?[\d]+/([-\d.e]+)", l).group(1))
        elif l.startswith("# lengthsrc "):
            for k in ("add_residue", "add_foreign", "add_parent", "lost_gap", "lost_parent", "lost_foreign"):
                b, dm = re.search(rf"{k}=(\d+)/([-\d.e]+)", l).groups()
                s = src.setdefault(k, [0, 0.0]); s[0] += int(b); s[1] += float(dm)
    name = "/".join(path.split("/")[-2:])
    print(f"{name}: dmean {dmean:+.2f} | " + " ".join(f"{t} {v:+.2f}" for t, v in acc.items() if abs(v) > 0.005))
    print("   copy_sp sources: " + " ".join(f"{k} {v[0]}/{v[1]:+.2f}" for k, v in src.items()))
