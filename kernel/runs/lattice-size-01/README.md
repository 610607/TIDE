# Does lattice size alone change whether RCCCJD persists?

**Status: running.** This study implements the agreed [scale-control brief](../../../docs/research/lattice-size-rq.md). It holds the read_fetch-retain cell fixed and runs it on 24 × 24, 32 × 32, 48 × 48 and 64 × 64 tori, with the same 32 seeds (32001–32032) at every size. It asks whether the fetch-requiring genotype `RCCCJD` is established and persists differently across sizes at fixed persistence filters (t = 1,024 and t = 4,096). It also asks whether any difference comes from size or from the filter length that changed with size in the earlier studies. No result is reported here yet.

[Frozen protocol](protocol.md) · [Research brief](../../../docs/research/lattice-size-rq.md)

## Files

| File | Contents |
| --- | --- |
| [protocol.md](protocol.md) | Configuration, observer changes, endpoints, tests, validation checks and clarifications |
| [study.cpp](study.cpp) | Observer, lifetime assays, spatial statistics and origin counts; built by the [Makefile](Makefile) into `kernel/build/lattice-size/study` |
| [run.py](run.py) | Validation and the batched primary driver; commits and pushes each batch |
| [analyze.py](analyze.py) | Endpoints, tests and descriptive patterns; standard library only |
| `revision.sha256` | Digests of the frozen files, written after validation passed |
| `results/validation/` | Validation worlds, `checks.tsv`, `extended.tsv` (agreed item 13) and the tested digests |
| `results/primary/` | 128 primary worlds, `L<size>-<seed>/`, with `progress.log` |

## Replay

```sh
make -C kernel/runs/lattice-size-01
kernel/build/lattice-size/study --controls
python3 kernel/runs/lattice-size-01/run.py validate
python3 kernel/runs/lattice-size-01/run.py primary --deadline 6900
python3 kernel/runs/lattice-size-01/analyze.py primary
```

Each world's `log.txt` records its exact command, the kernel revision, its end hash, run time and peak memory. Rerunning a command with the same seed and configuration reproduces its tables byte for byte.
