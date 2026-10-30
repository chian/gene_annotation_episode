# Experimental scoring research: first comparative batch

This is research for W04 part 2. The numerical sheet and its full compilation
are not settled. Part 3 remains dependent on that design. The original corpus,
evidence-axis list, production readers and annotation-credit function are not
changed by this report.

## Verified coverage

The three lane files cover 142 distinct groups and 149 retained record locators,
without missing or overlapping groups. Root checked the group pointers against
case_records.json and each retained record's original locator. The current
statuses are 121 corpus-reanalysis groups and 21 groups with new primary section
reading. Those 21 groups use 20 distinct experimental papers plus one correction
notice. CsiD/LhgO share a paper; the BioY correction is not another experiment.

The lane summaries specify exactly which Methods/Results, figures and tables
were read. A new read of one paper does not turn the other papers in its case
group into new reads. Historical abstract-only cases and failed retrievals retain
their limits. No raw experimental datasets were reanalysed in this batch.

## Findings that change the sheet

| Scoring question | Concrete contrast | Required distinction |
| --- | --- | --- |
| What result bears on which inference? | PopZ SPR gives Kd20nM for binding; origin tethering also needs the cellular perturbation/imaging experiments. | The same measurement has different relevance to binding and a broader physiological mechanism. |
| Is the activity attributed to the correct protein? | HFP preparations show real sugar isomerization, but 4/5 other preparations also show it and MS identifies host RpiA. | Chemical identity and protein attribution need distinct assessment. Orthogonal measurement of a contaminant remains the same attribution problem. |
| Does the perturbation isolate the proposed molecular property? | YeaG K116A fails rescue at64% WT abundance; K426A is at100% WT abundance. | A failed named catalytic mutant is not a selective test of catalysis unless abundance/folding/other relevant effects are addressed. |
| Does the measured range constrain the inferred quantity? | FrsA tests0.05–6.0mM substrate yet reports Km18.6±1.3mM. CysQ cannot confirm low-substrate initial-rate linearity. | Numerical precision, measurement validity and design coverage are different. Limited range is not by itself proof that the fit is invalid. |
| Which component determines a coupled assay's output? | Changing CofD while holding CofC fixed changes the product mixture. | Pair-level product fractions cannot be assigned as isolated upstream-enzyme specificity. |
| Has the defining operation completed? | Binding, a covalent adduct or cofactor half-reaction can occur without the expected full product. | A strong partial reaction can support that event while leaving complete turnover unestablished. |
| Did rescue repair the proposed mechanism? | YihI improves growth without restoring the measured GTPase defect; ThyA replacement needs FolA for near-WT growth and DNA labeling. | Rescue, biochemical repair, chemical equivalence and native responsibility are different inferences. |
| Are results comparable before scoring consistency? | YeaG shorter regrowth lag and worse later survival; BioY long accumulation versus initial-rate affinity. | Different endpoints/time windows are not contradictory repetitions. |
| Is a negative result capable of testing the proposed absence? | MurJ access controls and HemJ positive/blank controls address different reasons for no signal. | Detection limits, substrate access, partner availability and assay competence condition negative evidence. Unknown sensitivity is not exact zero activity. |
| What transfers to the target system? | Engineered exported TrxA has partner/dose-dependent oxidant activity; ComF dependence changes with sulfide and passage. | Sequence identity alone cannot transfer engineered localization, dosage or environmental dependence. |
| What is independently replicated? | CsiD biological and technical duplicates, shared subunit preparations, repeated readouts and mutant panels. | Record experimental units and shared preparation/data dependencies before counting independent support or precision. |
| Which weakness does another experiment resolve? | CsiD product/stereochemical identification resolves O2-readout ambiguity; FtsW partner/catalytic substitutions resolve attribution. | Complementarity changes a specific component of the interpretation. It is not a generic experiment-count bonus. |

These are research distinctions, not twelve new evidence axes. Their occurrence
in different existing axes does not move cellular or organismal evidence into
A105. The original three construction slots remain unchanged.

## Numerical proposals examined

The lanes independently proposed similar common meanings but different numerical
encodings. Molecular work used endpoint relation0–2; perturbation and system work
used claim relation0–3. These cannot be concatenated as if already calibrated.
All lanes retained native signal, uncertainty, comparable-result counts and
system correspondence separately. There is no empirically justified shared
probability scale in these retrospective cases.

One candidate that is concrete enough to review is the perturbation lane's
ordinal pair, with native measurements retained beside it:

| Proposed component |0|1|2|3|
| --- | --- | --- | --- | --- |
| Experimental relation to the particular inference | Measured endpoint cannot discriminate it | Association or proxy compatible with it | Controlled partial/dependency result leaves the proposed mediation unresolved | Measured endpoint directly instantiates the narrowly stated inference |
| Validity of that measured result/inference | A demonstrated error or artifact compromises it | A named critical confound remains unresolved | Controls support an interpretable result, with component/mediator specificity unresolved | Discriminating controls address the named material alternatives within scope |

Missing source information is unknown, not0. The numbers are proposed ordinal
grades, not probabilities or a claim that the gap from1to2 equals the gap from2to3.
The validity definition currently overlaps attribution and relation; HFP shows
why readout validity and attribution must be examined separately before adopting
this as the common sheet.

