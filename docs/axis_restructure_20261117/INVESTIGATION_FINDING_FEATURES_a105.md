# A105 (experimental_activity_evidence): investigation finding features

Proposal for the owner to correct line by line. No code was changed and no Python was run.

An investigation finding is a set of fields. Every field has a controlled answer set that code can validate: a
number with a range and unit, an integer count, a boolean, a value of a fixed vocabulary, or a record reference.
There is no open field and no field that holds several pieces of evidence. A gene, function or product ID or name
would be an annotation field: its source list is stated as its meaning only, and no code looks it up or verifies it.
The A105 sheets carry no such name (see section 6).

## 0. What was read, and three things that were not where the brief said

| # | Fact | Where |
|---|---|---|
| 0.1 | The A105 subscoring sheet is `a105_assay_grading_sheet_v1`. Its schema (`assay_grading_sheet_schema`, `assay_grading_cell_schema`, `COMPONENTS`, `CRITERIA_BY_TYPE`, `QUANTITY_KINDS`) is in `literature/grading/experimental_activity_evidence/literature_assay_grading.py`. That folder was not in the list I was given. I read that one file and `literature_required_grading.py` beside it, because `storage/experimental_activity_evidence/literature_assay_grading_storage.py` imports the schema from there. Nothing else outside the named folders was read. | grading file, storage file |
| 0.2 | `forms/literature_numerical_contracts.py` is the A106 catalog: every path in its `_SCHEMAS` points at `perturbation_evidence`, and its docstring says A105 declarations are not imported. The A105 list of reader families is `SOURCE_SCHEMAS` in `inputs/experimental_activity_evidence/literature_assay_grading_inputs.py` (36 families). | both files |
| 0.3 | A105 has one grader and one aggregator. The other 36 families are readers: they produce operands that the grader takes in (`quantities` roles). They are not graders and grade nothing. | `EFFECT_ROUTES`, `read_assay_grading_inputs` |
| 0.4 | Which episode writes which sheet: `table_evidence_extraction` writes only the assay grading sheet (through `literature_required_grading.execute` with `LiteratureAssayGradingRepository`). `passage_evidence_extraction` and `source_coverage_improvement` write the assay grading sheet the same way and, when the settings enable them, the reader sheets and `literature.a105.aggregate`. | the three `task.py` files |
| 0.5 | `obj(...)` is taken to mean "all listed properties required" unless a `required=` list is passed. `domain.obj` is outside the named folders and was not opened; the owner should correct the "required" column if that reading is wrong. | every schema below |
| 0.6 | The saved grading record holds more than the sheet: `selection`, `extraction`, `sheet`, `input_component_rows`, `direct_record_refs`, `input_source_refs`. Fields below marked "record, not sheet" come from `selection`, `extraction` or `input_component_rows` of the same record. | `LiteratureAssayGradingRepository.populate` |

## 1. Proposed `evidence_type` vocabulary for A105

| Value | Meaning | Source of the value |
|---|---|---|
| `activity_rate` | Enzyme activity and rate comparisons | sheet `assay_type` |
| `endpoint_conversion` | Reaction progress and endpoint conversion | sheet `assay_type` |
| `product_distribution` | Product distribution and equilibrium | sheet `assay_type` |
| `reaction_coupling` | Reaction coupling and stoichiometric balance | sheet `assay_type` |
| `ligand_binding` | Ligand binding and binding discrimination | sheet `assay_type` |
| `transport_response` | Transport and substrate-response comparisons | sheet `assay_type` |
| `protein_signal` | Reported protein signals and band measurements | sheet `assay_type` |
| `protein_amount` | Protein amount and preparation composition | sheet `assay_type` |
| `across_experiment_aggregate` | The sum/max aggregation over selected experiments | aggregation sheet (section 3) |
| `no_applicable_evidence` | Source-grounded finding that the examined material holds no applicable experiment or result; the only outcome with no sheet | `evidence_processing.kind` (section 4) |

The first eight are the owner's own `ASSAY_TYPES`, unchanged. The last two are added by this proposal.

## 2. Grader: assay grading sheet (`a105_assay_grading_sheet_v1`)

### 2.1 What it grades

One selected measurement of one experiment against one asserted function: it takes the native effect, its variance
and the two fixed predictions (assertion, alternative), and calculates nine cells ending in a signed log evidence
ratio. One sheet per (experiment, assertion) assessment. Tool: `literature.assay_grading.populate`; namespace
`literature_assay_grading_cells`.

### 2.2 Sheet fields as the schema names them

| Field | Type | Answer set | Required |
|---|---|---|---|
| `version` | const | `a105_assay_grading_sheet_v1` | yes |
| `axis` | const | `A105` | yes |
| `evaluation_scope` | const | `assay_type_experimental_evidence` | yes |
| `assay_type` | enum | the eight values in section 1 | yes |
| `assertion_ref` | record ref | hypothesis record | yes |
| `quantity_kind` | enum | per `assay_type`, table 2.5 | yes |
| `cells` | object | exactly the nine components of 2.3, each a cell of 2.4 | yes |
| `interpretations` | object | keys from the criteria of the `assay_type` (2.6); each `{status, support_refs}` | yes (each criterion key optional) |
| `interpretations.<criterion>.status` | enum | `supported`, `unknown`, `conflicting`, `not_applicable` | yes |
| `interpretations.<criterion>.support_refs` | record refs | reference records | yes |
| `prediction_model` | object or null | `{kind, variance_interpretation, support_refs}` | yes |
| `prediction_model.kind` | enum | `fixed_predictions_known_normal`, `fixed_predictions_estimated_normal`, `fixed_predictions_student_t` | yes |
| `prediction_model.variance_interpretation` | enum | `known`, `estimated`, `unknown` | yes |
| `annotation_credit` | null | always null | yes |

