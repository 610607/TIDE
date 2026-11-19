# physub: physical-substrate exploration

An exploratory C++ model of a physics-like substrate for digital life. It is **not the TIDE
kernel**: the kernel will be written fresh under an agreed contract (see `AGENTS.md`). Every
rule and value here is provisional configuration for experiments, not a decided requirement.
Do not copy rules from here into `docs/substrate-primitives.md` until they are finalized.

Related design notes: [`docs/physical-substrate-model.md`](../../docs/physical-substrate-model.md),
[`docs/substrate-primitives.md`](../../docs/substrate-primitives.md). A summary of v13-v30
(conclusions, criterion 1, open questions) is in [`STATUS.md`](STATUS.md).

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
- **Writes into active sites** (`ext_active`, from v29): `allow` (default) or `refuse`. With
  `refuse`, a write that crosses into a neighbor holding an activation is refused whatever
  the bytes, and the writer still pays. Activity is read when writes are applied: after
  energy payment, before the tick's ignitions. The check comes after the wall crossing and
  before `ext_write`. Writes within a site and reads are unaffected, and the census trial
  runs under the same rule. `ps_probe` then adds `ext_active_blocked` to `# physics`.
- **Copy error** (`p_mut`, per byte): a `MOV` that reads a non-inert byte writes a random
  non-inert byte instead. `mut_scope` (from v30) sets which `MOV`s: `all` (default) or
  `cross`, only a `MOV` whose destination pointer names a neighbor. With `cross` a `MOV`
  into its own site (counter set-up and resets, probes) writes the byte it read, and a
  `MOV` into a neighbor draws its error exactly as under `all`. `INC`, `DEC` and `RND`
  carry no copy error, and the census trial runs without it.
- **Inert operands** (`inert_operand`): `zero` (default) reads an INERT operand byte as
  offset 0, like any other value mod `site_len`. With `fail`, an instruction with an INERT
  byte among its operands pays `e_op`, advances `ip` by its length and does nothing else.
  Pointer directions, data values, counters and the ledger are the same in both modes, and
  non-inert operands that name offset 0 (64, 128, 192) still do. A program that never
  executes an INERT operand runs bit for bit as under `zero` (`ps_test`).
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
| `apps/ps_census.hpp` | Census trial (founder top-up by default, or the seed-limited trial), strict-replicator test and copy-difference classes, shared by the probe and the scan |
| `apps/ps_scan.cpp` | Isolated first-copy fidelity, knockout and substitution scans of genotypes listed by the probe |
| `apps/ps_knockout.cpp` | Single-byte knockout of an ancestor without mutation or decay |
| `apps/ps_copycut.cpp` | First-copy cut probability of polite alone under block rotation |
| `tests/ps_test.cpp` | Ledgers, replay, walls, ancestor, starvation, bond barrier, act_cap, ext_write, ext_active, mut_scope, p_dead, energy diffusion, bond storage, dead_quiet, whole decay, block rotation, whole decay per class, per-op decay tables, census trial and its seeding limit, copy-difference classes, writer records and inert operands |
| `viewer/index.html` | Replay viewer (layers, inspector, timeline) |
| `scripts/run_jobs.sh`, `scripts/jobs/` | Parallel runner and the v8-v30 job lists |

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
run without rotation, so the census tests a program's own ability to copy itself. The
founder's bytes are drawn from the trial center's `mass0` free monomers. By default
(`census_topup=1`, from revision b4b4ea1) the center is first topped up to the program's
non-inert byte count after the volatile reset, so every program can be seeded; this adds
monomers to the trial world only and changes nothing for programs of at most `mass0` bytes.
With `census_topup=0` a program with more than `mass0` (48) non-inert bytes cannot be seeded
and counts as a non-replicator, whatever it does in the run (v22). That seed-limited verdict
is the one v13-v22 first recorded; v23 recomputes v17-v22 with the default, and v13-v16
keep the seed-limited counts.

A strict replicator is a replicator all of whose copies by the trial founder carry its key.
By default (`census_born=1`, from revision 34839f4) a key that is strict from the reset
volatile offsets is tried again in a second fresh trial, with its volatile offsets set to
the values an exact copy of the reference carries at birth (polite: so 223, direction 72,
do 225, probe 0; copier: 216, 72, 218; a test checks them against a trial). It is strict
only when both trials are. A key whose counter reset does not take effect (polite with 36
filled, for instance) copies in register from reset counters but off register when
copy-born (v25), so it now counts as a loose replicator. The two-carrier replicator verdict
and the other census fields keep the reset trial. With `census_born=1` the `# census` line
ends with `strict`, `born_fail` (active sites strict from reset values only) and
`born_fail_genotypes`. `census_born=0` gives the reset-only verdict of v18-v25 byte for byte;
the second trial adds about a quarter to the run time of v25's settings. v27 recomputes
v18-v25.

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
non-volatile bytes, with s_k the strict share of substitutions at k. Its `census_topup`
option works as the probe's and also applies to the founder of the first copies.

With `census=1` and `fate=1` (no rotation), `ps_probe` follows every activation from its
birth (or the seeding) to its end and adds seven lines per interval, covering the interval since
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
  volatile offsets of strict sites (not status changes), and the most changed offsets, for
  foreign and for self-written losses.
- `# fatestart`: of the strict activations lost in place (and of those written by the site
  itself), how many were ignited at offset 0, polite's entry; strict births ignited at offset
  0; and, for self-written losses, the offset of the instruction that ran in that tick.
- `# fateconv`: converted activations alive, their copy births, and how many children are
  strict, equal to the parent's key, or equal to the key of the neighbor that the parent's
  source pointer names. `fill:` the same for activations converted by a foreign write to the
  source-pointer direction alone, with their ends by cause and the summed ticks from
  conversion to end.

The observer runs extra trials for keys the census has not seen and hands the census the
verdicts for active sites, so all other lines, including the census `trials` count, are the
same as without `fate=1`.

With `fate=1`, `trace=1` adds five lines per interval (observation only; all other lines are
unchanged). The age of an activation is the ticks since its ignition, in buckets below 1,000,
1,000-9,999 and from 10,000.

- `# traceout`: strict activations lost in place by a change credited to a foreign writer.
  It gives the writer's status and age, its birth kind, whether it was ignited at offset 0,
  and the offset of the instruction it ran that tick. It also counts whether that byte is a
  `MOV` (`not_mov` counts the others) and whether the MOV's source pointer names the
  writer's own site (`src_own`). Then come the changed offsets. `dir` counts losses in which
  a changed byte was INERT and is a pointer direction of the victim; `dir_only` counts those
  in which all changed bytes are such. Pointer directions are the bytes that the victim
  key's executed MOV and IGNITE instructions (census trial `op_mask`) read as directions.
- `# traceign`: births of any status, and those ignited off offset 0. For strict births, it
  splits by entry and kind. For strict births off offset 0, it gives the igniter's status,
  age and instruction offset, and the entry offset. It also counts how many igniters carry
  the child's key, and how many children's sites last held a strict activation that ended
  by wick (ignited at 0 or not), with the summed ticks since that end.
- `# traceend`: strict activations by entry (offset 0 or not): ends by cause, summed
  lifetimes, and copy births they made.
- `# tracemass`: the ledger's free, code and wall mass, and the code bytes in active sites
  by status. For sites with code but no activation, it gives their number, bytes, how many
  have byte 0 inert, and how many carry a key already known as strict (no new trials).
- `# tracekey`: the census seeding limit. Active sites by status and by the non-inert bytes
  their key seeds in a trial (bins up to 40, 41-44, ..., 61-64); the sites whose key exceeds
  `mass0`, the number of such keys, and their verdict in a trial whose founder site is first
  topped up to the key's byte count. Under the default `census_topup=1` that is the census
  verdict; under `census_topup=0` it comes from a separate cache, so the census and its
  `trials` count are unchanged. Then strict losses in place (self / foreign writer), those
  whose new key exceeds `mass0`, and those strict once topped up (none by construction under
  `census_topup=1`); and
  copy births, those whose child carries the parent's key, and both again for parents whose
  key exceeds `mass0`.

With `trace=1` and polite as the reference, `route=1` adds three lines per interval
(observation only; all other lines are unchanged). Entry 0 means the activation was
ignited at offset 0; entry off means elsewhere.

- `# route`: writes refused for lack of a free monomer in the window (`no_mass`), and for
  each entry the strict ledger: count at the last checkpoint and now, the balance (equal to
  the count when every flow is caught), births by kind, gains in place (and found at the
  census), ends by decay and wick, and in-place losses by route. Each route is split by
  whether the old key holds at most `mass0` non-inert bytes or more. The routes, by the
  non-volatile offsets that changed and the writer credited as in `fate`:
  - `f30_mov15`: offset 30 alone, by a foreign writer whose instruction that tick was the
    `MOV` at offset 15 (polite's copy loop);
  - `f30_other`: offset 30 alone, by any other foreign instruction;
  - `f_ptr`: foreign, only the own-site pointer directions 34, 36, 38 and 40;
  - `f_tail`: foreign, only offsets 46-63;
  - `f_other`: any other foreign change;
  - `self_0` and `self_other`: the site wrote every changed byte, with offset 0 among them
    or not.
- `# routecopy`: every copy birth in the window by a strict parent, by the parent's entry
  and difference class (as `# fidcopy`), with the strict children in parentheses. For
  non-strict `env` children of entry-0 parents, it counts those whose foreign-written
  differing offsets are offset 30 alone, include 30, or are none (residue only). It also
  gives who last wrote the child's offset 30 and the most frequent foreign offsets.
- `# routeign`: strict births off offset 0 by igniter status and by the pointer that the
  igniter's `IGNITE` read, at p = [ip+1] mod 64 (direction [p], entry [p+1]). The pointer
  classes are:
  - `filled_36_38`: p is 36 or 38 and that own-site direction is filled;
  - `filled_ref`: p is offset 30, 34 or 40, filled;
  - `inert`: the operand byte is INERT, so p = 0 (none under `inert_operand=fail`, where such
    an `IGNITE` fails);
  - `dest_32`: polite's own neighbor pointer;
  - `other`: any other p;
  - `not_ignite`: the instruction run that tick was not an `IGNITE`.

  The line ends with the most frequent pointer offsets.

With `trace=1` and polite as the reference, `length=1` adds seven lines per interval
(observation only; all other lines are unchanged). They follow the strict activations
ignited at offset 0 (entry 0, as in `route`). The length z of a key is its non-inert byte
count after the volatile reset, as the census seeds it (polite: 40). Only the extra offsets
can lengthen a polite-like key: those where polite is INERT and not volatile (30, 34, 36,
38, 40) and the tail 46-63.

- `# length`: count and mean z at the last checkpoint and now, and a ledger of the change in
  the mean. Each event that changes the set or a member's z changes the running mean
  m = Z / N by an exact amount, credited to the event's category, so the credits of a window
  sum to the change (`sum_dm` equals `dmean`). `check_n` and `check_z` recompute N and Z from
  the tracked keys (both 0 when no event is missed). Per category: events, summed z (for
  `copy_sp`, the summed z_child - z_parent; for in-place changes, the summed dz) and credit.
  - Entries (credit (z - m) / (N + 1)): `copy_sp`, copy births by a strict entry-0 parent,
    whose credit splits into transmission `trans` = sum of (z_child - z_parent) / (N + 1)
    and the parent's place in the set, (z_parent - m) / (N + 1); `copy_op`, copy births by
    other parents; `reignite`; `self` (self-ignition); `gain`, strict status gained in place;
    `found`, sites strict at the first census.
  - Exits (credit -(z - m) / (N - 1)): `decay` (whole decay), `wick` (also a birth into a
    tracked site), `loss_f` and `loss_s`, strict status lost in place by a foreign writer or
    by the site.
  - In place, strict status kept (credit dz / N): `inplace_f` and `inplace_s`, by a foreign
    writer or by the site.
- `# lengthsrc`: where length comes from. For copy births by a strict entry-0 parent with a
  strict child, each non-volatile offset where the child differs from the parent's key at
  birth, by the writer record used in `census::diff_sources`: a byte added (parent INERT,
  child not) was left in the child's site (`add_residue`), last written from another site
  (`add_foreign`) or from the parent's site (`add_parent`); a byte lost (parent non-inert,
  child INERT) was not written (`lost_gap`) or last written by the parent (`lost_parent`) or
  another site (`lost_foreign`). Bytes and credit; z_child - z_parent = added - lost exactly.
  `subs` counts substitutions (both non-inert), which keep z. Then bytes changed in place in
  strict entry-0 activations, whatever their status after the change: made non-inert by a
  foreign `MOV` at offset 15 (polite's copy loop) or another foreign instruction, or by the
  site, and made INERT by the site or a foreign writer. The `MOV` at 15 is read from the
  writer's bytes after the tick: source pointer p = [16], source offset [p+1]. The write is
  `aligned` when the source is the writer's own site ([p] INERT) at the offset written,
  `shift` when its own site at another offset, and `nbrsrc` when [p] names a neighbor.
  Foreign additions are also counted by writer status (rep/loose/prop/other/self/none).
- `# lengthoff`: the same transmission and in-place counts per extra offset; `rest` sums
  the other offsets.
- `# lengthuse`: for live strict entry-0 activations, how many hold each extra offset
  non-inert. For exits in the window, per extra offset: how many held it non-inert, and of
  those, how many executed it or read it as control during the activation. Each tick the
  instruction an activation runs (ip and bytes at the start of the tick) marks its opcode
  and operand offsets as executed. It marks as control reads the pointer pairs [p], [p+1] of
  `MOV` and `IGNITE` and the operand target [x] of `INC`, `DEC`, `JZ`, `JMP`, `WALL` and
  `UNWALL`; not the byte a `MOV` copies, nor `RND`'s target. Under `inert_operand=fail` an
  instruction with an INERT operand marks nothing.
- `# lengthbin`: per z bin (up to 40, 41-44, ..., 57-60, 61-64; the bin of the current z),
  exposure in activation-ticks, copy births, those with a strict child, those whose child
  carries the parent's key, whole decays, wick ends, and losses in place by a foreign writer
  and by the site.
- `# lengthcomp`: the same fields by composition: filled pointer directions among 34, 36,
  38 and 40 (0, 1, 2 or more) by filled tail bytes (0, 1-6, 7-12, 13-18).

- `# lengthptr` (from revision 3227e87): the same activations by the state of polite's
  counter pointers. Polite sets its counters so ([31]) and do ([33]) to K at the start of
  each cycle through the pointers whose directions are 36 and 38. With 36 or 38 filled,
  that `MOV` writes into a neighbor and the own counter keeps its value. The state is none,
  36 filled (`f36`), 38 filled (`f38`) or both, and in or off register: whether
  [31] - [33] is 0 mod 64. The line gives, per state: live activations at the checkpoint
  (bytes at the start of the tick, so a site between its two `INC`s counts as off
  register); copy births in the window by such parents, as copies, strict children,
  children carrying the parent's key, and `multi` and `env` children (`census::diff_sources`;
  parent bytes after the birth tick); and bytes they added in place to strict entry-0
  activations through the `MOV` at 15, all and by `rep` writers (writer bytes after the
  tick). It ends with the in-place `shift` additions by (source offset - written offset)
  mod 64.

`length=1` needs `trace=1` and `anc=polite`.

With `route=1` and `length=1`, `role=1` (from v28) adds two lines per interval (observation
only; all other lines are unchanged). They split the changed bytes by the role INERT played
there. The roles of a key's offsets are read statically from the key and the offsets where
its census founder executed an instruction (`census::key_roles`): `dir`, a pointer
direction read by `MOV`, `IGNITE`, `WALL` or `UNWALL`; `opnd`, an operand byte; `val`, a
pointer offset or the target of `INC`, `DEC`, `JZ` or `JMP`. A changed byte is `dir`,
`opnd`, `val` or `none` (INERT before, the first role that applies, else an empty slot
only), or `sub` (non-inert before). A change is `dir_only` when every changed byte is `dir`,
`dir_mixed` when some are, else the first of `opnd`, `val`, `sub` and `none` present.

- `# role`: per entry, each loss route of `# route` split by change class, with `kept`: the
  losses whose key is strict again (census verdict) when the `dir` bytes written by another
  site are put back to INERT. This is a first-order counterfactual for an own-site direction
  code that is not INERT, so that `fill` refuses foreign writes there; it does not follow
  the run further. Then gains in place by class, with `undone` (not strict once the foreign
  `dir` bytes are put back), and the offsets of those foreign `dir` bytes in losses.
