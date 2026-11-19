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
| api_service.py | method | APIJobService._publish_handoff | episode function | task.py tool `launch_operation`: writes the handoff row with `ctx.store.table(JOB_LEDGER).put` (BLOCKED-ON-JOB-SERVICE: job record kind) |
| api_service.py | method | APIJobService._handoff_source | episode function | task.py tool `launch_operation`: `ctx.store.artifact` + the handoff row (BLOCKED-ON-JOB-SERVICE: job record kind) |
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
| hmmer_service.py | method | HMMERJobService._publish_handoff | episode function | task.py tool `launch_operation`: handoff row (BLOCKED-ON-JOB-SERVICE: job record kind) |
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

Folder-level note: the old files `api_job_binding.py`, `runtime_source.py`, `runtime_credit.py`, `appservice_source.py` (hook-era port) were deleted; `configuration.py` was deleted afterwards (nothing imports it). The old `wait` action (wait/suspension machinery, `waiting.py`) is not carried.
