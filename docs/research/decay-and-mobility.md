# Decay Form and Whole-Site Mobility: Sources and Candidate Designs

Updated: 2026-11-17. Status: candidate designs for `experiments/physub/`. On 2026-11-17 the
user agreed to run decay form M with a uniform rate and mobility option (a) as optional
physub configurations (section 4), and then to two controls that separate the two effects of
form M (section 5), and then to per-op rates in form M as proposed in section 6. Binding
(b) and size-dependent mobility remain open. Nothing here applies to the kernel contract.

This note separates source findings, observations of the physub code, executed runs and
candidate designs. Page numbers are printed pages unless marked "PDF p.".

## 1. Motivation (executed runs and code)

The v13 runs ([physub README](../../experiments/physub/README.md), revision 7ef36f3, census
from 53898eb) show that once space saturates, 66-83% of active sites run copy-born programs
that no longer replicate, while replicators of any genotype fall about tenfold by 100k ticks.
Faster decay of inactive sites (`p_dead`, with or without `dead_quiet`) does not reach them.
In the code, an activation ends only when the byte at its ip decays or it starves (no
starvation occurred). Polite needs 26 bytes to replicate (`ps_knockout`), but its ip visits
only 4 opcode bytes while it waits for a free neighbor and 13 over a full cycle. A replicator
therefore usually loses replication before its activation ends, and keeps its site.

Two changes were requested on 2026-11-17: decay rates fixed per op class and independent of
activation (section 2), and movement of whole site contents (section 3).

## 2. Decay rate fixed per op class

Request (2026-11-17): each op class gets its own fixed decay rate, the same for every site
whether it runs or not, so that selection acts on replication versus decay. Rates that
depend on the environment or on other instructions are out of scope for now.

### Source findings

- **Species-specific decay in selection.** Eigen 1971 separates "an individual
  decomposition term 𝒟_i" from dilution in the removal term (Eq. II-11, p. 475) and defines
  the selective value W_i⁰ = 𝒜_i𝒬_i − 𝒟_i (Eq. II-31, p. 477). 𝒟_i may depend on
  concentrations (p. 476). On length: "Unless a protective macromolecular coat is formed,
  long chains will hydrolyse more easily than shorter ones" (p. 492).
  [cached scan](../references/pdf/eigen-1971-selforganization-of-matter.pdf)
- **Dynamic kinetic stability.** Pross 2011 writes dX/dt = kMX − gX, where "k and g are rate
  constants for replicator formation and decay" (Eq. 1, p. 5). He notes an "inherent
  difficulty in the formal quantification of DKS" but allows quantification between direct
  competitors from their relative replication and decay rates (§2.2.5, p. 6). Pascal, Pross
  and Sutherland 2013 use the same form (Eq. 5.1, p. 4) and find no environment-independent
  DKS parameter (pp. 5-6).
  [Pross 2011](../references/pdf/pross-2011-general-theory-of-evolution.pdf),
  [Pascal et al. 2013](../references/pdf/pascal-pross-sutherland-2013-evolutionary-theory-origin-of-life.pdf)
- **Composing a lifetime from parts.** For a series system, "the failure rate of the system
  is equal to the sum of the failure rates of all the blocks" (Gavrilov and Gavrilova 2001,
  p. 534). The NIST/SEMATECH e-Handbook (§8.1.8.2) states the conditions: independent
  components, failure at the first component failure; add failure rates, multiply
  reliabilities.
  [Gavrilov and Gavrilova](../references/pdf/gavrilov-gavrilova-2001-reliability-theory-of-aging.pdf),
  [NIST chapter 8](../references/pdf/nist-sematech-2012-handbook-ch8-product-reliability.pdf)
- **Decay in prior polymer and replicator models.**
  - Per bond, uniform: the Wu and Higgs model breaks bonds "at rate b between any pair of
    monomers" (Wu 2012 thesis, ch. 2, p. 51); Tkachenko and Maslov 2015 let each intra-polymer
    bond "spontaneously break at a constant rate" (p. 045102-2).
  - Per molecule: Walker, Grover and Hud 2012 make "hydrolysis ... all or none" with
    propensity k_h·N_i, proportional to length (p. 5). Takeuchi and Hogeweg 2009 use one
    invariant rate d, and each molecule in a complex decays independently (p. 2). Stringmol
    v0.2 compares decay only while unbound with decay in all states: the former selects
    non-terminating reactions; constant-rate decay in all states gives a regular turnover of
    dominant species (Appendix C, printed pp. 38-39).
  - State-dependent: Wu et al. 2017 lower the break probability of double-stranded regions and
    of a ribozyme bound to its template (p. 5). This is a precedent for protection by
    binding, the opposite of the requested design.
  - None of the models read assigns different decay rates to different monomer types.
