# table_evidence_extraction (A102)

Episode path: `root/a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction`.
Source: the episode's own files at `97308b94c` (27 Python files, about 1,650 lines; it has no `grading/` or `scoring/` subfolder). Old role name: `literature_table`. Old class: `LiteratureEpisode`.

## What it is for (goal, in its own words)

> Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.

The goal text then adds the literature investigation guidance. The investigation is iterative. There is no child order, reading quota or requirement to read the whole document. A supplied reading selector is context and is never executed automatically. The episode keeps the source's subject, conditions, representation, version and UTF-8 byte anchors. It separates what the source claims from whether that claim applies to the fixed target. Negative findings and qualifications count as progress. It commits interpretations with the common `reason` action and updates only the parent's declared typed form. Navigation, byte coverage and repeated reading earn no credit by themselves. "The commissioned task's own yield settings guide continuation."

## Task and instructions

- `task_instructions.compose_instructions` builds the instructions in this order: the old default runtime `INSTRUCTIONS`; this binding's goal text (appended, because the binding does not set `replaces_default_instructions`); `REASONING_COMMIT_REQUIREMENT`; tool-knowledge instructions; launch-instruction-library instructions; the text for repairing a pending child delivery with `redeliver_report`; the wait text (only if `wait` is permitted, which it is not here); the native-event text; and, under the exchange protocol, replacement history guidance that says to use `request_context` and `episode.history`. The file is identical to the resource episodes' `instructions.py`.
- `task.py`, `decision_delivery.py` and `task_state.py` hold the iteration source in the old runner's form. That code covers replay, the model call, response admission, execution, credit and checkpoints. Its intent is the generic one: a returned invalid or failed action still enters the iterator (`record_execution_failure` saves a failed outcome together with its credit and controller value), and a rejected malformed action creates no unit.
- Permitted common actions are `tool`, `reason`, `child` and `redeliver_report`. There is no `wait`, and `waiting.supports_wait` is False.

## What it reads from its parent's assignment

The assignment schema is `reading_assignment_v1` (`from_parent.py`):
- `page`: a `page_assignment_v1` with `source_ref`, `representation` (text/original/stdout/stderr), `artifact_ref`, `question_context_refs` and `prior_delivery_refs`.
- `selection`: either a table selector (`source_ref`, `sheet_key`, `offset`, `limit`, `header_row`, and `where` with column/match/value/case_sensitive) or a byte window (`source_ref`, `representation`, `offset`, `limit`).
- `literature_task` (from the old `task_schema()`) and `proposed_annotation_ref`. Both are required under `private_yield_binding`. In that case the parent does not supply `credit_unit`: `prepare_assignment` fills `credit_unit` and `yield_settings` {kind, cutoff, uncertainty_alpha} from this episode's own `yield_bindings` for the task key. A task that disagrees with the binding raises `literature_task_supplied_yield_binding_mismatch`.
- The A102 requested structure components field (`REQUESTED`, from the old `a102_literature_bindings`).

`prepare_assignment` and `_validate_assignment` also check custody:
- the artifact must match the source's representation;
- question and prior-delivery references must be in scope;
- a window offset must not be past the artifact size;
- the proposed annotation must equal the parent's;
- when the parent is a `literature_page`, the parent's page assignment is checked with this episode's own `commissioning_page_assignment.py`, and the reading must stay within the parent's source (`_within_source` walks `parent_source_refs`).

## Children

None. `child_roles` and `allowed_children` return `()`, so the episode sends no child requests and receives no child returns.

## Decision state and what it shows the model

The generic state is built inline in `task.py`. It contains: goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector, investigation_progress (with receipt projection), credit_binding, time_accounting, pending_work, last_local_outcome and feedback, visual_evidence (from the last `image.view`), report_deliveries, controller state and binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose and requested_form, current_report_update and its basis, and the report_lifecycle text.

**Unlike the resource episodes**, when `is_scientific_source` holds, the state also carries annotation context. Under annotation-axis credit that is the proposed annotations and comparisons; otherwise it is `annotation_context`.

