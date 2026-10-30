# A107 numerical research sheet: partner availability and co-expression

Research proposal, 2026-10-23 America/Chicago; public-data retrieval crossed into 2026-10-24 UTC. This is a numerical sheet with populated cells and targeted **unimplemented** reader contracts. It is not an accepted biological calibration, a production scorer, an investigation prompt, or an annotation-credit integration. W05 retains the latter responsibility. No axis-completion checklist or goal is changed.

The user's axis definition is preserved verbatim:

> (7) Native deployment is a fancy word that doesn’t mean much - get rid of it. You are looking for proposed function being supported by existance of partner molecules. I.e., if it’s part of a complex, is there evidence for the rest of the complex being present both in the genome and co-expressed - both these have scores b/c one is a homology score and the other is a co-expression statistical association.

The deliverable is one candidate's A107 coordinate in [0,1], accompanied by its actual component values, statistical interval, missing-input range and provenance. This coordinate measures the specified kinds of support; it is **not a probability that the function is true**. A constant half weight on genomic availability and half on expression support is an explicit proposed convention, not a measurement or a qualitative grade. Its consequence is deliberate: a genetically available partner with a measured nonpositive expression association receives genomic credit but no positive association credit. Unknown association produces an interval, not an invented half score.

## 1. What is being scored

A persistent `candidate_id` describes a particular possible function and explicit partner logic. Investigation may start from a sequence, file or snippet; a candidate and its partner requirements can emerge later. Distinct hypotheses remain distinct persistent records, including multiple hypotheses about the same sequence. No public name or pre-existing annotation is required to start.

This bounded proposal handles sequence-encoded protein/RNA partners with an identified target genome and a declared native expression comparison. The present examples are bacterial proteins measured through their transcripts. Transcript association does not establish protein abundance, physical interaction, stoichiometric sufficiency, or causal function. Those interpretations remain separate. Small-molecule/pathway accounting belongs to A110; a structural observation belongs to A111. Neither is silently converted into sequence identity or an extra A107 support term.

Partner requirements are a disjunction of complete conjunctions: `clauses = [[partner_a, partner_b], [partner_a, partner_c]]` means `(a AND b) OR (a AND c)`. A clause must be biologically stated before looking at its expression score. Optional partners are diagnostics, excluded from the coordinate. An unspecified partner set produces a missing coordinate; an empty set does not earn 1. Repeated copies of a gene name do not encode stoichiometry. Stoichiometry, alternative paralogs, and incompatible complexes require explicit separate fields/clauses.

Examples suggested by the retained papers, scored below only as hypotheses in the MG1655 reference system:

| Persistent research candidate | Target molecule in scored system | Complete partner clauses | Optional/separate evidence |
|---|---|---|---|
| `A107-MG1655-YfgM-PpiD-SecYEG-001` | NC_000913.3:b2513, YfgM | `[b0441 PpiD, b3300 SecY, b3981 SecE, b3175 SecG]` | Skp/SurA are not automatically required subunits |
| `A107-MG1655-NlpI-MepS-hydrolase-001` | NC_000913.3:b3163, NlpI | `[b2175 MepS,b3182 PBP4] OR [b2175 MepS,b2134 PBP7]` | MepM relation retained separately |
| `A107-MG1655-NlpI-PBP1A-LpoA-PBP4-001` | NC_000913.3:b3163, NlpI | `[b3396 PBP1A,b3147 LpoA,b3182 PBP4]` | This is a distinct hypothesis, not another observation of the preceding candidate |

The papers motivate the relationships. Their binding, perturbation and structural results are not numerical A107 terms. The table does not claim that all the proposed relationships have been demonstrated in MG1655, or that every member is obligatory for every possible YfgM/NlpI function.

## 2. Exact component definitions and calculation

Symbols below apply to partner relation `j`, native expression source block `b`, and candidate clause `c`. All weights and transformations in this section are proposed. Original program scores and measurement units are retained alongside transformed values.

