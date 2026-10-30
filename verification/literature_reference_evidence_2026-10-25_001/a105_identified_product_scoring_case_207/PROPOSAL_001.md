# A105 source-grounded proposal: productive product/cofactor coupling

Research proposal only. This changes no goal, permanent direction, production sheet, prompt, credit formula or episode. Parent conversation review and independent source review remain required. The intended contribution is a missing scientific link in the coordinated A105 numerical sheet: a precisely measured cofactor signal does not by itself establish the asserted substrate-to-product function. This is one worked reaction-system case with contrasting molecule arrangements; it is not another completed assay grader.

## Original source and experimental definitions

Kim, Heo and Ortiz de Montellano, 2008, *Efficient Catalytic Turnover of Cytochrome P450cam is Supported by a T252N Mutation*, DOI10.1016/j.abb.2008.02.044, PMID18359283, PMCIDPMC2577879. Public original article: https://pmc.ncbi.nlm.nih.gov/articles/PMC2577879/ . Full original HTML is acquisition_001.bin, SHA256fe5ba79bc3152f6d94f730cc7e02b43c041fbcb5092afa434386ba3c60c2e7de. Complete readable article text, including all four tables and references, is primary_read_001.txt. SOURCE_PACKET_001.json retains original-byte paragraph/table/cell witnesses; its displayed text is a convenience, not the authority. Original Fig4.jpg was actually viewed; its hash/custody are separate. No figure was digitized.

The studied molecule is Pseudomonas putida P450cam/CYP101. T252N, T252N/V253T and T252A mutants were produced separately in E. coli, with carboxyl-terminal6His constructs, then purified through Ni-affinity and DEAE steps. Exact E. coli strain and independent preparation count are not stated. The article does not equivalently specify the WT tag in the quoted construct paragraph; WT-versus-mutant construct identity therefore is not silently completed. No target sequence or target-to-reference transfer is involved.

Each reconstituted reaction contains a selected P450 variant plus putidaredoxin(Pd) and putidaredoxin reductase(PdR), at the stated1:5:1 ratio. WT and mutant P450 proteins replace one another between assay arms; the partner proteins coexist with the selected P450. Intended changes are the designated amino-acid substitutions. Whole-cell expression yields are not the amounts in the purified-enzyme assay and must not become corrections to its turnover numbers. The double mutant has both450 and420nm CO-complex signals, a separate possible stability/active-fraction limitation; a numeric active-fraction correction is unavailable.

The functional assertion addressed is that the selected P450 system catalyzes camphor hydroxylation to5-exo-hydroxycamphor. Organic product identity is supported by chromatographic and mass-spectrometric comparison with authentic standards(P11,P17); a7.57min product peak/mass-spectrum inset is shown forT252N(Fig4/P26). These observations qualify which chemical event the reported product rate represents. They are not a binary product-identity score and are not independent repetitions of the product rate.

Product assays(P10) specify200pmolP450,1nmolPd,200pmolPdR,0.50ml100mMphosphate,pH7.4, NADH addition50µl of10mM,37°C, general10–30min incubations and organic extraction. NADH oxidation(P12) uses1:5:1 partners,37°C,2mMcamphor,5min preincubation, addition10µl of10mMNADH, andA340 decay with6.22mM^-1cm^-1. Detailed Table3 product incubation/substrate matching, same aliquot and same protein preparation are not separately stated. The paper assigns product and cofactor rates to the same Table3 row, but this does not establish a simultaneous paired time course or identical measurement windows. Do not calculate a precise final NADH concentration from an ambiguous pre-/post-addition volume.

H2O2 is a separately assayed spectrophotometric endpoint(P13), terminated after60s. Water inTable3 is explicitly calculated from the other three endpoints(Table3footnote), not independently measured. Source-reported methods support a reaction-system utilization estimate; they do not support applying its ratio to an arbitrary different activity measurement.

## Concrete source numbers and their interpretation

All activities below are Table3 native min^-1 values, associated by the source with the reconstituted P450. Exact molar-concentration/active-enzyme quantification basis is not further reconstructed here.

| P450 arm | Organic product | NADH consumed | H2O2 | Reported inferred water | Reported coupling |
|---|---:|---:|---:|---:|---:|
| WT |206|289|printed0|42|71%|
| T252N |92|216|printed0|62|42%|
| T252N/V253T |132|343|printed0|106|38%|
| T252A |printed0|427|33|197|printed0%|

The results describe absent peroxide as nondetection and T252A hydroxylation as negligible; Table2's T252A kinetic parameters areND. Thus those printedzeros are retained native source entries with a nondetection qualification and unknown detection limit, not exact physicalzeros. No numerical upper bound or exact lack of function follows. The positive WT/T252N/double product entries remain usable reports despite these partial limitations.

