# FrsA 2011: a measured nuisance response is useful only in its demonstrated assay

New A105 research output, 2026-10-23. Reported data, derived numbers and proposed calculations are distinguished below. No production scoring rule or biological run is changed; no sheet is declared complete.

Source: Lee et al., *Nature Chemical Biology* 7:434–436 (2011), [DOI 10.1038/nchembio.589](https://doi.org/10.1038/nchembio.589), PMID 21623357. Inspected: the complete 28-page [corrected supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnchembio.589/MediaObjects/41589_2011_BFnchembio589_MOESM125_ESM.pdf), including its 7 June 2011 legend-restoration notice; publisher [Table 1](https://www.nature.com/articles/nchembio.589/tables/1); publisher [Fig. 1 and caption](https://www.nature.com/articles/nchembio.589/figures/1); and indexed original page 434 from the coauthor's institutional publication endpoint. The full main-paper PDF was not recovered. `frsa_2011_main_nature.pdf` is an HTML subscription-preview response, not a PDF. The supplement, Table 1 and figure were retrieved successfully and retained. Figures S5, S10 and Fig. 1 were visually inspected in addition to text extraction.

## Definitions first

The molecule is wild-type *Vibrio vulnificus* FrsA (gene amplified from genomic DNA and expressed using pQE30/pQE-frsA in *E. coli* JM109), purified by Ni-affinity and size exclusion chromatography. A Coomassie gel is shown, without quantified contaminant activity. The original wild-type activity rows do not mix mutant and wild-type FrsA. Additional reactions contain FrsA plus a distinct partner, IIA-Glc, deliberately added as an intended variable. Substitution/growth/rescue conclusions are not used here to score A105 attribution.

The pH response compares the same nominal recombinant protein and readout, deliberately changing pH. For an investigation of pH dependence this is the intended variable. For a comparison of two proteins or preparations assayed at different pH, the same curve can become a nuisance-response bridge—but only if its transfer to those preparations is justified. A difference cannot be both the intended variable and a comparability penalty in the same contrast.

The direct chemical endpoints are pyruvate disappearance, acetaldehyde identity/amount and CO2 amount. NADH depletion is the coupled reporter for acetaldehyde. The preparation could contain another enzyme producing the same products, and the chemical measurement alone does not quantify that contribution.

## Source measurements relevant to the numerical sheet

| Source location | Reported data | Derived numbers and their meaning |
|---|---|---|
| Table 1, WT row and footnote a | `Km=0.39±0.02 mM`; `kcat=1372±11 s⁻¹`; `kcat/Km=3518±183 s⁻¹ mM⁻¹`; mean and SD from at least two independent assays | CVs: 5.128%, 0.8017%, 5.202%, respectively. The kcat relative variance is `(11/1372)²=0.0000642802`. These are reported assay dispersion, not preparation-to-preparation dispersion or standard errors. Exact n and biological-preparation independence are unavailable. |
| Fig. S5, PDF p. 15; kinetic Methods, PDF p. 7 | 1 nM FrsA; 47 ng in 1 mL; 50 mM phosphate pH 7; 1 mM DTT; 2 mM NADH; 3.7 U ADH; 37°C; 1 minute. WT substrate series 0.05–2 mM; two kinetic experiments averaged | Native absorbance curves are available, but blank traces, individual replicate curves and path length are not supplied. Plotted points in time are not additional independent assays. |
| Fig. S10, PDF p. 20 | pH 4–9; same nominal 1 nM protein/2 mM NADH/3.7 U ADH; 37°C; **5-minute endpoint**, acid stopped. Authors state that ADH standard curves were made at corresponding pH | Visual estimates, not exact table data: at pH 7 and 8, kcat-axis values ≈235 and ≈95; efficiency-axis values ≈2330 and ≈580. Ratios are ≈0.4043 at saturation and ≈0.2489 in the low-substrate limit. Neither ratio is an annotation score. Axis unit text is absent; do not supply an unprinted unit to these graph readings. Error bars are drawn but their type and underlying replicate data are not specified in this legend. |
| Fig. 1b and caption | Acetaldehyde and CO2 measured at varying substrate with 1 nM FrsA; fitted association `R²=0.96`; main p. 434 describes 1:1 production | `1−R²=0.04` is the regression's residual-variation fraction, not a 4% stoichiometric error or 96% identity confidence. A high R² can coexist with the wrong slope or calibration bias. |
| Figs. S2a/S2b and NMR Methods, PDF pp. 7, 11–12 | 5 mM pyruvate with/without 2 µM FrsA, 20°C for 90 min in 95% D2O. Acetaldehyde standard: 2.24/9.68 ppm; hydrate: 1.33/5.25 ppm | Enzyme exposure is `2×5400=10800 µM·s`; substrate/enzyme is 2500. Spectral identity is supported by the standard comparison. Integrals, quantitative recovery and detection limit are missing. |

## Concrete comparability calculation

For a fitted biochemical response, define `v(S,c)=E*kcat(c)*S/[Km(c)+S]`. The nuisance conversion between conditions `c` and reference `c0` is

`K(S;c,c0) = {kcat(c) S/[Km(c)+S]} / {kcat(c0) S/[Km(c0)+S]}`.

This is a numerical response multiplier with a chemical meaning. At high substrate it tends to the kcat ratio; at low substrate it tends to the catalytic-efficiency ratio. The pH graph therefore demonstrates why a single pH mismatch weight is wrong: the same pH 7→8 difference corresponds to approximately 0.404 or 0.249 depending on substrate regime. A raw nominal ratio `7/8` has no such meaning.

Use the measured `K` to transform the signal once, `a=(v-b-h)/(E*K)`. Here `b` is the matched assay blank and `h` is independently estimated contaminant activity. Propagate the variance of `K`; do not then multiply `a` by `K` as a second relevance penalty. The graph's values apply to its 5-minute endpoint and pH-specific ADH calibration. They cannot directly repair the 1-minute kinetic assay: its Table 1 kcat is 1372 s⁻¹ while the pH 7 graph has a numerical ordinate near 235, and the graph does not print units. The plotted numerical ratio is ≈5.84, but it is not a demonstrated biological difference. Raw calculations/units and a time-course bridge are needed before combining the endpoints.

The deliberately different pH experiments also calibrate the reporter at each pH. Without those standards a coupled-assay pH curve can combine a true enzyme response and a detector response. The fact that standards were used is not a numerical calibration score. Their slopes, intercepts, residuals and covariance are needed to populate that cell.

## Explicit placement in the combined score

Proposed scoring-template quantities on a common log-rate scale are:

`ell = log(v-b-h) − log(E) − log(K)`

`V_total = V_measurement + V_calibration + V_nuisance + V_isolation + V_correspondence + covariance_terms`.

Each variance is an experimentally estimated uncertainty contribution in the same squared-log-rate unit. `V_nuisance` concerns conversion between experimental conditions; `V_isolation` concerns subtracting non-target activity. They are distinct even when they share observations. If they are correlated, use the full joint covariance and do not pretend the five summands are independent.

For independent mean estimates with valid variances, the combined log-rate estimate is `sum(w_i*ell_i)/sum(w_i)` with `w_i=1/V_total,i`. For correlated measurements use the covariance-matrix version. A comparability multiplier can be displayed as `C_i=V_before/(V_before+V_nuisance)`; it enters a combined precision weight exactly once through `C_i/V_before=1/(V_before+V_nuisance)`. Isolation uncertainty can enter analogously in the next variance increment. These multipliers measure lost precision from quantified uncertainty, not the physical fraction of activity attributed to FrsA. The latter is a separately displayed `I=(v-b-h)/(v-b)` when `h` is actually measured.

**Synthetic arithmetic demonstration anchored to the reported pH-response shape, not paper data:** take a *hypothetical* pH SD of 0.1 and assume the pH 7–8 log-response slope applies locally. The approximate slope is `ln(95/235)/(8−7)=−0.90571 per pH unit`, so `V_nuisance=(0.90571×0.1)²=0.00820308`. If the *illustrative* baseline variance is the Table 1 relative assay variance `0.0000642802`, then `C=0.0000642802/(0.0082673613)=0.0077752`. This is not a FrsA score: it mixes two protocols solely to demonstrate how such arithmetic behaves, and the real pH SD/bridge are unmeasured. It shows that an apparently precise assay need not remain precise after an uncertain condition adjustment. The paper does not justify filling any missing variance with zero.

For the actual FrsA record only the assay CV and variance above are computable; a complete numerical comparability/isolation-adjusted score is not. The score interface must preserve that incompleteness rather than report the baseline precision as total reliability. Neither variance weighting nor the log transform decides the parent's bounded annotation-credit mapping; that common-sheet conversion remains separate.

## Attribution and chemical balance remain separate

Pyruvate loss plus acetaldehyde/CO2 formation strengthens the reaction assignment. Quantifying coproduct agreement requires calibrated matched amounts and a constrained stoichiometry residual, such as `r_j = P_CO2,j − P_AcH,j` with `Var(r_j)=Var(P_CO2,j)+Var(P_AcH,j)−2Cov(...)`. Then `sum(r_j²/Var(r_j))`, or the full covariance version, is a numerical consistency component. The published R² is not enough to calculate it. Both amounts were obtained from the same reaction and are complementary endpoints, not independent preparation replications.

This stoichiometry does not assign the catalyst. If a contaminant generates exactly the same products, it passes the product-balance check. A fractionated preparation series quantifying FrsA abundance, candidate contaminant abundance and native activity could fit `v_j = k_F E_F,j + sum(k_h E_h,j) + b_j`, with uncertainty/covariance and identifiability checked. That model supplies `h_j` and the activity fraction `I`; a gel described as pure does not. The original crude-lysate deletion comparison belongs to the perturbation evidence lane and does not substitute for a measured activity-purity fraction under this A105 assignment.

## Reconciliation with the already reviewed 2013 report

This section compares known data; it does not claim the source papers are interchangeable. The 2013 preparation A used the original plasmid and JM109, improving construct correspondence, but purification/culture details still differ; its preparation B adds host/construct/tag differences. The 2013 optical assay changes NADH from 2 to 0.2 mM (a tenfold reporter-pool difference) and ranges over protein concentrations. The MS assay additionally uses 500 mM KCl. The NMR comparison has the same nominal temperature and incubation duration, but 5→10 mM pyruvate, 2→5 µM enzyme and 95%→unspecified D2O formulation. The original NMR Methods do not specify a numerical pD; do not silently assert pD matching.

**Conditional prediction from the 2011 Michaelis–Menten parameters, not a measured 2013 rate:** at 1 mM pyruvate and 50 nM FrsA, `v0=0.05×1372×1/(0.39+1)=49.35 µM/s`. If the kinetics transfer unchanged and there is no inactivation/product inhibition, integration gives `t_90%=[0.9+0.39 ln(10)]/(0.00005×1372)=26.21 s` and `t_99%=40.61 s`. Those are much shorter than the 2013 12-minute observation. This makes a calibrated negative potentially strongly discriminating; it does not calculate a negative-evidence score, because the 2013 detection threshold and the salt/state transfer are unmeasured. The correct result is a conditional predicted signal with explicitly missing calibration and comparability operands.

Numerical arithmetic is retained in `frsa_2011_derived_arithmetic.json`. No values in this review establish correspondence to ybhP, and no 2019 FrsA paper was reread or counted here.

## Full post-paper reset actually performed

After the supplementary text/figures and publisher Table 1/Fig. 1 were inspected, and before the interpretations above, all of these complete documents were reread in five nontruncated tool outputs: `AGENTS.md`; `GOAL.md`; `docs/EPISODE_STRUCTURE.md`; `docs/TIME_AWARE_ESTIMATION.md`; `docs/TOOL_KNOWLEDGE.md`; `docs/TASK_AND_STEERING.md`; `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`; `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`; `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md`; its `VERBATIM_RECOVERY_002.md`; `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`; `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`; the parent review directory's `AGENTS.md`; `A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`; `TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md`; and finally the complete current user goal `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`. The parent additionally instructed that the forthcoming method-paper detection limit must not be copied into FrsA's unmeasured limit; that constraint will govern the next source.
