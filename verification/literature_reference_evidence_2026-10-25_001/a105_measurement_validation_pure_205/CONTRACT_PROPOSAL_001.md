# Bounded pure measurement-validation contract, proposal001

This proposal changes no goal, authority, controller, existing recovery implementation or final annotation credit. Three new pure modules and tests only. Storage, rendering, selected LiteratureEpisodes execution and typed delivery remain a later workload. The source is retained PMC6454709, authenticated against its original bytes; no new paper is requested.

## Closed selected inputs

`measurement_validation_population_schema()` returns a closed object with:

- `source_ref`, `source_kind` = primary_source / retained_extraction / synthetic_fixture.
- `context`: nullable exact source witnesses for experiment, analyte, matrix, method, endpoint, repetition, mean_definition, nominal_uncertainty. These remain literal evidence, not assigned numerical grades or invented counts.
- `recovery` and `relative_bias`: nullable selectors, each closed namespace=`literature_calibration_recovery_cells`, sheet_ref, component fixed to its role. `read_component(selector)` returns exactly the actually possessed row. There is no read_record or private upstream read. Full existing recovery-row schema is validated. Both rows must share sheet, source, source-kind/origins, nominal/measured dependency-key sequence, source meanings, control role, dimensional scope and exact rational identity `bias=recovery-1`. A malformed or inconsistent pair returns a specific partial-pair reason without erasing native CV/Z. Borrowed rows and invalid selectors fail authorization; no callback fallback.
- `precision`: list of closed records: `number` exact selector, `quantity_label` witness explicitly identifying CV/coefficient of variation, `unit` closed value=percent/fraction plus exact witness, `basis` witnessed enum within_run/between_run/between_preparation/unspecified/unknown/conflicting, and witnessed relationships `mean_precision_population`=same/different/unknown/conflicting, `cv_denominator`=displayed_measured_mean/other_reported_mean/unknown/conflicting, `recovery_context`=same/different/unknown/conflicting, `validation_relation`=held_out_observations_and_stock_supported/shared_fit_or_stock/unknown/conflicting. Unknown requires no positive witness; conflicting requires two distinct physical witnesses. Positive declarations require original witnesses. Semantic interpretation remains the caller's responsibility.
- `zprime`: list of closed records: `number`, explicit `quantity_label`, witnessed `formula_relation`=conventional_zprime/different/unknown/conflicting. Conventional formula means exactly `1-3*(SDpos+SDneg)/abs(meanpos-meanneg)`; native Z is retained independently of this relation.

Original byte witnesses and character offsets are validated. Local dimensionless scalar reading reuses shared lexical helpers while retaining exact rational values when binary float range is unavailable. Bounds stay bounds; bounded CVs never silently supply point precision. A local label/unit guard checks table-column association when a number is in an XML table, disallowing CV headers borrowed across an RE/Z column or table. Adjacent explicit units, including units after a plus/minus spread, cannot be overwritten by the selected header. Percent/fraction witnesses must be complete; compound-unit clipping is rejected. Source labels are lexical evidence, not proof of population relationships.

## Pure functions and retained contracts

`read_measurement_validation_inputs(arguments, *, read_source, read_component)` verifies selected source bytes and possessed rows; returns `a105_measurement_validation_inputs_v1`. `measurement_validation_extraction_schema()` is closed and retains enriched witnesses, number relations/exact values/native origins/dependency identities, all interpreted relationships and the optional pair with a finite pair-reason list. Repeated aliases with the same numeric span share their measurement key. Compatible duplicates coalesce with retained alias selections; incompatible assignments return a specific error. Equal values at different spans remain distinct without claiming independence.

`populate_measurement_validation(extraction)` validates retained contracts without source IO and returns `a105_measurement_validation_components_v1`; `measurement_validation_sheet_schema()` defines it. Sheet has axis=A105, section=measurement_validation, extraction, precision sections, Z sections, explicit unimplemented raw-control route, qualifications and annotation_credit=null. Each section retains scientific context and original dependencies. No empty framework sheet or initial candidate annotation is required.

The finite numerical cell names are `reported_cv`, `cv_fraction`, `relative_bias_squared`, `relative_variance_plugin`, `relative_squared_deviation_plugin`, `relative_rms_percent`, `reported_zprime`, `control_band_ratio`, `raw_control_zprime`. Precision sections expose the first six cells; Z sections expose the next two; raw-control cell is unimplemented. Cells contain value/exact_value, conditional_value/conditional_exact_value, status=populated/conditional/unavailable, interpretation=native_statistic/deterministic_reexpression/estimated_plugin/conditional_plugin/unimplemented, origin=reported/derived/synthetic/proposed, input_origins, relation=point/lt/le/gt/ge, unit, formula, input_measurement_keys, contribution_key, assumptions and finite unavailable_reasons. Range failure preserves exact rationals and returns numerical_model_range rather than clamping or losing all partials. Root display is approximate and has no rational exact_value unless the square root is exactly rational.

