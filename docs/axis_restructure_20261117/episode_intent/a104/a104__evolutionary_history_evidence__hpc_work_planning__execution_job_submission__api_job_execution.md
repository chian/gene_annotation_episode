# a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/api_job_execution/<file>`
(the 54 files directly in this folder; no `grading/` or `scoring/` subfolder; it has no child folders).
Old binding class: `ExecutionEpisode` (`binding_path = '.../execution_job_submission/api_job_execution'`,
`commissioning_parent = '.../execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `APIJobTask`, prompt renderer `present_api_context`.

## What it is for (its goal, in its own words)

`instructions.py` `APIInstructions.instructions()` (the file named `goal.py` holds the selected-task view instead):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair
> from the actual available operations and received outcomes. Distinguish an immediate returned response from a service
> job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply
> does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded
> service facts. The configured controller governs continuation; verified original handoff completion gives exact zero
> future credit.

`{service}` is the assignment's `service` (e.g. `ncbi_blast`, `ebi_hmmer`, `uniprot`, `bvbrc_data`,
`bvbrc_appservice`). The episode executes one remote API request chosen by its launch parent and ends at a usable
handoff (monitoring/results reference) for that request.

## Task and instructions

`task_instructions.py`: the same composition as its launch parent (goal text replaces generic `INSTRUCTIONS`;
reasoning requirement only if `reason` permitted — it never is; tool knowledge; launch instruction library;
redeliver_report paragraph; wait paragraph when `wait` is permitted; native-event paragraph; exchange-protocol
replacement).

`task.py` (`APIJobTask`) carries `next`, `apply_response` and `execute` in one file. Because `reason` is never
permitted, there is no empty-reasoning-commit check; the report update is admitted with grain `launch_api`.

Permitted common actions (`episode.py`): `tool` and `wait` when the assignment version is `api_service_assignment_v1`;
otherwise (`api_execution_assignment_v1`, the legacy HMMER form) `tool` only.

## What it reads from its parent's assignment

`from_parent.py`: assignment = anyOf the concrete request schemas of the bound API resources (each with const
`resource_id`; `required` includes `resource_id`). `prepare_assignment` requires the commissioning role `launch`, a kind
match, the API service's own assignment validation in scope, the BLAST launch-selection check against the parent's
original launch, masking/utility inputs, the parent's immutable input versions and native BLAST database job inputs.
At `initialize` and before every action `_check_parent_inputs` re-reads the parent's recorded launch assignment
(`episode_assignment`) and repeats those checks plus `_validate_blast_api_parent_request` (this API-only check is
absent from the local/HPC siblings). `required_return_sources` returns `()`.

## Children it may commission

None (`child_roles` and `allowed_children` return `()`). It is a leaf.

## Decision state and what it shows the model

Generic old-runner context (as in the launch parent) plus this binding's `internal_summary.decision_context`:
`execution_assignment`, `execution_progress` (report facts), the API executor's `decision_context`
(`api_service`, `api_request`, `api_received_progress` = latest {state, kind, facts, failure_code} per operation name,
`api_execution_completed`; for legacy HMMER: `api_execution_assignment`, `api_execution_prepared_request`,
`api_execution_job`, `api_execution_completion`) and `selected_execution_task` for an `ebi_hmmer` request
(scientific question, selected tool info, request, resource information). Execution expectations are captured for role
`launch_api`.

## Tools it offers

The bound service's launch catalog for this request (`service.launch_catalog(request)`), or the HMMER catalog
(`hmmer_operation_catalog('launch_api')`) for `hmmer_api`. Execution (`api_service.py`):
- arguments validated against the operation's input schema; work selected once per operation key;
- per-action directory with a lock and immutable `intent.json`, `snapshot.json`, `event.json`, `outcome.json`;
- a second remote-mutating submission is refused (`api_original_submission_already_exists`) unless the earlier one is
  recorded `not_sent`; an interrupted call with no event becomes `api_operation_response_unknown` with submission
  outcome `unknown`;
- a `handoff_ready` event publishes an `api_service_receipt_v1` receipt and a handoff source (`api_handoff_<digest>`);
- BV-BRC AppService operations go to `appservice_submission.py`, whose publication grades the selected adapter
  calculation (bvbrc_proteome v1/v2) inside the download action and stores its sheet and components.

## How its credit is counted

`credit.py`: kind `operational`; the live credit is the API executor's `credit_view`:
`handoff_unit` x (new distinct `(resource_id, execution_id)` handoffs among known references, excluding those already
in the initial references) + `acquired_record_unit` x (new result identities, excluding initial ones). The binding
record states `scientific_credit: False`, `monitoring_credit: False`. Legacy HMMER uses the same formula with
qualification `received_qualified_original_api_handoffs_and_own_canonical_result_records`. Closed episodes return the
frozen `execution_closed_operational_credit_v1` view. Unbounded; only finiteness is checked.

Completion: the latest completed outcome with a receipt (AppService: the latest `TaskHandoff` receipt) gives
`practical_completion_v1`, endpoint `usable_handoff`.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_api_yield_controller`: task yield profile `launch_api:` + request class
(`api_<service>[_<algorithm>][_<database>]_handoff`), old `YieldController(epoch, initial_credit, profile.cutoff,
YieldParameters(**profile.parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`: forecasts
from observed history until a verified completion proof, then exact zero. In the new set of three this is
**completion with a target** (target = the verified usable handoff). Settings as in the launch parent
(`task_yield_profiles`, `handoff_unit`, `acquired_record_unit`, resources, log window/roles).

## What it reports to its parent

`to_parent.py`: empty native family sources, then the API executor's facts: `execution_handoff_refs`,
`execution_result_refs`, BV-BRC data facts, UniProt facts, `execution_blast_hsps` (empty), `execution_completed`;
`execution_result_origin` is `null`. AppService adds `bvbrc_appservice_support_refs` and homology / phylogeny /
proteome facts. `validate_report` requires `x-source` fields to equal the recorded facts (UniProt closed facts frozen).

## Differences from similar episodes

- vs `hpc_job_execution` / `local_job_execution`: remote API services instead of `exec_command`; its own
  `APIJobService` and `HMMERJobService` executors (the siblings and the launch parent use the shared `APIRecordAccess`);
  `wait` is permitted for `api_service_assignment_v1`; credit counts handoffs and acquired result records; report
  origin is always null; extra BLAST API parent-request validation; goal text lives in `instructions.py` and
  `goal.py` holds the selected-task view.
- vs the launch parent: leaf, no `reason`, credit per (resource_id, execution_id) rather than per resource_id, and
  completion-proof continuation rather than a count of remaining requests.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `action_outcomes.py` | 5 | `_outcome` (completed / invalid with arguments_or_reference feedback). | none |
| `api_actions.py` | 17 | Tool catalog and execute: check the original parent launch inputs, then delegate to the API execution for this assignment. | `import:communication` (1) |
| `api_service.py` | 296 | `APIJobService`, this episode's own API service executor: builds one service per `api` resource (`build_service`), a legacy HMMER executor for `hmmer_api`, BV-BRC data host, AppService submission, homology/phylogeny/proteome returns. Executes one operation per action under a file lock with immutable intent/snapshot/event/outcome files; refuses a second remote-mutating submission unless the first was `not_sent`; records unknown response on recovery; publishes a usable handoff source with receipt when the event is handoff_ready. Facts (handoff refs, result refs, BV-BRC, UniProt, HSPs, completed), credit view (handoff_unit x new (resource_id, execution_id) handoffs + acquired_record_unit x new result identities, excluding initial references; scientific_credit and monitoring_credit false), completion proof (`usable_handoff`), decision context (service, request, latest received progress per operation, completed). | none |
| `api_state.py` | 14 | `initialize`: local-file source probe, parent-input check, API execution initialize; `_api_execution_for` validates the request. | `import:communication` (1) |
| `appservice_publication.py` | 87 | BV-BRC AppService publication of an acquisition; `_grade` runs the selected pure adapter calculation (bvbrc_proteome v1/v2) inside the download action and publishes its sheet and components as an AdapterResult. | none |
| `appservice_submission.py` | 50 | BV-BRC AppService submission host: own receipts, facts (TaskHandoff handoff refs vs support refs, own results, homology/phylogeny/proteome facts), completion (latest TaskHandoff), publication of acquisitions. | none |
| `binding_record.py` | 9 | `as_record()`: binding id `.../execution_job_submission/api_job_execution`, version and full configuration. | none |
| `binding_roles.py` | 6 | VERSION, ROLES, KINDS, ROLE_KINDS copies. | none |
| `closed_credit.py` | 122 | Closed operational credit freezing and read-back, as in the launch episode (`execution_closed_operational_credit_v1`). | `import:communication` (1), `import:episode_receipts` (1), `import:episode_return_records` (3), `name:EpisodeReceipts` (1), `name:EpisodeReturnRecords` (1), `name:_same` (3), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations` (1), `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2) |
| `closed_credit_values.py` | 3 | `_CLOSED_CREDIT` constant. | none |
| `completion.py` | 55 | `completion_for_action` delegates to the API execution; `verify_completion` checks a recorded closed verdict, then the API execution's proof. | `import:communication` (1), `import:numerical` (1), `import:practical_yield` (1), `import:episode_return_records` (1), `import:method_loop.identities` (1), `name:ESTIMATOR_VERSION` (1), `name:NumericBand` (1), `name:_same` (4), `name:UnitRef` (1), `table:runtime_observations` (1) |
| `configuration.py` | 76 | Same validated settings as the launch episode, but its API executor is this episode's own `APIJobService` (with its own HMMER executor), and practical resources use its own `terminal_receipt_state.TerminalExecutionBehavior`. | `import:communication` (1), `import:numerical` (1), `name:YieldController` (2), `name:YieldParameters` (2) |
| `credit.py` | 26 | Credit kind `operational`; live credit is the API execution's `credit_view`; closed view returned when present. | none |
| `decision_context.py` | 54 | Generic decision-context assembly (old-runner body), class `APIJobTaskContext`. | `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.is_scientific_source` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:FACT_MEANINGS` (1), `name:FACT_SOURCES` (1), `name:_references_in` (1), `table:runtime_actions` (2) |
| `decision_contracts.py` | 133 | Generic exchange-protocol support (old-runner body). | `self.workflow.contract_information_reply` (1), `self.workflow.decision_exchanges` (2), `self.workflow.journal` (1), `self.workflow.store` (2), `self.workflow.validate_contract_information` (2), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:apply_state_frame` (1), `name:bind_functions` (1), `name:composition_lookup_schema` (2), `name:CONTRACT_INFORMATION_OPERATIONS` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (1), `name:is_contract_information` (1), `name:model_snapshot` (1), `name:_recorded_action_generation_schema` (1), `name:_references_in` (1), `name:requested_contract_information` (1), `name:WorkflowError` (9), `table:runtime_model_calls` (1) |
| `decision_exchange.py` | 113 | Generic exchange loop (old-runner body). | `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (1), `self.workflow.execute` (1), `self.workflow.journal` (1), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.validate_contract_information` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:bind_functions` (1), `name:_category_yield_parameters` (1), `name:child_option_information` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (2), `name:lookup_attempts` (1), `name:model_snapshot` (1), `name:requested_contract_information` (1), `name:schema_failure_diagnostic` (2), `name:state_frame` (1), `name:yield_table` (1), `table:runtime_model_calls` (2) |
| `decision_provider.py` | 60 | Generic presentation-routing model completion (old-runner body). | `self.workflow.provider` (1), `self.workflow.specialist` (2), `import:runtime` (1), `import:providers` (2), `import:root.providers` (1), `name:_ORIGINAL_DECLARED_PRESENTATION` (1), `name:_ORIGINAL_MODEL_COMPLETE` (2), `name:_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION` (2), `name:_ORIGINAL_MODEL_INSTANCE_DICT` (3) |
| `episode.py` | 53 | Binding class: binding_path `.../execution_job_submission/api_job_execution`, commissioning_parent `.../execution_job_submission`, roles ('launch_api',), leaf (no child roles); permitted actions tool + wait for `api_service_assignment_v1`, else tool only; replaces default instructions; prompt renderer `present_api_context`. | `import:communication` (1) |
| `from_parent.py` | 90 | Assignment schema: anyOf the concrete request schemas of API resources; `prepare_assignment` requires parent role `launch`, kind match, BLAST launch-selection check against the original launch, masking/utility inputs, input versions and native database job inputs; `_check_parent_inputs` re-reads the parent's recorded launch assignment and validates the BLAST API parent request; `required_return_sources` returns () (differs from launch). | `import:communication` (1), `table:runtime_episodes` (1) |
| `goal.py` | 38 | `_with_selected_execution_task`: the scientific parent task view for this one assignment (only for ebi_hmmer API requests). | `import:communication` (1) |
| `hmmer_service.py` | 303 | Legacy EBI HMMER job executor (`hmmer_api` kind): own tables, prepare one protein FASTA query with pinned input identities, submit/observe, publish handoff, facts, credit (qualification `received_qualified_original_api_handoffs_and_own_canonical_result_records`), decision context (prepared request, job, completion), report validation, completion proof. | `table:api_execution_actions` (8), `table:api_execution_episodes` (3), `table:api_execution_observations` (1), `table:api_execution_preparations` (4) |
| `__init__.py` | 0 | Empty package marker. | none |
| `instructions.py` | 10 | Own goal text: "Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit." | `import:communication` (1) |
| `internal_summary.py` | 12 | Decision context: execution_assignment, execution_progress facts, the API execution's own decision context, plus selected execution task. | `import:communication` (1) |
| `parent_launch_contract.py` | 13 | `parent_launch_schema`: the commissioning launch assignment schema, used to read back the parent's original launch. | none |
| `parent_request_contracts.py` | 74 | `_permitted`, `_request_schema`, `_validate_request`, `_launch` (original launch validation incl. BLAST graded request), `_constraints`. | none |
| `parent_request_values.py` | 3 | LAUNCH_VERSION constant. | none |
| `presentation.py` | 59 | `present_api_context`: same renderer selection as the launch episode, under its own name. | `import:providers` (1), `import:receiver_prompt` (1), `name:apply_state_frame` (3), `name:DECISION_CONTEXT_VERSION` (1), `name:is_api_launch_context` (2), `name:is_published_scientific_context` (2), `name:_ordinary_runtime_receiver_context` (1), `name:render_api_launch_prompt` (1), `name:render_evolutionary_history_evidence_prompt` (1), `name:render_receiver_prompt` (1), `name:text_instructions` (1) |
| `protected_reference_access.py` | 100 | Protected reader installation and classification (same as launch). | `import:communication` (1) |
| `received_execution_records.py` | 106 | Report sources/facts for received roles and service probes (same family dispatch as launch). | `import:communication` (1) |
| `received_practical_state.py` | 14 | `_delegate` / `_practical_context` for practical resources. | `import:communication` (1) |
| `received_reference_access.py` | 109 | Received-reference resolution incl. masking/utility helpers. | `import:communication` (1) |
| `received_report_admission.py` | 94 | Received report validation and admitted references. | `import:communication` (1) |
| `received_result_records.py` | 145 | Result directories, recorded result actions, result body validation, received selection and handoffs. | `import:communication` (1), `import:episode_receipts` (1), `name:EpisodeReceipts` (1), `table:runtime_actions` (2), `table:runtime_episodes` (1), `table:runtime_receipt_inheritance` (2) |
| `received_result_values.py` | 9 | RESULT_PROVIDER, RESULTS_VERSION/SCHEMA, NATIVE_RESULT_ORIGIN. | none |
| `received_selector_contracts.py` | 80 | Native selector validation per family and windows. | none |
| `received_selector_values.py` | 7 | NATIVE_SELECTOR_SCHEMA. | none |
| `received_target_custody.py` | 52 | `_target` and `_context_target`: for role launch with a BLAST graded request, the submitted query digest must match the subject sequence; for resource roles the handoff assignment must equal this assignment. | `import:communication` (1) |
| `report_delivery.py` | 32 | Generic finish/report delivery (old-runner body). | `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:form_with_facts` (1), `name:Record` (2), `table:runtime_forms` (2) |
| `report_fields.py` | 61 | Report fact sources (same set as launch). | `import:communication` (2) |
| `report_reference_access.py` | 139 | Report reference resolution. | `import:communication` (2), `import:episode_bindings` (2), `name:reference_in_context` (2) |
| `resource_information.py` | 95 | Resource information, initial decision context, capabilities, resource tool contracts (same as launch). | none |
| `resource_operation_information.py` | 7 | `launch_operation_catalog` (`execution.capabilities`). | none |
| `result_operation_information.py` | 10 | `native_result_operation_catalog` (status / collect / read). | none |
| `schema_fields.py` | 6 | TEXT, OFFSET, LIMIT, FILE_LIMIT. | none |
| `scientific_inputs.py` | 14 | Masking/utility input validation and input versions. | none |
| `task_decision.py` | 154 | Generic model call (old-runner body) with execution expectations for role `launch_api`. | `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.contract_information_profile` (1), `self.workflow.decision_exchanges` (1), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.is_job_source` (3), `self.workflow.job_episodes` (4), `self.workflow.journal` (1), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.numerical_contracts` (1), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.provider` (2), `self.workflow.receipts` (4), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (5), `self.workflow.services` (1), `self.workflow.shared_information_context` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (2), `self.workflow.waiting_support` (1), `import:runtime` (2), `import:episode_work_report` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:_ASSIGNMENT_TRANSPORT` (1), `name:bind_functions` (1), `name:child_option_information` (1), `name:completed_action_reports` (2), `name:DECISION_EXCHANGE_PROTOCOL` (5), `name:instructional_model_context` (1), `name:_recorded_assignment_transport` (1), `name:requested_action_history` (2), `name:WorkflowError` (5), `table:runtime_model_calls` (5) |
| `task_instructions.py` | 36 | Instruction composition (old-runner body; own goal text replaces the default). | `workflow.binding_context` (1), `workflow.decision_protocol` (1), `workflow.is_job_source` (1), `workflow.job_episodes` (1), `workflow.knowledge` (1), `workflow.launch_instructions` (1), `workflow.native_event_information` (1), `workflow.permits_common_action` (3), `workflow.specialist` (1), `import:runtime_prompt` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:DECISION_EXCHANGE_PROTOCOL` (1), `name:INSTRUCTIONS` (3), `name:REASONING_COMMIT_REQUIREMENT` (1) |
| `task.py` | 230 | `APIJobTask`: next / apply_response / execute in one file; reason is never permitted so there is no empty-commit check; report grain `launch_api`. | `self.workflow.action_schema` (1), `self.workflow.automatic_score_updates` (1), `self.workflow.binding_context` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execute` (1), `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.last_observed_credit` (1), `self.workflow.next_return` (1), `self.workflow.pending_work` (1), `self.workflow.perform_selected_wait` (1), `self.workflow.permits_common_action` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (3), `self.workflow.selected` (3), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (8), `self.workflow.validate_report` (1), `import:runtime` (2), `import:providers` (1), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:AcquisitionError` (2), `name:ActionFailure` (1), `name:bind_functions` (1), `name:ContractError` (1), `name:ContractInformationError` (1), `name:_decode_recorded_action_response` (1), `name:EventTargetError` (2), `name:ModelCallError` (1), `name:observes_action_outcome` (1), `name:record_source_failure` (1), `name:ReportBoundaryError` (1), `name:ReportRedelivery` (2), `name:schema_failure_diagnostic` (1), `name:SourceEnd` (2), `name:_wait_target_feedback` (2), `name:WorkflowError` (2), `table:runtime_actions` (8), `table:runtime_episodes` (1), `table:runtime_model_calls` (2) |
| `task_state.py` | 117 | Generic task state (old-runner body). | `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `workflow.context` (1), `workflow.grains` (1), `import:runtime` (2), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:ActionLeaf` (1), `name:bind_functions` (1), `name:EFFECT_VERSION` (1), `name:Episode` (1), `name:interpretation_schema` (1), `name:Record` (1), `name:record_source_failure` (1), `table:runtime_actions` (5) |
| `terminal_receipt_state.py` | 70 | Own copy of `operation_catalog` (exec_command) and TerminalExecutionBehavior incl. `fact_sources`. | `import:communication` (1) |
| `to_parent.py` | 72 | Report facts: native empty sources, the API execution's facts, `execution_result_origin` null; report validation against recorded facts. | `import:communication` (2) |
| `waiting.py` | 9 | `suspension_changed` (detached backend suspension). | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| `yield_estimator.py` | 49 | Continuation for role launch_api: profile `launch_api:` + request class (e.g. `api_<service>[_<algorithm>][_<database>]_handoff`); estimator ends at a verified completion proof. | `import:communication` (1), `import:numerical` (1), `import:practical_yield` (2), `name:PracticalYieldEstimator` (2), `name:YieldController` (1), `name:YieldParameters` (1) |

