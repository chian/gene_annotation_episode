# A102 (structural_homology_evidence): investigation finding features

A proposal for the owner to correct line by line. No code was changed and no Python was run.

An investigation finding is a set of fields. Each field has a controlled answer set that code can validate: a
number with a range and unit, an integer count, a boolean, a value from a fixed vocabulary, or a record reference.
There is no open field, and no field holds several pieces of evidence. Credit is the productivity signal, and no
finding field restates it.

## 0. What was read, and where the brief did not match the tree

| # | Fact | Where |
|---|---|---|
| 0.1 | Corrected 19 November 2026 (pilot 102): A102 has a literature grading sheet, `literature_structure_cells` (grader `structural_feature_geometry`, provider `literature.experimental.structure`, prompt `STRUCTURE_TASK`; `LOST_CONTENT_a102.md` rows 1 to 13). When this table was first written its library had been deleted with the old root and the folders `literature/{forms,calculations,inputs,storage}/structural_homology_evidence/` did not exist; they now hold the grader's types, calculations, input reader and storage, and `literature/readers/structural_homology_evidence/literature_structure_cells.py` reads the finding features of section 2.13 from the saved sheet. | folder listing, `git show 97308b94c:.../root/a102/literature_structure_*.py` |
| 0.2 | The A102 scoring sheets are native structural sheets. They are built in `grading/structural_homology_evidence/scoring.py` (geometry, comparison grade, feature sheet, contrast panel, native target sheet). The host attaches them to the target in `records/structural_homology_evidence/attachments.py` (per-producer attachment sheets). They are projected to credit in `grading/structural_homology_evidence/credit.py`: `A102StructuralCredit` plus five task credits. | those three files |
| 0.3 | A102's literature-side scientific record has no sheet. It is the `assessment` record with its typed `investigation_finding`, defined in `records/structural_homology_evidence/domain.py` (`RECORD_SCHEMAS['assessment']`, `SOURCE_CLAIM`, `FINDING_QUALIFICATIONS`, `FINDING_WITHDRAWAL_REASONS`). Its projector is `findings/structural_homology_evidence/investigation_progress.py` (`ScientificFindingProgress`). Nearly all of it is already controlled (section 2.10). | domain.py, findings/ |
| 0.4 | Three files outside the named folders were read for single definitions the A102 files import. `forms/protein_structure/structural_evidence.py` gives the task names and which projector each task uses. `tools/structural_homology_evidence/evidence_operations.py` `catalog()` gives the tool input schemas that become the sheet inputs. `literature/grading/literature_task_credit.py` gives `lead_schema` and `screening_schema`. Nothing else outside the named folders was opened. The head's parent (`root/`) was not read, so the decision rows for the head in section 4 are inferred from the head's own credit, not from root's `task.py`. | as listed |
| 0.5 | The scoring sheets are plain dicts built by code, not JSON schemas. In this document, "required" means the code writes the key on every sheet. "Conditional" means it appears only on some branch. | scoring.py, attachments.py |
| 0.6 | The sheets do not depend on any function hypothesis. B, F, E and the trait and contact kernels are measurements of correspondence. A measurement is tied to a proposed annotation only through an `assessment` whose `relation` is `strengthens` and whose transfer status is `established` (`A102StructuralCredit._annotation_measurements`, `_assessed_a102_attachments`). So a finding for an annotation is a sheet feature set plus the assessment features of section 2.10. | credit.py |
| 0.7 | There are two name mismatches between a tool input and the scoring code. I did not read the mapping code, so these are flags for the owner to check, not confirmed defects. (a) `structure.feature_geometry` declares feature `state` in `measure`, `unresolved`, `established_absent`, `established_incompatible`, while `scoring.feature_sheet` accepts `measured`, not `measure`. (b) `structure.contrast` takes `incompatibility_witness_refs`, while `attachments.refresh` and `contrast_panel` read `contrast_witness_refs`. | evidence_operations.py, scoring.py, attachments.py |

## 1. Proposed `evidence_type` vocabulary for A102

| Value | Meaning | Sheet it comes from |
|---|---|---|
| `native_structural_correspondence` | Measured CA correspondence between a target-bound model and a reference model: RMSD kernel times symmetric coverage (B) | `a102_comparison_grade_v1`, its direct attachment, and `a102_native_sheet_v1` (2.1-2.3) |
| `reference_fold_attribution` | Reference/reference geometry (Y/Z) transferred to the target X through a native or sequence map; inferred, not measured on the target | attachment `reference_fold_native_map_and_local_distance_v1` (2.4) |
| `feature_geometry` | Distances of source-defined physical feature anchors under the comparison transform (F, E) | `a102_feature_sheet_v1` and attachment `feature_geometry_local_scaffold_v1` (2.5) |
| `functional_contrast` | Best supporting E minus best witnessed incompatible E for one function | `a102_contrast_sheet_v1` and attachment `contrast_from_qualified_local_features_v1` (2.6) |
| `local_trait` | Conservation or change of defined reference residues, roles, motifs, regions or geometry constraints at mapped target positions | attachment `local_trait_<kind>_v1` (2.7) |
| `interface_contact` | Source-defined interchain contact distances in one coordinate model, attributed to the target | `a102_interface_constraint_v1` and attachment `interface_required_components_local_contacts_v1` (2.8) |
| `reported_comparison` | Structural comparison reported by an external source; earns no native B | attachment `reported_subject_scope_and_specific_distance_v1` (2.9) |
| `source_assessment` | A retained typed source claim, assessed against the proposed annotation | `assessment.investigation_finding` (2.10) |
| `experimental_structure_geometry` | Conditional geometry and local fit of an experimentally determined model a source supplies, graded by the literature grader `structural_feature_geometry`; kept apart from the native comparative sheets and never combined with them | `literature_structure_cells` (2.13) |
| `no_applicable_evidence` | The examined spans contain no applicable evidence. This is the only outcome with no sheet and no assessment. | `evidence_processing.kind` (2.11) |

The first eight values correspond one to one with the producers `structure.align`/`discover`/`compare_protein_structures`,
`structure.reference_align`, `structure.feature_geometry`, `structure.contrast`, `structure.reference_traits`,
`structure.interface_geometry`, `structure.reported_comparison`, and the reasoning commit. The model binding
(`structure.bind`, policy `model_sequence_entity_binding_v1`) is an operand, not evidence. It is left out of the
vocabulary (2.12). If the owner wants the `experimental_model_identity` task to return a finding, a `model_binding` value
would be added.

