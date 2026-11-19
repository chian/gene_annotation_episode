# Episode intent: A107 `api_job_execution`

Episode path: `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution`
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/<file>` (29 files, no `grading/` or `scoring/` subfolder).
Binding class: `ExecutionEpisode` (episode.py), built from 15 mixins. Role: `launch_api`. Commissioning parent: `execution_job_submission` (whose own role is `launch`). Binding version `execution_episode_v1`.

Siblings: `hpc_job_execution` (role `launch_hpc`) and `local_job_execution` (role `launch_local`) carry copies of the same 29 files. Eleven files are byte-identical across the three (`__init__`, configuration, presentation, received_records, resource_information, task, task_report, task_state, task_suspension, terminal_execution, waiting, work_operations). The places where they differ are listed under "Differences from siblings".

## What this episode is for (its goal, in its own words)

goal.py `NativeGoal.instructions`, built from the validated assignment's `service`:

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit.

`replaces_default_instructions = True`: this goal text replaces the default runtime INSTRUCTIONS. It is not appended to them.

execution_contracts.py docstring: "One explicit launch family for the shared episode loop. The binding routes a selected concrete assignment. Resource operations and result reads contain no model, resource selection or investigation loop."

So the episode runs one API service request (EBI HMMER, NCBI BLAST, UniProt, Rfam, BV-BRC AppService, all reached through `APIServiceExecution`) and stops at a usable monitoring/results handoff. It does no scientific interpretation of its own.

## Task and instructions

- task.py `NativeTask` (decision source type, `decision_source_type = NativeTask`) runs the old ordinary episode loop:
  - `next`: replays or completes recorded units, takes a decision snapshot, calls the model and applies the response.
  - `apply_response`: validates the selection. It also checks the reasoning commit (`empty_reasoning_commit`), job-child failure feedback and reads.map parameter feedback, then validates the `report_update` against the interpretation schema.
  - `execute`: runs the tool, reason or wait, journals the result and credit, and returns `controller_value`.
- task_instructions.py `instructions(source, context)` assembles the instruction text:
  - The base is the old `runtime_prompt.INSTRUCTIONS`. Because `replaces_default_instructions` is set, the specialist instructions (goal.py) replace it.
  - `REASONING_COMMIT_REQUIREMENT` is added when `reason` is permitted. It never is here: the episode permits only tool and wait.
  - Tool-knowledge and launch-instruction-library text are added when present.
  - The pending_child_delivery repair paragraph is always added.
  - The wait paragraph (pending_child_ handle) is added when `wait` is permitted.
  - The native_event_targets paragraph is added when wait is permitted and native event information exists.
  - Under the decision-exchange protocol, the old history guidance is replaced by the request_context exchange guidance.
- presentation.py `present_context` (`decision_prompt_renderer`) renders text TASK prompts from reconstructed state frames. It chooses a renderer by context type: hpc, published scientific (partner_presence_evidence), api launch, rna comparison/structure, selected execution, monitor or rna-comparison receiver. Anything else is presented as JSON. `presentation_protocol = 'episode_context_presentation_v1'`.

## What it reads from its parent's assignment (from_parent.py, science.py)

- `assignment_schema(role)`: an `anyOf` of one `_request_schema` per configured resource whose kind matches `ROLE_KINDS[role]`, here `api`. For an API resource the base schema is `api_execution.assignment_schema(resource_id)`, with `resource_id` fixed as a const and required.
- `prepare_assignment(parent, role, selection, scope, operation_key)` checks the selection against that schema and runs `_validate_request` and `api_execution.validate_assignment(selected, scope)`. It then:
  - requires the role's kind to equal the resource kind (`execution_resource_kind_conflict`);
  - requires `parent.role == 'launch'` (`resource_child_role_owned_by_launch`);
  - re-validates the parent's original launch assignment (`_launch`: launch_assignment_schema, BLAST graded requests, per-resource requests, resource constraints);
  - runs `_validate_blast_launch_selection`;
  - checks the masking, utility and immutable-input-version inputs (`_versions`), and native BLAST DB, standard BLAST DB and RNA-structure job inputs.
- `_permitted` applies the parent constraints: `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`.
- `child_assignment_schema` returns `assignment_schema(role)`. The api copy has a dead `if parent.role == 'launch' and False` branch.
- science.py `_check_parent_inputs` runs at initialize and execute. It reads the parent's recorded `episode_assignment` from `runtime_episodes` and re-validates it. The API-only extra is `_validate_blast_api_parent_request`, which binds a graded NCBI BLAST request to the parent's subject:
  - the service must be ncbi_blast and the resource permitted;
  - the query sequence sha256 must match `api.blast.prepare`;
  - the database must equal the parent's database.

## Children

None: `child_roles` returns `()`, `allowed_children` returns `()`, and `entry_roles` is `()`, so the episode is never a run entry.

## Decision state and what it shows the model

- internal_summary.py `native_decision_snapshot(self, view)` builds the model context. It reads:
  - `goal`, `scope` and `working_state`;
  - `visible_record_refs`, resolved through `_references_in`;
  - `current_credit`, `current_evidence_vector`, `credit_binding` and `time_accounting` (`journal.elapsed_view`);
  - `pending_work`, `last_local_outcome`, `feedback` and `visual_evidence`, the last image.view taken from runtime_actions;
  - `report_deliveries`, `controller`, `controller_binding`, `tools` (catalog), `tool_knowledge` and `job_episode_options`;
  - `available_report_facts` (FACT_SOURCES/FACT_MEANINGS plus extra sources), `requested_report_purpose`, `requested_form`, `current_report_update`, `current_report_basis_refs` and `report_lifecycle`;
  - the specialist's `decision_context` and `_completed_work_axis_results`.

  It contains an annotation-axis-credit branch that does not apply to this operational episode.
- `NativeInternalSummary.decision_context` (the episode's own addition) supplies:
  - `execution_assignment` and `execution_progress` (= `self.facts(context, {})`);
  - whatever `api_execution.decision_context(context, view)` returns;
  - `selected_execution_task` when `services.scientific_parent_task(context)` returns a parent. That task holds the scientific_question and selected_tool_info from the scientific parent, plus the per-request resource and job view. Only `ebi_hmmer` qualifies on API resources.
- task_decision.py `call` adds to the context:
  - `resource_context`, `shared_information_context`, `launch_instruction_library` and `selected_launch_instructions`;
  - `child_options` (none here) and the binding's initial decision context;
  - `completed_action_reports` from `episode_work_report`, plus `requested_action_history` for hpc contexts;
  - `pending_work`, `execution_expectations`, `resource_tool_estimates` and `native_execution_expectations`;
  - **`waiting_support`** when wait is permitted, which applies to this API copy only;
  - `contract_information_profile`.

  It also keeps the old decision-exchange protocol (request_context lookups and recorded exchanges).
- initial_information.py reads `resource_information` and `received_api_information` from the readers catalog for this binding path.

## Tools it offers

- `permitted_common_actions`: `('tool', 'wait')` when the validated assignment's version is `api_service_assignment_v1`, otherwise `('tool',)`. **Only the API copy can wait.** No reason, no child.
- `catalog(context)` (work_operations.py) is the `_delegate(context).catalog(practical_context)`. For API resources this is the api_execution's operation contracts.
- `execute` runs `_check_parent_inputs`, then the delegate's execute.
- resource_information.py `resource_tool_contracts()` publishes launch, result and homology operations per resource for the parent's catalog, with route `{'kind': 'commission', 'routes': [...]}`. Launch and result entries come from `api_execution.operation_contracts(resource_id, 'launch_api'|'results')`, plus `homology_api_contracts`. Local and hpc resources get `operation_catalog(kind)` and `native_result_operation_catalog()`: execution.results.status, collect and read. NMF, RNA-structure and Infernal tool contracts are added when those are configured.

## Credit

credit.py `ExecutionEpisodeCredit`:
- `credit_kind` is `'operational'`.
- Live credit comes from `api_execution.credit_view(context, receiver_selection)`, with units `handoff_unit` and `acquired_record_unit` from configuration.
- Closed credit is the `_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'` snapshot. It is captured once in the closing facts (`_closed_credit_facts`) and re-validated afterwards from `runtime_forms`, `runtime_episodes`, `runtime_observations` and the receipt-inheritance chain (`runtime_receipt_inheritance`, `runtime_record_receipts`, `EpisodeReceipts.read_manifest`), so later delivery never reprices it.
- Credit is used raw. It is only checked to be finite, never bounded.