## Components and worked source values

For actual possessed recovery `r=M/N`, exact bias `b=r-1`, and a point CV `c` converted from explicit percent/fraction:

| Cell | Formula | 8.6/8.72, within CV0.8% | Meaning |
|---|---|---:|---|
| reported_cv | source number | 0.8 percent | Native reported precision statistic |
| cv_fraction | reported/100 | 0.008 | Same native statistic in fraction units |
| relative_bias_squared | b² | 0.00019469983775013521 | Squared displayed relative calibration bias |
| relative_variance_plugin | (c*r)² | 0.00006579850730124391 conditional | Relative variance if c=SD/M on the same population |
| relative_squared_deviation_plugin | b²+(c*r)² | 0.00026049834505137914 conditional | Proposed relative squared-error plug-in estimate |
| relative_rms_percent | 100 sqrt(previous sum) | 1.613996112298227 conditional | Same contribution displayed as percent RMS |
| reported_zprime | source Table2 | 0.99 | Native reported control separation statistic |
| control_band_ratio | (1-Z')/3 | 0.0033333333333333335 | Same statistic under the source-supported formula |

Actual mean/population and denominator relationships are UNKNOWN, therefore variance/loss/RMS `value=null`, `status=conditional`, with the numbers above only in conditional_value and explicit assumptions. With source-supported same-population/displayed-mean/recovery-context relationships, a positive displayed mean and nonnegative CV, the same formula becomes status=populated, interpretation=estimated_plugin, origin=proposed; still not a known population moment, unbiased residual MSE or verified predictive MSE. Validation independence and nominal uncertainty remain separate qualifications, not fabricated gates or numbers.

Between-run CV1.7% supplies an alternative conditional loss0.0004918212222823148/RMS2.2177042685676437%, never an additional variance component. Native negative CV or Z>1 remain reported facts plus incompatibility, not clamped valid precision/band ratios. Negative Z is valid. Z bounds reverse when re-expressed under the supported formula; bounds that imply an impossible negative band ratio preserve the source limit and mark incompatibility. Raw control means/SD and zero-separation recomputation are explicitly unimplemented. CV is never substituted for a control SD. R² never supplies residual variance.

Prepared cofactor standards, purified human G6PD WST/UV arms, and the G6PD-serum enzyme spike remain distinct. Five days triplicate is not15 biological preparations. Standard-buffer applicability to complete assay matrix, pooling, nominal-stock uncertainty and validation independence remain unknown. WST/UV share NADPH and do not identify the organic product or establish productive coupling. No q=(As-Ab)/(m*t) conversion or product bridge is implemented here.

## Exact recurring TASK proposal

Determine what the selected precision and control-separation measurements establish about quantification of the reference molecule's assay endpoint. Begin from the supplied sequence, selected file contents or snippets and the experimental material actually received; a candidate annotation or public name is not required. Identify the assayed analyte, matrix, method, endpoint, standards and repetition basis. Keep prepared reporter standards, enzyme-activity spikes and functional-assay measurements separate. Possible functions can emerge from the evidence.

Select the reported coefficient of variation and its complete percent or fraction unit, actual within-run, between-run or between-preparation basis, and source definitions of the population and mean denominator. Determine separately whether the displayed mean and precision summarize the same population, whether CV uses that displayed mean, and whether the possessed recovery pair describes the same standard context. Do not infer these links from adjacent rows, matching values or one publication. Preserve unknown or conflicting relationships. Technical repetitions and repeated representations are not independent biological preparations.

Use only the recovery and relative-bias components actually received. Their original source and nominal/measured dependencies must agree. Ask the deterministic calculator for the requested precision and bias/precision components. Keep conditional arithmetic visibly conditional when the required population or denominator link is missing. Even supported calculations from displayed summaries remain estimates; do not call them source-reported MSE, unbiased empirical MSE or known predictive error. Within-run and between-run precision are alternative bases and must not be added as independent variance components.

For a reported Z-prime statistic, select its exact value or bound, statistic label and source formula. Retain the native statistic when raw positive/negative control means or SDs are absent. A formula-supported control-band ratio is a re-expression of that same statistic. Negative Z-prime is allowed; values above one retain their incompatibility with the conventional formula. Do not substitute CV for raw control SD or invent missing controls, uncertainty, pooling or calibration independence.

Keep calibration bias, precision, control separation, endpoint relevance and molecular attribution distinct. A precise NADPH reporter response does not identify an organic product, demonstrate productive coupling or establish that standard-buffer validation applies to a complete enzyme assay. Preserve shared measurements, units, bounds, source origins and specific limitations. Return the requested numerical components and their qualifications without an overall reliability grade, function probability or annotation credit.

This detailed TASK insert recurs in full; it is separate from the numerical sheet and from selected factual STEERING. No prompt renderer or runtime integration is changed by the pure workload.
