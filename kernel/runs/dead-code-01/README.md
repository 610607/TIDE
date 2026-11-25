# Does retaining dead code change evolutionary dynamics?

**In progress.** This record will hold the results of the agreed [dead-code question](../../../docs/research/dead-code-rq.md) once every world has run. Retain and empty reclamation are compared in the read and read_fetch arms, with a self-retain reference, on 32 matched seeds per cell at 32 × 32, followed by a descriptive 64 × 64 check. [Protocol](protocol.md)

## Status

- Kernel hooks for residue-cleared forks: `World::clear_residue` and `World::set_reclamation` (`2c28805`), tested in `kernel/tests/vm_tests.cpp`.
- Study code: [study.cpp](study.cpp), [run.py](run.py) and [analyze.py](analyze.py).
- Validation, freeze, primary set and scale check: progress is recorded in `results/*/progress.log` and in the commits of each batch.
