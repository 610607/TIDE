# Physical Substrate Model: Discrete Non-Equilibrium Laws for TIDE

Drafted: 2026-11-15. Status: **candidate physical model and discussion draft**. This document develops a physical-world-inspired substrate corresponding to Synthesis S1 in [R0 design options](r0-design-options.md). Nothing here alters the decided items in [AGENTS.md](../AGENTS.md) or settles an R0 rule until agreed.

> **Update 2026-11-15** ([substrate primitives](substrate-primitives.md)): later discussion chose three directions that are not yet reflected below:
> - **No ownership.** The substrate has no ownership. Sections that depend on it need rework: the `owner` and `written_mask` fields (section 3), `s_own` and the ablation rule (section 4), `DIVIDE` with `NASCENT`/`SOMATIC` (section 5), and the `s_own` entries in sections 6–7.
> - **Energy field.** Energy is a spatial integer field rather than per-tick CPU slices (law 2).
> - **Stochastic rounding.** Diffusion uses keyed stochastic rounding with a positivity guard instead of the floor rule.

It stays compatible with the decided local address-based VM, explicit read/write/fetch permissions, two-phase synchronous update, supplied-ancestor starting point, label-free kernel state, and bit-exact replay.

## 1. Reference scale: cellular biophysics, not macroscopic mechanics

If physical laws are used to constrain digital evolution, the relevant reference scale is **wet, micrometer-scale cellular biophysics**, not macroscopic orbital or rigid-body physics. Real protocells and microbes survive in an electrolyte medium where thermal agitation, short-range molecular binding, diffusion, and metabolic dissipation dominate.

Accordingly, two familiar macroscopic laws are **deliberately omitted**:

1. **Translational inertia and momentum conservation (`F = m a`).** Microbial life operates at low Reynolds number (`Re << 1`), where viscous drag completely overwhelms inertia (Purcell regime). Motion and construction are overdamped: once driving work stops, directed flux stops immediately without coasting or elastic rebounds. A discrete lattice state machine is naturally overdamped.
2. **Unscreened long-range `1/r^2` forces.** In aqueous ionic media, electrostatic fields are Debye-screened over nanometer distances, leaving short-range steric exclusion and nearest-neighbor reaction-diffusion as the primary physical couplings. Omitting unscreened action-at-a-distance keeps every causal interaction strictly local (`r = 1` per tick) and parallel-friendly.

## 2. Seven load-bearing physical laws and their discrete projections

Together, the following seven structural principles prevent a digital universe from collapsing into a zero-cost copying sandbox, a static crystal, or a featureless well-mixed soup.

| Physical law | Biophysical role | Minimal discrete form in TIDE | Non-physical artifacts ruled out |
| --- | --- | --- | --- |
| 1. Mass continuity (`d_t rho + div J = 0`) | Matter moves across adjacent interfaces and never spawns or vanishes | Conserved integer monomer count `M` across free pools, non-inert code bytes, and edge walls | Free byte creation during copying; unbounded wall construction |
| 2. Second law & driven dissipation | Closed matter + open free-energy flux sustains non-equilibrium structures | Closed (or metered) monomer ledger + per-tick CPU slice grants + spontaneous wall/code erosion | Immortal passive structures; zero-work steady states |
| 3. Causal locality (`r = 1` per tick) | Signals and matter traverse intermediate space at bounded speed | Nearest-neighbor (`N/E/S/W`) interactions only; multi-hop sensing/transport spans multiple ticks | Global reapers; direct long-range lookups ignoring intervening barriers |
| 4. Steric exclusion & finite capacity | Finite volume resists crowding and limits local density | Bounded `B_max` byte slots/site, wall cap `w_max`, optional `M_max`, and steric resistance `s_own` | Infinite private genomes inside one site; cost-free overlap |
| 5. Symmetry, gauge invariance, & reciprocity | Space has no preferred compass axis; physics ignores lineage/species tags; passive barriers act symmetrically | Isotropic keyed tie-breaking; label-free state transitions; shared edge impedance `W_uv` across passive channels | Directional scan bias; causal role/shield tags; free one-way passive membranes |
| 6. Metastability & programmable catalysis | High activation barriers keep polymers intact until hydrolyzed or enzymatically rewritten | Unowned code and walls decay slowly (`tau_decay >> 1`); active threads act as localized programmable catalysts | Instant corpse erasure; zero-time hydrolysis preventing code reuse |
| 7. Finite-temperature fluctuations (`T > 0`) | Finite energy per step bounds copying fidelity and containment | Keyed copy errors, stochastic erosion hazards, and symmetric arbitration draws | Cost-free zero-error replication; impenetrable zero-leak containers |

