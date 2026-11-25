# Residence and return of a six-bead contact pattern

Reuse the complete geometry and transition rules from the [structure trial](../chain-structure-01/README.md) at `b2ee1c5`. The arms are `001011` and `011100` at attraction factor four, plus their common neutral control at factor one. There is one intact chain, zero mutation and no feeding. Count all local move proposals, including stays. Also measure residence in accepted shape changes to expose the contribution of waiting in place.

## Targets and clocks

Before running the analysis, select the U in the previous figure as the primary target. Its entire indexed contact set is {1–6, 2–5}. Measure the same quantities for all eight individual contact maps and for the 2–5 contact alone, allowing other contacts in that pair measurement. Count how many distinct shapes realize each target after identifying rotations and reflections. Keep bead indices fixed.

A residence interval starts on an actual transition into the target and ends on the first transition out. A return interval starts on an actual exit and ends on the first transition back. Either interval can be one proposal long. Use the stationary flux across the target boundary to weight interval starts. For every target report occupancy, mean residence, mean return, and both means on the accepted-change clock. For the U also compute both first-passage distributions, their medians and the fractions remaining at selected times through 8,192 proposals. Include long excursions in the means without truncation.

## Return after opening

From a stationary exit from the U, measure the probability of regaining the U before reaching a shape with zero nonbackbone contacts. For excursions that reach zero first, continue from the actual first zero-contact shape and record which two-contact map occurs next. Publish the full distribution across all possible two-contact maps. Zero-contact shapes may still bend. Eventual return alone cannot distinguish preferences on the connected finite graph.

## Verification

Construct the finite transition matrix from the previous study's proposal slots and acceptance thresholds. Verify conservation, detailed balance, and agreement between stationary-flow means and first-passage means for the U. Check the return-after-opening boundary equations and probability sums. Numerical linear solves and propagation use floating point.

Use 64 fresh seeds, 29825–29856 and 29857–29888, for a trajectory check of the U. Start each arm in an exact draw from its own stationary law. Share move and acceptance proposals across arms within each seed. Run 32,768 proposals per trajectory. Count the proportion of new U visits lasting more than 128 proposals and the proportion of U exits returning within 128. Admit only interval starts with the full 128-proposal observation window available. Record every seed, event count, eligible denominator and success count. Flag a pooled block fraction if its absolute discrepancy from the finite-state prediction exceeds 0.04. The finite-state calculation is the primary estimate.
