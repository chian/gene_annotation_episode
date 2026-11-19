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

## Carried over

One row per old function, class and method (`runs/carry_over/functions/...tsv`). Kind: `machinery` (old runner, not carried), `episode function` (new place), `unplaced` (not carried, reported with its reason). Carried 19 November 2026 into the ten-file form; the library calls are `episode_support/...` names, the job service is BLOCKED-ON-JOB-SERVICE (see the blocked file).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_outcome.py | _outcome | machinery | the old outcome envelope (completed/invalid): a tool returns its own outcome, a rejected answer is Rejected in task.py action |
| binding_record.py | HPCExecutionBindingRecord | machinery | the binding's own as_record() (README 3) |
| binding_record.py | HPCExecutionBindingRecord.as_record | machinery | the binding's own as_record() (README 3) |
| closed_credit.py | HPCExecutionClosedCredit | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | HPCExecutionClosedCredit._closed_credit_carrier | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | HPCExecutionClosedCredit._closed_credit_receipts | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | HPCExecutionClosedCredit._closed_credit_value | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | HPCExecutionClosedCredit._closed_credit_facts | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | HPCExecutionClosedCredit._closed_operational_credit_view | machinery | frozen closed credit from runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| completion.py | HPCExecutionCompletion | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py _completion |
| completion.py | HPCExecutionCompletion.completion_for_action | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py _completion |
| completion.py | HPCExecutionCompletion._closed_completion_verdict | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py _completion |
| completion.py | HPCExecutionCompletion.verify_completion | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py _completion |
| configuration.py | HPCExecutionConfiguration | episode function | the values become ctx.settings (resource, coordinator_workspace, initial_information, launch/tool-knowledge directories, task_yield_profiles; task.py _operations and _resource, yield_estimator.py _task_yield_profile); the old-runner wiring (providers, readers, progress provider) is not carried |
| configuration.py | HPCExecutionConfiguration.__init__ | episode function | the values become ctx.settings (resource, coordinator_workspace, initial_information, launch/tool-knowledge directories, task_yield_profiles; task.py _operations and _resource, yield_estimator.py _task_yield_profile); the old-runner wiring (providers, readers, progress provider) is not carried |
| credit.py | HPCExecutionCredit | episode function | credit.py credit (the old operational credit) |
| credit.py | HPCExecutionCredit.credit_kind | machinery | constant 'operational': no credit kind in the final form; credit.py is the operational credit |
| credit.py | HPCExecutionCredit.project_credit | episode function | credit.py credit (the closed-view branch is machinery: frozen closed credit) |
| credit.py | HPCExecutionCredit._live_project_credit | episode function | credit.py credit (project_practical_credit over the summary's receipts); the applies() calls of the result readers are machinery |
| credit.py | HPCExecutionCredit.credit_view | episode function | credit.py credit |
| decision_context.py | HPCExecutionTaskContext | machinery | generic old-runner decision context (working state, visible refs, pending work, report deliveries, runtime_actions); what is the episode's own is in messages/internal_summary.py and task.py decide |
| decision_context.py | HPCExecutionTaskContext.assemble_decision_context | machinery | generic old-runner decision context (working state, visible refs, pending work, report deliveries, runtime_actions); what is the episode's own is in messages/internal_summary.py and task.py decide |
| decision_context.py | _bind_preserved_runtime_providers | machinery | generic old-runner decision context (working state, visible refs, pending work, report deliveries, runtime_actions); what is the episode's own is in messages/internal_summary.py and task.py decide |
| decision_contracts.py | HPCExecutionTaskDecisionContracts | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | HPCExecutionTaskDecisionContracts.interpretation_context | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | HPCExecutionTaskDecisionContracts.exchange_schema | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | HPCExecutionTaskDecisionContracts.exchange_response | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | HPCExecutionTaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | HPCExecutionTaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | decision-exchange contract validation (saved-request checks, request_context exchange) |
| decision_exchange.py | HPCExecutionTaskDecisionExchange | machinery | the decision-exchange loop (exchange_decision) |
| decision_exchange.py | HPCExecutionTaskDecisionExchange.exchange_decision | machinery | the decision-exchange loop (exchange_decision) |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | the decision-exchange loop (exchange_decision) |
| decision_provider.py | HPCExecutionTaskDecisionProvider | machinery | provider routing of the decision prompt (complete_with_presentation, provider patching) |
| decision_provider.py | HPCExecutionTaskDecisionProvider.decision_completion | machinery | provider routing of the decision prompt (complete_with_presentation, provider patching) |
| episode.py | ExecutionEpisode | episode function | episode.py HPCJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py action: only ToolCall exec_command is offered |
| from_parent.py | HPCExecutionFromParent | episode function | messages/read_from_parent.py |
| from_parent.py | HPCExecutionFromParent.required_return_sources | machinery | returned () always (the parent selects return fields, README 3b C4) |
| from_parent.py | HPCExecutionFromParent.child_assignment_schema | unplaced | the frozen-request enum (a launch parent under an hpc ancestor may pass only its already authorised hpc request) is a check of a commission against the parent's own assignment: no check of a commission (rule 1); the parent's msg_to_child copies its authorised request. Reported in contract_misfits |
| from_parent.py | HPCExecutionFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | HPCExecutionFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment); the checks against the commissioning launch request (masking, utility, versions, BLAST database inputs) are checks of a commission and are not carried |
| from_parent.py | HPCExecutionFromParent.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM field record_refs (the records the job inputs name, passed in custody) |
| goal.py | HPCExecutionGoal | episode function | goal.py GOAL and task.py GOAL_INSTRUCTION / _instructions |
| goal.py | HPCExecutionGoal.instructions | episode function | goal.py GOAL and task.py GOAL_INSTRUCTION / _instructions |
| instructions.py | instructions | episode function | task.py _instructions (specialist text, tool knowledge, launch library; the child-delivery repair, wait and exchange-protocol paragraphs describe actions that no longer exist and are not carried) |
| instructions.py | _bind_preserved_runtime_providers | machinery | provider patching |
| internal_summary.py | HPCExecutionInternalSummary | episode function | messages/internal_summary.py |
| internal_summary.py | HPCExecutionInternalSummary._with_selected_execution_task | machinery | returned its value unchanged for hpc (no selected-execution-task view): nothing to carry |
| internal_summary.py | HPCExecutionInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| native_actions.py | HPCExecutionNativeActions | episode function | task.py TOOLS / exec_command (the parent-input check before execution is a commission check and is not carried) |
| native_actions.py | HPCExecutionNativeActions.catalog | episode function | task.py TOOLS / exec_command (the parent-input check before execution is a commission check and is not carried) |
| native_actions.py | HPCExecutionNativeActions.execute | episode function | task.py TOOLS / exec_command (the parent-input check before execution is a commission check and is not carried) |
| native_assignment.py | HPCExecutionNativeAssignment | episode function | messages/read_from_parent.py |
| native_assignment.py | HPCExecutionNativeAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (the transport's validate_assignment) |
| native_assignment.py | HPCExecutionNativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| native_assignment.py | HPCExecutionNativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| native_completion.py | HPCExecutionNativeCompletion | machinery | completion proof / practical estimator: CompletionYieldController in yield_estimator.py, the proof in messages/internal_summary.py _completion |
| native_completion.py | HPCExecutionNativeCompletion.completion_for_action | machinery | completion proof / practical estimator: CompletionYieldController in yield_estimator.py, the proof in messages/internal_summary.py _completion |
| native_completion.py | HPCExecutionNativeCompletion.practical_estimator | machinery | completion proof / practical estimator: CompletionYieldController in yield_estimator.py, the proof in messages/internal_summary.py _completion |
| native_configuration.py | HPCExecutionNativeConfiguration | episode function | task.py _operations (TerminalExecution of the configured PBS resource, from ctx.settings) and settings |
| native_configuration.py | HPCExecutionNativeConfiguration.__init__ | episode function | task.py _operations (TerminalExecution of the configured PBS resource, from ctx.settings) and settings |
| native_configuration.py | HPCExecutionNativeConfiguration._operations | episode function | task.py _operations (TerminalExecution of the configured PBS resource, from ctx.settings) and settings |
| native_configuration.py | HPCExecutionNativeConfiguration.as_record | machinery | the binding's own as_record() (README 3) |
| native_credit.py | HPCExecutionNativeCredit | episode function | credit.py credit |
| native_credit.py | HPCExecutionNativeCredit.credit_kind | machinery | constant 'operational' |
| native_credit.py | HPCExecutionNativeCredit.credit_view | episode function | credit.py credit |
| native_execution_service.py | TerminalExecutionBehavior | machinery | mix-in composition of the practical executor behaviour (child_roles () and tool-only common actions are CHILD_SLOTS = {} and task.py action) |
| native_execution_service.py | TerminalExecutionBehavior.child_roles | machinery | mix-in composition of the practical executor behaviour (child_roles () and tool-only common actions are CHILD_SLOTS = {} and task.py action) |
| native_execution_service.py | TerminalExecutionBehavior.permitted_common_actions | machinery | mix-in composition of the practical executor behaviour (child_roles () and tool-only common actions are CHILD_SLOTS = {} and task.py action) |
| native_execution_service.py | TerminalExecutionBehavior.allowed_children | machinery | mix-in composition of the practical executor behaviour (child_roles () and tool-only common actions are CHILD_SLOTS = {} and task.py action) |
| native_goal.py | HPCExecutionNativeGoal | episode function | task.py GOAL_INSTRUCTION and _instructions |
| native_goal.py | HPCExecutionNativeGoal._resource_instructions | episode function | task.py GOAL_INSTRUCTION and _instructions |
| native_goal.py | HPCExecutionNativeGoal.instructions | episode function | task.py GOAL_INSTRUCTION and _instructions |
| native_internal_summary.py | HPCExecutionNativeInternalSummary | episode function | task.py decide and messages/internal_summary.py |
| native_internal_summary.py | HPCExecutionNativeInternalSummary.initial_decision_context | episode function | task.py decide (execution_resource_information from settings) |
| native_internal_summary.py | HPCExecutionNativeInternalSummary._resource_information | episode function | task.py _resource |
| native_internal_summary.py | HPCExecutionNativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| native_receipt_state.py | HPCExecutionNativeReceiptState | machinery | PracticalState bookkeeping (intent/receipt files, begin/finish idempotency): the system's attempts journal and ctx.operation_key; the receipt is a tool outcome and a held artifact |
| native_receipt_state.py | HPCExecutionNativeReceiptState._state_directory | machinery | PracticalState bookkeeping (intent/receipt files, begin/finish idempotency): the system's attempts journal and ctx.operation_key; the receipt is a tool outcome and a held artifact |
| native_receipt_state.py | HPCExecutionNativeReceiptState.initialize | machinery | PracticalState bookkeeping (intent/receipt files, begin/finish idempotency): the system's attempts journal and ctx.operation_key; the receipt is a tool outcome and a held artifact |
| native_receipt_state.py | HPCExecutionNativeReceiptState.state | machinery | PracticalState bookkeeping (intent/receipt files, begin/finish idempotency): the system's attempts journal and ctx.operation_key; the receipt is a tool outcome and a held artifact |
| native_return.py | HPCExecutionNativeReturn | episode function | messages/final_to_parent.py |
| native_return.py | HPCExecutionNativeReturn.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| native_return.py | HPCExecutionNativeReturn.facts | episode function | messages/final_to_parent.py _facts |
| native_return.py | HPCExecutionNativeReturn.resolve | machinery | resolution of references named in a report (the system admits record_refs fields against custody) |
| native_return.py | HPCExecutionNativeReturn.validate_report | episode function | messages/final_to_parent.py validate_report (called by final_to_parent); the form validation of the old body is the system's admission of RETURN_FORM |
| native_state.py | HPCExecutionNativeState | machinery | filesystem state of the results role (assignment manifest of the results directory): hpc launch has no results; custody replaces files |
| native_state.py | HPCExecutionNativeState.initialize | machinery | filesystem state of the results role (assignment manifest of the results directory): hpc launch has no results; custody replaces files |
| native_state.py | HPCExecutionNativeState._result_directory | machinery | filesystem state of the results role (assignment manifest of the results directory): hpc launch has no results; custody replaces files |
| native_tool_actions.py | HPCExecutionNativeToolActions | episode function | task.py exec_command (tool) and EXEC_COMMAND (catalog); the intent/receipt state (begin/finish) is machinery, the receipt, context tracking, validations and failure outcome are in the tool |
| native_tool_actions.py | HPCExecutionNativeToolActions.catalog | episode function | task.py exec_command (tool) and EXEC_COMMAND (catalog); the intent/receipt state (begin/finish) is machinery, the receipt, context tracking, validations and failure outcome are in the tool |
| native_tool_actions.py | HPCExecutionNativeToolActions.execute | episode function | task.py exec_command (tool) and EXEC_COMMAND (catalog); the intent/receipt state (begin/finish) is machinery, the receipt, context tracking, validations and failure outcome are in the tool |
| native_tool_contracts.py | operation_catalog | episode function | task.py EXEC_COMMAND |
| parent_launch_contract.py | parent_launch_schema | machinery | the commissioning launch's own schema, used to re-validate the parent's request from runtime_episodes: a check of a commission |
| parent_request_contracts.py | HPCExecutionParentRequestContracts | episode function | messages/read_from_parent.py and task.py _operations (only _validate_request); the rest are commission checks |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._check_parent_inputs | machinery | check of a commission against the parent's launch request (read from runtime_episodes): a wrong commission fails (rule 1) |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._permitted | machinery | check of a commission against the parent's launch request (read from runtime_episodes): a wrong commission fails (rule 1) |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._request_schema | machinery | check of a commission against the parent's launch request (read from runtime_episodes): a wrong commission fails (rule 1) |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (the transport's validate_assignment) |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._launch | machinery | check of a commission against the parent's launch request (read from runtime_episodes): a wrong commission fails (rule 1) |
| parent_request_contracts.py | HPCExecutionParentRequestContracts._constraints | machinery | check of a commission against the parent's launch request (read from runtime_episodes): a wrong commission fails (rule 1) |
| presentation.py | present_execution_context | episode function | task.py _task_text and decide (the HPC prompt presentation over this episode's own summary; the provider presentation-state machinery is not carried) |
| protected_reference_access.py | ProtectedReferenceAccess | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._install_protected_reference_readers | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._protein_reference_access | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._fluorescence_reference_access | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._expression_nmf_reference_access | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._atac_reference_access | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| protected_reference_access.py | ProtectedReferenceAccess._chromatin_reference_access | machinery | installation of protected reference readers for resolving references named in a report (report reference resolution) |
| receipt_selection.py | HPCExecutionReceiptSelection | machinery | receipts bookkeeping (selection of received records) |
| receipt_selection.py | HPCExecutionReceiptSelection._selection | machinery | receipts bookkeeping (selection of received records) |
| receipt_selection.py | HPCExecutionReceiptSelection._received | machinery | receipts bookkeeping (selection of received records) |
| received_action_identity.py | HPCExecutionReceivedActionIdentity | machinery | receipts bookkeeping (identity of the selected result action) |
| received_action_identity.py | HPCExecutionReceivedActionIdentity._selected_result_action | machinery | receipts bookkeeping (identity of the selected result action) |
| received_parent_records.py | HPCExecutionReceivedParentRecords | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords._has_appservice | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords._has_uniprot | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords._appservice_sources | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords._forwards_bvbrc_reports | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords.received_report_sources | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords.received_report_facts | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_parent_records.py | HPCExecutionReceivedParentRecords.received_report_closure_facts | machinery | received report sources and facts read from receipts and runtime_* tables (custody replaces them) |
| received_reference_access.py | HPCExecutionReceivedParentRecordsReferenceAccess | machinery | resolution of received references (custody) |
| received_reference_access.py | HPCExecutionReceivedParentRecordsReferenceAccess._masking_reference_access | machinery | resolution of received references (custody) |
| received_reference_access.py | HPCExecutionReceivedParentRecordsReferenceAccess._utility_reference_access | machinery | resolution of received references (custody) |
| received_reference_access.py | HPCExecutionReceivedParentRecordsReferenceAccess.resolve_received_reference | machinery | resolution of received references (custody) |
| received_report_admission.py | HPCExecutionReceivedParentRecordsAdmission | machinery | admission of received reports (the system admits results against the child's form) |
| received_report_admission.py | HPCExecutionReceivedParentRecordsAdmission.validate_received_report | machinery | admission of received reports (the system admits results against the child's form) |
| received_report_admission.py | HPCExecutionReceivedParentRecordsAdmission.received_form_references | machinery | admission of received reports (the system admits results against the child's form) |
| received_result_custody.py | HPCExecutionReceivedResultCustody | machinery | custody of received result bodies of the results role (system custody) |
| received_result_custody.py | HPCExecutionReceivedResultCustody._validate_result_body | machinery | custody of received result bodies of the results role (system custody) |
| received_result_custody.py | HPCExecutionReceivedResultCustody._read_result | machinery | custody of received result bodies of the results role (system custody) |
| report_delivery.py | HPCExecutionReportDelivery | machinery | report finish, runtime_forms and release (report_form machinery) |
| report_delivery.py | HPCExecutionReportDelivery.finish | machinery | report finish, runtime_forms and release (report_form machinery) |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | report finish, runtime_forms and release (report_form machinery) |
| report_fields.py | HPCExecutionToParentFields | episode function | messages/final_to_parent.py RETURN_FORM |
| report_fields.py | HPCExecutionToParentFields.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| report_reference_access.py | HPCExecutionToParentReferenceAccess | machinery | resolution of references in the report (the system admits record_refs fields against custody) |
| report_reference_access.py | HPCExecutionToParentReferenceAccess.resolve | machinery | resolution of references in the report (the system admits record_refs fields against custody) |
| resource_information.py | HPCExecutionResourceInformation | episode function | task.py _resource / decide (the hpc part); the resource list and commission routes are the parent's own text |
| resource_information.py | HPCExecutionResourceInformation._resource_information | episode function | task.py _resource (the hpc resource; the api configuration facts do not apply to hpc) |
| resource_information.py | HPCExecutionResourceInformation.initial_decision_context | episode function | task.py decide (execution_resource_information); the received BV-BRC values and BLAST jobs are for api and scientific roles |
| resource_information.py | HPCExecutionResourceInformation.capabilities | unplaced | configured operation availability of every bound resource, shown to the commissioning parent's model when it picks a resource: the parent's own text, not this episode's |
| resource_information.py | HPCExecutionResourceInformation.resource_tool_contracts | unplaced | commission routes and tool contracts of every resource, for the commissioning parent's model: the parent's own text, not this episode's |
| resource_operations.py | launch_operation_catalog | unplaced | declared launch operation execution.capabilities (read the configured resource) belonged to the parent's catalogue; the resource is in this episode's decide context |
| result_operations.py | native_result_operation_catalog | unplaced | catalogue of the results role (execution.results.status / collect / read): belongs to the result acquisition episode |
| retained_native_receipts.py | HPCExecutionRetainedNativeReceipts | machinery | delegate to the practical state of the resource role (receipts bookkeeping) |
| retained_native_receipts.py | HPCExecutionRetainedNativeReceipts._delegate | machinery | delegate to the practical state of the resource role (receipts bookkeeping) |
| retained_native_receipts.py | HPCExecutionRetainedNativeReceipts._practical_context | machinery | delegate to the practical state of the resource role (receipts bookkeeping) |
| retained_native_receipts.py | HPCExecutionRetainedNativeReceipts.state | machinery | delegate to the practical state of the resource role (receipts bookkeeping) |
| scientific_inputs.py | HPCExecutionScientificInputs | machinery | check of a commission's masking, utility and pinned input versions against the parent's request: a wrong commission fails (rule 1) |
| scientific_inputs.py | HPCExecutionScientificInputs._masking_inputs | machinery | check of a commission's masking, utility and pinned input versions against the parent's request: a wrong commission fails (rule 1) |
| scientific_inputs.py | HPCExecutionScientificInputs._utility_inputs | machinery | check of a commission's masking, utility and pinned input versions against the parent's request: a wrong commission fails (rule 1) |
| scientific_inputs.py | HPCExecutionScientificInputs._versions | machinery | check of a commission's masking, utility and pinned input versions against the parent's request: a wrong commission fails (rule 1) |
| selector_contracts.py | HPCExecutionSelectorContracts | machinery | validation of result selectors for the results role (a commission to result acquisition): not this episode's, and a commission check |
| selector_contracts.py | HPCExecutionSelectorContracts._masking_selector | machinery | validation of result selectors for the results role (a commission to result acquisition): not this episode's, and a commission check |
| selector_contracts.py | HPCExecutionSelectorContracts._utility_selector | machinery | validation of result selectors for the results role (a commission to result acquisition): not this episode's, and a commission check |
| selector_contracts.py | HPCExecutionSelectorContracts._selector | machinery | validation of result selectors for the results role (a commission to result acquisition): not this episode's, and a commission check |
| selector_contracts.py | HPCExecutionSelectorContracts._windows | machinery | validation of result selectors for the results role (a commission to result acquisition): not this episode's, and a commission check |
| target_custody.py | HPCExecutionTargetCustody | machinery | authentication of the handed-off target for the results role (receipt custody) |
| target_custody.py | HPCExecutionTargetCustody._retained_masking_target | machinery | authentication of the handed-off target for the results role (receipt custody) |
| target_custody.py | HPCExecutionTargetCustody._retained_utility_target | machinery | authentication of the handed-off target for the results role (receipt custody) |
| target_custody.py | HPCExecutionTargetCustody._target | machinery | authentication of the handed-off target for the results role (receipt custody) |
| target_custody.py | HPCExecutionTargetCustody._context_target | machinery | authentication of the handed-off target for the results role (receipt custody) |
| task.py | HPCExecutionTask | machinery | the old task class (mix-in composition of the decision machine): task.py decide, action and exec_command |
| task.py | HPCExecutionTask.next | machinery | the old decision loop with checkpoint/restore, completions and pending deliveries; task.py decide and action |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching |
| task_action.py | HPCExecutionTaskAction | episode function | task.py action and exec_command |
| task_action.py | HPCExecutionTaskAction.apply_response | episode function | task.py action (the answer is decoded, validated against EXEC_COMMAND's schema and the resource, rejected with Rejected otherwise) |
| task_action.py | HPCExecutionTaskAction.execute | episode function | task.py exec_command (the journalled action, score, credit and controller input are the system's: machinery) |
| task_action.py | _bind_preserved_runtime_providers | machinery | provider patching |
| task_decision.py | HPCExecutionTaskDecision | episode function | task.py decide |
| task_decision.py | HPCExecutionTaskDecision.call | episode function | task.py decide (the context of the model request; the old-runner assembly, journalling of the model call and the exchange are machinery) |
| task_decision.py | HPCExecutionTaskDecision.instructions | episode function | task.py _instructions |
| task_decision.py | HPCExecutionTaskDecision.conversation_key | machinery | conversation state across calls: every ModelRequest carries the full context |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching |
| task_state.py | HPCExecutionTaskState | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.__init__ | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.bind_execution_context | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.record_execution_failure | episode function | task.py _failure and exec_command (a failed command is a returned outcome with its receipt) |
| task_state.py | HPCExecutionTaskState.restore_checkpoint | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.restore | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.record_effect | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | HPCExecutionTaskState.checkpoint | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| task_state.py | _bind_preserved_runtime_providers | machinery | task state, checkpoint, restore and effect records (the system journals units and restores the view) |
| to_parent.py | HPCExecutionToParent | episode function | messages/final_to_parent.py |
| to_parent.py | HPCExecutionToParent.facts | episode function | messages/final_to_parent.py _facts |
| to_parent.py | HPCExecutionToParent._live_facts | episode function | messages/final_to_parent.py _facts (the native empty families; the handoff references come from the summary's receipts; the masking and utility families cannot be form fields; the file-capture, BV-BRC and AppService facts do not apply to hpc) |
| to_parent.py | HPCExecutionToParent.validate_report | episode function | messages/final_to_parent.py validate_report (the masking, utility and UniProt received-report checks belong to the results role) |
| waiting.py | HPCExecutionWaiting | machinery | suspension/wait machinery (set_suspension) |
| waiting.py | HPCExecutionWaiting.suspension_changed | machinery | suspension/wait machinery (set_suspension) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py _request_yield_class (library candidate; the api branch does not apply) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile (library candidate) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (the private-yield flag is configuration machinery) |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController replaces YieldController with PracticalYieldEstimator) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | the practical estimator (PracticalYieldEstimator): CompletionYieldController |
