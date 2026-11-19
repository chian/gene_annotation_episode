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