### Law details and modeling rationale

1. **Local mass continuity.** Copying a genome or building a barrier is assembly from available precursors, not pure arithmetic duplication. Every non-inert code byte and every unit of barrier thickness embodies one conserved monomer drawn from local free stock and returned locally on depolymerization or decay.
2. **Second law and driven dissipation.** A strictly closed world with no energy flux reaches thermodynamic equilibrium (uniform soup or matter locked in dead solids). Biosphere-like dynamics require **matter to cycle** while **free energy flows one way**. Instead of maintaining two separate conserved currencies, TIDE can represent matter via the conserved integer monomer `M` and free-energy throughput via per-tick CPU instruction slices: instructions consume execution opportunities to do ordering work (polymerizing code, reinforcing walls, pumping monomers) against continuous entropic erosion (diffusion and slow decay back to free monomers). See [boundaries and permeability](research/boundary-permeability.md) and [conservation and groups](research/conservation-and-groups.md).
3. **Causal locality and finite light cone.** Multi-cell convolution stencils or global priority queues bypass intermediate space, allowing an actor to inspect or displace distant state across an intact wall. Restricting all primitive crossings to adjacent lattice edges ensures a finite propagation speed (`<= 1` hop per tick) so barriers can genuinely occlude sensing and slow down diffusion or invasion.
4. **Steric exclusion and finite local capacity.** Bounding per-site code slots (`B_max`) and barrier height (`w_max`), alongside single-owner site occupancy, keeps organisms coupled to physical space. Exceeding one site's storage requires claiming adjacent sites (`D1-B` / `D3-d` in [R0 design options](r0-design-options.md)), turning multicellular extent and territorial competition into physical constraints rather than optional abstractions.
5. **Spacetime symmetry, gauge (label) invariance, and interface reciprocity.**
   - *Isotropy:* Contested writes, allocations, or monomer withdrawals must resolve via hash keys or symmetric rules, never fixed compass order (`N > E > S > W`) or thread-index order.
   - *Label invariance:* Transition laws depend solely on local material and VM state—never on `lineage_id`, species tags, or ecological labels ([AGENTS.md](../AGENTS.md)).
   - *Passive reciprocity vs. Maxwell's demon:* A passive lipid bilayer cannot act as free one-way bulletproof glass; thickening a passive barrier to block incoming damage or foreign reads symmetrically impedes outward sensing and passive diffusive nutrient intake. Asymmetry (active nutrient uptake against a gradient, selective pore opening, or active error correction) requires an active Maxwell's demon—a program spending CPU instruction ticks to do work.
6. **Metastability and programmable catalysis.** Unowned code left by dead threads behaves like metastable polymers (e.g., extracellular DNA): kinetically trapped long enough to serve both as readable/fetchable foreign subroutines and as an embodied monomer reserve ("whale falls"), yet thermodynamically unstable so dead structures gradually return their monomers to circulation. Active CPUs act as localized programmable catalysts whose instruction sequences determine what gets synthesized or dismantled before background hydrolysis intervenes.
7. **Thermal fluctuations at `T > 0`.** Finite dissipation per step prohibits perfect copying and absolute containment. Copy mutations and stochastic wall/code decay provide an irreducible noise floor sampled with counter-based PRNG keys ([spatial update semantics](research/spatial-update-semantics.md)), so achieving high fidelity or tight retention demands active evolved mechanisms (redundant coding, proofreading loops, continuous wall repair).

## 3. Candidate integer state space and exact conservation ledger

Consider a 2D periodic or bounded lattice `Z_Lx x Z_Ly` with von Neumann neighborhood `d in {N, E, S, W}` and opposite direction `opp(d)`. All state variables are integers to preserve cross-backend bit-exact replay (`P0`).

### Per-site state `u`

- `code[u][0 .. B_max - 1]`: fixed array of byte slots. `0x00` (`INERT`) represents unoccupied slot space embodying `0` monomers; every byte `!= 0x00` embodies `1` monomer. Let `N_code(u)` be the count of non-inert bytes at site `u`.
- `free_mass[u] >= 0`: integer pool of unbound monomers available at site `u` (optionally bounded above by `M_max`).
- `half_wall[u][d] in [0, w_max]`: nonnegative integer barrier mass deposited by `u` on its directed half-edge toward neighbor `nbr(u, d)`. Let `N_wall(u) = sum_{d in {N,E,S,W}} half_wall[u][d]`.
- `owner[u]`: `UNOWNED`, `SOMATIC(thread_id)`, or `NASCENT(thread_id)`.
- `written_mask[u]`: bitmask (or written-range metadata) tracking which offsets in `code[u]` were written during the current `NASCENT` reservation.

