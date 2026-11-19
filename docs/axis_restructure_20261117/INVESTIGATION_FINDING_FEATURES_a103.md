# A103 gene_context_evidence: investigation finding features (draft, for line-by-line correction)

Sources read (only): `episode_support/grading/gene_context_evidence/{scoring,credit,contribution,tool_grading_artifacts,progress_information_credit,practical_execution_credit}.py`,
`episode_support/records/gene_context_evidence/{publication,attachments}.py`,
`episode_support/findings/gene_context_evidence/*`, `episode_support/literature/readers/gene_context_evidence/*`,
and under `root/a103/gene_context_evidence/` the head and the seven literature episodes (`credit.py`, `task.py`
decide/action, `messages/{final_to_parent,msg_to_child,read_from_child}.py`), plus `root/task.py` and
`root/messages/msg_to_child.py` for the head's parent.

Facts that shape the proposal:

- A103 has **no literature grader**: there is no `literature/{forms,storage,inputs,grading}/gene_context_evidence/`,
  and no shared `literature/forms` file names the axis. `literature/readers/gene_context_evidence/` holds only
  source discovery and asset access. `findings/gene_context_evidence/` holds command custody and image decoding, no
  scoring.
- The axis grades with **one native sheet per measurement** (`a103_native_sheet_v1`, `publication.native_grade`)
  and **one attachment sheet per measurement and policy** (`a103_tool_attachment_v1`, `attachments.refresh`),
  read by **one credit projector** (`A103ContextCredit.read_details`, maximum attachment score per region cell, then a
  length-weighted mean over the assigned scope) and one annotation scalar (`contribution._result`).
- Every literature episode's credit is the same `A103ContextCredit` over held attachments, so reading literature
  earns nothing unless a native measurement is published and attached. Its findings have no sheet that code
  could read features from (see section B).
- Credit is not restated anywhere below.

## Proposed `evidence_type` vocabulary (fixed, 6 values)

| value | produced by (sheet kind -> attachment policy) | scored |
|---|---|---|
| `conserved_neighborhood` | `recurrence` -> `recurrence_specific_loci_components_and_sampling_v1` | yes |
| `gene_fusion` | `fusion` -> `fusion_each_required_region_and_actual_coding_product_v1` | yes |
| `phylogenetic_cooccurrence` | `cooccurrence` -> `enumerated_panel_actual_detections_and_declared_null_v1` | yes |
| `context_channel_association` | `native_channel` -> `native_channel_exact_endpoints_and_specific_distance_v1` | yes |
| `context_contrast` | `functional_contrast` -> `functional_contrast_matched_native_context_and_bounds_v1` | no (score is always null) |
| `single_locus_organization` | `organization` -> `actual_neighborhood_and_specific_target_locus_v1` | no (score is always null) |

`locus_binding` and `component_detection` are not evidence types: they are operands whose states feed the
attribution features below (`target_link_*`, `partner_*`). Code maps `grade.kind` to `evidence_type` with this
table; the model never chooses it.

Common features on every finding (code reads them from the attachment sheet):

