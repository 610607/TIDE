# A reader lineage transmitted dependence through two natural births

Seed 3562 met the prospective criterion for inherited read dependence. In two mother–daughter–grandchild pedigrees the mother copied an exact reader from a living neighbor, and her west-born daughter subsequently copied that still-living mother into another reader. Removing external read access independently from each of the four reproducing CPUs eliminated all its births. Both pedigrees belong to one family in one of 8,192 untreated worlds. In the separate matched placement experiment, west-born daughters produced live-reader grandchildren in eight of 64 seed backgrounds. [Frozen design](protocol.md) · [Natural chains](natural/chains.tsv) · [Controlled outcomes](controlled/summary.tsv)

## Untreated field incidence

All worlds started with one independent ancestor and ran 2,048 ticks. The 8,192 new seeds produced 10,598,408 births. There were 17,546 exact reader newborns and 18,869 births by readers. Twenty seeds produced 28 intact transfers in which one live external reader supplied all five unchanged bytes. Two of those births carried a chain through a second consecutive transfer. At the cutoff 8,191 populations were reproducing, zero were stagnant and seed 11304 was extinct after four births and five deaths. All 28 daughters of intact transfers reached age death inside the observation window. [Every seed and state hash](natural/seeds.tsv) · [Aggregate denominators](natural/summary.tsv) · [All intact transfers](natural/links.tsv)

| Natural chain in seed 3562 | Birth of mother | Birth of westward daughter | Birth of grandchild | Lifetime births with ordinary reads, mother / daughter | Lifetime births with focal reads denied, mother / daughter |
| --- | ---: | ---: | ---: | ---: | ---: |
| First | 425 | 464 | 477 | 3 / 2 | 0 / 0 |
| Second | 519 | 558 | 571 | 3 / 2 | 0 / 0 |

In both cases the mother occupied site 17, her daughter site 16, and the grandchild site 31 across the torus boundary. The mothers copied live eastern individuals born at site 18 on ticks 386 and 480 respectively. The daughters read their own mothers on ticks 467–475 and 561–569. Each source identity was checked for all five copies. Of all 28 natural intact transfers, six daughters lay west, 14 north and eight south of their mother. Two of the six western daughters continued the live chain. These six daughters came from three seeds. [Copy provenance](natural/links.tsv) · [Every birth by those daughters](natural/descendants.tsv) · [Placement denominators](natural/placements.tsv) · [Lifetime permission forks](natural/lifetime-scores.tsv)

The existing behavioral screen yielded 104 candidate grandchild events in 47 seeds. Of these, 23 had a live first source at both generations and nine met the serial permission assay. All nine were in seed 3562. The behavioral criterion allows the focal's first donor to differ from the material copied into a later birth, giving it a broader event count. In the positive assay, successive actual products used five external reads and produced an intact reader at tick 13 in each of three fresh arenas. Focal denial reached an exact cycle at tick 4. The independent ancestor reproduced in all three generations under both permissions. The manipulation tests the reader's access to bytes. All source banks counted as live had an occupying CPU at each observed read. [Behavioral candidates](natural/pairs.tsv) · [Assay generations and controls](natural/generations.tsv)

### How long the natural family lasted

After identifying the positive seed we reconstructed the contiguous same-genome maternal family inside the original field horizon. The founding reader arose at tick 425 when a parent copying its own `RHCLD` produced `RSCLD`. The second chain's mother, born at tick 519, was herself an offspring of the first chain's daughter. At that intermediate birth all five reads came from the daughter's own reservation at the former maternal site. This makes the two positive chains related and explains how the exact genome persisted between them. The family had 13 members with a maximum depth of five parent-to-child steps. The longest uninterrupted path using living donors was two steps. Both qualifying grandchildren died without offspring. The last exact family member died at tick 749. The seed's population still contained 55 living individuals at tick 2,048. [Post hoc family reconstruction](natural/members.tsv) · [Family endpoints](natural/families.tsv)

## Matched daughter placement

In each of 64 independently seeded field backgrounds we introduced a reader and a compatible donor at adjacent free sites. For the mother's first reserve instruction, we set which of three free neighboring sites she tried first. Competition determined the winner. The donor occupied the eastern site. Each matched set used the same background snapshot and the same introduced individuals. We restored the mother's eastward bearing immediately after reserve. Every daughter executed with the normal eastward bearing throughout its lifetime. Count an assigned background as positive if the first link succeeded, its daughter made an intact reader birth from any single live reader, and separate focal read denials eliminated reproduction. [Assignment and transitions](protocol.md) · [Setup states](controlled/setups.tsv)

| Assigned daughter position | Backgrounds | First reservation won | Intact daughter from original donor | Daughter copied while mother lived | Daughter gave birth | Confirmed grandchild from live reader |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| West | 64 | 26 | 22 | 9 | 9 | 8 |
| North | 64 | 54 | 47 | 10 | 11 | 0 |
| South | 64 | 64 | 56 | 15 | 15 | 0 |

In all eight successes the daughter read all five bytes from her mother. In the ninth western case where copying began during the mother's lifetime, seed 636, the daughter read `RSCLD` and a substitution produced `CSCLD`. For each west–north and west–south comparison eight seed pairs favored west and zero favored the other direction. Among pairs where both placements produced an intact daughter, the corresponding discordances were 7/18 and 8/22. Changing the destination also changes the site's competitors, later allocation opportunities and site-specific mutation context. The result measures this full placement change in these backgrounds. All 509 follow-up branches met the final-80 reproduction criterion. [Paired seed counts](controlled/comparisons.tsv) · [Branch ledgers](controlled/branches.tsv) · [Individual copies](controlled/copies.tsv) · [Birth products](controlled/births.tsv)

## Replay

The protocol was committed in 536f8f7 before either experiment. The natural fields use the reference VM directly. The field observer and behavioral assays come from the earlier geometry and horizon studies. An independent reference executable checks every seed's population ledger, reader count and final state hash. The lifetime observer extends the geometry fork's input range to this seed cohort. Only the controlled placement runner links the build-directory header exposing the introduction and bearing operations. The VM step implementation is copied verbatim. The field-level permission forks run through age death and ordinary products inside the primary observation window must match the field record.

Run from the repository root with C++20, Make, patch and Python 3.10 or newer.

```sh
make -C kernel all test
make -C kernel/runs/vacancy-01 all
make -C kernel/runs/placement-01 all
study=kernel/runs/placement-01
bin=kernel/build/placement
obs=kernel/build/vacancy
out=kernel/build/placement/results
mkdir -p "$out/controlled"
"$bin/placement" "$out/controlled"
python3 -B "$study/compare.py" "$out/controlled"
"$bin/reference" > "$out/reference.tsv"
python3 -B "$study/natural.py" "$out/reference.tsv" "$obs" "$bin/lifetime" "$out/natural"
python3 -B "$study/witness.py" "$out/natural" "$obs/field"
for dir in controlled natural; do for f in "$study"/"$dir"/*.tsv; do cmp "$f" "$out/$dir/${f##*/}" || exit 1; done; done
shasum -a 256 -c "$study/revision.sha256"
```

The 19 result tables reproduced byte for byte in a separately optimized build with reversed field traversal. To repeat, rebuild the vacancy and placement tools with separate `BUILD` paths and `CXXFLAGS='-O3 -Wall -Wextra -Werror'`, use a fresh output directory, and append `--reverse` to the placement, natural audit and witness commands. Use the forward reference census for both checks. The standardized serial assays retain their original traversal. [Source and artifact checksums](revision.sha256)
