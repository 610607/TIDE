"""Summarize matched placement forks and verify their denominators."""
import argparse
import csv
from collections import Counter
from pathlib import Path


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write(path, header, rows):
    with path.open("w", newline="") as stream:
        table = csv.writer(stream, delimiter="\t", lineterminator="\n")
        table.writerow(header.split())
        table.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir", type=Path)
    out = parser.parse_args().dir
    setups = read(out / "setups.tsv")
    assigned = [s["seed"] for s in setups]
    if list(map(int, assigned)) != list(range(577, 641)):
        raise ValueError("incomplete assignment list")
    arms = {(r["seed"], r["dir"], r["arm"]): r for r in read(out / "branches.tsv")}
    copies = read(out / "copies.tsv")
    scores, totals, comparisons = {}, [], []
    for direction in "WNS":
        won = first = reproduced = maternal = 0
        for s in setups:
            seed = s["seed"]
            qualified = success = False
            if s["tick"] != "-":
                ordinary = arms[seed, direction, "ordinary"]
                won += ordinary["opening_effect"] == "reserve"
                qualified = ordinary["first_link"] == "1"
                mother_denied = arms[seed, direction, "mother_denied"]
                if int(mother_denied["mother_births"]):
                    raise ValueError("mother denial did not block births")
                if qualified:
                    if not int(mother_denied["mother_failed_copies"]):
                        raise ValueError("first-link mother never attempted a blocked copy")
                    denied = arms[seed, direction, "daughter_denied"]
                    if int(denied["daughter_births"]) or denied["registered_hash"] != ordinary["registered_hash"]:
                        raise ValueError("daughter control mismatch")
                    if int(ordinary["live_births"]) and not int(denied["daughter_failed_copies"]):
                        raise ValueError("positive daughter never attempted a blocked copy")
                    success = int(ordinary["live_births"]) > 0
                    maternal += int(ordinary["maternal_births"]) > 0
                    reproduced += int(ordinary["daughter_births"]) > 0
                first += qualified
            scores[seed, direction] = qualified, success
        overlapping = {r["seed"] for r in copies if r["role"] == "daughter" and r["dir"] == direction
                       and r["arm"] == "ordinary" and r["effect"] == "copy" and r["mother_alive"] == "1"}
        totals.append((direction,len(assigned),sum(s["tick"] != "-" for s in setups),won,first,
                       len(overlapping),reproduced,sum(scores[s,direction][1] for s in assigned),maternal))
    for other in "NS":
        for restricted in (False, True):
            pairs = [(scores[s,"W"], scores[s,other]) for s in assigned]
            if restricted:
                pairs = [(a,b) for a,b in pairs if a[0] and b[0]]
            counts = Counter((a[1],b[1]) for a,b in pairs)
            comparisons.append(("W",other,"both_first_links" if restricted else "all_assigned",
                                len(pairs),counts[1,1],counts[1,0],counts[0,1],counts[0,0]))
    write(out / "summary.tsv","placement assigned setups opening_wins first_links daughters_copying_while_mother_alive "
          "daughters_reproducing confirmed_any_live confirmed_maternal",totals)
    write(out / "comparisons.tsv","first second population pairs both first_only second_only neither",comparisons)


if __name__ == "__main__":
    main()