Fields shared by every finding below:

| # | Finding field | Read from | Type | Validator | Keep |
|---|---|---|---|---|---|
| T | `evidence_type` | which sheet or record the finding is read from | vocabulary | section 1 | core |
| R0 | `sheet_ref` | the `source_ref` of the published sheet (native publication, derived publication or tool attachment source) | record ref | source record of the provider named per section | core |
| R1 | `target_ref` | sheet `target_ref` | record ref | input/read_subject record in the episode scope | core |

## 2. Sheet families, fields, proposed finding, fields left out

### 2.1 Native comparison grade (`a102_comparison_grade_v1`, version `a102_rmsd_2A_features_1A_v1`)

**What it grades:** one target model/reference model CA correspondence. It gives RMSD over paired CA atoms, symmetric extent
coverage, and B = coverage x 1/(1+(RMSD/2 A)^2). Producer `native.a102.structural_comparison`; grader
`a102_native_alignment_grader_v1`.

Native input (`a102_native_alignment_v1`), all required unless marked:

| Field | Type | Answer set |
|---|---|---|
| `supplied_length`, `reference_length` | integer | > 0 (residues) |
| `target_scope` | [integer, integer] | 0 <= start < end <= `supplied_length` |
| `target_positions`, `reference_positions` | list of integer | injective, inside scope or reference |
| `distances_A` | list of number | >= 0, A; same length as the positions |
| `target_ref`, `reference_ref`, `variant_ref`, `comparison_group` | string ids | non-empty |
| `primary` | boolean | |
| `atom_selection` | const | `CA` |
| `target_model.origin`, `reference_model.origin` | enum | `experimental`, `predicted`, `supplied_unknown` |
| `producer` | enum | `US-align`, `Foldseek`, `compare_protein_structures` (keys of `DIRECT_PRODUCERS`) |
| `distance_rounding_bounds_A` | list of number or absent | >= 0, A (conditional) |
| `*_sha256`, `target_selection`, `reference_selection` | hashes and selections | identity only |

Grade fields added (`components` from `geometry()`):

| Field | Type | Answer set | Required |
|---|---|---|---|
| `components.n_pairs` | integer | 0 to min(target, reference length) | yes |
| `components.target_length`, `components.reference_length` | integer | > 0 | yes |
| `components.target_coverage`, `components.reference_coverage`, `components.symmetric_coverage` | number | 0..1, fraction | yes |
| `components.rmsd_A` | number or null | >= 0, A; null when `n_pairs` = 0 | yes |
| `components.rmsd_kernel` | number or null | 0..1 | yes |
| `components.global_scale_A` | const | 2.0 | yes |
| `components.B` | number | 0..1, dimensionless | yes |
| `components.status` | enum | `measured`, `no_paired_coordinates` | yes |
| `components.rmsd_rounding_interval_A` | [number, number] | A | conditional |
| `components.B_rounding_interval` | [number, number] | 0..1 | conditional |
| `components.precision_status` | const | `conditional_native_print_rounding_bound_only_not_model_uncertainty` | conditional |
| `eligible` | boolean | false for a self copy | yes |
| `exclusion` | enum or null | `self_structure_copy`, `self_coordinate_copy` | yes |
| `function_specific.status` | const | `not_assessed` (F, E always null here) | yes |
| `interpretation` | const | `native_structural_correspondence_not_function_probability` | yes |

Direct attachment (`direct_native_geometry_v1`, made by `attachments._direct`): `state` const `direct`; `score` = B;
`entity_attribution.sequence_distance_on_mapped_residues` number 0..1; `construct_changes` list (its length is a
count); `origin`, `reference_origin` enum as above.

**Proposed finding** (one per received comparison):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `native_structural_correspondence` | | core |
| N1 | `correspondence_B` | `components.B` | number | 0..1 | dimensionless | core |
| N2 | `rmsd` | `components.rmsd_A` | number or null | >= 0 | A | core |
| N3 | `paired_residue_count` | `components.n_pairs` | integer | >= 0 | residues | core |
| N4 | `symmetric_coverage` | `components.symmetric_coverage` | number | 0..1 | fraction | core |
| N5 | `target_coverage` | `components.target_coverage` | number | 0..1 | fraction | optional |
| N6 | `reference_coverage` | `components.reference_coverage` | number | 0..1 | fraction | optional |
| N7 | `measurement_status` | `components.status` | vocabulary | `measured`, `no_paired_coordinates` | | core |
| U1 | `rmsd_rounding_low`, `rmsd_rounding_high` | `components.rmsd_rounding_interval_A` | number or null | >= 0, low <= high | A | optional |
| U2 | `uncertainty_kind` | `components.precision_status` present? | vocabulary | `print_rounding_bound_only`, `unreported` | | core |
| E1 | `eligible` | `eligible` | boolean | | | core |
| E2 | `exclusion` | `exclusion` | vocabulary | `self_structure_copy`, `self_coordinate_copy`, `none` | | core |
| E3 | `primary_variant` | `primary` | boolean | | | core |
| M1 | `target_model_origin` | `target_model.origin` | vocabulary | `experimental`, `predicted`, `supplied_unknown` | | core |
| M2 | `reference_model_origin` | `reference_model.origin` | vocabulary | same | | core |
| M3 | `producer` | `producer` | vocabulary | `US-align`, `Foldseek`, `compare_protein_structures` | | optional |
| M4 | `construct_change_count` | `len(direct attachment construct_changes)` | integer | >= 0 | residues | optional |
| M5 | `mapped_sequence_distance` | `entity_attribution.sequence_distance_on_mapped_residues` | number | 0..1 | fraction | optional |
| R2 | `reference_ref` | `reference_ref` | record ref | received binding source | | core |

### 2.2 Native target sheet (`a102_native_sheet_v1`, completed by `A102StructuralCredit.read_details`)

