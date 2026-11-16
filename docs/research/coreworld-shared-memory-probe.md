# Shared-memory probe: what fails without protection

Updated: 2026-11-15.

**Status:** Exploratory executed runs on a throwaway VM in the untracked `prototype/` tree. This is not the TIDE kernel, and the results are not agreed rules. The 2026-11-15 follow-up audited existing outputs and current source without rerunning simulations, corrected interpretation/counting errors below, and added a [primary-source comparison](shared-memory-prior-work.md). The original probe did not compare its implementation with Rasmussen's Coreworld or Ray's Tierra.

## Question

The current working default is one program per site, with writes restricted to an individual's own allocation. Discussion raised whether boundaries and individuality should instead emerge. This probe asks a narrower question first: in the least protected design, with fully shared memory, where does replication break?

## Model

Implementation: `prototype/experiments/coreworld/` (local only). The C++20 sources total about 900 lines. The model is independent of the earlier prototype VM.

- **Memory:** a 48×48 torus of sites, 32 bytes per site, initialized to an inert byte. There is no allocation and no ownership, except under `write=claimed` (round 3).
- **CPUs:** separate from memory. A CPU has an instruction pointer (site, offset), read/write offsets `a` and `b`, a counter `c`, a target direction `d`, and a read source `s` (self or a neighbor). Any number of CPUs may share a site.
- **Instructions (16):** template no-ops `nop0`/`nop1`; `zero`, `len`, `rdir`, `incd`, `sdir`, `sself`; `copy` (read `src[a]`, write `nbr(d)[b]`, then advance `a` and `b` and decrement `c`); `ifnz`; template jumps `jmpb`/`jmpf` within the current site; `spawn` (start a CPU at `nbr(d)`, offset 0); `hop` (move own instruction pointer to `nbr(d)`); two inert bytes.
- **Failed operations:** a blocked write still advances `a`, `b`, and `c`, so copy loops terminate. A rejected `spawn` creates nothing and advances the instruction pointer.
- **Ancestor:** a 17-byte program that picks a random neighbor, copies all 32 bytes of its own site there, spawns, and repeats.
- **Schedule:** sequential in birth order, 4 instructions per CPU per round. Newborns start in the next round. This is **not** TIDE's synchronous two-phase default.
- **Mutation:** per-byte substitution during `copy`, at rate 0 or 0.003.
- **Replay check:** splitmix64 seeded per run. A unit test compares a partial state digest for equal seeds/configurations. The digest omits future-relevant state; see the replay limitations below.

Named variables. A-C change one variable against the baseline; D-E combine variables, so this is not a complete factorial design:

| Variable | Values | Meaning |
| --- | --- | --- |
| `guard` | `none`, `occupied` | `occupied`: a write into a site that hosts any CPU's instruction pointer fails |
| `spawn` | `any`, `written` | `written`: `spawn` requires this CPU's successful-write mask to cover every target offset; successful spawn or a successful write to a different site resets coverage. A direction change alone does not reset it. |
| `reaper` | `global`, `local` | `global`: at the end of a round, remove the oldest CPUs anywhere until at most `cpu_cap` = 1024 remain; `local`: remove the oldest CPUs per site until at most `site_cap` = 1 remain |
| `max_age` | 0 or 200 rounds | 0 disables age death |
| `write` | `any`, `claimed` | `claimed`: see round 3 |

The global reaper is non-local and would not meet TIDE's locality criterion. It is retained only as the probe's baseline.

## Runs

Rounds 1-2: baseline plus A-E each ran 5 seeds × 2 guards × 2 mutation rates, 20,000 rounds each: 20 + 100 = 120 output files. Round 3 adds 20, for 140 files. Ten round-3 `write=any` cases repeat condition E, so there are 130 distinct seed/configuration tuples. Values are for the last 2,000-round interval, except where marked cumulative.

- **Fidelity:** the share of spawns whose target bytes exactly equal the spawner's current site at that instant. This does not compare against its birth genome, reconstruct copied-byte provenance, or test reproductive function.
- **Writes per spawn:** cumulative; full copying needs 32.
- **`repl`:** currently surviving CPUs that have spawned at least once in their lifetime; it is not a functional-replicator count or an interval birth count.
- **Genotype richness:** distinct strings across all nonblank memory sites, including retained dead code and allocations, not just living individuals.

### Mutation off (60 baseline/A-E output files)

All 60 files retained ancestor-identical memory strings. In the baseline, the two guards produced equal recorded digests for each seed, although write counters differed. Overwriting identical bytes leaves their content unchanged; protection can still change birth throughput and occupancy. In particular, the mutation-off D + occupied condition stalls, whereas D + none continues spawning.

Two exceptions are artifacts of the death rule, not failures of protection:

- **Baseline:** a CPU lives about 31 rounds, roughly one copy cycle. Only 159 of 1024 CPUs have spawned at any time.
- **`occupied` + `written` + `local`:** the full lattice blocks every write, so spawning stops completely while the population persists.

### Mutation 0.003

