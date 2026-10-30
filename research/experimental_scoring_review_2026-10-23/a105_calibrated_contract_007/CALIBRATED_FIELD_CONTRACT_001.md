# A105 calibrated multi-source sheet: exact population contract

2026-10-23. **Source-free, synthetic, unadopted research proposal.** Independent
arithmetic: **125 checks passed**. This defines numerical sheet cells and the
inputs that future targeted readers must supply. No reader, prompt, production
scorer, library publication, annotation-credit wiring or scientific run is
implemented. The goal remains all ten sheets, **0/10 complete, A105 first**.
The pending user aggregation question has not been answered by this calculation.

The three responsibilities remain separate: the investigation prompt guides
discovery from supplied sequence/file material/snippets; this sheet defines the
numbers; separately implemented readers or graders populate these exact cells.
The checker only verifies invented arithmetic. No actual target, paper result,
calibration experiment or biological interpretation is asserted here.

## Numerical meaning and boundary

After investigation establishes a comparison, this conditional route estimates
one target contrast, `theta_T = ln(a_A,T / a_B,T)`, at the declared reference
state. Each `a` is product amount per minute per amount of the intended molecule
(`min^-1`). The numerator is molecular reaction A; the denominator is molecular
reaction B. `theta_T > 0` means faster A than B, **not** activity versus inactivity
or physiological importance. `theta_T < 0` favors B over A. This needs neither
an initial candidate annotation nor a new target assay.

The fixture conditions are invented: reference 30 degrees C, pH 7, separate
A and B substrate assays at 1 mM, molecular state M0. G1/G2/G3 are separate
molecules/preparations, not mixed together. Other molecular contributors within
each preparation account for the difference between measured and attributable
rates. Source conditions are `(25,7)`, `(30,6.8)`, `(35,7.4)` in degrees C/pH.

The input boundary is **net-rate and calibration summaries**, after upstream
instrument/blank treatment. The record does not invent raw detector readings,
replicate counts or raw-scale covariance. Known covariance is declared directly
for the natural-log summaries. The native rate/control/fraction numbers are
consistent synthetic representations of those summaries, not a claim that their
full native-scale errors are Gaussian. A real reader must justify its transformed
error model or supply a suitable full likelihood.

## Exact cells and population responsibilities

Paths are in `SYNTHETIC_RECORD_001.json`. `o` below abbreviates
`input.observations[i]`; every other path is literal. Numeric inputs are finite;
ratios used in logs must be positive. Covariance entries use the product of the
row/column primitive units. Here every statistical primitive is dimensionless
on the natural-log-ratio scale; covariance has squared log-ratio units.

