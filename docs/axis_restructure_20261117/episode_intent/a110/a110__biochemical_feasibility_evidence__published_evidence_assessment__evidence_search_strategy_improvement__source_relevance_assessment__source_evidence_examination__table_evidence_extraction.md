# A110 table_evidence_extraction (old role `literature_table`)

Path: `root/a110/biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction`.
Source: the episode's own files at `97308b94c` (28 files, no `grading/` or `scoring/` subfolder).
Commissioning parent (`episode.py`): `.../source_evidence_examination` (old role `literature_page`).

## Purpose (its own words)

`goal.py` returns `_ROLE_INSTRUCTIONS['literature_table']` plus a shared reaction/resource paragraph:

> Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.
> Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness remain unresolved. A search or read earns no scientific credit by itself.

It is the table investigation of one source that the page episode already chose. It reads an XLSX sheet (rows, header row, row filter) or an article XML table through original-source byte windows, and it can populate reaction/resource evidence sheets from the cells it reads.

## Task and instructions

- `task.py` puts together `SourceInvestigationTask` from task_state, task_decision, task_suspension, task_action, task_report_delivery and internal_summary's `SourceDecisionSummary`. Its `next()` is the old runner's replay, completion-slot and model-call loop. It is machinery only and has no episode intent.
- `task_instructions.py`: the generic `INSTRUCTIONS` (old `library.scientific_instruction_text`), then the specialist's (this episode's) `instructions()`, then tool-knowledge and launch-instruction text when present. It also adds this episode-level text: *"When pending_child_delivery is supplied ... select redeliver_report with a corrected form. Use only the saved child facts and interpretations ... preserve current_report_update ... this repair does not select new scientific work."* Under the decision-exchange protocol it swaps the old history guidance for: *"Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices..."*
- `task_presentation.py` (`present_source_context`, protocol `episode_context_presentation_v1`) renders the decision as the literature experimental prompt (`render_literature_experimental_prompt` + `text_instructions`) whenever the context carries a `literature_experimental_work` task. Bootstrap, update and lookup-result frames are folded into a per-(episode, role) prompt state. Any other context is shown as JSON.

## What it reads from the parent's assignment (`from_parent.py`)

Schema `reading_assignment_v1`:
- `page`: `page_assignment_v1` = {`source_ref`, `representation` (text|original|stdout|stderr), `artifact_ref`, `question_context_refs[]`, `prior_delivery_refs[]`}.
- `selection`: `anyOf [table, window]`.
  - **table** = {`source_ref`, `sheet_key`, `offset` (>=0), `limit` (>=0), `header_row` (int>=1 or null), `where` (null, or {`column` (A-Z letters or null), `match` equals|contains, `value`, `case_sensitive`})}.
  - **window** = {`source_ref`, `representation`, `offset` (>=0), `limit` (>=1)}.
- plus `assignment_schema_fields()` from the old shared `library.literature_component_binding`: the requested population components and native-observation positions, which `numerical_report_facts` and `received_reports` read through `requested_field` and `POSITIONS_FIELD`.

Validation:
- The selection's `source_ref` must equal the page's (`literature_reading_source_mismatch`).
- For window selections only (a table selection has no `representation`, so these checks are skipped for it): the representation must match the page's (`literature_reading_representation_mismatch`), and `offset` must be no larger than the artifact size (`source_offset_out_of_bounds`).
- The table selection's `sheet_key` is enforced at tool time instead (see Tools).
- The page custody check (`source_custody._validate_page`) requires: the source is in scope; the artifact for that representation equals `artifact_ref` (`literature_source_artifact_mismatch`); the artifact and every question-context or prior-delivery reference are in scope.
- `prepare_assignment`: when the parent is `literature_page`, the page's source must fall inside the parent's assigned source, following the `parent_source_refs` chain (`literature_reading_outside_assigned_source`). An `operation_key` is required.

## Children

None. `child_roles()` returns `()` and `allowed_children()` defers to it. `permitted_common_actions` still lists `('tool', 'child', 'redeliver_report')`, but no child role exists, so in practice only tools and report redelivery are open.

## Decision state shown to the model (`internal_summary.LiteratureSummary.decision_context`)