### 2.1 Sequence correspondence and physical genomic presence

For two full sequences Q and R, preserve their pairwise raw alignment score `S_QR`, self scores `S_QQ,S_RR`, aligner/version, scoring matrix, gap parameters, searched database/version, E-value if produced, bit score if produced, aligned positions and lengths. All three scores must use the same algorithm and parameters. Define:

`H(Q,R) = min(1, max(0, S_QR / sqrt(S_QQ S_RR)))`, with positive self scores.

This is normalized sequence correspondence, not homology probability or functional calibration. It already incorporates the scoring algorithm's mismatch, gap and unaligned-length consequences; percent identity and coverage are preserved diagnostics, not additional independent multipliers. If scores are unavailable, do not reconstruct them from an E-value, invent a categorical fallback or borrow an A101 axis score. Return H unknown. If Q and R are the **same explicitly identified molecular object on the same versioned reference** or byte-identical complete sequences, H=1 by identity; record which equality was established and leave unrun aligner fields null. Mere shared species or gene name does not satisfy this equality. A partial snippet is not a complete identical sequence.

`H_j` identifies the target-genome molecule as the partner hypothesized in the clause. `H0_b` identifies the expression matrix's target molecule as the query molecule; it applies only to the expression operand. If a query is already the exact reference locus measured in that matrix, H0=1. Source-to-target sequence mapping is used as correspondence, once in its stated location; it is not an additional independent finding. An existing A101 result may supply its raw alignment record by reference, but its axis coordinate is never multiplied here.

`P_j = confirmed present target-genome loci / 1 required molecular identity`, with possible observations 1/1 or a genuinely resolved 0/1. A present locus needs a versioned assembly feature or sequence-placement record and coordinates. A resolved absence needs evidence about that same complete genomic scope that actually rules out the required identity; a threshold-filtered search, an unassembled region or a missing annotation does not do that. Preserve assay/search limits even for a stated absence. Unknown/incomplete scope gives P unknown, not 0. This 0/1 quantity is a binary genomic observation, not a low/high quality grade. Presence does not establish an intact active protein or adequate expression.

`G_j = P_j H_j`.

When multiple features could be the partner, retain their molecular identities and specify alternatives in clauses; do not add their homology scores. Contradictory positive and genuinely resolved negative records for the same versioned object require a conflict record and an unknown P until the discrepancy is resolved. An assay nondetection is not such a negative genomic record.

Native examples below use the deposited gene-coordinate table for the same NC_000913.3 reference loci explicitly named in the candidate. Thus P=1 and H=H0=1 **within that reference-defined example**. No BLAST search, strain resequencing, or nontrivial sequence-transfer score was performed. These values do not fill those fields for an unknown user sequence or a different genome.

### 2.2 Experimental comparability: measured coverage of the requested system

Declare the target comparison before calculating expression effects: organism/versioned genotype, expression layer, growth phase, medium and amounts, temperature, pH, electron acceptor, treatments, and intended varying factors. Let the requested scope contain `m` equally weighted condition cells. The empirical examples request exactly the 12 selected PRECISE condition cells. Conditions with more biological replicates receive more precise means but do not get more scope weight.

Let `q_b` be the number of those condition cells actually matched and measured in source block b, using the declared condition tuples. `C_b=q_b/m`. This is the measured fraction of requested condition coverage, not an intuitive transfer grade. Unknown condition metadata do not count as a match. Known differences are reported separately, including genotype, batch, library preparation and platform differences. Do not invent a numeric temperature/strain similarity kernel. Nonmatching systems provide unfilled evidence for this native comparison unless the user specifies another target scope.

For an incomplete comparison, unobserved coverage is an explicit unknown `U_jb ∈ [0,1]`, not evidence of low expression. The formula below propagates it. C=0 contributes no observed native comparison; C=1 eliminates U. C=1 for the actual example means only that its scope is the measured MG1655 panel. It does not assert equivalence to the YfgM paper's partly unspecified Figure 4 conditions or the NlpI paper's BW25113 LB experiment.

