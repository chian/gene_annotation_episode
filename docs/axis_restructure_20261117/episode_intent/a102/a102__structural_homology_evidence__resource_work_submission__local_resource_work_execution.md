# a102 / structural_homology_evidence / resource_work_submission / local_resource_work_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution/*`
(33 files, 1 263 lines; no `grading/` or `scoring/` subfolder). The episode-specific parts are the role name `launch_local`,
the binding path, and the responsibility sentence in `goal.py`. Everything else is a byte-for-byte copy shared
with `hpc_resource_work_execution` and `api_resource_work_execution`. The copies are intended, per the
private-bindings rule.

## Purpose (its own words)

`goal.py`: *"Investigate preparation, execution and receiving interfaces on the selected local resource."* This is the local
resource child of the `launch` (resource_work_submission) parent. It takes a job that the scientific parent has already
defined, with a resource that has already been selected, and carries that job through the selected local resource
adapter's real interfaces: preparation, execution and receiving. It reports the actual execution handoff(s) back
to its parent.

## Task and instructions

`goal.instructions(context)` builds the episode's own instruction text:

> Investigate preparation, execution and receiving interfaces on the selected local resource. Revise later choices from
> actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job,
> input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without
> selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the
> original parent-defined typed form. Only the configured local controller governs continuation.

- `contract_information_profile()` returns `None` here. The parent returns its configured profile instead. As a
  result, the "composition_information / episode.return_contract / `$ref: episode-fact:<source>`" discovery sentence
  never appears in this child's instructions.
- `instructions.py` (the `instruction_composer`) puts together the full model instructions in the original dispatch
  order:
  1. Start from the default `INSTRUCTIONS`, or from job-episode instructions when the source is a job.
  2. Add the specialist's instructions, appended or replacing the default.
  3. Add `REASONING_COMMIT_REQUIREMENT` if `reason` is permitted.
  4. Add tool-knowledge instructions and the launch-instruction-library instructions.
  5. Add the fixed `pending_child_delivery` / `redeliver_report` repair paragraph.
  6. Add the in-process `pending_child_` wait paragraph if `wait` is permitted: "Waiting only reports readiness and
     earns no scientific credit".
  7. Add the native_event_targets paragraph if native event information exists and `wait` is permitted.
  8. Under the decision-exchange protocol, replace the old history guidance with "Use request_context exchanges ...
     read exact previously received outcomes with episode.history".

  The words that belong to this episode are the paragraphs in steps 5–8. The `INSTRUCTIONS` and
  `REASONING_COMMIT_REQUIREMENT` text came from the old shared `runtime_prompt` and is not restored.
- `task_decision.instructions()` delegated to `self.workflow.services.instructions(self, context)`. That old services
  hook is where `instruction_composer` was invoked.

## What it reads from the parent's assignment (`from_parent.py`)

- `assignment_schema(role)` is a deep copy of `LAUNCH_SCHEMA` (`resource_launch_assignment_v1`, which wraps C9
  LaunchAssignmentV1). Per the docstring in `resource_contracts.py`, it carries:
  - the parent's job, input versions, constraints and allocation;
  - `launch_instructions`, the pinned instruction sections;
  - `resource_selection`;
  - `adapter_assignment`, the immutable job assignment, added only after a resource is selected.
- `prepare_assignment(parent, role, selection, scope, operation_key)` filters the selection to the schema's
  properties and validates it. When the parent role is `launch`:
  - Every inherited field except `resource_selection` must equal the parent's, or it raises
    `resource_assignment_conflict`.
  - `launch_instructions` must keep every pinned `(entry_id, section_id, sha256)` of the parent with the same
    `library_id`, or it raises `launch_instruction_inheritance_conflict`.
  - A parent `resource_selection` that is set may not change (`resource_selection_conflict`).

  It also requires an explicit `resource_selection` (`explicit_resource_selection_required`). The selected
  capability must exist, have kind `RESOURCE_ROLES[role]` and pass `_permitted`, which checks the constraints
  `allowed_resource_ids`, `allowed_kinds`, `resource_id` and `kind`. The adapter's own `prepare_assignment` then
  produces the final assignment.
- `decision_inputs.py` also reads `episode_assignment.launch_instructions` from the request message and
  materialises the selected launch instructions for the model.
- `task.py` reads `job_assignment` from the request message when it validates the report.

## Children

None. `child_commissioning.child_roles()` returns `()` and `allowed_children()` returns `()`. There is no
`child_request_assembler`, no `to_child_*` and no `from_child_*` file. The parent `resource_work_submission` is the
episode that commissions `launch_api` / `launch_local` / `launch_local` through its `to_child_*` files.
`permitted_common_actions` still lists `child` and `wait`. Those cover the job-child / in-process pending-child
handles that the old runner offered, and the `pending_child_delivery` redelivery path.

