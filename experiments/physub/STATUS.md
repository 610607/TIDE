# physub status, v13-v30

A summary of the executed runs v13-v30, written at revision 62365c2 (2026-11-19). It adds no
runs. Every number comes from the README's
[Findings from executed runs](README.md#findings-from-executed-runs) unless marked
*[computed here]*; those were computed for this summary from existing outputs in `runs/`
with the formula given. physub is an exploratory substrate, not the TIDE kernel. Its rules
are provisional configuration, and nothing here is an agreed requirement.

Claim types follow `AGENTS.md`: *run* (executed run), *code* (code inspection), *inference*.
The README entry of each version holds the tables, checks and limits.

## Baseline since v17

- 96x96 sites, `site_len` 64, `mass0` 48, ancestor `polite` (46 bytes, 40 non-inert).
- Whole-program decay (form M, `hydro_whole=1`), `p_hydro` 1.95e-6 per non-inert byte.
- Copy error `p_mut` 0.003; `ext_write=fill` (a neighbor may only fill INERT bytes).
- `inert_operand` `zero` or `fail`; 500k ticks; seeds 1-2; census every 50k.
- **Strict** means a strict replicator in the census trial. The trial changed twice:
  - v13-v16: seed-limited, two-carrier verdict. Not recomputed; counts are lower bounds
    wherever keys passed 48 bytes.
  - From b4b4ea1 (v23 recomputes v17-v22): the founder is topped up to the key's size.
  - From 34839f4 (v27 recomputes v18-v25): a key must also replicate from the counter values
    a copy-born child carries (`census_born=1`); otherwise it is `loose`.

## Versions

Revisions and job lists (`scripts/jobs/`) are in each README entry. Ranges cover the runs of
a version. "Revised" names the later version that changed a count or a reading.

| version | change (one mechanism or measurement) | key numbers | conclusion at the time | revised |
| --- | --- | --- | --- | --- |
| v13 | `dead_quiet`: `p_dead` only on inactive sites no write reached for N ticks | with `dead_quiet=64`, 2.8-3.5k replicators at 30k, then about 10x fewer by 100k; without `p_dead` 33-39 at 100k; 66-83% of active sites are copy-born non-replicators | protects copies under construction, raises late replicators 2-10x, does not stop the decline | seed-limited counts, not recomputed |
| v14 | whole-program decay (form M); block rotation `p_rot` | under M 5.4-5.5k replicators at 100k, 12-16% below the peak, against about 80x fewer under per-byte decay; rotation from 1e-3 cuts a third or more of copies, 1e-2 goes extinct | M almost removes the decline to 100k; rotation without binding does not help | v17: the decline returns after 100k; v19: writes still change live programs |
| v15 | M's two effects split (live vs inactive sites) | peak to 100k: 80x (per-byte), 9x (whole decay of inactive only), 1.6x (live only), 1.2x (M) | ending in-place damage of live programs is the main effect | v17, v19 as above |
| v16 | per-op decay rates, 30:1, four fast op classes | replicators 5.1-5.7k against 5.4-5.5k; data-byte fast share 0.16-1.04 points below control at 100k; opcodes unchanged | little effect to 100k; a weak late shift in data bytes | v17 extends it |
| v17 | v16 to 500k | data-byte shift 2.8 points at 500k (1.5-4.3); M control: replicators 6.4-6.6k at 50k to 3.0-3.3k at 500k, exact births 39-43% to 6-7% | the decline returns under M, about 2-fold; selection reaches data bytes only | v23 (the seed-limited census showed 6-9x); v27 strict counts 3-7% lower |
| v18 | copy fidelity per genotype (`fidelity=5000`, `ps_scan`) | leading genotypes alone give 91-94% strict first copies throughout; in the run, children of strict parents are strict in 83-85% at 50k and 64-69% at 500k (v27); losses rise as `env`, `gap`, `multi` | intrinsic fidelity does not fall; the in-run loss is environmental | v23, v27 (`multi` smaller) |
| v19 | activation fates (`fate=1`) | in-place losses carry the decline; after 150k a neighbor's fill of 30 is 42-45% of in-place losses (v27: 25-28%, and a write at 36 39-43%); the site itself 44-47% (v27: 24-31%) | in-place change by own and neighbor writes carries the decline under M; both routes use INERT's double meaning | v27 reorders the routes; v28 confirms them by role |
| v20 | `inert_operand=fail` | offset-0 self-losses fall 92-100% (v27); without copy error the decline is gone to 500k; with copy error strict at 500k 2,885 / 2,925 against 2,767 / 3,048 under `zero` (v27) | the operand split removes the self-overwrite; two seeds do not separate the rules with copy error | v27: foreign fills of 36-40 no longer rise |
| v21 | trace of foreign writers and off-entry igniters | foreign losses come from the `MOV` at 15 (79-85%, v27) and fill an inert pointer direction (98-99%, v27); off-entry ignitions by `other` sites through filled 36/38; free monomers 61-66k at 50k, 19-24k at 200k | the own-site direction role of INERT carries the foreign losses; off-entry visits end by wick | v27 shares |
| v22 | census seeding limit found | the seed-limited census missed keys past 48 bytes: 626-976 strict at 500k against 2,984-3,280 | the decline is about 2-fold, not 6-10-fold | fixed in b4b4ea1; v27: 6.2-6.5k to 2.8-3.0k |
| v23 | v17-v22 recomputed with the topped-up census | dynamics unchanged | readings of v17-v22 rewritten | v27 |
| v24 | loss-route ledger (`route=1`) | D 0.324-0.393 per strict entry-0 site per 5k ticks (v27); whole decay 23.5-25%, `env` 23-26%, `multi` 14-15%, fewer re-ignitions at 0 10-14%, fills of 30 in place 4.6-5.1%; `gap` at least 6-10% (v24) | the largest terms are whole decay of longer keys and foreign differences in children | v27 numbers; v28 |
| v25 | length ledger (`length=1`) | mean z 40 to 52.0-53.8 at 500k (v27), 40.7-42.5 without copy error; foreign writes add the bytes, 75-77% in place (v27), on the tail 46-63 and pointer directions; long keys copy more but lose more | length growth is a by-product of the one-way write rule, not drift | v26 confirms the cause; v27 halves the in-place credit |
| v26 | `ext_write=erase` against `fill` | mean z +1.6-2.5 against +12.0-13.8 by 500k; late strict 4,122-4,490 against 2,972-3,170; no mass shortage after the first window; more in-place losses through erasure | the one-way rule drives length growth | criterion 1 *[computed here]*: 1 of 4 runs passes |
| v27 | copy-born census trial (`census_born=1`); v18-v25 recomputed | the second trial removes 3.0-3.9% of strict sites at 50k and 5.4-7.3% at 500k; a filled 36 now ends strict status | the ranking of in-place routes changes (36 first, 30 second); the other readings stand | - |
| v28 | INERT role ledger (`role=1`) with a direction-split counterfactual | foreign fills of own-site direction bytes are 87.5-90.5% of entry-0 in-place strict losses and 13.5-14.4% of D; in-place length is 85% fills of empty slots, 13-14% direction fills | a direction split would remove those losses, not the main terms of D or the source of length | - |
| v29 | `ext_active=refuse`: no foreign write into an active site | criterion 1 fails 4 of 4 (ratio 0.555-0.571); in-place routes gone; mass shortage starts at 300-350k instead of 150-250k; mean z 48.8-50.1 at 500k | the decline is delayed, not stopped | - |
| v30 | `mut_scope=cross`: copy error only on `MOV`s into a neighbor | criterion 1 fails 4 of 4 (0.444-0.469); `multi` halved at 50k, 7-14% fewer over the run; mass shortage 50k-100k ticks later; strict at 500k 1-7% above v27 | the counter-reset route is minor; late off-register copying comes from other routes | - |

## Conclusions that hold now

These hold for this substrate and these settings, mostly on two seeds per rule.

1. **Per-byte decay of live programs** (v13-v15, run; mechanism inference). Replicators lose
   replication in place and keep their sites, so non-replicators fill the space. Faster
   reclamation of inactive sites does not reach them.
2. **Form M** (v14, v15, run). Whole-program decay removes most of that to 100k, mainly by
   ending in-place damage of live programs.
3. **The decline under M with copy error is about 2-fold** (v17, v22, v27, run). Strict
   sites fall from 6.2-6.5k at 50k to 2.8-3.0k at 500k. Without copy error they stay at
   7.6-8.6k at 500k (from 8.7k).
4. **Intrinsic fidelity does not fall** (v18, v27, run). Leading genotypes alone keep
   91-94% strict first copies. The in-run loss comes from foreign differences in children
   (`env`), `multi` and `gap` copies.
5. **What the decline is made of** (v24, v27, v28; accounting, not a counterfactual). D is
   0.32-0.39 per strict entry-0 site per 5k ticks:
   - whole decay of longer keys, 23.5-25%;
   - `env` children, 23-26%;
   - `multi` children, 14-15%;
   - fewer re-ignitions at offset 0, 10-14%;
   - in-place losses, 10.6-14.2%. The foreign fills of own-site direction bytes among them
     carry 13.5-14.4%, more than the total in three runs, because the site's own losses
     fall from early to late (v28);
   - `gap` children (mass shortage), at least 6-10% (v24).
6. **Length grows by a write-rule by-product** (v25, v26, v28; run and code). Keys gain
   12-14 bytes by 500k with copy error. The bytes come from foreign writes, 75-77% in
   place, 85% of those into empty slots, mostly on the non-executed tail. Point errors
   cannot change length (code). With erasure allowed the gain is about 2 bytes.
7. **Long keys gain nothing** (v25, run). The decay hazard follows length, and per-site
   balance falls with length.
8. **Mass shortage and the steepest fall coincide** (v24, v29, v30; run, causality
   inference). Writes refused for want of a free monomer jump when free monomers are down
   to about 18-26k. The jump came at 150k-250k in v27, 300k-350k in v29 and 250k-350k in
   v30, each time in the window of the steepest fall (for v30 *[computed here]* from the
   v30 tables).
9. **Two controls delay but do not stop the decline** (v29, v30, run). Refusing writes
   into active sites and removing own-site copy errors both fail criterion 1 in all runs.
10. **The census needed two fixes** (v22, v27; run and code). Verdicts since v27 test a
    key from reset and from copy-born counters; v13-v16 counts are not recomputed.

## Criterion 1

Set by the research channel with v29. With copy error, strict sites (copy-born census) do
not fall from 350k to 500k, and strict at 500k / strict at 50k ≥ 0.8. The counts are the
`strict=` field of the `# census` lines at 50k, 350k and 500k.

| version | rule | run | strict 350k → 500k | 500k / 50k | result |
| --- | --- | --- | --- | --- | --- |
| v27 | baseline (`fill`) | `zero` s1 | 3,052 → 2,767 (−285) | 0.441 | fail |
| v27 | baseline (`fill`) | `zero` s2 | 3,389 → 3,048 (−341) | 0.493 | fail |
| v27 | baseline (`fill`) | `fail` s1 | 3,069 → 2,885 (−184) | 0.447 | fail |
| v27 | baseline (`fill`) | `fail` s2 | 3,196 → 2,925 (−271) | 0.460 | fail |
| v29 | `ext_active=refuse` | `zero` s1 | 4,512 → 3,777 (−735) | 0.557 | fail |
| v29 | `ext_active=refuse` | `zero` s2 | 4,331 → 3,696 (−635) | 0.560 | fail |
| v29 | `ext_active=refuse` | `fail` s1 | 4,200 → 3,792 (−408) | 0.555 | fail |
| v29 | `ext_active=refuse` | `fail` s2 | 4,357 → 3,849 (−508) | 0.571 | fail |
| v30 | `mut_scope=cross` | `zero` s1 | 3,208 → 2,951 (−257) | 0.449 | fail |
| v30 | `mut_scope=cross` | `zero` s2 | 3,369 → 3,083 (−286) | 0.469 | fail |
| v30 | `mut_scope=cross` | `fail` s1 | 3,166 → 2,963 (−203) | 0.444 | fail |
| v30 | `mut_scope=cross` | `fail` s2 | 3,527 → 3,081 (−446) | 0.460 | fail |

Reference rows *[computed here]* from existing outputs, same formula:

| version | rule | run | strict 350k → 500k | 500k / 50k | result |
| --- | --- | --- | --- | --- | --- |
| v26 | `ext_write=erase` | `zero` s1 | 4,259 → 4,335 (+76) | 0.752 | fail (ratio) |
| v26 | `ext_write=erase` | `zero` s2 | 4,443 → 4,368 (−75) | 0.786 | fail |
| v26 | `ext_write=erase` | `fail` s1 | 4,013 → 4,072 (+59) | 0.879 | pass |
| v26 | `ext_write=erase` | `fail` s2 | 4,268 → 4,104 (−164) | 0.918 | fail (fall) |
| v27 | no copy error | `zero` s1 | 8,386 → 8,031 (−355) | 0.926 | fail (fall) |
| v27 | no copy error | `zero` s2 | 8,299 → 7,596 (−703) | 0.878 | fail (fall) |
| v27 | no copy error | `fail` s1 | 8,612 → 8,574 (−38) | 0.984 | fail (fall) |
| v27 | no copy error | `fail` s2 | 8,657 → 8,603 (−54) | 0.989 | fail (fall) |

- v26 is the only rule with a run that passes. Its 50k counts are low (4,470-5,766 against
  6,180-6,453 under `fill`), because erasure raises early in-place losses (v26), so the
  ratio is taken against a depressed start.
- The runs without copy error are outside the criterion. They show that its first part, a
  strict non-decrease between two checkpoints, fails on falls of 0.4-0.6% (`fail`), within
  the seed-to-seed spread of up to 10% at a checkpoint (v20).
- The per-op decay tables (v27 `t2_s1`, `t3_s1`) give 0.475 and 0.461 and fall too.

## Not yet attributed

- **Late off-register copying.** At 500k, 10-11% of copies by strict entry-0 parents are off
  register (v27, v30), and parents off register with neither 36 nor 38 filled make 78-80% of
  `multi` children. v30 shows the counter-reset copy error is a minor route (about 0.6% of
  copies, code inspection and run). Candidates: a walled read of K through a filled 34
  (v25 scratch check) and other first-cycle reset failures; their shares were not measured.
- **Why filled 34 spreads.** It rises from 6-10% of strict sites at 50k to 71-93% at 500k,
  mostly by inheritance, and also without copy error (93% in `zero_nomut_s1`). Per-site
  rates do not favor it (v25).
- **Mass shortage and length.** Where length grows more slowly (v29, v30, v26) the shortage
  comes later or not at all, but no run changed matter alone. Where the monomers go is
  known (v24: inactive sites 54-58%, `other` sites 33-37%, walls 8-9%); who is refused is
  not recorded (v21).
- **`env` children.** Which writers write into children under construction, and why that
  rises 3-fold, is not traced beyond offset 30 (v24).
- **Fewer re-ignitions at offset 0** (10-14% of D): not attributed (v24).
- **What erasure does** (v26): removing bytes, returning monomers and undoing fills are not
  separated.
- **A direction split in the dynamics** (v28): only a first-order counterfactual exists.
- **Beyond 500k**: whether v29 or v30 level off is not known.
- Two seeds per rule throughout; v13-v16 counts are seed-limited.

## Possible next steps (proposals, none agreed)

Each changes one thing and needs agreement before it is run.

- **Measure the off-register routes** (observer only): record per copy whether a reset was
  skipped, read through a wall or a filled 34, and in which cycle of the parent.
- **Test criterion 1 on `erase`** with more seeds, since it is the only rule with a passing
  run; or split erasure's effects (removal without monomer return) as separate rules.
- **Matter control**: raise `mass0` alone to test whether the shortage drives the late
  fall.
- **Longer runs** of v29 and v30 (for example 1M ticks) to see whether they level off.
- **Criterion robustness**: more seeds per rule, and a form that tolerates noise, such as
  the least-squares slope over 350k-500k with a confidence bound.
- **Split the own-site direction from INERT** (README Open proposals, encodings A and B).
- **Follow filled-34 lineages** to find why they spread.

## Reproducing

- Each version's job list in `scripts/jobs/` holds the seeds and settings, and its README
  entry the revision; `scripts/run_jobs.sh` runs a list. The outputs are in `runs/`.
- Criterion 1 follows from the `# census` lines alone, as above.
- The README's derived tables (ledgers, decompositions, shares) were computed with the
  scripts in `scripts/analysis/`; its README maps each script to versions, and `regen.sh`
  redoes the v23 and v27 recomputes. Definitions are in the README entries and in the
  observer comments in `apps/ps_probe.cpp`. The small-grid checks are in `checks/`.
