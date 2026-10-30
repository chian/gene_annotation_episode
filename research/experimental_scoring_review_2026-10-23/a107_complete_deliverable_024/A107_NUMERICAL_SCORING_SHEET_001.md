# A107 current numerical sheet: required partner molecules and coexpression

## 1. Goal, criteria and governing correction

**Goal:** deliver one usable numerical A107 sheet that turns evidence for required partner presence and coexpression into one explicitly calculated candidate contribution, with its component values and uncertainty. The supplied sequence, selected file contents or snippets can precede any candidate name or partner hypothesis. This sheet becomes applicable after a possible function and its partner requirements emerge.

Success means: (1) measurable numerical cells, units, denominators, formulas, uncertainty and missingness; (2) a complete component-to-candidate calculation; (3) contrasting source-based cells and a complete synthetic example with checked arithmetic; (4) explicit shared, replicated, contrary and nondetection handling; (5) source-to-component trace; (6) exact targeted population fields; and (7) formulas, examples and open proposed choices ready to print for the user's judgment, incorporating known feedback. Reader implementation, policy calibration, production credit wiring and a target annotation run are outside this research deliverable.

This is the current coherent reading of the retained A107 proposal. The parent's [missing-condition correction](../a107_sheet_construction_001/A107_MISSING_CONDITIONS_CORRECTION_001.md) governs: **the observed-subset correlation is never multiplied by condition coverage to stand in for the full-panel correlation**. The historical equation `H0[C D R+(1-C)U]`, its incomplete-panel example and corresponding old reader fields are superseded. All original files remain preserved. The complete native and complete synthetic results are unchanged.

The output is a dimensionless support coordinate in [0,1], **not a calibrated probability of function**. A105 was delivered first under progress 011. This document does not edit the ten-axis checklist or declare policy adoption. Exact fields are in [A107_EXACT_CELL_CROSSWALK_001.md](A107_EXACT_CELL_CROSSWALK_001.md); actual read/calculation coverage and the seven-criterion assessment are in [A107_SOURCE_AND_COVERAGE_001.md](A107_SOURCE_AND_COVERAGE_001.md).

## 2. Meaning and scope

The user's A107 definition is evidence that required partners exist in the genome and are coexpressed, using numerical sequence correspondence and statistical expression association. This bounded sheet handles sequence-encoded protein/RNA partner identities in a declared target genome. Its fully worked expression branch is transcript log2(TPM+1) across a declared native condition panel. Transcript association does not measure protein stock, physical interaction, stoichiometric sufficiency or causal function. Small-molecule and pathway resource accounting stays with A110; structural observations stay with A111; perturbation/restoration effects stay with A106. None becomes an extra A107 term.

A candidate has one or more **complete alternative partner sets**. For example, `[[P,Q],[P,R]]` means `(P AND Q) OR (P AND R)`. Every set and its biological rationale is recorded before inspecting its expression score. Optional partners are separate diagnostics. An unspecified partner set yields a null coordinate; an empty set does not earn 1. Repeating a partner does not encode stoichiometry. Stoichiometric demand is retained as a separate measured/unknown quantity, not inferred by counting duplicated names. An unknown or unexamined proposed alternative remains an explicit uncertain set; it cannot be silently dropped to improve a score. A proposal outside the defined measurement branch returns an unsupported status and [0,1], not an invented numeric conversion.

The three retained, reference-defined examples are hypotheses about **NC_000913.3 MG1655 objects**. The papers motivate these relationships; the sheet does not assert that every listed molecule is obligatory for every possible function of YfgM or NlpI.

| Candidate label | Target | Complete alternative partner sets |
|---|---|---|
| YfgM–PpiD–SecYEG | YfgM/b2513 | [PpiD/b0441, SecY/b3300, SecE/b3981, SecG/b3175] |
| NlpI–MepS–hydrolase | NlpI/b3163 | [MepS/b2175, PBP4/dacB/b3182] OR [MepS/b2175, PBP7/pbpG/b2134] |
| NlpI–PBP1A–LpoA–PBP4 | NlpI/b3163 | [PBP1A/mrcA/b3396, LpoA/b3147, PBP4/dacB/b3182] |

