# dead-code-01 protocol

This protocol runs the agreed [research brief](../../../docs/research/dead-code-rq.md): does retaining the bytes of the dead, rather than clearing them, change a population's long-term evolutionary dynamics from the same ancestor? The brief fixes the cells, endpoints, hypotheses, interpretation rules and seed budget; it reuses the measurements and rules of the [access study](../access-dynamics-01/protocol.md). This file records how the code implements them and the clarifications the brief left to implementation.

The code was tested on validation seeds and then frozen, with the files listed in [revision.sha256](revision.sha256), before any study seed ran. `run.py` refuses to run a study set unless those files match their recorded digests and validation passed on exactly those digests.

## Configuration

| Item | Primary | Scale check | Validation |
| --- | --- | --- | --- |
| Cells | self-retain, read-retain, read-empty, read_fetch-retain, read_fetch-empty | read and read_fetch × retain and empty | the five primary cells and self-empty |
| Lattice | 32 × 32 torus | 64 × 64 torus | 32 × 32 torus |
| Founder | `R..CLD` at x = 8, y = 16, PC 0, bearing E | x = 16, y = 32 | x = 8, y = 16 |
| Seeds | 31001–31032 (block A 31001–31016, block B 31017–31032) | 31101–31108 | 29921–29924, plus one mutation-free self-retain world with seed 29921 |
| Horizon H | 2²² ticks | 2²¹ ticks | 2¹⁶ ticks; mutation-free world 2²⁰ |
| Filter t, timepoint step, last window level | 1,024, 256, 16,384 | 4,096, 1,024, 16,384 | as primary |
| Sensitivity filters | t = 256 and 2,048 | none | as primary |
| Bedau samples | every 4,096 ticks | every 4,096 ticks | every 4,096 ticks |
| Neutrality levels (M4) | 1,024, 3,072, …, 15,360 and 16,384 (9) | 4,096, 12,288 and 16,384 (3) | as primary |

Every world uses synchronous next-tick update, coordinate arbitration, first-free placement, age limit 80 and 20,000 ppm copy substitution, as in the access study. The arms set `Access` to self {false, false}, read {true, false} and read_fetch {true, true}. The cells set reclamation to `retain` (the contract default) or `empty`. The kernel is `kernel/src` as frozen here. It adds three analysis hooks to the reference VM, used only in forks: `World::replace_bytes` (knockouts and substitutions), `World::clear_residue` and `World::set_reclamation` (residue-cleared forks, `2c28805`).

```sh
make -C kernel/runs/dead-code-01          # builds kernel/build/dead-code/study
kernel/build/dead-code/study --controls   # classifier and residue controls
python3 kernel/runs/dead-code-01/run.py validate
python3 kernel/runs/dead-code-01/run.py primary --stop-after 6000
python3 kernel/runs/dead-code-01/run.py scale --stop-after 6000
python3 kernel/runs/dead-code-01/analyze.py primary
python3 kernel/runs/dead-code-01/analyze.py scale
```

One world is one call: `study --arm ARM --reclamation retain|empty --seed SEED --size W H --horizon H --filter T STEP END --sensitivity T1,T2 --out DIR`. `--bare` prints the final hash of the same world without the observer. `--shadow-perturb K` changes only the shadow's random key.

## Running order and archiving

1. Validation runs first and records the digests of the files it tested. If a check fails, the work stops and is reported.
2. After validation passes, `revision.sha256` is written from those digests and committed. This is the freeze.
3. The primary set runs next, then the scale check. Worlds are ordered by seed and then cell, in the order of the configuration table, and grouped into batches of 8. Each batch runs four worlds at a time.
4. After each batch, its raw tables and logs are committed and pushed to the working branch and to main. A world counts as complete when its directory exists; it is written to a temporary directory and renamed. A restarted run skips complete worlds and commits anything left uncommitted. With `--stop-after S`, no batch starts after S seconds, so that a run under a wall-clock limit ends between batches.
5. A world that fails any internal check stops its set after the batch is recorded. Failed worlds leave a `.failed.txt` record.
6. Analysis runs only after the primary set is complete. The interpretation rules are not changed after any study seed has run, whatever the results show.

Every world directory holds `world`, `timepoints`, `filtered`, `bedau`, `collapsed`, `assays`, `ledger`, `census` and `neutrality` tables (gzipped TSV), and `log.txt` with the command, kernel revision, exit status, final hash, wall time and peak memory.

