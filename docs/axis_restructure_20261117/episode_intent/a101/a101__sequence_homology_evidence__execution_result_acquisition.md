# a101 / sequence_homology_evidence / execution_result_acquisition

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_result_acquisition/<file>`).
`tests/` is not covered here. Old binding class `ExecutionEpisode` (with `BlastResultGrading`); decision source `OperationalTask`.

## Purpose (goal, in its own words)

Role `results` (also an entry role). `goal.py`, with `replaces_default_instructions = True`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were produced
> by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the
> returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes
> this endpoint.

## Task and instructions

- `task_instructions.py` is identical to local_job_execution's. The goal above replaces the default prompt, and the
  composer then adds tool knowledge, launch instructions, repair guidance and exchange history. Wait guidance (and
  native-event guidance, when an event provider exists) is added only when `wait` is permitted, which happens only
  for an API service assignment (`api_service_assignment_v1`).
- `task.py` is local_job_execution's loop plus a selected `wait`, executed by `waiting._execute_selected_wait` →
  `perform_selected_wait`. An `EventTargetError` becomes a failed outcome that enters the iterator. A wait keeps the
  last observed credit and runs no automatic score updates.

## What it reads from its parent's assignment

- The parent is `sequence_homology_evidence` (it commissions role `results`).
- Assignment `execution_results_assignment_v1` = `{handoff_ref, selector}` (`from_parent.assignment_schema`). The
  selector may be `local_file_source_selector_v1` (requested local files), a native byte selector
  (`paths`/`path`/`offset`/`limit`), or a typed native result selector, following `result_selector_conditions()`
  (masking, utility, standard DB, DB, HMMER preparation, HMMER, BLAST pairwise, BV-BRC, MinHash).
- `prepare_assignment` does the following:
  - restores an already returned original Results commission (`_recorded_results_assignment`);
  - reads the handoff target (or the retained masking/utility target) and validates the selector against it;
  - admits local file sources and validates the selected native inputs (masking, utility, standard BLAST DB, BLAST
    DB, BV-BRC data, MinHash commission inputs).
- `initial_references` = the handoff_ref plus the BLAST DB-selected inputs (or the masking/utility selected inputs).
- `execution_state.initialize`: when the original Launch request was a BLAST database-grader request
  (`BLAST_GRADED_REQUEST_VERSION`), the parent's report contract must contain the exact typed `BLAST_GRADED_RETURN`
  field (`blast_grader_typed_return_required`).

## Children

None.

## Decision state shown to the model

The same `decision_state` as local_job_execution (goal, credit, controller, tools, report form, ...). The specialist
`decision_context` differs, however: execution_assignment, execution_progress (= current `facts`),
execution_target (the handoff target), execution_target_description (status/acquisition operations and provenance;
for local file sources, `execution.results.status` / `execution.results.collect` and the ORIGIN), own_bvbrc_values
for a BV-BRC API target, and selected_execution_task built from the target's original assignment.
`decision_inputs` adds `waiting_support` when wait is permitted.

## Tools offered

Native result operations `execution.results.status` (observe the exact handed-off attempt once),
`execution.results.collect` (observe and acquire the first bounded windows of the requested paths) and
`execution.results.read` (`{path, offset, limit <= 1 MiB}` inside the original requested paths and interval). The
native family catalogs (masking, utility, standard DB, DB, HMMER preparation, HMMER, BLAST) and the API service
result operations also apply. The tool is `wait` for API service targets.

## Credit

- `credit_kind` = `operational`.
- API target: `api_execution.credit_view`.
- Native byte selector: `credit = acquired_record_unit * newly covered requested-byte fraction` (each requested byte
  position counts once, minus what was already in the initial known records; the mean over requested paths).
  Binding `execution_received_selector_coverage_credit_v2`. The `handoff_count` term is fixed at 0.
- Local file sources: `credit = acquired_record_unit * new file acquisitions`
  (`execution_received_records_credit_v1`).
- Native typed families use their own `credit_view`.
- Completion proof as in local_job_execution, plus `supporting_receipt_sha256s`. `verify_completion` also goes
  through API execution and the native HMMER-preparation, BLAST and HMMER families.
- The closed-credit snapshot rule is the same as local's. No clamp or rescale.

## Continuation

`yield_estimator._results_yield_controller` (requires `require_private_yield`):

- Native selector with an unbounded requested length: `results_yield_profiles['native_unbounded_<local|hpc>']`, a
  plain `YieldController(cutoff, YieldParameters)`. This corresponds to the **accumulation** estimator.
- Native finite selector: `task_yield_profiles['results:native_finite_<kind>']` with `finite_result_yield`. It uses
  the endpoint proof once verified. It forecasts exact zero (`finite_result_selector_exhaustion_v1`) when no
  uncredited requested bytes remain. Otherwise it calls `estimate_bounded_credit_yield` with `maximum_credit =
  acquired_record_unit * (1 - original fraction)`. This corresponds to the **bounded quality** estimator (maximum =
  the remaining requested bytes).
- API target: `results:api_<service>[_<selector version>]`. Typed native target:
  `results:typed_<kind>_<selector version>`. Both use the `PracticalYieldEstimator` endpoint and correspond to the
  **completion-with-a-target** estimator.

## Report to parent

The same fact sources as local_job_execution, plus `BLAST_GRADED_RETURN_SOURCE` when an ncbi_blast API service is
bound and role = results. For API targets, `facts` comes from `api_execution.facts`, plus BLAST grader rows
(`_blast_grader_rows`: only retained grader sheets whose query length, sha256, subject and database match the
original request) and `execution_result_origin: None`. For native targets, `facts` = the native family facts, or
handoff refs plus `execution_completed` (`_native_results_complete`: a completed attempt with returncode 0 and every
requested byte window covered). `required_return_sources` → `('execution_result_refs',)` when the parent is
sequence_homology_evidence and the services require an annotation task. `validate_report` and `finish` are as in
local.

## Differences from similar episodes

- versus **local_job_execution**: see that file's note (4 files byte-identical, 10 that differ only in name, 12 that
  differ in substance). Only this episode has `blast_result_grading.py`, `wait`, the byte-coverage credit and three
  of the four continuation branches. `terminal_execution.py` is an identical, unused copy here.
- versus **execution_progress_assessment**: both observe an already submitted job. The monitor credits newly
  informative progress snapshots and may recurse into dependencies. This episode credits acquired result bytes and
  never commissions children.

## Per-file table

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| binding_record.py | 8 | Binding record id `sequence_homology_evidence/execution_result_acquisition`, VERSION `execution_episode_v1`, same configuration fields as local_job_execution. | none |
| blast_result_grading.py | 90 | Only here (not in local_job_execution): BlastResultGrading. `_blast_target_requirement` rebuilds the original BLAST database-grader return request from the original Launch request (query subject, length, sha256, database) and checks the submitted query; `_blast_grader_rows` returns only retained grader sheets whose normalized query/database match. | `import:a101.communication` (1), `import:a101.execution_contracts` (1), `import:a101.library.blast_return_contracts` (1), `import:a101.tool_grading_artifacts` (1), `table:runtime_episodes` (2) |
| configuration.py | 119 | Identical to local_job_execution's configuration (docstring differs): resources, units, log window, results_yield_profiles (native_unbounded_local/hpc), task_yield_profiles, result readers. | `import:a101.api_service_execution` (1), `import:a101.execution_progress` (1), `import:a101.library.retained_input_authority.atac_differential_returns` (1), `import:a101.library.retained_input_authority.chromatin_interaction_returns` (1), `import:a101.library.retained_input_authority.expression_nmf_returns` (1), `import:a101.library.retained_input_authority.fluorescence_returns` (1), `import:a101.library.retained_input_authority.flux_balance_execution_inputs` (1), `import:a101.library.retained_input_authority.flux_balance_returns` (1), `import:a101.library.retained_input_authority.native_atac_differential_results` (1), `import:a101.library.retained_input_authority.native_chromatin_interaction_results` (1), `import:a101.library.retained_input_authority.native_expression_nmf_results` (1), `import:a101.library.retained_input_authority.native_fluorescence_results` (1), `import:a101.library.retained_input_authority.native_flux_balance_results` (1), `import:a101.library.retained_input_authority.native_protein_structure_results` (1), `import:a101.library.retained_input_authority.native_protein_structure_returns` (1), `import:a101.numerical` (1), `name:YieldController` (3), `name:YieldParameters` (3) |
| credit.py | 286 | Operational credit. Differs from local: API targets use api_execution.credit_view; native targets credit = handoff_unit*0 + acquired_record_unit*newly covered requested-byte fraction (`execution_received_selector_coverage_credit_v2`), or acquired_record_unit*file acquisitions for local file sources (`execution_received_records_credit_v1`). Completion proof adds supporting_receipt_sha256s; verify_completion also via API execution and native HMMER/BLAST result families. Same closed-credit snapshot rule. | `import:a101.episode_receipts` (1), `import:a101.episode_return_records` (4), `import:a101.method_loop.identities` (1), `import:a101.numerical` (1), `import:a101.practical_yield` (1), `name:ESTIMATOR_VERSION` (2), `name:NumericBand` (2), `table:runtime_actions` (2), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations` (2), `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2), `table:sqlite_master` (2) |
| decision_inputs.py | 78 | As local_job_execution plus `waiting_support` when wait is permitted. | `import:a101.episode_work_report` (2), `import:a101.hpc_prompt` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.job_episodes` (2), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (4), `self.workflow.shared_information_context` (1), `self.workflow.store` (2), `self.workflow.waiting_support` (1) |
| decision_state.py | 55 | Identical to local_job_execution (only module name differs). | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `table:runtime_actions` (2) |
| episode.py | 56 | Role `results`, entry role `results`, commissioning parent `sequence_homology_evidence`, no children; permitted actions `('tool',)` or `('tool','wait')` for an API service assignment; adds BlastResultGrading; replaces_default_instructions=True. | `import:a101.library.blast_axis_summaries` (1), `import:a101.library.blast_return_contracts` (1) |
| execution_contracts.py | 59 | Same constants as local; imports this episode's own terminal_execution. | `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.execution_contracts` (1), `import:a101.launch_instructions` (1), `import:a101.library.blast_return_contracts` (1), `import:a101.local_file_capture_results` (1), `import:a101.native_blast_acquisition` (1), `import:a101.native_blast_database_acquisition` (1), `import:a101.native_blast_masking_acquisition` (1), `import:a101.native_blast_standard_database_acquisition` (1), `import:a101.native_blast_utility_acquisition` (1), `import:a101.native_hmmer_acquisition` (1), `import:a101.native_hmmer_preparation_acquisition` (1), `import:a101.practical_execution_operations` (1), `import:a101.practical_execution_records` (1), `import:a101.practical_execution_state` (1), `import:a101.practical_receipt_information` (1), `import:a101.resource_records` (1) |
| execution_operations.py | 174 | Same as local except role key `results`; catalog gives native result operations execution.results.status / collect / read (bounded byte windows) or the native family catalogs. | `import:a101.bvbrc_proteome_tool_info` (1), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.native_blast_database_results` (1), `import:a101.native_blast_masking_results` (1), `import:a101.native_blast_results` (1), `import:a101.native_blast_standard_database_results` (1), `import:a101.native_blast_utility_results` (1), `import:a101.native_file_capture` (1), `import:a101.native_hmmer_preparation_results` (1), `import:a101.native_hmmer_results` (1) |
| execution_state.py | 101 | initialize differs: validates selector against the target, requires a typed BLAST graded return field in the parent's report contract when the original Launch request asked for graded BLAST, initial references for masking/utility, API initialize or result directory. | `import:a101.episode_receipts` (1), `import:a101.native_blast_database_result_publication` (1), `import:a101.native_blast_standard_database_result_publication` (1), `table:runtime_actions` (1), `table:runtime_episodes` (1), `table:runtime_receipt_inheritance` (2), `table:sqlite_master` (1) |
| from_parent.py | 131 | Assignment schema = RESULTS_SCHEMA (`execution_results_assignment_v1`: handoff_ref + selector, with local_file_source_selector_v1 and native result selector conditions). prepare_assignment: restore a recorded Results commission, read the handoff target, validate selector, admit local file sources, validate masking/utility/standard-DB/DB/BV-BRC/MinHash selected inputs. initial_references = handoff_ref + DB-selected inputs. | `import:a101.bvbrc_data_host` (1), `import:a101.hpc_launch_authentication` (1), `import:a101.native_blast_database_result_publication` (2), `import:a101.native_blast_standard_database_result_publication` (2) |
| from_parent_launch.py | 9 | Identical copy of the parent's Launch form schema. | none |
| goal.py | 9 | Own goal text: "Acquire the original selected execution results through the original handoff. Choose bounded status or requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. ... The scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint." | none |
| internal_summary.py | 64 | decision_context differs: execution_assignment, execution_progress (=facts), execution_target and execution_target_description (status/acquisition operations, provenance), own_bvbrc_values for BV-BRC API targets; selected_execution_task built from the target's assignment. | `import:a101.bvbrc_data_host` (1), `import:a101.library.native_profile_presentation` (1), `import:a101.local_file_capture_results` (1) |
| native_input_custody.py | 313 | Identical to local. | `import:a101.episode_receipts` (1), `import:a101.episode_return_records` (1), `import:a101.execution_contracts` (1), `import:a101.execution_input_versions` (1), `import:a101.library.blast_pairwise_result_views` (1), `import:a101.library.blast_utility_result_views` (2), `import:a101.library.hmmer_native_result_views` (1), `import:a101.library.hmmer_preparation_result_views` (1), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.atac_differential_operands` (1), `import:a101.library.retained_input_authority.expression_nmf_operands` (1), `import:a101.library.retained_input_authority.fluorescence_operands` (1), `import:a101.library.retained_input_authority.flux_balance_request_binding` (1), `import:a101.library.retained_input_authority.lumpy_request_binding` (1), `import:a101.library.retained_input_authority.protein_structure_operands` (1), `import:a101.library.retained_input_authority.received_native_file_inputs` (1), `import:a101.library.sequence_masking_result_views` (2), `table:runtime_actions` (1), `table:runtime_episodes` (1), `table:runtime_report_attempts` (1) |
| received_evidence.py | 351 | Identical to local. | `import:a101.library.blast_pairwise_result_views` (1), `import:a101.library.blast_utility_result_views` (1), `import:a101.library.bvbrc_data_views` (1), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_minhash_views` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.hmmer_native_result_views` (1), `import:a101.library.hmmer_preparation_result_views` (1), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.library.sequence_masking_result_views` (1), `import:a101.library.uniprot_return_contracts` (1) |
| report_delivery.py | 34 | Identical to local. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `table:runtime_forms` (2) |
| result_acquisition.py | 209 | Identical to local (byte-window credit and completeness rules are used here for real). | `table:runtime_actions` (2), `table:runtime_episodes` (1) |
| task.py | 220 | As local plus selected `wait` execution; a wait carries last observed credit and skips automatic score updates. | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.library.read_mapping_values` (1), `import:a101.providers` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.action_schema` (1), `self.workflow.automatic_score_updates` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execute` (1), `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.last_observed_credit` (1), `self.workflow.next_return` (1), `self.workflow.pending_work` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (3), `self.workflow.services` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (7), `self.workflow.validate_report` (1), `table:runtime_actions` (8), `table:runtime_episodes` (1), `table:runtime_model_calls` (2) |
| task_decision.py | 294 | Identical to local. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.contract_information_profile` (1), `self.workflow.contract_information_reply` (1), `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.execute` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.journal` (3), `self.workflow.numerical_contracts` (1), `self.workflow.provider` (4), `self.workflow.receipts` (4), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `table:runtime_model_calls` (8) |
| task_instructions.py | 26 | Identical to local. | `self.workflow.binding_context` (1), `self.workflow.decision_protocol` (1), `self.workflow.knowledge` (1), `self.workflow.launch_instructions` (1), `self.workflow.native_event_information` (1), `self.workflow.permits_common_action` (3), `self.workflow.specialist` (1) |
| task_state.py | 115 | Identical to local. | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.context` (1), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.grains` (1), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `table:runtime_actions` (5) |
| terminal_execution.py | 242 | Identical copy of local's TerminalExecutionBehavior (not this episode's goal; results role does not use exec_command). | `import:a101.acquisition` (1), `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.practical_execution_operations` (1), `import:a101.practical_execution_records` (1), `import:a101.practical_execution_state` (1), `import:a101.practical_receipt_information` (3), `import:a101.practical_yield` (1), `import:a101.terminal_execution` (1), `import:a101.terminal_scientific_evidence` (2), `name:PracticalYieldEstimator` (2) |
| to_parent.py | 294 | As local, plus required_return_sources returns ('execution_result_refs',) when the parent is sequence_homology_evidence and an annotation task is required; facts for API targets come from api_execution with BLAST graded rows; no practical receipt handoffs. | `import:a101.episode_bindings` (2), `import:a101.library.blast_pairwise_result_views` (2), `import:a101.library.blast_result_views` (1), `import:a101.library.blast_utility_result_views` (2), `import:a101.library.bvbrc_data_views` (2), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_minhash_views` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.hmmer_native_result_views` (2), `import:a101.library.hmmer_preparation_result_views` (3), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.library.sequence_masking_result_views` (2), `import:a101.library.uniprot_return_contracts` (2), `import:a101.local_file_capture_results` (1), `import:a101.native_blast_database_results` (2), `import:a101.native_blast_standard_database_results` (2), `import:a101.native_hmmer_acquisition` (1) |
| waiting.py | 31 | As local plus `_execute_selected_wait` (perform_selected_wait; EventTargetError becomes a failed outcome entering the iterator). | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2), `self.workflow.perform_selected_wait` (1) |
| yield_estimator.py | 98 | Own continuation: native unbounded selector -> results_yield_profiles['native_unbounded_<kind>'] plain YieldController; native finite selector -> task profile `results:native_finite_<kind>` with finite_result_yield (endpoint proof if verified; exact zero when no uncredited requested bytes remain; else estimate_bounded_credit_yield with maximum_credit = acquired_record_unit*(1-original fraction)); API -> `results:api_<service>[_<selector version>]`; typed native -> `results:typed_<kind>_<selector version>`, both with PracticalYieldEstimator. | `import:a101.numerical` (1), `import:a101.practical_yield` (3), `name:estimate_bounded_credit_yield` (2), `name:NumericBand` (2), `name:PracticalYieldEstimator` (7), `name:YieldController` (4), `name:YieldEstimate` (2), `name:YieldParameters` (4) |

Old-runner names are counted per file: `self.workflow.<member>` (also `source.workflow` and `workflow.` in module functions), `self.services.<member>`, journal/receipt table names, imports from old shared-root modules (`import:<module>`), and old yield/rebinding names (`name:`). No `BindingContext` literal occurs in these files; the old binding context arrives through `self.workflow.binding_context(...)`. The same rows are in `runs/carry_over/calls/a101_02.tsv`.
