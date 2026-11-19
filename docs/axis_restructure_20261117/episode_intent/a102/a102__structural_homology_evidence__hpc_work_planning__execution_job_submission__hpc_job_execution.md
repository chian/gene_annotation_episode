# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution`

Source: this episode's own files at commit `97308b94c` (43 Python files directly in the folder, 2,227 lines;
its `tests/` folder was not read as intent; no `grading/` or `scoring/` folders). Old role name: `launch_hpc`. Old
class `ExecutionEpisode`, task class `NativeTask`. Old `binding_path`
`structural_homology_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution`; old
`commissioning_parent` `structural_homology_evidence/hpc_work_planning/execution_job_submission`; `entry_roles = ()`
(it cannot be an entry); `replaces_default_instructions = True`.

## What this episode is for

It is the execution agent for one assigned job on one bound HPC (`pbs_ssh`) resource. It writes and runs shell
commands with `exec_command` until the requested endpoint predicates have a saved validated completion. The goal is
the terminal behaviour's instruction text (`goal.py` delegates to `terminal_goal.py`), verbatim:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the
> shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the
> actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed.
> Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context,
> not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit
> enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual
> native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain,
> investigate that original submission rather than create a duplicate. Use the provided resource-specific
> instructions, account, storage and existing authentication route. workdir and env apply to the selected command
> only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for
> supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual
> allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured
> transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied
> configuration gives the existing connection details. target=resource uses that transport directly. The episode
> iterator decides continuation from credit; add no stopping budget.

After that text comes "Resource instructions supplied from the frozen library:" with the sections the launch
instruction library selects for this resource (`library.for_resource(resource configuration)`).

## Task and instructions

One unit is one `exec_command` action. Permitted common actions: `tool` only (`action_policy.py`). `task.py` follows
the parent's loop, but builds its context with `assemble_decision_context` and has no reason branch. It validates
report updates with grain `launch_hpc`. `instructions.py` composes the goal plus the same optional paragraphs as the
parent. With only `tool` permitted, the reasoning and wait paragraphs never apply. The library, knowledge and repair
paragraphs apply when present.

## What it reads from its parent's assignment

The assignment is one practical request (`practical_assignment_v1` / `ASSIGNMENT_SCHEMA`) with `resource_id` and
`resource_kind` `hpc` (`from_parent.py`).

- `child_assignment_schema`: when the parent is `launch` and an `hpc` ancestor exists, the schema is an `enum` of
  exactly the parent's permitted frozen hpc requests, raising `frozen_hpc_launch_request_missing` if there are none.
  The child can only take a request the parent already froze. Otherwise it is the `anyOf` of the concrete hpc
  request schemas.
- `prepare_assignment` checks the following:
  - schema;
  - `_validate_request` (resource bound, kind, workspace confined, operations validator);
  - role kind = resource kind;
  - the parent role must be `launch`;
  - the parent's launch assignment is re-validated with `parent_launch_schema`;
  - protein-structure job inputs;
  - the original `immutable_input_versions`.
- `_check_parent_inputs` (`operations.py`) re-reads the commissioning launch episode's recorded `episode_assignment`
  at initialise and before every execution.
- `terminal_assignment.py` additionally requires `resource_kind` to match the role and a bound resource, and the
  resource operations to validate it.
- `required_return_sources` is empty.

## Children it may commission

None (`child_eligibility.py`). It is a leaf.

## Decision state and what the model sees

`decision_context.py` uses the same field set as the parent's decision state: goal, scope, working state, visible
refs, credit, controller, tools, report form and the rest. `internal_summary.decision_context` gives the terminal
summary:

- `execution_assignment`;
- `execution_resource` (kind, workspace, policy, account, `ssh_argv`, python executable, scheduler, inventory
  snapshot);
- `coordinator_workspace`;
- `execution_progress` (the practical state credit view);
- `execution_completion`.

It also adds a `selected_execution_task` when the request is local with a `native_protein_structure` job and a
scientific parent task exists. For an hpc request this never applies. `decision_delivery.py` merges task_decision and
decision_inputs and captures `execution_expectations` for `launch_hpc`. The prompt renderer is `present_native_task`
(`decision_presentation.py`):

- a TASK section;
- STEERING: action yields, controller, current credit, completed action reports, last outcome, feedback, child
  reports, pending work, report deliveries, waiting support, resource estimates, pending delivery;
- "Current execution information": `execution_completed`; practical progress credit, initial and operational
  credit, requirements and satisfied keys; practical completion.

`complete_with_presentation` is used only for selected-execution contexts that are not HPC, published-scientific or
API launch. Otherwise plain `complete` is called.

## Tools it offers

One tool, `exec_command` (`terminal_contracts.py`), with these arguments:

- `cmd`: a string or argv list;
- `workdir`;
- `target`: `resource` (default) or `coordinator`;
- `env`.

`required` is cmd, workdir and env. `terminal_operations.py` does the following on each call:

1. validates the arguments and the action against the assignment;
2. opens an idempotent intent in `PracticalState` keyed by operation key (a completed intent reuses its receipt);
3. runs the command through `TerminalExecution` with `terminal_artifact_paths`;
4. finalises the scientific command artifacts;
5. updates the cwd/env context revision for resource commands inside the workspace;
6. assesses the validations, finishes the receipt and publishes a practical receipt record.

An invalid action returns status `invalid`. An execution error becomes a `failure` native outcome, which is still a
completed, observed action.

## How its credit is counted

Credit kind `operational`. The live credit is the practical state's `credit_view()` for the assigned resource
(`terminal_credit.py`; the protein-structure results view when that applies). The closed view takes precedence
(`closed_credit.py`). The practical credit itself (requirements, satisfied keys, operational credit) is computed by
the practical execution state and records, outside this folder. Completion is the practical state's
`completion_proof()` for the matching operation key. Verification goes through the recorded closed verdict or
`state.verify_completion`. Credit is never bounded.

## Continuation

`yield_estimator.py` requires `require_private_yield=True`. It uses a plain `YieldController` with cutoff and
parameters from the task yield profile `launch_hpc:<request class>`. The class is
`practical_hpc[_native_*]_<handoff|outputs>`, set by the request's `endpoint` (`usable_handoff` /
`completed_job_outputs`). The estimate comes from `PracticalYieldEstimator` over completion verification, which gives
exact zero next gain once completion is verified. In the new layout this is "completion with a target", with the
profile's settings.

## What it reports to its parent

`to_parent.py` fact sources: the parent's set (`execution_handoff_refs`, `execution_result_refs`,
`execution_completed`, `execution_result_origin`) plus the terminal sources:

- `practical_completed`;
- `practical_receipt_digests`;
- `practical_receipt_refs`, with namespace `practical_receipt`.

Live facts are the terminal facts, plus every practical receipt ref that reads as a returnable handoff matching this
assignment, added to `execution_handoff_refs`. `execution_completed` is `practical_completed`. `validate_report`
requires `x-source` fields to equal the facts. The parent receives the form through
`from_child_hpc_job_execution.receive_report`.

## Differences from similar episodes

