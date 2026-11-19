# resource_result_acquisition (A101) — intent of the old files

Episode folder: `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/resource_result_acquisition`

Source read: only this folder's own files at commit `97308b94c` (22 files, 1,249 lines; no `grading/` or `scoring/` subfolder; `tests/` holds only an empty `__init__.py`). Nothing outside the episode tree was read at that commit. Old-runner names per file are counted in `runs/carry_over/calls/a101_04.tsv`.

Old role name in the files: `results`. Old binding path: `sequence_homology_evidence/resource_result_acquisition`. Commissioning parent: `sequence_homology_evidence` (the A101 head). It could also be a run entry (`entry_roles = ('results',)`).

## What this episode is for

Its goal text (`goal.py`), verbatim:

> Acquire the requested data through the supplied receiving interface; the scientific parent interprets it. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

So: given a handoff from work that was already submitted to some resource, fetch the requested data through that resource's receiving interface and hand it back. It does not interpret the data scientifically and does not submit work.

`goal.py` also holds a "discovery" paragraph about `episode.return_contract` lookups, added only when a contract-information profile applies. In this episode `contract_information_profile` returns a profile only for the old role `launch`, so the paragraph is never added here.

## Task and instructions

`task_instructions.py` holds the whole base instruction text inside this folder (`INSTRUCTIONS`, one long string beginning "You own an iterative scientific annotation improvement, not a tool itinerary."), plus `REASONING_COMMIT_REQUIREMENT`. It is the general annotation-investigation text; nothing in it is specific to acquiring results. The episode-specific part is the goal text above. Composition order for each decision:

1. `INSTRUCTIONS`;
2. the goal text, appended on a new line;
3. `REASONING_COMMIT_REQUIREMENT` (reasoning is permitted here): "A common scientific reason action needs at least one proposed commit row. A request with every commit section empty is rejected before acquisition and creates no completed-action observation. ..." ;
4. tool-knowledge instructions, when `tool_knowledge` is in the decision context;
5. launch-instruction-library instructions, when `launch_instruction_library` is in the decision context;
6. the pending-child-delivery paragraph ("When pending_child_delivery is supplied, ... this repair does not select new scientific work.");
7. the wait paragraph (waiting is permitted here): "A pending_child_ handle names your original in-process child, not an external event-provider target. ... Waiting only reports readiness and earns no scientific credit. ...";
8. when native event information is configured, the native-event-targets paragraph ("The separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. ... No event probability, gain or scientific credit follows from registration or passing time alone.");
9. under the `decision_exchange_v1` protocol, the passage from "On a fresh provider conversation," up to "Do not execute native provider tools." is replaced by the `request_context` / `episode.history` paragraph.

The model call is the plain provider call (`provider.complete(episode_id, 'REASONING', instructions, context, schema)`), with no prompt renderer. This already has the shape of the one model provider's `complete`.

Action kinds this episode may select (`episode.py: permitted_common_actions`): `tool`, `reason`, `child`, `wait`, `redeliver_report`. It declares no children, so `child` and `redeliver_report` have nothing to act on.

- **reason** (`task.py`): the selection must match the reasoning envelope; a commit whose sections are all empty is rejected before anything runs (`empty_reasoning_commit`, no unit) unless it declares `evidence_processing.kind = no_applicable_evidence`. An admitted commit is written to the shared Store (`store.commit_reasoning(payload, scope, key)`, with the account invocation when it carries interpretation accounts).
- **wait** (`waiting.py`): performs the selected wait condition; an invalid wait target becomes a failed outcome with wait-target feedback, not an exception.
- **tool**: see Tools.

The model's response is `{selection, report_update}` as in every episode of this axis: invalid selection makes no unit and gives `action_contract` feedback; an invalid `report_update` gives `report_format` feedback and the selected work still proceeds.

## What it reads from its parent's assignment

`from_parent.py` admits `resource_results_assignment_v1` (`RESULTS_SCHEMA`; per `execution_contracts.py` it "carries handoff and requested_data_selector"). Fields outside the schema are dropped, the rest is validated, and then the assignment is handed to the **one adapter named by the handoff** (`assignment['handoff']['resource_selection']['resource_id']`), whose `prepare_assignment(parent, 'results', assignment, scope, operation_key)` produces the admitted assignment.

- No adapter bound for that resource: `resource_not_bound`.
- A parent of old role `launch` cannot commission this episode: `resource_child_role_not_owned_by_launch`. Result acquisition is commissioned by the scientific parent, not by work submission.
- `initial_references`: references the adapter says arrive with the assignment (none if the adapter has no such callback).

