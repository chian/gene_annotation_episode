# Investigation finding features: A110 (biochemical_feasibility_evidence), 19 November 2026

This is a proposal for the owner to correct line by line. No code was changed and no Python was run. Each line has an
ID (F1, P3, ...) so a correction can name it.

An investigation finding is a set of fields. Each field has a controlled answer set that code can validate: a number
with a range and a unit, an integer count, a boolean, a value of a fixed vocabulary, a record reference, or an
annotation. One field holds one thing. Credit is the productivity signal and no field restates it.

## 0. What A110 grades with, and what was read

| # | Fact | Where |
|---|---|---|
| 0.1 | A110 has **no literature subscoring sheet**. These folders do not exist: `literature/forms/biochemical_feasibility_evidence/`, `literature/storage/...`, `literature/inputs/...` and `literature/grading/...`. `literature/readers/biochemical_feasibility_evidence/` holds two readers (`literature_assets.py`, which lists PMC assets, and `literature_sequence_discovery.py`, which handles sequence-identity lookup). Both are acquisition. Neither grades. No shared file in `literature/forms/*.py` names A110. | folder listing; grep of `literature/forms/*.py` |
| 0.2 | The A110 literature graders that existed earlier are gone. In `passage_evidence_extraction/task.py` and `source_coverage_improvement/task.py`, `literature.reaction.populate` and `literature.reaction.source.populate` raise `NotImplementedError('a110_reaction_population_not_built:...')`: "its modules are not in the library". The head's `received_evidence` raises at `component_axis_reports.current_scoring_sheets`, `received_reports`, `component_axis_execution_context.prepared_assignments` and `a110_qualification.received` (`_not_placed`). The axis guidance still names the "reaction-prediction/resource components" and the `chemistry.*` operations (`request_accounting_hpc`, `request_flux_balance_hpc`, `reaction_evidence`, `experimental_reaction_evidence`, `source_identity_evidence`). None of these is in `tools/biochemical_feasibility_evidence/tools.py`. The native components are read by `jobs/sequence_and_context_sources/component_axis_native_hpc`, which is outside the named folders and was not read. | head `task.py`; leaf `task.py` files |
| 0.3 | So the controlled scoring that A110 actually has is: **S1** the typed `assessment` record with its `investigation_finding` (schema in `records/biochemical_feasibility_evidence/domain.py`). Every A110 scientific credit counts these. **S2** the retained-finding projector (`findings/biochemical_feasibility_evidence/investigation_progress.py` over `scientific_findings.py` and `finding_validity.py`). It is the credit of the head and of five literature episodes. **S3** the native tool sheet `biopython_pairwise_sheet_v1` (`grading/sequence_alignment/biochemical_feasibility_evidence/biopython_pairwise_grader.py`), kept by `grading/biochemical_feasibility_evidence/tool_grading_artifacts.py`. **S4 to S8** are operational projectors (practical execution, monitoring information, result-selector coverage, the HPC ledger and the HPC prediction model). They are not scientific evidence. Their returns are covered in section 5, and no `evidence_type` is proposed for them. | the files named |
| 0.4 | No A110 tool offered in `tools.py` calls `align_pair`, so in today's A110 tree nothing produces S3. `tools.py` also keeps sheets from graders outside the named folders (`sequence_composition_grader`, `sequence_extraction_grader`, `sequence_translation_grader`). Their score names appear in `tools.py` lines 270, 910 and 912, but their schemas were not read. | `tools.py` |
| 0.5 | `obj(...)` makes every listed property required unless a `required=` list is passed (`domain.py` line 26). That rule fills in the "required" column below. | `domain.py` |
| 0.6 | `table_evidence_extraction` has no `reason` tool, so it commits no `assessment`. Its credit is `finding_unit * len(summary['findings'])`, a count of prose report items. In the controlled design, its findings exist only once it commits assessments (see line D3). | `table_evidence_extraction/task.py`, `credit.py` |

## 1. Proposed `evidence_type` vocabulary for A110

`evidence_type` is computed by code from `observation.kind`, the enum `OBSERVATION_KINDS` of the observation that the
assessment's `observation_ref` names. The tool sheet S3 has its own fixed value. The model never writes the field.

