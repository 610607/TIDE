# physub: physical-substrate exploration

An exploratory C++ model of a physics-like substrate for digital life. It is **not the TIDE
kernel**: the kernel will be written fresh under an agreed contract (see `AGENTS.md`). Every
rule and value here is provisional configuration for experiments, not a decided requirement.
Do not copy rules from here into `docs/substrate-primitives.md` until they are finalized.

Related design notes: [`docs/physical-substrate-model.md`](../../docs/physical-substrate-model.md),
[`docs/substrate-primitives.md`](../../docs/substrate-primitives.md).

## Build and test

Requires CMake 3.20+ and a C++20 compiler.

```sh
cmake -S experiments/physub -B experiments/physub/build
cmake --build experiments/physub/build -j
ctest --test-dir experiments/physub/build --output-on-failure
```

`ps_test` runs 12 mechanism tests. Under the default configuration test 2 prints the replay
digest `6fb0e06a3160cc24`; CTest fails if it changes, because that means the default dynamics
changed.

## Run

From `experiments/physub/`:

```sh
build/ps_run   key=value ...   # TSV per interval; frames=<file.psv> every=N writes a replay
build/ps_probe key=value ...   # births, space census and copy errors; census=1 tests replicators
build/ps_knockout anc=polite   # single-byte knockouts: which bytes stop replication
build/ps_copycut p_rot=1e-3    # how often block rotation cuts polite's first copy
scripts/run_jobs.sh scripts/jobs/v11_energy.txt runs/v11 8   # a job list, 8 in parallel
python3 -m http.server 8765 -d viewer   # then open http://localhost:8765/?file=data/<name>.psv
```

- Both tools take `key=value` arguments and exit with an error on an unknown key. In zsh,
  expand a variable holding several arguments with `${=args}`; `ps_probe` rejects an
  argument that contains a space.
- A 96x96, 100k-tick run takes about 10-25 minutes on one core.
- `runs/` and `viewer/data/` are git-ignored. Results are reproduced from the job lists in
  `scripts/jobs/` with the recorded seeds.

## Model

- **Matter.** A closed integer ledger of free monomers, non-inert code bytes (one monomer
  each), and wall units. Free monomers diffuse; walls slow diffusion by `1 + W`.
- **Energy.** A per-site integer field with uniform inflow `e_in`, which stops at `e_max`
  (the cap applies to inflow only). An activation pays from its own site.
- **Update.** Two-phase synchronous: plan intents, then pay, write, wall, ignite and commit
  in keyed order. All randomness comes from keyed streams of (seed, tick, stream, ids), so
  a run is a pure function of its configuration.
- **ISA.** 9 ops, `op = (v - 1) % 9`, byte 0 = INERT: `MOV p q` (3 bytes); `INC`, `DEC`,
  `JZ`, `JMP`, `RND`, `IGNITE p`, `WALL`, `UNWALL` (2 bytes). A pointer is a byte pair
  `[dir, offset]`; `dir` INERT means the own site, otherwise `(v - 1) % 4` = N/E/S/W.
  Registers live in memory; an activation holds only `ip`. An activation ends when it
  cannot pay basal energy or when the byte at `ip` becomes inert.
- **Costs.** `e_basal` per tick, `e_op` per instruction, `e_bond` to change a non-inert
  byte, `e_ignite`, `e_wall`. Crossing a wall succeeds with probability `1 / (W + 1)`.
  An unaffordable instruction waits (or fails with `stall_fail=1`). Blocked writes still pay.
- **External writes** (`ext_write`): `allow` (default), `fill` (a neighbor may only fill
  INERT bytes), `erase` (fill, or erase to INERT for `e_erase`; no substitution).
- **Energy transport and storage**, both off by default (off reproduces the model above):
  - `e_diffuse=1`: the energy field diffuses with the monomer rule; walls insulate;
    divisor `e_div` (8).
  - `bond_store=1`: forming a bond pays `e_bond` and stores it in the byte. Breaking a bond,
    by a write or by hydrolysis, pays the barrier `e_act` (1; `e_erase` for an external
    erasure in `erase` mode) and releases `e_bond` to the byte's site. A failed write
    dissipates what it paid. Ledger: field + bonds = initial + inflow - dissipation.
- **Diagnostic only** (not candidate rules): `p_dead` sets the hydrolysis rate of sites
  without an activation; negative means off. `dead_quiet=N` (0 = off) limits `p_dead` to
  inactive sites that no write has reached for more than N ticks, so copies under
  construction keep `p_hydro`; when on, the per-site last-write tick enters the digest.
