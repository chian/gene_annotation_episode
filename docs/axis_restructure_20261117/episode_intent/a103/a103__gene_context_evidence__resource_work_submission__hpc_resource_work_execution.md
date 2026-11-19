# a103/gene_context_evidence/resource_work_submission/hpc_resource_work_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/resource_work_submission/hpc_resource_work_execution/<file>`
(32 files directly in this folder, 1 266 lines; no `grading/`, `scoring/` or `tests/` subfolder). Old binding class
`ResourceEpisode` (`binding_path = 'gene_context_evidence/resource_work_submission/hpc_resource_work_execution'`,
`commissioning_parent = 'gene_context_evidence/resource_work_submission'`, `roles = ('launch_hpc',)`,
`entry_roles = ()`), decision source `ResourceTask`. A leaf: it commissions no children.

Compared with its siblings: this folder is byte-identical to `local_resource_work_execution` and
`api_resource_work_execution` except for the role name `launch_hpc` (in `decision_inputs.py`, `episode.py`,
`internal_summary.py`, `task.py`), the binding id (`binding_record.py`, `episode.py`) and the one-sentence
responsibility in `goal.py`. Against the parent `resource_work_submission`, 16 files are identical blobs
(configuration, credit, decision_context, decision_contracts, decision_exchange, initial_references, instructions,
report_delivery, report_fields, resource_contracts, resource_selection, saved_decision_exchange, task_decision,
task_state, waiting, action_contract_feedback); the files that differ from the parent are child_commissioning,
from_parent, goal, handoff_check, internal_summary, operation_catalog, operations, received_messages,
report_reference_access, resource_inspection, to_parent, binding_record, decision_inputs, episode, task.

## What it is for (its goal, in its own words)

`goal.py` `instructions()`:

> Investigate the selected actual environment, queue, staging and execution interfaces. Revise later choices from
> actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job,
> input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without
> selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the
> original parent-defined typed form. Only the configured local controller governs continuation.

When `contract_information_profile(context)` is not `None` (in this file it always returns `None`, so the branch is
dormant) a discovery paragraph is appended: request `composition_information` / `episode.return_contract` for the
exact frozen fact contract, fill top-level fields with `$ref: episode-fact:<source>`, and keep the original
`job_ref` and receiving state so a later episode can repair an uncertain handoff without resubmitting.

So: given an already-chosen HPC resource (Aurora in this project) and the parent's fixed job, carry the job to that
resource's queue/staging/execution interfaces through the resource adapter's own tools, and return a usable
execution handoff (registry + execution handle) to the parent.

## Task and instructions

- `task.py` (`ResourceTask.next`, `apply_response`, `execute`): one decision per turn. Replays recorded actions on
  resume, takes a ready owned child return, otherwise builds `decision_state(view)` plus the private action schema
  (`library.action_contracts.action_schema`), calls the model, validates the selection. Selection kinds handled:
  `reason` (commits a reasoning payload to the store; rejects an all-empty commit unless the specialist says it has
  task content or `evidence_processing.kind == 'no_applicable_evidence'`), `wait`, `tool`, `redeliver_report`, and
  job-child failure feedback for `job_child`. The report update is admitted with `validate_form` and checked with
  `validate_report(..., grain='launch_hpc')`. Every executed action (completed, failed, invalid) is journalled with
  its result and credit and staged as a controller input; a model-call failure records a source failure and ends
  the source with `SourceEnd('source_failed')`. A rejected selection is recorded as a `rejected` effect, not an
  executed action.
- `instructions.py`: the default runtime `INSTRUCTIONS` (or the job episode's instructions when this is a job
  source), plus specialist text, the reasoning-commit requirement when `reason` is allowed, tool-knowledge and
  launch-instruction-library text, a fixed paragraph on `pending_child_delivery` / `redeliver_report`, a paragraph
  on `wait` for `pending_child_` handles, a paragraph on `native_event_targets`, and, under the decision-exchange
  protocol, replacement of the fresh-conversation history guidance with "use request_context ... read
  `episode.history` view=records".
- `goal.py` text above; `task_decision.instructions` calls `self.workflow.services.instructions(self, context)`.
- `episode.py` `permitted_common_actions`: `('tool', 'reason', 'child', 'wait', 'redeliver_report')`.

## What it reads from its parent's assignment

`from_parent.py`:
- `assignment_schema(role)` = deep copy of `LAUNCH_SCHEMA` (`resource_launch_assignment_v1`, from the old
  `resource_records`), after checking the role with `credit_kind`.