| ID | Value | Meaning | Source of the value |
|---|---|---|---|
| E1 | `reaction_record` | Database or source reaction facts: equation, direction, participants | `observation.kind = reaction_context` |
| E2 | `biochemical_assay` | Measured activity, rate or turnover | `kind in {biochemical_assay, assay_report}` |
| E3 | `mechanism` | Mechanistic and chemical accounting statements (electron flow, cofactor regeneration) | `kind = mechanism` |
| E4 | `prediction_contrast` | Comparison of a prediction or model with an observation or alternative | `kind = comparison` |
| E5 | `growth_phenotype` | Growth or genetic phenotype that bears on a resource or pathway | `kind in {growth_assay, genetic_phenotype}` |
| E6 | `condition_context` | Measured or declared conditions (pH, temperature, medium, oxygen) | `kind in {context_measurement, context}` |
| E7 | `database_annotation` | A source database's own annotation of the reaction or protein | `kind = source_annotation` |
| E8 | `source_statement` | A literal statement in a source text that is not one of the above | `kind = source_content` |
| E9 | `sequence_correspondence` | Correspondence between a target and a reference sequence | `kind in {alignment, coordinate_mapping}`; S3 always |
| E10 | `out_of_axis` | An observation kind that A110 does not interpret (`sequence_composition`, `gene_prediction`, `profile_match`, `structure_match`, `taxonomy_assignment`, `read_support`) | the remaining `kind` values |
| E11 | `no_applicable_evidence` | A source-grounded finding that the examined material has no applicable evidence. There is no assessment. | `evidence_processing.kind` of the reason commit (head `_check_commit`) |

Alternative for the owner (line E0): use the A110 head's `TASKS` list as the vocabulary instead (`reaction_identity`,
`stoichiometric_accounting`, `electron_accounting`, `cofactor_regeneration`, `resource_feasibility`,
`conditional_energetics`, `prediction_contrast`, `target_transfer`; `synthesis` dropped). No record holds a task name
today. That choice would need a new enum field on `investigation_finding`, which the model selects and the schema
validates. E1 to E11 need no new field.

## 2. S1: the typed assessment and its `investigation_finding`

### 2.1 What it grades

It records one source observation's bearing on one target hypothesis: the direction (`relation`), how directly the
observation transfers to the target (`applicability`), how its extent was attributed, and the typed source claim with
an explicit qualification kind. Every scientific credit in A110 counts these records (S2).

### 2.2 Numeric, integer, boolean and enum fields as the schema names them

