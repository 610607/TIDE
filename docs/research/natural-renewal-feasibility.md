# Is a larger untreated renewal study feasible?

The [original protocol](../../kernel/runs/natural-renewal-01/protocol.md) screened 1,024 untreated worlds. In the broad confirmed-reader screen, **7/1,024 worlds (0.684%)** had a start: a confirmed reader copied all six aligned bytes unchanged from one distinct living carrier of its sequence and produced a confirmed child. There was one start per positive world and none in the changed-reader subset. **0/7 starter-bearing worlds** produced a confirmed renewal: a qualifying copy by descendant replacements after both previous role holders died. Thus **0/1,024 worlds** renewed overall. The independent units are seeded worlds, not related readers, descendants, or copy attempts. [Starting births](../../kernel/runs/natural-renewal-01/results/starts.tsv) · [Per-world endpoints](../../kernel/runs/natural-renewal-01/results/endpoints.tsv)

## What would another zero tell us?

For zero events in `n` independent worlds with common event probability `p`, the exact one-sided 95% binomial upper bound is `1 − 0.05^(1/n)`: at that probability, `(1 − p)^n = 0.05`. The historical bound is **34.8% conditional on a start** (`n = 7`), versus **0.292% per untreated world** (`n = 1,024`). A low overall incidence can reflect scarce starts rather than scarce renewal once started.

| Desired conditional upper limit if none renew | Starter-bearing worlds needed | Fixed worlds to reach that count in expectation | Fixed worlds for about a 90% chance of reaching it |
| --- | ---: | ---: | ---: |
| 10% | 29 | ~4,240 | ~5,300 |
| 5% | 59 | ~8,630 | ~10,200 |

These recruitment estimates assume an unchanged start probability of `7/1,024`: divide the target count by that rate for the expectation, or use a binomial tail for the 90% column. The rate is estimated from only seven starts, not guaranteed; the 90% refers to obtaining enough starts, not to observing zero renewals.

## What to decide before spending compute

For a comparable untreated study, count each world once if any copy qualifies as a start, and once as a success if any eligible starter renews. Record multiple starters and depths without treating them as independent trials. Keep enrollment through tick 8,192 and the 324-tick clock from each enrolled reader's birth, not from the starting copy; retain the assay tail for confirmation only. Extinction before any start stays in the all-world denominator; extinction after a start without prior renewal is a conditional failure, not a reason to drop the world. The [historical extinct world](../../kernel/runs/natural-renewal-01/results/world.tsv) had no start. If a fixed cohort yields too few starts and no renewal, report the bound at the realized count (no conditional estimate if none start), keep the all-world result, and call the conditional target unresolved rather than adding seeds after seeing outcomes.

**Recommendation:** Decide whether ruling out a 10% conditional rate would change the next research decision, and whether a budget on the order of 5,300 fresh worlds is affordable. If not, defer a larger untreated cohort; do not default to the 5% target. These are planning examples, not an agreed design. One renewal would establish turnover once, not sustained renewal or a population effect.