### 2.3 Statistical expression association and measured co-detection

Use measured expression inputs in **log2(TPM+1)** for this RNA-seq branch. For each gene and condition cell, average the transformed values over distinct biological cultures, after merging technical measurements according to the original assay protocol. Do not average TPM then silently describe the result as mean log expression. For co-detection, a condition counts if **both condition means** are at least `log2(1 TPM+1)=1`. The 1-TPM threshold is an explicit proposed analytical threshold, not a validated instrument detection limit. Preserve zeros and report sensitivity to 5 and 10 TPM. A valid below-threshold observation is distinct from a missing value or failed assay.

`D_jb = number of matched condition means where target and partner both exceed threshold / number of matched condition means with valid paired measurements`.

Missing measurements reduce the measured matched cells q; they do not disappear from the requested denominator m. The published raw sample count and the condition-unit count are separate fields. The actual example also reports 28/28 sample-level co-detection; its D denominator is nevertheless 12 condition cells.

For matched condition means x (target), y (partner) and g (growth rate in h^-1), fit separate ordinary least-squares regressions on intercept and g:

`beta_x = sum_i (g_i-gbar)(x_i-xbar) / sum_i (g_i-gbar)^2`

`e_xi = x_i-xbar-beta_x(g_i-gbar)`, and identically for y.

`r = sum_i e_xi e_yi / sqrt[(sum_i e_xi²)(sum_i e_yi²)]`.

This is the growth-adjusted Pearson partial correlation. Preserve the raw Pearson correlation too. The one measured nuisance adjustment is chosen here before inspecting correlation values. It partly separates common growth-rate association; it does not isolate a causal partner interaction. Carbon source, supplements, oxygen and unrecorded batches can still generate common responses. The source-study grouping and its QC selection also limit generalization. A single-condition protein panel cannot populate this correlation.

For this bounded branch k=1, n is the number of matched condition units, and `df=n-k-2`. `t=r sqrt[df/(1-r²)]`; two-sided p is `2*StudentT_survival(|t|,df)`. If growth rate is constant, the intercept-only branch has k=0 and centered x,y; if growth is missing, do not silently switch branches, return the adjusted statistic missing and preserve the raw statistic separately. Zero residual variance makes r undefined, not zero. At least `n>k+3` is required for the interval below. Time series, phylogenetic samples and repeated individual measurements require an appropriate covariance model; this branch does not assign their nominal row count as n.

For a predeclared family of M scored relations, preserve ordinary 95% intervals and use approximate simultaneous intervals:

`z=atanh(r); SE_z=1/sqrt(n-k-3); zcrit=NormalQuantile(1-0.05/(2M))`

`r_L,r_U = tanh(z ± zcrit SE_z)`.

This tanh is only the inverse of the standard Fisher correlation transform. It is not the A105 scoring function. The intervals assume approximately independent condition units and the usual partial-correlation sampling model. The selected, small condition grid is not a random sample of all environments, and replicate-mean uncertainty and expression quantification uncertainty are not fully modeled. Report the nominal interval as conditional/model-based, plus leave-one-condition-out sensitivity. Bonferroni's family bound does not require independent relations; it still depends on the individual interval approximations. Perfect |r|=1, unestimable variance, or invalid residual degrees of freedom makes the interval unknown; no infinite-precision support is inferred.

Define positive association support:

`R_jb = [max(0,r_jb)]²`.

It is a continuous positive shared residual-variance convention, not a binding probability and not a p-value. Negative r is retained as signed evidence against positive co-expression; it earns no positive association component. Constant constitutive expression can be biologically compatible with a complex while leaving this statistic uninformative. Do not call that biological absence.

### 2.4 Fully specified combination

For one expression source block:

`E_jb = H0_b [ C_b D_jb R_jb + (1-C_b) U_jb ]`.