MepM/b1856 is a separate measured relation; it is not appended to those NlpI sets. Skp/SurA are not automatically mandatory YfgM partners. No example supplies a new annotation or correspondence for the project's ybhP sequence.

## 3. Numerical cells and the complete calculation

Indexes are partner relation `j`, native expression block `b`, condition `i`, and complete partner set `c`. Cells retain raw input values, source/biological identities and calculation references separately from their scores. All combination choices in this section are proposed conventions.

### 3.1 Genomic presence and sequence correspondence

| Cell | Inputs, denominator and calculation | Meaning and missingness |
|---|---|---|
| `H_j` | Raw pair score `S_QR` and full-sequence self scores `S_QQ,S_RR`, from the same algorithm, scoring matrix and gap parameters; positive self scores. `H=clip(S_QR/sqrt(S_QQ*S_RR),0,1)`. Unit: dimensionless. | Continuous normalized sequence correspondence of the observed genomic molecule to the required partner. It is not homology probability. Missing required scores gives null/[0,1]. Identity and coverage remain diagnostics, not duplicate multipliers. |
| Exact-object `H=1` | The same explicitly identified molecular object on the same versioned reference, or byte-identical **complete** sequences. | Requires recorded equality, not a shared name or species. Unrun alignment fields remain null. A partial snippet is not full-sequence equality. |
| `P_j` | Confirmed presence count / 1 required identity: 1/1 or a genuinely resolved 0/1 in the declared genome. | A feature requires versioned assembly, coordinates and molecular mapping. A search nondetection, incomplete assembly or missing annotation gives null/[0,1], not absence. A resolved absence requires an explicit scope/limit record that actually excludes that identity. |
| `G_j=P_j*H_j` | Product of the presence observation and its measured correspondence. | One qualified genomic observation; not two independent experiments. Known `P=0` fixes `G=0` even if H is unknown. |
| `H0_b` | The same normalized raw-score or exact-object calculation for the supplied target molecule versus the expression matrix's target molecule. | Shared across relations using that target mapping. It qualifies expression only. It does not multiply the already established genomic term or an entire A101 coordinate. |

The native example explicitly defines its required molecules as the reference loci in the deposited feature table. Within that example P=H=H0=1. No alignment was run, no strain was resequenced, and no nontrivial sequence transfer is claimed. A different unknown sequence or assembly must supply its own operands. Multiple possible loci are alternatives with distinct identities; their homology scores are not added. Contradictory present/absent records for the same versioned identity yield unresolved P/[0,1] until reconciled. A native transcript assigned to an allegedly absent same-genome locus is a mapping/record conflict, not permission to use both inconsistent facts.

### 3.2 Experimental comparability and condition denominators

Declare the expression layer, organism/versioned genotype, growth phase, medium and quantities, temperature, pH, electron acceptor, treatments and intended varying factors. The requested panel consists of `m>0` unique, equally weighted condition cells. Native examples use exactly the 12 retained PRECISE cells, not all environments. More cultures within one cell improve its measured mean without creating additional condition weight.

Within each cell use the declared biological-culture roster after the source's technical-measurement aggregation. For gene values `x_ih` in log2(TPM+1), `x_i=sum_h x_ih/n_i`; the partner mean uses the same declared paired cultures. Average growth over that roster in h^-1. Do not average TPM and relabel it mean log expression. Required unavailable culture values leave the declared full mean unknown; an available-culture mean can be retained as a separately scoped diagnostic. Any source-protocol exclusion and the resulting roster must be explicit. An output row or temperature aliquot is not automatically a biological culture.

