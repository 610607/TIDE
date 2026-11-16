# Substrate primitives and the laws they obey

Drafted 2026-11-15; restructured the same day around laws instead of analogies. Status: **discussion document for brainstorming**.

This document lists the basic elements a TIDE world must define and states which physical-style laws each one obeys. It accompanies the [physical substrate model](physical-substrate-model.md) and the [R0 design options](r0-design-options.md). Nothing here changes the "Decided" list in [AGENTS.md](../AGENTS.md).

## Method: laws first, analogies as tools

TIDE does not need a one-to-one correspondence between its elements and things in the physical world. Analogies serve one purpose: helping choose the laws each resource should obey. Once the laws are chosen, the analogy can be dropped.

Instead of asking "what does X correspond to physically?", ask **which laws apply to X, and how**.

**Completion criterion.** A primitive is sufficiently defined when every law in the matrix either applies to it in a stated way or is explicitly exempted.

Questions that no law can settle (section 5) are design and expressivity choices. They are discussed separately and do not need a physical justification.

## Status labels

| Label | Meaning |
| --- | --- |
| Decided | Listed as decided in AGENTS.md |
| Chosen in discussion | The user chose this direction for the substrate draft. It is not yet an R0 rule. |
| Draft | Present in `physical-substrate-model.md` or `r0-design-options.md`; not chosen |
| Open | No direction yet |
| Deferred | Explicitly postponed |

## 1. The laws

Adapted from the seven laws of the [physical substrate model](physical-substrate-model.md), section 2, with energy treated as a spatial field (Chosen in discussion).

| ID | Law | What it forbids |
| --- | --- | --- |
| L1 | **Conservation and accounting.** Matter is conserved in a closed integer ledger. Energy is not conserved but is fully accounted from source to use to dissipation. | Free creation of matter; untracked energy |
| L2 | **Locality and finite speed.** Every primitive interaction crosses at most one edge per tick. | Action at a distance; lookups that skip intervening space or walls |
| L3 | **Capacity and steric exclusion.** Every store is finite, and space resists crowding. | Unbounded storage in one site; cost-free overlap |
| L4 | **Symmetry and label invariance.** No preferred direction or index order; rules never read lineage, species or ecological labels. | Directional bias; role or shield fields with physical effect |
| L5 | **Dissipation and cost.** Doing anything consumes energy; ordering work fights spontaneous decay. | Free action; immortal passive structures |
| L6 | **Fluctuation (`T > 0`).** Irreducible noise from one keyed random source: copy errors, decay, diffusion rounding, arbitration. Structures are metastable rather than permanent. | Perfect copying; perfect containment |
| L7 | **Passive reciprocity.** A passive barrier impedes crossings in both directions equally. Breaking the symmetry requires active work, which L5 charges for. | Free one-way membranes |

## 2. Primitive × law matrix

✓ = applies as stated; **Exempt** = deliberately not subject to the law; **?** = not yet covered.

| Primitive | L1 Conservation | L2 Locality | L3 Capacity | L4 Label-free | L5 Cost | L6 Fluctuation | L7 Reciprocity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Matter** (free monomers, code bytes, walls) | ✓ closed ledger | ✓ moves only to neighbors | ✓ `B_max`, `w_max` | ✓ | Polymerization costs energy | Hydrolysis, erosion, rounding | ✓ symmetric diffusion |
| **Energy** | Accounted, not conserved: source → use → loss | ✓ | Optional cap | ✓ | — | Rounding noise | ✓ if it diffuses |
| **Activation state** (formerly thread) | Not conserved; ignition costs activation energy. Registers are **Exempt** (information) | ✓ stored in its site; acts only on adjacent sites | ✓ finite registers; activations per site capped | ✓ keyed by site, no identity | Basal and per-instruction price | Execution errors (optional) | ? if neighbors may sense it |
| **Code as information** | **Exempt** (copyable) | ✓ | — | ✓ | Copying costs matter and energy; erasure costs energy | Copy errors | — |
| **Signal** | Not conserved; emission costs energy | ✓ propagates one edge per tick | — | ✓ | Emission costs energy | Optional | ✓ symmetric attenuation |
| **Ownership** | Removed (section 4.1) | — | — | — | — | — | — |
| **Write protection** (replaces ownership) | Erasure releases the displaced monomer | ✓ adjacent writes only | — | ✓ no check of who wrote a byte | Overwriting a non-inert byte costs activation energy; writing an empty slot does not | Optional | ✓ walls impede writes in both directions |
| **Addressing** | — | **Must hold**: at most one hop per tick | — | ✓ | ? (does reaching farther cost more?) | — | ? (impeded across walls?) |

## 3. Notes per primitive

Analogies appear here only where they helped choose a law.

