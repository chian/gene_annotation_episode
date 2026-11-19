# Investigation finding features: A108 (sample_context_evidence), 19 November 2026

A proposal for the owner to correct line by line. No code was changed and nothing was run.

An investigation finding here is a set of fields, one feature per field, each with an answer set code can
validate: a number with a range and unit, an integer count, a boolean, a value of a fixed vocabulary, or a record
ref. No open text field. Every proposed field below has its validator and the exact place code reads it from.

## 0. What A108 grades with, and what was read

A108 has two sheets and nothing else. Its operation catalogue
(`literature/forms/sample_context_evidence/literature_population_catalog.py`) offers exactly two operations:

| Line | Sheet family | Sheet version | Provider / tool | Written by |
|---|---|---|---|---|
| S1 | Contextual observation subscoring sheet (11 graders, one schema) | `a108_context_observation_sheet_v1` | `literature.a108.context_grading` / `literature.a108_grading.populate`, and the `reason` tool's required grading | all eight A108 episodes (the head `sample_context_evidence` through `reason` only) |
| S2 | Main evidence sheet (aggregation) | `a108_across_observation_aggregation_v1` | `literature.a108.aggregation` / `literature.a108.aggregate` | the seven episodes at and under `published_evidence_assessment` |

Schemas read: `literature/grading/literature_grading.py` (S1: `grading_sheet_schema`, `grading_cell_schema`,
`relation_schema`, `grading_input_schema`, `COMPONENTS`, `GRADER_TYPES`, `SPECIFIC_CRITERIA`),
`literature/readers/sample_context_evidence/literature_aggregation.py` (S2: `aggregation_sheet_schema`,
`aggregation_cell_schema`, `COMPONENTS`), `literature/inputs/literature_grading_inputs.py`
(`grading_population_schema`), `literature/storage/literature_grading_storage.py`,
`literature/storage/sample_context_evidence/literature_aggregation_storage.py`,
`literature/grading/sample_context_evidence/literature_required_grading.py`, and the A108 episodes' `task.py`,
`credit.py` and `messages/`.

Required: every schema object is built with `obj(...)`, which marks every listed property required (inferred from
`schema['required'].remove(...)` in `literature_grading_inputs.py` and the explicit `required=[...]` override in
`literature_required_grading.py`; `obj` itself lives outside the folders I was allowed to search). So every field
named below is required unless the line says otherwise. "nullable" means the schema type is `[..., 'null']`.

A108 sheets hold no measured quantity. There is no statistical deviation, noise, error or signal magnitude field in
either sheet: the unit of every number is `distinct_contextual_observations` (a set cardinality). The signal is
`net_support`, the amount is `evidence_amount`, the contrary signal is `conflict_count`.

A108 sheets carry no annotation field (no gene, function or product ID or name). The annotation the evidence is for
is carried as a record ref (`assertion_ref`, a hypothesis record). See line X8 for the ID fields that exist only in
the saved selection.

## 1. Proposed evidence_type vocabulary for A108

Five values, copied from the sheets (no mapping code needed):

| Line | evidence_type | Read from | Meaning |
|---|---|---|---|
| T1 | `physiology` | S1 `sheet.domain`; S2 `cell.component` | organism physiology observations (resource response, metabolic mode) |
| T2 | `environment` | same | environment observations (pH, temperature, oxygen/redox, salinity/water) |
| T3 | `availability` | same | substrate or cofactor availability observations |
| T4 | `localization` | same | localization observations (microscopy, fractionation, curated record) |
| T5 | `overall` | S2 `cell.component` only | the union of original observations across the four domains |

T1 to T4 are `DOMAINS` in `literature_grading.py`; T1 to T5 are `COMPONENTS` in `literature_aggregation.py`. The
finer type is the separate field `grader_type` (11 values, line A2).

## 2. S1: contextual observation subscoring sheet

### 2.1 What it grades

Each selected original organism-context observation is assessed against one purpose-specific grader's criteria as a
supporting, conflicting or unresolved relation to a contextual claim; code counts distinct original observations.

### 2.2 Numeric, integer, boolean and enum fields, as the schema names them

Sheet (`grading_sheet_schema`):