- `# rolelen`: for strict entry-0 activations (as `# length`), bytes changed in place with
  strict status kept, foreign and by the site, by kind (added as `dir`, `opnd`, `val` or
  `none`, removed, substituted) with their credit; exits by loss in place by class, with
  their credit and the `kept` part; bytes added in copies (as `# lengthsrc`) by source and
  by their role in the parent's key; for non-strict `env` children of strict entry-0 parents,
  the foreign-written differing offsets by role in the parent's key; and the offsets of
  in-place `dir` additions.

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
  minutes on 4 cores; counts recomputed in v23). Under the seed-limited census, the census
  and class lines at 50k and 100k equal those of v16, apart from the cached trial count.
  The tables below use the topped-up census (v23 runs `t1_s1` to `t4_s2` and, as controls,
  `zero_m195_s1/s2`, whose rows equal v17's). Each table's control is `m195` of the same
  seed, measured under that table.

  Replicator data bytes: fast share, treatment minus control (percentage points):

  | tick | t1_s1 | t1_s2 | t2_s1 | t2_s2 | t3_s1 | t3_s2 | t4_s1 | t4_s2 | mean |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | +0.17 | -0.22 | -0.18 | +0.02 | -0.16 | -0.20 | -0.20 | -0.50 | -0.16 |
  | 100k | -0.67 | -0.46 | -0.32 | -0.49 | -0.99 | -0.55 | -0.53 | -0.93 | -0.62 |
  | 150k | -1.33 | -0.92 | -0.62 | -0.47 | -1.55 | -1.07 | -1.08 | -1.41 | -1.06 |
  | 200k | -1.57 | -1.25 | -0.56 | -0.85 | -1.53 | -0.78 | -1.69 | -1.88 | -1.26 |
  | 250k | -1.97 | -1.48 | -0.59 | -1.29 | -1.48 | -0.82 | -2.59 | -1.96 | -1.52 |
  | 300k | -2.08 | -1.75 | -0.44 | -2.05 | -0.55 | -1.51 | -3.14 | -1.66 | -1.65 |
  | 350k | -3.08 | -1.66 | -0.80 | -2.76 | -0.99 | -1.92 | -3.50 | -2.20 | -2.11 |
  | 400k | -3.50 | -1.19 | -0.73 | -3.05 | -1.53 | -2.54 | -3.32 | -1.59 | -2.18 |
  | 450k | -3.87 | -0.54 | -0.95 | -3.06 | -2.11 | -2.06 | -4.33 | -2.17 | -2.39 |
  | 500k | -4.05 | -1.64 | -1.54 | -3.78 | -1.99 | -2.46 | -4.27 | -2.41 | -2.77 |

  Replicator hazard, treatment over control minus 1 (%):

  | tick | t1_s1 | t1_s2 | t2_s1 | t2_s2 | t3_s1 | t3_s2 | t4_s1 | t4_s2 | mean |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | -0.4 | -0.1 | -0.2 | -0.5 | -0.4 | +0.4 | -0.4 | -1.2 | -0.34 |
  | 100k | -0.3 | +0.9 | -0.9 | -1.3 | -0.5 | +0.6 | -1.0 | -1.8 | -0.55 |
  | 150k | -0.6 | +2.0 | -1.8 | -1.4 | -0.2 | +0.6 | -2.3 | -2.8 | -0.81 |
  | 200k | -2.0 | +1.2 | -2.3 | -2.3 | -0.6 | +0.4 | -3.2 | -3.1 | -1.49 |
  | 250k | -4.0 | +0.8 | -2.7 | -2.4 | -1.9 | -0.1 | -4.7 | -3.4 | -2.29 |
  | 300k | -5.4 | +0.1 | -2.4 | -2.3 | -2.2 | +0.6 | -5.4 | -3.0 | -2.51 |
  | 350k | -6.8 | -0.0 | -3.8 | -3.4 | -3.7 | +0.1 | -6.0 | -3.7 | -3.41 |
  | 400k | -8.4 | +0.7 | -3.2 | -2.8 | -4.4 | -0.3 | -5.4 | -2.3 | -3.25 |
  | 450k | -8.8 | +1.2 | -2.5 | -2.9 | -4.1 | +0.8 | -6.0 | -2.9 | -3.15 |
  | 500k | -8.6 | -0.7 | -3.6 | -4.1 | -3.9 | +0.1 | -6.3 | -3.1 | -3.77 |

  Uniform form M (`m195`) over 500k. Births are per 50k-tick window; re-ignitions are births
  into code already present:

  | tick | replicators s1 / s2 | polite region intact | copy-born non-rep (% of active) | exact births % | re-ignitions (% of births) | replicator length |
  | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6567 / 6430 | 3270 / 2895 | 10% / 11% | 43 / 39 | 54% / 57% | 41.8 / 42.2 |
  | 100k | 5878 / 6060 | 1785 / 1746 | 11% / 11% | 24 / 24 | 72% / 69% | 42.9 / 43.1 |
  | 150k | 5463 / 5552 | 776 / 803 | 12% / 13% | 16 / 19 | 78% / 74% | 44.8 / 44.8 |
  | 200k | 4838 / 4632 | 283 / 277 | 15% / 18% | 12 / 11 | 80% / 82% | 47.1 / 46.8 |
  | 250k | 3978 / 3941 | 96 / 162 | 20% / 21% | 9 / 8 | 82% / 84% | 49.1 / 48.5 |
  | 300k | 3491 / 3702 | 51 / 115 | 24% / 21% | 8 / 8 | 83% / 84% | 50.7 / 49.7 |
  | 350k | 3363 / 3695 | 37 / 98 | 25% / 22% | 8 / 8 | 84% / 84% | 52.0 / 50.8 |
  | 400k | 3301 / 3521 | 28 / 65 | 23% / 22% | 7 / 8 | 85% / 84% | 53.0 / 51.6 |
  | 450k | 3381 / 3256 | 41 / 28 | 24% / 25% | 8 / 7 | 84% / 83% | 53.5 / 52.4 |
  | 500k | 3013 / 3301 | 54 / 6 | 26% / 24% | 6 / 7 | 86% / 84% | 54.0 / 52.9 |

  - **Data-byte shift.**
    - The mean over the eight runs grows from -0.16 points at 50k to -1.06 at 150k, -1.65
      at 300k and -2.77 at 500k (runs: -1.5 to -4.3). Under the seed-limited census it held
      at -1.1 to -1.2 from 200k to 450k; that plateau does not appear here.
    - From 100k on, every run is below its control at every point.
    - After 200k single runs move by up to 1.1 points from one point to the next; for
      example, t1_s2 is -0.54 at 450k and -1.64 at 500k.
  - **The control drifts too.** Under uniform rates, the data-byte fast share drifts toward
    the share in random bytes (44-45%). From 50k to 500k:
    - table 1: 50.1-50.4% to 46.0-48.1%;
    - table 2: 41.5-42.0% to 42.7-44.1%;
    - table 3: 60.8-60.9% to 53.0-53.5%;
    - table 4: 31.1-31.6% to 37.5-38.6%.

    The treatment stays below the control whichever way the control drifts.
  - **Replicator hazard against the control.**
    - The mean gap is -0.6% at 100k, -1.5% at 200k, -2.5% at 300k, -3.3% at 400k and -3.8%
      at 500k (runs: -8.6 to +0.1%).
    - Six runs are below their controls at every point; t1_s1 is furthest (-8.6% at 500k).
      The other two are not: t1_s2 is above its control at 100-300k and 400-450k (up to
      +2.0%), and t3_s2 stays within -0.3 to +0.8% of its control at every point.
  - **Absolute hazard rises.** From 50k to 500k it rises in every treatment run by
    15.6-29.4% and in every control by 16.8-37.5%. In both, replicators lengthen from
    41.6-42.4 to 52.7-54.7 non-inert bytes, and their composition drifts toward that of
    random bytes.
  - **Opcode bytes** show no consistent shift: the mean over the eight runs stays within
    -0.08 to +0.07 points. After 300k single runs depart by up to 0.8 points in both
    directions (t3_s1 -0.76 at 450k; t2_s2 +0.64 at 500k).
  - **Population.**
    - Replicators fall in treatment and control alike: from 6.3-6.9k at 50k to 2,983-3,290
      at 500k, against 3,013 and 3,301 in the controls.
    - Copy-born non-replicators make up 24-27% of active sites at 500k, against 24-26% in
      the controls.
    - Polite's region is intact in 0-39 replicators per run at 500k (controls: 6-54).

- **v18** (copy fidelity under form M to 500k ticks; revision 80f9fcf, job list
  `v18_fidelity.txt`; 12 jobs in 22 minutes on 4 cores; counts recomputed in v23; strict
  verdict from reset counters, see v27). Four runs repeat v17 `m195_s1`, `m195_s2`, `t2_s1`
  and `t3_s1` with `fidelity=5000`: every copy birth in the last 5,000 ticks before each 50k
  point is classified, and parent and child are judged by the census. Their rows and their
  census, class, substitution and physics lines equal v17's to 500k (trial counts aside).
  Below, a strict parent or child is one whose genotype is a strict replicator in the
  topped-up census trial (v23 runs `zero_m195_s1/s2`, `t2_s1` and `t3_s1`). `ps_scan` then
  tested the three strict genotypes with the most copies per run and point, 120
  genotype-points in all (`ps_scan label=RUN first=400 subs=4 < runs/v23/RUN.tsv`, at
  revision b4b4ea1).

  Copies by strict parents in the window / strict children among them (%):

  | tick | m195_s1 | m195_s2 | t2_s1 | t3_s1 |
  | --- | --- | --- | --- | --- |
  | 50k | 2439 / 83.5 | 2433 / 82.4 | 2129 / 83.3 | 2658 / 84.5 |
  | 100k | 2078 / 79.0 | 2303 / 80.6 | 1805 / 79.5 | 2378 / 78.6 |
  | 150k | 2115 / 76.3 | 2367 / 77.3 | 1872 / 77.3 | 2315 / 73.7 |
  | 200k | 2267 / 70.8 | 2406 / 66.1 | 1991 / 71.7 | 2547 / 68.3 |
  | 250k | 2318 / 62.0 | 2381 / 64.8 | 2140 / 61.7 | 2460 / 62.2 |
  | 300k | 2411 / 59.2 | 2336 / 65.8 | 2178 / 59.5 | 2473 / 66.1 |
  | 350k | 2509 / 56.7 | 2450 / 62.2 | 2167 / 60.6 | 2374 / 62.4 |
  | 400k | 2446 / 64.7 | 2465 / 65.0 | 2054 / 60.4 | 2384 / 64.9 |
  | 450k | 2546 / 63.5 | 2523 / 60.8 | 2074 / 60.8 | 2387 / 61.8 |
  | 500k | 2318 / 65.0 | 2484 / 62.9 | 2163 / 66.2 | 2334 / 67.6 |

  Strict-parent copies whose child is not strict, by class, in percentage points of all
  strict-parent copies (mean over the four runs, range in parentheses). The last two columns
  give the differing offsets per copy written from another site / left in the target
  (residue), as a four-run mean, and the writes refused in the window because the target
  site had no free monomer:

  | tick | point | gap | multi | env | total | foreign / residue per copy | no-mass writes |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6.2 (5.7-6.9) | 0.3 (0.2-0.5) | 3.2 (2.9-3.7) | 6.9 (6.3-7.7) | 16.6 (15.5-17.6) | 0.62 / 0.08 | 0 |
  | 100k | 5.7 (5.4-6.2) | 0.4 (0.2-0.5) | 4.1 (3.2-4.6) | 10.4 (8.9-12.2) | 20.6 (19.4-21.4) | 1.06 / 0.10 | 0 |
  | 150k | 5.2 (5.0-5.3) | 0.7 (0.3-1.3) | 5.2 (4.6-5.5) | 12.8 (11.8-14.6) | 23.8 (22.6-26.3) | 1.29 / 0.14 | 5-348 |
  | 200k | 4.1 (3.9-4.4) | 2.9 (1.4-4.9) | 6.6 (5.7-7.5) | 17.2 (16.1-18.2) | 30.8 (28.3-33.9) | 1.80 / 0.22 | 924-2412 |
  | 250k | 4.2 (3.6-5.0) | 6.2 (3.8-8.4) | 8.6 (8.1-9.6) | 18.3 (17.6-19.8) | 37.3 (35.2-38.3) | 1.74 / 0.26 | 3067-5874 |
  | 300k | 4.2 (3.7-4.7) | 4.6 (2.9-7.1) | 10.1 (9.5-10.5) | 18.5 (16.7-20.8) | 37.4 (33.9-40.8) | 1.67 / 0.24 | 2494-6799 |
  | 350k | 4.0 (3.5-4.5) | 5.5 (4.1-8.6) | 11.2 (9.7-12.0) | 18.8 (17.7-19.5) | 39.5 (37.6-43.3) | 1.62 / 0.20 | 3448-10266 |
  | 400k | 4.9 (4.6-5.3) | 3.7 (2.9-4.1) | 10.9 (9.7-12.0) | 16.8 (15.2-19.3) | 36.3 (35.0-39.6) | 1.50 / 0.20 | 2518-4454 |
  | 450k | 4.4 (4.1-5.0) | 4.8 (4.0-5.4) | 11.9 (11.5-12.4) | 17.1 (16.1-17.8) | 38.3 (36.5-39.2) | 1.52 / 0.18 | 4838-6472 |
  | 500k | 4.6 (4.2-4.8) | 3.1 (2.0-5.2) | 10.5 (9.1-12.2) | 16.4 (15.2-17.2) | 34.6 (32.4-37.1) | 1.50 / 0.17 | 1457-7882 |

  The same genotypes in the run and alone. In the run: the strict share of the children of
  the 12 genotypes (three per run), weighted by their copies; from 250k these are 197-301
  copies per point. Alone: 400 first copies per genotype in a 9x9 world with copy error and
  no decay. m counts non-inert, non-volatile bytes. The sensitive length is m minus the
  summed share of substitutions that leave a strict replicator, and pred is the first-order
  strict share from substitutions alone:

  | tick | copies | in-run strict % | alone: strict % | alone: exact % | (1-u)^m % | m | sensitive length | pred % |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 5378 | 87.6 | 91.8-92.0 | 88.0-89.2 | 89.5 | 37 | 26.5-26.8 | 92.2-92.3 |
  | 100k | 2757 | 84.6 | 91.8-93.0 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.5-26.8 | 92.2-93.1 |
  | 150k | 1321 | 84.0 | 91.8-93.0 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.5-26.8 | 92.2-93.1 |
  | 200k | 563 | 76.0 | 91.5-93.2 | 89.0-89.2 | 89.2-89.5 | 37-38 | 23.2-26.5 | 92.3-93.2 |
  | 250k | 301 | 72.1 | 92.0-93.0 | 86.0-89.2 | 86.1-89.5 | 37-50 | 22.5-26.5 | 92.3-93.3 |
  | 300k | 197 | 76.7 | 92.0-93.2 | 85.8-89.2 | 84.8-89.5 | 37-55 | 22.5-26.8 | 92.2-93.2 |
  | 350k | 241 | 49.8 | 91.2-93.2 | 82.8-89.5 | 85.0-89.5 | 37-54 | 22.8-27.8 | 92.0-93.3 |
  | 400k | 234 | 62.4 | 91.2-93.8 | 85.0-89.2 | 84.5-89.2 | 38-56 | 22.8-27.5 | 92.0-93.3 |
  | 450k | 239 | 72.4 | 91.2-93.5 | 86.2-89.2 | 86.3-89.2 | 38-49 | 23.0-28.0 | 91.9-93.2 |
  | 500k | 215 | 76.7 | 91.2-93.5 | 85.0-89.2 | 84.5-89.2 | 38-56 | 20.8-28.0 | 91.9-93.6 |

  None of the 48,000 first copies alone fell in the gap, multi or env class: 83-90% were
  exact and the rest point. Knockouts kill 25-32 of the m bytes at every point. Grouped by m
  over the 120 genotype-points ((1-u)^m at the mean m):

  | m | genotype-points | exact % | (1-u)^m % | strict % |
  | --- | --- | --- | --- | --- |
  | 37 | 44 | 89.2 | 89.5 | 92.0 |
  | 38-39 | 24 | 88.9 | 89.2 | 92.7 |
  | 40-42 | 18 | 88.5 | 88.3 | 93.0 |
  | 43-45 | 8 | 87.4 | 87.5 | 93.0 |
  | 46-49 | 11 | 86.6 | 86.7 | 93.1 |
  | 50-53 | 6 | 85.9 | 85.7 | 93.1 |
  | 54-56 | 9 | 85.1 | 84.9 | 93.1 |

  Population, range over the four runs. Status `other` is a non-replicator whose trial did
  not reach copy depth 2 (`loose` stays at most 52 sites and `prop` at most 101). Filled: a
  reference-inert offset (an own-site pointer) is non-inert. Re-ignitions are per window;
  their strict share comes from 300 sampled re-ignitions. The last column is the median,
  over strict genotypes with at least 10 copies, of their children's strict share:

  | tick | strict sites | filled % | `other` sites | filled % | copies by `other` (strict %) | re-ignitions | re-ignited strict % | genotype median strict % |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6385-6605 | 11-13 | 1131-1194 | 61-65 | 72-107 (5.3-10.3) | 4662-6137 | 14.3-23.3 | 83-87 |
  | 100k | 5689-6014 | 29-37 | 1349-1614 | 65-79 | 104-402 (4.0-5.8) | 5432-10234 | 11.3-15.7 | 82-89 |
  | 150k | 5006-5515 | 52-60 | 1506-1748 | 83-87 | 184-435 (1.1-7.1) | 8834-11611 | 4.7-18.7 | 80-85 |
  | 200k | 4182-4899 | 71-77 | 1681-1837 | 90-92 | 238-714 (1.7-7.1) | 9270-16766 | 7.0-19.0 | 73-83 |
  | 250k | 3563-3953 | 80-84 | 1782-2066 | 94-96 | 219-484 (2.5-8.1) | 13107-19421 | 4.3-11.7 | 64-80 |
  | 300k | 3413-3663 | 81-88 | 1805-2000 | 94-97 | 545-924 (1.3-2.6) | 13789-17006 | 1.7-13.7 | 67-75 |
  | 350k | 3329-3653 | 82-90 | 1791-1954 | 96-97 | 214-703 (2.3-8.4) | 14757-23622 | 7.3-9.7 | 64-80 |
  | 400k | 3153-3494 | 84-92 | 1755-1965 | 96-98 | 284-729 (2.5-3.7) | 15522-17977 | 2.7-7.3 | 65-80 |
  | 450k | 2957-3365 | 86-93 | 1747-2003 | 96-98 | 283-729 (1.8-6.7) | 13001-22209 | 7.0-9.0 | 67-71 |
  | 500k | 2984-3280 | 87-92 | 1776-1861 | 96-98 | 332-1367 (0.7-4.3) | 14570-19562 | 3.0-8.7 | 69-75 |

  - **Who copies.** Strict parents made 94-95% of all copy births at 50k, 77-90% at 200k and
    63-85% at 500k. Per strict site, their copies per window rose from 0.32-0.40 to
    0.66-0.78. Their mean length (non-inert bytes at the parent site) grew from 38.7-39.4 to
    50.8-51.9.
  - **Where the length went.** In the leading genotypes, polite's region (offsets 0-45)
    holds 37 non-inert bytes, or 38 when an own-site pointer offset is filled (0 of 12 at
    50k, 3-10 of 12 at later points). From 250k, 6-12 of 12 also carry 1-18 non-inert bytes
    at offsets 46-63, which polite copies but never executes.
  - **Mass.** Writes refused for lack of a free monomer start at 150-200k. At 500k free
    monomers are 4.7-6.3% of the initial 442,368.
  - **Balance (estimate).** For each 50k interval, take the strict sites at its start, add
    strict births (copies and re-ignitions, the mean of the two bounding windows times ten)
    and subtract the whole-program decays expected at 1.95e-6 per non-inert byte of the
    replicators' mean length (0.41-0.52 per strict site per 5k ticks). The result exceeds
    the strict sites at the end of the interval. The shortfall per strict site per 5k ticks
    is -0.02 to 0.22 up to 150k and 0.06 to 0.54 after, against 0.41-0.52 from decay.

  Short-ancestor control: `ancestor()` (35 bytes, `anc=copier`) in place of polite,
  otherwise as `m195`. Probes `anc_s1` and `anc_s2` report every 5k ticks (census counts
  recomputed in v23 from the runs of the same names; already at 5k a site holding the
  ancestor plus residue can be past 48 bytes); `ps_run` repeats seeds 1-6 to 100k ticks.
  For seeds 1 and 2 the probe and `ps_run` end at the same tick. Under the same settings
  polite has 7.7-7.9k active sites at 50k.

  | seed | end | peak active (10k points) | births | `ps_run` digest |
  | --- | --- | --- | --- | --- |
  | 1 | extinct at 8,250 | - | 3 | 85d62f9bf9de8331 |
  | 2 | extinct at 83,389 | 42 | 177 | 6894fabfc01687c0 |
  | 3 | extinct at 97,376 | 59 | 945 | 5ddfdddbfc5a493b |
  | 4 | 14 active at 100k | 138 | 12,830 | 64a1c85f6793b212 |
  | 5 | 1 active at 100k | 142 | 7,506 | 8396121b1b6ca5d8 |
  | 6 | extinct at 55,998 | 74 | 1,011 | c76036d3393260d5 |

  - **Alone.** `ancestor()` and its variants in the probes (12 genotype-points, `ps_scan
    anc=copier`) give 91.8-93.8% strict first copies; the highest is a 62-byte site (m 60)
    whose extra bytes are residue. `ancestor()` itself gives 92.25% (m 28, sensitive length
    22.75, pred 93.4%; knockouts kill 23 of 28 bytes), against polite's 92.0% (m 37, 26.5,
    92.3%).
  - **In the run** (`anc_s2`):
    - Strict parents' children are strict in 70% of 33 copies at 5k, 44% of 32 at 10k and
      18% of 17 at 15k.
    - Residue per copy rises from 0.33 to 1.03 to 4.65; offsets written from another site
      rise from 0.36 to 0.84 to 2.18.
    - Non-replicators are 12 against 14 strict replicators at 5k and outnumber them from
      10k: 30 against 12, and 23 against 5 at 15k. Of these non-replicators, 11 of 12 and 28
      of 30 have a filled own-site pointer offset.

  No-copy-error control: `nomut_s1` and `nomut_s2` are `m195` with `p_mut` 0 (revision
  94a6475, which only renames the shift class; 2 jobs in 13 minutes; counts recomputed in
  v23 from `zero_nomut_s1/s2`). The pairs are s1 / s2; the exact share of `other` copies is
  given from 100 copies:

  | tick | strict sites | `other` sites | strict sites filled % | strict children of strict parents % | env copies per window | copies by `other` (exact %) | re-ignited strict % |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 8677 / 8673 | 32 / 33 | 3 / 5 | 99.7 / 99.7 | 16 / 10 | 3 / 4 | 91 / 92 |
  | 100k | 8658 / 8638 | 24 / 41 | 7 / 10 | 99.6 / 99.5 | 16 / 26 | 5 / 2 | 95 / 96 |
  | 200k | 8596 / 8577 | 35 / 41 | 22 / 28 | 99.3 / 99.5 | 36 / 48 | 4 / 1 | 95 / 96 |
  | 300k | 8438 / 8476 | 76 / 78 | 50 / 57 | 98.9 / 98.0 | 67 / 84 | 2 / 4 | 91 / 95 |
  | 400k | 8296 / 8192 | 120 / 179 | 78 / 83 | 97.2 / 96.4 | 119 / 184 | 4 / 14 | 47 / 44 |
  | 500k | 8089 / 7717 | 193 / 358 | 93 / 96 | 96.8 / 94.6 | 143 / 256 | 7 / 253 (0) | 76 / 35 |

  - **Losses.** Without copy error, strict parents lose children almost only to env and
    multi. Gap copies number at most 5 per window. The total loss is 3.2-5.4% at 500k.
  - **Length.** Their mean length still grows, from 38.0 to 40.8-42.9.
  - **Mass.** Writes refused for lack of a free monomer occur only in s2's last window (20
    writes). Free monomers are 7.5-12.3% of the initial mass at 500k.
  - **Active sites at 500k.** 8.1-8.3k, against 4.9-5.2k with copy error.
  - **Balance.** These runs have no class lines, so the strict parents' mean length stands
    in for the replicators' in the estimate above. The shortfall per strict site per 5k
    ticks is then 0.01 to 0.06, against 0.37-0.41 from decay.
  - **`other` copies.** With copy error, 0-7% of the copies made by `other` parents are
    exact copies of the parent at every point (four runs). The seed-limited census found
    22-43%, because it counted long strict parents as `other`.
- **v19** (activation fates under form M to 500k ticks; revision 2280ebf, job list
  `v19_fate.txt`; 4 jobs in 43 minutes on 4 cores; counts recomputed in v23; strict verdict
  from reset counters, see v27). The runs repeat v18 `m195_s1`, `m195_s2`, `nomut_s1` and
  `nomut_s2` with `fate=1`. Every other line equals v18's to 500k (v18's m195 outputs print
  `multi` as `shift`). At all 40 checkpoints the strict balance equals the strict count, and
  the census mismatch, untracked, stale and replaced counts are 0, under the seed-limited
  census and again under the topped-up one. Earlier runs of the same jobs at 8368700 and
  9cc7ff8, before the start and fill counts were added, gave the same counts on every shared
  line. Below, "strict" is the census status (topped-up, from the v23 runs `zero_m195_s1/s2`
  and `zero_nomut_s1/s2`); "in place" means without a birth.

  Strict activations per 50k window with copy error (s1 / s2). Births are copy births plus
  re-ignitions (no self-ignitions occurred). A neighbor's fill of 30 is an in-place loss
  whose only non-volatile change is offset 30, written by another site:

  | tick | strict at end | births | ended: decay | ended: wick | lost in place | of which neighbor fill of 30 | gained in place | births - ends | in place, net |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6522 / 6385 | 24765 / 25640 | 16823 / 16429 | 348 / 1236 | 1561 / 2038 | 636 / 693 | 488 / 447 | +7594 / +7975 | -1073 / -1591 |
  | 100k | 5850 / 6014 | 27823 / 27510 | 25269 / 25429 | 1017 / 715 | 3374 / 2297 | 1026 / 976 | 1165 / 560 | +1537 / +1366 | -2209 / -1737 |
  | 150k | 5433 / 5515 | 28537 / 27467 | 23716 / 24445 | 2752 / 552 | 3437 / 4673 | 1314 / 1271 | 951 / 1704 | +2069 / +2470 | -2486 / -2969 |
  | 200k | 4819 / 4595 | 30630 / 27472 | 22642 / 22499 | 5951 / 3002 | 4028 / 4970 | 1530 / 1713 | 1377 / 2079 | +2037 / +1971 | -2651 / -2891 |
  | 250k | 3953 / 3903 | 25792 / 24304 | 19490 / 19387 | 4080 / 2557 | 3781 / 4133 | 1688 / 1857 | 693 / 1081 | +2222 / +2360 | -3088 / -3052 |
  | 300k | 3462 / 3663 | 22526 / 24322 | 17848 / 17875 | 2076 / 4108 | 4152 / 2884 | 1703 / 1743 | 1059 / 305 | +2602 / +2339 | -3093 / -2579 |
  | 350k | 3329 / 3653 | 25750 / 26131 | 17077 / 17751 | 5984 / 5626 | 4338 / 3627 | 1598 / 1731 | 1516 / 863 | +2689 / +2754 | -2822 / -2764 |
  | 400k | 3280 / 3494 | 22803 / 25229 | 16298 / 17463 | 3967 / 5441 | 3924 / 3474 | 1662 / 1630 | 1337 / 990 | +2538 / +2325 | -2587 / -2484 |
  | 450k | 3365 / 3235 | 23204 / 25130 | 16301 / 16685 | 4298 / 5790 | 3066 / 3470 | 1600 / 1717 | 546 / 556 | +2605 / +2655 | -2520 / -2914 |
  | 500k | 2984 / 3280 | 25023 / 27973 | 16108 / 16298 | 6217 / 8255 | 4215 / 4256 | 1732 / 1720 | 1136 / 881 | +2698 / +3420 | -3079 / -3375 |

  Totals after 150k (windows ending 200k-500k). Percentages are shares of all strict
  activations that ended or were lost in place:

  | run | net | births | decay | wick | lost in place | neighbor fill of 30 | gained in place | births - ends | in place, net |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | m195_s1 | -2449 | 175728 | 125764 (67.7%) | 32573 (17.5%) | 27504 (14.8%) | 11513 (6.2%) | 7664 | +17391 | -19840 |
  | m195_s2 | -2235 | 180561 | 127958 (67.5%) | 34779 (18.3%) | 26814 (14.1%) | 12111 (6.4%) | 6755 | +17824 | -20059 |
  | nomut_s1 | -530 | 241017 | 239529 (99.1%) | 285 (0.1%) | 1974 (0.8%) | 628 (0.3%) | 241 | +1203 | -1733 |
  | nomut_s2 | -889 | 243111 | 240533 (98.3%) | 687 (0.3%) | 3393 (1.4%) | 1149 (0.5%) | 613 | +1891 | -2780 |

  - **With copy error, births exceed ends in every window.** Births minus decay and wick
    ends is +1,971 to +3,420 per window after 150k. The count falls because in-place losses
    exceed in-place gains; after 150k the net in-place loss is 8.1-9.0 times the net
    decline. Without copy error, births and ends nearly balance (-48 to +1,466 per window
    from 100k; +1,203 and +1,891 in total after 150k), and the net in-place loss is 3.1-3.3
    times the net decline.
  - **Rates per strict site per 5,000 ticks after 150k.** Whole decay: 0.44-0.51 with copy
    error, 0.40-0.43 without. In-place loss with copy error: 0.076-0.133, rising late.
    Without copy error: 0.000-0.027. The fill of offset 30 alone: 0.030-0.055 with copy
    error, at most 0.005 without. Wick ends plus the net in-place loss, the counterpart of
    v18's balance shortfall: 0.12-0.36 with copy error (v18 estimated 0.06-0.28 in the same
    runs) and 0.000-0.028 without (v18: 0.01-0.04).
  - **Attribution.** A change is the set of non-volatile bytes of a site that differ after
    one tick. It is credited to the first foreign writer among them (lowest offset), or to
    the site itself when it wrote them all; the writer's class is the census status of its
    activation.
  - **Who changes a strict site in place (after 150k, with copy error).** The site itself
    44-47%, `other` sites 26-27%, strict sites 24-26%, `loose` and `prop` sites 2-3%. The
    status afterwards is `other` in 70-71% of losses, `prop` in 22-23% (93-94% of these
    self-written) and `loose` in 6-9%. Without copy error the site itself writes 62-64%.
  - **The fill of offset 30.** It is 42-45% of in-place losses and 6.2-6.4% of all strict
    losses after 150k with copy error (32-34% and 0.3-0.5% without). In all but 4 of 25,455
    cases, offset 30 is the only non-volatile change. `other` and strict sites write about
    half each (47-48% with copy error); after 150k only 26 and 27 changes of offset 30 were
    written by the site itself. The new direction names the writing neighbor in 21-26% of
    fills, about the chance 1/4. The closing jump `JMP 30` then lands at [30] mod 64: offset
    0 in 2-3%, another opcode offset of polite in 4-7%, elsewhere in 91-93%.
  - **What a fill leaves behind.** The converted program reads its source from the
    neighbor that [30] now names, but it seldom completes a copy: 0.14-0.29 copy births per
    conversion with copy error, 0.04-0.14 without. At most 0.1% of these children equal the
    parent's key; 33-50% equal the key of the named neighbor (55-67% without copy error),
    and 16-30% are strict (33-60% without). The converted activation stays active until
    whole decay in 71-81% of cases, on average 6,200-6,700 ticks after the conversion
    (8,500 over the 36 ends without copy error before 150k); up to 244 are alive at a
    checkpoint.
  - **Self-written losses.** After 150k they change offset 0 in 74-77% of cases with copy
    error (76-93% without). 85-89% come from activations ignited at an offset other than 0
    (99.4-99.8% without copy error), although such activations are only 22-23% of strict
    births (0.6-1.0% without). The instruction that ran is in polite's data region (offsets
    33-45) in 81-83% of cases with copy error and 98% without: 35 (RND with operand [36]),
    39 (RND [40]), 43 (RND [44]) and 33 (DEC [34]). Where the operand byte is inert it names
    offset 0, so the program overwrites its own first opcode (code inspection, consistent
    with the counts). Before 150k, a further 26% come from the instruction at 8 (`MOV 32
    40`), which writes a neighbor's byte to its own offset [41]. In the variants dumped,
    [41] pointed outside the masked offsets (to 61), so the key changes with every target
    check: a relabel by the census key rather than a change of behavior (inference from
    dumped cases).
  - **Other foreign writes.** Besides offset 30, foreign writes that end strict status
    change the own-site pointer bytes 36, 38 and 40 (at least 2,400-2,500 per run after
    150k). Tail offsets 47-53 account for at least 42 and 280 (at least 1,500 under the
    seed-limited census, whose tail losses were mostly keys pushed past 48; v22). Alone,
    polite with any one of offsets 34-40, 46-53 or 60 filled is still strict (all 255
    values; a scratch check, and `ps_test` checks value 192 at five of them), while any fill
    of 30 breaks it. So these losses involve evolved genotypes or several offsets at once.
    Strict writers (24-26% of in-place losses) were not examined further.
  - **Ends by status.** Over all windows, strict activations end by whole decay in 84% of
    ends with copy error and 99.8-99.9% without; `loose` in 80-82%. `prop` and `other`
    activations end by wick in 87% and 93% with copy error. The strict decay share falls
    late, to 66-79% at 450-500k, as wick ends rise.

