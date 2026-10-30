# A106 paper packet 01: YeaG perturbation and restoration

Research draft only. This is a populated numerical-sheet source packet, with proposed transformations identified separately. It neither completes A106 nor changes A105, A109, A110, prompts, readers or production credit.

Source: Figueira et al. (2015), *Adaptation to sustained nitrogen starvation by Escherichia coli requires the eukaryote-like serine/threonine kinase YeaG*, [DOI 10.1038/srep17524](https://doi.org/10.1038/srep17524), [PMC4664914](https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/). Fresh full main narrative/Methods and captions inspected through Europe PMC XML; Figures 2, 3 and 6 inspected as publisher images. The complete retained supplementary PDF text was inspected, including Tables S1–S3. No new experiment, gel quantification or curve digitization was performed.

## Experimental definitions before scoring

The growth comparison contains WT with empty pBAD18, chromosomal ΔyeaG with empty pBAD18, and that deletion complemented with plasmid-borne WT or variant YeaG. Supplementary Table S2 identifies ΔyeaG780::km (JW1772-1) and pBAD18 expressing 6xHis-YeaG. The table mixes an MG1655 description with the WT stock designation BW25113; the exact background should remain an unresolved source inconsistency rather than silently becoming verified MG1655. The chromosomal deletion and single complementation construct in the growth-arm labels provide no WT-plus-mutant coexpression arm. Figure 3C itself labels protein constructs, not each lysate's host genotype.

Within Fig. 3, the intended comparisons are WT versus substituted/truncated plasmid YeaG **in the deletion background**. Their common plasmid/promoter/tag and protocol improve comparability. Protein quantity differences are additional changes when the question is the substituted residue/domain, whereas loss of YeaG amount is the intended variable for the deletion comparison and must not be penalized as experimental mismatch. A residual His signal is not a measured residual ATPase/kinase activity.

Protocol quantities include 0.1% w/v arabinose for pBAD complementation, 3 mM initial ammonium for recovery cultures, 37 °C, and starting OD600 0.05. Matching those settings does not demonstrate identical protein amounts or physiological expression. Recovery starts after starvation and measures OD-based regrowth/lag. Prolonged-starvation viability is a different endpoint, in CFU/ml.

## Filled source-derived numerical cells

`native` denotes an author-reported number; `derived` is arithmetic on it; `proposed` is a scoring convention. None is a target/ybhP measurement.

| Row and source | Native measurement and exact ratio | Derived value | Proposed scoring cell | What remains unknown |
|---|---|---:|---:|---|
| YG-K116A, Fig. 3C | Anti-His signal of 6xHis-YeaG K116A divided by the WT 6xHis-YeaG lane signal: 0.64/1.0 | Relative signal = 0.64 | Amount comparability `C_amount=min(0.64,1)/max(0.64,1)=0.64` | Signal-to-moles calibration, loading normalization, blot sample timing, uncertainty, dose–phenotype relation and activity per molecule |
| YG-R232A, Fig. 3C | Corresponding R232A/WT His-signal ratio = 0.48/1.0 | 0.48 | `C_amount=0.48` | Same omissions; no numerical recovery-rescue fraction extracted |
| YG-K426A-text, main Results | Stated abundance = 100% of WT | 1.00 | Conditional `C_amount=1.00` | Conflicts with printed Fig. 3C signal intensity; cannot silently choose this as the sole number |
| YG-K426A-image, Fig. 3C | Printed signal intensity 1.12 versus WT 1.0 | 1.12 | Conditional `C_amount=1/1.12=0.8928571429` | No evidence here resolves the text/image discrepancy; preserve both as alternate source values, not biological replicates |
| YG-Y382Stop, Fig. 3C | Truncated His-tagged species/WT His-signal = 0.96/1.0 | 0.96 | `C_amount=0.96`, conditional on comparable immunodetection per molecule | Truncation changes molecular mass; equal signal is not equal full-length active protein or equal enzyme capacity |
| YG-lag-12h, Fig. 2 | WT-minus-deletion lag difference 18 ± 1.8 min; deletion lag 8.5% shorter than WT | `K/W=1−0.085=0.915` | Symmetric endpoint contrast `θ=(W−K)/(W+K)=0.085/1.915=0.0443864230` | Exact absolute WT lag, paired replicates, interpretation of tabulated ±, and covariance |
| YG-lag-18h, Fig. 2 | Difference 24 ± 1.8 min; 10.7% shorter | `K/W=0.893` | `θ=0.107/1.893=0.0565240359` | As above |
| YG-lag-24h, Fig. 2 | Difference 32 ± 0.0 min; 13.4% shorter | `K/W=0.866` | `θ=0.134/1.866=0.0718113612` | Rounded ±0.0 does not establish zero measurement error; no covariance/replicate values recovered |

`C_amount` is a **proposed fractional agreement of measured amounts**, not a calibrated reliability probability or the fraction of phenotype attributable to the variant. It compares the smaller to the larger measured amount. It does not divide the phenotype by 0.64, assert 36% activity loss, or extrapolate a dose response. The protein's molecular change remains excluded from this comparability calculation. `θ` is an effect-size component, not the final score, and is invariant to changing minutes to hours. The percentage source values are rounded, so their derived values are also approximate despite the arithmetic digits shown.

**Additive source discrepancy notice:** SOURCE_CORRECTIONS.md correctly separates Figures 3 and 6 and preserves the main-text 100% statement. Inspection of the actual Figure 3C image additionally finds 1.12 printed for K426A. This packet adds that unresolved discrepancy without replacing the original correction, the main text, or the earlier retained report. The two K426A values are not averaged.

## The 64% comparison and separate effect isolation

The denominator is WT **His-tagged plasmid protein signal**, not total native WT protein in a chromosomally intact organism. Because the functional comparison replaces the deletion with one construct, the observed failed recovery complementation can depend on the mutant protein's altered molecular properties, its smaller amount, or both. The source does not establish that 64% WT quantity would produce 64% WT recovery phenotype. Nor does it measure a mixture that is 64% mutant plus 36% WT.

The quantity confound requires a separate causal bound. Let `D=W−K` be the matched endpoint difference between a reference construct and a variant/depletion arm, and let `B` be a measured upper bound, in the **same endpoint units**, on the difference that the unintended amount change and other nominated nuisance changes could produce without the intended molecular change. A candidate isolation component is:

`I=max(0,1−B/abs(D))`, for `D≠0`.

For K116A, `B` would require a WT-expression titration under the relevant recovery conditions (and the same endpoint), or an equivalent controlled comparison. It is unknown. The observed signal ratio populates `C_amount`; it does not populate `B`. At matched amounts, folding, localization, oligomerization, partner effects or polar effects can still leave `I` uncertain. A direct activity measurement could establish residual molecular activity for a chemistry-specific interpretation, but would remain an A105 measurement linked as a control, not a fabricated A106 catalytic result.

For a hypothetical coexpression experiment, measured `A_mut/(A_mut+A_WT)` would be a molecule fraction only. The phenotype requires an empirically supported response model, particularly for oligomers, dominant interference or dosage thresholds. The full `W,K,R` cellular endpoint and measured nuisance bound would still be used. This paper supplies no such mixture example.

## Restoration, uncertainty, and complete proposed combination

For a declared nonnegative endpoint with a meaningful zero, let reference, perturbed and restored means be `W,K,R`. Let `D=W−K`. Define:

* Signal `θ=(W−K)/(W+K)`, when `W+K>0`.
* Restoration agreement `r=max(0,1−abs(R−W)/abs(D))`, clipped to at most 1. Thus restoration to `W` gives 1, unchanged `K` gives 0, and substantial overshoot is exposed and penalized. Preserve the raw restoration fraction `(R−K)/D` separately.
* `C=product(C_j)` over distinct applicable, measured nuisance-comparability components; quantities already used to construct another component are not multiplied twice.
* `I=max(0,1−B/abs(D))`, with `B` obtained from applicable controls rather than a protein-amount assumption.
* `U=theta_supported/abs(theta)`, where `theta_supported=max(0, min_{joint uncertainty set} signed_expected_theta)` and the result is capped by the point `abs(theta)`. If no defensible uncertainty set exists, `U` is unknown; an exact zero printed after rounding does not justify `U=1`.
* `H` is the measured target-correspondence component defined in the separate cross-case sheet. It is unknown for the supplied annotation target in this packet.

The bounded proposed row contribution for the oriented functional claim is `q=sign(theta)*abs(theta)*r*C*I*U*H`, in [−1,1]. This is a finite scoring convention, not a probability of function, and the signed direction is oriented to the particular claim after evidence gathering. The cross-case draft gives all aggregate and correspondence operands plus a fully filled synthetic calculation. Source omissions leave the complete published `q` unknown; they do not become zeros or qualitative fixed grades. This paper supplies real numerical components and contrasts, not a fully measured all-component score.

## Endpoint boundary and shared evidence

Figure 3 measures **recovery-growth complementation**, with K116A, R232A, K426A and Y382Stop. Figure 6B measures **prolonged-starvation CFU/ml**, at 20 min, 72 h and 120 h, and lists K426A and Y382Stop. There is no K116A survival row. Figure 6A reports SEM, n=3; 6B SD, n=3; Fig. 3 growth curves SD, n=3. Their error conventions and endpoints cannot be interchanged. No exact CFU means have been digitized here.

The same study's shorter lag and poorer late survival are not contradictory repetitions of one outcome. A single broad word such as “fitness” must not erase the endpoint and time. Fig. 2 starvation durations are separate conditions with unknown cross-time experimental dependence; they are not automatically independent replications. WT/deletion controls shared between variant plots also must not be counted repeatedly. CFU and ammonium-consumption checks can improve validity of a recovery-growth interpretation without becoming extra independent restoration experiments.

The Salmonella double deletion and competitive-infection endpoint are not a direct isolated YeaG counterpart to the E. coli recovery assay. Its stated CI is 0.64, but Methods defines mutant/WT output divided by mutant/WT input while Fig. 6C's caption states the inverse. Do not import that ratio, or its direction, into the single-gene recovery score without resolution. It also is not an allele-specific evidence axis.

## Exact population fields and remaining empirical gaps

Future targeted readers (unimplemented) must return: `arm_id`, `chromosomal_genotype`, `plasmid_construct`, `coexisting_wt_present`, `intended_change`, `endpoint_name`, `endpoint_unit`, `time_since_starvation`, `time_since_recovery`, `independent_unit_id`, `shared_control_ids`, `value`, `uncertainty_kind`, `uncertainty_value`, `n_biological`, `n_technical`, `ratio_numerator`, `ratio_denominator`, `source_locator`, `measurement_role`, `normalization_method`, `alternate_source_values`, and `unknown_reason` where needed. For `C_amount`, specifically return the two lane signals, loading denominator and whether signal calibration establishes comparable amounts. For `I`, return the actual nuisance-control endpoint contrasts and their joint bound. For restoration, return matched `W,K,R` on one endpoint and their covariance or raw independent units.

Remaining empirical gaps are finite and explicit: missing raw/paired recovery and survival measurements; unexplained Fig. 3C loading/time normalization; unresolved K426A 1.00/1.12 and strain-label discrepancies; no measured WT amount-response counterfactual at 0.64/0.48/0.96; no direct residual activity for each mutant in these assays; and no target correspondence supplied. These gaps limit this source's populated cells, not the ability to propose a reviewable numerical sheet.

## Inspection/reset coverage

After this primary-paper inspection and before this interpretation, all complete authority files enumerated in local AGENTS.md were reread, together with SOURCE_CORRECTIONS.md, A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md and the complete active ten-axis goal. Latest human direction was read last. The full paths and the earlier index-inspection deviation will be recorded in `coverage_ledger.md`. The full main text's first output truncated a short paragraph; lines 40–55 were reread completely to repair that omission. Main-text “100%” and image “1.12” were independently read and retained. Arithmetic is checked in the later standalone arithmetic record; no reader or production implementation is claimed.

## Additive calculation refinement after cross-case review

The preliminary `U` formula in this packet bounded only the signal component. For the complete proposed score, `a106_numerical_sheet_002.md` supersedes that preliminary formula with a joint bound on the **whole** product, including restoration and isolation. Its `B` also covers separate perturbation and restoration nuisance contrasts. Aggregate signed point contributions before applying their joint uncertainty bound once. Source measurements, missing inputs and experimental interpretations in this packet are unchanged. The standalone rational-arithmetic checks passed; the source's complete contribution remains unknown.
