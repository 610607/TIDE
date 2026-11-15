# Project instructions

## Purpose

TIDE is a digital-life kernel driven by basic rules. Execution, replication, spatial interaction, and resource constraints are the subject of study. The kernel is written in C++.

Upper layers (phenotype naming, cards, controller seats, narrative, web UI) are out of scope until the kernel is established. Do not add them, and do not let their vocabulary shape kernel rules.

## Current stage

Literature reading is complete for the first round. The first-kernel rule discussion is in progress. No kernel code exists in this repository yet.

Decided:

- Build the C++ kernel first; consider upper layers afterwards.
- Start the kernel fresh under an agreed contract rather than evolving the earlier prototype.
- Study evolution after a supplied ancestor first. Emergence of replicators from random programs is a separate, later experiment with its own acceptance criteria.
- Ecological labels and classifications must not influence physical behavior.

Open:

- The execution and addressing contract: local address-based VM versus bound-reaction model. See [kernel notes](docs/tierra-stringmol-kernel-notes.md).
- Spatial granularity, update order, explicit energy, offspring placement, and reclamation.

Do not present an open item or a candidate design as an agreed requirement. Move an item to "Decided" only after the user agrees to it.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Literature review, mechanism notes, and design discussion |
| `docs/references/` | Reference index and cache manifest; PDF files are local only |
| `prototype/` | Earlier exploratory prototype; local only, not tracked |

`prototype/` is a behavioral reference, not a starting point. Its instruction set, role labels, and upper layers carry no authority over the new kernel. Links from `docs/` into `prototype/` resolve only in a working copy that has it.

Record the kernel's location, build commands, and test commands here once they exist.

## Language

Use English for project documentation, code comments, identifiers, commit messages, and other repository artifacts. Conversation replies may follow the user's language preference.

## Research sources

Cache openly accessible research PDFs in `docs/references/pdf/` and read the local copy before downloading again. Keep original PDF bytes, and record the source URL, version, retrieval date, page count, and SHA-256 in `docs/references/manifest.json`.

The repository is public. PDF files are ignored by git and must not be committed; the manifest and reference index are the tracked record. To restore a missing PDF, download it from the manifest's source URL and verify its SHA-256.

Link research notes to cached PDFs and retain their original online sources in the reference index. Distinguish published articles, preprints, and technical specifications. Separate source findings, code observations, and proposed experiments; do not present a candidate design as an agreed requirement.

## Kernel changes

Settle a rule in discussion before implementing it. State each rule as an explicit transition with defined effects on failure.

Hard acceptance criteria for kernel changes:

- Instruction semantics: every instruction has a specified effect, including on invalid operands and failed operations.
- Resource accounting: every unit of each conserved quantity is traceable to a source and a sink.
- Locality: an individual's effects stay within its defined neighborhood and permissions.
- Deterministic replay: the same seed and configuration reproduce the same state, bit for bit.

Treat scheduling, boundaries, placement, reclamation, and mutation as experimental variables with named configuration, not as fixed implementation details.

## Experiments

Disable mutation and use small fixed programs when checking what the instruction set can express. Change one mechanism per experiment.

Report every run, including stagnation and extinction, alongside survivors. Record the seed, configuration, and kernel revision needed to replay a result. State whether a claim comes from a source, from code inspection, or from an executed run.

## Commits

Format: `<type>(scope): <summary>`, with `scope` optional. Write the summary in English, imperative mood, without a trailing period. Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
