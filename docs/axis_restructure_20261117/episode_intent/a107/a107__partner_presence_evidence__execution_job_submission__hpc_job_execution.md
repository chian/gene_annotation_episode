# a107/partner_presence_evidence/execution_job_submission/hpc_job_execution — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_job_submission/hpc_job_execution/<file>`. 29 Python files, 2,179 lines. Role `launch_hpc`, no children, no entry roles.

## Purpose (own words)

`goal.py` delegates to the practical behavior's instructions (`terminal_execution.TerminalExecutionBehavior.instructions`): "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. ... If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. ... target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work ... execution_resource.ssh_argv, when present, is the exact configured transport prefix ... The episode iterator decides continuation from credit; add no stopping budget." followed by the resource-specific sections from the frozen launch instruction library.

## Task and instructions

`replaces_default_instructions = True`. `task_instructions.py` composes the specialist text, tool knowledge, launch library instructions and the pending-child-delivery repair paragraph only (no reasoning, wait or native-event paragraphs; a leftover bare expression `source.workflow.native_event_information is not None`).

## What it reads from its parent's assignment

One practical assignment (`practical_assignment_v1`, `ASSIGNMENT_SCHEMA` with `resource_kind: hpc`, `resource_id`, `requested_job` alternatives, endpoint usable_handoff/completed_job_outputs, workspace, initial_context). `child_assignment_schema`: under an `hpc` ancestry, a `launch` parent exposes only its frozen permitted HPC requests (`enum` of those requests; `frozen_hpc_launch_request_missing` otherwise). `prepare_assignment` as the API sibling but without the BLAST launch-selection check; `science._check_parent_inputs` without the BLAST API check.

## Children

None.

## Decision state and what the model sees

`decision_context` from the practical delegate: `execution_assignment`, `execution_resource` (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory snapshot), `coordinator_workspace`, `execution_progress` (practical state credit view), `execution_completion` (completion proof). `task_decision.call` without waiting_support; HPC contexts get `requested_action_history`. Presentation renders the HPC prompt (`render_hpc_prompt`).

## Tools offered

The practical delegate's `operation_catalog('hpc')` (`exec_command` with target resource/coordinator, workdir, env). Each command: validated, `PracticalState.begin/finish`, `finalize_scientific_command`, receipt published as `episode.practical_receipt`. Common actions: tool only.

## Credit

Operational. Live credit = practical state `credit_view()` through `_delegate(context)`; closed credit = captured closed view.

## Continuation

