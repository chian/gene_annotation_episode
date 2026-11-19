# a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/`
(27 Python files; no subfolders, no `grading/` or `scoring/`). Nothing from the old shared root was read.

Old binding: class `LiteratureEpisode`, old role `literature_targeted`,
`binding_path = '.../source_evidence_examination/passage_evidence_extraction'`,
`commissioning_parent = '.../source_evidence_examination'` (old role `literature_page`), binding version
`literature_episode_binding_v1`. Decision source `SourceTask`, renderer `present_source_decision`.

## What this episode is for

It examines specific passages of one source that its parent selected, reading around them as needed. In its own words
(`goal.py`):

> Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications
> or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain
> separate; never concatenate them into a fabricated quotation.

followed by the shared literature paragraph (iterative investigation; a supplied reading selector is context, not an
automatically executed action; preserve subject, conditions, representation, version and UTF-8 byte anchors;
navigation and byte coverage earn no credit; the commissioned task's yield settings guide continuation).

## Task and instructions

- Permitted common actions: `tool`, `reason`, `child`, `redeliver_report`; no `wait`. `child` is listed but
  `child_roles` is empty, so there is nothing to commission.
- Instructions: default runner instructions + goal text, reasoning-commit requirement, tool knowledge, launch library,
  `redeliver_report` paragraph, `request_context` history guidance.
- Reasoning: `source_lead` for `verified_source_leads` tasks; witness read bounded to the page source.
- Constructor settings as its parent and grandparent.

## What it reads from its parent's assignment

Assignment form (`from_parent.py`), version `reading_assignment_v1`:

| Field | Meaning |
|---|---|
| `version` | const `reading_assignment_v1` |
| `page` | the parent's page assignment (`page_assignment_v1`: source, representation, artifact, question context, prior deliveries), validated as in the parent |
| `selection.spans` | one or more windows (`source_ref`, `representation`, `offset`, `limit`) — the passages to examine |
| `literature_task` | commissioned task; required with `private_yield_binding` |
| `proposed_annotation_ref` | must equal the parent's |
| requested components | structure components requested |

Checks: each span is on the page's `source_ref` and `representation`, and its `offset` is not past the artifact's
size. When the commissioning parent is `literature_page`, this episode re-validates the parent's own page assignment
with its own schema (`commissioning_page_assignment.py`, built with this episode's private-yield setting) and
requires the page source here to lie within the parent's source. Private yield binding fill-in as elsewhere.

## Children

None (`child_roles` returns `()`; no `from_child_*` / `to_child_*` files; no receiver/assembler methods).

## Decision state and what it shows the model

`internal_summary.py` with `page = assignment.get('page')`: `literature_assignment` (including the spans),
`literature_source_custody` for the page source, `own_literature_outcomes` (first `outcome_page_size` own
acquisition/read outcomes), `literature_history_meaning`; with `structure_population`, `literature_experimental_work`
and population task context. The spans are shown as context, never executed automatically.

## Tools it offers

Access tools only, page-bound, plus `literature.structure.populate` with `structure_population` (same as its parent
`source_evidence_examination`). No acquisition tools.

## How its credit is counted

Kind `scientific`, scientific credit view, `LiteratureTaskCredit` projector in the task's `credit_unit`; every
returned action enters with its credit; no bounding.

## Continuation

The commissioned task's private yield declaration (`kind`, `cutoff`, `uncertainty_alpha`) via
`_private_yield_controller`; no own controller without `private_yield_binding`. Declared `kind` to be mapped onto one
of the three yield estimators.

## What it reports to its parent

The parent's declared form from structure rate facts, `SCREENING` answers, `LEADS` dispositions, and the last
interpretation (`to_parent.py`, `report_delivery.py`).

## How it differs from similar episodes

- vs its sibling `source_coverage_improvement` (old `literature_ordered`): only the goal text, the role string and
  the selection shape differ. Here `selection` is `{spans: [window, ...]}` (one or more separate passages, never
  concatenated); the sibling takes exactly one window and reads in document order with byte continuations.
- vs its parent `source_evidence_examination`: takes a `reading_assignment_v1` (page + selection) instead of a bare
  page; authenticates the parent's page assignment; commissions nothing.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding record: version `literature_episode_binding_v1`, `binding_id` = this folder's path, configuration `outcome_page_size`, `structure_population`. | none |
| `child_commissioning.py` | 12 | No child roles (`()`), although `child` stays in the permitted common actions. | `BindingContext.role` x2 |
| `commissioning_page_assignment.py` | 28 | Schema and validation of the commissioning `literature_page` parent's page assignment, rebuilt with this episode's own settings (private yield binding), used to authenticate the parent. | `literature_task_credit.task_schema` |
| `configuration.py` | 13 | Contract-information profile applies when the role is a literature role (or the root annotation with `reference_parent_sources`). | `BindingContext.path`, `BindingContext.role` x2 |
| `credit.py` | 17 | Credit kind `scientific`; credit view from the scientific credit service; credit projector `LiteratureTaskCredit` (task-unit credit). | `BindingContext.role` x2, `literature_task_credit.LiteratureTaskCredit`, `services.scientific_credit` |
| `decision_delivery.py` | 346 | Old decision call path (journaled model calls, `request_context` exchange protocol, contract-information validation, launch-instruction library, child options, resource estimates, waiting support). Own intent: execution expectations captured under `literature_targeted`; otherwise runner machinery. | `episode_work_report.completed_action_reports`, `episode_work_report.requested_action_history`, `library.hpc_prompt.is_hpc_context`, `module:runtime`, `runtime._action_generation_schema` x2, `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information` x2, `runtime.composition_lookup_schema` x2, `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` x2, `runtime.DECISION_EXCHANGE_PROTOCOL` x5, `runtime._digest`, `runtime.Draft202012Validator`, `runtime.instructional_model_context` x4, `runtime.is_contract_information`, `runtime._json` x14, `runtime.json` x3, `runtime.lookup_attempts`, `runtime.Mapping` x4, `runtime.model_snapshot` x2, `runtime._object` x3, `runtime._plain` x2, `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` x2, `runtime.schema_failure_diagnostic` x2, `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` x5, `runtime.WorkflowError` x14, `runtime.yield_table`, `table:runtime_model_calls` x8, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.controller_binding`, `workflow.decision_exchanges` x4, `workflow.decision_protocol` x3, `workflow.episode_bindings`, `workflow.execute`, `workflow.execution_expectations`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.is_job_source` x3, `workflow.job_episodes` x2, `workflow.journal` x3, `workflow.launch_instructions` x2, `workflow.native_estimation_context`, `workflow.numerical_contracts`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.provider` x3, `workflow.receipts` x4, `workflow.resource_context`, `workflow.resource_estimator` x5, `workflow.run_id`, `workflow.services` x2, `workflow.shared_information_context`, `workflow.specialist`, `workflow.store` x2, `workflow.uses_received_record_context` x2, `workflow.validate_contract_information` x5, `workflow.waiting_support` |
| `decision_presentation.py` | 43 | Chooses a text prompt renderer from reconstructed state frames, keeps lookup results, falls back to JSON. No episode-specific content. | `module:providers`, `providers.apply_state_frame` x3, `providers.DECISION_CONTEXT_VERSION`, `providers.deepcopy`, `providers.json`, `providers.text_instructions` |
| `episode.py` | 78 | Class `LiteratureEpisode`; `roles = ('literature_targeted',)`; same constructor settings; mixes in `SourceCommissioningPageAssignment`; permitted actions `tool`, `reason`, `child`, `redeliver_report`; no child receiver/assembler. | `BindingContext.role`, `literature_task_credit.validate_yield_bindings` |
| `from_parent.py` | 85 | Assignment `reading_assignment_v1`: `page` (page assignment) + `selection.spans` (one or more `_WINDOW`s) + `literature_task`, `proposed_annotation_ref`, requested components. Each span must be on the page's source and representation and start within the artifact size. When the parent is `literature_page`, the parent's own page assignment is re-validated and this page's source must lie within it. | `BindingContext.assignment` x2, `BindingContext.role`, `BindingContext.scope`, `literature_task_credit._task_key`, `literature_task_credit.task_schema`, `services.read_record` |
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
| `task.py` | 269 | Old iterative loop (`next`, `apply_response`, `execute`): replay, model inputs, reasoning/tool/wait execution, report update admission, credit after each observed outcome. Own intent: report grain `literature_targeted`; empty reasoning commit rejected unless it carries task content (a source lead); report lifecycle sentence. | `episode_source_failure.record_source_failure`, `library.action_contracts.action_schema`, `library.private_policy_call.invoke`, `read_mapping.parameter_schema_failure`, `module:runtime`, `runtime.AcquisitionError` x2, `runtime.ActionFailure`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator` x3, `runtime.EventTargetError` x2, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.inspect`, `runtime._json` x5, `runtime.json` x10, `runtime.Mapping` x6, `runtime.nullcontext` x5, `runtime.observes_action_outcome`, `runtime._plain` x2, `runtime._references_in`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery` x2, `runtime.schema_failure_diagnostic`, `runtime.SourceEnd` x2, `runtime.sqlite3` x2, `runtime.subprocess` x2, `runtime.validate_form`, `runtime.ValidationError` x3, `runtime._wait_target_feedback` x2, `runtime.WorkflowError` x2, `SourceView.child_reports` x2, `SourceView.controller_state`, `SourceView.model_inputs`, `SourceView.units_consumed` x4, `table:runtime_actions` x10, `table:runtime_episodes`, `table:runtime_model_calls` x2, `workflow.action_schema`, `workflow.annotation_context`, `workflow.automatic_score_updates`, `workflow.binding_context` x3, `workflow.catalog`, `workflow.completed_unit` x3, `workflow.completions` x3, `workflow.controller_binding`, `workflow.controller_value` x2, `workflow.decision_exchanges` x3, `workflow.delivery_resolution_inputs`, `workflow.delivery_status`, `workflow.execute`, `workflow.execution_binding` x7, `workflow.extra_report_sources`, `workflow.inprocess_replay` x4, `workflow.is_scientific_source`, `workflow.job_episode_options`, `workflow.journal` x10, `workflow.knowledge`, `workflow.last_observed_credit`, `workflow.local_outcome_preview`, `workflow.next_return`, `workflow.pending_work` x2, `workflow.perform_selected_wait`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receipt_projection`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` x4, `workflow.selected` x3, `workflow.source_credit_binding`, `workflow.source_credit_view` x2, `workflow.specialist` x3, `workflow.store` x12, `workflow.tools`, `workflow.validate_report`, `workflow.working_state` |
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

Carried 19 November 2026 into the ten-file form (private binding `PassageEvidenceExtraction`). "UNPLACED" rows are also in `docs/axis_restructure_20261117/carry_over_blocked/a102__structural_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.md`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | SourceBindingRecord | machinery | binding_record.py: the binding's own record (README 3e) |
| binding_record.py | SourceBindingRecord.as_record | machinery | the binding's own as_record() is deleted (README 3d/3e) |
| child_commissioning.py | SourceChildCommissioning | episode function | task.py CHILD_SLOTS = {} (no child) |
| child_commissioning.py | SourceChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| child_commissioning.py | SourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS = {} (old roles were ()) |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment | episode function | UNPLACED: authenticates the parent's own page assignment, which a child cannot read (README 5 item 14) |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment._commissioning_page_schema | episode function | UNPLACED: schema of the parent's own assignment (README 5 item 14); the page itself is messages/read_from_parent.py PAGE_FORM |
| commissioning_page_assignment.py | SourceCommissioningPageAssignment._validate_commissioning_page_assignment | episode function | UNPLACED: re-validates the parent's assignment against the Store (a check of a commission, rule 1; README 5 item 14) |
| configuration.py | SourceConfiguration | machinery | contract-information profile configuration (decision exchange, README 3a) |
| configuration.py | SourceConfiguration.contract_information_configuration | machinery | contract-information freezing (README 5 item 16) |
| configuration.py | SourceConfiguration.contract_information_profile | machinery | contract-information freezing (README 5 item 16) |
| credit.py | SourceCredit | episode function | credit.py (the mix-in is not carried; its three methods are below) |
| credit.py | SourceCredit.credit_kind | machinery | credit_kind is deleted (README 3d); it was the constant 'scientific' |
| credit.py | SourceCredit.credit_view | episode function | credit.py credit(summary, records) (and internal_summary.py for the other fields of the old view) |
| credit.py | SourceCredit.credit_projector | episode function | credit.py credit, answers, lead_dispositions, screening_answers, assessment_answers, credit_binding (private re-expression of LiteratureTaskCredit) |
| decision_delivery.py | SourceDecisionDelivery | machinery | old decision machine class (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.call | machinery | journaled model call and decision exchange loop (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.instructions | episode function | task.py instructions |
| decision_delivery.py | SourceDecisionDelivery.conversation_key | machinery | conversation state (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.interpretation_context | machinery | request_context exchange (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.exchange_schema | machinery | request_context exchange (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.exchange_response | machinery | request_context exchange (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.validate_contract_exchange_request | machinery | saved-request check (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.validate_contract_exchange_history | machinery | saved-request check (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.exchange_decision | machinery | decision-exchange loop (README 3a) |
| decision_delivery.py | SourceDecisionDelivery.complete_decision | episode function | task.py decide (returns the ModelRequest; the system asks the model) |
| decision_presentation.py | present_source_decision | machinery | prompt renderer chosen from reconstructed state frames (README 3a); the episode's own context is built in task.py decide |
| episode.py | LiteratureEpisode | episode function | episode.py PassageEvidenceExtraction(EpisodeBinding) |
| episode.py | LiteratureEpisode.__init__ | episode function | constructor values: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE; structure_population -> settings key read in task.py offered/decide; private_yield_binding / yield_bindings -> machinery (the controller is always bound from the task, yield_estimator.py); contract_information_profile -> machinery |
| episode.py | LiteratureEpisode.reference_evidence | episode function | UNPLACED: root-only entry that builds a reference-source investigation (reference_parent_sources); not this episode's |
| episode.py | LiteratureEpisode._role | machinery | role check; each role is its own episode (README 3a BindingContext.role) |
| episode.py | LiteratureEpisode.permitted_common_actions | episode function | task.py TOOLS and offered (tool, reason); child has no slot; redeliver_report is gone (README 3b R2) |
| from_parent.py | SourceFromParent | episode function | messages/read_from_parent.py (the mix-in is not carried; its methods are below) |
| from_parent.py | SourceFromParent.child_assignment_schema | machinery | the parent's view of this assignment (README 3b C3: the parent writes its own) |
| from_parent.py | SourceFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (PAGE_FORM, WINDOW_FORM, SELECTION_FORM) |
| from_parent.py | SourceFromParent._validate_page | episode function | UNPLACED: checks the page against the Store (artifact equals the source's artifact for the representation; refs in scope): a check of a commission (rule 1); read_from_parent has no records |
| from_parent.py | SourceFromParent._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (span and page agreement); the source_offset_out_of_bounds check reads the artifact (Store) and is UNPLACED as a check of a commission |
| from_parent.py | SourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (task and credit unit); the private-yield fill-in becomes settings; the proposed-annotation equality and within-parent-page checks are UNPLACED (checks of a commission / the parent's assignment) |
| goal.py | SourceGoal | episode function | goal.py |
| goal.py | SourceGoal.instructions | episode function | goal.py GOAL (also placed in the instructions by task.py instructions) |
| internal_summary.py | SourceInternalSummary | episode function | messages/internal_summary.py |
| internal_summary.py | SourceInternalSummary.initial_decision_context | episode function | UNPLACED: root-only reference_evidence_parent initial context (reference_parent_sources, annotation role at depth 1); not this episode's |
| internal_summary.py | SourceInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, source custody, own outcomes page, history meaning); structure context UNPLACED with the population route |
| internal_summary.py | SourceInternalSummary._owned_population_task_sources | episode function | UNPLACED: classifies owned population outputs by SQL on store.db / sqlite_master / runtime tables; population route not built |
| internal_summary.py | SourceInternalSummary._population_task_context | episode function | UNPLACED: population route not built; reads runtime_actions through store.db |
| presentation_selection.py | source_presentation_selection | machinery | order of prompt renderers over state frames (README 3a) |
| received_evidence.py | SourceReceivedEvidence | episode function | messages/final_to_parent.py (validate_report) and UNPLACED parts below |
| received_evidence.py | SourceReceivedEvidence.received_report_sources | machinery | the receiving side of a child return (README 3b R1); this episode has no child |
| received_evidence.py | SourceReceivedEvidence.received_report_facts | episode function | UNPLACED: structure population cells (route not built) |
| received_evidence.py | SourceReceivedEvidence._complete_requested_received_arrays | episode function | UNPLACED: completes structure fact arrays of the parent-written report contract (the parent writes none now, rule 5) |
| received_evidence.py | SourceReceivedEvidence.received_form_references | machinery | receipt of returned references (README 3b R3, system custody) |
| received_evidence.py | SourceReceivedEvidence.received_evidence_tokens | machinery | received-cell tokens for receipt bookkeeping (README 3b R3); structure cells not built |
| received_evidence.py | SourceReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (the LEADS/SCREENING answers are computed from one summary); the structure-cell validation is UNPLACED |
| report_delivery.py | SourceReportDelivery | episode function | messages/final_to_parent.py |
| report_delivery.py | SourceReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (the saved runtime_forms row, Record wrapper, release and pending handles are machinery) |
| source_contracts.py | _population_catalog | episode function | task.py POPULATE_DESCRIPTION / literature_structure_populate (raises: population route not built) |
| source_interpretation.py | SourceSourceInterpretation | episode function | task.py (reason tool and action) |
| source_interpretation.py | SourceSourceInterpretation.reasoning_action_schema | episode function | task.py reason_schema (source_lead for verified_source_leads) |
| source_interpretation.py | SourceSourceInterpretation.reasoning_has_task_content | episode function | task.py action (a reason answer with an empty commit is rejected unless it carries a source_lead) and empty_commit |
| source_interpretation.py | SourceSourceInterpretation.execute_reasoning | episode function | task.py reason tool (commit_reasoning and lead validation in one transaction) and validate_source_lead; library candidate: validate_source_lead |
| source_operations.py | SourceSourceOperations | episode function | task.py (access tools, catalog, admitted) |
| source_operations.py | SourceSourceOperations.catalog | episode function | task.py catalog, offered, selection_schema (descriptions and input schemas of the access tools) |
| source_operations.py | SourceSourceOperations.execute | episode function | task.py run_access_tool and the per-tool functions; reason; literature_structure_populate (raises) |
| source_operations.py | SourceSourceOperations._tool_arguments | episode function | task.py admitted |
| source_operations.py | SourceSourceOperations._materialize_text_arguments | episode function | UNPLACED: materializes text witnesses for the population route (not built) |
| source_references.py | SourceSourceReferences | episode function | task.py within_source; library records/received_records.py |
| source_references.py | SourceSourceReferences._require | episode function | already in library: episode_support/records/received_records.py read_record_in_scope |
| source_references.py | SourceSourceReferences._artifact | episode function | UNPLACED: only used by the dropped page-artifact check of the commission |
| source_references.py | SourceSourceReferences._within_source | episode function | task.py within_source (library candidate) |
| source_references.py | SourceSourceReferences.resolve | machinery | reference_in_context resolver of the old report validation; held check is records.holds (internal_summary report_source_held) |
| structural_sheet_operations.py | SourceStructuralSheetOperations | episode function | UNPLACED: structure population route (repository not in the library) |
| structural_sheet_operations.py | SourceStructuralSheetOperations.literature_structure_repository | episode function | UNPLACED: LiteratureStructureRepository(store, run_id) is not in the library (lost at 97308b94c, not placed) |
| structural_sheet_operations.py | SourceStructuralSheetOperations._population_routes | episode function | UNPLACED: population_route comes from the old shared a102_literature_bindings |
| task.py | SourceTask | episode function | task.py |
| task.py | SourceTask.next | episode function | task.py decide (context of the old decision; the loop, replay, restore and exchange are machinery) |
| task.py | SourceTask.apply_response | episode function | task.py action (selection validation, empty-commit rejection); replay, journal rows and delivery resolution are machinery |
| task.py | SourceTask.execute | episode function | task.py tools (reason, report, access tools); reasoning, tool, wait and redelivery dispatch is machinery |
| task_instructions.py | compose_instructions | episode function | task.py instructions |
| task_state.py | SourceTaskState | machinery | old loop state (README 3e) |
| task_state.py | SourceTaskState.__init__ | machinery | old loop state |
| task_state.py | SourceTaskState.bind_execution_context | machinery | old runner binding |
| task_state.py | SourceTaskState.record_execution_failure | machinery | record_execution_failure: a failed tool returns failure_outcome (task.py run_access_tool) |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.restore | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | SourceTaskState.checkpoint | machinery | checkpoint/restore |
| task_waiting.py | SourceTaskWaiting | machinery | wait/suspension machinery |
| task_waiting.py | SourceTaskWaiting.suspension_changed | machinery | wait/suspension machinery |
| to_parent.py | SourceToParent | episode function | messages/final_to_parent.py |
| to_parent.py | SourceToParent.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (SCREENING, LEADS, STRUCTURE as selectable fields) |
| to_parent.py | SourceToParent.facts | episode function | messages/final_to_parent.py final_to_parent; the answers are computed in messages/internal_summary.py through credit.py lead_dispositions / screening_answers |
| to_parent.py | SourceToParent.current_report_facts | machinery | returned {}: no content |
| to_parent.py | SourceToParent._rate_fact_sources | episode function | messages/final_to_parent.py STRUCTURE field (raises when selected: population route not built) |
| to_parent.py | SourceToParent._rate_facts | episode function | UNPLACED: structure rate cells read through LiteratureStructureRepository.fact_cells (not in the library) |
| to_parent.py | SourceToParent.validate_report | episode function | messages/final_to_parent.py validate_report (raises NotImplementedError validate_form_not_built:A102 where validate_form was called) |
| waiting.py | SourceWaiting | machinery | wait support |
| waiting.py | SourceWaiting.supports_wait | machinery | wait support (was False) |
| yield_estimator.py | SourceYield | episode function | yield_estimator.py |
| yield_estimator.py | SourceYield.continuation_task | episode function | messages/read_from_parent.py task_key (carried in the parent input as task_key) |
| yield_estimator.py | SourceYield.yield_controller | episode function | yield_estimator.py yield_controller (Accumulation for verified_source_leads; Completion with target credit_unit for a source answer; README 7b) |

Library candidates: `task.py validate_source_lead` (the library's `literature_task_credit.validate_lead` takes the old binding context), `task.py within_source`, `credit.py` private projector logic (`lead_dispositions`, `screening_answers`, `assessment_answers`). Already in library: `read_record_in_scope`, `outcome_page`, `yield_table`, `time_accounting`, `extend_context`, `rejection_feedback`, `replace_span`, `failure_outcome`, `strict_output_schema`/`decode_strict_output`, `ToolRegistry`, `ToolKnowledge`, `lead_schema`, `INSTRUCTIONS`/`REASONING_COMMIT_REQUIREMENT` of `instructions/structural_homology_evidence/runtime_prompt.py`, `FindingIdentity`, `FindingValidity`/`target_eligible`.
