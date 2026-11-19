# a106/perturbation_evidence/published_evidence_assessment/execution_result_acquisition — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/execution_result_acquisition/<file>`
(the 25 files directly in this folder; there is no `grading/` or `scoring/` subfolder and no child folders).
Class: `ExecutionEpisode` in `episode.py`. It mixes the same 13 responsibility classes as its siblings. Its decision source
is `OperationalTask`.
- `binding_path = 'perturbation_evidence/published_evidence_assessment/execution_result_acquisition'`
- `commissioning_parent = 'perturbation_evidence/published_evidence_assessment'`
- `roles = ('results',)` and `entry_roles = ('results',)`. The episode can be an entry.
- `replaces_default_instructions = True`. The constants are shared with its siblings, including
  `RESULTS_VERSION = 'execution_results_assignment_v1'` and
  `RESULTS_SCHEMA = obj({version: const RESULTS_VERSION, handoff_ref: non-empty string, selector: object})`.
- `credit_kind(role)` returns `'operational'` for `results` only.

## What this episode is for (its goal, in its own words)

`goal.py`:

> "Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. The scientific parent interprets
> the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this
> endpoint."

This is the **results** endpoint of A106's execution work. Given a handoff that was received earlier from an
execution_job_submission (or launch_api) child, and a selector naming which results to fetch, the episode reads job status
and the requested result files or pages through the original API service, one operation per turn. It keeps the native
bytes and scores, and returns acquired result records to the scientific parent, which interprets them.

## Task and instructions

- `task_instructions.py` is identical to its siblings. The goal replaces the base INSTRUCTIONS. The pending-delivery
  repair text, the **wait** text, the native-event text (when present), the launch-library text and the decision-exchange
  replacement are added.
- There is no reasoning commit requirement, because `reason` is not permitted.
- `task.py` is identical to `api_job_execution`'s copy: tool or wait only, with no reasoning branches. Each decision is one
  model call. Rejected selections become typed feedback. Every executed tool or wait enters the iterator with its credit.
  `ActionFailure` is raised when no outcome is observed. `SourceEnd` is returned on a provider failure.

## What it reads from its parent's assignment

- `assignment_schema('results')` is a deep copy of `RESULTS_SCHEMA`: `{version, handoff_ref, selector}`.
- `prepare_assignment(parent, 'results', selection, scope, operation_key)` runs:
  - `checked` against the schema;
  - `_recorded_results_assignment(parent, selected, scope, operation_key)` (native_input_custody), which restores the
    assignment of an **original Results commission that already returned successfully**. It does so only when the parent
    has a receipt manifest, the admission is recorded, the child path is `('results', 'child_<index>')`, the child state is
    `yielded`, and the original action is `episode_child`/`results` with the same assignment and scope. Otherwise it
    returns None.
  - Otherwise `job_progress_provider.targets.read_target(handoff_ref, scope)` followed by `_selector(selected, target)`,
    which is `api_execution.validate_result_selector`.
- `_api_context(api, context)`, used by the host:
  - for role `results`, the assignment must have exactly `{version, handoff_ref, selector}` with
    `version == execution_results_assignment_v1`, otherwise `invalid_api_results_assignment`;
  - it returns `(target['assignment'], api.services[target['resource_id']], target)` after `read_target(...,
    verify_artifacts)` and `validate_result_selector`;
  - other roles get `standalone_api_context`.
- `initialize` and `catalog` re-validate the selector against `_target(context)`.
- `initial_references` returns `[handoff_ref]`, after `_target` succeeds. The original handoff is therefore this episode's
  initial known record.

## Children it may commission

None. This is a leaf, and there are no `to_child_*` or `from_child_*` files.

## Decision state and what it shows the model

- It has the same common decision frame as its siblings: identical `decision_state`, `decision_inputs` and
  `decision_presentation`, so it also receives the launch instruction library, completed action reports, pending work,
  execution expectations, estimates and waiting support.
- `internal_summary.decision_context` returns:
  - `execution_assignment`;
  - `execution_progress` (`facts`);
  - `execution_target = _target(context)`, the stored original handoff target;
  - `execution_target_description = job_progress_provider.targets.describe_target(handoff_ref, scope, selector=selector)`.
