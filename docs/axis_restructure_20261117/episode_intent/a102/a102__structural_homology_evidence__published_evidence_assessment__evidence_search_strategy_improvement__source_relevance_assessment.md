# a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/`
(28 Python files directly in the folder; no `grading/` or `scoring/` subfolder). The child folder
`source_evidence_examination` has its own page. Nothing from the old shared root was read; names imported from it are
listed only as names.

Old binding: class `LiteratureEpisode`, old role `literature_search`,
`binding_path = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'`,
`commissioning_parent = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'`,
binding version `literature_episode_binding_v1`, `entry_roles = ()`. Decision source: `SourceTask`; prompt renderer
`present_source_decision`.

## What this episode is for

It works through the sources a literature search returned and decides which of them merit examination for the
assigned question. Search results are only source-discovery information. In its own words (`goal.py`):

> Investigate which returned sources merit examination for the assigned question. Search results are
> source-discovery information. Examine original sources and their conditions before asserting biological evidence.
> A page child can investigate where and how to examine a selected source.

It then appends the paragraph that every literature episode in this family carries:

> This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms
> inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off
> search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action.
> Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors.
> Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can
> advance the investigation. Commit interpretations with the common reasoning action and update only the parent's
> declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific
> credit by themselves. The commissioned task's own yield settings guide continuation.

## Task and instructions

- One unit is one model-selected action. Permitted common actions (`episode.py`): `tool`, `reason`, `child`,
  `redeliver_report`. No `wait` (`waiting.py`: `supports_wait = False`).
- Instructions (`task_instructions.py`): the goal text above is appended to the default runner instructions (it does
  not replace them); then the reasoning-commit requirement (reasoning is permitted), tool knowledge when supplied, the
  launch instruction library when supplied, the `redeliver_report` paragraph for a finished child whose typed return
  was not delivered, and, under the exchange protocol, the `request_context` / `episode.history` guidance in place of
  the old history paragraph. The wait paragraphs are not reached because wait is not permitted.
- Reasoning (`source_interpretation.py`): when the commissioned `literature_task.kind` is `verified_source_leads`, the
  reasoning action carries a `source_lead` (schema from the literature task module). Executing it first checks the
  witness span is a permitted `source.read` (source, representation, start..end), then commits the reasoning and
  validates the lead in one transaction; the outcome carries `literature_source_lead`. A contract error returns an
  `invalid` outcome with feedback `{category: source_lead, code}` that still enters the iterator. An otherwise empty
  reasoning commit is rejected unless it carries this task content (`task.py`).
- Constructor settings (`episode.py`): `outcome_page_size` (positive int, default 8), `structure_population` (bool,
  default False), `reference_parent_sources` (unique non-empty refs, only with structure population),
  `contract_information_profile` (only the on-demand profile, only with structure population),
  `private_yield_binding` (bool), `yield_bindings` (only with a private yield binding; validated). A
  `reference_evidence(...)` constructor defaults `structure_population=True` and the on-demand contract-information
  profile for a caller-assigned reference-source investigation.

## What it reads from its parent's assignment

Assignment form (`from_parent.py`), version `search_assignment_v1`:

| Field | Meaning |
|---|---|
| `version` | const `search_assignment_v1` |
| `question_context_refs` | unique refs giving the question context (any namespace, must be in scope) |
| `search_result_refs` | unique refs of the returned search-result sources (namespace `source`, must be in scope) |
| `literature_task` | the commissioned literature task (schema from the literature task module); required when `private_yield_binding` |
| `proposed_annotation_ref` | the proposed annotation under test; required when `private_yield_binding`; must equal the parent's |
| requested components (`REQUESTED`) | the structure components the parent asks for (structure-population route) |

With a private yield binding, `prepare_assignment` looks up the task's key in this episode's `yield_bindings`, refuses a
task without a declaration, refuses a task that supplies a different `credit_unit` or `yield_settings`, and writes
`credit_unit` and `yield_settings` (`kind`, `cutoff`, `uncertainty_alpha`) from the declaration into the task.

## Children

One child role (`child_commissioning.py`): `literature_page`, the folder `source_evidence_examination`.

- Sent (`to_child_source_evidence_examination.py`): a child goal built from this episode's goal with the objective
  text and the child's report contract; a message with scope and initial report; optional report-contract declaration
  (validated against the expanded schema), job assignment, episode assignment (with launch instructions),
  `structural_homology_evidence`; knowledge inheritance from receipts. The child's own `from_parent` defines the
  content: a `page_assignment_v1` (one source, representation, artifact, question context, prior deliveries) plus the
  `literature_task`, `proposed_annotation_ref` and requested components.
- Taken back (`from_child_source_evidence_examination.py`, `received_evidence.py`): the child's typed form, the record
  references it carries, structure-population cells (stored with `receive_cells`, then the current sheet refs), and
  checks that a returned screening or leads answer equals the child's saved work and that returned structure cells
  cite permitted sheets and requested components.

## Decision state and what it shows the model

Own additions (`internal_summary.py`):