| Field | Type | Answer set | Required |
|---|---|---|---|
| `assessment.relation` | enum | `strengthens`, `weakens`, `mixed`, `does_not_discriminate` | yes |
| `assessment.applicability` | enum | `direct`, `transfer`, `contextual`, `scope_limited`, `incomparable` | yes |
| `assessment.extent_basis` | enum | `observed_extent`, `inferred_extent`, `context_allocation` | yes |
| `assessment.hypothesis_ref`, `observation_ref` | record ref | hypothesis, observation | yes |
| `assessment.condition_refs`, `assumption_refs` | record refs | context and assumption records | yes |
| `assessment.target_footprint[].start`, `.end` | integer | start >= 0, end >= 1 | no (null allowed) |
| `assessment.target_footprint[].unit` | enum | `nt`, `aa`, `symbol` | yes, inside a footprint |
| `investigation_finding.source_claim.predicate` | enum | `PREDICATES` (29 values, e.g. `catalyzes`, `uses`, `produces`, `requires`, `transports`, `binds`, `participates_in`, `growth_capability`) | yes |
| `investigation_finding.source_claim.value.type` | enum | `number`, `enum`, `term_ref`, `reference`, `relation` | yes |
| `...value.value` (number) | number | any finite number | yes, if type is `number` |
| `...value.unit_ref` | record ref or null | a unit term | yes, if type is `number` |
| `...value.bound` | enum | `less_than`, `less_or_equal`, `greater_than`, `greater_or_equal` | no |
| `...value.qualifier` | const | `approximate` | no |
| `...value.uncertainty.representation` | const | `plus_minus` | yes, inside the block |
| `...value.uncertainty.magnitude` | number | >= 0, in the value's unit | yes, inside the block |
| `...value.uncertainty.statistic` | const | `unspecified` | yes, inside the block |
| `...value.value` (enum) | enum | `ENUM_VALUES` (55 values, e.g. `present`, `absent`, `growth`, `no_growth`, `positive`, `negative`, `ambiguous`) | yes, if type is `enum` |
| `...value.roles[].role` | enum | `RELATION_ROLES` (22 values, e.g. `substrate`, `product`, `cofactor`, `electron_donor`, `electron_acceptor`, `control`) | yes, if type is `relation` |
| `investigation_finding.qualification.kind` | enum | `none`, `measurement_does_not_establish_claim`, `different_source_subject`, `conditions_limit_transfer`, `alternatives_not_discriminated`, `prediction_not_measurement`, `assumption_not_established`, `confounding_unresolved` | yes |
| `investigation_finding.status` | enum | `retained`, `withdrawn` | yes |
| `investigation_finding.withdrawal_reason` | enum | `not_withdrawn`, `source_misread`, `wrong_subject`, `wrong_condition`, `wrong_unit`, `unsupported_claim`, `duplicate_information`, `superseded_evidence` | yes |
| `investigation_finding.same_source_claim_as_ref` | record ref or null | an earlier assessment | yes |
| `investigation_finding.replaces_refs` | record refs | earlier assessments | yes |
| `observation.kind` | enum | `OBSERVATION_KINDS` (19 values) | yes |
| `observation.measurements[].name` | enum | `METRIC_NAMES` (includes `activity`, `concentration`, `dissociation_constant`, `growth_rate`, `temperature`, `ph`, `replicate`, `control_ref`, `count`) | yes |
| `observation.measurements[].value` | ATOM | as for `source_claim.value` above, including the uncertainty block | yes |
| `observation.anchor`, `visual_anchor` | object or null | the text byte window, or the image region | `anchor` yes (may be null); `visual_anchor` no |

### 2.3 Proposed `investigation_finding`, one for each retained assessment

| ID | Finding field | Read by code from | Type | Range or vocabulary | Unit |
|---|---|---|---|---|---|
| F1 | `evidence_type` | `observation.kind` through table 1 | enum | E1 to E10 | none |
| F2 | `assessment_ref` | the assessment id | record ref | assessment | none |
| F3 | `relation` | `assessment.relation` | enum | 4 values (2.2) | none |
| F4 | `applicability` | `assessment.applicability` | enum | 5 values | none |
| F5 | `extent_basis` | `assessment.extent_basis` | enum | 3 values | none |
| F6 | `qualification_kind` | `investigation_finding.qualification.kind` | enum | 8 values | none |
| F7 | `claim_predicate` | `source_claim.predicate` | enum | `PREDICATES` | none |
| F8 | `claim_value_type` | `source_claim.value.type` | enum | 5 values | none |
| F9 | `claim_value` | `source_claim.value.value`, only when type is `number` | number | finite | the unit `unit_ref` names |
| F10 | `claim_unit_ref` | `source_claim.value.unit_ref` | record ref or null | term | none |
| F11 | `claim_value_enum` | `source_claim.value.value`, only when type is `enum` | enum | `ENUM_VALUES` | none |
| F12 | `claim_bound` | `source_claim.value.bound`; absent maps to `exact` | enum | `exact`, `less_than`, `less_or_equal`, `greater_than`, `greater_or_equal` | none |
| F13 | `claim_approximate` | `qualifier == 'approximate'` | boolean | | none |
| U1 | `uncertainty_reported` | the uncertainty block is present on `source_claim.value` | boolean | | none |
| U2 | `uncertainty_magnitude` | `uncertainty.magnitude` | number or null | >= 0 | same as F9 |
| U3 | `uncertainty_kind` | `uncertainty.statistic` | enum | `unspecified`; `unreported` when U1 is false | none |
| U4 | `uncertainty_relative` | U2 / abs(F9), when F9 is nonzero | number or null | >= 0 | fraction |
| C1 | `condition_count` | `len(condition_refs)` | integer | >= 0 | records |
| C2 | `assumption_count` | `len(assumption_refs) + len(qualification.assumption_refs)` | integer | >= 0 | records |
| C3 | `claim_subject_count` | `len(source_claim.subject_refs)` | integer | >= 1 | records |
| C4 | `measurement_count` | `len(observation.measurements)` | integer | >= 0 | measurements |
| C5 | `replicate_count` | value of the observation measurement named `replicate`, when it is a number | integer or null | >= 1 | replicates |
| C6 | `control_present` | an observation measurement named `control_ref`, or a relation role `control` in `source_claim.value.roles` | boolean | | none |
| C7 | `footprint_length` | sum of `end - start` over `target_footprint` | integer or null | >= 0 | `target_footprint[].unit` (`nt`, `aa`, `symbol`) |
| C8 | `anchored` | `observation.anchor` or `visual_anchor` is non-null | boolean | | none |
| C9 | `anchor_kind` | which anchor: `text`, `image`, `none` | enum | 3 values | none |
| R1 | `repeats_earlier_claim` | `same_source_claim_as_ref is not None` | boolean | | none |
| R2 | `corrects_count` | `len(replaces_refs)` | integer | >= 0 | assessments |

