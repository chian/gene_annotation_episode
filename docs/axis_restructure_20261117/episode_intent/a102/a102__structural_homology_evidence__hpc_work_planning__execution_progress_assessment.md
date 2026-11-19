# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/execution_progress_assessment`

Source: this episode's own files at commit `97308b94c` (24 Python files, 1,237 lines, directly in the folder; its
`tests/` folder was not read). Old role name: `monitor`. Old class: `MonitorEpisode`, task class
`ProgressMonitoringTask`. Old `binding_path`: `structural_homology_evidence/hpc_work_planning/execution_progress_assessment`;
old `commissioning_parent`: `structural_homology_evidence/hpc_work_planning`.

## What this episode is for

It finds out which further exposed progress information about one assigned execution target is useful, and returns
what was actually observed. Its goal text, verbatim from `goal.py`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
> elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
> outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor
> for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the
> original parent's typed form at your closure even while the target remains active. Do not report private
> reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not
> poll or compose another report with a model. *(credit sentence, below)* Repeated observation identities and read
> timestamps alone earn no new information.

The credit sentence is one of two, chosen by configuration:

- own yield configured: "The monitor's information-credit projector and bound yield rule govern continuation."
- otherwise: "The caller's monitoring projector and configured controller own credit and continuation."

Its planning context adds: unresolved question "Which exposed progress information would improve the original
requested report?" and progress definition "Actual received information under the caller-bound monitoring
projector; repeated identities and timestamps alone earn no credit."

## Task and instructions

One unit is one model-selected action: a tool call, a child monitor commission, a wait, or a report redelivery.
There is no reasoning-commit action. Each model response carries `selection` and `report_update`; the report update
is the model's interpretation of the state before the selected action.

The instructions are the goal text followed by named text blocks kept in `task_instructions.py` (this is the only
one of the four episodes in this note that keeps them as named constants):

| Block | Content |
|---|---|
| `ACTION_BOUNDARY` | No stop action; do not invent a turn budget, approval review, quality gate, experiment, term or observation. |
| `CREDIT_COMPONENT_GUIDANCE` | `current_evidence_vector` holds the projector's components; they describe the progress proxy, not biological truth. |
| `RESOURCE_ESTIMATE_GUIDANCE` | `resource_tool_estimates` are expectations; a timing experiment earns monitoring credit for timing information learned; job elapsed time and the duration of an own monitoring action are distinct. |
| `REPORT_GUIDANCE` | Return only the parent's typed form; fill `report_update` in the same response; report repair uses `redeliver_report`, never a recommission. |
| `HISTORY_GUIDANCE` / `EXCHANGE_HISTORY_GUIDANCE` | How to read its own earlier decisions (one or the other, by decision protocol). |
| `HOST_EXECUTION_GUIDANCE` | Do not execute native provider tools; the host executes the selected action. |
| `REPAIR_GUIDANCE` | When `pending_child_delivery` is supplied, select `redeliver_report` with a corrected form. |
| `WAIT_GUIDANCE`, `NATIVE_EVENT_GUIDANCE` | Only when wait is permitted: how to wait on a pending child handle; what a native event target means. |

Tool-knowledge and launch-instruction library text are appended when those inputs are present.

## What it reads from its parent's assignment

Form `monitor_assignment_v1` (`contracts.py`), every field required:

| Field | Meaning | Check on admission |
|---|---|---|
| `target_handle` | The one execution target to observe | Must be an execution handle inside the assigned scope |
| `requested_fields` | Subset of `execution_status`, `measurements`, `log_windows`, `committed_record_refs`, `dependencies`, `result_available` | An observation may never request a field outside this set |
| `known_progress_refs` | Progress observations the parent already holds | Each must be a readable observation of the same target |
| `permitted_committed_record_types` | Record types whose committed records may be delivered | Limits what records are returned and may be cited |

It also reads the parent's report contract (requested form and purpose) and the initial report values.

## Children

One child slot, and the child is itself (self-nesting): `monitor`.

