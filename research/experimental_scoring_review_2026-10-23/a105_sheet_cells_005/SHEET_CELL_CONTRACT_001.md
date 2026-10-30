# A105 numerical cell contract — synthetic single-source example

2026-10-23. **Unadopted sheet/interface proposal.** The populated result is
`S = 2.078347031`, `B = 0.777561486`, `R = 0.792985576`,
`D = 0.616595043`, and proposed `c = max(0,D) = 0.616595043`.
These are conditional numerical components, not an annotation probability or
an implemented A105 scorer. All example inputs are **SYNTHETIC**.

This compact port starts at the supplied, already corrected source activity
and its propagated variance components. Those are **upstream derived inputs**,
not raw detector readings. The separate native correspondence scores/counts
and condition differences are input cells. The calculations below populate
the derived scoring cells. No independent generic reader design is proposed;
the function labels name arithmetic to be implemented separately against these
exact cells. Investigation prompt text remains a separate responsibility.

## Scope and numerical inputs

The declared endpoint is source-attributable formation of the specified product,
per amount of assayed source molecule per minute at the reference assay state.
The source comparison is positive physical activity `a > 0` versus `a = 0`;
the supremum includes the boundary. The target output is a conventional support
index for that same molecular capability through the measured correspondence.
It does not assert a target rate, substrate preference, physiological importance,
or a binding/transport consequence of an unmeasured endpoint. Target and source
are distinct hypothetical molecules. Supplied sequence/file material can define
the target; no initial function, searchable name, or target experiment is needed.

All scalar numeric types below mean finite numbers. Unknown values use `null`
plus the missing reason; zero is an actual value. Units and denominators are
fixed by this table, not inferred from a field name. The JSON record uses the
same paths under `input` and `derived`.

| Exact input cell | Type; unit and denominator | Population responsibility; synthetic value |
|---|---|---|
| `assay.corrected_activity` | Float; min^-1 = amount product / (minute × amount source molecule) | Copy the upstream corrected activity, **0.68**. Its definition is `(sample_rate-blank_rate-contaminant_rate)/(recovery*protein_concentration*condition_response_ratio)`. The three rates use amount/volume/minute; protein concentration uses the same amount/volume; recovery is measured/expected calibration response; condition ratio is comparison-test/comparison-reference response on the same endpoint. Raw assay operands are not supplied by this port and are not invented. |
| `assay.propagated_variance.measurement` | Nonnegative float; min^-2 | Upstream propagated sample/blank uncertainty: **0.0256**. |
| `assay.propagated_variance.recovery_calibration` | Nonnegative float; min^-2 | Upstream propagated recovery uncertainty: **0.001156**. |
| `assay.propagated_variance.experimental_comparability` | Nonnegative float; min^-2 | Upstream uncertainty of condition correction **outside the deliberately varied factor**: **0.00296225**. |
| `assay.propagated_variance.effect_isolation` | Nonnegative float; min^-2 | Upstream uncertainty of contaminating contribution/attribution correction: **0.0144**. This is distinct from comparability. |
| `assay.propagated_variance.protein_amount` | Nonnegative float; min^-2 | Upstream propagated amount uncertainty: **0.004624**. |
| `assay.propagated_variance.distinct_between_preparation` | Nonnegative float; min^-2 | Distinct residual preparation variation already expressed on the scored-effect scale: **0.0625**. Do not divide it by an invented preparation count. |
| `assay.covariance_cross_term_sum` | Float; min^-2 | Sum of applicable `2*J_i*J_j*Cov(x_i,x_j)` terms. **0** is an explicit synthetic zero-cross-covariance assumption, not a missing-data default. |
| `sequence.pair_raw_score`, `source_self_raw_score`, `target_self_raw_score` | Three nonnegative floats; same raw alignment-score unit | Supplied raw pair/self scores **240, 300, 320**, from one compatible local scoring convention. Denominator is the sum of the two self scores. These are not arbitrary HMM bit scores. |
| `structure.tm_source_normalized`, `tm_target_normalized` | Two floats in [0,1]; dimensionless | Native TM-score values **0.90, 0.85** with source and target normalization directions retained. |
| `site.declared_count`, `observed_count`, `exact_match_count` | Integers; residue/contact counts; `0 <= matches <= observed <= declared` | **10, 10, 8**. The denominator is all ten predefined functional sites, all observed in this example. |
| `evolution.eligible_tree_replicates`, `supporting_tree_replicates` | Integers; `0 <= supporting <= eligible` | **100, 85**. Count support for the same predefined placement against the specified alternative, not a newly selected favorable clade. |
| `system.descriptor_difference` | Two floats; target-minus-source `[degrees C, pH units]` | Supplied differences **[7, 0.5]**. Absolute conditions are not inferred from differences. |
| `system.reference_scale_covariance` | Symmetric positive-definite 2×2 matrix; entries in products of descriptor units | **[[100,0],[0,1]]**. Diagonal units are degrees C squared and pH units squared. This is a proposed synthetic reference **scale**, not measurement-error covariance. |
| `family_weights` | Object of five nonnegative floats; dimensionless scoring weights | Sequence, structure, site, evolution and system each **1**. Equal influence is a proposed convention, not an empirically learned relationship. |