- **Type-dependent rates in chemistry.** Lindahl's Nobel lecture gives about 9,000
  depurinations and 300 depyrimidinations in a 3×10⁹ bp double-stranded genome per 24 h at
  37 °C (Fig. 3, p. 76), about 30:1 between the two classes; guanine and adenine are lost at
  similar rates (p. 75). The 1993 review and the 1973 rate paper are not openly accessible
  and were not read.
  [lecture](../references/pdf/lindahl-2015-nobel-lecture-intrinsic-fragility-of-dna.pdf)

### Code observations

- `World::hydrolyze` makes one keyed draw per non-inert byte per tick; the threshold depends
  only on activation and, with `dead_quiet`, on recent writes. Equal per-op rates without
  `p_dead` are therefore today's `p_hydro`, i.e. the v13 `dead0` runs.
- An activation ends only when the byte at its ip is inert (`check_wicks`) or when it starves;
  no v13 run recorded a starvation death. With `act_cap` 1 an active site cannot be ignited.
- Polite has 26 lethal bytes (`ps_knockout`). In a 9x9 trace without decay its ip visits 4
  opcode bytes while waiting for a free neighbor (offsets 6, 8, 11, 13: rnd, mov, jz, jmp) and
  13 over a full cycle.

### Candidate forms (none agreed)

- **P, per byte.** Each non-inert byte becomes inert with probability r[op(v)] per tick,
  op(v) = (v − 1) mod 9, in every site. The uniform case matches the per-bond models above and
  equals `dead0`, which ended with 33-39 replicators and 79-83% copy-born non-replicators at
  100k. Inference from the code: a replicator that loses a byte outside its ip path keeps its
  activation and its site, and shares the waiting loop with intact replicators. Per-op rates
  therefore cannot shorten its occupancy relative to theirs; P alone is not expected to clear
  these sites.
- **M, whole program.** A site's program decays in one event with probability
  1 − ∏ₖ(1 − r[op(xₖ)]) per tick (series rule). All its non-inert bytes return to the site's
  free monomers and its activation ends. The uniform case matches Walker et al. (all-or-none,
  propensity proportional to length) and Stringmol's decay in all states. Consequences, by
  inference: no in-place partial damage, so a replicator cannot turn into a non-replicator
  where it stands; non-replicators come only from faulty copies and decay at their own rate;
  cleared sites are blank, so `fill` copies no longer inherit residue (v12's largest error
  source); hydrolysis no longer mutates running programs. With uniform r the hazard grows
  with the number of non-inert bytes, which favors shorter programs, as in Eigen's p. 492.

### Values

- **Step 1, uniform r, matched ancestor.** P keeps r = 3e-6, the `dead0` runs. M uses
  r = 26 × 3e-6 / 40 = 1.95e-6 per non-inert byte, so polite's whole-program hazard equals
  its current replicative hazard (mean ≈ 12.8k ticks). Only the form changes.
- **Step 2, per-op spread.** No source gives rates for these op classes; only the size of a
  spread between monomer classes has a source (≈ 30:1, Lindahl). Which op is fragile would be
  a free choice. A candidate that avoids a designer's choice: assign each op class to the fast
  or slow class at random, with several fixed table seeds, and rescale so polite's hazard stays
  matched. This assignment method has no source and needs agreement before use.

### What to measure

The replicator census as now, plus per-site hazard h(x) = Σ r[op(xₖ)] and non-inert length
for replicators and non-replicators over time. Under a spread, a fall in mean h(x) among
non-replicators that does not appear among replicators would be selection for durable
non-replicators.

## 3. Whole-site mobility

Request (2026-11-17): free monomers diffuse, but written code stays where it is, so
non-replicating programs form walls; free macromolecules would be diluted and drift instead.
Proposed: move whole site contents (code bytes, the activation and its ip; energy undecided)
by Toffoli-Margolus block diffusion with the rate as a scanned knob; keep the ledger; cross
walls with probability 1/(W+1); let mobility fall with the number of non-inert bytes
following Rouse/Zimm scaling. All sites move, active or not. Surface tension and adhesion
(Cellular Potts) are out of scope.

### Source findings

