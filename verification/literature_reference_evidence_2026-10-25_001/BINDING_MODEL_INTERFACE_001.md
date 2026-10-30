# Source binding observation-model components

The adopted GOAL_VERBATIM.txt controls. This follows the parent-reviewed IscR2013
case and BINDING_PARAMETER/RUNTIME_INTERFACES001–003. No new experimental paper
was read for this mathematical increment. The already reviewed primary case
does not report the known joint log-parameter error model required here. Its
printed fit spread/threshold cannot silently supply one. Old saved sheets remain
unchanged. This is an A105 source component family, not another evidence axis.

## Paired source fields, components and scientific meaning

Required extra source input is the actual joint covariance of the two natural-log
parameter estimates, with exact original measurement owners, parameter kind,
known/estimated/unknown status and the censoring/reporting mechanism. Model
interpretation is source-witnessed and conditional. Do not infer these inputs
from minimum experiment count, a fit-to-average spread, protein names, preparation
labels or the mere presence of a bound. IC50 remains an assay response parameter.

Scoring question is test_parameter_exceeds_reference within the same actual
protein/state/experiment, not intrinsic affinity, activation, target transfer or
function probability. All nuisance log parameters range over R. The two regions
are mu_test>=mu_reference and mu_test<=mu_reference; their shared equality boundary
does not manufacture another observation.

Numerical cells exactly log_parameter_contrast,log_contrast_noise_variance,
log_contrast_noise_sd,source_profile_log_ratio,source_signed_index. The first is
the saved native log(test/reference), retaining point/limit meaning. For full
supplied log covariance C, noise variance is Crr+Ctt−2Crt, noise sd its square
root. These describe measurement noise on an uncensored log contrast, not the
sampling SE of an observed censored point or physiological variation.

For two detected points and known normal log errors: e=log(test)-log(reference),
S=e*abs(e)/(2V), B=tanh(S/2). Shared covariance is used once; no extra independent
proof or amount/comparability multiplier is applied. B is a proposed bounded
normalization, not function probability. Synthetic10/20 and C=[[.04,.01],[.01,.09]]
give e=.6931471805599453,V=.11,sd=.33166247903554,S=2.1838773359918244,
B=.7975846370428177. This synthetic example was printed in chat before coding.

For one detected log parameter y_d and one genuine threshold-censored log
estimate at L, use the joint bivariate-normal likelihood, including correlation.
Let vd=Cdd,c=Ccd,vc=Ccc and sc²=vc−c²/vd. At equality mu_d=mu_c=m, omit only
constants common to both hypothesis fits:

ell_equal(m)=−(y_d−m)²/(2vd)+logPhi(s*(m−L+(c/vd)*(y_d−m))/sc),

where s=+1 for a right-censored (gt/ge) observation and −1 for lt/le. The free
region's supremum is0 on this relative scale, reached as a limit by sending the
censored mean in its allowed direction and fitting the point mean to y_d. The
other region's supremum is the global maximum of this concave equality function.
S=direction*(0−max ell_equal), direction=+1 for test-right/reference-left censoring,
−1 for test-left/reference-right. Use log-CDF arithmetic (e.g. scipy.special.log_ndtr)
and an adaptive bracket/derivative root or another demonstrably global concave
solver; no arbitrary finite parameter window, pseudocount, limit-as-point fit or
random numerical integration. Strict/non-strict continuous thresholds share this
likelihood but keep their original native relation. Two-censor likelihood remains
explicitly unsupported in this increment, rather than silently applying the point
formula. Missing scientific information and unsupported model cases stay distinct.

Official numerical API references consulted by parent (not experimental sources):
https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.log_ndtr.html
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html
The likelihood/equality reduction above is the stated mathematical derivation;
those API docs do not establish the scientific observation model for a paper.

## Shared pure model input

Normalized model null or exact JSON-compatible keys:
version=known_normal_log_binding_v1,parameter_kind=ic50|reported_hill_kd,
measurement_order=[reference,test],measurement_keys=[key_reference,key_test],
log_covariance=finite symmetric2x2,
variance_status=known|estimated|unknown,
censoring_model=none|threshold_of_log_estimate|unknown,
log_basis=natural_log_nM,origin=reported|derived|synthetic.
Covariance must be positive definite for this density model; no jitter/default
independence. Same physical operand cannot have contradictory covariance owners.
Known-normal likelihood requires variance_status=known. Estimated covariance can
populate conditional noise cells but not be promoted to known-normal evidence.
Unknown covariance status leaves dependent numerical cells unavailable. One
censored row additionally requires threshold_of_log_estimate. A fitted IC50
reporting limit with an unstated mechanism does not establish that event model.