The schema itself (`RESULTS_SCHEMA`, `HANDOFF_SCHEMA`, `CAPABILITY_SCHEMA`) lives outside the folder, in the old `root/a101/resource_records` (the placement table places `resource_records.py` at `episode_support/records/hpc/resource_records.py`).

It also reads from its request: the initial report values and the parent's report contract.

## Children

None (`child_roles` and `allowed_children` return `()`).

## Decision state shown to the model

`decision_state.py` (general state) plus `internal_summary.py` (own part) plus `decision_inputs.py` (extra inputs).

Own part (`internal_summary.py`):

- `role`: `results`;
- `assignment`: the assignment as received;
- `resource_capabilities`: every declared capability (a capability with no bound adapter is shown with an empty tool list: "Include unbound declarations accurately, but never offer their tools");
- `resource_tool_estimates`: prospective duration information from the assigned adapter only.

General state: as for the other A101 episodes (goal, scope, working state, visible record references, current credit and evidence vector, credit binding, time accounting, pending work, last outcome and feedback, visual evidence, report deliveries, controller state and binding, tools, tool knowledge, job episode options, available report facts, requested report purpose and form, current report update and basis) but **without** the annotation context: this episode is operational, not scientific.

Extra inputs: as for the other episodes, plus `waiting_support` (because waiting is permitted).

## Tools

`execution_operations.py: catalog`:

- `resource.capabilities` — "Read actual capability availability and configured resource information; this does not select or submit work." (no arguments; returns all capabilities);
- every tool in the **assigned adapter's** catalogue. The adapter's tool list is authoritative.