- `prepare_assignment(parent, role, selection, scope, operation_key)`: keeps only schema properties, validates; when
  the commissioning parent's role is `launch` the role must be a resource role; every LAUNCH_SCHEMA property except
  `resource_selection` must equal the parent's (inherited) assignment, `adapter_assignment` is dropped from the
  inherited copy; `launch_instructions` pins must keep the parent's library id and every parent section
  (entry_id, section_id, sha256) — else `launch_instruction_inheritance_conflict`; an inherited non-null
  `resource_selection` must be kept. `resource_selection` must be explicit, name a declared capability of kind
  `RESOURCE_ROLES[role]` and satisfy the constraints (`_permitted`: allowed_resource_ids, allowed_kinds,
  resource_id, kind). The adapter then prepares the actual assignment
  (`adapter.prepare_assignment(parent, role, selected, scope, operation_key)`).
- `decision_inputs.py` also reads `episode_assignment.launch_instructions` (materialized launch instructions) and
  `job_assignment` (for execution expectations and report validation) from the request message.

## Children

None. `child_commissioning.py`: `child_roles(role)` returns `()` and `allowed_children` returns `()`. `child` is
still a permitted common action, so the old runner could offer `child_options`, but this episode owns no child role.
It does see a parent's/its own `pending_child_` handles for `wait` and `pending_child_delivery` repair via the
instructions.

## Decision state and what it shows the model

