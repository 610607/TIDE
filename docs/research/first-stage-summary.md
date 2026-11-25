# First-stage summary

Written 2026-11-25 at commit `a50e00d`. No experiment or simulation was run for this summary. Each statement restates a committed record linked beside it. Numbers marked *derived* are arithmetic done here on recorded counts. *Not recorded* marks what the records do not settle. Next steps named here are proposals from the linked records, not agreed plans. The second-stage research question has not been chosen.

"Since `ede3fee`" covers the 54 commits after `ede3fee` (2026-11-19) up to `a50e00d`. They add the reference VM and the 23 study records under `kernel/runs/`, the physub v31 control and four separate pool and chain experiments.

## 1. What the first stage established

The first question was agreed on 2026-11-23. Starting from an independently reproducing ancestor, can descendants evolve a heritable dependence on reading a neighbor's data or on fetching its instructions? The two channels are measured separately. [Research question](neighbor-dependence-rq.md) · [Stage report](neighbor-dependence-results.md)

- **Instruction fetch: yes, in the tested fields.** In 7 of 32 prospective seeds, a field mother and her daughter each needed neighbor fetch in a serial three-generation assay. With only the focal's fetch removed, the assay arena reached an exact cycle without births. The independent ancestor reproduced in both branches. [horizon-01](../../kernel/runs/horizon-01/README.md)
- **Data read: yes, in the tested fields.** Two independent five-byte worlds among 16,384 each produced six consecutive individuals that needed external reads in their natural birth environments. [placement-01](../../kernel/runs/placement-01/README.md) · [inheritance-01](../../kernel/runs/inheritance-01/README.md)
  - In six-byte fields, changed mother–daughter pairs that both depended on reads arose in 22 of 1,024 and 8 of 1,024 worlds. [six-origin-01](../../kernel/runs/six-origin-01/README.md)
- **Three kinds of continuity give different answers.** Permission forks test behavior, family tracking follows uninterrupted identical genomes, and per-byte donor identity follows material.
  - Identical bytes reappeared in four worlds after the tracked fetch families had died out. [persistence-01](../../kernel/runs/persistence-01/README.md)
  - In 845 of 3,161 intact living-template births, the template came from an individual that produced no offspring of its own. [sequence-stock-01](../../kernel/runs/sequence-stock-01/README.md)
- **Behavior across a change of sequence.** In 4 of 1,024 long-run worlds, a read-dependent pedigree crossed a program change and produced a confirmed descendant after the first carrier died. Every such later birth carried the original program again. [trait-lineage-01](../../kernel/runs/trait-lineage-01/README.md)

**Boundary**

- **One rule set.** The result holds under VM v1 [kernel contract](../r0-kernel-contract.md):
  - a 64-site torus (8 × 8 in the first cohorts, 16 × 4 in most later ones);
  - one supplied ancestor;
  - substitution-only copy mutation at 20,000 ppm;
  - age limit 80;
  - horizons of 512 to 8,192 ticks.

  No other rule set was tested for this result.
- **Individual and environment-specific.** Dependence belongs to a focal individual in its tested environment. It is scored by forks that deny only that individual's own access.
- **Short-lived families.** All eight prospective fetch families had ended by tick 713. The longest unchanged confirmed path in the long run had eight carriers. [persistence-01](../../kernel/runs/persistence-01/README.md) · [trait-lineage-01](../../kernel/runs/trait-lineage-01/README.md)
- **Not shown:**
  - a changed program kept past its first carrier's death in untreated fields;
  - spontaneous renewal of a copying relationship (0 of 1,024 worlds) [natural-renewal-01](../../kernel/runs/natural-renewal-01/README.md);
  - dependence on a provider's ongoing execution rather than on its bytes, which the research question brief describes but no record tests;
  - accumulation of adaptive innovations;
  - open-ended evolution.

## 2. New results since `ede3fee`, by question