- **Margolus block diffusion.** Boerlijst and Hogeweg 1991: "the states of a subfield are
  rotated 90° clockwise or anti-clockwise with equal probability. After a diffusion step the
  subfields are shifted one cell diagonally" (pp. 18-19); the default is two diffusion steps
  per time step, and the algorithm conserves particles. Kulagin and Shapovalov 2023 rotate
  each way with probability 0 < p ≤ 0.5 ("the classic MCA uses p = 0.5"), derive
  D_c(p) = ½·p/(1 − p) for Δx = Δt = 1 (Eq. 30, p. 7), and show that skipping steps with
  probability p_s gives D = (1 − p_s)·D_c(0.5) (Eq. 32, p. 10). The Toffoli and Margolus 1987
  book was not accessible; the rule is cited as these papers state it.
  [Boerlijst and Hogeweg](../references/pdf/boerlijst-hogeweg-1991-spiral-wave.pdf),
  [Kulagin and Shapovalov](../references/pdf/kulagin-shapovalov-2023-margolus-diffusion.pdf)
- **Diffusion strength and parasites.** Boerlijst and Hogeweg tested 0, 2 and 16 steps and
  state that the result "surely holds up to 32 diffusion steps" (§3.4, p. 24). "Without
  diffusion the catalytic waves are thin; with diffusion they become thicker and thus more
  effective in eliminating molecules that receive no catalysis." One parasite "is fatal when
  there is no diffusion"; at higher rates spirals grow and become more stable against
  parasites. The paper does not report that weak diffusion lets dead or uncatalyzed molecules
  block space (decay simply empties a cell), nor that strong diffusion lets parasites win;
  the latter appears only as an intuition that their results contradict within the tested
  range. A cost of strong mixing is reported elsewhere:
  - Takeuchi and Hogeweg 2009: "the survival area in the surface model greatly varies as D
    changes" (p. 12); diffusion "can homogenize the spatial structure at the wave tip"
    (Text S1, p. 4).
  - Czárán, Könnyű and Szathmáry 2015: "at high mobilities the parasite can destroy
    cooperation" (manuscript p. 13).
  - Against this, Könnyű, Czárán and Szathmáry 2008 find that parasites "cannot drive the
    metabolic system extinct even at very high diffusion rates" (pp. 11-12).
  The effect of strong mixing therefore depends on the model.
- **What moves, and with what.**
  - Boerlijst and Hogeweg: one molecule or nothing per cell; whole cell states rotate (p. 18).
  - Metabolic replicator model: single-site replicators make D Toffoli-Margolus steps per
    generation, independent of content; replication is a single update, so no step is
    interrupted (Könnyű et al. 2008, p. 6; up to D = 20 with "no qualitative difference",
    p. 8). Czárán et al. 2015 rotate randomly chosen blocks and note that "even D = 0
    represents some minimum mixing" (manuscript p. 10).
  - Takeuchi and Hogeweg 2009 swap the contents of two squares at rate D (not Margolus);
    swaps involving complexes "maintain the association of molecules" (Text S1, pp. 2-3).
  - Hutton 2002: an atom moves to an empty neighbor only if it "remains within the
    neighbourhood of every atom it is bonded with"; bonds and states move with it (§2.2).
  - Spatial Stringmol 2021: strings do not move (paper; code of v0.2.3.4 checked).
- **Mobility and size.** Rouse: D_G = k_BT/[(N+1)ζ], without hydrodynamic interaction; it
  describes unentangled melts and concentrated solutions and is poor for dilute solutions
  (Padding 2005, pp. 5, 10, 13, 19, 35); entangled melts follow reptation, D ∝ N⁻²
  (p. 51). Zimm: dilute solution with hydrodynamic interaction, D ∝ N^-1/2 in a Θ solvent
  (Wuttke 2011, eq. 91, p. B4.23; Padding eq. 3.19, p. 38) and D ∝ N^-ν in a good solvent
  (Wuttke p. B4.23), with ν ≈ 0.588 for self-avoiding walks (Clisby 2010). These are chains
  spread through three-dimensional solvent. In the bond fluctuation model the size dependence
  emerges from chain connectivity (Wittmer et al. 2011, §II). No lattice artificial-life model
  read imposes size-dependent mobility; Czárán et al. 2015 left it out explicitly
  (manuscript p. 13).
  [Padding](../references/pdf/padding-2005-theory-of-polymer-dynamics.pdf),
  [Wuttke](../references/pdf/wuttke-2011-macromolecular-dynamics.pdf)
- **Movement during copying.** No model read treats movement that interrupts a copy as an
  error cost; replication is a single update or reacting molecules move as one complex. The
  nearest case is Hutton 2002, where two molecules stayed attached while replicating and
  produced crossover variants (§3). This was not a systematic search.
