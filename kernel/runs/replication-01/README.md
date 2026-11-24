# Independent replication on seeds 9 through 32

Zero of 24 new fetch seeds and zero of 24 new read seeds met the frozen heritable-dependence criterion. All 72 runs ended with living populations that had reproduced within the final 80 ticks. The discovery case still replays exactly from seed 8. Under this budget, the independent set yielded no second confirmed lineage. [Frozen protocol](protocol.md) · [All seeds](seeds.tsv) · [Every candidate birth](links.tsv) · [Discovery case](../pilot-01/README.md)

| Channels | Seeds | Field births | Births after contact | Candidate births | Seeds with candidates | Confirmed seeds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Self only | 24 | 7,345 | 0 | 0 | 0 | 0 |
| Neighbor data only | 24 | 7,362 | 16 | 0 | 0 | 0 |
| Neighbor fetch only | 24 | 7,326 | 69 | 35 | 11 | 0 |

The fetch screen produced 35 grandchild events. For 18 events at least one field CPU first contacted a free or reserved bank, outside the live-donor assay. Of the 17 with two live first contacts, 16 produced three generations from both field genotypes when fetch was enabled and zero generations within the horizon when it was disabled. The complete arena had not repeated within 64 ticks in the disabled branch, leaving those failures inconclusive under the protocol. In the remaining event the child's genotype also failed to reproduce with fetch enabled. The live-donor and cycle conditions therefore affect how much of the sample can be classified. Multiple events may belong to the same field family. [Paired observations](links.tsv)

A subsequent [horizon study](../horizon-01/README.md) preserved these original classifications, measured the first full-arena repeats and tested the extended assay on a new prospective cohort.

## Replay

VM, assay, field settings and site initializations are identical to the discovery run. The seed interval was fixed in advance of this batch. The frozen hashes cover the VM, assay sources and original protocol. The full build source and run records are pinned in the checksum manifests. [Source and build instructions](../pilot-01/README.md#replay)

```sh
shasum -a 256 -c kernel/runs/replication-01/frozen.sha256
shasum -a 256 -c kernel/runs/replication-01/revision.sha256
make -C kernel all test
kernel/build/tide batch 9 32 kernel/build/replication-links.tsv > kernel/build/replication-seeds.tsv
cmp kernel/runs/replication-01/seeds.tsv kernel/build/replication-seeds.tsv
cmp kernel/runs/replication-01/links.tsv kernel/build/replication-links.tsv
```