**Infrastructure.** Commit `b61abe7` added:
- the VM v1 contract, which defines the success and failure transitions of every instruction;
- the C++ reference, with replay tests and traversal-reversal tests;
- fixed-program assays for reproduction from self, by reading and by fetching.

[Contract](../r0-kernel-contract.md) · [Worked birth](../r0-worked-birth.md) · [Reference tests](../../kernel/tests/vm_tests.cpp)

**Does fetch dependence arise and persist?** Once a longer assay resolved the earlier timeouts, fetch dependence was confirmed in 7 of 32 prospective seeds. The confirmed families died out by tick 713 while their populations kept reproducing. One archived lineage kept dependence across a point substitution, as did 215 of 330 engineered substitutions. Every main-line study after transmission-01 disabled neighbor fetch and studied reading only. [pilot-01](../../kernel/runs/pilot-01/README.md) · [replication-01](../../kernel/runs/replication-01/README.md) · [horizon-01](../../kernel/runs/horizon-01/README.md) · [persistence-01](../../kernel/runs/persistence-01/README.md) · [transmission-01](../../kernel/runs/transmission-01/README.md)

**Why did early read dependence stop after one generation, and what let it continue?** At first no reader passed its sequence on:
- None of the 37 daughters of reading mothers received the mother's sequence.
- None of 143 newborn readers had a compatible live neighbor in its first-copy window.
- In the few live encounters, the reader was still waiting for daughter space when the live donor left the neighboring bank.

Natural chains through living readers then appeared rarely:
- one family in 2,560 worlds;
- two consecutive transfers in 1 of 8,192 worlds;
- five consecutive transfers in another 1 of 8,192 worlds.

Matched placement showed that a daughter born to the west can read her living mother: 8 of 64 western assignments succeeded, against 0 of 64 northern and 0 of 64 southern ones.

