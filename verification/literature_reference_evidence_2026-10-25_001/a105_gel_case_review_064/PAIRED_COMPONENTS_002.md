# Fresh064 — paired extraction and numerical components, unadopted

This is a bounded research proposal, not a new reader, axis, policy or runtime
integration. SCIENTIFIC_CASE_001.md defines the primary experiment and its limits.

## 1. Preserve useful existing sheet meanings without changing the measurand

The complete current amount implementation has twelve components, including
individual amounts, difference, ratio, reciprocal and their uncertainty. Its
supported cases are `stock_target_mass_estimate_over_total_mass_estimate`
(mg/ml) and `between_arm_nominal_molar_amount` (µM). It deliberately does not
turn nominal amount into active concentration or an amount-response correction.
Those distinctions remain useful. This Fig. 3C case supplies neither supported
case: it supplies relative anti-His signal, not target/total stock mass or
nominal molar recipe amount. Calling 0.64 µM, target mass fraction, purity,
active fraction or direct activity would change scientific meaning.

Proposed research extension: keep a separate relative-signal measurement basis
with explicit observation/normalization relationships. It could feed a future
experimental-comparability sheet shared with A106 and, when actually relevant,
A105. It must not be silently coerced into the current amount contract. Adding
a format reader is not adding an axis. No broad contract change is authorized
by this report.

The historical A105 sheet022/cell005 contains useful source-assay operands
`q`, `g`, `k`, `E`, `h` and covariance arithmetic, plus target/credit proposals.
Only its source-assay meanings are relevant here. Its target mappings, source
pooling and candidate contribution are outside this workload and are not adopted.

## 2. Extracted operands paired to numerical cells

Each row must retain source molecule/construct, ΔyeaG host arm, blot/panel/lane,
reference lane, endpoint, units/basis, origin, experiment endpoint and uncertainty.
Two displayed WT normalizations are separate denominator owners unless source
records establish identity. A printed normalized signal is already a summary;
do not pretend its primitive background-corrected intensities are available.

| Necessary extraction nomination | Proposed numerical cell | Inputs/calculation, units and purpose | Current result |
|---|---|---|---|
| Fig. 3C left lane 2 printed signal and lane 1 reference; Results 64%; K116A construct and complementation linkage | `relative_His_signal` r | Paper-reported lane signal relative to corresponding plasmid WT=1; dimensionless. Quantifies an expression-signal difference outside the intended mutation | 0.64, reported image summary; Results agrees |
| Same, left lane 3 / lane 1; Results 48% | Same r for R232A | Same denominator and meaning | 0.48, reported image summary; Results agrees |
| Right lane 2 / lane 1; Results 100% and image 1.12 separately | Same r for K426A with alternatives | Two incompatible source summaries of the same comparison, not two experiments | `conflicting`; candidates 1.00 and 1.12 retained separately |
| Right lane 3 / lane 1; Results 96%; truncated construct retained | Same r for Y382Stop | Relative anti-His signal; not calibrated equality of full-length molecule abundance | 0.96 |
| Above r with own reference normalization 1 | `relative_signal_difference` δ | r−1; dimensionless signed mismatch from plasmid-WT reference | −0.36, −0.52, conflict {0,+0.12}, −0.04 |
| Above r and positive-ratio condition | `log_relative_signal` l | ln(r); dimensionless fold mismatch, treats reciprocal fold differences with opposite signs | −0.446287103, −0.733969175, conflict {0,+0.113328685}, −0.040821995 |
| Same r only, no added experiment | `relative_signal_squared_deviation` d² | (r−1)²; dimensionless squared mismatch; proposed comparability-loss operand, not confidence | 0.1296, 0.2704, conflict {0,0.0144}, 0.0016 |
| Fig. 3C vector lane printed 0 plus actual background/detection protocol | `blank_signal` / `detection_limit` | Preserve printed author summary separately from measured blank/limit required for subtraction or censoring | Summary token 0 retained; physical background and limit unavailable |
| Lane loading amount/cell equivalent, loading-control intensity, exposure response and standard calibration | `loading_normalized_signal_ratio` / `molecule_amount_ratio` | Defined below; never supplied by printed r alone | Unavailable: loading basis and calibration unreported |
| Independent blots/preparations, raw replicate ratios and covariance of shared WT/control bands | `ratio_variance`, `ratio_standard_uncertainty`, `independent_preparation_count` | Defined below; no inferential precision from a single printed summary or growth n=3 | Unavailable; not 0 variance or n=1/3 |
| Recovery OD600 curves, viable-start control, exact sample linkage to blot | `recovery_endpoint_contrast` | A106-specific lag/OD600 comparison with actual endpoint definition, units and sampling model | No new numerical extraction performed; retained phenotype interpretation only |
| Direct ATPase/kinase rate, blank, contribution controls, actual active amount, reaction calibration | Existing A105 `net_rate`, `attributed_rate`, `corrected_activity`, variance | Source-assay activity cells require their own measured operands | All unavailable from Fig. 3C; no gel-based A105 activity score |

