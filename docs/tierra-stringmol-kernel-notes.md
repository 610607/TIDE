# Tierra and Spatial Stringmol Kernel Mechanisms

Updated: 2026-11-15.

This reading examines execution ownership, replication addresses, offspring placement, and scheduling against the C++ kernel of the earlier exploratory prototype (`prototype/core/src/tide_vm.cpp`) and its state definitions (`prototype/core/include/tide_vm.hpp`). The prototype is a local reference and is not tracked in this repository; "current" below refers to that prototype. See the [literature review](alife-literature-review.md) for the wider research scope.

The central design question is how far programs can change the source, destination, control flow, and cost of replication. Removing ecological labels from causal rules addresses only part of that question.

## Source mechanisms

### Tierra

Ray's shared soup separates the executing CPU from the location of executed code. Borrowed execution retains the borrower's CPU. The hyper-parasite example redirects that CPU's copying toward the code provider. Allocation occupies memory before division; reclamation removes the CPU and frees its allocation without erasing code.

Source: [Ray 1991, local PDF](references/pdf/ray-1991-synthesis-of-life.pdf), original book pp. 378-382, 385, and 402-403. Page numbers refer to printed book pagination.

The 1998 V5.0 manual specifies register-indirect `movii`, allocating `mal`, and activating `divide`, plus configurable free-memory permissions and length-dependent CPU slices. This later manual clarifies instruction contracts; its complete feature set should not be attributed to the 1991 implementation.