## Carried over

Rows copied from `runs/carry_over/functions/` for this episode (every old function, class and method of its own files, none in a child folder or in tests). The first three columns are copied from that file; `carried as` is `machinery` (old runner, not carried), `episode function` (has a new place) or `episode function (unplaced)` (no place yet; reason given, listed in the blocked file). The job service is not provided: whatever needs it is BLOCKED-ON-JOB-SERVICE.

| old file | kind | name | carried as | new place or machinery reason |
|---|---|---|---|---|
| action_outcomes.py | function | _outcome | episode function | task.py `_outcome` (envelope adapted: status, event, feedback, job and result identities) |
| api_actions.py | class | APIApiActions | episode function | task.py `decide` / `action` (catalog through `job_access.read('launch_catalog', assignment)`) and tool `launch_operation` |
| api_actions.py | method | APIApiActions.catalog | episode function | task.py `decide`/`action`: `job_access.read('launch_catalog', assignment)` |
| api_actions.py | method | APIApiActions.execute | episode function | task.py tool `launch_operation` (`_check_parent_inputs` not carried) |
| api_service.py | class | APIJobService | episode function (unplaced) | class dissolves: its methods are placed or unplaced by row |
| api_service.py | method | APIJobService.__init__ | episode function (unplaced) | unplaced: builds the per-resource API services, the BV-BRC host and the returns hosts; service construction (BLOCKED-ON-JOB-SERVICE) |
| api_service.py | method | APIJobService._legacy_context | episode function (unplaced) | unplaced: version test of the service (`api_execution_assignment_v1`); `job_access` |
| api_service.py | method | APIJobService._context | machinery | run/role identity checks of the old runner (`api_execution_run_conflict`, `api_execution_role_required`); the service's `validate_assignment` is BLOCKED-ON-JOB-SERVICE |
| api_service.py | method | APIJobService.initialize | machinery | old runner initialization and per-episode manifest directory (file state); selection of UniProt/AppService context is the service's (BLOCKED-ON-JOB-SERVICE) |
| api_service.py | method | APIJobService.catalog | episode function | task.py `decide`/`action`: `job_access.read('launch_catalog', assignment)`; the service side is BLOCKED-ON-JOB-SERVICE |
| api_service.py | method | APIJobService.execute | episode function | task.py tool `launch_operation`: `job_access.launch_operation(...)` (BLOCKED-ON-JOB-SERVICE: `job_access`) |
| api_service.py | method | APIJobService._execute_locked | episode function | task.py tool `launch_operation` (the one-immutable-intent, single-original-submission and unknown-reply rules are the service's: BLOCKED-ON-JOB-SERVICE) |
| api_service.py | method | APIJobService._publish_handoff | episode function | task.py tool `launch_operation`: writes the handoff row with `ctx.store.table(JOB_LEDGER).put` (JOB_LEDGER declared in task.py) |
| api_service.py | method | APIJobService._handoff_source | episode function | task.py tool `launch_operation`: `ctx.store.artifact` + the handoff row (JOB_LEDGER declared in task.py) |
| api_service.py | method | APIJobService._index_result | episode function (unplaced) | unplaced: result-index files read by the results binding; service state (BLOCKED-ON-JOB-SERVICE: `job_access`) |
| api_service.py | method | APIJobService.facts | episode function | messages/internal_summary.py (handoff and result identities from the tool outcomes) and messages/final_to_parent.py `_facts` |
| api_service.py | method | APIJobService.credit_view | episode function | credit.py `credit` |
| api_service.py | method | APIJobService._completion | episode function | messages/internal_summary.py `completed`; yield_estimator.py target |
| api_service.py | method | APIJobService.completion_for_action | machinery | completion proof plumbing (replaced by the completion controller) |
| api_service.py | method | APIJobService.verify_completion | machinery | completion proof plumbing (replaced by the completion controller) |
| api_service.py | method | APIJobService.decision_context | episode function | messages/internal_summary.py `received_progress`, `completed`; task.py `decide` context |
| api_state.py | class | APIApiState | machinery | old runner initialization (local file sources, `_check_parent_inputs`, service initialize, per-resource delegate lookup); the commission is admitted by `ASSIGNMENT_FORM` |
| api_state.py | method | APIApiState.initialize | machinery | old runner initialization (local file sources, `_check_parent_inputs`, service initialize, per-resource delegate lookup); the commission is admitted by `ASSIGNMENT_FORM` |
| api_state.py | method | APIApiState._api_execution_for | machinery | old runner initialization (local file sources, `_check_parent_inputs`, service initialize, per-resource delegate lookup); the commission is admitted by `ASSIGNMENT_FORM` |
| appservice_publication.py | class | AppServicePublication | episode function (unplaced) | class dissolves; see rows |
| appservice_publication.py | method | AppServicePublication._put_content | episode function (unplaced) | unplaced: BV-BRC AppService bundle publication and grading inside the download action; needs `job_access` and library modules `appservice_publication_records/values`, `appservice_record_values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_publication.py | method | AppServicePublication.publication_inputs | episode function (unplaced) | unplaced: BV-BRC AppService bundle publication and grading inside the download action; needs `job_access` and library modules `appservice_publication_records/values`, `appservice_record_values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_publication.py | method | AppServicePublication._grade | episode function (unplaced) | unplaced: BV-BRC AppService bundle publication and grading inside the download action; needs `job_access` and library modules `appservice_publication_records/values`, `appservice_record_values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_publication.py | method | AppServicePublication.publish | episode function (unplaced) | unplaced: BV-BRC AppService bundle publication and grading inside the download action; needs `job_access` and library modules `appservice_publication_records/values`, `appservice_record_values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_submission.py | class | AppServiceSubmission | episode function (unplaced) | class dissolves; see rows |
| appservice_submission.py | method | AppServiceSubmission.__init__ | episode function (unplaced) | unplaced: BV-BRC AppService receipts, facts and completion; needs `job_access` and library `appservice_record_access/values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_submission.py | method | AppServiceSubmission._own_receipts | episode function (unplaced) | unplaced: BV-BRC AppService receipts, facts and completion; needs `job_access` and library `appservice_record_access/values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_submission.py | method | AppServiceSubmission.facts | episode function (unplaced) | unplaced: BV-BRC AppService receipts, facts and completion; needs `job_access` and library `appservice_record_access/values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_submission.py | method | AppServiceSubmission.completion | episode function (unplaced) | unplaced: BV-BRC AppService receipts, facts and completion; needs `job_access` and library `appservice_record_access/values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| appservice_submission.py | method | AppServiceSubmission.publish_acquisition | episode function (unplaced) | unplaced: BV-BRC AppService receipts, facts and completion; needs `job_access` and library `appservice_record_access/values` that are not in episode_support (BLOCKED-ON-JOB-SERVICE: the `job_access` service (the old executor) does not exist) |
| binding_record.py | class | APIBindingRecord | machinery | class dissolves |
| binding_record.py | method | APIBindingRecord.as_record | machinery | binding's own `as_record()` |
| closed_credit.py | class | APIClosedCredit | machinery | class dissolves |
| closed_credit.py | method | APIClosedCredit._closed_credit_carrier | machinery | closed-credit freeze over runtime_* tables, receipts and sqlite_master; the Episode's credit is what its controller last saw (`completion['credit']`) |
| closed_credit.py | method | APIClosedCredit._closed_credit_receipts | machinery | closed-credit freeze over runtime_* tables, receipts and sqlite_master; the Episode's credit is what its controller last saw (`completion['credit']`) |
| closed_credit.py | method | APIClosedCredit._closed_credit_value | machinery | closed-credit freeze over runtime_* tables, receipts and sqlite_master; the Episode's credit is what its controller last saw (`completion['credit']`) |
| closed_credit.py | method | APIClosedCredit._closed_credit_facts | machinery | closed-credit freeze over runtime_* tables, receipts and sqlite_master; the Episode's credit is what its controller last saw (`completion['credit']`) |
| closed_credit.py | method | APIClosedCredit._closed_operational_credit_view | machinery | closed-credit freeze over runtime_* tables, receipts and sqlite_master; the Episode's credit is what its controller last saw (`completion['credit']`) |
| completion.py | class | APICompletion | machinery | class dissolves |
| completion.py | method | APICompletion.completion_for_action | machinery | completion proof plumbing (`practical_completion_v1`, historical verdicts from runtime_observations); replaced by the completion controller whose target is `handoff_unit` (yield_estimator.py) |
| completion.py | method | APICompletion._closed_completion_verdict | machinery | completion proof plumbing (`practical_completion_v1`, historical verdicts from runtime_observations); replaced by the completion controller whose target is `handoff_unit` (yield_estimator.py) |
| completion.py | method | APICompletion.verify_completion | machinery | completion proof plumbing (`practical_completion_v1`, historical verdicts from runtime_observations); replaced by the completion controller whose target is `handoff_unit` (yield_estimator.py) |
| configuration.py | class | APIConfiguration | episode function | class dissolves |
| configuration.py | method | APIConfiguration.__init__ | episode function | values become settings and assignment fields (see file row) |
| credit.py | class | APICredit | episode function | class dissolves; see rows |
| credit.py | method | APICredit.credit_kind | machinery | `credit_kind` is deleted (README 3d); this episode's credit is operational |
| credit.py | method | APICredit.project_credit | episode function | credit.py `credit` (closed-view branch is machinery) |
| credit.py | method | APICredit._live_project_credit | episode function | credit.py `credit` (the `.applies(context)` calls of the results readers are no-ops here) |
| credit.py | method | APICredit.credit_view | episode function | credit.py `credit` |
| decision_context.py | class | APIJobTaskContext | episode function | class dissolves |
| decision_context.py | method | APIJobTaskContext.assemble_decision_context | episode function | task.py `decide` context + messages/internal_summary.py; generic old-runner context machinery |
| decision_context.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_contracts.py | class | APITaskDecisionContracts | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | method | APITaskDecisionContracts.interpretation_context | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | method | APITaskDecisionContracts.exchange_schema | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | method | APITaskDecisionContracts.exchange_response | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | method | APITaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | method | APITaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange loop (request_context contract validation, saved-exchange checks) |
| decision_contracts.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_exchange.py | class | APITaskDecisionExchange | machinery | decision-exchange loop (`exchange_decision`) |
| decision_exchange.py | method | APITaskDecisionExchange.exchange_decision | machinery | decision-exchange loop (`exchange_decision`) |
| decision_exchange.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_provider.py | class | APITaskDecisionProvider | machinery | provider patching/routing of the old model class |
| decision_provider.py | method | APITaskDecisionProvider.decision_completion | machinery | provider patching/routing of the old model class |
| episode.py | class | ExecutionEpisode | episode function | episode.py `ApiJobExecution` |
| episode.py | method | ExecutionEpisode.child_roles | episode function | task.py `CHILD_SLOTS = {}` |
| episode.py | method | ExecutionEpisode.allowed_children | episode function | task.py `CHILD_SLOTS = {}` |
| episode.py | method | ExecutionEpisode.permitted_common_actions | machinery | common-action permission (tool, wait); every unit here is a tool unit; the `wait` action is wait machinery (this episode has no child and no native event target) |
| from_parent.py | class | APIFromParent | episode function | class dissolves; see rows |
| from_parent.py | method | APIFromParent.required_return_sources | machinery | receiver return-source requirement (returned `()`); the child declares its fields in `RETURN_FORM` |
| from_parent.py | method | APIFromParent._check_parent_inputs | machinery | the child's re-validation of its commission against the parent's original launch request read from `runtime_episodes`; a wrong commission just fails |
| from_parent.py | method | APIFromParent.child_assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` |
| from_parent.py | method | APIFromParent.assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` |
| from_parent.py | method | APIFromParent.prepare_assignment | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (admission); the launch-role/kind/version/input checks are the commission checks that are not carried |
| from_parent.py | method | APIFromParent.initial_references | episode function | messages/read_from_parent.py: the `input_refs` field (record_refs) names the masking and utility input references; messages/internal_summary.py `_initial_identities` |
| goal.py | class | APIGoal | episode function | class dissolves; see rows |
| goal.py | method | APIGoal._with_selected_execution_task | episode function | task.py `_selected_execution_task` (the scientific question and tool info arrive in the commission message: read_from_parent.py) |
| hmmer_service.py | class | HMMERJobService | episode function (unplaced) | class dissolves: its methods are placed or unplaced by row |
| hmmer_service.py | method | HMMERJobService.__init__ | episode function (unplaced) | unplaced: creates the api_execution_* tables on store.db and binds the tool registry; service construction (BLOCKED-ON-JOB-SERVICE) |
| hmmer_service.py | method | HMMERJobService._assignment | machinery | run/role identity checks and the child's check of its own commission (resource binding, sequence operand) |
| hmmer_service.py | method | HMMERJobService.initialize | machinery | old runner initialization (api_execution_episodes table) |
| hmmer_service.py | method | HMMERJobService.catalog | episode function | task.py `decide`/`action`: `job_access.read('launch_catalog', assignment)` |
| hmmer_service.py | method | HMMERJobService._prepare | episode function (unplaced) | unplaced: pins the single protein query and its input identities (reads the Store); the tool hands the held inputs to the service (`job_access`) |
| hmmer_service.py | method | HMMERJobService._update_job | machinery | raw SQL on provider_jobs (store.db); the job state is the service's |
| hmmer_service.py | method | HMMERJobService._save_action | machinery | raw SQL on api_execution_actions (store.db); the unit's outcome is the system's |
| hmmer_service.py | method | HMMERJobService._http | episode function (unplaced) | unplaced: the retained single HTTP exchange (snapshot kept per operation key); `job_access` |
| hmmer_service.py | method | HMMERJobService._failure | episode function (unplaced) | unplaced: failure feedback with job state and submission outcome; the tool outcome carries the service's `feedback` and `submission_outcome` (`job_access`) |
| hmmer_service.py | method | HMMERJobService.execute | episode function | task.py tool `launch_operation`: `job_access.launch_operation(...)` (BLOCKED-ON-JOB-SERVICE) |
| hmmer_service.py | method | HMMERJobService._publish_handoff | episode function | task.py tool `launch_operation`: handoff row (JOB_LEDGER declared in task.py) |
| hmmer_service.py | method | HMMERJobService.facts | episode function | messages/internal_summary.py and messages/final_to_parent.py `_facts` |
| hmmer_service.py | method | HMMERJobService.credit_view | episode function | credit.py `credit` (same formula) |
| hmmer_service.py | method | HMMERJobService.decision_context | episode function | messages/internal_summary.py and task.py `decide` context (the prepared request and the job description are the service's outcome in `received_progress`) |
| hmmer_service.py | method | HMMERJobService.validate_report | episode function | messages/final_to_parent.py `validate_report` (the fact check; `validate_form` has no schema to check against) |
| hmmer_service.py | method | HMMERJobService._completion | episode function | messages/internal_summary.py `completed`; yield_estimator.py target |
| hmmer_service.py | method | HMMERJobService.completion_for_action | machinery | completion proof plumbing |
| hmmer_service.py | method | HMMERJobService.verify_completion | machinery | completion proof plumbing |
| instructions.py | class | APIInstructions | episode function | class dissolves |
| instructions.py | method | APIInstructions.instructions | episode function | task.py `INSTRUCTIONS` and `instructions` |
| internal_summary.py | class | APIInternalSummary | episode function | class dissolves |
| internal_summary.py | method | APIInternalSummary.decision_context | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| parent_launch_contract.py | function | parent_launch_schema | episode function (unplaced) | unplaced: the commissioning launch's own assignment schema (checked the child's commission against the parent's original request); a wrong commission just fails |
| parent_request_contracts.py | class | APIParentRequestContracts | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| parent_request_contracts.py | method | APIParentRequestContracts._permitted | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| parent_request_contracts.py | method | APIParentRequestContracts._request_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| parent_request_contracts.py | method | APIParentRequestContracts._validate_request | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| parent_request_contracts.py | method | APIParentRequestContracts._launch | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| parent_request_contracts.py | method | APIParentRequestContracts._constraints | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (the per-resource request schema); the checks against the parent's launch request and the resource constraints are not carried (a wrong commission fails) |
| presentation.py | function | present_api_context | episode function (unplaced) | task.py `decide` builds `ModelRequest.context` as a mapping; unplaced: the prompt text renderers of the old shared root (`render_api_launch_prompt`, `render_selected_execution_prompt`, `render_hpc_prompt`, `render_monitor_prompt`, `render_receiver_prompt`) |
| protected_reference_access.py | class | ProtectedReferenceAccess | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._install_protected_reference_readers | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._protein_reference_access | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._fluorescence_reference_access | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._expression_nmf_reference_access | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._atac_reference_access | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| protected_reference_access.py | method | ProtectedReferenceAccess._chromatin_reference_access | episode function (unplaced) | unplaced: protected read authority for protein, fluorescence, expression NMF, ATAC and chromatin references of the results role; this episode (role launch_api) has no results role and the modules (`native_protein_structure_results`, `fluorescence_returns`, ...) are not in episode_support under these names |
| received_execution_records.py | class | APIReceivedExecutionRecords | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords._has_appservice | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords._has_uniprot | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords._appservice_sources | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords._forwards_bvbrc_reports | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords.received_report_sources | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords.received_report_facts | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_execution_records.py | method | APIReceivedExecutionRecords.received_report_closure_facts | episode function (unplaced) | unplaced: which execution fact sources are forwarded to annotation/evolutionary_history receivers; a receiver's function (the parent's `read_from_child`), not this episode's |
| received_practical_state.py | class | APIReceivedPracticalState | machinery | delegate to the practical (local/hpc) TerminalExecutionBehavior; not used for an API resource |
| received_practical_state.py | method | APIReceivedPracticalState._delegate | machinery | delegate to the practical (local/hpc) TerminalExecutionBehavior; not used for an API resource |
| received_practical_state.py | method | APIReceivedPracticalState._practical_context | machinery | delegate to the practical (local/hpc) TerminalExecutionBehavior; not used for an API resource |
| received_reference_access.py | class | APIReceivedExecutionRecordsReferenceAccess | episode function (unplaced) | unplaced: `resolve_received_reference` of the results role (masking/utility/other received references); receivers' function, system custody replaces reference resolution |
| received_reference_access.py | method | APIReceivedExecutionRecordsReferenceAccess._masking_reference_access | episode function (unplaced) | unplaced: `resolve_received_reference` of the results role (masking/utility/other received references); receivers' function, system custody replaces reference resolution |
| received_reference_access.py | method | APIReceivedExecutionRecordsReferenceAccess._utility_reference_access | episode function (unplaced) | unplaced: `resolve_received_reference` of the results role (masking/utility/other received references); receivers' function, system custody replaces reference resolution |
| received_reference_access.py | method | APIReceivedExecutionRecordsReferenceAccess.resolve_received_reference | episode function (unplaced) | unplaced: `resolve_received_reference` of the results role (masking/utility/other received references); receivers' function, system custody replaces reference resolution |
| received_report_admission.py | class | APIReceivedExecutionRecordsAdmission | machinery | `validate_received_report`, `received_form_references`: admission of a child's report (the system admits against the child's form); this episode has no child |
| received_report_admission.py | method | APIReceivedExecutionRecordsAdmission.validate_received_report | machinery | `validate_received_report`, `received_form_references`: admission of a child's report (the system admits against the child's form); this episode has no child |
| received_report_admission.py | method | APIReceivedExecutionRecordsAdmission.received_form_references | machinery | `validate_received_report`, `received_form_references`: admission of a child's report (the system admits against the child's form); this episode has no child |
| received_result_records.py | class | APIReceivedResultRecords | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._result_directory | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._selected_result_action | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._validate_result_body | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._read_result | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._selection | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_result_records.py | method | APIReceivedResultRecords._received | episode function (unplaced) | unplaced: results-role records (result directory, selected result action, result body validation, received handoffs/results); belongs to `execution_result_acquisition`, not to this launch episode; reads runtime_* tables (machinery) |
| received_selector_contracts.py | class | APIReceivedSelectorContracts | episode function (unplaced) | unplaced: result selector validation per native target family (results role); belongs to `execution_result_acquisition` |
| received_selector_contracts.py | method | APIReceivedSelectorContracts._masking_selector | episode function (unplaced) | unplaced: result selector validation per native target family (results role); belongs to `execution_result_acquisition` |
| received_selector_contracts.py | method | APIReceivedSelectorContracts._utility_selector | episode function (unplaced) | unplaced: result selector validation per native target family (results role); belongs to `execution_result_acquisition` |
| received_selector_contracts.py | method | APIReceivedSelectorContracts._selector | episode function (unplaced) | unplaced: result selector validation per native target family (results role); belongs to `execution_result_acquisition` |
| received_selector_contracts.py | method | APIReceivedSelectorContracts._windows | episode function (unplaced) | unplaced: result selector validation per native target family (results role); belongs to `execution_result_acquisition` |
| received_target_custody.py | class | APIReceivedTargetCustody | machinery | authenticate the handed-off target for the results role (receipts/custody bookkeeping) |
| received_target_custody.py | method | APIReceivedTargetCustody._retained_masking_target | machinery | authenticate the handed-off target for the results role (receipts/custody bookkeeping) |
| received_target_custody.py | method | APIReceivedTargetCustody._retained_utility_target | machinery | authenticate the handed-off target for the results role (receipts/custody bookkeeping) |
| received_target_custody.py | method | APIReceivedTargetCustody._target | machinery | authenticate the handed-off target for the results role (receipts/custody bookkeeping) |
| received_target_custody.py | method | APIReceivedTargetCustody._context_target | machinery | authenticate the handed-off target for the results role (receipts/custody bookkeeping) |
| report_delivery.py | class | APIReportDelivery | machinery | class dissolves |
| report_delivery.py | method | APIReportDelivery.finish | machinery | form filled from saved interpretations and facts, `runtime_forms`, `release`; replaced by `final_to_parent` |
| report_delivery.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| report_fields.py | class | APIToParentFields | episode function | class dissolves |
| report_fields.py | method | APIToParentFields.fact_sources | episode function | messages/final_to_parent.py `RETURN_FORM` |
| report_reference_access.py | class | APIToParentReferenceAccess | machinery | `resolve(context, reference, namespace)` for the parent's report form references (report_form machinery; custody replaces reference resolution) |
| report_reference_access.py | method | APIToParentReferenceAccess.resolve | machinery | `resolve(context, reference, namespace)` for the parent's report form references (report_form machinery; custody replaces reference resolution) |
| resource_information.py | class | APIResourceInformation | episode function | class dissolves; see rows |
| resource_information.py | method | APIResourceInformation._resource_information | episode function | task.py `_resource_information` |
| resource_information.py | method | APIResourceInformation.initial_decision_context | episode function | task.py `decide` context (`execution_resource_capabilities`, `execution_initial_information`); `received_bvbrc_values` and `received_blast_jobs` are receivers' views (unplaced) |
| resource_information.py | method | APIResourceInformation.capabilities | episode function | task.py `_resource_information` (`job_access.read('capabilities', resource_id)`) |
| resource_information.py | method | APIResourceInformation.resource_tool_contracts | episode function (unplaced) | unplaced: tool contracts with commission routes for the parent's catalog (declares other episodes' tools); the parent writes its own |
| resource_operation_information.py | function | launch_operation_catalog | episode function (unplaced) | unplaced: `execution.capabilities` operation of the local/hpc terminal catalog; not offered by an API resource |
| result_operation_information.py | function | native_result_operation_catalog | episode function (unplaced) | unplaced: `execution.results.status/collect/read` catalog of the results role; belongs to `execution_result_acquisition` |
| scientific_inputs.py | class | APIScientificInputs | machinery | the child's check of its own commission against the parent's request (`_masking_inputs`, `_utility_inputs`, pinned `immutable_input_versions`); a wrong commission just fails |
| scientific_inputs.py | method | APIScientificInputs._masking_inputs | machinery | the child's check of its own commission against the parent's request (`_masking_inputs`, `_utility_inputs`, pinned `immutable_input_versions`); a wrong commission just fails |
| scientific_inputs.py | method | APIScientificInputs._utility_inputs | machinery | the child's check of its own commission against the parent's request (`_masking_inputs`, `_utility_inputs`, pinned `immutable_input_versions`); a wrong commission just fails |
| scientific_inputs.py | method | APIScientificInputs._versions | machinery | the child's check of its own commission against the parent's request (`_masking_inputs`, `_utility_inputs`, pinned `immutable_input_versions`); a wrong commission just fails |
| task.py | class | APIJobTask | episode function | class dissolves; see rows |
| task.py | method | APIJobTask.next | episode function | task.py `decide` (the restore, replay, completions and SourceEnd on source failure are machinery; a model failure ends the run) |
| task.py | method | APIJobTask.apply_response | episode function | task.py `action` (selection validated against the catalog; the report_update admission and the reads.map repair hints are not carried: no report update here) |
| task.py | method | APIJobTask.execute | episode function | task.py tool `launch_operation` (receive_outcome, automatic score updates, credit and controller input staging are the system's; a failed outcome is returned, not raised) |
| task.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task_decision.py | class | APITaskDecision | episode function | class dissolves; see rows |
| task_decision.py | method | APITaskDecision.call | episode function | task.py `decide` |
| task_decision.py | method | APITaskDecision.instructions | episode function | task.py `instructions` |
| task_decision.py | method | APITaskDecision.conversation_key | machinery | conversation state across model calls (deleted: every request carries the full context) |
| task_decision.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task_instructions.py | function | instructions | episode function | task.py `instructions` (specialist text, tool knowledge, launch library); the wait/redelivery/native-event/exchange-protocol text is not carried |
| task_instructions.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task_state.py | class | APITaskState | machinery | class dissolves (episode-source state) |
| task_state.py | method | APITaskState.__init__ | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | method | APITaskState.bind_execution_context | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | method | APITaskState.record_execution_failure | machinery | failed action still gets credit and controller input: now a returned tool outcome (task.py `launch_operation`) |
| task_state.py | method | APITaskState.restore_checkpoint | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | method | APITaskState.restore | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | method | APITaskState.record_effect | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | method | APITaskState.checkpoint | machinery | episode-source state, `record_execution_failure`, restore/checkpoint/record_effect (checkpoint/restore); a failed action is now a returned tool outcome |
| task_state.py | function | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| terminal_receipt_state.py | function | operation_catalog | episode function (unplaced) | unplaced: local/hpc terminal operation catalog (`local_job_execution`, `hpc_job_execution`) |
| terminal_receipt_state.py | class | TerminalExecutionBehavior | episode function (unplaced) | unplaced: local/hpc executor (`local_job_execution`, `hpc_job_execution`) |
| terminal_receipt_state.py | method | TerminalExecutionBehavior.__init__ | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior._operations | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior._assignment | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior._state_directory | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior.initialize | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior.state | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior.fact_sources | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| terminal_receipt_state.py | method | TerminalExecutionBehavior.resolve | episode function (unplaced) | unplaced: TerminalExecutionBehavior for local/hpc resources (instruction-led exec_command executor); belongs to `local_job_execution` and `hpc_job_execution` |
| to_parent.py | class | APIToParent | episode function | class dissolves; see rows |
| to_parent.py | method | APIToParent.facts | episode function | messages/final_to_parent.py `_facts` (closed-credit facts are machinery) |
| to_parent.py | method | APIToParent._live_facts | episode function | messages/final_to_parent.py `_facts` (empty native family sources; `execution_result_origin` None cannot be returned: no null type) |
| to_parent.py | method | APIToParent.validate_report | episode function | messages/final_to_parent.py `validate_report` (called by `final_to_parent` before returning); the masking/utility/UniProt validators of received reports and the JSON-schema `validate_form` have no counterpart: no child, no schema |
| waiting.py | class | APIWaiting | machinery | class dissolves |
| waiting.py | method | APIWaiting.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | class dissolves |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py `_request_yield_class` (api branch; the practical branch is not reachable for an API resource) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py `_task_yield_profile` |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py `yield_controller` (`PracticalYieldEstimator` -> `CompletionYieldController`) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | `PracticalYieldEstimator(verify_completion)` plumbing (README 7b) |
