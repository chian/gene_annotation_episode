# a106/perturbation_evidence/published_evidence_assessment/execution_job_submission — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/execution_job_submission/<file>`
(only the 27 files directly in this folder; there is no `grading/` or `scoring/` subfolder. The `api_job_execution/` child
is described separately.)
Class: `ExecutionEpisode` in `episode.py`, which mixes 13 private responsibility classes (`LaunchParentAssignment,
OperationalConfiguration, OperationalBindingRecord, OperationalGoal, OperationalAssignment, OperationalReport,
ReceivedOperationalEvidence, OperationalSummary, OperationalExecutionState, NativeInputCustody, OperationalOperations,
ExecutionEpisodeCredit, ExecutionEpisodeYield`). Its decision source is `OperationalTask` (`task.py`), which mixes 6 classes.
- `binding_path = 'perturbation_evidence/published_evidence_assessment/execution_job_submission'`
- `commissioning_parent = 'perturbation_evidence/published_evidence_assessment'`
- `roles = ('launch',)`, `entry_roles = ('launch',)`, `replaces_default_instructions = True`
- `VERSION = 'execution_episode_v1'`, `LAUNCH_VERSION = 'execution_launch_assignment_v1'`,
  `RESULTS_VERSION = 'execution_results_assignment_v1'`, `_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'`
- `ROLES = ('launch', 'launch_api', 'results')`, `KINDS = {'api': 'api'}`, `ROLE_KINDS = {'launch_api': 'api'}`. Only API
  resources exist in this copy. No local or HPC resource kind is present.
- `credit_kind(role)` returns `'operational'` for any role in `self.roles` and raises `unknown_execution_episode_role` otherwise.
  Every public hook calls it first, so the hook is restricted to this binding's own role.

## What this episode is for (its goal, in its own words)

`goal.py`, `OperationalGoal.instructions(context)`:

> "Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and pinned
> instructions. A resource child carries out iterative execution in the private loop. Receive its requested typed handoff;
> no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with exact zero
> future credit."

This episode is the **launch** endpoint of A106's execution work. The published-evidence-assessment parent hands it a map
of concrete execution requests, one per configured resource. The episode picks which permitted request to commission and
commissions one `launch_api` resource child, which does the iterative service work. The episode then receives that child's
typed handoff, a record of the submitted remote job that can be used to monitor it or fetch its results. The episode does no
scientific interpretation of its own.

## Task and instructions

