# TIDE Roadmap

TIDE stands for TIDE Is Digital Evolution.

Updated 2026-11-23.

This roadmap is a plan. Stage contents are proposals until their rules are agreed; [AGENTS.md](../AGENTS.md) records what is decided.

The first C++ reference can separate neighbor instruction fetch from data copying. A longer paired assay confirmed heritable fetch dependence in 7 of 32 prospectively tested seeds. Tracing all 37 exposed births in the read arm showed that the daughters lost their mothers' reader sequence. All eight confirmed prospective same-genome families ended by field tick 713. A retrospective lineage retained fetch dependence across a point substitution. Across 256 new read-only seeds, no newborn reader encountered a compatible live neighbor during its first-copy window. In a seeded field, proximity and residual bytes enabled up to seven reader transmissions. [Transmission study](../kernel/runs/transmission-01/README.md) [Measurement and replay](../kernel/runs/horizon-01/README.md)

The exploratory substrate series pauses at v31. Its paired runs showed that extra material improved replication while strict sites continued to decline. A lineage that requires a neighbor could fail the isolated replication assay used in those runs. [v31 results](../experiments/physub/runs/v31/README.md)

## Goal

Research comes first. TIDE aims to contribute to the study of open-ended evolution in digital-life systems: a rule-driven kernel in which replication strategies and ecological relationships evolve rather than being scripted, with results that others can replay.

An experience layer (observation UI, cards, controller seats for humans, AI, and LLMs) may be built later on a stable kernel interface. It consumes kernel results and does not change kernel rules.

## Next milestones

**Agreed first question.** Starting from an independently reproducing ancestor, can a descendant lineage evolve a heritable dependence on reading a neighbor's data or fetching its instructions? The kernel must allow the two channels to be tested separately. [RQ brief](research/neighbor-dependence-rq.md)

| Milestone | Work | Evidence for moving on |
| --- | --- | --- |
| RQ and R0 | Implemented the first question as two separate access interventions. The contract defines each instruction, failure paths, scheduling and the space ledger. | [Research brief](research/neighbor-dependence-rq.md) · [VM v1](r0-kernel-contract.md) |
| R1. CPU reference | The C++ reference replays from a seed. Reversing the traversal order preserves the full serialized state at every step of a 512-tick test. | [Reference tests](../kernel/tests/vm_tests.cpp) |
| R2. Measurement | Fixed programs reproduce independently, by reading a neighbor, and by running a neighbor's instructions. A redirected-copy fixture produces the provider's program. | [Fixed-program tests](../kernel/tests/vm_tests.cpp) |
| R3. Bounded pilot | Completed 24 runs. In one fetch seed, a field mother and daughter met the predeclared serial-replay criterion. No read seed met it. | [Protocol, records and replay](../kernel/runs/pilot-01/README.md) |
| R3. Independent replication | Ran seeds 9–32 with the same rules and assay. Eleven fetch seeds produced candidates. None met the frozen confirmation rule. | [Independent results and every candidate](../kernel/runs/replication-01/README.md) |
| R4. Resolve measurement uncertainty | A 4,096-tick replay resolved all 16 previously timed-out replication events. A prospective 32-seed test confirmed seven fetch seeds. Six of its eight confirmed maternal families disappeared by tick 512. | [Every event, seed and family](../kernel/runs/horizon-01/README.md) |
| R4. Trace data-read transmission | In 37 exposed births the mother copied five neighbor bytes and produced a daughter with a different sequence. A matched live-donor comparison showed that changing one donor byte can transmit read use across three generations. | [Read paths and controlled replay](../kernel/runs/horizon-01/README.md#why-the-observed-data-reads-stopped-at-one-generation) |
| R4. Follow field families | Continued the seven affected prospective worlds to tick 4,096. All eight confirmed same-genome families died out. Matching genomes reappeared independently in four worlds. | [All checkpoints and family outcomes](../kernel/runs/persistence-01/README.md) |
| R4. Behavioral persistence and spatial opportunity | Verified one historical changed fetch lineage. Of 330 engineered single substitutions, 215 retained dependence in their founder backgrounds. In 256 new read-only fields, zero of 143 newborn readers saw a compatible live neighbor through the first-copy window. | [Pedigrees, sequence panel and spatial census](../kernel/runs/transmission-01/README.md) |
| R5. First one-variable field comparisons | Varied one byte per donor layout, then changed reclamation. A seeded reader family reached seven transmissions with retained bytes and four in the same layout with cleared bytes. Traces identified a parent reading residual code from its own daughter reservation. | [Controlled field outcomes](../kernel/runs/transmission-01/README.md#donor-supply-and-residual-memory) |

The pilot's budget, five-byte ancestor and substitution-only mutation restrict the interpretation. A remaining question is which spatial conditions bring independently arising readers and compatible banks together often enough for serial transmission.

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

Sequential random-order update is planned as a CPU-only comparison.

## Verification line

The verification proposal was assessed on 2026-11-17. Revisit it once a rule has stabilized. Adopting it would add a formal model above the C++ code and requires a separate decision. The single-threaded C++ implementation is the designated reference, as AGENTS.md records.

| Step | When | Content | Exit condition |
| --- | --- | --- | --- |
| V0 Pilot | When one rule has settled, for example field diffusion | Executable Lean 4 model of one rule; proofs of conservation, non-negativity, and independence from site visit order; differential test against the C++ code on random small lattices | Proofs check; outputs match; effort recorded; decision whether to use Lean for R0 |
| V1 Executable contract | Within R0, if V0 is adopted | Lean model of each agreed transition. Total functions with exhaustive cases force a defined effect for every invalid operand and failed operation. Theorems for conservation, locality, and order independence (the P0 exit condition) | Every agreed rule has a model; its properties are proved for all lattice sizes |
| V2 Differential testing | From R1 | Random configurations run on the Lean model and the C++ reference; state hashes compared | No mismatch over a stated test budget |
| V3 Parallel models | With P1 and P2 | TLA+ models of the multithreaded and GPU execute and resolve phases: barriers, atomics, conflicting writes; model-checked on small instances | Every modeled schedule yields the reference result |

Why Lean before TLA+: a kernel step is a deterministic function of state, and the two-phase synchronous update removes interleavings. Lean models such a function directly, runs as a differential-testing oracle, and proves properties for every lattice size. TLA+ is strongest for interleavings and temporal properties; its model checkers cover small instances only. Those concerns arise with real concurrency in P1 and P2.

Costs and limits:

- Learning the tool and maintaining proofs cost effort, and every rule change can break proofs. This is the reason to wait until rules settle.
- Integer semantics must be explicit; C++ signed overflow is undefined behavior.
- Differential testing samples inputs. It does not prove that the C++ code agrees with the model on every input.
- A machine-checked proof removes the need to trust whoever wrote it, human or agent, but not the theorem statement. Statements need human review.

Precedents:

- Cedar uses verification-guided development: an executable Lean model with proofs, and differential random testing against the Rust implementation. Disselkoen et al., [How We Built Cedar: A Verification-Guided Approach](https://arxiv.org/abs/2407.01688), arXiv:2407.01688, preprint.
- TLC can check recorded implementation traces against a TLA+ specification. Cirstea, Kuppe, Loillier, and Merz, [Validating Traces of Distributed Programs Against TLA+ Specifications](https://arxiv.org/abs/2404.16075), SEFM 2024, LNCS; read as arXiv:2404.16075v2.

A brief search on 2026-11-17 found no machine-checked proofs of a digital-life kernel; the search was not exhaustive.

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
