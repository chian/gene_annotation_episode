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

## Carried over

Carried 19 November 2026 into the ten-file private binding (`messages/` holds the five message files). Old code read with `git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>`. One row per row of `runs/carry_over/functions/a106__perturbation_evidence__execution_job_submission.tsv`; "machinery" rows are old-runner code that is not carried. Library pieces the episode calls: `forms/perturbation_evidence/execution_contracts.py::validate_api_assignment`, `forms/perturbation_evidence/communication.py::validate_form`, `acquisition/service_calls/bvbrc_application_facts.py::application_fact_sources`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`, `model_exchange/perturbation_evidence/action_transport.py`, `records/progress_views.py` (all already in the library). No row is a "library candidate".

| old file | kind | name | class | new place / reason |
|---|---|---|---|---|
| binding_record.py | class | OperationalBindingRecord | machinery | binding's own as_record (binding record); not carried |
| binding_record.py | method | OperationalBindingRecord.as_record | machinery | binding's own as_record (binding record); not carried |
| configuration.py | class | OperationalConfiguration | episode function | task.py _resources, read_from_parent.py handoff_unit, yield_estimator.py profiles; the rest is machinery |
| configuration.py | method | OperationalConfiguration.__init__ | episode function | checks of resources/initial_information -> task.py _resources; handoff_unit check -> messages/read_from_parent.py read_from_parent; task_yield_profiles -> ctx.settings read by yield_estimator.py; APIServiceExecution, ExecutionProgressProvider and native result/return custodians are old-runner machinery (job service, custody) |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py credit (formula of _live_project_credit); the rest is machinery |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit.project_credit | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit |
| credit.py | method | ExecutionEpisodeCredit.credit_view | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._proof_for_action | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit.completion_for_action | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_completion_verdict | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit.verify_completion | machinery | closed-credit / receipts / completion-proof bookkeeping over runtime_* tables; the system hands the controller's credit to final_to_parent |
| decision_inputs.py | class | OperationalDecisionInputs | episode function | task.py _context (what the model is shown) |
| decision_inputs.py | method | OperationalDecisionInputs.decision_inputs | episode function | task.py _context: launch_instruction_library, selected_launch_instructions, capabilities; resource_context, shared_information_context, child_options, pending_work, execution_expectations, resource estimates, waiting_support are old-runner services (not carried) |
| decision_inputs.py | function | _a106_original_global_ValueError | machinery | provider patching / runtime binder |
| decision_inputs.py | function | _a106_original_global_child_option_information | machinery | provider patching / runtime binder |
| decision_inputs.py | function | _a106_original_global_set | machinery | provider patching / runtime binder |
| decision_inputs.py | function | _bind_original_task_runtime_providers | machinery | provider patching / runtime binder |
| decision_presentation.py | function | present_credit_state | machinery | annotation-axis credit compaction / old journal-table reads / provider patching |
| decision_presentation.py | function | prepare_completed_work | machinery | annotation-axis credit compaction / old journal-table reads / provider patching |
| decision_presentation.py | function | decision_yield_table | episode function | messages/internal_summary.py (library records/progress_views.py yield_table) |
| decision_presentation.py | function | _bind_original_task_runtime_providers | machinery | annotation-axis credit compaction / old journal-table reads / provider patching |
| decision_state.py | class | OperationalDecisionState | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | method | OperationalDecisionState.decision_state | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_FACT_MEANINGS | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_FACT_SOURCES | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_Mapping | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global__references_in | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_callable | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_getattr | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_isinstance | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_json | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _a106_original_global_sorted | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| decision_state.py | function | _bind_original_task_runtime_providers | machinery | OperationalDecisionState: working state, journal reads, pending work, receipts projection, delivery status; not carried |
| episode.py | class | ExecutionEpisode | episode function | episode.py ExecutionJobSubmission |
| episode.py | method | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | method | ExecutionEpisode.allowed_children | episode function | messages/read_from_parent.py read_from_parent (permitted) |
| episode.py | method | ExecutionEpisode.permitted_common_actions | episode function | task.py decide/action (tool and child only; reason, wait and redeliver_report not carried, see contract_misfits) |
| episode.py | method | ExecutionEpisode.context_hook_applies | machinery | hook for the old runner |
| episode.py | method | ExecutionEpisode.child_request_preparer_for_binding | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | method | ExecutionEpisode.child_report_receiver_for_binding | episode function | messages/read_from_child.py read_from_child |
| execution_contracts.py | function | launch_operation_catalog | episode function | task.py execution_capabilities and CAPABILITIES_DESCRIPTION |
| execution_contracts.py | function | _outcome | machinery | old unit-outcome envelope |
| execution_operations.py | class | OperationalOperations | episode function | task.py execution_capabilities |
| execution_operations.py | method | OperationalOperations._resource_information | episode function | task.py execution_capabilities |
| execution_operations.py | method | OperationalOperations.capabilities | episode function | task.py execution_capabilities (job_access.capabilities, BLOCKED-ON-JOB-SERVICE) |
| execution_operations.py | method | OperationalOperations.catalog | machinery | old tool-catalog hook |
| execution_operations.py | method | OperationalOperations.execute | episode function | task.py execution_capabilities |
| execution_operations.py | method | OperationalOperations._appservice_sources | episode function | messages/final_to_parent.py RETURN_FORM (library application_fact_sources, support refs) |
| execution_state.py | class | OperationalExecutionState | episode function | messages/read_from_parent.py read_from_parent |
| execution_state.py | method | OperationalExecutionState.initialize | episode function | messages/read_from_parent.py read_from_parent (_launch check); pinned versions against the Store are a commission check (not carried) |
| execution_state.py | method | OperationalExecutionState._check_parent_inputs | machinery | runtime_episodes / receipts re-validation; results-role target (not this episode) |
| execution_state.py | method | OperationalExecutionState._target | machinery | runtime_episodes / receipts re-validation; results-role target (not this episode) |
| execution_state.py | method | OperationalExecutionState._selection | episode function | messages/read_from_parent.py received_handoff_resources field (new field) |
| execution_state.py | method | OperationalExecutionState._context_target | machinery | runtime_episodes / receipts re-validation; results-role target (not this episode) |
| from_child_api_job_execution.py | function | receive_report | episode function | messages/read_from_child.py read_from_child (progress provider, receipts and timing table are system custody) |
| from_parent.py | class | OperationalAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM, read_from_parent |
| from_parent.py | method | OperationalAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | OperationalAssignment._permitted | episode function | messages/read_from_parent.py _permitted |
| from_parent.py | method | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (_launch check); the input-version Store check is a commission check (not carried) |
| from_parent.py | method | OperationalAssignment._request_schema | episode function | library forms/perturbation_evidence/execution_contracts.py validate_api_assignment (envelope); the concrete service schema is job_access (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | method | OperationalAssignment._validate_request | episode function | messages/read_from_parent.py _request; service check in task.py _bound (job_access.validate_assignment, BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | method | OperationalAssignment._launch | episode function | messages/read_from_parent.py read_from_parent |
| from_parent.py | method | OperationalAssignment._constraints | episode function | messages/read_from_parent.py _constraints |
| from_parent.py | method | OperationalAssignment.initial_references | machinery | old runner hook (returned no references) |
| from_parent_launch.py | class | LaunchParentAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent_launch.py | method | LaunchParentAssignment._parent_launch_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| goal.py | class | OperationalGoal | episode function | goal.py GOAL |
| goal.py | method | OperationalGoal.instructions | episode function | goal.py GOAL |
| internal_summary.py | class | OperationalSummary | episode function | messages/internal_summary.py internal_summary; task.py execution_capabilities |
| internal_summary.py | method | OperationalSummary.initial_decision_context | episode function | messages/internal_summary.py internal_summary; task.py execution_capabilities |
| internal_summary.py | method | OperationalSummary.decision_context | episode function | messages/internal_summary.py internal_summary; task.py execution_capabilities |
| native_input_custody.py | class | NativeInputCustody | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._versions | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._recorded_results_assignment | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._selector | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._protein_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._atac_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._chromatin_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._flux_balance_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._fluorescence_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._expression_nmf_reference_access | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._atac_inputs | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._macs2_peak_inputs | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._lumpy_inputs | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._expression_nmf_inputs | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._fluorescence_inputs | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._matches_flux_balance_assignment | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| native_input_custody.py | method | NativeInputCustody._selected_result_action | machinery | custody of native inputs over old receipts/runtime tables; the system checks held records and this episode only commissions an API job (unplaced: see carry_over_blocked) |
| received_evidence.py | class | ReceivedOperationalEvidence | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._appservice_received_support_refs | episode function | messages/read_from_child.py support_refs, messages/internal_summary.py (support_refs) |
| received_evidence.py | method | ReceivedOperationalEvidence._appservice_validate_received_report | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._application_received_context | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._application_received_facts | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._application_validate_received_report | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._application_record_admission | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._application_resolve_received | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence._received | episode function | messages/internal_summary.py (handoff_resources) and credit.py |
| received_evidence.py | method | ReceivedOperationalEvidence.received_report_sources | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence.received_report_facts | episode function | messages/final_to_parent.py facts |
| received_evidence.py | method | ReceivedOperationalEvidence.resolve_received_reference | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence.validate_received_report | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| received_evidence.py | method | ReceivedOperationalEvidence.received_form_references | machinery | reference resolution/validation of received reports over old receipts, runtime_report_attempts and native custodians |
| report_delivery.py | class | OperationalReportDelivery | machinery | report_form finish / delivery lifecycle; the system fills the return form (final_to_parent) |
| report_delivery.py | method | OperationalReportDelivery.finish | machinery | report_form finish / delivery lifecycle; the system fills the return form (final_to_parent) |
| report_delivery.py | function | _bind_original_task_runtime_providers | machinery | report_form finish / delivery lifecycle; the system fills the return form (final_to_parent) |
| task.py | class | OperationalTask | episode function | task.py decide, action |
| task.py | method | OperationalTask.instructions | episode function | task.py decide (instruction text) |
| task.py | method | OperationalTask.next | episode function | task.py decide |
| task.py | method | OperationalTask.apply_response | episode function | task.py action |
| task.py | method | OperationalTask.execute | machinery | old action executor; the system runs the unit |
| task.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| task_decision.py | class | OperationalTaskDecision | episode function | task.py decide |
| task_decision.py | method | OperationalTaskDecision.call | episode function | task.py decide (model request) |
| task_decision.py | method | OperationalTaskDecision.conversation_key | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.interpretation_context | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.exchange_schema | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.exchange_response | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | method | OperationalTaskDecision.exchange_decision | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_DECISION_CONTEXT_VERSION | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_OSError | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_TypeError | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_ValidationError | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_ValueError | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global__action_generation_schema | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global__json | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global__plain | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_child_option_information | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_instructional_model_context | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_isinstance | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_len | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_lookup_attempts | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_model_snapshot | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_requested_contract_information | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_schema_failure_diagnostic | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_sqlite3 | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_state_frame | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_str | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _a106_original_global_type | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_decision.py | function | _bind_original_task_runtime_providers | machinery | decision-exchange loop, conversation key, saved-request checks, provider patching |
| task_instructions.py | function | instructions | episode function | task.py decide (GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION) |
| task_state.py | class | OperationalTaskState | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.__init__ | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.bind_execution_context | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.record_execution_failure | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.restore_checkpoint | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.restore | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.record_effect | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | method | OperationalTaskState.checkpoint | machinery | decision state restore/checkpoint/record_effect/execution failure |
| task_state.py | function | _bind_original_task_runtime_providers | machinery | decision state restore/checkpoint/record_effect/execution failure |
| to_child_api_job_execution.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child |
| to_parent.py | class | OperationalReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | OperationalReport._application_facts | episode function | messages/final_to_parent.py facts (outcomes from the child's report; latest saved adapter result read is BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | method | OperationalReport._application_resolve_own | episode function | messages/final_to_parent.py _resolver (BLOCKED-ON-JOB-SERVICE for outcome references) |
| to_parent.py | method | OperationalReport._application_resolve_reference | episode function | messages/final_to_parent.py _resolver |
| to_parent.py | method | OperationalReport.required_return_sources | episode function | messages/msg_to_child.py SELECTION |
| to_parent.py | method | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | method | OperationalReport.facts | episode function | messages/final_to_parent.py facts |
| to_parent.py | method | OperationalReport._live_facts | episode function | messages/final_to_parent.py facts |
| to_parent.py | method | OperationalReport.resolve | episode function | messages/final_to_parent.py _resolver (native custodian branches are machinery) |
| to_parent.py | method | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | class | OperationalTaskWaiting | machinery | wait/suspension machinery (selected wait on pending handles) |
| waiting.py | method | OperationalTaskWaiting._execute_selected_wait | machinery | wait/suspension machinery (selected wait on pending handles) |
| waiting.py | method | OperationalTaskWaiting.suspension_changed | machinery | wait/suspension machinery (selected wait on pending handles) |
| waiting.py | function | _bind_original_task_runtime_providers | machinery | wait/suspension machinery (selected wait on pending handles) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py _yield_class |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_yield_controller | episode function | yield_estimator.py yield_controller (bounded-quality controller; exact-zero estimator not carried) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | practical completion proof estimator |