When C=1, `E_jb=H0_b D_jb R_jb`. When C<1, report a null point and the interval obtained with U in [0,1], unless the result is mathematically fixed by another known zero. The uncovered term explicitly prevents C=0 from becoming an observed nonassociation.

If the same relation has several predeclared, comparable native source blocks addressing the **same requested comparison**, use `E_j=min_b E_jb`. This is a proposed conservative repeatability convention: every eligible replicate block constrains the positive-support claim; more papers do not add credit. Preserve each signed r, D, coverage and interval, and report the range across blocks. A discordant block can lower the result. This is not an independence product or a calibrated meta-analysis. Use all metadata-eligible blocks; do not choose them by their effect sizes. Different organism, expression layer, condition scope or relation produces a distinct scoped row/candidate comparison, not a secretly pooled correlation. If no eligible block exists, E is unknown [0,1].

Duplicate reports, copied tables, measurements of the same biological material, and reanalyses of the same expression matrix share one source-block identifier; the repeated record is not another b. Partially overlapping blocks require disjoint primitive units or a covariance-aware reanalysis. Until that is possible, keep them in one dependence block and use the envelope of their estimates (`point=null`, lower=min lower endpoints, upper=max upper endpoints), rather than increasing n or pretending independence. With known identical measurements, collapse by measurement ID and retain all publication links. The actual ten PRECISE relations share one block and all the same sample IDs.

Per partner relation:

`s_j = G_j (0.5 + 0.5 E_j)`.

Per complete required set and then candidate:

`A107_clause_c = min_{j in c}(s_j)`

`A107_candidate = max_{c in candidate}(A107_clause_c)`.

These are conjunction/disjunction support conventions. They prevent a long list of optional partners from diluting or inflating the coordinate, and prevent a strong alternative from compensating for a missing mandatory member within a complex. They also avoid multiplying correlated evidence as if independent. There is no averaging of arbitrary partner lists, no noisy-OR, and no sum of repeated binding assays. Only whole, explicitly allowed alternative clauses compete in the maximum. Shared partners are the same variable in every clause, not fresh evidence.

All primitives are bounded and monotone after r is mapped to R. Propagate uncertainty by evaluating products, sums, min and max at their lower and upper endpoints. Missing H, P, H0, D or R has a null point and domain [0,1]. Preserve **missing-input range** separately from statistical confidence intervals; neither is a probability distribution over missing data. If a known zero fixes a product or clause, its result is known even when an irrelevant other operand is missing. Otherwise null remains null. Do not plug 0, 0.5, an average or a best-case estimate into a missing cell. Native sequence/feature facts have no fabricated confidence interval; assembly error and mapping error not estimated here remain explicit limitations.

## 3. Published contrasting cells, without substituting them for co-expression

Sequential conversions are in `01_yfgM_conversion.md` and `02_nlpI_conversion.md`; their complete post-paper authority resets are in RESET_COVERAGE_001 and 002. The precise data extension and its associated paper had another full reset, RESET_COVERAGE_003. These sources were not reviewed in parallel.

