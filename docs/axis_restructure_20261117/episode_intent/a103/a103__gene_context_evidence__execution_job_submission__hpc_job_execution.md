# a103/gene_context_evidence/execution_job_submission/hpc_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/execution_job_submission/hpc_job_execution/<file>`,
only the 45 files directly in the folder (2675 lines). There is no `grading/` or `scoring/` subfolder, and `tests/`
was not read. Old-runner names are listed per file below and in `runs/carry_over/calls/a103_01.tsv`.

## What it is for (its goal, in its own words)

The A103 HPC job execution episode (role `launch_hpc`), commissioned only by the launch episode. An LLM execution
agent runs shell commands on the assigned HPC resource to carry out the job. Its goal is the terminal instructions
(`terminal_goal.py`, returned through `goal.py`):

> "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the
> shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the
> actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed.
> Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context,
> not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit
> enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native
> job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that
> original submission rather than create a duplicate. … target=resource runs on the assigned resource;
> target=coordinator runs in the local run directory for supplied-input and transport work. … For coordinator-side
> transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. … The episode
> iterator decides continuation from credit; add no stopping budget."

The frozen launch-library resource instructions for the resource are appended to this text.

## Task and instructions

`instructions.py` has the launch composition, including the reasoning-commit text, but `action_policy.py` permits only
`tool`. `task.py` (NativeTask, grain `launch_hpc`) has the launch loop shape.

## What it reads from its parent's assignment

`from_parent.py`: under an `hpc` ancestor, `child_assignment_schema` is an `enum` of the HPC requests that are already
frozen and permitted in the launch assignment (`frozen_hpc_launch_request_missing` when there are none). Otherwise it is
the HPC resources' selected request schemas. `prepare_assignment` validates the practical request (workspace confined
to the resource workspace; the resource operations' validator), requires the parent role to be `launch`, and checks
masking/utility inputs, input versions and native/standard BLAST inputs. `terminal_assignment.py`: resource_kind must
equal the role kind (`hpc`) and be configured. `operations._check_parent_inputs` re-validates against the parent launch
request read from `runtime_episodes`.

## Children it may commission

None (`child_eligibility.py`).

## Decision state and what it shows the model

`decision_state.py` has the same field set as the launch parent. `internal_summary.py` delegates to
`terminal_summary.decision_context`: execution_assignment, execution_resource (resource_kind, workspace, kind,
policy, account, ssh_argv, python_executable, scheduler, inventory_snapshot), coordinator_workspace,
execution_progress (practical state credit view) and execution_completion (completion proof). The initial context is
execution_resource_information. `decision_presentation.py` (`present_native_task`) uses the same renderer selection as
the launch parent.

## Tools it offers

`exec_command` only (`terminal_contracts.py`): `cmd` (string or argv), `workdir`, `env` (all required) and `target`
(`resource` default | `coordinator`). `terminal_operations.py`: the action is validated, then begun on the practical state.
It is idempotent by operation key, so a completed intent returns its receipt. It runs through `TerminalExecution` (artifact
selector `terminal_artifact_paths`), is finalized as a scientific command, and the cwd/env context revision is
updated for resource targets inside the workspace. Validations are assessed and the receipt is saved and published as a
`practical_receipt` record. Failures become an outcome (`execution_action_failed`), not an exception.

## How its credit is counted

`credit.py`: kind `operational`. The closed view comes first, then a native family's view, else the terminal delegate's
`credit_view`, which is the practical state's credit view (`terminal_credit.py`). Completion: native family proofs, else the
state's completion proof for the operation key. `verify_completion` falls through to the state's `verify_completion`.

## Continuation (yield estimator and settings)

