# Paired extraction and numerical components

Research proposal in sections of the same logical A105 sheet. No new evidence axis, mandatory episode, software suite or final quality grade.

| Extracted source observation | Numerical component and calculation | Meaning, qualification and combination |
|---|---|---|
| Fig.4A original image: initial ordinate, enzyme-addition location, displayed dashed baseline intercept, selected late trace point; exact original pixel coordinates and reading bounds | D_total=A0−AT; D_fast=A0−B0; D_tail=B0−AT; F_tail=D_fast/D_total | Endpoint decomposition, not initial rate. Here pixel differences 142,131,11 and F≈0.9225; D_fast=F*D_total and D_total=D_fast+D_tail. Same trace; not independent evidence. |
| Source witness for extrapolation and continuing reaction; assessed model applicability | Conditional applicability of the preceding numerical components | Baseline linearity/extrapolability, completed fast phase, same endpoint and preparation must be supported or explicitly conditional. Presence of a dashed line alone does not establish physical causality. Unknown/conflicting interpretation leaves the corresponding unconditional estimate unavailable. |
| Fig.4B/main text: approximately 0.6 mol MTZ reduced/mol CoM-S-S-CoB added, already corrected | Reported corrected stoichiometric ratio r≈0.6; relative excess r/0.5−1≈0.2 | The excess addresses one ideal coupling model. It is not a contamination probability. Preserve original corrected-stage status; do not multiply r by F_tail again. |
| Stated four-electron MTZ and two-electron disulfide reduction; limiting-ratio context | Electron accounting H2/disulfide=1+2r≈2.2 | Explicit sum/multiplier under the stated electron-account model. Not an independently measured H2 rate. Reported r≈0.5–0.7 across conditions maps to≈2–2.4; not a CI. |
| Native alternative homodisulfide control activity `<2 nmol/min`, assay volume0.75mL, concentration regime `<1mM`, exact prose endpoint scope | Upper threshold G=2/0.75=8/3 µM/min; the rate remains strictly less than G | Finite native control bound. No zero substitution, half-threshold point, SD or confidence interpretation. Specific endpoint/sample/additivity relationships to a proposed q remain unknown; no isolated Fig.4 rate follows. |

The first row is **graph-derived**; source-stated ratio, bound, volume and electron counts are **reported**; arithmetic results are **calculated**; the physical decomposition's applicability is a **scientific interpretation**. No synthetic experiment is introduced. The manual coordinate enclosure is a reading qualification, not experimental uncertainty.

## Proposed typed meanings, separate from numerical cells

An endpoint-contributor selection should retain source/preparation/endpoint/condition, measurement_stage=`endpoint_amplitude|initial_rate|other|unknown|conflicting`, correction_stage=`not_applied|already_applied|unknown|conflicting`, contributor_basis=`matched_control|source_extrapolation|molecular_identification|reported_limit|unknown|conflicting`, and an exact source witness. These are scientific meanings, not category-coded scores.

For source_extrapolation preserve the actual selected trace/axis calibration, initial ordinate and t0, late-window coordinates, displayed-versus-newly-fitted line, estimator and baseline covariance if reported, and model_applicability=`supported|explicit_conditional_scenario|unsupported|unknown|conflicting`. A displayed line can be read without pretending to refit raw experiments. A newly estimated line must be labelled graph-derived and must retain fit choices and their uncertainty. This packet uses only the displayed line; it does not fit the original biochemical time series.

For a contributor limit preserve strictness, species/endpoint, scale, denominator, preparation relationship, conditions, concentration regime and additive-versus-regenerating mechanism. Native bounds remain available when eligibility for subtraction is unknown. The existing point g route remains unchanged and usable for a genuine matched point estimate.

## Numerical uncertainty and dependence

For D_fast=A0−B0, Var(D_fast)=Var(A0)+Var(B0)−2Cov(A0,B0). For B0=alpha+beta*t0 at a fixed selected t0, Var(B0)=Var(alpha)+t0^2 Var(beta)+2t0Cov(alpha,beta). If t0 is uncertain its uncertainty and covariance require a further declared model. For F=D_fast/D_total, propagate the joint covariance of the actual shared quantities; D_fast and D_total share A0. Missing physical covariance is not zero. Source uncertainty of the published corrected ratio is not supplied by the pixel-reading enclosure.

For supported nonnegative additive g in [0,G) and a known same-scale net rate q, the conditional constraint would be q−G<r<=q, before any applicable positive calibration/amount factors. This paper does not establish all of those relationships for Fig.4, so no numerical q−g interval is populated. The source control's numerical G is retained without smuggling in a matchedness judgment.

## Populator status

The research script verifies source witnesses, original-raster coordinate readings, exact ratio/interval arithmetic and explicit current compiler guard behavior. It is not a registered production operation. Existing q/g point reading and within-assay arithmetic are reused conceptually; a completed selected endpoint-extrapolation path is not established. Any native-prose bound-reader reuse still needs its actual complete consumer path inspected. The table-bound function inspected here alone does not prove it.
