# Analysis scripts

Python 3 scripts (standard library only) that computed the tables and figures in the v13-v30
entries of [`../../README.md`](../../README.md) and in [`../../STATUS.md`](../../STATUS.md).
They read `ps_probe` outputs under `runs/` and print text or Markdown to stdout. Run them
from `experiments/physub/`, for example:

```sh
python3 scripts/analysis/v29_crit.py runs/v30/{zero,fail}_m195_s{1,2}.tsv
scripts/analysis/regen.sh v27 /tmp/v27_out
```

They were written during the runs and kept as they were used, apart from comments and
paths: a script that imports another one finds it in this directory. Most take the
version's run directory and expect that version's run names (`m195_s1`, `zero_s1`, ...);
`regen.sh` links the recompute runs under those names. "Used in" names the README entries
whose numbers a script produced; v23 and v27 recomputed earlier versions' tables.

| Script | Used in | Computes | Input |
| --- | --- | --- | --- |
| `summarize.py` | v13 | Key columns at chosen ticks and the final lines | `runs/v13 [ticks]` |
| `census.py` | v13 | Census at chosen ticks: active, replicators, prefix replicators, non-replicators (copy, re-ignition), ages | `runs/v13 20000,40000,60000,100000` |
| `table.py` | v13 | Table per run: end, replicator peak, census at 100k | `runs/v13` |
| `chk.py` | v14 | Mechanism check: births, exact births, copies started, cut, born | `runs/v14_rotation 'chk_*.tsv'` |
| `v14.py` | v14, v15 | Census at the last interval plus physics counters | `runs/v14_rotation 'rot*.tsv'`; `runs/v15` |
| `v16.py` | v16 | Identity checks, census table, class shares and substitutions, treatment against m195 | `runs/v16 runs/v15` |
| `v17.py` | v17 | Time series every 50k of data/opcode fast share, hazard and census | `runs/v17` |
| `v17_md.py` | v23 (v17 tables) | v17 tables and bullet figures | `runs/v17`; v23 view |
| `v17_m195.py` | v23 (v17 tables) | Uniform form M table | `runs/v17`; v23 view |
| `v17_extra.py` | v23 (v17 figures) | Opcode shift mean, control drift, polite intact at 500k, copy births | `runs/v17`; v23 view |
| `v18.py` | v18, v23, v27 | Fidelity summary; with a scan file, isolated scans; `len` for lengths | `runs/v18 runs/v18/scan_polite.tsv` |
| `v18_md.py` | v18, v23, v27 | Tables T1, T2, T4, T5 | `runs/v18` |
| `v18_extra.py` | v23, v27 | Bullet figures and the no-copy-error table | `runs/v18` |
| `v18_bal.py` | v23, v27 | Balance estimate per 50k interval | `runs/v18 m195_s1 m195_s2 t2_s1 t3_s1` |
| `v18_t3.py` | v23, v27 | T3 (top genotypes in the run and alone) and m groups | `runs/v18/scan_polite.tsv 37,38-39,40-42,43-45` |
| `v19.py` | v19, v23, v27 | Activation fates and in-place losses | `runs/v19 [run ...]` |
| `v19_md.py` | v19, v23, v27 | v19 tables | `runs/v19` |
| `v19_rates.py` | v23 | Rates per mean active count (wick plus net in-place loss, decay, out) | output of `v19.py` |
| `selfoff.py` | v23, v27 | Self-written in-place losses that change offset 0; foreign offsets | `runs/v19/*.tsv` |
| `idcheck.sh` | v19 | v19 outputs without fate lines equal v18's | none |
| `v20.py` | v20, v23, v27 | v20 (`inert_operand=fail`) against v19 | `runs/v19 runs/v20` |
| `v20_md.py` | v23, v27 | v20 tables and bullet figures | `runs/v19 runs/v20` |
| `v21.py` | v21, v23, v27 | Trace lines: foreign writers, off-entry igniters, matter holders | `runs/v21` |
| `v21_table.py` | v21, v23, v27 | Per window: foreign writes, ignitions off entry, ends by start offset | `runs/v21/*.tsv` |
| `v21_table2.py` | v23 | `v21_table.py` plus raw counts | `runs/v21/*.tsv` |
| `entry_emu.py` | v21 | Emulates polite's own-site steps when entered off offset 0 (code inspection; no run data) | none |
| `v22.py` | v22, v23, v27 | Census seeding limit per checkpoint | `runs/v22` |
| `v22_md.py` | v22 | v22 tables as first recorded (seed-limited census, c207f47); replaced by `v22_md2.py` | `runs/v22` |
| `v22_md2.py` | v23, v27 | v22 tables under the topped-up census | `runs/v22` |
| `routes_ledger.py` | v24 | Strict ledger per 50k from v23 fate, trace and fidcopy lines; preceded the route observer | `runs/v23/*_m195_s1.tsv` |
| `v24_routes.py` | v24, v27 | Loss-route ledger per 50k window | `runs/v24/*.tsv` |
| `v24_decomp.py` | v24, v27, v29, v30 | Per-site rate decomposition D (`EARLY`, `LATE` in the environment) | `runs/v24/*.tsv` |
| `v24_extra.py` | v24, v27 | Extra figures: offset-30 children, late shares, entry-0 counts | `runs/v24` |
| `v24_matter.py` | v24, v27 | Matter table and where monomers went | `runs/v24` |
| `v24_md.py` | v24, v27 | v24 tables | `runs/v24` |
| `v25_len.py` | v25 | Loader for `# length` lines; imported by later scripts | `runs/v25/*.tsv` |
| `v25_an.py` | v25, v27 | Length ledger analysis | `runs/v25` |
| `v25_md.py` | v25, v26, v27 | v25 tables | `runs/v25` |
| `v26_cmp.py` | v26 | `ext_write=erase` against `fill`: rates and length | erase and fill dirs (`regen.sh v26`) |
| `v28_an.py` | v28 | INERT role ledger over windows | `runs/v28/*.tsv` |
| `v28_decomp.py` | v28 | Shares of v24's D carried by the role classes | `runs/v28/*.tsv` |
| `v28_tab.py` | v28 | Compact rows for the README | `runs/v28/*.tsv` |
| `v28_id.py` | v28 | v28 lines without role lines equal the v27 run's | `runs/v28/X.tsv runs/v27/X.tsv` |
| `v29_crit.py` | v27, v29, v30, STATUS | Criterion 1: strict counts per checkpoint, 500k/50k, 350k to 500k | `runs/v29/*_m195_*.tsv` |
| `v29_series.py` | v29, v30 | Per-checkpoint strict, active, mean length, monomers, inactive sites | `runs/v29/*.tsv` |
| `v29_len.py` | v29, v30 | v25 length-ledger terms summed over windows | `runs/v29/*.tsv` |
| `v30_multi.py` | v30 | `multi` children and off-register parents per window, with `no_mass` | `runs/v30/*.tsv` |
| `v30_fill34.py` | v30 | Share of strict entry-0 activations with offset 34 filled | `runs/v27/X.tsv runs/v30/X.tsv` |
| `regen.sh` | v23, v26, v27 | Links recompute runs under each version's names and runs the scripts above | `v23`, `v27` or `v26`, output dir |

## Notes

- `regen.sh v23` and `regen.sh v27` run `build/ps_scan` on the fidelity runs before the
  scripts. The v23 scans were made at b4b4ea1, the v27 scans at 34839f4.
- STATUS.md's criterion-1 reference rows for v26 and v27 come from `v29_crit.py` on
  `runs/v26/*.tsv`, `runs/v27/*nomut*.tsv` and `runs/v27/t*_s1.tsv`.
- Line-equality checks in the entries' Checks bullets were mostly run as inline shell
  commands (`grep`, `cmp`, `md5sum`), as each bullet describes; only `idcheck.sh` and
  `v28_id.py` are scripts. A few single figures were also computed inline and not saved.
- Not included: a helper that searched extracted PDF text for page numbers (literature,
  not run data).