- `local_job_execution` is byte-identical except for:
  - role, binding path and docstrings;
  - the `execution_expectations` key and the report grain;
  - the yield profile prefix;
  - `from_parent.child_assignment_schema`: this hpc episode alone restricts its assignment to the parent's frozen
    hpc requests when an `hpc` ancestor exists.
- Sibling `hpc_allocation_execution/execution_job_submission/hpc_job_execution`: identical except for its binding
  path, its commissioning parent and its `contracts.py` import of its own `terminal_execution`.
- Compared with `api_job_execution`: it allows `tool` only (no `wait`), uses `exec_command` instead of API service
  operations, uses the `present_native_task` renderer, and keeps the `terminal_*` split files.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `action_policy.py` | 7 | Permitted common actions: `tool` only (no reason, child, wait or redeliver_report). | none |
| `binding_record.py` | 9 | Binding identity record `.../execution_job_submission/hpc_job_execution` with resources, inventory, units, log window/roles, private yield and yield profiles. | none |
| `child_eligibility.py` | 10 | No child roles, no allowed children (leaf). | none |
| `closed_credit.py` | 117 | Closed-credit snapshot, same as the parent: credit frozen in report facts at close and returned unchanged later. | BindingContext.as_record ×2, BindingContext.episode_id ×8, BindingContext.role, import:a102.episode_receipts, import:a102.episode_return_records ×3, old:EpisodeReceipts ×2, old:EpisodeReturnRecords ×2, store:self.store.db ×6, table:runtime_episodes ×2, table:runtime_forms ×3, table:runtime_observations, table:runtime_receipt_inheritance ×2, table:runtime_record_receipts ×2 |
| `completion.py` | 49 | Completion: protein-structure results proof, else the terminal behavior's practical state proof (`completion_for_action`); verification via the recorded closed verdict or `state.verify_completion`. | BindingContext.assignment, BindingContext.episode_id ×4, import:a102.episode_return_records, import:a102.method_loop.identities, import:a102.numerical, import:a102.practical_yield, old:UnitRef ×2, store:self.store.db, support:self.native_protein_structure_results ×4, table:runtime_observations, yield:ESTIMATOR_VERSION ×2, yield:NumericBand ×2 |
| `configuration.py` | 62 | Same construction-time configuration and checks as the parent (resources, inventory, foreign native bindings, positive units, log selection, yield profiles), building the per-resource terminal behaviors, API execution, progress provider, file sources, protein-structure results/returns. | import:a102.api_service_execution, import:a102.execution_progress, import:a102.native_protein_structure_results, import:a102.native_protein_structure_returns, import:a102.numerical, self.services, support:self.api_execution ×2, support:self.job_progress_provider, support:self.local_file_sources, support:self.native_protein_structure_results, support:self.native_protein_structure_returns, support:self._practical ×2, support:self.tool_registry, yield:YieldController ×3, yield:YieldParameters ×3 |
| `contracts.py` | 53 | Constants (same versions, ROLES, KINDS, ROLE_KINDS, NATIVE_RESULT_ORIGIN, schemas, catalogs) importing this episode's own TerminalExecutionBehavior and exec_command catalog. | import:a102.a102_execution_bindings, import:a102.communication, import:a102.domain, import:a102.execution_contracts, import:a102.launch_instructions, import:a102.local_file_capture_results, import:a102.native_protein_structure_acquisition, import:a102.practical_execution_operations, import:a102.practical_execution_records, import:a102.practical_execution_state, import:a102.practical_receipt_information, import:a102.resource_records, import:a102.structural_homology_evidence.hpc_work_planning.execution_job_submission.hpc_job_execution.terminal_execution |
| `credit.py` | 27 | Credit kind `operational`; live credit = protein-structure results credit view or the terminal practical state's `credit_view()` (closed view first). | support:self.native_protein_structure_results ×2 |
| `decision_context.py` | 45 | Decision state shown to the model (same field set as the parent's decision_state: goal, scope, working state, visible refs, current credit, credit binding, time accounting, pending work, last outcome, feedback, visual evidence, report deliveries, controller, tools, tool knowledge, job options, report facts, requested form, current report) plus the binding's decision_context. | import:a102.runtime ×2, runtime.FACT_MEANINGS, runtime.FACT_SOURCES, runtime.json ×2, runtime.Mapping ×3, runtime._plain ×2, runtime._references_in, self.workflow.binding_context, self.workflow.catalog, self.workflow.controller_binding, self.workflow.delivery_status, self.workflow.extra_report_sources, self.workflow.is_scientific_source, self.workflow.job_episode_options, self.workflow.journal ×3, self.workflow.knowledge, self.workflow.local_outcome_preview, self.workflow.pending_work, self.workflow.receipt_projection, self.workflow.run_id, self.workflow.source_credit_binding, self.workflow.source_credit_view, self.workflow.specialist, self.workflow.store ×3, self.workflow.tools, self.workflow.working_state, table:runtime_actions ×2 |
| `decision_contracts.py` | 128 | Decision-exchange contract information validation (copy of the shared protocol). | import:a102.decision_context, import:a102.execution_prompt, import:a102.library.hpc_prompt, import:a102.runtime ×2, import:a102.structural_homology_evidence_prompt, runtime.apply_state_frame, runtime.composition_lookup_schema ×2, runtime.CONTRACT_INFORMATION_OPERATIONS, runtime.DECISION_CONTEXT_VERSION, runtime.Draft202012Validator, runtime.instructional_model_context, runtime.is_contract_information, runtime._json ×8, runtime.json, runtime.Mapping ×2, runtime.model_snapshot, runtime._object ×3, runtime._recorded_action_generation_schema, runtime._references_in, runtime.requested_contract_information, runtime.ValidationError, runtime.WorkflowError ×9, self.workflow.contract_information_reply, self.workflow.decision_exchanges ×2, self.workflow.journal, self.workflow.store ×2, self.workflow.validate_contract_information ×2, table:runtime_model_calls |
| `decision_delivery.py` | 137 | One decision call (merged task_decision + decision_inputs): replay saved call, decision inputs incl. execution_expectations for role `launch_hpc`, contract information, decision exchange, history preview, model call save. | binding_attr:instruction_composer, import:a102.decision_context, import:a102.episode_work_report ×2, import:a102.execution_prompt, import:a102.library.hpc_prompt ×2, import:a102.runtime ×2, import:a102.structural_homology_evidence_prompt, old:completed_action_reports ×3, old:requested_action_history ×3, runtime._action_generation_schema, runtime._ASSIGNMENT_TRANSPORT, runtime.child_option_information, runtime.DECISION_EXCHANGE_PROTOCOL ×5, runtime._digest, runtime.instructional_model_context, runtime._json ×4, runtime.json ×2, runtime.Mapping, runtime._recorded_assignment_transport, runtime.WorkflowError ×5, self.workflow.available_child_roles, self.workflow.binding_context, self.workflow.contract_information_profile, self.workflow.decision_exchanges, self.workflow.decision_protocol ×3, self.workflow.episode_bindings, self.workflow.execution_expectations, self.workflow.freeze_contract_information, self.workflow.freeze_literature_numerical_contracts, self.workflow.history_preview, self.workflow.is_job_source ×3, self.workflow.job_episodes ×2, self.workflow.journal, self.workflow.launch_instructions ×2, self.workflow.native_estimation_context, self.workflow.numerical_contracts, self.workflow.pending_work, self.workflow.permits_common_action, self.workflow.provider ×2, self.workflow.receipts ×4, self.workflow.resource_context, self.workflow.resource_estimator ×5, self.workflow.services, self.workflow.shared_information_context, self.workflow.uses_received_record_context ×2, self.workflow.validate_contract_information ×2, self.workflow.waiting_support, table:runtime_model_calls ×5 |
| `decision_exchange.py` | 108 | Multi-step decision exchange (copy of the shared protocol). | import:a102.decision_context, import:a102.execution_prompt, import:a102.library.hpc_prompt, import:a102.runtime ×2, import:a102.structural_homology_evidence_prompt, runtime._action_generation_schema, runtime._category_yield_parameters, runtime.child_option_information, runtime.DECISION_CONTEXT_VERSION, runtime.instructional_model_context ×2, runtime._json ×2, runtime.lookup_attempts, runtime.Mapping, runtime.model_snapshot, runtime._plain ×2, runtime.requested_contract_information, runtime.schema_failure_diagnostic ×2, runtime.sqlite3, runtime.state_frame, runtime.ValidationError ×4, runtime.yield_table, self.workflow.controller_binding, self.workflow.decision_exchanges, self.workflow.execute, self.workflow.journal, self.workflow.run_id, self.workflow.services, self.workflow.validate_contract_information, table:runtime_model_calls ×2 |
| `decision_presentation.py` | 20 | Prompt renderer `present_native_task`: requires a selected execution task; TASK section + STEERING (action yields, controller, current credit, completed reports, last outcome, feedback, pending work, waiting support, resource estimates, pending delivery) + "Current execution information" (execution_completed, practical progress credit/requirements/satisfied keys, practical completion). | import:a102.structural_homology_evidence_prompt, old:completed_action_reports |
| `decision_provider.py` | 20 | Model call: `complete_with_presentation` with `present_native_task` for selected-execution contexts that are not HPC / published-scientific / API launch; else ordinary complete. | import:a102.decision_context, import:a102.execution_prompt, import:a102.library.hpc_prompt, import:a102.runtime, import:a102.structural_homology_evidence_prompt, self.workflow.provider, self.workflow.specialist |
| `episode.py` | 34 | Composition of the native binding; `decision_source_type = NativeTask`, renderer `present_native_task`, commissioning parent `.../execution_job_submission`, roles `('launch_hpc',)`, `entry_roles = ()`, `replaces_default_instructions = True`. | binding_attr:binding_path, binding_attr:commissioning_parent, binding_attr:decision_prompt_renderer, binding_attr:decision_source_type, binding_attr:entry_roles, binding_attr:replaces_default_instructions, binding_attr:roles |
| `from_parent.py` | 117 | Assignment form: when the parent is `launch` with an `hpc` ancestor, an enum of exactly the parent's permitted frozen hpc requests (`frozen_hpc_launch_request_missing` otherwise); else `anyOf` concrete hpc request schemas. prepare_assignment: validate request, role kind, parent role must be `launch`, re-validate parent launch assignment, protein-structure inputs, immutable input versions. Also holds `_permitted`, `_request_schema`, `_validate_request`, `_launch` (via parent_launch_schema), `_constraints`, initial_references. | BindingContext.assignment ×4, BindingContext.path ×2, BindingContext.role ×6, import:a102.native_protein_structure_tool_info, import:a102.protein_structure_operands ×3, self.services, self.services.annotation_task_required, support:self.api_execution ×3, support:self.native_protein_structure_results, support:self.native_protein_structure_returns ×3, support:self._practical |
| `goal.py` | 7 | Goal is the terminal behavior's instructions for this resource (see terminal_goal.py). | none |
| `__init__.py` | 0 | Empty package marker. | none |
| `instructions.py` | 22 | Instruction composition (same additions as the parent: reasoning commit, tool knowledge, launch library, pending delivery, wait texts, native event texts, exchange guidance). | import:a102.runtime_prompt ×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL, runtime_prompt.INSTRUCTIONS ×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT, self.workflow.binding_context, self.workflow.decision_protocol, self.workflow.knowledge, self.workflow.launch_instructions, self.workflow.native_event_information, self.workflow.permits_common_action ×3, self.workflow.specialist |
| `internal_summary.py` | 101 | initial_decision_context (resource capabilities + inventory); decision_context = terminal summary + `selected_execution_task` for a local native protein-structure request; resource information, capabilities, resource_tool_contracts. | BindingContext.assignment, import:a102.native_protein_structure_tool_info, self.services, self.services.scientific_parent_task, support:self.api_execution ×4, support:self.local_file_sources, support:self.tool_registry ×2 |
| `operations.py` | 40 | Operations delegated to the terminal behavior for the assigned resource after `_check_parent_inputs` (reads the commissioning launch episode's original assignment); catalog, execute, state (local/hpc roles only), initialize. | BindingContext.assignment ×2, BindingContext.path ×3, BindingContext.role ×2, BindingContext.scope, import:a102.protein_structure_operands, store:self.store.db, support:self.api_execution, support:self.native_protein_structure_returns, support:self._practical, table:runtime_episodes |
| `parent_launch_contract.py` | 8 | `parent_launch_schema`: the commissioning Launch's assignment schema. | none |
| `received_information.py` | 37 | Received report sources/facts for annotation / structural_homology_evidence roles (file sources, capture outcomes, protein-structure facts). | BindingContext.request, BindingContext.role, import:a102.protein_structure_result_views, support:self.local_file_sources ×2, support:self.native_protein_structure_returns |
| `received_record_selection.py` | 35 | Received handoff/result selection from known refs (copy of the parent's). | BindingContext.assignment, BindingContext.role, BindingContext.scope ×2, support:self.api_execution ×2, support:self.job_progress_provider |
| `received_reference_custody.py` | 35 | Received reference resolution and admission (copy of the parent's). | BindingContext.role, support:self.local_file_sources ×3, support:self.native_protein_structure_returns ×3 |
| `report_delivery.py` | 25 | Final report form from interpretations + facts (copy of the parent's). | import:a102.library.private_policy_call, import:a102.library.report_fact_assembly, import:a102.runtime ×2, old:_invoke_private_policy ×2, old:_private_report_facts ×2, runtime.form_with_facts, runtime._json ×2, runtime.json, runtime.Record ×2, self.workflow.binding_context, self.workflow.episode_bindings, self.workflow.facts, self.workflow.journal ×2, self.workflow.pending_handles, self.workflow.release ×2, self.workflow.source_credit_view, table:runtime_forms ×2 |
| `report_reference_access.py` | 45 | Reference resolution for report validation (copy of the parent's; practical receipts resolved by the terminal delegate for local/hpc roles). | BindingContext.role, BindingContext.scope ×4, import:a102.episode_bindings ×2, old:reference_in_context ×4, self.services ×4, support:self.api_execution ×2, support:self.job_progress_provider ×2, support:self.local_file_sources |
| `result_records.py` | 158 | Results-related records: input versions, results target and selector, result directory, windows, selected result action, result body validation and read, receiver selection, `_context_target` (target assignment must equal this episode's assignment). | BindingContext.assignment ×4, BindingContext.episode_id ×9, BindingContext.role ×3, BindingContext.run_id ×2, BindingContext.scope ×4, import:a102.episode_receipts, import:a102.execution_input_versions, import:a102.protein_structure_selection, old:EpisodeReceipts ×2, self.services ×2, self.services.record_selection, store:self.store.db ×5, support:self.api_execution, support:self.job_progress_provider ×2, support:self.local_file_sources ×2, table:runtime_actions ×2, table:runtime_episodes, table:runtime_receipt_inheritance ×2 |
| `retained_protein_reader.py` | 95 | Retained protein-structure read authority (copy of the parent's). | BindingContext.assignment, BindingContext.role, BindingContext.run_id, BindingContext.scope, import:a102.execution_contracts, import:a102.native_protein_structure_results, import:a102.native_protein_structure_returns, import:a102.protein_structure_contracts, import:a102.protein_structure_operands, import:a102.protein_structure_selection, import:a102.state, support:self.job_progress_provider, support:self.native_protein_structure_results ×2, support:self.native_protein_structure_returns ×2, table:runtime_episodes |
| `task.py` | 221 | Task loop like the parent's, using `assemble_decision_context`, no reason branch, report validated with grain `launch_hpc`, no HPC handoff report validator attached. | import:a102.episode_source_failure, import:a102.library.action_contracts, import:a102.library.private_policy_call, import:a102.providers, import:a102.read_mapping, import:a102.runtime ×2, old:_invoke_private_policy ×2, old:ModelCallError ×2, old:_private_action_schema ×2, old:record_source_failure ×2, runtime.AcquisitionError ×2, runtime.ActionFailure, runtime.ContractError, runtime.ContractInformationError, runtime._decode_recorded_action_response, runtime.Draft202012Validator ×2, runtime.EventTargetError ×2, runtime.inspect, runtime._json ×5, runtime.json ×8, runtime.Mapping ×2, runtime.nullcontext ×5, runtime.observes_action_outcome, runtime.ReportBoundaryError, runtime.ReportRedelivery ×2, runtime.schema_failure_diagnostic, runtime.SourceEnd ×2, runtime.sqlite3 ×2, runtime.subprocess ×2, runtime.validate_form, runtime.ValidationError ×3, runtime._wait_target_feedback ×2, runtime.WorkflowError ×2, self.workflow.action_schema, self.workflow.automatic_score_updates, self.workflow.binding_context, self.workflow.completed_unit ×3, self.workflow.completions ×3, self.workflow.controller_value ×2, self.workflow.decision_exchanges ×3, self.workflow.delivery_resolution_inputs, self.workflow.execute, self.workflow.execution_binding ×7, self.workflow.inprocess_replay ×4, self.workflow.journal ×7, self.workflow.last_observed_credit, self.workflow.next_return, self.workflow.pending_work, self.workflow.perform_selected_wait, self.workflow.permits_common_action, self.workflow.receive_native_outcome, self.workflow.receive_outcome, self.workflow.resolve_pending_deliveries, self.workflow.resolver, self.workflow.retain_shared_grading_results, self.workflow.run_id ×3, self.workflow.selected ×3, self.workflow.source_credit_view, self.workflow.specialist, self.workflow.store ×8, self.workflow.validate_report, table:runtime_actions ×8, table:runtime_episodes, table:runtime_model_calls ×2 |
| `task_state.py` | 108 | Task state/restore/checkpoint (copy of the parent's). | import:a102.episode_source_failure, import:a102.runtime ×2, old:record_source_failure ×2, runtime.ActionLeaf, runtime.EFFECT_VERSION, runtime.Episode, runtime.interpretation_schema, runtime._json ×2, runtime.json ×4, runtime._object, runtime._plain, runtime.Record, self.workflow.archive, self.workflow.completions ×4, self.workflow.context, self.workflow.controller_value, self.workflow.execution_binding ×4, self.workflow.grains, self.workflow.inprocess_replay ×7, self.workflow.journal ×5, self.workflow.progress_provider ×2, self.workflow.recover_commissions, self.workflow.run_id, self.workflow.source_credit_view, self.workflow.store ×2, table:runtime_actions ×5 |
| `terminal_assignment.py` | 22 | Assignment for the terminal role: practical `ASSIGNMENT_SCHEMA`, resource_kind must match the role and a bound resource, resource operations validate it. | BindingContext.assignment, BindingContext.role |
| `terminal_contracts.py` | 24 | Terminal constants: `terminal_execution_episode_v1`, ROLE_KINDS {launch_local, launch_hpc}, `exec_command` catalog (cmd string/argv, workdir, target resource/coordinator, env). | import:a102.acquisition, import:a102.communication, import:a102.domain, import:a102.practical_execution_operations, import:a102.practical_execution_records, import:a102.practical_execution_state, import:a102.terminal_execution |
| `terminal_credit.py` | 11 | Terminal credit view = PracticalState credit view; completion proof from the practical state for the matching operation key. | none |
| `terminal_execution.py` | 41 | TerminalExecutionBehavior composition (goal, operations, state, assignment, summary, report, credit); operational credit kind; `tool` only; no children; PracticalYieldEstimator over the state's completion verification. | import:a102.practical_yield, self.services, yield:PracticalYieldEstimator ×2 |
| `terminal_goal.py` | 18 | The execution-agent instruction text (see Goal) + resource instructions from the frozen launch-instruction library for this resource. | BindingContext.assignment, self.services, self.services.workflow, self.workflow.launch_instructions |
| `terminal_operations.py` | 47 | exec_command execution: validate arguments and action, begin/finish an intent in PracticalState (idempotent by operation key), run the command, finalize scientific command artifacts, update cwd/env context revision, assess validations, publish a practical receipt record. | BindingContext.assignment ×5, BindingContext.run_id, import:a102.practical_receipt_information, import:a102.terminal_scientific_evidence ×2 |
| `terminal_report.py` | 31 | Report fact sources `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`; facts published from state receipts; reference resolution for practical receipts; validate_report against recorded facts. | BindingContext.run_id ×2, import:a102.practical_receipt_information ×2 |
| `terminal_state.py` | 18 | PracticalState per (run, episode) under `practical-execution/<digest>` with initial outcome/validations on first creation. | BindingContext.episode_id ×4, BindingContext.run_id ×2 |
| `terminal_summary.py` | 16 | Terminal decision context: execution_assignment, execution_resource (kind, workspace, policy, account, ssh_argv, python, scheduler, inventory), coordinator_workspace, execution_progress (credit view), execution_completion. | BindingContext.assignment ×2 |
| `to_parent.py` | 62 | Report fact sources: parent's set + terminal facts for local/hpc roles; live facts = terminal facts + handoffs from practical receipt refs that are returnable and match; `execution_completed` = practical_completed; validate_report against recorded facts. | BindingContext.scope, import:a102.local_file_capture_results, import:a102.protein_structure_result_views ×2, support:self.job_progress_provider, support:self.local_file_sources ×2, support:self.native_protein_structure_results ×2, support:self.native_protein_structure_returns |
| `waiting.py` | 9 | Suspension condition forwarded to the execution backend (copy). | self.workflow.execution_backend, self.workflow.execution_handle ×2 |
| `yield_estimator.py` | 48 | Continuation: private yield binding required; YieldController with task yield profile `launch_hpc:<request class>` (e.g. `practical_hpc[_native_*]_handoff|outputs`) and PracticalYieldEstimator over completion verification. | BindingContext.assignment, BindingContext.role, import:a102.numerical, import:a102.practical_yield, yield:PracticalYieldEstimator ×2, yield:YieldController ×2, yield:YieldParameters ×2 |

## Old-runner names found (distinct, by kind)

Counts per file are in `runs/carry_over/calls/a102_03.tsv`. In the table, `support:self.<x>` is a construction-time collaborator built from old shared A102 modules, `table:` is an old journal or receipt table name, and `import:` is an old module path.

- **binding_attr**: `binding_attr:binding_path`, `binding_attr:commissioning_parent`, `binding_attr:decision_prompt_renderer`, `binding_attr:decision_source_type`, `binding_attr:entry_roles`, `binding_attr:instruction_composer`, `binding_attr:replaces_default_instructions`, `binding_attr:roles`
- **BindingContext**: `BindingContext.as_record`, `BindingContext.assignment`, `BindingContext.episode_id`, `BindingContext.path`, `BindingContext.request`, `BindingContext.role`, `BindingContext.run_id`, `BindingContext.scope`
- **import**: `import:a102.a102_execution_bindings`, `import:a102.acquisition`, `import:a102.api_service_execution`, `import:a102.communication`, `import:a102.decision_context`, `import:a102.domain`, `import:a102.episode_bindings`, `import:a102.episode_receipts`, `import:a102.episode_return_records`, `import:a102.episode_source_failure`, `import:a102.episode_work_report`, `import:a102.execution_contracts`, `import:a102.execution_input_versions`, `import:a102.execution_progress`, `import:a102.execution_prompt`, `import:a102.launch_instructions`, `import:a102.library.action_contracts`, `import:a102.library.hpc_prompt`, `import:a102.library.private_policy_call`, `import:a102.library.report_fact_assembly`, `import:a102.local_file_capture_results`, `import:a102.method_loop.identities`, `import:a102.native_protein_structure_acquisition`, `import:a102.native_protein_structure_results`, `import:a102.native_protein_structure_returns`, `import:a102.native_protein_structure_tool_info`, `import:a102.numerical`, `import:a102.practical_execution_operations`, `import:a102.practical_execution_records`, `import:a102.practical_execution_state`, `import:a102.practical_receipt_information`, `import:a102.practical_yield`, `import:a102.protein_structure_contracts`, `import:a102.protein_structure_operands`, `import:a102.protein_structure_result_views`, `import:a102.protein_structure_selection`, `import:a102.providers`, `import:a102.read_mapping`, `import:a102.resource_records`, `import:a102.runtime`, `import:a102.runtime_prompt`, `import:a102.state`, `import:a102.structural_homology_evidence.hpc_work_planning.execution_job_submission.hpc_job_execution.terminal_execution`, `import:a102.structural_homology_evidence_prompt`, `import:a102.terminal_execution`, `import:a102.terminal_scientific_evidence`
- **old**: `old:completed_action_reports`, `old:EpisodeReceipts`, `old:EpisodeReturnRecords`, `old:_invoke_private_policy`, `old:ModelCallError`, `old:_private_action_schema`, `old:_private_report_facts`, `old:record_source_failure`, `old:reference_in_context`, `old:requested_action_history`, `old:UnitRef`
- **runtime (old a102.runtime)**: `runtime.AcquisitionError`, `runtime.ActionFailure`, `runtime._action_generation_schema`, `runtime.ActionLeaf`, `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information`, `runtime.composition_lookup_schema`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION`, `runtime.DECISION_EXCHANGE_PROTOCOL`, `runtime._decode_recorded_action_response`, `runtime._digest`, `runtime.Draft202012Validator`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.EventTargetError`, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.form_with_facts`, `runtime.inspect`, `runtime.instructional_model_context`, `runtime.interpretation_schema`, `runtime.is_contract_information`, `runtime._json`, `runtime.json`, `runtime.lookup_attempts`, `runtime.Mapping`, `runtime.model_snapshot`, `runtime.nullcontext`, `runtime._object`, `runtime.observes_action_outcome`, `runtime._plain`, `runtime.Record`, `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery`, `runtime.requested_contract_information`, `runtime.schema_failure_diagnostic`, `runtime.SourceEnd`, `runtime.sqlite3`, `runtime.state_frame`, `runtime.subprocess`, `runtime.validate_form`, `runtime.ValidationError`, `runtime._wait_target_feedback`, `runtime.WorkflowError`, `runtime.yield_table`
- **runtime_prompt**: `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`, `runtime_prompt.INSTRUCTIONS`, `runtime_prompt.REASONING_COMMIT_REQUIREMENT`
- **self.services**: `self.services`
- **self.services.annotation_task_required**: `self.services.annotation_task_required`
- **self.services.record_selection**: `self.services.record_selection`
- **self.services.scientific_parent_task**: `self.services.scientific_parent_task`
- **self.services.workflow**: `self.services.workflow`
- **self.workflow**: `self.workflow.action_schema`, `self.workflow.archive`, `self.workflow.automatic_score_updates`, `self.workflow.available_child_roles`, `self.workflow.binding_context`, `self.workflow.catalog`, `self.workflow.completed_unit`, `self.workflow.completions`, `self.workflow.context`, `self.workflow.contract_information_profile`, `self.workflow.contract_information_reply`, `self.workflow.controller_binding`, `self.workflow.controller_value`, `self.workflow.decision_exchanges`, `self.workflow.decision_protocol`, `self.workflow.delivery_resolution_inputs`, `self.workflow.delivery_status`, `self.workflow.episode_bindings`, `self.workflow.execute`, `self.workflow.execution_backend`, `self.workflow.execution_binding`, `self.workflow.execution_expectations`, `self.workflow.execution_handle`, `self.workflow.extra_report_sources`, `self.workflow.facts`, `self.workflow.freeze_contract_information`, `self.workflow.freeze_literature_numerical_contracts`, `self.workflow.grains`, `self.workflow.history_preview`, `self.workflow.inprocess_replay`, `self.workflow.is_job_source`, `self.workflow.is_scientific_source`, `self.workflow.job_episode_options`, `self.workflow.job_episodes`, `self.workflow.journal`, `self.workflow.knowledge`, `self.workflow.last_observed_credit`, `self.workflow.launch_instructions`, `self.workflow.local_outcome_preview`, `self.workflow.native_estimation_context`, `self.workflow.native_event_information`, `self.workflow.next_return`, `self.workflow.numerical_contracts`, `self.workflow.pending_handles`, `self.workflow.pending_work`, `self.workflow.perform_selected_wait`, `self.workflow.permits_common_action`, `self.workflow.progress_provider`, `self.workflow.provider`, `self.workflow.receipt_projection`, `self.workflow.receipts`, `self.workflow.receive_native_outcome`, `self.workflow.receive_outcome`, `self.workflow.recover_commissions`, `self.workflow.release`, `self.workflow.resolve_pending_deliveries`, `self.workflow.resolver`, `self.workflow.resource_context`, `self.workflow.resource_estimator`, `self.workflow.retain_shared_grading_results`, `self.workflow.run_id`, `self.workflow.selected`, `self.workflow.services`, `self.workflow.shared_information_context`, `self.workflow.source_credit_binding`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store`, `self.workflow.tools`, `self.workflow.uses_received_record_context`, `self.workflow.validate_contract_information`, `self.workflow.validate_report`, `self.workflow.waiting_support`, `self.workflow.working_state`
- **store**: `store:self.store.db`
- **support**: `support:self.api_execution`, `support:self.job_progress_provider`, `support:self.local_file_sources`, `support:self.native_protein_structure_results`, `support:self.native_protein_structure_returns`, `support:self._practical`, `support:self.tool_registry`
- **table**: `table:runtime_actions`, `table:runtime_episodes`, `table:runtime_forms`, `table:runtime_model_calls`, `table:runtime_observations`, `table:runtime_receipt_inheritance`, `table:runtime_record_receipts`
- **yield**: `yield:ESTIMATOR_VERSION`, `yield:NumericBand`, `yield:PracticalYieldEstimator`, `yield:YieldController`, `yield:YieldParameters`

## Carried over

Every old function, class and method of this episode at 97308b94c (`runs/carry_over/functions/a102__structural_homology_evidence__hpc_work_planning__execution_job_submission__hpc_job_execution.tsv`), and where it is now. `episode function` rows name the new file and member (`library candidate` marks a function not in the library that stays in the file that uses it); `episode function (unplaced)` rows could not be placed and are reported with the reason; `machinery` rows give the reason.

| old file | name | kind | new place or reason |
|---|---|---|---|
| action_policy.py | NativeActionPolicy | episode function | task.py: the episode offers the tool action only (selection_schema, decide) |
| action_policy.py | NativeActionPolicy.permitted_common_actions | episode function | task.py selection_schema: only exec_command is offered; no reason, wait or child |
| binding_record.py | NativeBindingRecord | machinery | binding record / the binding's own as_record(): deleted (README 3e); the system records the binding |
| binding_record.py | NativeBindingRecord.as_record | machinery | binding record / the binding's own as_record(): deleted (README 3e); the system records the binding |
| child_eligibility.py | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| closed_credit.py | NativeClosedCredit | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| closed_credit.py | NativeClosedCredit._closed_credit_carrier | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| closed_credit.py | NativeClosedCredit._closed_credit_receipts | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| closed_credit.py | NativeClosedCredit._closed_credit_value | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| closed_credit.py | NativeClosedCredit._closed_credit_facts | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| closed_credit.py | NativeClosedCredit._closed_operational_credit_view | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, receipts): the system hands the credit its controller last saw to final_to_parent (README 3b D1, 3e) |
| completion.py | NativeCompletion | episode function | messages/internal_summary.py completion_proof (library candidate) |
| completion.py | NativeCompletion.completion_for_action | episode function | messages/internal_summary.py completion_proof: the proof names the last receipt's operation key |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | re-check of a completion against runtime_observations of the old journal (README 3d, 3e) |
| completion.py | NativeCompletion.verify_completion | machinery | completion verification by the practical state / recorded history (PracticalYieldEstimator input): the controller is the completion controller; the proof is recomputed from the summary's receipts |
| configuration.py | NativeConfiguration | episode function | settings of the episode (ctx.settings): resource, initial_information, coordinator_workspace, task_yield_profiles, launch_instructions_directory, knowledge_library_directory (task.py header; yield_estimator.py) |
| configuration.py | NativeConfiguration.__init__ | episode function | settings read in task.py (resource -> library TerminalExecution validates the configuration; initial_information; coordinator_workspace) and yield_estimator.py (task_yield_profiles). services, store, run_id, tool_registry, API executor, progress provider, local file sources, protein-structure custody, results_yield_profiles, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield: other roles / old-runner wiring, not carried (the old profile switch require_private_yield has no new meaning: the profile is always required) |
| contracts.py | launch_operation_catalog | episode function (unplaced) | not placed: execution.capabilities is an operation of the parent role launch, not of launch_hpc |
| contracts.py | native_result_operation_catalog | episode function (unplaced) | not placed: execution.results.* are operations of the results role (execution_result_acquisition), not of launch_hpc |
| contracts.py | _outcome | episode function (unplaced) | not placed: outcome shape of the execution.results.* operations (results role), not of launch_hpc |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (the closed branch is machinery: closed_credit.py) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical branch; the native_protein_structure_results branch applies to local protein-structure jobs, which an hpc assignment cannot request) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (the number); the view fields are shown from internal_summary progress |
| decision_context.py | NativeTaskContext | episode function | task.py decide + messages/internal_summary.py |
| decision_context.py | NativeTaskContext.assemble_decision_context | episode function | task.py decide (goal, execution_*, tools, time_accounting, current_credit, credit_binding, feedback, action_yields, library listings) + internal_summary; scope, working_state, visible_record_refs, current_evidence_vector, pending_work, visual_evidence, report_deliveries, controller_binding, job_episode_options, available_report_facts, requested_report_purpose/form, report_lifecycle, current_report_update: old-runner/report-form machinery or not applicable |
| decision_contracts.py | NativeDecisionDeliveryContracts | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_contracts.py | NativeDecisionDeliveryContracts.interpretation_context | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_contracts.py | NativeDecisionDeliveryContracts.exchange_schema | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_contracts.py | NativeDecisionDeliveryContracts.exchange_response | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_contracts.py | NativeDecisionDeliveryContracts.validate_contract_exchange_request | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_contracts.py | NativeDecisionDeliveryContracts.validate_contract_exchange_history | machinery | decision-exchange loop and its saved-exchange validation (request_context/select_action; README 3a) |
| decision_delivery.py | NativeDecisionDelivery | episode function | task.py decide (extra inputs) and instructions |
| decision_delivery.py | NativeDecisionDelivery.call | episode function | task.py decide: the context additions resource_context -> execution_resource, shared_information_context (none), launch_instruction_library, selected_launch_instructions, tool knowledge; child_options, completed_action_reports, requested_action_history, pending_work, execution_expectations, resource_tool_estimates, native_execution_expectations, waiting_support, contract_information_profile: machinery or services/estimate table (not built); saving and replay of the exchange: machinery |
| decision_delivery.py | NativeDecisionDelivery.instructions | episode function | task.py instructions |
| decision_delivery.py | NativeDecisionDelivery.conversation_key | machinery | conversation state (README 3a) |
| decision_exchange.py | NativeDecisionDeliveryExchange | machinery | decision-exchange loop (exchange_decision): a lookup is a tool, none is offered here (README 3a) |
| decision_exchange.py | NativeDecisionDeliveryExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision): a lookup is a tool, none is offered here (README 3a) |
| decision_presentation.py | present_native_task | episode function (unplaced) | not placed: the renderer of a selected_execution_task context; internal_summary.py never added that context for an HPC assignment and decision_provider used the renderer only for it, so this episode's prompt was the plain JSON context (carried as decide's context); the renderer lived in the old shared root (structural_homology_evidence_prompt), which is not read |
| decision_provider.py | NativeDecisionDeliveryProvider | episode function | task.py decide returns ModelRequest('REASONING', ...) |
| decision_provider.py | NativeDecisionDeliveryProvider.complete_decision | episode function | task.py decide: ModelRequest role REASONING; the system calls the provider; the renderer branch never applied |
| episode.py | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| from_parent.py | NativeAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | NativeAssignment.child_assignment_schema | machinery | the parent's view of the child's schema (README 3b C3); the restriction to the parent's frozen HPC requests (frozen_hpc_launch_request_missing) read the parent's assignment: contract_misfits |
| from_parent.py | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment._permitted | episode function (unplaced) | not placed: filter of the parent's frozen requests by the parent's launch constraints: reads the parent's own assignment (README 5 item 14) |
| from_parent.py | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (library validate_assignment) and task.py decide (terminal(settings).validate_assignment: workspace inside the resource workspace, account and scheduler constraints); the parent-role check, the parent's protein-structure inputs and immutable_input_versions checks read the parent's assignment and are not carried (contract_misfits) |
| from_parent.py | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (resource_kind declared hpc; the generic requested_job; the per-resource native job schemas are the library's validate_assignment) |
| from_parent.py | NativeAssignment._validate_request | episode function | messages/read_from_parent.py (library validate_assignment) and task.py decide (library TerminalExecution.validate_assignment: confinement to the configured workspace) |
| from_parent.py | NativeAssignment._launch | episode function (unplaced) | not placed: validation of the parent launch's execution_launch_assignment_v1 (requests, immutable_input_versions, constraints, launch_instructions): the child cannot read its parent's assignment (README 5 item 14) |
| from_parent.py | NativeAssignment._constraints | episode function (unplaced) | not placed: validation of the parent launch's allowed_resource_ids / allowed_kinds constraints: reads the parent's assignment |
| from_parent.py | NativeAssignment.required_return_sources | machinery | required_return_sources: the parent writes no return form (README 3b C4); it returned () for this episode |
| from_parent.py | NativeAssignment.initial_references | machinery | initial_references / records handed down: record_refs fields (README 3b P2); for an hpc assignment it validated no protein-structure inputs and returned no reference |
| goal.py | NativeGoal | episode function | goal.py GOAL, task.py INSTRUCTIONS |
| goal.py | NativeGoal.instructions | episode function | task.py instructions / INSTRUCTIONS |
| instructions.py | instructions | episode function | task.py instructions (library candidate: composition keyword arguments; the reasoning-commit, pending_child_delivery, wait, native-event and request_context paragraphs describe actions this episode does not offer) |
| internal_summary.py | NativeSummary | episode function | messages/internal_summary.py, task.py decide |
| internal_summary.py | NativeSummary.initial_decision_context | episode function | task.py decide: execution_resource (resource_information from settings) and its inventory snapshot |
| internal_summary.py | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | NativeSummary._with_selected_execution_task | episode function (unplaced) | not placed: added a selected_execution_task only for a local native protein-structure request (resource_kind local) with the ancestor's scientific_parent_task callback: never applies to an hpc assignment |
| internal_summary.py | NativeSummary._resource_information | episode function | task.py resource_information (library candidate; the configured resource only) |
| internal_summary.py | NativeSummary.capabilities | episode function (unplaced) | not placed: capabilities of every configured resource (all kinds, API operations): this episode shows its one configured resource |
| internal_summary.py | NativeSummary.resource_tool_contracts | episode function (unplaced) | not placed: commissionable launch/results operation contracts of every resource, for the parent roles (launch, results): not this episode's tools |
| operations.py | NativeOperations | episode function | task.py TOOLS and exec_command |
| operations.py | NativeOperations._delegate | machinery | routing by role and resource: each role is its own episode |
| operations.py | NativeOperations._practical_context | machinery | identity wrapper of the old context |
| operations.py | NativeOperations.initialize | machinery | initialisation of the practical state: initial validations are computed in messages/internal_summary.py |
| operations.py | NativeOperations._check_parent_inputs | episode function (unplaced) | not placed: re-read the parent launch's recorded request from runtime_episodes before every command and re-validated protein-structure inputs and immutable input versions: the child cannot read its parent's assignment (README 5 item 14) |
| operations.py | NativeOperations.state | machinery | exposed the old file-backed practical state: its content is the summary's receipts |
| operations.py | NativeOperations.catalog | episode function | task.py operation_catalog |
| operations.py | NativeOperations.execute | episode function | task.py exec_command (and action for the validation) |
| parent_launch_contract.py | parent_launch_schema | episode function (unplaced) | not placed: schema of the parent launch assignment: the child cannot read its parent's assignment |
| received_information.py | ReceivedExecutionInformation | machinery | what an ancestor may read from this return: the parent's read_from_child (README 3b R1) |
| received_information.py | ReceivedExecutionInformation.received_report_sources | machinery | ancestor-side reading of the return: parent's read_from_child |
| received_information.py | ReceivedExecutionInformation.received_report_facts | machinery | ancestor-side reading of the return: parent's read_from_child |
| received_information.py | ReceivedExecutionInformation.received_report_closure_facts | machinery | returned no closure facts; ancestor-side |
| received_record_selection.py | NativeReceivedRecordSelection | machinery | which known records count for the episode (record_selection): custody, records.holds (README 3c) |
| received_record_selection.py | NativeReceivedRecordSelection._received | machinery | which known records count for the episode (record_selection): custody, records.holds (README 3c) |
| received_reference_custody.py | NativeReceivedReferenceCustody | machinery | authentication of received references / received report validation: system custody (README 3b R1, R3, 3e F3) |
| received_reference_custody.py | NativeReceivedReferenceCustody.resolve_received_reference | machinery | authentication of received references / received report validation: system custody (README 3b R1, R3, 3e F3) |
| received_reference_custody.py | NativeReceivedReferenceCustody.validate_received_report | machinery | authentication of received references / received report validation: system custody (README 3b R1, R3, 3e F3) |
| received_reference_custody.py | NativeReceivedReferenceCustody.received_form_references | machinery | authentication of received references / received report validation: system custody (README 3b R1, R3, 3e F3) |
| report_delivery.py | NativeReportDelivery | episode function | messages/final_to_parent.py |
| report_delivery.py | NativeReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (facts + credit + finding; saving the form, release and pending_handles are machinery) |
| report_reference_access.py | NativeReportReferenceAccess | machinery | which references may appear in the report, by namespace: custody (records.holds; README 3b D2) |
| report_reference_access.py | NativeReportReferenceAccess.resolve | machinery | which references may appear in the report, by namespace: custody (records.holds; README 3b D2) |
| result_records.py | ExecutionResultRecords | episode function (unplaced) | not placed: results-role helpers kept in this copy (results target, selector, directory, windows, result reads, known-record selection); not used by launch_hpc, read old runtime tables |
| result_records.py | ExecutionResultRecords._versions | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._target | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._selector | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._result_directory | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._windows | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._selected_result_action | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._validate_result_body | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._read_result | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._selection | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| result_records.py | ExecutionResultRecords._context_target | episode function (unplaced) | not placed: results-role helper kept in this copy: not used by launch_hpc; reads old runtime_actions/runtime_episodes/receipt tables |
| retained_protein_reader.py | NativeRetainedProteinReader | episode function (unplaced) | not placed: protein-structure custody for native local jobs; validate_assignment refuses native_protein_structure on a non-local resource; reads runtime_episodes |
| retained_protein_reader.py | NativeRetainedProteinReader.retained_protein_structure_reader | episode function (unplaced) | not placed: protein-structure custody for native local jobs: not applicable to an hpc assignment |
| retained_protein_reader.py | NativeRetainedProteinReader._protein_reference_access | episode function (unplaced) | not placed: protein-structure custody for native local jobs: not applicable to an hpc assignment |
| retained_protein_reader.py | NativeRetainedProteinReader._retained_protein_result | episode function (unplaced) | not placed: protein-structure custody for native local jobs: not applicable to an hpc assignment |
| task.py | NativeTask | episode function | task.py decide, action, exec_command |
| task.py | NativeTask.next | episode function | task.py decide (the decision) and the loop; source_failed, replay, restore, pending deliveries, redelivery: machinery (README 3a, 3b) |
| task.py | NativeTask.apply_response | episode function | task.py action (decode, validate the selection, validate the command by the resource: Rejected on failure); the report_update admission and validate_report(grain launch_hpc) of the model's report are not carried; job_child, reads.map and ContractInformation branches: other roles |
| task.py | NativeTask.execute | episode function | task.py exec_command (the journalling of the action, its credit and the controller value are the system's) |
| task_state.py | NativeTaskState | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.__init__ | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.bind_execution_context | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.record_execution_failure | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.restore | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.record_effect | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| task_state.py | NativeTaskState.checkpoint | machinery | task state, checkpoint/restore and record_effect: old-runner machinery (README 3a, 3e); the decision counter, feedback, last outcome are the loop's (decide feedback, view.outcomes); report_values/report_basis (the model's report_update) are not carried |
| terminal_assignment.py | TerminalAssignment | episode function | messages/read_from_parent.py, task.py decide |
| terminal_assignment.py | TerminalAssignment._assignment | episode function | read_from_parent (validate_assignment; resource_kind a DeclaredField hpc) and decide (TerminalExecution.validate_assignment) |
| terminal_assignment.py | TerminalAssignment.prepare_assignment | episode function | read_from_parent and decide, as _assignment |
| terminal_assignment.py | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_contracts.py | operation_catalog | episode function | task.py operation_catalog (library candidate) |
| terminal_credit.py | TerminalCredit | episode function | credit.py |
| terminal_credit.py | TerminalCredit.credit_view | episode function | credit.py credit (library project_practical_credit) |
| terminal_credit.py | TerminalCredit.completion_for_action | episode function | messages/internal_summary.py completion_proof |
| terminal_execution.py | TerminalExecutionBehavior | episode function | assembled from task.py, credit.py, messages/*, yield_estimator.py; episode.py |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | settings (resource, initial_information, coordinator_workspace; services, store, flux_balance_input_reader: old-runner wiring) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record(): deleted (README 3e) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind is deleted (README 3d) |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py selection_schema: the tool action only |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function | yield_estimator.py: CompletionYieldController (README 7b: PracticalYieldEstimator) |
| terminal_goal.py | TerminalGoal | episode function | task.py INSTRUCTIONS |
| terminal_goal.py | TerminalGoal.instructions | episode function | task.py instructions |
| terminal_goal.py | TerminalGoal._resource_instructions | episode function | task.py decide: LaunchInstructions(directory).for_resource(settings['resource']) (library) |
| terminal_operations.py | TerminalOperations | episode function | task.py exec_command, action, terminal |
| terminal_operations.py | TerminalOperations._operations | episode function | task.py terminal(settings): library TerminalExecution with the library artifact selector |
| terminal_operations.py | TerminalOperations.catalog | episode function | task.py operation_catalog |
| terminal_operations.py | TerminalOperations.execute | episode function | task.py action (argument and command validation -> Rejected), exec_command (execution failure as a recorded failure, context carry-forward, validations, receipt published through ctx.store.artifact) and run_command (BLOCKED-ON-JOB-SERVICE); the operation ledger (state.begin/finish, completed intent returns its receipt) is the system's attempts journal and ctx.operation_key |
| terminal_report.py | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | TerminalReport.facts | episode function | messages/final_to_parent.py facts |
| terminal_report.py | TerminalReport.resolve | machinery | resolution of practical_receipt references through the practical state / PracticalReceiptInformation: custody (records.holds) |
| terminal_report.py | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; the validate_form call raises validate_form_not_built:A102) |
| terminal_state.py | TerminalState | machinery | file-backed practical state: its content is the summary's receipts; initial validations in internal_summary.py |
| terminal_state.py | TerminalState._state_directory | machinery | state directory under the run directory (practical-execution/<digest>): files outside custody |
| terminal_state.py | TerminalState.initialize | episode function | messages/internal_summary.py: initial validations of the assignment with no facts (assess_validations) |
| terminal_state.py | TerminalState.state | machinery | state cache by episode id |
| terminal_summary.py | TerminalSummary | episode function | messages/internal_summary.py, task.py decide |
| terminal_summary.py | TerminalSummary.initial_decision_context | episode function | task.py decide: execution_resource inventory snapshot from settings |
| terminal_summary.py | TerminalSummary._resource_information | episode function | task.py resource_information (library candidate) |
| terminal_summary.py | TerminalSummary.decision_context | episode function | task.py decide: execution_assignment, execution_resource, coordinator_workspace; internal_summary: execution_progress (progress), execution_completion (completion_proof) |
| to_parent.py | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (all nine fact sources, selectable) |
| to_parent.py | NativeReport.facts | episode function | messages/final_to_parent.py facts (the closed-credit facts are machinery) |
| to_parent.py | NativeReport._live_facts | episode function | messages/final_to_parent.py facts; messages/internal_summary.py returnable_handoff (library candidate); the received handoffs and result windows of the old _received are none for this role; the protein-structure facts are of local/results roles |
| to_parent.py | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; validate_form raises validate_form_not_built:A102) |
| waiting.py | NativeWaiting | machinery | wait/suspension machinery (README 3b) |
| waiting.py | NativeWaiting.suspension_changed | machinery | wait/suspension machinery (README 3b) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (the practical_assignment_v1 branch; the API branches are the API sibling's; library candidate) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, raises execution_original_task_yield_profile_required) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller: CompletionYieldController(cutoff as cost, target from parent_input); PracticalYieldEstimator -> README 7b |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | estimator accessor: no episode supplies an estimator (README 3d) |
