# a106/perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution/<file>`
(the 25 files directly in this folder; there is no `grading/` or `scoring/` subfolder, and the episode has no child folders).
Class: `ExecutionEpisode` in `episode.py`. It mixes the same 13 responsibility classes as its parent, but without the child
preparer and receiver. Its decision source is `OperationalTask`.
- `binding_path = 'perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution'`
- `commissioning_parent = 'perturbation_evidence/published_evidence_assessment/execution_job_submission'`
- `roles = ('launch_api',)` and `entry_roles = ()`. The episode is **not** an entry; only the launch parent can commission it.
- `replaces_default_instructions = True`. The constants are shared with its siblings: `VERSION 'execution_episode_v1'`,
  `ROLES ('launch','launch_api','results')`, `KINDS {'api':'api'}`, `ROLE_KINDS {'launch_api':'api'}`.
- `credit_kind(role)` returns `'operational'` for `launch_api` only.

## What this episode is for (its goal, in its own words)

`goal.py`. The goal text is built from the assigned request: `assignment = _validate_request(context.assignment)` and
`service = assignment['service']`.

> "Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request,
> resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual
> available operations and received outcomes. Distinguish an immediate returned response from a service job that continues
> remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that
> no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured
> controller governs continuation; verified original handoff completion gives exact zero future credit."

This is the resource-level iterative executor for one API service request, such as a BV-BRC AppService job. Each turn it
picks one real service operation and executes it. It does this until it has a usable handoff: a recorded submitted job
identity that can be used to monitor it or fetch its results. The handoff goes back to the launch parent.

## Task and instructions

- `task_instructions.py` is identical to its siblings: the long base INSTRUCTIONS plus composition.
  `replaces_default_instructions` means the goal text above replaces the base text.
- The parts actually added for this episode are:
  - the pending-delivery repair text, which is always added;
  - the **wait** text, because `wait` is permitted;
  - the native-event text, when the old runner has `native_event_information`;
  - the launch instruction library text, because `decision_inputs` always supplies `launch_instruction_library`;
  - the decision-exchange history replacement.
- `REASONING_COMMIT_REQUIREMENT` is **not** added, because `reason` is not permitted.
- `task.py` is the same loop as its siblings, with the reasoning branches **removed**: `apply_response` validates only
  `schema.properties.selection`, and `execute` handles `wait` or a tool. The rest is the same as in its siblings:
  - Each decision is one model call.
  - Rejected selections become typed feedback.
  - Every executed tool or wait enters the iterator with its credit.
  - `ActionFailure` is raised when no outcome is observed.
  - `record_execution_failure` turns an exception into a failed outcome.
  - `SourceEnd('source_failed')` is returned on a provider error.

## What it reads from its parent's assignment

`from_parent.assignment_schema('launch_api')` is `{'anyOf': [request_schema(resource_id, selected=True) for each resource]}`,
or `{'not': {}}` when there are no resources.
- Each alternative is the concrete API request schema from `api_execution.assignment_schema(resource_id)` with
  `resource_id: const`. Here `resource_id` is **required** (`selected=True`).
- `prepare_assignment(parent, 'launch_api', selection, scope, key)` runs these checks:
  - `checked` against the schema;
  - `api_execution.validate_assignment(_validate_request(selected), scope=scope)`;
  - the parent's role must be `launch`, otherwise `resource_child_role_owned_by_launch`;
  - the parent's original launch assignment is re-admitted with `_launch(parent.assignment)`, and its
    `immutable_input_versions` are validated against the child scope.
- `_api_context(api, context)` is used by the API host:
  - the run must match;
  - for role `launch_api` it returns `(validated assignment, api.services[resource_id], None)`;
  - otherwise it returns `standalone_api_context(...)`.
- `initialize` and `execute` call `_check_parent_inputs`. When the parent path ends in `launch`, this reads the parent's
  recorded request from `runtime_episodes` and re-validates its immutable input versions. A missing parent raises
  `execution_original_launch_assignment_unavailable`. `initialize` then calls `api_execution.initialize(context)`.
- `initial_references` is empty.

## Children it may commission