| Count/cell | Exact meaning |
|---|---|
| `m` | Number of requested condition IDs; unchanged by missing measurements or covariates. |
| `q_pair` | Requested, metadata-matched cells with valid target **and** partner expression means. |
| `q_adjusted` | Those paired cells whose required growth means are also known; `0<=q_adjusted<=q_pair<=m`. |
| `C_pair=q_pair/m`, `C_adjusted=q_adjusted/m` | Measured coverage diagnostics. Neither multiplies a subset correlation. |
| `a` | Integer number of the q_pair cells with both means `>= log2(1+1)=1`. The 1 TPM threshold is a proposed analytical threshold, not an instrument detection limit. |
| `D_observed=a/q_pair` | Paired-subset diagnostic; null if q_pair=0. |
| `D_full` | Co-detected full-panel condition count / m. If q_pair=m, `D_full=a/m`. Otherwise point null and outer range `[a/m,(a+m-q_pair)/m]`. |

Unknown expression and valid below-threshold expression have different meanings. Observed nondetections remain in the expression denominator even when growth is missing. The range for incomplete D is the hull of integer fractions `(a+k)/m`, `k=0,...,m-q_pair`; fractional counts are invalid. It can be conservative when additional known constraints rule out some completions. Threshold counts at 5 and 10 TPM are separate sensitivity diagnostics.

Condition matching, coverage and known differences evaluate **experimental comparability**. There is no unmeasured strain/temperature similarity weight. Nonmatching systems leave this native panel unfilled; they do not receive a prose-derived relevance grade. The native panel is not asserted to match a paper's deletion experiment just because the organism is E. coli.

### 3.3 Expression association and effect isolation

For all condition means in the requested panel, regress target x and partner y separately on intercept and measured growth g:

`beta_x = sum((g-gbar)*(x-xbar))/sum((g-gbar)^2)`

`e_x = x-xbar-beta_x*(g-gbar)`; analogously for y.

`r_full = sum(e_x*e_y)/sqrt(sum(e_x^2)*sum(e_y^2))`.

Keep raw Pearson r from centered x,y separately. If all measured g values are constant, use the explicitly identified intercept-only branch, `k=0`; otherwise `k=1`. Missing g does not authorize switching branches. Zero target or partner residual variance makes r undefined, not zero. The observed-subset statistic, if computable, uses exactly the `q_adjusted` cells and is stored under that scope. If any required full-panel expression or growth mean is unknown, **r_full remains null**; the observed-subset r cannot fill it.

Growth adjustment addresses a measured common covariate. This is a separate **effect-isolation** calculation from condition matching. It does not isolate a causal protein interaction: nutrient responses, oxygen, unrecorded batches and post-transcriptional control remain possible contributors. Those limitations are stated, not collapsed into another multiplier. A single-condition protein panel cannot produce this cross-condition statistic.

For a defined r, descriptive positive association is `R_full=max(0,r_full)^2`. Signed negative r remains in the sheet and contributes R=0; it is not converted into positive support by squaring its sign away. Constant constitutive expression may be compatible with a complex while leaving correlation undefined. Unknown correlation has R range [0,1] and null point, not R=0.

Conditional statistical quantities, where defined, are:

`df=n-k-2`; `t=r*sqrt(df/(1-r^2))`; `p=2*StudentT_survival(abs(t),df)`.

`z=atanh(r)`; `SE_z=1/sqrt(n-k-3)`.

For a declared family of M unique relation/block statistics, `zcrit=NormalQuantile(1-.05/(2*M))`, then `r_CI=tanh(z +/- zcrit*SE_z)`. Ordinary 95% uses M=1. A family must include every consumed interval; a predeclared larger family is allowed. The native family retains all ten relations, including diagnostic MepM, and is not retroactively reduced to nine. Duplicate reports do not increase M.

The Fisher interval requires `n>k+3`, `abs(r)<1`, valid variance and its approximate independent-condition sampling model. If an algebraic r exists but those interval requirements fail, keep the descriptive r/R/coordinate and leave its statistical interval null with the specific reason. This resolves the old reader's ambiguous statement that insufficient interval degrees of freedom makes the entire scoring branch unresolved. It neither invents precision nor changes the 12- or 20-condition examples. Perfect r, deficient residuals and unsupported covariance structure are not evidence for infinite precision. No p-value multiplier is used.

