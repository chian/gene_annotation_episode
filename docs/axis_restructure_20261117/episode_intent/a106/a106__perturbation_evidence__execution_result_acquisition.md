# a106 / perturbation_evidence / execution_result_acquisition

Source: this episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_result_acquisition/<file>`).
`tests/` is not covered here. The old binding class is `ExecutionEpisode`. Its decision source is `OperationalTask`.
It has no grading/ or scoring/ folder.

## Purpose (goal, in its own words)

Role `results` (also its only entry role). `goal.py`, with `replaces_default_instructions = True`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. The scientific parent
> interprets the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition
> establishes this endpoint.

This is an operational (non-scientific) episode. It fetches what an already launched job produced and gives the
records back. Interpreting them is the parent's job.

## Task and instructions

- The goal text replaces the default literature/scientific prompt (`replaces_default_instructions`). The composer
  (`task_instructions.py`, the same text as the other operational episodes) then adds tool knowledge, the
  launch-instruction library, guidance for repairing a pending child delivery, wait guidance (only when wait is
  permitted, which it always is here) and native-event guidance (only when the runner has an event provider). It also
  adds the exchange-protocol history note.
- `task.py` is the generic operational loop. Its only actions are `tool` and `wait`. It has **no `reason` branch**,
  unlike its sibling `perturbation_evidence/execution_job_submission`, whose `task.py` adds reason handling (empty
  commit check, `execute_reasoning`, `commit_reasoning`).
- `task_decision.py` calls the provider directly (`provider.complete(... 'REASONING' ...)`). It does not use the
  literature prompt renderer.

## What it reads from its parent's assignment

- Parent: `perturbation_evidence` (`commissioning_parent`). It is commissioned as role `results`.
- Assignment `execution_results_assignment_v1` = `{version, handoff_ref, selector}` (`RESULTS_SCHEMA`). Nothing else
  is admitted (`_api_context` rejects other keys).
- `prepare_assignment`:
  1. restores an already returned original Results commission (`native_input_custody._recorded_results_assignment`).
     This happens only after it authenticates the receipt manifest, the admission index, the yielded child, and the
     original action, assignment and scope;
  2. otherwise reads the handoff target through the progress provider and validates the selector against it.
- `initial_references` = `[handoff_ref]`.
- `execution_state._check_parent_inputs`: when the parent is a `launch` episode, it re-reads that launch's original
  assignment and verifies its immutable input versions.
- `from_parent_launch.py` keeps the original Launch form schema, so that the launch can be admitted independently.

## Children

None. `child_roles` and `allowed_children` return `()`. `permitted_common_actions` = `('tool', 'wait')`.

## Decision state and what the model sees

- Generic decision state (`decision_state.py` / `decision_presentation.present_credit_state`): goal, scope, working
  state, visible record refs, current credit and evidence vector, credit binding, time accounting, pending work, last
  outcome and feedback, visual evidence, delivery status, controller state, tool catalog, tool knowledge, job episode
  options, available report facts, requested form and current report update.
- The episode's own part (`internal_summary.py`):
  - at start: `execution_resource_capabilities` (one entry per bound resource: id, kind `api`, availability,
    tool names, service, base_url, inventory snapshot) and `execution_initial_information`;
  - at every decision: `execution_assignment`, `execution_progress` (its own facts), `execution_target`, and
    `execution_target_description` for the selector.

## Tools it offers

- The API execution engine's catalog for the results role: `service.result_catalog(request, selector)` for the
  original handoff (`execution_operations.catalog`).
- `execute` accepts only tools in that catalog and validates the arguments against the tool's input schema. A
  `ValueError` or `TypeError` becomes an `invalid` outcome with feedback `arguments_or_reference`, and that outcome
  enters the iterator.
- `resource_tool_contracts` publishes the per-resource results operation contracts with commission routes.

## Credit

- Kind `operational` (`credit_kind`).
- Live credit is `api_execution.credit_view` → `operational_credit_from_identities`: (new usable handoffs ×
  `handoff_unit`) + (new acquired result identities × `acquired_record_unit`). Handoffs or results already known at
  start (`initial_known_record_refs`) earn nothing. Both units are explicit, positive and finite. Nothing is bounded.
- Closed credit: on finish, the projected view is pinned into the saved facts (`execution_closed_operational_credit_v1`)
  together with digests of the context, binding, completion, archive, observation history and receipt prefix. After
  that, `project_credit` returns only this pinned view (“later delivery never reprices it”).
- Completion: a practical completion proof (`practical_completion_v1`) for an action whose outcome references a
  usable handoff. For TnSeq/RNASeq adapters, the completion is the latest publication's `completion_proof`.
  `verify_completion` first reuses a single recorded verification from history, then asks the API engine.

## Continuation

- Private yield only. `yield_controller` raises `execution_private_yield_binding_not_enabled` unless
  `require_private_yield=True`.
- Profile key `results:api_<service>[_<selector version>]` → `task_yield_profiles[key] = {cutoff, parameters}`.
  The profile must exist, `cutoff > 0`, and it is validated at construction.
- `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=
  PracticalYieldEstimator(verify_completion))`: the forecast becomes exact zero once an endpoint proof verifies.
- Mapping to the current three estimators: **completion with a target**. The target is verified acquisition; the
  settings are the profile's cutoff and parameters.

## What it reports to its parent

- Fact sources: `execution_handoff_refs`, `execution_result_refs`, `execution_completed` (true only with verified
  endpoint information; yielding alone is false), `bvbrc_appservice_support_refs`, plus the AppService application
  fact sources (`bvbrc_application_facts`).
- `required_return_sources`: when the parent is `perturbation_evidence` and an annotation task is required, the
  return form must carry `execution_result_refs` exactly once.
- `validate_report`: the form must resolve its references, and every fact-sourced field must equal the recorded facts
  (`execution_report_disagrees_with_recorded_facts`).
- `resolve` tries, in this order: FBA, fluorescence, NMF, ATAC, chromatin and protein native result access, then the
  API engine. Handoff sources do not resolve as results.
- `received_evidence.py` defines what the parent itself reads back (support refs, application facts, the admitted
  forms of the native families).

## Differences from similar episodes

- Compared with the sibling `perturbation_evidence/execution_job_submission`, the goal differs: launch chooses which
  permitted request to commission, and a usable handoff completes it. Its yield also differs: launch caps the next
  gain by the uncredited request slots (`BoundedYieldController` over eligible resources); results uses a practical
  completion estimator keyed by service/selector version. `from_parent` differs (launch admits a request map;
  results admits only `{handoff_ref, selector}`), and so does `execution_operations` (launch catalog versus result
  catalog). Results has no `reason` branch in `task.py`. Results' `credit.py` adds the closed-credit snapshot and
  the TnSeq/RNASeq publication completion.
- This episode is distinct from `published_evidence_assessment/execution_result_acquisition`, which has the binding
  path `.../published_evidence_assessment/execution_result_acquisition` and is commissioned by the literature
  episode. That one is not covered here.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `binding_record.py` | 8 | binding identity `perturbation_evidence/execution_result_acquisition` and its saved configuration: resources, initial_information, handoff_unit, acquired_record_unit, log window, log roles, require_private_yield, task_yield_profiles | none |
| `configuration.py` | 92 | constructor contract: explicit API resources only (`KINDS={'api':'api'}`), positive finite handoff/acquired-record credit units, explicit log window/roles, boolean private yield, per-task yield profiles `{cutoff>0, parameters}` validated up front; builds the API execution engine, the progress provider, and the native result/return readers (FBA, protein structure, fluorescence, expression NMF, ATAC, chromatin), each only when a resource asks for it | `import a106.api_service_execution`, `import a106.execution_progress`, `import a106.library.retained_input_authority` ×13, `import a106.numerical`, `YieldController` ×2, `YieldParameters` ×2 |
| `credit.py` | 252 | operational credit = new usable handoffs × handoff_unit + new acquired result identities × acquired_record_unit (initial known refs excluded); closed-credit snapshot carried in the final facts so later delivery never reprices it; TnSeq/RNASeq adapter publication completion; practical completion proof per action; completion verification that reuses a recorded verdict | `import a106.domain`, `import a106.episode_receipts`, `import a106.episode_return_records` ×4, `import a106.library.api_operational_credit`, `import a106.library.standalone_appservice_reports`, `import a106.method_loop.identities`, `import a106.numerical`, `import a106.practical_yield`, `runtime_actions`, `runtime_episodes` ×2, `runtime_forms` ×3, `runtime_observations` ×2, `runtime_receipt_inheritance` ×2, `runtime_record_receipts` ×2 |
| `decision_inputs.py` | 71 | generic runner input assembly (resource context, launch instructions, child options, initial binding context, pending work, execution/native estimates, waiting support); no episode-specific content | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.execution_expectations`, `workflow.launch_instructions` ×2, `workflow.native_estimation_context`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.resource_context`, `workflow.resource_estimator` ×4, `workflow.shared_information_context`, `workflow.waiting_support` |
| `decision_presentation.py` | 51 | generic presentation of the credit state, completed-work reports and the yield table; no episode-specific content | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_work_report`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×5, `runtime_actions`, `workflow.controller_binding`, `workflow.journal` |
| `decision_state.py` | 78 | generic decision state the model sees (goal, scope, working state, visible refs, credit, tools, pending work, report form); no episode-specific content | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions`, `workflow.binding_context`, `workflow.catalog`, `workflow.controller_binding`, `workflow.delivery_status`, `workflow.extra_report_sources`, `workflow.job_episode_options`, `workflow.journal` ×2, `workflow.knowledge`, `workflow.local_outcome_preview`, `workflow.pending_work`, `workflow.receipt_projection`, `workflow.run_id`, `workflow.source_credit_binding`, `workflow.source_credit_view`, `workflow.specialist`, `workflow.store` ×3, `workflow.tools`, `workflow.working_state` |
| `episode.py` | 46 | assembles the binding; roles `('results',)`, entry role `results`, `replaces_default_instructions = True`, no children, common actions only `tool` and `wait` (no `reason`, no `child`) | none |
| `execution_contracts.py` | 26 | versions (`execution_episode_v1`, `execution_results_assignment_v1`), roles, results assignment schema `{version, handoff_ref, selector}`, launch capability catalog, outcome shape for invalid arguments | `import a106.communication`, `import a106.execution_contracts`, `import a106.launch_instructions`, `import a106.practical_execution_records`, `import a106.resource_records` |
| `execution_operations.py` | 57 | tools: the API execution catalog for the results selector (`service.result_catalog`); execute validates arguments against the catalog and turns ValueError/TypeError into an invalid outcome; resource information/capabilities; AppService fact sources incl. `bvbrc_appservice_support_refs` | `import a106.library.bvbrc_application_facts` |
| `execution_state.py` | 57 | initialize validates selector against the handoff target; checks the parent's original launch inputs; reads the handoff target; known/initial record selection (receipts or own actions); target-conflict checks per role | `import a106.episode_receipts`, `runtime_actions`, `runtime_episodes`, `runtime_receipt_inheritance` ×2 |
| `from_parent_launch.py` | 9 | schema of the original parent Launch form (requests per resource, immutable input versions, constraints, launch_instructions), used to admit the original launch | none |
| `from_parent.py` | 80 | reads the parent assignment `execution_results_assignment_v1 {handoff_ref, selector}`; prepare_assignment restores an already returned commission or validates the selector against the handoff target; initial_references = the handoff_ref | `import a106.library.standalone_api_context` |
| `goal.py` | 9 | the goal text (see Purpose) | none |
| `__init__.py` | 0 | empty package marker | none |
| `internal_summary.py` | 15 | initial context: resource capabilities and initial inventory; decision context: assignment, execution progress facts, handoff target and its description for the selector | none |
| `native_input_custody.py` | 229 | restores a previously returned Results commission only after authenticating receipts and the original child/action/assignment/scope; guarded reference access for protein, ATAC, chromatin, FBA, fluorescence and NMF native results (a protected denial never falls through); native input readers | `import a106.episode_receipts`, `import a106.episode_return_records`, `import a106.execution_contracts`, `import a106.execution_input_versions`, `import a106.library.retained_input_authority` ×7, `runtime_actions` ×2, `runtime_episodes`, `runtime_report_attempts` |
| `received_evidence.py` | 173 | what the parent reads from this child's return: AppService support refs, application return facts, received reference resolution and form admission for the native result families | `import a106.bvbrc_appservice_custody`, `import a106.bvbrc_appservice_host`, `import a106.bvbrc_appservice_records`, `import a106.communication`, `import a106.execution_contracts` ×2, `import a106.form_reference_validation`, `import a106.library.bvbrc_application_facts` ×2, `runtime_report_attempts` |
| `report_delivery.py` | 33 | generic finish: saves form with facts and releases the episode | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_forms` ×2, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.facts`, `workflow.journal` ×2, `workflow.pending_handles`, `workflow.release` ×2, `workflow.source_credit_view` |
| `task_decision.py` | 374 | generic model call and decision-exchange protocol; uses the plain provider complete (no literature prompt renderer) | `bind_functions` ×3, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×4, `runtime_model_calls` ×8, `services.decision_exchange_instructions`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.decision_exchanges` ×4, `workflow.decision_protocol` ×3, `workflow.execute`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.journal` ×3, `workflow.numerical_contracts`, `workflow.provider` ×4, `workflow.receipts` ×4, `workflow.run_id`, `workflow.services`, `workflow.store` ×2, `workflow.uses_received_record_context` ×2, `workflow.validate_contract_information` ×5 |
| `task_instructions.py` | 26 | generic composer (same text as other operational episodes); the goal replaces the default instructions; wait and native-event guidance added when wait is permitted | `workflow.binding_context`, `workflow.decision_protocol`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.permits_common_action` ×3, `workflow.specialist` |
| `task.py` | 199 | generic operational loop (next / apply_response / execute) with tool and wait only; no reason branch (sibling execution_job_submission has one) | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.providers`, `import a106.runtime` ×3, `runtime_actions` ×8, `runtime_episodes`, `runtime_model_calls` ×2, `services.instructions`, `workflow.action_schema`, `workflow.automatic_score_updates`, `workflow.completed_unit` ×3, `workflow.completions` ×3, `workflow.controller_value` ×2, `workflow.decision_exchanges` ×3, `workflow.delivery_resolution_inputs`, `workflow.execute`, `workflow.execution_binding` ×7, `workflow.inprocess_replay` ×4, `workflow.journal` ×7, `workflow.last_observed_credit`, `workflow.next_return`, `workflow.pending_work`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` ×2, `workflow.selected` ×3, `workflow.services`, `workflow.source_credit_view`, `workflow.store` ×7, `workflow.validate_report` |
| `task_state.py` | 114 | generic restore/checkpoint/failure recording | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions` ×5, `workflow.archive`, `workflow.completions` ×4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding` ×4, `workflow.grains`, `workflow.inprocess_replay` ×7, `workflow.journal` ×5, `workflow.progress_provider` ×2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store` ×2 |
| `to_parent.py` | 125 | report facts: `execution_handoff_refs`, `execution_result_refs`, `execution_completed` (+ AppService application facts); `required_return_sources` forces `execution_result_refs` when parent is `perturbation_evidence` and an annotation task is required; the report must equal the recorded facts; reference resolution through the native families then the API engine | `import a106.bvbrc_appservice_host`, `import a106.bvbrc_appservice_saved_results`, `import a106.episode_bindings`, `import a106.execution_contracts`, `import a106.form_reference_validation`, `import a106.library.bvbrc_application_facts` |
| `waiting.py` | 30 | generic selected wait; an EventTargetError becomes a failed outcome | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.execution_backend`, `workflow.execution_handle` ×2, `workflow.perform_selected_wait` |
| `yield_estimator.py` | 43 | private yield only (raises if not enabled); profile key `results:api_<service>[_<selector version>]`; controller with that profile's cutoff/parameters and a practical-completion estimator (exact zero once endpoint proof verifies) | `PracticalYieldEstimator` ×4, `import a106.numerical`, `import a106.practical_yield` ×2, `YieldController` ×2, `YieldParameters` ×2 |

