# R0 design options: execution, boundaries, conservation, and measurement

Drafted 2026-11-15. Status: **discussion document**. It lists decision points for the R0 kernel contract and the trade-offs of each option. It deliberately names **no defaults and no recommendations**. Nothing here changes the "Decided" list in [AGENTS.md](../AGENTS.md); an option becomes a rule only after the user agrees to it.

## Scope and fixed constraints

The user's design intent, which is a direction and not a rule:

- individual boundaries and replication structure should emerge rather than be imposed by the kernel;
- physically meaningful rules (conservation, leakage, local propagation) may make boundaries more likely to emerge;
- a boundary is graded, not 0/1, so that organisms can interact with their surroundings at several levels, including perception.

Options below must stay compatible with the decided items in AGENTS.md:

- a local address-based VM, in which each individual owns its CPU;
- copying moves a byte from a read pointer to a write pointer;
- allocation occupies lattice space before division;
- the update is two-phase and synchronous;
- no ecological labels in kernel state;
- evolution starts from a supplied ancestor;
- replay is deterministic and bit-exact.

Where an option strains one of these, that is listed as a cost.

The kernel's hard acceptance criteria also apply to every option: specified failure effects, a traceable source and sink for every conserved unit, locality, and bit-exact replay.

Evidence sources:

- [boundaries and permeability](research/boundary-permeability.md) (A);
- [conservation and groups](research/conservation-and-groups.md) (B);
- [individuality measures](research/individuality-measures.md) (C);
- [shared-memory prior work](research/shared-memory-prior-work.md);
- [the shared-memory probe](research/coreworld-shared-memory-probe.md).

Probe results come from an untracked prototype. They are exploratory, not specification.

## Decision map

| ID | Decision | Depends on |
| --- | --- | --- |
| D1 | Where the individual comes from | — |
| D2 | Ownership and territory | D1 |
| D3 | Reproduction transition | D1, D2 |
| D4 | Boundary representation | D1, D2 |
| D5 | Meaning of "graded" | D4 |
| D6 | Channels present in R0 | D4 |
| D7 | Conserved quantity | — |
| D8 | Material transport | D7 |
| D9 | Boundary cost and maintenance | D4, D7 |
| D10 | Perception and signals | D6 |
| D11 | Death | D7 |
| D12 | Fate of dead bytes and abandoned claims | D2, D11 |
| E1–E8 | Execution semantics | D1–D3 |
| M1 | Observation and logging | D6 |

D1, D4 and D7 constrain most of the others. Settling them first reduces the option space of the rest.

---

## Part D: structure, boundary, and resources

### D1. Where the individual comes from

**D1-A. Individual given.** One CPU owns one contiguous allocation. The body is that allocation, and division creates a new CPU and body. This follows the Tierra pattern.
- Pros:
  - closest to the decided VM and the supplied-ancestor plan;
  - well-studied precedents (Tierra, Avida);
  - simplest contract, conflict rules and replay;
  - ancestors are easy to write.
- Cons:
  - the boundary is fixed by the kernel, so its emergence cannot be studied;
  - "graded boundary" reduces to permission settings on a given body;
  - multicellular or group structure can appear only as an analysis-level relation among separate CPUs.

**D1-B. Threads and site ownership given; body extent evolves.** Execution threads and per-site ownership are primitives. A thread or a set of threads may own many sites. Body size, shape, territorial division and multi-thread cooperation are left to evolution. Reports A (C5) and B call this candidate option B.
- Pros:
  - keeps a supplied ancestor and an explicit VM;
  - the body's spatial extent, layout, and any constructed barriers can vary and evolve;
  - groups need no group object;
  - compatible with label-free analysis (report C).
- Cons:
  - "each individual owns its CPU" must be reinterpreted as "each thread has a CPU"; "individual" then becomes an analysis concept;
  - new transitions (thread creation, ownership capture, release and transfer) each need failure semantics;
  - more conflict cases arise;
  - ancestors are harder to write;
  - DISHTINY shows that much of the apparent group structure can come from supplied scaffolding, so claims need careful controls.