| field | type | values / range | unit | read from |
|---|---|---|---|---|
| `evidence_type` | enum | the six values above | - | `grade.kind` via the table |
| `sheet_ref` | record_ref | the attachment source | - | `_publish` return (`source_ref`) |
| `measurement_ref` | record_ref | the native measurement source | - | attachment `measurement_ref` |
| `attachment_state` | enum | `evaluated`, `partial`, `unresolved` | - | attachment `state` |
| `score_lower` | number | [0, 1] or null | context association index | attachment `score` (= `bounds[0]` for recurrence) |
| `score_upper` | number | [0, 1] or null | context association index | attachment `bounds[1]`; equals `score` where no bounds |
| `missing_count` | integer | >= 0 | missing operands | `len(attachment.missing)` |
| `missing_codes` | list of enum | the closed code set of `attachments.py` (`actual_neighborhood_measurement`, `complete_scoped_partner_detection`, `actual_partner_footprint_for_relationship`, `conflicting_specific_component_detection`, `actual_relationship_geometry_or_scoped_nondetection`, `received_specific_component_sequences`, `native_map_in_required_component_region`, `actual_unambiguous_cds_translation`, `actual_verified_cds_translation`, `protein_product_or_original_genomic_placement`, `actual_target_locus_or_fragment_placement_disambiguation`, `evaluable_independent_detections_for_both_components`, `native_endpoint_to_canonical_sequence_identity`, `supporting_context_comparison`, `opposing_context_comparison`, `qualified_context_for_each_selected_comparison`, `matched_native_route_and_original_scope`) | - | attachment `missing` (owner: keep as list-of-enum or drop for `missing_count` only) |
| `target_link_state` | enum | `evaluated`, `unresolved` | - | attachment `target_link.state` (fusion, cooccurrence, organization, recurrence rows) |
| `target_link_factor` | number | [0, 1] or null | fraction of matched residues weighted by native strength | `target_link.factor` |
| `target_identity_distance` | number | [0, 1] or null | fraction of mismatched aligned residues | `target_link.identity_distance` |
| `target_coverage` | number | [0, 1] or null | fraction of the longer sequence | `target_link.coverage` |
| `locus_application` | enum | `actual_nucleotide_placement_in_received_genomic_source`, `supplied_target_genomic_provenance`, `inferred_reference_locus_context`, `ambiguous_supplied_target_placement` | - | `target_link.locus_application` |
| `dependency_variant_ambiguous` | boolean | | - | credit projector: attachment's `dependency_group` in the `ambiguous` set |

## A. Sheet families and scoring projectors

### A1. `a103_native_sheet_v1` (publication.native_grade) — the native grade of every measurement

(1) The per-measurement native index on [0, 1] for any of the eight measurement schemas; it is "progress, not function
probability" and must be attached before it counts.

(2) Fields: `kind` (enum, required: `locus_binding`, `organization`, `recurrence`, `fusion`, `cooccurrence`,
`native_channel`, `functional_contrast`, `component_detection`); `raw_value` (number in [0, 1] or null, required;
= `group_balanced_fraction` | `observed_link_fraction` | `native_significance_index` | `native_value` | null);
`schema`, `version`, `profile` (fixed constants); `producer_operation` (enum of operation names); `target_ref`
(record_ref); `native_measurement_sha256` (hash). No boolean or integer fields.

(3) Finding: not a finding by itself. Contributes `evidence_type` (via `kind`) and `raw_value` to the finding of
its attachment (A2–A7) as `native_raw_value` (number [0, 1] or null, unit as per family).

(4) Prose left out: `target_attribution`, `interpretation` (both fixed code constants, carried by `kind` +
`attachment_state`).

### A2. `a103_recurrence_v1` + recurrence attachment — conserved neighborhood across an explicit genome panel

(1) Whether a declared pair arrangement (gap, intervening genes, orientation, order) recurs across the loci of a
panel, balanced over genomes within sampling groups, with each locus row qualified by target and partner identity.

(2) Native sheet (`compare_neighborhoods`), all required: `supporting_loci` (int >= 0), `evaluable_loci` (int >= 0),
`unknown_loci` (int >= 0), `evaluable_genomes` (int >= 0), `native_fraction` (number [0, 1] or null),
`sampling_group_count` (int >= 0), `group_balanced_fraction` (number [0, 1] or null); `definition`:
`maximum_gap_bp` (int, bp), `maximum_intervening_genes` (int), `orientation` (enum `any|same|convergent|divergent`),
`order` (enum `any|left_before_right|...`). Per row `organization`: `state` (enum `measured|unresolved|measured_nondetection`),
`gap_bp` (int, bp, negative when overlapping order), `overlap_bp` (int >= 0, bp), `intervening_annotated_cds`
(int >= 0), `orientation` (enum `same|convergent|divergent|unknown`), `right_direction_from_left` (int -1|1),
`circular_arc_used` (bool); row `relationship_holds` (bool or null).
Attachment: `state` (enum `evaluated|partial`), `score` (number [0, 1]), `bounds` (2 numbers [0, 1]), `raw_value`,
`sampling_group_count` (int), per row `qualified_value` (number [0, 1] or null), `raw_relationship_holds` (bool|null),
`relationship_holds` (bool|null), `partner_link.state` (enum `evaluated|unresolved|evaluated_nondetection`),
`partner_link.factor` (number [0, 1]|null); `dependency_group`, `variant` (record ids).

