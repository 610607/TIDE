# v31 paired matter control

Does increasing initial monomer supply reduce cross-site copy-write refusals, increase production of strict copy-born children, and delay the decline in strict sites? Compare 48 and 64 initial monomers per site under each v27 operand rule (`zero`, `fail`) and seeds 1 and 2. The initial total increases by 147,456 monomers on the 96 × 96 lattice. The census uses 48 in both arms, with founder top-up and the copy-born trial enabled. Both arms run for 500,000 ticks or until extinction, with measurements every 50,000 ticks. See the [eight jobs](../../scripts/jobs/v31_mass_control.txt).

## Results

All eight populations remained active through 500,000 ticks. Each of the four mass-48 replays matched v27 at all ten checkpoints for active and strict sites, the birth-status counts and total writes refused for lack of mass. Their terminal records matched v27. At all 80 checkpoints the fate balance closed and the exposure counts reconciled to the existing birth ledger.

**Run observations.** At mass 64, all four runs recorded zero writes refused for lack of material, including both own-site and cross-site writes. In the paired controls, 225,030–458,009 cross-site writes were refused per run. At mass 64 the total number of strict copy-born children rose by 4.5–10.7%. In the zero/seed-2 pair the total number of copy births fell while the number of strict children rose. At 500k each rich arm carried 325–748 more strict sites than its control. All four rich arms lost strict sites from 350k to 500k, and retained 54.0–55.8% of their 50k count. All eight runs failed criterion 1.

**Timing.** The largest absolute drop between consecutive checkpoints was smaller at mass 64 in every pair. It occurred earlier in three pairs and in the same interval in the fourth. Strict counts had already fallen in every rich arm by 100k. The prediction that the steepest decline would be delayed received no support in these runs.

**Inference.** Extra initial material improved strict offspring production and late persistence under these settings. Scarcity aggravates the loss, and the decline persists in a world with zero mass-refused writes. Changing initial material changes the entire subsequent population history. The exposed-parent counts do not isolate the effect of an individual failed write. Two seeds per operand rule limit generalization.

| Rule and seed | Main stock | Active at end | Strict at 50k | Strict at 350k | Strict at 500k | 500k / 50k | Largest 50k fall after 50k | Criterion 1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| zero 1 | 48 | 4,945 | 6269 | 3052 | 2767 | 0.441 | 200k–250k (−851) | fail |
| zero 1 | 64 | 5,721 | 6346 | 3593 | 3457 | 0.545 | 50k–100k (−707) | fail |
| zero 2 | 48 | 5,163 | 6180 | 3389 | 3048 | 0.493 | 150k–200k (−909) | fail |
| zero 2 | 64 | 5,550 | 6251 | 3429 | 3373 | 0.540 | 100k–150k (−649) | fail |
| fail 1 | 48 | 4,998 | 6453 | 3069 | 2885 | 0.447 | 150k–200k (−1,233) | fail |
| fail 1 | 64 | 5,846 | 6516 | 3710 | 3633 | 0.558 | 50k–100k (−892) | fail |
| fail 2 | 48 | 4,930 | 6354 | 3196 | 2925 | 0.460 | 150k–200k (−1,067) | fail |
| fail 2 | 64 | 5,705 | 6367 | 3968 | 3499 | 0.550 | 150k–200k (−733) | fail |

Counts below span complete checkpoint windows. The strict share uses all classified copy births as its denominator.

| Rule and seed | Main stock | Cross-site refusals | Activations first refused | Strict children / all copies | Strict share | Strict children / copies after a parental refusal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| zero 1 | 48 | 259,348 | 60,402 | 159,182 / 270,821 | 58.8% | 48,878 / 92,820 |
| zero 1 | 64 | 0 | 0 | 173,258 / 279,510 | 62.0% | 0 / 0 |
| zero 2 | 48 | 225,030 | 59,007 | 163,714 / 282,841 | 57.9% | 47,191 / 89,324 |
| zero 2 | 64 | 0 | 0 | 171,111 / 271,486 | 63.0% | 0 / 0 |
| fail 1 | 48 | 440,321 | 79,969 | 158,082 / 277,415 | 57.0% | 64,367 / 124,320 |
| fail 1 | 64 | 0 | 0 | 174,922 / 277,421 | 63.1% | 0 / 0 |
| fail 2 | 48 | 458,009 | 79,781 | 162,040 / 276,983 | 58.5% | 67,150 / 120,933 |
| fail 2 | 64 | 0 | 0 | 174,897 / 277,334 | 63.1% | 0 / 0 |

