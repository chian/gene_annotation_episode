# A105 relevance packet 01: TriA/AtzA correspondence

New research note, 2026-10-23. This uses the previously reviewed Seffernick et al. (2001) source for a NEW question, not as a new paper discovery. Citation: *Melamine Deaminase and Atrazine Chlorohydrolase: 98 Percent Identical but Functionally Different*, DOI [10.1128/JB.183.8.2405-2410.2001](https://doi.org/10.1128/JB.183.8.2405-2410.2001). Inspected evidence is the COMPLETE retained `template_a105_reactions_001/06_tria_atza_2001_001.md`; this worker has not freshly reread its primary article. This is sheet research, with no adopted score or implemented reader.

## Define the comparison first

The source assay subject is cloned TriA from Pseudomonas sp. NRRL B-12227, expressed in E. coli DH5α(pJS3), and partially purified. The contrasting protein is AtzA from Pseudomonas sp. ADP, expressed in DH5α(pMD4), highly purified. They are in SEPARATE assays, not a TriA/AtzA mixture. The molecular questions are melamine deamination and atrazine dechlorination. Protein identity is the deliberate changed variable for transfer between these proteins. Purification/active protein amount, substrate exposure, metal loading and assay windows are separate nuisance variables.

There is no supplied target sequence/construct correspondence in this packet. In particular, the project's ybhP sequence is not claimed to correspond to either protein. The examples below explicitly declare TriA or AtzA as the illustrative target; unfamiliar names never establish identity.

The source assay's denominator is milligrams of TOTAL partially purified protein, not milligrams or micromoles of active TriA. The source reported melamine activity is 245 ± 2 nmol/min/mg; duplicate samples are n = 2 and the uncertainty type is unspecified in the retained packet. The panel's atrazine nondetection limit is 0.01 nmol/min/mg under a prolonged screen. This is a censored preparation result, not exact zero or a fully commensurate initial-rate measurement. Raw cross-protein activity ratios would require the missing pure/active protein denominator correction.

## Actual numerical cells and their roles

| Numerical cell | Inputs and calculation | Value | Meaning and limit |
|---|---|---:|---|
| Aligned sequence identity | 466 identical residues / 475 compared residues | 0.9810526316 | Fraction of this complete alignment that is identical. It is NOT the probability that a particular activity transfers. |
| Sequence difference fraction | 9 / 475 | 0.0189473684 | Global magnitude of observed sequence change. A model must learn its relationship to the specified molecular endpoint, or use resolved determinants. |
| TriA preparation melamine/atrazine rate ratio | 245 / 0.01 | >24,500 | Conditional lower bound under the retained assay-window comparability qualification; within-TriA specificity, not a source/target ratio. |
| TriA two-substrate preference | 245 / (245 + 0.01) | >0.9999591853 | Fraction of the declared TWO measured/bounded preparation rates attributed to melamine. Not target relevance or a confidence probability. |

The actual contrast refutes the proposed shortcut `target evidence = assay reliability × 0.9810526316` when that fraction is being interpreted as transferable reaction specificity. It does not refute quantitative source-to-target correspondence. The information needed is endpoint-specific: which sequence/structural differences change the measured reaction and by how much.

## Proposed conversion into the user's numerical sheet

Retain the source activity estimate and its reliability unchanged. For a positive molecular-activity endpoint `a`, source-to-target correspondence estimates a LOG activity difference:

```
d = log(a_target / a_source)
a_target_from_source = a_source * exp(d)
```

`d` is dimensionless and concerns the SAME declared activity, molecular denominator and conditions. It is not a generic functional similarity grade. Activity zero/nondetection uses a censored likelihood and cannot be logged as an invented finite value.

If paired molecular measurements supply `d`, propagate their full covariance. If a measured predictor supplies `d = sum_j beta_j * x_j`, retain each numerical contribution, fitted coefficient units and covariance. Candidate `x_j` can include native alignment score, coverage, mapped specificity-site change, structure/site distances, phylogenetic relationships, and measured system differences. They are distinct inputs whose coefficients must be estimated against paired ACTIVITY outcomes. This packet supplies only the global identity fraction, not fitted coefficients or specificity-determinant effects. The accompanying proposal will define the fitting calculation rather than leave the phrase “calibrated mapping” undefined.

Let `z_source = log(a_source)` with variance `V_source`, and let independently obtained `d` have variance `V_d`. Then:

```
z_target = z_source + d
V_target = V_source + V_d + 2*Cov(z_source,d)
precision_target = 1 / V_target
```

The additive error components and the multiplicative activity correction are the sheet's numerical relevance calculations. Conditional evidence for two specified target log-rate predictions `m1` and `m0` is:

```
log_evidence_ratio = ((z_target-m0)^2 - (z_target-m1)^2)/(2*V_target)
```

This is a proposed contribution to annotation comparison, not posterior annotation probability or final W05 credit wiring. The assumptions and the full likelihood must change for nonlinear, censored or non-Gaussian data.

For a demonstrably identical assayed molecule AND molecular state at the same declared reference condition, `d = log(1) = 0` and the additional identity-related variance is zero because there is no transfer step. This is a factual identity relationship, not an awarded 1.0 relevance grade. Incomplete target snippets cannot establish it. Other condition/state differences still need their own measured correction and uncertainty, once.

For AtzA→TriA reaction-specific transfer, the retained packet does not provide active-enzyme-normalized paired rate data or fitted predictor effects. Thus `d` and target contribution are unknown, while the numerical sequence and specificity cells above remain populated. This is an exact data gap, not a reason to replace `d` with an identity fraction or 0.25/0.5/0.75.

## Comparability, isolation and shared evidence

Comparability requires accounting for different preparation purities, available substrate, active-protein amounts, iron treatment and observation windows outside the deliberate protein change. A measured condition response can correct the rate; the same correction is not multiplied in again as a penalty.

Isolation concerns what fraction of a preparation's measured activity is actually from its named enzyme. Protein mass purity is not that fraction. Quantitative contaminants or matched host-background activities, purification-linked activity and active-enzyme amount would address this separately. Their unresolved error belongs to source assay reliability, not a second source-to-target penalty.

The sequence identity and identity-derived mismatch fraction are two representations of one alignment and must not earn independent factors. The preference fraction and rate ratio are two functions of the same assay panel. If that panel supplies an empirical bridge, its measurements enter the joint likelihood once; they are not independent assay evidence plus independent functional correspondence. HPLC and mass identification support the same product observation rather than two independent reaction rates.

## Full authority reset performed

After reading this one retained paper packet and before interpreting it above, I reloaded and read: root AGENTS.md; GOAL.md; complete docs/EPISODE_STRUCTURE.md; complete docs/TIME_AWARE_ESTIMATION.md; docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md; its TASK_AND_STEERING amendment; EVIDENCE_AXIS_REVIEW amendment; VERBATIM_DIRECTION.md and complete VERBATIM_RECOVERY_002.md; complete EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment; scoring_sheet_numeric_review_002.md; the complete research AGENTS.md; A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md; and the active goal attachment last. The first combined output truncated EPISODE_STRUCTURE/TIME_AWARE content; both were immediately reread completely. VERBATIM_RECOVERY was also reread separately to repair truncation. SOURCE_CORRECTIONS.md and the parent's complete unadopted EXPERIMENTAL_RELIABILITY_001.md were read. The latest narrow assignment requires explicit component arithmetic, modalities beyond sequence, and no architecture or production changes; those directions govern this new use of the retained source.

No new primary dataset, experimental quantity, target relationship or source-to-target fitted coefficient was fabricated. Formulae here are proposals, not conclusions asserted by the paper.
