# Project instructions

## Purpose

TIDE is a digital-life kernel driven by basic rules. Execution, replication, spatial interaction, and resource constraints are the subject of study. The kernel is written in C++.

Research comes first: the project aims to contribute to the study of open-ended evolution, with results others can replay. See the [roadmap](docs/roadmap.md) for stages, the performance line, and the literature search plan.

Upper layers (phenotype naming, cards, controller seats, narrative, web UI) are out of scope until the kernel is established. Do not add them, and do not let their vocabulary shape kernel rules.

## Current stage

Literature reading is complete for the first round. Research positioning (RQ) and the kernel contract (R0) are in progress. No kernel code exists in this repository yet.

Decided:

- Research is the first priority. Build the C++ kernel first; consider upper layers afterwards.
- Start the kernel fresh under an agreed contract rather than evolving the earlier prototype.
- Study evolution after a supplied ancestor first. Emergence of replicators from random programs is a separate, later experiment with its own acceptance criteria.
- Ecological labels and classifications must not influence physical behavior. Kernel state carries no role, shield, or host fields; relationships such as parasitism are diagnosed in analysis only.
- The first kernel is a local address-based VM: each individual owns its CPU, and readable regions, writable allocations, and instruction-fetch permissions are explicit. A bound-reaction model is a possible later kernel or comparison, not the first one. See [kernel notes](docs/tierra-stringmol-kernel-notes.md).
- Copying moves a byte from a read pointer to a write pointer. A program can direct the read pointer at any region its permissions allow, including a neighbor's.
- Allocation occupies public lattice space before division, so competition for space happens during replication.
- The default update is two-phase and synchronous: execute, then resolve conflicts by a deterministic rule. Sequential random-order update is a CPU-only comparison mode.
- GPU acceleration comes after the rules stabilize and must be cross-platform. The single-threaded CPU implementation is the reference that other backends must match by state hash.

Working defaults for the first version. Each is a named configuration variable to test, not a settled rule:

- One program per site; addresses are a neighbor direction plus an offset.
- A program writes only to its own allocation; reading and instruction fetch may reach neighbors.
- Death leaves the code bytes in place as unowned memory that others can read and fetch but that no longer executes itself.
- CPU time slices are the only cost. Per-byte upkeep and length-based division costs are switchable variables, off by default.

Open:

- The research question the kernel must be able to test.
- Conflict resolution and newborn scheduling, boundaries, offspring placement, reclamation policy, and mutation operators.
- The instruction set and the exact permission rules that realize the decisions above.

Do not present an open item or a candidate design as an agreed requirement. Move an item to "Decided" only after the user agrees to it.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Roadmap, literature review, mechanism notes, and design discussion |
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
