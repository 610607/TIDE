# Fate of the eight prospective fetch families

All eight confirmed maternal same-genome families in the prospective cohort lost their last clonal member by tick 713. All seven surrounding field populations were still reproducing at tick 4,096. The field settings and mutations continued from their original deterministic trajectories. The complete state hashes and family counts at tick 512 matched the archived run for every seed. [Protocol](protocol.md) · [All field checkpoints](fields.tsv) · [Every family at each checkpoint](families.tsv)

Six families had already ended by tick 512. Of the two still present then, the seed 41 `RJCLH` family had its last birth at tick 491 and its last death at 572. The seed 36 `J.CLD` family continued to a total of nine clonal individuals and a maximum depth of seven, counting its founder. Its last birth occurred at tick 632 and its last death at tick 713. None of the eight had a living member at the 1,024, 2,048 or 4,096 checkpoints. [Clonal records](families.tsv)

In four of the seven worlds, the bytes of a previously confirmed family arose again after tick 512 from a different-genome parent outside that family. Across those four worlds there were seven such births and eleven subsequent or other same-genome births outside the tracked families. A later sequence match alone would therefore overstate survival of the original families. The tracking rule follows uninterrupted genomic identity. The fate of dependence across a mutation requires replaying the changed descendants. [Family and recurrence counts](families.tsv)

## Replay

Run from the repository root with a C++20 compiler and Python 3. The field runner emits physical births, deaths and canonical checkpoint hashes. The tracker follows actual individual identities and the parent recorded at each birth. The seed selection and family roots come from the [prospective study](../horizon-01/README.md).

```sh
shasum -a 256 -c kernel/runs/persistence-01/revision.sha256
mkdir -p kernel/build/persistence
c++ -std=c++20 -O2 -Ikernel/src kernel/src/vm.cpp kernel/runs/persistence-01/field.cpp -o kernel/build/field
python3 -B kernel/runs/persistence-01/track.py kernel/build/persistence
cmp kernel/build/persistence/fields.tsv kernel/runs/persistence-01/fields.tsv
cmp kernel/build/persistence/families.tsv kernel/runs/persistence-01/families.tsv
```

`members` and `max_depth` include the founder. `living` counts clonal members alive at the checkpoint. `extinction_tick` is the last clonal death. The two `other_identical` columns accumulate births outside the focal family since tick 512. The new-origin column requires different immediate parent bytes. Its count does not assume that the new lineage uses the same ecological strategy.