- **Decay form** (`hydro_whole`, 0 = off): with 1, a site's program decays in one event
  with probability `1 - (1 - r)^n` per tick over its `n` non-inert bytes, `r` = `p_hydro`
  (`p_dead` and `dead_quiet` select `r` as before). Every byte returns to the site's free
  monomers and the activation ends at the wick check. Off, each byte decays on its own.
- **Mobility** (`p_rot`, 0 = off): Margolus block rotation at the start of each tick. The
  lattice is split into 2x2 blocks offset by (0,0) on even and (1,1) on odd ticks; each block
  rotates clockwise or counterclockwise with probability `p_rot / 2` each, so a site moves
  with probability `p_rot` per tick. Code bytes and activation slots move; free monomers,
  energy and walls stay. Each of the block's four internal edges must pass a `1 / (W + 1)`
  crossing, or the block stays. There is no binding: a copy whose parent and target are
  separated continues into whatever site lies in its direction.
- **Ancestors.** `ancestor()`: a 35-byte copier that overwrites neighbors. `polite()`: a
  46-byte copier that copies all 64 bytes, and only into a neighbor whose byte 0 is INERT.
  Runs use `site_len` 64 and `mass0` 48.
- **Observer only** (not in the digest): lineage ids, a birth log with write provenance,
  replay frames (PSV1), a content identity per site that follows rotations, and copy
  counters (a copy runs from an activation's first write into a neighbor to its next paid
  ignition into a neighbor; it is cut when a rotation leaves its target outside the written
  direction).

## Files

| Path | Role |
| --- | --- |
| `src/ps_core.hpp` | Config, ISA, World API |
| `src/ps_exec.cpp` | Phase 1: plan intents and write costs |
| `src/ps_resolve.cpp` | Phase 2: pay, writes, walls, ignitions, commit, wick checks; birth observation |
| `src/ps_physics.cpp` | Diffusion (monomers, energy), hydrolysis (per byte or whole program), erosion, energy inflow, block rotation |
| `src/ps_world.cpp` | Construction, ledger, digest, ancestors, disassembler |
| `apps/ps_run.cpp` | Runner: TSV per interval, PSV replay frames |
| `apps/ps_probe.cpp` | Probe for polite-seeded runs (columns below) |
| `apps/ps_knockout.cpp` | Single-byte knockout of an ancestor without mutation or decay |
| `apps/ps_copycut.cpp` | First-copy cut probability of polite alone under block rotation |
| `tests/ps_test.cpp` | Ledgers, replay, walls, ancestor, starvation, bond barrier, act_cap, ext_write, p_dead, energy diffusion, bond storage, dead_quiet, whole decay, block rotation |
| `viewer/index.html` | Replay viewer (layers, inspector, timeline) |
| `scripts/run_jobs.sh`, `scripts/jobs/` | Parallel runner and the v8-v14 job lists |

