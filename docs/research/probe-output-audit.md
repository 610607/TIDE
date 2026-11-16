# Audit of the archived shared-memory probe

Date: 2026-11-15. Read-only inspection of existing outputs and source; no simulations or tests were rerun. Findings were incorporated into the [corrected probe record](coreworld-shared-memory-probe.md) and [historical comparison](shared-memory-prior-work.md). No prototype or fresh-kernel code was changed.

## Inventory and provenance

| Output group | Files | Mutation off | Mutation 0.003 |
| --- | ---: | ---: | ---: |
| Baseline (`e1`) | 20 | 10 | 10 |
| A-E (`e2`) | 100 | 50 | 50 |
| Ownership comparison (`e3`) | 20 | 10 | 10 |
| Total | 140 | 70 | 70 |

Ten `e3/write=any` records repeat E + guard none. All interval rows and recorded digests agree; totals agree after accounting for the additional `denied=0` output field. Thus the archive contains 130 distinct seed/configuration tuples, not 140 independent treatments. All seven current source hashes match the probe's recorded source table. The previous claim of 140 re-executed runs was not independently rerun in this audit.

The review's empirical figure uses exactly the ten mutation-on `e3` files, five per permission condition. [The plotted snapshot](../review/figures/probe-data.json) preserves source filenames and SHA-256 hashes. [The extractor](../review/figures/extract_probe.py) checks the setting and observation times. Every plot value and hash was independently checked by a second reviewer.

## Mechanisms and metrics checked against source

| Source location | Actual meaning | Implication |
| --- | --- | --- |
| `cw_vm.cpp`, copy and spawn, lines 139-194 | `written` records successful offsets; other writers can subsequently change them. A direction change alone does not clear the mask. | Coverage is historical construction evidence, not intact inherited code or functional reproduction. |
| `cw_vm.cpp`, lines 180-182 | `faithful_spawns` compares target bytes with the CPU's current site at spawn time. | Hopping, parent changes, inert copies, and foreign reads complicate any heredity interpretation. |
| `cw_inspect.cpp`, lines 53-55 | `repl` counts currently surviving CPUs with any lifetime spawn. | Zero survivors with past births can coexist with a large interval birth count. |
| `cw_inspect.cpp`, lines 63-75 | Genotype census includes all nonblank sites. | Dead code and allocations contribute to richness. |
| `cw_death.cpp`, lines 15-26 and 65-78 | After newborn insertion and age removal, local reaping removes excess CPUs at a site. Hops can also create excess occupancy. | Byte overwrite is not itself a CPU-death operation. |
| `cw_vm.cpp`, lines 187-192 and 207-213 | Child ownership transfers conditionally from an allocation; hopping changes execution location but not home/allocation ownership. | CPU vacancy is not synonymous with allocatable vacancy. |
| `cw_inspect.cpp`, lines 78-94 | The digest excludes RNG state, birth rounds, coverage masks/sites, home/allocation bookkeeping, next identity and counters/configuration. | Equal digest values cannot prove complete-state deterministic replay. |

These locations refer to the source hashes recorded in the probe. The local-only source lives under `prototype/experiments/coreworld/` and is not part of the review archive.

## Interpretations corrected

- Baseline none, mutation-on seeds 2-4 freeze with 1,024 CPUs on 2,304 sites; full occupancy is not required. D + occupied instead illustrates a full-occupancy write stall.
- Protection changes some mutation-off throughput outcomes despite preserving identical bytes. Equal baseline digests do not imply identical counters or general policy equivalence.
- The experiment is not a complete factorial. A-C are single-variable changes, D-E combine variables, and other combinations are missing. No universal necessity or unique successful rule set follows.
- In mutation-on round 3, claimed writes reduce matched-seed final birth throughput by 3.38-5.17 times; with mutation off, by 9.53-10.34 times. The earlier one-tenth statement conflated these settings.
- For mutation-on seed 1, claimed age deaths are 144,645 / 146,299 = 98.87%; unrestricted age deaths are 44,363 / 613,768 = 7.23%. These are cumulative fractions, separate from final-interval byte agreement and birth counts.
- Claimed final CPU counts leave 26-32% of sites without a CPU, but the logs do not establish that these sites are unowned or available for allocation.
- The numeric parser rejects unknown keys/enums and trailing junk, but does not fully validate non-finite values or unsigned-domain inputs. This caveat does not alter the documented headers in the audited dataset.

## Boundary of verification

This audit establishes consistency of recorded outputs, selected summary calculations, and source-level metric definitions. It does not establish reproductive viability of evolved strings, full-state replay, or causality for every birth/death event. Those require new instrumentation or controlled replay experiments under a separately agreed contract.