Line F11 is the only place where a value from a fixed list carries biology (for example `present`, `growth` or
`no_growth`). It is a fixed vocabulary, not an annotation.

### 2.4 Fields left out because they are prose, and what carries their meaning

| Left out | Why | Carried by |
|---|---|---|
| `observation.anchor.quote` | quoted source text | C8, C9; the anchor stays in the record |
| `context.name`, `term.label`, `reference.label` (records reached through refs) | labels | the refs (F10, C1) |
| the head report's `interpretation`, `qualification`; the literature reports' `interpretation`, `qualification`, `statement`, `claim`, `subject`, `anchor` (text) | model prose | F3 to F6, F12, U1 to U4, C1 to C9 |
| the `qualification` constants of the operational returns (fixed text) | code constants that carry no information | nothing |

## 3. S2: the retained-finding projector (`known_retained_scientific_findings_v1`)

### 3.1 What it grades

It counts one `finding_unit` for each distinct canonical finding key among the assessments that the episode knows.
The key is the hypothesis, the source identity, the source claim and the qualification. It retires findings that a
current correction replaced and lists every inactive known assessment with a reason. This is the credit of the head
and of `published_evidence_assessment`, `evidence_search_strategy_improvement`, `source_relevance_assessment`,
`source_evidence_examination`, `passage_evidence_extraction` and `source_coverage_improvement`.

### 3.2 Fields as the code names them

| Field | Type | Answer set | Always present |
|---|---|---|---|
| `credit` | number | `finding_unit * retained_finding_count` | yes |
| `retained_finding_count` | integer | >= 0 | yes |
| `inactive_dependencies[].reason` | enum | `typed_finding_not_recorded`, `finding_target_outside_scope`, `scientific_finding_withdrawn`, `finding_replaced`, `not_current_assessment_revision` | yes |
| `inactive_dependencies[].withdrawal_reason` | enum | the 8 values of 2.2 | when the reason is withdrawn |
| `inactive_dependencies[].assessment_ref`, `current_assessment_ref`, `replacement_refs` | record refs | assessments | as applicable |
| `detail_pages.source_contributions_total`, `inactive_dependencies_total`, `offset`, `limit` | integer | >= 0 | yes |
| `source_contributions[].meaning.source` | object | a publication id (`doi`, `pmcid`, `pmid`) or a provider, accession and artifact | per row |
| `policy.finding_unit` | number | > 0 | yes |

### 3.3 Proposed aggregate finding of an episode (computed over the rows of 3.2 and the S1 findings it counts)