- The wall-crossing probability 1/(W+1) is the existing physub rule; no source was checked.

### Code observations

- A site carries code bytes, activation slots (with ip) and energy; free monomers already
  diffuse on their own. Walls are stored per depositing site and edge, and erosion returns a
  unit to that site index. Observer arrays (`writer_`, `written_at_`, `ignited_at_`,
  `last_write_`, lineage) hold site indices or per-site times.
- Pointers are directions relative to the site. A 2x2 rotation turns the relative position
  of two sites in the same block by 90° and separates pairs that straddle two blocks. A copy
  in progress then continues into whatever site lies in the old direction.
- The substrate has no binding or pair relation; which site copies into which exists only in
  observer data. Moving copying pairs together needs a new physical relation, comparable to
  the bound complexes of Takeuchi and Hogeweg.
- Polite needs about 324 ticks to its first copy in an empty world. Estimate (inference): if
  any rotation that moves either member disturbs a copy, the disturbance rate per tick q lies
  between p_rot and 2·p_rot, and a copy survives with probability about (1 − q)^300. At
  q = 1e-3 about a quarter of copies are lost; at q = 1e-2, about 95%. The models above
  replicate in one update and have no such limit.
- A rotation moves four sites together, so per-site mobility needs a new block rule (for
  example a block probability computed from its four occupants). No source was found for one.

### Candidate design (none agreed)

