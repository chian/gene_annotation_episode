# A103 api_resource_work_execution: intent carried over from 97308b94c

Episode path: `a103/gene_context_evidence/resource_work_submission/api_resource_work_execution`
Old role name: `launch_api` (not an entry role). Old class: `ResourceEpisode` (episode.py), decision source `ResourceTask` (task.py).
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/<path>/<file>`. Only files directly in this folder were read; it has no grading/ or scoring/ subfolder.

## What it is for (goal, in its own words)

goal.py:

> Investigate execution through the selected actual API or service, including real availability and authentication. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

In short, it runs the assigned job through one selected API or service resource, using that adapter's tools, and returns the handoff. `contract_information_profile()` returns None, so the discovery text is never added.

## Task and instructions

instructions.py: the old default `INSTRUCTIONS` composition, with the reasoning rule and wait text, the same as its parent. The goal text comes in as the specialist instructions.

## What it reads from its parent's assignment

from_parent.py:
- The schema is `LAUNCH_SCHEMA` (`resource_launch_assignment_v1`). Declared keys are kept and validated.
- If the parent role is `launch`, the role must be a resource role.
- Inheritance from a `launch` parent (resource_work_submission):
  - The parent assignment is taken without `adapter_assignment`.
  - Every `LAUNCH_SCHEMA` property except `resource_selection` and `launch_instructions` must equal the parent's (`resource_assignment_conflict`).
  - `launch_instructions` must keep the parent's library and every parent (entry_id, section_id, sha256) pin (`launch_instruction_inheritance_conflict`).
  - If the parent fixed a `resource_selection`, the child's must equal it (`resource_selection_conflict`).
- An explicit `resource_selection` is required (`explicit_resource_selection_required`). Its capability must exist, have kind `RESOURCE_ROLES['launch_api']` (api), and pass `_permitted`.
- The selected adapter's `prepare_assignment` then produces the final assignment, which adds `adapter_assignment`.

## Children

None. `child_roles` and `allowed_children` return `()`.

## Decision state and what it shows the model

The same fields as resource_result_acquisition. The specialist context is {`role: launch_api`, `assignment`, `resource_capabilities`, selected adapter `resource_tool_estimates`}. Execution expectations are for `launch_api`. `waiting_support` is shown.

## Tools offered

`resource.capabilities` plus the selected API adapter's catalogue, dispatched to `adapter.execute`. `resource.inspect` and `resource.check_handoff` have dispatch branches but are not catalogued. The common actions are tool, reason, child (with no children), wait and redeliver_report.

## Credit

`operational`, via `services.bound_role_credit`. It is not bounded.

## Continuation

There is no yield_estimator.py. In the old runner, the runner's controller_binding governed continuation. The port must choose one of the three estimators, and the files record no settings.

## What it reports to its parent

Fact sources are `execution_handoff` and `execution_handoffs`, plus the adapters' fact sources. The facts come from the selected adapter only, with deduplicated handoffs. The handoff fields must equal the recorded facts. The parent receives these handoffs through `from_child_api_resource_work_execution.receive_handoff`, which applies the adapter's `received_form_references` proof.

## Differences from similar episodes

- Siblings `hpc_resource_work_execution` and `local_resource_work_execution` are identical apart from the goal's first sentence, the role, and the binding_path. Their first sentences are:
  - hpc: "Investigate the selected actual environment, queue, staging and execution interfaces.";
  - local: "Investigate preparation, execution and receiving interfaces on the selected local resource.".
- Versus resource_result_acquisition, this episode:
  - uses `LAUNCH_SCHEMA` instead of `RESULTS_SCHEMA`;
  - checks inheritance from its parent;
  - requires an explicit api selection that passes `_permitted`;
  - is not an entry.

## Files at 97308b94c

| Old file | Lines | This episode's own intent | Old-runner names used (name x count; wf. = self.workflow.) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| action_contract_feedback.py | 46 | Invalid selection feedback: contract-information repair text, `component_native_return_channels_required` detail, BV-BRC minhash results selector input detail, `reads.map` parameter feedback; record rejected effect. | import:a103.read_mapping×1, import:a103.runtime×1, runtime.ContractError×2, runtime.ContractInformationError×1, runtime.Mapping×7, runtime._plain×1, runtime.ReportBoundaryError×1, runtime.schema_failure_diagnostic×1, runtime.ValidationError×2 |
| binding_record.py | 7 | Record `resource_episode_binding_v1`, binding id = this path, adapters' records, optional contract-information profile. | none |
| child_commissioning.py | 12 | No children (`()` for every parent). | BindingContext:parent.role×1 |
| configuration.py | 22 | Explicit resource adapters (required callable API, unique `resource_id`, optional `bind_record_selection`); contract-information profile limited to the one known profile. | import:a103.composition_information×1 |
| credit.py | 13 | Credit kind `operational`; view = `services.bound_role_credit(context, receiver_selection)`. | services.bound_role_credit×1 |
| decision_context.py | 45 | What the model sees (see Decision state section); calls `is_scientific_source` with result ignored. | EpisodeRequest:request.goal×1, EpisodeRequest:request.report_contract×4, import:a103.runtime×1, journal_table:runtime_actions×1, method_view:view.child_reports×2, method_view:view.controller_state×1, method_view:view.model_inputs×1, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, wf.binding_context×1, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| decision_contracts.py | 35 | Exchange envelope validation (same as siblings). | import:a103.runtime×1, runtime.composition_lookup_schema×2, runtime.Draft202012Validator×1, runtime._object×3 |
| decision_exchange.py | 119 | Pending exchange loop; model called directly via `provider.complete` (no presentation renderer). | import:a103.runtime×1, journal_table:runtime_model_calls×2, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×1, runtime._plain×2, runtime._references_in×1, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.provider×2, wf.run_id×1, wf.services×1, wf.store×2, wf.validate_contract_information×1 |
| decision_inputs.py | 69 | As acquisition but execution expectations for role `launch_api`. | EpisodeRequest:request.message×2, import:a103.episode_work_report×2, import:a103.library.hpc_prompt×1, import:a103.runtime×1, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| episode.py | 25 | Composition; `binding_path`, `commissioning_parent=resource_work_submission`, `roles=(launch_api,)`, `entry_roles=()`; same permitted actions. | none |
| from_parent.py | 47 | Assignment = `LAUNCH_SCHEMA`; under a `launch` parent every launch field except resource_selection must equal the parent's, parent instruction pins retained, parent resource selection kept; explicit `resource_selection` of kind `api`, permitted by constraints; then adapter prepares. | BindingContext:parent.assignment×1, BindingContext:parent.role×2 |
| goal.py | 12 | Responsibility text (quoted above); no contract-information profile. | none |
| handoff_check.py | 19 | `resource.check_handoff` body: adapter `check_handoff` or `receiving_interface_unavailable`; invalid -> `invalid_resource_handoff` (identity conflict re-raised). | none |
| initial_references.py | 11 | Initial refs from adapter `initial_references` for role `results`. | BindingContext:context.assignment×1, BindingContext:context.role×1 |
| instructions.py | 26 | Composer over old default INSTRUCTIONS (same composition as table episode's task_instructions). | import:a103.runtime_prompt×1, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×4, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×1, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| internal_summary.py | 16 | Context: role `launch_api`, assignment, capabilities, selected adapter estimates. | BindingContext:context.assignment×2 |
| operation_catalog.py | 11 | `resource.capabilities` + the selected adapter's catalogue. | BindingContext:context.assignment×1 |
| operations.py | 25 | Dispatch: capabilities, inspect, check_handoff, else adapter.execute (inspect/check_handoff not in this catalogue, so unreachable here). | BindingContext:context.assignment×1 |
| received_messages.py | 31 | Received form refs: for `execution_handoff(s)` fields, adapter `received_form_references` proof, else `resource_information_handoff_proof_missing`. | none |
| report_delivery.py | 25 | Same finish as siblings. | EpisodeRequest:request.report_contract×2, import:a103.library.private_policy_call×1, import:a103.library.report_fact_assembly×1, import:a103.runtime×1, journal_table:runtime_forms×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| report_fields.py | 15 | Fact sources `execution_handoff` (one known physical execution or null) and `execution_handoffs` (per registry/handle, latest check) + adapter facts; conflicting definitions raise. | none |
| report_reference_access.py | 11 | Resolve: context first, else selected adapter. | BindingContext:context.assignment×1 |
| resource_contracts.py | 36 | `_failure`, `_outcome`, `_availability_failure` (unavailable / authentication_required / unknown) helpers; re-exports resource schemas. | import:a103.communication×1, import:a103.domain×1, import:a103.episode_bindings×1, import:a103.launch_instructions×1, import:a103.local_resources×1, import:a103.resource_records×1 |
| resource_inspection.py | 15 | `resource.inspect` body: not bound / availability failures. | none |
| resource_selection.py | 36 | As acquisition plus `_permitted` constraint filter. | BindingContext:context.assignment×1, BindingContext:context.role×1, services.capabilities×1 |
| saved_decision_exchange.py | 81 | Saved exchange authentication (same as siblings). | import:a103.runtime×1, journal_table:runtime_model_calls×1, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2 |
| task.py | 209 | Unit loop; grain `launch_api`. | EpisodeRequest:request.message×1, import:a103.episode_source_failure×1, import:a103.library.action_contracts×1, import:a103.library.private_policy_call×1, import:a103.providers×1, import:a103.runtime×1, journal_table:runtime_actions×8, journal_table:runtime_episodes×1, journal_table:runtime_model_calls×2, method_view:view.units_consumed×4, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×3, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportRedelivery×2, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×1, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×2, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×2, wf.store×9, wf.validate_report×1 |
| task_decision.py | 82 | Decision call (same as table's call.py, but receipts skipped for job sources and direct `provider.complete`). | import:a103.runtime×1, journal_table:runtime_model_calls×5, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×2, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2 |
| task_state.py | 108 | Same state/restore/checkpoint as siblings. | import:a103.episode_source_failure×1, import:a103.runtime×1, journal_table:runtime_actions×5, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.controller_value×1, wf.execution_binding×4, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, workflow.context(param)×1, workflow.grains(param)×1 |
| to_parent.py | 48 | Facts merged from selected adapter; handoffs deduplicated by (capability_binding_ref, execution_handle); report handoff fields must equal recorded facts. | BindingContext:context.assignment×2 |
| waiting.py | 9 | Forwards suspension condition to execution backend. | wf.execution_backend×1, wf.execution_handle×2 |

## Carried over

Carried 19 November 2026 into the ten-file form. The old files could not be read in this step (the working tree has no git history to read `97308b94c` from); the sibling carry of the same episode in A101 (`a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution`) and the intent record above were the source, with the A103 prompt text and transport modules of `episode_support`. Library candidates (kept in the episode file because the library has no copy): task.py `_failure`, `_outcome`, `_availability_failure`, `_permitted`, `capabilities_of`, `_named_refs`, `_empty_commit`; messages/final_to_parent.py `handoff_facts`. Every other function is placed below or is machinery.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_contract_feedback.py | ResourceActionContractFeedback | episode function | task.py: action (the rejection part) |
| action_contract_feedback.py | ResourceActionContractFeedback.reject_invalid_action | episode function | task.py: _action_feedback (called by action: generic rejection_feedback plus the reads.map parameter diagnostic via library readers/sequence_alignment/gene_context_evidence/read_mapping.py::parameter_schema_failure); the contract-information, component-return-channel and BV-BRC minhash hints served child commissions and report forms this episode does not have, so they are not carried |
| binding_record.py | ResourceBindingRecord | machinery | binding record (resource_episode_binding_v1); deleted |
| binding_record.py | ResourceBindingRecord.as_record | machinery | the binding's own as_record(); deleted |
| child_commissioning.py | ResourceChildCommissioning | episode function | task.py: CHILD_SLOTS = {} (no children) |
| child_commissioning.py | ResourceChildCommissioning.child_roles | episode function | task.py: CHILD_SLOTS = {} |
| child_commissioning.py | ResourceChildCommissioning.allowed_children | episode function | task.py: CHILD_SLOTS = {} |
| configuration.py | ResourceConfiguration | episode function | task.py: SERVICES = ('resource_adapter', 'native_events'); settings read via ctx.settings (cost, parameters, tool_knowledge_directory, launch_instructions_directory) |
| configuration.py | ResourceConfiguration.__init__ | episode function | explicit adapters keyed by resource_id become the service resource_adapter (not built, blocked); the contract-information profile is not carried (goal returned None) |
| credit.py | ResourceCredit | episode function | credit.py: credit |
| credit.py | ResourceCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ResourceCredit.credit_view | episode function | credit.py: credit (adapter credit view value returned by task.py: resource_operation as adapter_credit) |
| decision_context.py | ResourceDecisionContext | episode function | messages/internal_summary.py: internal_summary and task.py: _context |
| decision_context.py | ResourceDecisionContext.decision_state | episode function | messages/internal_summary.py: internal_summary; task.py: _context (what comes from ctx) |
| decision_contracts.py | ResourceDecisionContracts | machinery | decision-exchange envelope; no exchange inside a decision |
| decision_contracts.py | ResourceDecisionContracts.exchange_schema | machinery | decision-exchange loop |
| decision_contracts.py | ResourceDecisionContracts.exchange_response | machinery | decision-exchange loop |
| decision_exchange.py | ResourceDecisionExchange | machinery | decision-exchange loop (a lookup is a tool: task.py knowledge_lookup, launch_instruction_lookup) |
| decision_exchange.py | ResourceDecisionExchange.conversation_key | machinery | conversation state; deleted |
| decision_exchange.py | ResourceDecisionExchange.interpretation_context | machinery | decision-exchange loop |
| decision_exchange.py | ResourceDecisionExchange.exchange_decision | machinery | decision-exchange loop; the model call is the ModelRequest returned by task.py: decide |
| decision_inputs.py | ResourceDecisionInputs | episode function | task.py: _context |
| decision_inputs.py | ResourceDecisionInputs.decision_inputs | episode function | task.py: _context (tool knowledge, launch instruction library and selection, native event targets, time accounting, resource estimates); execution expectations and waiting-support text: task.py NATIVE_EVENTS and the adapter's decision_context read |
| episode.py | ResourceEpisode | episode function | episode.py: ApiResourceWorkExecution |
| episode.py | ResourceEpisode.permitted_common_actions | episode function | task.py: _schema (tool, reason, wait branches; no child and no redeliver_report) |
| from_parent.py | ResourceFromParent | episode function | messages/read_from_parent.py |
| from_parent.py | ResourceFromParent.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM |
| from_parent.py | ResourceFromParent._require_launch_child_instruction_pins | machinery | check of a commission against the parent's pins; a wrong commission fails, no check is carried |
| from_parent.py | ResourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py: read_from_parent (explicit selection, kind api) and task.py: prepare_resource_assignment (capability, _permitted, bound, adapter prepare); the parent-equality checks are not carried |
| goal.py | ResourceGoal | episode function | goal.py: GOAL, UNIT, RESULT |
| goal.py | ResourceGoal.contract_information_profile | episode function | not carried: returned None, nothing to place |
| goal.py | ResourceGoal.instructions | episode function | goal.py: GOAL; task.py: _instructions |
| handoff_check.py | ResourceHandoffCheck | episode function | task.py: resource_operation (check_handoff branch) |
| handoff_check.py | ResourceHandoffCheck.check_selected_handoff | episode function | task.py: resource_operation (adapter check_handoff; invalid_resource_handoff; identity conflict re-raised) |
| initial_references.py | ResourceInitialReferences | episode function | messages/read_from_parent.py: input_refs field (new field) |
| initial_references.py | ResourceInitialReferences.initial_references | episode function | messages/read_from_parent.py: input_refs; the adapter's initial_references member is not placed (see carry_over_blocked) |
| instructions.py | instructions | episode function | task.py: _instructions |
| internal_summary.py | ResourceInternalSummary | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | ResourceInternalSummary.decision_context | episode function | messages/internal_summary.py: internal_summary; task.py: _context |
| operation_catalog.py | ResourceOperationCatalog | episode function | task.py: _catalog |
| operation_catalog.py | ResourceOperationCatalog.catalog | episode function | task.py: _catalog (resource.capabilities + adapter catalog) |
| operations.py | ResourceOperations | episode function | task.py: TOOLS (resource_capabilities, resource_operation) |
| operations.py | ResourceOperations.execute | episode function | task.py: resource_capabilities, resource_operation |
| received_messages.py | ResourceReceivedMessages | machinery | receipts bookkeeping (received_form_references) |
| received_messages.py | ResourceReceivedMessages.received_form_references | machinery | receipts bookkeeping; handoff records are returned in custody (execution_handoff_refs) |
| report_delivery.py | ResourceReportDelivery | machinery | report delivery; final_to_parent returns the result |
| report_delivery.py | ResourceReportDelivery.finish | machinery | report_form/delivery machinery; messages/final_to_parent.py: final_to_parent |
| report_fields.py | ResourceReportFields | episode function | messages/final_to_parent.py: RETURN_FORM |
| report_fields.py | ResourceReportFields.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (execution_handoff, execution_handoffs, adapter_facts) |
| report_reference_access.py | ResourceReportReferenceAccess | machinery | report reference resolver (custody); deleted |
| report_reference_access.py | ResourceReportReferenceAccess.resolve | machinery | report reference resolver (custody); deleted |
| resource_contracts.py | _failure | episode function | task.py: _failure |
| resource_contracts.py | _outcome | episode function | task.py: _outcome |
| resource_contracts.py | _availability_failure | episode function | task.py: _availability_failure |
| resource_inspection.py | ResourceInspection | episode function | task.py: resource_operation (inspect branch) |
| resource_inspection.py | ResourceInspection.inspect_resource | episode function | task.py: resource_operation (inspect branch; reachable only when the adapter catalog names it) |
| resource_selection.py | ResourceResourceSelection | episode function | task.py: capabilities_of, _capabilities, _permitted |
| resource_selection.py | ResourceResourceSelection.capabilities | episode function | task.py: capabilities_of, _capabilities |
| resource_selection.py | ResourceResourceSelection._adapter | episode function | task.py: ctx.services['resource_adapter'] (service) |
| resource_selection.py | ResourceResourceSelection._permitted | episode function | task.py: _permitted |
| saved_decision_exchange.py | ResourceSavedDecisionExchange | machinery | saved-request checks; the system compares a rebuilt request on resume |
| saved_decision_exchange.py | ResourceSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request checks |
| saved_decision_exchange.py | ResourceSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request checks |
| task.py | ResourceTask | episode function | task.py: decide, action, TOOLS |
| task.py | ResourceTask.next | episode function | task.py: decide (the loop is the system's) |
| task.py | ResourceTask.apply_response | episode function | task.py: action |
| task.py | ResourceTask.execute | episode function | task.py: TOOLS (resource_operation, reason, wait, lookups); child and redeliver_report not carried |
| task_decision.py | ResourceTaskDecision | episode function | task.py: decide, _context, _instructions |
| task_decision.py | ResourceTaskDecision.call | episode function | task.py: decide (ModelRequest), _context |
| task_decision.py | ResourceTaskDecision.instructions | episode function | task.py: _instructions |
| task_state.py | ResourceTaskState | machinery | task state, restore and checkpoint |
| task_state.py | ResourceTaskState.__init__ | machinery | task state; the state is the view's summary |
| task_state.py | ResourceTaskState.bind_execution_context | machinery | old runner binding |
| task_state.py | ResourceTaskState.record_execution_failure | machinery | failed action is the tool's returned outcome (README 3c) |
| task_state.py | ResourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | ResourceTaskState.restore | machinery | checkpoint/restore |
| task_state.py | ResourceTaskState.record_effect | machinery | recorder |
| task_state.py | ResourceTaskState.checkpoint | machinery | checkpoint/restore |
| to_parent.py | ResourceToParent | episode function | messages/final_to_parent.py |
| to_parent.py | ResourceToParent.facts | episode function | messages/final_to_parent.py: handoff_facts, final_to_parent |
| to_parent.py | ResourceToParent.validate_report | episode function | messages/final_to_parent.py: validate_report (called in final_to_parent) |
| waiting.py | ResourceWaiting | machinery | suspension machinery (the wait tool is task.py: wait) |
| waiting.py | ResourceWaiting.suspension_changed | machinery | suspension forwarding to the execution backend |