Source: [Tierra manual](https://tomray.me/pubs/doc/index.html), sections 7 and 8.4.

### Spatial Stringmol

The 2021 experiment schedules a bound reaction pair, one instruction per pair per step, without a separate energy gate. Products require neighboring vacancies; stochastic decay releases space. Replication strategies can change through program execution. Analysis disables mutation and tests both reaction directions to diagnose parasitism as a relationship.

Source: [Hickinbotham et al. 2021, local PDF](references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf), sections 2.4, 2.6, and 5.1-5.3.

The v0.2 language specification describes paired pointers into both strings, held by the active partner. Copy uses read/write pointers, cleavage uses the flow pointer, and termination releases the binding. This explains language structure; older configuration defaults cannot be assumed for the 2021 experiment.

Source: [Stringmol specification, local PDF](references/pdf/stringmol-specification-v0.2-ycs-2010-458.pdf), sections 7 and 10.6-10.8.

The follow-up [pinned-code inspection](research/spatial-update-semantics.md) confirms built-in indels and substitution in release 0.2.3.4's spatial copy path. The exact configurations of the twenty published runs remain unverified; operator support is not an exact experimental mutation mix.

## Current C++ behavior

These observations come from source inspection, not newly executed experiments. Locations refer to the files on the update date.

| Mechanism | Current implementation | Consequence |
| --- | --- | --- |
| Execution ownership | `execute_tick` fetches from `code_cell_idx` but operates on the caller's `self`; `call_tpl` does not make the neighbor passive | Code borrowing differs from pair-owned reaction execution |
| Copy addresses | `OP_COPY_BYTE`, line 495 onward, reads `self.genome` and writes `self.child_buf`; `OP_MEASURE` returns own length | Programs cannot select an arbitrary permitted source region through a general address operation |
| Offspring allocation | `OP_ALLOC` sets internal buffer length; `handle_divide` selects a site later | Replication does not reserve public lattice space before birth |
| First execution | `run_epoch` visits shuffled site indices; a newly occupied unvisited site can execute in that sweep | First-execution delay depends on the target's position in the update order |
| Provider invalidation | Line 446 onward checks `alive` and `birth_id`; failure resets execution, and site reuse clears `Cell` | References are tied to a live identity; retained bytes are not automatically usable residual code |
| Costs | Fixed ticks per visit, per-byte upkeep, and division costs based on copied length | Several mechanisms can independently favor shorter programs |
| Classification feedback | Lines 389-396 use `ROLE_PARASITE` to protect hosts and alter replacement scores; shield affects borrowing and replacement | Changing classification can change physical trajectories |

These differences are model choices, not automatically bugs or reasons to reproduce another system wholesale.

## Check expressive capacity before changing the instruction set

Use small fixed programs with mutation disabled to inspect these traces.

| Trace | What the source establishes | What remains to check |
| --- | --- | --- |
| Self-copy | Bytewise copying and division exist | Every product byte comes from the current copy attempt; failed division has defined state effects |
| Borrow code to copy self | Borrowed instructions operate on caller state and its copy buffer | CPU owner, instruction source, and copied data source can be tracked separately |
| Redirect a borrower toward copying its provider | The copy source is fixed; general source addressing is absent | Which readable targets and permissions a revised primitive should expose |
| Self-scanning or fragment rewriting | Copy destinations are restricted to the offspring buffer | Whether these capabilities belong in the first revised kernel or a later extension |

A label or borrow counter alone does not establish that a trace is expressible.

## Candidate experiments

These experiments have not been implemented. Define their contracts and observations before delegating the necessary C++ changes.

### Copy addresses and execution context

Use two distinguishable sequences, no mutation, and both ordinary copying code and code intended to redirect copying. Record the executing identity, instruction source, read/write locations, and product bytes. The new local address-based VM must express these traces; the old prototype supplies a behavioral comparison. A bound-reaction model remains a possible later comparison.

### Spatial occupation and update timing

Separate two interventions:

- Reservation timing: compare ordinary replicators with programs that allocate and delay division. Measure allocation failures, reservation duration, and successful births.
- Full-neighborhood placement: hold resource and baseline-death parameters fixed while comparing vacancy-only birth with uniform replacement. Disable role-based protection for this baseline; assess the existing scoring rule separately. Count replacement deaths separately.

Record birth-to-first-execution delay. Change newborn scheduling in a separate experiment rather than combining it with placement changes.

### Scheduling and upkeep

Compare a short replicator and a replicator with an appended tail, with mutation disabled. Cross fixed versus length-proportional CPU allocation with zero versus current per-byte upkeep. Hold the world's total execution budget fixed and report actual execution, instructions per birth, and energy expenditure. An unexecuted tail still has to be copied.

Zero upkeep is an experimental control, not a decision to remove the energy system.

### Residual code and reference invalidation

Invalidate a provider during borrowed execution, first retaining its bytes and then overwriting its location. Trace the next instruction, registers, and stack. Verify the existing identity-reference contract before considering readable unowned memory. Deleting memory-safety checks is not an acceptable implementation of residual-code ecology.

## Design comparison and current decision

The comparison below records the alternatives considered. The local address-based VM has since been selected; its instruction-level contract is still open.

| Candidate | Contract | Main cost |
| --- | --- | --- |
| Local address-based VM | An individual owns its CPU; readable regions, writable allocations, and instruction-fetch permissions are explicit | Define addresses, allocation, invalidation, and revised copy instructions |
| Bound-reaction model | Two programs form an execution unit controlling cross-string copying and product formation | Redesign state ownership, binding, and release; effectively a different kernel model |

The project decision is to build a fresh local address-based VM first, as recorded in [AGENTS.md](../AGENTS.md). It directly tests whether programs can change what they copy. This is a project choice, not a literature-mandated conclusion. Reading a neighbor does not automatically imply permission to overwrite it.

After agreement, centralize shared state/interface changes and delegate implementation, testing, and review with separate file ownership. Hard acceptance criteria should cover instruction semantics, resource accounting, locality, and deterministic replay. Ecological experiments should report survival, stagnation, and extinction.

## Status

- Mechanism reading and source-code comparison are complete for this round.
- The local address-based VM direction is agreed. Detailed instruction transitions, failure effects, and several experimental policies remain open; the full R0 contract is not complete.
- These experiments have not been run, and C++, Node bindings, and frontend files have not been changed.
- The follow-up code inspection confirms the release's indel/substitution support. Exact published per-run mutation configurations remain open; this does not alter the execution and spatial distinctions established here.
