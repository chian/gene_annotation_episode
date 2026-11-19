# a106/.../source_evidence_examination/table_evidence_extraction — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/<file>`
(only files directly in this folder plus `grading/` and `scoring/`; `tests/` holds only an empty `__init__.py`).

Old binding class: `LiteratureEpisode` (`binding_path = '.../source_evidence_examination/table_evidence_extraction'`,
`commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_table',)`,
`entry_roles = ()`). Decision source `LiteratureTask`. Model prompt renderer `render_literature_experimental_prompt`
(old shared `library/literature_experimental_prompt`). Binding record version `literature_episode_binding_v1`; task
contract version `literature_local_task_v1`; evidence axis `A106`. A leaf: `_CHILDREN['literature_table'] = ()`.

## What it is for (its goal, in its own words)

Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_table']`):

> Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.

`goal.py` `LiteratureGoal.instructions()` joins this text with `PERTURBATION_TASK` (old shared
`library/literature_perturbation_prompt`) and `TASK` (old shared `library/literature_a106_subscore`); those two texts
are in the old shared library (out of bounds; not reproduced). `source_contracts.py` docstring: "a reading selection
is information for an investigation, never a script that this binding executes."

`goal.planning_context()` (shown as `literature_goal_plan` when a `literature_task` is assigned): `objective`,
`proposed_annotation_ref`, `commissioned_result`, `progress_definition` (credit projector record),
`planning_question`.

## Task and instructions

Same three commissioned task kinds as its parent `source_evidence_examination` (`goal.task_schema()`, identical
code): `A106:verified_source_leads` (lead dispositions), `A106:source_answer:assessment` (`source_refs`;
`changed_assessment_refs`), `A106:source_answer:screening` (`examined` spans; `literature_screening_answers`), each
with `credit_unit` and optional `yield_settings` {kind, cutoff, uncertainty_alpha}. "A106 score computation is
automatic work, not an episode-credit task."

`commissioned_task` checks are the parent's, except the assigned page is `assignment.get('page', None)` (the page
inside the reading assignment): all task sources must be that page's source; screening spans must be on that page's
artifact.

Model instructions (`task_instructions.py`, identical to the parent's): base `INSTRUCTIONS` (old shared
`literature_investigation_prompt`) + goal text; `REASONING_COMMIT_REQUIREMENT`; tool-knowledge and launch
instructions when present; `pending_child_delivery` → `redeliver_report` repair paragraph; `pending_child_` wait
paragraph when wait is permitted ("Waiting only reports readiness and earns no scientific credit"); native event
targets paragraph; decision_exchange_v1 history replacement. `task.py`, `task_state.py`, `task_decision.py`,
`decision_inputs.py`, `decision_state.py`, `decision_presentation.py`, `report_delivery.py`, `waiting.py` are
byte-identical to the parent's apart from module paths and the role name in docstrings (same decision loop: invalid
or failed returned results still enter the iterator; model-call failure ends with `source_failed`).

## What it reads from its parent's assignment

Assignment schema (`from_parent.assignment_schema`): `version: reading_assignment_v1`, `page` = the parent's
`_PAGE` (`page_assignment_v1`, `source_ref`, `representation`, `artifact_ref`, `question_context_refs`,
`prior_delivery_refs`), and `selection` = `anyOf [_TABLE, _WINDOW]`: an XLSX table selection (`source_ref`, `sheet_key`, `offset`, `limit`, `header_row`, `where` {column A-Z, equals|contains, value, case_sensitive}) or an exact original-source byte window for an article XML table; plus top-level `literature_task`, `proposed_annotation_ref`
(required with `private_yield_binding`) and the same requested-component arrays for every numerical family as the
parent (conditional ones by population flag).

`_validate_assignment`: page validated as in the parent (source/artifact/representation/context refs in scope); then
for the selection (one window or table), each window's `source_ref` must equal the page's (`literature_reading_source_mismatch`); a window with a
`representation` must match the page's (`literature_reading_representation_mismatch`) and its `offset` must not exceed
the page artifact's size (`source_offset_out_of_bounds`).

