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
  `live` applies the whole form only to live sites (those that decay at `p_hydro`: active,
  or recently written with `dead_quiet`), `dead` only to the others.
- **Per-op rates** (`decay_table`, 0 = off; `decay_ratio`, default 30): with whole decay,
  table T marks four of the nine op classes as fast (`decay_fast_classes`, a fixed hash of
  T; tables 1-4 are mov/dec/rnd/unwall, jmp/ignite/wall/unwall, dec/jmp/rnd/unwall and
  mov/inc/jmp/wall). A byte's class is `(v - 1) % 9` whether it runs or not. Fast bytes
  decay at `decay_ratio` times the slow rate, and the unweighted mean of the nine class
  rates is `p_hydro`. A site with `n_f` fast and `n_s` slow bytes decays with probability
  `1 - (1 - r_f)^n_f (1 - r_s)^n_s` per tick, active or not. The apps require
  `hydro_whole=1` without `p_dead`. `decay_ratio=1` reproduces uniform form M bit for bit.
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
| `apps/ps_probe.cpp` | Probe for runs seeded with polite or `ancestor()` (columns below) |
| `apps/ps_census.hpp` | Census trial, strict-replicator test and copy-difference classes, shared by the probe and the scan |
| `apps/ps_scan.cpp` | Isolated first-copy fidelity, knockout and substitution scans of genotypes listed by the probe |
| `apps/ps_knockout.cpp` | Single-byte knockout of an ancestor without mutation or decay |
| `apps/ps_copycut.cpp` | First-copy cut probability of polite alone under block rotation |
| `tests/ps_test.cpp` | Ledgers, replay, walls, ancestor, starvation, bond barrier, act_cap, ext_write, p_dead, energy diffusion, bond storage, dead_quiet, whole decay, block rotation, whole decay per class, per-op decay tables, census trial, copy-difference classes and writer records |
| `viewer/index.html` | Replay viewer (layers, inspector, timeline) |
| `scripts/run_jobs.sh`, `scripts/jobs/` | Parallel runner and the v8-v19 job lists |

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

With `census=1` and `classes=1,2,...`, `ps_probe` adds two lines per interval and listed
table, whether or not the table is the run's `decay_table`. `# classes` gives the share of
non-inert bytes in the table's fast classes and the mean hazard at the run's `p_hydro` and
`decay_ratio`, for replicators, non-replicators and all code. For replicators, it also
splits bytes into opcode bytes (offsets where the census founder executed an instruction
during its 2000-tick trial) and the others (operands and data). `# subst` counts, per
replicator site, the bytes that differ from polite at polite's own offsets (volatile offsets
excluded). The counts are split by polite's role of the offset (13 opcode offsets, the rest
data) and by direction between the table's classes (fast to slow, slow to fast, fast to
fast, slow to slow, to inert, from inert).

`anc=copier` seeds `ancestor()` instead of polite; intact, distances, volatile offsets
(24-26 instead of 31-33 and 44) and opcode offsets then refer to `ancestor()`.

With `census=1` and `fidelity=W` (W at most the interval), `ps_probe` keeps every copy birth
in the last W ticks before each checkpoint and adds four kinds of line (definitions in
`apps/ps_census.hpp`):

- Status of a genotype: `rep` is a strict replicator: a census replicator all of whose
  founder copies in the trial are exact (the two-carrier test alone passes a program whose
  first copy is exact and later ones are not). `loose` passes only the two-carrier test.
  `prop` is not a replicator, but its trial reached copy depth 2: a child of the founder
  made a copy. `other` is the rest.
- Class of a copy birth, from the sources of the offsets where child and parent differ.
  Writers are recorded by site, not by activation, so "written from the parent's site"
  includes writes by an earlier occupant of that site. `env` when any difference was
  written from another site (foreign) or left by an earlier occupant of the child's site
  (residue); else `multi` when three or more were written from the parent's site (not copy
  errors alone: three in one copy have probability about 2.7e-4 at `p_mut` 0.003 and 40
  copied bytes); else `gap` when an offset was never written and is inert in the child; else
  `point` (one or two such differences: copy errors); else `exact`. v18 outputs, made at
  80f9fcf, print `multi` as `shift`.