For the sequence normalization, the declared local scoring setup has nonpositive
gap penalties, positive self-substitution scores and
`s(x,y) <= (s(x,x)+s(y,y))/2`; each residue is used at most once. These conditions
justify the proposed [0,1] normalization. They are synthetic assumptions here,
not verified properties of an actual alignment tool invocation.

## Derived cells and exact population calculations

| Exact output cell | Deterministic calculation | Synthetic output; meaning |
|---|---|---|
| `assay.total_variance` | `sum(propagated_variance.values()) + covariance_cross_term_sum` | **0.11124225 min^-2**; total conditional effect variance. The six entries already contain their `J_i^2` propagation. |
| `assay.standard_uncertainty` | `sqrt(total_variance)` | **0.333529983660 min^-1**; standard uncertainty, not a confidence interval. |
| `assay.constrained_activity` | `max(0, corrected_activity)` | **0.68 min^-1**; best nonnegative activity under this model. Preserve the original signed measured contrast separately. |
| `source.profile_log_ratio` (`S`) | `constrained_activity^2/(2*total_variance)` | **2.078347030917 nats**; best normal fit with nonnegative activity versus zero. Requires the declared fixed-variance model and `V>0`. |
| `source.bounded_profile_contrast` (`B`) | `tanh(S/2)` | **0.777561486079**; normalized difference between the two best likelihood fits. |
| `correspondence.sequence` | `2*pair_raw_score/(source_self_raw_score+target_self_raw_score)` | **480/620 = 0.774193548387**; pair score relative to self scores. |
| `correspondence.structure` | `min(tm_source_normalized, tm_target_normalized)` | **0.85**; more demanding normalization direction. |
| `correspondence.site` | `exact_match_count/declared_count`, when all declared sites are observed | **8/10 = 0.8**; exact identity fraction, not equal biological importance of residues. |
| `correspondence.evolution` | `supporting_tree_replicates/eligible_tree_replicates` | **85/100 = 0.85**; stability of the declared placement, not functional probability. |
| `correspondence.system_distance_squared` | `delta^T * inverse(reference_scale_covariance) * delta` | **0.74**; dimensionless standardized squared descriptor distance. |
| `correspondence.system` | `exp(-system_distance_squared/2)` | **exp(-0.37) = 0.690734330637**; conventional condition similarity, not enzyme response. |
| `correspondence.available_mean` (`R`) | `sum_observed(w_j*r_j)/sum_observed(w_j)` | **0.792985575805**; here all five are present, so denominator **5**. |
| `correspondence.observed_weight_fraction` | `sum_observed(w_j)/sum_declared(w_j)` | **1**; completeness diagnostic, not another multiplier. |
| `target.conventional_signed_index` (`D`) | `R*B` | **0.616595042762**; explicitly conventional correspondence-adjusted index. It no longer has likelihood semantics. |
| `target.proposed_support_coordinate` (`c`) | `null if D is unknown, otherwise max(0,D)` | **0.616595042762**; proposed positive-support coordinate. The unprojected signed index remains retained. |

