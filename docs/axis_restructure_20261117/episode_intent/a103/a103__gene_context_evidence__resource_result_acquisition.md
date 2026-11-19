# A103 resource_result_acquisition: intent carried over from 97308b94c

Episode path: `a103/gene_context_evidence/resource_result_acquisition`
Old role name: `results` (also an entry role). Old class: `ResourceEpisode` (episode.py), decision source `ResourceTask` (task.py).
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/<path>/<file>`. Only files directly in this folder were read; it has no grading/ or scoring/ subfolder.

## What it is for (goal, in its own words)

goal.py:

> Acquire the requested data through the supplied receiving interface; the scientific parent interprets it. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

In short: given a handoff from finished execution work, this episode gets the requested result data through that resource's receiving interface. It does not interpret the science; the A103 head (`gene_context_evidence`) does that.

`contract_information_profile()` returns None, so the `episode.return_contract` discovery sentence is never appended here, even though configuration.py accepts and records a profile.

## Task and instructions

instructions.py composes the old default `INSTRUCTIONS` and `REASONING_COMMIT_REQUIREMENT` texts from `runtime_prompt`. This episode imports them and does not copy them. The composition matches the table episode:
1. job or default text;
2. specialist instructions, i.e. the goal text above;
3. the reasoning rule, which applies because `reason` is permitted;
4. tool knowledge and the launch library;
5. the pending delivery repair text;
6. the wait text, which applies because `wait` is permitted;
7. the native-event text, when native events are configured;
8. the exchange-protocol history paragraph.

The intent is the same instruction set as the literature episodes, plus the goal above.

The adapter API (episode.py docstring) is:
- `resource_id`, `capability()`, `as_record()`, `prepare_assignment(context, role, launch_assignment, scope, operation_key)`;
- `catalog(context)`, `execute(context, tool_name, arguments, operation_key)`;
- `fact_sources(role)`, `facts(context, completion_snapshot)`;
- `resolve(context, reference, namespace)`, `validate_report(context, form, original_schema)`, `credit_view(context, receiver_selection)`;
- optional `decision_context(context)` for prospective duration;
- optional `check_handoff`, `initial_references`, `received_form_references`, `bind_record_selection`.

"An adapter's tool list is authoritative."

## What it reads from its parent's assignment

from_parent.py:
- The assignment is `RESULTS_SCHEMA`, the `resource_results_assignment_v1` record. It carries `handoff` (the returned execution handoff with its `resource_selection`) and `requested_data_selector`, per the resource_contracts.py docstring.
- Unknown keys are dropped, the rest is validated, and the adapter named by `handoff.resource_selection.resource_id` prepares the final assignment.
- If the parent role is `launch`, the role must be a resource role.
- From the request it also takes the initial report, the report contract, and `episode_assignment.launch_instructions`. It also takes `job_assignment`, used for execution expectations and report validation.

## Children

None. `child_roles` and `allowed_children` return `()`.

## Decision state and what it shows the model

decision_context.py shows the same fields as the table episode: goal, scope, working_state, visible refs, credit, evidence vector, investigation progress, credit binding, time accounting, pending work, last outcome, feedback, visual evidence, report deliveries, controller and controller binding, tools, tool knowledge, job options, report facts, requested purpose and form, current report update and basis, and lifecycle. It has no annotation_context update. It calls `is_scientific_source`, but the result is not used.

The specialist context (internal_summary.py) is {`role: results`, `assignment`, `resource_capabilities`, `resource_tool_estimates` from the selected adapter's `decision_context`}.

decision_inputs.py matches the table episode, with these changes:
- execution expectations are for `results`;
- a job source gets `resource_estimator.estimate(..., job_ref, latest_sample)`;
- `waiting_support` is added because `wait` is permitted.

## Tools offered

operation_catalog.py offers `resource.capabilities` plus the selected adapter's `catalog(context)`. `resource.capabilities` reads availability and does not select or submit.

operations.py validates arguments against the catalogue and then dispatches:
- capabilities: listed here;
- inspect and check_handoff: these branches exist, but neither tool is in this catalogue, so they are unreachable;
- any other tool: `adapter.execute`.

Common actions are `tool`, `reason`, `child` (with no children), `wait` and `redeliver_report`.

Reasoning: `apply_response` rejects an all-empty reasoning commit (`empty_reasoning_commit`) unless `evidence_processing.kind == no_applicable_evidence` or the specialist says the selection has task content.

Feedback for a rejected action (action_contract_feedback.py) covers:
- contract-information repair text;
- the `component_native_return_channels_required` field, missing fact sources and repair;
- for a `results` child with selector `bvbrc_minhash_result_selector_v2`, the affected input detail;
- for `reads.map`, parameter schema feedback.

A storage, control or acquisition error in a `job_child` selection becomes `job_assignment` failure feedback, and the selection is recorded as rejected.

## Credit

credit.py sets `credit_kind = 'operational'` for any role in `ROLES`. The view is `services.bound_role_credit(context, receiver_selection)`. Credit is read after observed outcomes as in the siblings. Wait actions take the last observed credit. Credit is not bounded.

## Continuation

There is no yield_estimator.py, and no continuation hook in this folder. In the old runner the runner's `controller_binding` and `_category_yield_parameters` governed continuation. The goal text says only the configured local controller governs continuation. The episode files record no estimator or settings, so the port must choose one of the three. Bounded quality, or completion with a target, fits operational acquisition best, but that is not recorded intent.

## What it reports to its parent

report_fields.py declares these fact sources:
- `execution_handoff`: the latest usable received or own check when exactly one physical execution is known, otherwise null. No new check is made at closure.
- `execution_handoffs`: for each distinct registry/execution handle, the usable check with the latest `checked_at`, in identity order.
- the adapter's own fact sources. A definition that conflicts raises `resource_fact_definition_conflict`.

to_parent.py `facts`:
- merges the selected adapter's facts;
- deduplicates handoffs by (`capability_binding_ref`, `execution_handle`);
- sets `execution_handoff` only when there is one identity.

`validate_report` runs the adapter's validation, then requires every `execution_handoff(s)` field to equal the recorded facts (`resource_handoff_fact_mismatch`). References resolve in context first, then through the adapter. Received handoff fields need the adapter's `received_form_references` proof (`resource_information_handoff_proof_missing`).

report_delivery.py finishes the same way as the siblings: credit and pending handles without a contract, otherwise the parent form filled from facts and interpretations, saved once.

## Differences from similar episodes

- Versus `resource_work_submission` (`launch`):
  - acquisition uses only the one selected adapter (`_adapter(context.assignment)`) for catalogue, facts, resolve and validation, where submission uses all adapters;
  - acquisition offers adapter tools, but not `resource.inspect` or `resource.check_handoff`;
  - acquisition has no children;
  - the adapter prepares the assignment, and the schema is `RESULTS_SCHEMA` rather than `LAUNCH_SCHEMA`;
  - acquisition has no contract-information profile.
- Versus `api_resource_work_execution`: the code is the same apart from schema and role, the parent-inheritance checks, and the goal text.

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
| decision_inputs.py | 69 | As literature episodes but expectations for role `results`, job-source resource estimate branch, plus `waiting_support` when wait permitted. | EpisodeRequest:request.message×2, import:a103.episode_work_report×2, import:a103.library.hpc_prompt×1, import:a103.runtime×1, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| episode.py | 25 | Composition; `binding_path`, `commissioning_parent='gene_context_evidence'`, `roles=entry_roles=('results',)`, permits `tool, reason, child, wait, redeliver_report`; adapter API docstring. | none |
| from_parent.py | 18 | Assignment = `RESULTS_SCHEMA` (resource_results_assignment_v1: handoff + requested_data_selector), restricted to declared keys; adapter of the handoff's resource prepares it. | BindingContext:parent.role×1 |
| goal.py | 12 | Responsibility text (quoted above); contract-information profile None, so no discovery text. | none |
| handoff_check.py | 19 | `resource.check_handoff` body: adapter `check_handoff` or `receiving_interface_unavailable`; invalid -> `invalid_resource_handoff` (identity conflict re-raised). | none |
| initial_references.py | 11 | Initial refs from adapter `initial_references` for role `results`. | BindingContext:context.assignment×1, BindingContext:context.role×1 |
| instructions.py | 26 | Composer over old default INSTRUCTIONS (same composition as table episode's task_instructions). | import:a103.runtime_prompt×1, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×4, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×1, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| internal_summary.py | 16 | Context: role, assignment, resource capabilities, adapter `resource_tool_estimates`. | BindingContext:context.assignment×2 |
| operation_catalog.py | 11 | `resource.capabilities` + the selected adapter's catalogue. | BindingContext:context.assignment×1 |
| operations.py | 25 | Dispatch: capabilities, inspect, check_handoff, else adapter.execute (inspect/check_handoff not in this catalogue, so unreachable here). | BindingContext:context.assignment×1 |
| received_messages.py | 31 | Received form refs: for `execution_handoff(s)` fields, adapter `received_form_references` proof, else `resource_information_handoff_proof_missing`. | none |
| report_delivery.py | 25 | Same finish as siblings. | EpisodeRequest:request.report_contract×2, import:a103.library.private_policy_call×1, import:a103.library.report_fact_assembly×1, import:a103.runtime×1, journal_table:runtime_forms×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| report_fields.py | 15 | Fact sources `execution_handoff` (one known physical execution or null) and `execution_handoffs` (per registry/handle, latest check) + adapter facts; conflicting definitions raise. | none |
| report_reference_access.py | 11 | Resolve: context first, else selected adapter. | BindingContext:context.assignment×1 |
| resource_contracts.py | 36 | `_failure`, `_outcome`, `_availability_failure` (unavailable / authentication_required / unknown) helpers; re-exports resource schemas. | import:a103.communication×1, import:a103.domain×1, import:a103.episode_bindings×1, import:a103.launch_instructions×1, import:a103.local_resources×1, import:a103.resource_records×1 |
| resource_inspection.py | 15 | `resource.inspect` body: not bound / availability failures. | none |
| resource_selection.py | 31 | Capabilities: declared (unbound get no tools) + adapters' (identity and tool binding checked); `_adapter` from handoff or resource_selection. | BindingContext:context.assignment×1, BindingContext:context.role×1, services.capabilities×1 |
| saved_decision_exchange.py | 81 | Saved exchange authentication (same as siblings). | import:a103.runtime×1, journal_table:runtime_model_calls×1, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2 |
| task.py | 209 | Unit loop; `apply_response` adds empty reasoning commit rejection and job_child operational failure feedback; grain `results`. | EpisodeRequest:request.message×1, import:a103.episode_source_failure×1, import:a103.library.action_contracts×1, import:a103.library.private_policy_call×1, import:a103.providers×1, import:a103.runtime×1, journal_table:runtime_actions×8, journal_table:runtime_episodes×1, journal_table:runtime_model_calls×2, method_view:view.units_consumed×4, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×3, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportRedelivery×2, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×1, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×2, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×2, wf.store×9, wf.validate_report×1 |
| task_decision.py | 82 | Decision call (same as table's call.py, but receipts skipped for job sources and direct `provider.complete`). | import:a103.runtime×1, journal_table:runtime_model_calls×5, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×2, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2 |
| task_state.py | 108 | Same state/restore/checkpoint as siblings. | import:a103.episode_source_failure×1, import:a103.runtime×1, journal_table:runtime_actions×5, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.controller_value×1, wf.execution_binding×4, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, workflow.context(param)×1, workflow.grains(param)×1 |
| to_parent.py | 48 | Facts merged from selected adapter; handoffs deduplicated by (capability_binding_ref, execution_handle); report handoff fields must equal recorded facts. | BindingContext:context.assignment×2 |
| waiting.py | 9 | Forwards suspension condition to execution backend. | wf.execution_backend×1, wf.execution_handle×2 |