`execute` refuses a tool not in that catalogue (`tool_not_owned_by_resource_role`), validates arguments against the tool's schema, answers `resource.capabilities` itself, and passes everything else to the assigned adapter. It also knows how to answer `resource.inspect` and `resource.check_handoff`, but this episode's own catalogue does not add them (the submission episode's does), so they run here only if the adapter lists them.

Outcome shape helpers in `execution_contracts.py`: `_outcome(value, failure, record_refs)` gives `status` `completed` or `failed`; `_failure(code, references)`; unavailable / authentication-required / unknown availability map to `resource_unavailable` / `resource_authentication_required` / `resource_availability_unknown`.

## Credit

`credit.py`: credit kind `operational`; the credit is the bound-role credit for this episode's context (`services.bound_role_credit(context, receiver_selection)`). Adapters must expose a `credit_view` (checked in `configuration.py`), but this file does not call it.

`task.py: execute` measures credit after every observed outcome of a tool or reasoning action. A **wait** takes the last observed credit unchanged and records no received outcome: waiting earns nothing. Nothing bounds, clamps or rescales the credit.

## Continuation

`yield_estimator.py` (`original_continuation_controller`) does not choose an estimator. It asks the caller's controller factory for a controller for this path and initial credit, "caller settings unchanged". Because this role's credit kind is `operational`, no continuation task key and no credit definition are passed. The goal text says the same: "Only the configured local controller governs continuation."

So the old files name no yield estimator and no settings for this episode. Which of the three estimators in `yield_control/` (accumulation, bounded quality, completion with a target) and which settings apply is **not stated in the carried-over files** and has to be decided when it is bound. The new contract supplies settings through the `continuation` collaborator keyed by binding path, which is the same idea as "caller settings".

## What it reports to its parent

`to_parent.py`. The report is the parent's typed form; this episode can fill these fact sources:

| Fact source | Meaning (verbatim) |
|---|---|
| `execution_handoff` (object or null) | "The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure." |
| `execution_handoffs` (array) | "For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it." |
| adapter fact sources | whatever each bound adapter declares for `results`; two adapters declaring the same name differently raises `resource_fact_definition_conflict:<name>` |

- `facts`: taken from the assigned adapter only; handoffs are made distinct by (capability binding, execution handle) and ordered; `execution_handoff` is the single one, or null when there are zero or several.
- `validate_report`: the assigned adapter validates the form, and any form field declared as a handoff fact must equal the recorded facts exactly (`resource_handoff_fact_mismatch`).
- `resolve`: a reference may appear in the report if this episode can see it or the assigned adapter resolves it.
- `report_delivery.py: finish`: the form is filled once from facts plus the last interpretation and reused; with no report contract the result is `{credit, pending_handles}`.

`received_evidence.py`: for a received form, each handoff fact needs proof references from the adapter that owns that handoff; an adapter that cannot give them raises `resource_information_handoff_proof_missing`.

## Configuration

`configuration.py`: constructed with the services object, an explicit list of resource adapters and an optional contract-information profile.

- Each adapter must have a non-empty `resource_id` and the callables `capability`, `as_record`, `prepare_assignment`, `catalog`, `execute`, `fact_sources`, `facts`, `resolve`, `validate_report`, `credit_view` (`explicit_resource_adapter_required`); ids must be unique (`duplicate_resource_id`).
- An adapter that asks for it is given the record-selection service.
- A profile other than the one known contract-information profile raises.

## Differences from its siblings

- **resource_work_submission** (same parent): the files are the same template. This episode differs in: the role sentence of the goal; assignment is the results assignment and is prepared by the one adapter named in the handoff (there: the launch assignment, returned without adapter preparation); tools are `resource.capabilities` plus the assigned adapter's own tools (there: three fixed tools and no adapter tools); it has no children (there: three resource children); summary, facts and report validation use the one assigned adapter (there: all adapters); the contract-information profile never applies (there it can); for an unknown role, `context_hook_applies` is false (there: true).
- **Literature leaves** (`source_coverage_improvement`, `table_evidence_extraction`): this episode permits reasoning commits and waiting, carries its base instruction text in its own folder, has operational credit, calls the provider without a prompt renderer, and shows no annotation context.

## File by file

Exact counts are in `runs/carry_over/calls/a101_04.tsv`. Most hooks begin with `self.credit_kind(role)`, used only as an old role guard.

| Old file | Lines | This episode's own intent in it | Old-runner names it uses |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| `tests/__init__.py` | 0 | none | none |
| `goal.py` | 10 | the results sentence, the common tail, the conditional discovery paragraph | `context.role` (BindingContext); `contract_information_profile`; hook `instructions` |
| `task_instructions.py` | 26 | the base text, the reasoning-commit requirement, the composition order, the wait and native-event paragraphs | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`, `.knowledge.instructions`, `.launch_instructions.instructions`, `.native_event_information`, `.decision_protocol` |
| `configuration.py` | 22 | explicit adapters and what an adapter must provide | `services` object held, `services.record_selection`; import from old `root.a101.composition_information` (`CONTRACT_INFORMATION_PROFILE`) |
| `binding_record.py` | 7 | record: version `resource_episode_binding_v1`, binding id, adapter records, profile | hook `as_record` |
| `episode.py` | 46 | role `results`, may be an entry, no children, the five action kinds, the adapter API description | old binding protocol: `decision_source_type`, `_original_continuation_owner`, `binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `child_roles`, `contract_information_profile`, `permitted_common_actions`, `allowed_children`, `context_hook_applies`; `context.role`, `context.path`, `parent.role` |
| `execution_contracts.py` | 36 | outcome and failure shapes; availability failure codes | imports from old `root.a101.communication` (`ReportBoundaryError`, `plain`), `root.a101.domain` (`obj`), `root.a101.episode_bindings` (`reference_in_context`), `root.a101.resource_records` (19 names; used here: `RESOURCE_ROLES`, `RESULTS_VERSION`, `CAPABILITY_SCHEMA`, `HANDOFF_SCHEMA`, `LAUNCH_SCHEMA`, `RESULTS_SCHEMA`, `_string`, `_array`, `_nullable`, `_validate`, `ROLES`), `root.a101.launch_instructions` (`validate_selection`), `root.a101.local_resources` (`LocalResources`, unused) |
| `execution_operations.py` | 68 | capabilities (unbound shown without tools), the adapter chosen from the handoff, the tool list, how tools run | `self.services.capabilities`; `context.role`, `.assignment`; hooks `capabilities`, `catalog`, `execute` |
| `from_parent.py` | 43 | results assignment, prepared by the handoff's adapter; not commissionable by a launch parent | `parent.role`, `context.role`, `.assignment` (BindingContext); hooks `assignment_schema`, `prepare_assignment`, `initial_references` |
| `internal_summary.py` | 17 | the four summary fields | `context.role`, `.assignment`; hook `decision_context` |
| `decision_state.py` | 55 | which fields the model sees (no annotation context) | 18 `self.workflow.*` members (`store`, `journal`, `working_state`, `local_outcome_preview`, `source_credit_view`, `source_credit_binding`, `receipt_projection`, `pending_work`, `delivery_status`, `controller_binding`, `catalog`, `knowledge`, `job_episode_options`, `extra_report_sources`, `specialist`, `binding_context`, `tools`, `run_id`); SQL on table `runtime_actions`; `journal.elapsed_view`; `view.model_inputs`, `view.child_reports`, `view.controller_state`; imports from old `root.a101.runtime` (`FACT_MEANINGS`, `FACT_SOURCES`, `_plain`, `_references_in`); `bind_functions` rebinding |
| `decision_inputs.py` | 78 | which extra inputs are added, including waiting support | 15 `self.workflow.*` members (as the literature leaves, plus `permits_common_action`, `waiting_support`); `request.message` keys `episode_assignment`, `job_assignment`; imports from old `root.a101.runtime` (`child_option_information`), `root.a101.episode_work_report`, `root.a101.hpc_prompt`; `bind_functions` rebinding |
| `task.py` | 239 | response shape; empty reasoning commit rejected before running; reasoning committed to the Store; wait keeps the last credit; credit measured after each observed outcome | 29 `self.workflow.*` members (the 24 of the literature leaves plus `permits_common_action`, `reasoning_action_schema`, `specialist`, `binding_context`, `last_observed_credit`; `store.reasoning_schema`, `store.commit_reasoning`); tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; `_execution_context._ready_owned_child`; imports from old `root.a101.runtime` (21 names), `root.a101.providers` (`ModelCallError`), `root.a101.episode_source_failure`, `root.a101.library.read_mapping_values`; `bind_functions` rebinding |
| `task_decision.py` | 294 | plain provider call; the exchange protocol | 18 `self.workflow.*` members (`provider`, `journal`, `contract_information_profile`, `validate_contract_information`, `numerical_contracts`, `decision_protocol`, `decision_exchanges`, `freeze_literature_numerical_contracts`, `freeze_contract_information`, `receipts`, `uses_received_record_context`, `history_preview`, `store`, `contract_information_reply`, `controller_binding`, `services`, `execute`, `run_id`); table `runtime_model_calls`; imports from old `root.a101.runtime` (30 names, including `yield_table`, `_category_yield_parameters`); `bind_functions` rebinding. No provider identity checks. |
| `task_state.py` | 115 | starts from the parent's initial report; a failed selected operation is recorded as a failed outcome with credit | `self.workflow.*` (`context`, `grains`, `archive`, `store`, `run_id`, `journal`, `source_credit_view`, `controller_value`, `execution_binding`, `completions`, `inprocess_replay`, `recover_commissions`, `progress_provider`); table `runtime_actions`; `request.message['initial_report']`, `request.report_contract`; imports from old `root.a101.runtime` (`ActionLeaf`, `EFFECT_VERSION`, `Episode`, `Record`, `_json`, `_object`, `_plain`, `interpretation_schema`), `root.a101.episode_source_failure`; `bind_functions` rebinding |
| `to_parent.py` | 62 | the two handoff fact sources and their meanings; facts from the assigned adapter; exact-match check of handoff facts in the report | `context.role`, `.assignment`; `self.services` (through `reference_in_context`, old `episode_bindings`); hooks `fact_sources`, `facts`, `resolve`, `validate_report` |
| `received_evidence.py` | 28 | handoff facts in a received form need adapter proof | hook `received_form_references` |
| `report_delivery.py` | 34 | form filled once and reused; without a contract, credit and pending handles | `self.workflow.*` (`source_credit_view`, `pending_handles`, `episode_bindings.current_report_facts`, `binding_context`, `release`, `journal`, `facts`); table `runtime_forms`; `request.report_contract`; imports from old `root.a101.runtime` (`Record`, `_json`, `form_with_facts`, `json`); `bind_functions` rebinding |
| `credit.py` | 13 | credit kind `operational`; bound-role credit | `self.services.bound_role_credit`; old hooks `credit_kind`, `credit_view`; old role list `self.roles` |
| `yield_estimator.py` | 25 | continuation comes from the caller's settings, unchanged; no task key for an operational role | `BindingContext` (built by hand); `workflow.controller_factory`, `workflow.run_id`, `workflow.receipts.known`, `workflow.scientific_projector_for_context`; `request['message']['scope']`, `['episode_assignment']`; `binding.credit_kind`, `continuation_task`; imports from old `root.a101.runtime` (`BindingContext`, `_plain`); old hook `original_continuation_controller` |
| `waiting.py` | 31 | a selected wait is performed; an invalid target is a failed outcome with feedback | `self.workflow.perform_selected_wait`, `.execution_handle`, `.execution_backend.set_suspension`; imports from old `root.a101.runtime` (`EventTargetError`, `_wait_target_feedback`); `bind_functions` rebinding |

## Carried over

One row per row of `runs/carry_over/functions/a101__sequence_homology_evidence__resource_result_acquisition.tsv`. Machinery is not carried; episode functions are placed in the ten files or marked library candidate. The package of this episode was carried on 19 November 2026 (binding class `ResourceResultAcquisition`).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e): the system journals the declaration, settings and services |
| binding_record.py | OperationalBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3e): the system journals the declaration, settings and services |
| configuration.py | OperationalConfiguration | machinery | configuration.__init__ (services, adapters, contract_information_profile): the adapters are now the declared service `resources`; the profile is never applied to this episode; duplicate/incomplete-adapter checks belong to the service the run supplies |
| configuration.py | OperationalConfiguration.__init__ | machinery | configuration.__init__ (services, adapters, contract_information_profile): the adapters are now the declared service `resources`; the profile is never applied to this episode; duplicate/incomplete-adapter checks belong to the service the run supplies |
| credit.py | ResourceEpisodeCredit | episode function | credit.py: credit (class dissolved) |
| credit.py | ResourceEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d); the role check goes with the old role table: each role is its own episode |
| credit.py | ResourceEpisodeCredit.credit_view | episode function | credit.py: credit, reading the credit_view the resource tools return (task.py: _observed) |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py: decide (class dissolved) |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py: decide (resource_context via service reads, launch_instruction_library, tool_knowledge, own_outcomes, resource_tool_estimates; pieces without a service or library are listed in contract_misfits) |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| decision_state.py | OperationalDecisionState | episode function | messages/internal_summary.py: internal_summary and task.py: decide (class dissolved) |
| decision_state.py | OperationalDecisionState.decision_state | episode function | messages/internal_summary.py: internal_summary (outcomes, feedback, credit, facts, interpretation, controller) and task.py: decide (context) |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| episode.py | ResourceEpisode | episode function | episode.py: ResourceResultAcquisition (the one class) |
| episode.py | ResourceEpisode.child_roles | episode function | task.py: CHILD_SLOTS = {} |
| episode.py | ResourceEpisode.contract_information_profile | machinery | contract-information profile: returned a profile only for role launch, never for this episode; frozen contract information is not carried |
| episode.py | ResourceEpisode.permitted_common_actions | episode function | task.py: _selection_schema (the offered actions: tool, reason, wait, plus report; child and redeliver_report are not offered) |
| episode.py | ResourceEpisode.allowed_children | episode function | task.py: CHILD_SLOTS = {} |
| episode.py | ResourceEpisode.context_hook_applies | machinery | hook-era role dispatch: each role is its own episode |
| execution_contracts.py | _failure | episode function | task.py: _failure (library candidate) |
| execution_contracts.py | _outcome | episode function | task.py: _outcome (library candidate) |
| execution_contracts.py | _availability_failure | episode function | task.py: _availability_failure (library candidate) |
| execution_operations.py | OperationalOperations | episode function | task.py: resource_tool, capabilities, _tools (class dissolved) |
| execution_operations.py | OperationalOperations.capabilities | episode function | task.py: capabilities (library candidate); the tool-bound check ran only for the resource roles, not for results |
| execution_operations.py | OperationalOperations._adapter | machinery | adapter lookup from the handoff: the service `resources` selects its adapter from the assignment handoff (and, for resource.check_handoff, from the handoff given); a missing binding raises in the service (resource_not_bound) |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py: _tools (resource.capabilities entry plus service.catalog) |
| execution_operations.py | OperationalOperations.execute | episode function | task.py: resource_tool (resource.capabilities, resource.inspect, resource.check_handoff, adapter execute) |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM, read_from_parent (class dissolved) |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (version, handoff, requested_data_selector) |
| from_parent.py | OperationalAssignment._permitted | episode function | not carried: the results assignment has no resource_selection of its own and the check compared a capability with constraints the assignment does not hold; reported in unplaced_old_functions |
| from_parent.py | OperationalAssignment._require_launch_child_instruction_pins | episode function | not carried: commission check against the parent assignment (pins the parent held); the child never sees it (rule 1). Reported in unplaced_old_functions |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (field filter and schema validation: the form admits exactly the schema properties). The launch-parent role check (resource_child_role_not_owned_by_launch) and adapter.prepare_assignment are not carried (unplaced_old_functions) |
| from_parent.py | OperationalAssignment.initial_references | machinery | initial_references: nothing is received without being named (README 3b P2) |
| goal.py | OperationalGoal | episode function | goal.py: GOAL (class dissolved) |
| goal.py | OperationalGoal.instructions | episode function | goal.py: GOAL (results sentence and common tail); task.py: instructions (assembly). The `discovery` paragraph was never added for this episode |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py: internal_summary and task.py: decide (class dissolved) |
| internal_summary.py | OperationalSummary.decision_context | episode function | task.py: decide (role, assignment, resource_capabilities, resource_tool_estimates from service reads) and messages/internal_summary.py: internal_summary |
| received_evidence.py | ReceivedOperationalEvidence | machinery | received-form receipt checks (README 3b R3): system custody |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | received_form_references / receipt ledger of received references (README 3b R3): system custody |
| report_delivery.py | OperationalReportDelivery | episode function | messages/final_to_parent.py: final_to_parent (class dissolved) |
| report_delivery.py | OperationalReportDelivery.finish | episode function | messages/final_to_parent.py: final_to_parent (the typed result from the facts and the interpretation; saving the form, Record wrappers, release and pending_handles are machinery) |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| task.py | OperationalTask | episode function | task.py: decide, action, TOOLS (class dissolved) |
| task.py | OperationalTask.instructions | episode function | task.py: instructions |
| task.py | OperationalTask.next | machinery | the decision machine loop (next, restore, replay, source_failed end, delivery refs): the system loop; decide/action produce the unit |
| task.py | OperationalTask.apply_response | episode function | task.py: action (selection validated against the episode schema, empty reasoning commit rejected, rejection feedback). The report_update admission is the report tool; ContractInformation, component-channel and reads.map/bvbrc feedback branches are not this episode's |
| task.py | OperationalTask.execute | episode function | task.py: resource_tool, reason, wait, report (the tool units; credit via credit.py; recording, journal rows, ActionFailure and automatic_score_updates are machinery) |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| task_decision.py | OperationalTaskDecision | machinery | the old decision machine class (README 3a) |
| task_decision.py | OperationalTaskDecision.call | machinery | model call recording (runtime_model_calls, journal.measure): decide returns a ModelRequest |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | decision-exchange interpretation context (README 3a): the interpretation is the report tool |
| task_decision.py | OperationalTaskDecision.exchange_schema | machinery | decision-exchange loop (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | decision-exchange loop (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | saved-request checks (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | saved-request checks (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | the decision-exchange loop (exchange_decision, README 3a) |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| task_instructions.py | instructions | episode function | task.py: instructions (explicit parameters has_knowledge, has_launch; request_context span replaced with replace_span; the pending_child_delivery, pending_child_ wait and decision-protocol paragraphs are not carried) |
| task_state.py | OperationalTaskState | machinery | the state kept between decisions: summary is a pure function of the view (README 3a, 3e F8) |
| task_state.py | OperationalTaskState.__init__ | machinery | state kept between decisions (README 3e F8); the initial report values and feedback are in internal_summary |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | execution binding (old runner) |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | record_execution_failure (README 3c): a tool returns its failed outcome; the unit enters the iterator |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | restore_checkpoint (README 3e) |
| task_state.py | OperationalTaskState.restore | machinery | restore (README 3e) |
| task_state.py | OperationalTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | OperationalTaskState.checkpoint | machinery | checkpoint (README 3e) |
| task_state.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py: RETURN_FORM, facts_from, validate_report, final_to_parent (class dissolved) |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (execution_handoff, execution_handoffs, adapter_facts) |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py: facts_from, final_to_parent |
| to_parent.py | OperationalReport.resolve | machinery | report-reference resolver (reference_in_context, workflow.resolver): the adapter validates the interpretation in the report tool; held-ness is custody |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py: validate_report (called before the result is returned); the adapter's own validate_report is called by task.py: report |
| waiting.py | OperationalTaskWaiting | episode function | task.py: wait (class dissolved) |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | episode function | task.py: wait (calls library jobs/waiting.py selected_wait with the native_events service) |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | wait/suspension machinery (execution_backend.set_suspension): the system has no suspension |
| waiting.py | _bind_original_task_runtime_providers | machinery | provider patching (_bind_original_task_runtime_providers) |
| yield_estimator.py | OriginalContinuation | episode function | yield_estimator.py: yield_controller (class dissolved) |
| yield_estimator.py | OriginalContinuation.original_continuation_controller | episode function | yield_estimator.py: yield_controller (AccumulationYieldController, README 7b); BindingContext, workflow.controller_factory, scientific_child branch and receipts are machinery |
