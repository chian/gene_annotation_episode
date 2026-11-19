# a104/evolutionary_history_evidence/execution_job_submission/api_job_execution — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/execution_job_submission/api_job_execution/`
(53 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` not read). Nothing from
the old shared root was read; the API services it builds (`api_services.build_service`, `library.api_record_access`,
`library.hmmer_record_access`, the AppService record libraries, BV-BRC hosts) are named only by what this episode asks
of them. Most files are copies of the launch parent's (marked "copy" below); the episode's own work is in
`api_service.py`, `hmmer_service.py`, `appservice_*.py`, `instructions.py`, `from_parent.py`, `episode.py`, `task.py`,
`credit.py`, `completion.py`, `to_parent.py`, `yield_estimator.py`.

Old binding: class `ExecutionEpisode`, `binding_path =
'evolutionary_history_evidence/execution_job_submission/api_job_execution'`, `commissioning_parent =
'evolutionary_history_evidence/execution_job_submission'`, old role `launch_api`, `entry_roles = ()` (never an entry),
`replaces_default_instructions = True`, version `execution_episode_v1`. Decision source: `APIJobTask`. Prompt
renderer: `present_api_context` (same body as the parent's; API launch contexts go to `render_api_launch_prompt`).

## What this episode is for

It carries out one concrete API request that its launch parent chose, one service operation per turn, until a usable
handoff exists. In its own words (`instructions.py`, the whole text; `{service}` is the request's service):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair
> from the actual available operations and received outcomes. Distinguish an immediate returned response from a
> service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a
> missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff
> from recorded service facts. The configured controller governs continuation; verified original handoff completion
> gives exact zero future credit.

## Task and instructions

- Permitted actions (`episode.py`): `tool` and `wait` when the request is `api_service_assignment_v1` (a service job
  continuing remotely); otherwise `tool` only. No reason, no children, no redelivery.
- Instructions: the text above replaces the defaults (`task_instructions.py` composer: tool knowledge, launch library,
  redelivery paragraph, wait and native-event paragraphs when wait is permitted, exchange-protocol history guidance).
- `task.py` carries its own admission without the reasoning-commit branch (every selection is checked against the
  selection schema) and the report update is admitted for grain `launch_api`.

## What it reads from its parent's assignment

`from_parent.py`, `parent_request_contracts.py`:

- Assignment form: `anyOf` the request schemas of the configured API resources, each with `resource_id` fixed and
  required; `{'not': {}}` when none is configured.
- `prepare_assignment`: request validated, then validated by the API executor with the scope; its resource must be of
  kind `api`; the parent must be `launch`; the parent's own launch assignment is re-validated and supplies the BLAST
  launch selection check and `immutable_input_versions`; masking/utility inputs and native BLAST database inputs are
  validated.
- `_check_parent_inputs` repeats this before initialize and before every execution, re-reading the parent launch
  assignment from the old `runtime_episodes` table by path (and the BLAST API parent-request check); it fails with
  `execution_original_launch_assignment_unavailable` if missing.
- Required returns: none.

## Children

None (`child_roles` and `allowed_children` return `()`).

## Decision state and what it shows the model

- Context: the shared decision-context text; execution expectations captured for `launch_api`.
- Own block (`internal_summary.py`): `execution_assignment`, `execution_progress` (its facts), plus the API service's
  view: `api_service`, `api_request`, `api_received_progress` (latest state, kind, facts and failure code per
  operation name), `api_execution_completed`. For the legacy HMMER service: `api_execution_assignment`,
  `api_execution_prepared_request`, `api_execution_job`, `api_execution_completion`.
- `goal.py` holds `_with_selected_execution_task` for this single request (the parent's per-request view).

## Tools

`api_actions.py`, `api_service.py`, `hmmer_service.py`:

- Catalog: the service's `launch_catalog` for the request; legacy EBI HMMER: `api.hmmer.prepare`,
  `api.hmmer.databases`, `api.hmmer.submit`, `api.hmmer.status`, `api.hmmer.check_handoff`.
- Execution: per operation key a lock and immutable `intent` / `snapshot` / `event` / `outcome` files; a reused key
  for different work is invalid; a second remote-mutating submission is refused unless the earlier one was
  `not_sent`; a missing reply without a saved event is `api_operation_response_unknown` with unknown submission
  outcome; a handoff-ready event publishes a handoff source with its receipt. Errors keep the provider response.
  BV-BRC AppService requests go through `appservice_submission.py` / `appservice_publication.py` (publication
  inputs, adapter grading inside the download action, bundle publication; completed when the requested form is
  satisfied, otherwise partial with the first missing reason).
- Legacy HMMER keeps its own tables (`api_execution_episodes`, `api_execution_preparations`,
  `api_execution_actions`, `api_execution_observations`) and the provider job rows (`provider_jobs`,
  `provider_job_failures`).

## Credit

`credit.py`, `api_service.py`: kind `operational`; closed view first. Live: new handoffs counted by
(`resource_id`, `execution_id`) beyond the initial ones × `handoff_unit` plus new result identities ×
`acquired_record_unit`; binding marks `scientific_credit: False`, `monitoring_credit: False`. Completion: the latest
completed outcome with a receipt gives `practical_completion_v1`, endpoint `usable_handoff` (AppService: from its
TaskHandoff receipt).

## Continuation

`yield_estimator.py`: profile `task_yield_profiles['launch_api:<request class>']` (cutoff, parameters); accumulation
controller whose estimate comes from the practical estimator (verified completion → exact zero future credit).

## What it reports to its parent

`to_parent.py`: the API service's facts (`execution_handoff_refs`, `execution_result_refs`, BV-BRC and UniProt facts,
AppService facts, `execution_blast_hsps`, `execution_completed`) over empty native families, and
`execution_result_origin: null`; plus the closed credit capture. Return fields must equal these facts.

## Differences from similar episodes

- Versus `hpc_job_execution`: allows `wait` for remote service jobs; its own service-specific instruction text
  (HPC uses the execution-agent text); credit counts handoffs and acquired result identities (HPC uses the practical
  receipt state); BLAST launch-selection checks against the parent launch.
- Versus the launch parent: no children, no reason; accumulation with a practical estimator instead of bounded
  launch yield; no required returns.

## Files

Name abbreviations: `wf.X` = old `self.workflow.X` / `source.workflow.X` / `workflow.X`; `wf(self).X` = a parent-runtime function bound into the old workflow namespace using `self.X`; `BC.X` = old `BindingContext` field; `services.X` = old binding services; `SelectionView.X` = old selection view; `tbl:` = old journal/receipt/provider table; `imp:` = import from old `root.a104.<module>`; `lrf.` = `library.live_runtime_functions` rebinding into the old runtime namespace; bare names are old runtime/provider/numerical names. Counts are uses in that file. Full rows: `runs/carry_over/calls/a104_01.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `action_outcomes.py` | 5 | outcome envelope (copy of the launch parent's) | none |
| `api_actions.py` | 17 | tool catalog and execution delegated to the API service for this request after checking parent inputs | imp:communication×1 |
| `api_service.py` | 296 | APIJobService: builds per-resource API services (or the legacy HMMER service); per-operation lock and intent/snapshot/event/outcome files; refuses a second remote-mutating submission; publishes the usable handoff source; facts, credit view (new handoffs by resource and execution id plus new result identities), completion proof, decision context | BC.assignment×7, BC.episode_id×7, BC.request×4, BC.role×1, BC.run_id×1, BC.scope×10, imp:api_selected_effects×1, imp:api_services×1, imp:blast_result_views×1, imp:bvbrc_data_host×2, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:library.api_record_access×1, imp:library.api_record_values×1, imp:library.bvbrc_proteome_returns×1 |
| `api_state.py` | 14 | initialize through the API service after checking parent inputs | BC.assignment×1, imp:communication×1 |
| `appservice_publication.py` | 87 | BV-BRC AppService acquisition publication: publication inputs, adapter grading inside the download action, bundle publication, completion when the requested form is satisfied | BC.assignment×2, BC.episode_id×1, BC.run_id×1, imp:library.api_record_values×1, imp:library.appservice_publication_records×1, imp:library.appservice_publication_values×1 |
| `appservice_submission.py` | 50 | BV-BRC AppService host: own receipts, facts (handoffs, support refs, results, homology/phylogeny/proteome facts), completion from TaskHandoff | BC.assignment×1, BC.episode_id×1, BC.request×1, BC.scope×1, imp:library.appservice_record_access×1, imp:library.appservice_record_values×1 |
| `binding_record.py` | 9 | binding identity with binding_id .../api_job_execution | none |
| `binding_roles.py` | 6 | roles and kinds (copy) | none |
| `closed_credit.py` | 122 | closed operational credit (copy) | BC.as_record×2, BC.episode_id×8, BC.role×1, imp:communication×1, imp:episode_receipts×1, imp:episode_return_records×3, imp:execution_contracts×2, EpisodeReceipts×2, EpisodeReturnRecords×2, tbl:runtime_episodes×2, tbl:runtime_forms×3, tbl:runtime_observations×1, tbl:runtime_receipt_inheritance×2, tbl:runtime_record_receipts×2 |
| `closed_credit_values.py` | 3 | closed credit fact name | none |
| `completion.py` | 55 | completion through the API service; verification by the API service | BC.assignment×1, BC.episode_id×4, imp:communication×1, imp:episode_return_records×1, imp:execution_contracts×1, imp:method_loop.identities×1, imp:numerical×1, imp:practical_execution_records×1, imp:practical_yield×1, ESTIMATOR_VERSION×2, NumericBand×2, UnitRef×2, tbl:runtime_observations×1 |
| `configuration.py` | 76 | constructor (copy) with APIJobService as the API executor | imp:a104_execution_bindings×4, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:evolutionary_history_evidence.execution_progress_assessment.api_observer×1, imp:execution_contracts×1, imp:execution_progress×1, imp:local_file_capture_results×1, imp:numerical×1, YieldController×3, YieldParameters×3 |
| `credit.py` | 26 | operational credit from the API service's credit view (closed view first) | none |
| `decision_context.py` | 54 | decision context assembly (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, FACT_MEANINGS×1, FACT_SOURCES×1, _references_in×1, SelectionView.child_reports×2, SelectionView.controller_state×1, SelectionView.model_inputs×1, tbl:runtime_actions×2, wf.binding_context×2, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| `decision_contracts.py` | 133 | exchange envelope and replay validation (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, apply_state_frame×1, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×1, is_contract_information×1, model_snapshot×1, _references_in×1, requested_contract_information×1, WorkflowError×9, tbl:runtime_model_calls×1, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.store×2, wf.validate_contract_information×2 |
| `decision_exchange.py` | 113 | request_context exchange loop (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _category_yield_parameters×1, child_option_information×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×2, lookup_attempts×1, model_snapshot×1, requested_contract_information×1, state_frame×1, yield_table×1, tbl:runtime_model_calls×2, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.validate_contract_information×1 |
| `decision_provider.py` | 60 | provider routing (shared text) | imp:providers×2, imp:runtime×1, imp:root.providers×1, _ORIGINAL_DECLARED_PRESENTATION×2, _ORIGINAL_MODEL_COMPLETE×3, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×3, _ORIGINAL_MODEL_INSTANCE_DICT×4, wf.provider×1, wf.specialist×2 |
| `episode.py` | 53 | assembles the API binding; binding_path .../api_job_execution, commissioning_parent .../execution_job_submission, roles (launch_api,), entry_roles (); no children; actions tool and wait for api_service_assignment_v1, otherwise tool; prompt renderer present_api_context | BC.assignment×1, BC.role×1, imp:a104_homology_execution×1, imp:communication×1 |
| `from_parent.py` | 90 | assignment: anyOf API request schemas with resource_id; prepare_assignment validates with scope, kind api, parent must be launch, original launch, BLAST launch selection, inputs, versions; _check_parent_inputs re-reads the parent launch assignment; no required returns | BC.assignment×8, BC.path×4, BC.role×5, BC.scope×2, imp:communication×1, imp:execution_contracts×2, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_publication×3, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_publication×3, services.annotation_task_required×1, tbl:runtime_episodes×1 |
| `goal.py` | 38 | selected_execution_task view for this single request (no goal text here) | BC.assignment×1, imp:communication×1, imp:native_profile_presentation×1, services.scientific_parent_task×1 |
| `hmmer_service.py` | 303 | legacy EBI HMMER service: own tables, prepare/databases/submit/status/check_handoff, provider job rows, failure feedback, handoff publication, facts, credit, completion | BC.assignment×10, BC.episode_id×15, BC.role×1, BC.run_id×2, BC.scope×12, imp:api_error_feedback×1, imp:domain×1, imp:episode_input_versions×1, imp:library.hmmer_record_access×1, imp:library.hmmer_record_values×1, tbl:api_execution_actions×8, tbl:api_execution_episodes×3, tbl:api_execution_observations×1, tbl:api_execution_preparations×4, tbl:provider_job_failures×2, tbl:provider_jobs×7 |
| `instructions.py` | 10 | the goal/instructions text for this episode (service-specific) | BC.assignment×1, imp:communication×1 |
| `internal_summary.py` | 12 | own block: execution_assignment, execution_progress, plus the API service's decision context | BC.assignment×1, imp:communication×1 |
| `parent_request_contracts.py` | 73 | _permitted, request schema, _validate_request, _launch, constraints (copy of the launch parent's launch_requests) | imp:a104_execution_bindings×2, imp:a104_homology_execution×2, imp:execution_contracts×1, imp:practical_execution_operations×1, imp:practical_execution_records×3 |
| `parent_request_values.py` | 3 | LAUNCH_VERSION constant | none |
| `presentation.py` | 59 | presentation (copy, renamed present_api_context) | imp:evolutionary_history_evidence_prompt×2, imp:library.hpc_prompt×1, imp:library.monitor_prompt×1, imp:native_profile_presentation×1, imp:providers×1, imp:receiver_prompt×1, apply_state_frame×3, DECISION_CONTEXT_VERSION×1, is_api_launch_context×2, is_published_scientific_context×2, _ordinary_runtime_receiver_context×1, render_api_launch_prompt×1, render_evolutionary_history_evidence_prompt×1, text_instructions×1 |
| `protected_reference_access.py` | 100 | protected readers (copy) | BC.assignment×4, imp:communication×1, imp:library.fluorescence_returns×1, imp:library.native_fluorescence_results×1, imp:library.native_protein_structure_results×1, imp:library.native_protein_structure_returns×1, imp:library.protein_structure_operands×1 |
| `received_execution_records.py` | 106 | received report sources/facts (copy of received_parent_records) | BC.request×2, BC.role×10, imp:a104_homology_execution×1, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `received_practical_state.py` | 14 | _delegate and practical context (copy) | BC.assignment×1, BC.role×1, imp:communication×1 |
| `received_reference_access.py` | 109 | resolve_received_reference (copy) | BC.role×9, imp:a104_homology_execution×1, imp:blast_utility_result_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:library.bvbrc_proteome_returns×1, imp:sequence_masking_result_views×1 |
| `received_report_admission.py` | 94 | validate_received_report, received_form_references (copy) | BC.role×1, imp:a104_homology_execution×1, imp:communication×1, imp:hmmer_native_result_views×1 |
| `received_result_records.py` | 145 | result directory, selected action identity, result body validation, _read_result (copies) | BC.assignment×2, BC.episode_id×9, BC.role×1, BC.run_id×2, BC.scope×3, imp:communication×1, imp:domain×1, imp:episode_receipts×1, imp:execution_contracts×2, imp:local_file_capture_results×1, imp:practical_execution_state×2, EpisodeReceipts×2, services.record_selection×1, tbl:runtime_actions×2, tbl:runtime_episodes×1, tbl:runtime_receipt_inheritance×2 |
| `received_result_values.py` | 9 | result constants (copy) | imp:execution_contracts×1 |
| `received_selector_contracts.py` | 80 | selector validation (copy) | imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×1, imp:native_blast_acquisition×1, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_views×1, imp:native_blast_masking_acquisition×1, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_views×1, imp:native_blast_utility_acquisition×1, imp:native_hmmer_acquisition×1, imp:native_hmmer_preparation_acquisition×1, imp:practical_execution_operations×1, imp:sequence_masking_result_views×1 |
| `received_selector_values.py` | 7 | native selector schema (copy) | imp:execution_contracts×1 |
| `received_target_custody.py` | 52 | target custody (copy) | BC.assignment×3, BC.role×3, BC.scope×6, imp:a104_homology_execution×1, imp:communication×1, imp:execution_contracts×2 |
| `report_delivery.py` | 32 | finish (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, form_with_facts×1, tbl:runtime_forms×2, wf.binding_context×2, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| `report_fields.py` | 61 | fact_sources (copy) | imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×2, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:native_hmmer_acquisition×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `report_reference_access.py` | 139 | resolve (copy) | BC.role×13, BC.scope×4, imp:a104_homology_execution×2, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×2, imp:episode_bindings×2, imp:execution_contracts×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, reference_in_context×4 |
| `resource_information.py` | 95 | resource information and initial decision context (copy) | BC.role×1, imp:a104_execution_bindings×3, imp:execution_contracts×1, imp:library.bvbrc_proteome_tool_info×1 |
| `resource_operation_information.py` | 7 | execution.capabilities catalog (copy) | imp:execution_contracts×1 |
| `result_operation_information.py` | 10 | native result operation catalog (copy) | imp:execution_contracts×1 |
| `schema_fields.py` | 6 | schema constants (copy) | none |
| `scientific_inputs.py` | 14 | input validation (copy) | imp:library.execution_input_versions×1 |
| `task.py` | 230 | decision source with its own action admission (no reasoning-commit branch; grain launch_api) and execution | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:providers×1, imp:read_mapping×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionFailure×1, _decode_recorded_action_response×1, ModelCallError×2, observes_action_outcome×1, record_source_failure×2, ReportRedelivery×2, SourceEnd×2, _wait_target_feedback×2, WorkflowError×2, SelectionView.units_consumed×4, tbl:runtime_actions×8, tbl:runtime_episodes×1, tbl:runtime_model_calls×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×2, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×1, wf.store×8, wf.validate_report×1 |
| `task_decision.py` | 154 | decision call (execution expectations for launch_api) | imp:root.a104×1, imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _ASSIGNMENT_TRANSPORT×1, child_option_information×1, completed_action_reports×3, DECISION_EXCHANGE_PROTOCOL×5, instructional_model_context×1, _recorded_assignment_transport×1, requested_action_history×3, WorkflowError×5, tbl:runtime_model_calls×5, wf.available_child_roles×1, wf.binding_context×4, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.episode_bindings×1, wf.execution_expectations×1, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×3, wf.job_episodes×4, wf.journal×1, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.numerical_contracts×1, wf.pending_work×1, wf.permits_common_action×1, wf.provider×2, wf.receipts×4, wf.resource_context×1, wf.resource_estimator×5, wf.services×1, wf.shared_information_context×1, wf.store×2, wf.uses_received_record_context×2, wf.validate_contract_information×2, wf.waiting_support×1 |
| `task_instructions.py` | 36 | instruction composer (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime_prompt×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, DECISION_EXCHANGE_PROTOCOL×1, REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×2, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| `task_state.py` | 117 | source state (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionLeaf×1, EFFECT_VERSION×1, Episode.identity×1, record_source_failure×2, tbl:runtime_actions×5, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2 |
| `terminal_receipt_state.py` | 70 | terminal execution behaviour (copy of terminal_validation without assess/report parts) | BC.assignment×1, BC.episode_id×4, BC.role×1, BC.run_id×3, imp:acquisition×1, imp:communication×1, imp:domain×1, imp:library.native_terminal_transport×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:practical_receipt_information×1, imp:terminal_scientific_evidence×1 |
| `to_parent.py` | 72 | facts from the API service plus empty native families, execution_result_origin null | imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `waiting.py` | 9 | suspension notice | wf.execution_backend×1, wf.execution_handle×2 |
| `yield_estimator.py` | 49 | task profile key launch_api:<request class>; accumulation controller with the practical (verified completion) estimator | BC.assignment×1, BC.role×1, imp:communication×1, imp:numerical×1, imp:practical_yield×2, PracticalYieldEstimator×4, YieldController×2, YieldParameters×2 |