### Where strict sites went from 250k to 500k

The second half consists of the five 50,000-tick intervals after the 250k census. The unchanged stability criterion uses the narrower 350k–500k interval. The [window ledger](analysis/strict-site-windows.tsv) gives the opening and closing censuses and every flow for both stocks, both rules and both seeds. All 40 second-half balances close exactly.

A strict site can enter the count through a copy birth, a re-ignition, a self-ignition, or a change of strict status during execution. It can leave when execution ends or when its running program loses strict status. The observer counts whole decay when all bytes are inert at the end of an activation. It counts other ends as `wick`, when execution reaches an inert instruction in these runs. Recorded starvation and self-ignitions were zero throughout. A re-ignition starts execution on existing code. The observer separates it from a copy birth by the fraction of non-inert bytes written from the parent's site since the previous ignition. In-place gains include sites first recognized as strict at a census. Such gains carry checkpoint timing. Counts refer to events, so one site can appear repeatedly. [Fate observer](../../apps/ps_probe.cpp) and [birth classification](../../apps/ps_census.hpp).

| Rule, seed | Stock | Strict copies | Strict re-ignitions | In-place gains | Whole decay | Wick | In-place losses | Change in strict sites |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| zero, 1 | 48 | 74,257 | 36,015 | 4,014 | 77,169 | 18,982 | 19,061 | -926 |
| zero, 1 | 64 | 85,971 | 57,214 | 6,767 | 93,218 | 33,410 | 24,167 | -843 |
| zero, 2 | 48 | 76,222 | 43,098 | 2,005 | 79,612 | 25,232 | 17,053 | -572 |
| zero, 2 | 64 | 82,836 | 42,271 | 3,852 | 89,080 | 19,605 | 20,973 | -699 |
| fail, 1 | 48 | 74,289 | 82,981 | 860 | 77,084 | 66,323 | 15,375 | -652 |
| fail, 1 | 64 | 87,787 | 99,801 | 3,851 | 96,584 | 75,728 | 19,721 | -594 |
| fail, 2 | 48 | 76,247 | 76,007 | 2,052 | 78,254 | 58,989 | 17,602 | -539 |
| fail, 2 | 64 | 87,132 | 100,482 | 1,219 | 96,930 | 74,743 | 17,679 | -519 |

**Whole decay was the largest individual outflow in each of the 20 high-stock windows.** Across the five windows, its share of gross losses ranged from 50.3% to 68.7% across the four runs. In absolute numbers each high-stock run produced fewer strict copies than the number of strict activations ending by whole decay. Re-ignitions supplied a substantial additional inflow.

Counting all strict ignitions and subtracting both kinds of execution end gives the net activation column below. Subtracting in-place losses from in-place gains gives the next column. Together they sum to the observed census change.

| Rule, seed | Net activations at 64 | Net in-place change at 64 | Site change at 64 | Site change at 48 |
| --- | ---: | ---: | ---: | ---: |
| zero, 1 | +16,557 | -17,400 | -843 | -926 |
| zero, 2 | +16,422 | -17,121 | -699 | -572 |
| fail, 1 | +15,276 | -15,870 | -594 | -652 |
| fail, 2 | +15,941 | -16,460 | -519 | -539 |

Net activations were positive and net in-place change was negative in each high-stock window. The in-place deficit exceeded the activation surplus in 13 of 20 windows. The other seven gained strict sites. Across five windows the deficit exceeded the surplus in all four runs. The same two flows had opposing signs in all four controls. At 250k the high-stock advantage already ranged from 452 to 690 strict sites. From that point the paired advantage changed by +83, −127, +58 and +20 sites in table order.