| Condition | `guard=none` | `guard=occupied` |
| --- | --- | --- |
| Baseline (`any`, `global`) | 3 frozen: births stopped by round 2,000 and 1,024 CPUs persist with no deaths. 2 spawn floods: about 1,200 spawns per round at 0.07–0.20 writes per spawn, fidelity 0.5–2.6%. | 5 persist. Fidelity falls to 0–1.5% by the end, at 3–5 writes per spawn. |
| A: `written` | 5 persist. Fidelity 46–84%, 54–65 writes per spawn. No floods and no freezes. | 5 persist. Fidelity 79–80%, 34–36 writes per spawn. |
| B: `local` | 5 spawn floods: 1.7–2.6 M spawns per interval, 3.4–4.6 writes per spawn, fidelity 31–38%. | 5 persist with frozen memory: 0.06 writes per spawn, because every site is occupied and every write is blocked. Only CPUs reproduce. |
| C: `max_age=200` | 4 extinct by round 4,000. 1 spawn flood: 2.0 writes per spawn, fidelity 10%. | 5 persist. Fidelity 1–18%, 1.5–9 writes per spawn. |
| D: `written` + `local` | 5 near freezes: 88–6,046 spawns per interval, fidelity 3–25%, 358–498 writes per spawn. CPUs fall to 797–1,397 of 2,304 sites. | 5 frozen: 0 spawns in the last interval. |
| E: `written` + `local` + `max_age=200` | 5 persist. Fidelity 20–29%, 78–93 writes per spawn, 1,587–2,112 CPUs. | 5 persist. Fidelity 54–63%, 46–50 writes per spawn. |

Raw outputs and digests: `prototype/experiments/coreworld/runs/` (`e1/` holds the baseline, `e2/` holds conditions A–E). Exact-ancestor share fell to 0% in every mutation run that uses `written`. Mutations in the inert tail of each site drift neutrally, so exact-byte ancestor share and genotype richness do not measure function here.

### Round 3: write permission on top of condition E

This round starts from condition E (`spawn=written`, `reaper=local`, `site_cap=1`, `max_age=200`, `guard=none`) and changes only `write`. The instruction set is unchanged.

Rules for `write=claimed`:

- Each site has at most one owner.
- The seeded CPU owns its home. Writing to an unowned site claims it as the CPU's allocation. A CPU holds at most one allocation, and claiming a new one releases the old. `hop` changes execution location without moving home/allocation ownership.
- A write to a site owned by another CPU fails, with the same register effects as a blocked write.
- A successful spawn transfers ownership when the destination is the parent's current allocation. A spawn elsewhere does not necessarily give its newborn ownership; this edge is possible after hopping.
- Death releases both sites. The bytes stay in place as unowned memory.
- Reads and instruction fetch may still reach neighbors.

5 seeds × 2 mutation rates × 2 values of `write`, 20 runs. The `write=any` runs reproduce condition E's digests bit for bit.

| `write`, mutation | Outcome (5/5 seeds each) | Fidelity | Spawns per interval | CPUs | Writes per spawn | Death by age (seed 1, cumulative) |
| --- | --- | --- | --- | --- | --- | --- |
| `any`, 0 | All ancestors | 100% | 150–163 k | about 2,300 | 35–37 | — |
| `claimed`, 0 | All ancestors | 100% | about 15.7 k | 1,524–1,624 | about 43 | — |
| `any`, 0.003 | Persist | 20–29% | 53–81 k | 1,587–2,112 | 78–93 | 7% of deaths |
| `claimed`, 0.003 | Persist | 91–92% | 15.5–16.8 k | 1,564–1,697 | 44–45 | 98.87% of deaths |

- **Denied writes under `claimed`:** in seed 1 with mutation, 28.8 M writes were denied against 6.6 M accepted. Blind target selection makes permission failures frequent. At the final sample, 26-32% of sites lack a CPU; that does not imply they are unowned or available, because CPUs also hold allocations. Mutation-on seed 1 produces 27.0% as many final-interval births as `any` (3.70 times slower), not one tenth. The approximately tenfold slowdown occurs with mutation off.
- **How CPUs die:** under `any`, most deaths are local-cap removals after births or hops make a site exceed its CPU limit. Raw overwriting changes bytes but does not directly remove a CPU. Under `claimed`, almost all recorded deaths are by age. Logs do not assign each local-cap removal to a specific preceding event.
- **Diversity:** richness of all nonblank memory-site strings was 580-644 under `claimed`, against 2,007-2,169 under `any`; relics and allocations are included.

## Findings from these runs