`decision_context.py` `decision_state(view)` (inside a store read snapshot):
- `working_state`, last `image.view` visual inputs (from `runtime_actions`), `last_local_outcome` (preview) and
  `feedback`, `visible_record_refs` computed from those plus the report forms (own interpretation schema and, unless
  annotation-axis credit, each child report's schema), scoped by `reference_subset`.
- `goal`, `scope`, `current_credit` (or `{mode: annotation_axis_credit, root_score}`), `current_evidence_vector`,
  `investigation_progress` (retained_finding_count, inactive_dependencies, detail_pages) when receipt projection is
  on, `credit_binding`, `time_accounting` (journal elapsed view), `pending_work`, `report_deliveries`,
  `controller` and `controller_binding`, `tools` (catalog), `tool_knowledge`, `job_episode_options`,
  `available_report_facts` (FACT_SOURCES with meanings, plus extra sources; replaced by
  `tools.model_contract_catalog` when present), `requested_report_purpose`, `requested_form`,
  `current_report_update`, `current_report_basis_refs`, and the lifecycle line "Interpretations are the last actual
  reasoning basis; later tool outcomes are facts, not a new judgment."
- Under annotation-axis credit: working state emptied, controller reduced to arms/annotation_credits/root_score/
  decision, a child action's outcome reduced to counts.
- Monitoring-information credit fields, specialist decision context, and `_completed_work_axis_results`
  (a103_sheet, target_sheets, tool_attachments, source_contributions).

`decision_inputs.py` adds, per fresh decision: `resource_context`, `shared_information_context`,
`launch_instruction_library` and `selected_launch_instructions`, `child_options` (when child roles exist),
binding-supplied initial context (conflict raises), `completed_action_reports` (unless literature / annotation-axis),
`requested_action_history` when `is_hpc_context(context)`, `pending_work`, `execution_expectations` captured for
`launch_hpc` (with `job_execution_options` query_ref/cpu/search_mode/execution_class_ref when the job config has
`search_modes`, else prospective execution classes), `resource_tool_estimates` from the resource estimator (job
sample or context), `native_execution_expectations` and their estimates, `native_event_targets`, `waiting_support`
when `wait` is allowed, and `contract_information_profile`.

`internal_summary.py` (the binding's decision context): `role: 'launch_hpc'`, the assignment, all
`resource_capabilities`, and `resource_tool_estimates` from the selected adapter's `decision_context`.

Decision exchange (`decision_exchange.py`, `decision_contracts.py`, `saved_decision_exchange.py`): under the
exchange protocol the model may answer `request_context` (lookup: `child_options`, `composition_information`
operation, or own attempt history) any number of times before `select_action` with `selection` + `report_update`;
each exchange is saved and replayed; the snapshot includes an action-yield table; contract-information profile
frames are authenticated against the saved originals.

## Tools it offers

`operation_catalog.py` / `operations.py`:
- `resource.capabilities` — read actual capability availability and configured resource information; selects or
  submits nothing.
- `resource.inspect` (handled in `resource_inspection.py`) — one capability by `resource_id`; failure
  `resource_not_bound` or the availability failure (`resource_unavailable`, `resource_authentication_required`,
  `resource_availability_unknown`).
- `resource.check_handoff` (`handoff_check.py`) — the adapter's `check_handoff` on a handoff; missing callback ->
  `receiving_interface_unavailable`; error -> `invalid_resource_handoff` (identity conflict re-raised).
- Every tool in the selected adapter's `catalog(context)` (authoritative), executed by `adapter.execute`. A tool not
  in the catalogue raises `tool_not_owned_by_resource_role`; arguments are validated against the tool's schema.
  (`resource.inspect`/`resource.check_handoff` are dispatched here but only offered if the adapter lists them.)
- Common actions: `reason`, `wait`, `redeliver_report` (and `child`, with no child roles).

`resource_selection.py`: capabilities come from services plus bound adapters; unbound declarations are shown with
empty `tool_names`; a selected adapter's declared tool names must all be in its catalogue.
`configuration.py`: adapters must expose `capability, as_record, prepare_assignment, catalog, execute, fact_sources,
facts, resolve, validate_report, credit_view`, unique `resource_id`; optional `bind_record_selection`; the only
accepted contract-information profile is `composition_information.CONTRACT_INFORMATION_PROFILE`.

## Credit

`credit.py`: `credit_kind(role)` is `'operational'` for every known role (unknown role raises);
`credit_view(context, receiver_selection)` is `self.services.bound_role_credit(context, receiver_selection)` (credit
computed by the bound role service/adapter, not by this episode). In `task.py` each observed action's credit is
`source_credit_view(self)['credit']` after `automatic_score_updates`; a `wait` takes `last_observed_credit`; a
`shared.read_information` tool also retains shared grading results. Credit is stored unmodified in the action row;
no bound/clamp.

## Continuation

No yield estimator file in this folder. Goal text: "Only the configured local controller governs continuation."
The controller value per action is `controller_value(self, index, credit)`; the model sees an action-yield table
built by old `yield_table(journal, episode_id, before=index, parameters=_category_yield_parameters(controller_binding))`
(annotation-axis mode instead shows the root controller's arms). Settings come from `controller_binding`, not from
this folder. For the new runner this is an operational launch episode: the intended estimator is the
completion-with-a-target kind (a verified usable handoff completes the target), but the folder itself does not name
one; that choice is the porter's.

## What it reports to its parent

`report_fields.py` fact sources:
- `execution_handoff` (object|null): latest original usable received or own check when exactly one physical
  execution is known; null for zero or several. No new check at closure.
- `execution_handoffs` (array): per distinct (registry, execution handle) the usable check with latest checked_at,
  identity order.
- plus each adapter's `fact_sources(role)` (a conflicting definition raises).

`to_parent.py` `facts`: merges adapter facts, deduplicates handoffs by
`(resource_selection.capability_binding_ref, execution_handle)`, sorts them, and sets `execution_handoff` only for
exactly one identity. `validate_report`: the adapter validates, then any form field with `x-source`
execution_handoff(s) must equal those facts (`resource_handoff_fact_mismatch`).
`received_messages.py`: references carried by handoff-sourced form fields are resolved through the adapter's
`received_form_references` (missing -> `resource_information_handoff_proof_missing`).
`report_reference_access.py`: a reference resolves if it is in context (`reference_in_context`) or the adapter
resolves it. `initial_references.py`: only for role `results` (never this episode's role) the adapter's initial
references.
`report_delivery.py` `finish`: without a report contract returns `{credit, pending_handles, current report facts}`;
otherwise the saved `runtime_forms` form, or a form filled from private report facts plus interpretations, saved
once; releases the episode either way.

## File-by-file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `action_contract_feedback.py` | 46 | invalid-selection feedback: schema diagnostic, contract error code/field, repair text for `closed_top_level_form_required`, schema_reason, `component_native_return_channels_required` fact sources + repair, BV-BRC MinHash results-selector input detail, `reads.map` parameter feedback; records `rejected` effect | `from root.a103.runtime import` (AcquisitionError ... validate_form), `_live_original_runtime.*` (ContractError, ContractInformationError, ValidationError, ReportBoundaryError, Mapping, _plain, schema_failure_diagnostic), `root.a103.read_mapping.parameter_schema_failure` |
| `binding_record.py` | 7 | record `resource_episode_binding_v1`, binding id, adapters' records, optional profile | — |
| `child_commissioning.py` | 12 | no child roles | — (imports RESOURCE_ROLES unused) |
| `configuration.py` | 22 | adapter contract (10 required methods), unique ids, `bind_record_selection`, single allowed profile | `root.a103.composition_information.CONTRACT_INFORMATION_PROFILE`, `services` object (old binding services) |
| `credit.py` | 13 | operational credit kind; credit view from bound role credit | `self.services.bound_role_credit` |
| `decision_context.py` | 45 | the decision state fields listed above | `self.workflow.` store, working_state, journal (db, row, elapsed_view), run_id, local_outcome_preview, source_credit_view, receipt_projection, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, is_scientific_source, specialist, binding_context, tools; table `runtime_actions`; runtime FACT_MEANINGS, FACT_SOURCES, _references_in, _plain |
| `decision_contracts.py` | 35 | exchange envelope: `request_context` (lookup) or `select_action` (selection, report_update) | runtime `_object`, `composition_lookup_schema(self.workflow, self)`, Draft202012Validator |
| `decision_exchange.py` | 119 | pending-decision lookup loop, retries, conversation continuation, lookups child_options / composition_information / own attempts | `self.workflow.` provider (conversation_key, complete), store, decision_exchanges, journal (measure, save), validate_contract_information, controller_binding, services.decision_exchange_instructions, execute, run_id; tables `runtime_model_calls`; old yield `_category_yield_parameters`, `yield_table`; runtime model_snapshot, state_frame, instructional_model_context, requested_contract_information, child_option_information, lookup_attempts, _action_generation_schema, DECISION_CONTEXT_VERSION |
| `decision_inputs.py` | 69 | fresh decision inputs listed above, `launch_hpc` execution expectations | `self.workflow.` resource_context, shared_information_context, launch_instructions, available_child_roles, episode_bindings.initial_decision_context, binding_context, pending_work, execution_expectations, job_episodes, store, resource_estimator, is_job_source, native_estimation_context, native_event_information, permits_common_action, waiting_support; `root.a103.episode_work_report` (completed_action_reports, requested_action_history), `root.a103.library.hpc_prompt.is_hpc_context`; runtime child_option_information |
| `episode.py` | 25 | binding identity, role `launch_hpc`, permitted common actions, adapter API docstring | composition of mixins (old binding class); `decision_source_type`, `commissioning_parent`, `entry_roles` (old binding-table attributes) |
| `from_parent.py` | 47 | assignment schema and preparation rules above; launch-instruction pin inheritance | `parent.role`, `parent.assignment` (old BindingContext); old `resource_records` schemas via resource_contracts |
| `goal.py` | 12 | goal text | — |
| `handoff_check.py` | 19 | `resource.check_handoff` behaviour | — |
| `initial_references.py` | 11 | results-role initial references from adapter | `context.role`, `context.assignment` (BindingContext) |
| `instructions.py` | 26 | instruction composition and the fixed paragraphs | `source.workflow.` job_episodes, is_job_source, specialist, binding_context, permits_common_action, knowledge, launch_instructions, native_event_information, decision_protocol; `root.a103.runtime_prompt` (INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, DECISION_EXCHANGE_PROTOCOL) |
| `internal_summary.py` | 16 | `launch_hpc` summary with capabilities and tool estimates | `context.assignment` (BindingContext) |
| `operation_catalog.py` | 11 | `resource.capabilities` tool + adapter catalogue | — |
| `operations.py` | 25 | tool dispatch | — |
| `received_messages.py` | 31 | handoff-sourced received references via adapter | — |
| `report_delivery.py` | 25 | closure form / no-contract record, release | `self.workflow.` source_credit_view, pending_handles, episode_bindings.current_report_facts, binding_context, release, journal, facts; table `runtime_forms`; `library.report_fact_assembly.facts`, `library.private_policy_call.invoke`; runtime Record, form_with_facts |
| `report_fields.py` | 15 | execution_handoff(s) fact definitions | — |
| `report_reference_access.py` | 11 | reference resolution | `reference_in_context(self.services, ...)` (episode_bindings) |
| `resource_contracts.py` | 36 | module doc (C7/C9 assignment versions), `_failure`, `_outcome`, `_availability_failure` | `root.a103.communication` (ReportBoundaryError, plain), `root.a103.domain.obj`, `root.a103.episode_bindings.reference_in_context`, `root.a103.resource_records` (ROLES, RESOURCE_ROLES, LAUNCH/RESULTS versions and schemas, _validate ...), `root.a103.launch_instructions.validate_selection`, `root.a103.local_resources.LocalResources` (unused) |
| `resource_inspection.py` | 15 | `resource.inspect` | — |
| `resource_selection.py` | 36 | capability list, adapter lookup, permission constraints | `self.services.capabilities` |
| `saved_decision_exchange.py` | 81 | authenticate contract-profile exchange frames/history | `self.workflow.` validate_contract_information, decision_exchanges, journal, contract_information_reply; table `runtime_model_calls`; runtime apply_state_frame, model_snapshot, instructional_model_context, is_contract_information, CONTRACT_INFORMATION_OPERATIONS, WorkflowError |
| `task.py` | 209 | the action loop, selection admission, `grain='launch_hpc'`, execution/credit per action | `self.workflow.` journal, inprocess_replay, store, selected, execution_binding, completions, completed_unit, next_return, resolve_pending_deliveries, action_schema, delivery_resolution_inputs, decision_exchanges, permits_common_action, reasoning_action_schema, specialist, binding_context, resolver, validate_report, run_id, perform_selected_wait, execute, pending_work, receive_native_outcome, receive_outcome, automatic_score_updates, last_observed_credit, source_credit_view, retain_shared_grading_results, controller_value; tables `runtime_episodes`, `runtime_actions`, `runtime_model_calls`; `providers.ModelCallError`, `episode_source_failure.record_source_failure`, `library.action_contracts.action_schema`, `library.private_policy_call.invoke`; runtime SourceEnd, ReportRedelivery, ActionFailure, EventTargetError, observes_action_outcome, validate_form, _decode_recorded_action_response |
| `task_decision.py` | 82 | one decision call, saved-request replay, protocol checks | `self.workflow.` journal, contract_information_profile, validate_contract_information, numerical_contracts, decision_protocol, decision_exchanges, freeze_literature_numerical_contracts, freeze_contract_information, receipts.receive (kind `decision_input`), is_job_source, uses_received_record_context, provider (has_session, complete), history_preview, services.instructions; table `runtime_model_calls`; runtime DECISION_EXCHANGE_PROTOCOL, _ASSIGNMENT_TRANSPORT, _recorded_assignment_transport, _digest, WorkflowError |
| `task_state.py` | 108 | source state fields, execution-failure recording as a failed action with credit, restore/checkpoint | `self.workflow.` context, grains, archive, store, run_id, journal, source_credit_view, controller_value, execution_binding, completions (restore_source, record_decision_effect, checkpoint_source, stage), inprocess_replay, recover_commissions, progress_provider; table `runtime_actions`; runtime Episode.identity, ActionLeaf, EFFECT_VERSION, interpretation_schema, Record; `episode_source_failure.record_source_failure` |
| `to_parent.py` | 48 | facts merge/dedupe, handoff fact check | `context.assignment` (BindingContext) |
| `waiting.py` | 9 | suspension condition to execution backend | `self.workflow.execution_handle`, `self.workflow.execution_backend` |

## Carried over

Carried 19 November 2026 into the ten-file form. The old files could not be read in this step (the working tree has no git history to read `97308b94c` from); the sibling carry of the same episode in A101 (`a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution`) and the intent record above were the source, with the A103 prompt text and transport modules of `episode_support`. Library candidates (kept in the episode file because the library has no copy): task.py `_failure`, `_outcome`, `_availability_failure`, `_permitted`, `capabilities_of`, `_named_refs`, `_empty_commit`; messages/final_to_parent.py `handoff_facts`. Every other function is placed below or is machinery.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_contract_feedback.py | ResourceActionContractFeedback | episode function | task.py: action (the rejection part) |
| action_contract_feedback.py | ResourceActionContractFeedback.reject_invalid_action | episode function | task.py: action (Rejected(rejection_feedback(error, category='action_contract')) in the library's feedback form); the contract-information, component-return-channel, BV-BRC minhash and reads.map repair hints are not carried (old text not readable, see carry_over_blocked) |
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
| episode.py | ResourceEpisode | episode function | episode.py: HpcResourceWorkExecution |
| episode.py | ResourceEpisode.permitted_common_actions | episode function | task.py: _schema (tool, reason, wait branches; no child and no redeliver_report) |
| from_parent.py | ResourceFromParent | episode function | messages/read_from_parent.py |
| from_parent.py | ResourceFromParent.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM |
| from_parent.py | ResourceFromParent._require_launch_child_instruction_pins | machinery | check of a commission against the parent's pins; a wrong commission fails, no check is carried |
| from_parent.py | ResourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py: read_from_parent (explicit selection, kind hpc) and task.py: prepare_resource_assignment (capability, _permitted, bound, adapter prepare); the parent-equality checks are not carried |
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