The propagated variance uses `J Sigma J^T + distinct_residual_variance` upstream;
this port adds its named components once. No second comparability, isolation,
calibration or reliability multiplier is applied after that correction. Source
assay condition calibration and the target/source descriptor comparison are
declared different inputs in this fixture; reusing one observation for both
would require removing the duplicated use.

## Uncertainty, missing cells and dependencies

The source calculation is conditional on a normal measurement model with the
six supplied variances treated as fixed synthetic operands. Their real finite
degrees of freedom and independent preparation count are **unknown**, not an
invented `n=1`, `n=3` or infinite degrees of freedom. This arithmetic does not
validate a normal model or justify treating estimated real variances as known.

The correspondence outputs retain their actual kinds: raw score normalizations,
site fraction, empirical tree-support fraction and proposed condition kernel.
No sampling error or probability interval for `R`, `D` or `c` is supplied.
The reference scale matrix is not an uncertainty estimate. A zero-width
missing-family identification bound when all families are observed does not
assert zero measurement uncertainty.

| Condition | Exact handling at this interface |
|---|---|
| Missing applicable source effect/variance/covariance term | Keep the missing cell null; full-model `V`, `S`, `B`, `D`, `c` are unknown. A separately labeled conditional calculation may retain only explicitly stated assumptions; it is not silently the full result. |
| Undefined denominator, incompatible units, conflicting representations or invalid variance | Preserve the inputs and specific reason; dependent output is null. Do not clamp an invalid raw input or substitute zero. |
| Some relevant correspondence families missing | Keep them null. Calculate the available-family point and observed-weight fraction. With declared total weight `W`, retain identification bounds `[sum_observed(w*r)/W, (sum_observed(w*r)+sum_missing(w))/W]`. These are not confidence limits or imputed measurements. |
| No measured relevant correspondence | `R`, `D`, `c` are null; source `S/B` can remain known. Missing target activity or absent endpoint calibration alone does not cause this state. |
| Partly observed functional-site set | Full-site fraction has bounds `[matches/declared, (matches+declared-observed)/declared]`. The exact full-site point is unknown. An observed-sites point has its own denominator/label and cannot silently replace it. |
| Known source zero with known positive variance | `S=B=0`, then `D=c=0` when R exists. This is no improved fit over zero under the presence model, not proof that every possible activity is absent. |
| Nondetection or a different endpoint/error model | Retain the censoring limit/observation form or actual endpoint. Use its defined likelihood path before this scoring handoff; do not fabricate a zero activity or apply the detected-normal formula. |

For signed `B` in the broader contribution contract, image any R bounds through
`D=R*B` using `min/max` to order endpoints, then apply `max(0,D)` to each bound.
Do not replace bounds by their midpoint. The complete example has
`R bounds=[0.792985575805,0.792985575805]` and
`c bounds=[0.616595042762,0.616595042762]`, solely as missing-family bounds.

Dependency group `source_assay_block` contains the upstream activity and its
six error terms: it is one summarized finding, not six experiments. Original
measurement identity establishes duplicate representations; equal numbers do
not. Group `target_correspondence` contains the five families; alignment,
structure, site conservation and tree placement may be correlated. The mean
makes no independence claim and supplies no `sqrt(5)` uncertainty reduction.
Repeated methods share a family's fixed total weight. The same assay cannot
be added again as separate activity, specificity and correspondence evidence.
This contract consumes one source result; the assigned multi-source worker owns
the additional combination convention.

## Supporting provenance and verification

`SYNTHETIC_RECORD_001.json` separates `input`, `declared_conventions`, `derived`,
and supporting `scope`, `uncertainty`, `dependencies` and `provenance` records.
Provenance records do not contribute scores. The mathematical definitions come
from the complete source-free contribution, correspondence and coordinate
proposals listed in `AUTHORITY_READ_001.md`. No primary paper or paper-specific
packet was read in this workload.

There is **no essential undefined arithmetic in this single-source chain**.
Election of the S/B scale, equal-family convention and explicit positive-support
projection remains a design decision. Real assay operands/models, empirical
validation, multi-source aggregation and W05's annotation-wide consumption are
separate work. The checked synthetic record does not finish A105 or change 0/10.