**What it grades:** for one target and its required regions, the best eligible primary B per region (native or
attributed reference fold). The value is the geometric mean over the regions. The head's credit is this value,
weighted by scope length over the targets.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `value` | number | 0..1; 0 when any region is 0 | yes |
| `native_value` | number | 0..1, value before attribution | yes (credit) |
| `regions[].start`, `regions[].end` | integer | residues | yes |
| `regions[].value`, `regions[].native_value` | number | 0..1 | yes |
| `regions[].comparisons[]` | geometry rows of 2.1 | | yes |
| `regions[].attributed_comparisons[]` | `{value, applicability_factor, attribution_kind}` | 0..1, 0..1, const `reference_geometry_inference` | yes (credit) |
| `excluded[].reason` | enum | `self_structure_copy`, `self_coordinate_copy` | yes |
| `comparison_count` | integer | >= 0 | yes |
| `status` | enum | `derived`, `not_observed`, `attributed_reference_geometry`, `unresolved_attribution` | yes |
| `unresolved_reference_variants` | list of group ids | length is a count | yes (credit) |
| `function_specific_index.status`, `full_target_index.status` | const | `not_assessed` | yes |
| credit `source_contribution_count` | integer | >= 0 | yes |

**Proposed finding** (one per target, per annotation when the commission names one):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `native_structural_correspondence` | | core |
| S1 | `target_correspondence` | `value` | number | 0..1 | dimensionless | core |
| S2 | `target_native_correspondence` | `native_value` | number | 0..1 | dimensionless | optional |
| S3 | `sheet_status` | `status` | vocabulary | the four values above | | core |
| S4 | `region_count` | `len(regions)` | integer | >= 1 | count | core |
| S5 | `regions_with_correspondence_count` | regions with `value` > 0 | integer | 0..S4 | count | core |
| S6 | `independent_comparison_count` | `comparison_count` (primary variants, one per `comparison_group`) | integer | >= 0 | count | core |
| S7 | `attributed_region_count` | regions with non-empty `attributed_comparisons` | integer | 0..S4 | count | optional |
| S8 | `excluded_comparison_count` | `len(excluded)` | integer | >= 0 | count | optional |
| S9 | `unresolved_variant_group_count` | `len(unresolved_reference_variants)` | integer | >= 0 | count | optional |
| S10 | `minimum_region_correspondence` | min of `regions[].value` | number | 0..1 | dimensionless | optional |

### 2.3 Reported-comparison and binding inputs do not change this sheet. See 2.9 and 2.12.

### 2.4 Reference-fold attribution (attachment `reference_fold_native_map_and_local_distance_v1`)

**What it grades:** the native geometry of reference model Y against reference Z, projected onto target X regions
through the X/Y map. Each region value = projected B x mean(local identity x native strength) over the mapped pairs.
Credit: `A102ReferenceAttributionCredit`, one per resolved assessed region.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `state` | enum | `excluded`, `evaluated_transfer`, `unresolved` | yes |
| `exclusion` | enum | `self_structure_copy`, `self_coordinate_copy`, `nonprimary_comparison` | conditional |
| `raw_score` | number | 0..1, the Y/Z B | yes |
| `score` | number or null | 0..1 | yes |
| `region_scores[].value` | number or null | 0..1 | yes |
| `region_scores[].applicability_factor` | number or null | 0..1 | yes |
| `region_scores[].mapped_pair_count` | integer | >= 0 | yes |
| `region_scores[].local_sequence_distance.{required_position_count, mapped_position_count}` | integer | >= 0 | yes |
| `region_scores[].local_sequence_distance.{identity_on_mapped, sequence_distance, target_coverage, native_strength}` | number or null | 0..1 | yes |
| `missing[]` | list of code | `native_correspondence_in_required_region`, `specific_target_reference_native_alignment`, `unambiguous_primary_native_correspondence` (from `sequence_link`) | yes |
| `reference_length` | integer | > 0 | conditional |