The image summaries and Results percentages are repeated representations, not
independent confirmations. δ, l and d² are deterministic alternative views of r,
not independent evidence or three reliability bonuses. Conflict sets above
are alternatives, not sampling intervals or uniform distributions. Calculating
both alternatives for sensitivity does not resolve the conflict.

## 3. Explicit combination roles; actual arithmetic and limits

**A comparability operand, not a renamed reliability grade.** For a declared
set of same-basis unintended expression differences, a proposed squared
comparison loss is `L_signal = sum_j w_j (r_j−1)^2 / sum_j w_j`. Coefficients
must be declared for a scientifically defined comparison; they are not learned
from the paper. No value or weights are supplied for this YeaG case because
K116A, R232A, K426A and Y382Stop are separate interventions, not four nuisance
features of one intervention. Averaging them would hide which variant failed.
For one K116A contrast only, `L_signal = (0.64−1)^2 = 0.1296`, without needing
an arbitrary weight. This evaluates reported signal mismatch, not overall
experimental reliability. It does not quantify unrelated temperature, loading,
folding or specificity differences. `1−L_signal` is not proposed as a grade.

The sum role is therefore explicit but limited: d² is a potential additive
signal-comparability-loss operand. It must not be added to rate units or to
likelihoods, nor appended again after a model has already accounted for the
same expression measurement. A multi-feature reliability transformation would
need a supported response/measurement model or a separately justified policy;
this case does not supply one. Unknown required comparisons remain unknown.

**When expression can enter a measurement equation.** Let target-band raw
integrated intensities be Tm,Tw; respective backgrounds bm,bw; actual loaded
amounts/cell equivalents be Lm,Lw; response constants be cm,cw in
signal-per-molecule. Then

`r_signal = [(Tm−bm)/Lm] / [(Tw−bw)/Lw]`

`E_m/E_w = r_signal × (cw/cm)`.

The last equation requires an applicable linear, unsaturated response model,
appropriate loading normalization and construct-specific detection response.
Identical His tags do not by themselves establish cm=cw. Fig. 3C reports a
summary r without the four intensity/background operands, load normalization
or response calibration. Therefore the paper cannot populate these equations'
physical E values or the calibration multiplier cw/cm. The printed r values
survive as partial results.

For an actual direct activity comparison with matched units/conditions,
`q=s−b` and `a=(q−g)/(k E h)` remain the existing A105 source-assay equation:
sample/blank sum-difference, contaminating contribution subtraction, and
calibration/amount/condition-response denominators. If a validated relative
amount r_E and reference amount Ew are supplied, `Em=r_E×Ew`; thus `1/r_E`
is a **denominator conversion multiplier** for that same arm's net rate. It
is not an additional evidence-quality multiplier. Comparability correction h
requires a measured same-endpoint response outside the intended change; r_E
does not substitute for h. Direct activity itself does not measure the
growth phenotype's dose response.

