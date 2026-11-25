# access-dynamics-01 protocol

This protocol runs the agreed [research brief](../../../docs/research/access-dynamics-rq.md): does the neighbor access permission change a population's long-term evolutionary dynamics from the same ancestor? The brief fixes the arms, measurements, windows, endpoints, interpretation rules and seed budget. This file records how the code implements them and the clarifications the brief left to implementation. It was frozen, with the files listed in [revision.sha256](revision.sha256), before any study seed ran. `run.py` refuses to run if any of those files differs from its recorded digest.

## Configuration

| Item | Primary | Scale check | Validation |
| --- | --- | --- | --- |
| Lattice | 32 × 32 torus | 64 × 64 torus | 32 × 32 torus |
| Founder | `R..CLD` at x = 8, y = 16, PC 0, bearing E | x = 16, y = 32 | x = 8, y = 16 |
| Seeds | 30001–30032 (block A 30001–30016, block B 30017–30032) | 30101–30108 | 29901–29904, plus one mutation-free self world with seed 29901 |
| Horizon H | 2²² ticks | 2²¹ ticks | 2¹⁶ ticks; mutation-free world 2²⁰ |
| Filter t, timepoint step, last window level | 1,024, 256, 16,384 | 4,096, 1,024, 16,384 | as primary |
| Sensitivity filters | t = 256 and 2,048 | none | as primary |
| Bedau samples | every 4,096 ticks | every 4,096 ticks | every 4,096 ticks |

Every world uses synchronous next-tick update, coordinate arbitration, first-free placement, age limit 80, 20,000 ppm copy substitution and retained bytes at death. The arms set `Access` to self {false, false}, read {true, false} and read_fetch {true, true}. The mutation-free world sets the substitution rate to 0 and is otherwise a validation self world. The kernel is `kernel/src` as frozen here; it adds only the analysis hook `World::replace_bytes` to the reference VM, used for knockouts in forks.

```sh
make -C kernel/runs/access-dynamics-01          # builds kernel/build/access-dynamics/study
kernel/build/access-dynamics/study --controls   # classifier controls
python3 kernel/runs/access-dynamics-01/run.py validate
python3 kernel/runs/access-dynamics-01/run.py primary
python3 kernel/runs/access-dynamics-01/run.py scale
python3 kernel/runs/access-dynamics-01/analyze.py primary
python3 kernel/runs/access-dynamics-01/analyze.py scale
```

One world is one call: `study --arm ARM --seed SEED --size W H --horizon H --filter T STEP END --sensitivity T1,T2 --out DIR`. `--bare` prints the final hash of the same world without the observer. `--shadow-perturb K` changes only the shadow's random key.

## Running order and archiving

1. Validation runs first. The study sets refuse to start unless `results/validation/checks.tsv` exists with no failed check. If a check fails, the work stops and is reported.
2. The primary set runs next, then the scale check. Worlds are ordered by seed and then arm (self, read, read_fetch) and grouped into batches of 8. Each batch runs four worlds at a time.
3. After each batch, its raw tables and logs are committed and pushed to the working branch and to main. A world counts as complete when its directory exists; it is written to a temporary directory and renamed. A restarted run skips complete worlds and commits anything left uncommitted.
4. A world that fails any internal check stops its set after the batch is recorded. Failed worlds leave a `.failed.txt` record.
5. Analysis runs only after the primary set is complete. The interpretation rules are not changed after any study seed has run, whatever the results show.

Every world directory holds `world`, `timepoints`, `filtered`, `bedau`, `collapsed` and `assays` tables (gzipped TSV) and `log.txt` with the command, kernel revision, exit status, final hash, wall time and peak memory.

## Observer

The observer reads the kernel's per-tick event list and never writes to the world. It keeps a mirror of every bank's bytes and, for each byte, the lifetime that supplied it. Every 4,096 ticks it checks the world's invariants and requires the mirror bytes, occupancy, birth ticks and genotypes to equal the world's. Any mismatch aborts the world.

**Byte provenance.** When a copy writes a byte, the byte's supplier is the lifetime recorded for the byte it read. A newborn's six bytes are then attributed to the newborn itself, so later readers of its body copy from it. Zero bytes created by a reservation have no supplier. Retained bytes of the dead keep their suppliers, so a dead lifetime can be a material parent.

**Material parent.** Among the suppliers of a child's six final input bytes, the one with most bytes is the parent. Bytes without a supplier cast no vote. A tie goes to the executor if it is among the tied suppliers, otherwise to the tied supplier of the lowest offset. If no input byte has a supplier, the executor is the parent. **Executor parent:** the dividing CPU's lifetime.

**Variation birth.** A birth is a variation birth if any of its six copies substituted a byte, or if its inputs were not an aligned copy: all six inputs from one lifetime L, each read from offset equal to its write offset, with the input string equal to L's genotype.

**Genealogies.** Material, executor and shadow genealogies are kept separately. A node is pruned once it is dead, has no retained children and supplies no stored byte or pending copy record. Depth is the parent's depth plus one; Ḡ is the mean depth of the living.