(3) Finding `evidence_type = conserved_neighborhood`. Strength features:

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `score_lower` | number | [0, 1] | balanced fraction of genomes with the arrangement | attachment `bounds[0]` |
| `score_upper` | number | [0, 1] | same | attachment `bounds[1]` |
| `native_raw_value` | number | [0, 1] or null | same, before target/partner qualification | native `group_balanced_fraction` |
| `supporting_locus_count` | integer | >= 0 | loci | count rows with `qualified_value > 0` |
| `evaluable_locus_count` | integer | >= 0 | loci | native `evaluable_loci` |
| `unknown_locus_count` | integer | >= 0 | loci | count rows with `qualified_value` null |
| `evaluable_genome_count` | integer | >= 0 | genomes | native `evaluable_genomes` |
| `sampling_group_count` | integer | >= 0 | independent sampling groups | attachment `sampling_group_count` |
| `partner_nondetection_count` | integer | >= 0 | loci (a negative-control row: complete local search found no partner) | count rows with `partner_link.state == evaluated_nondetection` |
| `max_gap_bp` | integer | 0..100000 | bp | definition `maximum_gap_bp` |
| `max_intervening_genes` | integer | >= 0 | annotated CDS | definition `maximum_intervening_genes` |
| `required_orientation` | enum | `any|same|convergent|divergent` | - | definition `orientation` |
| `min_target_link_factor` | number | [0, 1] or null | see common | min over rows of `target_link.factor` |
| uncertainty block: `uncertainty_magnitude` | number | [0, 1] | balanced fraction | `bounds[1] - bounds[0]` |
| `uncertainty_count` | integer | >= 0 | unresolved rows | = `unknown_locus_count` |
| `uncertainty_kind` | enum | `unresolved_row_interval` | - | constant for this family |
| `sampling_basis` | enum | `locus_within_genome_within_group` | - | constant (native `sampling_aggregation`) |

(4) Prose left out: native `interpretation`, `sampling_aggregation` (fixed constants: carried by
`sampling_basis`); attachment `interpretation` (constant). `required_operands` (list of records with codes; carried by
`missing_codes` and the sheet ref).

### A3. `a103_fusion_v1` + fusion attachment — attributed domain fusion in one coding product

(1) Whether two or more attributed regions sit in one verified coding product, each region's sequence linked to a
named component and the product linked to the target.

(2) Native: `same_coding_product` (bool, always true), `observed_link_fraction` (number, always 1.0), `regions[]`:
`start`, `end` (int, aa positions, required), `component_ref` (record_ref); `coding_locus.translation.status`
(enum `verified|qualified`), `.qualification` (enum `partial_codon|source_translation_exception|declared_translation_conflict|internal_stop|sequence_or_location_unavailable|partial_or_pseudogene_annotation` or null),
`.exact_boundaries` (bool), `.genetic_code` (int), `.codon_start` (int 1..3).
Attachment: `state` (enum `evaluated|unresolved`), `score` (number [0, 1] or null = min of all factors), `bounds`,
per region `component_attribution.state` (enum), `.factor`, `.identity_distance`, `.coverage` (numbers [0, 1]),
`target_positions` (ints), `target_feature_ref` (record_ref).

