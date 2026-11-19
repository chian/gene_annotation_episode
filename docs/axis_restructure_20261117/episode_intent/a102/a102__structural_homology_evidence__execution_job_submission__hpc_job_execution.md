# a102/structural_homology_evidence/execution_job_submission/hpc_job_execution — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_job_submission/hpc_job_execution/`
(42 files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` not read). Nothing from the old
shared root was read; where behaviour lives there (`terminal_execution.TerminalExecution`, `practical_execution_state.PracticalState`,
the prompt helpers), this page says only what this episode's own files ask of it.

Old binding: class `ExecutionEpisode`, `binding_path =
'structural_homology_evidence/execution_job_submission/hpc_job_execution'`, `commissioning_parent =
'structural_homology_evidence/execution_job_submission'`, old role `launch_hpc`, `entry_roles = ()`,
`replaces_default_instructions = True`, version `execution_episode_v1`. Decision source: `NativeTask`. Prompt
renderer: `present_native_task`.

## What this episode is for

It is the execution agent for one concrete HPC job on one configured HPC resource: it writes and runs shell
commands until the requested endpoint is validated. In its own words (`terminal_goal.py`, the whole text):

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run
> the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery
> from the actual resource instructions and observed results. No sequence of setup or job-stage operations is
> prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical
> inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual
> result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records
> command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission
> outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided
> resource-specific instructions, account, storage and existing authentication route. workdir and env apply to
> the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local
> run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation
> belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is
> the exact configured transport prefix. Append the remote shell command as its final argument and preserve
> stdin. The supplied configuration gives the existing connection details. target=resource uses that transport
> directly. The episode iterator decides continuation from credit; add no stopping budget.

followed by "Resource instructions supplied from the frozen library:" and the sections the launch instruction
library selects for this resource (`library.for_resource`). `goal.py` delegates to this text.

## Task and instructions

- One unit is one `exec_command` tool action (`action_policy.py`: `('tool',)` only). No reasoning, children,
  waiting or redelivery.
- Instructions (`instructions.py`, `decision_delivery.instructions`): the goal text above (it replaces the
  default), then the same composition paragraphs as its parent where they apply.
- `task.py`: the parent's decision-source text without the reasoning branch; report updates validated for grain
  `launch_hpc`.

## What it reads from its parent's assignment

`from_parent.py`, `operations.py`, `terminal_assignment.py`:

- Assignment form: `anyOf` the practical assignment forms of the configured HPC resources (`resource_id`,
  `resource_kind: hpc`, workspace, `requested_job`, endpoint, `initial_context`, ...).
- Under an `hpc` ancestor the form offered to the launch parent is narrowed to an `enum` of the parent's own
  permitted HPC requests (`frozen_hpc_launch_request_missing` if none): the HPC planning branch has frozen the job.
- The request must name a bound HPC resource, its workspace confined to the configured workspace, and pass the
  command executor's assignment validation.
- It must be commissioned by `launch`; the parent launch's `immutable_input_versions` and the request's
  protein-structure inputs are validated, and are re-checked from the parent's recorded request before
  initialize and every command (`_check_parent_inputs`).
- Required returns: none.

## Children

None (`child_eligibility.py`).

## Decision state and what it shows the model

- Model inputs (`decision_context.py`): the same fields as the parent's `decision_state.py` (identical text).
- Own block (`internal_summary.py` → `terminal_summary.decision_context`): `execution_assignment`,
  `execution_resource` (kind, workspace, `kind`, `policy`, `account`, `ssh_argv`, `python_executable`, `scheduler`,
  inventory snapshot), `coordinator_workspace`, `execution_progress` (command-state credit view),
  `execution_completion` (completion proof); plus `selected_execution_task` when the request is a local native
  protein-structure job (parent's scientific question and tool info).
- Initial context: `execution_resource_capabilities` and `execution_initial_information`.
- Context additions (`decision_delivery.py`): as the parent's, inline in the call; execution expectations
  captured for `launch_hpc`.
- Presentation (`decision_presentation.py`, `present_native_task`): the selected execution TASK, a STEERING block
  (action yields, controller, current credit, completed action reports, last outcome, feedback, child reports,
  pending work, deliveries, waiting support, resource estimates, pending delivery) and "Current execution
  information" (`execution_completed`, practical progress `credit, initial_credit, operational_credit,
  requirements, satisfied_keys`, practical completion). It refuses a context that is not a selected execution
  context.

## Tools it offers

One tool (`terminal_contracts.operation_catalog`):

- `exec_command` — "Execute the shell command you write on the assigned resource. Use normal shell/file tools to
  inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed.
  Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly
  on each action." Arguments: `cmd` (string or argv list), `workdir`, `env` (required), `target` (`resource` or
  `coordinator`).

Execution (`terminal_operations.py`): argument and action validation (invalid → `invalid` outcome with feedback);
an already completed operation key returns its saved receipt; a raised error becomes a failed native outcome;
the command outcome is finalized for scientific evidence; cwd/env revision tracked; endpoint validations assessed;
the receipt is published as a practical receipt record.

## How its credit is counted

Credit kind `operational`. `credit.py` → `terminal_credit.credit_view`: the practical command state's own
`credit_view()` (the requirements/satisfied keys of the assignment's endpoint predicates; computed in the old shared
`PracticalState`, not read). The closed view captured at close is returned afterwards (`closed_credit.py`).
Completion: the state's completion proof for the operation key; verification via the recorded-history verdict,
else `state.verify_completion`.

## Continuation

`yield_estimator.py`: old `YieldController` (today's accumulation estimator):

- profile `launch_hpc:{request yield class}` from `task_yield_profiles`, class
  `practical_hpc[_{native_*}]_{handoff|outputs}` by the request's endpoint (`usable_handoff` / `completed_job_outputs`);
- settings: the profile's `cutoff` (above zero) and `parameters`;
- `estimate_with_context=PracticalYieldEstimator(verify_completion)`: exact zero once completion is verified.

`private_yield_binding` must be enabled.

## What it reports to its parent

`to_parent.py`, `terminal_report.py`:

- `practical_completed` — "Whether original requested endpoint predicates have a saved validated completion.";
- `practical_receipt_digests`, `practical_receipt_refs` — the original selected command receipts;
- `execution_handoff_refs` — handoffs received plus returnable handoffs found among its own practical receipts;
- `execution_result_refs`, `execution_completed` (= `practical_completed`), `execution_result_origin`, file
  sources, protein-structure sources.

Any report field bound to a fact must equal the recorded fact.

## How it differs from similar episodes

- Against its sibling `api_job_execution`: runs shell commands through `exec_command` instead of API service
  operations; `tool` only (no `wait`); credit is the command state's endpoint-predicate progress instead of the API
  executor's view; own prompt `present_native_task` instead of `render_api_launch_prompt`; the parent's form is
  narrowed to frozen requests under an HPC planning ancestor; handoffs are also found in its own receipts.
- Against its parent `execution_job_submission`: no children or reasoning; accumulation instead of bounded
  continuation; it does the work its parent only routes.
- File layout differs from both: the command behaviour is split into `terminal_*.py` parts (the parent and API
  sibling carry one 242-line `terminal_execution.py`); decision code is `decision_delivery.py` +
  `decision_context.py` (like the head) instead of the parent's six split files; result helpers are merged in
  `result_records.py`.

## Points the carry-over has to settle (seen in these files)

- `PracticalYieldEstimator` passed as `estimate_with_context`; only the three yield estimators exist now.
- `_check_parent_inputs` and the history verdict read the old `runtime_episodes`/`runtime_observations` tables.
- `required_return_sources` returns `()` in both branches (kept as written).

## Old-runner names (totals for this episode)

| Group | Distinct names | Uses |
|---|---|---|
| `self.workflow.<member>` | 74 | 196 |
| BindingContext (`binding_context`), receipts, return records, `UnitRef`, raw `store.db.execute`, `_ready_owned_child` | 6 | 27 |
| imports from old `root.a102` shared modules (incl. `runtime`, `providers`, `communication`, `decision_context`, `episode_bindings`, `episode_journal`, `composition_information`) | 44 | 106 |
| old `services.<member>` (services held the Workflow) | 4 | 4 |
| old journal and receipt tables | 8 | 49 |
| old yield names | 5 | 18 |
| symbols through `runtime`, `runtime_prompt`, `providers` | 55 | 148 |

Counted mechanically from the files at `97308b94c`; every row (name, file, uses, purpose) is in
`runs/carry_over/calls/a102_01.tsv`. `workflow.x` and `source.workflow.x` are counted as `self.workflow.x`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty | none |
| `action_policy.py` | 7 | tool only | none |
| `binding_record.py` | 9 | binding identity record (path hpc_job_execution) | none |
| `child_eligibility.py` | 10 | no children | none |
| `closed_credit.py` | 117 | closed credit capture/return (same as launch) | `EpisodeReceipts` 2, `EpisodeReturnRecords` 2, `import root.a102.episode_receipts` 1, `import root.a102.episode_return_records` 3, `store.db.execute` 5, `table runtime_episodes` 2, `table runtime_forms` 3, `table runtime_observations` 1, `table runtime_receipt_inheritance` 2, `table runtime_record_receipts` 2, `table sqlite_master` 2 |
| `completion.py` | 49 | completion delegated to the resource command state; recorded-history verdict | `import root.a102.episode_return_records` 1, `import root.a102.method_loop.identities` 1, `import root.a102.numerical` 1, `import root.a102.practical_yield` 1, `store.db.execute` 1, `table runtime_observations` 1, `UnitRef` 2, `ESTIMATOR_VERSION` 2, `NumericBand` 2 |
| `configuration.py` | 62 | construction settings (same as launch) | `import root.a102.api_service_execution` 1, `import root.a102.execution_progress` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.numerical` 1, `YieldController` 3, `YieldParameters` 3 |
| `contracts.py` | 53 | constants; operation_catalog from terminal_contracts | `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.execution_contracts` 1, `import root.a102.launch_instructions` 1, `import root.a102.local_file_capture_results` 1, `import root.a102.native_protein_structure_acquisition` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.practical_receipt_information` 1, `import root.a102.resource_records` 1 |
| `credit.py` | 27 | operational credit = resource command state credit view (or native protein results) | none |
| `decision_context.py` | 45 | model inputs (same text as launch decision_state) | `binding_context` 1, `import root.a102.runtime` 2, `runtime.FACT_MEANINGS` 1, `runtime.FACT_SOURCES` 1, `runtime.Mapping` 3, `runtime._plain` 2, `runtime._references_in` 1, `self.workflow.binding_context` 1, `self.workflow.catalog` 1, `self.workflow.controller_binding` 1, `self.workflow.delivery_status` 1, `self.workflow.extra_report_sources` 1, `self.workflow.is_scientific_source` 1, `self.workflow.job_episode_options` 1, `self.workflow.journal` 3, `self.workflow.knowledge` 1, `self.workflow.local_outcome_preview` 1, `self.workflow.pending_work` 1, `self.workflow.receipt_projection` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_binding` 1, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 1, `self.workflow.store` 3, `self.workflow.tools` 1, `self.workflow.working_state` 1, `table runtime_actions` 2 |
| `decision_contracts.py` | 128 | request_context exchange envelope and replay checks | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime.apply_state_frame` 1, `runtime.composition_lookup_schema` 2, `runtime.CONTRACT_INFORMATION_OPERATIONS` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.Draft202012Validator` 1, `runtime.instructional_model_context` 1, `runtime.is_contract_information` 1, `runtime._json` 8, `runtime.Mapping` 2, `runtime.model_snapshot` 1, `runtime._object` 3, `runtime._recorded_action_generation_schema` 1, `runtime._references_in` 1, `runtime.requested_contract_information` 1, `runtime.ValidationError` 1, `runtime.WorkflowError` 9, `self.workflow.contract_information_reply` 1, `self.workflow.decision_exchanges` 2, `self.workflow.journal` 1, `self.workflow.store` 2, `self.workflow.validate_contract_information` 2, `table runtime_model_calls` 1 |
| `decision_delivery.py` | 137 | decision call with inline context additions (expectations captured for launch_hpc) | `binding_context` 1, `import root.a102.decision_context` 1, `import root.a102.episode_work_report` 2, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 2, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime._action_generation_schema` 1, `runtime._ASSIGNMENT_TRANSPORT` 1, `runtime.child_option_information` 1, `runtime.DECISION_EXCHANGE_PROTOCOL` 5, `runtime._digest` 1, `runtime.instructional_model_context` 1, `runtime._json` 4, `runtime.Mapping` 1, `runtime._recorded_assignment_transport` 1, `runtime.WorkflowError` 5, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 1, `self.workflow.contract_information_profile` 1, `self.workflow.decision_exchanges` 1, `self.workflow.decision_protocol` 3, `self.workflow.episode_bindings` 1, `self.workflow.execution_expectations` 1, `self.workflow.freeze_contract_information` 1, `self.workflow.freeze_literature_numerical_contracts` 1, `self.workflow.history_preview` 1, `self.workflow.is_job_source` 3, `self.workflow.job_episodes` 2, `self.workflow.journal` 1, `self.workflow.launch_instructions` 2, `self.workflow.native_estimation_context` 1, `self.workflow.numerical_contracts` 1, `self.workflow.pending_work` 1, `self.workflow.permits_common_action` 1, `self.workflow.provider` 2, `self.workflow.receipts` 4, `self.workflow.resource_context` 1, `self.workflow.resource_estimator` 5, `self.workflow.services` 1, `self.workflow.shared_information_context` 1, `self.workflow.uses_received_record_context` 2, `self.workflow.validate_contract_information` 2, `self.workflow.waiting_support` 1, `table runtime_model_calls` 5 |
| `decision_exchange.py` | 108 | request_context exchange loop | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime._action_generation_schema` 1, `runtime._category_yield_parameters` 1, `runtime.child_option_information` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.instructional_model_context` 2, `runtime._json` 2, `runtime.lookup_attempts` 1, `runtime.Mapping` 1, `runtime.model_snapshot` 1, `runtime._plain` 2, `runtime.requested_contract_information` 1, `runtime.schema_failure_diagnostic` 2, `runtime.sqlite3` 1, `runtime.state_frame` 1, `runtime.ValidationError` 4, `runtime.yield_table` 1, `self.workflow.controller_binding` 1, `self.workflow.decision_exchanges` 1, `self.workflow.execute` 1, `self.workflow.journal` 1, `self.workflow.run_id` 1, `self.workflow.services` 1, `self.workflow.validate_contract_information` 1, `table runtime_model_calls` 2 |
| `decision_presentation.py` | 20 | present_native_task: selected execution TASK + STEERING + execution progress | `import root.a102.structural_homology_evidence_prompt` 1 |
| `decision_provider.py` | 20 | presentation choice for selected execution contexts | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 1, `import root.a102.structural_homology_evidence_prompt` 1, `self.workflow.provider` 1, `self.workflow.specialist` 1 |
| `episode.py` | 34 | binding identity: role launch_hpc, parent execution_job_submission, not an entry, replaces default instructions | none |
| `from_parent.py` | 116 | HPC request; under an hpc ancestor the form is the frozen HPC requests of the parent launch; parent must be launch; required returns none | `import root.a102.native_protein_structure_tool_info` 1, `import root.a102.protein_structure_operands` 3, `services.annotation_task_required` 1 |
| `goal.py` | 7 | instructions delegated to the resource command behaviour | none |
| `instructions.py` | 22 | instruction composition | `binding_context` 1, `import root.a102.runtime_prompt` 2, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL` 1, `runtime_prompt.INSTRUCTIONS` 3, `runtime_prompt.REASONING_COMMIT_REQUIREMENT` 1, `self.workflow.binding_context` 1, `self.workflow.decision_protocol` 1, `self.workflow.knowledge` 1, `self.workflow.launch_instructions` 1, `self.workflow.native_event_information` 1, `self.workflow.permits_common_action` 3, `self.workflow.specialist` 1 |
| `internal_summary.py` | 101 | initial context, delegated decision context + selected_execution_task, capabilities, resource tool contracts | `import root.a102.native_protein_structure_tool_info` 1, `services.scientific_parent_task` 1 |
| `operations.py` | 40 | delegate to resource executor after parent-input check; state for local/hpc roles | `import root.a102.protein_structure_operands` 1, `store.db.execute` 1, `table runtime_episodes` 1 |
| `received_information.py` | 37 | facts the annotation/head parent may receive | `import root.a102.protein_structure_result_views` 1 |
| `received_record_selection.py` | 35 | received handoffs/results of own request | none |
| `received_reference_custody.py` | 35 | received reference resolution/admission | none |
| `report_delivery.py` | 25 | final form = report values + facts | `binding_context` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.library.report_fact_assembly` 1, `import root.a102.runtime` 2, `runtime.form_with_facts` 1, `runtime._json` 2, `runtime.Record` 2, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.facts` 1, `self.workflow.journal` 2, `self.workflow.pending_handles` 1, `self.workflow.release` 2, `self.workflow.source_credit_view` 1, `table runtime_forms` 2 |
| `report_reference_access.py` | 45 | reference resolution | `import root.a102.episode_bindings` 2 |
| `result_records.py` | 158 | versions, target, selector, windows, result receipts, receiver selection, handoff match | `EpisodeReceipts` 2, `import root.a102.episode_receipts` 1, `import root.a102.execution_input_versions` 1, `import root.a102.protein_structure_selection` 1, `services.record_selection` 1, `store.db.execute` 5, `table runtime_actions` 2, `table runtime_episodes` 1, `table runtime_receipt_inheritance` 2, `table sqlite_master` 1 |
| `retained_protein_reader.py` | 95 | retained protein reader | `import root.a102.execution_contracts` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.protein_structure_contracts` 1, `import root.a102.protein_structure_operands` 1, `import root.a102.protein_structure_selection` 1, `import root.a102.state` 1, `store.db.execute` 1, `table runtime_episodes` 1 |
| `task.py` | 221 | decision source; no reasoning branch; grain launch_hpc | `binding_context` 1, `_execution_context._ready_owned_child` 1, `import root.a102.episode_source_failure` 1, `import root.a102.library.action_contracts` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.providers` 1, `import root.a102.read_mapping` 1, `import root.a102.runtime` 2, `runtime.AcquisitionError` 2, `runtime.ActionFailure` 1, `runtime.ContractError` 1, `runtime.ContractInformationError` 1, `runtime._decode_recorded_action_response` 1, `runtime.Draft202012Validator` 2, `runtime.EventTargetError` 2, `runtime.inspect` 1, `runtime._json` 5, `runtime.Mapping` 2, `runtime.nullcontext` 5, `runtime.observes_action_outcome` 1, `runtime.ReportBoundaryError` 1, `runtime.ReportRedelivery` 2, `runtime.schema_failure_diagnostic` 1, `runtime.SourceEnd` 2, `runtime.sqlite3` 2, `runtime.subprocess` 2, `runtime.validate_form` 1, `runtime.ValidationError` 3, `runtime._wait_target_feedback` 2, `runtime.WorkflowError` 2, `self.workflow.action_schema` 1, `self.workflow.automatic_score_updates` 1, `self.workflow.binding_context` 1, `self.workflow.completed_unit` 3, `self.workflow.completions` 3, `self.workflow.controller_value` 2, `self.workflow.decision_exchanges` 3, `self.workflow.delivery_resolution_inputs` 1, `self.workflow.execute` 1, `self.workflow.execution_binding` 7, `self.workflow.inprocess_replay` 4, `self.workflow.journal` 7, `self.workflow.last_observed_credit` 1, `self.workflow.next_return` 1, `self.workflow.pending_work` 1, `self.workflow.perform_selected_wait` 1, `self.workflow.permits_common_action` 1, `self.workflow.receive_native_outcome` 1, `self.workflow.receive_outcome` 1, `self.workflow.resolve_pending_deliveries` 1, `self.workflow.resolver` 1, `self.workflow.retain_shared_grading_results` 1, `self.workflow.run_id` 3, `self.workflow.selected` 3, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 1, `self.workflow.store` 8, `self.workflow.validate_report` 1, `table runtime_actions` 8, `table runtime_episodes` 1, `table runtime_model_calls` 2 |
| `task_state.py` | 108 | source state | `import root.a102.episode_source_failure` 1, `import root.a102.runtime` 2, `runtime.ActionLeaf` 1, `runtime.EFFECT_VERSION` 1, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime._object` 1, `runtime._plain` 1, `runtime.Record` 1, `self.workflow.archive` 1, `self.workflow.completions` 4, `self.workflow.context` 1, `self.workflow.controller_value` 1, `self.workflow.execution_binding` 4, `self.workflow.grains` 1, `self.workflow.inprocess_replay` 7, `self.workflow.journal` 5, `self.workflow.progress_provider` 2, `self.workflow.recover_commissions` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_view` 1, `self.workflow.store` 2, `table runtime_actions` 5 |
| `terminal_assignment.py` | 22 | command-behaviour assignment checks | none |
| `terminal_contracts.py` | 24 | exec_command contract | `import root.a102.acquisition` 1, `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.terminal_execution` 1 |
| `terminal_credit.py` | 11 | command-state credit view and completion | none |
| `terminal_execution.py` | 41 | command behaviour class assembled from terminal_* parts | `import root.a102.practical_yield` 1, `PracticalYieldEstimator` 2 |
| `terminal_goal.py` | 18 | execution agent instructions + frozen resource instructions | `services.workflow` 1 |
| `terminal_operations.py` | 47 | exec_command execution with receipts and validations | `import root.a102.practical_receipt_information` 1, `import root.a102.terminal_scientific_evidence` 2 |
| `terminal_report.py` | 31 | practical_completed, receipt digests, receipt refs; report must equal facts | `import root.a102.practical_receipt_information` 2 |
| `terminal_state.py` | 18 | practical state per episode | none |
| `terminal_summary.py` | 16 | resource information and command decision context | none |
| `to_parent.py` | 62 | facts: command facts + handoffs found in practical receipts + result refs; report must equal facts | `import root.a102.local_file_capture_results` 1, `import root.a102.protein_structure_result_views` 2 |
| `waiting.py` | 9 | suspension forwarded to backend | `self.workflow.execution_backend` 1, `self.workflow.execution_handle` 2 |
| `yield_estimator.py` | 48 | accumulation controller, profile launch_hpc:<class>, practical completion estimate | `import root.a102.numerical` 1, `import root.a102.practical_yield` 1, `PracticalYieldEstimator` 2, `YieldController` 2, `YieldParameters` 2 |

## Carried over

One row per old function, class and method (`runs/carry_over/functions/a102__structural_homology_evidence__execution_job_submission__hpc_job_execution.tsv`). Kind is the old kind. Class column: machinery (not carried, with the reason) or episode function (the new place; "library candidate" marks a function that stays in this episode's file until a library function is made; "unplaced" is also listed in the blocked file).

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| action_policy.py | class | NativeActionPolicy | episode function | task.py action: the one action is the exec_command tool |
| action_policy.py | method | NativeActionPolicy.permitted_common_actions | episode function | task.py action: the one action is the exec_command tool |
| binding_record.py | class | NativeBindingRecord | machinery | the binding's own as_record() is deleted (the system journals settings and service names) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | the binding's own as_record() is deleted (the system journals settings and service names) |
| child_eligibility.py | class | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | method | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | method | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| closed_credit.py | class | NativeClosedCredit | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| closed_credit.py | method | NativeClosedCredit._closed_credit_carrier | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| closed_credit.py | method | NativeClosedCredit._closed_credit_receipts | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| closed_credit.py | method | NativeClosedCredit._closed_credit_value | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| closed_credit.py | method | NativeClosedCredit._closed_credit_facts | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| closed_credit.py | method | NativeClosedCredit._closed_operational_credit_view | machinery | closed credit view authenticated through runtime_* tables and receipt inheritance: deleted (the system returns completion['credit']) |
| completion.py | class | NativeCompletion | machinery | class: closed-history completion verdict and estimator callbacks |
| completion.py | method | NativeCompletion.completion_for_action | machinery | completion proof handed to the estimator per action: no way into the controller (README 5 item 5) |
| completion.py | method | NativeCompletion._closed_completion_verdict | machinery | reads runtime_observations (controller observations): deleted |
| completion.py | method | NativeCompletion.verify_completion | episode function | messages/internal_summary.py completion_proof (the practical completion proof; the estimator-verdict route is machinery); library candidate |
| configuration.py | class | NativeConfiguration | episode function | values: ctx.settings (task.py _operations / _resource_information / _launch_instructions: resource, coordinator_workspace, launch_instructions_directory) and settings task_yield_profiles (yield_estimator.py); the resource configuration is validated by TerminalExecution (library) |
| configuration.py | method | NativeConfiguration.__init__ | episode function | same: configuration values become settings read where used; api/local resources, handoff/acquired units, log window, results yield profiles, protein-structure readers and local file sources belong to other roles (see unplaced); require_private_yield is a flag of the old per-episode controller wiring: deleted |
| contracts.py | function | launch_operation_catalog | episode function (unplaced) | UNPLACED: the 'execution.capabilities' operation of the launch role (the parent's tool), not a tool of launch_hpc |
| contracts.py | function | native_result_operation_catalog | episode function (unplaced) | UNPLACED: execution.results.* operations belong to the results role (execution_result_acquisition), not to launch_hpc |
| contracts.py | function | _outcome | episode function (unplaced) | UNPLACED: outcome builder of the launch/results-role operations; the exec_command tool builds its own outcome |
| credit.py | class | ExecutionEpisodeCredit | machinery | class: closed-credit mix-in over the credit view (kept pieces are the three methods below) |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (project_practical_credit over the receipts of the summary); the closed-view branch is machinery |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| decision_context.py | class | NativeTaskContext | episode function | task.py decide (context) and messages/internal_summary.py internal_summary; reads of runtime_actions/image.view, receipt_projection, pending_work, report_deliveries, job_episode_options, tool_knowledge are machinery or not offered here |
| decision_context.py | method | NativeTaskContext.assemble_decision_context | episode function | task.py decide: goal, execution_*, practical_progress, current_credit, completed_action_reports, last_local_outcome, feedback, action_yields, time_accounting, tools; the runtime_actions image.view read, visible_record_refs, pending_work, report_deliveries, controller_binding, available_report_facts and report-form fields are machinery (no parent-written form, no pending work) |
| decision_contracts.py | class | NativeDecisionDeliveryContracts | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_contracts.py | method | NativeDecisionDeliveryContracts.interpretation_context | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_contracts.py | method | NativeDecisionDeliveryContracts.exchange_schema | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_contracts.py | method | NativeDecisionDeliveryContracts.exchange_response | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_contracts.py | method | NativeDecisionDeliveryContracts.validate_contract_exchange_request | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_contracts.py | method | NativeDecisionDeliveryContracts.validate_contract_exchange_history | machinery | decision-exchange schema and saved-request checks (exchange_decision loop): deleted; the system compares a rebuilt model request with its record |
| decision_delivery.py | class | NativeDecisionDelivery | episode function | task.py decide / INSTRUCTIONS; recording parts are machinery |
| decision_delivery.py | method | NativeDecisionDelivery.call | episode function | task.py decide: launch_instruction_library and selected_launch_instructions in the context (_launch_instructions), initial context (_initial_context); the saved-call/exchange/session/receipt parts are machinery; execution_expectations, resource_tool_estimates and native_execution_expectations are not provided yet (README 5 item 19) and are listed as unplaced |
| decision_delivery.py | method | NativeDecisionDelivery.instructions | episode function | task.py decide: INSTRUCTIONS (the goal text) + the resource instructions of the launch library; the composer's reasoning/wait/exchange/redelivery paragraphs describe actions that do not exist |
| decision_delivery.py | method | NativeDecisionDelivery.conversation_key | machinery | provider conversation key: conversation state is deleted (every ModelRequest carries the full context) |
| decision_exchange.py | class | NativeDecisionDeliveryExchange | machinery | the decision-exchange loop (exchange_decision): deleted; a lookup would be a tool, a rejected answer is Rejected(feedback) |
| decision_exchange.py | method | NativeDecisionDeliveryExchange.exchange_decision | machinery | the decision-exchange loop (exchange_decision): deleted; a lookup would be a tool, a rejected answer is Rejected(feedback) |
| decision_presentation.py | function | present_native_task | episode function (unplaced) | UNPLACED: the renderer helpers (_selected_execution_task, _steering, _execution_presentation_values, is_selected_execution_context) lived in structural_homology_evidence_prompt, which has no module now (axis_shared_modules.tsv: none); decide sends the structured context as ModelRequest.context |
| decision_provider.py | class | NativeDecisionDeliveryProvider | machinery | model-provider routing and call: decide returns a ModelRequest, the system calls and records the provider |
| decision_provider.py | method | NativeDecisionDeliveryProvider.complete_decision | machinery | model-provider routing and call: decide returns a ModelRequest, the system calls and records the provider |
| episode.py | class | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| from_parent.py | class | NativeAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | method | NativeAssignment.child_assignment_schema | episode function (unplaced) | UNPLACED: enum of the parent launch's frozen hpc requests: the parent's msg_to_child names the assignment it passes; the child cannot read its parent's assignment |
| from_parent.py | method | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment._permitted | episode function (unplaced) | UNPLACED: filters the parent launch's frozen requests by the parent's own constraints: reads the parent assignment |
| from_parent.py | method | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (practical assignment contract, resource kind); the parent-launch re-read, immutable_input_versions and protein-structure input checks are commission checks / reads of another Episode's records: not carried |
| from_parent.py | method | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property; the requested_job alternatives are one record field) |
| from_parent.py | method | NativeAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py exec_command (TerminalExecution.validate_action validates the assignment against the configured resource) |
| from_parent.py | method | NativeAssignment._launch | episode function (unplaced) | UNPLACED: validation of the parent launch assignment (requests, immutable_input_versions, constraints): the child cannot read its parent assignment |
| from_parent.py | method | NativeAssignment._constraints | episode function (unplaced) | UNPLACED: validation of the parent launch constraints: the child cannot read its parent assignment |
| from_parent.py | method | NativeAssignment.required_return_sources | machinery | returns () in both branches: the parent selects return fields in msg_to_child; credit and finding are always returned |
| from_parent.py | method | NativeAssignment.initial_references | machinery | initial receipt references of the old receipt ledger (protein-structure job inputs, handoff_ref): custody replaces the ledger; the assignment names no records |
| goal.py | class | NativeGoal | episode function | goal.py and task.py INSTRUCTIONS |
| goal.py | method | NativeGoal.instructions | episode function | task.py INSTRUCTIONS (the delegate is terminal_goal.TerminalGoal.instructions) |
| instructions.py | function | instructions | episode function | task.py decide: INSTRUCTIONS + resource instructions; the reasoning, tool_knowledge, redelivery, wait and decision-exchange paragraphs describe actions this episode does not offer |
| internal_summary.py | class | NativeSummary | episode function | messages/internal_summary.py and task.py decide |
| internal_summary.py | method | NativeSummary.initial_decision_context | episode function | task.py _initial_context: execution_resource_capabilities, execution_initial_information |
| internal_summary.py | method | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion) |
| internal_summary.py | method | NativeSummary._with_selected_execution_task | episode function (unplaced) | UNPLACED: applies only to a local native protein-structure request and needs the ancestor scientific_parent_task callback; an hpc assignment returns the value unchanged |
| internal_summary.py | method | NativeSummary._resource_information | episode function | task.py _initial_context (capabilities of the configured resource) |
| internal_summary.py | method | NativeSummary.capabilities | episode function | task.py _initial_context (availability unknown, observed_at caller_configuration, tool_names) |
| internal_summary.py | method | NativeSummary.resource_tool_contracts | episode function (unplaced) | UNPLACED: the commissionable launch/results operation contracts of every configured resource, for the parent's routes: the parent describes its children in its own task.py; this episode's contract is TOOL_DESCRIPTION |
| operations.py | class | NativeOperations | episode function | task.py exec_command and TOOLS |
| operations.py | method | NativeOperations._delegate | machinery | routing to the api/practical delegate by role: this episode is the hpc role only |
| operations.py | method | NativeOperations._practical_context | machinery | identity wrapper of the context |
| operations.py | method | NativeOperations.initialize | machinery | opens the file-backed PracticalState and re-checks the parent inputs: deleted (job_access service, attempts journal) |
| operations.py | method | NativeOperations._check_parent_inputs | episode function (unplaced) | UNPLACED: re-reads the parent launch's recorded request from runtime_episodes and re-validates its immutable input versions and protein-structure inputs: another Episode's journal rows (README 5 item 14) |
| operations.py | method | NativeOperations.state | machinery | returns the file-backed PracticalState: deleted (see terminal_state.py) |
| operations.py | method | NativeOperations.catalog | episode function | task.py TOOL_DESCRIPTION (the catalogue shown to the model) |
| operations.py | method | NativeOperations.execute | episode function | task.py exec_command |
| received_information.py | class | ReceivedExecutionInformation | episode function (unplaced) | UNPLACED: received_report_* serve the annotation/structural heads receiving protein-structure and file-source returns; not this launch_hpc episode |
| received_information.py | method | ReceivedExecutionInformation.received_report_sources | episode function (unplaced) | UNPLACED: received_report_* serve the annotation/structural heads receiving protein-structure and file-source returns; not this launch_hpc episode |
| received_information.py | method | ReceivedExecutionInformation.received_report_facts | episode function (unplaced) | UNPLACED: received_report_* serve the annotation/structural heads receiving protein-structure and file-source returns; not this launch_hpc episode |
| received_information.py | method | ReceivedExecutionInformation.received_report_closure_facts | episode function (unplaced) | UNPLACED: received_report_* serve the annotation/structural heads receiving protein-structure and file-source returns; not this launch_hpc episode |
| received_record_selection.py | class | NativeReceivedRecordSelection | machinery | received handoff/result selection through the removed record_selection/job_progress_provider and receipts: custody is the system's (records.holds / receipt) |
| received_record_selection.py | method | NativeReceivedRecordSelection._received | machinery | received handoff/result selection through the removed record_selection/job_progress_provider and receipts: custody is the system's (records.holds / receipt) |
| received_reference_custody.py | class | NativeReceivedReferenceCustody | machinery | received reference custody (resolve/validate/admit received forms): the system admits and receipts every pass and return |
| received_reference_custody.py | method | NativeReceivedReferenceCustody.resolve_received_reference | machinery | received reference custody (resolve/validate/admit received forms): the system admits and receipts every pass and return |
| received_reference_custody.py | method | NativeReceivedReferenceCustody.validate_received_report | machinery | received reference custody (resolve/validate/admit received forms): the system admits and receipts every pass and return |
| received_reference_custody.py | method | NativeReceivedReferenceCustody.received_form_references | machinery | received reference custody (resolve/validate/admit received forms): the system admits and receipts every pass and return |
| report_delivery.py | class | NativeReportDelivery | machinery | report finish: runtime_forms save, form_with_facts, workflow.release: deleted (final_to_parent returns the typed result) |
| report_delivery.py | method | NativeReportDelivery.finish | machinery | report finish: runtime_forms save, form_with_facts, workflow.release: deleted (final_to_parent returns the typed result) |
| report_reference_access.py | class | NativeReportReferenceAccess | machinery | reference resolution for the parent-written report form (resolver, runtime tables, job_progress_provider): custody (records.holds) replaces it; the form is the child's own RETURN_FORM |
| report_reference_access.py | method | NativeReportReferenceAccess.resolve | machinery | reference resolution for the parent-written report form (resolver, runtime tables, job_progress_provider): custody (records.holds) replaces it; the form is the child's own RETURN_FORM |
| result_records.py | class | ExecutionResultRecords | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._versions | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._target | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._selector | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._result_directory | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._windows | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._selected_result_action | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._validate_result_body | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._read_result | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._selection | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| result_records.py | method | ExecutionResultRecords._context_target | episode function (unplaced) | UNPLACED: execution result-window acquisition belongs to the results role (execution_result_acquisition), not to launch_hpc |
| retained_protein_reader.py | class | NativeRetainedProteinReader | episode function (unplaced) | UNPLACED: reads retained protein-structure results for the results role / structural head; not used by launch_hpc |
| retained_protein_reader.py | method | NativeRetainedProteinReader.retained_protein_structure_reader | episode function (unplaced) | UNPLACED: reads retained protein-structure results for the results role / structural head; not used by launch_hpc |
| retained_protein_reader.py | method | NativeRetainedProteinReader._protein_reference_access | episode function (unplaced) | UNPLACED: reads retained protein-structure results for the results role / structural head; not used by launch_hpc |
| retained_protein_reader.py | method | NativeRetainedProteinReader._retained_protein_result | episode function (unplaced) | UNPLACED: reads retained protein-structure results for the results role / structural head; not used by launch_hpc |
| task.py | class | NativeTask | machinery | the old decision machine: task.py decide/action/exec_command replace it |
| task.py | method | NativeTask.next | machinery | the old loop (restore, SourceEnd, exchange, report redelivery): decide/action; the system runs the loop |
| task.py | method | NativeTask.apply_response | episode function | task.py action: decode_strict_output and schema validation of the one exec_command, Rejected(rejection_feedback(...)) on failure; the wait/job_child/report_update/reads.map branches do not exist for this episode |
| task.py | method | NativeTask.execute | episode function | task.py exec_command (the tool) and the unit outcome the system journals; runtime_actions saves, receive_outcome, automatic_score_updates and checkpoints are machinery |
| task_state.py | class | NativeTaskState | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.__init__ | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.restore | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.record_effect | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| task_state.py | method | NativeTaskState.checkpoint | machinery | task checkpoint/restore/record_effect (restore_checkpoint, runtime_* rows): deleted; the loop restores outcomes on resume |
| terminal_assignment.py | class | TerminalAssignment | episode function | messages/read_from_parent.py and task.py exec_command |
| terminal_assignment.py | method | TerminalAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment, resource kind hpc) and task.py exec_command (TerminalExecution.validate_action) |
| terminal_assignment.py | method | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_assignment.py | method | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_contracts.py | function | operation_catalog | episode function | task.py TOOL_DESCRIPTION / COMMAND_SCHEMA |
| terminal_credit.py | class | TerminalCredit | episode function | credit.py and messages/internal_summary.py |
| terminal_credit.py | method | TerminalCredit.credit_view | episode function | credit.py credit (project_practical_credit over the summary receipts) |
| terminal_credit.py | method | TerminalCredit.completion_for_action | machinery | completion proof handed to the estimator per action: no way into the controller (README 5 item 5); the proof is messages/internal_summary.py completion_proof |
| terminal_execution.py | class | TerminalExecutionBehavior | machinery | the mix-in class assembled from the terminal_* parts (episode.py HpcJobExecution replaces it) |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function | values: ctx.settings (resource, coordinator_workspace) and assignment inventory_snapshot (task.py _resource_information); the resource validation is TerminalExecution (library) |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() is deleted |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit_kind is deleted |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py action: the one action is the exec_command tool |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator(verify_completion) as estimate_with_context: deleted; yield_estimator.py chooses the completion controller (README 7b) |
| terminal_goal.py | class | TerminalGoal | episode function | task.py INSTRUCTIONS and _launch_instructions |
| terminal_goal.py | method | TerminalGoal.instructions | episode function | task.py INSTRUCTIONS + decide (resource instructions appended) |
| terminal_goal.py | method | TerminalGoal._resource_instructions | episode function | task.py _launch_instructions (LaunchInstructions.for_resource) |
| terminal_operations.py | class | TerminalOperations | episode function | task.py exec_command |
| terminal_operations.py | method | TerminalOperations._operations | episode function | task.py _operations (TerminalExecution over the configured resource) |
| terminal_operations.py | method | TerminalOperations.catalog | episode function | task.py TOOL_DESCRIPTION |
| terminal_operations.py | method | TerminalOperations.execute | episode function | task.py exec_command: validate_action, the transport run through job_access (BLOCKED-ON-JOB-SERVICE), finalize_scientific_command, context transition, assess_validations, the receipt, _publish_receipt (BLOCKED-ON-STORE-ACCESS); state.begin/finish and the saved-receipt return are the attempts journal and the service |
| terminal_report.py | class | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | method | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM: practical_completed, practical_receipt_digests, practical_receipt_refs |
| terminal_report.py | method | TerminalReport.facts | episode function | messages/final_to_parent.py facts (from the receipts of the summary, not from PracticalState or a store publish) |
| terminal_report.py | method | TerminalReport.resolve | machinery | reference resolution for the parent-written form (PracticalReceiptInformation.resolve, receipt digests): custody (records.holds) replaces it |
| terminal_report.py | method | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report (raises validate_form_not_built:structural_homology_evidence at the old validate_form call; then the facts-agreement check) |
| terminal_state.py | class | TerminalState | machinery | the file-backed PracticalState opening per episode (directory, initialize, state): deleted as episode code; its credit/completion are pure functions of the receipts (credit.py, messages/internal_summary.py), its intents/receipts are the attempts journal and the job_access service (BLOCKED-ON-JOB-SERVICE) |
| terminal_state.py | method | TerminalState._state_directory | machinery | the file-backed PracticalState opening per episode (directory, initialize, state): deleted as episode code; its credit/completion are pure functions of the receipts (credit.py, messages/internal_summary.py), its intents/receipts are the attempts journal and the job_access service (BLOCKED-ON-JOB-SERVICE) |
| terminal_state.py | method | TerminalState.initialize | machinery | the file-backed PracticalState opening per episode (directory, initialize, state): deleted as episode code; its credit/completion are pure functions of the receipts (credit.py, messages/internal_summary.py), its intents/receipts are the attempts journal and the job_access service (BLOCKED-ON-JOB-SERVICE) |
| terminal_state.py | method | TerminalState.state | machinery | the file-backed PracticalState opening per episode (directory, initialize, state): deleted as episode code; its credit/completion are pure functions of the receipts (credit.py, messages/internal_summary.py), its intents/receipts are the attempts journal and the job_access service (BLOCKED-ON-JOB-SERVICE) |
| terminal_summary.py | class | TerminalSummary | episode function | task.py decide and _resource_information, _initial_context |
| terminal_summary.py | method | TerminalSummary.initial_decision_context | episode function | task.py _initial_context: execution_initial_information |
| terminal_summary.py | method | TerminalSummary._resource_information | episode function | task.py _resource_information |
| terminal_summary.py | method | TerminalSummary.decision_context | episode function | task.py decide (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion) with the progress from messages/internal_summary.py |
| to_parent.py | class | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM: practical_*, execution_handoff_refs, execution_result_refs, execution_completed, execution_result_origin (the results-role file sources and protein-structure sources are not launch_hpc fields) |
| to_parent.py | method | NativeReport.facts | episode function | messages/final_to_parent.py facts (the closed-credit facts are machinery: credit is completion['credit']) |
| to_parent.py | method | NativeReport._live_facts | episode function | messages/final_to_parent.py facts; the handoff set comes from the receipts of the summary (the removed job_progress_provider handoff reader is not carried); the result/file-source/protein branches belong to the results role |
| to_parent.py | method | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report (validate_form_not_built:structural_homology_evidence); the native_protein_structure_returns.validate_received_report call has no module now (unplaced) |
| waiting.py | class | NativeWaiting | machinery | suspension_changed: wait/suspension machinery: deleted; the episode has no wait |
| waiting.py | method | NativeWaiting.suspension_changed | machinery | suspension_changed: wait/suspension machinery: deleted; the episode has no wait |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py _request_yield_class (copied unchanged) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, same error code) |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController; private_yield_binding flag deleted) |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (PracticalYieldEstimator estimate_with_context deleted, README 7b) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator delegate: deleted (README 7b) |
