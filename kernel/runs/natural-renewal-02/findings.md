# Natural copying relationships rarely started and did not renew in the observation window

The [fixed follow-up](protocol.md) completed 53 batches of 100 new untreated worlds (seeds 100001–105300). Each starter-bearing world counts once, even if it had multiple starting copies. No historical seeds enter these estimates.

| Endpoint | New cohort |
| --- | ---: |
| Worlds with a confirmed starting copy | 29 / 5,300 (0.55%) |
| Starting copies across those worlds | 31 |
| Worlds with a confirmed renewal after both original roles turned over | 0 / 5,300 (one-sided exact 95% upper bound: 0.05651%) |
| Starter-bearing worlds with a confirmed renewal | 0 / 29 (one-sided exact 95% upper bound: 9.8145%) |
| Starter-bearing worlds with a second successive renewal | 0 / 29 |
| Final status: reproducing / stagnant / extinct | 5,300 / 0 / 0 |

The fixed cohort reached the target of 29 starter-bearing worlds. The result constrains both recruitment and post-start renewal: under these rules, a renewal within the original observation window is uncommon even among worlds that formed a relationship. It does not exclude rarer renewals, later renewals, or effects on population dynamics. The outcome concerns replacement by descendants in both roles, not the fate of every interaction or genotype. One world had a start in the descriptive changed-reader subset; it did not renew.

**Next research decision.** Do not enlarge the unchanged cohort to chase the first event. The [completed replay of all 31 starts](starter-audit/README.md) found that 24 lacked a second eligible descendant. One reached a post-turnover birth, but its child did not reproduce and could not be confirmed. An intervention is worth designing only if the replay identifies a specific comparison; it is not implied by the zero count. A post hoc [eligibility audit](eligibility-audit/README.md) classified the 74 births that left starter lineages: 58 copied another program without substitution, 34 of them in place from residue in the executor's own daughter reservation. Only 9 carried a substitution, and 7 had the lineage's program but no offspring.

**Audit.** See the [batch records](results/primary/) for full world ledgers, program histories, contact and pedigree tables, endpoints and per-batch checksums. The [input manifest](revision.sha256) was checked before primary execution (manifest SHA-256: `0bbde1f8cc58f457d958b60bd1ef8974be52a666422aaff6e94a1b52d4d0d5a7`; base repository revision: `aded00f`). Four archived worlds matched all six reference tables under both forward and reverse execution. The supplied-partner classifier scored one renewal in the together branch and none in either control. Primary execution took 153 s elapsed on the local machine. Use the [replay commands](README.md) to regenerate missing batches or verify existing ones.