(3) Finding `evidence_type = gene_fusion`. Strength features:

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `score_lower` = `score_upper` | number | [0, 1] or null | min correspondence factor | attachment `score` |
| `region_count` | integer | >= 2 | regions | `len(regions)` |
| `attributed_region_count` | integer | >= 0 | regions | count regions with `component_attribution.factor` not null |
| `min_region_coverage` | number | [0, 1] | fraction of region | min `component_attribution.coverage` |
| `max_region_identity_distance` | number | [0, 1] | fraction of mismatched residues | max `component_attribution.identity_distance` |
| `translation_status` | enum | `verified|qualified` | - | `coding_locus.translation.status` |
| `translation_qualification` | enum | the six codes above, or `none` | - | `coding_locus.translation.qualification` |
| `exact_boundaries` | boolean | | - | `coding_locus.translation.exact_boundaries` |
| uncertainty block: magnitude | number | [0, 1] | fraction | = `max_region_identity_distance` |
| count / kind / basis | int / enum / enum | `region_count` / `sequence_correspondence_identity_distance` / `per_region` | | |

(4) Prose left out: `interpretation` (constant). Region `label`-like keys, if the caller's region rows carry any, stay in the sheet.

### A4. `a103_cooccurrence_v1` + cooccurrence attachment — presence/absence association over a genome panel

(1) A one-sided exact (hypergeometric) enrichment of joint presence of two components over an enumerated panel,
with independence of rows checked by sampling group.

(2) Native, all required: `contingency.both`, `.left_only`, `.right_only`, `.neither` (ints >= 0),
`evaluable_genomes`, `unknown_genomes`, `sampling_group_count` (ints >= 0), `risk_difference` (number [-1, 1] or
null), `p_value` (number [0, 1] or null), `log10_significance` (number >= 0 or null), `native_significance_index`
(number [0, 1] or null), `independent_row_test_eligible` (bool); per row `left_present`, `right_present`
(bool or null). Attachment: `state` (enum `evaluated|unresolved`), `score` (= raw x target factor), `raw_value`,
`contingency`, `risk_difference`, `p_value` copied, `detection_scope` (caller-supplied; type outside these folders).

(3) Finding `evidence_type = phylogenetic_cooccurrence`. Strength features:

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `score_lower` = `score_upper` | number | [0, 1] or null | L/(1+L), L = -log10 p, positive effect only | attachment `score` |
| `both_present_count` | integer | >= 0 | genomes | `contingency.both` |
| `left_only_count` | integer | >= 0 | genomes | `contingency.left_only` |
| `right_only_count` | integer | >= 0 | genomes | `contingency.right_only` |
| `neither_count` | integer | >= 0 | genomes | `contingency.neither` |
| `evaluable_genome_count` | integer | >= 0 | genomes | `evaluable_genomes` |
| `unknown_genome_count` | integer | >= 0 | genomes | `unknown_genomes` |
| `risk_difference` | number | [-1, 1] or null | difference of proportions | `risk_difference` |
| `sampling_group_count` | integer | >= 0 | sampling groups | `sampling_group_count` |
| `independent_rows` | boolean | | - | `independent_row_test_eligible` |
| `control_present` | boolean | | - | `left_only + neither > 0` (genomes without the target component exist) |
| uncertainty block: `uncertainty_magnitude` | number | [0, 1] or null | probability | `p_value` |
| `uncertainty_count` | integer | >= 0 | genomes | `evaluable_genomes` |
| `uncertainty_kind` | enum | `one_sided_hypergeometric_p` | - | constant (native `null_model`) |
| `sampling_basis` | enum | `independent_rows|correlated_rows` | - | from `independent_row_test_eligible` |

(4) Prose left out: `null_model`, `multiple_comparison_adjustment`, `normalization`, `interpretation` (fixed
constants: carried by `uncertainty_kind`, `sampling_basis`); per-row free fields (rows stay in the sheet).

### A5. `a103_channel_v1` + channel attachment — a native context channel (external score) between two endpoints

(1) A context score from a native resource channel between the target-linked left endpoint and a right endpoint,
kept only when both native ids are bound to canonical sequences.