None. `child_roles` and `allowed_children` return `()`, and there is no `to_child_*` or `from_child_*` file. This is a leaf.

## Decision state and what it shows the model

- It has the same common decision frame as its siblings (`decision_state.py`, `decision_inputs.py`,
  `decision_presentation.py` are identical copies). Like its parent, it gets the launch instruction library, the selected
  pinned instructions, completed action reports, pending work, execution expectations, resource estimates, waiting support
  and the contract-information profile.
- `internal_summary.decision_context` adds `execution_assignment`, `execution_progress` and, in addition,
  `api_execution.decision_context(context, current_view)`.
- The API host calls back `_api_decision_summary(api, context)`, which returns:
  - `api_service`;
  - `api_request`, the assigned request;
  - `api_received_progress`, the latest event per name `{state, kind, facts, failure_code}`;
  - `api_execution_completed`.
- `initial_decision_context` is the same as in its parent: resource capabilities and initial inventory.

## Tools it offers

`permitted_common_actions = ('tool', 'wait')`.
- `catalog(context)` is `api_execution.catalog(context)`. The host calls back `_api_operation_catalog`, which returns
  `service.launch_catalog(request)`. Since there is no target, these are the service's real launch operations.
- `execute` runs `_check_parent_inputs` and then `api_execution.execute(context, tool_name, arguments, operation_key)`.
- `resource_tool_contracts()` publishes, for each resource, the `launch_api` operation contracts with
  `invocation_route {kind:'commission', routes:[{entry_role:'launch', resource_id, resource_role:'launch_api'}]}`. A name
  whose schemas conflict raises `execution_resource_operation_contract_conflict:<name>`. These contracts tell the
  scientific layer which tools can be reached by commissioning.

## How its credit is counted

`credit.py`:
- `project_credit` returns the frozen `_CLOSED_CREDIT` view when there is one, otherwise `api_execution.credit_view`. The
  host calls back `_api_operational_credit(api, context, receiver_selection)`, which works as follows:
  - `facts = api.facts(context, {})`.
  - `initial` must be a subset of `known`.
  - The old identities are taken from the initial references: handoffs as `(resource_id, execution_id)` and results as
    `api.result_identity`.
  - The new identities are the known `execution_handoff_refs` and `execution_result_refs` from the facts.
  - The credit is `operational_credit_from_identities(handoffs, old_handoffs, results, old_results, handoff_unit,
    acquired_record_unit)`: one unit per new unique handoff identity plus one unit per new unique result. It is unbounded.
- **Completion**:
  - `_appservice_completion(host, context)`: for role `launch_api` it takes the latest own `TaskHandoff` receipt, verifies
    it with `read_handoff`, and returns `practical_completion_v1` with `endpoint 'usable_handoff'`, the operation_key from
    the receipt origin and `receipt_sha256`. For any other role it returns `standalone_appservice_completion`.
  - `completion_for_action` and `verify_completion` delegate to `api_execution`. `verify_completion` first checks the
    closed historical verdict.
- The closed-credit snapshot and authentication code is the same as in its parent, with the carrier checking for
  `'launch_api' in ROLES`.

## Continuation (yield estimator and settings)

`yield_estimator._launch_api_yield_controller` requires `require_private_yield`. It builds:
- `profile = task_yield_profiles['launch_api:' + _request_yield_class(request)]`, where the class is
  `api_<service>[_<algorithm>][_<database>]_handoff`;
- `YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']),
  estimate_with_context=PracticalYieldEstimator(verify_completion))`.

This is the old plain **accumulation** controller with a cutoff, whose estimate is the practical endpoint estimator. A
verified completion proof gives an exact zero forecast. In the new set it maps to **completion with a target**, the target
being a verified usable handoff, or to accumulation with the practical endpoint. This choice has to be made when the
episode is ported. The settings are the per-class `cutoff` and `parameters`.

## What it reports to its parent

`to_parent.py`:
- The fact sources are the same as in its parent: application facts, `bvbrc_appservice_support_refs`,
  `execution_handoff_refs`, `execution_result_refs` and `execution_completed`.