## Continuation (yield estimator)

yield_estimator.py `ExecutionEpisodeYield`:
- requires `require_private_yield=True`, and otherwise raises `execution_private_yield_binding_not_enabled`;
- the controller is `YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(verify_completion))`;
- the profile key is `'launch_api:' + _request_yield_class(request)`. For an API request the class is `api_<service>[_<algorithm>][_<database>]_handoff`, for example `launch_api:api_ebi_hmmer_phmmer_..._handoff`. A missing profile raises `execution_original_task_yield_profile_required:<key>`.
- The old estimator: a verified original handoff completion gives exact zero expected next gain.

In the new estimators this is **completion with a target**: the verified handoff endpoint is the target, and before it the gain is estimated from the profile's parameters. Settings: `task_yield_profiles[key] = {cutoff>0, parameters}`.

completion.py: `verify_completion` validates the proof. It first reuses an endpoint verification recorded in `runtime_observations` (`_closed_completion_verdict`, checking ESTIMATOR_VERSION, `fitting_scope == 'verified_assignment_endpoint'` and an exact-zero `expected_next_gain`), and otherwise calls `api_execution.verify_completion`.

## What it reports to its parent (to_parent.py, task_report.py)

- `facts(context, snapshot)` = live facts plus closed credit facts. Live facts are:
  - empty lists for every native result fact family (HMMER, masking, BLAST utility, RNA comparison and structure, NMF, Infernal and preparation, BLAST standard and DB, HMMER preparation, BLAST pairwise);
  - then `api_execution.facts(...)`;
  - `execution_result_origin: None`.
