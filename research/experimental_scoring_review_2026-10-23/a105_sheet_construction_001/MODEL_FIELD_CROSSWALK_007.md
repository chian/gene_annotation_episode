# A105 equation-to-cell crosswalk

Additive research contract, 2026-10-23. This fills the finite field-mapping gap
identified in `a105_completion_criteria_007/COMPLETION_CRITERIA_REVIEW_001.md`.
It defines inputs to the numerical sheet, not implemented readers, production
model selection, a new annotation formula or a runtime approval stage.

Investigation TASK text remains separate. A targeted literature reader or
dataset-analysis function populates the same numerical cells; a deterministic
calculation consumes them. Source identity, conditions, units, original data
and actual measurement dependencies accompany the cells without becoming scores.
The assay design and scientific statement determine the applicable equation;
one must not select a statistical model merely because it gives a larger score.

## Scope and common outputs

Each record concerns one declared molecular statement, one supplied-target
material scope and stated molecular conditions. The statement can emerge during
investigation. No initial candidate annotation or public identifier is required.

The numerical outputs are `effect`, `effect_uncertainty`, `native_ratio`,
`profile_log_ratio`, `bounded_signed_index`, and, where explicitly elected,
`target_contribution` and `positive_support_coordinate`. Their meanings remain
separate. Known values can survive when later dependent outputs are unknown.
`calculation_status` distinguishes `calculated`, `conditional`, `bounds_only`
and `unknown`; a zero value is a number, not the status for missing information.

Every route retains the actual observation scope and model assumptions. Bounds
retain their kind: detection/quantification limit, sampling interval or allowed-
input sensitivity interval. These are not interchangeable error bars.

## Measurement equation inputs

| Numerical route | Exact populated cells and units | Deterministic effect calculation | Missing/qualification behavior |
|---|---|---|---|
| Corrected activity | `sample_rate`, `blank_rate`, `contaminant_rate` in one rate unit; `recovery` dimensionless; `protein_amount` in the declared concentration/amount unit; `condition_response` a same-endpoint measured ratio; full ordered `input_covariance`; `distinct_residual_variance` | `(sample_rate-blank_rate-contaminant_rate)/(recovery*protein_amount*condition_response)`; propagate through the same equation with `J Sigma J'`, adding only separately defined residuals | Missing applicable corrections leave the corrected result unknown; retain a clearly labeled preparation-level result if supported. Unknown covariance is not zero. |
| Signed rate difference | `rate_A`, `rate_B`, their common units and 2-by-2 covariance; `difference_boundary` in those units | `rate_A-rate_B-difference_boundary`; variance `var_A+var_B-2*cov_AB` | A missing boundary is not silently replaced by a biologically consequential threshold. Equality comparisons can explicitly use zero. |
| Log rate preference | Positive `rate_A`, `rate_B`; joint covariance; positive `required_ratio` | `log(rate_A/rate_B)-log(required_ratio)`; derivative vector `[1/rate_A,-1/rate_B]` | Nondetections and nonpositive noisy readings do not receive pseudocounts or ordinary logs. |
| Log affinity preference | Positive `Kd_A`, `Kd_B` in the same concentration unit; joint fit covariance; positive `required_affinity_ratio` | `log(Kd_B/Kd_A)-log(required_affinity_ratio)`; smaller Kd for A yields a positive preference | An IC50 stays an IC50; it cannot fill Kd cells without a justified quantitative binding model. |
| One-site occupancy comparison | `free_ligand_A`, `free_ligand_B`, `Kd_A`, `Kd_B`, complete joint covariance; `occupancy_difference_boundary` | `free_ligand_A/(Kd_A+free_ligand_A) - free_ligand_B/(Kd_B+free_ligand_B) - boundary` | Conditional on the declared equilibrium one-site model and free concentrations. Total ligand is not automatically free ligand. |
| Michaelis-Menten condition response | Positive `substrate_source`, `substrate_reference`, `Km` in one concentration unit; joint parameter covariance; same applicable source molecule/preparation/model | `[substrate_source/(Km+substrate_source)] / [substrate_reference/(Km+substrate_reference)]` | This computes a condition response, not a reliability score. A shared Km is propagated once; transferring the curve to another preparation requires its own relationship. |