- **v20** (inert operands fail under form M to 500k ticks; revision 857bf01, job list
  `v20_inert_operand.txt`; 4 jobs in 39 minutes on 4 cores; counts recomputed in v23; strict
  verdict from reset counters, see v27). The runs repeat v19 `m195_s1`, `m195_s2`,
  `nomut_s1` and `nomut_s2` with one change, `inert_operand=fail`; v19 is the baseline. At
  857bf01 the default `zero` reproduces v19 `m195_s1` line for line to 50k (census trial
  counts and the physics line included), and `ps_test` keeps its digest. At all 40 v20
  checkpoints the strict balance equals the strict count, and the census mismatch,
  untracked, stale and replaced counts are 0, under both census verdicts. Instructions that
  failed on an inert operand: 144k by 50k and 10.2-11.8 million by 500k with copy error;
  37-38k by 50k and 67-73k by 500k without.

  Choice of split. INERT has four roles: it embodies no monomer (an empty byte, which `fill`
  lets other sites write), it is the own-site direction of a pointer, it is the value 0 of
  data and counters, and as an operand byte it names offset 0. v19 tied the self-overwrite
  route to the last role and the fills of 30, 36, 38 and 40 to the first two together. Two
  splits were considered:
  - A separate empty code or a non-inert own-site direction. Polite's own-site direction
    bytes (30, 34, 36, 38, 40) would become non-inert, so each copy would take five more
    monomers, polite's whole-decay hazard would rise with 5 more of its 37 non-inert bytes,
    and the decoding of neighbor directions or of 0 as data would change. This changes the
    ledger and other rules, so it was not implemented.
  - Inert operands fail (chosen). Only the operand role changes: no mass, decay, direction,
    data or ancestor change. Polite executes no inert operand, so alone it runs bit for bit
    as before (`ps_test`). This targets the self-overwrite route only; the own-site direction
    role, and with it the fills of 30, 36, 38 and 40, stays.

  Strict sites (v19 / v20; topped-up census, v23 runs `zero_*` / `fail_*`):

  | tick | m195_s1 | m195_s2 | nomut_s1 | nomut_s2 |
  | --- | --- | --- | --- | --- |
  | 50k | 6522 / 6656 | 6385 / 6567 | 8677 / 8722 | 8673 / 8703 |
  | 100k | 5850 / 5846 | 6014 / 6018 | 8658 / 8679 | 8638 / 8692 |
  | 150k | 5433 / 5415 | 5515 / 5355 | 8619 / 8657 | 8606 / 8662 |
  | 200k | 4819 / 4219 | 4595 / 4306 | 8596 / 8681 | 8577 / 8629 |
  | 250k | 3953 / 3768 | 3903 / 3694 | 8497 / 8615 | 8542 / 8622 |
  | 300k | 3462 / 3527 | 3663 / 3309 | 8438 / 8598 | 8476 / 8625 |
  | 350k | 3329 / 3310 | 3653 / 3398 | 8421 / 8613 | 8359 / 8658 |
  | 400k | 3280 / 3124 | 3494 / 3207 | 8296 / 8577 | 8192 / 8632 |
  | 450k | 3365 / 3198 | 3235 / 3278 | 8244 / 8602 | 7998 / 8577 |
  | 500k | 2984 / 3075 | 3280 / 3092 | 8089 / 8589 | 7717 / 8604 |

  Strict activations after 150k (windows ending 200k-500k), v19 / v20. Self-written and
  foreign-written split the in-place losses by writer (attribution as in v19). Offsets 36,
  38, 40 and 47-53 count foreign-written losses that changed the offset, from the top 8
  offsets per window, so they are lower bounds:

  | run | net | copy births | re-ignitions | decay | wick | lost in place: self-written | foreign-written | self-written at offset 0 | neighbor fill of 30 | 36, 38, 40 | 47-53 | in place, net | births off offset 0 |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | m195_s1 | -2449 / -2340 | 109260 / 107829 | 66468 / 144141 | 125764 / 122749 | 32573 / 114169 | 12954 / 3984 | 14550 / 15713 | 9973 / 576 | 11513 / 11959 | 2461 / 3189 | 280 / 207 | -19840 / -17392 | 21.6% / 46.7% |
  | m195_s2 | -2235 / -2263 | 112186 / 110469 | 68375 / 131933 | 127958 / 124158 | 34779 / 100814 | 11743 / 8283 | 15071 / 15403 | 8670 / 22 | 12111 / 11903 | 2428 / 2950 | 42 / 40 | -20059 / -19693 | 22.9% / 44.2% |
  | nomut_s1 | -530 / -68 | 148541 / 153927 | 92476 / 87835 | 239529 / 241324 | 285 / 642 | 1228 / 0 | 746 / 88 | 930 / 0 | 628 / 72 | 112 / 15 | 0 / 0 | -1733 / +136 | 0.6% / 0.3% |
  | nomut_s2 | -889 / -58 | 149977 / 154391 | 93134 / 87932 | 240533 / 241951 | 687 / 611 | 2170 / 0 | 1223 / 50 | 2016 / 0 | 1149 / 38 | 63 / 11 | 0 / 0 | -2780 / +181 | 1.0% / 0.3% |

  The same flows per strict site per 5,000 ticks after 150k with copy error (s1 / s2):

  | | copy births | decay | re-ignitions minus wick ends | self-written loss | foreign-written loss | in place, net | net |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | v19 | 0.414 / 0.416 | 0.476 / 0.475 | +0.128 / +0.125 | 0.049 / 0.044 | 0.055 / 0.056 | -0.075 / -0.074 | -0.009 / -0.008 |
  | v20 | 0.425 / 0.435 | 0.483 / 0.489 | +0.118 / +0.122 | 0.016 / 0.033 | 0.062 / 0.061 | -0.068 / -0.077 | -0.009 / -0.009 |

  - **The self-overwrite of offset 0 is gone.** After 150k, self-written losses that change
    offset 0 fall from 9,973 and 8,670 to 576 and 22 with copy error, and from 930 and 2,016
    to 0 without. Without copy error no self-written loss remains. With copy error,
    self-written losses fall by 29-69% (25-68% per strict site). The rest come mostly from
    the instructions at 43 (20-23%), 33 (16-35%) and 45 (10%), and change offset 1 (1,181
    and 2,237) or offsets 4-6 (779 and 2,084). At 43, polite's data byte is `RND` with
    operand byte 44, which holds the byte the target check read from a neighbor's offset 0:
    non-inert when the neighbor is occupied, and 1 when it holds polite (code inspection).
  - **Without copy error, foreign fills fall too, and the decline is gone to 500k.**
    Foreign-written losses fall by 88-96%, the fill of 30 by 89-97%, and offsets 36, 38, 40
    by 83-87%, though the write rule is unchanged; no foreign loss changes 47-53 in either
    rule (the seed-limited census had counted 275 and 390 there, all relabels past 48). Both
    kinds of writer write less: strict sites 36 and 17 times (v19: 368 and 615), `other`
    sites 51 and 33 times (v19: 365 and 584). `other` sites stay at 2-21 (v19: 193 and 358
    at 500k). Strict sites stay at 8,577-8,722 from 50k to 500k, and the net change after
    150k is -68 and -58 (v19: -530 and -889). The net in-place change is positive. Strict
    sites with a filled own-site pointer offset reach 21-28% at 500k (v19: 93-96%), and
    99.4-100% of strict parents' children are strict (v19: 94.6-96.8% at 500k).
  - **With copy error, foreign fills barely change.** Foreign-written losses rise by 2-8%
    (8-12% per strict site). The fill of 30 changes by +4% and -2%, offsets 36, 38, 40 rise
    by 21-30%, and the tail falls by 5-26% on small counts. `other` sites are as many as in
    v19 (1,820 and 1,754 at 500k against 1,849 and 1,776).
  - **With copy error, the decline is not smaller.** In-place losses fall by 12-28% and the
    net in-place loss by 2-12%, but strict sites are lower than in v19 at most checkpoints
    from 150k (by up to 12% in s1 and 10% in s2; higher by 1-3% at three points), and the
    net change after 150k is about the same (-2,340 and -2,263 against -2,449 and -2,235).
    Per strict site, copy births, decay and the net in-place loss are within 10% of v19, and
    the net decline is 0.009 per site per 5,000 ticks in both seeds (v19: 0.009 and 0.008).
  - **Off-entry visits now end by wick.** With copy error, strict re-ignitions rise 1.9-2.2
    times and strict wick ends 2.9-3.5 times; 44-47% of strict births now start off offset 0
    (v19: 22-23%). Re-ignitions minus wick ends per strict site change little (+0.118 and
    +0.122 against +0.128 and +0.125).
  - **Mass runs short earlier with copy error.** Writes refused for lack of a free monomer
    in the window before 200k: 4,985 and 5,278 (v19: 1,649 and 2,412). The cause was not
    traced. (These counts do not depend on the census.)
  - **Copy fidelity in the run.** The strict share of strict parents' children is as in v19
    with copy error (59-86% against 57-84%, by point).
