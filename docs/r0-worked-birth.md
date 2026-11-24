# One birth on a local address-based VM

**R0 paper example · 2026-11-23.** This trace illustrates a positive control for the [neighbor-dependence question](research/neighbor-dependence-rq.md). It uses the agreed local VM, individually owned CPU, bytewise copy, public allocation before division and synchronous execute/resolve update. These seven ticks and their failure branches are now exercised by the [v1 reference tests](../kernel/tests/vm_tests.cpp). The [v1 contract](r0-kernel-contract.md) defines the remaining instructions and boundary cases. [Project decisions](../AGENTS.md) · [R0 design options](r0-design-options.md)

## Initial state

| Site | Contents at tick 0 |
| --- | --- |
| A at (0,0) | Borrower's three bytes `R J D`. Its CPU starts at A[0], with allocation direction north. |
| B at (1,0) | Live provider's five bytes `C C C T P`. Its own CPU is parked at B[4]. |
| N at (0,1) | Free northern site with room for three bytes. |

The borrowed instructions run on A's CPU. Directions and read/write pointers are relative to that CPU's owner. In the example each active CPU gets one instruction attempt per tick, including a denied attempt. Instructions read the opening snapshot. Register updates, writes, reservations and births become visible at the end of resolution. Mutation is off.

## Successful division

Each letter denotes one fixture byte. N can be free, reserved by A, or occupied by a newborn. The reservation records which offsets this attempt has written. This lets a hand calculation distinguish copied bytes from residual contents.

| Tick | Fetch by A's CPU | Effect after resolution |
| ---: | --- | --- |
| 1 | A[0] = `R` | A reserves N for its three-byte length. N is publicly unavailable and has no CPU. Set read pointer to A[0], write pointer to N[0], and clear the three written flags. Advance to A[1]. |
| 2 | A[1] = `J` | With eastward instruction access permitted, save A[2] as the return address and set the instruction pointer to B[0]. |
| 3 | B[0] = `C` | Read `R` from A[0] and write it to N[0]. Mark offset 0. Advance both data pointers and the instruction pointer by one. |
| 4 | B[1] = `C` | Copy `J` from A[1] to N[1]. Mark offset 1 and advance the pointers. |
| 5 | B[2] = `C` | Copy `D` from A[2] to N[2]. Mark offset 2 and advance the pointers. The data pointers now sit one past the copied span. |
| 6 | B[3] = `T` | Return to A[2] and clear the saved return address. |
| 7 | A[2] = `D` | All three offsets were written in this reservation. Transfer N to a new individual with bytes `R J D`. A keeps its body and returns to A[0]. Clear A's reservation, pointers and written flags. |

N's CPU becomes eligible on tick 8 with the same entry offset and initial register defaults as A at birth. B's own CPU executes `P` and stays at B[4] throughout. The seven ticks consume seven attempts by A and seven by B. The three physical sites go from two occupied and one free, through two occupied and one reserved, to three occupied. This fixture charges CPU slices and reserves space. Copying writes information into existing storage.

The recorded parent is A, the instruction provider for the loop is B, and the three copied bytes came from A. To test a second generation, give N a matched eastern provider and a free northern site in a fresh assay and trace N's own division. In the evolutionary run, follow the actual daughter and record the neighbors available to it. One successful hand-worked birth establishes the expected trace for the first assay.

## Denied cross-site jump

**Agreed transition.** If instruction-fetch permission denies a cross-site jump, the caller spends one instruction attempt and continues at its next local instruction. In the fixture, A fetches the jump at A[1], permission denies entry to B[0], and A's next instruction is A[2]. A program can put a local recovery instruction there. This fixture puts division there, so the eventual birth outcome also depends on the complete-coverage division rule.

## Two forks to check by hand

| Fork | Transition and failure effect | Observable result |
| --- | --- | --- |
| **Deny neighbor fetch** | Start from the same tick-0 state and deny A's external fetch permission. Tick 1 still reserves N. On tick 2 the jump checks its target, records a denial and falls through to A[2] without entering B or saving a return address. On tick 3 division finds zero of three offsets written. Release N, clear A's copy state and return to A[0]. | One failed division, zero offspring, two occupied sites and one free. Repeating the three-tick cycle in this fixed fixture produces the same failure. B stays present. A self-copying control using its own copy instructions retains access to them. |
| **Two allocations compete** | Add a CPU at X=(0,2) that also executes `R` on tick 1, facing south toward N. Both callers see N free. Resolve competing requests in ascending origin-coordinate order. A wins. X consumes its attempt, receives a busy result and remains at its reserve instruction with no allocation or pointer advance. | One public reservation and one winner. Reversing the order in which intents are collected gives A the same reservation. On tick 2 X sees N already reserved and receives the same busy result if it retries. |

The data-read comparison needs its own fixture. At a `C` whose source pointer addresses B and whose instruction is fetched locally, the denied-read transition spends one attempt, advances to the next instruction, leaves both data pointers and the destination byte unchanged, and sets no written flag. A later division still has to satisfy the coverage rule. The read control uses `RSCLD` with an eastern provider carrying `RSCLDP`. Successful reads produce a daughter carrying `RSCLD`. With access removed, the write offset stays at zero and the local loop repeats. The [serial assays](../kernel/tests/vm_tests.cpp) check the actual daughters across three fresh neighborhoods. The [v1 contract](r0-kernel-contract.md) also specifies interrupted foreign fetch, reservation release on death and next-tick visibility.
