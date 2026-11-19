# resource_work_submission (A102)

Episode path: `root/a102/structural_homology_evidence/resource_work_submission`. Source: the episode's own files at `97308b94c` (35 Python files, about 1,500 lines; it has no `grading/` or `scoring/` subfolder, and its child folders are not covered here). Old role: `launch`. Old class: `ResourceEpisode`. It is commissioned by `structural_homology_evidence`.

## What it is for (goal, in its own words)

> Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

When a contract information profile is configured, the goal also says:

> Within the pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level form field with only $ref set to episode-fact:<source> to have the host expand and fill that type. Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original job_ref and receiving state allows later work to repair that job without submitting a replacement.

Of the three resource episodes, this is the only one whose `contract_information_profile()` returns its configured profile.

## Task and instructions

- `instructions.py` builds the instructions in this order: the old default runtime `INSTRUCTIONS`; the goal text above (appended); `REASONING_COMMIT_REQUIREMENT`; tool-knowledge instructions; launch-instruction-library instructions; the text for repairing a pending child delivery with `redeliver_report`; the wait text (a `pending_child_` handle with event `returned`, `after_cursor` 0 and `reconsider_at` null; waiting reports readiness only and earns no credit); the native-event-target text (a registration is not proof of submission); and, under the exchange protocol, replacement history guidance that says to use `request_context` and `episode.history`.
- `task.py`, `task_decision.py`, `decision_*.py`, `saved_decision_exchange.py` and `task_state.py` hold the iteration source in the old runner's form: replay, the model call, response admission, execution, credit and checkpoints. Its intent is the generic one. A `reason` commit with every field empty is rejected (`empty_reasoning_commit`). A returned invalid or failed action still enters the iterator with its credit (`record_execution_failure`). A malformed action gets typed repair feedback (`action_contract_feedback.py`), is recorded as `rejected`, and acquires no unit.
- Permitted common actions are `tool`, `reason`, `child`, `wait` and `redeliver_report`.

## Decision state and what it shows the model

The generic state (`decision_context.py`) contains: goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector, investigation_progress (with receipt projection), credit_binding, time_accounting, pending_work, last_local_outcome and feedback, visual_evidence, report_deliveries, controller state and binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose and requested_form, current_report_update and its basis, and the report_lifecycle text. Under annotation-axis credit, working_state is emptied and the controller state is cut to arms/annotation_credits/root_score/decision. The file calls `is_scientific_source` but adds **no** annotation context, unlike `table_evidence_extraction`.

The fresh decision inputs (`decision_inputs.py`) add:
- resource_context and shared_information_context;
- launch_instruction_library and selected_launch_instructions;
- child_options;
- the binding's initial context (a field conflict raises);
- completed_action_reports, and requested_action_history for HPC contexts;
- pending_work;
- execution_expectations for this role;
- resource_tool_estimates (job sample when the episode is a job source, else from expectations);
- native execution expectations and estimates;
- waiting_support;
- contract_information_profile.

The binding's own context (`internal_summary.py`) is given below. Under the exchange protocol, the model may first make `request_context` lookups, which create no work and earn no credit, before `select_action`. The model snapshot includes a yield table built from the controller binding parameters. The provider is called with `complete` and no presentation renderer.

## Credit

- `credit.py`: the kind is `operational` for every role in `ROLES` (other roles raise `unknown_resource_episode_role`), and the view is `services.bound_role_credit(context, receiver_selection)`.
- The episode has no scientific credit of its own. Wait outcomes take `last_observed_credit`.
- Nothing is bounded or rescaled.

## Continuation

- There is no `yield_estimator.py` and no `yield_controller` hook. The goal says "Only the configured local controller governs continuation", so this episode has no private estimator or settings.
- The controller binding parameters are only shown to the model in the yield table.
- In the new layout it needs one of the three `yield_control/` estimators chosen for it. For an operational resource episode the obvious candidate is completion with a target, but the old files do not state one.

The binding's own decision context: role `launch`, the assignment, `resource_capabilities`, and `resource_tool_estimates` from **every configured adapter**.

## What it reads from its parent's assignment