Nonlinear propagation is a local approximation unless the stated transformation
is linear. Where that approximation is unsuitable, retain the actual joint fit
or measurement distribution. No unspecified universal error model is implied.
Comparability corrects other experimental conditions; isolation corrects which
molecule produced the measured signal. The variable intentionally compared is
not itself an experimental mismatch penalty.

## Statistical equation inputs

Each row below defines a particular calculation rather than a generic
`measurement_model_inputs` placeholder. Numerical unknowns remain nullable.

| Equation name | Exact required numerical cells | Calculation and output |
|---|---|---|
| `known_normal_signed_contrast` | `contrast_estimate`, positive `known_variance`; real contrast parameter; explicit zero boundary after any stated boundary subtraction | `S=contrast_estimate*abs(contrast_estimate)/(2*known_variance)`; `B=tanh(S/2)` |
| `known_normal_nonnegative_presence` | `observed_corrected_activity`, positive `known_variance`; physical activity constrained nonnegative; alternative zero | `S=max(0,observed_corrected_activity)^2/(2*known_variance)`; negative measured activity is retained but does not become positive evidence by squaring |
| `paired_normal_unknown_variance` | `independent_pair_count=n>1`, `mean_paired_difference`, positive `sample_sd_paired_difference`, actual pairing/independent-unit identities | `t=mean/(sd/sqrt(n))`; `S=sign(mean)*(n/2)*log1p(t^2/(n-1))`; B as above. For the explicitly nonnegative presence variant, a negative mean has S=0. |
| `known_normal_common_effect` | Vector `contrast_estimates`, full known positive-definite `contrast_covariance`, one common target/source contrast | `P=1' C^-1 1`; mean `(1' C^-1 z)/P`; variance `1/P`; signed-normal formula on that fitted mean/variance. Preserve `Q=(z-mean)' C^-1(z-mean)` separately. |
| `known_normal_detected_and_censored` | For each detected independent observation: `observed_value`, positive `known_variance`; for each independently justified censored observation: numeric `lower_limit`, `upper_limit`, positive `known_sd`; shared physical parameter and its allowed range | Add detected normal log densities and `log[Phi((upper-a)/sd)-Phi((lower-a)/sd)]`; one-sided endpoints may be explicitly infinite. Maximize the joint function in the two declared parameter regions, then subtract best fits. |
| `defined_compound_normal_statement` | Vector `contrast_estimates`, full known covariance; explicit joint inequalities defining the statement and its complement | Compare the constrained quadratic minima for those two regions. Do not add the separately optimized single-contrast S values. Missing required endpoints leave the compound result unknown while retaining individual measured rows. |

The censor route requires its actual factorization: independence cannot be
deduced from separate source records. Correlated censoring needs its declared
joint censored distribution instead. A missing detection limit or noise model
does not produce a numerical likelihood. Unknown-variance, bootstrap, clustered
or nonlinear estimates are not silently passed to the known-variance equations.
The paired formula is not a conversion of an arbitrary t statistic, Welch test,
p-value or unspecified +/- error bar. A zero sample SD, singular covariance or
unidentified parameter model remains a specific unresolved calculation for that
case, without invented noise or an infinite-score fallback.

Native endpoints with only reported means, limits or unresolved uncertainty can
still fill the measurement cells. Those inputs do not manufacture a source S.

## Source-to-target and combination fields

| Route | Concrete cells and receiving operation |
|---|---|
| Native correspondence convention | The existing single-source contract binds `source_profile_log_ratio`, native pair/self alignment scores, structure scores, declared/observed/matched site counts, placement counts, condition differences/scales and explicit family weights. Its defined outputs are R, B and D=R*B, with conditional and full-family bounds distinguished. No correspondence family is required solely to fill a fixed number of columns. |
| Calibrated common-target mapping | `a105_calibrated_contract_007/CALIBRATED_FIELD_CONTRACT_001.md` supplies exact JSON paths for y, separate c and d, X, beta, their joint covariance and owned residual terms. The fully populated synthetic record supplies every numerical operand. Use the mapped z and its full C in `known_normal_common_effect`; do not apply R again. |
| Several uncalibrated sources | Each source supplies finite S and its numerical correspondence calculation, plus original observation identity. The explicitly proposed combination requires its own declared allocation operands; labels of common study or family alone do not supply a correlation coefficient. The separate 007 combination handoff owns that calculation; no average/cumulative choice is silently installed by this crosswalk. |
| Proposed nonnegative support output | Once compatible evidence for the statement is combined, `max(0,signed_target_index)` is the proposed support-only projection. Signed results remain in the sheet. Unknown input remains unknown, and opposition is not clipped before combining. This remains a proposal for judgment. |

