# Review figures

Six original Python/Matplotlib figures accompany the review. The PDF assets are vector graphics. No source-paper image is reproduced or traced; no kernel simulation is executed by the renderer.

| Asset | Evidence type | Source or construction |
| --- | --- | --- |
| `soft-substrates.pdf` | Conceptual synthesis | Langton 1984 local CA neighborhoods; Ray 1991 CPU/memory organization; Hickinbotham et al. 2021 bound-pair reaction context. The CA highlight is a neighborhood, not a reproducing pattern. |
| `replication-provenance.pdf` | Original illustrative VM configuration | Ray 1991 motivates borrowed copying routines and redirected copying. The four labeled entities are not a recorded Tierra event or an approved TIDE contract. Permissions are assumed for the drawn channels. |
| `update-semantics.pdf` | Deterministic didactic construction | A five-site binary ring with `x[i] = x[i] OR x[i-1]`; snapshot and fixed-order in-place updates have the displayed one-sweep outputs. This rule eventually saturates in both cases. |
| `measurement-limits.pdf` | Synthetic categories and timing | Standish 2003 and Taylor et al. 2016 motivate separating sequence variation, functional tests, and ongoing innovation. The lower example is a lineage still alive at cutoff but too young for a declared persistence lag. The dotted future is unknown. |
| `graded-boundaries.pdf` | Original candidate schematic | Six independently specified interaction channels and a paired amount ledger. Informed by the second-pass mechanism comparisons; symbolic transmission rules are not empirical values, approved TIDE transitions, or a reproduced model. |
| `probe-tradeoffs.pdf` | Reanalysis of archived exploratory results | All five seeds for both `write=any` and `write=claimed`, mutation 0.003, from round 3 of the local shared-memory probe. No runs were excluded within this stated subset. |

## Regeneration

Python 3 and Matplotlib are sufficient to render the figures (verified with Python 3.10.10 and Matplotlib 3.7.1). No network, cached reference PDF, LaTeX, or prototype executable is required:

```sh
python3 figures/render_figures.py
```

Run from the review directory. The script defaults to writing the six vector PDFs beside itself. Add `--preview /path/to/previews` for optional PNG inspection images, or `--output /path/to/figures` for another destination. `diagram_style.py` centralizes typography and colors. The manuscript can compile from the included PDFs without installing Python packages.

`probe-data.json` contains the plotted records, source filenames, original-log SHA-256 hashes, and metric definitions. These records are intentionally distributed separately from the ignored prototype tree. The log percentages were printed to two decimals; no extra precision is inferred. The birth and byte-agreement windows are rounds 18,000 to 20,000; age-death fractions are cumulative over 20,000 rounds. Bars show medians, not uncertainty estimates. Common seed identifiers do not guarantee shared random-event histories after treatments diverge.

To refresh that snapshot when the original local logs are available, from the repository root:

```sh
python3 docs/review/figures/extract_probe.py \
  --runs prototype/experiments/coreworld/runs/e3
```

The extraction script checks the plotted setting and observation times before writing the snapshot. The archived data do not establish functional heredity, adaptive improvement, or full-state replay. See the manuscript appendix and the repository research notes for those limits.
