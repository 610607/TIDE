# Where starter lineages lost their program

This is a post hoc, descriptive audit of archived tables. It runs no new simulation and does not change the [fixed cohort](../findings.md) or its endpoints. The [starter audit](../starter-audit/README.md) found that 24 of 31 starts never had a second eligible descendant. This audit asks how each birth from a starter's lineage failed to stay in it.

**Lineage.** For each start, the lineage is every confirmed individual whose same-program ancestry reaches the starting reader. Ancestry runs through actual division or intact living donation, exactly as in the [original pedigree](../../natural-renewal-01/pedigree.py). The script reproduces the archived `confirmed_later` count for all 38 starts (31 here, 7 in [natural-renewal-01](../../natural-renewal-01/starter-audit/README.md)). Every recorded birth executed by a lineage member, or copied intact from one, is either in the lineage or an **exit**. The node tables record every birth whose executor or donor was confirmed, so no exit is missing.

**Exit classes**, tested in this order:

| Class | Definition |
| --- | --- |
| `after_window` | born after the reader's 324-tick window |
| `substituted` | different program, with at least one copy substitution |
| `other_input` | different program, copied without substitution from other bytes |
| `no_offspring` | same program, no births in its lifetime, so the denial assay cannot confirm it |
| `self_only`, `independent`, `never_blocked` | same program but failed the read-denial assay in another way |

**Byte sources:**
- `own_reservation`: all six reads came from the bank being written, which is residue already in the daughter's reservation.
- `one_living_neighbor`: six aligned reads from one living individual.
- `mixed`: any other combination.

## Result

| Cohort | Starts | Lineage births | Stayed in lineage | Exits |
| --- | ---: | ---: | ---: | ---: |
| natural-renewal-02 | 31 | 128 | 54 | 74 |
| natural-renewal-01 | 7 | 25 | 11 | 14 |

| Exit (natural-renewal-02) | Source | Births | Starts with any | Born after both originals died |
| --- | --- | ---: | ---: | ---: |
| other program, unsubstituted | own reservation | 34 | 21 | 9 |
| other program, unsubstituted | one living neighbor | 20 | 16 | 9 |
| other program, unsubstituted | mixed | 4 | 4 | 2 |
| substituted | own reservation | 5 | 5 | 0 |
| substituted | one living neighbor | 4 | 4 | 1 |
| same program, no offspring | one living neighbor | 7 | 7 | 1 |
| **all** | | **74** | **31** | **22** |

- **Most exits were births of another program, copied without error.** That covers 58 of 74 exits. In 34 of them the executor read all six bytes in place from its own daughter's reservation, so the daughter inherited whatever dead program occupied that bank. In 20 it copied a living neighbor that carried a different program.
- **Substitution was a minor exit.** 9 of 74 exits (12%) carried a substitution. At 20,000 ppm per byte, about 11% of six-byte copies are expected to carry at least one.
- **Death before reproduction was a minor exit.** 7 of 74 exits had the lineage's program but no offspring, so the denial assay could not confirm them. Seed 104218's post-turnover birth is one of these.
- **No exit failed the denial assay itself.** Every same-program exit that had offspring was confirmed, and no birth fell outside the window.
- **natural-renewal-01 shows the same pattern.** 12 of its 14 exits were unsubstituted copies of another program (10 from a living neighbor, 2 from the executor's own reservation).

**Interpretation (descriptive).** These readers copy whatever bytes they read. A program stays in the lineage only when the source is a living carrier of the same program. The largest loss comes from copying a different program or in-place residue, not from substitution, early death or loss of dependence. So a cohort that varies mutation rate or lifespan would not address the main exit. These counts are births from related readers and are not independent trials. They do not estimate the effect of any intervention. Why the read pointer meets the daughter's own reservation is not traced here.

## Replay

From the repository root (Python 3.10+; reads only archived tables):

```sh
d=kernel/runs/natural-renewal-02/eligibility-audit
out=$(mktemp -d)
python3 -B "$d/exits.py" "$out"
diff -qr "$d/results" "$out"
```

Outputs: [summary](results/summary.tsv) · [per-start counts](results/families.tsv) · [every exit birth](results/exits.tsv).