**D1-C. Fully emergent.** No given threads or owners: BFF-style programs on a tape, or a Lenia/Flow-Lenia field.
- Pros:
  - the strongest claim about emergence;
  - nothing individual-shaped is built in.
- Cons:
  - conflicts with several decided items: the local VM with CPUs, allocation before division, and the supplied ancestor first;
  - Flow-Lenia gives no distinct membrane, and parameter domains are not individuals (report A6);
  - BFF has no spatial bodies;
  - individuals are hard to measure (report C);
  - effectively a different project stage.

### D2. Ownership and territory (relevant if D1-B)

**D2-a. Ownership per site, owner = thread.**
- Pros:
  - simple;
  - every write check is local.
- Cons:
  - when a thread dies, its sites need a rule (see D12);
  - cooperating threads cannot share a site unless ownership can be transferred.

**D2-b. Ownership per site, owner = a lineage key inherited at thread creation.** Several threads share ownership through common descent.
- Pros:
  - a multi-thread body can share writable territory without explicit transfers.
- Cons:
  - the key is exactly the kind of supplied scaffold DISHTINY uses;
  - it risks acting as a hidden group label with physical effect;
  - kin cooperation becomes a default rather than an evolved behavior.

**D2-c. No persistent ownership; access depends only on local material or boundary state** (see D4-c).
- Pros:
  - the closest to physics-like rules;
  - a boundary is whatever local state blocks access.
- Cons:
  - the decided "writable allocations are explicit" needs reinterpretation;
  - the probe found replication fidelity of about 20–29% without write protection;
  - protection must then come entirely from constructed state, which a supplied ancestor would have to build.

### D3. Reproduction transition

**D3-a. Allocate, then divide.** As decided: reserve a block, copy into it, and a divide instruction creates a new CPU or thread there.
- Pros:
  - decided pattern;
  - well understood;
  - competition for space happens during replication.
- Cons:
  - under D1-B the newborn's body equals the allocated block, so the body shape is partly given by the allocation instruction's form.

**D3-b. Spawn a thread inside one's own territory, then separate.** Creating a thread does not create an offspring. Reproduction is a later transfer or split of territory.
- Pros:
  - distinguishes growth (more threads, one body) from reproduction (territory splits);
  - permits multicellular-like development.
- Cons:
  - two transitions instead of one, each with failure semantics;
  - "split" needs a local definition: who goes where, and what happens to a disconnected region;
  - fragmentation is not reproduction (report B), so analysis must separate the two.

**D3-c. Local founding.** A thread can start a new thread on an adjacent unowned site, which it then claims.
- Pros:
  - minimal;
  - fully local;
  - resembles propagule founding.
- Cons:
  - without a construction requirement, it repeats the probe's spawn-loop failure: CPUs created with almost no copying;
  - needs an eligibility gate (cf. Avida `h-divide` checks, Tierra movement counts), and that gate is itself a design choice.

**D3-d. Multi-site somatic growth with single-site propagule budding.** A single thread may claim multiple adjacent sites as somatic territory during its lifetime, while `divide` transfers ownership of only one prepared target site to a newborn thread. The offspring begins as a single-site juvenile and must grow any larger territory itself.
- Pros:
  - keeps `divide` local and single-site, avoiding arbitrary multi-site graph-splitting rules and fragmentation ambiguity (`D3-b`);
  - introduces a developmental life cycle (unicellular bottleneck to multi-site body) using only thread and per-site ownership primitives (`D1-B`, `D2-a`);
  - requires no group ID or hereditary kin key (`D2-b`).
- Cons:
  - rules out direct binary fission of a multi-site body in one transition;
  - parent death still requires a reclamation rule across all of its somatic sites (`D12`).

Related sub-choice, the **division eligibility gate**:
- none;
- allocation fully written (distinct addresses);
- a write count;
- a minimum executed fraction (Avida).

Trade-offs:
- stricter gates block empty or degenerate offspring but encode the designer's notion of a "complete" copy;
- weaker gates allow degenerate spawn strategies;
- write counts can be satisfied by rewriting one address ([prior work](research/shared-memory-prior-work.md)).