- `fact_sources` and `resolve` come from the library received_result_readers.
- `validate_report` runs each configured return adapter's `validate_received_report`. That covers RNA comparison and structure, NMF, Infernal and preparation, masking and utility. When requested, it adds the UniProt returns, whose closed facts are frozen, and the Rfam returns. It then checks `validate_form` and requires every `x-source` field to equal its recorded fact (`execution_report_disagrees_with_recorded_facts`).
- `required_return_sources` is `()`.
- task_report.py `finish`:
  - without a report contract it returns `{credit, pending_handles, **current_report_facts}`;
  - otherwise it builds the form with `form_with_facts(report_values, schema, facts)` and saves it once in `runtime_forms`.

## Configuration (configuration.py, binding_record.py)

`NativeConfiguration(services, *, store, directory, run_id, resources, initial_information, tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield=False, results_yield_profiles=None, task_yield_profiles=None)`:
- `resources` must be explicit, each with `kind` in `local`, `pbs_ssh`, `hmmer_api` or `api`.
- Units must be positive and finite.
- `results_yield_profiles` keys are limited to `native_unbounded_local` and `native_unbounded_hpc`.
- Allowed native bindings per resource are checked; NMF, RNA-structure and Infernal must be local.
- A `TerminalExecutionBehavior` is built per non-API resource, and an `APIServiceExecution` for the API resources.
- Also built: `ExecutionProgressProvider`, `LocalFileSourceResults`, the primary and preparation result readers, and the optional NMF, RNA and Infernal result/return adapters.

`as_record` records the binding id (its own path) and the configuration.

## File-by-file

`w.` = `self.workflow.`. Uses are counts in the file.

