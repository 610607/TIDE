# TIDE Roadmap

TIDE stands for TIDE Is Digital Evolution.

Updated: 2026-11-15.

This roadmap is a plan. Stage contents are proposals until their rules are agreed; [AGENTS.md](../AGENTS.md) records what is decided.

## Goal

Research comes first. TIDE aims to contribute to the study of open-ended evolution in digital-life systems: a rule-driven kernel in which replication strategies and ecological relationships evolve rather than being scripted, with results that others can replay.

An experience layer (observation UI, cards, controller seats for humans, AI, and LLMs) may be built later on a stable kernel interface. It consumes kernel results and does not change kernel rules.

## Main line

| Stage | Content | Exit condition |
| --- | --- | --- |
| RQ Research positioning | Survey the current frontier; map open problems; choose a research question and the claims the kernel must be able to test | A stated research question, with the closest prior work and the expected difference from it |
| R0 Contract | Every instruction as an explicit state transition, including failure cases; permissions, allocation, scheduling, reclamation; parallel-ready constraints (P0) | Each rule agreed and documented |
| R1 Minimal kernel | C++ VM, lattice, scheduler, reclamation, seeded randomness | Bit-for-bit replay from a seed; the ancestor replicates stably without mutation |
| R2 Expressivity | Hand-written programs, no mutation: self-copy, borrowed copy, redirected copy | All three are expressible; CPU owner, instruction source, and data source are traced separately |
| R3 Evolution runs | Mutation on; many seeds in batch; lineage records | Every run reported as survival, stagnation, or extinction; at least one non-ancestral replication strategy observed |
| R4 Measurement | Phylogenies, relationship diagnosis by pairwise replay, open-ended-evolution measures | A run can be characterized without labels or visual inspection |
| R5 Variable experiments | Scheduling, placement, energy, spatial heterogeneity, one at a time; random-origin replicators as a separate experiment | Known sensitivity of results to each rule; evidence for or against the research question |
| R6 Write-up | Replay package (seeds, configurations, kernel revision), analysis, and report | A third party can reproduce the reported results |
| R7 Stable interface | Snapshot, branch, rollback, intervention entry points, event stream | Upper layers need no access to kernel internals |
| R8 Experience layer | Observation UI and controllers | Defined when reached |

RQ and R0 run together: the survey informs the contract, and the contract discussion does not wait for the survey to finish. The research question must be fixed before R3 experiments are designed.

R3 is the largest uncertainty. In studied Tierra configurations, selection can favor short programs, while relaxed parsimony can produce longer programs without increased measured complexity. These are distinct outcomes, not a universal convergence rule; see the [stagnation evidence](research/stagnation-and-measurement.md). After R3, decide explicitly whether to vary rules, add environmental structure, or build a bound-reaction kernel as a comparison.

R4 tooling is needed to read R3 results, so its design starts before R3 runs.

## Performance line

| Step | When | Content | Exit condition |
| --- | --- | --- | --- |
| P0 Parallel-ready contract | Within R0 | Two-phase synchronous update (execute, then resolve conflicts); integer-only state; counter-based randomness keyed by seed, step, and site; fixed-size memory; bounded template search | No rule depends on the order in which sites are visited |
| P1 CPU baseline | After R2 | Single-threaded reference implementation as the oracle; benchmarks; array layout and multithreading | Multithreaded state hashes match the reference at every step |
| P2 GPU backend | After R5, or earlier if R3 is too slow to run | Execute and resolve phases as compute shaders on a cross-platform framework | State hashes match the CPU reference; scale and speed reported |

The GPU backend must be cross-platform. Candidates to compare before P2 include Kompute, direct Vulkan, and native WebGPU implementations. Single-vendor or single-platform APIs are not primary targets. No framework is chosen yet.

Sequential random-order update remains available on the CPU as a comparison mode.

## Literature and project search plan

A bounded first pass of directions F, 3, 4, and 5 was conducted on 2026-11-15; see the [search record and evidence limits](research/README.md). The lists below remain a search plan, not a claim that every named lead was read. Tierra successors and the implementation survey remain deferred. Follow the research-source rules in [AGENTS.md](../AGENTS.md) when continuing.

### Tier 1: before the research question and contract are fixed

| Direction | Question | Leads |
| --- | --- | --- |
| F. Current frontier | What has the field shown since about 2020, what is contested, and where are the open problems? | Recent ALIFE proceedings and *Artificial Life* issues; follow-ups to the Computational Life (BFF) work; open-endedness in AI research; foundation-model-assisted search such as ASAL; continuous and neural substrates such as Lenia, Flow Lenia, and neural cellular automata; recent Avida and Stringmol work |
| 4. Stagnation and remedies | Why does digital evolution stop, and which conditions sustain innovation? | Standish on complexity in Tierra; Soros and Stanley on necessary conditions; Zaman et al. on host-parasite coevolution in Avida; major-transitions work |
| 5. Measuring open-ended evolution | Which measures can report a run, and what are their limits? | Bedau's evolutionary activity statistics; the MODES toolbox by Dolson et al.; Hickinbotham and Stepney on detecting open-endedness |
| 1. Tierra successors | How did others choose instruction sets, permissions, and reclamation, and where did each stagnate? | Network Tierra; Cosmos; Amoeba; Physis; Nanopond |
| 3. Space, scheduling, and parallel semantics | How does spatial structure sustain host-parasite coexistence? What do synchronous and asynchronous updates change? Which update semantics are parallel and replayable? | Boerlijst and Hogeweg; Takeuchi and Hogeweg; asynchronous and block-synchronous cellular automata; counter-based random number generators |

Direction F produces a map of open problems and candidate research questions. The other Tier 1 directions are read with those candidates in mind.

### Tier 2: before implementation and evolution runs

| Direction | Question | Leads |
| --- | --- | --- |
| 2. Existing codebases | Which implementations and engineering practices are worth comparing against? | Tierra source; Avida; the Stringmol repository; `cubff`; ALIEN |
| 6. Spontaneous origin of replicators | How should a random-origin experiment be set up and judged? | Computational Life (read); Rasmussen's Coreworld; Pargellis |

### Tier 3: when the corresponding stage approaches

| Direction | Question | Leads | Stage |
| --- | --- | --- | --- |
| 10. GPU implementation | How do interpreters perform on GPUs, and which cross-platform framework is viable? | GPU implementations of `cubff`, ALIEN, and Lenia; Kompute, Vulkan, and WebGPU documentation and status | P2 |
| 8. Controllers on artificial-life systems | How have models been used as observers, searchers, or interveners? | ASAL; OMNI; quality-diversity search | R7-R8 |
| 9. Product and game precedents | How do evolution-based games handle quiet periods and legibility? | Core War; Creatures; SimLife; Thrive; The Bibites | R8 |
