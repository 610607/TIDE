# What transmits neighbor dependence?

An archived fetch borrower transmitted its dependence across a point substitution. In a separate prospective cohort, all 143 newborn readers lacked a compatible live neighbor from birth through the opening of their first copy attempt or the end of observation. In a seeded field, supplying compatible readers and retaining residual bytes allowed an uninterrupted reader lineage to reach seven parent-to-daughter transmissions. These results have different denominators. The fetch example comes from an evolved pedigree, the spatial census covers unseeded encounters after the independent ancestor, and the donor arrangements are controlled interventions. [Field protocol](protocol.md) · [Control protocol](controls-protocol.md)

## Fetch dependence across a mutation

The eight previously confirmed prospective founder families contained 34 individuals including the founders. Of their 26 descendant births, one changed sequence. In seed 47 a parent carrying `J.CLD` copied its own bytes and the first byte changed to `D`. The daughter `D.CLD` was born at tick 374, never fetched externally and left no offspring. In its root's matched donor assay both focal permission settings reached a birthless cycle at tick 92. Across all eight pedigrees, including changed descendants, the last death occurred at tick 713. [Every root](families.tsv) · [Changed birth](changed-births.tsv) · [Paired generation outcomes](generations.tsv)

A retrospective audit of all 35 previously confirmed three-individual events found four with unequal genomes somewhere in the chain. In one event the change occurred between the two field individuals that were themselves tested. In discovery seed 8, the mother at site 62 copied a no-op as `H` at tick 405. Her daughter at site 63 was born at tick 413 with `JHCLD` and produced a `JHCLD` daughter at tick 466. Both field CPUs fetched external instructions and copied their own data. With the same eastern `R.CLD` donor, each genotype took 14 ticks per birth over three generations. Disabling focal fetch yielded zero births and an exact cycle at tick 96 in both cases. This is a retrospective witness in the discovery cohort. The prospective pedigrees above contributed no second example. [All previously confirmed pairs](archived-pairs.tsv) · [Ten copy events in seed 8](archived-witness.tsv)

To measure what the field's small mutation sample could miss, we tested every one-step substitution around the six distinct confirmed founder setups. The field's substitution alphabet gives 55 alternatives per five-byte genome. Of the 330 mutant–background combinations, 215 retained serial fetch dependence, eight reproduced for three generations under both permission settings, and 107 stopped in an exact cycle before completing three generations even with access. The number retaining dependence ranged from 22 to 43 per setup. These are equally weighted changes in the recorded donor arenas. Field mutation opportunities and reproductive success set different weights. [Complete substitution panel](substitutions.tsv) · [Generation-level witnesses](substitution-generations.tsv)

## Natural reader encounters

The spatial census included all newborns with genome `RSCLD`, even when they never copied. Each occupied neighbor sequence was tested as a live eastern donor in the standardized read assay. We also checked the actual eastern address, the four local banks of any ownership for exact reader bytes, and the rest of the lattice for other live readers. A view is taken at birth and on each opening through the first copy attempt, death or cutoff. A reader that survived without attempting a copy contributed the final tick-512 view. [Every reader and its window](readers.tsv)

| Read-only field cohort | Seeds | Newborn readers | Other live reader present somewhere during window | Compatible live donor in four neighbors during window | Readers reaching first attempt | Readers producing daughters | Daughter births | Daughters subsequently reading externally |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical, 1–64 | 64 | 28 | 3 | 0 | 23 | 22 | 37 | 0 |
| Prospective, 65–320 | 256 | 143 | 15 | 0 | 114 | 103 | 146 | 0 |

