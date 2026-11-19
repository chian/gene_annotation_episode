# a103 / gene_context_evidence / hpc_work_planning / execution_job_submission / api_job_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_job_submission/api_job_execution/<file>` (files directly in the folder; no grading/ or scoring/ subfolder; `tests/` not read). Old role: `launch_api`. `binding_path = '.../execution_job_submission/api_job_execution'`, `commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`, `replaces_default_instructions = True`, renderer `render_api_job_prompt` (presentation `present_api_job_task`).

## Purpose (goal, in its own words)

`goal.py` `APIJobGoal.instructions` (service taken from the validated assignment):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit.

It runs one API service request (for example NCBI BLAST, EBI HMMER, BV-BRC services) chosen by the launch parent, one operation per turn, until a usable monitoring/results handoff is recorded.

## Task and instructions

- `instructions.py`: the binding's goal, tool-knowledge instructions, launch-instruction-library instructions, the pending_child_delivery repair paragraph, the `pending_child_` wait paragraph when wait is permitted, the native_event_targets paragraph when available, and the exchange-protocol history rewrite. Unlike the launch parent and the native children it does not append `REASONING_COMMIT_REQUIREMENT` (no reason action).
- `task.py` (`APIJobTask`): same loop as the parent, but the reasoning-commit emptiness check is removed (selection validated against the selection schema unless it is a permitted reason action), no `_validate_hpc_launch_report_contract`, and report updates validated with `grain='launch_api'`.

## What it reads from its parent's assignment