[horizon-01 read audit](../../kernel/runs/horizon-01/README.md#why-the-observed-data-reads-stopped-at-one-generation) · [transmission-01](../../kernel/runs/transmission-01/README.md) · [geometry-01](../../kernel/runs/geometry-01/README.md) · [vacancy-01](../../kernel/runs/vacancy-01/README.md) · [lineage-01](../../kernel/runs/lineage-01/README.md) · [placement-01](../../kernel/runs/placement-01/README.md) · [inheritance-01](../../kernel/runs/inheritance-01/README.md)

**Can read dependence survive a change of program?** For five-byte readers, no single substitution kept confirmed dependence (0 of 1,210 trials). Six-byte programs could keep it: 8 of 11 supplied variants did. Natural six-byte fields produced changed dependent pairs, but none of their 57 grandchildren carried the changed sequence.

A single matching template restored exact copies in 33 of 40 cases. After the template was withdrawn, two of those lines reached a great-grandchild. Over the long run the behavior crossed a change in 4 of 1,024 worlds, and the new program never persisted. [read-variants-01](../../kernel/runs/read-variants-01/README.md) · [six-origin-01](../../kernel/runs/six-origin-01/README.md) · [template-pulse-01](../../kernel/runs/template-pulse-01/README.md) · [trait-lineage-01](../../kernel/runs/trait-lineage-01/README.md)

**Whose sequence persists, the executor's or the material's?** Intact copies of a living neighbor with a different genome occurred in 1,490 of 2,048 worlds. In 845 of the 3,161 such births, the donor itself had no offspring. Chains through living neighbors never exceeded two transfers. [sequence-stock-01](../../kernel/runs/sequence-stock-01/README.md)

**How do orientation, placement and movement shape copying and handoff?** Contact and read direction govern single copies:
- Randomizing the initial read direction alone accounts for repeated use of a newborn by its original executor (463 against 0).
- Moving a distant reader next to a surviving template gave a post-death birth in 45 of 3,439 cases. Equal-distance moves to non-adjacent sites gave none.
- Concentrating exchange into bursts raised complete six-byte reading from 43.6% to 61.6% of qualifying starts.

Handoff to a different reader stayed rare in every arm:
- It occurred in 0 to 6 worlds per 2,048.
- Only 845 of 15,129 templates ever had a neighbor carrying the S instruction after their executor died.
- High exchange lowered handoff from 6 new-seed worlds to 0 (exact paired p = 0.031).

[spatial-transport-01](../../kernel/runs/spatial-transport-01/README.md) · [bearing-handoff-01](../../kernel/runs/bearing-handoff-01/README.md) · [handoff-window-01](../../kernel/runs/handoff-window-01/README.md) · [contact-placement-01](../../kernel/runs/contact-placement-01/README.md) · [transport-handoff-01](../../kernel/runs/transport-handoff-01/README.md) · [transport-timing-01](../../kernel/runs/transport-timing-01/README.md)

**Can a changed program outlive its first carrier, and can untreated families renew copying?**
- **With a supplied partner.** Placing a living match beside a changed newborn produced a same-sequence descendant after the focal died in 3 of 46 cases. With the match placed far away, 1 case did. In seed 20349, two descendants supplied both the executor and the template after both original individuals had died.
- **Untreated.** No family renewed in 1,024 worlds. The record gives a one-sided 95% upper bound of 0.292% per world.
- **Where the seven starting copies stopped.**
  - In four families, only one eligible descendant appeared later.
  - The furthest family wrote all six bytes, but its executor died one step before division.

[partner-placement-01](../../kernel/runs/partner-placement-01/README.md) · [natural-renewal-01](../../kernel/runs/natural-renewal-01/README.md) · [Starter audit](../../kernel/runs/natural-renewal-01/starter-audit/README.md)

**physub, a separate substrate: does extra material stop the decline in strict sites?** No. With 64 instead of 48 initial monomers per site, no write was refused for lack of mass, and strict offspring rose by 4.5% to 10.7%. Even so, strict sites fell between 350k and 500k ticks in all four rich runs, and all eight runs failed criterion 1. The series is paused at v31. [v31](../../experiments/physub/runs/v31/README.md)

Section 4 covers the four pool and chain experiments.

## 3. Open lines

| Line | Current state | Where it is stuck | What continuing could answer |
| --- | --- | --- | --- |
| Renewal of a copying relationship in untreated fields | No renewal in 1,024 worlds; each of the seven starting copies was traced to the stage where it stopped. [natural-renewal-01](../../kernel/runs/natural-renewal-01/README.md) · [Starter audit](../../kernel/runs/natural-renewal-01/starter-audit/README.md) | Starting copies occur in under 1% of worlds, so a batch yields only a handful. The seven traced cases are a selection and do not estimate frequencies. | Which stage loses the most families, measured before choosing a placement or timing intervention. The stages are a second relative, overlap, adjacency, a read from the relative, a complete write and division. The starter audit proposes this prospective census; it has not been agreed. |
| Retention of a changed program | The behavior crossed a change in 4 of 1,024 worlds, but the changed bytes never persisted. A supplied partner gave 3 cases against 1 out of 46. [trait-lineage-01](../../kernel/runs/trait-lineage-01/README.md) · [partner-placement-01](../../kernel/runs/partner-placement-01/README.md) | There is no untreated positive case, and the partner effect rests on two discordant seeds. | Whether moving a changed carrier together with a compatible template lets the new program outlive the carrier. The stage report names this as a candidate comparison; it has not been run. |
| Handoff under movement | High exchange reduced handoff. Bursts raised continuity of reading, but handoff was equal (1 world against 1). [transport-handoff-01](../../kernel/runs/transport-handoff-01/README.md) · [transport-timing-01](../../kernel/runs/transport-timing-01/README.md) | With 0 to 6 handoff worlds per 2,048, the schedules cannot be told apart (section 5). | Whether the timing of movement changes takeover by a new reader, not only single copies. |
| Fetch channel beyond the first families | One archived lineage crossed a substitution, and 215 of 330 engineered substitutions kept dependence. [transmission-01](../../kernel/runs/transmission-01/README.md) | No fetch study since transmission-01. AGENTS.md lists survival of fetch dependence across genomic change in sampled pedigrees as open. | Whether fetch shows the same pattern of returns to the original sequence as reading does. |
| Dependence on a provider's execution | Not tested. [Research question](neighbor-dependence-rq.md) | A test would pause the provider's CPU while keeping its bytes readable. No record does this. | Whether the dependence is on bytes or on a running neighbor. |
| physub substrate | Paused at v31. [v31](../../experiments/physub/runs/v31/README.md) · [STATUS](../../experiments/physub/STATUS.md) | The decline persists without refusals for lack of material, and its cause is not isolated. | The census trial runs each key alone (code inspection of `apps/ps_census.hpp`; the roadmap also notes this), so it would not count a lineage that needs a neighbor as strict. Whether this contributes to the decline was not measured. |

## 4. Side lines

| Experiment | Its own question and main result | Link to the first question |
| --- | --- | --- |
| [template-pool-01](../../experiments/template-pool-01/README.md) | Can one supplied six-symbol guide bias what a pool of free pieces assembles, and can a randomly transferred product pass the bias on? The complement's share was 20.16% with the guide against 1.15% without. Starting from free pieces alone, 28 of 2,048 pools recovered an order through two exact transfers. | Not linked to the main question. It is motivated by the [sources on the origins of molecular inheritance](../references/README.md#origins-of-molecular-inheritance-2026-11-25) and uses its own model, not the VM. |
| [template-persistence-01](../../experiments/template-persistence-01/README.md) | How long does a naturally assembled sequence family persist under breakage and fresh supply? In 231 of 1,779 pools the original order was born again after its first chain broke. Median family survival was 112 encounters, and no family reached 2,048. | Not linked to the main question. |
| [chain-structure-01](../../experiments/chain-structure-01/README.md) | Does order bias contacts within a chain at fixed composition? The 2–5 contact occurred in 42.75% of the ensemble for one order and 17.30% for the other; the distributions were identical without attraction. | Not linked to the main question. |
| [chain-residence-01](../../experiments/chain-residence-01/README.md) | How long does a U bend last, and does it return after the chain opens? It lasted 96 proposals against 24, and the same U returned first in 23.25% and 18.37% of excursions. | Not linked to the main question. |

No record connects these four experiments to the reference VM or to the first question. This summary notes one formal parallel only. template-persistence-01 measures loss of exact descent after an origin breaks and the later recurrence of the same sequence. Those are pool analogues of the renewal and return measures in natural-renewal-01 and trait-lineage-01. The models share no rules.

## 5. Compute

**Wall time is not recorded for any kernel batch.** Commit times cannot stand in for it:
- Commit `b61abe7` added the VM together with five completed studies.
- Later protocol and result commits are about 4 to 10 minutes apart, and the records do not say when the runs started.
- Whether the runners used more than one thread is also not recorded.

The only recorded run times come from physub. Each 500k-tick run on the 96 × 96 lattice took 1 h 42 min to 2 h 25 min, with 16 jobs sharing 4 cores (v26 and v27). The eight v31 runs have no recorded time.

**Batch sizes in the main line.** Each world is a 64-site torus.

| Study | Worlds × arms | Ticks per world | Recorded births |
| --- | --- | ---: | ---: |
| [pilot-01](../../kernel/runs/pilot-01/README.md) | 8 × 3 | 512 | 7,327 |
| [replication-01](../../kernel/runs/replication-01/README.md) | 24 × 3 | 512 | 22,033 |
| [horizon-01](../../kernel/runs/horizon-01/README.md) | 32 × 3; assays up to 4,096 ticks per generation | 512 | not summed |
| [transmission-01](../../kernel/runs/transmission-01/README.md) | 256 read-only | 512 | not summed |
| [geometry-01](../../kernel/runs/geometry-01/README.md) | 256 × 3 layouts | 2,048 | 1,000,951 |
| [vacancy-01](../../kernel/runs/vacancy-01/README.md) and [lineage-01](../../kernel/runs/lineage-01/README.md) | 2,560 | 2,048 | 3,313,197 |
| [placement-01](../../kernel/runs/placement-01/README.md) | 8,192 | 2,048 | 10,598,408 |
| [inheritance-01](../../kernel/runs/inheritance-01/README.md) | 8,192 | 2,048 | 10,600,887 |
| [six-origin-01](../../kernel/runs/six-origin-01/README.md) | 1,024 + 1,024 | 2,048 | 2,521,383 |
| [spatial-transport-01](../../kernel/runs/spatial-transport-01/README.md) and [bearing-handoff-01](../../kernel/runs/bearing-handoff-01/README.md) | six-origin seeds × 4 arms each | 2,048 | about 2.5 million per arm |
| [transport-handoff-01](../../kernel/runs/transport-handoff-01/README.md) | (2,048 earlier seeds + 2,048 new) × 3 | 2,048 | not summed |
| [transport-timing-01](../../kernel/runs/transport-timing-01/README.md) | (2,048 earlier seeds + 2,048 new) × 2 | 2,048 | not summed |
| [trait-lineage-01](../../kernel/runs/trait-lineage-01/README.md) | 1,024, plus 11,718 paired lifetime assays | 8,192 | 5,282,748 |
| [natural-renewal-01](../../kernel/runs/natural-renewal-01/README.md) | 1,024 | 8,192 | 5,493,369 |

Follow-up studies on selected cases are limited by how many natural cases exist: 40 in template-pulse-01, 46 eligible in partner-placement-01 and 7 in the starter audit.

**Limits on detecting rare events (derived).** The world is the sampling unit; individuals within one world are related. The figures in brackets are Wilson 95% intervals.

| Recorded outcome | Count | Rate per world |
| --- | ---: | ---: |
| Two consecutive live-reader transfers, five-byte | 2 / 16,384 | 0.012% [0.003%, 0.045%] |
| Different-reader handoff, stationary, new seeds | 6 / 2,048 | 0.29% [0.13%, 0.64%] |
| Different-reader handoff, high exchange, new seeds | 0 / 2,048 | at most 0.146% |
| Behavior survived its first carrier across a change | 4 / 1,024 | 0.39% [0.15%, 1.00%] |
| Starting copy for renewal | 7 / 1,024 | 0.68% [0.33%, 1.40%] |
| Renewal, or a changed program kept after its carrier died | 0 / 1,024 | at most 0.292% |

- **A zero count bounds the rate only loosely.** The one-sided 95% upper bound is 0.29% for 1,024 worlds, 0.15% for 2,048 and 0.037% for 8,192.
- **Seeing one event at all needs many worlds.** For a 95% chance of at least one event, about 1,000 worlds are needed at a rate of 0.3%, about 3,000 at 0.1% and about 24,500 at 0.012%.
- **Comparing two arms needs many more.** This uses a normal approximation with independent arms, 80% power and a two-sided 5% level. Separating 6 from 1 handoff worlds per 2,048 needs about 4,500 worlds per arm. Doubling a rate needs about 7,800 worlds per arm from 0.3% and about 47,000 from 0.05%. Paired seeds can lower these numbers; that reduction is not computed here.
- **Ticks limit long persistence.** With 81-tick lifetimes, 2,048 ticks spans about 25 lifetimes and 8,192 ticks about 100. Persistence beyond that is not observed.

The current batches of 1,024 to 8,192 worlds are therefore sized to detect events of roughly 0.1% per world or more. Comparing arms at the observed handoff and renewal rates would need batches several times larger. Whether such batches are affordable cannot be judged from the repository: wall time is not recorded, and the CPU baseline benchmarks (P1 in the roadmap) have not been run.
