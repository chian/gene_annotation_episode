# A104 (evolutionary_history_evidence): investigation finding features

Proposal for the owner to correct line by line. No code was changed and no Python was run.

An investigation finding is a set of fields. Every field has a controlled answer set that code can validate: a
number with a range and unit, an integer count, a boolean, a value of a fixed vocabulary, or a record reference.
There is no open field and no field that holds several pieces of evidence. Credit is not restated in any field.

## 0. What A104 scores with, and what was read

| # | Fact | Where |
|---|---|---|
| 0.1 | A104's own scoring is phylogenetic, not literature grading. Two sheet builders, `placement` (`a104_placement_v1`) and `history_comparison` (`a104_history_comparison_v1`), read an authenticated native IQ-TREE/MUSCLE result (`VERSION = 'a104_native_evolutionary_measurement_v1'`). | `episode_support/grading/evolutionary_history_evidence/scoring.py` |
| 0.2 | Four credit projectors: `A104EvolutionaryCredit` (bounded quality over three dimensions: `placement`, `history_comparison`, `characterized_clade`), `A104RobustnessCredit` (count of evaluated `compare_placements` uses), `A104PanelIdentityCredit` and `A104AlignmentSuitabilityCredit` (one preparation unit each, `scientific_support: none_from_preparation_alone`). `combine_received_task_progress` sums them. | `grading/evolutionary_history_evidence/credit.py` |
| 0.3 | The projectors read "attachments": rows of table `a104_attachments` (provider `native.a104.tool_attachment`) whose body is the graded sheet plus `score`, `policy`, `state`, `missing`, `measurement_ref`, `target_ref`, `target_regions`, `qualification_dependencies`, `variant_group`, `variant`, `compared_variant_group`, `compared_variants`. The reader is in `records/evolutionary_history_evidence/attachments.py`. Nothing inside the named folders writes this table, and no sheet schema exists in them for the `characterized_clade` (`clade_functions` policy) or the `robustness` (`compare_placements` policy) dimensions: the projectors name only their policy strings. Lines C* and R* below are therefore built from the projector alone. | grep of all `evolutionary_history_evidence` folders and `root/a104` |
| 0.4 | The `literature/{forms,readers,storage,inputs,grading,calculations,validation}/evolutionary_history_evidence/` folders are copies of the A105/A106 literature machinery. Their schemas name `A105` or `a106` (for example `literature_assay_grading.py`: `VERSION = 'a105_assay_grading_sheet_v1'`; `literature_sheet_policy.py`: `AXIS = 'A105'`; `literature_perturbation_summary.py`: `a106_source_summary_restoration_v2`). `literature_sheet_updates.py` imports that policy as `a104_policy`, but the policy still says `A105`. No A104 episode calls any grader or storage repository from them. The A104 literature episodes import only `ExperimentalContractError`, `_Sources`, `_witness_schema`, `literature_sequence_discovery` and the shared `literature_task_credit` (`lead_schema`, `_resolve`). No A104 finding is proposed from these copies. For their sheet fields, see `INVESTIGATION_FINDING_FEATURES_a105.md` and the A106 table. | those folders; `root/a104/.../published_evidence_assessment/**/task.py` |
| 0.5 | The shared literature task schema (`literature/grading/literature_task_credit.py`, `task_schema`) allows `evidence_axis` only from `A105`, `A106`, `A108`. A104's `published_evidence_assessment/messages/read_from_parent.py` checks only that the axis is a non-empty string, so it would accept `A104`. | both files |
| 0.6 | The A104 literature chain has no grading sheet. What it scores is the retained assessment (`investigation_finding.status == 'retained'`, eligible for the target and anchored) and the validated source lead. Credit is `credit_unit` × the number of answers. The finding features for this chain therefore come from the assessment record and from `annotation_assessments` (section 5). | `published_evidence_assessment/**/credit.py`; `records/sequence_and_context_sources/evolutionary_history_evidence/component_assessment_dependencies.py` |
| 0.7 | The head does not offer the `literature` slot to its model (`OFFERED_CHILDREN = ('evolutionary_history_evidence', 'hpc')`), so nothing commissions the literature chain at present. Section 7 still lists the chain's own parent→child decisions. | `root/a104/evolutionary_history_evidence/task.py` |
| 0.8 | The other graders in `grading/sequence_alignment/evolutionary_history_evidence/` and `grading/similarity_search/evolutionary_history_evidence/` (Biopython pairwise, minimap2, BLAST pairwise/database, HMMER, BV-BRC homology) are tool graders for homology search. No A104 projector reads them; `tool_grading_artifacts.py` only checks their correspondence. They are listed in section 6 and get no A104 `evidence_type`. | those files |
| 0.9 | `calculations/phylogeny/phylogeny_calculators.compare_unrooted_relationships` is outside the named folders and was not opened. Of its output, only `gene_splits.value` and `organismal_splits.value` are used in `scoring.py`. Line H8 is marked "unconfirmed". | `scoring.py` lines 204–209 |

