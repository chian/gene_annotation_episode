# Episode intent: `a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution`

Source: the episode's own files at commit `97308b94c`
(`gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution/`,
21 Python files (one an empty `__init__.py`), 1264 lines, plus an empty `tests/__init__.py`; no `grading/` or `scoring/` subfolder).
Only those files were read. Anything the files delegate to the deleted runner or to the old axis-level modules
is named below as a delegation and was not looked up.

Old role name: `launch_api`. Resource kind: `api`. Parent: `sequence_homology_evidence/resource_work_submission`
(old role `launch`). Children: none.

## What this episode is for

Its goal, in its own words (`goal.py`, the `launch_api` entry of its responsibility table followed by the common tail):

> Investigate execution through the selected actual API or service, including real availability and authentication. Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this
> shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration
> estimates inform your decisions, without selecting an approach or imposing an order.
> Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only
> the configured local controller governs continuation.

Read together with its assignment and report facts (my reading, not the files' words): the launch parent has already chosen one actual `api` resource for the scientific parent's job. This
episode works on that one resource, through that resource's own tools, until the job has a usable execution
handoff (a handle whose monitoring and results interfaces were actually checked) or the resource is shown to be
unavailable, unauthenticated or unknown. It never changes the job, the inputs, the constraints or the allocation,
and it never substitutes another resource.

The `discovery` paragraph in `goal.py` (about `request_context` with `view=composition_information` and
`episode-fact:<source>` references) is never added for this episode: `episode.py`
`contract_information_profile` returns a profile only for role `launch`.

## Task and instructions

The task class is `OperationalTask` (`task.py`), an ordinary model-decided loop: each turn the model sees the
decision state, selects exactly one action, and returns a `report_update` for the parent's typed form in the same
response.

The instruction text the model received was composed by `task_instructions.py` `instructions(source, context)`:

1. The general A101 text `INSTRUCTIONS` (line 4; a long scientific-investigation text beginning "You own an
   iterative scientific annotation improvement, not a tool itinerary."). It is the same text in every A101
   folder compared here (the three siblings, the launch parent, `execution_job_submission/api_job_execution`) and
   is mostly about scientific reasoning rather than resource work.
2. This episode's own goal text (above), appended. It would replace the general text only if the binding set
   `replaces_default_instructions`; this episode's files do not set it.
3. `REASONING_COMMIT_REQUIREMENT` (line 3), because `reason` is a permitted action here.
4. The tool-knowledge text and the launch-instruction-library text, because the decision context always carries
   `tool_knowledge` and `launch_instruction_library`.
5. The `pending_child_delivery` paragraph (always appended; this episode has no children, so it never applies).
6. The waiting paragraph, because `wait` is a permitted action; and the `native_event_targets` paragraph when
   native event information is configured.
7. Under the decision-exchange protocol (`decision_exchange_v1`) the "On a fresh provider conversation" history
   paragraph is replaced by the `request_context` wording, and the exchange-protocol text is appended.

Permitted action kinds (`episode.py` `permitted_common_actions`): `tool`, `reason`, `child`, `wait`,
`redeliver_report`. `child_roles` and `allowed_children` both return `()`, so `child` and `redeliver_report` can
never be carried out here; the list is the same tuple as the parent's. That is a carried-over inconsistency to
settle in the port (offer only `tool`, `reason`, `wait`), not an intent to commission children.

## What it reads from its parent's assignment

The assignment is the persisted `resource_launch_assignment_v1` (`from_parent.py` `assignment_schema` returns a
copy of `LAUNCH_SCHEMA`; the schema itself lived in the old axis-level `resource_records` module, whose current
copy is `episode_support/records/hpc/resource_records.py`):

| Field | Meaning | How this episode uses it |
|---|---|---|
| `version` | `resource_launch_assignment_v1` | admitted |
| `job_request` | the scientific parent's job | fixed; must equal the launch parent's |
| `immutable_input_versions` | `reference`, `version`, `content_sha256` per input | fixed; must equal the launch parent's |
| `constraints` | may hold `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind` | fixed; the chosen resource must satisfy them |
| `resource_selection` | `resource_id`, `kind`, `allocation` (`cpu`, `memory_bytes`, `scratch_bytes`), `capability_binding_ref` | required non-null; names the one adapter this episode uses |
| `software_knowledge_refs`, `resource_knowledge_refs` | knowledge entries | fixed; must equal the launch parent's |
| `launch_instructions` | pinned launch-instruction selection (`library_id`, `sections` with `entry_id`, `section_id`, `sha256`) | must keep every section the parent pinned, from the same library; expanded for the model as `selected_launch_instructions` |

Admission rules (`from_parent.py` `prepare_assignment`), each failing with its own error:

- Fields outside the schema are dropped, then the record is validated.
- When the commissioner is the launch parent, every field except `resource_selection` and `launch_instructions`
  must equal the parent's own assignment (`resource_assignment_conflict`); the parent's `adapter_assignment` is
  ignored for this comparison.
- The child's `launch_instructions` must retain the parent's pinned sections
  (`launch_instruction_inheritance_conflict`).
- If the parent already holds a `resource_selection`, the child's must equal it (`resource_selection_conflict`).
- `resource_selection` must be present (`explicit_resource_selection_required`).
- The selected resource must have a declared capability of kind `api` that the constraints permit
  (`resource_selection_conflict`).
- The selected adapter then prepares the final assignment
  (`adapter.prepare_assignment(parent, 'launch_api', selected, scope, operation_key)`). Per `execution_contracts.py`
  it "adds `adapter_assignment` only after a resource is selected. That field holds the existing immutable job
  assignment; it is not a selectable replacement for the scientific parent's job, inputs, constraints or
  allocation."

Besides the assignment, the old request message also carried `scope` (the subject scope), `initial_report` (the
parent's initial values for the report form), an optional `job_assignment`, and the parent's `report_contract`
(its `schema` and its `decision`, shown to the model as `requested_form` and `requested_report_purpose`).

`initial_references` returns `[]`: the episode starts with no extra references.

## Children

None. `child_roles(role)` and `allowed_children(parent, caller_capabilities)` return `()`. There are no
`to_child_*` or `from_child_*` files.

## Decision state: what it shows the model

Built by `decision_state.py`, extended by `decision_inputs.py`, with this episode's own fields from
`internal_summary.py`.

This episode's own fields (`internal_summary.py` `decision_context`):

| Key | Content |
|---|---|
| `role` | `launch_api` |
| `assignment` | the admitted launch assignment, in full |
| `resource_capabilities` | every declared capability (bound and unbound; an unbound one is shown with an empty `tool_names`) |
| `resource_tool_estimates` | prospective duration information from the selected adapter's optional `decision_context(context)`; only the selected adapter is asked |

General fields (`decision_state.py`): `goal`, `scope`, `working_state`, `visible_record_refs`, `current_credit`,
`current_evidence_vector`, `credit_binding`, `time_accounting` (elapsed view, information only),
`pending_work`, `last_local_outcome`, `feedback`, `visual_evidence` (pixels of the last completed `image.view`),
`report_deliveries`, `controller` (controller state), `controller_binding`, `tools`, `tool_knowledge`,
`job_episode_options`, `available_report_facts`, `requested_report_purpose`, `requested_form`,
`current_report_update`, `current_report_basis_refs`, `report_lifecycle`; `investigation_progress` only when the
episode projects receipts; `monitoring_information_credit` and `monitoring_information_binding` when the credit
view carries them. The `annotation_axis_credit` branches in this file belong to the root annotation episode and
are never taken here.

Added per call (`decision_inputs.py`): `resource_context`, `shared_information_context`,
`launch_instruction_library`, `selected_launch_instructions`, the binding's initial decision fields,
`completed_action_reports`, `requested_action_history` (HPC contexts only), `pending_work`,
`execution_expectations` and `job_execution_options` (when execution expectations apply to the role),
`resource_tool_estimates`, `native_execution_expectations`, `native_event_targets`, `waiting_support`.
`child_options` and `contract_information_profile` are never added for this episode.

The model's response is `{selection, report_update}`. A selection that fails admission creates no unit and no
observation; the feedback (`action_contract`, with schema diagnostics) is shown at the next decision. A
`report_update` that fails admission does not discard the selected work; it leaves `report_format` feedback.
A reason action whose commit sections are all empty is rejected (`empty_reasoning_commit`) unless it declares
`evidence_processing.kind=no_applicable_evidence`.

## Tools it offers

`execution_operations.py` `catalog(context)`:

1. `resource.capabilities` (its own; no arguments): "Read actual capability availability and configured resource
   information; this does not select or submit work."
2. Every tool in the selected adapter's `catalog(context)`. The adapter's tool list is authoritative; the adapter
   is the one named by `assignment.resource_selection.resource_id`, and a missing binding raises
   `resource_not_bound`.

`execute` validates the arguments against the catalog entry, answers `resource.capabilities` itself, and sends
everything else to `adapter.execute(context, tool_name, arguments, operation_key)`. A tool outside the catalog
raises `tool_not_owned_by_resource_role`. `execute` also contains the handlers for `resource.inspect` and
`resource.check_handoff`, but this episode's catalog does not list them (the launch parent's does), so here they
are reachable only if the adapter's own catalog names them.

Capabilities (`capabilities`): declared capabilities come from the services object; one whose resource has no
bound adapter is reported accurately but with no tools. For the selected adapter, every tool name its capability
declares must be in its catalog (`resource_capability_tool_not_bound`).

Besides tools: `reason` commits rows to the shared Store's reasoning schema, and `wait` performs a selected wait
condition and reports suspension. Under the decision-exchange protocol the model may also ask `request_context`
lookups (own earlier attempts, composition information) before selecting; a lookup is not a unit.

## How its credit is counted

- `credit.py` `credit_kind(role)`: `operational` (an unknown role raises `unknown_resource_episode_role`).
- `credit.py` `credit_view(context, receiver_selection)`: `self.services.bound_role_credit(context,
  receiver_selection)`. The number's definition is therefore not in this folder; it lived in the old services
  object, and each resource adapter also exposes `credit_view(context, receiver_selection)`. The port has to
  state this episode's credit in its own `credit.py` from explicit library functions.
- When it is measured (`task.py` `execute`): after each tool or reason action whose outcome is observed, the
  episode's current credit is read and saved with the action; that credit is the controller input for the unit.
  A `wait` action carries the last observed credit unchanged (waiting earns nothing). An own action that raises
  is recorded as a failed outcome with the credit measured after it (`task_state.py`
  `record_execution_failure`), so a returned failed action still enters the iterator. An action whose outcome is
  not observed raises `ActionFailure` instead of returning a controller input.
- Nothing in these files bounds, clamps or rescales the credit.

## Continuation

`yield_estimator.py` is titled "original continuation factory selection; caller settings unchanged". It selects
nothing itself: `original_continuation_controller` hands the episode path and the commission's `initial_credit`
to the old runner's `controller_factory`, and (when the factory asks for the original task) the episode's
`BindingContext` with `task_key=None` and `credit_definition=None`, because the credit kind is `operational`.
The `scientific_child` branch (task key, scientific projector) is never taken here.

So the old files name neither a yield estimator nor its settings for this episode; the goal text only says
"Only the configured local controller governs continuation." Which of the three estimators in `yield_control/`
this episode uses, and with which settings, is a decision the port must record in this episode's own
`yield_estimator.py`. Observation, not a decision: the episode's work has a definite end (one usable handoff for
the assigned job), which is the shape of the completion-with-a-target estimator.

## What it reports to its parent

"Return the original parent-defined typed form." (`goal.py`). `report_delivery.py` `finish`:

- With a report contract: the form is the parent's schema filled from the model's latest admitted
  `report_update` (interpretive fields) and the recorded facts (fact fields); it is saved once and returned as
  `{'form': form}`.
- Without a report contract: `{'credit': current credit, 'pending_handles': ...}` plus the current report facts.

Facts this episode can supply (`to_parent.py` `fact_sources`, `facts`):

| Fact | Meaning (its own words) |
|---|---|
| `execution_handoff` | "The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure." |
| `execution_handoffs` | "For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it." |
| adapter facts | whatever `adapter.fact_sources('launch_api')` declares; a definition that conflicts with one already declared raises `resource_fact_definition_conflict` |

A handoff is an `execution_handoff_v1` record: `execution_handle`, `resource_selection`,
`submitted_input_versions`, `monitoring` and `results` receivers (`provider_id`, `target_handle`,
`contract_ref`), `checked_at`, `check_record_refs`, `state` (`usable` or `unavailable`), `failure`.

Rules: facts come only from the selected adapter (the launch parent gathers from all adapters). Handoffs are
de-duplicated by (`capability_binding_ref`, `execution_handle`) and ordered by that identity. `validate_report`
lets the selected adapter validate the form, then requires every form field sourced from `execution_handoff` or
`execution_handoffs` to equal the recorded facts (`resource_handoff_fact_mismatch`). `resolve` admits a report
reference that is visible in the episode's context or that the selected adapter resolves.
`received_evidence.py` `received_form_references`: a handoff inside a received form counts only with the
adapter's proof references (`resource_information_handoff_proof_missing` otherwise).

## Construction and identity

- `configuration.py`: `ResourceEpisode(services, *, resource_adapters=(), contract_information_profile=None)`.
  Adapters are explicit caller bindings keyed by `resource_id`; each must provide `capability`, `as_record`,
  `prepare_assignment`, `catalog`, `execute`, `fact_sources`, `facts`, `resolve`, `validate_report` and
  `credit_view` (`explicit_resource_adapter_required`); a repeated id raises `duplicate_resource_id`. Optional
  adapter members used elsewhere: `bind_record_selection`, `decision_context`, `check_handoff`,
  `received_form_references`.
- `binding_record.py`: `{'version': 'resource_episode_binding_v1', 'binding_id':
  'sequence_homology_evidence/resource_work_submission/api_resource_work_execution', 'configuration': {'resource_adapters': [...]}}`.
- `episode.py`: `binding_path`, `commissioning_parent`, `roles = ('launch_api',)`, `entry_roles = ()` (it is never a
  run entry in the old design), and `context_hook_applies` (its hooks apply only to role `launch_api`).

## How it differs from its siblings and similar episodes

Against its two siblings (`hpc_resource_work_execution`, role `launch_hpc`; `local_resource_work_execution`, role
`launch_local`): the three folders hold the same 21 files with the same line counts. They differ in exactly these
places: the responsibility sentence chosen in `goal.py` (here: execution through the selected actual API or
service, "including real availability and authentication"; HPC: "the selected actual environment, queue, staging
and execution interfaces"; local: "preparation, execution and receiving interfaces on the selected local
resource"); the kind the selected capability must have (`from_parent.py`: here `api`); the role handed to the
adapter (`prepare_assignment`, `fact_sources`); the `role` shown in the decision state; and the identity strings.
Everything else that separates API work from HPC or local work was meant to come from the selected resource
adapter: its tools, facts, duration estimates and report validation. Only this episode's sentence names
availability and authentication as part of the investigation.

Against the launch parent (`resource_work_submission`, 31 differing lines in `episode.py`, a handful elsewhere):
the parent may commission the three resource children and has `to_child_*`/`from_child_*` files; its assignment
may leave `resource_selection` null and its `prepare_assignment` returns the validated record without calling an
adapter; its catalog adds `resource.inspect` and `resource.check_handoff`; its facts, estimates and report
validation range over all adapters, where this episode uses only the selected one; it is an entry role and gets
the contract-information profile.

Against `execution_job_submission/api_job_execution` in the same axis (same old role name `launch_api`): that
episode has its own goal text, its own credit (255 differing lines), its own yield file (`ExecutionEpisodeYield`
with task yield profiles) and extra files for execution state, result acquisition and input custody. This
episode has none of that: it is the thin resource-adapter form, where everything resource-specific comes from the
adapter. The two are different episodes and should not be folded together.

Against the same-named episodes on A102 and A103: those folders are split into different files (32 files such as
`resource_selection.py`, `handoff_check.py`, `operation_catalog.py`, `decision_exchange.py`) and have no
`yield_estimator.py`, `task_instructions.py` or `execution_contracts.py`. Their contents were not read here.

Copied files: `task.py`, `task_decision.py`, `task_state.py`, `task_instructions.py`, `decision_state.py`,
`decision_inputs.py`, `report_delivery.py`, `waiting.py`, `yield_estimator.py` and `execution_contracts.py` are
this episode's private copies of the A101 decision loop. At this commit they are the same text in the three
sibling folders (only the docstring and the `defining_module` string differ), and nearly the same as the
parent's. The copies are intended, so each episode can be tuned alone; at this commit none of the three had been
tuned apart yet.

Current working tree (today's port, to be replaced by the carried-over files): the folder holds only `episode.py`.
Its class `ApiResourceWorkExecutionEpisode(A101ContractBinding, ApiJobConfiguration)` inherits a shared A101 base
class and the configuration of another episode (`execution_job_submission/api_job_execution`), takes its
controller and its decision source from that other episode (`runtime_credit.completion_controller`,
`runtime_source.ApiJobExecutionSource`), and asks for an assignment of `scope`, `resource_id` and `request`. None
of the intent above is in it: the launch assignment and its inheritance checks, the adapter catalog with
`resource.capabilities`, and the handoff facts are absent.

## File by file

Lines are at `97308b94c`. "Old-runner names" lists every name the file takes from the deleted runner or the old
axis-level modules; exact counts per name are in `runs/carry_over/calls/a101_05.tsv`.

| Old file | Lines | This episode's own intent in it | Old-runner names it uses |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| `tests/__init__.py` | 0 | none (no tests at this commit) | none |
| `goal.py` | 10 | The goal and instruction text for `launch_api`; the common tail about preserving the parent job, explicit unknown or unauthenticated resources, the parent-defined form and the local controller. The table also holds the four other roles' sentences, unused here. | `context.role` (BindingContext); hook `instructions(context)`; `self.credit_kind`; `self.contract_information_profile` |
| `episode.py` | 46 | Identity (`binding_path`, `commissioning_parent`, role `launch_api`), no children, not an entry, permitted action kinds, hooks apply only to its own role, the adapter interface description. | `decision_source_type`; `_original_continuation_owner`; `OriginalContinuation.original_continuation_controller`; hooks `roles`, `entry_roles`, `child_roles`, `allowed_children`, `permitted_common_actions`, `contract_information_profile`, `context_hook_applies`; `context.role`, `parent.role`; the class is assembled by inheriting the nine mixin classes of the other files |
| `configuration.py` | 22 | Construction over explicit resource adapters; the required adapter interface; duplicate and incomplete adapters raise. | `self.services` (old services object), `services.record_selection`; import `root.a101.composition_information:CONTRACT_INFORMATION_PROFILE` |
| `binding_record.py` | 7 | The binding's recorded identity and adapter configuration. | hook `as_record`; `adapter.as_record` |
| `from_parent.py` | 58 | The assignment form (launch assignment), the inheritance checks against the launch parent, the required resource selection of kind `api`, the adapter preparing the final assignment, no initial references. | `parent.role`, `parent.assignment`, `context.role` (BindingContext); hooks `assignment_schema`, `prepare_assignment`, `initial_references`; via `execution_contracts`: `LAUNCH_SCHEMA`, `RESOURCE_ROLES`, `_validate`, `plain`, `validate_selection` |
| `to_parent.py` | 62 | The report facts (`execution_handoff`, `execution_handoffs`, adapter facts), their de-duplication, reference resolution, and the check that reported handoffs equal recorded facts. | `self.services` (passed to `reference_in_context`); `context.role`, `context.assignment`; hooks `fact_sources`, `facts`, `resolve`, `validate_report`; via `execution_contracts`: `HANDOFF_SCHEMA`, `RESOURCE_ROLES`, `ReportBoundaryError`, `_array`, `_nullable`, `plain`, `reference_in_context` |
| `received_evidence.py` | 28 | A handoff in a received form needs the adapter's proof references. | hook `received_form_references`; via `execution_contracts`: `RESULTS_VERSION` |
| `internal_summary.py` | 17 | Its own decision fields: role, assignment, capabilities, the selected adapter's duration estimates. | `context.role`, `context.assignment`; hook `decision_context(context, current_view)`; via `execution_contracts`: `plain` |
| `execution_operations.py` | 68 | Capabilities (unbound ones shown without tools), the catalog (`resource.capabilities` plus the selected adapter's tools), tool execution and the handoff-check and inspect handlers. | `self.services.capabilities`; `context.role`, `context.assignment`; hooks `capabilities`, `catalog`, `execute`; via `execution_contracts`: `CAPABILITY_SCHEMA`, `RESOURCE_ROLES`, `RESULTS_VERSION`, `_validate`, `obj` |
| `execution_contracts.py` | 36 | The module docstring (adapters are explicit caller bindings; what `adapter_assignment` is; the results assignment carries handoff and requested data selector) and three small helpers: `_failure`, `_outcome`, `_availability_failure`. | imports `root.a101.communication` (`ReportBoundaryError`, `plain`), `root.a101.domain` (`obj`), `root.a101.episode_bindings` (`reference_in_context`), `root.a101.resource_records` (19 names), `root.a101.launch_instructions` (`validate_selection`), `root.a101.local_resources` (`LocalResources`, unused); it is the re-export hub for the other files |
| `credit.py` | 13 | Credit kind `operational`; credit read from the bound role credit. | `self.services.bound_role_credit`; hooks `credit_kind`, `credit_view`; `self.roles` |
| `yield_estimator.py` | 25 | Continuation is whatever the caller configured; no task key or credit definition for this operational episode. | `BindingContext` (import and construction); `workflow.controller_factory`, `workflow.run_id`, `workflow.receipts`, `workflow.receipts.known`, `workflow.scientific_projector_for_context`; journal episode row fields `request`, `initial_credit`; request message fields `scope`, `episode_assignment`; `binding.credit_kind`, `binding.continuation_task` |
| `task_instructions.py` | 26 | The general instruction text, the reasoning-commit requirement, and the order in which this episode's goal text, tool knowledge, launch instructions, delivery repair, waiting and native-event paragraphs are appended. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`, `.knowledge.instructions`, `.launch_instructions.instructions`, `.native_event_information`, `.decision_protocol` (7 members, 9 uses) |
| `decision_state.py` | 55 | Which fields the model sees at each decision (listed above). | 22 `self.workflow` members (22 uses): `store`, `store.read_snapshot`, `store.get`, `working_state`, `journal.db`, `journal.row`, `journal.elapsed_view`, `run_id`, `local_outcome_preview`, `source_credit_view`, `source_credit_binding`, `receipt_projection`, `pending_work`, `delivery_status`, `controller_binding`, `catalog`, `knowledge.context`, `job_episode_options`, `extra_report_sources`, `specialist`, `binding_context`, `tools`; journal table `runtime_actions`; imports from `root.a101.runtime`: `FACT_MEANINGS`, `FACT_SOURCES`, `_plain`, `_references_in`, `Mapping`, `json`; the rebinding block (`_bind_original_task_runtime_providers`, `bind_functions`, `_original_runtime`) |
| `decision_inputs.py` | 78 | Which run information is added per call (listed above). | 18 `self.workflow` members (23 uses): `resource_context`, `shared_information_context`, `launch_instructions.context`, `launch_instructions.materialize`, `available_child_roles`, `episode_bindings.initial_decision_context`, `binding_context`, `pending_work`, `execution_expectations`, `job_episodes`, `store`, `resource_estimator`, `resource_estimator.estimate_context`, `native_estimation_context`, `native_event_information`, `native_event_information.read`, `permits_common_action`, `waiting_support`; request message fields `episode_assignment`, `job_assignment`; imports `root.a101.runtime` (`child_option_information`, `Mapping`), `root.a101.episode_work_report` (`completed_action_reports`, `requested_action_history`), `root.a101.hpc_prompt` (`is_hpc_context`); the rebinding block |
| `task.py` | 239 | One action per decision; admission of the selection and of the report update; rejected selections create no unit; credit measured after every observed outcome; wait carries credit unchanged; specific feedback for some rejected selections. | 39 `self.workflow` members (70 uses), chiefly `journal.row/save/measure`, `store.transaction`, `execution_binding`, `inprocess_replay`, `completions.slot/stage`, `completed_unit`, `selected`, `execute`, `source_credit_view`, `controller_value`, `last_observed_credit`, `receive_outcome`, `receive_native_outcome`, `automatic_score_updates`, `retain_shared_grading_results`, `validate_report`, `resolver`, `action_schema`, `reasoning_action_schema`, `specialist`, `binding_context`, `services.instructions`, `permits_common_action`, `pending_work`, `next_return`, `resolve_pending_deliveries`, `delivery_resolution_inputs`, `decision_exchanges`; journal tables `runtime_actions`, `runtime_model_calls`, `runtime_episodes`; request message field `job_assignment`; 21 names from `root.a101.runtime`; `root.a101.providers:ModelCallError`; `root.a101.episode_source_failure:record_source_failure`; `root.a101.library.read_mapping_values:parameter_schema_failure`; the rebinding block |
| `task_decision.py` | 294 | How one decision is asked: saved request and response per call, the `request_context` / `select_action` exchange, the restored-history index for a fresh conversation. | 29 `self.workflow` members (49 uses), chiefly `journal.row/save/measure`, `decision_exchanges.rows/prepare/respond/resolve_lookup/measure`, `decision_protocol`, `provider.complete`, `receipts.receive`, `uses_received_record_context`, `validate_contract_information`, `freeze_contract_information`, `freeze_literature_numerical_contracts`, `numerical_contracts`, `contract_information_profile`, `contract_information_reply`, `controller_binding`, `history_preview`, `execute`, `store.get`, `services.decision_exchange_instructions`; journal table `runtime_model_calls`; 30 names from `root.a101.runtime`; the rebinding block |
| `task_state.py` | 115 | The state the episode keeps between decisions (report values and their basis, feedback, last outcome); a failed own action is recorded as an observed failed outcome. | 19 `self.workflow` members (29 uses): `journal.row/save`, `completions.restore_source/checkpoint_source/record_decision_effect/stage`, `inprocess_replay` (`unfinished`, `capture`), `execution_binding`, `recover_commissions`, `progress_provider.flush_notifications`, `archive.store`, `store`, `store.transaction`, `source_credit_view`, `controller_value`, `run_id`; `workflow.context`, `workflow.grains`; journal table `runtime_actions`; request message field `initial_report`; `request.report_contract`; 9 names from `root.a101.runtime` (`ActionLeaf`, `EFFECT_VERSION`, `Episode`, `Record`, `interpretation_schema`, `_json`, `_object`, `_plain`, `json`); `root.a101.episode_source_failure:record_source_failure`; the rebinding block |
| `report_delivery.py` | 34 | The result: the parent's typed form filled from interpretations and facts, or credit, pending handles and facts when no contract was given. | 8 `self.workflow` members (9 uses): `source_credit_view`, `pending_handles`, `episode_bindings.current_report_facts`, `binding_context`, `release`, `journal.row`, `journal.save`, `facts`; journal table `runtime_forms`; `request.report_contract`; `root.a101.runtime`: `Record`, `_json`, `form_with_facts`, `json`; the rebinding block |
| `waiting.py` | 31 | A selected wait is performed and an invalid wait target becomes failed feedback; suspension is reported while waiting. | `self.workflow.perform_selected_wait`, `.execution_handle`, `.execution_backend.set_suspension`; `root.a101.runtime`: `EventTargetError`, `_wait_target_feedback`; the rebinding block |

Old-runner machinery that carries no intent and goes away with the old runner: the `_bind_original_task_runtime_providers`
blocks at the end of seven files; resume, replay and checkpoint handling (`completions`, `inprocess_replay`,
`execution_binding`, `restore`, `checkpoint`, the `runtime_*` journal tables), which the new runner's journal and
recorder replace; receipt recording (`receipts.receive`, `receipts.known`); and the old role names. The
`annotation_axis_credit` branches and the `reads.map` and `bvbrc_minhash_result_selector_v2` feedback branches in
`task.py` come with the copied loop and do not concern a resource episode's own tools.

## Carried over

One row per row of `runs/carry_over/functions/a101__sequence_homology_evidence__resource_work_submission__api_resource_work_execution.tsv`: old file, kind, name copied, then the classification and the new place or the machinery reason. "library candidate" = a function that is not in `episode_support/` and stays in the episode file that uses it.

| old file | kind | name | class | new place / reason |
|---|---|---|---|---|
| binding_record.py | class | `OperationalBindingRecord` | machinery | binding_record.py: the binding's own record; the system records settings and declared services |
| binding_record.py | method | `OperationalBindingRecord.as_record` | machinery | the binding's own as_record() (README 3e) |
| configuration.py | class | `OperationalConfiguration` | machinery | configuration object over resource adapters: the adapters are the service `resource_adapter` the run supplies (SERVICES in task.py); the interface the service must offer is listed in the task.py docstring; hook-era home construction |
| configuration.py | method | `OperationalConfiguration.__init__` | machinery | construction over explicit adapters (required members, duplicate resource_id, `bind_record_selection`, the contract-information profile check) belongs to whoever builds the service; `record_selection` has no use (README 3c) |
| credit.py | class | `ResourceEpisodeCredit` | episode function | credit.py `credit` |
| credit.py | method | `ResourceEpisodeCredit.credit_kind` | machinery | credit kind is deleted (README 3d); the unknown-role check goes with the role names (each role is its own episode) |
| credit.py | method | `ResourceEpisodeCredit.credit_view` | episode function | credit.py `credit` reads `summary[adapter_credit]`; the adapter credit view is asked in task.py `resource_operation` and returned in its outcome (credit has no services) |
| decision_inputs.py | class | `OperationalDecisionInputs` | episode function | task.py `_context` |
| decision_inputs.py | method | `OperationalDecisionInputs.decision_inputs` | episode function | task.py `_context` (launch_instruction_library, selected_launch_instructions, resource_tool_estimates, native_event_targets as recorded service reads; completed_action_reports from the summary); not carried: `resource_context`, `shared_information_context`, `child_options`, contract information profile (never for this role), `requested_action_history`/`execution_expectations`/`job_execution_options`/`native_execution_expectations` (the adapter and `native_events` services supply the same information through `decision_context` and `targets`), `waiting_support` (the wait tool and its schema) |
| decision_inputs.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| decision_state.py | class | `OperationalDecisionState` | episode function | messages/internal_summary.py `internal_summary` |
| decision_state.py | method | `OperationalDecisionState.decision_state` | episode function | messages/internal_summary.py `internal_summary` and task.py `_context`; not carried: working_state/visible_record_refs/visual_evidence (journal-row reads and `image.view`, not a tool of this episode), `annotation_axis_credit` branches (root episode), `report_lifecycle`/`current_report_update`/`requested_form` (report-form machinery) |
| decision_state.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| episode.py | class | `ResourceEpisode` | episode function | episode.py `ApiResourceWorkExecution` (the old class assembled mix-ins; the new class only assigns members) |
| episode.py | method | `ResourceEpisode.child_roles` | episode function | task.py `CHILD_SLOTS = {}` |
| episode.py | method | `ResourceEpisode.contract_information_profile` | machinery | never applied to this role (profile only for `launch`); the discovery paragraph is not carried (goal.py docstring) |
| episode.py | method | `ResourceEpisode.permitted_common_actions` | episode function | task.py `_schema` / `action` (tool, reason, wait; `child` and `redeliver_report` could never be carried out here) |
| episode.py | method | `ResourceEpisode.allowed_children` | episode function | task.py `CHILD_SLOTS = {}` |
| episode.py | method | `ResourceEpisode.context_hook_applies` | machinery | hook applicability by role: each role is its own episode |
| execution_contracts.py | function | `_failure` | episode function | task.py `_failure` (library candidate) |
| execution_contracts.py | function | `_outcome` | episode function | task.py `_outcome` (library candidate) |
| execution_contracts.py | function | `_availability_failure` | episode function | task.py `_availability_failure` (library candidate) |
| execution_operations.py | class | `OperationalOperations` | episode function | task.py tools `prepare_resource_assignment`, `resource_capabilities`, `resource_operation` |
| execution_operations.py | method | `OperationalOperations.capabilities` | episode function | task.py `capabilities_of` and `_capabilities` (library candidate) |
| execution_operations.py | method | `OperationalOperations._adapter` | episode function | task.py `prepare_resource_assignment` (`resource_not_bound` against the service `bound_resource_ids()`); the results-handoff branch (`RESULTS_VERSION`) is the service's `check_handoff` |
| execution_operations.py | method | `OperationalOperations.catalog` | episode function | task.py `_catalog` and `CAPABILITIES_ENTRY` |
| execution_operations.py | method | `OperationalOperations.execute` | episode function | task.py `resource_operation` (`resource.capabilities` is the tool `resource_capabilities`; the catalog and argument check `tool_not_owned_by_resource_role` / `_validate` are `action`'s schema validation) |
| from_parent.py | class | `OperationalAssignment` | episode function | messages/read_from_parent.py |
| from_parent.py | method | `OperationalAssignment.assignment_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (one field per `LAUNCH_SCHEMA` property) |
| from_parent.py | method | `OperationalAssignment._permitted` | episode function | task.py `_permitted` (library candidate) |
| from_parent.py | method | `OperationalAssignment._require_launch_child_instruction_pins` | machinery | check of a commission against the launch parent (`launch_instruction_inheritance_conflict`): a wrong commission just fails, nothing checks it (README 3b C3) |
| from_parent.py | method | `OperationalAssignment.prepare_assignment` | episode function | messages/read_from_parent.py `read_from_parent` (schema validation, explicit selection of kind api) and task.py `prepare_resource_assignment` (capability kind and constraints, bound, adapter preparation); the equality checks against the parent's assignment (`resource_assignment_conflict`, `resource_selection_conflict`) are checks of a commission and are not carried |
| from_parent.py | method | `OperationalAssignment.initial_references` | machinery | returned `[]`; records are passed by `record_refs` fields of the assignment |
| goal.py | class | `OperationalGoal` | episode function | goal.py |
| goal.py | method | `OperationalGoal.instructions` | episode function | goal.py `GOAL` (responsibility and common tail) and task.py `_instructions` |
| internal_summary.py | class | `OperationalSummary` | episode function | messages/internal_summary.py |
| internal_summary.py | method | `OperationalSummary.decision_context` | episode function | messages/internal_summary.py `internal_summary` (role, assignment, capabilities) and task.py `_context` (`resource_tool_estimates` through a recorded service read) |
| received_evidence.py | class | `ReceivedOperationalEvidence` | machinery | receipts bookkeeping: proof references of a handoff inside a received form; custody replaces it (the handoff records are returned in `execution_handoff_refs`) |
| received_evidence.py | method | `ReceivedOperationalEvidence.received_form_references` | machinery | receipts bookkeeping (`received_form_references`, README 3b R3) |
| report_delivery.py | class | `OperationalReportDelivery` | episode function | messages/final_to_parent.py |
| report_delivery.py | method | `OperationalReportDelivery.finish` | episode function | messages/final_to_parent.py `final_to_parent` (the form-filling with the parent's schema and `runtime_forms` saving is report-form machinery; the no-contract result `credit`/`pending_handles`/facts: credit and facts are returned, `pending_handles` is deleted) |
| report_delivery.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| task.py | class | `OperationalTask` | episode function | task.py |
| task.py | method | `OperationalTask.instructions` | episode function | task.py `_instructions` |
| task.py | method | `OperationalTask.next` | episode function | task.py `decide`; the restore, replay, checkpoint, `SourceEnd`, pending-delivery and ready-child parts are old-runner machinery |
| task.py | method | `OperationalTask.apply_response` | episode function | task.py `action` (validation of the selection, the `empty_reasoning_commit` check, `Rejected` feedback); not carried: `report_update` admission (`report_format`, `validate_report` of the parent-defined form), wait-target `invalid` feedback (the wait validates its targets in the tool and returns a failed outcome), `ContractInformationError`/results-selector/`reads.map` feedback branches (other episodes' tools), `record_effect` |
| task.py | method | `OperationalTask.execute` | episode function | task.py tools (`reason`, `wait`, `resource_operation`, lookups); the journaling, measuring, `receive_outcome`, `automatic_score_updates` and controller input are the system's |
| task.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| task_decision.py | class | `OperationalTaskDecision` | episode function | task.py `decide` |
| task_decision.py | method | `OperationalTaskDecision.call` | episode function | task.py `decide` returns the `ModelRequest`; the saved request/response per call and `journal.measure` are the system's |
| task_decision.py | method | `OperationalTaskDecision.conversation_key` | machinery | conversation state (README 3a: deleted) |
| task_decision.py | method | `OperationalTaskDecision.interpretation_context` | machinery | `request_context` exchange (a lookup is a tool) |
| task_decision.py | method | `OperationalTaskDecision.exchange_schema` | machinery | decision-exchange loop |
| task_decision.py | method | `OperationalTaskDecision.exchange_response` | machinery | decision-exchange loop |
| task_decision.py | method | `OperationalTaskDecision.validate_contract_exchange_request` | machinery | saved-request check of the decision exchange |
| task_decision.py | method | `OperationalTaskDecision.validate_contract_exchange_history` | machinery | saved-request check of the decision exchange |
| task_decision.py | method | `OperationalTaskDecision.exchange_decision` | machinery | decision-exchange loop (`exchange_decision`) |
| task_decision.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| task_instructions.py | function | `instructions` | episode function | task.py `_instructions` (INSTRUCTIONS with the report/redelivery/history span replaced, goal, reasoning commit requirement, tool knowledge, launch instructions, native events; the pending-child-delivery and pending-child wait paragraphs and the `decision_exchange_v1` replacement are not carried: no child, no exchange) |
| task_state.py | class | `OperationalTaskState` | episode function | messages/internal_summary.py (the state between decisions is a pure function of the view) |
| task_state.py | method | `OperationalTaskState.__init__` | episode function | messages/internal_summary.py (feedback, last outcome); the report values/basis are report-form machinery |
| task_state.py | method | `OperationalTaskState.bind_execution_context` | machinery | execution context binding of the old runner |
| task_state.py | method | `OperationalTaskState.record_execution_failure` | machinery | a failed or invalid returned outcome is the tool's returned outcome and enters the iterator; the summary reads its feedback |
| task_state.py | method | `OperationalTaskState.restore_checkpoint` | machinery | checkpoint/restore |
| task_state.py | method | `OperationalTaskState.restore` | machinery | checkpoint/restore |
| task_state.py | method | `OperationalTaskState.record_effect` | machinery | recorder (`record_effect`) |
| task_state.py | method | `OperationalTaskState.checkpoint` | machinery | checkpoint/restore |
| task_state.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| to_parent.py | class | `OperationalReport` | episode function | messages/final_to_parent.py |
| to_parent.py | method | `OperationalReport.fact_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` (`execution_handoff`, `execution_handoffs`; the adapter's own fact sources in the selectable field `adapter_facts`) |
| to_parent.py | method | `OperationalReport.facts` | episode function | messages/final_to_parent.py `handoff_facts` and `final_to_parent` (library candidate) |
| to_parent.py | method | `OperationalReport.resolve` | machinery | reference resolution for the parent-defined form: `records.holds` and custody (README 3b D2) |
| to_parent.py | method | `OperationalReport.validate_report` | episode function | messages/final_to_parent.py `validate_report` (handoff fields equal the recorded facts, `resource_handoff_fact_mismatch`); the adapter's `validate_report` of the parent-defined JSON-Schema form is not carried (that form no longer exists) |
| waiting.py | class | `OperationalTaskWaiting` | episode function | task.py `wait` |
| waiting.py | method | `OperationalTaskWaiting._execute_selected_wait` | episode function | task.py `wait` (calls the library `selected_wait` with the service `native_events`) |
| waiting.py | method | `OperationalTaskWaiting.suspension_changed` | machinery | suspension of the old execution backend (`set_suspension`): wait/suspension machinery |
| waiting.py | function | `_bind_original_task_runtime_providers` | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`) |
| yield_estimator.py | class | `OriginalContinuation` | machinery | delegate of the old runner's `controller_factory`; replaced by yield_estimator.py `yield_controller` |
| yield_estimator.py | method | `OriginalContinuation.original_continuation_controller` | episode function | yield_estimator.py `yield_controller` (the completion controller; the old file chose none itself) |

The old tests folder held only an empty `tests/__init__.py`; nothing was retired. The new tests are `tests/test_api_resource_work_execution_binding.py`.
