# Project instructions

## Purpose

TIDE (TIDE Is Digital Evolution) is a digital-life kernel driven by basic rules. Execution, replication, spatial interaction, and resource constraints are the subject of study. The kernel is written in C++.

Research comes first: the project aims to contribute to the study of open-ended evolution, with results others can replay. See the [roadmap](docs/roadmap.md) for stages, the performance line, and the literature search plan.

Upper layers (phenotype naming, cards, controller seats, narrative, web UI) are out of scope until the kernel is established. Do not add them, and do not let their vocabulary shape kernel rules.

## Current stage

Literature reading is complete for the first round. The first research question is selected, and its first stage has a [stage report](docs/research/neighbor-dependence-results.md) and a [summary of results, open lines and compute](docs/research/first-stage-summary.md). The [v1 contract](docs/r0-kernel-contract.md), single-threaded C++ reference and fixed-program assays are in place under `kernel/`. In the tested fields, descendants evolved heritable dependence on neighbor instruction fetch and, separately, on neighbor data reads. The dependent families were short-lived. In untreated long runs no confirmed descendant born after its first carrier's death kept a changed program. The latest study found no spontaneous renewal of a copying relationship in 1,024 untreated worlds and traced where its seven starting families stopped ([natural-renewal-01](kernel/runs/natural-renewal-01/README.md)). The roadmap proposes measuring those stages prospectively; this is not agreed. The second-stage research question is agreed: does neighbor access change long-term evolutionary dynamics ([brief](docs/research/access-dynamics-rq.md))? Its runs are recorded in [access-dynamics-01](kernel/runs/access-dynamics-01/README.md). Dead code as an ecological resource is a proposal ranked after it. The exploratory substrate under `experiments/physub/` is paused at v31. The pool and chain experiments `experiments/template-pool-01`, `template-persistence-01`, `chain-structure-01` and `chain-residence-01` use separate models and are not linked to the first question.

Decided:

- Research is the first priority. Build the C++ kernel first; consider upper layers afterwards.
- Start the kernel fresh under an agreed contract rather than evolving the earlier prototype.
- Study evolution after a supplied ancestor first. Emergence of replicators from random programs is a separate, later experiment with its own acceptance criteria.
- The first research question is whether descendants of an independently reproducing ancestor can evolve a heritable dependence on reading a neighbor's data or fetching its instructions. Evaluate the two channels separately. See the [RQ brief](docs/research/neighbor-dependence-rq.md).
- The second research question is whether the neighbor access permission (own body only, neighbor data reads, or neighbor reads plus instruction fetch) changes a population's long-term evolutionary dynamics from the same ancestor, with every other rule fixed. It is measured with Bedau's activity statistics and a neutral shadow, and with the MODES metrics after a persistence filter, under the preregistered windows, endpoints and interpretation rules of the [brief](docs/research/access-dynamics-rq.md). The six-byte genome caps complexity, so the question compares dynamics and does not test open-ended growth.
- Ecological labels and classifications must not influence physical behavior. Kernel state carries no role, shield, or host fields; relationships such as parasitism are diagnosed in analysis only.
- The first kernel is a local address-based VM: each individual owns its CPU, and readable regions, writable allocations, and instruction-fetch permissions are explicit. A bound-reaction model is a possible later kernel or comparison, not the first one. See [kernel notes](docs/tierra-stringmol-kernel-notes.md).
- If instruction-fetch permission denies a cross-site jump, the caller spends one instruction attempt and continues at its next local instruction. See the [worked jump](docs/r0-worked-birth.md#denied-cross-site-jump).
- Copying moves a byte from a read pointer to a write pointer. A program can direct the read pointer at any region its permissions allow, including a neighbor's.
- Allocation occupies public lattice space before division, so competition for space happens during replication.
- The default update is two-phase and synchronous: execute, then resolve conflicts by a deterministic rule. Sequential random-order update is a planned CPU-only comparison mode.
- GPU acceleration comes after the rules stabilize and must be cross-platform. The single-threaded CPU implementation is the reference that other backends must match by state hash.

Reference settings for the first pilot are versioned in the contract. Future experiments can vary one mechanism at a time.

- One program per site; addresses are a neighbor direction plus an offset.
- A program writes only to its own allocation; reading and instruction fetch may reach neighbors.
- Death leaves the code bytes in place as unowned memory that others can read and fetch but that no longer executes itself.
- CPU time slices are the only cost. Per-byte upkeep and length-based division costs are deferred comparison variables.

The v1 baseline uses next-tick newborns, coordinate arbitration and complete write coverage at division. Failed copies advance only the PC. Supported variations include boundary, placement, reclamation, age limit, access and copy-substitution rate. See the [contract](docs/r0-kernel-contract.md) for every transition and the [pilot protocol](kernel/runs/pilot-01/protocol.md) for its generation threshold, horizon and seed budget.

Open questions include how often fetch dependence survives genomic change in independently sampled field pedigrees, whether a changed program can persist beyond its first carrier without a supplied partner, whether untreated families can renew a copying relationship, and whether dependence is on a provider's bytes or on its ongoing execution.

Do not present an open item or a candidate design as an agreed requirement. Move an item to "Decided" only after the user agrees to it.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Roadmap, literature review, mechanism notes, and design discussion |
| `docs/references/` | Reference index and cache manifest; PDF files are local only |
| `kernel/` | C++ reference VM, fixed-program assays, pilot runner and replay records |
| `experiments/physub/` | Exploratory physics-like substrate in C++ (not the kernel); provisional rules, tests, probes, replay viewer, run job lists |
| `prototype/` | Earlier exploratory prototype; local only, not tracked |

`prototype/` is a behavioral reference, not a starting point. Its instruction set, role labels, and upper layers carry no authority over the new kernel. Links from `docs/` into `prototype/` resolve only in a working copy that has it.

`experiments/` code is tracked for reproducibility and remote development. Its rules are provisional experiment configuration and carry no authority over the kernel contract. Build and test `experiments/physub/` with CMake (3.20+, C++20):

```sh
cmake -S experiments/physub -B experiments/physub/build
cmake --build experiments/physub/build -j
ctest --test-dir experiments/physub/build --output-on-failure
```

See `experiments/physub/README.md` for running experiments and replaying results.

Build and test the reference kernel with a C++20 compiler and Make from the repository root.

```sh
make -C kernel all test
```

See the [pilot record](kernel/runs/pilot-01/README.md) for commands to replay a field run, audit its ancestry and fork the focal permission.

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
