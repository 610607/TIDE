# Untreated renewal follow-up

From the repository root (Python 3.10+, POSIX, C++20 compiler):

```sh
python3 -B kernel/runs/natural-renewal-02/run.py --validate
python3 -B kernel/runs/natural-renewal-02/run.py --first-batch
python3 -B kernel/runs/natural-renewal-02/run.py --all
```

The first command runs archive-only validation. The second runs at most seeds 100001–100100; the third resumes through batch 53 and reports cohort incidence. Batches are under `kernel/runs/natural-renewal-02/results/primary/`. See the [frozen protocol](protocol.md).
