# Proposed binding portion of the A105 numerical sheet

Research synthesis, 2026-10-23. This is a proposed numerical portion of the user's sheet, not a new evidence axis, overall paper grade, approved scoring policy, reader implementation or completed A105 sheet. Eleven assigned remaining primary papers were inspected individually with complete post-paper authority resets. NlpI PMC7049810 and RbkR PMC5397151 belong to the prior completed worker; they were not repeated or added to this count. The common parent proposal `a105_sheet_construction_001/EXPERIMENTAL_RELIABILITY_001.md` was not used as authority or assumed adopted.

The experimental unit is a measured molecular binding inference in a defined preparation and context. A paper is not the unit, and a ratio is not automatically an annotation score. The scoring meaning follows the inferred quantity: controlled association, equilibrium affinity, retained capture after washing, competition selectivity, or change in binding. The reader must retain the actual endpoint instead of converting all of these to an invented Kd.

## Numerical cells and deterministic calculations

Supporting descriptions of construct, organism, mixture, intended variable, preparation identity, controls, units and source locations are necessary to interpret the numbers. They do not themselves become numeric scores. The proposed cells below have measurable operands; missing operands remain unknown. Bounds retain their direction and basis. The formula letters are labels for numbers, not ordinal grades.

| User consideration | Numerical cells | Calculation and meaning |
| --- | --- | --- |
| Signal | Corrected response y; contrast d; fitted Kapp, IC50 or rate constants when justified | Detector-specific calibration/background correction first; then a declared difference, log ratio or fitted curve. Response magnitude is distinct from support for a molecular inference. |
| Specificity / isolation | Specific-minus-alternative contrast s; residual unwanted contribution b_iso; uncertainty v_iso; active concentration and mixture fractions | Same-condition alternative substrates/partners and controls identify unwanted contributors. Mixture fractions enter the response model and concentration, not a generic discount. |
| Comparability outside intended variable | Nuisance condition differences Delta_x; measured response sensitivities beta; resulting correction b_cmp and uncertainty v_cmp | `b_cmp = beta^T Delta_x` locally, or a validated nonlinear response difference. Exclude the deliberately tested variable. Comparability is measured by its consequence for this response; no raw ratios of pH, time or salt. |
| Measurement validity and named weaknesses | Calibration gain g and its uncertainty; brightness q; recovery r; depletion fraction; residual/model discrepancy | These parameters correct the actual response and/or its uncertainty. A missing calibration is not a fixed score. Complementary experiments target a named alternative explanation. |
| Uncertainty | Covariance of calibrated response/parameters; interval/bound; sampling variance v0 | `Var(f(u)) ≈ J Cov(u) J^T` for a justified local approximation, or a full response likelihood. Preserve source SD versus SE versus fit error distinctions. |
| Consistency / replication | Independent preparation count; between-preparation variance tau²; matched-effect discrepancy Q | Count real preparations, not lanes/time points/papers. Fit a preparation-level model. Different endpoints or changed molecular states require different observation models. |
| Target/system relationship | Measured relationship parameters a,b (or a specified nonlinear model) and their uncertainty | Map the source molecular effect to the target effect with experimentally/calibrationally supported relationships, not only sequence scores and not an overall transfer label. |
| Contribution to annotation scoring | A target-effect estimate and uncertainty, plus a declared model-comparison contribution ell with bounds | Numerical combination is explicit below. Source measurements, derived components and proposed transforms stay separate. A z statistic alone is not the final annotation contribution. |

### Observable-to-response calculations

Use these only under the named conditions; they are alternative measurement models, not extra independent points to sum.

