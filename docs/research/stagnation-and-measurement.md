# Stagnation, ecological feedback, and measurement

Updated: 2026-11-15. Bounded first pass for roadmap directions 4 and 5.

**Status:** Source findings and candidate research proposals, not agreed kernel requirements. No TIDE experiments were run; the fresh C++ kernel does not yet exist. The supplied-ancestor, local-address VM and synchronous execute/resolve decisions remain the starting point.

## What this pass establishes

Failure to sustain innovation has several observable outcomes: extinction, cessation of heritable behavioral novelty in a surviving population, repeated cycling, and failure of a particular complexity measure to increase. Extinction is separate from persistent-but-stagnant runs. Neither a large genotype count nor a rising maximum program length establishes sustained innovation. Responsive ecological feedback is a plausible experimental mechanism, with strong substrate-specific precedents; its benefit in TIDE is untested.

## Primary evidence

### S1. Size growth can occur without measured complexification

Russell K. Standish. 2003. *Open-Ended Artificial Evolution*. *International Journal of Computational Intelligence and Applications* 3(2):167-175. [DOI](https://doi.org/10.1142/S1469026803000914) | [Read version: arXiv:nlin/0210027v1, submitted 2002](https://arxiv.org/pdf/nlin/0210027v1) | [Local PDF](../references/pdf/standish-2003-open-ended-artificial-evolution-v1.pdf).

- **Read:** Full-text sections 3-5, especially section 4, Table 1 and Figure 1; PDF pages 4-8, cross-checked in the cached PDF during integration. Web screenshot rendering was unavailable.
- **Finding:** In one size-neutral run of six billion executed instructions, genome length rose from 80 to 526 while the reported complexity measures showed no increase. Phenotypes were distinguished through pairwise tournaments against organisms sampled from the run. The author explicitly notes context sensitivity and the finite run's limitations.
- **Limit:** This is evidence about one setup, phenotype definition, and observation horizon; it does not establish that every Tierra configuration must converge to short genomes or that all later innovation is impossible.

### S2. Parsimony changes outcomes; relaxing it is not a demonstrated cure

Russell K. Standish. 2004 workshop contribution, available as a 2006 preprint. *The influence of parsimony and randomness on complexity growth in Tierra*. *ALife IX Workshop and Tutorial Proceedings*, p. 51. [Bibliographic record](https://arxiv.org/abs/nlin/0604026) | [Read version: arXiv:nlin/0604026v1](https://arxiv.org/pdf/nlin/0604026v1) | [Local PDF](../references/pdf/standish-2004-parsimony-randomness-tierra-arxiv-v1.pdf).

- **Read:** Full-text “Measurement of Complexity in Tierra,” “Results,” and “Discussion”; Figures 1-3, PDF pages 2-5, also checked in the cached PDF.
- **Finding:** The pilot sweeps `SlicePow` from 0.9 to 1.0 under two randomness sources. Intermediate settings generated some organisms with estimated complexity above the ancestor; completely relaxed parsimony produced early termination. The discussion explicitly reports no evidence of open-ended complexity growth and says the methodology and significance analysis need strengthening.
- **Limit:** The entropy-source difference was not established as statistically significant. The theoretical discussion of algorithmic information is not evidence that external entropy cures stagnation. It does not justify abandoning TIDE's replayable seeded randomness.
- **TIDE inference:** Keep length, replication cost, and measured functionality separate; vary an agreed cost mechanism independently before explaining a plateau by “selection for short programs.” `SlicePow` is a Tierra parameter, not a proposed TIDE instruction.

### S3. New organisms creating opportunities is a testable hypothesis

L. B. Soros and Kenneth O. Stanley. 2014. *Identifying Necessary Conditions for Open-Ended Evolution through the Artificial Life World of Chromaria*. *ALIFE 14*, pp. 793-800. [DOI](https://doi.org/10.7551/978-0-262-32621-6-ch128) | [Public institutional PDF](https://wiki.santafe.edu/images/9/9c/Soros_alife14.pdf).

- **Access/read:** Indexed primary full-text extracts from “Hypothesized Necessary Conditions,” results/Figures 5-6, and “Discussion” were read. Direct PDF retrieval timed out; this is partial full-text access, not complete PDF inspection or abstract-only reading.
- **Finding:** Four necessary conditions are hypothesized. The preliminary experiment controls one: whether individuals create new opportunities for others to satisfy the reproduction criterion. Removing visibility of other individuals inhibits that mechanism; standard and control Chromaria runs differ in behavioral/world growth over 50,000 reproductions.
- **Limit:** This single-domain ablation supports a mechanism within Chromaria; it does not prove universal necessity or sufficiency of the four conditions. Its color-matching reproductive criterion is designed. TIDE need not import an additional task, score, or explicit ecological category to study opportunity creation through its own memory and space rules.

### S4. Responsive coevolution can matter beyond exposure to diverse opponents

Luis Zaman, Justin R. Meyer, Suhas Devangam, David M. Bryson, Richard E. Lenski, and Charles Ofria. 2014. *Coevolution Drives the Emergence of Complex Traits and Promotes Evolvability*. *PLOS Biology* 12(12):e1002023. [Publisher full text and DOI](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1002023) | [Data and configurations](https://doi.org/10.5061/dryad.485qq) | [Local PDF](../references/pdf/zaman-et-al-2014-coevolution-complex-traits.pdf).

- **Read:** “Parasites Drive Greater Host Complexity,” “Parasites Retain ‘Memory’ of Previous Hosts,” subsequent results, and methods including “Freeze and Replay Experiments”; key claims also checked in the cached PDF, pages 3-5 and 8.
- **Finding:** Across 50 replicates per main treatment, the most complex supplied logic task evolved in 17 coevolution runs and zero parasite-free runs. Freezing or replaying parasite genotypes weakened the effect compared with responsive coevolution. Twelve coevolution runs lost their parasites; those runs were generally retained in analysis.
- **Limit:** Complexity means minimum NAND operations for the most complex task performed, from nine supplied tasks. Tasks have equal resource rewards here, but reproduction still requires task performance; infection and CPU transfer are explicit model rules. This is neither task-free ecological emergence nor evidence of indefinite OEE.
- **TIDE inference:** Distinguish feedback from mere neighbor diversity through counterfactual replay, if evolved interactions arise. Diagnose relationships from consequences; do not add causal host/parasite labels.

### S5. MODES gives diagnostics, with choices that must remain visible

Emily L. Dolson, Anya E. Vostinar, Michael J. Wiser, and Charles Ofria. 2019. *The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems*. *Artificial Life* 25(1):50-73. [DOI](https://doi.org/10.1162/artl_a_00280) | [Author PDF](https://web.cse.msu.edu/~dolsonem/pdfs/modes_paper.pdf) | [Author repository](https://github.com/emilydolson/MODES-toolbox-paper) | [Read manuscript](https://raw.githubusercontent.com/emilydolson/MODES-toolbox-paper/master/paper/dolson.tex).

- **Read:** Author manuscript methods/results, then published sections 3.1-3.2 (pp. 56-60) through the 24-page author-hosted PDF during integration. Relevant published methods match the manuscript. No implementation was run or audited.
- **Finding:** MODES separates change, novelty, complexity, and ecology; complexity uses maximum informative-site count, ecology uses filtered diversity. Descendant persistence does not eliminate all drift; informative-site tests can miss epistasis.
- **Limit:** Component definitions, contexts, and filter times affect these operational hallmarks. Original Bedau papers were not independently read here.

The existing cached [Taylor et al. 2016 workshop synthesis](../references/pdf/taylor-et-al-2016-open-ended-evolution.pdf), especially section 3, provides complementary conceptual context: novelty, organism complexity, interaction complexity, and major transitions are separable concerns. It is a synthesis, not an additional controlled mechanism experiment.

## Candidate minimal measurement set for R2/R3

These are analysis proposals. They should not reward, preserve, or select organisms inside the kernel.

| Quantity | Candidate operational observation | Counterexample / interpretation limit |
| --- | --- | --- |
| Viability | Population, occupied/allocated space, births, deaths, failed divisions, and replication latency versus VM steps and executed instructions | A surviving population can be behaviorally static; occupied space can be dead code |
| Diversity | Exact-byte genotype richness and abundance entropy; separately, richness of replay-defined behavioral signatures | Neutral junk and spatial isolation can maintain many genotypes without new strategies |
| Novelty and turnover | Count first appearances of genotypes and behavioral signatures separately; retain the complete sampled history to distinguish recurrence | A two-strategy cycle has turnover but no later first appearances; mutation can inflate byte novelty |
| Lineage persistence | Descendants after several declared lags; lineage survival curves, with generation depth and VM time both recorded | Drift, hitchhiking, or geographical separation can preserve a lineage; persistence does not prove adaptation |
| Functional complexity | Program length alongside contextual informative-site proxies from replication perturbations; report distribution and maximum | These estimate functional dependence under tested conditions, not literal algorithmic complexity; redundancy and epistasis can alter rankings |
| Ecological interaction | Mutation-free paired replay: compare each focal program alone and with another, measuring births, lifetime reproduction, and execution/data dependence | Co-occurrence and diverse types do not establish an interaction; pair tests can miss effects requiring three participants |

For an optional MODES adaptation, compare consecutive filtered component sets for change, and current against all earlier filtered sets for novelty. [S5 methods](https://raw.githubusercontent.com/emilydolson/MODES-toolbox-paper/master/paper/dolson.tex) TIDE-specific proposal: retain raw results and finite replay-context definitions alongside these counts.

**TIDE-specific safeguards (proposals):**

1. Define the observation window, sampling interval, persistence lags, and analysis revision before examining outcomes. Report sensitivity to lags and context panels. A well-mixed coalescence heuristic is not automatically valid on TIDE's lattice.
2. Treat the final lag-length portion of a run as right-censored for persistence; report these observations as unresolved, not failed lineages. Extinction is a separate observed outcome.
3. In perturbation replays, preserve addressing/layout where possible; deleting an instruction can shift every later offset. Do not claim an indispensable-site count measures algorithmic complexity. Repeat across empty, ancestor-neighbor, and sampled evolved-neighbor contexts; report individual and pairwise perturbations separately if used.
4. For relationship diagnosis, hold initialization, placement, permissions, and replay duration fixed. Compare A alone, B alone, and A+B. Record effects on each participant independently, plus instruction and copy provenance. Interaction signs may change with density or context.
5. Before R3, operationalize “stagnation” as no newly persistent behavioral signature within a declared window, with stable recorded observables; retain genotype turnover, cycling, and complexity plateau as separate descriptors. The window and signature definition are candidate analysis choices, not settled acceptance thresholds.
6. Compare multiple seeds and report every run, including extinction, unfinished classifications, and plateaus. Extend horizons or system sizes as separate experiments. A finite trajectory or a fitted unbounded growth curve cannot prove indefinitely continuing OEE; a fixed finite state space also limits literal unbounded novelty.

## Trace data to preserve before evolution runs

R2's hand-written mutation-free programs can validate these observations before R3. Proposed trace categories are independent of any final event schema:

- **Replay identity:** seed, complete named configuration, ancestor bytes, kernel revision/build identity, step/time definition, and periodic state hashes/checkpoints.
- **Lifecycle:** stable individual IDs, birth/division initiator ID, child ID, exact birth bytes/hash, birth/death step and reason, site, allocation/reclamation changes, and mutation records. Preserve failed operations and conflict-resolution outcomes.
- **Three provenance channels:** CPU owner; fetched-instruction address/source and memory version; copied-byte read address/source and write destination/version. Record whether each source was owned, unowned, or absent, using physical state rather than role labels. A neighbor instruction source and a neighbor data source are different observations.
- **Ancestry versus material origin:** maintain division/lifecycle genealogy separately from byte-donor provenance. Borrowed copying can give a child material from a program other than the division initiator; neither graph substitutes for the other. Record self-modification and overwrites so a source hash can resolve to the bytes actually read.
- **Analysis inputs:** sampled population multiplicities and positions, genotype archives including extinct variants, local replay contexts, elapsed CPU work, and enough event/checkpoint data to reconstruct retrospective lineages. Sampling-only archives must state that short-lived types can be missed.

Detailed instruction traces can be restricted to deterministic replay windows to contain volume, provided checkpoints retain all state needed to reproduce them. Birth/death and provenance summaries need enough identity to prevent recycled addresses from being mistaken for continuing organisms. No new persistent data format is approved by this note.

## Candidate research questions

1. **Does neighbor-derived replication support persistent behavioral diversification, or mainly accelerate simplification?** Compare the agreed VM with one explicitly isolated restriction on neighbor instruction fetch or neighbor data reading; change only one permission dimension per comparison, using an ancestor viable in both. Measure replay-defined strategies, persistence, births, and extinction. Grounding: S1-S2's efficiency/complexity distinction and S4's ecological-feedback mechanism. A negative result is continued byte novelty with unchanged replication behavior. The permission ablation is a proposed experimental configuration, not a reversal of the chosen kernel.
2. **Do retained unowned bytes create heritable replication opportunities after their producer dies?** Compare otherwise matched reclamation policies after those policies are agreed. Test archived programs with and without the recorded residual code; measure causal changes in copying/fetch and reproductive output. Grounding: S3's opportunity-creation hypothesis, with TIDE's specific memory substrate as the test case. A counterexample is residual code merely blocking space or feeding nonheritable one-off copies. No claim of a new field-wide mechanism is made.
3. **Is apparent innovation sustained by responsive interactions rather than static environmental heterogeneity?** If R3 produces interaction-dependent strategies, compare their replay against responsive neighbors, frozen archived neighbors, and a prerecorded neighbor sequence, matching exposure and resource/space changes where possible. Grounding: S4's freeze/replay controls. This is a later analysis intervention, with confounding documented if exposure cannot be matched. If static replay gives the same outcome, responsive feedback is not supported as the explanation.

Questions 1-2 are compatible first-kernel candidates; question 3 requires evolved interactions and more analysis control. None is an agreed RQ, and none claims novelty over unsearched literature. None studies random-origin replication.

## Search and screening record

Search date: **2026-11-15**. Public web search followed by primary arXiv, publisher, institutional, and author-repository inspection; cached PDFs/manifest were checked first. Exact queries used (including unsuccessful narrowing searches):

```text
Standish 2003 Open-ended artificial evolution Tierra complexity
Soros Stanley identifying necessary conditions open ended evolution 2014
Zaman 2014 coevolution drives emergence complex traits promotes evolvability host parasite
Dolson MODES toolbox measuring open ended dynamics 2019
"MODES" "Dolson" 2019 open-ended
"Identifying Necessary Conditions" "Soros" 2014 Stanley pdf
"Open-Ended Artificial Evolution" Standish 2003 doi
"modes_paper.pdf" Dolson
"The MODES Toolbox" github
"Soros" "Stanley" "Chromaria" pdf 2014 site:cs.ucf.edu
"Soros_alife14.pdf"
"modes_paper.pdf" "persistence"
"Soros_alife14.pdf" "Condition"
"Identifying Necessary Conditions" Chromaria pdf site:mit.edu
site:wiki.santafe.edu/images/9/9c/Soros_alife14.pdf "Condition 1"
site:wiki.santafe.edu/images/9/9c/Soros_alife14.pdf "Condition 2"
site:wiki.santafe.edu/images/9/9c/Soros_alife14.pdf "Condition 3"
site:wiki.santafe.edu/images/9/9c/Soros_alife14.pdf "Condition 4"
"Soros_alife14.pdf" "Condition 2:"
"Soros_alife14.pdf" "Condition 3:"
"Soros_alife14.pdf" "Condition 4:"
"Soros_alife14.pdf" "Results"
Soros Stanley Chromaria "Condition 2" minimal criterion
Soros Stanley Chromaria "Condition 3" individuals
Soros Stanley Chromaria "Condition 4" individuals
Soros Stanley Chromaria 2014 condition self reproduction results
"soros_alife14.pdf" -site:bestofama.com -site:wiki.santafe.edu -site:reddit.com
"Identifying Necessary Conditions" "pdf" "Soros" "Stanley" -site:ai.updf.com -site:wiki.santafe.edu
"Identifying Necessary Conditions" site:stars.library.ucf.edu
"Chromaria" "Soros" "pdf" site:lisabentonsoros.com
"Soros" "alife14" "pdf" -site:wiki.santafe.edu -site:researchgate.net -site:scribd.com
"Identifying Necessary Conditions" "kenstanley"
"Identifying Necessary Conditions" "lisabentonsoros"
"Identifying Necessary Conditions" "eplex"
site:web.cse.msu.edu/~dolsonem/pdfs/modes_paper.pdf "Filtering" "Metrics"
site:web.cse.msu.edu/~dolsonem/pdfs/modes_paper.pdf "Change Metric" "Novelty Metric"
```

- **Retained:** The five papers S1-S5 above. Standish's 2004/2006 pilot is distinct from the 2003 article; publication and repository dates are not conflated.
- **Screened/deferred:** Standish's *Some Techniques for the Measurement of Complexity in Tierra* (1999; arXiv posted 2000), Soros's 2018 dissertation, the later OEE4 workshop abstract *Necessary Conditions for Open-Ended Evolution Empirically Validated in Chromaria*, and the 2016 minimal-criterion strictness paper. Landing pages or indexed extracts only; not used to claim independently verified mechanisms or results here.
- **Not independently reviewed:** Original Bedau activity-statistics papers, major-transition studies, and Hickinbotham/Stepney detection work. The later Bohm/Zhang/Dolson MODES assessment is an additional next-reading lead identified during integration, not evaluated evidence here. The bibliography is not exhaustive.
- **Access limits:** Soros 2014 direct PDF timed out; the UCF repository records its unavailability. The old `cse.msu.edu` MODES address is not the working author PDF endpoint; use `web.cse.msu.edu` above. Its published PDF was readable through web extraction, while local-download TLS handshakes failed. No secondary commentary, search-engine synthesis, or third-party implementation is used as scientific evidence.
- **Cache handoff:** Metadata covers all five new primary sources with known public PDF endpoints. Both Standish papers and Zaman were cached and read locally during integration. Local PDF retrieval remained unresolved for Soros and MODES; Soros retains partial-text status, while MODES has published-PDF methods verification. See the manifest for final retrieval status.

Skill used: `pdf` for PDF-reading and evidence-handling guidance. No kernel code, fitness reward, experiment, or causal ecological label was added.
