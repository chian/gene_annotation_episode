# A105 original reported-curve grid: read-only implementation plan228

Status: proposal for root coordination. No production or test file is edited. This is a numerical section within the existing A105 assay workflow, populated by pure reader/calculator functions. It introduces no episode, software suite, overall evidence grade, annotation-credit formula, target-transfer calculation or goal amendment.

## Scientific conversion after this agent's own complete reset

The selected source is the WT BbPK/DHA panel in Yang2023's original S1Data.xlsx. Sheet1 Q193:Q205 contains13 concentrations and R193:T205 contains39 reported rate entries. A189/B190/Q191/R192/S192/T192 provide the panel, endpoint/unit, subject and three reporting-column labels. The existing175line v1 observation reader requires labelled observations down rows under group headers, with values in one subject column. This source has concentration rows and report columns. It requires its own explicit version and layout contract; it cannot be silently reinterpreted as v1.

These measurements populate precision and signal/model descriptors, not molecular attribution. Full point means, variances, SD and CV describe the selected reported entries. Each reporting column can be fitted descriptively as a reported curve. The mean of fitted parameter vectors and a fit to point means are different estimators and need different covariance calculations. The source does not establish that its columns identify independent physical preparations or exchangeable curve vectors. A conditional statistical scenario must remain conditional, with its actual assumption and provenance. A reporting count is not a biological n.

The native endpoint conflict remains: workbook NADH consumption versus Methods NADPH production. Native rate arithmetic can be retained without deciding reporter species or product yield. The helper enzymes coexist with BbPK; the grid lacks a quantitatively matched blank/recovery and a resolved protocol mapping. No active molecular amount binds these rates to kcat. This work supplies no product-specific activity, Vmax-to-kcat conversion or physical preparation covariance. GCMS/HPLC readouts in the packet complement endpoint identification but are not extra replicates of these39 measurements.

Examples already grounded in the frozen research calculation: at10mM mean0.00080543umol/min, SD0.0000280972583 and CV0.0348847924; at100mM CV0.189610657. Conditional first-order log(Vmax/Km) variance is approximately0.00390297409 for the mean of the three fitted parameter vectors and0.003392732339 for fitting the13 point means. The former divides the covariance of fitted vectors by3; the latter propagates the full cross-concentration curve covariance through the fitted estimator's sensitivity. Neither describes the covariance of the paper's published parameters.

## Exclusive files and compatibility

After explicit root release, only append versioned additions to:

- gene_annotation_episode/literature_rate_observation_inputs.py
- gene_annotation_episode/literature_rate_observation_calculations.py
- new tests/test_literature_reported_curve_precision_228.py
- this228 verification directory

Preserve each current file's complete byte prefix, public VERSION, v1 schema/function behavior, imports used by v1, and legacy callers. Add separately named GRID_* constants/functions; do not redefine existing globals. New imports live in the appended section or function scope. Existing storage314lines and prompt70lines are read for compatibility but not owned. Compiled common221 input/calculation sections were read completely and remain frozen.223 confirms its immutable2023file pin003 isolates its final tests; root owns release of this work. The live transitive fingerprint will change after production additions and must be recorded separately from223's frozen evidence.

## Proposed closed reader interface

Add GRID_INPUT_VERSION='a105_reported_rate_grid_v1', reported_rate_grid_population_schema(), read_reported_rate_grid(content, arguments, *, artifact_ref, context_documents=()), and reported_rate_grid_extraction_schema(). No IO/network/model calls. Original content bytes are supplied by the existing authenticated source adapter in future integration.

All listed object fields are required, additionalProperties=false. Nullable fields are explicit. Arguments contain only locations, expected labels and selected scientific meanings, never caller-supplied measured numeric values:

- version: literal GRID_INPUT_VERSION.
- source_ref: existing reference; source_kind: primary_source|retained_extraction|synthetic_fixture; worksheet: nonempty text.
- panel, subject, native_rate_label: existing closed {cell,expected_text} label selectors.
- curves: nonempty array of {header:{cell,expected_text}}.
- points: nonempty array of {concentration_cell:cell, rate_cells:[cell,...]}; rate_cells order corresponds exactly to curves.
- rate_unit: {code, witness}; code enum umol/min|nmol/min|mmol/min; witness is a selected label or exact context span as defined below.
- concentration_unit: {code,witness}; code enum M|mM|uM|nM|unknown; witness nullable only for unknown.
- endpoint_relationship: {status,witnesses}; status reported_convention_only|supported|unknown|conflicting. This does not infer reporter-to-product stoichiometry.
- curve_sampling: {status,witnesses}; status supported|stipulated_sensitivity|unknown|conflicting. This is the aspect-specific judgment whether the reporting columns can be treated as IID exchangeable complete curve vectors. Unknown/conflicting cannot authorize conditional estimator covariance.