(2) Native (schema module is outside the searched folders; fields as `attachments.py`/`publication.py` read them):
`native_value` (number [0, 1] or null, required), `channel` (text), `left_native_id`, `right_native_id` (ids),
`left_reference_ref`, `right_actual_ref`, `right_reference_ref`, `source_ref` (record_refs). Attachment: `state`
(enum `evaluated|unresolved`), `score` (= native x min endpoint factor), `endpoint_links[].factor`,
`.identity_distance`, `.coverage` (numbers [0, 1]).

(3) Finding `evidence_type = context_channel_association`. Strength features:

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `score_lower` = `score_upper` | number | [0, 1] or null | channel score x endpoint factor | attachment `score` |
| `native_raw_value` | number | [0, 1] or null | the resource's own channel score | `native_value` |
| `channel` | enum | the resource's channel names (owner: fix the list) | - | native `channel` |
| `endpoints_bound` | boolean | | - | absence of `native_endpoint_to_canonical_sequence_identity` in `missing` |
| `min_endpoint_factor` | number | [0, 1] or null | | min `endpoint_links[].factor` |
| uncertainty block | - | none reported by the native channel: `uncertainty_kind = not_reported`, others null | | |

(4) Prose left out: `interpretation` (constant).

### A6. `a103_contrast_v1` + contrast attachment — supporting versus opposing context comparison

(1) The difference between the best qualified supporting context and the best qualified opposing context for a named
function, with matched policy and scope; it earns no credit (score is null).

(2) Native: `supporting_source_refs`, `opposing_source_refs`, `incompatibility_witness_refs` (record_refs),
`function_ref` (record_ref). Attachment: `state` (enum `evaluated|unresolved`), `qualified_panel`:
`supporting_context_bounds`, `opposing_context_bounds` (2 numbers [0, 1] each), `contrast` (number [0, 1] or null),
`contrast_bounds` (2 numbers [0, 1]), `comparison_state` (enum `incomparable_or_unresolved|discriminating_index|not_established_discriminating`).

(3) Finding `evidence_type = context_contrast`. Strength features:

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `contrast` | number | [0, 1] or null | association index difference | `qualified_panel.contrast` |
| `contrast_lower`, `contrast_upper` | number | [0, 1] | same | `qualified_panel.contrast_bounds` |
| `comparison_state` | enum | three values above | - | `qualified_panel.comparison_state` |
| `supporting_comparison_count` | integer | >= 0 | measurements | `len(supporting_source_refs)` |
| `opposing_comparison_count` | integer | >= 0 | measurements (the control arm) | `len(opposing_source_refs)` |
| `function_ref` | annotation | function id | - | native `function_ref` |
| uncertainty block: magnitude / kind | number / enum | `contrast_upper - contrast_lower` / `bound_interval` | | |

(4) Prose left out: both `interpretation` strings (constants).

### A7. `a103_neighborhood_v1` + organization attachment — one measured neighborhood around the target locus

(1) The CDS inventory and regulatory features in a flank window around the bound locus; no association score
("requires explicit comparative association for controller credit").

(2) Native: `cds[]` with `exact_boundaries` (bool), `strand`, `focal` (bool), `translation.status` (enum);
`regulatory_features[]`; `gene_order_reference_axis` (ints); `raw_neighborhood.window.wrap_permitted` (bool),
`raw_neighborhood.source.length` (int bp). Attachment: `state` (= target link state), `score` null.

(3) Finding `evidence_type = single_locus_organization`. Features (no strength scalar, since score is null):
`neighborhood_cds_count` (int, `len(cds)`), `exact_cds_count` (int, count `exact_boundaries`),
`regulatory_feature_count` (int), `circular_window` (bool, `wrap_permitted`), `target_link_state` (enum).
Owner: decide whether this is returned as a finding at all, since it never moves credit.

(4) Prose left out: `source_labels_are` (constant); CDS `qualifiers` (source annotation text: gene names and
products are annotations and may be kept as annotation fields if a parent needs them; nothing below does).

### A8. Operand sheets feeding attribution: `a103_locus_binding_v1`, `a103_detection_v1`