Table3 supplies no per-row uncertainty, covariance or repetition count. Fig5's triplicate mean±SD applies to its kinetic points, not automatically Table3. Table2 fittedkcat124±6,54±2,165±7min^-1 and Table3 product rates206,92,132min^-1 have different labels and unresolved detailed experiment links: do not pool them as repeated estimates of one parameter or label their differences a contradiction without establishing comparability.

There is also an actual source-label conflict: the original Fig4 upper-right panel visually readsT252N/V253N, whereas Methods/Results and Tables2–4 identifyT252N/V253T. Keep the image label, numeric table identity and conflict. Do not silently relabel the panel, or transfer the single-mutant mass-spectrum identity proof to a supposedly resolved double-mutant panel.

## Paired extraction fields and numerical cells

The reader needs two authorized rate operands, their exact source-cell spans, endpoint chemical identities, molar/turnover bases and normalization stages. Interpretations must retain actual subject/construct/preparation/partners, substrate/product, buffer,pH,temperature,time window, reported pairing, same-preparation/aliquot status, calibration/blank treatments, source uncertainty/repetition, and the stoichiometric reaction account. Distinguish the cofactor endpoint from the organic product endpoint. An existing scalar or ratio reader can supply arithmetic, but it does not establish these experimental meanings.

Let aH be the measured cofactor-consumption activity and aP the identified-product activity, both on a compatible canonical basis. Let ν be molecules of identified product per molecule of cofactor for the declared productive chemical reaction. Here ν=1 is the source's reaction-account model: oneNADH-equivalent is assigned to one productive hydroxylation, as also reflected in its water-residual formula. It is not estimated from the same rate ratio and is not an empirical quality weight.

Proposed cells and their roles:

1. `reported_product_activity` and `reported_cofactor_activity`: preserve native positive rates, qualifications and original normalization. These are magnitudes; neither is annotation confidence.
2. `source_pair_productive_utilization = aP/(ν*aH)`: dimensionless measured-endpoint relevance component. It quantifies how much of the reporter/cofactor turnover corresponds to the chemically identified productive event, conditional on the assigned source pairing and stoichiometric account. Detailed matching remains visible; it is not a probability that the enzyme has the function.
3. `source_reported_coupling`: retain the author's71/42/38/0percent separately, without substituting recalculated ratios. `displayed_minus_reported_coupling` is a numerical consistency diagnostic in percentage points; it does not become a penalty from assumed rounding.
4. `product_activity_from_linked_cofactor = ν*φ*aH`: applies a genuinely linked utilization multiplier only to the corresponding cofactor activity, and only once. For the same source pair φ is derived fromaP: this is an identity/reconstruction ofaP, not additional supporting evidence. Applying φ to another assay requires its own explicit compatible relationship; absent that relationship, return an unavailable component and retain native operands.
5. `coupling_variance`: with a supported joint uncertainty model for the two activities and fixedν, useVar(φ)=Var(aP)/(ν²*aH²)+aP²Var(aH)/(ν²*aH⁴)−2*aP*Cov(aP,aH)/(ν²*aH³). Full covariance, units and normalization dependencies matter. This paper cannot populate it; no independence, known-normal model, n correction, confidence interval or function-probability conversion is fabricated.
6. `inferred_water_activity = (aH−aR−aP)/2` describes the author's reaction-account residual, whereaR is H2O2 production. It must be labeled inferred, with all dependencies and nondetection qualifications. A displayed-value diagnostic can reproduce the author's arithmetic convention, but physical water bounds require actual nondetection limits. `chemical_account_closure = aP+aR+2*aW−aH` computed using that inferredaW is algebraicallyzero and has no independent mass-balance evidential value.

The quantities selected for function support are the source's identified-product activity and its uncertainty/limits, qualified by the endpoint-identification, control and experimental-relationship evidence. Do not multiply a generic source-presence index for NADH turnover byφ and call the result function reliability. First establish the function-specific endpoint and propagate the appropriate uncertainties; any subsequent statistical scoring must have its own defined model and meanings. Existing positive-endpoint profiles describe their actual measured endpoint and do not establish this missing mapping.

## Worked numerical conversions and explicit combination

These are proposed deterministic conversions of original reported numbers, not new experimental measurements. NUMERICAL_ORACLE_001.json records exact Fractions and independent70digitDecimal cross-checks.

| Source arm | aP/(νaH) from displayed positive rates | Percentage | Native reported percentage | Displayed−reported |
|---|---:|---:|---:|---:|
| WT |206/289|71.280276816609%|71%|+0.280276816609pp|
| T252N |92/216=23/54|42.592592592593%|42%|+0.592592592593pp|
| Double |132/343|38.483965014577%|38%|+0.483965014577pp|