## Observer

The observer is the access study's: byte provenance, material and executor parents, variation births, genealogies, the neutral shadow, MODES timepoints and Bedau activity are defined exactly as in its [protocol](../access-dynamics-01/protocol.md#observer). It reads the kernel's per-tick event list and never writes to the world. Every 4,096 ticks it checks the world's invariants and requires its mirror of every bank's bytes, occupancy, birth ticks, genotypes and reservation write counts to equal the world's. Any mismatch aborts the world.

**Mirror under empty reclamation.** When a death or a failed `D` releases a bank under `empty`, the mirror clears its bytes, and their suppliers stop being held. Under `retain`, released bytes keep their suppliers, as in the access study.

**Mechanism ledger.** A division attempt runs from a reservation to its birth, its release at `D`, or the actor's death. Fetched instructions count from the CPU's previous `D` or its birth, so that code executed abroad before the reservation belongs to the attempt. Each copied byte and each instruction fetched abroad is classified by its bank at the opening snapshot:

| Category | Bank |
| --- | --- |
| 0 | the actor's own body (bytes only) |
| 1 | a living neighbor |
| 2, 3 | the actor's own reservation, at a written or an unwritten offset |
| 4, 5 | another reservation, at a written or an unwritten offset |
| 6 | a free bank |

An offset of a reservation is written if it is below its owner's write count. **Residue** is a byte in category 3, 5 or 6 that has a supplier: bytes a lifetime once wrote that no living individual owns. Zero bytes created by a reservation have no supplier and are not residue.

The ledger sums, by actor genotype (`RCCCJD` or other), outcome (birth, failed division, death) and number of substituted copies in the attempt:

- attempts and bytes written;
- variation births and substitution-free variation births, as defined for the shadow;
- bytes and fetched instructions in each category;
- residue bytes and residue fetches;
- attempts with any residue byte, with any residue fetch, with any fetch abroad, and with any fetch from the actor's own reservation.

Under `empty`, a world aborts if any byte or fetch comes from a free bank or is residue.

**Lifetime tallies.** Every death in (0, H] is an age death. For each, the observer records whether the individual gave birth, and whether it was a substitution-bearing newborn, meaning at least one of the six copies that made it substituted a byte. The founder is not substitution-bearing.

**Event digest.** An FNV-style fold of every event's fields (tick, actor and its birth tick, effect, opcode, fetch site, PC, read site and offset, target, write offset, input, output, and product bytes). It shows whether two worlds' event streams are identical.

**Census.** At each material snapshot level (0, step, 2·step, …), at the snapshot tick, the observer counts:

- living, reserved and free banks, the free banks split by whether they hold bytes;
- `RCCCJD` carriers;
- for each carrier, the state of its bearing neighbor (living, reserved, free with bytes, free and empty);
- across carriers, the number of neighbors that are free banks with bytes, and the number that are `RCCCJD` carriers.

## Lifetime assays

Pass 2 replays the world without the observer and forks each first filtered carrier at its birth tick, as in the access study: ordinary, reads denied, fetch denied, both denied, and the six knockouts. Classes follow the access protocol. The ordinary count must equal the field's recorded births, or the world aborts.

**Residue-cleared fork.** At the carrier's birth tick, every free bank is emptied and every reservation's unwritten offsets are zeroed (`clear_residue`). Reclamation is then set to `empty` (`set_reclamation`) for the rest of the fork, and the focal keeps the cell's access. A genotype whose ordinary births are positive and whose residue-cleared births are zero is **residue-requiring**.

Code inspection predicts that the fork cannot change the focal's births in a self cell, where no other bank's bytes are visible, or in an empty cell, where no residue exists. A world aborts if it does.

The fork clears residue for every individual, not only the focal. A focal can therefore lose its births through a neighbor's changed behavior, for example through competition for space. Residue-requiring genotypes are reported in two groups:

- direct: the permission class shows neighbor access is required;
- indirect: the permission class is independent.

**Neutrality (M4).** A genotype is sampled if it is in F(A) at any neutrality level of the configuration table. Its first material carrier is forked once per single-substitution neighbor, the focal's bytes being replaced through `replace_bytes`. The neighbors are those the kernel's substitution can produce: at each site, every other byte of the 12-byte alphabet (11 per site, 66 in all; 12 at a zero byte). A neighbor is viable if the focal gives birth at least once before its age death in the fork.

