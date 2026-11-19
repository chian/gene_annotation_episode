# a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/`
(27 Python files; no subfolders, no `grading/` or `scoring/`). Nothing from the old shared root was read.

Old binding: class `LiteratureEpisode`, old role `literature_ordered`,
`binding_path = '.../source_evidence_examination/source_coverage_improvement'`,
`commissioning_parent = '.../source_evidence_examination'` (old role `literature_page`), binding version
`literature_episode_binding_v1`. Decision source `SourceTask`, renderer `present_source_decision`.

## What this episode is for

It reads one source in document order from a starting window, deciding as it goes whether to continue, reread,
move or interpret. In its own words (`goal.py`):

> Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations
> and retain representation identity. Decide whether to continue, reread, change the examined window or interpret
> obtained evidence from actual outcomes.

followed by the shared literature paragraph (iterative investigation; no reading quota or complete-document
requirement; a supplied reading selector is context, not an automatically executed action; preserve byte anchors;
navigation and byte coverage earn no credit; the commissioned task's yield settings guide continuation).

## Task and instructions

- Permitted common actions: `tool`, `reason`, `child`, `redeliver_report`; no `wait`. `child` is listed but
  `child_roles` is empty.
- Instructions: default runner instructions + goal text, reasoning-commit requirement, tool knowledge, launch library,
  `redeliver_report` paragraph, `request_context` history guidance.
- Reasoning: `source_lead` for `verified_source_leads` tasks; witness read bounded to the page source.
- Constructor settings as its parent.

## What it reads from its parent's assignment

Assignment form (`from_parent.py`), version `reading_assignment_v1`:

| Field | Meaning |
|---|---|
| `version` | const `reading_assignment_v1` |
| `page` | the parent's page assignment (`page_assignment_v1`), validated as in the parent |
| `selection` | exactly one window (`source_ref`, `representation`, `offset`, `limit`) — where reading starts |
| `literature_task` | commissioned task; required with `private_yield_binding` |
| `proposed_annotation_ref` | must equal the parent's |
| requested components | structure components requested |

Checks: the window is on the page's source and representation and its offset is within the artifact size; when the
parent is `literature_page`, the parent's page assignment is re-validated with this episode's own schema
(`commissioning_page_assignment.py`) and the page source must lie within it. Private yield binding fill-in as
elsewhere.

## Children

None (`child_roles` returns `()`; no child receiver/assembler).

## Decision state and what it shows the model

`page = assignment.get('page')`: `literature_assignment` (including the window), `literature_source_custody` for
the page source, `own_literature_outcomes` (first `outcome_page_size`), `literature_history_meaning`; with
`structure_population`, `literature_experimental_work` and population task context.

## Tools it offers

Access tools only, page-bound, plus `literature.structure.populate` with `structure_population`. No acquisition tools.

## How its credit is counted

Kind `scientific`, scientific credit view, `LiteratureTaskCredit` projector in the task's `credit_unit`; every
returned action enters with its credit; no bounding.

## Continuation

The commissioned task's private yield declaration (`kind`, `cutoff`, `uncertainty_alpha`); no own controller without
`private_yield_binding`. Declared `kind` to be mapped onto one of the three yield estimators.

## What it reports to its parent

The parent's declared form from structure rate facts, `SCREENING` answers, `LEADS` dispositions, and the last
interpretation.

## How it differs from similar episodes

- vs its sibling `passage_evidence_extraction` (old `literature_targeted`): goal text, role string, and selection
  shape only — one starting window (`selection = _WINDOW`, checked as `[selected]`) versus a list of separate spans.
  All other files are identical apart from the role string.
- vs its parent `source_evidence_examination`: reading assignment (page + window) instead of a bare page;
  authenticates the parent's page; commissions nothing.
- The folder name says "coverage improvement" but its goal explicitly sets no reading quota or complete-document
  requirement; byte coverage earns no credit.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding record: version `literature_episode_binding_v1`, `binding_id` = this folder's path, configuration `outcome_page_size`, `structure_population`. | none |
| `child_commissioning.py` | 12 | No child roles (`()`), although `child` stays in the permitted common actions. | `BindingContext.role` x2 |
| `commissioning_page_assignment.py` | 28 | Schema and validation of the commissioning `literature_page` parent's page assignment, rebuilt with this episode's own settings (private yield binding), used to authenticate the parent. | `literature_task_credit.task_schema` |
| `configuration.py` | 13 | Contract-information profile applies when the role is a literature role (or the root annotation with `reference_parent_sources`). | `BindingContext.path`, `BindingContext.role` x2 |
| `credit.py` | 17 | Credit kind `scientific`; credit view from the scientific credit service; credit projector `LiteratureTaskCredit` (task-unit credit). | `BindingContext.role` x2, `literature_task_credit.LiteratureTaskCredit`, `services.scientific_credit` |
| `decision_delivery.py` | 346 | Old decision call path (journaled model calls, `request_context` exchange protocol, contract-information validation, launch-instruction library, child options, resource estimates, waiting support). Own intent: execution expectations captured under `literature_ordered`; otherwise runner machinery. | `episode_work_report.completed_action_reports`, `episode_work_report.requested_action_history`, `library.hpc_prompt.is_hpc_context`, `module:runtime`, `runtime._action_generation_schema` x2, `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information` x2, `runtime.composition_lookup_schema` x2, `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` x2, `runtime.DECISION_EXCHANGE_PROTOCOL` x5, `runtime._digest`, `runtime.Draft202012Validator`, `runtime.instructional_model_context` x4, `runtime.is_contract_information`, `runtime._json` x14, `runtime.json` x3, `runtime.lookup_attempts`, `runtime.Mapping` x4, `runtime.model_snapshot` x2, `runtime._object` x3, `runtime._plain` x2, `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` x2, `runtime.schema_failure_diagnostic` x2, `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` x5, `runtime.WorkflowError` x14, `runtime.yield_table`, `table:runtime_model_calls` x8, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.controller_binding`, `workflow.decision_exchanges` x4, `workflow.decision_protocol` x3, `workflow.episode_bindings`, `workflow.execute`, `workflow.execution_expectations`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.is_job_source` x3, `workflow.job_episodes` x2, `workflow.journal` x3, `workflow.launch_instructions` x2, `workflow.native_estimation_context`, `workflow.numerical_contracts`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.provider` x3, `workflow.receipts` x4, `workflow.resource_context`, `workflow.resource_estimator` x5, `workflow.run_id`, `workflow.services` x2, `workflow.shared_information_context`, `workflow.specialist`, `workflow.store` x2, `workflow.uses_received_record_context` x2, `workflow.validate_contract_information` x5, `workflow.waiting_support` |
| `decision_presentation.py` | 43 | Chooses a text prompt renderer from reconstructed state frames, keeps lookup results, falls back to JSON. No episode-specific content. | `module:providers`, `providers.apply_state_frame` x3, `providers.DECISION_CONTEXT_VERSION`, `providers.deepcopy`, `providers.json`, `providers.text_instructions` |
| `episode.py` | 78 | Class `LiteratureEpisode`; `roles = ('literature_targeted',)`; same constructor settings; mixes in `SourceCommissioningPageAssignment`; permitted actions `tool`, `reason`, `child`, `redeliver_report`; no child receiver/assembler. | `BindingContext.role`, `literature_task_credit.validate_yield_bindings` |
| `from_parent.py` | 85 | Assignment `reading_assignment_v1`: `page` (page assignment) + `selection` (exactly one `_WINDOW`) + `literature_task`, `proposed_annotation_ref`, requested components. The window must be on the page's source and representation and start within the artifact size. When the parent is `literature_page`, the parent's own page assignment is re-validated and this page's source must lie within it. | `BindingContext.assignment` x2, `BindingContext.role`, `BindingContext.scope`, `literature_task_credit._task_key`, `literature_task_credit.task_schema`, `services.read_record` |
| `goal.py` | 8 | The goal text (quoted above). | `BindingContext.role` |
| `internal_summary.py` | 83 | Decision context: `literature_assignment`, source custody (version/artifact/text/stdout/stderr/parent sources), first `outcome_page_size` own outcomes of acquisition+read tools, `literature_history_meaning`; with `structure_population` also `literature_experimental_work` (aspect `source_experimental_evidence`) and population task context (own completed population sheets; latest failed population attempt). Root-only `reference_evidence_parent` initial context. | `BindingContext.assignment`, `BindingContext.episode_id` x4, `BindingContext.path`, `BindingContext.received_record_refs` x2, `BindingContext.role` x2, `BindingContext.run_id` x5, `BindingContext.scope` x4, `literature_task_selection.population_task_metadata_specs`, `services.own_outcomes`, `table:runtime_actions` x2, `workflow.run_id` x2, `workflow.store` x2 |
| `presentation_selection.py` | 30 | Predicate order of prompt renderers (hpc, published scientific, monitor, API launch, selected execution, receiver). No episode-specific content. | `library.hpc_prompt.is_hpc_context`, `library.hpc_prompt.render_hpc_prompt`, `library.monitor_prompt.is_monitor_context`, `library.monitor_prompt.render_monitor_prompt`, `receiver_prompt.render_receiver_prompt`, `structural_homology_evidence_prompt.is_selected_execution_context`, `structural_homology_evidence_prompt.render_selected_execution_prompt`, `module:providers`, `providers.is_api_launch_context` x2, `providers.is_published_scientific_context` x2, `providers._ordinary_runtime_receiver_context`, `providers.render_api_launch_prompt`, `providers.render_structural_homology_evidence_prompt` |
| `received_evidence.py` | 73 | Receiving structure-population cells from children, current sheet refs, received evidence tokens; validation that a returned screening/leads answer equals the child's saved work and that returned structure cells cite permitted sheets and requested components. | `BindingContext.assignment` x2, `BindingContext.episode_id`, `BindingContext.received_record_refs`, `BindingContext.request`, `BindingContext.role` x2, `BindingContext.run_id`, `literature_sheet_updates.current_sheet_refs`, `literature_task_credit.lead_dispositions`, `literature_task_credit.LEADS`, `literature_task_credit.screening_answers`, `literature_task_credit.SCREENING`, `method_loop.durable.content_digest`, `services.record_selection`, `workflow.store` x2 |
| `report_delivery.py` | 25 | `finish`: without a report contract returns credit + pending handles + current report facts; otherwise builds the form from facts and the interpretation, saved once. | `library.private_policy_call.invoke`, `library.report_fact_assembly.facts`, `module:runtime`, `runtime.form_with_facts`, `runtime._json` x2, `runtime.json`, `runtime.Record` x2, `table:runtime_forms` x2, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.facts`, `workflow.journal` x2, `workflow.pending_handles`, `workflow.release` x2, `workflow.source_credit_view` |
| `source_contracts.py` | 38 | Literature constants: `VERSION`, `ROLES` (7 literature roles), `_WINDOW`/`_TABLE`/`_PAGE` schemas, tool lists `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`, population catalog (`literature.structure.populate`). | `communication.plain`, `communication.ReportBoundaryError`, `communication.validate_form`, `composition_information.CONTRACT_INFORMATION_PROFILE`, `domain.ContractError`, `domain.identity`, `domain.obj`, `domain.REF`, `domain.source_location_inputs`, `domain.validate_schema`, `episode_bindings.reference_in_context`, `experimental_database_acquisition.OPERATIONS` |
| `source_interpretation.py` | 43 | For a `verified_source_leads` task the reasoning action carries a `source_lead`; executing it re-checks the witness read is permitted, commits reasoning and validates the lead in one transaction; invalid leads return an `invalid` outcome. | `BindingContext.assignment`, `BindingContext.episode_id`, `BindingContext.run_id`, `BindingContext.scope`, `literature_contract_error.ExperimentalContractError`, `literature_task_credit.commissioned_task`, `literature_task_credit.lead_schema` x2, `literature_task_credit.validate_lead`, `workflow.store` |
| `source_operations.py` | 93 | Access tools only, page-bound (same as the page episode). | `BindingContext.assignment`, `BindingContext.received_record_refs`, `BindingContext.role` x2, `BindingContext.scope` x6, `composition_information.CONTRACT_ARGUMENT_TRANSPORT`, `library.literature_assay_inputs.materialize_text_witness_inputs`, `literature_contract_error.ExperimentalContractError`, `services.execute_tool`, `services.tool_catalog` |
| `source_references.py` | 35 | Reference checks: `_require` (in scope, namespace), `_artifact` (representation to artifact), `_within_source` (walks `parent_source_refs`), `resolve`. | `BindingContext.role`, `services.read_record`, `services.reference_in_scope` |
| `structural_sheet_operations.py` | 17 | Literature structure repository (source-model geometry / local-fit components) and the single population route when `structure_population`. | `literature_structure_storage.LiteratureStructureRepository`, `workflow.run_id`, `workflow.store` |
| `task.py` | 269 | Old iterative loop (`next`, `apply_response`, `execute`): replay, model inputs, reasoning/tool/wait execution, report update admission, credit after each observed outcome. Own intent: report grain `literature_ordered`; empty reasoning commit rejected unless it carries task content (a source lead); report lifecycle sentence. | `episode_source_failure.record_source_failure`, `library.action_contracts.action_schema`, `library.private_policy_call.invoke`, `read_mapping.parameter_schema_failure`, `module:runtime`, `runtime.AcquisitionError` x2, `runtime.ActionFailure`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator` x3, `runtime.EventTargetError` x2, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.inspect`, `runtime._json` x5, `runtime.json` x10, `runtime.Mapping` x6, `runtime.nullcontext` x5, `runtime.observes_action_outcome`, `runtime._plain` x2, `runtime._references_in`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery` x2, `runtime.schema_failure_diagnostic`, `runtime.SourceEnd` x2, `runtime.sqlite3` x2, `runtime.subprocess` x2, `runtime.validate_form`, `runtime.ValidationError` x3, `runtime._wait_target_feedback` x2, `runtime.WorkflowError` x2, `SourceView.child_reports` x2, `SourceView.controller_state`, `SourceView.model_inputs`, `SourceView.units_consumed` x4, `table:runtime_actions` x10, `table:runtime_episodes`, `table:runtime_model_calls` x2, `workflow.action_schema`, `workflow.annotation_context`, `workflow.automatic_score_updates`, `workflow.binding_context` x3, `workflow.catalog`, `workflow.completed_unit` x3, `workflow.completions` x3, `workflow.controller_binding`, `workflow.controller_value` x2, `workflow.decision_exchanges` x3, `workflow.delivery_resolution_inputs`, `workflow.delivery_status`, `workflow.execute`, `workflow.execution_binding` x7, `workflow.extra_report_sources`, `workflow.inprocess_replay` x4, `workflow.is_scientific_source`, `workflow.job_episode_options`, `workflow.journal` x10, `workflow.knowledge`, `workflow.last_observed_credit`, `workflow.local_outcome_preview`, `workflow.next_return`, `workflow.pending_work` x2, `workflow.perform_selected_wait`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receipt_projection`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` x4, `workflow.selected` x3, `workflow.source_credit_binding`, `workflow.source_credit_view` x2, `workflow.specialist` x3, `workflow.store` x12, `workflow.tools`, `workflow.validate_report`, `workflow.working_state` |
| `task_instructions.py` | 26 | Instruction composition: goal text, reasoning-commit requirement, tool knowledge, launch library, `redeliver_report` paragraph, wait paragraphs (only if wait permitted; not here), `request_context` history guidance. | `module:runtime_prompt`, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`, `runtime_prompt.INSTRUCTIONS` x4, `runtime_prompt.REASONING_COMMIT_REQUIREMENT`, `workflow.binding_context`, `workflow.decision_protocol`, `workflow.is_job_source`, `workflow.job_episodes`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.permits_common_action` x3, `workflow.specialist` |
| `task_state.py` | 108 | Source state: report values, feedback, restore/checkpoint, recording an execution failure as a failed outcome that still enters the iterator with credit. Runner machinery. | `episode_source_failure.record_source_failure`, `module:runtime`, `runtime.ActionLeaf`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.interpretation_schema`, `runtime._json` x2, `runtime.json` x4, `runtime._object`, `runtime._plain`, `runtime.Record`, `table:runtime_actions` x5, `workflow.archive`, `workflow.completions` x4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding` x4, `workflow.grains`, `workflow.inprocess_replay` x7, `workflow.journal` x5, `workflow.progress_provider` x2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store` x2 |
| `task_waiting.py` | 9 | Passes a suspension condition to the execution backend. Runner machinery. | `workflow.execution_backend`, `workflow.execution_handle` x2 |
| `to_parent.py` | 41 | Report fact sources: structure rate facts (if `structure_population`), `SCREENING` answers, `LEADS` dispositions; `facts` fills them for the task kind; `validate_report` checks assignment, form refs and received cells. | `BindingContext.assignment` x4, `BindingContext.received_record_refs`, `BindingContext.role` x2, `BindingContext.scope`, `literature_task_credit.lead_dispositions`, `literature_task_credit.lead_return_schema`, `literature_task_credit.LEADS` x2, `literature_task_credit.screening_answers`, `literature_task_credit.screening_schema`, `literature_task_credit.SCREENING` x2, `services.read_record`, `workflow.store` x2 |
| `waiting.py` | 8 | `supports_wait = False`. | none |
| `yield_estimator.py` | 22 | `continuation_task` key; `yield_controller` built from the commissioned task's private yield declaration (`kind`, `cutoff`, `uncertainty_alpha`); none without `private_yield_binding`. | `BindingContext.role` x2, `literature_task_credit.continuation_task` x2, `literature_task_credit._private_yield_controller` |

Old-runner names are counted per occurrence: `workflow.<member>` covers `self.workflow`, `source.workflow`, the `workflow` parameter and `self.services.workflow`; `BindingContext.<field>` covers `context.`/`parent.` binding-context fields; `SourceView.<member>` the old loop's view; `runtime.`/`providers.`/`runtime_prompt.` the old per-axis modules; `table:` old journal/receipt tables; other names are imports from the old shared root (`root/a102/...`). Row-level detail: `runs/carry_over/calls/a102_07.tsv`.

## Old-runner names (totals for this episode)

| Kind | Distinct names | Uses |
|---|---|---|
| `BindingContext` | 8 | 65 |
| `import:communication` | 3 | 3 |
| `import:composition_information` | 2 | 2 |
| `import:domain` | 6 | 6 |
| `import:episode_bindings` | 1 | 1 |
| `import:episode_source_failure` | 1 | 2 |
| `import:episode_work_report` | 2 | 2 |
| `import:experimental_database_acquisition` | 1 | 1 |
| `import:library` | 8 | 10 |
| `import:literature_contract_error` | 1 | 2 |
| `import:literature_sheet_updates` | 1 | 1 |
| `import:literature_structure_storage` | 1 | 1 |
| `import:literature_task_credit` | 15 | 24 |
| `import:literature_task_selection` | 1 | 1 |
| `import:method_loop` | 1 | 1 |
| `import:read_mapping` | 1 | 1 |
| `import:receiver_prompt` | 1 | 1 |
| `import:structural_homology_evidence_prompt` | 2 | 2 |
| `module` | 3 | 7 |
| `providers` | 10 | 14 |
| `runtime` | 53 | 163 |
| `runtime_prompt` | 3 | 6 |
| `services` | 7 | 9 |
| `SourceView` | 4 | 8 |
| `table` | 4 | 30 |
| `workflow` | 76 | 214 |

## Carried over

Episode: `source_coverage_improvement` (old role `literature_ordered`), carried 19 November 2026 as a private ten-file binding without children. Old = `97308b94c`. Library candidates are marked.

| old file | name | kind | new place / machinery reason |
|---|---|---|---|
| binding_record.py | SourceBindingRecord | machinery | binding_record.py / the binding's own as_record(): the system records the binding and its settings |
| binding_record.py | SourceBindingRecord.as_record | machinery | binding_record.py / the binding's own as_record(): the system records the binding and its settings |
| child_commissioning.py | SourceChildCommissioning | machinery | child roles: CHILD_SLOTS = {} in task.py; the old allowed_children/child_roles (both empty) are the slot table |
| child_commissioning.py | SourceChildCommissioning.allowed_children | machinery | child roles: CHILD_SLOTS = {} in task.py; the old allowed_children/child_roles (both empty) are the slot table |
| child_commissioning.py | SourceChildCommissioning.child_roles | machinery | child roles: CHILD_SLOTS = {} in task.py; the old allowed_children/child_roles (both empty) are the slot table |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment | machinery | authentication of the commissioning literature_page parent's page assignment by the child: a check of a commission (rule 1), not carried; the parent now passes the page in the child's own assignment_form |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment._commissioning_page_schema | machinery | authentication of the commissioning literature_page parent's page assignment by the child: a check of a commission (rule 1), not carried; the parent now passes the page in the child's own assignment_form |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment._validate_commissioning_page_assignment | machinery | authentication of the commissioning literature_page parent's page assignment by the child: a check of a commission (rule 1), not carried; the parent now passes the page in the child's own assignment_form |
| configuration.py | SourceConfiguration | machinery | contract-information profile: the contract-information freezing was old-runner/shared-root content (README 5 item 16); no profile is carried |
| configuration.py | SourceConfiguration.contract_information_configuration | machinery | contract-information profile: the contract-information freezing was old-runner/shared-root content (README 5 item 16); no profile is carried |
| configuration.py | SourceConfiguration.contract_information_profile | machinery | contract-information profile: the contract-information freezing was old-runner/shared-root content (README 5 item 16); no profile is carried |
| credit.py | SourceCredit | machinery | mix-in class replaced by credit.py functions |
| credit.py | SourceCredit.credit_kind | machinery | credit kind label of the old credit view (system credit view) |
| credit.py | SourceCredit.credit_view | machinery | services.scientific_credit view: replaced by credit(summary, records) |
| credit.py | SourceCredit.credit_projector | episode function | credit.py: credit(), credit_binding(), answers() (private re-expression of LiteratureTaskCredit, library candidate) |
| decision_delivery.py | SourceDecisionDelivery | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.call | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.instructions | episode function | task.py: instructions() |
| decision_delivery.py | SourceDecisionDelivery.conversation_key | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.interpretation_context | machinery | request_context exchange context: a lookup is a tool; no exchange |
| decision_delivery.py | SourceDecisionDelivery.exchange_schema | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.exchange_response | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.validate_contract_exchange_request | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.validate_contract_exchange_history | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.exchange_decision | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_delivery.py | SourceDecisionDelivery.complete_decision | machinery | old decision call path (journaled model calls, request_context exchange, state frames, contract-information validation, waiting support, exchange validation): replaced by decide/action; execution expectations / launch library are not part of this episode (no job) |
| decision_presentation.py | present_source_decision | machinery | renderer selection from reconstructed state frames: replaced by ModelRequest.context built in decide (task.py) |
| episode.py | LiteratureEpisode | episode function | episode.py: SourceCoverageImprovement(EpisodeBinding) |
| episode.py | LiteratureEpisode.__init__ | machinery | constructor settings (outcome_page_size, structure_population, yield bindings, profile): fixed values are constants of internal_summary.py/task.py; run values are ctx.settings; validate_yield_bindings is replaced by read_from_parent task validation |
| episode.py | LiteratureEpisode.reference_evidence | machinery | root-only reference-evidence constructor (reference_parent_sources): not this episode's |
| episode.py | LiteratureEpisode._role | machinery | role check of a shared per-kind class: each role is its own episode |
| episode.py | LiteratureEpisode.permitted_common_actions | episode function | task.py: tools and reason/report tools offered; child and redeliver_report are not carried (no child; redelivery deleted) |
| from_parent.py | SourceFromParent | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM, read_from_parent, task_key (old _task_key) |
| from_parent.py | SourceFromParent.child_assignment_schema | machinery | child assignment schema as the parent's: parent builds in msg_to_child (no child here) |
| from_parent.py | SourceFromParent.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM |
| from_parent.py | SourceFromParent._validate_page | machinery | page source/artifact/scope membership checks of a commission: custody (the received records are named in received_record_refs); a wrong commission fails |
| from_parent.py | SourceFromParent._validate_assignment | episode function | messages/read_from_parent.py: read_from_parent (window on page source and representation) and messages/internal_summary.py (offset within artifact size); the schema part is ASSIGNMENT_FORM |
| from_parent.py | SourceFromParent.prepare_assignment | machinery | private yield binding fill-in, proposed-annotation equality and literature_page parent re-validation: checks/fill-in of a commission; the commissioner supplies credit_unit in literature_task (read_from_parent checks it is finite and positive) |
| goal.py | SourceGoal | episode function | goal.py: GOAL |
| goal.py | SourceGoal.instructions | episode function | goal.py: GOAL |
| internal_summary.py | SourceInternalSummary | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | SourceInternalSummary.initial_decision_context | machinery | root-only reference_evidence_parent initial context: not this episode's (README intent record) |
| internal_summary.py | SourceInternalSummary.decision_context | episode function | messages/internal_summary.py: internal_summary (literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning); with structure_population the experimental-work context belongs to the population route (not built, decide raises) |
| internal_summary.py | SourceInternalSummary._owned_population_task_sources | machinery | structure population route context read from raw SQL (runtime tables, store.db): population route not built; decide raises NotImplementedError(literature_structure_population_not_built) when settings ask for it |
| internal_summary.py | SourceInternalSummary._population_task_context | machinery | structure population route context read from runtime_actions: population route not built; decide raises |
| presentation_selection.py | source_presentation_selection | machinery | predicate order of prompt renderers (hpc, monitor, API launch, receiver): no episode content; decide renders its own context |
| received_evidence.py | SourceReceivedEvidence | episode function | messages/final_to_parent.py |
| received_evidence.py | SourceReceivedEvidence.received_report_sources | machinery | receiving structure cells from children: this episode has no child |
| received_evidence.py | SourceReceivedEvidence.received_report_facts | machinery | receiving structure cells from children: this episode has no child |
| received_evidence.py | SourceReceivedEvidence._complete_requested_received_arrays | machinery | report_contract schema completion of a parent-written form: the child declares RETURN_FORM |
| received_evidence.py | SourceReceivedEvidence.received_form_references | machinery | receipts bookkeeping of received references (custody) / structure cells from children |
| received_evidence.py | SourceReceivedEvidence.received_evidence_tokens | machinery | receipts bookkeeping (received evidence tokens): custody |
| received_evidence.py | SourceReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py: validate_report (answers compare to saved work: both computed from one summary); structure-cell checks belong to the population route (not built) |
| report_delivery.py | SourceReportDelivery | episode function | messages/final_to_parent.py: final_to_parent |
| report_delivery.py | SourceReportDelivery.finish | episode function | messages/final_to_parent.py: final_to_parent (RETURN_FORM from facts + interpretation; pending handles, runtime_forms, release are machinery) |
| source_contracts.py | _population_catalog | episode function | task.py: POPULATE_DESCRIPTION / literature_structure_populate (raises literature_structure_population_not_built) |
| source_interpretation.py | SourceSourceInterpretation | episode function | task.py: reason_schema, reason, validate_source_lead |
| source_interpretation.py | SourceSourceInterpretation.reasoning_action_schema | episode function | task.py: reason_schema |
| source_interpretation.py | SourceSourceInterpretation.reasoning_has_task_content | episode function | task.py: action (empty_commit rule) and validate_source_lead (library candidate: library validate_lead takes the old binding context) |
| source_interpretation.py | SourceSourceInterpretation.execute_reasoning | episode function | task.py: reason tool (one transaction: commit_reasoning + lead validation + evidence processing) |
| source_operations.py | SourceSourceOperations | episode function | task.py: access tools and run_access_tool |
| source_operations.py | SourceSourceOperations.catalog | episode function | task.py: catalog(), offered(), DESCRIPTIONS, INPUT_SCHEMAS |
| source_operations.py | SourceSourceOperations.execute | episode function | task.py: run_access_tool, invalid, the tool functions in TOOLS |
| source_operations.py | SourceSourceOperations._tool_arguments | episode function | task.py: admitted(), within_source() |
| source_operations.py | SourceSourceOperations._materialize_text_arguments | machinery | materialization of text witnesses for literature.structure.populate: population route not built |
| source_references.py | SourceSourceReferences | episode function | task.py: within_source (library: records/received_records.py read_record_in_scope) |
| source_references.py | SourceSourceReferences._require | episode function | already in library: episode_support/records/received_records.py read_record_in_scope |
| source_references.py | SourceSourceReferences._artifact | episode function | task.py: examined_spans (artifact of a representation) |
| source_references.py | SourceSourceReferences._within_source | episode function | task.py: within_source (library candidate) |
| source_references.py | SourceSourceReferences.resolve | machinery | reference_in_context resolver for the old validate_form: custody; A102 has no validate_form (raises validate_form_not_built:A102 in final_to_parent) |
| structural_sheet_operations.py | SourceStructuralSheetOperations | episode function | task.py: literature_structure_populate (population route not built) |
| structural_sheet_operations.py | SourceStructuralSheetOperations.literature_structure_repository | episode function | task.py: literature_structure_populate raises: LiteratureStructureRepository is not in episode_support (unplaced) |
| structural_sheet_operations.py | SourceStructuralSheetOperations._population_routes | episode function | task.py: literature_structure_populate raises: population_route is not in episode_support (unplaced) |
| task.py | SourceTask | episode function | task.py: decide, action, tools |
| task.py | SourceTask.next | episode function | task.py: decide (context, tools, schema); replay/exchange/wait/redeliver parts are machinery |
| task.py | SourceTask.apply_response | episode function | task.py: action (validation, empty-commit rule); report update admission is the report tool; rejection path via rejection_feedback |
| task.py | SourceTask.execute | episode function | task.py: tool functions (access tools, reason, report); wait/redeliver/child branches and replay are machinery |
| task_instructions.py | compose_instructions | episode function | task.py: instructions |
| task_state.py | SourceTaskState | machinery | task state: the loop view is the system's |
| task_state.py | SourceTaskState.__init__ | machinery | task state fields (report values, feedback, effects) |
| task_state.py | SourceTaskState.bind_execution_context | machinery | execution binding of the old runner |
| task_state.py | SourceTaskState.record_execution_failure | machinery | failed tool recorded as an outcome: run_access_tool returns failure_outcome(...) in task.py |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.restore | machinery | replay/restore |
| task_state.py | SourceTaskState.record_effect | machinery | effect recording |
| task_state.py | SourceTaskState.checkpoint | machinery | checkpoint |
| task_waiting.py | SourceTaskWaiting | machinery | wait/suspension |
| task_waiting.py | SourceTaskWaiting.suspension_changed | machinery | wait/suspension |
| to_parent.py | SourceToParent | episode function | messages/final_to_parent.py |
| to_parent.py | SourceToParent.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (SCREENING, LEADS, STRUCTURE under their old names) |
| to_parent.py | SourceToParent.facts | episode function | messages/final_to_parent.py: final_to_parent; messages/internal_summary.py (answers) |
| to_parent.py | SourceToParent.current_report_facts | machinery | returns {} (no current report facts) |
| to_parent.py | SourceToParent._rate_fact_sources | episode function | messages/final_to_parent.py: STRUCTURE field (population route not built: selecting raises) |
| to_parent.py | SourceToParent._rate_facts | episode function | messages/final_to_parent.py: STRUCTURE (raises literature_structure_population_not_built) |
| to_parent.py | SourceToParent.validate_report | episode function | messages/final_to_parent.py: validate_report (ends in NotImplementedError validate_form_not_built:A102) |
| waiting.py | SourceWaiting | machinery | wait support flag |
| waiting.py | SourceWaiting.supports_wait | machinery | wait support flag |
| yield_estimator.py | SourceYield | episode function | yield_estimator.py |
| yield_estimator.py | SourceYield.continuation_task | episode function | messages/read_from_parent.py: task_key and the task in parent input |
| yield_estimator.py | SourceYield.yield_controller | episode function | yield_estimator.py: yield_controller |