- `literature_assignment` (the validated assignment), `literature_source_custody` (per source: version, artifact,
  text, stdout, stderr, parent sources), `own_literature_outcomes` (first `outcome_page_size` of its own acquisition
  and read tool outcomes), and `literature_history_meaning` ("Own outcome metadata only. Read exact prior outcomes
  through episode.history. Source delivery does not establish scientific understanding.").
- With `structure_population`: `literature_experimental_work` (`literature_experimental_task_v1`, aspect
  `source_experimental_evidence`, axis A102), `literature_owned_population_sources` (its own completed population
  sheets, classified from metadata only), and `literature_selected_population_attempt` (its latest selected tool action
  if it was invalid/failed/error).
- Root-only initial context (`reference_evidence_parent`) when built with `reference_parent_sources`; not reached at
  this depth.

The rest of the model inputs come from the old loop (`task.py`, `decision_delivery.py`): goal, scope, working state,
visible refs, current credit and evidence vector, credit binding, pending work, last outcome and feedback, visual
evidence, report deliveries, controller state, tools, tool knowledge, requested form and current report update,
child options, launch instruction library, completed action reports.

## Tools it offers

`source_operations.py`, from `source_contracts.py`:

- Access tools: `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`,
  `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`,
  `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`,
  `execution.estimate` (only its xlsx branches).
- Acquisition tools (this episode only, not its page child): `public.literature.search`, `public.literature.read`,
  `public.literature.sequence_identity`, `public.ncbi.search` (database restricted to `pubmed`), `public.pmc.versions`,
  `public.pmc.files`, `public.pmc.asset`, and the experimental-database operations.
- `literature.structure.populate` when `structure_population` (with the contract argument transport under the
  on-demand profile); its text witness inputs are materialized from permitted source reads.
- No page boundary on arguments: this assignment has no `page`.

## How its credit is counted

`credit.py`: credit kind `scientific`; the credit view is the scientific credit service; the projector is
`LiteratureTaskCredit(self, context)`, i.e. credit in the commissioned task's `credit_unit`. Navigation, byte
coverage and repeated reading earn nothing by themselves (goal). Each returned action, including invalid/failed ones,
is saved with the credit view read after it (`task.py`, `task_state.py`). Nothing in these files bounds or rescales
credit.

## Continuation

`yield_estimator.py`: the continuation task key comes from the commissioned task. With `private_yield_binding`, the
controller is built from this episode's declaration for that key: `kind`, `cutoff`, `uncertainty_alpha` (and
`credit_unit`). Without a private yield binding it returns no controller of its own. The kind is not fixed in this
folder; it is per literature task in the declarations, so the carry-over has to map each declared `kind` onto one of
the three yield estimators (accumulation, bounded quality, completion with a target); `cutoff` is the estimator's
yield threshold, not a count or time limit.

## What it reports to its parent

`to_parent.py`, `report_delivery.py`: the form the parent's report contract declares, filled from facts plus the last
interpretation. Fact sources: structure rate facts (when `structure_population`), `SCREENING` answers (when the task's
`answer_kind` is `screening`), `LEADS` dispositions (when the task kind is `verified_source_leads`). Validation checks
the assignment, every form reference, and received cells. Without a report contract it returns credit, pending
handles and current report facts.

## How it differs from similar episodes

- Only literature episode in this subtree with acquisition tools (search/read/PMC/NCBI); its page child and the
  page's reading children get access tools only.
- Its assignment is a list of search results (`search_result_refs`), not a page; it has no source boundary on tool
  arguments.
- Its custody code reads `assignment.get('page')` then `assignment.get('source_refs', [])`; the assignment field is
  `search_result_refs`, so `literature_source_custody` is always empty here. The carry-over has to decide whether
  custody should list the search results.