Viability is counted in the ordinary environment and in the residue-cleared environment. Where no residue is visible (self or empty cells), the cleared count reuses the ordinary count.

## Endpoints

P1–P4 use the material genealogy at t = 1,024 over the 61 window levels from 1,024 to 16,384, exactly as in the [access protocol](../access-dynamics-01/protocol.md#endpoints), including the rules for extinction, unreached levels and missing values.

Mechanism endpoints, per world:

- **M1, rescue.** Of the substitution-bearing newborns that died in (0, H], the fraction that gave birth at least once.
- **M2, substitution-free variation.** Births with no substituted copy whose product genotype differs from the material parent's genotype, per 10⁶ births. The access study's variation-birth definition also counts misaligned copies that reproduce the parent's genotype; that count is reported descriptively.
- **M3, realized load.** Of all deaths in (0, H], the fraction without a birth.
- **M4, neutrality.** Of each sampled genotype, the fraction of its neighbors that are viable in the ordinary environment. At each neutrality level that was evaluated and has a non-empty F(A), the genotypes' fractions are averaged, weighted by passing individuals. M4 is the mean over those levels. M4-cleared is the same with residue-cleared viability.
- **M5, persistence.** For every genotype, each run of consecutive window levels at which it is in F(A) is counted. An unreached level ends a run. M5 is the mean run length over all runs in the world.
- **M6, dependent classes (descriptive).** Strategy establishment, loss and episodes follow the access protocol for each permission class. Residue-requiring genotypes are counted in total, direct and indirect.

## Tests

The statistical machinery is the access study's, unchanged: the exact Wilcoxon signed-rank test, Holm correction, the block rule, the bootstrap equivalence interval and the neutral expectation ([tests](../access-dynamics-01/protocol.md#tests)). The comparison is always retain minus empty within an access arm, and the reference cell for Glass's Δ and the equivalence bound is the empty cell.

- **Primary family.** D1 (read-retain vs read-empty) and D2 (read_fetch-retain vs read_fetch-empty) on P1–P4, with Holm correction over these 8 tests. The endpoint and claim outcomes, the 10% unreached rule and the neutral expectation are as in the access study.
- **Replication of C3.** read_fetch-retain vs self-retain on P1–P4, with Holm correction over its own 4 tests. It is reported separately and does not enter any D claim.
- **Mechanism family.** M1–M5 for D1 and D2, with Holm correction over these 10 tests, under rules 1–3. M5 is inconclusive if more than 10% of the living worlds in either cell are unreached.
- **Pattern rule.** Each access arm is classified as the brief specifies:
  - buffer-consistent: M1, M4 or M5 higher, or M3 or P2 lower, and none in the opposite direction;
  - raw-consistent: M2, P1, P2 or P4 higher, and none lower;
  - both, if both hold;
  - neither, if neither holds.

  "Differs" for P1, P2 and P4 is the primary-family outcome. The direction of a difference is the sign shared by the two blocks' median paired differences.
- **Descriptive contrasts, uncorrected.**
  - The D2 effect minus the D1 effect per seed, for P1–P4 and M1–M5: median and exact Wilcoxon p.
  - M4 minus M4-cleared in each retain cell with visible residue.
- **Sensitivity analyses and boundedness (descriptive).** As in the access study, for D1 and D2: the sensitivity analyses for t = 256, t = 2,048, executor parentage, informative sites and pooled P4 thresholds, and the boundedness fits per cell.
- **Scale check (descriptive).** The same endpoints are computed with t = 4,096 over levels 4,096 to 16,384 in steps of 1,024, with stagnation from level 12,288. No tests are run.

## Optional analyses (descriptive)

1. **`RCCCJD` stability.** Per world, the component's establishment and loss episodes in F(A), with the access study's rule: a loss is four consecutive absent levels, dated at the first of them. The census at each establishment and loss level gives:
   - the carrier count;
   - the share of carriers whose bearing neighbor is living, reserved, free with bytes, or free and empty;
   - residue neighbors and carrier neighbors per carrier.

   The ledger gives the share of `RCCCJD` births with a residue fetch or a fetch from the carrier's own reservation, and the split of their fetched instructions by category.
2. **Effective error rate.** Per cell:
   - the variation share, its substitution-bearing part and its substitution-free part, against the binomial 1 − (1 − 0.02)⁶;
   - the mean substitutions and the share of attempts with a substitution, for births, failed divisions and attempts ended by death;
   - for `RCCCJD`, the number of failed divisions with a substitution and a fetch from the carrier's own reservation.

   The last item checks the self-execution candidate of the brief.

## Validation checks

`run.py validate` records each check in `results/validation/checks.tsv`.

1. Each validation world's observed final hash equals its `--bare` hash.
2. Each world rerun with shadow key perturbation 1 keeps the run hash and changes its shadow columns, except in the mutation-free world.
3. Every assayed carrier's ordinary fork reproduced its recorded births. The binary aborts otherwise. The number of assayed carriers is recorded.
4. **Self null.** For each validation seed, self-retain and self-empty have:
   - equal event digests;
   - identical timepoint, filtered, Bedau, collapsed, assay, ledger and neutrality tables;
   - world tables identical except for the reclamation label, the final hash and timings;
   - census tables identical except for the counts of free banks with bytes.
5. **Empty cells.** No byte or fetch from a free bank and no residue in the ledger, and no free bank with bytes in the census.
6. **Residue-fork null.** In self and empty cells, every residue-cleared count equals the ordinary count. The number of changed counts in retain cells with visible residue is recorded.
7. **Mutation-free self-retain world**, run for 2²⁰ ticks:
   - D = 1 in every sample;
   - only `R..CLD` among filtered material and executor genotypes;
   - all 61 window levels evaluated;
   - zero change from level 1,280 on, zero ecology, and four informative sites for `R..CLD`;
   - `R..CLD` as the only genotype sampled for neutrality.
8. **Controls**, in the stage-1 fixture arenas of the access protocol:
   - `R..CLD`, `RSCLD` and `RJD` classify as independent, read-requiring and fetch-requiring, and none is residue-requiring, since their donors are alive throughout.
   - **Residue control.** This is the `residue_override` fixture of `kernel/tests/vm_tests.cpp`. `.RJD` at (1, 0), with donors `CCCCTP` parked at PC 5 at (2, 0) and (2, 1), fetch allowed and age limit 10, makes a daughter at (1, 1) at tick 9. Forked there, the daughter must make one ordinary birth by executing the retained body of its dead donor, classify as fetch-requiring, and be residue-requiring.

Validation outcomes are not examined beyond these checks.

## Disclosures before freezing

Before validation, the implementation was exercised in three ways:

- the controls and the kernel tests;
- seed 7 for 65,536 ticks in the five primary cells and self-empty, to check bare hashes, the self null and speed;
- seeds 1 and 2 with a short filter (t = 64) for 65,536 ticks in the five primary cells, to test pass 2, neutrality and `analyze.py`.

These runs showed world summaries: births, variation counts, deaths without birth, and counts of changed residue-cleared assays. In a read_fetch-retain world, the residue-cleared fork changed the births of four assayed carriers. One of them, an independent genotype without `J`, lost its only birth. That observation led to the direct and indirect split above. These runs are not records. No validation, primary or scale seed had run when this protocol was written.

Pass 1 measured about 93 µs per tick for a 32 × 32 world, single-threaded. A primary world is therefore expected to take about 7 minutes plus its assays, and the primary set about 5 hours on four cores.

## Clarifications of the brief

These choices were made during implementation; the brief does not fix them:

- the ledger categories, the attempt boundaries, and the definition of residue as supplied bytes;
- counting M1 and M3 over every death in (0, H];
- M2 as product genotype differing from the material parent's, with the access-style count reported alongside;
- the M4 neutrality levels (every eighth window timepoint from the first, plus the last), the weighting by passing individuals, and viability as at least one birth;
- the M5 treatment of unreached levels and window edges;
- the residue-fork null as an abort condition, and the direct and indirect split of residue-requiring genotypes;
- Holm correction over its own four tests for the C3 replication;
- the 10% unreached rule applied to M5;
- the direction of a difference taken from the block medians;
- the event digest and census fields.

`kernel/src/vm.cpp` and `vm.hpp` are also frozen by [access-dynamics-01](../access-dynamics-01/revision.sha256). Adding the residue hooks changed their digests, so that study's `run.py` refuses to run at later revisions. Its records replay from the revisions in their logs.