- `facts = api_execution.facts(context, completion_snapshot)`, plus the closed-credit facts. The host calls back
  `_appservice_report_facts(host, context)`, which builds:
  - from the own receipts: `execution_handoff_refs` (`TaskHandoff` contracts) and `bvbrc_appservice_support_refs`
    (other contracts);
  - `execution_result_refs = host.publications.own_results`;
  - `execution_completed`;
  - the application-return facts, merged in. An overlap raises `appservice_own_fact_source_conflict`.
- `required_return_sources` returns `()`. The branch is `pass`: unlike its parent, it never forces handoff refs.
- `resolve` and `validate_report` are the same as in its parent.
- `report_delivery.finish` is the same as in its parent.

## Configuration it is built with

The same `__init__` signature and validation as its parent. The `APIServiceExecution` is built with additional callbacks:
`credit_projector=_api_operational_credit`, `decision_summary=_api_decision_summary`, `report_facts=_appservice_report_facts`,
`completion_projector=_appservice_completion`, `context_reader=_api_context` and `operation_catalog=_api_operation_catalog`.
The other three are shared with its siblings: `application_return_owner`, `support_receipts` and `support_report_validator`.

## Differences from siblings

- Compared with **execution_job_submission** (its parent):
  - This episode is the only one that actually calls the service: its catalog is the real launch operations.
  - It is a leaf and cannot be an entry.
  - It has no reason, child or redeliver actions.
  - Its credit counts handoff and result identities through the API host.
  - Its yield is a plain controller with the practical estimator; the parent's is bounded remaining-request.
  - Its goal text is parameterised by the service name.
  - It never requires `execution_handoff_refs` from a return.
  - It checks the parent's inputs at runtime from `runtime_episodes`.
- Compared with **execution_result_acquisition**:
  - That sibling has the same plain controller and practical estimator, but keys it by
    `results:api_<service>[_<selector version>]`.
  - That sibling's catalog is `service.result_catalog(request, selector)` and its assignment is `RESULTS_SCHEMA`.
  - That sibling has a publication-based completion and requires `execution_result_refs`.

## File by file