- `_validate_page` is present (copied) but unused.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding record: version `literature_episode_binding_v1`, `binding_id` = this folder's path, configuration `outcome_page_size`, `structure_population`. | none |
| `child_commissioning.py` | 12 | Only child role: `literature_page` (folder `source_evidence_examination`). | `BindingContext.role` x2 |
| `configuration.py` | 13 | Contract-information profile applies when the role is a literature role (or the root annotation with `reference_parent_sources`). | `BindingContext.path`, `BindingContext.role` x2 |
| `credit.py` | 17 | Credit kind `scientific`; credit view from the scientific credit service; credit projector `LiteratureTaskCredit` (task-unit credit). | `BindingContext.role` x2, `literature_task_credit.LiteratureTaskCredit`, `services.scientific_credit` |
| `decision_delivery.py` | 346 | Old decision call path (journaled model calls, `request_context` exchange protocol, contract-information validation, launch-instruction library, child options, resource estimates, waiting support). Own intent: execution expectations captured under `literature_search`; otherwise runner machinery. | `episode_work_report.completed_action_reports`, `episode_work_report.requested_action_history`, `library.hpc_prompt.is_hpc_context`, `module:runtime`, `runtime._action_generation_schema` x2, `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information` x2, `runtime.composition_lookup_schema` x2, `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` x2, `runtime.DECISION_EXCHANGE_PROTOCOL` x5, `runtime._digest`, `runtime.Draft202012Validator`, `runtime.instructional_model_context` x4, `runtime.is_contract_information`, `runtime._json` x14, `runtime.json` x3, `runtime.lookup_attempts`, `runtime.Mapping` x4, `runtime.model_snapshot` x2, `runtime._object` x3, `runtime._plain` x2, `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` x2, `runtime.schema_failure_diagnostic` x2, `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` x5, `runtime.WorkflowError` x14, `runtime.yield_table`, `table:runtime_model_calls` x8, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.controller_binding`, `workflow.decision_exchanges` x4, `workflow.decision_protocol` x3, `workflow.episode_bindings`, `workflow.execute`, `workflow.execution_expectations`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.is_job_source` x3, `workflow.job_episodes` x2, `workflow.journal` x3, `workflow.launch_instructions` x2, `workflow.native_estimation_context`, `workflow.numerical_contracts`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.provider` x3, `workflow.receipts` x4, `workflow.resource_context`, `workflow.resource_estimator` x5, `workflow.run_id`, `workflow.services` x2, `workflow.shared_information_context`, `workflow.specialist`, `workflow.store` x2, `workflow.uses_received_record_context` x2, `workflow.validate_contract_information` x5, `workflow.waiting_support` |
| `decision_presentation.py` | 43 | Chooses a text prompt renderer from reconstructed state frames, keeps lookup results, falls back to JSON. No episode-specific content. | `module:providers`, `providers.apply_state_frame` x3, `providers.DECISION_CONTEXT_VERSION`, `providers.deepcopy`, `providers.json`, `providers.text_instructions` |
| `episode.py` | 89 | Class `LiteratureEpisode`; `binding_path`/`commissioning_parent`; `roles = ('literature_search',)`, no entry roles; constructor settings with validation (`outcome_page_size=8`, `structure_population=False`, `reference_parent_sources`, `contract_information_profile`, `private_yield_binding=False`, `yield_bindings`); `reference_evidence` constructor; permitted actions `tool`, `reason`, `child`, `redeliver_report`; child receiver/assembler for `literature_page`. | `BindingContext.role`, `literature_task_credit.validate_yield_bindings` |
| `from_child_source_evidence_examination.py` | 45 | Receiving the `literature_page` child's form: recorded admission references, child progress forms, form references (incl. structure cells), timing receipts, receipts. Own intent: what comes back is a typed form plus its references. | `delivery_counterpart.child_role_for_delivery`, `episode_return_records.EpisodeReturnRecords`, `module:runtime`, `runtime._json`, `runtime.json`, `runtime._references_in`, `runtime.WorkflowError`, `table:runtime_report_attempts` x2, `workflow.binding_context` x4, `workflow.episode_bindings`, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information`, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.receive_tool_attributions`, `workflow.run_id` x6, `workflow.specialist`, `workflow.store` x7 |
| `from_parent.py` | 72 | Assignment schema `search_assignment_v1` (`question_context_refs`, `search_result_refs`, `literature_task`, `proposed_annotation_ref`, requested components); fills task `credit_unit`/`yield_settings` from the private yield declaration; rejects a child whose proposed annotation differs from the parent's; every `*_refs` entry must be in scope (`source` namespace except question context). `_validate_page` is defined but not used here. | `BindingContext.assignment`, `literature_task_credit._task_key`, `literature_task_credit.task_schema` |
| `goal.py` | 8 | The goal text (quoted above). | `BindingContext.role` |
| `internal_summary.py` | 83 | Decision context: `literature_assignment`, source custody (version/artifact/text/stdout/stderr/parent sources), first `outcome_page_size` own outcomes of acquisition+read tools, `literature_history_meaning`; with `structure_population` also `literature_experimental_work` (aspect `source_experimental_evidence`) and population task context (own completed population sheets; latest failed population attempt). Root-only `reference_evidence_parent` initial context. | `BindingContext.assignment`, `BindingContext.episode_id` x4, `BindingContext.path`, `BindingContext.received_record_refs` x2, `BindingContext.role` x2, `BindingContext.run_id` x5, `BindingContext.scope` x4, `literature_task_selection.population_task_metadata_specs`, `services.own_outcomes`, `table:runtime_actions` x2, `workflow.run_id` x2, `workflow.store` x2 |
| `presentation_selection.py` | 30 | Predicate order of prompt renderers (hpc, published scientific, monitor, API launch, selected execution, receiver). No episode-specific content. | `library.hpc_prompt.is_hpc_context`, `library.hpc_prompt.render_hpc_prompt`, `library.monitor_prompt.is_monitor_context`, `library.monitor_prompt.render_monitor_prompt`, `receiver_prompt.render_receiver_prompt`, `structural_homology_evidence_prompt.is_selected_execution_context`, `structural_homology_evidence_prompt.render_selected_execution_prompt`, `module:providers`, `providers.is_api_launch_context` x2, `providers.is_published_scientific_context` x2, `providers._ordinary_runtime_receiver_context`, `providers.render_api_launch_prompt`, `providers.render_structural_homology_evidence_prompt` |
| `received_evidence.py` | 73 | Receiving structure-population cells from children, current sheet refs, received evidence tokens; validation that a returned screening/leads answer equals the child's saved work and that returned structure cells cite permitted sheets and requested components. | `BindingContext.assignment` x2, `BindingContext.episode_id`, `BindingContext.received_record_refs`, `BindingContext.request`, `BindingContext.role` x2, `BindingContext.run_id`, `literature_sheet_updates.current_sheet_refs`, `literature_task_credit.lead_dispositions`, `literature_task_credit.LEADS`, `literature_task_credit.screening_answers`, `literature_task_credit.SCREENING`, `method_loop.durable.content_digest`, `services.record_selection`, `workflow.store` x2 |
| `report_delivery.py` | 25 | `finish`: without a report contract returns credit + pending handles + current report facts; otherwise builds the form from facts and the interpretation, saved once. | `library.private_policy_call.invoke`, `library.report_fact_assembly.facts`, `module:runtime`, `runtime.form_with_facts`, `runtime._json` x2, `runtime.json`, `runtime.Record` x2, `table:runtime_forms` x2, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.facts`, `workflow.journal` x2, `workflow.pending_handles`, `workflow.release` x2, `workflow.source_credit_view` |
| `source_contracts.py` | 38 | Literature constants: `VERSION`, `ROLES` (7 literature roles), `_WINDOW`/`_TABLE`/`_PAGE` schemas, tool lists `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`, population catalog (`literature.structure.populate`). | `communication.plain`, `communication.ReportBoundaryError`, `communication.validate_form`, `composition_information.CONTRACT_INFORMATION_PROFILE`, `domain.ContractError`, `domain.identity`, `domain.obj`, `domain.REF`, `domain.source_location_inputs`, `domain.validate_schema`, `episode_bindings.reference_in_context`, `experimental_database_acquisition.OPERATIONS` |
| `source_interpretation.py` | 43 | For a `verified_source_leads` task the reasoning action carries a `source_lead`; executing it re-checks the witness read is permitted, commits reasoning and validates the lead in one transaction; invalid leads return an `invalid` outcome. | `BindingContext.assignment`, `BindingContext.episode_id`, `BindingContext.run_id`, `BindingContext.scope`, `literature_contract_error.ExperimentalContractError`, `literature_task_credit.commissioned_task`, `literature_task_credit.lead_schema` x2, `literature_task_credit.validate_lead`, `workflow.store` |
| `source_operations.py` | 94 | Tool catalog = access tools + acquisition tools (literature search/read, NCBI restricted to `pubmed`, PMC, experimental databases), `execution.estimate` only for xlsx tools, plus `literature.structure.populate` when `structure_population`; execute with record permission for locate/scan/experimental tools; no page boundary because the assignment has no `page`. | `BindingContext.assignment`, `BindingContext.received_record_refs`, `BindingContext.role` x2, `BindingContext.scope` x6, `composition_information.CONTRACT_ARGUMENT_TRANSPORT`, `library.literature_assay_inputs.materialize_text_witness_inputs`, `literature_contract_error.ExperimentalContractError`, `services.execute_tool`, `services.tool_catalog` |
| `source_references.py` | 35 | Reference checks: `_require` (in scope, namespace), `_artifact` (representation to artifact), `_within_source` (walks `parent_source_refs`), `resolve`. | `BindingContext.role`, `services.read_record`, `services.reference_in_scope` |
| `structural_sheet_operations.py` | 17 | Literature structure repository (source-model geometry / local-fit components) and the single population route when `structure_population`. | `literature_structure_storage.LiteratureStructureRepository`, `workflow.run_id`, `workflow.store` |
| `task.py` | 269 | Old iterative loop (`next`, `apply_response`, `execute`): replay, model inputs, reasoning/tool/wait execution, report update admission, credit after each observed outcome. Own intent: report grain `literature_search`; empty reasoning commit rejected unless it carries task content (a source lead); report lifecycle sentence. | `episode_source_failure.record_source_failure`, `library.action_contracts.action_schema`, `library.private_policy_call.invoke`, `read_mapping.parameter_schema_failure`, `module:runtime`, `runtime.AcquisitionError` x2, `runtime.ActionFailure`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator` x3, `runtime.EventTargetError` x2, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.inspect`, `runtime._json` x5, `runtime.json` x10, `runtime.Mapping` x6, `runtime.nullcontext` x5, `runtime.observes_action_outcome`, `runtime._plain` x2, `runtime._references_in`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery` x2, `runtime.schema_failure_diagnostic`, `runtime.SourceEnd` x2, `runtime.sqlite3` x2, `runtime.subprocess` x2, `runtime.validate_form`, `runtime.ValidationError` x3, `runtime._wait_target_feedback` x2, `runtime.WorkflowError` x2, `SourceView.child_reports` x2, `SourceView.controller_state`, `SourceView.model_inputs`, `SourceView.units_consumed` x4, `table:runtime_actions` x10, `table:runtime_episodes`, `table:runtime_model_calls` x2, `workflow.action_schema`, `workflow.annotation_context`, `workflow.automatic_score_updates`, `workflow.binding_context` x3, `workflow.catalog`, `workflow.completed_unit` x3, `workflow.completions` x3, `workflow.controller_binding`, `workflow.controller_value` x2, `workflow.decision_exchanges` x3, `workflow.delivery_resolution_inputs`, `workflow.delivery_status`, `workflow.execute`, `workflow.execution_binding` x7, `workflow.extra_report_sources`, `workflow.inprocess_replay` x4, `workflow.is_scientific_source`, `workflow.job_episode_options`, `workflow.journal` x10, `workflow.knowledge`, `workflow.last_observed_credit`, `workflow.local_outcome_preview`, `workflow.next_return`, `workflow.pending_work` x2, `workflow.perform_selected_wait`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receipt_projection`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` x4, `workflow.selected` x3, `workflow.source_credit_binding`, `workflow.source_credit_view` x2, `workflow.specialist` x3, `workflow.store` x12, `workflow.tools`, `workflow.validate_report`, `workflow.working_state` |
| `task_instructions.py` | 26 | Instruction composition: goal text, reasoning-commit requirement, tool knowledge, launch library, `redeliver_report` paragraph, wait paragraphs (only if wait permitted; not here), `request_context` history guidance. | `module:runtime_prompt`, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`, `runtime_prompt.INSTRUCTIONS` x4, `runtime_prompt.REASONING_COMMIT_REQUIREMENT`, `workflow.binding_context`, `workflow.decision_protocol`, `workflow.is_job_source`, `workflow.job_episodes`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.permits_common_action` x3, `workflow.specialist` |
| `task_state.py` | 108 | Source state: report values, feedback, restore/checkpoint, recording an execution failure as a failed outcome that still enters the iterator with credit. Runner machinery. | `episode_source_failure.record_source_failure`, `module:runtime`, `runtime.ActionLeaf`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.interpretation_schema`, `runtime._json` x2, `runtime.json` x4, `runtime._object`, `runtime._plain`, `runtime.Record`, `table:runtime_actions` x5, `workflow.archive`, `workflow.completions` x4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding` x4, `workflow.grains`, `workflow.inprocess_replay` x7, `workflow.journal` x5, `workflow.progress_provider` x2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store` x2 |
| `task_waiting.py` | 9 | Passes a suspension condition to the execution backend. Runner machinery. | `workflow.execution_backend`, `workflow.execution_handle` x2 |
| `to_child_source_evidence_examination.py` | 29 | Building the `literature_page` child request: child goal from parent, scope, initial report, report-contract declaration, assignments, knowledge inheritance. Runner machinery. | `module:runtime`, `runtime.ContractInformationError`, `runtime.EpisodeGoal` x2, `runtime.EpisodeRequest`, `runtime.Episode` x2, `runtime._plain` x3, `runtime.Record`, `runtime.validate_saved_fact_form`, `workflow.context` x2, `workflow.grains` x2, `workflow.inprocess_completion_order` x2, `workflow.launch_instructions`, `workflow.receipts` x2 |
| `to_parent.py` | 41 | Report fact sources: structure rate facts (if `structure_population`), `SCREENING` answers, `LEADS` dispositions; `facts` fills them for the task kind; `validate_report` checks assignment, form refs and received cells. | `BindingContext.assignment` x4, `BindingContext.received_record_refs`, `BindingContext.role` x2, `BindingContext.scope`, `literature_task_credit.lead_dispositions`, `literature_task_credit.lead_return_schema`, `literature_task_credit.LEADS` x2, `literature_task_credit.screening_answers`, `literature_task_credit.screening_schema`, `literature_task_credit.SCREENING` x2, `services.read_record`, `workflow.store` x2 |
| `waiting.py` | 8 | `supports_wait = False`. | none |
| `yield_estimator.py` | 22 | `continuation_task` key; `yield_controller` built from the commissioned task's private yield declaration (`kind`, `cutoff`, `uncertainty_alpha`); none without `private_yield_binding`. | `BindingContext.role` x2, `literature_task_credit.continuation_task` x2, `literature_task_credit._private_yield_controller` |

