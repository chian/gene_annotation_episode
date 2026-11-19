# A107 `partner_presence_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution` (launch_hpc)

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution/<file>`, 29 files. It has no `grading/`, `scoring/` or child folders.

Old internal names: the class is `ExecutionEpisode`, assembled from the mixins `Native*`. The role is `launch_hpc`. The binding path is `.../execution_job_submission/hpc_job_execution`, commissioned by `.../execution_job_submission`. The version is `execution_episode_v1`.

## Purpose (its own words)

The goal text comes from `terminal_execution.TerminalExecutionBehavior.instructions`; `goal.py` delegates to it:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget.

After this text it adds "Resource instructions supplied from the frozen library:" followed by the sections that `launch_instructions.for_resource(<resource configuration>)` selects for this resource.

This episode runs one concrete job on an HPC (`pbs_ssh`) resource, for example Aurora through the configured SSH transport. The model writes and runs shell commands until the requested endpoint (`usable_handoff` or `completed_job_outputs`) is validated.

## Task and instructions

- `replaces_default_instructions = True`; the text above is the whole goal.
- `task_instructions.py` appends tool knowledge, the launch instruction library and the pending-child redelivery repair text. It also applies the decision-exchange history replacement.
- There is no reasoning-commit text and no wait text, because the only permitted action is `tool`.
- Prompt rendering (`presentation.present_context`) uses the same renderer chain as the launch parent, reached through the old `providers` module.

## What it reads from its parent's assignment

The assignment is a single concrete practical request: `assignment_schema(role)` is anyOf the `_request_schema(resource_id, selected=True)` of every configured resource whose kind is `hpc` (`pbs_ssh`). Each schema is `ASSIGNMENT_SCHEMA` with:

- `resource_id` const and `resource_kind` const `hpc`;
- `requested_job` anyOf: the generic job, plus that resource's native job alternatives (BLAST family, HMMER, NMF, RNA structure, Infernal, preparation).

The terminal behaviour also reads `workspace`, `initial_context` and `endpoint`.

`prepare_assignment` checks, in order:

1. `_validate_request`.
2. The request kind equals the resource kind.
3. The parent role is `launch` (`resource_child_role_owned_by_launch`).
4. It re-validates the parent's launch assignment, masking and utility inputs, input versions, and the BLAST-database, standard-BLAST and RNA-structure inputs.

Own difference: `child_assignment_schema(parent, role)` freezes the assignment when the parent is `launch` and any ancestor role is `hpc`. The assignment must then be `{'type':'object','enum': <the parent's permitted requests with resource_kind hpc>}`, and the call raises `frozen_hpc_launch_request_missing` when there are none. Under HPC work planning, this child can only run a request the planner already authorised.

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

`initial_decision_context` adds `execution_resource_information`. Own difference: `internal_summary._with_selected_execution_task` returns the value unchanged. The HPC child shows no `selected_execution_task` view (the scientific question and job view that local and API add).

## Tools it offers

- `operation_catalog('hpc')`: the exec_command-style terminal operations. The arguments include `target` (resource|coordinator), `workdir` and `env`.
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

`yield_estimator._launch_hpc_yield_controller` uses `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`.

- The profile key is `launch_hpc:<request yield class>`, for example `practical_hpc_native_blast_handoff` or `practical_hpc_outputs`. The key must exist in `task_yield_profiles` (`{cutoff, parameters}`).
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

- **vs `local_job_execution`.** The files are byte-identical except for:
  - role and binding path;
  - the yield profile prefix;
  - `internal_summary` (this child omits `selected_execution_task`);
  - `from_parent.child_assignment_schema` (this child freezes the assignment under an `hpc` ancestor).
- **Configured native families.** The configuration rejects native NMF, RNA-structure, Infernal and Infernal-preparation families on non-local kinds (`..._resource_execution_binding_unfinished:hpc`). On HPC only the BLAST/HMMER-family native jobs and generic jobs can be configured.
- **vs `api_job_execution`.** The API child has its own goal text, permits `wait` for service assignments, and delegates credit, completion, facts and state to `api_execution` instead of the terminal behaviour. It also adds the BLAST graded-request checks.
- **vs the launch parent.** `configuration.py` and `resource_information.py` are copies of the launch versions, and `terminal_execution.py` is a reformatted superset of the launch copy (it adds `as_record`, `instructions`, `decision_context` and the binding stubs).
- **vs A101.** The A101 resource children carry BLAST axis summaries and return contracts that this one lacks.

## File by file

Old-runner names are counted per file as `name(uses)`. `workflow.X` stands for `self.workflow.X`, `source.workflow.X` or `workflow.X` on the old runner object. `runtime_*` are journal/receipt table names. `root.a107.<module>` entries are imports of old-runner modules. `catalog.*` is the old received-information catalog. Imports of old shared-root support modules (`root.a107.execution_contracts`, `a107_execution_bindings`, `native_*`, `library/*` and others) are not listed as old-runner names; the support code they named is now placed under `episode_support/`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding identity `.../execution_job_submission/hpc_job_execution`, version `execution_episode_v1`, same recorded configuration fields as the launch parent. | none |
| `completion.py` | 51 | Completion delegated to the resource terminal behaviour (`completion_proof` for this operation key); verification first reuses a recorded closed verdict (exact-zero next gain), else `PracticalState.verify_completion`. | ESTIMATOR_VERSION(2), NumericBand(2), root.a107.episode_return_records(1), root.a107.method_loop.identities(1), root.a107.numerical(1), root.a107.practical_yield(1), runtime_observations(1), UnitRef(2) |
| `configuration.py` | 119 | Identical copy of the launch configuration (resources, units, log selection, yield profiles, native families, readers). | root.a107.numerical(1), YieldController(3), YieldParameters(3) |
| `credit.py` | 136 | Credit kind `operational`; live credit = the terminal behaviour's `state.credit_view()` (operational credit earned by its practical command receipts); after closing the recorded closed view is returned unchanged. | EpisodeReceipts(2), EpisodeReturnRecords(2), root.a107.episode_receipts(1), root.a107.episode_return_records(3), runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2) |
| `episode.py` | 103 | roles ('launch_hpc',); commissioned by `.../execution_job_submission`; replaces default instructions; no children; permitted actions ('tool',) only. | root.a107.communication(1), root.a107.runtime(1) |
| `execution_contracts.py` | 57 | Local copy of shared constants (VERSION, LAUNCH/RESULTS versions, RESULT_PROVIDER, closed-credit key, ROLES, KINDS, ROLE_KINDS, schema atoms, NATIVE_RESULT_ORIGIN, native result operation catalog) and re-exports. | root.a107.communication(1) |
| `from_parent.py` | 117 | Assignment schema = anyOf the concrete request schemas of configured resources whose kind is hpc (resource_id required). Preparation requires parent role `launch`, re-validates the parent launch assignment, masking/utility inputs, immutable input versions, BLAST-database / standard-BLAST / RNA-structure inputs; request kind must equal the resource kind. Own difference: under an `hpc` ancestor the child assignment schema is frozen to an enum of the parent launch's permitted hpc requests (`frozen_hpc_launch_request_missing`). | none |
| `goal.py` | 6 | Goal/instructions delegated to the terminal behaviour (`TerminalExecutionBehavior.instructions`, quoted below). | none |
| `initial_information.py` | 9 | Initial information from its own declared readers (binding path hpc_job_execution). | catalog.readers(1) |
| `internal_summary.py` | 58 | Decision context = terminal behaviour context only; `_with_selected_execution_task` returns it unchanged (no selected_execution_task view, unlike local/api). | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.json(2), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), root.a107.runtime(6), runtime_actions(2), workflow.binding_context(1), workflow.catalog(1), workflow.controller_binding(1), workflow.delivery_status(1), workflow.extra_report_sources(1), workflow.job_episode_options(1), workflow.journal(3), workflow.knowledge(1), workflow.local_outcome_preview(1), workflow.pending_work(1), workflow.run_id(1), workflow.source_credit_binding(1), workflow.source_credit_view(1), workflow.specialist(1), workflow.store(3), workflow.tools(1), workflow.working_state(1) |
| `presentation.py` | 74 | Prompt renderer selection (same predicates and renderers as the launch parent, reached through the old providers module). | _live_original_providers.apply_state_frame(3), _live_original_providers.DECISION_CONTEXT_VERSION(2), _live_original_providers.deepcopy(1), _live_original_providers.infernal_receiver_context(1), _live_original_providers.is_api_launch_context(2), _live_original_providers.is_published_scientific_context(2), _live_original_providers.json(1), _live_original_providers._ordinary_runtime_receiver_context(1), _live_original_providers.render_api_launch_prompt(1), _live_original_providers.render_partner_presence_evidence_prompt(1), _live_original_providers._rna_comparison_receiver_context(3), _live_original_providers.text_instructions(1), root.a107.decision_context(1) |
| `received_api_reports.py` | 4 | Own declared API reader authority (binding path hpc_job_execution). | catalog.configured(1), catalog.received(1) |
| `received_execution_information.py` | 4 | Own declared result readers (binding path hpc_job_execution). | catalog.configured(1), catalog.received(1) |
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
| `yield_estimator.py` | 50 | Continuation: profile `launch_hpc:<request yield class>` from task_yield_profiles; `YieldController(cutoff, parameters)` with the practical completion estimator (exact zero after verified completion). | PracticalYieldEstimator(2), root.a107.numerical(1), root.a107.practical_yield(1), YieldController(2), YieldParameters(2) |