- **Fluorescence anisotropy:** for one free/bound pair with brightness ratio q=brightness_bound/brightness_free, `f = (A-A_free)/((A_bound-A)*q + A-A_free)`. Unknown q or multiple brightness classes require an appropriate model. An anisotropy axis is not already a fraction bound. Fitted endpoints share uncertainty with every point normalized by them.
- **EMSA:** with background-corrected, comparably detected labelled-DNA counts, `f_shift = sum B/(U+sum B)`. Include material retained in wells/smears according to a declared recovery rule. This is the fraction retaining a shifted state through the procedure. Equilibrium occupancy requires that the separation preserves the relevant complexes or a measured dissociation model.
- **Affinity capture/precipitation:** `m_j=(signal_j/g_j)*(fraction_volume_j/loaded_volume_j)` and `f_recovered=m_bound/m_input`, or `f_pellet=m_P/(m_P+m_S)` when both fractions are quantified. Recovery controls and protein-specific calibration are essential. Neither washed capture nor zinc precipitation is a binding isotherm by itself.
- **SPR:** a possible double-reference response is `(R_pair-R_reference) - (R_buffer,pair-R_buffer,reference)`. Carry all covariance from shared reference channels and buffers. Association/dissociation fitting needs a stated kinetic model and examination of transport, rebinding and surface activity. A steady-state curve and kinetic parameters derived from the same trace are not independent evidence.
- **Direct equilibrium affinity:** under a justified 1:1 model, `bound = (P_a + L_t + Kd - sqrt((P_a+L_t+Kd)^2-4*P_a*L_t))/2`, and `f=bound/L_t`. `P_a` is active binding-site concentration, not necessarily total monomer concentration. The free-ligand approximation is a separate simplification. Cooperative/multisite or mixed-state proteins require a different mass-balance model. A Hill coefficient is not automatically the count of protomers bound.
- **Competition:** IC50 retains its actual concentration-response meaning. Converting it to an intrinsic competitor affinity requires the competition, active-site, free-concentration and depletion model. Unspecified protein/dye concentrations or heterogeneous nonspecific DNA prevent that conversion.
- **Crosslink capture:** a limited model is `fraction_trapped = fraction_occupied*c_capture + b_capture`, where capture efficiency and background need measurement. A negative crosslink lane does not imply unoccupied protein when capture efficiency is unknown.

### Keep the two user questions separate

For a measured contrast d on its natural meaningful scale, calculate

`d_source = d_calibrated - b_cmp - b_iso`.

`b_cmp` is the response difference predicted from changed conditions outside the intended variable. Examples of operands are ionic strength, temperature, effective dose, construct differences and state at measurement, but only if a response model quantifies their effect. `b_iso` is an unwanted contributor to the measured signal after that condition comparison: nonspecific capture, contamination, mixed active populations or another signal-producing molecule. The same uncertainty must not be filed under both. Which variable is intended must be explicit: total PMS exposure and pure redox-state change are distinct comparisons.

Use `v_source = Var(d_calibrated - b_cmp - b_iso)` with full covariance. In an independent-component approximation the sum is

`v_source = v_sampling + v_calibration + v_comparability + v_isolation + v_between_preparations`.

That last term depends on the estimand: predictive variation for a new preparation is different from the sampling variance of a mean across n preparations. Shared calibration/background uncertainty does not shrink as if it had been independently remeasured n times.

A measured correction and its residual uncertainty are different: subtracting an estimated bias and carrying uncertainty in that estimate is appropriate. Subtracting a bias and then penalizing its full magnitude again through an arbitrary multiplier is double correction. If only a defensible bias bound is known, carry an interval/sensitivity calculation; do not assume that the bound is a Gaussian SD.

### Quantitative relationship to target/system

The simplest worked relationship is `theta_target = a*theta_source + b`. a and b must be estimated from a relevant paired measurement/calibration or derived from established identity under explicitly identical relevant conditions. They are not assigned from a 'close homolog' label. Measured molecular identity, structural/interface correspondence, evolutionary relationships, context and functional interchangeability can inform an appropriate relationship model, but raw measurements on those different scales cannot simply be multiplied together.

With independent uncertain a, source effect and b, the exact variance of the linear-product expression is

`v_target = a²*v_source + theta_source²*v_a + v_source*v_a + v_b`.

With dependence, use the joint distribution/covariance rather than this independent formula. A local nonlinear mapping uses its Jacobian with parameter and residual uncertainty. Preserve the source's binding measurement separately from the target prediction. None of the reviewed examples establishes a numeric relationship to the project's ybhP target. That relationship is a missing operand, not grounds for a default factor of 0.5 or automatic identity weight of 1.

The relationship must also preserve the functional inference. A binding assay can distinguish binding from its measured background. It does not by itself distinguish 'binding activates transcription' from another mechanism producing the same binding observation. If two *specified* models predict exactly the same binding data, their binding likelihood ratio is 1 (log contribution 0) for that distinction. An unspecified model is unknown, not an assumed likelihood ratio of 1.

## Explicit combination and full synthetic worked example

This example illustrates a proposed calculation, with invented inputs. It is not paper data, a target experiment, a real dataset analysis, a calibrated universal reliability scale or an adopted contribution. The intended quantity is a controlled binding-fraction difference predicted for a new comparable preparation. All uncertainty terms below are stipulated independent for illustration.