| Exact cell(s) | Type, unit, denominator and population responsibility | Calculation/use |
|---|---|---|
| `o.assay.net_rate_A`, `net_rate_B` | Positive numbers, `min^-1`, each per amount of assayed source molecule; a targeted assay/dataset reader supplies actual corrected measurements | Preserve the specified A numerator/B denominator and measurement identities |
| `o.assay.log_ratio_y`, `variance_y` | Number and nonnegative number; log ratio and squared log ratio | `y=ln(net_rate_A/net_rate_B)`; variance comes from the supported joint assay model, never paper count |
| `o.comparability.attributed_ratio_A_over_B_at_source_condition`, `attributed_ratio_A_over_B_at_reference_condition` | Positive dimensionless numbers; matched condition-control reader supplies A/B for **the intended source molecule** in both conditions | The A-versus-B comparison is retained; only other experimental conditions change |
| `o.comparability.log_condition_ratio_c`, `variance_c` | Number and nonnegative number on log/squared-log scales | `c=ln(control_A/B_at_source_condition / control_A/B_at_reference_condition)`; subtract to standardize condition differences |
| `o.isolation.fraction_A`, `fraction_B` | Numbers in `(0,1]`; independent attribution-control reader supplies intended-molecule contribution divided by each respective **net measured** rate | These fractions address which molecule produced the signal; comparability alone does not establish attribution |
| `o.isolation.negative_log_fraction_ratio_d`, `variance_d` | Number and nonnegative number on log/squared-log scales | `d=-ln(fraction_A/fraction_B)`; `y-d=ln(f_A rate_A / (f_B rate_B))` |
| `o.descriptor.source_value`, `target_value`, `target_minus_source_x`, `measurement_variance` | Dimensionless numbers; here exact toy molecular descriptor, separate from already corrected temperature/pH differences | `x=target_value-source_value`; fixed `X_i=[1,x_i]` only because descriptor uncertainty is exactly zero in this fixture |
| `input.response.prediction_design_X` | `n x p` numeric matrix; row order matches observations and coefficient order | Calibrated response design at the **same reference state and endpoint** |
| `input.response.coefficient_values_beta`, `coefficient_covariance` | `p` vector and symmetric PSD `p x p` matrix; coefficient units are stated separately | A separate calibration analysis supplies estimates/covariance, fit identity, domain and data-reuse relationships; no fitting data are supplied here |
| `input.response.calibration_training_design` and its `_status` | Actual calibration design or null with status | Null here: coefficients are synthetic supplied fit summaries; no real fit is claimed |
| `input.residuals.source`, `.target`, `.family` | Each has explicit owners, zero means, loadings and covariance | Calibration supplies centered residual distributions. Ownership determines reuse; names or clade membership never determine a variance |
| `input.primitive.order`, `.values`, `.units`, `.covariance_matrix`, `.jacobian_J` | Complete ordered vector, units, `m x m` covariance, `n x m` Jacobian | Joint input assembly retains **all** reused-data cross-covariances; no default-zero missing entries |
| `input.uncertainty.model`, `.covariance_status`, `.degrees_of_freedom`, `.degrees_of_freedom_reason` | Declared model/status and nullable df | Here known fixed Gaussian log-summary covariance; null df means this is not an estimated-variance fixture, not infinite empirical df |
| `o.observation_id`, `.source_molecule_id`, `.preparation_id`; `scope`; control/fit/residual IDs | Provenance and declared endpoint/state identities, not scores | Readers reconcile representations and bind compatible endpoints before numerical pooling; these identities earn no extra contribution |

The identified population responsibilities above are **unimplemented**. Literature
extraction and dataset analysis must populate the same meanings. Neither a free
prose confidence grade nor a generic reader result substitutes for these inputs.

## Fully populated asymmetric example

`net_rate_B=1 min^-1` in every row. `f_B=(.8,.9,.75)` and
`f_A=f_B exp(-d)`. The JSON contains their full numerical values. Condition
control numerator is `exp(c)` and its reference denominator is 1, independent
of the main assay denominator. These are three different denominators.

| Source | A rate (`min^-1`) | y | c | d | x | `y-c-d` | `X beta` | z |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | 2.459603111 | .90 | .10 | .10 | -1 | .70 | .10 | .80 |
| G2 | 1.822118800 | .60 | .05 | .10 | 0 | .45 | .15 | .60 |
| G3 | 2.585709659 | .95 | .20 | .05 | 1 | .70 | .20 | .90 |

Comparability and isolation remain distinct additive corrections:

```
z = y - c - d + X beta
X = [[1,-1],[1,0],[1,1]]
beta = [.15,.05]
Cov(beta) = [[.020,.005],[.005,.020]]
Var(y) = [.04,.09,.16]
Var(c) = [.01,.01,.04]
Var(d) = [.01,.04,.01]
```

For this supplied external fit, `x=2-[3,2,1]`, with synthetic domain `[-1,1]`.
No sequence identity, biological feature-response law, empirical sample size or
training design is inferred from that toy definition. The nonzero coefficient
covariance is preserved. No additional correspondence multiplier `R` appears:
the calibrated map already expresses correspondence and its uncertainty.
The separate 005 sheet's activity-versus-zero comparison and conventional `R*B`
route have different meanings; its positive clamp is not imported here.

