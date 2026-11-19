# Intent: a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission

Read from its own files at commit `97308b94c`. The child folders `hpc_job_execution/` and `local_job_execution/` have their own notes; `tests/` was not read. Old role name: `launch`. Old commissioning parent: `hpc_allocation_execution` (role `hpc_execution`). Its parent's code also accepts parent role `hpc`.

## Purpose (its own words, `goal.py`)

"Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with exact zero future credit."

The episode is a dispatcher. It never runs commands itself. It picks one of the permitted per-resource requests in its assignment, commissions the matching resource child (`launch_local` or `launch_hpc`), and finishes once a usable handoff (a practical receipt) has been received.

## Task and instructions

`goal.py` gives the text above, and `replaces_default_instructions = True` (it replaces the shared instructions). `task_instructions.py` composes the full text. Everything it adds comes from old-runner machinery:
- the specialist instructions;
- the `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted;
- the tool_knowledge and launch_instruction_library blocks;
- `pending_child_delivery` repair text and pending-child `wait` text;
- native_event text;
- under `DECISION_EXCHANGE_PROTOCOL`, replacing the fresh-conversation history guidance with "request_context exchanges ... episode.history tool".

`task_decision.LaunchTaskDecision.instructions` calls `self.workflow.services.instructions(self, context)`; the composer above is `instruction_composer`.

## What it reads from its parent's assignment (`from_parent.py`)

The assignment schema, `execution_launch_assignment_v1`:
- `version`;
- `requests`: one entry per configured resource_id, each a `practical_assignment_v1` with `resource_id` const, `resource_kind` const, and `requested_job` that is either generic or, internally, a native flux-balance alternative;
- `immutable_input_versions` (INPUT_VERSION_SCHEMA[]);
- `constraints` (allowed_resource_ids, allowed_kinds, resource_id, kind);
- `launch_instructions` (SELECTION_SCHEMA).

With a native_flux_balance resource, the alternative is a compact `launch_assignment_schema`.

`prepare_assignment`:
- When the parent is `hpc`/`hpc_execution`, it calls the parent's `authenticate_launch`: only the exact frozen planned launch is accepted, and it consumes one launch reservation.
- A compact launch goes through `flux_balance_requests.preview`.
- Otherwise it validates each request and the constraints, checks flux-balance inputs against `immutable_input_versions`, and validates the input versions in scope.

`_permitted(assignment, resource_id)` applies the constraints.

## Children it may commission

`child_roles` = (`launch_local`, `launch_hpc`). `allowed_children` keeps only the roles that have a configured resource of the matching kind and is permitted by the assignment.

| Child | What it sends | What it takes back |
|---|---|---|
| `launch_local` -> `local_job_execution` | One selected per-resource `practical_assignment_v1` (or the compact resource assignment). The child's own `from_parent` validates it. The request envelope comes from `to_child_local_job_execution.assemble_request`: goal, scope, initial_report, job/episode assignment, report-contract declaration, receipt binding. | The child's typed form: `practical_*` facts and `execution_handoff_refs`. `from_child_local_job_execution.receive_report` records the form's references as received. |
| `launch_hpc` -> `hpc_job_execution` | Same, for the PBS resource. Under an HPC ancestor the child accepts only the frozen hpc request (enum). | Same. |

`prepare_child_request` passes the assignment through unchanged.

## Decision state and what the model sees

`LaunchDecisionState` (in `internal_summary.py`) builds the old generic context:
- goal, scope, working_state, credit, credit_binding, time_accounting;
- pending_work, last_local_outcome, feedback, controller, tools;
- available_report_facts, requested_form, current_report_update;
- handling for annotation-axis credit mode.

On top of that, `LaunchInternalSummary.decision_context` adds this episode's own items:
- `execution_assignment` and `execution_progress` (this episode's facts);
- `selected_execution_task` for native flux-balance work: the scientific_question and selected_tool_info from the services hook `scientific_parent_task`, plus per-request resource information;
- for a compact assignment: `practical_assignment`, `practical_progress` and `practical_completed`.

`task_decision` decision inputs:
- resource_context, shared_information_context;
- launch_instruction_library and selected_launch_instructions;
- child_options and the initial binding context, which includes the parent's `hpc_execution_job`;
- completed_action_reports, requested_action_history (HPC context);
- execution_expectations('launch'), resource_tool_estimates, native expectations.

`task_presentation.present_launch_context` picks the prompt renderer: HPC, published-scientific (`render_biochemical_feasibility_evidence_prompt`), selected-execution, monitor or receiver. Otherwise the context is sent as JSON.

## Tools it offers

- `execution.capabilities` (no arguments): "Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection." It returns `execution_capability_information`.
- `resource_tool_contracts()` publishes, for the shared tool catalog, the per-resource launch operations (`operation_catalog(kind)`) and result operations (`execution.results.status`, `.collect` and `.read`, from `received_result_records.py`). These are routed as commissions (entry_role, resource_id, resource_role). It also publishes native flux-balance tool contracts per resource.

Common actions:
- under an `hpc` ancestor: `tool`, `child`, `redeliver_report`;
- otherwise: `tool`, `reason`, `child`, `wait`, `redeliver_report`.

`task.py` adds behaviour specific to this episode:
- `reason` commits, through `store.commit_reasoning` or the specialist's `execute_reasoning`;
- feedback for `job_child` storage/control failures;
- feedback for `ContractError` `component_native_return_channels_required`;
- feedback for BV-BRC minhash `results` selector input errors;
- `automatic_score_updates` and `retain_shared_grading_results` after `shared.read_information`.

## Credit (`credit.py`)

`credit_kind` = 'operational'. Live credit = `handoff_unit × handoff_count + acquired_record_unit × acquired_fraction`, where:
- `handoff_count` is the number of distinct resource_ids with a *usable* received handoff that was not already in the initial known refs;
- `acquired_fraction` is fixed at 0.0, and the `mixed` path is dead code.

Credit binding `execution_received_records_credit_v1`.

Closed credit: once the episode has closed, `_closed_operational_credit_view` returns only the snapshot captured in `runtime_forms` facts (`execution_closed_operational_credit_v1`). The snapshot is authenticated against the episode row, the archive, the observation history and the receipt-inheritance prefix. It is never re-projected.

## Continuation (`yield_estimator.py`, `configuration.py`)

Old behaviour:
- Remaining = |eligible original requests − those already received in the initial handoffs| × handoff_unit.
- If remaining > 0: `BoundedYieldController(epoch, initial_credit, cutoff, remaining, YieldParameters)`. The profile is looked up as `task_yield_profiles['launch:' + '+'.join(sorted request yield classes)]`, where a class looks like `practical_<kind>[_native_*]_<handoff|outputs>` or `compact_<version>`.
- If remaining = 0: an exact-zero YieldController (initial credit must be 0; any nonzero credit raises).
- `require_private_yield` must be true.
- Configuration validates `results_yield_profiles` (keys `native_unbounded_local` / `native_unbounded_hpc`) and `task_yield_profiles` as `{cutoff > 0, parameters}`.

Mapping: the credit has a finite target (remaining handoffs × handoff_unit, and "exact zero future credit" once it is reached), so the fit is **CompletionYieldEstimator(initial_credit, target=remaining)**. Settings come from the task_yield_profile for the request classes. The remaining = 0 case cannot construct that estimator (target must be > 0), so the binding has to decide that case explicitly. One option is to refuse the commission. There must be no fallback.

## What it reports to its parent (`to_parent.py`)

Facts:
- `execution_handoff_refs` and `execution_result_refs`;
- `execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin`;
- `execution_completed`;
- empty native FBA fact sources when FBA is configured;
- the closed-credit snapshot.

`fact_sources` and `resolve` come from library `received_result_readers`. `required_return_sources` returns `('execution_handoff_refs',)` when the parent is `biochemical_feasibility_evidence` and the services hook `annotation_task_required()` is true. The report must equal the recorded facts.

## Differences from sibling / similar episodes

- Its siblings under `hpc_allocation_execution` are `execution_progress_assessment` (monitor) and `execution_result_acquisition` (results).
- Launch is the only one of them that commissions children.
- Its credit counts received handoffs. Its job children count practical receipts instead.
- Its `terminal_execution.py` is a reduced copy: no `instructions` or `decision_context`, used only as the `_practical` per-resource delegate builder in `configuration.py`. The job children's copies carry the execution-agent instructions.

## File-by-file

| Old file | Lines | Own intent | Old-runner names |
|---|---|---|---|
| goal.py | 13 | Launch goal text | `communication.plain` (unused) |
| task_instructions.py | 28 | Composition (above) | `runtime_prompt.INSTRUCTIONS`×4, `REASONING_COMMIT_REQUIREMENT`, `DECISION_EXCHANGE_PROTOCOL`; `self.workflow.job_episodes`, `.is_job_source`, `.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol` |
| task.py | 211 | Action loop plus reason / job_child / contract feedback (above) | Same set as the parent's task.py plus `runtime.AcquisitionError`, `ContractError`, `subprocess`, `sqlite3`, `Mapping`; `self.workflow.automatic_score_updates`, `.retain_shared_grading_results`, `.store.commit_reasoning`; tables `runtime_actions`, `runtime_model_calls`, `runtime_episodes` |
| task_decision.py | 358 | Decision inputs (inlined), exchange protocol, presentation-gated provider call | `providers._ORIGINAL_MODEL_COMPLETE`, `_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION`, `_ORIGINAL_MODEL_INSTANCE_DICT`×2; `self.workflow.shared_information_context`, `.freeze_literature_numerical_contracts`, `.services.instructions`, and others; about 30 `runtime.*` names; `episode_work_report.*` |
| task_state.py | 108 | As parent; failed `tool`/`reason` action recorded | As parent's task_state.py |
| task_suspension.py | 9 | Suspension | `self.workflow.execution_handle`, `.execution_backend` |
| task_presentation.py | 60 | Renderer choice | `decision_context.apply_state_frame`, `VERSION` |
| report_delivery.py | 23 | Finish | As parent's report_delivery.py; table `runtime_forms` |
| internal_summary.py | 80 | Selected execution task, decision context, LaunchDecisionState | `runtime.FACT_*`, `_references_in`, `Mapping`; about 20 `self.workflow.*` names; `self.services.scientific_parent_task`; table `runtime_actions` |
| episode.py | 125 | Binding: roles, children, common actions, child routing | BindingContext.path; old hook names |
| configuration.py | 74 | Resources, credit units, log window, yield profiles, per-resource delegates, progress provider, FBA helpers | `numerical.YieldController`×2, `YieldParameters`×2; `communication.plain` |
| credit.py | 150 | Live and closed operational credit | `EpisodeReturnRecords`, `_same`×6, `EpisodeReceipts`, `knowledge_inheritance`; tables `runtime_episodes`, `runtime_observations`, `runtime_forms`×3, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2 |
| credit_records.py | 3 | `_CLOSED_CREDIT` version | none |
| yield_estimator.py | 61 | Continuation (above) | `numerical.BoundedYieldController`, `YieldController`, `YieldParameters`×2, `YieldEstimate`, `NumericBand`; `practical_yield.PracticalYieldEstimator` |
| completion.py | 76 | Completion proof = a completed action whose record_refs hold a usable handoff matching the context; closed verdict replay | `method_loop.identities.UnitRef`, `numerical.NumericBand`, `practical_yield.ESTIMATOR_VERSION`, `_same`×4; tables `runtime_actions`, `runtime_observations` |
| from_parent.py | 80 | Assignment schema/prepare (above) | `communication.plain` |
| to_parent.py | 36 | Facts/validate | `communication.validate_form`, `plain` |
| to_child_hpc_job_execution.py | 29 | Request envelope | `runtime.EpisodeGoal`, `EpisodeRequest`, `Episode`, `validate_saved_fact_form`; `self.workflow.context`, `.grains`, `.receipts`, `.inprocess_completion_order`, `.launch_instructions`; `knowledge_inheritance` |
| to_child_local_job_execution.py | 29 | Identical copy | Same as above |
| from_child_hpc_job_execution.py | 32 | Receive the child form | `self.workflow.receipts`, `.progress_provider`×4, `.specialist`, `.binding_context`×4, `.episode_bindings`, `.is_job_source`, `.receive_tool_attributions`; `EpisodeReturnRecords`; `delivery_counterpart` |
| from_child_local_job_execution.py | 32 | Identical copy | Same as above |
| context_receipts.py | 33 | required_return_sources, initial_references (flux inputs / handoff / saved sheet) | BindingContext.assignment/role; `self.services.annotation_task_required` |
| handoff_receipts.py | 52 | _context_target, _received (handoffs, result bodies; skips native bundles) | BindingContext.assignment/role/scope |
| input_versions.py | 26 | Input version / flux-balance input checks | `EpisodeReturnRecords._equal` |
| launch_state.py | 24 | initialize; `state()` refuses (no practical state for launch) | BindingContext.assignment/scope |
| resource_information.py | 64 | launch_operation_catalog, resource_tool_contracts | none |
| received_result_records.py | 16 | Result provider/origin/selector and the result op catalog | none |
| terminal_execution.py | 131 | Per-resource practical delegate (reduced copy) | BindingContext.*; `communication.*`; `practical_yield.PracticalYieldEstimator` |
| work_operations.py | 27 | execution.capabilities | none |
| scientific_reference_support.py | 11 | _matches_flux_balance_assignment | BindingContext.assignment |
| action_outcome.py | 5 | Outcome record shape | none |
| binding_record.py | 9 | as_record (execution_episode_v1) | none |
| binding_roles.py | 6 | VERSION, ROLES, KINDS, ROLE_KINDS | none |
| launch_assignment_records.py | 3 | LAUNCH_VERSION | none |
| schema_fields.py | 6 | TEXT/OFFSET/LIMIT/FILE_LIMIT (1 MiB read window) | none |
| initial_information.py | 8 | catalog readers | old catalog protocol |
| received_execution_information.py | 4 | catalog configured/received | old catalog protocol |
| __init__.py | 1 | none | none |

## Carried over

Old files are those of 97308b94c (`execution_job_submission/` without child folders and tests). Every row of `runs/carry_over/functions/a110__biochemical_feasibility_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission.tsv` has one row here.

| old file | name | kind | new place |
|---|---|---|---|
| action_outcome.py | _outcome | machinery | old action outcome envelope (status, record_refs, changed_record_refs, feedback); a tool returns its own outcome dict and a refused answer is Rejected |
| binding_record.py | LaunchBindingRecord | machinery | the binding's own as_record() (execution_episode_v1) |
| binding_record.py | LaunchBindingRecord.as_record | machinery | the binding's own as_record() |
| completion.py | LaunchCompletion | machinery | completion proof of a received usable handoff (practical_completion_v1) and its closed-verdict replay against runtime_actions/runtime_observations; a completion proof is not a controller input (README 5 item 5); the credit counts the handoffs (credit.py) |
| completion.py | LaunchCompletion._proof_for_action | machinery | completion proof read from runtime_actions and the job progress provider |
| completion.py | LaunchCompletion.completion_for_action | machinery | completion proof wrapper |
| completion.py | LaunchCompletion._closed_completion_verdict | machinery | replay of an earlier controller record (runtime_observations, estimator provenance) |
| completion.py | LaunchCompletion.verify_completion | machinery | completion verification for the old PracticalYieldEstimator; replaced by the bounded quality controller (yield_estimator.py) |
| configuration.py | LaunchConfiguration | episode function | settings read where used: task.py (resources, initial_information, coordinator_workspace, directories), yield_estimator.py (task_yield_profiles); the credit units are assignment fields checked in messages/read_from_parent.py read_from_parent. Not carried: job_progress_provider, local_file_sources, flux_balance_inputs/requests, native_flux_balance_results/returns, per-resource TerminalExecutionBehavior delegates (old-runner machinery / result side); results_yield_profiles, log_window_bytes, log_roles (result-side settings, belong to execution_result_acquisition) |
| configuration.py | LaunchConfiguration.__init__ | episode function | see LaunchConfiguration: units -> read_from_parent (positive finite handoff_unit and acquired_record_unit); resources -> task.py _bound and execution_capabilities; initial_information -> task.py execution_capabilities; task_yield_profiles -> yield_estimator.py _task_yield_profile (missing profile raises); require_private_yield, results_yield_profiles, log selection, native flux balance configuration check (validate_flux_balance_bindings), job_progress_provider and the other helpers are not carried |
| context_receipts.py | LaunchContextReceipts | episode function | ftp: RETURN_FORM requires execution_handoff_refs (see required_return_sources); initial_references is machinery |
| context_receipts.py | LaunchContextReceipts.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM: execution_handoff_refs and execution_completed are required fields (the old rule was conditional on an annotation task parent; see contract_misfits) |
| context_receipts.py | LaunchContextReceipts.initial_references | machinery | receipt ledger initial references (flux balance inputs, saved sheet); the records the job inputs name are the record_refs field of the assignment, passed in custody (messages/read_from_parent.py, messages/msg_to_child.py) |
| credit.py | LaunchCredit | episode function | credit.py credit |
| credit.py | LaunchCredit.credit_kind | machinery | credit kind label 'operational' (no credit kinds in the final form) |
| credit.py | LaunchCredit._closed_credit_carrier | machinery | closed-credit snapshot authentication against runtime_episodes/runtime_observations |
| credit.py | LaunchCredit._closed_credit_receipts | machinery | closed-credit receipt prefix pinning (runtime_receipt_inheritance, runtime_record_receipts) |
| credit.py | LaunchCredit._closed_credit_value | machinery | closed-credit snapshot value check |
| credit.py | LaunchCredit._closed_credit_facts | machinery | closed-credit snapshot captured into runtime_forms facts; the system hands the controller credit to final_to_parent |
| credit.py | LaunchCredit._closed_operational_credit_view | machinery | closed-credit snapshot replay (runtime_forms) |
| credit.py | LaunchCredit.project_credit | machinery | selects the closed snapshot or the live projection; only the live projection remains (credit.py credit) |
| credit.py | LaunchCredit._live_project_credit | episode function | credit.py credit (handoff_unit x new distinct resources with a usable handoff + acquired_record_unit x 0; handoffs from the launch children reports in the summary) |
| credit.py | LaunchCredit.credit_view | machinery | credit view wrapper of project_credit |
| episode.py | ExecutionEpisode | episode function | episode.py ExecutionJobSubmission (private binding of EpisodeBinding); decision_source_type, decision_prompt_renderer, received_execution_information*, initial_information_* hooks and the delegated library attributes are old hooks and are not carried |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS (launch_local, launch_hpc) |
| episode.py | ExecutionEpisode.allowed_children | episode function | messages/read_from_parent.py read_from_parent: parent_input[permitted] (slot per permitted request; the old filter by configured resource kind is made by task.py _bound and action) |
| episode.py | ExecutionEpisode.permitted_common_actions | machinery | common action policy (tool, reason, child, wait, redeliver_report); the episode offers units through decide/action only; reason, wait and redeliver_report no longer exist |
| episode.py | ExecutionEpisode.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child (the request is passed through unchanged as the child assignment) |
| episode.py | ExecutionEpisode.execution_child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| episode.py | ExecutionEpisode.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child |
| from_child_hpc_job_execution.py | receive_report | episode function | messages/read_from_child.py read_from_child (the receipt ledger and progress provider calls are system custody) |
| from_child_local_job_execution.py | receive_report | episode function | messages/read_from_child.py read_from_child (copy; the receipt ledger and progress provider calls are system custody) |
| from_parent.py | LaunchFromParent | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LaunchFromParent.child_assignment_schema | machinery | the child's assignment schema shown to the parent (README 5 item 10); the child's own ASSIGNMENT_FORM admits the commission |
| from_parent.py | LaunchFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version, requests, immutable_input_versions, constraints, launch_instructions) |
| from_parent.py | LaunchFromParent._permitted | episode function | messages/read_from_parent.py _permitted |
| from_parent.py | LaunchFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validation of requests, constraints, input versions). Not carried: authenticate_launch (owner ledger of frozen plans), compact flux balance launch preview, flux balance inputs against the immutable input versions and the input versions in scope (Store reads of a commission: a wrong commission fails) |
| from_parent.py | LaunchFromParent._request_schema | episode function | already in library: records/biochemical_feasibility_evidence/practical_execution_records.py validate_assignment (ASSIGNMENT_SCHEMA with the request resource id); the compact flux balance resource_assignment_schema is not carried |
| from_parent.py | LaunchFromParent._launch | episode function | messages/read_from_parent.py read_from_parent, _request, _constraints |
| goal.py | LaunchGoal | episode function | goal.py GOAL |
| goal.py | LaunchGoal.instructions | episode function | goal.py GOAL (text unchanged); task.py decide builds the instructions from it |
| handoff_receipts.py | LaunchHandoffReceipts | machinery | received-handoff reading through the receipts ledger and the job progress provider; replaced by the launch child reports (messages/read_from_child.py, messages/internal_summary.py) |
| handoff_receipts.py | LaunchHandoffReceipts._context_target | machinery | handoff target check against the context assignment (runtime tables, request binding) |
| handoff_receipts.py | LaunchHandoffReceipts._received | machinery | known record references read through the old Store and progress provider; the handoffs are in the summary (messages/internal_summary.py) |
| initial_information.py | initial_information | machinery | old catalog protocol (catalog.readers, resource_information(readers)); the recorded inventory is settings[initial_information], shown by task.py execution_capabilities |
| input_versions.py | LaunchInputVersions | unplaced | see _versions, _flux_balance_inputs — Store-backed validation of the immutable input versions and the flux balance inputs |
| input_versions.py | LaunchInputVersions._versions | unplaced | validate_execution_input_versions — validation of immutable_input_versions through the old execution_input_versions module (no placed home; reads the Store); the shape is checked in messages/read_from_parent.py with INPUT_VERSION_SCHEMA |
| input_versions.py | LaunchInputVersions._flux_balance_inputs | unplaced | flux balance input references — reads the flux balance input binding (old flux_balance_inputs, receipts); the references travel as the record_refs field of the assignment |
| internal_summary.py | LaunchInternalSummary | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | LaunchInternalSummary._with_selected_execution_task | episode function | task.py _selected_execution_task (scientific_task is the assignment field filling services.scientific_parent_task; scientific_job_view has no placed home: the job is shown as the request has it) |
| internal_summary.py | LaunchInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (execution_assignment, execution_progress) and task.py decide; the compact practical_assignment branch is not carried |
| internal_summary.py | LaunchDecisionState | machinery | generic old-runner decision context (working state, pending work, report deliveries, credit binding, annotation axis mode) |
| internal_summary.py | LaunchDecisionState.decision_state | machinery | generic old-runner decision context; the visible pieces are in task.py decide (goal, tools, time_accounting, controller) |
| launch_state.py | LaunchLaunchState | machinery | practical state of an assignment; a launch has none |
| launch_state.py | LaunchLaunchState.initialize | machinery | practical state initialisation (flux balance request binding) |
| launch_state.py | LaunchLaunchState.state | machinery | refused for a launch (no practical state) |
| received_execution_information.py | received_execution_information | machinery | old catalog protocol (catalog.configured / catalog.received) |
| received_result_records.py | native_result_operation_catalog | unplaced | execution.results.status/collect/read operation catalog — result-side operations carried in the launch copy; they belong to execution_result_acquisition |
| report_delivery.py | LaunchReportDelivery | machinery | report finishing through runtime_forms and the release of the Episode; the return is messages/final_to_parent.py final_to_parent |
| report_delivery.py | LaunchReportDelivery.finish | machinery | finish(record): saves the form in runtime_forms and releases; replaced by messages/final_to_parent.py final_to_parent |
| resource_information.py | launch_operation_catalog | episode function | task.py TOOLS execution_capabilities (the one declared launch operation) |
| resource_information.py | LaunchResourceInformation | unplaced | resource_tool_contracts — commissionable launch/results operation contracts per resource |
| resource_information.py | LaunchResourceInformation.resource_tool_contracts | unplaced | resource_tool_contracts — per-resource launch and result operation contracts routed as commissions (shared tool catalog); native flux balance contracts (flux_balance_tool_contracts) have no placed home; the model is shown the resource configuration and inventory by execution_capabilities and the permitted resource ids |
| scientific_reference_support.py | LaunchScientificReferenceSupport | machinery | frozen flux balance assignment matching against the materialized request binding (Store) |
| scientific_reference_support.py | LaunchScientificReferenceSupport._matches_flux_balance_assignment | machinery | frozen flux balance assignment matching (Store, request binding) |
| task.py | LaunchTask | machinery | the old decision machine; task.py decide/action |
| task.py | LaunchTask.next | machinery | old decision loop (restore, replay, source failure): the system loop |
| task.py | LaunchTask.apply_response | episode function | task.py action (the answer selects one commission; reason, wait and redeliver_report actions do not exist; failed tool/reason feedback and ContractError feedback are old-runner paths) |
| task.py | LaunchTask.execute | machinery | executes the selected action through the old runner (tool, child, job_child, reason); the system runs units from decide/action |
| task_decision.py | LaunchTaskDecision | episode function | task.py decide (decision inputs) and machinery (call, exchange) |
| task_decision.py | LaunchTaskDecision.call | episode function | task.py decide: launch_instruction_library, selected_launch_instructions, tool knowledge, selected execution task, estimates; the model-call recording, receipts of decision inputs, restore and literature numerical contract freezing are machinery. Unplaced decision inputs: resource_context, shared_information_context, child_options, completed_action_reports, requested_action_history, execution_expectations, native_execution_expectations |
| task_decision.py | LaunchTaskDecision.instructions | episode function | task.py decide (instructions text) |
| task_decision.py | LaunchTaskDecision.conversation_key | machinery | provider conversation key (sessions) |
| task_decision.py | LaunchTaskDecision.interpretation_context | machinery | decision exchange context |
| task_decision.py | LaunchTaskDecision.exchange_schema | machinery | decision exchange schema |
| task_decision.py | LaunchTaskDecision.exchange_response | machinery | decision exchange response |
| task_decision.py | LaunchTaskDecision.validate_contract_exchange_request | machinery | decision exchange validation |
| task_decision.py | LaunchTaskDecision.validate_contract_exchange_history | machinery | decision exchange history validation |
| task_decision.py | LaunchTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_decision.py | LaunchTaskDecision.decision_completion | machinery | provider call selection (presentation-gated) |
| task_instructions.py | instructions | episode function | task.py decide: GOAL, ACTION_BOUNDARY, HOST_EXECUTION_GUIDANCE, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, ANSWER_INSTRUCTION. Not carried: the reasoning-commit requirement, pending_child_delivery, wait, native-event and decision-exchange paragraphs (actions that no longer exist) |
| task_presentation.py | present_launch_context | unplaced | render_hpc_prompt, render_selected_execution_prompt, render_monitor_prompt, render_receiver_prompt, render_biochemical_feasibility_evidence_prompt — the per-context prompt renderers lived in the old shared root and were not read (README 5 item 16); task.py _task_text writes the episode's own text and the context is sent as a record |
| task_state.py | LaunchTaskState | machinery | task state: restore, checkpoint, effect and failure records |
| task_state.py | LaunchTaskState.__init__ | machinery | task state initialisation |
| task_state.py | LaunchTaskState.bind_execution_context | machinery | execution context binding |
| task_state.py | LaunchTaskState.record_execution_failure | machinery | failed tool/reason action recorded in the old journal |
| task_state.py | LaunchTaskState.restore_checkpoint | machinery | checkpoint restore |
| task_state.py | LaunchTaskState.restore | machinery | restore from the old journal |
| task_state.py | LaunchTaskState.record_effect | machinery | effect recording |
| task_state.py | LaunchTaskState.checkpoint | machinery | checkpoint |
| task_suspension.py | LaunchTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | LaunchTaskSuspension.suspension_changed | machinery | wait/suspension machinery (execution_backend.set_suspension) |
| terminal_execution.py | TerminalExecutionBehavior | episode function | carried by the launch children (hpc_job_execution, local_job_execution): the reduced per-resource practical delegate; the library validator TerminalExecution is called by task.py _bound |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | machinery | delegate construction (state directory, resources by kind) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py _bound (library TerminalExecution(config).validate_assignment) |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | task.py _bound (validate_assignment of each request against its configured resource) |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | practical state directory of the old file-backed state |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | practical state initialisation |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | practical state lookup |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | carried by the launch children (operation_catalog of the resource) |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | carried by the launch children (exec_command tools) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | machinery | completion proof of the practical state |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator over verify_completion (README 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (result-side sources, selectable); the practical sources are the children's |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py _facts (the execution facts); the practical facts are the children's |
| terminal_execution.py | TerminalExecutionBehavior.resolve | machinery | reference resolution of the old runner (receipt resolver) |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | machinery | credit view of the practical state; the children carry it |
| to_child_hpc_job_execution.py | assemble_request | episode function | messages/msg_to_child.py msg_to_child (slot launch_hpc: the request is the assignment, selection of execution_handoff_refs and execution_completed); the request envelope (EpisodeGoal, EpisodeRequest, report-contract declaration, receipt binding, inprocess completion order) is old-runner machinery |
| to_child_local_job_execution.py | assemble_request | episode function | messages/msg_to_child.py msg_to_child (slot launch_local, copy; adds record_refs and scientific_task); the request envelope is old-runner machinery |
| to_parent.py | LaunchToParent | episode function | messages/final_to_parent.py RETURN_FORM and final_to_parent |
| to_parent.py | LaunchToParent.facts | episode function | messages/final_to_parent.py final_to_parent (the closed-credit facts are machinery) |
| to_parent.py | LaunchToParent._live_facts | episode function | messages/final_to_parent.py _facts (execution_handoff_refs, execution_completed, and the empty result sources; execution_result_origin raises; the flux balance fact sources have no placed home) |
| to_parent.py | LaunchToParent.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; then raises NotImplementedError validate_form_not_built:biochemical_feasibility); the flux balance adapter check applied only when an adapter was configured |
| work_operations.py | LaunchWorkOperations | episode function | task.py execution_capabilities |
| work_operations.py | LaunchWorkOperations.catalog | episode function | task.py TOOLS (execution_capabilities) |
| work_operations.py | LaunchWorkOperations.execute | episode function | task.py execution_capabilities (the invalid-argument outcome envelope _outcome is machinery) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (private copy; library candidate) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (require private yield switch not carried) |
| yield_estimator.py | ExecutionEpisodeYield._launch_yield_controller | episode function | yield_estimator.py yield_controller (BoundedQualityYieldController, maximum = new requests x handoff_unit; the exact-zero estimator no_remaining_requests is not carried) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator(verify_completion) (README 7b); not a controller input |