Added on the delivered rows (`assay_grading_cells_schema`): `sheet_ref` (record ref, required),
`evidence_source_ref` (record ref, required), `experiment_ref` (record ref, not required).

### 2.3 The nine cells

| `component` | `dimension` | Formula as the sheet states it | Unit | Statuses that can occur |
|---|---|---|---|---|
| `measured_effect` | `measurement` | `selected_native_effect` | unit of the effect | `populated`, `bounded`, `unavailable` |
| `effect_variance` | `reliability` | `selected_variance_of_native_effect` | effect unit squared | `populated`, `unavailable` |
| `effect_precision` | `reliability` | `1/variance` | 1/(variance unit) | `populated`, `conditional`, `unavailable` |
| `recovery_deviation` | `validity` | `recovery-1` | dimensionless | `populated`, `unavailable` |
| `attributed_fraction` | `attribution` | `attributed_signal/total_signal` | fraction | `populated`, `unavailable` |
| `condition_response` | `comparability` | `condition_test/condition_reference` | dimensionless | `populated`, `unavailable` |
| `assertion_prediction_error` | `relevance` | `effect-assertion_prediction` | unit of the effect | `populated`, `conditional`, `bounded`, `unavailable` |
| `alternative_prediction_error` | `relevance` | `effect-alternative_prediction` | unit of the effect | `populated`, `conditional`, `bounded`, `unavailable` |
| `source_log_evidence_ratio` | `experimental_evidence` | log likelihood ratio, assertion against alternative | dimensionless | `conditional`, `unavailable` |

### 2.4 Cell fields as the schema names them

| Field | Type | Answer set | Required |
|---|---|---|---|
| `component` | enum | the nine names of 2.3 | yes |
| `dimension` | enum | `measurement`, `reliability`, `validity`, `attribution`, `comparability`, `relevance`, `experimental_evidence` | yes |
| `value` | number or null | finite | yes |
| `unit` | string | open in the schema; see 2.8 line U | yes |
| `status` | enum | `populated`, `conditional`, `bounded`, `unavailable` | yes |
| `input_origins` | array of enum | `reported`, `derived`, `graph_derived`, `synthetic`, `proposed` | yes |
| `bound.relation` | enum | `lt`, `le`, `gt`, `ge`, `interval` | no (`bound` present only when bounded) |
| `bound.lower`, `bound.upper` | number or null | finite | no |
| `measurement_keys` | array of string | identity keys | yes |
| `source_refs` | array of record refs | | yes |
| `reasons` | array of string | not a closed list (prose column, 2.9) | yes |
| `conditions` | array of string | not a closed list (2.9) | yes |
| `formula` | string | fixed text per component (2.9) | yes |
| `meaning` | string | fixed prose per component (2.9) | yes |

### 2.5 `quantity_kind` per `assay_type`

| `assay_type` | `quantity_kind` values |
|---|---|
| `activity_rate` | `rate`, `rate_difference`, `rate_ratio`, `turnover`, `catalytic_efficiency`, `kinetic_parameter`, `kinetic_parameter_difference`, `kinetic_parameter_ratio`, `log_kinetic_parameter_ratio`, `partner_rate_difference`, `partner_response_fraction` |
| `endpoint_conversion` | `conversion_fraction`, `conversion_difference`, `endpoint_amount`, `completion_time`, `completion_time_ratio` |
| `product_distribution` | `product_fraction`, `product_fraction_ratio`, `equilibrium_fraction`, `equilibrium_ratio` |
| `reaction_coupling` | `productive_fraction`, `stoichiometric_ratio`, `balance_residual` |
| `ligand_binding` | `binding_parameter`, `binding_parameter_ratio`, `log_binding_parameter_ratio`, `binding_discrimination_ratio`, `log_binding_discrimination`, `band_display_fraction`, `relative_binding_response`, `log_relative_binding_response` |
| `transport_response` | `transport_rate`, `transport_rate_ratio`, `log_transport_rate_ratio`, `accumulated_amount`, `transport_parameter`, `substrate_saturation`, `substrate_response_ratio`, `log_substrate_response`, `electrical_current`, `electrical_conductance`, `charge_equivalent_rate` |
| `protein_signal` | `signal_ratio`, `signal_difference`, `log_signal_ratio`, `band_display_fraction`, `band_display_darkness` |
| `protein_amount` | `protein_amount`, `protein_amount_difference`, `protein_amount_ratio`, `sites_per_monomer`, `active_fraction` |

### 2.6 Criteria per `assay_type` (the keys of `interpretations`)

Nine criteria are common to every assay type: `measurement_identity`, `calibration_applicability`,
`matrix_interference`, `background_alternatives`, `attribution_supported`, `assertion_relevance`, `condition_scope`,
`variance_correspondence`, `sampling_basis`.

