# Space can disappear before a reader can use a live donor

Changing the shape of a 64-site torus produced three encounters with a compatible live eastern neighbor in the 16 × 4 fields. All three focal readers spent the encounter waiting for a daughter site. Across all 768 runs, no reader had a compatible live eastern neighbor at its first copy attempt, the prespecified primary endpoint. Three mothers in the 16 × 4 fields did transmit their reader bytes unchanged by copying residual material in their own reserved daughter sites. Focal permission forks reproduced each of those births and identified the required read access. [Field protocol](protocol.md) · [Targeted fork protocol](fork-protocol.md)

## Matched layout comparison

Each layout began with a single independent ancestor and ran the same 256 new seeds, 321–576, for 2,048 ticks. Width runs east–west. The mutation rate, total site count, lifespan, first-free placement, coordinate arbitration and reclamation policy were fixed. Seeds were matched by identifier. Geometry changes the later site and timing of mutation draws. This is a comparison of these complete spatial layouts.

| Layout | Reader newborns | Readers reaching first copy | Compatible live donor in any adjacent bank during window | Compatible live donor east during window | Compatible live donor east at first copy | Two-generation field candidate events | Confirmed events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 × 8 | 554 | 429 | 1 | 0 | 0 | 1 | 0 |
| 4 × 16 | 551 | 395 | 1 | 0 | 0 | 2 | 0 |
| 16 × 4 | 529 | 431 | 8 | 3 | 0 | 2 | 0 |

The primary seed incidence was 0/256 in each arm, with zero discordant seed pairs for either rectangle versus the square. The three eastern encounters occurred in distinct seeds. Their scarcity limits inference about an advantage of a wider layout. Across all arms there were 1,000,951 births. Every population was alive and reproducing in the final 80 ticks at both checkpoints. [Paired seed comparisons](contrasts.tsv) · [Every field outcome](checkpoints.tsv) · [Per-seed screen](seeds.tsv) · [Reader census](readers.tsv)

## What prevented simultaneous access

In the three pre-copy eastern encounters the focal CPU was executing reserve. Across 112 ticks with the compatible eastern reader alive it received 112 busy outcomes. On 111 of those ticks every neighbor was occupied or reserved. On the remaining tick a free site was contested. At the first successful reservation the eastern bank had already ceased to be occupied by the reader. [Opening snapshots and executed instructions](fork-openings.tsv)

| Seed | Live eastern reader at opening of ticks | Focal reservation won | First copy | Eastern bytes at first copy | Focal product |
| ---: | --- | ---: | ---: | --- | --- |
| 419 | 1446–1485 | 1499 | 1501 | `RJCLT` | `RJCLT` |
| 561 | 1993–2035 | 2036 | 2038 | `RSCLD` | `RSCLD` |
| 569 | 842–870 | 871 | 873 | `RSCLD` | `RSCLD` |

In seed 419 another CPU reserved the released bank and overwrote two positions before the focal won it. In seeds 561 and 569 the focal reserved the former reader's bank while the reader bytes were still there. All five byte reads then came from its own reservation. [Detailed field products](products.tsv) · [Fork products](fork-products.tsv)

## Five reader-to-reader births

Of 1,754 births after external reads, five produced `RSCLD` from an `RSCLD` mother. In seeds 390 (8 × 8) and 349 (4 × 16), the actual copy inputs were `R.CLD`. A copy substitution restored the reader's `S` instruction in the product. In seeds 555, 561 and 569 (16 × 4), all five input bytes already encoded the reader and survived copying unchanged. Each of those three mothers read from its own daughter reservation. Seed 555 first saw exact eastern bytes as free or reserved material. Seeds 561 and 569 also saw them in a living individual before reservation. The byte provenance separates these two routes to a same-genome daughter. [Inputs, outputs and bank ownership](products.tsv)

The frozen field screen yielded five grandchild events across four seeds. Three events had a reserved first source in at least one generation. The two live-first-source events belonged to seed 349. Their donor backgrounds supported the first birth but did not sustain serial read use. No event met the live-donor confirmation criterion. [All candidate replays](pairs.tsv) · [Assay generations](generations.tsv)

## Counterfactuals in the actual fields

We forked the committed birth state for 11 selected individuals and followed each one to age death under ordinary access, denial of reads specifically from its own reservation, and denial of all external reads. The factual branches matched every original birth through tick 2,048. Denying only own-reservation reads eliminated all births from each of the three mothers that had copied intact reader inputs into reader daughters. Denying all external reads eliminated births in all 11 selected individuals. These changes were confined to the focal CPU's copy attempts. [All 33 forks](forks.tsv) · [Selection reasons](fork-targets.tsv)

All five same-genome daughters eventually produced offspring. None produced another reader in its lifetime. The daughter born at the original cutoff in seed 561 produced `P.CLD` at tick 2,063 in the ordinary follow-up. That birth belongs only to the follow-up. The focal interventions establish a requirement for reading the reserved bank in specific births. The search for sustained natural read dependence remains open. [Branch birth ledgers](fork-products.tsv)

## Replay

The baseline VM and earlier measurements were published at `b61abe7`. The field protocol was committed separately at `3c43a53` before the outcome runs. From the repository root use a C++20 compiler and Python 3.10+.

```sh
d=kernel/runs/geometry-01
out=kernel/build/geometry
mkdir -p "$out"
shasum -a 256 -c "$d/revision.sha256"
make -C kernel all test
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp kernel/runs/horizon-01/observe.cpp -o kernel/build/observe
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp "$d/field.cpp" -o "$out/field"
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp "$d/fork.cpp" -o "$out/fork"
python3 -B "$d/geometry.py" "$out"
python3 -B "$d/audit.py" "$out"
for f in "$d"/*.tsv; do cmp "$f" "$out/${f##*/}" || exit 1; done
```

The square prefix checks cover four historical seeds outside the study sample. A second build using reversed VM visit order reproduced the field tables and the fork records. In `products.tsv`, each external write lists destination offset, copy tick, source site, source offset, opening bank type, source birth tick and reservation owner's site, in that order. The types o, r and f mean occupied, reserved and free. Unlisted offsets used local data. A dash in a first-attempt field means the reader reached death or the cutoff without attempting a copy. [Prefix checks](prefix-checks.tsv) · [Pinned inputs and records](revision.sha256)