## Decision state shown to the model

`decision_context.decision_state(view)` builds the model context from the following:

- `goal`, `scope`, `working_state`.
- `visible_record_refs`, resolved from working state, the last outcome, visual evidence and report forms (its own
  form plus child report forms).
- `current_credit`, and `current_evidence_vector`, which is the axis components.
- `investigation_progress` (`retained_finding_count`, `inactive_dependencies`, `detail_pages`), shown when a receipt
  projection exists.
- `credit_binding`.
- `time_accounting`, which is `journal.elapsed_view`. This is an elapsed-time display; see the note below.
- `pending_work`, `last_local_outcome`, `feedback`.
- `visual_evidence`, the latest completed `image.view` result.
- `report_deliveries`.
- `controller` and `controller_binding`.
- `tools`, `tool_knowledge`, `job_episode_options`.
- `available_report_facts`, built from FACT_SOURCES/FACT_MEANINGS plus extra sources, or replaced by the tool
  registry's `model_contract_catalog`.
- `requested_report_purpose`, `requested_form`, `current_report_update`, `current_report_basis_refs`.
- `report_lifecycle`: "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new
  judgment."
- An annotation-axis-credit mode, which reduces the state to arms/annotation_credits/root_score/decision and
  compresses child outcomes to counts.
- `monitoring_information_*`.
- The specialist's `decision_context`. For this binding, that is `internal_summary.decision_context`: `role:
  'launch_local'`, the assignment, `resource_capabilities`, and `resource_tool_estimates` from the selected adapter's
  `decision_context`.
- `_completed_work_axis_results`: `a102_sheet`, `target_sheets`, `tool_attachments`, `source_contributions`.

`decision_inputs.decision_inputs()` adds the following to each fresh decision:

- `resource_context`, `shared_information_context`, `launch_instruction_library`, `selected_launch_instructions`.
- `child_options`, if any child roles are available.
- The binding's `initial_decision_context`. A conflict raises `initial_binding_context_field_conflict`.
- `completed_action_reports`.
- `requested_action_history`, when `is_hpc_context` (the same HPC-context check is copied here unchanged).
- `pending_work`.
- `execution_expectations` for role `launch_local`.
- `resource_tool_estimates`: the job-source estimate (job_ref plus the latest sample) or the context estimate, plus
  the native estimates.
- `native_execution_expectations`, `waiting_support`, `contract_information_profile`.

The decision exchange (`decision_exchange.py`, `decision_contracts.py`, `saved_decision_exchange.py`) works like this:

- The model answers either `request_context` with a lookup or `select_action` with a `selection` and a
  `report_update`.
- A lookup can request `child_options`, `composition_information` (which executes a composition operation), or its
  own attempt lookups. Each lookup is recorded and none counts as an action.
- The snapshot includes an action-yield table: either the old `yield_table` with `_category_yield_parameters`, or the
  root controller arms under annotation-axis credit.
- Saved exchanges are authenticated on resume. Any mismatch raises `original_contract_*`.

## Tools offered

From `operation_catalog.py` and `operations.py`:

- `resource.capabilities` reads the actual capability availability and the configured resource information. It does
  not select or submit work.
- The selected adapter's `catalog(context)`, which is authoritative.
- `resource.inspect`, `resource.check_handoff`. These are dispatched in `execute` when the adapter catalogue lists
  them. `inspect_resource` reports `resource_not_bound` or an availability failure: unavailable,
  authentication_required, or unknown. `check_selected_handoff` calls the adapter's `check_handoff` (if missing:
  `receiving_interface_unavailable`; on a read error: `invalid_resource_handoff`).
- A tool name outside the catalogue raises `tool_not_owned_by_resource_role`.

Capabilities declared by services but not bound to an adapter are listed with `tool_names: []`. They are never
offered.

Common actions: `tool`, `reason`, `child`, `wait`, `redeliver_report`.

## Credit

`credit.py`:

- `credit_kind(role)` is `'operational'` for any role in `ROLES`; any other role raises `unknown_resource_episode_role`.
- `credit_view` delegates to `services.bound_role_credit(context, receiver_selection)`.

In `task.execute`, credit per action is the `source_credit_view` credit after the outcome. For a `wait` action it is
instead `last_observed_credit`, so waiting earns nothing new. That value goes to the controller through
`controller_value`. Malformed actions are recorded as `rejected` effects before any unit is acquired. A returned
invalid or failed outcome still enters the iterator with its credit, and `ActionFailure` is raised only when no
outcome was observed. No bounding or rescaling appears.

## Continuation

There is no yield-estimator selection in this folder. The old runner's `controller_binding`, together with
`_category_yield_parameters` and `yield_table`, governed continuation: "Only the configured local controller governs
continuation." The credit is operational and gained per action. It has no target and no quality ceiling, so the
nearest of the three `yield_control/` estimators is **accumulation**. That is an inference: no setting is named in
these files.

## Report to the parent

`to_parent.py`, `report_fields.py`, `report_delivery.py`, `received_messages.py`:

- **Fact sources:**
  - `execution_handoff` is the latest original usable received check or the episode's own selected check when
    exactly one physical execution is known. It is `null` when there are zero or several, and no new check happens
    at closure.
  - `execution_handoffs` gives one check per distinct (registry, execution_handle), the one with the latest
    `checked_at`, in identity order.
  - The adapter's own fact sources are merged in; a conflict raises `resource_fact_definition_conflict:<name>`.
- `facts()` gathers the selected adapter's facts. It dedupes handoffs by
  `(resource_selection.capability_binding_ref, execution_handle)` and sets `execution_handoff` only when exactly one
  identity exists. The parent version iterates over all adapters; this child uses only the selected adapter.
- `validate_report()` runs the adapter's `validate_report`. It then requires every `x-source` handoff field in the
  form to equal the recorded facts, or it raises `resource_handoff_fact_mismatch`.
- `received_form_references()` collects the adapter's proof references for the handoff fields; if missing, it raises
  `resource_information_handoff_proof_missing`.
- `resolve()` uses the shared `reference_in_context` and then the adapter's `resolve`.
- `initial_references()` returns the adapter's initial references only for role `results`, which is never this role.
- `finish()`:
  - With no report contract, it returns credit, the pending handles and the binding's current report facts.
  - Otherwise it builds the form from the interpretations plus the assembled facts (`form_with_facts`) once, saves it
    in `runtime_forms`, and returns `{'form': form}`.
- `binding_record.as_record()` gives version `resource_episode_binding_v1`, the binding_id, the adapter records and
  the profile.
- `configuration.py`:
  - It requires each adapter to provide `capability`, `as_record`, `prepare_assignment`, `catalog`, `execute`,
    `fact_sources`, `facts`, `resolve`, `validate_report` and `credit_view`; otherwise it raises
    `explicit_resource_adapter_required`. A repeated id raises `duplicate_resource_id`.
  - It binds the adapter's record selection.
  - It accepts only `CONTRACT_INFORMATION_PROFILE` or `None`.

## Note on time

`decision_context` shows `time_accounting: journal.elapsed_view(...)`, and the resource estimator supplies duration
estimates. Both are informational displays: "inform your decisions, without selecting an approach or imposing an
order". Neither is a stopping gate, and neither may become one.

## Files

| file | lines | own intent | old-runner names |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `action_contract_feedback.py` | 40 | Repairs malformed actions. It adds typed `contract_error` details, the explicit repair text for `closed_top_level_form_required`, required fact sources for `component_native_return_channels_required`, and reads.map parameter feedback. It records a `rejected` effect, with no unit acquired. | import `runtime` (ContractError, ContractInformationError, ReportBoundaryError, ValidationError, schema_failure_diagnostic, Mapping); import `read_mapping.parameter_schema_failure`; `self.record_effect` |
| `binding_record.py` | 7 | Binding record `resource_episode_binding_v1`, with binding_id `.../local_resource_work_execution`, the adapter records and the profile. | — |
| `child_commissioning.py` | 12 | No children (`()`). | — |
| `configuration.py` | 22 | Adapter API requirement, unique resource ids, profile check, record-selection binding. | import `composition_information.CONTRACT_INFORMATION_PROFILE`; `services.record_selection` |
| `credit.py` | 13 | Credit is `operational` for known roles. | `self.services.bound_role_credit`; `resource_records.ROLES` (via resource_contracts) |
| `decision_context.py` | 45 | Model decision state: the fields listed above, the annotation-axis reduction, visual evidence, report lifecycle sentence. | `self.workflow.store` ×3, `.journal` ×3 (`db`, `row`, `elapsed_view`), `.working_state`, `.run_id`, `.local_outcome_preview`, `.source_credit_view`, `.receipt_projection`, `.source_credit_binding`, `.pending_work`, `.delivery_status`, `.controller_binding`, `.catalog`, `.knowledge`, `.job_episode_options`, `.extra_report_sources`, `.is_scientific_source`, `.specialist`, `.binding_context` (BindingContext), `.tools`; raw SQL on table `runtime_actions`; runtime `FACT_MEANINGS`, `FACT_SOURCES`, `_references_in`, `_plain` |
| `decision_contracts.py` | 35 | Exchange envelope: `request_context` lookup or `select_action` (selection, report_update), keeping ordinary action admission. | runtime `_object`, `composition_lookup_schema(self.workflow, self)`, `Draft202012Validator` |
| `decision_exchange.py` | 119 | Pending-decision exchange loop: lookup kinds `child_options`, `composition_information` and own attempts; retry handling; conversation continuation frames. | `self.workflow.provider` ×2 (complete, conversation_key), `.decision_exchanges`, `.journal` (`measure`, `save`), `.validate_contract_information`, `.controller_binding`, `.services.decision_exchange_instructions`, `.execute`, `.run_id`, `.store`; tables `runtime_model_calls`; old yield `yield_table`, `_category_yield_parameters`; runtime `model_snapshot`, `state_frame`, `instructional_model_context`, `child_option_information`, `lookup_attempts`, `requested_contract_information`, `DECISION_CONTEXT_VERSION`, `_action_generation_schema` |
| `decision_inputs.py` | 58 | Fresh decision inputs. `launch_local` is the execution_expectations role. requested_action_history when is_hpc_context (same check as the HPC sibling). | `self.workflow.resource_context`, `.shared_information_context`, `.launch_instructions` ×2, `.available_child_roles`, `.episode_bindings.initial_decision_context`, `.binding_context`, `.pending_work`, `.execution_expectations`, `.resource_estimator` ×5, `.is_job_source`, `.job_episodes` ×2, `.native_estimation_context`, `.permits_common_action`, `.waiting_support`; imports `episode_work_report`, `library.hpc_prompt`; runtime `child_option_information` |
| `episode.py` | 25 | `binding_path`, `commissioning_parent = .../resource_work_submission`, `roles = ('launch_local',)`, `entry_roles = ()`, common actions (tool, reason, child, wait, redeliver_report), adapter API docstring. | Mixin composition, `decision_source_type`. The docstring says "all iteration/commissioning remains in shared method_loop" |
| `from_parent.py` | 47 | Assignment schema and inheritance checks (job, inputs, constraints unchanged; instruction pins retained; resource selection fixed and permitted). | `resource_records` LAUNCH_SCHEMA/RESOURCE_ROLES/_validate, `launch_instructions.validate_selection` (via resource_contracts) |
| `goal.py` | 12 | Responsibility sentence and instruction text. No contract-information profile. | — |
| `handoff_check.py` | 19 | `resource.check_handoff` through the adapter's `check_handoff`, with explicit failures. | `RESULTS_VERSION` (resource_records) |
| `initial_references.py` | 11 | Adapter initial references only for role `results`. | — |
| `instructions.py` | 26 | Instruction composition order and the redelivery, wait, native event and exchange-history paragraphs. | `source.workflow.job_episodes`, `.is_job_source`, `.specialist`, `.binding_context`, `.permits_common_action` ×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`; import `runtime_prompt` (INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, DECISION_EXCHANGE_PROTOCOL) |
| `internal_summary.py` | 16 | Specialist decision context: role `launch_local`, assignment, capabilities, the selected adapter's tool estimates. | — |
| `operation_catalog.py` | 11 | `resource.capabilities` plus the adapter catalogue. | `domain.obj` |
| `operations.py` | 25 | Tool dispatch (capabilities, inspect, check_handoff, adapter execute). | — |
| `received_messages.py` | 31 | Proof references for received handoff fields. | — |
| `report_delivery.py` | 25 | Finish: the no-contract record or the form saved once. | `self.workflow.source_credit_view`, `.pending_handles`, `.episode_bindings.current_report_facts`, `.binding_context`, `.release` ×2, `.journal` ×2, `.facts`; table `runtime_forms`; imports `library.report_fact_assembly`, `library.private_policy_call`; runtime `Record`, `form_with_facts` |
| `report_fields.py` | 15 | `execution_handoff`/`execution_handoffs` fact definitions plus the adapter's fact sources. | — |
| `report_reference_access.py` | 11 | Resolve through shared receiving, then the adapter. | `episode_bindings.reference_in_context` |
| `resource_contracts.py` | 36 | Docstring on the assignment versions. `_failure`, `_outcome`, `_availability_failure`. | imports `communication` (ReportBoundaryError, plain), `domain.obj`, `episode_bindings.reference_in_context`, `resource_records` (roles, schemas, `_validate`), `launch_instructions.validate_selection`, `local_resources.LocalResources` (unused) |
| `resource_inspection.py` | 15 | `resource.inspect` with bound/availability failures. | — |
| `resource_selection.py` | 36 | Capability listing (unbound entries have no tools), tool-binding check, adapter lookup, `_permitted` constraints. | `self.services.capabilities` |
| `saved_decision_exchange.py` | 81 | Authentication of saved exchange history on resume. | `self.workflow.validate_contract_information` ×2, `.decision_exchanges` ×2, `.journal`, `.contract_information_reply`; table `runtime_model_calls`; runtime `WorkflowError` ×9, `apply_state_frame`, `model_snapshot`, `CONTRACT_INFORMATION_OPERATIONS`, `is_contract_information` |
| `task.py` | 209 | Iteration unit. Admits reason vs. other selections (empty reasoning commit rejected), keeps report updates separate from work, gives job_child failure feedback, executes reason/wait/tool, credits after observed outcome, raises `ActionFailure` only when nothing was observed. Grain `launch_local` in validate_report. | `self.workflow.journal` ×7, `.store` ×9, `.execution_binding` ×7, `.inprocess_replay` ×4, `.completions` ×3, `.completed_unit` ×3, `.selected` ×3, `.decision_exchanges` ×3, `.run_id` ×3, `.next_return`, `.resolve_pending_deliveries`, `.action_schema`, `.delivery_resolution_inputs`, `.permits_common_action`, `.reasoning_action_schema`, `.specialist` ×2, `.binding_context` ×2, `.resolver`, `.validate_report`, `.execute`, `.perform_selected_wait`, `.pending_work`, `.receive_native_outcome`, `.receive_outcome`, `.automatic_score_updates`, `.last_observed_credit`, `.source_credit_view`, `.retain_shared_grading_results`, `.controller_value` ×2; tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; imports `providers.ModelCallError`, `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`; runtime `SourceEnd`, `ReportRedelivery`, `EventTargetError`, `AcquisitionError`, `ActionFailure`, `observes_action_outcome`, `validate_form`, `_decode_recorded_action_response`, `_wait_target_feedback` |
| `task_decision.py` | 82 | Per-decision call: saved-call reuse and validation, protocol choice, history preview for a fresh session. | `self.workflow.journal`, `.contract_information_profile`, `.validate_contract_information` ×2, `.numerical_contracts`, `.decision_protocol` ×3, `.freeze_literature_numerical_contracts`, `.freeze_contract_information`, `.receipts` ×4 (receipts.receive decision_input), `.is_job_source` ×2, `.uses_received_record_context` ×2, `.decision_exchanges`, `.provider` ×2 (has_session, complete), `.history_preview`, `.services.instructions`; table `runtime_model_calls` ×5; runtime `_ASSIGNMENT_TRANSPORT`, `_recorded_assignment_transport`, `_digest`, `DECISION_EXCHANGE_PROTOCOL`, `instructional_model_context` |
| `task_state.py` | 108 | Source state fields, execution-failure recording as a failed outcome that still enters the iterator with credit, restore/checkpoint/record_effect. | `self.workflow.context`, `.grains` (Episode.identity), `.archive`, `.journal` ×5, `.store` ×2, `.source_credit_view`, `.controller_value`, `.execution_binding` ×4, `.completions` ×4, `.inprocess_replay` ×7, `.recover_commissions`, `.progress_provider` ×2, `.run_id`; table `runtime_actions` ×5; import `episode_source_failure`; runtime `Episode`, `ActionLeaf`, `EFFECT_VERSION`, `interpretation_schema`, `Record` |
| `waiting.py` | 9 | Suspension condition sent to the execution backend. | `self.workflow.execution_handle` ×2, `.execution_backend` |

## Differences from siblings and parent

- **vs `hpc_resource_work_execution`**: identical apart from the role (`launch_hpc`), the binding path, and the
  goal sentence: "Investigate the selected actual environment, queue, staging and execution interfaces." The HPC-context `requested_action_history` gate (`is_hpc_context`) is copied into this local episode unchanged; whether it ever fires for a local context depends on the old shared `library.hpc_prompt`, which was not read.
- **vs `api_resource_work_execution`**: identical apart from the role (`launch_api`), the binding path, and the goal
  sentence: "Investigate execution through the selected actual API or service, including real availability and
  authentication."
- **vs parent `resource_work_submission`** (role `launch`):
  - The parent commissions the three children. It allows a role only when a bound, available, permitted adapter with
    tools of that kind exists.
  - The parent's goal is "Choose which actual execution approach is productive ... commission a resource child when
    useful".
  - The parent returns its configured contract-information profile.
  - The parent's summary, facts and report validation iterate over all adapters, where this child uses only the
    selected adapter.