1. **Unrestricted CPU creation permits a shortcut.** With `spawn=any`, CPU births can greatly outnumber accepted writes; creating execution pointers need not copy code. `occupied` does not close that route. Among the tested single-variable interventions, `written` removed the extreme birth floods and interval-level freezes in all ten mutation-on cases. It enforces historical write coverage, not self-copying, intact final content, or functional heredity: other CPUs can overwrite covered offsets afterward.
2. **Birth-triggered removal permits a non-reproducing survivor state.** If births stop below the global cap, this reaper does not remove the remaining CPUs. Age death instead led to extinction in four of five unguarded C runs. E had births in every observed interval under local reaping, but the sweep omitted combinations such as written + age with global reaping. It cannot establish that E is uniquely sufficient or that independent death is universally necessary.
3. **Permission effects depend on the other rules.** Under `written`, `occupied` changed final byte-agreement ranges from 46-84% to 79-80% in A, and from 20-29% to 54-63% in E. With local reaping and no age death (D), occupied-site guarding blocked births at full occupancy. These are conditional effects on the stated metric, not tests of functional replication.
4. **There are different kinds of freeze.** Full-occupancy write blocking explains D + occupied. Baseline none seeds 2-4 froze with 1,024 CPUs on 2,304 sites, so a full lattice is not necessary. Occupancy, birth activity, and functional reproductive capacity must be measured separately.
5. **Claimed writes alter several mechanisms together.** In mutation-on E, `claimed` raised byte agreement to about 91%, reduced matched-seed final birth throughput by 3.38-5.17 times, and shifted recorded deaths toward age. With mutation off, throughput fell by 9.53-10.34 times. The intervention bundles body protection, single-writer allocation, reservation, and ownership transfer; these runs cannot isolate their effects or equate CPU vacancies with allocatable space.

## Relevance to TIDE decisions (proposals, not agreements)

- **Allocation before division.** Reserving public space does not itself require successful copying. Division eligibility must separately specify copied-byte coverage, copy count, or another chosen gate. These runs do not rank allocation, write permission, and heredity as universal necessities.
- **Death and reclamation.** These remain open experimental variables. A birth-independent removal process is a useful control for the observed absorbing survivor states; age is one option. The dataset does not prove that every spatial model needs it.
- **Write permission.** TIDE's own-allocation working default and this probe's `claimed` policy are related but not identical, especially after hopping and conditional ownership transfer. The latter raises byte agreement and reduces throughput in this setup. Whether overwrite remains available is a research choice to test under a precise contract.
- **Possible next variables:**
  - Protect bodies but allow shared allocations, to separate the two protections bundled in `claimed`.
  - Give the ancestor a way to sense free space, to test how much of the throughput loss comes from blind targeting.
  - Use synchronous two-phase updates.

## Limits

- One instruction set, one ancestor, one non-zero mutation rate, one age limit, one grid size, and 20,000 rounds.
- Sequential update only. The synchronous two-phase default was not tested.
- Fidelity counts exact copies, not functional replicators. No replay or perturbation test was run to check which evolved sites can still replicate.
- Condition A, `none`, seed 5 has zero surviving prior spawners but 68,900 births in the final interval. This is not contradictory: spawning CPUs may die before sampling. The coarse bins do not determine whether reproduction continues at the final instant.
- The ancestor has no way to sense whether a neighbor is free. Under `claimed`, this makes throughput depend on blind retries.
- The prototype tree is untracked, so the source revision is recorded only by hash.

## Replay

Compiler: Apple clang 21.0.0, `-std=c++20 -O2`. Current source SHA-256:

| File | SHA-256 |
| --- | --- |
| `cw_vm.hpp` | `805504c3b050a9337292135541dc63c1c6476e56292cbfcfd73f64e631668e1c` |
| `cw_vm.cpp` | `c968476361ddf5adcf112ddfb14dc4c57e88a1df8aa4d5b2383d37de18514fb1` |
| `cw_death.cpp` | `ffa2eda7d4ac839f84cd354cf2807d0515d79a0f1065323ae923bcbf634a8853` |
| `cw_inspect.cpp` | `b45f8988f5c389d0728afad66955cbd3ea29c7936ef91e00a864c32c47ade093` |
| `cw_run.cpp` | `336a5abf69a5d3c8fb2d080ec48c195166ad21db00f1ad5f941e35f7212e7f75` |
| `cw_test.cpp` | `eb25a1992bca2999e352fe14ccc7453e377fd67a1397bae057522eb58dbcc356` |
| `Makefile` | `6cc4fe3b6fbbcca4958fdf83a01f3a2ad76fdf9b42ec6fea76fd728a3f55356a` |

Earlier rounds ran on earlier revisions of these files. The original replay record reports matching all 140 stored digest values with the current source. The follow-up audited these records, the ten duplicate E configurations, and all seven source hashes; it did not rerun the simulations.

The digest covers memory, the round, selected CPU fields, and claimed ownership, but omits RNG state, CPU ages, successful-write masks/sites, home/allocation bookkeeping, next identity, and counters/configuration. Several omitted fields affect future transitions. Equal recorded digests are therefore not proof of complete-state bit-for-bit replay; TIDE's stronger acceptance criterion remains unmet by this probe.

The runner rejects unknown keys, unknown enum values, and trailing numeric junk, because a loose parser once ignored mis-split arguments. It does not fully validate numeric domains: non-finite floating-point values and some signed inputs remain possible. The audited run headers use the documented values.

```sh
cd prototype/experiments/coreworld && make test
./build/cw_run seed=1 rounds=20000 interval=2000 guard=none mut=0.003 \
  spawn=written reaper=local site_cap=1 max_age=200 write=claimed
```

Example digest for that command: `eae4d1bc02443761`. With `write=any`, the digest is `ad2d9da572db6d55`.