- `literature_assignment`: the validated assignment.
- `literature_source_custody`: for the page source, {version, artifact_ref, text_ref, stdout_ref, stderr_ref, parent_source_refs}.
- `own_literature_outcomes`: one page (`offset=0, limit=outcome_page_size`, default 8) of its own outcomes for the acquisition and read tools.
- `literature_history_meaning`: "Own outcome metadata only. Inspect original source records and exact prior operations before interpreting them."
- `literature_experimental_work`: {version `literature_experimental_task_v1`, aspect `source_experimental_evidence`}. This is what triggers the experimental prompt renderer.
- `literature_owned_population_sources`: which population sources it already owns. These come from SQL over the population tables (completed outcomes whose sheet_ref was received and authenticated by operation identity, provider and version). Metadata only, no cells.
- `literature_selected_population_attempt`: present when its latest action was an invalid, failed or error tool call. Shows tool, version and population_version, and status.
- `component_axis_source_origin` and `component_axis_source_access`, when the old helpers return them.
- The old generic snapshot is added on top (`SourceDecisionSummary._decision_snapshot`): goal, scope, working_state, visible refs, current_credit, evidence vector, credit binding, time_accounting, pending work, last outcome, feedback, visual evidence (latest completed image.view), deliveries, controller, tools, tool knowledge, report facts, requested form, current report update and basis, and the lifecycle text "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment."

`parent_context.initial_decision_context` applies only to role `annotation` at path length 1, so it gives `{}` here. `contract_information_profile` returns the configured profile, because the role is in `ROLES`.

## Tools offered (`source_operations.py`)

- From the scoped tool catalog, only `_ACCESS_TOOLS`: `state.query, source.read, source.locate, source.sequence.scan, source.sequence.references, source.experimental.records, image.view, source.archive.members, source.archive.extract, source.xlsx.sheets, source.xlsx.rows, source.pdf.info, source.pdf.text, source.pdf.page, execution.estimate`.
- `execution.estimate` is narrowed to its `source.xlsx.sheets` and `source.xlsx.rows` branches, and dropped if neither exists.
- The population operations from `population_catalog_entries()` (`literature.reaction.populate`, `literature.reaction.source.populate`) are added. They get `argument_transport = CONTRACT_ARGUMENT_TRANSPORT` when a contract profile is configured.
- Every input schema is wrapped with `source_location_inputs`.

Argument rules:
- Every `source_ref` must lie within the assigned page source; `archive.extract` is checked through its member's source.
- For populate, every nested `source_ref`, `sheet_ref`, `data_source_ref`, `reaction_source_ref` or `metadata_source_ref` is checked the same way.
- A violation gives `literature_reading_outside_assigned_source` with `rejection_detail`.
- **Specific to this episode:** when the assignment's selection carries a `sheet_key`, a `source.xlsx.rows` call must use that same `sheet_key`, otherwise `literature_table_sheet_mismatch` (an invalid outcome).

Execution:
- Populate first materializes text-witness inputs by reading the source (through the `source.read` admission check), then runs `populate` or `populate_source` against the reaction repository.
- `source.locate/sequence.scan/sequence.references/experimental.records` are given `permitted_record_refs = received_record_refs`.
- Invalid arguments produce an `invalid` outcome with feedback, which enters the iterator as an executed action.

Configuration has no reasoning actions: `reasoning_action_schema` and `execute_reasoning` return None.

## Credit

`credit_kind = 'scientific'`. `credit_view = services.scientific_credit(context, receiver_selection)`. No credit projector. No bounding or rescaling appears.

## Continuation

`yield_estimator.py`: `continuation_task()` and `yield_controller()` both return None, so the episode declares no estimator or settings of its own. The old runner used `_category_yield_parameters(controller_binding)` for the exchange's yield table. `waiting.supports_wait = False`. In the new layout one of the three `yield_control/` estimators must be chosen explicitly. The old files do not name one.

## Report to parent