**Explicitly synthetic illustration, not YeaG assay data:** suppose loading and
calibration establish r_E=0.64, Em/Ew; matched blank/contaminant-corrected direct
enzyme rates vm/vw=0.20, and rate per enzyme is the relevant comparison. Then
`(am/aw)=(vm/vw)/(Em/Ew)=0.20/0.64=0.3125`. The reciprocal 1.5625 is applied
once in the denominator conversion. It neither becomes a 0.64 reliability
penalty nor an extra 1.5625 evidence bonus. Missing covariance leaves its
standard uncertainty unknown. No such YeaG direct-rate ratio or calibrated
molecular amount was measured here.

**Why that multiplication cannot repair recovery growth:** recovery lag is an
organism/network endpoint with potentially nonlinear, thresholded response to
protein amount. `lag_mutant/0.64` or `growth_difference×0.64` has no established
meaning. A matched WT-expression dose-response curve spanning the mutant's
calibrated abundance and matched mutant-rescue conditions would supply the
needed relation. Only then could the model distinguish a dosage-predicted
phenotype from a sequence-dependent residual. Such residual would enter A106;
it would still not be a direct kinase-rate measurement.

**No coexistence fraction here.** This is ΔyeaG replacement complementation, so
the ratio 0.64 does not mean 64% of a mixed enzyme pool or imply 36% WT remains.
For illustration only, if a different experiment established simultaneous
amounts mutant=0.64 and WT=1, the mutant molar fraction would be
`0.64/(0.64+1)=0.390243902`. That sum is a different denominator from this
paper's plasmid-WT-normalized signal; it must not be used for this case.

## 4. Uncertainty, dependence and diagnostic failures

For positive calibrated quantities X and Y with r=X/Y and full ordered
covariance Σ, `Var(r) ≈ [1/Y, −X/Y²] Σ [1/Y, −X/Y²]^T` and
`Var(ln r) ≈ [1/X, −1/Y] Σ [1/X, −1/Y]^T` are first-order propagation.
When r is built from background, loading, calibration and intensity operands,
use the full gradient over those actual primitives; do not treat a normalized
WT=1 as a physically error-free denominator. Full numerical uncertainty needs
the actual supported covariance or replicate/measurement model. Estimated
variance is not known variance. Shared WT lanes induce possible dependence
across ratios. A105 sheet's `JΣJᵀ + distinct residual` sum can be reused only
on the applicable effect scale and without adding the same uncertainty twice.

Nondetection needs the actual threshold and acquisition model. Printed vector
0 cannot populate positive-background denominators, an infinite signal/blank
ratio or perfect specificity. Missing exposure/loading/calibration is a
measurement gap, not a zero signal or permission for a generic validity factor.
K426A conflict invalidates a unique point for that comparison; unrelated
K116A/R232A/Y382Stop partial values remain available.

## 5. Necessary targeted interpretation, separate from arithmetic

These are proposed aspect-specific instruction questions and finite return
meanings, not a complete sheet inserted into a prompt or a runtime template
already approved by the user. A future implementation needs separate full TASK
and concise STEERING, keeping custody IDs/hashes outside model-facing text.

1. **What quantity does this band readout measure for this source construct?**
   Read panel, lane labels, Results, assay Methods and applicable supplement.
   Allowed: `relative_epitope_signal`, `loading_normalized_relative_signal`,
   `calibrated_molecular_amount`, `total_protein_mass_signal`,
   `activity_coupled_band_signal`, `unknown`, `conflicting`.
   A method name or protein band alone cannot choose a calibrated/active meaning.
   Here: `relative_epitope_signal`; activity/purity meanings unsupported.
2. **Do the compared source molecules coexist or replace one another?**
   Allowed: `separate_replacement_arms`, `same_arm_coexistence`,
   `distinct_preparations_other`, `unknown`, `conflicting`.
   Need genotype/construct evidence and comparison linkage; do not infer from
   protein names alone. Here: separate ΔyeaG complementation arms; per-lane
   sample timing still unknown.
