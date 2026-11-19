# resource_work_submission (A101): intent of the old files

Episode folder: `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/resource_work_submission`

Source read: only this folder's own files at commit `97308b94c` (28 `.py` files directly in the folder, 1,504 lines; no `grading/` or `scoring/` subfolder). The child folders `api_resource_work_execution/`, `hpc_resource_work_execution/` and `local_resource_work_execution/` and `tests/` were not read. Nothing outside the episode tree was read at that commit. Old-runner names per file are counted in `runs/carry_over/calls/a101_04.tsv`.

Old role name in the files: `launch`. Old binding path: `sequence_homology_evidence/resource_work_submission`. Commissioning parent: `sequence_homology_evidence` (the A101 head). It could also be a run entry (`entry_roles = ('launch',)`).

## What this episode is for

Its goal text (`goal.py`), verbatim:

> Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.

When a contract-information profile is configured (`contract_information_profile` returns it for role `launch`, so here it **can** apply), this paragraph is appended, verbatim:

> Within the pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level form field with only $ref set to episode-fact:<source> to have the host expand and fill that type. Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original job_ref and receiving state allows later work to repair that job without submitting a replacement.

So: given the scientific parent's job (inputs, CPU, search, constraints), decide which actual resource (API, local, HPC) to use, inspect capabilities and check returned handoffs, and commission the resource-specific child that does the execution. It returns the execution handoff(s) to the parent in the parent's typed form. It does not fetch result data (that is `resource_result_acquisition`) and does not interpret results.

## Task and instructions

`task_instructions.py` holds the whole base instruction text in this folder (`INSTRUCTIONS`, beginning "You own an iterative scientific annotation improvement, not a tool itinerary.") and `REASONING_COMMIT_REQUIREMENT`. The text is identical to `resource_result_acquisition`'s. It is general annotation-investigation text; the submission-specific part is the goal above. Composition order per decision:

1. `INSTRUCTIONS`;
2. the goal text on a new line (no `replaces_default_instructions`);
3. `REASONING_COMMIT_REQUIREMENT`, because `reason` is permitted;
4. tool-knowledge instructions when `tool_knowledge` is in the context;
5. launch-instruction-library instructions when `launch_instruction_library` is in the context;
6. the pending-child-delivery paragraph ("When pending_child_delivery is supplied, ... this repair does not select new scientific work.");
7. the wait paragraph, because `wait` is permitted ("A pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. ... Waiting only reports readiness and earns no scientific credit. ..."). This is what the episode actually uses: it has children it may wait on;
8. the native-event-targets paragraph when native event information is configured;
9. under `decision_exchange_v1`, the "On a fresh provider conversation," ... passage replaced by the `request_context` / `episode.history` paragraph.

Model call: plain `provider.complete(episode_id, 'REASONING', instructions, context, schema)`, with no prompt renderer and no provider identity checks. That is already the shape of the one model provider's `complete`.

Action kinds (`episode.py: permitted_common_actions`): `tool`, `reason`, `child`, `wait`, `redeliver_report`. All five do something here.

- **reason**: the selection must match the reasoning envelope. A commit whose sections are all empty is rejected before anything runs (`empty_reasoning_commit`, no unit) unless it declares `evidence_processing.kind = no_applicable_evidence` or the binding's `reasoning_has_task_content` accepts it. An admitted commit goes to `store.commit_reasoning` (with the account invocation when it carries interpretation accounts), unless the binding's `execute_reasoning` returns a result.
- **wait**: `waiting.py` performs the selected wait. An invalid wait target becomes a failed outcome with wait-target feedback.
- **child**: one of the three resource children (see Children).
- **redeliver_report**: repair a completed child's delivery with a corrected form using saved facts only.

Response is `{selection, report_update}`. An invalid selection makes no unit (`action_contract` feedback); an invalid `report_update` gives `report_format` feedback and the selected work still proceeds.

## What it reads from its parent's assignment

`from_parent.py` admits `resource_launch_assignment_v1` (`LAUNCH_SCHEMA`). Per `execution_contracts.py`: it "wraps C9 LaunchAssignmentV1 losslessly and adds `adapter_assignment` only after a resource is selected. That field holds the existing immutable job assignment; it is not a selectable replacement for the scientific parent's job, inputs, constraints or allocation." The schema itself lives outside the folder (old `root/a101/resource_records`, now placed at `episode_support/records/hpc/resource_records.py`).