`prepare_assignment` (called by the parent page episode): operation key required; private yield binding fills
`credit_unit`/`yield_settings` from this binding's `yield_bindings[task key]` (supplied mismatch is an error);
proposed annotation must equal the parent's; and, because the parent role is `literature_page`, the parent's own page
assignment is validated with `from_parent_page.OriginalPageAssignment._validate_parent_page` (the parent's `_PAGE`
schema with task, annotation and requested components) and the reading's `page.source_ref` must be within the
parent's page source (`literature_reading_outside_assigned_source`).

## Children it may commission

None (`_CHILDREN['literature_table'] = ()`; `allowed_children` returns `()`), although `permitted_common_actions` still lists
`child`. No `to_child_*` / `from_child_*` files.

## Decision state and what it shows the model

As the parent (`decision_state.py`, `decision_inputs.py` identical). `internal_summary.decision_context()` is the
parent's with `page = assignment.get('page')`: `literature_assignment` (the whole reading assignment, including the
selection), source custody of the page source, `own_literature_outcomes` (page of `outcome_page_size`, default 8),
`literature_history_meaning`, `literature_examined_source_inputs`, `received_intervention_analysis_rows`,
`literature_experimental_work`, the numerical display/receipt-binding contexts, owned population sources and the
latest failed population attempt, `literature_completed_work`, current scoring sheets, `literature_goal_plan`.

## Tools it offers

