# TIDE Artificial Life Literature Review

Updated: 2026-11-15.

TIDE's current focus is a digital-life kernel driven by basic rules. Execution, replication, spatial interaction, and resource constraints come before phenotype naming, cards, and narrative. C++ implementation follows the rule discussion.

## Direction and open decisions

- Established: learn from Tierra and cellular automata; ecological labels should not determine physical behavior.
- Established: read and discuss the literature before delegating C++ implementation; start a fresh local address-based VM rather than extending the exploratory prototype.
- Established: pointer-directed byte copying, public-space allocation before division, and two-phase synchronous updates as the default, with sequential random-order updates as a CPU comparison.
- Established: study evolution after a supplied ancestor first; emergence from random programs is a separate, later experiment.
- Working defaults: one program per site, writes restricted to owned allocations, readable residual code, and CPU time as the only active cost. These remain named experimental variables.
- Open: the research question, instruction-level permissions and failure effects, conflict resolution, newborn timing, boundaries, placement, reclamation, and mutation operators.

[AGENTS.md](../AGENTS.md) is the authority for current decisions. The [research search record](research/README.md) tracks the next literature pass.

The design question is whether rules are composable, testable, and permit replication mechanisms to evolve. Few opcodes, no explicit fitness function, or complex images do not independently establish open-ended evolution.

## Core reading

### Tierra

Thomas S. Ray. 1991. *An Approach to the Synthesis of Life*. In *Artificial Life II*, pp. 371-408.

[Local PDF](references/pdf/ray-1991-synthesis-of-life.pdf) | [Author source](https://tomray.me/pubs/alife2/Ray1991AnApproachToTheSynthesisOfLife.pdf)

Programs allocate, copy, and divide in shared memory. Templates, permissions, and CPU scheduling define their interaction environment. Experiments start from a designed ancestor. For TIDE, permissions and scheduling are model assumptions rather than neutral implementation details.

### Avida

Charles Ofria and Claus O. Wilke. 2004. *Avida: A Software Platform for Research in Computational Evolutionary Biology*. *Artificial Life* 10(2):191-229.

[Local PDF](references/pdf/ofria-wilke-2004-avida.pdf) | [Author source](https://cse.msu.edu/~ofria/pubs/2004OfriaEtAl.pdf) | [DOI](https://doi.org/10.1162/106454604773563612)

Individuals have private program memory and virtual CPUs; experiments configure space, mutation, and task rewards. Its experimental controls are useful precedents. Task rewards prescribe some advantageous directions and should be distinguished from reproduction-only competition.

### Evoloop

Hiroki Sayama. 1998. *Spontaneous evolution of self-reproducing loops on cellular automata*. *InterJournal*, Brief Article 236.

[Local PDF](references/pdf/sayama-1998-evoloop.pdf) | [Institutional source](https://necsi.edu/spontaneous-evolution-of-self-reproducing-loops-on-cellular-automata) | [Author bibliography](https://bingdev.binghamton.edu/sayama/pub.html)

Collisions under deterministic local rules can produce heritable changes and differential reproduction. Rules and starting structures were designed; experiments commonly converge toward small loops. External random mutation is therefore not the only source of variation, and size convergence does not necessarily mean all genetic change stops.

Bibliographic distinction: this short article is different from the 1999 *Artificial Life* 5(4):343-365 paper, *A new structurally dissolvable self-reproducing loop evolving in a simple cellular automata space*. The detailed reading here used the short article.

Supplement: Hiroki Sayama and Chrystopher L. Nehaniv. 2024 preprint, v2. *Self-Reproduction and Evolution in Cellular Automata: 25 Years after Evoloops*. [Local PDF](references/pdf/sayama-nehaniv-2024-evoloops-v2.pdf) | [Versioned text](https://arxiv.org/html/2402.03961v2)

### Spatial Stringmol

Simon J. Hickinbotham, Susan Stepney, and Paulien Hogeweg. 2021. *Nothing in evolution makes sense except in the light of parasitism: evolution of complex replication strategies*. *Royal Society Open Science* 8:210441.

[Local PDF](references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf) | [Institutional source](https://research-portal.uu.nl/ws/files/110685157/rsos.210441.pdf) | [DOI](https://doi.org/10.1098/rsos.210441)

Neighboring programs bind and execute replication reactions. Recognition and defense strategies evolve within programs. Of 20 runs, 12 went extinct and eight continued to two million timesteps. The work motivates evolving replication strategies and reporting failed trajectories alongside survivors.

### Replication arising from random programs

Blaise Agüera y Arcas et al. 2024 preprint, v2. *Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction*.

[Local PDF](references/pdf/aguera-y-arcas-et-al-2024-computational-life-v2.pdf) | [Versioned text](https://arxiv.org/html/2406.19108v2)

Execution and self-modification produce replicators on several computational substrates, including some conditions without background random mutation. Other tested substrates did not show spontaneous replication. Replicator origins and evolution after a supplied ancestor require different experiments and acceptance criteria.

### Open-ended evolution

Tim Taylor et al. 2016. *Open-Ended Evolution: Perspectives from the OEE Workshop in York*. *Artificial Life* 22(3):408-423.

[Local PDF](references/pdf/taylor-et-al-2016-open-ended-evolution.pdf) | [Author source](https://www.tim-taylor.com/papers/taylor2016openended.pdf) | [DOI](https://doi.org/10.1162/artl_a_00210)

This workshop synthesis distinguishes observable hallmarks of open-ended evolution from candidate mechanisms. For TIDE, ongoing change, new strategies, complexification, and ecological relationships should be evaluated separately rather than collapsed into one score.

## Design implications

These are project inferences, not sufficient conditions proved by the papers.

1. Replication needs a traceable execution and write process; allocation, birth, and permissions still need explicit definitions.
2. Preserve opportunities for replication pathways to change instead of hiding the entire process inside a fixed high-level operation.
3. Treat scheduling, boundaries, placement, reclamation, and mutation as experimental variables.
4. Distinguish copying, heritable variation, differential reproduction, and sustained innovation.
5. Allow stagnation and extinction; enforcing the persistence of an ecological role is not evidence of its emergence.

## Reading and discussion sequence

| Step | Status | Output |
| --- | --- | --- |
| Focused literature review | Complete for this round | Sources, limitations, and open decisions above |
| Tierra and spatial Stringmol mechanism reading | Complete for this round | [Kernel notes](tierra-stringmol-kernel-notes.md), including code comparisons and candidate experiments |
| Research positioning and first-kernel rule discussion | In progress | Selected VM direction; research question and detailed transition rules remain open |
| Delegated C++ implementation and integration | After rule agreement | Implementation, targeted tests, and experimental results |

## Reading scope and cache

The core entries use relevant methods, results, and discussion sections of full-text sources. The 2024 entries refer explicitly to preprint versions. Langton 1984 was checked only at abstract level and is not used for detailed mechanism claims here. This is a focused design review, not an exhaustive literature survey.

See the [reference index](references/README.md) and [cache manifest](references/manifest.json) for local files, source URLs, versions, and verification metadata.

The subsequent [LaTeX field review](review/README.md) covers soft, hard, and wet artificial life with soft systems as its focus. It includes full-text follow-up on Langton 1984, newer frontier studies, and explicit access/version limits. The [research search record](research/README.md) distinguishes completed searches from deferred leads.