The **stated** independence assumptions are: all source assay errors independent;
all condition-control summaries independent; all attribution-control summaries
independent; these three blocks independent of one another; the external fit
reuses none of those measurements; residual blocks independent of measurement
and coefficient errors. The coefficients are correlated. Source residuals are
independent **conditional on** the shared target and family effects. These are
invented model assumptions, not deductions from distinct preparation/paper IDs.

Residual ownership is explicit:

| Term | Numerical covariance and ownership | Repeated measurements |
|---|---|---|
| Source mapping residual | `.04 I_3`, one realization for each G molecule | A new preparation of the **same molecule** shares its mapping residual |
| Target mapping residual | `.06`, loading `[1,1,1]^T` | Every mapping to this target shares it; more source assays cannot remove it |
| Family mapping residual | `Omega_F=.04 I_2`, `L_F=[[1,0],[1,0],[0,1]]` | G1/G2 share F12; G3 has F3; variance is supplied, not inferred from a family label |

All six residual means are zero. A centered supported residual distribution is
essential: an unbounded fixed unknown common target bias identifies only
`theta_T+bias`; no finite target uncertainty follows without more information.

The 17 primitive entries are `(y[3],c[3],d[3],beta[2],u_source[3],u_target,
u_family[2])`; `Sigma` is their full block-diagonal matrix in the fixture.
`J=[I,-I,-I,X,I,1,L_F]`. The record has every one of 289 covariance entries and
51 Jacobian entries. Residuals are already in `Sigma` and are added **once**:

```
C = J Sigma J^T
  = diag(Var(y)+Var(c)+Var(d)) + X Cov(beta) X^T
    + .04 I + .06 11^T + L_F (.04 I_2) L_F^T
  = [[.230,.115,.060], [.115,.300,.085], [.060,.085,.400]]
```

For real reused measurements, the full joint covariance replaces block
independence. For uncertain predictors or nonlinear maps, expand the primitive
vector/Jacobian with justified propagation, or use the appropriate full model.
Do not tack on another reliability penalty for a weakness already corrected
and included in this uncertainty model.

## Exact derived sheet outputs

| Exact `derived` cell | Deterministic calculation | Result and evaluation |
|---|---|---|
| `source_corrected_contrast` | `y-c-d` | `[.70,.45,.70]`, source attributable contrast at reference conditions |
| `response_mean` | `X beta` | `[.10,.15,.20]`, calibrated target-minus-source correction |
| `mapped_target_contrast_z` | Sum of preceding two vectors | `[.80,.60,.90]`, estimates of the same target contrast |
| `covariance_components`, `target_covariance_C` | Named component propagation and `J Sigma J^T` | Numerical error contributions and their joint covariance; not independent evidence credits |
| `pool.precision_P`, `.weights` | `P=1^T C^-1 1`; `w=C^-1 1/P` | `6.431627794853`; `[.477136431784,.261244377811,.261619190405]` |
| `pool.theta_hat`, `.variance_V`, `.standard_uncertainty` | `w^T z`, `1/P`, `sqrt(V)` | `.773913043478`, `.155481634183`, `.394311595294`; contrast, squared contrast, standard uncertainty |
| `pool.Q`, `.Q_df_conditional_on_known_C` | `(z-theta_hat 1)^T C^-1(z-theta_hat 1)`; `n-1` | `.217391304348`, `2`; disagreement diagnostic, never an extra score multiplier |
| `pool.theta_plus`, `.theta_minus` | `max(0,theta_hat)`, `min(0,theta_hat)` | `.773913043478`, `0`; common-effect directional constrained fits |
| `pool.Q_plus`, `.Q_minus` | Evaluate the same quadratic at each constrained fit | `.217391304348`, `4.069559452781` |
| `pool.S_nats` | `max_(theta>=0) ell(theta)-max_(theta<=0) ell(theta) = (Q_minus-Q_plus)/2 = theta_hat*abs(theta_hat)/(2V)` | **`1.926084074217`**, signed directional profile separation |
| `pool.B` | `tanh(S/2)` | **`.745630704507`**, proposed bounded index in `[-1,1]`, **not a probability** |
| `annotation_support_coordinate`, `annotation_support_status` | Null; `unresolved_W05_signed_to_annotation_interface` | No approved projection or annotation-wide aggregation is supplied |

