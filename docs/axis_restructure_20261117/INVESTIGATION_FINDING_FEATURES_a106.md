# Investigation finding features: A106 (perturbation_evidence)

19 November 2026. Proposal for the owner to correct line by line. No code was changed and nothing was run.

An investigation finding is evidence for an annotation: its type and its strength, as a set of fields that code
reads from the grading (subscoring) sheet. Every proposed field below has one feature and a controlled answer
set that code can validate: a number with a range and unit, an integer count, a boolean, a value of a fixed
vocabulary, or a record reference. There is no open text field. Prose in a sheet is left out (item 4 of each
block) with the controlled fields that carry what it meant.

## 0. What was read

Library, under `gene_annotation_episode/episodic_workflow/episode_support/literature/`:

- `readers/literature_subscore.py`, `storage/literature_subscore_storage.py` (the A106 final subscore).
- `storage/perturbation_evidence/*_storage.py`, `inputs/perturbation_evidence/*_inputs.py`,
  `forms/perturbation_evidence/*`, `readers/perturbation_evidence/*` (the cell schemas of every sheet family).
- Read by known path because the files above import their schemas from them (no search was run there):
  `storage/literature_intervention_storage.py`, `inputs/literature_intervention_inputs.py`,
  `grading/literature_intervention_grading.py`, `grading/perturbation_evidence/literature_assay_grading.py`,
  `grading/perturbation_evidence/literature_perturbation_assessments.py`,
  `grading/perturbation_evidence/literature_perturbation_summary.py`, `storage/literature_repositories.py`, and the
  `COMPONENTS` / vocabulary constants of the matching `calculations/perturbation_evidence/*_calculations.py`.

Episodes, under `root/a106/perturbation_evidence/`: only one episode writes sheets,
`published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/task.py`.
It offers 36 population tools (`literature.*.populate` and `literature.a106.finalize`), routed by
`POPULATION_OWNERS` in `storage/literature_repositories.py`. Eleven of them are optional and off by default
(`literature_populations` setting): `ratio_source`, `controlled_response`, `gel`, `completion_time`,
`product_partition`, `active_site`, `parent_depletion`, `stoichiometric_balance`, `compiled_assay`, `channel`,
`ion_discrimination`. No other A106 episode (`passage_evidence_extraction`, `table_evidence_extraction`, the
parents) writes a sheet.

Facts the owner should know before reading the tables:

- A106 has two graders: the intervention grading sheet (G1, one per experiment) and the A106 final subscore
  (G2, across experiments). Every other sheet is an operand sheet: it holds measured numbers, and it is graded
  against an annotation only when G1 selects its cells as operands.
- Many providers in the A106 folder are named `literature.a105.*`. The names were not changed here.
- `storage/perturbation_evidence/literature_assay_grading_storage.py` (provider `literature.a105.assay_grading`)
  and `literature_aggregation_storage.py` (provider `literature.a105.aggregation`) are in the A106 folder, but no
  A106 tool reaches them. They are listed in section 3 (G3, G4) without a proposed finding.
- No A106 sheet has a typed gene, function or product name field, with one exception (the constant
  `assayed_molecule` of the stoichiometric balance sheet, B24). The annotation is carried by record reference:
  `assertion_ref` (the proposed-annotation hypothesis record), `comparison_ref` (the alternative hypothesis
  record) and `subject_ref` (the molecule record).

## 1. Proposed `evidence_type` vocabulary for A106

One field, eleven values. Values 3 to 10 are the owner's own `ASSAY_TYPES` of the assay grader; value 1 is the
`assay_type` constant of the intervention grader.

| # | value | meaning | sheets that take it |
|---|---|---|---|
| 1 | `intervention_response` | one experiment that changes the molecule and measures the outcome | G1, B1, B2, B3 |
| 2 | `intervention_response_combined` | the A106 result over several intervention experiments | G2 |
| 3 | `activity_rate` | rate, kinetic parameter or rate contrast | B4 to B16 |
| 4 | `endpoint_conversion` | reaction progress, endpoint amount or completion time | B17 to B21 |
| 5 | `product_distribution` | fractions of products | B22 |
| 6 | `reaction_coupling` | coupling and stoichiometric balance | B23, B24 |
| 7 | `ligand_binding` | binding parameter, binding contrast, band shift | B25 to B29 |
| 8 | `transport_response` | transport response, current, ion discrimination | B30 to B32 |
| 9 | `protein_signal` | reported relative protein or transcript signal | B33, B34 |
| 10 | `protein_amount` | protein amount and active-site amount | B35, B36 |
| 11 | `measurement_validity` | calibration recovery and assay precision; supports a measurement, not an annotation | B37, B38 |

## 2. Reading conventions used in every table

- `cell(X)` is the row of the sheet whose `component` equals `X`. `cell(X).value` is its `value`.
- A numeric feature is null when its cell is unavailable. "finite or null" means: a finite float, or null.
- "required" follows the schema: `obj(...)` makes every listed property required unless a `required` list says
  otherwise. Exceptions are stated.
- Two fields are proposed for every finding and not repeated in the tables:

| field | read from | type | validator |
|---|---|---|---|
| `evidence_type` | fixed per sheet family (section 1) | enum | the 11 values of section 1 |
| `sheet_ref` | the sheet's `sheet_ref` | record ref | a `source` record the episode holds |

- One more field is proposed for every operand sheet (B1 to B38), to strike once if unwanted:

| field | read from | type | validator |
|---|---|---|---|
| `cells_populated_count` | count of rows whose `status` is the family's populated value (`populated`, `point`, `measured`, `calculated` or `available`) | integer | 0 to the number of components of the family |

## 3. Graders

### G1. Intervention grading sheet

1. `literature_intervention_grading_cells`, provider `literature.a106.intervention_grading`, tool
   `literature.intervention_grading.populate`, sheet version `a106_intervention_grading_sheet_v1`. Grades one
   intervention experiment against the proposed annotation and one named alternative: effect, variance and a
   signed log evidence ratio.

2. Fields (`intervention_cells_schema`; all required except `bound`):

| field | type | values |
|---|---|---|
| `component` | enum | `measured_effect`, `effect_variance`, `effect_precision`, `recovery_deviation`, `attributed_fraction`, `condition_response`, `assertion_prediction_error`, `alternative_prediction_error`, `source_log_evidence_ratio` |
| `dimension` | enum | `measurement`, `reliability`, `validity`, `attribution`, `comparability`, `relevance`, `experimental_evidence` |
| `value` | number or null | |
| `status` | enum | `populated`, `conditional`, `bounded`, `unavailable` |
| `bound.relation` (optional) | enum | `lt`, `le`, `gt`, `ge`, `interval` |
| `bound.lower`, `bound.upper` (optional) | number or null | |
| `input_origins` | array of enum | `reported`, `derived`, `graph_derived`, `synthetic`, `proposed` |
| `assay_type` | const | `intervention_response` |
| `quantity_kind` | enum | `native_endpoint`, `endpoint_difference`, `endpoint_ratio`, `log2_fold_change`, `fitness_difference` |
| `interpretations.<criterion>.status` (each criterion optional) | enum | `supported`, `unknown`, `conflicting`; criteria: `measurement_identity`, `calibration_applicability`, `matrix_interference`, `background_alternatives`, `attribution_supported`, `assertion_relevance`, `condition_scope`, `variance_correspondence`, `sampling_basis`, `intervention_identity`, `subject_correspondence`, `contrast_definition`, `prediction_independence` |
| `prediction_model` | object or null | |
| `prediction_model.kind` | enum | `fixed_predictions_known_normal`, `fixed_predictions_estimated_normal`, `fixed_predictions_student_t` |
| `prediction_model.variance_interpretation` | enum | `known`, `estimated`, `unknown` |
| `experiment_assessment.experiment_type` | enum | `intervention_response` |
| `sample_bindings[].arm` | enum | `reference`, `intervention`, `restoration`, `other`, `unknown` |
| `evaluation_scope` | const | `intervention_experimental_evidence` |
| `annotation_credit` | null | |
| references | record ref | `sheet_ref`, `evidence_source_ref`, `experiment_ref`, `assertion_ref`, `comparison_ref`, `experiment_assessment.revises_sheet_ref` (or null), `source_refs`, `interpretations.*.support_refs`, `sample_bindings[].file_refs` |
| open strings (see item 4) | string | `unit`, `reasons[]`, `conditions[]`, `formula`, `meaning`, `measurement_keys[]`, `evidence_measurement_keys[]`, `experiment_assessment.{assessment_key, scientific_question, conclusion, limitations[], revision_reason}`, `experimental_design.<14 fields>` (witness with `quote`), `sample_bindings[].sample_id` and its witnesses |

3. Proposed finding. `evidence_type` = `intervention_response`.