Related sub-choice, **fate of unwritten offsets in an allocated child site** (distinct from requiring fixed-size full coverage, so shorter replicators or indels remain expressible):
- clear or mark inert on allocation, or truncate valid code at `divide` to offsets written during the current reservation (prevents zero-write `divide` from reviving pre-existing dead code without imposing a fixed byte-count quota);
- retain pre-existing residual bytes unless overwritten (permits sequence scavenging or chimera formation, but reopens zero-copy corpse activation if `divide` has a weak gate; see [prior work](research/shared-memory-prior-work.md)).

### D4. Boundary representation

**D4-a. Global binary permission per channel.** A configuration switch such as `write=own|any`.
- Pros:
  - trivial to implement;
  - matches the probe's endpoints;
  - clean one-variable comparisons.
- Cons:
  - not graded;
  - not constructible or evolvable;
  - uniform across the world.

**D4-b. Per-site, per-channel integer strength.** Each owned site carries a small integer per channel, set by instructions.
- Pros:
  - directly expresses "graded" and "channel-specific";
  - local;
  - integer-exact;
  - can evolve through the instructions that set it.
- Cons:
  - the per-channel split is a designer abstraction; the literature supports channel-specific selectivity only for material (report A);
  - more state per site;
  - strength values become an evolvable "shield" field, close to the forbidden role/shield vocabulary unless their meaning is purely physical (resistance or cost).

**D4-c. Material-mediated.** Barrier is a distinct local material state, such as a wall byte or bonded state. Its presence on a path or at a site affects passage, as in Varela's links or Ono–Ikegami membranes.
- Pros:
  - the most physics-like;
  - selectivity follows from what the barrier is made of;
  - leakage and repair arise from the same rules;
  - the best fit to the user's intent.
- Cons:
  - the designer still supplies the interaction laws (report A, qualification 1);
  - McMullin–Varela show such rules can be fragile or under-specified;
  - harder to make each channel independently tunable;
  - needs D7 conservation to have a cost;
  - most new semantics to define.

**D4-d. No explicit boundary; access determined only by ownership and occupancy.**
- Pros:
  - the smallest contract.
- Cons:
  - boundaries remain binary;
  - the user's graded-boundary intent is unsupported.

**D4-e. Directed half-edge barrier mass (hemichannel / gap-junction interface).** Each site stores a small nonnegative integer `w(u -> v)` on each of its lattice half-edges; the total interface impedance across edge `(u, v)` is `W_uv = w(u -> v) + w(v -> u)` (or an asymmetric variant if outward and inward passage differ). Barrier state lives on interfaces between sites while code bytes and free stock live inside sites.
- Pros:
  - avoids McMullin–Varela internal chain clogging ([report A](research/boundary-permeability.md), A2) because barrier mass never occupies interior code or repair-stock space;
  - allows multi-site compartments without group labels (`D2-b`): a single thread can raise `w > 0` on its outer perimeter while leaving interior edges at `w = 0`, and two adjacent threads can form a low-impedance bridge only when both lower their facing half-edges (`w(u -> v) = w(v -> u) = 0`), while either side can unilaterally close its half-edge against exploitation;
  - permits spatial polarization (high-wall sides paired with a low-wall pore for intake or sensing);
  - under symmetric edge impedance, raising `W_uv` against foreign writes or reads equally attenuates outward sensing and diffusive intake across that edge (physical reciprocity without a separate coupling tax).
- Cons:
  - adds per-direction integer state to every site (four values on a von Neumann lattice, more on Moore);
  - interface laws are still supplied by the kernel rather than emerging from free particle bonding (`D4-c`);
  - coupling all channels to one scalar `W_uv` may over-constrain selective permeability unless channel-specific multipliers are added (which would reintroduce extra parameters).

### D5. Meaning of "graded" (relevant if D4-b, D4-c, or D4-e)

**D5-a. Success probability.** Strength s blocks an attempt with probability f(s).
- Pros:
  - intuitive.
- Cons:
  - needs a keyed random draw per attempt for replay;
  - integer thresholds change the probability law;
  - simultaneous-attempt semantics become harder.

**D5-b. Resistance or cost.** An attempt succeeds only if the actor pays at least s units (time or material).
- Pros:
  - deterministic;
  - integer;
  - creates a real protection-versus-attack trade-off.