## 1. Proposed `evidence_type` vocabulary for A104

| Value | Meaning | Source of the value |
|---|---|---|
| `clade_placement` | The target sits in one measured, bootstrap-supported split of a native family, regional or sensitivity tree | sheet `schema == 'a104_placement_v1'` / attachment policy containing `measure_placement` |
| `history_comparison` | The restricted gene tree is compared with an independent organismal (ribosomal-marker) tree over shared taxa | sheet `schema == 'a104_history_comparison_v1'` / policy containing `compare_histories` |
| `characterized_clade` | The target's clade contains characterized references (the third credit dimension) | attachment policy containing `clade_functions` (sheet schema absent, 0.3) |
| `placement_robustness` | One evaluated comparison of placements across analysis configurations | attachment policy `phylogeny.compare_placements_original_native_operands_v1` |
| `published_evolutionary_claim` | A retained literature assessment whose observation is anchored in a source | assessment record with `investigation_finding.status == 'retained'` (section 5) |
| `no_applicable_evidence` | Source-grounded declaration that the examined spans hold no applicable evidence; no assessment | reasoning selection `evidence_processing.kind` / screening answer `disposition` |

Not proposed as evidence types: panel identity and alignment suitability. Their projectors state they are
preparation with no scientific support. They stay credit only.

## 2. Placement sheet (`a104_placement_v1`, `phylogeny.measure_placement`)

### 2.1 What it grades

For one native analysis (purpose `family`, `regional` or `sensitivity`) and one split, the sheet gives the bootstrap
fraction of the split that contains the target tip. It also gives, for every reference in the panel, the MSA
correspondence and the patristic distance to the target.

### 2.2 Numeric, integer, boolean and enum fields, as the code builds them

The sheet is built as a dict in `placement()`; there is no JSON schema, so every key below is always present and
"required" means "always built".

| Field | Type | Answer set | Required |
|---|---|---|---|
| `schema` | const | `a104_placement_v1` | yes |
| `version` | const | `a104_native_evolutionary_measurement_v1` | yes |
| `producer_operation` | const | `phylogeny.measure_placement` | yes |
| `target_ref`, `native_phylogeny_ref`, `native_request_ref`, `hpc_result_ref` | record ref | | yes |
| `target_regions` | array of [start, end] integers | residue intervals | yes |
| `split_index` | integer | 0 ≤ i < number of splits | yes |
| `support_method` | enum | `ultrafast_bootstrap` (only value: `hpc_worker.py`) | yes |
| `support_scale` | enum | `percent` (only value) | yes |
| `bootstrap_population.matches` | integer | 0 ≤ m ≤ denominator | yes |
| `bootstrap_population.denominator` | integer | > 0 (protocol fixes 1000) | yes |
| `raw_value` | number | matches / denominator, [0, 1] | yes |
| `population.usable_replicates` | integer | = 1000 by protocol | yes |
| `population.excluded_replicates` | integer | = 0 by protocol | yes |
| `function_status` | const | `unassessed` | yes |
| `rooting_status` | const | `unestablished` | yes |
| `reference_correspondences[]` (one row per non-target panel member): `aligned_residue_pairs`, `identical_canonical_pairs`, `query_compared_length`, `reference_compared_length` | integer ≥ 0 | residues | yes |
| … `query_coverage`, `reference_coverage`, `identity_extent_factor` | number | [0, 1] | yes |
| … `observed_identity` | number or null | [0, 1]; null with no comparable pair | yes |
| … `patristic_distance` | number ≥ 0 | unit `patristic_unit` = `expected_substitutions_per_site` | yes |
| … `reference_full_length` | integer | residues | yes |
| `analysis_configuration_digest`, `variant_group`, `variant` | sha256 hex | identity, not evidence | yes |

