# A107 `partner_presence_evidence/hpc_work_planning/execution_job_submission/api_job_execution` (launch_api)

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_job_submission/api_job_execution/<file>`, 29 files. It has no `grading/`, `scoring/` or child folders.

Old internal names: the class is `ExecutionEpisode`, assembled from the mixins `Native*`. The role is `launch_api`. The binding path is `.../execution_job_submission/api_job_execution`, commissioned by `.../execution_job_submission`. The version is `execution_episode_v1`.

## Purpose (its own words)

`goal.py` gives this text, with `{service}` filled from the validated assignment:

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit.

This episode runs one concrete request against a configured API service, for example EBI HMMER, NCBI BLAST, UniProt, Rfam or BV-BRC app service. It ends when it has a usable monitoring/results handoff.

## Task and instructions

- `replaces_default_instructions = True`.
- `task_instructions.py` appends, each only when it applies:
  - the reasoning-commit requirement, if `reason` is permitted (it never is here);
  - tool knowledge;
  - the launch instruction library;
  - the redelivery repair text;
  - if `wait` is permitted, the in-process child wait text and the native event target text ("A target is registration metadata, not proof that submission succeeded ... No event probability, gain or scientific credit follows from registration or passing time alone.");
  - the decision-exchange history replacement.
- Prompt rendering is the same chain as the siblings (`presentation.present_context`).

## What it reads from its parent's assignment

The assignment is anyOf `_request_schema(resource_id, selected=True)` over the configured `api` resources. Each is `api_execution.assignment_schema(resource_id)` with `resource_id` const. Versions are `api_execution_assignment_v1` / `api_service_assignment_v1`, and the request carries `service` plus optional `algorithm` and `database`.

`prepare_assignment` checks, in order:

1. `_validate_request`, then `api_execution.validate_assignment(selected, scope)`.
2. The kind matches the resource.
3. The parent role is `launch`.
4. It re-validates the parent launch.
5. `_validate_blast_launch_selection(original, selected, scope)`.
6. The masking/utility inputs, input versions, and BLAST-DB, standard-BLAST and RNA inputs.

`science._check_parent_inputs` re-reads the parent launch request, as in the siblings. Own addition: `_validate_blast_api_parent_request`. When the parent request for this resource is a BLAST graded request:

- the selected service must be `ncbi_blast` and permitted;
- the prepared query (`api.blast.prepare`) must have the sha256 of the subject sequence;
- a fixed database must match.

The error codes are `blast_grader_selected_service_conflict`, `blast_grader_selected_query_conflict` and `blast_grader_selected_database_conflict`.

## Children it may commission

None.

## Decision state shown to the model

`internal_summary.decision_context`:

- `execution_assignment`;
- `execution_progress` (its own facts);
- whatever `api_execution.decision_context(context, view)` supplies;
- `selected_execution_task`, only for `ebi_hmmer` requests (other services return no task view).

`task_decision` adds `waiting_support` when `wait` is permitted, along with the common inputs: launch library, child options (none), pending work, execution expectations for its own role, and resource estimates.

## Tools it offers

- The delegate's catalog: the API service operations for the resource (`api_execution.operation_contracts(resource_id, 'launch_api')`, for example prepare/submit/status). Execution goes through the delegate after the parent-input check.
- Actions: `('tool',)`. For an `api_service_assignment_v1` request the actions are `('tool', 'wait')`, so it can wait on native service events.
- `state()` raises `practical_resource_role_required`, because the API child has no terminal practical state.

## How its credit is counted

- Credit kind is `operational`.
- Live credit is `api_execution.credit_view(context, receiver_selection)`: the API service's operational credit for the handoff and acquired records, priced with the configured `handoff_unit` / `acquired_record_unit`.
- The closed-credit snapshot is returned unchanged after closing. Credit is never bounded.

## Continuation (yield estimator and settings)

`_launch_api_yield_controller` uses `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`.

- The profile key is `launch_api:api_<service>[_<algorithm>][_<database>]_handoff` in `task_yield_profiles` (required).
- `practical_estimator` builds the practical estimator on its own `verify_completion`. The siblings delegate this to the terminal behaviour instead.
- Completion: a recorded closed verdict, else `api_execution.verify_completion(context, proof)`. A verified original handoff gives exact zero future credit.
- In the new layout this maps to the "completion with a target" estimator, with the profile's cutoff/parameters as settings.

## What it reports to its parent

- An empty list for every native family fact source.
- `api_execution.facts(context, completion_snapshot)`: the service handoff/result facts, including `execution_handoff_refs` as produced by the service host.
- `execution_result_origin` = None.
- The closed credit facts.

`validate_report` is the same as the siblings'. UniProt closed facts are frozen, and Rfam returns are validated. `required_return_sources` returns `()`.

## Differences from siblings and similar episodes

- **vs `local_job_execution` and `hpc_job_execution`.** This child has:
  - its own goal text, where the siblings delegate to the terminal behaviour;
  - `wait` for service assignments;
  - reasoning/wait instruction texts;
  - `waiting_support` in its context;
  - credit, completion and facts from `api_execution`, where the siblings use the terminal practical state;
  - no practical state;
  - the BLAST graded-request bindings (`_validate_blast_launch_selection`, `_validate_blast_api_parent_request`).
- **Unused terminal copy.** `terminal_execution.py` is a byte-identical copy that is unused for API resources.
- **vs A101's `api_job_execution`.** The A101 version carries BLAST request custody and axis summaries.

## File by file

Old-runner names are counted per file as `name(uses)`. `workflow.X` stands for `self.workflow.X`, `source.workflow.X` or `workflow.X` on the old runner object. `runtime_*` are journal/receipt table names. `root.a107.<module>` entries are imports of old-runner modules. `catalog.*` is the old received-information catalog. Imports of old shared-root support modules (`root.a107.execution_contracts`, `a107_execution_bindings`, `native_*`, `library/*` and others) are not listed as old-runner names; the support code they named is now placed under `episode_support/`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding identity `.../execution_job_submission/api_job_execution`, version `execution_episode_v1`, same recorded configuration fields as the launch parent. | none |
| `completion.py` | 51 | Completion delegated to the API service execution; verification first reuses a recorded closed verdict, else `api_execution.verify_completion`. | ESTIMATOR_VERSION(2), NumericBand(2), root.a107.episode_return_records(1), root.a107.method_loop.identities(1), root.a107.numerical(1), root.a107.practical_yield(1), runtime_observations(1), UnitRef(2) |
| `configuration.py` | 119 | Identical copy of the launch configuration (resources, units, log selection, yield profiles, native families, readers). | root.a107.numerical(1), YieldController(3), YieldParameters(3) |
| `credit.py` | 136 | Credit kind `operational`; live credit = `api_execution.credit_view(context, receiver_selection)`; closed view returned unchanged after closing. | EpisodeReceipts(2), EpisodeReturnRecords(2), root.a107.episode_receipts(1), root.a107.episode_return_records(3), runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2) |
| `episode.py` | 106 | roles ('launch_api',); commissioned by `.../execution_job_submission`; replaces default instructions; no children; permitted actions ('tool',), or ('tool','wait') when the request is `api_service_assignment_v1`. | root.a107.communication(1), root.a107.runtime(1) |
| `execution_contracts.py` | 57 | Local copy of shared constants (VERSION, LAUNCH/RESULTS versions, RESULT_PROVIDER, closed-credit key, ROLES, KINDS, ROLE_KINDS, schema atoms, NATIVE_RESULT_ORIGIN, native result operation catalog) and re-exports. | root.a107.communication(1) |
| `from_parent.py` | 114 | Assignment schema = anyOf the API request schemas of configured api resources. Preparation as local, plus validation through `api_execution.validate_assignment` and `_validate_blast_launch_selection` against the parent launch. | none |
| `goal.py` | 9 | Own goal text (quoted below), naming the assigned service. | none |
| `initial_information.py` | 9 | Initial information from its own declared readers (binding path api_job_execution). | catalog.readers(1) |
| `internal_summary.py` | 91 | Decision context = `execution_assignment`, `execution_progress` (own facts) and the API service's `decision_context`, plus `selected_execution_task` (ebi_hmmer only). | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.json(2), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), root.a107.runtime(6), runtime_actions(2), workflow.binding_context(1), workflow.catalog(1), workflow.controller_binding(1), workflow.delivery_status(1), workflow.extra_report_sources(1), workflow.job_episode_options(1), workflow.journal(3), workflow.knowledge(1), workflow.local_outcome_preview(1), workflow.pending_work(1), workflow.run_id(1), workflow.source_credit_binding(1), workflow.source_credit_view(1), workflow.specialist(1), workflow.store(3), workflow.tools(1), workflow.working_state(1) |
| `presentation.py` | 74 | Prompt renderer selection (same predicates and renderers as the launch parent, reached through the old providers module). | _live_original_providers.apply_state_frame(3), _live_original_providers.DECISION_CONTEXT_VERSION(2), _live_original_providers.deepcopy(1), _live_original_providers.infernal_receiver_context(1), _live_original_providers.is_api_launch_context(2), _live_original_providers.is_published_scientific_context(2), _live_original_providers.json(1), _live_original_providers._ordinary_runtime_receiver_context(1), _live_original_providers.render_api_launch_prompt(1), _live_original_providers.render_partner_presence_evidence_prompt(1), _live_original_providers._rna_comparison_receiver_context(3), _live_original_providers.text_instructions(1), root.a107.decision_context(1) |
| `received_api_reports.py` | 4 | Own declared API reader authority (binding path api_job_execution). | catalog.configured(1), catalog.received(1) |
| `received_execution_information.py` | 4 | Own declared result readers (binding path api_job_execution). | catalog.configured(1), catalog.received(1) |
| `received_records.py` | 127 | Which received records count (same as launch handoff_receipts) and initial references (role launch_local takes its own assignment's inputs; other resource roles none). | none |
| `resource_information.py` | 70 | Resource tool contracts per resource (same as launch); resource information and capabilities helpers. | none |
| `science.py` | 76 | Input checks as local, plus `_validate_blast_api_parent_request`: for a BLAST graded parent request the selected service must be ncbi_blast, the prepared query sequence sha256 must equal the subject sequence, and the database must match. | runtime_episodes(1) |
| `state.py` | 19 | No practical state (`practical_resource_role_required`); initialise checks parent inputs then delegates. | none |
| `task.py` | 225 | Decision loop/action execution (old-runner); own bits: reasoning selections need non-empty commit content, grain = own role, wait through waiting.py. | _live_original_runtime.AcquisitionError(2), _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractError(1), _live_original_runtime.ContractInformationError(1), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime.Draft202012Validator(3), _live_original_runtime.EventTargetError(1), _live_original_runtime.inspect(1), _live_original_runtime._json(5), _live_original_runtime.json(8), _live_original_runtime.Mapping(3), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.SourceEnd(2), _live_original_runtime.sqlite3(2), _live_original_runtime.subprocess(2), _live_original_runtime.validate_form(1), _live_original_runtime.ValidationError(3), _live_original_runtime._wait_target_feedback(1), _live_original_runtime.WorkflowError(2), root.a107.episode_source_failure(1), root.a107.providers(1), root.a107.runtime(1), runtime_actions(8), runtime_episodes(1), runtime_model_calls(2), workflow.action_schema(1), workflow.automatic_score_updates(1), workflow.binding_context(2), workflow.completed_unit(3), workflow.completions(3), workflow.controller_value(2), workflow.decision_exchanges(3), workflow.delivery_resolution_inputs(1), workflow.execute(1), workflow.execution_binding(7), workflow.inprocess_replay(4), workflow.journal(7), workflow.last_observed_credit(1), workflow.next_return(1), workflow.pending_work(1), workflow.permits_common_action(1), workflow.reasoning_action_schema(1), workflow.receive_native_outcome(1), workflow.receive_outcome(1), workflow.resolve_pending_deliveries(1), workflow.resolver(1), workflow.retain_shared_grading_results(1), workflow.run_id(3), workflow.selected(3), workflow.source_credit_view(1), workflow.specialist(2), workflow.store(9), workflow.validate_report(1) |
| `task_decision.py` | 359 | Model call machinery (old-runner); own bits as local plus `waiting_support` context when wait is permitted. | _live_original_runtime._action_generation_schema(2), _live_original_runtime.apply_state_frame(1), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._category_yield_parameters(1), _live_original_runtime.child_option_information(2), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime._digest(1), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.infernal_receiver_context(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime._json(14), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.Mapping(4), _live_original_runtime.model_snapshot(2), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime.yield_table(1), root.a107.episode_work_report(2), root.a107.providers(1), root.a107.runtime(1), runtime_model_calls(8), workflow.available_child_roles(1), workflow.binding_context(1), workflow.contract_information_profile(1), workflow.contract_information_reply(1), workflow.controller_binding(1), workflow.decision_exchanges(4), workflow.decision_protocol(3), workflow.episode_bindings(1), workflow.execute(1), workflow.execution_expectations(1), workflow.freeze_contract_information(1), workflow.freeze_literature_numerical_contracts(1), workflow.history_preview(1), workflow.is_job_source(3), workflow.job_episodes(2), workflow.journal(3), workflow.launch_instructions(2), workflow.native_estimation_context(1), workflow.numerical_contracts(1), workflow.pending_work(1), workflow.permits_common_action(1), workflow.provider(3), workflow.receipts(4), workflow.resource_context(1), workflow.resource_estimator(5), workflow.run_id(1), workflow.services(2), workflow.shared_information_context(1), workflow.specialist(1), workflow.store(2), workflow.uses_received_record_context(2), workflow.validate_contract_information(5), workflow.waiting_support(1) |
| `task_instructions.py` | 25 | Instruction composition as local plus reasoning-commit text (if reason permitted) and the wait / native event target texts when wait is permitted. | _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL(1), _live_original_runtime_prompt.INSTRUCTIONS(4), _live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT(1), workflow.binding_context(1), workflow.decision_protocol(1), workflow.is_job_source(1), workflow.job_episodes(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.permits_common_action(3), workflow.specialist(1) |
| `task_report.py` | 22 | Finish/report delivery (old-runner machinery only). | _live_original_runtime.form_with_facts(1), _live_original_runtime._json(2), _live_original_runtime.json(1), _live_original_runtime.Record(2), root.a107.runtime(1), runtime_forms(2), workflow.binding_context(1), workflow.episode_bindings(1), workflow.facts(1), workflow.journal(2), workflow.pending_handles(1), workflow.release(2), workflow.source_credit_view(1) |
| `task_state.py` | 107 | Source state (old-runner machinery only; identical to launch). | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime._json(2), _live_original_runtime.json(4), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.Record(1), root.a107.episode_source_failure(1), root.a107.runtime(1), runtime_actions(5), workflow.archive(1), workflow.completions(4), workflow.context(1), workflow.controller_value(1), workflow.execution_binding(4), workflow.grains(1), workflow.inprocess_replay(7), workflow.journal(5), workflow.progress_provider(2), workflow.recover_commissions(1), workflow.run_id(1), workflow.source_credit_view(1), workflow.store(2) |
| `task_suspension.py` | 8 | Suspension forwarding (old-runner only). | workflow.execution_backend(1), workflow.execution_handle(2) |
| `terminal_execution.py` | 226 | Byte-identical copy of the terminal behaviour; not built for API resources (configuration builds it only for non-API kinds). | PracticalYieldEstimator(2), root.a107.communication(1), root.a107.practical_yield(1) |
| `to_parent.py` | 88 | Report facts = native empty sources + `api_execution.facts(context, completion_snapshot)`; `execution_result_origin` None. Report validation as local. | none |
| `waiting.py` | 10 | Selected wait through the old runner, failure turned into a failed outcome. | _live_original_runtime.EventTargetError(1), _live_original_runtime._wait_target_feedback(1), root.a107.runtime(1), workflow.perform_selected_wait(1) |
| `work_operations.py` | 35 | Tools = the delegate's catalog (API service operations); execute checks parent inputs then runs through the delegate. | none |
| `yield_estimator.py` | 50 | Continuation: profile `launch_api:<request yield class>` (e.g. `api_<service>[_<algorithm>][_<database>]_handoff`); `YieldController(cutoff, parameters)` with the practical completion estimator verifying via its own `verify_completion`. | PracticalYieldEstimator(4), root.a107.numerical(1), root.a107.practical_yield(2), YieldController(2), YieldParameters(2) |

## Old-runner names, totals for this episode

`_live_original_runtime._json`(23), `workflow.journal`(20), `_live_original_runtime.json`(18), `_live_original_runtime.WorkflowError`(16), `workflow.store`(16), `runtime_actions`(15), `root.a107.runtime`(12), `workflow.execution_binding`(11), `workflow.inprocess_replay`(11), `_live_original_runtime.Mapping`(10), `runtime_model_calls`(10), `_live_original_runtime.ValidationError`(8), `workflow.completions`(7), `workflow.decision_exchanges`(7), `PracticalYieldEstimator`(6), `workflow.binding_context`(6), `workflow.run_id`(6), `_live_original_runtime.DECISION_EXCHANGE_PROTOCOL`(5), `_live_original_runtime.nullcontext`(5), `_live_original_runtime._plain`(5), `runtime_forms`(5), `workflow.permits_common_action`(5), `workflow.resource_estimator`(5), `workflow.specialist`(5), `workflow.validate_contract_information`(5), `YieldController`(5), `YieldParameters`(5), `_live_original_runtime.Draft202012Validator`(4), `_live_original_runtime.instructional_model_context`(4), `_live_original_runtime._object`(4), `_live_original_runtime_prompt.INSTRUCTIONS`(4), `root.a107.episode_return_records`(4), `root.a107.practical_yield`(4), `runtime_episodes`(4), `workflow.decision_protocol`(4), `workflow.is_job_source`(4), `workflow.receipts`(4), `workflow.source_credit_view`(4), `_live_original_providers.apply_state_frame`(3), `_live_original_providers._rna_comparison_receiver_context`(3), `_live_original_runtime.Record`(3), `_live_original_runtime.schema_failure_diagnostic`(3), `_live_original_runtime.sqlite3`(3), `root.a107.communication`(3), `root.a107.numerical`(3), `workflow.completed_unit`(3), `workflow.controller_value`(3), `workflow.job_episodes`(3), `workflow.launch_instructions`(3), `workflow.pending_work`(3), `workflow.provider`(3), `workflow.selected`(3), `catalog.configured`(2), `catalog.received`(2), `EpisodeReceipts`(2), `EpisodeReturnRecords`(2), `ESTIMATOR_VERSION`(2), `_live_original_providers.DECISION_CONTEXT_VERSION`(2), `_live_original_providers.is_api_launch_context`(2), `_live_original_providers.is_published_scientific_context`(2), `_live_original_runtime.AcquisitionError`(2), `_live_original_runtime._action_generation_schema`(2), `_live_original_runtime.child_option_information`(2), `_live_original_runtime.composition_lookup_schema`(2), `_live_original_runtime.DECISION_CONTEXT_VERSION`(2), `_live_original_runtime.EventTargetError`(2), `_live_original_runtime.infernal_receiver_context`(2), `_live_original_runtime.model_snapshot`(2), `_live_original_runtime._references_in`(2), `_live_original_runtime.ReportRedelivery`(2), `_live_original_runtime.requested_contract_information`(2), `_live_original_runtime.SourceEnd`(2), `_live_original_runtime.subprocess`(2), `_live_original_runtime._wait_target_feedback`(2), `NumericBand`(2), `root.a107.episode_source_failure`(2), `root.a107.episode_work_report`(2), `root.a107.providers`(2), `runtime_observations`(2), `runtime_receipt_inheritance`(2), `runtime_record_receipts`(2), `UnitRef`(2), `workflow.controller_binding`(2), `workflow.episode_bindings`(2), `workflow.execute`(2), `workflow.execution_handle`(2), `workflow.knowledge`(2), `workflow.progress_provider`(2), `workflow.release`(2), `workflow.services`(2), `workflow.uses_received_record_context`(2), `catalog.readers`(1), `_live_original_providers.deepcopy`(1), `_live_original_providers.infernal_receiver_context`(1), `_live_original_providers.json`(1), `_live_original_providers._ordinary_runtime_receiver_context`(1), `_live_original_providers.render_api_launch_prompt`(1), `_live_original_providers.render_partner_presence_evidence_prompt`(1), `_live_original_providers.text_instructions`(1), `_live_original_runtime.ActionFailure`(1), `_live_original_runtime.ActionLeaf`(1), `_live_original_runtime.apply_state_frame`(1), `_live_original_runtime._ASSIGNMENT_TRANSPORT`(1), `_live_original_runtime._category_yield_parameters`(1), `_live_original_runtime.ContractError`(1), `_live_original_runtime.ContractInformationError`(1), `_live_original_runtime.CONTRACT_INFORMATION_OPERATIONS`(1), `_live_original_runtime._decode_recorded_action_response`(1), `_live_original_runtime._digest`(1), `_live_original_runtime.EFFECT_VERSION`(1), `_live_original_runtime.Episode`(1), `_live_original_runtime.FACT_MEANINGS`(1), `_live_original_runtime.FACT_SOURCES`(1), `_live_original_runtime.form_with_facts`(1), `_live_original_runtime.inspect`(1), `_live_original_runtime.interpretation_schema`(1), `_live_original_runtime.is_contract_information`(1), `_live_original_runtime.lookup_attempts`(1), `_live_original_runtime.observes_action_outcome`(1), `_live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL`(1), `_live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT`(1), `_live_original_runtime._recorded_action_generation_schema`(1), `_live_original_runtime._recorded_assignment_transport`(1), `_live_original_runtime.ReportBoundaryError`(1), `_live_original_runtime.state_frame`(1), `_live_original_runtime.validate_form`(1), `_live_original_runtime.yield_table`(1), `root.a107.decision_context`(1), `root.a107.episode_receipts`(1), `root.a107.method_loop.identities`(1), `workflow.action_schema`(1), `workflow.archive`(1), `workflow.automatic_score_updates`(1), `workflow.available_child_roles`(1), `workflow.catalog`(1), `workflow.context`(1), `workflow.contract_information_profile`(1), `workflow.contract_information_reply`(1), `workflow.delivery_resolution_inputs`(1), `workflow.delivery_status`(1), `workflow.execution_backend`(1), `workflow.execution_expectations`(1), `workflow.extra_report_sources`(1), `workflow.facts`(1), `workflow.freeze_contract_information`(1), `workflow.freeze_literature_numerical_contracts`(1), `workflow.grains`(1), `workflow.history_preview`(1), `workflow.job_episode_options`(1), `workflow.last_observed_credit`(1), `workflow.local_outcome_preview`(1), `workflow.native_estimation_context`(1), `workflow.native_event_information`(1), `workflow.next_return`(1), `workflow.numerical_contracts`(1), `workflow.pending_handles`(1), `workflow.perform_selected_wait`(1), `workflow.reasoning_action_schema`(1), `workflow.receive_native_outcome`(1), `workflow.receive_outcome`(1), `workflow.recover_commissions`(1), `workflow.resolve_pending_deliveries`(1), `workflow.resolver`(1), `workflow.resource_context`(1), `workflow.retain_shared_grading_results`(1), `workflow.shared_information_context`(1), `workflow.source_credit_binding`(1), `workflow.tools`(1), `workflow.validate_report`(1), `workflow.waiting_support`(1), `workflow.working_state`(1)

Every row (name, episode, file, uses, purpose) is in `runs/carry_over/calls/a107_03.tsv`.

## Carried over

Old source read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`); one row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__execution_job_submission__api_job_execution.tsv` (128 rows). Rows marked "episode function, unplaced" are listed in `carry_over_blocked/`. The folder takes the file shapes of the A102 sibling `api_job_execution` (same old source; private copy, nothing imported). The old `APIServiceExecution` (`api_execution`) was in the old shared root, is not in the library and is the BLOCKED-ON-JOB-SERVICE `job_access` service; the job records are BLOCKED-ON-JOB-SERVICE too.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| `binding_record.py` | `NativeBindingRecord` | machinery | binding's own as_record(): settings and declared services are journaled by the system (README 3e) |
| `binding_record.py` | `NativeBindingRecord.as_record` | machinery | binding's own as_record(): settings and declared services are journaled by the system (README 3e) |
| `completion.py` | `NativeCompletion` | machinery | completion proof read from old runtime_observations; replaced by CompletionYieldController with its target from parent_input (yield_estimator.py) |
| `completion.py` | `NativeCompletion.completion_for_action` | machinery | completion proof read from old runtime_observations; replaced by CompletionYieldController with its target from parent_input (yield_estimator.py) |
| `completion.py` | `NativeCompletion._closed_completion_verdict` | machinery | completion proof read from old runtime_observations; replaced by CompletionYieldController with its target from parent_input (yield_estimator.py) |
| `completion.py` | `NativeCompletion.verify_completion` | machinery | completion proof read from old runtime_observations; replaced by CompletionYieldController with its target from parent_input (yield_estimator.py) |
| `configuration.py` | `NativeConfiguration` | episode function | settings read as `ctx.settings` in task.py (`resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`) and `settings` in yield_estimator.py (`cost`, `parameters`); the API executor it built is the BLOCKED-ON-JOB-SERVICE `job_access` service; its local native-result adapters, `ExecutionProgressProvider`, `LocalFileSourceResults` and result readers serve local/hpc/results roles, not this episode (machinery of the old runner) |
| `configuration.py` | `NativeConfiguration.__init__` | episode function | settings read as `ctx.settings` in task.py (`resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`) and `settings` in yield_estimator.py (`cost`, `parameters`); the API executor it built is the BLOCKED-ON-JOB-SERVICE `job_access` service; its local native-result adapters, `ExecutionProgressProvider`, `LocalFileSourceResults` and result readers serve local/hpc/results roles, not this episode (machinery of the old runner) |
| `credit.py` | `ExecutionEpisodeCredit` | episode function | credit.py `credit` (the service credit view arrives in the tool outcome field `credit`, task.py `service_operation`) |
| `credit.py` | `ExecutionEpisodeCredit.credit_kind` | machinery | credit_kind deleted (README 3d) |
| `credit.py` | `ExecutionEpisodeCredit._closed_credit_carrier` | machinery | frozen closed credit view checked against old journal/receipt tables; credit is `credit.py` and the system hands `completion['credit']` |
| `credit.py` | `ExecutionEpisodeCredit._closed_credit_receipts` | machinery | frozen closed credit view checked against old journal/receipt tables; credit is `credit.py` and the system hands `completion['credit']` |
| `credit.py` | `ExecutionEpisodeCredit._closed_credit_value` | machinery | frozen closed credit view checked against old journal/receipt tables; credit is `credit.py` and the system hands `completion['credit']` |
| `credit.py` | `ExecutionEpisodeCredit._closed_credit_facts` | machinery | frozen closed credit view checked against old journal/receipt tables; credit is `credit.py` and the system hands `completion['credit']` |
| `credit.py` | `ExecutionEpisodeCredit._closed_operational_credit_view` | machinery | frozen closed credit view checked against old journal/receipt tables; credit is `credit.py` and the system hands `completion['credit']` |
| `credit.py` | `ExecutionEpisodeCredit.project_credit` | episode function | credit.py `credit` (the service credit view arrives in the tool outcome field `credit`, task.py `service_operation`) |
| `credit.py` | `ExecutionEpisodeCredit._live_project_credit` | episode function | credit.py `credit` (the service credit view arrives in the tool outcome field `credit`, task.py `service_operation`) |
| `credit.py` | `ExecutionEpisodeCredit.credit_view` | episode function | credit.py `credit` (the service credit view arrives in the tool outcome field `credit`, task.py `service_operation`) |
| `episode.py` | `ExecutionEpisode` | episode function | episode.py `ApiJobExecution` |
| `episode.py` | `ExecutionEpisode.child_roles` | episode function | task.py `CHILD_SLOTS = {}` (leaf) |
| `episode.py` | `ExecutionEpisode.allowed_children` | episode function | task.py `CHILD_SLOTS = {}` (leaf) |
| `episode.py` | `ExecutionEpisode.permitted_common_actions` | episode function | task.py `wait_permitted`, `offered_actions` |
| `execution_contracts.py` | `native_result_operation_catalog` | episode function, unplaced | results-role catalog of the native protein-structure results operations; never used by this episode's launch_api branch (UNPLACED, in carry_over_blocked) |
| `from_parent.py` | `NativeParentRequests` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM`, `read_from_parent` (the api branch of the request schema; the local requested_job alternatives belong to the local/hpc siblings) |
| `from_parent.py` | `NativeParentRequests._permitted` | machinery | check of the commission against the parent launch assignment (a wrong commission fails, rule 1); not carried |
| `from_parent.py` | `NativeParentRequests._request_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM`, `read_from_parent` (the api branch of the request schema; the local requested_job alternatives belong to the local/hpc siblings) |
| `from_parent.py` | `NativeParentRequests._launch` | machinery | check of the commission against the parent launch assignment (a wrong commission fails, rule 1); not carried |
| `from_parent.py` | `NativeParentRequests._constraints` | machinery | check of the commission against the parent launch assignment (a wrong commission fails, rule 1); not carried |
| `from_parent.py` | `NativeParentRequests.child_assignment_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM`, `read_from_parent` (the api branch of the request schema; the local requested_job alternatives belong to the local/hpc siblings) |
| `from_parent.py` | `NativeParentRequests.assignment_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM`, `read_from_parent` (the api branch of the request schema; the local requested_job alternatives belong to the local/hpc siblings) |
| `from_parent.py` | `NativeParentRequests.prepare_assignment` | episode function | messages/read_from_parent.py `read_from_parent`; its checks against the parent launch (kind, role, BLAST selection, masking/utility/version/BLAST-database inputs) are commission checks and are not carried |
| `goal.py` | `NativeGoal` | episode function | task.py `GOAL_TEXT`, `instructions`; goal.py `GOAL` |
| `goal.py` | `NativeGoal.instructions` | episode function | task.py `GOAL_TEXT`, `instructions`; goal.py `GOAL` |
| `initial_information.py` | `initial_information` | episode function | task.py `resource_capabilities` (decide context `execution_resource_capabilities`); the receiving-catalog reader authority (`catalog.readers`) is machinery |
| `internal_summary.py` | `native_decision_snapshot` | machinery | reads the old journal and Store tables (runtime_actions, working_state, local_outcome_preview); the state comes from the view (messages/internal_summary.py) and decide |
| `internal_summary.py` | `NativeInternalSummary` | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` context (`execution_assignment`, `execution_progress`); the api_execution decision_context is the BLOCKED-ON-JOB-SERVICE `job_access` read |
| `internal_summary.py` | `NativeInternalSummary._with_selected_execution_task` | episode function | task.py `selected_execution_task` (ebi_hmmer only; the parent task values are the new assignment fields `scientific_question`, `selected_tool_info`) |
| `internal_summary.py` | `NativeInternalSummary.decision_context` | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` context (`execution_assignment`, `execution_progress`); the api_execution decision_context is the BLOCKED-ON-JOB-SERVICE `job_access` read |
| `presentation.py` | `present_context` | episode function | task.py `decide` (the context travels as a mapping in ModelRequest.context); the prompt renderers `render_api_launch_prompt` and `is_api_launch_context` are in the old shared root and not found: UNPLACED, in carry_over_blocked |
| `received_api_reports.py` | `received_api_reports` | machinery | old receiving catalog authority (catalog.configured, catalog.received); custody replaces it |
| `received_execution_information.py` | `received_execution_information` | machinery | old receiving catalog authority (catalog.configured, catalog.received); custody replaces it |
| `received_records.py` | `NativeReceivedRecords` | machinery | old received-record bookkeeping over receipts and the old handoff reader; custody replaces it |
| `received_records.py` | `NativeReceivedRecords._context_target` | machinery | handoff target authentication against the parent launch (BLAST graded request check) over old receipts; not carried |
| `received_records.py` | `NativeReceivedRecords._received` | machinery | old received-record bookkeeping over receipts and the old handoff reader; custody replaces it |
| `received_records.py` | `NativeReceivedRecords.initial_references` | machinery | old received-record bookkeeping over receipts and the old handoff reader; custody replaces it |
| `resource_information.py` | `NativeResourceInformation` | episode function | task.py `catalog_of` (decide, action) : the api launch/results operation contracts are a BLOCKED-ON-JOB-SERVICE `job_access` read (`api_catalog`); the local native contracts serve the local siblings |
| `resource_information.py` | `NativeResourceInformation.resource_tool_contracts` | episode function | task.py `catalog_of` (decide, action) : the api launch/results operation contracts are a BLOCKED-ON-JOB-SERVICE `job_access` read (`api_catalog`); the local native contracts serve the local siblings |
| `science.py` | `NativeScienceInputs` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._masking_inputs` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._utility_inputs` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._expression_nmf_inputs` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._versions` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._check_parent_inputs` | machinery | check of the commission against the parent launch inputs; a wrong commission fails (rule 1); not carried |
| `science.py` | `NativeScienceInputs._validate_blast_api_parent_request` | episode function, unplaced | check of the selected request against the parent BLAST graded request (needs the parent launch assignment and `api.blast.prepare`); a commission check, not carried (UNPLACED, in carry_over_blocked) |
| `state.py` | `NativeState` | machinery | re-check of the parent launch inputs and delegation of initialization; custody and the first decision replace it |
| `state.py` | `NativeState.initialize` | machinery | re-check of the parent launch inputs and delegation of initialization; custody and the first decision replace it |
| `state.py` | `NativeState.state` | machinery | raised practical_resource_role_required: this episode has no practical state; nothing to carry |
| `task.py` | `NativeTask` | episode function | task.py `decide`, `action`, `TOOLS` |
| `task.py` | `NativeTask.next` | machinery | old decision loop (next): replay, completions, redelivery, model-call journal |
| `task.py` | `NativeTask.apply_response` | episode function | task.py `action` (admission of the model selection; rejection through Rejected) |
| `task.py` | `NativeTask.execute` | episode function | task.py tools `service_operation`, `capabilities`, `wait`, `launch_instructions`, `tool_knowledge` |
| `task_decision.py` | `NativeTaskDecision` | episode function | task.py `decide`; the exchange machinery of the class is not carried |
| `task_decision.py` | `NativeTaskDecision.call` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.instructions` | episode function | task.py `instructions` |
| `task_decision.py` | `NativeTaskDecision.conversation_key` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.interpretation_context` | episode function | task.py `decide` context |
| `task_decision.py` | `NativeTaskDecision.exchange_schema` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.exchange_response` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.validate_contract_exchange_request` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.validate_contract_exchange_history` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.exchange_decision` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_decision.py` | `NativeTaskDecision.decision_completion` | machinery | decision-exchange loop, saved-exchange checks, provider and conversation machinery |
| `task_instructions.py` | `instructions` | episode function | task.py `instructions` (goal, action and wait texts, launch-instruction and tool-knowledge texts); the reasoning-commit, redelivery, pending-child and decision-exchange texts describe actions that do not exist and are not carried |
| `task_report.py` | `NativeTaskReport` | machinery | report delivery (finish): the result is final_to_parent |
| `task_report.py` | `NativeTaskReport.finish` | machinery | report delivery (finish): the result is final_to_parent |
| `task_state.py` | `NativeTaskState` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.__init__` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.bind_execution_context` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.record_execution_failure` | machinery | failed action recording (record_source_failure); a failed operation is a returned outcome (task.py `service_operation`, library `failure_outcome`) |
| `task_state.py` | `NativeTaskState.restore_checkpoint` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.restore` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.record_effect` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_state.py` | `NativeTaskState.checkpoint` | machinery | old source state: restore, checkpoint, effects, inprocess replay |
| `task_suspension.py` | `NativeTaskSuspension` | machinery | suspension forwarding to the old execution backend |
| `task_suspension.py` | `NativeTaskSuspension.suspension_changed` | machinery | suspension forwarding to the old execution backend |
| `terminal_execution.py` | `TerminalExecutionBehavior` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.__init__` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior._operations` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior._assignment` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior._state_directory` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.initialize` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.state` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.as_record` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.child_roles` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.credit_kind` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.assignment_schema` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.permitted_common_actions` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.allowed_children` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.prepare_assignment` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.initial_decision_context` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior._resource_information` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior._resource_instructions` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.instructions` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.decision_context` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.catalog` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.execute` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.completion_for_action` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.practical_estimator` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.fact_sources` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.facts` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.resolve` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.validate_report` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `terminal_execution.py` | `TerminalExecutionBehavior.credit_view` | episode function, unplaced | byte-identical copy of the local/hpc terminal behaviour, never built for API resources; carried by the hpc_job_execution and local_job_execution episodes (UNPLACED, in carry_over_blocked) |
| `to_parent.py` | `NativeParentReturns` | episode function | messages/final_to_parent.py `final_to_parent`, `RETURN_FORM` (fact fields `execution_handoff_refs`, `execution_result_refs`, `execution_completed`, `execution_result_origin`, the hmmer family sources) |
| `to_parent.py` | `NativeParentReturns.required_return_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` (no source required of the parent) |
| `to_parent.py` | `NativeParentReturns.facts` | episode function | messages/final_to_parent.py `final_to_parent`, `RETURN_FORM` (fact fields `execution_handoff_refs`, `execution_result_refs`, `execution_completed`, `execution_result_origin`, the hmmer family sources) |
| `to_parent.py` | `NativeParentReturns._live_facts` | episode function | messages/final_to_parent.py `final_to_parent`, `RETURN_FORM` (fact fields `execution_handoff_refs`, `execution_result_refs`, `execution_completed`, `execution_result_origin`, the hmmer family sources) |
| `to_parent.py` | `NativeParentReturns.validate_report` | episode function | messages/final_to_parent.py `validate_report` (fact agreement, called in `final_to_parent`); the UniProt/Rfam host checks and the local native adapters are UNPLACED, in carry_over_blocked |
| `waiting.py` | `perform_selected_native_wait` | episode function | task.py `wait` tool (EventTargetError turned into a failed outcome) |
| `work_operations.py` | `NativeWorkOperations` | episode function | task.py `service_operation` (tool), `catalog_of`; the executor is BLOCKED-ON-JOB-SERVICE |
| `work_operations.py` | `NativeWorkOperations.catalog` | episode function | task.py `catalog_of` |
| `work_operations.py` | `NativeWorkOperations.execute` | episode function | task.py `service_operation` (tool), `catalog_of`; the executor is BLOCKED-ON-JOB-SERVICE |
| `yield_estimator.py` | `ExecutionEpisodeYield` | episode function | yield_estimator.py `yield_controller` (CompletionYieldController, target from parent_input) |
| `yield_estimator.py` | `ExecutionEpisodeYield._request_yield_class` | episode function | yield_estimator.py: the `launch_api:<class>` profile lookup is replaced by this episode's own `continuation` entry (README 3d) |
| `yield_estimator.py` | `ExecutionEpisodeYield._task_yield_profile` | episode function | yield_estimator.py: the `launch_api:<class>` profile lookup is replaced by this episode's own `continuation` entry (README 3d) |
| `yield_estimator.py` | `ExecutionEpisodeYield.yield_controller` | episode function | yield_estimator.py `yield_controller` (CompletionYieldController, target from parent_input) |
| `yield_estimator.py` | `ExecutionEpisodeYield._launch_api_yield_controller` | episode function | yield_estimator.py `yield_controller` (CompletionYieldController, target from parent_input) |
| `yield_estimator.py` | `ExecutionEpisodeYield.practical_estimator` | machinery | PracticalYieldEstimator deleted (README 7b) |
