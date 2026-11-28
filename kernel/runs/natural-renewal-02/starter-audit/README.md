# Where the 31 starts stopped

This is a post hoc audit of the [fixed cohort](../findings.md), not a new sample. Recompiling the reference field at `-O3` and reversing traversal reproduced the six archived `-O2` forward tables in every one of the 53 batches (318 tables; nodes compared after decompression). Separately, [check.py](check.py) reads the sparse raw birth, permission and six-write records without using the original pedigree classifier to select starting copies or score their first renewal. It found the same 31 starts in 29 of 5,300 worlds and zero qualifying first renewals; therefore no repeated renewals. It uses the historical opening-state observer to trace each starting family in reverse traversal, verifying field hashes at tick 2048, at the observation horizon and at the end of the assay tail.

| Furthest stage reached after both originals died | Starting copies (exclusive) |
| --- | ---: |
| No second eligible descendant within the family window | 24 |
| Eligible relatives overlapped in time but not at adjacent sites | 4 |
| Eligible relatives were adjacent but neither copied the other during the overlap | 2 |
| A successor copied six aligned bytes unchanged from its living relative and divided; the child did not reproduce | 1 |
| Confirmed renewal | 0 |

These are descriptions of starting copies, not 31 independent observations: seeds 100798 and 102482 each contributed two. Eligibility requires confirmed same-program descent; lack of a second *eligible* descendant does not mean the executor had no other descendants. The stage counts do not estimate the effect of adding a partner, relaxing eligibility, or extending lifetimes. [Family ledger](results/families.tsv) · [Directed overlaps](results/pairs.tsv) · [Births executed by starter children](results/products.tsv)

**Why a birth was not scored as a renewal.** In seed 104218 the last original participant died at tick 7541. Executor 4674 copied offsets 0–5 of living relative 4689 at ticks 7578–7588. Offspring 4704 was born at tick 7590 with the exact program `R+SCLD` and zero substitutions. It produced zero offspring in its ordinary lifetime. Consequently there was no denial assay for it (`denied_births = -1`), and its read dependence could not be confirmed. This was a completed post-turnover birth, **not** a failure to divide. The frozen endpoint also requires a confirmed child; it correctly remained zero. [Tick trace](results/ticks.tsv) · [Child and permission records](../results/primary/batch-043/nodes.tsv.gz)

**Interpretation.** The largest observed loss in this cohort precedes the existence of a second confirmed same-program successor. If asking why these relationships fail, trace how births acquire or lose that eligibility before treating lack of space or failed division as the general explanation.

From the repository root (C++20, Python 3.10+; use an empty output directory):

```sh
d=kernel/runs/natural-renewal-02/starter-audit
python3 -B "$d/replay_all.py"
out=$(mktemp -d)
python3 -B "$d/check.py" "$out"
diff -qr "$d/results" "$out"
```
