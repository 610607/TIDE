"""Enumerate the v1 single-copy substitutions around the confirmed fetch founders."""
import argparse
from pathlib import Path

from study import BUILD, HERE, LIMIT, Assays, Setup, require, rows_to_file, table

ALPHABET = b"R.JTSH+>CLDP"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--observe",type=Path,default=BUILD/"observe")
    args = parser.parse_args()
    assays = Assays(args.observe.resolve())
    cases = sorted({r["anchor_assay"] for r in table(HERE/"families.tsv")})
    observed = {(r["parent_common_assay"], r["child_hex"]):r["child_common"]
                for r in table(HERE/"changed-births.tsv")}
    tests = []
    for anchor in cases:
        arm, parent_hex, donor, side = anchor.split("-")
        parent = bytes.fromhex(parent_hex)
        direction = "NESW".index(side)
        ref = Setup(arm,parent_hex,donor,direction)
        require(assays.run(ref,LIMIT)[1] == "dependent", "missing parent phenotype")
        for offset, original in enumerate(parent):
            for new in ALPHABET:
                if original == new:
                    continue
                mutant = (parent[:offset]+bytes([new])+parent[offset+1:]).hex()
                case = Setup(arm,mutant,donor,direction)
                scores, result = assays.run(case,LIMIT)
                field_result = observed.get((anchor,mutant))
                if field_result:
                    require(result == field_result, "observed substitution differs")
                tests.append(dict(anchor=anchor, offset=offset, original=chr(original), substitute=chr(new),
                    mutant_hex=mutant, assay=case.key(), result=result,
                    allowed_births=scores["on"][0], denied_births=scores["off"][0],
                    allowed_using_channel=scores["on"][1], allowed_cycle=scores["on"][3],
                    denied_cycle=scores["off"][3], observed_pedigree_edge=int(field_result is not None)))
    require(len(tests) == 55*len(cases) and sum(r["observed_pedigree_edge"] for r in tests) == len(observed),
            "incomplete single-step census")
    args.out.mkdir(parents=True,exist_ok=True)
    rows_to_file(args.out/"substitutions.tsv",tests)
    # The serial paths repeat for overlapping mutant neighborhoods. One row per
    # generation and assay key keeps the exact witnesses available for replay.
    rows_to_file(args.out/"substitution-generations.tsv",assays.records)


if __name__ == "__main__":
    main()
