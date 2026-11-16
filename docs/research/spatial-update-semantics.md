# Spatial Ecology and Replayable Update Semantics

Updated: 2026-11-15. Bounded first pass for RQ/R0; no kernel changes or new experiments.

## Scope and current decisions

The first TIDE kernel is an individual-CPU, local address-based VM. Neighbor reads/fetches, writes to owned allocations, public-space reservation before division, synchronous execute-then-resolve updates, and a CPU random-sequential comparison are the current starting points. [AGENTS.md](../../AGENTS.md) is authoritative; this note does not reopen those choices or promote candidates to requirements.

The research implication is conditional: spatial organization can change selection, but a lattice alone does not establish coexistence. Bit-for-bit replay across implementations and ecological robustness across different update rules are separate claims.

## Primary evidence

### B1. Boerlijst and Hogeweg (1991): spatial protection has a mechanism and limits

Published article: *Physica D* 48:17-28, [DOI](https://doi.org/10.1016/0167-2789(91)90049-F), [institutional PDF](https://www-binf.bio.uu.nl/pdf/Boerlijst.pd91-48.pdf), [cached scan](../references/pdf/boerlijst-hogeweg-1991-spiral-wave.pdf). Local full text read, especially section 2, table 1, sections 3.1-3.4 and 4.1-4.3; printed pages 18-26.

- The model has one molecule or vacancy per site, vacancy-only reproduction, local catalysis, decay, and separate particle-conserving diffusion. Catalytic relationships are predefined; this is not an evolving instruction-level VM.
- Spiral centers seed outward growth. Many parasites expand outward and are removed by later catalytic waves. Center invasion can destroy a local spiral; persistent small parasite regions also occur. This is resistance to a class of parasites, not their universal exclusion.
- Section 3.4 reports that increasing diffusion thickens/enlarges waves over the tested range; zero diffusion can remove protection. It does not establish a universal monotonic benefit of mixing.
- Section 4.1 reports spiral formation under tested asynchronous updates and non-toroidal boundaries. It does not specify enough of that comparison to establish trajectory equality, identical coexistence statistics, or robustness for TIDE.

**Transfer limit:** test spatial growth, loss, and mixing mechanisms; do not import species labels, catalytic rules, or a promise of coexistence.

### T1. Takeuchi and Hogeweg (2009): waves and compartments need not select alike

Published article: *PLoS Computational Biology* 5(10):e1000542, [publisher full text](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000542), [cached PDF](../references/pdf/takeuchi-hogeweg-2009-multilevel-selection-ii.pdf) | [publisher PDF](https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1000542&type=printable). Main-text sections “Replicator Model,” “Analysis of the Surface Model,” and “Discussion” read; detailed supporting algorithms were not audited.

- Empty sites limit reproduction locally and globally. Dynamics choose a random site and apply local reaction/diffusion rules; grid-boundary crossing is forbidden. Replicase and parasite types are predefined.
- In the surface model, replicase escape from a wave front can found a new wave, subsequently reached by parasites. Weaker parasites can increase wave reproduction; limited diffusion supports variation and inheritance among waves. Stronger parasites can also invade regions with excessively weak parasites.
- Both surface organization and compartments can stabilize these replicators, yet their long-term evolutionary trends differ. Therefore, population persistence does not identify a unique evolutionary mechanism or imply equivalent evolutionary outcomes.

**Transfer limit:** these abstract reactions do not establish how CPU ownership, reservation delays, retained bytes, or instruction permissions behave in TIDE.

### S1. Hickinbotham, Stepney and Hogeweg (2021): a closer executable precedent

Published article: *Royal Society Open Science* 8:210441, [DOI](https://doi.org/10.1098/rsos.210441), [cached publisher text](../references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf). Sections 2.1, 3.2-3.3 and 5.1-5.4 read; publication pages 2, 11-14 (the cached PDF adds a cover).

- Replicators invade vacancies at wave fronts and parasites exploit them behind the front. Evolution can alter the duration and control flow of copying; the chemistry is not restricted to a fixed replication-rate parameter.
- Section 5.1 gives one opcode per bound pair per timestep, local reactions, vacancy-dependent product placement, and stochastic decay. A new product becomes available for binding on the subsequent timestep (figure 8). This is pair-owned reaction scheduling, not TIDE's individual-CPU model.
- Section 5.3 diagnoses parasitism by mutation-free reactions in both orientations. This supports treating ecological relations as analysis results, without putting them into physical transition rules.

**Transfer limit:** the paper does not settle TIDE's public reservation lifecycle, conflict arbitration, residual-code permissions, or snapshot visibility.

### U1. Schonfisch and de Roos (1999): the update algorithm is part of the model

Published article: *BioSystems* 51(3):123-143, [publisher record/preview](https://www.sciencedirect.com/science/article/pii/S0303264799000258), [DOI](https://doi.org/10.1016/S0303-2647(99)00025-8).

**Partial access:** the publisher's indexed abstract, introduction, and section previews were available; direct full-text opening returned HTTP 403. No complete proof or table was inspected.

The primary preview distinguishes ordered sweeps, random choice with replacement, and time-driven exponential waiting times. It reports that correlations in update order affect patterns, and that identical stationary configurations can have different attraction basins. Its deterministic local-CA statements must not be generalized to TIDE's stochastic, allocating VM. In particular, a fresh random permutation per sweep and repeated uniform sampling are different processes; “asynchronous” is insufficient specification.

### R1. Salmon, Moraes, Dror and Shaw (2011): random draws can follow logical events

Published SC11 conference paper, 12-page author copy: [DOI](https://doi.org/10.1145/2063384.2063405), [cached PDF](../references/pdf/salmon-et-al-2011-parallel-random123.pdf) | [author PDF](https://www.thesalmons.org/john/random123/papers/random123sc11.pdf). Sections 2, 5.1 and 6 read, especially PDF pages 9-10. The [official repository](https://github.com/DEShawResearch/random123) corroborates provenance; no library/backend choice is made here.

Counter-based generators compute outputs from key/counter inputs without advancing shared generator state. Section 5.1 gives stable object identity plus simulation time as an example, permits seed fields, and warns that improper tuple reuse repeats random values. This supports schedule-independent assignment of draws. It does not supply TIDE's event identifiers, prove ecology is unchanged by a scheduler change, or make nondeterministic state transitions replayable.

## Code observation: the Stringmol mutation ambiguity is only partly closed

The paper's section 2.1 mentions replacement/insertion/deletion; section 5.1 explains replacement. Section 5.2 names software 0.2.3.4. The official [tag ref](https://api.github.com/repos/uoy-research/stringmol/git/refs/tags/0.2.3.4) resolves to commit `aa6c7301822a93b74ad60b46437515ef6804784f` (also verified in `franticspider/stringmol`).

Pinned code inspected on 2026-11-15:

- [`src/setupSM.cpp`, lines 1145-1149](https://github.com/uoy-research/stringmol/blob/aa6c7301822a93b74ad60b46437515ef6804784f/src/setupSM.cpp#L1145): the spatial `=` dispatcher calls `A->hcopy(act)`.
- [`src/stringPM.cpp`, lines 205-225](https://github.com/uoy-research/stringmol/blob/aa6c7301822a93b74ad60b46437515ef6804784f/src/stringPM.cpp#L205): `MUTATE` loads both `subrate` and `indelrate` with the same value; a missing parameter instead uses older hard-coded rates.
- [The same file, lines 2044-2087](https://github.com/uoy-research/stringmol/blob/aa6c7301822a93b74ad60b46437515ef6804784f/src/stringPM.cpp#L2044): the valid-copy path selects indels first, splits insertion/deletion with another draw, otherwise tests the substitution interval. Pointer advances differ between branches; this is more specific than an abstract genome-level indel operator.
- [`config/spatial_stringmol_v1.2.2.conf`](https://github.com/uoy-research/stringmol/blob/aa6c7301822a93b74ad60b46437515ef6804784f/config/spatial_stringmol_v1.2.2.conf) contains `MUTATE 0.0002`. It is a repository example, not verified as the configuration of all twenty published runs.

**Established:** the specified release's spatial copy path supports built-in indels as well as substitution. **Still open:** the exact per-run configurations/restarts and substitution distribution used in the reported dataset. The [dataset DOI](https://doi.org/10.15124/305dfdb6-9483-4c5b-8a01-c030570b9c31) did not open through the web tool. No software was built or executed; do not report the exact published mutation mix as resolved.

## R0 questions within the agreed two-phase default

The following are engineering proposals/questions, not literature results or agreed rules. Each eventual rule needs an explicit transition and failure effects.

| Contract surface | Exact point still to settle | Minimal diagnostic |
| --- | --- | --- |
| Execution granularity and reads | One opcode or a bounded slice per phase? Do neighbor data/fetch reads always see the step-start snapshot? Do own writes forward to later instructions in the same slice? Are partially copied reserved bytes readable/fetchable? | A writes a distinguishable byte while B reads/fetches it; reverse traversal and worker order. |
| Allocation result | When is success reported to the CPU? Can it copy into a newly won reservation in the same step? On loss, specify IP, status, pointers, existing reservation, and spent slice. | Two allocators target one vacancy and inspect both post-resolution CPU states. |
| Conflict arbitration | Define contenders, eligibility, total priority including ties, and whether one request can win multiple targets. A fixed site priority is reproducible but may introduce spatial bias. | Symmetric contenders under reflections/rotations and multiple thread partitions. |
| Reservation lifecycle | Does reservation survive a failed divide, parent death, timeout, or a second allocate? When does release become available to contenders? Can a request use a site released in this same resolution? | Allocate, wait, fail divide, die; account for every site and retained byte at each boundary. |
| Division and newborn activation | Specify when ownership/CPU identity changes, first instruction eligibility, and registers/pointers. Is a child committed at step t first eligible at t+1? What if the parent dies in the same step? | Child increments a counter on its first instruction; log birth-to-first-execution delay. |
| Residual bytes and reuse | Death removes the CPU under the working default but leaves bytes. Specify byte validity, read/fetch permissions, length metadata, and the effect of later reservation/overwrite at that address. | Kill a code provider, retain bytes, then reserve and overwrite one byte; trace CPU owner versus instruction/data source. |
| CPU comparison mode | Specify fresh permutation versus sampling with replacement, eligible cohort, immediate visibility, newborn handling, and the unit of reported time/budget. | Count actual instructions and repeat visits; use equal execution opportunities before comparing ecology. |
| Boundaries and placement | Specify neighborhood geometry, edge addressing, vacancy selection, failed placement, and whether neighborhood changes are separate from scheduling changes. | Small edge/corner worlds and a nearly full neighborhood. |

Candidate names for experimental controls are `execute_quantum`, `shared_read_visibility`, `conflict_priority`, `reservation_release`, `newborn_activation`, `residual_read_policy`, `update_mode`, `boundary_mode`, and `offspring_placement`. Their values and failure transitions remain to be agreed; these names do not define a public API.

Candidate implementation discipline: compute intents from an explicitly defined view, then resolve each contested target with an order-independent reduction over a fully specified priority. Hardware arrival order must not choose winners. If resolution needs multiple subphases (release, reserve, divide), their precedence is itself part of the model. This is compatible with two phases at the public contract level only if the resulting transition is unambiguous.

Candidate accounting invariant: every site is exactly live, reserved, or available; available sites may retain non-executing bytes. Treat this as a proposed bookkeeping partition, not a new state schema. A reservation occupies public space without creating another CPU. Failed operations must not silently duplicate or lose sites, ownership, or execution opportunities.

## Random-event identity and replay

P0's `seed, step, site` is a starting coordinate, not yet a complete random-event contract. A candidate logical tuple is `(seed, step, phase, site, event_kind, event_ordinal, draw_or_retry_index)`, packed injectively into a specified key/counter representation. Separate mutation, decay, placement, arbitration, and comparison-scheduler events; never use worker ID, thread order, or an incrementing global call count.

Settle whether randomness attaches to the site or to a persistent individual identity when sites are reused. Add identity only if multiple distinct events could otherwise share a tuple, or if individual-attached coupling is desired; define identity creation without traversal dependence. Multiple instructions, multiple copy attempts, vector-output lanes, and rejection-sampling retries all need distinct coordinates. Specify counter widths, overflow behavior, generator/version/rounds, integer-to-probability mapping, and bounded-choice sampling. Checkpoint all logical coordinates required to resume.

Replay acceptance: identical initial state, seed, configuration, rules version and RNG mapping produce identical canonical state hashes at every step, across CPU traversals and later parallel backends. Hash the complete future-relevant state, including reservations, residual bytes, CPU state, identities and counters; define serialization instead of hashing struct padding. No replay check has been run here.

Ecological comparison: synchronous and random-sequential modes intentionally define different transition processes. Neither equal seeds nor matching mean population counts prove ecological equivalence. Compare distributions over declared seeds, including extinction, stagnation, coexistence duration, spatial correlations, births, reservation failures/durations, and actual instruction budgets. Match a justified time/budget scale and report remaining differences rather than force hash equality between these modes.

## Minimal discriminating experiments (proposed, not run)

1. **Visibility and activation:** mutation off, two/three fixed programs, distinguishable bytes and first-instruction markers. Vary only the proposed visibility or activation rule. This tests semantics before ecological interpretation.
2. **Reservation competition:** mutation off, ordinary replicator versus allocate-and-delay program; separately vary release/timeout behavior and arbitration. Measure denied allocations, reserved-site time and births; do not combine with a placement change.
3. **Residual-code dependence:** mutation off, a borrower and provider; kill the provider, then overwrite its unowned location in a separate treatment. Trace execution owner, fetched source, copied source and products.
4. **Scheduling sensitivity:** once the ancestor is stable, compare the agreed synchronous default with the fully specified CPU comparison at matched instruction budgets. Use spatial snapshots plus numerical pattern measures; report every seed, not only surviving waves.
5. **Spatial mechanism:** hold scheduler/mutation/death fixed and change one of neighborhood range, placement range, boundary condition, or mixing. Retain the VM's permission/locality contract. Evidence for coexistence must include failed invasions and extinctions, not a selected attractive pattern.

B1/T1 motivate experiment 5; U1 motivates experiment 4; S1 motivates explicit timing/traces. None predicts that these programs or future evolved populations will coexist in TIDE.

## Search record and screening

Search/access date: **2026-11-15**. Existing manifest and cached Stringmol full text were checked first. Web search was used for primary discovery and official repositories for the bounded code check. Exact query strings (including unproductive searches):

```text
Boerlijst Hogeweg 1991 Spiral wave structure pre-biotic evolution hypercycles pdf
Takeuchi Hogeweg 2009 multilevel selection models prebiotic evolution parasites spatial pdf
Schönfisch de Roos 1999 Synchronous asynchronous updating cellular automata pdf
Salmon Moraes Dror Shaw 2011 Parallel random numbers as easy as 1 2 3 pdf
site.tbb.bio.uu.nl Boerlijst Hogeweg 1991 spiral pdf
site.desres.com random123 pdf 2011
"Synchronous and asynchronous updating" "pdf" "de Roos"
"Spiral wave structure" "pdf" Boerlijst Hogeweg
"Synchronous and asynchronous updating in cellular automata" pdf -site:academia.edu -site:researchgate.net
"Parallel random numbers" "deshawresearch" pdf
Hickinbotham Stringmol 2021 v0.2.3.4 github mutation
"Boerlijst" "Hogeweg" "90049" pdf
"Spiral wave structure in pre-biotic evolution" Utrecht
"Schönfisch" "de Roos" 1999 site:uva.nl
"Synchronous and asynchronous updating" site:jcasim.de
"Boerlijst.pd91-48.pdf"
"Synchronous and asynchronous updating in cellular automata" author fulltext
```

Included five primary papers above: four with relevant full-text sections read, U1 with explicitly partial primary access. Boerlijst's institution initially returned 502 through the web tool; the parent subsequently cached the original and its local text was read. Takeuchi's publisher PDF endpoint was verified (17 pages); Salmon's author PDF was opened (12 pages). Cached-file metadata/hashes belong in the parent-maintained manifest.

Screened but not used for research findings: the separate Boerlijst/Hogeweg *Artificial Life II* chapter (overlapping lead, not substituted for the journal article); JCASim's 2000 implementation note (useful terminology, not a substitute for U1's full proof); Fatès' asynchronous-CA survey and Nehaniv's emulation leads (review/theory follow-up, outside this pass); Caron-Lormier et al.'s individual-based-model comparison (additional model family, deferred); third-party mirrors, encyclopedias and aggregators (discovery only). Random123's official repository was provenance/context, not an extra empirical source. No GPU framework survey was performed.

Open evidence work: retrieve U1's authorized full text; audit Stringmol's archived per-run configs and restart handling only if exact mutation parameters matter to a proposed comparison; specify R0 rules with the user before implementation. No claim of exhaustive literature coverage or of executed TIDE results is made.
