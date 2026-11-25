# Does retaining dead code change evolutionary dynamics?

**Third research question, agreed 2026-11-25.** This brief takes the dead-code question, [frontier candidate 2](frontier.md#candidate-research-questions-proposals-only), as the third research question, after the [access question](access-dynamics-rq.md). Every decision at the end was settled as recommended ([agreed choices](#agreed-choices)). The run protocol and records are in [dead-code-01](../../kernel/runs/dead-code-01/README.md).

**Question.** Start from the same independently reproducing ancestor and the same access permission. Does keeping the bytes of dead individuals readable and executable, rather than clearing them, change the population's long-term evolutionary dynamics? The only manipulated rule is the contract's existing reclamation setting, retain or empty. The measurements are those of the access question, so its results can be compared directly.

**Two hypotheses, stated as outcome patterns.** Both can hold at once, and neither is assumed.

- **H-buffer.** Residual bytes buffer mutation. They lower the effective error burden and raise the persistence of genotypes.
- **H-raw.** Residual bytes are raw material for reading and borrowed execution. They raise novelty and the rate at which dependent strategies appear.

## What reclamation does in this kernel

The statements in this section come from code inspection of the [contract](../r0-kernel-contract.md) and `kernel/src/vm.cpp`. None comes from an executed run.

- **Release paths.** `release()` (`vm.cpp:19-23`) either keeps the bank's bytes (`retain`, the default) or resets the bank to an empty one with visible length 0 (`empty`). It is called in three places:
  - for an aging CPU's own bank;
  - for that CPU's held reservation (`vm.cpp:121-122`);
  - for an incomplete reservation released at `D` (`vm.cpp:212`).

  Residue is therefore of two kinds: the complete bodies of the dead, and partly written offspring banks.
- **Space is identical.** Death and release move a site to free under both settings. Free + reserved + occupied is the same, and so is every placement decision.
- **Death is unselective.** With age limit 80, placement on free sites only, and newborns that never overwrite, age is the only cause of death. Every individual's body becomes residue at age 80, whatever its genotype. Residue is therefore a sample of the population lagged by 80 ticks, plus the failed partial copies. This differs from Tierra, whose reaper also moves error-prone creatures up its queue ([Ray 1991, printed p. 379](../references/pdf/ray-1991-synthesis-of-life.pdf#page=9)).
- **Residue inside reservations.** `R` resizes a claimed free bank and preserves its visible prefix. Under retain, the unwritten offsets of a new reservation hold the previous occupant's bytes. Under empty, they are zero.
- **Who can see residue.** A CPU can always read and fetch its own body. The external flags open all four neighboring banks, whatever their state.
  - **self.** No residue is visible. A copy from a neighbor and a jump into one fail on permission, whatever the bytes. The event streams under retain and empty are therefore identical, and only the state hash differs. This gives an exact null control.
  - **read.** `S` plus `C` can copy residual bytes from a free or reserved neighbor bank into the CPU's reservation.
  - **read_fetch.** In addition, `J` can transfer execution to offset 0 of a free bank and run residue as code. Under empty, offset 0 of a free bank is invalid, so the jump falls through locally.

The access study kept retain in every arm. Its read and read_fetch arms therefore exposed living, reserved and dead neighbors together, and its results cannot separate them ([run record](../../kernel/runs/access-dynamics-01/README.md#what-this-does-not-show)).

## Why this question, and what the access study already suggests

Under the access study's preregistered rules, reads plus fetch raised Bedau's mean new activity over self-only access. No MODES endpoint differed. The only dependent genotype to pass the persistence filter was the fetch-requiring `RCCCJD`. It was transient at 32 × 32 and established in all eight full-access worlds of the descriptive 64 × 64 check.

Code inspection shows that `RCCCJD` can complete a copy by executing the code of a neighbor at its bearing. That neighbor can be living or reserved. Under retain, it can also be a free bank holding the body of a dead `R..CLD`, `RCCCLD` or `RCCCJD`. Whether `RCCCJD` actually used dead code was not recorded.

The 64 × 64 check also gave one unexplained, descriptive observation. In read_fetch worlds, variation births were 10.5–10.7% of births, against 11.5–11.6% in self and read worlds. With 6 copies per birth and a 2% substitution rate, substitutions alone predict 1 − 0.98⁶ = 11.42%. A share below that floor means substitution-bearing copies were lost before birth. The 32 × 32 primary arms were all within 11.35–11.46% ([scale section](../../kernel/runs/access-dynamics-01/README.md#scale-check-descriptive)).

One candidate mechanism comes from code inspection only and has not been checked by replay. When an `RCCCJD` carrier's reservation lies in its bearing direction, its `J` executes its own offspring's freshly written bytes. A substitution in those bytes can then stop the division. If so, the mechanism acts under both reclamation settings. This brief proposes to measure it rather than assume it.

## Closest precedents

Source claims only; page numbers are printed pages unless marked PDF. Reading depth and access are recorded in the [reference manifest](../references/manifest.json) and the [ledger of uncached sources](../references/unavailable.md).

| Source | What it shows | Use here |
| --- | --- | --- |
| Ray 1991, *An Approach to the Synthesis of Life*, published chapter ([local](../references/pdf/ray-1991-synthesis-of-life.pdf#page=9)) | Creatures are killed by deallocating their memory. "Their 'dead' code is not removed from the soup" (p. 379). Parasites are sloppy replicators that move pieces of code between creatures. Ray attributes this to "the parasites' inability to discriminate between live, dead, or embryonic code" (p. 380). | Tierra retains dead code, which is H-raw's precedent. The reaper is selective, unlike TIDE's age death. |
| Ofria and Wilke 2004, *Avida*, published article ([local](../references/pdf/ofria-wilke-2004-avida.pdf#page=15)) | In most Avida experiments organisms may not read or write each other's genomes, "so that Tierra-style parasites cannot form" (p. 205). A newborn replaces its parent or another cell in the neighborhood (p. 203). | In its default configuration, a system with no access to other genomes or to dead code. |
| Hickinbotham, Stepney and Hogeweg 2021, spatial Stringmol, published article ([local](../references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf#page=14)) | Decay removes strings from the system with a fixed uniform probability (article p. 12, PDF p. 13). | A clearing rule; decay leaves no residue. |
| Agüera y Arcas et al. 2024, *Computational Life*, arXiv:2406.19108v2 preprint ([local](../references/pdf/aguera-y-arcas-et-al-2024-computational-life-v2.pdf#page=4)) | No programs are generated or removed; change comes only from self-modification and background mutation (PDF p. 4). At the first replicator, "a few bytes persist on the tape from the epoch 1, but most were copied from another tape" (PDF p. 7). | Every byte persists, and replicators are assembled from other tapes' bytes. |
| van Nimwegen, Crutchfield and Huynen 1999, arXiv:adap-org/9903006v2, preprint of PNAS 96:9716 ([local](../references/pdf/van-nimwegen-crutchfield-huynen-1999-neutral-robustness-v2.pdf)) | Mutational robustness is measured as the population's average number of neutral mutant neighbors. It can be inferred from average fitness and mutation rate (Eq. 4, PDF p. 2), and it rises with population size times mutation rate (PDF pp. 5–6). | Source of the neutrality measure M4 below. |
| Wilke et al. 2001, *Nature* 412:331, abstract only ([DOI](https://doi.org/10.1038/35085569)) | At high mutation rates, genotypes in flatter regions of the fitness surface outcompeted faster replicators on higher peaks. | Robustness can decide competition. This supports measuring robustness, not only replication rate. |
| Redfield 1988, *Genetics* 119:213, abstract only ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1203342/)) | Simulations compare transformation using DNA from living and from killed cells. The abstract concludes that transformation can reduce mutation load. | A biological analogue for H-buffer: material from the dead as a source of repair. |
| Michod, Wojciechowski and Hoelzer 1988, *Genetics* 118:31, abstract only ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1203263/)) | UV-treatment experiments are reported as supporting the DNA-repair hypothesis for the evolution of transformation. | The repair reading of H-buffer. It is an analogy, not a mechanism claim about TIDE. |

The targeted search found no artificial-life study that compares retained and cleared dead code with everything else fixed. Tierra successors other than those listed (Cosmos, Amoeba, Physis, Nanopond) remain unread, as the [roadmap](../roadmap.md) records.

## Design

### Manipulation

Reclamation is set to `retain` or `empty`. Everything else is as in the [access study protocol](../../kernel/runs/access-dynamics-01/protocol.md):

- the `R..CLD` ancestor;
- a 32 × 32 torus with first-free placement;
- age limit 80 and 20,000 ppm substitution;
- synchronous update with coordinate arbitration;
- H = 2²² ticks;
- the MODES window t = 1,024 with 61 timepoints, and the neutral shadow.

### Combining with the access arms

| Option | Cells | Worlds at 32 seeds | Comparisons it supports |
| --- | --- | ---: | --- |
| **A (recommended)** | read × {retain, empty}, read_fetch × {retain, empty}, plus self (retain) as a reference | 160 | Reclamation effect under each access level. Whether it depends on fetch, descriptively. A replication of the access study's C3 on new seeds. |
| B | read_fetch × {retain, empty} | 64 | Reclamation effect where residue can be both copied and executed. It cannot tell copying from execution. |
| C | Full 3 × 2 | 192 | As A. The self-empty cell adds no information, because it is identical to self-retain by construction. |

Under every option, self-empty runs only in validation, as the exact null check.

### Primary claims

- **D1.** In the read arm, retain versus empty changes P1–P4.
- **D2.** In the read_fetch arm, retain versus empty changes P1–P4.

P1–P4 and rules 1–6 are those of the access brief ([interpretation rules](access-dynamics-rq.md#interpretation-rules)), with two changes:

- Holm correction runs over these 8 tests.
- The reference arm for Glass's Δ and for the equivalence bound is the empty arm.

Claim outcomes keep the access brief's three labels: "supported", "no detectable effect at this scale" and "inconclusive".

The difference between the D2 and D1 effects is reported descriptively.

### Endpoints that separate the hypotheses

Each is computed per world, and the comparison is always retain minus empty within an access arm.

| ID | Endpoint | H-buffer predicts | H-raw predicts |
| --- | --- | --- | --- |
| M1 | **Rescue**: fraction of substitution-bearing newborns that give birth at least once before death | Higher | No prediction |
| M2 | **Substitution-free variation births** per 10⁶ births: products that differ from their material parent without any substitution, because their bytes came from several sources or were misaligned | No prediction | Higher |
| M3 | **Realized load**: fraction of individuals that reach age 80 without giving birth | Lower | No prediction |
| M4 | **Neutrality** (van Nimwegen's measure, applied to sampled filtered genotypes): fraction of the 66 single-substitution neighbors that still reproduce in the carrier's birth environment | Higher, and lower again when residue is cleared in the fork | No prediction |
| M5 | **Persistence**: mean run of consecutive window timepoints a filtered genotype stays in F(A) | Higher | No prediction |
| M6 | **Dependent classes**: establishment of read-, fetch- and residue-requiring classes | No prediction | Higher |
| P1, P4 | MODES novelty, Bedau new activity (primary endpoints) | No prediction | Higher |
| P2 | MODES change (primary endpoint) | Lower, since filtered sets turn over less | Higher, since new genotypes enter |

Most predictions fall on different endpoints, so the hypotheses need not compete. P2 is the one endpoint where they predict opposite directions. A result in the opposite direction counts against a hypothesis:

- against H-buffer: M1, M4 or M5 lower, or M3 or P2 higher;
- against H-raw: M2, P1, P2 or P4 lower.

**Pattern rule.** Classify each access arm's result:

| Pattern | Condition |
| --- | --- |
| Buffer-consistent | At least one of M1, M3, M4, M5 or P2 differs in the H-buffer direction, and none differs against it |
| Raw-consistent | At least one of M2, P1, P2 or P4 differs in the H-raw direction, and none differs against it |
| Both | Both conditions hold |
| Neither | Neither condition holds |

"Differs" follows rules 1–3 of the access brief. Holm correction runs within a mechanism family of M1–M5 × 2 arms; P1, P2 and P4 keep their primary-family result. Because P2 cannot satisfy both, the pattern "both" requires P2 not to differ. M6 is descriptive, as strategies were in the access study. The total variation share and its substitution-bearing part are reported descriptively under the optional analyses.

A consistent pattern is not a causal attribution. Causal claims need the residue fork below.

### Mechanism ledger (observer only)

The observer records, for every completed and every abandoned division:

- each byte's supplier bank and its state at the opening snapshot: own body, living neighbor, reserved bank, or free bank;
- for borrowed execution, the state of the bank each fetched instruction came from;
- the substitution count of each copy;
- whether the division completed.

The ledger gives each birth's share of material and executed code taken from residue. It also splits the variation share into its substitution-bearing part and M2, and it checks the candidate self-execution filter above. In the empty arms, residue sources must be zero; this is a validation check. The ledger changes no transition.

### Residue fork

The access study classifies genotypes by forking at the first filtered carrier's birth with permissions or bytes changed. This study adds one fork. At that tick, every free bank and the unwritten offsets of every reservation are cleared, and the fork runs with reclamation set to empty for the carrier's lifetime. Everything else is unchanged. A genotype whose ordinary births exceed zero but whose residue-cleared births are zero is **residue-requiring**.

This separates causal use of dead code from merely having it nearby, as the frontier note requires. The fork uses two analysis hooks, tested like `World::replace_bytes`: `World::clear_residue` empties those banks and `World::set_reclamation` switches the forked world's reclamation setting. Neither changes a transition rule.

### Optional analyses (descriptive)

1. **`RCCCJD` stability under read_fetch.** For each world, report:
   - establishment and loss episodes;
   - the share of `RCCCJD` births whose borrowed fetch came from a free bank, a living neighbor, a reserved bank, or the carrier's own reservation;
   - at each establishment and loss timepoint, the local density of carriers and of residue.

   If `RCCCJD` relies on dead code, it should establish less often under empty.
2. **Effective error rate from borrowed copying.**
   - Report per arm and cell the total variation share, its substitution-bearing part and M2, together with the binomial expectation 1 − (1 − μ)⁶.
   - Report the substitution count per abandoned division against completed births. This tests whether substitution-bearing copies are lost before birth.
   - At zero substitution, every variation birth comes from foreign or misaligned material. This is the direct measure of borrowed copying's contribution.

### Validation (before any study seed)

These run as in the access study:

- identical hashes with and without the observer;
- forks that reproduce recorded births;
- a shadow that never changes the run hash;
- the fixed-program controls.

Three checks are new:

1. **Self null.** In self-arm worlds, retain and empty give identical event streams, genealogies, MODES and Bedau outputs.
2. **Empty arms.** No byte or fetched instruction comes from a free bank.
3. **Residue-fork control.** A fixture shows a fetch into a retained dead body completing a birth, and the residue-cleared fork failing it.

### Seeds

- **Validation.** 29921–29924.
- **Primary.** 31001–31032, block A 31001–31016 and block B 31017–31032.
- **Scale check, descriptive.** 31101–31108 at 64 × 64, as in the access study.

These ranges are disjoint from every earlier kernel protocol. The access study's worlds are not reused: their observer lacked the ledger, and their results have already been read.

## Compute estimate

Per-world timings come from the access study's executed runs on this 4-core container, four worlds at a time:

| World size | Observer pass | Assay pass | Peak memory |
| --- | --- | --- | --- |
| 32 × 32, H = 2²² | median 337 s | 29 s for 117 genotypes × 10 forks in `read_fetch-30001`, about 25 ms per fork | about 170 MB |
| 64 × 64, H = 2²¹ | median 1,066–1,091 s by arm | 6–10 genotypes | |

**Assumptions.**

- The ledger and the residue fork add 15%. This is to be checked on the validation seeds.
- M4 needs 132 forks per sampled genotype: 66 neighbors, each in the ordinary and the residue-cleared environment.
  - Computing it for every assayed genotype (about 90 per world) would add about 300 s per world.
  - Sampling the genotypes in F(A) at every eighth window timepoint (9 timepoints, roughly 10–20 genotypes) adds about 60 s.

**Estimate with the sampled M4,** at about 480 s per 32 × 32 world and about 1,300 s per 64 × 64 world:

| Set | Worlds | Wall time |
| --- | ---: | --- |
| Option A primary | 160 | ≈ 5.3 h |
| Option B primary | 64 | ≈ 2.1 h |
| Option C primary | 192 | ≈ 6.4 h |
| Scale check, 4 cells × 8 seeds | 32 | ≈ 2.9 h |
| Validation | 12 short worlds plus the self null | < 0.5 h |

Option A with the scale check needs about 9 hours of wall time here, in committed batches as before. The ledger, the hook and their tests are separate implementation work.

## What this cannot show

- **Two settings only.** The study compares the two ends of reclamation. Intermediate decay of residual bytes would need a new contract variable.
- **Unselective death.** Residue here is an unbiased, lagged sample of the population. Results need not transfer to systems whose deaths are selective, such as Tierra's error-ordered reaper.
- **Six-byte genomes.** As in the access study, the genome caps complexity, and the question compares dynamics. It cannot show open-ended growth.
- **Pattern is not mechanism.** A buffer- or raw-consistent pattern is an outcome description. Residue dependence of a genotype is shown only by the residue fork, and adaptation only by replay.

## Agreed choices

On 2026-11-25 every decision below was settled as recommended, including option A, the new seed blocks, the residue-fork hooks, the 64 × 64 check and the optional analyses.

| # | Decision | Agreed |
| --- | --- | --- |
| 1 | Adopt the question, with H-buffer and H-raw as outcome patterns that may both hold | Adopt |
| 2 | How to combine with the access arms | Option A: read and read_fetch × retain and empty, plus self-retain as reference; self-empty in validation only |
| 3 | Seeds | New blocks as proposed; do not reuse access-study worlds |
| 4 | Primary claims D1, D2 on P1–P4 under the access study's rules, Holm over 8, empty arm as reference | Adopt |
| 5 | Mechanism endpoints M1–M5 as a preregistered secondary family with the pattern rule; M6 descriptive | Adopt |
| 5a | Scope of M4 | Sample the genotypes in F(A) at every eighth timepoint, not all assayed genotypes, which would add about 300 s per world |
| 6 | Mechanism ledger in the observer | Adopt; observer only |
| 7 | Analysis hooks for the residue fork: empty free banks and unwritten reservation offsets, and switch a forked world to empty reclamation | Adopt, as analysis-only kernel hooks tested like `replace_bytes` |
| 8 | Re-test the access study's C3 (read_fetch vs self, both retain) on the new seeds, reported separately | Adopt; costs no extra worlds under option A |
| 9 | 64 × 64 descriptive scale check over the four reclamation cells | Adopt, given the size difference seen for `RCCCJD` |
| 10 | Optional analyses: `RCCCJD` stability and effective error rate | Adopt, descriptive |
| 11 | All other parameters and windows as in the access study | Adopt, for direct comparison |
