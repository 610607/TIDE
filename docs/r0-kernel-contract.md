# Reference VM v1

This is the baseline adopted for the first neighbor-dependence pilot. The worked seven-tick birth fixes the meaning of reserve, copy, jump, return and divide. The following choices complete that example under the delegated implementation decision. Each comparison can cite this version. [Worked trace](r0-worked-birth.md) · [Research question](research/neighbor-dependence-rq.md)

## World and time

A rectangular lattice has one bank of up to 32 bytes per site. Coordinates increase east and north. Each bank is free, reserved by one adjacent CPU, or occupied by one individual. A bank has a visible length of 0 to 32. Bytes inside that length are readable and executable, including residual or partly written bytes, subject to permissions. Every other offset is invalid. Each occupied bank has a CPU. Its newborn state is local PC 0, east bearing, own read bank at offset 0, write offset 0, no allocation and no saved return. Host addresses and host instructions have no representation.

The schedule is synchronous with next-tick newborns. All attempts see the opening world. Each opening CPU gets one slice except a CPU due for reclamation. A due CPU dies before its attempt. In resolution, apply each CPU's local register edits and its exclusive writes or releases, and award competing claims on opening-free sites. A release becomes available for new claims next tick. A newborn never overwrites an opening CPU. The sole conserved resource is lattice space. Free + reserved + occupied equals the lattice area. Reserving moves one site from free to reserved. A birth moves it to occupied, an abandoned reservation moves it back to free, and death moves an occupied site to free. Bytes are information in preexisting banks. Slices expire each tick. There is no energy account.

Boundary can be bounded or toroidal. A directional lookup that leaves a bounded world, or wraps to the caller itself, has no neighbor. Directions always originate at the CPU site, including during borrowed execution. Placement starts at the direction left of the bearing. Directed placement tries only that site. First-free placement scans north, east, south, west cyclically from that starting direction. An attempt proposes exactly one opening-free target. A contested claim goes to the smallest origin coordinate (x, then y). Losers wait for the next tick. Arbitration and scheduling have one supported setting each in v1.

## Transitions

PC advancement means one byte, with no wrap. One failed fetch consumes its slice. An invalid local PC returns to local entry. An inaccessible or invalid foreign PC returns to the saved local continuation. Each tick rechecks access. A CPU can fetch its own body and read it regardless of the two external permission flags. The external read and fetch flags independently allow all four neighboring banks. A focal-site override is available for paired assays. Only the CPU's current reservation accepts its writes.

| Byte | Effect |
| --- | --- |
| `R` | If already holding a reservation, advance. Otherwise request placement. On success resize the opening-free bank to the caller's body length, preserve the visible prefix and fill new bytes with zero. Set read to own offset 0 and write to reservation offset 0. Advance. On no space or a lost claim, leave PC and registers in place. |
| `J` | From a local instruction, check external fetch access and offset 0 in the bearing direction. If valid, save the next local PC and transfer there. Otherwise fall through locally with no saved return. A jump fetched abroad falls through there with the existing return intact. |
| `T` | Return to the saved local PC and consume the return address. Without a saved return, advance. |
| `S`, `H` | Select the neighbor in the bearing direction or the caller's own body as read bank, respectively, at offset 0. A missing neighbor selects an invalid bank. Advance. The permission check happens at copy time. |
| `+` | Advance the read offset, saturating at 32, then advance PC. |
| `>` | Turn the bearing clockwise by 90 degrees and advance. Existing addresses stay fixed. |
| `C` | If the source offset is permitted and visible and the destination is in the caller's reservation, copy one byte, apply the configured substitution, and increment both offsets and the PC. Otherwise spend the attempt and advance PC only. The pointers, bank bytes and written coverage stay unchanged on failure. |
| `L` | If a reservation has unwritten bytes and PC is above offset 0, go back one byte in the current bank. Otherwise advance. |
| `D` | If every offset of the reservation has been written, give it a newborn CPU at entry. Otherwise release any held reservation. Both outcomes restart the caller with newborn registers, preserving its body and birth time. |
| `P` | Stay at the current instruction, consuming the slice. |
| Any other byte | Advance by one. The ancestor's period is an ordinary no-op. |

Writes are sequential and the write offset is exactly the length of the written prefix. It supplies complete coverage without a separate flag array. Opening-snapshot visibility applies to borrowed fetches and data reads even if the supplying individual dies or modifies a reservation on that tick.

## Run configuration and replay

The optional maximum age is the number of eligible ticks since birth. Zero disables age death. Death also releases the caller's reservation. Reclamation retains the visible bytes by default, with an empty-bank alternative. Successful division always preserves the offspring bytes. The only mutation operator is a per-successful-copy substitution. The integer rate is in parts per million. One keyed draw decides whether to substitute. A separate draw selects a byte from `R.JTSH+>CLDP` excluding the input. This keeps genome length fixed. Seed, resolving tick, CPU site and destination offset key the draws. Each seed has the same draws across permission arms for matching addresses and ticks.

The reference hash serializes configuration, focal permissions, tick, visibility, bank contents, birth ticks, reservation ownership and CPU state in canonical site order with explicit integer encoding. Attempt and birth observations are outputs. Removing the observer has no effect on transitions. No per-byte upkeep, length tariff, asynchronous scheduler or alternate arbitration is implemented in v1.
