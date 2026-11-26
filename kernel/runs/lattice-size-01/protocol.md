# lattice-size-01 protocol

This protocol runs the agreed [scale-control brief](../../../docs/research/lattice-size-rq.md). It asks whether the lattice side length alone changes whether the fetch-requiring genotype `RCCCJD` is established and persists. The brief fixes the cell, sizes, filters, endpoints, rules and seeds. This file records how the code implements them and the details the brief left to implementation.

The code was tested on validation seeds and then frozen before any study seed ran. The frozen files are listed in [revision.sha256](revision.sha256). `run.py` refuses to run the primary set unless those files match their recorded digests and validation passed on exactly those digests.

## Configuration

| Item | Primary | Validation |
| --- | --- | --- |
| Cell | read_fetch access, retain reclamation | as primary |
| Lattices | 24 × 24, 32 × 32, 48 × 48, 64 × 64 tori | the same four sizes |
| Founder | `R..CLD` at (⌊L/4⌋, ⌊L/2⌋), PC 0, bearing E: (6, 12), (8, 16), (12, 24), (16, 32) | as primary |
| Seeds | 32001–32032 at every size; block A 32001–32016, block B 32017–32032 | 29941–29944 at every size |
| Horizon H | 2²² ticks | 2¹⁶ ticks, with the exceptions listed under validation checks |
| Filters | t ∈ {576, 1,024, 2,304, 4,096} at every size; the primary filter of the series is t = N | the same divided by 16: {36, 64, 144, 256} |
| Grid | snapshots every 256 generations from 0 to 16,384; window 4,096–16,384 (49 timepoints) | every 16 generations to 1,024; window 256–1,024 |
| Extended grid (agreed item 13) | t = N, every 1,024 generations; window 17,408–65,536 (48 levels), used only if validation adopts it | t = N, every 64 generations to 4,096 |
| Bedau samples | every 4,096 ticks | every 4,096 ticks |

Every world uses synchronous next-tick update, coordinate arbitration, first-free placement, age limit 80 and 20,000 ppm copy substitution, as in the two earlier studies. The kernel is `kernel/src` as frozen for dead-code-01, unchanged. The study does not call the residue hooks.

```sh
make -C kernel/runs/lattice-size-01          # builds kernel/build/lattice-size/study
kernel/build/lattice-size/study --controls   # classifier, spatial and origin fixtures
python3 kernel/runs/lattice-size-01/run.py validate
python3 kernel/runs/lattice-size-01/run.py primary --deadline 6900 --first-batch 3600
python3 kernel/runs/lattice-size-01/analyze.py primary
```

A primary world is

```sh
kernel/build/lattice-size/study --size L L --filter tN 256 16384 --sensitivity <other three filters> \
  --horizon 4194304 --arm read_fetch --reclamation retain [--extend 1024 65536] --seed S --out DIR
```

## Running order and archiving

- **Batches.** Worlds run in 16 batches of 8, four at a time. Each batch holds two consecutive seeds at all four sizes. Within a batch the 64 × 64 worlds start first, then 48, 32 and 24, so that the four workers stay busy.
- **Archiving.** After each batch the outputs are gzip-compressed, committed and pushed to the working branch and to `main`.
- **Time limit.** Background commands here are limited to two hours. The driver therefore starts a batch only if the elapsed time plus 1.25 times the longest batch so far stays within `--deadline`, and a later call resumes at the next batch.
- **Failures.** A failed world stops the set. Its record is kept as `<world>.failed.txt`.
- **Logs.** Each world's `log.txt` records the command, revision, exit status, end hash, seconds and peak memory.

## Observer

The observer is the dead-code observer ([dead-code-01/study.cpp](../dead-code-01/study.cpp)) with these changes:

1. **Filter list.** The material series evaluates the four filters on one snapshot grid. The executor and shadow series use t = N only, as before.
2. **Targets.** Assay targets are the first filtered carriers of every genotype filtered at t = N, as before, plus the focus genotype `RCCCJD` at its first carrier found by any filter evaluation.
3. **Origins.** An origin is a birth of the focus genotype whose material parent is not the focus. Each world records the counts and the first origin: tick, site, executor site and genotype, parent genotype, and whether it was substituted.
4. **Spatial statistics (`spatial.tsv`).** At every main grid level, and at every extended level when that grid is on, the observer records:
   - cumulative births, focus births and origins;
   - living focus carriers;
   - 4-connected clusters on the torus, and the largest cluster;
   - ordered carrier–carrier neighbor pairs;
   - ρ(r) and ξ.

   ρ(r) is the axis-averaged normalized two-point correlation of the carrier indicator, for r = 1..L/2. ξ is the smallest r with ρ(r) < 1/e. It is censored at L/2, and set to −1 when no carrier, or only carriers, are present.