Old-runner names use `w.` for `self.workflow.`. Counts are occurrences per file and are listed in
`runs/carry_over/calls/a106_04.tsv`. "Same as parent" means the file is identical to the one in
`execution_job_submission` except for the docstring and module path.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `binding_record.py` | 8 | Binding record with this path as `binding_id` | — |
| `configuration.py` | 92 | As parent, plus the host callbacks for credit, summary, report facts, completion, context and catalog | `a106.numerical:YieldController, YieldParameters`; `self.services`; support `api_service_execution`, `execution_progress`, `library.retained_input_authority.*` |
| `credit.py` | 239 | `_appservice_completion` (latest own TaskHandoff), `_api_operational_credit` (identity-based units), closed-credit snapshot, delegated completion and verification | `self.store.db` (8); tables `runtime_episodes, runtime_observations, runtime_receipt_inheritance, runtime_record_receipts, runtime_forms, runtime_actions`; `a106.episode_return_records:EpisodeReturnRecords, _same`; `a106.episode_receipts:EpisodeReceipts`; `a106.method_loop.identities:UnitRef`; `a106.numerical:NumericBand`; `a106.practical_yield:ESTIMATOR_VERSION`; `a106.domain:ContractError`; support `library.api_operational_credit`, `library.standalone_appservice_reports`; `context.as_record()` |
| `decision_inputs.py` | 71 | Same as parent | `w.resource_context, w.shared_information_context, w.launch_instructions(2), w.available_child_roles, w.episode_bindings, w.binding_context, w.pending_work, w.execution_expectations, w.resource_estimator(4), w.native_estimation_context, w.permits_common_action, w.waiting_support`; `a106.runtime:child_option_information, Mapping`; `bind_functions` |
| `decision_presentation.py` | 51 | Same as parent | `w.journal` (`runtime_actions`), `w.controller_binding`; `a106.runtime` (5 names); `a106.episode_work_report:completed_action_reports`; `bind_functions` |
| `decision_state.py` | 78 | Same as parent (common frame) | Same 20 `w.*` members as parent; `a106.runtime:FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json`; `bind_functions` |
| `episode.py` | 46 | Identity, no children, actions `('tool','wait')`, owns hooks only for the `launch_api` role (returns False for foreign roles) | old hooks `context_hook_applies`, `decision_source_type`, `commissioning_parent` |
| `execution_contracts.py` | 26 | Same as parent | `a106.communication:plain, validate_form`; support `execution_contracts`, `launch_instructions`, `practical_execution_records`, `resource_records` |
| `execution_operations.py` | 50 | `_api_operation_catalog` (launch catalog), capabilities, `resource_tool_contracts` (commission routes), catalog and execute through the host | support `library.bvbrc_application_facts:application_fact_sources` |
| `execution_state.py` | 57 | `initialize` runs `_check_parent_inputs` and then `api_execution.initialize`; receiver selection; `_context_target` | `self.store.db` (4); tables `runtime_episodes, runtime_receipt_inheritance, runtime_actions`; `a106.episode_receipts:EpisodeReceipts`; `self.services.record_selection` |
| `from_parent.py` | 76 | `_api_context`; `anyOf` selected-request schema; `prepare_assignment` (parent must be `launch`, re-admits the original launch and versions); request validation | support `library.standalone_api_context` |
| `from_parent_launch.py` | 9 | The parent's original launch form (used to re-admit the parent) | — |
| `goal.py` | 11 | Service-parameterised goal (quoted above) | — |
| `internal_summary.py` | 22 | `_api_decision_summary`; decision context adds the host's decision context | — |
| `native_input_custody.py` | 229 | Same as parent | `self.store.db` (5); tables `runtime_report_attempts, runtime_episodes, runtime_actions`; `EpisodeReceipts`, `EpisodeReturnRecords`; support `execution_input_versions`, `retained_input_authority.*` |
| `received_evidence.py` | 173 | Same as parent | `runtime_report_attempts`; `a106.communication:plain`; support AppService and application facts |
| `report_delivery.py` | 33 | Same as parent | `w.source_credit_view, w.pending_handles, w.episode_bindings, w.binding_context, w.release(2), w.journal` (`runtime_forms`), `w.facts`; `a106.runtime:Record, _json, form_with_facts, json`; `bind_functions` |
| `task.py` | 199 | Loop without reasoning: tool or wait only | Parent's set minus the reasoning members (`reasoning_action_schema, specialist, binding_context` and the `store.commit_reasoning` / `reasoning_schema` calls); 19 `a106.runtime` names (no `Mapping`); `a106.providers:ModelCallError`; `episode_source_failure:record_source_failure`; `bind_functions` |
| `task_decision.py` | 374 | Same as parent | Same as parent: `w.journal, w.provider(4), w.decision_exchanges(4), w.validate_contract_information(5), w.receipts(4), ...`; `runtime_model_calls` (8); 32 `a106.runtime` names; `bind_functions` |
| `task_instructions.py` | 26 | Same as parent | `source.workflow.specialist, .binding_context, .permits_common_action(3), .knowledge, .launch_instructions, .native_event_information, .decision_protocol` |
| `task_state.py` | 114 | Same as parent | `w.context, w.grains, w.archive, w.journal(5), w.completions(4), w.inprocess_replay(7), w.execution_binding(4), w.recover_commissions, w.progress_provider(2), w.controller_value, w.source_credit_view, w.store, w.run_id`; `runtime_actions`; 9 `a106.runtime` names; `record_source_failure`; `bind_functions` |
| `to_parent.py` | 125 | `_appservice_report_facts`; facts delegated to the host; `required_return_sources` returns `()`; resolve and validate | `self.services`; `a106.episode_bindings:reference_in_context`; support `bvbrc_appservice_host:SUPPORT_SOURCE`, `bvbrc_application_facts`, `bvbrc_appservice_saved_results`, `form_reference_validation` |
| `waiting.py` | 30 | Same as parent | `w.perform_selected_wait, w.execution_handle(2), w.execution_backend`; `a106.runtime:EventTargetError, _wait_target_feedback`; `bind_functions` |
| `yield_estimator.py` | 37 | Plain controller with the practical estimator, keyed `launch_api:<class>` | `a106.numerical:YieldController, YieldParameters`; `a106.practical_yield:PracticalYieldEstimator` |