- Cons:
  - needs a currency (D7);
  - failed payment semantics must be defined (refund, burn, or keep).

**D5-c. Capacity.** At most s units or events cross per tick.
- Pros:
  - deterministic;
  - natural for material and signal flux.
- Cons:
  - when demand exceeds capacity, an ordering rule decides who gets through;
  - less natural for single write events.

**D5-d. Latency.** An action through strength s takes s ticks to complete.
- Pros:
  - deterministic;
  - gives defenders time to respond.
- Cons:
  - pending actions become new state;
  - interruption and cancellation semantics are needed.

**D5-e. Attenuation.** A signal or amount is reduced by s per crossing (integer).
- Pros:
  - suits perception;
  - deterministic.
- Cons:
  - only meaningful for quantities, not for discrete writes.

**D5-f. Single-tick deterministic ablation.** Against an interface with barrier `W > 0`, a hostile write or breach action executes atomically in one tick, leaves target code bytes unchanged, consumes the actor's tick (plus any required effort), and decrements the barrier (`W -> W - 1`); target bytes are affected only when `W = 0`.
- Pros:
  - keeps strictly atomic one-instruction-per-tick execution (`E1-a`) with zero multi-tick pending CPU state, yet creates an effective `W`-tick delay before breach (`D5-d`) during which a defender can sense damage and repair;
  - deterministic and integer-exact, requiring no per-attempt RNG draw (`D5-a`).
- Cons:
  - simultaneous ablation attempts on the same edge in one synchronous tick require an explicit aggregation or cap rule (`E4`);
  - non-destructive channels (read, fetch, passive diffusion, signals) cannot use ablation without destroying walls on every query, so they still require a companion rule such as attenuation (`D5-e`) or threshold resistance (`D5-b`).

Different channels may use different meanings. Mixing them is coherent but enlarges the contract.

### D6. Channels present in R0

Candidate channels:
- write;
- damage (destructive change distinct from a write);
- data read;
- instruction fetch;
- material;
- signal.

**D6-a. VM channels only:** write, read, fetch.
- Pros:
  - fits the decided VM;
  - the probe already maps the write endpoints.
- Cons:
  - no material or signal channel, so physics-like boundaries have no function beyond access control.

**D6-b. VM channels plus material.**
- Pros:
  - boundaries can retain or exclude resources, which the literature supports (Ono–Ikegami, Varela);
  - gives conservation a role.
- Cons:
  - requires D7 and D8;
  - the material/VM coupling must be invented.

**D6-c. All six.**
- Pros:
  - the full intended vision, including perception.
- Cons:
  - the largest contract;
  - many interacting variables violate "change one mechanism per experiment" unless introduced in stages;
  - no source shows all channels evolving together.

Separate sub-choice: whether damage is distinct from write.
- Distinct: allows "readable but not destructible" states.
- Merged: fewer rules.

### D7. Conserved quantity

**D7-0. None; CPU time slices are the only cost.** Listed in AGENTS.md as a working default.
- Pros:
  - simplest;
  - matches Tierra and Avida;
  - the ledger only covers sites and threads.
- Cons:
  - boundaries cost nothing physical;
  - copying is free, so maintenance and leakage have no meaning.

**D7-a. Integer material.** Copying a byte consumes one unit; the unit is embodied in the written byte; decay or release returns it. Under a unified monomer ledger ("bytes and walls as matter"), every non-inert code byte and every unit of constructed barrier (`D4-b/c/e`) embodies one unit from the local free monomer pool `M(x)`, giving a single conservation identity `sum_x (M_free(x) + N_code(x) + N_barrier(x)) = M_total` (adjusted by explicit inflow/outflow if open).
- Pros:
  - the physics-like rule the user is considering;
  - gives construction, repair and leakage a cost;
  - puts growth, replication, and boundary construction/repair into direct competition for the same conserved stock without an ad hoc upkeep tax (`D9`);
  - integer ledger possible;
  - no prior system closes such a ledger (report B), so the rule is defined from first principles rather than inherited.
- Cons:
  - every operation needs a debit/credit rule, including failure, collision and overflow;
  - rewriting an existing non-inert byte versus writing into an inert slot needs an explicit swap/release rule so conservation holds bit-for-bit;
  - starvation becomes a new extinction mode;
  - simultaneous intents must not spend one stock twice.