- **Rule.** After the physics phase of a tick, each block of the current partition rotates
  clockwise or counterclockwise with probability p_rot/2 each and otherwise stays
  (Kulagin and Shapovalov's p); the partition shifts diagonally every tick. Code bytes,
  activation slots and observer data move with their site; energy moving or staying is
  open. Free monomers keep their own diffusion. Walls stay on their edges. A rotation crosses
  the block's four internal edges; requiring each crossing to pass 1/(W+1) is an extension of
  the current rule without a source. The ledger is unchanged because sites are only
  permuted.
- **All sites alike.** Every site moves under the same rule, active or not, as in every model
  read.
- **Rate scan.** Boerlijst and Hogeweg tested 0-32 steps per time step and Könnyű et al. up
  to 20 per generation. A polite generation is roughly 300 ticks, so p_rot in
  {0, 1e-3, 1e-2, 1e-1} gives about 0, 0.3, 3 and 30 block steps per generation. By the
  estimate above, rates near 1e-2 already break most copies.
- **Copying pairs.** (a) Accept misdirection as the price of mobility and measure it; no model
  read does this. (b) Move pairs together; this has a precedent in Takeuchi's complexes but
  needs a binding relation the substrate lacks.
- **Size dependence: deferred.** Rouse and Zimm describe chains in solvent, not a program held
  in one cell, so carrying over the exponent would be an analogy, and no lattice
  artificial-life model imposes it.

## 4. Agreed steps and implementation (2026-11-17)

Agreed by the user:

1. Decay form M with uniform r = 1.95e-6 per byte against `dead0`, so polite's hazard equals
   its current replicative hazard. No per-op rates yet.
2. Mobility option (a): no binding relation; copies may be cut, and the cut and error rates
   are measured.
3. A p_rot scan from well below 1/300 to 1e-2, bracketing the copy duration.

Both are optional physub configurations (`hydro_whole`, `p_rot`), off by default, and the
default replay digest is unchanged (revision 5579cb7). Choices made in implementing them,
not separately agreed:

- Rotation runs at the start of each tick, which is the same as after the previous tick's
  physics; it lets observers read a tick's births at their final positions.
- Energy stays with the lattice position, like free monomers: both are site fields fed or
  moved by their own rules, and an activation pays from the site it occupies.
- Each of the four crossed internal edges must pass 1/(W+1) (the extension above); a failed
  crossing leaves the whole block in place.
- Levels: p_rot in {1e-5, 1e-4, 1e-3, 3e-3, 1e-2}. A site moves with probability p_rot per
  tick, so a ~320-tick copy sees about 0.003, 0.03, 0.3, 1 and 3 moves of its parent. 1e-5
  is a near-static control, 1e-4 and 1e-3 lie below 1/300, 3e-3 is close to it, and 1e-2
  is the agreed upper end.
- The census trial runs without rotation, so "replicator" keeps meaning a program that can
  copy itself.

Results are in the [physub README](../../experiments/physub/README.md) (v14).

## 5. Separating the two effects of form M (agreed 2026-11-17)

In v14, form M with r = 1.95e-6 kept replicators near their peak, while form P (`dead0`)
lost about 80x. M changed two things at once: no program is damaged in place, and inactive
code clears in one event instead of byte by byte. The user agreed to two controls: (1)
per-byte decay of live programs with whole clearance of inactive code, and (2) whole decay of
live programs with per-byte decay of inactive code. Both use the same settings as v14:
96x96, 100k ticks, `ext_write` fill, `p_mut` 0.003, seeds 1-2, census, no rotation.

Definitions (choices made in implementing them, with reasons):

- **Classes.** The split uses the existing `p_dead` classes. A live site has an activation
  (or, with `dead_quiet`, was written recently; off here) and decays at `p_hydro`; any other
  site decays at `p_dead`. `hydro_whole` = `live` or `dead` picks the class that decays as a
  whole program. Reason: the classes and their rate keys already exist and are tested, so the
  controls add only the per-class choice of form.
- **Rates.** Each class keeps the form and rate it has in one v14 run: per byte at 3e-6 as in
  `dead0`, or whole at 1.95e-6 per byte as in `m195`. `dead0` and `m195` are then the diagonal
  of a 2x2 design, and each control differs from a v14 run in one class only:

  | run | live sites | other sites |
  | --- | --- | --- |
  | `dead0` | per byte, 3e-6 | per byte, 3e-6 |
  | `m195` | whole, 1.95e-6 | whole, 1.95e-6 |
  | `whole_dead` (control 1) | per byte, 3e-6 | whole, 1.95e-6 |
  | `whole_live` (control 2) | whole, 1.95e-6 | per byte, 3e-6 |

  Reason: this keeps the agreed hazard match (polite's whole-program hazard under M equals
  its replicative hazard under P) and introduces no new rate.
- **Switching class.** A site changes class when an activation starts or ends. In
  `whole_dead` an activation ended by a wick leaves its remaining bytes, which then clear in
  one event at the inactive rate.

Expected differences (inference, not measured):

- Copies under construction have no activation, so they decay with the inactive class:
  whole in `whole_dead`, per byte in `whole_live`. A copy takes about 320 ticks, and either
  form hits it rarely (expected per-byte losses about 3e-6 x 32 bytes x 320 ticks = 0.03;
  whole clearance about 1.95e-6 x 32 x 320 = 0.02).
- In `whole_live` an activation usually ends together with its code, so wick corpses are
  rare. Inactive code then comes mostly from abandoned or failed copies and from activations
  ended by writes, and that code decays byte by byte.

Results are in the [physub README](../../experiments/physub/README.md) (v15).

## 6. Per-op decay rates in form M (agreed 2026-11-17)

Request (2026-11-17): keep form M (a whole program decays in one event, with hazard equal to
the sum of its byte rates) and give each op class its own rate. The rate is fixed per class
and does not depend on activation or environment. The mean rate is aligned with the v14
r = 1.95e-6 for comparison with M. The spread between classes needs a source. The binding
rule (b) stays out. The proposal below was agreed as recommended; see "Agreed and
implemented" at the end of this section.

### Rule as requested

A site with non-inert bytes x₁…xₙ decays as a whole with probability
1 − ∏ₖ(1 − r[c(xₖ)]) per tick, c(v) = (v − 1) mod 9. Its hazard is h(x) ≈ Σₖ r[c(xₖ)]
(series rule, section 2). The same table applies to every site, live or not, so the option
would run with `hydro_whole` = 1 and without `p_dead` or `dead_quiet`.

### Code observations

- **The class is a property of the byte value.** Every non-inert byte has a class, whether it
  runs as an opcode or serves as an operand or data. The values 1-255 give mov, inc and dec 29
  values each and the other six classes 28 each. A per-op rate therefore applies to all
  bytes, not only to executed opcodes. Polite has 40 non-inert bytes out of 46: 13 opcode
  bytes and 27 operand or data bytes. By class: jmp 7, rnd 7, mov 5, jz 5, dec 5, ignite 4,
  inc 3, wall 2, unwall 2. Wall and unwall occur only as data. Inert bytes never decay.
- **Synonyms.** An opcode byte's class is its op, so its rate changes only with the
  instruction. Many operand bytes are read only as an offset mod `site_len` (64) or as a
  direction ((v − 1) mod 4, or INERT for the own site), so other values do the same job.
  Since 64 ≡ 1 (mod 9), the offset synonyms v, v + 64, v + 128, v + 192 fall in four
  consecutive classes. Direction synonyms (step 4) reach all nine classes. Some data bytes
  use the full value: polite's copy counter starts at K = 192 and the loop ends when it
  wraps to INERT, so a synonym there changes the copy length. Inference: under a spread,
  selection could lower a program's hazard through data-byte substitutions before it
  changes instructions. The resemblance to synonymous codons is an analogy without a source.
- **Rates change during execution.** INC and DEC change a byte's value and hence its class.
  Polite's two copy counters pass through all nine classes during a copy.
- **Random bytes.** Mutation and RND write `1 + key % 255`, uniform over the non-inert
  values (`ps_exec.cpp`). The expected rate of a written random byte is therefore the mean
  over the 255 values, weighted by values per class.

### Source findings

Spread between monomer classes:

- **Lindahl, Nobel lecture 2015.** In a 3×10⁹ bp double-stranded genome per 24 h at 37 °C,
  there are 9,000 depurinations and 300 depyrimidinations (Fig. 3, p. 76; slides, slide 6).
  Purines and pyrimidines occur in equal numbers in a duplex (base pairing; inference), so
  the per-base ratio between the two classes is about 30:1. "The abasic sites resulting from
  the loss of the bases guanine or adenine are chemically identical and were introduced at
  similar rates" (p. 75). Double- and single-stranded DNA depurinate "with only a 3- to
  4-fold difference" (p. 75). This is the only source read that gives two monomer classes
  leaving the same polymer under one condition.
  [lecture](../references/pdf/lindahl-2015-nobel-lecture-intrinsic-fragility-of-dna.pdf),
  [slides](../references/pdf/lindahl-2015-nobel-lecture-slides.pdf)
- **An et al. 2014.** The difference between adenine and guanine loss "was not obvious, and
  only a change of 3–25% was observed" (p. 4). At 37 °C and pH 7.1, the rate constants are
  2.2×10⁻¹⁰ s⁻¹ for G and 2.5×10⁻¹⁰ s⁻¹ for A (Table 1, p. 5). Context matters, however:
  "depurination rates changed dramatically with different sequences" (p. 8), and at pH 2.5
  the A30 half-life was 11.4 times that of AT15 (p. 9).
  [cached](../references/pdf/an-et-al-2014-nonenzymatic-depurination.pdf)
- **Levy and Miller 1998** (abstract, p. 7933; full text not cached). Free nucleobases at
  pH 7 have half-lives at 100 °C of "A and G ≈ 1 yr; U = 12 yr; C = 19 days". At 0 °C, A, U,
  G and T have half-lives of at least 10⁶ yr, and C has 17,000 yr. At 100 °C the rate
  ratios are C : A ≈ G : U ≈ 230 : 12 : 1 (computed from the half-lives). These are free
  bases decomposing, not monomers leaving a chain, and the order and spread depend on
  temperature.
- **Context dependence** (excluded by the request, listed so the exclusion is visible):
  - Kaukinen et al. 2002 (abstract, p. 468; not cached): RNA phosphodiester bonds 5′-UpA-3′
    and 5′-CpA-3′ showed ">100- and up to 35-fold reactivity differences" across sequence
    contexts, "a change of a single base several nucleosides away from the scissile bond
    markedly affected the reaction rate", and duplex formation was "strongly rate retarding".
  - Robinson and Robinson 2001 (HTML read, not cached, no page): asparagine deamidation
    half-times range from about 1 to 455 days depending on the neighboring residue.

Precedents in artificial life and replicator models:

- **Rates per molecular species.** Boerlijst and Hogeweg 1991 set p(empty) = decay[x] for
  each molecule species x (Table 1, p. 19). The hypercycle species share decay 0.2, and the
  parasite's decay (0.15, or "≤ 0.1" in plate 1C) is an experimental setting (p. 25).
  Takeuchi, Hogeweg and Koonin 2011 note that DNA is "markedly more resistant to hydrolysis
  than RNA" (p. 1). They give DNA a "substantially lower" decay rate than RNA as a model
  condition (p. 17), and each constituent of a complex decays on its own (p. 3). Both set
  rates per polymer species, not per monomer.
  [Boerlijst and Hogeweg](../references/pdf/boerlijst-hogeweg-1991-spiral-wave.pdf),
  [Takeuchi et al.](../references/pdf/takeuchi-hogeweg-koonin-2011-origin-of-dna-genomes.pdf)
- **Rates from structure.** Könnyű, Szilágyi and Czárán 2015 set the degradation
  probability from the fold energy, between a minimum of 0.1 and a maximum of 0.9 (p. 4).
  This is context dependent and so outside the request.
  [cached](../references/pdf/konnyu-et-al-2015-in-silico-ribozyme-evolution.pdf)
- **Uniform rates.** Ono and Ikegami 2000 use one rate (p. 244), and Hutton 2002 is
  uniform. Avida's per-instruction `prob_fail` (default 0; code) is an execution failure,
  not decay.
- **Instructions as monomers.** Ray 1991 compares instructions to amino acids rather than
  nucleotides "because they are 'chemically active'" (p. 374). Dorn, Nealson and Adami 2011
  treat Avida instructions as monomers "in the sense that they are selectable" (PDF p. 6).
  In a discussion of biosignatures they note that "different monomers may degrade at
  different rates" (PDF p. 4), but that remark is not a rule of their model.
  [Ray](../references/pdf/ray-1991-synthesis-of-life.pdf),
  [Dorn et al.](../references/pdf/dorn-nealson-adami-2011-monomer-abundance-v1.pdf)

What the sources support, and what they do not:

1. Decay rates that depend on monomer type exist in chemistry.
2. The spread between two monomer classes in one polymer under one condition is about 30:1
   (Lindahl).
3. Within a class, rates are close: A and G differ by 3-25%.
4. Context changes rates by one to two orders of magnitude; this is excluded by the request.

No source maps a specific instruction to a specific monomer or bond, so which op is fast
cannot be taken from the literature.

### Candidate design (none agreed)

**Spectrum.**

- **S1 (recommended): two levels, fast : slow = 30 : 1, from Lindahl.** This is the one
  source with two monomer classes leaving the same polymer under one condition, and it is
  physiological. Treating each class as a single rate follows Lindahl's "similar rates" and
  An et al.'s 3-25%.
- **S2 (not recommended first): four levels, 230 : 12 : 12 : 1, from Levy and Miller at
  100 °C.** These are free bases, and the spread and order change with temperature. Nine
  classes over four levels would also need a second grouping without a source.

**Assignment.** No source assigns ops to levels. Proposed: draw the assignment at random
and treat each draw ("table") as a replicate over the unknown mapping.

- **Number of fast classes.** Lindahl's ratio compares two classes of equal size. Nine
  classes cannot split evenly, so four are fast and five slow. Fast values are then 112-114
  of 255 (44-45%). Five fast classes is equally close to half; the choice of four is a tie
  break to confirm.
- **Draw rule.** For table t ≥ 1, h = mix(t ⊕ 17·golden). The classes k = 0…8 are sorted
  by mix(h ⊕ k), and the first four are fast. `mix` is physub's existing hash, and 17 is
  the next free stream id. A table does not depend on the run seed, so table and seed are
  separate factors.
- **Tables 1-4** are drawn by this rule; table 5 repeats an earlier set, so the list stops at
  four distinct tables:

  | table | fast classes | polite fast bytes (opcode + data) | polite hazard, N2 | vs M |
  | --- | --- | --- | --- | --- |
  | 1 | mov, dec, rnd, unwall | 19/40 (5 + 14) | 8.30e-5 | 1.06 |
  | 2 | jmp, ignite, wall, unwall | 15/40 (4 + 11) | 6.67e-5 | 0.85 |
  | 3 | dec, jmp, rnd, unwall | 21/40 (4 + 17) | 9.11e-5 | 1.17 |
  | 4 | mov, inc, jmp, wall | 17/40 (9 + 8) | 7.48e-5 | 0.96 |

  Under uniform M, polite's hazard is 40 × 1.95e-6 = 7.8e-5 (mean lifetime about 12.8k
  ticks).