### Per-thread (CPU) state

- `thread_id`: deterministic unique identifier;
- `home_site`: anchor lattice coordinate of the thread;
- `ip = (site_ref, offset)`: instruction pointer (local direction or reachable coordinate reference plus byte offset);
- `read_ptr`, `write_ptr`: address pointers for copy/inspect operations;
- integer general registers, `fail` / `zero` status flags, and `age_ticks`.

### Exact monomer conservation identity

At the end of every tick `t`, the global integer mass ledger is:

`M_total(t) = sum_u (free_mass[u] + N_code(u) + N_wall(u))`

- In a **closed** configuration: `M_total(t) == M_total(0)` bit for bit at every step.
- In an **open chemostat** configuration: `M_total(t) == M_total(0) + cumulative_inflow(t) - cumulative_outflow(t)`.

### Byte-level mass transitions and saturation back-pressure

Every local state transition touching `code`, `half_wall`, or `free_mass` preserves total monomers locally:

- **Polymerization (`INERT -> non-inert`):** consumes `1` monomer from the actor's accessible local `free_mass` (`fail = 1` and no write if `free_mass == 0`).
- **Depolymerization / hydrolysis (`non-inert -> INERT`):** releases `1` monomer into `free_mass[u]`.
- **Wall deposition (`half_wall[u][d] -> half_wall[u][d] + 1`):** requires `half_wall[u][d] < w_max` and `free_mass[u] > 0`; debits `1` from `free_mass[u]`.
- **Wall retraction / erosion / ablation (`half_wall[u][d] -> half_wall[u][d] - 1`):** returns `1` monomer to `free_mass[u]`.
- **Le Chatelier saturation back-pressure (if `M_max` is finite):** if `free_mass[u] == M_max`, spontaneous hydrolysis/erosion at `u` is suppressed rather than overflowing or discarding monomers, keeping `M_total` exact without hidden sinks.
- **Allocation cleanup on `UNOWNED` sites:** if claiming an unowned site clears pre-existing residual bytes (`non-inert -> INERT`) so zero-write `divide` cannot revive dead code, each cleared byte returns `1` monomer to `free_mass[target]` (or remains unowned/uncleared until overwritten, depending on the chosen `D3` cleanliness rule).
- **Non-inert overwrite (`non-inert -> non-inert`):** two exact variants remain open for R0 (Section 7): either a `0`-net in-place base substitution, or an exchange consuming `1` monomer from the actor's source pool while crediting the displaced byte's `1` monomer to `free_mass[target]`.

## 4. Interface mechanics: reciprocity, ablation, diffusion, and active work

For any adjacent pair `(u, v)` along direction `d`, the total edge impedance is the sum of the two facing half-edges (`D4-e` in [R0 design options](r0-design-options.md)):

`W_uv = half_wall[u][d] + half_wall[v][opp(d)]`

### Emergent compartments and gap junctions without group labels

Because `half_wall` belongs strictly to sites and edges without any lineage or group ID (`D2-b` avoided):

- **Multi-site soma:** A single thread holding multiple adjacent sites can maintain `half_wall = 0` on internal edges (free internal monomer mixing and code access) and `half_wall > 0` on outer perimeter edges (forming a shared outer membrane).
- **Gap junctions (hemichannel docking):** Two neighboring independent threads form a low-impedance bridge (`W_uv = 0`) if and only if *both* keep their facing half-edges at `0`. Either thread can unilaterally raise its half-edge (`half_wall[u][d] > 0`) to seal off an exploitative neighbor.
- **Spatial polarization:** A thread can maintain high `half_wall` on three sides while leaving one low-`W` pore open to import diffusing monomers or sense external state.

### Hostile write resistance and single-tick deterministic ablation (`D5-f`, `E3`)

Total cross-edge write/breach resistance from actor site `u` to neighbor site `v` is:

`R(u -> v) = s_own * I[owned(v) and owner(v) != actor] + W_uv`

where `s_own >= 0` (or `infinity`) is a configurable baseline steric resistance attached to live ownership:

- When `s_own = infinity`, writes to another thread's site always fail (recovering strict `own allocation only`).
- When `s_own` is finite and `W_uv > 0`, a hostile write or breach instruction executes **atomically in one tick** (`E1-a`, no multi-tick pending CPU state): `code[v]` is left unchanged, the actor spends its tick (and sets a breach/ablation outcome flag), `W_uv` decreases by `1` (e.g., ablating the defender's facing `half_wall[v][opp(d)]` first, or `half_wall[u][d]` if defender's side is `0`), and `1` monomer returns to that edge owner's `free_mass`.
- Only when `W_uv == 0` and any finite `s_own` gate is cleared does a subsequent write alter `code[v]` (or ablate `s_own` steps as configured). Thus a wall of thickness `W` gives a defender a `W`-tick reaction window to detect interface damage and actively repair `half_wall` before its genome is overwritten.

### Conservative integer diffusion and discrete stability bound

Between each undirected neighbor pair `{u, v}`, let `delta = free_mass[u] - free_mass[v]`. The discrete Fickian flux along the edge is:

`J(u -> v) = sign(delta) * floor(|delta| / (D_div * (1 + W_uv)))`

where `D_div` is an integer diffusivity constant. Because `J(v -> u) = -J(u -> v)`, updating all edges simultaneously by `free_mass'[u] = free_mass[u] - sum_{v in N(u)} J(u -> v)` is **inherently order-independent and strictly conservative**:

- **Discrete maximum principle (`D_div >= 2 * deg`):** On a 4-neighbor lattice (`deg = 4`), choosing `D_div >= 8` guarantees that for any node `u`, the total outgoing flux across all four edges is at most `4 * floor(free_mass[u] / 8) <= free_mass[u] / 2`. Consequently:
  1. `free_mass'[u] >= 0` is mathematically guaranteed without clamping or negative-stock conflict arbitration;
  2. no checkerboard numerical instability can occur;
  3. raising `W_uv` smoothly throttles passive leakage down to `0` (`|delta| < D_div * (1 + W_uv)` cuts off sub-threshold trickle by integer quantization).

### Passive reciprocity vs. active Maxwell's-demon instructions

- **Passive channels (reciprocity):** `W_uv` gates or attenuates *both* inward and outward passive crossings across `(u, v)`—passive monomer diffusion, passive neighbor reads (`D10-b`), and optional cross-edge instruction fetch. Blocking external inspection or diffusion simultaneously dims a cell's passive outward view and starves passive inflow.
- **Active work (spending CPU ticks):** Programs break passive symmetry by paying execution ticks:
  - active `pump(d)` / `give(d)` moves monomers across an interface when permitted (e.g., harvesting free monomers through a high-`W` membrane or transferring resources through a cooperative pore);
  - active `wall_inc(d)` / `wall_dec(d)` modulates hemichannel thickness dynamically in response to internal stock or sensed boundary hits;
  - active proofread/repair loops rewrite decayed bytes or mend breached walls.

## 5. Two-phase synchronous tick pipeline

Every tick `t` advances from canonical state `S(t)` to `S(t+1)` with zero dependence on thread iteration order (`P0`):

### Phase 1: Snapshot read and intent emission

All active threads (`age_ticks > 0` or activated before `t`) execute `execute_quantum` (default `1` instruction) reading from a consistent view (`E2-a` start-of-tick snapshot, or `E2-b` if own allocation writes are immediately visible within slices). Threads do not mutate shared lattice arrays directly; instead they emit typed local intents:

- register/IP updates (local to the thread);
- `ALLOC(target_site)` or `RELEASE(site)`;
- `WRITE(target_site, offset, byte)` (or `ABLATE` against a defended neighbor);
- `DIVIDE(target_site)` (single-site propagule transfer, `D3-d`);
- `WALL_MOD(dir, delta_w)` (`+1` deposit or `-1` retract);
- `PUMP(dir, amount)` (active monomer transfer).

### Phase 2: Order-independent conservative resolution

