# Does lattice size alone change whether the fetch-requiring genotype persists?

**Scale control, agreed 2026-11-26.** This brief sets out a scale control after the [access](access-dynamics-rq.md) and [dead-code](dead-code-rq.md) studies. Every decision at the end was settled as recommended ([agreed choices](#agreed-choices)). The run protocol and records are in [lattice-size-01](../../kernel/runs/lattice-size-01/README.md).

**Question.** Start from the same `R..CLD` founder, with neighbor reads plus instruction fetch and retained dead code. Does the side length L of the torus, changed alone, change whether the fetch-requiring genotype `RCCCJD` is established and how long it persists? Filter lengths, timepoints, loss rule, tick horizon, mutation rate, seed list and every kernel rule stay the same at every size.

## Why this control

`RCCCJD` behaved differently at the two sizes tested. The sources for each row are the [access results](../../kernel/runs/access-dynamics-01/README.md) and the [dead-code results](../../kernel/runs/dead-code-01/README.md).

| Set | Worlds | Established | Fraction of window timepoints in F(A) | Present at the last timepoint |
| --- | ---: | ---: | ---: | ---: |
| Access study, read_fetch, 32 × 32 | 32 | 17 | 3.1% | 0 |
| Dead-code study, read_fetch-retain, 32 × 32 | 32 | 21 | 3.4% | 0 |
| Access study, read_fetch, 64 × 64 | 8 | 8 | 49% | 4 |
| Dead-code study, read_fetch-retain, 64 × 64 | 8 | 8 | 47% | 3 |

The 64 × 64 sets were descriptive checks. They changed several settings with the size, and the dead-code record says so: they "cannot attribute differences from the primary set to population size alone".

| Setting | 32 × 32 primary | 64 × 64 check |
| --- | --- | --- |
| Horizon H | 2²² ticks | 2²¹ ticks |
| Filter length t | 1,024 generations (= N) | 4,096 (= N) |
| Timepoint step | 256 generations | 1,024 |
| Window, Ḡ | 1,024–16,384, 61 timepoints | 4,096–16,384, 13 timepoints |
| Loss rule, 4 consecutive absent timepoints | 1,024 generations | 4,096 generations |
| Sensitivity filters | 256 and 2,048 | none |
| Seeds | 30001–30032, 31001–31032 | 30101–30108, 31101–31108 |

The question is whether the difference comes from the world size or from these measurement settings.

## What the existing records already show

**Horizon (code inspection).** Replay is deterministic, and the observer does not change state, so a world run to 2²² ticks passes through the same states as one run to 2²¹. Both windows need Ḡ up to 16,384 + t ≤ 20,480. At about 41 ticks per generation that happens near tick 850,000, well before either horizon. The horizon therefore cannot affect any `RCCCJD` endpoint.

**Direction of the filter (code inspection).** `Series::evaluate` in [dead-code-01/study.cpp](../../kernel/runs/dead-code-01/study.cpp) passes a genotype at timepoint A if a carrier alive at A is still alive, or has a living descendant, when Ḡ first reaches A + t. Suppose every parent is alive at its child's birth. Then any line of descent that reaches a later time is unbroken at every earlier time, and a longer filter can only remove genotypes. The exception is a birth copied from a dead body, which retained bytes allow. Apart from such births, raising t from 1,024 to 4,096 can only lower the measured persistence at 32 × 32. The filter change moves the 32 × 32 result away from the 64 × 64 result, not towards it.

**Re-analysis of committed 32 × 32 outputs (descriptive, no new run).** `RCCCJD` in the material-parent filtered sets, placed on other grids:

| Set | t | Grid, Ḡ | Established | Mean fraction |
| --- | ---: | --- | ---: | ---: |
| Access, read_fetch | 1,024 | 4,096–16,384, step 256 | 12/32 | 0.024 |
| Access, read_fetch | 2,048 | 4,096–16,384, step 256 | 10/32 | 0.022 |
| Access, read_fetch | 2,048 | 4,096–16,384, step 1,024 (the 64 × 64 grid) | 8/32 | 0.019 |
| Dead-code, read_fetch-retain | 1,024 | 4,096–16,384, step 256 | 14/32 | 0.020 |
| Dead-code, read_fetch-retain | 2,048 | 4,096–16,384, step 256 | 14/32 | 0.020 |
| Dead-code, read_fetch-retain | 2,048 | 4,096–16,384, step 1,024 (the 64 × 64 grid) | 6/32 | 0.014 |

The 32 × 32 runs did not compute t = 4,096. By the inclusion above, its values would be at most the t = 2,048 values, apart from dead-body births. On the 64 × 64 grid, 32 × 32 therefore stays near 2% while 64 × 64 reached 47–49%.

**Filter-free census (descriptive, no new run).** The dead-code observer counted living `RCCCJD` carriers at every grid level, with no filter. Over Ḡ 4,096–16,384 in read_fetch-retain:

| Size | Worlds | Fraction of levels with a carrier | Median carriers when present | Median share of the living | Mean `RCCCJD` neighbors per carrier, of 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 32 × 32 | 32 | 0.18 | 46 | 5.5% | 2.1 |
| 64 × 64 | 8 | 0.97 | 1,125 | 33% | 2.7 |

These counts do not depend on t. The difference lies in the population, not only in the filter. Carriers were strongly clustered at both sizes; randomly placed carriers at a 5.5% share would have about 0.2 `RCCCJD` neighbors each.

**What remains open.** These records make a filter explanation unlikely, but they are not a size-only comparison. The 64 × 64 sets had 8 worlds each, used other seeds and timepoints, and carried no preregistered test. They also cannot show the shape of the size dependence or which property of size matters.

## What the literature says about size

**A correction to the framing.** The request cites Boerlijst and Hogeweg 1991 for the idea that a large enough space sustains parasitic replicators. The paper does not state that. It shows that spiral waves make a hypercycle resistant to parasites, which grow towards the periphery of a spiral and are wiped out (pp. 20–21). The paper used one field, 300 × 300 (p. 18). It discusses space only in relation to the spirals. With more diffusion, spirals grow "bigger and bigger (if the space is large enough)", and higher rates were not studied because "the spirals become too big for our cellular automaton" (p. 24).

The paper's one case of a persistent parasite is a cyst at the centre of a single spiral (plate 5, p. 21). The cyst persists because "the remaining spirals constantly induce the reformation of the 'killed' single spiral" (p. 24). That mechanism needs room for several spirals, so a size dependence is a reasonable inference from the paper. It is not a result of the paper.

### Closest precedents

| Source | What it shows | Use here |
| --- | --- | --- |
| Boerlijst and Hogeweg 1991 (published article). [Cached PDF](../references/pdf/boerlijst-hogeweg-1991-spiral-wave.pdf) | Spirals suppress parasites (pp. 20–21). A cyst persists through reinforcement by other spirals (p. 24). Spirals need space to grow (p. 24). The result was robust to asynchronous updating and a non-toroidal field, and needs at least five hypercycle members (p. 25). | Source of the spatial-pattern hypothesis A2, read as an inference. TIDE has no hypercycle, so only the general claim that a spatial pattern needs room transfers. |
| Takeuchi and Hogeweg 2009 (published article). [Cached PDF](../references/pdf/takeuchi-hogeweg-2009-multilevel-selection-ii.pdf) | On a surface, replicases and parasites form traveling waves. A single wave's lifetime is limited mainly by "collision with other waves or boundaries", so an isolated wave can persist far longer (p. 9). | A2 prediction: losses on small tori, where structures meet sooner. |
| Colizzi and Hogeweg 2016 (published article). [Cached PDF](../references/pdf/colizzi-hogeweg-2016-parasites-spatial-self-organisation.pdf) | Local accumulation of parasites leads to their own local extinction, which frees space for replicators (PDF p. 1). Mixing, or a large increase in diffusion, leads to global extinction (PDF p. 3). | A2 prediction: in large worlds, local losses without global loss. Also shows why a mixing manipulation is the causal test. |
| Ovaskainen and Meerson 2010 (preprint of a review). [Cached PDF](../references/pdf/ovaskainen-meerson-2010-stochastic-extinction-v1.pdf) | Demographic stochasticity makes the mean time to extinction grow exponentially with population size (PDF p. 2), MTE ∝ exp(cK) with carrying capacity K (Leigh, Lande; PDF p. 4). In the threshold case it scales as √K (PDF p. 12). | Source of the finite-population hypothesis A1b: smooth growth of persistence with carrier number, with no characteristic length. |
| Dolson et al. 2019, MODES (published article). [Cached PDF](../references/pdf/dolson-et-al-2019-modes-toolbox.pdf) | Median neutral coalescence takes 2N generations, and "one should strive to use consistent values of t relative to population size" (p. 8). The paper crossed population sizes 500, 1,000 and 2,000 with t = 500, 1,000 and 2,000, plus N = 2,000 with t = 4,000 (p. 13). t = N "seems to yield an adequate filter" (p. 15). | Basis for crossing size with filter length, and for reading a fixed-t effect against the neutral scaling of the filter. |

"Parasite" is an analysis label only, as AGENTS.md requires. `RCCCJD` is fetch-requiring by permission assay. In the dead-code ledger it fetched 46% of its instructions from living neighbors and 50% from written offsets of its own reservation, so it is partly self-executing.

## Hypotheses, stated as outcome patterns

These patterns can co-occur, and none is assumed.

- **A0, measurement.** The earlier gap came from filter length, timepoints or loss rule. Prediction: at a fixed filter, establishment and persistence do not change with L. The code inspection and re-analysis above already count against A0.
- **A1a, mutational supply.** Larger worlds produce `RCCCJD` more often. Prediction: new origins of `RCCCJD` per generation grow about in proportion to N, while each episode lasts no longer.
- **A1b, finite population.** A larger carrier population is lost less often by chance. Prediction: episodes lengthen smoothly with carrier number, with no threshold and no length scale independent of L.
- **A2, spatial pattern.** `RCCCJD` persists as clusters with a characteristic size ξ that does not depend on L. Predictions: ξ is about the same at every size; persistence rises steeply once L/ξ is large enough for several clusters; on small tori the last cluster's collapse precedes a global loss; in large worlds clusters vanish locally while the genotype stays.

A size series changes N and L together, so it cannot separate A1b from A2 causally. The spatial endpoints describe which pattern the data resemble. A causal test of A2 would change spatial structure at a fixed N, which is a separate later experiment.

## Design

### Arm and fixed rules

- **Arm.** read_fetch access with retained dead code: neighbor reads plus instruction fetch, retain reclamation. This cell exists in both earlier studies, so the 32 × 32 set replicates it on new seeds.
- **Fixed at every size:**
  - H = 2²² ticks;
  - 20,000 ppm copy substitution;
  - age limit 80;
  - first-free placement;
  - torus;
  - next-tick newborns and coordinate arbitration, as in the v1 contract;
  - founder `R..CLD` at (⌊L/4⌋, ⌊L/2⌋), the same relative position as before;
  - material-parent genealogy for the filter.
- **Kernel.** Unchanged. `kernel/src/vm.cpp` and `vm.hpp` keep their frozen digests.

### Manipulation: the sizes

| Option | Sizes L | N = L² |
| --- | --- | --- |
| A, as requested | 32, 48, 64 | 1,024, 2,304, 4,096 |
| B, agreed | 24, 32, 48, 64 | 576, 1,024, 2,304, 4,096 |
| C | 24, 32, 40, 48, 64 | 576, 1,024, 1,600, 2,304, 4,096 |

**Reasons for option B, the agreed choice:**

- 24 × 24 tests whether 32 × 32 is already at a floor. A floor at 24 and 32 followed by a rise points to a threshold (A2). A continued decline points to smooth scaling (A1b).
- It adds about 2 CPU-hours.
- Every size is even, like 32 and 64, so any period-2 spatial pattern under synchronous update fits the torus in both directions. This is a precaution, not a known effect.

### Measurement held fixed across sizes

The table lists every change from the earlier studies, with the reason for each.

| Item | Here | Earlier | Reason |
| --- | --- | --- | --- |
| Timepoints | Ḡ = 4,096, 4,352, …, 16,384 at every size: 49 timepoints, step 256 | 32 × 32: from 1,024, step 256. 64 × 64: from 4,096, step 1,024 | One grid for every size and filter. It starts at the longest filter, as the access study started its window at t. The step keeps the finer 32 × 32 resolution, which short episodes at small L need. |
| Filter lengths | t ∈ {576, 1,024, 2,304, 4,096} computed at every size, from the same runs | One t per size, plus sensitivity filters at 32 × 32 | Follows the MODES crossing of size and t (p. 13). Fixed-t rows are the requested control. The t = N diagonal is the MODES convention (pp. 8, 15) and reproduces each earlier setting. |
| Primary filters | t = 1,024 and t = 4,096 | — | The two values used before. |
| Loss rule | 1,024 generations absent (4 timepoints) at every size and filter. Sensitivity: 4,096 generations (16 timepoints). | Four timepoints, which was t generations | Fixed in generations so that it no longer changes with the filter. |
| Filter-free census | Carriers, share and spatial statistics at every grid level | Carriers and `RCCCJD` neighbors, in dead-code-01 only | A t-independent endpoint (E3). |
| Seeds | The same 32 seeds at every size | Different blocks per size | Same seed scheme, as requested. |

### Primary endpoints, per world

- **E1, establishment.** `RCCCJD` is in F(A) at one or more window timepoints.
- **E2, persistence.** The fraction of the 49 window timepoints at which `RCCCJD` is in F(A).
- E1 and E2 are each computed at t = 1,024 and at t = 4,096, which gives four endpoints.
- **E3, filter-free presence.** The fraction of the 49 grid levels with at least one living `RCCCJD` carrier.

`RCCCJD` is a genotype, so these endpoints need no permission assay. Its class is assayed once per world at its first filtered carrier.

### Secondary endpoints (descriptive)

- **Episodes.** Under both loss rules and every filter: number of establishment episodes, losses, longest episode in generations, first establishment generation, and presence at the last window timepoint.
- **Strategy classes.** Establishment and timepoint fraction for every dependent class. Class assays are run only for genotypes in F(A) at t = N, as before, plus `RCCCJD`. Shorter filters at 64 × 64 would pass many more genotypes, and each needs ten forks.
- **Origins (A1a).** Births of `RCCCJD` whose material parent is not `RCCCJD`, per generation and per 10⁶ births.
- **Carriers (A1b).** Count and share of the living at each grid level.
- **Spatial pattern (A2),** at each grid level:
  - number of 4-connected `RCCCJD` clusters on the torus, and the largest cluster's share;
  - mean `RCCCJD` neighbors per carrier, and its ratio to the expectation under random placement at the same count;
  - the axis-averaged two-point correlation C(r) of the carrier indicator for r ≤ L/2;
  - ξ, the smallest r at which the normalized C(r) falls below 1/e, censored at L/2.
- **Loss anatomy.** The cluster count at the last level before each filter-free global loss. Also, the number of levels at which the cluster count fell while carriers remained.
- **Fetch sources.** The dead-code ledger for `RCCCJD` births: living neighbors, own reservation, other reservations and free banks.
- **Other.** P1–P4, the neutral shadow and Bedau statistics, for continuity with the earlier studies.
- **Extended descriptive window.** The same `RCCCJD` endpoints at t = N on Ḡ 17,408–65,536, step 1,024, if validation shows it costs under 10% more time. It needs Ḡ ≥ 69,632 by H, which holds at up to 60 ticks per generation. At 64 × 64 the genotype was still present at the last timepoint in 3–4 of 8 worlds. A longer window shows whether such presence lasts (A2) or ends in a later loss (A1b).

### Interpretation rules

These rules are fixed before any study seed runs.

1. **Tests.** For each of the five primary endpoints, a two-sided permutation test of Spearman's ρ between L and the endpoint across all worlds, using 100,000 permutations of size labels and a fixed generator seed. The p-values are Holm-corrected over the five tests at family-wise 0.05.
   - Worlds at different sizes are not paired (see Seeds), so the access study's signed-rank test does not apply.
   - Spearman's ρ tests a monotone association without assuming the shape that separates A1b from A2.
   - Each size's median or proportion is reported with a 95% interval: exact for E1, bootstrap for E2 and E3.
   - Kruskal–Wallis across sizes is reported for comparability with MODES. It does not decide anything.
2. **Differs.** An endpoint differs with size if its Holm-adjusted p < 0.05 and ρ has the same sign in both seed blocks.
3. **Equivalent.** An endpoint is equivalent across sizes if a 90% bootstrap interval of the largest-minus-smallest-size difference lies within ±0.5 pooled within-size SDs. The interval uses 10,000 resamples of worlds within each size and a fixed generator seed.
4. **Otherwise inconclusive.** A failed validation check also makes the affected endpoint inconclusive. So does a size where more than 10% of living worlds are unreached, meaning Ḡ < 20,480 at H.
5. **Attribution.** Let Δ = E2(64, t = 4,096) − E2(32, t = 1,024), the earlier contrast. Δ splits two ways:
   - Δ = S₄₀₉₆ + F₃₂ = S₁₀₂₄ + F₆₄;
   - here S_t = E2(64, t) − E2(32, t) is the size part at fixed t, and F_L = E2(L, 4,096) − E2(L, 1,024) is the filter part at fixed L;
   - each part gets a 90% bootstrap interval.

   The outcomes are:
   - **Size, not filter length:** E2 and E3 differ with the sign of Δ at both primary filters (rule 2), and neither F_L interval lies entirely on Δ's side of zero.
   - **Filter length, not size:** E2 and E3 are equivalent at both primary filters, and an F_L interval lies entirely on Δ's side.
   - **Both:** size differs as in the first outcome, and an F_L interval lies on Δ's side.
   - **Inconclusive:** otherwise.

   Code inspection predicts F_L ≤ 0, apart from dead-body births.
6. **Neutral scaling of the filter.** At a fixed t, lineages in larger populations pass the filter more easily under drift alone, since neutral coalescence takes about 2N generations (MODES p. 8).
   - If E1 or E2 differs at a fixed t, run the same test on the t = N diagonal, uncorrected.
   - If it differs in the same direction, label the result *beyond the filter's neutral scaling*. Otherwise label it *consistent with the filter's neutral scaling*.
   - E3 has no filter. A1a, mutational supply, can still raise it, and the origin endpoint describes that.
7. **Patterns are descriptive.** Each label below is used in the report only if its criterion holds. No label is a claim, and more than one may hold.
   - *Supply-like* (A1a): the bootstrap interval of the log–log slope of origins per generation against N contains 1, and the Spearman ρ between L and longest episode has an interval that contains 0.
   - *Smooth* (A1b): episode length rises with L, and no single step between adjacent sizes accounts for more than half of the rise in E2 from the smallest to the largest size.
   - *Pattern-like* (A2): the Spearman ρ between L and ξ has an interval that contains 0, and ξ < L/4 at 64 × 64. In addition, at the smallest size, most filter-free global losses follow a level with one cluster.
8. **Strategy classes are descriptive.** They are reported per size with exact 95% intervals, as in the access study.

### Code changes, before validation

Put these in a new study directory, `kernel/runs/lattice-size-01`, copied from dead-code-01's `study.cpp`. Neither the kernel nor any earlier study changes.

1. Separate the window start from t, and evaluate every filter in one list on one grid.
2. Run class assays for genotypes in F(A) at t = N, plus `RCCCJD` at its first filtered carrier under any filter.
3. Count `RCCCJD` origins.
4. Add the spatial statistics to the census. Clusters use union–find with torus wrap-around.
5. Make the loss rule an analysis parameter in generations.
6. Keep the mechanism ledger. Drop the residue fork and M4, which served the dead-code claims.

### Validation (before any study seed)

These checks carry over from the earlier studies:

- identical hashes with and without the observer, now at all sizes, including the two new ones;
- forks that reproduce recorded births;
- a shadow that never changes the run hash;
- the fixed-program controls.

Three checks are new:

1. **Regression against a committed world.** At 32 × 32 with t = 1,024 and the old grid, the new observer reproduces the filtered sets and census of dead-code-01's `read_fetch-retain-31001` byte for byte.
2. **Spatial fixtures.** Hand-built lattices with known cluster counts. One cluster spans the wrap-around and must count once; stripes and a checkerboard have known C(r).
3. **Origin fixture.** A replayed birth of `RCCCJD` from a non-`RCCCJD` parent counts once; an `RCCCJD` parent's faithful birth does not count.

Validation seeds 29941–29944 run at each size for 65,536 ticks. Their outcomes are not examined beyond these checks. Their timings revise the compute estimate before the primary run.

### Seeds

- **Primary.** 32001–32032 at every size. Block A is 32001–32016 and block B is 32017–32032.
- **Validation.** 29941–29944.
- **Disjoint from earlier protocols.** The latest earlier block ended at 31108.

**Using the same seeds at every size.** The kernel's only random draw is the copy substitution, keyed by seed, tick, site index and offset (`World::copied` in `kernel/src/vm.cpp`). A site index names a different place at each size, and the founder's index differs. Worlds with one seed therefore share no trajectory across sizes, and they are analysed as independent samples. The common list keeps the seed scheme identical, as requested.

**Detection limits.** These are approximate, from Fisher's z, ignoring ties.

- With 128 worlds (option B), the test has 80% power at |ρ| ≈ 0.30 at the strictest Holm level (0.05/5).
- With 96 worlds (option A), it has 80% power at |ρ| ≈ 0.34.
- Binary E1 has many ties, so its power is lower.

The earlier contrast, about 2% against 48% of timepoints, is far larger than these limits. Power matters mainly for the intermediate sizes and for the equivalence rule.

## Compute estimate

**Measured per-world times** come from the dead-code study on this 4-core container, four worlds at a time:

- 32 × 32 at H = 2²²: 383–440 s;
- 64 × 64 at H = 2²¹: 1,480–1,552 s for most worlds, and up to 2,514 s. At H = 2²² this gives about 3,000 s.
- Peak memory was 171–183 MB.

**Assumptions.**

- The new sizes are interpolated with a power law fitted to those two sizes: time ∝ N^1.41.
- A 15% margin covers the extra filters and spatial statistics, less the dropped residue fork and M4. The validation seeds will check it.

| Size | Seconds per world | CPU-hours for 32 worlds |
| --- | ---: | ---: |
| 24 × 24 | ≈ 190 | ≈ 1.9 |
| 32 × 32 | ≈ 420 | ≈ 4.3 |
| 40 × 40 | ≈ 790 | ≈ 8.1 |
| 48 × 48 | ≈ 1,300 | ≈ 13.3 |
| 64 × 64 | ≈ 3,000 | ≈ 30.7 |

| Option | Worlds | CPU-hours | Wall time on 4 cores |
| --- | ---: | ---: | ---: |
| A: 32, 48, 64 | 96 | ≈ 48 | ≈ 12 h |
| B: 24, 32, 48, 64 | 128 | ≈ 50 | ≈ 12.6 h |
| C: 24, 32, 40, 48, 64 | 160 | ≈ 58 | ≈ 14.6 h |
| Validation | 4 seeds per size, short, plus the regression world | < 0.5 | < 0.5 h |

**Not proposed now.**

- 96 × 96 for 32 seeds would need roughly 60–95 CPU-hours by extrapolation, or 15–24 h of wall time.
- A 32 × 128 strip has the same N as 64 × 64 but a short side of 32, so it would separate number (A1b) from length (A2) at a fixed N. It needs about 31 CPU-hours.

Both are better decided after this study shows whether persistence saturates by 64.

The work runs in committed batches as before. The 64 × 64 worlds take about 60% of the time.

## What this cannot show

- **It cannot test causality.** Size changes N and L together. Only a manipulation of spatial structure at fixed N, such as mixing, placement or a strip geometry, can test A2 causally.
- **One cell only.** It covers read_fetch with retained dead code. Other arms, and cleared dead code, may scale differently.
- **No adaptation claim.** A size effect, even one beyond the filter's neutral scaling, does not show adaptation. Neutral mutational supply also rises with N.
- **No open-endedness claim.** The six-byte genome caps complexity. The study compares persistence of one genotype, not open-ended growth.
- **The parasite reading is an analogy.** `RCCCJD` is partly self-executing and has no hypercycle partner. The precedents supply hypotheses, not expected values.

## Agreed choices

On 2026-11-26 every decision below was settled as recommended, including option B. Item 13 is settled by its stated condition on the validation timings.

| # | Decision | Agreed |
| --- | --- | --- |
| 1 | Adopt the question as a scale control after the dead-code study, with A0, A1a, A1b and A2 as outcome patterns that may co-occur | Adopt |
| 2 | Arm | read_fetch-retain only, the cell where `RCCCJD` occurs in both earlier studies. Adding read_fetch-empty would roughly double the cost. |
| 3 | Sizes | Option B: 24, 32, 48, 64 |
| 4 | Seeds | 32001–32032 at every size, blocks A and B; validation 29941–29944 |
| 5 | Common grid | Ḡ 4,096–16,384, step 256, at every size and filter |
| 6 | Filters | Compute t ∈ {576, 1,024, 2,304, 4,096} at every size. Primary: fixed t = 1,024 and 4,096. The t = N diagonal is secondary. |
| 7 | Primary family | E1 and E2 at both primary filters, plus E3; Spearman permutation tests, Holm over five, block-sign rule |
| 8 | Loss rule | 1,024 generations at every size and filter; 4,096 as sensitivity |
| 9 | Attribution rule | The decomposition in rule 5 |
| 10 | Secondary endpoints | Origins, spatial statistics, loss anatomy and the ledger, descriptive and in the observer only |
| 11 | Class assays | Only at t = N, plus `RCCCJD` itself |
| 12 | Drop the residue fork and M4 | Adopt |
| 13 | Extended window, Ḡ 17,408–65,536 at t = N | Adopt if validation shows under 10% extra time; otherwise drop |
| 14 | Later options: 96 × 96, a 32 × 128 strip, a mixing or placement manipulation | Defer until this study's result is known |