These are model-based intervals conditional on the chosen panel and nuisance model, not a random-sample statement about all environments. They do not fully include uncertainty in replicate means, RNA quantification, threshold classification or genomic mapping. Leave-one-condition-out sensitivity is reported separately; if any deletion makes the statistic undefined, mark the range incomplete rather than hiding that deletion.

### 3.4 Governing combination and bounds

For every expression block:

**`E_jb = H0_b * D_full_jb * max(0,r_full_jb)^2`.**

For same-scope, comparable, distinct expression blocks, after deduplication/dependence handling below:

`E_j = min_b(E_jb)`.

Then the complete candidate calculation is:

**`s_j = G_j*(0.5+0.5*E_j)`**

**`A107_clause_c = min_(j in c)(s_j)`**

**`A107_candidate = max_c(A107_clause_c)`**.

The .5 genomic term and .5 expression term are explicit proposed weights. Minimum across required members and maximum across genuine complete alternatives are proposed conjunction/disjunction conventions, not independent-event probabilities. A strong optional partner cannot compensate for a missing mandatory one. A partner shared between alternatives is the same variable, not fresh evidence. No A101 axis score, binding assay count or other axis coordinate enters this expression.

Without justified stronger missing-input constraints, use `r_full in [-1,1]`, `R_full in [0,1]`. For known H0/G and incomplete panel:

`E_jb in [0,H0*(a+m-q_pair)/m]`;

`s_j in [G/2, G*(.5+.5*H0*(a+m-q_pair)/m)]` for that one-block relation.

Both points are null unless known operands mathematically fix them. If H0=0 or fully measured D_full=0, E=0 despite unmeasured/undefined r. If G=0, s=0. No eligible expression block gives E=null/[0,1]; it does not mean nonassociation. Unknown H/P/H0 uses its declared [0,1] domain. Products, sums, min and max are monotone over these nonnegative domains; evaluate all lower endpoints and all upper endpoints for a valid outer enclosure. Reuse shared variables. A collapsed range fixes a point even if irrelevant upstream cells remain missing. Otherwise emit no fabricated midpoint.

Propagate conditional statistical intervals through the same formulas, **holding measured count and genomic operands fixed**. Missing-input ranges and statistical intervals occupy separate fields. When both kinds of uncertainty occur, retain the statistical interval conditional on its stated known operands plus a separately labeled joint outer enclosure. Do not call that enclosure a confidence interval. Default range propagation is a conservative box calculation; narrower bounds require an explicit joint feasible-completion derivation. No such tighter method is needed or claimed by this sheet.

## 4. Shared evidence, replication, contradiction and nondetection

| Situation | Numerical treatment and retained information |
|---|---|
| Same measurement in multiple papers/files | Collapse by original measurement and biological-unit IDs. Preserve all citations. No extra block, sample count, M, or score. |
| Technical repeats/aliquots | Apply source-protocol aggregation before biological means. They do not increase independent n. Unknown aggregation leaves the corresponding mean unavailable. |
| Several eligible blocks on the same native question | Apply `min(E_1,...,E_B)`. This proposed repeatability requirement can lower support; it does not award replication points or claim meta-analysis. Preserve block-specific signed r, counts, intervals and eligible-block roster. |
| New block on a different layer, organism or panel | Separate scoped comparison. Do not pool its correlations or let it lower a different claim. |
| Partially shared units or conflicting reanalyses | Collapse exact duplicates. Otherwise group them as one unresolved dependence block. Point=null; its nonstatistical range is the hull of the representations' point/missing-input ranges. Keep a separate hull of valid family statistical intervals only when their stated family covers the component intervals; otherwise that statistical envelope is null. Feed the one dependence-block range to the same-scope minimum. No sum of n, independent replicate claim or point selected by effect size. |
| Negative measured r | R=0, retain signed r and its interval. With G=1 this yields s=.5, reflecting the retained genomic contribution. It does not prove partners cannot cooperate. |
| Valid co-detection count a=0 in a fully measured panel | D_full=0, E=0. This is a panel-specific transcript nondetection at the declared analytical threshold, not genomic absence. |
| Incomplete expression/growth or failed assay | Missing mean/covariate and full r remain null. Apply the corrected outer bounds. A failed measurement cannot be counted as zero expression. |
| Genomic contradiction | P=null/[0,1], conflict references retained. Do not silently choose the favorable record. |