- **v21** (who writes the remaining in-place losses and who ignites strict code off entry;
  measurement only; revision 76ef87b, job list `v21_trace.txt`; 4 jobs in 43 minutes on 4
  cores, the last 7 shared with v22; counts recomputed in v23; strict verdict from reset
  counters, see v27). `trace=1` under v20
  settings: `m195_s1` and `m195_s2` (`inert_operand=fail`, copy error), `nomut_s1` (`fail`,
  no copy error), and `zero_s1`, which is v19 `m195_s1` (the default `zero`). Apart from the
  `# trace*` lines, each output equals its v20 or v19 counterpart line for line. Counts are
  summed over windows, to 150k and from 150k to 500k. Offsets, writer instructions and
  entries are kept per window only for the top 10-24, so their shares are lower bounds.
  Pairs are s1 / s2 under `fail`; `zero` is seed 1. Statuses are the topped-up census (v23
  runs `fail_m195_s1/s2`, `fail_nomut_s1` and `zero_m195_s1`).

  Foreign-written strict losses in place (shares in % of losses):

  | | `fail` to 150k | `fail` 150k-500k | `zero` to 150k | `zero` 150k-500k |
  | --- | --- | --- | --- | --- |
  | losses | 3,743 / 4,280 | 15,713 / 15,403 | 3,999 | 14,550 |
  | writer `other` / strict / `loose` or `prop` | 52-54 / 40-41 / 6 | 48-50 / 46-47 / 4-5 | 53 / 42 / 5 | 49 / 46 / 5 |
  | writer age under 1k / 1k-10k / from 10k ticks | 40-42 / 43-44 / 15-16 | 44 / 42 / 14 | 43 / 42 / 15 | 45 / 42 / 13 |
  | writer born by copy / by re-ignition | 58-60 / 40-42 | 67-68 / 32-33 | 58 / 42 | 67 / 33 |
  | writer ran offset 15 (polite's copy `MOV`) | 87.7-88.3 | 84.7-86.3 | 89.4 | 85.4 |
  | that MOV read the writer's own site | 74-75 | 70-72 | 76 | 71 |
  | filled an inert pointer direction of the victim | 93.9-94.5 | 96.5-96.6 | 94.4 | 96.3 |
  | filled offset 30 | 72.4-72.8 | 76.1-77.3 | 74.4 | 79.1 |
  | filled offsets 34, 36, 38, 40 | 21.0-22.1 | 19.3-20.4 | 20.0 | 17.2 |
  | changed tail offsets 46-63 (at least) | 5.0-5.6 | 2.5-2.6 | 4.6 | 2.7 |

  - In all but 11 of the 55,391 losses with a direction fill, the direction bytes were the
    only non-volatile change. The victim activation was ignited at offset 0 in 98.1-99.4% of
    losses, the writer in 94-97%. Two losses in 57,688 came from an instruction that was not
    a `MOV`.
  - Under the seed-limited census the same table counted 40,417 losses, about half of them
    tail fills (44.5-51.9%) and half direction fills (47.0-54.7%). Most of those tail fills
    pushed the key past 48 bytes and were relabels (v22); with the topped-up census direction
    fills are 94-97% of foreign losses, and the fill of 30 alone 72-79%.
  - Without copy error (`nomut_s1`), 41 and 88 losses: strict writers 68% then 41%,
    direction fills 100% then 99%.

  Strict births off offset 0 (re-ignitions in 99.3-100%; shares in % of these births):

  | | `fail` to 150k | `fail` 150k-500k | `zero` to 150k | `zero` 150k-500k | `nomut` to 150k | `nomut` 150k-500k |
  | --- | --- | --- | --- | --- | --- | --- |
  | births (% of strict births) | 39,660 / 36,446 (32-35) | 117,626 / 107,066 (44-47) | 5,924 (7.3) | 37,872 (21.6) | 568 (0.6) | 647 (0.3) |
  | igniter `other` | 93.4 / 87.4 | 96.1 / 96.8 | 95.3 | 98.3 | 100 | 99.8 |
  | igniter age from 1k ticks | 96 / 95 | 94 / 92 | 86 | 87 | 99 | 83 |
  | entry 33 / 31 / 32 | 54 / 26 / 7; 35 / 45 / 8 | 23 / 20 / 14; 31 / 19 / 11 | 22 / 15 / 8 | 14 / 14 / 17 | 0.2 / 99.5 / 0 | 74 / 0 / 0 |
  | igniter instruction at offset 1 / 4 | 19 / 12; 39 / 13 | 12 / 6; 9 / 10 | 8 / 12 | 9 / 7 | 99 / 0 | 0 / 2 |
  | the site last held a strict off-entry activation that ended by wick | 94.5 / 92.7 | 91.9 / 89.6 | 52.0 | 71.7 | 98.9 | 97.8 |
  | mean ticks since that end | 12 / 20 | 18 / 19 | 83 | 34 | 4 | 2 |
  | these activations end by wick | 99.6 / 99.5 | 98.8 / 98.7 | 97.2 | 96.5 | 99.6 | 99.4 |
  | their mean life (ticks) | 40 / 55 | 117 / 127 | 280 | 323 | 29 | 15 |
  | their copy births | 87 / 157 | 1,615 / 1,582 | 89 | 1,293 | 1 | 4 |

  - Strict activations ignited at offset 0 made 65-67k copy births to 150k and 163-165k
    from 150k in every run with copy error. The igniter carried the child's key in 0.0-0.2%.
  - The most frequent igniter instruction from 150k with copy error is at offset 6 (24-29%),
    then offsets 0, 1, 3, 4 and 8; without copy error, 6 and 38 from 150k. Entries 32 and 34
    follow 31 and 33 (under `zero` from 150k, 32 leads with 17%).
  - **Rule comparison** (0-500k, `fail` against `zero`; seed 2 `zero` from v23
    `zero_m195_s2`):

    | seed | strict re-ignitions | off entry | at offset 0 | strict wick ends | off entry |
    | --- | --- | --- | --- | --- | --- |
    | 1 | 205,129 / 93,330 (+111,799) | 156,983 / 43,501 (+113,482) | 48,146 / 49,829 | 152,958 / 36,690 (+116,268) | +117,302 |
    | 2 | 189,295 / 92,950 (+96,345) | 143,168 / 45,707 (+97,461) | 46,127 / 47,243 | 136,468 / 37,282 (+99,186) | +99,268 |

    Off-entry activations are 98.7-99.6% of strict wick ends under `fail` and 80-99% under
    `zero`, per period.

  Matter (`# tracemass`; 442,368 monomers in all, 48 per site) and writes refused for lack
  of a free monomer (`no_mass`, counted only in the 5,000 ticks before each checkpoint), in
  thousands except refusals:

  | tick | free | walls | active strict bytes | active `other` bytes | inactive bytes | refused writes |
  | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 65.7 / 61.8; 65.2 | 2.9 / 3.0; 3.3 | 278 / 277; 273 | 49 / 53; 55 | 40 / 42; 40 | 0 / 0; 0 |
  | 100k | 52.8 / 48.8; 56.3 | 4.8 / 5.2; 5.7 | 251 / 262; 251 | 76 / 69; 72 | 53 / 52; 54 | 0 / 0; 0 |
  | 150k | 34.0 / 30.9; 37.7 | 6.8 / 7.6; 7.4 | 246 / 245; 243 | 83 / 82; 81 | 68 / 72; 68 | 49 / 112; 5 |
  | 200k | 22.6 / 19.1; 24.4 | 10.2 / 10.2; 9.1 | 203 / 209; 227 | 103 / 100; 92 | 99 / 100; 86 | 4,985 / 5,278; 1,649 |

  - The cells are `fail` s1 / s2; `zero` s1.
  - At 150k an `other` site holds 52.7-52.8 non-inert bytes on average and a strict site
    44.8-45.8, in all three runs (seed-limited census: 54 and 42.5-42.8).
  - From 250k, refusals per window are 3,404-9,614 under `fail` and 1,707-10,266 under
    `zero` (v19 s1-s2).
  - Without copy error, free monomers stay at 71.6-76.5k and no write is refused.
- **v22** (the census seeding limit; measurement only; revision b56495b, job list
  `v22_seed_limit.txt`; 4 jobs in 49 minutes on 4 cores, the first 7 minutes shared with
  v21; tables recomputed in v23; strict verdict from reset counters, see v27). Found while
  tracing v21. The census trial drew the
  founder's bytes from the trial center's `mass0` (48) free monomers. A key with more than
  48 non-inert bytes after the volatile reset therefore could not be seeded, and the census
  called it a non-replicator (`other`) whatever it did in the run. Since b4b4ea1 the census
  tops up the founder site by default. Polite has 40 such bytes. With 8 tail bytes filled
  it is still strict; with 9 it is `other` without top-up, and strict once the founder site
  is topped up to its byte count (`ps_test`). Alone, polite stays strict with any single
  fill of 34, 36, 38, 40 or 46-63 and is a non-replicator with any fill of 30 (all 255
  values; scratch check with `mass0` 48 and `inert_operand=fail`). From copy-born counters
  a fill of 36 is not strict either (v28).

  The runs repeat v20 `m195_s1` and `m195_s2` (`fail`) and v19 `m195_s1` and `m195_s2`
  (`zero`) with `trace=1`. Apart from `# tracekey`, the outputs equal v21 and v19 `m195_s2`
  line for line. A topped-up trial is the census trial with the founder site given as many
  free monomers as the key has bytes; nothing else changes. Its children are still written
  from the target sites' own free monomers, as in the run.

  The tables below are recomputed with the topped-up census (v23 runs `fail_m195_s1/s2` and
  `zero_m195_s1/s2`, whose rows equal these runs). The seed-limited column reproduces the
  census strict counts first recorded here; the seed-limited tables are at c207f47.

  Active sites, `fail` s1 / s2; `zero` s1 / s2. "Past 48": more than 48 non-inert bytes
  after the volatile reset. Strict is the topped-up census; "seed-limited strict" leaves out
  the strict sites past 48, which the seed-limited census called `other`:

  | tick | strict | of which past 48 | seed-limited strict | `other` | `other` past 48 (%) | copy births by parents past 48 (% of the window) |
  | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 6,656 / 6,567; 6,522 / 6,385 | 255 / 379; 228 / 377 | 6,401 / 6,188; 6,294 / 6,008 | 1,033 / 1,074; 1,143 / 1,194 | 32 / 38; 32 / 37 | 2 / 6; 2 / 5 |
  | 100k | 5,846 / 6,018; 5,850 / 6,014 | 463 / 705; 481 / 577 | 5,383 / 5,313; 5,369 / 5,437 | 1,557 / 1,366; 1,450 / 1,349 | 39 / 45; 39 / 43 | 8 / 12; 8 / 12 |
  | 150k | 5,415 / 5,355; 5,433 / 5,515 | 1,239 / 1,280; 979 / 903 | 4,176 / 4,075; 4,454 / 4,612 | 1,573 / 1,548; 1,540 / 1,506 | 59 / 59; 58 / 58 | 18 / 22; 18 / 15 |
  | 200k | 4,219 / 4,306; 4,819 / 4,595 | 1,597 / 1,727; 1,455 / 1,320 | 2,622 / 2,579; 3,364 / 3,275 | 1,888 / 1,830; 1,681 / 1,827 | 70 / 70; 68 / 67 | 37 / 37; 34 / 26 |
  | 250k | 3,768 / 3,694; 3,953 / 3,903 | 1,945 / 1,976; 1,733 / 1,531 | 1,823 / 1,718; 2,220 / 2,372 | 1,869 / 1,787; 1,782 / 1,835 | 79 / 81; 74 / 74 | 55 / 56; 49 / 42 |
  | 300k | 3,527 / 3,309; 3,462 / 3,663 | 2,150 / 2,146; 1,927 / 1,760 | 1,377 / 1,163; 1,535 / 1,903 | 1,808 / 1,807; 1,913 / 1,865 | 84 / 85; 81 / 79 | 62 / 65; 58 / 53 |
  | 350k | 3,310 / 3,398; 3,329 / 3,653 | 2,267 / 2,460; 2,135 / 2,046 | 1,043 / 938; 1,194 / 1,607 | 1,805 / 1,722; 1,894 / 1,791 | 87 / 90; 85 / 82 | 73 / 75; 67 / 57 |
  | 400k | 3,124 / 3,207; 3,280 / 3,494 | 2,284 / 2,330; 2,288 / 2,191 | 840 / 877; 992 / 1,303 | 1,759 / 1,814; 1,755 / 1,759 | 90 / 89; 88 / 87 | 78 / 77; 74 / 65 |
  | 450k | 3,198 / 3,278; 3,365 / 3,235 | 2,535 / 2,436; 2,476 / 2,156 | 663 / 842; 889 / 1,079 | 1,751 / 1,702; 1,747 / 1,828 | 92 / 92; 88 / 87 | 82 / 79; 77 / 73 |
  | 500k | 3,075 / 3,092; 2,984 / 3,280 | 2,449 / 2,443; 2,314 / 2,304 | 626 / 649; 670 / 976 | 1,820 / 1,754; 1,849 / 1,776 | 94 / 93; 92 / 88 | 85 / 83; 81 / 76 |

  - Strict sites grow past the limit: at 50k, 75-83% hold 40 bytes or fewer and 3-6% are
    past 48; at 500k, 70-80% are past 48, and 79-84% of these hold 53-64 bytes.
  - The seed-limited verdict counted 626-976 strict sites at 500k against 2,984-3,280.
    Those it missed were 54-57% of its `other` sites at 500k.
  - The remaining `other` sites are long too: 88-94% are past 48 at 500k, and 91-93% of
    these hold 53-64 bytes. Alone and topped up, they do not replicate.

  In-place strict losses and copy births, summed over windows. Under the topped-up census no
  loss is a relabel across the seeding limit; copy births do not depend on the census:

  | | `fail` to 150k | `fail` 150k-500k | `zero` to 150k | `zero` 150k-500k |
  | --- | --- | --- | --- | --- |
  | foreign-written strict losses | 3,743 / 4,280 | 15,713 / 15,403 | 3,999 / 4,018 | 14,550 / 15,071 |
  | new key past 48 (%) | 38.1 / 40.2 | 80.1 / 81.2 | 35.1 / 34.4 | 78.1 / 75.3 |
  | self-written strict losses (new key past 48) | 3,691 (287) / 4,746 (2,604) | 3,984 (2,223) / 8,283 (4,428) | 4,373 (226) / 4,990 (733) | 12,954 (7,174) / 11,743 (5,047) |
  | copy births | 70,892 / 73,055 | 206,523 / 203,928 | 72,091 / 76,459 | 198,730 / 206,382 |
  | by parents past 48 (%) | 9.3 / 13.4 | 68.0 / 68.6 | 9.2 / 10.7 | 63.0 / 56.7 |
  | child carries the parent's key: all copies / parents past 48 (%) | 67.6 / 66.5; 42.0 / 45.3 | 41.3 / 42.9; 36.7 / 38.2 | 66.9 / 64.9; 37.5 / 42.6 | 43.6 / 43.4; 37.5 / 36.6 |

  - Under the seed-limited census, foreign-written losses were 4,628 / 5,026 and 8,566 /
    8,175 under `fail` and 4,975 / 4,881 and 9,047 / 10,309 under `zero`; 46-65% pushed the
    key past 48, and 92-97% of those were strict once topped up (relabels). The topped-up
    census removes those and adds the losses of strict sites already past 48, which the
    seed-limited census did not follow as strict.

- **v23** (v17-v22 recomputed with the topped-up census; measurement only; revision b4b4ea1,
  job list `v23_census_topup.txt`; 18 jobs in 2 hours 37 minutes on 4 cores). Since b4b4ea1
  the census trial tops up the founder site to the key's non-inert byte count (v22), so a
  key past 48 bytes is tested instead of being counted as `other`. Run dynamics are
  unchanged; every census-based line can change. One run per distinct dynamics of v17-v22
  carries every observer line those versions used; the job list maps runs to versions.
  - **Checks.** The data rows and `# physics` lines of all 18 runs equal those of the
    earlier runs (v22 `m195_s1/s2` and `zero_s1/s2`, the `nomut` runs of v19-v21, the
    table runs of v17 and v18, and v18 `anc_s1/s2`). With `census_topup=0`, `ps_probe` at
    b4b4ea1 gives the same output as c207f47 byte for byte (v20 `m195_s1` settings, checked
    to 50k).
  - **What was recomputed.** The v17-v22 tables and readings above, marked "recomputed in
    v23". `ps_scan` re-read the `# fidtop` lines of `zero_m195_s1/s2`, `t2_s1`, `t3_s1` and
    `anc_s1/s2`. The seed-limited tables are at c207f47. v13-v16 keep the seed-limited
    counts and were not recomputed; how many of their sites were past 48 was not measured.
  - **Effect.** In the `m195` runs the strict counts rise by 4-6% at 50k and 3.4-4.9-fold
    at 500k (v22). The short-ancestor control changes from 5k, where a site with the
    ancestor and residue can be past 48. Counts that do not use the census (births,
    re-ignitions, exact births, active sites, decays) are unchanged.
- **v24** (what share of the strict decline each loss route carries, under the topped-up
  census; measurement only; revision 6a6bdc0, job list `v24_loss_routes.txt`; 4 jobs in
  1 hour 15 minutes on 4 cores; strict verdict from reset counters, see v27). A container
  restart stopped a first attempt at 450k /
  400k. The rerun started from tick 0, and the first attempt's outputs equal the rerun's up
  to where they stopped. The research channel asked what share of the decline comes from
  three routes:
  - the fill of offset 30 by polite's copy `MOV` at 15, which ends replication in place;
  - ignitions off offset 0 by `other` sites through filled pointers 36 and 38;
  - monomer depletion.

  The runs repeat v23 `zero_m195_s1/s2` (`inert_operand=zero`) and `fail_m195_s1/s2`
  (`fail`) with `route=1`. Ranges cover all four runs; lists are `zero` s1 / s2 and `fail`
  s1 / s2.
  - **Checks.** Apart from the `# route*` lines, each output equals its v23 run line for
    line. In all 40 windows:
    - both entry ledgers close (the balance equals the count);
    - entry 0 plus entry off equals the census strict count.
  - **Method.** The ledger follows strict activations ignited at offset 0 (entry 0). These
    are the census strict count apart from 5-83 activations ignited elsewhere.
    - Inflow: strict children of copies by strict entry-0 parents, strict children of
      other parents, re-ignitions at 0, and gains in place.
    - Outflow: whole decay, wick ends, in-place losses by route, and copies whose child is
      not strict, by difference class.
    - Rates are per strict entry-0 site per 5,000 ticks (window count / mean count / 10).
      "Early" is the windows ending at 100k and 150k; "late" is those ending at 350k-500k.
    - Per window: copies − non-strict children + other parents' strict children +
      re-ignitions + gains − decay − wick − in-place losses = net change. The residual is
      below 2e-16.

    From early to late the mean entry-0 count falls from 5,600-6,270 to 3,060-3,610. Copies
    per strict site rise from 0.365-0.383 to 0.700-0.751: as density falls, each site makes
    more copies, and the count settles where copies match losses.

    The last column takes each term's change toward decline: a rise in a per-site loss, or
    a fall in a per-site inflow other than copies. It divides that change by their sum D
    (0.351 / 0.313 for `zero`, 0.379 / 0.349 for `fail`, per site per 5k ticks).

    If the copy rate depends only on density, the drop in the settled count is, to first
    order, proportional to D, and the column gives each route's share of the decline
    (inference from that balance). It is an accounting, not a counterfactual: removing one
    route would change the others.

  | term (per strict entry-0 site per 5k ticks) | early | late | share of D, % (`zero` s1 / s2; `fail` s1 / s2) |
  | --- | --- | --- | --- |
  | copies by strict parents (all) | 0.365-0.383 | 0.700-0.751 | |
  | strict copies by other parents | 0.003 | 0.011-0.014 | -2 / -2 / -3 / -3 |
  | strict re-ignitions at 0 | 0.127-0.137 | 0.086-0.096 | +11 / +11 / +12 / +14 |
  | gains in place | 0.011-0.027 | 0.005-0.013 | -1 / +3 / +4 / +6 |
  | whole decay | 0.415-0.421 | 0.495-0.510 | +24 / +25 / +24 / +25 |
  | wick ends | 0.001-0.002 | 0.002-0.009 | +2 / +0 / +0 / +0 |
  | in place: fill of 30 by the `MOV` at 15 | 0.016-0.018 | 0.044-0.047 | +7 / +9 / +8 / +8 |
  | in place: fill of 30, other instruction | 0.002 | 0.006-0.007 | +1 / +1 / +1 / +1 |
  | in place: foreign, pointers 34-40 only | 0.005-0.006 | 0.010-0.014 | +2 / +2 / +2 / +2 |
  | in place: foreign, tail 46-63 only | 0.001 | 0.001-0.002 | +0 / +0 / +0 / +0 |
  | in place: foreign, other | 0.000 | 0.000-0.001 | +0 / +0 / +0 / +0 |
  | in place: self, offset 0 | 0.000-0.005 | 0.000-0.001 | +0 / -1 / -0 / -0 |
  | in place: self, other | 0.009-0.025 | 0.002-0.010 | +0 / -2 / -4 / -6 |
  | non-strict children: `point` | 0.020-0.021 | 0.031-0.035 | +3 / +3 / +3 / +4 |
  | non-strict children: `gap` | 0.002 | 0.024-0.040 | +9 / +9 / +10 / +6 |
  | non-strict children: `multi` | 0.012-0.018 | 0.071-0.080 | +18 / +17 / +18 / +18 |
  | non-strict children: `env` | 0.038-0.041 | 0.119-0.128 | +24 / +26 / +23 / +23 |
  | net change | -0.011 to -0.007 | -0.004 to -0.002 | |

  - **Fill of offset 30.** In place it is 8.5-9.7% of D; the `MOV` at 15 alone is 7.3-8.6%.
    Late, it is 5.9-6.3% of entry-0 outflow. The `MOV` fills alone are 59-67% of entry-0
    in-place losses, and 84-88% of their victims held keys past 48 bytes.
    - The same fill reaches children under construction. Of the `env` non-strict children
      of entry-0 parents, late, 23-26% have offset 30 written by another site, and in
      0.8-1.3% it is the only foreign difference.
    - Who last wrote that 30, late: strict sites 52-54%, `other` 27-28%, no writer recorded
      10-13%.
    - The rise of these children is 5.7-6.8% of D. This is an upper bound for that part:
      v22 shows that a fill of 30 alone stops polite, but these children also carry other
      differences.
  - **Ignitions off offset 0.** From 350k, strict births off 0 are re-ignitions in
    99.2-99.7% and are ignited by `other` sites in 89-100% per window. The pointer the
    igniter's `IGNITE` read, pooled over 150k-500k:

    | pointer | share of births (%) |
    | --- | --- |
    | a filled 36 or 38 | 32-44 |
    | a filled 30, 34 or 40 | 8-14 |
    | polite's 32 | 17-24 |
    | another offset | 28-38 |
    | an inert operand (`zero` only) | 1 |

    To 100k, a filled 36 or 38 is 39-85%.

    These activations are a separate population of 5-83 sites at a time. In every window
    their births equal their ends plus in-place losses, give or take 25 (net -25 to +19).
    As in v21, they end by wick. They take nothing directly from the entry-0 count: the
    direct share is 0. Two indirect paths were checked:
    - *Their writes into entry-0 strict sites.* In v21 the writer was ignited at 0 in 94-97%
      of foreign-written losses, and foreign in-place losses here are 10.4-11.8% of D.
      Off-entry writers can therefore account for at most about 0.7% of D.
    - *The pool of inactive strict sites.* Under `zero` they overwrite their own offset 0
      in 396-2,484 sites per window, removing those keys; under `fail`, in 2-68.
      Re-ignitions at 0 per site fall by 0.039 / 0.036 under `zero` and 0.046 / 0.049
      under `fail`. The drop is not larger where keys are removed, so no effect through the
      pool is visible.

    `fail` has 3.1-3.6 times as many off-entry births over the run, and the slightly larger
    drop (1.6-3.8% of D per seed). The `fail` rule also changes other ignitions, so this
    does not isolate an effect of off-entry ignition.
  - **Depletion.** Copies with a write refused for lack of a free monomer and no foreign or
    residue difference (`gap`) are 6.3-10.2% of D and 2.9-4.7% of late outflow. This is a
    lower bound: a copy with a refusal and any foreign difference counts as `env`.

    Refused writes per 50k window are under 300 to 150k and 25,846-105,476 from 250k.
    Between 50k and 500k, 136-158 thousand monomers left the free pool and active strict
    sites. They went to:
    - inactive sites, 54-58%;
    - active `other` sites, 33-37%;
    - walls, 8-9%.

    Inactive sites rose from 1,330-1,407 to 3,255-3,415. Those whose key is already known as
    strict rose from 125-160 to 252-316.

    Matter (`# tracemass`, thousands; refused writes per 50k window from `# route`):

  | tick | free | walls | active strict bytes | active `other` bytes | inactive bytes | refused writes |
  | --- | --- | --- | --- | --- | --- | --- |
  | 50k | 65.2 / 61.0; 65.7 / 61.8 | 3.3 / 3.1; 2.9 / 3.0 | 272.6 / 269.2; 278.2 / 276.6 | 54.9 / 58.3; 49.4 / 52.6 | 40.0 / 43.8; 39.6 / 42.5 | 251 / 269; 266 / 274 |
  | 150k | 37.7 / 35.4; 34.0 / 30.9 | 7.4 / 7.7; 6.8 / 7.6 | 243.3 / 246.9; 246.2 / 245.4 | 81.2 / 79.1; 82.9 / 81.8 | 68.5 / 68.5; 68.1 / 71.9 | 10 / 26; 68 / 294 |
  | 250k | 22.7 / 24.1; 20.2 / 23.2 | 12.7 / 14.0; 12.4 / 13.0 | 193.9 / 189.4; 188.6 / 186.3 | 99.2 / 101.5; 105.4 / 101.3 | 108.8 / 107.5; 110.7 / 114.5 | 35,419 / 26,304; 65,448 / 54,694 |
  | 350k | 18.0 / 22.8; 20.0 / 18.8 | 15.3 / 15.3; 14.3 / 14.5 | 172.9 / 185.5; 173.7 / 180.0 | 108.9 / 102.2; 104.5 / 100.7 | 121.4 / 110.0; 124.8 / 122.3 | 45,431 / 25,846; 77,364 / 75,283 |
  | 500k | 28.0 / 20.9; 18.5 / 20.0 | 17.0 / 15.9; 15.6 / 16.0 | 161.0 / 173.5; 167.8 / 167.8 | 109.1 / 103.4; 108.3 / 104.3 | 121.0 / 122.8; 126.4 / 129.5 | 63,123 / 59,536; 82,032 / 105,476 |

  - **The other terms.**
    - Whole decay of strict activations rises from 0.415-0.421 to 0.495-0.510 per site per
      5k ticks, 24-25% of D. Under form M a site with n non-inert bytes decays with
      probability 1 − (1 − 1.95e-6)^n per tick. These rates fit a mean of about 43 bytes
      early and 51-52 late, consistent with v22's growth past 48. This is inference from
      the rule; key length per strict activation was not recorded.
    - `env` children without a foreign 30: 16-20% of D. `multi`: 17-18% (its source is not
      resolved). Point errors: 3-4%. The fall of re-ignitions at 0: 11-14% (not attributed).
  - **Answer to the three questions** (accounting from executed runs):
    - The fill of 30 by the `MOV` at 15, in place: 7.3-8.6% of D. All fills of 30 in place:
      8.5-9.7%. With children whose 30 another site wrote: at most 14-16%.
    - Off-entry ignitions through filled 36/38: no direct share. No indirect share is
      visible; writes by off-entry activations are at most about 0.7%.
    - Depletion: at least 6.3-10.2%, as refused writes in children.

    The largest single terms are whole decay of longer keys (24-25%) and foreign
    differences in children other than at 30 (16-20%).
  - **Limits.**
    - First-order accounting over two periods, not a counterfactual.
    - Two seeds per rule.
    - `gap` is a lower bound for depletion, and `env` an upper bound for foreign writes in
      children.
    - The source of `multi` and of the fall of re-ignitions at 0 is not resolved.
    - The upper bound on off-entry writers uses the v21 writer shares, not this ledger.
- **v25** (why strict keys grow longer; measurement only; revision 3227e87, job list
  `v25_length.txt`; 6 jobs, the four copy-error runs in 70 minutes on 4 cores; strict
  verdict from reset counters, see v27). The research channel asked four questions:
  - where the added bytes come from: foreign writes, children written past the program,
    point errors, or residue copied in;
  - which offsets they occupy, and whether they are executed;
  - whether long keys copy faster, more faithfully or survive better, enough to offset the
    M hazard;
  - or whether the growth is neutral drift or a by-product of the write rules.

  The runs repeat v24 (`zero` and `fail`, seeds 1-2) and v23 `zero_nomut_s1` /
  `fail_nomut_s1` (no copy error) with `length=1`. A first attempt at c3eae86, without
  `# lengthptr`, was stopped at 100k; its outputs equal the rerun's to that point apart from
  that line. Ranges cover the four copy-error runs; lists are `zero` s1 / s2 and `fail`
  s1 / s2.
  - **Checks.**
    - Apart from the `# length*` lines, the copy-error outputs equal v24 line for line, and
      the controls equal v23 `zero_nomut_s1` and `fail_nomut_s1`.
    - In every window `check_n` and `check_z` are 0 and no event found the set empty.
    - The credits sum to the change of the mean; the residual over a run is below 1e-7.
  - **Length.** z is the key's non-inert byte count after the volatile reset (polite: 40);
    an extra byte can only sit at 30, 34, 36, 38, 40 or 46-63. The site counts in v17 and
    v22 (41.6-42.4 rising to 52.7-54.7) also include filled volatile counters.

    Whole decay per strict entry-0 site in each z bin implies, under 1 − (1 − 1.95e-6)^n
    per tick, an n within or just above the bin's range: late, 46.4-47.1 at 45-48,
    55.0-55.7 at 53-56 and 58.6-58.9 at 57-60. The M hazard follows key length, as the rule
    says. Mean z of strict entry-0 activations, with their count:

    | tick | `zero` s1 | `zero` s2 | `fail` s1 | `fail` s2 | `zero` no copy error | `fail` no copy error |
    | --- | --- | --- | --- | --- | --- | --- |
    | 50k | 40.9 (6,517) | 41.3 (6,366) | 40.9 (6,643) | 41.2 (6,551) | 40.0 (8,677) | 40.0 (8,722) |
    | 100k | 42.0 (5,832) | 42.3 (6,001) | 42.0 (5,823) | 42.6 (5,996) | 40.1 (8,657) | 40.0 (8,679) |
    | 150k | 44.0 (5,405) | 44.0 (5,485) | 44.6 (5,378) | 45.0 (5,324) | 40.2 (8,619) | 40.0 (8,657) |
    | 200k | 46.3 (4,782) | 46.1 (4,558) | 47.4 (4,184) | 47.7 (4,263) | 40.3 (8,593) | 40.0 (8,681) |
    | 250k | 48.4 (3,898) | 47.9 (3,876) | 49.4 (3,722) | 49.7 (3,643) | 40.5 (8,496) | 40.1 (8,615) |
    | 300k | 50.1 (3,419) | 49.0 (3,619) | 50.8 (3,470) | 51.5 (3,249) | 40.7 (8,436) | 40.1 (8,598) |
    | 350k | 51.4 (3,284) | 50.1 (3,603) | 51.9 (3,236) | 52.4 (3,331) | 41.0 (8,418) | 40.2 (8,613) |
    | 400k | 52.4 (3,238) | 50.9 (3,437) | 52.6 (3,049) | 52.6 (3,124) | 41.4 (8,293) | 40.3 (8,577) |
    | 450k | 52.9 (3,322) | 51.8 (3,182) | 53.6 (3,122) | 53.0 (3,220) | 41.9 (8,240) | 40.5 (8,602) |
    | 500k | 53.4 (2,926) | 52.3 (3,229) | 54.0 (3,001) | 53.7 (3,020) | 42.5 (8,078) | 40.7 (8,587) |

    At 500k a strict site holds 0.83-1.05 filled pointer directions (34, 36, 38, 40) and
    11.4-13.0 filled tail bytes (46-63); 40 plus these equals the mean z.
  - **Ledger of the mean, 0 to 500k.** Each credit is the exact change of the running mean
    caused by one kind of event (see `# length`). Credits for entries and exits are not
    effects in themselves: an entry raises the mean when its key is longer than the mean
    at that moment.

    | credit | `zero` s1 | `zero` s2 | `fail` s1 | `fail` s2 | `zero` no copy error | `fail` no copy error |
    | --- | --- | --- | --- | --- | --- | --- |
    | bytes added in place by foreign writes, strict status kept | +36.30 | +38.19 | +35.27 | +34.74 | +1.39 | +0.15 |
    | bytes changed in place by own writes, strict status kept | +0.02 | +0.01 | +0.01 | +0.02 | +0.00 | +0.00 |
    | copies by strict entry-0 parents: transmission, z_child − z_parent | +7.08 | +7.42 | +7.25 | +8.28 | +0.53 | +0.15 |
    | copies by strict entry-0 parents: the parent's z against the mean | +1.05 | −0.39 | +3.41 | +0.90 | −0.21 | −0.10 |
    | re-ignitions at 0 | +13.88 | +13.19 | +13.88 | +13.97 | +3.16 | +0.74 |
    | strict copies by other parents | +1.17 | +1.18 | +1.20 | +1.47 | +0.02 | +0.00 |
    | strict status gained in place, and found at the census | +1.13 | +1.45 | +2.25 | +7.98 | +0.02 | +0.00 |
    | whole decay | −28.27 | −28.78 | −30.11 | −28.97 | −1.87 | −0.21 |
    | strict status lost in place, foreign writer | −17.94 | −19.21 | −17.94 | −17.55 | −0.50 | −0.04 |
    | strict status lost in place, own write | −0.03 | −0.26 | −1.11 | −6.77 | −0.00 | +0.00 |
    | wick ends | −1.00 | −0.46 | −0.14 | −0.36 | −0.01 | +0.00 |
    | sum: change of the mean since tick 0 | +13.37 | +12.33 | +13.98 | +13.71 | +2.53 | +0.69 |

    Mean z by event, pooled over the run:
    - copying parents: 46.6-47.9, with children 0.19-0.21 bytes longer than their parents;
    - re-ignited keys: 46.9-47.8;
    - whole decays: 47.1-48.3;
    - foreign losses of strict status in place: 51.7-52.7.

    In `fail_s2`, gains of strict status in place and own-write losses (+8.0 and −6.8) are
    larger than in the other runs, with mean z 52.5 and 52.3; they nearly cancel.
  - **Where the bytes come from** (bytes over the run):

    | source | `zero` s1 | `zero` s2 | `fail` s1 | `fail` s2 | `zero` no copy error | `fail` no copy error |
    | --- | --- | --- | --- | --- | --- | --- |
    | in place: foreign `MOV` at 15, shifted | 97,451 | 104,014 | 90,657 | 88,407 | 8,191 | 971 |
    | in place: foreign `MOV` at 15, aligned | 40,294 | 39,641 | 42,564 | 41,829 | 1,651 | 250 |
    | in place: foreign `MOV` at 15, source in a neighbor | 17,144 | 19,374 | 15,665 | 17,315 | 1,341 | 68 |
    | in place: other foreign instruction | 11,739 | 12,408 | 10,370 | 10,257 | 1,101 | 150 |
    | in place: own write | 2,637 | 2,485 | 1,394 | 2,721 | 0 | 0 |
    | in place: erased by own write | 113 | 75 | 84 | 84 | 0 | 0 |
    | in place: erased by foreign write | 0 | 0 | 0 | 0 | 0 | 0 |
    | copy: added, foreign write | 32,547 | 34,860 | 31,212 | 35,509 | 4,837 | 1,098 |
    | copy: added, residue | 2,499 | 2,284 | 3,070 | 2,547 | 166 | 24 |
    | copy: added, parent write | 1,928 | 1,799 | 2,193 | 1,982 | 742 | 669 |
    | copy: lost, not written | 3,437 | 3,422 | 3,562 | 3,032 | 14 | 14 |
    | copy: lost, parent write | 1,111 | 1,167 | 1,153 | 1,276 | 98 | 0 |
    | copy: lost, foreign write | 2,441 | 2,453 | 2,337 | 2,246 | 1,346 | 646 |
    | copy: substituted (z unchanged) | 41,134 | 40,989 | 41,226 | 45,519 | 1,555 | 163 |

    - In-place additions are 80-82% of all bytes added to strict entry-0 keys. They come at
      0.40-0.42 bytes per strict site per 5k ticks: 0.25-0.31 in the windows to 100k and
      0.49-0.57 at 250-300k.
    - The in-place additions split by the writer's `MOV` at 15 (shares of in-place adds):
      - shifted source: 55-59%;
      - aligned: 22-27%;
      - source in a neighbor: 10-11%.

      Other foreign instructions add 6-7% and own writes 1-2%. Writers are census-strict
      in 57-60% and `other` in 36-38%.
    - Nothing foreign removes a byte (the `fill` rule), and own writes remove 75-113 per
      run.
    - Point errors substitute 41-46 thousand bytes in children without changing z
      (inspection: a copy error replaces a non-inert byte with a non-inert one). Residue
      adds 2.3-3.1 thousand. Parent writes where the parent's key is INERT (a shifted
      copy, or a parent key changed since) add 1.8-2.2 thousand. Foreign writes into
      children under construction add 31-36 thousand, against 6.4-7.4 thousand lost to
      gaps, parent writes and foreign writes.
  - **Where they sit and whether they run.**
    - In-place additions fall on the tail 46-63 (68-69%), on 36, 38 and 40 (18-19%), on
      30 (8-9%, which ends strict status) and on 34 (3-4%).
    - The standing share of strict sites with 34 filled rises from 6-10% at 50k to 72-92%
      at 500k. Over the run, only 7.4-8.3 thousand fills of 34 reach strict sites in place
      or in their children, against 112-142 thousand exits with 34 filled. The fill spreads
      mostly by inheritance. Why filled-34 lineages spread is not resolved: per site they
      copy no better (below).

    | tick | strict sites with 34 filled (%) | 36 (%) | 38 (%) | 40 (%) | filled tail bytes per site |
    | --- | --- | --- | --- | --- | --- |
    | 100k | 18.8-31.7 | 2.5-3.7 | 1.5-2.0 | 1.6-2.1 | 1.7-2.4 |
    | 150k | 41.5-55.1 | 3.1-5.0 | 1.9-3.0 | 2.2-2.9 | 3.3-4.5 |
    | 200k | 59.2-74.6 | 4.5-5.8 | 2.6-3.3 | 2.8-3.7 | 5.2-7.0 |
    | 250k | 69.2-83.2 | 5.0-6.2 | 3.0-4.1 | 3.1-4.4 | 6.9-9.0 |
    | 300k | 73.6-87.4 | 4.9-7.5 | 3.1-3.8 | 3.5-4.2 | 8.1-10.6 |
    | 350k | 74.8-89.8 | 5.0-7.0 | 2.4-3.8 | 2.8-3.8 | 9.2-11.5 |
    | 400k | 74.9-92.0 | 5.1-6.8 | 2.4-3.7 | 3.2-3.9 | 10.0-11.8 |
    | 450k | 70.8-92.4 | 4.6-6.4 | 2.5-3.7 | 2.6-4.2 | 10.8-12.6 |
    | 500k | 72.5-91.3 | 4.4-6.3 | 2.8-3.6 | 3.0-3.5 | 11.4-13.0 |

    - At exits, a filled 34 had been read as a pointer direction during the activation in
      99.0-99.7% of cases, and a filled 36, 38 or 40 in 94.7-97.3%. A filled tail byte had
      been executed in 0.3-0.7% and read as control in 0.1-0.3%. The tail bytes are
      carried and copied but almost never run.
  - **Who writes them.** `# lengthptr` splits parents and writers by polite's counter
    pointers. Off register means the copy loop's source and destination counters differ
    mod 64, so the copy is shifted. Whole run:

    | so/do pointer state | copies by such strict entry-0 parents (% of all) | strict children (%) | share of all `multi` children (%) | share of `MOV`-at-15 additions in place (%) |
    | --- | --- | --- | --- | --- |
    | none, in register | 88.2-88.9 | 76-79 | 11-13 | 20-25 |
    | none, off register | 7.2-7.3 | 2 | 60-63 | 45-46 |
    | 36 filled, in | 0.6-0.9 | 70-75 | 0 | 1 |
    | 36 filled, off | 2.0-2.5 | 0 | 17-21 | 8-10 |
    | 38 filled, in | 0.3-0.4 | 71-76 | 0 | 1 |
    | 38 filled, off | 0.4-0.5 | 0-1 | 3-4 | 6-7 |
    | both filled, in | 0.1 | 63-66 | 0 | 3-4 |
    | both filled, off | 0.4-0.5 | 0-1 | 3-4 | 10-11 |

    Off-register parents of every pointer state make 10.1-10.5% of copies by strict entry-0
    parents. Their children are almost never strict; they are 87-88% of all `multi`
    children, which resolves v24's unattributed `multi` term. They make 70-74% of the
    in-place additions through the `MOV` at 15. Their share of copies rises from 2.6-3.6%
    at 50k to 13.5-15.4% at 500k.

    The most frequent shifts of in-place additions are 31 (15-18%), 62 (15-17%) and 63
    (7-8%). Code inspection: polite resets so ([31]) and do ([33]) to K = 192 each cycle.
    A copy-born child starts with the values its parent's loop copied, so = 31 and
    do = 33 mod 64. Leaving one of them unreset gives a shift of 31, and leaving both
    gives 62 (−2).

    Scratch checks (not tracked, mutation and decay off, 9x9 worlds) show three ways a
    census-strict key copies off register:
    - *Filled 36.* All 255 values of a filled 36 pass the census, which starts from reset
      counters. Started from copy-born counters, none is strict (one seed: 5 copies, none
      exact). Single substitutions at offsets 0-2 (the so reset) and 5 give another 120
      such keys (28, 8, 76 and 8). Offsets 3, 4, 34, 35, 38 and 42 give none, under either
      `inert_operand`.
    - *A copy error in a counter reset.* A `MOV` copy error can hit the reset of so or do
      (copy errors apply to every `MOV`). If do then starts off K, the probe reads the
      target at that offset. A live polite is INERT at 23 of its 64 offsets, so the probe
      can report it empty. Polite with do starting at offsets 30, 44 or 58 then wrote 22,
      18 or 6 bytes into a live polite neighbor whenever `RND` chose it (50 of 200 seeds
      each). Starting at offsets 4 or 18 (non-inert there), or at 0, it wrote nothing.
      Filling 30 this way ends the neighbor's replication.
    - *A walled read of K through a filled 34.* The pointer at 34 then reads K from a
      neighbor across an edge. Each read crosses a wall with probability 1/(W + 1), so
      MOV 0 and MOV 3 can fail separately. Copy-born polite with 34 filled made an exact
      first copy in 100 of 100 seeds without a wall. With one wall unit on that edge it
      made an exact first copy in 41 of 96, and 51 were `multi`.

    Wall units in the runs grow from about 3 thousand at 50k to 15.6-17.0 thousand at 500k
    (v24 matter table). This route fits the rise of off-register copies with the spread of
    filled 34, but its share in the runs was not measured.
  - **Do long keys gain anything?** Rates per strict entry-0 site per 5k ticks, by current
    z:

    | z | share of exposure (%) | copies | strict children (%) | children with the parent's key (%) | whole decay | n implied by decay | foreign losses in place | strict children − exits |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | ≤40 | 0.9-2.4 | 0.585-0.704 | 68-71 | 56-60 | 0.396-0.432 | 40.6-44.3 | 0.012-0.025 | −0.162 to +0.052 |
    | 41-44 | 9.7-18.4 | 0.626-0.683 | 67-69 | 56-59 | 0.412-0.426 | 42.3-43.7 | 0.024-0.040 | −0.027 to +0.005 |
    | 45-48 | 14.1-19.7 | 0.678-0.690 | 66-69 | 54-57 | 0.453-0.459 | 46.4-47.1 | 0.037-0.041 | −0.050 to −0.029 |
    | 49-52 | 15.9-17.1 | 0.715-0.768 | 62-68 | 50-56 | 0.498-0.511 | 51.1-52.4 | 0.049-0.054 | −0.123 to −0.082 |
    | 53-56 | 18.8-20.5 | 0.750-0.803 | 61-63 | 47-49 | 0.536-0.543 | 55.0-55.7 | 0.059-0.061 | −0.158 to −0.103 |
    | 57-60 | 22.0-35.7 | 0.801-0.840 | 60-63 | 46-49 | 0.571-0.575 | 58.6-58.9 | 0.081-0.090 | −0.182 to −0.154 |
    | 61-64 | 1.2-1.5 | 0.119-0.224 | 16-18 | 7-12 | 0.567-0.622 | 58.2-63.8 | 0.606-0.798 | −1.400 to −1.168 |

    Late, longer keys make more copies per site (0.59-0.70 up to 40 bytes, 0.80-0.84 at
    57-60). Fewer of those copies are strict (68-71% against 60-63%) or exact (56-60%
    against 46-49%). Whole decay rises from 0.40-0.43 to 0.57 and foreign losses in place
    from 0.01-0.03 to 0.08-0.09.

    Strict children minus exits falls with length: from −0.03 to +0.01 at 41-44 bytes to
    −0.18 to −0.15 at 57-60. The bin up to 40 bytes holds 0.9-2.4% of exposure late.
    Within pointer classes 0 and 1 (`# lengthcomp`), keys with 13-18 filled tail bytes have
    a lower balance than those with 1-6 in every run. The faster copying of long keys is an
    association; its cause was not measured. It does not make up for their losses.

    Early (50k-150k) copy rates overlap: 0.43-0.45 up to 40 bytes, 0.41-0.51 at 57-60.
  - **Without copy error** (`zero_nomut_s1` / `fail_nomut_s1`):
    - Mean z rises from 40.0 to 42.5 / 40.7 at 500k (table above), against 52.3-54.0 with
      copy error.
    - In-place additions arrive at 0.015 / 0.0017 bytes per strict site per 5k ticks, 27 and
      240 times fewer than with copy error. Off-register parents make 0.0-0.2% of copies.
    - Most of the rise in `zero_nomut_s1` is a filled 34: 93% of strict sites at 500k hold
      it, with 1.58 filled tail bytes per site. In `fail_nomut_s1` 34 is filled in 28%, with
      0.41 tail bytes. Filled 34 therefore spreads without copy error too, while per-site
      rates do not favor it. Late, keys up to 40 bytes (which cannot hold a filled 34) make
      0.255-0.256 copies and 0.397-0.398 whole decays per site per 5k ticks, against
      0.256-0.260 and 0.410-0.413 at 41-44 bytes; all their copies by strict entry-0
      parents are strict in 98-100%.
  - **Literature** (sources; pages are printed pages unless noted; cached PDFs in
    `docs/references/`):
    - Tierra, Ray 1991:
      - mutations "cannot result in a change in the size of a creature" (p. 383);
      - the slicer gives CPU time in proportion to genome size raised to a power, size
        neutral at 1 (p. 378);
      - in size-neutral long runs communities moved from sizes in the 80s to 400-800
        (p. 387);
      - where the mutation rate was not lowered, mean size grew by an order of magnitude
        and two communities died, genomes having "melted" (p. 390).
    - Standish 2004 (arXiv preprint), Tierra with SlicePow = 1 (no parsimony): length
      rapidly increases with "junk" until the soup dies; SlicePow < 0.9 gave shorter
      genomes (p. 1).
    - Avida, Ofria and Wilke 2004:
      - insertions and deletions at division (pp. 200, 207);
      - an offspring size-range check, default 2.0, against out-of-control size change
        (p. 206);
      - optional death after a number of executed instructions, constant or proportional
        to genome length (p. 204).
    - Gupta et al. 2016 (Avida, equal insertion and deletion rates):
      - 19,262 insertions against 16,998 deletions on the lines of descent; insertions
        mostly beneficial, deletions mostly deleterious (p. 5, figure legend);
      - insertions preceded 87% of innovations (p. 4);
      - higher mutation rates gave smaller genomes through mutational load (p. 2).
    - Nordin and Banzhaf 1995 (linear GP): introns shield effective code from destructive
      crossover, and absolute length grows while effective length stays small; parsimony
      removes introns (PDF p. 7).
    - Dignum and Poli 2007 (tree GP): under size-neutral crossover "mean program size
      evolves as if selection only was acting" (p. 1591).
    - Batut et al. 2013 (aevol): relaxed selection shrank genomes by about 35% and removed
      about 55% of noncoding sequence (p. 1).

    Comparison (inference from these sources and the runs above):
    - Point errors here cannot change length, as in Tierra. Unlike Tierra and Avida,
      where a creature's own allocation and division set its size, a key here lengthens
      when other sites write into it.
    - The change operator is not size neutral. Under `fill`, foreign writes only add, and
      only a site's own writes or whole decay remove. The Dignum-Poli condition does not
      hold. Gupta et al.'s excess of insertions came from selection under symmetric
      operators; here the excess is in the operator.
    - M is a parsimony pressure, like SlicePow < 1 or length-proportional death. Standish
      and Ray report runaway length without one; here it is present and slows the growth
      without stopping it.
    - No intron-like protection is seen: long keys lose strict status in place more often,
      not less. The tail bytes are non-coding, as in Standish's "junk" and Nordin and
      Banzhaf's introns, but they arrive by foreign writes rather than by selection for
      robustness.
  - **Answer** (executed runs, with code inspection and scratch checks where stated):
    - The bytes come mostly from neighbors' copy loops writing into live strict sites
      (80-82% of added bytes, in place), and from foreign writes into children under
      construction (the rest, apart from about 2% residue and parent writes). Point errors
      add none.
    - They sit on the tail 46-63 and on pointer directions. Tail bytes are not executed.
      Filled directions are read and redirect the pointer.
    - Long keys make more copies per site late, but a smaller share of those copies is
      strict or exact. They decay and are overwritten more, and their per-site balance is
      lower. No offsetting advantage was found.
    - The growth is not drift: it is a directional flux of additions that exits only partly
      remove. It is a by-product of the write rules. A copy loop off register, through a
      copy error in a counter reset, a filled 36, or a failed read of K, probes and writes
      into occupied sites, and `fill` lets such writes add but never remove. Without copy
      error the flux nearly vanishes (0.015 / 0.0017 against 0.40-0.42 added bytes per
      strict site per 5k ticks).
  - **Limits.**
    - Two seeds per rule and one seed per control.
    - The ledger is an accounting of the running mean, not a counterfactual.
    - Re-ignited keys are longer than the mean, but where inactive keys lengthen is not
      followed.
    - The shares of the three off-register routes in the runs are not measured; the scratch
      checks show each can occur.
    - The rise of filled 34 is not explained.