- `LAUNCH_SCHEMA` (`resource_launch_assignment_v1`, which wraps C9 `LaunchAssignmentV1` losslessly; `adapter_assignment` is added only after a resource is selected and is the existing job assignment, not a replacement for it).
- `prepare_assignment` keeps the schema properties, validates them, and returns the assignment unchanged. There is no adapter preparation at this level.
- Constraints that `_permitted` reads: `resource_selection`, `allowed_resource_ids`, `allowed_kinds`, `resource_id` and `kind`.

## Children it may commission

`child_roles` = `RESOURCE_ROLES`: `launch_api` -> `api_resource_work_execution`, `launch_local` -> `local_resource_work_execution`, `launch_hpc` -> `hpc_resource_work_execution`.

`allowed_children` (when the parent role is `launch`) offers a role only if some capability of that kind meets all of these conditions:
- it is bound to a configured adapter;
- it has tool names;
- its availability is not `unavailable`;
- the assignment constraints permit it.

What it sends (`to_child_<kind>_resource_work_execution.assemble_request`; the three files differ only in their docstring):
- a child goal refining this goal, with the report contract schema;
- a message with `scope` and `initial_report`;
- the old `inprocess_completion_order` tag;
- an optional `report_contract_declaration`, checked against the expanded contract with `validate_saved_fact_form`;
- `job_assignment`;
- `episode_assignment`, with the launch instructions materialized;
- an optional `structural_homology_evidence` payload;
- `knowledge_inheritance` bound from the old receipts.

The child itself checks inheritance of the launch fields and instruction pins.

What it takes back: the child's typed form with `execution_handoff` / `execution_handoffs` facts. Proof of a received handoff comes from the owning adapter's `received_form_references`.

## Tools offered

- `resource.capabilities`: read availability and configuration. No selection or submission.
- `resource.inspect {resource_id}`: inspect one declared resource and its binding. It returns distinct failures for unavailable, unknown, unauthenticated and unbound resources and does not submit.
- `resource.check_handoff {handoff}`: exercise the receiving interfaces of an explicitly supplied handoff through that handoff's adapter `check_handoff`. No submission and no substitution. It fails with `receiving_interface_unavailable` or `invalid_resource_handoff`.

There are no adapter tools at this level, so actual submission happens in the children.

## What it reports to its parent

- `execution_handoff` / `execution_handoffs` facts gathered from **every configured adapter**, deduplicated by (capability_binding_ref, execution_handle).
- `validate_report` runs every adapter's validation and then the handoff-equals-facts check.
- A reference resolves if it is in context or if any adapter resolves it.
- `finish`: fills the parent's typed form once from its interpretations and facts and saves it.

## Differences from similar episodes

Compared with `resource_result_acquisition`:
- it has children and their request assemblers;
- it offers inspection and handoff-check tools instead of adapter tools;
- it has the `_permitted` constraint check;
- it uses all adapters for facts, validation and reference resolution;
- it returns its contract-information profile;
- it does not prepare the assignment through an adapter.

Its `initial_references` only acts for role `results`, so as copied it never adds references for `launch`.

## File by file