The following grades were applied by the researcher under that proposed rubric:

| Actual evidence and inference | Relation | Validity | Native measurement/qualification |
| --- | ---: | ---: | --- |
| PopZ SPR -> direct PopZ–ParB binding in the tested assay |3|3|Kd20nM; uncertainty/preparation count unavailable in inspected text|
| The same SPR alone -> native origin anchoring |1|3|Same20nM; stronger affinity does not supply the missing cellular inference|
| YeaG induction -> later survival contribution |1|2|36±2.3SD-fold induction|
| YeaG CFU loss plus addback -> tested starvation-survival contribution |3|3|Different endpoint; no fabricated numerical rescue fraction|
| YeaG K116A failed rescue -> catalytic necessity |2|1|64% WT abundance leaves an attribution confound|
| YeaG K426A failed rescue -> STK-domain functional requirement |2|2|100% WT abundance addresses one confound, not all folding/catalytic-specificity questions|

These are review examples, not adopted final scores. An initial candidate
annotation is not required: the inference can emerge during investigation.

## Compilation tests and remaining work

The candidate E=min(relation,validity) distinguishes direct binding from a weak
mechanistic extrapolation, but it leaves better precision and independent
replication with no effect whenever those two grades stay fixed. It therefore
does not implement the full requested score. An unqualified average has the
opposite failure: a large signal or many dependent readouts can compensate for
a demonstrated attribution problem. Neither is adopted.

The molecular lane's count vector for supported endpoints, attribution challenges,
opposing endpoints and unknown groups preserves important information. It is
useful reporting, but counts alone do not finish the requested scoring sheet.
The system lane's per-weakness comparison identifies useful complements without
justifying a universal mean across ordinal grades and native quantities.

The next compilation proposal must satisfy concrete case-based changes:

- Increasing a controlled signal without addressing its known attribution
  problem must not convert it to strong evidence for the target's activity.
- Chemical-product identification can strengthen the relevant functional
  inference without inventing independent replication.
- A meaningful reduction in uncertainty or a genuinely independent matched
  replication must be capable of changing support.
- A controlled contrary result must remain capable of lowering the supported
  annotation, while useful investigation progress is recorded separately.
- An additional copy/publication of the same result must add no contribution.
- Different conditions/endpoints must not be pooled as inconsistent repetitions.
- An improved measurement cannot silently fill a missing target correspondence
  or system condition.
- Unknown quantities must remain visible; an unreported error is not zero error,
  and an unavailable experiment is not a negative observation.

The unresolved work is specific: choose common numerical anchors without
double-counting relation/attribution; define how native signal and uncertainty
affect contribution; compile complementary/dependent results and genuinely
independent results differently; and show the resulting numerical changes on
the cases above. This is the remaining part-2 design, not reader implementation.

## Primary source crosswalk for the examples above

- PopZ: https://pmc.ncbi.nlm.nih.gov/articles/PMC2745220/ — Fig3D, main Results/SPR Methods.
- HFP: https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/ — Figs2–5, screening/purification/NMR Methods.
- YeaG: https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/ — Results and Fig1, CFU/complementation/abundance comparisons.
- FrsA: https://pmc.ncbi.nlm.nih.gov/articles/PMC6450606/ — kinetic Methods, steady-state Results and Fig4.
- CysQ: https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/ — Table1, kinetic/MS Methods.
- CofC/CofD: https://pmc.ncbi.nlm.nih.gov/articles/PMC8764529/ — Figs2/6, combined-assay Methods.
- CsiD/LhgO: https://pmc.ncbi.nlm.nih.gov/articles/PMC6265302/ — Figs2/3, product/quinone/genetic comparisons.
- FtsW: https://pmc.ncbi.nlm.nih.gov/articles/PMC6430707/ — Figs1/2, polymerase and catalytic/partner controls.
- ThyX: https://pmc.ncbi.nlm.nih.gov/articles/PMC2168944/ — Figs3/4 and Table2; media-specific values remain separate.
- BioY: https://pmc.ncbi.nlm.nih.gov/articles/PMC1815280/ — initial-rate versus accumulation Results; correction https://pmc.ncbi.nlm.nih.gov/articles/PMC1829295/.
- TrxA: https://pmc.ncbi.nlm.nih.gov/articles/PMC94335/ — Fig1 and Tables2/3, reconstructed genotype.
- ComF: https://pmc.ncbi.nlm.nih.gov/articles/PMC12068725/ — Figs3/4, sulfide/passage/rescue comparisons.

YihI, MurJ and the reaction-half-step comparisons above use retained corpus
evidence unless their lane explicitly identifies an additional new source read.
Full source scopes remain attached to the corresponding case row.

## Subsequent source-boundary correction

Read SOURCE_CORRECTIONS.md before using the worked score examples. SC01 records
that the YeaG K116A/K426A abundance comparison belongs to Fig.3 recovery-growth
complementation, not the Fig.6 long-term survival endpoint. The failed-rescue
rows above must be read with that exact scope. Fig.6B includes K426A and
Y382Stop; it does not supply a K116A survival comparison. The original lane
packet is preserved as history and is superseded at this boundary.