- `fact_sources` are the shared population fact sources (reaction cells, semantic cells, native observations namespace).
- `facts(context, completion_snapshot)` is `_rate_facts` over the committed refs plus the current sheet refs. For each population route it selects received source rows of that provider at version `literature_reaction_record_v2`/`v3` and returns `fact_cells` for the requested components. It also returns the native-observation rows for the requested positions, from v3 records that hold `native_observations`.
- `validate_report` re-validates the assignment, runs `validate_form` with its resolver, then `validate_received_report`:
  - sheet refs must be received or known to the same run and episode (`literature_reaction_receiver_mismatch`);
  - an empty return needs either a companion family or `validate_empty_return_family`;
  - only requested components are allowed (`unrequested_literature_reaction_component`);
  - only requested positions are allowed (`unrequested_literature_reaction_native_observation`).
- `current_report_facts = {}`.
- Since it has no children, `received_report_sources` and `received_report_facts` give `{}` for its own role.
- Old `task_report_delivery.finish` saves the form built by `form_with_facts` from the facts and interpretations, or, when there is no contract, credit plus pending handles.

## Files

| file | lines | own intent | old-runner names |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| binding_record.py | 13 | record version `literature_episode_binding_v1`, binding_id = path, configuration {outcome_page_size, reference_parent_sources, contract_information_profile} | none |
| configuration.py | 35 | `outcome_page_size` (default 8, positive int); optional unique `reference_parent_sources`; profile must equal CONTRACT_INFORMATION_PROFILE; no reasoning actions | CONTRACT_INFORMATION_PROFILE (via contracts from composition_information) |
| contracts.py | 39 | role table `ROLES`, `_CHILDREN`, `_ROLE_INSTRUCTIONS` text, window/table/page schemas, `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS` | imports from a110.communication, composition_information, domain, episode_bindings (`reference_in_context`), experimental_database_acquisition, library.literature_component_binding |
| credit.py | 16 | scientific credit, no projector | services.scientific_credit |
| episode.py | 53 | role `literature_table`, parent path, no children, actions tool/child/redeliver_report, presentation renderer | imports its own received_execution_information twice (harmless duplication); assembles old mixins |
| from_parent.py | 63 | reading assignment (table or window), source checks; representation/offset checks only for window selections, parent-source containment | library.literature_component_binding.assignment_schema_fields, services.read_record |
| goal.py | 9 | goal text above | none |
| initial_information.py | 8 | initial resource readers for this path | library.execution_initial_information.presentation, catalog.readers |
| internal_summary.py | 133 | decision_context fields above; owned population sources; latest failed population attempt | old SourceDecisionSummary (self.workflow.* x~25), runtime.*, SQL on sqlite_master/runtime_actions/population tables, services.workflow.store.db, literature_source_origin, component_axis_source_access, library.literature_task_selection, services.own_outcomes |
| numerical_report_facts.py | 47 | report facts from reaction sheets and native observations | literature_sheet_updates, library.reaction_native_observations, reaction_population_contracts, literature_component_binding, services.workflow.store, services.read_record |
| parent_context.py | 21 | annotation-only reference-parent context (inactive for this role); profile | none beyond contracts |
| reaction_records.py | 15 | reaction repository access | literature_reaction_storage, services.workflow.store/run_id, library.literature_component_binding |
| received_execution_information.py | 4 | readers configured/received for this path | catalog.configured/received |
| received_reports.py | 109 | validation of returned reaction cells and native rows (receiver, empty families, requested components/positions) | library.reaction_native_observations, literature_sheet_updates, method_loop.durable, services.workflow.store, services.record_selection |
| source_custody.py | 39 | scope check, representation artifact, parent-source containment, page validation | services.reference_in_scope/read_record |
| source_operations.py | 106 | tool filter, assigned-sheet check for source.xlsx.rows, estimate narrowing, populate operations, source containment, text-witness materialization | library.reaction_population, reaction_source_selection, literature_assay_inputs, literature_contract_error, composition_information, component_axis_source_access (getattr services.workflow), services.tool_catalog/execute_tool |
| task.py | 84 | none (old iterator) | runtime, providers.ModelCallError, episode_source_failure, journal tables runtime_episodes/actions/model_calls, self.workflow.{journal, inprocess_replay, execution_binding, completions, completed_unit, selected, next_return, resolve_pending_deliveries, store, run_id} |
| task_action.py | 111 | feedback repair text for `closed_top_level_form_required` and `component_native_return_channels_required` | runtime.*, runtime_actions/model_calls, self.workflow.{journal, decision_exchanges, selected, resolver, validate_report, execute, pending_work, receive_native_outcome, receive_outcome, automatic_score_updates, last_observed_credit, source_credit_view, retain_shared_grading_results, completions, controller_value, execution_binding, store, run_id} |
| task_decision.py | 349 | none of its own beyond literature numerical-contract freezing and completed_action_reports in context | runtime.* (~35 names), providers internals, episode_work_report, runtime_model_calls, self.workflow.{receipts, decision_exchanges, launch_instructions, resource_estimator, episode_bindings, binding_context, specialist, provider, ...} |
| task_instructions.py | 19 | pending-child-delivery repair text; exchange-protocol history text | runtime_prompt.INSTRUCTIONS/DECISION_EXCHANGE_PROTOCOL, source.workflow.{specialist, binding_context, knowledge, launch_instructions, decision_protocol} |
| task_presentation.py | 46 | literature experimental prompt rendering | decision_context (VERSION, apply_state_frame), library.scientific_decision_presentation, library.literature_source_presentation |
| task_report_delivery.py | 23 | none (old finish) | runtime.Record/form_with_facts, runtime_forms, self.workflow.{source_credit_view, pending_handles, episode_bindings, binding_context, release, journal, facts} |
| task_state.py | 108 | none (old state/checkpoint) | runtime.*, runtime_actions, episode_source_failure, self.workflow.{inprocess_replay, completions, journal, archive, execution_binding, recover_commissions, progress_provider, controller_value, source_credit_view, store} |
| task_suspension.py | 9 | none | self.workflow.execution_handle/execution_backend |
| to_parent.py | 18 | fact sources, resolve, validate_report | episode_bindings.reference_in_context, communication.validate_form |
| waiting.py | 8 | supports_wait False | none |
| yield_estimator.py | 12 | no private continuation | none (old yield hook names continuation_task/yield_controller) |

