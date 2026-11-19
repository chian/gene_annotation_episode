# a101/sequence_homology_evidence/execution_job_submission/hpc_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/hpc_job_execution/<file>`
(files directly in this folder; `tests/` not covered). Old binding class `ExecutionEpisode` (`binding_path =
'sequence_homology_evidence/execution_job_submission/hpc_job_execution'`, `commissioning_parent =
'sequence_homology_evidence/execution_job_submission'`, `roles = ('launch_hpc',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `OperationalTask`. A leaf.

## What it is for (its goal, in its own words)

`goal.py` returns the delegate `TerminalExecutionBehavior.instructions` (`terminal_execution.py`):

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
> run directory for supplied-input and transport work ... For coordinator-side transfers,
> execution_resource.ssh_argv, when present, is the exact configured transport prefix ... The episode iterator
> decides continuation from credit; add no stopping budget.

followed by "Resource instructions supplied from the frozen library:" and the sections that the launch
instruction library selects for this resource. For A101 this runs a native BLAST/HMMER (or other requested job)
on Aurora via PBS over the configured SSH route.

## Task and instructions

`task_instructions.py` identical to the Launch parent's (the goal replaces the generic prompt). `task.py`: the
Launch loop **without reasoning and without wait** — every action is a tool execution; credit is always the
current credit view (no wait carry-over). `task_decision.py`, `task_state.py`, `report_delivery.py`,
`decision_state.py` are the Launch parent's rules (separate copies). `waiting.py` keeps only
`suspension_changed`.

## What it reads from its parent's assignment

`from_parent.py`: one practical request (`ASSIGNMENT_SCHEMA`, `practical_assignment_v1`) for one configured HPC
resource (`resource_kind` const `hpc`, `resource_id` const, `requested_job` generic or native alternatives,
`workspace` confined to the resource workspace, endpoint `usable_handoff` / `completed_job_outputs`,
`initial_context`). The terminal behaviour additionally validates it against its resource operations.
`prepare_assignment`: request validation, kind must be `hpc`, parent role must be `launch`, re-reads the parent
Launch assignment, masking/utility inputs, the parent's immutable input versions, native and standard BLAST
database job inputs. Unlike the API sibling it does **not** apply the BLAST graded-selection check.
`initial_references` = none.

## Children it may commission

None.

## Decision state and what it shows the model

Same presentation shell as Launch. `decision_context` is the terminal behaviour's: `execution_assignment`,
`execution_resource` (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory
snapshot), `coordinator_workspace`, `execution_progress` (practical state credit view), `execution_completion`
(completion proof or null). `initial_decision_context` = resource capabilities, initial information, received
BV-BRC/MinHash values. `decision_inputs.py`: as Launch without `waiting_support`.

## Tools it offers

`permitted_common_actions = ('tool',)`. Catalog = `exec_command` (cmd string or argv, required `workdir` and
`env`, optional `target` resource|coordinator). Each command begins/finishes a `PracticalState` intent keyed by the
operation key (a completed intent is replayed, not re-run), finalizes scientific command artifacts, tracks cwd and
environment revisions, assesses endpoint validations, and publishes a practical receipt record
(`PracticalReceiptInformation`). Argument errors return `invalid`; execution exceptions become a failed native
outcome that still enters the iterator.

## How its credit is counted

`credit.py`: kind `operational`; same closed-credit snapshot rules (role `launch_hpc`). Live credit:
`self._delegate(context).credit_view(...)` = the practical state's credit view (operational progress from
validated endpoint predicates). Completion: terminal `completion_for_action` (the state's completion proof for that
operation key); verification: `self.state(context).verify_completion(proof)`.

## Continuation (yield estimator and settings)

`yield_estimator.py` (requires `require_private_yield`): **accumulation** estimator with cutoff and parameters from
the task profile `launch_hpc:<request class>` (class = `practical_hpc_<native_* names>_{handoff|outputs}`), and
`estimate_with_context = PracticalYieldEstimator(state.verify_completion)` via the terminal delegate.

## What it reports to its parent

`to_parent.py`: no required return sources. Facts: the terminal delegate's `practical_completed`,
`practical_receipt_digests`, `practical_receipt_refs`, plus `execution_handoff_refs` = received usable handoffs
extended by every practical receipt reference that reads back as a returnable handoff target,
`execution_completed` = `practical_completed`, result refs, file sources/outcomes, appservice support refs, and
the closed credit snapshot. `validate_report` (terminal) requires fact fields to equal the recorded facts.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 9 | Goal = terminal execution instructions + frozen resource sections. | none (delegate reads `services.workflow.launch_instructions`). |
| task_instructions.py | 26 | Same inlined prompt copy as Launch. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`. |
| configuration.py | 119 | Same configuration as Launch (separate copy). | as Launch. |
| binding_record.py | 8 | `as_record()` (binding_id differs). | none. |
| execution_contracts.py | 59 | Same contracts; imports `hpc_job_execution.terminal_execution`. | as Launch. |
| from_parent.py | 111 | One HPC practical request; parent must be `launch`. | native database publication validators; `hpc_launch_authentication` guarded off. |
| from_parent_launch.py | 9 | Parent Launch form schema. | none. |
| execution_state.py | 89 | Delegate = TerminalExecutionBehavior for the resource; parent input re-check. | `self.store.db` on `runtime_episodes`, `runtime_actions`, `runtime_receipt_inheritance`×2; `self.services.record_selection`; `episode_receipts`. |
| execution_operations.py | 174 | Catalog/execute delegated to the terminal behaviour. | as API sibling. |
| terminal_execution.py | 242 | exec_command behaviour, instructions, decision context, facts, credit (the substantive HPC intent). | imports `acquisition`, `communication`, `domain`, `practical_execution_operations/records/state`, `practical_receipt_information`×3, `practical_yield`, `terminal_execution`, `terminal_scientific_evidence`×2; `services.workflow.launch_instructions.for_resource`. |
| native_input_custody.py | 313 | Same input custody. | as Launch. |
| received_evidence.py | 351 | Same received-evidence rules. | as Launch. |
| result_acquisition.py | 209 | Same result acquisition. | `self.store.db` on `runtime_actions`×2, `runtime_episodes`. |
| internal_summary.py | 25 | Terminal decision context; no selected execution task. | none. |
| decision_inputs.py | 76 | Per-call inputs without waiting_support. | as Launch minus `.waiting_support`. |
| decision_state.py | 55 | Same presentation. | as Launch. |
| task.py | 214 | Tool-only loop. | as API sibling minus `.perform_selected_wait`/`.last_observed_credit`. |
| task_decision.py | 294 | Model-call/exchange rules. | as Launch. |
| task_state.py | 115 | Per-episode state. | as Launch. |
| waiting.py | 9 | Only suspension registration. | `self.workflow.execution_handle`×2, `.execution_backend`. |
| report_delivery.py | 34 | Final form fill. | as Launch (`runtime_forms`×2). |
| credit.py | 260 | Practical-state credit and verification. | as API sibling (`runtime_*` tables via `self.store.db`, `episode_receipts`, `episode_return_records`, `method_loop.identities`, `numerical.NumericBand`, `practical_yield`). |
| yield_estimator.py | 58 | Accumulation + practical forecast, key `launch_hpc:<class>`. | imports `numerical.YieldController, YieldParameters`, `practical_yield.PracticalYieldEstimator`. |
| to_parent.py | 296 | Practical facts and receipt-derived handoffs. | as Launch. |
| episode.py | 52 | Identity, no children, `('tool',)`, `context_hook_applies` only for `launch_hpc`. | old registry declarations (`binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `decision_source_type`, `_private_practical_estimator_owner`). |

## Differences from similar episodes

- vs `api_job_execution`: tool-only (no wait), goal from the terminal behaviour, credit/verification from the
  practical state, handoffs also derived from practical receipts, no BLAST selection check against the parent,
  no `blast_request_custody.py`, no waiting_support input, `decision_context` without selected execution task.
- vs Launch parent: one practical request, no children, no reason/wait, accumulation estimator.
- The `local_job_execution` sibling (not covered here) is the local-resource counterpart of this episode.

## Carried over

Every old function, class and method of this episode at 97308b94c (`runs/carry_over/functions/a101__sequence_homology_evidence__execution_job_submission__hpc_job_execution.tsv`, 186 rows), and where it is now. `machinery` is old-runner machinery and is not carried; `episode function` is placed in the file named, or is a library function the episode calls; `episode function (not placed)` could not be placed and is reported with its reason in `carry_over_blocked/a101__sequence_homology_evidence__execution_job_submission__hpc_job_execution.md`. Rows marked "library candidate" stay in the episode file until they move to `episode_support/`. The old files of this folder that are not binding files (grading, scoring, readers, records, contracts) are already in the library under the same names and are called from there (practical_execution_records, practical_execution_credit, terminal_execution, terminal_scientific_evidence, launch_instructions, tool_knowledge, strict_output, rejection_feedback, presentation, progress_views, the result-view fact sources).

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | binding record / the binding's own as_record(): deleted (README 3e); the system records the binding |
| binding_record.py | OperationalBindingRecord.as_record | machinery | binding record / the binding's own as_record(): deleted (README 3e); the system records the binding |
| configuration.py | OperationalConfiguration | episode function | task.py: the configured resource, initial_information, coordinator_workspace and launch/knowledge library directories are read from ctx.settings; yield_estimator.py: task_yield_profiles. The old provider wiring of the constructor (api_execution, job_progress_provider, local_file_sources, native result readers, tool_registry, flux/fluorescence/nmf/atac/chromatin result and return objects) is not carried: old-runner provider machinery for the results and api roles |
| configuration.py | OperationalConfiguration.__init__ | episode function | task.py: the configured resource, initial_information, coordinator_workspace and launch/knowledge library directories are read from ctx.settings; yield_estimator.py: task_yield_profiles. The old provider wiring of the constructor (api_execution, job_progress_provider, local_file_sources, native result readers, tool_registry, flux/fluorescence/nmf/atac/chromatin result and return objects) is not carried: old-runner provider machinery for the results and api roles |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit (the practical requirement credit) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit kind label 'operational': the system derives the credit's kind from the controller; nothing to carry |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, runtime_record_receipts): the system hands the credit its controller last saw to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, runtime_record_receipts): the system hands the credit its controller last saw to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, runtime_record_receipts): the system hands the credit its controller last saw to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, runtime_record_receipts): the system hands the credit its controller last saw to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit view frozen at closure and re-checked against the old journal/receipt tables (runtime_episodes, runtime_forms, runtime_observations, runtime_record_receipts): the system hands the credit its controller last saw to final_to_parent |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (the live branch; the closed branch is machinery) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit: the practical branch (library project_practical_credit); the native masking/utility/database/hmmer/blast results branches belong to the results role and are not placed |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._proof_for_action | episode function (not placed) | completion proof of a results acquisition, read from the old runtime_actions rows and result records (results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | episode function | messages/internal_summary.py completion_proof (library candidate): the practical completion proof over the saved receipts |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | verdict re-read from the old runtime_observations of a closed episode: old journal re-validation |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | verification of a completion proof for PracticalYieldEstimator: replaced by the completion controller toward the credit target (yield_estimator.py, README 7b); the proof itself is internal_summary.completion_proof |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py decide (the per-call model inputs) |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py decide: launch_instruction_library and selected_launch_instructions are carried; resource_context, shared_information_context, child_options, literature completed work and the annotation credit context belong to the old shared loop and are not carried |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers): old-runner machinery |
| decision_state.py | OperationalDecisionState | machinery | presentation shell of the old annotation iterator over the runner tables (working_state, journal.db visual evidence, report forms, annotation axis credit): the episode shows its own context in task.py decide |
| decision_state.py | OperationalDecisionState.decision_state | machinery | presentation shell of the old annotation iterator over the runner tables (working_state, journal.db visual evidence, report forms, annotation axis credit): the episode shows its own context in task.py decide |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers): old-runner machinery |
| episode.py | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py selection_schema: only exec_command is offered; no reason, wait or child |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | old registry hook (roles = launch_hpc): the binding path now names the episode |
| execution_contracts.py | launch_operation_catalog | episode function (not placed) | execution.capabilities is an operation of the parent role launch, not of launch_hpc |
| execution_contracts.py | native_result_operation_catalog | episode function (not placed) | execution.results.* are operations of the results role (execution_result_acquisition), not of launch_hpc |
| execution_contracts.py | _outcome | episode function (not placed) | outcome shape of the execution.results.* operations (results role), not of launch_hpc |
| execution_operations.py | OperationalOperations | episode function | task.py: operation_catalog, resource_information, exec_command |
| execution_operations.py | OperationalOperations._resource_information | episode function | task.py resource_information |
| execution_operations.py | OperationalOperations.capabilities | episode function (not placed) | capabilities of every configured resource (all kinds, API operations): parent role launch; this episode shows its one configured resource |
| execution_operations.py | OperationalOperations.resource_tool_contracts | episode function (not placed) | commissionable launch/results operation contracts of every resource, for the parent roles (launch, results): not this episode's tools |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py operation_catalog (the one tool exec_command) |
| execution_operations.py | OperationalOperations.execute | episode function | task.py exec_command (and run_command, blocked on the job_access service) |
| execution_operations.py | OperationalOperations._has_appservice | episode function (not placed) | api_execution test for BV-BRC appservice sources: this binding has no api execution |
| execution_operations.py | OperationalOperations._has_uniprot | episode function (not placed) | api_execution test for UniProt return sources: this binding has no api execution |
| execution_operations.py | OperationalOperations._appservice_sources | episode function (not placed) | BV-BRC appservice fact sources of the api role: not a fact source of launch_hpc |
| execution_state.py | OperationalExecutionState | episode function | task.py terminal(settings) and messages/internal_summary.py (the practical state as a pure function of the view) |
| execution_state.py | OperationalExecutionState._delegate | episode function | task.py terminal(settings): the one configured resource |
| execution_state.py | OperationalExecutionState._practical_context | machinery | identity function on the old binding context |
| execution_state.py | OperationalExecutionState.initialize | machinery | initialisation of the file-backed PracticalState under the run directory: the saved receipts are the unit outcomes of the view |
| execution_state.py | OperationalExecutionState._check_parent_inputs | episode function (not placed) | re-read the parent launch's recorded request from runtime_episodes and re-validated masking/utility inputs, immutable input versions and BLAST database job inputs before every command: the child cannot read its parent's assignment (README 5 item 14) |
| execution_state.py | OperationalExecutionState.state | machinery | accessor of the file-backed PracticalState: replaced by messages/internal_summary.py |
| execution_state.py | OperationalExecutionState._target | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| execution_state.py | OperationalExecutionState._selection | machinery | receiver record selection read from runtime_receipt_inheritance / runtime_actions: receipts bookkeeping |
| execution_state.py | OperationalExecutionState._context_target | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | OperationalAssignment.child_assignment_schema | episode function (not placed) | choice among the parent launch's frozen HPC requests: the child cannot read its parent's assignment (README 5 item 14); the parent copies the chosen request into this child's assignment |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._permitted | episode function (not placed) | filter of the parent's frozen requests by the parent's launch constraints: reads the parent's own assignment |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py decide (the resource's own validate_assignment); the parent-assignment reads (parent launch, masking/utility inputs, immutable versions, BLAST database job inputs) are not carried |
| from_parent.py | OperationalAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (resource_kind fixed to hpc) |
| from_parent.py | OperationalAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (library validate_assignment) and task.py decide (TerminalExecution.validate_assignment for the configured resource; workspace confinement) |
| from_parent.py | OperationalAssignment._launch | episode function (not placed) | validation of the parent launch's execution_launch_assignment_v1: the child cannot read its parent's assignment |
| from_parent.py | OperationalAssignment._constraints | episode function (not placed) | validation of the parent launch's allowed_resource_ids / allowed_kinds constraints: reads the parent's assignment |
| from_parent.py | OperationalAssignment.initial_references | machinery | initial record references of the old request (always an empty list for this role): custody names the records a commission passes |
| from_parent_launch.py | LaunchParentAssignment | episode function (not placed) | schema of the parent launch assignment (execution_launch_assignment_v1): the child cannot read its parent's assignment (README 5 item 14) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | episode function (not placed) | schema of the parent launch assignment (execution_launch_assignment_v1): the child cannot read its parent's assignment (README 5 item 14) |
| goal.py | OperationalGoal | episode function | goal.py GOAL and task.py INSTRUCTIONS / instructions (the terminal goal text, then the resource sections of the frozen launch library) |
| goal.py | OperationalGoal.instructions | episode function | goal.py GOAL and task.py INSTRUCTIONS / instructions (the terminal goal text, then the resource sections of the frozen launch library) |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | task.py decide: the resource information and its inventory snapshot are shown at every decision; resource capabilities of other resources and the received BV-BRC and MinHash values (api_execution reads of old receipts) are not carried |
| internal_summary.py | OperationalSummary._with_selected_execution_task | episode function (not placed) | returned its input unchanged for this role |
| internal_summary.py | OperationalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, progress, completion proof, last command) and task.py decide |
| native_input_custody.py | NativeInputCustody | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._masking_selector | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._masking_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._retained_masking_target | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._masking_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._utility_selector | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._utility_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._retained_utility_target | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._utility_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._versions | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._selector | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._protein_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._atac_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._atac_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables |
| received_evidence.py | ReceivedOperationalEvidence | machinery | receipts bookkeeping and report_form machinery of received evidence: custody and the typed return replace it |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | receipts bookkeeping: the known records of the binding context from the old receipt tables |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | receipts bookkeeping and report_form sources of received reports |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | receipts bookkeeping: facts of received reports |
| received_evidence.py | ReceivedOperationalEvidence.received_report_closure_facts | machinery | receipts bookkeeping: closure facts of received reports |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | report-reference resolution against the old receipts: custody (records.holds) replaces it |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | episode function (not placed) | validation of received BLAST/HMMER/api reports of a head or results role: not applicable to launch_hpc, which receives no reports |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | report_form reference machinery |
| report_delivery.py | OperationalReportDelivery | machinery | report_form machinery: filling and delivering the parent-written report form (runtime_forms); the system admits the result against RETURN_FORM |
| report_delivery.py | OperationalReportDelivery.finish | machinery | report_form machinery: filling and delivering the parent-written report form (runtime_forms); the system admits the result against RETURN_FORM |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | report_form machinery: filling and delivering the parent-written report form (runtime_forms); the system admits the result against RETURN_FORM |
| result_acquisition.py | OperationalResultAcquisition | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._result_directory | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._windows | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._selected_result_action | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._execute_native_results | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._publish_result | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._validate_result_body | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._read_result | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._generic_result_selector_progress | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| result_acquisition.py | OperationalResultAcquisition._native_results_complete | episode function (not placed) | results-role / native retained-input custody: this launch_hpc episode receives no result, handoff or retained input records and acquires no results; it read the parent assignment, the old Store or the old runtime tables (results role helper kept in this old copy) |
| task.py | OperationalTask | episode function | task.py decide, action and exec_command |
| task.py | OperationalTask.instructions | episode function | task.py instructions |
| task.py | OperationalTask.next | episode function | task.py decide: the model request; the old reason/wait/report-update paths are not carried |
| task.py | OperationalTask.apply_response | episode function | task.py action: the one tool action, rejected as Rejected when invalid; the report_update, redelivery and feedback bookkeeping are machinery |
| task.py | OperationalTask.execute | episode function | task.py exec_command: the journal/measure bookkeeping, receipts and checkpoint are machinery |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers): old-runner machinery |
| task_decision.py | OperationalTaskDecision | episode function | task.py decide / action (the model exchange) |
| task_decision.py | OperationalTaskDecision.call | episode function | task.py decide: ModelRequest of role REASONING over the strict-output generation schema |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | model conversation key of the old decision exchange: the system journals model calls |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | context of the parent-written report-update form: report_form machinery |
| task_decision.py | OperationalTaskDecision.exchange_schema | episode function | task.py selection_schema / generation_schema |
| task_decision.py | OperationalTaskDecision.exchange_response | episode function | task.py decode_response (strict output) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop (exchange_decision) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop (exchange_decision) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | decision-exchange loop: information gathering is tool calls |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers): old-runner machinery |
| task_instructions.py | instructions | episode function | task.py instructions (the goal text, resource sections, tool-knowledge and launch-library paragraphs; the reasoning-commit, pending-child, wait, native-event and decision-exchange paragraphs describe actions this episode never had or no longer has) |
| task_state.py | OperationalTaskState | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.__init__ | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.restore | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.record_effect | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | OperationalTaskState.checkpoint | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| task_state.py | _bind_original_task_runtime_providers | machinery | per-episode loop state, execution failure record, record_effect, checkpoint/restore of the old runner (journal tables): the system journals units and resumes; a failed command is a returned failed outcome in task.py exec_command |
| terminal_execution.py | operation_catalog | episode function | task.py operation_catalog |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py (terminal, resource_information, instructions, operation_catalog, exec_command), messages/internal_summary.py, messages/final_to_parent.py |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | task.py: resources and initial_information are read from ctx.settings; the explicit-resource checks are the library TerminalExecution constructor |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py terminal(settings): the library TerminalExecution |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | task.py decide: validate_assignment and the resource/kind match |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | file-backed practical state directory under the run directory: the saved receipts are artifacts held by custody |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | initialisation of the file-backed PracticalState |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | accessor of the file-backed PracticalState |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() (README 3e) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit kind label 'operational' |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py selection_schema: the tool action only |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent and task.py decide |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide: the inventory snapshot of execution_resource |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | task.py resource_information |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | task.py decide: LaunchInstructions.for_resource of the configured resource |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | task.py INSTRUCTIONS and instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | task.py decide (resource, coordinator workspace) over messages/internal_summary.py (progress, completion) |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | task.py operation_catalog |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | task.py exec_command (library finalize_scientific_command, assess_validations, validate_receipt); the intent/finish ledger of PracticalState is the system attempts journal; the receipt record is one artifact via ctx.store.artifact; the command itself is blocked on the job_access service |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | messages/internal_summary.py completion_proof (library candidate) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator(verify_completion): replaced by the completion controller (yield_estimator.py, README 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py facts |
| terminal_execution.py | TerminalExecutionBehavior.resolve | machinery | resolution of report references against the old receipts: custody (records.holds) replaces it |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (the fact-agreement check; the validate_form step has no parent-written schema left) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py RETURN_FORM, facts, final_to_parent |
| to_parent.py | OperationalReport.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM: no required return source beyond credit and finding |
| to_parent.py | OperationalReport._forwards_bvbrc_reports | episode function (not placed) | api_execution test for forwarding BV-BRC reports of an annotation/head role: this binding has no api execution |
| to_parent.py | OperationalReport._forwards_minhash_reports | episode function (not placed) | api_execution test for forwarding MinHash reports of an annotation/head role: this binding has no api execution |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM: the practical, handoff, result, completed, origin and native-family fact sources by their old names; the masking and utility families (dotted names), the uniprot and BV-BRC appservice / MinHash sources and the BLAST database grader return source are not declared (see the blocked file) |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py facts |
| to_parent.py | OperationalReport._live_facts | episode function | messages/final_to_parent.py facts: the practical branch; the per-family results branches (native_blast_*_results.applies) belong to the results role: all families are empty here; the closed-credit capture is machinery |
| to_parent.py | OperationalReport.resolve | machinery | resolution of report references against the old receipts and result readers: custody (the returned records are held) replaces it |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement); the received masking/utility/uniprot report validations are results-role |
| waiting.py | OperationalTaskWaiting | machinery | suspension/wait registration (execution_handle, execution_backend): wait/suspension machinery |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | suspension/wait registration (execution_handle, execution_backend): wait/suspension machinery |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (task_yield_class of the parent input; the api versions it classified are the api sibling's) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, same error) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller: CompletionYieldController toward parent_input completion_target |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator(verify_completion): replaced by the completion controller |
| yield_estimator.py | ExecutionEpisodeYield._private_practical_estimator | machinery | PracticalYieldEstimator(verify_completion): replaced by the completion controller |