| `assay_type` | Its own criteria | Total | May be `not_applicable` (by `quantity_kind`) |
|---|---|---|---|
| `activity_rate` | `rate_regime`, `normalization_basis`, `kinetic_model`, `partner_perturbation` | 13 | `kinetic_model` unless a kinetic/turnover/efficiency kind; `rate_regime`, `normalization_basis` for kinetic-parameter kinds; `partner_perturbation` unless a `partner_` kind |
| `endpoint_conversion` | `endpoint_alignment`, `conversion_denominator`, `product_identity` | 12 | `product_identity`; `conversion_denominator` for `endpoint_amount`, `completion_time`, `completion_time_ratio` |
| `product_distribution` | `species_identity`, `response_factors`, `common_denominator`, `equilibrium_state` | 13 | `equilibrium_state` unless an `equilibrium_` kind |
| `reaction_coupling` | `product_identity`, `stoichiometry`, `matched_windows`, `reporter_specificity` | 13 | none |
| `ligand_binding` | `binding_parameter_definition`, `binding_species`, `binding_controls`, `binding_regime`, `binding_comparison` | 14 | `binding_parameter_definition` for `band_display_fraction` |
| `transport_response` | `membrane_system`, `transport_endpoint`, `transport_driving_force`, `transport_specificity`, `transport_response_model` | 14 | `transport_response_model` unless a parameter/saturation/response kind |
| `protein_signal` | `signal_assignment`, `signal_response_range`, `signal_normalization`, `signal_representation` | 13 | none |
| `protein_amount` | `amount_basis`, `preparation_relationship`, `amount_calibration`, `active_site_stoichiometry` | 13 | `active_site_stoichiometry` unless `sites_per_monomer` or `active_fraction` |

### 2.7 Proposed investigation finding for one assay grading sheet

The same field set serves all eight assay types; only the criterion fields (line C) differ by type, as table 2.6
lists. One finding per saved sheet. "core" is what I would return; "optional" is offered for the owner to strike or
keep.

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | `sheet.assay_type` | vocabulary | the eight assay types of section 1 | | core |
| Q | `quantity_kind` | `sheet.quantity_kind` | vocabulary | the row of 2.5 for the `evidence_type` | | core |
| R1 | `sheet_ref` | the saved sheet's id | record ref | source record of provider `literature.a105.assay_grading` | | core |
| R2 | `experiment_ref` | `selection.experiment_ref` (record, not sheet) | record ref | reference record with `reference_type` `assay` | | core |
| R3 | `assertion_ref` | `sheet.assertion_ref` | record ref | hypothesis record | | core |
| S1 | `source_log_evidence_ratio` | `cells.source_log_evidence_ratio.value` | number or null | finite; signed, positive supports the assertion | natural log, dimensionless | core |
| S2 | `source_log_evidence_ratio_status` | `cells.source_log_evidence_ratio.status` | vocabulary | `conditional`, `unavailable` | | core |
| E1 | `effect_value` | `cells.measured_effect.value` | number or null | finite | `effect_unit` | core |
| E2 | `effect_status` | `cells.measured_effect.status` | vocabulary | `populated`, `bounded`, `unavailable` | | core |
| U | `effect_unit` | `cells.measured_effect.unit` | vocabulary | the units `_quantity_unit_supported` admits for the `quantity_kind`, plus `unknown` (see 2.8) | | core |
| E3 | `effect_bound_relation` | `cells.measured_effect.bound.relation` | vocabulary | `lt`, `le`, `gt`, `ge`, `interval`, `none` (`none` when no bound) | | optional |
| E4 | `effect_bound_lower` | `cells.measured_effect.bound.lower` | number or null | finite | `effect_unit` | optional |
| E5 | `effect_bound_upper` | `cells.measured_effect.bound.upper` | number or null | finite; above `effect_bound_lower` when both present | `effect_unit` | optional |
| E6 | `effect_origin` | the one entry of `cells.measured_effect.input_origins` | vocabulary | `reported`, `derived`, `graph_derived`, `synthetic`, `proposed`, `not_selected` | | core |
| V1 | `effect_variance` | `cells.effect_variance.value` | number or null | finite, >= 0 | `effect_unit` squared | core |
| V2 | `effect_variance_status` | `cells.effect_variance.status` | vocabulary | `populated`, `unavailable` | | core |
| V3 | `effect_precision` | `cells.effect_precision.value` | number or null | finite, > 0 | 1/(`effect_unit` squared) | optional (it is 1/V1) |
| V4 | `effect_precision_status` | `cells.effect_precision.status` | vocabulary | `populated`, `conditional`, `unavailable` | | optional |
| D1 | `recovery_deviation` | `cells.recovery_deviation.value` | number or null | finite, > -1 | dimensionless | optional |
| D2 | `attributed_fraction` | `cells.attributed_fraction.value` | number or null | finite; the grader does not clamp it to 0..1 | fraction | optional |
| D3 | `condition_response` | `cells.condition_response.value` | number or null | finite, >= 0 | dimensionless | optional |
| D4 | `assertion_prediction_error` | `cells.assertion_prediction_error.value` | number or null | finite, signed | `effect_unit` | optional |
| D5 | `alternative_prediction_error` | `cells.alternative_prediction_error.value` | number or null | finite, signed | `effect_unit` | optional |
| M1 | `prediction_model_kind` | `sheet.prediction_model.kind` | vocabulary | `fixed_predictions_known_normal`, `fixed_predictions_estimated_normal`, `fixed_predictions_student_t`, `not_selected` (`not_selected` when the model is null) | | core |
| M2 | `variance_interpretation` | `sheet.prediction_model.variance_interpretation` | vocabulary | `known`, `estimated`, `unknown`, `not_selected` | | core |
| M3 | `effect_degrees_of_freedom` | `extraction.quantities.effect_degrees_of_freedom.value` (record, not sheet) | number or null | finite, > 0 | count | optional |
| C | `<criterion>_status`, one field per criterion of the `evidence_type` (12 to 14 fields, table 2.6) | `sheet.interpretations.<criterion>.status` | vocabulary | `supported`, `unknown`, `conflicting`, `not_applicable`, `not_selected` (`not_selected` when the key is absent) | | core |
| N1 | `criteria_supported_count` | code counts criteria with status `supported` | integer | 0 to the total of 2.6 | count | optional (compressed alternative to C) |
| N2 | `criteria_unresolved_count` | code counts criteria that are `unknown`, `conflicting` or absent | integer | 0 to the total of 2.6 | count | optional (compressed alternative to C) |
| N3 | `effect_measurement_count` | `len(cells.measured_effect.measurement_keys)` | integer | >= 0 | count | optional |
| N4 | `evidence_unavailable_reason_count` | `len(cells.source_log_evidence_ratio.reasons)` | integer | >= 0; 0 exactly when S2 is `conditional` | count | optional |
| O1 | `evidence_uses_synthetic_input` | `'synthetic' in cells.source_log_evidence_ratio.input_origins` | boolean | true/false | | core |
| O2 | `evidence_uses_proposed_input` | `'proposed' in` the same list | boolean | true/false | | core |
| O3 | `evidence_uses_graph_derived_input` | `'graph_derived' in` the same list | boolean | true/false | | optional |

