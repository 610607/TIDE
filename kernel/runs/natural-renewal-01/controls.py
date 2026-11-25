"""Test the same classifier against a recorded family and multi-generation fixtures."""
import csv
import gzip
from dataclasses import replace
from pedigree import Pedigree, Person, from_record
from run import HERE


def rows(path):
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt") as stream:
        yield from csv.DictReader(stream, delimiter="\t")


def archive():
    src = HERE.parent / "partner-placement-01/results"
    key = "20349-13-1227"
    case, = (r for r in rows(src / "cases.tsv") if r["seed"] == "20349" and r["born"] == "1227" and r["site"] == "13")
    events = [r for r in rows(src / "nodes.tsv.gz") if r["case"] == key]
    tests = {}
    for b in rows(src / "branches.tsv"):
        if b["case"] != key:
            continue
        root = Person(int(b["root"]), int(case["born"]), case["genome"], b["root_confirmed"] == "1")
        people = [root]
        for r in events:
            if r["arm"] == b["arm"]:
                passed = int(r["births"]) > 0 and int(r["exposed"]) > 0 and r["denied"] == "0" and int(r["blocked"]) > 0
                people.append(from_record(r, passed))
        tree = Pedigree(people)
        _, _, chains = tree.score(root)
        renewed = [c for c in chains if len(c) > 1]
        assert renewed == ([(76, 121)] if b["arm"] == "together" else [])
        if renewed:
            assert tree.people[121].actor == 83 and tree.people[121].donor == 76
        tests[b["arm"]] = len(renewed)
    assert tests == {"together": 1, "apart": 0, "ordinary": 0}
    return tests


def fixture():
    # Two complete replacements. A passive initial template is eligible.
    g = "52532e434c44"
    r, d = Person(1, 0, g, True), Person(2, 0, g, False)
    a = Person(3, 35, g, True, 1, 2, True, 10, 0)
    b = Person(4, 50, g, True, 1)
    c = Person(5, 100, g, True, 4, 3, True, 82, 35)
    e = Person(6, 110, g, True, 4)
    f = Person(7, 155, g, True, 6, 5, True, 134, 100)
    group = [r, d, a, b, c, e, f]

    def depth(people):
        return max((len(path) - 1 for path in Pedigree(people).score(r)[2]), default=0)

    assert depth(group) == 2
    assert depth([r, d, a, b, replace(c, first_read=81)]) == 0
    assert depth([r, d, a, replace(b, actor=-1), c]) == 0
    assert depth([r, d, a, replace(b, confirmed=False), c]) == 0
    assert depth([r, d, replace(a, intact=False), b, c]) == 0
    assert list(Pedigree(group).chains(a, 154)) == [(3, 5)]


if __name__ == "__main__":
    print("Archived replacements:", archive())
    fixture()
    print("Recursion, ancestry, assay, copy, death and cutoff controls passed.")