- **v26** (`ext_write=erase` against `fill`: does the one-way write rule drive length
  growth? Revision 34839f4, job list `v26_erase.txt`; 4 jobs in one queue with v27's 12 on
  4 cores, 1 hour 42 minutes to 2 hours 25 minutes per run). The research channel asked for
  this control and for its effects on write cost and in-place losses, reported separately.
  - **Setup.** The runs repeat v25's copy-error runs (`zero` and `fail`, seeds 1-2) with
    one rule changed: a neighbor's write may also erase a byte to INERT. Substitution of a
    non-inert byte stays refused. The `fill` runs compared are v27 `zero_m195_s1/s2` and
    `fail_m195_s1/s2`, whose dynamics equal v25's and whose census is the same copy-born
    verdict (v27). Cells are `erase` / `fill`; ranges cover four runs per rule.
  - **Price** (code inspection, `World::write_cost`, `World::pay_energy`,
    `World::apply_writes`). A write that changes a non-inert byte plans a barrier on top of
    `e_op`: `e_bond` (1), or `e_erase` (1) for a foreign erasure under `erase`. The price is
    paid before writes are applied, and a refused write keeps it paid. So the price of each
    write is the same under both rules. Under `fill`, a foreign erasure pays and is
    refused; under `erase` it pays and takes effect, and the freed monomer goes to the
    target site's pool.
  - **Checks.** The ledger of the mean closes in every run (residual below 5e-8 over the
    run). The `fill` runs' checks are under v27.
  - **Length.** Mean z of strict entry-0 activations, with their count:

    | tick | `zero` s1 | `zero` s2 | `fail` s1 | `fail` s2 |
    | --- | --- | --- | --- | --- |
    | 50k | 40.4 (5,760) / 40.6 (6,265) | 40.3 (5,548) / 41.0 (6,166) | 40.5 (4,620) / 40.6 (6,442) | 40.7 (4,448) / 41.0 (6,344) |
    | 100k | 40.8 (4,207) / 41.8 (5,604) | 40.6 (5,060) / 42.0 (5,750) | 41.5 (2,497) / 41.8 (5,626) | 41.2 (3,384) / 42.4 (5,824) |
    | 150k | 41.0 (4,508) / 43.7 (5,152) | 40.9 (4,937) / 43.6 (5,180) | 42.1 (2,668) / 44.4 (5,194) | 41.4 (3,852) / 44.8 (5,114) |
    | 200k | 41.3 (4,772) / 46.0 (4,522) | 41.1 (4,532) / 45.7 (4,263) | 42.3 (3,039) / 47.0 (3,960) | 41.4 (3,742) / 47.4 (4,036) |
    | 250k | 41.5 (4,445) / 48.1 (3,649) | 41.2 (4,378) / 47.5 (3,597) | 42.2 (3,233) / 49.1 (3,497) | 41.6 (3,951) / 49.4 (3,421) |
    | 300k | 41.7 (4,318) / 49.6 (3,114) | 41.4 (4,405) / 48.7 (3,362) | 42.3 (3,674) / 50.4 (3,254) | 41.8 (4,505) / 51.2 (3,064) |
    | 350k | 41.9 (4,232) / 51.0 (3,013) | 41.3 (4,427) / 49.9 (3,346) | 42.2 (3,990) / 51.6 (3,008) | 41.7 (4,243) / 52.1 (3,140) |
    | 400k | 42.0 (4,036) / 52.1 (2,986) | 41.5 (4,527) / 50.7 (3,190) | 42.0 (4,236) / 52.4 (2,869) | 41.9 (4,168) / 52.4 (2,938) |
    | 450k | 42.1 (4,052) / 52.6 (3,069) | 41.5 (4,584) / 51.5 (2,952) | 42.3 (4,165) / 53.3 (2,940) | 42.0 (3,911) / 52.8 (3,056) |
    | 500k | 42.2 (4,315) / 53.1 (2,723) | 41.6 (4,350) / 52.0 (3,006) | 42.5 (4,050) / 53.8 (2,822) | 42.1 (4,094) / 53.5 (2,866) |

    - By 500k the mean rises 1.6-2.5 bytes under `erase` against 12.0-13.8 under `fill`.
      Strict sites hold a filled 34 in 21-54% against 71-91%, and 1.3-2.4 filled tail bytes
      against 11.2-12.9.
    - Ledger of the mean, 0 to 500k (as in v25): bytes added in place by foreign writes,
      strict status kept, +9.8 to +15.6 against +18.6 to +19.1; transmission +0.12 to
      +0.21 against +6.0 to +7.4; re-ignitions +0.7 to +2.7 against +14.9 to +16.0; whole
      decay −3.7 to −10.3 against −26.4 to −28.7. Foreign losses in place (−10.4 to −39.9)
      and gains in place (+2.7 to +22.1) are larger under `erase`.
    - In place, per strict entry-0 site per 5k ticks over the run: foreign writes add
      0.44-0.79 bytes and erase 0.33-0.66, against 0.24-0.25 added and none erased. The net
      change of keys that stay strict is +0.10 to +0.14 bytes against +0.18 to +0.19.
    - In copies by strict entry-0 parents, the child is 0.003-0.005 bytes longer than its
      parent, against 0.153-0.177; bytes written into the child by other sites, where the
      parent is INERT, fall from 0.172-0.191 to 0.008-0.010 per copy. Code inspection:
      polite's loop also copies its INERT bytes. Under `fill`, that write is refused where
      a neighbor has already filled the byte in the child, so the neighbor's byte stays;
      under `erase` the parent's copy erases it.
    - Off-register parents make 4.1-5.4% of copies by strict entry-0 parents (4.5-5.2% in
      the last window), against 7.4-7.5% (10.7-11.6%).
  - **Write cost** (separately).
    - Foreign writes refused after paying, per 5k window from 350k: 249-273 thousand
      against 699-720 thousand. Foreign erasures applied: 66-73 thousand per 5k. Writes
      that paid the barrier from outside (refused or erased) are thus 314-344 thousand per
      5k against 699-720 thousand. To 500k, 23.4-27.5 million refused and 6.1-7.3 million
      erasures, against 60.2-61.5 million refused.
    - Activations that could not pay their instruction price (stalls), per 50k from 350k:
      4.4-5.0 million against 9.3-9.8 million. Stored site energy is 1.5-2.0% higher
      (578-580 thousand against 569 thousand).
    - Erasure returns matter: at 500k, 78-85 thousand free monomers against 18-28 thousand,
      and 350-357 thousand code bytes against 397-408 thousand. After the first window no
      write is refused for lack of a free monomer, against 25.8-105.5 thousand per 50k
      window from 250k under `fill` (v24 table).
  - **In-place losses** (separately; per strict entry-0 site per 5k ticks, early =
    windows to 100k and 150k, late = 350k-500k, as v24).

    | term | early | late |
    | --- | --- | --- |
    | lost in place, foreign writer | 0.107-0.390 / 0.033-0.036 | 0.123-0.170 / 0.082-0.089 |
    | of which: pointers 34-40 only | 0.041-0.169 / 0.019-0.021 | 0.053-0.080 / 0.050-0.054 |
    | of which: fill of 30 by the `MOV` at 15 | 0.012-0.027 / 0.012-0.014 | 0.009-0.012 / 0.025-0.028 |
    | of which: other offsets (none under `fill`) | 0.052-0.218 / 0.000 | 0.052-0.096 / 0.000 |
    | lost in place, own write | 0.003-0.012 / 0.009-0.015 | 0.002-0.022 / 0.001-0.010 |
    | gained in place | 0.026-0.156 / 0.009-0.016 | 0.029-0.053 / 0.002-0.011 |
    | net in-place loss | 0.084-0.295 / 0.032-0.035 | 0.089-0.141 / 0.081-0.087 |

    - Foreign losses in place are 1.5-1.9 times as frequent late and 3-12 times early. The
      new route is the erasure of key bytes; erasures at pointer directions add to the
      fills. Late fills of 30 fall to a third to a half.
    - Gains in place are also more frequent. That an erasure removes an earlier fill of 30
      or of a pointer is a likely route (inference; not traced).
    - Net, late in-place losses are 1.1-1.6 times those under `fill`; early, 2.4-9.2
      times. In the `fail` runs the strict count falls to 2,497 and 3,384 at 100k before
      it recovers.
    - Keys lost in place by a foreign writer average 41.9-43.2 bytes, against 49.2-50.6.
  - **Population.** Late (350k-500k), `erase` holds 4,122-4,490 strict sites (census)
    against 2,972-3,170, and 5,500-5,838 active sites against 5,059-5,313. Its strict count
    is lower to 150k, and higher from 200k (`zero`) or 250-300k (`fail`). Late per strict
    site, whole decay
    (0.397-0.405 against 0.494-0.507 per 5k) and non-strict children (0.13-0.18 against
    0.25-0.28) are lower, and copies by strict parents also (0.49-0.60 against 0.72-0.76).
    Re-ignitions per 50k fall from 155-184 thousand to 88-97 thousand, and exact copies
    are 13.4-14.7% of births against 6.3-7.4%.
  - **Answer** (executed runs; mechanisms marked as inference or code inspection):
    - The one-way rule drives the growth. With erasure allowed, mean z rises by about
      2 bytes to 500k against about 13 under `fill`. Both routes shrink: in place,
      foreign erasures remove most of what foreign writes add; in copies, the parent's
      own copy erases what neighbors wrote into the child (code inspection).
    - Write cost: the price per write is unchanged. About half as many foreign writes
      pay the barrier, half as many activations stall, and the free monomers that `fill`
      exhausts stay available.
    - In-place losses: more frequent, through a new route (erasure of key bytes), partly
      offset by more gains in place. The net loss is much larger early and close to
      `fill` late.
  - **Limits.**
    - One rule with several effects: erasure removes bytes, returns monomers and can undo
      earlier fills. The runs do not separate which of these keeps keys short or raises
      the late strict count.
    - Two seeds per rule; one erasure price (`e_erase` 1).
    - Rates are per strict entry-0 site, and the strict sets differ in size and length
      between rules.