## Carried over

Carried 19 November 2026 into the ten-file form (no children: no `msg_to_child.py`, no `read_from_child.py`). Private copy of the carried sibling `perturbation_evidence/published_evidence_assessment/execution_result_acquisition` shape, rewritten against this episode's old files at `97308b94c`. One row per old function (`runs/carry_over/functions/...tsv`). Class column: old kind. Machinery rows are not carried; "UNPLACED" rows are episode functions that could not be placed (see `carry_over_blocked/a106__perturbation_evidence__execution_result_acquisition.md`).

| old file | name | old kind | classification | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | OperationalBindingRecord | class | machinery | binding_record.py and as_record() are deleted (README 3e) |
| binding_record.py | OperationalBindingRecord.as_record | method | machinery | binding_record.py and as_record() are deleted (README 3e) |
| configuration.py | OperationalConfiguration | class | machinery | constructor of old providers and settings; the settings values are read from ctx.settings / settings (task.py, yield_estimator.py); engine and native readers construction unplaced (UNPLACED) |
| configuration.py | OperationalConfiguration.__init__ | method | machinery | constructor of old providers and settings; the settings values are read from ctx.settings / settings (task.py, yield_estimator.py); engine and native readers construction unplaced (UNPLACED) |
| credit.py | ExecutionEpisodeCredit | class | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._appservice_completion | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| credit.py | ExecutionEpisodeCredit._appservice_publication_completion | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| credit.py | ExecutionEpisodeCredit._api_operational_credit | method | episode function | credit.py credit (formula rebuilt over summary identities); library candidate: operational_credit_from_identities |
| credit.py | ExecutionEpisodeCredit.credit_kind | method | machinery | credit_kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | method | machinery | closed-credit snapshot over runtime_* tables and receipts (receipts bookkeeping, journal re-validation); the system pins the credit in completion |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | method | machinery | closed-credit snapshot over runtime_* tables and receipts (receipts bookkeeping, journal re-validation); the system pins the credit in completion |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | method | machinery | closed-credit snapshot over runtime_* tables and receipts (receipts bookkeeping, journal re-validation); the system pins the credit in completion |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | method | machinery | closed-credit snapshot over runtime_* tables and receipts (receipts bookkeeping, journal re-validation); the system pins the credit in completion |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | method | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.project_credit | method | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._live_project_credit | method | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_view | method | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._proof_for_action | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| credit.py | ExecutionEpisodeCredit.verify_completion | method | machinery | practical-completion proof and verification of the old estimator; not a controller input (README 3d, 5 item 5); the completion fact is the tool outcome execution_completed (UNPLACED reader) |
| decision_inputs.py | OperationalDecisionInputs | class | machinery | old runner input assembly, pending work, completed-work reports; deleted (README 3a) |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | method | machinery | old runner input assembly, pending work, completed-work reports; deleted (README 3a) |
| decision_inputs.py | _a106_original_global_ValueError | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_inputs.py | _a106_original_global_child_option_information | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_inputs.py | _a106_original_global_set | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_inputs.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_presentation.py | present_credit_state | function | episode function | task.py _context (action_yields via library records/progress_views.yield_table) and messages/internal_summary.py |
| decision_presentation.py | prepare_completed_work | function | machinery | old runner input assembly, pending work, completed-work reports; deleted (README 3a) |
| decision_presentation.py | decision_yield_table | function | episode function | task.py _context (action_yields via library records/progress_views.yield_table) and messages/internal_summary.py |
| decision_presentation.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | OperationalDecisionState | class | episode function | task.py _context (action_yields via library records/progress_views.yield_table) and messages/internal_summary.py |
| decision_state.py | OperationalDecisionState.decision_state | method | episode function | task.py _context (action_yields via library records/progress_views.yield_table) and messages/internal_summary.py |
| decision_state.py | _a106_original_global_FACT_MEANINGS | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_FACT_SOURCES | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_Mapping | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global__references_in | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_callable | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_getattr | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_isinstance | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_json | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _a106_original_global_sorted | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| decision_state.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| episode.py | ExecutionEpisode | class | episode function | episode.py ExecutionResultAcquisition |
| episode.py | ExecutionEpisode.child_roles | method | machinery | child roles: task.py CHILD_SLOTS = {}; hook applicability is old runner |
| episode.py | ExecutionEpisode.allowed_children | method | machinery | child roles: task.py CHILD_SLOTS = {}; hook applicability is old runner |
| episode.py | ExecutionEpisode.permitted_common_actions | method | episode function | task.py OFFERED tools (tool, wait -> wait_for_service_job) |
| episode.py | ExecutionEpisode.context_hook_applies | method | machinery | child roles: task.py CHILD_SLOTS = {}; hook applicability is old runner |
| execution_contracts.py | launch_operation_catalog | function | episode function | not carried: launch role operation, not results (UNPLACED) |
| execution_contracts.py | _outcome | function | episode function | task.py _invalid (the old _outcome(code=...)); library forms/perturbation_evidence/execution_contracts.py |
| execution_operations.py | OperationalOperations | class | episode function | task.py result_catalog / api_result_operation |
| execution_operations.py | OperationalOperations._api_operation_catalog | method | episode function | task.py result_catalog |
| execution_operations.py | OperationalOperations._resource_information | method | episode function | task.py result_catalog (capabilities, inventory snapshot) |
| execution_operations.py | OperationalOperations.capabilities | method | episode function | task.py result_catalog (capabilities, inventory snapshot) |
| execution_operations.py | OperationalOperations.resource_tool_contracts | method | episode function | not carried: parent-side route contracts (the parent text in its own task.py) (UNPLACED) |
| execution_operations.py | OperationalOperations.catalog | method | episode function | task.py result_catalog |
| execution_operations.py | OperationalOperations.execute | method | episode function | task.py api_result_operation |
| execution_operations.py | OperationalOperations._appservice_sources | method | episode function | messages/final_to_parent.py RETURN_FORM (fact-source fields); library application_fact_sources |
| execution_state.py | OperationalExecutionState | class | episode function | task.py handoff_target (BLOCKED-ON-JOB-SERVICE) |
| execution_state.py | OperationalExecutionState.initialize | method | machinery | old initialise; the selector is validated where the service is asked (task.py result_catalog) |
| execution_state.py | OperationalExecutionState._check_parent_inputs | method | machinery | receipts / runtime_* reads and check of a commission; custody is the system (README 3e F1, 3b C3) |
| execution_state.py | OperationalExecutionState._target | method | episode function | task.py handoff_target (BLOCKED-ON-JOB-SERVICE) |
| execution_state.py | OperationalExecutionState._selection | method | machinery | receipts / runtime_* reads and check of a commission; custody is the system (README 3e F1, 3b C3) |
| execution_state.py | OperationalExecutionState._context_target | method | episode function | task.py handoff_target (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | OperationalAssignment | class | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment._api_context | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | OperationalAssignment.child_assignment_schema | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | OperationalAssignment.assignment_schema | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | OperationalAssignment._permitted | method | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment.prepare_assignment | method | machinery | restore of a returned Results commission and selector check against the target; not carried (check of a commission) |
| from_parent.py | OperationalAssignment._request_schema | method | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment._validate_request | method | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment._launch | method | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment._constraints | method | episode function | not carried: launch-role request validation (UNPLACED) |
| from_parent.py | OperationalAssignment.initial_references | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent_launch.py | LaunchParentAssignment | class | episode function | not carried: launch-role schema (UNPLACED) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | method | episode function | not carried: launch-role schema (UNPLACED) |
| goal.py | OperationalGoal | class | episode function | goal.py GOAL |
| goal.py | OperationalGoal.instructions | method | episode function | goal.py GOAL |
| internal_summary.py | OperationalSummary | class | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | OperationalSummary.initial_decision_context | method | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | OperationalSummary.decision_context | method | episode function | messages/internal_summary.py internal_summary |
| native_input_custody.py | NativeInputCustody | class | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._versions | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | method | machinery | restore from receipts / runtime_* tables; custody is the system |
| native_input_custody.py | NativeInputCustody._selector | method | episode function | task.py api_result_operation (selector kept in the arguments; service validates it) |
| native_input_custody.py | NativeInputCustody._protein_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._atac_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._atac_inputs | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | method | episode function | not carried: native retained-input authority readers (UNPLACED) |
| native_input_custody.py | NativeInputCustody._selected_result_action | method | machinery | restore from receipts / runtime_* tables; custody is the system |
| received_evidence.py | ReceivedOperationalEvidence | class | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._appservice_received_support_refs | method | machinery | parent-side re-validation of received reports over runtime_report_attempts; custody and read_from_child are the system (README 3b R1) |
| received_evidence.py | ReceivedOperationalEvidence._appservice_validate_received_report | method | machinery | parent-side re-validation of received reports over runtime_report_attempts; custody and read_from_child are the system (README 3b R1) |
| received_evidence.py | ReceivedOperationalEvidence._application_received_context | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._application_received_facts | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._application_validate_received_report | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._application_record_admission | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._application_resolve_received | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence._received | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | method | machinery | parent-side re-validation of received reports over runtime_report_attempts; custody and read_from_child are the system (README 3b R1) |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | method | machinery | receipts bookkeeping / received-report re-validation over runtime_* tables; deleted (README 3e F5) |
| report_delivery.py | OperationalReportDelivery | class | machinery | finish: saves the form and releases the episode (README 3b D1, D3) |
| report_delivery.py | OperationalReportDelivery.finish | method | machinery | finish: saves the form and releases the episode (README 3b D1, D3) |
| report_delivery.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task.py | OperationalTask | class | episode function | task.py decide, action, TOOLS |
| task.py | OperationalTask.instructions | method | episode function | task.py _instructions |
| task.py | OperationalTask.next | method | episode function | task.py decide |
| task.py | OperationalTask.apply_response | method | episode function | task.py action |
| task.py | OperationalTask.execute | method | episode function | task.py TOOLS (api_result_operation, wait_for_service_job, lookups) |
| task.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision | class | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.call | method | episode function | task.py decide (ModelRequest REASONING) |
| task_decision.py | OperationalTaskDecision.conversation_key | method | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.interpretation_context | method | episode function | task.py _context |
| task_decision.py | OperationalTaskDecision.exchange_schema | method | machinery | decision-exchange loop; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_response | method | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | method | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | method | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_decision | method | machinery | decision-exchange protocol and saved-exchange checks; deleted (README 3a) |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_OSError | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_TypeError | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_ValidationError | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_ValueError | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global__action_generation_schema | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global__json | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global__plain | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_child_option_information | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_instructional_model_context | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_isinstance | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_len | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_lookup_attempts | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_model_snapshot | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_requested_contract_information | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_schema_failure_diagnostic | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_sqlite3 | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_state_frame | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_str | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _a106_original_global_type | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_decision.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| task_instructions.py | instructions | function | episode function | task.py _instructions (goal + tool knowledge + launch instructions; decision-exchange, pending delivery and wait text dropped) |
| task_state.py | OperationalTaskState | class | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.__init__ | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.bind_execution_context | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.record_execution_failure | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.restore_checkpoint | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.restore | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.record_effect | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | OperationalTaskState.checkpoint | method | machinery | restore / checkpoint / failure recording; deleted (README 3e) |
| task_state.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| to_parent.py | OperationalReport | class | episode function | messages/final_to_parent.py final_to_parent and messages/internal_summary.py facts_by_source |
| to_parent.py | OperationalReport._application_facts | method | episode function | task.py _outcome (reply[facts]); reader BLOCKED-ON-JOB-SERVICE |
| to_parent.py | OperationalReport._application_resolve_own | method | machinery | reference resolution through the old registries and receipts; custody (README 3b D2) |
| to_parent.py | OperationalReport._application_resolve_reference | method | machinery | reference resolution through the old registries and receipts; custody (README 3b D2) |
| to_parent.py | OperationalReport._appservice_report_facts | method | episode function | messages/final_to_parent.py final_to_parent and messages/internal_summary.py facts_by_source |
| to_parent.py | OperationalReport.required_return_sources | method | episode function | messages/final_to_parent.py RETURN_FORM (execution_result_refs required) |
| to_parent.py | OperationalReport.fact_sources | method | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | OperationalReport.facts | method | episode function | messages/final_to_parent.py final_to_parent and messages/internal_summary.py facts_by_source |
| to_parent.py | OperationalReport._live_facts | method | episode function | messages/final_to_parent.py final_to_parent and messages/internal_summary.py facts_by_source |
| to_parent.py | OperationalReport.resolve | method | machinery | reference resolution through the old registries and receipts; custody (README 3b D2) |
| to_parent.py | OperationalReport.validate_report | method | episode function | messages/final_to_parent.py validate_report (fact agreement; the validate_form call has no object: parent writes no form) |
| waiting.py | OperationalTaskWaiting | class | machinery | suspension machinery / provider patching; deleted |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | method | episode function | task.py wait_for_service_job (BLOCKED-ON-JOB-SERVICE) |
| waiting.py | OperationalTaskWaiting.suspension_changed | method | machinery | suspension machinery / provider patching; deleted |
| waiting.py | _bind_original_task_runtime_providers | function | machinery | provider patching / hook-era module-global binding; deleted (README 3a) |
| yield_estimator.py | ExecutionEpisodeYield | class | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | method | episode function | not carried: launch yield class (UNPLACED) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | method | episode function | yield_estimator.py task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | method | episode function | yield_estimator.py yield_controller / yield_key |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | method | episode function | yield_estimator.py yield_controller / yield_key |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | method | machinery | PracticalYieldEstimator deleted (README 3d, 7b) |
