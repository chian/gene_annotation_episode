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