1. **Deterministic arbitration (`E4`):** For each contested target site or shared pool withdrawal, contenders are ordered by an isotropic keyed hash `H(seed, t, target_site, thread_id)` (or declared priority plus hash tie-breaker). Only winning intents commit; losers receive deterministic `fail = 1` effects while preserving resource conservation (failed writes spend no monomer unless an explicit collision-loss rule is selected).
2. **Lifecycle and division commit:** Winning `DIVIDE(target_site)` converts `NASCENT(parent)` to `SOMATIC(child)` for a newly assigned deterministic `thread_id`, clears or truncates unwritten offsets per `D3` so pre-existing dead bytes cannot be revived without copying, and marks the newborn eligible at tick `t + 1` (`E6`).
3. **Conservative transport and entropic decay:** Apply simultaneous antisymmetric diffusion `J(u -> v)` across all undirected edges (`D_div >= 8`). Then apply keyed spontaneous erosion (`half_wall -> free_mass`), unowned-code hydrolysis (`non-inert code -> free_mass`), and thread death transitions (`age_ticks` limit, stochastic decay, or starvation).
4. **Canonical conservation & state check:** Every state transition keeps `M_total(t+1)` exact and hashes `(code, free_mass, half_wall, owner, written_mask, threads, step_metadata)` to verify bit-for-bit parity across single-threaded CPU, multithreaded CPU, and future GPU compute backends (`P1`, `P2`).

## 6. Controlled ablation regimes and falsifiable ecological outcomes

Because every physical mechanism above maps to a named configuration switch, the model supports **one-mechanism-at-a-time ablation** from the same kernel state layout (Synthesis S2 in [R0 design options](r0-design-options.md)):

| Regime | `s_own` | `half_wall` (`w_max`) | Monomer ledger (`D7`) | Diffusion & decay | Hypothesis tested |
| --- | --- | --- | --- | --- | --- |
| **R-VM (Baseline)** | `infinity` | `0` (off) | `off` (`D7-0`) | `off` | Expressivity (`R2`) and read/fetch permission effects (`RQ1`) |
| **R-Wall (Steric + ablation)** | finite (e.g. `1–2`) | `> 0` (on) | `off` | erosion only (optional) | Predatory breach vs. active wall defense and gap junctions without starvation |
| **R-Matter (Economy only)** | `infinity` | `0` (off) | `on` (`D7-a`) | `on` (`D8`) | Monomer scarcity, growth-vs-reproduction competition, and corpse recycling |
| **R-Phys (Full substrate)** | finite or `0` | `> 0` (on) | `on` (`D7-a`) | `on` (`D8-b`, `D9`) | Coupled autopoietic boundary maintenance, retention/perception tradeoff, and coevolution |

### Falsifiable negative and mixed outcomes

Running `R-Phys` (or its intermediate ablations) is **not** assumed to guarantee open-ended evolution or emergent membranes. Observable falsifying outcomes include:

1. **Autopoietic self-starvation:** Raising `half_wall` traps free monomers outside faster than active pumping imports them, causing walled cells to go extinct against thinner-walled competitors.
2. **Naked-replicator dominance:** Short, wall-less `r`-strategists (`w = 0`) out-reproduce armored or multi-site builders purely through shorter gestation time, suppressing boundary evolution across parameter sweeps.
3. **Corpse monomer lockup:** Under a closed `M_total` budget with slow unowned-code decay, dead sequences sequester most monomers in non-executing bytes until the live population starves.
4. **Pore parasitism:** Polarized cells that leave a `w = 0` intake/sensing pore get selectively invaded or hijacked through that open pore faster than they gain metabolic advantage from it.

## 7. Open R0 contract choices within this model

If this physical substrate is selected (either as the R0 layout or as a staged R0+ target), the following exact transitions must still be settled before implementation:

1. **In-place overwrite accounting:** When writing a non-inert byte over an already non-inert byte, does the write perform a `0`-net base substitution or debit `1` monomer from the actor while releasing `1` monomer to `free_mass[target]`?
2. **Read and instruction-fetch attenuation across `W_uv`:** When `W_uv > 0`, are cross-edge `read` and `fetch` blocked above a threshold `W_max_read`, charged extra latency/effort, or stochastically attenuated by a keyed draw?
3. **Multi-attacker ablation aggregation:** If `k > 1` threads attempt hostile writes across the same edge in one synchronous tick, is wall ablation capped at `1` unit per tick (via winner hash) or summed up to `min(k, W_uv)`?
4. **Closed `M_total` vs. open chemostat:** Should the reference configuration conserve `M_total` strictly, or include localized inflow/outflow sinks (and if open, what spatial inflow profile)?
5. **Steric baseline and mortality clock:** Which baseline `s_own` (`0`, small finite integer, or `infinity`) and birth-independent death rule (`age_ticks` cap, stochastic hazard, or starvation) serve as the primary reference vs. comparison controls?