- `# lineage`: active sites and genotypes by status, mean trial depth, and sites whose
  reference-inert offsets (polite's own-site pointer directions 30, 34, 36, 38, 40) have
  been filled from outside.
- `# fidelity`: births in the window by kind, and the window's refused, conflicting and
  walled writes. `# fidcopy` (one line per parent status): copy births, the shares of
  children that are census replicators, strict replicators and propagators, the births per
  class with the strict children in parentheses, and differing offsets per birth by source.
  `# fidgeno`: quartiles over strict-replicator parent genotypes with at least 10 copies of
  the strict share of their children. `# fidtop`: the three census-replicator genotypes with
  the most copy births, with their key in hex for `ps_scan`. `# fidreig`: the first 300
  re-ignitions in the window and the status of the re-ignited code.

`ps_scan` reads the `# fidtop` lines and, for each genotype, measures the share of strict
replicators among the founder's first copies in 9x9 worlds with copy error but no decay
(`first` seeds; the target is empty and nothing else is active, so differences come only from
the program's own copying), counts knockouts (byte set to inert, as `ps_knockout`) and random
substitutions (`subs` per byte) that are not strict replicators, and predicts the strict share
from text substitutions alone: (1-u)^m + u(1-u)^(m-1) sum_k s_k over the m non-inert,
non-volatile bytes, with s_k the strict share of substitutions at k.

With `census=1` and `fate=1` (no rotation), `ps_probe` follows every activation from its
birth (or the seeding) to its end and adds six lines per interval, covering the interval since
the previous checkpoint. An activation takes the status (`rep`, `loose`, `prop`, `other`) of
its key at birth. When a non-volatile byte of a live `rep`, `loose` or `prop` site changes
without a birth (in place), its key is tested again. In-place changes of `other` sites are
counted but not tested (about 98% of all in-place changes, and most produce a key never seen
before); the census at the checkpoint finds any that became a replicator (`found_at_census`).
The observer compares every tracked site with a snapshot after each tick. Between births a
site's bytes change only by writes (whole decay empties the site and ends its activation), so
each changed byte was written that tick and the writer records name the writing site.

- `# fate`: strict-replicator activations at the previous and this checkpoint, strict births by
  kind, strict ends by cause, strict activations lost and gained in place, and the balance
  (previous + born + gained - ended - lost), which must equal the current count. Checks:
  `census_mismatch` (tracked status differs from the census), `untracked` (active sites without
  an activation), `stale` (changed bytes whose last write was not this tick) and `replaced` (a
  birth into a site whose activation was still on) must all be 0. `starved`: starvation deaths
  in the interval, which the end causes count as wick.
- `# fateborn` / `# fateend`: births by status and kind; ends by status and cause. An
  activation ends by `decay` when its site holds no non-inert byte after the tick (whole
  decay), otherwise by `wick` (its ip reached an inert byte). `converted`: ends of activations
  that had lost strict status in place.
- `# fatechange`: in-place key changes by status before and after, and by writer: `self`, the
  status of the foreign writer's activation, or `none` (the writer's site is no longer active).
  When several sites wrote, the first foreign writer counts.
- `# fateout`: strict activations lost in place: writer, writer by status after (`by_to`),
  whether the source-pointer direction byte (`src_ptr`: 30 for polite, 23 for `ancestor()`)
  changed (`with_src`) or was the only non-volatile change (`only_src`), who wrote that byte
  (`src_writer`), how often a foreign writer is the neighbor the new direction names
  (`src_names_writer`), where the closing jump then lands (polite's JMP 30 jumps to [30] mod
  64: offset 0, another opcode offset of the reference, or elsewhere), foreign writes into
  volatile offsets of strict sites (not status changes), and the most changed offsets.
- `# fateconv`: converted activations alive, their copy births, and how many children are
  strict, equal to the parent's key, or equal to the key of the neighbor that the parent's
  source pointer names.

The observer runs extra trials for keys the census has not seen and hands the census the
verdicts for active sites, so all other lines, including the census `trials` count, are the
same as without `fate=1`.

With `hydro_whole` on, `p_rot > 0` or `physics=1`, `ps_probe` adds a `# physics` line per
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
- **v15** (separating the two effects of form M; revision 4eef9cf, job list
  `v15_decay_split.txt`; settings as v14, no rotation). Live (active) sites and the others
  each take the form and rate they have in one v14 run; `dead0` and `m195` were rerun and
  match v14 byte for byte. Census at 100k:

  | run | live sites | other sites | replicator peak | active | replicators | polite region intact | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | replicator genotypes |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | dead0_s1 | byte, 3e-6 | byte, 3e-6 | 3047 (30k) | 2089 | 39 | 5 | 1731 (83%) | 319 | 53713 / 70591 | 32 |
  | dead0_s2 | byte, 3e-6 | byte, 3e-6 | 2676 (30k) | 2009 | 33 | 2 | 1590 (79%) | 386 | 48090 / 68809 | 31 |
  | whole_dead_s1 | byte, 3e-6 | whole, 1.95e-6 | 3431 (30k) | 3605 | 361 | 31 | 2683 (74%) | 561 | 23334 / 51628 | 214 |
  | whole_dead_s2 | byte, 3e-6 | whole, 1.95e-6 | 3323 (30k) | 3394 | 362 | 41 | 2440 (72%) | 592 | 18838 / 50783 | 207 |
  | whole_live_s1 | whole, 1.95e-6 | byte, 3e-6 | 5712 (30k) | 4747 | 3635 | 1584 | 732 (15%) | 380 | 12895 / 12002 | 617 |
  | whole_live_s2 | whole, 1.95e-6 | byte, 3e-6 | 4801 (30k) | 4112 | 3036 | 926 | 734 (18%) | 342 | 12565 / 11650 | 549 |
  | m195_s1 | whole, 1.95e-6 | whole, 1.95e-6 | 6452 (40k) | 7390 | 5396 | 1752 | 1119 (15%) | 875 | 12051 / 10945 | 1082 |
  | m195_s2 | whole, 1.95e-6 | whole, 1.95e-6 | 6254 (30k) | 7479 | 5473 | 1642 | 1211 (16%) | 795 | 11982 / 10440 | 1081 |

  - Replicators fall from peak to 100k by about 80x (`dead0`), 9x (`whole_dead`), 1.6x
    (`whole_live`) and 1.2x (`m195`).
  - Whole decay of live programs alone (`whole_live`) brings copy-born non-replicators down
    to the M level: 15-18% of active sites against 15-16% under M and 72-83% in the two runs
    with per-byte decay of live programs. Replicators make up 74-77% of active sites, as
    under M (73%).
  - Whole clearance of inactive code alone (`whole_dead`) leaves about 10x more replicators
    at 100k than `dead0` (361-362 against 33-39). But 72-74% of active sites are still
    copy-born non-replicators, and they are 2.2-2.7x older than the replicators.
  - Non-replicators outlive replicators only where live programs decay byte by byte (1.3-1.4x
    in `dead0`, 2.2-2.7x in `whole_dead`). With whole decay of live programs both groups
    live about 12k ticks.
  - Combined: the two effects act on different quantities. Whole decay of live programs sets
    the non-replicator share and is the larger effect on replicator numbers (about 90x over
    `dead0` and 15x over `whole_dead`). Whole clearance of inactive code adds about 10x over
    `dead0` and 1.6x over `whole_live`, and it raises the number of active sites (4.1-4.7k
    to 7.4-7.5k).

- **v16** (per-op rates in form M; revision 84092a3, job list `v16_per_op_decay.txt`;
  settings as v15, no rotation). Two rate levels, fast : slow = 30 : 1, four fast op classes
  per `decay_table`, unweighted class mean 1.95e-6 (slow 1.404e-7, fast 4.212e-6; design in
  [decay-and-mobility.md](../../docs/research/decay-and-mobility.md), section 6). Identity
  checks:
  - All eight table and seed runs with `decay_ratio=1` reproduce v15 `m195` byte for byte.
  - `m195` was rerun with `classes=1,2,3,4`. Without the `# classes` and `# subst` lines,
    it matches v15 byte for byte.

  Census at 100k:

  | run | polite hazard vs M | replicator peak | active | replicators | polite region intact | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | replicator genotypes |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | t1_s1 | 1.06 | 6660 (40k) | 7574 | 5466 | 1390 | 1215 (16%) | 893 | 11743 / 11052 | 1226 |
  | t1_s2 | 1.06 | 6270 (40k) | 7549 | 5297 | 1717 | 1303 (17%) | 949 | 11431 / 10505 | 1130 |
  | t2_s1 | 0.85 | 6552 (40k) | 7574 | 5542 | 1995 | 1177 (16%) | 855 | 13918 / 14537 | 1026 |
  | t2_s2 | 0.85 | 6245 (60k) | 7686 | 5640 | 2315 | 1185 (15%) | 861 | 13891 / 13356 | 1029 |
  | t3_s1 | 1.17 | 6595 (40k) | 7414 | 5212 | 1364 | 1344 (18%) | 858 | 10734 / 12179 | 1215 |
  | t3_s2 | 1.17 | 6074 (30k) | 7275 | 5094 | 1854 | 1346 (19%) | 835 | 10425 / 11544 | 1040 |
  | t4_s1 | 0.96 | 6765 (40k) | 7664 | 5680 | 1758 | 1065 (14%) | 919 | 12541 / 11294 | 1133 |
  | t4_s2 | 0.96 | 6422 (40k) | 7628 | 5605 | 2060 | 1139 (15%) | 884 | 12628 / 11388 | 981 |
  | m195_s1 | 1 | 6452 (40k) | 7390 | 5396 | 1752 | 1119 (15%) | 875 | 12051 / 10945 | 1082 |
  | m195_s2 | 1 | 6254 (30k) | 7479 | 5473 | 1642 | 1211 (16%) | 795 | 11982 / 10440 | 1081 |

  Composition at 100k, each table's run (T) against `m195` of the same seed measured with that
  table (C). Shares are of non-inert bytes in the table's fast classes. Opcode bytes are the
  offsets the census founder executed; the volatile counters fall among the data bytes. The
  hazard is in units of 1e-5 per tick:

  | table | seed | replicator data bytes, T / C | replicator opcode bytes, T / C | replicator hazard, T / C | non-replicators, T / C | all code, T / C |
  | --- | --- | --- | --- | --- | --- | --- |
  | 1 | 1 | 48.8 / 49.4 | 38.7 / 38.7 | 8.39 / 8.42 | 43.4 / 45.1 | 44.7 / 45.5 |
  | 1 | 2 | 49.3 / 49.7 | 38.7 / 38.7 | 8.45 / 8.44 | 43.6 / 44.8 | 45.0 / 45.6 |
  | 2 | 1 | 42.4 / 42.6 | 30.5 / 30.3 | 7.16 / 7.18 | 36.4 / 39.8 | 38.3 / 39.4 |
  | 2 | 2 | 42.1 / 42.2 | 30.6 / 30.4 | 7.12 / 7.13 | 37.2 / 40.3 | 38.3 / 39.4 |
  | 3 | 1 | 59.2 / 60.2 | 30.2 / 30.2 | 9.18 / 9.25 | 43.8 / 48.1 | 48.0 / 49.9 |
  | 3 | 2 | 60.3 / 60.7 | 30.4 / 30.2 | 9.32 / 9.29 | 44.5 / 48.3 | 48.6 / 50.2 |
  | 4 | 1 | 31.4 / 32.0 | 69.0 / 69.0 | 7.90 / 7.97 | 44.1 / 45.6 | 43.4 / 44.0 |
  | 4 | 2 | 31.0 / 31.7 | 68.9 / 68.9 | 7.82 / 7.92 | 43.0 / 45.9 | 42.8 / 44.1 |

  - **Population.**
    - Replicators number 5.1-5.7k against 5.4-5.5k under uniform M, with peaks of 6.1-6.8k
      against 6.3-6.5k.
    - Mean replicator age follows polite's hazard under the table: 13.9k ticks for table 2
      (0.85 of M), 10.4-10.7k for table 3 (1.17), and 12.0k in `m195`. 12.0k / 0.85 = 14.1k
      and 12.0k / 1.17 = 10.3k.
    - Table 3 has the most copy-born non-replicators (18-19% of active against 15-16%), and
      only there do non-replicators outlive replicators (age ratio 1.11-1.13 against
      0.87-0.91 in `m195`).
  - **Opcode bytes do not move.** Their fast share stays within 0.25 points of the control
    in every run. Substitutions at polite's opcode offsets stay below 0.02 per replicator in
    treatment and control.
  - **Data bytes.**
    - At 100k, replicator data bytes have a lower fast share than the control in all eight
      runs, by 0.16-1.04 points. At 50k the sign is mixed (-0.30 to +0.19).
    - The replicator hazard is within 1.3% of the control: lower in six runs and slightly
      higher in t1_s2 and t3_s2, where replicators are 0.2-0.3 bytes longer.
    - Substitution counts at polite's data offsets are dominated by a few variants carried
      by large clades, in the controls too. For example, the table-3 control on seed 1 has
      0.27 fast-to-slow substitutions per replicator.
    - Slow-to-fast data substitutions are lower than or equal to the control in seven of
      eight runs, while fast-to-slow ones are higher only in t3_s1. These counts do not
      separate selection from clade structure.
  - **Non-replicators and all code.** At 100k their fast share is 1.2-4.3 points below the
    control for non-replicators and 0.6-1.9 points below for all code. The non-replicator
    gap is already present at 10k in all eight runs.

- **v17** (v16 run to 500k ticks; dynamics of revision 84092a3, job list
  `v17_long_per_op_decay.txt`; one census and class point every 50k ticks; 10 runs in 46
  minutes on 4 cores). The census and class lines at 50k and 100k equal those of v16, apart
  from the cached trial count. Each table's control is `m195` of the same seed, measured
  under that table.

  Replicator data bytes: fast share, treatment minus control (percentage points):

  | tick | t1_s1 | t1_s2 | t2_s1 | t2_s2 | t3_s1 | t3_s2 | t4_s1 | t4_s2 | mean |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | +0.18 | -0.19 | -0.15 | +0.19 | -0.18 | -0.09 | -0.11 | -0.30 | -0.08 |
  | 100k | -0.59 | -0.38 | -0.17 | -0.16 | -1.04 | -0.44 | -0.52 | -0.72 | -0.50 |
  | 150k | -1.27 | -0.46 | -0.44 | -0.35 | -1.41 | -0.64 | -0.83 | -0.84 | -0.78 |
  | 200k | -1.43 | -1.06 | -0.27 | -0.50 | -1.75 | -0.94 | -1.58 | -1.05 | -1.07 |
  | 250k | -1.30 | -0.94 | -0.54 | -0.92 | -1.47 | -0.77 | -1.98 | -1.33 | -1.16 |
  | 300k | -1.13 | -0.89 | -0.12 | -1.20 | -1.13 | -1.85 | -1.84 | -1.26 | -1.18 |
  | 350k | -1.75 | -0.12 | -0.38 | -1.77 | -0.65 | -1.10 | -2.19 | -1.19 | -1.14 |
  | 400k | -1.71 | -0.26 | -0.08 | -1.99 | -1.08 | -1.71 | -1.04 | -1.06 | -1.12 |
  | 450k | -1.38 | -0.03 | -0.47 | -2.85 | -0.51 | -1.25 | -1.40 | -1.32 | -1.15 |
  | 500k | -1.65 | -1.64 | -0.99 | -3.99 | -1.22 | -2.41 | -1.04 | -2.13 | -1.88 |

  Replicator hazard, treatment over control minus 1 (%):

  | tick | t1_s1 | t1_s2 | t2_s1 | t2_s2 | t3_s1 | t3_s2 | t4_s1 | t4_s2 | mean |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | +0.2 | -0.1 | -0.1 | +0.4 | -0.4 | +0.6 | -0.2 | -0.5 | -0.01 |
  | 100k | -0.4 | +0.1 | -0.3 | -0.2 | -0.8 | +0.4 | -0.8 | -1.3 | -0.43 |
  | 150k | -1.0 | -0.1 | -0.5 | -1.0 | -0.9 | -0.1 | -1.3 | -1.8 | -0.83 |
  | 200k | -1.6 | -1.2 | -0.8 | -0.8 | -1.1 | -0.6 | -2.4 | -1.7 | -1.26 |
  | 250k | -1.8 | -1.4 | -0.8 | -1.6 | -1.4 | -0.4 | -2.8 | -2.0 | -1.52 |
  | 300k | -2.2 | -1.5 | +0.8 | -2.0 | -1.2 | -1.4 | -2.7 | -1.7 | -1.49 |
  | 350k | -2.5 | -1.1 | +0.3 | -2.7 | -1.4 | -0.8 | -3.7 | -1.8 | -1.72 |
  | 400k | -3.0 | -1.8 | +0.9 | -3.4 | -2.1 | -3.6 | -2.5 | -2.2 | -2.22 |
  | 450k | -2.9 | -2.0 | -0.4 | -4.1 | -1.7 | -3.2 | -3.7 | -2.0 | -2.49 |
  | 500k | -2.8 | -3.6 | -0.6 | -5.9 | -2.5 | -3.8 | -2.4 | -2.8 | -3.05 |

  Uniform form M (`m195`) over 500k. Births are per 50k-tick window; re-ignitions are births into code already present:

  | tick | replicators s1 / s2 | polite region intact | copy-born non-rep (% of active) | exact births % | re-ignitions (% of births) | replicator length |
  | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6338 / 6045 | 3234 / 2740 | 12% / 14% | 43 / 39 | 54% / 57% | 41.2 / 41.2 |
  | 100k | 5396 / 5473 | 1752 / 1642 | 15% / 16% | 24 / 24 | 72% / 69% | 41.8 / 41.7 |
  | 150k | 4474 / 4639 | 749 / 757 | 21% / 21% | 16 / 19 | 78% / 74% | 42.5 / 42.6 |
  | 200k | 3376 / 3298 | 258 / 254 | 29% / 31% | 12 / 11 | 80% / 82% | 43.5 / 43.4 |
  | 250k | 2231 / 2390 | 82 / 146 | 42% / 41% | 9 / 8 | 82% / 84% | 44.1 / 44.1 |
  | 300k | 1548 / 1915 | 48 / 103 | 51% / 45% | 8 / 8 | 83% / 84% | 44.6 / 44.5 |
  | 350k | 1200 / 1621 | 22 / 93 | 57% / 51% | 8 / 8 | 84% / 84% | 44.8 / 44.9 |
  | 400k | 997 / 1309 | 17 / 57 | 59% / 56% | 7 / 8 | 85% / 84% | 45.1 / 45.4 |
  | 450k | 890 / 1083 | 38 / 26 | 63% / 60% | 8 / 7 | 84% / 83% | 45.6 / 45.5 |
  | 500k | 671 / 979 | 48 / 6 | 65% / 61% | 6 / 7 | 86% / 84% | 45.3 / 45.4 |

  - **Data-byte shift.**
    - The mean over the eight runs grows from -0.08 points at 50k to -1.07 at 200k. It
      holds at -1.1 to -1.2 through 450k and is -1.88 at 500k (runs: -1.0 to -4.0).
    - From 100k on, every run is below its control at every point.
    - After 200k single runs move by up to 1.6 points from one point to the next; for
      example, t1_s2 is -1.06 at 200k, -0.03 at 450k and -1.64 at 500k.
  - **The control drifts too.** Under uniform rates, the data-byte fast share drifts toward
    the share in random bytes (44-45%). From 50k to 500k:
    - table 1: 50.3-50.6% to 45.6-47.0%;
    - table 2: 41.3-41.9% to 43.3-44.7%;
    - table 3: 61.3-61.4% to 56.8-57.2%;
    - table 4: 30.7-30.8% to 34.5-35.4%.

    The treatment stays below the control whichever way the control drifts.
  - **Replicator hazard against the control.**
    - The mean gap is -0.4% at 100k, -1.3% at 200k, -1.5% at 300k, -2.2% at 400k and -3.1% at
      500k (runs: -0.6 to -5.9%).
    - All eight runs are below their controls at 150-250k and at 450-500k. The one exception
      in between is t2_s1, at +0.3 to +0.9% from 300k to 400k.
  - **Absolute hazard rises.** From 50k to 500k it rises in seven treatment runs by 0.2-12.7%
    (t1_s2 is unchanged) and in every control by 3.5-16.6%. In both, replicators lengthen
    from 41.2 to 45.0-45.7 non-inert bytes, and their composition drifts toward that of
    random bytes.
  - **Opcode bytes** show no consistent shift. After 300k single runs depart by up to 1.8
    points in both directions (t2_s2 +1.79 and t3_s2 +1.29 at 500k; t3_s1 -1.20 at 350k).
  - **Population.**
    - Replicators fall in treatment and control alike: from 5.9-6.7k at 50k to 500-1014 at
      500k, against 671-979 in the controls.
    - Copy-born non-replicators make up 60-68% of active sites at 500k, against 61-65% in
      the controls.
    - Polite's region is intact in 0-28 replicators per run at 500k (controls: 6-48).
- **v18** (copy fidelity under form M to 500k ticks; revision 80f9fcf, job list
  `v18_fidelity.txt`; 12 jobs in 22 minutes on 4 cores). Four runs repeat v17 `m195_s1`,
  `m195_s2`, `t2_s1` and `t3_s1` with `fidelity=5000`: every copy birth in the last 5,000
  ticks before each 50k point is classified, and parent and child are judged by the census.
  Their rows and their census, class, substitution and physics lines equal v17's to 500k
  (trial counts aside). Below, a strict parent or child is one whose genotype is a strict
  replicator in the census trial. `ps_scan` (revision 94a6475) then tested the three strict
  genotypes with the most copies per run and point, 120 genotype-points in all
  (`ps_scan label=RUN first=400 subs=4 < runs/v18/RUN.tsv`).

  Copies by strict parents in the window / strict children among them (%):

  | tick | m195_s1 | m195_s2 | t2_s1 | t3_s1 |
  | --- | --- | --- | --- | --- |
  | 50k | 2362 / 83.3 | 2303 / 82.2 | 2051 / 83.1 | 2578 / 84.2 |
  | 100k | 1902 / 79.6 | 2070 / 79.9 | 1653 / 79.5 | 2169 / 78.2 |
  | 150k | 1732 / 75.8 | 1975 / 76.6 | 1589 / 76.0 | 1805 / 74.2 |
  | 200k | 1530 / 71.0 | 1662 / 65.3 | 1417 / 72.4 | 1657 / 68.7 |
  | 250k | 1249 / 62.9 | 1381 / 65.6 | 1229 / 61.4 | 1266 / 62.2 |
  | 300k | 1023 / 58.1 | 1143 / 66.5 | 985 / 59.0 | 1106 / 68.1 |
  | 350k | 828 / 56.6 | 1013 / 62.4 | 793 / 61.2 | 881 / 64.6 |
  | 400k | 702 / 66.5 | 875 / 64.9 | 602 / 63.0 | 769 / 64.8 |
  | 450k | 625 / 65.8 | 792 / 60.9 | 429 / 59.7 | 581 / 64.9 |
  | 500k | 467 / 72.0 | 673 / 65.7 | 428 / 66.8 | 507 / 69.8 |

  Strict-parent copies whose child is not strict, by class, in percentage points of all
  strict-parent copies (mean over the four runs, range in parentheses). The last two columns
  give the differing offsets per copy written from another site / left in the target
  (residue), as a four-run mean, and the writes refused in the window because the target
  site had no free monomer:

  | tick | point | gap | multi | env | total | foreign / residue per copy | no-mass writes |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6.3 (5.7-7.0) | 0.3 (0.2-0.5) | 3.1 (2.7-3.6) | 7.1 (6.7-7.9) | 16.8 (15.8-17.8) | 0.61 / 0.08 | 0 |
  | 100k | 5.8 (5.6-6.4) | 0.4 (0.2-0.6) | 3.6 (2.6-4.5) | 10.9 (9.3-13.1) | 20.7 (20.1-21.9) | 1.03 / 0.10 | 0 |
  | 150k | 5.5 (5.4-5.6) | 0.7 (0.3-1.2) | 4.6 (4.4-5.0) | 13.6 (12.6-14.6) | 24.4 (23.4-25.8) | 1.26 / 0.12 | 5-348 |
  | 200k | 4.3 (4.0-4.6) | 3.0 (1.3-4.9) | 5.2 (4.3-6.0) | 18.2 (17.1-19.8) | 30.6 (27.6-34.7) | 1.75 / 0.20 | 924-2412 |
  | 250k | 4.5 (3.6-5.1) | 6.6 (4.1-9.4) | 6.7 (6.4-7.0) | 19.2 (18.2-20.3) | 37.0 (34.4-38.6) | 1.64 / 0.21 | 3067-5874 |
  | 300k | 4.6 (3.9-5.1) | 5.6 (3.2-9.1) | 7.1 (6.4-7.7) | 19.8 (16.3-22.8) | 37.1 (31.9-41.9) | 1.59 / 0.25 | 2494-6799 |
  | 350k | 4.6 (3.7-5.3) | 5.6 (4.3-7.6) | 7.5 (7.4-7.9) | 21.1 (18.2-23.5) | 38.8 (35.4-43.4) | 1.78 / 0.19 | 3448-10266 |
  | 400k | 5.2 (4.2-6.5) | 4.6 (3.2-6.0) | 8.2 (5.7-9.6) | 17.2 (16.7-17.7) | 35.2 (33.5-37.0) | 1.44 / 0.22 | 2518-4454 |
  | 450k | 5.3 (4.4-5.9) | 5.8 (3.4-7.7) | 8.7 (8.4-9.0) | 17.5 (15.0-19.6) | 37.2 (34.2-40.3) | 1.35 / 0.15 | 4838-6472 |
  | 500k | 5.2 (4.6-6.1) | 4.3 (1.9-5.6) | 7.1 (5.3-9.6) | 14.9 (12.1-16.6) | 31.4 (28.1-34.3) | 1.31 / 0.13 | 1457-7882 |

  The same genotypes in the run and alone. In the run: the strict share of the children of
  the 12 genotypes (three per run), weighted by their copies; from 250k these are 169-289
  copies per point. Alone: 400 first copies per genotype in a 9x9 world with copy error and
  no decay. m counts non-inert, non-volatile bytes. The sensitive length is m minus the
  summed share of substitutions that leave a strict replicator, and pred is the first-order
  strict share from substitutions alone:

  | tick | copies | in-run strict % | alone: strict % | alone: exact % | (1-u)^m % | m | sensitive length | pred % |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 5378 | 87.4 | 91.8-92.0 | 88.0-89.2 | 89.5 | 37 | 26.5-26.8 | 92.2-92.3 |
  | 100k | 2757 | 83.6 | 91.8-93.0 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.5-26.8 | 92.2-93.1 |
  | 150k | 1321 | 82.4 | 91.8-93.0 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.5-26.8 | 92.2-93.1 |
  | 200k | 563 | 72.5 | 91.5-93.2 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.2-26.5 | 92.3-93.2 |
  | 250k | 289 | 68.2 | 92.0-93.0 | 88.2-89.2 | 87.6-89.5 | 37-44 | 22.8-26.5 | 92.3-93.3 |
  | 300k | 194 | 72.2 | 92.0-93.2 | 86.2-89.2 | 87.4-89.5 | 37-45 | 23.0-26.8 | 92.2-93.2 |
  | 350k | 182 | 67.6 | 91.2-93.0 | 87.5-90.0 | 87.9-89.5 | 37-43 | 22.8-27.8 | 92.0-93.3 |
  | 400k | 219 | 69.4 | 91.2-93.2 | 87.2-89.2 | 87.4-89.2 | 38-45 | 22.8-27.5 | 92.0-93.3 |
  | 450k | 230 | 71.3 | 91.2-94.0 | 86.2-89.2 | 87.4-89.2 | 38-45 | 23.0-28.0 | 91.9-93.2 |
  | 500k | 169 | 77.5 | 91.2-93.0 | 87.5-89.5 | 87.9-89.2 | 38-43 | 23.2-28.0 | 91.9-93.2 |

  None of the 48,000 first copies alone fell in the gap, multi or env class: 86-90% were
  exact and the rest point. Knockouts kill 25-32 of the m bytes at every point. Grouped by m
  over the 120 genotype-points ((1-u)^m at the mean m):

  | m | genotype-points | exact % | (1-u)^m % | strict % |
  | --- | --- | --- | --- | --- |
  | 37 | 45 | 89.2 | 89.5 | 92.0 |
  | 38-39 | 36 | 89.0 | 89.2 | 92.7 |
  | 40-42 | 25 | 88.5 | 88.4 | 92.9 |
  | 43-45 | 14 | 87.5 | 87.6 | 93.1 |

  Population, range over the four runs. Status `other` is a non-replicator whose trial did
  not reach copy depth 2 (`loose` and `prop` stay below 70 sites). Filled: a reference-inert
  offset (an own-site pointer) is non-inert. Re-ignitions are per window; their strict share
  comes from 300 sampled re-ignitions. The last column is the median, over strict genotypes
  with at least 10 copies, of their children's strict share:

  | tick | strict sites | filled % | `other` sites | filled % | copies by `other` (strict %) | re-ignitions | re-ignited strict % | genotype median strict % |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6008-6378 | 10-12 | 1398-1625 | 60-62 | 153-244 (2.6-5.1) | 4662-6137 | 14.0-23.0 | 83-87 |
  | 100k | 5177-5509 | 27-34 | 1958-2158 | 67-77 | 316-615 (2.0-2.8) | 5432-10234 | 10.0-13.7 | 82-89 |
  | 150k | 3933-4684 | 47-53 | 2456-2871 | 81-85 | 710-773 (0.6-2.3) | 8834-11611 | 4.3-17.3 | 80-86 |
  | 200k | 2703-3534 | 64-69 | 3180-3374 | 89-92 | 995-1630 (0.6-1.5) | 9270-16766 | 5.0-12.7 | 67-83 |
  | 250k | 1922-2372 | 69-76 | 3436-3686 | 93-95 | 1172-1581 (0.5-1.1) | 13107-19421 | 2.0-8.3 | 70-79 |
  | 300k | 1535-1903 | 67-81 | 3712-3917 | 94-96 | 1772-2351 (0.3-0.7) | 13789-17006 | 0.7-4.0 | 67-82 |
  | 350k | 1194-1607 | 64-81 | 3928-4116 | 95-96 | 1767-2439 (0.2-0.9) | 14757-23622 | 2.3-6.3 | 67-75 |
  | 400k | 961-1303 | 66-84 | 4043-4244 | 94-97 | 2064-2280 (0.1-0.4) | 15522-17977 | 0.3-1.3 | 64-80 |
  | 450k | 628-1079 | 68-81 | 4071-4405 | 95-97 | 2072-2675 (0.1-0.4) | 13001-22209 | 0.3-5.0 | 70-79 |
  | 500k | 670-976 | 59-79 | 4172-4501 | 96-97 | 2126-3243 (0.1-0.2) | 14570-19562 | 0.7-4.0 | 69-80 |

  - **Who copies.** Strict parents made 89-92% of all copy births at 50k, 50-62% at 200k and
    14-17% at 500k. Per strict site, their copies per window rose from 0.32-0.40 to
    0.63-0.70. Their mean length (non-inert bytes, volatile offsets excluded) grew from
    38.3-38.5 to 42.8-43.3. v17's 41 to 45 counts the volatile offsets too.
  - **Where the length went.** In the leading genotypes, polite's region (offsets 0-45)
    holds 37 non-inert bytes, or 38 when an own-site pointer offset is filled (0 of 12 at
    50k, 3-9 of 12 at later points). From 250k, 5-12 of 12 also carry 1-7 non-inert bytes
    at offsets 46-63, which polite copies but never executes.
  - **Mass.** Writes refused for lack of a free monomer start at 150-200k. At 500k free
    monomers are 4.7-6.3% of the initial 442,368.
  - **Balance (estimate).** For each 50k interval, take the strict sites at its start, add
    strict births (copies and re-ignitions, the mean of the two bounding windows times ten)
    and subtract the whole-program decays expected at 1.95e-6 per non-inert byte (0.40-0.45
    per strict site per 5k ticks). The result exceeds the strict sites at the end of the
    interval. The shortfall per strict site per 5k ticks is -0.01 to 0.16 up to 150k and
    0.08 to 0.72 after, against 0.40-0.45 from decay.

  Short-ancestor control: `ancestor()` (35 bytes, `anc=copier`) in place of polite,
  otherwise as `m195`. Probes `anc_s1` and `anc_s2` report every 5k ticks; `ps_run` repeats
  seeds 1-6 to 100k ticks. For seeds 1 and 2 the probe and `ps_run` end at the same tick.
  Under the same settings polite has 7.7-7.9k active sites at 50k.

  | seed | end | peak active (10k points) | births | `ps_run` digest |
  | --- | --- | --- | --- | --- |
  | 1 | extinct at 8,250 | - | 3 | 85d62f9bf9de8331 |
  | 2 | extinct at 83,389 | 42 | 177 | 6894fabfc01687c0 |
  | 3 | extinct at 97,376 | 59 | 945 | 5ddfdddbfc5a493b |
  | 4 | 14 active at 100k | 138 | 12,830 | 64a1c85f6793b212 |
  | 5 | 1 active at 100k | 142 | 7,506 | 8396121b1b6ca5d8 |
  | 6 | extinct at 55,998 | 74 | 1,011 | c76036d3393260d5 |

  - **Alone.** `ancestor()` and its variants in the probes (13 genotype-points, `ps_scan
    anc=copier`) give 91.8-92.8% strict first copies. `ancestor()` itself gives 92.25% (m 28,
    sensitive length 22.75, pred 93.4%; knockouts kill 23 of 28 bytes), against polite's
    92.0% (m 37, 26.5, 92.3%).
  - **In the run** (`anc_s2`):
    - Strict parents' children are strict in 72% of 29 copies at 5k, 48% of 29 at 10k and
      25% of 12 at 15k.
    - Residue per copy rises from 0.17 to 0.93 to 4.5; offsets written from another site
      rise from 0.07 to 0.66 to 2.25.
    - Non-replicators outnumber strict replicators from the first point: 17 against 9 at 5k
      and 34 against 8 at 10k. Of these non-replicators, 16 of 17 and 31 of 34 have a filled
      own-site pointer offset.

  No-copy-error control: `nomut_s1` and `nomut_s2` are `m195` with `p_mut` 0 (revision
  94a6475, which only renames the shift class; 2 jobs in 13 minutes). The pairs are s1 / s2:

  | tick | strict sites | `other` sites | strict sites filled % | strict children of strict parents % | env copies per window | copies by `other` (exact %) | re-ignited strict % |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 8672 / 8664 | 40 / 43 | 3 / 5 | 99.6 / 99.7 | 16 / 10 | 3 / 4 | 91 / 92 |
  | 100k | 8652 / 8630 | 32 / 50 | 7 / 9 | 99.5 / 99.3 | 16 / 26 | 5 / 3 | 95 / 96 |
  | 200k | 8576 / 8565 | 62 / 54 | 22 / 28 | 99.3 / 99.5 | 36 / 48 | 6 / 1 | 95 / 96 |
  | 300k | 8397 / 8383 | 122 / 172 | 50 / 56 | 98.8 / 97.2 | 67 / 83 | 11 / 17 | 91 / 93 |
  | 400k | 8206 / 7595 | 213 / 785 | 78 / 82 | 97.4 / 94.4 | 111 / 157 | 34 / 177 | 46 / 40 |
  | 500k | 7670 / 6306 | 623 / 1782 | 93 / 95 | 97.2 / 94.0 | 110 / 188 | 154 (71) / 780 (54) | 71 / 29 |

  - **Losses.** Without copy error, strict parents lose children almost only to env and
    multi. Gap copies number at most 2 per window. The total loss is 2.8-6.0% at 500k.
  - **Length.** Their mean length still grows, from 38.0 to 39.9-40.6.
  - **Mass.** Writes refused for lack of a free monomer occur only in s2's last window (20
    writes). Free monomers are 7.5-12.3% of the initial mass at 500k.
  - **Active sites at 500k.** 8.1-8.3k, against 4.9-5.2k with copy error.
  - **Balance.** The balance estimate above closes in every interval: the shortfall per
    strict site per 5k ticks is -0.01 to 0.03.
  - **`other` copies.** With copy error, 22-43% of the copies made by `other` parents are
    exact copies of the parent at every point (four runs).

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
about 26 times sooner, so v14 alone does not show which of the two changes matters; v15
separates them (below). Block
rotation without binding does not clear non-replicating sites. (v17 shows that the decline
returns under form M after 100k; the statements here hold to 100k.) Up to 1e-4 it has no clear
effect. From 1e-3 it cuts a third or more of all copies, replicators fall further than
under `dead0`, and non-replicators shift from copy-born to re-ignited. A cut copy ends by
igniting a site the parent wrote only in part, which fits that shift but was not measured
directly.