### 2.3 Proposed finding for one placement sheet

| Line | Finding field | Read from (or computed how) | Type | Range / vocabulary | Unit |
|---|---|---|---|---|---|
| P0 | `evidence_type` | constant | enum | `clade_placement` | – |
| P1 | `bootstrap_support` | `raw_value` | number | [0, 1] | fraction of bootstrap replicates |
| P2 | `bootstrap_matches` | `bootstrap_population.matches` | integer | ≥ 0 | replicates |
| P3 | `bootstrap_replicates` | `bootstrap_population.denominator` | integer | > 0 | replicates |
| P4 | `support_method` | `support_method` | enum | `ultrafast_bootstrap` | – |
| P5 | `analysis_purpose` | `purpose` of the binding named by `analysis` in the native result (`native_phylogeny_ref`) | enum | `family`, `regional`, `sensitivity` | – |
| P6 | `clade_size` | `len(target_side_tip_ids)` | integer | ≥ 2 (includes target) | tips |
| P7 | `panel_size` | `len(reference_panel_members)` | integer | ≥ 2 | tips |
| P8 | `target_region_length` | Σ (end − start) over `target_regions` | integer | ≥ 1 | residues |
| P9 | `nearest_clade_patristic_distance` | min `patristic_distance` over `reference_correspondences` whose `tip_id` is in `target_side_tip_ids` | number | ≥ 0 | expected substitutions per site |
| P10 | `nearest_clade_observed_identity` | `observed_identity` of the P9 row | number or null | [0, 1] | fraction of aligned residue pairs |
| P11 | `nearest_clade_query_coverage` | `query_coverage` of the P9 row | number | [0, 1] | fraction of target residues |
| P12 | `nearest_clade_aligned_pairs` | `aligned_residue_pairs` of the P9 row | integer | ≥ 0 | residue pairs |
| P13 | `analyses_agreeing` | number of distinct `analysis` names in which the same physical relationship occurs (`relationship_inventory`: row whose `occurrences` include this `split_index` and analysis) | integer | ≥ 1 | analyses (agreement across arms) |
| P14 | `competing_configuration` | from the credit view: this sheet's `variant_group` has more than one `variant` among the received attachments | boolean | | – |
| P15 | `sheet_ref` | the attachment `grading_artifact_ref` | record ref | | – |

### 2.4 Fields left out

| Field | Why | What carries its meaning |
|---|---|---|
| `interpretation` (`'observed_native_target_relationship; no_function_transfer_or_biological_root'`) | constant prose label | P0 together with the fixed `function_status` / `rooting_status` |
| `function_status`, `rooting_status` | constants (`unassessed`, `unestablished`), so they carry no information | P0 (the type says no function transfer is claimed) |
| `analysis` (analysis name), `target_tip`, tip id lists, `clade_members`, `native_split`, `reference_panel_members`, `native_correspondence` | open strings or nested member lists | P5, P6, P7, P9–P12 |
| `basis` (`'exact_native_MUSCLE_rows_and_IQ_TREE_branch_lengths'`) | constant label | unit of P9 |
| `population.usable_replicates` / `excluded_replicates` | fixed by protocol (1000 / 0) | P3 |
| digests (`analysis_configuration_digest`, `variant_group`, `variant`, `result_sha256`), `pbs_job_id` | identity, not strength | P14, P15 |

## 3. History comparison sheet (`a104_history_comparison_v1`, `phylogeny.compare_histories`)

### 3.1 What it grades

The sheet compares the gene (family) tree, restricted to a declared set of ≥ 4 single-copy taxa that includes the
target, with an independent organismal reference tree (`independent_ribosomal_marker_supermatrix`, markers L2, L3 and
S3). It gives split counts and the mean bootstrap reliability of the evaluable restricted splits in each tree. The
sheet records agreement and conflict, and leaves the historical cause unresolved.