| file | lines | own intent | old-runner names |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| binding_record.py | 8 | binding id = own path; recorded configuration incl. yield profiles | none |
| completion.py | 51 | verify handoff completion; reuse one recorded endpoint verification | runtime_observations(1), episode_return_records `_same`(1), method_loop.identities `UnitRef`(1), numerical `NumericBand`(1), practical_yield ESTIMATOR_VERSION(2) |
| configuration.py | 119 | resource, unit and log configuration; per-resource behaviours; API execution; progress provider; result readers | numerical YieldController(3)/YieldParameters(3) (profile validation) |
| credit.py | 136 | operational credit; closed-credit snapshot that is never repriced | runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2), episode_receipts(1), episode_return_records(3) |
| episode.py | 106 | role `launch_api`; parent `execution_job_submission`; no children; tool, plus wait for api_service_assignment_v1 | imports communication(1), runtime FACT_*(1); class attrs decision_source_type/received_* authority flags |
| execution_contracts.py | 57 | constants: ROLES, KINDS, ROLE_KINDS, NATIVE_RESULT_ORIGIN, native results operation catalog | communication(1); imports many shared-root modules |
| from_parent.py | 114 | assignment schema; parent constraint permission; launch re-validation; input checks | none (shared-root imports only) |
| goal.py | 9 | the goal text (service-specific) | none |
| initial_information.py | 9 | readers for own path | none |
| internal_summary.py | 91 | `decision_context` + `selected_execution_task` (ebi_hmmer only on API) | `_live_original_runtime`(11), runtime(6), runtime_actions(2), w.journal(3), w.store(3), w.working_state, w.local_outcome_preview, w.source_credit_view, w.source_credit_binding, w.pending_work, w.delivery_status, w.controller_binding, w.catalog, w.knowledge, w.job_episode_options, w.extra_report_sources, w.specialist, w.binding_context, w.tools, w.run_id (1 each) |
| presentation.py | 74 | renderer selection by context type | `_live_original_providers`(20), decision_context(1) |
| received_api_reports.py | 4 | API reader authority for own path | none |
| received_execution_information.py | 4 | result readers for own path | none |
| received_records.py | 127 | own handoff and result target checks; BLAST grader query hash check; initial references | none (library readers) |
| resource_information.py | 70 | tool contracts published to the parent | none |
| science.py | 76 | parent input re-validation; API BLAST grader binding | runtime_episodes(1) |
| state.py | 19 | initialize = check parent inputs + delegate; `state` raises for API | none |
| task.py | 225 | old loop next/apply_response/execute | `_live_original_runtime`(51), runtime(1), providers(1), episode_source_failure(1), runtime_actions(8), runtime_episodes(1), runtime_model_calls(2), w.execution_binding(7), w.store(9), w.journal(7), w.inprocess_replay(4), w.completions(3), w.completed_unit(3), w.selected(3), w.run_id(3), w.decision_exchanges(3), w.controller_value(2), w.specialist(2), w.binding_context(2), w.action_schema, w.automatic_score_updates, w.delivery_resolution_inputs, w.execute, w.last_observed_credit, w.next_return, w.pending_work, w.permits_common_action, w.reasoning_action_schema, w.receive_native_outcome, w.receive_outcome, w.resolve_pending_deliveries, w.resolver, w.retain_shared_grading_results, w.source_credit_view, w.validate_report |
| task_decision.py | 359 | decision context assembly incl. waiting_support; exchange protocol | `_live_original_runtime`(85), runtime(1), providers(1), episode_work_report(2), runtime_model_calls(8), w.resource_estimator(5), w.validate_contract_information(5), w.decision_exchanges(4), w.receipts(4), w.decision_protocol(3), w.is_job_source(3), w.journal(3), w.provider(3), w.job_episodes(2), w.launch_instructions(2), w.services(2), w.store(2), w.uses_received_record_context(2), w.available_child_roles, w.binding_context, w.contract_information_profile, w.contract_information_reply, w.controller_binding, w.episode_bindings, w.execute, w.execution_expectations, w.freeze_contract_information, w.freeze_literature_numerical_contracts, w.history_preview, w.native_estimation_context, w.numerical_contracts, w.pending_work, w.permits_common_action, w.resource_context, w.run_id, w.shared_information_context, w.specialist, w.waiting_support |
| task_instructions.py | 25 | instruction assembly incl. wait and native event paragraphs | `_live_original_runtime_prompt`(7), w.permits_common_action(3), w.binding_context, w.decision_protocol, w.is_job_source, w.job_episodes, w.knowledge, w.launch_instructions, w.native_event_information, w.specialist |
| task_report.py | 22 | finish: form with facts | `_live_original_runtime`(7), runtime(1), runtime_forms(2), w.journal(2), w.release(2), w.binding_context, w.episode_bindings, w.facts, w.pending_handles, w.source_credit_view |
| task_state.py | 107 | source state, restore, checkpoint, record_effect | `_live_original_runtime`(14), runtime(1), episode_source_failure(1), runtime_actions(5), w.inprocess_replay(7), w.journal(5), w.completions(4), w.execution_binding(4), w.progress_provider(2), w.store(2), w.archive, w.controller_value, w.recover_commissions, w.run_id, w.source_credit_view |
| task_suspension.py | 8 | suspension condition to backend | w.execution_handle(2), w.execution_backend(1) |
| terminal_execution.py | 226 | local/HPC terminal behaviour: exec_command instructions, receipts, completion proof, facts | communication(1), practical_yield PracticalYieldEstimator(2); `services.workflow.launch_instructions` via getattr |
| to_parent.py | 88 | facts (API: api_execution.facts) and report validation | none (shared-root imports only) |
| waiting.py | 10 | selected wait wrapper | `_live_original_runtime`(3), runtime(1), w.perform_selected_wait(1) |
| work_operations.py | 35 | catalog/execute through delegate | none |
| yield_estimator.py | 50 | `launch_api:` profile selection, completion target | numerical YieldController(2)/YieldParameters(2), practical_yield PracticalYieldEstimator(4) |

