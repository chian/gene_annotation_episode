# a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution/<file>`
(the 63 files directly in this folder; no `grading/` or `scoring/` subfolder; no child folders).
Old binding class: `ExecutionEpisode` (`binding_path = '.../execution_job_submission/hpc_job_execution'`,
`commissioning_parent = '.../execution_job_submission'`, `roles = ('launch_hpc',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `HPCExecutionTask`, prompt renderer `present_execution_context`.
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
one hpc resource by writing and executing shell commands until the requested endpoint is validated.

## Task and instructions

`instructions.py`: the same composition as the launch parent (the goal text above replaces the generic
`INSTRUCTIONS`; tool knowledge; launch instruction library; redeliver_report paragraph; wait / native-event paragraphs
only when `wait` is permitted — it never is; exchange-protocol replacement).

`task.py` / `task_action.py`: one model decision per unit (old-runner body); no `reason` action, so no empty-commit
check; report update admitted with grain `launch_hpc`. Permitted common actions: `tool` only.

## What it reads from its parent's assignment

`child_assignment_schema` (own to this episode): when commissioned by `launch` under an `hpc` ancestor, the schema is an `enum` of exactly the already authorized HPC requests of the parent launch (`frozen_hpc_launch_request_missing` if none) — a frozen HPC launch exposes only its authorized request; otherwise anyOf the concrete request schemas of the bound HPC resources.

The assignment is the practical `ASSIGNMENT_SCHEMA` (resource_id, resource_kind `hpc`, workspace confined to the
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
`internal_summary._with_selected_execution_task` returns the value unchanged: no `selected_execution_task` view is added (differs from `local_job_execution`).
Execution expectations are captured for role `launch_hpc`.

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

`yield_estimator.py` `_launch_hpc_yield_controller`: task yield profile `launch_hpc:` + request class
(`practical_hpc[_native_*]_handoff` or `..._outputs`), old `YieldController(epoch, initial_credit,
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

- vs `local_job_execution` (otherwise the same files with role/kind names swapped): (1) `from_parent.child_assignment_schema` freezes the assignment to the parent launch's already authorized HPC request(s) when the launch runs under an `hpc` ancestor; local has no such rule. (2) `internal_summary` adds no `selected_execution_task` view; local adds it.
- vs `api_job_execution`: `exec_command` on a resource instead of API operations, tool-only (no `wait`), credit from the
  practical state rather than counted handoffs/records, and a non-null native result origin.
- vs the launch parent: leaf, no `reason`/`child`/`wait`, its own terminal behavior and completion-proof continuation.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `action_outcome.py` | 5 | `_outcome` helper. | none |
| `binding_record.py` | 9 | `as_record()`: binding id `.../execution_job_submission/hpc_job_execution`, version and full configuration. | none |
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
| `episode.py` | 47 | Binding class: binding_path `.../execution_job_submission/hpc_job_execution`, commissioning_parent `.../execution_job_submission`, roles ('launch_hpc',), leaf, permitted actions tool only, replaces default instructions, renderer `present_execution_context`. | none |
| `from_parent.py` | 74 | Assignment schema and preparation. Own: under an `hpc` ancestor the child assignment schema is an enum of the parent launch's already authorized HPC requests; otherwise anyOf the HPC resource request schemas. `prepare_assignment` requires parent role `launch`, kind match, masking/utility inputs, versions, native database inputs; `initial_references`. | `import:communication` (1) |
| `goal.py` | 7 | `instructions` delegates to the resource's terminal behavior (`native_goal`). | none |
| `__init__.py` | 0 | Empty package marker. | none |
| `instructions.py` | 36 | Instruction composition (old-runner body; own goal text replaces the default). | `workflow.binding_context` (1), `workflow.decision_protocol` (1), `workflow.is_job_source` (1), `workflow.job_episodes` (1), `workflow.knowledge` (1), `workflow.launch_instructions` (1), `workflow.native_event_information` (1), `workflow.permits_common_action` (3), `workflow.specialist` (1), `import:runtime_prompt` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:DECISION_EXCHANGE_PROTOCOL` (1), `name:INSTRUCTIONS` (3), `name:REASONING_COMMIT_REQUIREMENT` (1) |
| `internal_summary.py` | 13 | `decision_context` = the terminal behavior's context; `_with_selected_execution_task` adds nothing. | `import:communication` (1) |
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
| `task_action.py` | 149 | Response application and action execution (old-runner body); no reason action, report grain `launch_hpc`. | `self.workflow.automatic_score_updates` (1), `self.workflow.binding_context` (1), `self.workflow.completions` (1), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.execute` (1), `self.workflow.execution_binding` (5), `self.workflow.journal` (3), `self.workflow.last_observed_credit` (1), `self.workflow.pending_work` (1), `self.workflow.perform_selected_wait` (1), `self.workflow.permits_common_action` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (5), `self.workflow.validate_report` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:AcquisitionError` (2), `name:ActionFailure` (1), `name:bind_functions` (1), `name:ContractError` (1), `name:ContractInformationError` (1), `name:_decode_recorded_action_response` (1), `name:EventTargetError` (2), `name:observes_action_outcome` (1), `name:ReportBoundaryError` (1), `name:ReportRedelivery` (2), `name:schema_failure_diagnostic` (1), `name:_wait_target_feedback` (2), `name:WorkflowError` (1), `table:runtime_actions` (6), `table:runtime_model_calls` (1) |
| `task_decision.py` | 154 | Generic model call (old-runner body) with execution expectations for role `launch_hpc`. | `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.contract_information_profile` (1), `self.workflow.decision_exchanges` (1), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.is_job_source` (3), `self.workflow.job_episodes` (4), `self.workflow.journal` (1), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.numerical_contracts` (1), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.provider` (2), `self.workflow.receipts` (4), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (5), `self.workflow.services` (1), `self.workflow.shared_information_context` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (2), `self.workflow.waiting_support` (1), `import:runtime` (2), `import:episode_work_report` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:_ASSIGNMENT_TRANSPORT` (1), `name:bind_functions` (1), `name:child_option_information` (1), `name:completed_action_reports` (2), `name:DECISION_EXCHANGE_PROTOCOL` (5), `name:instructional_model_context` (1), `name:_recorded_assignment_transport` (1), `name:requested_action_history` (2), `name:WorkflowError` (5), `table:runtime_model_calls` (5) |
| `task.py` | 97 | Task `next` (old-runner body). | `self.workflow.action_schema` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (2), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execution_binding` (2), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (4), `self.workflow.next_return` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.run_id` (1), `self.workflow.selected` (2), `self.workflow.store` (3), `import:runtime` (2), `import:providers` (1), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:ModelCallError` (1), `name:record_source_failure` (1), `name:SourceEnd` (2), `name:WorkflowError` (1), `table:runtime_actions` (2), `table:runtime_episodes` (1), `table:runtime_model_calls` (1) |
| `task_state.py` | 117 | Generic task state (old-runner body). | `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `workflow.context` (1), `workflow.grains` (1), `import:runtime` (2), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:ActionLeaf` (1), `name:bind_functions` (1), `name:EFFECT_VERSION` (1), `name:Episode` (1), `name:interpretation_schema` (1), `name:Record` (1), `name:record_source_failure` (1), `table:runtime_actions` (5) |
| `to_parent.py` | 84 | Report facts: native empty sources, terminal practical facts, received handoffs incl. returnable practical receipts, result refs, file sources/outcomes, origin, `execution_completed` = practical_completed; report validation. | `import:communication` (2) |
| `waiting.py` | 9 | `suspension_changed`. | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| `yield_estimator.py` | 49 | Continuation for role launch_hpc: profile `launch_hpc:` + request class (`practical_<kind>[_native_*]_handoff\|outputs`); estimator ends at a verified completion proof. | `import:communication` (1), `import:numerical` (1), `import:practical_yield` (1), `name:PracticalYieldEstimator` (1), `name:YieldController` (1), `name:YieldParameters` (1) |