Old-runner names are counted per occurrence: `workflow.<member>` covers `self.workflow`, `source.workflow`, the `workflow` parameter and `self.services.workflow`; `BindingContext.<field>` covers `context.`/`parent.` binding-context fields; `SourceView.<member>` the old loop's view; `runtime.`/`providers.`/`runtime_prompt.` the old per-axis modules; `table:` old journal/receipt tables; other names are imports from the old shared root (`root/a102/...`). Row-level detail: `runs/carry_over/calls/a102_07.tsv`.

## Old-runner names (totals for this episode)

| Kind | Distinct names | Uses |
|---|---|---|
| `BindingContext` | 8 | 62 |
| `import:communication` | 3 | 3 |
| `import:composition_information` | 2 | 2 |
| `import:delivery_counterpart` | 1 | 1 |
| `import:domain` | 6 | 6 |
| `import:episode_bindings` | 1 | 1 |
| `import:episode_return_records` | 1 | 1 |
| `import:episode_source_failure` | 1 | 2 |
| `import:episode_work_report` | 2 | 2 |
| `import:experimental_database_acquisition` | 1 | 1 |
| `import:library` | 8 | 10 |
| `import:literature_contract_error` | 1 | 2 |
| `import:literature_sheet_updates` | 1 | 1 |
| `import:literature_structure_storage` | 1 | 1 |
| `import:literature_task_credit` | 15 | 23 |
| `import:literature_task_selection` | 1 | 1 |
| `import:method_loop` | 1 | 1 |
| `import:read_mapping` | 1 | 1 |
| `import:receiver_prompt` | 1 | 1 |
| `import:structural_homology_evidence_prompt` | 2 | 2 |
| `module` | 3 | 9 |
| `providers` | 10 | 14 |
| `runtime` | 56 | 178 |
| `runtime_prompt` | 3 | 6 |
| `services` | 7 | 8 |
| `SourceView` | 4 | 8 |
| `table` | 5 | 32 |
| `workflow` | 79 | 255 |