**Interpretation.** With ample material, reproduction and re-ignition sustained enough strict activations to cover execution ends in aggregate. Changes in the status of programs still running accounted for the remaining deficit. Between 61.1% and 75.5% of gross in-place losses in the high-stock runs included a change attributed to an external writer (all writer classes except self, divided by gross in-place losses). The complementary share was attributed to the site's own writes. The ledger gives the observed balance. It cannot predict the result of blocking a writer, since births, ends and status gains could also change.

To regenerate the window ledger, run `python3 scripts/analysis/v31_fates.py runs/v31` from `experiments/physub`. Sum the five rows per seed, rule and stock to reproduce these tables. This analysis uses the archived outputs of the eight original v31 runs.

## Measurements

- Each `# massfate` line covers the entire preceding 50,000-tick interval. `no_mass` counts all writes refused for lack of a monomer. `cross_refused` counts the subset of those events where a MOV targets a neighbor. `newly_refused` counts activations encountering their first such refusal.
- At a copy birth, `copies_after_refusal` counts children whose parent had at least one such refusal since its own ignition. `strict_after_refusal` counts children among them that pass the fixed census. `copies_clear` and `strict_clear` cover the remaining copy births. A first refusal stays with the activation across observation windows and resets at the next ignition. A refused write can target a different site from the eventual child. These cohorts describe exposure histories. Their difference in child success cannot by itself establish a causal effect of one refused write.
- Compare total refusals and strict copy births over the full run and by window, including exact counts and the share of all copy births that are strict. Locate the largest absolute decrease in strict sites between consecutive census checkpoints starting at 50k. Report ties and the previous stability criterion (500k/50k at least 0.8 and 500k at least 350k). Report every seed separately. Refusals, strict births and persistence can respond differently to extra material.
- The mass-48 runs replay the archived [v27 controls](../v27/) to obtain the new refusal histories. Compare the census series, total lack-of-mass refusals and strict copy births against v27 at every checkpoint. The code and both arms use identical physical transitions. The only intervention within a seed/operand pair is the initial stock.

## Replay

From `experiments/physub`, build as in the [experiment README](../../README.md), then run the following commands. Use a fresh output directory to preserve previous results.

```sh
scripts/run_jobs.sh scripts/jobs/v31_mass_control.txt runs/v31-replay 4 build
python3 scripts/analysis/v31_mass.py runs/v31-replay runs/v27
```

The simulator used the source tree at `ede3fee57e46d04432cc2d79bc84bf16e6c37eb0` with the three observer-source files below. SHA-256 fingerprints identify the exact working-copy version. The local build used Apple Clang 21.0.0, C++20, `-O3 -flto -DNDEBUG -Wall -Wextra -Werror`. The reference test emitted `6fb0e06a3160cc24`.

| File | SHA-256 |
| --- | --- |
| `apps/ps_probe.cpp` | `a4efaa859c29b4f29883ed8693fb2865dff48106f6a7a3d8969ca4e59fa7cd45` |
| `src/ps_core.hpp` | `753cbd6c6a86b72aa74e67892a9e86fc41c7af128342ef5c236644507884fd7e` |
| `src/ps_resolve.cpp` | `989803970624dee7d25a2a07261758d4cc20859dde9e3bf78cc9f4ad2f1b9f9d` |

## Instrument checks

On an 8 × 8 lattice, an explicit census stock of 48 produced the same baseline output as inheriting 48, apart from the new observer lines. With main stock 64, changing the assay to zero stock without founder top-up removed all strict census calls while preserving the main-world final line. Both checks used seed 1, 3,000 ticks, 1,000-tick checkpoints, whole decay with zero rate, fill-only writes, and the census, fate, trace and route observers.

A low-stock check used the same geometry and seed, main stock 40, census stock 48, 25,000 ticks, 5,000-tick checkpoints, copy error 0.003 and whole-program decay rate 0.000002. The run ended with 36 active sites. Its five intervals recorded 158, 767, 821, 125 and 189 cross-site refusals. The corresponding exposed-parent cohorts produced 2/9, 4/31, 8/28, 5/12 and 6/14 strict children/copy births. All pre-existing output lines matched the same run with the observer off.