**Proposed finding** (one per attachment):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `reference_fold_attribution` | | core |
| F1 | `attribution_state` | `state` | vocabulary | `excluded`, `evaluated_transfer`, `unresolved` | | core |
| F2 | `attributed_correspondence` | `score` | number or null | 0..1 | dimensionless | core |
| F3 | `reference_correspondence_B` | `raw_score` | number | 0..1 | dimensionless | core |
| F4 | `region_count` | `len(region_scores)` | integer | >= 1 | count | core |
| F5 | `resolved_region_count` | regions with `value` not null | integer | 0..F4 | count | core |
| F6 | `minimum_applicability_factor` | min `applicability_factor` | number or null | 0..1 | fraction | core |
| F7 | `mapped_pair_count` | sum `mapped_pair_count` | integer | >= 0 | residue pairs | optional |
| F8 | `mean_local_sequence_distance` | mean `local_sequence_distance.sequence_distance` | number or null | 0..1 | fraction | optional |
| F9 | `missing_correspondence_count` | `len(missing)` | integer | >= 0 | count | optional |
| F10 | `exclusion` | `exclusion` | vocabulary | the three above, `none` | | core |
| F11 | `inference_kind` | constant | vocabulary | `inferred_from_reference_geometry` (the sheet's `interpretation`) | | core |

### 2.5 Feature geometry (`a102_feature_sheet_v1`, attachment `feature_geometry_local_scaffold_v1`)

**What it grades:** for one comparison and one `function_ref`, K source-defined physical feature anchors. Each kernel
is 1/(1+d^2), with d in A at a 1 A scale. F is the mean kernel and E = B x F. The attachment keeps only features whose
target site maps to the scaffold, and recomputes `score` and E from them. Credit: `A102FeatureGeometryCredit`, one per evaluated feature.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `features[].state` (sheet) | enum | `measured`, `established_absent`, `established_incompatible`, `unresolved` | yes |
| `features[].distance_A` | number | >= 0, A | when measured |
| `features[].coordinate_bound_A` | number or absent | >= 0, A | conditional |
| `features[].kernel` | number or null | 0..1 | yes |
| `features[].bounds` | [number, number] | 0..1 | yes |
| `K` | integer | >= 1 | yes |
| `F`, `E` | number or null | 0..1 | yes |
| `F_bounds`, `E_bounds` | [number, number] | 0..1 | yes |
| `n_unresolved` | integer | 0..K | yes |
| `uncertainty_status` | enum | `conditional_on_supplied_bounds`, `unreported` | yes |
| `eligible`, `primary` | boolean | | yes |
| `feature_scale_A` | const | 1.0 | yes |
| attachment `state` | enum | `evaluated`, `unresolved` | yes |
| attachment `score`, `E` | number or null | 0..1 | yes |
| attachment `features[].state` | enum | `evaluated`, `unresolved` | yes |
| attachment `features[].correspondence_route` | enum | `native_scaffold_map`, `specific_sequence_site_map` | yes |
| attachment `missing[]` | list of code | `construct_to_target_site_attribution`, `specific_local_structural_correspondence` | yes |

**Proposed finding** (one per feature sheet):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `feature_geometry` | | core |
| G1 | `feature_count` | `K` | integer | >= 1 | count | core |
| G2 | `evaluated_feature_count` | attachment features with `state` `evaluated` | integer | 0..K | count | core |
| G3 | `unresolved_feature_count` | `n_unresolved` | integer | 0..K | count | core |
| G4 | `established_absent_count` | sheet features with state `established_absent` or `established_incompatible` | integer | 0..K | count | core |
| G5 | `feature_fit` | attachment `score` (else sheet `F`) | number or null | 0..1 | dimensionless | core |
| G6 | `feature_support_E` | attachment `E` | number or null | 0..1 | dimensionless | core |
| G7 | `feature_support_E_low`, `feature_support_E_high` | `E_bounds` | number | 0..1, low <= high | dimensionless | core |
| G8 | `uncertainty_kind` | `uncertainty_status` | vocabulary | `conditional_on_supplied_bounds`, `unreported` | | core |
| G9 | `maximum_feature_distance` | max `features[].distance_A` over measured | number or null | >= 0 | A | optional |
| G10 | `site_mapped_by_sequence_count` | attachment features with route `specific_sequence_site_map` | integer | 0..K | count | optional |
| G11 | `eligible`, `primary_variant` | sheet | boolean | | | core |
| A1 | `function_ref` | `function_ref` | annotation (hypothesis id) | as given, not looked up | | core |
| R2 | `comparison_ref` | `comparison_ref` | record ref | comparison source of 2.1 | | core |

### 2.6 Functional contrast (`a102_contrast_sheet_v1`, attachment `contrast_from_qualified_local_features_v1`)

**What it grades:** for one function and scope, S = max supporting E, O = max witnessed incompatible E, and
A102_f = max(0, S - O). A102_f is null unless witnesses and opposing refs exist. Credit: `A102FunctionalContrastCredit`,
one per derived panel.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `S`, `O` | number or null | 0..1 | yes |
| `A102_f` | number or null | 0..1 | yes |
| `bounds` | [number, number] | 0..1 | yes |
| `status` | enum | `derived`, `support_only_or_unresolved_contrast` | yes |
| `supporting_refs`, `opposing_refs`, `contrast_witness_refs` | lists of refs | lengths are counts | yes |
| `profile` | const | `a102_rmsd_2A_features_1A_v1` | yes |

**Proposed finding:**

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `functional_contrast` | | core |
| C1 | `contrast_value` | `A102_f` | number or null | 0..1 | dimensionless | core |
| C2 | `support_value` | `S` | number or null | 0..1 | dimensionless | core |
| C3 | `opposition_value` | `O` | number or null | 0..1 | dimensionless | core |
| C4 | `contrast_low`, `contrast_high` | `bounds` | number | 0..1, low <= high | dimensionless | core |
| C5 | `contrast_status` | `status` | vocabulary | `derived`, `support_only_or_unresolved_contrast` | | core |
| C6 | `supporting_comparison_count` | `len(supporting_refs)` | integer | >= 0 | count | core |
| C7 | `opposing_comparison_count` | `len(opposing_refs)` | integer | >= 0 | count | core |
| C8 | `contrast_witness_count` | `len(contrast_witness_refs)` | integer | >= 0 | count | optional |
| A1 | `function_ref` | `function_ref` | annotation | as given | | core |

### 2.7 Local trait (attachment `local_trait_<kind>_v1`, producer `structure.reference_traits`)

**What it grades:** whether reference-defined positions keep the allowed symbols or chemical role at mapped target
positions. For `geometry_constraint`, the match is multiplied by the feature kernel. Credit: `A102LocalTraitCredit`, one per
resolved trait.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `trait_kind` | enum | `residue_identity`, `chemical_role`, `motif`, `region_identity`, `geometry_constraint` | yes |
| `state` | enum | `unresolved`, `evaluated_geometry`, `conserved`, `changed` | yes |
| `score` | number or null | 0..1 | yes |
| `trait_match` | number or null | 0..1 | yes |
| `cell_scores[]` | list of 0, 1 or null | | yes |
| `bounds` | [number, number] | 0..1 | yes |
| `raw_geometry_kernel` | number or null | 0..1 | yes |
| `target_geometry.distance_A`, `.kernel` | number | >= 0 A; 0..1 | conditional |
| `target_geometry.target_model_origin` | enum | `experimental`, `predicted`, `supplied_unknown` | conditional |
| `local_sequence_distance.identity_distance` | number or null | 0..1 | yes |
| `local_sequence_distance.required_reference_positions`, `.mapped_positions` | integer | >= 0 | yes |
| `inference_kind` | enum | `measured_target_model_shape_trait`, `inferred_shape_trait`, `evaluated_target_sequence_trait` | yes |
| `missing[]` | list of code | `native_map_for_all_required_trait_positions`, `native_reference_feature_geometry`, plus the `sequence_link` codes | yes |
| `correspondence.route` | enum | `native_structural_residue_correspondence`, `native_structure_with_specific_sequence_site_evidence`, sequence-link routes | conditional |
| request `chemical_role` | enum or null | `acidic`, `basic_KR`, `aromatic`, `hydroxyl`, `amide`, `sulfur`, `small` | yes |

**Proposed finding** (one per trait):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `local_trait` | | core |
| L1 | `trait_kind` | `trait_kind` | vocabulary | five values above | | core |
| L2 | `trait_state` | `state` | vocabulary | four values above | | core |
| L3 | `trait_score` | `score` | number or null | 0..1 | dimensionless | core |
| L4 | `trait_score_low`, `trait_score_high` | `bounds` | number | 0..1 | dimensionless | core |
| L5 | `required_position_count` | `local_sequence_distance.required_reference_positions` | integer | >= 1 | residues | core |
| L6 | `mapped_position_count` | `local_sequence_distance.mapped_positions` | integer | 0..L5 | residues | core |
| L7 | `changed_position_count` | count of `cell_scores` equal to 0 | integer | 0..L6 | residues | core |
| L8 | `inference_kind` | `inference_kind` | vocabulary | three values above | | core |
| L9 | `chemical_role` | request `chemical_role` | vocabulary | seven roles, `none` | | optional |
| L10 | `target_geometry_distance` | `target_geometry.distance_A` | number or null | >= 0 | A | optional |
| L11 | `target_model_origin` | `target_geometry.target_model_origin` | vocabulary | origins, `not_measured` | | optional |
| R3 | `target_feature_ref` | `target_feature_ref` | record ref | feature record | | core |

### 2.8 Interface contact (`a102_interface_constraint_v1`, attachment `interface_required_components_local_contacts_v1`)

**What it grades:** source-defined interchain contacts in one coordinate model. Each kernel is
1/(1+max(0, d - max_d)^2). `raw_score` is the mean kernel. The attached `score` = `raw_score` x min component applicability. Credit:
`A102InterfaceContactCredit`, one per resolved assessed contact.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `contacts[].maximum_distance_A` | number | > 0, A | yes |
| `contacts[].distance_A` | number or null | >= 0, A | yes |
| `contacts[].kernel` | number or null | 0..1 | yes |
| `raw_score` | number or null | 0..1 | yes |
| `assembly_context` | const | `same_coordinate_model_biological_assembly_and_partner_presence_unestablished` | yes |
| attachment `state` | enum | `evaluated_transfer`, `unresolved` | yes |
| attachment `score` | number or null | 0..1 | yes |
| attachment `component_links[].local_applicability` | number or null | 0..1 | yes |
| attachment `missing[]` | list of code | `attributed_partner_identity`, `construct_to_target_interface_site_attribution`, `interface_component_0_local_map`, `interface_component_1_local_map`, `native_contact_atoms`, plus `sequence_link` codes | yes |

**Proposed finding:**

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `interface_contact` | | core |
| I1 | `contact_count` | `len(contacts)` | integer | >= 1 | count | core |
| I2 | `measured_contact_count` | contacts with `kernel` not null | integer | 0..I1 | count | core |
| I3 | `contacts_within_limit_count` | contacts with `distance_A` <= `maximum_distance_A` | integer | 0..I2 | count | core |
| I4 | `interface_fit` | `raw_score` | number or null | 0..1 | dimensionless | core |
| I5 | `attributed_interface_fit` | attachment `score` | number or null | 0..1 | dimensionless | core |
| I6 | `minimum_component_applicability` | min `component_links[].local_applicability` | number or null | 0..1 | fraction | core |
| I7 | `partner_identity_attributed` | `'attributed_partner_identity' not in missing` | boolean | | | core |
| I8 | `attribution_state` | attachment `state` | vocabulary | `evaluated_transfer`, `unresolved` | | core |
| I9 | `assembly_established` | constant false (the sheet's `assembly_context`) | boolean | always false today | | optional |

### 2.9 Reported comparison (attachment `reported_subject_scope_and_specific_distance_v1`)

**What it grades:** nothing new. It keeps a source-reported structural metric and maps the reported subject to the target
by sequence. `score` and `native_B` are always null. There is no credit class.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `reported_metric.metric_name` | enum | `RMSD`, `TM-score`, `DALI_Z`, `other` | yes |
| `reported_metric.metric_value` | number or null | finite | yes |
| `reported_metric.metric_unit` | string | open in the tool schema | yes |
| `reported_metric.matched_extent` | string | open | yes |
| `state` | enum | `unresolved`, `reported_on_target`, `evaluated_reported_transfer` | yes |
| `local_sequence_distance` (as 2.4) | numbers, integers | 0..1, >= 0 | conditional |
| `missing[]` | list of code | `actual_reported_subject_pair`, `structured_reported_and_target_regions`, `canonical_reported_subject_sequence`, plus `sequence_link` codes | yes |

**Proposed finding:**

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `reported_comparison` | | core |
| P1 | `reported_metric_name` | `metric_name` | vocabulary | four values | | core |
| P2 | `reported_metric_value` | `metric_value` | number or null | finite | per P3 | core |
| P3 | `reported_metric_unit` | `metric_unit` | vocabulary (proposed) | `angstrom`, `dimensionless`, `z_score`, `unknown` | | core |
| P4 | `reported_transfer_state` | `state` | vocabulary | three values | | core |
| P5 | `target_coverage` | `local_sequence_distance.target_coverage` | number or null | 0..1 | fraction | core |
| P6 | `sequence_distance` | `local_sequence_distance.sequence_distance` | number or null | 0..1 | fraction | optional |
| P7 | `matched_residue_count` | sum of `end - start` over `measured_regions` (structured input) | integer or null | >= 0 | residues | optional (replaces `matched_extent`) |

### 2.10 Source assessment (`assessment` with `investigation_finding`)

**What it grades:** one observation, whether a source passage, a structure-derived observation such as
`trait_conservation_index`, or a database row, assessed against the proposed annotation (`hypothesis_ref`). The literature chain
and the head's `reason` tool write these. Projector: `ScientificFindingProgress`, one unit per distinct retained
`finding_key`. The literature credit (2.11) counts answers built on them.

| Field | Type | Answer set | Required |
|---|---|---|---|
| `relation` | enum | `strengthens`, `weakens`, `mixed`, `does_not_discriminate` | yes |
| `applicability` | enum | `direct`, `transfer`, `contextual`, `scope_limited`, `incomparable` | yes |
| `extent_basis` | enum | `observed_extent`, `inferred_extent`, `context_allocation` | yes |
| `condition_refs`, `assumption_refs` | record refs | lengths are counts | yes |
| `target_footprint` | intervals or null | | no |
| `investigation_finding.source_claim.predicate` | enum | the 20 `PREDICATES` (`catalyzes`, `binds`, `feature_structure`, ...) | yes |
| `investigation_finding.source_claim.value` | ATOM | `number` {value, `unit_ref`, `bound` enum, `qualifier` const `approximate`, `uncertainty.magnitude` >= 0}, `enum` (`ENUM_VALUES`), `term_ref`, `reference`, `relation` | yes |
| `investigation_finding.source_claim.subject_refs`, `.context_refs` | record refs | | yes |
| `investigation_finding.qualification.kind` | enum | `none`, `measurement_does_not_establish_claim`, `different_source_subject`, `conditions_limit_transfer`, `alternatives_not_discriminated`, `prediction_not_measurement`, `assumption_not_established`, `confounding_unresolved` | yes |
| `investigation_finding.status` | enum | `retained`, `withdrawn` | yes |
| `investigation_finding.withdrawal_reason` | enum | `not_withdrawn`, `source_misread`, `wrong_subject`, `wrong_condition`, `wrong_unit`, `unsupported_claim`, `duplicate_information`, `superseded_evidence` | yes |
| `investigation_finding.same_source_claim_as_ref`, `.replaces_refs` | record refs | | yes |
| observation `kind` | enum | `OBSERVATION_KINDS` (19 values, including `structure_match`, `comparison`, `biochemical_assay`) | yes |
| observation `anchor`, `visual_anchor` | object or null | presence only | yes |

**Proposed finding** (one per current assessment):

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `source_assessment` | | core |
| R4 | `assessment_ref` | assessment id | record ref | assessment record | | core |
| A2 | `relation` | `relation` | vocabulary | four values | | core |
| A3 | `applicability` | `applicability` | vocabulary | five values | | core |
| A4 | `extent_basis` | `extent_basis` | vocabulary | three values | | core |
| A5 | `claim_predicate` | `source_claim.predicate` | vocabulary | `PREDICATES` | | core |
| A6 | `claim_value_kind` | `source_claim.value.type` | vocabulary | `number`, `enum`, `term_ref`, `reference`, `relation` | | core |
| A7 | `claim_value_number` | `source_claim.value.value` when number | number or null | finite | `unit_ref` | optional |
| A8 | `claim_value_bound` | `source_claim.value.bound` | vocabulary | four bounds, `none` | | optional |
| A9 | `claim_uncertainty_magnitude` | `source_claim.value.uncertainty.magnitude` | number or null | >= 0 | `unit_ref` | optional |
| A10 | `claim_value_approximate` | `source_claim.value.qualifier == 'approximate'` | boolean | | | optional |
| A11 | `qualification_kind` | `qualification.kind` | vocabulary | eight values | | core |
| A12 | `finding_status` | `status` | vocabulary | `retained`, `withdrawn` | | core |
| A13 | `withdrawal_reason` | `withdrawal_reason` | vocabulary | eight values | | core |
| A14 | `observation_kind` | observation `kind` | vocabulary | `OBSERVATION_KINDS` | | core |
| A15 | `source_anchored` | observation `anchor` or `visual_anchor` not null | boolean | | | core |
| A16 | `condition_count`, `assumption_count` | `len(condition_refs)`, `len(assumption_refs)` | integer | >= 0 | count | optional |
| A17 | `claim_value_enum` | `source_claim.value.value` when enum | vocabulary | `ENUM_VALUES` | | optional |

Across the assessments an episode holds (the summary of the `ScientificFindingProgress` output, not one record):

| # | Finding field | How code computes it | Type | Validator | Unit |
|---|---|---|---|---|---|
| X1 | `retained_finding_count` | `retained_finding_count` (distinct `finding_key`) | integer | >= 0 | count |
| X2 | `strengthening_finding_count` | retained current findings with `relation` `strengthens` | integer | 0..X1 | count |
| X3 | `weakening_finding_count` | the same with `weakens` | integer | 0..X1 | count |
| X4 | `direct_finding_count` | the same with `applicability` `direct` | integer | 0..X1 | count |
| X5 | `independent_source_count` | distinct `FindingIdentity.source(observation.source_ref)` over retained findings | integer | 0..X1 | count |
| X6 | `inactive_count_by_reason` | one integer per reason: `typed_finding_not_recorded`, `finding_target_outside_scope`, `scientific_finding_withdrawn`, `finding_replaced`, `not_current_assessment_revision` | integer x 5 | >= 0 | count |
| X7 | `arm_agreement` | over the native sheet (2.2) and X2/X3: `agree` when S1 > 0 and X2 > 0 and X3 = 0; `conflict` when X3 > 0 and (S1 > 0 or X2 > 0); `single_arm` otherwise | vocabulary | `agree`, `conflict`, `single_arm` | |

X7 is a proposal for "agreement across arms". The current code computes nothing like it, so the owner should strike it or define it.

### 2.11 No applicable evidence, leads and screening (literature answers)

`evidence_processing` (head `task.py` `EVIDENCE_PROCESSING` and the literature `reason` tools): `kind` const
`no_applicable_evidence`, `reason` string (prose), `examined[]` {`source_ref`, `representation` enum `original`/`text`,
`start`, `end` integers}. Lead (`lead_schema`): `disposition` enum `relevant`/`not_relevant`, `relevance_rationale`
string (prose), `source_ref`, `subject_ref`, `proposed_annotation_ref`, `witness`. Screening (`screening_schema`): `disposition`
const `no_applicable_evidence`, `examined[]` spans, `annotation_support` const `not_assessed`.

| # | Finding field | Read from | Type | Validator | Unit | Keep |
|---|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `no_applicable_evidence` | | core |
| K1 | `examined_span_count` | `len(examined)` | integer | >= 1 | count | core |
| K2 | `examined_byte_count` | sum `end - start` | integer | >= 1 | bytes | optional |
| K3 | `examined_source_count` | distinct `examined[].source_ref` | integer | >= 1 | count | optional |
| K4 | `commissioned_spans_covered` | `screening_answers` non-empty (every requested span covered) | boolean | | | core |
| D1 | `relevant_lead_count` | leads with `disposition` `relevant` (the `verified_source_leads` answers) | integer | >= 0 | count | core (for lead tasks) |
| D2 | `lead_source_refs` | `source_ref` of the relevant leads | record refs | source records | | core (for lead tasks) |

### 2.12 Model binding (`structure.bind`, `model_sequence_entity_binding_v1`): operand, no finding proposed

Its controlled fields: `state` const `mapped_model`, `sequence_distance` number 0..1, `mapped_sequence_positions` integer,
`observed_coordinate_positions` integer, `origin` enum, and `construct_changes` (its length is a count). They reach the
findings above only as M1/M2/M4/M5 of 2.1. `qualifier` and `interpretation` are fixed strings.

### 2.13 Literature source geometry (`literature_structure_cells`, grader `structural_feature_geometry`)

Added 19 November 2026 (pilot 102). **What it grades:** for one deposited model a source supplies (exact model,
author chain, residue, insertion code, component, atom groups and alternate locations), a fixed geometry panel of
atom-group pairs with separate supporting (`positive_max_A`) and incompatible (`incompatible_min_A`) distance
criteria, and a fixed local-validation panel of residues joined to the matching validation entry and revision. Six
cells, each a conditional interval in [-1, 1] (`literature_structure_calculations.COMPONENTS`): `local_fit_index`
(weakest squared RSCC), `geometry_support_fraction`, `geometry_opposition_fraction`, and the products
`source_geometry_positive`, `source_geometry_opposing`, `source_geometry_signed` (local fit times the geometry
fractions, the shared factor kept). Values are conditional geometry only: not occupancy, causal isolation, target
correspondence or credit. One sheet row per cell (work table `structural_homology_literature_structure_cells`).

**Finding** (one per current sheet; code reads it in `literature_structure_cells.sheet_features`, each feature with
its validator in `FEATURES`):

| # | Finding field | Read from | Type | Validator | Unit |
|---|---|---|---|---|---|
| T | `evidence_type` | constant | vocabulary | `experimental_structure_geometry` | |
| R0 | `sheet_refs` | the saved sheet's `source` record (provider `literature.experimental.structure`) | record ref (one) | held sheet | |
| L1 | `<component>_lower`, `<component>_upper` (six components) | cell `lower`, `upper` | number | -1..1, lower <= upper | dimensionless |
| L2 | `<component>_status` | cell `status` | vocabulary | `populated` (lower = upper), `unavailable` | |
| L3 | `<component>_unavailable_reason` | cell `unavailable_reason` | vocabulary | `REASONS` of the calculations (13 codes), `none` | |
| P1 | `geometry_member_count` | `len(sheet.native_geometry)` | integer | >= 0 | atom-group pairs |
| P2 | `geometry_measured_count` | members with a measured distance | integer | 0..P1 | count |
| P3 | `local_member_count` | `len(extraction.native_local)` | integer | >= 0 | residues |
| P4 | `local_measured_count` | local residues with a joined RSCC | integer | 0..P3 | residues |
| V1 | `validation_binding` | `calculation_inputs.validation_binding` | vocabulary | `matching_entry_revision`, `entry_mismatch`, `revision_mismatch`, `binding_unreported`, `not_supplied` | |
| V2 | `operand_source_kind` | `extraction.source_kind` | vocabulary | `primary_source`, `retained_extraction`, `graph_extraction`, `synthetic_fixture` | |
| V3 | `experiment_assessed` | an `experiment_assessment` saved with the sheet | boolean | | |

Left out: the assessment's `scientific_question`, `conclusion`, `limitations` and `revision_reason` (model-written
text, kept in the sheet), the selectors and literal witnesses (identity, kept in the sheet), `conditional_on` and
the fixed metadata codes (constant per cell). A revised sheet (`revises_sheet_ref`) supersedes its predecessor; only
current sheets are returned. Every literature episode returns these features in `finding.structure_sheets`, one entry
per sheet, its own and its children's side by side; the head keeps them in its `experimental_structure_arm`
(`aggregation: none`), apart from its native credit view.

## 3. Fields left out because they are prose or open strings

| Sheet field | Why it is out | Controlled fields that carry what it meant |
|---|---|---|
| `interpretation` (grade, native sheet, attachments, credit output) | fixed sentence per sheet | `evidence_type`; F11, L8 |
| `whole_protein_function` (feature, interface, trait attachments) | fixed sentence | `evidence_type`; I9 |
| `entity_attribution.qualifier`, `entity_attribution.route` | fixed sentences | M4, M5 |
| `function_specific.reason`, `full_target_index.reason` | fixed codes, constant | nothing (always `not_assessed`) |
| `precision_status` | one fixed code | U2 |
| `assembly_context` | one fixed code | I9 |
| `missing[]` lists | code lists; the codes are fixed in code but some come from `sequence_link`, which I read only partly | F9, G3, I7, I8, L2, P4 counts and states. A per-code boolean is possible once the owner fixes the code list |
| feature `missing_reason`, `reason` (tool input); trait/contact definitions | model-written text | G3, G4 (state counts) |
| `structure.bind` `qualifications`, `origin_witness_refs` | text list; refs | M1, M2 |
| `structure.reported_comparison` `description`, `transfer_limits` | prose | P4, P5, P6 |
| `structure.reported_comparison` `matched_extent`, `metric_unit` | open strings | P7 (structured regions), P3 (proposed unit vocabulary) |
| `evidence_processing.reason`; each witness `quote` | prose | K1-K3; the outcome itself |
| lead `relevance_rationale`, `witness` text | prose | D1, D2 |
| literature `finding.interpretation`, `finding.qualification`, `passages[].statement`, `passages[].qualification`, table `readings[].locator`/`statement`/`qualification` | model-written paragraphs (they are all `final_to_parent` today) | the assessment features A2-A17 behind `assessment_ref`; K1-K4; D1-D2; passage `offset`/`limit` stay with the record |
| head `finding.interpretation`, `finding.qualification`, `qualification_of_credit`, `task` text | prose; `task` is a vocabulary (`A102:<task>`, 15 tasks) | `a102_task` vocabulary; S1-S10 and X1-X7 |
| `children[].slot` | a vocabulary (the 8 head slots), not prose | keep as vocabulary |
| `axis_components` | a record holding a restatement of credit (`{'A102': credit}`) | nothing (credit is never restated) |
| `source_contributions`, `tool_attachments`, `reference_attributions`, `selected_components`-like detail rows | whole rows | `sheet_ref`, and the counts above |
| hashes, `measurement_keys`-like ids, `native_input_sha256`, `comparison_group`, `variant_ref` | identity, not evidence | S6 (one per group), E3 |

## 4. What each parent decides next, and the smallest return it needs

Every A102 parent here chooses its next unit with the model (`decide` builds a `ModelRequest` from the summary), and
its yield controller alone stops it. A child's return enters the parent's summary through `read_from_child`. It then
counts toward the parent's credit only where the parent's `credit.py` reads it.

### 4.1 Investigation episodes

| Child (returns to) | What the parent decides next (its `task.py` decide/action and `msg_to_child`) | Smallest controlled return that decision needs |
|---|---|---|
| `table_evidence_extraction`, `passage_evidence_extraction`, `source_coverage_improvement` (to `source_evidence_examination`) | Whether to commission another reading of the same page (`literature_table`, `literature_ordered`, `literature_targeted`, each with its own `selection`), read with its own tools, commit reasoning, or report. Its credit merges the child leads (`source_leads`) for `verified_source_leads`; screening counts only its own spans; assessment answers count only assessments it holds. | credit; for leads: D1, D2; for screening: K1, K4; for assessment: `assessment_refs` (R4) with A2, A3, A11, A12, A14, A15 each. The assessment refs are needed because `assessment_answers` reads only held records, and the return passes no assessment ref today. |
| `source_evidence_examination` (to `source_relevance_assessment`) | Whether to commission another page (`literature_page`: `source_ref`, `representation`, `artifact_ref`, `prior_delivery_refs`), acquire or read more, or report | as above, plus `examined_source_count` (K3) so that the parent knows which pages produced nothing |
| `source_relevance_assessment` (to `evidence_search_strategy_improvement`) | Whether to commission another search (`literature_search`: `search_result_refs`, `question_context_refs`) or revise terms | credit; D1, D2 (the relevant leads it verified); `relevant_lead_count` against the number of `search_result_refs` assigned is the yield of that search |
| `evidence_search_strategy_improvement` (to `published_evidence_assessment`) | Whether to commission another strategy (`literature_strategy`: `question_context_refs`, `prior_search_refs`) | credit; D1, D2; the per-type count of assessments it holds (X1, X2, X3) |
| `published_evidence_assessment` (to the head, slot `literature`) | The head chooses among its own structure tools, another literature commission, an execution child, `reason` or `report`. Its credit for a finding-progress task (`ScientificFindingProgress`) counts only the assessments the head holds. For a comparative task (`A102StructuralCredit`), it counts only received native sheets linked by an assessment with `relation` `strengthens`. | credit; `assessment_refs` (R4) of current retained findings, each with A2, A3, A4, A5, A11, A12; X1-X3, X5; D1/D2 or K1/K4 per task kind. Without the refs, the head's credit cannot include the literature arm. |
| head `structural_homology_evidence` (self-commissioned, slot `structural_homology_evidence`, to the head) | Whether a `process_revise` alternative was productive and whether to launch another. Today it reads `structural_homology_evidence_results` and `committed_record_refs`. | credit; the target finding (S1, S3, S6), X1-X3; `committed_record_refs` (record refs); `sheet_ref` of the native target sheet |
| head (to `root`, outside the folders read) | Not read. The head's credit and `A102StructuralCredit.annotation_contribution` suggest that root weighs the A102 contribution per proposed annotation. | credit; per annotation: S1, S3, S5, S6; G6 and C1 when present; X1-X5, X7; `assessment_refs` and `sheet_ref` (record refs); the `a102_task` value |

### 4.2 Practical episodes (their findings are job facts, not evidence; listed because they return a finding)

| Child (returns to) | What the parent decides next | Smallest controlled return | Prose to drop |
|---|---|---|---|
| `execution_job_submission` (head `execution_launch`; `hpc_work_planning` launch) | Whether to acquire results, monitor, or relaunch: `read_from_child` reads `execution_handoff_refs` and `execution_completed` | credit; `execution_handoff_refs`; `execution_completed`; `new_handoff_count` (integer) | `finding.qualification` |
| `local_job_execution`, `hpc_job_execution`, `api_job_execution` (to an `execution_job_submission`) | The same: `handoff_refs`, `completed`, and, under `hpc_allocation_execution`, `result_refs` and `artifact_refs` | credit; `execution_handoff_refs`; `execution_result_refs`; `execution_completed`; `commands_run` (integer); failure count (integer) | `failures` text, `requested_job` record, `endpoint` (make it a vocabulary: `usable_handoff`, `completed_job_outputs`) |
| `resource_work_submission` (head `resource_launch`) | Whether a usable handoff exists to acquire from | credit; `execution_handoff_refs`; `usable_handoffs`, `identities` (integers) | `finding.qualification`, `adapter_facts` (open record) |
| `resource_result_acquisition` (head `resource_results`) | Whether data arrived or another acquisition is needed | credit; `handoff_state` as a vocabulary (`usable`, `unavailable`, ...); `handoff_count`; failure-code count | `interpretation` record, `adapter_facts` |
| `execution_result_acquisition` (head `execution_results`; `hpc_*` results) | Whether to run structure tools on the result refs or acquire again | credit; `execution_result_refs`; `execution_completed`; `results_acquired`, `windows_acquired`, `acquisition_failures` (integers); saved-sheet refs | `qualification`, `requested_paths`/`uncovered_paths` (use counts) |
| `execution_progress_assessment` (head `monitor`; `hpc_*` monitor) | Whether to wait, acquire results, or relaunch | credit; `monitoring_progress_refs`; `monitoring_execution_state` (vocabulary); `monitoring_result_available` (boolean); `monitoring_observed_at_unix_seconds` (number) | `qualification` |
| `hpc_work_planning` (head `hpc`) | Whether HPC results exist to grade | credit; `hpc_result_refs`; accepted and remaining obligation counts (integers); `plans_frozen`, `plans_closed`, `results_published` | `qualification`; `credit_components` (restates credit) |
| `hpc_resource_prediction`, `hpc_allocation_execution` (to `hpc_work_planning`) | `read_from_child` reads `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs` | credit; `hpc_model_ref` (record ref); `model_quality_improvement` (number); `hpc_result_refs`; accepted-obligation count | `qualification`; `hpc_credit` and `prospective_validation_credit` restate credit |

## 5. Points the owner must settle

| # | Point |
|---|---|
| P1 | Do the native sheets count as A102 "findings"? Today findings are assessments. The native sheets reach an annotation only through an assessment (0.6). The proposal returns both: the sheet features (2.1-2.9) and the linking assessment features (2.10). |
| P2 | The literature chain returns no assessment refs, so a parent's assessment-answer credit and the head's finding progress cannot see a child's assessments (4.1). The smallest fix is a `record_refs` return field of current retained assessment refs. |
| P3 | `metric_unit` (2.9) is open. P3 proposes `angstrom`, `dimensionless`, `z_score`, `unknown`. |
| P4 | The `missing[]` code lists are code-written but not closed in one place: `sequence_link` adds its own codes. Counts are proposed now. Per-code booleans need the closed list. |
| P5 | X7 (agreement across arms) is new. Nothing in the code computes it. |
| P6 | The two tool/scoring name mismatches of 0.7 (`measure` vs `measured`, `incompatibility_witness_refs` vs `contrast_witness_refs`). |
| P7 | `A1 function_ref` is an annotation field (a hypothesis id taken as given). It is the only annotation-like field. Everything else that names a function is a record ref. |