Other old names used: the old `services` callbacks (`services.scientific_parent_task`, `services.annotation_task_required`, `services.read_received_molecular_input`), the old `context` record (`context.role`, `path`, `scope`, `assignment`, `episode_id`, `run_id`), and the `BindingContext` handed in by `self.workflow.binding_context(self)`.

## Differences from siblings (hpc_job_execution, local_job_execution)

These are the API copy's own pieces:
- **goal.py**: the service-specific goal text. The siblings return `self._delegate(context).instructions(...)`, the TerminalExecutionBehavior exec_command text.
- **episode.py `permitted_common_actions`**: wait is allowed for `api_service_assignment_v1`; the siblings allow tool only.
- **task_decision.py**: adds `waiting_support`.
- **task_instructions.py**: adds the reasoning-commit, wait and native-event paragraphs. The siblings leave the native-event line as the no-op expression `source.workflow.native_event_information is not None`.
- **credit.py `_live_project_credit`**: uses `api_execution.credit_view`. The siblings use `_delegate(...).credit_view` (terminal state).
- **completion.py**: falls back to `api_execution.verify_completion`. The siblings use `self.state(context).verify_completion`.
- **state.py `state`**: raises `practical_resource_role_required`. The siblings delegate.
- **internal_summary.py `decision_context`**: built from `execution_assignment`, `execution_progress` and the api_execution decision context. The siblings use `_delegate(...).decision_context`.
- **to_parent.py facts**: `api_execution.facts`. The siblings collect practical receipts, handoffs, result windows, file sources and file capture outcomes, plus `execution_result_origin` and `execution_completed`.
- **science.py**: `_validate_blast_api_parent_request`.
- **from_parent.py**: `_validate_blast_launch_selection` in `prepare_assignment`. The siblings omit it.
- **yield_estimator.py**: profile prefix `launch_api:`. `practical_estimator` builds `PracticalYieldEstimator(verify_completion)`; the siblings delegate to the terminal behaviour.

## Carried over

