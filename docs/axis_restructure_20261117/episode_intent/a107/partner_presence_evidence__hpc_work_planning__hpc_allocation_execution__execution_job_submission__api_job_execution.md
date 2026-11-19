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