| Numerical component | Synthetic input/calculation | Value |
| --- | --- | ---: |
| Observed detector-scale contrast | measured difference | 0.40 |
| Calibration gain | separately estimated response gain g | 0.80 |
| Calibrated contrast | 0.40/0.80 | 0.50 fraction units |
| Comparability correction outside intended variable | beta^T Delta_x | 0.05 fraction units |
| Unwanted-contributor correction | independent background/contributor estimate | 0.10 fraction units |
| Controlled source effect | 0.50−0.05−0.10 | 0.35 fraction units |
| Sampling variance after calibration | supplied estimate | 0.0004 fraction² |
| Calibration variance contribution | supplied propagated estimate | 0.0001 fraction² |
| Comparability variance contribution | supplied sensitivity/model uncertainty | 0.0009 fraction² |
| Isolation variance contribution | supplied unwanted-contributor uncertainty | 0.0016 fraction² |
| Between-preparation predictive variance | supplied tau² | 0.0004 fraction² |
| Source predictive variance | sum of five preceding variance components | 0.0034 fraction² |
| Target relation slope and offset | independently measured hypothetical a,b | a=0.80; b=0.01 fraction |
| Relation-parameter variances | hypothetical v_a,v_b | 0.0025; 0.0004 fraction² |
| Target effect | 0.80×0.35+0.01 | 0.29 fraction units |
| Target variance | 0.80²×0.0034 + 0.35²×0.0025 + 0.0034×0.0025 + 0.0004 | 0.00289075 fraction² |
| Target SE | sqrt(0.00289075) | 0.0537656954 fraction |
| Standardized effect | 0.29/0.0537656954 | 5.393773817 |

The calibration gain and relationship slope happen to share the synthetic value 0.80; they describe different quantities and are stipulated independently estimated. They are not the same calibration used twice. The source calibration variance here is an already supplied propagated contribution. If it is estimated through a nonlinear ratio, its approximation/model must be recorded.

For an explicit contribution to annotation evidence, define the predictions to be compared. Under a stipulated Gaussian predictive approximation with the same variance, suppose model H1 predicts target contrast delta1=0.25 and model H0 predicts delta0=0. The proposed log-likelihood contribution is

`ell = ((d_target-delta0)^2 - (d_target-delta1)^2)/(2*v_target)`

`= (0.29² - 0.04²)/(2×0.00289075) = 14.26965320`.

This has natural-log evidence-ratio units. It is not a posterior probability. Normality here is a model approximation; a product of uncertain variables is not automatically Gaussian. A different stated H1 changes ell, which is appropriate: evidence is for a particular molecular inference. Choosing H1 retrospectively to maximize fit and then calling that the same fixed-model likelihood ratio would overstate support; composite hypotheses require an explicit fitted/predictive model and treatment of estimation.

For independent data blocks, `L_binding(H1,H0)=sum_b ell_b`; likelihood ratios multiply as `exp(L_binding)=product_b exp(ell_b)`. With common controls or relationship parameters, evaluate one joint likelihood and integrate/profile shared quantities under an explicitly defined method. Do not add single-pair ratios while pretending the shared control is independent each time. A contradicted inference can receive a negative log contribution. Zero measured effect with tight precision and zero measured effect with poor precision are different data.

### If the sheet needs explicit multiplicative component displays

The variance calculation already combines the components. It can also be displayed through conditional precision-retention factors without adding a second adjustment. Express every variance in target-effect units. For the example these are sampling 0.000256; calibration 0.000064; comparability 0.000576; isolation 0.001024; between-preparation 0.000256; relation 0.00071475. The final relation term contains the a,b and product uncertainty contributions shown above.

With cumulative variance V starting at sampling variance, each factor is `sqrt(V_before/V_after)`. In the fixed display order calibration→comparability→isolation→between-preparation→target relationship:

| Component display | Explicit factor | Synthetic value |
| --- | --- | ---: |
| Calibration retention | sqrt(0.000256/0.000320) | 0.8944271910 |
| Comparability retention | sqrt(0.000320/0.000896) | 0.5976143047 |
| Isolation retention | sqrt(0.000896/0.001920) | 0.6831300511 |
| Preparation consistency retention | sqrt(0.001920/0.002176) | 0.9393364366 |
| Target-relation precision retention | sqrt(0.002176/0.00289075) | 0.8676092595 |

