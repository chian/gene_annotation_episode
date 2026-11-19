# A107 `partner_presence_evidence/hpc_work_planning/execution_job_submission/local_job_execution` (launch_local)

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_job_submission/local_job_execution/<file>`, 29 files. It has no `grading/`, `scoring/` or child folders.

Old internal names: the class is `ExecutionEpisode`, assembled from the mixins `Native*`. The role is `launch_local`. The binding path is `.../execution_job_submission/local_job_execution`, commissioned by `.../execution_job_submission`. The version is `execution_episode_v1`.

## Purpose (its own words)

The goal text comes from `terminal_execution.TerminalExecutionBehavior.instructions`; `goal.py` delegates to it:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget.

After this text it adds "Resource instructions supplied from the frozen library:" followed by the sections that `launch_instructions.for_resource(<resource configuration>)` selects for this resource.

This episode runs one concrete job on a local resource. The model writes and runs shell commands until the requested endpoint (`usable_handoff` or `completed_job_outputs`) is validated.

## Task and instructions

- `replaces_default_instructions = True`; the text above is the whole goal.
- `task_instructions.py` appends tool knowledge, the launch instruction library and the pending-child redelivery repair text. It also applies the decision-exchange history replacement.
- There is no reasoning-commit text and no wait text, because the only permitted action is `tool`.
- Prompt rendering (`presentation.present_context`) uses the same renderer chain as the launch parent, reached through the old `providers` module.

## What it reads from its parent's assignment

The assignment is a single concrete practical request: `assignment_schema(role)` is anyOf the `_request_schema(resource_id, selected=True)` of every configured resource whose kind is `local`. Each schema is `ASSIGNMENT_SCHEMA` with:

- `resource_id` const and `resource_kind` const `local`;
- `requested_job` anyOf: the generic job, plus that resource's native job alternatives (BLAST family, HMMER, NMF, RNA structure, Infernal, preparation).

The terminal behaviour also reads `workspace`, `initial_context` and `endpoint`.

`prepare_assignment` checks, in order:

1. `_validate_request`.
2. The request kind equals the resource kind.
3. The parent role is `launch` (`resource_child_role_owned_by_launch`).
4. It re-validates the parent's launch assignment, masking and utility inputs, input versions, and the BLAST-database, standard-BLAST and RNA-structure inputs.

`science._check_parent_inputs` runs at initialisation and before every tool action. It re-reads the parent launch's recorded `episode_assignment` and validates this child's assignment against it.

## Children it may commission

None. `child_roles` and `allowed_children` both return `()`.

## Decision state shown to the model

The terminal behaviour's `decision_context`:

- `execution_assignment`;
- `execution_resource`: resource_kind, workspace, kind/policy/account/ssh_argv/python_executable/scheduler, and `inventory_snapshot`;
- `coordinator_workspace`;
- `execution_progress` (`state.credit_view()`);
- `execution_completion` (`completion_proof()`).

`initial_decision_context` adds `execution_resource_information`. `internal_summary._with_selected_execution_task` adds `selected_execution_task` (`selected_execution_task_v1`), which holds the scientific question, the selected tool info and the one request's job view. The view exists only for the supported native families; HMMER and NMF jobs are shown through their scientific views.

## Tools it offers

- `operation_catalog('local')`: the exec_command-style terminal operations. The arguments include `target` (resource|coordinator), `workdir` and `env`.
- Each call is checked against the catalog schema and `TerminalExecution.validate_action`.
- `PracticalState.begin/finish` records the command intent and receipt. A replayed completed intent returns its saved receipt.
- Outcomes go through `finalize_scientific_command`.
- Each receipt is published as a `practical_receipt` record ref.
- Invalid arguments return an `invalid` outcome with `arguments_or_reference` feedback. Execution exceptions become a `native_outcome.failure` (`execution_action_failed`).
- The only action is `tool`.

## How its credit is counted

- Credit kind is `operational`.
- Live credit is `TerminalExecutionBehavior.credit_view` = `PracticalState.credit_view()`: the operational credit recorded for its own command receipts and validations.
- The closed-credit snapshot (`execution_closed_operational_credit_v1`) is returned unchanged after closing. Credit is never bounded.

## Continuation (yield estimator and settings)

`yield_estimator._launch_local_yield_controller` uses `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`.

- The profile key is `launch_local:<request yield class>`, for example `practical_local_native_blast_handoff` or `practical_local_outputs`. The key must exist in `task_yield_profiles` (`{cutoff, parameters}`).
- A private yield binding is required.
- Completion uses the terminal state's completion proof for this operation key. A verified proof gives exact zero future gain. A closed episode reuses a verdict only if exactly one recorded observation carries it.
- In the new layout this maps to the "completion with a target" estimator (the target is the validated endpoint), with the profile's cutoff/parameters as settings.

## What it reports to its parent

- An empty list for every native family fact source (same set as the launch).
- The terminal facts `practical_completed`, `practical_receipt_digests` and `practical_receipt_refs`. `fact_sources` declares their meanings and the `practical_receipt` reference schema.
- `execution_handoff_refs`: received handoffs plus its own practical receipts that read as returnable handoffs for this assignment.
- `bvbrc_appservice_support_refs`, when bound.
- `execution_blast_hsps` = [].
- `execution_result_refs`, `execution_file_source_refs`, `execution_file_capture_outcomes` and `execution_result_origin`.
- `execution_completed` = `practical_completed`.
- The closed credit facts.

`validate_report` is the same as the launch parent's. `required_return_sources` returns `()`; the head-return requirement is a dead `pass`.

## Differences from siblings and similar episodes

- **vs `hpc_job_execution`.** The files are byte-identical except for:
  - role and binding path;
  - the yield profile prefix;
  - `internal_summary` (HPC omits `selected_execution_task`);
  - `from_parent.child_assignment_schema` (HPC freezes the assignment under an `hpc` ancestor).
- **vs `api_job_execution`.** The API child has its own goal text, permits `wait` for service assignments, and delegates credit, completion, facts and state to `api_execution` instead of the terminal behaviour. It also adds the BLAST graded-request checks.
- **vs the launch parent.** `configuration.py` and `resource_information.py` are copies of the launch versions, and `terminal_execution.py` is a reformatted superset of the launch copy (it adds `as_record`, `instructions`, `decision_context` and the binding stubs).
- **vs A101.** The A101 resource children carry BLAST axis summaries and return contracts that this one lacks.

## File by file

Old-runner names are counted per file as `name(uses)`. `workflow.X` stands for `self.workflow.X`, `source.workflow.X` or `workflow.X` on the old runner object. `runtime_*` are journal/receipt table names. `root.a107.<module>` entries are imports of old-runner modules. `catalog.*` is the old received-information catalog. Imports of old shared-root support modules (`root.a107.execution_contracts`, `a107_execution_bindings`, `native_*`, `library/*` and others) are not listed as old-runner names; the support code they named is now placed under `episode_support/`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding identity `.../execution_job_submission/local_job_execution`, version `execution_episode_v1`, same recorded configuration fields as the launch parent. | none |
| `completion.py` | 51 | Completion delegated to the resource terminal behaviour (`completion_proof` for this operation key); verification first reuses a recorded closed verdict (exact-zero next gain), else `PracticalState.verify_completion`. | ESTIMATOR_VERSION(2), NumericBand(2), root.a107.episode_return_records(1), root.a107.method_loop.identities(1), root.a107.numerical(1), root.a107.practical_yield(1), runtime_observations(1), UnitRef(2) |
| `configuration.py` | 119 | Identical copy of the launch configuration (resources, units, log selection, yield profiles, native families, readers). | root.a107.numerical(1), YieldController(3), YieldParameters(3) |
| `credit.py` | 136 | Credit kind `operational`; live credit = the terminal behaviour's `state.credit_view()` (operational credit earned by its practical command receipts); after closing the recorded closed view is returned unchanged. | EpisodeReceipts(2), EpisodeReturnRecords(2), root.a107.episode_receipts(1), root.a107.episode_return_records(3), runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2) |
| `episode.py` | 103 | roles ('launch_local',); commissioned by `.../execution_job_submission`; replaces default instructions; no children; permitted actions ('tool',) only. | root.a107.communication(1), root.a107.runtime(1) |
| `execution_contracts.py` | 57 | Local copy of shared constants (VERSION, LAUNCH/RESULTS versions, RESULT_PROVIDER, closed-credit key, ROLES, KINDS, ROLE_KINDS, schema atoms, NATIVE_RESULT_ORIGIN, native result operation catalog) and re-exports. | root.a107.communication(1) |
| `from_parent.py` | 113 | Assignment schema = anyOf the concrete request schemas of configured resources whose kind is local (resource_id required). Preparation requires parent role `launch`, re-validates the parent launch assignment, masking/utility inputs, immutable input versions, BLAST-database / standard-BLAST / RNA-structure inputs; request kind must equal the resource kind. | none |
| `goal.py` | 6 | Goal/instructions delegated to the terminal behaviour (`TerminalExecutionBehavior.instructions`, quoted below). | none |
| `initial_information.py` | 9 | Initial information from its own declared readers (binding path local_job_execution). | catalog.readers(1) |
| `internal_summary.py` | 88 | Decision context = terminal behaviour context (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion) plus `selected_execution_task` (scientific question, selected tool info, this one request's job view for supported native families; ebi_hmmer only for API). | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.json(2), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), root.a107.runtime(6), runtime_actions(2), workflow.binding_context(1), workflow.catalog(1), workflow.controller_binding(1), workflow.delivery_status(1), workflow.extra_report_sources(1), workflow.job_episode_options(1), workflow.journal(3), workflow.knowledge(1), workflow.local_outcome_preview(1), workflow.pending_work(1), workflow.run_id(1), workflow.source_credit_binding(1), workflow.source_credit_view(1), workflow.specialist(1), workflow.store(3), workflow.tools(1), workflow.working_state(1) |
| `presentation.py` | 74 | Prompt renderer selection (same predicates and renderers as the launch parent, reached through the old providers module). | _live_original_providers.apply_state_frame(3), _live_original_providers.DECISION_CONTEXT_VERSION(2), _live_original_providers.deepcopy(1), _live_original_providers.infernal_receiver_context(1), _live_original_providers.is_api_launch_context(2), _live_original_providers.is_published_scientific_context(2), _live_original_providers.json(1), _live_original_providers._ordinary_runtime_receiver_context(1), _live_original_providers.render_api_launch_prompt(1), _live_original_providers.render_partner_presence_evidence_prompt(1), _live_original_providers._rna_comparison_receiver_context(3), _live_original_providers.text_instructions(1), root.a107.decision_context(1) |
| `received_api_reports.py` | 4 | Own declared API reader authority (binding path local_job_execution). | catalog.configured(1), catalog.received(1) |
| `received_execution_information.py` | 4 | Own declared result readers (binding path local_job_execution). | catalog.configured(1), catalog.received(1) |
| `received_records.py` | 127 | Which received records count (same as launch handoff_receipts) and initial references (role launch_local takes its own assignment's inputs; other resource roles none). | none |
| `resource_information.py` | 70 | Resource tool contracts per resource (same as launch); resource information and capabilities helpers. | none |
| `science.py` | 57 | Input checks (masking, utility, NMF, input versions); `_check_parent_inputs` re-reads the parent launch request and validates this child's assignment against it (`execution_original_launch_assignment_unavailable` otherwise). | runtime_episodes(1) |
| `state.py` | 19 | Initialise after the parent-input check; state delegated to the resource terminal behaviour. | none |
| `task.py` | 225 | Decision loop/action execution (old-runner); own bits: reasoning selections need non-empty commit content, grain = own role, wait through waiting.py. | _live_original_runtime.AcquisitionError(2), _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractError(1), _live_original_runtime.ContractInformationError(1), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime.Draft202012Validator(3), _live_original_runtime.EventTargetError(1), _live_original_runtime.inspect(1), _live_original_runtime._json(5), _live_original_runtime.json(8), _live_original_runtime.Mapping(3), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.SourceEnd(2), _live_original_runtime.sqlite3(2), _live_original_runtime.subprocess(2), _live_original_runtime.validate_form(1), _live_original_runtime.ValidationError(3), _live_original_runtime._wait_target_feedback(1), _live_original_runtime.WorkflowError(2), root.a107.episode_source_failure(1), root.a107.providers(1), root.a107.runtime(1), runtime_actions(8), runtime_episodes(1), runtime_model_calls(2), workflow.action_schema(1), workflow.automatic_score_updates(1), workflow.binding_context(2), workflow.completed_unit(3), workflow.completions(3), workflow.controller_value(2), workflow.decision_exchanges(3), workflow.delivery_resolution_inputs(1), workflow.execute(1), workflow.execution_binding(7), workflow.inprocess_replay(4), workflow.journal(7), workflow.last_observed_credit(1), workflow.next_return(1), workflow.pending_work(1), workflow.permits_common_action(1), workflow.reasoning_action_schema(1), workflow.receive_native_outcome(1), workflow.receive_outcome(1), workflow.resolve_pending_deliveries(1), workflow.resolver(1), workflow.retain_shared_grading_results(1), workflow.run_id(3), workflow.selected(3), workflow.source_credit_view(1), workflow.specialist(2), workflow.store(9), workflow.validate_report(1) |
| `task_decision.py` | 357 | Model call machinery (old-runner); own bits: execution_expectations captured for its own role; job-source resource estimates. | _live_original_runtime._action_generation_schema(2), _live_original_runtime.apply_state_frame(1), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._category_yield_parameters(1), _live_original_runtime.child_option_information(2), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime._digest(1), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.infernal_receiver_context(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime._json(14), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.Mapping(4), _live_original_runtime.model_snapshot(2), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime.yield_table(1), root.a107.episode_work_report(2), root.a107.providers(1), root.a107.runtime(1), runtime_model_calls(8), workflow.available_child_roles(1), workflow.binding_context(1), workflow.contract_information_profile(1), workflow.contract_information_reply(1), workflow.controller_binding(1), workflow.decision_exchanges(4), workflow.decision_protocol(3), workflow.episode_bindings(1), workflow.execute(1), workflow.execution_expectations(1), workflow.freeze_contract_information(1), workflow.freeze_literature_numerical_contracts(1), workflow.history_preview(1), workflow.is_job_source(3), workflow.job_episodes(2), workflow.journal(3), workflow.launch_instructions(2), workflow.native_estimation_context(1), workflow.numerical_contracts(1), workflow.pending_work(1), workflow.provider(3), workflow.receipts(4), workflow.resource_context(1), workflow.resource_estimator(5), workflow.run_id(1), workflow.services(2), workflow.shared_information_context(1), workflow.specialist(1), workflow.store(2), workflow.uses_received_record_context(2), workflow.validate_contract_information(5) |
| `task_instructions.py` | 20 | Instruction composition: own instructions replace default; tool knowledge, launch library, redelivery repair text; no reasoning or wait text (tool-only episode). | _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL(1), _live_original_runtime_prompt.INSTRUCTIONS(4), workflow.binding_context(1), workflow.decision_protocol(1), workflow.is_job_source(1), workflow.job_episodes(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.specialist(1) |
| `task_report.py` | 22 | Finish/report delivery (old-runner machinery only). | _live_original_runtime.form_with_facts(1), _live_original_runtime._json(2), _live_original_runtime.json(1), _live_original_runtime.Record(2), root.a107.runtime(1), runtime_forms(2), workflow.binding_context(1), workflow.episode_bindings(1), workflow.facts(1), workflow.journal(2), workflow.pending_handles(1), workflow.release(2), workflow.source_credit_view(1) |
| `task_state.py` | 107 | Source state (old-runner machinery only; identical to launch). | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime._json(2), _live_original_runtime.json(4), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.Record(1), root.a107.episode_source_failure(1), root.a107.runtime(1), runtime_actions(5), workflow.archive(1), workflow.completions(4), workflow.context(1), workflow.controller_value(1), workflow.execution_binding(4), workflow.grains(1), workflow.inprocess_replay(7), workflow.journal(5), workflow.progress_provider(2), workflow.recover_commissions(1), workflow.run_id(1), workflow.source_credit_view(1), workflow.store(2) |
| `task_suspension.py` | 8 | Suspension forwarding (old-runner only). | workflow.execution_backend(1), workflow.execution_handle(2) |
| `terminal_execution.py` | 226 | The execution-agent behaviour: exec_command catalog per resource kind, instruction text (quoted below), decision context, state directory `practical-execution/<digest(run_id, episode_id)>`, receipts published as practical_receipt refs, completion proof, practical facts, credit view. Byte-identical in the three resource children. | PracticalYieldEstimator(2), root.a107.communication(1), root.a107.practical_yield(1) |
| `to_parent.py` | 100 | Report facts = native empty sources + terminal practical facts (`practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`) + `execution_handoff_refs` (received handoffs plus own practical receipts that are returnable handoffs) + result/file/origin facts + `execution_completed` = practical_completed. Report validation same as launch. No required return sources. | none |
| `waiting.py` | 10 | Selected wait through the old runner, failure turned into a failed outcome. | _live_original_runtime.EventTargetError(1), _live_original_runtime._wait_target_feedback(1), root.a107.runtime(1), workflow.perform_selected_wait(1) |
| `work_operations.py` | 35 | Tools = the terminal behaviour's catalog; execute checks parent inputs, then runs the selected command through the terminal behaviour. | none |
| `yield_estimator.py` | 50 | Continuation: profile `launch_local:<request yield class>` from task_yield_profiles; `YieldController(cutoff, parameters)` with the practical completion estimator (exact zero after verified completion). | PracticalYieldEstimator(2), root.a107.numerical(1), root.a107.practical_yield(1), YieldController(2), YieldParameters(2) |

## Old-runner names, totals for this episode

`_live_original_runtime._json`(23), `workflow.journal`(20), `_live_original_runtime.json`(18), `_live_original_runtime.WorkflowError`(16), `workflow.store`(16), `runtime_actions`(15), `root.a107.runtime`(12), `workflow.execution_binding`(11), `workflow.inprocess_replay`(11), `_live_original_runtime.Mapping`(10), `runtime_model_calls`(10), `_live_original_runtime.ValidationError`(8), `workflow.completions`(7), `workflow.decision_exchanges`(7), `workflow.binding_context`(6), `workflow.run_id`(6), `_live_original_runtime.DECISION_EXCHANGE_PROTOCOL`(5), `_live_original_runtime.nullcontext`(5), `_live_original_runtime._plain`(5), `runtime_forms`(5), `workflow.resource_estimator`(5), `workflow.specialist`(5), `workflow.validate_contract_information`(5), `YieldController`(5), `YieldParameters`(5), `_live_original_runtime.Draft202012Validator`(4), `_live_original_runtime.instructional_model_context`(4), `_live_original_runtime._object`(4), `_live_original_runtime_prompt.INSTRUCTIONS`(4), `PracticalYieldEstimator`(4), `root.a107.episode_return_records`(4), `runtime_episodes`(4), `workflow.decision_protocol`(4), `workflow.is_job_source`(4), `workflow.receipts`(4), `workflow.source_credit_view`(4), `_live_original_providers.apply_state_frame`(3), `_live_original_providers._rna_comparison_receiver_context`(3), `_live_original_runtime.Record`(3), `_live_original_runtime.schema_failure_diagnostic`(3), `_live_original_runtime.sqlite3`(3), `root.a107.communication`(3), `root.a107.numerical`(3), `root.a107.practical_yield`(3), `workflow.completed_unit`(3), `workflow.controller_value`(3), `workflow.job_episodes`(3), `workflow.launch_instructions`(3), `workflow.pending_work`(3), `workflow.provider`(3), `workflow.selected`(3), `catalog.configured`(2), `catalog.received`(2), `EpisodeReceipts`(2), `EpisodeReturnRecords`(2), `ESTIMATOR_VERSION`(2), `_live_original_providers.DECISION_CONTEXT_VERSION`(2), `_live_original_providers.is_api_launch_context`(2), `_live_original_providers.is_published_scientific_context`(2), `_live_original_runtime.AcquisitionError`(2), `_live_original_runtime._action_generation_schema`(2), `_live_original_runtime.child_option_information`(2), `_live_original_runtime.composition_lookup_schema`(2), `_live_original_runtime.DECISION_CONTEXT_VERSION`(2), `_live_original_runtime.EventTargetError`(2), `_live_original_runtime.infernal_receiver_context`(2), `_live_original_runtime.model_snapshot`(2), `_live_original_runtime._references_in`(2), `_live_original_runtime.ReportRedelivery`(2), `_live_original_runtime.requested_contract_information`(2), `_live_original_runtime.SourceEnd`(2), `_live_original_runtime.subprocess`(2), `_live_original_runtime._wait_target_feedback`(2), `NumericBand`(2), `root.a107.episode_source_failure`(2), `root.a107.episode_work_report`(2), `root.a107.providers`(2), `runtime_observations`(2), `runtime_receipt_inheritance`(2), `runtime_record_receipts`(2), `UnitRef`(2), `workflow.controller_binding`(2), `workflow.episode_bindings`(2), `workflow.execute`(2), `workflow.execution_handle`(2), `workflow.knowledge`(2), `workflow.progress_provider`(2), `workflow.release`(2), `workflow.services`(2), `workflow.uses_received_record_context`(2), `catalog.readers`(1), `_live_original_providers.deepcopy`(1), `_live_original_providers.infernal_receiver_context`(1), `_live_original_providers.json`(1), `_live_original_providers._ordinary_runtime_receiver_context`(1), `_live_original_providers.render_api_launch_prompt`(1), `_live_original_providers.render_partner_presence_evidence_prompt`(1), `_live_original_providers.text_instructions`(1), `_live_original_runtime.ActionFailure`(1), `_live_original_runtime.ActionLeaf`(1), `_live_original_runtime.apply_state_frame`(1), `_live_original_runtime._ASSIGNMENT_TRANSPORT`(1), `_live_original_runtime._category_yield_parameters`(1), `_live_original_runtime.ContractError`(1), `_live_original_runtime.ContractInformationError`(1), `_live_original_runtime.CONTRACT_INFORMATION_OPERATIONS`(1), `_live_original_runtime._decode_recorded_action_response`(1), `_live_original_runtime._digest`(1), `_live_original_runtime.EFFECT_VERSION`(1), `_live_original_runtime.Episode`(1), `_live_original_runtime.FACT_MEANINGS`(1), `_live_original_runtime.FACT_SOURCES`(1), `_live_original_runtime.form_with_facts`(1), `_live_original_runtime.inspect`(1), `_live_original_runtime.interpretation_schema`(1), `_live_original_runtime.is_contract_information`(1), `_live_original_runtime.lookup_attempts`(1), `_live_original_runtime.observes_action_outcome`(1), `_live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL`(1), `_live_original_runtime._recorded_action_generation_schema`(1), `_live_original_runtime._recorded_assignment_transport`(1), `_live_original_runtime.ReportBoundaryError`(1), `_live_original_runtime.state_frame`(1), `_live_original_runtime.validate_form`(1), `_live_original_runtime.yield_table`(1), `root.a107.decision_context`(1), `root.a107.episode_receipts`(1), `root.a107.method_loop.identities`(1), `workflow.action_schema`(1), `workflow.archive`(1), `workflow.automatic_score_updates`(1), `workflow.available_child_roles`(1), `workflow.catalog`(1), `workflow.context`(1), `workflow.contract_information_profile`(1), `workflow.contract_information_reply`(1), `workflow.delivery_resolution_inputs`(1), `workflow.delivery_status`(1), `workflow.execution_backend`(1), `workflow.execution_expectations`(1), `workflow.extra_report_sources`(1), `workflow.facts`(1), `workflow.freeze_contract_information`(1), `workflow.freeze_literature_numerical_contracts`(1), `workflow.grains`(1), `workflow.history_preview`(1), `workflow.job_episode_options`(1), `workflow.last_observed_credit`(1), `workflow.local_outcome_preview`(1), `workflow.native_estimation_context`(1), `workflow.native_event_information`(1), `workflow.next_return`(1), `workflow.numerical_contracts`(1), `workflow.pending_handles`(1), `workflow.perform_selected_wait`(1), `workflow.permits_common_action`(1), `workflow.reasoning_action_schema`(1), `workflow.receive_native_outcome`(1), `workflow.receive_outcome`(1), `workflow.recover_commissions`(1), `workflow.resolve_pending_deliveries`(1), `workflow.resolver`(1), `workflow.resource_context`(1), `workflow.retain_shared_grading_results`(1), `workflow.shared_information_context`(1), `workflow.source_credit_binding`(1), `workflow.tools`(1), `workflow.validate_report`(1), `workflow.working_state`(1)

Every row (name, episode, file, uses, purpose) is in `runs/carry_over/calls/a107_03.tsv`.

## Carried over

Carried 19 November 2026 into the ten-file form (no children: no msg_to_child.py or read_from_child.py). One row per old function, class and method (`runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__execution_job_submission__local_job_execution.tsv`). "library candidate": the function stays in the episode file that uses it. Machinery is not carried (reason given). A function marked unplaced is listed with its reason in `carry_over_blocked/a107__partner_presence_evidence__hpc_work_planning__execution_job_submission__local_job_execution.md`.

| old file | name | kind | class | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | NativeBindingRecord | class | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| binding_record.py | NativeBindingRecord.as_record | method | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| completion.py | NativeCompletion | class | machinery | class shell |
| completion.py | NativeCompletion.completion_for_action | method | machinery | completion proof as a controller packet (not a controller input in the new system; the proof is read in messages/internal_summary.py::_completion) |
| completion.py | NativeCompletion._closed_completion_verdict | method | machinery | re-reads runtime_observations of the old journal (README 3d: reading earlier controller records) |
| completion.py | NativeCompletion.verify_completion | method | episode function | messages/internal_summary.py::_completion (the verified completion of the assignment's endpoint over the held receipts); library candidate |
| configuration.py | NativeConfiguration | class | machinery | NativeConfiguration.__init__ values are the run's settings (ctx.settings / settings: resources, initial_information, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles; read in task.py and yield_estimator.py); the constructed adapters (native result readers and returns, api_execution, job_progress_provider, local_file_sources) serve the results role and old-runner wiring; YieldController/YieldParameters construction replaced by yield_estimator.py |
| configuration.py | NativeConfiguration.__init__ | method | machinery | NativeConfiguration.__init__ values are the run's settings (ctx.settings / settings: resources, initial_information, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles; read in task.py and yield_estimator.py); the constructed adapters (native result readers and returns, api_execution, job_progress_provider, local_file_sources) serve the results role and old-runner wiring; YieldController/YieldParameters construction replaced by yield_estimator.py |
| credit.py | ExecutionEpisodeCredit | class | machinery | class shell |
| credit.py | ExecutionEpisodeCredit.credit_kind | method | machinery | credit kind label 'operational' of the old credit view (README 3d: credit_kind is deleted) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | method | machinery | closed credit view rebuilt from runtime_episodes and EpisodeReturnRecords of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | method | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | method | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | method | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | method | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run |
| credit.py | ExecutionEpisodeCredit.project_credit | method | episode function | credit.py::credit |
| credit.py | ExecutionEpisodeCredit._live_project_credit | method | episode function | credit.py::credit (library episode_support/grading/partner_presence_evidence/practical_execution_credit.py::project_practical_credit) |
| credit.py | ExecutionEpisodeCredit.credit_view | method | episode function | credit.py::credit |
| episode.py | ExecutionEpisode | class | episode function | episode.py::LocalJobExecution |
| episode.py | ExecutionEpisode.child_roles | method | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | method | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | method | machinery | the old loop's permitted common actions ('tool',): the system's decide/action produce only tool or child units |
| execution_contracts.py | native_result_operation_catalog | function | episode function | not this episode's: the catalogue of the 'results' role; not carried here, see unplaced_old_functions |
| from_parent.py | NativeParentRequests | class | episode function | messages/read_from_parent.py (class shell) |
| from_parent.py | NativeParentRequests._permitted | method | episode function | not this episode's: resource permission test of the parent launch's requests (role launch); not carried, see unplaced_old_functions |
| from_parent.py | NativeParentRequests._request_schema | method | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (one field per property of ASSIGNMENT_SCHEMA; the requested_job alternatives are validated by validate_assignment and TerminalExecution.validate_assignment) |
| from_parent.py | NativeParentRequests._launch | method | machinery | re-validation of the commissioner's launch contract (execution_launch_assignment_v1); the parent's assignment is passed in custody, no re-read of the old runtime_episodes table |
| from_parent.py | NativeParentRequests._constraints | method | machinery | part of the launch contract re-validation (_launch) |
| from_parent.py | NativeParentRequests.child_assignment_schema | method | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | NativeParentRequests.assignment_schema | method | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | NativeParentRequests.prepare_assignment | method | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment); the masking, utility, input-version and native job input checks of the commissioner are unplaced (modules in no library location, and a check of a commission is not added) |
| goal.py | NativeGoal | class | episode function | goal.py (GOAL, UNIT, RESULT) and task.py::GOAL_INSTRUCTION |
| goal.py | NativeGoal.instructions | method | episode function | task.py::GOAL_INSTRUCTION and task.py::_instructions |
| initial_information.py | initial_information | function | episode function | task.py::decide (context keys execution_initial_information and execution_resource_information from settings); the old library presentation module (library.execution_initial_information.presentation) is in no library location |
| internal_summary.py | native_decision_snapshot | function | machinery | old decision-state snapshot over the journal, workflow store and credit view; replaced by messages/internal_summary.py::internal_summary |
| internal_summary.py | NativeInternalSummary | class | episode function | messages/internal_summary.py (class shell) |
| internal_summary.py | NativeInternalSummary._with_selected_execution_task | method | episode function | messages/internal_summary.py::_selected_execution_task (the resource of each request is added in task.py::decide); the scientific job views of native_hmmer, native_hmmer_preparation and native_expression_nmf raise (unplaced) |
| internal_summary.py | NativeInternalSummary.decision_context | method | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| presentation.py | present_context | function | episode function | task.py::_task_text and task.py::decide (the selected-execution prompt over the summary); the renderer dispatch over the old provider state frames is machinery |
| received_api_reports.py | received_api_reports | function | machinery | hook that selects the recipient's API reader authority for the old received-report catalog (old receiving-context machinery) |
| received_execution_information.py | received_execution_information | function | machinery | hook that selects the recipient's result reader authority for the old received-information catalog (old receiving-context machinery) |
| received_records.py | NativeReceivedRecords | class | machinery | class shell of the old received-record context (custody replaces it) |
| received_records.py | NativeReceivedRecords._context_target | method | machinery | reads authenticated handoffs of the old receipt ledger and the old job progress provider (receipts bookkeeping); custody replaces it |
| received_records.py | NativeReceivedRecords._received | method | machinery | reads the old receipt ledger of received references (README 3b R3); custody replaces it |
| received_records.py | NativeReceivedRecords.initial_references | method | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM field record_refs (the records the job inputs name travel in custody); the rna structure, masking, utility and expression input validations are unplaced (commission checks, modules in no library location) |
| resource_information.py | NativeResourceInformation | class | episode function | task.py::_resource and task.py::_capabilities (the resource information of this episode's resource) |
| resource_information.py | NativeResourceInformation.resource_tool_contracts | method | episode function | not this episode's: the declared operations over every bound resource for the parent's catalogue; not carried, see unplaced_old_functions |
| science.py | NativeScienceInputs | class | machinery | class shell |
| science.py | NativeScienceInputs._masking_inputs | method | episode function | unplaced: input check of the commissioner's masking inputs (module not in a library location; a check of a commission); the records travel in the record_refs field of the assignment |
| science.py | NativeScienceInputs._utility_inputs | method | episode function | unplaced: input check of the commissioner's utility inputs (module not in a library location; a check of a commission) |
| science.py | NativeScienceInputs._expression_nmf_inputs | method | episode function | unplaced: input check of the commissioner's expression NMF inputs (expression_nmf_operands not in a library location; a check of a commission) |
| science.py | NativeScienceInputs._versions | method | episode function | unplaced: execution_input_versions.validate_execution_input_versions (no library module; a check of a commission) |
| science.py | NativeScienceInputs._check_parent_inputs | method | machinery | re-reads the parent launch's recorded episode_assignment from the old runtime_episodes table and re-validates it before every action (runtime_* table re-validation) |
| state.py | NativeState | class | machinery | class shell |
| state.py | NativeState.initialize | method | machinery | practical state initialisation of the old PracticalState files (state.begin/finish, receipts bookkeeping); the system's attempts journal and ctx.operation_key replace it |
| state.py | NativeState.state | method | machinery | the old practical state handle (PracticalState begin/finish ledger); the receipts are in the unit outcomes and read through messages/internal_summary.py |
| task.py | NativeTask | class | machinery | class shell of the old decision machine |
| task.py | NativeTask.next | method | machinery | old decision loop (journal row lookups, inprocess replay, completions slots, model call, SourceEnd, redelivery resolution); the system's loop with task.py::decide and ::action replaces it |
| task.py | NativeTask.apply_response | method | episode function | task.py::action (validation of the answer against the tool schema and the resource); report_update / report_form handling, ReportRedelivery and the rejection bookkeeping of the old loop are machinery |
| task.py | NativeTask.execute | method | episode function | task.py::exec_command (the tool: one command through job_access); the runtime_actions journal rows, wait branch, automatic score updates, pending_work and the controller value are machinery |
| task_decision.py | NativeTaskDecision | class | machinery | class shell of the old decision-exchange loop |
| task_decision.py | NativeTaskDecision.call | method | episode function | task.py::decide (context keys launch_instruction_library and selected_launch_instructions; the resource, shared-information, child-option, planning, expectations, estimator and completed-work branches do not apply to launch_local); journal rows, protocol checks and the provider call are machinery |
| task_decision.py | NativeTaskDecision.instructions | method | machinery | delegation to services.instructions (task_instructions.instructions); the text is task.py::_instructions |
| task_decision.py | NativeTaskDecision.conversation_key | method | machinery | provider conversation key of the old decision loop |
| task_decision.py | NativeTaskDecision.interpretation_context | method | machinery | decision-exchange loop (visible record refs of the exchange) |
| task_decision.py | NativeTaskDecision.exchange_schema | method | machinery | decision-exchange loop (exchange_decision schema) |
| task_decision.py | NativeTaskDecision.exchange_response | method | machinery | decision-exchange loop (exchange_decision response) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_request | method | machinery | saved-request check of the decision exchange (README 3a: deleted) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_history | method | machinery | saved-request check of the decision exchange (README 3a: deleted) |
| task_decision.py | NativeTaskDecision.exchange_decision | method | episode function | task.py::knowledge_lookup and task.py::launch_instruction_lookup (the lookups the exchange served are tools); the exchange loop itself is machinery |
| task_decision.py | NativeTaskDecision.decision_completion | method | machinery | provider dispatch of the old decision loop |
| task_instructions.py | instructions | function | episode function | task.py::_instructions (the knowledge and launch-library instruction text is appended: KNOWLEDGE_INSTRUCTIONS and LAUNCH_INSTRUCTIONS); the pending-child redelivery repair text and the decision-exchange history replacement are machinery |
| task_report.py | NativeTaskReport | class | machinery | class shell of the old report delivery |
| task_report.py | NativeTaskReport.finish | method | machinery | report_form machinery: saved runtime_forms, form_with_facts, workflow.release (README 3b D1, D3); replaced by messages/final_to_parent.py::final_to_parent |
| task_state.py | NativeTaskState | class | machinery | class shell |
| task_state.py | NativeTaskState.__init__ | method | machinery | old decision-state fields (feedback, report_values, checkpoint flags) |
| task_state.py | NativeTaskState.bind_execution_context | method | machinery | old execution-context binding |
| task_state.py | NativeTaskState.record_execution_failure | method | machinery | record_execution_failure of the old action ledger (README 3c: a failed action is the tool's outcome) |
| task_state.py | NativeTaskState.restore_checkpoint | method | machinery | checkpoint/restore (README 3e) |
| task_state.py | NativeTaskState.restore | method | machinery | checkpoint/restore (README 3e) |
| task_state.py | NativeTaskState.record_effect | method | machinery | record_effect of the old action ledger (README 3e) |
| task_state.py | NativeTaskState.checkpoint | method | machinery | checkpoint/restore (README 3e) |
| task_suspension.py | NativeTaskSuspension | class | machinery | wait/suspension machinery |
| task_suspension.py | NativeTaskSuspension.suspension_changed | method | machinery | wait/suspension machinery |
| terminal_execution.py | TerminalExecutionBehavior | class | episode function | task.py (the episode's tool, decide and action) and messages/final_to_parent.py; class shell |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | method | machinery | values are the run's settings (resources, initial_information); the per-state dict self._states is old-runner state |
| terminal_execution.py | TerminalExecutionBehavior._operations | method | episode function | task.py::_operations (TerminalExecution over the configured resource, called by action; the library class TerminalExecution is episode_support/jobs/local_execution/partner_presence_evidence/terminal_execution.py) |
| terminal_execution.py | TerminalExecutionBehavior._assignment | method | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations (the resource's own validate_assignment) |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | method | machinery | the old PracticalState directory (host receipt location per run and episode); the system's attempts journal replaces it |
| terminal_execution.py | TerminalExecutionBehavior.initialize | method | machinery | PracticalState initialisation with the frozen initial validations; the baseline is computed in messages/internal_summary.py |
| terminal_execution.py | TerminalExecutionBehavior.state | method | machinery | the old PracticalState handle |
| terminal_execution.py | TerminalExecutionBehavior.as_record | method | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | method | episode function | task.py CHILD_SLOTS = {} (no children) |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | method | machinery | credit kind label 'operational' (README 3d: credit_kind is deleted) |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | method | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | method | machinery | the old loop's permitted common actions ('tool',) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | method | episode function | task.py CHILD_SLOTS = {} (no children) |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | method | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | method | episode function | task.py::decide (context key execution_resource_information) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | method | episode function | task.py::_resource |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | method | episode function | task.py::_instructions (LaunchInstructions.for_resource of the configured resource) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | method | episode function | task.py::GOAL_INSTRUCTION and task.py::_instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | method | episode function | messages/internal_summary.py::internal_summary (progress, completion) and task.py::decide (assignment, resource, coordinator workspace) |
| terminal_execution.py | TerminalExecutionBehavior.catalog | method | episode function | task.py::EXEC_COMMAND (the one general capability) and task.py::TOOLS |
| terminal_execution.py | TerminalExecutionBehavior.execute | method | episode function | task.py::exec_command (validation of the arguments is task.py::action; begin/finish of the PracticalState, finalize_scientific_command, the context update and assess_validations are the job_access service's exec_command: BLOCKED-ON-JOB-SERVICE); PracticalReceiptInformation.publish is BLOCKED-ON-STORE-ACCESS (the receipt is saved with ctx.store.artifact) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | method | machinery | completion proof as a controller packet (not a controller input in the new system) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | method | machinery | PracticalYieldEstimator (README 3d/7b: deleted; the completion controller of yield_estimator.py replaces it) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | method | episode function | messages/final_to_parent.py::RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | TerminalExecutionBehavior.facts | method | episode function | messages/final_to_parent.py::_facts and final_to_parent |
| terminal_execution.py | TerminalExecutionBehavior.resolve | method | machinery | reference resolver of the old report form (README 3b D2); custody replaces it |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | method | episode function | messages/final_to_parent.py::validate_report (the fact fields of the report equal the recorded facts; the validate_form call over the resolver is the old report-form machinery) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | method | episode function | credit.py::credit |
| to_parent.py | NativeParentReturns | class | episode function | messages/final_to_parent.py (class shell) |
| to_parent.py | NativeParentReturns.required_return_sources | method | machinery | returns () for this role (the required return sources of the old parent edge); credit and finding are always returned |
| to_parent.py | NativeParentReturns.facts | method | episode function | messages/final_to_parent.py::_facts and final_to_parent |
| to_parent.py | NativeParentReturns._live_facts | method | episode function | messages/final_to_parent.py::_facts and RETURN_FORM (the result family sources, handoff refs, result/file/hsp sources, execution_completed); the results of a launch are empty; the masking, utility and infernal family sources and execution_result_origin are unplaced (contract misfits) |
| to_parent.py | NativeParentReturns.validate_report | method | episode function | messages/final_to_parent.py::validate_report (the recorded-fact check); the result-family adapters' validate_received_report calls serve the results role |
| waiting.py | perform_selected_native_wait | function | machinery | wait machinery (perform_selected_wait): not carried |
| work_operations.py | NativeWorkOperations | class | episode function | task.py::TOOLS (class shell) |
| work_operations.py | NativeWorkOperations.catalog | method | episode function | task.py::EXEC_COMMAND and task.py::TOOLS |
| work_operations.py | NativeWorkOperations.execute | method | episode function | task.py::exec_command (the _check_parent_inputs call before every action is old-runner machinery) |
| yield_estimator.py | ExecutionEpisodeYield | class | machinery | class shell |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | method | episode function | yield_estimator.py::_request_yield_class (the practical_assignment_v1 branch; the API branch serves the api role); library candidate |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | method | episode function | yield_estimator.py::_task_yield_profile; library candidate |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | method | episode function | yield_estimator.py::yield_controller (CompletionYieldController, README 7b) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | method | episode function | yield_estimator.py::yield_controller (profile key launch_local:<yield class>) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | method | machinery | PracticalYieldEstimator (README 3d/7b: deleted) |
