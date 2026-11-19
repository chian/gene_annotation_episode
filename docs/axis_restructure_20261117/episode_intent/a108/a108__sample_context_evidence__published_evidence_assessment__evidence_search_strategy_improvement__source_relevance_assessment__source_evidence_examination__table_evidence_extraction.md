# A108 source_evidence_examination / table_evidence_extraction (role `literature_table`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/<file>` at 97308b94c. Only this folder's own files and its `grading/` and `scoring/` were read. Every file was also diffed against the parent `source_evidence_examination` folder. Where this file says "as parent", the text is identical apart from the package path and role string. The full detail is in the parent's intent file, `a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination.md`.

Binding class `LiteratureEpisode`. `binding_path = '.../source_evidence_examination/table_evidence_extraction'`, `commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_table',)`, `entry_roles = ()`, `decision_source_type = LiteratureTask`, `decision_prompt_renderer = render_literature_experimental_prompt`.

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_table']`): "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows."
- Instructions are this role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK` (old shared `a108.library.literature_a108_prompt`).
- Investigates one selected table or sheet and its scientific meaning (rows, headers, conditions, footnotes). The parent commissions it as `literature_table`.

## Task and instructions

`task.py` is the same as the parent's apart from its docstring. `task_state.py`, `task_decision.py`, `task_instructions.py`, `decision_inputs.py` and `decision_presentation.py` are byte-identical to the parent's. That covers the old iterative decision source, the empty-reasoning rejection, grading-coupled reasoning, failed actions entering the iterator with credit, `SourceEnd('source_failed')` on a model-call failure, and the redelivery/exchange instruction text.

## What it reads from its parent's assignment (`from_parent.py`, 111 lines)

- Schema: `obj({version: const 'reading_assignment_v1', page: _PAGE, selection: anyOf[_TABLE, _WINDOW]})`. On top of that come the same `literature_task` (goal.task_schema), `proposed_annotation_ref` and A108 grading/aggregation requested-component properties as the parent. These are required under `private_yield_binding`, with `credit_unit` and `yield_settings` filled from the owner's `yield_bindings`.
- Selection: either `_TABLE{source_ref, sheet_key, offset, limit, header_row|null, where{column A-Z|null, match equals/contains, value, case_sensitive}|null}` for XLSX, or one `_WINDOW` for an article XML table read through an exact original-source window.
- Window checks: each window's `source_ref` must equal `page.source_ref` (`literature_reading_source_mismatch`). If the window has a representation, it must equal the page's (`literature_reading_representation_mismatch`), and `offset` must be at most the artifact size (`source_offset_out_of_bounds`).
- `page` is validated as the parent's is: source in scope, artifact matching the representation, context and prior-delivery refs in scope.
- When the commissioning parent's role is `literature_page`, the binding validates the parent's own page assignment (`_parent_page_schema` / `_validate_parent_page`). It then requires this child's `page.source_ref` to lie within the parent's assigned source (`literature_reading_outside_assigned_source`). This check exists only in the children.
- The proposed annotation must equal the parent's.
- `goal.commissioned_task` takes `assigned_page = assignment.get('page', None)` (the parent uses the assignment itself). Task source refs and screening spans must be on this page's source and artifact.

## Children it may commission

None. `_CHILDREN = {'literature_table': ()}`, and `episode.py` has no `child_request_preparer` or `child_report_receiver` and no to_child/from_child files. `permitted_common_actions` still lists `'child'` as the parent's does, but `child_roles` returns an empty tuple.

## Decision state and what it shows the model

As parent. `internal_summary.decision_context` uses `page = assignment.get('page')`, so `literature_assignment` is the whole `reading_assignment_v1` (page + selection), and custody covers the page source. The keys `own_literature_outcomes`, `literature_history_meaning`, `literature_examined_source_inputs`, `literature_experimental_work` (aspect `source_experimental_evidence`, A108), `literature_received_fact_display`, `literature_owned_population_sources`, `literature_selected_population_attempt`, `literature_completed_work` / `literature_current_scoring_sheets` and `literature_goal_plan` (when `literature_task` is present) are all as in the parent.

## Tools it offers (`source_operations.py`, 113 lines)

As parent: the `_A108_ACCESS_TOOLS` subset of the services catalog, `execution.estimate` narrowed to xlsx, the population catalog (A108 grading populate and aggregate), and `source_location_inputs`. All reads must stay within `page.source_ref`. Only in this child, `source.xlsx.rows` must use the assignment's `selection.sheet_key` when one is given (`literature_table_sheet_mismatch`). There is no wait. Reasoning goes through `grading/contextual_interpretation.py`, identical to the parent's: the required-grading action schema, `source_lead` for verified_source_leads tasks, `validate_lead`, and the provider `literature.a108.context_grading`.

## How its credit is counted

`credit.py` is as parent. `LiteratureTaskCredit` counts `credit_unit × answered items`, finite and unbounded:
- verified_source_leads: relevant lead dispositions per canonical source, from own reason results and admitted child forms;
- screening: one item when own `no_applicable_evidence` spans cover every requested span;
- assessment: at most one current retained, target-eligible assessment anchored in `task.source_refs`.

`credit_kind = 'scientific'`, and the credit view goes through `services.scientific_credit_for` and the workflow projector.

## Continuation

`yield_estimator.py` is as parent. The task keys are `A108:verified_source_leads` → **accumulation**, and `A108:source_answer:{assessment,screening}` → `remaining_commissioned_credit`, which is **completion with a target** (target = `credit_unit`). Settings are `{credit_unit, kind, cutoff, uncertainty_alpha}` per task key. Without `private_yield_binding` there is no private controller.

## What it reports to its parent

`to_parent.py` and `received_evidence.py` are as parent. It reports `literature_a108_grading_cells`, `literature_a108_aggregation_cells` (requested components only), `literature_screening_answers` (screening tasks), `literature_source_lead_dispositions` (lead tasks), `literature_completed_work` and `literature_current_scoring_sheets`. The report must equal the saved work and the requested sheet subset. The parent's `from_child_table_evidence_extraction.py` receives it, and the A108 cells reach the parent through `received_form_references`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| __init__.py | 1 | none | none |
| binding_record.py | 16 | as parent (binding_id = this path) | none |
| configuration.py | 31 | as parent | composition_information CONTRACT_INFORMATION_PROFILE |
| credit.py | 221 | as parent | as parent: BindingContext.*, communication, domain, numerical yield names, library.literature_assay_inputs, finding_validity, scientific_findings, runtime_actions/runtime_report_attempts SQL, services.{scientific_credit_for,scientific_credit,proposed_annotation_for,annotation_task_required,workflow}, workflow.{scientific_projector_for_context,projector_receipt_arguments,projection_view} |
| decision_inputs.py | 36 | identical | as parent (self.workflow.* context builders, runtime FACT_*, runtime_actions) |
| decision_presentation.py | 21 | identical | runtime _category_yield_parameters/yield_table; episode_work_report; self.workflow.controller_binding |
| episode.py | 62 | role guard `literature_table`, no children, no preparers/receivers | BindingContext.{role,path}; library.literature_experimental_prompt |
| from_parent.py | 111 | reading_assignment_v1 with selection anyOf[_TABLE, _WINDOW]; window checks; within parent's page source | BindingContext.{assignment,role,scope} and parent.{role,assignment,scope}; services.{read_record,proposed_annotation_for}; library grading/aggregation storage |
| goal.py | 104 | as parent, with `assignment.get('page', None)` | BindingContext.{assignment,request,role}; communication; domain; numerical (duplicated header); library.literature_a108_prompt |
| internal_summary.py | 106 | as parent, with `page = assignment.get('page')` | BindingContext.*; services.{own_outcomes,workflow}; workflow.{store,run_id}; runtime_actions SQL; library.literature_source_inputs/_task_families/_work_report |
| received_evidence.py | 90 | as parent | BindingContext.*; services.{record_selection,workflow}; library.literature_sheet_updates; method_loop.durable; domain.canonical |
| scientific_records.py | 16 | as parent | library grading/aggregation storage |
| source_contracts.py | 37 | `_CHILDREN = {'literature_table': ()}`; own role instruction | communication; composition_information; domain; episode_bindings.reference_in_context; library.literature_population_catalog, literature_required_grading |
| source_operations.py | 113 | as parent with `page = assignment.get('page')`; sheet_key guard | BindingContext.*; services.{tool_catalog,execute_tool,read_record}; composition_information.CONTRACT_ARGUMENT_TRANSPORT; literature_contract_error; library.literature_assay_inputs |
| source_references.py | 35 | as parent | services.{reference_in_scope,read_record}; episode_bindings.reference_in_context |
| task.py | 209 | as parent | as parent (runtime helpers, self.workflow.* runner, providers.ModelCallError, episode_source_failure, runtime_episodes/actions/model_calls/forms) |
| task_decision.py | 351 | identical | as parent (runtime exchange helpers, providers internals, self.workflow.*, receipts, runtime_model_calls) |
| task_instructions.py | 28 | identical | runtime_prompt; library.literature_investigation_prompt; workflow.* |
| task_state.py | 108 | identical | runtime Episode/ActionLeaf/...; self.workflow.* replay/completions; episode_source_failure; runtime_actions |
| to_parent.py | 64 | as parent | BindingContext.*; services.{workflow,read_record}; library literature_sheet_updates/_work_report/_a108_grading_storage/_a108_aggregation_storage/_numerical_contracts |
| waiting.py | 8 | no wait | none |
| yield_estimator.py | 108 | as parent | numerical YieldController/YieldParameters/YieldEstimate/NumericBand/STATUS_NORMAL/estimate_score_yield; BindingContext.role |
| grading/__init__.py | 0 | none | none |
| grading/contextual_interpretation.py | 49 | as parent | BindingContext.*; services.workflow.store; literature_contract_error |
| grading/contextual_subscoring.py | 14 | as parent | library.literature_a108_grading_storage; services.workflow.{store,run_id} |
| scoring/__init__.py | 0 | none | none |
| scoring/contextual_main_sheet.py | 11 | as parent | library.literature_a108_aggregation_storage; services.workflow.{store,run_id} |

The per-file counts are in `runs/carry_over/calls/a108_02.tsv` (episode `table_evidence_extraction`).

## Differences from the parent and siblings

- Only `from_parent.py` (the selection shape), `source_contracts.py` (role instruction, no children), `episode.py` (no child wiring) and `source_operations.py` (sheet_key guard) carry content that differs from the parent. Credit, yield, reporting, grading and the decision machinery are the same in all four.
- The three children differ from one another only in role, instruction and selection: targeted takes `selection.spans[]` of `_WINDOW` (minItems 1), ordered takes one `_WINDOW`, and table takes `anyOf[_TABLE, _WINDOW]`, with the table child alone enforcing the `sheet_key` match.

## Carried over

Carried over 19 November 2026 by the a108 table_evidence_extraction carry-over. Old code read from the disk repository's git (`/home/chia/repos/gene_annotation_episode_disk`) at 97308b94c; the folder is a private binding of the ten-file form without children (no `msg_to_child.py`, no `read_from_child.py`). Files named below are in this episode folder. "library candidate" marks a private copy of a function that is not in `episode_support/` yet. Items that could not be placed or are blocked are in `docs/axis_restructure_20261117/carry_over_blocked/` for this episode.

| old file | name | kind | new place / reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | machinery: binding record of the old runner (the binding does not record itself; as_record of the binding is deleted) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | machinery: binding record of the old runner (the binding does not record itself; as_record of the binding is deleted) |
| configuration.py | LiteratureConfiguration | machinery | machinery: hook-era configuration/constructor of the binding; the run values are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| configuration.py | LiteratureConfiguration.__init__ | machinery | machinery: hook-era configuration/constructor of the binding; the run values are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | machinery: hook-era configuration/constructor of the binding; the run values are the episode settings (cost, parameters, tool_registry, knowledge_library_directory) |
| credit.py | _resolve | episode function | task.py resolve_aliases (private copy; library candidate) |
| credit.py | lead_schema | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | lead_return_schema | episode function | messages/final_to_parent.py LEADS field of RETURN_FORM (list; the lead shape is task.py lead_schema, checked by validate_lead before a lead enters the summary) |
| credit.py | validate_lead | episode function | task.py validate_lead (on custody: store.require, store.refs, store.get_artifact; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py lead_dispositions (own leads from the summary; the admitted-child-form branch is not carried: no child) |
| credit.py | screening_schema | episode function | messages/final_to_parent.py SCREENING field of RETURN_FORM (list; the answer is built by credit.py screening_answers) |
| credit.py | _current_assessments | episode function | credit.py current_assessments (FindingValidity, target_eligible: library not carried) |
| credit.py | screening_answers | episode function | credit.py screening_answers (spans from the summary, read from unit outcomes) |
| credit.py | LiteratureTaskCredit | episode function | credit.py (module functions credit, answers, credit_binding) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (the credit projector as_record is episode content) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py credit and answers (hypothesis in scope and rooted at a target subject; the credit_unit times the answers; the request-mismatch check and read_snapshot are not carried) |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py answers, assessment_answers |
| credit.py | LiteratureCredit | machinery | machinery: credit hook mixin of the old binding; the credit is credit(summary, records) in credit.py |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | machinery: services.scientific_credit / workflow.projection_view and projector receipt arguments of the old runner |
| credit.py | LiteratureCredit.credit_kind | machinery | machinery: credit_kind 'scientific' (kind routing of the old runner) |
| credit.py | LiteratureCredit.credit_view | machinery | machinery: services.scientific_credit view of the old runner; the number is credit(summary, records) |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py credit (the projector is called as credit(summary, records)) |
| decision_inputs.py | build_decision_inputs | episode function | task.py decide (the model context) and messages/internal_summary.py internal_summary (working state, last outcome, visual evidence, credit binding, yield table); the journal SQL, receipts, pending work, report-delivery and workflow context builders are machinery |
| decision_presentation.py | prepare_completed_work | machinery | machinery: completed_action_reports of the old runner (workflow); the literature_completed_work path is unplaced (see unplaced) |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py action_yields = yield_table(view.controller_state, forecast_unit=...) shown by task.py decide |
| episode.py | LiteratureEpisode | episode function | episode.py class TableEvidenceExtraction(EpisodeBinding) |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | machinery: contract-information freezing of the old runner (README 5 item 16) |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | machinery: contract-information freezing of the old runner (README 5 item 16) |
| episode.py | LiteratureEpisode._role | machinery | machinery: role guard of a shared per-kind class; this episode is its own binding |
| episode.py | LiteratureEpisode.allowed_children | machinery | machinery: child registry lookup; CHILD_SLOTS = {} in task.py (no child) |
| episode.py | LiteratureEpisode.child_roles | machinery | machinery: child registry lookup; CHILD_SLOTS = {} in task.py (no child) |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | machinery: context hook of the old runner |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | machinery: the parent-side schema of a child assignment (msg_to_child of a parent); this episode has no child |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and task_schema (the yield_settings property is the episode settings; credit_unit stays in the task) |
| from_parent.py | LiteratureAssignment._validate_page | machinery | machinery: Store checks of the commission (source artifact matches the representation, refs in scope); a wrong commission fails where its records are read |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (page/selection checks without the Store; the artifact-size check of a window and the in-scope reads are commission checks, not carried) |
| from_parent.py | LiteratureAssignment.prepare_assignment | machinery | machinery: parent-side assignment preparation, yield-binding injection (now settings) and the page-source check against the parent (commission checks) |
| from_parent.py | LiteratureAssignment._parent_page_schema | machinery | machinery: check of the parent's own page assignment (commission check) |
| from_parent.py | LiteratureAssignment._validate_parent_page | machinery | machinery: check of the parent's own page assignment (commission check) |
| goal.py | _yield_kind | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | _task_key | episode function | messages/read_from_parent.py task_key (private copy; library candidate) |
| goal.py | task_schema | episode function | messages/read_from_parent.py task_schema (private copy; library candidate) |
| goal.py | _return_sources | machinery | machinery: reads the request report contract (x-source fields); the parent selects fields in msg_to_child |
| goal.py | _return_components | machinery | machinery: reads the request report contract; the parent selects fields in msg_to_child |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py commissioned_task (checks over the assignment; the checks against the request report contract are not carried) |
| goal.py | continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"], read by yield_estimator.py) |
| goal.py | LiteratureGoal | episode function | goal.py (BINDING_PATH, GOAL, UNIT, RESULT) |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (role instruction + A108_CONTEXT_TASK + A108_READING_TASK, already in library: literature/prompts/literature_prompt.py); task.py instructions |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py literature_goal_plan |
| grading/contextual_interpretation.py | ContextualInterpretation | episode function | task.py (reason_schema, reasoning_has_task_content, reason) |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_action_schema | episode function | task.py reason_schema (required-grading action schema from the library, plus source_lead) |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_has_task_content | episode function | task.py reasoning_has_task_content (used by action) |
| grading/contextual_interpretation.py | ContextualInterpretation.execute_reasoning | episode function | task.py reason (literature_required_grading.execute: commit and grading sheet in one action; source lead in the same transaction) |
| grading/contextual_subscoring.py | ContextualSubscoring | episode function | task.py repositories (the library LiteratureA108GradingRepository, handed ctx.store) |
| grading/contextual_subscoring.py | ContextualSubscoring._required_grading_repository | episode function | task.py repositories (the library LiteratureA108GradingRepository, handed ctx.store) |
| grading/contextual_subscoring.py | ContextualSubscoring._a108_grading_repository | episode function | task.py repositories (the library LiteratureA108GradingRepository, handed ctx.store) |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py |
| internal_summary.py | LiteratureSummary.initial_decision_context | machinery | machinery: the root-only reference_evidence_parent context (applies only to role annotation at path length 1), not this episode's |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning, literature_experimental_work, received-fact display, population context, literature_goal_plan); literature_examined_source_inputs and current_report_facts are unplaced |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py literature_owned_population_sources (re-expressed over the unit outcomes that saved a sheet; the SQL over the operations tables is not carried) |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py literature_owned_population_sources and literature_selected_population_attempt (latest failed tool outcome) |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py received_fact_display (held records; the source metadata of the old display is unplaced) |
| received_evidence.py | LiteratureReceivedEvidence | machinery | machinery: parent-side receipt of a child report; this role is a leaf and always in ROLES, so its received facts are {} |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | machinery: receipt of a child report (empty for this role) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | machinery: receipt of a child report (empty for this role) |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | machinery: receipt of a child report |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | machinery: receipts ledger / received-cell bookkeeping; returned records are record_refs fields |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | machinery: receipts ledger tokens |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (the lead and screening answers equal the saved work; the A108 cells are produced by messages/internal_summary.py saved_cells from the same saved sheets, so the old repository.validate_fact_values comparison is by construction) |
| scientific_records.py | LiteratureScientificRecords | machinery | machinery: hook mixin of the old runner |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function | messages/internal_summary.py GRADING_NAMESPACE / AGGREGATION_NAMESPACE and saved_cells; messages/final_to_parent.py GRADING_CELLS / AGGREGATION_CELLS; requested components in messages/read_from_parent.py |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | machinery | machinery: automatic score hook of the old runner (returned []) |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | machinery | machinery: automatic score hook of the old runner (raised 'a108_automatic_judgment_unavailable') |
| scoring/contextual_main_sheet.py | ContextualMainSheet | episode function | task.py repositories (the library LiteratureA108AggregationRepository, handed ctx.store, reading grading cells through the grading repository) |
| scoring/contextual_main_sheet.py | ContextualMainSheet._a108_aggregation_repository | episode function | task.py repositories (the library LiteratureA108AggregationRepository, handed ctx.store, reading grading cells through the grading repository) |
| source_contracts.py | _a108_population_catalog | episode function | task.py catalog (population_catalog from the library; already in library: literature/forms/sample_context_evidence/literature_population_catalog.py) |
| source_contracts.py | _required_grading_logic | episode function | task.py reason (literature_required_grading imported from the library; already in library: literature/grading/sample_context_evidence/literature_required_grading.py) |
| source_operations.py | LiteratureOperations | episode function | task.py |
| source_operations.py | LiteratureOperations.permitted_common_actions | machinery | machinery: common-action set of the old loop (tool, reason, child, redeliver_report); the offered units are task.py offered() |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py offered, catalog, INPUT_SCHEMAS, DESCRIPTIONS (the A108 access tools the library implements, execution.estimate only with timing statistics, the two population operations) |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool, populate, TOOLS (invalid outcome for a contract error; state.query record authorization) |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted and authorize_source (schema, page-source restriction, sheet_key rule, population sources, repository authorization) |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function | task.py populate (read_source passed to materialize_text_witness_inputs) |
| source_references.py | LiteratureReferences | episode function | task.py within_source |
| source_references.py | LiteratureReferences._require | machinery | machinery: services.reference_in_scope + read_record; the library read_record_in_scope is called in task.py within_source |
| source_references.py | LiteratureReferences._artifact | machinery | machinery: only used by the page-artifact check of the commission (commission check, not carried) |
| source_references.py | LiteratureReferences._within_source | episode function | task.py within_source (private copy; library candidate) |
| source_references.py | LiteratureReferences.resolve | machinery | machinery: reference_in_context resolver of the old report validation (validate_form not built for A108) |
| task.py | LiteratureTask | machinery | machinery: the old decision-loop class (replay, exchange, delivery, checkpoint) |
| task.py | LiteratureTask.next | machinery | machinery: old loop: replay slots, completions, pending deliveries, SourceEnd on model-call failure; the decision itself is task.py decide |
| task.py | LiteratureTask.apply_response | episode function | task.py action (the validation of the model answer, the empty-reasoning rejection); the recorder, redelivery and report_update parts are machinery |
| task.py | LiteratureTask.execute | episode function | task.py TOOLS (each selected tool/reason runs as one unit and returns its outcome); the journal rows, receipts and controller_value are machinery |
| task.py | LiteratureTask.finish | episode function | messages/final_to_parent.py final_to_parent (the report is filled from the summary; forms, release and runtime_forms are machinery) |
| task_decision.py | LiteratureTaskDecision | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide (the model context and instructions); the saved-request checks, journal rows, receipts and exchange are machinery |
| task_decision.py | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | machinery: decision exchange loop, saved-exchange checks, provider patching and conversation state of the old runner |
| task_instructions.py | instructions | episode function | task.py instructions (INSTRUCTIONS + goal + REASONING_COMMIT_REQUIREMENT + knowledge text; the history, delivery and wait spans are not carried) |
| task_state.py | LiteratureTaskState | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.__init__ | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.suspension_changed | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.record_execution_failure | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.restore | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.record_effect | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| task_state.py | LiteratureTaskState.checkpoint | machinery | machinery: state restore, checkpoint, effect and execution-failure recording of the old runner |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (GRADING_CELLS, AGGREGATION_CELLS, SCREENING, LEADS; credit and finding required) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent (screening and lead answers, cells selected by the parent); cells computed in messages/internal_summary.py |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py COMPLETED_WORK / CURRENT_SHEETS selectable fields; they raise where selected (UNPLACED / BLOCKED-ON-STORE-ACCESS) |
| to_parent.py | LiteratureReport._a108_fact_sources | episode function | messages/final_to_parent.py GRADING_CELLS and AGGREGATION_CELLS fields (the old RETURN_MEANINGS text for them is not in the library: own meanings) |
| to_parent.py | LiteratureReport._a108_facts | episode function | messages/internal_summary.py saved_cells (BLOCKED-ON-STORE-ACCESS: repository.fact_cells -> records.table(T).select) |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (assignment check, validate_form step raising validate_form_not_built:a108, answers equal saved work) |
| waiting.py | LiteratureWaiting | machinery | machinery: wait support of the old loop (supports_wait); this episode offers no wait tool |
| waiting.py | LiteratureWaiting.supports_wait | machinery | machinery: wait support of the old loop (supports_wait); this episode offers no wait tool |
| yield_estimator.py | validate_yield_bindings | machinery | machinery: check of the owner's yield declarations at construction; settings are journaled at link and the controllers check their own values |
| yield_estimator.py | _RemainingCommissionedCredit | machinery | machinery: episode-local estimator, replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | machinery | machinery: episode-local estimator, replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | machinery: episode-local estimator, replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | machinery | machinery: episode-local controller class, replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | machinery | machinery: episode-local controller class, replaced by CompletionYieldController |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | machinery: transitioned/next_epoch of an episode-local controller (deleted) |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"]) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (the "no private yield binding returns None" case is not carried) |