v15 reading (counts from executed runs; the mechanism is inference). Most of the effect of
form M comes from ending in-place damage. When a live program decays as a whole, a
replicator cannot lose replication and keep its site, so copy-born non-replicators fall to
15-18% of active sites, as under M. Clearing inactive code in one event raises replicator
numbers in either case but leaves the non-replicator share where per-byte decay of live
programs puts it.

v16 reading (counts from executed runs; mechanisms and estimates are inference):

- **Replicators barely change.** Per-op rates with a 30:1 spread change replicators very
  little within 100k ticks. Opcode bytes stay fixed.
- **Data bytes shift only weakly and late.** The only movement is in data bytes: by 100k
  their fast share is 0.2-1.0 points below the uniform-rate control in all eight runs. The
  shift is absent at 50k, and the replicator hazard did not fall. So data bytes are the only
  place selection shows, but the runs do not establish that selection replaces data bytes
  first.
- **A strong shift was not expected (estimate).** One fast-to-slow data substitution lowers
  polite's hazard by about (r_f - r_s) / h = 4.1e-6 / 8e-5, or 5%. 100k ticks are about eight
  replicator lifetimes.
- **The larger shift is in non-replicators.** The standing stock of non-replicators and
  inactive code shifts more, since decay filters it directly. Non-replicators do not
  reproduce, so this is survivorship, not heritable change.
