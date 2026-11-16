# Shared-memory probe: what earlier systems actually controlled

Updated: 2026-11-15.

**Status:** Targeted primary-source comparison, not a kernel contract or a new experiment. The [executed probe](coreworld-shared-memory-probe.md) supplies the observations; the sources below supply historical mechanisms. Proposed controls are unexecuted. A separate source/log audit corrected that record: 140 files represent 130 distinct seed/configuration tuples; the review appendix plots ten archived round-3 records.

The closest precedents are unusually specific: Tierra documented a division gate against empty offspring; Avida explicitly warned that birth-only replacement can preserve a population that has lost replication; Coreworld's authors reported seeded programs losing reproduction through noise and mutual overwriting. These are different problems, and earlier systems controlled them with different mechanisms. Their existence does not establish that TIDE must adopt any particular combination.

## Source identity and access

Page numbers below are **one-based PDF pages**, with printed pages separately identified. Existing PDFs were read from the local cache, not downloaded again.

The newly retrieved complete volume is now [cached locally](../references/pdf/langton-et-al-1992-artificial-life-ii.pdf); its unmodified bytes and third-party provenance are recorded in the reference manifest. The HTML manual remains a web source, not a fabricated PDF original.

| ID | Primary source and inspected location | Access and scope |
| --- | --- | --- |
| C90 | Rasmussen, S., Knudsen, C., Feldberg, R., and Hindsholm, M. (1990). *The coreworld: Emergence and evolution of cooperative structures in a computational chemistry*. Physica D 42:111-134. [Publisher / DOI](https://doi.org/10.1016/0167-2789(90)90070-6). | Publisher abstract inspected; full article not obtained. No claims about its detailed instruction implementation are made from the abstract. |
| C91 | Rasmussen, S., Knudsen, C., and Feldberg, R. *Dynamics of Programmable Matter*. In C. G. Langton, C. Taylor, J. D. Farmer, and S. Rasmussen (eds.), *Artificial Life II*, SFI Studies in the Sciences of Complexity X, Addison-Wesley, pp. 211-254. [Published-volume scan](https://gwern.net/doc/ai/1992-langton-artificiallife-2.pdf#page=116). | Direct author text, chapter colophon 1991; volume copyright 1992. Whole-volume PDF pp. 116-138 contain the chapter. Public third-party mirror, not author/institution hosting; no open license verified. No chapter DOI verified. |
| R91 | Ray, T. S. (1991). *An Approach to the Synthesis of Life*. Same edited volume, pp. 371-408. [Author-hosted PDF](https://tomray.me/pubs/alife2/Ray1991AnApproachToTheSynthesisOfLife.pdf); [local cache](../references/pdf/ray-1991-synthesis-of-life.pdf). | Published chapter, author-hosted copy. Relevant PDF pp. 8-10, 23, 32; printed pp. 378-380, 393, 402. |
| R98 | Ray, T. S. *Documentation for the Tierra Simulator*, Tierra V5.0, dated 17 March 1998. [Author's technical documentation](https://tomray.me/pubs/doc/index.html). | HTML, sections 7 and 8.4; later than R91. Its implementation details must not be silently backdated to every 1991 run. |
| A04 | Ofria, C., and Wilke, C. O. (2004). *Avida: A Software Platform for Research in Computational Evolutionary Biology*. Artificial Life 10:191-229. [Author-hosted PDF](https://cse.msu.edu/~ofria/pubs/2004OfriaEtAl.pdf); [local cache](../references/pdf/ofria-wilke-2004-avida.pdf). | System authors' article. Sections 2.2.3, 3.2, 5.2 and Appendix A1.2: PDF pp. 9-10, 13-14, 21-22, 28; printed pp. 199-200, 203-204, 211-212, 218. |
| S21 | Hickinbotham, S. J., Stepney, S., and Hogeweg, P. (2021). *Nothing in evolution makes sense except in the light of parasitism: evolution of complex replication strategies*. Royal Society Open Science 8:210441. [Institutional repository PDF](https://research-portal.uu.nl/ws/files/110685157/rsos.210441.pdf); [local cache](../references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf). | Published article with one repository cover page. Sections 2.1-2.2, 5.1, 5.3: PDF pp. 3-4, 13-15; article pp. 2-3, 12-14. |
| S10 | Hickinbotham, S., Clark, E., Stepney, S., Clarke, T., Nellis, A., Pay, M., and Young, P. *Specification of the Stringmol chemical programming language version 0.2*. Technical Report YCS-2010-458. [Institution-hosted specification](https://www.cs.york.ac.uk/library/reports/2010/YCS/458/YCS-2010-458.pdf); [local cache](../references/pdf/stringmol-specification-v0.2-ycs-2010-458.pdf). | Technical specification, not the S21 experiment. Sections 4, 10.6-10.8, 11.2: PDF pp. 7, 21-24; printed pp. 6, 20-23. |

## The historical mechanisms

### Coreworld/Venus: resource-limited execution, not protected organisms

C91 section 3.1 allows `SPL` to create execution pointers without copying. Insufficient local renewable execution resources or `DAT` delete pointers; random pointer injection supplies new ones. Venus I computes effects from a shared memory snapshot, resolving writes by queue position; Venus II updates sequentially. [C91, printed pp. 222-225, PDF pp. 122-123](https://gwern.net/doc/ai/1992-langton-artificiallife-2.pdf#page=122).

Section 4.2 reports supplied self-replicators typically malfunctioning after about 200 iterations under noise and mutual overwriting. Section 5 describes simple COPY takeover in Luna, proposing execution resources or finite pointer lifetimes as interventions. These observations do not prove ownership necessary. [C91, printed p. 229 / PDF p. 125; printed pp. 240-241 / PDF p. 131](https://gwern.net/doc/ai/1992-langton-artificiallife-2.pdf#page=125).

Thus the local probe shares a failure mode with this work, but is not a reproduction of Venus: it omits the local execution-resource system and external pointer supply and uses different geometry, instructions, and scheduling.

### Tierra: ownership, division checks, and pressure-driven reclamation

R91 gives a creature exclusive writes to its body and one allocated daughter block, while allowing foreign reads and execution. Division transfers the daughter block and grants it an instruction pointer. Death deallocates memory and removes the CPU but leaves bytes in the soup. The early reaper responds to memory pressure and orders victims by age and execution errors; the abbreviated main loop checks memory pressure after time slices. Background mutation is also present. This is not the probe's CPU-count cap. [R91, PDF pp. 8-9 and 32](../references/pdf/ray-1991-synthesis-of-life.pdf#page=8).

R98 adds the directly relevant warning: `MovPropThrDiv` checks movement into daughter memory because otherwise mutants produce empty cells. The documented count can repeatedly write the same location; it does **not** establish distinct-address coverage. `MinCellSize` also limits tiny offspring. Section 7's prose inconsistently uses mother size while section 8.4 uses daughter size as the threshold denominator; source-code inspection would be needed to resolve that detail. Allocation and copy evidence are separate checks. [R98, sections 7 and 8.4](https://tomray.me/pubs/doc/index.html).

### Avida: explicit division eligibility and an acknowledged death trap

A04 separates allocation from copying and division eligibility. Newly allocated memory may contain default instructions or random code. `h-divide` checks allocation, genome size, executed-parent fraction, and copied-offspring fraction; failing the checks prevents birth. The article is internally inconsistent about the fractions: section 2.2.3 says one-half, while Appendix A1.2 says 70%. Neither should be treated as a universal Avida constant. [A04, PDF pp. 9-10 and 28](../references/pdf/ofria-wilke-2004-avida.pdf#page=9).

Default death is replacement at birth. Section 3.2 explicitly warns that a population can lose self-replication yet persist without independent death; optional death counts executed instructions, either absolutely or relative to genome length. Section 5.2 tests offspring and descendant viability with a timeout, while acknowledging that solitary tests miss interactions. [A04, PDF pp. 14 and 21-22](../references/pdf/ofria-wilke-2004-avida.pdf#page=14).

### Stringmol: bounded reactions, decay, and functional classification

S21 permits effects only within a bound pair and its products. New products require a neighboring empty cell or are discarded. Uniform per-timestep stochastic decay frees space independently of births. Nevertheless 12 of 20 spatial runs went extinct; eight reached two million steps. These outcomes establish neither guaranteed persistence nor that decay alone explains survival. [S21, sections 2.1-2.2 and 5.1, PDF pp. 4, 13-14](../references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf#page=4).

The underlying cleave operation splits off existing sequence; it is not an unrestricted command that attaches another CPU to arbitrary public memory. This does not imply that every cleaved sequence was freshly copied. The earlier specification's decay and energy model must not be conflated with S21. [S10, sections 4, 10.7-10.8, PDF pp. 7, 22-23](../references/pdf/stringmol-specification-v0.2-ycs-2010-458.pdf#page=22).

S21 classifies reactions with mutation disabled: determine which sequence increases in number and examine both orientations of a pair. Parasitism is partner-relative. This is an analysis procedure, not a physical role assigned to strings. [S21, section 5.3, PDF p. 15](../references/pdf/hickinbotham-et-al-2021-spatial-stringmol.pdf#page=15).

## Observations mapped to prior mechanisms

The final two columns are inferences and proposed experiments, not findings from the cited sources.

| Observed issue in the probe | Exact historical mechanism | What the comparison permits us to infer | Discriminating next control |
| --- | --- | --- | --- |
| `spawn` loops create CPUs with almost no writing | C91 `SPL` permits this, but execution competes for local renewable resources. R98 has a movement-count division gate; A04 has allocation/copy/execution gates. | CPU creation, spatial allocation, and construction evidence are independent choices. Earlier systems did not solve the same problem in one universal way. | Hold ownership and death fixed; compare allocation-only, movement-count, and distinct-address coverage eligibility. Include repeated writes to one address as a negative control. |
| Birth collapse leaves a persistent CPU census | A04 explicitly documents this birth-replacement trap and offers instruction-age death. C91 deletes pointers for insufficient local resources or `DAT`; S21 uses per-step decay. | Independent removal can expose loss of reproduction; it can also turn persistence into extinction. A healthy CPU census alone is inadequate evidence of a reproductive population. | With births disabled after a snapshot, measure CPU/occupied-site decay under each policy; separate instruction-age, round-age, and stochastic decay clocks. |
| Writes overwrite potentially functional code | R91 protects allocated body and daughter blocks but allows foreign execution; C91 reports overwrite-induced loss of seeded replication. | Protection is one successful architecture and overwrite fragility is documented. These papers do not isolate protection as the sole cause of evolutionary persistence. | Cross body-write protection with allocation-writer exclusivity, keeping birth eligibility, death and mutation constant. |
| A full protected lattice stalls construction | S21 rejects products without local vacancy and replenishes vacancies through decay. R91 deallocates memory under pressure. | Empty-space supply and destination policy are causal variables separate from write permission. Birth replacement is another possible route to turnover if constructing offspring does not first require a vacancy. | Fix a vacancy process, then compare blind targeting with explicit free-space selection. Record denied attempts, waiting time, and usable contiguous capacity. |
| `claimed` raises fidelity while births slow | R91 combines protection with allocation, placement and reclamation; A04 constructs offspring in private VM memory before replacing a world cell. | The systems compete for different things. Probe throughput changes may reflect blind retries, delayed access to vacancies, or longer lifetimes rather than the intrinsic cost of accurate replication. | Compare the same ancestor with and without vacancy sensing, using a common death hazard and birth-time accounting. |
| Byte fidelity and genotype counts disagree with apparent persistence | A04 uses descendant viability tests; S21 tests pair reaction outcomes with mutation off. R91 also reports manually constructed partners unable to replicate alone but viable together (PDF p. 23). | Equality of sites measures copying accuracy, not autonomous or ecological reproduction. A viable lineage can change sequence; a faithful copy can be a non-replicator or require a partner. | Replay sampled genotypes and observed pairs without mutation, then descendants; report bounded-time sustained reproduction, partner dependence and exact-copy frequency separately. |

## The allocation implication that the probe does not establish

The probe's initial interpretation said allocation before division already supplies the property of `spawn=written`. That does not follow from allocation alone; the audited record now corrects this claim.

A counterexample is sufficient: reserve an unowned region containing old bytes, perform no writes, and divide into it. If division checks only reservation ownership, the new CPU runs old code without construction. Initializing the region to inert bytes makes that less useful but still does not prove the parent copied anything; initializing with executable defaults or recycled code changes the opportunity again.

Three distinguishable conditions are therefore needed in discussion:

1. **Reservation:** the parent has an exclusive spatial claim.
2. **Construction evidence:** some specified amount of work or address coverage has occurred since a defined event.
3. **Functional reproduction:** the resulting code can contribute to further reproduction in a stated environment.

None implies the next. Even full distinct-address coverage can copy arbitrary permitted source bytes or be followed by subsequent overwriting. It supplies a provenance/work criterion, not self-copying identity or viability. R98's warning about repeated writes is especially useful for distinguishing work-count and coverage rules. A04's initialized allocation likewise shows why reserving memory is not the same transition as constructing offspring.

An explicit future contract would have to specify the eligibility event, counters or coverage set, resets, permitted writers, intervening overwrites, mutation, target changes, and failed-operation effects. This note proposes no selected values and no implementation.

## Confounds that should remain visible

- **The outcome metric changes with the model.** A CPU flood can indicate process replication without fresh code construction. It is a failure relative to the probe's intended code-reproduction question, not proof that all process reproduction is illegitimate.
- **Pressure is not age.** Ray's global memory-pressure reaper, the probe's global CPU cap, local displacement, executed-instruction age, and wall-round age are different interventions. Calling all of them mortality conceals their different triggers and selection pressures.
- **Copies are attributed at particular times.** If fidelity compares destination bytes with the parent's current site at birth, foreign writes can change either during construction. Log source bytes when read, final target bytes, successful coverage, and intervening writes before interpreting low fidelity as faulty copying machinery.
- **Round 3 bundles mechanisms.** Body protection and single-writer allocation change together; ownership also changes vacancy access and the main route of death. The observed fidelity/throughput tradeoff cannot identify their separate effects.
- **The ancestor is not policy-neutral.** Blind random targeting was designed for another permission regime. Denied writes that still consume instruction steps affect gestation time and its relation to the fixed age limit.
- **Tail variation is not function.** Neutral changes in the inert tail inflate genotype counts and lower exact-ancestor share. Report functional replay alongside these statistics rather than interpreting sequence richness as adaptive diversity.
- **Scheduling remains untreated.** C91 distinguishes snapshot and sequential memory effects. The probe's birth-order execution can confer systematic read/write advantages; changing protection does not remove that confound. Merely describing CPUs as simultaneous is insufficient to establish two-phase synchronous semantics.
- **Persistence is conditional.** Five seeds, one ancestor and one nonzero mutation rate cannot establish necessity or sufficiency across instruction sets. S21's extinctions are a useful reminder that mortality and locality are compatible with failure.
- **Counts and diagnostics were audited separately.** The record now distinguishes 140 output files from 130 distinct seed/configuration tuples, corrects full-occupancy and death-cause overclaims, and limits replay evidence to the incomplete digest actually stored. No runs were re-executed during this follow-up.

## Most informative follow-up order

1. Audit run inventory and metric definitions; snapshot evolved code and enough execution state to replay the claimed floods and freezes.
2. Test construction independently of ownership: allocation-only versus counted writes versus distinct-address coverage, with a fixed death policy and mutation disabled for mechanism checks.
3. Test turnover independently of reproduction: suppress new births from the same snapshot and observe each death clock. Distinguish extinction from renewed reproduction.
4. Split the two protections in `claimed` and control vacancy selection before comparing throughput.
5. Replay sampled genotypes, descendants, and relevant neighbor pairs without mutation. Add perturbation or partner-removal tests before labeling ecological strategies.
6. Only then repeat the informative contrasts with TIDE's proposed synchronous schedule and a mutation-rate sweep.

These are separate experiments. They should not be installed together as an assumed historically validated solution.