| Field | Type | Values |
|---|---|---|
| `version` | const | `a108_context_observation_sheet_v1` |
| `axis` | const | `A108` |
| `evaluation_scope` | const | `a108_organism_context_observations` |
| `assertion_ref` | record ref (hypothesis) | |
| `target_context_ref` | record ref (context), nullable | |
| `grader_type` | enum | `physiology_resource_response`, `physiology_metabolic_observation`, `environment_ph`, `environment_temperature`, `environment_oxygen_redox`, `environment_salinity_water`, `substrate_availability`, `cofactor_availability`, `localization_microscopy`, `localization_fractionation`, `localization_curated_observation` |
| `domain` | enum | `physiology`, `environment`, `availability`, `localization` |
| `cells` | object | one cell per component: `support_count`, `conflict_count`, `overlap_count`, `evidence_amount`, `net_support`, `unresolved_count` |
| `relations` | array of relation rows | see below |
| `annotation_credit` | null | always null |

Cell (`grading_cell_schema`), one per component:

| Field | Type | Values |
|---|---|---|
| `component` | enum | the six component names above |
| `domain` | enum | the four domains |
| `value` | integer, nullable | the component's count; null when the sheet has no relation |
| `available_value` | integer, nullable | same number as `value` |
| `status` | enum | `populated`, `conditional`, `partial`, `unavailable` (the same value in all six cells of a sheet) |
| `unit` | const | `distinct_contextual_observations` |
| `observation_sets` | object of three string arrays | keys `support`, `conflict`, `unresolved` (opaque observation keys) |
| `observation_refs`, `relation_refs`, `source_subject_refs`, `source_context_refs`, `source_refs` | arrays of record refs | |
| `measurement_keys` | array of strings | always empty for this grader (the reader sets `[]`) |
| `relations` | array of relation rows | the rows this component counts |
| `missing_inputs` | array of `{original_observation_key, context_claim_ref, reasons}` | |
| `qualifications`, `formula`, `meaning` | strings | text, see section 2.5 |

Relation row (`relation_schema`), one per (original observation, contextual claim):

| Field | Type | Values |
|---|---|---|
| `original_observation_key` | string | opaque identity computed by code |
| `original_observation_ref`, `context_claim_ref`, `source_subject_ref` | record refs | |
| `source_context_ref` | record ref (context), nullable | |
| `origin` | enum | `organism_physiology_report`, `observed_phenotype`, `recorded_sample_condition`, `curated_observation`, `prediction`, `annotation_lead` |
| `target_relationship` | enum | `direct`, `qualified_transfer`, `conditional`, `unknown` |
| `requested_relation` | enum | `support`, `conflict`, `unresolved` (what the grading call asked for) |
| `relation` | enum | `support`, `conflict`, `unresolved` (what the grader admitted) |
| `source_refs` | array of record refs | |
| `measurement_keys`, `qualifications` | arrays of strings | |
| `reasons` | array of strings | code-written tokens: `target_organism_context_unestablished`, `source_observation_unwitnessed`, `origin_is_not_observed_context_evidence`, `target_context_relationship_unknown`, `source_context_connection_unresolved`, `criterion_missing:<name>`, `criterion_unknown:<name>`, `criterion_conflicting:<name>`, `criterion_not_applicable:<name>`, `criterion_unwitnessed:<name>` |

Saved grader input (`grading_input_schema`, kept beside the sheet as `extraction` in the saved sheet record):

| Field | Type | Values |
|---|---|---|
| `version` | const | `a108_context_observation_inputs_v1` |
| `target_identity.status` | enum | `supported`, `unknown`, `conflicting`, `not_applicable` |
| `target_identity.support_refs` | array of record refs | |
| `observations[].criteria.<criterion>.status` | enum | `supported`, `unknown`, `conflicting`, `not_applicable`. Each criterion is optional in the schema (a missing one becomes `criterion_missing:<name>`); only the grader's own criteria names are allowed |
| `observations[].criteria.<criterion>.support_refs` | array of record refs | |
| other `observations[]` fields | | the relation row's fields without `requested_relation` and `reasons` |