Witness union: {kind:'xlsx_label',cell,expected_text}, or {kind:'context_span',source_ref,artifact_ref,start,end,quote}. context_documents is a host-only array of closed {source_ref,artifact_ref,content:bytes} records; the reader authenticates artifact SHA and exact UTF8 source span before accepting a context witness. It performs no source acquisition and no numeric extraction from context prose. This small explicit context path is needed because the selected concentration column has no native unit header, and the source conflict/sampling interpretations have Methods/caption witnesses outside the workbook. Root may instead bind this context through an existing authenticated helper during integration; the grid result must retain equivalent authenticated custody. No unsupported/supplied interpretation becomes an actual source sampling claim merely because its quote exists.

For a supported curve_sampling status, at least one authenticated witness is required; stipulated_sensitivity also retains a witness explaining the provenance of the selected assumption. Neither status creates physical sampling-unit IDs. For225 it must be stipulated_sensitivity, with the triplicate caption retained as insufficient evidence for a physical IID interpretation. Unknown is the default if no model is selected; the literal descriptive output can be computed in every case.

Validate exact curve/point dimensionality, column-header/value-column agreement, same-row concentration/rate cells, common concentration column, header precedence, unique concentration row addresses and distinct report columns. The selected roster may omit unrelated source rows deliberately; it need not be a whole sheet. Every selected row remains in that roster, including nonnumeric cells. Duplicate selections of exactly the same coordinates are aliases, not independent reports. Canonicalize aliases while retaining representation count and original selections. A reused value cell with incompatible point/curve meanings is a structured layout association error. Different source cells with equal numbers remain distinct. Headers with identical text at distinct cells remain distinct reporting columns; text does not invent preparation identities.

Reader extraction fields: version, original_arguments, source_kind, custody, meanings, context_witnesses, curves, points, entries, aliases, qualifications. Each custody/witness retains source_ref, artifact_ref, workbook_sha256, worksheet, member, member_sha256, cell, cell_type, decoded value, raw lexeme, formula object, value_is_formula_cache, style_index and error. Reuse Workbook.layout/open/index_strings/cell and _tag, read completely in this reset. Preserve workbook/package relationship custody for selected members. No reparsing or formula evaluation by a new spreadsheet engine.

Each numeric entry includes measurement_key=identity over original artifact+member+cell, representation_key over source_ref+selection, point_key over artifact+concentration_cell, reporting_curve_key over artifact+header_cell, exact_value as canonical fraction or null, status observed|missing|not_detected|censored|unsupported_cell, bound with comparator and exact limit when available, origin reported|synthetic, source/implementation reasons and witnesses. Formula caches are unsupported measured points; exact limits remain bounds. Cells typed as source errors remain errors even when their text resembles a number. Physical preparation ID, biological n and published-estimator identity remain null.

## Proposed pure calculator and selectors

Add GRID_SHEET_VERSION='a105_reported_curve_precision_v1', reported_curve_precision_request_schema(), populate_reported_curve_precision(extraction, request), reported_curve_precision_sheet_schema(), reported_curve_precision_selector_schema(). The calculator accepts only validated extraction plus a closed request; no callbacks/IO/model use.

Request fields: version literal 'a105_reported_curve_precision_request_v1'; fit_model enum none|unweighted_positive_km_mm; requested_components unique selector array. IID propagation is authorized solely by the retained curve_sampling meaning. Selecting fit_model permits descriptive fitting; it does not authorize a sampling inference.

Selector union, closed objects; all addresses must exist in the canonical selected roster:

1. {scope:'point', concentration_cell, component:mean|sample_variance|sample_sd|cv|available_point_mean|available_point_variance|available_point_sd|available_point_cv|selected_entry_count|available_point_count}.
2. {scope:'curve', curve_header_cell, component:Vmax|Km|SSE|stationarity_error|selected_point_count|available_point_count}.
3. {scope:'estimator', estimator:mean_of_reported_curve_fits|fit_of_point_means, component:Vmax|Km|native_efficiency|SSE|log_efficiency_variance|log_efficiency_standard_uncertainty|diagonal_only_log_efficiency_variance}.
4. {scope:'reported_curve_covariance', left_concentration_cell, right_concentration_cell, component:sample_covariance|conditional_mean_curve_covariance}.
5. {scope:'parameter_covariance', estimator:reported_curve_fit_distribution|mean_of_reported_curve_fits|fit_of_point_means, left_parameter:Vmax|Km, right_parameter:Vmax|Km, component:covariance|correlation}.
6. {scope:'sensitivity', estimator:'fit_of_point_means', parameter:Vmax|Km, concentration_cell, component:'d_parameter_d_point_mean'}.
7. {scope:'variance_term', estimator:mean_of_reported_curve_fits|fit_of_point_means, left_parameter:Vmax|Km, right_parameter:Vmax|Km, component:'signed_log_efficiency_variance_term'}.
8. {scope:'grid', component:all_reported_residual_SS|within_concentration_reported_entry_SS|mean_curve_fit_residual_SS_times_curve_count|reported_curve_count|complete_curve_count}.

SSE for mean_of_reported_curve_fits is not defined as the average of column SSE: return a specific not_applicable_to_estimator reason. The curve count is a reporting count only. Available-point fits are not substituted for complete selected-curve fits; available point summaries remain useful partials. Additional estimator kinds require another version rather than overloading a name.

Each returned numerical cell is closed: selector, cell_key, value, exact_value, conditional_value, conditional_exact_value, unit, formula_id, meaning_id, status(populated|conditional_scenario|unavailable), source_missing_reasons[], relationship_reasons[], implementation_reasons[], input_measurement_keys[], input_origins[], estimator_key|null, model_keys[], contribution_key, variance_status(not_applicable|estimated|unknown), count_basis and scope(full_selected_roster|available_points|not_applicable). The sheet retains version, axis A105, evaluation_scope reported_curve_precision, extraction, request, cells, calculation_metadata and remaining_implementation_limits. Each number has an explicit finite formula/meaning identifier; no free-form overall scores. Canonical exact rationals are retained for source-derived means/variances/covariances. Fitted numbers retain canonical decimal operands and solver diagnostics, not fictitious exact algebraic values.

Identities separate primitive measurement ownership, selected reported-curve roster, estimator, sampling/model assumption and contribution dependencies. Same-cell source aliases share measurement keys even across source records for the identical artifact. Different cells with equal data retain different keys. Two estimator rows sharing the39 primitive rates are overlapping calculations, not independent experiments. Estimator keys include canonical roster, units, estimator definition and numerical implementation version; model keys include status/provenance and IID assumption. A selector names one scalar covariance entry, not an unrequested matrix. Signed off-diagonal terms appear separately and their sum evaluates the stated variance.

## Numerical definitions and algorithm boundaries

At point i with n distinct numeric reported entries, mean=sum(y)/n; sample variance=sum((y-mean)^2)/(n-1); SD=sqrt(variance); CV=SD/mean only for positive mean. Full-set components require the complete selected roster. Available-point components declare their smaller denominator and cannot populate full-set fields. Zero, negative and missing values remain distinct. Descriptive variance does not require an IID assumption.

Fit each selected complete reported curve and the complete point-mean curve by unweighted positive-Km MM amount-rate least squares y=V*S/(K+S). Concentrations require witnessed compatible units; no dimensionless concentrations. Fit requires positive finite concentrations and a positive identifiable interior V/K solution with enough distinct substrate values. Use positive dimensionless normalization of x/y for numerical conditioning, then restore native units. Profile V analytically for each positive K. Proposed implementation uses a versioned finite log-K search in numerical units, brackets/refines profile-stationarity roots, checks Hessian/normal equations and compares candidate/boundary objectives. It must return fit_domain_exhausted or fit_solution_unresolved if a reliable unique interior solution is not established; no endpoint fit is quietly accepted. Numerical domain/tolerances are implementation diagnostics, not biological Km bounds or assay-quality thresholds. Before coding, root should review this finite-domain limitation; no claim of a mathematically global optimizer across arbitrary sources is intended. Source225 has an independently checked interior solution. No SciPy/complex suite installation is proposed.

For theta_j=(V_j,K_j), descriptive theta_bar=sum(theta_j)/n and C_theta=sum((theta_j-theta_bar)(theta_j-theta_bar)^T)/(n-1). Only the IID reporting-vector scenario yields C_mean_theta=C_theta/n for estimator mean_of_reported_curve_fits. Fit_of_point_means estimates theta_hat by fitting the means, not by averaging fits. Let C_y=sum((y_j-ybar)(y_j-ybar)^T)/(n-1), preserving all cross-concentration entries. Its conditional mean-curve covariance is C_y/n. At theta_hat, J_i=(S/(K+S),-V*S/(K+S)^2); retain the actual residual contribution H=J^TJ-sum_i residual_i Hessian(f_i). A=H^-1 J^T; conditional C_hat=A(C_y/n)A^T. Do not substitute the Gauss-Newton H or C_theta/n. Estimate signed terms g_a*C_ab*g_b with g=(1/V,-1/K); their full sum is the first-order variance of log(V/K). Diagonal-only variance is an explicitly different calculation, not extra verification.