- **The table sets lifetimes.** Polite's hazard under each table sets replicator lifetimes.
  The table where polite is most fragile (3) has the largest share and relative age of
  non-replicators.

v17 reading (counts from executed runs; mechanisms are inference):

- **The data-byte shift grows, then levels off.** It grows over the first 200k ticks to
  about 1 point below the uniform-rate control. It then stays there with a wider spread
  between runs, and the last point is the largest (-1.9).
- **Only data bytes shift.** Opcode bytes show no consistent shift over 500k. This fits the
  synonym inference in the design note: selection reaches data bytes and leaves opcodes.
  The shift is small next to the control's own mutational drift, which is 1.4-5.0 points
  over the same span.
- **The hazard falls only against the control.** The replicator hazard falls relative to
  the control, and the gap keeps widening to 500k (-3.1% on average). In absolute terms it
  rises: replicators lengthen and drift toward the composition of random bytes under both
  rates, and the per-op rates only slow the rise.
- **The decline returns under uniform form M.** The v14 statement that form M almost
  removes the decline, and the v15 non-replicator shares, hold to 100k only. In `m195`
  from 50k to 500k:
  - replicators fall 6-9x;
  - copy-born non-replicators grow from 12-14% to 61-65% of active sites;
  - exact births fall from 39-43% to 6-7%;
  - re-ignitions rise from 54-57% to 84-86% of births, while copy births stay near
    24-31k per 50k ticks.

  Form M has no in-place damage, so this decline has another source. The fall in exact
  births suggests that copies from evolved replicators more often yield non-replicators,
  but copy fidelity per genotype was not measured (v18 measures it).