**D7-b. Local execution credit** (Coreworld-like). Sites receive replenished credit; executing an instruction spends local credit.
- Pros:
  - ties computation to place;
  - discourages self-sufficient spawn loops (Coreworld §5 suggestion).
- Cons:
  - a regenerated budget is not conservation;
  - the neighborhood debit and overlap rules were never specified in the source;
  - it duplicates the time-slice cost.

**D7-c. Both material and credit.**
- Pros:
  - separates "matter" from "energy".
- Cons:
  - two ledgers;
  - more variables;
  - harder to attribute effects.

**Closed or open supply** (sub-choice):
- *Closed*: the total is constant. It gives a strict ledger identity, but a closed system can run down or lock material into dead structures.
- *Open*: external inflow and outflow. Sustained activity is easier, but source and sink placement becomes an experimental variable, and inflow patterns can impose spatial structure.

### D8. Material transport (if D7-a)

**D8-a. Diffusion among unowned sites only.**
- Pros:
  - owned sites retain material;
  - ownership acts as a partial boundary.
- Cons:
  - ties material retention to ownership, so the boundary is again given;
  - integer diffusion needs a remainder rule.

**D8-b. Diffusion everywhere, attenuated by boundary strength.**
- Pros:
  - leakage is graded;
  - boundaries have a material function (cf. Ono–Ikegami wall density).
- Cons:
  - the most rules;
  - deterministic integer splitting and flux ordering must be specified.

**D8-c. Only by explicit instructions (take, give).**
- Pros:
  - every transfer is an attributable event;
  - simple ledger.
- Cons:
  - no passive leakage, so "boundary as retainer" has no pressure to evolve.

**D8-d. None; material is consumed where it lies.**
- Pros:
  - simplest.
- Cons:
  - depletion is local and permanent unless decay or inflow restores it.

### D9. Boundary cost and maintenance (if D4-b/c)

Options:
- construction cost only;
- construction cost plus decay (requires repair);
- continuous upkeep per tick;
- no cost.

Trade-offs:
- **Construction only:** creates an up-front trade-off, but strength is permanent once built, so the evolutionary pressure is weak.
- **Decay plus repair:** gives a maintenance burden without a per-tick tax. Varela and McMullin show repair can fail, for example by repair stock trapping itself. It is the most dynamic option and also the most fragile.
- **Upkeep:** easy to tune, but an explicit tax that is not physical (report A, qualification 2).
- **No cost:** strength saturates at the maximum, so a graded boundary collapses to binary.

The three cost forms should be separate named variables if more than one is retained.

### D10. Perception and signals

**D10-a. Direct neighborhood read** (decided: reads may target neighbors).
- Pros:
  - already decided;
  - cheap.
- Cons:
  - no travel time and no occlusion, so a wall cannot block "vision" (report A, Flow-Lenia distinction);
  - no protection-versus-perception trade-off.

**D10-b. Read blocked by the read-channel strength of the target site.**
- Pros:
  - creates a trade-off between protection and being sensed, using the existing read path.
- Cons:
  - affects only being read by others, not one's own view outward.

**D10-c. Propagated signal field.** Integer values spread one step per tick, are attenuated per crossing, and are emitted by instructions.
- Pros:
  - real locality and finite speed;
  - walls can occlude;
  - closest to "vision";
  - perception has a physical cost through emission and attenuation.
- Cons:
  - an extra per-site field and update phase;
  - integer attenuation and summation rules are needed;
  - more state to hash.

**D10-d. Uptake-mediated sensing** (Egbert et al.). Sensing happens only through the effect of absorbed material on internal state.
- Pros:
  - no separate sensor channel.
- Cons:
  - requires D7-a and D8;
  - slow and indirect.

### D11. Death

**D11-a. Age limit in executed ticks.** Limit = k × the ancestor's measured gestation (cf. Avida's optional instruction-count death).
- Pros:
  - deterministic;
  - prevents populations that persist after losing replication (Avida warning).
- Cons:
  - k is arbitrary;
  - a fixed lifespan suppresses selection on longevity.