Grading call selection (`grading_population_schema`, saved as `selection`): the input above without `version`,
`original_observation_key`, `source_refs`, `measurement_keys`, plus `source_ref` (record ref),
`target_identity_evidence` and per observation `evidence` (at least one) and `origin_link_evidence`. A selector is one
of five kinds (`kind` const: `literature_passage`, `uniprot_context`, `genbank_source_qualifier`,
`supplied_genbank_qualifier`, `taxonomy_identity`) with integers `start` (>= 0), `end` (>= 1), `occurrence`,
`source_feature_index`, `record_ordinal`, `feature_index`, `value_index` (>= 0), enums `representation`
(`original`, `text`), `field` (`organism`, `SUBCELLULAR LOCATION`, `TISSUE SPECIFICITY`, `DEVELOPMENTAL STAGE`,
`INDUCTION`, `BIOPHYSICOCHEMICAL PROPERTIES`), `qualifier` (`organism`, `strain`, `isolate`, `host`,
`isolation_source`, `collection_date`, `country`, `geo_loc_name`, `lat_lon`, `environmental_sample`, `db_xref`,
`note`), and strings `accession`, `record_accession`, `taxon_id` (pattern `^[0-9]+$`), `quote`.

### 2.3 Proposed investigation_finding, one per saved S1 sheet

Notation: `R` = `sheet['relations']`; `C` = the rows of `R` whose `relation` is `support` or `conflict`; "key" =
`original_observation_key`. The cell `cells['net_support']` holds exactly the rows of `C`.

Type:

| Line | Field | Type | Validator | Code reads it from |
|---|---|---|---|---|
| A1 | `evidence_type` | vocabulary | one of `physiology`, `environment`, `availability`, `localization` | `sheet['domain']` |
| A2 | `grader_type` | vocabulary | one of the 11 `GRADER_TYPES`; must map to A1 by `DOMAIN_BY_TYPE` | `sheet['grader_type']` |
| A3 | `sheet_ref` | record ref | a sheet record this episode saved | the population result's `sheet_ref` |
| A4 | `assertion_ref` | record ref | a hypothesis record | `sheet['assertion_ref']` |

Strength, read directly from the sheet's cells:

| Line | Field | Type, unit | Validator | Code reads it from |
|---|---|---|---|---|
| A5 | `support_count` | integer, distinct contextual observations | >= 0; null only when A11 is `unavailable` | `cells['support_count']['value']` |
| A6 | `conflict_count` | integer, same unit | >= 0; null as A5 | `cells['conflict_count']['value']` |
| A7 | `overlap_count` | integer, same unit | 0 <= value <= min(A5, A6); null as A5 | `cells['overlap_count']['value']` |
| A8 | `evidence_amount` | integer, same unit | equals A5 + A6 - A7; null as A5 | `cells['evidence_amount']['value']` |
| A9 | `net_support` | integer, same unit, signed | equals A5 - A6; null as A5 | `cells['net_support']['value']` |
| A10 | `unresolved_count` | integer, same unit | >= 0; null as A5 | `cells['unresolved_count']['value']` |
| A11 | `status` | vocabulary | one of `populated`, `conditional`, `partial`, `unavailable` | `cells['evidence_amount']['status']` |

Strength, a count code computes over the sheet's rows:

| Line | Field | Type, unit | Validator | How code computes it |
|---|---|---|---|---|
| A12 | `direct_observation_count` | integer, distinct observations | 0 <= value <= A8 | number of distinct keys among rows of `C` with `target_relationship == 'direct'` |
| A13 | `qualified_transfer_observation_count` | integer, distinct observations | 0 <= value <= A8 | same, `target_relationship == 'qualified_transfer'` |
| A14 | `conditional_observation_count` | integer, distinct observations | 0 <= value <= A8 | same, `target_relationship == 'conditional'` |
| A15 | `source_count` | integer, source records | >= 0; >= 1 when A8 > 0 | `len(cells['net_support']['source_refs'])` (it includes the grading call's primary source and any origin-link source) |
| A16 | `source_subject_count` | integer, source subject records | >= 0; >= 1 when A8 > 0 | `len(cells['net_support']['source_subject_refs'])` |
| A17 | `target_context_established` | boolean | true / false | the grader's own `target_known` rule on the saved `extraction`: `target_context_ref` is not null and `target_identity.status == 'supported'` and `target_identity.support_refs` is not empty |

Optional lines (they say why observations stayed unresolved or what kind they are; strike or keep each):

| Line | Field | Type, unit | Validator | How code computes it |
|---|---|---|---|---|
| A18 | `context_claim_count` | integer, hypothesis records | >= 0 | `len(cells['net_support']['relation_refs'])` |
| A19 | `demoted_support_count` | integer, relation rows | 0 <= value <= len(R) | rows of `R` with `requested_relation == 'support'` and `relation == 'unresolved'` |
| A20 | `demoted_conflict_count` | integer, relation rows | 0 <= value <= len(R) | rows of `R` with `requested_relation == 'conflict'` and `relation == 'unresolved'` |
| A21 | `physiology_report_observation_count` | integer, distinct observations | 0 <= value <= A8 | distinct keys among rows of `C` with `origin == 'organism_physiology_report'` |
| A22 | `observed_phenotype_observation_count` | integer, distinct observations | 0 <= value <= A8 | same, `origin == 'observed_phenotype'` |
| A23 | `recorded_condition_observation_count` | integer, distinct observations | 0 <= value <= A8 | same, `origin == 'recorded_sample_condition'` |
| A24 | `curated_observation_count` | integer, distinct observations | 0 <= value <= A8 | same, `origin == 'curated_observation'` |
| A25 | `lead_only_observation_count` | integer, distinct observations | 0 <= value <= A10 | distinct keys among rows of `R` with `origin` in `prediction`, `annotation_lead` (the grader always leaves these unresolved) |
| A26 | `unwitnessed_observation_count` | integer, relation rows | 0 <= value <= len(R) | rows of `R` whose `reasons` contain `source_observation_unwitnessed` |
| A27 | `relationship_unknown_count` | integer, relation rows | 0 <= value <= len(R) | rows of `R` whose `reasons` contain `target_context_relationship_unknown` |
| A28 | `criterion_unmet_count` | integer, relation rows | 0 <= value <= len(R) | rows of `R` with at least one reason starting `criterion_` |
| A29 | `unmet_<criterion>_count`, one field per criterion of the grader (section 2.4) | integer, relation rows | 0 <= value <= len(R); `<criterion>` must be one of that grader's criteria | rows of `R` with a reason `criterion_<state>:<criterion>` for any state |

A29 is the only place the graders differ. A supporting or conflicting observation has, by the grader's own rule,
every required criterion `supported` with a support ref, so per-criterion counts carry information only about the
unresolved rows.

### 2.4 The eleven graders (same sheet schema, same finding fields A1 to A28; only the criteria differ)

Common criteria of every grader (each an enum `status` plus `support_refs`): `source_subject_identity`,
`original_observation_identity`, `context_applicability`, `function_context_connection`, and `conflict_scope`
(required only for a conflicting relation).

| Line | `grader_type` | `evidence_type` | What it grades | Its own criteria (the `<criterion>` names for A29, with the common five) |
|---|---|---|---|---|
| G1 | `physiology_resource_response` | `physiology` | an organism-level response (growth, survival, yield) to an identified resource | `resource_role`, `response_endpoint`, `culture_circumstance`, `response_interpretation` |
| G2 | `physiology_metabolic_observation` | `physiology` | an organism-level metabolic mode (respiration, consumption, production, assimilation) of identified chemicals | `chemical_process_identity`, `organism_metabolic_mode`, `metabolic_observation_meaning` |
| G3 | `environment_ph` | `environment` | a reported pH circumstance, its compartment and its relation to the proposed role | `ph_circumstance`, `ph_compartment`, `ph_function_relation` |
| G4 | `environment_temperature` | `environment` | a growth, exposure or activity temperature and its thermal history | `thermal_circumstance`, `thermal_duration_state`, `activity_stability_distinction` |
| G5 | `environment_oxygen_redox` | `environment` | an oxygen or redox property, its exposure and its relation to the proposed role | `oxygen_redox_property`, `oxygen_redox_exposure`, `oxygen_redox_function_relation` |
| G6 | `environment_salinity_water` | `environment` | an ionic or water property (salt, ionic strength, osmolarity, water activity) and its compartment | `ionic_water_property`, `ionic_water_compartment`, `ionic_water_function_relation` |
| G7 | `substrate_availability` | `availability` | presence, supply, production or absence of the role's actual substrate | `substrate_chemical_identity`, `substrate_presence_supply`, `substrate_access_scope` |
| G8 | `cofactor_availability` | `availability` | the active form, supply route and accessible pool of the role's cofactor | `cofactor_active_form`, `cofactor_supply_route`, `cofactor_access_scope` |
| G9 | `localization_microscopy` | `localization` | a microscopy observation of where the molecule or construct is | `microscopy_molecule_construct`, `microscopy_location_assignment`, `microscopy_resolution`, `microscopy_spatial_relation` |
| G10 | `localization_fractionation` | `localization` | a fractionation distribution and its fraction-to-compartment assignment | `fractionation_molecule_preparation`, `fraction_marker_assignment`, `fractionation_distribution`, `fractionation_spatial_relation` |
| G11 | `localization_curated_observation` | `localization` | a curated database record of an observed location | `curated_molecule_identity`, `curated_evidence_origin`, `curated_location_meaning`, `curated_spatial_relation` |

### 2.5 Fields considered and left out

Prose, and the controlled fields that carry what it meant:

| Line | Sheet field | Why it is prose | Carried by |
|---|---|---|---|
| X1 | `qualifications` (cell and relation row; in the selection too) | open strings the model writes, mixed with code tokens | A11 `status`, A12 to A14 (transfer or condition-specific evidence), A25 (identity-only metadata becomes `annotation_lead`). The token `cross_source_original_observation_link_is_witnessed_interpretation` is carried by nothing; say if a count is wanted |
| X2 | `formula`, `meaning` (cell) | sentences (constant per component, written by code) | the field name and unit of A5 to A10 |
| X3 | `quote` and selector `value` (selection, reader records) | source text | A3 `sheet_ref` |
| X4 | the assessment record's current `investigation_finding` (source claim: subjects, predicate, value, contexts; qualification; what it replaces) | model-written claim and qualification | the whole of section 2.3; its `status` (`credit.py` reads `retained`) stays inside the episode |
| X5 | the report form in `messages/final_to_parent.py` (`interpretation`, `source_claim`, `source_subject`, `qualification`, `readings[].location`, `readings[].statement`, `readings[].qualification`) | model-written text | the whole of section 2.3 |

Not prose, left out for another reason:

| Line | Sheet field | Reason |
|---|---|---|
| X6 | `observation_sets`, `original_observation_key`, `observation_refs`, `relation_refs`, `source_subject_refs`, `source_context_refs`, `source_refs`, `relations`, `missing_inputs` | each gathers several items in one field; their cardinalities are A5 to A10, A15, A16, A18; the identities stay in the sheet behind A3 |
| X7 | `reasons` (relation row, `missing_inputs`) | a list of code tokens; turned into the counts A26 to A29 |
| X8 | `accession` (UniProt accession), `record_accession` (GenBank record accession), `taxon_id` (NCBI Taxonomy ID) in the selection's selectors | IDs of the source record or organism the evidence was read from, several per sheet, not the annotated gene, function or product; if the owner wants one as an annotation field, its meaning is the named list |
| X9 | `available_value`, `measurement_keys`, `unit`, `version`, `axis`, `evaluation_scope`, `annotation_credit`, `component`, cell `domain` | duplicates, constants or always empty |
| X10 | `target_context_ref` | the parent passed it; A17 says whether it was established |
| X11 | `target_identity.status` | A17 is the grader's own use of it; replace A17 by this 4-value field if the unknown / conflicting distinction is wanted |
| X12 | selector integers (`start`, `end`, `occurrence`, the index fields) | locations in a source, not strength |

## 3. S2: main evidence sheet (aggregation)

### 3.1 What it grades

It unions the original observations of selected S1 `evidence_amount` cells within each domain and across all four,
counting each original observation once.

### 3.2 Numeric, integer, boolean and enum fields, as the schema names them

Sheet (`aggregation_sheet_schema`): `version` (const `a108_across_observation_aggregation_v1`), `axis` (const
`A108`), `evaluation_scope` (const `a108_across_observation_aggregation`), `assertion_ref` (record ref, hypothesis),
`target_context_ref` (record ref, context, nullable), `cells` (object with the five cells `physiology`,
`environment`, `availability`, `localization`, `overall`), `annotation_credit` (null).

Cell (`aggregation_cell_schema`):

| Field | Type | Values |
|---|---|---|
| `component` | enum | `physiology`, `environment`, `availability`, `localization`, `overall` |
| `evaluation_scope` | const | `a108_across_observation_aggregation` |
| `assertion_ref`, `target_context_ref` | record refs (the second nullable) | |
| `value` | integer, nullable | equals `evidence_amount` |
| `available_value` | integer, nullable | same number |
| `status` | enum | `complete`, `partial`, `unavailable` |
| `unit` | const | `distinct_contextual_observations` |
| `support_count`, `conflict_count`, `overlap_count`, `evidence_amount`, `net_support`, `unresolved_count` | integer, nullable (each) | null when the cell has no relation |
| `observation_sets` | object of three string arrays | `support`, `conflict`, `unresolved` |
| `observation_refs`, `relation_refs`, `source_subject_refs`, `source_context_refs`, `source_refs`, `unavailable_sheet_refs` | arrays of record refs | `source_refs` also lists the selected sheets |
| `measurement_keys` | array of strings | |
| `relations` | array of relation rows | same row schema as S1 |
| `selected_components` | array of `{sheet_ref, component}` | `component` const `evidence_amount` |
| `missing_inputs` | array | as S1 |
| `qualifications`, `formula`, `meaning` | strings | text |
| `annotation_credit` | null | |

Aggregation call (`aggregation_population_schema`): `assertion_ref`, `target_context_ref` (nullable),
`contributions[]` of `{sheet_ref, component: const 'evidence_amount'}`. The current-revision variant adds a
`calculation_context` with `source_versions[].publication_order` (integer).

### 3.3 Proposed investigation_finding, one per S2 cell whose `status` is not `unavailable`

Notation: `cell` = `sheet['cells'][component]`; `Cc` = rows of `cell['relations']` whose `relation` is `support` or
`conflict`.

| Line | Field | Type, unit | Validator | Code reads or computes it from |
|---|---|---|---|---|
| B1 | `evidence_type` | vocabulary | one of `physiology`, `environment`, `availability`, `localization`, `overall` | `cell['component']` |
| B2 | `sheet_ref` | record ref | an aggregation sheet record this episode saved | the population result's `sheet_ref` |
| B3 | `assertion_ref` | record ref | a hypothesis record | `sheet['assertion_ref']` |
| B4 | `support_count` | integer, distinct contextual observations | >= 0 | `cell['support_count']` |
| B5 | `conflict_count` | integer, same unit | >= 0 | `cell['conflict_count']` |
| B6 | `overlap_count` | integer, same unit | 0 <= value <= min(B4, B5) | `cell['overlap_count']` |
| B7 | `evidence_amount` | integer, same unit | equals B4 + B5 - B6 and equals `cell['value']` | `cell['evidence_amount']` |
| B8 | `net_support` | integer, same unit, signed | equals B4 - B5 | `cell['net_support']` |
| B9 | `unresolved_count` | integer, same unit | >= 0 | `cell['unresolved_count']` |
| B10 | `status` | vocabulary | one of `complete`, `partial` (`unavailable` cells produce no finding) | `cell['status']` |
| B11 | `selected_sheet_count` | integer, subscoring sheets | >= 1 | `len(cell['selected_components'])` |
| B12 | `unavailable_sheet_count` | integer, subscoring sheets | 0 <= value <= B11 | `len(cell['unavailable_sheet_refs'])` |
| B13 | `direct_observation_count` | integer, distinct observations | 0 <= value <= B7 | distinct keys among rows of `Cc` with `target_relationship == 'direct'` |
| B14 | `qualified_transfer_observation_count` | integer, distinct observations | 0 <= value <= B7 | same, `qualified_transfer` |
| B15 | `conditional_observation_count` | integer, distinct observations | 0 <= value <= B7 | same, `conditional` |
| B16 | `source_count` | integer, source records | >= 0 | number of distinct refs in `row['source_refs']` over rows of `Cc` (not `cell['source_refs']`, which also lists the sheets and the unresolved rows' sources) |
| B17 | `source_subject_count` | integer, source subject records | >= 0 | number of distinct `row['source_subject_ref']` over rows of `Cc` |
| B18 | `domain_count` (only when B1 is `overall`) | integer, domains | 0 <= value <= 4 | number of the four domain cells of the same sheet whose `evidence_amount` is >= 1 |

Optional, as for S1: the origin counts A21 to A25 and the demoted counts A19, A20, computed the same way over
`cell['relations']`.

### 3.4 Fields considered and left out

Prose, and the controlled fields that carry what it meant:

| Line | Sheet field | Why it is prose | Carried by |
|---|---|---|---|
| Y1 | `qualifications` | the S1 open strings unioned, plus code tokens (`contains_source_qualified_transfer_or_condition_specific_evidence`, `no_subscoring_component_selected_for_this_domain`, `known_eligible_counts_preserved_with_unresolved_selected_relations`, three fixed disclaimers) | B14, B15 (transfer or condition-specific), B11 (nothing selected gives no finding), B10 and B9 (unresolved kept) |
| Y2 | `formula`, `meaning` | sentences written by code | the field names and unit of B4 to B9 |

Not prose, left out for another reason:

| Line | Sheet field | Reason |
|---|---|---|
| Y3 | `observation_sets`, the ref arrays, `relations`, `selected_components`, `missing_inputs` | each gathers several items; cardinalities are B4 to B9, B11, B12, B16, B17; identities stay behind B2 |
| Y4 | `value`, `available_value`, `unit`, `version`, `axis`, `evaluation_scope`, `annotation_credit`, `measurement_keys`, `target_context_ref` | duplicates, constants or the parent's own input |
| Y5 | `calculation_context.source_versions[].publication_order` | revision bookkeeping, not evidence |

## 4. Not sheets: read, nothing proposed

| Line | Item | Its controlled fields | Proposal |
|---|---|---|---|
| Z1 | Root scalar over the `overall` cell (`annotation_scalar` in `literature_aggregation.py`, `_result` in `literature_annotation_scalar.py`) | `value` (number, -1 <= value <= 1, nullable; formula (support - conflict) / (1 + evidence_amount)), `status` (`available`, `partial`, `unavailable`), `direction` (`unknown`, `support`, `opposition`, `measured_neutral`), `transfer.status` (`established`, `unresolved`, `invalid`), `source_contribution_count` (integer); text: `formula`, `interpretation`, `missing_inputs` | no finding field: it is a reader, not a grader, and it restates B4, B5 and B7 |
| Z2 | The `no_applicable_evidence` outcome of required grading (`literature_required_grading.py`) | `evidence_processing.kind` (`graded`, `no_applicable_evidence`), `examined[]` with `representation` (`original`, `text`), `start` (integer >= 0), `end` (integer >= 1); text: `reason`, `quote` | no finding: no sheet exists and it is not evidence for the annotation. Owner to say if a sixth evidence_type value is wanted for it |
| Z3 | The rate, assay, partner-unit and rate-domain files in the A108 library folders (`forms/sample_context_evidence/literature_rate_domains.py`, `literature_experimental_contracts.py`, `literature_partner_*.py`, `storage/sample_context_evidence/literature_rate_storage.py`, `inputs/sample_context_evidence/literature_rate_native_inputs.py`, `calculations/sample_context_evidence/literature_rate_calculations.py`) | A105 rate-sheet schemas (provider `literature.a105.rate_population`) | none for A108: no A108 episode writes a rate sheet; the A108 episodes import only the witness readers from `literature_assay_inputs.py` |

## 5. Lines the owner may want to decide

1. Whether `evidence_type` should be the four domains (as proposed) or the eleven `grader_type` values directly
   (then A2 is dropped).
2. S1 and S2 use different `status` vocabularies (`populated / conditional / partial / unavailable` and
   `complete / partial / unavailable`). The proposal keeps each sheet's own words (A11, B10).
3. Which of the optional lines A18 to A29 stay.
4. `source_count` (A15) counts source records cited by the counted observations, including the grading call's
   primary source; it is not a count of independent studies. The sheets hold no such count.