No source count, citation count or laboratory count is added to A107. Native transcript values and their genomic correspondence qualify the same evidence chain; recording the correspondence elsewhere does not create independent confirmation here.

## 5. Contrasting published quantities and their correct cells

This consolidation uses the original worker's retained source review, not a new primary-paper inspection. The two papers' own experiments do not supply a native condition-panel r. Their source-only candidate coordinates remain null with the applicable missing-input bounds. The arithmetic below illustrates what their measurements do and do not fill.

| Source, experiment and measured comparison | Reported quantity | Checked derivation | Cell and limit |
|---|---|---|---|
| Götzke 2014, Figure 4: E. coli WT versus ΔyfgM immunoblot; intended changed variable is YfgM deletion, not coexisting WT/mutant YfgM fractions. Each partner band is compared with its own WT=100. Strain/harvest/replicate details are incompletely specified. | PpiD 99%, Skp 131%, SurA 95%; loading band 112% of WT. | Reported ratios .99, 1.31, .95. Only **if** not already loading-corrected: 99/112=.8839285714; 131/112=1.1696428571; 95/112=.8482142857. Optional symmetric amount-similarity `min(a,1/a)` gives Skp 112/131=.8549618321. | `comparability_diagnostic`; normalization ambiguity retained. These are protein abundance ratios, not r, D or a native coexpression contribution. No second loading correction is assumed. The deletion response belongs to A106. |
| Banzhaf 2020, Figure 6A: published quantities attributed to earlier ribosome profiling; a common source table for listed native proteins, not a new TPP or binding experiment. | NlpI 389, PBP4 441, MepM 341, MepS 3931 molecules per generation. | Using the authors' rounded 5 nM per molecule, the concentration-style numbers are 1.945, 2.205, 1.705, 19.655 µM. | `supply_diagnostic`; synthesis per generation is not steady-state stock. The conversion retains its assumption. Upstream ribosome profiling was not independently reviewed by this consolidation or the original A107 worker. |
| Same Figure 6A, explicitly **assumed** one-to-one demand for comparison | PBP4 or MepM synthesis divided by NlpI synthesis. | 441/389=1.1336760925 versus 341/389=.8766066838; `min(1,ratio)` would be 1 versus .8766066838. MepS/NlpI=3931/389=10.1053984576. | Illustrative quantity comparison only; stoichiometry and turnover are not supplied. Neither cap enters G, E or s. NlpI-mediated MepS degradation prevents equating synthesis ratio with available partner supply. |

