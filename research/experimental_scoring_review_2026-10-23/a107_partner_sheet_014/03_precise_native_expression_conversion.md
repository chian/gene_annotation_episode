# Third sequential conversion: dated PRECISE native co-expression extension

This targeted extension fills an identified missing numeric operand: neither retained paper supplies a native statistical co-expression coefficient for its partner set. It is a new derivation from deposited processed RNA-seq data, separate from those papers' experiments. Associated primary methods: [Sastry et al. 2019, DOI10.1038/s41467-019-13483-w](https://doi.org/10.1038/s41467-019-13483-w), [PMC6892915](https://pmc.ncbi.nlm.nih.gov/articles/PMC6892915/). The repository is [SBRG/precise-db at commit782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe](https://github.com/SBRG/precise-db/tree/782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe). Retrieval:2026-10-24 UTC,2026-10-23 local. Exact URLs/checksums are in PRECISE_RETRIEVAL.json.

The relevant RNA extraction and PRECISE compilation Methods, README, sample metadata and gene mappings were inspected before conversion. Complete authority rereading was then performed and recorded in RESET_COVERAGE_003.json, including repair of a truncated final authority call. Latest human direction was read last. No new primary paper was opened during the calculation.

## Experimental definition

Scored organism is the explicitly reference-defined E. coli K-12 MG1655 system, with expression reads mapped by the source processing to NC_000913.3. Target molecules are YfgM(b2513) and NlpI(b3163); partner identities are below. The original literature hypotheses arose in other/partly unspecified strain contexts. These data are not retroactively called measurements from either earlier paper.

The selected subset has Project ID`ica`, exact strain-description`Escherichia coli K-12 MG1655`, Evolved Sample`No`, M9,37°C,pH7,Batch. It contains28 biological-sample values across12 condition IDs.11 conditions have two cultures; glucose control has six. BW25113 purR-deletion samples are excluded. The associated Methods describe RNA from distinct biological cultures and exponential-phase sampling around OD6000.5; the deposited selected records share HiSeq4000 and GEO GSE122295. The source processing supplies log2(TPM+1). Its existing mapping/counting, library-normalization and replicate-consistency QC are inherited, not newly verified read-level measurements.

Intended comparison: expression association across a specified nutrient/electron-acceptor panel in a single wild-type strain. Both target and partner are measured in the same cultures. Deliberately varying carbon/supplement/oxygen conditions are part of that panel, not gene perturbations. Growth rate is a measured nuisance covariate. Unrecorded library batches and common transcriptional regulation remain possible confounders. Transcript abundance is not protein stock, periplasmic availability, binding or causal function.

## Exact condition scope

Raw strings below preserve source units; all conditions have NH4Cl(1g/L),M9,37°C,pH7,Batch and no listed antibiotic. The full metadata rows remain in PRECISE_SELECTED_SAMPLE_INPUTS_001.csv. Means in the last column are arithmetic means of the biological-sample growth-rate fields, not independently measured condition rates.

|Condition ID|Biological sample n|Carbon source(g/L)|Supplement(source string)|Electron acceptor|Mean growth h^-1|
|---|---:|---|---|---|---:|
|ade_glc|2|glucose(2)|adenine (100mg/L)|O2|0.78|
|arg_sbt|2|sorbitol(4)|L-arginine (5.75mM)|O2|0.27|
|cytd_rib|2|D-ribose(4)|cytidine (1mM)|O2|0.31|
|gth|2|glucose(2)|glutathione (1mM)|O2|0.07|
|leu_glcr|2|glucarate(4)|leucine (10mM)|O2|0.29|
|met_glc|2|glucose(2)|methionine (5mM)|O2|0.74|
|no3_anaero|2|glucose(2)|none listed|KNO3(20mM)|0.35|
|phe_acgam|2|N-acetylglucosamine(4)|phenylalanine (5mM)|O2|0.63|
|thm_gal|2|galactose(4)|thiamine (1uM)|O2|0.34|
|tyr_glcn|2|gluconate(4)|tyrosine (5mM)|O2|0.57|
|ura_pyr|2|pyruvate(3.3)|uracil (1 mM)|O2|0.27|
|wt_glc|6|glucose(2)|none listed|O2|0.6233333333333333|

The six glucose controls have reported growth-rate fields .58,.58,.66,.66,.63,.63h^-1; their mean is .6233333333333333. This variation and the differing replicate-label counts show why sample metadata must be retained. Six controls are one condition point here, not six independent environments. Biological culture independence is inherited from source descriptions; no source metadata establish that every preparation batch is independent.

## Reference-genome partner observations

These are **deposited feature coordinates**, not newly run homology search outputs. The provided gene table gives length=stop−start; its coordinate convention is not silently relabeled as inclusive. Presence P=1 applies to the named reference feature. Actual alleles and coding integrity in every sequenced culture were not resequenced here. Raw alignment/BLAST fields remain null.

|Gene|Locus|Start|Stop|Strand|Source length(nt)|
|---|---|---:|---:|---|---:|
|ppiD|b0441|461914|463786|+|1872|
|mepM|b1856|1940312|1941635|-|1323|
|pbpG|b2134|2223937|2224870|-|933|
|mepS|b2175|2269978|2270545|+|567|
|yfgM|b2513|2638662|2639283|-|621|
|lpoA|b3147|3293399|3295436|+|2037|
|nlpI|b3163|3308039|3308924|-|885|
|secG|b3175|3322172|3322505|-|333|
|dacB|b3182|3328962|3330396|+|1434|
|secY|b3300|3442765|3444097|-|1332|
|mrcA|b3396|3522870|3525423|+|2553|
|secE|b3981|4177357|4177741|+|384|

