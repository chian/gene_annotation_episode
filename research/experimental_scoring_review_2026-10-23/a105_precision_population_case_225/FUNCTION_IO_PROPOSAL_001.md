# Proposed source-grid to precision-component interface

Research proposal only. These functions are not installed or advertised operations. This proposes one bounded paired reader/calculator interface for a reported-curve section of A105. It does not release production files or add an episode, controller rule or overall grade. Root review and concrete ownership precede implementation under the existing user requirements.

## Reader: read_reported_rate_grid

Signature: `read_reported_rate_grid(content: bytes, selection: RateGridSelection, *, artifact_ref: str) -> ReportedRateGrid`.

The scientific selection contains **locations and meanings, never caller-supplied measured values**:

| Field | Declared type / case225 input |
| --- | --- |
| source_ref, source_kind | Scoped source identity; `primary_source` for this workbook |
| worksheet | Exact source name, `Sheet1` |
| panel | `{cell, expected_text}`, A189 and original FigS17 heading |
| subject | `{cell, expected_text}`, Q191=`PK_WT-DHA` |
| rate_header | `{cell, expected_text}`, B190=`NADH consumption rate µmol min-1` |
| concentration_column | Source column Q |
| rows | Explicit ordered source rows193:205; no fixed thirteen-row requirement in implementation |
| reported_curves | Ordered `{value_column, label_cell, expected_label}` entries R/R192/data-1, S/S192/data-2, T/T192/data-3 |
| concentration_unit_meaning | Value `mM` with exact S17-caption/method witness; `unknown`/`conflicting` allowed; workbook column lacks its own unit header |
| endpoint_meaning | Closed `reported_nicotinamide_rate` with status `conflicting` and both header/method witnesses; no automatic AcP or kcat mapping |
| reporting_to_physical_units | `unknown`, `supported` or `conflicting`, with actual source witnesses and nullable physical grouping; unknown for225 |

The host enforces source receipt, source/page ancestry and scope. The reader verifies workbook digest/member/worksheet identity, source labels, row/column association, numeric nonformula lexemes and full selected roster. Preserve cells that are absent, formula-cached, censored or nondetected without imputing a numeric point. Keep raw original-byte custody and decoded shared-string witnesses. Do not manufacture a physical measurement or sampling-unit identity from a column label or cell coordinate.

Reader output has closed fields: version; original source/workbook/member custody; selected label witnesses; subject and endpoint/unit meanings; ordered concentration entries with exact fractions; ordered reporting-curve entries with exact source-fraction rates/status/locations; source-record identities; reporting membership; nullable physical-unit/preparation membership; explicit unresolved relationships. The full source is host custody, not a numerical scoring cell.

**Actual225 output:** thirteen concentrations and39 numeric rate entries with exact Q193:Q205/R193:T205 locations. Physical preparation count and physical curve pairing remain null. Native amounts are source-reported µmol/min with the unresolved NADH-consumption/NADPH-production meaning retained.

## Calculator: populate_curve_precision

Signature: `populate_curve_precision(grid: ReportedRateGrid, request: CurvePrecisionRequest) -> CurvePrecisionSection`.

Request fields are closed and separate from the source selection:

- `model`: `michaelis_menten_amount_rate` for225; explicit modeled endpoint applicability remains qualified.
- `fit_domain`: positive Km and finite native-rate fit; native signed/censored entries remain available when a requested fit is unavailable.
- `weighting`: `unweighted` for the worked research calculation; alternative weighting needs its own defined operands/model, not an inferred Prism default.
- `estimator`: `each_reported_curve`, `mean_of_reported_curve_parameter_vectors` or `fit_to_reported_point_means`.
- `unit_model`: `none` or `iid_reporting_curve_vectors`. IID must carry `supported` or `stipulated_sensitivity` meaning and source/model provenance.225 only supports a separately stipulated scenario, not source-established physical IID.
- `requested_cells`: ordered selected components, enforced against the parent's requested section on eventual integration.

