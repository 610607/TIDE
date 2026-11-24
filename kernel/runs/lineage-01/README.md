# Can a reader daughter reach a living copy of its own program?

An audit of every birth in the 2,560 previously sampled fields found two intact transfers from a single live reader. Both belonged to one mother in seed 2437. Neither daughter continued that chain in the untreated field. In a fork of the older daughter's second allocation, directing its read pointer to its still-living mother produced an exact reader grandchild at the original division tick. The new observation is the effect of this address change in one family. The field incidence comes from the two archived cohorts. [Protocol](protocol.md) · [Every qualifying live transfer](live-links.tsv) · [All direction forks](forks.tsv)

## All-birth audit

The previous census selected opportunities before a reader's first copy attempt. This audit revisited all births through tick 2,048, including later allocations by the same individual. An intact link required a reader CPU to copy five reader bytes unchanged from a single occupied external reader, identified by site and birth tick. For the wider behavioral endpoint, all genotypes qualified for screening. The existing live-donor assay tested mother and daughter separately in their own first-contact backgrounds. [Previous study](../vacancy-01/README.md) · [Behavioral criterion](../horizon-01/protocol.md)

| Cohort | Fields | All births | Births by readers | Intact live links | Longest live chain | Behavioral candidate events | Both first donors live | Confirmed pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Seeds 577–1088 | 512 | 663,119 | 1,197 | 0 | 0 | 2 | 0 | 0 |
| Seeds 1089–3136 | 2,048 | 2,650,078 | 4,617 | 2 | 1 | 8 | 1 | 0 |

All fields reproduced during the final 80 ticks. Both qualifying daughters reached age death before the census cutoff. The ten behavioral candidates arose in five seeds. Nine had a reserved bank as the first source in at least one generation. In the one eligible pair, the daughter produced the independent program on its first assay birth. Subsequent assay generations reproduced without using external reads. [All seeds and terminal hashes](seeds.tsv) · [All behavioral pairs](pairs.tsv) · [Per-generation assays and controls](generations.tsv)

## Four independent forks of one actual family

Seed 2437's reader at site 20 lived through the opening of its death tick, 1744. Its older daughter was born north of it, the younger daughter south. Both read east in the untreated field. Each fork started immediately before the first copy of an already reserved allocation. We ran ordinary access, a single change of read address to site 20, and that same address change with the daughter's external reads denied. Each row below starts from its own ordinary field history. [Ordinary copy windows](daughter-windows.tsv) · [Input and product bytes, source identities and hashes](forks.tsv)

| Daughter and allocation | Division tick | Ordinary product | Maternal-site product | Bytes from the living mother | Explanation |
| --- | ---: | --- | --- | ---: | --- |
| Older, first | 1718 | `R.CJD` | `RSCJD` | 5 | The original copy substitution changed `L` to `J` on both branches. |
| Older, second | 1741 | `R.CJD` | `RSCLD` | 5 | All five reads occurred before maternal death and the product retained them. |
| Younger, first | 1754 | `R.CLD` | `RSCLD` | 1 | The first read coincided with maternal death. Four reads took bytes from a later reservation. |
| Older, third | 1757 | `R.CJD` | `RSCLD` | 0 | The daughter copied retained bytes from its own reservation at its mother's former site. |

All four denied branches reached focal death without a birth. A matching product arose three times after the address change. Only the older daughter's second allocation yielded a complete live-maternal transfer. Together with that daughter's natural origin, this gives a two-link pedigree with one intervened link. The forks ended at birth or focal death. Persistence of the resulting grandchild was outside this test.

## Next experiment

Test whether normal eastward reading supports the same second transfer when daughter placement puts its mother to the east. In matched backgrounds from distinct seeds, register the daughters before looking at offspring and record placement, maternal lifetime over each copy, source identity, substitutions and births. Count independent seed backgrounds separately from sister forks. Use ordinary placement and reading for field incidence. Intervened starting backgrounds can test the mechanism. A later fixed-budget, disjoint field cohort can test for an untreated mother–daughter–grandchild chain and apply the established permission assay to both generations. A zero is reportable at the declared cutoff.

## Replay

Run from the repository root with C++20, Python 3.10 or newer, Make and patch. The observer builds from the reference VM. For the direction forks a build-directory header exposes a single assignment to the focal read address. The source VM's step implementation is copied verbatim. The ordinary forks check every focal birth tick, target and product against the archived reference events.

```sh
make -C kernel all test
make -C kernel/runs/vacancy-01 all
make -C kernel/runs/lineage-01
study=kernel/runs/lineage-01
out=kernel/build/lineage/results
python3 -B "$study/audit.py" "$out" kernel/build/vacancy
kernel/build/lineage/direction "$out/daughter-windows.tsv" > "$out/forks.tsv"
for file in "$study"/*.tsv; do cmp "$file" "$out/${file##*/}" || exit 1; done
shasum -a 256 -c "$study/revision.sha256"
```

All six output tables also matched under field traversal reversal with `-O3`. To repeat that comparison, build the vacancy tools and the direction runner in separate build directories using `BUILD=../../build/vacancy-replay` and `BUILD=../../build/lineage-replay`, respectively, with `CXXFLAGS='-O3 -Wall -Wextra -Werror'`. Pass the new binary directory to the audit, use the new direction runner and add `--reverse` to both commands. The standardized serial assays keep their original traversal. [Study inputs and artifact checksums](revision.sha256)