### 3.2 Fields

| Field | Type | Answer set | Required |
|---|---|---|---|
| `schema` | const | `a104_history_comparison_v1` | yes |
| `producer_operation` | const | `phylogeny.compare_histories` | yes |
| `selected_tip_ids` | array of tip id | ≥ 4, unique, one per taxon | yes |
| `taxon_join[]`: `taxon_id` | integer (NCBI taxon) | | yes |
| `organismal_basis.kind` | const | `independent_ribosomal_marker_supermatrix` | yes |
| `organismal_basis.markers` | const list | `L2`, `L3`, `S3` | yes |
| `comparison.gene_splits.value`, `comparison.organismal_splits.value` | integer | ≥ 0 | yes |
| `comparison.*` (other outputs of `compare_unrooted_relationships`) | not read (0.9) | | |
| `native_relationship_reliability.family` | number or null | [0, 1] | yes |
| `native_relationship_reliability.organismal_reference` | number or null | [0, 1] | yes |
| `raw_value` | number or null | min of the two above, null if no splits or either is null | yes |
| `historical_cause` | const | `unresolved` | yes |
| `limitations` | const list | `paralog_subset_declared`, `restricted_taxon_scope`, `rooting_unestablished`, `discordance_does_not_establish_horizontal_transfer` | yes |

### 3.3 Proposed finding

| Line | Finding field | Read from (or computed how) | Type | Range / vocabulary | Unit |
|---|---|---|---|---|---|
| H0 | `evidence_type` | constant | enum | `history_comparison` | – |
| H1 | `comparison_reliability` | `raw_value` | number or null | [0, 1] | mean bootstrap fraction |
| H2 | `gene_tree_reliability` | `native_relationship_reliability.family` | number or null | [0, 1] | mean bootstrap fraction |
| H3 | `organismal_tree_reliability` | `native_relationship_reliability.organismal_reference` | number or null | [0, 1] | mean bootstrap fraction |
| H4 | `shared_taxon_count` | `len(selected_tip_ids)` | integer | ≥ 4 | taxa (independent units) |
| H5 | `gene_split_count` | `comparison.gene_splits.value` | integer | ≥ 0 | splits |
| H6 | `organismal_split_count` | `comparison.organismal_splits.value` | integer | ≥ 0 | splits |
| H7 | `organismal_marker_count` | `len(organismal_basis.markers)` | integer | 3 (protocol) | markers |
| H8 | `shared_split_count`, `conflicting_split_count` | the calculator's split agreement output (name unconfirmed, 0.9) | integer | ≥ 0 | splits (agreement between trees) |
| H9 | `sheet_ref` | attachment `grading_artifact_ref` | record ref | | – |

### 3.4 Fields left out

| Field | Why | What carries its meaning |
|---|---|---|
| `interpretation`, `historical_cause`, `limitations` | constant labels / prose | H0 (the type never claims a transfer or duplication cause) |
| `family_analysis`, `organismal_analysis`, tip ids, `taxon_join` rows | open names / member lists | H4 |
| `organismal_basis.kind` | constant | H7 |

## 4. Credit projectors (the A104 sheet as the parent reads it)

### 4.1 `A104EvolutionaryCredit` view (`read_details`)

For each target: `assigned_length` (integer, residues), `cells[]` (`start`, `end` integers; `native_dimensions`:
`placement`, `history_comparison`, `characterized_clade`, each a number in [0, 1], the max compatible attachment
score), `pending_measurement_refs`, `unresolved_variant_groups`, and `status` (enum `attributed_phylogeny_received`,
`unresolved_attribution`, `no_received_native_phylogeny_test`). Top level: `source_contribution_count` (integer).
The `value` and `credit` fields are the credit and are not restated.