- Fields outside the schema are dropped and the rest is validated. The assignment is **not** passed to an adapter (unlike result acquisition).
- When the commissioning parent is itself `launch`, inheritance is checked: every schema field except `resource_selection` and `launch_instructions` must equal the parent's (`resource_assignment_conflict`). Every launch-instruction section pin (`entry_id`, `section_id`, `sha256`) the parent supplied must be kept, from the same library (`launch_instruction_inheritance_conflict`). A non-null parent `resource_selection` must be kept unchanged (`resource_selection_conflict`).
- `constraints` (`allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`) and `resource_selection` decide which resources are permitted (`_permitted`).
- `initial_references`: none.

It also reads from its request: the initial report values, the parent's report contract, and `episode_assignment.launch_instructions` / `job_assignment` (in `decision_inputs.py`).

## Children

`execution_contracts.RESOURCE_ROLES` (role to resource kind): `launch_api`, `launch_hpc`, `launch_local`. Their bindings are the folders `api_resource_work_execution`, `hpc_resource_work_execution`, `local_resource_work_execution` (`episode.py: child_request_preparer_for_binding`, `child_report_receiver_for_binding`).

A child role is **allowed** only when some declared capability has that role's kind, a bound adapter, a non-empty tool list, availability other than `unavailable`, and is permitted by this assignment's constraints and resource selection.

**What it sends** (`to_child_<kind>_resource_work_execution.py: prepare_commission`; the three files are the same except the role, binding path and one HPC rule):

- the child's scope, which must lie within this episode's scope;
- the child's return form (`expanded_contract_form` from the selection) and its report declaration. Each fact source the child binding declares as required must appear exactly once among the form's top-level `x-source` fields (`child_return_requires_<source>`);
- **HPC only**: when the HPC rule applies (role `launch_hpc` with an `hpc` part in the path), the form must contain an `execution_handoff_refs` fact (`hpc_launch_requires_original_handoff_fact_in_return_form`);
- initial report values, validated against the form's interpretation schema;
- the selected launch instructions, materialized (must exist);
- the child assignment: the selected assignment, optionally transformed by this binding's `prepare_child_request`, then prepared by the child binding's own `prepare_assignment` with operation key `<run>:<episode>:<index>`;
- refuses the role if not allowed (`child_role_not_available_to_parent`) or if the bound child is not the expected binding path (`child_binding_path_conflict`).

**What it takes back** (`from_child_<kind>_resource_work_execution.py: receive_report`; three identical files except role and path):