`baseline standardized effect = 0.29/sqrt(0.000256) = 18.125`.

`18.125 × 0.8944271910 × 0.5976143047 × 0.6831300511 × 0.9393364366 × 0.8676092595 = 5.393773817`.

These are continuous calculations from variance operands, not category labels. Their product equals the single total-variance calculation; **do not multiply these factors into ell or z again**. Individual factors depend on display order and baseline precision, so they are conditional descriptions of uncertainty retention, not standalone absolute experimental-relevance grades. Increasing sampling noise can increase a conditional retention ratio while worsening final evidence; report the underlying variance and final result together. With correlated contributors there may be no unique nonnegative variance partition; use the full covariance calculation instead of manufacturing five factors. Unknown variances must not become a factor of 1. This limitation is an explicit design choice for discussion with the user, not a settled common grading scheme.

## Missingness, bounds, nonsaturation and repetition

- No binding assay means no observed binding result. It is distinct from a measured nondetection and from measured zero with uncertainty. An empty experiment set adds no likelihood term; that accounting identity is not a negative finding about binding.
- A source-reported lower bound on Kapp/IC50 remains a bound. Use an appropriate tail/interval likelihood only if its generation and uncertainty model are known. An unsaturated curve with unknown amplitude does not itself prove that Kd exceeds the highest protein concentration.
- For a known detection limit c and a specified observation distribution, a nondetection contributes `log Pr(y<c | H1)-log Pr(y<c | H0)`. Missing c or assay sensitivity leaves this quantitative contribution unknown.
- Equivalence is a separate inference from failure to find a change. A possible descriptive component is `(epsilon-abs(d_corrected))/SE(d_corrected)`, with an explicit meaningful tolerance epsilon. It needs uncertainty and is not a probability. A visual 'same shift' cannot fill it.
- For genuinely comparable preparation-level effects, estimate between-preparation variance and/or `Q=(d-d_bar*1)^T Sigma^-1(d-d_bar*1)` with covariance and appropriate parameter estimation. Variation due to a measured changed state/condition should first enter its model, not an unexplained penalty.
- Parameter estimates, derived percentage activity, fitted curves, plots and source prose referring to one assay are one measurement lineage. Independent purifications, independent condition changes and orthogonal controls have different roles. A second method addressing an artifact is complementary evidence, not automatically an independent repeat of the same endpoint.
- A shared calibrant, blank, baseline curve or source-to-target relationship couples measurements even across different papers. Reprinted old values and narrative citations add no new experiment. Reused quantities must appear once in the joint data structure.

## Source-to-component map

Individual packets contain exact source values, organism/construct definitions, calculations, limitations and full reset provenance. This table is a navigation map to those packets; it does not reprint multiple experimental packets together. The component meanings are defined above.

| Source and individual packet | Numerical component(s) informed |
| --- | --- |
| Bowman et al. 2008, PMC2745220 — `paper_01_popz_2745220_001.md` | SPR reference-response arithmetic; concentration/dose definitions; condition-dependent comparison; missing fitted uncertainty |
| Ebersbach et al. 2008, PMC2614312 — `paper_02_popz_2614312_001.md` | Capture recovery calibration and shared standards; mass versus molar normalization; oligomer-size measurement interpretation |
| Fleischhacker et al. 2012, PMC3447993 — `paper_03_iscr_3447993_001.md` | Binding-state definition; equivalence versus visual similarity; endpoint brightness; read together with later qualification in packet 10 |
| Nesbit et al. 2009, PMC2709974 — `paper_04_iscr_2709974_001.md` | Apparent affinity, fluorescence brightness correction, depletion/stoichiometry, competition contrasts and shared-reference covariance |
| Rajagopalan et al. 2013, PMC3676455 — `paper_05_iscr_3676455_001.md` | Specificity contrasts distinct from one affinity; censored competition ratios; preparation/cofactor mixtures; duplicated derived percentages |
| Giel et al. 2013, PMC4108476 — `paper_06_iscr_4108476_001.md` | Nonsaturation versus a reported quantitative bound; active-dose assumptions; same-protein/different-site covariance |
| Kessler et al. 2001, PMC94954 — `paper_07_nifi_94954_001.md` | No direct binding measurement versus zero binding; endpoint/axis separation |
| Sarwar et al. 2016, PMC4894688 — `paper_08_gcsr_4894688_001.md` | Gel-shift fractions and sequence-specific controls; first detected shift versus Kd; matched competition doses |
| Noirot-Gros et al. 2006, PMC1413692 — `paper_09_yaba_1413692_001.md` | Calibrated precipitation fraction; capture efficiency; three-component mixtures; unequal alternative-control concentration |
| Banerjee et al. 2025, PMC12594620 — `paper_10_iscr_12594620_001.md` | Molecular state at readout; additive qualification of earlier interpretation; cross-buffer comparison; source-rounded versus derived bound |
| Wagner et al. 2014, PMC3911195 — `paper_11_malr_3911195_001.md` | Assay-equivalence uncertainty; host/tag/buffer differences; DNA mass/concentration denominator consistency; carryover isolation |

