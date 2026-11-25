# Tick timing benchmark

This directory measures the wall-clock cost of VM v1 ticks. It is a timing benchmark, not an experiment. It reports elapsed time, the final state hash and the occupied-site count at the last tick. The count is recorded only as the workload behind each time: step cost grows with occupied sites. No lineage, genotype or population outcome is computed or interpreted here.

## Configuration

`tick_timing WIDTH HEIGHT FIRST_SEED WORLDS TICKS [events]` runs WORLDS consecutive seeds in each of three access arms and times the two halves of TICKS separately. `events` also collects the per-tick `Event` vector that study observers read; without it, `step` runs bare.

| Setting | Value |
| --- | --- |
| World | WIDTH × HEIGHT torus, synchronous next-tick update, first-free placement |
| Founder | One `R..CLD` at x = WIDTH / 4, y = HEIGHT / 2 (site 36 at 16 × 4) |
| Rules held fixed | Age limit 80, 20,000 ppm copy substitution, retained bytes |
| Arms | `self`: no external read or fetch. `read`: neighbor reads. `read_fetch`: neighbor reads and neighbor instruction fetch |
| Kernel source | `kernel/src` as of `b61abe7` (unchanged through `a79a670`) |
| Build | `make -C kernel bench`: g++ 13.3.0, `-O2 -Wall -Wextra -Wpedantic -std=c++20` |
| Machine | 4 vCPU Intel Xeon @ 2.10 GHz, one thread per core, 15 GB RAM, Linux 6.18 |
| Date | 2026-11-25 |

## Runs

Every run is in [results/2026-11-25.tsv](results/2026-11-25.tsv). The `run` column says whether a process ran alone (`serial`) or as one of four simultaneous processes (`concurrent4`).

```sh
make -C kernel bench
kernel/build/tick_timing 16 4 1 16 8192
kernel/build/tick_timing 16 4 1 16 8192 events
kernel/build/tick_timing 32 32 1 4 16384
kernel/build/tick_timing 32 32 1 4 16384 events
kernel/build/tick_timing 64 64 1 2 16384
kernel/build/tick_timing 64 64 1 2 16384 events
# concurrent4: four processes at once, FIRST_SEED 101, 105, 109 and 113
kernel/build/tick_timing 32 32 101 4 16384
```

The bare and `events` runs of each serial world reached the same final hash in all 66 pairs. At 16 × 4, seed 1, `self`, 2,048 ticks, the hash is `5ad5609e62e364d0`.

## Timing

Mean wall-clock microseconds per tick per world, both halves pooled.

| World | Worlds per arm | Ticks | Mode | self | read | read_fetch | µs per occupied site-tick |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 16 × 4 | 16 | 8,192 | bare | 2.55 | 1.92 | 2.00 | 0.037–0.048 |
| 16 × 4 | 16 | 8,192 | events | 3.26 | 3.49 | 3.59 | 0.061–0.068 |
| 32 × 32 | 4 | 16,384 | bare | 33.9 | 34.2 | 32.8 | 0.039–0.041 |
| 32 × 32 | 4 | 16,384 | events | 61.5 | 54.5 | 59.3 | 0.065–0.073 |
| 64 × 64 | 2 | 16,384 | bare | 143.0 | 142.7 | 131.8 | 0.039–0.042 |
| 64 × 64 | 2 | 16,384 | events | 300.6 | 299.9 | 305.8 | 0.088–0.091 |

The last column divides by the mean occupied count at the final tick. Cost per occupied site-tick was about 0.04 µs bare and 0.06–0.09 µs with event collection. It did not depend on the arm. The 16 × 4 `self` bare mean includes warm-up: that arm ran first in its process, and six of its first seven worlds took 2.88–4.10 µs, while the other ten took 1.86–2.10 µs.

Four simultaneous 32 × 32 bare processes averaged 34.2 µs per tick per world, the same as one process alone. Together they finished 48 worlds × 16,384 ticks in 6.84 s of wall time, about 115,000 world-ticks per second. On this machine, throughput scales with the number of cores for independent worlds.

These numbers cover the VM step and event collection only. Study observers add their own bookkeeping, and lifetime assays fork and run whole worlds. Estimates built on these numbers must state the extra cost they assume.