## Carried over

One row per old function, class or method of this episode folder at `97308b94c` (`runs/carry_over/functions/a102__structural_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment.tsv`). Kind is the old kind; the next column says whether the row is old-runner machinery (not carried, with its reason) or an episode function (with its new place). Functions of this folder that are not in the library already stay in the episode file that uses them (library candidates): `validate_source_lead`, `examined_spans`, `checked_page`, `source_custody` and the credit functions. Not placed (their route is not built) are listed in `docs/axis_restructure_20261117/carry_over_blocked/a102__structural_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment.md`.

| old file | kind | name | classification | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | class | SourceBindingRecord | machinery | binding record: the binding's own as_record() (README 3e); the settings are journaled by the system |
| binding_record.py | method | SourceBindingRecord.as_record | machinery | binding record: the binding's own as_record() (README 3e); the settings are journaled by the system |
| child_commissioning.py | class | SourceChildCommissioning | episode function | task.py CHILD_SLOTS = {literature_page: .../source_evidence_examination} |
| child_commissioning.py | method | SourceChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS (the one child role literature_page, old allowed_children/child_roles) |
| child_commissioning.py | method | SourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS (the one child role literature_page, old allowed_children/child_roles) |
| configuration.py | class | SourceConfiguration | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| configuration.py | method | SourceConfiguration.contract_information_configuration | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| configuration.py | method | SourceConfiguration.contract_information_profile | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| credit.py | class | SourceCredit | episode function | credit.py (credit) and messages/internal_summary.py (credit_binding) |
| credit.py | method | SourceCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | SourceCredit.credit_view | episode function | credit.py credit(summary, records) (the number); the other fields of the old view are computed in messages/internal_summary.py |
| credit.py | method | SourceCredit.credit_projector | episode function | credit.py: private re-expression of LiteratureTaskCredit (credit, answers, lead_dispositions, screening_answers, assessment_answers, current_assessments, credit_binding) |
| decision_delivery.py | class | SourceDecisionDelivery | machinery | old decision call path (README 3a) |
| decision_delivery.py | method | SourceDecisionDelivery.call | episode function | task.py decide(summary, feedback, ctx) returns the ModelRequest (the model call itself and its journaling are the system's); the context fields it showed (goal, scope, assignment, custody, own outcomes, child reports, credit_binding, report update, tools, time, action_yields, tool_knowledge) |
| decision_delivery.py | method | SourceDecisionDelivery.instructions | episode function | task.py instructions(*, knowledge) |
| decision_delivery.py | method | SourceDecisionDelivery.conversation_key | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.interpretation_context | machinery | decision-exchange interpretation context (README 3a): no exchange |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_schema | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_response | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.validate_contract_exchange_request | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.validate_contract_exchange_history | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_decision | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.complete_decision | episode function | task.py decide(summary, feedback, ctx) returns the ModelRequest (the model call itself and its journaling are the system's); the context fields it showed (goal, scope, assignment, custody, own outcomes, child reports, credit_binding, report update, tools, time, action_yields, tool_knowledge) |
| decision_presentation.py | function | present_source_decision | machinery | state-frame prompt renderer selection of the old provider (README 3a: every ModelRequest carries the full context; the episode puts its context into ModelRequest.context) |
| episode.py | class | LiteratureEpisode | episode function | episode.py SourceRelevanceAssessment(EpisodeBinding) |
| episode.py | method | LiteratureEpisode.__init__ | episode function | settings of the run (ctx.settings: structure_population, tool_registry, knowledge_library_directory); outcome_page_size is the constant OUTCOME_PAGE_SIZE in messages/internal_summary.py; private_yield_binding/yield_bindings are replaced by the commissioned task's credit_unit and the settings cost/parameters (yield_estimator.py); reference_parent_sources and contract_information_profile are root-only and not built |
| episode.py | method | LiteratureEpisode.reference_evidence | episode function | not placed: root-only constructor for a caller-assigned reference-source investigation (requires structure_population, not built); reported in unplaced_old_functions |
| episode.py | method | LiteratureEpisode._role | machinery | one binding per role: the role check is gone (README 3a BindingContext.role) |
| episode.py | method | LiteratureEpisode.permitted_common_actions | episode function | task.py offered/selection_schema: tool, reason, child; redeliver_report is deleted (README 3b R2) |
| episode.py | method | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child (slot literature_page) |
| episode.py | method | LiteratureEpisode.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child (slot literature_page) |
| from_child_source_evidence_examination.py | function | receive_report | episode function | messages/read_from_child.py read_from_child; recorded admission, progress receipts, timing receipts and receipt bookkeeping are the system's (README 3b R1, R3, R5) |
| from_parent.py | class | SourceFromParent | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent, task_key) |
| from_parent.py | method | SourceFromParent.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (search_assignment_v1; the child's own form states what it takes) |
| from_parent.py | method | SourceFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (search_assignment_v1; the child's own form states what it takes) |
| from_parent.py | method | SourceFromParent._validate_page | episode function | task.py checked_page (applied to the model's answer in action, as a rejection; the old method was defined but unused here) |
| from_parent.py | method | SourceFromParent._validate_assignment | machinery | commission check: the scope/namespace tests of the assignment are the system's custody over record_refs fields (rule 1); the schema check is the form's admission; the finite task and kind checks are in messages/read_from_parent.py |
| from_parent.py | method | SourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (task checks, credit_unit); the private yield declaration lookup is replaced by the credit_unit in the task and the settings (yield_estimator.py); the proposed-annotation equality check of a commission is not carried (rule 1) |
| goal.py | class | SourceGoal | episode function | goal.py GOAL, UNIT, RESULT, BINDING_PATH |
| goal.py | method | SourceGoal.instructions | episode function | goal.py GOAL (the instruction text); the role check is gone |
| internal_summary.py | class | SourceInternalSummary | episode function | messages/internal_summary.py |
| internal_summary.py | method | SourceInternalSummary.initial_decision_context | episode function | not placed: root-only reference_evidence_parent context (requires structure_population and reference_parent_sources; not built); reported in unplaced_old_functions |
| internal_summary.py | method | SourceInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning) with source_custody, held_sources |
| internal_summary.py | method | SourceInternalSummary._owned_population_task_sources | episode function | not placed: structure population context (owned population sheets by raw SQL on runtime tables and sqlite_master; the route is not built; decide raises when structure_population is set); reported in unplaced_old_functions |
| internal_summary.py | method | SourceInternalSummary._population_task_context | episode function | not placed: structure population context (owned population sheets by raw SQL on runtime tables and sqlite_master; the route is not built; decide raises when structure_population is set); reported in unplaced_old_functions |
| presentation_selection.py | function | source_presentation_selection | machinery | predicate order of the old per-context prompt renderers (README 3a: the episode renders its own context in decide) |
| received_evidence.py | class | SourceReceivedEvidence | machinery | receiving a child report (README 3b R1, R3) |
| received_evidence.py | method | SourceReceivedEvidence.received_report_sources | machinery | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | SourceReceivedEvidence.received_report_facts | machinery | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | SourceReceivedEvidence._complete_requested_received_arrays | machinery | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | SourceReceivedEvidence.received_form_references | machinery | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | SourceReceivedEvidence.received_evidence_tokens | machinery | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | SourceReceivedEvidence.validate_received_report | machinery | check of a child's return: the system admits the result against the child's own form (README 3b R1, D2); the child computes both answer and facts from one summary |
| report_delivery.py | class | SourceReportDelivery | episode function | messages/final_to_parent.py final_to_parent (facts and report); saving the form, release and pending_handles are deleted (README 3b D1, D3) |
| report_delivery.py | method | SourceReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (facts and report); saving the form, release and pending_handles are deleted (README 3b D1, D3) |
| source_contracts.py | function | _population_catalog | episode function | task.py (VERSION/ROLES dropped; _WINDOW/_PAGE as PAGE and WINDOW schemas; access and acquisition tool lists as ACCESS_NAMES, ACQUISITION_NAMES, HELD_SOURCE_TOOLS); the population catalog is the not-built literature_structure_populate tool |
| source_interpretation.py | class | SourceSourceInterpretation | episode function | task.py reason (tool), reason_schema, empty_commit |
| source_interpretation.py | method | SourceSourceInterpretation.reasoning_action_schema | episode function | task.py reason_schema |
| source_interpretation.py | method | SourceSourceInterpretation.reasoning_has_task_content | episode function | task.py action (a reason answer without a source_lead and with an empty commit is rejected, empty_commit) |
| source_interpretation.py | method | SourceSourceInterpretation.execute_reasoning | episode function | task.py reason (tool): witness read check, commit_reasoning and validate_source_lead in one transaction; invalid outcome returned |
| source_operations.py | class | SourceSourceOperations | episode function | task.py TOOLS (access and acquisition tools) and run_tool |
| source_operations.py | method | SourceSourceOperations.catalog | episode function | task.py catalog, offered, DESCRIPTIONS, INPUT_SCHEMAS (ncbi restricted to pubmed; execution.estimate only its xlsx branches) |
| source_operations.py | method | SourceSourceOperations.execute | episode function | task.py run_tool (library ToolRegistry.execute_async with ctx.store); literature.structure.populate raises (not built) |
| source_operations.py | method | SourceSourceOperations._tool_arguments | episode function | task.py run_tool schema check (no page, so no source boundary); the catalog-membership check is the offered schema |
| source_operations.py | method | SourceSourceOperations._materialize_text_arguments | episode function | not placed: text-witness materialization of literature.structure.populate arguments (needs LiteratureStructureRepository, not in the library); reported in unplaced_old_functions |
| source_references.py | class | SourceSourceReferences | episode function | README 3b D2: custody (records.holds) and task.py checked_page |
| source_references.py | method | SourceSourceReferences._require | machinery | reference_in_scope / resolver over the old services: custody (records.holds, README 3b D2) replaces it |
| source_references.py | method | SourceSourceReferences._artifact | episode function | task.py artifact_of |
| source_references.py | method | SourceSourceReferences._within_source | episode function | not carried: used only to bound reads to a page source; this assignment has no page (the page child carries its own) |
| source_references.py | method | SourceSourceReferences.resolve | machinery | reference_in_scope / resolver over the old services: custody (records.holds, README 3b D2) replaces it |
| structural_sheet_operations.py | class | SourceStructuralSheetOperations | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| structural_sheet_operations.py | method | SourceStructuralSheetOperations.literature_structure_repository | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| structural_sheet_operations.py | method | SourceStructuralSheetOperations._population_routes | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| task.py | class | SourceTask | episode function | task.py (decide, action, tools) |
| task.py | method | SourceTask.next | episode function | task.py decide (the loop, replay, model call, exchange and journaling are the system's) |
| task.py | method | SourceTask.apply_response | episode function | task.py action (decode, schema check, empty-commit rejection, page and report-reference checks; Rejected(feedback)); the report update admission is the report tool; the wait/redelivery/job branches are not carried |
| task.py | method | SourceTask.execute | episode function | task.py TOOLS (tool calls), CHILD_SLOTS (child commission), reason, report; wait, redeliver_report and the credit-after-outcome bookkeeping are deleted |
| task_instructions.py | function | compose_instructions | episode function | task.py instructions(*, knowledge); the pending-delivery, wait, native-event and exchange paragraphs are not carried |
| task_state.py | class | SourceTaskState | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.__init__ | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.bind_execution_context | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.record_execution_failure | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.restore_checkpoint | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.restore | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.record_effect | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.checkpoint | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_waiting.py | class | SourceTaskWaiting | machinery | suspension machinery (README 3b: wait is deleted) |
| task_waiting.py | method | SourceTaskWaiting.suspension_changed | machinery | suspension machinery (README 3b: wait is deleted) |
| to_child_source_evidence_examination.py | function | assemble_request | episode function | messages/msg_to_child.py msg_to_child (objective, page, assignment, selection); child goal/EpisodeRequest/knowledge inheritance are the system's (README 3b C3, C4) |
| to_parent.py | class | SourceToParent | episode function | messages/final_to_parent.py (RETURN_FORM, final_to_parent) |
| to_parent.py | method | SourceToParent.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM selectable fields SCREENING, LEADS (and STRUCTURE, not built) |
| to_parent.py | method | SourceToParent.facts | episode function | messages/final_to_parent.py final_to_parent (screening and leads from the summary; structure raises) |
| to_parent.py | method | SourceToParent.current_report_facts | episode function | messages/final_to_parent.py final_to_parent (returned no extra facts) |
| to_parent.py | method | SourceToParent._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM selectable fields SCREENING, LEADS (and STRUCTURE, not built) |
| to_parent.py | method | SourceToParent._rate_facts | episode function | not placed: structure rate facts of the population route (LiteratureStructureRepository.fact_cells; not built); STRUCTURE selection raises; reported in unplaced_old_functions |
| to_parent.py | method | SourceToParent.validate_report | episode function | messages/final_to_parent.py validate_report (held references; then raises NotImplementedError validate_form_not_built:A102 where the old body called validate_form) |
| waiting.py | class | SourceWaiting | machinery | supports_wait = False: wait is deleted (README 3b) |
| waiting.py | method | SourceWaiting.supports_wait | machinery | supports_wait = False: wait is deleted (README 3b) |
| yield_estimator.py | class | SourceYield | episode function | yield_estimator.py |
| yield_estimator.py | method | SourceYield.continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"]) |
| yield_estimator.py | method | SourceYield.yield_controller | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion with target credit_unit for a source answer; README 7b) |
