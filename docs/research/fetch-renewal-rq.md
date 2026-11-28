# Does the fetch relationship renew where the fetch-requiring genotype persists?

**Draft for discussion, 2026-11-28. Not agreed.** Nothing here is a decision until the user agrees to it. The items under [decisions to settle](#decisions-to-settle) carry a recommendation each.

**Question.** In the read_fetch-retain worlds of [lattice-size-01](../../kernel/runs/lattice-size-01/README.md), does the relationship between a fetch-requiring executor and the living neighbor it fetches from get renewed across turnover of both roles, by descendants of both? Does renewal differ between the sizes where `RCCCJD` persists (64 × 64) and where it is lost (24 × 24)?

## Why this question

- **Copying renewal is rare.** Untreated copying relationships rarely started, and none renewed ([natural-renewal-02](../../kernel/runs/natural-renewal-02/findings.md): 31 starts in 29 of 5,300 worlds). The [eligibility audit](../../kernel/runs/natural-renewal-02/eligibility-audit/README.md) found that starter lineages mostly lost their program by copying other bytes without error, not by substitution or early death.
- **`RCCCJD` persists at 64 × 64.** In the same kernel, at 64 × 64, the fetch-requiring `RCCCJD` had a living carrier at every window level in 31 of 32 worlds ([lattice-size-01](../../kernel/runs/lattice-size-01/README.md)). In seed 32001 it had 54,970,677 births and 84,600 origins, so births, not repeated origin, carry most of its presence. 45% of its births fetched from a living neighbor ([secondary](../../kernel/runs/lattice-size-01/results/analysis/secondary.tsv)).
- **Persistence alone does not show renewal.** The [renewal evidence](relationship-renewal-evidence.md) notes that type presence, descendant survival and fetch-source shares do not trace both roles across turnover. A persisting executor type could rely on any available provider. It could also rely on its own kin, or on a provider lineage that is itself renewed. These are different findings, and existing records cannot tell them apart.
- **It tests stage 3 on existing worlds.** The 24 vs 64 contrast gives a place where persistence fails and one where it holds, with every other rule fixed. That is the roadmap's stage 3 test of predicting both outcomes.

## Material and kernel

- **Worlds.** Worlds are replayed from the lattice-size-01 configuration: read_fetch access, retain reclamation, `R..CLD` founder, 20,000 ppm substitution, age limit 80, the same seeds 32001–32032 and sizes 24, 32, 48 and 64, and the frozen kernel.
- **No kernel change.** Every `Event` already carries `fetch_site`, `fetch_contact` (site, birth tick, bank kind, bytes) and `pc`. Provider identity is therefore observable without new state. The observer is analysis-only.
- **Replay check.** In every world, the observed run's end hash and event digest must equal lattice-size-01's committed values.

## Definitions (candidate)

- **Executor.** A living carrier of `RCCCJD`, the genotype assayed as fetch-requiring in lattice-size-01.
- **Gestation.** An executor's interval from its birth, or its previous successful `D`, to the `D` that produces a birth.
- **Provider.** A living individual at a neighboring site that supplied at least one instruction the executor executed during that gestation. It is identified by site and birth tick (`fetch_contact.kind == occupied`, `fetch_site ≠ actor`). Fetches from reservations, free banks or the executor's own body do not make a provider. They are recorded by source class as in the ledger.
- **Fetch-dependent birth (FDB).** A birth whose gestation had at least one provider. It is written b = (E, P, c, t): executor, provider, child, birth tick. A gestation with several providers gives one FDB per provider, all marked as the same birth.
- **Confirmation.** An executor is confirmed if a fork at its birth gives ordinary births > 0, zero births with fetch denied at its site, and at least one blocked fetch. This is the same paired fork used in the copying studies, with fetch in place of reads.
- **Role descent.** Descent follows the material-parent links of the access study's genealogy. Each path must stay within one genotype: `RCCCJD` for executors, and the provider's genotype at b for providers.
- **Start.** A confirmed executor's FDB, sampled as described under [sampling](#sampling).
- **Renewal (depth one).** A later FDB b₁ = (E₁, P₁, c₁, t₁) renews b₀ = (E₀, P₀, c₀, t₀) when all of the following hold:
  1. Every fetch from P₁ in b₁'s gestation comes strictly after the committed deaths of both E₀ and P₀.
  2. E₁ and P₁ are distinct from each other and from E₀ and P₀. Both were born after the later of E₀'s and P₀'s births.
  3. E₁ is confirmed and descends from E₀. P₁ descends from P₀.
  4. At least one of E₁ and P₁ is c₀ or descends from c₀.
  5. t₁ falls within the follow horizon from t₀.

  This mirrors the copying rule of [natural-renewal-01](../../kernel/runs/natural-renewal-01/protocol.md), with fetch providers in place of living templates. Applying the same rule recursively gives depth.
- **Executor-only continuation (handoff).** An FDB that meets conditions 1, 2, 3 for E₁ and 5, with a provider that does not descend from P₀.
- **Kin provision.** A provider of genotype `RCCCJD` that shares a same-genotype material ancestor with its executor within the follow horizon.

## Endpoints (candidate)

Each world is one unit. Conditional endpoints use worlds with at least one start, and the number of worlds with no start is reported.

| Endpoint | Definition |
| --- | --- |
| **F1** | Fraction of sampled starts with depth ≥ 1 |
| **F2** | Fraction of sampled starts with depth ≥ 2 |
| **F3** | Provider continuity excess. Among post-turnover FDBs by descendants of E₀, the observed share whose provider descends from P₀, minus a null share. The null share is the mean, over the same FDBs, of the fraction of the executor's living neighbors at the fetch tick that descend from P₀. |
| F4 (descriptive) | Share of FDBs with kin provision, and the provider genotype distribution |
| F5 (descriptive) | Starts per generation in the window; maximum depth per world |

**Tests.** For F1–F3, use the lattice-size-01 test family: two-sided permutation Spearman ρ between L and the endpoint, 100,000 permutations, Holm correction over three tests, the same block-sign rule and the same equivalence rule.

**Outcome patterns (descriptive labels, not hypotheses with claims attached):**
- **Renewal.** F1 > 0 at 64 × 64, F3 interval above 0, F1 rising with L.
- **Generic provision.** Executor-only continuation common, F3 interval containing 0. Persistence would then be explained by provider availability, not by a renewing partnership.
- **Kin provision.** F4 above one half at 64 × 64. Both roles are then filled from one family, so this is not a two-type relationship.

These patterns can overlap. Each is reported with its interval.

**Stage 3 prediction check (descriptive).** At 24 × 24, use each filter-free global loss of `RCCCJD` from lattice-size-01. Record whether the last start before the loss ended without renewal, and whether its executor lineage outlived its provider lineage. One account has to predict both the 64 × 64 persistence and the 24 × 24 losses, or it is revised.

## Sampling

1. **Pass 1.** Replay each world to the tick at which Ḡ reaches 16,384. List every FDB by a confirmed-type executor born in the window Ḡ 4,096–12,288, so that every start has its full follow horizon before Ḡ 16,384.
2. **Pass 2.** Draw up to 64 starts per world uniformly from that list. The generator is seeded from the world seed and a fixed constant. Where fewer than 64 exist, every one is taken. Replay again, fork-confirm the sampled executors and every candidate E₁, and score depth within the follow horizon.

## Validation (before any primary world)

- Hand-built fixtures:
  - a supplied executor–provider pair with known fetch events, scoring depth 0;
  - a supplied two-generation family with both roles replaced after both deaths, scoring depth 1;
  - rejection cases: an early fetch, an unrelated provider and a non-descendant executor.
- On a validation seed at each size, the observed and bare runs give equal end hashes. Reverse traversal at a second optimization level gives the same scored tables.
- One lattice-size-01 world reproduces its committed ledger fetch-source counts from the new observer's provider records.

## Cost (estimate, not measured)

A lattice-size-01 64 × 64 world reached Ḡ 16,384 near tick 704,000 of 4,194,304, and the full run took 2,126 s. Two passes to Ḡ 16,384, plus forks, should take roughly 15–25 minutes per 64 × 64 world, and much less at smaller sizes. With four workers, all 128 worlds should take about three to five hours. Storage covers only FDBs, sampled starts and their families.

## Decisions to settle

1. **Executor set.** Recommended: `RCCCJD` only, for continuity with lattice-size-01. Other genotypes assayed as fetch-requiring would be recorded descriptively.
2. **Provider descent.** Recommended: same-genotype material descent, as in the copying rule. Any-genotype descent would be descriptive only, because over long times almost everything descends from the founder.
3. **Follow horizon.** Recommended: 1,296 ticks (16 lifetimes), so that depth ≥ 2 is reachable. Natural-renewal used 324 ticks.
4. **Sizes.** Recommended: all four, so that Spearman tests match lattice-size-01. The alternative is 24 and 64 only, which roughly halves the 48 × 48 cost but cannot show shape.
5. **Confirmation.** Recommended: individual fetch-denial forks for E₀ and every candidate E₁. Providers are not confirmed, since the question is about the executor's dependence.
6. **Sample size.** Recommended: up to 64 starts per world.
7. **Out of scope.** Whether dependence is on the provider's bytes or on its execution (a frozen-provider fork) is out of scope for this question. It would be a follow-up if renewal is found.