The prior worker's NlpI/RbkR packets remain separate; this synthesis does not imply that their raw data or proposed components were freshly inspected here.

## Exact fields the eventual reader must populate

These are sheet operand definitions, not a separate generic reader design. No reader functions are implemented in this research work.

1. **Measured response operands:** numeric detector readings, units, blank/reference readings, concentrations with their molecular unit (monomer/dimer/site/molecule or mass), loaded/total volumes, DNA/ligand identity and amount, measured time, calibration curve and covariance, brightness/recovery measurements, active concentration and measured state fractions.
2. **Derived assay result:** response-model identifier and parameter definitions, numeric response/contrast/parameter estimate, units, transformation, uncertainty type/value and confidence level where applicable, bound direction/value and its basis, full covariance or exact missing entries. Existing source values and a reader's refit must stay separately identified.
3. **Comparability operands:** intended variable specification, other measured condition differences with units, response sensitivity/model and covariance, `b_cmp`, `v_cmp`, and observed/predicted-range limits. Missing sensitivities remain unfilled.
4. **Isolation operands:** measured unwanted response contributors, their calibration and mixing model, `b_iso`, `v_iso`, and overlap with comparability/calibration terms. Distinguish absent interference from interference not assayed.
5. **Replication/consistency operands:** preparation/group identities attached to numeric observations, source covariance, estimator of between-preparation variance, repeated-condition contrasts, and count of actual independent preparations. IDs are provenance, not numeric evidence weights.
6. **Target relationship operands:** source and target molecular/system identity, actual comparison measurements, specified relationship function and fitted/derived parameters, parameter covariance, residual uncertainty, and validated domain. Do not accept only an opaque relevance number.
7. **Combination operands:** the functional inference/models emerging from investigation, their predicted observations, the observation distribution and dependent blocks, resulting `ell`/bounds, and the exact observations already consumed. A source measurement cannot earn a second likelihood term merely because another sheet cell reproduces it.

The proposed interface to annotation scoring is a hypothesis/scope-specific signed log-evidence contribution plus its underlying filled components, model assumptions, dependence and unresolved operands. The parent must decide and show how that contributes to the common A105 and annotation score. This document does not silently install a global rescaling, prior or cross-axis aggregation. A single scalar forced from an undefined target mapping or unspecified competing model would be unfinished work.

## Exact remaining work and inspection limits

The binding sheet still needs empirical calibration/testing of nuisance response models, contributor/active-state models and target correspondence; a justified set of model predictions/observation distributions for evidence compilation; treatment of incomplete but informative qualitative curves without invented uncertainty; an adopted choice of what the comparability/isolation display should mean; and integration with the parent's common A105 score. A real raw binding dataset must demonstrate the proposed fields and dependence calculations. The synthetic example here does not satisfy that empirical dataset requirement. Reader implementation and cross-axis annotation wiring remain separate later responsibilities.

Paper-specific missing inputs and failed supplement access are recorded in each note. Neither source PDFs/supplements not opened nor unshown control data were treated as inspected. No calibrated gel digitization, raw-data reanalysis, target sequence relationship, production scoring run or scientific experiment was performed. Formula arithmetic was checked with Python; the exact synthetic calculation receipt is `synthetic_component_arithmetic_001.json`. Two earlier decimal slips in packets 04 and 06 were corrected by additive notes in those same files. The newer IscR qualification is additive in packet 10.

SOURCE_CORRECTIONS.md heading discovery found only the YeaG correction; that unassigned A106 evidence was not imported into this binding synthesis. Each source was reset individually before scoring interpretation; synthesis uses those completed interpretations and the final complete authority reset, without bulk rereading prior packets or treating memory as a substitute for the required per-paper authority reads. No completed scoring-sheet count is claimed.