- **v27** (v18-v25 recomputed with the copy-born census trial; measurement only; revision
  34839f4, job list `v27_census_born.txt`; 12 jobs in one queue with v26's 4 on 4 cores,
  05:19 to 09:42). The research channel asked to fix Known issue 7, recompute the strict
  counts it affects, and say which conclusions of v13-v25 change. Since 34839f4 a key that
  is strict from reset volatile offsets is tried again from the values an exact copy
  carries at birth, and is strict only if both trials are (see `census_born` above).
  Otherwise it is `loose`. The two-carrier replicator verdict is unchanged; v13-v17 use only
  that verdict (census replicators and classes), so they need no recompute. One run per
  distinct dynamics of v18-v25 carries every observer line those versions used; the job
  list maps runs to versions.
  - **Checks.**
    - In all 12 runs, the data rows, the final line and the `# physics`, `# classes` and
      `# subst` lines equal those of the v23 runs of the same names, and so do the
      `# census` fields before `strict=`. Every line that uses the strict verdict can
      change, `# lineage` included. Every removed site moves to `loose`.
    - With `census_born=0`, `ps_probe` at 34839f4 gives the same output as a23e624 byte
      for byte (v25 `zero_s1` settings, to 60k). With `census_born=1` every line that does
      not use the strict verdict is unchanged; the run takes about a quarter longer.
    - At all 80 fate checkpoints (eight runs with `fate=1`) the strict balance equals the
      strict count, and the census mismatch, untracked, stale and replaced counts are 0.
      The v24 decomposition identity holds (residual at most 1.8e-16) and the v25 ledger
      of the mean closes (at most 4.5e-8) in the six runs with `length=1`.
  - **Strict sites** (census, reset-only → copy-born, with the share the second trial
    removes):

    | run | 50k | 150k | 250k | 350k | 500k |
    | --- | --- | --- | --- | --- | --- |
    | `zero` s1 | 6,522 → 6,269 (3.9%) | 5,433 → 5,178 (4.7%) | 3,953 → 3,693 (6.6%) | 3,329 → 3,052 (8.3%) | 2,984 → 2,767 (7.3%) |
    | `zero` s2 | 6,385 → 6,180 (3.2%) | 5,515 → 5,202 (5.7%) | 3,903 → 3,620 (7.3%) | 3,653 → 3,389 (7.2%) | 3,280 → 3,048 (7.1%) |
    | `fail` s1 | 6,656 → 6,453 (3.0%) | 5,415 → 5,222 (3.6%) | 3,768 → 3,537 (6.1%) | 3,310 → 3,069 (7.3%) | 3,075 → 2,885 (6.2%) |
    | `fail` s2 | 6,567 → 6,354 (3.2%) | 5,355 → 5,140 (4.0%) | 3,694 → 3,464 (6.2%) | 3,398 → 3,196 (5.9%) | 3,092 → 2,925 (5.4%) |
    | `t2_s1` | 6,579 → 6,378 (3.1%) | 5,477 → 5,187 (5.3%) | 3,779 → 3,514 (7.0%) | 3,375 → 3,118 (7.6%) | 3,266 → 3,031 (7.2%) |
    | `t3_s1` | 6,605 → 6,405 (3.0%) | 5,006 → 4,745 (5.2%) | 3,563 → 3,303 (7.3%) | 3,405 → 3,192 (6.3%) | 3,161 → 2,951 (6.6%) |
    | `zero` nomut s1 | 8,677 → 8,671 (0.1%) | 8,619 → 8,613 (0.1%) | 8,497 → 8,479 (0.2%) | 8,421 → 8,386 (0.4%) | 8,089 → 8,031 (0.7%) |
    | `zero` nomut s2 | 8,673 → 8,656 (0.2%) | 8,606 → 8,592 (0.2%) | 8,542 → 8,526 (0.2%) | 8,359 → 8,299 (0.7%) | 7,717 → 7,596 (1.6%) |
    | `fail` nomut s1 | 8,722 → 8,716 (0.1%) | 8,657 → 8,654 (0.0%) | 8,615 → 8,615 (0.0%) | 8,613 → 8,612 (0.0%) | 8,589 → 8,574 (0.2%) |
    | `fail` nomut s2 | 8,703 → 8,698 (0.1%) | 8,662 → 8,660 (0.0%) | 8,622 → 8,619 (0.0%) | 8,658 → 8,657 (0.0%) | 8,604 → 8,603 (0.0%) |

    - With copy error (six runs) the second trial removes 3.0-3.9% of strict sites at 50k,
      5.4-7.3% at 500k and at most 6.4-9.0% at any census. They belong to 18.9-22.6% of
      strict genotypes at 50k and 11.6-15.9% at 500k: many rare genotypes. Without copy
      error it removes at most 0.7%, except 1.6% in `zero` nomut s2 at 500k.
    - Every removed site becomes `loose`; `prop` and `other` counts do not change. The
      removed sites hold a filled own-site pointer offset (`ref_inert_filled`) in 88-92% at
      50k and 98-100% from 250k (copy-error runs), and all but 3 of the nomut sites removed
      at 50k, 250k and 500k.
    - Ancestor control (`anc_s2`): 8 of 14 strict sites at 5k, 6 of 12 at 10k and all 5 at
      15k are removed, each with a filled pointer offset. From 15k no strict site remains,
      against 1-5 before to the last census at 80k (extinct at 83,389). `anc_s1` has none
      either way.
  - **What changes, by version** (reset-only as recorded above → copy-born; ranges and
    lists as in each entry). The counts that do not use the strict verdict (births,
    re-ignitions, exact births, decays, active sites, matter) are unchanged.
    - *v18.* The same 120 genotype-points are scanned and all stay strict.
      - Copies by strict parents fall 2.3-7.0% per window, and the strict share of their
        children rises 0.4-2.3 points (85.0 / 82.9 / 84.2 / 84.9 at 50k and 67.2 / 64.2 /
        67.5 / 68.5 at 500k, were 83.5 / 82.4 / 83.3 / 84.5 and 65.0 / 62.9 / 66.2 / 67.6).
        Non-strict children of strict parents, in points of their copies: `multi` 2.2 to
        9.2 (3.2 to 11.9), point 4.4-6.6 (4.0-6.2), gap and env within 0.6 of before; the
        total is 15.7-38.1 (16.6-39.5).
      - Population: strict sites as in the table above, 9-10% filled at 50k (11-13%) and
        86-92% at 500k (87-92%); `loose` up to 350 sites (52); re-ignited strict 13.0-21.7%
        at 50k and 2.0-5.7% at 500k (14.3-23.3% and 3.0-8.7%); the genotype median strict
        share 62-89% (64-89%).
      - Strict parents make 92-93% of copy births at 50k, 74-85% at 200k and 60-80% at 500k
        (94-95%, 77-90%, 63-85%); per strict site 0.33-0.41 copies per window rising to
        0.68-0.79 (0.32-0.40 to 0.66-0.78); their mean length rises from 38.6-39.2 to
        50.6-51.6 (38.7-39.4 to 50.8-51.9). Where the length went is unchanged.
      - Top genotypes: the in-run strict share falls by at most 1.8 points (74.9% at 500k,
        76.7%). Alone, the strict share of first copies changes in 4 of 120 points, by at
        most 0.5; more substitutions leave a non-strict key, so the sensitive length is
        23.5-28.0 (20.8-28.0) and pred 91.7-92.9% (91.9-93.6%); knockouts kill 26-32 bytes
        (25-32).
      - Balance: the shortfall per strict site per 5k ticks is −0.01 to 0.23 up to 150k
        and 0.04 to 0.56 after (−0.02 to 0.22 and 0.06 to 0.54).
      - Without copy error: strict sites 8,031 / 7,596 at 500k (8,089 / 7,717), strict
        children of strict parents 97.2 / 95.5% (96.8 / 94.6%), total loss 2.9-4.5%
        (3.2-5.4%), mean length to 40.7-42.8 (40.8-42.9).
      - Ancestor alone: 9 of the 12 genotype-points stay strict and give 91.5-92.0% strict
        first copies; the 34- and 62-byte sites at 5k and a 36-byte site at 20k are now
        `loose`. `ancestor()` gives 92.0% (m 28, sensitive length 23.25, pred 93.2%;
        knockouts kill 23 of 28), against polite's 92.0% (m 37, 26.75, 92.2%).
      - Ancestor in the run (`anc_s2`): strict parents' children are strict in 81% of 26
        copies at 5k, 50% of 28 at 10k and 15% of 13 at 15k (70% of 33, 44% of 32, 18% of
        17); residue per copy rises from 0.19 to 1.18 to 5.85 (0.33, 1.03, 4.65) and
        foreign offsets from 0.08 to 0.86 to 2.38 (0.36, 0.84, 2.18). Strict sites are 6, 6
        and 0 against 12, 30 and 23 `other` sites (14, 12 and 5 strict); the decline is
        unchanged.
    - *v19.* After 150k, in-place losses total 26,568 / 24,977 (were 27,504 / 26,814), but
      their routes shift.
      - A neighbor's write at 36 now ends strict status: at least 10,289 / 10,659 of the
        losses (39-43%) change 36, against at least 646 / 777. With 36, 38 and 40
        together, at least 43-47% (at least 9%). Code inspection and v25's scratch checks:
        a filled 36 leaves polite's so reset ineffective, so the key copies off register
        from copy-born counters and is now `loose`. Before, such a site stayed strict
        and its later fill of 30 counted as the loss.
      - The fill of 30 alone: 6,689 / 6,925 (was 11,513 / 12,111): 25-28% of in-place
        losses (42-45%), 3.9-4.0% of all strict losses (6.2-6.4%) and 32% of the net
        in-place loss (58-60%).
      - The site itself writes 24-31% of in-place losses (44-47%); other sites 69-76%
        (53-56%). Without copy error: fill of 30 18-19% (32-34%), the site 36% (62-64%), a
        write at 36 44%.
      - Unchanged: converted activations rarely finish a copy (0.23 copies per conversion
        after 150k); in-place change carries the decline.
    - *v20.* Strict sites at 500k: 2,885 / 2,925 under `fail` against 2,767 / 3,048 under
      `zero` (were 3,075 / 3,092 against 2,984 / 3,280); two seeds still do not separate
      the rules. Without copy error 8,574 / 8,603 (8,589 / 8,604): the decline stays
      removed. Per strict site the net in-place loss is −0.086 / −0.085 (`zero`) against
      −0.086 / −0.094 (`fail`), and the net decline −0.009 to −0.010 under both.
      Offset-0 self-losses fall 92-100% (94-100%). Changed: foreign fills of 36, 38 and 40
      with copy error change by −8% to +1% (were +21% to +30%); without copy error they
      fall 93-96% (83-87%).
    - *v21.* Foreign-written in-place losses: the victim's pointer direction is filled in
      98-99% (94-97%); it is offset 30 in 36-44% (72-79%) and 34-40 in 54-62% (17-22%).
      Writers: strict 32-38% (40-47%), `loose` or `prop` 13-16% (4-6%), `other` 49-52%
      (48-54%); the `MOV` at 15 in 79-85% (85-89%). Off-entry ignitions are unchanged in
      substance: `other` sites ignite 86-99% (87-100%), mostly at 33 and 31.
    - *v22.* With copy error, strict sites fall from 6.2-6.5k at 50k to 2.8-3.0k at 500k
      (6.4-6.7k to 3.0-3.3k), still about 2-fold. Past 48 bytes at 500k: 69-79% (70-80%).
    - *v24.* D is 0.324-0.393 (0.313-0.379). Shares of D:
      - in place, fill of 30 by the `MOV` at 15: 3.6-4.2% (7.3-8.6%); all fills of 30
        4.6-5.1% (8.5-9.7%); with children whose 30 another site wrote, at most 10-12%
        (14-16%);
      - in place, foreign at pointers 34-40 only: 8.4-9.4% (1.5-2.1%);
      - `multi` children 14-15% (17-18%); whole decay 23.5-25.0% (24-25%); `env` 23-26%
        (23-26%); re-ignitions at 0 10-14% (11-14%).

      Late, the `MOV` fills of 30 are 27-33% of entry-0 in-place losses (59-67%), and
      pointer-only fills 56-62%. The largest terms are still whole decay of longer keys
      and foreign differences in children.
    - *v25.* Mean z changes by 0.2-0.3 bytes (53.1 / 52.0 / 53.8 / 53.5 at 500k, were 53.4
      / 52.3 / 54.0 / 53.7); the strict entry-0 count by 3-7%.
      - Ledger, 0 to 500k: foreign additions in place to keys that stay strict +18.6 to
        +19.1 (+34.7 to +38.2); the parent's z against the mean +9.1 to +12.5 (−0.4 to
        +3.4); re-ignitions +14.9 to +16.0 (+13.2 to +14.0); foreign losses in place −11.35
        to −12.27 (−17.6 to −19.2); whole decay −26.4 to −28.7 (−28.3 to −30.1).
      - In-place additions are 75-77% of bytes added to strict keys (80-82%), 0.24-0.25
        bytes per strict site per 5k ticks over the run (0.40-0.42). Many additions had
        gone to keys with 36 filled, which are now `loose`.
      - Pointer states: strict parents with 36 filled make no copies (0.6-0.9% in
        register and 2.0-2.5% off register before). Off-register parents make 7.0-7.5%
        of copies (10.1-10.5%), 82-84% of `multi` children (87-88%) and 55-61% of the
        additions by the `MOV` at 15 in place (70-74%).
      - By z bin, late, strict children minus exits still falls with length (−0.022 to
        +0.038 up to 44 bytes, −0.175 to −0.157 at 57-60); foreign losses in place per
        site are higher in every bin.
  - **Which conclusions change.**
    - The ranking of in-place loss routes (v19, v21, v24): the fill of a pointer
      direction, mostly 36, is now the largest foreign route, and the fill of 30 is
      second. Both use the own-site direction role of INERT, so the reading that both
      depend on it is unchanged and holds for a larger share.
    - v20: with copy error the operand split no longer raises foreign fills of 36, 38 and
      40.
    - v25: the in-place credit is about half as large, and filled-36 parents drop out of
      the strict set; the source of length (foreign writes, mostly in place) and the
      answer (a by-product of the write rule, no gain for long keys) stand, and v26
      confirms the write-rule cause.
    - Unchanged: v13-v17 (two-carrier verdict); v18's reading (in the run the strict share
      of children falls far below the 92% of the same genotypes alone, through env, multi
      and gap copies, not length sensitivity) with `multi` smaller; v20's finding that two
      seeds do not separate the operand rules and that without copy error `fail` removes
      the decline; v21's off-entry ignitions; v22's 2-fold decline.
  - **Limits.**
    - The born values are those of the reference's exact child. A variant whose own
      children carry other counter values is still tried with polite's.
    - A key that fails only the born trial may still copy faithfully from other starting
      values; `loose` means it does not from these.
