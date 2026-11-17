# Decay Form and Whole-Site Mobility: Sources and Candidate Designs

Updated: 2026-11-17. Status: candidate designs for `experiments/physub/`, none agreed. Nothing
here applies to the kernel contract.

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

## 4. Proposed next steps (not run)

1. Decay form: M with uniform r = 1.95e-6 against `dead0` (`ext_write` fill, seeds 1-2, 96x96,
   100k ticks, census). Only the form changes.
2. Mobility, once the design is agreed: a mechanism check with mutation off (polite alone,
   48x48, p_rot scan) counting completed intact copies and misdirected writes; then census
   runs at two or three rates.
3. Per-op spread and size-dependent mobility only after agreement on how values are chosen.

## Search record

Two verification passes on 2026-11-17 read the sources above and cached them; the
[reference index](../references/README.md) lists them. Not accessible and not read: the
Toffoli and Margolus 1987 book; Lindahl 1993 and Lindahl and Karlström 1973; the Rouse 1953
and Zimm 1956 originals; Carmesin and Kremer 1988; the Czárán and Szathmáry 2000 chapter;
Szabó et al. 2002; Higgs and Lehman 2015; the Wu and Higgs 2009 article. Hutton 2007 could not
be restored because its archive copy was unreachable.