**D11-b. Age limit relative to body or genome size.**
- Pros:
  - scales with larger organisms.
- Cons:
  - under D1-B, "size" needs a definition.

**D11-c. Stochastic hazard per tick** (Stringmol 2021 decay).
- Pros:
  - memoryless;
  - no gestation calibration.
- Cons:
  - needs keyed random draws;
  - 12 of 20 spatial Stringmol runs still went extinct.

**D11-d. Reaper on memory pressure** (Tierra).
- Pros:
  - a death rate driven by density.
- Cons:
  - a global queue conflicts with locality unless made local;
  - error-weighted ordering adds evaluative bias.

**D11-e. Displacement only** (Avida default).
- Pros:
  - no separate death rule.
- Cons:
  - in the probe under `write=any`, displacement caused 93% of deaths;
  - non-replicating populations can persist.

**D11-f. Starvation** (if D7).
- Pros:
  - physical;
  - ties death to resources.
- Cons:
  - requires a conserved quantity and an upkeep or decay rule.

These options can combine. Each combination should remain a named configuration.

### D12. Dead bytes and abandoned claims

Fate of a dead thread's sites:

**Bytes stay as unowned memory** (AGENTS.md working default).
- Pros:
  - code can be scavenged, read or fetched;
  - matches Tierra.
- Cons:
  - dead code can be fetched and executed by others indefinitely (a parasitism substrate, which may be desirable).

**Bytes decay to raw material** (if D7-a).
- Pros:
  - closes the material ledger.
- Cons:
  - the decay rate becomes another variable.

**Dual informational-and-material residue** (combines unowned retention with `D7-a`). Unowned dead bytes remain readable and fetchable while holding embodied monomers until reclaimed by gradual decay or active depolymerization/overwrite.
- Pros:
  - turns dead sites into both potential subroutine libraries and conserved material pools, creating a trade-off between preserving foreign code and harvesting monomers.
- Cons:
  - adds depolymerization or overwrite-release rules alongside decay rates (`D12`).

**Ownership transfers to a neighbor or co-owner.**
- Pros:
  - supports multi-thread bodies.
- Cons:
  - choosing the heir is a new rule;
  - risks a hidden group effect.

Fate of abandoned allocations:
- **released on owner death:** simple, but a claimer that idles forever holds space;
- **released after K ticks without writes:** prevents space hoarding, but K is arbitrary and allows claims to be "kept alive" by token writes;
- **never released:** possible space lock-up.

---

## Part E: execution semantics

### E1. Tick granularity

**E1-a. One instruction per thread per tick.**
- Pros:
  - simplest synchronous model;
  - conflicts are per instruction.
- Cons:
  - all instructions cost the same.

**E1-b. Variable instruction costs** (multi-tick instructions).
- Pros:
  - copy or allocate can cost more.
- Cons:
  - pending state;
  - interruption semantics.

**E1-c. N instructions per tick** (time slice).
- Pros:
  - fewer conflict phases;
  - faster.
- Cons:
  - within-slice reads see either stale or live state, which must be specified;
  - the semantics are no longer purely two-phase.

### E2. Visibility of reads and fetch

**E2-a. Start-of-tick snapshot for all reads and fetches.**
- Pros:
  - order-independent;
  - GPU-friendly;
  - matches Coreworld Venus I.
- Cons:
  - a program cannot observe its own write until the next tick.

**E2-b. Snapshot for others' sites, live view of own allocation.**
- Pros:
  - a program sees its own writes.
- Cons:
  - two visibility rules;
  - subtle when ownership changes in the same tick.

**E2-c. Live sequential reads.**
- Pros:
  - intuitive.
- Cons:
  - order-dependent;
  - conflicts with the decided synchronous default (allowed only as a CPU comparison mode).

### E3. Write permission (links D4)

Options:
- own allocation only (AGENTS.md working default);
- any site;
- graded by D4/D5;
- parameterized ownership steric resistance plus constructed barrier: `Resistance(u -> v) = s_own * I[owned(v) and owner(v) != actor] + W_uv` (with an optional cooperative override if mutual pores are used).

