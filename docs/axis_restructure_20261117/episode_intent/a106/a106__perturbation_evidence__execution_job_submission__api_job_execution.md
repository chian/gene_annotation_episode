# a106/perturbation_evidence/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_job_submission/api_job_execution/<file>`
(only files directly in this folder; no `grading/`/`scoring/`; `tests/` not covered). Old binding class
`ExecutionEpisode` (`binding_path = '.../execution_job_submission/api_job_execution'`, `commissioning_parent =
'perturbation_evidence/execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `OperationalTask`. Version `execution_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py` (service name from the assignment): "Carry out the assigned work through {service} using one selected
operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful
preparation, service requests, observations or repair from the actual available operations and received outcomes.
Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request
or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish
the requested usable monitoring/results handoff from recorded service facts. The configured controller governs
continuation; verified original handoff completion gives exact zero future credit."

## Task and instructions

Goal replaces the inline INSTRUCTIONS copy; the rest of the composition as the launch parent. `task.py` has no
reason-action branch (actions are tool and wait only).

## What it reads from its parent's assignment

One concrete API request for one configured resource (`anyOf` of per-resource api_execution assignment schemas with
`resource_id` required). `prepare_assignment` accepts it only from a `launch` parent, validates it in scope and
re-checks the parent's `immutable_input_versions`. `execution_state.initialize` re-checks the parent launch inputs
from the recorded parent request, then `api_execution.initialize`. `initial_references` none.

## Children it may commission

None (leaf): `child_roles` and `allowed_children` return ().

## Decision state and what it shows the model

As the launch parent, plus `api_execution.decision_context` (`_api_decision_summary`: api_service, api_request,
latest received progress per event name {state, kind, facts, failure_code}, api_execution_completed).

## Tools it offers

`api_execution.catalog(context)`: the service's launch catalog for its request, or its result catalog for a
selector. Its operation contracts are published upward (`resource_tool_contracts`) as `commission` invocation routes
(entry_role launch, resource_role launch_api) so the head can see them. Common actions: tool, wait.

## How its credit is counted

Credit kind `operational`, delegated to `api_execution.credit_view` which calls `_api_operational_credit`:
`operational_credit_from_identities(new (resource_id, execution_id) handoffs, new result identities, handoff_unit,
acquired_record_unit)` over known refs minus initial refs. Closed credit capture as the launch parent. Completion
proof: latest own `TaskHandoff` receipt (endpoint `usable_handoff`), via api_execution.

## Continuation

`YieldController(cutoff from task_yield_profiles['launch_api:' + request class], parameters,
estimate_with_context=PracticalYieldEstimator(verify_completion))`: accumulation with exact zero forecast after a
verified handoff completion. Requires `require_private_yield`.

## What it reports to its parent

`api_execution.facts`: execution_handoff_refs (TaskHandoff receipts), bvbrc_appservice_support_refs (other receipts),
execution_result_refs (own published results), execution_completed, application facts; plus closed credit fact. No
required return sources.

## Differences from siblings

Copy of the launch parent's file set with: no children, tool/wait only, credit and facts delegated to the API
execution layer (handoff + result identities), accumulation + practical completion continuation, service-specific
goal.

## File by file
| old file | lines | own intent | old-runner names (uses) |
|---|---|---|---|
| __init__.py | 0 | empty package marker | none |
| binding_record.py | 8 | as_record: binding_id perturbation_evidence/execution_job_submission/api_job_execution, version execution_episode_v1, resources, initial_information, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield, task_yield_profiles | none |
| configuration.py | 92 | same construction as launch but APIServiceExecution gets credit_projector=_api_operational_credit and decision summary hooks | `import:api_service_execution` x1, `import:execution_progress` x1, `import:library.retained_input_authority.atac_differential_returns` x1, `import:library.retained_input_authority.chromatin_interaction_returns` x1, `import:library.retained_input_authority.expression_nmf_returns` x1, `import:library.retained_input_authority.fluorescence_returns` x1, `import:library.retained_input_authority.flux_balance_execution_inputs` x1, `import:library.retained_input_authority.flux_balance_returns` x1, `import:library.retained_input_authority.native_atac_differential_results` x1, `import:library.retained_input_authority.native_chromatin_interaction_results` x1, `import:library.retained_input_authority.native_expression_nmf_results` x1, `import:library.retained_input_authority.native_fluorescence_results` x1, `import:library.retained_input_authority.native_flux_balance_results` x1, `import:library.retained_input_authority.native_protein_structure_results` x1, `import:library.retained_input_authority.native_protein_structure_returns` x1, `import:numerical` x1, `services.read_received_molecular_input` x1 |
| credit.py | 239 | credit kind operational; live credit delegated to api_execution.credit_view via _api_operational_credit (operational_credit_from_identities: new (resource_id, execution_id) handoffs x handoff_unit + new result identities x acquired_record_unit); closed credit capture as launch; completion proof = latest TaskHandoff receipt (usable_handoff) via api_execution | `import:domain` x1, `import:episode_receipts` x1, `import:episode_return_records` x4, `import:library.api_operational_credit` x1, `import:library.standalone_appservice_reports` x1, `import:method_loop.identities` x1, `import:numerical` x1, `import:practical_yield` x1, `sqlite_master` x2, `table:runtime_actions` x1, `table:runtime_episodes` x2, `table:runtime_forms` x3, `table:runtime_observations` x2, `table:runtime_receipt_inheritance` x2, `table:runtime_record_receipts` x2 |
| decision_inputs.py | 71 | same input set as head minus job estimates: resource_context, shared_information_context, launch instructions, child_options, initial binding context (execution_resource_capabilities, execution_initial_information), completed work, pending_work, execution_expectations, resource estimates, native expectations, waiting_support, profile | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.available_child_roles` x1, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.execution_expectations` x1, `self.workflow.launch_instructions` x2, `self.workflow.native_estimation_context` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.resource_context` x1, `self.workflow.resource_estimator` x4, `self.workflow.shared_information_context` x1, `self.workflow.waiting_support` x1 |
| decision_presentation.py | 51 | present_credit_state (annotation-axis compaction), prepare_completed_work, decision_yield_table | `bind_functions` x2, `import:episode_work_report` x1, `import:library.live_runtime_functions` x1, `import:runtime` x4, `self.workflow.controller_binding` x1, `self.workflow.journal` x1, `table:runtime_actions` x1 |
| decision_state.py | 78 | decision state shown to model; adds job_episode_options; no annotation_context | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.catalog` x1, `self.workflow.controller_binding` x1, `self.workflow.delivery_status` x1, `self.workflow.extra_report_sources` x1, `self.workflow.job_episode_options` x1, `self.workflow.journal` x2, `self.workflow.knowledge` x1, `self.workflow.local_outcome_preview` x1, `self.workflow.pending_work` x1, `self.workflow.receipt_projection` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_binding` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x1, `self.workflow.store` x3, `self.workflow.tools` x1, `self.workflow.working_state` x1, `table:runtime_actions` x1 |
| episode.py | 46 | binds role launch_api (leaf, entry_roles empty); no children; common actions tool and wait only; context hooks apply to launch_api | none |
| execution_contracts.py | 26 | constants: VERSION execution_episode_v1, LAUNCH/RESULTS versions, _CLOSED_CREDIT, ROLES (launch, launch_api, results), KINDS {api}, ROLE_KINDS {launch_api: api}, RESULTS_SCHEMA, execution.capabilities catalog, _outcome | `import:communication` x1, `import:execution_contracts` x1, `import:launch_instructions` x1, `import:practical_execution_records` x1, `import:resource_records` x1 |
| execution_operations.py | 50 | catalog = api_execution.catalog (service launch catalog or result catalog for the selector); execute delegates to api_execution after parent input check; resource_tool_contracts published to the head as commission routes | `import:library.bvbrc_application_facts` x1 |
| execution_state.py | 57 | initialize checks parent launch inputs then api_execution.initialize; receiver selection and target checks as launch | `import:episode_receipts` x1, `services.record_selection` x1, `sqlite_master` x1, `table:runtime_actions` x1, `table:runtime_episodes` x1, `table:runtime_receipt_inheritance` x2 |
| from_parent.py | 76 | assignment schema = anyOf concrete per-resource api request (resource_id required); prepare_assignment only from a launch parent, validates request and parent immutable input versions; _api_context; initial_references none | `import:library.standalone_api_context` x1 |
| from_parent_launch.py | 9 | the parent launch assignment schema used for admission | none |
| goal.py | 11 | the episode goal text, service-specific | none |
| internal_summary.py | 22 | decision_context adds api_execution.decision_context (api_service, api_request, received progress events, completion) | none |
| native_input_custody.py | 229 | immutable input version checks; restore recorded Results commission; per-native-kind reference access (protein structure, ATAC, chromatin, FBA, fluorescence, NMF) and input extraction (ATAC, MACS2, LUMPY, NMF, fluorescence, FBA) | `import:episode_receipts` x1, `import:episode_return_records` x1, `import:execution_contracts` x1, `import:execution_input_versions` x1, `import:library.retained_input_authority.atac_differential_operands` x1, `import:library.retained_input_authority.expression_nmf_operands` x1, `import:library.retained_input_authority.fluorescence_operands` x1, `import:library.retained_input_authority.flux_balance_request_binding` x1, `import:library.retained_input_authority.lumpy_request_binding` x1, `import:library.retained_input_authority.protein_structure_operands` x1, `import:library.retained_input_authority.received_native_file_inputs` x1, `table:runtime_actions` x2, `table:runtime_episodes` x1, `table:runtime_report_attempts` x1 |
| received_evidence.py | 173 | AppService received support refs and report validation; application received facts/validation/admission/resolution; _received (usable handoffs among known refs); received_report_sources/facts for perturbation_evidence parent; received reference resolution; received_form_references | `import:bvbrc_appservice_custody` x1, `import:bvbrc_appservice_host` x1, `import:bvbrc_appservice_records` x1, `import:communication` x1, `import:execution_contracts` x2, `import:form_reference_validation` x1, `import:library.bvbrc_application_facts` x2, `table:runtime_report_attempts` x1 |
| report_delivery.py | 33 | finish: fills the typed form from facts once | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.facts` x1, `self.workflow.journal` x2, `self.workflow.pending_handles` x1, `self.workflow.release` x2, `self.workflow.source_credit_view` x1, `table:runtime_forms` x2 |
| task.py | 199 | decision loop without reason actions | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:providers` x1, `import:runtime` x2, `self.workflow.action_schema` x1, `self.workflow.automatic_score_updates` x1, `self.workflow.completed_unit` x3, `self.workflow.completions` x3, `self.workflow.controller_value` x2, `self.workflow.decision_exchanges` x3, `self.workflow.delivery_resolution_inputs` x1, `self.workflow.execute` x1, `self.workflow.execution_binding` x7, `self.workflow.inprocess_replay` x4, `self.workflow.journal` x7, `self.workflow.last_observed_credit` x1, `self.workflow.next_return` x1, `self.workflow.pending_work` x1, `self.workflow.receive_native_outcome` x1, `self.workflow.receive_outcome` x1, `self.workflow.resolve_pending_deliveries` x1, `self.workflow.resolver` x1, `self.workflow.retain_shared_grading_results` x1, `self.workflow.run_id` x2, `self.workflow.selected` x3, `self.workflow.services` x1, `self.workflow.source_credit_view` x1, `self.workflow.store` x7, `self.workflow.validate_report` x1, `services.instructions` x1, `table:runtime_actions` x8, `table:runtime_episodes` x1, `table:runtime_model_calls` x2 |
| task_decision.py | 374 | model call + decision exchange (same as head; yield table from decision_presentation; receipts no job-source check) | `bind_functions` x3, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.contract_information_profile` x1, `self.workflow.contract_information_reply` x1, `self.workflow.decision_exchanges` x4, `self.workflow.decision_protocol` x3, `self.workflow.execute` x1, `self.workflow.freeze_contract_information` x1, `self.workflow.freeze_literature_numerical_contracts` x1, `self.workflow.history_preview` x1, `self.workflow.journal` x3, `self.workflow.numerical_contracts` x1, `self.workflow.provider` x4, `self.workflow.receipts` x4, `self.workflow.run_id` x1, `self.workflow.services` x1, `self.workflow.store` x2, `self.workflow.uses_received_record_context` x2, `self.workflow.validate_contract_information` x5, `services.decision_exchange_instructions` x1, `table:runtime_model_calls` x8 |
| task_instructions.py | 26 | own copy of INSTRUCTIONS text + composition (replaced by goal since replaces_default_instructions) | `binding_context` x1, `source.workflow.binding_context` x1, `source.workflow.decision_protocol` x1, `source.workflow.knowledge` x1, `source.workflow.launch_instructions` x1, `source.workflow.native_event_information` x1, `source.workflow.permits_common_action` x3, `source.workflow.specialist` x1 |
| task_state.py | 114 | per-episode decision state/restore/checkpoint (same as head) | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.archive` x1, `self.workflow.completions` x4, `self.workflow.controller_value` x1, `self.workflow.execution_binding` x4, `self.workflow.inprocess_replay` x7, `self.workflow.journal` x5, `self.workflow.progress_provider` x2, `self.workflow.recover_commissions` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_view` x1, `self.workflow.store` x2, `table:runtime_actions` x5, `workflow.context` x1, `workflow.grains` x1 |
| to_parent.py | 125 | facts delegated to api_execution.facts; _appservice_report_facts (TaskHandoff refs, support refs, own results, completion); no required return sources | `import:bvbrc_appservice_host` x1, `import:bvbrc_appservice_saved_results` x1, `import:episode_bindings` x1, `import:execution_contracts` x1, `import:form_reference_validation` x1, `import:library.bvbrc_application_facts` x1, `services.annotation_task_required` x1 |
| waiting.py | 30 | selected wait + suspension | `bind_functions` x2, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.execution_backend` x1, `self.workflow.execution_handle` x2, `self.workflow.perform_selected_wait` x1 |
| yield_estimator.py | 37 | accumulation YieldController with profile task_yield_profiles[launch_api:<class>] and PracticalYieldEstimator(verify_completion) as estimate_with_context | `import:numerical` x1, `import:practical_yield` x2 |

## Carried over

Carried over on 19 November 2026 from `97308b94c` as a private binding: goal.py, task.py, credit.py, yield_estimator.py, episode.py, messages/read_from_parent.py, internal_summary.py, final_to_parent.py (no children, so no msg_to_child.py or read_from_child.py). Nothing is imported from another episode; the library functions called are `launch_instructions`, `tool_knowledge`, `rejection_feedback`, `time_accounting`, `failure_outcome` and `application_fact_sources`. The shape follows the finished private carries of the A101/A102 siblings. The service work is BLOCKED-ON-JOB-SERVICE (see `carry_over_blocked/a106__perturbation_evidence__execution_job_submission__api_job_execution.md`). `runtime_source.py` (hook-era; recorder, method_loop.Leaf, import of perturbation_evidence/episode_contract) was deleted: no module imports it. The old working tree files `binding.py` (ApiJobBinding) and the old `episode.py` were deleted. Note: the old source was read with the git dir `/home/chia/repos/gene_annotation_episode_disk/.git` (the working tree has no `.git`).

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | machinery: the binding's own as_record(); the system records the binding |
| binding_record.py | OperationalBindingRecord.as_record | machinery | machinery: the binding's own as_record(); the system records the binding |
| configuration.py | OperationalConfiguration | episode function | task.py reads ctx.settings (resources, initial_information, handoff_unit, acquired_record_unit; controller profiles in yield_estimator.py); the APIServiceExecution it built is the job_access service (BLOCKED-ON-JOB-SERVICE) |
| configuration.py | OperationalConfiguration.__init__ | episode function | task.py reads ctx.settings (resources, initial_information, handoff_unit, acquired_record_unit; controller profiles in yield_estimator.py); the APIServiceExecution it built is the job_access service (BLOCKED-ON-JOB-SERVICE) |
| credit.py | ExecutionEpisodeCredit | machinery | machinery: old credit mixin class; credit.py credit replaces it |
| credit.py | ExecutionEpisodeCredit._appservice_completion | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller target is the commission completion_target, the verified flag rides in the outcome (completed) |
| credit.py | ExecutionEpisodeCredit._api_operational_credit | episode function | task.service_operation: the executor (job_access api_execute, BLOCKED-ON-JOB-SERVICE) computes operational_credit_from_identities (not in the library: no api_operational_credit exists in episode_support; the job_access api_execute service, BLOCKED-ON-JOB-SERVICE, computes it) and returns it in the outcome; credit.py reads it |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | machinery: credit_kind deleted (README 3d); one episode, one credit |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | machinery: frozen closed-credit snapshot over runtime_* tables, receipts and archive (journal/receipts bookkeeping) |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | episode function | credit.py credit (the service executor credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (the service executor credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (the service executor credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (the service executor credit, returned by task.service_operation in its outcome) |
| credit.py | ExecutionEpisodeCredit._proof_for_action | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller target is the commission completion_target, the verified flag rides in the outcome (completed) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller target is the commission completion_target, the verified flag rides in the outcome (completed) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller target is the commission completion_target, the verified flag rides in the outcome (completed) |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | machinery: completion proof for PracticalYieldEstimator (README 3d/7b); the controller target is the commission completion_target, the verified flag rides in the outcome (completed) |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py decide (resource capabilities, initial information, launch_instruction_library, tool_knowledge); pending_work, child_options, native_expectations, resource estimates, waiting_support were old-runner or other-role context and are not carried |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py decide (resource capabilities, initial information, launch_instruction_library, tool_knowledge); pending_work, child_options, native_expectations, resource estimates, waiting_support were old-runner or other-role context and are not carried |
| decision_inputs.py | _a106_original_global_ValueError | machinery | machinery: old-module global shim of the provider patching |
| decision_inputs.py | _a106_original_global_child_option_information | machinery | machinery: old-module global shim of the provider patching |
| decision_inputs.py | _a106_original_global_set | machinery | machinery: old-module global shim of the provider patching |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| decision_presentation.py | present_credit_state | episode function | task.py decide (current_credit, controller state from internal_summary); the annotation-axis compaction is old-runner presentation, not carried |
| decision_presentation.py | prepare_completed_work | machinery | machinery: completed-work report over runtime_actions (old journal) |
| decision_presentation.py | decision_yield_table | episode function | task.py decide (current_credit, controller state from internal_summary); the annotation-axis compaction is old-runner presentation, not carried |
| decision_presentation.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| decision_state.py | OperationalDecisionState | episode function | messages/internal_summary.py and task.py decide (credit, controller state, report_update); old working_state/visible refs/report deliveries/pending work are old-runner machinery |
| decision_state.py | OperationalDecisionState.decision_state | episode function | messages/internal_summary.py and task.py decide (credit, controller state, report_update); old working_state/visible refs/report deliveries/pending work are old-runner machinery |
| decision_state.py | _a106_original_global_FACT_MEANINGS | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_FACT_SOURCES | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_Mapping | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global__references_in | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_callable | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_getattr | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_isinstance | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_json | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _a106_original_global_sorted | machinery | machinery: old-module global shim of the provider patching |
| decision_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| episode.py | ExecutionEpisode | episode function | episode.py ApiJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py wait_permitted / offered_actions |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | machinery: old registry hook (context_hook_applies) |
| execution_contracts.py | launch_operation_catalog | episode function | task.py catalog_of (the service operation catalog; BLOCKED-ON-JOB-SERVICE job_access api_catalog) and task.capabilities |
| execution_contracts.py | _outcome | episode function | task.py service_operation failure outcome (failure_outcome, already in library: episode_support/tools/unit_outcomes.py) |
| execution_operations.py | OperationalOperations | episode function | task.py TOOLS |
| execution_operations.py | OperationalOperations._api_operation_catalog | episode function | task.py catalog_of (BLOCKED-ON-JOB-SERVICE job_access api_catalog) |
| execution_operations.py | OperationalOperations._resource_information | episode function | task.py resource_capabilities |
| execution_operations.py | OperationalOperations.capabilities | episode function | task.py capabilities tool |
| execution_operations.py | OperationalOperations.resource_tool_contracts | episode function (unplaced) | unplaced: assembles contracts of every resource for the parent commission text; the parent writes its own text (README 3a) |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py catalog_of (BLOCKED-ON-JOB-SERVICE job_access api_catalog) |
| execution_operations.py | OperationalOperations.execute | episode function | task.py service_operation (BLOCKED-ON-JOB-SERVICE job_access api_execute) |
| execution_operations.py | OperationalOperations._appservice_sources | episode function | messages/final_to_parent.py: AppService fact sources (already in library: acquisition/service_calls/bvbrc_application_facts.py application_fact_sources; SUPPORT_SOURCE copied as a constant) |
| execution_state.py | OperationalExecutionState | machinery | machinery: runtime_* table state and receipt inheritance (journal/receipts bookkeeping) |
| execution_state.py | OperationalExecutionState.initialize | machinery | machinery: check of this commission against the parent recorded request (runtime_episodes); a wrong commission fails (rule 1), nothing checks it ahead |
| execution_state.py | OperationalExecutionState._check_parent_inputs | machinery | machinery: runtime_* table state and receipt inheritance (journal/receipts bookkeeping) |
| execution_state.py | OperationalExecutionState._target | machinery | machinery: check of this commission against the parent recorded request (runtime_episodes); a wrong commission fails (rule 1), nothing checks it ahead |
| execution_state.py | OperationalExecutionState._selection | machinery | machinery: check of this commission against the parent recorded request (runtime_episodes); a wrong commission fails (rule 1), nothing checks it ahead |
| execution_state.py | OperationalExecutionState._context_target | machinery | machinery: check of this commission against the parent recorded request (runtime_episodes); a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | OperationalAssignment._api_context | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._permitted | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment.prepare_assignment | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._validate_request | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment._launch | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment._constraints | machinery | machinery: admission of the commission against the parent launch assignment; a wrong commission fails (rule 1), nothing checks it ahead |
| from_parent.py | OperationalAssignment.initial_references | episode function | messages/read_from_parent.py read_from_parent (no initial references) |
| from_parent_launch.py | LaunchParentAssignment | machinery | machinery: the parent launch assignment schema used only for admission of the commission (rule 1) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | machinery | machinery: the parent launch assignment schema used only for admission of the commission (rule 1) |
| goal.py | OperationalGoal | episode function | goal.py GOAL; task.py GOAL_TEXT and instructions |
| goal.py | OperationalGoal.instructions | episode function | goal.py GOAL; task.py GOAL_TEXT and instructions |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_progress) |
| internal_summary.py | OperationalSummary._api_decision_summary | episode function | task.py decide: job_access read api_decision_context (BLOCKED-ON-JOB-SERVICE) |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | task.py resource_capabilities and decide (execution_resource_capabilities, execution_initial_information) |
| internal_summary.py | OperationalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_progress) |
| native_input_custody.py | NativeInputCustody | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._versions | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._selector | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._protein_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._atac_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._atac_inputs | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| native_input_custody.py | NativeInputCustody._selected_result_action | machinery | machinery: checks of this commission and of received native inputs against the parent records (runtime_actions/episodes/report_attempts, retained input authority); not reached by an AppService launch_api role, and a wrong commission fails (rule 1) |
| received_evidence.py | ReceivedOperationalEvidence | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._appservice_received_support_refs | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._appservice_validate_received_report | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._application_received_context | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._application_received_facts | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._application_validate_received_report | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._application_record_admission | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._application_resolve_received | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | machinery: validation and resolution of reports received from a child (runtime_report_attempts, receipts); this episode has no children, nothing is received |
| report_delivery.py | OperationalReportDelivery | episode function | messages/final_to_parent.py final_to_parent (fills the typed form from the recorded facts once) |
| report_delivery.py | OperationalReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (fills the typed form from the recorded facts once) |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| task.py | OperationalTask | episode function | task.py decide/action/TOOLS |
| task.py | OperationalTask.instructions | episode function | task.py instructions |
| task.py | OperationalTask.next | episode function | task.py decide |
| task.py | OperationalTask.apply_response | episode function | task.py action |
| task.py | OperationalTask.execute | episode function | task.py TOOLS (service_operation, capabilities, wait, launch_instructions, tool_knowledge) |
| task.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| task_decision.py | OperationalTaskDecision | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | OperationalTaskDecision.call | episode function | task.py decide (ModelRequest REASONING with the decision context and output_schema) |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | OperationalTaskDecision.interpretation_context | episode function | task.py decide (ModelRequest REASONING with the decision context and output_schema) |
| task_decision.py | OperationalTaskDecision.exchange_schema | episode function | task.py output_schema |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | machinery: decision-exchange loop, model-call recording and contract-information exchange (exchange_decision, runtime_model_calls) |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_OSError | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_TypeError | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_ValidationError | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_ValueError | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global__action_generation_schema | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global__json | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global__plain | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_child_option_information | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_instructional_model_context | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_isinstance | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_len | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_lookup_attempts | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_model_snapshot | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_requested_contract_information | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_schema_failure_diagnostic | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_sqlite3 | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_state_frame | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_str | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _a106_original_global_type | machinery | machinery: old-module global shim of the provider patching |
| task_decision.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| task_instructions.py | instructions | episode function | task.py instructions (the goal text replaces the default instructions) |
| task_state.py | OperationalTaskState | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.__init__ | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.restore | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.record_effect | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | OperationalTaskState.checkpoint | machinery | machinery: per-episode state, restore and checkpoint over runtime_actions and the journal |
| task_state.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py |
| to_parent.py | OperationalReport._application_facts | episode function | messages/final_to_parent.py bvbrc_application_outcomes (library project_application_facts runs in the job service; BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | OperationalReport._application_resolve_own | machinery | machinery: reference resolution for report validation over the old receipts/records (receiving side); the system checks held records |
| to_parent.py | OperationalReport._application_resolve_reference | machinery | machinery: reference resolution for report validation over the old receipts/records (receiving side); the system checks held records |
| to_parent.py | OperationalReport._appservice_report_facts | episode function | messages/final_to_parent.py recorded_facts/fact and messages/internal_summary.py (execution_handoff_refs, support refs, result refs, completion from the outcomes) |
| to_parent.py | OperationalReport.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM (required_return_sources none) |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (required_return_sources none) |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py recorded_facts/fact and messages/internal_summary.py (execution_handoff_refs, support refs, result refs, completion from the outcomes) |
| to_parent.py | OperationalReport._live_facts | episode function | messages/final_to_parent.py recorded_facts/fact and messages/internal_summary.py (execution_handoff_refs, support refs, result refs, completion from the outcomes) |
| to_parent.py | OperationalReport.resolve | machinery | machinery: reference resolution for report validation over the old receipts/records (receiving side); the system checks held records |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report (the form-reference validate_form part is A106 form validation, none called: finding is plain) |
| waiting.py | OperationalTaskWaiting | machinery | machinery: wait suspension/redelivery (suspension_changed) |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | episode function | task.py wait tool (BLOCKED-ON-JOB-SERVICE job_access wait_for_job) |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | machinery: wait suspension/redelivery (suspension_changed) |
| waiting.py | _bind_original_task_runtime_providers | machinery | machinery: provider patching |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py request_yield_class |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController, README 7b) |
| yield_estimator.py | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController, README 7b) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | machinery: PracticalYieldEstimator construction; the completion controller replaces it (README 7b) |