3. **What relationship makes the denominator applicable?**
   Allowed: `same_blot_construct_WT_reference`,
   `different_blot_reference_with_supported_cross_calibration`,
   `loading_control`, `external_amount_standard`, `unknown`, `conflicting`.
   Record independent loading and calibration statuses as `supported`,
   `unreported`, `unknown`, `conflicting`. Here same-blot plasmid-WT reference;
   cross-blot equivalence and calibrated loading unreported.
4. **Which functional assertion and endpoint does this comparison qualify?**
   Allowed: `source_expression_comparability`,
   `source_preparation_mass_purity`, `source_direct_molecular_activity`,
   `perturbation_recovery_growth`, `perturbation_starvation_viability`,
   `unknown`, `conflicting`. More than one relation can be separately recorded
   only with explicit endpoint links, not automatic shared effect credit.
   Here Fig. 3C qualifies expression comparability for Fig. 3 recovery growth;
   Fig. 6B viability is separate and contains no K116A comparison.
5. **Do source summaries agree, and what repeats/controls are actually shared?**
   Allowed agreement: `same_summary_represented_twice`,
   `distinct_observations`, `conflicting_representations`, `unknown`.
   Allowed repetition: `independent_preparations`, `technical_repeats`,
   `repeated_timepoints`, `unspecified`, `conflicting`.
   Here K426A summaries conflict; blot repetition unspecified. Growth n=3
   cannot supply blot n/covariance. Neither repeated text nor complementary
   endpoints establish independence.

`Unreported` means absent from the inspected packet; it is not a claim that
authors never performed the check. `Unknown` covers ambiguity or insufficient
linkage; `conflicting` requires retained incompatible source assertions.

## 6. Exact future reader/calculator needs

- **Document/panel/lane reader:** separate manuscript assay interpretation,
  figure labels and scientific endpoint linkage. Return lane/construct/host,
  intended change, reference lane and typed quantity meaning with source anchors.
  Keep WT denominators distinct, preserve the strain-label issue, and report
  K426A 100% versus image1.12 as conflict. This case first needs printed-label
  extraction, not raw densitometry.
- **Printed numerical-summary reader:** transcribe image-label number tokens
  and Results percent spans independently, preserve `reported_image_summary`
  versus `reported_text`, then deterministic percentage conversion (64/100=.64)
  and cross-representation comparison. Host retains original image/region and
  text custody. It must not call a printed ratio a pixel-derived measurement.
- **Actual densitometry reader, only if later justified:** retain original
  unprocessed image/exposure, explicit lane and band regions, locally estimated
  background regions/model, integrated-intensity definition, clipping/saturation
  diagnostics, loading controls, standard curve/range, response fit and sample
  identities. Output region/background operands and uncertainty model; fail
  specifically on insufficient calibration/loading rather than fabricate amount.
  A JPEG plus visible bands cannot independently validate the instrument range.
- **Relative-signal calculator:** use exact retained summary r or validated
  raw-signal/loading operands; compute δ, ln r, d² with dimensional/basis and
  conflict checks. Preserve original r and unavailable dependencies. A conflict
  set is not averaged. A log requires a valid positive value; nondetection
  cannot be given a pseudocount. No fixed signal-to-reliability conversion.
- **Amount-calibration calculator:** only after scientific input establishes
  response/loading relations, compute r_E and its covariance from supported
  operands. It may supply actual E to the existing source activity equation;
  it must not apply a correction to growth lag or an already amount-normalized
  rate. The existing mg/ml and µM contract remains unchanged by this proposal.
- **Dependence assembler:** bind primitive observation owners across lanes,
  controls, figures and text; identify duplicate summaries, shared WT/control
  denominators, actual independent units, unknown/estimated covariance and
  conflicts. No independent-preparation count from number of lanes/panels.

No functions above were implemented or executed. The only new computation was
transparent scalar research arithmetic on reported summaries and marked
synthetic examples. Root must independently read the source/reset and print
the concrete examples before deciding any later gel implementation scope.