| ID | Field | How code computes it | Type | Range | Unit |
|---|---|---|---|---|---|
| P1 | `retained_finding_count` | the projector's field | integer | >= 0 | distinct findings |
| P2 | `count_by_evidence_type` | count of the retained findings for each F1 value | object of integers, one key per E1 to E10 | >= 0 each | findings |
| P3 | `strengthening_count` | retained findings with F3 = `strengthens` | integer | >= 0 | findings |
| P4 | `weakening_count` | F3 = `weakens` | integer | >= 0 | findings |
| P5 | `mixed_or_nondiscriminating_count` | F3 in {`mixed`, `does_not_discriminate`} | integer | >= 0 | findings |
| P6 | `direct_count` | F4 = `direct` | integer | >= 0 | findings |
| P7 | `qualified_count` | F6 != `none` | integer | >= 0 | findings |
| P8 | `independent_source_count` | distinct `meaning.source` among the retained findings | integer | >= 0 | sources |
| P9 | `uncertainty_reported_count` | U1 true | integer | >= 0 | findings |
| P10 | `controlled_count` | C6 true | integer | >= 0 | findings |
| P11 | `arm_agreement` | `agree` if P3 > 0 and P4 = 0, or P4 > 0 and P3 = 0; `conflict` if both > 0; `none` if both = 0 | enum | `agree`, `conflict`, `none` | none |
| P12 | `inactive_count_by_reason` | count of `inactive_dependencies` for each reason | object of integers, 5 keys | >= 0 | assessments |
| P13 | `finding_refs` | ids of the current assessments that are retained | record refs | assessment | none |

`credit` is not repeated in the finding (the rule that credit is the productivity signal).

## 4. S3: tool sheet `biopython_pairwise_sheet_v1` and its scores `biopython_pairwise_scores_v1`

### 4.1 What it grades

One supplied native pairwise alignment. It counts its columns from the traceback, checks the coordinate geometry
against the operand lengths and the alignment mode, and calculates identity and coverage fractions. It assigns no
function confidence.

### 4.2 Fields as the schema names them (`_validate_sheet` requires all of these keys)

| Field | Type | Answer set |
|---|---|---|
| `schema` | const | `biopython_pairwise_sheet_v1` |
| `status` | enum (computed) | `complete`, `partial`, `no_alignment`, `alignment_data_unavailable` |
| `molecule` | enum | `protein`, `dna`, `rna` |
| `mode` | enum | `local`, `global` |
| `aligned` | boolean | |
| `alignment_state` | enum | `alignment`, `no_alignment`, `conflicting` |
| `native_score` | number or null | native alignment score |
| `lengths.query`, `lengths.reference` | integer or null | >= 0, in `aa` or `nt` |
| `measured_column_counts.{alignment_columns, paired_positions, identical_positions, substituted_positions, query_gap_columns, reference_gap_columns, query_aligned_positions, reference_aligned_positions}` | integer or null | >= 0 |
| `reported_measurements.{paired_positions, identical_positions}` | integer or null | >= 0 |
| `reported_measurements.{identity_fraction, query_coverage, reference_coverage}` | number or null | 0 to 1 |
| `native_parameters.gap_open`, `gap_extend` | number or null | |
| `traceback.status` | enum | `valid`, `invalid`, `unavailable`, `no_alignment`, `conflicting` |
| `geometry.available` | boolean | |
| `geometry.operand_bounds_checked.query`, `.reference` | boolean | |
| `issues[].code` | enum (codes in the grader) | e.g. `traceback_missing`, `coordinate_path_invalid`, `reported_count_traceback_conflict`, ... |
| scores: `paired_identity`, `alignment_identity`, `query_paired_coverage`, `reference_paired_coverage`, `query_aligned_coverage`, `reference_aligned_coverage` | number or null | 0 to 1, fraction |

### 4.3 Proposed finding for one retained S3 grading

| ID | Field | Read from | Type | Range | Unit |
|---|---|---|---|---|---|
| A1 | `evidence_type` | constant | enum | `sequence_correspondence` (E9) | none |
| A2 | `sheet_ref` | the `tool_grading_artifact_v2` artifact ref | record ref | artifact | none |
| A3 | `sheet_status` | `status` | enum | 4 values | none |
| A4 | `alignment_state` | `alignment_state` | enum | 3 values | none |
| A5 | `mode` | `mode` | enum | `local`, `global` | none |
| A6 | `paired_positions` | `measured_column_counts.paired_positions` | integer or null | >= 0 | `aa` if `molecule` is protein, else `nt` |
| A7 | `paired_identity` | scores `paired_identity` | number or null | 0 to 1 | fraction |
| A8 | `query_aligned_coverage` | scores | number or null | 0 to 1 | fraction of the query length |
| A9 | `reference_aligned_coverage` | scores | number or null | 0 to 1 | fraction of the reference length |
| A10 | `native_score` | `native_score` | number or null | finite | native alignment score (matrix units) |
| A11 | `geometry_available` | `geometry.available` | boolean | | none |
| A12 | `issue_count` | `len(issues)` | integer | >= 0 | issues |