**Normalization.**

- **N2 (recommended): the unweighted mean over the nine class rates equals r.** With four
  fast classes, (4·r_f + 5·r_s)/9 = r and r_f = 30·r_s. This gives r_s = 9r/125 = 1.404e-7
  and r_f = 4.212e-6, the same for every table. The mean over the 255 values, which is the
  expected rate of a random byte from mutation or RND, is 1.93-1.96e-6 in tables 1-4, within
  1.1% of r. Polite's hazard varies by table (0.85-1.17 × M). That variation is part of what
  the tables sample. Reasons: N2 follows the request's "mean rate", and it keeps the rates a
  property of the substrate rather than of the ancestor.
- **N1 (alternative): rescale each table so that polite's mean byte rate is r.** Polite's
  hazard then equals M's 7.8e-5 in every table, as in the step-1 ancestor match (section 2).
  The rates depend on the ancestor and differ by table. (slow, fast) are (1.32e-7, 3.96e-6),
  (1.64e-7, 4.93e-6), (1.20e-7, 3.61e-6) and (1.46e-7, 4.39e-6) for tables 1-4.

**Not chosen.**

- Picking fast ops by analogy, for example making "chemically active" ops fast after Ray.
  No source supports any specific assignment.
- Context-dependent rates, which the request excludes.