The binding's own context (`internal_summary.decision_context`) adds:
- `literature_assignment`;
- `literature_source_custody` (version, artifact, text, stdout, stderr and parent references);
- `own_literature_outcomes` (a page of this episode's acquisition and read tool outcomes, `outcome_page_size`, default 8);
- `literature_history_meaning`;
- with `structure_population`: `literature_experimental_work` {aspect `source_experimental_evidence`, axis A102} and the population task context. That context lists the population sources this episode owns, found by metadata-only SQL, and the latest failed population attempt.

The fresh decision inputs (`decision_delivery.call`) add:
- resource_context and shared_information_context;
- the launch instruction library and the selected launch instructions;
- child_options;
- the binding's initial context (a field conflict raises);
- completed_action_reports, and requested_action_history for HPC contexts;
- execution_expectations for `literature_table`;
- resource_tool_estimates and native expectations;
- waiting_support;
- contract_information_profile.

Presentation: the episode has its own `decision_prompt_renderer = present_source_decision` (`decision_presentation.py` and `presentation_selection.py`). It renders a text prompt from reconstructed state frames and picks the renderer: HPC, published scientific (structural evidence), API launch, selected execution, monitor, or receiver. When no text task applies, it sends the context as JSON. The provider is called through `complete_with_presentation` with that renderer. The resource episodes do not do this.

## Tools offered

`source_operations.catalog` offers only the `_ACCESS_TOOLS` found in the shared catalogue:
- `state.query`;
- `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`;
- `image.view`;
- `source.archive.members`, `source.archive.extract`;
- `source.xlsx.sheets`, `source.xlsx.rows`;
- `source.pdf.info`, `source.pdf.text`, `source.pdf.page`;
- `execution.estimate`, restricted to the xlsx sheets/rows branches.

`public.ncbi.search` would be narrowed to pubmed, but it is not in the access set. With `structure_population` the catalogue adds `literature.structure.populate`, carrying the contract argument transport when a contract profile is set. All input schemas go through `source_location_inputs`.

Execution rules:
- Every tool call must stay within the assigned page source.
- `source.xlsx.rows` must use the assigned `sheet_key`.
- References given to `populate` must lie within the source.
- `populate` runs through `LiteratureStructureRepository`, with text witness inputs materialized after a `source.read` permission check.
- The locate, sequence and experimental tools may only use received references.
- An invalid argument returns an `invalid` outcome with feedback.

Reasoning extension (`source_interpretation.py`): for `verified_source_leads` tasks, `reason` may carry a `source_lead` with a witness window. The episode reads that window, commits the reasoning and validates the lead.

## Credit

- The credit kind is `scientific`, and the view is `services.scientific_credit(context, receiver_selection)`.
- The projector is `LiteratureTaskCredit(self, context)` from the old `literature_task_credit` module.
- Navigation and reading earn nothing by themselves.
- Nothing is bounded or rescaled in these files.

## Continuation

`yield_estimator.py`:
- The continuation task key comes from the commissioned `literature_task` (`continuation_task`).
- With `private_yield_binding=True`, the controller is `_private_yield_controller(context, initial_credit, epoch, declaration)`, where the declaration is this episode's own `yield_bindings[key]` = {kind, cutoff, uncertainty_alpha, credit_unit}. A missing declaration raises `literature_yield_binding_missing_for_task`.
- Without a private binding, `yield_controller` returns None, so the parent's or default controller is used.
- The `kind` value chooses the estimator. In the new layout that must map to one of the three `yield_control/` estimators. The old declaration format lives in the old `literature_task_credit` and is not in this tree.

## What it reports to its parent

`to_parent.py` and `received_evidence.py`:
- Fact sources: the A102 structure population fact source (when `structure_population` is on), screening answers (`SCREENING`) and verified source leads (`LEADS`).
- Facts: screening answers when `answer_kind == 'screening'`; lead dispositions for `verified_source_leads`; and, under structure population, rate facts per provider from the received source records, limited to the requested components.
- `validate_report` re-validates the assignment and form references, and requires saved screening and lead answers to equal the saved work (`literature_task_answer_differs_from_saved`). Structure rows must come from received or selected sheets and from requested components.
- `report_delivery.finish`: with a report contract, the episode fills the parent's typed form once from its interpretations and facts and saves it. Without one, it returns credit, pending handles and the current report facts.

## Differences from similar episodes

- Compared with the resource episodes in this batch: scientific rather than operational credit; its own private yield binding; no `wait`; its own text prompt renderer; annotation context in the decision state; literature custody checks.
- Its sibling literature roles share the `ROLES` list (`literature`, `literature_strategy`, `literature_search`, `literature_page`, `literature_table`, `literature_ordered`, `literature_targeted`). This episode alone requires the `sheet_key` match on `source.xlsx.rows`, and it authenticates a `literature_page` parent through its own `commissioning_page_assignment.py`.

## File by file

| old file | lines | this episode's own intent | old-runner names used (×uses) |
|---|---|---|---|
| binding_record.py | 8 | binding record literature_episode_binding_v1, binding_id = this episode's path, configuration outcome_page_size + structure_population | none |
| child_commissioning.py | 12 | no children: allowed_children / child_roles return () (after role check) | none |
| commissioning_page_assignment.py | 28 | authenticates a literature_page parent's page_assignment_v1 with this child's own configuration (literature_task, proposed_annotation_ref required under private yield binding; A102 requested structure components field) and checks source/artifact custody | import root.a102.a102_literature_bindings ×1, import root.a102.literature_task_credit ×1 |
| configuration.py | 13 | contract_information_profile only for literature roles (or the reference-evidence annotation root) | none |
| credit.py | 17 | credit kind 'scientific'; credit view from services.scientific_credit; credit projector LiteratureTaskCredit (old literature_task_credit) | import root.a102.literature_task_credit ×1, self.services.scientific_credit ×1 |
| decision_delivery.py | 346 | model call (same as resource task_decision plus inline decision inputs, execution_expectations captured for 'literature_table') and the exchange loop; differs: complete_decision uses provider.complete_with_presentation with this binding's decision_prompt_renderer (present_source_decision) when available | import root.a102.episode_work_report ×2, import root.a102.library.hpc_prompt ×1, import root.a102.runtime ×2, _live_original_runtime._action_generation_schema ×2, _live_original_runtime.apply_state_frame ×1, _live_original_runtime._ASSIGNMENT_TRANSPORT ×1, _live_original_runtime._category_yield_parameters ×1, _live_original_runtime.child_option_information ×2, _live_original_runtime.composition_lookup_schema ×2, _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS ×1, _live_original_runtime.DECISION_CONTEXT_VERSION ×2, _live_original_runtime.DECISION_EXCHANGE_PROTOCOL ×5, _live_original_runtime._digest ×1, _live_original_runtime.Draft202012Validator ×1, _live_original_runtime.instructional_model_context ×4, _live_original_runtime.is_contract_information ×1, _live_original_runtime.lookup_attempts ×1, _live_original_runtime.model_snapshot ×2, _live_original_runtime._object ×3, _live_original_runtime._plain ×2, _live_original_runtime._recorded_action_generation_schema ×1, _live_original_runtime._recorded_assignment_transport ×1, _live_original_runtime._references_in ×1, _live_original_runtime.requested_contract_information ×2, _live_original_runtime.schema_failure_diagnostic ×2, _live_original_runtime.state_frame ×1, _live_original_runtime.ValidationError ×5, _live_original_runtime.WorkflowError ×14, _live_original_runtime.yield_table ×1, 'runtime_model_calls' ×8, workflow.available_child_roles ×1, workflow.binding_context ×1, workflow.contract_information_profile ×1, workflow.contract_information_reply ×1, workflow.controller_binding ×1, workflow.decision_exchanges ×4, workflow.decision_protocol ×3, workflow.episode_bindings ×1, workflow.execute ×1, workflow.execution_expectations ×1, workflow.freeze_contract_information ×1, workflow.freeze_literature_numerical_contracts ×1, workflow.history_preview ×1, workflow.is_job_source ×3, workflow.job_episodes ×2, workflow.journal ×3, workflow.launch_instructions ×2, workflow.native_estimation_context ×1, workflow.numerical_contracts ×1, workflow.pending_work ×1, workflow.permits_common_action ×1, workflow.provider ×3, workflow.receipts ×4, workflow.resource_context ×1, workflow.resource_estimator ×5, workflow.run_id ×1, workflow.services ×2, workflow.shared_information_context ×1, workflow.specialist ×1, workflow.store ×2, workflow.uses_received_record_context ×2, workflow.validate_contract_information ×5, workflow.waiting_support ×1 |
| decision_presentation.py | 43 | present_source_decision: text-prompt rendering of the decision from reconstructed state frames (bootstrap/update/lookup_result), keeps per-(episode, role) prompt state, falls back to JSON dump of the context when no text task applies | import root.a102.providers ×2, _live_original_providers.apply_state_frame ×3, _live_original_providers.DECISION_CONTEXT_VERSION ×1, _live_original_providers.text_instructions ×1 |
| episode.py | 78 | episode class; binding_path ...source_evidence_examination/table_evidence_extraction, commissioned by source_evidence_examination, role 'literature_table'; constructor options outcome_page_size (positive int, default 8), structure_population (bool), reference_parent_sources (unique refs, only with structure population), contract_information_profile (only with structure population), private_yield_binding (bool), yield_bindings (only with private binding); reference_evidence() entry; permitted common actions tool, reason, child, redeliver_report (no wait) | import root.a102.literature_task_credit ×1 |
| from_parent.py | 85 | assignment schema reading_assignment_v1: page (page_assignment_v1) + selection anyOf table selector (source_ref, sheet_key, offset, limit, header_row, where column/match/value/case_sensitive) or byte window; literature_task (+ proposed_annotation_ref required under private yield binding; credit_unit then supplied by binding); requested structure components; prepare_assignment fills credit_unit + yield_settings (kind, cutoff, uncertainty_alpha) from this episode's yield_bindings for the task key and refuses mismatches, checks proposed annotation equals the parent's, checks custody (artifact matches representation, offsets in bounds) and that the reading stays within the literature_page parent's source | import root.a102.a102_literature_bindings ×1, import root.a102.literature_task_credit ×2, self.services.read_record ×1 |
| goal.py | 8 | goal text: investigate the selected table/sheet and its scientific meaning; select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant; XLSX cells/formulas/caches keep native identity; article XML tables read through exact source windows; plus shared literature investigation guidance (no reading quota; preserve subject, conditions, representation, version, byte anchors; distinguish source claims from target applicability; negatives advance; navigation earns no credit; commissioned yield settings guide continuation) | none |
| __init__.py | 0 | empty package marker | none |
| internal_summary.py | 83 | decision context: literature_assignment, literature_source_custody (version/artifact/text/stdout/stderr/parent refs), own_literature_outcomes page (acquisition + read tools, outcome_page_size), history meaning; with structure population: literature_experimental_work (source_experimental_evidence, A102) and population task context (owned population sources by metadata SQL, latest failed population attempt); reference-evidence root initial context | import root.a102.literature_task_selection ×1, 'runtime_actions' ×1, self.services.own_outcomes ×1, self.services.workflow ×2, workflow.run_id ×2, workflow.store ×2 |
| presentation_selection.py | 30 | chooses the text renderer for the state: HPC, published scientific (structural evidence), API launch, selected execution, monitor, else receiver prompt | import root.a102.library.hpc_prompt ×1, import root.a102.library.monitor_prompt ×1, import root.a102.providers ×2, import root.a102.receiver_prompt ×1, import root.a102.structural_homology_evidence_prompt ×1, _live_original_providers.is_api_launch_context ×2, _live_original_providers.is_published_scientific_context ×2, _live_original_providers._ordinary_runtime_receiver_context ×1, _live_original_providers.render_api_launch_prompt ×1, _live_original_providers.render_structural_homology_evidence_prompt ×1 |
| received_evidence.py | 73 | received report sources/facts for non-literature parents (structure cells), receive_cells on received forms, received evidence tokens (content digests), validate_received_report: screening/lead answers must equal saved work; structure rows must be from received/selected sheets and requested components | import root.a102.literature_sheet_updates ×1, import root.a102.literature_task_credit ×1, import root.a102.method_loop.durable ×1, self.services.record_selection ×1, workflow.store ×2 |
| report_delivery.py | 25 | finish: without contract returns credit + pending handles + current report facts; with contract fills parent's typed form from interpretations + facts once and saves it | import root.a102.library.private_policy_call ×1, import root.a102.library.report_fact_assembly ×1, import root.a102.runtime ×2, _invoke_private_policy ×1, _live_original_runtime.form_with_facts ×1, _live_original_runtime.Record ×2, 'runtime_forms' ×2, workflow.binding_context ×1, workflow.episode_bindings ×1, workflow.facts ×1, workflow.journal ×2, workflow.pending_handles ×1, workflow.release ×2, workflow.source_credit_view ×1 |
| source_contracts.py | 38 | module docstring (binding supplies operands, operations, custody and the commissioned task's private yield binding; reading selection is information, never a script); ROLES list; schemas _WINDOW/_TABLE/_PAGE; tool sets _ACCESS_TOOLS (state.query, source.read/locate/sequence.scan/sequence.references/experimental.records, image.view, archive members/extract, xlsx sheets/rows, pdf info/text/page, execution.estimate), _ACQUISITION_TOOLS, _READ_TOOLS; population catalogue literature.structure.populate | import root.a102.a102_literature_bindings ×1, import root.a102.communication ×1, import root.a102.composition_information ×1, import root.a102.domain ×1, import root.a102.episode_bindings ×1, import root.a102.experimental_database_acquisition ×1 |
| source_interpretation.py | 43 | reason action extension for verified_source_leads tasks (source_lead with witness); execute_reasoning reads the witness window, commits reasoning and validates the lead; invalid lead returns status invalid | import root.a102.literature_contract_error ×1, import root.a102.literature_task_credit ×3, workflow.store ×1 |
| source_operations.py | 96 | tool catalogue: only _ACCESS_TOOLS from the shared catalogue (pubmed-only ncbi search; execution.estimate limited to xlsx sheets/rows), plus literature.structure.populate under structure population (argument transport under contract profile); execute: argument check, populate through structure repository with text witness materialization, else shared execute_tool (locate/sequence/experimental tools restricted to received refs); _tool_arguments: within the page source, xlsx rows must use the assigned sheet_key, populate refs within the source | import root.a102.composition_information ×1, import root.a102.library.literature_assay_inputs ×1, import root.a102.literature_contract_error ×1, self.services.execute_tool ×1, self.services.tool_catalog ×1 |
| source_references.py | 35 | custody helpers: _require (reference in scope), _artifact by representation, _within_source walk of parent_source_refs, resolve via reference_in_context | self.services.read_record ×1, self.services.reference_in_scope ×1 |
| structural_sheet_operations.py | 17 | lazily built LiteratureStructureRepository (source-model geometry and local-fit components); population routes under structure population | import root.a102.a102_literature_bindings ×1, import root.a102.literature_structure_storage ×1, workflow.run_id ×1, workflow.store ×1 |
| task_instructions.py | 26 | composes default runtime instructions + binding goal + reasoning-commit + tool knowledge + launch library + redeliver_report text + wait text + native event text; exchange protocol history guidance replacement (identical to resource instructions.py) | import root.a102.runtime_prompt ×2, _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL ×1, _live_original_runtime_prompt.INSTRUCTIONS ×4, _live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT ×1, workflow.binding_context ×1, workflow.decision_protocol ×1, workflow.is_job_source ×1, workflow.job_episodes ×1, workflow.knowledge ×1, workflow.launch_instructions ×1, workflow.native_event_information ×1, workflow.permits_common_action ×3, workflow.specialist ×1 |
| task.py | 269 | iteration source: as resource task.py but decision state built inline and adds annotation context when is_scientific_source (proposed annotations + comparisons under annotation-axis credit, else annotation_context); action-contract feedback inline; report_update validated with grain 'literature_table' | import root.a102.episode_source_failure ×1, import root.a102.library.action_contracts ×1, import root.a102.library.private_policy_call ×1, import root.a102.providers ×1, import root.a102.read_mapping ×1, import root.a102.runtime ×2, _invoke_private_policy ×1, _live_original_runtime.AcquisitionError ×2, _live_original_runtime.ActionFailure ×1, _live_original_runtime.ContractError ×1, _live_original_runtime.ContractInformationError ×1, _live_original_runtime._decode_recorded_action_response ×1, _live_original_runtime.Draft202012Validator ×3, _live_original_runtime.EventTargetError ×2, _live_original_runtime.FACT_MEANINGS ×1, _live_original_runtime.FACT_SOURCES ×1, _live_original_runtime.observes_action_outcome ×1, _live_original_runtime._plain ×2, _live_original_runtime._references_in ×1, _live_original_runtime.ReportBoundaryError ×1, _live_original_runtime.ReportRedelivery ×2, _live_original_runtime.schema_failure_diagnostic ×1, _live_original_runtime.SourceEnd ×2, _live_original_runtime.validate_form ×1, _live_original_runtime.ValidationError ×3, _live_original_runtime._wait_target_feedback ×2, _live_original_runtime.WorkflowError ×2, 'runtime_actions' ×9, 'runtime_episodes' ×1, 'runtime_model_calls' ×2, workflow.action_schema ×1, workflow.annotation_context ×1, workflow.automatic_score_updates ×1, workflow.binding_context ×3, workflow.catalog ×1, workflow.completed_unit ×3, workflow.completions ×3, workflow.controller_binding ×1, workflow.controller_value ×2, workflow.decision_exchanges ×3, workflow.delivery_resolution_inputs ×1, workflow.delivery_status ×1, workflow.execute ×1, workflow.execution_binding ×7, workflow.extra_report_sources ×1, workflow.inprocess_replay ×4, workflow.is_scientific_source ×1, workflow.job_episode_options ×1, workflow.journal ×10, workflow.knowledge ×1, workflow.last_observed_credit ×1, workflow.local_outcome_preview ×1, workflow.next_return ×1, workflow.pending_work ×2, workflow.perform_selected_wait ×1, workflow.permits_common_action ×1, workflow.reasoning_action_schema ×1, workflow.receipt_projection ×1, workflow.receive_native_outcome ×1, workflow.receive_outcome ×1, workflow.resolve_pending_deliveries ×1, workflow.resolver ×1, workflow.retain_shared_grading_results ×1, workflow.run_id ×4, workflow.selected ×3, workflow.source_credit_binding ×1, workflow.source_credit_view ×2, workflow.specialist ×3, workflow.store ×12, workflow.tools ×1, workflow.validate_report ×1, workflow.working_state ×1 |
| task_state.py | 108 | per-episode source state and restore/checkpoint/record_effect/record_execution_failure (identical to resource task_state.py) | import root.a102.episode_source_failure ×1, import root.a102.runtime ×2, _live_original_runtime.ActionLeaf ×1, _live_original_runtime.EFFECT_VERSION ×1, _live_original_runtime.Episode ×1, _live_original_runtime.interpretation_schema ×1, _live_original_runtime._object ×1, _live_original_runtime._plain ×1, _live_original_runtime.Record ×1, 'runtime_actions' ×5, workflow.archive ×1, workflow.completions ×4, workflow.context ×1, workflow.controller_value ×1, workflow.execution_binding ×4, workflow.grains ×1, workflow.inprocess_replay ×7, workflow.journal ×5, workflow.progress_provider ×2, workflow.recover_commissions ×1, workflow.run_id ×1, workflow.source_credit_view ×1, workflow.store ×2 |
| task_waiting.py | 9 | suspension registration of a wait condition with the execution backend | workflow.execution_backend ×1, workflow.execution_handle ×2 |
| to_parent.py | 41 | fact sources: A102 structure population fact source (if enabled), screening answers, verified source leads; facts: screening answers when answer_kind screening, lead dispositions for verified_source_leads, structure rate facts from received source records per provider; validate_report re-validates assignment, form references, received report | import root.a102.a102_literature_bindings ×1, import root.a102.literature_task_credit ×2, self.services.read_record ×1, workflow.store ×2 |
| waiting.py | 8 | supports_wait False | none |
| yield_estimator.py | 22 | continuation task key from the commissioned literature_task; with private yield binding, the controller is built from this episode's yield_bindings declaration (kind, cutoff, uncertainty_alpha, credit_unit) for that task key; missing declaration raises; without private binding no own controller (None) | import root.a102.literature_task_credit ×2 |

Indirect old-runner names: `source_contracts.py` re-exports `ReportBoundaryError`, `plain` and `validate_form` (old `communication`); `CONTRACT_INFORMATION_PROFILE` (old `composition_information`); `ContractError`, `REF`, `identity`, `obj`, `source_location_inputs` and `validate_schema` (old `domain`); `reference_in_context` (old `episode_bindings`); and `EXPERIMENT_DATABASE_TOOLS`. Several mixins use these through `.source_contracts`. `self.services.workflow.store` and `.run_id` (in `internal_summary`, `received_evidence`, `to_parent`, `source_interpretation` and `structural_sheet_operations`) reach the old runner through services. The old tables `runtime_actions` and the population-operation tables are read directly by SQL in `internal_summary`.

## Carried over

Carried 19 November 2026 into the ten-file form (private binding `TableEvidenceExtraction`), shaped on the finished private binding of its sibling `passage_evidence_extraction` (copies are intended). What differs from it: the `selection` form, the `sheet_key` check of `source.xlsx.rows`, the goal text and the `readings` of the finding. "UNPLACED" rows are also in `docs/axis_restructure_20261117/carry_over_blocked/a102__structural_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__table_evidence_extraction.md`.

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
| episode.py | LiteratureEpisode | episode function | episode.py TableEvidenceExtraction(EpisodeBinding) |
| episode.py | LiteratureEpisode.__init__ | episode function | constructor values: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE; structure_population -> settings key read in task.py offered/decide; private_yield_binding / yield_bindings -> machinery (the controller is always bound from the task, yield_estimator.py); contract_information_profile -> machinery |
| episode.py | LiteratureEpisode.reference_evidence | episode function | UNPLACED: root-only entry that builds a reference-source investigation (reference_parent_sources); not this episode's |
| episode.py | LiteratureEpisode._role | machinery | role check; each role is its own episode (README 3a BindingContext.role) |
| episode.py | LiteratureEpisode.permitted_common_actions | episode function | task.py TOOLS and offered (tool, reason); child has no slot; redeliver_report is gone (README 3b R2) |
| from_parent.py | SourceFromParent | episode function | messages/read_from_parent.py (the mix-in is not carried; its methods are below) |
| from_parent.py | SourceFromParent.child_assignment_schema | machinery | the parent's view of this assignment (README 3b C3: the parent writes its own) |
| from_parent.py | SourceFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (PAGE_FORM; `selection` is one untyped record because the old anyOf of table selector or window is not a form type) |
| from_parent.py | SourceFromParent._validate_page | episode function | UNPLACED: checks the page against the Store (artifact equals the source's artifact for the representation; refs in scope): a check of a commission (rule 1); read_from_parent has no records |
| from_parent.py | SourceFromParent._validate_assignment | episode function | messages/read_from_parent.py read_from_parent, check_selection, check_where (exact shape of the table selector or window; source and representation agree with the page); the source_offset_out_of_bounds check reads the artifact (Store) and is UNPLACED as a check of a commission |
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
| source_operations.py | SourceSourceOperations._tool_arguments | episode function | task.py admitted (schema, within-source check, and the literature_table_sheet_mismatch check of source.xlsx.rows against the commission's sheet_key, which action adds to the tool envelope as sheet_key) |
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