Episode folder: `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` (ten-file form). Old files read from `97308b94c`. One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__api_job_execution.tsv`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | NativeBindingRecord | machinery | the binding's own as_record() and recorded configuration (README 3, binding_record.py): the system journals settings and declared services |
| binding_record.py | NativeBindingRecord.as_record | machinery | the binding's own as_record() and recorded configuration (README 3, binding_record.py): the system journals settings and declared services |
| completion.py | NativeCompletion | machinery | completion proof and verified-completion lookup in runtime_observations (README 3d: completion proof is no controller input); the handoff-completion value now comes from the job_access reply (tool outcome execution_completed, task.py::_outcome) and the completion controller target (yield_estimator.py) |
| completion.py | NativeCompletion.completion_for_action | machinery | completion proof and verified-completion lookup in runtime_observations (README 3d: completion proof is no controller input); the handoff-completion value now comes from the job_access reply (tool outcome execution_completed, task.py::_outcome) and the completion controller target (yield_estimator.py) |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | completion proof and verified-completion lookup in runtime_observations (README 3d: completion proof is no controller input); the handoff-completion value now comes from the job_access reply (tool outcome execution_completed, task.py::_outcome) and the completion controller target (yield_estimator.py) |
| completion.py | NativeCompletion.verify_completion | machinery | completion proof and verified-completion lookup in runtime_observations (README 3d: completion proof is no controller input); the handoff-completion value now comes from the job_access reply (tool outcome execution_completed, task.py::_outcome) and the completion controller target (yield_estimator.py) |
| configuration.py | NativeConfiguration | machinery | home factory/configuration of the old runner (services, providers, APIServiceExecution, ExecutionProgressProvider, result readers, TerminalExecutionBehavior); its values are the continuation settings read in task.py::_outcome (handoff_unit, acquired_record_unit) and yield_estimator.py::task_yield_profile (task_yield_profiles), tool_knowledge_directory, launch_instructions_directory |
| configuration.py | NativeConfiguration.__init__ | machinery | home factory/configuration of the old runner (see class row); resources/initial_information validation has no home (reported unplaced) |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py::credit (the class); closed-credit snapshot parts are machinery (rows below) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit snapshot over runtime_episodes/runtime_observations (store.db) and EpisodeReturnRecords |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit snapshot over runtime_receipt_inheritance/runtime_record_receipts (EpisodeReceipts) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit snapshot check |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit snapshot captured into runtime_forms facts |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit snapshot read from runtime_forms (the system returns completion[credit]; final_to_parent.py returns it) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py::credit (live credit over summary; the closed view is machinery) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py::credit (old api_execution.credit_view; formula reconstructed, see blocked file) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py::credit |
| episode.py | ExecutionEpisode | episode function | episode.py::ApiJobExecution (one class, members from the ten files) |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py::_offered (wait only for api_service_assignment_v1) |
| execution_contracts.py | native_result_operation_catalog | episode function | unplaced: local/PBS result acquisition operations of the results role; the API launch path never offers them (reported) |
| from_parent.py | NativeParentRequests | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent); parent-launch checks are not carried |
| from_parent.py | NativeParentRequests._permitted | episode function | unplaced: check of the parent launch assignment (a commission check, rule 1; reported) |
| from_parent.py | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (the api branch; the non-api requested_job branches belong to the local/hpc routes) |
| from_parent.py | NativeParentRequests._launch | episode function | unplaced: re-validation of the parent launch assignment (a commission check, rule 1; reported) |
| from_parent.py | NativeParentRequests._constraints | episode function | unplaced: check of the parent launch constraints (a commission check; reported) |
| from_parent.py | NativeParentRequests.child_assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_api_assignment from forms/partner_presence_evidence/execution_contracts.py: already in library); the later parent-launch/BLAST/masking/utility/version/DB checks are commission checks and are not carried (reported) |
| goal.py | NativeGoal | episode function | goal.py GOAL; task.py INSTRUCTIONS |
| goal.py | NativeGoal.instructions | episode function | task.py::INSTRUCTIONS (with {service}) and task.py::_instructions; goal.py::GOAL |
| initial_information.py | initial_information | episode function | task.py::api_capabilities (first unit, lookup tool) and task.py::_context configured_resource; its reader catalog (resource_information, received_api_information) has no library home (reported) |
| internal_summary.py | native_decision_snapshot | machinery | old decision snapshot over working_state, journal.db runtime_actions, source_credit_view, pending_work, delivery_status (README 3a); its content is rebuilt in messages/internal_summary.py::internal_summary and task.py::_context |
| internal_summary.py | NativeInternalSummary | episode function | messages/internal_summary.py::internal_summary and task.py::_context |
| internal_summary.py | NativeInternalSummary._with_selected_execution_task | episode function | unplaced: reads the scientific parent task through services.scientific_parent_task (ebi_hmmer only); no home (reported) |
| internal_summary.py | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py::internal_summary (execution_assignment, execution_progress) and task.py::_context; api_execution.decision_context has no library copy (reported) |
| presentation.py | present_context | episode function | task.py::_context (TASK and STEERING as named sections of the model context); the old renderer chain (render_api_launch_prompt, render_partner_presence_evidence_prompt, apply_state_frame) lives in the old shared root and the state-frame part is machinery (reported) |
| received_api_reports.py | received_api_reports | machinery | old received-information catalog authority (catalog.received/configured): replaced by system custody (README 3b R3, F1) |
| received_execution_information.py | received_execution_information | machinery | old received-information catalog authority (catalog.received/configured): replaced by system custody (README 3b R3, F1) |
| received_records.py | NativeReceivedRecords | machinery | received-record custody (README 3b P2, R3): the system holds what the parent named in input_refs |
| received_records.py | NativeReceivedRecords._context_target | machinery | commission/handoff-target checks against the parent launch (rule 1: not carried; custody replaces) |
| received_records.py | NativeReceivedRecords._received | machinery | receipt ledger of received references (EpisodeReceipts, store.read_snapshot): system custody |
| received_records.py | NativeReceivedRecords.initial_references | machinery | initial received references: system custody (input_refs named in msg_to_child of the parent) |
| resource_information.py | NativeResourceInformation | episode function | task.py::api_capabilities (job_access.api_capabilities returns the operation contracts); api_execution.operation_contracts has no library copy (BLOCKED-ON-JOB-SERVICE) |
| resource_information.py | NativeResourceInformation.resource_tool_contracts | episode function | task.py::api_capabilities / task.py::_context callable_operations; the contracts come from the job_access service (BLOCKED-ON-JOB-SERVICE) |
| science.py | NativeScienceInputs | episode function | unplaced: checks of the parent launch inputs (commission checks); see rows |
| science.py | NativeScienceInputs._masking_inputs | episode function | unplaced: commission check against the parent launch (reported) |
| science.py | NativeScienceInputs._utility_inputs | episode function | unplaced: commission check against the parent launch (reported) |
| science.py | NativeScienceInputs._expression_nmf_inputs | episode function | unplaced: commission check against the parent launch (reported) |
| science.py | NativeScienceInputs._versions | episode function | unplaced: immutable-input-version check against the parent launch (reported) |
| science.py | NativeScienceInputs._check_parent_inputs | episode function | unplaced: re-read of the parent launch request (commission check; reported) |
| science.py | NativeScienceInputs._validate_blast_api_parent_request | episode function | unplaced: BLAST graded-request check (service ncbi_blast, query sha256 of the subject sequence, fixed database) against the parent request, reading the Store through tool_registry; a commission check and A107BlastExecution is not in the library (reported) |
| state.py | NativeState | machinery | old practical-state hooks (initialize/state: practical_resource_role_required); the API child has no practical state |
| state.py | NativeState.initialize | machinery | old practical-state hooks (initialize/state: practical_resource_role_required); the API child has no practical state |
| state.py | NativeState.state | machinery | old practical-state hooks (initialize/state: practical_resource_role_required); the API child has no practical state |
| task.py | NativeTask | machinery | old decision loop; own parts rows below |
| task.py | NativeTask.next | machinery | old decision loop (inprocess_replay, completions, runtime_model_calls, SourceEnd, decision exchange); the loop is the system decide/action cycle |
| task.py | NativeTask.apply_response | episode function | task.py::action (schema admission of the answer, rejection with feedback, record held check); reasoning commit, redelivery, report_update and recorder parts are machinery |
| task.py | NativeTask.execute | episode function | task.py TOOLS (api_operation, wait_for_service_job, lookups run as tool units); journal.save/measure, receive_outcome, automatic_score_updates are machinery |
| task_decision.py | NativeTaskDecision | machinery | model-call machinery (journal runtime_model_calls, decision exchange, receipts); own parts rows below |
| task_decision.py | NativeTaskDecision.call | episode function | task.py::decide (context pieces: launch_instruction_library and selected_launch_instructions, tool knowledge, waiting support text) ; context pieces resource_context, shared_information_context, completed_action_reports, execution_expectations, resource_tool_estimates, native_execution_expectations, waiting_support have no home here (reported); recording is machinery |
| task_decision.py | NativeTaskDecision.instructions | episode function | task.py::_instructions |
| task_decision.py | NativeTaskDecision.conversation_key | machinery | provider conversation key (README 3a conversation state) |
| task_decision.py | NativeTaskDecision.interpretation_context | machinery | decision-exchange lookup references (decision-exchange loop) |
| task_decision.py | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | NativeTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_decision.py | NativeTaskDecision.decision_completion | machinery | provider patching (decision completion binding) |
| task_instructions.py | instructions | episode function | task.py::_instructions (goal text, knowledge and launch instructions, wait text); reasoning-commit, in-process child wait, redelivery and decision-exchange texts describe actions that no longer exist |
| task_report.py | NativeTaskReport | machinery | report_form machinery: finish, form_with_facts, runtime_forms, workflow.release (README 3b D1, D3) |
| task_report.py | NativeTaskReport.finish | machinery | report_form machinery: finish, form_with_facts, runtime_forms, workflow.release (README 3b D1, D3) |
| task_state.py | NativeTaskState | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.__init__ | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.bind_execution_context | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.record_execution_failure | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.restore | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.record_effect | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_state.py | NativeTaskState.checkpoint | machinery | recorder/checkpoint/restore/record_effect/inprocess_replay source state (README 3e) |
| task_suspension.py | NativeTaskSuspension | machinery | suspension forwarding to the old execution backend (wait/suspension machinery) |
| task_suspension.py | NativeTaskSuspension.suspension_changed | machinery | suspension forwarding to the old execution backend (wait/suspension machinery) |
| terminal_execution.py | TerminalExecutionBehavior | episode function | unplaced: byte-identical copy of the local/HPC terminal behaviour, never built for API resources (reported) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.as_record | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | unplaced (see class row): terminal behaviour never built for API resources |
| to_parent.py | NativeParentReturns | episode function | messages/final_to_parent.py (RETURN_FORM, final_to_parent, validate_report) |
| to_parent.py | NativeParentReturns.required_return_sources | machinery | returns () : the parent selects return fields in msg_to_child (rule 5) |
| to_parent.py | NativeParentReturns.facts | episode function | messages/final_to_parent.py::final_to_parent (credit, finding, handoff refs, completion, selected facts); closed-credit facts are machinery |
| to_parent.py | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py::final_to_parent / EMPTY / FIELDS (native empty families; api_execution.facts arrive in the tool outcome facts) |
| to_parent.py | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py::validate_report (the recorded-facts agreement check); validate_received_report of masking/utility/uniprot/rfam returns has no library copy and raises validate_received_report_not_built (reported) |
| waiting.py | perform_selected_native_wait | episode function | task.py::wait_for_service_job (the wait TOOL; the failed wait is a returned outcome) |
| work_operations.py | NativeWorkOperations | episode function | task.py TOOLS |
| work_operations.py | NativeWorkOperations.catalog | episode function | task.py::api_capabilities and task.py::_context callable_operations |
| work_operations.py | NativeWorkOperations.execute | episode function | task.py::api_operation (parent-input check dropped: commission check) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py::request_yield_class |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py::task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller (CompletionYieldController; target from parent_input) |
| yield_estimator.py | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator deleted (README 3d): one of the three controllers |