`ps_probe` columns per interval: births, `exact%`, `intact_parent%`, top genotype, `copies`
(child mostly written by the parent) and `reignites` (child code already present),
`intact_copies`, space census (`blank`, `open0` = byte 0 inert, `dead` = inactive with code),
`pfx_active` / `pfx_copies` (polite's program region 0-45 only), `ext_erased`, `stalls`,
`starved`, field `energy`. The summary splits births by parent integrity and kind, and breaks
down the copy differences of intact parents by source: foreign write, decay after writing,
parent-written but different (mutation or misaligned copy), and residue.

With `census=1`, `ps_probe` adds a `# census` line per interval. Each distinct active program
(volatile offsets reset) is seeded alone in a fresh 9x9 world with the run's physics but no
mutation, hydrolysis, erosion or `p_dead`; it counts as a replicator when at least two active
sites carry it after 2000 ticks. The line reports replicators (any genotype), the subset with
polite's program region intact, non-replicators by how their activation began
(self/copy/reignite), mean activation age, and the mean ip span: distinct offsets the
founder's ip visits in the trial's last 500 ticks, i.e. the bytes whose decay ends the
activation by wick. Trial worlds are separate, so the interval rows are unchanged. Trials
run without rotation, so the census tests a program's own ability to copy itself.

With `hydro_whole=1`, `p_rot > 0` or `physics=1`, `ps_probe` adds a `# physics` line per
interval and at the end with cumulative counters: whole-program decays (and how many hit an
active site), wick deaths, rotations, rotations stopped by walls, copies started, cut, ended
in a birth, and ended in a birth after a cut.

## Findings from executed runs

All runs use 96x96 sites, `p_hydro` 3e-6 and `p_mut` 0.003 unless noted. v5-v7 ran on earlier
revisions without job lists; v8-v13 replay from `scripts/jobs/`. Observer changes since then
do not alter the dynamics: the v9 baseline is byte-identical to v8.

- **v5-v6** (`p_hydro` 1e-5 / 3e-6; `p_mut` down to 0.0003): the intact polite lineage is lost
  by 40-60k ticks in every run and the population declines. Lower mutation does not help.
- **v7** (`ext_write` fill / erase): `fill` doubles intact lifespan (~40k) and final
  population (~2k) but the lineage is still lost; `erase` ~ `allow`. By 50k only 18-80 sites
  are blank and 75-87% hold dead code. The overwriting copier fails in all modes.
- **v8** (birth classes): 95-98% of births are re-ignitions of corpses (life 64-96 ticks).
  Intact copies stop at 40-50k when blank space runs out. Earlier population figures include
  these short-lived re-ignitions.
- **v9** (`e_ignite` up to 256): re-ignitions fall ~10x; population, copy rates and the timing
  of lineage loss do not change. Re-ignition is a side niche, not the cause.
- **v9 census**: intact copying collapses exactly when blank sites run out (30k -> 40k);
  sites with only byte 0 cleared then accumulate unused. The functionally intact lineage
  halves every ~10k ticks.
- **v10** (`p_dead`): faster decay of inactive sites does not rescue the lineage. At 1e-4
  children decay while being written and the population collapses; at 3e-5 blank sites stay
  plentiful yet the lineage is lost by 50-70k (intact children ~65%).
- **v11** (energy diffusion, bond storage; rich `e_in` 3 vs lean `e_in` 1 with `e_basal` 2):
  same fate. With `e_in` >= 2 diffusion makes energy non-binding and doubles re-ignitions.
  Bond storage slightly improves fidelity and lifespan; external erasures do not rise, so no
  decomposer lineage appears. Corpses hold several times the field energy untouched, since a
  release at the target site gives the eraser almost nothing.
- **v12** (copy-error sources): with `p_mut` 0 intact parents make 94-96% intact children and
  the lineage still collapses when blank sites run out. Space for offspring is the primary
  limit and fidelity is secondary. In `fill` mode, foreign writes land mostly on polite's
  inert self-pointer bytes (34, 30, 36, 38, 40).
- **Knockouts** (`ps_knockout anc=polite`, revision 7ef36f3; 9x9, seed 1, no mutation,
  hydrolysis or erosion, 4000 ticks): of polite's 40 non-inert bytes, 26 are lethal, 7
  impaired and 7 neutral. 13 of the 26 lethal knockouts leave the founder running without
  copying. Intact polite births at ticks 324 and 650 in an empty world. Losing any of 26
  bytes ends replication, while a saturated neighbor opens as a polite target only when its
  byte 0 decays. At equal per-byte rates an intact parent therefore gets about 4/26 = 0.15
  openings per replicative lifetime, whatever the rate. This is consistent with v5-v12, where
  rate changes did not rescue the lineage. With 7 neutral bytes, loss of the exact genotype
  is not loss of replication; the v13 census measures both.
- **v13** (`dead_quiet`; dynamics of revision 7ef36f3, census from 53898eb on; `ext_write`
  fill, seeds 1-2, 100k ticks; `dead0` = no `p_dead`). Census at 100k ("copy-born" =
  non-replicating activations that began as copies; ages are mean activation ages):

  | run | replicator peak | active | replicators | polite region intact | non-rep copy-born | re-ignited | age rep / non-rep |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | dead0_s1 | 3047 (30k) | 2089 | 39 | 5 | 1731 | 319 | 53713 / 70591 |
  | dead0_s2 | 2676 (30k) | 2009 | 33 | 2 | 1590 | 386 | 48090 / 68809 |
  | dq0_dead3e-5_s1 | 660 (70k) | 2359 | 303 | 0 | 1547 | 509 | 17650 / 36346 |
  | dq0_dead3e-5_s2 | 1517 (40k) | 2298 | 100 | 1 | 1619 | 579 | 26373 / 51636 |
  | dq0_dead1e-4_s1 | 17 (10k) | 23 | 0 | 0 | 17 | 6 | - / 76461 |
  | dq0_dead1e-4_s2 | 3 (10k) | 3 | 0 | 0 | 2 | 1 | - / 71974 |
  | dq0_dead3e-4_s1 | - | extinct at 4768 | | | | | |
  | dq0_dead3e-4_s2 | 1 (10k) | extinct at 78997 | | | | | |
  | dq64_dead3e-5_s1 | 3166 (30k) | 2353 | 129 | 20 | 1835 | 389 | 32657 / 60628 |
  | dq64_dead3e-5_s2 | 2789 (30k) | 2215 | 90 | 8 | 1654 | 471 | 31899 / 60020 |
  | dq64_dead1e-4_s1 | 3301 (30k) | 3182 | 223 | 23 | 2365 | 594 | 23806 / 52912 |
  | dq64_dead1e-4_s2 | 2925 (30k) | 3280 | 207 | 12 | 2416 | 657 | 19376 / 52331 |
  | dq64_dead3e-4_s1 | 3516 (30k) | 4130 | 340 | 29 | 3039 | 751 | 19623 / 50320 |
  | dq64_dead3e-4_s2 | 3147 (30k) | 3817 | 236 | 30 | 2822 | 759 | 24776 / 50509 |

  - With `dead_quiet=0` (the v10 rule), `p_dead` 1e-4 and 3e-4 leave no replicator in any
    run and two of the four runs go extinct. This reproduces v10.
  - With `dead_quiet=64` all six runs reach 2.8-3.5k replicators by 30k at every `p_dead`.
    Replicators of any genotype then fall about 10x by 100k. Without `p_dead` replicators
    peak at the same time and level, then fall faster (33-39 at 100k).
  - Exact-genotype counts understate replication: at 100k most replicators differ from
    polite's program region. Yet in every surviving run 66-83% of active sites run copy-born
    programs that do not replicate. Their mean activation age (36-71k ticks) is 1.3-2.7 times
    the replicators'.
  - `dead_quiet` thus removes the damage `p_dead` does to copies under construction. It
    raises late replicator counts 2-10x over `dead0` but does not stop the decline.
  - The census ip span (revision f3810da) is similar for both groups: 5-8 offsets throughout,
    and at 100k 6.3-7.8 for replicators and 5.0-5.7 for non-replicators. Non-replicators do
    not owe their age to much smaller loops; both loops are far smaller than the 26 bytes
    replication needs.
  - Size control (`w48_*`, 48x48): non-replicating copy-born shares at 100k are 75-78%
    (`dq64_dead1e-4`) and 88% (`dead0`), against 74% and 79-83% at 96x96; replicator density
    per site is similar (2.4-3.1% vs 2.2-2.4%; 0.3% vs 0.4%). The small world saturates
    earlier, so it is further along at the same tick.
- **v14** (decay form and mobility; dynamics of revision 5579cb7, `physics=1` and
  `ps_copycut` from 77c156c; job lists `v14_whole_decay.txt`, `v14_rotation.txt`,
  `v14_copycut.txt`). The census runs use the v13 `dead0` configuration (`ext_write` fill,
  `p_mut` 0.003, 96x96, 100k ticks, seeds 1-2) and change one mechanism. The rerun `dead0`
  rows match the v13 output line for line.
  - **Decay form M** (`hydro_whole=1`, r = 1.95e-6 per non-inert byte, so polite's
    whole-program hazard equals its replicative hazard under `dead0`). Census at 100k:

    | run | replicator peak | active | replicators | polite region intact | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | replicator genotypes | births |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | dead0_s1 | 3047 (30k) | 2089 | 39 | 5 | 1731 (83%) | 319 | 53713 / 70591 | 32 | 334456 |
    | dead0_s2 | 2676 (30k) | 2009 | 33 | 2 | 1590 (79%) | 386 | 48090 / 68809 | 31 | 537922 |
    | m195_s1 | 6452 (40k) | 7390 | 5396 | 1752 | 1119 (15%) | 875 | 12051 / 10945 | 1082 | 136897 |
    | m195_s2 | 6254 (30k) | 7479 | 5473 | 1642 | 1211 (16%) | 795 | 11982 / 10440 | 1081 | 144659 |

    - Under M, replicators of any genotype peak at 6.3-6.5k and are still 5.4-5.5k at 100k,
      12-16% below the peak; under `dead0` they fall about 80x. At 100k, 73% of active sites
      replicate, and copy-born non-replicators are 15-16% of active sites against 79-83%.
    - Mean activation ages of replicators and non-replicators are close (12.0k; 10.4-10.9k)
      and near the expected life of a 40-byte program, 1 / (40 r) = 12.8k ticks. Under
      `dead0` non-replicators live 1.3-1.4 times longer than replicators.
    - Replicator genotypes rise to about 1080 by 100k (31-32 under `dead0`); replicators with
      polite's program region intact fall from 3.1-3.6k at 30k to 1.6-1.8k.
    - 88-89% of whole-program decays hit an active site. Births are 2.4-3.7x fewer, mostly
      because re-ignitions by altered parents fall from 322k to 82k (seed 1).
    - Only the form changed, but M changes two things at once: no program is damaged in
      place, and inactive code (corpses, abandoned copies) also clears in one event. Under
      form P a 40-byte corpse waits on average 1 / 3e-6 = 333k ticks for its byte 0 to decay;
      under M it clears after 12.8k ticks on average. Active sites rise to 7.4-7.5k from
      2.0-2.1k. These runs do not separate the two effects.
  - **Mobility** (`p_rot`, option (a): no binding; a cut copy continues into whatever site
    now lies in its direction). A site moves with probability `p_rot` per tick, about
    `p_rot * 320` times per copy. Levels 1e-5, 1e-4, 1e-3, 3e-3 (about 1/300) and 1e-2.
    - First copy of polite alone (`ps_copycut`, 400 seeds, 16x16, no mutation or decay).
      The estimate assumes a copy is cut with probability q per tick, q between `p_rot`
      (parent and target in one block) and `2 p_rot` (in two blocks):

      | p_rot | copy duration | cut | estimate 1 - (1 - q)^d | ended in a birth | birth after a cut |
      | --- | --- | --- | --- | --- | --- |
      | 0 | 319 | 0% | 0% | 100% | - |
      | 1e-5 | 319 | 0.75% (3) | 0.3-0.6% | 99.25% | 0 of 3 |
      | 1e-4 | 319 | 3.25% | 3.1-6.2% | 97.0% | 1 of 13 |
      | 1e-3 | 322 | 36.3% | 27-47% | 65.8% | 5.5% |
      | 3e-3 | 324 | 75.5% | 62-86% | 32.0% | 9.9% |
      | 1e-2 | 326 | 99.25% | 96-99.9% | 6.5% | 5.8% |

      Every uncut copy ended in a birth.
    - Mechanism check (`chk_*`): polite alone, `p_mut` 0, 48x48, 20k ticks; seeds 1 / 2.
      "From cut copies" is the share of copy births whose copy was cut; "intact child" is
      the share of copies by intact parents whose child matches polite:

      | p_rot | births | active at 20k | from cut copies | intact child |
      | --- | --- | --- | --- | --- |
      | 0 | 3360 / 2573 | 1869 / 1970 | 0 / 0% | 97.2 / 97.5% |
      | 1e-5 | 3072 / 2591 | 1862 / 1956 | 0.1 / 0.2% | 97.0 / 97.3% |
      | 1e-4 | 3046 / 2257 | 1833 / 1911 | 2.0 / 2.0% | 96.8 / 96.6% |
      | 1e-3 | 2349 / 2730 | 1297 / 1453 | 19.7 / 18.4% | 91.0 / 91.7% |
      | 3e-3 | 655 / 653 | 234 / 251 | 57.9 / 65.4% | 61.4 / 66.0% |
      | 1e-2 | 2 / 3 | extinct at 2615 / 2 | all | - |

    - Census at 100k (control: the `dead0` rows above):

      | run | replicator peak | active | replicators | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | intact child |
      | --- | --- | --- | --- | --- | --- | --- | --- |
      | rot1e-5_s1 | 3087 (30k) | 2137 | 54 | 1725 (81%) | 358 | 48014 / 69384 | 84.2% |
      | rot1e-5_s2 | 2412 (30k) | 1930 | 26 | 1361 (71%) | 543 | 50074 / 66716 | 84.2% |
      | rot1e-4_s1 | 2933 (30k) | 2210 | 54 | 1640 (74%) | 516 | 52266 / 65221 | 83.1% |
      | rot1e-4_s2 | 2894 (30k) | 2124 | 38 | 1571 (74%) | 515 | 42826 / 64165 | 84.3% |
      | rot1e-3_s1 | 1390 (40k) | 2838 | 9 | 1014 (36%) | 1815 | 53141 / 46955 | 76.3% |
      | rot1e-3_s2 | 1594 (40k) | 2872 | 13 | 1126 (39%) | 1733 | 59025 / 47532 | 78.0% |
      | rot3e-3_s1 | 98 (20k) | 2450 | 23 | 339 (14%) | 2088 | 19878 / 29339 | 62.5% |
      | rot3e-3_s2 | 258 (50k) | 3236 | 9 | 477 (15%) | 2749 | 40643 / 33549 | 55.1% |
      | rot1e-2_s1 | 1 (10k) | extinct at 11539 | | | | | |
      | rot1e-2_s2 | 0 (10k) | extinct at 11681 | | | | | |

    - The cut probability follows the estimate at every level. A cut copy rarely ends in a
      birth (5-10% at 1e-3 and above), and the births it does give are often altered: with
      mutation off, intact children fall from 97% to 91% at 1e-3 and to 61-66% at 3e-3.
    - In the census runs, 1e-5 and 1e-4 stay close to `dead0` (replicators 26-54 against
      33-39; copy-born non-replicators 71-81% of active against 79-83%). At 1e-3
      replicators peak at half the `dead0` level and fall to 9-13 by 100k. More than 99% of
      active sites still do not replicate, but most of them are now re-ignited (60-64% of
      active) rather than copy-born (36-39%). At 3e-3 replicators never exceed 98 and 258,
      and 85% of active sites are re-ignited. At 1e-2 both seeds go extinct after 4 and 2
      births.
    - The copy counters also count the short write-and-ignite loops of altered programs, so
      the share of births from cut copies in the census runs (0.1-4%) is not comparable to
      the mechanism check.

Working interpretation (v13 and code inspection): saturation starts the decline in every
run, and the space then fills with activations that no longer replicate. An activation ends
only when the byte at its ip decays (`check_wicks`; no run recorded a starvation death).
In a 9x9 trace without decay, polite's ip visits 4 opcode bytes while it waits for a free
neighbor and 13 over a full cycle, but replication needs 26 bytes. A replicator therefore
usually loses replication before its activation ends, and its site stays occupied. `p_dead` acts only on inactive
sites, so faster reclamation of corpses (v10, v13) does not reach these sites.

v14 reading (the counts are executed runs; the mechanisms are inference). Whole-program
decay (form M) almost removes the decline: 12-16% below the peak at 100k against about 80x
under form P. Under M a replicator cannot turn into a non-replicator where it stands, and a
non-replicator decays at the same per-byte rate as a replicator. Form M also clears corpses
about 26 times sooner, so the runs do not show which of the two changes matters. Block
rotation without binding does not clear non-replicating sites. Up to 1e-4 it has no clear
effect. From 1e-3 it cuts a third or more of all copies, replicators fall further than
under `dead0`, and non-replicators shift from copy-born to re-ignited. A cut copy ends by
igniting a site the parent wrote only in part, which fits that shift but was not measured
directly.

## Known issues (code inspection)

1. INERT means both "empty" and "own-site pointer / value 0", so self-pointer bytes can be
   filled from outside even under `fill`. Mutation and `RND` never produce INERT.
2. Re-ignition is cheap relative to copying, and corpse sites sit at full energy.
3. Without `bond_store`, `e_bond` also charges in-site counter updates.
4. Walls drop bytes during cross-edge copying while the counters still advance.
5. Minor: the cost of a write is computed from the byte behind a wall before the crossing
   check; the wick check covers only the byte at `ip`; modulo bias in direction and opcode
   decoding.

## Open proposals (none agreed)

- **Per-op decay rates and size-dependent mobility** (requested 2026-11-17): sources, code
  observations and candidate designs are in
  [the decay and mobility note](../../docs/research/decay-and-mobility.md). The uniform
  whole-program form and block rotation are implemented as options (v14); per-op rates and
  size dependence are not.
- **Bond release to the actor**: an external write that breaks a bond releases `e_bond` at
  the writer's site instead of the byte's site, so clearing dead code pays the clearer.
- **Reclaiming ancestor**: a seeded replicator that clears its target before copying.
- **Cut 1, direction encoding**: direction = `v % 5` with 0 = own site, so self-pointers are
  non-inert; needs new ancestor encodings.
- **Cut 2, re-ignition**: deprioritized after v9; `e_ignite` 256 would cut re-ignitions ~10x.
- **Cut 3, costs**: charge the bond barrier only for cross-edge breaks.

Physics and ISA changes are discussed and agreed before they are implemented.