## Fresh model-calculator ownership

Own ONLY new literature_binding_models.py and tests/test_literature_binding_models.py.
Synthetic inputs only; do not inspect primary papers/packets. Export
binding_model_operand_keys(binding_sheet)->{reference:key|null,test:key|null},
populate_binding_model(binding_sheet,model=None)->{version:binding_model_sheet_v1,
parameter_kind,contrast_meaning:test_parameter_exceeds_reference,
measurement_keys,model,source_uncertainty_basis,minimum_experiment_count,
independent_preparation_count:null,cells,diagnostics,annotation_credit:null}.
Export COMPONENTS,FORMULAS,REASONS for closed host schema. Consume the existing
binding_parameter_sheet_v1; rebuild/validate its normalized native rows through
the existing pure calculator as needed, no source reads or writes. Do not mutate
the source sheet. Preserve raw source scope and aliases/conflicts. Canonical
physical source identity follows existing visual-alias rules; measurement key
is binding_measurement_ + SHA256 of canonical JSON {parameter_kind,physical},
where physical is parsed existing _physical_identity(row). Exact key definition
is shared with source-model parser/repository; no key inferred from equal values.
Return null keys for ambiguous/unreported/missing/conflicting arm selection.

Each cell has value:number|null,relation:eq|gt|ge|lt|le|unreported,
unit:dimensionless|log_parameter_squared,
status:populated|reported_limit|unavailable|conflicting,
formula:finite string,origin:derived|proposed,unavailable_reason:finite code|null,
bound_kind:reported_limit_arithmetic|null,confidence_bound:null,
parameter_identification_bound:null,conditional_on:[finite codes].
Conditional codes supplied_log_covariance,known_normal_log_parameters,
threshold_censoring_of_log_estimate as applicable. Never label a likelihood
as a reported limit or a confidence interval. e preserves raw limit meaning;
S/B are point calculations conditional on the declared model. Keep diagnostics
conditional/noise/boundary-fit quantities distinct from observations.

Model null -> usable native e plus binding_sampling_model_unreported for dependent
cells, correcting the earlier descriptive family's unimplemented status only in
this new explicit selected result. Other required unavailable codes include
known_log_covariance_required,covariance_status_unknown,
binding_censoring_mechanism_unreported,two_censored_observations_unsupported,
nonfinite_calculation,numerical_model_range plus actual base selection reasons.
Invalid malformed/ownership/covariance inputs raise ExperimentalContractError;
unavailable source information/unsupported observation cases preserve partial
cells. Do not manufacture exact0 or1 from numerical underflow/overflow. Known
equal point estimates can legitimately yield S=B=0. Include meaningful symmetry,
correlation, missingness, alias/conflict, positive/negative, censor-vs-point,
extreme/numerical-range and independent numerical verification tests.

## Fresh model-source reader ownership

Own ONLY new literature_binding_model_inputs.py and tests/test_literature_binding_model_inputs.py.
Synthetic source fixtures only. Export read_binding_model(source,*,parameter_kind,
measurement_keys). source exact {source_ref,artifact_ref,content:bytes}; strict
UTF8 JSON of the exact model shape above. Reject duplicate keys/nonfinite JSON,
wrong ordering/kind/keys/log_basis/unknown fields and malformed scalar/matrix
types. Validate finite covariance shape and exact owner keys; positive-definite
numerical model validation belongs to calculator. Return {model:normalized_model,
source:{source_ref,artifact_ref}}. No source acquisition, model call, interpretation,
matrix estimation, unit inference, count inflation or fallback data. Reuse common
ExperimentalContractError(code,field). Root validates actual receipt/scope/lineage.

## Root selected integration ownership

Root owns new literature_binding_model_storage.py, services/binding/prompt glue,
typed parent forms, assembled checks and retained examples. New selected ordinary
tool literature.binding.model.populate consumes a received actual selected binding
sheet, optional received model_source_ref and literal model witnesses. Model
numbers come solely from that retained source artifact. No numerical tool args.
No separate model report composer, scientific acceptance gate, new episode or
observation/progress policy. Exact return namespace is literature_binding_model_cells;
requested_binding_model_components selects only requested cells. Provenance includes
binding sheet, actual original evidence source, optional model source, witnesses
and exact measurement owners. Old descriptive sheets and live_pin004 stay intact.