The scoped row is not a complete scalar reducer over arbitrary molecular claims
in an annotation. If one whole-annotation A105 coordinate is promised, that
claim/endpoint combination is still an essential numerical design task. Calling
it reader implementation or wiring would not define it.

## Concrete populated crosswalk checks

All values in this table are **synthetic**, already fully specified in the
retained arithmetic proposals; they are not new observations.

| Input cells | Equation | Checked numerical outputs |
|---|---|---|
| activity=0.68/min; variance=0.11124225/min^2 | Nonnegative presence | S=2.078347030917; B=0.777561486079 |
| n=3; paired mean=1.5 micromolar/min; paired sample SD=0.1 micromolar/min | Paired normal, unknown variance | S=8.736786139; B=0.999678913 |
| detected 0.68, variance 0.11124225; separate independent censored value below 0.10, known SD=0.20; a>=0 | Detected plus censored joint likelihood | fitted a=0.147958504; S=0.271726302; B=0.135033321 |
| z=[0.8,0.6,0.9] and fully specified 3-by-3 C in the calibrated contract | Known-normal common target contrast | effect=0.773913043478; variance=0.155481634183; S=1.926084074217; B=0.745630704507 |
| Contrasts [2,3]; identity covariance; both directions required positive | Compound normal conjunction | S=2; B=0.761594155956; this differs from summing the two individual S values |

The source examples retain their measured rates, Km, apparent Kd, IC50 or limits
under their actual names. Table 1 errors with unspecified meaning remain
unspecified. Literature extraction and dataset analysis populate the same cells;
the source label does not alter the deterministic equation. The earlier source
conversions and their inspection limits remain the provenance for those values.

This crosswalk defines numerical operands and result meanings. It does not
complete production readers, empirically calibrate the models, answer pending
scoring choices or mark A105 complete.

## Additional exact route: two independent normal groups with unknown variances

This additive entry supplies the non-paired two-group profile model used in the
retained reaction example. It is not a Welch-statistic conversion. Required
cells are `group_A.count`, `.mean`, `.sample_sd` and the corresponding group B
cells, with the same endpoint units, actual independent-unit definitions and an
explicitly justified independent normal-groups model. Both n values exceed one
and both sample SD values are positive. Each group's variance is estimated
separately; neither is known or assumed equal to the other.

Let `v_g=(n_g-1)*sample_sd_g^2/n_g`. Apart from constants shared between fits:

`ell_free = -0.5*sum_g[n_g*log(v_g)]`

`ell_equal(mu) = -0.5*sum_g[n_g*log(v_g+(mean_g-mu)^2)]`

`S = sign(mean_A-mean_B) * (ell_free-max_mu ell_equal(mu))`

The maximizing common mean is sought globally in the interval between the two
observed means. Evaluate all real stationary roots in that interval and its
endpoints. The stationary polynomial is

`n_A*(mu-mean_A)*(v_B+(mu-mean_B)^2)`
`+ n_B*(mu-mean_B)*(v_A+(mu-mean_A)^2) = 0`.

A single local optimization or the average of the two means is not generally
the required optimum. For the **synthetic** groups `(n,mean,SD)=(3,3,1)` and
`(3,1,1)`, the stationary means are about 1.422649731, 2 and 2.577350269.
The first and third maximize the constrained likelihood, giving
`S=2.687639203842` and `B=0.872586619007`. Using the midpoint would instead give
S=2.748872195622 and is incorrect for this model. The parent checked the cubic
roots and evaluated the common and separate fit expressions numerically.

If reported +/- is not identified as sample SD, these SD cells remain unknown.
This route does not infer independence from n, a paper count or distinct group
labels. Unknown dependence, zero sample spread or incompatible endpoint scope
preserves the native quantities and leaves this profile result unresolved.