| field | read from | type, unit | validator |
|---|---|---|---|
| `experiment_ref` | `experiment_ref` | record ref | a `reference` record of type assay |
| `assertion_ref` | `assertion_ref` | record ref (the proposed annotation; meaning: the hypothesis record list of the run) | a `hypothesis` record |
| `comparison_ref` | `comparison_ref` | record ref (the alternative) | a `hypothesis` record, different from `assertion_ref` |
| `quantity_kind` | `quantity_kind` | enum | the 5 values above |
| `log_evidence_ratio` | `cell(source_log_evidence_ratio).value` | number, natural log ratio (positive supports the annotation over the alternative) | finite or null |
| `log_evidence_ratio_status` | `cell(source_log_evidence_ratio).status` | enum | `conditional`, `unavailable` (the grader writes only these two for this cell; a censored effect still gives `conditional`) |
| `measured_effect` | `cell(measured_effect).value` | number, on the scale named by `quantity_kind` (signal) | finite or null |
| `effect_is_censored` | `cell(measured_effect).status == 'bounded'` | boolean | true or false |
| `effect_variance` | `cell(effect_variance).value` | number, square of the effect scale (noise) | finite, 0 or more, or null |
| `effect_over_noise` | code computes `cell(measured_effect).value / sqrt(cell(effect_variance).value)` | number, dimensionless | finite or null; null when either cell is unavailable or the variance is 0. This is an aggregate of two cells: strike it if only direct cells are wanted. |
| `assertion_prediction_error` | `cell(assertion_prediction_error).value` | number, effect scale | finite or null |
| `alternative_prediction_error` | `cell(alternative_prediction_error).value` | number, effect scale | finite or null |
| `recovery_deviation` | `cell(recovery_deviation).value` | number, dimensionless (recovery minus 1) | finite, greater than -1, or null |
| `attributed_fraction` | `cell(attributed_fraction).value` | number, fraction (not clamped by the grader) | finite or null |
| `condition_response` | `cell(condition_response).value` | number, dimensionless ratio | finite, 0 or more, or null |
| `prediction_model_kind` | `prediction_model.kind` | enum | the 3 kinds, or null when no model was selected |
| `variance_interpretation` | `prediction_model.variance_interpretation` | enum | `known`, `estimated`, `unknown`, or null when no model |
| `criterion_<name>` (13 fields, one per criterion named in item 2) | `interpretations.<name>.status`; `not_selected` when the criterion is absent | enum | `supported`, `unknown`, `conflicting`, `not_selected` (`not_selected` is the grader's own word for an absent criterion: `<name>_not_selected` in `reasons`) |
| `unresolved_reason_count` | code counts `cell(source_log_evidence_ratio).reasons` | integer | 0 or more |
| `prediction_reuses_observed_measurement` | the exact code `prediction_reuses_observed_measurement` is in `cell(source_log_evidence_ratio).reasons` | boolean | true or false |
| `uses_proposed_operand` | `'proposed'` in `cell(source_log_evidence_ratio).input_origins` | boolean | true or false |
| `uses_synthetic_operand` | `'synthetic'` in the same list | boolean | true or false |
| `uses_graph_derived_operand` | `'graph_derived'` in the same list | boolean | true or false |
| `observed_measurement_count` | code counts `evidence_measurement_keys` | integer | 0 or more |
| `reference_sample_count` | code counts `sample_bindings` rows with `arm == 'reference'` | integer | 0 or more |
| `intervention_sample_count` | same, `arm == 'intervention'` | integer | 0 or more |
| `restoration_sample_count` | same, `arm == 'restoration'` | integer | 0 or more |
| `biological_unit_witnessed_count` | code counts `sample_bindings` rows whose `biological_unit` is not null | integer | 0 or more |
| `design_fields_witnessed_count` | code counts the non-null fields of `experimental_design` | integer | 0 to 14 |
| `restoration_arm_witnessed` | `experimental_design.restoration_arm` is not null | boolean | true or false |
| `replication_witnessed` | `experimental_design.replication` is not null | boolean | true or false |
| `shared_controls_witnessed` | `experimental_design.shared_controls` is not null | boolean | true or false |
| `is_revision` | `experiment_assessment.revises_sheet_ref` is not null | boolean | true or false |

4. Left out as prose or open text, and what carries their meaning:

| sheet field | why left out | carried by |
|---|---|---|
| `unit` of each cell | declared `{'type': 'string'}`, not a closed list | `quantity_kind`. To pass the unit itself, the owner would have to close its vocabulary in the grader. |
| `reasons[]`, `conditions[]` | code strings, but they can embed the operand's own free `reason` and source qualification text | `log_evidence_ratio_status`, `unresolved_reason_count`, the 13 `criterion_*` fields, `prediction_reuses_observed_measurement` |
| `formula`, `meaning` | fixed sentences per component; they say nothing about this experiment | the field name |
| `experiment_assessment.scientific_question`, `.conclusion`, `.limitations[]`, `.revision_reason` | model-written prose | `log_evidence_ratio`, the `criterion_*` fields, `is_revision` |
| `experiment_assessment.assessment_key` | model-chosen label | `experiment_ref` and `sheet_ref` |
| `experimental_design.<field>` (each a witness: source ref, offsets, `quote`) | source quotation | `design_fields_witnessed_count` and the three `*_witnessed` booleans; the witness stays in the sheet |
| `sample_bindings[].sample_id` and its witnesses | source labels and quotations | the three sample counts and `biological_unit_witnessed_count` |
| `measurement_keys[]`, `evidence_measurement_keys[]` | internal identity strings | `observed_measurement_count` |

Not in a delivered cell, but in the saved sheet record (`extraction.quantities`, `selection`): the
`effect_degrees_of_freedom` operand and the selected analysis metric of a TRANSIT or DESeq2 row
(`reference_mean`, `intervention_mean`, `log2_fold_change`, `mean_difference`, `base_mean`, `standard_error`,
`effect_variance`, `p_value`, `adjusted_p_value`). If the owner wants degrees of freedom or a p-value in the
finding, they would be read from there; they are not proposed above.

### G2. A106 final subscore

1. `literature_a106_subscore_cells`, provider `literature.a106.subscore`, tool `literature.a106.finalize`, version
   `a106_experimental_subscore_v1`. Combines the current G1 assessment of each original experiment into one
   signed log evidence ratio for one question (subject, annotation, alternative, scope).

2. Fields (`cell_schema`; all required):

| field | type | values |
|---|---|---|
| `component` | enum | `experimental_subscore` |
| `axis` | const | `A106` |
| `evaluation_scope` | const | `a106_intervention_experimental_evidence` |
| `score_meaning` | const | `conditional_signed_log_evidence_ratio` |
| `value` | number or null | null unless there are no unavailable reasons |
| `available_value` | number or null | the supported subtotal |
| `status` | enum | `complete`, `partial`, `unavailable` |
| `unit` | const | `natural_log_ratio` |
| `dependence.status` | enum | `independent`, `shared`, `unknown` |
| `annotation_credit` | null | |
| `selected_components` | array of G1 rows | the `source_log_evidence_ratio` row of each selected sheet |
| references | record ref | `subject_ref`, `assertion_ref`, `comparison_ref`, `experiments[].experiment_ref`, `experiments[].sheet_ref` (or null), `revises_subscore_ref` (or null), `source_refs`, `sheet_ref` (in `cells_schema`) |
| open strings (see item 4) | string | `scope_statement`, `conclusion`, `limitations[]`, `revision_reason`, `dependence.rationale`, `dependence.witnesses[].quote`, `experiments[].missing_reason`, `unavailable_reasons[]`, `conditions[]`, `evidence_measurement_keys[]`, `input_origins[]` |

3. Proposed finding. `evidence_type` = `intervention_response_combined`.

| field | read from | type, unit | validator |
|---|---|---|---|
| `subject_ref` | `subject_ref` | record ref (the molecule) | a record the episode holds |
| `assertion_ref` | `assertion_ref` | record ref (the proposed annotation) | a `hypothesis` record |
| `comparison_ref` | `comparison_ref` | record ref (the alternative) | a `hypothesis` record, different from `assertion_ref` |
| `log_evidence_ratio` | `value` | number, natural log ratio | finite or null; null unless `status` is `complete` |
| `available_log_evidence_ratio` | `available_value` | number, natural log ratio | finite or null |
| `status` | `status` | enum | `complete`, `partial`, `unavailable` |
| `experiment_count` | code counts `experiments` | integer | 0 or more |
| `scored_experiment_count` | code counts `selected_components` rows with a non-null `value` and `status` in `populated`, `conditional` | integer | 0 to `experiment_count` |
| `missing_assessment_count` | code counts `experiments` rows whose `sheet_ref` is null | integer | 0 to `experiment_count` |
| `supporting_experiment_count` | code counts `selected_components` rows with `value` above 0 | integer | 0 to `scored_experiment_count` |
| `opposing_experiment_count` | code counts `selected_components` rows with `value` below 0 | integer | 0 to `scored_experiment_count` |
| `dependence_status` | `dependence.status` | enum | `independent`, `shared`, `unknown` |
| `dependence_witness_count` | code counts `dependence.witnesses` | integer | 0 or more |
| `shared_observed_measurement` | the exact code `shared_observed_measurement` is in `unavailable_reasons` | boolean | true or false |
| `independence_unresolved` | the exact code `between_experiment_independence_unresolved` is in `unavailable_reasons` | boolean | true or false |
| `observed_measurement_count` | code counts `evidence_measurement_keys` | integer | 0 or more |
| `is_revision` | `revises_subscore_ref` is not null | boolean | true or false |

4. Left out as prose or open text:

| sheet field | why left out | carried by |
|---|---|---|
| `scope_statement` | model-written biological scope | `subject_ref`, `assertion_ref`, `comparison_ref` |
| `conclusion`, `limitations[]` | model-written prose | `log_evidence_ratio`, `status`, the counts |
| `dependence.rationale`, `dependence.witnesses[].quote` | model prose and source quotations | `dependence_status`, `dependence_witness_count` |
| `experiments[].missing_reason` | model-written explanation | `missing_assessment_count` |
| `revision_reason` | model-written | `is_revision` |
| `unavailable_reasons[]` | codes, some with an embedded record id (`experiment_score_missing:<ref>`) | `status`, the two booleans, `missing_assessment_count` |
| `conditions[]`, `input_origins[]`, `evidence_measurement_keys[]` | open string arrays in the schema | `scored_experiment_count`, `observed_measurement_count` |

The existing `annotation_scalar` (`tanh(value/2)`) is computed from `value` alone; it is not proposed as a
separate field.

### G3. Assay grading sheet (in the A106 folder, not reachable from an A106 episode)

1. `literature_assay_grading_cells`, provider `literature.a105.assay_grading`, sheet axis constant `A105`. Grades
   one assay measurement against an assertion. It is the cell schema G1 is built on.
2. Fields as G1 item 2, with these differences: `assay_type` is an enum (`activity_rate`, `endpoint_conversion`,
   `product_distribution`, `reaction_coupling`, `ligand_binding`, `transport_response`, `protein_signal`,
   `protein_amount`); `quantity_kind` is the per-type list `QUANTITY_KINDS`; criteria are `CRITERIA_BY_TYPE`
   (9 common plus 3 to 5 per type) and a criterion status may also be `not_applicable`; no `comparison_ref`,
   `experimental_design`, `experiment_assessment` or `sample_bindings`; `experiment_ref` is optional.
3. No finding is proposed: `POPULATION_OWNERS` has no tool for it and no A106 episode writes it. If the owner
   wants it offered in A106, the G1 table applies with `evidence_type` = the sheet's own `assay_type`.
4. Prose: as G1 (`unit`, `reasons`, `conditions`, `formula`, `meaning`).

### G4. Across-experiment aggregation sheet (in the A106 folder, not reachable from an A106 episode)

1. `literature_a105_aggregation_cells`, provider `literature.a105.aggregation`, version
   `a105_across_experiment_aggregation_v1`. Reduces G3 cells over experiments.
2. Fields: `component` enum (`reliability`, `validity`, `relevance`, `attribution`, `overall`); `dimension` enum
   (`reliability`, `validity`, `relevance`, `attribution`, `experimental_evidence`); `reducer` enum (`sum`, `max`);
   `value`, `available_value` number or null; `status` enum (`complete`, `partial`, `unavailable`);
   `comparison_binding` enum (`parent_declared`, `not_declared`); reference arrays `selected_experiment_refs`,
   `available_experiment_refs`, `missing_experiment_refs`. All required.
3. No finding is proposed (not reachable from A106).
4. Prose or open strings: `unit`, `input_units`, `source_component_names`, `source_meanings`, `formula`,
   `meaning`, `missing_inputs[].reason`, `conditions`, `input_origins`.

## 4. Operand sheets

Shared core. Unless a block says otherwise, every operand row has these required fields: `component` (enum, the
family's components), `value` (number or null), `unit` (enum, closed list), `status` (enum), `origin` (enum),
`unavailable_reason` (enum or null), `conditional_on` (array of enum), `sheet_ref` and `evidence_source_ref`
(record refs). Each block lists the components and the fields beyond this core. Long vocabularies are named by
their constant and file instead of being copied.

Where a proposed numeric feature has a unit that varies with the row, the unit is passed as its own field
`<feature>_unit` with the sheet's closed unit list as validator; this is said once here and not repeated.

### Intervention sheets (`evidence_type` = `intervention_response`)

#### B1. Perturbation point sheet

1. `literature_perturbation_cells`, provider `literature.experimental.perturbation`, tool
   `literature.perturbation.populate`. Reference, perturbed and restored outcomes of one experiment and a source
   restoration index.
2. Components (14): `reference_endpoint`, `perturbed_endpoint`, `restored_endpoint`, `perturbation_difference`,
   `symmetric_effect`, `restoration_fraction_raw`, `restoration_agreement`, `amount_comparability`,
   `perturbation_isolation`, `restoration_isolation`, `effect_isolation`, `reference_restoration_index`,
   `reference_index_lower`, `reference_index_upper`. Beyond the core, all required:

| field | type | values |
|---|---|---|
| `orientation` | integer or null | -1, 1 |
| `design` | enum | `native_deletion_restoration`, `selective_perturbation_restoration`, `cas_free_reconstitution`, `variant_replacement`, `other_explicit`, `unknown`, `conflicting` |
| `measurement_status` | enum | `validated_ratio_scale`, `qualitative_only`, `unknown`, `conflicting` |
| `same_endpoint_scope` | enum | `yes`, `no`, `unknown`, `conflicting` |
| `amount_role` | enum | `nuisance`, `intended_change`, `unknown` |
| `data_origin` | enum or null | `reported`, `graph_derived`, `synthetic` |
| `operand_source_kind` | enum | `primary_source`, `retained_extraction`, `graph_extraction`, `synthetic_fixture` |
| `uncertainty_basis` | enum | `unreported` |
| `endpoint_unit` | enum | `unreported`, `events_per_100000_cells`, `fraction`, `CFU_per_mL`, `CFU_per_initial_OD_per_mL`, `minutes`, `per_min`, `per_h` |
| `exposure_unit` | enum | `unreported`, `molecules_per_cell`, `normalized_signal`, `fraction`, `mg_per_mL` |
| `formula_code`, `index_kind`, `evaluated_scope` | enum | fixed per component or constant |
| `status` | enum | `populated`, `unavailable` |
| `unavailable_reason` | enum or null | `REASONS` (18) of `calculations/perturbation_evidence/literature_perturbation_calculations.py` |
| `conditional_on` | array of enum | `CONDITIONAL_CODES` (8) of the same file |
| references (each or null) | record ref | `data_source_ref`, `assayed_subject_ref`, `recipient_ref`, `donor_ref`, `experiment_ref`, `reference_arm_ref`, `perturbed_arm_ref`, `restored_arm_ref`, `partner_ref`, `endpoint_ref`, `normalization_ref`, `condition_ref`, `intended_change_ref` |

3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `experiment_ref` | `experiment_ref` | record ref | a `reference` record, or null |
| `assayed_subject_ref` | `assayed_subject_ref` | record ref (the molecule) | a `reference` record, or null |
| `intervention_design` | `design` | enum | the 7 values above |
| `measurement_status` | `measurement_status` | enum | the 4 values above |
| `same_endpoint_scope` | `same_endpoint_scope` | enum | the 4 values above |
| `amount_role` | `amount_role` | enum | the 3 values above |
| `orientation` | `orientation` | integer | -1, 1, or null |
| `perturbation_difference` | `cell(perturbation_difference).value` | number, row unit (signal) | finite or null |
| `symmetric_effect` | `cell(symmetric_effect).value` | number, row unit | finite or null |
| `restoration_fraction_raw` | `cell(restoration_fraction_raw).value` | number, row unit | finite or null |
| `restoration_agreement` | `cell(restoration_agreement).value` | number, row unit | finite or null |
| `amount_comparability` | `cell(amount_comparability).value` | number, row unit | finite or null |
| `effect_isolation` | `cell(effect_isolation).value` | number, row unit | finite or null |
| `reference_restoration_index` | `cell(reference_restoration_index).value` | number, row unit | finite or null |
| `reference_index_lower` | `cell(reference_index_lower).value` | number, row unit | finite or null |
| `reference_index_upper` | `cell(reference_index_upper).value` | number, row unit | finite or null |
| `operand_source_kind` | `operand_source_kind` | enum | the 4 values above |

   No noise feature: this sheet's `uncertainty_basis` is always `unreported`.
4. No prose field. The component `description` in the schema is schema documentation, not data.

#### B2. Perturbation summary sheet

1. `literature_perturbation_summary_cells`, record `literature_perturbation_record_v2` of the same tool as B1. The
   B1 components plus, per arm, the reported summary, spread and count, the mean variance of each contrast and
   the shared-control covariance.
2. Components (64): the 14 of B1; `<role>_<statistic>` for role in `W`, `K`, `R`, `A_reference`, `A_restored`,
   `B_pert`, `B_rest` and statistic in `summary_value`, `reported_spread`, `reported_count`, `sample_sd`,
   `mean_se`, `mean_variance`; and `perturbation_mean_variance`, `perturbation_variance_lower`,
   `perturbation_variance_upper`, `restoration_difference`, `restoration_mean_variance`,
   `restoration_variance_lower`, `restoration_variance_upper`, `shared_contrast_covariance`. All fields of B1
   (with `uncertainty_basis` = `per_measurement`), plus, all required:

| field | type | values |
|---|---|---|
| `lower`, `upper`, `lower_error_cap`, `upper_error_cap` | number or null | |
| `n` | integer or null | 1 or more |
| `reported_coverage` | number or null | above 0 and below 1 |
| `statistic_method` | enum | `METHODS` of `storage/perturbation_evidence/literature_perturbation_summary_storage.py` |
| `variance_status` | enum | `known`, `estimated`, `unknown` |
| `variance_scope` | enum | `technical_mean_within_studied_unit`, `biological_unit_mean`, `preparation_mean`, `other_unit_mean`, `source_reported_unresolved_scope`, `mixed_estimator_scopes`, `unavailable`, `not_applicable` |
| `bound_kind` | enum | `none`, `conditional_digitization_not_confidence_interval`, `reported_confidence_interval`, `reported_detection_limit`, `covariance_enclosure_not_confidence_interval` |
| `spread_reading` | enum | `not_applicable`, `unresolved`, `symmetric_compatible`, `asymmetric_readings`, `reported_interval` |
| `measurement_role` | enum or null | `W`, `K`, `R`, `A_reference`, `A_restored`, `B_pert`, `B_rest` |
| `summary_kind` | enum | `arithmetic_mean`, `geometric_mean`, `median`, `single_observation`, `unknown` |
| `value_scale`, `summary_scale`, `spread_scale`, `error_cap_scale` | enum | `endpoint`, `log10_endpoint`, `ln_endpoint`, `unknown` |
| `spread_kind` | enum | `sd`, `sem`, `confidence_interval`, `detection_limit`, `untyped_pm`, `unreported` |
| `count_unit` | enum | `culture`, `organism`, `preparation`, `biological_unit`, `technical_reading`, `other`, `unknown` |
| `independence` | enum | `independent`, `not_independent`, `unknown` |
| `statistical_interpretation_basis.<role>.<basis field>` | enum | `source_reported`, `source_supported_inference`, `conditional_assumption`, `unresolved` |
| `covariance_interpretations` | object | not read in detail |

3. Proposed finding: the B1 fields, plus:

| field | read from | type, unit | validator |
|---|---|---|---|
| `perturbation_mean_variance` | `cell(perturbation_mean_variance).value` | number, squared row unit (noise) | finite, 0 or more, or null |
| `perturbation_over_noise` | code computes `cell(perturbation_difference).value / sqrt(cell(perturbation_mean_variance).value)` | number, dimensionless | finite or null. Aggregate of two cells: strike if unwanted. |
| `restoration_difference` | `cell(restoration_difference).value` | number, row unit | finite or null |
| `restoration_mean_variance` | `cell(restoration_mean_variance).value` | number, squared row unit | finite, 0 or more, or null |
| `shared_contrast_covariance` | `cell(shared_contrast_covariance).value` | number, squared row unit | finite or null |
| `reference_n` | `n` of `cell(W_reported_count)` | integer | 1 or more, or null |
| `perturbed_n` | `n` of `cell(K_reported_count)` | integer | 1 or more, or null |
| `restored_n` | `n` of `cell(R_reported_count)` | integer | 1 or more, or null |
| `reference_count_unit` | `count_unit` of `cell(W_reported_count)` | enum | the 7 `count_unit` values |
| `reference_independence` | `independence` of `cell(W_reported_count)` | enum | `independent`, `not_independent`, `unknown` |
| `perturbation_variance_status` | `variance_status` of `cell(perturbation_mean_variance)` | enum | `known`, `estimated`, `unknown` |
| `perturbation_variance_scope` | `variance_scope` of `cell(perturbation_mean_variance)` | enum | the 8 `variance_scope` values |
| `reference_spread_kind` | `spread_kind` of `cell(W_reported_spread)` | enum | the 6 `spread_kind` values |

   The same `count_unit`, `independence` and `spread_kind` fields exist for the `K` and `R` arms; they are not
   listed, to keep the finding small. Add them if wanted.
4. No prose field.

#### B3. Perturbation operand view

1. `literature_perturbation_operand_cells` (`readers/perturbation_evidence/literature_perturbation_operands.py`).
   A read view that copies B1 or B2 cells in the operand form G1 accepts. No tool writes it.
2. Components (10): `reference_endpoint`, `perturbed_endpoint`, `restored_endpoint`, `perturbation_difference`,
   `restoration_difference` and `reference_mean_variance`, `perturbed_mean_variance`, `restored_mean_variance`,
   `perturbation_mean_variance`, `restoration_mean_variance`. Fields, all required: `row_version` (const),
   `quantity_kind` (enum `native_endpoint`, `endpoint_difference`), `variance_for` (enum or null, the five effect
   names), `cell.value` (number or null), `cell.status` (enum `point`, `bounded`, `unavailable`), `cell.origin`
   (enum, 5 origins), `source_cell` (a B1 or B2 row).
3. No separate finding: its numbers are the B1 and B2 numbers, and it reaches the parent through G1.
4. Open strings: `cell.unit`, `cell.reason`, `cell.native_component`, `cell.measurement_keys`.

### Activity and rate sheets (`evidence_type` = `activity_rate`)

#### B4. Rate contrast sheet

1. `literature_rate_cells`, provider `literature.a105.rate_population`, tool `literature.rate.populate`. Reference
   and test rates and their contrast.
2. Components (10): `reference_rate`, `test_rate`, `rate_difference`, `retained_fraction`, `fractional_decrease`,
   `reference_mean_se`, `test_mean_se`, `difference_se`, `signed_profile_log_ratio`, `source_signed_index`. Core
   fields only: `unit` enum or null (`RATE_UNITS` of
   `forms/perturbation_evidence/literature_experimental_contracts.py`, `fraction`, `dimensionless`); `status`
   (`populated`, `unavailable`); `origin` (5 origins); `unavailable_reason` (`UNAVAILABLE_REASONS`, 18);
   `conditional_on` (`independent_normal_groups`, `independent_groups`). References, each or null:
   `assayed_subject_ref`, `experiment_ref`, `reference_condition_ref`, `test_condition_ref`, `endpoint_ref`,
   `normalization_ref`. All required.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `experiment_ref` | `experiment_ref` | record ref | a `reference` record, or null |
| `rate_difference` | `cell(rate_difference).value` | number, rate unit (signal) | finite or null |
| `difference_se` | `cell(difference_se).value` | number, rate unit (noise) | finite, 0 or more, or null |
| `retained_fraction` | `cell(retained_fraction).value` | number, fraction | finite or null |
| `signed_profile_log_ratio` | `cell(signed_profile_log_ratio).value` | number, natural log ratio | finite or null |
| `source_signed_index` | `cell(source_signed_index).value` | number, dimensionless | -1 to 1, or null (range assumed from the tanh form used by the other sheets; confirm) |
| `groups_assumed_independent` | `'independent_groups'` or `'independent_normal_groups'` is in `conditional_on` of `cell(difference_se)` | boolean | true or false |

4. No prose field.

#### B5. Native rate sheet and its two views

1. `literature_rate_source_cells`, tool `literature.rate.source.populate` (record
   `literature_rate_population_record_v2`). The B4 components read from the source in native units, with bounds.
   Views of the same rows: `literature_rate_source_domain_cells` (adds the reported domain) and
   `literature_rate_source_meaning_cells` (adds source witnesses of the rate's meaning).
2. B4 fields, plus, all required: `approximate` (boolean); `threshold` (number or null); `bound` (enum `none`,
   `lt`, `le`, `gt`, `ge`); six more references (`<reference|test>_<subject|construct|preparation>_ref`, each or
   null); `unavailable_reason` also takes `NATIVE_REASONS` (10). Domain view: `reported_domain.kind` (enum `point`,
   `lower_bounded`, `upper_bounded`, `finite_interval`, `unbounded`, `undefined`, `unavailable`,
   `numerical_range`), `.lower`, `.upper` (number or null), `.lower_inclusive`, `.upper_inclusive` (boolean),
   `.projection` (enum `exact`, `outward`, `none`), `.basis` (enum, 5), `.conditioning` (enum, 2), `.failure`
   (enum or null). Meaning view: `rate_meanings[].rate_unit.canonical_unit` (enum or null),
   `.multiplier` (number or null).
3. Proposed finding: the B4 fields, plus:

| field | read from | type, unit | validator |
|---|---|---|---|
| `rate_difference_bound` | `bound` of `cell(rate_difference)` | enum | `none`, `lt`, `le`, `gt`, `ge` |
| `rate_difference_approximate` | `approximate` of `cell(rate_difference)` | boolean | true or false |
| `rate_difference_lower` | `reported_domain.lower` of `cell(rate_difference)` (domain view) | number, rate unit | finite or null |
| `rate_difference_upper` | `reported_domain.upper` of the same row | number, rate unit | finite or null |

4. Left out: in the meaning view, `comparison_intended_change` and `rate_meanings[].endpoint`,
   `.normalization` (source witnesses with quotations) and `rate_unit.raw_unit` (source text). Carried by
   `endpoint_ref`, `normalization_ref`, `<feature>_unit`.

#### B6. Rate replicate sheet

1. `literature_rate_replicate_cells`, provider `literature.a105.rate_replicate_population`, tool
   `literature.rate.replicates.populate`. Rates recomputed from raw replicate values, with sample SD and
   standard errors.
2. Components (11): `reference_rate`, `test_rate`, `rate_difference`, `retained_fraction`, `fractional_decrease`,
   `paired_sample_sd`, `difference_se`, `reference_sample_sd`, `test_sample_sd`, `reference_mean_se`,
   `test_mean_se`. Beyond the core, all required: `evaluation_scope` (const); `approximate` (boolean);
   `unit_model` (enum `none`, `iid_units`); `dependence` (enum `unknown`, `independent`, `paired_units`);
   `conditional_on` (`iid_units`, `independent_groups`, `iid_unit_pairs`); `input_origins` (array of enum);
   `groups.<reference|test>.status` (enum `observed`, `not_observed`); `groups.<role>.observed.sampling_basis`
   (enum or null), `.measurement_count`, `.representation_count`, `.sampling_unit_count`, `.complete_unit_count`
   (integers, 0 or more); `origin` (const `derived`); `unavailable_reason` (`REASONS`, 20).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `rate_difference` | `cell(rate_difference).value` | number, rate unit | finite or null |
| `difference_se` | `cell(difference_se).value` | number, rate unit | finite, 0 or more, or null |
| `retained_fraction` | `cell(retained_fraction).value` | number, fraction | finite or null |
| `reference_sample_sd` | `cell(reference_sample_sd).value` | number, rate unit | finite, 0 or more, or null |
| `test_sample_sd` | `cell(test_sample_sd).value` | number, rate unit | finite, 0 or more, or null |
| `paired_sample_sd` | `cell(paired_sample_sd).value` | number, rate unit | finite, 0 or more, or null |
| `reference_sampling_unit_count` | `groups.reference.observed.sampling_unit_count` | integer | 0 or more, or null when not observed |
| `test_sampling_unit_count` | `groups.test.observed.sampling_unit_count` | integer | 0 or more, or null when not observed |
| `reference_measurement_count` | `groups.reference.observed.measurement_count` | integer | 0 or more, or null |
| `test_measurement_count` | `groups.test.observed.measurement_count` | integer | 0 or more, or null |
| `dependence` | `dependence` | enum | `unknown`, `independent`, `paired_units` |
| `unit_model` | `unit_model` | enum | `none`, `iid_units` |

4. Left out: `formula` (open string), `observed_subject`, `observed_experiment` (source labels), `pairing.*`
   (arrays of unit labels), group `units` labels. Carried by `dependence`, the counts and `sheet_ref`.

#### B7. Reported rate observation sheet

1. `literature_rate_observation_cells`, provider `literature.a105.reported_rate_observations`, tool
   `literature.rate.observations.populate`. Means, sample SD and CV over the reported entries of a reference and
   a test group.
2. Components (13): `reference_rate`, `test_rate`, `rate_difference`, `retained_fraction`,
   `fractional_decrease`, `reference_sample_sd`, `test_sample_sd`, `reference_cv`, `test_cv`,
   `reference_observed_point_mean`, `test_observed_point_mean`, `reference_observed_point_sd`,
   `test_observed_point_sd`. Fields, all required: `value` (number or null); `formula` (enum); `origin` (const
   `derived`); `status` (`populated`, `unavailable`); `unavailable_reason` (enum or null); `source_kind` (enum
   `primary_source`, `retained_extraction`, `synthetic_fixture`); `groups.<role>.status` (enum `observed`,
   `not_observed`); `groups.<role>.observed.selected_row_count`, `.known_entry_count`, `.representation_count`,
   `.point_entry_count` (integers, 0 or more), `.entry_count` (integer or null), `.association_unresolved`,
   `.complete` (boolean), `.limitations` (array of enum); `grouping`, `physical_conversion` (const `unknown`);
   `qualifications` (const list); `input_origins` (array of enum `reported`, `synthetic`).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `rate_difference` | `cell(rate_difference).value` | number, source native unit | finite or null |
| `retained_fraction` | `cell(retained_fraction).value` | number, fraction | finite or null |
| `reference_sample_sd` | `cell(reference_sample_sd).value` | number, source native unit | finite, 0 or more, or null |
| `test_sample_sd` | `cell(test_sample_sd).value` | number, source native unit | finite, 0 or more, or null |
| `reference_cv` | `cell(reference_cv).value` | number, dimensionless | finite or null |
| `test_cv` | `cell(test_cv).value` | number, dimensionless | finite or null |
| `reference_entry_count` | `groups.reference.observed.entry_count` | integer | 0 or more, or null |
| `test_entry_count` | `groups.test.observed.entry_count` | integer | 0 or more, or null |
| `reference_roster_complete` | `groups.reference.observed.complete` | boolean | true, false, or null when not observed |
| `test_roster_complete` | `groups.test.observed.complete` | boolean | true, false, or null when not observed |

4. Left out: `unit` (open string here), `subject`, `panel`, `source_native_unit`, group `label`,
   `requested_label`, `observation_labels` (source labels and witnesses). Carried by `sheet_ref` and the counts.
   The unit is open in this sheet, so no `<feature>_unit` field can be validated for it.

#### B8. Reported curve precision sheet

1. `literature_rate_grid_cells`, record `literature_reported_rate_observation_record_v2` of the same tool as B7.
   Precision of reported rate curves over a concentration grid, with an optional Km fit.
2. Fields, all required: `component` (open string, a cell key); `value`, `conditional_value` (number or null);
   `numeric_basis` (enum, 2); `status` (enum `populated`, `conditional_scenario`, `unavailable`);
   `variance_status` (enum `not_applicable`, `estimated`, `unknown`); `scope` (enum `full_selected_roster`,
   `available_points`, `not_applicable`); `sampling.status` (enum `supported`, `stipulated_sensitivity`,
   `unknown`, `conflicting`), `.assumption` (enum, 2), `.source_claim` (enum, 4);
   `reporting_counts.selected_reporting_entries`, `.available_numeric_entries`, `.selected_concentrations`,
   `.reporting_curves` (integer or null, 0 or more); `model_meaning.fit_model` (enum `none`,
   `unweighted_positive_km_mm`), `.estimator` (enum, 5), `.weighting` (enum, 2);
   `scientific_scope.precision_basis` (enum, 4), `.endpoint_relationship` (enum, 4); `source_kind` (enum);
   `coordinate_context[].unit` (enum `M`, `mM`, `uM`, `nM`, `unknown`) and its status, bound and origin enums.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `reporting_curve_count` | `reporting_counts.reporting_curves` | integer | 0 or more, or null |
| `concentration_count` | `reporting_counts.selected_concentrations` | integer | 0 or more, or null |
| `numeric_entry_count` | `reporting_counts.available_numeric_entries` | integer | 0 or more, or null |
| `sampling_status` | `sampling.status` | enum | `supported`, `stipulated_sensitivity`, `unknown`, `conflicting` |
| `fit_model` | `model_meaning.fit_model` | enum | `none`, `unweighted_positive_km_mm` |
| `precision_basis` | `scientific_scope.precision_basis` | enum | `not_applicable`, `descriptive_reported_entries`, `descriptive_fitted_curve_distribution`, `conditional_iid_reporting_curve_vectors` |
| `endpoint_relationship` | `scientific_scope.endpoint_relationship` | enum | `reported_convention_only`, `supported`, `unknown`, `conflicting` |

   No value feature is proposed: `component` is an open string here, so code cannot name a headline cell. The
   owner would have to fix the cell keys first.
4. Left out: `component`, `unit`, `formula_id`, `meaning_id` (open strings), `source_context.*.display_text`
   (source labels). Carried by the counts and enums above.

#### B9. Optical (NADH depletion) sheet

1. `literature_optical_cells`, provider `literature.a105.optical_population`, tool `literature.optical.populate`.
   Net NADH depletion rate from absorbance slopes and its propagated variance.
2. Components (2): `net_rate` (unit `uM/min`), `variance_net_rate` (unit `uM2/min2`). Beyond the core, all
   required: `formula_code` (enum); `evaluation_scope`, `endpoint_kind`, `endpoint_assignment` (constants);
   `source_kind` (enum, 3); `source_origin` (enum `reported`, `derived`, `synthetic`);
   `interpretations.signal_kind.value` (enum `absorbance_slope`, `absorbance_difference`, `static_absorbance`,
   `unknown`), `.relation.value` (enum `applicable_extinction_relation`, `not_applicable`, `unknown`,
   `conflicting`), `.blank_role.value` (enum `matched_no_reaction_background`, `condition_reference`,
   `component_omission`, `unknown`, `conflicting`), `.same_endpoint.value`, `.matched_window.value` (enum `same`,
   `different`, `unknown`), `.rate_window.value` (enum `source_supported_rate_interval`, `interval_mean_only`,
   `static_only`, `unknown`); `covariance.status` (enum `known`, `estimated`, `unknown`);
   `operands.<role>.approximate` (boolean or null), `.qualification`, `.observed_relation`,
   `.observation_status`, `.input_status` (enums); `unavailable_reason` (`REASONS`, 16); `conditional_on` (2).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `net_rate` | `cell(net_rate).value` | number, uM/min (signal) | finite or null |
| `net_rate_variance` | `cell(variance_net_rate).value` | number, uM2/min2 (noise) | finite, 0 or more, or null |
| `covariance_status` | `covariance.status` | enum | `known`, `estimated`, `unknown` |
| `extinction_relation` | `interpretations.relation.value` | enum | the 4 values above |
| `blank_role` | `interpretations.blank_role.value` | enum | the 5 values above |
| `same_endpoint` | `interpretations.same_endpoint.value` | enum | `same`, `different`, `unknown` |
| `matched_window` | `interpretations.matched_window.value` | enum | `same`, `different`, `unknown` |
| `rate_window` | `interpretations.rate_window.value` | enum | the 4 values above |

4. No prose field. `context.*.ref` and operand references are record refs and stay in the sheet.

#### B10. Assay component sheet

1. `literature_assay_cells`, provider `literature.a105.assay_population`, tool `literature.assay.populate`.
   Corrected activity from net rate, contaminant rate, recovery, protein amount and condition rates.
2. Components (14): `net_rate`, `contaminant_rate`, `recovery`, `protein_amount`, `condition_test_rate`,
   `condition_reference_rate`, `attributed_rate`, `condition_response`, `corrected_activity`, `effect_variance`,
   `effect_standard_uncertainty`, `effect_precision`, `source_profile_log_ratio`, `source_presence_index`. Beyond
   the core, all required: `unit` (enum `uM/min`, `uM`, `dimensionless`, `per_min`, `per_min_squared`,
   `min_squared`); `endpoint_kind` (enum `oxygen_consumption`, `product_formation`, `substrate_depletion`,
   `ligand_binding`, `transport_flux`, `growth`, `abundance`, `other_measured_endpoint`, `unknown`,
   `conflicting`); `arrangement_kind` (enum `single_preparation`, `replacement`, `coexistence`, `not_applicable`,
   `unknown`, `conflicting`); `operand_source_kind` (enum, 4); `covariance_origin` (enum or null);
   `interpretation_kind`, `evaluated_scope` (constants); `conditional_on` (`source_role_assignments`,
   `first_order_covariance_propagation`, `known_variance`, `known_normal_nonnegative_presence`); references
   `input_measurement_refs` and 16 binding refs (each or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `assayed_subject_ref` | `assayed_subject_ref` | record ref (the molecule) | a `reference` record, or null |
| `endpoint_kind` | `endpoint_kind` | enum | the 10 values above |
| `arrangement_kind` | `arrangement_kind` | enum | the 6 values above |
| `corrected_activity` | `cell(corrected_activity).value` | number, per_min (signal) | finite or null |
| `effect_standard_uncertainty` | `cell(effect_standard_uncertainty).value` | number, per_min (noise) | finite, 0 or more, or null |
| `recovery` | `cell(recovery).value` | number, dimensionless | finite, above 0, or null |
| `condition_response` | `cell(condition_response).value` | number, dimensionless | finite or null |
| `source_profile_log_ratio` | `cell(source_profile_log_ratio).value` | number, natural log ratio | finite, 0 or more, or null |
| `source_presence_index` | `cell(source_presence_index).value` | number, dimensionless | 0 to 1, or null |
| `variance_known` | `'known_variance'` in `conditional_on` of `cell(source_profile_log_ratio)` | boolean | true or false |

4. No prose field.

#### B11. Compiled assay sheet

1. `literature_compiled_assay_cells` (v1), `literature_compiled_assay_v2_cells`, `literature_compiled_assay_v3_cells`,
   provider `literature.a105.compiled_assay`, tool `literature.assay.components.populate` (optional population
   `compiled_assay`). The B10 calculation compiled from other saved sheets' cells.
2. Components v1 (16): the 14 of B10 plus `measured_endpoint_per_selected_amount`,
   `calibrated_measured_endpoint_per_selected_amount`; v2 adds `<estimand>_propagated_variance` and
   `<estimand>_propagated_standard_uncertainty`; v3 uses `COMMON_COMPONENTS` of
   `calculations/perturbation_evidence/literature_compiled_assay_calculations.py`. Fields v1 and v2, all
   required: `value`; `unit` (enum or null, 16 units); `status`; `unavailable_reason`; `formula` (enum); `origin`
   (enum, 6); `section` (enum); `meaning` (enum of fixed sentences); `conditional_on`; `qualifications` (array of
   enum); `formula_code` (enum); `operand_meanings.<role>` (enum); `endpoint_kind`, `arrangement_kind` (as B10);
   `correction_stages.<stage>` (enum); `variance_status` (enum `known`, `estimated`, `unknown`);
   `observation_model` (enum `none`, `known_normal_nonnegative_presence`); `operand_eligibility.<role>` (enum or
   null); `covariance_input_status` (enum `not_selected`, `selected_known`, `selected_estimated`,
   `selected_unknown`); `partial_uncertainty_status` (const); `annotation_credit` (null); v2 `uncertainty.scope`
   (enum, 3), `.variance_status`, `.propagation_model` (enums).
3. Proposed finding: the B10 fields except `variance_known`, plus:

| field | read from | type, unit | validator |
|---|---|---|---|
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown` |
| `covariance_input_status` | `covariance_input_status` | enum | the 4 values above |
| `observation_model` | `observation_model` | enum | `none`, `known_normal_nonnegative_presence` |

4. Left out: `assay_meanings.<field>` (source display text for molecule, organism, genotype, construct,
   preparation, condition and so on), `dependencies`, `native_quantity`. Carried by `endpoint_kind`,
   `arrangement_kind` and `sheet_ref`. `meaning` is a fixed sentence per component and adds nothing to the field
   name.

#### B12. Source quantity sheet

1. `literature_quantity_cells`, provider `literature.a105.source_quantity`, tool `literature.quantity.populate`.
   One reported value with its reported spread, and the activity derived from it.
2. Components (9): `reported_value`, `reported_spread`, `relative_reported_spread`, `corrected_activity`,
   `effect_variance`, `effect_standard_uncertainty`, `effect_precision`, `source_profile_log_ratio`,
   `source_presence_index`. Beyond the core, all required: `unit` (enum `umol/min/mg`, `uM`, `dimensionless`,
   `per_min`, `per_min_squared`, `min_squared`); `reported_uncertainty_kind` (enum `unspecified`, `unreported`);
   binding refs (each or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `reported_value` | `cell(reported_value).value` | number, row unit (signal) | finite or null |
| `reported_spread` | `cell(reported_spread).value` | number, row unit (noise) | finite, 0 or more, or null |
| `relative_reported_spread` | `cell(relative_reported_spread).value` | number, dimensionless | finite, 0 or more, or null |
| `reported_uncertainty_kind` | `reported_uncertainty_kind` | enum | `unspecified`, `unreported` |
| `source_profile_log_ratio` | `cell(source_profile_log_ratio).value` | number, natural log ratio | finite, 0 or more, or null |
| `source_presence_index` | `cell(source_presence_index).value` | number, dimensionless | 0 to 1, or null |

4. No prose field.

#### B13. Kinetic parameter contrast sheet

1. `literature_kinetic_cells`, provider `literature.a105.kinetic_population`, tool `literature.kinetic.populate`.
   Two kinetic parameters (Km, kcat or catalytic efficiency) and their contrast.
2. Components (5): `numerator_parameter`, `denominator_parameter`, `parameter_difference`, `parameter_ratio`,
   `log_parameter_contrast`. Beyond the core, all required: `threshold` (number or null); `relation` (enum `eq`,
   `lt`, `le`, `gt`, `ge`, `none`); `approximate` (boolean); `formula_code`, `evaluation_scope`,
   `contrast_meaning`, `model_input_status`, `model_reader_capability` (enums or constants);
   `comparison.subject_relationship.value` (enum `same_molecule_and_construct`, `different`, `unknown`,
   `conflicting`), `.parameter_definition_relationship.value` (enum `same`, `different`, `unknown`,
   `conflicting`), `.substrate_arrangement.value` (enum `separate_assays`, `mixed_substrates`, `unknown`,
   `conflicting`), `.comparison_scope.value` (enum `reported_protocols`, `common_conditions`, `unknown`,
   `conflicting`), `.nonintended_conditions_relationship.value` (enum `matched`, `different`, `unknown`,
   `conflicting`); for `numerator` and `denominator`: `parameter_kind` (enum `Km`, `kcat`,
   `catalytic_efficiency`, `unknown`, `conflicting`), `qualification` (enum, 4), `approximate` (boolean or null),
   `input_status` (enum, 5), `uncertainty.statistic` (enum `sd`, `sem`, `ci`, `unspecified`, `unreported`),
   `uncertainty.repetition_basis` (enum `biological_preparations`, `technical_measurements`, `unspecified`),
   `uncertainty.estimate_basis` (enum `fit_to_averaged_curve`, `between_fitted_parameters`, `unknown`),
   `uncertainty_values.magnitude`, `.confidence_level` (number or null), `.interval` (2 numbers or null),
   `.count` (integer or null, 1 or more), `.count_reported_value` (integer or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `parameter_kind` | `numerator.parameter_kind` | enum | `Km`, `kcat`, `catalytic_efficiency`, `unknown`, `conflicting` |
| `log_parameter_contrast` | `cell(log_parameter_contrast).value` | number, natural log ratio (signal) | finite or null |
| `parameter_ratio` | `cell(parameter_ratio).value` | number, dimensionless | finite, above 0, or null |
| `contrast_relation` | `relation` of `cell(log_parameter_contrast)` | enum | `eq`, `lt`, `le`, `gt`, `ge`, `none` |
| `numerator_uncertainty_magnitude` | `numerator.uncertainty_values.magnitude` | number, parameter unit | finite, 0 or more, or null |
| `numerator_uncertainty_statistic` | `numerator.uncertainty.statistic` | enum | `sd`, `sem`, `ci`, `unspecified`, `unreported` |
| `numerator_count` | `numerator.uncertainty_values.count` | integer | 1 or more, or null |
| `denominator_uncertainty_magnitude` | `denominator.uncertainty_values.magnitude` | number, parameter unit | finite, 0 or more, or null |
| `denominator_uncertainty_statistic` | `denominator.uncertainty.statistic` | enum | the same 5 values |
| `denominator_count` | `denominator.uncertainty_values.count` | integer | 1 or more, or null |
| `repetition_basis` | `numerator.uncertainty.repetition_basis` | enum | `biological_preparations`, `technical_measurements`, `unspecified` |
| `estimate_basis` | `numerator.uncertainty.estimate_basis` | enum | `fit_to_averaged_curve`, `between_fitted_parameters`, `unknown` |
| `subject_relationship` | `comparison.subject_relationship.value` | enum | the 4 values above |
| `comparison_scope` | `comparison.comparison_scope.value` | enum | the 4 values above |
| `nonintended_conditions` | `comparison.nonintended_conditions_relationship.value` | enum | `matched`, `different`, `unknown`, `conflicting` |

4. No prose field. Witness and token references stay in the sheet.

#### B14. Kinetic log model sheet

1. `literature_kinetic_model_cells`, provider `literature.a105.kinetic_model_population`, tool
   `literature.kinetic.model.populate`. The variance of the B13 log contrast under a supplied model, and the
   signed profile log ratio.
2. Components (4): `log_contrast_variance`, `log_contrast_standard_uncertainty`, `source_profile_log_ratio`,
   `source_signed_index`. B13 fields, plus, all required: `unit` (enum `dimensionless`, `dimensionless_squared`);
   `origin` (enum `derived`, `proposed`); `model_input_status` (enum `supplied`, `not_supplied`);
   `variance_status` (enum `known`, `estimated`, `unknown`, `not_supplied`); `observation_model` (enum
   `known_normal_log_parameters`, `unspecified`, `not_supplied`); `log_basis` (enum, 2); `model_origin` (enum
   `reported`, `derived`, `synthetic`, `not_supplied`); references `kinetic_sheet_ref`, `model_source_ref` (or
   null), `model_support_refs`.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `kinetic_sheet_ref` | `kinetic_sheet_ref` | record ref (the B13 sheet) | a `source` record |
| `log_contrast_standard_uncertainty` | `cell(log_contrast_standard_uncertainty).value` | number, natural log (noise) | finite, 0 or more, or null |
| `source_profile_log_ratio` | `cell(source_profile_log_ratio).value` | number, natural log ratio | finite or null |
| `source_signed_index` | `cell(source_signed_index).value` | number, dimensionless | -1 to 1, or null |
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown`, `not_supplied` |
| `observation_model` | `observation_model` | enum | the 3 values above |
| `model_origin` | `model_origin` | enum | the 4 values above |

4. No prose field.

#### B15. Kinetic summary precision sheet

1. `literature_kinetic_summary_precision_cells`, provider `literature.a105.kinetic_summary_precision`, reached
   through `literature.kinetic.populate` with version `literature_kinetic_summary_precision_population_v1`.
   Precision of one reported kinetic parameter from its reported SD and count.
2. Components (30): `source_<cell_name>` and `scenario_<cell_name>` for cell_name in `reported_parameter`,
   `reported_sd`, `source_summary_count`, `independent_preparation_count`, `statistical_estimator_count`,
   `relative_reported_sd`, `mean_variance`, `mean_standard_error`, `relative_mean_standard_error`,
   `mean_interval_df`, `mean_interval_confidence_level`, `mean_interval_t_multiplier`,
   `mean_interval_halfwidth`, `mean_interval_lower`, `mean_interval_upper`. Row fields: `population` (enum
   `source_cells`, `scenario_cells`); `cell_name` (enum); `parameter_kind` (enum `Km`, `kcat`,
   `catalytic_efficiency`, `unknown`, `conflicting`); `source_kind` (enum); `sampling_basis.source_count_meaning`
   (enum `physical_preparation_count`, `statistical_estimator_count`, `both_same_count`,
   `technical_measurement_count`, `unknown`, `conflicting`), `.repetition_basis`, `.estimate_basis` (enums as
   B13); `model_conditions[].condition` (enum, 8) and `.state` (enum `source_supported`, `source_contradicted`,
   `unknown`, `conflicting`); `limits` (array of enum); `contribution.*` (constants). Cell fields: `value`
   (number or null; counts are integers of 1 or more; the confidence level is 0.95 or null); `unit` (enum or
   null); `status` (`populated`, `unavailable`); `qualification` (enum `source_reported`,
   `derived_source_supported_conditions`, `conditional_on_stipulated_assumptions`, `unavailable`);
   `formula_code` (enum); `origin` (enum); `approximate` (boolean); `conditional_on`, `stipulated_assumptions`
   (arrays of enum); `unavailable_reason` (enum or null, 35).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `parameter_kind` | `parameter_kind` | enum | the 5 values above |
| `reported_parameter` | `cell(source_reported_parameter)` value | number, parameter unit (signal) | finite, above 0, or null |
| `reported_sd` | `cell(source_reported_sd)` value | number, parameter unit (noise) | finite, 0 or more, or null |
| `independent_preparation_count` | `cell(source_independent_preparation_count)` value | integer | 1 or more, or null |
| `statistical_estimator_count` | `cell(source_statistical_estimator_count)` value | integer | 1 or more, or null |
| `mean_standard_error` | `cell(source_mean_standard_error)` value | number, parameter unit | finite, 0 or more, or null |
| `relative_mean_standard_error` | `cell(source_relative_mean_standard_error)` value | number, dimensionless | finite, 0 or more, or null |
| `mean_interval_df` | `cell(source_mean_interval_df)` value | integer | 1 or more, or null |
| `mean_interval_halfwidth` | `cell(source_mean_interval_halfwidth)` value | number, parameter unit | finite, 0 or more, or null |
| `source_count_meaning` | `sampling_basis.source_count_meaning` | enum | the 6 values above |
| `repetition_basis` | `sampling_basis.repetition_basis` | enum | `biological_preparations`, `technical_measurements`, `unspecified` |
| `mean_standard_error_qualification` | `qualification` of `cell(source_mean_standard_error)` | enum | the 4 `qualification` values |

4. Left out: `source_context.<field>.fragments[].text` (source text for organism, genotype, molecule, construct,
   substrate and so on), `contribution.physical_measurement_id`. Carried by `parameter_kind` and `sheet_ref`.

#### B16. Controlled response sheet and measurement comparison sheet

B16a. Controlled response.

1. `literature_controlled_response_component_cells`, provider `literature.a105.controlled_response`, tool
   `literature.controlled_response.source_v3.populate` (optional population `controlled_response`). Response of
   the protein against an empty control under two conditions, and their difference.
2. Components (15): `protein_condition1_response`, `empty_condition1_response`, `protein_condition0_response`,
   `empty_condition0_response`, `condition1_controlled_response`, `condition0_controlled_response`,
   `controlled_response_difference`, `contrast_variance`, `contrast_standard_uncertainty`,
   `contrast_precision`, `source_profile_log_ratio`, `source_signed_index`, `local_difference`,
   `local_variance`, `local_standard_uncertainty`. Row: `kind` (enum `native_raw`, `local_difference`,
   `local_variance`, `local_standard_uncertainty`, `final`, `conditional`); `cell.value`, `.lower`, `.upper`
   (number or null); `cell.relation` (enum `none`, `eq`, `lt`, `le`, `gt`, `ge`, `interval`);
   `cell.approximate` (boolean); `cell.unit` (enum or null, 13 units); `cell.status` (enum `available`,
   `bounded`, `partial`, `unavailable`, `unsupported`, `conflicting`); `cell.origin` (enum or null);
   `cell.unavailable_reason` (null or array of enum); `cell.formula_code` (enum); `context.owner_state` (enum
   `known`, `unknown`, `conflicting`), `.control_application` (enum or null, 4), `.control_reuse` (enum or null,
   4), `.protein_arrangements` (array of enum), `.variance_status` (enum `known`, `estimated`, `unknown`),
   `.model_kind` (enum `none`, `known_joint_normal_source_means`), `.representation_state` (enum `single`,
   `reconciled`, `unresolved`, `conditional`).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `controlled_response_difference` | `cell` value of the `final` row for `controlled_response_difference` | number, row unit (signal) | finite or null |
| `contrast_standard_uncertainty` | same, `contrast_standard_uncertainty` | number, row unit (noise) | finite, 0 or more, or null |
| `source_profile_log_ratio` | same, `source_profile_log_ratio` | number, natural log ratio | finite or null |
| `source_signed_index` | same, `source_signed_index` | number, dimensionless | -1 to 1, or null |
| `variance_status` | `context.variance_status` | enum | `known`, `estimated`, `unknown` |
| `model_kind` | `context.model_kind` | enum | `none`, `known_joint_normal_source_means` |
| `control_reuse` | `context.control_reuse` | enum | `distinct_observations`, `same_reference_with_stated_invariance`, `unknown`, `conflicting`, or null |
| `representation_state` | `context.representation_state` | enum | `single`, `reconciled`, `unresolved`, `conditional` |

4. Left out: `component_key`, `pair_key` (open keys), `context.endpoint_id`, `.normalization_id` and the id
   arrays (open ids). Carried by `sheet_ref`.

B16b. Measurement comparison.

1. `literature_measurement_comparison_cells`, provider `literature.a105.measurement_comparison`, tool
   `literature.measurement_comparison.populate`. Compares two estimates of a quantity: difference, standardized
   difference, combined estimate and an optical interference correction. G1 accepts its cells as effect
   operands.
2. Components (26): `native_left`, `native_right`, `converted_left`, `converted_right`, `protocol_difference`,
   `protocol_ratio`, `protocol_log_ratio`, `common_difference`, `common_ratio`, `common_log_ratio`,
   `difference_variance`, `difference_standard_uncertainty`, `standardized_difference`,
   `squared_standardized_difference`, `weight_left`, `weight_right`, `combined_estimate`, `combined_variance`,
   `combined_standard_uncertainty`, `spectral_multiplier`, `spectral_multiplier_variance`,
   `observed_interference`, `corrected_estimate`, `corrected_estimate_variance`,
   `required_interference_scenario`, `required_nuisance_equivalent_scenario`. Row: `assertion_question` (enum
   `activity_existence`, `partner_dependence`, `quantitative_activity`, `coupling_compatibility`); `source_kind`
   (enum); `cell.value`, `.conditional_value` (number or null); `cell.status` (enum `populated`,
   `conditional_scenario`, `unavailable`); `cell.relation` (enum, 7); `cell.approximate` (boolean);
   `cell.interpretation` (enum, 16); `cell.formula`, `.meaning_code` (enums); `cell.origin` (enum);
   `role_meanings[]`, `relationships[]`, `model_conditions[]`, `conversion_conditions[]`,
   `covariance_provenance[]`, `dependence[]` (objects of enums); `model_settings.*` (enums); `assumptions`
   (array of enum).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `assertion_question` | `assertion_question` | enum | the 4 values above |
| `common_difference` | `cell(common_difference).value` | number (signal) | finite or null |
| `difference_standard_uncertainty` | `cell(difference_standard_uncertainty).value` | number (noise) | finite, 0 or more, or null |
| `standardized_difference` | `cell(standardized_difference).value` | number, dimensionless | finite or null |
| `combined_estimate` | `cell(combined_estimate).value` | number | finite or null |
| `combined_standard_uncertainty` | `cell(combined_standard_uncertainty).value` | number | finite, 0 or more, or null |
| `standardization_interpretation` | `cell(standardized_difference).interpretation` | enum | the 16 `interpretation` values |
| `covariance_variance_status` | `covariance_provenance[0].variance_status`, null when the list is empty | enum | `known`, `estimated`, `unknown` |

4. Left out: `cell.unit` (open string or null here), `operand_keys`, `model_keys`, `contribution_key` (open
   keys), `assertion_context.*.fragments` (source text of the molecule and the functional assertion). Carried by
   `assertion_question` and `sheet_ref`. The unit is open in this sheet, so no `<feature>_unit` field.

### Endpoint sheets (`evidence_type` = `endpoint_conversion`)

#### B17. Completion time sheet

1. `literature_completion_time_cells`, provider `literature.a105.completion_time_population`, tool
   `literature.completion_time.populate` (optional). Two completion times and their ratio.
2. Components (4): `numerator_time`, `denominator_time`, `completion_time_ratio`,
   `inverse_completion_time_ratio`. Fields, all required: `value`; `unit` (enum or null: `min`,
   `dimensionless`); `status` (enum `point`, `bounded`, `unavailable`); `unavailable_reason` (enum or null);
   `origin` (enum `reported`, `synthetic`, `derived`); `approximate` (boolean); `conditional_on` (array of enum,
   4); `reported_domain.kind` (enum `point`, `finite_interval`, `lower_bounded`, `upper_bounded`, `unbounded`,
   `unavailable`), `.lower`, `.upper` (number or null), `.lower_inclusive`, `.upper_inclusive` (boolean),
   `.projection` (enum), `.basis` (enum), `.failure` (enum or null); `comparison.endpoint_relation.value`,
   `.preparation_relation.value` (enum `same`, `different`, `unknown`, `conflicting`),
   `.pair_relationship.value` (enum `supported`, `unknown`, `conflicting`), `.other_changes_status.value` (enum
   `described`, `partial`, `unknown`, `conflicting`); `operands[].role`, `.qualification.value`,
   `.reading.bound` (enums).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `completion_time_ratio` | `cell(completion_time_ratio).value` | number, dimensionless (signal) | finite, above 0, or null |
| `completion_time_ratio_lower` | `reported_domain.lower` of that row | number, dimensionless | finite or null |
| `completion_time_ratio_upper` | `reported_domain.upper` of that row | number, dimensionless | finite or null |
| `ratio_status` | `status` of that row | enum | `point`, `bounded`, `unavailable` |
| `endpoint_relation` | `comparison.endpoint_relation.value` | enum | `same`, `different`, `unknown`, `conflicting` |
| `preparation_relation` | `comparison.preparation_relation.value` | enum | the same 4 values |
| `other_changes_status` | `comparison.other_changes_status.value` | enum | `described`, `partial`, `unknown`, `conflicting` |

   No noise feature: the sheet has no variance cell.
4. Left out: `experiment`, `intended_change`, `other_changes`, operand `meanings`, `reading` (witnesses with
   `quote`). Carried by the three comparison enums.

#### B18. Parent depletion sheet

1. `literature_parent_depletion_cells`, provider `literature.a105.parent_depletion_population`, tool
   `literature.parent_depletion.populate` (optional). Parent compound removal fractions from one workbook: active,
   inactive and abiotic arms.
2. Components (8): `active_parent_removal`, `inactive_parent_removal`, `abiotic_parent_removal`,
   `active_reported_sd`, `inactive_reported_sd`, `abiotic_reported_sd`, `active_minus_inactive`,
   `active_minus_abiotic`. Fields, all required: `value` (number, never null); `unit` (const `fraction`);
   `status` (const `point`); `origin` (enum `reported`, `calculated`); `time_hours` (integer, 0 or more);
   `row_number` (integer, 1 or more); constants `evaluation_scope`, `normalization_status`, `repetition_basis`
   (`unknown`), `active_control_covariance` (`unknown`), `equal_mutant_protein_amount` (`unknown`),
   `product_identity_for_studied_enzyme` (`unknown`), `difference_uncertainty_status`; nulls
   `reported_sd_of_difference`, `standard_error_of_difference`, `product_coupling_factor`, `annotation_credit`.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `active_minus_inactive` | `cell(active_minus_inactive).value` | number, fraction (signal) | finite |
| `active_minus_abiotic` | `cell(active_minus_abiotic).value` | number, fraction (signal) | finite |
| `active_reported_sd` | `cell(active_reported_sd).value` | number, fraction (noise) | finite, 0 or more |
| `inactive_reported_sd` | `cell(inactive_reported_sd).value` | number, fraction (noise) | finite, 0 or more |
| `abiotic_reported_sd` | `cell(abiotic_reported_sd).value` | number, fraction (noise) | finite, 0 or more |
| `time_hours` | `time_hours` | integer, hours | 0 or more |

   The sheet fixes the SD of the difference, the repetition basis and the control covariance as unknown, so no
   count and no difference noise can be proposed.
4. Left out: `compound`, `submix`, `sheet_name` (open strings from the workbook), `formula`, `exact_decimal`,
   `source_cell_addresses`, `input_measurement_keys`, `shared_active_observation_key`. Carried by `sheet_ref` and
   `time_hours`. `compound` is a chemical name, not a gene, function or product name, so it is not kept as an
   annotation field; the owner may decide otherwise.

#### B19. Concentration window sheet

1. `literature_concentration_window_cells`, provider `literature.a105.concentration_window`, tool
   `literature.concentration_window.populate`. Substrate loss, product gain and their balance over one time
   window, with propagated variances.
2. Components (34): 8 native operands (`substrate_start`, `substrate_end`, `total_product_start`,
   `total_product_end`, `fate_product_start`, `fate_product_end`, `coordinate_start`, `coordinate_end`);
   `substrate_loss`, `total_product_gain`, `fate_product_gain`, `coordinate_span`, `chemical_discrepancy`,
   `chemical_ratio`, `chemical_relative_discrepancy`, `fate_fraction`, `substrate_depletion_fraction`; six
   `source_` and `scenario_interval_average_*`; ten `*_variance`; `chemical_standardized_discrepancy`. Row:
   `source_kind` (enum, 4); `assertion_resolution` (const); `cell.value`, `.conditional_value` (number or null);
   `cell.status` (enum `populated`, `conditional_scenario`, `unavailable`); `cell.unit` (enum, 11); `cell.formula`,
   `.meaning` (enums of fixed text); `covariance_context.selection_status` (enum `selected`, `not_selected`),
   `.variance_status` (enum or null: `known`, `estimated`, `unknown`), `.origin`, `.derivation`,
   `.systematic_coverage` (enums or null); `operand_metadata[].status` (enum `point`, `bounded`, `nondetection`,
   `unavailable`), `.relation` (enum), `.approximate` (boolean); `limits` (array of enum); reason arrays (enums).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `substrate_loss` | `cell(substrate_loss).value` | number, uM (signal) | finite or null |
| `substrate_loss_variance` | `cell(substrate_loss_variance).value` | number, uM squared (noise) | finite, 0 or more, or null |
| `total_product_gain` | `cell(total_product_gain).value` | number, uM (signal) | finite or null |
| `total_product_gain_variance` | `cell(total_product_gain_variance).value` | number, uM squared | finite, 0 or more, or null |
| `substrate_depletion_fraction` | `cell(substrate_depletion_fraction).value` | number, fraction | finite or null |
| `fate_fraction` | `cell(fate_fraction).value` | number, fraction | finite or null |
| `chemical_ratio` | `cell(chemical_ratio).value` | number, dimensionless | finite or null |
| `chemical_standardized_discrepancy` | `cell(chemical_standardized_discrepancy).value` | number, dimensionless | finite or null |
| `covariance_variance_status` | `covariance_context.variance_status` | enum | `known`, `estimated`, `unknown`, or null |

4. Left out: `scientific_context` (source fields and witnesses), `estimate_bindings[].owner_key`,
   `.dependency_keys` (open keys), `source_artifacts`. Carried by `sheet_ref`.

#### B20. Endpoint signal sheet

1. `literature_endpoint_signal_cells`, provider `literature.experimental.figure`, reached through
   `literature.figure.populate` with version `literature_figure_endpoint_signal_population_v1`. Reporter trace
   amplitudes read from a figure: total, baseline-corrected and additional, as fractions and with variances.
2. Components (10): `total_amplitude`, `corrected_amplitude`, `additional_amplitude`, `retained_fraction`,
   `additional_fraction` and the `_variance` of each. Fields, all required: `value`, `conditional_value`,
   `lower`, `upper` (number or null); `unit` (enum `direction_oriented_pixel`, `dimensionless`, `pixel^2`,
   `dimensionless^2`); `status` (enum `populated`, `conditional_scenario`, `unavailable`); `origin` (const
   `derived`); `input_origins` (array of enum); `formula`, `meaning` (enums of fixed text); `conditional_on`
   (array of enum, 17); `unavailable_reasons` (array of enum, 20); `qualifications` (array of enum, 7);
   `bound_kind` (enum `manual_reading_enclosure_not_confidence_interval`, `none`); `uncertainty_basis` (enum or
   null: `joint_manual_reading_error`, `joint_physical_ordinate_estimates`); `source_kind` (enum, 3);
   `source_context.<field>.status` (enum `selected`, `not_selected`, `source_unavailable`); `row_version`,
   `evaluation_scope` (constants).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `retained_fraction` | `cell(retained_fraction).value` | number, dimensionless (signal) | finite or null |
| `retained_fraction_variance` | `cell(retained_fraction_variance).value` | number, dimensionless squared (noise) | finite, 0 or more, or null |
| `additional_fraction` | `cell(additional_fraction).value` | number, dimensionless (signal) | finite or null |
| `additional_fraction_variance` | `cell(additional_fraction_variance).value` | number, dimensionless squared | finite, 0 or more, or null |
| `retained_fraction_lower` | `lower` of `cell(retained_fraction)` | number, dimensionless | finite or null |
| `retained_fraction_upper` | `upper` of `cell(retained_fraction)` | number, dimensionless | finite or null |
| `uncertainty_basis` | `uncertainty_basis` of `cell(retained_fraction_variance)` | enum | the 2 values above, or null |
| `manual_reading` | `'manual_reading_not_physical_measurement'` in `qualifications` of `cell(retained_fraction)` | boolean | true or false |

4. Left out: `source_context.<field>.fragments[].text` (source text for subject, organism, genotype, construct,
   preparation, partners, experiment and so on), `contribution_key`, `primitive_owners`. Carried by `sheet_ref`.

#### B21. Figure ordinate sheet

1. `literature_figure_cells`, provider `literature.experimental.figure`, tool `literature.figure.populate`. One or
   two bar heights digitized from a figure and their difference.
2. Components (3): `first_ordinate`, `second_ordinate`, `ordinate_difference`. Fields, all required: `value`,
   `lower`, `upper` (number or null); `unit` (enum or null: `relative_turnover_percent`, `arbitrary_signal`,
   `nanomolar`, `relative_turnover_percentage_points`); `origin` (enum `graph_derived`, `derived`); `bound_kind`
   (const `conditional_digitization_not_confidence_interval`); `status` (`populated`, `unavailable`);
   `unavailable_reason` (enum or null, 7); `formula_code` (enum); `source_kind` (enum); `first_image_origin`
   (enum `published`, `synthetic`); `second_image_origin` (same or null); `design.arrangement` (enum
   `coexisting_sequential_catalysts`, `coexisting_complex`, `single_molecule`, `unresolved`),
   `design.contrast_kind` (enum `source_representation`, `partner_swap`, `other`, `unreported`),
   `design.endpoint_scope` (enum `coupled_final_product`, `direct_subject_step`, `binding`, `indirect_response`,
   `unreported`), `design.normalization_basis` (enum, 4), `design.measurement_relation` (enum
   `same_physical_measurement`, `distinct_physical_measurements`, `unresolved`); `design.first_repeat` and
   `design.second_repeat` (or null): `reported_n` (integer or null, 1 or more), `repeat_kind` (enum `biological`,
   `technical`, `unknown`), `independent_preparation_count` (integer or null, 1 or more), `spread_kind` (enum
   `SD`, `SEM`, `CI`, `unspecified`, `unreported`), `spread_numeric_status` (enum `not_extracted`, `unreported`);
   `first_axis_unit`, `second_axis_unit` (enums); fixed-metadata constants; references.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `ordinate_difference` | `cell(ordinate_difference).value` | number, row unit (signal) | finite or null |
| `ordinate_difference_lower` | `lower` of that row | number, row unit (digitization enclosure, not a confidence interval) | finite or null |
| `ordinate_difference_upper` | `upper` of that row | number, row unit | finite or null |
| `endpoint_scope` | `design.endpoint_scope` | enum | the 5 values above |
| `contrast_kind` | `design.contrast_kind` | enum | the 4 values above |
| `measurement_relation` | `design.measurement_relation` | enum | the 3 values above |
| `first_reported_n` | `design.first_repeat.reported_n` | integer | 1 or more, or null |
| `first_repeat_kind` | `design.first_repeat.repeat_kind` | enum | `biological`, `technical`, `unknown` |
| `first_independent_preparation_count` | `design.first_repeat.independent_preparation_count` | integer | 1 or more, or null |
| `second_reported_n` | `design.second_repeat.reported_n` | integer | 1 or more, or null |

   The evidence type of this sheet depends on `design.endpoint_scope` (it has a `binding` value). It is given
   `endpoint_conversion` here; the owner may prefer to derive `evidence_type` from `endpoint_scope`.
4. No prose field.

### Product distribution (`evidence_type` = `product_distribution`)

#### B22. Product partition sheet

1. `literature_product_partition_cells`, provider `literature.a105.product_partition_population`, tool
   `literature.product_partition.populate` (optional). Two reported product fractions, their sum and ratio.
2. Components (5): `partition_a_fraction`, `partition_b_fraction`, `selected_fraction_sum`,
   `selected_closure_deviation`, `partition_a_over_b`. Beyond the core, all required: `unit` (enum `fraction`,
   `dimensionless`); `approximate` (boolean); `threshold` (number or null); `bound` (enum `none`, `lt`, `le`,
   `gt`, `ge`); `outside_reported_fraction_range` (boolean); `experiment_status` (enum, 3);
   `relationships.same_preparation`, `.same_endpoint`, `.shared_denominator` (enum `supported`, `unknown`,
   `conflicting`); `quantities[].role`, `.basis` (enum `amount_fraction`, `signal_fraction`, `unknown`,
   `conflicting`), `.stage` (enum `equilibrium`, `timepoint`, `endpoint`, `unknown`, `conflicting`),
   `.qualification` (enum, 4); `evidence[].role` (enum, 6), `.availability` (enum, 2); `evaluation_scope`,
   `uncertainty_calculation` (constants; the latter `not_implemented`); `conditional_on` (4).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `experiment_ref` | `experiment_ref` | record ref | a `reference` record, or null |
| `partition_a_fraction` | `cell(partition_a_fraction).value` | number, fraction | finite or null |
| `partition_b_fraction` | `cell(partition_b_fraction).value` | number, fraction | finite or null |
| `partition_a_over_b` | `cell(partition_a_over_b).value` | number, dimensionless (signal) | finite or null |
| `selected_closure_deviation` | `cell(selected_closure_deviation).value` | number, fraction | finite or null |
| `outside_reported_fraction_range` | `outside_reported_fraction_range` of `cell(selected_fraction_sum)` | boolean | true or false |
| `same_preparation` | `relationships.same_preparation` | enum | `supported`, `unknown`, `conflicting` |
| `same_endpoint` | `relationships.same_endpoint` | enum | `supported`, `unknown`, `conflicting` |
| `shared_denominator` | `relationships.shared_denominator` | enum | `supported`, `unknown`, `conflicting` |
| `fraction_basis` | `quantities[0].basis` | enum | `amount_fraction`, `signal_fraction`, `unknown`, `conflicting` |

   No noise feature: `uncertainty_calculation` is `not_implemented`.
4. No prose field.

### Coupling (`evidence_type` = `reaction_coupling`)

#### B23. Product coupling sheet

1. `literature_product_coupling_cells`, provider `literature.a105.product_coupling`, tool
   `literature.product_coupling.populate`. Product formed per cofactor consumed and the productive fraction.
2. Components (11): `reported_product_activity`, `reported_cofactor_activity`, `product_per_cofactor`,
   `productive_fraction`, `calculated_coupling_percent`, `reported_coupling_percent`,
   `displayed_coupling_difference_pp`, `reconstructed_product_activity`, `product_per_cofactor_variance`,
   `productive_fraction_variance`, `productive_fraction_standard_uncertainty`. Fields, all required: `value`,
   `conditional_value`, `source_value` (number or null); `status` (enum `populated`, `conditional`,
   `unavailable`); `interpretation` (enum, 10); `origin` (enum, 4); `input_origins` (array of enum); `relation`
   (enum); `formula`, `meaning` (enums of fixed text); `native_measurement_semantics` (enum or null);
   `physical_fraction_status` (enum `within_reported_model_domain`, `outside_reported_model_domain`,
   `unresolved`, `not_applicable`); `assumptions`, `unavailable_reasons` (arrays of enum); `source_kind` (enum);
   `relationships.source_pairing.value` (enum `author_assigned`, `not_assigned`, `unknown`, `conflicting`),
   `.same_molecule.value`, `.same_preparation.value` (enum `same`, `different`, `unknown`, `conflicting`),
   `.normalization.value` (enum `compatible`, `incompatible`, `unknown`, `conflicting`), `.conditions.value`
   (enum `matched`, `different`, `unknown`, `conflicting`); `reaction_account.status` (enum `fixed_model`,
   `uncertain_model`, `unknown`, `conflicting`); `qualifications` (const list).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `productive_fraction` | `cell(productive_fraction).value` | number, fraction (signal) | finite or null |
| `productive_fraction_standard_uncertainty` | `cell(productive_fraction_standard_uncertainty).value` | number, fraction (noise) | finite, 0 or more, or null |
| `product_per_cofactor` | `cell(product_per_cofactor).value` | number, dimensionless | finite or null |
| `displayed_coupling_difference_pp` | `cell(displayed_coupling_difference_pp).value` | number, percentage points | finite or null |
| `physical_fraction_status` | `physical_fraction_status` of `cell(productive_fraction)` | enum | the 4 values above |
| `reaction_account_status` | `reaction_account.status` | enum | `fixed_model`, `uncertain_model`, `unknown`, `conflicting`, or null |
| `same_preparation` | `relationships.same_preparation.value` | enum | `same`, `different`, `unknown`, `conflicting` |
| `conditions_relation` | `relationships.conditions.value` | enum | `matched`, `different`, `unknown`, `conflicting` |

4. Left out: `unit`, `source_unit` (open strings here), `source_meanings.*.display_text`,
   `quantity_meanings.*.label` and `.unit` (source text), `input_measurement_keys`, `input_model_keys`,
   `contribution_key`. Carried by the enums above and `sheet_ref`.

#### B24. Stoichiometric balance sheet

1. `literature_stoichiometric_balance_cells`, provider `literature.a105.stoichiometric_balance_population`, tool
   `literature.stoichiometric_balance.populate` (optional). Soluble product and phosphate accounting of one
   workbook panel. The schema is fixed to one dataset (panel `D`, sheet `Data`, rows from 53).
2. Components (21): reported `g2_initial`, `g2`, `g3`, `g4`, `g5`, `g6`, `pi`, `g2_sd`, `g3_sd`, `g4_sd`, `g5_sd`,
   `g6_sd`, `pi_sd`; derived `g2_loss`, `soluble_product_molecules`, `acceptor_accounting_ratio`,
   `acceptor_balance_remainder`, `soluble_added_glucosyl_equivalents`, `soluble_glucosyl_accounting_ratio`,
   `glucosyl_balance_remainder`, `nominal_donor_to_soluble_yield`. Fields, all required: `value` (number, never
   null); `unit` (enum `mM`, `fraction`); `status` (const `point`); `origin` (enum
   `source_time_zero_nominal_matching`, `reported_mean`, `reported_sd`, `calculated`); `row_number` (integer, 53
   or more); `time_minutes` (number, 0 or more); `reaction_conditions.nominal_donor_mM`, `.nominal_acceptor_mM`,
   `.enzyme_U_per_mL`, `.MES_mM`, `.pH`, `.temperature_C` (numbers); constants `reported_sd_basis`
   (`duplicate_reactions`), `construct_status`, `initial_baseline_status`, `panel`, `sheet_name`,
   `assayed_molecule`; nulls `ratio_sd`, `ratio_se`, `ratio_confidence_interval`, `joint_covariance`,
   `matched_no_enzyme_arm`, `independent_preparation_count`, `molecule_specific_attribution`,
   `assay_validity_multiplier`, `annotation_credit`, `expression_host`.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `assayed_molecule` | `assayed_molecule` | annotation (a protein product name; meaning: the product name as printed in the source workbook) | no code looks it up; the schema fixes it to one constant string |
| `acceptor_accounting_ratio` | `cell(acceptor_accounting_ratio).value` | number, fraction (signal) | finite |
| `soluble_glucosyl_accounting_ratio` | `cell(soluble_glucosyl_accounting_ratio).value` | number, fraction (signal) | finite |
| `acceptor_balance_remainder` | `cell(acceptor_balance_remainder).value` | number, mM | finite |
| `glucosyl_balance_remainder` | `cell(glucosyl_balance_remainder).value` | number, mM | finite |
| `nominal_donor_to_soluble_yield` | `cell(nominal_donor_to_soluble_yield).value` | number, fraction | finite |
| `pi_sd` | `cell(pi_sd).value` | number, mM (noise) | finite, 0 or more |
| `g2_sd` | `cell(g2_sd).value` | number, mM (noise) | finite, 0 or more |
| `time_minutes` | `time_minutes` | number, minutes | 0 or more |
| `reaction_replicate_count` | fixed 2 because `reported_sd_basis` is the constant `duplicate_reactions` | integer | 2. Strike if a constant is not wanted in the finding. |

   The sheet fixes the ratio SD, SE, interval and covariance as null, so no noise of the ratios can be proposed.
4. Left out: `meaning`, `formula`, `exact_decimal`, `one_pi_per_transfer_premise` (open strings),
   `source_cell_addresses`, `input_measurement_keys`. Carried by the component names and `sheet_ref`.

### Binding (`evidence_type` = `ligand_binding`)

#### B25. Binding parameter sheet

1. `literature_binding_cells`, provider `literature.experimental.binding_parameter`, tool
   `literature.binding.populate`. Reference and test binding parameters (IC50 or reported Hill Kd), their spreads
   and ratio.
2. Components (10): `reference_parameter`, `test_parameter`, `reference_reported_spread`,
   `test_reported_spread`, `reference_relative_spread`, `test_relative_spread`, `native_parameter_ratio`,
   `log_native_parameter_ratio`, `source_profile_log_ratio`, `source_signed_index`. Beyond the core (no
   `conditional_on`), all required: `relation` (enum `eq`, `gt`, `ge`, `lt`, `le`, `unreported`); `unit` (enum
   `nM`, `fraction`, `dimensionless`); `status` (enum `populated`, `reported_limit`, `unavailable`,
   `conflicting`); `origin` (enum `derived`, `proposed`); `bound_kind` (enum or null); `parameter_kind` (enum
   `ic50`, `reported_hill_kd`); `uncertainty_basis` (enum `fit_to_averaged_curve`,
   `between_independent_fitted_parameters`, `unknown`); `minimum_experiment_count` (integer or null, 1 or
   more); `source_origins` (array of enum); `design` (enum `equilibrium_competition`,
   `direct_binding_isotherm`, `other`, `unknown`, `conflicting`); `protein_arrangement` (enum
   `single_preparation`, `separate_preparations`, `protein_mixture`, `unknown`, `conflicting`); nulls
   `confidence_bound`, `parameter_identification_bound`, `independent_preparation_count`; references
   `subject_ref`, `state_ref`, `experiment_ref`, `reference_ligand_ref`, `test_ligand_ref` (each or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `subject_ref` | `subject_ref` | record ref (the molecule) | a `reference` record, or null |
| `parameter_kind` | `parameter_kind` | enum | `ic50`, `reported_hill_kd` |
| `binding_design` | `design` | enum | the 5 values above |
| `protein_arrangement` | `protein_arrangement` | enum | the 5 values above |
| `log_native_parameter_ratio` | `cell(log_native_parameter_ratio).value` | number, natural log ratio (signal) | finite or null |
| `ratio_relation` | `relation` of that row | enum | `eq`, `gt`, `ge`, `lt`, `le`, `unreported` |
| `reference_relative_spread` | `cell(reference_relative_spread).value` | number, fraction (noise) | finite, 0 or more, or null |
| `test_relative_spread` | `cell(test_relative_spread).value` | number, fraction (noise) | finite, 0 or more, or null |
| `minimum_experiment_count` | `minimum_experiment_count` | integer | 1 or more, or null |
| `uncertainty_basis` | `uncertainty_basis` | enum | the 3 values above |
| `source_profile_log_ratio` | `cell(source_profile_log_ratio).value` | number, natural log ratio | finite or null |
| `source_signed_index` | `cell(source_signed_index).value` | number, dimensionless | -1 to 1, or null |

4. No prose field.

#### B26. Binding model sheet

1. `literature_binding_model_cells`, provider `literature.experimental.binding_model`, tool
   `literature.binding.model.populate`. Noise variance of the B25 log contrast under a supplied covariance, and
   the signed profile log ratio.
2. Components (5): `log_parameter_contrast`, `log_contrast_noise_variance`, `log_contrast_noise_sd`,
   `source_profile_log_ratio`, `source_signed_index`. Beyond the core, all required: `relation`, `status`,
   `bound_kind`, `parameter_kind`, `design`, `protein_arrangement`, `minimum_experiment_count` as B25; `unit`
   (enum `dimensionless`, `log_parameter_squared`); `model_kind` (enum `not_supplied`,
   `known_normal_log_parameters`); `variance_status` (enum `not_supplied`, `known`, `estimated`, `unknown`);
   `censoring_model` (enum `not_supplied`, `none`, `threshold_of_log_estimate`, `unknown`); `model_origin` (enum
   `not_supplied`, `reported`, `derived`, `synthetic`); `source_uncertainty_basis` (enum, 3); `conditional_on`
   (`supplied_log_covariance`, `known_normal_log_parameters`, `threshold_censoring_of_log_estimate`);
   references as B25 plus `original_evidence_source_ref`, `model_source_ref` (or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `log_parameter_contrast` | `cell(log_parameter_contrast).value` | number, natural log ratio (signal) | finite or null |
| `log_contrast_noise_sd` | `cell(log_contrast_noise_sd).value` | number, natural log (noise) | finite, 0 or more, or null |
| `source_profile_log_ratio` | `cell(source_profile_log_ratio).value` | number, natural log ratio | finite or null |
| `source_signed_index` | `cell(source_signed_index).value` | number, dimensionless (`tanh(source_profile_log_ratio/2)`) | -1 to 1, or null |
| `model_kind` | `model_kind` | enum | `not_supplied`, `known_normal_log_parameters` |
| `variance_status` | `variance_status` | enum | `not_supplied`, `known`, `estimated`, `unknown` |
| `censoring_model` | `censoring_model` | enum | the 4 values above |
| `minimum_experiment_count` | `minimum_experiment_count` | integer | 1 or more, or null |

4. No prose field.

#### B27. Binding interaction sheet

1. `literature_binding_interaction_cells`, provider `literature.a105.binding_interaction_population`, tool
   `literature.binding.interaction.populate`. Four binding parameters (reference or test subject with reference
   or test ligand) and their interaction ratio.
2. Components (8): `parameter_rr`, `parameter_rt`, `parameter_tr`, `parameter_tt`, `reference_subject_ratio`,
   `test_subject_ratio`, `interaction_ratio`, `log_interaction`. Fields, all required: `value`, `threshold`
   (number or null); `relation` (enum, 7); `unit` (enum or null: `nM`, `dimensionless`); `status` (enum
   `populated`, `reported_limit`, `conflicting`, `unavailable`); `origin` (enum `synthetic`,
   `visual_transcription`, `derived`); `unavailable_reason`, `calculation_unavailable_reason` (enum or null);
   `bound_kind` (enum or null); `formula_code`, `evaluation_scope`, `model_input_status`,
   `model_reader_capability` (enums); `comparison_scope` (enum `reported_protocols`, `common_conditions`);
   `common_parameter_kind.value` (enum `ic50`, `reported_hill_kd`, `unknown`, `conflicting`);
   `calculation_input_status` (enum); `relationships.<relation>.value` (enum `supported`, `unknown`,
   `conflicting`; for `common_conditions`: `matched`, `not_matched`, `unknown`, `conflicting`); per role
   (`reference_subject_reference_ligand` and the other three): `parse_status` (enum),
   `values.native.value`, `.reported_spread` (number or null), `values.uncertainty.statistic` (enum),
   `.basis` (enum), `.exact_count`, `.minimum_count` (integer or null), `.repetition_basis` (enum),
   `.confidence_level` (number or null), `.interval` (2 numbers or null), and scalar `approximate`, `percent`
   (boolean).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `log_interaction` | `cell(log_interaction).value` | number, natural log ratio (signal) | finite or null |
| `interaction_ratio` | `cell(interaction_ratio).value` | number, dimensionless | finite, above 0, or null |
| `interaction_relation` | `relation` of `cell(log_interaction)` | enum | `eq`, `lt`, `le`, `gt`, `ge`, `unreported`, `none` |
| `comparison_scope` | `comparison_scope` | enum | `reported_protocols`, `common_conditions` |
| `common_parameter_kind` | `common_parameter_kind.value` | enum | `ic50`, `reported_hill_kd`, `unknown`, `conflicting` |
| `common_conditions` | `relationships.common_conditions.value` | enum | `matched`, `not_matched`, `unknown`, `conflicting` |
| `minimum_count_<role>` (4 fields, one per role) | `roles.<role>.values.uncertainty.minimum_count` | integer | 0 or more, or null |

4. Left out: role `expression`, `unit` literals and `definitions` (candidate and fragment references to source
   text), `numeric_locations`. They are references, not text; they stay in the sheet.

#### B28. Binding interaction model sheet

1. `literature_binding_interaction_model_cells`, provider
   `literature.a105.binding_interaction_model_population`, tool `literature.binding.interaction.model.populate`.
   Variance of the B27 log interaction under a supplied covariance, and the signed index.
2. Components (4): `log_interaction_variance`, `log_interaction_standard_uncertainty`,
   `signed_profile_log_ratio`, `signed_index`. B27 fields, with: `unit` (enum `dimensionless`,
   `dimensionless_squared`); `origin` (enum `derived`); `status` (enum `populated`, `unavailable`); `relation`
   (enum `eq`, `none`); `threshold`, `bound_kind` (null); `model_input_status` (enum `supplied`, `not_supplied`,
   `supplied_native_inputs_unavailable`); `variance_status` (enum `known`, `estimated`, `unknown`,
   `not_supplied`); `distribution` (enum `normal`, `unspecified`, `not_supplied`); `log_basis` (enum, 2);
   `reporting_event` (enum `unknown`, `source_defined`, `not_supplied`); `source_kind` (enum
   `synthetic_fixture`, `primary_source`); `qualifications` (array of enum); `contrast_meaning` (const);
   references `binding_interaction_sheet_ref`, `model_source_ref` (or null), `model_support_refs`. All required.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `binding_interaction_sheet_ref` | `binding_interaction_sheet_ref` | record ref (the B27 sheet) | a `source` record |
| `log_interaction_standard_uncertainty` | `cell(log_interaction_standard_uncertainty).value` | number, natural log (noise) | finite, 0 or more, or null |
| `signed_profile_log_ratio` | `cell(signed_profile_log_ratio).value` | number, natural log ratio | finite or null |
| `signed_index` | `cell(signed_index).value` | number, dimensionless (`tanh(S/2)`) | -1 to 1, or null |
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown`, `not_supplied` |
| `distribution` | `distribution` | enum | `normal`, `unspecified`, `not_supplied` |
| `dependent_representations` | `'dependent_representations'` in `qualifications` | boolean | true or false |

4. No prose field.

#### B29. Gel band sheet

1. `literature_gel_component_cells`, provider `literature.a105.gel`, tool `literature.gel.populate` (optional).
   Band darkness read from a gel image: shifted and free bands per lane, and protein-associated and
   competitor-sensitive shifts between lanes.
2. Components (19): raw `pixel_count`, `sum_gray`, `sum_darkness`, `minimum_gray`, `maximum_gray`,
   `zero_gray_count`; `background_corrected_band_darkness`; lane `shifted_display_darkness`,
   `free_display_darkness`, `selected_total_display_darkness`, `shifted_display_fraction`,
   `off_band_display_fraction`, `display_black_pixel_fraction`, `display_total_ratio_to_protein_lane`;
   comparison `protein_associated_display_shift`, `competitor_residual_display_fraction`,
   `displaced_display_fraction`, `factorized_competitor_sensitive_shift`, `direct_competitor_sensitive_shift`.
   Row, all required: `view` (enum `raw_region`, `corrected_band`, `lane`, `comparison`, `sensitivity`);
   `region_kind` (enum or null), `band_role` (enum or null: `shifted`, `free`, `other`); `origin` (enum
   `graph_derived`, `synthetic`); `cell.value` (number or null); `cell.exact`, `.lower`, `.upper` (rational
   as two integer strings, or null); `cell.unit` (enum `display_fraction`, `display_darkness_sum`,
   `pixel_count`, `gray_level`, `gray_level_sum`); `cell.formula` (enum); `cell.status` (enum `measured`,
   `calculated`, `unavailable`, `available_range`); `cell.unavailable_reason` (enum or null, 17);
   `cell.qualifications` (array of enum, 11); `cell.sensitivity.status` (enum `complete`, `partial`,
   `no_available_values`); nulls `cell.sampling_standard_uncertainty`, `cell.confidence_interval`,
   `scientific_context.independent_preparation_count`; `scientific_context.interpretation.status` (enum
   `unknown`, `conflicting`, `descriptive_only`) and `.reasons` (array of enum);
   `scientific_context.global.<field>.state` and `scientific_context.lanes[].<meaning>.state` (enum `known`,
   `unknown`, `conflicting`);
   `dependence[].source_dependence.baseline_reused_in_factorized_form` (boolean), `.factorization_equal_to_direct`
   (boolean or null), `.same_image` (const true), `.independence_established` (const false);
   `roi_methods[].background_method` (enum `mean`, `median`).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `protein_associated_display_shift` | `cell.value` of the `comparison` row for that component | number, display fraction (signal) | finite or null |
| `direct_competitor_sensitive_shift` | same, `direct_competitor_sensitive_shift` | number, display fraction (signal) | finite or null |
| `competitor_residual_display_fraction` | same, `competitor_residual_display_fraction` | number, display fraction (not clamped) | finite or null |
| `displaced_display_fraction` | same, `displaced_display_fraction` | number, display fraction (not clamped) | finite or null |
| `shift_roi_range_lower` | code divides the numerator by the denominator of `cell.lower` of the row with `view == 'sensitivity'` for `protein_associated_display_shift` (cell status `available_range`; confirm that this is the row that carries the range) | number, display fraction | finite or null |
| `shift_roi_range_upper` | same, `cell.upper` | number, display fraction | finite or null |
| `interpretation_status` | `scientific_context.interpretation.status` | enum | `unknown`, `conflicting`, `descriptive_only`, or null |
| `lane_count` | code counts `scientific_context.lanes` | integer | 0 or more |
| `baseline_reused` | `baseline_reused_in_factorized_form` of the first `dependence` entry | boolean | true, false, or null when there is none |

   No noise feature: the sheet fixes the sampling uncertainty, the confidence interval and the independent
   preparation count as null. The ROI range is a sensitivity range, not a sampling interval.
4. Left out: `component_key`, `assignment_id`, `lane_id`, `band_id`, `observation_id` (open keys). The lane
   meanings (`subject`, `construct`, `endpoint`, `condition`, `control_role`) are record references, not text;
   they stay in the sheet.

### Transport (`evidence_type` = `transport_response`)

#### B30. Transport response sheet

1. `literature_transport_cells`, provider `literature.experimental.transport_response`, tool
   `literature.transport.response.populate`. Substrate saturation at a test and a reference concentration under
   one fitted kinetic curve, and their ratio.
2. Components (9): `substrate_test`, `substrate_reference`, `apparent_km`, `test_saturation`,
   `reference_saturation`, `condition_response`, `log_condition_response`, `condition_response_variance`,
   `condition_response_standard_uncertainty`. Beyond the core, all required: `unit` (enum `uM`,
   `dimensionless`, `dimensionless_squared`); `formula_code` (enum); `variance_status` (enum `known`,
   `estimated`, `unknown`); `observation_model` (enum `michaelis_menten`, `unknown`); `operand_source_kind`
   (enum, 4); `covariance_origin` (enum or null); `reported_km_uncertainty_kind` (enum `unspecified`,
   `unreported`, `not_supplied`); `evaluated_scope` (const); `conditional_on` (`same_kinetic_curve`,
   `michaelis_menten_response`, `first_order_covariance_propagation`); references `km_sheet_ref`,
   `covariance_source_ref` (each or null) and binding refs.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `condition_response` | `cell(condition_response).value` | number, dimensionless (signal) | finite, 0 or more, or null |
| `log_condition_response` | `cell(log_condition_response).value` | number, natural log | finite or null |
| `condition_response_standard_uncertainty` | `cell(condition_response_standard_uncertainty).value` | number, dimensionless (noise) | finite, 0 or more, or null |
| `apparent_km` | `cell(apparent_km).value` | number, uM | finite, above 0, or null |
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown` |
| `observation_model` | `observation_model` | enum | `michaelis_menten`, `unknown` |
| `reported_km_uncertainty_kind` | `reported_km_uncertainty_kind` | enum | the 3 values above |

4. No prose field. The component `description` is schema documentation.

#### B31. Channel sheet

1. `literature_channel_cells`, provider `literature.a105.channel`, tool `literature.channel.populate` (optional).
   Current, voltages and chord conductance of an electrical recording.
2. Components (9): `current`, `applied_voltage`, `reversal_voltage`, `reported_conductance`,
   `absolute_driving_voltage`, `chord_conductance`, `charge_equivalent_rate`, `chord_conductance_variance`,
   `chord_conductance_standard_uncertainty`. Fields, all required: `value`; `unit` (enum `pA`, `mV`, `pS`,
   `elementary_charge_equivalents_per_s`, `pS_squared`); `status` (`populated`, `unavailable`); `formula`,
   `section`, `meaning` (enums of fixed text); `origin`; `unavailable_reason`; `conditional_on`,
   `operand_roles` (arrays of enum); `source_kind` (enum); `arrangement_kind.value` (enum
   `single_preparation`, `replacement`, `coexistence`, `unknown`, `conflicting`); `current_kind.value` (enum
   `signed_current`, `current_step_magnitude`, `unknown`, `conflicting`); `arrangement_relation.value` (enum);
   `operands[].spread_kind.value` (enum `SD`, `SEM`, `unspecified`, `unknown`, `conflicting`);
   `variance_status` (enum `known`, `estimated`, `unknown`); `covariance_origin` (enum or null);
   `replication_status` (const `not_evaluated_by_this_component`); `interpretation_limits` (const list);
   `annotation_credit` (null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `chord_conductance` | `cell(chord_conductance).value` | number, pS (signal) | finite, 0 or more, or null |
| `chord_conductance_standard_uncertainty` | `cell(chord_conductance_standard_uncertainty).value` | number, pS (noise) | finite, 0 or more, or null |
| `current` | `cell(current).value` | number, pA | finite or null |
| `charge_equivalent_rate` | `cell(charge_equivalent_rate).value` | number, elementary charge equivalents per second | finite, 0 or more, or null |
| `current_kind` | `current_kind.value` | enum | the 4 values above |
| `arrangement_kind` | `arrangement_kind.value` | enum | the 5 values above |
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown` |

   No count: `replication_status` is the constant `not_evaluated_by_this_component`.
4. Left out: `source_meanings.*`, operand `context`, `reading`, `spread_reading` (source witnesses),
   `measurement_keys`. Carried by the enums above and `sheet_ref`.

#### B32. Ion discrimination sheet

1. `literature_ion_discrimination_cells`, provider `literature.a105.ion_discrimination`, tool
   `literature.ion_discrimination.populate` (optional). Ratio of the activity with a preferred ion to that with
   an alternative ion.
2. Components (10): `preferred_activity`, `alternative_activity`, `activity_ratio`, `log_activity_ratio`,
   `activity_ratio_variance`, `activity_ratio_standard_uncertainty`, `log_activity_ratio_variance`,
   `log_activity_ratio_standard_uncertainty`, `reported_selectivity`, `nominal_threshold_ratio`. Fields, all
   required: `value`, `threshold` (number or null); `unit` (enum or null: `dimensionless`, `per_min`, `per_s`,
   `ions_per_s`, `dimensionless_squared`); `status` (enum `populated`, `bounded`, `conditional_arithmetic`,
   `unavailable`, `conflicting`); `origin` (enum `reported`, `author_inferred`, `derived`, `synthetic`,
   `graph_derived`); `meaning` (enum, 10 codes); `relation` (enum `point`, `lt`, `le`, `gt`, `ge`,
   `lower_limit`, `upper_limit`, `none`); `approximation` (enum `source_qualified`,
   `not_explicitly_qualified`, `unknown`, `conflicting`); `quantity_kind` (enum, 8 listed and extended at import
   with the source-quantity meanings); `scientific_applicability`
   (enum `supported_for_selected_comparison`, `conditional_source_report`, `unresolved`, `incompatible`,
   `estimator_comparison_only`); `zero_denominator_case` (enum, 6); `derivation` (enum); `unavailable_reasons`,
   `source_qualifications` (arrays of enum); `reported_domain`, `nominal_domain`, `physical_domain` (domain
   objects or null); `route` (enum); `source_kind` (enum, 3); `covariance.status` (enum, 7), `.origin` (enum or
   null); `adjustment_bindings[].compiled_stage_verified` (boolean); `replication_status` (const
   `not_evaluated_by_this_component`).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `log_activity_ratio` | `cell(log_activity_ratio).value` | number, natural log ratio (signal) | finite or null |
| `log_activity_ratio_standard_uncertainty` | `cell(log_activity_ratio_standard_uncertainty).value` | number, natural log (noise) | finite, 0 or more, or null |
| `activity_ratio` | `cell(activity_ratio).value` | number, dimensionless | finite or null |
| `activity_ratio_relation` | `relation` of `cell(activity_ratio)` | enum | the 8 values above |
| `reported_selectivity` | `cell(reported_selectivity).value` | number, dimensionless | finite or null |
| `scientific_applicability` | `scientific_applicability` of `cell(activity_ratio)` | enum | the 5 values above |
| `quantity_kind` | `quantity_kind` of `cell(activity_ratio)` | enum | the `quantity_kind` values of the cell schema |
| `covariance_status` | `covariance.status` | enum | the 7 values of the schema |

4. Left out: `source_meanings`, `relationships.*.support`, `operands[].*_meanings`,
   `nonintended_differences[].support` (source witnesses with `display_text`). Carried by
   `scientific_applicability` and `sheet_ref`.

### Protein signal (`evidence_type` = `protein_signal`)

#### B33. Relative signal sheet

1. `literature_ratio_cells`, provider `literature.experimental.relative_signal`, tool
   `literature.ratio.populate`. A reported signal ratio of a variant to its reference.
2. Components (7): `reported_ratio`, `difference_from_reference`, `log_reported_ratio`,
   `calibrated_amount_ratio`, `amount_adjusted_effect`, `source_profile_log_ratio`, `source_signed_index`.
   Beyond the core, all required: `value_candidates` (array of number); `candidate_basis` (const);
   `raw_representation_roster_complete` (boolean); `unit` (enum or null: `fraction`, `dimensionless`); `status`
   (enum `populated`, `conflicting`, `unavailable`); `origin` (enum, 5); `conditional_on`
   (`source_interpretation`); `uncertainty_kind` (enum `unreported`); `independent_preparation_count` (integer
   or null, 0 or more); `source_origins` (array of enum); `interpretation_kind` (const); `signal_kind` (enum
   `protein_band`, `transcript_signal`, `other_reported_signal`, `unknown`); `reference_role` (enum
   `tagged_wt_complementation`, `endogenous_wt`, `other_reported_reference`, `unknown`, `conflicting`);
   `arrangement` (enum `single_preparation`, `replacement`, `coexistence`, `not_applicable`, `unknown`,
   `conflicting`); binding refs (each or null).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `signal_kind` | `signal_kind` | enum | the 4 values above |
| `reference_role` | `reference_role` | enum | the 5 values above |
| `arrangement` | `arrangement` | enum | the 6 values above |
| `reported_ratio` | `cell(reported_ratio).value` | number, fraction or dimensionless (signal) | finite or null |
| `log_reported_ratio` | `cell(log_reported_ratio).value` | number, natural log | finite or null |
| `reported_ratio_candidate_count` | code counts `value_candidates` of `cell(reported_ratio)` | integer | 0 or more |
| `reported_ratio_status` | `status` of `cell(reported_ratio)` | enum | `populated`, `conflicting`, `unavailable` |
| `roster_complete` | `raw_representation_roster_complete` | boolean | true or false |
| `independent_preparation_count` | `independent_preparation_count` | integer | 0 or more, or null |

   No noise feature: `uncertainty_kind` is always `unreported`.
4. No prose field.

#### B34. Relative signal source sheet

1. `literature_ratio_source_cells`, provider `literature.experimental.relative_signal_source`, tool
   `literature.ratio.source.populate` (optional). The B33 ratio read directly from selected source
   representations, with reading states.
2. Components: as B33. Fields, all required: `value`; `value_candidates` (array of number);
   `reported_domains[]` (`lower`, `upper` number or null; four booleans `lower_infinite`, `lower_closed`,
   `upper_infinite`, `upper_closed`); `unit`, `status`, `origin`, `unavailable_reason`, `conditional_on`;
   `selected_roster_resolved`, `point_candidate_set_complete`, `known_source_conflict` (boolean);
   `independent_preparation_count` (null); `uncertainty_kind` (const `unknown`); `source_origins`,
   `representation_reading_states` (array of enum `exact`, `ambiguous`, `unreadable`, `conflicting`,
   `not_applicable`); `signal_kind` (enum, B33 values plus `conflicting`); `reference_role`, `arrangement` (as
   B33); `comparison_relation_states` (array of enum `supported`, `different`, `unknown`, `conflicting`);
   `signal_scale_states` (array of enum); `signal_use` (enum `experimental_comparability`,
   `measured_endpoint`, `other`, `unknown`, `conflicting`); `meaning_statuses.<13 meanings>` (enum `known`,
   `unknown`, `conflicting`); `physical_identity_states`, `reference_identity_states` (arrays of enum);
   `uncertainty_evaluation` (const); 13 binding refs and 2 measurement ref arrays.
3. Proposed finding: `signal_kind`, `reference_role`, `arrangement`, `reported_ratio`, `log_reported_ratio`,
   `reported_ratio_candidate_count`, `reported_ratio_status` as B33, plus:

| field | read from | type, unit | validator |
|---|---|---|---|
| `signal_use` | `signal_use` | enum | the 5 values above |
| `selected_roster_resolved` | `selected_roster_resolved` | boolean | true or false |
| `point_candidate_set_complete` | `point_candidate_set_complete` | boolean | true or false |
| `known_source_conflict` | `known_source_conflict` | boolean | true or false |
| `subject_meaning_status` | `meaning_statuses.subject` | enum | `known`, `unknown`, `conflicting` |
| `reference_meaning_status` | `meaning_statuses.reference` | enum | `known`, `unknown`, `conflicting` |
| `endpoint_meaning_status` | `meaning_statuses.endpoint` | enum | `known`, `unknown`, `conflicting` |

   No noise and no count: `uncertainty_kind` is the constant `unknown` and `independent_preparation_count` is
   null.
4. No prose field.

### Protein amount (`evidence_type` = `protein_amount`)

#### B35. Amount comparison sheet

1. `literature_amount_cells`, provider `literature.a105.amount_population`, tool `literature.amount.populate`.
   Two protein amounts, their difference and ratio with uncertainties.
2. Components (12): `numerator_amount`, `denominator_amount`, `amount_difference`, `amount_ratio`,
   `reciprocal_amount_ratio`, `conditional_mass_denominator_factor`, `amount_difference_variance`,
   `amount_difference_standard_uncertainty`, `amount_ratio_variance`, `amount_ratio_standard_uncertainty`,
   `reciprocal_amount_ratio_variance`, `reciprocal_amount_ratio_standard_uncertainty`. Beyond the core, all
   required: `threshold` (number or null); `bound` (enum `none`, `lt`, `le`, `gt`, `ge`); `unit` (enum or null:
   `mg/ml`, `uM`, `mg2/ml2`, `uM2`, `dimensionless`); `approximate` (boolean); `evaluation_scope` (const);
   `comparison_kind` (enum `stock_target_mass_estimate_over_total_mass_estimate`,
   `between_arm_nominal_molar_amount`, `unknown`, `conflicting`); `pair_relationship` (enum `supported`,
   `unknown`, `conflicting`); `stock_relationship` (enum `same`, `different`, `not_applicable`, `unknown`,
   `conflicting`); `variance_status` (enum `known`, `estimated`, `unknown`); `covariance_origin` (enum or
   null); for `numerator` and `denominator`: `amount_role` (enum, 5), `amount_kind` (enum `measured`,
   `estimated`, `nominal`, `unknown`, `conflicting`), `basis_status` (enum, 3), `qualification` (enum, 4),
   `approximate` (boolean), `reported_uncertainty_kind` (enum `sd`, `sem`, `ci`, `untyped`, `unreported`,
   `unknown`, `conflicting`); `mass_factor_applied_to_rate` (const false); references.
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `comparison_kind` | `comparison_kind` | enum | the 4 values above |
| `stock_relationship` | `stock_relationship` | enum | the 5 values above |
| `amount_ratio` | `cell(amount_ratio).value` | number, dimensionless (signal) | finite, 0 or more, or null |
| `amount_ratio_standard_uncertainty` | `cell(amount_ratio_standard_uncertainty).value` | number, dimensionless (noise) | finite, 0 or more, or null |
| `amount_difference` | `cell(amount_difference).value` | number, row unit | finite or null |
| `amount_difference_standard_uncertainty` | `cell(amount_difference_standard_uncertainty).value` | number, row unit | finite, 0 or more, or null |
| `amount_ratio_bound` | `bound` of `cell(amount_ratio)` | enum | `none`, `lt`, `le`, `gt`, `ge` |
| `variance_status` | `variance_status` | enum | `known`, `estimated`, `unknown` |
| `numerator_amount_kind` | `numerator.amount_kind` | enum | the 5 values above |
| `denominator_amount_kind` | `denominator.amount_kind` | enum | the 5 values above |

4. No prose field.

#### B36. Active site sheet

1. `literature_active_site_cells`, provider `literature.a105.active_site_population`, tool
   `literature.active_site.populate` (optional). Active-site concentration from a titration against the total
   monomer concentration.
2. Components (9): `protein_mass_concentration`, `assumed_molecular_weight`, `total_monomer_concentration`,
   `active_site_concentration`, `sites_per_total_monomer`, `conditional_active_monomer_fraction`,
   `conditional_nominal_to_active_denominator_factor`, `reported_active_fraction`,
   `derived_minus_reported_fraction`. Fields, all required: `value`; `unit` (enum or null: `mg/mL`, `kDa`, `nM`,
   `dimensionless`); `status` (enum `point`, `bounded`, `unavailable`); `unavailable_reason`; `origin` (enum
   `reported`, `synthetic`, `derived`); `approximate` (boolean); `conditional_on` (array of enum, 11);
   `reported_domain` (as B17); `evaluation_scope` (const); `interpretations.molecular_basis.value` (enum
   `per_monomer`, `per_dimer`, `unknown`, `conflicting`), `.amount_linkage.value` (enum
   `same_preparation_and_assay`, `different`, `unknown`, `conflicting`), `.active_estimate_meaning.value` (enum
   `titrated_active_sites`, `other`, `unknown`, `conflicting`), `.titrant_concentration_basis.value` (enum
   `nominal_reported`, `independently_standardized_active`, `unknown`, `conflicting`),
   `.titrant_to_site_stoichiometry.value` (enum `reported_one_to_one`, `other`, `unknown`, `conflicting`),
   `.site_stoichiometry.value` (enum `one_site_per_monomer`, `other`, `unknown`, `conflicting`),
   `.normalization_stage.value` (enum `none`, `total_monomer`, `active_sites`, `unknown`, `conflicting`);
   `operands[].reported_uncertainty.kind.value` (enum `regression_sd`, `sd`, `sem`, `untyped`, `unreported`,
   `unknown`, `conflicting`), `.sampling_basis.value` (enum `same_preparation_aliquots`,
   `independent_preparations`, `unknown`, `conflicting`); `fraction_uncertainty.value` (null, constant
   `unavailable`); `rate_application_status` (enum, 5).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `conditional_active_monomer_fraction` | `cell(conditional_active_monomer_fraction).value` | number, dimensionless (signal) | finite or null |
| `active_fraction_lower` | `reported_domain.lower` of that row | number, dimensionless | finite or null |
| `active_fraction_upper` | `reported_domain.upper` of that row | number, dimensionless | finite or null |
| `sites_per_total_monomer` | `cell(sites_per_total_monomer).value` | number, dimensionless | finite, 0 or more, or null |
| `derived_minus_reported_fraction` | `cell(derived_minus_reported_fraction).value` | number, dimensionless | finite or null |
| `molecular_basis` | `interpretations.molecular_basis.value` | enum | the 4 values above |
| `amount_linkage` | `interpretations.amount_linkage.value` | enum | the 4 values above |
| `titrant_concentration_basis` | `interpretations.titrant_concentration_basis.value` | enum | the 4 values above |
| `rate_application_status` | `rate_application_status` | enum | the 5 values of the schema |

   No noise feature: `fraction_uncertainty.value` is fixed null.
4. Left out: `experiment`, `intended_change`, `other_changes`, operand `meanings`, `reading`,
   `reported_uncertainty.statement` (witnesses with `quote`), `raw_unit`. Carried by the enums above.

### Measurement validity (`evidence_type` = `measurement_validity`)

#### B37. Calibration recovery sheet

1. `literature_calibration_recovery_cells`, provider `literature.a105.calibration_recovery`, tool
   `literature.calibration.recovery.populate`. Recovery of a known amount by the assay: measured over nominal.
2. Components (14): `nominal`, `measured`, `signed_difference`, `recovery`, `relative_bias`, `percent_bias`,
   `inverse_recovery`, `reported_measured_spread`, `measured_sd`, `measured_cv`, `reported_recovery`,
   `displayed_minus_reported_recovery`, `correction_for_other_measurement`, `recovery_variance`. Fields, all
   required: `value`; `unit` (enum or null: `nmol`, `nmol/min`, `fraction`, `percent`, `fraction_squared`);
   `status` (`populated`, `unavailable`); `origin` (enum `reported`, `derived`, `synthetic`); `input_origins`
   (array of enum); `unavailable_reason` (enum or null, 13); `formula` (enum); `conditional_on` (const);
   `evaluation_scope` (const); `source_kind` (enum); `section` (enum `calibration_validity`,
   `matrix_activity_response`, `recovery_control_role_unresolved`); `control_kind` (enum `reporter_standard`,
   `enzyme_activity_spike`, `unknown`, `conflicting`); `applicability` (enum
   `same_matrix_same_endpoint_supported`, `different_matrix_or_endpoint`, `unknown`, `conflicting`);
   `spread_kind` (enum `SD`, `SEM`, `unspecified`, `unknown`); `interpretation_scope_unavailable_reason` (enum or
   null); `qualifications` (const list).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `recovery` | `cell(recovery).value` | number, fraction (signal) | finite, above 0, or null |
| `relative_bias` | `cell(relative_bias).value` | number, fraction | finite or null |
| `measured_cv` | `cell(measured_cv).value` | number, fraction (noise) | finite, 0 or more, or null |
| `recovery_variance` | `cell(recovery_variance).value` | number, fraction squared (noise) | finite, 0 or more, or null |
| `control_kind` | `control_kind` | enum | the 4 values above |
| `applicability` | `applicability` | enum | the 4 values above |
| `spread_kind` | `spread_kind` | enum | `SD`, `SEM`, `unspecified`, `unknown` |
| `section` | `section` | enum | the 3 values above |

4. Left out: `source_meanings.<field>` (open strings quoted from the source), `input_measurement_keys`. Carried
   by `control_kind`, `applicability`, `section`.

#### B38. Measurement validation sheet

1. `literature_measurement_validation_cells`, provider `literature.a105.measurement_validation`, tool
   `literature.measurement_validation.populate`. Assay precision (CV) and Z-prime, combined with a received
   recovery.
2. Components (9): `reported_cv`, `cv_fraction`, `relative_bias_squared`, `relative_variance_plugin`,
   `relative_squared_deviation_plugin`, `relative_rms_percent`, `reported_zprime`, `control_band_ratio`,
   `raw_control_zprime`. Fields, all required: `value`, `conditional_value` (number or null); `status` (enum
   `populated`, `conditional`, `unavailable`); `interpretation` (enum `native_statistic`,
   `deterministic_reexpression`, `estimated_plugin`, `conditional_plugin`, `unimplemented`); `origin` (enum,
   4); `input_origins` (array of enum); `relation` (enum); `unit` (enum `percent`, `fraction`,
   `fraction_squared`); `formula`, `meaning` (enums); `assumptions` (array of enum); `family` (enum `precision`,
   `zprime`, `raw_control`); `source_kind` (enum, 3); `relationships.<name>.value` and `formula_relation.value`
   (enums, or null); `basis` (enum or null); `evaluation_scope`, `recovery_operand_scope` (constants);
   `qualifications` (const list).
3. Proposed finding:

| field | read from | type, unit | validator |
|---|---|---|---|
| `cv_fraction` | `cell(cv_fraction).value` | number, fraction (noise) | finite, 0 or more, or null |
| `relative_rms_percent` | `cell(relative_rms_percent).value` | number, percent (noise) | finite, 0 or more, or null |
| `reported_zprime` | `cell(reported_zprime).value` | number, fraction (signal window) | finite or null |
| `control_band_ratio` | `cell(control_band_ratio).value` | number, fraction | finite, 0 or more, or null |
| `rms_interpretation` | `interpretation` of `cell(relative_rms_percent)` | enum | the 5 values above |
| `precision_basis` | `basis` | enum | the values of `RELATIONSHIPS['basis']` in `calculations/perturbation_evidence/literature_measurement_validation_calculations.py`, or null |

4. Left out: `source_meanings.*.display_text` (source text), `measurement_key`, `input_measurement_keys`,
   `contribution_key`. Carried by `family`, `precision_basis` and `sheet_ref`.

## 5. Open points for the owner

1. The unit of a G1 cell is an open string. The finding passes `quantity_kind` in its place. Closing the unit
   vocabulary in the grader would let the unit be passed.
2. `reasons` and `conditions` of G1 and G2 are open string arrays that can embed source text or record ids. The
   finding passes counts, the per-criterion statuses and exact-code booleans in their place.
3. Two aggregates combine two cells (`effect_over_noise` in G1, `perturbation_over_noise` in B2), and
   `reaction_replicate_count` in B24 restates a schema constant. Strike them if only direct sheet values are
   wanted.
4. Which sheets send a finding to the parent at all. An operand sheet is not graded against the annotation; its
   numbers reach the parent through G1 when G1 selects them. One reading of the owner's rule is that only G1 and
   G2 produce an `investigation_finding` and blocks B1 to B38 describe what G1 can cite. The tables above support
   either choice.
5. `source_signed_index` and `signed_index` are given the range -1 to 1 from the `tanh` formula seen in the
   binding model, binding interaction model and compiled assay calculations. The rate (B4) and kinetic model
   (B14) formulas were not read; confirm the range there. Likewise `source_profile_log_ratio` and
   `source_presence_index` are given "0 or more" and "0 to 1" in B10 and B12 from the compiled assay formulas
   (`max(0,corrected_activity)^2/(2*effect_variance)` and its `tanh`); confirm for those two sheets.
6. B8 (curve precision), B7, B16b and B23 declare `component` or `unit` as open strings, so some values cannot be
   named or given a unit validator until those are closed.
7. B21 (figure) has its own `design.endpoint_scope`; its `evidence_type` could be derived from it instead of
   fixed to `endpoint_conversion`.
8. G3 (assay grading) and G4 (aggregation) are in the A106 folder but unreachable from A106. They are either to be
   offered or to be removed from this axis's library.