| Source and experiment | Reported numbers and denominator | Checked calculation | A107 role and limit |
|---|---|---|---|
| Götzke 2014 [DOI 10.1074/jbc.M113.541672](https://doi.org/10.1074/jbc.M113.541672), Figure 4, WT versus ΔyfgM immunoblot | PpiD 99%, Skp 131%, SurA 95%; each relative to its own WT=100. Loading band ΔyfgM=112 relative to WT=100 | Reported ratios .99, 1.31, .95. **Conditional only**, if not already loading-normalized: 99/112=.88392857; 131/112=1.16964286; 95/112=.84821429 | Native protein detection and an expression-comparability example. Whether the labels already include loading correction is not established, so no second correction is silently used. Mutant contrasts are not a native co-expression correlation. n, r and SE remain null |
| Same Figure 4 | Skp conditional abundance 131/112 above baseline; PpiD conditional abundance 99/112 below | Optional amount-similarity diagnostic `min(a,1/a)`: Skp 112/131=.85496183, PpiD99/112=.88392857 | A concrete symmetric comparability calculation, **not used** in the native RNA-seq A107 coordinate. Deleting YfgM changes the biological arrangement; it is not a mixture of 64% mutant and 36% WT protein |
| Banzhaf 2020 [DOI 10.15252/embj.2019102246](https://doi.org/10.15252/embj.2019102246), Figure 6A | NlpI389, PBP4 441, MepM341, MepS3931 molecules per generation; copied/derived ribosome-profiling estimates, not new TPP counts | At authors' rounded 5nM/molecule: NlpI1.945µM, PBP4 2.205µM, MepM1.705µM, MepS19.655µM. Printed table rounds to1.9,2.2,1.7,19.7µM | Defined supply operands, not measured steady-state availability or co-expression. Synthesis per generation and molecular stock are different quantities; NlpI changes MepS degradation |
| Same Figure 6A, **illustrative assumed** one-to-one demand | Numerators PBP4 441 or MepM341; denominator NlpI389 | 441/389=1.13367609 versus341/389=.87660668; a demand cap would yield1 versus.87660668 | Contrasting arithmetic under an explicitly unverified stoichiometry assumption. It is not a scored A107 term. MepS3931/389=10.10539846 does not prove excess available MepS protein |

Figure 4 strain/harvest details and biological replicate counts were not fully specified. NlpI TPP uses BW25113 and ΔnlpI comparisons, with two replicates and temperature aliquots; those abundance/stability effects belong to A106. Temperature aliquots are not independent biological replicates. The NlpI Figure 1 local-FDR threshold (<.01) differs from the Methods threshold (<.05 plus |score|≥10); the discrepancy is preserved, not resolved by selecting one. MepS was not detected in an affinity extract, which is assay nondetection, not genomic absence. The original upstream ribosome-profiling paper was not independently reviewed; its values copied in Figure 6 remain one evidence family. Supplementary archives that downloaded late are retained but **uninspected and unused**.

## 4. Actual statistical co-expression cells from the dated public extension

The [PRECISE repository](https://github.com/SBRG/precise-db/tree/782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe) is pinned to commit `782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe`. Associated primary methods: Sastry et al. 2019 [DOI 10.1038/s41467-019-13483-w](https://doi.org/10.1038/s41467-019-13483-w). These are **newly derived statistics on public processed data**, not correlations reported in either retained paper. PRECISE_RETRIEVAL.json contains the retrieval date, exact URLs and SHA256 values.

Exact selection: project `ica`; strain description `Escherichia coli K-12 MG1655`; unevolved `No`; M9;37°C;pH7;Batch. This selects28 biological culture measurements in12 conditions, including six glucose controls collapsed to one condition mean. The other11 conditions each have two samples. The BW25113 purR-deletion samples are excluded. The intended variation is nutrient/electron-acceptor condition; other recorded conditions are held as just specified. All selected samples use HiSeq4000 and GEO GSE122295. Unrecorded batch differences remain a limitation.

The source processing aligns to NC_000913.3 and provides log2(TPM+1). Use `log_tpm_full.csv`; do not infer gene absence from the noise-filtered table. Original preprocessing/QC and its replicate-consistency selection are inherited limitations. `PRECISE_SELECTED_SAMPLE_INPUTS_001.csv` contains all exact selected metadata and raw processed values; `PRECISE_CONDITION_INPUTS_001.csv` contains every averaged operand. These files preserve full floating-point precision. Display below is rounded.

For every row: n=12 conditions,28 biological samples,k=1 growth covariate,df=9,D=12/12=1,C=12/12=1,H0=G=1 in the reference-defined example. The10 relations were specified before numeric analysis. Fisher SE=1/√8=.35355339; M=10 gives zcrit2.80703377. Every pair also has28/28 sample-level co-detection. Raising the threshold from1 to5 or10TPM leaves every D at12/12 for these data.

| Target–partner | Raw Pearson r | Growth-adjusted r | Nominal family95% r interval | R=max(0,r)² | s=.5+.5R |
|---|---:|---:|---|---:|---:|
| YfgM–PpiD | .719865 | .690835 | [−.141921,.950986] | .477253 | .738626 |
| YfgM–SecY | .785031 | .820276 | [.163736,.973231] | .672852 | .836426 |
| YfgM–SecE | .708076 | .684927 | [−.152891,.949902] | .469125 | .734563 |
| YfgM–SecG | .539416 | .470225 | [−.447905,.905652] | .221112 | .610556 |
| NlpI–MepS | −.248555 | −.181181 | [−.826072,.669167] | 0 | .500000 |
| NlpI–MepM | .331607 | .345663 | [−.559377,.874747] | .119483 | .559742 |
| NlpI–PBP4(dacB) | .404490 | .682866 | [−.156671,.949522] | .466305 | .733153 |
| NlpI–PBP7(pbpG) | .520261 | .652918 | [−.208945,.943916] | .426302 | .713151 |
| NlpI–PBP1A(mrcA) | .493055 | .732787 | [−.057651,.958503] | .536977 | .768489 |
| NlpI–LpoA | −.117752 | −.042926 | [−.776061,.739549] | 0 | .500000 |

One reproducible numerator/denominator example: YfgM–PpiD has residual cross-product .4404846462288093, target residual sum of squares .6664976355145927, and partner residual sum of squares .6099786276418819. Thus r=.4404846462288093/√(.6664976355145927×.6099786276418819)=.6908347247657706. R=.47725261694219795 and s=.738626308471099. Its unadjusted two-sided partial-correlation p=.01858291 and ordinary95% r interval[.155331,.912540] are preserved; the family interval above is wider. A p-value is not another score multiplier.

NlpI–MepS provides a contrasting real negative association: residual cross-product−.656139196359658; residual sums of squares1.7285079209551986 and7.587410585072929; r=−.1811813545785072,p=.59393386. This supplies no positive co-expression component. Its wide interval and simultaneous detection prevent an assertion that the molecules cannot cooperate. mRNA co-expression also cannot resolve NlpI-mediated MepS turnover.

The combined coordinates, **conditional on the explicitly specified MG1655 hypotheses and this panel**, are:

| Candidate | Explicit calculation | A107 point | Nominal family interval propagated through min/max |
|---|---|---:|---|
| YfgM–PpiD–SecYEG | min(.738626,.836426,.734563,.610556) | .610556 | [.500000,.910103] |
| NlpI–MepS with PBP4 or PBP7 | max(min(.500000,.733153),min(.500000,.713151)) | .500000 | [.500000,.723892] |
| NlpI–PBP1A–LpoA–PBP4 | min(.768489,.500000,.733153) | .500000 | [.500000,.773466] |

MepM's .559742 is not appended to either NlpI clause. Its relationship is retained separately. The shared MepS term in the two alternatives is used once as the same variable. All10 relations share the same samples and normalization. Neither the table rows nor the two papers are independent replications of the coordinate.

Sensitivity is substantial: leaving one condition out moves YfgM–SecY partial r from.248777 to.873204; YfgM–SecE from−.069888 to.818532; YfgM–SecG from−.048458 to.576728. These ranges are diagnostics, not formal confidence intervals. Precision shown for reproducibility exceeds biological accuracy; practical reporting should use roughly .611,.500,.500 and the accompanying limitations.

## 5. Complete synthetic end-to-end example

Everything in this section is constructed, not measured biology. It fills operands absent from the publications. The generated20-condition,20-culture log2(TPM+1) matrix is `SYNTHETIC_EXPRESSION_INPUTS_001.csv`. Growth rates are0.1,0.2,…,2.0 h^-1. One culture supplies each condition; there is no invented within-condition replication. Orthogonal vectors were constructed so residualizing on intercept/growth produces the specified correlations; `SYNTHETIC_VECTOR_CHECKS_001.json` independently checks the correlations and threshold counts. The synthetic alignment scores are illustrative program-like raw outputs, not the result of running an aligner or a biological calibration.

Suppose a query maps to the expression target with pair/self/self scores180/200/200: H0=180/√(200×200)=.9. All20 requested condition cells are matched: C=20/20=1. Genomic feature observations are P=1/1 for all partners. Partner sequence-score operands and expression results are:

| Partner | Pair/selfQ/selfR raw score | H and G=P×H | D numerator/denominator | Partial r | R | E=H0×D×R | s=G(.5+.5E) |
|---|---|---:|---:|---:|---:|---:|---:|
| P required in both clauses |160/200/200|.8|18/20=.9|.8|.64|.5184|.60736|
| Q alternative complete set member |135/180/180|.75|16/20=.8|.6|.36|.2592|.47220|
| R alternative complete set member |180/200/200|.9|20/20=1|−.4|0|0|.45000|
| O optional |190/200/200|.95|20/20=1|.95|.9025|.81225|.86081875, diagnostic only|

Candidate clauses are `(P AND Q) OR (P AND R)`. Clause values are min(.60736,.47220)=.47220 and min(.60736,.45000)=.45000. **A107=max(.47220,.45000)=.47220.** The optional strong relation does not inflate the coordinate. For M=3 scored relations,n=20,k=1, the nominal family interval propagates to[.45,.57448586]. O's diagnostic interval is not part of this three-relation family guarantee.

The sequence scores lower support through continuous H values; they are not coded categories. The query mapping H0 affects expression correspondence only. It does not reduce a separate, already observed genomic-presence half by multiplying an entire A101 coordinate.

Missing/negative contrasts with fully specified outcomes:

* If R is genuinely absent in the specified complete genome, P_R=0, so its clause is0. The Q clause still yields.47220.
* If the Q genome region is missing from an incomplete assembly, P_Q is unknown[0,1]; this is not a zero. With H_Q=.75 and the known expression operands, s_Q lies[0,.47220]. Because the R clause is.45, the candidate is point-null with missing-input range[.45,.47220].
* If Q's expression association is missing but G_Q=.75,H0=.9 and D_Q=.8 are known, R_Q∈[0,1], so s_Q∈[.375,.645]. Combining with fixed P and R gives candidate point-null range[.45,.60736]. No default .5 association is inserted.
* If only16 of20 intended conditions are measured with D=.8,r=.6,H0=.9, then E=.9[.8×.8×.36+.2U] ∈[.20736,.38736]. A P=1,H=.75 partner has s∈[.45276,.52026], point null. Coverage is measured; what happened in the four missing conditions is unknown.
* Two copies of the same source row or a paper reprinting its table add no source block, no n, and no score. Two independently measured, comparable blocks with R=.64 and R=0 constrain E through the stated minimum, preserving the discordant signed correlation rather than manufacturing a second positive vote.

## 6. Source and component trace

| Component/cell | Inspected source or data | Measurement provenance | Derivation/proposal boundary |
|---|---|---|---|
| Partner hypotheses, source experiment definitions | Götzke2014 PMC4081946; Banzhaf2020 PMC7049810, Results/captions and relevant complete Methods | Native IP/co-migration, reconstitutions and perturbations motivate specific relationships | Their binding/activity/perturbation outcomes are not extra A107 terms |
| Protein abundance ratios | Götzke Figure4 visual and caption | Printed percentages relative to each protein's WT100 | Conditional loading arithmetic only; normalization ambiguity retained |
| Molecules per generation/concentration examples | Banzhaf Figure6A visual/caption | Published derived values attributed to earlier ribosome profiling | No independent reread of that upstream study; no conversion of synthesis into steady-state amount |
| Reference locus presence/identity | Pinned PRECISE `gene_info.csv`, NC_000913.3 mapping specified by associated Methods | Deposited coordinate/strand/length records | P=1 and H=1 only for the same explicitly reference-defined objects; no search scores invented |
| Samples, biological units and condition matching | Pinned `metadata.csv`; Sastry2019 RNA-seq/PRECISE Methods | Strain, media, temperature, pH, project, growth, replicate IDs |28 samples→12 equal condition means; C12/12 is target-scope definition |
| Expression numbers | Pinned `log_tpm_full.csv` | Public processed log2(TPM+1), not new reads | New growth-adjusted r, p, Fisher interval, D and sensitivity calculations |
| H normalization | Synthetic raw-score operands; exact-reference equality for native case | Raw program scores preserved when available | Normalized score transformation proposed; no functional probability calibration |
| R,D,E,s,min/max and weights | This draft | Source values above remain separate | All scoring transformations, half weights, repeatability minimum and partner-logic reduction proposed |
| Statistical/arithmetical checks | `calculate_research_cells_002.py`, checked JSON; `check_synthetic_vectors_001.py` | Local research calculations only | No production reader, scorer, annotation run or remote computation |

Figure-image filenames and correction provenance are recorded in the paper conversions. `paper02_fig6.jpg` was an initial misleading download name for actual Figure5; `paper02_figure6_actual.jpg` is the inspected Figure6. No old file was overwritten. `calculate_research_cells_001.py` is an unexecuted draft preserved with an additive correction; version002 produced the checked outputs. See ADDITIVE_CORRECTIONS_001.md.

## 7. Exact reader contracts and practical limits

`A107_READER_CONTRACTS_001.md` defines the exact record fields, units, validation, targeted inputs/outputs and failure meanings. The responsibilities remain separate: investigation guidance identifies candidate functions and partner hypotheses; this sheet defines the numerical cells/combination; readers populate those cells. No prompt is replaced by this sheet and no production reader is implemented.

Every calculation necessary for the stated sequence-encoded, native, condition-panel branch is specified above. The actual data and synthetic example both reach a single coordinate. Remaining essential **data** gaps for a different user-supplied candidate are its target-genome feature correspondence, partner-set specification, compatible native expression inputs and their condition/replication metadata. Those gaps produce the specified nulls/ranges. The retained two papers alone do not supply native association statistics, experimental protein replicate uncertainty, or query-specific homology scores. The dated extension fills the association branch only for its explicitly named reference-system examples.

No numerical mapping is supplied from a STRING combined score, structural similarity, categorical expression label, evolutionary distance or a cross-species environment mismatch into this branch's r or H. Such fields are preserved if available, and require their own justified measured conversion before they can replace these operands. That is a limitation of the bounded proposal, not a hidden caller choice or a default quality grade. Biological calibration of the half weights, positive-r-squared transform, repeatability minimum and clause min/max remains a user-review question; they are fully defined computationally and can be judged now.

Checks actually run: the local revision002 calculation, independent partial-correlation algebra and SciPy checks for all10 real relations, threshold sensitivity, condition-unit counts, min/max dependence checks, published-ratio arithmetic, and synthetic raw-vector reconstruction. No production tests or pipeline runs were performed because production files were not changed.

### Additive clarification: one genomic observation, with correspondence

`G=P×H` does not mean two independent confirmations. P answers whether the identified feature is observed in the declared genome; H describes that feature's measured correspondence to the required partner. They qualify the same observation. The sheet neither adds their scores as separate votes nor treats their product as an independent-event probability. The same raw identification record can be referenced from another axis without earning another independent identification event here. H0 is likewise one shared query-to-expression correspondence variable across all relations that use that target, and it is never repeatedly multiplied through a chain of partner clauses.

Final artifact audit:21 checks passed in FINAL_ARITHMETIC_AUDIT_001.json, including unchanged public-input hashes and the printed missing-data example bounds. A Git status check was unavailable because this workspace path has no Git repository; the actual writes and artifact inventory remain confined to this owned directory.