| Line | Finding field | Read from (or computed how) | Type | Range / vocabulary | Unit |
|---|---|---|---|---|---|
| F1 | `attribution_status` | `target_sheets[target].status` | enum | `attributed_phylogeny_received`, `unresolved_attribution`, `no_received_native_phylogeny_test` | – |
| F2 | `placement_max` | max `native_dimensions.placement` over the target's cells | number | [0, 1] | bootstrap fraction |
| F3 | `history_comparison_max` | max `native_dimensions.history_comparison` | number | [0, 1] | bootstrap fraction |
| F4 | `characterized_clade_max` | max `native_dimensions.characterized_clade` | number | [0, 1] | (scale of the absent producer, 0.3) |
| F5 | `supported_length` | Σ (end − start) over the cells with any dimension > 0 | integer | 0 … `assigned_length` | residues |
| F6 | `assigned_length` | `assigned_length` | integer | ≥ 1 | residues |
| F7 | `contribution_count` | `source_contribution_count` | integer | ≥ 0 | received measurements |
| F8 | `pending_measurement_count` | `len(pending_measurement_refs)` | integer | ≥ 0 | measurements |
| F9 | `competing_configuration_count` | `len(unresolved_variant_groups)` | integer | ≥ 0 | variant groups (disagreement across configurations) |

### 4.2 `characterized_clade` and `placement_robustness` attachments

