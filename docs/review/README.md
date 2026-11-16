# Artificial Life Review

English narrative review covering soft, hard, and wet artificial life, with soft artificial life as the main emphasis. Digital organisms, cellular automata, executable chemistries, spatial ecology, and open-ended-evolution measurement receive the most attention. Hard and wet systems supply substantive comparisons. TIDE's research positioning is a separate concluding section. The second pass adds a fifteen-work synthesis of emergent boundaries, channel-specific permeability, resource accounting, group transitions, and label-free measurement; all candidate rules remain open for discussion.

## Deliverables

- [Compiled review](artificial-life-review.pdf)
- [LaTeX entry point](artificial-life-review.tex)
- [BibTeX references](references.bib)
- [Source archive](artificial-life-review-source.zip)
- [Evidence and access notes](evidence.md)
- [Figure provenance and regeneration](figures/README.md)

The review is a research draft, not an exhaustive systematic review or a peer-reviewed publication. Five original conceptual diagrams accompany the literature synthesis; a separate appendix reanalyzes archived exploratory outputs in a sixth figure. No new simulations were run. It distinguishes preprints, journal versions, limited-access sources, project proposals, and the archived probe. Citation/access checks were made on 2026-11-15.

## Build

Requirements: a LaTeX distribution with `pdflatex`, BibTeX, `latexmk`, and the standard packages declared in the entry point. This workspace was checked with TeX Live 2023 and latexmk 4.81. No package installation was needed.

From this directory in the repository:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -outdir=../../build/alife-review artificial-life-review.tex
```

For a separately extracted source archive, use a local build directory:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -outdir=build artificial-life-review.tex
```

BibTeX and cross-reference reruns are managed by latexmk. The source compiles without the cached reference PDFs, Python, or a network connection: the six vector figure PDFs are included. Regenerating them requires Python 3 and Matplotlib; run `python3 figures/render_figures.py`. The ten plotted records and an optional original-log extraction script are included. All intermediate files belong in the build directory; the delivered PDF is copied here only after validation.

## Source organization

The entry point includes eight files under `sections/`: conceptual framework, soft systems, hard systems, wet systems, ecology/measurement, emergent boundaries and operational individuality, the research agenda, and an archived-probe appendix. Shared bibliography and styling are maintained centrally. Subagents contributed independent literature searches, the hard and wet chapters, scientific reviews, and an audit of the probe's recorded outputs; integration and compilation were checked by the coordinating agent.

Original research PDFs remain separate, local-only files indexed in [references](../references/README.md). [Unavailable sources](../references/unavailable.md) record retrieval and evidence limits. The supplementary evidence notes retain initial discovery receipts as history; the integration notes at their top and the reference manifest hold the final cache status.

## Verification

Verified on 2026-11-15:

- Repository and independently extracted source-archive builds completed with `latexmk` exit status 0. The review has **26 pages, six figures, and 44 resolved bibliography entries**. Extracted text matched between builds.
- Final LaTeX logs contain no warnings, undefined references, or overfull/underfull boxes. All pages were rendered and visually inspected; the corrected cover and final bibliography were rechecked.
- All six vector figures regenerated from the archive without network access, cached papers, or a prototype executable and matched repository figure bytes exactly. The archive contains 25 source/assets files, including the Python scripts and archived data snapshot.
- All 39 cached original PDFs matched their recorded byte counts, page counts, and SHA-256 hashes and remain ignored by Git. The second pass added eleven PDFs, two for screening only; its included corpus is fifteen works.
- Local documentation links, Python source syntax and function/file line limits, bibliography keys, archive integrity/input identity, and `git diff --check` were checked.
- Three independent stream reviewers checked the added scientific synthesis. Source findings, code observations, and candidate TIDE transitions remain separate. Exact-version and failed-retrieval limits are retained in the evidence reports.
- The earlier independent audit of the ten plotted probe records remains applicable; no original logs or plotted data were changed in this second pass.

No new TIDE runtime tests or biological/robotic/simulation runs are claimed by this review. The appendix reanalyzes existing local prototype logs and narrows their interpretation. The evidence notes identify sources whose available text or reading depth remains limited.