Pure output contains the following numerical cells with exact or finite numeric value, units, source origins, formula, estimator key, source-entry dependency keys, model key, statistical-scope status and specific reason lists:

| Component | Formula / actual225 result | Scope |
| --- | --- | --- |
| Point mean and descriptive variance | mean_i=sum(yij)/3; s_i²=sum((yij−mean_i)²)/2 | Across reported entries; no independent n |
| Point SD/CV | sqrt(s_i²), SD/mean_i | Descriptive precision only; CV unavailable at nonpositive mean |
| Column-fit parameter vector | argmin sum_i[yij−V*S_i/(K+S_i)]² | Derived parameter on each source reporting column |
| Descriptive parameter covariance | sum_j[(θj−meanθ)(θj−meanθ)ᵀ]/(3−1) | Distribution of fitted reporting-column vectors |
| Conditional covariance of mean fitted vectors | sampleCov(θj)/3 | Applies to meanθ only, conditional IID-column-vector scenario |
| Fit-to-means sensitivity | A=(JᵀJ−sum_i residual_i*Hessian(f_i))⁻¹Jᵀ | Applies to the exact selected fit-to-mean estimator |
| Conditional covariance of fit-to-means parameters | A*(sampleCov(reported curve vectors)/3)*Aᵀ | Full empirical cross-concentration covariance retained; conditional IID reporting curves |
| Conditional log-native-efficiency variance | gᵀ*C*g, g=(1/V,−1/K) |225 fit-to-means value0.00339273234; no p-value or function probability |
| Within-reported-entry/model residual SS | SS_total=SS_within+n_curves*SS_mean_fit | Descriptive decomposition, no acceptance threshold |

Numerical matrices must declare parameter order, row/column units, exact selected estimator and shared dependencies. Descriptive covariance **cannot** use basis `joint_covariance_of_selected_estimates`. Conditional estimator covariance can use that mathematical target only with its explicit model/scope carried through; it cannot be stripped into an apparently source-established matrix. Normality or known variance is not inferred from these estimates.

Estimator identities differ even with the same source cells. `mean(column fits)` gives Km36.49549; `fit(point means)` gives Km35.87599. The published S5Km35.88 remains a third, source-reported estimate with undocumented fit basis. The numerical closeness does not authorize attaching either derived covariance to it.

## Current consumer boundary

The existing kinetic model consumes same-parameter numerator/denominator **log covariance**, with actual operand ownership. This Vmax/Km native matrix is a different object. The existing common section has kcat/Km native roles, no Vmax role, no derived-grid estimate input and no low-efficiency contrast uncertainty component. It must not accept Vmax as kcat or a descriptive matrix as covariance of its existing operands.

An eventual conversion needs a compatible numerical section/typed derived estimate with estimator, normalization, scientific model and sampling scope preserved. For kcat specifically, the applicable enzyme molecular amount and active-fraction basis must be supplied. Source absence remains separate from unimplemented conversion.225 returns no unconditional covariance, no physical preparation count and no current common/kinetic covariance export.

These are source/scientific limitations, not runtime approval mechanisms. Useful native means, variability, fitted curve descriptions and explicitly conditional scenarios survive. They are numerical components within the same A105 sheet; table/reader/function/parameter counts are not independent assay counts.

## Necessary meaningful verification

Verify original workbook/header/row/column custody, numeric/formula/absence behavior, transposed source layout, repeated representation identity and unknown physical grouping. Verify estimator mismatch rejection, known endpoint conflicts, unit scaling, dependency identities and full signed propagation. Check numeric fits against independent algorithms/derivatives and preserve partial native results when fitting fails. Later selected integration must independently verify exact parent scope, typed delivery, first-read-only saved reconstruction without fitting/reacquisition, and ordinary observation accounting. Research arithmetic alone establishes none of those integration requirements.