| Line | Finding field | Read from | Type | Range / vocabulary | Unit |
|---|---|---|---|---|---|
| C0 | `evidence_type` | policy contains `clade_functions` | enum | `characterized_clade` | – |
| C1 | `characterized_clade_value` | attachment `score` | number | [0, 1] (the projector's `native_score_maximum = 1`) | not defined in the folders |
| R0 | `evidence_type` | policy `phylogeny.compare_placements_original_native_operands_v1` | enum | `placement_robustness` | – |
| R1 | `robustness_value` | attachment `score` (`native_value` in `A104RobustnessCredit`) | number | not defined in the folders | – |
| R2 | `evaluated_comparison_count` | `source_contribution_count` of `A104RobustnessCredit` | integer | ≥ 0 | comparisons (distinct `measurement_ref`, target, regions) |

The owner must settle C1 and R1 once a producer and sheet schema exist (0.3).

### 4.3 Annotation link (`annotation_contribution`, `annotation_assessments`)

These fields hold for every type above when a proposed annotation is assigned:

| Line | Finding field | Read from | Type | Range / vocabulary |
|---|---|---|---|---|
| L1 | `transfer_status` | `assessment_transfer(...).status` | enum | `established`, `unresolved`, `invalid`, `withdrawn` |
| L2 | `relation` | assessment `relation` | enum | includes `strengthens` (the full assessment vocabulary is outside the folders) |
| L3 | `linked_assessment_count` | `len(link_refs)` | integer | ≥ 0 |
| L4 | `missing_input_kinds` | `missing_inputs` | array of enum | `assessment_withdrawn`, `assessment_not_current`, `assessment_explicitly_incomparable`, `assessment_dependencies_not_received`, `assessment_native_extent_unavailable`, `no_received_applicable_supporting_assessment`, `assessed_observation_has_no_received_applicable_supporting_measurement`, `unresolved_native_attribution` |
| L5 | `assessment_refs` | `assessment_refs` | record refs | |

`assessment_qualifications` is left out. It holds the free `qualification` of each assessment, and L1–L4 carry
what it meant.

### 4.4 Preparation projectors (no finding)

`A104PanelIdentityCredit` and `A104AlignmentSuitabilityCredit` have credit 0 or 1 and return `source_ref`,
`target_ref`, `native_request_sha256` or `request_ref` and `hpc_result_ref`, and `analysis_names`. None of these is
evidence. Proposal: no finding; the parent reads their credit and, where the parent needs them, the refs.

## 5. Literature chain (`published_evidence_assessment` and below): the assessment finding

There is no sheet (0.6). The proposed finding for one retained assessment counted by `assessment_answers`:

| Line | Finding field | Read from | Type | Range / vocabulary |
|---|---|---|---|---|
| A0 | `evidence_type` | constant | enum | `published_evolutionary_claim` |
| A1 | `finding_status` | `investigation_finding.status` | enum | `retained`, `withdrawn` |
| A2 | `relation` | assessment `relation` | enum | as L2 |
| A3 | `applicability` | assessment `applicability` | enum | includes `incomparable` (full vocabulary outside the folders) |
| A4 | `transfer_status` | `annotation_assessments` row | enum | as L1 |
| A5 | `target_correspondence` | replaces the text field of `source_coverage_improvement`'s `FINDING_FORM` ("established, unresolved or not applicable, and why") | enum | `established`, `unresolved`, `not_applicable` |
| A6 | `source_subject_count` | `len(investigation_finding.source_claim.subject_refs)` | integer | ≥ 0 |
| A7 | `condition_count` | `len(condition_refs)` (assessment ∪ qualification `context_refs`) | integer | ≥ 0 |
| A8 | `assumption_count` | `len(assumption_refs)` | integer | ≥ 0 |
| A9 | `anchored` | observation `anchor` or `visual_anchor` is present | boolean | |
| A10 | `is_correction` | `replaces_refs` non-empty | boolean | |
| A11 | `same_claim_as_prior` | `same_source_claim_as_ref` is not null | boolean | |
| A12 | `assessment_ref`, `source_ref` | the answer row | record refs | |

The screening answer and the source lead are already controlled except for the prose rationale:

| Line | Field | Type | Answer set |
|---|---|---|---|
| S1 | `evidence_type` (screening answer) | enum | `no_applicable_evidence` |
| S2 | `examined_span_count` | integer | `len(examined)` ≥ 1 |
| S3 | `examined_byte_total` | integer | Σ (end − start), bytes |
| D1 | lead `disposition` | enum | `relevant`, `not_relevant` |
| D2 | lead `source_ref`, `subject_ref`, `proposed_annotation_ref` | record refs | |

Left out as prose in all seven literature returns: `interpretation`, `qualification`, `readings[].statement`,
`readings[].qualification`, `readings[].location`, `passages[].statement` and `.qualification`, `source_claim`,
`source_subject`, `windows[].quote`, `windows[].representation` (this one is really the enum `text`, `original`,
`stdout`, `stderr` and could stay as such), lead `relevance_rationale` and `witness.quote`. Lines A1–A11 carry what
they meant. The windows' `source_ref`, `offset` and `limit` may stay as record ref plus integers, but no parent
decision below needs them.

## 6. Homology tool graders (listed, no A104 type proposed)

| Grader | Score output | Controlled fields available |
|---|---|---|
| `biopython_pairwise_grader` | `biopython_pairwise_scores_v1` | integer counts `alignment_columns`, `paired_positions`, `identical_positions`, `substituted_positions`, `query_gap_columns`, `reference_gap_columns`, `query_aligned_positions`, `reference_aligned_positions`; fractions `paired_identity`, `alignment_identity`, `query/reference_paired_coverage`, `query/reference_aligned_coverage`; `native_score` |
| `minimap2_grader` | `minimap2_placement_scores_v1` | `query_length`, `reference_length`, `native_matching_bases`, `native_block_length`, `mapping_quality` (null at 255), `original_symbol_equal/substituted_positions`, span/paired/aligned coverage fractions |
| `blast_database_grader` | `blast_database_probabilities_v1` | `unadjusted_probabilities`, `representation_adjusted_probabilities` (per function), `unannotated_reference_kernel_fraction`, `unscored_sequence_group_count`; `calibrated_annotation_probability = False` |
| `hmmer_search_grader` | `hmmer_search_scores_v1` | per hit `retained_domain_count`, `is_reported`, `is_included`; per query `acquired_hit_row_count`, `acquired_included_hit_row_count`; per domain span coverages |
| `bvbrc_homology_grader` | `bvbrc_homology_scores_v1` | per query `status`, plus the BLAST database or pairwise output above |

These belong to the homology axes. If the owner wants them as A104 evidence, each would need its own type.

## 7. What each parent decides next, and the smallest return it needs

| Child → parent | What the parent decides next (its `task.py` decide/action and `msg_to_child`) | Smallest controlled return |
|---|---|---|
| A104 head → root | `root/task.py` decide: which of the nine axes to commission next, with objective, purpose, thought pattern and tools. It is shown each axis's `credit`, `commissions`, `latest_finding` and `job_handoff_refs`. `msg_to_child` selects only `committed_record_refs` for A104. | `credit`; `finding` = {`evidence_types_present` (array of the section 1 enum), F1, F5, F6, F7, F8, F9}; `committed_record_refs` (selected). Whether to come back depends on F8 > 0 (pending native measurements) or on a job still outstanding. A104 declares no `execution_handoff_refs`, so the root's `job_handoff_refs` for A104 stays empty. The owner may want that field added. |
| A104 head (own slot, narrower investigation) → A104 head | The head model decides the next unit: another tool, `reason`, `report`, `process.revise`, or another child commission (own slot or `hpc`). It reads the child's `credit`, `finding` and `committed_record_refs`. | `credit`; `committed_record_refs`; per received sheet the type-specific lines P1, P5, P6, P13, P14 (placement) and H1, H4, H5, H6, H8 (history), plus F1, F8, F9. These tell the head which relationship lacks support or agreement and which configuration is in conflict, which is where a narrower investigation is needed. |
| `hpc_work_planning` → A104 head | Whether to commission HPC planning again (more obligations), or to read the results it returned. | Already almost controlled: `credit`, `hpc_result_refs`, `hpc_accepted_obligations`, plus integer counts `plans_frozen`, `plans_closed`, `results_published` and `remaining_obligation_count` (replacing the `remaining_obligations` list). Leave out: the `qualification` text and the `hpc_model_ref` text, which should become a record ref. No evidence type: this is operational. |
| `published_evidence_assessment` → A104 head | Not offered at present (0.7). If offered: whether to read the assessments into the head's credit or commission more literature. | `credit`; `assessment_refs` (A12) of the answers; per answer A0, A1, A2, A4, A5, A9; `literature_source_lead_dispositions` as D1/D2 only, when the task is `verified_source_leads`. |
| `evidence_search_strategy_improvement` → `published_evidence_assessment` | Whether to commission the strategy child again with other `prior_search_refs`, or to read and reason itself. `msg_to_child` selects only leads (for `verified_source_leads`). | `credit` plus D1/D2 leads when selected. For `source_answer: assessment` tasks also A12 + A1 + A5 (the parent's own credit counts a child's retained assessment through custody). |
| `source_relevance_assessment` → `evidence_search_strategy_improvement` | Which further `search_result_refs` to triage next. | Same as the row above: `credit`, D1/D2, A12/A1/A5. |
| `source_evidence_examination` → `source_relevance_assessment` | Which source to examine next, or whether to re-examine the same source with `prior_delivery_refs`. | `credit`, D1/D2, A12/A1/A5, S1–S3 for a screening task. |
| `table_evidence_extraction`, `passage_evidence_extraction`, `source_coverage_improvement` → `source_evidence_examination` | Which other table, sheet, passage or window of the same page to commission next. | `credit`; A12/A1/A4/A5/A9 per assessment the reading committed; S1–S3 when the reading found no applicable evidence; D1/D2 when selected. |
| execution children (`execution_job_submission`, `execution_progress_assessment`, `execution_result_acquisition` and their sub-episodes, under the head or under `hpc_work_planning`) → their parent | Whether to launch, monitor or acquire again. These are not offered by the head's model today (only declared). | Operational, not evidence findings, so outside this proposal. Their text fields (`last_status`, `endpoint`, `execution_state`, `target_family`, `resource_id`, `qualification`) need their own fixed vocabularies in a separate pass. |

## 8. Annotation fields

No A104 sheet carries a gene, function or product name or ID. The proposed annotation is present only as
`proposed_annotation_ref` (a hypothesis record reference) and the target as `target_ref`. Both stay record
references. If the owner wants one, the single candidate is `asserted_function`, read from the hypothesis record that
`proposed_annotation_ref` names. That record's schema is outside the folders read.

## 9. Lines the owner may want to decide

1. Whether `characterized_clade` and `placement_robustness` stay in the vocabulary while their producer and sheet schemas are absent (0.3).
2. Whether the A105/A106 literature copies under the A104 folder names (0.4) are wanted at all. Nothing in A104 calls their graders.
3. Whether the head should declare `execution_handoff_refs` like A101, so the root can return to an outstanding A104 job.
4. Whether `published_evolutionary_claim` should carry its own strength features once A104 has a literature grader. Today it has only the qualitative lines A1–A11.