The probe measured the endpoints (fidelity about 91% vs 20–29%; births about 15.6k vs 53–81k per interval). The graded option interpolates between them but depends on D4–D7. Under the parameterized form, setting `s_own = infinity, W_uv = 0` recovers `own allocation only`, and `s_own = 0, W_uv = 0` recovers `any site`; setting `s_own` to a small finite integer (e.g., 1 or 2) gives a minimal supplied ancestor baseline protection against single-tick accidental overwrites without wall-building code (mitigating the probe's cold-start collapse), while leaving predatory breach (paying or ablating through `s_own`) and active wall reinforcement (`W_uv > 0`) reachable. Any `s_own > 0`, however, retains a built-in ownership privilege rather than purely constructed protection, and blocks inter-thread writes unless paid through or explicitly gated down.

### E4. Conflict resolution and failure effects

Priority rule options:
- **Hash of (seed, tick, thread id):**
  - Pros: fair on average and deterministic.
  - Cons: arbitrary and opaque to analysis.
- **Lowest or oldest id:** deterministic and simple, but systematically biased.
- **Strength-based** (if D4–D5): physically meaningful, but requires a tie rule anyway.
- **All conflicting writes fail:** symmetric, but can produce deadlock-like stalls and wasted actions.

Failure effect options:
- **Failure flag only:**
  - Pros: nothing lost.
  - Cons: retries are free.
- **Flag plus spent time:** a retry costs time.
- **Flag plus spent material:** under D7, failed attempts have a physical cost, but the ledger must record burned units.

### E5. Division eligibility

See D3. Options:
- fully written allocation (distinct addresses);
- write count;
- executed fraction;
- none.

### E6. Newborn activation

**Next tick.**
- Pros: no same-tick cascades.
- Cons: none significant beyond one tick of delay.

**Same tick.**
- Pros: none notable.
- Cons: order effects within a synchronous phase.

**After a delay of d ticks.**
- Pros: a vulnerable juvenile phase.
- Cons: another parameter.

### E7. Reclamation

See D12. Options:
- on death;
- after K idle ticks;
- never.

### E8. Mutation operators

**Copy error only.**
- Pros:
  - mutation is tied to replication;
  - one rate.
- Cons:
  - unexpressed code never mutates.

**Copy error plus background flips** (Tierra cosmic rays).
- Pros:
  - dead or idle code also changes.
- Cons:
  - a second rate;
  - damages ancestors before the first division.

**Insertion and deletion during copy.**
- Pros:
  - genome length can change without explicit instructions.
- Cons:
  - with allocation before division, insertion overflows or deletion underfills the block, which needs rules.

For replay, every random event needs a keyed identity, for example (seed, tick, thread, event kind, counter). That requirement holds for all options.

---

## Part M: observation

### M1. Logging granularity

**M1-a. State snapshots plus deterministic replay.**
- Pros:
  - minimal storage;
  - everything can in principle be recomputed.
- Cons:
  - each analysis needs a replay;
  - counterfactual tests still need separate runs.

**M1-b. Per-tick aggregate counters per channel:** attempts, opportunities, successes, denials, conflict losses.
- Pros:
  - cheap;
  - answers "zero crossings: no demand or protection?" (report C).
- Cons:
  - loses which actor did what to whom.

**M1-c. Full event log** (actor, target, channel, intent, resolved outcome, amount).
- Pros:
  - supports flux-across-region and information-theoretic analyses without replay.
- Cons:
  - large;
  - the log format becomes a shared schema to maintain.

**M1-d. Periodic checkpoints plus windowed per-edge/per-site channel counters, with targeted replay.** Fast evolutionary runs record full-state checkpoints (`M1-a`) alongside compact window counters `(attempts, successes, blocks)` per site or lattice edge (`M1-b`), while full event logs (`M1-c`) are generated offline by replaying selected checkpoint intervals of interest.
- Pros:
  - reveals spatial contours of active boundary blocking versus lack of demand across whole runs at bounded storage cost;
  - preserves exact actor-to-target provenance for selected intervals via deterministic replay.
- Cons:
  - requires maintaining both summary counters and a replay-to-event-log mode;
  - sub-window timing of events outside replayed intervals remains coarse.

All four options keep analysis labels out of kernel state. Which individuality measures are planned (report C: ITI, closure, copy assays) determines which observables must be recoverable.

## Composite syntheses and staged paths

The packages below show how several individual options above fold together. They are **composite candidates for discussion, not defaults or recommendations**.

- **Synthesis S1: monomer-coupled half-edge impedance (`D1-B` + `D2-a` + `D3-d` + `D4-e` + `D5-e/f` + `D7-a`).** One conserved integer monomer pool (`D7-a`) funds both non-inert code bytes and four-direction half-edge barriers `w(u -> v)` (`D4-e`). Hostile writes or breach attempts act via single-tick deterministic ablation (`D5-f`), passive monomer diffusion and outward/inward sensing attenuate across `W_uv = w(u -> v) + w(v -> u)` (`D5-e`, `D8-b`, `D10-b`), natural barrier erosion returns monomers to the local pool (`D9`), and multi-site somatic growth pairs with single-site propagule budding (`D3-d`). See [the companion physical substrate model](physical-substrate-model.md) for a full discrete formulation of the underlying physical laws, conservation ledger, and synchronous update equations.
  - Pros:
    - replaces six independent channel sliders and ad hoc upkeep taxes with one conserved monomer ledger and symmetric interface impedance;
    - keeps execution one-tick atomic while giving defenders a multi-tick ablation response window and spatial pores/gap-junction cooperation without lineage keys (`D2-b`).
  - Cons:
    - couples multiple mechanisms at once, creating starvation risk, potential over-constraint across channels, and harder causal attribution unless ablated one term at a time.

- **Synthesis S2: unified transition layout for staged experimental unlocking.** Implementing the parameterized resistance law (`E3`) and local state layout once permits single-variable progression across configurations in one codebase:
  - *Stage configuration A (VM permissions baseline)*: `s_own = infinity`, `W_uv = 0`, monomer gating disabled (`D7-0`) — isolates read and fetch permissions for baseline expressivity (`R2`) and permission-ablation runs;
  - *Stage configuration B (finite steric ownership and constructible barriers)*: finite `s_own` and/or `W_uv` enabled — tests predatory breach, active boundary maintenance, and gap-junction coupling without cold-start collapse;
  - *Stage configuration C (monomer conservation)*: `D7-a` and `D8-b` enabled — tests resource retention, leakage, and dead-code monomer harvesting.
  - Pros:
    - preserves one-mechanism-per-experiment controls across stages without rewriting the VM state machine.
  - Cons:
    - requires locking R0's state layout and canonical state hash upfront for fields that sit inactive (`0` or disabled) in baseline runs, rather than keeping R0 minimal and introducing those fields in a later kernel revision.

## Cross-cutting tensions

- **Emergence vs. a supplied ancestor:** D1-B/C and D4-c increase what can emerge, but make the ancestor harder to write and the first viability check harder to pass.
- **Physics-like rules vs. one mechanism per experiment:**
  - D4-c, D7-a, D8 and D10-c interact strongly;
  - introducing them together makes effects hard to attribute;
  - introducing them in stages means early stages lack the intended boundary function.
- **Graded vs. deterministic:** probability-based grading (D5-a) costs replay complexity; cost, capacity, latency or attenuation grading costs a currency or pending state.
- **Ownership vs. physical boundary:**
  - with ownership-based protection (E3 own only), a boundary is given;
  - with material-based protection (D2-c, D4-c), the probe's low-fidelity regime is the starting point unless the ancestor builds walls.
- **Perception vs. decided reads:**
  - direct neighbor reads are decided;
  - occlusion and attenuation require either gating those reads (D10-b) or adding a separate propagated channel (D10-c).

## Open questions for the user

1. Which emergence level (D1) is in scope for R0, and which for later?
2. Is a conserved quantity part of R0, or a later stage?
3. If boundaries are graded in R0, which channels and which meaning of "graded"?
4. Are perception and signals in R0 or deferred?
5. Which death and reclamation combination is the R0 reference configuration, and which are comparison configurations?
6. Should R0 lock only the minimal VM contract first and add conservation/graded interfaces in a later revision, or include the parameterized edge-impedance and monomer state layout in R0 (with switches to disable them in baseline controls)?