### Implementation outline (after agreement)

- **Options.** New optional settings: `decay_table` (0 = off, the default; t ≥ 1 selects a
  table) and `decay_ratio` (default 30). The mean rate comes from `p_hydro`. The settings
  require `hydro_whole` = 1, and `p_dead` must be unset.
- **Hazard.** With two levels, the hazard depends only on the counts of fast and slow bytes
  (n_f, n_s). The thresholds form a 65 × 65 table built by repeated multiplication: first
  n_f factors of (1 − r_f), then n_s factors of (1 − r_s). There is one keyed draw on
  `kWhole` per site, as now.
- **Checks.**
  - With `decay_ratio` 1 the factors are identical, so the chain of multiplications is the
    same as uniform M and the run should reproduce v14 `m195` bit for bit.
  - The default replay digest stays unchanged.
  - A test pins the table draw.

### Runs and measures (after agreement)

Same settings as v15: 96x96, 100k ticks, `ext_write` fill, `p_mut` 0.003, seeds 1-2,
census, no rotation. Tables 1-4 × seeds 1-2 make 8 runs, about 15-20 min. The control is
`m195`, which the uniform case should reproduce.

Measures:

- The replicator census, as before.
- Mean h(x) and mean non-inert length over time, for replicators and for non-replicators.
- Share of non-inert bytes in fast classes over time, overall and in replicators. Random
  bytes have a fast share of 44-45%.