**Shadow.** The shadow's random key is derived from the seed and is independent of the kernel's draws. Within a tick, each run birth draws a shadow parent uniformly from the shadow individuals alive at the start of the tick. Each run death then draws a distinct victim from the same start-of-tick set. Newborns are added after both draws, and the victims are removed. A shadow child receives a new label exactly when its run birth is a variation birth; otherwise it inherits the parent's label. The shadow has the same population size as the run at every tick, and the observer checks this.

## MODES timepoints

For each genealogy and filter length, a snapshot of the living is taken at the first tick at which Ḡ reaches each level 0, step, 2·step, …, up to the last window level. The snapshot is evaluated at the first later tick at which Ḡ ≥ Ḡ(snapshot) + t. A snapshot individual passes if it is still recorded and is an ancestor of, or identical to, an individual alive at the evaluation tick. If the population goes extinct, every pending evaluation is made with no living individuals. Snapshots not evaluated by H are recorded as unreached. Levels never reached are absent.

For each passing genotype, the first filtered carrier is the passing individual of that genotype with the earliest birth tick and then the lowest site. It is taken at the first level at which the genotype passes, at any level from 0 to the last window level and at the primary t. Material and executor genealogies keep separate first carriers.

## Lifetime assays

Pass 2 replays the world without the observer to each first carrier's birth tick. It requires the carrier's site to hold an occupied bank with that birth tick and genotype. It forks the whole world there and changes only the focal's access, or one of its bytes. Each fork runs to the focal's age death at birth + 81 ticks and counts the focal's divisions.

- **Ordinary:** the arm's own access. Its count must equal the births the field recorded for that lifetime, or the world aborts.
- **Permission assays:** reads denied, fetch denied, and both denied. A denial the arm already imposes is not rerun and takes the matching count.
- **Knockouts:** the arm's access with byte i replaced by `.`. A site already holding `.` keeps the ordinary count. A site is informative if ordinary births are positive and the knockout births are fewer. Complexity at a timepoint is the largest number of informative sites in F(A), and 0 when F(A) is empty.
- **Classes** follow the brief's table. A combination not in the table, such as births with fetch denied but none with reads denied while both denied still reproduces, is reported as `other`. A carrier shared by both genealogies is assayed once.

## Bedau activity

A genotype's counter grows by one for every tick at which it is present at the end of the tick. Within a tick, births are applied before deaths. The founder is present from tick 0. A sample at tick s reports each present genotype's counter including tick s, together with D, A_cum, mean and median cumulative activity, and the same for shadow labels.

**Thresholds.** Activity values from all samples of the run and of the shadow are each collapsed and normalized to a frequency distribution over logarithmic bins of 8 per octave (bin = ⌊8 log₂ a⌋). a* is the smallest activity in the first bin at which the sign of the run-minus-shadow difference differs from its sign at the first bin where the two differ. a_max is the largest activity in any sample. a₀, a₁ = a* ∓ 0.05 (a_max − a*), and A_new is computed exactly from the sampled counters. A world whose distributions never cross has no threshold, and its P4 is missing. For the pooled sensitivity analysis, the observer also stores counts and A_new weights in bins of 64 per octave. Pooled thresholds sum those counts over all 96 primary worlds. Each world's P4 under pooled thresholds is then computed from the stored weights, prorated within a bin by the share of its integer activities inside [a₀, a₁]. This is an approximation; on short test worlds it stayed within 1% of the exact value.

## Endpoints

Endpoints use the material genealogy at t = 1,024 over the 61 window levels from 1,024 to 16,384.

- F(A) holds the genotypes with at least one passing individual. Change counts genotypes in F(A) absent from F at the previous level. Novelty counts genotypes in F(A) absent from every earlier level from 0. Ecology is the Shannon entropy, in bits, of passing individuals' genotype counts.
- P1 is total novelty over the reached window levels. P2 is mean change and P3 mean ecology over the same levels. P4 is the mean of A_new over the samples in (0, H].
- After extinction, levels score empty F(A). An extinct world is never unreached. A living world with any window level not evaluated by H is unreached and uses its reached levels. A world without a defined value has a missing endpoint, and its pair is dropped from that test.
- Demographic stagnation: alive at H with no birth in the final 80 ticks. Evolutionary stagnation: alive with zero novelty at every level from 12,288 to 16,384. A world that has not reached those levels is reported as unreached for this item.
- Strategy establishment, loss and episodes follow the brief over reached window levels. The class comes from the first material carrier's assay.

## Tests

Tests follow the brief's interpretation rules.