Compute propagated covariance stably from centered reporting-vector modes when useful, while retaining each signed covariance contribution. This permits the valid rank-at-most(n-1) source covariance and avoids treating singular source C as invalid. The fitted2parameter Hessian must still be identifiable. Scale x by b and rates by a: V transforms by a, K by b, covariances by the corresponding products, and log-efficiency variance remains invariant. No normality, confidence interval, p-value, assay-error probability or function probability follows.

Residual decomposition uses all originally selected points: sum_j,i(y_ji-f_i)^2 = within-point SS + n*sum_i(ybar_i-f_i)^2. This is an arithmetic/model diagnostic without a significance threshold. No standard error is returned for an unknown/conflicting sampling model. Conditional results have value=null and conditional_value populated, retaining estimated rather than known variance status.

Reasons distinguish source absence, selection/association unknown, sampling assumption unknown/conflicting, unit meaning unknown, incomplete selected roster, insufficient distinct points/count, zero/nonpositive denominator, model not selected, fit numerical domain exhaustion, nonidentifiability, solver failure, numerical range and estimator mismatch. A fit failure does not remove native point statistics, other successful curves or exact source covariance. Failure is not falsely reported as missing scientific source information.

## Future binding handoff, not part of this coding ownership

Reuse literature.rate.observations.populate by an explicit versioned grid branch. Existing no-version v1 requests and saved records keep their original schemas and behavior. Storage must save complete validated extraction, computed requested cells, solver/model/estimator definitions, original argument selection and authenticated context/custody once. Future requested typed rows use the selector union and scalar cell identities; do not append grid numbers to an unbounded generic parent return.

Cold read validates saved artifacts/request/selection/dependencies and projects already saved selected rows. It must not call Workbook, reacquire context, refit or reinterpret a paper. If only CV was admitted, the recipient cannot inspect the private fitted parameters or covariance. Requesting a new component is new selected work with appropriate possession checks; it is not hidden reconstruction. Integration must add schemas, storage, prompt scientific display and transitive fingerprints under a separately assigned owner. No new unbound operation is advertised by228.

The common221 assessment currently accepts kcat/Km selected estimates in fixed units and supplied joint-selected-estimate covariance; it has no Vmax-native reported-grid estimator branch. Do not smuggle these conditional values into that contract or claim its binding/published-estimate covariance is implemented. General experimental-quality compilation, same-estimand contradiction compilation and W05 aggregation remain unfinished. This bounded feature is not A105 completion.

## Verification after coding release

- Use the retained original XLSX bytes, not a hand-built CSV replacement: verify39 rate lexemes,13 concentration lexemes and6 header witnesses against225's frozen packet. Verify exact point means/variances independently with Fraction or Decimal oracle arithmetic in tests.
- Independently check the two estimators, their signed covariance sums and difference. Compare solver output with parent227's high-precision numerical witnesses or an independent Decimal stationarity solver, not only a copied production algorithm. Finite-difference all13 point-mean sensitivity directions and observed-column modes.
- Unit/rate scaling, full cross-concentration covariance and low-rank n3 behavior; shared representations, duplicate aliases, equal-valued distinct cells and conflicting source associations.
- Synthetic XLSX fixtures clearly labelled synthetic: missing, ND, bounded, formula-cache, source-error and invalid numeric cells; preserve full roster and useful available-point/unaffected-curve results. Incomplete data cannot silently enter full-estimator covariance.
- No-model/unknown/conflicting versus stipulated/supported conditional behavior; source statistical support and physical unit identity never inferred from labels.
- Positive-Km boundaries, flat/negative/unidentifiable data, unsupported units, numerical overflow/underflow and explicit solver limits preserve native components.
- Legacy v1 inputs/calculations exact byte-prefix preservation and existing relevant166 tests; no modifications to old tests solely to accommodate new behavior.
- Validate closed schemas and each scalar selector, canonical identities/dependencies and no hidden-source mutation. No production transport/reconstruction success claimed until a later integration workload tests those paths.

Root review is implementation ownership coordination, not a runtime approval gate or request to alter the goal.