`yield_estimator.py`: YieldController(epoch, initial_credit, cutoff of task profile `launch_hpc:<request class>`,
parameters, estimate_with_context = the delegate's `practical_estimator` = PracticalYieldEstimator(state.verify_completion)).
This is the completion kind. It needs `require_private_yield`. Request class: `practical_hpc[_native_*…]_<handoff|outputs>`.

## What it reports to its parent

`to_parent.py`: the launch fact sources plus `practical_completed`, `practical_receipt_digests` and `practical_receipt_refs`
(`terminal_report.py`). Facts: the delegate's facts. Each returnable practical receipt target is added to
`execution_handoff_refs`; results, file sources, outcomes and origin are as in launch. `execution_completed` =
`practical_completed`. `validate_report` requires x-source fields to equal the recorded facts.

## Differences from similar episodes

- Against its sibling api_job_execution: `tool` only (API also has `wait`); an instruction-led shell agent instead of service
  operations; credit/completion from the practical terminal state; the frozen-request `enum` under an HPC
  ancestor; no BLAST launch-selection check; the shared renderer selector instead of an own API prompt.
- This episode splits the launch parent's single-file `terminal_execution.py` into `terminal_assignment`, `terminal_contracts`,
  `terminal_credit`, `terminal_goal`, `terminal_operations`, `terminal_report`, `terminal_state` and `terminal_summary`. The
  behaviour is the same, and the terminal goal text ("add no stopping budget") lives in `terminal_goal.py`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (name×uses) |
|---|---|---|---|
| action_policy.py | 9 | Permitted actions: tool only. | none |
| binding_record.py | 9 | As the launch parent's, binding_id gene_context_evidence/execution_job_submission/hpc_job_execution. | none |
| child_eligibility.py | 10 | No child roles, no allowed children. | none |
| closed_credit.py | 117 | Same as the launch parent's closed_credit.py (class renamed): Closed operational credit: validates closed runtime metadata, pins the original receipt prefix, captures the projected view once in closing facts and returns only that view later (no repricing). | BindingContext.episode_id×8, BindingContext.role×1, import:episode_receipts×1, import:episode_return_records×3, table:runtime_episodes×2, table:runtime_forms×3, table:runtime_observations×1, table:runtime_receipt_inheritance×2, table:runtime_record_receipts×2 |
| completion.py | 65 | Native-family completion proofs as launch, then the practical delegate's completion_for_action; verify_completion ends in this episode's practical state verify_completion. | BindingContext.assignment×1, BindingContext.episode_id×4, import:episode_return_records×1, import:method_loop.identities×1, import:numerical×1, import:practical_yield×1, table:runtime_observations×1, yield:NumericBand×2 |
| configuration.py | 65 | Same as the launch parent's configuration.py (class renamed): Operands: services, store, directory, run_id, resources (kind local/pbs_ssh/hmmer_api/api), initial_information, tool_registry, handoff_unit and acquired_record_unit (finite > 0), log_window_bytes, log_roles, require_private_yield, results_yield_profiles (native_unbounded_local/hpc), task_yield_profiles ({cutoff>0, parameters}). Only A103 native resource bindings allowed; builds TerminalExecutionBehavior per non-API resource, APIServiceExecution, ExecutionProgressProvider, LocalFileSourceResults; installs result readers. | import:api_service_execution×1, import:execution_progress×1, import:numerical×1, svc.read_received_molecular_input×1, yield:YieldController×3, yield:YieldParameters×3 |
| contracts.py | 60 | As the launch parent's contracts; imports its own terminal_execution and operation_catalog from terminal_contracts. | import:a103_execution_bindings×1, import:a103_homology_execution×1, import:communication×1, import:domain×1, import:execution_contracts×1, import:launch_instructions×1, import:local_file_capture_results×1, import:native_blast_acquisition×1, import:native_blast_database_acquisition×1, import:native_blast_masking_acquisition×1, import:native_blast_standard_database_acquisition×1, import:native_blast_utility_acquisition×1, import:native_hmmer_acquisition×1, import:native_hmmer_preparation_acquisition×1, import:practical_execution_operations×1, import:practical_execution_records×1, import:practical_execution_state×1, import:practical_receipt_information×1, import:resource_records×1 |
| credit.py | 39 | Credit kind operational; closed view, else native family view, else the practical (terminal) delegate's credit_view = practical state credit. | none |
| decision_contracts.py | 36 | Same as the launch parent's decision_contracts.py (class renamed): Exchange envelope: request_context(lookup) or select_action(selection, report_update). | import:runtime×2, runtime.composition_lookup_schema×2, runtime.Draft202012Validator×1, runtime._object×3 |
| decision_delivery.py | 82 | Same as the launch parent's decision_delivery.py (class renamed): Model call for the launch decision (saved call replay, exchange protocol, provider dispatch); composes LaunchDecisionInputs/Contracts/SavedDecisionExchange/DecisionExchange/Provider. | import:runtime×2, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×1, wf.provider.has_session×1, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2, table:runtime_model_calls×5 |
| decision_exchange.py | 116 | Same as the launch parent's decision_exchange.py (class renamed): Pending-decision lookup exchange and the interpretation context derived from received lookups. | import:runtime×2, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×1, runtime._plain×2, runtime._references_in×1, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.store×2, wf.store.reference_subset×1, wf.validate_contract_information×1, table:runtime_model_calls×2 |
| decision_inputs.py | 70 | As launch, with execution_expectations captured for role launch_hpc. | import:episode_work_report×2, import:library.hpc_prompt×1, import:runtime×2, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| decision_presentation.py | 59 | present_native_task: same renderer selection and prompt-state keeping as the launch parent. | import:gene_context_evidence_prompt×1, import:library.hpc_prompt×1, import:library.monitor_prompt×1, import:native_profile_presentation×1, import:providers×2, import:receiver_prompt×1, providers.apply_state_frame×3, providers.DECISION_CONTEXT_VERSION×1, providers.deepcopy×1, providers.is_api_launch_context×2, providers.is_published_scientific_context×2, providers.json×1, providers._ordinary_runtime_receiver_context×1, providers.render_api_launch_prompt×1, providers.render_gene_context_evidence_prompt×1, providers.text_instructions×1 |
| decision_provider.py | 18 | Same as the launch parent's decision_provider.py (class renamed): Provider dispatch with this binding's prompt renderer under conversation 'REASONING'. | import:runtime×1, wf.provider×2, wf.provider.conversation_key×1, wf.specialist×1 |
| decision_state.py | 45 | Same as the launch parent's decision_state.py (class renamed): Decision context shown to the model (same field set as the scientific task) plus the launch binding's decision_context. | import:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, wf.binding_context×1, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.store.reference_subset×1, wf.tools×1, wf.tools.model_contract_catalog×1, wf.working_state×1, table:runtime_actions×2 |
| episode.py | 31 | ExecutionEpisode at gene_context_evidence/execution_job_submission/hpc_job_execution, commissioning_parent the launch episode, roles (launch_hpc,), entry_roles (), renderer present_native_task. | none |
| from_parent.py | 130 | child_assignment_schema under an hpc ancestor = enum of the frozen, permitted HPC requests already in the launch assignment; otherwise selected HPC request schemas; prepare_assignment validates like the API child without API validation or BLAST launch selection check. | BindingContext.assignment×4, BindingContext.path×2, BindingContext.role×6, import:native_blast_database_result_publication×2, import:native_blast_standard_database_result_publication×2, svc.annotation_task_required×1 |
| goal.py | 7 | Goal = the terminal delegate's instructions (exec_command execution agent text + frozen resource instructions). | none |
| __init__.py | 0 | Same as the launch parent's __init__.py (class renamed): Empty package marker. | none |
| instructions.py | 22 | As launch (keeps reasoning-commit text, though reason is not permitted). | import:runtime_prompt×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×1, wf.decision_protocol×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| internal_summary.py | 94 | Decision context = terminal delegate's decision_context (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion). | BindingContext.assignment×1, BindingContext.role×3 |
| operations.py | 48 | initialize/execute check the parent launch request, then delegate to TerminalExecutionBehavior; state() exposes the practical state for launch_local/launch_hpc. | BindingContext.assignment×5, BindingContext.path×3, BindingContext.role×2, BindingContext.scope×1, import:native_blast_database_result_publication×1, import:native_blast_standard_database_result_publication×1, table:runtime_episodes×1 |
| received_information.py | 113 | Same as the launch parent's received_information.py (class renamed): Which received child report sources are forwarded (BVBRC, minhash) and received report facts / closure facts. | BindingContext.request×2, BindingContext.role×11, import:blast_pairwise_result_views×1, import:blast_utility_result_views×1, import:bvbrc_data_views×1, import:bvbrc_minhash_views×1, import:hmmer_preparation_result_views×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_result_views×1, import:sequence_masking_result_views×1, import:uniprot_return_contracts×1 |
| received_record_selection.py | 35 | Same as the launch parent's received_record_selection.py (class renamed): Receipt-scoped selection of handoffs and results from received records (initial known refs, handoffs, results). | BindingContext.assignment×1, BindingContext.role×1, BindingContext.scope×2 |
| received_reference_custody.py | 160 | Same as the launch parent's received_reference_custody.py (class renamed): Resolve references received from children, validate received typed reports, collect received form references. | BindingContext.role×10, import:bvbrc_homology_returns×1, import:hmmer_native_result_views×1 |
| report_delivery.py | 25 | Same as the launch parent's report_delivery.py (class renamed): finish(): same as the scientific parent (credit + pending handles, or saved form from facts). | import:library.private_policy_call×1, import:library.report_fact_assembly×1, import:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1, table:runtime_forms×2 |
| report_reference_access.py | 115 | Same as the launch parent's report_reference_access.py (class renamed): Outgoing-report reference resolution; failures become denial. | BindingContext.role×12, BindingContext.scope×4, import:bvbrc_data_views×1, import:bvbrc_homology_returns×1, import:episode_bindings×2, import:hmmer_preparation_result_views×1, import:native_blast_database_results×1, import:native_blast_standard_database_results×1 |
| result_records.py | 260 | Same as the launch parent's result_records.py (class renamed): Result records: masking/utility selectors and inputs, input versions, handoff target lookup, selector validation, result directory, byte windows, selected result action, result body validation/read, context target checks, appservice/uniprot presence. | BindingContext.assignment×4, BindingContext.episode_id×9, BindingContext.role×3, BindingContext.run_id×2, BindingContext.scope×7, import:blast_pairwise_result_views×1, import:blast_utility_result_views×2, import:bvbrc_homology_returns×1, import:episode_receipts×1, import:execution_input_versions×1, import:hmmer_native_result_views×1, import:hmmer_preparation_result_views×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_result_views×1, import:sequence_masking_result_views×2, svc.record_selection×1, table:runtime_actions×2, table:runtime_episodes×1, table:runtime_receipt_inheritance×2 |
| saved_decision_exchange.py | 82 | Same as the launch parent's saved_decision_exchange.py (class renamed): Authenticate frozen contract-information requests and saved exchange history without dispatch. | import:runtime×2, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2, table:runtime_model_calls×1 |
| task.py | 226 | NativeTask loop (grain launch_hpc). | import:episode_source_failure×1, import:library.action_contracts×1, import:library.private_policy_call×1, import:providers×1, import:read_mapping×1, import:runtime×2, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime.ContractError×2, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×9, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime._plain×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×1, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×1, wf.store×8, wf.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_state.py | 108 | Same as the launch parent's task_state.py (class renamed): Launch decision state and checkpoint/restore (same shape as the scientific task_state). | import:episode_source_failure×1, import:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, table:runtime_actions×5 |
| terminal_assignment.py | 22 | Terminal assignment: practical assignment whose resource_kind matches the role kind and is configured; operations validate it. | BindingContext.assignment×1, BindingContext.role×1 |
| terminal_contracts.py | 24 | exec_command contract for local/hpc: cmd, workdir, env required, target resource|coordinator. | import:acquisition×1, import:communication×1, import:domain×1, import:practical_execution_operations×1, import:practical_execution_records×1, import:practical_execution_state×1, import:terminal_execution×1 |
| terminal_credit.py | 11 | credit_view = practical state credit; completion_for_action = state completion proof for that operation key. | none |
| terminal_execution.py | 41 | TerminalExecutionBehavior composed from the terminal_* parts (split of the launch parent's single-file terminal_execution); credit kind operational, actions tool only, no children, PracticalYieldEstimator from state.verify_completion. | import:practical_yield×1, yield:PracticalYieldEstimator×2 |
| terminal_goal.py | 18 | Execution-agent instructions: write and run shell code via exec_command, no prescribed sequence, keep scientific inputs/outputs/acceptance criteria, each command is one iterator action including failure/zero progress, do not duplicate uncertain submissions, coordinator vs resource targets, ssh_argv transport, "add no stopping budget"; plus frozen resource instructions. | BindingContext.assignment×1, svc.workflow×1 |
| terminal_operations.py | 47 | exec_command execution: validate, begin/finish state intent (idempotent by operation key), finalize_scientific_command, cwd/env context revision, assess validations, publish receipt as practical_receipt record. | BindingContext.assignment×5, BindingContext.run_id×1, import:practical_receipt_information×1, import:terminal_scientific_evidence×2 |
| terminal_report.py | 31 | Fact sources practical_completed, practical_receipt_digests, practical_receipt_refs; validate_report requires x-source fields equal facts. | BindingContext.run_id×2, import:practical_receipt_information×2 |
| terminal_state.py | 18 | Practical state directory per run/episode and lazy initialize with initial validations. | BindingContext.episode_id×4, BindingContext.run_id×2 |
| terminal_summary.py | 16 | Initial context execution_resource_information; decision context with resource information (workspace, kind, policy, account, ssh_argv, python_executable, scheduler, inventory). | BindingContext.assignment×2 |
| to_parent.py | 132 | Fact sources add practical_* for launch_local/launch_hpc; facts = delegate facts + handoffs (adds returnable practical receipt targets), results, file sources, origin, execution_completed = practical_completed. | BindingContext.scope×1, import:blast_pairwise_result_views×2, import:blast_result_views×1, import:blast_utility_result_views×2, import:bvbrc_data_views×1, import:bvbrc_minhash_views×1, import:hmmer_native_result_views×2, import:hmmer_preparation_result_views×2, import:local_file_capture_results×1, import:native_blast_database_results×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_results×1, import:native_blast_standard_database_result_views×1, import:native_hmmer_acquisition×1, import:sequence_masking_result_views×2, import:uniprot_return_contracts×2 |
| waiting.py | 9 | Same as the launch parent's waiting.py (class renamed): Record suspension condition and forward it to the execution backend. | wf.execution_backend×1, wf.execution_handle×2 |
| yield_estimator.py | 50 | Controller: YieldController(cutoff from task profile `launch_hpc:<request class>`, parameters) with the delegate's practical_estimator (PracticalYieldEstimator on the practical state's verify_completion). | BindingContext.assignment×1, BindingContext.role×1, import:numerical×1, import:practical_yield×1, yield:PracticalYieldEstimator×2, yield:YieldController×2, yield:YieldParameters×2 |

## Carried over

New files: `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/{read_from_parent,internal_summary,final_to_parent}.py` (no children: no `msg_to_child.py`, no `read_from_child.py`). Old files read with `git show 97308b94c:<path>`. Kind column of the first three: as in `runs/carry_over/functions/`. Rows marked UNPLACED are listed in `carry_over_blocked/a103__gene_context_evidence__execution_job_submission__hpc_job_execution.md`.

| old file | kind | name | classification | new place or machinery reason |
|---|---|---|---|---|
| action_policy.py | class | NativeActionPolicy | machinery | action policy: permitted actions are the loop's own; the episode offers only its exec_command tool unit |
| action_policy.py | method | NativeActionPolicy.permitted_common_actions | machinery | action policy: permitted actions are the loop's own; the episode offers only its exec_command tool unit |
| binding_record.py | class | NativeBindingRecord | machinery | the binding's own as_record() (binding_record.py) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | the binding's own as_record() (binding_record.py) |
| child_eligibility.py | class | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} (no child roles, no allowed children) |
| child_eligibility.py | method | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} (no child roles, no allowed children) |
| child_eligibility.py | method | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} (no child roles, no allowed children) |
| closed_credit.py | class | ClosedExecutionCredit | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_carrier | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_receipts | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_value | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_facts | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| closed_credit.py | method | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed operational credit: runtime_* table re-validation and receipt pinning; credit is the system's completion['credit'] (final_to_parent) |
| completion.py | class | ExecutionCompletion | machinery | native-family completion proofs and runtime_observations verdict (completion_for_action, _closed_completion_verdict): estimator completion-proof machinery, not carried |
| completion.py | method | ExecutionCompletion.completion_for_action | machinery | native-family completion proofs and runtime_observations verdict (completion_for_action, _closed_completion_verdict): estimator completion-proof machinery, not carried |
| completion.py | method | ExecutionCompletion._closed_completion_verdict | machinery | native-family completion proofs and runtime_observations verdict (completion_for_action, _closed_completion_verdict): estimator completion-proof machinery, not carried |
| completion.py | method | ExecutionCompletion.verify_completion | machinery | completion verification as controller input (README 3d: the completion proof is not a controller input); the proof is rebuilt in messages/internal_summary.py completion_proof |
| configuration.py | class | NativeConfiguration | machinery | constructor operands of the home factory; the values the episode reads are settings (ctx.settings: resource, coordinator_workspace, initial_information, launch_instruction_directory, task_yield_profiles) |
| configuration.py | method | NativeConfiguration.__init__ | machinery | constructor operands of the home factory; the values the episode reads are settings (ctx.settings: resource, coordinator_workspace, initial_information, launch_instruction_directory, task_yield_profiles) |
| contracts.py | function | launch_operation_catalog | episode function | UNPLACED: launch/results operation catalogue of the launch parent and the results role, not an operation of launch_hpc (its only tool is exec_command, task.py EXEC_COMMAND) |
| contracts.py | function | native_result_operation_catalog | episode function | UNPLACED: launch/results operation catalogue of the launch parent and the results role, not an operation of launch_hpc (its only tool is exec_command, task.py EXEC_COMMAND) |
| contracts.py | function | _outcome | episode function | UNPLACED: launch/results operation catalogue of the launch parent and the results role, not an operation of launch_hpc (its only tool is exec_command, task.py EXEC_COMMAND) |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py credit (project_practical_credit over the receipts, unbounded); credit_view fields are computed in messages/internal_summary.py |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (project_practical_credit over the receipts, unbounded); credit_view fields are computed in messages/internal_summary.py |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (project_practical_credit over the receipts, unbounded); credit_view fields are computed in messages/internal_summary.py |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (project_practical_credit over the receipts, unbounded); credit_view fields are computed in messages/internal_summary.py |
| decision_contracts.py | class | NativeDecisionContracts | machinery | decision-exchange loop (request_context / select_action envelope) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_schema | machinery | decision-exchange loop (request_context / select_action envelope) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_response | machinery | decision-exchange loop (request_context / select_action envelope) |
| decision_delivery.py | class | NativeDecisionDelivery | machinery | decision-exchange loop: saved-call replay, provider dispatch, runtime_model_calls |
| decision_delivery.py | method | NativeDecisionDelivery.call | machinery | decision-exchange loop: saved-call replay, provider dispatch, runtime_model_calls |
| decision_delivery.py | method | NativeDecisionDelivery.instructions | episode function | task.py decide (INSTRUCTIONS plus the resource instructions) |
| decision_exchange.py | class | NativeDecisionExchange | machinery | decision-exchange loop (pending lookup exchange, interpretation context): a lookup is a tool; none is needed here |
| decision_exchange.py | method | NativeDecisionExchange.interpretation_context | machinery | decision-exchange loop (pending lookup exchange, interpretation context): a lookup is a tool; none is needed here |
| decision_exchange.py | method | NativeDecisionExchange.exchange_decision | machinery | decision-exchange loop (pending lookup exchange, interpretation context): a lookup is a tool; none is needed here |
| decision_inputs.py | class | NativeDecisionInputs | episode function | task.py decide (launch resource instructions and requested_action_history in ModelRequest.context); UNPLACED parts: execution_expectations, resource_tool_estimates, native_execution_expectations, native_event_targets, waiting_support, pending_work, completed_action_reports (old shared-root services, no module; wait/pending machinery) |
| decision_inputs.py | method | NativeDecisionInputs.decision_inputs | episode function | task.py decide (launch resource instructions and requested_action_history in ModelRequest.context); UNPLACED parts: execution_expectations, resource_tool_estimates, native_execution_expectations, native_event_targets, waiting_support, pending_work, completed_action_reports (old shared-root services, no module; wait/pending machinery) |
| decision_presentation.py | function | present_native_task | episode function | task.py decide (the context is one mapping); UNPLACED: the renderer texts (render_hpc_prompt, is_hpc_context) lived in the old shared root library.hpc_prompt, which is not read or restored |
| decision_provider.py | class | NativeDecisionProvider | machinery | provider dispatch and conversation_key (the system calls the model) |
| decision_provider.py | method | NativeDecisionProvider.conversation_key | machinery | provider dispatch and conversation_key (the system calls the model) |
| decision_provider.py | method | NativeDecisionProvider.complete_decision | machinery | provider dispatch and conversation_key (the system calls the model) |
| decision_state.py | class | NativeDecisionState | episode function | messages/internal_summary.py internal_summary and task.py decide context; the runtime_actions / report_deliveries / pending_work reads are machinery and not carried |
| decision_state.py | method | NativeDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary and task.py decide context; the runtime_actions / report_deliveries / pending_work reads are machinery and not carried |
| episode.py | class | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| from_parent.py | class | NativeAssignment | machinery | parent-side commission schema and checks (child_assignment_schema enum of frozen requests, _permitted, _launch, _constraints): they check a commission; a wrong commission fails |
| from_parent.py | method | NativeAssignment.child_assignment_schema | machinery | parent-side commission schema and checks (child_assignment_schema enum of frozen requests, _permitted, _launch, _constraints): they check a commission; a wrong commission fails |
| from_parent.py | method | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment._permitted | machinery | parent-side commission schema and checks (child_assignment_schema enum of frozen requests, _permitted, _launch, _constraints): they check a commission; a wrong commission fails |
| from_parent.py | method | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment); the parent-role, masking/utility input, input-version and native BLAST checks are checks of a commission and are not carried |
| from_parent.py | method | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of ASSIGNMENT_SCHEMA) |
| from_parent.py | method | NativeAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py action (TerminalExecution.validate_action: workspace and scheduler constraints against settings['resource']) |
| from_parent.py | method | NativeAssignment._launch | machinery | parent-side commission schema and checks (child_assignment_schema enum of frozen requests, _permitted, _launch, _constraints): they check a commission; a wrong commission fails |
| from_parent.py | method | NativeAssignment._constraints | machinery | parent-side commission schema and checks (child_assignment_schema enum of frozen requests, _permitted, _launch, _constraints): they check a commission; a wrong commission fails |
| from_parent.py | method | NativeAssignment.required_return_sources | machinery | always returned (); the child declares its return fields in RETURN_FORM |
| from_parent.py | method | NativeAssignment.initial_references | machinery | record passing for the launch parents; empty for launch_hpc; custody is the system's |
| goal.py | class | NativeGoal | episode function | task.py INSTRUCTIONS and decide (the old goal instructions text) |
| goal.py | method | NativeGoal.instructions | episode function | task.py INSTRUCTIONS and decide (the old goal instructions text) |
| instructions.py | function | instructions | episode function | task.py decide (INSTRUCTIONS + resource instructions); the reasoning-commit, wait, redelivery and decision-exchange texts describe actions that do not exist and are not carried |
| internal_summary.py | class | NativeSummary | episode function | UNPLACED: launch parent's capabilities and resource_tool_contracts listings (not operations of launch_hpc) |
| internal_summary.py | method | NativeSummary.initial_decision_context | episode function | task.py decide (execution_resource in the context, _resource_information) |
| internal_summary.py | method | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | method | NativeSummary._with_selected_execution_task | machinery | no-op (returned its argument) |
| internal_summary.py | method | NativeSummary._resource_information | episode function | task.py _resource_information |
| internal_summary.py | method | NativeSummary.capabilities | episode function | UNPLACED: launch parent's capabilities and resource_tool_contracts listings (not operations of launch_hpc) |
| internal_summary.py | method | NativeSummary.resource_tool_contracts | episode function | UNPLACED: launch parent's capabilities and resource_tool_contracts listings (not operations of launch_hpc) |
| operations.py | class | NativeOperations | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations._delegate | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations._practical_context | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations.initialize | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations._check_parent_inputs | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations.state | machinery | delegate lookup, practical state initialisation, re-validation of the parent launch request from runtime_episodes |
| operations.py | method | NativeOperations.catalog | episode function | task.py TOOLS and EXEC_COMMAND |
| operations.py | method | NativeOperations.execute | episode function | task.py exec_command (tool), via ctx.services['job_access'] |
| received_information.py | class | ReceivedExecutionInformation | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_information.py | method | ReceivedExecutionInformation._forwards_bvbrc_reports | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_information.py | method | ReceivedExecutionInformation._forwards_minhash_reports | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_information.py | method | ReceivedExecutionInformation.received_report_sources | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_information.py | method | ReceivedExecutionInformation.received_report_facts | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_information.py | method | ReceivedExecutionInformation.received_report_closure_facts | machinery | receipt-scoped forwarding of child reports (this episode has no children) |
| received_record_selection.py | class | ReceivedRecordSelection | machinery | receipt-scoped record selection (custody is the system's) |
| received_record_selection.py | method | ReceivedRecordSelection._received | machinery | receipt-scoped record selection (custody is the system's) |
| received_reference_custody.py | class | ReceivedReferenceCustody | machinery | received-reference custody and validation of children's returns (no children; custody is the system's) |
| received_reference_custody.py | method | ReceivedReferenceCustody.resolve_received_reference | machinery | received-reference custody and validation of children's returns (no children; custody is the system's) |
| received_reference_custody.py | method | ReceivedReferenceCustody.validate_received_report | machinery | received-reference custody and validation of children's returns (no children; custody is the system's) |
| received_reference_custody.py | method | ReceivedReferenceCustody.received_form_references | machinery | received-reference custody and validation of children's returns (no children; custody is the system's) |
| report_delivery.py | class | NativeReportDelivery | machinery | report delivery (finish): report-form machinery; the episode content is final_to_parent |
| report_delivery.py | method | NativeReportDelivery.finish | machinery | report delivery (finish): report-form machinery; the episode content is final_to_parent |
| report_reference_access.py | class | ReportReferenceAccess | machinery | outgoing-report reference resolution (custody: the system admits and checks the return) |
| report_reference_access.py | method | ReportReferenceAccess.resolve | machinery | outgoing-report reference resolution (custody: the system admits and checks the return) |
| result_records.py | class | ExecutionResultRecords | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._masking_selector | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._masking_inputs | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._retained_masking_target | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._masking_reference_access | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._utility_selector | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._utility_inputs | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._retained_utility_target | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._utility_reference_access | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._versions | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._target | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._selector | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._result_directory | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._windows | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._selected_result_action | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._validate_result_body | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._read_result | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._selection | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._context_target | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._has_appservice | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._has_uniprot | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| result_records.py | method | ExecutionResultRecords._appservice_sources | episode function | UNPLACED: results-role (execution_result_acquisition) functions of the launch parent's mixin: selectors, byte windows, result reads; not operations of launch_hpc |
| saved_decision_exchange.py | class | NativeSavedDecisionExchange | machinery | saved-request checks of the decision-exchange loop |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request checks of the decision-exchange loop |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request checks of the decision-exchange loop |
| task.py | class | NativeTask | machinery | task class |
| task.py | method | NativeTask.next | episode function | task.py decide |
| task.py | method | NativeTask.apply_response | episode function | task.py action (validation of the model answer, Rejected) |
| task.py | method | NativeTask.execute | episode function | task.py exec_command (tool) |
| task_state.py | class | NativeTaskState | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.__init__ | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.restore | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.record_effect | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| task_state.py | method | NativeTaskState.checkpoint | machinery | decision state checkpoint/restore, record_effect, execution-failure record (the tool returns its failure as its outcome) |
| terminal_assignment.py | class | TerminalAssignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py action (validate_action against the configured resource) |
| terminal_assignment.py | method | TerminalAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py action (validate_action against the configured resource) |
| terminal_assignment.py | method | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py action (validate_action against the configured resource) |
| terminal_assignment.py | method | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_contracts.py | function | operation_catalog | episode function | task.py EXEC_COMMAND (the exec_command contract) |
| terminal_credit.py | class | TerminalCredit | episode function | credit.py credit |
| terminal_credit.py | method | TerminalCredit.credit_view | episode function | credit.py credit and messages/internal_summary.py (project_practical_credit over the receipts) |
| terminal_credit.py | method | TerminalCredit.completion_for_action | machinery | completion proof as estimator input (not carried; the proof is internal_summary.completion_proof) |
| terminal_execution.py | class | TerminalExecutionBehavior | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | class composition, constructor operands (settings), as_record(), credit_kind, permitted_common_actions, PracticalYieldEstimator (replaced by CompletionYieldController) |
| terminal_goal.py | class | TerminalGoal | episode function | task.py INSTRUCTIONS and decide (LaunchInstructions(...).for_resource for the resource instructions) |
| terminal_goal.py | method | TerminalGoal.instructions | episode function | task.py INSTRUCTIONS and decide (LaunchInstructions(...).for_resource for the resource instructions) |
| terminal_goal.py | method | TerminalGoal._resource_instructions | episode function | task.py INSTRUCTIONS and decide (LaunchInstructions(...).for_resource for the resource instructions) |
| terminal_operations.py | class | TerminalOperations | episode function | task.py exec_command (tool): validate (action), run (job_access), finalize_scientific_command, cwd/env context revision, assess_validations, receipt artifact; the begin/finish intent replay and the PracticalReceiptInformation publication are machinery / library not carried |
| terminal_operations.py | method | TerminalOperations._operations | episode function | library episode_support/jobs/local_execution/gene_context_evidence/terminal_execution.py TerminalExecution (validate_action called in task.py action; execute is the job_access service's: BLOCKED-ON-JOB-SERVICE) |
| terminal_operations.py | method | TerminalOperations.catalog | episode function | task.py TOOLS and EXEC_COMMAND |
| terminal_operations.py | method | TerminalOperations.execute | episode function | task.py exec_command (tool): validate (action), run (job_access), finalize_scientific_command, cwd/env context revision, assess_validations, receipt artifact; the begin/finish intent replay and the PracticalReceiptInformation publication are machinery / library not carried |
| terminal_report.py | class | TerminalReport | episode function | messages/final_to_parent.py (RETURN_FORM, _facts, validate_report) |
| terminal_report.py | method | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | method | TerminalReport.facts | episode function | messages/final_to_parent.py _facts |
| terminal_report.py | method | TerminalReport.resolve | machinery | reference resolution against the old receipt ledger (custody is the system's) |
| terminal_report.py | method | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_state.py | class | TerminalState | machinery | file-based PracticalState directory and lazy initialisation (replaced by the attempts journal, ctx.operation_key and the summary rebuilt from the units' receipts) |
| terminal_state.py | method | TerminalState._state_directory | machinery | file-based PracticalState directory and lazy initialisation (replaced by the attempts journal, ctx.operation_key and the summary rebuilt from the units' receipts) |
| terminal_state.py | method | TerminalState.initialize | machinery | file-based PracticalState directory and lazy initialisation (replaced by the attempts journal, ctx.operation_key and the summary rebuilt from the units' receipts) |
| terminal_state.py | method | TerminalState.state | machinery | file-based PracticalState directory and lazy initialisation (replaced by the attempts journal, ctx.operation_key and the summary rebuilt from the units' receipts) |
| terminal_summary.py | class | TerminalSummary | episode function | task.py decide and messages/internal_summary.py internal_summary |
| terminal_summary.py | method | TerminalSummary.initial_decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| terminal_summary.py | method | TerminalSummary._resource_information | episode function | task.py _resource_information |
| terminal_summary.py | method | TerminalSummary.decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| to_parent.py | class | NativeReport | machinery | class |
| to_parent.py | method | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (one selectable field per old fact source; the dotted names cannot be declared, see contract misfits) |
| to_parent.py | method | NativeReport.facts | episode function | messages/final_to_parent.py _facts |
| to_parent.py | method | NativeReport._live_facts | episode function | messages/final_to_parent.py _facts (execution_handoff_refs: BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | method | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report (the native-family and uniprot receivers do not apply to launch_hpc) |
| waiting.py | class | NativeWaiting | machinery | wait/suspension machinery |
| waiting.py | method | NativeWaiting.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | class | ExecutionEpisodeYield | machinery | class; practical_estimator (PracticalYieldEstimator) is replaced by the completion controller |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py _request_yield_class |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | class; practical_estimator (PracticalYieldEstimator) is replaced by the completion controller |