## Old-runner names, totals for this episode

`_live_original_runtime._json`(23), `workflow.journal`(20), `_live_original_runtime.json`(18), `_live_original_runtime.WorkflowError`(16), `workflow.store`(16), `runtime_actions`(15), `root.a107.runtime`(12), `workflow.execution_binding`(11), `workflow.inprocess_replay`(11), `_live_original_runtime.Mapping`(10), `runtime_model_calls`(10), `_live_original_runtime.ValidationError`(8), `workflow.completions`(7), `workflow.decision_exchanges`(7), `workflow.binding_context`(6), `workflow.run_id`(6), `_live_original_runtime.DECISION_EXCHANGE_PROTOCOL`(5), `_live_original_runtime.nullcontext`(5), `_live_original_runtime._plain`(5), `runtime_forms`(5), `workflow.resource_estimator`(5), `workflow.specialist`(5), `workflow.validate_contract_information`(5), `YieldController`(5), `YieldParameters`(5), `_live_original_runtime.Draft202012Validator`(4), `_live_original_runtime.instructional_model_context`(4), `_live_original_runtime._object`(4), `_live_original_runtime_prompt.INSTRUCTIONS`(4), `PracticalYieldEstimator`(4), `root.a107.episode_return_records`(4), `runtime_episodes`(4), `workflow.decision_protocol`(4), `workflow.is_job_source`(4), `workflow.receipts`(4), `workflow.source_credit_view`(4), `_live_original_providers.apply_state_frame`(3), `_live_original_providers._rna_comparison_receiver_context`(3), `_live_original_runtime.Record`(3), `_live_original_runtime.schema_failure_diagnostic`(3), `_live_original_runtime.sqlite3`(3), `root.a107.communication`(3), `root.a107.numerical`(3), `root.a107.practical_yield`(3), `workflow.completed_unit`(3), `workflow.controller_value`(3), `workflow.job_episodes`(3), `workflow.launch_instructions`(3), `workflow.pending_work`(3), `workflow.provider`(3), `workflow.selected`(3), `catalog.configured`(2), `catalog.received`(2), `EpisodeReceipts`(2), `EpisodeReturnRecords`(2), `ESTIMATOR_VERSION`(2), `_live_original_providers.DECISION_CONTEXT_VERSION`(2), `_live_original_providers.is_api_launch_context`(2), `_live_original_providers.is_published_scientific_context`(2), `_live_original_runtime.AcquisitionError`(2), `_live_original_runtime._action_generation_schema`(2), `_live_original_runtime.child_option_information`(2), `_live_original_runtime.composition_lookup_schema`(2), `_live_original_runtime.DECISION_CONTEXT_VERSION`(2), `_live_original_runtime.EventTargetError`(2), `_live_original_runtime.infernal_receiver_context`(2), `_live_original_runtime.model_snapshot`(2), `_live_original_runtime._references_in`(2), `_live_original_runtime.ReportRedelivery`(2), `_live_original_runtime.requested_contract_information`(2), `_live_original_runtime.SourceEnd`(2), `_live_original_runtime.subprocess`(2), `_live_original_runtime._wait_target_feedback`(2), `NumericBand`(2), `root.a107.episode_source_failure`(2), `root.a107.episode_work_report`(2), `root.a107.providers`(2), `runtime_observations`(2), `runtime_receipt_inheritance`(2), `runtime_record_receipts`(2), `UnitRef`(2), `workflow.controller_binding`(2), `workflow.episode_bindings`(2), `workflow.execute`(2), `workflow.execution_handle`(2), `workflow.knowledge`(2), `workflow.progress_provider`(2), `workflow.release`(2), `workflow.services`(2), `workflow.uses_received_record_context`(2), `catalog.readers`(1), `_live_original_providers.deepcopy`(1), `_live_original_providers.infernal_receiver_context`(1), `_live_original_providers.json`(1), `_live_original_providers._ordinary_runtime_receiver_context`(1), `_live_original_providers.render_api_launch_prompt`(1), `_live_original_providers.render_partner_presence_evidence_prompt`(1), `_live_original_providers.text_instructions`(1), `_live_original_runtime.ActionFailure`(1), `_live_original_runtime.ActionLeaf`(1), `_live_original_runtime.apply_state_frame`(1), `_live_original_runtime._ASSIGNMENT_TRANSPORT`(1), `_live_original_runtime._category_yield_parameters`(1), `_live_original_runtime.ContractError`(1), `_live_original_runtime.ContractInformationError`(1), `_live_original_runtime.CONTRACT_INFORMATION_OPERATIONS`(1), `_live_original_runtime._decode_recorded_action_response`(1), `_live_original_runtime._digest`(1), `_live_original_runtime.EFFECT_VERSION`(1), `_live_original_runtime.Episode`(1), `_live_original_runtime.FACT_MEANINGS`(1), `_live_original_runtime.FACT_SOURCES`(1), `_live_original_runtime.form_with_facts`(1), `_live_original_runtime.inspect`(1), `_live_original_runtime.interpretation_schema`(1), `_live_original_runtime.is_contract_information`(1), `_live_original_runtime.lookup_attempts`(1), `_live_original_runtime.observes_action_outcome`(1), `_live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL`(1), `_live_original_runtime._recorded_action_generation_schema`(1), `_live_original_runtime._recorded_assignment_transport`(1), `_live_original_runtime.ReportBoundaryError`(1), `_live_original_runtime.state_frame`(1), `_live_original_runtime.validate_form`(1), `_live_original_runtime.yield_table`(1), `root.a107.decision_context`(1), `root.a107.episode_receipts`(1), `root.a107.method_loop.identities`(1), `workflow.action_schema`(1), `workflow.archive`(1), `workflow.automatic_score_updates`(1), `workflow.available_child_roles`(1), `workflow.catalog`(1), `workflow.context`(1), `workflow.contract_information_profile`(1), `workflow.contract_information_reply`(1), `workflow.delivery_resolution_inputs`(1), `workflow.delivery_status`(1), `workflow.execution_backend`(1), `workflow.execution_expectations`(1), `workflow.extra_report_sources`(1), `workflow.facts`(1), `workflow.freeze_contract_information`(1), `workflow.freeze_literature_numerical_contracts`(1), `workflow.grains`(1), `workflow.history_preview`(1), `workflow.job_episode_options`(1), `workflow.last_observed_credit`(1), `workflow.local_outcome_preview`(1), `workflow.native_estimation_context`(1), `workflow.native_event_information`(1), `workflow.next_return`(1), `workflow.numerical_contracts`(1), `workflow.pending_handles`(1), `workflow.perform_selected_wait`(1), `workflow.permits_common_action`(1), `workflow.reasoning_action_schema`(1), `workflow.receive_native_outcome`(1), `workflow.receive_outcome`(1), `workflow.recover_commissions`(1), `workflow.resolve_pending_deliveries`(1), `workflow.resolver`(1), `workflow.resource_context`(1), `workflow.retain_shared_grading_results`(1), `workflow.shared_information_context`(1), `workflow.source_credit_binding`(1), `workflow.tools`(1), `workflow.validate_report`(1), `workflow.working_state`(1)

Every row (name, episode, file, uses, purpose) is in `runs/carry_over/calls/a107_03.tsv`.

## Carried over

One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__execution_job_submission__hpc_job_execution.tsv`. Columns: old file, kind and name (copied), then whether it is old-runner machinery or an episode function, then its new place (or the machinery reason). Rows whose place begins "unplaced:" are also listed in `carry_over_blocked/a107__partner_presence_evidence__hpc_work_planning__execution_job_submission__hpc_job_execution.md`.

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
| from_parent.py | method | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the ASSIGNMENT_SCHEMA properties with resource_id and resource_kind fixed) and library validate_assignment in read_from_parent |
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