| old file | lines | this episode's own intent | old-runner names used (×uses) |
|---|---|---|---|
| action_contract_feedback.py | 40 | typed repair feedback for a malformed action (closed top-level form repair text, component_native_return_channels_required, reads.map parameter diagnostics); records the decision effect 'rejected' with no unit acquired | import root.a102.read_mapping ×1, import root.a102.runtime ×2, _live_original_runtime.ContractError ×1, _live_original_runtime.ContractInformationError ×1, _live_original_runtime.ReportBoundaryError ×1, _live_original_runtime.schema_failure_diagnostic ×1, _live_original_runtime.ValidationError ×2 |
| binding_record.py | 7 | durable binding record: version resource_episode_binding_v1, binding_id = this episode's path, configured resource adapters and optional contract_information_profile | none |
| configuration.py | 22 | constructor: services, explicit resource_adapters (each must provide capability/as_record/prepare_assignment/catalog/execute/fact_sources/facts/resolve/validate_report/credit_view; unique resource_id; optional bind_record_selection), optional contract_information_profile (only the one profile accepted) | import root.a102.composition_information ×1 |
| credit.py | 13 | credit kind 'operational' for every resource role; credit view delegated to services.bound_role_credit (no scientific credit of its own) | self.services.bound_role_credit ×1 |
| decision_context.py | 45 | the decision state shown to the model: goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector, credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence (last image.view), report_deliveries, controller state/binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested form/purpose, current_report_update/basis, report_lifecycle text; annotation-axis credit mode trims state; specialist decision_context merged; calls is_scientific_source but does not add annotation context (differs from table_evidence_extraction) | import root.a102.runtime ×2, _live_original_runtime.FACT_MEANINGS ×1, _live_original_runtime.FACT_SOURCES ×1, _live_original_runtime._plain ×2, _live_original_runtime._references_in ×1, 'runtime_actions' ×1, workflow.binding_context ×1, workflow.catalog ×1, workflow.controller_binding ×1, workflow.delivery_status ×1, workflow.extra_report_sources ×1, workflow.is_scientific_source ×1, workflow.job_episode_options ×1, workflow.journal ×3, workflow.knowledge ×1, workflow.local_outcome_preview ×1, workflow.pending_work ×1, workflow.receipt_projection ×1, workflow.run_id ×1, workflow.source_credit_binding ×1, workflow.source_credit_view ×1, workflow.specialist ×1, workflow.store ×3, workflow.tools ×1, workflow.working_state ×1 |
| decision_contracts.py | 35 | request_context / select_action exchange envelope schema and validation | import root.a102.runtime ×2, _live_original_runtime.composition_lookup_schema ×2, _live_original_runtime.Draft202012Validator ×1, _live_original_runtime._object ×3 |
| decision_exchange.py | 119 | pending-decision exchange loop: request_context lookups (no work selected, no credit) then select_action; model snapshot with yield table; conversation key; interpretation context from looked-up publications | import root.a102.runtime ×2, _live_original_runtime._action_generation_schema ×1, _live_original_runtime._category_yield_parameters ×1, _live_original_runtime.child_option_information ×1, _live_original_runtime.DECISION_CONTEXT_VERSION ×1, _live_original_runtime.instructional_model_context ×2, _live_original_runtime.lookup_attempts ×1, _live_original_runtime.model_snapshot ×1, _live_original_runtime._plain ×2, _live_original_runtime._references_in ×1, _live_original_runtime.requested_contract_information ×1, _live_original_runtime.schema_failure_diagnostic ×2, _live_original_runtime.state_frame ×1, _live_original_runtime.ValidationError ×4, _live_original_runtime.yield_table ×1, 'runtime_model_calls' ×2, workflow.controller_binding ×1, workflow.decision_exchanges ×1, workflow.execute ×1, workflow.journal ×1, workflow.provider ×2, workflow.run_id ×1, workflow.services ×1, workflow.store ×2, workflow.validate_contract_information ×1 |
| decision_inputs.py | 58 | fresh decision inputs: resource_context, shared_information_context, launch_instruction_library and selected_launch_instructions, child_options, binding initial context (conflicts raise), completed_action_reports, HPC requested_action_history, pending_work, execution_expectations captured for role 'launch', resource_tool_estimates and native execution expectations/estimates, waiting_support, contract_information_profile | import root.a102.episode_work_report ×2, import root.a102.library.hpc_prompt ×1, import root.a102.runtime ×2, _live_original_runtime.child_option_information ×1, workflow.available_child_roles ×1, workflow.binding_context ×1, workflow.episode_bindings ×1, workflow.execution_expectations ×1, workflow.is_job_source ×1, workflow.job_episodes ×2, workflow.launch_instructions ×2, workflow.native_estimation_context ×1, workflow.pending_work ×1, workflow.permits_common_action ×1, workflow.resource_context ×1, workflow.resource_estimator ×5, workflow.shared_information_context ×1, workflow.waiting_support ×1 |
| episode.py | 25 | episode class composition; binding_path structural_homology_evidence/resource_work_submission, commissioned by structural_homology_evidence, role 'launch', no entry roles; adapter API docstring; permitted common actions tool, reason, child, wait, redeliver_report | none |
| from_parent.py | 19 | assignment schema LAUNCH_SCHEMA (resource_launch_assignment_v1 wrapping C9 LaunchAssignmentV1); keeps schema properties and validates; returns the assignment unchanged (no adapter preparation at this level) | none |
| goal.py | 12 | goal text "Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful." plus shared resource guidance; returns its configured contract_information_profile, so the request_context / episode.return_contract discovery sentence is added when a profile is configured | none |
| handoff_check.py | 19 | resource.check_handoff: exercise the selected adapter's receiving interface (check_handoff) on a supplied handoff; distinct failures receiving_interface_unavailable / invalid_resource_handoff; no submission or substitution | none |
| initial_references.py | 11 | initial references hook: for role 'results' only, asks the selected adapter's initial_references | none |
| __init__.py | 0 | empty package marker | none |
| instructions.py | 26 | composes default runtime instructions + this binding's goal instructions + reasoning-commit requirement + tool knowledge + launch instruction library + redeliver_report text + wait text (pending_child_ handle) + native event target text; replaces history guidance under the exchange protocol | import root.a102.runtime_prompt ×2, _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL ×1, _live_original_runtime_prompt.INSTRUCTIONS ×4, _live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT ×1, workflow.binding_context ×1, workflow.decision_protocol ×1, workflow.is_job_source ×1, workflow.job_episodes ×1, workflow.knowledge ×1, workflow.launch_instructions ×1, workflow.native_event_information ×1, workflow.permits_common_action ×3, workflow.specialist ×1 |
| internal_summary.py | 16 | binding decision context: role 'launch', assignment, resource_capabilities, resource_tool_estimates from every configured adapter's decision_context | none |
| operation_catalog.py | 12 | tools: resource.capabilities, resource.inspect (one declared resource and its binding; no submission), resource.check_handoff (exercise receiving interfaces of a supplied handoff; no submission or substitution); no adapter tools at this level | none |
| operations.py | 23 | dispatch: validates arguments against the catalogue; resource.capabilities, resource.inspect, resource.check_handoff handled here; no adapter dispatch at this level (other names already refused by the catalogue check) | none |
| received_messages.py | 31 | received_form_references: for x-source execution_handoff(s) fields, ask the adapter owning each handoff for its proof references; missing proof raises resource_information_handoff_proof_missing | none |
| report_delivery.py | 25 | finish: without report contract returns credit + pending handles + current report facts; with contract fills the parent's typed form from interpretations + facts once and saves it | import root.a102.library.private_policy_call ×1, import root.a102.library.report_fact_assembly ×1, import root.a102.runtime ×2, _invoke_private_policy ×1, _live_original_runtime.form_with_facts ×1, _live_original_runtime.Record ×2, 'runtime_forms' ×2, workflow.binding_context ×1, workflow.episode_bindings ×1, workflow.facts ×1, workflow.journal ×2, workflow.pending_handles ×1, workflow.release ×2, workflow.source_credit_view ×1 |
| report_fields.py | 15 | fact sources: execution_handoff (single usable check or null) and execution_handoffs (one per registry+handle, latest check, identity order) plus each adapter's fact sources; conflicting definitions raise | none |
| report_reference_access.py | 11 | a reference resolves if in the episode's received context, else if any configured adapter resolves it | none |
| resource_contracts.py | 36 | module docstring (C7 binding, resource_launch_assignment_v1 wraps C9 LaunchAssignmentV1 and adds adapter_assignment only after selection; resource_results_assignment_v1 carries handoff + requested_data_selector); helpers _failure/_outcome/_availability_failure (unavailable / authentication_required / unknown -> distinct codes); re-exports schemas from old resource_records | import root.a102.communication ×1, import root.a102.domain ×1, import root.a102.episode_bindings ×1, import root.a102.launch_instructions ×1, import root.a102.local_resources ×1, import root.a102.resource_records ×1 |
| resource_inspection.py | 15 | resource.inspect: distinct resource_not_bound / unavailable / authentication / unknown failures for a declared resource; does not submit | none |
| resource_selection.py | 36 | capabilities(): validated service capabilities, unbound declarations shown with empty tool_names; adapter capability identity and tool binding checked; _permitted(): resource_selection plus constraints allowed_resource_ids / allowed_kinds / resource_id / kind; _adapter(): from the handoff's resource_selection (results version) or the assignment's resource_selection; unbound raises resource_not_bound | self.services.capabilities ×1 |
| saved_decision_exchange.py | 81 | validation of saved contract-information exchange history on replay (frozen request, snapshot, public exchanges) | import root.a102.runtime ×2, _live_original_runtime.apply_state_frame ×1, _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS ×1, _live_original_runtime.DECISION_CONTEXT_VERSION ×1, _live_original_runtime.instructional_model_context ×1, _live_original_runtime.is_contract_information ×1, _live_original_runtime.model_snapshot ×1, _live_original_runtime._recorded_action_generation_schema ×1, _live_original_runtime.requested_contract_information ×1, _live_original_runtime.ValidationError ×1, _live_original_runtime.WorkflowError ×9, 'runtime_model_calls' ×1, workflow.contract_information_reply ×1, workflow.decision_exchanges ×2, workflow.journal ×1, workflow.validate_contract_information ×2 |
| task_decision.py | 82 | model call: replay saved request/response, else build decision inputs, freeze numerical/contract information, record receipts, save request, call provider REASONING with action generation schema (or exchange protocol), save response | import root.a102.runtime ×2, _live_original_runtime._action_generation_schema ×1, _live_original_runtime._ASSIGNMENT_TRANSPORT ×1, _live_original_runtime.DECISION_EXCHANGE_PROTOCOL ×5, _live_original_runtime._digest ×1, _live_original_runtime.instructional_model_context ×1, _live_original_runtime._recorded_assignment_transport ×1, _live_original_runtime.WorkflowError ×5, 'runtime_model_calls' ×5, workflow.contract_information_profile ×1, workflow.decision_exchanges ×1, workflow.decision_protocol ×3, workflow.freeze_contract_information ×1, workflow.freeze_literature_numerical_contracts ×1, workflow.history_preview ×1, workflow.is_job_source ×2, workflow.journal ×1, workflow.numerical_contracts ×1, workflow.provider ×2, workflow.receipts ×4, workflow.services ×1, workflow.uses_received_record_context ×2, workflow.validate_contract_information ×2 |
| task.py | 209 | iteration source: next() replays journaled units, collects ready owned children, calls model, applies response; apply_response validates selection (reason commit must not be empty unless the binding claims task content), report_update validated with grain 'launch'; execute() runs reason/wait/tool, saves outcome, receipts, automatic grading, credit from source_credit_view, stages controller input; failed outcome raises ActionFailure | import root.a102.episode_source_failure ×1, import root.a102.library.action_contracts ×1, import root.a102.library.private_policy_call ×1, import root.a102.providers ×1, import root.a102.runtime ×2, _invoke_private_policy ×1, _live_original_runtime.AcquisitionError ×2, _live_original_runtime.ActionFailure ×1, _live_original_runtime._decode_recorded_action_response ×1, _live_original_runtime.Draft202012Validator ×3, _live_original_runtime.EventTargetError ×2, _live_original_runtime.observes_action_outcome ×1, _live_original_runtime.ReportRedelivery ×2, _live_original_runtime.SourceEnd ×2, _live_original_runtime.validate_form ×1, _live_original_runtime.ValidationError ×1, _live_original_runtime._wait_target_feedback ×2, _live_original_runtime.WorkflowError ×2, 'runtime_actions' ×8, 'runtime_episodes' ×1, 'runtime_model_calls' ×2, workflow.action_schema ×1, workflow.automatic_score_updates ×1, workflow.binding_context ×2, workflow.completed_unit ×3, workflow.completions ×3, workflow.controller_value ×2, workflow.decision_exchanges ×3, workflow.delivery_resolution_inputs ×1, workflow.execute ×1, workflow.execution_binding ×7, workflow.inprocess_replay ×4, workflow.journal ×7, workflow.last_observed_credit ×1, workflow.next_return ×1, workflow.pending_work ×1, workflow.perform_selected_wait ×1, workflow.permits_common_action ×1, workflow.reasoning_action_schema ×1, workflow.receive_native_outcome ×1, workflow.receive_outcome ×1, workflow.resolve_pending_deliveries ×1, workflow.resolver ×1, workflow.retain_shared_grading_results ×1, workflow.run_id ×3, workflow.selected ×3, workflow.source_credit_view ×1, workflow.specialist ×2, workflow.store ×9, workflow.validate_report ×1 |
| task_state.py | 108 | per-episode source state (calls, feedback, last outcome, report_values from initial_report, report_basis, interpret_schema) and restore/checkpoint/record_effect/record_execution_failure (failed tool/reason action still enters iterator with its credit) | import root.a102.episode_source_failure ×1, import root.a102.runtime ×2, _live_original_runtime.ActionLeaf ×1, _live_original_runtime.EFFECT_VERSION ×1, _live_original_runtime.Episode ×1, _live_original_runtime.interpretation_schema ×1, _live_original_runtime._object ×1, _live_original_runtime._plain ×1, _live_original_runtime.Record ×1, 'runtime_actions' ×5, workflow.archive ×1, workflow.completions ×4, workflow.context ×1, workflow.controller_value ×1, workflow.execution_binding ×4, workflow.grains ×1, workflow.inprocess_replay ×7, workflow.journal ×5, workflow.progress_provider ×2, workflow.recover_commissions ×1, workflow.run_id ×1, workflow.source_credit_view ×1, workflow.store ×2 |
| to_parent.py | 48 | facts: execution_handoff/execution_handoffs gathered from every configured adapter, deduplicated by (capability_binding_ref, execution_handle), single handoff only when exactly one identity; validate_report: adapter validation then every x-source handoff field must equal the recorded facts (resource_handoff_fact_mismatch) | none |
| waiting.py | 9 | suspension registration of a wait condition with the execution backend | workflow.execution_backend ×1, workflow.execution_handle ×2 |
| to_child_api_resource_work_execution.py | 35 | assembles the immutable launch_api child request: child goal refining the parent with the contract schema, message scope + initial_report, optional report_contract_declaration (validated), job_assignment, episode_assignment (launch instructions materialized), structural_homology_evidence payload; knowledge_inheritance bound from receipts | import root.a102.runtime ×1, _runtime.ContractInformationError ×1, _runtime.Episode ×2, _runtime.EpisodeGoal ×2, _runtime.EpisodeRequest ×1, _runtime._plain ×3, _runtime.Record ×1, _runtime.validate_saved_fact_form ×1, workflow.context ×2, workflow.grains ×2, workflow.inprocess_completion_order ×2, workflow.launch_instructions ×1, workflow.receipts ×2, workflow.structural_homology_evidence_binding ×1 |
| to_child_hpc_resource_work_execution.py | 35 | assembles the immutable launch_hpc child request: child goal refining the parent with the contract schema, message scope + initial_report, optional report_contract_declaration (validated), job_assignment, episode_assignment (launch instructions materialized), structural_homology_evidence payload; knowledge_inheritance bound from receipts | import root.a102.runtime ×1, _runtime.ContractInformationError ×1, _runtime.Episode ×2, _runtime.EpisodeGoal ×2, _runtime.EpisodeRequest ×1, _runtime._plain ×3, _runtime.Record ×1, _runtime.validate_saved_fact_form ×1, workflow.context ×2, workflow.grains ×2, workflow.inprocess_completion_order ×2, workflow.launch_instructions ×1, workflow.receipts ×2, workflow.structural_homology_evidence_binding ×1 |
| to_child_local_resource_work_execution.py | 35 | assembles the immutable launch_local child request: child goal refining the parent with the contract schema, message scope + initial_report, optional report_contract_declaration (validated), job_assignment, episode_assignment (launch instructions materialized), structural_homology_evidence payload; knowledge_inheritance bound from receipts | import root.a102.runtime ×1, _runtime.ContractInformationError ×1, _runtime.Episode ×2, _runtime.EpisodeGoal ×2, _runtime.EpisodeRequest ×1, _runtime._plain ×3, _runtime.Record ×1, _runtime.validate_saved_fact_form ×1, workflow.context ×2, workflow.grains ×2, workflow.inprocess_completion_order ×2, workflow.launch_instructions ×1, workflow.receipts ×2, workflow.structural_homology_evidence_binding ×1 |

Indirect old-runner names: the same `resource_contracts.py` re-exports as `resource_result_acquisition` (old `communication`, `domain`, `episode_bindings`, `resource_records`, `launch_instructions` and `local_resources`). The `to_child_*` files take the old `workflow` object as a parameter and use `workflow.context`, `.grains`, `.inprocess_completion_order`, `.launch_instructions`, `.receipts` and `.structural_homology_evidence_binding`. The last is evaluated and its result is discarded.
