# A103 resource_work_submission: intent carried over from 97308b94c

Episode path: `a103/gene_context_evidence/resource_work_submission`
Old role name: `launch` (also an entry role). Old class: `ResourceEpisode` (episode.py), decision source `ResourceTask` (task.py).
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/<path>/<file>`. Only files directly in this folder were read. The child folders `api_/hpc_/local_resource_work_execution` were not read here, except to compare the api child with its hpc/local siblings. There is no grading/ or scoring/ subfolder.

## What it is for (goal, in its own words)

goal.py:

> Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

When a contract-information profile is configured, `contract_information_profile()` returns it, and this text is appended:

> Within the pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level form field with only $ref set to episode-fact:<source> to have the host expand and fill that type. Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original job_ref and receiving state allows later work to repair that job without submitting a replacement.

In short, it decides where and how a job from the A103 head is executed: API, local or HPC. It commissions the matching execution child and returns the resulting handoff(s) in the head's form.

## Task and instructions

instructions.py is the same composer as resource_result_acquisition. It uses the old default `INSTRUCTIONS` from `runtime_prompt`, the reasoning rule (`reason` is permitted), the wait text (`wait` is permitted), the pending-delivery text, and the exchange-protocol paragraph. The goal text above comes in as the specialist instructions.

## What it reads from its parent's assignment

from_parent.py:
- The assignment is `LAUNCH_SCHEMA`, the `resource_launch_assignment_v1` record. It wraps C9 LaunchAssignmentV1 losslessly: parent job, input versions, CPU and allocation, search, constraints, `resource_selection` (may be null), and `launch_instructions` pins. `adapter_assignment` is added only after a resource is selected, and it is not a replacement for the parent's job.
- Only declared keys are kept, and they are validated.
- There is no adapter preparation: the admitted assignment is returned as given.

The constraint fields that `_permitted` reads are `resource_selection`, `constraints.allowed_resource_ids`, `constraints.allowed_kinds`, `constraints.resource_id` and `constraints.kind`.

## Children

child_commissioning.py: the child roles are `RESOURCE_ROLES`, a mapping from role to resource kind: `launch_api` -> api, `launch_local` -> local, `launch_hpc` -> hpc. They are offered only when this episode's role is `launch`, and only roles with at least one capability that meets all of these:
- the kind matches;
- the resource is bound to an adapter;
- it has non-empty `tool_names`;
- availability is not `unavailable`;
- it passes `_permitted(assignment, capability)`.

To each child it sends one request per commission, built by `to_child_<kind>_resource_work_execution.assemble_request`. The three copies are identical. Each request contains:
- goal: `EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)`, or a root goal with `result_contract={'role': name}` when there is no parent;
- message: `scope`, `initial_report` (or {}), `inprocess_completion_order` (when configured), `report_contract_declaration` (validated with `validate_saved_fact_form` against the expanded schema; it requires a contract), `job_assignment`, `episode_assignment` (launch instructions materialized first), `gene_context_evidence`, and `knowledge_inheritance` (receipts bound from the parent episode);
- the parent's report contract.

What it takes back: the child's typed form, using this episode's chosen fact sources. For handoff fields, received_messages.py routes on `handoff.resource_selection.kind` to `from_child_<kind>_resource_work_execution.receive_handoff`. That calls the adapter's `received_form_references` proof, or raises `resource_information_handoff_proof_missing`. An unknown kind or a non-builtin handoff goes through the same callback, inline.

## Decision state and what it shows the model

The same fields as resource_result_acquisition. The specialist context is {`role: launch`, `assignment`, `resource_capabilities`, `resource_tool_estimates` from every adapter's `decision_context`}. Execution expectations are captured for `launch`. Child options are added because children are available. `waiting_support` is added.

## Tools offered

operation_catalog.py:
- `resource.capabilities`: reads availability and configured resource information; does not select or submit.
- `resource.inspect {resource_id}`: inspects one declared resource and its binding. It returns distinct failures for unavailable, unknown, unauthenticated and unbound resources (resource_inspection.py), and does not submit.
- `resource.check_handoff {handoff}`: exercises the configured receiving interfaces of a supplied returned handoff, using the adapter's `check_handoff`. It returns `receiving_interface_unavailable` or `invalid_resource_handoff`. It makes no submission or substitution.

There are no adapter tools: execution happens only through children. The common actions are tool, reason, child, wait and redeliver_report. A job_child operational failure and invalid-selection feedback are handled the same as in acquisition.

## Credit

`operational`, via `services.bound_role_credit(context, receiver_selection)`. It is not bounded.

## Continuation

There is no yield_estimator.py and no continuation hook. Continuation was governed by the old runner's controller_binding. The port must choose one of the three yield_control estimators, and the files record no settings.

## What it reports to its parent

Fact sources are `execution_handoff` and `execution_handoffs`, plus every adapter's fact sources, with conflicts raising. The facts merge across all adapters and deduplicate handoffs by identity. `validate_report` runs every adapter's validation, and the handoff fields must equal the recorded facts. Resolution: context first, then any adapter. Finish is the same as the siblings.

## Differences from similar episodes

This is the only episode of the four that has children, `child_request_assembler`, the to_child_/from_child_ files, and the three resource tools without adapter tools. It also aggregates over all adapters, admits its assignment without adapter preparation, and can carry a contract-information profile. Compare resource_result_acquisition, which has a single adapter, and api_resource_work_execution, which has a single adapter plus parent-inheritance checks.

## Files at 97308b94c

| Old file | Lines | This episode's own intent | Old-runner names used (name x count; wf. = self.workflow.) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| action_contract_feedback.py | 46 | Invalid selection feedback: contract-information repair text, `component_native_return_channels_required` detail, BV-BRC minhash results selector input detail, `reads.map` parameter feedback; record rejected effect. | import:a103.read_mapping×1, import:a103.runtime×1, runtime.ContractError×2, runtime.ContractInformationError×1, runtime.Mapping×7, runtime._plain×1, runtime.ReportBoundaryError×1, runtime.schema_failure_diagnostic×1, runtime.ValidationError×2 |
| binding_record.py | 7 | Record `resource_episode_binding_v1`, binding id = this path, adapters' records, optional contract-information profile. | none |
| child_commissioning.py | 27 | Children = RESOURCE_ROLES (`launch_api`, `launch_local`, `launch_hpc`); offered only under role `launch` when a bound capability of that kind has tools, is not unavailable, and is permitted by assignment constraints; per-role request assembler. | BindingContext:parent.assignment×1, BindingContext:parent.role×1 |
| configuration.py | 22 | Explicit resource adapters (required callable API, unique `resource_id`, optional `bind_record_selection`); contract-information profile limited to the one known profile. | import:a103.composition_information×1 |
| credit.py | 13 | Credit kind `operational`; view = `services.bound_role_credit(context, receiver_selection)`. | services.bound_role_credit×1 |
| decision_context.py | 45 | What the model sees (see Decision state section); calls `is_scientific_source` with result ignored. | EpisodeRequest:request.goal×1, EpisodeRequest:request.report_contract×4, import:a103.runtime×1, journal_table:runtime_actions×1, method_view:view.child_reports×2, method_view:view.controller_state×1, method_view:view.model_inputs×1, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, wf.binding_context×1, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| decision_contracts.py | 35 | Exchange envelope validation (same as siblings). | import:a103.runtime×1, runtime.composition_lookup_schema×2, runtime.Draft202012Validator×1, runtime._object×3 |
| decision_exchange.py | 119 | Pending exchange loop; model called directly via `provider.complete` (no presentation renderer). | import:a103.runtime×1, journal_table:runtime_model_calls×2, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×1, runtime._plain×2, runtime._references_in×1, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.provider×2, wf.run_id×1, wf.services×1, wf.store×2, wf.validate_contract_information×1 |
| decision_inputs.py | 69 | As acquisition but execution expectations for role `launch`. | EpisodeRequest:request.message×2, import:a103.episode_work_report×2, import:a103.library.hpc_prompt×1, import:a103.runtime×1, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| episode.py | 25 | Composition; `binding_path`, `commissioning_parent=gene_context_evidence`, `roles=entry_roles=(launch,)`; same permitted actions. | none |
| from_child_api_resource_work_execution.py | 10 | What comes back from an API child: adapter `received_form_references` proof for its handoff. | none |
| from_child_hpc_resource_work_execution.py | 10 | Same for an HPC child. | none |
| from_child_local_resource_work_execution.py | 10 | Same for a local child. | none |
| from_parent.py | 19 | Assignment = `LAUNCH_SCHEMA` (resource_launch_assignment_v1 wrapping C9 LaunchAssignmentV1); admitted as given, no adapter preparation. | BindingContext:parent.role×2 |
| goal.py | 12 | Responsibility text (quoted above); returns the configured contract-information profile, so discovery text about `episode.return_contract` can be appended. | none |
| handoff_check.py | 19 | As acquisition (also imports HANDOFF_SCHEMA, _string). | none |
| initial_references.py | 11 | Initial refs from adapter `initial_references` for role `results`. | BindingContext:context.assignment×1, BindingContext:context.role×1 |
| instructions.py | 26 | Composer over old default INSTRUCTIONS (same composition as table episode's task_instructions). | import:a103.runtime_prompt×1, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×4, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×1, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| internal_summary.py | 16 | Context: role `launch`, assignment, capabilities, estimates from every adapter. | BindingContext:context.assignment×1 |
| operation_catalog.py | 12 | `resource.capabilities`, `resource.inspect`, `resource.check_handoff`; no adapter tools. | none |
| operations.py | 23 | Dispatch of the three resource tools only (no adapter.execute). | none |
| received_messages.py | 62 | Received form refs for returned handoffs; routes by `resource_selection.kind` to the matching from_child_* receiver, else the local callback. | none |
| report_delivery.py | 25 | Same finish as siblings. | EpisodeRequest:request.report_contract×2, import:a103.library.private_policy_call×1, import:a103.library.report_fact_assembly×1, import:a103.runtime×1, journal_table:runtime_forms×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| report_fields.py | 15 | Fact sources `execution_handoff` (one known physical execution or null) and `execution_handoffs` (per registry/handle, latest check) + adapter facts; conflicting definitions raise. | none |
| report_reference_access.py | 11 | Resolve: context, else any adapter. | none |
| resource_contracts.py | 36 | `_failure`, `_outcome`, `_availability_failure` (unavailable / authentication_required / unknown) helpers; re-exports resource schemas. | import:a103.communication×1, import:a103.domain×1, import:a103.episode_bindings×1, import:a103.launch_instructions×1, import:a103.local_resources×1, import:a103.resource_records×1 |
| resource_inspection.py | 15 | `resource.inspect` body: not bound / availability failures. | none |
| resource_selection.py | 36 | As acquisition plus `_permitted(assignment, capability)` constraint filter (resource id/kind, allowed ids/kinds). | BindingContext:context.assignment×1, BindingContext:context.role×1, services.capabilities×1 |
| saved_decision_exchange.py | 81 | Saved exchange authentication (same as siblings). | import:a103.runtime×1, journal_table:runtime_model_calls×1, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2 |
| task.py | 209 | Unit loop; grain `launch`. | EpisodeRequest:request.message×1, import:a103.episode_source_failure×1, import:a103.library.action_contracts×1, import:a103.library.private_policy_call×1, import:a103.providers×1, import:a103.runtime×1, journal_table:runtime_actions×8, journal_table:runtime_episodes×1, journal_table:runtime_model_calls×2, method_view:view.units_consumed×4, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×3, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportRedelivery×2, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×1, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×2, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×2, wf.store×9, wf.validate_report×1 |
| task_decision.py | 82 | Decision call (same as table's call.py, but receipts skipped for job sources and direct `provider.complete`). | import:a103.runtime×1, journal_table:runtime_model_calls×5, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×2, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2 |
| task_state.py | 108 | Same state/restore/checkpoint as siblings. | import:a103.episode_source_failure×1, import:a103.runtime×1, journal_table:runtime_actions×5, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.controller_value×1, wf.execution_binding×4, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, workflow.context(param)×1, workflow.grains(param)×1 |
| to_child_api_resource_work_execution.py | 36 | What is sent to an API child: goal (objective, parent form as result contract), message {scope, initial_report, completion order, validated report_contract_declaration, job_assignment, episode_assignment with materialized launch instructions, gene_context_evidence, knowledge_inheritance}. | import:a103.runtime×1, runtime.ContractInformationError×1, runtime.Episode×2, runtime.EpisodeGoal×2, runtime.EpisodeRequest×1, runtime._plain×3, runtime.Record×1, runtime.validate_saved_fact_form×1, workflow.context(param)×2, workflow.gene_context_evidence_binding(param)×1, workflow.grains(param)×2, workflow.inprocess_completion_order(param)×2, workflow.launch_instructions(param)×1, workflow.legacy_parent_for_path(param)×1, workflow.receipts(param)×2 |
| to_child_hpc_resource_work_execution.py | 36 | Same request for an HPC child. | import:a103.runtime×1, runtime.ContractInformationError×1, runtime.Episode×2, runtime.EpisodeGoal×2, runtime.EpisodeRequest×1, runtime._plain×3, runtime.Record×1, runtime.validate_saved_fact_form×1, workflow.context(param)×2, workflow.gene_context_evidence_binding(param)×1, workflow.grains(param)×2, workflow.inprocess_completion_order(param)×2, workflow.launch_instructions(param)×1, workflow.legacy_parent_for_path(param)×1, workflow.receipts(param)×2 |
| to_child_local_resource_work_execution.py | 36 | Same request for a local child. | import:a103.runtime×1, runtime.ContractInformationError×1, runtime.Episode×2, runtime.EpisodeGoal×2, runtime.EpisodeRequest×1, runtime._plain×3, runtime.Record×1, runtime.validate_saved_fact_form×1, workflow.context(param)×2, workflow.gene_context_evidence_binding(param)×1, workflow.grains(param)×2, workflow.inprocess_completion_order(param)×2, workflow.launch_instructions(param)×1, workflow.legacy_parent_for_path(param)×1, workflow.receipts(param)×2 |
| to_parent.py | 48 | Facts merged across all adapters; same handoff dedupe and equality check. | none |
| waiting.py | 9 | Forwards suspension condition to execution backend. | wf.execution_backend×1, wf.execution_handle×2 |

## Carried over

The carried form is in `gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/resource_work_submission/` (ten files, class `ResourceWorkSubmission(EpisodeBinding)`). One row per row of `runs/carry_over/functions/a103__gene_context_evidence__resource_work_submission.tsv`.

| old file | name | kind | new place (file and name, or machinery reason) |
|---|---|---|---|
| action_contract_feedback.py | ResourceActionContractFeedback | machinery | old-runner machinery: the class wraps the rejected-effect accounting (record_effect, self.feedback); its generic rejection is `action` in task.py (see the method row) |
| action_contract_feedback.py | ResourceActionContractFeedback.reject_invalid_action | episode function | task.py `action` (raises Rejected(rejection_feedback(error, category='action_contract'))); library: model_exchange/rejection_feedback.py::rejection_feedback. The contract-information repair text, component_native_return_channels_required detail, BV-BRC minhash selector input detail and reads.map parameter feedback are not carried (they served the decision exchange and other tools, none of which this episode offers); `self.record_effect(index, 'rejected')` is machinery |
| binding_record.py | ResourceBindingRecord | machinery | binding_record.py / the binding's own as_record() is deleted |
| binding_record.py | ResourceBindingRecord.as_record | machinery | binding's own as_record() is deleted (settings and declared services are recorded by the system) |
| child_commissioning.py | ResourceChildCommissioning | episode function | task.py CHILD_SLOTS, allowed_children; messages/msg_to_child.py |
| child_commissioning.py | ResourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS = {launch_api, launch_local, launch_hpc: child binding paths} |
| child_commissioning.py | ResourceChildCommissioning.allowed_children | episode function | task.py `allowed_children(assignment, capabilities, bound_ids)` (the slots offered in the action schema by `decide`/`action`) |
| child_commissioning.py | ResourceChildCommissioning.child_request_assembler | machinery | binding lookup of the request owner (README 3b C1); the three assemblers are messages/msg_to_child.py `msg_to_child` |
| configuration.py | ResourceConfiguration | machinery | configuration values are the run's settings (ctx.settings) and the declared service `resource_adapter`; the adapters' required-callable check and duplicate resource_id check are the service's |
| configuration.py | ResourceConfiguration.__init__ | machinery | settings (`cost`, `parameters`, `tool_knowledge_directory`, `launch_instructions_directory`) and service `resource_adapter` (README 3d); `bind_record_selection` is gone with record_selection; the contract-information profile check belongs to the decision exchange (not carried) |
| credit.py | ResourceCredit | episode function | credit.py `credit` |
| credit.py | ResourceCredit.credit_kind | machinery | credit_kind is deleted (README 3d); every resource role was `operational` |
| credit.py | ResourceCredit.credit_view | episode function | credit.py `credit(summary, records)` (the adapters' credit view is measured by the resource tools of task.py and rides in their outcome as adapter_credit) |
| decision_context.py | ResourceDecisionContext | episode function | messages/internal_summary.py `internal_summary` (what comes from the view) and task.py `_context` (what comes from ctx) |
| decision_context.py | ResourceDecisionContext.decision_state | episode function | messages/internal_summary.py `internal_summary` (own outcomes, credit, feedback, controller state via yield_table) and task.py `_context`; the runtime_actions SQL, visual evidence, receipt_projection, pending_work, report_deliveries and report-update parts are machinery and are not carried |
| decision_contracts.py | ResourceDecisionContracts | machinery | decision-exchange loop |
| decision_contracts.py | ResourceDecisionContracts.exchange_schema | machinery | decision-exchange loop (composition_lookup_schema) |
| decision_contracts.py | ResourceDecisionContracts.exchange_response | machinery | decision-exchange loop (request_context / select_action envelope) |
| decision_exchange.py | ResourceDecisionExchange | machinery | decision-exchange loop; the model call is the ModelRequest of `decide` |
| decision_exchange.py | ResourceDecisionExchange.conversation_key | machinery | conversation state (README 3a) |
| decision_exchange.py | ResourceDecisionExchange.interpretation_context | machinery | decision-exchange loop |
| decision_exchange.py | ResourceDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision is not carried; lookups are tools) |
| decision_inputs.py | ResourceDecisionInputs | episode function | task.py `_context` |
| decision_inputs.py | ResourceDecisionInputs.decision_inputs | episode function | task.py `_context` (launch_instruction_library, selected_launch_instructions, child_options, resource_tool_estimates and native_event_targets through the service read handles, tool_knowledge, time_accounting) and `decide`; completed_action_reports from internal_summary. Not carried: resource_context, shared_information_context, pending_work, hpc request history, job_execution_options and the execution_expectations capture (they read the old workflow object; the adapter's duration information is the `decision_context` member of the `resource_adapter` service) |
| episode.py | ResourceEpisode | episode function | episode.py `ResourceWorkSubmission(EpisodeBinding)` |
| episode.py | ResourceEpisode.permitted_common_actions | episode function | task.py `_schema` (tool, reason, child, wait are offered; redeliver_report is not carried) |
| from_child_api_resource_work_execution.py | receive_handoff | machinery | received-handoff proof is custody: the child returns the handoff records in a record_refs field (messages/read_from_child.py) |
| from_child_hpc_resource_work_execution.py | receive_handoff | machinery | received-handoff proof is custody: the child returns the handoff records in a record_refs field (messages/read_from_child.py) |
| from_child_local_resource_work_execution.py | receive_handoff | machinery | received-handoff proof is custody: the child returns the handoff records in a record_refs field (messages/read_from_child.py) |
| from_parent.py | ResourceFromParent | episode function | messages/read_from_parent.py |
| from_parent.py | ResourceFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per LAUNCH_SCHEMA property, same names; library schema records/hpc/resource_records.py::LAUNCH_SCHEMA) |
| from_parent.py | ResourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py `read_from_parent` (keeps the schema properties and validates them with `_validate`; the check that the parent role owns the child role is machinery) |
| goal.py | ResourceGoal | episode function | goal.py GOAL; task.py `_instructions` |
| goal.py | ResourceGoal.contract_information_profile | machinery | contract-information profile belongs to the decision exchange (request_context / episode.return_contract); not carried |
| goal.py | ResourceGoal.instructions | episode function | goal.py GOAL (old responsibility text and common tail, unchanged); the discovery paragraph is decision-exchange text and is not carried; task.py `_instructions` appends it to the model instructions |
| handoff_check.py | ResourceHandoffCheck | episode function | task.py `resource_check_handoff` |
| handoff_check.py | ResourceHandoffCheck.check_selected_handoff | episode function | task.py tool `resource_check_handoff` (async; `receiving_interface_unavailable`, `invalid_resource_handoff`; the adapter is the service `resource_adapter`, members `can_check_handoff`, `check_handoff`) |
| initial_references.py | ResourceInitialReferences | machinery | initial references of the role `results` (a different episode); this episode's records travel in assignment record_refs (scope_refs, input_refs) |
| initial_references.py | ResourceInitialReferences.initial_references | machinery | only answered for the role `results`, which this episode does not have; record passing is custody (record_refs fields) |
| instructions.py | instructions | episode function | task.py `_instructions` (old default INSTRUCTIONS and REASONING_COMMIT_REQUIREMENT from library literature/prompts/gene_context_evidence/literature_investigation_prompt.py, the history/children span replaced with replace_span, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, the native-events text); the pending-delivery, pending_child_ wait and request_context protocol paragraphs are not carried |
| internal_summary.py | ResourceInternalSummary | episode function | messages/internal_summary.py `internal_summary`; task.py `_context` |
| internal_summary.py | ResourceInternalSummary.decision_context | episode function | task.py `_context` (role, assignment, resource_capabilities, resource_tool_estimates) and messages/internal_summary.py; the capabilities and estimates are service reads made in `decide` |
| operation_catalog.py | ResourceOperationCatalog | episode function | task.py CATALOG |
| operation_catalog.py | ResourceOperationCatalog.catalog | episode function | task.py CATALOG (resource.capabilities, resource.inspect, resource.check_handoff) and `_schema` |
| operations.py | ResourceOperations | episode function | task.py TOOLS and `action` |
| operations.py | ResourceOperations.execute | episode function | task.py tools `resource_capabilities`, `resource_inspect`, `resource_check_handoff` (dispatch is the ToolCall of `action`; the argument validation is the action schema) |
| received_messages.py | _parent_name_ValueError | machinery | hook-era name helper of the received-handoff callback; custody replaces the callback |
| received_messages.py | _parent_name_getattr | machinery | hook-era name helper of the received-handoff callback; custody replaces the callback |
| received_messages.py | ResourceReceivedMessages | machinery | receipts bookkeeping (received_form_references); custody: the child returns the handoff records in record_refs |
| received_messages.py | ResourceReceivedMessages.received_form_references | machinery | receipts bookkeeping (F3/F5): the proof of a returned handoff is the `returned` receipt; messages/read_from_child.py reads the returned records |
| received_messages.py | _handoff_receiver | machinery | routing of the received-handoff proof by resource kind; custody replaces it |
| report_delivery.py | ResourceReportDelivery | episode function | messages/final_to_parent.py |
| report_delivery.py | ResourceReportDelivery.finish | episode function | messages/final_to_parent.py `final_to_parent` (facts, credit = completion['credit'], finding, validate_report before return); saving of runtime_forms, form_with_facts, pending_handles and release are machinery |
| report_fields.py | ResourceReportFields | episode function | messages/final_to_parent.py RETURN_FORM |
| report_fields.py | ResourceReportFields.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (execution_handoff, execution_handoffs, adapter_facts selectable, execution_handoff_refs selectable; credit and finding required). The adapters' own fact sources are one selectable field `adapter_facts` (a form is fixed at class definition) |
| report_reference_access.py | ResourceReportReferenceAccess | machinery | report reference resolution through the old resolver; custody (`records.holds`) |
| report_reference_access.py | ResourceReportReferenceAccess.resolve | machinery | old resolver of report references; "does this episode hold the reference" is `records.holds(ref)` (README 3b D2) |
| resource_contracts.py | _failure | episode function | task.py `_failure` (private copy) |
| resource_contracts.py | _outcome | episode function | task.py `_outcome` (private copy) |
| resource_contracts.py | _availability_failure | episode function | task.py `_availability_failure` (private copy) |
| resource_inspection.py | ResourceInspection | episode function | task.py `resource_inspect` |
| resource_inspection.py | ResourceInspection.inspect_resource | episode function | task.py tool `resource_inspect` |
| resource_selection.py | ResourceResourceSelection | episode function | task.py `capabilities_of`, `_permitted`; the adapter lookup is the service `resource_adapter` |
| resource_selection.py | ResourceResourceSelection.capabilities | episode function | task.py `capabilities_of(declared, adapter_capabilities, bound_ids)` (services.capabilities() is the service member `declared_capabilities`; the per-adapter tool-bound check was only for a selected resource and is not made here) |
| resource_selection.py | ResourceResourceSelection._adapter | machinery | adapter lookup by selection; the adapters are the service `resource_adapter` (members take the handoff or assignment) |
| resource_selection.py | ResourceResourceSelection._permitted | episode function | task.py `_permitted` (private copy) |
| saved_decision_exchange.py | ResourceSavedDecisionExchange | machinery | saved-request checks (README 3a: deleted; the system compares a rebuilt model request with its record) |
| saved_decision_exchange.py | ResourceSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request check (deleted) |
| saved_decision_exchange.py | ResourceSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request check (deleted) |
| task.py | ResourceTask | episode function | task.py `decide`, `action`, TOOLS |
| task.py | ResourceTask.next | machinery | the decision loop, restore/inprocess replay, SourceEnd and the model-call recovery are the system's; the model request is `decide` |
| task.py | ResourceTask.apply_response | episode function | task.py `action` (decoding, schema validation, reason envelope and empty_reasoning_commit rejection, unheld named-record rejection; raises Rejected). The report_update validation, delivery resolution, EventTargetError feedback, job_child failure feedback and record_effect are machinery |
| task.py | ResourceTask.execute | episode function | task.py tools `reason` (commit_reasoning through ctx.store with ctx.operation_key), `wait` (selected_wait over the `native_events` service), the three resource tools; ChildCall for `child`. The journal rows, controller_value, receive_outcome, automatic_score_updates and last_observed_credit are machinery |
| task_decision.py | ResourceTaskDecision | episode function | task.py `decide` |
| task_decision.py | ResourceTaskDecision.call | episode function | task.py `decide` (ModelRequest('REASONING', instructions, context, generation_schema(schema))); the model-call saving, transport digests, receipts and exchange protocol are machinery |
| task_decision.py | ResourceTaskDecision.instructions | episode function | task.py `_instructions` |
| task_state.py | ResourceTaskState | machinery | task state, restore and checkpoint (the system restores the view) |
| task_state.py | ResourceTaskState.__init__ | machinery | task state (view outcomes replace it) |
| task_state.py | ResourceTaskState.bind_execution_context | machinery | execution context binding of the old runner |
| task_state.py | ResourceTaskState.record_execution_failure | machinery | record_execution_failure: a tool returns its failure as its outcome (README 3c) |
| task_state.py | ResourceTaskState.restore_checkpoint | machinery | restore_checkpoint |
| task_state.py | ResourceTaskState.restore | machinery | restore |
| task_state.py | ResourceTaskState.record_effect | machinery | record_effect |
| task_state.py | ResourceTaskState.checkpoint | machinery | checkpoint |
| to_child_api_resource_work_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_api: assignment of launch fields + scope, scope_refs, input_refs, completion_target; message scope + initial_report; selection of the child's declared return fields). goal/EpisodeGoal, report_contract_declaration validation, inprocess_completion_order, knowledge_inheritance and the identity are machinery |
| to_child_hpc_resource_work_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_hpc; same body as the api one) |
| to_child_local_resource_work_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_local; same body as the api one) |
| to_parent.py | ResourceToParent | episode function | messages/final_to_parent.py |
| to_parent.py | ResourceToParent.facts | episode function | messages/final_to_parent.py `handoff_facts(adapter_facts, handoffs)` (merge, de-duplicate by (capability_binding_ref, execution_handle), single handoff); the adapters' facts come through the outcome of the check tool (`facts`) and the children's handoffs through the child reports |
| to_parent.py | ResourceToParent.validate_report | episode function | messages/final_to_parent.py `validate_report(result, facts)` (every reported handoff field equals the recorded facts; called by `final_to_parent` before it returns). The per-adapter `adapter.validate_report` is not carried (the adapters are a service, and final_to_parent has none) |
| waiting.py | ResourceWaiting | machinery | suspension of an execution handle by the old runner |
| waiting.py | ResourceWaiting.suspension_changed | machinery | wait/suspension machinery of the old runner (set_suspension on the execution backend); the wait itself is task.py tool `wait` |