In the 256 prospective fields, 115 seeds produced a newborn reader. Thirty distinct live neighbor genotypes occurred within the observation windows. None qualified as a compatible eastern donor in the assay. No exact reader bytes appeared in any adjacent free or reserved bank in those windows either. At the first attempt the addressed bank was occupied for 40 readers, reserved for 70 and free for four. All 146 field daughters had different bytes from their reader mother. Seventy-four daughters themselves reproduced. The original two-generation contact screen, run across all genotypes, found zero qualifying events. All 256 fields were alive and reproducing in their final 80 ticks. This evidence localizes a shortage of compatible local bytes for this reader under these settings. The spatial census ends at the first attempt and the daughter audit extends through tick 512. [All 320 seeds](read-seeds.tsv) · [Every reader product](reader-products.tsv) · [Two-generation field candidates](read-links.tsv)

## Donor supply and residual memory

The seeded assay leaves daughters at their actual birth sites. The focal reader starts west of a three-site column of live donors. In each adjacent condition one more donor carries the five-byte reader sequence through a change at offset 1. The mutation rate is zero and the independent ancestor and all starting positions are fixed. Each cell below gives maximum reader transmission depth and total reader births from the focal family. Founder depth is zero. [Seeded layout and controls](controls-protocol.md)

| Compatible donors in column | Retain released bytes, depth / births | Clear released bytes, depth / births |
| ---: | ---: | ---: |
| 0 | 0 / 0 | 0 / 0 |
| 1 | 3 / 6 | 1 / 3 |
| 2 | 4 / 12 | 4 / 7 |
| 3 | 7 / 20 | 4 / 8 |

The one-donor layout shows how reclamation enters the pedigree. At tick 94 the same parent at site 35 divided into site 36 under both policies. All five reads came from site 36, then reserved by that parent. Retention left the former occupant's reader bytes there and the daughter received `RSCLD`. Clearing on release gave the daughter five zeros. This birth accounts for the first extra transmission in the one-donor retained field. The source was the parent's own daughter reservation in a neighboring bank. The seven-step chain is evidence for inherited use of neighboring bytes in this seeded field. These traces distinguish access to neighboring memory from the separate question of dependence on ongoing donor execution. [Retained birth provenance](patch-births.tsv) · [Cleared birth provenance](empty-births.tsv)

All 32 seeded trajectories, including the controls, contained a reproducing population at tick 512. No continuously transmitted reader family descended from the focal founder had a living member then. With focal read denied, the reader founder had zero births under every layout and reclamation policy. Independent ancestor founders had three births in every condition. The depth-seven result describes a transient lineage in one deterministic arrangement. [Retained populations](patch.tsv) · [Cleared populations](empty-patch.tsv) · [Reclamation comparison protocol](reclamation-protocol.md)

## Replay

Run from the repository root with a C++20 compiler, Make and Python 3.10+. These observers use the frozen VM and assay. The historical hashes, clonal ledgers and previously exposed reader births are checked during the analysis.

```sh
shasum -a 256 -c kernel/runs/transmission-01/revision.sha256
make -C kernel all test
d=kernel/runs/transmission-01
out=kernel/build/transmission
mkdir -p "$out"
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp kernel/runs/horizon-01/observe.cpp -o kernel/build/observe
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp "$d/field.cpp" -o "$out/field"
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp "$d/donor_patch.cpp" -o "$out/donor_patch"
python3 -B "$d/study.py" "$out"
python3 -B "$d/substitutions.py" "$out"
python3 -B "$d/archive.py" "$out"
"$out/donor_patch" "$out/patch.tsv" "$out/patch-births.tsv" retain
"$out/donor_patch" "$out/empty-patch.tsv" "$out/empty-births.tsv" empty
for f in "$d"/*.tsv; do cmp "$f" "$out/${f##*/}" || exit 1; done
```

The first two columns of an individual identity are its site and birth tick within a seed. Assay keys encode the channel, focal and donor bytes in hexadecimal, and the relative direction. Exact state equality is evaluated by the frozen [generation observer](../horizon-01/observe.cpp). For the birth traces, `own_reserved_bytes` counts external bytes read from a reservation owned by the executing CPU. `reader_depth` equals -1 once a descendant has left a continuous reader path. A zero last reader birth in a population summary means no reader transmission occurred.