- checks that the delivery came from that role and binding path (`original_delivery_binding_path_conflict`);
- on a first delivery that is not from a job episode, reuses already recorded admission references when present;
- passes the admitted form to progress (per-role counterpart, binding's own receiver, or the generic progress provider);
- references taken in: every record reference in the form, plus this episode's own `received_form_references`. That means every `execution_handoff` / `execution_handoffs` field must come with proof references from the adapter that owns that handoff (`resource_information_handoff_proof_missing`);
- with native timing and job episodes configured: the native execution references from the recorded report attempt's timing receipts (computed once and saved);
- records the references as received (`child_form`, or `report_redelivery`), plus tool attributions.

## Decision state shown to the model

Own part (`internal_summary.py`):

- `role`: `launch`;
- `assignment`: as received;
- `resource_capabilities`: every declared capability (unbound ones shown with an empty tool list);
- `resource_tool_estimates`: prospective duration estimates from **all** bound adapters.

General state (`decision_state.py`): the same as the other A101 resource episode, with no annotation context: goal, scope, working state, visible record references, visual evidence, current credit and evidence vector, credit binding, time accounting (informational), pending work, last outcome and feedback, report deliveries, controller state and binding, tools, tool knowledge, job episode options, available report facts, requested purpose and form, current report update and basis, and the report-lifecycle sentence.

Extra inputs (`decision_inputs.py`): resource context, shared-information context, launch-instruction library and selected instructions, `child_options` (the child roles above are available), completed action reports, pending work, execution expectations and resource estimates, native expectations and event targets, `waiting_support`, contract-information profile.

## Tools

`execution_operations.py: catalog` offers exactly three fixed tools and **no adapter tools**:

- `resource.capabilities`: "Read actual capability availability and configured resource information; this does not select or submit work."
- `resource.inspect(resource_id)`: "Inspect one declared resource and its actual binding. Unavailable, unknown, unauthenticated and unbound resources return distinct structured failures; this does not submit work." It returns the capability, or a failed outcome `resource_not_bound` / `resource_unavailable` / `resource_authentication_required` / `resource_availability_unknown`.
- `resource.check_handoff(handoff)`: "Exercise the configured receiving interfaces of an explicitly supplied returned handoff. No submission or resource substitution." It goes to the handoff's adapter's `check_handoff`. With no such callback it returns failed `receiving_interface_unavailable`. A bad handoff returns failed `invalid_resource_handoff` (the handle as affected reference). `resource_information_identity_conflict` is raised, not converted.

A tool not in the catalogue is refused (`tool_not_owned_by_resource_role`), and arguments are validated against its schema. Submitting work is not a tool here: it happens only by commissioning a resource child.

## Credit

`credit.py`: kind `operational`; credit is `services.bound_role_credit(context, receiver_selection)`. It is measured after each observed outcome of a tool, reason or child. A wait takes the last observed credit unchanged and earns nothing. Nothing bounds, clamps or rescales it.

## Continuation

`yield_estimator.py: original_continuation_controller` (registered as `_original_continuation_owner = ('launch', ...)`) asks the caller's controller factory for a controller for this path and initial credit, "caller settings unchanged". Because the role is operational, it passes no task key and no credit definition. The goal says "Only the configured local controller governs continuation." The old files name **no yield estimator and no settings**. Which of the three in `yield_control/` applies, and with which settings, is not stated in the carried-over files and must be decided when bound. The new `continuation` collaborator keyed by binding path is the counterpart of "caller settings".

## What it reports to its parent

`to_parent.py`. The parent's typed form, with fact sources:

| Fact source | Meaning (verbatim) |
|---|---|
| `execution_handoff` (object or null) | "The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure." |
| `execution_handoffs` (array) | "For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it." |
| adapter fact sources | each bound adapter's sources for `launch`; a conflicting definition raises `resource_fact_definition_conflict:<name>` |

- `facts`: merged from **all** adapters. Handoffs are deduplicated by (capability binding, execution handle) and sorted; `execution_handoff` is the single one or null.
- `validate_report`: for role `launch`, **every** adapter validates the form. Any handoff field must equal the recorded facts exactly (`resource_handoff_fact_mismatch`).
- `resolve`: visible in context, or resolved by any adapter.
- `report_delivery.py: finish`: the form is filled once from facts plus the last interpretation, saved and reused. With no contract the result is `{credit, pending_handles}`.

## Configuration

`configuration.py`: services, an explicit list of resource adapters, and an optional contract-information profile (only the one known profile is accepted). Each adapter needs a non-empty unique `resource_id` and the callables `capability`, `as_record`, `prepare_assignment`, `catalog`, `execute`, `fact_sources`, `facts`, `resolve`, `validate_report`, `credit_view`. Adapters may take the record-selection service. `binding_record.py` records version `resource_episode_binding_v1`, binding id, adapter records and profile.

## Differences from its sibling and similar episodes

- **resource_result_acquisition** (same parent, same template). Here: the launch role sentence; the contract-information profile and its discovery paragraph can apply; the launch assignment with inheritance checks, not adapter-prepared (there: the results assignment, prepared by the handoff's adapter, and a launch parent may not commission it); the three fixed tools and no adapter tools (there: `resource.capabilities` plus the assigned adapter's catalogue); three resource children with to/from files (there: none); summary, facts and report validation across all adapters (there: the one assigned adapter); `context_hook_applies` is true for roles outside the resource set ("the original Launch parent admits external delivery"), false there.
- **Literature leaves** (`source_coverage_improvement`, `table_evidence_extraction`): those have scientific credit, a prompt renderer, no reasoning or waiting, no children, annotation context in state, and import their base instruction text from outside the folder.

## File by file

Exact counts per name are in `runs/carry_over/calls/a101_04.tsv`. Most hooks begin with `self.credit_kind(role)`, an old role guard.

| Old file | Lines | This episode's own intent in it | Old-runner names it uses |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| `goal.py` | 10 | the launch sentence, common tail, discovery paragraph (applies here) | `context.role` (BindingContext); `contract_information_profile`; hook `instructions` |
| `task_instructions.py` | 26 | base text, reasoning-commit requirement, composition order, wait and native-event paragraphs | `source.workflow.specialist`, `.binding_context`, `.permits_common_action` (3), `.knowledge.instructions`, `.launch_instructions.instructions`, `.native_event_information`, `.decision_protocol` |
| `configuration.py` | 22 | explicit adapters and their required API; one profile | `services`, `services.record_selection`; import from old `root.a101.composition_information` |
| `binding_record.py` | 7 | binding record | hook `as_record` |
| `episode.py` | 59 | role `launch`, entry; three resource child roles; allowed-children rule; five action kinds; child preparer/receiver per (role, binding path); adapter API description | old binding protocol: `decision_source_type`, `_original_continuation_owner`, `binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `child_roles`, `contract_information_profile`, `permitted_common_actions`, `allowed_children`, `context_hook_applies`, `child_request_preparer_for_binding`, `child_report_receiver_for_binding`; `context.role`, `.path`, `parent.assignment` |
| `execution_contracts.py` | 36 | assignment semantics (docstring); outcome/failure shapes; availability failure codes | imports from old `root.a101.communication`, `root.a101.domain`, `root.a101.episode_bindings` (`reference_in_context`), `root.a101.resource_records` (19 names), `root.a101.launch_instructions` (`validate_selection`), `root.a101.local_resources` (unused) |
| `execution_operations.py` | 69 | capabilities (unbound without tools), adapter from handoff, the three tools and their outcomes | `self.services.capabilities`; `context.role`, `.assignment`; hooks `capabilities`, `catalog`, `execute` |
| `from_parent.py` | 53 | launch assignment; inheritance checks for a launch parent; `_permitted` rule | `parent.role`, `parent.assignment` (BindingContext); hooks `assignment_schema`, `prepare_assignment`, `initial_references` |
| `to_child_api_resource_work_execution.py` | 29 | what is sent to the API child | `workflow.store.validate_scope`, `.expanded_contract_form`, `.episode_bindings.for_child` (2) / `.entry_roles`, `.binding_context` (4), `.child_initial_report_input`, `.specialist`, `.available_child_roles`, `.annotation_child_roles`, `.services.capabilities`, `.launch_instructions.materialize`, `.run_id`; imports from old `root.a101.runtime` (`ContractError`, `parse_json_object`, `validate_form`, `interpretation_schema`) |
| `to_child_hpc_resource_work_execution.py` | 32 | as API, plus the HPC handoff-fact rule | same as API |
| `to_child_local_resource_work_execution.py` | 29 | as API for the local child | same as API |
| `from_child_api_resource_work_execution.py` | 47 | what is taken back from the API child | `workflow.episode_bindings.for_child` / `.received_form_references`, `.receipts` (3: test, `receive`), `.is_job_source` (2), `.store` (7, incl. raw SQL), `.run_id` (6), `.binding_context` (4), `.progress_provider` (4), `.specialist`, `.native_timing_information`, `.job_episodes.received_timing_records`, `.receive_tool_attributions`; table `runtime_report_attempts`; imports from old `root.a101.runtime`, `root.a101.delivery_counterpart`, `root.a101.episode_return_records` |
| `from_child_hpc_resource_work_execution.py` | 47 | same, HPC child | same as API |
| `from_child_local_resource_work_execution.py` | 47 | same, local child | same as API |
| `internal_summary.py` | 17 | summary fields; estimates from all adapters | `context.role`, `.assignment`; hook `decision_context` |
| `decision_state.py` | 55 | which fields the model sees (no annotation context) | 18 `self.workflow.*` members (`store`, `journal`, `working_state`, `local_outcome_preview`, `source_credit_view`, `source_credit_binding`, `receipt_projection`, `pending_work`, `delivery_status`, `controller_binding`, `catalog`, `knowledge`, `job_episode_options`, `extra_report_sources`, `specialist`, `binding_context`, `tools`, `run_id`); SQL on `runtime_actions`; `view.model_inputs`; old `root.a101.runtime` imports; `bind_functions` |
| `decision_inputs.py` | 78 | extra inputs incl. waiting support and child options | `self.workflow.*` (`resource_context`, `shared_information_context`, `launch_instructions`, `available_child_roles`, `episode_bindings.initial_decision_context`, `binding_context`, `pending_work`, `execution_expectations`, `job_episodes`, `store`, `resource_estimator`, `native_estimation_context`, `native_event_information`, `permits_common_action`, `waiting_support`); old `root.a101.runtime`, `root.a101.episode_work_report`, `root.a101.hpc_prompt`; `bind_functions` |
| `task.py` | 239 | response shape; empty reasoning rejected before running; reasoning to the Store; wait keeps last credit; credit after each observed outcome | ~29 `self.workflow.*` members (as result acquisition: `journal`, `store` incl. `reasoning_schema`/`commit_reasoning`, `inprocess_replay`, `execution_binding`, `completions`, `completed_unit`, `selected`, `next_return`, `resolve_pending_deliveries`, `action_schema`, `delivery_resolution_inputs`, `decision_exchanges`, `resolver`, `validate_report`, `execute`, `pending_work`, `receive_native_outcome`, `receive_outcome`, `automatic_score_updates`, `source_credit_view`, `retain_shared_grading_results`, `controller_value`, `last_observed_credit`, `permits_common_action`, `reasoning_action_schema`, `specialist`, `binding_context`, `run_id`, `services`); tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; old `root.a101.runtime`, `root.a101.providers` (`ModelCallError`), `root.a101.episode_source_failure`, `root.a101.library.read_mapping_values`; `bind_functions` |
| `task_decision.py` | 294 | plain provider call; exchange protocol | `self.workflow.*` (`provider` (4), `journal`, `contract_information_profile`, `validate_contract_information` (5), `numerical_contracts`, `decision_protocol`, `decision_exchanges`, `freeze_literature_numerical_contracts`, `freeze_contract_information`, `receipts` (4), `uses_received_record_context`, `history_preview`, `store`, `contract_information_reply`, `controller_binding`, `services`, `execute`, `run_id`); table `runtime_model_calls`; old `root.a101.runtime` (incl. `yield_table`, `_category_yield_parameters`); `bind_functions` |
| `task_state.py` | 115 | starts from the parent's initial report; a failed selected operation becomes a failed outcome with credit | `self.workflow.*` (`context`, `grains`, `archive`, `store`, `run_id`, `journal`, `source_credit_view`, `controller_value`, `execution_binding`, `completions`, `inprocess_replay`, `recover_commissions`, `progress_provider`); table `runtime_actions`; old `root.a101.runtime`, `root.a101.episode_source_failure`; `bind_functions` |
| `to_parent.py` | 62 | handoff fact sources and meanings; facts and validation across all adapters; exact handoff match | `reference_in_context(self.services, ...)` (old `episode_bindings`); `context.role`, `.assignment`; hooks `fact_sources`, `facts`, `resolve`, `validate_report` |
| `received_evidence.py` | 28 | handoff facts in a child's form need adapter proof | hook `received_form_references` |
| `report_delivery.py` | 34 | form filled once and reused; else credit and pending handles | `self.workflow.*` (`source_credit_view`, `pending_handles`, `episode_bindings.current_report_facts`, `binding_context`, `release`, `journal`, `facts`); table `runtime_forms`; old `root.a101.runtime`; `bind_functions` |
| `credit.py` | 13 | operational credit; bound-role credit | `self.services.bound_role_credit`; hooks `credit_kind`, `credit_view` |
| `yield_estimator.py` | 25 | continuation from caller's settings, unchanged; no task key for an operational role | `BindingContext` (built by hand); `workflow.controller_factory` (3), `.run_id`, `.receipts.known`, `.scientific_projector_for_context`; `binding.credit_kind`, `continuation_task`; old `root.a101.runtime` (`BindingContext`, `_plain`) |
| `waiting.py` | 31 | a selected wait is performed; an invalid target is a failed outcome | `self.workflow.perform_selected_wait`, `.execution_handle`, `.execution_backend.set_suspension`; old `root.a101.runtime` (`EventTargetError`, `_wait_target_feedback`); `bind_functions` |