5. **Census and ledger.** Both are kept unchanged.
6. **Dropped.** The residue-cleared fork and the neutrality sample (M4) are dropped. The assay table has no residue columns.

With the dead-code settings, the observer reproduces dead-code-01's outputs byte for byte; validation check 3 tests this.

## Lifetime assays

Each target is forked at its birth and runs four lifetimes:

- ordinary;
- reads denied;
- fetch denied;
- both denied.

Six single-site knockouts to `.` run as well. Births are counted to age 80, as in the access study. The classes are those of the [access brief](../../../docs/research/access-dynamics-rq.md#strategy-classes). Every ordinary fork must reproduce the carrier's recorded births, or the world fails.

## Endpoints

All endpoints use the material genealogy and the 49 window timepoints. In unreached worlds they use the reached timepoints. In extinct worlds, timepoints after extinction count as absent.

- **E1_t.** `RCCCJD` is in F(A) at one or more window timepoints, for t = 1,024 and t = 4,096.
- **E2_t.** The fraction of window timepoints with `RCCCJD` in F(A), for the same two filters.
- **E3.** The fraction of window levels at which the census counts at least one living `RCCCJD` carrier.
- **Diagonal.** E1_tN and E2_tN take each world's own t = N.
- **Episodes.**
  - An episode starts at a present timepoint outside an episode.
  - It ends with a loss after 4 consecutive absent timepoints, which is 1,024 generations. The sensitivity rule uses 16 timepoints, 4,096 generations.
  - Its length is its last present level minus its first, plus 256.
  - Episodes are computed for every filter and for filter-free presence.
- **Origins per generation.** The origins between window levels 4,096 and 16,384, divided by 12,288. Origins per 10⁶ births in the same interval are also reported.
- **Spatial summaries,** per world over window levels with carriers:
  - median clusters;
  - median largest-cluster share;
  - mean join ratio, which is pairs per carrier divided by 4(k − 1)/(N − 1) for k carriers;
  - median ξ, over levels where it is defined.
- **Loss anatomy.**
  - A filter-free global loss is a window level with no carrier after a level with carriers. For each one, the number of clusters at the preceding level is recorded.
  - A cluster drop is a level where the number of clusters fell while carriers remained.
- **Ledger.** The fetch-source shares of focus births.
- **Continuity.** P1–P3 at t = N on the window, computed as in the access study, and P4 from the Bedau samples.
- **Classes.** Strategy-class establishment at t = N, and the class of `RCCCJD` in each world.
- **Extended window.** E1, E2 at t = N and filter-free presence on the extended levels. A world is unreached there if Ḡ at H is below 65,536 + t_N.

## Tests

These implement the brief's rules 1–8 in `analyze.py`.

1. **Primary family.** E1_1024, E1_4096, E2_1024, E2_4096 and E3.
   - For each, a two-sided permutation test of Spearman's ρ between L and the endpoint, over all worlds. Ties take average ranks.
   - 100,000 permutations of the size labels; p = (count + 1)/(100,000 + 1). The generator seed is 20261126 plus the endpoint's index.
   - Holm correction over the five tests.
   - Kruskal–Wallis H is reported with its χ² p for 3 degrees of freedom. It decides nothing.
2. **Differs.** Holm p < 0.05, and ρ has the same nonzero sign in block A, in block B and overall.
3. **Equivalent.** Compare the 64 × 64 and 24 × 24 means. The 90% percentile bootstrap interval of their difference must lie within ±0.5 pooled within-size SDs. The bootstrap uses 10,000 resamples of worlds within each size.
4. **Inconclusive.** Otherwise. Every endpoint is inconclusive if more than 10% of living worlds at any size are unreached (Ḡ < 20,480 at H).
5. **Attribution.**
   - Δ = mean E2(64, 4,096) − mean E2(32, 1,024).
   - The four parts S₁₀₂₄, S₄₀₉₆, F₃₂ and F₆₄ each get 90% bootstrap intervals, with resamples within size.
   - The outcome follows the brief's rule 5, using the outcomes of E2_1024, E2_4096 and E3.
6. **Neutral scaling.**
   - For E1 or E2, if either fixed filter differs, the same permutation test runs on the diagonal, uncorrected.
   - The direction is that of the first differing fixed filter.
7. **Patterns (descriptive).**
   - All three labels use filter-free episodes, since they concern the population and not the filter.
   - *Supply-like.* The least-squares slope of log mean origins per generation on log N, over sizes, has a 95% stratified bootstrap interval containing 1. In addition, the 95% bootstrap interval of ρ(L, longest filter-free episode) contains 0.
   - *Smooth.* That same interval lies above 0. In addition, at both primary filters, the rise in mean E2 from 24 to 64 is positive and no adjacent step carries more than half of it.
   - *Pattern-like.* The 95% bootstrap interval of ρ(L, world median ξ) contains 0, and the median ξ at 64 × 64 is below 16. In addition, at 24 × 24 there is at least one filter-free global loss, and more than half of those losses follow a level with one cluster.
8. **Classes.** Established counts per size, with Clopper–Pearson 95% intervals.

## Validation checks

Validation runs before any study seed and records `results/validation/checks.tsv`.

1. **Controls.**
   - The stage-1 fixed programs classify as independent, read-requiring and fetch-requiring.
   - Five 8 × 8 spatial fixtures give their known clusters, pairs, ρ and ξ. They are an empty lattice, a pair joined across the wrap plus a single, a full row, a checkerboard and stripes of width 2.
   - The origin rule gives 1 for a focus child of another parent, and 0 for a focus parent or for a child that is not the focus.
2. **Identity.** At every size, seeds 29941–29944 run for 2¹⁶ ticks with the scaled filters and the scaled extended grid. In each world:
   - the observed run's end hash equals a bare run's;
   - a perturbed shadow key keeps the run hash and changes the shadow;
   - every ordinary fork reproduces its births;
   - spatial carriers equal the census focus count at every level.
3. **Regression.** A 32 × 32 world with seed 31001 runs with the dead-code primary settings. It must reproduce dead-code-01's committed `read_fetch-retain-31001` byte for byte:
   - timepoints, filtered sets, Bedau samples, collapsed distributions, ledger and census;
   - its end hash, event digest, births, deaths, Ḡ and P4.
4. **Origin replay.** The bare kernel replays the regression world to its first recorded origin. The executor's bytes must match the recorded executor genotype, and the event must be a birth of `RCCCJD` at the recorded site. The recorded parent genotype must not be `RCCCJD`.
5. **Mutation-free world.** A 24 × 24 world with seed 29941 runs for 2²⁰ ticks without substitution, with the founder genotype as focus. It must show:
   - focus births equal to all births, and no origins;
   - one genotype in every filtered set, and D = 1;
   - complexity 4;
   - spatial carriers equal to the living count.
6. **Extended window (item 13).**
   - Seed 29941 runs to H at 24 × 24 and 32 × 32, with and without the extended grid. The four worlds run together, so each pair shares its load.
   - The extended runs must keep the end hash and differ only by the added rows.
   - The extended grid is adopted if the larger of the two time overheads is below 10%. The decision is written to `extended.tsv`, and the primary driver reads it.
7. **Analysis.** `analyze.py test` runs end to end on the 16 short worlds. This is a code test, and its outputs are not interpreted.

## Clarifications of the brief

These were settled in implementation, before freezing:

- **Pattern rules (7).** The brief did not say which episodes the pattern rules use. They use filter-free episodes, as stated under tests. "Episode length rises with L" means the 95% bootstrap interval of ρ lies above 0. "Most losses" means more than half.
- **Origin check.** The brief's "replayed birth" origin fixture is a bare-kernel replay of the regression world's first origin (check 4). The mutation-free world supplies the negative case with real births: faithful births from a focus parent never count (check 5).
- **Extended grid.** It has 48 levels, 17,408–65,536. Its unreached threshold is 65,536 + t_N, which equals the brief's 69,632 at 64 × 64.
- **Grid and window.** Snapshots start at level 0 so that P1–P3 can compute novelty against earlier sets, as in the earlier studies. The window starts at 4,096.
- **Item 13 timing.** The overhead is measured at 24 × 24 and 32 × 32 only. A 64 × 64 world to H takes about 50 minutes, longer than the whole rest of validation.

## Disclosures before freezing

- **Regression world run during development.** Before freezing, during development, the regression world (dead-code seed 31001 at its old settings) was run once as a code check. Its six tables and run identifiers equalled the committed dead-code outputs. Its first origin replayed with the bare kernel, and it took 349 s.
- **Debugging the analysis.** Short worlds on the validation seeds were generated outside the repository to debug `analyze.py`. Their outcomes were not examined beyond whether the script ran.
- **No study seed.** No study seed was run before freezing.