- **v28** (the roles of INERT in in-place losses, gains, length and copies; measurement
  only; revision 14dea48, job list `v28_role.txt`; 6 jobs on 4 cores, 14:12 to 16:53,
  the four copy-error runs in 2 hours 28 minutes). The research channel asked to separate
  the own-site direction role of INERT from its other meanings in the ledger without
  changing the dynamics, to re-attribute the in-place loss routes (fill of 36, fill of 30
  and so on), and to say which conclusions of v22, v25 and v27 change. `role=1` (above)
  classes each byte that an in-place change or a copy touched by the role INERT had there
  in the key before: own-site direction (`dir`), operand, value, empty slot (`none`), or
  substituted (`sub`). It then tries each strict loss and gain with the `dir` bytes another
  site wrote put back to INERT. This stands in, to first order, for an own-site direction
  code that `fill` does not let other sites overwrite (Open proposals). The runs repeat v27
  `zero_m195_s1/s2`, `fail_m195_s1/s2`, `zero_nomut_s1` and `fail_nomut_s1` with `role=1`,
  which needs `route=1 length=1`; the nomut runs of v27 had neither. Lists are `zero` s1 /
  s2; `fail` s1 / s2.
  - **Checks.**
    - Without the `# role` and `# rolelen` lines (and the `# route*` lines in the nomut
      runs), each output equals its v27 run line for line.
    - In all 60 windows the classes of each loss route sum to the `# route` count, and the
      gain classes to its gains; the `# rolelen` bytes and exits equal the `# length`
      in-place and loss terms (credits to print precision).
    - Every kept loss holds exactly one foreign `dir` byte: over each run the foreign `dir`
      bytes in losses sum to the kept count, give or take 1.
  - **Entry-0 in-place strict losses by route** (% of the losses). The five fill rows are
    the losses kept by the counterfactual: another site filled one own-site direction byte,
    and nothing outside own-site direction bytes changed.

    | route | 0-500k | 150k-500k |
    | --- | --- | --- |
    | losses (count) | 26,391 / 26,159; 26,092 / 26,375 | 19,824 / 19,034; 19,322 / 19,309 |
    | foreign fill of 36 | 49.2 / 50.9; 48.0 / 45.6 | 51.3 / 55.3; 51.7 / 48.8 |
    | foreign fill of 30 | 32.9 / 34.3; 34.2 / 35.9 | 33.3 / 36.0; 36.0 / 36.9 |
    | foreign fill of 38 | 4.1 / 4.4; 5.4 / 5.0 | 4.6 / 5.1; 6.3 / 5.8 |
    | foreign fill of 40 | 0.9 / 0.6; 0.7 / 0.5 | 1.1 / 0.6; 0.9 / 0.5 |
    | foreign fill of 34 | 0.4 / 0.3; 0.4 / 0.5 | 0.2 / 0.1; 0.2 / 0.2 |
    | other foreign changes | 1.4 / 1.3; 1.4 / 1.3 | 1.4 / 1.2; 1.3 / 1.2 |
    | the site itself | 11.0 / 8.2; 9.9 / 11.2 | 8.2 / 1.7; 3.5 / 6.6 |

    - **Own-site direction fills by other sites** are 87.5-90.5% of the losses over the
      run and 90.4-97.1% after 150k. A loss that fills an own-site direction byte and
      also changes another kind of byte (`dir_mixed`) occurs 0-4 times per run. So the
      counterfactual adds nothing beyond the class: a loss whose only change is a foreign
      own-site direction fill is kept by construction.
    - **The rest.** The site itself writes 8.2-11.2% (1.7-8.2% after 150k), mostly into
      its own empty slots (`none`, 4.8-8.6% of all losses) or over non-inert bytes (`sub`,
      1.8-5.0%); it fills its own direction bytes in 0.2-2.0%, mostly before 150k. Other
      foreign changes are mostly fills of tail bytes read as values (0.9-1.2%).
    - **Alone** (scratch check at 14dea48: census trial from reset and copy-born counters,
      each of the 255 values, both operand rules), polite is not strict with 30 or 36
      filled and is strict with 34, 38, 40 or 50 filled. The losses at 38 and 40 are in
      evolved keys (inference).
    - **Gains in place**: 2,019-2,985 over the run. 4.0-6.6% need a foreign own-site
      direction fill (`undone`): 108-140, against 23,077-23,667 kept losses.
    - **Off-entry losses** (4,495-8,647) are 91-97% substitutions, mostly by the site
      itself; 3.0-6.9% are kept.
  - **Share of D** (v24's decomposition, D as in v27: 0.365 / 0.324; 0.393 / 0.356 per
    site per 5k ticks).
    - The kept losses carry 13.6 / 14.4; 14.0 / 13.5% of D. They are v27's fills of 30 and
      foreign pointer fills (4.6-5.1% and 8.4-9.4%), now shown to change nothing else.
    - All entry-0 in-place losses carry 14.2 / 11.1; 10.6 / 11.0%, less than the kept part
      in three runs because the site's own losses fall from early to late.
    - Whole decay (23.5-25.0%), `env` and `multi` children (23-26% and 14-15%) and the fall
      of re-ignitions (10-14%) lie outside in-place losses; the counterfactual does not
      touch them.
  - **Length** (v25's ledger, 0-500k).
    - Foreign in-place additions to keys that stay strict credit +18.57 / +18.96; +18.55 /
      +19.10 to the mean z. Own-site direction fills give +2.47 / +2.58; +2.57 / +2.70
      (13-14%), at 34, 40 and 38; 36 almost never, since a filled 36 leaves the strict set.
      Empty slots give +15.87 / +16.16; +15.74 / +16.18 (85%), operand and value fills
      +0.22 to +0.24.
    - Exits by foreign loss in place credit −11.70 / −12.27; −11.78 / −11.35, and 99-100%
      of that is kept losses.
    - So length comes mostly from fills of empty slots, which a direction split leaves
      alone. To first order the split removes the direction fills (+2.5 to +2.7) and
      postpones the kept exits; how those sites would end instead is not followed.
  - **Copies.**
    - Strict children of strict entry-0 parents: of the bytes added by foreign writes
      (26,540-30,253), 7.9-8.8% are at own-site direction offsets of the parent's key;
      of residue, 3.4-6.2%; of the parent's own writes, 3.6-5.4%.
    - Non-strict `env` children: 38.9-42.0% have a foreign-written difference at an
      own-site direction offset of the parent's key, and 4.5-5.2% have no other foreign
      difference. A non-inert own-site code would protect a child's byte only once the
      parent had written it, which was not recorded, so 4.5-5.2% is an upper bound on the
      `env` children it could keep strict at first order.
  - **Without copy error** (`zero_nomut_s1` / `fail_nomut_s1`).
    - Entry-0 in-place losses: 1,453 / 185, every one a foreign fill of a single own-site
      direction byte: 36 in 69.6 / 55.7%, 30 in 27.9 / 41.6%, 38 in 2.1 / 2.2%, 40 and 34
      in under 1%. The site itself causes none. Gains: 51 / 124, of which 3 / 0 undone.
    - In-place credit to the mean z: +0.56 / +0.07, of which own-site direction fills
      +0.18 / +0.04 (32 / 47%), mostly at 34. Of the bytes foreign writes add to strict
      children, 31 / 43% (of 3,354 / 836) are at own-site direction offsets. This is the
      filled 34 that spreads in `zero_nomut_s1` (v25); alone it leaves polite strict.
  - **Which conclusions change.**
    - *v22.* Polite alone with 36 filled is not strict from copy-born counters (above), so
      "stays strict with any single fill of 34, 36, 38, 40 or 46-63" now holds for 34, 38
      and 40 and for offset 50, the one tail byte rechecked. The direction path of Answer 1
      (v21 and v22 reading; recomputed in v27) is now measured by role: own-site direction
      fills by other sites are 87.5-90.5% of entry-0 in-place losses, each a single byte.
      The 2-fold decline is unchanged.
    - *v25.* The answer stands: length comes from foreign writes, mostly in place, as a
      by-product of the write rule. The in-place part is 85% fills of empty slots and
      13-14% fills of own-site direction bytes, so a direction split would not remove the
      source of length.
    - *v27.* The ranking stands, measured directly: fills of 36 first, of 30 second, then
      38, 40 and 34. v27 inferred from offsets that both routes use the own-site direction
      role; the role classes confirm it, with no other byte changed. "Holds for a larger
      share" refers to in-place losses: they carry 13.5-14.4% of D, and the decline's larger
      terms lie elsewhere.
    - v24's in-place shares, v20 and v21 are unchanged; v28 changes no count.
  - **Limits.**
    - First order: no feedback on the run. The refused writer's next steps, the cost of a
      non-inert own-site code (monomers, decay), and what kept sites do later are not
      modeled.
    - Roles come from the key and its census trial (`op_mask`), not from the run; a byte
      read both as a direction and as a value (polite's 30) counts as `dir`.
    - Two seeds per rule with copy error, one without.
- **v29** (refuse foreign writes into active sites; changes the dynamics; revision 797cac6,
  job list `v29_ext_active.txt`; 4 jobs on 4 cores, 01:11 to 02:22). The research channel
  asked for the fourth control of v25 (Open proposals): a write from another site into a
  site that holds an activation is refused whatever the bytes (`ext_active=refuse`, above),
  so nothing outside a running key adds to it or removes from it. The runs repeat v27
  `zero_m195_s1/s2` and `fail_m195_s1/s2` with `ext_active=refuse` and nothing else
  changed. The test is criterion 1 alone: with copy error, strict sites (copy-born census
  trial) do not fall from 350k to 500k, and strict at 500k / strict at 50k ≥ 0.8. Lists
  are `zero` s1 / s2; `fail` s1 / s2.
  - **Criterion 1: all four runs fail.** Strict sites:

    | run | 350k → 500k | 500k / 50k | v27, same seed |
    | --- | --- | --- | --- |
    | `zero` s1 | 4,512 → 3,777 (−735) | 0.557 | 3,052 → 2,767 (−285); 0.441 |
    | `zero` s2 | 4,331 → 3,696 (−635) | 0.560 | 3,389 → 3,048 (−341); 0.493 |
    | `fail` s1 | 4,200 → 3,792 (−408) | 0.555 | 3,069 → 2,885 (−184); 0.447 |
    | `fail` s2 | 4,357 → 3,849 (−508) | 0.571 | 3,196 → 2,925 (−271); 0.460 |

    | tick | `zero` s1, v29 / v27 | `zero` s2 | `fail` s1 | `fail` s2 |
    | --- | --- | --- | --- | --- |
    | 50k | 6,786 / 6,269 | 6,599 / 6,180 | 6,835 / 6,453 | 6,740 / 6,354 |
    | 150k | 5,939 / 5,178 | 5,923 / 5,202 | 5,743 / 5,222 | 5,606 / 5,140 |
    | 250k | 5,479 / 3,693 | 5,064 / 3,620 | 5,388 / 3,537 | 5,246 / 3,464 |
    | 300k | 5,287 / 3,149 | 4,856 / 3,400 | 4,823 / 3,303 | 5,076 / 3,114 |
    | 350k | 4,512 / 3,052 | 4,331 / 3,389 | 4,200 / 3,069 | 4,357 / 3,196 |
    | 400k | 4,174 / 3,023 | 4,177 / 3,241 | 3,967 / 2,931 | 3,908 / 3,003 |
    | 450k | 3,827 / 3,106 | 3,900 / 3,000 | 3,967 / 3,001 | 4,038 / 3,104 |
    | 500k | 3,777 / 2,767 | 3,696 / 3,048 | 3,792 / 2,885 | 3,849 / 2,925 |

    The least-squares slope over 350k-500k is −255 / −218; −122 / −139 strict sites per
    50k ticks (v27: −77 / −126; −48 / −71).
  - **Checks.**
    - Without `ext_active`, `ps_probe` at 797cac6 gives the same output as 8e16ff2 byte for
      byte (v27 `zero_m195_s1` settings, to 60k). Unit test 8b: with `refuse`, a copier
      leaves active neighbors' bytes intact and still writes inactive ones.
    - In every window of the four runs the five foreign in-place loss routes of `# route`
      and the foreign in-place terms of `# length` are 0. The fate balance equals the
      strict count with no mismatch, the v24 identity holds (residual at most 6.7e-17), and
      the length ledger closes.
    - Refused writes (`ext_active_blocked`): 72.4 / 70.2; 74.1 / 69.3 million per run,
      6.8-8.5 million per 50k window after 150k.
  - **What changed** (executed runs; causes marked as inference).
    - More strict sites at every checkpoint, and a ratio of 0.56-0.57 instead of
      0.44-0.49. The fall is later, not stopped: v27 falls fastest at 150k-250k, v29 at
      300k-350k (−525 to −775 in that window), and v29 is still falling at 500k. So
      350k-500k, where v27 fell slowly, is v29's steep part.
    - In both rules the steep part starts with mass shortage. Writes refused for want of a
      free monomer (`no_mass`) jump from near 0 to tens of thousands per window: in v27 at
      150k-250k, in v29 at 300k-350k (2,844 → 32,103 / 228 → 17,154; 18,169 → 76,608 /
      7,809 → 54,753), with 18-26k free monomers left at the end of that window. The two
      coincide in all eight runs; that the shortage drives the fall is inference.
    - Length grows more slowly, so mass runs short later. Mean z of strict entry-0
      activations goes from 40.1 / 40.3; 40.1 / 40.2 at 50k to 49.2 / 48.8; 50.0 / 50.1 at
      500k (v27: 53.1 / 52.0; 53.8 / 53.5). In the v25 ledger over the run, the foreign
      in-place credit (+18.6 to +19.1 in v27) and the exits by foreign loss (−11.4 to
      −12.3) are gone. Strict children credit +11.9 / +11.5; +13.8 / +13.8 (v27: +15.9 to
      +18.8), re-ignitions +15.9 / +14.0; +14.5 / +16.4 (as before), and decay −17.9 /
      −16.8; −18.8 / −20.0; with the smaller terms the net is +9.2 / +8.8; +10.0 / +10.1
      (v27: +12.1 to +13.8).
    - Foreign writes still reach children under construction, which are not active: they
      add 26,932 / 30,958; 30,342 / 31,011 bytes to strict children (v27: 26,540-30,253)
      and +5.6 / +6.5; +6.4 / +6.6 to the mean z.
    - Copy writes into active neighbors are refused too (code inspection). Copies by
      strict entry-0 parents rise from 0.31-0.33 to 0.56-0.59 per site per 5k ticks
      (v27: 0.36-0.39 to 0.72-0.76), and copies born fall from 0.94-1.04 to 0.82-0.93
      million per run.
  - **v24 decomposition** (per strict entry-0 site per 5k ticks, 100k-150k against
    350k-500k). D falls from 0.32-0.39 to 0.244 / 0.237; 0.268 / 0.263. The foreign
    in-place routes, 13.6-14.5% of D in v27, are 0. What D is made of now:
    - whole decay rising: 27.2 / 31.4; 26.4 / 25.3%. Decay per site rises 16.5-18.4%, and
      mean z over the same windows 16.5-19.5%; v25 found that the hazard follows key
      length;
    - `env` children (a difference another site wrote): 29.3 / 29.1; 27.2 / 27.4%, rising
      from 0.031-0.034 to 0.103-0.107 (v27: 0.038-0.041 to 0.123-0.133);
    - `multi` 12.9-14.8%, `gap` 8.2-14.7%, `point` 2.5-3.5%;
    - fewer re-ignitions at offset 0: 10.1 / 16.0; 13.5 / 17.1%.
  - **Answer.** Refusing foreign writes into active sites removes the in-place routes
    entirely and keeps more strict sites, but within 500k ticks it delays the decline
    rather than stopping it. What is left acts before a child ignites (foreign writes into
    children under construction, seen as `env`, `multi` and `gap` children and as length)
    or follows length (whole decay, mass shortage). Whether v29 levels off later at a
    higher count is not known from these runs.
  - **Limits.** Two seeds per rule; 500k ticks. The refused writer pays and gets nothing
    back. Activity is read when writes are applied, before the tick's ignitions, so a
    site that ignites in a tick can still be written in that tick.
- **v30** (copy errors only on cross-site `MOV`s; changes the dynamics; revision 80a16c9,
  job list `v30_mut_scope.txt`; 4 jobs on 4 cores, 1 hour 42 minutes to 1 hour 58 minutes
  per run). The research channel asked for the second length-growth control of v25 (Open
  proposals): copy error applies only to a `MOV` whose destination names a neighbor
  (`mut_scope=cross`, Model above). Counter set-up and resets then copy exactly, while
  children still receive errors. The runs repeat v27 `zero_m195_s1/s2` and
  `fail_m195_s1/s2` with `mut_scope=cross` and nothing else changed (`ext_active` stays
  `allow`, `ext_write` stays `fill`). The test is criterion 1 alone, as in v29. Lists are
  `zero` s1 / s2; `fail` s1 / s2.
  - **Criterion 1: all four runs fail.** Strict sites:

    | run | 350k → 500k | 500k / 50k | v27, same seed |
    | --- | --- | --- | --- |
    | `zero` s1 | 3,208 → 2,951 (−257) | 0.449 | 3,052 → 2,767 (−285); 0.441 |
    | `zero` s2 | 3,369 → 3,083 (−286) | 0.469 | 3,389 → 3,048 (−341); 0.493 |
    | `fail` s1 | 3,166 → 2,963 (−203) | 0.444 | 3,069 → 2,885 (−184); 0.447 |
    | `fail` s2 | 3,527 → 3,081 (−446) | 0.460 | 3,196 → 2,925 (−271); 0.460 |

    | tick | `zero` s1, v30 / v27 | `zero` s2 | `fail` s1 | `fail` s2 |
    | --- | --- | --- | --- | --- |
    | 50k | 6,572 / 6,269 | 6,579 / 6,180 | 6,671 / 6,453 | 6,696 / 6,354 |
    | 150k | 5,247 / 5,178 | 5,236 / 5,202 | 5,053 / 5,222 | 5,389 / 5,140 |
    | 200k | 4,698 / 4,544 | 4,774 / 4,293 | 4,698 / 3,989 | 5,012 / 4,073 |
    | 250k | 3,884 / 3,693 | 4,028 / 3,620 | 3,787 / 3,537 | 4,503 / 3,464 |
    | 300k | 3,591 / 3,149 | 3,781 / 3,400 | 3,253 / 3,303 | 3,974 / 3,114 |
    | 350k | 3,208 / 3,052 | 3,369 / 3,389 | 3,166 / 3,069 | 3,527 / 3,196 |
    | 400k | 3,105 / 3,023 | 3,304 / 3,241 | 2,939 / 2,931 | 3,323 / 3,003 |
    | 450k | 2,949 / 3,106 | 3,125 / 3,000 | 2,995 / 3,001 | 3,328 / 3,104 |
    | 500k | 2,951 / 2,767 | 3,083 / 3,048 | 2,963 / 2,885 | 3,081 / 2,925 |

    The least-squares slope over 350k-500k is −93 / −104; −55 / −133 strict sites per 50k
    ticks (v27: −77 / −126; −48 / −71).
  - **Checks.**
    - With `mut_scope` unset or `all`, `ps_probe` at 80a16c9 gives the same output as
      bfab877 byte for byte (v27 `zero_m195_s1` settings, to 30k). Unit test 8c: with every
      `MOV` in error, `cross` leaves the own-site copy exact and gives the neighbor copy the
      same erroneous byte as `all`.
    - In every window of the four runs the fate balance equals the strict count with no
      census mismatch, the v24 identity holds (residual at most 8.1e-17), and the length
      ledger closes.
  - **What changed** (executed runs; causes marked as inference or code inspection).
    - **`multi` children.** Their share of copies by strict entry-0 parents falls from
      1.5 / 2.0; 1.4 / 1.9% to 0.7 / 1.3; 0.7 / 1.0% at 50k, but reaches 8.5 / 7.9;
      8.5 / 8.0% at 500k (v27: 9.2 / 8.7; 9.1 / 8.9%). Over the run there are 10,886 /
      11,338; 11,827 / 11,292 (v27: 12,454 / 12,982; 12,764 / 13,199), 7-14% fewer.
      Parents off register with neither 36 nor 38 filled (`# lengthptr`) still make
      78-80% of them (v27: 78-79%).
    - **Off-register copies.** Copies by off-register strict entry-0 parents fall from
      1.6-2.5% to 0.8-1.6% of those parents' copies at 50k, and from 7.4-7.5% to 6.7-7.1%
      over the run. At 500k they are 10.0-10.8% (v27: 10.7-11.6%).
      Code inspection: a completed in-register loop leaves both counters at 0, which is
      K mod 64. A reset that does not happen then leaves the next copy in register; it
      shifts a copy only when the counters do not start from a completed loop, as in a
      copy-born child's first cycle. A reset that writes a wrong value, the route v30
      removes, shifts a copy in any cycle. Two reset `MOV`s per cycle at `p_mut` = 0.003
      predict about 0.6% of copies shifted that way, close to the observed drop of
      0.3-0.8 points (inference). The late rise of off-register copies therefore comes
      from other routes. v26's scratch checks found one, a walled read of K through a
      filled 34, which acts in a first cycle. Filled 34 spreads as in v27: 71-93% of
      strict sites at 500k (v27: 71-91%). The split between routes was not measured.
    - **Shifted in-place additions.** Bytes added in place by shifted `MOV`s at 15
      (`# lengthptr`, writers of any status) fall by 19-24% over the run. Those at shifts
      31 and 62, which unreset counters give (v26), and 63 and 1 stay as in v27 (13.9-15.6
      against 13.9-15.8 thousand). Those at other shifts fall from 27.9-30.5 to 19.6-20.3
      thousand, as expected if a wrong reset value spreads its shift over all values
      (inference).
    - **Mass shortage starts 50k-100k ticks later.** Writes refused for want of a free
      monomer (`no_mass`) per 50k window:

      | window ending | `zero` s1, v30 / v27 | `zero` s2 | `fail` s1 | `fail` s2 |
      | --- | --- | --- | --- | --- |
      | 150k | 0 / 10 | 0 / 26 | 0 / 68 | 0 / 294 |
      | 200k | 292 / 2,902 | 41 / 8,287 | 872 / 32,157 | 11 / 18,445 |
      | 250k | 10,121 / 35,419 | 6,116 / 26,304 | 37,875 / 65,448 | 1,928 / 54,694 |
      | 300k | 14,028 / 39,314 | 17,971 / 30,158 | 69,211 / 54,665 | 28,399 / 74,913 |
      | 350k | 37,848 / 45,431 | 31,207 / 25,846 | 70,774 / 77,364 | 53,688 / 75,283 |

      Free monomers at 150k are 45.0 / 53.7; 46.8 / 55.7 thousand (v27: 37.7 / 35.4;
      34.0 / 30.9). Strict sites stay above v27 at 200k and 250k in all four runs and at
      300k and 350k in three. At 500k they are 1-7% above v27, as at 50k (3-7%), so the
      ratio does not change.
    - **Length grows more slowly at first, then catches up.** Mean z of strict entry-0
      activations is 40.2 / 40.3; 40.3 / 40.2 at 50k and 46.5 / 46.5; 47.8 / 46.4 at 250k
      (v27: 40.6 / 41.0; 40.6 / 41.0 and 48.1 / 47.5; 49.1 / 49.4), but 52.7 / 52.5;
      53.2 / 52.0 at 500k (v27: 53.1 / 52.0; 53.8 / 53.5). In the v25 ledger over the run,
      the foreign in-place credit falls to +15.7 / +15.4; +16.3 / +14.8 (v27: +18.6 to
      +19.1), strict children to +12.8 / +9.9; +15.2 / +14.8 (v27: +15.9 to +18.8) and
      decay to −20.7 / −19.8; −22.5 / −23.4 (v27: −26.4 to −28.7); the net is +12.7 /
      +12.5; +13.2 / +12.1 (v27: +12.1 to +13.8). That fewer off-register copy loops
      early mean fewer foreign additions and so a later shortage is inference.
    - Copies born per run are 0.90 / 0.93; 0.95 / 0.87 million (v27: 0.94 / 0.94; 1.04 /
      1.04).
  - **v24 decomposition** (per strict entry-0 site per 5k ticks, 100k-150k against
    350k-500k). D is 0.362 / 0.320; 0.388 / 0.321 (v27: 0.365 / 0.324; 0.393 / 0.356).
    `multi` is 12.8-14.5% of D (v27: 13.8-15.3%), late `multi` per site 0.050-0.062
    (v27: 0.057-0.065). Whole decay is 22.2-27.4% (v27: 23.5-25.0%) and `env` 23.5-25.4%
    (v27: 23.4-26.2%). Own in-place losses and gains at 100k-150k both fall (losses
    0.009-0.015 to 0.001-0.008 per site, gains 0.009-0.017 to 0.001-0.008), and their
    shares of D shift by up to 6.5 points in opposite directions. The remaining terms move
    by at most 3 points.
  - **Answer.** Removing copy error from `MOV`s into the own site removes the
    counter-reset route, halves `multi` children early and delays mass shortage by
    50k-100k ticks. Strict counts end only 1-7% above v27, and criterion 1 fails in all
    four runs. Most off-register copying late, and most `multi` children, come from
    routes other than a copy error in a counter reset.
  - **Limits.** Two seeds per rule; 500k ticks. `cross` also makes probes and other
    own-site `MOV`s exact, not only resets. The routes behind the late off-register
    copies are not separated.

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
separates them (below). Block rotation without binding does not clear non-replicating
sites. (v17 shows that the decline returns under form M after 100k, about 2-fold by 500k;
the statements here hold to 100k.) Up to 1e-4 it has no clear effect. From 1e-3 it cuts a
third or more of all copies, replicators fall further than under `dead0`, and
non-replicators shift from copy-born to re-ignited. A cut copy ends by igniting a site the
parent wrote only in part, which fits that shift but was not measured directly.

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

v17 reading (counts from executed runs, recomputed in v23 with the topped-up census;
mechanisms are inference):

- **The data-byte shift keeps growing.** It grows over the whole 500k ticks: about 1 point
  below the uniform-rate control by 150k and 2.8 points by 500k, with a wide spread between
  runs (1.5-4.3). The plateau from 200k to 450k seen under the seed-limited census came from
  leaving out the replicators past 48 bytes.
- **Only data bytes shift.** Opcode bytes show no consistent shift over 500k. This fits the
  synonym inference in the design note: selection reaches data bytes and leaves opcodes.
  The control's own mutational drift over the same span is 0.8-7.9 points.
- **The hazard falls against the control in six runs of eight.** The mean gap widens to
  -3.8% at 500k, but t1_s2 and t3_s2 stay at or above their controls at most points. In
  absolute terms the hazard rises in every run: replicators lengthen from about 42 to 53-55
  non-inert bytes and drift toward the composition of random bytes under both rates, and
  where the per-op rates help, they only slow the rise.
- **The decline returns under uniform form M, about 2-fold.** The v14 statement that form M
  almost removes the decline, and the v15 non-replicator shares, hold to 100k only. In
  `m195` from 50k to 500k:
  - replicators fall from 6.4-6.6k to 3.0-3.3k (the seed-limited census showed a 6-9x fall,
    because it counted the long replicators as non-replicators);
  - copy-born non-replicators grow from 10-11% to 24-26% of active sites;
  - exact births fall from 39-43% to 6-7%;
  - re-ignitions rise from 54-57% to 84-86% of births, while copy births stay near
    24-31k per 50k ticks.

  Form M has no in-place damage, so this decline has another source. The fall in exact
  births suggests that copies from evolved replicators more often yield non-replicators,
  but copy fidelity per genotype was not measured (v18 measures it).

v18 reading (counts from executed runs, recomputed in v23 with the topped-up census; which
mechanism fills each class is inference; v27 lists what the copy-born census changes):

- **The genotypes' own fidelity does not fall.**
  - Alone, the leading strict genotypes give 91-94% strict first copies at every point from
    50k to 500k. This is within about one point of the prediction from their substitution
    scans.
  - Their exact share falls with m as (1-u)^m, from 89.2% at m 37 to 85.1% at m 54-56. This
    is Eigen's quality factor for precise copies, Q = q^ν
    ([Eigen 1971](../../docs/references/pdf/eigen-1971-selforganization-of-matter.pdf#page=11),
    journal pp. 475 and 491).
  - Their strict share does not fall (92.0% to 93.1%), because the bytes they gained are
    neutral: the sensitive length stays at 21-28.

  Length growth costs exact copies, not replicating children.
- **The length grew outside the copy mechanism.** In the leading genotypes the growth is a
  filled own-site pointer offset and up to 18 bytes past polite's region, which are never
  executed. A copy error only replaces a non-inert byte with another (`src/ps_exec.cpp`), so
  these bytes did not come from an aligned copy of the parent. They came from other sites,
  from residue or from a misaligned copy, and were then copied along (inference). Without
  copy error, length grows too.
- **The short ancestor is no help here.** Alone, `ancestor()` is no more faithful than
  polite (92.25% against 92.0%). Under these settings it does not persist: 4 of 6 seeds are
  extinct by 100k, and the other two are down to 14 sites and 1. It was not modified.
  Polite's 11 extra bytes are its target check. Without the check, `ancestor()` copies into
  occupied sites, and under `fill` the refused writes leave chimeras: residue reaches 4.6
  offsets per copy by 15k.
- **Fidelity in the run falls, for environmental reasons.**
  - In the run, the same genotypes give 88% strict children at 50k and 50-77% from 200k.
  - Over all strict parents, losses rise from 16-18 points to 34-43 at 250-350k. Point
    losses (copy errors) stay at 4-7 points.
  - The rise is in three classes, none of which occurs alone:
    - env: mostly offsets written into the target by other sites;
    - gap: in step with writes refused for lack of a free monomer;
    - multi.
- **Lost copies are the smaller part of the decline.** From 50k to 500k, strict children
  per strict-parent copy fall by a factor of 1.25-1.31, while strict sites fall 1.9-2.2-fold
  (6-9-fold under the seed-limited census). Per strict site, copies even rise.
  - **A further loss channel.** With copy error, the balance leaves a loss of strict sites
    beyond whole-program decay. After 150k it reaches 0.06-0.54 per site per 5k ticks,
    against 0.41-0.52 from decay. Without copy error the same balance nearly closes
    (0.01-0.06). So the missing loss needs copy error somewhere, yet it does not pass
    through the parent's own failed copies.
  - **One route that fits (code inspection, not measured): in-place change by outside
    writes** (known issue 1). Offset 30 is both the direction of polite's source pointer
    and the address its loop jumps back to. A fill there turns a live polite into a program
    that copies from a neighbor; with `[30]=192` the census test finds a non-replicator.
    Mutants and `other` sites write more varied bytes than polite does. This would also fit
    the 96-98% of `other` sites that carry a filled offset. (The seed-limited census also
    showed 22-43% of `other` copies as exact copies of the parent; with the topped-up census
    it is 0-7%, so those parents were long strict replicators.)

    It was not measured here. v19 measures it: the route occurs, it is 42-45% of in-place
    losses after 150k, and its copies are not exact copies of the converted parent.
- **Copy error accelerates a process that the environment alone also starts.** Without copy
  error, intrinsic fidelity is 1. Even so:
  - filled offsets spread to 93-96% of strict sites;
  - env copies rise about ten- to twentyfold;
  - `other` sites grow from about 30 to 193 and 358;
  - strict sites begin to fall after 300k.

  With copy error, the same signs appear by 100k and are larger by an order of magnitude.
- **Method and its limits.**
  - Testing offspring alone follows Avida practice. A04 section 5.2 tests offspring and
    descendant viability alone with a timeout, and notes that solitary tests miss
    interactions ([A04, PDF pp. 21-22, as recorded in the prior-work
    note](../../docs/research/shared-memory-prior-work.md)). Here the gap between alone and
    in-run is that interaction. Under the seed-limited census, `other` genotypes that
    seemed to copy themselves in the run but not alone were mostly strict replicators the
    trial could not seed.
  - Knockout and substitution scans are the kind of measurement Lenski et al. 1999 made in
    digital organisms (abstract only; see `docs/references/unavailable.md`).
  - The test alone covers first copies only, and only the three most-copied strict
    genotypes per run and point.
  - The balance uses windows of 5,000 ticks to stand for intervals of 50,000. Its
    re-ignition term comes from 300 sampled re-ignitions per window.
- **A next measurement** (proposal, not agreed). For each active site between census
  points, count status changes without a birth, and the offsets and writers of the changing
  bytes. Also record how each activation ends (whole decay or wick), by status. (v19 makes
  this measurement.)

v19 reading (counts from executed runs, recomputed in v23 with the topped-up census;
mechanisms marked as inference; v27 lists what the copy-born census changes):

- **The offset-30 route is one of the two main in-place routes.** After 150k a neighbor's
  fill of offset 30 turns a strict activation into a non-replicator 11,513 and 12,111 times,
  and in all but 4 of 25,455 cases over the run nothing else non-volatile changes. That is
  42-45% of in-place losses, 6.2-6.4% of all strict losses and 58-60% of the net in-place
  loss. The converted program does copy from the neighbor that [30] now names, but it seldom
  finishes a copy and then mostly holds its site until whole decay. At most 0.1% of its
  children have its own genotype. (The seed-limited census put it at 18% of in-place
  losses; most of the other losses it counted were keys pushed past 48 bytes, relabels.)
- **In-place change carries the decline (accounting, not a counterfactual).** With copy
  error, births exceed decay and wick ends in every window, and strict sites fall because
  in-place losses exceed in-place gains. Without in-place losses the population, mass and
  births would differ, so the decomposition does not say how large the population would
  then be.
- **v18's missing loss is measured.** Wick ends plus the net in-place loss are of the size of
  v18's balance shortfall, with and without copy error (0.12-0.36 against an estimate of
  0.06-0.28 after 150k with copy error). Most of it is in-place change; wick ends grow
  late.
- **Two routes carry nearly all in-place losses.**
  - The site itself writes 44-47% of in-place losses. Most come from activations ignited at
    an offset other than 0, which run polite's data region as code. An inert operand byte
    names offset 0, so such a run overwrites the program's first opcode (code inspection,
    consistent with 74-77% of these losses changing offset 0). What ignites strict
    genotypes off entry, and why copy error raises their share from under 1% to 22-23% of
    strict births, was not traced here (v21 traces it).
  - Other sites write 53-56%, mostly the fill of 30. Fills of polite's own-site pointer
    bytes 36, 38 and 40 are at least 9% of in-place losses; tail fills are about 3% of
    foreign losses (v21). Alone, polite stays strict with any one of 34-40 filled, so those
    losses involve evolved genotypes or several offsets at once (inference).
- **Both routes come from INERT's double meaning** (known issue 1, inference). An inert byte
  is an empty slot that `fill` lets other sites write, and it is also the own-site direction
  and the value 0. The fills of 30, 36, 38 and 40 use the first meaning; the self-overwrite
  of offset 0 uses the second.
- **Copy error scales the routes; it does not open new ones.** Without copy error the same
  routes occur, with similar shares (the fill of 30 is 32-34% of in-place losses and the
  site itself writes 62-64%), at a rate 17-41 times lower per strict site after 150k.
- **This qualifies v14 and v15.** Whole-program decay cannot alter a live replicator, but
  writes, its own and its neighbors', still can. After 150k they are the larger term.
- **Limits.**
  - Status is the census verdict for a site's bytes alone. Some in-place changes may be
    relabels that leave the behavior in the run unchanged; the scratch writes at
    instruction 8 before 150k are a likely case.
  - Changes of `other` sites are not tested; `found_at_census` (9-47 per window) corrects
    the balance for them.
  - A change with several foreign writers is credited to the first; the writer's status is
    its status when the change is seen.
  - Two seeds per condition; the fill test alone covers polite, not evolved genotypes.
  - `fate=1` costs about 3.4 times the run time (580 s against 170 s per 100k ticks).
- **Next steps** (proposals, not agreed).
  - Separate the meanings of INERT, for example a distinct empty value that `fill` writes
    to, as a one-mechanism comparison under form M. This changes a rule, so it needs
    agreement first. (v20 separates the operand role.)
  - Trace off-entry ignitions of strict genotypes: who ignites them, at which offset, and
    why copy error raises their share.

v20 reading (counts from executed runs, recomputed in v23 with the topped-up census;
mechanisms marked as inference; v27 lists what the copy-born census changes):

- **The minimal split removes the self-overwrite route in both conditions.** An inert operand
  no longer reaches offset 0, and self-written losses at offset 0 almost vanish.
- **Without copy error, it also removes the decline to 500k.** The self-overwrite route was
  then the main source of `other` sites. With the split, `other` sites stay rare, and
  foreign-written losses fall by 88-96% from both strict and `other` writers, although the
  write rule is unchanged. So without copy error, v19's late decline came from the operand
  role of INERT (inference from the counts). Why strict writers also change strict sites
  less often was not traced.
- **With copy error, it does not change the decline.**
  - Copy errors keep making non-replicators directly (the in-run strict share of children
    is as in v19), so `other` sites stay as numerous and keep writing into neighbors. The
    fills of 30, 36, 38 and 40 use the own-site direction role, which this split leaves in
    place.
  - Per strict site, the net in-place loss and the net decline are the same as in v19
    (0.009 per site per 5,000 ticks). Strict sites are lower at 13 of 16 checkpoints from
    150k, by up to 12%, and end at 3,075 and 3,092 against 2,984 and 3,280. v19's two seeds
    differ by up to 10% at a checkpoint, so two seeds do not separate the rules here.
- **Off-entry visits change their end, not their effect (inference).** An off-entry
  activation that once overwrote offset 0, and was counted as an in-place loss, now runs
  through the data region and ends by wick at an inert byte. It leaves intact strict code
  that can be ignited and counted again, which fits the rise in strict re-ignitions and
  wick ends that nearly cancel per site. Who ignites strict code off entry was not traced
  here (v21).
- **Answer to the request.**
  - The self-overwrite route disappears: offset-0 losses fall 94-100%.
  - Foreign fills of 36, 38 and 40 fall 83-87% without copy error and rise 21-30% with it.
    No foreign loss at 47-53 occurs without copy error under either rule.
  - The net in-place loss and the decline improve without copy error (the decline is gone
    to 500k). With copy error they do not improve per strict site, and strict sites end
    about where they end in v19.
- **Limits.**
  - Two seeds per condition, each a single realization.
  - The lower bounds at 36, 38, 40 and 47-53 come from the top 8 offsets per window.
  - Census status is judged under each run's own rule, so a genotype can have a different
    status in v19 and v20.
  - The earlier mass shortage with copy error is not explained. (v21: the same depletion,
    reached sooner.)
- **Next steps** (proposals, not agreed).
  - Split the own-site direction role as well, which addresses the fills of 30, 36, 38 and
    40. This changes the ledger (five more monomers per polite copy, a higher whole-decay
    hazard) and the direction decoding, so it needs agreement on the encoding first.
  - With copy error, trace who writes the remaining foreign in-place losses, and who
    ignites strict code off entry. (v21.)

v21 and v22 reading (counts from executed runs, recomputed in v23 with the topped-up
census; mechanisms marked as inference or code inspection; v27 lists what the copy-born
census changes):

- **The seed-limited census missed long replicators** (v22). It could not seed a key past 48
  bytes, so it counted such a program as `other`. With copy error, strict genotypes grow
  toward the limit and past it: at 500k, 70-80% of strict sites are past 48. The
  seed-limited census counted 626-976 strict sites at 500k against 2,984-3,280, and the
  ones it missed were 54-57% of its `other` sites. This affected every census verdict
  (`census=1`) wherever programs grow past 48. Since b4b4ea1 the census tops up the
  founder, and v23 recomputes v17-v22 with it; v13-v16 keep the seed-limited verdict.
- **The decline is real but about 2-fold, not 6- to 10-fold.** Strict sites fall from
  6.4-6.7k at 50k to 3.0-3.3k at 500k, against 0.6-1.0k under the seed-limited census. At
  500k the two rules do not differ (3,075 and 3,092 under `fail`, 2,984 and 3,280 under
  `zero`). v20's lower seed-limited counts under `fail` therefore reflected which
  replicators are long, not how many replicate (inference from four runs).
- **Answer 1: who writes the remaining foreign in-place losses.**
  - **Writer and instruction.** Polite's copy loop writes them: the `MOV` at offset 15
    (85-89%), reading the writer's own site (70-76%). The writer is `other` (48-54%) or
    strict (40-47%), and was ignited at offset 0 (94-97%). 40-45% of writers are younger
    than 1k ticks, and 58-68% were born by copy. `other` writers are programs that do not
    replicate alone even when topped up.
  - **Direction path.** Nearly all losses (94-97%) fill an inert pointer direction of the
    victim, which is the own-site direction role of INERT: offset 30 in 72-79% and 34, 36,
    38, 40 in 17-22%. Tail fills (46-63) are 2.5-5.6%.
  - **Relabels removed.** Under the seed-limited census half of these losses were tail
    fills, and most of them pushed the key past 48 (relabels, v22). With the topped-up
    census they drop out, which confirms the earlier inference: what remains is mainly the
    fill of 30.
  - **Same under `zero`.** The pattern is the same under `zero`, so the operand split does
    not touch this route.
- **Answer 2: off-entry ignitions.**
  - **Who and where.** `other` sites ignite strict code off entry (87-100%). Under `fail`,
    92-96% of these igniters have been active for at least 1k ticks. The entries are mostly
    33 and 31, then 32 and 34.
  - **Igniting the neighbor** (code inspection). Polite holds 34 at offsets 1 and 4, which
    decodes as `IGNITE`. Its operand is 36 or 38, whose pointers name offset 31 ([37]) or
    33 ([39]). Once 36 or 38 has been filled, the pointer names a neighbor. A
    polite-derived program that runs from offset 1 or 4 then ignites that neighbor at 31
    or 33.
  - **Filling the entry byte.** The same filled pointer makes `MOV 34 36` and `MOV 34 38`
    copy byte 42 (192) into the neighbor's 31 or 33 when empty, and 192 decodes as `DEC`.
    Without copy error, 99% of these ignitions are this one (instruction at 1, entry 31,
    to 150k). With copy error, instructions at 1 and 4 account for 16-52%, and other
    variant instructions (offset 6 above all from 150k, then 0, 3 and 8) for much of the
    rest; those were not resolved.
  - **What the visit does** (own-site emulation of polite entered at 33 holding 192, code
    inspection).
    - Under `zero`: `DEC`'s inert operand names offset 0, so the visit erases byte 0, and
      three `RND`s then write there. This matches v19's self-overwrite of offset 0.
    - Under `fail`: each of those instructions fails, one `WALL` runs, and the activation
      dies by wick at 47 with the code intact.
    - Consistent with this, under `fail` 90-95% of off-entry strict births follow an
      off-entry strict activation that ended by wick on the same site, 12-20 ticks
      earlier. Under `zero` the share is 36-73%, with gaps of 21-83 ticks.
  - **Why copy error raises their share.** The igniters are `other` sites, which copy error
    makes in large numbers (1.0-1.9k against 2-21 without it under `fail`). Without copy
    error the route exists but fires 568 and 647 times per period.
  - **The rise in re-ignitions and wick ends is this route.** Under `fail` against `zero`,
    the extra strict re-ignitions (+112k and +96k) and extra wick ends (+116k and +99k) are
    all off-entry activations. These activations live 40-127 ticks and make almost no
    copies (87-1,615 per period, against 65-166k from activations ignited at 0).
- **Answer 3: writes refused for lack of a free monomer before 200k.**
  - **Depletion.** With copy error, free monomers fall from 61-66k at 50k to 19-24k at
    200k in every run. Matter accumulates in inactive sites (40-44k to 86-100k bytes), in
    walls (3k to 9-11k) and in `other` sites (49-58k to 92-103k bytes), which hold about
    53 non-inert bytes each against about 45 for strict sites at 150k, mostly programs
    past 48 (v22).
  - **Why earlier under `fail`.** At 150k, seed by seed, `fail` holds 3.7k and 4.5k fewer
    free monomers than `zero` (v23 `zero_m195_s2` for seed 2), and 4.4k and 4.6k more
    bytes of code. The excess is not in one class: `other` sites hold 1.8k and 2.6k more, strict
    sites 2.9k more and 1.5k fewer, inactive sites 0.4k fewer and 3.4k more. (The
    seed-limited census put 16.5k and 23.8k more bytes in `other` sites, by counting long
    strict sites there.) Refusals start one checkpoint earlier; from 250k they are in the
    same range under both rules. So the early refusals are the same depletion reached
    sooner; where the extra code comes from was not traced.
  - **Not recorded.** A write is refused when the target site's own pool is empty. The
    distribution of free monomers over sites, and who was refused, were not recorded.
- **Limits.**
  - Two seeds per rule.
  - The topped-up trial tests a program alone with enough monomers to place it, not in the
    depleted run.
  - Writer and igniter status is the census status of the program alone.
  - Offsets, instructions and entries are top-N per window (lower bounds).
- **Next steps** (proposals, not agreed).
  - The census verdict free of the seeding limit is done (b4b4ea1, default top-up; v23
    recomputes v17-v22). v13-v16 are not recomputed.
  - Record per in-place loss which offsets changed together, with the key length.
  - The fill of 30 and the off-entry route both depend on the own-site direction role of
    INERT (a filled 30 redirects polite's source; a filled 36 or 38 turns polite's
    misaligned `IGNITE` toward a neighbor). The open proposal to split that role addresses
    both; it changes the ledger and needs agreement on the encoding.

## Known issues (code inspection)

1. INERT means both "empty" and "own-site pointer / value 0", so self-pointer bytes can be
   filled from outside even under `fill`. Mutation and `RND` never produce INERT. An inert
   operand byte also names offset 0, so a program that runs its own data as code overwrites
   its first byte (v19 counts both effects as routes of in-place loss). `inert_operand=fail`
   removes the second effect (v20); the own-site direction role remains. v28 measures it:
   foreign fills of own-site direction bytes are 87.5-90.5% of entry-0 in-place strict
   losses.
2. Re-ignition is cheap relative to copying, and corpse sites sit at full energy.
3. Without `bond_store`, `e_bond` also charges in-site counter updates.
4. Walls drop bytes during cross-edge copying while the counters still advance.
5. Minor: the cost of a write is computed from the byte behind a wall before the crossing
   check; the wick check covers only the byte at `ip`; modulo bias in direction and opcode
   decoding.
6. Census (observer, not dynamics), resolved in b4b4ea1: the trial seeded the founder from
   the trial center's `mass0` free monomers, so a key with more than 48 non-inert bytes after
   the volatile reset was a non-replicator by construction (v22). The founder site is now
   topped up by default (`census_topup=1`); v23 recomputes v17-v22. v13-v16 still use the
   seed-limited verdict, so their strict counts are lower bounds wherever programs passed 48
   bytes.
7. Census (observer, not dynamics), resolved in 34839f4: the trial seeded the founder with
   its volatile offsets reset, so polite's counters so ([31]) and do ([33]) started equal. A
   copy-born child starts with the counter values its parent's loop copied (31 and 33 mod
   64). Keys whose counter reset does not take effect, such as a filled 36 or some
   substitutions at offsets 0-2 and 5, passed the census but copy off register when
   copy-born (v25 scratch checks). The census now also tries such a key from copy-born
   values (`census_born=1`, default) and counts it as `loose` when that trial fails; v27
   recomputes v18-v25. The born values are the reference's; a variant whose own children
   carry other counter values is still tried with them.