- **When allowed:** only when the assigned target exposes at least one direct dependency.
- **What it sends:** a `monitor_assignment_v1` whose `target_handle` is one of the exposed direct dependencies and
  whose permitted record types are not wider than its own (`to_child_execution_progress_assessment.py`). No
  descendant traversal, fan-out, cadence or depth is prescribed.
- **What it takes back:** the child's typed form; every `episode_progress` reference in it is read in scope and
  recorded as received progress under a content signature (`from_child_execution_progress_assessment.py`). These
  references then count as its own received progress.

## Decision state and what the model sees

State kept per episode: call count, last outcome and its index, feedback, current report values and their basis
references, plus restore/checkpoint fields of the old runner.

Shown at each decision (`decision_state.py`, `internal_summary.py`, `decision_inputs.py`): goal; scope; working
state; visible record references; current credit and evidence vector; the credit rule; an elapsed-time view;
pending work; last outcome and feedback; report delivery status; controller state; tools; tool knowledge; report
facts on offer; the parent's requested form and purpose; current report update and its basis; the assignment; the
target description; the target's direct dependencies; received progress references; the note "Exposed direct
relationships and already delivered observations. Empty measurements/log windows do not assert absence or a
stall."; the planning context; execution expectations for role `monitor`; resource estimates; waiting support.

## Tools

| Tool | What it does |
|---|---|
| `progress.observe` | Observe selected exposed fields of the assigned target once; keeps the original observation identity when facts are unchanged; never traverses dependent work. Accepts `requested_fields` and, when the target declares one, a `native_operation`. |
| `progress.read` | Read an already delivered exact progress observation (`progress_ref`). |
| `progress.log` | Read one exact retained log window from a delivered observation (`progress_ref`, `log_index`), preserving source and artifact byte custody. |

A contract error becomes an `invalid` outcome with feedback and still enters the iterator.

## Credit

Credit kind `monitoring`. Credit is information actually received: the number of newly informative received
snapshots times `information_unit` (`ProgressInformationCredit`, estimator note
`newly_informative_received_snapshot_count_times_information_unit`). Repeated observation identities and read
timestamps earn nothing. Without its own yield configured, credit is whatever the caller-bound monitoring
projector returns (`services.bound_role_credit`). Credit may not decrease (`monitor_information_credit_cannot_decrease`).

## Continuation

Estimator: **accumulation** (old `estimate_nonnegative_yield`, labelled `monitor_information_accumulation_v1`):
forecast the next monitor action's information credit; stop when the predicted upper gain is at or below the
monitor's cutoff.

Settings (`configuration.py`): `yield_settings` = exactly `{kind: 'information_accumulation', cutoff >= 0,
uncertainty_alpha in (0, 1)}` and `information_unit > 0`; `outcome_page_size` (default 32). When `yield_settings`
is absent the old code raises `monitor_private_yield_binding_not_enabled` and leaves continuation to the caller's
controller.

## What it reports to its parent

The parent's typed form, built once at closure from saved observations and the last admitted interpretation; no
polling and no model call at closure. Facts it can fill (`to_parent.py`):

| Fact | Meaning |
|---|---|
| `monitoring_progress_refs` | Delivered progress observation identities, including admitted child updates |
| `monitoring_target_handle` | The assigned target handle |
| `monitoring_execution_state` | `pending`, `executing`, `returned`, `admitted`, or unknown, from the latest observation of the target |
| `monitoring_result_available` | Result availability in the latest observation |
| `monitoring_observed_at_unix_seconds` | Original observation time, not refreshed |
| `monitoring_committed_record_refs` | Parent-permitted committed records actually delivered |
| `monitoring_dependency_handles` | Exposed direct dependencies in the latest observation; no descendant traversal |

A report field declared from one of these facts must equal the recorded fact; a cited record must be of a
permitted type and actually received.

## Differences from similar episodes

- A second copy of this episode exists at
  `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`. By blob hash, 22 of 24 files are
  identical; only `binding_record.py` and `episode.py` differ (not read here; another agent has that folder).
- Unlike `execution_result_acquisition` and `execution_job_submission`: it has no reasoning-commit action, no
  completion proof, no closed-credit custody, its credit kind is `monitoring` rather than `operational`, it may be
  a run entry (`entry_roles = ('monitor',)`), and it is the only one that commissions itself.