`from_parent.py` `APIJobAssignment`:
- `child_assignment_schema(parent, role)` = `assignment_schema(role)` = `anyOf` of the selected request schemas of every configured resource whose kind is `api` (`{'not': {}}` if none). Each request schema is `api_execution.assignment_schema(resource_id)` with `resource_id` const and required.
- `prepare_assignment`: validate the request; `api_execution.validate_assignment(selected, scope=scope)`; resource kind must be `api` (`execution_resource_kind_conflict`); parent role must be `launch` (`resource_child_role_owned_by_launch`); re-validate the parent's original launch assignment (`parent_launch_contract.parent_launch_schema`, independent of this child's role) and check the BLAST launch selection against it (`_validate_blast_launch_selection`); masking/utility inputs; immutable input versions of the parent launch; native BLAST database / standard database input validation.
- `operations._check_parent_inputs` (on initialize and every execute): reads the parent's saved request (`runtime_episodes` by path), re-validates its launch assignment, `_validate_blast_api_parent_request`, masking/utility inputs, immutable versions and BLAST database inputs; missing parent row raises `execution_original_launch_assignment_unavailable`.
- `required_return_sources` returns `()` (the parent's version returns `execution_handoff_refs` for launch).

## Children

None: `child_eligibility.py` returns `()` for `child_roles` and `allowed_children`.

## Decision state and what it shows the model

`decision_state.py` and `decision_inputs.py` are the parent's copies (the latter with `launch_api` as the execution-expectations role). The binding's `decision_context` (`internal_summary.py`) gives `execution_assignment`, `execution_progress` (its facts), plus whatever `api_execution.decision_context(context, view)` adds, plus `selected_execution_task` built from the single assignment when the scientific parent task is available and the request is `ebi_hmmer` (API branch) — other API services return the value without a selected task.

`decision_presentation.py` (413 lines, specific to this episode) holds the API launch prompt: `is_api_launch_context` (assignment version `api_service_assignment_v1` with request, service matching `api_service`, and an `api_request`), `select_profile_api_execution_values` (keeps `service, subject_ref, algorithm, database, parameters, page_size` of an `api_execution_assignment_v1`), and `render_api_launch_prompt` = TASK + STEERING:
- TASK: Scientific QUESTION (root objective, or the selected execution task's question), Assigned job, Assigned scope, Selected API work (`resource_id, service, endpoint`), Parent constraints, parent-selected tool guidance, Configured resource, Exact assigned scientific request, Execution method and decision rules (instructions), each callable operation with its instructions and argument schema, selected resource instructions, information requested by the parent, the requested controlled JSON return and the meaning of requested recorded facts.
- STEERING: completed action reports, pending child delivery, own action categories table (completed, observed signed yield, expected next yield, uncertainty, uncompleted attempts), current operational continuation (completed actions, credit, expected next gain, uncertainty, continuation cost, controller decision), yield information limits, original handoff completion (`api_execution_completed`), recorded own API outcomes (errors shown in full via `is_api_error_return`), latest own action (complete returned error when failed), complete returned feedback, own pending work, and lookup results ("Requested information; continue the same decision").
- Operational facts are filtered by `_CODE_FIELDS`, `_NUMBER_FIELDS`, `_BOOLEAN_FIELDS`, measurement names/units.
- `render_api_job_prompt` / `present_api_job_task` pick a renderer in this order: HPC, published scientific, API launch, selected execution, monitor, receiver.

## Tools it offers

`operations.py`: the catalog and execution are delegated to `api_execution` (`_delegate` returns `api_execution` for role `launch_api`): the configured service's own operation contracts. Execution first runs `_check_parent_inputs`.

Action policy: `('tool', 'wait')` when the assignment version is `api_service_assignment_v1` (a remote service job may continue and be waited on), else `('tool',)`.

## Credit

`credit.py`: kind `operational`; closed view if saved; else a native result family's view if one applies; otherwise `api_execution.credit_view(context, receiver_selection)` (the parent instead counts usable handoffs per resource). Unbounded.

`completion.py`: `completion_for_action` = native family proofs, else `_delegate(context).completion_for_action(...)` (the API execution's own proof); `verify_completion` = closed recorded verdict, else native family, else `api_execution.verify_completion(context, proof)`. The parent's `_proof_for_action` (usable-handoff proof from `runtime_actions`) is absent here.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_api_yield_controller` (requires `require_private_yield=True`): profile key `'launch_api:' + request_class`, where the class is `api_<service>[_<algorithm>][_<database>]_handoff` (or `compact_<version>`). Uses old `YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(verify_completion))` — gives exact zero once a verified completion proof exists. Settings: `task_yield_profiles['launch_api:<class>'] = {cutoff > 0, parameters}`. In the new layout this corresponds to the completion-with-a-target estimator (inferred).

## What it reports to its parent

`to_parent.py` `APIJobReport`: same fact-source catalogue as the parent (no terminal practical sources). `_live_facts`: a native family's facts if one applies; otherwise `{**native_empty, **api_execution.facts(context, completion_snapshot), 'execution_result_origin': None}`. Closed credit facts are merged. `validate_report` as in the parent (recorded `x-source` facts must match). `report_delivery.py` is the parent's copy.

## Configuration

`configuration.py` is the parent's `LaunchConfiguration` body under the name `APIJobConfiguration` (same parameters and validation). `binding_record.py` uses `binding_id = '.../execution_job_submission/api_job_execution'`, `VERSION = 'execution_episode_v1'`.

## Differences from sibling/similar episodes

- Only API child: own 413-line prompt renderer; `wait` permitted for `api_service_assignment_v1`; credit, completion, verification and facts delegated to `api_execution`; checks the parent's BLAST launch selection (`_validate_blast_launch_selection`, `_validate_blast_api_parent_request`); goal text names the service and stresses submission uncertainty.
- vs hpc/local: no `terminal_*.py` split (single `terminal_execution.py`, byte-identical to the parent's); no `REASONING_COMMIT_REQUIREMENT` in instructions; `selected_execution_task` filled (hpc returns it empty).
- vs parent: no children, no `execution.capabilities` tool, no handoff-count credit, `required_return_sources` empty.

## File by file

`wf.` = `self.workflow.` / `source.workflow.`. Imports are old shared-root modules (not read).

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `goal.py` | 10 | API job goal (quoted). | — |
| `instructions.py` | 20 | Same paragraphs as parent minus reasoning requirement. | wf.specialist, wf.binding_context, wf.knowledge, wf.launch_instructions, wf.permits_common_action×2, wf.native_event_information, wf.decision_protocol; runtime_prompt.INSTRUCTIONS×3, .DECISION_EXCHANGE_PROTOCOL; import runtime_prompt |
| `task.py` | 226 | Loop with grain `launch_api`, no empty-reasoning check. | as parent task.py minus wf.reasoning_action_schema / one wf.specialist / one wf.binding_context: wf.journal×7, wf.store×8, wf.execution_binding×7, wf.inprocess_replay×4, wf.completions×3, wf.completed_unit×3, wf.selected×3, wf.decision_exchanges×3, wf.run_id×3, wf.controller_value×2, ... ; runtime.*; ModelCallError; record_source_failure; tables runtime_actions×8, runtime_model_calls×2, runtime_episodes; imports runtime, providers, episode_source_failure, library.action_contracts, library.private_policy_call, read_mapping |
| `task_state.py` | 108 | Generic. | same as parent task_state.py |
| `decision_state.py` | 45 | Generic copy. | same as parent decision_state.py |
| `decision_inputs.py` | 70 | Execution expectations for `launch_api`. | same as parent decision_inputs.py |
| `decision_presentation.py` | 413 | API launch TASK/STEERING prompt (above). | providers.apply_state_frame×3, is_published_scientific_context×2, render_gene_context_evidence_prompt, _ordinary_runtime_receiver_context, DECISION_CONTEXT_VERSION, text_instructions, deepcopy, json; imports api_error_feedback, gene_context_evidence_prompt, execution_contracts, episode_work_report, library.hpc_prompt, library.monitor_prompt, native_profile_presentation, receiver_prompt, providers |
| `decision_delivery.py` | 82 | Generic. | same as parent |
| `decision_exchange.py` | 116 | Generic. | same as parent |
| `saved_decision_exchange.py` | 82 | Generic. | same as parent |
| `decision_contracts.py` | 36 | Generic. | same as parent |
| `decision_provider.py` | 18 | Dispatch with this renderer. | wf.provider×2, wf.specialist; import runtime |
| `waiting.py` | 9 | Generic suspension (used by its `wait`). | wf.execution_handle×2, wf.execution_backend |
| `report_delivery.py` | 25 | Generic finish. | same as parent |
| `episode.py` | 32 | Composition, role `launch_api`, renderer. | — |
| `action_policy.py` | 12 | tool (+wait for service assignments). | — |
| `binding_record.py` | 9 | Binding record. | — |
| `child_eligibility.py` | 12 | No children. | — |
| `parent_launch_contract.py` | 8 | Parent launch schema independent of this child's role. | — |
| `configuration.py` | 65 | Same as parent. | YieldController×3, YieldParameters×3; imports numerical, api_service_execution, execution_progress |
| `contracts.py` | 59 | Same constants; imports own terminal_execution. | same shared-root imports as parent |
| `from_parent.py` | 128 | API assignment schema and parent-checked preparation. | imports native_blast_database_result_publication, native_blast_standard_database_result_publication |
| `operations.py` | 56 | Delegation to api_execution; parent input checks. | table runtime_episodes; imports native_blast_*_result_publication, native_blast_masking_results, native_blast_utility_results |
| `internal_summary.py` | 124 | api_execution decision context; single-request selected task. | import native_profile_presentation; `self.services.scientific_parent_task` |
| `credit.py` | 39 | Credit delegated to api_execution. | — |
| `closed_credit.py` | 117 | Identical to parent. | same as parent |
| `completion.py` | 65 | Delegated completion/verification. | UnitRef×2, NumericBand×2, ESTIMATOR_VERSION×2; table runtime_observations; imports method_loop.identities, episode_return_records, numerical, practical_yield |
| `yield_estimator.py` | 50 | `launch_api:<class>` profile + completion estimator. | YieldController×2, YieldParameters×2, PracticalYieldEstimator×4; imports numerical, practical_yield |
| `to_parent.py` | 118 | API facts with null result origin. | result-view module imports (as parent) |
| `received_information.py` | 113 | Same as parent. | result-view imports |
| `received_record_selection.py` | 35 | Same as parent. | — |
| `received_reference_custody.py` | 160 | Same as parent. | imports bvbrc_homology_returns, hmmer_native_result_views |
| `report_reference_access.py` | 115 | Same as parent. | imports episode_bindings and result modules |
| `result_records.py` | 260 | Same as parent. | EpisodeReceipts×2; tables runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2; imports episode_receipts, execution_input_versions, result views |
| `terminal_execution.py` | 185 | Byte-identical to parent's single-class terminal behaviour (built for any local/HPC resources configured alongside). | PracticalYieldEstimator×2; imports practical_execution_*, terminal_execution, terminal_scientific_evidence, practical_receipt_information, practical_yield |

Per-use counts: `runs/carry_over/calls/a103_03.tsv`.

## Carried over

Carried 19 November 2026 into the ten-file form (no children: no msg_to_child.py, no read_from_child.py). One row per old function, class and method of the old episode folder (runs/carry_over/functions). Classification: machinery (old runner, not carried) or episode function (placed; "unplaced" rows could not be placed and are in carry_over_blocked).

| old file | kind | name | machinery or episode function | new place or reason |
|---|---|---|---|---|
| action_policy.py | class | APIJobActionPolicy | episode function | task.py `_offered` (the wait is offered only for `api_service_assignment_v1`) |
| action_policy.py | method | APIJobActionPolicy.permitted_common_actions | episode function | task.py `_offered` (the wait is offered only for `api_service_assignment_v1`) |
| binding_record.py | class | APIJobBindingRecord | machinery | the binding's own as_record() and binding descriptor (README 3) |
| binding_record.py | method | APIJobBindingRecord.as_record | machinery | the binding's own as_record() and binding descriptor (README 3) |
| child_eligibility.py | class | APIJobChildEligibility | episode function | task.py `CHILD_SLOTS = {}` (no child roles) |
| child_eligibility.py | method | APIJobChildEligibility.child_roles | episode function | task.py `CHILD_SLOTS = {}` (no child roles) |
| child_eligibility.py | method | APIJobChildEligibility.allowed_children | episode function | task.py `CHILD_SLOTS = {}` (no child roles) |
| closed_credit.py | class | ClosedExecutionCredit | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_carrier | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_receipts | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_value | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_facts | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| closed_credit.py | method | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed-credit capture and receipt/observation authentication (receipt inheritance, runtime_* tables); credit is `credit.py`, completion credit is `completion['credit']` |
| completion.py | class | ExecutionCompletion | machinery | completion proof and estimator provenance (reads runtime_observations); replaced by the completion controller in `yield_estimator.py` (README 3d, 7b); the verified-completion value comes from the job-access reply as `execution_completed` in the tool outcome |
| completion.py | method | ExecutionCompletion.completion_for_action | machinery | completion proof and estimator provenance (reads runtime_observations); replaced by the completion controller in `yield_estimator.py` (README 3d, 7b); the verified-completion value comes from the job-access reply as `execution_completed` in the tool outcome |
| completion.py | method | ExecutionCompletion._closed_completion_verdict | machinery | completion proof and estimator provenance (reads runtime_observations); replaced by the completion controller in `yield_estimator.py` (README 3d, 7b); the verified-completion value comes from the job-access reply as `execution_completed` in the tool outcome |
| completion.py | method | ExecutionCompletion.verify_completion | machinery | completion proof and estimator provenance (reads runtime_observations); replaced by the completion controller in `yield_estimator.py` (README 3d, 7b); the verified-completion value comes from the job-access reply as `execution_completed` in the tool outcome |
| configuration.py | class | APIJobConfiguration | episode function | settings (README 3: configuration values): `handoff_unit`, `acquired_record_unit` read in task.py `_outcome`; `task_yield_profiles` in yield_estimator.py `task_yield_profile`; resources, workspace and native result readers are old-runner/results-role configuration (not carried) |
| configuration.py | method | APIJobConfiguration.__init__ | episode function | settings (README 3: configuration values): `handoff_unit`, `acquired_record_unit` read in task.py `_outcome`; `task_yield_profiles` in yield_estimator.py `task_yield_profile`; resources, workspace and native result readers are old-runner/results-role configuration (not carried) |
| contracts.py | function | launch_operation_catalog | episode function | task.py `api_capabilities` tool |
| contracts.py | function | native_result_operation_catalog | episode function (not placed) | unplaced: local/PBS result acquisition operations (results role); the API launch path never offers them |
| contracts.py | function | _outcome | episode function | task.py `_outcome` (returned outcome of a job-access reply) |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py `credit` (the old `api_execution.credit_view` is not in the library: reconstructed from handoff_unit and acquired_record_unit; the native result families are not on the API launch path) |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py `credit` (the old `api_execution.credit_view` is not in the library: reconstructed from handoff_unit and acquired_record_unit; the native result families are not on the API launch path) |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py `credit` (the old `api_execution.credit_view` is not in the library: reconstructed from handoff_unit and acquired_record_unit; the native result families are not on the API launch path) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py `credit` (the old `api_execution.credit_view` is not in the library: reconstructed from handoff_unit and acquired_record_unit; the native result families are not on the API launch path) |
| decision_contracts.py | class | APIJobDecisionContracts | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_contracts.py | method | APIJobDecisionContracts.exchange_schema | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_contracts.py | method | APIJobDecisionContracts.exchange_response | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_delivery.py | class | APIJobDecisionDelivery | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_delivery.py | method | APIJobDecisionDelivery.call | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_delivery.py | method | APIJobDecisionDelivery.instructions | episode function | task.py `_instructions` |
| decision_exchange.py | class | APIJobDecisionExchange | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_exchange.py | method | APIJobDecisionExchange.interpretation_context | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_exchange.py | method | APIJobDecisionExchange.exchange_decision | machinery | the decision-exchange loop / decision machine (README 3a) |
| decision_inputs.py | class | APIJobDecisionInputs | episode function | task.py `_context` (TASK and STEERING sections) and `_offered`; the pieces without a home are in the blocked file |
| decision_inputs.py | method | APIJobDecisionInputs.decision_inputs | episode function | task.py `_context` (TASK and STEERING sections) and `_offered`; the pieces without a home are in the blocked file |
| decision_presentation.py | function | select_profile_api_execution_values | machinery | provider masking of operands before generic tracking masking (provider patching) |
| decision_presentation.py | function | is_api_launch_context | machinery | renderer dispatch of the old provider |
| decision_presentation.py | function | _scope | episode function (not placed) | unplaced: the old Store scope of the assignment is not an assignment field now; no scope rendering |
| decision_presentation.py | function | _requested_sources | episode function (not placed) | unplaced: listed the x-source fields of the parent-written return form; the parent selects fields now (rule 5) |
| decision_presentation.py | function | _task | episode function | task.py `_context` (the TASK section as a mapping) |
| decision_presentation.py | function | _band | episode function | already in library: episode_support/records/progress_views.py `yield_table` (shown in `action_yields`) |
| decision_presentation.py | function | _number | episode function | messages/internal_summary.py `_number` |
| decision_presentation.py | function | _returned_value | episode function | messages/internal_summary.py `_returned_value` |
| decision_presentation.py | function | _is_error_return | episode function | already in library: episode_support/acquisition/service_calls/api_error_feedback.py `is_api_error_return` |
| decision_presentation.py | function | _error_text | episode function (not placed) | unplaced: text rendering of an error table; the structured context carries the complete returned error unfiltered |
| decision_presentation.py | function | _operational_scalars | episode function | messages/internal_summary.py `_operational_scalars` |
| decision_presentation.py | function | _measurements | episode function | messages/internal_summary.py `_measurements` |
| decision_presentation.py | function | _qualifications | episode function | messages/internal_summary.py `_qualifications` |
| decision_presentation.py | function | _operational_facts | episode function | messages/internal_summary.py `_operational_facts` |
| decision_presentation.py | function | _api_progress | episode function | messages/internal_summary.py `_api_progress` |
| decision_presentation.py | function | _own_outcome | episode function | messages/internal_summary.py `_own_outcome` |
| decision_presentation.py | function | _lookup | episode function | task.py `_context` (`requested_information` carries the lookup outcomes; lookups are tools) |
| decision_presentation.py | function | _steering | episode function | task.py `_context` (the STEERING section as a mapping) |
| decision_presentation.py | function | render_api_launch_prompt | episode function | task.py `decide` / `_context` (rendered as structured sections, not text tables: the text helpers are not in the library) |
| decision_presentation.py | function | render_api_job_prompt | machinery | renderer dispatch among the HPC, gene-context, monitor and receiver renderers of other roles |
| decision_presentation.py | function | present_api_job_task | machinery | provider presentation hook and conversation state frames (README 3a) |
| decision_provider.py | class | APIJobDecisionProvider | machinery | conversation key and provider call (README 3a) |
| decision_provider.py | method | APIJobDecisionProvider.conversation_key | machinery | conversation key and provider call (README 3a) |
| decision_provider.py | method | APIJobDecisionProvider.complete_decision | machinery | conversation key and provider call (README 3a) |
| decision_state.py | class | APIJobDecisionState | episode function | messages/internal_summary.py `internal_summary` and task.py `_context` |
| decision_state.py | method | APIJobDecisionState.decision_state | episode function | messages/internal_summary.py `internal_summary` and task.py `_context` |
| episode.py | class | ExecutionEpisode | episode function | episode.py `ApiJobExecution` |
| from_parent.py | class | APIJobAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | APIJobAssignment.child_assignment_schema | machinery | the parent-side description of the child assignment (README 3b C3) |
| from_parent.py | method | APIJobAssignment.assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` |
| from_parent.py | method | APIJobAssignment._permitted | episode function (not placed) | unplaced: check of the parent launch request against resources and constraints: a check of a commission (rule 1) |
| from_parent.py | method | APIJobAssignment.prepare_assignment | episode function | messages/read_from_parent.py `read_from_parent` (`validate_api_assignment`); the checks against the parent launch selection, immutable input versions and native/standard BLAST job inputs are checks of a commission and not carried |
| from_parent.py | method | APIJobAssignment._request_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (API branch) |
| from_parent.py | method | APIJobAssignment._validate_request | episode function | messages/read_from_parent.py `read_from_parent` (API branch via `validate_api_assignment`; the local/PBS branch is not this episode) |
| from_parent.py | method | APIJobAssignment._launch | episode function (not placed) | unplaced: validates the parent launch assignment, which a child cannot read (README 5 item 14) |
| from_parent.py | method | APIJobAssignment._constraints | episode function (not placed) | unplaced: validates the parent launch constraints (README 5 item 14) |
| from_parent.py | method | APIJobAssignment.required_return_sources | machinery | parent-written return form (README 3b C4); returned () |
| from_parent.py | method | APIJobAssignment.initial_references | episode function | messages/read_from_parent.py `input_refs` (record_refs field: records are passed in custody) |
| goal.py | class | APIJobGoal | episode function | goal.py `GOAL` |
| goal.py | method | APIJobGoal.instructions | episode function | goal.py `GOAL` |
| instructions.py | function | instructions | episode function | task.py `_instructions` (the pending-delivery, in-process wait and native-event paragraphs and the exchange-history replacement describe actions that no longer exist and are dropped) |
| internal_summary.py | class | APIJobSummary | episode function | messages/internal_summary.py and task.py `_context` |
| internal_summary.py | method | APIJobSummary.initial_decision_context | episode function | task.py `_context` (configured resource from `api_capabilities`); received_bvbrc_values, received_blast_jobs, received_minhash_values come from `api_execution` (not in the library): blocked file |
| internal_summary.py | method | APIJobSummary.decision_context | episode function | messages/internal_summary.py `internal_summary` (assignment, progress facts, API decision context) |
| internal_summary.py | method | APIJobSummary._with_selected_execution_task | episode function (not placed) | unplaced: reads the scientific parent task (`scientific_parent_task`) and `native_profile_presentation`: the parent task is not a record this episode holds (README 5 item 14) |
| internal_summary.py | method | APIJobSummary._resource_information | episode function | task.py `api_capabilities` tool and `_context` (`configured_resource`) |
| internal_summary.py | method | APIJobSummary.capabilities | episode function | task.py `api_capabilities` tool |
| internal_summary.py | method | APIJobSummary.resource_tool_contracts | episode function | task.py `ARGUMENTS`, `DESCRIPTIONS`, `TOOLS`; `api_execution.operation_contracts` and `homology_api_contracts` are not in the library: blocked file |
| operations.py | class | APIJobOperations | episode function | task.py `TOOLS` |
| operations.py | method | APIJobOperations._delegate | episode function | task.py `api_operation` (the API resource is the only delegate) |
| operations.py | method | APIJobOperations._practical_context | machinery | identity function of the old context |
| operations.py | method | APIJobOperations.initialize | machinery | local-file-source initialisation and the parent-input check against runtime_episodes (README 3e) |
| operations.py | method | APIJobOperations._check_parent_inputs | machinery | reads the parent request from runtime_episodes and re-validates it: a commission check (rule 1) and old journal |
| operations.py | method | APIJobOperations.catalog | episode function | task.py `_offered`, `ARGUMENTS`, `DESCRIPTIONS` |
| operations.py | method | APIJobOperations.execute | episode function | task.py `api_operation` and `wait_for_service_job` tools |
| parent_launch_contract.py | function | parent_launch_schema | episode function (not placed) | unplaced: schema of the commissioning parent Launch assignment; the parent's own assignment is not readable by the child (README 5 item 14) |
| received_information.py | class | ReceivedExecutionInformation | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_information.py | method | ReceivedExecutionInformation._forwards_bvbrc_reports | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_information.py | method | ReceivedExecutionInformation._forwards_minhash_reports | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_information.py | method | ReceivedExecutionInformation.received_report_sources | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_information.py | method | ReceivedExecutionInformation.received_report_facts | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_information.py | method | ReceivedExecutionInformation.received_report_closure_facts | episode function (not placed) | unplaced: forwards report sources of children to a scientific owner (annotation or gene_context_evidence roles); this launch_api leaf is never that role |
| received_record_selection.py | class | ReceivedRecordSelection | machinery | record_selection and received-record custody (README 3c) |
| received_record_selection.py | method | ReceivedRecordSelection._received | machinery | record_selection and received-record custody (README 3c) |
| received_reference_custody.py | class | ReceivedReferenceCustody | machinery | received reference custody and received-report validation (README 3b R1, R3) |
| received_reference_custody.py | method | ReceivedReferenceCustody.resolve_received_reference | machinery | received reference custody and received-report validation (README 3b R1, R3) |
| received_reference_custody.py | method | ReceivedReferenceCustody.validate_received_report | machinery | received reference custody and received-report validation (README 3b R1, R3) |
| received_reference_custody.py | method | ReceivedReferenceCustody.received_form_references | machinery | received reference custody and received-report validation (README 3b R1, R3) |
| report_delivery.py | class | APIJobReportDelivery | machinery | `finish`: saving the report form and release (README 3b D1, D3); the facts are `final_to_parent` |
| report_delivery.py | method | APIJobReportDelivery.finish | machinery | `finish`: saving the report form and release (README 3b D1, D3); the facts are `final_to_parent` |
| report_reference_access.py | class | ReportReferenceAccess | machinery | reference resolver and report reference custody (README 3b D2) |
| report_reference_access.py | method | ReportReferenceAccess.resolve | machinery | reference resolver and report reference custody (README 3b D2) |
| result_records.py | class | ExecutionResultRecords | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._masking_selector | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._masking_inputs | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._retained_masking_target | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._masking_reference_access | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._utility_selector | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._utility_inputs | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._retained_utility_target | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._utility_reference_access | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._versions | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._target | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._selector | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._result_directory | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._windows | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._selected_result_action | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._validate_result_body | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._read_result | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._selection | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._context_target | episode function (not placed) | unplaced: results-role helper (native masking/utility selectors, result directory and windows, result body reading); the API launch role never reaches it |
| result_records.py | method | ExecutionResultRecords._has_appservice | episode function | messages/final_to_parent.py (all fact sources are declared as selectable fields; no per-configuration test) |
| result_records.py | method | ExecutionResultRecords._has_uniprot | episode function | messages/final_to_parent.py (all fact sources are declared as selectable fields; no per-configuration test) |
| result_records.py | method | ExecutionResultRecords._appservice_sources | episode function | messages/final_to_parent.py `FIXED` (`bvbrc_appservice_support_refs`); `homology_fact_sources` is not in the library: blocked file |
| saved_decision_exchange.py | class | APIJobSavedDecisionExchange | machinery | saved-request and exchange-history checks (README 3a) |
| saved_decision_exchange.py | method | APIJobSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request and exchange-history checks (README 3a) |
| saved_decision_exchange.py | method | APIJobSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request and exchange-history checks (README 3a) |
| task.py | class | APIJobTask | episode function | task.py |
| task.py | method | APIJobTask.next | episode function | task.py `decide` (loop, replay, in-process restore and SourceEnd are machinery) |
| task.py | method | APIJobTask.apply_response | episode function | task.py `action` (rejection feedback; the report_update admission and redelivery are machinery) |
| task.py | method | APIJobTask.execute | episode function | task.py tools `api_operation`, `wait_for_service_job` (journaling, controller_value and score updates are machinery) |
| task_state.py | class | APIJobTaskState | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.__init__ | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.bind_execution_context | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.record_execution_failure | episode function | task.py `_outcome` (a failed, invalid or unavailable reply is a returned outcome that enters the iterator) |
| task_state.py | method | APIJobTaskState.restore_checkpoint | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.restore | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.record_effect | machinery | task state restore, checkpoint and effect records (README 3e) |
| task_state.py | method | APIJobTaskState.checkpoint | machinery | task state restore, checkpoint and effect records (README 3e) |
| terminal_execution.py | function | operation_catalog | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | class | TerminalExecutionBehavior | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior._operations | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior._assignment | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior._state_directory | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.initialize | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.state | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.assignment_schema | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.prepare_assignment | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.initial_decision_context | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_information | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_instructions | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.instructions | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.decision_context | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.catalog | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.execute | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.completion_for_action | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.fact_sources | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.facts | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.resolve | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function (not placed) | unplaced: single-file terminal (local/PBS) behaviour kept for the contracts import only; the API path never used it (intent record) |
| to_parent.py | class | APIJobReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | APIJobReport.fact_sources | episode function | messages/final_to_parent.py `RETURN_FORM` (the declarations come from the library views) |
| to_parent.py | method | APIJobReport.facts | episode function | messages/final_to_parent.py `final_to_parent` |
| to_parent.py | method | APIJobReport._live_facts | episode function | messages/final_to_parent.py `final_to_parent` (recorded facts from the summary; the native families are not on the API path) |
| to_parent.py | method | APIJobReport.validate_report | episode function | messages/final_to_parent.py `validate_report` |
| waiting.py | class | APIJobWaiting | machinery | `suspension_changed`: wait suspension on the execution backend (README 3b); the wait itself is the `wait_for_service_job` tool |
| waiting.py | method | APIJobWaiting.suspension_changed | machinery | `suspension_changed`: wait suspension on the execution backend (README 3b); the wait itself is the `wait_for_service_job` tool |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py `request_yield_class` |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py `task_yield_profile` |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py `yield_controller` (completion controller) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | `PracticalYieldEstimator(verify_completion)` (README 3d) |
