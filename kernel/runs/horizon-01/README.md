# Neighbor dependence with a longer observation window

Seven of 32 prospectively tested fetch seeds evolved a field mother–daughter pair that required access to a neighbor's instructions in the standardized assay. Both genomes transmitted the use of that access through three serial births. Removing the focal CPU's fetch permission produced an exact, birthless cycle. In the data-read arm, the 37 daughters born to externally reading mothers across all three cohorts inherited a different sequence from their mother's. None subsequently made a successful external read during observation. [Horizon protocol](protocol.md) · [Read audit protocol](read-audit-protocol.md)

## What the 64-tick assay missed

All 16 previously unresolved two-generation events in the replication cohort were resolved by observing the same complete arenas for longer. They came from six seeds and four distinct genome–donor–direction setups. Their denied arenas first repeated at tick 96, 106 or 110, with periods of 5, 2 or 6 ticks, respectively. Because mutation and age death were disabled, exact equality of the complete dynamical state proves that subsequent execution in that arena repeats. In the enabled branches each focal genome used neighbor fetch in three generations. The independent ancestor reproduced under both permissions. [Each generation and its first repeat](generations.tsv)

| Field cohort | Fetch seeds | Candidate events | Eligible events with two live first contacts | Confirmed events at 4,096 | Confirmed seeds at 64 | Confirmed seeds at 4,096 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Discovery, seeds 1–8, retrospective | 8 | 28 | 9 | 7 | 1 | 3 |
| Original replication, seeds 9–32, retrospective | 24 | 35 | 17 | 16 | 0 | 6 |
| New seeds 33–64, prospective | 32 | 75 | 21 | 12 | 0 | 7 |

The longer limit was fixed before generating seeds 33–64. In this prospective set, 12 qualifying events occurred in seeds 36, 39, 41, 47, 50, 62 and 64. All 12 retained the same genomic bytes through field mother, daughter and granddaughter. Among the other nine eligible events, both tested genotypes could reproduce with fetch removed in seven events and one could do so in two. Fifty-four events had a non-live first contact in one or both field individuals. These remain outside the live-donor comparison. Every generation in the complete long-window assay table reached a birth or repeat by tick 112. That observed maximum applies to these reconstructed arenas. [Candidate rows with both classifications](events.tsv) · [All seeds, including zeros](seeds.tsv)

All 96 new field runs, covering the three arms, were alive and reproducing in their last 80 ticks. The read-only and self-only arms produced zero two-generation candidates in all three cohorts. The seed results give incidence under this field screen, donor reconstruction and fixed search budget. [Original new field output](field-seeds.tsv) · [Original 64-tick candidate replays](field-links.tsv)

## Field persistence

Replaying the complete field traces verified every confirmed birth link, initial donor contact and product. The 35 confirmed events belonged to 19 distinct mothers' same-genome families across the three cohorts. Thirty-one events retained identical bytes through all three field individuals. The prospective cohort contributed eight families. Six of those had lost their last clonal member by tick 512. The other two still had one and two members, respectively. A member here is a descendant along a chain of identical genomes. Mutant branches can have a different fate. A separate [continuation to field tick 4,096](../persistence-01/README.md) followed those original families. [Origins, copy provenance, depth and all family outcomes at 512](families.tsv)

## Why the observed data reads stopped at one generation

Across the 64 read-only runs, 19 seeds produced 221 successful external reads. In 16 seeds, 22 mothers with the same five-byte genome `RSCLD` subsequently produced 37 daughters. All five bytes of every daughter were read from a neighboring bank. In 34 births the copy introduced no substitution. In the other three it introduced one. None of the 37 daughters received the mother's complete `RSCLD` sequence. Twenty-five daughters reproduced, all without a successful external read. Thirty-two daughters were followed through death and five through the field cutoff. This localizes the loss to the copied product on the observed paths. [Every exposed birth, copy source and daughter fate](read-births.tsv) · [All 64 read seeds](read-seeds.tsv)

The first external read came from an occupied bank for six mothers responsible for 12 births. All six had the same reconstructed background, an eastern donor carrying the independent ancestor `R.CLD`. In the mutation-free replay the mother needed the donor for its first birth, which produced `R.CLD`. The daughter and granddaughter reproduced without using external reads. The other 25 field births had mothers whose first contact was a reserved bank. [Live-donor generation records](read-generations.tsv)

A separate engineered comparison changed the donor's second byte from the no-op period to `S`, leaving its length at five. With the `RSCLD` donor, the same focal mother produced `RSCLD` and all three successive generations made five external reads each. With access removed, the focal arena repeated without a birth under either donor condition. The independent ancestor reproduced in both. This shows that the donor's sequence can determine whether the reader's behavior is transmitted in the specified arena. The occurrence of a matching natural donor neighborhood remains a separate field question. [Matched donor protocol](donor-control.md) · [Both conditions and all controls](donor-generations.tsv)

## Replay

Use Make, a C++20 compiler and Python 3.10+ from the repository root. The field runner and VM are the versions in the historical manifests. The new single-generation observer calls the same VM and records complete states with their first tick. The analysis replays daughter bytes in fresh arenas and checks all eligible 64-tick branch scores against the original field runner before accepting the longer results.

```sh
shasum -a 256 -c kernel/runs/pilot-01/revision.sha256
shasum -a 256 -c kernel/runs/replication-01/revision.sha256
shasum -a 256 -c kernel/runs/horizon-01/revision.sha256
make -C kernel all test
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp kernel/runs/horizon-01/observe.cpp -o kernel/build/observe
mkdir -p kernel/build/horizon
kernel/build/tide batch 33 64 kernel/build/horizon/field-links.tsv > kernel/build/horizon/field-seeds.tsv
python3 -B kernel/runs/horizon-01/measure.py kernel/build/horizon --field-dir kernel/build/horizon
python3 -B kernel/runs/horizon-01/read_paths.py kernel/build/horizon --field-dir kernel/build/horizon
python3 -B kernel/runs/horizon-01/donor_control.py kernel/build/horizon
for f in kernel/runs/horizon-01/*.tsv; do cmp "$f" "kernel/build/horizon/${f##*/}" || exit 1; done
```

`events.tsv` joins to the original candidate row by arm, seed, birth tick and daughter site. Its two assay keys join to `generations.tsv`. Within a generation `end_tick` counts ticks from that arena's initialization. A cycle has an earlier identical state at `first_equal_tick` and period equal to their difference. A zero confirmed count on an excluded event means the event did not pass the screen. `families.tsv` joins on cohort, arm, seed and family root (site, birth tick). In an origin write, `tick@site.offset=input>output` records the read location and bytes in hexadecimal. Family depth counts the founder as one. The three protocols and the source and data checksums pin this measurement. [Checksum manifest](revision.sha256)