- Unlike `api_job_execution`, it does not include the host's own `decision_context` and has no `_api_decision_summary`.
- `initial_decision_context` holds the resource capabilities and inventory, as in its siblings.

## Tools it offers

`permitted_common_actions = ('tool', 'wait')`.
- `catalog(context)` re-validates the selector and returns `api_execution.catalog(context)`. The host's
  `_api_operation_catalog` returns `service.result_catalog(request, selector)` because a target exists. These are the
  service's real status and result read operations.
- `execute` first checks the tool name against the catalog, otherwise `execution_operation_not_available`. It then checks
  the arguments against the entry's `input_schema`, otherwise `invalid_execution_operation_arguments`. Only then does it call
  `api_execution.execute`. A `ValueError`/`TypeError` returns an `invalid` `_outcome`. This local pre-validation is
  absent from `api_job_execution`.
- `resource_tool_contracts()` publishes the `results` operation contracts with routes
  `{entry_role:'results', resource_id, resource_role:'results'}`.

## How its credit is counted

`credit.py`:
- The credit is `api_execution.credit_view`, through `_api_operational_credit` (identical to `api_job_execution`). It
  counts new unique handoff identities times `handoff_unit` plus new unique result identities times `acquired_record_unit`,
  relative to the initial references. Those include the original `handoff_ref`, so the handoff itself earns nothing here;
  acquired results do. The credit is unbounded.
- **Completion** (`_appservice_completion` with role `results`) is `host.publications.completion(context)`, which calls
  back `_appservice_publication_completion(publication, context)`:
  - For the selector adapters `('bvbrc_tnseq','1')` and `('bvbrc_rnaseq','1')` it authenticates custody, walks the own
    outcomes from the latest back, and takes the first one with a `publication_ref`. When that outcome has
    `result_record_refs`, the completion is the last one's `publication.completion_proof`; when it has none, the result is
    None. Otherwise the result is None.
  - Otherwise it uses the latest own published result that has a non-None `completion_proof`.
- Other roles use `standalone_appservice_completion`.
- `completion_for_action` and `verify_completion` delegate to the host, with the closed historical verdict checked first.
- The closed-credit snapshot is the same as in its siblings, with the carrier checking for `'results' in ROLES`.

## Continuation (yield estimator and settings)

`yield_estimator._results_yield_controller` requires `require_private_yield`. It works as follows:
- `assignment = checked(RESULTS_SCHEMA)`, `target = _target`, `selector = _selector`;
- `service = target.service or target.assignment.service`; a missing service raises
  `results_original_api_service_required_for_yield`;
- `key = 'results:api_' + service + ('_' + selector['version'] if present)`;
- `YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']),
  estimate_with_context=PracticalYieldEstimator(verify_completion))`.

This is a plain cutoff controller with the practical endpoint estimator: a verified complete acquisition gives an exact
zero forecast. In the new set it maps to **completion with a target**, the target being complete acquisition, or to
accumulation with the practical endpoint. This has to be decided when the episode is ported. The settings are the
per-(service, selector version) `cutoff` and `parameters`.

## What it reports to its parent

`to_parent.py`:
- `facts` and the host's `_appservice_report_facts` are identical to `api_job_execution`: handoff refs, support refs,
  `execution_result_refs = publications.own_results`, `execution_completed` and the application facts.
- `required_return_sources` returns `('execution_result_refs',)` when the parent's path ends in `perturbation_evidence` and
  `services.annotation_task_required()` holds. The scientific return must therefore carry the acquired results.
- `_application_resolve_reference` resolves its own references for the `results` role, and the application facts are
  validated against the **own** facts for role `results` (received_evidence).
- Resolve, validate and `report_delivery.finish` are the same as in its siblings.

## Configuration it is built with

The same `__init__` as its siblings. The `APIServiceExecution` callbacks are `credit_projector`, `report_facts`,
`completion_projector`, **`publication_completion=_appservice_publication_completion`**, `context_reader`,
`operation_catalog`, `application_return_owner`, `support_receipts` and `support_report_validator`. There is no
`decision_summary`.

## Differences from siblings