`ell(theta)=-.5(z-theta 1)^T C^-1(z-theta 1)+constant` uses **one** shared target
effect. The two directional hypotheses both include equality. Reversing A/B
reverses S/B. S/B do not distinguish two inactive molecules from equal positive
rates; the declared positive-rate input model is essential. Neither adding
separately optimized S values nor adding B values reproduces this joint fit.
Under correlation, use the joint likelihood, not a product of marginals.

For example, with independent variance .25 per observation, `.8,.1` gives
`theta=.45`, `V=.125`, `S=.81`, below `.8` alone's `S=1.28`. The positive but
smaller observation changes the common-effect estimate. `.8,-.8` gives `S=B=0`
but `Q=5.12`; conflict has not disappeared. Q remains a diagnostic, with no
automatic inflation, acceptance threshold or stopping rule.

## Dependence, missingness and estimation limits

| Case | Exact treatment in this proposed interface |
|---|---|
| Reused calibration/denominator | Preserve cross-covariance. Example `(source, target-minus-same-source)` covariance `[[.04,-.04],[-.04,.13]]` gives variance of their sum `.09`, not `.17`. This calibration difference is **not** isolation d. |
| Exact re-representation | Reconcile original observation/control/fit identities, retain aliases, and count the canonical observation once. Repeating `.8` with variance `.25` leaves `V=.25`. |
| Distinct equal numeric observations | Keep both identities; values alone establish neither duplication nor independence. With separately justified independent `.25` variances, two `.8` values give `V=.125`. |
| New preparation, same source | Retain shared source mapping uncertainty. The separate balanced example with independent `.06` plus shared `.19` yields two-preparation `V=.22`, not `.125`. |
| Missing positive rate, c, d, h, covariance entry, required calibration term or applicable uncertainty | Keep null and a specific reason; affected corrected/pooled outputs remain null. Preserve unaffected source cells. Missing covariance is not zero. A separately labeled sensitivity set is not an imputed point. |
| Estimated covariance | Retain estimation method, sample/preparation structure, df where defined, and variance-component/coefficient estimation uncertainty. The fixed-C result is only conditional arithmetic; calibrated uncertainty needs the supported joint/profile/bootstrap model. That model is not supplied here. |
| Singular total C, all-zero C, deterministic unknown constraints | General treatment remains **unresolved**. Canonicalize proven duplicates; otherwise require a separately specified identifiable degenerate model. No diagonal jitter, invented error bars, generic pseudo-inverse or infinite-score fallback. |
| Invalid covariance, undefined denominator, incompatible unit/endpoint or conflicting representation | Preserve inputs and explicit reason; dependent score null. Do not clamp inputs or combine inconsistent copies as new data. |
| Nondetection/censored observation | Retain detection limit, direction and observation model. Use a censored likelihood/mapping if supplied; no zero substitution, pseudocount or ordinary detected-log GLS. |
| Different endpoint/state | Pool only through an explicitly supported common target estimand. Binding, transport, rate, occupancy and growth are not interchangeable repeated measures. Complementary assays can repair a named weakness without becoming independent repeats. |

A future population result with unavailable required inputs must add
`unresolved_cells: [{path, reason_code, supporting_reference}]`, and set affected
`derived` fields to null. Proposed reason codes are `missing_measurement`,
`missing_covariance`, `missing_mapping`, `estimated_covariance_model_needed`,
`singular_model_needed`, `invalid_operand`, `conflicting_representation`,
`incompatible_endpoint`, and `censored_likelihood_needed`. The synthetic main
fixture has no unavailable arithmetic operand; its null training design,
replicate counts and annotation coordinate retain their explicit statuses.
This field contract does not implement an extractor or runtime gate.

## Sensitivity sets retain established covariance

The record's **separate** ten-equal-observation sensitivity example is not a
replacement for the fully fixed three-source C. It assumes `z_i=.8`,
`C=.10 I+R`, `diag(R)=.15`, and `R PSD`. Known `.10 I` stays fixed:

```
V in [.010,.160]; S in [2,32]; B in [.761594155956,.999999999999975]
```

The lower variance follows `C >= .10 I`; the upper follows the equal-weight
variance bound `.10/10+.15` and GLS minimum variance. Both are attainable:
`R=.15 J` gives `.16`; `R=.15 I` gives `.025`; and
`R=.15((10/9)I-(1/9)J)` gives `.01`. The last residual R is singular but total
C is positive definite, so no degenerate-total-C workaround is involved.
With the **additional** assumption of nonnegative exchangeable residual
correlation, `V=.025+.135 kappa`, `kappa in [0,1]`, hence `S in [2,12.8]`.

Known independent `.10` and remaining diagonal `.15` cap total positive pair
correlation at `.6`. Allowing `.8` would discard established information.
Any other known shared terms must likewise remain in the allowed set; no broad
bound, midpoint or most favorable score replaces the actual known model. Unequal
effects require optimizing both their fitted mean and variance over the actual
allowed covariance set; these equal-effect endpoints are not universal.

## Inputs still needing actual calibration or user resolution

| Exact field(s) | Still needed for an actual target calculation |
|---|---|
| `scope` and all assay/condition/isolation cells above | Actual supplied target material, emerged A/B endpoint, source molecular identities, states, positive net measurements, independently supported condition response and attribution fractions; covariance of all reused readings |
| `input.response.prediction_design_X`, `coefficient_values_beta`, `coefficient_covariance`, `calibration_training_design`, domain/data-reuse fields | Supported descriptor definitions, measured predictors/uncertainty, reference-state response mapping, original training/calibration data and fit audit, validated domain and coefficient covariance |
| `input.residuals.source`, `.target`, `.family` | Supported residual centering, ownership/loadings, scales and cross-covariances; evidence separating within-preparation, source, family and target variation; no conversion from group labels alone |
| `input.primitive.covariance_matrix`, `input.uncertainty` | Joint measurement/calibration covariance including overlap, plus an estimation-uncertainty model if covariance is estimated; known components retained in any sensitivity set |
| Selection and censored/alternative endpoint model | Actual tested panel/selection scope; supported likelihood when log-normal-summary assumptions do not apply; no current computation supplies it |
| `derived.annotation_support_coordinate` | User feedback on proposed signed scale, still-pending aggregation convention, and separate W05 signed-to-annotation interface. This common-effect fit does not answer those decisions. |

The actual scientific and empirical inputs in this table remain absent. All
conditional fixture arithmetic is specified; this does not complete A105,
contrasting published-case examples, either reader path, or any other axis.

## Provenance and executed verification

| Inspected record | Use here |
|---|---|
| `../a105_correlated_bridge_006/CORRELATED_RESPONSE_PROPOSAL_001.md` (complete) | Signed A/B common-target model, asymmetric operands, covariance ownership, duplicate/reuse/contradiction limits |
| `../a105_correlated_bridge_006/SENSITIVITY_CONSTRAINT_ADDENDUM_001.md` (complete) | Bounds that preserve known independent covariance |
| `../a105_correlated_bridge_006/check_correlated_bridge_001.py` (complete) and `arithmetic_001.json` (selected records) | Independently compared asymmetric outputs; no import/execution or rewrite of those files |
| `../a105_sheet_cells_005/SHEET_CELL_CONTRACT_001.md` (complete) | Exact field/reader separation; retained distinct endpoint and uncalibrated correspondence convention |

`check_calibrated_contract_001.py` ran under Python standard-library exact
`Fraction` matrix algebra; logarithm/square-root/tanh comparisons use floating
point. `ARITHMETIC_RESULTS_001.json` records **125 passed checks**, rational
outputs, synthetic edge cases and unchanged hashes of all five supplied prior
artifacts. It verifies the declared mathematics, not empirical adequacy.
`AUTHORITY_READ_001.md` records full instruction reads. No paper, paper-specific
evidence packet, web source or biological service was opened.
