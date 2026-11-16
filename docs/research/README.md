# Research Search Record

Updated: 2026-11-15.

This directory records bounded literature passes informing research positioning (RQ) and the kernel contract (R0). It extends the [initial literature review](../alife-literature-review.md). Current project decisions live in [AGENTS.md](../../AGENTS.md); literature findings do not change them automatically. The second pass below is design input only: it does not assess novelty or extend the deferred successor/horizontal-transfer survey.

## First-pass repository inspection (historical)

- Inspection baseline: `main`, commit `9f5426226dddcb130e0b6dbb24c7efcc0025586b`; the working tree was clean before this pass. Local remote-tracking state matched `origin/main`; no remote fetch was performed.
- Tracked deliverables are documentation, research metadata, project instructions, and the license. The new C++ kernel, build target, and tests do not exist yet.
- `prototype/` remains an ignored local reference. Its behavior is not the specification for the fresh kernel. No prototype build or runtime test is needed for this documentation and literature pass.
- Eight cached PDFs were present; all eight SHA-256 hashes matched the manifest. PDFs remain ignored by Git.
- The earlier review still called the VM choice and synchronous scheduling undecided. Its status text has been reconciled with current project instructions; the detailed instruction contract remains open.

## First-pass execution checklist (historical)

| Step | Status | Evidence or exit condition |
| --- | --- | --- |
| Inspect repository, decisions, and cache | Complete | Baseline and cache check above |
| Search and read three independent literature streams | Complete for this pass | Three reports below, with explicit evidence limits |
| Review findings, integrate references, and write the requested LaTeX review | Complete for this pass and the illustrated follow-up | Checked claims, cached public PDFs, updated metadata, compiled and reviewed the 21-page manuscript with five figures |
| Prepare the next RQ/R0 discussion | Complete for this pass | Candidate questions and remaining gaps below; the RQ and instruction contract still require discussion |

## First-pass assignments

All three agents use `gpt-6.1-sol` with `xhigh` reasoning. Each owns one report; only the coordinating agent edits shared documentation and reference metadata. Each stream targets three to five primary works. Public PDFs for included works are cached when retrievable; failures are recorded separately rather than represented as cached files.

| Agent | Roadmap directions | Question | Owned report |
| --- | --- | --- | --- |
| `/root/rq_frontier` | F | What recent results change the questions a local digital-life VM should test? | [Frontier](frontier.md) |
| `/root/rq_measures` | 4 and 5 | What distinguishes sustained adaptive innovation from diversity or turnover, and how can stagnation be measured? | [Stagnation and measurement](stagnation-and-measurement.md) |
| `/root/rq_spatial` | 3 | How do spatial structure and update semantics affect coexistence, and which unresolved rules need controls? | [Spatial update semantics](spatial-update-semantics.md) |

Separate from the literature streams, [a shared-memory probe](coreworld-shared-memory-probe.md) records executed exploratory runs on an untracked prototype VM. It examines which failures appear without write protection.

The requested follow-up [compares those failures with original Coreworld, Tierra, Avida, and Stringmol methods](shared-memory-prior-work.md). A [read-only audit](probe-output-audit.md) of 140 stored output files found 130 distinct seed/configuration tuples and corrected the probe's counting, metric definitions, death attribution, and incomplete-digest claims. The illustrated review includes a separate appendix plotting all ten mutation-on records from the ownership comparison; no new simulations were run for it.

Tierra successors (direction 1) and the full implementation survey (direction 2) are deferred. The first pass does not exhaust Tier 1. GPU frameworks, controllers, and product precedents remain later-stage work.

## Evidence and integration rules

1. Search original papers, author or institutional repositories, and official code. Record query strings and search date. Recent work is checked against accessible versions, not inferred from a title or search snippet.
2. Separate full-text findings, abstract-only leads, code observations, and project proposals. Record the relevant section and limitations; do not invent printed page numbers.
3. Reuse cached PDFs before downloading. Preserve downloaded bytes; record the version, URL, date, page count, size, and SHA-256. Public availability does not establish a redistribution license.
4. Do not infer open-endedness from visual complexity, changing genotypes, or finite survival. Distinguish externally guided search, spontaneous replicator origins, and evolution after a supplied ancestor.
5. Candidate research questions need the closest prior work, a discriminating experiment, observable outcomes, and a plausible falsifying result. A difference from an example paper is not proof of novelty across the field.
6. Integrate only after checking evidence and scope. No kernel implementation, contract changes, simulations, commits, or remote operations are part of this pass.

## R0 questions the search should inform

- Which snapshot supplies instruction fetch and data reads during a synchronous step?
- How are competing allocations resolved, and what state does a failed operation leave?
- When does an offspring gain a CPU, and when are abandoned reservations reclaimed?
- How are residual bytes read after ownership ends or a site is reused?
- Which mutation operators and event identities make comparisons replayable?
- Which observations distinguish a new replication strategy from neutral sequence turnover?

These remain discussion questions. The chosen synchronous default is not evidence that it is ecologically equivalent to sequential updates.

## First-pass integrated recommendation (historical)

Prioritize the candidate question: **How do local data-reading and instruction-fetch permissions affect the appearance and persistence of functionally distinct replication strategies after a supplied ancestor?** Tierra and spatial Stringmol are close precedents. A targeted successor/horizontal-transfer search is still required before claiming novelty.

Use mutation-free expressivity checks before evolution runs. Keep genome novelty separate from replay-defined strategy novelty, and compare permissions one dimension at a time. A viable ancestor must exist in each relevant control. Continued sequence turnover with unchanged replication behavior is a possible negative result, not an implementation failure.