`_launch_hpc_yield_controller`: profile `launch_hpc:<request yield class>` (`practical_hpc_<native jobs>_<handoff|outputs>`) → `YieldController(..., estimate_with_context=<delegate practical_estimator>)` (PracticalYieldEstimator over the practical state's verify_completion). `verify_completion`: recorded closed verdict, else the practical state.

## Report to parent

`facts`: delegate facts (`practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`) + `execution_handoff_refs` (returnable handoffs from practical receipt refs), appservice support refs, `execution_blast_hsps` [], `execution_result_refs`, file source refs, capture outcomes, `NATIVE_RESULT_ORIGIN` when windows exist, `execution_completed` + closed-credit facts. `validate_report` as the API sibling.

## Differences from its sibling api_job_execution

See the API document; in short: shell-command execution agent instead of service operations, no wait, frozen-HPC-request child schema, handoffs derived from practical receipts, no BLAST-graded checks, no selected_execution_task view.

## File by file
| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| binding_record.py | 8 | as_record: binding_id partner_presence_evidence/execution_job_submission/hpc_job_execution (same configuration fields) | none |
| completion.py | 51 | completion_for_action via practical delegate; verify_completion via closed verdict else practical state(context).verify_completion | ESTIMATOR_VERSION(2), import:episode_return_records(1), import:numerical(1), import:practical_yield(1), NumericBand(2), runtime_observations(1) |
| configuration.py | 119 | same constructor as parent launch; builds TerminalExecutionBehavior, APIServiceExecution, progress provider, native readers | import:numerical(1), YieldController(3), YieldParameters(3) |
| credit.py | 136 | operational credit; closed-credit capture/verification; live credit = practical delegate credit_view | import:episode_receipts(1), import:episode_return_records(3), runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2) |
| episode.py | 103 | ExecutionEpisode assembly; binding_path .../hpc_job_execution; roles (launch_hpc,), no children; common actions tool only | import:communication(1), import:runtime(1) |
| execution_contracts.py | 57 | constants (VERSION, LAUNCH/RESULTS versions, RESULT_PROVIDER, _CLOSED_CREDIT, ROLES, KINDS, ROLE_KINDS, schema fragments, NATIVE_RESULT_ORIGIN) + native_result_operation_catalog; re-exports helpers | import:communication(1) |
| from_parent.py | 117 | same as API child except child_assignment_schema: under hpc ancestry a launch exposes only frozen hpc requests; no BLAST launch selection check in prepare_assignment | none |
| goal.py | 6 | goal = practical delegate instructions (TerminalExecutionBehavior execution-agent text) | none |
| initial_information.py | 9 | reader catalog .../hpc_job_execution | none |
| __init__.py | 0 | empty package marker | none |
| internal_summary.py | 58 | decision_context from practical delegate (resource, workspace, progress, completion proof); no selected_execution_task | import:runtime(6), _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.json(2), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), runtime_actions(2), workflow.binding_context(1), workflow.catalog(1), workflow.controller_binding(1), workflow.delivery_status(1), workflow.extra_report_sources(1), workflow.job_episode_options(1), workflow.journal(3), workflow.knowledge(1), workflow.local_outcome_preview(1), workflow.pending_work(1), workflow.run_id(1), workflow.source_credit_binding(1), workflow.source_credit_view(1), workflow.specialist(1), workflow.store(3), workflow.tools(1), workflow.working_state(1) |
| presentation.py | 74 | present_context renderer choice | import:decision_context(1), _live_original_providers.apply_state_frame(3), _live_original_providers.DECISION_CONTEXT_VERSION(2), _live_original_providers.deepcopy(1), _live_original_providers.infernal_receiver_context(1), _live_original_providers.is_api_launch_context(2), _live_original_providers.is_published_scientific_context(2), _live_original_providers.json(1), _live_original_providers._ordinary_runtime_receiver_context(1), _live_original_providers.render_api_launch_prompt(1), _live_original_providers.render_partner_presence_evidence_prompt(1), _live_original_providers._rna_comparison_receiver_context(3), _live_original_providers.text_instructions(1) |
| received_api_reports.py | 4 | reader authority .../hpc_job_execution | none |
| received_execution_information.py | 4 | reader authority .../hpc_job_execution | none |
| received_records.py | 127 | _context_target, _received handoffs/results, initial_references | none |
| resource_information.py | 70 | resource_tool_contracts: launch/results/homology/native operations per resource | none |
| science.py | 57 | parent input checks without the BLAST API parent check | runtime_episodes(1) |
| state.py | 19 | initialize via delegate; state() returns delegate practical state | none |
| task_decision.py | 357 | call/exchange without waiting_support | binding_context(1), import:episode_work_report(2), import:providers(1), import:runtime(1), _live_original_runtime._action_generation_schema(2), _live_original_runtime.apply_state_frame(1), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._category_yield_parameters(1), _live_original_runtime.child_option_information(2), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime._digest(1), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.infernal_receiver_context(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime._json(14), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.Mapping(4), _live_original_runtime.model_snapshot(2), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime.yield_table(1), runtime_model_calls(8), workflow.available_child_roles(1), workflow.binding_context(1), workflow.contract_information_profile(1), workflow.contract_information_reply(1), workflow.controller_binding(1), workflow.decision_exchanges(4), workflow.decision_protocol(3), workflow.episode_bindings(1), workflow.execute(1), workflow.execution_expectations(1), workflow.freeze_contract_information(1), workflow.freeze_literature_numerical_contracts(1), workflow.history_preview(1), workflow.is_job_source(3), workflow.job_episodes(2), workflow.journal(3), workflow.launch_instructions(2), workflow.native_estimation_context(1), workflow.numerical_contracts(1), workflow.pending_work(1), workflow.provider(3), workflow.receipts(4), workflow.resource_context(1), workflow.resource_estimator(5), workflow.run_id(1), workflow.services(2), workflow.shared_information_context(1), workflow.specialist(1), workflow.store(2), workflow.uses_received_record_context(2), workflow.validate_contract_information(5) |
| task_instructions.py | 20 | composition without reasoning/wait/native event paragraphs | _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL(1), _live_original_runtime_prompt.INSTRUCTIONS(4), workflow.binding_context(1), workflow.decision_protocol(1), workflow.is_job_source(1), workflow.job_episodes(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.specialist(1) |
| task.py | 225 | NativeTask loop | import:episode_source_failure(1), import:providers(1), import:runtime(1), _live_original_runtime.AcquisitionError(2), _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractError(1), _live_original_runtime.ContractInformationError(1), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime.Draft202012Validator(3), _live_original_runtime.EventTargetError(1), _live_original_runtime.inspect(1), _live_original_runtime._json(5), _live_original_runtime.json(8), _live_original_runtime.Mapping(3), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.SourceEnd(2), _live_original_runtime.sqlite3(2), _live_original_runtime.subprocess(2), _live_original_runtime.validate_form(1), _live_original_runtime.ValidationError(3), _live_original_runtime._wait_target_feedback(1), _live_original_runtime.WorkflowError(2), runtime_actions(8), runtime_episodes(1), runtime_model_calls(2), workflow.action_schema(1), workflow.automatic_score_updates(1), workflow.binding_context(2), workflow.completed_unit(3), workflow.completions(3), workflow.controller_value(2), workflow.decision_exchanges(3), workflow.delivery_resolution_inputs(1), workflow.execute(1), workflow.execution_binding(7), workflow.inprocess_replay(4), workflow.journal(7), workflow.last_observed_credit(1), workflow.next_return(1), workflow.pending_work(1), workflow.permits_common_action(1), workflow.reasoning_action_schema(1), workflow.receive_native_outcome(1), workflow.receive_outcome(1), workflow.resolve_pending_deliveries(1), workflow.resolver(1), workflow.retain_shared_grading_results(1), workflow.run_id(3), workflow.selected(3), workflow.source_credit_view(1), workflow.specialist(2), workflow.store(9), workflow.validate_report(1) |
| task_report.py | 22 | finish: form_with_facts into runtime_forms | import:runtime(1), _live_original_runtime.form_with_facts(1), _live_original_runtime._json(2), _live_original_runtime.json(1), _live_original_runtime.Record(2), runtime_forms(2), workflow.binding_context(1), workflow.episode_bindings(1), workflow.facts(1), workflow.journal(2), workflow.pending_handles(1), workflow.release(2), workflow.source_credit_view(1) |
| task_state.py | 107 | NativeTaskState | import:episode_source_failure(1), import:runtime(1), _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime._json(2), _live_original_runtime.json(4), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.Record(1), runtime_actions(5), workflow.archive(1), workflow.completions(4), workflow.context(1), workflow.controller_value(1), workflow.execution_binding(4), workflow.grains(1), workflow.inprocess_replay(7), workflow.journal(5), workflow.progress_provider(2), workflow.recover_commissions(1), workflow.run_id(1), workflow.source_credit_view(1), workflow.store(2) |
| task_suspension.py | 8 | suspension_changed | workflow.execution_backend(1), workflow.execution_handle(2) |
| terminal_execution.py | 226 | full TerminalExecutionBehavior for local/hpc incl. execution-agent instructions text (exec_command, resource instructions, no stopping budget) | import:communication(1), import:practical_yield(1), PracticalYieldEstimator(2) |
| to_parent.py | 100 | facts: delegate facts + execution_handoff_refs from practical receipt refs, appservice refs, result refs, file sources, capture outcomes, NATIVE_RESULT_ORIGIN, execution_completed | none |
| waiting.py | 10 | perform_selected_native_wait | import:runtime(1), _live_original_runtime.EventTargetError(1), _live_original_runtime._wait_target_feedback(1), workflow.perform_selected_wait(1) |
| work_operations.py | 35 | catalog/execute through practical delegate after parent input checks | none |
| yield_estimator.py | 50 | YieldController with profile launch_hpc:<request class>; estimator from practical delegate | import:numerical(1), import:practical_yield(1), PracticalYieldEstimator(2), YieldController(2), YieldParameters(2) |

## Carried over

One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__execution_job_submission__hpc_job_execution.tsv`. Columns: old file, kind and name (copied), then whether it is old-runner machinery or an episode function, then its new place (or the machinery reason). Rows whose place begins "unplaced:" are also listed in `carry_over_blocked/a107__partner_presence_evidence__execution_job_submission__hpc_job_execution.md`.

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | class | NativeBindingRecord | machinery | binding record and the binding's own as_record() (README 3e: settings/declaration recorded by the system) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | the binding's own as_record() (README 3e) |
| completion.py | class | NativeCompletion | machinery | completion mix-in of the old runner; its methods are listed below |
| completion.py | method | NativeCompletion.completion_for_action | machinery | per-action completion proof as a controller packet (README 3d: the controller input is built by the system); the completion controller is chosen in yield_estimator.py |
| completion.py | method | NativeCompletion._closed_completion_verdict | machinery | reads runtime_observations of the old journal to reuse a recorded verification (README 3d: deleted) |
| completion.py | method | NativeCompletion.verify_completion | machinery | estimator completion verification (README 3d/7b PracticalYieldEstimator(verify_completion)); the proof it verified is rebuilt from the held receipts in messages/internal_summary.py completion_proof |
| configuration.py | class | NativeConfiguration | episode function | values the run sets: ctx.settings read in task.py (resource, initial_information, coordinator_workspace, launch_instructions_directory, knowledge_library_directory) and settings in yield_estimator.py (task_yield_profiles); adapters, providers and Store handles of the old construction are machinery |
| configuration.py | method | NativeConfiguration.__init__ | episode function | the same settings values (README 3 configuration.py row); old-runner adapters/providers built there are not carried |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py credit (project_practical_credit) |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind 'operational' (README 3d: deleted) |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed credit snapshot: reads runtime_episodes/runtime_actions (journal) |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed credit snapshot: reads the receipt inheritance tables |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_value | machinery | closed credit snapshot sanity check; the system hands the controller-seen credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed credit snapshot written into the closing facts, reads runtime_forms; replaced by completion[credit] |
| credit.py | method | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed credit snapshot re-validation over runtime_forms/sqlite_master |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (live projection; the closed branch is machinery) |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (PracticalState.credit_view = library project_practical_credit over summary receipts) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| episode.py | class | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| episode.py | method | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | ExecutionEpisode.permitted_common_actions | episode function | task.py selection_schema / action (the tool action only) |
| execution_contracts.py | function | native_result_operation_catalog | episode function | unplaced: the execution.results.* operations belong to the results role (execution_result_acquisition), not to launch_hpc |
| from_parent.py | class | NativeParentRequests | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | method | NativeParentRequests._permitted | episode function | unplaced: filter of the parent launch's frozen requests by the parent's constraints (reads the parent's assignment, README 5 item 14) |
| from_parent.py | method | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the ASSIGNMENT_SCHEMA properties with resource_kind fixed (DeclaredField hpc) and resource_id a free text field) and library validate_assignment in read_from_parent |
| from_parent.py | method | NativeParentRequests._launch | episode function | unplaced: validation of the parent launch's execution_launch_assignment_v1 (reads the parent's assignment) |
| from_parent.py | method | NativeParentRequests._constraints | episode function | unplaced: validation of the parent launch's allowed_resource_ids/allowed_kinds |
| from_parent.py | method | NativeParentRequests.child_assignment_schema | episode function | unplaced: the frozen HPC launch request exposed from the parent's assignment (frozen_hpc_launch_request_missing); the parent copies the chosen request into this child's assignment in its msg_to_child |
| from_parent.py | method | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (library validate_assignment); the re-validation against the parent launch (masking, utility, input-version, native BLAST DB, standard BLAST DB, RNA-structure inputs) is unplaced: it reads the parent's assignment |
| goal.py | class | NativeGoal | episode function | goal.py GOAL/UNIT/RESULT; the instruction text in task.py |
| goal.py | method | NativeGoal.instructions | episode function | task.py INSTRUCTIONS and instructions() |
| initial_information.py | function | initial_information | episode function | task.py decide: resource_information(settings) with the recorded inventory_snapshot shown at every decision; the received_api_information part is the API role's and is not carried |
| internal_summary.py | function | native_decision_snapshot | machinery | decision snapshot over runtime_actions/journal/credit view/receipts of the old runner; the model context is built in task.py decide from the summary |
| internal_summary.py | class | NativeInternalSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | NativeInternalSummary._with_selected_execution_task | episode function | unplaced: identity function in this HPC copy (it returned its value unchanged), so no selected_execution_task exists to carry |
| internal_summary.py | method | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion) |
| presentation.py | function | present_context | episode function | unplaced: the per-context prompt renderer (render_hpc_prompt of the old shared root, which is not read) and the replay of saved state frames; decide hands the plain JSON context in ModelRequest.context |
| received_api_reports.py | function | received_api_reports | episode function | unplaced: selects the API reader authority of the old reader catalog; launch_hpc receives no API report |
| received_execution_information.py | function | received_execution_information | episode function | unplaced: selects the result readers of the old reader catalog (names an a110 path); launch_hpc receives no result |
| received_records.py | class | NativeReceivedRecords | episode function | messages/internal_summary.py returnable_handoff and messages/final_to_parent.py facts (the received-record readers are the results role's) |
| received_records.py | method | NativeReceivedRecords._context_target | episode function | messages/internal_summary.py returnable_handoff (the handoff must be for this exact assignment; the launch/results branches are other roles') |
| received_records.py | method | NativeReceivedRecords._received | episode function | unplaced: reads the known record refs of the binding context through the old handoff reader and result readers; this role received none, so execution_result_refs and file source facts are empty (messages/final_to_parent.py) |
| received_records.py | method | NativeReceivedRecords.initial_references | episode function | unplaced: for launch_hpc it returned no initial references (the validations of masking, utility, NMF and RNA inputs ran only for roles launch and launch_local) |
| resource_information.py | class | NativeResourceInformation | episode function | unplaced: commissionable operation contracts of every configured resource for the parent roles; not this episode's tools |
| resource_information.py | method | NativeResourceInformation.resource_tool_contracts | episode function | unplaced: commissionable launch/results operation contracts of every resource, for the parent roles (launch, results) |
| science.py | class | NativeScienceInputs | episode function | unplaced: re-validation of the parent launch's science inputs (reads the parent's recorded request) |
| science.py | method | NativeScienceInputs._masking_inputs | episode function | unplaced: validates masking inputs against the parent launch (reads the parent's assignment, README 5 item 14) |
| science.py | method | NativeScienceInputs._utility_inputs | episode function | unplaced: validates BLAST utility inputs against the parent launch |
| science.py | method | NativeScienceInputs._expression_nmf_inputs | episode function | unplaced: validates expression NMF inputs against the parent launch |
| science.py | method | NativeScienceInputs._versions | episode function | unplaced: validates the parent launch's immutable input versions |
| science.py | method | NativeScienceInputs._check_parent_inputs | episode function | unplaced: re-read the parent launch request from runtime_episodes before every command (README 5 item 14) |
| state.py | class | NativeState | machinery | practical state mix-in (file-backed PracticalState); the state is the view outcomes (messages/internal_summary.py) |
| state.py | method | NativeState.initialize | machinery | creates the file-backed PracticalState and runs _check_parent_inputs |
| state.py | method | NativeState.state | machinery | returns the file-backed PracticalState |
| task.py | class | NativeTask | episode function | task.py decide/action/exec_command; the loop is the system's |
| task.py | method | NativeTask.next | episode function | task.py decide (the model request) and the tool unit; the loop and the replay/checkpoint branches are the system's |
| task.py | method | NativeTask.apply_response | episode function | task.py action (validate the answer, return the exec_command ToolCall or Rejected) |
| task.py | method | NativeTask.execute | episode function | task.py exec_command (tool) |
| task_decision.py | class | NativeTaskDecision | episode function | task.py decide/action; its exchange methods are machinery (listed below) |
| task_decision.py | method | NativeTaskDecision.call | machinery | model call wrapped in runtime_model_calls and the decision exchange; the system records the ModelRequest |
| task_decision.py | method | NativeTaskDecision.instructions | episode function | task.py instructions() |
| task_decision.py | method | NativeTaskDecision.conversation_key | machinery | conversation sessions (README 3a: deleted) |
| task_decision.py | method | NativeTaskDecision.interpretation_context | machinery | context of the old report_update interpretation (the parent-written form is gone) |
| task_decision.py | method | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop (request_context/select_action) |
| task_decision.py | method | NativeTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision); a lookup is a tool |
| task_decision.py | method | NativeTaskDecision.decision_completion | machinery | decision completion record of the old runner |
| task_instructions.py | function | instructions | episode function | task.py instructions() (the resource instructions, tool-knowledge and launch-library texts); the pending_child_delivery and decision-exchange history paragraphs describe actions that no longer exist |
| task_report.py | class | NativeTaskReport | machinery | report_form machinery (form_with_facts, runtime_forms, release) |
| task_report.py | method | NativeTaskReport.finish | machinery | saves runtime_forms and releases the episode; the facts are messages/final_to_parent.py final_to_parent |
| task_state.py | class | NativeTaskState | machinery | task state with checkpoint/restore |
| task_state.py | method | NativeTaskState.__init__ | machinery | task state of the old decision machine (identity, calls, restored flags) |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | binds the old execution context |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | writes a failure into runtime_actions and the credit; the tool returns its failure as its outcome (task.py exec_command) |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | restore_checkpoint (README 3e) |
| task_state.py | method | NativeTaskState.restore | machinery | restore (README 3e) |
| task_state.py | method | NativeTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | method | NativeTaskState.checkpoint | machinery | checkpoint (README 3e) |
| task_suspension.py | class | NativeTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | method | NativeTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| terminal_execution.py | class | TerminalExecutionBehavior | episode function | task.py (terminal(), exec_command, instructions, resource_information), messages/read_from_parent.py, messages/internal_summary.py, messages/final_to_parent.py |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function | settings read in task.py (resource, initial_information, coordinator_workspace); the explicit_execution_resources_required and initial_inventory_resource_not_bound checks have no counterpart: one resource, supplied as settings |
| terminal_execution.py | method | TerminalExecutionBehavior._operations | episode function | task.py terminal(settings) (TerminalExecution with terminal_artifact_paths) |
| terminal_execution.py | method | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py decide (terminal.validate_assignment) |
| terminal_execution.py | method | TerminalExecutionBehavior._state_directory | machinery | location of the file-backed practical state (PracticalState) |
| terminal_execution.py | method | TerminalExecutionBehavior.initialize | machinery | creates the file-backed PracticalState with the initial validations; the initial validations are messages/internal_summary.py |
| terminal_execution.py | method | TerminalExecutionBehavior.state | machinery | returns the file-backed PracticalState |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit_kind 'operational' (README 3d: deleted) |
| terminal_execution.py | method | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py selection_schema / action (tool only) |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_execution.py | method | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide (execution_resource.inventory_snapshot from settings initial_information) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_information | episode function | task.py resource_information(settings) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_instructions | episode function | task.py decide (LaunchInstructions.for_resource of the configured resource) |
| terminal_execution.py | method | TerminalExecutionBehavior.instructions | episode function | task.py INSTRUCTIONS and instructions() |
| terminal_execution.py | method | TerminalExecutionBehavior.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| terminal_execution.py | method | TerminalExecutionBehavior.catalog | episode function | task.py operation_catalog (EXEC_COMMAND) |
| terminal_execution.py | method | TerminalExecutionBehavior.execute | episode function | task.py exec_command (tool); the begin/finish intent ledger is the system's attempts journal; run_command is BLOCKED-ON-JOB-SERVICE |
| terminal_execution.py | method | TerminalExecutionBehavior.completion_for_action | machinery | per-action completion proof as a controller packet (README 3d) |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator(verify_completion) (README 7b): the completion controller in yield_estimator.py |
| terminal_execution.py | method | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | method | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py facts (receipts published by their own units, not at the report) |
| terminal_execution.py | method | TerminalExecutionBehavior.resolve | machinery | resolver of report-form references (receipt digests, PracticalReceiptInformation sources); held-ness is records.holds and the system admits the result |
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; the validate_form step is a contract misfit) |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | class | NativeParentReturns | episode function | messages/final_to_parent.py RETURN_FORM / facts / validate_report |
| to_parent.py | method | NativeParentReturns.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM: returned no required source here (an empty tuple) |
| to_parent.py | method | NativeParentReturns.facts | episode function | messages/final_to_parent.py facts (the closed-credit facts are machinery) |
| to_parent.py | method | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py facts (handoff refs, empty result and native families, execution_completed); bvbrc_appservice_support_refs and the adapter-conditional families are not carried (contract_misfits) |
| to_parent.py | method | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; adapter received-report checks belong to result acquisition; the validate_form step is a contract misfit) |
| waiting.py | function | perform_selected_native_wait | machinery | wait machinery (perform_selected_wait); this episode has no wait |
| work_operations.py | class | NativeWorkOperations | episode function | task.py TOOLS / exec_command |
| work_operations.py | method | NativeWorkOperations.catalog | episode function | task.py operation_catalog |
| work_operations.py | method | NativeWorkOperations.execute | episode function | task.py exec_command (the _check_parent_inputs re-validation before every command is unplaced) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (the practical_assignment_v1 branch; the API versions it also classified are the API sibling's) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, execution_original_task_yield_profile_required) |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (require_private_yield has no meaning: the profile is always required) |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController from the profile cutoff and the commissioned target) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator delegate (README 7b) |
