# a106/perturbation_evidence/execution_job_submission — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_job_submission/<file>`
(only files directly in this folder; no `grading/`/`scoring/`; `api_job_execution/` and `tests/` not covered).
Old binding class `ExecutionEpisode` (`binding_path = 'perturbation_evidence/execution_job_submission'`,
`commissioning_parent = 'perturbation_evidence'`, `roles = entry_roles = ('launch',)`,
`replaces_default_instructions = True`), decision source `OperationalTask`. Version `execution_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py`: "Choose which permitted concrete execution request to commission on an explicit resource_id.
Capabilities, recorded inventory and timing information inform the choice. Preserve the original job, immutable
inputs, constraints and pinned instructions. A resource child carries out iterative execution in the private loop.
Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes
this launch endpoint with exact zero future credit."

## Task and instructions

Because `replaces_default_instructions` is true, the goal text replaces the inline `INSTRUCTIONS` copy in
`task_instructions.py` (own copy of the scientific instruction text, same content the head imports from the shared
library). Then reasoning-commit requirement (if reason permitted), tool knowledge, launch-instruction library,
pending-delivery repair, wait and native-event guidance, exchange history guidance are appended.
`task.py` (class `OperationalTask`) is the head's loop without the job_child failure branch and without the
perturbation_evidence execution-context validation; reason actions still allowed.

## What it reads from its parent's assignment

`execution_launch_assignment_v1`: `requests` {resource_id -> concrete API request (api_execution assignment schema +
`resource_id` const)} (min 1), `immutable_input_versions` [INPUT_VERSION_SCHEMA], `constraints`
(allowed_resource_ids, allowed_kinds, resource_id, kind), optional `launch_instructions` (SELECTION_SCHEMA). Each
request is validated by the API execution layer in scope; input versions checked (`_versions`) incl. native inputs.
`initial_references` = none.

## Children it may commission

| role | child binding | sent | taken back |
|---|---|---|---|
| `launch_api` | `perturbation_evidence/execution_job_submission/api_job_execution` | one concrete per-resource request (anyOf per resource, resource_id required), scope, typed form, initial report | typed form (execution_handoff_refs, support refs, result refs, execution_completed, application facts) admitted with receipts/progress/timing |

Allowed only for a resource whose kind is `api` and that is permitted by the assignment's requests/constraints.

## Decision state and what it shows the model

Same shape as the head's standalone presentation, without annotation_context, plus `job_episode_options`.
Binding context: `execution_resource_capabilities` (resource_id, kind api, availability unknown, tool_names,
service/base_url, inventory_snapshot) and `execution_initial_information`; decision_context `execution_assignment`
and `execution_progress` (live facts). Decision inputs as head (resource_context, shared information, launch
instructions, child options, expectations, estimates, waiting_support).

## Tools it offers

`execution.capabilities` (read caller-bound resource configuration and recorded inventory; no discovery). Common
actions: tool, reason, child, wait, redeliver_report.

## How its credit is counted

Credit kind `operational`. Live: `handoff_unit x |resource_ids with a usable received handoff - those already among
initial known refs|`; `new_acquired_record_count` 0; binding `execution_received_records_credit_v1`. At closure the
projected view is captured once in the closing facts (`execution_closed_operational_credit_v1`) with digests of
context, binding, completion, archive, observation history and receipt prefix; later reads return only that view.
Practical completion proof (`practical_completion_v1`, endpoint `usable_handoff`) from an action whose record_refs
contain a usable handoff.

## Continuation

`_launch_yield_controller`: when eligible original requests remain uncredited, `BoundedYieldController(cutoff,
remaining = count x handoff_unit)` with `task_yield_profiles['launch:' + '+'.join(sorted request classes)]`
(class = `api_<service>[_<algorithm>][_<database>]_handoff`); when none remain (all in initial handoffs) an
exact-zero `YieldController(cutoff 0)` (`launch_original_request_exhaustion_v1`). Requires
`require_private_yield`. `practical_estimator` wraps verify_completion.

## What it reports to its parent

Fact sources `execution_handoff_refs`, `execution_result_refs` (always [] here), `execution_completed`,
`bvbrc_appservice_support_refs`, BV-BRC application facts; plus the closed credit fact. Required return
`execution_handoff_refs` when the parent is `perturbation_evidence` and the annotation task is required.
`validate_report` requires fact fields to equal recorded facts; reference resolution goes through the native
custodians (FBA, fluorescence, NMF, ATAC, chromatin, protein structure) then the API execution layer.