### Matter

- Monomers, code bytes and walls are one kind of matter in one ledger. A non-inert byte or one unit of wall embodies one monomer.
- Free monomers diffuse along edges through an antisymmetric integer flux with **keyed stochastic rounding** (Chosen in discussion):
  - the fractional part of each edge flux rounds up with matching probability;
  - one draw per edge per tick is shared by both sides, so conservation is exact;
  - expected flux has no dead zone, so every wall leaks with a small nonzero probability.
- A **positivity guard** is required by stochastic rounding (exact rule Open). When rounded outflows exceed a site's stock, edges are served in keyed order until the stock runs out; the remaining edges carry zero flux that tick. Each edge still debits and credits equally.
- Dead code and walls are metastable: they decay slowly back to free monomers (L6).

### Energy

- A spatial integer field, not CPU slices (Chosen in discussion).
- Deferred: the shape of sources (patches, cycles, moving hotspots), whether stored energy diffuses, and whether waste heat or temperature exist.

### Activation state (formerly thread) and code

**Framing adopted in discussion.** Machine code is treated as functional macromolecules, and inheritance is native: copying code copies the functional molecules themselves, with no separate translation layer.

- **Fixed by the kernel:** the semantics of each instruction. This plays the role of chemistry.
- **Evolvable:** the replication machinery, because the copy loop is itself code, and all behavior.

**Chosen in discussion: there is no thread entity.**

What used to be a thread is a property of matter, the **activation state** of a site. It holds:
- the position of the active byte;
- a few registers, which are the site's local chemical state.

There is no thread list and no thread identifier. Arbitration keys use site coordinates, which keeps them isotropic.

| Former thread concept | Activation-state form |
| --- | --- |
| Thread identifier | None; keys are (site, activation slot, tick) |
| Instruction pointer | Which byte of the site is active |
| Registers | Local state stored in the site |
| Spawn / ignite | Excite code in an adjacent site, with registers cleared |
| Death | The activation ceases: it cannot pay basal energy, or its active byte becomes inert |

Execution is still sequential instruction fetch, so the local VM remains; only its state lives in the site. No expressiveness is lost relative to a thread capped at one per site.

Consequences:
- **Matter, energy and walls are all that exist,** together with matter's activation state. Individuals are entirely an analysis concept.
- **Activation becomes physical state.** Neighbors could in principle sense or perturb it, which would be a new interaction channel.

Open:
- how many activations a site can hold at once;
- whether an activation can migrate into a neighbor site, for example when executing neighbor code, carrying its registers;
- whether neighbors may read or modify a site's activation registers;
- existence cost: basal metabolism per tick, or none (the prototype uses basal metabolism);
- whether an unaffordable action fails and advances, or waits. The prototype waits, which froze activations permanently when a price exceeded the energy cap.

### Signal

- Information from beyond adjacent sites arrives only through fields that propagate one edge per tick and attenuate across walls (L2, L7).
- Whether R0 includes any signal field is Open.

### Ownership and addressing

See section 4.

## 4. Ownership and addressing

### 4.1 Ownership: removed

**Chosen in discussion: the substrate has no ownership.**

The physical world has no ownership. Molecules move under physical and chemical laws, and individuals exist only at the level of macroscopic observation. Ownership was also the only primitive that supplied an individual directly. Removing it is what leaves individuals free to emerge, and makes "individual" purely an analysis concept.

Ownership currently performs several functions. Each one passes to the laws:

| Function of ownership | What does it in the physical world | Replacement (candidate) | Status |
| --- | --- | --- | --- |
| Write protection | Bond stability, membranes, steric exclusion | **Bond energy plus walls.** Overwriting or erasing a non-inert byte costs activation energy (L5). Bytes bonded into a chain might cost more. Walls `W_uv` impede writes in both directions (L7). Protection becomes graded and priced instead of 0/1. | Draft |
| Claiming space for offspring | Space occupied by matter excludes other matter | Writing into empty slots occupies space (L3). Protecting a copy under construction means enclosing it with walls. | Draft |
| Division: handing a new region to a new executor | Matter separates and keeps reacting | Exciting the copied code (a new activation state). Whether parent and copy are "separate" is a matter of walls and distance, judged in analysis. | Draft |
| Reclamation after death | Corpses decompose | Not needed. There are no claims to release; dead code hydrolyzes under L6. | — |
| Thread identity | — | Not needed: there is no thread entity. Arbitration keys use site coordinates (L4). | Chosen in discussion |

Evidence and inference:

- **Source findings.**
  - BFF has no ownership, and replicators still arise from random programs. Replication itself therefore does not need protection.
  - Coreworld has no write protection: seeded replicators typically malfunction after about 200 iterations, and in Luna a simple self-copying instruction took over.
  - See [shared-memory prior work](research/shared-memory-prior-work.md).