`tool`, `reason`, `child`, `wait`, `redeliver_report`. Same catalog as the parent: access tools (`state.query`,
`source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`,
`image.view`, `source.archive.*`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.*`, `execution.estimate`
restricted to xlsx branches) plus the 36 A106 population operations (some flag-gated) and
`literature.intervention_analysis.contract` in `execute`. Custody: every source argument must lie within the page
source (`_within_source` over `parent_source_refs`). Own extra rule (`source_operations._tool_arguments`, 3 lines): when the selection is a `_TABLE` (has `sheet_key`), `source.xlsx.rows` must use that same `sheet_key`, else `literature_table_sheet_mismatch`. Lead reasoning (`source_lead`, validated witness) only
for a `verified_source_leads` task; `_required_grading_repository` is `None`. `grading/intervention_assessment.py`
and `scoring/intervention_main_sheet.py` are identical to the parent's (intervention-grading cell reader; A106
subscore repository and automatic score judgments).

## How its credit is counted

Identical to the parent (`credit.py` same code): `credit_kind` `scientific`; `LiteratureTaskCredit` record
`{kind: literature_local_task_v1, task, credit_unit, unit, revision_credit: False, activity_credit: False,
annotation_support: separate}`; `credit = credit_unit × len(items)`, finite, never clamped. Items: relevant lead
dispositions (own reason results; `runtime_report_attempts` admitted child forms, none here since it has no
children), one screening answer when all requested examined spans are covered by own `no_applicable_evidence`
witnesses, or one current retained target-eligible assessment anchored in a task source.

## Continuation (yield estimator and settings)

Identical to the parent: only with `private_yield_binding`; `yield_bindings[task key] = {credit_unit, kind, cutoff,
uncertainty_alpha}`; leads → **accumulation**; source answers → **completion with a target** (target = `credit_unit`,
forecast band limited to remaining commissioned credit, exact zero once earned). Stops when the next-credit upper
estimate is at or below `cutoff`.

## What it reports to its parent

Identical to the parent (`to_parent.py`, `received_evidence.py`, `report_delivery.py` same code): all numerical
`literature_*_cells` namespaces, `literature_screening_answers`, `literature_source_lead_dispositions`; facts from
committed/current sheets actually received, completed work and scoring sheets; validation that leads/screening equal
saved work and numerical rows are received and exactly the requested subset. The parent page episode receives this
through its `from_child_table_evidence_extraction.py` (typed form references, population-cell receipts, native timing receipts), and
counts relevant leads in this form toward its own leads credit.

## Differences from siblings / similar episodes

- vs parent `source_evidence_examination`: reading assignment (`reading_assignment_v1`: page + selection) instead of
  the page itself; extra `from_parent_page.py`; leaf (no child files or child maps); `commissioning_parent` is the page
  episode; `page = assignment.get('page')` in goal, internal summary and source operations.
- vs siblings: only this episode has the `sheet_key` rule on `source.xlsx.rows` and accepts a `_TABLE` selection; `source_coverage_improvement` takes exactly one window; `passage_evidence_extraction` takes one or more spans. Everything else (credit, yield, report, tools, decision loop) is the same code.

## File by file

| old file | lines | own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `episode.py` | 63 | composes the binding with `OriginalPageAssignment` first, role `literature_table`, `_SOURCE_REPOSITORIES` | library `literature_experimental_prompt` |
| `binding_record.py` | 26 | saved configuration record, `binding_id` = this path | — |
| `configuration.py` | 100 | same constructor as parent | `composition_information`, library controlled_response/gel storage |
| `source_contracts.py` | 51 | ROLES, `_WINDOW`/`_TABLE`/`_PAGE`, `_CHILDREN`, tools, role instructions, catalog order (same values as parent) | `communication`, `composition_information`, `domain`, `episode_bindings` (`reference_in_context`), `experimental_database_acquisition`, `library` |
| `goal.py` | 104 | task schema, commissioned task (page from `assignment['page']`), instructions, planning context | `communication`, `domain`, `numerical` (YieldController, YieldEstimate, YieldParameters, estimate_score_yield, NumericBand, STATUS_NORMAL; imported) |
| `from_parent.py` | 177 | reading assignment schema with selection, window checks, `prepare_assignment` | services.read_record (artifact size), services.proposed_annotation_for; ~40 library component imports |
| `from_parent_page.py` | 119 | `_parent_page_schema`, `_validate_parent_page` | ~40 library component imports |
| `task.py` | 215 | decision loop (identical to parent) | as parent: runtime (+module), bind_functions, episode_source_failure, providers; self.workflow.journal ×7, store ×9, execution_binding ×7, inprocess_replay ×4, ... ; tables runtime_actions ×8, runtime_model_calls ×2, runtime_episodes |
| `task_state.py` | 114 | state/restore/checkpoint (identical) | as parent; workflow.context, workflow.grains; runtime_actions ×5 |
| `task_decision.py` | 427 | model call / decision exchange (identical) | as parent; runtime_model_calls ×8 |
| `task_instructions.py` | 24 | instruction composition (identical) | source.workflow.* (7 members) |
| `decision_inputs.py` | 78 | identical | self.workflow.* (17 members) |
| `decision_state.py` | 59 | identical | self.workflow.* (24 members); runtime_actions ×2 |
| `decision_presentation.py` | 33 | identical | `episode_work_report`, controller_binding |
| `internal_summary.py` | 306 | decision context with `page = assignment.get('page')` | services.read_record ×5, own_outcomes, self.services.workflow.store ×2, workflow.store/run_id; runtime_actions ×2 |
| `received_evidence.py` | 269 | identical | services.record_selection ×3, self.services.workflow.store ×2, `method_loop.durable`, `library.intervention_execution_lookup` |
| `scientific_records.py` | 223 | identical | self.services.workflow.store ×18, run_id ×18 |
| `source_operations.py` | 219 | catalog, execute, custody with `page = assignment.get('page')`; plus the `sheet_key` match rule | services.tool_catalog, execute_tool, read_record ×4, self.services.workflow.store; `composition_information`, `literature_contract_error`, `bvbrc_appservice_adapters` |
| `source_references.py` | 35 | identical | services.reference_in_scope, read_record; `reference_in_context` |
| `credit.py` | 202 | identical | services.scientific_credit_for, scientific_credit, proposed_annotation_for, annotation_task_required; workflow.scientific_projector_for_context, projector_receipt_arguments, projection_view; runtime_actions ×4, runtime_report_attempts ×2 |
| `yield_estimator.py` | 103 | identical | YieldController ×4, YieldParameters ×3, estimate_score_yield ×3, YieldEstimate ×2, NumericBand ×2, STATUS_NORMAL ×2 |
| `to_parent.py` | 185 | identical | services.read_record ×3, self.services.workflow.store ×3, workflow.store ×2; 44 library imports |
| `report_delivery.py` | 33 | identical | self.workflow.release ×2, journal ×2, facts, pending_handles, source_credit_view, episode_bindings, binding_context; runtime_forms ×2 |
| `waiting.py` | 37 | identical | perform_selected_wait, execution_handle ×2, execution_backend |
| `grading/intervention_assessment.py` | 33 | identical | self.services.workflow.store, run_id |
| `scoring/intervention_main_sheet.py` | 13 | identical | self.services.workflow.store, run_id |

Full per-file counts: `runs/carry_over/calls/a106_03.tsv`.

## Carried over

Carried over 19 November 2026 by the table_evidence_extraction carry-over. Old code read from the disk repository's git at 97308b94c; the folder is a private binding of the ten-file form. Rows with "UNPLACED" are listed in docs/axis_restructure_20261117/carry_over_blocked/ for this episode.

| old file | name | kind | new place / reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | machinery: binding record of the old runner (the binding does not record itself) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | machinery: binding record of the old runner (the binding does not record itself) |
| configuration.py | LiteratureConfiguration | machinery | machinery: old configuration/constructor of the hook-era binding; settings are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| configuration.py | LiteratureConfiguration.__init__ | machinery | machinery: old configuration/constructor of the hook-era binding; settings are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | machinery: old configuration/constructor of the hook-era binding; settings are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| credit.py | _resolve | episode function | already in library: literature/grading/literature_task_credit.py::_resolve, called by task.py validate_source_lead |
| credit.py | validate_lead | episode function | task.py validate_source_lead (private re-expression on custody; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py lead_dispositions (library candidate) |
| credit.py | _current_assessments | episode function | credit.py current_assessments (library candidate) |
| credit.py | screening_answers | episode function | credit.py screening_answers (library candidate) |
| credit.py | LiteratureTaskCredit | episode function | credit.py (module functions answers, credit) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py credit |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py answers, assessment_answers |
| credit.py | LiteratureCredit | machinery | machinery: scientific_credit projector wiring of the old runner |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | machinery: services.scientific_credit invocation |
| credit.py | LiteratureCredit.credit_kind | machinery | machinery: credit kind hook |
| credit.py | LiteratureCredit.credit_view | machinery | machinery: credit view hook |
| credit.py | LiteratureCredit.credit_projector | machinery | machinery: projector hook |
| decision_inputs.py | LiteratureDecisionInputs | episode function | task.py decide (context) |
| decision_inputs.py | LiteratureDecisionInputs.decision_inputs | episode function | task.py decide (context) |
| decision_inputs.py | LiteratureDecisionInputs.current_decision_inputs | episode function | task.py decide (context) |
| decision_inputs.py | _a106_original_global_ValueError | machinery | machinery: provider patching / old global rebinding |
| decision_inputs.py | _a106_original_global_child_option_information | machinery | machinery: provider patching / old global rebinding |
| decision_inputs.py | _a106_original_global_set | machinery | machinery: provider patching / old global rebinding |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| decision_presentation.py | prepare_completed_work | episode function (unplaced) | UNPLACED: completed-work display of the rate-population route |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py action_yields (library yield_table) |
| decision_presentation.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| decision_state.py | LiteratureDecisionState | episode function | messages/internal_summary.py internal_summary |
| decision_state.py | LiteratureDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary |
| decision_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| episode.py | LiteratureEpisode | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode._role | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode.allowed_children | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode.child_roles | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | machinery: old binding class, role/child tables and context hooks; episode.py is now the member assignments |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | machinery: parent/child assignment schema routing of the old runner |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the rate-population requested_* properties are unplaced: no populate tool) |
| from_parent.py | LiteratureAssignment._validate_page | episode function (unplaced) | UNPLACED: Store checks of the page (source/artifact in scope); a wrong commission fails |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (selection checks that need no Store; Store checks not carried) |
| from_parent.py | LiteratureAssignment.prepare_assignment | machinery | machinery: private yield-binding filling and parent re-validation of the old runner; the commissioned task carries credit_unit |
| from_parent_page.py | OriginalPageAssignment | episode function (unplaced) | UNPLACED: validates the parent page episode's own page assignment from the Store; the parent commissions, a wrong commission fails (no check carried) |
| from_parent_page.py | OriginalPageAssignment._parent_page_schema | episode function (unplaced) | UNPLACED: validates the parent page episode's own page assignment from the Store; the parent commissions, a wrong commission fails (no check carried) |
| from_parent_page.py | OriginalPageAssignment._validate_parent_page | episode function (unplaced) | UNPLACED: validates the parent page episode's own page assignment from the Store; the parent commissions, a wrong commission fails (no check carried) |
| goal.py | _yield_kind | episode function | yield_estimator.py yield_controller (kind choice) |
| goal.py | _task_key | episode function | messages/read_from_parent.py task_key |
| goal.py | task_schema | episode function | messages/read_from_parent.py (literature_task field, TASK_KINDS, ANSWER_KINDS, read_from_parent checks) |
| goal.py | _return_sources | episode function | messages/final_to_parent.py RETURN_FORM (SCREENING, LEADS) |
| goal.py | _return_components | episode function (unplaced) | UNPLACED: rate-population return components; not declared |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py read_from_parent |
| goal.py | continuation_task | episode function | yield_estimator.py yield_controller (task from parent_input) |
| goal.py | LiteratureGoal | episode function | goal.py |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py credit_binding |
| grading/intervention_assessment.py | InterventionAssessment | episode function (unplaced) | UNPLACED: rate-population route (intervention grading cell reader); no populate tool offered |
| grading/intervention_assessment.py | InterventionAssessment._required_grading_repository | episode function (unplaced) | UNPLACED: rate-population route (intervention grading cell reader); no populate tool offered |
| grading/intervention_assessment.py | InterventionAssessment._intervention_source_cells | episode function (unplaced) | UNPLACED: rate-population route (intervention grading cell reader); no populate tool offered |
| grading/intervention_assessment.py | InterventionAssessment._intervention_grading_repository | episode function (unplaced) | UNPLACED: rate-population route (intervention grading cell reader); no populate tool offered |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | messages/internal_summary.py internal_summary / task.py decide |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary / task.py decide |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._population_task_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._concentration_window_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._measurement_comparison_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._summary_precision_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._endpoint_signal_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._controlled_response_bindings | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._gel_bindings | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._gel_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._native_rate_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._native_rate_domain_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| internal_summary.py | LiteratureSummary._native_rate_meaning_display_context | episode function (unplaced) | UNPLACED: rate-population display context of the old summary; no populate tool offered |
| received_evidence.py | LiteratureReceivedEvidence | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report |
| received_evidence.py | received_application_rows | episode function (unplaced) | UNPLACED: rate-population received facts/receipts; no fact cells returned |
| report_delivery.py | LiteratureReportDelivery | machinery | machinery: report delivery/release/redelivery machinery; the system returns final_to_parent |
| report_delivery.py | LiteratureReportDelivery.finish | machinery | machinery: report delivery/release/redelivery machinery; the system returns final_to_parent |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| scientific_records.py | LiteratureScientificRecords | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._a106_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._endpoint_signal_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._concentration_window_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._measurement_comparison_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._summary_precision_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._rate_grid_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v2_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v3_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._product_coupling_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._measurement_validation_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._ion_discrimination_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._channel_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._completion_time_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._active_site_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._perturbation_operand_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._parent_depletion_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._stoichiometric_balance_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._product_partition_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._binding_interaction_model_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._kinetic_model_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._ratio_source_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._controlled_response_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._gel_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._native_rate_meaning_repository | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function (unplaced) | UNPLACED: rate-population route (population operands/records); no populate tool offered |
| scoring/intervention_main_sheet.py | InterventionMainSheet | episode function (unplaced) | UNPLACED: rate-population route (A106 subscore repository); no populate tool offered |
| scoring/intervention_main_sheet.py | InterventionMainSheet._a106_subscore_repository | episode function (unplaced) | UNPLACED: rate-population route (A106 subscore repository); no populate tool offered |
| scoring/intervention_main_sheet.py | InterventionMainSheet.automatic_score_judgments | episode function (unplaced) | UNPLACED: rate-population route (A106 subscore repository); no populate tool offered |
| scoring/intervention_main_sheet.py | InterventionMainSheet.complete_score_judgment | episode function (unplaced) | UNPLACED: rate-population route (A106 subscore repository); no populate tool offered |
| source_contracts.py | _required_grading_logic | episode function (unplaced) | UNPLACED: required grading logic of the rate-population route; raises nothing here, not called |
| source_contracts.py | _population_catalog | episode function (unplaced) | UNPLACED: population catalog of the rate-population route; no populate tool offered |
| source_operations.py | LiteratureOperations | episode function | task.py |
| source_operations.py | LiteratureOperations.permitted_common_actions | machinery | machinery: old common-action permission list (tool/reason/child/wait/redeliver_report) |
| source_operations.py | LiteratureOperations.reasoning_action_schema | episode function | task.py reason_schema |
| source_operations.py | LiteratureOperations.reasoning_has_task_content | episode function | task.py empty_commit |
| source_operations.py | LiteratureOperations.execute_reasoning | episode function | task.py reason |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py catalog, offered, selection_schema |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool and the access tools |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted (includes this episode's sheet_key rule: literature_table_sheet_mismatch) |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function (unplaced) | UNPLACED: populate branch of the rate-population route |
| source_operations.py | prepare_analysis_contract | episode function (unplaced) | UNPLACED: literature.intervention_analysis.contract needs the old execution binding of the BV-BRC service; no such tool |
| source_references.py | LiteratureReferences | episode function | task.py within_source |
| source_references.py | LiteratureReferences._require | episode function | library records/received_records.py read_record_in_scope, called by task.py within_source |
| source_references.py | LiteratureReferences._artifact | episode function (unplaced) | UNPLACED: artifact-of-representation check of the page validation (Store check; wrong commission fails) |
| source_references.py | LiteratureReferences._within_source | episode function | task.py within_source |
| source_references.py | LiteratureReferences.resolve | episode function (unplaced) | UNPLACED: reference-in-scope resolution of the old runner; custody holds the records |
| task.py | LiteratureTask | episode function | task.py |
| task.py | LiteratureTask.instructions | episode function | task.py instructions |
| task.py | LiteratureTask.next | episode function | task.py decide |
| task.py | LiteratureTask.apply_response | episode function | task.py action |
| task.py | LiteratureTask.execute | episode function | task.py TOOLS and the tool functions |
| task.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| task_decision.py | LiteratureTaskDecision | episode function | task.py decide |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.interpretation_context | episode function | task.py decide (context) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_OSError | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_TypeError | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_ValidationError | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_ValueError | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global__action_generation_schema | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global__json | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global__plain | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_child_option_information | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_instructional_model_context | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_isinstance | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_len | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_lookup_attempts | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_model_snapshot | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_requested_contract_information | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_schema_failure_diagnostic | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_sqlite3 | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_state_frame | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_str | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _a106_original_global_type | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_decision.py | _bind_original_task_runtime_providers | machinery | machinery: decision-exchange loop / model-call recording / contract exchange validation |
| task_instructions.py | instructions | episode function | task.py instructions |
| task_state.py | LiteratureTaskState | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.__init__ | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.record_execution_failure | episode function | task.py run_access_tool (failure_outcome of an executed operation) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.restore | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.record_effect | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | LiteratureTaskState.checkpoint | machinery | machinery: checkpoint/restore/state bookkeeping of the old runner |
| task_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | LiteratureReport._rate_fact_sources | episode function (unplaced) | UNPLACED: rate-population fact sources; not declared |
| to_parent.py | LiteratureReport._rate_facts | episode function (unplaced) | UNPLACED: rate-population facts; not returned |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | LiteratureWaiting | machinery | machinery: wait/suspension machinery; no wait tool is offered |
| waiting.py | LiteratureWaiting.supports_wait | machinery | machinery: wait/suspension machinery; no wait tool is offered |
| waiting.py | LiteratureTaskWaiting | machinery | machinery: wait/suspension machinery; no wait tool is offered |
| waiting.py | LiteratureTaskWaiting._execute_selected_wait | machinery | machinery: wait/suspension machinery; no wait tool is offered |
| waiting.py | LiteratureTaskWaiting.suspension_changed | machinery | machinery: wait/suspension machinery; no wait tool is offered |
| waiting.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching / old global rebinding |
| yield_estimator.py | validate_yield_bindings | machinery | machinery: private yield-binding link check; the controller is always built from the commissioned task |
| yield_estimator.py | _RemainingCommissionedCredit | episode function | yield_control CompletionYieldController (target = credit_unit) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | episode function | yield_control CompletionYieldController |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | machinery: as_record of the old forecast band projector |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | episode function | yield_control CompletionYieldController |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | episode function | yield_control CompletionYieldController |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | machinery: old controller transition hook |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | yield_estimator.py yield_controller (task from parent_input) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
