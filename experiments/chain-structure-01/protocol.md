# Can sequence order bias the shape of one chain?

This exploratory model starts with one intact six-bead chain. Supply the two sequences used in the earlier pool example, `001011` and `011100`. Also enumerate all 20 orders with three beads of each type. No material enters or leaves. There is no copying, mutation or partner chain.

## Rules

Place bead 1 at the origin of the open square lattice and enumerate every oriented, self-avoiding walk with five unit steps. Each site holds at most one bead. Rotations and reflections have equal weight. A contact is a pair of beads one lattice edge apart and at least two positions apart along the chain. Contacts are observed afresh in each shape. A bead can touch multiple beads.

Give a shape weight `q^u`, where `u` counts contacts between unlike beads. Compare attraction (`q=4`) and neutral geometry (`q=1`). Condition on the supplied chain and normalize over the same set of shapes in every case. This contact preference is a supplied assumption. The comparison asks where contacts occur along the backbone when the order changes.

## Measurements

The primary endpoint is the total variation distance between the two exact distributions of indexed geometric contact maps, calculated as half the sum of absolute probability differences. The maps record which positions touch, irrespective of their bead types. Repeat with chain reversal identified. Report how frequently each feasible pair touches, the distribution of the number of contacts, and the range of any-contact probabilities across all 20 sequences. Check neutral equality, bit-complement symmetry and reversal symmetry exactly.

Use reversible single-bead moves to check the equilibrium result from a straight start and a common compact U-shaped start. Choose one bead and one displacement uniformly from the four unit diagonals and four axial displacements of length two. Reject overlap or a broken backbone. Accept a valid move with probability `min(1, new_weight/old_weight)`. Check proposal symmetry and graph connectivity on the full shape set before running trajectories. If the local graph is disconnected, report that fact and use a half-and-half mixture with a uniformly chosen pivot bead and one of the eight square symmetries applied to the suffix. The sampler has no physical time calibration.

For each start and seed, run the two orders under attraction and the common neutral ensemble. Use seeds 29761–29792 and 29793–29824 as two blocks. Discard 1,024 proposals, then record the map after each of 8,192 proposals, including rejected moves. Preserve every run histogram, count steps that gain and lose contacts, and compare pooled map frequencies to the exact law for each arm, start and block. Flag any pooled distance above 0.025. Exact distributions determine the structural result.