- **Probe observation** ([shared-memory probe](research/coreworld-shared-memory-probe.md)):
  - under `write=any`, fidelity was about 20–29% and 93% of deaths were displacements;
  - under owner-only writes, fidelity was about 91%;
  - writes in the probe were free.
- **Inference, untested.** Under the substrate, overwriting costs bond energy while copying into empty space costs only monomers and energy. Attack becomes much more expensive than expansion, so the probe's low-fidelity regime need not recur. This is an empirical question.

Risks:

1. **Protection too weak:** copies are overwritten halfway, returning to the probe's low-fidelity regime.
2. **Protection too strong:** high bond energy freezes the world.
3. **Separation becomes graded:** parent and offspring are separated by degree. This is the intended intermediate boundary, but counts such as "births" must be defined in analysis.

Open:
- the bond-energy rule (flat cost, or higher for bytes bonded into chains);
- who may modify a wall when no site has an owner (any activation on an adjacent site, or only the activation of the site that holds the wall);
- what protects a copy under construction.

### 4.2 Addressing

A memory address has no physical meaning, but that does not matter under the law-first method. Only L2 binds it: an address may not reach farther than one hop per tick.

Remaining questions:
- Do reads and fetches across a wall weaken with `W_uv` (L7)?
- Does reaching farther within the allowed range cost more (L5)?
- Address or template match is a design choice (section 5), not a law question.

## 5. Choices no law decides

These are judged by evolvability, ease of writing an ancestor, and ease of analysis, not by physics.

| Choice | Options | Status |
| --- | --- | --- |
| Granularity of function | Byte-level (each value is an instruction), motif-level (function computed from a sequence), or mixed (Tierra-style templates) | Open |
| Passive-function bytes | Whether some byte values act merely by existing (barrier, stability, storage). If so, walls could be made of code bytes instead of separate half-edge walls. | Open |
| Addressing scheme | Direction plus offset, template matching, or both | Open |
| Instruction set content | Size, generality, and price table | Open; prices depend on the energy field |
| Activation–code relation | Whether a site without code can hold activation; how many activations per site; what a newly excited site inherits | Open |

## 6. Recorded choices

| Choice | Status |
| --- | --- |
| Energy is a spatial integer field rather than CPU slices | Chosen in discussion; shape Deferred |
| Diffusion uses antisymmetric flux with keyed stochastic rounding and a positivity guard | Chosen in discussion; guard rule Open |
| Correspondences are tools for choosing laws, not requirements | Method adopted in discussion |
| Code is treated as functional macromolecules with native inheritance; instruction semantics play the role of chemistry | Framing adopted in discussion |
| The substrate has no ownership; its functions pass to bond energy, walls and steric occupation | Chosen in discussion; replacement rules Draft |
| There is no thread entity; execution state is the activation state of a site | Chosen in discussion; capacity, migration and neighbor access Open |

## 7. Conflicts with decided items

Removing ownership touches items in AGENTS.md. Per the user's direction, conflicts are recorded here first. AGENTS.md is revised only after explicit agreement, once the substrate design has settled.

| AGENTS.md item | Current status | Under the substrate without ownership |
| --- | --- | --- |
| "Each individual owns its CPU" | Decided | The kernel has neither individuals nor CPUs as entities, only the activation state of matter. Individuals are derived in analysis. |
| "Readable regions, writable allocations, and instruction-fetch permissions are explicit" | Decided | Whether a write succeeds is set by bond energy, walls and energy, not by permissions. Reads and fetches are bounded by locality and walls. |
| "Allocation occupies public lattice space before division" | Decided | The intent, competing for space during replication, is kept. The mechanism becomes physical occupation of empty slots, possibly enclosed by walls. |
| "A program writes only to its own allocation" | Working default | Removed |
| "Death leaves the code bytes in place as unowned memory" | Working default | Kept in substance; "unowned" becomes meaningless, and dead code hydrolyzes slowly. |

The [physical substrate model](physical-substrate-model.md) also depends on ownership in:
- the `owner` and `written_mask` fields (section 3);
- the resistance law with `s_own` and the ablation rule (section 4);
- `DIVIDE` with `NASCENT`/`SOMATIC` (section 5);
- the `s_own` column of the regime table and open question 5 (sections 6–7).

## 8. Suggested discussion order

1. Write protection without ownership: the bond-energy rule and wall modification rights (section 4.1).
2. Activation state: capacity per site, migration, neighbor access, existence cost (section 3).
3. Addressing across walls (section 4.2).
4. Choices in section 5, starting with granularity and passive-function bytes.
5. Energy field shape and the price table.