## Open proposals (none agreed)

- **Length-growth controls** (from v25; each changes one mechanism and needs agreement
  first). Done at the research channel's request: `ext_write=erase` against `fill` (v26),
  the copy-born census trial (34839f4, v27), refusing foreign writes into active sites
  (`ext_active=refuse`, v29: in-place additions gone, decline delayed, criterion 1 failed
  in all four runs) and copy errors on cross-site writes only (`mut_scope=cross`, v30:
  early `multi` children halved, mass shortage 50k-100k ticks later, criterion 1 failed
  in all four runs).
- **Per-op decay rates and size-dependent mobility** (requested 2026-11-17): sources, code
  observations and candidate designs are in
  [the decay and mobility note](../../docs/research/decay-and-mobility.md). The uniform
  whole-program form and block rotation are implemented as options (v14); per-op rates and
  size dependence are not.
- **Bond release to the actor**: an external write that breaks a bond releases `e_bond` at
  the writer's site instead of the byte's site, so clearing dead code pays the clearer.
- **Reclaiming ancestor**: a seeded replicator that clears its target before copying.
- **Split the own-site direction from INERT** (refines Cut 1 after v28; changes dynamics;
  not agreed). INERT is at once an empty slot that `fill` lets other sites write, the
  own-site direction, the value 0 and the operand that names offset 0 (Known issue 1). In
  v28, foreign fills of own-site direction bytes are 87.5-90.5% of entry-0 in-place strict
  losses but carry 13.5-14.4% of v24's D and 13-14% of the in-place length credit; to first
  order a split removes those and leaves the rest. Two encodings, each with new ancestor
  bytes:
  - *A: direction = `v % 5`, 0 = own site* (Cut 1 as first proposed). Every multiple of 5
    names the own site, so a non-inert self-pointer exists. All neighbor codes change, and
    `RND` names the own site in 51 of 255 draws. A value read of a non-inert own-site code
    is not 0, so polite's `JMP 30`, which reads the INERT at 30 as address 0, needs another
    layout, and the 0 it reads would stay INERT and fillable.
  - *B: a reserved zero code Z* (one non-inert value, e.g. 255). Every read decodes Z as it
    decodes INERT: own-site direction, value 0 (`JZ` skips, `JMP` goes to 0), operand naming
    offset 0, no edge for `WALL` and `UNWALL`. Every write rule and every count of matter
    treats Z as non-inert: it holds a monomer, decays, and `fill` refuses a foreign write to
    it. Polite with Z at 30, 34, 36, 38 and 40 is otherwise unchanged, and `JMP 30` still
    goes to 0. Costs: 5 more monomers per copy (z 40 to 45), 5 more bytes open to copy
    error, and under whole decay a 12.5% higher hazard. Open: what `INC` and `DEC` give on
    Z; whether copy error and `RND` may produce Z (1 in 255); what an ip on Z does (INERT
    there ends the activation by wick); the modulo bias of the 254 remaining codes.
  - B separates the empty slot from every read role, for the bytes that hold Z; A separates
    the direction only. The v28 counterfactual corresponds to B with Z at every own-site
    direction byte a key reads.
- **Cut 2, re-ignition**: deprioritized after v9; `e_ignite` 256 would cut re-ignitions ~10x.
- **Cut 3, costs**: charge the bond barrier only for cross-edge breaks.

Physics and ISA changes are discussed and agreed before they are implemented.
