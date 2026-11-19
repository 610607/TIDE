# Small-grid checks

Single-purpose programs used while writing the v14-v28 entries in
[`../README.md`](../README.md), where they are called scratch checks. Most seed polite (or a
variant) alone in a small world with mutation and decay off, or run the census trial of
`apps/ps_census.hpp` on chosen keys, and print a few lines. They are built with the rest of
the project (`PHYSUB_CHECKS`, on by default; executables in `build/checks/`) and are not run
by `ctest`.

They were written against the sources of their day and now build against the current ones.
Two changes since then were needed: three read-only copy-observer accessors in `World`
(`copy_target`, `copy_was_cut`, `body`) that the `chk_cut_*` programs used from a local copy
of the sources, and an unnamed `argc` in those programs. Census defaults changed after some
of them were written (founder top-up at b4b4ea1, copy-born trial at 34839f4), so a check
from before a change can print other verdicts now. To reproduce a quoted figure, build at
the source revision in the table.

| Check | Entry | Written (UTC) | Source revision | Checks | Scratch name |
| --- | --- | --- | --- | --- | --- |
| `chk_cut` | v14 | 11-17 02:01 | 5579cb7 | First-copy cut probability and duration of polite alone at a given `p_rot` (`chk_cut P_ROT SEEDS`); `apps/ps_copycut` replaced it | `cut/cut.cpp` |
| `chk_cut_pop` | v14 | 11-17 02:02 | 5579cb7 | Copy durations and cut share in a populated 48x48 run, by content identity (`chk_cut_pop P_ROT SEED`) | `cut/pop.cpp` |
| `chk_cut_short` | v14 | 11-17 02:02 | 5579cb7 | The first copies shorter than 50 ticks in such a run (`chk_cut_short P_ROT SEED`) | `cut/short.cpp` |
| `chk_trial` | v18 | 11-17 06:06 | 84092a3 | Census verdicts of polite and copier, of polite with 30, 34, 36, 38 or 40 filled, and with 26 knocked out | `chk_trial.cpp` |
| `chk_trial_fill` | v19 | 11-17 09:06 | 2280ebf | Census verdicts of polite with one reference-inert or tail offset filled, every value (v19: "all 255 values; a scratch check") | `dbg/trial_fill.cpp` |
| `chk_tail` | v22 | 11-17 11:37 | 76ef87b | Census status of polite with one INERT offset filled, `inert_operand=fail`; `MASS0` in the environment sets `mass0` (v22: "scratch check with `mass0` 48") | `tailtest/tail.cpp` |
| `chk_tail_extra` | v22 | 11-17 11:39 | 76ef87b | Census status of polite with k tail bytes filled (v22: 8 filled strict, 9 `other` without top-up) | `tailtest/extra.cpp` |
| `chk_shift` | v25 | 11-18 03:24 | c3eae86 | Whether keys with 36 or 38 filled copy in register from copy-born counters (31 = 223, 33 = 225) | `shiftchk/shiftchk.cpp` |
| `chk_probe` | v25 | 11-18 03:30 | 3227e87 | A writer whose do counter starts at V next to a live polite: does it fill the neighbor's INERT offsets | `shiftchk/probechk.cpp` |
| `chk_born` | v25 | 11-18 04:50 | 3227e87 | Single-byte variants at offsets 0-5, 34, 35, 42, 36, 38: census strict against strict from copy-born counters (v25: 120 such keys) | `shiftchk/bornchk.cpp` |
| `chk_wall` | v26 | 11-18 04:53 | 3227e87 | Polite with 34 filled reading K through W wall units, from copy-born counters (walled read of K) | `shiftchk/wallchk.cpp` |
| `chk_fillscan` | v28 | 11-18 16:18 | 14dea48 | Polite alone with one own-site direction or tail byte filled, every value 1-255, census from reset and copy-born counters, both operand rules | `fillscan/fillscan.cpp` |

"Source revision" is the last commit of `src/` or `apps/` before the check was written; the
working tree may have held uncommitted changes then. Scratch names are the paths the checks
had in the session's scratch directory.