## Differences from siblings

Compared with `api_job_execution`: has a child (launch_api) and reason/child/redeliver actions; credit counts
distinct resource_ids from received handoffs (not handoff+result identities); continuation is bounded quality over
remaining requests (child: accumulation + practical completion). Compared with the head: operational credit, no
science selection.

## File by file
| old file | lines | own intent | old-runner names (uses) |
|---|---|---|---|
| __init__.py | 0 | empty package marker | none |
| binding_record.py | 8 | as_record: binding_id perturbation_evidence/execution_job_submission, version execution_episode_v1, resources, initial_information, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield, task_yield_profiles | none |
| configuration.py | 92 | construction: explicit api resources (KINDS api only), initial inventory per resource, positive handoff_unit and acquired_record_unit, log window/roles, require_private_yield, task_yield_profiles (cutoff + parameters, validated as accumulation controllers); builds APIServiceExecution, ExecutionProgressProvider and the native result/return custodians (FBA, protein structure, fluorescence, expression NMF, ATAC, chromatin interactions) | `import:api_service_execution` x1, `import:execution_progress` x1, `import:library.retained_input_authority.atac_differential_returns` x1, `import:library.retained_input_authority.chromatin_interaction_returns` x1, `import:library.retained_input_authority.expression_nmf_returns` x1, `import:library.retained_input_authority.fluorescence_returns` x1, `import:library.retained_input_authority.flux_balance_execution_inputs` x1, `import:library.retained_input_authority.flux_balance_returns` x1, `import:library.retained_input_authority.native_atac_differential_results` x1, `import:library.retained_input_authority.native_chromatin_interaction_results` x1, `import:library.retained_input_authority.native_expression_nmf_results` x1, `import:library.retained_input_authority.native_fluorescence_results` x1, `import:library.retained_input_authority.native_flux_balance_results` x1, `import:library.retained_input_authority.native_protein_structure_results` x1, `import:library.retained_input_authority.native_protein_structure_returns` x1, `import:numerical` x1, `services.read_received_molecular_input` x1 |
| credit.py | 206 | credit kind 'operational'; live credit = handoff_unit x number of new resource_ids with a usable received handoff (baseline = handoffs among initial known refs); closed credit captured once in closing facts and re-authenticated (carrier, receipt prefix, history digest); practical completion proof from an action whose record_refs include a usable handoff; verify_completion | `import:episode_receipts` x1, `import:episode_return_records` x4, `import:method_loop.identities` x1, `import:numerical` x1, `import:practical_yield` x1, `sqlite_master` x2, `table:runtime_actions` x1, `table:runtime_episodes` x2, `table:runtime_forms` x3, `table:runtime_observations` x2, `table:runtime_receipt_inheritance` x2, `table:runtime_record_receipts` x2 |
| decision_inputs.py | 71 | same input set as head minus job estimates: resource_context, shared_information_context, launch instructions, child_options, initial binding context (execution_resource_capabilities, execution_initial_information), completed work, pending_work, execution_expectations, resource estimates, native expectations, waiting_support, profile | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.available_child_roles` x1, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.execution_expectations` x1, `self.workflow.launch_instructions` x2, `self.workflow.native_estimation_context` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.resource_context` x1, `self.workflow.resource_estimator` x4, `self.workflow.shared_information_context` x1, `self.workflow.waiting_support` x1 |
| decision_presentation.py | 51 | present_credit_state (annotation-axis compaction), prepare_completed_work, decision_yield_table | `bind_functions` x2, `import:episode_work_report` x1, `import:library.live_runtime_functions` x1, `import:runtime` x4, `self.workflow.controller_binding` x1, `self.workflow.journal` x1, `table:runtime_actions` x1 |
| decision_state.py | 78 | decision state shown to model; adds job_episode_options; no annotation_context | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.catalog` x1, `self.workflow.controller_binding` x1, `self.workflow.delivery_status` x1, `self.workflow.extra_report_sources` x1, `self.workflow.job_episode_options` x1, `self.workflow.journal` x2, `self.workflow.knowledge` x1, `self.workflow.local_outcome_preview` x1, `self.workflow.pending_work` x1, `self.workflow.receipt_projection` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_binding` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x1, `self.workflow.store` x3, `self.workflow.tools` x1, `self.workflow.working_state` x1, `table:runtime_actions` x1 |
| episode.py | 55 | binds role launch; child roles = ROLE_KINDS (launch_api); allowed children = launch_api when a permitted api resource is in the assignment; common actions tool/reason/child/wait/redeliver_report; replaces_default_instructions; maps launch_api to its to_child/from_child | none |
| execution_contracts.py | 26 | constants: VERSION execution_episode_v1, LAUNCH/RESULTS versions, _CLOSED_CREDIT, ROLES (launch, launch_api, results), KINDS {api}, ROLE_KINDS {launch_api: api}, RESULTS_SCHEMA, execution.capabilities catalog, _outcome | `import:communication` x1, `import:execution_contracts` x1, `import:launch_instructions` x1, `import:practical_execution_records` x1, `import:resource_records` x1 |
| execution_operations.py | 34 | tool execution.capabilities (caller-bound resource configuration and recorded inventory); _resource_information; AppService fact sources | `import:library.bvbrc_application_facts` x1 |
| execution_state.py | 57 | initialize validates launch assignment and immutable input versions; parent launch input check; results target; receiver selection (known/initial refs from services.record_selection, receipts or own actions); context target checks per role | `import:episode_receipts` x1, `services.record_selection` x1, `sqlite_master` x1, `table:runtime_actions` x1, `table:runtime_episodes` x1, `table:runtime_receipt_inheritance` x2 |
| from_child_api_job_execution.py | 46 | admits the launch_api child's typed return (receipts, progress, native timing) | `binding_context` x4, `import:delivery_counterpart` x2, `import:episode_return_records` x1, `import:runtime` x1, `table:runtime_report_attempts` x2, `workflow.binding_context` x4, `workflow.episode_bindings` x2, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information` x1, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.run_id` x6, `workflow.specialist` x1, `workflow.store` x7 |
| from_parent.py | 63 | assignment schema execution_launch_assignment_v1: requests per resource (api assignment schema + resource_id), immutable_input_versions, constraints, launch_instructions; _permitted by allowed_resource_ids/kinds/resource_id/kind; prepare_assignment validates requests and input versions; initial_references none | none |
| from_parent_launch.py | 9 | the parent launch assignment schema used for admission | none |
| goal.py | 9 | the episode's goal text | none |
| internal_summary.py | 13 | initial context: execution_resource_capabilities + execution_initial_information; decision_context: execution_assignment + execution_progress (facts) | none |
| native_input_custody.py | 229 | immutable input version checks; restore recorded Results commission; per-native-kind reference access (protein structure, ATAC, chromatin, FBA, fluorescence, NMF) and input extraction (ATAC, MACS2, LUMPY, NMF, fluorescence, FBA) | `import:episode_receipts` x1, `import:episode_return_records` x1, `import:execution_contracts` x1, `import:execution_input_versions` x1, `import:library.retained_input_authority.atac_differential_operands` x1, `import:library.retained_input_authority.expression_nmf_operands` x1, `import:library.retained_input_authority.fluorescence_operands` x1, `import:library.retained_input_authority.flux_balance_request_binding` x1, `import:library.retained_input_authority.lumpy_request_binding` x1, `import:library.retained_input_authority.protein_structure_operands` x1, `import:library.retained_input_authority.received_native_file_inputs` x1, `table:runtime_actions` x2, `table:runtime_episodes` x1, `table:runtime_report_attempts` x1 |
| received_evidence.py | 173 | AppService received support refs and report validation; application received facts/validation/admission/resolution; _received (usable handoffs among known refs); received_report_sources/facts for perturbation_evidence parent; received reference resolution; received_form_references | `import:bvbrc_appservice_custody` x1, `import:bvbrc_appservice_host` x1, `import:bvbrc_appservice_records` x1, `import:communication` x1, `import:execution_contracts` x2, `import:form_reference_validation` x1, `import:library.bvbrc_application_facts` x2, `table:runtime_report_attempts` x1 |
| report_delivery.py | 33 | finish: fills the typed form from facts once | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.facts` x1, `self.workflow.journal` x2, `self.workflow.pending_handles` x1, `self.workflow.release` x2, `self.workflow.source_credit_view` x1, `table:runtime_forms` x2 |
| task.py | 218 | decision loop (same as head minus job_child failure handling and execution-context validation) | `bind_functions` x2, `binding_context` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:providers` x1, `import:runtime` x2, `self.workflow.action_schema` x1, `self.workflow.automatic_score_updates` x1, `self.workflow.binding_context` x2, `self.workflow.completed_unit` x3, `self.workflow.completions` x3, `self.workflow.controller_value` x2, `self.workflow.decision_exchanges` x3, `self.workflow.delivery_resolution_inputs` x1, `self.workflow.execute` x1, `self.workflow.execution_binding` x7, `self.workflow.inprocess_replay` x4, `self.workflow.journal` x7, `self.workflow.last_observed_credit` x1, `self.workflow.next_return` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.reasoning_action_schema` x1, `self.workflow.receive_native_outcome` x1, `self.workflow.receive_outcome` x1, `self.workflow.resolve_pending_deliveries` x1, `self.workflow.resolver` x1, `self.workflow.retain_shared_grading_results` x1, `self.workflow.run_id` x3, `self.workflow.selected` x3, `self.workflow.services` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x2, `self.workflow.store` x9, `self.workflow.validate_report` x1, `services.instructions` x1, `table:runtime_actions` x8, `table:runtime_episodes` x1, `table:runtime_model_calls` x2 |
| task_decision.py | 374 | model call + decision exchange (same as head; yield table from decision_presentation; receipts no job-source check) | `bind_functions` x3, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.contract_information_profile` x1, `self.workflow.contract_information_reply` x1, `self.workflow.decision_exchanges` x4, `self.workflow.decision_protocol` x3, `self.workflow.execute` x1, `self.workflow.freeze_contract_information` x1, `self.workflow.freeze_literature_numerical_contracts` x1, `self.workflow.history_preview` x1, `self.workflow.journal` x3, `self.workflow.numerical_contracts` x1, `self.workflow.provider` x4, `self.workflow.receipts` x4, `self.workflow.run_id` x1, `self.workflow.services` x1, `self.workflow.store` x2, `self.workflow.uses_received_record_context` x2, `self.workflow.validate_contract_information` x5, `services.decision_exchange_instructions` x1, `table:runtime_model_calls` x8 |
| task_instructions.py | 26 | own copy of INSTRUCTIONS text + composition (replaced by goal since replaces_default_instructions) | `binding_context` x1, `source.workflow.binding_context` x1, `source.workflow.decision_protocol` x1, `source.workflow.knowledge` x1, `source.workflow.launch_instructions` x1, `source.workflow.native_event_information` x1, `source.workflow.permits_common_action` x3, `source.workflow.specialist` x1 |
| task_state.py | 114 | per-episode decision state/restore/checkpoint (same as head) | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.archive` x1, `self.workflow.completions` x4, `self.workflow.controller_value` x1, `self.workflow.execution_binding` x4, `self.workflow.inprocess_replay` x7, `self.workflow.journal` x5, `self.workflow.progress_provider` x2, `self.workflow.recover_commissions` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_view` x1, `self.workflow.store` x2, `table:runtime_actions` x5, `workflow.context` x1, `workflow.grains` x1 |
| to_child_api_job_execution.py | 29 | prepares launch_api child commission | `binding_context` x4, `import:runtime` x1, `services.capabilities` x1, `workflow.annotation_child_roles` x1, `workflow.available_child_roles` x1, `workflow.binding_context` x4, `workflow.child_initial_report_input` x1, `workflow.episode_bindings` x3, `workflow.expanded_contract_form` x1, `workflow.launch_instructions` x1, `workflow.run_id` x1, `workflow.services` x1, `workflow.specialist` x1, `workflow.store` x1 |
| to_parent.py | 115 | required return execution_handoff_refs when parent is perturbation_evidence and annotation task required; fact sources execution_handoff_refs, execution_result_refs, execution_completed, AppService support refs + application facts; live facts from received handoffs; closed credit fact; resolve via native custodians then api_execution; validate_report checks fact fields equal recorded facts | `import:bvbrc_appservice_saved_results` x1, `import:episode_bindings` x1, `import:execution_contracts` x1, `import:form_reference_validation` x1, `import:library.bvbrc_application_facts` x1, `services.annotation_task_required` x1 |
| waiting.py | 30 | selected wait + suspension | `bind_functions` x2, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.execution_backend` x1, `self.workflow.execution_handle` x2, `self.workflow.perform_selected_wait` x1 |
| yield_estimator.py | 55 | bounded-quality controller: remaining = (eligible requests without initial usable handoff) x handoff_unit, profile task_yield_profiles['launch:'+classes]; if none remaining an exact-zero YieldController; practical_estimator from verify_completion | `import:numerical` x1, `import:practical_yield` x1 |