- Compared with **api_job_execution**:
  - Its assignment is a handoff and a selector, not a request.
  - Its catalog is the result catalog, not the launch catalog.
  - It validates tool names and arguments locally before the host call.
  - Its completion is publication-based, not TaskHandoff-based.
  - Its yield key is `results:api_<service>[_<selector version>]`.
  - It requires `execution_result_refs` in a scientific return.
  - It can be an entry, from the published-evidence-assessment parent.
  - Its initial references are the handoff.
  - It shows the model the target description instead of the host decision summary.
  - It has recorded-Results-commission restoration in `prepare_assignment`.
- Compared with **execution_job_submission**:
  - It has no child, no reason/child/redeliver actions and no bounded remaining-request yield.
  - Its credit counts acquired results, not only handoffs.

## File by file

Old-runner names use `w.` for `self.workflow.`. Counts are occurrences per file and are listed in
`runs/carry_over/calls/a106_04.tsv`. "Same as api_job_execution" means identical except for the docstring and module path.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `binding_record.py` | 8 | Binding record with this path as `binding_id` | — |
| `configuration.py` | 92 | As its siblings, with the `publication_completion` callback and no decision summary | `a106.numerical:YieldController, YieldParameters`; `self.services`; support `api_service_execution`, `execution_progress`, `retained_input_authority.*` |
| `credit.py` | 252 | `_appservice_completion` through publications, `_appservice_publication_completion` (TnSeq/RNA-seq adapter rule), identity credit, closed credit | `self.store.db` (8); tables `runtime_episodes, runtime_observations, runtime_receipt_inheritance, runtime_record_receipts, runtime_forms, runtime_actions`; `EpisodeReturnRecords, _same`; `EpisodeReceipts`; `a106.method_loop.identities:UnitRef`; `a106.numerical:NumericBand`; `a106.practical_yield:ESTIMATOR_VERSION`; `a106.domain:ContractError`; support `library.api_operational_credit`, `library.standalone_appservice_reports`; `context.as_record()` |
| `decision_inputs.py` | 71 | Same as siblings | `w.resource_context, w.shared_information_context, w.launch_instructions(2), w.available_child_roles, w.episode_bindings, w.binding_context, w.pending_work, w.execution_expectations, w.resource_estimator(4), w.native_estimation_context, w.permits_common_action, w.waiting_support`; `a106.runtime:child_option_information, Mapping`; `bind_functions` |
| `decision_presentation.py` | 51 | Same as siblings | `w.journal` (`runtime_actions`), `w.controller_binding`; `a106.runtime` (5 names); `episode_work_report:completed_action_reports`; `bind_functions` |
| `decision_state.py` | 78 | Same as siblings | Same 20 `w.*` members; `a106.runtime` (6 names); `bind_functions` |
| `episode.py` | 46 | Identity (entry role `results`), no children, actions `('tool','wait')`, hooks owned only for `results` | old hooks `context_hook_applies`, `decision_source_type`, `commissioning_parent` |
| `execution_contracts.py` | 26 | Same as siblings (`RESULTS_SCHEMA` lives here) | `a106.communication:plain, validate_form`; support `execution_contracts`, `launch_instructions`, `practical_execution_records`, `resource_records` |
| `execution_operations.py` | 57 | Result catalog through the host, `resource_tool_contracts` for `results`, local name/argument check before `api_execution.execute` | support `bvbrc_application_facts:application_fact_sources` |
| `execution_state.py` | 57 | `initialize` validates the selector against the target; `_target`; receiver selection; `_context_target` (results target must equal the assignment's) | `self.store.db` (4); tables `runtime_episodes, runtime_receipt_inheritance, runtime_actions`; `EpisodeReceipts`; `self.services.record_selection` |
| `from_parent.py` | 80 | `_api_context` for results; `RESULTS_SCHEMA` assignment; `prepare_assignment` with recorded restoration or target and selector; `initial_references = [handoff_ref]` | support `library.standalone_api_context` |
| `from_parent_launch.py` | 9 | The launch form (inherited copy; used by `_launch` in shared code paths) | — |
| `goal.py` | 9 | Goal text (quoted above) | — |
| `internal_summary.py` | 15 | Decision context adds `execution_target` and `execution_target_description` | — |
| `native_input_custody.py` | 229 | Same as siblings; `_recorded_results_assignment` is used by this episode | `self.store.db` (5); `runtime_report_attempts, runtime_episodes, runtime_actions`; `EpisodeReceipts, EpisodeReturnRecords`; support `execution_input_versions`, `retained_input_authority.*` |
| `received_evidence.py` | 173 | Same as siblings (the `results` role validates against its own facts) | `runtime_report_attempts`; `a106.communication:plain`; support AppService and application facts |
| `report_delivery.py` | 33 | Same as siblings | `w.source_credit_view, w.pending_handles, w.episode_bindings, w.binding_context, w.release(2), w.journal` (`runtime_forms`), `w.facts`; `a106.runtime:Record, _json, form_with_facts, json`; `bind_functions` |
| `task.py` | 199 | Same as api_job_execution (tool or wait loop) | As api_job_execution; 19 `a106.runtime` names; `a106.providers:ModelCallError`; `record_source_failure`; `bind_functions` |
| `task_decision.py` | 374 | Same as siblings | `w.journal, w.provider(4), w.decision_exchanges(4), w.validate_contract_information(5), w.receipts(4), ...`; `runtime_model_calls` (8); 32 `a106.runtime` names; `bind_functions` |
| `task_instructions.py` | 26 | Same as siblings | `source.workflow.specialist, .binding_context, .permits_common_action(3), .knowledge, .launch_instructions, .native_event_information, .decision_protocol` |
| `task_state.py` | 114 | Same as siblings | `w.context, w.grains, w.archive, w.journal(5), w.completions(4), w.inprocess_replay(7), w.execution_binding(4), w.recover_commissions, w.progress_provider(2), w.controller_value, w.source_credit_view, w.store, w.run_id`; `runtime_actions`; 9 `a106.runtime` names; `record_source_failure`; `bind_functions` |
| `to_parent.py` | 125 | As api_job_execution, but `required_return_sources` returns `('execution_result_refs',)` | `self.services`; `a106.episode_bindings:reference_in_context`; support `bvbrc_appservice_host`, `bvbrc_application_facts`, `bvbrc_appservice_saved_results`, `form_reference_validation` |
| `waiting.py` | 30 | Same as siblings | `w.perform_selected_wait, w.execution_handle(2), w.execution_backend`; `a106.runtime:EventTargetError, _wait_target_feedback`; `bind_functions` |
| `yield_estimator.py` | 43 | Plain controller with the practical estimator, keyed `results:api_<service>[_<selector version>]` | `a106.numerical:YieldController, YieldParameters`; `a106.practical_yield:PracticalYieldEstimator` |

## Carried over

Carried over on 19 November 2026 (final ten-file form). Library calls and the job service are named in `carry_over_blocked/a106__perturbation_evidence__published_evidence_assessment__execution_result_acquisition.md`. One row per old function, class or method of the files directly in the old episode folder (`runs/carry_over/functions/...tsv`).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | binding_record.py and the binding's own `as_record()` (README 3a, 3e) |
| binding_record.py | OperationalBindingRecord.as_record | machinery | binding_record.py and the binding's own `as_record()` (README 3a, 3e) |
| configuration.py | OperationalConfiguration | episode function | settings values -> `ctx.settings` / `settings` (`task_yield_profiles` in `yield_estimator.py`; `handoff_unit`, `acquired_record_unit`, `initial_information` in `task.py`); construction of `APIServiceExecution`, `ExecutionProgressProvider` and the retained input authorities -> unplaced (BLOCKED-ON-JOB-SERVICE, see blocked file) |
| configuration.py | OperationalConfiguration.__init__ | episode function | settings values -> `ctx.settings` / `settings` (`task_yield_profiles` in `yield_estimator.py`; `handoff_unit`, `acquired_record_unit`, `initial_information` in `task.py`); construction of `APIServiceExecution`, `ExecutionProgressProvider` and the retained input authorities -> unplaced (BLOCKED-ON-JOB-SERVICE, see blocked file) |
| credit.py | ExecutionEpisodeCredit | episode function | `credit.py credit` (class dissolved) |
| credit.py | ExecutionEpisodeCredit._appservice_completion | episode function | verified completion (TnSeq/RNA-seq adapter rule, latest published `completion_proof`) -> `execution_completed` of the job_access reply read by `task.py _outcome`; unplaced (BLOCKED-ON-JOB-SERVICE) |
| credit.py | ExecutionEpisodeCredit._appservice_publication_completion | episode function | verified completion (TnSeq/RNA-seq adapter rule, latest published `completion_proof`) -> `execution_completed` of the job_access reply read by `task.py _outcome`; unplaced (BLOCKED-ON-JOB-SERVICE) |
| credit.py | ExecutionEpisodeCredit._api_operational_credit | episode function | `credit.py credit` (identity credit from the tools' outcomes through the summary) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | single-role check (`results` only); no roles any more |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit snapshot over `runtime_episodes`/`runtime_observations`/`runtime_forms`/receipts (README 3e) |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit snapshot over `runtime_episodes`/`runtime_observations`/`runtime_forms`/receipts (README 3e) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit snapshot over `runtime_episodes`/`runtime_observations`/`runtime_forms`/receipts (README 3e) |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit snapshot over `runtime_episodes`/`runtime_observations`/`runtime_forms`/receipts (README 3e) |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit snapshot over `runtime_episodes`/`runtime_observations`/`runtime_forms`/receipts (README 3e) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | `credit.py credit` (identity credit from the tools' outcomes through the summary) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | `credit.py credit` (identity credit from the tools' outcomes through the summary) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | `credit.py credit` (identity credit from the tools' outcomes through the summary) |
| credit.py | ExecutionEpisodeCredit._proof_for_action | machinery | completion proof of the practical estimator over `runtime_actions`/`runtime_observations` (README 3d, 7b) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | machinery | completion proof of the practical estimator over `runtime_actions`/`runtime_observations` (README 3d, 7b) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | completion proof of the practical estimator over `runtime_actions`/`runtime_observations` (README 3d, 7b) |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | completion proof of the practical estimator over `runtime_actions`/`runtime_observations` (README 3d, 7b) |
| decision_inputs.py | OperationalDecisionInputs | episode function | class dissolved into the files its methods are placed in |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | `task.py _context` (instruction library, tool knowledge, time, yields, last outcome); launch_instructions/resource/estimate/pending/waiting pieces -> unplaced (see blocked file) |
| decision_inputs.py | _a106_original_global_ValueError | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_inputs.py | _a106_original_global_child_option_information | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_inputs.py | _a106_original_global_set | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_presentation.py | present_credit_state | episode function | unplaced: presentation of root axis credit / completed-work reports of the old shared root (see blocked file) |
| decision_presentation.py | prepare_completed_work | episode function | unplaced: presentation of root axis credit / completed-work reports of the old shared root (see blocked file) |
| decision_presentation.py | decision_yield_table | episode function | `messages/internal_summary.py` `yield_table(...)` as `action_yields` (library `records/progress_views.py`) |
| decision_presentation.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | OperationalDecisionState | episode function | `messages/internal_summary.py internal_summary` and `task.py _context` |
| decision_state.py | OperationalDecisionState.decision_state | episode function | `messages/internal_summary.py internal_summary` and `task.py _context` |
| decision_state.py | _a106_original_global_FACT_MEANINGS | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_FACT_SOURCES | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_Mapping | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global__references_in | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_callable | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_getattr | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_isinstance | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_json | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _a106_original_global_sorted | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| decision_state.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| episode.py | ExecutionEpisode | episode function | `episode.py ExecutionResultAcquisition` |
| episode.py | ExecutionEpisode.child_roles | episode function | `task.py CHILD_SLOTS = {}` |
| episode.py | ExecutionEpisode.allowed_children | episode function | `task.py CHILD_SLOTS = {}` |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | `task.py OFFERED` tools (`api_result_operation`, `wait_for_service_job`, lookups) |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | old hook `context_hook_applies` |
| execution_contracts.py | launch_operation_catalog | episode function | unplaced: `execution.capabilities` catalog entry of the launch role, not of results (see blocked file) |
| execution_contracts.py | _outcome | episode function | `task.py _invalid` (the invalid outcome of a refused selection) |
| execution_operations.py | OperationalOperations | episode function | class dissolved into `task.py` tools |
| execution_operations.py | OperationalOperations._api_operation_catalog | episode function | `task.py result_catalog` (`job_access.api_result_catalog`) |
| execution_operations.py | OperationalOperations._resource_information | episode function | `task.py result_catalog` (`job_access.api_capabilities`) |
| execution_operations.py | OperationalOperations.capabilities | episode function | `task.py result_catalog` (`job_access.api_capabilities`) |
| execution_operations.py | OperationalOperations.resource_tool_contracts | episode function | unplaced: invocation-route contracts for the commissioning parent (see blocked file) |
| execution_operations.py | OperationalOperations.catalog | episode function | `task.py result_catalog` |
| execution_operations.py | OperationalOperations.execute | episode function | `task.py api_result_operation` (name and argument check, then `job_access.api_result_operation`) |
| execution_operations.py | OperationalOperations._appservice_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (fact sources) |
| execution_state.py | OperationalExecutionState | episode function | class dissolved |
| execution_state.py | OperationalExecutionState.initialize | episode function | `task.py result_catalog` (the selector is validated against the target by the service) |
| execution_state.py | OperationalExecutionState._check_parent_inputs | machinery | check of the launch assignment behind the handoff over `runtime_episodes` (a commission check; README 5 item 3 removed) |
| execution_state.py | OperationalExecutionState._target | episode function | `task.py handoff_target` (BLOCKED-ON-JOB-SERVICE, raises) |
| execution_state.py | OperationalExecutionState._selection | machinery | receiver selection over `runtime_receipt_inheritance`/`runtime_actions`/`EpisodeReceipts` and `record_selection` (README 3c, 3e F1) |
| execution_state.py | OperationalExecutionState._context_target | machinery | target/assignment re-check against the old context (a commission check) |
| from_parent.py | OperationalAssignment | episode function | class dissolved |
| from_parent.py | OperationalAssignment._api_context | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM`, `read_from_parent` |
| from_parent.py | OperationalAssignment.child_assignment_schema | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM`, `read_from_parent` |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM`, `read_from_parent` |
| from_parent.py | OperationalAssignment._permitted | episode function | unplaced: launch-role request validation (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`), not used by the results role (see blocked file) |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | `messages/read_from_parent.py read_from_parent`; the restoration of a recorded commission and the target read are machinery / a commission check |
| from_parent.py | OperationalAssignment._request_schema | episode function | unplaced: launch-role request validation (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`), not used by the results role (see blocked file) |
| from_parent.py | OperationalAssignment._validate_request | episode function | unplaced: launch-role request validation (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`), not used by the results role (see blocked file) |
| from_parent.py | OperationalAssignment._launch | episode function | unplaced: launch-role request validation (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`), not used by the results role (see blocked file) |
| from_parent.py | OperationalAssignment._constraints | episode function | unplaced: launch-role request validation (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`), not used by the results role (see blocked file) |
| from_parent.py | OperationalAssignment.initial_references | episode function | `messages/read_from_parent.py` (`handoff_ref` in the parent input) and `credit.py` (handoff identity earns nothing) |
| from_parent_launch.py | LaunchParentAssignment | episode function | unplaced: launch-role assignment schema copy, not used by the results role (see blocked file) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | episode function | unplaced: launch-role assignment schema copy, not used by the results role (see blocked file) |
| goal.py | OperationalGoal | episode function | `goal.py GOAL` |
| goal.py | OperationalGoal.instructions | episode function | `goal.py GOAL` |
| internal_summary.py | OperationalSummary | episode function | `messages/internal_summary.py internal_summary` |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | `messages/internal_summary.py internal_summary` |
| internal_summary.py | OperationalSummary.decision_context | episode function | `messages/internal_summary.py internal_summary` |
| native_input_custody.py | NativeInputCustody | episode function | class dissolved |
| native_input_custody.py | NativeInputCustody._versions | episode function | unplaced: native input-version re-validation (see blocked file) |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | machinery | restoration of a recorded original Results commission over runtime tables and receipts (README 3e) |
| native_input_custody.py | NativeInputCustody._selector | episode function | `task.py result_catalog` (service validates the selector: `api_execution.validate_result_selector`; BLOCKED-ON-JOB-SERVICE) |
| native_input_custody.py | NativeInputCustody._protein_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._atac_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._atac_inputs | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | episode function | unplaced: native retained-input authority (protein, ATAC, chromatin, flux balance, fluorescence, NMF), not reached by the API results role (see blocked file) |
| native_input_custody.py | NativeInputCustody._selected_result_action | machinery | reads `runtime_actions` (README 3e F6) |
| received_evidence.py | ReceivedOperationalEvidence | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._appservice_received_support_refs | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._appservice_validate_received_report | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._application_received_context | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._application_received_facts | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._application_validate_received_report | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._application_record_admission | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._application_resolve_received | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | received-report admission and re-validation over `runtime_report_attempts` and the old publications; the system admits the result against `RETURN_FORM` (README 3b R1, F5); the parent reads it in its own `read_from_child` |
| report_delivery.py | OperationalReportDelivery | machinery | `finish`: saving the form, `form_with_facts`, `release` (README 3b D1, D3) |
| report_delivery.py | OperationalReportDelivery.finish | machinery | `finish`: saving the form, `form_with_facts`, `release` (README 3b D1, D3) |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task.py | OperationalTask | episode function | class dissolved into `task.py decide`/`action`/tools |
| task.py | OperationalTask.instructions | episode function | `task.py _instructions` |
| task.py | OperationalTask.next | episode function | `task.py decide` (restore, replay, checkpoint, delivery and source-failure branches are machinery) |
| task.py | OperationalTask.apply_response | episode function | `task.py action` (the report-update validation and redelivery branches are machinery) |
| task.py | OperationalTask.execute | episode function | `task.py` tools `api_result_operation`, `wait_for_service_job` (journal rows, receive_outcome, automatic score updates, checkpoint are machinery) |
| task.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | OperationalTaskDecision | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.call | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_schema | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | decision exchange, saved-request checks, conversation state and model-call recording (README 3a) |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_OSError | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_TypeError | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_ValidationError | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_ValueError | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global__action_generation_schema | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global__json | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global__plain | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_child_option_information | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_instructional_model_context | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_isinstance | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_len | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_lookup_attempts | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_model_snapshot | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_requested_contract_information | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_schema_failure_diagnostic | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_sqlite3 | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_state_frame | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_str | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _a106_original_global_type | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_decision.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| task_instructions.py | instructions | episode function | `task.py _instructions` (goal text, tool knowledge and launch instruction texts; pending-delivery, wait-handle, native-event and decision-exchange texts describe removed actions) |
| task_state.py | OperationalTaskState | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.__init__ | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.restore | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.record_effect | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | OperationalTaskState.checkpoint | machinery | task state restore/checkpoint/record_effect (README 3e F8) |
| task_state.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| to_parent.py | OperationalReport | episode function | class dissolved |
| to_parent.py | OperationalReport._application_facts | episode function | `task.py _outcome` facts (`reply['facts']`) and `final_to_parent` `bvbrc_application_outcomes`; the saved-adapter read (`read_latest_adapter_result`, `project_application_facts`) belongs to the job_access service (BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | OperationalReport._application_resolve_own | machinery | reference access of the report's references: custody is the system's (README 3b D2, F3) |
| to_parent.py | OperationalReport._application_resolve_reference | machinery | reference access of the report's references: custody is the system's (README 3b D2, F3) |
| to_parent.py | OperationalReport._appservice_report_facts | episode function | `messages/internal_summary.py facts_by_source` |
| to_parent.py | OperationalReport.required_return_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (`execution_result_refs` required) |
| to_parent.py | OperationalReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` |
| to_parent.py | OperationalReport.facts | episode function | `messages/final_to_parent.py final_to_parent` |
| to_parent.py | OperationalReport._live_facts | episode function | `messages/final_to_parent.py final_to_parent` |
| to_parent.py | OperationalReport.resolve | machinery | reference access of the report's references: custody is the system's (README 3b D2, F3) |
| to_parent.py | OperationalReport.validate_report | episode function | `messages/final_to_parent.py validate_report` |
| waiting.py | OperationalTaskWaiting | episode function | class dissolved |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | episode function | `task.py wait_for_service_job` |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | suspension/redelivery notification (README 3b) |
| waiting.py | _bind_original_task_runtime_providers | machinery | old runner provider patching (`_bind_original_task_runtime_providers` / `_a106_original_global_*` aliases of the old runtime module) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | class dissolved |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | unplaced: launch-role yield class of a request, not used by the results role (see blocked file) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | `yield_estimator.py task_yield_profile` |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | episode function | `yield_estimator.py yield_controller` and `yield_key` (accumulation; README 7b) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | `PracticalYieldEstimator` over a completion proof (README 7b) |