Locus binding fields: `selection_status` (enum `selected|not_found|ambiguous`), `record_length` (int bp), `topology`
(text from source; enum `linear|circular|unknown`), `translation.status`, `.qualification`, `.exact_boundaries`,
`native_input_placement.state` (enum `unique|ambiguous|not_found`), `.candidate_limit_reached` (bool),
`organism` (annotation). Detection fields: `present` (bool or null), `native_search_complete` (bool),
`all_actual_cds_in_search` (bool). These are not findings; they set `target_link_*`, `locus_application` and the
recurrence `partner_*` features. `interpretation`, `selection_scope` (constants) are left out.

### A9. Credit projector `A103ContextCredit.read_details` and `annotation_contribution`

(1) The episode-level reading: per target, the maximum attached score per region cell, length-weighted; and the
annotation scalar with its direction.

(2) Fields: `credit` (number [0, 1]) — not restated; per target `target_sheets[t].status` (enum
`partial_attribution|attributed_context_received|unresolved_attribution|no_received_context_association`),
`.value` (number [0, 1]), `.assigned_length` (int, residues or nt), `.cells[]` (`start`, `end` ints, `value` [0, 1]),
`.unresolved_variant_groups` (ids), `.pending_measurement_refs` (record_refs); `source_contribution_count` (int);
annotation scalar `status` (enum `available|unavailable`), `direction` (enum `support|measured_neutral|unknown`;
`opposition` is unreachable since values are in [0, 1]), `missing_inputs` (codes:
`no_received_applicable_supporting_assessment`, `assessed_observation_has_no_received_applicable_supporting_measurement`,
`no_received_native_measurement`, `unresolved_native_attribution`).