- Its `task_decision.py` and `decision_state.py` carry an `annotation_axis_credit` branch that belongs to the root
  episode, not to a monitor.

## Old support modules this episode imports

Where each imported old module is now (looked up in `runs/placement_plan/placement.tsv` and by file name under
`episode_support/`; the modules themselves were not read):

| Old module (`root.a102.`...) | Files importing it | Home now |
|---|---|---|
| `communication` | 8 | no structural_homology_evidence copy found (same-named copies exist for seven other axes under episode_support/forms/AXIS/; top-level method_loop/communication.py exists) |
| `domain` | 8 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 2 | the deleted old per-axis binding table |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `library.action_contracts` | 1 | no placed home found |
| `library.monitor_prompt` | 1 | no placed home found |
| `library.private_policy_call` | 2 | no placed home found |
| `library.progress_information_credit` | 1 | episode_support/grading/structural_homology_evidence/progress_information_credit.py |
| `library.report_fact_assembly` | 1 | no placed home found |
| `method_loop.durable` | 1 | top-level method_loop/durable.py (the only method_loop) |
| `numerical` | 1 | old yield code; its names NumericBand, YieldParameters, YieldEstimate, estimate_nonnegative_yield, estimate_bounded_credit_yield are now in top-level yield_control; YieldController/BoundedYieldController are not (controllers there are Accumulation/BoundedQuality/Completion) |
| `providers` | 1 | gene_annotation_episode/model_provider.py (defines ModelCallError) |
| `runtime` | 6 | the deleted old per-axis runner |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow` and a `workflow` argument;
"BindingContext fields" are attribute reads on the old context object (`context`, `parent`, `child`); "old-runner
callbacks defined" are methods the old runner called on the binding or task. The same rows, one per name and file,
are in `runs/carry_over/calls/a102_04.tsv` (540 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 1 | Nothing (package marker). | none |
| `binding_record.py` | 9 | Its configuration record: outcome page size, and the information unit and yield settings when its own yield is configured. | **old-runner callbacks defined**: `as_record` |
| `configuration.py` | 31 | Settings and their checks: `outcome_page_size` (default 32, positive integer); optional `yield_settings` = exactly {kind: 'information_accumulation', cutoff >= 0, uncertainty_alpha in (0,1)} which then requires `information_unit` > 0; role must be `monitor`. | **imports from old `root.a102`**: `communication` |
| `contracts.py` | 10 | The assignment form (`monitor_assignment_v1`: target_handle, requested_fields, known_progress_refs, permitted_committed_record_types), the six observable fields and the four lifecycle states. | **imports from old `root.a102`**: `domain` |
| `credit.py` | 21 | Credit kind `monitoring`; credit is the caller-bound projector's view, or `ProgressInformationCredit` (newly informative received snapshots times the information unit). | **BindingContext fields**: `role`; **imports from old `root.a102`**: `library.progress_information_credit`; **old-runner callbacks defined**: `credit_kind`, `credit_view`; **self.services**: `bound_role_credit`; **old yield names**: `ProgressInformationCredit`×2 |
| `decision_inputs.py` | 49 | What is added to each decision: resource context, launch-instruction library and selected instructions, child options, completed-action reports, pending work, execution expectations for role `monitor`, resource/native estimates, waiting support. No `requested_action_history` and no shared-information context (unlike the results/launch/allocation episodes). | **imports from old `root.a102`**: `episode_work_report`, `runtime`×2; **old-runner callbacks defined**: `decision_inputs`; **old runtime**: `child_option_information`, `Mapping`; **self.workflow**: `available_child_roles`, `binding_context`, `episode_bindings`, `execution_expectations`, `launch_instructions`×2, `native_estimation_context`, `pending_work`, `permits_common_action`, `resource_context`, `resource_estimator`×4, `waiting_support` |
| `decision_state.py` | 44 | What the model is shown: goal, scope, working state, visible record refs, current credit, evidence vector, credit rule, elapsed-time view, pending work, last outcome and feedback, visual evidence, report deliveries, controller state, tools, tool knowledge, report facts on offer, the parent's requested form and purpose, current report update and its basis, plus `monitoring_information_credit` and its binding when present. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `decision_state`; **old runtime**: `FACT_MEANINGS`, `FACT_SOURCES`, `json`×2, `Mapping`×3, `_plain`×2, `_references_in`; **self.workflow**: `binding_context`, `catalog`, `controller_binding`, `delivery_status`, `extra_report_sources`, `job_episode_options`, `journal`×3, `knowledge`, `local_outcome_preview`, `pending_work`, `receipt_projection`, `run_id`, `source_credit_binding`, `source_credit_view`, `specialist`, `store`×3, `tools`, `working_state`; **journal/receipt tables**: `runtime_actions`×2 |
| `episode.py` | 53 | The binding itself: path, parent, role `monitor`, entry role `monitor`; it may commission another `monitor` (itself) only when the target exposes direct dependencies; permitted actions tool, child, wait, redeliver_report; return source `monitoring_progress_refs` required when the axis head is the parent and requires it; monitor prompt renderer. | **BindingContext fields**: `assignment`, `path`, `role`×2, `scope`×2; **imports from old `root.a102`**: `communication`, `library.monitor_prompt`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `roles`; **old-runner callbacks defined**: `allowed_children`, `child_roles`, `permitted_common_actions`, `prepare_child_request`, `receive_child_progress`, `required_return_sources`; **self.services**: `annotation_task_required`, `dependencies` |
| `from_child_execution_progress_assessment.py` | 20 | Admits a child monitor's typed form: every `episode_progress` reference in it is read in scope and recorded as received progress under a content signature and operation key. | **BindingContext fields**: `episode_id`×3, `scope`×2; **imports from old `root.a102`**: `communication`, `domain`, `method_loop.durable` |
| `from_parent.py` | 33 | Admission of the parent's assignment: target handle must be an execution handle in scope; every known progress ref must belong to that target; a monitor parent's request must be a direct dependency with no wider record types. | **BindingContext fields**: `role`; **imports from old `root.a102`**: `communication`, `domain`; **old-runner callbacks defined**: `assignment_schema`, `prepare_assignment`; **self.services**: `read_progress`, `reference_in_scope` |
| `goal.py` | 15 | The goal text and the planning context (objective, target, requested fields, unresolved question, progress definition, yield settings). The credit sentence switches on whether its own yield is configured. | **BindingContext fields**: `assignment`, `request`, `role`, `scope`; **imports from old `root.a102`**: `communication`; **old-runner callbacks defined**: `instructions`, `planning_context` |
| `internal_summary.py` | 13 | Per-decision summary: the assignment, target description, direct dependencies, received progress refs, and the meaning note that empty measurements do not assert absence or a stall. | **BindingContext fields**: `assignment`, `role`, `scope`×3; **imports from old `root.a102`**: `communication`; **old-runner callbacks defined**: `decision_context`; **self.services**: `dependencies`, `describe_progress_target` |
| `progress_operations.py` | 58 | The three tools (`progress.observe`, `progress.read`, `progress.log`), their schemas and execution, including the optional `native_operation` field taken from the target's own observation schema; contract errors become an `invalid` outcome with feedback. | **BindingContext fields**: `assignment`×2, `role`, `scope`×4; **imports from old `root.a102`**: `communication`, `domain`, `episode_bindings`; **old-runner callbacks defined**: `catalog`, `execute`; **self.services**: `describe_progress_target`, `execute_tool`, `observe_progress`, `read_record`×2 |
| `progress_records.py` | 16 | UTC timestamp parsing and order-preserving de-duplication. | **imports from old `root.a102`**: `domain` |
| `received_progress.py` | 30 | What counts as received progress: assignment-known refs, refs from its own recorded outcomes (paged), and refs received from children; a snapshot may be read only if received. | **BindingContext fields**: `assignment`, `episode_id`×2, `scope`×2; **imports from old `root.a102`**: `domain`; **self.services**: `own_outcomes`, `progress_selection`, `read_progress`, `received_progress_refs` |
| `report_delivery.py` | 25 | Closure: without a report contract return credit, pending handles and current report facts; otherwise build the typed form once from saved facts and the last interpretation, save it, release the episode. | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `task.py` | 182 | The decision loop: replay recorded units, ask the model, admit the response (rejections create no unit), admit the report update, execute tool or wait actions, record result and credit. Report grain name `monitor`. No reasoning-commit action. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`, `providers`, `runtime`×2; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `ActionFailure`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×2, `EventTargetError`×2, `inspect`, `_json`×5, `json`×8, `nullcontext`×5, `observes_action_outcome`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `validate_form`, `ValidationError`×2, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `completed_unit`×3, `completions`×3, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `execute`, `execution_binding`×7, `inprocess_replay`×4, `journal`×7, `last_observed_credit`, `next_return`, `pending_work`, `perform_selected_wait`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `run_id`×2, `selected`×3, `source_credit_view`, `store`×7, `validate_report`; **journal/receipt tables**: `runtime_actions`×8, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_decision.py` | 299 | The model call and the request_context/select_action exchange; includes the `annotation_axis_credit` branch for the yield table (carried from a root-level copy; a monitor never has that credit mode). | **imports from old `root.a102`**: `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `call`, `complete_decision`, `conversation_key`, `exchange_decision`, `exchange_response`, `exchange_schema`, `instructions`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old provider interface**: `complete_with_presentation`, `has_session`×3, `prompt_renderer`; **old runtime**: `_action_generation_schema`×2, `apply_state_frame`, `_ASSIGNMENT_TRANSPORT`, `_category_yield_parameters`, `child_option_information`, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`×2, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `Draft202012Validator`, `instructional_model_context`×4, `is_contract_information`, `_json`×14, `json`×3, `lookup_attempts`, `Mapping`×3, `model_snapshot`×2, `_object`×3, `_plain`×2, `_recorded_action_generation_schema`, `_recorded_assignment_transport`, `_references_in`, `requested_contract_information`×2, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×5, `WorkflowError`×14, `yield_table`; **self.workflow**: `contract_information_profile`, `contract_information_reply`, `controller_binding`, `decision_exchanges`×4, `decision_protocol`×3, `execute`, `freeze_contract_information`, `history_preview`, `journal`×3, `numerical_contracts`, `provider`×3, `receipts`×4, `run_id`, `services`×2, `specialist`, `store`×2, `uses_received_record_context`×2, `validate_contract_information`×5; **journal/receipt tables**: `runtime_model_calls`×8; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `task_instructions.py` | 86 | The instruction text: goal, then action boundary, credit-component, resource-estimate, report, history, host-execution, repair, wait and native-event guidance. This episode is the only one of the four that keeps these as named text blocks. | **old-runner callbacks defined**: `instructions`; **self.workflow**: `binding_context`, `decision_protocol`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`, `specialist` |
| `task_state.py` | 108 | Per-episode decision state fields and their restore/checkpoint; failure of a selected tool or reason action is recorded as a failed outcome that still enters the iterator with its credit. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `to_child_execution_progress_assessment.py` | 11 | The rule for commissioning a child monitor: target must be an exposed direct dependency; permitted record types may not widen. | **BindingContext fields**: `assignment`, `scope`×2; **imports from old `root.a102`**: `domain`; **self.services**: `dependencies` |
| `to_parent.py` | 91 | The seven report facts (progress refs, target handle, execution state, result availability, observation time, committed record refs, dependency handles), reference resolution, and report validation (recorded facts must match; only permitted and received records may be cited). | **BindingContext fields**: `assignment`×3, `role`×2, `scope`×6; **imports from old `root.a102`**: `communication`, `domain`, `episode_bindings`; **old-runner callbacks defined**: `facts`, `fact_sources`, `resolve`, `validate_report`; **self.services**: `read_progress`×3, `read_record`×2 |
| `waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `yield_estimator.py` | 23 | Continuation: accumulation of information credit (`estimate_nonnegative_yield`), credit may never decrease, stops when the predicted upper gain is at or below the monitor's cutoff; raises when its own yield is not configured. | **BindingContext fields**: `role`; **imports from old `root.a102`**: `numerical`×2; **old-runner callbacks defined**: `yield_controller`; **old yield names**: `estimate_nonnegative_yield`×2, `YieldController`×2, `YieldParameters`×2 |

## Carried over

Old files read at `97308b94c` through `git show` (the repository's `.git` is in `gene_annotation_episode_disk`). The finished same-axis copy `hpc_allocation_execution/execution_progress_assessment` was used for the shape of the files (private copy: nothing is imported from it). Library functions called: `ProgressInformationCredit` (`episode_support/grading/structural_homology_evidence/progress_information_credit.py`), `LaunchInstructions`, `ToolKnowledge`, `extend_context`, `rejection_feedback`, `strict_output_schema`/`decode_strict_output`, `time_accounting`, `RECORD_SCHEMAS` (domain). Nothing was added to `episode_support/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e: configuration record of the old binding); not carried |
| binding_record.py | MonitorBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3e: configuration record of the old binding); not carried |
| configuration.py | MonitorConfiguration | episode function | settings and assignment field (see MonitorConfiguration.__init__) |
| configuration.py | MonitorConfiguration.__init__ | episode function | settings checks: `yield_estimator.py yield_controller` (cutoff -> settings['cost'], uncertainty_alpha -> settings['parameters'], error codes monitor_information_yield_values_invalid / monitor_private_yield_binding_not_enabled); information_unit -> new assignment field `information_unit` (`messages/read_from_parent.py`); `outcome_page_size` dropped (every outcome is in the view) |
| configuration.py | MonitorConfiguration._role | machinery | role check: each role is its own episode now (README 3a, BindingContext `.role`) |
| credit.py | MonitorEpisodeCredit | episode function | `credit.py` |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | machinery | `services.bound_role_credit` caller-bound projector: the episode owns its credit now; `credit.py credit` |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | `credit.py information_projection` / `credit` (library projector `ProgressInformationCredit` in episode_support/grading/structural_homology_evidence/progress_information_credit.py, called with a reader over the summary's snapshots) |
| decision_inputs.py | MonitorDecisionInputs | episode function | `task.py decide` (context of the model request: launch-instruction and tool-knowledge library contexts via episode_support/instructions/launch_instructions.py and tools/tool_knowledge.py, `extend_context`); resource_context, execution_expectations, resource_tool_estimates, native expectations, waiting_support, child_options, completed_action_reports, pending_work, contract_information_profile are old-runner state or services not provided (carry_over_blocked file) |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | `task.py decide` (context of the model request: launch-instruction and tool-knowledge library contexts via episode_support/instructions/launch_instructions.py and tools/tool_knowledge.py, `extend_context`); resource_context, execution_expectations, resource_tool_estimates, native expectations, waiting_support, child_options, completed_action_reports, pending_work, contract_information_profile are old-runner state or services not provided (carry_over_blocked file) |
| decision_state.py | MonitorDecisionState | episode function | `messages/internal_summary.py internal_summary` (fields that come from the view) and `task.py decide` (what the model is shown); `runtime_actions` visual-evidence read, report deliveries, pending work, report lifecycle, annotation_axis_credit branch and journal reads are old-runner machinery and not carried |
| decision_state.py | MonitorDecisionState.decision_state | episode function | `messages/internal_summary.py internal_summary` (fields that come from the view) and `task.py decide` (what the model is shown); `runtime_actions` visual-evidence read, report deliveries, pending work, report lifecycle, annotation_axis_credit branch and journal reads are old-runner machinery and not carried |
| episode.py | MonitorEpisode | episode function | `episode.py ExecutionProgressAssessment(EpisodeBinding)` |
| episode.py | MonitorEpisode.child_roles | episode function | `task.py CHILD_SLOTS = {'monitor': BINDING_PATH}` |
| episode.py | MonitorEpisode.required_return_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (monitoring_progress_refs is selectable; the parent selects it in its msg_to_child; the axis-head rule belongs to that parent) |
| episode.py | MonitorEpisode.permitted_common_actions | machinery | permitted_common_actions: wait and redeliver_report actions are gone (README 3b); tool and child are `decide`/`action` |
| episode.py | MonitorEpisode.allowed_children | episode function | `task.py selection_schema` (monitor_dependency offered only while the target exposes direct dependencies) and `messages/msg_to_child.py` |
| episode.py | MonitorEpisode.prepare_child_request | episode function | `messages/msg_to_child.py msg_to_child` |
| episode.py | MonitorEpisode.receive_child_progress | episode function | `messages/read_from_child.py read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | `messages/read_from_child.py read_from_child` (each delivered ref must be a readable observation: the snapshot rides in the child's return); recording under operation key and content signature (provider._receive_progress) is the system's |
| from_parent.py | MonitorAssignment | episode function | `messages/read_from_parent.py read_from_parent`; the monitor-parent branch (prepare_dependency_request) is in `messages/msg_to_child.py` |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM` |
| from_parent.py | MonitorAssignment._assignment | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM` (schema admission); target/known-ref admission against the progress provider is not carried (no services in read_from_parent): UNPLACED, see blocked file |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM` (schema admission); target/known-ref admission against the progress provider is not carried (no services in read_from_parent): UNPLACED, see blocked file |
| goal.py | MonitorGoal | episode function | `messages/internal_summary.py` `monitor_goal` (planning context) |
| goal.py | MonitorGoal.instructions | episode function | `goal.py GOAL` (own-yield sentence) and `task.py instructions` |
| goal.py | MonitorGoal.planning_context | episode function | `messages/internal_summary.py` `monitor_goal` (planning context) |
| internal_summary.py | MonitorSummary | episode function | `messages/internal_summary.py internal_summary` (target description and dependencies come from `task.py decide` / the snapshot) |
| internal_summary.py | MonitorSummary.decision_context | episode function | `messages/internal_summary.py internal_summary` (target description and dependencies come from `task.py decide` / the snapshot) |
| progress_operations.py | ProgressOperations | episode function | `task.py progress_observe`, `progress_read`, `progress_log`, `_delivered`, `_invalid` (log window read through ctx.store.open_artifact); `source.read` registry call: own few lines, see blocked file |
| progress_operations.py | ProgressOperations.catalog | episode function | `task.py CATALOG` (tools progress_observe, progress_read, progress_log; the native_operation property is not carried) |
| progress_operations.py | ProgressOperations.execute | episode function | `task.py progress_observe`, `progress_read`, `progress_log`, `_delivered`, `_invalid` (log window read through ctx.store.open_artifact); `source.read` registry call: own few lines, see blocked file |
| progress_records.py | _timestamp | episode function | `messages/final_to_parent.py _timestamp_seconds` (private copy) |
| progress_records.py | _unique | episode function | `messages/internal_summary.py _unique` (private copy) |
| received_progress.py | ReceivedProgress | episode function | `messages/internal_summary.py internal_summary` (own progress refs from `view.outcomes`; no paging) |
| received_progress.py | ReceivedProgress._received | episode function | `messages/internal_summary.py internal_summary` (received = known refs + own outcomes' progress_refs, de-duplicated; children's refs are in the child unit outcomes) |
| received_progress.py | ReceivedProgress._snapshot | episode function | `task.py action/_tool_call` (a snapshot is read only when its ref was received) |
| received_progress.py | OwnProgress | episode function | `messages/internal_summary.py internal_summary` (own progress refs from `view.outcomes`; no paging) |
| received_progress.py | OwnProgress._own_progress_refs | episode function | `messages/internal_summary.py internal_summary` (own progress refs from `view.outcomes`; no paging) |
| report_delivery.py | MonitorReportDelivery | episode function | `messages/final_to_parent.py final_to_parent` (facts from saved delivered observations, no polling, no model call); runtime_forms save, form_with_facts, release and the no-contract return are old-runner machinery |
| report_delivery.py | MonitorReportDelivery.finish | episode function | `messages/final_to_parent.py final_to_parent` (facts from saved delivered observations, no polling, no model call); runtime_forms save, form_with_facts, release and the no-contract return are old-runner machinery |
| task.py | ProgressMonitoringTask | machinery | task class (ProgressMonitoringTask): decision machine; replaced by `decide`/`action`/tools |
| task.py | ProgressMonitoringTask.next | machinery | decision loop `next`: replay/restore, runtime_episodes/inprocess_replay, source_failed end; the loop is the system's (`decide`) |
| task.py | ProgressMonitoringTask.apply_response | episode function | `task.py action` (decode and validate the model answer, Rejected on error); report_update admission, journal reads and record_effect are not carried |
| task.py | ProgressMonitoringTask.execute | episode function | `task.py TOOLS` and `action` return a ToolCall or ChildCall; runtime_actions saves, wait branch, controller_value, observes_action_outcome and receive_outcome are old-runner machinery |
| task_decision.py | MonitorTaskDecision | machinery | decision machine class: replaced by `decide`/`action` |
| task_decision.py | MonitorTaskDecision.call | episode function | `task.py decide` (the model request: instructions, context, output schema); runtime_model_calls, saved-request checks, sessions, request_context exchange are machinery |
| task_decision.py | MonitorTaskDecision.instructions | episode function | `task.py instructions` |
| task_decision.py | MonitorTaskDecision.complete_decision | machinery | model call (`provider.complete`, prompt renderer): the system calls the provider for a ModelRequest |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | conversation state: deleted (README 3a) |
| task_decision.py | MonitorTaskDecision.interpretation_context | machinery | request_context exchange (decision-exchange loop): not carried |
| task_decision.py | MonitorTaskDecision.exchange_schema | machinery | decision-exchange loop (request_context / select_action): not carried (a lookup is a tool) |
| task_decision.py | MonitorTaskDecision.exchange_response | machinery | decision-exchange loop (request_context / select_action): not carried (a lookup is a tool) |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision exchange: deleted (the system compares a rebuilt request with its record on resume) |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision exchange: deleted (the system compares a rebuilt request with its record on resume) |
| task_decision.py | MonitorTaskDecision.exchange_decision | machinery | decision-exchange loop (request_context / select_action): not carried (a lookup is a tool) |
| task_instructions.py | instructions | episode function | `task.py instructions` and the constants ACTION_BOUNDARY, CREDIT_COMPONENT_GUIDANCE, HOST_EXECUTION_GUIDANCE (private copy); REPORT/HISTORY/EXCHANGE_HISTORY/REPAIR/WAIT/NATIVE_EVENT/RESOURCE_ESTIMATE guidance describe actions or inputs that are gone and are not carried |
| task_state.py | MonitorTaskState | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.__init__ | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.restore | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.record_effect | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| task_state.py | MonitorTaskState.checkpoint | machinery | per-episode state and restore/checkpoint/record_effect/record_execution_failure (README 3e, 3a: failure is a tool outcome; the state is the view) |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | `messages/msg_to_child.py msg_to_child` (errors monitor_child_target_not_exposed_direct_dependency and monitor_child_expands_permitted_record_types kept) |
| to_parent.py | MonitorReport | episode function | `messages/final_to_parent.py` |
| to_parent.py | MonitorReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (seven monitoring facts, selectable, plus monitoring_progress_snapshots) |
| to_parent.py | MonitorReport.facts | episode function | `messages/final_to_parent.py monitor_facts` and `final_to_parent` |
| to_parent.py | MonitorReport.resolve | machinery | reference resolver for form validation (the old receipts/resolver): the system admits the result exactly and requires custody of returned records |
| to_parent.py | MonitorReport.validate_report | episode function | `messages/final_to_parent.py validate_report` (fact comparison, received refs, execution state); validate_form step raises NotImplementedError('validate_form_not_built:A102'); permitted-record visit not carried (committed refs are filtered in the summary) |
| waiting.py | MonitorWaiting | machinery | wait/suspension machinery (suspension_changed): not carried |
| waiting.py | MonitorWaiting.suspension_changed | machinery | wait/suspension machinery (suspension_changed): not carried |
| yield_estimator.py | _monitor_information_yield | episode function | controller choice: accumulation (README 7b); the decreasing-credit raise is in `credit.py credit` (monitor_information_credit_cannot_decrease) |
| yield_estimator.py | MonitorEpisodeYield | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
