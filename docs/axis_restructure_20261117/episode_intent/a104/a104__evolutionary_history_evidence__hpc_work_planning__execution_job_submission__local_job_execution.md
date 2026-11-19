# a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/local_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/local_job_execution/<file>`
(the 63 files directly in this folder; no `grading/` or `scoring/` subfolder; no child folders).
Old binding class: `ExecutionEpisode` (`binding_path = '.../execution_job_submission/local_job_execution'`,
`commissioning_parent = '.../execution_job_submission'`, `roles = ('launch_local',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `LocalExecutionTask`, prompt renderer `present_execution_context`.
Inner terminal behavior: `native_execution_service.TerminalExecutionBehavior` (version `terminal_execution_episode_v1`).

## What it is for (its goal, in its own words)

`goal.py` delegates to the terminal behavior; `native_goal.py` `instructions()`:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the
> shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the
> actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed.
> Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context,
> not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit
> enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native
> job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that
> original submission rather than create a duplicate. Use the provided resource-specific instructions, account,
> storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs
> on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work.
> Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side
> transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote
> shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection
> details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no
> stopping budget.

When the frozen launch-instruction library has sections for this resource (`launch_instructions.for_resource`), they
are appended under "Resource instructions supplied from the frozen library:". The episode runs one practical job on
one local resource by writing and executing shell commands until the requested endpoint is validated.

## Task and instructions

`instructions.py`: the same composition as the launch parent (the goal text above replaces the generic
`INSTRUCTIONS`; tool knowledge; launch instruction library; redeliver_report paragraph; wait / native-event paragraphs
only when `wait` is permitted — it never is; exchange-protocol replacement).

`task.py` / `task_action.py`: one model decision per unit (old-runner body); no `reason` action, so no empty-commit
check; report update admitted with grain `launch_local`. Permitted common actions: `tool` only.

## What it reads from its parent's assignment

`child_assignment_schema`: anyOf the concrete request schemas of the bound local resources (no frozen-request rule, unlike `hpc_job_execution`).

The assignment is the practical `ASSIGNMENT_SCHEMA` (resource_id, resource_kind `local`, workspace confined to the
resource workspace, requested_job — generic or one of the A104 native/preparation jobs — endpoint `usable_handoff` or
`completed_job_outputs`, initial_context) validated by the resource's `TerminalExecution`
operations. `prepare_assignment` requires the commissioning role `launch`, a kind match, masking/utility inputs, the
parent's immutable input versions and native BLAST database job inputs; `_check_parent_inputs` re-reads the parent's
recorded launch before `initialize` and each action.

## Children it may commission

None (leaf).

## Decision state and what it shows the model

Generic old-runner context plus the terminal behavior's `decision_context`: `execution_assignment`,
`execution_resource` (resource_kind, workspace, kind, policy, account, ssh_argv, python_executable, scheduler,
inventory snapshot), `coordinator_workspace`, `execution_progress` (practical state credit view),
`execution_completion` (proof or null). Initial context: `execution_resource_information` (initial inventory).
`internal_summary._with_selected_execution_task` adds `selected_execution_task` for this one request (scientific question and selected tool info from the scientific parent task; resource, kind, endpoint, constraints, job view — native HMMER jobs in their scientific view) when the request is an `ebi_hmmer` API request or exactly one A104 native job (differs from `hpc_job_execution`, which adds nothing).
Execution expectations are captured for role `launch_local`.

## Tools it offers

One tool, `exec_command` (`native_tool_contracts.py`): `cmd` (string or argv), `workdir`, `env` (required), `target`
`resource` (default) or `coordinator`. `native_tool_actions.py`: validate arguments and the action against the
assignment; `state.begin(operation_key)` (a completed operation returns its saved receipt instead of running again);
run through `TerminalExecution`; any execution exception becomes `execution_action_failed` in the native outcome;
finalize scientific command evidence; track cwd/environment revision for resource commands inside the workspace;
assess validations; `state.finish`; publish the receipt as a `practical_receipt` source. Always returns status
`completed` with the receipt (failure is inside the receipt, so it enters the iterator).

## How its credit is counted

`credit.py` -> `native_credit.py`: kind `operational`; live credit = the practical state's `credit_view()` for this
episode (computed in the old shared `practical_execution_state.PracticalState`, which is outside this folder).
Closed episodes return the frozen `execution_closed_operational_credit_v1` view. Completion proof:
`state.completion_proof()` (operation key must match the action); `verify_completion` = `state.verify_completion`.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_local_yield_controller`: task yield profile `launch_local:` + request class
(`practical_local[_native_*]_handoff` or `..._outputs`), old `YieldController(epoch, initial_credit,
profile.cutoff, YieldParameters(**profile.parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`:
observed-history forecast until a verified endpoint, then exact zero. In the new set of three this is **completion
with a target** (target = the requested endpoint's validated completion). Settings as in the launch parent.

## What it reports to its parent

`to_parent.py`: empty native family sources; the terminal facts `practical_completed`, `practical_receipt_digests`,
`practical_receipt_refs`; `execution_handoff_refs` (received handoffs plus own practical receipts that read as
returnable handoffs), `execution_result_refs`, `execution_file_source_refs`, `execution_file_capture_outcomes`,
`execution_result_origin`, `execution_blast_hsps` (empty), `execution_completed` = `practical_completed`; AppService
support refs when bound. `validate_report` requires `x-source` fields to equal the recorded facts.

## Differences from similar episodes

- vs `hpc_job_execution` (otherwise the same files with role/kind names swapped): (1) no frozen-request rule in `from_parent.child_assignment_schema`; (2) `internal_summary` adds the `selected_execution_task` view of the scientific parent task.
- vs `api_job_execution`: `exec_command` on a resource instead of API operations, tool-only (no `wait`), credit from the
  practical state rather than counted handoffs/records, and a non-null native result origin.
- vs the launch parent: leaf, no `reason`/`child`/`wait`, its own terminal behavior and completion-proof continuation.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `action_outcome.py` | 5 | `_outcome` helper. | none |
| `binding_record.py` | 9 | `as_record()`: binding id `.../execution_job_submission/local_job_execution`, version and full configuration. | none |
| `binding_roles.py` | 6 | VERSION, ROLES, KINDS, ROLE_KINDS copies. | none |
| `closed_credit.py` | 122 | Closed operational credit freezing and read-back (`execution_closed_operational_credit_v1`). | `import:communication` (1), `import:episode_receipts` (1), `import:episode_return_records` (3), `name:EpisodeReceipts` (1), `name:EpisodeReturnRecords` (1), `name:_same` (3), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations` (1), `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2) |
| `completion.py` | 57 | `completion_for_action` delegates to the resource's terminal behavior; `verify_completion` checks a recorded closed verdict, then the practical state's own `verify_completion`. | `import:communication` (1), `import:numerical` (1), `import:practical_yield` (1), `import:episode_return_records` (1), `import:method_loop.identities` (1), `name:ESTIMATOR_VERSION` (1), `name:NumericBand` (1), `name:_same` (4), `name:UnitRef` (1), `table:runtime_observations` (1) |
| `configuration.py` | 76 | Same validated settings as the launch episode; practical resources use this episode's own `native_execution_service.TerminalExecutionBehavior`; API access is the old shared `APIRecordAccess`. | `import:communication` (1), `import:numerical` (1), `name:YieldController` (2), `name:YieldParameters` (2) |
| `credit.py` | 28 | Credit kind `operational`; live credit is the practical state's `credit_view()` for this resource; closed view returned when present. | `import:communication` (1) |
| `credit_records.py` | 3 | `_CLOSED_CREDIT` constant. | none |
| `decision_context.py` | 54 | Generic decision-context assembly (old-runner body). | `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.is_scientific_source` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:FACT_MEANINGS` (1), `name:FACT_SOURCES` (1), `name:_references_in` (1), `table:runtime_actions` (2) |
| `decision_contracts.py` | 133 | Generic exchange-protocol support (old-runner body). | `self.workflow.contract_information_reply` (1), `self.workflow.decision_exchanges` (2), `self.workflow.journal` (1), `self.workflow.store` (2), `self.workflow.validate_contract_information` (2), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:apply_state_frame` (1), `name:bind_functions` (1), `name:composition_lookup_schema` (2), `name:CONTRACT_INFORMATION_OPERATIONS` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (1), `name:is_contract_information` (1), `name:model_snapshot` (1), `name:_recorded_action_generation_schema` (1), `name:_references_in` (1), `name:requested_contract_information` (1), `name:WorkflowError` (9), `table:runtime_model_calls` (1) |
| `decision_exchange.py` | 113 | Generic exchange loop (old-runner body). | `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (1), `self.workflow.execute` (1), `self.workflow.journal` (1), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.validate_contract_information` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:bind_functions` (1), `name:_category_yield_parameters` (1), `name:child_option_information` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (2), `name:lookup_attempts` (1), `name:model_snapshot` (1), `name:requested_contract_information` (1), `name:schema_failure_diagnostic` (2), `name:state_frame` (1), `name:yield_table` (1), `table:runtime_model_calls` (2) |
| `decision_provider.py` | 60 | Generic presentation-routing model completion (old-runner body). | `self.workflow.provider` (1), `self.workflow.specialist` (2), `import:runtime` (1), `import:providers` (2), `import:root.providers` (1), `name:_ORIGINAL_DECLARED_PRESENTATION` (1), `name:_ORIGINAL_MODEL_COMPLETE` (2), `name:_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION` (2), `name:_ORIGINAL_MODEL_INSTANCE_DICT` (3) |
| `episode.py` | 47 | Binding class: binding_path `.../execution_job_submission/local_job_execution`, commissioning_parent `.../execution_job_submission`, roles ('launch_local',), leaf, permitted actions tool only, replaces default instructions, renderer `present_execution_context`. | none |
| `from_parent.py` | 69 | Assignment schema (anyOf the local resource request schemas) and `prepare_assignment` (parent role `launch`, kind match, masking/utility inputs, versions, native database inputs); `initial_references`. | `import:communication` (1) |
| `goal.py` | 7 | `instructions` delegates to the resource's terminal behavior (`native_goal`). | none |
| `__init__.py` | 0 | Empty package marker. | none |
| `instructions.py` | 36 | Instruction composition (old-runner body; own goal text replaces the default). | `workflow.binding_context` (1), `workflow.decision_protocol` (1), `workflow.is_job_source` (1), `workflow.job_episodes` (1), `workflow.knowledge` (1), `workflow.launch_instructions` (1), `workflow.native_event_information` (1), `workflow.permits_common_action` (3), `workflow.specialist` (1), `import:runtime_prompt` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:DECISION_EXCHANGE_PROTOCOL` (1), `name:INSTRUCTIONS` (3), `name:REASONING_COMMIT_REQUIREMENT` (1) |
| `internal_summary.py` | 42 | `decision_context` = the terminal behavior's context plus `selected_execution_task` (scientific parent task view of this request when it is one A104 native job or an ebi_hmmer request). | `import:communication` (1) |
| `native_actions.py` | 17 | Tool catalog / execute: check the original parent launch inputs, then delegate to the terminal behavior. | `import:communication` (1) |
| `native_assignment.py` | 26 | Terminal behavior assignment: practical ASSIGNMENT_SCHEMA, resource_kind must match the role, operations validator. | `import:communication` (1) |
| `native_completion.py` | 12 | Completion proof from the practical state (operation key must match) and PracticalYieldEstimator over `state.verify_completion`. | `import:practical_yield` (1), `name:PracticalYieldEstimator` (1) |
| `native_configuration.py` | 27 | Terminal behavior construction: resources limited to local/hpc, initial inventory bound to them, TerminalExecution operations with terminal artifact selector; binding id `terminal_execution`. | `import:communication` (1) |
| `native_credit.py` | 10 | Terminal behavior credit: `state.credit_view()` (operational). | none |
| `native_execution_service.py` | 22 | `TerminalExecutionBehavior` composed of the native_* pieces; leaf, tool only. | none |
| `native_goal.py` | 18 | Own goal text: "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget." Followed by the frozen launch-instruction library sections for this resource when present. | none |
| `native_internal_summary.py` | 17 | Terminal decision context: execution_assignment, execution_resource (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory snapshot), coordinator_workspace, execution_progress (state credit view), execution_completion; initial context = execution_resource_information. | `import:communication` (1) |
| `native_receipt_state.py` | 20 | Practical state per episode under `practical-execution/<digest>` with initial validations from the assignment's initial_context. | none |
| `native_resource_contracts.py` | 4 | VERSION `terminal_execution_episode_v1`, ROLE_KINDS {launch_local: local, launch_hpc: hpc}. | none |
| `native_return.py` | 32 | Terminal report fact sources (`practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`), facts from the practical state (receipts published as sources), resolution and report validation. | `import:communication` (1) |
| `native_state.py` | 31 | `initialize` (file-source probe, parent-input check, delegate) and the result directory with its immutable assignment manifest. | `import:communication` (1) |
| `native_tool_actions.py` | 50 | The `exec_command` tool: validate arguments and action, begin/finish an operation in the practical state (completed operations replay their receipt), run on the resource or coordinator, finalize scientific command evidence, track cwd/environment revision, assess validations, publish the receipt as a practical_receipt source. | `import:communication` (1) |
| `native_tool_contracts.py` | 8 | `operation_catalog(kind)`: the single exec_command tool (cmd, workdir, target resource/coordinator, env). | none |
| `parent_launch_contract.py` | 13 | `parent_launch_schema` for reading the parent's original launch. | none |
| `parent_request_contracts.py` | 93 | `_check_parent_inputs` (re-read the parent's recorded launch and validate inputs, versions and native database inputs), `_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`. | `import:communication` (1), `table:runtime_episodes` (1) |
| `presentation.py` | 60 | `present_execution_context` renderer selection (same as launch). | `import:providers` (1), `import:receiver_prompt` (1), `name:apply_state_frame` (3), `name:DECISION_CONTEXT_VERSION` (1), `name:is_api_launch_context` (2), `name:is_published_scientific_context` (2), `name:_ordinary_runtime_receiver_context` (1), `name:render_api_launch_prompt` (1), `name:render_evolutionary_history_evidence_prompt` (1), `name:render_receiver_prompt` (1), `name:text_instructions` (1) |
| `protected_reference_access.py` | 100 | Protected reader installation and classification. | `import:communication` (1) |
| `receipt_selection.py` | 59 | Received selection and handoffs/results for this context. | `import:communication` (1), `import:episode_receipts` (1), `name:EpisodeReceipts` (1), `table:runtime_actions` (1), `table:runtime_receipt_inheritance` (2) |
| `received_action_identity.py` | 26 | `_selected_result_action`: read a recorded result action by operation key. | `import:communication` (1), `table:runtime_actions` (1) |
| `received_launch_records.py` | 3 | LAUNCH_VERSION constant. | none |
| `received_parent_records.py` | 106 | Report sources/facts for received roles and service probes. | `import:communication` (1) |
| `received_reference_access.py` | 109 | Received-reference resolution. | `import:communication` (1) |
| `received_report_admission.py` | 94 | Received report validation and admitted references. | `import:communication` (1) |
| `received_result_custody.py` | 62 | Result body validation and reading. | `import:communication` (1), `table:runtime_episodes` (1) |
| `report_delivery.py` | 32 | Generic finish/report delivery (old-runner body). | `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:form_with_facts` (1), `name:Record` (2), `table:runtime_forms` (2) |
| `report_fields.py` | 61 | Report fact sources incl. terminal practical receipt sources for launch_local/launch_hpc. | `import:communication` (2) |
| `report_reference_access.py` | 139 | Report reference resolution incl. practical_receipt digests for local/hpc roles. | `import:communication` (2), `import:episode_bindings` (2), `name:reference_in_context` (2) |
| `resource_information.py` | 95 | Resource information, initial context, capabilities, resource tool contracts. | none |
| `resource_operations.py` | 7 | `launch_operation_catalog` (`execution.capabilities`). | none |
| `result_operations.py` | 10 | `native_result_operation_catalog`. | none |
| `result_records.py` | 9 | RESULTS_VERSION, RESULT_PROVIDER, NATIVE_RESULT_ORIGIN, RESULTS_SCHEMA. | none |
| `retained_native_receipts.py` | 19 | `_delegate`, `_practical_context`, and `state` (only for launch_local/launch_hpc roles). | `import:communication` (1) |
| `schema_fields.py` | 6 | TEXT, OFFSET, LIMIT, FILE_LIMIT. | none |
| `scientific_inputs.py` | 14 | Masking/utility input validation and input versions. | none |
| `selector_contracts.py` | 80 | Native selector validation per family and windows. | none |
| `selector_records.py` | 7 | NATIVE_SELECTOR_SCHEMA. | none |
| `target_custody.py` | 52 | `_target` and `_context_target` (handoff assignment must equal this assignment for resource roles). | `import:communication` (1) |
| `task_action.py` | 149 | Response application and action execution (old-runner body); no reason action, report grain `launch_local`. | `self.workflow.automatic_score_updates` (1), `self.workflow.binding_context` (1), `self.workflow.completions` (1), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.execute` (1), `self.workflow.execution_binding` (5), `self.workflow.journal` (3), `self.workflow.last_observed_credit` (1), `self.workflow.pending_work` (1), `self.workflow.perform_selected_wait` (1), `self.workflow.permits_common_action` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (5), `self.workflow.validate_report` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:AcquisitionError` (2), `name:ActionFailure` (1), `name:bind_functions` (1), `name:ContractError` (1), `name:ContractInformationError` (1), `name:_decode_recorded_action_response` (1), `name:EventTargetError` (2), `name:observes_action_outcome` (1), `name:ReportBoundaryError` (1), `name:ReportRedelivery` (2), `name:schema_failure_diagnostic` (1), `name:_wait_target_feedback` (2), `name:WorkflowError` (1), `table:runtime_actions` (6), `table:runtime_model_calls` (1) |
| `task_decision.py` | 154 | Generic model call (old-runner body) with execution expectations for role `launch_local`. | `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.contract_information_profile` (1), `self.workflow.decision_exchanges` (1), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.is_job_source` (3), `self.workflow.job_episodes` (4), `self.workflow.journal` (1), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.numerical_contracts` (1), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.provider` (2), `self.workflow.receipts` (4), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (5), `self.workflow.services` (1), `self.workflow.shared_information_context` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (2), `self.workflow.waiting_support` (1), `import:runtime` (2), `import:episode_work_report` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:_ASSIGNMENT_TRANSPORT` (1), `name:bind_functions` (1), `name:child_option_information` (1), `name:completed_action_reports` (2), `name:DECISION_EXCHANGE_PROTOCOL` (5), `name:instructional_model_context` (1), `name:_recorded_assignment_transport` (1), `name:requested_action_history` (2), `name:WorkflowError` (5), `table:runtime_model_calls` (5) |
| `task.py` | 97 | Task `next` (old-runner body). | `self.workflow.action_schema` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (2), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execution_binding` (2), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (4), `self.workflow.next_return` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.run_id` (1), `self.workflow.selected` (2), `self.workflow.store` (3), `import:runtime` (2), `import:providers` (1), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:ModelCallError` (1), `name:record_source_failure` (1), `name:SourceEnd` (2), `name:WorkflowError` (1), `table:runtime_actions` (2), `table:runtime_episodes` (1), `table:runtime_model_calls` (1) |
| `task_state.py` | 117 | Generic task state (old-runner body). | `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `workflow.context` (1), `workflow.grains` (1), `import:runtime` (2), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:ActionLeaf` (1), `name:bind_functions` (1), `name:EFFECT_VERSION` (1), `name:Episode` (1), `name:interpretation_schema` (1), `name:Record` (1), `name:record_source_failure` (1), `table:runtime_actions` (5) |
| `to_parent.py` | 84 | Report facts: native empty sources, terminal practical facts, received handoffs incl. returnable practical receipts, result refs, file sources/outcomes, origin, `execution_completed` = practical_completed; report validation. | `import:communication` (2) |
| `waiting.py` | 9 | `suspension_changed`. | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| `yield_estimator.py` | 49 | Continuation for role launch_local: profile `launch_local:` + request class (`practical_<kind>[_native_*]_handoff\|outputs`); estimator ends at a verified completion proof. | `import:communication` (1), `import:numerical` (1), `import:practical_yield` (1), `name:PracticalYieldEstimator` (1), `name:YieldController` (1), `name:YieldParameters` (1) |

## Carried over

Every row of the old function list (`runs/carry_over/functions/...local_job_execution.tsv`), carried to the private binding in this folder. "machinery" is old-runner code that is not carried (reason given); "episode function" lands in the file named, or is reported as not carried with its reason.

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| `action_outcome.py` | function | `_outcome` | machinery | old-runner outcome envelope (status, record_refs, changed_record_refs); the tool returns its own outcome |
| `binding_record.py` | class | `LocalExecutionBindingRecord` | machinery | binding_record / as_record of the binding (README 3e) |
| `binding_record.py` | method | `LocalExecutionBindingRecord.as_record` | machinery | binding_record / as_record of the binding (README 3e) |
| `closed_credit.py` | class | `LocalExecutionClosedCredit` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `closed_credit.py` | method | `LocalExecutionClosedCredit._closed_credit_carrier` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `closed_credit.py` | method | `LocalExecutionClosedCredit._closed_credit_receipts` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `closed_credit.py` | method | `LocalExecutionClosedCredit._closed_credit_value` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `closed_credit.py` | method | `LocalExecutionClosedCredit._closed_credit_facts` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `closed_credit.py` | method | `LocalExecutionClosedCredit._closed_operational_credit_view` | machinery | frozen closed operational credit over runtime_episodes, runtime_observations, runtime_record_receipts, runtime_receipt_inheritance; the system returns completion[credit] |
| `completion.py` | class | `LocalExecutionCompletion` | machinery | completion proof as controller input and its verification over runtime_observations (README 3d, 5 item 5); the proof is derived from the held receipts in messages/internal_summary.py _completion |
| `completion.py` | method | `LocalExecutionCompletion.completion_for_action` | machinery | completion proof as controller input and its verification over runtime_observations (README 3d, 5 item 5); the proof is derived from the held receipts in messages/internal_summary.py _completion |
| `completion.py` | method | `LocalExecutionCompletion._closed_completion_verdict` | machinery | completion proof as controller input and its verification over runtime_observations (README 3d, 5 item 5); the proof is derived from the held receipts in messages/internal_summary.py _completion |
| `completion.py` | method | `LocalExecutionCompletion.verify_completion` | machinery | completion proof as controller input and its verification over runtime_observations (README 3d, 5 item 5); the proof is derived from the held receipts in messages/internal_summary.py _completion |
| `configuration.py` | class | `LocalExecutionConfiguration` | episode function | settings of the run: ctx.settings (task.py _resource_configuration, decide); yield_estimator.py settings[task_yield_profiles]; the other old checks are API / results-role (unplaced) or machinery |
| `configuration.py` | method | `LocalExecutionConfiguration.__init__` | episode function | task.py _resource_configuration and yield_estimator.py _task_yield_profile read the values from settings; construction of the API execution, progress provider and result readers is machinery / not this role |
| `credit.py` | class | `LocalExecutionCredit` | episode function | credit.py |
| `credit.py` | method | `LocalExecutionCredit.credit_kind` | machinery | credit_kind deleted (README 3d) |
| `credit.py` | method | `LocalExecutionCredit.project_credit` | episode function | credit.py credit (the closed-credit branch is machinery) |
| `credit.py` | method | `LocalExecutionCredit._live_project_credit` | episode function | credit.py credit over project_practical_credit (the native readers applies() calls are results-role machinery) |
| `credit.py` | method | `LocalExecutionCredit.credit_view` | episode function | credit.py credit |
| `decision_context.py` | class | `LocalExecutionTaskContext` | machinery | generic decision-context assembly of the old runner (reads runtime_actions, receipts, provider); this episode context is task.py decide + messages/internal_summary.py |
| `decision_context.py` | method | `LocalExecutionTaskContext.assemble_decision_context` | machinery | generic decision-context assembly of the old runner (reads runtime_actions, receipts, provider); this episode context is task.py decide + messages/internal_summary.py |
| `decision_context.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `decision_contracts.py` | class | `LocalExecutionTaskDecisionContracts` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | method | `LocalExecutionTaskDecisionContracts.interpretation_context` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | method | `LocalExecutionTaskDecisionContracts.exchange_schema` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | method | `LocalExecutionTaskDecisionContracts.exchange_response` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | method | `LocalExecutionTaskDecisionContracts.validate_contract_exchange_request` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | method | `LocalExecutionTaskDecisionContracts.validate_contract_exchange_history` | machinery | decision exchange: request_context exchange, saved-request checks (README 3a) |
| `decision_contracts.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `decision_exchange.py` | class | `LocalExecutionTaskDecisionExchange` | machinery | decision exchange loop (exchange_decision) |
| `decision_exchange.py` | method | `LocalExecutionTaskDecisionExchange.exchange_decision` | machinery | decision exchange loop (exchange_decision) |
| `decision_exchange.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `decision_provider.py` | class | `LocalExecutionTaskDecisionProvider` | machinery | model call through the provider and runtime_model_calls; the system calls the model for the ModelRequest |
| `decision_provider.py` | method | `LocalExecutionTaskDecisionProvider.decision_completion` | machinery | model call through the provider and runtime_model_calls; the system calls the model for the ModelRequest |
| `episode.py` | class | `ExecutionEpisode` | episode function | episode.py LocalJobExecution |
| `episode.py` | method | `ExecutionEpisode.child_roles` | episode function | task.py CHILD_SLOTS = {} (leaf) |
| `episode.py` | method | `ExecutionEpisode.allowed_children` | episode function | task.py CHILD_SLOTS = {} (leaf) |
| `episode.py` | method | `ExecutionEpisode.permitted_common_actions` | episode function | task.py decide / action: the one tool exec_command only |
| `from_parent.py` | class | `LocalExecutionFromParent` | episode function | messages/read_from_parent.py |
| `from_parent.py` | method | `LocalExecutionFromParent.required_return_sources` | machinery | the parent selects return fields in msg_to_child (README 3b C4); it always returned () |
| `from_parent.py` | method | `LocalExecutionFromParent.child_assignment_schema` | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| `from_parent.py` | method | `LocalExecutionFromParent.assignment_schema` | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| `from_parent.py` | method | `LocalExecutionFromParent.prepare_assignment` | episode function | messages/read_from_parent.py read_from_parent (validate_assignment; the checks of the launch commission, input versions and database job inputs through the old Store are machinery: a wrong commission fails) |
| `from_parent.py` | method | `LocalExecutionFromParent.initial_references` | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs (the records the job inputs name, passed in custody) |
| `goal.py` | class | `LocalExecutionGoal` | episode function | goal.py and task.py _instructions |
| `goal.py` | method | `LocalExecutionGoal.instructions` | episode function | task.py _instructions (GOAL_INSTRUCTION) |
| `instructions.py` | function | `instructions` | episode function | task.py _instructions (goal text, tool knowledge, launch instructions; the redeliver_report, wait, native-event and exchange paragraphs are machinery) |
| `instructions.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `internal_summary.py` | class | `LocalExecutionInternalSummary` | episode function | messages/internal_summary.py |
| `internal_summary.py` | method | `LocalExecutionInternalSummary._with_selected_execution_task` | episode function | messages/internal_summary.py _selected_execution_task (the resource is added by task.py decide); native_profile_scientific_job_view unplaced (raises) |
| `internal_summary.py` | method | `LocalExecutionInternalSummary.decision_context` | episode function | messages/internal_summary.py internal_summary and task.py decide |
| `native_actions.py` | class | `LocalExecutionNativeActions` | episode function | task.py TOOLS |
| `native_actions.py` | method | `LocalExecutionNativeActions.catalog` | episode function | task.py EXEC_COMMAND |
| `native_actions.py` | method | `LocalExecutionNativeActions.execute` | episode function | task.py exec_command (the _check_parent_inputs call is machinery) |
| `native_assignment.py` | class | `LocalExecutionNativeAssignment` | episode function | messages/read_from_parent.py |
| `native_assignment.py` | method | `LocalExecutionNativeAssignment._assignment` | episode function | messages/read_from_parent.py read_from_parent and task.py _resource_configuration / _operations |
| `native_assignment.py` | method | `LocalExecutionNativeAssignment.assignment_schema` | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| `native_assignment.py` | method | `LocalExecutionNativeAssignment.prepare_assignment` | episode function | messages/read_from_parent.py read_from_parent |
| `native_completion.py` | class | `LocalExecutionNativeCompletion` | machinery | completion proof machinery (README 3d) |
| `native_completion.py` | method | `LocalExecutionNativeCompletion.completion_for_action` | machinery | completion proof as controller input (README 5 item 5) |
| `native_completion.py` | method | `LocalExecutionNativeCompletion.practical_estimator` | machinery | PracticalYieldEstimator deleted; replaced by CompletionYieldController in yield_estimator.py |
| `native_configuration.py` | class | `LocalExecutionNativeConfiguration` | episode function | settings: ctx.settings resources and initial_information (task.py) |
| `native_configuration.py` | method | `LocalExecutionNativeConfiguration.__init__` | episode function | settings: ctx.settings resources and initial_information (task.py _resource_configuration) |
| `native_configuration.py` | method | `LocalExecutionNativeConfiguration._operations` | episode function | task.py _operations (TerminalExecution over the configured resource) |
| `native_configuration.py` | method | `LocalExecutionNativeConfiguration.as_record` | machinery | binding as_record (README 3e) |
| `native_credit.py` | class | `LocalExecutionNativeCredit` | episode function | credit.py |
| `native_credit.py` | method | `LocalExecutionNativeCredit.credit_kind` | machinery | credit_kind deleted (README 3d) |
| `native_credit.py` | method | `LocalExecutionNativeCredit.credit_view` | episode function | credit.py credit (project_practical_credit over the summary receipts) |
| `native_execution_service.py` | class | `TerminalExecutionBehavior` | episode function | aggregator of the native mix-ins; each of its parts is placed on its own row |
| `native_execution_service.py` | method | `TerminalExecutionBehavior.child_roles` | episode function | task.py CHILD_SLOTS = {} (leaf) |
| `native_execution_service.py` | method | `TerminalExecutionBehavior.permitted_common_actions` | episode function | task.py decide / action: the one tool only |
| `native_execution_service.py` | method | `TerminalExecutionBehavior.allowed_children` | episode function | task.py CHILD_SLOTS = {} (leaf) |
| `native_goal.py` | class | `LocalExecutionNativeGoal` | episode function | task.py GOAL_INSTRUCTION, _instructions |
| `native_goal.py` | method | `LocalExecutionNativeGoal._resource_instructions` | episode function | task.py _instructions (LaunchInstructions.for_resource) |
| `native_goal.py` | method | `LocalExecutionNativeGoal.instructions` | episode function | task.py GOAL_INSTRUCTION, _instructions |
| `native_internal_summary.py` | class | `LocalExecutionNativeInternalSummary` | episode function | messages/internal_summary.py and task.py decide |
| `native_internal_summary.py` | method | `LocalExecutionNativeInternalSummary.initial_decision_context` | episode function | task.py decide (execution_resource_information) |
| `native_internal_summary.py` | method | `LocalExecutionNativeInternalSummary._resource_information` | episode function | task.py _resource |
| `native_internal_summary.py` | method | `LocalExecutionNativeInternalSummary.decision_context` | episode function | messages/internal_summary.py internal_summary and task.py decide |
| `native_receipt_state.py` | class | `LocalExecutionNativeReceiptState` | machinery | PracticalState file ledger under the coordinator directory (begin/finish/receipts/completion proof); receipts are tool outcomes, the completion proof is derived in messages/internal_summary.py |
| `native_receipt_state.py` | method | `LocalExecutionNativeReceiptState._state_directory` | machinery | PracticalState file ledger under the coordinator directory (begin/finish/receipts/completion proof); receipts are tool outcomes, the completion proof is derived in messages/internal_summary.py |
| `native_receipt_state.py` | method | `LocalExecutionNativeReceiptState.initialize` | machinery | PracticalState file ledger under the coordinator directory (begin/finish/receipts/completion proof); receipts are tool outcomes, the completion proof is derived in messages/internal_summary.py |
| `native_receipt_state.py` | method | `LocalExecutionNativeReceiptState.state` | machinery | PracticalState file ledger under the coordinator directory (begin/finish/receipts/completion proof); receipts are tool outcomes, the completion proof is derived in messages/internal_summary.py |
| `native_return.py` | class | `LocalExecutionNativeReturn` | episode function | messages/final_to_parent.py |
| `native_return.py` | method | `LocalExecutionNativeReturn.fact_sources` | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| `native_return.py` | method | `LocalExecutionNativeReturn.facts` | episode function | messages/final_to_parent.py _facts (receipts are the tool outcomes; PracticalReceiptInformation.publish is not called: blocked) |
| `native_return.py` | method | `LocalExecutionNativeReturn.resolve` | episode function | messages/final_to_parent.py _resolver |
| `native_return.py` | method | `LocalExecutionNativeReturn.validate_report` | episode function | messages/final_to_parent.py validate_report (validate_form + x-source facts agreement) |
| `native_state.py` | class | `LocalExecutionNativeState` | machinery | immutable assignment control file and result directories of the old receipt ledger |
| `native_state.py` | method | `LocalExecutionNativeState.initialize` | machinery | immutable assignment control file and result directories of the old receipt ledger |
| `native_state.py` | method | `LocalExecutionNativeState._result_directory` | machinery | immutable assignment control file and result directories of the old receipt ledger |
| `native_tool_actions.py` | class | `LocalExecutionNativeToolActions` | episode function | task.py |
| `native_tool_actions.py` | method | `LocalExecutionNativeToolActions.catalog` | episode function | task.py EXEC_COMMAND |
| `native_tool_actions.py` | method | `LocalExecutionNativeToolActions.execute` | episode function | task.py action (argument validation, Rejected) and exec_command (the run, through the job_access service: BLOCKED-ON-JOB-SERVICE) |
| `native_tool_contracts.py` | function | `operation_catalog` | episode function | task.py EXEC_COMMAND |
| `parent_launch_contract.py` | function | `parent_launch_schema` | machinery | schema of the launch parent assignment, used to check the commission against the old runtime_episodes request; a wrong commission fails |
| `parent_request_contracts.py` | class | `LocalExecutionParentRequestContracts` | episode function | messages/read_from_parent.py and task.py (the parts below) |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._check_parent_inputs` | machinery | check of the commission against runtime_episodes through store.db; a wrong commission fails |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._permitted` | episode function | not carried: choice of the permitted resource among the launch requests belongs to the launch parent (unplaced, reported) |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._request_schema` | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the concrete request schema of this local resource) |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._validate_request` | episode function | messages/read_from_parent.py read_from_parent and task.py _operations (TerminalExecution.validate_assignment) |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._launch` | machinery | check of the launch commission against its schema; a wrong commission fails |
| `parent_request_contracts.py` | method | `LocalExecutionParentRequestContracts._constraints` | machinery | check of the launch commission constraints; a wrong commission fails |
| `presentation.py` | function | `present_execution_context` | episode function | task.py _task_text and decide (the stateful scientific_prompt_states and the unplaced render_selected_execution_prompt are not carried) |
| `protected_reference_access.py` | class | `ProtectedReferenceAccess` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._install_protected_reference_readers` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._protein_reference_access` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._fluorescence_reference_access` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._expression_nmf_reference_access` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._atac_reference_access` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `protected_reference_access.py` | method | `ProtectedReferenceAccess._chromatin_reference_access` | machinery | reference resolution over the receipt ledger for protected result readers (README 3b R3, 3e F3); custody is the system |
| `receipt_selection.py` | class | `LocalExecutionReceiptSelection` | machinery | record_selection over runtime_receipt_inheritance / runtime_actions (README 3c); custody is the system |
| `receipt_selection.py` | method | `LocalExecutionReceiptSelection._selection` | machinery | record_selection over runtime_receipt_inheritance / runtime_actions (README 3c); custody is the system |
| `receipt_selection.py` | method | `LocalExecutionReceiptSelection._received` | machinery | record_selection over runtime_receipt_inheritance / runtime_actions (README 3c); custody is the system |
| `received_action_identity.py` | class | `LocalExecutionReceivedActionIdentity` | machinery | identity check of a saved action in runtime_actions (results-role receipts) |
| `received_action_identity.py` | method | `LocalExecutionReceivedActionIdentity._selected_result_action` | machinery | identity check of a saved action in runtime_actions (results-role receipts) |
| `received_parent_records.py` | class | `LocalExecutionReceivedParentRecords` | machinery | received-report receipts (README 3b R3, 3e F5) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords._has_appservice` | episode function | not carried: API route (api_job_execution); this episode is local only (unplaced, reported) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords._has_uniprot` | episode function | not carried: API route (api_job_execution); this episode is local only (unplaced, reported) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords._appservice_sources` | episode function | not carried: API route (api_job_execution); this episode is local only (unplaced, reported) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords._forwards_bvbrc_reports` | episode function | not carried: API route (api_job_execution); this episode is local only (unplaced, reported) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords.received_report_sources` | machinery | fact sources a parent receives from its children (README 3b R1, C4); the children declare their own fields |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords.received_report_facts` | machinery | received report facts over the receipt ledger (README 3e F5) |
| `received_parent_records.py` | method | `LocalExecutionReceivedParentRecords.received_report_closure_facts` | machinery | received report closure facts over the receipt ledger (README 3e F5) |
| `received_reference_access.py` | class | `LocalExecutionReceivedParentRecordsReferenceAccess` | machinery | reference resolution over the receipt ledger (README 3e F3); custody is the system |
| `received_reference_access.py` | method | `LocalExecutionReceivedParentRecordsReferenceAccess._masking_reference_access` | machinery | reference resolution over the receipt ledger (README 3e F3); custody is the system |
| `received_reference_access.py` | method | `LocalExecutionReceivedParentRecordsReferenceAccess._utility_reference_access` | machinery | reference resolution over the receipt ledger (README 3e F3); custody is the system |
| `received_reference_access.py` | method | `LocalExecutionReceivedParentRecordsReferenceAccess.resolve_received_reference` | machinery | reference resolution over the receipt ledger (README 3e F3); custody is the system |
| `received_report_admission.py` | class | `LocalExecutionReceivedParentRecordsAdmission` | machinery | admission of a received report and its references (README 3b R1); the system admits the child result |
| `received_report_admission.py` | method | `LocalExecutionReceivedParentRecordsAdmission.validate_received_report` | machinery | admission of a received report and its references (README 3b R1); the system admits the child result |
| `received_report_admission.py` | method | `LocalExecutionReceivedParentRecordsAdmission.received_form_references` | machinery | admission of a received report and its references (README 3b R1); the system admits the child result |
| `received_result_custody.py` | class | `LocalExecutionReceivedResultCustody` | machinery | results-role receipt authentication over runtime_episodes, runtime_actions and result directories |
| `received_result_custody.py` | method | `LocalExecutionReceivedResultCustody._validate_result_body` | machinery | results-role receipt authentication over runtime_episodes, runtime_actions and result directories |
| `received_result_custody.py` | method | `LocalExecutionReceivedResultCustody._read_result` | machinery | results-role receipt authentication over runtime_episodes, runtime_actions and result directories |
| `report_delivery.py` | class | `LocalExecutionReportDelivery` | machinery | report delivery: finish, runtime_forms, form_with_facts, release (README 3b D1, D3) |
| `report_delivery.py` | method | `LocalExecutionReportDelivery.finish` | machinery | report delivery: finish, runtime_forms, form_with_facts, release (README 3b D1, D3) |
| `report_delivery.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `report_fields.py` | class | `LocalExecutionToParentFields` | episode function | messages/final_to_parent.py RETURN_FORM |
| `report_fields.py` | method | `LocalExecutionToParentFields.fact_sources` | episode function | messages/final_to_parent.py RETURN_FORM (one field per fact source: terminal facts, handoff / result / file / origin / hsps / completed, the HMMER, BLAST database, standard database, preparation and pairwise families; the dotted masking and utility sources are not declarable) |
| `report_reference_access.py` | class | `LocalExecutionToParentReferenceAccess` | episode function | messages/final_to_parent.py _resolver |
| `report_reference_access.py` | method | `LocalExecutionToParentReferenceAccess.resolve` | episode function | messages/final_to_parent.py _resolver (own receipts; the protected result-family branches are machinery / results-role) |
| `resource_information.py` | class | `LocalExecutionResourceInformation` | episode function | task.py |
| `resource_information.py` | method | `LocalExecutionResourceInformation._resource_information` | episode function | task.py _capabilities (the API branch is not this episode) |
| `resource_information.py` | method | `LocalExecutionResourceInformation.initial_decision_context` | episode function | task.py decide (execution_resource_capabilities, execution_initial_information; received_bvbrc_values and received_blast_jobs are API) |
| `resource_information.py` | method | `LocalExecutionResourceInformation.capabilities` | episode function | task.py _capabilities |
| `resource_information.py` | method | `LocalExecutionResourceInformation.resource_tool_contracts` | episode function | not carried: the catalogue of operations the launch parent routes to its children (native, preparation, API); this episode offers only EXEC_COMMAND (unplaced, reported) |
| `resource_operations.py` | function | `launch_operation_catalog` | episode function | not carried: execution.capabilities is an operation of the launch parent (unplaced, reported) |
| `result_operations.py` | function | `native_result_operation_catalog` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `retained_native_receipts.py` | class | `LocalExecutionRetainedNativeReceipts` | machinery | retained practical state delegation |
| `retained_native_receipts.py` | method | `LocalExecutionRetainedNativeReceipts._delegate` | episode function | task.py _resource_configuration / _operations (the practical resource of the assignment) |
| `retained_native_receipts.py` | method | `LocalExecutionRetainedNativeReceipts._practical_context` | machinery | identity function over the old context |
| `retained_native_receipts.py` | method | `LocalExecutionRetainedNativeReceipts.state` | machinery | PracticalState access |
| `scientific_inputs.py` | class | `LocalExecutionScientificInputs` | machinery | checks of the commissioned native job inputs through the old Store; custody (record_refs) replaces them |
| `scientific_inputs.py` | method | `LocalExecutionScientificInputs._masking_inputs` | machinery | check of commissioned masking inputs (library validate_job_inputs is in no place); custody replaces it |
| `scientific_inputs.py` | method | `LocalExecutionScientificInputs._utility_inputs` | machinery | check of commissioned utility inputs (library validate_job_inputs is in no place); custody replaces it |
| `scientific_inputs.py` | method | `LocalExecutionScientificInputs._versions` | machinery | check of the launch immutable input versions (validate_execution_input_versions is in no place); custody replaces it |
| `selector_contracts.py` | class | `LocalExecutionSelectorContracts` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `selector_contracts.py` | method | `LocalExecutionSelectorContracts._masking_selector` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `selector_contracts.py` | method | `LocalExecutionSelectorContracts._utility_selector` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `selector_contracts.py` | method | `LocalExecutionSelectorContracts._selector` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `selector_contracts.py` | method | `LocalExecutionSelectorContracts._windows` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `target_custody.py` | class | `LocalExecutionTargetCustody` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `target_custody.py` | method | `LocalExecutionTargetCustody._retained_masking_target` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `target_custody.py` | method | `LocalExecutionTargetCustody._retained_utility_target` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `target_custody.py` | method | `LocalExecutionTargetCustody._target` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `target_custody.py` | method | `LocalExecutionTargetCustody._context_target` | episode function | not carried: results-role function; the result acquisition is the episode execution_result_acquisition (unplaced, reported) |
| `task.py` | class | `LocalExecutionTask` | machinery | old-runner loop body (next, inprocess_replay, completions, journal reads) |
| `task.py` | method | `LocalExecutionTask.next` | machinery | old-runner loop body (next, inprocess_replay, completions, journal reads) |
| `task.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `task_action.py` | class | `LocalExecutionTaskAction` | episode function | task.py action and exec_command |
| `task_action.py` | method | `LocalExecutionTaskAction.apply_response` | episode function | task.py action (Rejected for an invalid answer) |
| `task_action.py` | method | `LocalExecutionTaskAction.execute` | episode function | task.py exec_command via ToolCall (the recorded-action branches, state and report update are machinery) |
| `task_action.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `task_decision.py` | class | `LocalExecutionTaskDecision` | episode function | task.py decide |
| `task_decision.py` | method | `LocalExecutionTaskDecision.call` | episode function | task.py decide (ModelRequest; the provider call, saved exchanges and history preview are machinery) |
| `task_decision.py` | method | `LocalExecutionTaskDecision.instructions` | episode function | task.py _instructions |
| `task_decision.py` | method | `LocalExecutionTaskDecision.conversation_key` | machinery | conversation state (README 3a: deleted) |
| `task_decision.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `task_state.py` | class | `LocalExecutionTaskState` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.__init__` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.bind_execution_context` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.record_execution_failure` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.restore_checkpoint` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.restore` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.record_effect` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | method | `LocalExecutionTaskState.checkpoint` | machinery | checkpoint / restore / record_effect / record_execution_failure / inprocess_replay (README 3e); a failed command is a receipt inside the tool outcome |
| `task_state.py` | function | `_bind_preserved_runtime_providers` | machinery | provider patching |
| `to_parent.py` | class | `LocalExecutionToParent` | episode function | messages/final_to_parent.py |
| `to_parent.py` | method | `LocalExecutionToParent.facts` | episode function | messages/final_to_parent.py _facts |
| `to_parent.py` | method | `LocalExecutionToParent._live_facts` | episode function | messages/final_to_parent.py _facts (handoff refs from the receipts; the received-handoff scan and the result readers are machinery / results-role) |
| `to_parent.py` | method | `LocalExecutionToParent.validate_report` | episode function | messages/final_to_parent.py validate_report |
| `waiting.py` | class | `LocalExecutionWaiting` | machinery | wait / suspension machinery (suspension_changed) |
| `waiting.py` | method | `LocalExecutionWaiting.suspension_changed` | machinery | wait / suspension machinery (suspension_changed) |
| `yield_estimator.py` | class | `ExecutionEpisodeYield` | episode function | yield_estimator.py |
| `yield_estimator.py` | method | `ExecutionEpisodeYield._request_yield_class` | episode function | yield_estimator.py _request_yield_class |
| `yield_estimator.py` | method | `ExecutionEpisodeYield._task_yield_profile` | episode function | yield_estimator.py _task_yield_profile |
| `yield_estimator.py` | method | `ExecutionEpisodeYield.yield_controller` | episode function | yield_estimator.py yield_controller |
| `yield_estimator.py` | method | `ExecutionEpisodeYield._launch_local_yield_controller` | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| `yield_estimator.py` | method | `ExecutionEpisodeYield.practical_estimator` | machinery | PracticalYieldEstimator deleted (README 3d) |
