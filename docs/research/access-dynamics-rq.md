# Does neighbor access change long-term evolutionary dynamics?

**Second research question, draft of 2026-11-25; not agreed.** Start from the same independently reproducing ancestor in every arm. Does the access permission change the long-term evolutionary dynamics of the whole population? The arms allow only the own body, neighbor data reads, or neighbor reads plus borrowed instruction fetch. Measure the dynamics with published open-ended-evolution statistics, not new ones. Every rule other than access stays fixed. Nothing in this draft is agreed. A [dead-code question](frontier.md#candidate-research-questions-proposals-only) (candidate 2) is proposed to follow it and has no brief.

**Worked example.** In a read-arm world, a copy substitution produces genotype G. Its carriers copy their own bytes but need a neighbor read to finish the loop. From the tick G first appears, Bedau's activity counter for G grows by one each tick that at least one carrier is alive. At MODES timepoint A, suppose a G carrier has a descendant alive t generations later. G then passes the persistence filter at A. It counts once toward novelty if it never passed before, and toward change if it was not in the previous timepoint's filtered set. Forking the world at the birth of that first filtered carrier then asks what G needs. If denying reads to the focal alone stops its births, G is classified as read-requiring. The classification is made in analysis and never feeds back into the run.

### Why this question follows the first

The first stage measured rare events in 16 × 4 fields of up to 8,192 ticks. Descendants evolved dependence on neighbor fetch and, separately, on neighbor reads. The dependent families were short-lived, and no confirmed changed program persisted beyond its first carrier without a supplied partner ([stage summary](first-stage-summary.md); [stage report](neighbor-dependence-results.md)). These executed results do not say whether access changes the population as a whole. Access might still change it through borrowed copying of neighbors' genotypes, mixed-source products, or use of retained dead bytes, even if no dependent family lasts. This question measures that aggregate effect in larger, longer fields.

The access flags apply to all four neighboring banks, whatever their state ([contract](../r0-kernel-contract.md#transitions)). The read and read_fetch arms therefore also expose reserved banks and the retained bytes of the dead. Reclamation stays at retain in every arm. Separating the dead-byte effect would need the reclamation comparison that the dead-code candidate proposes.

### Claims to test

| Claim | Comparison | Primary statistics |
| --- | --- | --- |
| C1. Neighbor reads change long-term dynamics | read vs self | P1–P4 below |
| C2. Adding borrowed fetch to reads changes them | read_fetch vs read | P1–P4 |
| C3. Full neighbor access changes them | read_fetch vs self | P1–P4 |

Each claim is two-sided; no direction is predicted. The first stage gives no basis for one. Dependent families were rare and short-lived, so a small or null effect is plausible. A matched difference of zero is a valid outcome, and the [interpretation rules](#interpretation-rules) state how equivalence is declared.

### Closest precedents

| Source | What it contributes | Expected difference in TIDE |
| --- | --- | --- |
| Bedau, Snyder and Packard 1998 (published conference paper) | Genotype activity counters, diversity, new and mean cumulative activity, a neutral shadow and three classes of long-term dynamics, applied to Echo and the fossil record. [Cached PDF](../references/pdf/bedau-snyder-packard-1998-long-term-evolutionary-dynamics.pdf) · [Source](https://people.reed.edu/~mab/papers/alife6.pdf) | The paper classifies systems. TIDE compares three access rules of one system on matched seeds. Genomes have a fixed length of six bytes, so at most 12^6 = 2,985,984 genotypes exist and diversity is bounded by construction. |
| Bedau and Packard 1992; Bedau et al. 1997 (book chapter; conference paper) | The origin of activity counters and the first neutral analogues of Evita and Bugs. [1992](../references/pdf/bedau-packard-1992-evolutionary-activity.pdf) · [1997](../references/pdf/bedau-et-al-1997-evolutionary-activity-comparison.pdf) | Background only. The definitions used here follow the 1998 paper. |
| Dolson, Vostinar, Wiser and Ofria 2019, MODES (published article) | Change, novelty, complexity and ecology after a persistence filter of t generations. Applied to NK landscapes and to Avida treatments with 30 replicates per condition, using Kruskal–Wallis and post hoc Wilcoxon tests. [Cached PDF](../references/pdf/dolson-et-al-2019-modes-toolbox.pdf) · [Article](https://doi.org/10.1162/artl_a_00280) | Access, not environment or population size, is the treatment. Complexity is capped at six informative sites. Borrowed copying separates the executing parent from the byte supplier, so "descendant" needs a stated parent rule. |
| Stout and Spector 2005 (published conference paper) | Attempts to make the activity statistics classify an unlifelike system as class 3 failed. The paper reports Channon's criticism that the shadow drifts from the run, and his use of median activity. [Cached PDF](../references/pdf/stout-spector-2005-activity-validation.pdf) | Channon's own papers have not been read. His reset normalization is therefore not adopted. Median activity is reported because MODES also adopts it (Table 1 and footnote 2). |
| Hickinbotham, Stepney and Hogeweg 2021, spatial Stringmol (published experiment) | Replication strategies with parasitism and defenses evolved in surviving runs; 12 of 20 runs went extinct. [Frontier notes, F1](frontier.md#f1-spatial-stringmol-replication-strategy-evolves) | A bound-pair chemistry without TIDE's per-site CPU ownership. TIDE varies only the access permission and reports extinction with survival. |
| Ray's Tierra (book chapter) | Borrowed execution and redirected copying arise when programs can read and execute others' code. [Mechanism notes](../tierra-stringmol-kernel-notes.md#tierra) | The project notes record the mechanism, not a matched comparison of long-run dynamics with that access removed. |

The arms match [frontier candidate 1](frontier.md#candidate-research-questions-proposals-only): self-only, neighbor-read, and neighbor-read-plus-fetch, with own-allocation writes and the other rules held fixed.

## Arms and fixed rules

| Arm | `Access.read` | `Access.fetch` |
| --- | --- | --- |
| self | false | false |
| read | true | false |
| read_fetch | true | true |

A CPU can always read and fetch its own body. Everything else is the v1 baseline as used in the first stage, scaled up:

- 32 × 32 torus, synchronous next-tick update and coordinate arbitration.
- First-free placement, age limit 80 and 20,000 ppm copy substitution.
- Retained bytes at death.
- One `R..CLD` founder at x = 8, y = 16, PC 0, default bearing.

The same seed runs in all three arms. The contract keys substitution draws by seed, resolving tick, CPU site and destination offset, so the arms share draws for matching addresses and ticks. The kernel revision and every setting are frozen in a protocol commit before any study seed runs.

A 32 × 32 lattice holds up to 1,024 individuals, inside the 500–2,000 range of MODES's Avida populations. The first stage's 16 × 4 field caps coexisting genotypes at 64.

## Measurement

All statistics are computed by an observer that reads kernel events. It must leave the world's state hash unchanged.

### Components, parents and generations

- **Component:** the full six-byte genotype, as in Bedau 1998 and the MODES examples. MODES recommends reducing genomes to informative sites. Here that reduction is secondary for two reasons. It depends on one recorded birth environment per genotype. In TIDE it also misses bytes that matter only when another executor copies them.
- **Material parent:** the bank lifetime that supplied most of the child's six final input bytes, living or dead. A tie goes to the executor if it is tied, otherwise to the tied supplier of the lowest offset. *Adaptation:* MODES and Bedau assume one parent per birth. Here the genotype is inherited through bytes, which can come from a neighbor. In the self arm the material parent is always the executor.
- **Executor parent:** the CPU that divided. Every MODES statistic is repeated with executor parentage as a sensitivity analysis.
- **Generation:** the founder has depth 0, and each child has its material parent's depth plus one. The population's average generation Ḡ(τ) is the mean depth of living individuals at tick τ. MODES footnote 4 notes that average generation need not increase monotonically. A look-ahead of t generations from tick τ therefore ends at the first later tick with Ḡ ≥ Ḡ(τ) + t.

### MODES statistics

Definitions follow Dolson et al. 2019, §§3.1–3.2, read in the cached published article.

- **Persistence filter:** at timepoint A, a genotype passes if some individual alive at A carrying it has a descendant alive t generations later. The primary filter length is t = 1,024 generations, the lattice capacity. MODES used t equal to population size for NK and compared t = 500–4,000 in Avida. It also notes that the median neutral coalescence time is 2N, so t = N relies on selection. The same t is used in every arm.
- **Timepoints:** every 256 generations of Ḡ. This is finer than t, as §3.2.1 permits.
- **Change:** the number of genotypes in the filtered set F(A) that were absent from the previous timepoint's filtered set (eq. 1).
- **Novelty:** the number of genotypes in F(A) that have never passed the filter before (eq. 2). The genotype space has 2,985,984 entries, so an exact bit array replaces the paper's Bloom filter.
- **Ecology:** the Shannon entropy, in bits, of genotype frequencies among individuals at A whose lineages passed (eq. 3).
- **Complexity:** the largest number of informative sites among genotypes in F(A) (§3.2.3).
  - A site is informative if replacing its byte with `.` reduces the focal's births. The test forks the whole world at the birth of the genotype's first filtered carrier and runs to the focal's age death. `.` is a no-op in the contract.
  - MODES specifies a null replacement where positions matter (§3.1.2). Its footnote 3 uses lifetime reproductive output as fitness when a system defines none.
  - *Adaptation:* the paper uses average output. One recorded birth environment is used here because dependent genotypes can produce zero offspring outside their neighborhood.
  - The ceiling is 6. A genotype that persists only as a template for other executors scores 0.
- **Boundedness:** descriptive only. MODES §3.1.3 recommends fitting models rather than reading plateaus. Constant, linear, logarithmic and saturating-exponential models are fitted, and the one with the lowest AIC is reported. Because the genotype space is finite, "unbounded" can only mean no saturation within the horizon.

### Bedau activity statistics

Definitions follow Bedau, Snyder and Packard 1998, read in the cached copy.

- **Activity:** a genotype's activity counter grows by one each tick that the genotype is present (eq. 1).
- **Diversity:** D(t) is the number of genotypes present (eq. 2).
- **Cumulative activity:** total cumulative activity A_cum(t) sums the counters of genotypes present (eq. 4). Mean cumulative activity is A_cum / D. Median cumulative activity is reported alongside, following MODES Table 1 and footnote 2.
- **New activity:** A_new(t) is (1/D) times the sum of counters between a₀ and a₁ (eq. 7). It is 0 when D = 0.
- **Thresholds:** collapse the run's and the shadow's activity distributions over time. a* is the lowest activity at which the two cross, and a_max is the highest activity with a positive value in either. Then a₀, a₁ = a* ∓ 0.05 (a_max − a*), as in the paper's section on Echo's neutral shadow. Thresholds are set per world, as the paper sets them per run. Pooled thresholds across all worlds are a sensitivity analysis.
- **Sampling:** every 4,096 ticks over the whole horizon.

**Neutral shadow.** The shadow follows the 1998 paper:

- It holds nominal genotypes with no location.
- Each run birth picks a shadow parent uniformly from the individuals alive at the start of that tick.
- Each run death removes one uniformly chosen shadow individual alive at the start of that tick.
- Same-tick newborns join after both steps, so the two populations always have equal size.

In the paper, a shadow child receives a new, unique genotype when a mutation occurs, at the run's mutation rate.

*Adaptation:* TIDE has no fixed per-birth mutation rate, and borrowed copying can create new genotypes without substitution. The shadow child therefore receives a new genotype exactly when its run birth was a variation birth. A variation birth is one with at least one substitution in the final bytes, or whose inputs were not an aligned copy of one bank's six bytes. A faithful copy of a neighbor is treated as the choice of a different parent, and the shadow randomizes that choice.

The shadow uses its own counter-based random stream keyed by seed and event index, so it cannot affect the run. MODES statistics are also computed on the shadow, with its own parent links, as the neutral expectation under the run's demography. The MODES conclusions (§6) call a comparison of the shadow with the persistence filter worthwhile. Complexity and strategy classes are undefined for the shadow.

Channon's shadow reset and the component-level normalization reported by Stout and Spector are not used, because the original papers have not been read.

### Strategy classes

Classes are diagnosed by permission forks after the run, as in the first stage, and never enter kernel state. For each genotype, take its first filtered carrier and fork the world at that carrier's birth. Run four lifetime assays of the focal: ordinary, reads denied, fetch denied, and both denied. Count the focal's births to age 80. The forking procedure is that of [trait-lineage-01](../../kernel/runs/trait-lineage-01/field.cpp).

| Class | Ordinary births | Reads denied | Fetch denied | Both denied |
| --- | --- | --- | --- | --- |
| independent | > 0 | > 0 | > 0 | > 0 |
| read-requiring | > 0 | 0 | > 0 | 0 |
| fetch-requiring | > 0 | > 0 | 0 | 0 |
| both-requiring | > 0 | 0 | 0 | 0 |
| either-sufficient | > 0 | > 0 | > 0 | 0 |
| template-only | 0 | — | — | — |

A denial that the arm already imposes is a no-op, so the self arm has only independent and template-only genotypes. Read-requiring, fetch-requiring, both-requiring and either-sufficient together are the dependent classes.

## Observation windows and endpoints

| Item | Definition |
| --- | --- |
| Horizon | H = 2²² = 4,194,304 ticks for every world. The MODES window needs Ḡ to reach 17t = 17,408 generations. At 80 ticks per generation that takes 1.39 million ticks, so H covers mean generation intervals up to 241 ticks. |
| MODES window | Timepoints at Ḡ = 1,024, 1,280, …, 16,384 (61 timepoints, t to 16t), each looking ahead t generations. Starting at t gives the first timepoint a previous filtered set. |
| Bedau window | Ticks 0 to H, sampled every 4,096 ticks (1,024 samples). |
| Survival | At least one occupied site at H. |
| Extinction | No occupied site at some tick up to H. This is absorbing. Window timepoints after extinction score zero change, novelty and ecology, and A_new = 0. Extinct worlds stay in the paired tests. |
| Demographic stagnation | Alive at H with no birth in the final 80 ticks, as in earlier TIDE protocols. |
| Evolutionary stagnation | Alive, with zero MODES novelty at every timepoint in the last quarter of the window (12t to 16t). |
| Unreached window | Alive at H but Ḡ < 17t. Endpoints use the reached timepoints, and the world is flagged. If more than 10% of living worlds in any arm are unreached, P1–P3 for comparisons with that arm are inconclusive. |
| Strategy establishment | Class X is established at the first window timepoint where F(A) contains a genotype of class X. |
| Strategy loss | After establishment, four consecutive timepoints (t generations) in which F(A) contains no class-X genotype. The class can re-establish later. |

### Primary endpoints, per world

- **P1** Total MODES novelty over the window.
- **P2** Mean MODES change per window timepoint.
- **P3** Mean MODES ecology per window timepoint.
- **P4** Mean Bedau A_new over the samples in (0, H].

MODES describes novelty as functionally equivalent to A_new, and ecology to D. Using both families tests whether a conclusion depends on the method.

### Secondary endpoints

These are reported for every world and arm without confirmatory tests:

- **Activity statistics:** D, A_cum, mean and median cumulative activity, and their values in the shadow.
- **MODES on the shadow,** plus run-minus-shadow differences.
- **Complexity:** window maximum and mean.
- **Boundedness:** the model fits above.
- **Demography:** survival, extinction tick, both kinds of stagnation, population size, and mean generation interval under each parent rule.
- **Strategies, per class:** whether it was established, the first establishment generation, the number of establishment episodes, the number of losses, and the fraction of window timepoints with a filtered genotype of that class.
- **Sensitivity analyses:** t = 256 and t = 2,048, executor parentage, informative-site components, and pooled a₀ and a₁.

## Interpretation rules

These rules are fixed before any study seed runs.

1. **Tests.** For each primary endpoint and each of C1–C3, run a two-sided Wilcoxon signed-rank test on the paired seed differences. Holm-correct across all 12 tests at family-wise 0.05. As effect sizes, report the median paired difference and Glass's Δ against the self arm (or the read arm for C2), which MODES used. Report Kruskal–Wallis across the three arms for comparability with MODES; it does not decide anything.
2. **Differs.** A comparison differs on an endpoint if its Holm-adjusted p < 0.05 and the median paired difference has the same sign in both seed blocks.
3. **Equivalent.** An endpoint is equivalent if a 90% bootstrap interval (10,000 seed resamples, fixed generator seed) of the mean paired difference lies within ±0.5 between-seed SDs of the reference arm.
4. **Otherwise inconclusive.** A failed observer check or more than 10% unreached worlds also makes the affected comparison inconclusive.
5. **Claim outcome.** A claim is supported if at least one of P1–P4 differs. It is answered "no detectable effect at this scale" if all four are equivalent, and is inconclusive otherwise.
6. **Neutral expectation.** For each endpoint that differs, compare the run-minus-shadow difference between the same arms with the same test, uncorrected.
   - If it differs in the same direction, the result is labelled *beyond the neutral expectation*.
   - If it does not, the result is labelled *matched by the shadow*: the arms differ in demography or variation timing, and the data do not show an effect through selection.
   - Neither label is an adaptation claim. The roadmap requires replay for those ([frontier](frontier.md#candidate-research-questions-proposals-only)).
7. **Strategies are descriptive.**
   - For each dependent class, report the number of worlds in which it was established, out of 32, with exact 95% intervals.
   - With 0/32, the one-sided 95% upper bound is 8.9% per world.
   - No strategy result can support C1–C3 alone.
8. **Classification is descriptive.** Bedau classes and boundedness can label an arm's trajectories. They cannot support C1–C3 or any open-endedness claim.

## Seed budget

- **Validation, not scored.** Seeds 29901–29904 run in all three arms for 65,536 ticks, plus one mutation-free self-arm world. The checks are:
  - With and without the observer, the world reaches identical state hashes.
  - Every fork reproduces the ordinary births it replays.
  - The shadow never changes the run's hash.
  - The mutation-free self-arm world has one genotype, zero change after its first window timepoint and zero ecology. Code inspection predicts complexity 4 for `R..CLD`, since `R`, `C`, `L` and `D` are each required.
  - The stage-1 fixed programs classify as independent, read-requiring and fetch-requiring in their fixture arenas ([fixed-program tests](../../kernel/tests/vm_tests.cpp)).

  Outcomes of these seeds are not examined beyond these checks.
- **Primary.** Seeds 30001–30032 in all three arms, 96 worlds. Block A is seeds 30001–30016 and block B is seeds 30017–30032. These ranges are disjoint from every earlier kernel protocol; the latest earlier block ended at 27712.
- **Scale check, descriptive.** Seeds 30101–30108 on a 64 × 64 torus in all three arms, 24 worlds. The founder sits at x = 16, y = 32, with t = 4,096 generations. The window runs from t to 4t, with timepoints every 1,024 generations, and H = 2²¹ ticks. MODES likewise ran several population sizes to check whether size constrained the dynamics.

Detection limits are from a normal approximation, checked by simulating the signed-rank test. They are stated as the paired standardized difference d_z, the mean paired difference divided by the SD of the paired differences.

- **Difference tests.** With 32 pairs, the test has 80% power at d_z ≈ 0.75 at the strictest Holm level (0.05/12), and at d_z ≈ 0.5 at 0.05 unadjusted. The block-consistency rule lowers power further.
- **Correlation between arms.** Shared draws may correlate the arms early on, but after millions of ticks they may be close to independent. With correlation ρ between arms, the SD of differences is √(2(1 − ρ)) times the arm SD. At ρ = 0, d_z = 0.75 corresponds to about 1.06 between-seed SDs of an arm.
- **Equivalence.** At a true difference of zero, the ±0.5 SD equivalence rule has about 74% power at ρ = 0.5 and about 24% at ρ = 0. A null result is therefore more likely to be inconclusive than equivalent unless the arms stay correlated.

MODES used 30 replicates per condition.

## Compute estimate

This estimate rests on the [tick timing benchmark](../../kernel/bench/README.md) of 2026-11-25, which timed VM steps only and ran no evolutionary analysis.

| Measured | Value |
| --- | --- |
| Bare step, per occupied site-tick | 0.037–0.048 µs, independent of arm |
| Step with event collection, per occupied site-tick | 0.061–0.091 µs |
| 32 × 32, per tick per world | 33–34 µs bare, 55–62 µs with events |
| 64 × 64, per tick per world | 132–143 µs bare, 300–306 µs with events |
| Four simultaneous processes | Same per-world speed as one, so throughput scales with cores |

The estimate assumes:

- Full occupancy at the highest per-site rates measured: 0.091 µs with events and 0.048 µs bare.
- Observer bookkeeping costs as much again as the event pass. This is not measured.
- A second, bare replay pass provides fork states.
- Each assayed genotype needs at most 10 lifetime forks of 81 ticks: four permission assays and six knockouts. The ordinary assay doubles as the intact baseline.
- Assays are needed only for genotypes first filtered inside the window. Their number is unknown. The upper bound is 61 timepoints × 1,024 individuals = 62,464 in the primary, and 13 × 4,096 = 53,248 in the scale check.

| Run | Fixed cost per world | Assays per world, upper bound | Worlds | CPU-hours | Wall time on 4 cores |
| --- | --- | --- | ---: | --- | --- |
| Primary, 32 × 32, H = 2²² | 391 s events + 391 s observer + 206 s replay = 988 s | 62,464 × 39.8 ms = 2,487 s | 96 | 26–93 | 7–23 h |
| Scale check, 64 × 64, H = 2²¹ | 782 + 782 + 412 = 1,976 s | 53,248 × 159 ms = 8,480 s | 24 | 13–70 | 3–17 h |
| Validation | — | — | 13 short worlds | < 1 | < 1 h |
| **Total** | | | | **about 40–165** | **about 10–41 h** |

The lower figures assume no assays. The upper figures assume every window timepoint is filled with distinct, newly filtered genotypes, which is not physically expected. Memory per world is small: the genotype bit array is 0.4 MB, activity counters for all genotypes take 12 MB, and the pruned phylogeny is a few MB.

**GPU (P2): not needed for this question.** The upper bound fits on this 4-core machine in under two days. Independent worlds already scale linearly across CPU cores, and the uncertain part of the cost is observer and fork work, which branches per genotype and does not map naturally onto a lattice GPU kernel. AGENTS.md places GPU work after the rules stabilize. The roadmap schedules P2 after R5 unless runs are too slow, and this estimate says they are not. A GPU backend must also match the CPU reference by state hash ([roadmap](../roadmap.md#performance-line)). Reconsider P2 if a follow-up needs lattices of 128 × 128 or larger at the same filter-relative window. One such world would need about 22 million ticks at about 1.5 ms each with events, roughly 9 hours of field simulation per world before observers and assays.

## What this cannot show

- Six-byte genomes hold the genotype space at 2,985,984 entries and complexity at six sites. The design compares dynamics across access rules; it cannot test open-ended growth.
- One ancestor, one lattice size for the confirmatory test, and one mutation rate. Effects may differ elsewhere, and only the one-variable rule allows that to be checked later.
- The arms change access to living, reserved and dead neighboring banks together. Attributing an effect to dead bytes needs the reclamation comparison, which is deferred.
- The persistence filter and the shadow reduce, but do not remove, neutral contributions. Adaptive claims about particular genotypes need permission or knockout replays.

## Open items for agreement

1. The primary parent rule: material, with executor as sensitivity.
2. Lattice size and the primary filter length t = 1,024.
3. The four primary endpoints and the ±0.5 SD equivalence bound.
4. The shadow adaptation for variation births.
5. Whether to run the 64 × 64 scale check.
6. Whether the complexity assays are required, or reported only if their cost is affordable.