- **Wilcoxon test.** An exact two-sided signed-rank test on the paired differences of seeds with both values present. Zero differences are dropped. Tied absolute values receive average ranks. The p-value comes from the exact permutation distribution given those ranks.
- **Holm correction** across the 12 primary tests.
- **Differs.** The Holm-adjusted p is below 0.05, and the medians of the paired differences in blocks A and B have the same non-zero sign.
- **Equivalence.** A 90% percentile bootstrap interval of the mean paired difference lies within ±0.5 SD of the reference arm (sample SD over the paired seeds). The interval uses 10,000 resamples of seed pairs from Python's `random.Random(20261125)`.
- **Endpoint outcome.** "Differs" takes precedence over "equivalent". If more than 10% of the living worlds in either compared arm are unreached, P1–P3 for that comparison are inconclusive.
- **Claim outcome.** As in the brief.
- **Neutral expectation.** For an endpoint that differs, the run-minus-shadow values are compared between the same arms with the exact Wilcoxon test, uncorrected. The label is "beyond the neutral expectation" if p < 0.05 and the median paired difference has the same sign as the endpoint's; otherwise it is "matched by the shadow". Shadow endpoints use the shadow genealogy at t = 1,024 and the shadow's A_new under the run's thresholds.
- **Effect sizes and Kruskal–Wallis.** Effect sizes are the median paired difference and Glass's Δ: the mean paired difference divided by the reference arm's SD. Kruskal–Wallis uses tie-corrected H with a χ² p-value and is reported only.
- **Strategy counts.** Reported out of 32 with two-sided exact 95% Clopper–Pearson intervals, plus the one-sided 95% upper bound for zero counts.

**Sensitivity analyses (descriptive).** Each variant repeats the paired tests with Holm correction within the variant:

- P1–P3 with t = 256;
- P1–P3 with t = 2,048;
- P1–P3 with executor parentage;
- P1–P3 with informative-site components, where each genotype's non-informative sites are masked using its material assay;
- P4 with pooled thresholds.

Variant complexity is not recomputed for t = 256 or 2,048.

**Boundedness (descriptive).** Each arm's mean change, cumulative novelty, ecology and complexity over the window levels are fitted by least squares with four models:

- constant;
- linear;
- logarithmic in the level;
- saturating exponential, c + a(1 − exp(−(level − 1,024)/s)), with s from a 200-point logarithmic grid.

The model with the lowest AIC, n ln(RSS/n) + 2k, is reported. Each world's cumulative novelty is also fitted, and the number of worlds best fitted by each model is counted. Bedau class labels are not assigned, because the brief gives no operational rule for them.

**Scale check (descriptive).** The same endpoints are computed with t = 4,096 over levels 4,096 to 16,384 in steps of 1,024. Evolutionary stagnation uses levels from 12,288 (3t). No tests are run.

## Validation checks

Validation follows the brief's seed budget. `run.py validate` records each check in `results/validation/checks.tsv`.

1. Each validation world's observed final hash equals its `--bare` hash.
2. Each world rerun with shadow key perturbation 1 keeps the run hash. Its shadow columns change, except in the mutation-free world, whose shadow has a single label.
3. Every assayed carrier's ordinary fork reproduced its recorded births. The binary aborts otherwise, so each completed world passes. The number of assayed carriers is recorded. The same check runs in every study world.
4. The mutation-free self world must meet four conditions:
   - D = 1 in every sample;
   - only `R..CLD` among filtered material and executor genotypes;
   - all 61 window levels evaluated;
   - zero change from level 1,280 on, zero ecology, and four informative sites for `R..CLD`.

   Its horizon is 2²⁰ ticks, so that the whole window is reached.
5. Classifier controls use the stage-1 fixture arenas of `kernel/tests/vm_tests.cpp`: the default 5 × 5 bounded world, directed placement and no substitution. The age limit is set to 80 so that the assay ends.
   - `R..CLD` alone at (1, 1) with no neighbor access must be independent.
   - `RSCLD` at (1, 1), with donor `RSCLDP` parked at PC 5 east of it and reads allowed, must be read-requiring.
   - `RJD` at (0, 0), with donor `CCCTP` parked at PC 4 east of it and fetch allowed, must be fetch-requiring.

Validation outcomes are not examined beyond these checks.

## Disclosures before freezing

Before freezing, the implementation was exercised in four ways:

- the classifier controls;
- validation seed 29901 for 65,536 ticks in each arm, to measure speed and check the output format;
- the mutation-free world;
- seeds 1–6 with a short filter (t = 64) for 65,536 ticks, to test `analyze.py`.

The seed 29901 runs showed their world summaries. Those included population, births, mean generation intervals of about 42 ticks and final Ḡ of about 1,500. These runs are not records. No primary or scale seed ran before the freeze.

Pass 1 measured about 80 µs per tick for a 32 × 32 world. A primary world is therefore expected to take about 6 minutes, and the primary set about 2.5 hours on four cores.

## Clarifications of the brief

These choices were made during implementation; the brief does not fix them:

- the material-parent handling of unsupplied zero bytes and of births without any supplier;
- the logarithmic bins used to find a*;
- the `other` class;
- separate executor first carriers;
- the informative-site mask;
- the classifier controls' age limit and fixture arenas;
- the mutation-free horizon;
- the scale check's stagnation levels;
- dropping pairs with a missing endpoint;
- giving "differs" precedence over "equivalent".
