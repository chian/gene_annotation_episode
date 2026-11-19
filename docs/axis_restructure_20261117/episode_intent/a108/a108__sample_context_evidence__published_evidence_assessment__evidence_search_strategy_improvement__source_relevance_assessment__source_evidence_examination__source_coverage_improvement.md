# A108 source_evidence_examination / source_coverage_improvement (role `literature_ordered`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/<file>` at 97308b94c. Only this folder's own files and its `grading/` and `scoring/` were read. Every file was also diffed against the parent `source_evidence_examination` folder. Where this file says "as parent", the text is identical apart from the package path and role string. The full detail is in the parent's intent file, `a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination.md`.

Binding class `LiteratureEpisode`. `binding_path = '.../source_evidence_examination/source_coverage_improvement'`, `commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_ordered',)`, `entry_roles = ()`, `decision_source_type = LiteratureTask`, `decision_prompt_renderer = render_literature_experimental_prompt`.

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_ordered']`): "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes."
- Instructions are this role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK` (old shared `a108.library.literature_a108_prompt`).
- Reads the assigned source in document order from a given window and decides whether to continue, reread or change the window. The parent commissions it as `literature_ordered` (the "ordered-reading investigation").

## Task and instructions

`task.py` is the same as the parent's apart from its docstring. `task_state.py`, `task_decision.py`, `task_instructions.py`, `decision_inputs.py` and `decision_presentation.py` are byte-identical to the parent's. That covers the old iterative decision source, the empty-reasoning rejection, grading-coupled reasoning, failed actions entering the iterator with credit, `SourceEnd('source_failed')` on a model-call failure, and the redelivery/exchange instruction text.

## What it reads from its parent's assignment (`from_parent.py`, 111 lines)

- Schema: `obj({version: const 'reading_assignment_v1', page: _PAGE, selection: _WINDOW})`. On top of that come the same `literature_task` (goal.task_schema), `proposed_annotation_ref` and A108 grading/aggregation requested-component properties as the parent. These are required under `private_yield_binding`, with `credit_unit` and `yield_settings` filled from the owner's `yield_bindings`.
- Selection: one `_WINDOW{source_ref, representation, offset>=0, limit>=1}`, the starting window for document-order reading.
- Window checks: each window's `source_ref` must equal `page.source_ref` (`literature_reading_source_mismatch`). If the window has a representation, it must equal the page's (`literature_reading_representation_mismatch`), and `offset` must be at most the artifact size (`source_offset_out_of_bounds`).
- `page` is validated as the parent's is: source in scope, artifact matching the representation, context and prior-delivery refs in scope.
- When the commissioning parent's role is `literature_page`, the binding validates the parent's own page assignment (`_parent_page_schema` / `_validate_parent_page`). It then requires this child's `page.source_ref` to lie within the parent's assigned source (`literature_reading_outside_assigned_source`). This check exists only in the children.
- The proposed annotation must equal the parent's.
- `goal.commissioned_task` takes `assigned_page = assignment.get('page', None)` (the parent uses the assignment itself). Task source refs and screening spans must be on this page's source and artifact.

## Children it may commission

None. `_CHILDREN = {'literature_ordered': ()}`, and `episode.py` has no `child_request_preparer` or `child_report_receiver` and no to_child/from_child files. `permitted_common_actions` still lists `'child'` as the parent's does, but `child_roles` returns an empty tuple.

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

`to_parent.py` and `received_evidence.py` are as parent. It reports `literature_a108_grading_cells`, `literature_a108_aggregation_cells` (requested components only), `literature_screening_answers` (screening tasks), `literature_source_lead_dispositions` (lead tasks), `literature_completed_work` and `literature_current_scoring_sheets`. The report must equal the saved work and the requested sheet subset. The parent's `from_child_source_coverage_improvement.py` receives it, and the A108 cells reach the parent through `received_form_references`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| __init__.py | 1 | none | none |
| binding_record.py | 16 | as parent (binding_id = this path) | none |
| configuration.py | 31 | as parent | composition_information CONTRACT_INFORMATION_PROFILE |
| credit.py | 221 | as parent | as parent: BindingContext.*, communication, domain, numerical yield names, library.literature_assay_inputs, finding_validity, scientific_findings, runtime_actions/runtime_report_attempts SQL, services.{scientific_credit_for,scientific_credit,proposed_annotation_for,annotation_task_required,workflow}, workflow.{scientific_projector_for_context,projector_receipt_arguments,projection_view} |
| decision_inputs.py | 36 | identical | as parent (self.workflow.* context builders, runtime FACT_*, runtime_actions) |
| decision_presentation.py | 21 | identical | runtime _category_yield_parameters/yield_table; episode_work_report; self.workflow.controller_binding |
| episode.py | 62 | role guard `literature_ordered`, no children, no preparers/receivers | BindingContext.{role,path}; library.literature_experimental_prompt |
| from_parent.py | 111 | reading_assignment_v1 with selection _WINDOW; window checks; within parent's page source | BindingContext.{assignment,role,scope} and parent.{role,assignment,scope}; services.{read_record,proposed_annotation_for}; library grading/aggregation storage |
| goal.py | 104 | as parent, with `assignment.get('page', None)` | BindingContext.{assignment,request,role}; communication; domain; numerical (duplicated header); library.literature_a108_prompt |
| internal_summary.py | 106 | as parent, with `page = assignment.get('page')` | BindingContext.*; services.{own_outcomes,workflow}; workflow.{store,run_id}; runtime_actions SQL; library.literature_source_inputs/_task_families/_work_report |
| received_evidence.py | 90 | as parent | BindingContext.*; services.{record_selection,workflow}; library.literature_sheet_updates; method_loop.durable; domain.canonical |
| scientific_records.py | 16 | as parent | library grading/aggregation storage |
| source_contracts.py | 37 | `_CHILDREN = {'literature_ordered': ()}`; own role instruction | communication; composition_information; domain; episode_bindings.reference_in_context; library.literature_population_catalog, literature_required_grading |
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

The per-file counts are in `runs/carry_over/calls/a108_02.tsv` (episode `source_coverage_improvement`).

## Differences from the parent and siblings

- Only `from_parent.py` (the selection shape), `source_contracts.py` (role instruction, no children), `episode.py` (no child wiring) carry content that differs from the parent. Credit, yield, reporting, grading and the decision machinery are the same in all four.
- The three children differ from one another only in role, instruction and selection: targeted takes `selection.spans[]` of `_WINDOW` (minItems 1), ordered takes one `_WINDOW`, and table takes `anyOf[_TABLE, _WINDOW]`, with the table child alone enforcing the `sheet_key` match.

## Carried over

One row per row of `runs/carry_over/functions/<episode>.tsv` (old file, kind, name copied); then the class (machinery or episode function) and the new place or the reason. New files: `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/read_from_parent.py`, `messages/internal_summary.py`, `messages/final_to_parent.py`, `tests/test_binding.py`. No `msg_to_child.py` or `read_from_child.py` (no children).

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | the binding's own as_record() (README 3e) |
| configuration.py | class | LiteratureConfiguration | machinery | configuration class of the old binding; its values: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE, yield bindings -> the episode's settings (yield_estimator.py), contract_information_profile and reference_parent_sources are not this episode's (README 3c) |
| configuration.py | method | LiteratureConfiguration.__init__ | machinery | values only: outcome_page_size -> internal_summary.py OUTCOME_PAGE_SIZE; private_yield_binding/yield_bindings -> settings read by yield_estimator.py; contract_information_profile (composition information) and reference_parent_sources (root annotation context) dropped |
| configuration.py | method | LiteratureConfiguration.reference_evidence | machinery | root-only reference-evidence parent configuration (role annotation), not this episode's |
| credit.py | function | _resolve | episode function | task.py resolve_aliases (private copy; library candidate) |
| credit.py | function | lead_schema | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | function | lead_return_schema | episode function | x-source report-form schema replaced by the RETURN_FORM field literature_source_lead_dispositions (messages/final_to_parent.py LEADS) |
| credit.py | function | validate_lead | episode function | task.py validate_source_lead (private copy re-expressed on custody; library candidate) |
| credit.py | function | lead_dispositions | episode function | credit.py lead_dispositions (over the summary's own leads; the admitted-child-form branch is machinery: no child) |
| credit.py | function | screening_schema | episode function | x-source report-form schema replaced by the RETURN_FORM field literature_screening_answers (messages/final_to_parent.py SCREENING) |
| credit.py | function | _current_assessments | episode function | credit.py current_assessments (calls library FindingValidity/target_eligible) |
| credit.py | function | screening_answers | episode function | credit.py screening_answers (over the summary's no_applicable_evidence spans) |
| credit.py | class | LiteratureTaskCredit | episode function | credit.py (module functions; the projector class is not carried) |
| credit.py | method | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding |
| credit.py | method | LiteratureTaskCredit.__call__ | episode function | credit.py credit (its commission-equality and annotation-scope checks are checks of a commission: not carried, rule 1) |
| credit.py | method | LiteratureTaskCredit._answers | episode function | credit.py answers / assessment_answers |
| credit.py | class | LiteratureCredit | machinery | credit view/projector wiring over services.scientific_credit (README 3d); the credit is credit.py credit |
| credit.py | method | LiteratureCredit._scientific_credit_invocation | machinery | services.workflow projector invocation (projection_view, projector_receipt_arguments), README 3d |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | LiteratureCredit.credit_view | machinery | services.scientific_credit view (README 3d) |
| credit.py | method | LiteratureCredit.credit_projector | machinery | projector wiring; the projector is re-expressed in credit.py |
| decision_inputs.py | function | build_decision_inputs | episode function | task.py decide (context for the model) and messages/internal_summary.py (state); journal, receipts and pending-work parts are machinery |
| decision_presentation.py | function | prepare_completed_work | episode function | not placed: library episode_work_report (completed_action_reports) has no module in episode_support; the completed work is shown as current_findings and current_scoring_cells in task.py decide |
| decision_presentation.py | function | decision_yield_table | episode function | messages/internal_summary.py action_yields via library records/progress_views.py yield_table; shown by task.py decide |
| episode.py | class | LiteratureEpisode | episode function | episode.py SourceCoverageImprovement(EpisodeBinding) |
| episode.py | method | LiteratureEpisode.contract_information_configuration | machinery | composition-information profile (contract information exchange), not carried |
| episode.py | method | LiteratureEpisode.contract_information_profile | machinery | composition-information profile (contract information exchange), not carried |
| episode.py | method | LiteratureEpisode._role | machinery | role guard: each role is its own episode |
| episode.py | method | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | LiteratureEpisode.context_hook_applies | machinery | context hooks of the old runner |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | LiteratureAssignment.child_assignment_schema | machinery | parent-side schema of a child's assignment (README 3b C3); no children |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and task_schema |
| from_parent.py | method | LiteratureAssignment._validate_page | machinery | checks of a commission against the Store (page source and artifact in scope): a wrong commission fails (rule 1); the page is passed in custody |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (window against page); the offset against the artifact size is a commission check, not carried |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | machinery | parent-side preparation of the assignment: yield-binding filling, annotation equality with the parent and page-within-parent-source checks are commission checks (rule 1; README 3b C3) |
| from_parent.py | method | LiteratureAssignment._parent_page_schema | machinery | reads the commissioning parent's raw assignment (gone, README 3b P1) |
| from_parent.py | method | LiteratureAssignment._validate_parent_page | machinery | reads the commissioning parent's raw assignment (gone, README 3b P1) |
| goal.py | function | _yield_kind | episode function | yield_estimator.py (accumulation for verified_source_leads, completion otherwise) |
| goal.py | function | _task_key | episode function | messages/read_from_parent.py task_key |
| goal.py | function | task_schema | episode function | messages/read_from_parent.py task_schema |
| goal.py | function | _return_sources | machinery | check of the parent's report contract against the task (a commission check; the child declares its fields in RETURN_FORM and the parent selects) |
| goal.py | function | _return_components | machinery | check of the parent's report contract against the task (a commission check) |
| goal.py | function | commissioned_task | episode function | messages/read_from_parent.py read_from_parent (task checks that need no request); the request/report-contract checks are commission checks, not carried |
| goal.py | function | continuation_task | episode function | messages/read_from_parent.py task_key (read by yield_estimator.py through parent_input['task']) |
| goal.py | class | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | method | LiteratureGoal.instructions | episode function | goal.py GOAL (role instruction + A108_CONTEXT_TASK + A108_READING_TASK) |
| goal.py | method | LiteratureGoal.planning_context | episode function | messages/internal_summary.py literature_goal_plan |
| grading/contextual_interpretation.py | class | ContextualInterpretation | episode function | task.py reason / reason_schema |
| grading/contextual_interpretation.py | method | ContextualInterpretation.reasoning_action_schema | episode function | task.py reason_schema (library literature_required_grading.action_schema plus source_lead) |
| grading/contextual_interpretation.py | method | ContextualInterpretation.reasoning_has_task_content | episode function | task.py has_task_content (used by action) |
| grading/contextual_interpretation.py | method | ContextualInterpretation.execute_reasoning | episode function | task.py reason tool (library literature_required_grading.execute couples the grading and the saved sheet; validate_source_lead for leads) |
| grading/contextual_subscoring.py | class | ContextualSubscoring | episode function | task.py grading_repository / reason |
| grading/contextual_subscoring.py | method | ContextualSubscoring._required_grading_repository | episode function | task.py grading_repository |
| grading/contextual_subscoring.py | method | ContextualSubscoring._a108_grading_repository | episode function | task.py grading_repository (library LiteratureA108GradingRepository) |
| internal_summary.py | class | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | LiteratureSummary.initial_decision_context | machinery | root-only context (role annotation at path length 1, reference_parent_sources): not this episode's |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, custody, own outcomes, history meaning, experimental work); library literature_source_inputs.own_source_inputs and literature_work_report have no module: literature_examined_source_inputs and the completed-work display are not shown |
| internal_summary.py | method | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py literature_owned_population_sources (from the unit outcomes; the old SQL over the population operation tables is machinery) |
| internal_summary.py | method | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py literature_owned_population_sources and literature_selected_population_attempt (latest outcome) |
| internal_summary.py | method | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py literature_received_fact_display (held records by kind); source_metadata (library literature_work_report) has no module and is not shown |
| received_evidence.py | class | LiteratureReceivedEvidence | machinery | receiving a child's report (README 3b R1, R3); this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_sources | machinery | receiving a child's report; no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_facts | machinery | receiving a child's report; no child |
| received_evidence.py | method | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | receiving a child's report; no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_form_references | machinery | receipts bookkeeping (README 3e F1, F5) |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | machinery | receipts bookkeeping (README 3e F5) |
| received_evidence.py | method | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (requested-component check; the answers are computed from the same summary as the facts) |
| scientific_records.py | class | LiteratureScientificRecords | machinery | old runner hook class |
| scientific_records.py | method | LiteratureScientificRecords._population_routes | episode function | messages/internal_summary.py POPULATION_ROUTES |
| scientific_records.py | method | LiteratureScientificRecords.automatic_score_judgments | machinery | old runner automatic-judgment hook (returned []) |
| scientific_records.py | method | LiteratureScientificRecords.complete_score_judgment | machinery | old runner automatic-judgment hook (raised a108_automatic_judgment_unavailable) |
| scoring/contextual_main_sheet.py | class | ContextualMainSheet | episode function | task.py aggregation_repository |
| scoring/contextual_main_sheet.py | method | ContextualMainSheet._a108_aggregation_repository | episode function | task.py aggregation_repository (library LiteratureA108AggregationRepository) |
| source_contracts.py | function | _a108_population_catalog | episode function | task.py catalog (library literature_population_catalog.population_catalog) |
| source_contracts.py | function | _required_grading_logic | episode function | task.py reason_schema / reason (library literature_required_grading module; the provider check is inside the library execute) |
| source_operations.py | class | LiteratureOperations | episode function | task.py TOOLS |
| source_operations.py | method | LiteratureOperations.permitted_common_actions | machinery | set of common actions (tool, reason, child, redeliver_report): the tools and reason are TOOLS, child and redeliver_report do not exist |
| source_operations.py | method | LiteratureOperations.catalog | episode function | task.py offered / catalog (the access subset and the two population tools; the old services.tool_catalog is the registry in the library) |
| source_operations.py | method | LiteratureOperations.execute | episode function | task.py run_access_tool, populate, reason |
| source_operations.py | method | LiteratureOperations._tool_arguments | episode function | task.py admitted |
| source_operations.py | method | LiteratureOperations._materialize_text_arguments | episode function | task.py populate (read_source and library materialize_text_witness_inputs) |
| source_references.py | class | LiteratureReferences | episode function | task.py within_source and library read_record_in_scope |
| source_references.py | method | LiteratureReferences._require | episode function | already in library: records/received_records.py read_record_in_scope |
| source_references.py | method | LiteratureReferences._artifact | machinery | used only by the page check _validate_page (a commission check) |
| source_references.py | method | LiteratureReferences._within_source | episode function | task.py within_source |
| source_references.py | method | LiteratureReferences.resolve | machinery | report reference resolver (reference_in_context), README 3b D2 |
| task.py | class | LiteratureTask | episode function | task.py decide and action |
| task.py | method | LiteratureTask.next | episode function | task.py decide (the replay, checkpoint, delivery and source_failed branches are machinery) |
| task.py | method | LiteratureTask.apply_response | episode function | task.py action (the report_update admission, redelivery and record_effect are machinery) |
| task.py | method | LiteratureTask.execute | episode function | task.py tools (the runtime_actions journaling, receive_outcome, automatic_score_updates and controller_value are machinery) |
| task.py | method | LiteratureTask.finish | episode function | messages/final_to_parent.py final_to_parent (runtime_forms saving and release are machinery) |
| task_decision.py | class | LiteratureTaskDecision | machinery | old decision machine; its instructions text is carried in task.py instructions |
| task_decision.py | method | LiteratureTaskDecision.call | episode function | task.py decide (ModelRequest); the runtime_model_calls and receipts are machinery |
| task_decision.py | method | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | method | LiteratureTaskDecision.decision_completion | machinery | provider patching |
| task_decision.py | method | LiteratureTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.interpretation_context | machinery | decision exchange lookup (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | method | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_request | machinery | saved-request checks (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_history | machinery | saved-request checks (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_instructions.py | function | instructions | episode function | task.py instructions (the decision-exchange, pending-delivery and redeliver paragraphs are not carried) |
| task_state.py | class | LiteratureTaskState | machinery | task state, checkpoint and restore (README 3e) |
| task_state.py | method | LiteratureTaskState.__init__ | machinery | task state, checkpoint and restore |
| task_state.py | method | LiteratureTaskState.bind_execution_context | machinery | old runner execution context |
| task_state.py | method | LiteratureTaskState.suspension_changed | machinery | wait/suspension machinery |
| task_state.py | method | LiteratureTaskState.record_execution_failure | machinery | failed action recording: the tool returns the failure as its outcome (task.py run_access_tool, failure_outcome) |
| task_state.py | method | LiteratureTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | LiteratureTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | LiteratureTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | method | LiteratureTaskState.checkpoint | machinery | checkpoint/restore |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | method | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | method | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py (literature_completed_work: library literature_work_report has no module; literature_current_scoring_sheets: library current_scoring_sheets in the old Store form); selecting either raises |
| to_parent.py | method | LiteratureReport._a108_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (literature_a108_grading_cells, literature_a108_aggregation_cells) |
| to_parent.py | method | LiteratureReport._a108_facts | episode function | messages/internal_summary.py grading_cells and aggregation_cells (read from the unit outcomes that saved the sheets); returned by final_to_parent |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | class | LiteratureWaiting | machinery | wait machinery: this episode has no wait |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait machinery: this episode has no wait |
| yield_estimator.py | function | validate_yield_bindings | machinery | owner configuration validation (settings are the system's now) |
| yield_estimator.py | class | _RemainingCommissionedCredit | machinery | episode-local estimator -> CompletionYieldController (README 7b) |
| yield_estimator.py | method | _RemainingCommissionedCredit.__call__ | machinery | episode-local estimator -> CompletionYieldController (README 7b) |
| yield_estimator.py | method | _RemainingCommissionedCredit.as_record | machinery | episode-local estimator -> CompletionYieldController (README 7b) |
| yield_estimator.py | function | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | class | _FiniteLiteratureYieldController | machinery | episode-local controller class -> CompletionYieldController (README 7b) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.__init__ | machinery | episode-local controller class -> CompletionYieldController (README 7b) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.transitioned | machinery | transitioned(epoch) is deleted (README 3d) |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | method | LiteratureYield.continuation_task | episode function | yield_estimator.py (task kind read from parent_input['task']) |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
