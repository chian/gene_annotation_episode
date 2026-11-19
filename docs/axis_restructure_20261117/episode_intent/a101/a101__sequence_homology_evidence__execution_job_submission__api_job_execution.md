# a101/sequence_homology_evidence/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/api_job_execution/<file>`
(files directly in this folder; `tests/` not covered). Old binding class `ExecutionEpisode` (`binding_path =
'sequence_homology_evidence/execution_job_submission/api_job_execution'`, `commissioning_parent =
'sequence_homology_evidence/execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `OperationalTask`. A leaf: it commissions no children.

## What it is for (its goal, in its own words)

`goal.py` (the service name comes from the validated assignment):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or
> repair from the actual available operations and received outcomes. Distinguish an immediate returned response
> from a service job that continues remotely. Preserve the actual request or job identity and submission
> uncertainty; a missing reply does not establish that no job was created. Establish the requested usable
> monitoring/results handoff from recorded service facts. The configured controller governs continuation;
> verified original handoff completion gives exact zero future credit.

For A101 this is where an NCBI BLAST (or EBI HMMER, BV-BRC, UniProt ...) request is submitted once and a usable
RID/job handoff is established for later monitor/results episodes.

## Task and instructions

`task_instructions.py` is identical to the Launch parent's (inlined INSTRUCTIONS copy, same composition rules);
with `replaces_default_instructions` the goal text above replaces the generic prompt. `task.py`: the Launch loop
**without the reasoning path** (every selection is validated against the action schema; no `reason` execution);
`wait` and tool execution remain. `task_decision.py`, `task_state.py`, `report_delivery.py`, `decision_state.py`
are the Launch parent's rules (separate copies).

## What it reads from its parent's assignment

`from_parent.py`: the assignment is exactly one request for one configured API resource (`anyOf` the API
resources' request schemas with `resource_id` const and required). `prepare_assignment`:
- validates through the API service (`api_execution.validate_assignment(..., scope)`), and that the resource kind
  is `api`;
- requires the commissioning parent role `launch` and re-reads the parent's Launch assignment;
- for a BLAST graded request in the parent, `_validate_blast_launch_selection`: the selected resource must be a
  permitted request of the parent; service must be `ncbi_blast`; the prepared query's sequence digest must equal
  the parent's `query_subject_ref` sequence; a parent-stated database must be kept;
- masking/utility input references, the parent's immutable input versions, native and standard BLAST database
  job inputs.
`initial_references` = none. On `initialize`, `_check_parent_inputs` re-reads the parent Launch request from
`runtime_episodes` and repeats the input checks, and `_validate_blast_api_parent_request` (own
`blast_request_custody.py`) binds the selected BLAST search to the parent's query digest and database.

## Children it may commission

None (`child_roles` and `allowed_children` return `()`).

## Decision state and what it shows the model

Same presentation as the Launch parent (incl. `job_episode_options`). `internal_summary.py`:
`initial_decision_context` = resource capabilities, initial information, received BV-BRC values and MinHash
values (no received_blast_jobs block — that branch is `pass` here). `decision_context` = `execution_assignment`,
`execution_progress` (its facts), plus `api_execution.decision_context(context, view)` when the service provides
one, plus `selected_execution_task` for an `ebi_hmmer` request (from the single request). `decision_inputs.py`:
as the Launch parent, including `waiting_support`.

## Tools it offers

`permitted_common_actions` = `('tool', 'wait')` for an `api_service_assignment_v1` request, else `('tool',)`.
Catalog and execution are delegated to the API service execution (`_delegate` → `self.api_execution`;
`api_execution.catalog(context)` / `.execute(...)`), i.e. the configured service's prepare/submit/status/result
operations. The non-API catalog branches (native database/HMMER/BLAST result catalogs) remain in the copy but are
not reached for the `launch_api` role.

## How its credit is counted

`credit.py`: kind `operational`; the same closed-credit snapshot rules as the Launch parent (role `launch_api`).
Live credit: native result readers if they apply, otherwise `api_execution.credit_view(context,
receiver_selection)` (the service's handoff/acquired-record credit with the configured `handoff_unit` and
`acquired_record_unit`). Completion: delegated to `api_execution.completion_for_action`; verification to
`api_execution.verify_completion(context, proof)` (after the closed-history verdict).

## Continuation (yield estimator and settings)

`yield_estimator.py` (requires `require_private_yield`): **accumulation** estimator
(`YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters))`) with
`estimate_with_context=PracticalYieldEstimator(verify_completion)` (a verified completion proof forecasts exact
zero). Profile key `launch_api:<request class>` from `task_yield_profiles`; request class =
`api_<service>[_<algorithm>][_<database>]_handoff` for `api_execution_assignment_v1` / `api_service_assignment_v1`,
else `compact_<version>`.

## What it reports to its parent

`to_parent.py`: no required return sources (the Launch parent's `execution_handoff_refs` requirement is `pass`
here). Fact sources: the Launch parent's set. Facts: `api_execution.facts(context, completion_snapshot)` over empty
native defaults, with `execution_result_origin = None`, plus the closed credit snapshot.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 11 | Service-specific execution goal text. | none. |
| task_instructions.py | 26 | Same inlined prompt copy as Launch. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`. |
| configuration.py | 119 | Same configuration as Launch (separate copy). | as Launch: `numerical`, `api_service_execution`, `execution_progress`, `retained_input_authority` readers. |
| binding_record.py | 8 | `as_record()` (binding_id differs). | none. |
| execution_contracts.py | 59 | Same contracts; imports `api_job_execution.terminal_execution`. | as Launch. |
| from_parent.py | 112 | One API request; parent role must be `launch`; BLAST selection check against parent. | `hpc_launch_authentication` (guarded off by `and False`), native database publication validators. |
| from_parent_launch.py | 9 | Parent Launch form schema (for re-reading the parent). | none. |
| blast_request_custody.py | 61 | Launch's BLAST custody plus `_validate_blast_api_parent_request` (query digest, database, service). | `self.tool_registry._check_sequence_operand/_sequence`, `api_execution.services[...].prepare('api.blast.prepare')`. |
| execution_state.py | 89 | Delegate = api_execution; parent input re-check; BLAST parent request check on initialize. | `self.store.db` on `runtime_episodes`, `runtime_actions`, `runtime_receipt_inheritance`×2; `self.services.record_selection`; `episode_receipts`. |
| execution_operations.py | 174 | Catalog/execute delegated to the API service. | as Launch plus native result catalog imports. |
| native_input_custody.py | 313 | Same input custody as Launch. | as Launch. |
| received_evidence.py | 351 | Same received-evidence rules. | as Launch. |
| result_acquisition.py | 209 | Same result acquisition. | `self.store.db` on `runtime_actions`×2, `runtime_episodes`. |
| terminal_execution.py | 242 | Same TerminalExecutionBehavior copy (unused for api role). | as Launch. |
| internal_summary.py | 55 | API decision context hook; no BLAST job summaries. | `self.services.scientific_parent_task`; `library.native_profile_presentation`. |
| decision_inputs.py | 78 | Per-call inputs incl. waiting_support. | as Launch. |
| decision_state.py | 55 | Same presentation. | as Launch. |
| task.py | 220 | Loop without reasoning. | as Launch minus `.reasoning_action_schema`, `.specialist`, `store.commit_reasoning`. |
| task_decision.py | 294 | Model-call/exchange rules. | as Launch. |
| task_state.py | 115 | Per-episode state. | as Launch. |
| waiting.py | 31 | Selected wait and suspension. | `self.workflow.perform_selected_wait`, `.execution_handle`×2, `.execution_backend`. |
| report_delivery.py | 34 | Final form fill. | as Launch (`runtime_forms`×2). |
| credit.py | 260 | API credit view / completion / verification delegated to the service. | `self.store.db` on `runtime_episodes`×2, `runtime_observations`×2, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2, `runtime_forms`×3, `runtime_actions`×2; `episode_receipts`, `episode_return_records`, `method_loop.identities`, `numerical.NumericBand`, `practical_yield`. |
| yield_estimator.py | 58 | Accumulation + practical completion forecast, key `launch_api:<class>`. | imports `numerical.YieldController, YieldParameters`, `practical_yield.PracticalYieldEstimator`×3. |
| to_parent.py | 284 | Facts from the API service. | as Launch (`library.*` views, `episode_bindings`). |
| episode.py | 56 | Identity, no children, actions (`tool`, `wait` for service assignments), `context_hook_applies` only for `launch_api`. | old registry declarations (`binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `decision_source_type`, `_private_practical_estimator_owner`). |

## Differences from similar episodes

- vs Launch parent: one request instead of a request map; no children; no `reason`; accumulation (not bounded)
  estimator; credit/facts/catalog delegated to the API service; no required return; parent must be `launch`.
- vs `hpc_job_execution`: keeps `wait` (for service assignments) and its waiting/decision `waiting_support`
  inputs, validates the BLAST selection against the parent (HPC does not), delegates to `api_execution` instead of
  a TerminalExecutionBehavior, own goal text instead of the terminal instructions, own `blast_request_custody.py`.

## Carried over

Carried over on 19 November 2026 from `97308b94c` as a private binding: goal.py, task.py, credit.py, yield_estimator.py, episode.py, messages/read_from_parent.py, internal_summary.py, final_to_parent.py (no children, so no msg_to_child.py or read_from_child.py). Nothing is imported from another episode; the library functions called are `launch_instructions`, `tool_knowledge`, `rejection_feedback`, `time_accounting`, `failure_outcome` and the A101 fact-source functions of the result views. The shape follows the finished private carry of the A102 sibling (same old function list). The service work is BLOCKED-ON-JOB-SERVICE (see `carry_over_blocked/a101__sequence_homology_evidence__execution_job_submission__api_job_execution.md`). `configuration.py` keeps only `build_api_service`, still imported by `execution_result_acquisition/acquisition_source.py`.

Kind "episode function (not reached by the API role)" rows are listed as unplaced in the blocked file.

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | machinery: the binding's own as_record(); the system records the binding |
| binding_record.py | OperationalBindingRecord.as_record | machinery | machinery: the binding's own as_record(); the system records the binding |
| blast_request_custody.py | BlastRequestCustody | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (BLAST query digest and database against the parent request: also needs the old tool registry sequence reads and `api_execution.services[...].prepare`) |
| blast_request_custody.py | BlastRequestCustody._blast_launch_requirement | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (BLAST query digest and database against the parent request: also needs the old tool registry sequence reads and `api_execution.services[...].prepare`) |
| blast_request_custody.py | BlastRequestCustody._validate_blast_launch_selection | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (BLAST query digest and database against the parent request: also needs the old tool registry sequence reads and `api_execution.services[...].prepare`) |
| blast_request_custody.py | BlastRequestCustody._validate_blast_api_parent_request | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (BLAST query digest and database against the parent request: also needs the old tool registry sequence reads and `api_execution.services[...].prepare`) |
| configuration.py | OperationalConfiguration | episode function | task.py reads `ctx.settings` (resources, initial_information, handoff_unit, acquired_record_unit; the controller profiles in yield_estimator.py); the APIServiceExecution it built is the `job_access` service (BLOCKED-ON-JOB-SERVICE); log_window_bytes/log_roles/results_yield_profiles served the monitor and results roles, not carried |
| configuration.py | OperationalConfiguration.__init__ | episode function | task.py reads `ctx.settings` (resources, initial_information, handoff_unit, acquired_record_unit; the controller profiles in yield_estimator.py); the APIServiceExecution it built is the `job_access` service (BLOCKED-ON-JOB-SERVICE); log_window_bytes/log_roles/results_yield_profiles served the monitor and results roles, not carried |
| credit.py | ExecutionEpisodeCredit | machinery | machinery: credit_kind deleted (README 3d); one episode, one credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | machinery: credit_kind deleted (README 3d); one episode, one credit |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (API branch: the service executor's credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (API branch: the service executor's credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (API branch: the service executor's credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit._proof_for_action | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller's target is the commission's completion_target, the verified flag rides in the outcome (`completed`) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller's target is the commission's completion_target, the verified flag rides in the outcome (`completed`) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller's target is the commission's completion_target, the verified flag rides in the outcome (`completed`) |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller's target is the commission's completion_target, the verified flag rides in the outcome (`completed`) |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py decide (launch_instruction_library, selected_launch_instructions, tool_knowledge, waiting text); pending_work, completed_action_reports, execution_expectations, native_event_targets, waiting_support, child_options were old-runner/other-role context and are not carried |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py decide (launch_instruction_library, selected_launch_instructions, tool_knowledge, waiting text); pending_work, completed_action_reports, execution_expectations, native_event_targets, waiting_support, child_options were old-runner/other-role context and are not carried |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| decision_state.py | OperationalDecisionState | episode function | messages/internal_summary.py and task.py decide (current credit, controller state, report_update); old working_state/visible refs/report deliveries/pending work are old-runner machinery |
| decision_state.py | OperationalDecisionState.decision_state | episode function | messages/internal_summary.py and task.py decide (current credit, controller state, report_update); old working_state/visible refs/report deliveries/pending work are old-runner machinery |
| decision_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| episode.py | ExecutionEpisode | episode function | episode.py ApiJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py wait_permitted / offered_actions |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | machinery: old registry hook (`context_hook_applies`) |
| execution_contracts.py | launch_operation_catalog | episode function | task.py catalog_of (the service's operation catalog; BLOCKED-ON-JOB-SERVICE job_access api_catalog) |
| execution_contracts.py | native_result_operation_catalog | episode function (not reached by the API role) | unplaced: results role catalog; carried by execution_result_acquisition |
| execution_contracts.py | _outcome | episode function | task.py service_operation failure outcome (`failure_outcome`, already in library: episode_support/tools/unit_outcomes.py) |
| execution_operations.py | OperationalOperations | episode function | task.py tools |
| execution_operations.py | OperationalOperations._resource_information | episode function | task.py resource_capabilities |
| execution_operations.py | OperationalOperations.capabilities | episode function | task.py capabilities tool |
| execution_operations.py | OperationalOperations.resource_tool_contracts | episode function (not reached by the API role) | unplaced: assembles the contracts of every resource for the parent commission text; the parent writes its own text (README 3a, C3) |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py catalog_of (BLOCKED-ON-JOB-SERVICE job_access api_catalog) |
| execution_operations.py | OperationalOperations.execute | episode function | task.py service_operation (BLOCKED-ON-JOB-SERVICE job_access api_execute) |
| execution_operations.py | OperationalOperations._has_appservice | episode function (not reached by the API role) | unplaced: chose the AppService fact sources by configuration; those sources are not declared (see carry-over record) |
| execution_operations.py | OperationalOperations._has_uniprot | episode function (not reached by the API role) | unplaced: chose the UniProt results sources (results role only) |
| execution_operations.py | OperationalOperations._appservice_sources | episode function (not reached by the API role) | unplaced: the AppService fact-source modules of the old shared root were not moved into episode_support |
| execution_state.py | OperationalExecutionState | machinery | machinery: old state holder |
| execution_state.py | OperationalExecutionState._delegate | episode function | task.py (the `job_access` service is the delegate) |
| execution_state.py | OperationalExecutionState._practical_context | machinery | machinery: returned its context unchanged for the local/hpc roles |
| execution_state.py | OperationalExecutionState.initialize | machinery | machinery: parent-input re-check on initialize (commission check) and local/results branches |
| execution_state.py | OperationalExecutionState._check_parent_inputs | machinery | machinery: re-read the parent request from runtime_episodes (store.db) and check the commission against it; check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| execution_state.py | OperationalExecutionState.state | episode function (not reached by the API role) | unplaced: local/hpc practical state; not reached by launch_api |
| execution_state.py | OperationalExecutionState._target | episode function (not reached by the API role) | unplaced: results-role target; not reached by launch_api |
| execution_state.py | OperationalExecutionState._selection | machinery | machinery: receipts inheritance and runtime_actions reads (record_selection); custody is the system's |
| execution_state.py | OperationalExecutionState._context_target | episode function (not reached by the API role) | unplaced: results/launch handoff target comparison; not reached by launch_api |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | OperationalAssignment.child_assignment_schema | episode function (not reached by the API role) | unplaced: the frozen HPC launch child schema; not the API role |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._permitted | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the API service validate_assignment, the BLAST selection check and the input checks are commission checks: machinery) |
| from_parent.py | OperationalAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (executor schema properties are the `request` record) |
| from_parent.py | OperationalAssignment._validate_request | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version choice, service, resource_id) |
| from_parent.py | OperationalAssignment._launch | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead; the parent now copies what this episode reads into its assignment |
| from_parent.py | OperationalAssignment._constraints | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment.initial_references | machinery | machinery: returned no references (`requests = []`); records are named in record_refs fields |
| from_parent_launch.py | LaunchParentAssignment | machinery | machinery: schema for re-reading the parent's Launch assignment; check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | machinery | machinery: schema for re-reading the parent's Launch assignment; check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| goal.py | OperationalGoal | episode function | goal.py GOAL and task.py GOAL_TEXT / instructions |
| goal.py | OperationalGoal.instructions | episode function | goal.py GOAL and task.py GOAL_TEXT / instructions |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py and task.py decide |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | task.py decide (execution_resource_capabilities, execution_initial_information, received_bvbrc_values via job_access read BLOCKED-ON-JOB-SERVICE); the MinHash values were for scientific roles only |
| internal_summary.py | OperationalSummary._with_selected_execution_task | episode function | task.py selected_execution_task (the parent's scientific_question and selected_tool_info are assignment fields) |
| internal_summary.py | OperationalSummary.decision_context | episode function | messages/internal_summary.py (execution_progress) and task.py decide (execution_assignment, api_decision_context via job_access read BLOCKED-ON-JOB-SERVICE) |
| native_input_custody.py | NativeInputCustody | machinery | machinery: native input custody and reference resolver of the old report validation; check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| native_input_custody.py | NativeInputCustody._masking_selector | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._masking_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._retained_masking_target | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._masking_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._utility_selector | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._utility_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._retained_utility_target | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._utility_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._versions | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._selector | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._protein_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._atac_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | machinery | machinery: reference resolver of the old report validation (resolve); the system admits returned records by custody |
| native_input_custody.py | NativeInputCustody._atac_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | machinery | machinery: check of this episode's own commission against the parent's assignment; a wrong commission fails (rule 1), nothing checks it ahead (native/masking/utility/immutable input versions against the parent) |
| received_evidence.py | ReceivedOperationalEvidence | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.received_report_closure_facts | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | machinery: receipts bookkeeping and received-report resolution/validation (README 3b R1, R3, D2); the system admits results and custody |
| report_delivery.py | OperationalReportDelivery | episode function | messages/final_to_parent.py final_to_parent |
| report_delivery.py | OperationalReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| result_acquisition.py | OperationalResultAcquisition | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._result_directory | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._windows | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._selected_result_action | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._execute_native_results | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._publish_result | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._validate_result_body | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._read_result | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._generic_result_selector_progress | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._native_results_complete | episode function (not reached by the API role) | unplaced: results role; carried by execution_result_acquisition |
| task.py | OperationalTask | episode function | task.py |
| task.py | OperationalTask.instructions | episode function | task.py instructions |
| task.py | OperationalTask.next | machinery | machinery: the old decision loop, replay, restore and source-failure end (decide/action are the new loop) |
| task.py | OperationalTask.apply_response | episode function | task.py action (admission by the action schema; rejection = Rejected; report-form validation machinery) |
| task.py | OperationalTask.execute | episode function | task.py tools service_operation / capabilities / wait / lookups (journaling, receipts and score updates are machinery) |
| task.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| task_decision.py | OperationalTaskDecision | machinery | machinery: the decision-exchange loop |
| task_decision.py | OperationalTaskDecision.call | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_schema | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | machinery: model-call recording, conversation state, decision exchange (README 3a) |
| task_decision.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| task_instructions.py | instructions | episode function | task.py instructions (the goal text replaces the default instructions; the default INSTRUCTIONS, the reasoning-commit, pending_child, native_event_targets and exchange paragraphs are not carried) |
| task_state.py | OperationalTaskState | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.__init__ | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.record_execution_failure | episode function | task.py service_operation returns the failed outcome (`failure_outcome`) |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.restore | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.record_effect | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | OperationalTaskState.checkpoint | machinery | machinery: per-episode state, checkpoint/restore, record_effect |
| task_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| terminal_execution.py | operation_catalog | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | machinery: the binding's own as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function (not reached by the API role) | unplaced: local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py |
| to_parent.py | OperationalReport.required_return_sources | machinery | machinery: returned no required sources (`pass`); required fields are credit and finding |
| to_parent.py | OperationalReport._forwards_bvbrc_reports | episode function (not reached by the API role) | unplaced: only for the annotation/sequence_homology_evidence roles |
| to_parent.py | OperationalReport._forwards_minhash_reports | episode function (not reached by the API role) | unplaced: only for the annotation/sequence_homology_evidence roles |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (selectable fields); masking, utility, AppService and UniProt sources not declared |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | OperationalReport._live_facts | episode function | messages/final_to_parent.py final_to_parent / fact (native families `[]`, service facts from the outcome) |
| to_parent.py | OperationalReport.resolve | machinery | machinery: reference resolver of the old report validation; custody |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report (called before the result is returned) |
| waiting.py | OperationalTaskWaiting | episode function | task.py wait |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | episode function | task.py wait tool (BLOCKED-ON-JOB-SERVICE job_access wait_for_job) |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | machinery: suspension machinery |
| waiting.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching (`_bind_original_task_runtime_providers`) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py request_yield_class (API branch; the practical branch is not reachable for this role) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py yield_controller (completion, README 7b) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | machinery: PracticalYieldEstimator packet estimator deleted (README 3d) |
| yield_estimator.py | ExecutionEpisodeYield._private_practical_estimator | machinery | machinery: PracticalYieldEstimator packet estimator deleted (README 3d) |