Retained unowned code is a second candidate mechanism; scheduler/conflict-policy sensitivity is a robustness question. Neither is a new agreed rule. The immediate R0 discussion should settle execution granularity, snapshot visibility, allocation failure effects, and newborn activation before C++ delegation.

## Requested field review

The user expanded the deliverable to a broad English LaTeX review of soft, hard, and wet artificial life, with **soft artificial life as the emphasis**. [Review sources and build instructions](../review/README.md) link the compiled artifact, bibliography, and evidence receipts. Additional subagent reading supplied CA foundations and the hard/wet comparison chapters; a separate read-only review checked scientific distinctions and citation coverage.

The first pass did not exhaust the roadmap's literature agenda. The requested second pass below now takes priority; Tierra successors and the verified-but-unread 2024 MODES assessment remain deferred. Kernel implementation remains a later task under an explicit contract.

## Second pass: emergent, graded boundaries

Requested 2026-11-15. The discussion direction is that different interaction channels may acquire different permeabilities, possibly constructed and maintained at a cost. Boundaries and replication structure should be investigated as emergent properties. Candidate option B retains execution threads and per-site ownership as supplied primitives while leaving body extent, shape, territorial division, and multi-thread grouping open to evolution. These are design candidates, not changes to the decisions in `AGENTS.md`.

Three independent agents use `gpt-6.1-sol` with `xhigh` reasoning. Only the coordinator edits the shared reference index, manifest, synthesis, and LaTeX review. The included primary-work budget is A: six, B: five, C: four, at most fifteen total; screened leads are recorded separately. Official documentation or code used to clarify a selected work is identified by version and does not silently introduce another experimental paper.

| Step | Status | Scope |
| --- | --- | --- |
| Verify context and allocate the bounded corpus | Complete | Existing decisions, local cache, and file ownership checked |
| Search/read primary sources in three streams | Complete | Six + five + four primary works; screening kept separate |
| Integrate evidence, cache records, and review additions | Complete | Thirty-nine cached PDFs; fifteen-work synthesis; proposals remain distinct |
| Compile, render, and validate deliverables | Complete | Twenty-six pages, six figures, forty-four references; standalone rebuild and source hashes checked |

No simulations, kernel changes, commits, or Git remote operations belong to this pass. Historical claims, code observations, and candidate TIDE transitions are reported separately.

The three completed reports are [boundaries and permeability](boundary-permeability.md), [conservation and groups](conservation-and-groups.md), and [individuality measures](individuality-measures.md). Each records queries, versions, sections read, explicit mechanisms, failure effects, replay constraints, excluded leads, and open R0 questions. The [English review](../review/README.md) integrates them in its new boundary/individuality section with an original Python schematic. Eleven PDFs were added to the existing twenty-eight-file cache, including two screened-only works; unavailable versions and recovered alternatives are recorded in the [access ledger](../references/unavailable.md).

## Cross-stream design implications (second pass)

**Graded, buildable boundaries.** Separate boundary assembly, selective interaction laws, and evolution of their local realization. Prior systems often supply catalysts, bonding, species mobility, reaction eligibility, or ancestor structures. A TIDE candidate is ordinary local state whose construction, damage, decay, and repair modify explicitly named channels: writing, damage, reading, instruction fetch, material, and signal. “Graded” must mean a declared capacity, rate, resistance, latency, coefficient, or probability. A membrane's material selectivity does not determine VM access. Direct neighborhood sensing also does not imply path-dependent attenuation or occlusion. Protection/intake/perception tradeoffs follow only from specified coupling, not from drawing an enclosure. See [A](boundary-permeability.md).

**Conservation.** Select the conserved quantity and unit before adding costs. Replenished execution credit, scheduling weight, finite space, and transported mass are different constraints; neither Stringmol's 2010 energy gate nor its 2021 space limit conserves copied symbols. A candidate ledger includes free, in-transit, and embodied amounts plus named sources/sinks. Every accepted transfer pairs debit and credit; construction/release, rejected operations, decay, caps, overflow, and rounding need explicit treatment. Simultaneous intents must not spend the same stock twice. Continuous conservation arguments and deterministic seeds do not establish exact integer accounting. See [B](conservation-and-groups.md) and [A](boundary-permeability.md).

**Group transitions.** Option B keeps primitive threads and site ownership supplied while allowing body extent, geometry, and cooperation to vary. DISHTINY shows why given IDs, recognition, controller counts, aging, and reward machinery must be distinguished from evolved behavior. Its even-inflow controls retain much of that machinery. TIDE need not add a group object: creation/death, capture/release, exchange, and local founding can be primitive transitions, with group reproduction assessed afterward. If join/leave/fission operations are proposed, define what moves, who activates, which claims persist, and what failure or conflict does. Geometric fragmentation, shared ancestry, and reproductive independence are different events. See [B](conservation-and-groups.md).

**Label-free measurement.** Keep analyst labels out of physical privileges and rewards, while making observer choices explicit. Candidate generation, scoring, and causal validation are separate tasks. Record channel attempts, opportunities, outcomes, provenance, and actual amounts; zero observed crossings alone do not establish low permeability. Information scores require partitions, lags, estimators, and size regularization. Chemical closure requires a defined reaction universe; observed logs cannot prove that unobserved reactions are impossible. BFF supplies a finite copying assay, not a general body detector. Replay can support alternative analyses, but counterfactual claims need separately authorized interventions. Preserve multiple plausible extents rather than force one border. See [C](individuality-measures.md).

The [R0 design options](../r0-design-options.md) note lists each open decision with the trade-offs of its alternatives, without defaults.

These are design inputs, not accepted requirements. R0 still needs to settle state units, snapshot visibility, arbitration, resource and ownership failure effects, newborn activation, and replay identity. This pass neither selects parameters nor establishes that the candidate rules will produce emergent individuality.
