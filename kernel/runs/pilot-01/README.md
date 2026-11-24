# Pilot 01, one evolved instruction borrower

In the eight discovery seeds, one fetch-only seed met the predeclared test for heritable dependence. The read-only arm produced births after external reads, with zero qualifying two-generation links. All 24 populations were alive and had reproduced in the final 80 ticks. These are executed results from VM v1. [Protocol](protocol.md) · [All seeds](seeds.tsv) · [All candidate births and assays](links.tsv)

| Channels | Seeds | Births | Births after contact | Candidate births | Seeds with candidates | Confirmed seeds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Self only | 8 | 2,444 | 0 | 0 | 0 | 0 |
| Neighbor data only | 8 | 2,442 | 9 | 0 | 0 | 0 |
| Neighbor fetch only | 8 | 2,441 | 46 | 28 | 5 | 1 |

## What evolved in seed 8

The supplied ancestor `R.CLD` loops over its own copy instruction. At tick 74 a successful copy by its descendant at site 35 substituted `J` for `L` at offset 3. The offspring at site 34 was born at tick 78 with `R.CJD`. The new sequence copies one byte locally, then jumps east. In the confirmed pair, the eastern bank contained `J.CLD`. Its copy loop finished copying the caller's five-byte body into the caller's reservation. Its final divide instruction also ran on the caller's CPU. All five data bytes came from the caller. [Mutation, addresses and field birth trace](case-trace.tsv)

The link from the founder to the confirmed pair is identifiable even when a site is reused. Each tuple gives (site, birth tick).

```text
(36,0) → (35,52) → (34,78) → (42,93) → (50,108) → (58,123)
ancestor             mutant      mother     daughter    granddaughter
```

The field CPUs at sites 42 and 50 borrowed from sites 43 and 51, respectively. Both produced daughters carrying their own sequence. In separate mutation-free assays their first donor backgrounds had identical bytes and relative positions. Each starting genotype produced three serial generations in 45 ticks with focal fetch enabled. With only focal fetch removed, no daughter was born and the full dynamical state repeated by tick 8. The independent ancestor produced three generations in 39 ticks in both branches. The assay tests access to a bank's instructions. Whether the donor's own CPU has to keep running is a separate question. [Paired assay rows](links.tsv)

Six individuals belonged to the contiguous `R.CJD` field family founded at tick 78, counting the founder. Its deepest path contained four individuals. Its last clonal birth was at tick 177 and the last member died at tick 258. The population as a whole still reproduced through the end of the run. [Pedigree audit](audit_case.py)

## Reading the records

In `seeds.tsv`, contacts count successful external copy reads or fetched instructions. A birth counts as exposed once its CPU has made any such contact. A candidate birth is a grandchild event whose mother and grandmother each had a contact before their respective birth events. Repeated births by a given CPU can therefore contribute multiple rows. The primary incidence denominator is seeds. A zero first-candidate tick means no candidate.

In `links.tsv`, mother and child denote the two field CPUs tested, and daughter denotes the second CPU's product. Site numbers are row-major with y increasing northward. Direction 0, 1, 2, 3 denotes north, east, south, west. Byte strings are hexadecimal. The four assay scores each give generations completed / generations using the channel / total ticks / exact-cycle flag. A timeout at 64 ticks per generation is inconclusive. A first contact with a free or reserved bank cannot enter the protocol's live-donor assay. Those rows retain the observed bank type and bytes. The independent [replication batch](../replication-01/README.md) used the same screening and assay rules.

## Replay

Run from the repository root using Make, a C++20 compiler and Python 3 for the pedigree audit. The published runs used Apple Clang 21 on arm64. The SHA-256 manifest pins the actual source files and protocol relative to the repository root. The parent repository revision when implementing v1 was `ede3fee57e46d04432cc2d79bc84bf16e6c37eb0`. Build output and local traces go under the ignored build directory.

```sh
shasum -a 256 -c kernel/runs/pilot-01/revision.sha256
make -C kernel all test
kernel/build/tide pilot kernel/build/discovery-links.tsv > kernel/build/discovery-seeds.tsv
cmp kernel/runs/pilot-01/seeds.tsv kernel/build/discovery-seeds.tsv
cmp kernel/runs/pilot-01/links.tsv kernel/build/discovery-links.tsv
kernel/build/tide trace fetch 8 > kernel/build/fetch-8.tsv
python3 kernel/runs/pilot-01/audit_case.py kernel/build/fetch-8.tsv kernel/build/case-trace.tsv
cmp kernel/runs/pilot-01/case-trace.tsv kernel/build/case-trace.tsv
kernel/build/tide assay fetch R.CJD J.CLD E > kernel/build/seed8-assay.tsv
```

The trace command emits each CPU attempt and death, its opening addresses, bytes copied, external bank provenance and offspring bytes. The assay command writes the focal steps for all four branches to standard output and their scores to standard error. For any live-donor candidate row, decode the recorded genome and donor bytes, and pass the corresponding compass direction.