The exact candidate references the same loci as the matrix, so the direct-object correspondence H=H0=1 is an equality statement in this example. It is not a fabricated homology search score, a functional-orthology conclusion, or a mapping for an unknown supplied sequence. For a new sequence, its required mapping must be populated independently using the sheet's alignment operands. No A101 total enters A107.

## Measurements and conversion

Use `log_tpm_full.csv`, preserving low-expression genes; the filtered file cannot establish genomic absence. For each condition, average log2(TPM+1) over biological samples. Define D using both condition means at or above1 (the proposed1TPM threshold). Every target/partner pair has12/12 qualifying condition means and28/28 qualifying individual samples; the threshold sensitivity at5 and10TPM also remains12/12. D's scored denominator is12, not28. This finite observed-panel fraction has no invented binomial confidence interval.

Fit target and partner means separately on intercept and growth rate. Correlate their residuals. n=12,k=1,df=9; interval Fisher SE=1/sqrt8. The ten pairs were declared before calculating numeric coefficients. The approximate family95% normal critical value is2.807033768343811. Condition means are the association units. The cultures supply replicate means but do not turn twelve environmental contrasts into twenty-eight.

|Target|Partner|Raw r|Partial r|Two-sided p(df9)|Family95% r interval|Positive squared r|
|---|---|---:|---:|---:|---|---:|
|yfgM|ppiD|0.719865|0.690835|0.01858291|[-0.141921,0.950986]|0.477253|
|yfgM|secY|0.785031|0.820276|0.00198370|[0.163736,0.973231]|0.672852|
|yfgM|secE|0.708076|0.684927|0.02004269|[-0.152891,0.949902]|0.469125|
|yfgM|secG|0.539416|0.470225|0.14441509|[-0.447905,0.905652]|0.221112|
|nlpI|mepS|-0.248555|-0.181181|0.59393386|[-0.826072,0.669167]|0.000000|
|nlpI|mepM|0.331607|0.345663|0.29777780|[-0.559377,0.874747]|0.119483|
|nlpI|dacB|0.404490|0.682866|0.02057078|[-0.156671,0.949522]|0.466305|
|nlpI|pbpG|0.520261|0.652918|0.02940297|[-0.208945,0.943916]|0.426302|
|nlpI|mrcA|0.493055|0.732787|0.01031091|[-0.057651,0.958503]|0.536977|
|nlpI|lpoA|-0.117752|-0.042926|0.90027289|[-0.776061,0.739549]|0.000000|

All exact values, residual dot products and single-relation intervals are in CHECKED_NUMERICAL_CELLS_001.json. Every sample operand is in PRECISE_SELECTED_SAMPLE_INPUTS_001.csv and every averaged operand in PRECISE_CONDITION_INPUTS_001.csv. The correlation formula, positive-squared-r proposal, and min/max partner combination are fully specified in A107_NUMERICAL_SHEET_001.md. The resulting conditional example coordinates are .6105558279445487 for the YfgM complete partner clause, .5 for the NlpI MepS/PBP4-or-PBP7 hypothesis, and .5 for the distinct NlpI PBP1A/LpoA/PBP4 hypothesis. These are proposed support coordinates, not biological probabilities or accepted annotations.

## Comparability and isolation are separate

Comparability to the declared native target panel is C=12 matched cells/12 requested cells=1. This does not transfer BW25113 LB protein assays into MG1655 M9. Their conditions/strains remain distinct source contexts. A target that requests additional/different conditions gets C<1 or unknown, with the missing-scope calculation rather than an intuitive transfer weight.

Isolation is statistical and limited: residualization removes the specified linear growth-rate component from each gene vector. Raw and partial correlations are both shown, making the adjustment inspectable. It does not hold the carbon source or supplement fixed across the panel and cannot separate direct coupling from shared responses. Leave-one-condition-out ranges are wide for several pairs; YfgM–SecE even changes sign in one omission. The condition grid was selected deliberately and is small. Fisher intervals are conditional sampling-model intervals, not a calibrated claim about all bacterial conditions. There is no causal effect-isolation multiplier. The actual endpoint is observational association, for which the explicit adjustment is the available measured control.

## Shared sources, contradictory signs and missingness

All ten relations share the same28 sample IDs,12 condition means, mapping and normalization; shared genes add further covariance. They are not independent experiment replicates. Family-wise Bonferroni intervals do not assume independence of relations, but each interval retains its sampling assumptions. Min/max assembly uses each shared partner as the same variable. Duplicate reanalysis or publication of this matrix cannot create another source block.

NlpI–MepS and NlpI–LpoA have negative point correlations, retained as signed observations. They earn no positive association support under the proposed transform; neither is an assertion of genomic absence or inability to bind. All samples exceed the analytical expression threshold, and the intervals are broad. The NlpI paper's post-translational relationships therefore cannot be judged false from these mRNA coefficients.

Unknown source-strain alleles, validated protein detection limits, periplasmic protein stoichiometry, cross-species transfer, and measurement-error covariance remain unfilled. They are not coded as low quality. No structural correspondence, binding strength or growth-perturbation effect is added to this A107 calculation. The full scoring branch is numerically defined; its remaining limits are data scope, statistical assumptions and uncalibrated proposed weights.

## Arithmetic checks actually run

The local research script revision002 checked all ten partial correlations against the independent formula `(r_xy−r_xg*r_yg)/sqrt[(1−r_xg²)(1−r_yg²)]` and against SciPy's residual Pearson calculation, with agreement better than2e−13. It checked28 unique samples,12 conditions, six-control collapse, bounded endpoints, alternative/required logic, and the retained-paper ratios. Synthetic raw vectors independently reconstruct r=.8,.6,−.4,.95 and co-detection counts18,16,20,20 out of20. This is reproducibility arithmetic, not a scientific annotation run, remote job or production reader implementation.