(3) Episode-level finding features (the head's return, section C):

| feature | type | range / values | unit | code |
|---|---|---|---|---|
| `attribution_state` | enum | the four `target_sheets` statuses | - | status of the assigned target (worst over targets if several) |
| `source_contribution_count` | integer | >= 0 | attached scored measurements | `source_contribution_count` |
| `evidence_type_counts` | one integer per `evidence_type` value (6 fields, e.g. `conserved_neighborhood_count`) | >= 0 | contributions | count `source_contributions` by attachment `policy` |
| `covered_fraction` | number | [0, 1] | fraction of assigned length with cell value > 0 | sum of lengths of cells with value > 0 / `assigned_length` |
| `pending_measurement_count` | integer | >= 0 | measurements | `len(pending_measurement_refs)` |
| `ambiguous_variant_group_count` | integer | >= 0 | dependency groups | `len(unresolved_variant_groups)` |
| `annotation_direction` | enum | `support|measured_neutral|unknown` | - | scalar `direction` |
| `annotation_missing_input` | enum | the four codes above, or `none` | - | first of `missing_inputs` |

(4) Prose left out: `interpretation`, `aggregation`, `missing` of `as_record` (constants); `assessment_qualifications`
(from the A103 assessment dependency module; text stays there, its count can be `assessment_count`).

### A10. Non-scientific projectors (not findings)

`ProgressInformationCredit` (monitoring units) and `project_practical_credit` (requirement keys) are credit for
execution/monitoring episodes; their returns are operational and out of the finding scope. `tool_grading_artifacts`
is custody only.

## B. Literature episodes: no sheet to read from

The seven literature episodes (`published_evidence_assessment` and its descendants) return model-written prose
(`interpretation`, `source_claim`, `source_subject`, `qualification`, `target_correspondence`, `reason`,
`relevance`, `statement`, `location`, `quote`, `approach`, `outcome`). A103 has no literature grading sheet, so code
cannot read strength features from one. Two options for the owner:

- (D-a, proposed) Keep the prose inside the episode as its report record and return only controlled fields the
  model fills from a closed form that code validates: `finding_ref` (record_ref to the report record),
  `evidence_type` (the six values plus `none_applicable`), `target_correspondence` (enum
  `established|unresolved|not_applicable`, already the declared meaning of the text field), `reported_genome_count`
  (int >= 0 or null), `reported_gap_bp` (int or null, bp), `reported_intervening_genes` (int >= 0 or null),
  `reported_orientation` (enum `same|convergent|divergent|unknown`), `reported_fusion` (bool or null),
  `reported_cooccurrence` (bool or null), `subject_annotation` (annotation: the source's gene/locus id or name) and
  the counts and record refs below. These are model-declared, not graded: they carry no strength.
- (D-b) Add an A103 literature subscoring sheet. Not proposed here.

Mapping of left-out prose: `source_claim` -> `evidence_type` + the `reported_*` fields; `source_subject` ->
`subject_annotation`; `target_correspondence` / `qualification` -> `target_correspondence` enum;
`location` / `quote` / passage windows -> `offset`, `limit` (ints, bytes) + `source_ref` (record_ref), already
controlled; `relevance` / `reason` -> `merits_examination` (bool, already controlled); `approach` / `outcome` ->
the search outcome records' refs; `interpretation` -> `finding_ref`.

## C. What each parent decides next and the smallest return it needs

| child -> parent | parent's next decision (task.py decide/action, msg_to_child) | smallest controlled return (besides credit) |
|---|---|---|
| A103 head -> root | Which axis to commission next (objective, purpose, thought pattern, tools), and whether to come back to A103 for an outstanding job (`axis_view`: credit, `latest_finding`, `job_handoff_refs`) | `attribution_state` (enum), `source_contribution_count` (int), `pending_measurement_count` (int), `evidence_type_counts` (6 ints, picks the thought pattern/tools next time), `finding_ref` (record_ref), `committed_record_refs` (record_refs, already selected by root; carries job handoffs) |
| recursive A103 head -> A103 head | Whether to commission another narrower `gene_context_evidence` child, which scope, and which held records to pass as `evidence_refs` (its `msg_to_child` reads only `committed_record_refs`) | `committed_record_refs` (already required), `attribution_state`, `pending_measurement_count`, `evidence_type_counts` |
| published_evidence_assessment -> A103 head | Whether to commission a native measurement (bind/neighborhood/compare/cooccurrence) on loci the literature names, or literature again, and which records to pass to that child | `assessed_source_refs` (record_refs: sources whose correspondence is established), `established_correspondence_count` (int), `unresolved_correspondence_count` (int), `evidence_type` per assessed source as one int count per type, `finding_ref` |
| evidence_search_strategy_improvement -> published_evidence_assessment | Whether to relaunch with other `prior_search_refs` (its `msg_to_child` takes only those) or report | `candidate_source_refs` (record_refs), `candidate_count` (int); productivity is the credit, nothing else |
| source_relevance_assessment -> evidence_search_strategy_improvement | Which further `search_result_refs` to send (its `child_operands` takes a non-empty list of held refs) | `merits_examination_source_refs` (record_refs), `judged_source_count` (int), `merits_examination_count` (int), `established_correspondence_count` (int) |
| source_evidence_examination -> source_relevance_assessment | Whether to examine another source or the same source in another representation, and which `prior_delivery_refs` to pass (`child_operands`) | `target_correspondence` (enum), `evidence_type` (enum incl. `none_applicable`), `reading_count` (int), `finding_ref` (record_ref, usable as a prior delivery) |
| table_evidence_extraction / passage_evidence_extraction / source_coverage_improvement -> source_evidence_examination | Which next `selection` (table rows `offset`/`limit` on a `sheet_key`, or a byte window) to commission, or report | `target_correspondence` (enum), `evidence_type` (enum incl. `none_applicable`), `covered_offset`, `covered_limit` (ints, bytes or rows: the extent read, so the next selection does not repeat it), `finding_ref` |

Notes for the owner:

- The head's `read_from_child` and `final_to_parent` today pass `finding` whole (prose); the root shows it as
  `latest_finding`. Under the proposal the head's `finding` becomes the A9 feature set plus `finding_ref`.
- The A103 execution children (`execution_*`, `hpc_*`, `resource_*`) return operational findings, not
  investigation findings; they are outside this table.
- Channel `channel` vocabulary and recurrence `order` values beyond `any|left_before_right` are fixed outside the
  searched folders; confirm them.