### 4.4 Left out

`native_result` (raw copy), `traceback.query` and `.reference` (strings), `residue_correspondence` (per-column rows),
`native_parameters.matrix` (a name), `symbol_interpretation` and `limitations` (fixed strings), and the score
`definitions` (formula text). A6 to A12 carry what these meant for the decision. The rows stay in the saved sheet.

## 5. What each returning episode's parent decides, and the smallest controlled return

Duplicated subtrees (`hpc_work_planning/execution_*`, `hpc_allocation_execution/execution_*`) have the same forms as
the top-level ones, so they are covered by the same lines. `credit` is always returned and is not listed again.

| ID | Child, then parent | What the parent decides next (its `task.py` and `msg_to_child`) | Smallest controlled return | Drop from today's form |
|---|---|---|---|---|
| D1 | `passage_evidence_extraction` to `source_evidence_examination` | another reading of the same source (another table, more passages, an ordered reading) or `report` | P1, P3, P4, P11, P13 | `interpretation`, `qualification`, `passages[].statement` and `.qualification` (prose); `passages[].offset` and `.limit` stay in the record |
| D2 | `source_coverage_improvement` to `source_evidence_examination` | the same as D1, and whether the document still has unread parts | P1, P3, P4, P13; `covered_byte_count` (integer, bytes, sum over `windows_read[].limit`); `next_offset` (integer, bytes, end of the last window) | `interpretation`, `qualification`, `passages[]` prose; `windows_read` list (replaced by the two integers) |
| D3 | `table_evidence_extraction` to `source_evidence_examination` | the same as D1 | P1, P3, P4, P13; `rows_read_count` (integer, rows) | `findings[].claim`, `.subject`, `.qualification`, `.anchor` (prose). **This episode commits no assessment (0.6), so P1 and P13 exist only if it gets the `reason` commit. Until then its credit counts prose items.** |
| D4 | `source_evidence_examination` to `source_relevance_assessment` | which other returned source to examine next | P1, P2, P3, P4, P8, P13 | `interpretation`, `qualification`, `investigations[]` (the children's prose re-sent) |
| D5 | `source_relevance_assessment` to `evidence_search_strategy_improvement` | whether this search approach is productive (its credit trend) and whether to revise terms | P1, P8, P13; `examined_source_count` (integer); `productive_source_count` (integer, sources with at least one retained finding) | `examinations[]` prose; `source_refs` given as text: move them to `record_refs` |
| D6 | `evidence_search_strategy_improvement` to `published_evidence_assessment` | another strategy investigation, or `report` | P1, P2, P8, P11, P13 | `assessments[]` prose, `interpretation`, `qualification` |
| D7 | `published_evidence_assessment` to the head | the next action: another literature commission, launch, hpc, a recursive child, `reason`, or `write_interpretation` | P1, P2, P3, P4, P6, P8, P11, P13 | `strategies[]` prose, `interpretation`, `qualification`. **The head's credit counts the `assessment` records it holds (`records.list('assessment')`). Today the literature return has no `record_refs` field, so literature findings never reach the head's credit. P13 as `record_refs` is required, not optional.** |
| D8 | the head (and the recursive A110 child) to the root (or to the head) | the root picks the axis whose next commission should raise the product annotation credit most. It reads `credit`, `latest_finding` and `job_handoff_refs` (`root/task.py` lines 49 to 55, 91) | P1, P2, P3, P4, P11, P12, P13; `committed_record_refs` (already required); `outstanding_handoff_count` (integer); `execution_handoff_refs` (record refs; the root's `msg_to_child` says only A101 declares it today) | `finding.interpretation`, `.qualification`, `.source_refs` (text); `children[]` (re-sent child findings); `reasoning_commits` (an activity count that restates productivity) |
| D9 | `execution_job_submission` (launch) to the head or `hpc_allocation_execution` | whether to monitor or acquire results through a handoff | `handoff_established` (boolean), `new_handoff_count` (integer), `execution_handoff_refs` (record refs) | `handoff_resources` and `launches[]` (open resource-id strings, a nested list); `launches_run` (activity) |
| D10 | `local_job_execution`, `hpc_job_execution` to `execution_job_submission` | whether the launch reached its endpoint, or to retry it | `practical_completed` (boolean); `endpoint` (enum `usable_handoff`, `completed_job_outputs`); `satisfied_requirement_count`, `unsatisfied_requirement_count`, `failed_command_count` (integers); `execution_handoff_refs` | `satisfied_keys` and `unsatisfied_keys` (caller-defined key strings: count them); `failures[]` (records: keep only the failure `code`, if it is an enum); `commands_run` (activity) |
| D11 | `execution_progress_assessment` (monitor) to the head, `hpc_work_planning` or `hpc_allocation_execution` | whether results can be acquired now, or to look elsewhere | `observed` (boolean); `execution_state` (enum `pending`, `executing`, `returned`, `admitted`); `result_available` (boolean); `monitoring_progress_refs` (record refs) | `qualification` (constant text); `target_handle` (echo of the commission); `newly_informative_snapshot_count` (the credit's own count: it restates credit) |
| D12 | `execution_result_acquisition` to the head or an HPC parent | whether the selected results are complete enough to interpret, or to acquire more | `complete` (boolean); `window_count`, `failure_count` (integers); `acquired_selector_fraction` (number 0 to 1, fraction of byte positions; see O3); `execution_result_refs`, `execution_result_artifact_refs` (record refs) | `qualification` (constant text); `handoff_refs` (echo) |
| D13 | `hpc_work_planning`, `hpc_allocation_execution` to the head or `hpc_work_planning` | whether the HPC work is done, or whether more plans or allocations are needed | `accepted_obligation_count`, `remaining_obligation_count`, `plans_frozen`, `plans_closed` (integers); `hpc_result_refs` (record refs) | `credit_components` and `hpc_credit` (restate credit); `accepted_obligations` and `remaining_obligations` (open id strings: count them); `qualification` (constant text) |
| D14 | `hpc_resource_prediction` to `hpc_work_planning` | whether the prediction model is good enough to plan with, or to fit again | `validation_quality` (number or null, the grader's proper-score scale); `training_case_count` (integer); `hpc_model_ref`, `hpc_ledger_refs` (record refs) | `model_quality_improvement`, `prospective_validation_credit`, `hpc_credit` (credit components); `entry_model_ref` (echo); `training_ids` (count them); `qualification` |

## 6. Annotation fields

No A110 scoring record holds a gene, function or product ID as a value. The function under test is the hypothesis
record that `assessment.hypothesis_ref` names (`predicate` from `PREDICATES`, value an ATOM). Reaction and chemical
identities are `term` or `reference` records reached through refs (Rhea, ChEBI and KEGG accessions with `namespace`
and `accession`). If the owner wants them in the finding:

| ID | Field | Read from | Type | Keep |
|---|---|---|---|---|
| N1 | `claim_term_accession` | `source_claim.value.ref`, when type is `term_ref`, then the term record's `namespace:accession` | annotation (ID; not looked up) | owner to decide |
| N2 | `asserted_function` | the hypothesis record's `value`, when it is a `term_ref`, same route as N1 | annotation | owner to decide |

## 7. Lines the owner may want to decide

| ID | Question |
|---|---|
| O1 | Vocabulary: E1 to E11, derived from `observation.kind`, or the `TASKS` list (E0), which needs a new enum field on `investigation_finding`? |
| O2 | Should the reaction-population cells and the `chemistry.*` components (0.2) be rebuilt as A110 subscoring sheets? Once they exist, they would supply strength features (equation residuals, electron balance, Gibbs components with their uncertainty) that S1 cannot carry. None of them is in the library today. |
| O3 | Is `acquired_selector_fraction` (D12) the credit restated? Credit = `acquired_record_unit * selector_progress`, which is the same quantity scaled. If yes, drop it and keep `complete`. |
| O4 | D7 and D3: the two structural gaps. The literature returns no assessment `record_refs` to the head, and `table_evidence_extraction` has no typed commit. |