`task_instructions.instructions(source, context)`. This file is identical in all three sibling episodes.
1. The base `INSTRUCTIONS` text is the long scientific-annotation guidance ("You own an iterative scientific annotation
   improvement, not a tool itinerary ..."). It is copied verbatim into this file.
2. The specialist's `instructions(binding_context)` is the goal text above. Because `replaces_default_instructions = True`,
   the goal text **replaces** the base text and is not appended to it.
3. `REASONING_COMMIT_REQUIREMENT` is added when `reason` is permitted. It is permitted here.
4. `workflow.knowledge.instructions` is added when `tool_knowledge` is in the context. `workflow.launch_instructions.instructions`
   is added when `launch_instruction_library` is in the context. This episode always adds the latter in `decision_inputs`.
5. The pending-child-delivery repair text is always added: select `redeliver_report` and preserve `current_report_update`.
6. The wait text is added because `wait` is permitted. A `pending_child_` handle names the in-process child. The model waits
   with `event returned, after_cursor 0, reconsider_at null`. Waiting earns no credit.
7. The native-event-target text is added when `workflow.native_event_information` is set.
8. Under `decision_exchange_v1`, the restored-history guidance is replaced by `request_context` / `episode.history
   view=records` guidance.
The instructions the model actually receives come from `OperationalTask.instructions = self.workflow.services.instructions(self, context)`,
which uses `instruction_composer = compose_instructions`.

`task.py` (`OperationalTask.next / apply_response / execute`):
- `next` performs these steps:
  - When the episode is closed with `source_failed` and its unit count matches, it returns `SourceEnd('source_failed')`.
  - When in-process replay is active, it restores state and replays ready units and unfinished own actions.
  - When a durable execution binding is active, it restores the recorded completion slots, unfinished actions,
    `next_return` and pending deliveries.
  - Otherwise it makes one model decision per unit. It reuses a saved model-call request when one exists. A
    `ModelCallError` is recorded through `record_source_failure` and ends the source with `SourceEnd('source_failed')`.
- `apply_response` validates a selection as follows:
  - It decodes the recorded response.
  - A `reason` selection is validated against the reasoning envelope. An all-empty commit is rejected as
    `empty_reasoning_commit` unless the specialist's `reasoning_has_task_content` admits it or the selection is
    `no_applicable_evidence`.
  - Any other selection is validated against `schema.properties.selection`.
  - When a delivery is being repaired, `report_update` must equal the current values.
  - Invalid selections become typed `feedback` and are recorded with `record_effect(index, 'rejected')`. The feedback
    includes a contract-information repair hint for `closed_top_level_form_required` and the required fact sources for
    `component_native_return_channels_required`.
  - The `report_update` is then admitted through the resolver and `validate_report`.
- `execute` runs one selected action:
  - A changed reconstruction raises `reconstructed selected work changed`.
  - A `reason` selection goes to the specialist's `execute_reasoning` when present, otherwise to `store.commit_reasoning`.
  - A `wait` selection goes to `_execute_selected_wait`. Anything else goes to `workflow.execute(tool)`.
  - `pending_work_after_action` is appended to the result.
  - Native outcomes and ordinary outcomes are received, and automatic score updates run.
  - The credit is `source_credit_view(...).credit`. For a wait it is `last_observed_credit`.
    `shared.read_information` keeps its grading results.
  - When no outcome is observed, the action raises `ActionFailure`. A failed or invalid action therefore still enters the
    iterator.
- `task_state.record_execution_failure` turns an exception during a tool or reason action into a `failed` outcome. That
  outcome still gets a credit and a staged controller input, as an `ActionLeaf`.

## What it reads from its parent's assignment

`from_parent.assignment_schema('launch')` and `from_parent_launch._parent_launch_assignment_schema` define the same closed
object. The parent must send these fields:
- `version`: const `execution_launch_assignment_v1`.
- `requests`: an object with at least one property. Its keys are the configured `resource_id`s. Each value is that
  resource's concrete API request schema, taken from `api_execution.assignment_schema(resource_id)` with a
  `resource_id: const` added.
- `immutable_input_versions`: an array of `INPUT_VERSION_SCHEMA`.
- `constraints`: an object. It may contain `allowed_resource_ids`, `allowed_kinds`, `resource_id` and `kind`.
  `_constraints` requires the two list fields to be lists of non-empty strings.
- `launch_instructions`: the `SELECTION_SCHEMA` of the launch instruction library, i.e. the pinned instructions.

The assignment is admitted in two places:
- `prepare_assignment` runs when this episode is commissioned. It validates the request with `checked`, then `_launch`
  validates every request through `api_execution.validate_assignment` (also against the scope). It then checks the immutable
  input versions with `_versions`, which calls `validate_execution_input_versions`, against the parent's scope.
- `initialize` re-admits the assignment and the versions against the episode's own scope.

`_permitted(assignment, resource_id)` says whether a resource may be commissioned. It must appear in `requests` and pass
every constraint present.

`initial_references` is empty.

## Children it may commission

One slot: role `launch_api`, binding `.../execution_job_submission/api_job_execution`.
- `child_roles` returns `tuple(ROLE_KINDS)`, which is `('launch_api',)`.
- `allowed_children` returns `launch_api` only when some configured resource of kind `api` is `_permitted` by the parent's
  launch assignment.
- **Sent** (`to_child_api_job_execution.prepare_commission`):
  - The scope is validated as a subset of the parent's scope.
  - The report-contract form is expanded with `workflow.expanded_contract_form`.
  - The child binding is looked up with `episode_bindings.for_child`. Its path must equal the api_job_execution path,
    otherwise `child_binding_path_conflict` is raised.
  - Every source in the child's `required_return_sources` must appear exactly once in the return schema, otherwise
    `child_return_requires_<source>` is raised.
  - The initial report input is validated against the interpretation schema.
  - The role must be among the allowed children.
  - The pinned `launch_instructions` are materialised.
  - The specialist's `prepare_child_request` runs when present.
  - Finally the child's own `prepare_assignment(parent_ctx, 'launch_api', assignment, scope, key)` produces the child
    assignment: **one** selected resource request, which must carry `resource_id`. The child also re-checks the original
    launch's immutable input versions.
  - Result: `{scope, role, schema, report_declaration, initial, episode_assignment, perturbation_evidence: None, assignment: None}`.
- **Taken back** (`from_child_api_job_execution.receive_report`):
  - The delivery role must be `launch_api` and the binding path must match.
  - When receipts are active, it is not a redelivery and the source is not a job source, the already-recorded admission
    references are reused through `EpisodeReturnRecords.recorded_admission_references`.
  - The form goes to the progress provider. The specialist's `receive_child_progress_for_role` or
    `receive_child_progress` handles it when present, otherwise `progress_provider.receive_form` does.
  - The references are collected from the form and from `episode_bindings.received_form_references`. The latter calls
    this episode's `received_form_references`, which admits the AppService application references and requires each
    `execution_handoff_refs`, `execution_result_refs` and `bvbrc_appservice_support_refs` entry to resolve.
  - When native timing information is present, the timing receipts are frozen once into
    `runtime_report_attempts.timing_receipts` and their `native_execution_refs` are appended.
  - Everything is recorded as receipts of kind `child_form` or `report_redelivery`.

## Decision state and what it shows the model

`decision_state.decision_state(view)` is the old common decision frame. It contains:
- `goal`, `scope`, `working_state` and `visible_record_refs`.
- `current_credit` and `current_evidence_vector`. `investigation_progress` is included when receipt projection is on.
- `credit_binding` and `time_accounting` (`journal.elapsed_view`).
- `pending_work`, `last_local_outcome`, `feedback` and `visual_evidence`, the last completed `image.view` pixels.
- `report_deliveries`, `controller` and `controller_binding`.
- `tools`, `tool_knowledge` and `job_episode_options`.
- `available_report_facts`, `requested_report_purpose`, `requested_form`, `current_report_update`,
  `current_report_basis_refs` and `report_lifecycle`.
- Child reports.
- Monitoring credit fields when present, and the A101–A104 `_completed_work_axis_results` sheets.

`present_credit_state` collapses the frame when credit is `annotation_axis_credit`; for this binding that does not happen.

The specialist part (`internal_summary.py`) adds:
- `initial_decision_context`:
  - `execution_resource_capabilities`: for each resource, `{resource_id, resource_kind:'api', availability:'unknown',
    tool_names, service, base_url, inventory_snapshot}`.
  - `execution_initial_information`.
- `decision_context`: `execution_assignment` (the launch assignment) and `execution_progress` (`facts(context, {})`).

`decision_inputs.decision_inputs` then adds:
- `resource_context` and `shared_information_context`.
- `launch_instruction_library` and `selected_launch_instructions`, the materialised pinned instructions.
- `child_options`, as text.
- The initial binding context above. A field that collides raises `initial_binding_context_field_conflict`.
- `completed_action_reports`, `pending_work`, `execution_expectations`, `resource_tool_estimates`,
  `native_execution_expectations`, `waiting_support` and `contract_information_profile`.

`task_decision.call / exchange_decision` covers the model-call protocol:
- It freezes the request: context, schema, assignment transport and literature numerical contracts.
- It supports the `decision_exchange_v1` protocol: `request_context` lookups of `child_options`, `composition_information`
  or its own attempts, followed by `select_action`. Recorded exchanges are validated against the original snapshot and
  replies.
- The model call is `workflow.provider.complete(episode_id, 'REASONING', instructions, context, _action_generation_schema(schema))`.
- `decision_yield_table` supplies the `yield_table` in the snapshot.

## Tools it offers

`permitted_common_actions = ('tool', 'reason', 'child', 'wait', 'redeliver_report')`.

Own catalog (`launch_operation_catalog`): one operation, `execution.capabilities`. Its description is "Read the actual
caller-bound resource configuration and already recorded inventory; no discovery or selection." It takes the empty input
schema `{}`. `execute` validates the arguments and returns `_outcome(initial_decision_context)`, a `completed` outcome with
no record refs. Errors return an `invalid` outcome with category `arguments_or_reference`.

The real service work is in the child. This episode itself never calls the API.

## How its credit is counted

`credit.py`, `ExecutionEpisodeCredit`. Credit is operational.
- **Live credit** (`_live_project_credit`):
  - `_received(context, selection)` reads every known reference that is an API handoff source, admits it with
    `_context_target`, and keeps it when it can be returned.
  - The kept handoffs are filtered to usable ones.
  - The baseline is the set of resource_ids whose handoffs were already in `initial_known_record_refs`.
  - `credit = handoff_unit * |distinct resource_ids among usable handoffs − baseline|`.
  - The view reports `operational_credit`, `new_handoff_count` and `new_acquired_record_count: 0`, plus
    `operational_credit_binding`: `{version: 'execution_received_records_credit_v1', handoff_unit, acquired_record_unit,
    qualification: 'original_request_resource_scope_selector_and_actual_received_unique_information'}`.
  - Credit is unbounded: one unit per newly received resource handoff.
- **Receiver selection** (`execution_state._selection`) sets which references count as known:
  - the `services.record_selection` callback when one is supplied;
  - otherwise the receipts and their baseline, when `runtime_receipt_inheritance` has a row;
  - otherwise the record_refs of the episode's own `runtime_actions`, with an empty initial set.
  - The selection's identity must match and initial must be a subset of known.
- **Closed credit**: closing facts freeze a `_CLOSED_CREDIT` snapshot. It holds hashes of the context, binding,
  completion, archive and observation history, the receiver selection, the receipt prefix across the inheritance chain,
  and the view. `project_credit` returns that frozen view once it exists ("never reprices"). Every hash and receipt
  prefix is re-authenticated, and a mismatch raises `execution_closed_credit_*_conflict`.
- **Completion proof**:
  - `completion_for_action` / `_proof_for_action`: a completed action whose record_refs include a usable handoff that
    matches this context yields a `practical_completion_v1` proof with `endpoint 'usable_handoff'` and `validation_keys
    ['received_usable_handoff']`.
  - `verify_completion` accepts a proof that matches exactly one recorded observation with zero expected gain, on a closed
    view, or that equals the proof recomputed for its operation_key.

## Continuation (yield estimator and settings)

`yield_estimator.py`. It requires `require_private_yield=True` and otherwise raises `execution_private_yield_binding_not_enabled`.
- **When eligible original requests are not yet received**:
  - `remaining = (#eligible resource_ids − #already received usable in initial handoffs) * handoff_unit`.
  - The estimator is `BoundedYieldController(epoch, initial_credit, cutoff, remaining, YieldParameters(**params))`, the
    old **bounded quality** estimator with a finite remaining maximum.
  - The profile key is `'launch:' + '+'.join(sorted(_request_yield_class(request) for eligible))`, where the class is
    `api_<service>[_<algorithm>][_<database>]_handoff`.
- **When nothing remains**:
  - A non-zero initial credit raises `launch_no_uncredited_requests_but_nonzero_initial_credit`.
  - Otherwise the estimator is a `YieldController(epoch, initial_credit, 0.0, YieldParameters(), estimate_with_context=no_remaining_requests)`.
    Its estimate is exact zero (`launch_original_request_exhaustion_v1`), and any non-zero history raises.
- **Settings**: `task_yield_profiles[key] = {cutoff: positive finite, parameters: YieldParameters kwargs}`. These are
  validated in `configuration.__init__` by constructing a `YieldController`. A missing key raises
  `execution_original_task_yield_profile_required:<key>`.
- `practical_estimator(context)` is `PracticalYieldEstimator(verify_completion)`, kept for the practical endpoint.

In the new three-estimator set, the first branch maps to **bounded quality**, with the maximum equal to the remaining
original-request credit. The exhausted branch is an exact-zero forecast. Whether that is the **completion with a target**
estimator with target 0, or an immediate stop, has to be decided when the episode is ported.

## What it reports to its parent

`to_parent.py`:
- `fact_sources` are:
  - the AppService application fact sources (`application_fact_sources()` + `bvbrc_appservice_support_refs`);
  - `execution_handoff_refs` (namespace `execution_handoff`);
  - `execution_result_refs` (namespace `execution_result`);
  - `execution_completed` (boolean: "Yielding alone is false").
- `facts` = `_live_facts`, read in one snapshot:
  - `execution_handoff_refs` = the sorted received returnable handoffs;
  - `bvbrc_appservice_support_refs` = `api_execution.appservice.received_support_refs`;
  - `execution_result_refs = []`;
  - `execution_completed` is true when any received handoff is complete.
  - The `_closed_credit_facts` snapshot is merged in when the episode closes.
- `required_return_sources`: when the parent's path ends in `perturbation_evidence` and `services.annotation_task_required()`
  holds, the return must carry `execution_handoff_refs`. This "preserve[s] the original job identity across a scientific return".
- `resolve` / `validate_report`:
  - References are resolved in this order: FBA, fluorescence, NMF, ATAC, chromatin, then protein access, then the API
    execution, then a refusal for a bare handoff source, then `reference_in_context(services, ...)` or the store scope.
  - Fact-sourced fields must equal the recorded facts, otherwise `execution_report_disagrees_with_recorded_facts` is raised.
- `received_evidence.py` validates what this episode **receives** for its own `annotation`/`perturbation_evidence` parent. It
  covers the received report sources and facts, AppService support-ref and application-return validation, and resolution
  of the native result references.
- **Report delivery** (`report_delivery.finish`):
  - Without a report contract it returns `{credit, pending_handles, current_report_facts}`.
  - Otherwise it reuses the form saved in `runtime_forms`, or builds `form_with_facts(report_values, schema, facts)` and
    saves both, then releases the episode.

## Configuration it is built with

`configuration.__init__(services, *, store, directory, run_id, resources, initial_information, tool_registry, handoff_unit,
acquired_record_unit, log_window_bytes, log_roles, require_private_yield=False, task_yield_profiles=None)`.
- `resources` must be non-empty and every kind must be in `KINDS`. `initial_information` keys must be a subset of
  `resources`.
- Both credit units must be positive finite numbers. `log_window_bytes` must be an int ≥ 1, and `log_roles` non-empty
  strings.
- It builds these objects:
  - `APIServiceExecution(...)` for the API resources, with the received-input reader, `application_return_owner=self`,
    `support_receipts=self._appservice_received_support_refs` and the validator.
  - `ExecutionProgressProvider`.
  - `FluxBalanceExecutionInputs`.
  - The native result and return hosts for protein structure and fluorescence, always.
  - The FBA hosts when an ordinary FBA backend or `native_flux_balance` is present. The NMF, ATAC and chromatin hosts when
    their resource flags are set.
- `binding_record.as_record` publishes this configuration under `binding_id = binding_path`.

## Differences from siblings

- Compared with **api_job_execution** (its child):
  - This copy is the only one that commissions a child. It permits `reason`, `child` and `redeliver_report`; the child
    permits only `tool` and `wait`.
  - Its own catalog is just `execution.capabilities`.
  - Its credit counts distinct new resource handoffs locally; the child's credit comes from `api_execution.credit_view`.
  - It uses the **bounded** yield controller keyed `launch:<classes>`; the child uses a plain controller with a practical
    estimator keyed `launch_api:<class>`.
  - It requires `execution_handoff_refs` from a scientific return.
  - Its `APIServiceExecution` is built without the child's credit projector, decision summary, report facts, completion
    projector, context reader or operation catalog callbacks.
- Compared with **execution_result_acquisition**: that sibling is a separate entry from the same parent, with role
  `results`. It reads an existing handoff and has no children.
- These 11 files are identical, except for docstrings and module paths, across all three episodes: `task_instructions`,
  `execution_contracts`, `from_parent_launch`, `task`, `task_state`, `task_decision`, `decision_inputs`,
  `decision_presentation`, `decision_state`, `received_evidence` and `native_input_custody`. This episode's `task.py` is the
  only one that keeps the `reason` branches.

## File by file

Old-runner names use `w.` for `self.workflow.` / `source.workflow.` / `workflow.`. Counts are occurrences in the file;
the full list is in `runs/carry_over/calls/a106_04.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `binding_record.py` | 8 | Binding identity and configuration record (`binding_id`, VERSION, resources, units, log window, private yield, task yield profiles) | — |
| `configuration.py` | 92 | Explicit resources and units, validation of task yield profiles, construction of the API execution host, progress provider and native result/return hosts | `a106.numerical:YieldController, YieldParameters`; `self.services` (`read_received_molecular_input`); support imports `api_service_execution`, `execution_progress`, `library.retained_input_authority.*` (15 hosts) |
| `credit.py` | 206 | Operational credit (handoff_unit per new resource handoff), closed-credit snapshot and authentication, completion proof (usable handoff) | `self.store.db` (8); tables `runtime_episodes`, `runtime_observations`, `runtime_receipt_inheritance`, `runtime_record_receipts`, `runtime_forms`, `runtime_actions`; `a106.episode_return_records:EpisodeReturnRecords, _same`; `a106.episode_receipts:EpisodeReceipts`; `a106.method_loop.identities:UnitRef`; `a106.numerical:NumericBand`; `a106.practical_yield:ESTIMATOR_VERSION`; `context.as_record()` (BindingContext) |
| `decision_inputs.py` | 71 | Adds the launch instruction library, selected pinned instructions and child options to the model inputs | `w.resource_context, w.shared_information_context, w.launch_instructions(2), w.available_child_roles, w.episode_bindings.initial_decision_context, w.binding_context, w.pending_work, w.execution_expectations, w.resource_estimator(4), w.native_estimation_context, w.permits_common_action, w.waiting_support`; `a106.runtime:child_option_information, Mapping`; `library.live_runtime_functions:bind_functions` |
| `decision_presentation.py` | 51 | Credit-state presentation, completed-work reports, yield table | `w.journal.row` (`runtime_actions`), `w.controller_binding`; `a106.runtime:_plain, json, Mapping, _category_yield_parameters, yield_table`; `a106.episode_work_report:completed_action_reports`; `bind_functions` |
| `decision_state.py` | 78 | The common decision frame (see above) | `w.store.read_snapshot/get/reference_subset, w.working_state, w.journal.db` (`runtime_actions` image.view query), `w.run_id, w.local_outcome_preview, w.source_credit_view, w.receipt_projection, w.source_credit_binding, w.journal.elapsed_view, w.pending_work, w.delivery_status, w.controller_binding, w.catalog, w.knowledge, w.job_episode_options, w.extra_report_sources, w.specialist, w.binding_context, w.tools`; `a106.runtime:FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json`; `bind_functions` |
| `episode.py` | 55 | Identity (path, parent, roles), child roles, allowed children by permitted API resource, permitted actions, context-hook ownership (`launch` only), child preparer/receiver mapping for `launch_api` | old hooks `child_request_preparer_for_binding`, `child_report_receiver_for_binding`, `context_hook_applies`, `decision_source_type`, `commissioning_parent` |
| `execution_contracts.py` | 26 | Versions, roles/kinds, `RESULTS_SCHEMA`, `execution.capabilities` catalog, `_outcome` shape | `a106.communication:plain, validate_form`; support `a106.execution_contracts:canonical, checked, digest, obj`, `launch_instructions:SELECTION_SCHEMA`, `practical_execution_records:validate_completion_proof`, `resource_records:INPUT_VERSION_SCHEMA` |
| `execution_operations.py` | 34 | Resource information/capabilities, own catalog and execute, AppService fact sources | support `library.bvbrc_application_facts:application_fact_sources` |
| `execution_state.py` | 57 | `initialize` re-admits launch and versions; `_check_parent_inputs`; `_target`; receiver `_selection`; `_context_target` per role | `self.store.db` (4); tables `runtime_episodes`, `runtime_receipt_inheritance`, `runtime_actions`; `a106.episode_receipts:EpisodeReceipts`; `self.services.record_selection` |
| `from_child_api_job_execution.py` | 46 | Admit the `launch_api` child form: path check, progress, references, timing receipts | `w.episode_bindings.for_child, w.receipts(2), w.is_job_source(2), w.store, w.run_id(6), w.binding_context(4), w.progress_provider(3), w.specialist, w.episode_bindings.received_form_references, w.native_timing_information, w.job_episodes(.received_timing_records), w.store.transaction/db/get/reference_subset`; table `runtime_report_attempts`; `a106.runtime:_references_in, _json, WorkflowError, json`; `a106.delivery_counterpart:child_role_for_delivery`; `a106.episode_return_records:EpisodeReturnRecords` |
| `from_parent.py` | 63 | Launch assignment schema, `_permitted`, `prepare_assignment`, request schema/validation, `_launch`, `_constraints`, `initial_references` | — (support via `self.api_execution`) |
| `from_parent_launch.py` | 9 | The parent's original launch form, admitted independently | — |
| `goal.py` | 9 | Goal text (quoted above) | — |
| `internal_summary.py` | 13 | `initial_decision_context` (capabilities and inventory), `decision_context` (assignment and progress) | — |
| `native_input_custody.py` | 229 | Immutable input versions; restoring a recorded `results` commission; selector; per-native-family reference access (protein, ATAC, chromatin, FBA, fluorescence, NMF); native input validators (ATAC, MACS2, LUMPY, NMF, fluorescence); FBA assignment match; selected result action lookup | `self.store.db` (5); tables `runtime_report_attempts`, `runtime_episodes`, `runtime_actions`; `a106.episode_receipts:EpisodeReceipts`; `a106.episode_return_records:EpisodeReturnRecords`; support `execution_input_versions`, `library.retained_input_authority.*` |
| `received_evidence.py` | 173 | Received AppService support refs and validation, application-return context/facts/admission/resolution, `_received` handoffs, received report sources/facts/resolution/validation, `received_form_references` | `host.store.db` with table `runtime_report_attempts`; `a106.communication:plain`; support `bvbrc_application_facts`, `form_reference_validation`, `bvbrc_appservice_custody/records/host`, `execution_contracts` |
| `report_delivery.py` | 33 | Closing form from facts and interpretations, saved once | `w.source_credit_view, w.pending_handles, w.episode_bindings.current_report_facts, w.binding_context, w.release(2), w.journal.row/save` (`runtime_forms`), `w.facts`; `a106.runtime:Record, _json, form_with_facts, json`; `bind_functions`; `a106 import runtime` |
| `task.py` | 218 | Decision loop, admission of selections and reports, execution with credit (see above) | `w.journal(7), w.inprocess_replay(4), w.execution_binding(7), w.completions(3), w.completed_unit(3), w.selected(3), w.next_return, w.resolve_pending_deliveries, w.action_schema, w.delivery_resolution_inputs, w.decision_exchanges, w.permits_common_action, w.reasoning_action_schema, w.store(9), w.specialist(2), w.binding_context(2), w.resolver, w.validate_report, w.run_id(3), w.execute, w.pending_work, w.receive_native_outcome, w.receive_outcome, w.automatic_score_updates, w.last_observed_credit, w.source_credit_view, w.retain_shared_grading_results, w.controller_value(2), w.services`; tables `runtime_episodes, runtime_model_calls, runtime_actions`; 20 `a106.runtime` names (ActionFailure, ContractError, ContractInformationError, Draft202012Validator, EventTargetError, Mapping, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form); `a106.providers:ModelCallError`; `a106.episode_source_failure:record_source_failure`; `bind_functions` |
| `task_decision.py` | 374 | Model call freezing, decision exchange protocol, contract-information validation | `w.journal(3), w.contract_information_profile, w.validate_contract_information(5), w.numerical_contracts, w.decision_protocol(3), w.decision_exchanges(4), w.freeze_literature_numerical_contracts, w.freeze_contract_information, w.receipts(4), w.uses_received_record_context(2), w.provider(4), w.history_preview, w.store(2), w.services.decision_exchange_instructions, w.contract_information_reply, w.execute, w.run_id`; table `runtime_model_calls` (8); 32 `a106.runtime` names (see TSV); `bind_functions` |
| `task_instructions.py` | 26 | Instruction composition (see above) | `source.workflow.specialist, .binding_context, .permits_common_action(3), .knowledge, .launch_instructions, .native_event_information, .decision_protocol` |
| `task_state.py` | 114 | Source state, failure-to-outcome conversion, restore/checkpoint/effects | `w.context, w.grains, w.archive, w.store(2), w.run_id, w.journal(5), w.source_credit_view, w.controller_value, w.execution_binding(4), w.completions(4), w.inprocess_replay(7), w.recover_commissions, w.progress_provider(2)`; table `runtime_actions`; `a106.runtime:ActionLeaf, EFFECT_VERSION, Episode, Record, _json, _object, _plain, interpretation_schema, json`; `a106.episode_source_failure:record_source_failure`; `bind_functions` |
| `to_child_api_job_execution.py` | 29 | Prepare the `launch_api` commission (see above) | `w.store.validate_scope, w.expanded_contract_form, w.episode_bindings.for_child(2), w.binding_context(4), w.child_initial_report_input, w.specialist, w.available_child_roles, w.annotation_child_roles, w.services.capabilities, w.episode_bindings.entry_roles, w.launch_instructions.materialize, w.run_id`; `a106.runtime:ContractError, parse_json_object, validate_form, interpretation_schema` |
| `to_parent.py` | 115 | Application facts, fact sources, live facts, `required_return_sources` (handoff refs for a scientific parent), resolution, report validation against facts | `self.services` (3: `annotation_task_required`, `reference_in_context`); `a106.episode_bindings:reference_in_context`; support `bvbrc_application_facts`, `bvbrc_appservice_saved_results`, `execution_contracts`, `form_reference_validation` |
| `waiting.py` | 30 | Selected wait; suspension marker | `w.perform_selected_wait, w.execution_handle(2), w.execution_backend.set_suspension`; `a106.runtime:EventTargetError, _wait_target_feedback`; `bind_functions` |
| `yield_estimator.py` | 55 | Bounded remaining-request yield and exact-zero exhaustion (see above) | `a106.numerical:BoundedYieldController, NumericBand, YieldController, YieldEstimate, YieldParameters`; `a106.practical_yield:PracticalYieldEstimator` |

Every `bind_functions` file ends with `_bind_original_task_runtime_providers(vars(a106.runtime))`. This rebinds the methods
into the old runtime's globals. It is old-runner machinery and is not this episode's intent.