ForT252N: 1*(23/54)*216=92min^-1. Multiplying its reported42% by216 instead gives90.72min^-1,1.28below the native product rate. Retain both inputs and this difference; do not replace92or42, silently declare43%, or infer an experimental error distribution from displayed precision.

For the WT/T252N contrast:

(aP_mut/aP_WT) = (aH_mut/aH_WT)*(φ_mut/φ_WT)
= (216/289)*(6647/11124)
= 0.747404844291*0.597536857246
= 46/103 = 0.446601941748.

This factorization explains why cofactor turnover alone overstates retained productive hydroxylation. The product ratio is not a separate third independent signal to be added to its two factors. It also does not normalize away the intended mutation or correct the underlying reaction into wild-type behavior.

The contrastingT252A arm makes the endpoint distinction concrete: NADH consumption427 exceedsWT289, yet identified product is not detected/negligible. A high cofactor-turnover score could therefore support the wrong functional inference. Its printed0/427diagnostic is0, but physical coupling remains unknown with unreported upper limit. Do not present the diagnostic as measured exactzero or full proof of catalytic absence.

The displayed-value water calculation gives41.5,62,105.5,197min^-1, compared with reported42,62,106,197. These small differences are retained diagnostics. The physical WT/T252N/double residuals remain qualified by peroxide nondetection. The resulting numericalclosure is a reuse of the same operands, not an orthogonal experiment.

## Validity, comparability and attribution remain distinct

Authentic-standard GC-MS addresses chemical identity and reduces the ambiguity of NADH-loss as an activity proxy. Peroxide measurement examines an alternate electron sink. Water by subtraction is not complementary measurement. Binding(KdWT1.8±0.1µM;T252A2.9±0.2µM) shows that retained substrate association alone does not establish hydroxylation. Those are different questions and cannot be counted as interchangeable repeated successes.

Attribution to the assayed P450 remains distinct from productive utilization of its reaction system. Pd/PdR and possible contaminants could consume cofactor. No numerical partner-only/no-P450 blank is supplied in the inspected article. The nonproductiveT252A arm is a changed catalytic system, not a valid blank to subtract fromWT. Product identity does not itself quantify contaminant contributions or sample recovery. Unknown blank/calibration/active-fraction measurements must stay unknown rather than becomeg=0,k=1,E=1.

Comparability outside the mutation requires preserved common partner ratios and conditions, plus the unresolved detailed procedural differences above. Stability/P420 effects in the double mutant are a distinct actual limitation. The supplied material does not justify a universal percentage-comparable score or a nuisance correction borrowed from a different system.

Later A105 compilation should reuse the underlying chemical-activity result once, retaining these different scientific qualifications. Complementary identity and peroxide evidence can address named alternatives; their contributions need declared dependence, not automatic addition or multiplication of independent confidence. Independent-preparation replication and uncertainty are unavailable here. A106 and the later axes remain outside this workload; mutation contrasts serve the A105 endpoint problem without implementing perturbation/restoration graders.

## Necessary implementation work and handoff

The existing compiled assay module corrects/normalizes one selected endpoint through(q−g)*v/(k*E*u), with uncertainty when supplied. It does not convert NADH turnover into identified organic-product activity. Its corrected_activity must retain the endpoint it actually corrects. The existing product-partition module reads composition fractions/sums/closure; it explicitly does not measure formation rate or molecular attribution. The calibration recovery module evaluates standards/spikes and does not establish productive chemical coupling. Reusing those modules requires these meaning distinctions; simply selecting an arbitrary existing ratio cell is insufficient.

A future bounded workload can implement source/possessed-rate input routes, the scientifically constrained pairing/stoichiometry/censoring fields, and the proposed cells. Native ratio and product reports should survive missing covariance or detailed pairing. A source with no product measurement cannot populateφ merely because it has good cofactor precision. A nondetection without a limit must not enter point arithmetic aszero. Explicit same-pair reconstruction dependencies prevent an apparent product-rate result from counting twice.

Required contrasting checks include positive source pair, nondetection/unknown limit, different preparations/conditions, alreadyproduct-based or alreadycoupling-corrected rates, shared enzyme denominator, reversed/uncertain stoichiometry, compound identity conflict, missing/duplicate measurements, incomplete covariance and a truly independent measured product balance. No new global scoring categories, private loops, runtime gates, computational biology suites, target-transfer weights or W05 wiring are proposed.

This proposal contributes an actual source-grounded component for evaluating endpoint relevance and productive specificity. It does not finish common experimental reliability, effect isolation, cross-assay complementary/contradictory compilation, all A105 coverage, or the full literature goal. Hand off exact typed components with source scope, conditions, origin, uncertainty and dependency groups for later credit work; do not send an invented total annotation score.