The full per-name counts are in `runs/carry_over/calls/a110_07.tsv`.

## Differences from the sibling `source_coverage_improvement` (`literature_ordered`)

All 28 files are identical apart from role and path strings, with three real differences:
- **Selection.** This episode accepts `anyOf [_TABLE, _WINDOW]`; the ordered sibling accepts only `_WINDOW`.
- **Sheet check.** This episode alone refuses `source.xlsx.rows` calls on a sheet other than the assigned `sheet_key` (`literature_table_sheet_mismatch`). That makes 106 lines in source_operations.py against the sibling's 103.
- **Goal head.** This one does table/sheet investigation: rows, headers, conditions and footnotes, with native XLSX cell identity. The sibling does document-order byte reading.

Both share the reaction/resource goal paragraph, the tools, credit, report validation and the absent private yield. The third sibling, `literature_targeted`, is not read here.

## Carried over

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3, 3e) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3, 3e) |
| configuration.py | LiteratureConfiguration | machinery | old configuration mix-in; outcome_page_size is the constant OUTCOME_PAGE_SIZE in task.py; reference_parent_sources and the contract profile belong to the old reaction route |
| configuration.py | LiteratureConfiguration.__init__ | machinery | old configuration mix-in; outcome_page_size is the constant OUTCOME_PAGE_SIZE in task.py; reference_parent_sources and the contract profile belong to the old reaction route |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | old configuration mix-in; outcome_page_size is the constant OUTCOME_PAGE_SIZE in task.py; reference_parent_sources and the contract profile belong to the old reaction route |
| configuration.py | LiteratureConfiguration.contract_information_configuration | machinery | old configuration mix-in; outcome_page_size is the constant OUTCOME_PAGE_SIZE in task.py; reference_parent_sources and the contract profile belong to the old reaction route |
| configuration.py | LiteratureConfiguration.reasoning_action_schema | machinery | no reasoning actions in this episode |
| configuration.py | LiteratureConfiguration.reasoning_has_task_content | machinery | no reasoning actions in this episode |
| configuration.py | LiteratureConfiguration.execute_reasoning | machinery | no reasoning actions in this episode |
| contracts.py | _population_catalog | episode function | episode function (not carried, library missing): task.py literature_reaction_populate / literature_reaction_source_populate raise a110_reaction_population_not_built |
| credit.py | LiteratureCredit | episode function | credit.py credit (scientific credit of distinct retained findings x finding_unit; no projector, no bound) |
| credit.py | LiteratureCredit.credit_kind | episode function | credit.py credit (scientific credit of distinct retained findings x finding_unit; no projector, no bound) |
| credit.py | LiteratureCredit.credit_view | episode function | credit.py credit (scientific credit of distinct retained findings x finding_unit; no projector, no bound) |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py credit (scientific credit of distinct retained findings x finding_unit; no projector, no bound) |
| episode.py | LiteratureEpisode | machinery | old mix-in class; child_roles/allowed_children: no children, CHILD_SLOTS = {} in task.py; permitted_common_actions: redeliver_report is deleted (R2), tool actions are TOOLS in task.py |
| episode.py | LiteratureEpisode._role | machinery | old mix-in class; child_roles/allowed_children: no children, CHILD_SLOTS = {} in task.py; permitted_common_actions: redeliver_report is deleted (R2), tool actions are TOOLS in task.py |
| episode.py | LiteratureEpisode.allowed_children | machinery | old mix-in class; child_roles/allowed_children: no children, CHILD_SLOTS = {} in task.py; permitted_common_actions: redeliver_report is deleted (R2), tool actions are TOOLS in task.py |
| episode.py | LiteratureEpisode.child_roles | machinery | old mix-in class; child_roles/allowed_children: no children, CHILD_SLOTS = {} in task.py; permitted_common_actions: redeliver_report is deleted (R2), tool actions are TOOLS in task.py |
| episode.py | LiteratureEpisode.permitted_common_actions | machinery | old mix-in class; child_roles/allowed_children: no children, CHILD_SLOTS = {} in task.py; permitted_common_actions: redeliver_report is deleted (R2), tool actions are TOOLS in task.py |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment._parent_page_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment._validate_parent_page_assignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| goal.py | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL |
| initial_information.py | initial_information | machinery | old initial-resource reader catalog (catalog.readers); a lookup is a tool, none declared |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.facts | episode function | messages/final_to_parent.py final_to_parent (facts become the result) |
| internal_summary.py | LiteratureSummary.current_report_facts | machinery | current_report_facts = {} (report update machinery) |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | episode function (not carried, library missing): SQL over the reaction population tables; reaction_population is not in the library |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | episode function (not carried, library missing): reaction population context |
| internal_summary.py | SourceDecisionSummary | machinery | old generic decision snapshot over self.workflow (README 3a) |
| internal_summary.py | SourceDecisionSummary._decision_snapshot | machinery | old generic decision snapshot over self.workflow (README 3a) |
| numerical_report_facts.py | LiteratureNumericalReportFacts | episode function | episode function (not carried, library missing): reaction rate facts and native observations; literature_component_binding, literature_sheet_updates are not in the library |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_fact_sources | episode function | episode function (not carried, library missing): reaction rate facts and native observations; literature_component_binding, literature_sheet_updates are not in the library |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_facts | episode function | episode function (not carried, library missing): reaction rate facts and native observations; literature_component_binding, literature_sheet_updates are not in the library |
| parent_context.py | LiteratureParentContext | machinery | annotation-only reference-parent context, inactive for this role; contract information profile of the old reaction route |
| parent_context.py | LiteratureParentContext.initial_decision_context | machinery | annotation-only reference-parent context, inactive for this role; contract information profile of the old reaction route |
| parent_context.py | LiteratureParentContext.contract_information_profile | machinery | annotation-only reference-parent context, inactive for this role; contract information profile of the old reaction route |
| reaction_records.py | LiteratureReactionRecords | episode function | episode function (not carried, library missing): literature_reaction_storage / literature_component_binding are not in the library; no reaction repository is used |
| reaction_records.py | LiteratureReactionRecords.literature_reaction_repository | episode function | episode function (not carried, library missing): literature_reaction_storage / literature_component_binding are not in the library; no reaction repository is used |
| reaction_records.py | LiteratureReactionRecords._population_routes | episode function | episode function (not carried, library missing): literature_reaction_storage / literature_component_binding are not in the library; no reaction repository is used |
| received_execution_information.py | received_execution_information | machinery | old received-reader catalog (catalog.received) |
| received_reports.py | LiteratureReceivedReports | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports.received_report_sources | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports.received_report_facts | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports._complete_requested_received_arrays | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports.received_form_references | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports.received_evidence_tokens | machinery | child-report reception: no children, own-role facts are {} |
| received_reports.py | LiteratureReceivedReports.validate_received_report | episode function | episode function (not carried, library missing): validation of returned reaction cells; no reaction fact source is declared in RETURN_FORM |
| source_custody.py | LiteratureSourceCustody | episode function | messages/internal_summary.py source_custody and task.py _within_source |
| source_custody.py | LiteratureSourceCustody._require | machinery | old receipt-bound read; custody is the system |
| source_custody.py | LiteratureSourceCustody._artifact | episode function | messages/internal_summary.py source_custody (REPRESENTATION_FIELD) |
| source_custody.py | LiteratureSourceCustody._within_source | episode function | task.py _within_source |
| source_custody.py | LiteratureSourceCustody._validate_page | episode function | messages/internal_summary.py source_custody |
| source_operations.py | LiteratureSourceOperations | episode function | task.py tools and action |
| source_operations.py | LiteratureSourceOperations.catalog | episode function | task.py TOOLS, OUTPUT_SCHEMA and INSTRUCTIONS (the tools shown to the model) |
| source_operations.py | LiteratureSourceOperations.execute | episode function | task.py tools read_source_window, list_xlsx_sheets, read_xlsx_rows (assigned-sheet check literature_table_sheet_mismatch), report |
| source_operations.py | LiteratureSourceOperations._tool_arguments | episode function | task.py action (arguments, source containment, assigned sheet) |
| source_operations.py | LiteratureSourceOperations._materialize_text_arguments | episode function | episode function (not carried, library missing): text-witness materialization for populate; task.py literature_reaction_populate raises |
| task.py | SourceInvestigationTask | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task.py | SourceInvestigationTask.next | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_action.py | SourceTaskAction | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_action.py | SourceTaskAction.apply_response | machinery | old apply_response flow; its rejection of an invalid answer is task.py action (Rejected); repair text for closed_top_level_form_required / component_native_return_channels_required belongs to the old parent-written form |
| task_action.py | SourceTaskAction.execute | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.call | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.instructions | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.conversation_key | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.interpretation_context | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.exchange_schema | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.exchange_response | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_request | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_history | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.exchange_decision | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_decision.py | SourceTaskDecision.decision_completion | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_instructions.py | instructions | episode function | task.py INSTRUCTIONS |
| task_presentation.py | present_source_context | episode function | task.py decide (the context and instructions rendered as ModelRequest) |
| task_report_delivery.py | SourceTaskReportDelivery | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_report_delivery.py | SourceTaskReportDelivery.finish | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.__init__ | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.bind_execution_context | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.record_execution_failure | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.restore | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.record_effect | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_state.py | SourceTaskState.checkpoint | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_suspension.py | SourceTaskSuspension | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| task_suspension.py | SourceTaskSuspension.suspension_changed | machinery | old iterator, decision exchange, report delivery, state/checkpoint, suspension (README 3a, 3e) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (credit, finding, reads; reaction fact sources not declared, library missing) |
| to_parent.py | LiteratureReport.resolve | episode function | messages/final_to_parent.py validate_report (every finding source is held) |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (the validate_form call is not carried: axis a110 has no validate_form) |
| waiting.py | LiteratureWaiting | machinery | supports_wait False; wait machinery |
| waiting.py | LiteratureWaiting.supports_wait | machinery | supports_wait False; wait machinery |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py yield_controller (AccumulationYieldController; the old one returned None) |
| yield_estimator.py | LiteratureYield.continuation_task | machinery | returned None; no private continuation |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