Sources: [Götzke et al., DOI 10.1074/jbc.M113.541672](https://doi.org/10.1074/jbc.M113.541672); [Banzhaf et al., DOI 10.15252/embj.2019102246](https://doi.org/10.15252/embj.2019102246). The inherited review also preserves the NlpI BW25113/ΔnlpI TPP comparison, two biological replicates with temperature aliquots, its Figure 1 versus Methods threshold discrepancy, and MepS affinity-extract nondetection. Those observations are not independent transcript panels or genomic-absence facts. Late supplementary archives were uninspected and unused.

## 6. Complete native source-data example

Source: [pinned PRECISE processed data](https://github.com/SBRG/precise-db/tree/782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe), associated [Sastry et al. 2019 methods](https://doi.org/10.1038/s41467-019-13483-w). The original worker derived these statistics; the parent independently verified the retained public-input hashes, reselected 28 samples and reconstructed 12 condition means from the full processed matrix. This consolidation checks the numerical joins from that verified receipt. No raw-read processing, new public-data download or new primary review is claimed.

Selection: project `ica`; E. coli K-12 MG1655; unevolved; M9; 37 °C; pH 7; batch. All selected samples are GSE122295/HiSeq4000. Nutrient/electron-acceptor condition is intended to vary. Six glucose cultures form one condition mean; eleven other conditions have two cultures each. Thus n=m=q_pair=q_adjusted=12 and biological culture count=28. The conditions are ade_glc, arg_sbt, cytd_rib, gth, leu_glcr, met_glc, no3_anaero, phe_acgam, thm_gal, tyr_glcn, ura_pyr and wt_glc. Unrecorded batches and original processing/QC selection remain limitations.

For every row below, P=H=H0=G=1 for the exact reference-defined objects, D_full=12/12=1, k=1 and df=9. Counts remain 12/12 at 1, 5 and 10 TPM; sample-level counts are 28/28 but are not the D denominator. Fisher SE=1/sqrt(8)=.3535533906. The retained M=10 gives zcrit=2.8070337683. The reported correlations are new derivations from processed data, not figures printed in either partner paper.

| Target–partner | Raw r | Full-panel growth-adjusted r | Conditional family 95% r interval | E=max(0,r)^2 | s=.5+.5E |
|---|---:|---:|---|---:|---:|
| YfgM–PpiD | .719865059 | .690834725 | [−.141920986,.950985523] | .477252617 | .738626308 |
| YfgM–SecY | .785030523 | .820275801 | [.163736390,.973231248] | .672852390 | .836426195 |
| YfgM–SecE | .708076369 | .684927031 | [−.152891357,.949901638] | .469125038 | .734562519 |
| YfgM–SecG | .539415538 | .470225112 | [−.447905461,.905652164] | .221111656 | .610555828 |
| NlpI–MepS | −.248554802 | −.181181355 | [−.826071886,.669166616] | 0 | .500000000 |
| NlpI–MepM | .331606860 | .345663291 | [−.559377113,.874746949] | .119483110 | .559741555 |
| NlpI–PBP4/dacB | .404489781 | .682865555 | [−.156671453,.949521913] | .466305367 | .733152683 |
| NlpI–PBP7/pbpG | .520261094 | .652918081 | [−.208945022,.943916006] | .426302020 | .713151010 |
| NlpI–PBP1A/mrcA | .493054914 | .732787330 | [−.057651453,.958502991] | .536977271 | .768488636 |
| NlpI–LpoA | −.117752245 | −.042926407 | [−.776060730,.739549133] | 0 | .500000000 |

For YfgM–PpiD, `r=.44048464622881/sqrt(.6664976355145932*.6099786276418824)=.6908347247657712`. Its E=.4772526169421989 and s=.7386263084710994. The unadjusted two-sided p=.01858290934 and ordinary 95% interval [.1553312191,.9125399574] remain statistical descriptors, not extra multipliers.

For the contrary NlpI–MepS comparison, `r=-.6561391963596611/sqrt(1.728507920955197*7.587410585072925)=-.1811813545785082`, p=.5939338557. Its measured signed correlation gives E=0, s=.5, with broad uncertainty; it does not establish inability to cooperate or explain protein turnover.

| Candidate | Complete partner arithmetic | Point | Propagated conditional family interval |
|---|---|---:|---|
| YfgM–PpiD–SecYEG | min(.738626308471,.836426194829,.734562518974,.610555827945) | **.610555827945** | [.500000000000,.910102921453] |
| NlpI–MepS with PBP4 or PBP7 | max(min(.5,.733152683345),min(.5,.713151009985)) | **.500000000000** | [.500000000000,.723891980302] |
| NlpI–PBP1A–LpoA–PBP4 | min(.768488635704,.5,.733152683345) | **.500000000000** | [.500000000000,.773466460199] |

All relations share one dataset and normalization. They are not ten independent demonstrations. The shared MepS operand appears in both alternatives without extra credit. Leaving one condition out changes SecY's adjusted r to a range [.248776990,.873204160], SecE's to [−.069888472,.818532267], and SecG's to [−.048458459,.576728023]. Those are sensitivity ranges, not confidence intervals. Report practical points as roughly .611, .500 and .500 with their intervals.

## 7. Complete synthetic example and current missingness/replication contrasts

All values in this section are constructed. The retained [20-row synthetic matrix](../a107_partner_sheet_014/SYNTHETIC_EXPRESSION_INPUTS_001.csv) supplies complete log2(TPM+1) measurements for target/P/Q/R/O and growth .1,.2,...,2 h^-1. There is one stipulated independent culture per condition, not fabricated within-condition replication. Raw sequence scores below are synthetic program-like inputs; no aligner produced them.

The query-to-expression mapping has pair/self/self scores 180/200/200, so H0=.9. The panel is complete, m=q_pair=q_adjusted=20, and genomic P=1/1 for each partner. The current checker recomputes correlations and realizable co-detection counts from the 20 rows.

| Partner | Pair/self/self | H=G | D count/m | r_full | R_full | E=.9*D*R | s=G(.5+.5E) |
|---|---|---:|---:|---:|---:|---:|---:|
| P, required in both sets | 160/200/200 | .8 | 18/20=.9 | .8 | .64 | .5184 | .60736 |
| Q, one alternative | 135/180/180 | .75 | 16/20=.8 | .6 | .36 | .2592 | .47220 |
| R, other alternative | 180/200/200 | .9 | 20/20=1 | −.4 | 0 | 0 | .45000 |
| O, optional diagnostic | 190/200/200 | .95 | 20/20=1 | .95 | .9025 | .81225 | .86081875 |

Candidate `(P AND Q) OR (P AND R)` gives `max(min(.60736,.47220),min(.60736,.45000))=max(.47220,.45000)=.47220`. The optional O is excluded. With n=20,k=1,M=3, the required-relation family r intervals are P [.462209433,.935046467], Q [.094370575,.859556009], R [−.770738310,.173085795]. Their partner intervals are P [.469218569,.683277054], Q [.377404567,.574485864], R [.450000000,.462133270]. Applying the same min/max gives **[.45,.574485863585]**. O is outside this three-relation family.

| Counterfactual or additional observation | Exact current result |
|---|---|
| Q's genomic presence is unknown in an incomplete assembly; H_Q and expression operands remain stipulated | s_Q in [0,.47220]; candidate point null, missing-input range [.45,.47220]. |
| R is resolved absent in a consistent counterfactual genome; its native expression is unmeasured rather than borrowed from the previous genome | G_R=0, s_R=0; candidate remains .47220 from the Q set. |
| Q has all 20 expression means, a=16, but required growth values are missing | D_full=16/20=.8 remains known. r_full=null/[−1,1], s_Q in [.375,.645]. Candidate point null, range [.45,.60736]. q_adjusted cannot replace 20 in the D denominator. |
| All 20 expression pairs are measured and a=0; r is undefined | D_full=0 fixes E=0. For G=.75, s=.375 exactly; no missing-correlation imputation is needed. |
| A copy of the original source row is added | Collapse it by measurement identity; all scores and denominators unchanged. |
| A genuinely distinct, same-scope P block has H0=.9,D=.9,r=.4 | E_P2=.1296; min(.5184,.1296)=.1296. s_P=.45184; candidate becomes .45184. |
| Instead that second P block has r=−.4 | E_P2=0; s_P=.4; both sets have minimum .4, so candidate=.4. Negative evidence is retained, not averaged into an extra positive vote. |
| The two P estimates overlap in unresolvable biological units, rather than being distinct blocks | One ambiguous dependence-block E range [.1296,.5184], point null; s_P range [.45184,.60736]; candidate range [.45184,.47220], point null. Statistical uncertainty is recorded separately. |

### Missing-condition counterexample that controls the correction

The parent's retained synthetic example has 16 observed conditions with r_observed=.6, all 16 co-detected, and four unobserved conditions. Their eventual target log-expression values are [17,3,3,17], partner values [3,17,17,3], all above threshold. Across all 20, growth-adjusted r becomes `-186.4/212=-.879245283019`.

With H0=.9,G=.75, the invalid old coverage blend gives [.4722,.5397]. The actual completed full panel gives E=0 and s=.375, outside those bounds. The **current** pre-completion calculation is:

`m=20; q_pair=16; a=16; D_full in [16/20,20/20]=[.8,1]`;

`r_full=null, domain [-1,1]; E_full=null, range [0,.9]`;

**`s=null, missing-input range [.375,.7125]`.**

The completion .375 lies within the corrected range. These are outer missing-input bounds, not a confidence interval or a claim that every endpoint is attainable. The observed r=.6 remains available only for its 16-condition subset. The old separate `D=.8 over 16 conditions` example would require 12.8 co-detections and is invalid; it is not used in the current sheet. The complete synthetic D=16/20=.8 above is valid and unchanged.

## 8. Source-to-component trace and remaining proposed choices

| Numerical component | Source/record actually supporting it | Boundary |
|---|---|---|
| Partner sets and experiment arrangement | Original A107 worker's Götzke and Banzhaf reviews, summarized in the retained joined sheet; exact papers above | Relationship motivation, not new numeric binding/perturbation terms. Necessity and alternative-set choices are declared hypotheses. |
| Published amount comparisons | Götzke Figure 4 and Banzhaf Figure 6A as retained by that worker | Reported values versus conditional arithmetic remain distinct. This consolidation did not reopen the primary papers or source-specific packets. |
| Native P/H/H0 and feature identity | Deposited PRECISE gene-coordinate table, same NC_000913.3 reference objects; parent verified identities | Reference presence/identity only; no new sequence search or sample allele determination. |
| Native condition means, D, adjusted r and uncertainty | Pinned PRECISE metadata/full matrix; parent independently reconstructed 28 samples into 12 means and ten associations | This consolidation rechecks residual-statistic and score joins from the parent's receipt, not the full public matrix. |
| Complete nontrivial H/D/r example | Retained synthetic score operands and 20-row matrix | Constructed inputs; newly checked arithmetic, no biological measurement. |
| Correct missing-panel domain | Parent's counterexample, correction and receipt | Governs the old incomplete equation and reader fields; independently rejoined here. |
| E, source-block min, .5/.5, clause min/alternative max | Explicit equations in this sheet, inherited from the retained proposal except the governing correction and stated interface clarifications | Proposed numerical conventions, not adopted policy or calibration. |

Remaining **fully specified but unadopted** choices are the raw/self score normalization, exact genomic observation interpretation, equal condition-cell weighting, growth adjustment, 1 TPM co-detection threshold, positive-r-squared transform, .5/.5 weighting, repeatability minimum, and required-set minimum/genuine-alternative maximum. Their consequences are visible in the examples, including the genomic .5 baseline when association is nonpositive. Different reasonable choices could change values; these choices are not disguised as measurements.

Remaining actual measurement limits include native protein coexpression/stoichiometry, unmeasured batch or causal contributors, source-specific replicate uncertainty, and sequence/genomic mappings for a new supplied target. They remain named missing operands or interpretation limits with defined outputs. Production targeted readers and W05 credit integration are unimplemented and outside this task. No essential calculation is left undefined **within the declared sequence-encoded, native condition-panel branch**.

The bounded checker executed successfully with 87 arithmetic/assertion checks, many repeated across relations, in [A107_FINAL_ARITHMETIC_001.json](A107_FINAL_ARITHMETIC_001.json). That is numerical verification, not 87 scientific validations. Full source inspection and data-reconstruction coverage are attributed separately in the coverage record.