Across the sheets an episode holds (the per-episode summary, not one sheet):

| # | Finding field | How code computes it | Type | Validator | Unit |
|---|---|---|---|---|---|
| A1 | `assay_count` | distinct `experiment_ref` among the episode's saved sheets with this `assertion_ref` (`experiment_sheets` already groups this way) | integer | >= 0 | count |
| A2 | `assessment_count` | number of saved sheets with this `assertion_ref` | integer | >= `assay_count` | count |
| A3 | `assay_count_with_evidence_ratio` | distinct `experiment_ref` whose sheet has S2 = `conditional` | integer | 0 to `assay_count` | count |

### 2.8 Points the owner must settle for this grader

| # | Point |
|---|---|
| U | `unit` is an open string in the cell schema. The values are code-produced (`_unit` aliases in the inputs file, or the reader cell's own unit enum), and the grader holds a closed list per `quantity_kind` in `_quantity_unit_supported`. The proposal validates `effect_unit` against that list plus `unknown`. A unit outside the list makes the two prediction-error cells and the evidence ratio unavailable (`quantity_kind_unit_unsupported`), but `measured_effect` still carries it, so the validator would have to reject or map it. |
| G1 | Target correspondence is not on the sheet. The old finding kept "unresolved target correspondence" in its qualification prose. The sheet has no cell or criterion for it; the evidence-ratio cell always carries the fixed condition `no_target_correspondence_or_W05_aggregation`. No controlled field in this proposal carries it. If the owner wants it, it needs a new sheet field with a fixed vocabulary. |
| G2 | The number of replicates or independent preparations inside one experiment is not on the grading sheet. It exists only on some reader sheets (section 5) and, for a Student-t model, as `effect_degrees_of_freedom` in the record's `extraction`. Line M3 is the only replicate-like number reachable without reading a reader row. |
| G3 | The credit files today test `investigation_finding.status == 'retained'`. `retained` is the only value I saw; the full list of that field's values was not found in the folders I read. |

### 2.9 Sheet fields left out because they are prose or open strings

| Sheet field | Why it is out | Controlled fields that carry what it meant |
|---|---|---|
| `cells.<c>.meaning` | fixed explanatory sentence per component | the component name itself (the finding field name) |
| `cells.<c>.formula` | fixed text per component; three variants for the evidence ratio | `prediction_model_kind` and `effect_status` (`bounded` selects the censoring formula) |
| `cells.<c>.reasons` | list of strings; includes reader-supplied reason text and `..._source_qualification:<text>`, so not a closed list | `<component>_status`, the `<criterion>_status` fields, `variance_interpretation`, `evidence_unavailable_reason_count` |
| `cells.<c>.conditions` | list of strings; fixed grader codes plus reader qualifications | `prediction_model_kind`, `effect_status`, `effect_origin`, the `evidence_uses_*` booleans |
| `cells.<c>.unit` for cells other than the effect | derivable | `effect_unit` (variance is its square, errors share it, the rest are dimensionless or fraction) |
| `cells.<c>.measurement_keys` | identity hashes, not evidence | `effect_measurement_count`; the keys stay behind `sheet_ref` |
| `cells.<c>.source_refs`, `interpretations.<c>.support_refs`, `prediction_model.support_refs` | lists of record refs to the supporting passages | `sheet_ref` (the parent reaches them through the sheet) |
| `annotation_credit` | always null | nothing; credit is the system's signal |
| `version`, `axis`, `evaluation_scope` | constants | nothing |
| `extraction.quantities.<role>.reason`, `.qualifications`, `.native_component` (record, not sheet) | strings | `effect_status`, `effect_origin` |
| the criterion questions (`CRITERION_QUESTIONS`) | prose shown to the model, not sheet data | the `<criterion>_status` field names |

## 3. Aggregator: across-experiment aggregation sheet (`a105_across_experiment_aggregation_v1`)

### 3.1 What it grades

Nothing new: it applies the owner's reducers to grading-sheet cells the parent selected, one per experiment and
metric: `reliability` sum, `validity` sum, `relevance` max, `attribution` max, `overall` sum. Tool:
`literature.a105.aggregate`; namespace `literature_a105_aggregation_cells`.

### 3.2 Fields as the schema names them

| Field | Type | Answer set | Required |
|---|---|---|---|
| sheet `version` | const | `a105_across_experiment_aggregation_v1` | yes |
| sheet `axis` | const | `A105` | yes |
| sheet `evaluation_scope` | const | `a105_across_experiment_aggregation` | yes |
| sheet `assertion_ref` | record ref | hypothesis record | yes |
| sheet `comparison_ref` | record ref or null | hypothesis record | yes |
| sheet `experiment_refs` | array of record refs | reference records | yes |
| sheet `cells` | object | `reliability`, `validity`, `relevance`, `attribution`, `overall` | yes |
| sheet `annotation_credit` | null | always null | yes |
| cell `component` | enum | `reliability`, `validity`, `relevance`, `attribution`, `overall` | yes |
| cell `dimension` | enum | `reliability`, `validity`, `relevance`, `attribution`, `experimental_evidence` | yes |
| cell `comparison_binding` | enum | `parent_declared`, `not_declared` | yes |
| cell `reducer` | enum | `sum`, `max` | yes |
| cell `value` | number or null | finite; null unless every selected experiment contributed | yes |
| cell `available_value` | number or null | finite; the reducer over the experiments that did contribute | yes |
| cell `status` | enum | `complete`, `partial`, `unavailable` | yes |
| cell `unit` | string | open in the schema; code writes the single input unit, `mixed_native_units` or `unknown` | yes |
| cell `selected_experiment_refs`, `available_experiment_refs`, `missing_experiment_refs` | arrays of record refs | reference records | yes |
| cell `missing_inputs[].reason` | string | code-written: `metric_component_not_selected` or `selected_component_<status>` | yes |
| cell `selected_components` | array of grading-sheet rows | section 2.4 | yes |
| cell `input_units`, `source_component_names`, `source_meanings`, `measurement_keys`, `input_origins`, `conditions`, `formula`, `meaning` | strings | see 3.4 | yes |

### 3.3 Proposed investigation finding for one aggregation sheet

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `across_experiment_aggregate` | | core |
| R1 | `sheet_ref` | the saved sheet's id | record ref | source record of provider `literature.a105.aggregation` | | core |
| R2 | `assertion_ref` | `sheet.assertion_ref` | record ref | hypothesis record | | core |
| R3 | `comparison_ref` | `sheet.comparison_ref` | record ref or null | hypothesis record | | optional |
| X1 | `selected_assay_count` | `len(sheet.experiment_refs)` | integer | >= 0 | count | core |
| X2 | `overall_value` | `cells.overall.value` | number or null | finite, signed | sum of natural-log evidence ratios when X6 is true; otherwise as `overall_unit` | core |
| X3 | `overall_available_value` | `cells.overall.available_value` | number or null | finite, signed | same | core |
| X4 | `overall_status` | `cells.overall.status` | vocabulary | `complete`, `partial`, `unavailable` | | core |
| X5 | `overall_available_assay_count` | `len(cells.overall.available_experiment_refs)` | integer | 0 to `selected_assay_count` | count | core |
| X6 | `overall_is_log_evidence_ratio` | `cells.overall.source_component_names == ['source_log_evidence_ratio']` and `cells.overall.unit == 'dimensionless'` (the test `annotation_scalar` already applies) | boolean | true/false | | core |
| X7 | `overall_unit` | `cells.overall.unit` | vocabulary | the unit list of line U in 2.8, plus `dimensionless`, `mixed_native_units`, `unknown` | | optional |
| Y1-Y4 | `reliability_value`, `validity_value`, `relevance_value`, `attribution_value` | `cells.<metric>.value` | number or null | finite | the metric cell's unit | optional |
| Y5-Y8 | `reliability_status`, `validity_status`, `relevance_status`, `attribution_status` | `cells.<metric>.status` | vocabulary | `complete`, `partial`, `unavailable` | | optional |
| Y9-Y12 | `reliability_available_assay_count` and the same for the other three metrics | `len(cells.<metric>.available_experiment_refs)` | integer | 0 to `selected_assay_count` | count | optional |
| Z1 | `comparison_binding` | `cells.overall.comparison_binding` | vocabulary | `parent_declared`, `not_declared` | | optional |
| Z2 | `aggregate_uses_synthetic_input` | `'synthetic' in cells.overall.input_origins` | boolean | true/false | | core |
| Z3 | `aggregate_uses_proposed_input` | `'proposed' in cells.overall.input_origins` | boolean | true/false | | core |

### 3.4 Aggregation fields left out because they are prose or open strings

| Sheet field | Why it is out | Controlled fields that carry what it meant |
|---|---|---|
| `meaning`, `source_meanings` | sentences | the metric name; `overall_is_log_evidence_ratio` |
| `formula` | fixed text `<reducer>(selected_<metric>_component_per_experiment)` | the metric name (the reducer is fixed per metric) |
| `conditions` | strings, including those inherited from grading rows | `overall_status`, `comparison_binding`, the `aggregate_uses_*` booleans |
| `missing_inputs[].reason` | code-written string per experiment | `<metric>_status` and `<metric>_available_assay_count` against `selected_assay_count` |
| `input_units`, `source_component_names` | string lists | `overall_unit`, `overall_is_log_evidence_ratio` |
| `selected_components` | whole grading rows | `sheet_ref` (they stay in the episode) |
| `measurement_keys`, `source_refs`, the three experiment-ref lists | identities and refs | the counts X1, X5, Y9-Y12; refs stay behind `sheet_ref` |
| `reducer`, `dimension`, `annotation_credit`, `version`, `axis`, `evaluation_scope` | fixed per metric or constant | nothing |

## 4. No applicable evidence (no sheet)

The one source-processing outcome that saves no sheet: `evidence_processing.kind == 'no_applicable_evidence'`.

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `no_applicable_evidence` | | core |
| K1 | `examined_span_count` | `len(evidence_processing.examined)` | integer | >= 1 | count | core |
| K2 | `examined_byte_count` | sum of `end - start` over `evidence_processing.examined` | integer | >= 1 | bytes | optional |
| K3 | `source_ref` | the assigned source | record ref | source record | | core |

Left out: `evidence_processing.reason` (a model-written sentence, `minLength 1`) and each witness `quote`. Nothing
controlled carries the reason; the outcome itself is the whole finding. Acquisition or processing failure is not
this outcome and produces no finding.

## 5. Reader families (operands, not graders)

These sheets are the grader's inputs. They carry no `evidence_type` and I propose no finding for them: what a reader
measured reaches the finding through the grading sheet's cells. The column "count and flag fields" lists what each
reader holds that the grading sheet does not, in case the owner wants a replicate count in the finding (point G2);
code would read it from `input_component_rows` of the grading record.

Coverage of this table: `rate`, `rate_source`, `quantity`, `assay`, `ratio` and `optical` schemas were read in full.
For the rest, component names come from `EFFECT_ROUTES` or the family's `COMPONENTS` line, and the number, integer and
boolean field names were pulled by pattern from the family's storage and inputs files, so their nesting and
"required" status were not confirmed. Selector offsets (`start`, `end`, `number_start`, `number_end`, `row_number`,
pixel sizes) are omitted: they locate text and are not evidence.

Fields shared by nearly every family, all required: `component` (enum), `value` (number or null), `unit` (enum per
family), `status` (enum, at least `populated`, `unavailable`), `origin` (enum from `reported`, `derived`,
`graph_derived`, `synthetic`, `proposed`), `unavailable_reason` (enum or null), `conditional_on` (array of enum),
`sheet_ref`, `evidence_source_ref`.

| Family (`x-source`) | Routes to `assay_type` | `component` values | Count and flag fields beyond the shared ones |
|---|---|---|---|
| `literature_rate_cells` | (none fixed) | `reference_rate`, `test_rate`, `rate_difference`, `retained_fraction`, `fractional_decrease`, `reference_mean_se`, `test_mean_se`, `difference_se`, `signed_profile_log_ratio`, `source_signed_index` | none |
| `literature_rate_source_cells` | (none fixed) | as above | `approximate` boolean; `threshold` number or null; `bound` enum `none`, `lt`, `le`, `gt`, `ge` |
| `literature_rate_source_domain_cells` | (none fixed) | as above | `lower`, `upper` number or null; `lower_inclusive`, `upper_inclusive` boolean |
| `literature_rate_source_meaning_cells` | (none fixed) | as above | `multiplier` number or null |
| `literature_rate_observation_cells`, `literature_rate_grid_cells` | (none fixed) | not expanded | `entry_count` integer or null, >= 0; `complete`, `conflicting`, `association_unresolved`, `value_is_formula_cache` boolean |
| `literature_rate_replicate_cells` | (none fixed) | `reference_rate`, `test_rate`, `rate_difference`, `retained_fraction`, `fractional_decrease`, `paired_sample_sd`, `difference_se`, `reference_sample_sd`, `test_sample_sd`, `reference_mean_se`, `test_mean_se` | `approximate`, `complete`, `conflicting_identity` boolean |
| `literature_quantity_cells` (not in `SOURCE_SCHEMAS`) | (none fixed) | `reported_value`, `reported_spread`, `relative_reported_spread`, `corrected_activity`, `effect_variance`, `effect_standard_uncertainty`, `effect_precision`, `source_profile_log_ratio`, `source_presence_index` | `reported_uncertainty_kind` enum `unspecified`, `unreported` |
| `literature_assay_cells` | (none fixed) | `net_rate`, `contaminant_rate`, `recovery`, `protein_amount`, `condition_test_rate`, `condition_reference_rate`, `attributed_rate`, `condition_response`, `corrected_activity`, `effect_variance`, `effect_standard_uncertainty`, `effect_precision`, `source_profile_log_ratio`, `source_presence_index` | enums `endpoint_kind`, `arrangement_kind`, `operand_source_kind`, `covariance_origin` (`reported`, `derived`, `synthetic`, null) |
| `literature_compiled_assay_cells`, `_v2_cells`, `_v3_cells` | (none fixed) | not expanded | `approximate` boolean or null; `threshold` number or null |
| `literature_controlled_response_component_cells` | (none fixed) | arithmetic components (not expanded), `local_difference`, `local_variance`, `local_standard_uncertainty` | none found |
| `literature_completion_time_cells` | `endpoint_conversion` (`completion_time`, `completion_time_ratio` only) | not expanded | `approximate`, `lower_inclusive`, `upper_inclusive` boolean |
| `literature_product_partition_cells` | `product_distribution` only | not expanded | `approximate`, `outside_reported_fraction_range` boolean; `threshold` number or null |
| `literature_product_coupling_cells` | (none fixed) | includes `productive_fraction`, `calculated_coupling_percent`, `displayed_coupling_difference_pp`, `productive_fraction_variance`, `productive_fraction_standard_uncertainty`, `product_per_cofactor_variance` | none found |
| `literature_endpoint_signal_cells` | (none fixed) | `total_amplitude`, `corrected_amplitude`, `additional_amplitude`, `retained_fraction`, `additional_fraction` and each with `_variance` | none found |
| `literature_concentration_window_cells` | (none fixed) | about 30, from `substrate_start` to variance components (not expanded) | `approximate`, `negative_observed_change`, `outside_physical_fraction_range` boolean; `conditional_value`, `threshold` number or null |
| `literature_parent_depletion_cells` | (none fixed) | not expanded | `time_hours` integer, >= 0 |
| `literature_stoichiometric_balance_cells` | (none fixed) | not expanded | `time_minutes` number, >= 0 |
| `literature_calibration_recovery_cells` | (none fixed; feeds role `recovery`) | includes `reported_measured_spread`, `measured_sd`, `measured_cv` | none found |
| `literature_measurement_validation_cells` | (none fixed) | not expanded | `native_value` number or null |
| `literature_measurement_comparison_cells` | (none fixed) | 26: `native_left`, `native_right`, `converted_left`, `converted_right`, `protocol_difference`, `protocol_ratio`, `protocol_log_ratio`, `common_difference`, `common_ratio`, `common_log_ratio`, `difference_variance`, `difference_standard_uncertainty`, `standardized_difference`, `squared_standardized_difference`, `weight_left`, `weight_right`, `combined_estimate`, `combined_variance`, `combined_standard_uncertainty`, `spectral_multiplier`, `spectral_multiplier_variance`, `observed_interference`, `corrected_estimate`, `corrected_estimate_variance`, `required_interference_scenario`, `required_nuisance_equivalent_scenario` | none found |
| `literature_kinetic_cells` | `activity_rate` (or `transport_response` for a Km) | `numerator_parameter`, `denominator_parameter`, `parameter_difference`, `parameter_ratio`, `log_parameter_contrast` | `count` integer or null, >= 1; `count_reported_value` integer or null; `count_approximate` boolean or null; `approximate` boolean; `confidence_level`, `threshold`, `magnitude` number |
| `literature_kinetic_model_cells` | `activity_rate` | not expanded | none found |
| `literature_kinetic_summary_precision_cells` | (none fixed) | 30: for each of `source_` and `scenario_`: `reported_parameter`, `reported_sd`, `source_summary_count`, `independent_preparation_count`, `statistical_estimator_count`, `relative_reported_sd`, `mean_variance`, `mean_standard_error`, `relative_mean_standard_error`, `mean_interval_df`, `mean_interval_confidence_level`, `mean_interval_t_multiplier`, `mean_interval_halfwidth`, `mean_interval_lower`, `mean_interval_upper` | the counts are components here (their `value`) |
| `literature_binding_cells` | `ligand_binding` | `reference_parameter`, `test_parameter`, `native_parameter_ratio`, `log_native_parameter_ratio` | `minimum_experiment_count` integer or null, >= 1 |
| `literature_binding_model_cells` | `ligand_binding` | `log_parameter_contrast`, `log_contrast_noise_variance`, `log_contrast_noise_sd`, `source_profile_log_ratio`, `source_signed_index` | `minimum_experiment_count` integer or null, >= 1 |
| `literature_binding_interaction_cells` | `ligand_binding` | `parameter_rr`, `parameter_rt`, `parameter_tr`, `parameter_tt`, `reference_subject_ratio`, `test_subject_ratio`, `interaction_ratio`, `log_interaction` | `exact_count`, `minimum_count` integer; `approximate`, `percent` boolean; `confidence_level`, `reported_spread`, `threshold` number |
| `literature_binding_interaction_model_cells` | `ligand_binding` | not expanded | none found |
| `literature_transport_cells` | `transport_response` | `apparent_km`, `test_saturation`, `reference_saturation`, `condition_response`, `log_condition_response` | none found |
| `literature_channel_cells` | `transport_response` | `current`, `reported_conductance`, `chord_conductance`, `charge_equivalent_rate` | `native_value` number |
| `literature_ion_discrimination_cells` | `transport_response` | `preferred_activity`, `alternative_activity`, `activity_ratio`, `log_activity_ratio`, `reported_selectivity` | `compiled_stage_verified` boolean; `lower_unbounded`, `upper_unbounded` boolean |
| `literature_ratio_cells` | `protein_signal` | `reported_ratio`, `difference_from_reference`, `log_reported_ratio` | `independent_preparation_count` integer or null, >= 0; `raw_representation_roster_complete` boolean; `value_candidates` array of number; `status` adds `conflicting`; enums `signal_kind`, `reference_role`, `arrangement`, `uncertainty_kind` (`unreported`) |
| `literature_ratio_source_cells` | `protein_signal` | `reported_ratio`, `difference_from_reference`, `log_reported_ratio`, `calibrated_amount_ratio`, `amount_adjusted_effect`, `source_profile_log_ratio`, `source_signed_index` | `lower`, `upper` number or null; `lower_closed`, `upper_closed`, `lower_infinite`, `upper_infinite`, `known_source_conflict`, `point_candidate_set_complete`, `selected_roster_resolved` boolean |
| `literature_gel_component_cells` | `protein_signal` (or `ligand_binding` for display fractions) | `pixel_count`, `sum_gray`, `sum_darkness`, `minimum_gray`, `maximum_gray`, `zero_gray_count`, `background_corrected_band_darkness`, `shifted_display_darkness`, `free_display_darkness`, `selected_total_display_darkness`, `shifted_display_fraction`, `off_band_display_fraction`, `display_black_pixel_fraction`, `display_total_ratio_to_protein_lane`, `protein_associated_display_shift`, `competitor_residual_display_fraction`, `displaced_display_fraction`, `factorized_competitor_sensitive_shift`, `direct_competitor_sensitive_shift` | `baseline_reused_in_factorized_form` boolean |
| `literature_amount_cells` | `protein_amount` | `numerator_amount`, `denominator_amount`, `amount_difference`, `amount_ratio`, `reciprocal_amount_ratio` | `approximate` boolean; `threshold` number or null |
| `literature_active_site_cells` | `protein_amount` | `protein_mass_concentration`, `total_monomer_concentration`, `active_site_concentration`, `sites_per_total_monomer`, `conditional_active_monomer_fraction`, `reported_active_fraction` | `approximate`, `lower_inclusive`, `upper_inclusive` boolean |
| `literature_optical_cells` | `activity_rate` | `net_rate`, `variance_net_rate` | `covariance.status` enum `known`, `estimated`, `unknown`; per operand `approximate` boolean or null, `observed_relation` enum `point`, `lt`, `le`, `gt`, `ge`, `observation_status` enum `observed`, `censored`, `unavailable`, `unreported`, `input_status` enum `available`, `unavailable`, `context_only` |
| `literature_partner_cells` (schema outside the named folders) | `activity_rate` | `reference_rate`, `omitted_rate`, `addback_rate`, `partner_loss`, `addback_gain`, `partner_loss_fraction`, `addback_fraction`, `restored_reference_fraction` | not read |
| `literature_figure_cells` (not in `SOURCE_SCHEMAS`) | (none fixed) | `first_ordinate`, `second_ordinate`, `ordinate_difference` | `independent_preparation_count` integer or null, >= 1; `reported_n` integer or null, >= 1 |
| perturbation and perturbation-summary cells (storage files present in the A105 folder; not in `SOURCE_SCHEMAS`) | (none fixed) | not expanded | `orientation` integer `-1`, `1` or null; `n` integer or null, >= 1; `lower`, `upper`, `lower_error_cap`, `upper_error_cap` number or null; `reported_coverage` number, strictly between 0 and 1 |

Reader fields that are prose or open strings and would stay out of any finding: witness `quote`, `formula` and
`meaning` texts, `qualifications`, `limitations`, `source_qualifications`, and the free `reason` strings. What they
meant reaches the grading sheet only as the cell `status` and the operand `origin`, which lines E2, E6, V2 and S2 of
table 2.7 carry.

## 6. Annotation fields

No A105 sheet carries a gene, function or product name or ID. The asserted function is present only as
`assertion_ref`, a reference to a hypothesis record, and the experiment as `experiment_ref`, a reference to an assay
reference record. Both are record references, not annotation fields, and the proposal keeps them as such (lines R2
and R3 of table 2.7).

If the owner wants an annotation field in the finding, it would be this one line:

| Finding field | Read from | Type | Meaning (source list; not looked up or verified by code) | Keep |
|---|---|---|---|---|
| `asserted_function` | the hypothesis record that `assertion_ref` names | annotation (ID or name) | the function the assessment was graded against, as named in the list the hypothesis record took it from | owner to decide |

The hypothesis record's schema is outside the folders I read, so which of its fields holds the function ID or name,
and which list that name comes from, are not stated here.