v18 reading (counts from executed runs; which mechanism fills each class is inference):

- **The genotypes' own fidelity does not fall.**
  - Alone, the leading strict genotypes give 91-94% strict first copies at every point from
    50k to 500k. This is within about one point of the prediction from their substitution
    scans.
  - Their exact share falls with m as (1-u)^m, from 89.2% at m 37 to 87.5% at m 43-45. This
    is Eigen's quality factor for precise copies, Q = q^ν
    ([Eigen 1971](../../docs/references/pdf/eigen-1971-selforganization-of-matter.pdf#page=11),
    journal pp. 475 and 491).
  - Their strict share does not fall (92.0% to 93.1%), because the bytes they gained are
    neutral: the sensitive length stays at 23-28.

  Length growth costs exact copies, not replicating children.
- **The length grew outside the copy mechanism.** In the leading genotypes the growth is a
  filled own-site pointer offset and up to 7 bytes past polite's region, which are never
  executed. A copy error only replaces a non-inert byte with another (`src/ps_exec.cpp`), so
  these bytes did not come from an aligned copy of the parent. They came from other sites,
  from residue or from a misaligned copy, and were then copied along (inference). Without
  copy error, length grows too.
- **The short ancestor is no help here.** Alone, `ancestor()` is no more faithful than
  polite (92.25% against 92.0%). Under these settings it does not persist: 4 of 6 seeds are
  extinct by 100k, and the other two are down to 14 sites and 1. It was not modified.
  Polite's 11 extra bytes are its target check. Without the check, `ancestor()` copies into
  occupied sites, and under `fill` the refused writes leave chimeras: residue reaches 4.5
  offsets per copy by 15k.
- **Fidelity in the run falls, for environmental reasons.**
  - In the run, the same genotypes give 87% strict children at 50k and 68-78% from 200k.
  - Over all strict parents, losses rise from 16-18 points to 31-43 at 250-350k. Point
    losses (copy errors) stay at 4-7 points.
  - The rise is in three classes, none of which occurs alone:
    - env: mostly offsets written into the target by other sites;
    - gap: in step with writes refused for lack of a free monomer;
    - multi.
- **Lost copies are the smaller part of the decline.** From 50k to 500k, strict children
  per strict-parent copy fall by a factor of 1.16-1.25, while strict sites fall 6-9-fold.
  Per strict site, copies even rise.
  - **A further loss channel.** With copy error, the balance leaves a loss of strict sites
    beyond whole-program decay. After 150k it reaches 0.08-0.72 per site per 5k ticks,
    against 0.40-0.45 from decay. Without copy error the same balance closes. So the
    missing loss needs copy error somewhere, yet it does not pass through the parent's own
    failed copies.
  - **One route that fits (code inspection, not measured): in-place change by outside
    writes** (known issue 1). Offset 30 is both the direction of polite's source pointer
    and the address its loop jumps back to. A fill there turns a live polite into a program
    that copies from a neighbor; with `[30]=192` the census test finds a non-replicator.
    Mutants and `other` sites write more varied bytes than polite does. This would also fit
    two observations:
    - 22-43% of `other` copies are exact copies of the parent, though `other` genotypes
      make almost no copies alone;
    - 96-97% of `other` sites carry a filled offset.

    It was not measured.
- **Copy error accelerates a process that the environment alone also starts.** Without copy
  error, intrinsic fidelity is 1. Even so:
  - filled offsets spread to 93-95% of strict sites;
  - env copies rise about tenfold;
  - `other` sites grow from about 40 to 623 and 1782;
  - strict sites begin to fall after 300k.

  With copy error, the same signs appear by 100k and are larger by an order of magnitude.
- **Method and its limits.**
  - Testing offspring alone follows Avida practice. A04 section 5.2 tests offspring and
    descendant viability alone with a timeout, and notes that solitary tests miss
    interactions ([A04, PDF pp. 21-22, as recorded in the prior-work
    note](../../docs/research/shared-memory-prior-work.md)). Here the gap between alone and
    in-run is that interaction, and `other` genotypes that copy themselves in the run but
    not alone are a case of it.
  - Knockout and substitution scans are the kind of measurement Lenski et al. 1999 made in
    digital organisms (abstract only; see `docs/references/unavailable.md`).
  - The test alone covers first copies only, and only the three most-copied strict
    genotypes per run and point.
  - The balance uses windows of 5,000 ticks to stand for intervals of 50,000. Its
    re-ignition term comes from 300 sampled re-ignitions per window.
- **A next measurement** (proposal, not agreed). For each active site between census
  points, count status changes without a birth, and the offsets and writers of the changing
  bytes. Also record how each activation ends (whole decay or wick), by status.

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