- Durable non-replicators: a fall in mean h(x) among non-replicators that does not appear
  among replicators.

Expected (inference, not measured): in saturated space, births need vacancies, so a lower
hazard lengthens a program's occupancy and its copies per lifetime. The size of the effect
over 100k ticks is not predicted.

### Agreed and implemented

The user agreed to the following:

1. S1: two levels, fast : slow = 30 : 1.
2. Random assignment by tables 1-4, with four fast classes.
3. N2: slow 1.404e-7, fast 4.212e-6.
4. Tables 1-4 × seeds 1-2, with `m195` as the control. `decay_ratio` = 1 must reproduce `m195`
   bit for bit, and the default replay digest must stay unchanged.

The user also asked for a separate report if data bytes are selected first.

Implementation: `decay_table` and `decay_ratio` (revision 84092a3, test 16).

Choices made in measuring, not separately agreed:

- **Opcode bytes** of an evolved program are the offsets where its census founder executed
  an instruction during the 2000-tick trial. The other non-inert bytes count as operand or
  data bytes. For polite this gives 13 and 27, as in the code observations.
- **Control.** Each run prints the class measures under all four tables. Each table's
  control is `m195` with the same seed, measured under that table, so drift under uniform
  rates is measured with the same classification.
- **Substitutions** are also counted at polite's own offsets, by polite's role of the offset
  and by direction between classes. This is direct for programs that keep polite's layout and
  says nothing about programs that do not.
- **Identity runs.** Each table and seed is run once more with `decay_ratio` = 1, and the
  output is compared byte for byte with v15 `m195`.

Results are in the [physub README](../../experiments/physub/README.md) (v16).

## Search record

Two verification passes on 2026-11-17 read the sources above and cached them; the
[reference index](../references/README.md) lists them. Not accessible and not read: the
Toffoli and Margolus 1987 book; Lindahl 1993 and Lindahl and Karlström 1973; the Rouse 1953
and Zimm 1956 originals; Carmesin and Kremer 1988; the Czárán and Szathmáry 2000 chapter;
Szabó et al. 2002; Higgs and Lehman 2015; the Wu and Higgs 2009 article. Hutton 2007 could not
be restored because its archive copy was unreachable.

A third pass on 2026-11-17, for section 6, cached An et al. 2014, Takeuchi, Hogeweg and Koonin
2011, Dorn, Nealson and Adami 2011, and Könnyű, Szilágyi and Czárán 2015. Levy and Miller 1998,
Kaukinen et al. 2002 and Robinson and Robinson 2001 were not cached: their PDF hosts returned
bot challenges, and the open-access full-text services failed. Their abstracts were checked
through NCBI. Not accessible and not read: Lindahl and Nyberg 1972 (one subagent saw it only
in a scan inside a court filing; not used), Radzicka and Wolfenden 1996, and Ofria and Wilke
2004.
