# A108 source_evidence_examination / passage_evidence_extraction (role `literature_targeted`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/<file>` at 97308b94c. Only this folder's own files and its `grading/` and `scoring/` were read. Every file was also diffed against the parent `source_evidence_examination` folder. Where this file says "as parent", the text is identical apart from the package path and role string. The full detail is in the parent's intent file, `a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination.md`.

Binding class `LiteratureEpisode`. `binding_path = '.../source_evidence_examination/passage_evidence_extraction'`, `commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_targeted',)`, `entry_roles = ()`, `decision_source_type = LiteratureTask`, `decision_prompt_renderer = render_literature_experimental_prompt`.

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_targeted']`): "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation."
- Instructions are this role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK` (old shared `a108.library.literature_a108_prompt`).
- Reads supplied source-bound passages for the assigned question. The parent commissions it as `literature_targeted` (the "targeted-passage investigation").

## Task and instructions

`task.py` is the same as the parent's apart from its docstring. `task_state.py`, `task_decision.py`, `task_instructions.py`, `decision_inputs.py` and `decision_presentation.py` are byte-identical to the parent's. That covers the old iterative decision source, the empty-reasoning rejection, grading-coupled reasoning, failed actions entering the iterator with credit, `SourceEnd('source_failed')` on a model-call failure, and the redelivery/exchange instruction text.

## What it reads from its parent's assignment (`from_parent.py`, 111 lines)

- Schema: `obj({version: const 'reading_assignment_v1', page: _PAGE, selection: obj({spans: array minItems 1 of _WINDOW})})`. On top of that come the same `literature_task` (goal.task_schema), `proposed_annotation_ref` and A108 grading/aggregation requested-component properties as the parent. These are required under `private_yield_binding`, with `credit_unit` and `yield_settings` filled from the owner's `yield_bindings`.
- Selection: `selection.spans`, one or more `_WINDOW{source_ref, representation, offset>=0, limit>=1}`. Every span is checked, and the spans stay separate (no concatenated quotation).
- Window checks: each window's `source_ref` must equal `page.source_ref` (`literature_reading_source_mismatch`). If the window has a representation, it must equal the page's (`literature_reading_representation_mismatch`), and `offset` must be at most the artifact size (`source_offset_out_of_bounds`).
- `page` is validated as the parent's is: source in scope, artifact matching the representation, context and prior-delivery refs in scope.
- When the commissioning parent's role is `literature_page`, the binding validates the parent's own page assignment (`_parent_page_schema` / `_validate_parent_page`). It then requires this child's `page.source_ref` to lie within the parent's assigned source (`literature_reading_outside_assigned_source`). This check exists only in the children.
- The proposed annotation must equal the parent's.
- `goal.commissioned_task` takes `assigned_page = assignment.get('page', None)` (the parent uses the assignment itself). Task source refs and screening spans must be on this page's source and artifact.

## Children it may commission

None. `_CHILDREN = {'literature_targeted': ()}`, and `episode.py` has no `child_request_preparer` or `child_report_receiver` and no to_child/from_child files. `permitted_common_actions` still lists `'child'` as the parent's does, but `child_roles` returns an empty tuple.

## Decision state and what it shows the model

As parent. `internal_summary.decision_context` uses `page = assignment.get('page')`, so `literature_assignment` is the whole `reading_assignment_v1` (page + selection), and custody covers the page source. The keys `own_literature_outcomes`, `literature_history_meaning`, `literature_examined_source_inputs`, `literature_experimental_work` (aspect `source_experimental_evidence`, A108), `literature_received_fact_display`, `literature_owned_population_sources`, `literature_selected_population_attempt`, `literature_completed_work` / `literature_current_scoring_sheets` and `literature_goal_plan` (when `literature_task` is present) are all as in the parent.

## Tools it offers (`source_operations.py`, 110 lines)

As parent: the `_A108_ACCESS_TOOLS` subset of the services catalog, `execution.estimate` narrowed to xlsx, the population catalog (A108 grading populate and aggregate), and `source_location_inputs`. All reads must stay within `page.source_ref`. There is no wait. Reasoning goes through `grading/contextual_interpretation.py`, identical to the parent's: the required-grading action schema, `source_lead` for verified_source_leads tasks, `validate_lead`, and the provider `literature.a108.context_grading`.

## How its credit is counted

`credit.py` is as parent. `LiteratureTaskCredit` counts `credit_unit × answered items`, finite and unbounded:
- verified_source_leads: relevant lead dispositions per canonical source, from own reason results and admitted child forms;
- screening: one item when own `no_applicable_evidence` spans cover every requested span;
- assessment: at most one current retained, target-eligible assessment anchored in `task.source_refs`.

`credit_kind = 'scientific'`, and the credit view goes through `services.scientific_credit_for` and the workflow projector.

## Continuation

`yield_estimator.py` is as parent. The task keys are `A108:verified_source_leads` → **accumulation**, and `A108:source_answer:{assessment,screening}` → `remaining_commissioned_credit`, which is **completion with a target** (target = `credit_unit`). Settings are `{credit_unit, kind, cutoff, uncertainty_alpha}` per task key. Without `private_yield_binding` there is no private controller.

## What it reports to its parent

`to_parent.py` and `received_evidence.py` are as parent. It reports `literature_a108_grading_cells`, `literature_a108_aggregation_cells` (requested components only), `literature_screening_answers` (screening tasks), `literature_source_lead_dispositions` (lead tasks), `literature_completed_work` and `literature_current_scoring_sheets`. The report must equal the saved work and the requested sheet subset. The parent's `from_child_passage_evidence_extraction.py` receives it, and the A108 cells reach the parent through `received_form_references`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| __init__.py | 1 | none | none |
| binding_record.py | 16 | as parent (binding_id = this path) | none |
| configuration.py | 31 | as parent | composition_information CONTRACT_INFORMATION_PROFILE |
| credit.py | 221 | as parent | as parent: BindingContext.*, communication, domain, numerical yield names, library.literature_assay_inputs, finding_validity, scientific_findings, runtime_actions/runtime_report_attempts SQL, services.{scientific_credit_for,scientific_credit,proposed_annotation_for,annotation_task_required,workflow}, workflow.{scientific_projector_for_context,projector_receipt_arguments,projection_view} |
| decision_inputs.py | 36 | identical | as parent (self.workflow.* context builders, runtime FACT_*, runtime_actions) |
| decision_presentation.py | 21 | identical | runtime _category_yield_parameters/yield_table; episode_work_report; self.workflow.controller_binding |
| episode.py | 62 | role guard `literature_targeted`, no children, no preparers/receivers | BindingContext.{role,path}; library.literature_experimental_prompt |
| from_parent.py | 111 | reading_assignment_v1 with selection obj({spans: array minItems 1 of _WINDOW}); window checks; within parent's page source | BindingContext.{assignment,role,scope} and parent.{role,assignment,scope}; services.{read_record,proposed_annotation_for}; library grading/aggregation storage |
| goal.py | 104 | as parent, with `assignment.get('page', None)` | BindingContext.{assignment,request,role}; communication; domain; numerical (duplicated header); library.literature_a108_prompt |
| internal_summary.py | 106 | as parent, with `page = assignment.get('page')` | BindingContext.*; services.{own_outcomes,workflow}; workflow.{store,run_id}; runtime_actions SQL; library.literature_source_inputs/_task_families/_work_report |
| received_evidence.py | 90 | as parent | BindingContext.*; services.{record_selection,workflow}; library.literature_sheet_updates; method_loop.durable; domain.canonical |
| scientific_records.py | 16 | as parent | library grading/aggregation storage |
| source_contracts.py | 37 | `_CHILDREN = {'literature_targeted': ()}`; own role instruction | communication; composition_information; domain; episode_bindings.reference_in_context; library.literature_population_catalog, literature_required_grading |
| source_operations.py | 110 | as parent with `page = assignment.get('page')` | BindingContext.*; services.{tool_catalog,execute_tool,read_record}; composition_information.CONTRACT_ARGUMENT_TRANSPORT; literature_contract_error; library.literature_assay_inputs |
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

The per-file counts are in `runs/carry_over/calls/a108_02.tsv` (episode `passage_evidence_extraction`).

## Differences from the parent and siblings

- Only `from_parent.py` (the selection shape), `source_contracts.py` (role instruction, no children), `episode.py` (no child wiring) carry content that differs from the parent. Credit, yield, reporting, grading and the decision machinery are the same in all four.
- The three children differ from one another only in role, instruction and selection: targeted takes `selection.spans[]` of `_WINDOW` (minItems 1), ordered takes one `_WINDOW`, and table takes `anyOf[_TABLE, _WINDOW]`, with the table child alone enforcing the `sheet_key` match.

## Carried over

Carried over on 19 November 2026 (private binding, ten-file form), from the old files at 97308b94c. One row per old function, class and method (`runs/carry_over/functions/a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.tsv`). Rows "library candidate" are private copies the library does not hold yet. Items that could not be placed or are blocked are in `carry_over_blocked/a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.md`.

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() |
| configuration.py | LiteratureConfiguration | machinery | construction-time settings of the old binding; the episode settings are ctx.settings (cost, parameters, tool_registry, knowledge_library_directory); outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py |
| configuration.py | LiteratureConfiguration.__init__ | machinery | construction-time settings of the old binding; the episode settings are ctx.settings (cost, parameters, tool_registry, knowledge_library_directory); outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py |
| configuration.py | LiteratureConfiguration.reference_evidence | episode function | not carried: root-only reference_evidence_parent context (not this episode's); see unplaced |
| credit.py | _resolve | episode function | task.py resolve_aliases (private copy; library candidate; the library _resolve of literature_task_credit is the A104 file) |
| credit.py | lead_schema | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | lead_return_schema | episode function | declared by messages/final_to_parent.py RETURN_FORM field literature_source_lead_dispositions (the old x-source schema becomes a typed list field) |
| credit.py | validate_lead | episode function | task.py validate_source_lead (private re-expression on custody; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py lead_dispositions (private re-expression over summary and records; library candidate) |
| credit.py | screening_schema | episode function | declared by messages/final_to_parent.py RETURN_FORM field literature_screening_answers |
| credit.py | _current_assessments | episode function | credit.py current_assessments (library candidate) |
| credit.py | screening_answers | episode function | credit.py screening_answers / examined_spans (library candidate) |
| credit.py | LiteratureTaskCredit | episode function | credit.py (module) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (README 3d: the projector's as_record is episode content) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py credit (credit_unit times the answers; the commission-agreement checks are old-runner receipt checks and are not carried) |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py answers / assessment_answers (library candidate) |
| credit.py | LiteratureCredit | episode function | credit.py (module) |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | services.scientific_credit / projection_view invocation of the old runner |
| credit.py | LiteratureCredit.credit_kind | machinery | credit kind declaration of the old runner |
| credit.py | LiteratureCredit.credit_view | machinery | services.scientific_credit view; credit(summary, records) is called by the system |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py credit |
| decision_inputs.py | build_decision_inputs | episode function | task.py decide (context the model is shown) over messages/internal_summary.py; resource, child-option, pending-work, contract-information and native-event pieces have no home here (no job, launch or child tool); see unplaced |
| decision_presentation.py | prepare_completed_work | episode function | the completed-work display (episode_work_report.completed_action_reports) has no library module; not carried, see unplaced |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py action_yields (yield_table over view.controller_state), shown by task.py decide |
| episode.py | LiteratureEpisode | episode function | episode.py class PassageEvidenceExtraction(EpisodeBinding) |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | report-contract information profile (report_form machinery) |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | report-contract information profile (report_form machinery) |
| episode.py | LiteratureEpisode._role | machinery | role check of the old shared binding (role literature_targeted is now the binding_path) |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (a leaf) |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (a leaf) |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | context hook of the old runner |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (page, selection.spans, literature_task, proposed_annotation_ref, requested_a108_grading_components, requested_a108_aggregation_components, scope, received_record_refs) |
| from_parent.py | LiteratureAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (page, selection.spans, literature_task, proposed_annotation_ref, requested_a108_grading_components, requested_a108_aggregation_components, scope, received_record_refs) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (page, selection.spans, literature_task, proposed_annotation_ref, requested_a108_grading_components, requested_a108_aggregation_components, scope, received_record_refs) |
| from_parent.py | LiteratureAssignment._validate_page | episode function | not carried: checks the page against the Store and the parent's own page assignment (a wrong commission fails); see unplaced |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (window checks that need no Store); the Store checks (page source and artifact in scope, offset within the artifact size) are not carried, see unplaced |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | the parent's msg_to_child builds the assignment; the child side is ASSIGNMENT_FORM and read_from_parent; the old yield-binding fill, operation-key check and parent-annotation equality are not carried (settings; wrong commission fails), see unplaced |
| from_parent.py | LiteratureAssignment._parent_page_schema | episode function | not carried: validates the parent page assignment (old-runner parent.assignment); see unplaced |
| from_parent.py | LiteratureAssignment._validate_parent_page | episode function | not carried: validates the parent page assignment (old-runner parent.assignment); see unplaced |
| goal.py | _yield_kind | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | _task_key | episode function | messages/read_from_parent.py task_key |
| goal.py | task_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM literature_task field and read_from_parent task checks |
| goal.py | _return_sources | machinery | report_form machinery: x-source walk over the parent-written report contract (the child declares RETURN_FORM) |
| goal.py | _return_components | machinery | report_form machinery: x-source walk over the parent-written report contract (the child declares RETURN_FORM) |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py read_from_parent (task kind, credit_unit, source and span checks); the report_contract and request checks are old-runner |
| goal.py | continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"]) |
| goal.py | LiteratureGoal | episode function | goal.py GOAL, task.py instructions / decide |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (role instruction + A108_CONTEXT_TASK + A108_READING_TASK) and task.py instructions |
| goal.py | LiteratureGoal.planning_context | episode function | task.py decide key literature_goal_plan |
| grading/contextual_interpretation.py | ContextualInterpretation | episode function | task.py reason_schema / reason |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_action_schema | episode function | task.py reason_schema (required-grading action_schema from the library, plus source_lead) |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_has_task_content | episode function | task.py action (a leads task's source_lead is task content; empty_commit) |
| grading/contextual_interpretation.py | ContextualInterpretation.execute_reasoning | episode function | task.py reason (async-free tool; calls the library required_grading.execute; source_lead flow in one transaction) |
| grading/contextual_subscoring.py | ContextualSubscoring | episode function | task.py repositories (the grading repository over ctx.store; library LiteratureA108GradingRepository, library not carried) |
| grading/contextual_subscoring.py | ContextualSubscoring._required_grading_repository | episode function | task.py repositories (the grading repository over ctx.store; library LiteratureA108GradingRepository, library not carried) |
| grading/contextual_subscoring.py | ContextualSubscoring._a108_grading_repository | episode function | task.py repositories (the grading repository over ctx.store; library LiteratureA108GradingRepository, library not carried) |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | not carried: root-only reference_evidence_parent context (role annotation, one-level path), not this episode's; see unplaced |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, source custody, own outcomes, history meaning, experimental work, received fact display, population sources and attempt) shown by task.py decide; own_source_inputs and source_metadata have no library module, see unplaced |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py owned_population_sources (from the unit outcomes instead of the operation-ledger SQL) |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py owned_population_sources / selected_population_attempt (from the unit outcomes instead of runtime_actions SQL) |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py received_fact_display (held records of the display kinds; source_metadata not in the library, see unplaced) |
| received_evidence.py | LiteratureReceivedEvidence | episode function | messages/final_to_parent.py validate_report |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | receipts bookkeeping of what a parent received; a parent's read_from_child / the child's RETURN_FORM declare the fact sources |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | receipts bookkeeping of what a parent received (received_cells ledger) |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | receipts bookkeeping / report_form machinery on the parent side |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | receipts bookkeeping (receive_cells ledger, received_form_references) |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | receipts bookkeeping (received-cell tokens) |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (answers equal the saved work; requested-subset equality of the cells is blocked with the cells, see blocked file) |
| scientific_records.py | LiteratureScientificRecords | episode function | task.py repositories / populate |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function | task.py repositories / populate (grading and aggregation repositories) and messages/internal_summary.py SOURCE_OF_TOOL |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | machinery | automatic score judgment hook of the old runner (returned []); no automatic judgment exists |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | machinery | automatic score judgment hook of the old runner (raised a108_automatic_judgment_unavailable) |
| scoring/contextual_main_sheet.py | ContextualMainSheet | episode function | task.py repositories (the aggregation repository over ctx.store with the grading cells reader; library LiteratureA108AggregationRepository, library not carried) |
| scoring/contextual_main_sheet.py | ContextualMainSheet._a108_aggregation_repository | episode function | task.py repositories (the aggregation repository over ctx.store with the grading cells reader; library LiteratureA108AggregationRepository, library not carried) |
| source_contracts.py | _a108_population_catalog | episode function | already in library: literature/forms/sample_context_evidence/literature_population_catalog.py population_catalog (called by task.py catalog) |
| source_contracts.py | _required_grading_logic | episode function | already in library: literature/grading/sample_context_evidence/literature_required_grading.py (imported by task.py as required_grading) |
| source_operations.py | LiteratureOperations | episode function | task.py tools |
| source_operations.py | LiteratureOperations.permitted_common_actions | machinery | common-action permission list of the old runner (tool, reason, child, redeliver_report); the actions are the TOOLS of task.py |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py catalog / offered (the A108 access tools and the two population tools; execution.estimate narrowed to the workbook tools) |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool and populate (tools); the state.query post-authorization is in run_access_tool |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted / named_sources / authorize_source (schema, page-source restriction and the repositories' access rules) |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function | task.py populate (read_source and materialize_text_witness_inputs) |
| source_references.py | LiteratureReferences | episode function | task.py within_source |
| source_references.py | LiteratureReferences._require | episode function | library already has it: records/received_records.py read_record_in_scope (called by task.py) |
| source_references.py | LiteratureReferences._artifact | episode function | not carried: the representation-to-artifact choice is inlined where the artifact is read (task.py populate / validate_source_lead, credit.py examined_spans) |
| source_references.py | LiteratureReferences._within_source | episode function | task.py within_source (private copy; library candidate) |
| source_references.py | LiteratureReferences.resolve | machinery | receiving-context reference resolver of the old report path (reference_in_context) |
| task.py | LiteratureTask | episode function | task.py |
| task.py | LiteratureTask.next | machinery | the old decision loop (replay, inprocess_replay, completions, model-call journal, SourceEnd); decide and action of task.py |
| task.py | LiteratureTask.apply_response | episode function | task.py action (schema validation, empty-reasoning rejection); the report_update validation and redelivery are old-runner machinery |
| task.py | LiteratureTask.execute | episode function | task.py tools (a tool returns its outcome, a failed one too); the runtime_actions journaling, receipts and credit save are old-runner machinery |
| task.py | LiteratureTask.finish | machinery | report_form machinery (form_with_facts, runtime_forms, workflow.release); messages/final_to_parent.py final_to_parent |
| task_decision.py | LiteratureTaskDecision | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.call | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange loop (request_context exchange) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | the decision-exchange loop and saved-request checks (exchange_decision, exchange_response, validate_contract_exchange_*, conversation_key, decision_completion); decide and action of task.py |
| task_instructions.py | instructions | episode function | task.py instructions (the pending-delivery, wait and exchange paragraphs are not carried) |
| task_state.py | LiteratureTaskState | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.__init__ | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.suspension_changed | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.record_execution_failure | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.restore | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.record_effect | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| task_state.py | LiteratureTaskState.checkpoint | machinery | task state, suspension, failure record, restore/checkpoint/record_effect of the old runner |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (the six fact sources under their old names, selectable) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent (screening and leads from the summary; cells, current sheets and completed work blocked, see blocked file) |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py final_to_parent (literature_current_scoring_sheets and literature_completed_work raise where the library is not carried) |
| to_parent.py | LiteratureReport._a108_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (literature_a108_grading_cells, literature_a108_aggregation_cells) |
| to_parent.py | LiteratureReport._a108_facts | episode function | messages/final_to_parent.py final_to_parent (cells; raises where the library is not carried, BLOCKED-ON-STORE-ACCESS) |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (assignment agreement, held references, finding form, then the unbuilt validate_form raises) |
| waiting.py | LiteratureWaiting | machinery | wait/suspension machinery (supports_wait); the episode has no wait |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait/suspension machinery (supports_wait); the episode has no wait |
| yield_estimator.py | validate_yield_bindings | machinery | construction-time yield declaration check of the old binding; settings are the run's continuation entry |
| yield_estimator.py | _RemainingCommissionedCredit | machinery | episode-local estimator replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | machinery | episode-local estimator replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | episode-local estimator replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | machinery | episode-local controller class replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | machinery | episode-local controller class replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | episode-local controller class replaced by CompletionYieldController (README 7b) |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"]) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
